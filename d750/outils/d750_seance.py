#!/usr/bin/env python3
"""Plan d'une séance de calibration du D750 par USB : une vue par Picture Control d'essai, toutes sur la même scène.

Chaque vue = un bloc écrit dans l'emplacement d'essai C-9, activé, déclenché, NEF + JPEG rapatriés (d750_seance.swift).
Le JPEG de chaque vue se compare à son propre NEF : on mesure ce que fait le boîtier, base par base, curseur par curseur.

  d750_seance.py plan <dossier> [--lot portrait|complement|v1|v1-<K>|v2|v2-<K>|biblio|biblio-<K>]   écrit <dossier>/plan.json et les blocs <dossier>/blocs/*.bin
                                     (v2 : K = 5600, 6250, 10000, 4000, 5000, 8000 ; voir plan_v2)
  d750_seance.py ranger <dossier>    range <dossier>/images dans <dossier>/rangees/NN-NOM.{NEF,JPG} d'après le nom du Picture Control
                                     noté dans chaque fichier (exiftool), et signale les vues sans NEF ou sans JPEG
  d750_seance.py --self-test

Le plan (une vue par ligne de PLAN) :
- bases : les sept bases, curseurs à 0, accentuation 0, clarté 0, sans courbe. On n'utilise pas les Picture Control d'usine :
  leurs réglages courants ont pu être retouchés (le Monochrome de Thomas porte un virage, sonde d’octobre 2026) ;
- curseurs : saturation et teinte à -3 et +3 sur les six bases couleur, contraste à -3 et +3 sur Standard et Monochrome ;
- courbe : une courbe identité et une courbe en S, sur Standard, Neutre et Monochrome (la courbe remplace-t-elle celle de la
  base, s'applique-t-elle par canal ou sur la luminance ?) ;
- v0 : les six Picture Control de recettes/d750-v0, tels quels.
"""
import json, os, sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import picture_control as pc

BASES = {1: 'STANDARD', 2: 'NEUTRE', 3: 'SATURE', 4: 'MONOCHROME', 5: 'PORTRAIT', 6: 'PAYSAGE', 7: 'UNIFORME'}
NEUTRE = {'accentuation': 0, 'contraste': 0, 'luminosite': 0, 'clarte': 0}
S = [[0, 0], [64, 44], [128, 128], [192, 212], [255, 255]]
IDENTITE = [[0, 0], [255, 255]]
V0 = os.path.join(ICI, '..', 'recettes', 'd750-v0', 'usb')


def plan(lot='complet'):
    if lot == 'portrait': return plan_portrait()
    if lot == 'complement': return plan_complement()
    if lot.startswith('v1'): return plan_v1(int(lot.split('-')[1]) if '-' in lot else None)
    if lot.startswith('v2'): return plan_v2(int(lot.split('-')[1]) if '-' in lot else None)
    if lot.startswith('biblio'): return plan_biblio(int(lot.split('-')[1]) if '-' in lot else None)
    vues = []
    def vue(nom, base, reglages=None, points=None, recette=None):
        vues.append(dict(nom=nom, base=base, reglages={**NEUTRE, **(reglages or {})}, points=points, recette=recette))
    for b, n in BASES.items():
        vue(f'BASE {n}', b)
    for b, n in BASES.items():
        if b == 4: continue
        for cle, v in (('saturation', -3), ('saturation', 3), ('teinte', -3), ('teinte', 3)):
            vue(f'{n[:8]} {cle[:3].upper()}{v:+d}', b, {cle: v})
    for b in (1, 4):
        for v in (-3, 3):
            vue(f'{BASES[b][:8]} CON{v:+d}', b, {'contraste': v})
    for b in (1, 2, 4):
        vue(f'{BASES[b][:8]} COURBE ID', b, points=IDENTITE)
        vue(f'{BASES[b][:8]} COURBE S', b, points=S)
    for f in sorted(os.listdir(V0)):
        if f.endswith('.json'): vue('V0 ' + f[:-5].upper(), None, recette=os.path.join(V0, f))
    return vues


