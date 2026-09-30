#!/usr/bin/env python3
"""Simulateur du rendu JPEG du D40 : NEF → ce que le boîtier produirait, avec le firmware d'origine ou
avec des patchs (JSON de patchs/), pour juger un rendu avant de flasher.

Chaîne simulée (vérifiée sur les JPEG d'origine contenus dans les NEF, voir README) :
  NEF (LibRaw : linéarisation, noir, balance du boîtier, dématriçage) → RGB caméra linéaire,
  saturation du capteur = 1 → matrice firmware (0x332888, /512) → courbe de 4 096 entrées
  (entrée = signal linéaire 12 bits, sortie = code 0..4095 → 8 bits) → saturation (facteur sur
  l'écart à la luminance Rec. 601, approximation de l'étage YCbCr) → étage à 16 secteurs de teinte
  (0x331E0E, un jeu de 64 valeurs par matrice, voir `etage`) → JPEG sRGB.
Non simulé : netteté, réduction de bruit, sélection exacte de la matrice selon la balance (on
prend n° 13 en IIIa, la plus proche en moyenne), étage YCbCr exact (0x33270E).

  simulateur.py rendu <nef> <sortie.jpg> [--patch p.json] [--matrice 13] [--courbe 17] [--saturation 1]
  simulateur.py rendu <nef> <sortie.jpg> --recette recettes/v1/<nom>.json [--balance 1]
  simulateur.py valider <nef>…      ΔE2000 contre le JPEG du boîtier, réglages lus dans le NEF
  simulateur.py valider-etage --patch p.json <nef>…   ΔE2000 étage neutre / étage du patch
  simulateur.py --self-test
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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import patch as patchpy  # noqa: E402
import courbes  # noqa: E402
import matrices_spectrales as ms  # noqa: E402

SATURATION = {'Normal': 1.0, 'Low': 0.85, 'Moderate': 0.85, 'Enhanced': 1.2, 'High': 1.2}  # Low mesuré, Enhanced supposé
# Correction des tons → cran de courbe dans un groupe de 7 (CARTE.md §7)
CRAN = {'Low': 0, 'Med.Low': 1, 'Normal': 3, 'Med.High': 5, 'High': 6}
GROUPE = {'Mode1a': 0, 'Mode2': 1, 'Mode3a': 2}
MATRICE_DEFAUT = {0: 1, 1: 7, 2: 13}


def firmware(patch=None):
    b = bytearray(courbes.FIRMWARE.read_bytes())
    if patch:
        for p in json.loads(pathlib.Path(patch).read_text())['patchs']:
            o, apres = int(p['offset'], 16), bytes.fromhex(p['apres']['hex'])
            assert patchpy.avant_conforme(b, o, p['avant']), f'patch {p["offset"]} : octets d’origine différents'
            b[o:o + len(apres)] = apres
    return bytes(b)


def tables(b):
    o = ms.MATRICES - courbes.BASE
    mats = [np.array(struct.unpack('>9h', b[o + 18 * n:o + 18 * n + 18])).reshape(3, 3) / 512 for n in range(18)]
    return mats, courbes.courbes(b)


# Étage à 16 secteurs de teinte (sondes 1 et 2, README « Sonde 2 : résultat »). 18 jeux, un par matrice
# caméra, de 64 int16 big-endian : t1[16], t2[16], t3[16], t4[16] ; neutre t1 = t4 = 256, t2 = t3 = 0.
# Par secteur : [Cb′ ; Cr′] = [t1 t2 ; t3 t4] / 256 · [Cb ; Cr] (YCbCr BT.601 plein). Les valeurs sont
# interpolées linéairement entre les deux nœuds voisins selon l'angle atan2(Cr, Cb) du pixel.
SECTEURS = 0x331E0E
NEUTRE = [256] * 16 + [0] * 32 + [256] * 16
# angle (degrés) du centre de chaque secteur (indice dans les tables), ajusté en octobre 2026 sur les blocs des
# deux sondes (README « V1 : rendus ») : la sonde 1 (indices impairs coupés) fixe la parité, la sonde 2 (t4 en
# rampe) le sens et le départ. Secteur 0 = 184° (jaune-vert), pas 163° comme lu d'abord : décalage d'un nœud.
NOEUDS = [184, 198, 223, 246, 265, 284, 313, 346, 2, 17, 44, 66, 86, 104, 134, 166]
NOEUDS_V0 = [163, 189, 209, 227, 244, 263, 286, 314, 343, 9, 29, 47, 64, 83, 106, 134]  # lecture d’octobre avant ajustement


def jeux_secteurs(b):
    o = SECTEURS - courbes.BASE
    return [list(struct.unpack('>64h', b[o + 128 * n:o + 128 * n + 128])) for n in range(18)]


def ycc(a):
    """sRGB (0..1, codé) → Y, Cb, Cr BT.601 plein (Cb, Cr dans ±0,5)."""
    y = a @ np.array([.299, .587, .114], np.float32)
    return y, (a[..., 2] - y) / 1.772, (a[..., 0] - y) / 1.402


def rgb(y, cb, cr):
    return np.stack([y + 1.402 * cr, y - .344136 * cb - .714136 * cr, y + 1.772 * cb], -1)


def coefficients(theta, jeu, noeuds=NOEUDS):
    """t1..t4 / 256 interpolés à l'angle theta (degrés), par nœud voisin (interpolation linéaire, 360° périodique)."""
    ordre = np.argsort(noeuds)
    ang = np.asarray(noeuds, np.float64)[ordre]
    t = np.asarray(jeu, np.float64).reshape(4, 16)[:, ordre] / 256
    return [np.interp(theta, ang, t[k], period=360).astype(np.asarray(theta).dtype) for k in range(4)]


