#!/usr/bin/env python3
"""Fichiers Picture Control de Nikon : lire et écrire un .NCP et un .NP2 (courbe perso comprise), lire un .NP3.

Format d'après l'analyse publique de Pinksert (github.com/Pinksert/Nikon-Picture-Control-NCP-Analysis, README_EN,
lu en octobre 2026 ; dépôt sans licence : rien n'en est recopié, le code est écrit ici) :
- NCP : "NCP\\0", puis des enregistrements type(4) longueur(4) données, gros-boutiste, fin = type 0.
  Type 1 (36 octets) : version "0100", nom ASCII sur 20 octets, base (2), drapeau « modifié », 0xFF, 8 curseurs.
  Type 2 (578 octets) : courbe perso = entête de 64 octets (8 octets fixes, nombre de points, points (x, y) sur 8 bits)
  puis 257 valeurs uint16 de 0 à 32767, appliquées après le gamma sRGB, en dernier.
- Curseurs : valeur + 0x80 ; 0x00 = auto, 0x01 = « géré par la courbe » (contraste, luminosité), 0xFF = sans objet.
  Ordre : accentuation, contraste, luminosité, saturation, teinte, filtre (N&B), virage (N&B), force du virage.
- NP2 : "NCP\\0" puis des cartes type(4) longueur(4) données ; valeur = (v - 0x80) * pas / 16. Écrit ici par `ecrire_np2` d'après
  la lecture, la disposition des cartes du NP3 de gerard662 (voir plus bas) et une vérification dans NX Studio (novembre 2026,
  recherche/rd-nikon-2026-11-formats-nx.md : aucun .NP2 réel n'était disponible ; NX Studio, imposé par fichier
  annexe avec SavedPicConProcess=1, rend un NP2 écrit ici bit à bit comme le NEF qui porte les mêmes réglages).
  Cartes : 0x100 version « 0200 », 0x200 nom (ASCII, 20 octets), 0x300 base, 0x400, 0x500, 0x600 accentuation, 0x700 clarté,
  0x800 contraste, 0x900 luminosité, 0xA00 saturation, 0xB00 teinte, 0xC00 filtre, 0xD00 virage, 0xE00 force du virage, 0x2 courbe.
  Chaque carte réglage = (valeur, pas) : 0xFF sans objet, 0x00 auto (hypothèse, repris du NCP), 0x01 « courbe » (contraste et luminosité).
- NP3 (Flexible Color, boîtiers Z ; lecture seule) : même enveloppe, version « 0310 », cartes en plus 0x1E00 saturation, 0x1F00
  Color Blender (8 teintes × teinte, chroma, luminosité + 4 octets), 0x2000 Color Grading (3 zones × 4 octets, fondu, équilibre).
  Disposition d'après `np3lib.py` de gerard662/nikon-picture-control-matcher (MIT, Copyright (c) 2026 Gerry Needham).
Le D750 lit NCP et NP2 (aide Picture Control Utility 2), pas le NP3. NCP n'a ni clarté ni base Uniforme (Flat).

Bloc USB du D750 (GetPictCtrlData 0x90CC, SetPictCtrlData 0x90CD), d'après le firmware C 1.15 et la doc USB du SDK Nikon
(détail et preuves : recherche/d750-picture-control-usb.md) : 32 octets, petit-boutiste, valeurs signées en quarts de point,
-128 = auto ; si l'octet 31 vaut 1, suivent les 578 octets de la courbe, identiques à l'enregistrement de type 2 d'un NCP
(gros-boutiste). Ce module ne fait que lire et fabriquer des octets : il ne parle à aucun boîtier.

  picture_control.py lire <fichier>             affiche le contenu (NCP, NP2, NP3)
  picture_control.py np2 <recette.json> <sortie.NP2>   écrit un .NP2 (mêmes recettes que `bloc`, plus la clarté)
  picture_control.py ptp <fichier.bin>          décode un bloc lu par d750_ptp.swift (pictctrl_*.bin)
  picture_control.py bloc <recette.json> <sortie.bin>   fabrique le bloc à envoyer par d750_ecrire.swift
      recette : {"nom": "TRI-X COURBE", "base": "Monochrome", "reglages": {"filtre": "aucun", "accentuation": 5, "clarte": 1},
                 "courbe": {"points": [[0, 0], [64, 52], [192, 200], [255, 255]]}}
      courbe (facultative) : "points" (x, y de 0 à 255, interpolation monotone), "lut" (257 valeurs de 0 à 32767)
      ou "ncp" (chemin d'un .NCP, relatif à la recette : sa courbe est reprise à l'octet près)
  picture_control.py --self-test                écrit, relit et compare des fichiers de test
"""
import json, os, struct, sys

