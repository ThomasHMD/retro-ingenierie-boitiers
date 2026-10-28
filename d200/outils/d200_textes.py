#!/usr/bin/env python3
"""Textes des menus du firmware B du D200 (2.01) : chercher, lister, renommer.

Structure (vérifiée sur le binaire, d200/recherche/d200-firmware-image.md §9) :
  13 tables de langue de 2395 pointeurs 32 bits (gros-boutiste), une par langue ; l'identifiant de
  texte (0 à 2394) est le même dans toutes les langues. La langue active est choisie par
  FUN_001389e4 (0x1389E4) d'après les bits 3 à 6 de l'octet 0x9799106A, qui range l'adresse de la
  table dans le mot RAM 0x9799112C. Il n'y a pas de fonction unique de résolution : le code lit
  partout `*(u32 *)(0x9799112C + 4 × identifiant)`, puis passe le pointeur au traceur de texte
  FUN_00085224 (0x85224) ou au calcul de largeur FUN_00085D68 (0x85D68). Une ligne de menu est
  dessinée par FUN_00143DA4 (libellé = identifiant au décalage +2 de l'entrée).
  Les chaînes de chaque langue sont rangées juste après sa table, dans l'ordre inverse des
  identifiants, sans trou : la chaîne i occupe exactement [pointeur i, pointeur i-1). La place
  disponible est donc la longueur de la chaîne elle-même, terminateur compris.
Codage d'une chaîne : mots de 16 bits gros-boutistes, terminés par 0xFFFF. Police proportionnelle
  des menus : 0x200 + code ASCII (0x220 espace, 0x230 à 0x239 chiffres, 0x241 'A'...), lettres
  accentuées minuscules 0x280 à 0x296, majuscules accentuées 0x201 à 0x21F (0x208 = É, 0x214 = ß),
  cyrillique 0x2A0 à 0x2C0 (majuscules) et 0x2D0 à 0x2F0 (minuscules).
  Un code inférieur à 0x100 est un caractère de la police fixe (par exemple les « : » des textes
  d'aide), les codes 0xF001 et suivants sont des pictogrammes.

Notation du texte décodé (et accepté par « renommer ») :
  lettres ordinaires et accents en clair ; `x = caractère x de la police fixe (code brut) ;
  <f005> = un mot de 16 bits quelconque (4 chiffres hexadécimaux).

Utilisation :
  d200_textes.py langues                         les 13 tables
  d200_textes.py chercher <texte> [-i] [--brut]  toutes les occurrences (codage 16 bits) dans le fichier
  d200_textes.py lister <adresse> [n]            décode n chaînes consécutives (1 par défaut)
  d200_textes.py id <langue> <id> [n]            idem, par identifiant (ex. : id fr 254)
  d200_textes.py optimiser [--langue fr|toutes]  les 7 entrées d'Optimiser l'image et leur aide
  d200_textes.py renommer noms.json [--sortie patch.json] [--repointer] [--zone 0x3F7300] [--avec patch.json]
  d200_textes.py --self-test

Fichier de noms pour « renommer » : {"0x25924C": "Tri-X", "fr:214": "Chrome"}. La clé est l'adresse
d'une chaîne (ou « langue:id »). Le nom doit tenir dans la place de la chaîne d'origine (terminateur
compris) : sinon refus, sauf avec --repointer, qui écrit le texte dans une zone libre (--zone,
2 octets d'alignement, octets d'origine 0xFF) et change le pointeur de la table. Les chaînes ASCII 8 bits
des pages de données de visualisation (0x16BCF4 à 0x16BD3C) sont acceptées (15 caractères au plus).
Sortie : fichier de patch au format de d40/patch.py ("firmware": "D200B"), à passer à
`python3 d40/patch.py <fichier>`. Rien n'est flashé, aucun fichier du projet n'est modifié par ce script
sauf la sortie demandée (par défaut d200/patchs/d200-noms.json).
"""
import argparse
import bisect
import json
import re
import struct
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent.parent
FIRMWARE = Path.home() / 'Library/Caches/retro-ingenierie-boitiers/firmware/d200-201/B2000201.bin'
BASE = 0x50000
NB_IDS = 2395
TABLE_LARGEURS = 0x2AE398      # 256 largeurs 16 bits, indexées par l'octet bas du code 0x2xx
LARGEUR_FIXE = 11              # avance de la police fixe (codes inférieurs à 0x100)
LARGEUR_LIBELLE = 154          # plus long libellé déjà affiché dans la liste d'Optimiser l'image (anglais)
# Hors des secteurs de 8 Ko 0x3F8000-0x3FFFFF, que Nikon ne programme jamais (d200-firmware-image.md §6, point 5) ;
# 0x177000-0x17B9FF est pris par les préréglages (d200_preglages.py, chevauchement contrôlé à la combinaison).
ZONES_LIBRES = [(0x0E3600, 0x0EFBF0), (0x1765EA, 0x1D0000), (0x3F72A8, 0x3F8000), (0x400000, 0x40FFFE)]
ZONE_PAR_DEFAUT = 0x3F7300

