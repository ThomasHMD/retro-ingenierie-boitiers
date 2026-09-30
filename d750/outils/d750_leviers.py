#!/usr/bin/env python3
"""Leviers de réglage du D750 (sans firmware) chiffrés contre une cible couleur : le Kodachrome du modèle spectral
(kodachrome.py) ou une simulation Fujifilm par sa LUT officielle (fuji-lut/). Pour chaque cible :
  1. la courbe neutre de la cible seule (appliquée sur la luminance, ou sur chaque canal R, V, B : le D750 fait
     l'un ou l'autre, à mesurer) ;
  2. + saturation et teinte globales (curseurs du Picture Control ; teinte modélisée en rotation CIELAB : hypothèse) ;
  3. + décalage de balance des blancs (gains R et B du capteur, avant la matrice du boîtier), converti en crans de
     réglage fin du D750 (A-B : 1 cran ≈ 5 mired ; G-M : 1 cran ≈ 0,05 de densité ; manuel D750 p. 149-151).
Capteur : sensibilités de Nikon voisins (D3X, D700, D5100, base camspec, Jiang et al. 2013), faute de données
publiées du D750 ; matrice du boîtier approchée par l'ajustement de matrices_spectrales.ajuster (D65).
600 spectres lisses + ColorChecker, gris à 18 %. Sortie : ΔE2000 médian et 90e centile contre la cible.

  d750_leviers.py <cible> <camspec_database.txt> <status_A/>   cible : kodachrome_64 (25, 200), CLASSIC-CHROME, ...
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import colour  # noqa: E402
import kodachrome as k  # noqa: E402
import matrices_spectrales as ms  # noqa: E402
import fuji_lut as fl  # noqa: E402
from scipy.optimize import minimize  # noqa: E402

CIBLE, CAMSPEC, STATUS_A = sys.argv[1:4]
forme = colour.SpectralShape(400, 700, 5)
R, noms = k.reflectances_test()
Rt = np.clip(R * 0.18 / R[noms.index('neutral 5 (.70 D)')].mean(), 0, 1)
il_f = np.arange(-9, 5.001, 0.05)
gris = np.repeat((0.18 * 2.0 ** il_f)[:, None], len(k.L), 1)
D65w = colour.xy_to_XYZ(colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65'])
cmf = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer'].copy().align(forme).values

if CIBLE.startswith('kodachrome'):
    m = k.charger(CIBLE, STATUS_A)
    a = k.analytiques(m)
    lf = k.lab(k.rendu(m, a, Rt)[0])
    Yf = k.rendu(m, a, gris)[0][:, 1]
    E = m['D55']
else:
    lut = fl.lire_cube(CIBLE)
    E = colour.SDS_ILLUMINANTS['D65'].copy().align(forme).values
    def scene709(Rx):
        xyz = (Rx * E) @ cmf / (E @ cmf[:, 1])
        return xyz @ np.linalg.inv(fl.M_709_VERS_XYZ).T
    lf = fl.affichage_vers_lab(fl.rendre(lut, scene709(Rt)))
    code_g = fl.rendre(lut, scene709(gris))
    Yf = (fl.srgb_vers_lin(code_g) @ fl.M_709_VERS_XYZ.T)[:, 1] / D65w[1]
courbeY = lambda y: np.interp(np.log2(np.maximum(y, 1e-6) / 0.18), il_f, Yf)
M_srgb = colour.RGB_COLOURSPACES['sRGB'].matrix_XYZ_to_RGB
M_xyz = colour.RGB_COLOURSPACES['sRGB'].matrix_RGB_to_XYZ


def crans(sens, gR, gB):
    """Équivalent du décalage de gains en réglage fin A-B (mired) et G-M (densité CC), autour de l'éclairage E."""
    rep = lambda S_: (S_ @ sens.T)
    r0 = rep(E)
    best = None
    for dm in np.arange(-200, 201, 1.0):
        cct = 1e6 / (1e6 / 5500 + dm)
        try:
            Sx = colour.sd_CIE_illuminant_D_series(colour.temperature.CCT_to_xy_CIE_D(cct)).copy().align(forme).values
        except Exception:
            continue
        rx = rep(Sx) / rep(colour.sd_CIE_illuminant_D_series(colour.temperature.CCT_to_xy_CIE_D(5500)).copy().align(forme).values)
        # régler la WB sur un éclairage plus chaud que la lumière (mired +) : gains = 1/rx relatifs
        g = (1 / rx) / (1 / rx)[1]
        e = (np.log(g[0] / g[2]) - np.log(gR / gB)) ** 2
        if best is None or e < best[0]:
            best = (e, dm, g)
    dm, g = best[1], best[2]
    resid_G = np.sqrt(gR * gB) / np.sqrt(g[0] * g[2])  # >1 : moins de vert relatif (magenta)
    return {'mired_reglage_WB': round(float(dm), 0), 'crans_A_B': round(float(dm / 5), 1),
            'crans_G_M': round(float(np.log10(resid_G) / 0.05), 1)}


