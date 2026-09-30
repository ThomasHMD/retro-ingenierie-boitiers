#!/usr/bin/env python3
"""Rendus noir et blanc du D40 (Tri-X 400, HP5 Plus, FP4 Plus) : pondération R, G, B de la matrice (trois lignes
identiques, donc sortie grise) et courbe de tons, d'après les fiches techniques des films et un tirage standard.

Sources (relevées en octobre 2026, courbes numérisées à la main ou au pixel sur les graphiques des fiches) :
- Kodak Professional Tri-X 320 et 400, fiche F-4017 (Kodak Alaris, octobre 2021) : « Spectral Sensitivity
  Curves », courbe D = 1,0 au-dessus du voile (log sensibilité, sensibilité = 1 / exposition en erg/cm²) ;
  « Characteristic Curves, Tri-X 400 / 400TX 35 mm », révélateur T-MAX, 6 min à 20 °C (indice de contraste
  ≈ 0,56, celui que vise la fiche).
  https://kodakprofessional.com/sites/default/files/wysiwyg/film/f4017_trix_320400.pdf
- Ilford HP5 Plus, fiche technique Harman (juin 2010) : « Wedge spectrogram to tungsten light (2850 K) »,
  lu comme une réponse relative linéaire à une source de 2 850 K (on divise par le corps noir à 2 850 K pour
  revenir à une sensibilité par énergie) ; « Characteristic curves », Ilfotec HC 1+31, 6 min 30 à 20 °C.
  https://www.ilfordphoto.com/amfile/file/download/file/1903/product/691/ (copie lue : kennethleegallery.com/pdf/HP5Plus.pdf)
- Ilford FP4 Plus, fiche Ilford d'avril 2004 (graphiques vectoriels, lus dans le PDF par fiches_vectorielles.py,
  données complètes dans recherche/donnees-films/fp4-plus.json ; la fiche Harman de novembre 2018 reprend les mêmes
  graphiques en image) : « Wedge spectrogram to tungsten light (2850K) », même lecture que HP5 ; « Characteristic
  curve », Ilfotec HC 1+31, 8 min à 20 °C. https://125px.com/docs/film/ilford/FP4+-200404.pdf
- Sensibilités spectrales du D40 : base camspec (Jiang et al. 2013), voir matrices_spectrales.py.
- Tirage : papier grade 2, ISO 6846 (étendue d'exposition R 100 à 120 pour le grade 2, ici 1,10 log), Dmin 0,05,
  Dmax 2,10 (papier RC brillant), courbe logistique en log d'exposition ; noir et blanc du papier ramenés à 0 et
  255 (comme un scan de tirage). Exposition du tirage : un gris que la courbe IIIa du D40 rend 118/255 garde ce rendu.

Tri-X, cible du preset acheté (octobre 2026, consigne de Thomas) : profil Look d’un preset Tri-X acheté
(un preset que l’auteur aimait beaucoup ; rien de son contenu brut n'est recopié dans le projet).
Le profil est une table RGB 32³ (format dng_big_table du DNG SDK : base 85 maison, zlib, écarts à l'identité en
uint16), primaires et gamma sRGB, sortie grise. On en tire le mélange de canaux (sRGB linéaire) et sa
diagonale ; la courbe complète (avec la courbe de base de Lightroom) est ajustée sur les exports JPEG de
Thomas développés avec ce profil (paires RAW + JPEG, gain par image), comme les rendus couleur.

  films_nb.py poids <camspec.txt>          pondérations du D40 pour chaque film (D65)
  films_nb.py srgb                         mélange de canaux en sRGB linéaire pour chaque film (D65), constantes
                                           et données lues exactement dans les PDF (« _fiche »)
  films_nb.py tonale                       courbe film + tirage de chaque film et de chaque développement de la
                                           Tri-X 400 35 mm publié (T-MAX, D-76), indépendante du boîtier (JSON)
  films_nb.py look <profil.xmp>            mélange de canaux et diagonale d'un profil Look N&B
  films_nb.py paires <échantillons> <camspec.txt> <profil.xmp> <liste.tsv RAW<tab>JPEG>   Tri-X du preset acheté : ajustement
      sur les exports (blocs uniformes pour le mélange et le ΔE, histogrammes des images entières pour les ombres)
  films_nb.py --self-test
"""
import argparse
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import matrices_spectrales as ms  # noqa: E402

# Tri-X 400 : log10 sensibilité (D = 1,0 au-dessus du voile), F-4017 p. 8
TRIX_SPECTRE = {300: 2.50, 350: 2.70, 370: 2.72, 380: 2.72, 390: 2.72, 400: 2.71, 410: 2.70, 420: 2.68, 430: 2.66,
                440: 2.62, 450: 2.58, 460: 2.53, 470: 2.46, 480: 2.37, 490: 2.29, 500: 2.24, 510: 2.24, 520: 2.28,
                530: 2.33, 540: 2.37, 550: 2.41, 560: 2.44, 570: 2.46, 580: 2.46, 590: 2.42, 600: 2.38, 610: 2.40,
                620: 2.42, 630: 2.34, 640: 1.95, 650: 1.15, 660: 0.40, 670: -3.0}
