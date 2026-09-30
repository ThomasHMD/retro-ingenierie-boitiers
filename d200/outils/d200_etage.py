#!/usr/bin/env python3
"""Étage à 16 secteurs du D200 : lecture sur une roue de teintes photographiée (d200/images/2026-10-roue-teintes/).

Pour une vue NEF + JPEG prise avec un rendu des préréglages (emplacement de d200_preglages.rendus, matrice F = 1),
le simulateur donne (Cb, Cr) avant l'étage ; le JPEG du boîtier donne (Cb, Cr) après. Par tranche de teinte
θ = atan2(Cr, Cb) du simulé : gain (module du rapport médian) et rotation (son argument). Seules les zones
uniformes et non écrêtées comptent (fenêtre 5 × 5, écart-type < 0,02, chroma simulée > 8).

  d200_etage.py profil <nef> <rendu> [--temoin <nef> <rendu>]   gain et rotation par tranche de 5,625°
  d200_etage.py carte <nef> <rendu> [--temoin <nef> <rendu>]    sonde n° 2 (rampe 64 + 12 s) : numéro du secteur par tranche
  d200_etage.py --self-test

<rendu> : chrome, positive (emplacements couleur). Le témoin (même roue, secteurs neutres) sert de plancher :
le gain de la sonde est divisé par celui du témoin à la même teinte.

Modèle de l'étage (sondes n° 1 à 3 d’octobre 2026, d200/recherche/d200-preglages.md §7) : la matrice du secteur s,
[b1 b2 ; b3 b4] / 256, s'applique à (Cb, Cr) ; 16 nœuds tous les 22,5° de θ = atan2(Cr, Cb), interpolation linéaire
entre deux nœuds voisins. Nœud k (à 22,5° k) → secteur NOEUDS[k] : les axes −Cb, +Cb, −Cr, +Cr portent les secteurs
0, 4, 8, 12 ; dans chaque quadrant, groupe g = 2·(Cr > 0) + (Cb > 0), secteurs 4g + 1 à 4g + 3 de l'axe Cb vers l'axe Cr.
"""
import argparse
import pathlib
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI.parent.parent / 'd40' / 'outils'))
import d200_simulateur as sim  # noqa: E402

PAS = 5.625
NOEUDS = [4, 13, 14, 15, 12, 11, 10, 9, 0, 1, 2, 3, 8, 7, 6, 5]   # secteur du nœud k, à 22,5° k


def appliquer(C, secteurs):
    """(Cb, Cr) de forme (n, 2) → après l'étage ; secteurs = 4 blocs de 16 valeurs (b1, b2, b3, b4), /256."""
    C = np.asarray(C, float)
    A = np.stack([np.asarray(b, float) for b in secteurs], -1).reshape(16, 2, 2) / 256
    h = np.degrees(np.arctan2(C[:, 1], C[:, 0])) % 360 / 22.5
    k = np.floor(h).astype(int) % 16
    f = (h - np.floor(h))[:, None, None]
    n = np.array(NOEUDS)
    M = A[n[k]] * (1 - f) + A[n[(k + 1) % 16]] * f
    return np.einsum('nij,nj->ni', M, C)


def ycc_jpeg(J):
    r, g, b = (J * 255).transpose(2, 0, 1)
    return np.stack([.299 * r + .587 * g + .114 * b, -.168736 * r - .331264 * g + .5 * b,
                     .5 * r - .418688 * g - .081312 * b], -1)