BASES = {0x0001: 'Standard', 0x03C2: 'Neutre', 0x00C3: 'Saturé', 0x0486: 'Portrait', 0x04C7: 'Paysage', 0x064D: 'Monochrome',
         0x028E: 'Uniforme (pas en NCP)'}
CURSEURS = ['accentuation', 'contraste', 'luminosite', 'saturation', 'teinte', 'filtre', 'virage', 'force_virage']
FILTRES = ['aucun', 'jaune', 'orange', 'rouge', 'vert']
ENTETE_COURBE = bytes.fromhex('493000ff00ff0100')
BANDES_NP3 = ['rouge', 'orange', 'jaune', 'vert', 'cyan', 'bleu', 'violet', 'magenta']   # Color Blender, d'après gerard662 (MIT)
ZONES_NP3 = ['hautes_lumieres', 'tons_moyens', 'ombres']
BASES_NP3 = {0x0020: 'Flexible Color'}
CARTES_NP2 = {0x100: 'version', 0x200: 'nom', 0x300: 'base', 0x600: 'accentuation', 0x700: 'clarte', 0x800: 'contraste',
              0x900: 'luminosite', 0xA00: 'saturation', 0xB00: 'teinte', 0xC00: 'filtre', 0xD00: 'virage', 0xE00: 'force_virage',
              0x10100: 'legende'}


def code_curseur(v):
    if v in ('auto', None): return 0x00 if v == 'auto' else 0xFF
    if v == 'courbe': return 0x01
    v = int(v)
    if not -126 <= v <= 126: raise ValueError(f'curseur hors plage : {v}')
    return v + 0x80


def lire_curseur(b):
    return {0x00: 'auto', 0x01: 'courbe', 0xFF: None}.get(b, b - 0x80)


def points_courbe(lut, n=20):
    """Points d'ancrage (x, y) sur 8 bits tirés de la table : le logiciel Nikon recalcule la courbe à partir d'eux,
    il faut donc les écrire avec la table (Pinksert, §5)."""
    xs = sorted({round(i * 255 / (n - 1)) for i in range(n)})
    return [(x, round(lut[round(x * 256 / 255)] * 255 / 32767)) for x in xs]


def ecrire_ncp(nom, base, curseurs, lut=None):
    """nom ASCII (19 caractères au plus), base = identifiant (BASES), curseurs = dict de CURSEURS, lut = 257 valeurs 0..32767."""
    if base == 0x028E: raise ValueError('la base Uniforme (Flat) n’existe pas en NCP')
    n = nom.encode('ascii')[:19]
    sl = bytes(code_curseur(curseurs.get(k)) for k in CURSEURS)
    profil = b'0100' + n.ljust(20, b'\0') + struct.pack('>H', base) + bytes([1, 0xFF]) + sl
    assert len(profil) == 36
    out = b'NCP\0' + struct.pack('>II', 1, 36) + profil
    if lut is not None:
        lut = [int(round(v)) for v in lut]
        if len(lut) != 257 or min(lut) < 0 or max(lut) > 32767: raise ValueError('courbe : 257 valeurs de 0 à 32767')
        if any(b < a for a, b in zip(lut, lut[1:])): raise ValueError('courbe non monotone')
        pts = points_courbe(lut)
        tete = ENTETE_COURBE + bytes([len(pts)]) + b''.join(bytes(p) for p in pts)
        out += struct.pack('>II', 2, 578) + tete.ljust(64, b'\0') + struct.pack('>257H', *lut)
    return out + struct.pack('>I', 0)


def _carte_np2(t, d):
    return struct.pack('>II', t, len(d)) + d


def _reglage_np2(cle, v, bornes):
    """Carte (valeur, pas 4) d'un réglage en points (multiples de 0,25) : None sans objet, 'auto', 'courbe'."""
    if v is None: return bytes([0xFF, 4])
    if v == 'auto':
        if not bornes[2]: raise ValueError(f'{cle} : pas d’auto possible')
        return bytes([0x00, 4])
    if v == 'courbe': return bytes([0x01, 4])
    q = round(v * 4)
    if q != v * 4 or not bornes[0] <= v <= bornes[1]: raise ValueError(f'{cle} : {v} hors de [{bornes[0]}, {bornes[1]}] ou pas multiple de 0,25')
    return bytes([0x80 + q, 4])