# HP5 Plus : spectrogramme au tungstène 2 850 K, hauteur relative (fiche Harman p. 1)
HP5_SPECTROGRAMME = {353: 0.0, 367: 0.27, 385: 0.59, 400: 0.71, 422: 0.78, 450: 0.81, 477: 0.81, 503: 0.78, 523: 0.84,
                     550: 0.94, 573: 0.99, 587: 0.96, 601: 0.92, 619: 0.94, 632: 0.92, 638: 0.69, 645: 0.36, 655: 0.0}
# FP4 Plus : spectrogramme au tungstène 2 850 K (fiche Ilford 2004 p. 1, zéro de l'axe pris aux graduations 0,5 et 1,0 ;
# la courbe coupe ce zéro à 367 et 664 nm)
FP4_SPECTROGRAMME = {367: 0.0, 370: 0.062, 380: 0.194, 390: 0.288, 400: 0.392, 410: 0.44, 420: 0.46, 430: 0.509, 440: 0.578,
                     450: 0.641, 460: 0.67, 470: 0.681, 480: 0.68, 490: 0.671, 500: 0.653, 510: 0.647, 520: 0.694, 530: 0.74,
                     540: 0.747, 550: 0.749, 560: 0.794, 570: 0.845, 580: 0.904, 590: 0.949, 600: 0.972, 605: 0.974,
                     610: 0.969, 620: 0.936, 630: 0.935, 635: 0.875, 640: 0.752, 650: 0.467, 660: 0.135, 664: 0.0}
# Courbes caractéristiques : (log H, densité). Tri-X : log lux·s absolu ; HP5, FP4 : log relatif (fiche).
TRIX_CC = [(-3.45, 0.30), (-3.32, 0.31), (-3.08, 0.33), (-2.96, 0.34), (-2.84, 0.37), (-2.71, 0.40), (-2.59, 0.45),
           (-2.47, 0.50), (-2.35, 0.56), (-2.23, 0.62), (-2.10, 0.69), (-1.98, 0.75), (-1.86, 0.82), (-1.74, 0.89),
           (-1.62, 0.96), (-1.49, 1.03), (-1.37, 1.11), (-1.25, 1.19), (-1.13, 1.26), (-1.01, 1.34), (-0.88, 1.41),
           (-0.76, 1.49), (-0.64, 1.56), (-0.52, 1.63), (-0.40, 1.71), (-0.27, 1.77), (-0.15, 1.84), (-0.03, 1.91),
           (0.09, 1.97), (0.21, 2.03), (0.34, 2.09)]
HP5_CC = [(0.03, 0.165), (0.45, 0.165), (0.56, 0.17), (0.66, 0.179), (0.77, 0.192), (0.87, 0.214), (0.98, 0.237),
          (1.09, 0.272), (1.19, 0.308), (1.30, 0.353), (1.40, 0.406), (1.51, 0.469), (1.62, 0.527), (1.72, 0.598),
          (1.83, 0.670), (1.93, 0.741), (2.04, 0.812), (2.14, 0.884), (2.25, 0.951), (2.36, 1.013), (2.46, 1.089),
          (2.57, 1.152), (2.67, 1.223), (2.78, 1.295), (2.89, 1.357), (2.99, 1.429), (3.10, 1.496), (3.20, 1.562),
          (3.31, 1.629), (3.42, 1.696), (3.52, 1.763), (3.63, 1.830), (3.73, 1.897), (3.84, 1.969), (3.95, 2.031),
          (4.05, 2.098)]
FP4_CC = [(0.07, 0.081), (0.8, 0.083), (0.9, 0.09), (1.0, 0.104), (1.1, 0.132), (1.2, 0.169), (1.3, 0.211), (1.4, 0.258),
          (1.5, 0.311), (1.6, 0.368), (1.7, 0.426), (1.8, 0.487), (1.9, 0.551), (2.0, 0.621), (2.1, 0.696), (2.2, 0.773),
          (2.3, 0.852), (2.4, 0.931), (2.5, 1.008), (2.6, 1.087), (2.7, 1.171), (2.8, 1.257), (2.9, 1.342), (3.0, 1.425),
          (3.1, 1.501), (3.2, 1.571), (3.3, 1.636), (3.4, 1.696), (3.5, 1.748), (3.6, 1.792), (3.7, 1.825), (3.8, 1.848),
          (3.9, 1.862), (4.0, 1.868), (4.16, 1.868)]