# (code, nom, base de la table de pointeurs, valeur du sélecteur de langue)
LANGUES = [
    ('de', 'Deutsch', 0x21F3D0, 0), ('en', 'English', 0x233F08, 1), ('es', 'Español', 0x29A504, 2),
    ('fr', 'Français', 0x246600, 3), ('it', 'Italiano', 0x26661C, 4), ('nl', 'Nederlands', 0x286548, 5),
    ('pt', 'Português', 0x35D894, 6), ('ru', 'Russe', 0x341708, 7), ('sv', 'Svenska', 0x20D188, 8),
    ('zh1', 'Chinois (1)', 0x35400C, 9), ('zh2', 'Chinois (2)', 0x3713FC, 10),
    ('ja', 'Japonais', 0x27A504, 11), ('ko', 'Coréen', 0x25ABD8, 12)]
LATINES = ('de', 'en', 'es', 'fr', 'it', 'nl', 'pt', 'sv')

# Les 7 entrées d'Optimiser l'image : (nom anglais, identifiant du libellé, identifiants des lignes d'aide).
# Entrées de menu en 0x159BE0 (20 octets chacune, libellé au décalage +2, aide au +0xC : 0x1FA, 21 lignes).
ENTREES = [
    ('Normal', 214, (506, 507)), ('Softer', 251, (508, 509)), ('Vivid', 252, (510, 511, 512, 513)),
    ('More vivid', 253, (514, 515, 516, 517)), ('Portrait', 217, (518, 519, 520)),
    ('Custom', 221, (521, 522)), ('Black-and-white', 254, ())]

# Chaînes ASCII 8 bits de la page 2 des données de visualisation (ligne « DEVELOPMENT »), table des
# pointeurs en 0x16BC90 (indice = mode d'Optimiser l'image 0 à 6). adresse : (texte, octets du créneau).
CRENEAUX_ASCII = {0x16BD34: ('NORMAL', 8), 0x16BD2C: ('SOFT', 8), 0x16BD24: ('VIVID', 8),
                  0x16BD18: ('MORE VIVID', 12), 0x16BD0C: ('PORTRAIT', 12), 0x16BD04: ('CUSTOM', 8),
                  0x16BCF4: ('BLACK AND WHITE', 16)}
LONGUEUR_ASCII_MAX = 15        # tampon de 16 octets dans le bloc de données, 15 colonnes visibles

MINUSCULES = 'àáâãäçèéêëòóôõöùúûüíåîìï≈'          # 0x280 + indice
MAJUSCULES = {0x201: 'À', 0x202: 'Á', 0x203: 'Â', 0x204: 'Ã', 0x205: 'Ä', 0x206: 'Ç', 0x207: 'È',
              0x208: 'É', 0x209: 'Ê', 0x20A: 'Ë', 0x20B: 'Ò', 0x20C: 'Ó', 0x20D: 'Ô', 0x20E: 'Õ',
              0x20F: 'Ö', 0x210: 'Ù', 0x211: 'Ú', 0x212: 'Û', 0x213: 'Ü', 0x214: 'ß', 0x215: 'Ø',
              0x216: 'ñ', 0x217: '¡', 0x218: '¿', 0x219: 'Í', 0x21A: 'º', 0x21B: 'Å', 0x21F: 'Ñ'}
