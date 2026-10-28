#!/usr/bin/env python3
"""Rendus film noir et blanc pour le D200 (firmware B 2.01) : patchs du mode « Noir et blanc » d'Optimiser l'image.

Le N&B neutre du D200 (d200/recherche/d200-firmware-image.md) : matrice caméra et ligne Y chargées en dur par des
instructions LDI dans FUN_000d57e6 (0xD7840 à 0xD789C), courbe de 4 096 octets à 0x3B22DD appliquée aux trois
canaux, Cb = Cr = 0. Le patch :
- lignes 0 et 1 de la matrice caméra = k × pondération du film (R, G, B du RGB caméra équilibré, films_nb.poids
  avec les sensibilités camspec du D200) ; trois EXTSB remplacés par NOP pour que les octets chargés par LDI:8
  vaillent 0 à 255 (au lieu de −128 à 127) ; k ramène la plus grande pondération à 255/512 ;
- ligne Y = (128, 128, 0) : Y = R′ = G′, donc gris = courbe(k × pondération · RGB caméra) ;
- courbe : film + tirage (films_nb.courbe), gris moyen calé sur celui du N&B Nikon d'origine, épaule jusqu'au blanc.
Rien n'est flashé : le JSON se fabrique avec `python3 d40/patch.py d40/patchs/d200-nb-<film>.json`.

  d200_nb.py patch <film> [--sortie d40/patchs/d200-nb-<film>.json]     film = trix, hp5, fp4
  d200_nb.py planche <nef> <sortie.jpg> [--films trix hp5]          N&B Nikon | films, côte à côte
  d200_nb.py comparer <dossier de séance>                           N&B simulé contre le JPEG du boîtier
  d200_nb.py --self-test
"""
import argparse
import json
import pathlib
import struct
import sys
import warnings

import numpy as np

warnings.filterwarnings('ignore')
ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI.parent.parent / 'd40' / 'outils'))
sys.path.insert(0, str(ICI.parent.parent / 'd40' / 'outils'))
import d200_simulateur as sim  # noqa: E402

CAMSPEC = pathlib.Path.home() / 'Library/Caches/retro-ingenierie-boitiers/camspec/camspec_database.txt'
BASE = sim.BASE
# Instructions du N&B neutre (FUN_000d57e6), relues dans le désassemblage : (adresse, forme, coefficient)
# forme : 'l20' = LDI:20 #i,R0 (4 octets) ; 'l32' = LDI:32 #i,R0 (6 octets) ; 'l8' = LDI:8 #i,R0 (2 octets),
# suivie ou non de EXTSB R0 (0x9780) à l'adresse + 2.
CAMERA = [(0xD7840, 'l20', 0), (0xD7846, 'l32', 1), (0xD7850, 'l8s', 2),
          (0xD7858, 'l8s', 3), (0xD7860, 'l20', 4), (0xD7868, 'l8s', 5),
          (0xD7870, 'l8s', 6), (0xD7878, 'l8s', 7), (0xD7880, 'l20', 8)]
LIGNE_Y = [(0xD7888, 'l8', 0), (0xD7892, 'l8', 1), (0xD789C, 'l8', 2)]
EXTSB, NOP = b'\x97\x80', b'\x9f\xa0'


def decoder(b, adresse, forme):
    """Valeur chargée dans R0 par l'instruction (et l'éventuel EXTSB qui la suit)."""
    o = adresse - BASE
    if forme == 'l20':
        h, l = struct.unpack_from('>HH', b, o)
        assert h & 0xFF0F == 0x9B00, hex(adresse)
        return ((h >> 4) & 0xF) << 16 | l
    if forme == 'l32':
        h, v = struct.unpack_from('>HI', b, o)
        assert h == 0x9F80, hex(adresse)
        return v - (1 << 32) if v & 0x80000000 else v
    h = struct.unpack_from('>H', b, o)[0]
    assert h & 0xF00F == 0xC000, hex(adresse)
    v = (h >> 4) & 0xFF
    if b[o + 2:o + 4] == EXTSB:
        v = v - 256 if v & 0x80 else v
    return v


