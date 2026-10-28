#!/usr/bin/env python3
"""Cibles des neuf Picture Control du D750, comme fonctions de la scène.

Entrée commune : XYZ de la scène (D65, blanc équilibré par la balance des blancs de la vue), à l'échelle d'exposition
du posemètre du D750 : Y = 0,18 pour un gris moyen exposé comme la mire d'Imaging Resource (voir d750_analyse.py,
`echelle_scene`). Sortie : CIELAB D65 de l'image rendue (affichage sRGB).

- CLASSIC-CHROME, CLASSIC-Neg. : LUT officielles F-Log2 de Fujifilm (fuji-lut/), scène en BT.709 linéaire → BT.2020 →
  F-Log2 → LUT. Gris de 18 % au gris de la LUT (calage F-Log2, vérifié dans fuji_lut.py).
- POSITIVE, HASSELBLAD : modèles matrice + courbe mesurés sur paires RAW + JPEG (recettes/mesures/positive-film.json,
  hncs.json : `code sRGB = T(K · XYZ)`). Leur échelle d'exposition est celle des boîtiers d'origine (GR III, X2D) :
  on la cale pour que le gris de 18 % sorte à 118/255, la convention des recettes V1 du D40 (hypothèse).
- KODACHROME : modèle spectral de kodachrome.py (fiche E-55, Status A d'agx-emulsion à fournir en argument).
  La réflectance de chaque couleur est reconstruite depuis son RVB linéaire par les trois spectres de base de
  Mallett et Yuksel (2019) ; une couleur hors du gamut sRGB est ramenée au bord (limite nommée dans le rapport).
  Calage du posemètre (gris 18 % à log H = log10(q·K/S)) : diapositive dense, comme la v0.
- TRI-X, HP5, FP4 : mélange de canaux (sRGB linéaire) et courbe ; voir `cible_nb`.
"""
import json
import pathlib
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import d750_modele as dm  # noqa: E402

RACINE = ICI.parent
M_XYZ_709 = np.linalg.inv(dm.M709)


def _lab_affichage(code):
    return dm.code_lab(np.clip(code, 0, 1))


# --- Fujifilm -----------------------------------------------------------------------------------------------
def fuji(nom):
    import fuji_lut as fl
    lut = fl.lire_cube(nom)
    return lambda xyz: _lab_affichage(fl.rendre(lut, np.clip(np.asarray(xyz) @ M_XYZ_709.T, 0, None)))


# --- rendus mesurés (rendus.py) ----------------------------------------------------------------------------
def rendu_mesure(fichier, gris=118 / 255):
    m = json.loads((RACINE / 'recettes' / 'mesures' / fichier).read_text(encoding='utf-8'))
    K = np.array(m['K_XYZ_vers_lineaire'])
    T = np.array(m['courbe'])
    v = np.linspace(0, 1, len(T))
    g = m['gain_blanc']
    f = lambda lin: np.interp(lin / g, v, T)
    # exposition : gris de 18 % → `gris` (moyenne des trois canaux)
    from scipy.optimize import brentq
    blanc = dm.M709.sum(1)
    e = brentq(lambda e: f(e * K @ (0.18 * blanc)).mean() - gris, 1e-3, 1e3)
    return lambda xyz: _lab_affichage(f(e * np.asarray(xyz) @ K.T)), {'gain_exposition': e}


# --- Kodachrome --------------------------------------------------------------------------------------------
def kodachrome(status_a, film='kodachrome_64'):
    import colour
    import kodachrome as k
    km = k.charger(film, status_a)
    a = k.analytiques(km)
    base = colour.recovery.MSDS_BASIS_FUNCTIONS_sRGB_MALLETT2019.copy().align(colour.SpectralShape(400, 700, 5)).values
    # blanc de la scène (D55 adapté D65) : le RVB (1, 1, 1) des bases redonne la réflectance 1, à 1 % près

    def f(xyz):
        rgb = np.clip(np.asarray(xyz, float) @ M_XYZ_709.T, 0, None)
        R = rgb @ base.T
        return k.lab(k.rendu(km, a, R)[0])
    return f


# --- noir et blanc ----------------------------------------------------------------------------------------
MELANGES = {   # sRGB linéaire, somme 1 (perspectives-d200-xt4-d750.md §3.3, fp4-cibles.json)
    'preset_trix': [0.284, 0.521, 0.194],
    'trix_fiche': [0.167, 0.312, 0.521],
    'hp5_fiche': [0.097, 0.236, 0.667],
    'fp4_fiche': [0.122, 0.272, 0.606],
}