def preparer(nef, rendu, emplacements=None):
    """(Cb, Cr) simulés avant l'étage et (Cb, Cr) du JPEG, sur les zones uniformes et non écrêtées."""
    import d200_preglages as P
    from scipy.ndimage import uniform_filter
    if emplacements is None:
        emplacements = dict(zip([p[0] for p in P.PREGLAGES], P.rendus(sim.firmware())))
    d = emplacements[rendu]
    cam_plein = sim.camera(nef)
    cam, J = sim.reduire(cam_plein, 3), sim.reduire(sim.jpeg_aligne(nef, cam_plein), 3)
    lut = np.array(d['courbe'], np.uint8)
    lin = np.clip(cam @ (np.array(d['matrices'][1]).reshape(3, 3) / 512).T, 0, 1)
    ys = lut[(lin * 4095).astype(np.int32)].astype(np.float32) @ (np.array(d['ycc']).reshape(3, 3) / 256).T
    yj = ycc_jpeg(J)
    m1, m2 = uniform_filter(J, (5, 5, 1)), uniform_filter(J * J, (5, 5, 1))
    ok = ((np.sqrt(np.clip(m2 - m1 * m1, 0, None)).max(-1) < .02) & (J.max(-1) < .995) & (J.min(-1) > .005)
          & (np.hypot(ys[..., 1], ys[..., 2]) > 8))
    return ys[ok][:, 1:], yj[ok][:, 1:]


def profil(S, J, pas=PAS, mini=60):
    """[(teinte de début, gain, rotation en degrés, pixels)] ; nan si moins de `mini` pixels."""
    zs, zj = S[:, 0] + 1j * S[:, 1], J[:, 0] + 1j * J[:, 1]
    h = np.degrees(np.angle(zs)) % 360
    out = []
    for a in np.arange(0, 360, pas):
        m = (h >= a) & (h < a + pas)
        q = np.median(zj[m] / zs[m]) if m.sum() >= mini else np.nan
        out.append((a, abs(q), np.degrees(np.angle(q)), int(m.sum())))
    return out


def lire(args):
    S, J = preparer(args.nef, args.rendu)
    p = profil(S, J)
    t = profil(*preparer(args.temoin[0], args.temoin[1])) if args.temoin else None
    return p, t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('commande', nargs='?', choices=['profil', 'carte'])
    ap.add_argument('nef', nargs='?')
    ap.add_argument('rendu', nargs='?', choices=['chrome', 'positive'])
    ap.add_argument('--temoin', nargs=2, metavar=('NEF', 'RENDU'))
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        S = np.array([[10., 0], [0, 10], [-10, 0], [0, -10]] * 40)
        p = profil(S, S * .5, pas=90, mini=1)
        assert all(abs(g - .5) < 1e-9 and abs(r) < 1e-9 for _, g, r, _ in p), p
        neutre = [[256] * 16, [0] * 16, [0] * 16, [256] * 16]
        assert np.allclose(appliquer(S, neutre), S)
        gris = [[256] * 16, [0] * 16, [0] * 16, [256] * 16]
        gris[0][0] = gris[3][0] = 0                                   # secteur 0 = axe −Cb (180°)
        out = appliquer([[-10., 0], [10, 0], [-10, -.0001]], gris)
        assert np.allclose(out[0], 0) and np.allclose(out[1], [10, 0]) and abs(out[2][0]) < 1e-3, out
        assert sorted(NOEUDS) == list(range(16))
        print('self-test OK')
        return
    if not (a.commande and a.nef and a.rendu):
        ap.error('commande, NEF et rendu requis')
    p, t = lire(a)
    print(f'{"teinte":>8}  {"gain":>5} {"rot":>6}  {"n":>6}' + ('   témoin gain   rot' if t else '')
          + ('   gain/témoin  secteur' if a.commande == 'carte' else ''))
    for k, (h, g, r, n) in enumerate(p):
        ligne = f'{h:7.2f}°  {g:5.2f} {r:+6.1f}° {n:6d}'
        gt = 1.
        if t:
            _, gt, rt, _ = t[k]
            ligne += f'   {gt:11.2f} {rt:+5.1f}°'
        if a.commande == 'carte':
            gr = g / gt if t and np.isfinite(gt) else g
            ligne += f'   {gr:11.2f}  {(gr * 256 - 64) / 12:7.1f}'
        print(ligne)


if __name__ == '__main__':
    main()
