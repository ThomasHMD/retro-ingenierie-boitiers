#!/usr/bin/env python3
"""Plan d'une séance de calibration du D200 par USB (une scène = un lot) : tout ce qu'il faut mesurer sans flasher
pour fabriquer ensuite tous les rendus (N&B films, Classic Chrome, Hasselblad, Positive…) dans le firmware.

Chaque vue = des réglages d'Optimiser l'image (et, pour certaines, une courbe perso envoyée par CurveUpload),
un déclenchement, le NEF rapatrié (il embarque le JPEG du boîtier en pleine taille). d200_seance.swift l'exécute.

  d200_seance.py plan <dossier>      écrit <dossier>/plan.json et les courbes <dossier>/courbes/*.bin
  d200_seance.py analyser <dossier>  après la prise de vue : écrit <dossier>/analyse.txt (voir analyser())
  d200_seance.py --self-test

Ce que chaque groupe de vues apprend :
- les 7 choix d'Optimiser l'image : quel jeu de matrices et quelle courbe du firmware sert à quel choix du menu
  (d200_simulateur.py valider) ; le N&B : fidélité du simulateur N&B, base des patchs Tri-X, HP5, FP4 ;
- Personnalisé, tons, mode couleur, saturation : les autres jeux de tables ;
- Personnalisé, teinte de −9 à +9 : ce que fait l'étage à 16 secteurs quand le boîtier tourne les teintes, pour
  écrire ensuite les secteurs de Classic Chrome, Hasselblad et Positive (sur le D40, il avait fallu flasher une sonde) ;
- courbes perso : « usine » (Personnalisée sans changement = Normale ?), « linéaire » (sortie = lumière : l'entrée de la
  courbe est-elle linéaire, où est le blanc), puis les courbes de tonalité de Classic Chrome, Hasselblad et Positive,
  composées comme le seraient celles du firmware (aperçu sans flash, et contrôle de l'exposition transposée).
Le N&B est repris en fin de lot pour voir si la lumière a bougé.
"""
import json
import pathlib
import struct
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI.parent.parent / 'd40' / 'outils'))

# codes des réglages (d200/recherche/d200-ptp-usb.md §4) ; ordre des valeurs : celui des menus, calé sur les valeurs d'usine
OPTIMISER, TONS, MODE, SATURATION, TEINTE, ESPACE = 0xD140, 0xD02B, 0xD02C, 0xD142, 0xD02D, 0xD032
CHOIX = ['normal', 'moins-net', 'sature', 'tres-sature', 'portrait', 'perso', 'noir-et-blanc']
PERSONNALISEE = 4   # Correction des tons › Personnalisée (la courbe perso)
MESURES = ICI.parent.parent / 'd40' / 'recettes' / 'mesures'
LOOKS = {'chrome': 'classic-chrome.json', 'hasselblad': 'hncs.json', 'positive': 'positive-film.json'}


def bloc(table, points=((0, 0), (255, 255))):
    """Bloc CurveUpload de 0x844 octets : préambule (octets 0 et 1 non nuls : la courbe est utilisée), structure
    PTPNIKONCurveData (axes 0-255, gamma 1,00, points recopiés dans le NEF), puis 2 048 sorties sur 8 bits."""
    t = np.asarray(table)
    assert t.shape == (2048,) and t.min() >= 0 and t.max() <= 255 and (np.diff(t) >= 0).all()
    pts = list(points)[:19]
    entete = bytes([1, 1, 0, 0, 0, 0, 0, 255, 0, 255, 1, 0, len(pts)]) + b''.join(bytes(p) for p in pts)
    entete = entete.ljust(68, b'\0')
    return entete + bytes(int(v) for v in t)