SPECTROGRAMMES = {'hp5': HP5_SPECTROGRAMME, 'fp4': FP4_SPECTROGRAMME}
SPECTRES_LOG = {'trix': TRIX_SPECTRE}
CC = {'trix': TRIX_CC, 'hp5': HP5_CC, 'fp4': FP4_CC}
DONNEES = pathlib.Path(__file__).resolve().parent.parent / 'recherche' / 'donnees-films'


def pente_moyenne(cc, d=1.5):
    """Pente moyenne entre voile + 0,1 et 1,5 log plus loin (définition du G-barre)."""
    cc = np.array(cc)
    voile = cc[:, 1].min()
    lv = np.interp(voile + 0.1, cc[:, 1], cc[:, 0])
    return (np.interp(lv + d, cc[:, 0], cc[:, 1]) - (voile + 0.1)) / d


def interpoler_pente(cc_a, cc_b, cible):
    """Courbe entre deux temps de développement publiés (même axe log H), à la pente moyenne visée."""
    a, b = np.array(cc_a), np.array(cc_b)
    x = a[:, 0]
    yb = np.interp(x, b[:, 0], b[:, 1])
    from scipy.optimize import brentq
    t = brentq(lambda t: pente_moyenne(np.c_[x, (1 - t) * a[:, 1] + t * yb]) - cible, -0.5, 1.5)
    return [(float(u), float(v)) for u, v in zip(x, (1 - t) * a[:, 1] + t * yb)]


def fiches_exactes():
    """Ajoute les données lues exactement dans les PDF vectoriels (recherche/donnees-films/) : 'trix_fiche' et
    'hp5_fiche' (mêmes conditions que les constantes ci-dessus), et les variantes de développement de la Tri-X 400
    35 mm ('trix_tmax_7', 'trix_d76_8', etc.). Renvoie la liste des noms ajoutés."""
    import json
    t = json.loads((DONNEES / 'tri-x-f4017-2021.json').read_text(encoding='utf-8'))
    h = json.loads((DONNEES / 'hp5-plus.json').read_text(encoding='utf-8'))
    pts = lambda c: [tuple(p) for p in c]
    noms = []
    sp = t['sensibilites_spectrales']['D=1.0>Gross Fog']
    for nom, rev in (('tmax', 'tri-x_400_35mm_T-MAX'), ('d76', 'tri-x_400_35mm_D-76')):
        for cle, c in t['courbes_caracteristiques'][rev].items():
            if cle.endswith('minutes'):
                n = f'trix_{nom}_{cle.split()[0]}'
                CC[n], SPECTRES_LOG[n] = pts(c), dict(pts(sp))
                noms.append(n)
    CC['trix_fiche'], SPECTRES_LOG['trix_fiche'] = CC['trix_tmax_6'], dict(pts(sp))
    # développement « normal » au sens d'Ilford (pente moyenne ≈ 0,62, fiche des révélateurs liquides de juin 2010) :
    # Tri-X en DD-X ou en Rodinal à leurs temps conseillés, faute de courbe publiée (hypothèse), interpolé entre
    # deux temps D-76 puis entre deux temps T-MAX
    for nom, (a, b) in (('trix_g062_d76', ('trix_d76_8', 'trix_d76_10')), ('trix_g062_tmax', ('trix_tmax_7', 'trix_tmax_9'))):
        CC[nom], SPECTRES_LOG[nom] = interpoler_pente(CC[a], CC[b], 0.62), dict(pts(sp))
        noms.append(nom)
    CC['hp5_fiche'] = pts(h['courbe_caracteristique']['points'])
    SPECTROGRAMMES['hp5_fiche'] = {l: max(v, 0.0) for l, v in h['spectrogramme']['points']}
    return ['trix_fiche', 'hp5_fiche'] + noms
# point de vitesse ISO (densité voile + 0,1) et gris moyen environ 1,0 log plus haut (ISO 6, mesure K = 12,5)
PAPIER = {'dmin': 0.05, 'dmax': 2.10, 'R': 1.10}
LAMBDA = np.arange(400, 721, 10)


def sensibilite(film):
    """Sensibilité spectrale relative par énergie, 400 à 720 nm (pas de 10 nm, comme camspec)."""
    import colour
    if film.startswith('trix'):
        l, v = zip(*sorted(SPECTRES_LOG[film].items()))
        s = 10 ** np.interp(LAMBDA, l, v)
    else:
        l, v = zip(*sorted(SPECTROGRAMMES[film].items()))
        h = np.interp(LAMBDA, l, v, left=0, right=0)
        s = h / colour.sd_blackbody(2850, ms.FORME).values
    return s / s.max()


def sens_srgb():
    """« Sensibilités » d'une caméra qui verrait en sRGB linéaire (CIE 1931 2° → sRGB), 3 × 33 : avec poids(), donne
    le mélange de canaux en sRGB linéaire qui imite un film."""
    import colour
    cmf = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer'].copy().align(ms.FORME).values
    return ms.XYZ_VERS_SRGB @ cmf.T