def ecrire_np2(nom, base, reglages, lut=None):
    """Fichier .NP2 (Picture Control Utility 2 : clarté, base Uniforme). `base` = identifiant (BASES), `reglages` = dict de
    accentuation, clarte, contraste, luminosite, saturation, teinte (points, 'auto' si BORNES_PTP le permet, None = sans objet),
    et pour Monochrome filtre (0 à 4), virage (0 à 9), force_virage ; `lut` = 257 valeurs de 0 à 32767 (alors contraste et
    luminosité sont écrits « courbe », comme le NCP). Défauts : 0 partout, saturation et teinte sans objet en Monochrome."""
    n = nom.encode('ascii')
    if len(n) > 19 or any(not 0x20 <= c < 0x7F for c in n): raise ValueError('nom : 19 caractères ASCII imprimables au plus')
    if base not in BASES: raise ValueError(f'base inconnue : {base:#x}')
    mono = base == 0x064D
    r = dict(accentuation=0, clarte=0, contraste=0, luminosite=0)
    r.update(saturation=None, teinte=None) if mono else r.update(saturation=0, teinte=0)
    r.update(reglages)
    inconnus = set(r) - set(BORNES_PTP) - {'filtre', 'virage'}
    if inconnus: raise ValueError(f'réglages inconnus : {sorted(inconnus)}')
    if mono and (r['saturation'] is not None or r['teinte'] is not None): raise ValueError('Monochrome : ni saturation ni teinte')
    if not mono and any(r.get(k) is not None for k in ('filtre', 'virage', 'force_virage')): raise ValueError('filtre, virage et force : Monochrome seulement')
    if lut is not None:
        r['contraste'] = r['luminosite'] = 'courbe'
        lut = [int(round(v)) for v in lut]
        if len(lut) != 257 or min(lut) < 0 or max(lut) > 32767: raise ValueError('courbe : 257 valeurs de 0 à 32767')
        if any(b < a for a, b in zip(lut, lut[1:])): raise ValueError('courbe non monotone')
    carte = lambda k: _reglage_np2(k, r[k], BORNES_PTP[k])
    if mono:
        virage = r.get('virage', 0)
        if not 0 <= r.get('filtre', 0) <= 4 or not 0 <= virage <= 9: raise ValueError('filtre 0 à 4, virage 0 à 9')
        c_filtre, c_virage = bytes([0x80 + r.get('filtre', 0), 0]), bytes([0x80 + virage, 0])
        c_force = _reglage_np2('force_virage', r['force_virage'], BORNES_PTP['force_virage']) if virage else bytes([0xFF, 4])
    else:
        c_filtre = c_virage = bytes([0xFF, 0]); c_force = bytes([0xFF, 4])
    out = b'NCP\0' + _carte_np2(0x100, b'0200') + _carte_np2(0x200, n.ljust(20, b'\0')) + _carte_np2(0x300, struct.pack('>H', base))
    out += _carte_np2(0x400, b'\0\0') + _carte_np2(0x500, bytes([0xFF, 1]))
    for t, k in ((0x600, 'accentuation'), (0x700, 'clarte'), (0x800, 'contraste'), (0x900, 'luminosite'), (0xA00, 'saturation'), (0xB00, 'teinte')):
        out += _carte_np2(t, carte(k))
    out += _carte_np2(0xC00, c_filtre) + _carte_np2(0xD00, c_virage) + _carte_np2(0xE00, c_force)
    if lut is not None:
        pts = points_courbe(lut)
        tete = ENTETE_COURBE + bytes([len(pts)]) + b''.join(bytes(p) for p in pts)
        out += _carte_np2(0x2, tete.ljust(64, b'\0') + struct.pack('>257H', *lut))
    return out + struct.pack('>I', 0)


def lire(data):
    if data[:4] != b'NCP\0': raise ValueError('pas un fichier Picture Control (magie NCP)')
    version = data[12:16]
    if version == b'0100':
        return lire_ncp(data)
    if version[:2] == b'03':
        return lire_np3(data)
    return lire_np2(data)


def lire_ncp(data):
    i, res = 4, {'format': 'NCP'}
    while i + 4 <= len(data):
        t = struct.unpack('>I', data[i:i + 4])[0]
        if t == 0: break
        n = struct.unpack('>I', data[i + 4:i + 8])[0]; d = data[i + 8:i + 8 + n]; i += 8 + n
        if t == 1:
            base = struct.unpack('>H', d[24:26])[0]
            res.update(version=d[:4].decode(), nom=d[4:24].rstrip(b'\0').decode('ascii', 'replace'),
                       base=BASES.get(base, hex(base)), modifie=d[26], curseurs={k: lire_curseur(b) for k, b in zip(CURSEURS, d[28:36])})
        elif t == 2:
            npts = d[8]
            res['courbe'] = {'entete': d[:8].hex(), 'points': [tuple(d[9 + 2 * k:11 + 2 * k]) for k in range(npts)],
                             'lut': list(struct.unpack('>257H', d[64:64 + 514]))}
        else:
            res.setdefault('autres', []).append((t, d.hex()))
    return res


