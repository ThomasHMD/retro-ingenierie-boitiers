#!/usr/bin/env python3
"""Décortique une simulation de film Fuji à partir des LUT officielles F-Log2 (fuji-lut/).

Ce qui entre dans la LUT : une scène en lumière linéaire (gamut BT.2020 = F-Gamut), encodée
en F-Log2. Ce qui sort : l'image rendue (BT.709, codée pour l'affichage). On y passe :
  - une rampe de gris de -8 à +6 IL autour du gris 18 % : la courbe de tonalité ;
  - une roue de 36 teintes à luminosité et chroma constantes (Lab) : ce que la simulation
    fait à chaque teinte (décalage de teinte, rapport de chroma) ;
  - la mire ColorChecker (24 patchs) : écart moyen avec la référence neutre de Fuji (WDR-709).
Puis on traduit pour le D40 : une courbe « look » à appliquer sur un rendu neutre (19 points),
et la meilleure matrice 3x3 (ce qu'un mode d'optimisation pourrait porter dans le firmware).

    python3 outils/fuji_lut.py CLASSIC-CHROME [--json sortie.json] [--svg courbe.svg]
"""
import argparse
import json
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent.parent
LUTS = ICI / "fuji-lut"

# F-Log2 (fiche technique Fujifilm ; log_encoding_FLog2(0.18) = 0.3910 dans colour-science)
A, B, C, D, E, F, CUT1 = 5.555556, 0.064829, 0.245281, 0.384316, 8.799461, 0.092864, 0.000889

M_709_VERS_2020 = np.array([[0.6274040, 0.3292820, 0.0433136],
                            [0.0690970, 0.9195400, 0.0113612],
                            [0.0163916, 0.0880132, 0.8955950]])
M_709_VERS_XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                           [0.2126729, 0.7151522, 0.0721750],
                           [0.0193339, 0.1191920, 0.9503041]])
BLANC_D65 = M_709_VERS_XYZ @ np.ones(3)

# ColorChecker Classic, sRGB 8 bits (valeurs usuelles BabelColor, D65)
COLORCHECKER = [(115, 82, 68), (194, 150, 130), (98, 122, 157), (87, 108, 67), (133, 128, 177), (103, 189, 170),
                (214, 126, 44), (80, 91, 166), (193, 90, 99), (94, 60, 108), (157, 188, 64), (224, 163, 46),
                (56, 61, 150), (70, 148, 73), (175, 54, 60), (231, 199, 31), (187, 86, 149), (8, 133, 161),
                (243, 243, 242), (200, 200, 200), (160, 160, 160), (122, 122, 121), (85, 85, 85), (52, 52, 52)]


def flog2(lin):
    lin = np.asarray(lin, dtype=float)
    return np.where(lin >= CUT1, C * np.log10(np.maximum(A * lin + B, 1e-12)) + D, E * lin + F)


def lire_cube(nom):
    chemin = next(LUTS.glob(f"FLog2_to_{nom}_33grid_*.cube"))
    vals, n = [], None
    for ligne in chemin.read_text().splitlines():
        if ligne.startswith("LUT_3D_SIZE"):
            n = int(ligne.split()[1])
        elif ligne and (ligne[0].isdigit() or ligne[0] == "-"):
            vals.append([float(x) for x in ligne.split()])
    # .cube : R varie le plus vite → indices [b][g][r]
    return np.array(vals).reshape(n, n, n, 3)


def appliquer(lut, rgb):
    """Interpolation trilinéaire, rgb dans [0,1], forme (..., 3)."""
    n = lut.shape[0]
    p = np.clip(np.asarray(rgb, dtype=float), 0, 1) * (n - 1)
    i0 = np.minimum(np.floor(p).astype(int), n - 2)
    t = p - i0
    out = 0
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = ((t[..., 0] if dr else 1 - t[..., 0]) * (t[..., 1] if dg else 1 - t[..., 1])
                     * (t[..., 2] if db else 1 - t[..., 2]))
                out = out + w[..., None] * lut[i0[..., 2] + db, i0[..., 1] + dg, i0[..., 0] + dr]
    return out


def rendre(lut, lin709):
    """Scène linéaire BT.709 → valeurs de sortie de la LUT (0-1, codées affichage)."""
    lin2020 = np.asarray(lin709) @ M_709_VERS_2020.T
    return appliquer(lut, flog2(lin2020))