def plan_portrait():
    """Lot court sur un visage (Thomas, octobre 2026) : la peau, que la scène du premier lot n'avait pas. 24 vues."""
    vues = []
    def vue(nom, base, reglages=None, points=None, recette=None, brut=None):
        vues.append(dict(nom=nom, base=base, reglages={**NEUTRE, **(reglages or {})}, points=points, recette=recette, brut=brut))
    for b, n in BASES.items():
        vue(f'BASE {n}', b)
    for b in (1, 2, 5):
        for cle, v in (('saturation', -3), ('saturation', 3), ('teinte', -3), ('teinte', 3)):
            vue(f'{BASES[b][:8]} {cle[:3].upper()}{v:+d}', b, {cle: v})
    vue('PORTRAIT COURBE ID', 5, points=IDENTITE)
    for f in ('chrome', 'classic-neg', 'kodachrome'):
        vue('V0 ' + f.upper(), None, recette=os.path.join(V0, f + '.json'))
    # le « Portra 400 » actuel de Thomas (C-3), relu par USB en octobre 2026, renommé pour ne pas se confondre avec lui
    sonde = os.path.join(ICI, '..', 'sondes', 'd750', 'usb', '2026-10.5', 'pictctrl_203_0.bin')
    vue('PORTRA ACTUEL', None, brut=sonde)
    return vues


def plan_complement():
    """Ce que le plan complet ne couvre pas (demandé par la session d'analyse, octobre 2026) : filtres Monochrome,
    crans ±1 de saturation et de teinte sur Standard et Neutre, courbes identité et en S sur Portrait. 14 vues."""
    vues = []
    def vue(nom, base, reglages=None, points=None):
        vues.append(dict(nom=nom, base=base, reglages={**NEUTRE, **(reglages or {})}, points=points, recette=None))
    for f in (1, 2, 3, 4):
        vue(f'MONOCHRO {pc.FILTRES[f].upper()}', 4, {'filtre': f})
    for b in (1, 2):
        for cle, v in (('saturation', -1), ('saturation', 1), ('teinte', -1), ('teinte', 1)):
            vue(f'{BASES[b][:8]} {cle[:3].upper()}{v:+d}', b, {cle: v})
    vue('PORTRAIT COURBE ID', 5, points=IDENTITE)
    vue('PORTRAIT COURBE S', 5, points=S)
    return vues


def plan_v1(kelvin=None):
    """Contrôle des recettes v1 (recherche/d750-analyse-seances.md §6) : chacune telle quelle, plus la variante 5 600 K du
    Kodachrome. 10 vues. L'outil ne règle pas la WB : `--lot v1-5600`, `v1-5000`, `v1-10000` ne gardent que les vues à
    prendre avec cette WB (d'après resume.json), une séance par WB ; `--lot v1` les garde toutes."""
    d = os.path.join(ICI, '..', 'recettes', 'd750-v1')
    wb = {e['nom']: e.get('kelvin') or 5600 for e in json.load(open(os.path.join(d, 'resume.json'), encoding='utf-8'))}
    vues = []
    for f in sorted(os.listdir(os.path.join(d, 'usb'))):
        if not f.endswith('.json'): continue
        nom = json.load(open(os.path.join(d, 'usb', f), encoding='utf-8'))['nom']
        if kelvin is None or wb.get(nom, 5600) == kelvin:
            vues.append(dict(nom=nom, base=None, reglages=None, points=None, recette=os.path.join(d, 'usb', f)))
    return vues


BLOCS = [os.path.join(ICI, '..', 'recettes', v, 'blocs') for v in ('d750-v1', 'd750-v2')]
# ce que contiennent C-1 à C-9 : la livraison d’octobre 2026, puis le Tri-X v2 en C-7 en octobre 2026
# (recettes/d750/HISTORIQUE.md) : blocs relus dans le boîtier après écriture, un fichier C-n-<nom>.bin par emplacement
CHARGES = {int(n.split('-')[1]): os.path.join(b, n) for b in BLOCS
           for n in sorted(os.listdir(b)) if n.startswith('C-') and n.endswith('.bin')}