def _cartes(data):
    """Cartes (type, données) d'un NP2/NP3, dans l'ordre du fichier ; refuse les octets en trop après le terminateur."""
    i, out = 4, []
    while i + 4 <= len(data):
        t = struct.unpack('>I', data[i:i + 4])[0]
        if t == 0:
            if i + 4 != len(data): raise ValueError('octets en trop après le terminateur')
            return out
        n = struct.unpack('>I', data[i + 4:i + 8])[0]
        if i + 8 + n > len(data): raise ValueError('carte tronquée')
        out.append((t, data[i + 8:i + 8 + n])); i += 8 + n
    raise ValueError('terminateur absent')


def _nom(d):
    """Nom d'un NP2/NP3 : ASCII sur 20 octets (NP3 de gerard662, relu) ; UTF-16 gros-boutiste si les octets impairs sont nuls (ancien code, non vérifié)."""
    if len(d) >= 2 and d[0] == 0 and d[1] != 0: return d.decode('utf-16-be', 'replace').rstrip('\0')
    return d.split(b'\0')[0].decode('ascii', 'replace')


def _valeur_carte(d):
    """Carte réglage (valeur, pas) : None = sans objet (0xFF), 'auto' (0x00), 'courbe' (0x01), sinon (v − 0x80) × pas / 16."""
    if len(d) != 2: return d.hex()
    if d[0] == 0xFF: return None
    if d[1] == 0: return d[0] - 0x80   # filtre, virage : indice
    if d[0] == 0x00: return 'auto'
    if d[0] == 0x01: return 'courbe'
    return (d[0] - 0x80) * d[1] / 16


def _courbe(d):
    return {'entete': d[:8].hex(), 'points': [tuple(d[9 + 2 * k:11 + 2 * k]) for k in range(d[8])],
            'lut': list(struct.unpack('>257H', d[64:64 + 514]))}


def lire_np2(data):
    res = {'format': 'NP2', 'cartes': {}}
    for t, d in _cartes(data):
        nom = CARTES_NP2.get(t, hex(t))
        if nom == 'version': v = d.decode('ascii', 'replace')
        elif nom == 'nom': v = _nom(d)
        elif nom == 'base': v = BASES.get(struct.unpack('>H', d[:2])[0], d.hex())
        elif t == 2: res['courbe'] = _courbe(d); continue
        elif nom in CURSEURS + ['clarte']: v = _valeur_carte(d)
        else: v = d.hex()
        res['cartes'][nom] = v
    return res


def lire_np3(data):
    """NP3 Flexible Color : cartes communes lues comme un NP2, plus saturation (0x1E00), Color Blender (0x1F00), Color Grading
    (0x2000), courbe (0x2). Valeurs en unités du fichier (v − 0x80) ; la correspondance avec l'affichage du boîtier n'est pas établie.
    Disposition d'après gerard662/nikon-picture-control-matcher, `np3lib.py` (MIT, Copyright (c) 2026 Gerry Needham)."""
    res = lire_np2(data); res['format'] = 'NP3'
    for t, d in _cartes(data):
        if t == 0x300: res['cartes']['base'] = BASES_NP3.get(struct.unpack('>H', d[:2])[0], d.hex())
        elif t == 0x1E00: res['saturation_flex'] = d[0] - 0x80
        elif t == 0x1F00:
            if len(d) != 28: raise ValueError('Color Blender : 28 octets attendus')
            res['color_blender'] = {n: {'teinte': d[3 * i] - 0x80, 'chroma': d[3 * i + 1] - 0x80, 'luminosite': d[3 * i + 2] - 0x80}
                                    for i, n in enumerate(BANDES_NP3)}
            res['color_blender_fin'] = d[24:].hex()
        elif t == 0x2000:
            if len(d) != 20: raise ValueError('Color Grading : 20 octets attendus')
            res['color_grading'] = {z: {'teinte_deg': ((d[4 * j] & 0x0F) << 8) + d[4 * j + 1], 'chroma': d[4 * j + 2] - 0x80,
                                        'luminosite': d[4 * j + 3] - 0x80} for j, z in enumerate(ZONES_NP3)}
            res['color_grading']['fondu'] = d[16] - 0x80
            res['color_grading']['equilibre'] = d[18] - 0x80
            res['color_grading_reste'] = d[12:16].hex() + d[17:18].hex() + d[19:].hex()
    return res


