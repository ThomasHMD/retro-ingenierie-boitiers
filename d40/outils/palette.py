#!/usr/bin/env python3
"""Palette de l'interface du D40 (firmware B, 0x1B0000, 104 entrées « 00 Y Cb Cr »).

Vérifié (CARTE.md §9) : icone_dessiner (0x7C904) y prend la couleur de chaque tuile d'icône,
l'octet Y va au plan de luminance de l'écran, Cb et Cr aux plans de chrominance ; l'entrée 1
est le rouge pur en BT.601. Ce script produit un patch qui teinte toute la palette d'une seule
couleur en gardant la luminance (Y) ; flashé, il montre quelles zones de l'écran en dépendent.

  palette.py liste                       # les 104 entrées en RGB
  palette.py patch --teinte 1aff80 > patchs/pipboy-palette.json   # vert Pip-Boy
  palette.py patch --teinte ffb642 > patchs/newvegas-palette.json # ambre
"""
import argparse
import json
import pathlib

ICI = pathlib.Path(__file__).resolve().parent.parent
FIRMWARE = ICI / 'firmware' / 'BD400111.bin'
ADRESSE, NB = 0x1B0000, 104
OFFSET = ADRESSE - 0x40000


def vers_rgb(y, cb, cr):
    r = y + 1.402 * (cr - 128)
    g = y - 0.344136 * (cb - 128) - 0.714136 * (cr - 128)
    b = y + 1.772 * (cb - 128)
    return tuple(max(0, min(255, round(v))) for v in (r, g, b))


def vers_ycc(r, g, b):
    y = 0.299 * r + 0.587 * g + 0.114 * b
    return y, 128 - 0.168736 * r - 0.331264 * g + 0.5 * b, 128 + 0.5 * r - 0.418688 * g - 0.081312 * b


def entrees(data):
    return [tuple(data[OFFSET + 4 * i:OFFSET + 4 * i + 4]) for i in range(NB)]


def teinter(e, teinte):
    """Garde Y, remplace la chrominance par celle de la teinte, proportionnelle à Y."""
    ty, tcb, tcr = vers_ycc(*teinte)
    k = e[1] / ty if ty else 0
    cb = max(0, min(255, round(128 + (tcb - 128) * min(k, 1))))
    cr = max(0, min(255, round(128 + (tcr - 128) * min(k, 1))))
    return (0, e[1], cb, cr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['liste', 'patch'])
    ap.add_argument('--teinte', default='1aff80', help='couleur RGB hexadécimale')
    a = ap.parse_args()
    data = FIRMWARE.read_bytes()
    es = entrees(data)
    assert all(e[0] == 0 for e in es), 'le bloc ne commence plus par des entrées 00 Y Cb Cr'
    if a.action == 'liste':
        for i, e in enumerate(es):
            print(i, '%02x %02x %02x %02x' % e, '#%02x%02x%02x' % vers_rgb(*e[1:]))
        return
    teinte = tuple(int(a.teinte[k:k + 2], 16) for k in (0, 2, 4))
    avant = bytes(b for e in es for b in e)
    apres = bytes(b for e in es for b in teinter(e, teinte))
    print(json.dumps({'description': f'Palette de l\'interface (0x1B0000) teintée #{a.teinte}, luminance gardée',
                      'patchs': [{'offset': hex(OFFSET), 'avant': {'hex': avant.hex()}, 'apres': {'hex': apres.hex()}}]},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