def courbes():
    """Tables de 2 048 sorties (entrée linéaire sur 12 bits, une valeur sur deux) : usine, linéaire, looks."""
    import d200_simulateur as sim
    import films_nb
    b = sim.firmware()
    usine = sim.developper(sim.lire(b, sim.COURBE_USINE, 2048)).astype(float)
    out = {'usine': np.frombuffer(sim.lire(b, sim.COURBE_USINE, 2048), np.uint8).astype(int),
           'lineaire': np.round(np.arange(2048) * 255 / 2047).astype(int)}
    for nom, f in LOOKS.items():
        T = json.loads((MESURES / f).read_text())['courbe']
        c = films_nb.courbe_d40(T, usine * 4095 / 255)          # même gris 118 que la courbe Normale du D200
        out[nom] = np.maximum.accumulate(np.round(c[0::2] * 255 / 4095).astype(int).clip(0, 255))
    return out


def plan():
    vues = []

    def vue(nom, optimiser=5, tons=1, mode=0, saturation=1, teinte=0, courbe=None):
        # tous les réglages à chaque vue (une reprise ne dépend pas des vues précédentes) ; Optimiser en dernier.
        # Le mode couleur II n'existe qu'en Adobe RGB (refusé en sRGB, octobre 2026) : espace couleur avant le mode
        espace = 1 if mode == 1 else 0
        vues.append(dict(numero=len(vues) + 1, nom=nom, courbe=courbe,
                         reglages=[[TONS, tons], [ESPACE, espace], [MODE, mode], [SATURATION, saturation], [TEINTE, teinte],
                                   [OPTIMISER, optimiser]]))
    for i, n in enumerate(CHOIX):
        vue(n if n != 'perso' else 'perso-reference', optimiser=i)
    vue('perso-tons-moins', tons=2)
    vue('perso-tons-plus', tons=3)
    vue('perso-mode-II', mode=1)          # JPEG en Adobe RGB
    vue('perso-mode-III', mode=2)
    vue('perso-saturation-moderee', saturation=2)
    vue('perso-saturation-accentuee', saturation=3)
    for t in (-9, -6, -3, 3, 6, 9):
        vue(f'perso-teinte{t:+d}', teinte=t)
    for c in ['usine', 'lineaire'] + list(LOOKS):
        vue(f'courbe-{c}', tons=PERSONNALISEE, courbe=f'courbes/{c}.bin')
    vue('noir-et-blanc-fin', optimiser=6)
    return vues


def ecrire(dossier):
    d = pathlib.Path(dossier)
    (d / 'courbes').mkdir(parents=True, exist_ok=True)
    for nom, t in courbes().items():
        pts = [(int(x), int(t[min(2047, x * 8)])) for x in range(0, 256, 15)] + [(255, int(t[-1]))]
        (d / 'courbes' / f'{nom}.bin').write_bytes(bloc(t, pts))
    v = plan()
    (d / 'plan.json').write_text(json.dumps({'vues': v}, indent=1, ensure_ascii=False))
    print(f'écrit {d / "plan.json"} : {len(v)} vues, dont {sum(1 for x in v if x["courbe"])} avec une courbe perso')


def rotation_cbcr(ref, jpg, reduction=8):
    """Application linéaire 2×2 qui envoie (Cb, Cr) du JPEG `ref` sur ceux de `jpg` (même scène), pixels assez colorés
    et ni bouchés ni brûlés : (rotation en degrés, échelle, résidu médian en niveaux)."""
    from PIL import Image
    lire = lambda f: np.asarray(Image.open(f).convert('YCbCr').reduce(reduction), float).reshape(-1, 3) - [0, 128, 128]
    r, t = lire(ref), lire(jpg)
    m = (np.hypot(r[:, 1], r[:, 2]) > 6) & (r[:, 0] > 20) & (r[:, 0] < 220)
    A = np.linalg.lstsq(r[m][:, 1:], t[m][:, 1:], rcond=None)[0].T
    angle = np.degrees(np.arctan2(A[1, 0] - A[0, 1], A[0, 0] + A[1, 1]))
    return angle, np.sqrt(abs(np.linalg.det(A))), float(np.median(np.abs(t[m][:, 1:] - r[m][:, 1:] @ A.T)))