BASES_PTP = {1: 'Standard', 2: 'Neutre', 3: 'Saturé', 4: 'Monochrome', 5: 'Portrait', 6: 'Paysage', 7: 'Uniforme'}
VIRAGES = ['N&B', 'sépia', 'cyanotype', 'rouge', 'jaune', 'vert', 'bleu-vert', 'bleu', 'violet-bleu', 'rouge-violet']
# bornes acceptées par SetPictCtrlData (validation à 0x9026A6BC du firmware C 1.15), en points ; True = « auto » accepté
BORNES_PTP = {'accentuation': (0, 9, True), 'contraste': (-3, 3, True), 'luminosite': (-1.5, 1.5, False), 'clarte': (-5, 5, True),
              'saturation': (-3, 3, True), 'teinte': (-3, 3, False), 'force_virage': (1, 7, False)}


def _quart(nom, v):
    bas, haut, auto = BORNES_PTP[nom]
    if v == 'auto':
        if not auto: raise ValueError(f'{nom} : pas d’auto possible')
        return 0x80
    q = round(v * 4)
    if q != v * 4 or not bas <= v <= haut: raise ValueError(f'{nom} : {v} hors de [{bas}, {haut}] ou pas multiple de 0,25')
    return q & 0xFF


def bloc_ptp(nom, base, reglages, lut=None, courbe=None):
    """Bloc de données de SetPictCtrlData pour un Picture Control perso (C-1 à C-9) : base = 1 à 7 (BASES_PTP),
    reglages en points ('auto' accepté si BORNES_PTP le permet), lut = 257 valeurs de 0 à 32767 ou None,
    courbe = les 578 octets bruts d'une courbe (enregistrement de type 2 d'un NCP), à la place de lut.
    Couleur : saturation, teinte ; Monochrome : filtre (0 à 4, FILTRES), virage (0 à 9, VIRAGES), force_virage."""
    mono = base == 4
    n = nom.encode('ascii')
    if len(n) > 19 or any(not 0x20 <= c < 0x7F for c in n): raise ValueError('nom : 19 caractères ASCII imprimables au plus')
    b = bytes([base, int(mono), 1]) + n.ljust(20, b'\0')
    if mono:
        virage = reglages.get('virage', 0)
        if not 0 <= reglages.get('filtre', 0) <= 4 or not 0 <= virage <= 9: raise ValueError('filtre 0 à 4, virage 0 à 9')
        b += bytes([reglages.get('filtre', 0), virage, _quart('force_virage', reglages['force_virage']) if virage else 0, 0])
    else:   # accentuation rapide toujours coupée : le boîtier la refuse sur un Picture Control perso
        b += bytes([0, 0, _quart('saturation', reglages.get('saturation', 0)), _quart('teinte', reglages.get('teinte', 0))])
    b += bytes(_quart(k, reglages.get(k, 0)) for k in ('accentuation', 'contraste', 'luminosite', 'clarte'))
    if lut is None and courbe is None: return b + b'\0'
    if courbe is None: courbe = ecrire_ncp(nom, 1, {}, lut)[56:-4]   # enregistrement de type 2 du NCP, sans type ni longueur
    if len(courbe) != 578 or courbe[:2] != ENTETE_COURBE[:2]: raise ValueError('courbe : 578 octets, entête « I0 » attendu')
    assert len(b) == 31
    return b + b'\x01' + courbe


def courbe_ncp(data):
    """Les 578 octets bruts de la courbe d'un .NCP (enregistrement de type 2), ou None."""
    i = 4
    while i + 8 <= len(data):
        t, n = struct.unpack('>II', data[i:i + 8])
        if t == 0: return None
        if t == 2: return data[i + 8:i + 8 + n]
        i += 8 + n
    return None


