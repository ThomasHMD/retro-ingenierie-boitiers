#!/usr/bin/env python3
"""Modèle du traitement JPEG du D750, mesuré sur les séances de calibration (blocs de d750_blocs.py).

Entrée du modèle : x = RVB du capteur, noir soustrait, en fraction de la pleine échelle, balance des blancs de la vue
appliquée (vert = 1). Sortie : code sRGB 0..1 du JPEG. Briques, toutes ajustées par moindres carrés robustes en CIELAB :
- vignetage corrigé par le boîtier (contrôle du vignetage) : gain radial V(r) = 1 + a r² + b r⁴ sur x ;
- matrice 3 × 3 M (lignes de somme 1 : un neutre reste neutre) ;
- courbe T, croissante, la même sur R, V, B (une courbe sur la luminance seule fait nettement moins bien, rapport §2.1) ;
- étage chroma dans le plan CbCr (BT.601, après la courbe) : gain et rotation qui dépendent de la teinte
  (série de Fourier d'ordre 2), comme l'étage à secteurs du D40.

Fonctions utilisées par d750_analyse.py ; aucun accès au boîtier.
"""
import numpy as np

# --- couleur -------------------------------------------------------------------------------------------------
M709 = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
BLANC = M709.sum(1)


def eotf(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((np.clip(c, 0, None) + 0.055) / 1.055) ** 2.4)


def oetf(v):
    v = np.asarray(v, float)
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.clip(v, 0, None) ** (1 / 2.4) - 0.055)


def xyz_lab(xyz):
    t = np.asarray(xyz, float) / BLANC
    f = np.where(t > 216 / 24389, np.cbrt(np.clip(t, 0, None)), (24389 / 27 * t + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_xyz(lab):
    lab = np.asarray(lab, float)
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], -1)
    t = np.where(f > 6 / 29, f ** 3, (116 * f - 16) / (24389 / 27))
    return t * BLANC


def code_lab(code):
    """Code sRGB (0..1) → CIELAB D65."""
    return xyz_lab(eotf(code) @ M709.T)


def lab_code(lab):
    return oetf(lab_xyz(lab) @ np.linalg.inv(M709).T)


def de2000(a, b):
    import colour
    return colour.delta_E(a, b, method='CIE 2000')


def stats(e):
    e = np.asarray(e)
    return {'mediane': round(float(np.median(e)), 2), 'p90': round(float(np.percentile(e, 90)), 2)}


# --- YCbCr (BT.601, sur les codes) ---------------------------------------------------------------------------
YCC = np.array([[0.299, 0.587, 0.114], [-0.168736, -0.331264, 0.5], [0.5, -0.418688, -0.081312]])
YCC_INV = np.linalg.inv(YCC)


# --- courbe croissante --------------------------------------------------------------------------------------
NOEUDS = np.geomspace(2e-4, 2.5, 28)


def courbe_valeurs(p):
    """28 paramètres libres → valeurs croissantes aux nœuds (la première fixée par p[0])."""
    return np.cumsum(np.exp(p))


def courbe(p, x):
    y = courbe_valeurs(p)
    lx = np.log(np.clip(x, 1e-6, None))
    ln = np.log(NOEUDS)
    out = np.interp(lx, ln, y)
    # sous le premier nœud : droite vers 0 en linéaire
    bas = x < NOEUDS[0]
    return np.where(bas, y[0] * np.clip(x, 0, None) / NOEUDS[0], out)


def courbe_init(T=None):
    """Paramètres de départ : la courbe sRGB (ou une fonction T donnée), aux nœuds."""
    y = oetf(np.clip(NOEUDS * 2.5, 0, 1)) if T is None else T(NOEUDS)
    y = np.maximum.accumulate(np.maximum(y, 1e-4))
    d = np.diff(np.r_[0, y])
    return np.log(np.maximum(d, 1e-5))


# --- étage chroma -------------------------------------------------------------------------------------------
ORDRE = 2


def etage(q, code):
    """q = [gain0, cos1, sin1, cos2, sin2 (gain), rot0, cos1, sin1, cos2, sin2 (rotation, rad)] ; agit sur CbCr."""
    ycc = code @ YCC.T
    h = np.arctan2(ycc[..., 2], ycc[..., 1])
    base = lambda c: c[0] + sum(c[2 * k - 1] * np.cos(k * h) + c[2 * k] * np.sin(k * h) for k in range(1, ORDRE + 1))
    n = 2 * ORDRE + 1
    g = np.exp(base(q[:n]))
    r = base(q[n:2 * n])
    cb, cr = ycc[..., 1], ycc[..., 2]
    c, s = np.cos(r), np.sin(r)
    ycc = np.stack([ycc[..., 0], g * (c * cb - s * cr), g * (s * cb + c * cr)], -1)
    return ycc @ YCC_INV.T


ETAGE_NEUTRE = np.zeros(2 * (2 * ORDRE + 1))


# --- matrice à lignes de somme 1 --------------------------------------------------------------------------
def matrice(m6):
    """6 paramètres hors diagonale → 3 × 3, lignes de somme 1."""
    M = np.zeros((3, 3))
    M[0, 1], M[0, 2], M[1, 0], M[1, 2], M[2, 0], M[2, 1] = m6
    M[np.diag_indices(3)] = 1 - M.sum(1)
    return M


def vignetage(v, r):
    return 1 + v[0] * r ** 2 + v[1] * r ** 4