DECODE = {0x280 + i: c for i, c in enumerate(MINUSCULES)}
DECODE.update(MAJUSCULES)
# cyrillique (russe) : majuscules 0x2A0 + rang dans l'alphabet (Ё en 6e), minuscules 0x2D0 + rang
DECODE.update({0x2A0 + i: c for i, c in enumerate('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')})
DECODE.update({0x2D0 + i: c for i, c in enumerate('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')})
ENCODE = {c: m for m, c in DECODE.items()}


def decoder(mots):
    """Mots 16 bits -> texte (notation du module)."""
    s = []
    for w in mots:
        if 0x220 <= w < 0x27F and w != 0x260:
            s.append(chr(w - 0x200))
        elif w in DECODE:
            s.append(DECODE[w])
        elif 0x20 <= w < 0x7F:
            s.append('`' + chr(w))
        else:
            s.append('<%04x>' % w)
    return ''.join(s)


def encoder(texte):
    """Texte (notation du module) -> mots 16 bits, sans terminateur."""
    mots, i = [], 0
    while i < len(texte):
        c = texte[i]
        m = re.match(r'<([0-9a-fA-F]{4})>', texte[i:])
        if m:
            mots.append(int(m.group(1), 16))
            i += 6
        elif c == '`' and i + 1 < len(texte):
            mots.append(ord(texte[i + 1]))
            i += 2
        elif 0x20 <= ord(c) < 0x7F:
            mots.append(0x200 + ord(c))
            i += 1
        elif c in ENCODE:
            mots.append(ENCODE[c])
            i += 1
        else:
            raise ValueError("caractère %r sans code connu (écrire <xxxx> pour un code brut)" % c)
    if 0xFFFF in mots:
        raise ValueError('0xFFFF est le terminateur')
    return mots


class Firmware:
    def __init__(self, chemin=None):
        self.b = bytes(Path(chemin or FIRMWARE).read_bytes())
        self.tables = {code: [self.u32(base + 4 * i) for i in range(NB_IDS)] for code, _, base, _ in LANGUES}
        self.base = {code: base for code, _, base, _ in LANGUES}
        self.par_adresse = {}
        self.tries = {}
        for code, ptrs in self.tables.items():
            for i, p in enumerate(ptrs):
                self.par_adresse.setdefault(p, []).append((code, i))
            self.tries[code] = sorted((p, i) for i, p in enumerate(ptrs))
        self.largeurs = [self.u16(TABLE_LARGEURS + 2 * i) for i in range(256)]

    def u16(self, a):
        return struct.unpack('>H', self.b[a - BASE:a - BASE + 2])[0]

    def u32(self, a):
        return struct.unpack('>I', self.b[a - BASE:a - BASE + 4])[0]

    def brut(self, a):
        """Mots 16 bits de la chaîne en a, sans le terminateur."""
        mots = []
        while len(mots) < 4000:
            w = self.u16(a + 2 * len(mots))
            if w == 0xFFFF:
                return mots
            mots.append(w)
        raise ValueError('pas de terminateur en 0x%X' % a)

    def pointeur(self, langue, ident):
        return self.tables[langue][ident]

    def octets(self, langue, ident):
        """Taille de la chaîne (terminateur compris) = place disponible."""
        p = self.tables[langue][ident]
        if ident == 0:
            return 2 * len(self.brut(p)) + 2
        return self.tables[langue][ident - 1] - p

    def bornes_pool(self, langue):
        p0 = self.tables[langue][0]
        return self.tables[langue][-1], p0 + 2 * len(self.brut(p0)) + 2

    def chaine_contenant(self, a):
        """(langue, id, début) de la chaîne qui contient l'adresse a, ou None."""
        for code in self.tables:
            debut, fin = self.bornes_pool(code)
            if debut <= a < fin:
                t = self.tries[code]
                k = bisect.bisect_right(t, (a, 99999)) - 1
                p, i = t[k]
                return code, i, p
        return None

    def largeur(self, mots):
        """Largeur en pixels de l'écran, comme FUN_00085D68 (0x85D68) : somme des avances moins 1."""
        t = 0
        for w in mots:
            if w < 0x100:
                t += LARGEUR_FIXE
            elif 0x200 <= w < 0x300:
                t += self.largeurs[w & 0xFF]
            elif 0xF001 <= w < 0xFF00:
                t += self.b[0x2AE598 - BASE + 4 * (w - 0xF001) + 1] * 21      # colonnes du pictogramme
            else:
                t += 21
        return max(t - 1, 0)

    def texte(self, langue, ident):
        return decoder(self.brut(self.tables[langue][ident]))