res = {'cible': CIBLE}
for cam in ('Nikon D3X', 'Nikon D700', 'Nikon D5100'):
    sens10 = ms.lire_camspec(CAMSPEC, cam)
    sens = np.stack([np.interp(k.L, np.arange(400, 721, 10), s) for s in sens10])
    rgb, xyz, _ = ms.donnees(sens10, 'D65')
    M = ms.ajuster(rgb, xyz)
    cam_rgb = (Rt * E) @ sens.T / (E @ sens.T)

    def sortie(p, mode):
        lr, lb, kc, rot = p
        XYZ = (cam_rgb * np.array([np.exp(lr), 1.0, np.exp(lb)])) @ M.T
        if mode == 'luminance':
            Y = np.maximum(XYZ[:, 1], 1e-6)
            XYZ = XYZ * (courbeY(Y) / Y)[:, None]
        else:
            XYZ = courbeY(np.clip(XYZ @ M_srgb.T, 1e-6, None)) @ M_xyz.T
        L = k.lab(XYZ)
        C, h = np.hypot(L[:, 1], L[:, 2]) * kc, np.arctan2(L[:, 2], L[:, 1]) + np.radians(rot)
        return np.stack([L[:, 0], C * np.cos(h), C * np.sin(h)], 1)

    out = {}
    for mode in ('luminance', 'canaux'):
        de = lambda p: np.median(k._de(sortie(p, mode), lf))
        st = lambda p: {'mediane': round(float(de(p)), 2), 'p90': round(float(np.percentile(k._de(sortie(p, mode), lf), 90)), 2)}
        r1 = minimize(lambda q: de([0, 0, *q]), [1.0, 0.0], method='Nelder-Mead', options={'initial_simplex': [[1.0, 0.0], [0.8, 0.0], [1.0, 5.0]]})
        best = None
        for lr in np.arange(-0.4, 0.41, 0.1):
            for lb in np.arange(-0.4, 0.41, 0.1):
                r = minimize(lambda q: de([lr, lb, *q]), r1.x, method='Nelder-Mead', options={'initial_simplex': [r1.x, r1.x + [0.1, 0], r1.x + [0, 5]], 'maxiter': 200})
                if best is None or r.fun < best[0]:
                    best = (r.fun, [lr, lb, *r.x])
        x0 = best[1]
        r2 = minimize(de, x0, method='Nelder-Mead', options={'initial_simplex': [x0] + [np.add(x0, d) for d in ([0.05, 0, 0, 0], [0, 0.05, 0, 0], [0, 0, 0.05, 0], [0, 0, 0, 3])], 'maxiter': 2000})
        gR, gB = float(np.exp(r2.x[0])), float(np.exp(r2.x[1]))
        out[mode] = {'courbe_seule': st([0, 0, 1, 0]),
                     'courbe_sat_teinte': {**st([0, 0, *r1.x]), 'sat': round(float(r1.x[0]), 2), 'teinte': round(float(r1.x[1]), 1)},
                     'plus_WB': {**st(r2.x), 'gain_R': round(gR, 3), 'gain_B': round(gB, 3), 'sat': round(float(r2.x[2]), 2),
                                 'teinte': round(float(r2.x[3]), 1), **crans(sens, gR, gB)}}
    res[cam] = out
print(json.dumps(res, ensure_ascii=False))