def srgb_vers_lin(v):
    v = np.asarray(v, dtype=float)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def affichage_vers_lab(code):
    """Sortie de LUT (BT.709 affichage, traitée comme sRGB) → Lab D65."""
    xyz = srgb_vers_lin(code) @ M_709_VERS_XYZ.T / BLANC_D65
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_vers_lin709(lab):
    lab = np.asarray(lab, dtype=float)
    fy = (lab[..., 0] + 16) / 116
    fx, fz = fy + lab[..., 1] / 500, fy - lab[..., 2] / 200
    inv = lambda f: np.where(f > 6 / 29, f ** 3, 3 * (6 / 29) ** 2 * (f - 4 / 29))
    xyz = np.stack([inv(fx), inv(fy), inv(fz)], -1) * BLANC_D65
    return xyz @ np.linalg.inv(M_709_VERS_XYZ).T


def analyser(nom):
    lut, neutre, provia = lire_cube(nom), lire_cube("WDR-709"), lire_cube("PROVIA")
    res = {"simulation": nom}

    # 1. Tonalité : rampe de gris
    ev = np.arange(-8, 6.01, 0.5)
    gris = 0.18 * 2.0 ** ev
    g = np.repeat(gris[:, None], 3, 1)
    res["gris"] = [{"IL": float(e), "neutre": round(float(a) * 255, 1), "provia": round(float(b) * 255, 1),
                    "simulation": round(float(c) * 255, 1)}
                   for e, a, b, c in zip(ev, rendre(neutre, g)[:, 1], rendre(provia, g)[:, 1], rendre(lut, g)[:, 1])]

    # 2. Courbe « look » pour le D40 : sortie neutre → sortie simulation, sur la même scène
    fin = 0.18 * 2.0 ** np.linspace(-10, 7, 400)
    gf = np.repeat(fin[:, None], 3, 1)
    x, y = rendre(neutre, gf)[:, 1] * 255, rendre(lut, gf)[:, 1] * 255
    ordre = np.argsort(x)
    x, y = x[ordre], y[ordre]
    xs = np.linspace(0, 255, 19)
    ys = np.interp(xs, x, y, left=0, right=255)
    ys[0], ys[-1] = 0, max(ys[-1], 250)
    res["courbe_d40_19pts"] = [[int(round(a)), int(round(b))] for a, b in zip(xs, ys)]

    # Modèle « D40 » : rendu neutre → courbe appliquée à chaque canal (comme la courbe perso du boîtier)
    courbe = lambda v: np.interp(v * 255, x, y, left=0, right=255) / 255
    courbe_inv = lambda v: np.interp(v * 255, y, x, left=0, right=255) / 255

    # 3. Roue des teintes : Lab L=55, C=35, 36 teintes. On compare la simulation au rendu neutre
    #    passé dans la même courbe : ce qui reste, c'est ce que la courbe seule ne fait pas.
    h = np.radians(np.arange(0, 360, 10))
    lab_in = np.stack([np.full_like(h, 55), 35 * np.cos(h), 35 * np.sin(h)], -1)
    scene = np.clip(lab_vers_lin709(lab_in), 1e-5, None) * 0.18 / 0.2  # ancré près du gris moyen
    def comparer(ref_code, sim_code):
        lr, ls = affichage_vers_lab(ref_code), affichage_vers_lab(sim_code)
        hr = np.degrees(np.arctan2(lr[:, 2], lr[:, 1])) % 360
        hs = np.degrees(np.arctan2(ls[:, 2], ls[:, 1])) % 360
        cr, cs = np.hypot(lr[:, 1], lr[:, 2]), np.hypot(ls[:, 1], ls[:, 2])
        return [{"teinte": round(float(a)), "decalage": round(float((b - a + 180) % 360 - 180), 1),
                 "chroma_x": round(float(d / c), 2), "dL": round(float(f - e), 1)}
                for a, b, c, d, e, f in zip(hr, hs, cr, cs, lr[:, 0], ls[:, 0])]
    rs_roue = rendre(lut, scene)
    res["teintes_vs_neutre_plus_courbe"] = comparer(courbe(rendre(neutre, scene)), rs_roue)
    res["teintes_vs_provia"] = comparer(rendre(provia, scene), rs_roue)

    # 4. Mire : neutre + courbe, puis meilleure matrice 3x3 appliquée AVANT la courbe (en linéaire),
    #    comme une matrice de mode couleur du boîtier.
    mire = srgb_vers_lin(np.array(COLORCHECKER) / 255)
    rn, rs = rendre(neutre, mire), rendre(lut, mire)
    ls_ = affichage_vers_lab(rs)
    de = lambda code: round(float(np.mean(np.linalg.norm(affichage_vers_lab(code) - ls_, axis=1))), 1)
    res["mire_deltaE"] = {"neutre": de(rn), "neutre_plus_courbe": de(courbe(rn))}
    cible = srgb_vers_lin(courbe_inv(rs))           # ce qu'il faudrait avant la courbe
    source = srgb_vers_lin(rn)
    M, *_ = np.linalg.lstsq(source, cible, rcond=None)
    avec_m = courbe(np.clip(np.clip(source @ M, 0, 1) ** (1 / 2.4), 0, 1))  # retour en codé, approx.
    res["mire_deltaE"]["matrice_puis_courbe"] = de(avec_m)
    res["matrice_avant_courbe"] = np.round(M.T, 4).tolist()
    # saturation équivalente : partie « tout sauf la luminance » de la matrice
    lum = np.array([0.2126, 0.7152, 0.0722])
    s = float(np.trace(M.T - np.outer(np.ones(3), lum) * np.trace(M.T) / 3) / 2)
    res["saturation_equivalente"] = round(s / (np.trace(M.T) / 3), 2)
    return res