def verifier_tables(fw):
    """Contrôle : pointeurs décroissants, chaînes jointives, une seule référence par adresse."""
    for code, ptrs in fw.tables.items():
        for i in range(1, NB_IDS):
            assert ptrs[i] < ptrs[i - 1] or (ptrs[i] == ptrs[i - 1] - 2 and not fw.brut(ptrs[i])), (code, i)
            assert ptrs[i] + 2 * len(fw.brut(ptrs[i])) + 2 == ptrs[i - 1], (code, i, 'chaînes non jointives')
    for a, refs in fw.par_adresse.items():
        assert len(refs) == 1, (hex(a), refs)


# ---------------------------------------------------------------------------------------------
def commande_langues(fw):
    print('code\tnom\tsélecteur\ttable de pointeurs\tchaînes (de - à)')
    for code, nom, base, sel in LANGUES:
        d, f = fw.bornes_pool(code)
        print('%s\t%s\t%d\t0x%06X-0x%06X\t0x%06X-0x%06X' % (code, nom, sel, base, base + 4 * NB_IDS - 1, d, f - 1))


def decrire(fw, a):
    mots = fw.brut(a)
    refs = fw.par_adresse.get(a)
    ref = ('%s:%d' % refs[0]) if refs else '-'
    return '0x%06X\t%s\t%d octets\t%d px\t%s' % (a, ref, 2 * len(mots) + 2, fw.largeur(mots), decoder(mots))


def commande_lister(fw, a, n):
    for _ in range(n):
        print(decrire(fw, a))
        a += 2 * len(fw.brut(a)) + 2


def commande_id(fw, langue, ident, n):
    for i in range(ident, ident + n):
        print('%d (0x%04X)\t%s' % (i, i, decrire(fw, fw.pointeur(langue, i))))


def commande_chercher(fw, texte, minuscule_majuscule, brut):
    if brut:
        modele_mots = [ord(c) for c in texte]
    else:
        modele_mots = encoder(texte)
    cibles = [modele_mots]
    if minuscule_majuscule and not brut:
        cibles = [encoder(texte.lower()), encoder(texte.upper()), encoder(texte.capitalize()), modele_mots]
    trouves = {}
    for mots in cibles:
        motif = b''.join(struct.pack('>H', w) for w in mots)
        i = fw.b.find(motif)
        while i >= 0:
            if (i + BASE) % 2 == 0:
                trouves[i + BASE] = len(motif)
            i = fw.b.find(motif, i + 1)
    for a in sorted(trouves):
        c = fw.chaine_contenant(a)
        if c:
            code, ident, debut = c
            mots = fw.brut(debut)
            ext = 'entière' if debut == a and len(mots) == len(modele_mots) else 'dans une chaîne'
            print('0x%06X\t%s:%d\tdébut 0x%06X\t%s\t%s' % (a, code, ident, debut, ext, decoder(mots)))
        else:
            print('0x%06X\t(hors des 13 tables)' % a)
    print('%d occurrence(s)' % len(trouves))