def reflectances(n=600, graine=0):
    """ColorChecker (Ohta) + spectres lisses aléatoires (sommes de gaussiennes), pour ajuster des pondérations."""
    import colour
    cc = colour.SDS_COLOURCHECKERS['ColorChecker N Ohta']
    R = [sd.copy().align(ms.FORME).values for sd in cc.values()]
    rng = np.random.default_rng(graine)
    for _ in range(n):
        r = np.full(len(LAMBDA), rng.uniform(0.02, 0.3))
        for _ in range(rng.integers(1, 4)):
            r += rng.uniform(0.1, 0.8) * np.exp(-0.5 * ((LAMBDA - rng.uniform(380, 740)) / rng.uniform(15, 90)) ** 2)
        R.append(np.clip(r, 0.01, 0.98))
    return np.array(R)


def poids(film, sens, illuminant='D65'):
    """Pondération (R, G, B) du RGB caméra équilibré du D40 qui reproduit la réponse du film (blanc = 1, somme 1)."""
    import colour
    E = colour.SDS_ILLUMINANTS[illuminant].copy().align(ms.FORME).values
    R = reflectances()
    cam = (R * E) @ sens.T / (E @ sens.T)
    S = sensibilite(film)
    y = (R * E) @ S / (E @ S)
    # moindres carrés relatifs, pondérations ≥ 0 et somme = 1 (le blanc reste blanc, pas de bruit amplifié)
    from scipy.optimize import minimize
    f = lambda w: np.mean(((cam @ w - y) / y) ** 2)
    r = minimize(f, np.full(3, 1 / 3), method='SLSQP', bounds=[(0, 1)] * 3,
                 constraints=[{'type': 'eq', 'fun': lambda w: w.sum() - 1}])
    w = r.x
    err = np.abs(cam @ w - y) / y
    return w, float(np.median(err))


def logistique_papier(logE, p=None):
    """Densité de réflexion du papier (grade 2 par défaut, PAPIER) en fonction du log d'exposition (0 = milieu de la
    courbe) ; p : autre papier (dmin, dmax, R = étendue d'exposition)."""
    p = PAPIER if p is None else p
    f0, f1 = 0.04 / (p['dmax'] - p['dmin']), 0.9
    s = p['R'] / (np.log(f1 / (1 - f1)) - np.log(f0 / (1 - f0)))
    return p['dmin'] + (p['dmax'] - p['dmin']) / (1 + np.exp(-logE / s))


def courbe(film, ref, gris_cible=118, papier=None):
    """Courbe de 4 096 valeurs (échelle des courbes d'usine, 0..4095) : entrée = signal linéaire du D40 après
    la matrice N&B (blanc capteur = 1). Le gris moyen de la scène est l'entrée où la courbe de référence
    `ref` (IIIa, cran Normal) rend 118/255 ; il est posé 1,0 log au-dessus du point de vitesse ISO du film.
    papier : clés de PAPIER à remplacer pour le tirage (R plus petit = grade plus dur ; dmax plus bas = noirs mats)."""
    pap = {**PAPIER, **(papier or {})}
    cc = np.array(CC[film])
    voile = cc[:, 1].min()
    logH_vitesse = np.interp(voile + 0.1, cc[:, 1], cc[:, 0])
    logH_gris = logH_vitesse + 1.0
    ref = np.asarray(ref, float)
    v_gris = np.searchsorted(ref, gris_cible / 255 * 4095) / 4095
    v = np.arange(4096) / 4095
    logH = logH_gris + np.log10(np.maximum(v, 1e-6) / v_gris)
    # pied : en dessous de la courbe numérisée, densité du voile ; au-dessus, prolongement linéaire de la pente
    # (FP4 : la fiche montre une épaule, densité tenue au-delà)
    pente = 0.0 if film == 'fp4' else (cc[-1, 1] - cc[-4, 1]) / (cc[-1, 0] - cc[-4, 0])
    D = np.where(logH > cc[-1, 0], cc[-1, 1] + pente * (logH - cc[-1, 0]), np.interp(logH, cc[:, 0], cc[:, 1]))
    D_gris = np.interp(logH_gris, cc[:, 0], cc[:, 1])

    def tirage(decal):
        Dp = logistique_papier(decal - D, pap)  # plus le négatif est dense, moins le papier est exposé
        Rp = 10 ** -Dp
        r_blanc, r_noir = 10 ** -pap['dmin'], 10 ** -PAPIER['dmax']  # blanc du papier ; noir de référence : grade 2
        lin = np.clip((Rp - r_noir) / (r_blanc - r_noir), 0, 1)
        return np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)

    # exposition du tirage : le gris de la scène sort à gris_cible
    from scipy.optimize import brentq
    k = int(round(v_gris * 4095))
    decal = brentq(lambda d: tirage(d)[k] * 255 - gris_cible, D_gris - 2, D_gris + 3)
    out = np.maximum.accumulate(tirage(decal)) * 4095
    return np.round(out).astype(int), {'logH_gris': round(float(logH_gris), 2), 'densite_gris': round(float(D_gris), 2),
                                       'v_gris': round(float(v_gris), 4)}