def svg_courbe(res, chemin):
    pts = res["gris"]
    def poly(cle, couleur):
        c = " ".join(f"{40 + (p['IL'] + 8) * 30:.1f},{300 - p[cle]:.1f}" for p in pts)
        return f'<polyline fill="none" stroke="{couleur}" stroke-width="2" points="{c}"/>'
    lignes = [f'<line x1="40" y1="{300 - v}" x2="460" y2="{300 - v}" stroke="#ddd"/>' for v in (0, 64, 128, 192, 255)]
    lignes += [f'<line x1="{40 + (e + 8) * 30}" y1="45" x2="{40 + (e + 8) * 30}" y2="300" stroke="#eee"/>' for e in range(-8, 7, 2)]
    corps = "".join(lignes) + poly("neutre", "#999") + poly("provia", "#2a6fdb") + poly("simulation", "#c0392b")
    leg = ('<text x="50" y="30" font-size="13" font-family="sans-serif">gris : neutre Fuji (gris), Provia (bleu), '
           f'{res["simulation"]} (rouge), de -8 à +6 IL</text>')
    chemin.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320" style="background:#fff">{leg}{corps}</svg>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("simulation", help="CLASSIC-CHROME, ACROS, PROVIA, Velvia, ASTIA, CLASSIC-Neg., ...")
    ap.add_argument("--json")
    ap.add_argument("--svg")
    a = ap.parse_args()
    res = analyser(a.simulation)
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    if a.svg:
        svg_courbe(res, Path(a.svg))
    print(f"== {res['simulation']}")
    print("IL     neutre  provia  simulation")
    for p in res["gris"][::2]:
        print(f"{p['IL']:+5.1f}  {p['neutre']:6.1f}  {p['provia']:6.1f}  {p['simulation']:6.1f}")
    print("teintes : teinte de réf., décalage °, chroma ×, écart de L | réf. = neutre + courbe ; réf. = Provia")
    for a, b in list(zip(res["teintes_vs_neutre_plus_courbe"], res["teintes_vs_provia"]))[::3]:
        print(f"  {a['teinte']:4d}°  {a['decalage']:+6.1f}°  ×{a['chroma_x']:.2f}  {a['dL']:+5.1f}   |"
              f"  {b['teinte']:4d}°  {b['decalage']:+6.1f}°  ×{b['chroma_x']:.2f}  {b['dL']:+5.1f}")
    print("courbe D40 (19 points, rendu neutre → simulation) :", res["courbe_d40_19pts"])
    print("mire, ΔE moyen jusqu'à la simulation :", res["mire_deltaE"])
    print("matrice avant courbe :", res["matrice_avant_courbe"], "saturation équivalente ×", res["saturation_equivalente"])


if __name__ == "__main__":
    main()