def commande_optimiser(fw, langues):
    for code in langues:
        nom = next(n for c, n, _, _ in LANGUES if c == code)
        print('== %s (%s), table 0x%06X' % (nom, code, fw.base[code]))
        print('entrée\tid\tadresse\toctets\tcaractères max\tpx\ttexte')
        for anglais, ident, aide in ENTREES:
            mots = fw.brut(fw.pointeur(code, ident))
            o = fw.octets(code, ident)
            print('%s\t%d\t0x%06X\t%d\t%d\t%d\t%s' % (anglais, ident, fw.pointeur(code, ident), o, o // 2 - 1,
                                                       fw.largeur(mots), decoder(mots)))
            for h in aide:
                mots = fw.brut(fw.pointeur(code, h))
                o = fw.octets(code, h)
                print('  aide\t%d\t0x%06X\t%d\t%d\t%d\t%s' % (h, fw.pointeur(code, h), o, o // 2 - 1,
                                                           fw.largeur(mots), decoder(mots)))


# ---------------------------------------------------------------------------------------------
def hexa(octets):
    return octets.hex()


def mots_en_octets(mots):
    return b''.join(struct.pack('>H', w) for w in mots)


def resoudre_cle(fw, cle):
    """Clé du fichier de noms -> adresse de chaîne."""
    if re.fullmatch(r'[a-z0-9]+:\d+', cle) and cle.split(':')[0] in fw.tables:
        langue, ident = cle.split(':')
        return fw.pointeur(langue, int(ident))
    return int(cle, 0)


