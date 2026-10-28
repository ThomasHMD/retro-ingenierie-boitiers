#!/usr/bin/env python3
"""Pictogrammes des menus du D40 : lire, dessiner, remplacer (patch de données).

Lu dans le code (`icone_dessiner` 0x7C904) : une icône 0x8xxx = liste de tuiles de 4 octets dans
`tblIcones` (0x157904 ; la fin = le pointeur de l'icône suivante). Tuile : octet 0 = position
(quartet haut × largeur, quartet bas × hauteur de la planche), octet 1 = couleur (palette 0x1B0000),
u16 en +2 : bits 8-14 = planche (descripteur de 12 octets à 0x1B01A0 : +0 largeur, +1 hauteur,
+6 bits par ligne, +8 adresse des données), bits 0-7 = numéro du glyphe. Un glyphe = hauteur ×
(bits par ligne / 8) octets, 1 bit par point, bit fort à gauche.

Les préréglages d'Optimisation images : planche 0x10 (40 × 40), un pinceau (glyphe pair) puis un
bloc de lettres (glyphe impair) : N = 5, SO = 7, VI = 9, VI+ = 0xB, PO = 0xD, BW = 0x11.

  icones.py voir <glyphe> [--planche 0x10]          dessin en texte
  icones.py patch "5=N,7=HB,9=CC,0xB=PF,0xD=TX,0x11=H5" > patchs/x.json
  icones.py --self-test
"""
import argparse
import json
import pathlib
import struct
import sys

ICI = pathlib.Path(__file__).resolve().parent.parent
FIRMWARE = ICI / 'firmware' / 'BD400111.bin'
BASE = 0x40000
PLANCHES = 0x1B01A0
POLICE = '/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf'


def planche(b, n):
    d = b[PLANCHES + 12 * n - BASE:PLANCHES + 12 * n - BASE + 12]
    return {'l': d[0], 'h': d[1], 'octets_ligne': d[6] >> 3, 'donnees': struct.unpack('>I', d[8:12])[0]}


def glyphe(b, n, p=0x10):
    pl = planche(b, p)
    t = pl['h'] * pl['octets_ligne']
    a = pl['donnees'] + t * n
    return a, b[a - BASE:a - BASE + t], pl


def en_texte(data, pl):
    r = pl['octets_ligne']
    lignes = []
    for y in range(pl['h']):
        v = int.from_bytes(data[y * r:(y + 1) * r], 'big')
        lignes.append(''.join('#' if v >> (r * 8 - 1 - x) & 1 else '.' for x in range(pl['l'])))
    return lignes


def dessiner(texte, pl, haut=4, bas=35):
    """Lettres blanches sur fond transparent, à la manière des blocs d'origine : capitales de
    32 points de haut (lignes 4 à 35), centrées, police DIN Condensed Bold, seuil à 50 %."""
    from PIL import Image, ImageDraw, ImageFont
    W, H, r = pl['l'], pl['h'], pl['octets_ligne']
    cible = bas - haut + 1
    taille = 20
    while True:  # taille de police dont la hauteur de capitale vaut la cible
        f = ImageFont.truetype(POLICE, taille)
        x0, y0, x1, y1 = f.getbbox('H')
        if y1 - y0 >= cible:
            break
        taille += 1
    im = Image.new('L', (W * 4, H), 0)
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = d.textbbox((0, 0), texte, font=f)
    larg = x1 - x0
    if larg > W - 2:  # trop large : on resserre horizontalement
        tmp = Image.new('L', (larg + 4, H), 0)
        ImageDraw.Draw(tmp).text((-x0 + 2, haut - y0), texte, font=f, fill=255)
        im = tmp.resize((W - 2, H), Image.LANCZOS)
        out = Image.new('L', (W, H), 0)
        out.paste(im, (1, 0))
    else:
        out = Image.new('L', (W, H), 0)
        ImageDraw.Draw(out).text(((W - larg) // 2 - x0, haut - y0), texte, font=f, fill=255)
    px = out.load()
    data = bytearray()
    for y in range(H):
        v = 0
        for x in range(r * 8):
            v = v << 1 | (1 if x < W and px[x, y] >= 128 else 0)
        data += v.to_bytes(r, 'big')
    return bytes(data)


def patch(spec, b):
    patchs, desc = [], []
    for morceau in spec.split(','):
        g, _, texte = morceau.partition('=')
        a, avant, pl = glyphe(b, int(g, 0))
        apres = dessiner(texte, pl)
        patchs.append({'offset': hex(a - BASE), 'avant': {'hex': avant.hex()}, 'apres': {'hex': apres.hex()}})
        desc.append(f'glyphe {g} → {texte}')
    return {'description': 'Pictogrammes des préréglages (planche 0x10, 40 × 40) : ' + ', '.join(desc), 'patchs': patchs}


def self_test():
    b = FIRMWARE.read_bytes()
    a, data, pl = glyphe(b, 5)
    assert (pl['l'], pl['h'], pl['octets_ligne']) == (40, 40, 5) and a == 0x20FA00 + 200 * 5
    n = en_texte(data, pl)
    assert n[4].startswith('..........#####') and n[4].rstrip('.').endswith('####')  # le N d'origine
    neuf = dessiner('HB', pl)
    assert len(neuf) == 200 and any(neuf)
    print('self-test OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['voir', 'patch'])
    ap.add_argument('arg', nargs='?')
    ap.add_argument('--planche', type=lambda s: int(s, 0), default=0x10)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    b = FIRMWARE.read_bytes()
    if a.action == 'voir':
        _, data, pl = glyphe(b, int(a.arg, 0), a.planche)
        print('\n'.join(en_texte(data, pl)))
    else:
        print(json.dumps(patch(a.arg, b), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.exit(main())