def cible_tonale(film, gris_cible=118):
    """Courbe film + tirage indépendante du boîtier : entrée = scène en sRGB linéaire (gris de 18 % → gris_cible/255),
    sortie sRGB codée. Renvoie la table par IL autour du gris, la table de 257 valeurs (entrée sRGB codée, si le
    boîtier rendait la scène en sRGB pur avant la courbe : hypothèse), et les repères de la courbe du négatif."""
    v = np.arange(4096) / 4095
    ref = np.round(oetf(v) * 4095)
    c, info = courbe(film, ref, gris_cible)
    c = c / 4095
    il = np.round(np.arange(-7, 4.01, 1 / 3), 2)
    lin = np.clip(0.18 * 2.0 ** il, 0, 1)
    x = np.linspace(0, 1, 257)
    cc = np.array(CC[film])
    voile = cc[:, 1].min()
    lv = np.interp(voile + 0.1, cc[:, 1], cc[:, 0])
    g = lambda d: (np.interp(lv + d, cc[:, 0], cc[:, 1]) - (voile + 0.1)) / d
    return {'film': film, 'gris_cible_8bits': gris_cible, **info,
            'negatif': {'voile': round(float(voile), 3), 'logH_point_vitesse': round(float(lv), 3),
                        'pente_moyenne_1_5_log': round(float(g(1.5)), 3), 'densite_max_lue': round(float(cc[:, 1].max()), 3)},
            'par_IL': [[float(a), round(float(np.interp(b, v, c)) * 255, 1)] for a, b in zip(il, lin)],
            'table_257_entree_srgb_codee': np.interp(eotf(x), v, c).round(4).tolist()}