def construire(fw, noms, repointer=False, zone=ZONE_PAR_DEFAUT):
    """Liste de patchs (format d40/patch.py) pour {clé: nouveau nom}. Lève SystemExit si un nom ne tient pas."""
    patchs, avertissements, zone_courante, occupe = [], [], zone, []
    for cle, nom in noms.items():
        a = resoudre_cle(fw, cle)
        if a in CRENEAUX_ASCII:
            ancien, taille = CRENEAUX_ASCII[a]
            try:
                brut = nom.encode('ascii')
            except UnicodeEncodeError:
                sys.exit('%s : texte ASCII seul (page de données, police fixe)' % cle)
            limite = min(taille - 1, LONGUEUR_ASCII_MAX)
            if len(brut) > limite:
                sys.exit('%s : « %s » fait %d caractères, le créneau 0x%X en accepte %d' % (cle, nom, len(brut), a, limite))
            avant = fw.b[a - BASE:a - BASE + taille]
            apres = brut + b'\0' * (taille - len(brut))
            patchs.append({'offset': '0x%X' % (a - BASE), 'avant': {'hex': hexa(avant)}, 'apres': {'hex': hexa(apres)},
                           'note': 'page de données, créneau ASCII 0x%X : « %s » -> « %s »' % (a, ancien, nom)})
            continue
        refs = fw.par_adresse.get(a)
        if not refs:
            sys.exit("%s : aucune table de langue ne pointe sur 0x%X (donner l'adresse du début d'une chaîne, voir « chercher »)" % (cle, a))
        langue, ident = refs[0]
        place = fw.octets(langue, ident)
        try:
            mots = encoder(nom)
        except ValueError as e:
            sys.exit('%s : %s' % (cle, e))
        px = fw.largeur(mots)
        if ident in [e[1] for e in ENTREES] and px > LARGEUR_LIBELLE:
            avertissements.append('%s : « %s » fait %d px, le plus long libellé de cette liste fait %d px (anglais)' % (cle, nom, px, LARGEUR_LIBELLE))
        ancien = fw.texte(langue, ident)
        taille = 2 * len(mots) + 2
        note = '%s id %d (0x%X) : « %s » -> « %s »' % (langue, ident, a, ancien, nom)
        if taille <= place:
            avant = fw.b[a - BASE:a - BASE + place]
            apres = mots_en_octets(mots + [0xFFFF] * (place // 2 - len(mots)))
            patchs.append({'offset': '0x%X' % (a - BASE), 'avant': {'hex': hexa(avant)}, 'apres': {'hex': hexa(apres)}, 'note': note})
            continue
        if not repointer:
            sys.exit('%s : « %s » prend %d octets, la chaîne d\'origine « %s » en offre %d (%d caractères au plus) ; '
                     'ajouter --repointer pour la placer dans une zone libre' % (cle, nom, taille, ancien, place, place // 2 - 1))
        n = taille
        debut = (zone_courante + 1) & ~1
        if not any(lo <= debut and debut + n <= hi for lo, hi in ZONES_LIBRES):
            sys.exit('zone 0x%X + %d octets hors des zones libres %s' % (debut, n, ['0x%X-0x%X' % z for z in ZONES_LIBRES]))
        libre = fw.b[debut - BASE:debut - BASE + n]
        if libre != b'\xff' * n:
            sys.exit('la zone 0x%X n\'est pas vide (octets d\'origine différents de 0xFF)' % debut)
        zone_courante = debut + n
        occupe.append((debut, debut + n))
        patchs.append({'offset': '0x%X' % (debut - BASE), 'avant': {'hex': 'ff' * n}, 'apres': {'hex': hexa(mots_en_octets(mots + [0xFFFF]))},
                       'note': note + ' (nouveau texte, zone libre)'})
        cellule = fw.base[langue] + 4 * ident
        patchs.append({'offset': '0x%X' % (cellule - BASE), 'avant': {'hex': hexa(struct.pack('>I', a))},
                       'apres': {'hex': hexa(struct.pack('>I', debut))}, 'note': 'pointeur %s:%d, 0x%X -> 0x%X' % (langue, ident, a, debut)})
    return patchs, avertissements


def octets_de(v):
    """Champ « avant » ou « apres » d'un patch (format de d40/patch.py) : {"hex": ...} ou texte ASCII."""
    return bytes.fromhex(v['hex']) if isinstance(v, dict) else v.encode('ascii')


def intervalles(patchs):
    res = []
    for p in patchs:
        o = int(p['offset'], 16)
        res.append((o, o + len(octets_de(p['avant'])), p.get('note', '')))
    return sorted(res)


def controler_chevauchement(patchs):
    iv = intervalles(patchs)
    for (a0, a1, n0), (b0, b1, n1) in zip(iv, iv[1:]):
        if b0 < a1:
            sys.exit('deux patchs se chevauchent à 0x%X (%s / %s)' % (b0 + BASE, n0, n1))


def appliquer_en_memoire(fw, patchs):
    data = bytearray(fw.b)
    for p in patchs:
        o = int(p['offset'], 16)
        avant, apres = octets_de(p['avant']), octets_de(p['apres'])
        apres = apres.ljust(len(avant), b' ')
        assert bytes(data[o:o + len(avant)]) == avant, 'octets d\'origine différents à 0x%X' % (o + BASE)
        data[o:o + len(avant)] = apres
    return bytes(data)


def commande_renommer(fw, fichier, sortie, repointer, zone, avec):
    noms = json.loads(Path(fichier).read_text(encoding='utf-8'))
    patchs, avertissements = construire(fw, noms, repointer, zone)
    description = 'D200 2.01, noms de menu : ' + ', '.join('%s -> %s' % (k, v) for k, v in noms.items()) + '. Jamais flashé.'
    if avec:
        autre = json.loads(Path(avec).read_text(encoding='utf-8'))
        if autre.get('firmware') != 'D200B':
            sys.exit('%s n\'est pas un patch D200B' % avec)
        patchs = autre['patchs'] + patchs
        description = autre.get('description', '').rstrip() + ' + ' + description
    controler_chevauchement(patchs)
    appliquer_en_memoire(fw, patchs)       # contrôle : octets d'origine conformes
    for av in avertissements:
        print('ATTENTION largeur : ' + av, file=sys.stderr)
    sortie = Path(sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps({'firmware': 'D200B', 'description': description, 'patchs': patchs}, indent=1, ensure_ascii=False) + '\n',
                      encoding='utf-8')
    print('%d patch(s) écrit(s) dans %s' % (len(patchs), sortie))
    print('suite : python3 d40/patch.py %s --sortie <dossier>' % sortie)


# ---------------------------------------------------------------------------------------------
def self_test():
    import importlib.util
    import tempfile
    sys.dont_write_bytecode = True
    if not FIRMWARE.exists():
        sys.exit('firmware absent : %s' % FIRMWARE)
    fw = Firmware()
    verifier_tables(fw)
    # « Noir et blanc » à 0x25924C (menu, id 254) et 0x2592B8 (groupe Monochrome, id 248)
    assert fw.pointeur('fr', 254) == 0x25924C and fw.pointeur('fr', 248) == 0x2592B8
    assert fw.texte('fr', 254) == 'Noir et blanc' and fw.texte('fr', 248) == 'Noir et blanc'
    assert fw.octets('fr', 254) == 28
    assert fw.texte('en', 254) == 'Black-and-white' and fw.pointeur('en', 254) == 0x244FA4
    assert [fw.texte('fr', e[1]) for e in ENTREES] == ['Normale', 'Moins nette', 'Saturée', 'Plus saturée', 'Portrait', 'Personnalisée', 'Noir et blanc']
    assert [fw.texte('en', e[1]) for e in ENTREES] == ['Normal', 'Softer', 'Vivid', 'More vivid', 'Portrait', 'Custom', 'Black-and-white']
    motif_perso = mots_en_octets(encoder('Personnalis'))
    perso, i = [], fw.b.find(motif_perso)
    while i >= 0:
        perso.append(i + BASE)
        i = fw.b.find(motif_perso, i + 1)
    assert perso == [0x25799C, 0x257B82, 0x259394, 0x2594F2], [hex(x) for x in perso]
    # aller-retour décodage / codage sur toutes les chaînes des langues latines
    for code in LATINES + ('ru',):
        for i in range(NB_IDS):
            mots = fw.brut(fw.pointeur(code, i))
            assert encoder(decoder(mots)) == mots, (code, i, decoder(mots))
    assert decoder([0x287, 0x208, 0x214]) == 'éÉß' and encoder('Élevée') == [0x208, 0x26C, 0x265, 0x276, 0x287, 0x265]
    assert fw.largeur(encoder('Tri-X')) < LARGEUR_LIBELLE
    # chercher
    d = tempfile.TemporaryDirectory()
    trouves = {}
    for a in (0x25924C, 0x2592B8):
        trouves[a] = fw.chaine_contenant(a)
    assert trouves[0x25924C][:2] == ('fr', 254)
    motif = mots_en_octets(encoder('Noir et blanc'))
    adresses = set()
    i = fw.b.find(motif)
    while i >= 0:
        adresses.add(i + BASE)
        i = fw.b.find(motif, i + 1)
    assert {0x25924C, 0x2592B8} <= adresses
    # zones libres bien vides
    for lo, hi in ZONES_LIBRES:
        assert set(fw.b[lo - BASE:hi - BASE]) == {0xFF}, hex(lo)
    # d40/patch.py
    spec = importlib.util.spec_from_file_location('patch_d200', ICI / 'd40/patch.py')
    patch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patch)
    original = bytes(patch.charger_original('D200B'))
    assert original == fw.b, 'le firmware lu n\'est pas celui de d40/patch.py'
    # nom plus court : « Noir et blanc » -> « Tri-X »
    patchs, _ = construire(fw, {'0x25924C': 'Tri-X'})
    mod = bytes(patch.appliquer(bytearray(original), patchs))
    f2 = Firmware.__new__(Firmware)
    f2.b = mod
    assert decoder(f2.brut(0x25924C)) == 'Tri-X' and mod[0x25924C - BASE + 12:0x25924C - BASE + 28] == b'\xff' * 16
    assert patch.crc16_xmodem(mod) == 0, 'CRC du fichier modifié'
    # trop long : refusé ; --repointer : zone libre + pointeur
    try:
        construire(fw, {'fr:254': 'Noir et blanc contrasté'})
    except SystemExit:
        pass
    else:
        raise AssertionError('nom trop long accepté sans --repointer')
    patchs, _ = construire(fw, {'fr:254': 'Noir et blanc contrasté'}, repointer=True)
    assert len(patchs) == 2 and patchs[1]['offset'] == '0x%X' % (fw.base['fr'] + 4 * 254 - BASE)
    mod = bytes(patch.appliquer(bytearray(original), patchs))
    f2.b = mod
    nouveau = f2.u32(fw.base['fr'] + 4 * 254)
    assert nouveau == ZONE_PAR_DEFAUT and decoder(f2.brut(nouveau)) == 'Noir et blanc contrasté'
    assert patch.crc16_xmodem(mod) == 0
    # créneau ASCII de la page de données
    patchs, _ = construire(fw, {'0x16BD34': 'TRI-X'})
    mod = bytes(patch.appliquer(bytearray(original), patchs))
    assert mod[0x16BD34 - BASE:0x16BD34 - BASE + 8] == b'TRI-X\0\0\0'
    try:
        construire(fw, {'0x16BD34': 'TRI-X HP5'})
    except SystemExit:
        pass
    else:
        raise AssertionError('créneau ASCII dépassé accepté')
    # fusion avec le patch Tri-X existant (sans chevauchement)
    existant = ICI / 'd200' / 'patchs' / 'd200-nb-trix.json'
    if existant.exists():
        autre = json.loads(existant.read_text(encoding='utf-8'))
        fusion = autre['patchs'] + construire(fw, {'fr:254': 'Tri-X'})[0]
        controler_chevauchement(fusion)
        mod = bytes(patch.appliquer(bytearray(original), fusion))
        assert patch.crc16_xmodem(mod) == 0
    # commande complète dans un dossier temporaire
    chemin = Path(d.name) / 'noms.json'
    chemin.write_text(json.dumps({'0x25924C': 'Tri-X'}), encoding='utf-8')
    commande_renommer(fw, chemin, Path(d.name) / 'patch.json', False, ZONE_PAR_DEFAUT, None)
    doc = json.loads((Path(d.name) / 'patch.json').read_text(encoding='utf-8'))
    assert doc['firmware'] == 'D200B' and len(doc['patchs']) == 1
    d.cleanup()
    print('self-test OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['langues', 'chercher', 'lister', 'id', 'optimiser', 'renommer'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('-i', action='store_true', help='chercher : insensible à la casse (minuscules, majuscules, initiale)')
    ap.add_argument('--brut', action='store_true', help='chercher : codes bruts (police fixe), sans le décalage 0x200')
    ap.add_argument('--langue', default='fr', help='optimiser : code de langue ou « toutes »')
    ap.add_argument('--sortie', default=str(ICI / 'd200' / 'patchs' / 'd200-noms.json'))
    ap.add_argument('--repointer', action='store_true')
    ap.add_argument('--zone', default=hex(ZONE_PAR_DEFAUT))
    ap.add_argument('--avec', help='patch existant à fusionner (ex. d200/patchs/d200-nb-trix.json)')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.action:
        ap.error('action manquante')
    fw = Firmware()
    if a.action == 'langues':
        commande_langues(fw)
    elif a.action == 'chercher':
        commande_chercher(fw, ' '.join(a.args), a.i, a.brut)
    elif a.action == 'lister':
        commande_lister(fw, int(a.args[0], 0), int(a.args[1]) if len(a.args) > 1 else 1)
    elif a.action == 'id':
        commande_id(fw, a.args[0], int(a.args[1], 0), int(a.args[2]) if len(a.args) > 2 else 1)
    elif a.action == 'optimiser':
        commande_optimiser(fw, [c for c, _, _, _ in LANGUES] if a.langue == 'toutes' else [a.langue])
    elif a.action == 'renommer':
        if not a.args:
            ap.error('fichier de noms manquant')
        commande_renommer(fw, a.args[0], a.sortie, a.repointer, int(a.zone, 0), a.avec)


if __name__ == '__main__':
    sys.exit(main())