WB_CHARGES = {1: 6250, 7: 10000}   # Kodachrome (spektrafilm vif) et Tri-X (U1) ; les autres à 5 600 K


def plan_v2(kelvin=None):
    """Lot de contrôle n° 2 (recherche/resultats-mesures.md), de jour : les neuf Picture Control tels que chargés dans
    C-1 à C-9 (octets relus après écriture, recopiés dans C-9 sous le même nom), le Tri-X v2 proposé, les crans de Standard
    que les recettes utilisent sans qu'ils aient été mesurés (saturation +2, teinte ±2), deux demi-crans (le bloc accepte
    les quarts de point : effet jamais mesuré), et une vue Standard par WB pour relever les gains réels de 4 000, 5 000 et
    8 000 K (ceux de 5 600, 6 250 et 10 000 K viennent des autres vues). 19 vues, six passages : `--lot v2-<K>` ne garde
    que les vues d'une WB, `--lot v2` les garde toutes."""
    vues = []
    def vue(K, nom, base=None, reglages=None, recette=None, brut=None):
        if kelvin is None or kelvin == K:
            vues.append(dict(nom=nom, base=base, reglages={**NEUTRE, **(reglages or {})}, points=None, recette=recette, brut=brut))
    for c, d in sorted(CHARGES.items()):
        f = d
        vue(WB_CHARGES.get(c, 5600), pc.lire_bloc_ptp(open(f, 'rb').read())['nom'], brut=f)
    v2 = os.path.join(ICI, '..', 'recettes', 'd750-v2', 'usb', 'tri-x.json')
    vue(10000, 'TRI-X V2', recette=v2)
    vue(5600, 'BASE STANDARD', 1)
    for cle, v in (('saturation', 2), ('teinte', -2), ('teinte', 2), ('saturation', 2.5), ('teinte', -2.5)):
        vue(5600, f'STANDARD {cle[:3].upper()}{v:+g}', 1, {cle: v})
    for K in (4000, 5000, 8000):
        vue(K, f'WB {K}K', 1)
    return vues



def plan_biblio(kelvin=None):
    """Série courte du lot n° 2 sur la bibliothèque (exemples de la page du blog : jamais le visage ni le pédalier) :
    BASE STANDARD (l'image de départ), puis les neuf Picture Control tels que dans C-1 à C-9 une fois le Tri-X v2 chargé
    en C-7, chacun à sa WB. 10 vues, trois passages (5 600, 6 250, 10 000 K) : `--lot biblio-<K>`."""
    vues = []
    def vue(K, **v):
        if kelvin is None or kelvin == K:
            vues.append({**dict(base=None, reglages=dict(NEUTRE), points=None, recette=None, brut=None), **v})
    vue(5600, nom='BASE STANDARD', base=1)
    for c, d in sorted(CHARGES.items()):
        if c == 7:
            vue(10000, nom='TRI-X', recette=os.path.join(ICI, '..', 'recettes', 'd750-v2', 'usb', 'tri-x.json'))
            continue
        f = d
        vue(WB_CHARGES.get(c, 5600), nom=pc.lire_bloc_ptp(open(f, 'rb').read())['nom'], brut=f)
    return vues


def bloc(v):
    if v.get('recette') and v['nom'] != json.load(open(v['recette'], encoding='utf-8'))['nom']:
        r = json.load(open(v['recette'], encoding='utf-8'))
        return pc.bloc_recette({**r, 'nom': v['nom']}, os.path.dirname(v['recette']))
    if v.get('brut'):
        b = bytearray(open(v['brut'], 'rb').read())
        b[3:23] = v['nom'].encode('ascii').ljust(20, b'\0')
        return bytes(b)
    if v['recette']:
        return pc.bloc_recette(json.load(open(v['recette'], encoding='utf-8')), os.path.dirname(v['recette']))
    lut = pc.lut_points(v['points']) if v['points'] else None
    return pc.bloc_ptp(v['nom'], v['base'], v['reglages'], lut)