def analyser(dossier):
    """Ce que la séance apprend, vue par vue, dans <dossier>/analyse.txt :
    - N&B : ΔE2000 du N&B simulé (firmware d'origine) contre le JPEG du boîtier ;
    - couleur sans courbe perso : jeu de matrices et courbe intégrée qui reproduisent le mieux le JPEG ;
    - courbe perso : ΔE2000 avec la courbe envoyée imposée (meilleur jeu de matrices cherché) ;
    - teinte, saturation, mode : rotation et échelle de (Cb, Cr) par rapport à la vue perso-reference."""
    import d200_nb
    import d200_simulateur as sim
    d = pathlib.Path(dossier)
    vues = json.loads((d / 'plan.json').read_text())['vues']
    b = sim.firmware()
    mats, cs = sim.matrices(b), sim.courbes(b)
    trouver = lambda v, ext: next(iter(sorted((d / 'images').glob(f'{v["numero"]:02d}-{v["nom"]}-*.{ext}'))), None)
    ref = next(trouver(v, 'JPG') for v in vues if v['nom'] == 'perso-reference')
    lignes = []
    for v in vues:
        nef = trouver(v, 'NEF')
        if nef is None:
            lignes.append(f'{v["numero"]:2d} {v["nom"]:28s} NEF absent')
            continue
        cam = sim.camera(nef)
        J = sim.jpeg_aligne(nef, cam)
        optimiser = dict(v['reglages'])[OPTIMISER]
        if optimiser == 6:
            (e,), ok = sim.ecarts(J, [d200_nb.rendre(cam, b)])
            quoi = 'N&B simulé'
        elif v['courbe']:
            lut = sim.developper((d / v['courbe']).read_bytes()[68:])
            m, _, e, ok = sim.ajuster(cam, J, mats, cs, lut=lut)
            quoi = f'courbe envoyée, jeu {m}'
        else:
            m, k, e, ok = sim.ajuster(cam, J, mats, cs)
            quoi = f'jeu {m}, courbe {k}'
        ligne = (f'{v["numero"]:2d} {v["nom"]:28s} {quoi:24s} ΔE2000 médian {np.median(e):5.2f}, '
                 f'90e centile {np.percentile(e, 90):5.2f}, lumière {cam.mean():.4f}')
        if optimiser == 5 and not v['courbe'] and v['nom'] != 'perso-reference':
            a, s, r = rotation_cbcr(ref, trouver(v, 'JPG'))
            ligne += f' ; (Cb, Cr) : rotation {a:+5.1f}°, échelle {s:.3f}, résidu {r:.2f}'
        print(ligne)
        lignes.append(ligne)
    (d / 'analyse.txt').write_text('\n'.join(lignes) + '\n')
    print('écrit', d / 'analyse.txt')


def self_test():
    import d200_simulateur as sim
    cs = courbes()
    assert all(len(t) == 2048 and t[0] <= 8 and t[-1] >= 230 for t in cs.values()), 'courbes'  # Chrome finit à 241 : blanc capteur sous 255, comme sur le D40
    b = bloc(cs['usine'])
    assert len(b) == 0x844 and b[0] and b[1], 'bloc'
    # la courbe « usine » envoyée doit redonner, développée, la courbe d'usine du firmware
    assert (sim.developper(b[68:]) == sim.developper(sim.lire(sim.firmware(), sim.COURBE_USINE, 2048))).all()
    v = plan()
    assert len({x['nom'] for x in v}) == len(v) and v[-1]['nom'] == 'noir-et-blanc-fin'
    print(f'self-test OK : {len(v)} vues, {len(cs)} courbes, bloc de {len(b)} octets')


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        self_test()
    elif len(sys.argv) == 3 and sys.argv[1] == 'plan':
        ecrire(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == 'analyser':
        analyser(sys.argv[2])
    else:
        print(__doc__)
