#!/usr/bin/env python3
"""Simulateur du rendu JPEG du D200 (firmware B 2.01) : NEF → ce que le boîtier produirait, avec le firmware
d'origine ou avec des patchs (JSON au format de d40/patch.py), pour juger un rendu avant de flasher.

Chaîne lue dans le firmware (d200/recherche/d200-firmware-image.md) :
  NEF (LibRaw : linéarisation, noir, balance du boîtier, dématriçage) → RGB caméra linéaire, saturation = 1
  → matrice caméra (3×3, /512) → courbe par canal (4 096 entrées, entrée linéaire 12 bits, sortie 8 bits)
  → matrice YCbCr (3×3, /256 : Y, Cb, Cr) → JPEG.
  Couleur : les deux matrices viennent de la table 0x384BF8 (294 entrées, 126 à 209 vides), la courbe des 21 courbes intégrées
  (0x3884D8) ou de la courbe perso ; N&B neutre : matrice caméra et Y en dur dans le code (0xD57E6), courbe
  0x3B22DD sur les trois canaux, Cb = Cr = 0.
Non simulé : étage à 16 secteurs, table de saturation (0x5001EC00), netteté, réduction de bruit.

  d200_simulateur.py rendu <nef> <sortie.jpg> [--patch p.json] [--nb] [--matrice n] [--courbe n]
  d200_simulateur.py valider <nef>…       meilleure matrice et meilleure courbe, ΔE2000 contre le JPEG du boîtier
  d200_simulateur.py --self-test
"""
import argparse
import io
import json
import pathlib
import struct
import subprocess
import sys
import warnings

import numpy as np

warnings.filterwarnings('ignore')
FIRMWARE = pathlib.Path.home() / 'Library/Caches/retro-ingenierie-boitiers/firmware/d200-201/B2000201.bin'
BASE = 0x50000
MATRICES, N_MATRICES = 0x384BF8, 294      # 24 demi-mots par entrée : caméra (9), YCbCr (9), 6 autres
COURBES, N_COURBES = 0x3884D8, 21         # 256 seuils 16 bits par courbe (FUN_0005df82)
COURBE_NB = 0x3B22DD                      # 4 096 octets, N&B neutre (FUN_000dcf50, index 0)
COURBE_USINE = 0x17329C                   # 2 048 octets, courbe perso quand aucune n'est chargée
# N&B neutre (FUN_000d57e6, _DAT_97be3dbc = 1, _DAT_97be3db8 = 0)
NB_CAMERA = np.array([[744, -223, -9], [-41, 656, -103], [-23, -7, 542]]) / 512
NB_YCC = np.array([[76, 151, 29], [0, 0, 0], [0, 0, 0]]) / 256


def firmware(patch=None):
    b = bytearray(FIRMWARE.read_bytes())
    if patch:
        for p in json.loads(pathlib.Path(patch).read_text())['patchs']:
            o, avant, apres = int(p['offset'], 16), bytes.fromhex(p['avant']['hex']), bytes.fromhex(p['apres']['hex'])
            assert b[o:o + len(avant)] == avant, f'patch {p["offset"]} : octets d’origine différents'
            b[o:o + len(apres)] = apres
    return bytes(b)


def lire(b, adresse, n):
    return b[adresse - BASE:adresse - BASE + n]


def matrices(b):
    """294 couples (caméra /512, YCbCr /256)."""
    out = []
    for n in range(N_MATRICES):
        v = struct.unpack('>24h', lire(b, MATRICES + 48 * n, 48))
        out.append((np.array(v[:9]).reshape(3, 3) / 512, np.array(v[9:18]).reshape(3, 3) / 256))
    return out


def courbe_seuils(seuils):
    """256 seuils (entrée 12 bits) → table de 4 096 sorties 8 bits, comme FUN_0005df82."""
    lut, i = np.zeros(4096, np.uint8), 0
    for k, s in enumerate(seuils):
        s = min(s, 0xFFF)
        if s >= i:
            lut[i:s + 1] = k
            i = s + 1
    return lut


def courbes(b):
    return [courbe_seuils(struct.unpack('>256H', lire(b, COURBES + 0x200 * n, 0x200))) for n in range(N_COURBES)]


def developper(t2048):
    """Table perso de 2 048 octets → 4 096 entrées (valeur, puis moyenne avec la suivante), comme FUN_0005DF30."""
    t = np.frombuffer(bytes(t2048), np.uint8).astype(np.int32)
    out = np.empty(4096, np.int32)
    out[0:4094:2], out[1:4095:2] = t[:2047], (t[:2047] + t[1:]) >> 1
    out[4094] = out[4095] = t[2047]
    return out.astype(np.uint8)


def courbe_nb(b):
    return np.frombuffer(lire(b, COURBE_NB, 4096), np.uint8)


def rgb(ycc):
    """Y, Cb, Cr (0..255, Cb et Cr centrés sur 0) → sRGB codé 0..1 (BT.601 plein, comme un décodeur JPEG)."""
    y, cb, cr = ycc[..., 0], ycc[..., 1], ycc[..., 2]
    return np.clip(np.stack([y + 1.402 * cr, y - .344136 * cb - .714136 * cr, y + 1.772 * cb], -1) / 255, 0, 1)


def rendre(cam, m_camera, lut, m_ycc):
    lin = np.clip(cam @ np.clip(m_camera, -1023 / 512, 1023 / 512).T, 0, 1)
    code = lut[(lin * 4095).astype(np.int32)].astype(np.float32)
    return rgb(code @ np.asarray(m_ycc, np.float32).T)