def ecrire(dossier, lot='complet'):
    os.makedirs(os.path.join(dossier, 'blocs'), exist_ok=True)
    out = []
    for k, v in enumerate(plan(lot), 1):
        b = bloc(v)
        f = os.path.join('blocs', f'{k:02d}.bin')
        open(os.path.join(dossier, f), 'wb').write(b)
        out.append(dict(numero=k, nom=pc.lire_bloc_ptp(b)['nom'], bloc=f, octets=len(b)))
    json.dump(dict(emplacement='C-9', vues=out), open(os.path.join(dossier, 'plan.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return out


def ranger(dossier):
    """Le classement à la volée de la séance peut décaler une vue sur la suivante (le NEF arrive après le JPEG) ;
    le nom du Picture Control écrit dans le fichier, lui, est sûr. Liens physiques : aucune place de plus."""
    import subprocess
    vues = {v['nom']: v['numero'] for v in json.load(open(os.path.join(dossier, 'plan.json'), encoding='utf-8'))['vues']}
    src = os.path.join(dossier, 'images'); dst = os.path.join(dossier, 'rangees'); os.makedirs(dst, exist_ok=True)
    out = subprocess.run(['exiftool', '-j', '-q', '-PictureControlName', '-FileName', src], capture_output=True, text=True).stdout
    trouve, inconnus = {}, []
    for r in json.loads(out or '[]'):
        nom = str(r.get('PictureControlName', '')).strip().upper()
        tph = r['FileName'].split('-')[-1]
        if nom not in vues: inconnus.append((r['FileName'], nom)); continue
        cible = os.path.join(dst, f"{vues[nom]:02d}-{nom.replace(' ', '_')}{os.path.splitext(tph)[1].upper()}")
        if not os.path.exists(cible): os.link(os.path.join(src, r['FileName']), cible)
        trouve.setdefault(vues[nom], set()).add(os.path.splitext(tph)[1].upper())
    manque = [(n, k) for k, n in vues.items() if trouve.get(n) != {'.NEF', '.JPG'}]
    for f, nom in inconnus: print('hors plan :', f, repr(nom))
    for n, k in sorted(manque): print(f'vue {n:2d} {k} : {sorted(trouve.get(n, []))}')
    print(f'{len(vues) - len(manque)} vues complètes sur {len(vues)}')
    return manque


def self_test():
    import tempfile
    d = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    vues = ecrire(d)
    noms = [v['nom'] for v in vues]
    ok = len(vues) == 7 + 24 + 4 + 6 + 6 and len(set(noms)) == len(noms)
    for v in vues:
        b = open(os.path.join(d, v['bloc']), 'rb').read()
        r = pc.lire_bloc_ptp(b)
        ok &= len(b) in (32, 610) and r['genre'] == 'perso' and len(r['nom']) <= 19
    ok &= sum(v['octets'] == 610 for v in vues) == 6 + 6
    print('self-test', 'OK' if ok else 'ÉCHEC', f'({len(vues)} vues)')
    return ok


if __name__ == '__main__':
    if '--self-test' in sys.argv: sys.exit(0 if self_test() else 1)
    if len(sys.argv) == 3 and sys.argv[1] == 'ranger': sys.exit(1 if ranger(sys.argv[2]) else 0)
    if len(sys.argv) in (3, 5) and sys.argv[1] == 'plan':
        lot = sys.argv[4] if len(sys.argv) == 5 and sys.argv[3] == '--lot' else 'complet'
        for v in ecrire(sys.argv[2], lot): print(f"{v['numero']:2d} {v['nom']:20s} {v['octets']} octets")
        sys.exit(0)
    print(__doc__); sys.exit(2)