def parametres(b):
    """Matrice caméra (/512) et ligne Y (/256) du N&B neutre, lues dans le firmware (patché ou non)."""
    cam = np.array([decoder(b, a, f) for a, f, _ in CAMERA]).reshape(3, 3) / 512
    y = np.array([decoder(b, a, f) for a, f, _ in LIGNE_Y]) / 256
    return cam, np.vstack([y, np.zeros((2, 3))])


def rendre(cam_rgb, b):
    m, y = parametres(b)
    return sim.rendre(cam_rgb, m, sim.courbe_nb(b), y)


def epaule(c):
    """Épaule des préréglages V1 du D40 (recettes_v1.epaule) : la courbe rejoint le blanc (4095) à la pleine échelle
    seulement, en compression douce dès −1,5 IL ; sans elle, le blanc du tirage (243/255 pour Tri-X) arrivait dès
    85 % de l'entrée et les hautes lumières sortaient en gris uniforme (relevé en octobre 2026)."""
    import recettes_v1
    return recettes_v1.epaule(c)


# V2 (octobre 2026) : un tirage par film, pour des rendus typés (en V1, papier grade 2 commun : les trois films ne
# s'écartaient que de 5 à 10 niveaux sur 255). R = étendue d'exposition du papier (grade 2 : 1,10 ; plus petit = plus
# dur), dmax = noir du papier (grade 2 : 2,10 ; plus bas = noirs mats, plus haut = noirs bouchés). Niveaux obtenus
# (gris de la scène à 118, comme le N&B de Nikon), de −2 à +2 IL : Tri-X 17, 47, 118, 200, 241 (contrasté, noirs
# profonds, blancs francs) ; HP5 55, 78, 118, 162, 203 (doux, noirs mats vers 37) ; FP4 34, 64, 118, 180, 224
# (contraste moyen, hautes lumières longues).
TIRAGE = {'trix': {'R': 0.75, 'dmax': 2.15}, 'hp5': {'R': 1.45, 'dmax': 1.75}, 'fp4': {'R': 1.45, 'dmax': 2.2}}


def courbe_film(film, b, version=2):
    """Courbe film + tirage (0..4095, entrée = gris linéaire, blanc capteur = 1) avec l'épaule ; version 1 : papier
    grade 2 commun (V1 flashée en octobre 2026), version 2 : TIRAGE."""
    import films_nb
    ref = sim.courbe_nb(b).astype(float) * 4095 / 255
    c, info = films_nb.courbe(film, ref, 118, TIRAGE[film] if version == 2 else None)
    if version == 2:
        info = {**info, 'tirage': TIRAGE[film]}
    return epaule(c), info


def table_film(film, k, b, version=2):
    """4 096 octets : entrée = k × gris linéaire (blanc capteur = 1) sur 12 bits, sortie 8 bits."""
    c, info = courbe_film(film, b, version)
    v = np.minimum(np.arange(4096) / (4095 * k), 1)
    return np.round(np.interp(v, np.arange(4096) / 4095, c) / 4095 * 255).astype(np.uint8), info


def fabriquer(film, version=2):
    import films_nb
    import matrices_spectrales as ms
    b = sim.firmware()
    w, err = films_nb.poids(film, ms.lire_camspec(CAMSPEC, 'Nikon D200'))
    k = 255 / (w.max() * 512)
    rang = np.round(w * k * 512).astype(int)
    table, info = table_film(film, k, b, version)
    patchs = []

    def remplacer(adresse, avant, apres, note):
        patchs.append({'offset': hex(adresse - BASE), 'avant': {'hex': avant.hex()}, 'apres': {'hex': apres.hex()},
                       'note': note})

    for (a, f, i), v in zip(CAMERA[:6], list(rang) * 2):
        o = a - BASE
        if f == 'l20':
            remplacer(a, b[o:o + 4], struct.pack('>HH', 0x9B00, v), f'matrice N&B [{i}] = {v}')
        elif f == 'l32':
            remplacer(a, b[o:o + 6], struct.pack('>HI', 0x9F80, v), f'matrice N&B [{i}] = {v}')
        else:
            assert b[o + 2:o + 4] == EXTSB
            remplacer(a, b[o:o + 4], struct.pack('>H', 0xC000 | v << 4) + NOP, f'matrice N&B [{i}] = {v}, EXTSB → NOP')
    for (a, f, i), v in zip(LIGNE_Y, (128, 128, 0)):
        o = a - BASE
        remplacer(a, b[o:o + 2], struct.pack('>H', 0xC000 | v << 4), f'ligne Y [{i}] = {v}')
    o = sim.COURBE_NB - BASE
    remplacer(sim.COURBE_NB, b[o:o + 4096], bytes(table), f'courbe N&B {film}')
    doc = {'firmware': 'D200B',
           'description': f'D200 2.01, mode Noir et blanc → {film} : pondération {(w / w.sum()).round(3).tolist()} '
                          f'(erreur médiane {err:.3f}), k = {k:.3f}, {info}, tirage V{version}.',
           'patchs': patchs}
    return doc