# --- Profils Look de Lightroom (lecture seule, usage interne) -----------------------------------------------
B85 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?`'|()[]{}@%$#"


def lire_look(xmp):
    """Table RGB d'un profil Look (.xmp) : dict(lut (n, n, n, 3) dans 0..1, primaires, gamma, div)."""
    import html
    import re
    import struct
    import zlib
    s = html.unescape(re.search(r'crs:Table_[0-9A-F]+="([^"]*)"', pathlib.Path(xmp).read_text(encoding='utf-8')).group(1))
    dec = {c: i for i, c in enumerate(B85)}
    raw = bytearray()
    for i in range(0, len(s), 5):
        ch = s[i:i + 5]
        v = sum(dec[c] * 85 ** k for k, c in enumerate(ch))
        raw += struct.pack('<I', v & 0xFFFFFFFF)[:4 if len(ch) == 5 else len(ch) - 1]
    d = zlib.decompress(bytes(raw[4:]))
    assert len(d) == struct.unpack('<I', raw[:4])[0]
    typ, ver, dims, div = struct.unpack('<4I', d[:16])
    assert typ == 1 and dims == 3
    v = np.frombuffer(d[16:16 + 6 * div ** 3], '<u2').astype(np.int64).reshape(div, div, div, 3)
    nom = (np.arange(div) * 0xFFFF + (div >> 1)) // (div - 1)
    ident = np.stack(np.meshgrid(nom, nom, nom, indexing='ij'), -1)
    prim, gam = struct.unpack('<2I', d[16 + 6 * div ** 3:24 + 6 * div ** 3])
    return {'lut': ((v + ident) & 0xFFFF) / 65535.0, 'primaires': prim, 'gamma': gam, 'div': div}


def eotf(v):
    return np.where(v <= 0.04045, v / 12.92, ((np.clip(v, 0, None) + 0.055) / 1.055) ** 2.4)


def oetf(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * v ** (1 / 2.4) - 0.055)


def melange_look(xmp):
    """Mélange de canaux d'un profil N&B : sortie ≈ diag(Σ w_c · entrée_c) en sRGB linéaire ; renvoie
    (w sRGB linéaire, diagonale (entrée codée → sortie codée), écart médian relatif)."""
    t = lire_look(xmp)
    assert t['primaires'] == 0 and t['gamma'] == 1, 'profil attendu en sRGB'
    L = t['lut']
    assert np.ptp(L, -1).max() < 1e-3, 'profil attendu en noir et blanc (sortie grise)'
    L = L[..., 0]
    n = t['div']
    x = np.arange(n) / (n - 1)
    diag = np.maximum.accumulate(np.array([L[i, i, i] for i in range(n)]))
    R, G, B = np.meshgrid(x, x, x, indexing='ij')
    o = L.ravel()
    m = (o > 0.05) & (o < 0.95)
    A = eotf(np.c_[R.ravel(), G.ravel(), B.ravel()])[m]
    y = eotf(np.interp(o, diag + np.arange(n) * 1e-9, x))[m]
    w = np.linalg.lstsq(A, y, rcond=None)[0]
    w = w / w.sum()
    return w, (x, diag), float(np.median(np.abs(A @ w - y) / y))


def histogrammes(liste, fs, I, X, J, w_xyz, ref):
    """Courbe de tons lue sur les images entières (appariement des quantiles RAW → export), car les blocs
    uniformes manquent dans les ombres (bruit) : c'est là que la courbe se joue pour les noirs.
    Le RAW est mis à l'exposition de l'export par un gain calé sur les blocs avec la courbe `ref`.
    Renvoie (x, y) regroupés par classes de log x, et les % de pixels < 2 % et < 10 % de chaque export."""
    import os
    import rawpy
    from PIL import Image, ImageOps
    from scipy.optimize import minimize_scalar
    v = np.linspace(0, 1, 4096)
    paires = {}
    for l in pathlib.Path(liste).read_text().splitlines():
        if l.strip():
            raw, jp = l.split('\t')
            paires[os.path.splitext(os.path.basename(jp))[0]] = (raw, jp)
    q = np.r_[np.linspace(0.001, 0.02, 20), np.linspace(0.025, 0.99, 60)]
    XS, YS, noirs = [], [], []
    for k, fch in enumerate(fs):
        m = I == k
        if m.sum() < 300:
            continue
        raw, jp = paires[os.path.basename(fch)[:-4]]
        ys, yj = X[m] @ w_xyz, J[m].mean(1)
        lg = minimize_scalar(lambda lg: np.median(np.abs(np.interp(np.clip(ys * np.exp(lg), 0, 1), v, ref) - yj)),
                             bounds=(-4, 4), method='bounded').x
        x = rawpy.imread(raw).postprocess(half_size=True, output_color=rawpy.ColorSpace.XYZ, gamma=(1, 1), no_auto_bright=True,
                                          use_camera_wb=True, output_bps=16).astype(np.float32) / 65535
        x = np.clip((x @ w_xyz) * np.exp(lg), 0, 1)
        j = np.asarray(ImageOps.exif_transpose(Image.open(jp)).convert('L'), np.float32) / 255
        XS.append(np.quantile(x, q)); YS.append(np.quantile(j, q))
        noirs.append((100 * (j < .02).mean(), 100 * (j < .10).mean()))
    XS, YS = np.concatenate(XS), np.concatenate(YS)
    bords = np.geomspace(5e-4, 1, 30)
    xb, yb = [], []
    for a, b in zip(bords[:-1], bords[1:]):
        m = (XS >= a) & (XS < b)
        if m.sum() >= 3:
            xb.append(np.sqrt(a * b)); yb.append(np.median(YS[m]))
    return np.array(xb), np.maximum.accumulate(np.array(yb)), np.array(noirs)


def paires_preset(dossier, camspec, xmp, liste, par_image=1500):
    """Tri-X du preset acheté : mélange tiré du profil, courbe ajustée sur les exports de Thomas (gain par image).
    Renvoie aussi l'ajustement avec un mélange libre, pour contrôle. 1 image sur 4 tenue à part."""
    import colour
    import rendus
    from scipy.optimize import least_squares, minimize_scalar
    w_srgb, (xd, diag), e_look = melange_look(xmp)
    X, J, I, fs, espace = rendus.charger(dossier, par_image)
    S = colour.RGB_COLOURSPACES[espace]
    cible = colour.XYZ_to_Lab(colour.RGB_to_XYZ(eotf(J), S, ms.D65), ms.D65)
    test = np.arange(len(fs)) % 4 == 3
    tr = ~test[I]
    w_xyz_look = w_srgb @ colour.RGB_COLOURSPACES['sRGB'].matrix_XYZ_to_RGB
    lab = lambda g: colour.XYZ_to_Lab(colour.RGB_to_XYZ(eotf(np.repeat(g[:, None], 3, 1)), colour.RGB_COLOURSPACES['sRGB'], ms.D65), ms.D65)
    imgs = np.flatnonzero(~test)
    pos = np.full(len(fs), -1); pos[imgs] = np.arange(len(imgs))

    def sortie(q, libre, Xs, Is):
        w = q[:3] if libre else w_xyz_look
        o = 3 if libre else 0
        pc = q[o:o + rendus.NK]
        g = np.exp(q[o + rendus.NK:])[pos[Is]]
        return rendus.courbe(pc, (Xs @ w) * g)

    def ajuste(libre):
        q0 = np.r_[w_xyz_look if libre else [], np.zeros(rendus.NK), np.zeros(len(imgs))]
        f = lambda q: (lab(sortie(q, libre, X[tr], I[tr])) - cible[tr]).ravel()
        return least_squares(f, q0, loss='soft_l1', f_scale=3, max_nfev=200).x

    def ecarts(q, libre):
        e_tr = colour.delta_E(lab(sortie(q, libre, X[tr], I[tr])), cible[tr], method='CIE 2000')
        es = []
        for im in np.flatnonzero(test):
            m = I == im
            if not m.any():
                continue
            w = q[:3] if libre else w_xyz_look
            pc = q[(3 if libre else 0):(3 if libre else 0) + rendus.NK]
            e = lambda lg: colour.delta_E(lab(rendus.courbe(pc, (X[m] @ w) * np.exp(lg))), cible[m], method='CIE 2000')
            lg = minimize_scalar(lambda lg: np.median(e(lg)), bounds=(-3, 3), method='bounded').x
            es.append(e(lg))
        e_te = np.concatenate(es) if es else np.array([np.nan])
        st = lambda e: {'mediane': round(float(np.median(e)), 2), 'centile_90': round(float(np.percentile(e, 90)), 2)}
        return {'entrainement': st(e_tr), 'tenu_a_part': st(e_te)}

    q_look = ajuste(False)
    q_libre = ajuste(True)
    # gain médian = 1 (luminosité moyenne de ses exports) reporté dans la courbe
    med = np.median(q_look[rendus.NK:])
    pc = q_look[:rendus.NK]
    v = np.linspace(0, 1, 4096)
    T = rendus.courbe(pc, v * np.exp(med))
    # pondérations D40 : w_xyz · M_D40 (caméra équilibrée → XYZ D65, sensibilités camspec)
    sens = ms.lire_camspec(camspec)
    rgb, xyz, _ = ms.donnees(sens, 'D65')
    M = ms.ajuster(rgb, xyz)
    w_d40 = w_xyz_look @ M
    w_libre_srgb = q_libre[:3] @ np.linalg.inv(colour.RGB_COLOURSPACES['sRGB'].matrix_XYZ_to_RGB)
    # courbe livrée : diagonale du profil appliquée à la courbe IIIa Normal du D40 (n° 17), notée sur toutes les paires
    import simulateur as sm
    c17 = np.asarray(sm.tables(sm.firmware())[1][17], float) / 4095
    v = np.linspace(0, 1, 4096)
    comp = np.interp(c17, xd, diag)
    # ombres : la composition (diagonale ∘ courbe IIIa) bouche les ombres plus que les exports (Lightroom et les
    # réglages de Thomas les ouvrent) ; sous 0,18 on prend la courbe lue sur les histogrammes, au-dessus la
    # composition (les deux s'accordent à ±4/255 entre 0,18 et 0,5), raccord progressif en log de 0,12 à 0,25
    xh, yh, noirs = histogrammes(liste, fs, I, X, J, w_xyz_look, comp)
    lx = np.log(np.maximum(v, 1e-6))
    hist = np.interp(lx, np.log(xh), yh)
    a = np.clip((lx - np.log(0.12)) / (np.log(0.25) - np.log(0.12)), 0, 1)
    livree = np.maximum.accumulate((1 - a) * hist + a * comp)

    def note(Tc):
        es = []
        for k in range(len(fs)):
            m = I == k
            if not m.any():
                continue
            e = lambda lg: colour.delta_E(lab(np.interp(np.clip((X[m] @ w_xyz_look) * np.exp(lg), 0, 1), v, Tc)), cible[m], method='CIE 2000')
            lg = minimize_scalar(lambda lg: np.median(e(lg)), bounds=(-4, 4), method='bounded').x
            es.append(e(lg))
        e = np.concatenate(es)
        return {'mediane': round(float(np.median(e)), 2), 'centile_90': round(float(np.percentile(e, 90)), 2)}
    return {'source': f'{len(fs)} paires RAW + export JPEG ({dossier}), {len(X)} blocs ; 1 image sur 4 tenue à part',
            'melange_srgb_lineaire_profil': w_srgb.round(4).tolist(), 'ecart_median_relatif_profil': round(e_look, 3),
            'melange_srgb_lineaire_libre': (w_libre_srgb / w_libre_srgb.sum()).round(4).tolist(),
            'poids_D40': (w_d40 / w_d40.sum()).round(4).tolist(),
            'dE2000_melange_du_profil': ecarts(q_look, False), 'dE2000_melange_libre': ecarts(q_libre, True),
            'dE2000_courbe_composee': note(comp), 'dE2000_courbe_livree': note(livree),
            'dE2000_courbe_IIIa_sans_preset': note(c17),
            'exports_pct_pixels_sous_2_et_10_pourcent': np.median(noirs, 0).round(1).tolist(),
            'courbe_livree': livree.round(6).tolist(),
            'courbe_lineaire': T.round(6).tolist(),
            'diagonale_profil_8bits': [[int(round(a * 255)), int(round(b * 255))] for a, b in zip(xd[::4], diag[::4])]}


def noter_courbes_paires(dossier, xmp, courbes, seuil=2 ** -1.5, par_image=1500):
    """ΔE2000 sur les paires du preset acheté (blocs) de courbes N&B au format D40 (4 096 valeurs 0..4095) ; gain par image
    ajusté avec la première courbe puis gardé. « Hautes lumières » : entrée de la courbe au-dessus de `seuil`."""
    import colour
    import rendus
    from scipy.optimize import minimize_scalar
    w_srgb, _, _ = melange_look(xmp)
    w_xyz = w_srgb @ colour.RGB_COLOURSPACES['sRGB'].matrix_XYZ_to_RGB
    X, J, I, fs, espace = rendus.charger(dossier, par_image)
    cible = colour.XYZ_to_Lab(colour.RGB_to_XYZ(eotf(J), colour.RGB_COLOURSPACES[espace], ms.D65), ms.D65)
    lab = lambda g: colour.XYZ_to_Lab(colour.RGB_to_XYZ(eotf(np.repeat(g[:, None], 3, 1)), colour.RGB_COLOURSPACES['sRGB'], ms.D65), ms.D65)
    v = np.arange(4096) / 4095
    C0 = np.asarray(courbes[next(iter(courbes))], float) / 4095
    y = X @ w_xyz
    g = np.ones(len(fs))
    for k in range(len(fs)):
        m = I == k
        if m.any():
            e = lambda lg: np.median(colour.delta_E(lab(np.interp(np.clip(y[m] * np.exp(lg), 0, 1), v, C0)), cible[m], method='CIE 2000'))
            g[k] = np.exp(minimize_scalar(e, bounds=(-4, 4), method='bounded').x)
    x = np.clip(y * g[I], 0, 1)
    haut = x > seuil
    res = {'part_hautes_lumieres': round(float(haut.mean()), 3)}
    for nom, C in courbes.items():
        e = colour.delta_E(lab(np.interp(x, v, np.asarray(C, float) / 4095)), cible, method='CIE 2000')
        res[nom] = {'tout': round(float(np.median(e)), 2), 'hors_hautes_lumieres': round(float(np.median(e[~haut])), 2),
                    'hautes_lumieres': round(float(np.median(e[haut])), 2) if haut.any() else None}
    return res


def courbe_d40(T, ref, gris_cible=118):
    """Courbe T (entrée linéaire, blanc = 1, sortie 0..1 codée) au format des courbes d'usine, étirée en entrée
    pour qu'un gris que la courbe de référence rend 118/255 garde ce rendu (même exposition que le D40)."""
    T = np.asarray(T, float) * 4095
    ref = np.asarray(ref, float)
    v = np.arange(4096) / 4095
    k = int(np.searchsorted(ref, gris_cible / 255 * 4095))
    x_T = np.interp(gris_cible / 255 * 4095, T, v)
    return np.round(np.maximum.accumulate(np.clip(np.interp(v * x_T / (k / 4095), v, T), 0, 4095))).astype(int)


def self_test():
    for f in ['trix', 'hp5', 'fp4'] + fiches_exactes():
        s = sensibilite(f)
        assert s.shape == (33,) and abs(s.max() - 1) < 1e-9 and s[LAMBDA >= 680].max() < 0.01
    y = logistique_papier(np.array([-5.0, 0, 5]))
    assert y[0] < PAPIER['dmin'] + 0.01 and y[2] > PAPIER['dmax'] - 0.01
    print('self-test OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['poids', 'srgb', 'tonale', 'look', 'paires'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.action == 'look':
        w, (x, d), e = melange_look(a.args[0])
        print('mélange sRGB linéaire', w.round(4), f'écart médian relatif {e:.3f}')
        print('diagonale (8 bits)', [(round(u * 255), round(o * 255)) for u, o in zip(x[::3], d[::3])])
        return
    if a.action == 'paires':
        import json
        print(json.dumps(paires_preset(*a.args), ensure_ascii=False))
        return
    if a.action == 'tonale':
        import json
        print(json.dumps([cible_tonale(f) for f in ['trix', 'hp5', 'fp4'] + fiches_exactes()], ensure_ascii=False))
        return
    if a.action == 'srgb':
        for f in ['trix', 'hp5', 'fp4'] + fiches_exactes()[:2]:
            w, e = poids(f, sens_srgb())
            print(f, 'mélange sRGB linéaire (R, G, B) :', w.round(4), f'écart médian relatif {e:.3f}')
        return
    sens = ms.lire_camspec(a.args[0])
    for f in ('trix', 'hp5', 'fp4'):
        w, e = poids(f, sens)
        print(f, 'pondérations D40 (R, G, B) :', w.round(4), f'écart médian relatif {e:.3f}')


if __name__ == '__main__':
    sys.exit(main())