def lut_points(points):
    """257 valeurs de 0 à 32767 à partir de points (x, y) sur 0..255, par interpolation cubique monotone
    (Fritsch et Carlson : pas de dépassement entre deux points, la courbe reste croissante si les points le sont)."""
    p = sorted((float(x), float(y)) for x, y in points)
    if len(p) < 2 or p[0][0] != 0 or p[-1][0] != 255 or len({x for x, _ in p}) != len(p): raise ValueError('points : x de 0 à 255, distincts')
    if any(b[1] < a[1] for a, b in zip(p, p[1:])): raise ValueError('points : y doit croître avec x')
    xs, ys = [x for x, _ in p], [y for _, y in p]
    d = [(ys[k + 1] - ys[k]) / (xs[k + 1] - xs[k]) for k in range(len(p) - 1)]
    m = [d[0]] + [0 if d[k - 1] * d[k] <= 0 else (d[k - 1] + d[k]) / 2 for k in range(1, len(d))] + [d[-1]]
    for k, dk in enumerate(d):
        if dk == 0: m[k] = m[k + 1] = 0
        else:
            a, b = m[k] / dk, m[k + 1] / dk
            if a * a + b * b > 9: t = 3 / (a * a + b * b) ** 0.5; m[k], m[k + 1] = t * a * dk, t * b * dk
    lut = []
    for i in range(257):
        x = min(255.0, i * 255 / 256); k = max(j for j in range(len(d)) if xs[j] <= x)
        h = xs[k + 1] - xs[k]; t = (x - xs[k]) / h
        y = ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[k] + (t ** 3 - 2 * t ** 2 + t) * h * m[k]
             + (-2 * t ** 3 + 3 * t ** 2) * ys[k + 1] + (t ** 3 - t ** 2) * h * m[k + 1])
        lut.append(min(32767, max(0, round(y * 32767 / 255))))
    return lut


def bloc_recette(recette, dossier='.'):
    """Bloc PTP à partir d'une recette JSON (voir l'aide du module)."""
    base = recette['base']
    if isinstance(base, str): base = {v: k for k, v in BASES_PTP.items()}[base]
    reg = dict(recette.get('reglages', {}))
    for cle, noms in (('filtre', FILTRES), ('virage', VIRAGES)):
        if isinstance(reg.get(cle), str): reg[cle] = noms.index(reg[cle])
    c = recette.get('courbe') or {}
    if 'ncp' in c:
        brute = courbe_ncp(open(os.path.join(dossier, c['ncp']), 'rb').read())
        if brute is None: raise ValueError(f"{c['ncp']} : pas de courbe perso dans ce NCP")
        return bloc_ptp(recette['nom'], base, reg, courbe=brute)
    lut = c.get('lut') or (lut_points(c['points']) if 'points' in c else None)
    return bloc_ptp(recette['nom'], base, reg, lut)


BASE_PTP_VERS_ID = {1: 0x0001, 2: 0x03C2, 3: 0x00C3, 4: 0x064D, 5: 0x0486, 6: 0x04C7, 7: 0x028E}   # BASES_PTP -> BASES


def np2_recette(recette, dossier='.'):
    """Fichier .NP2 à partir d'une recette JSON (même forme que pour `bloc_recette`, la clarté en plus)."""
    base = recette['base']
    if isinstance(base, str): base = {v: k for k, v in BASES_PTP.items()}[base]
    reg = dict(recette.get('reglages', {}))
    for cle, noms in (('filtre', FILTRES), ('virage', VIRAGES)):
        if isinstance(reg.get(cle), str): reg[cle] = noms.index(reg[cle])
    c = recette.get('courbe') or {}
    if 'ncp' in c:
        brute = courbe_ncp(open(os.path.join(dossier, c['ncp']), 'rb').read())
        if brute is None: raise ValueError(f"{c['ncp']} : pas de courbe perso dans ce NCP")
        lut = list(struct.unpack('>257H', brute[64:64 + 514]))
    else:
        lut = c.get('lut') or (lut_points(c['points']) if 'points' in c else None)
    return ecrire_np2(recette['nom'], BASE_PTP_VERS_ID[base], reg, lut)


def lire_bloc_ptp(data):
    """Décode un bloc de GetPictCtrlData (32 ou 610 octets)."""
    if len(data) not in (32, 610): raise ValueError(f'{len(data)} octets : 32 ou 610 attendus')
    s = lambda x: 'auto' if x == 0x80 else (x - 256 if x > 127 else x) / 4
    res = {'base': BASES_PTP.get(data[0], data[0]), 'monochrome': data[1],
           'genre': {0: 'usine', 1: 'perso', 2: 'vide'}.get(data[2], data[2]), 'nom': data[3:23].split(b'\0')[0].decode('ascii', 'replace')}
    if data[1]:
        res.update(filtre=FILTRES[data[23]] if data[23] < 5 else data[23], virage=VIRAGES[data[24]] if data[24] < 10 else data[24],
                   force_virage=s(data[25]) if data[24] else None)
    else:
        res.update(accentuation_rapide=s(data[24]) * 4 if data[23] else None, saturation=s(data[25]), teinte=s(data[26]))
    res.update(accentuation=s(data[27]), contraste=s(data[28]), luminosite=s(data[29]), clarte=s(data[30]), courbe=bool(data[31]))
    if data[31]:
        res['courbe_entete'] = data[32:96].hex()
        res['lut'] = list(struct.unpack('>257H', data[96:610]))
    return res