def courbe_trix_preset():
    """Courbe Tri-X des recettes V1 (preset Tri-X vérifié sur les exports de Thomas) : entrée = signal linéaire
    du D40 où la courbe IIIa Normal rend le gris à 118/255. Renvoie Y scène (gris = 0,18) → code."""
    tx = np.array(json.loads((RACINE / 'recettes' / 'v1' / 'tri-x.json').read_text(encoding='utf-8'))['courbe']) / 4095
    nk = np.array(json.loads((RACINE / 'recettes' / 'v1' / 'nikon.json').read_text(encoding='utf-8'))['courbe']) / 4095
    v = np.linspace(0, 1, 4096)
    v_gris = float(np.interp(118 / 255, nk, v))
    return lambda Y: np.interp(np.asarray(Y) / 0.18 * v_gris, v, tx)


def courbe_film(film):
    """Courbe film + tirage (films_nb.cible_tonale) : Y scène (gris = 0,18 → 118/255) → code."""
    import films_nb as fn
    fn.fiches_exactes()
    t = fn.cible_tonale(film)
    il = np.array(t['par_IL'])
    return lambda Y: np.interp(np.log2(np.maximum(np.asarray(Y), 1e-6) / 0.18), il[:, 0], il[:, 1] / 255)


def cible_nb(melange, T):
    w = np.asarray(MELANGES[melange] if isinstance(melange, str) else melange, float)

    def f(xyz):
        Y = np.clip(np.asarray(xyz) @ M_XYZ_709.T, 0, None) @ w
        c = T(Y)
        return _lab_affichage(np.repeat(np.asarray(c)[..., None], 3, -1))
    return f


def paires(chemin):
    """Rendu mesuré sur paires NEF + export (d750_analyse.py cible-paires), ex. le preset Portra. Si le rendu a été
    ajusté avec un Look, son .xmp est cherché dans le dossier de la variable d'environnement D750_LOOKS (il n'est pas
    dans le dépôt : usage personnel)."""
    import os
    m = json.loads(pathlib.Path(chemin).read_text(encoding='utf-8'))
    K = np.array(m['K'])
    if m.get('look'):
        d = os.environ.get('D750_LOOKS')
        if not d or not (pathlib.Path(d) / m['look']).exists():
            raise FileNotFoundError(f"profil {m['look']} introuvable : D750_LOOKS doit pointer vers son dossier")
        table = table_look(pathlib.Path(d) / m['look'])
        return lambda xyz: _lab_affichage(appliquer_look(table, dm.courbe(np.array(m['courbe']), np.asarray(xyz) @ K.T)))
    return lambda xyz: _lab_affichage(dm.etage(np.array(m['etage']), dm.courbe(np.array(m['courbe']), np.asarray(xyz) @ K.T)))


PORTRA = RACINE / 'recherche' / 'donnees-films' / 'd750-seances' / 'portra-preset.json'

# Adobe RGB (1998), D65
M_ARGB_XYZ = np.array([[0.5767309, 0.1855540, 0.1881852], [0.2973769, 0.6273491, 0.0752741], [0.0270343, 0.0706872, 0.9911085]])


def table_look(xmp):
    """Table RVB d'un profil Look (films_nb.lire_look), dans l'ordre de fuji_lut.appliquer ; Adobe RGB gamma 2,2 exigé."""
    import films_nb as fn
    t = fn.lire_look(xmp)
    if (t['primaires'], t['gamma']) != (1, 3):
        raise ValueError(f"table attendue en Adobe RGB gamma 2,2 (primaires {t['primaires']}, gamma {t['gamma']})")
    return t['lut'].transpose(2, 1, 0, 3)


def appliquer_look(table, code_argb):
    """Codes Adobe RGB gamma 2,2 → table → codes sRGB d'affichage."""
    import fuji_lut as fl
    lin = fl.appliquer(table, np.clip(code_argb, 0, 1)) ** 2.2
    return dm.oetf(lin @ M_ARGB_XYZ.T @ M_XYZ_709.T)


def look_preset(xmp, courbe_base, gris=None):
    """Profil Look de Lightroom (table RVB 3D, ex. le preset Portra) appliqué à une base neutre : scène (XYZ D65) →
    Adobe RGB linéaire → courbe de base sur chaque canal → codage gamma 2,2 → table → affichage.
    La table est lue par films_nb.lire_look (rien n'en est recopié). La base que Lightroom met sous un Look (profil de
    l'appareil et sa courbe) n'est pas connue ici : `courbe_base` (Y → code sRGB) la remplace (hypothèse)."""
    import films_nb as fn
    import fuji_lut as fl
    t = fn.lire_look(xmp)
    if (t['primaires'], t['gamma']) != (1, 3):
        raise ValueError(f"table attendue en Adobe RGB gamma 2,2 (primaires {t['primaires']}, gamma {t['gamma']})")
    lut = t['lut'].transpose(2, 1, 0, 3)   # [r][g][b] → [b][g][r] (ordre de fuji_lut.appliquer)

    def f(xyz):
        lin = np.clip(np.asarray(xyz) @ np.linalg.inv(M_ARGB_XYZ).T, 0, None)
        code = dm.eotf(courbe_base(lin)) ** (1 / 2.2)
        out = fl.appliquer(lut, np.clip(code, 0, 1)) ** 2.2
        return dm.xyz_lab(out @ M_ARGB_XYZ.T)
    return f