def planche(nef, sortie, films):
    from PIL import Image
    cam = sim.camera(nef)
    images = [rendre(cam, sim.firmware())]
    for film in films:
        chemin = pathlib.Path(sim.FIRMWARE.parent / f'.d200-nb-{film}.json')
        chemin.write_text(json.dumps(fabriquer(film)))
        images.append(rendre(cam, sim.firmware(chemin)))
        chemin.unlink()
    img = np.concatenate(images, 1)
    Image.fromarray((img * 255 + .5).astype(np.uint8)).save(sortie, quality=88)
    print('écrit', sortie, '(gauche : N&B Nikon, puis', ', '.join(films) + ')')


def comparer(dossier):
    """N&B simulé (firmware d'origine) contre le JPEG du boîtier, pour les vues N&B d'une séance (d200_seance.swift)."""
    from PIL import Image
    b = sim.firmware()
    nefs = sorted(pathlib.Path(dossier).glob('images/*noir-et-blanc*.NEF')) or sorted(pathlib.Path(dossier).glob('*.NEF'))
    for nef in nefs:
        cam = sim.camera(nef)
        J = np.asarray(sim.jpeg_boitier(nef).convert('RGB').resize((cam.shape[1], cam.shape[0]), Image.BOX), np.float32) / 255
        (e,), ok = sim.ecarts(J, [rendre(cam, b)])
        print(f'{nef.name} : ΔE2000 médian {np.median(e):.2f}, 90e centile {np.percentile(e, 90):.2f} ({ok.sum()} blocs uniformes)')


def self_test():
    b = sim.firmware()
    m, y = parametres(b)
    assert np.allclose(m, sim.NB_CAMERA) and np.allclose(y, sim.NB_YCC), 'décodage des LDI du N&B neutre'
    doc = fabriquer('trix')
    chemin = sim.FIRMWARE.parent / '.d200-nb-test.json'
    chemin.write_text(json.dumps(doc))
    bp = sim.firmware(chemin)
    chemin.unlink()
    m2, y2 = parametres(bp)
    assert np.allclose(m2[0], m2[1]) and np.allclose(y2[0], [.5, .5, 0]), 'lignes du patch'
    assert len(bp) == len(b) and sum(x != z for x, z in zip(b, bp)) < 4096 + 40
    print('self-test OK : LDI du N&B relus, patch Tri-X cohérent, ligne 0 =', (m2[0] * 512).round().tolist())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('commande', nargs='?', choices=['patch', 'planche', 'comparer'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--sortie')
    ap.add_argument('--films', nargs='+', default=['trix', 'hp5'])
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.commande == 'patch':
        film = a.args[0]
        sortie = pathlib.Path(a.sortie or ICI.parent / 'patchs' / f'd200-nb-{film}.json')
        sortie.write_text(json.dumps(fabriquer(film), indent=1, ensure_ascii=False))
        return print('écrit', sortie)
    if a.commande == 'planche':
        return planche(a.args[0], a.args[1], a.films)
    if a.commande == 'comparer':
        return comparer(a.args[0])
    ap.print_help()


if __name__ == '__main__':
    sys.exit(main())