def self_test():
    ok = True
    # bloc réel lu sur le D750 de Thomas en octobre 2026 (sondes/d750/usb/2026-10.5/pictctrl_202_0.bin, « TRI-X »)
    trix = bytes.fromhex('040101' + b'TRI-X'.hex().ljust(40, '0') + '02000000140c000400')
    r = lire_bloc_ptp(trix)
    ok &= r['nom'] == 'TRI-X' and r['filtre'] == 'orange' and r['accentuation'] == 5 and r['contraste'] == 3 and r['clarte'] == 1
    ok &= bloc_ptp('TRI-X', 4, {'filtre': 2, 'accentuation': 5, 'contraste': 3, 'clarte': 1}) == trix
    lut0 = [min(32767, round(32767 * (i / 256) ** 0.8)) for i in range(257)]
    b = bloc_ptp('TRI-X COURBE', 4, {'accentuation': 5}, lut0)
    ok &= len(b) == 610 and b[31] == 1 and lire_bloc_ptp(b)['lut'] == lut0
    ok &= b[32:] == ecrire_ncp('X', 0x064D, {}, lut0)[56:-4]   # courbe octet pour octet comme dans le NCP
    ncp = ecrire_ncp('X', 0x064D, {}, lut0)
    ok &= bloc_ptp('X', 4, {}, courbe=courbe_ncp(ncp)) == bloc_ptp('X', 4, {}, lut0)
    l = lut_points([[0, 0], [64, 40], [128, 128], [255, 255]])
    ok &= len(l) == 257 and l[0] == 0 and l[-1] == 32767 and all(b >= a for a, b in zip(l, l[1:])) and abs(l[64] - 40 * 32767 / 255) < 300
    r = lire_bloc_ptp(bloc_recette({'nom': 'R', 'base': 'Monochrome', 'reglages': {'filtre': 'orange', 'accentuation': 5},
                                    'courbe': {'points': [[0, 0], [255, 255]]}}))
    ok &= r['filtre'] == 'orange' and r['courbe'] and abs(r['lut'][128] - 16384) < 100
    for mauvais in ({'luminosite': 'auto'}, {'contraste': 3.1}, {'clarte': 6}):
        try: bloc_ptp('X', 1, mauvais); ok = False
        except ValueError: pass
    lut = [min(32767, round(32767 * (i / 256) ** 0.8)) for i in range(257)]
    f = ecrire_ncp('TRI-X V2', 0x064D, {'accentuation': 5, 'contraste': 'courbe', 'luminosite': 'courbe', 'saturation': None,
                                        'teinte': None, 'filtre': 0, 'virage': 0, 'force_virage': None}, lut)
    ok &= len(f) == 638
    r = lire(f)
    ok &= r['nom'] == 'TRI-X V2' and r['base'] == 'Monochrome' and r['curseurs']['contraste'] == 'courbe' and r['courbe']['lut'] == lut
    ok &= len(r['courbe']['points']) == 20 and r['courbe']['entete'] == ENTETE_COURBE.hex()
    g = ecrire_ncp('PLAIN', 0x0001, {k: 0 for k in CURSEURS[:5]})
    ok &= len(g) == 52 and lire(g)['curseurs']['saturation'] == 0 and lire(g)['curseurs']['filtre'] is None
    for mauvais in ([1] * 256, list(range(257))[::-1]):
        try: ecrire_ncp('X', 1, {}, mauvais); ok = False
        except ValueError: pass
    # NP2 : aller-retour, courbe identique à celle du NCP, bornes, Monochrome
    n = ecrire_np2('NP2 TEST', 0x0001, {'accentuation': 3, 'clarte': 2.5, 'saturation': -3, 'teinte': 0.25, 'luminosite': 0.5}, None)
    r = lire(n)['cartes']
    ok &= lire(n)['format'] == 'NP2' and r['nom'] == 'NP2 TEST' and r['base'] == 'Standard' and r['version'] == '0200'
    ok &= (r['accentuation'], r['clarte'], r['contraste'], r['luminosite'], r['saturation'], r['teinte']) == (3, 2.5, 0, 0.5, -3, 0.25)
    ok &= r['filtre'] is None and n[-4:] == b'\0\0\0\0' and [t for t, _ in _cartes(n)] == [0x100, 0x200, 0x300, 0x400, 0x500, 0x600, 0x700, 0x800, 0x900, 0xA00, 0xB00, 0xC00, 0xD00, 0xE00]
    nc = ecrire_np2('C', 0x064D, {'accentuation': 3, 'filtre': 2, 'virage': 1, 'force_virage': 4}, lut)
    ok &= courbe_ncp(nc) == courbe_ncp(ecrire_ncp('C', 0x064D, {}, lut)) and lire(nc)['courbe']['lut'] == lut
    rc = lire(nc)['cartes']
    ok &= (rc['contraste'], rc['luminosite'], rc['filtre'], rc['virage'], rc['force_virage'], rc['saturation']) == ('courbe', 'courbe', 2, 1, 4, None)
    ok &= lire(ecrire_np2('U', 0x028E, {}))['cartes']['base'].startswith('Uniforme')
    for mauvais in ({'saturation': 4}, {'clarte': 5.1}, {'contraste': 0.1}, {'luminosite': 'auto'}, {'filtre': 1}, {'bidule': 1}):
        try: ecrire_np2('X', 0x0001, mauvais); ok = False
        except ValueError: pass
    for mauvais in ((0x064D, {'saturation': 1}), (0x0001, {'virage': 1})):
        try: ecrire_np2('X', mauvais[0], mauvais[1]); ok = False
        except ValueError: pass
    try: ecrire_np2('X' * 20, 1, {}); ok = False
    except ValueError: pass
    ok &= np2_recette({'nom': 'R', 'base': 'Monochrome', 'reglages': {'filtre': 'orange', 'accentuation': 5}, 'courbe': {'points': [[0, 0], [255, 255]]}}) \
        == ecrire_np2('R', 0x064D, {'filtre': 2, 'accentuation': 5}, lut_points([[0, 0], [255, 255]]))
    # NP3 de gerard662 (MIT), s'ils sont là : lecture du Color Blender, du Color Grading et de la courbe
    ref = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'references', 'gerard662')
    for fich, sat, fondu in (('flexible_color_template.NP3', -3, 78), ('flexible_color_template_alt.NP3', 0, 50)):
        f = os.path.join(ref, fich)
        if os.path.exists(f):
            r = lire(open(f, 'rb').read())
            ok &= r['format'] == 'NP3' and r['saturation_flex'] == sat and r['color_grading']['fondu'] == fondu and len(r['color_blender']) == 8
            ok &= r['cartes']['version'] == '0310' and r['cartes']['base'] == 'Flexible Color' and len(r['courbe']['lut']) == 257
    f = os.path.join(ref, 'flexible_color_template.NP3')
    if os.path.exists(f):
        r = lire(open(f, 'rb').read())
        ok &= r['color_blender']['rouge'] == {'teinte': -6, 'chroma': 9, 'luminosite': 17} and r['color_grading']['hautes_lumieres']['teinte_deg'] == 116
        ok &= r['cartes']['nom'] == 'Flexible Template'
    print('self-test', 'OK' if ok else 'ÉCHEC')
    return ok