# Plages des registres de la puce (outils/preglages_v1.signe_grandeur : grandeur + bit de signe) : matrice caméra
# 10 bits + signe (0x400), |coef| ≤ 1 023 à l'échelle 512 ; secteurs et YCbCr 9 bits + signe (0x200), ≤ 511.
# Le simulateur écrête à ces bornes, comme la puce ne peut rien recevoir au-delà.
BORNE_MATRICE = 1023
BORNE_SECTEURS = 511


def etage(img, jeu, noeuds=NOEUDS):
    """Applique un jeu de 64 valeurs de l'étage à 16 secteurs à une image sRGB codée (0..1), écrêtées à ±BORNE_SECTEURS."""
    if jeu is None or list(jeu) == NEUTRE:
        return img
    jeu = np.clip(np.asarray(jeu, float), -BORNE_SECTEURS, BORNE_SECTEURS)
    y, cb, cr = ycc(img)
    t1, t2, t3, t4 = coefficients(np.degrees(np.arctan2(cr, cb)) % 360, jeu, noeuds)
    return np.clip(rgb(y, t1 * cb + t2 * cr, t3 * cb + t4 * cr), 0, 1)


def camera(nef, half=True, tourner=True):
    import rawpy
    r = rawpy.imread(str(nef))
    return r.postprocess(output_color=rawpy.ColorSpace.raw, gamma=(1, 1), no_auto_bright=True, use_camera_wb=True,
                         output_bps=16, half_size=half,
                         **({} if tourner else {'user_flip': 0})).astype(np.float32) / 65535


def rendre(cam, mat, courbe, saturation=1.0, jeu=None):
    """Matrice (/512, coefficients écrêtés à ±BORNE_MATRICE/512 comme dans le registre), courbe, saturation, étage."""
    lut = np.asarray(courbe, np.float32) / 4095
    mat = np.clip(np.asarray(mat, np.float32), -BORNE_MATRICE / 512, BORNE_MATRICE / 512)
    out = lut[(np.clip(cam @ mat.T, 0, 1) * 4095).astype(np.int32)]
    if saturation != 1:
        y = out @ np.array([.299, .587, .114], np.float32)
        out = y[..., None] + (out - y[..., None]) * saturation
    return etage(np.clip(out, 0, 1), jeu)