PORTRA_REGLE = RACINE / 'recherche' / 'donnees-films' / 'd750-seances' / 'portra-preset-regle.json'
TONALITE_SCANS = RACINE / 'recherche' / 'donnees-films' / 'd750-seances' / 'portra-tonalite-scans.json'


def remap_clarte(f, src, dst):
    """Cible f dont la clarté L* est ramenée, centile par centile, de la distribution `src` à `dst` (a*, b* gardés)."""
    xs, ys = np.r_[0, src, 100], np.r_[0, dst, 100]

    def g(xyz):
        L = f(xyz)
        return np.stack([np.interp(L[..., 0], xs, ys), L[..., 1], L[..., 2]], -1)
    return g


PORTRA_ESPRIT = RACINE / 'recherche' / 'donnees-films' / 'd750-seances' / 'portra-esprit.json'


def melange_film(f, m):
    """« Esprit Portra » (Thomas, octobre 2026) : le rendu f (le preset Portra tel qu'il le règle) tiré vers ses Portra scannées,
    avec le poids m['poids_film'] : clarté ramenée centile par centile (exports → scans) et teinte des tons neutres
    (a*, b* par tranche de clarté, exports → scans) ; les couleurs saturées gardent celles de f."""
    w = m['poids_film']
    xs, ys = np.r_[0, m['src'], 100], np.r_[0, m['dst'], 100]
    centres = np.array(m['tranches_centres'])
    da = np.array(m['teinte_dst'])[:, 0] - np.array(m['teinte_src'])[:, 0]
    db = np.array(m['teinte_dst'])[:, 1] - np.array(m['teinte_src'])[:, 1]

    def g(xyz):
        L = f(xyz)
        Lf = np.interp(L[..., 0], xs, ys)
        neutre = np.exp(-np.hypot(L[..., 1], L[..., 2]) / 12)
        return np.stack([(1 - w) * L[..., 0] + w * Lf,
                         L[..., 1] + w * neutre * np.interp(L[..., 0], centres, da),
                         L[..., 2] + w * neutre * np.interp(L[..., 0], centres, db)], -1)
    return g


def toutes(status_a=None):
    out = {'CLASSIC CHROME': fuji('CLASSIC-CHROME'), 'CLASSIC NEG': fuji('CLASSIC-Neg.'),
           'POSITIVE': rendu_mesure('positive-film.json')[0], 'HASSELBLAD': rendu_mesure('hncs.json')[0]}
    if status_a:
        out['KODACHROME'] = kodachrome(status_a)
    if PORTRA.exists():
        out['PORTRA'] = paires(PORTRA)
        if TONALITE_SCANS.exists():   # option 2 : couleurs du preset Portra, tonalité des scans Portra retouchés de Thomas
            t = json.loads(TONALITE_SCANS.read_text(encoding='utf-8'))
            out['PORTRA SCANS'] = remap_clarte(out['PORTRA'], t['src'], t['dst'])
    if PORTRA_REGLE.exists():   # option 1 : le preset Portra avec les réglages habituels de Thomas, mesuré sur paires
        out['PORTRA REGLE'] = paires(PORTRA_REGLE)
        if PORTRA_ESPRIT.exists():
            out['PORTRA ESPRIT'] = melange_film(out['PORTRA REGLE'], json.loads(PORTRA_ESPRIT.read_text(encoding='utf-8')))
    import os
    spk = os.environ.get('D750_SPEKTRAFILM')   # tables d750_spektrafilm.py, hors du dépôt (usage personnel)
    if spk and (pathlib.Path(spk) / 'kodak_kodachrome_64.npz').exists():
        import d750_spektrafilm as sp
        t = pathlib.Path(spk) / 'kodak_kodachrome_64.npz'
        out['KODACHROME SPK'] = sp.cible(t)
        out['KODACHROME VIF'] = sp.cible(t, chroma=1.2)   # choix de goût : +20 % de chroma, rien de mesuré
        t = pathlib.Path(spk) / 'kodak_kodachrome_64_ev-0.5.npz'   # sous-exposée d'1/2 IL, pratique courante en diapo
        if t.exists():
            out['KODACHROME DENSE'] = sp.cible(t)
    return out