if __name__ == '__main__':
    if '--self-test' in sys.argv: sys.exit(0 if self_test() else 1)
    if len(sys.argv) == 3 and sys.argv[1] == 'ptp':
        r = lire_bloc_ptp(open(sys.argv[2], 'rb').read())
        if 'lut' in r: r['lut'] = r['lut'][::32]
        print(json.dumps(r, ensure_ascii=False, indent=1)); sys.exit(0)
    if len(sys.argv) == 4 and sys.argv[1] == 'bloc':
        b = bloc_recette(json.load(open(sys.argv[2], encoding='utf-8')), os.path.dirname(os.path.abspath(sys.argv[2])))
        open(sys.argv[3], 'wb').write(b)
        r = lire_bloc_ptp(b); r.pop('lut', None); r.pop('courbe_entete', None)
        print(len(b), 'octets', json.dumps(r, ensure_ascii=False)); sys.exit(0)
    if len(sys.argv) == 4 and sys.argv[1] == 'np2':
        b = np2_recette(json.load(open(sys.argv[2], encoding='utf-8')), os.path.dirname(os.path.abspath(sys.argv[2])))
        open(sys.argv[3], 'wb').write(b); print(len(b), 'octets'); sys.exit(0)
    if len(sys.argv) == 3 and sys.argv[1] == 'lire':
        r = lire(open(sys.argv[2], 'rb').read())
        if 'courbe' in r: r['courbe']['lut'] = r['courbe']['lut'][::32]
        print(json.dumps(r, ensure_ascii=False, indent=1)); sys.exit(0)
    print(__doc__); sys.exit(2)