def recette(chemin, balance=1):
    """Préréglage de recettes/v1 : (matrice /512, courbe, jeu de secteurs) pour l'emplacement de balance donné
    (0 à 5 dans le groupe ; 1 = la n° 13 d'usine en IIIa, celle du simulateur)."""
    r = json.loads(pathlib.Path(chemin).read_text())
    return np.array(r['matrices'][balance]).reshape(3, 3) / 512, r['courbe'], r['secteurs'][balance]


def reglages(nef):
    t = subprocess.run(['exiftool', '-s3', '-ColorHue', '-ToneComp', '-Saturation', '-ColorMode', str(nef)],
                       capture_output=True, text=True).stdout.split('\n')
    return dict(zip(('mode', 'tons', 'saturation', 'couleur'), t))


def jpeg_boitier(nef):
    from PIL import Image
    return Image.open(io.BytesIO(subprocess.run(['exiftool', '-b', '-JpgFromRaw', str(nef)], capture_output=True).stdout))


def ecarts(J, sims, F=6):
    """ΔE2000 bloc par bloc (blocs F×F uniformes du JPEG du boîtier J) entre J et chaque rendu simulé."""
    import colour
    S = colour.RGB_COLOURSPACES['sRGB']
    lab = lambda v: colour.XYZ_to_Lab(colour.RGB_to_XYZ(colour.models.eotf_sRGB(v), S, ms.D65), ms.D65)
    h, w = J.shape[0] // F * F, J.shape[1] // F * F
    bl = lambda a: a[:h, :w].reshape(h // F, F, w // F, F, 3)
    jb = bl(J)
    ok = ((jb.std((1, 3)).mean(-1) < 0.03) & (jb.mean((1, 3)).max(-1) < 0.95) & (jb.mean((1, 3)).min(-1) > 0.04))
    return [colour.delta_E(lab(bl(s).mean((1, 3))[ok]), lab(jb.mean((1, 3))[ok]), method='CIE 2000') for s in sims], ok


def valider(nefs):
    from PIL import Image
    mats, cs = tables(firmware())
    for nef in nefs:
        r = reglages(nef)
        if r['couleur'] != 'Color' or r['mode'] not in GROUPE or r['tons'] not in CRAN:
            print(pathlib.Path(nef).name, 'réglages non simulés', r)
            continue
        g = GROUPE[r['mode']]
        cam = camera(nef, tourner=False)  # le JPEG du NEF n'est pas tourné
        sim = rendre(cam, mats[MATRICE_DEFAUT[g]], cs[7 * g + CRAN[r['tons']]], SATURATION.get(r['saturation'], 1))
        J = np.asarray(jpeg_boitier(nef).resize((cam.shape[1], cam.shape[0]), Image.BOX), np.float32) / 255
        (e,), ok = ecarts(J, [sim])
        print(f'{pathlib.Path(nef).name}  {r["mode"]} tons {r["tons"]} saturation {r["saturation"]} : '
              f'ΔE2000 médiane {np.median(e):.2f}, 90e centile {np.percentile(e, 90):.2f} ({ok.sum()} blocs uniformes)')


def valider_etage(patch, nefs, noeuds=NOEUDS):
    """JPEG d'un boîtier flashé avec `patch` (sonde des secteurs) : rendu simulé avec l'étage neutre, puis avec
    le jeu du patch (celui de la matrice utilisée), nœuds `noeuds`. Renvoie, par NEF, (nom, mode, ΔE neutre, ΔE étage)."""
    from PIL import Image
    b = firmware(patch)
    mats, cs = tables(b)
    jeux = jeux_secteurs(b)
    res = []
    for nef in nefs:
        r = reglages(nef)
        g = GROUPE[r['mode']]
        n = MATRICE_DEFAUT[g]
        cam = camera(nef, tourner=False)
        base = rendre(cam, mats[n], cs[7 * g + CRAN[r['tons']]], SATURATION.get(r['saturation'], 1))
        J = np.asarray(jpeg_boitier(nef).resize((cam.shape[1], cam.shape[0]), Image.BOX), np.float32) / 255
        (e0, e1), ok = ecarts(J, [base, etage(base, jeux[n], noeuds)])
        res.append((pathlib.Path(nef).name, r['mode'], e0, e1))
    return res


def self_test():
    mats, cs = tables(firmware())
    assert all(abs(m.sum(1) - 1).max() < 0.01 for m in mats)
    gris = np.full((2, 2, 3), 0.25, np.float32)
    out = rendre(gris, mats[13], cs[17])
    assert np.ptp(out) < 1e-6, 'un gris doit rester gris'
    assert abs(out[0, 0, 0] - cs[17][1023] / 4095) < 1e-3
    assert all(j == NEUTRE for j in jeux_secteurs(firmware())), 'étage d’usine neutre'
    rng = np.random.default_rng(0)
    img = rng.uniform(.1, .9, (8, 8, 3)).astype(np.float32)
    assert np.abs(rgb(*ycc(img)) - img).max() < 1e-5
    assert np.abs(etage(img, [256] * 16 + [0] * 32 + [256] * 16 + []) - img).max() < 1e-6
    zero = etage(img, [0] * 64)
    assert np.ptp(zero, -1).max() < 1e-5, 'étage à zéro = gris'
    # un gain de Cr seul (t4) au nœud du rouge (secteur 13, 104°) : un pixel exactement à ce nœud prend le gain
    jeu = NEUTRE.copy(); jeu[48 + 13] = 128
    a = np.radians(NOEUDS[13])
    px = rgb(np.float32(.5), np.float32(.1 * np.cos(a)), np.float32(.1 * np.sin(a)))[None]
    y, cb, cr = ycc(etage(px, jeu))
    assert abs(cr[0] - .05 * np.sin(a)) < 1e-4 and abs(cb[0] - .1 * np.cos(a)) < 1e-4
    # écrêtage aux bornes des registres : un coefficient de 1 200 agit comme 1 023, un secteur à 600 comme 511
    m = np.array([[1200, -600, -88], [0, 512, 0], [0, 0, 512]]) / 512
    m_ = np.array([[1023, -600, -88], [0, 512, 0], [0, 0, 512]]) / 512
    assert np.abs(rendre(img * .5, m, cs[17]) - rendre(img * .5, m_, cs[17])).max() < 1e-6
    j1 = NEUTRE.copy(); j1[48 + 13] = 600
    j2 = NEUTRE.copy(); j2[48 + 13] = 511
    assert np.abs(etage(px, j1) - etage(px, j2)).max() < 1e-6
    print('self-test OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['rendu', 'valider', 'valider-etage'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--patch')
    ap.add_argument('--matrice', type=int, default=13)
    ap.add_argument('--courbe', type=int, default=17)
    ap.add_argument('--saturation', type=float, default=1.0)
    ap.add_argument('--recette', help='préréglage recettes/v1/<nom>.json (matrice, courbe, secteurs)')
    ap.add_argument('--balance', type=int, default=1, help='emplacement de balance 0..5 dans la recette')
    ap.add_argument('--noeuds-v0', action='store_true', help='valider-etage avec les nœuds lus avant ajustement')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.action == 'valider':
        return valider(a.args)
    if a.action == 'valider-etage':
        for nom, mode, e0, e1 in valider_etage(a.patch, a.args, NOEUDS_V0 if a.noeuds_v0 else NOEUDS):
            print(f'{nom} {mode} : ΔE2000 médiane étage neutre {np.median(e0):.2f} → étage du patch {np.median(e1):.2f} '
                  f'(90e centile {np.percentile(e0, 90):.2f} → {np.percentile(e1, 90):.2f}, {len(e0)} blocs)')
        return
    from PIL import Image
    if a.recette:
        mat, courbe, jeu = recette(a.recette, a.balance)
        img = rendre(camera(a.args[0], half=False), mat, courbe, 1.0, jeu)
    else:
        b = firmware(a.patch)
        mats, cs = tables(b)
        img = rendre(camera(a.args[0], half=False), mats[a.matrice], cs[a.courbe], a.saturation, jeux_secteurs(b)[a.matrice])
    Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(a.args[1], quality=92)


if __name__ == '__main__':
    sys.exit(main())