def rendre_nb(cam, b):
    return rendre(cam, NB_CAMERA, courbe_nb(b), NB_YCC)


def camera(nef, half=True):
    import rawpy
    r = rawpy.imread(str(nef))
    return r.postprocess(output_color=rawpy.ColorSpace.raw, gamma=(1, 1), no_auto_bright=True, use_camera_wb=True,
                         output_bps=16, half_size=half, user_flip=0).astype(np.float32) / 65535


def jpeg_boitier(nef):
    from PIL import Image
    return Image.open(io.BytesIO(subprocess.run(['exiftool', '-b', '-JpgFromRaw', str(nef)], capture_output=True).stdout))


def ecarts(J, sims, F=6):
    """ΔE2000 bloc par bloc (blocs F×F uniformes du JPEG du boîtier J) entre J et chaque rendu simulé."""
    import colour
    S = colour.RGB_COLOURSPACES['sRGB']
    d65 = colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65']
    lab = lambda v: colour.XYZ_to_Lab(colour.RGB_to_XYZ(colour.models.eotf_sRGB(v), S, d65), d65)
    h, w = J.shape[0] // F * F, J.shape[1] // F * F
    bl = lambda a: a[:h, :w].reshape(h // F, F, w // F, F, 3)
    jb = bl(J)
    ok = ((jb.std((1, 3)).mean(-1) < 0.03) & (jb.mean((1, 3)).max(-1) < 0.95) & (jb.mean((1, 3)).min(-1) > 0.04))
    return [colour.delta_E(lab(bl(s).mean((1, 3))[ok]), lab(jb.mean((1, 3))[ok]), method='CIE 2000') for s in sims], ok


def reduire(img, f):
    h, w = img.shape[0] // f * f, img.shape[1] // f * f
    return img[:h, :w].reshape(h // f, f, w // f, f, 3).mean((1, 3))


def ajuster(cam, J, mats, cs, petit=8, lut=None):
    """Meilleure courbe intégrée (ou la courbe `lut` imposée, courbe perso), puis meilleur jeu de matrices, puis
    ΔE2000 en pleine définition. Rend (jeu, courbe ou None, ΔE par bloc, blocs retenus)."""
    utiles = [i for i, (m, _) in enumerate(mats) if m.any()]
    c, Jp = reduire(cam, petit), reduire(J, petit)
    err = lambda s: float(np.mean(np.abs(s - Jp)))
    m, k = 0, 10
    for _ in range(2):
        if lut is None:
            k = min(range(N_COURBES), key=lambda i: err(rendre(c, mats[m][0], cs[i], mats[m][1])))
        t = cs[k] if lut is None else lut
        m = min(utiles, key=lambda i: err(rendre(c, mats[i][0], t, mats[i][1])))
    (e,), ok = ecarts(J, [rendre(cam, mats[m][0], t, mats[m][1])])
    return m, (k if lut is None else None), e, ok


def jpeg_aligne(nef, cam):
    from PIL import Image
    return np.asarray(jpeg_boitier(nef).resize((cam.shape[1], cam.shape[0]), Image.BOX), np.float32) / 255


def valider(nefs, petit=8):
    """Pour chaque NEF : meilleure courbe intégrée, puis meilleure entrée de matrice, puis ΔE2000 en pleine définition."""
    b = firmware()
    mats, cs = matrices(b), courbes(b)
    for nef in nefs:
        cam = camera(nef)
        m, k, e, ok = ajuster(cam, jpeg_aligne(nef, cam), mats, cs, petit)
        print(f'{pathlib.Path(nef).name}  matrice {m}, courbe {k} : ΔE2000 médiane {np.median(e):.2f}, '
              f'90e centile {np.percentile(e, 90):.2f} ({ok.sum()} blocs uniformes)')


def self_test():
    b = firmware()
    mats, cs = matrices(b), courbes(b)
    vides = [i for i, (m, _) in enumerate(mats) if not m.any()]
    assert vides == list(range(126, 210)), f'entrées vides inattendues : {vides}'
    assert all(abs(m.sum(1) - 1).max() < 0.01 for m, _ in mats if m.any()), 'lignes des matrices caméra ≠ 1'
    assert all((np.diff(c.astype(int)) >= 0).all() and c[0] < 8 and c[-1] == 255 for c in cs), 'courbes intégrées'
    assert abs(NB_CAMERA.sum(1) - 1).max() < 0.01 and NB_YCC[0].sum() == 1
    u = developper(lire(b, COURBE_USINE, 2048))
    assert [int(u[i]) for i in (0, 256, 4095)] == [0, 63, 255], 'courbe perso d’usine'
    print('self-test OK : 294 matrices (126 à 209 vides), 21 courbes, N&B, courbe perso d’usine')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('commande', nargs='?', choices=['rendu', 'valider'])
    ap.add_argument('fichiers', nargs='*')
    ap.add_argument('--patch')
    ap.add_argument('--nb', action='store_true')
    ap.add_argument('--matrice', type=int, default=10)
    ap.add_argument('--courbe', type=int, default=10)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.commande == 'valider':
        return valider(a.fichiers)
    if a.commande == 'rendu':
        from PIL import Image
        b = firmware(a.patch)
        cam = camera(a.fichiers[0], half=False)
        if a.nb:
            img = rendre_nb(cam, b)
        else:
            m = matrices(b)[a.matrice]
            img = rendre(cam, m[0], courbes(b)[a.courbe], m[1])
        Image.fromarray((img * 255 + .5).astype(np.uint8)).save(a.fichiers[1], quality=95)
        return print('écrit', a.fichiers[1])
    ap.print_help()


if __name__ == '__main__':
    sys.exit(main())
