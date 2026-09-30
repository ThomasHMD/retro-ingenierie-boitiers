#!/usr/bin/env python3
"""Rendus couleur du D200 (firmware B 2.01) : Chrome et Positive au format des tables du firmware, et planche de
tous les rendus prévus pour le menu Optimiser l'image (choix de Thomas en octobre 2026 : Normal et Personnalisé
gardés, Moins net → Chrome, Saturé → Positive, Très saturé → FP4, Portrait → HP5, Noir et blanc → Tri-X).

Chaque rendu couleur part du modèle mesuré du rendu (d40/recettes/mesures/<rendu>.json : K, XYZ → espace linéaire du
rendu, et sa courbe, ajustés sur les paires RAW+JPEG du boîtier d'origine) :
- matrice caméra : ajustée pour le capteur du D200 (sensibilités camspec) au moindre ΔE2000 moyen contre le modèle
  appliqué au XYZ exact, sur 424 réflectances (ColorChecker + 400 spectres lisses, films_nb.reflectances), sous
  D65, |coefficient| ≤ 980/512 (registre : 1 023 ; marge des déclinaisons), lignes = 512. Écrite par `ajuster` dans
  d200/recettes/matrices.json, relue ensuite ;
- matrice YCbCr : BT.601 plein (le JPEG décodé redonne le sRGB du rendu) ;
- courbe : courbe mesurée du rendu (d40/recettes/mesures), étirée en entrée pour qu'un gris que la courbe Normale
  du D200 (n° 3) rend 118/255 garde ce rendu (même exposition que Nikon), épaule jusqu'au blanc à la pleine
  échelle (recettes_v1.epaule, comme les V1 du D40), sortie sur 8 bits, puis codée en
  256 seuils (format des 21 courbes intégrées, 0x3884D8) ;
- secteurs : **neutres** (256, 0, 0, 256). Essai d’octobre 2026 sur les vues de séance : les secteurs de Nikon
  appliqués avec le modèle du D40 (nœuds, ordre des blocs, quel que soit l'ordre essayé) éloignent le simulateur
  du JPEG du D200 (ΔE2000 médian 1,8 → 2,2 à 3,0 sur les blocs les plus touchés) : l'étage du D200 ne se lit pas
  comme celui du D40. Les recettes V1 (matrice ajustée AVEC secteurs) ne se transportent donc pas telles quelles ;
  sans secteurs, la matrice bornée ajustée ici reste à 0,5-0,7 (Chrome) et 0,2-0,3 (Positive) du modèle mesuré sur
  les deux scènes, contre 0,3-0,4 et 0,2-0,5 pour V1 + secteurs si le modèle du D40 avait été juste.
Le noir et blanc vient de d200_nb.py (Tri-X, HP5, FP4).

  d200_rendus.py planche <nef>… --sortie <fichier.jpg>    colonnes titrées : JPEG du boîtier, Chrome, Positive, Tri-X, HP5, FP4
  d200_rendus.py recette <rendu>                           matrice, YCbCr, seuils (aperçu)
  d200_rendus.py ajuster                                   réajuste les matrices, écrit d200/recettes/matrices.json
  d200_rendus.py etage                                     V2 : matrice + 16 secteurs ajustés sur les paires, écrit d200/recettes/etage-v2.json
  d200_rendus.py planche-v2 <nef>… --sortie <préfixe>      <préfixe>-couleur.jpg (V1, V2 fidèle, V2 typée) et <préfixe>-nb.jpg
  d200_rendus.py --self-test
"""
import argparse
import json
import pathlib
import sys
import warnings

import numpy as np

warnings.filterwarnings('ignore')
ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI.parent.parent / 'd40' / 'outils'))
import d200_simulateur as sim  # noqa: E402

RECETTES = ICI.parent.parent / 'd40' / 'recettes'
CAMSPEC = pathlib.Path.home() / 'Library/Caches/retro-ingenierie-boitiers/camspec/camspec_database.txt'
COULEURS = {'chrome': 'classic-chrome.json', 'positive': 'positive-film.json'}
MATRICES = ICI.parent / 'recettes' / 'matrices.json'
ETAGE = ICI.parent / 'recettes' / 'etage-v2.json'   # V2 : matrice + 16 secteurs ajustés sur les paires (ajuster_etage)
PAIRES = pathlib.Path('paires')   # paires RAW + JPEG des boîtiers d'origine, à fabriquer soi-même (rendus.py extraire)
ECHANTILLONS = {'chrome': 'ech-Classic_Chrome', 'positive': 'ech-Positive_Film'}
TYPE = {'chrome': 0.80, 'positive': 1.20}   # variante « typée » : (Cb, Cr) de la V2 fidèle × facteur, par les secteurs
BORNE = 980                    # /512 ; registre : 1 023 (signe et grandeur, bit 0x400) ; marge pour les déclinaisons par éclairage et Adobe RGB (d200_preglages, borne 1 000)
NEUTRE = [256] * 16 + [0] * 32 + [256] * 16
COURBE_NORMALE = 3             # mode I, tons Normale
YCC_601 = np.array([[77, 150, 29], [-43, -85, 128], [128, -107, -21]])   # /256
MENU = {'moins-net': 'chrome', 'sature': 'positive', 'tres-sature': 'fp4', 'portrait': 'hp5', 'noir-et-blanc': 'trix'}
NOMS = {'chrome': 'Chrome', 'positive': 'Positive', 'trix': 'Tri-X', 'hp5': 'HP5', 'fp4': 'FP4'}
ENTREE = {'chrome': 'Moins net', 'positive': 'Saturé', 'trix': 'N&B', 'hp5': 'Portrait', 'fp4': 'Très saturé'}


def entiers(m):
    """Matrice (lignes = 1) → 3×3 int à l'échelle 512, chaque ligne ramenée à 512 exactement (colonne du milieu)."""
    e = np.round(np.asarray(m) * 512).astype(int)
    e[:, 1] += 512 - e.sum(1)
    return e


def passage_d40_d200():
    import matrices_spectrales as ms
    S = {}
    for n in ('Nikon D40', 'Nikon D200'):
        rgb, xyz, _ = ms.donnees(ms.lire_camspec(CAMSPEC, n), 'D65')
        S[n] = ms.ajuster(rgb, xyz)
    return np.linalg.inv(S['Nikon D40']) @ S['Nikon D200']


def ajuster_etage(nom, lissage=1.0, par_image=300, graine=0):
    """V2 : matrice caméra du D200 et 64 valeurs de l'étage à 16 secteurs (d200_etage, sondes d’octobre 2026), ajustées
    ensemble sur les paires RAW+JPEG du rendu d'origine (d40/outils/rendus.py extraire : XYZ de la scène, JPEG sRGB),
    avec un gain par image. Scène vue par le D200 : RGB caméra = M_D200⁻¹ · XYZ (M_D200 : camspec, ColorChecker, D65).
    Chaîne simulée : matrice, courbe du rendu (celle de recette(), continue), YCbCr BT.601, étage, décodage JPEG.
    Comme rendus.ajuster_etage (D40) : passe sans étage en perte robuste, puis passe avec étage en moindres carrés
    pondérés (poids robustes de la 1re passe) ; régularisation : écart entre nœuds voisins (poids `lissage`) et rappel
    vers le neutre (lissage/5) ; diagonale 0,5-1,8, termes croisés ±0,5 ; |coefficient de matrice| ≤ BORNE par
    pénalité. 3 images sur 4 en entraînement, la 4e tenue à part (seul son gain y est ajusté)."""
    import colour
    import d200_etage
    import d200_nb
    import films_nb
    import matrices_spectrales as ms
    import rendus
    from scipy.optimize import least_squares, minimize_scalar
    from scipy.sparse import lil_matrix
    X, J, I, fs, espace = rendus.charger(str(PAIRES / ECHANTILLONS[nom]), par_image, graine)
    assert espace == 'sRGB', espace
    S = colour.RGB_COLOURSPACES['sRGB']
    lab = lambda v: colour.XYZ_to_Lab(colour.RGB_to_XYZ(rendus.eotf(v), S, ms.D65), ms.D65)
    cible = lab(J)
    rgb24, xyz24, _ = ms.donnees(ms.lire_camspec(CAMSPEC, 'Nikon D200'), 'D65')
    cam = X @ np.linalg.inv(ms.ajuster(rgb24, xyz24)).T
    b = sim.firmware()
    T = json.loads((RECETTES / 'mesures' / COULEURS[nom]).read_text())['courbe']
    ref = sim.courbes(b)[COURBE_NORMALE].astype(float) * 4095 / 255
    C = d200_nb.epaule(films_nb.courbe_d40(T, ref)) / 4095
    V = np.arange(4096) / 4095
    neutre = np.array(NEUTRE, float) / 256
    ordre = np.array(d200_etage.NOEUDS)

    def sortie(M, sec, c, g):
        y = (np.interp(np.clip((c @ M.T) * g[:, None], 0, 1), V, C) * 255) @ (YCC_601 / 256).T
        if sec is not None:
            y[:, 1:] = d200_etage.appliquer(y[:, 1:], sec.reshape(4, 16) * 256)
        return sim.rgb(y)

    def mat(q):
        M = np.zeros((3, 3))
        M[:, :2] = q[:6].reshape(3, 2)
        M[:, 2] = 1 - M[:, :2].sum(1)
        return M

    test = np.arange(len(fs)) % 4 == 3
    tr = ~test[I]
    imgs = np.flatnonzero(~test)
    pos = -np.ones(len(fs), int)
    pos[imgs] = np.arange(len(imgs))
    Xs, Is, cs = cam[tr], I[tr], cible[tr]
    n = len(Xs)

    def decoupe(q, etage):
        sec = q[6:70] if etage else None
        g = np.ones(len(fs))
        g[imgs] = np.exp(q[70 if etage else 6:])
        return mat(q), sec, g

    def regul(sec):
        if sec is None:
            return np.zeros(0)
        t = sec.reshape(4, 16)[:, ordre]
        return np.sqrt(n) * lissage * np.r_[np.diff(np.c_[t, t[:, :1]], axis=1).ravel(), 0.2 * (sec - neutre)]

    pen = lambda q: np.sqrt(n) * 50 * np.maximum(0, np.abs(mat(q)) - BORNE / 512).ravel()

    def ajuste(etage, q0, wv=None):
        wv = np.ones(3 * n) if wv is None else np.repeat(wv, 3)

        def f(q):
            M, sec, g = decoupe(q, etage)
            return np.r_[wv * (lab(sortie(M, sec, Xs, g[Is])) - cs).ravel(), regul(sec), pen(q)]
        ng = 70 if etage else 6
        lb, ub = np.full(len(q0), -np.inf), np.full(len(q0), np.inf)
        if etage:
            for k in range(4):
                lb[6 + 16 * k:22 + 16 * k], ub[6 + 16 * k:22 + 16 * k] = (0.5, 1.8) if k in (0, 3) else (-0.5, 0.5)
            q0 = np.clip(q0, lb + 1e-9, ub - 1e-9)
        Sp = lil_matrix((len(f(q0)), len(q0)), dtype=int)
        Sp[:, :ng] = 1
        Sp[np.repeat(np.arange(n), 3) * 3 + np.tile(np.arange(3), n), ng + np.repeat(pos[Is], 3)] = 1
        return least_squares(f, q0, jac_sparsity=Sp, loss='linear' if etage else 'soft_l1', f_scale=3,
                             max_nfev=200, bounds=(lb, ub), x_scale='jac').x

    m1 = np.array(json.loads(MATRICES.read_text())[nom]['matrice']) / 512
    q_v1 = np.r_[m1[:, :2].ravel(), np.zeros(len(imgs))]
    q_av = ajuste(False, q_v1)
    M, _, g = decoupe(q_av, False)
    e = np.linalg.norm(lab(sortie(M, None, Xs, g[Is])) - cs, axis=1)
    q_ap = ajuste(True, np.r_[q_av[:6], neutre, q_av[6:]], (1 + (e / 3) ** 2) ** -0.25)

    def ecarts(q, etage, masque):
        """ΔE2000 par image, le gain de chaque image réajusté (modèle figé)."""
        M, sec, _ = decoupe(q, etage)
        out = []
        for im in np.unique(I[masque]):
            m = I == im
            d = lambda lg: colour.delta_E(lab(sortie(M, sec, cam[m], np.full(m.sum(), np.exp(lg)))), cible[m], method='CIE 2000')
            out.append(d(minimize_scalar(lambda lg: np.median(d(lg)), bounds=(-2, 2), method='bounded').x))
        e = np.concatenate(out)
        return {'mediane': round(float(np.median(e)), 2), 'centile_90': round(float(np.percentile(e, 90)), 2)}

    M, sec, g = decoupe(q_ap, True)
    y = (np.interp(np.clip((Xs @ M.T) * g[Is][:, None], 0, 1), V, C) * 255) @ (YCC_601 / 256).T
    h = np.degrees(np.arctan2(y[:, 2], y[:, 1])) % 360
    couverture = [int(((np.abs((h - 22.5 * k + 180) % 360 - 180) < 11.25) & (np.hypot(y[:, 1], y[:, 2]) > 4)).sum())
                  for k in range(16)]
    return {'matrice': entiers(M).tolist(), 'secteurs': np.round(sec * 256).astype(int).tolist(),
            'dE2000': {'v1': {'entrainement': ecarts(q_v1, False, tr), 'tenu_a_part': ecarts(q_v1, False, ~tr)},
                       'v2': {'entrainement': ecarts(q_ap, True, tr), 'tenu_a_part': ecarts(q_ap, True, ~tr)}},
            'echantillons_par_noeud': couverture,
            'source': f'{len(fs)} paires RAW+JPEG ({ECHANTILLONS[nom]}, liste dans le même dossier), {par_image} blocs par '
                      f'image, graine {graine}, lissage {lissage} ; images tenues à part : {np.flatnonzero(test).tolist()} ; '
                      'd200/outils/d200_rendus.py etage'}


def ecrire_etage():
    d = {n: ajuster_etage(n) for n in COULEURS}
    ETAGE.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    for n, x in d.items():
        print(n, 'matrice', x['matrice'], '\n  ΔE2000', x['dE2000'], '\n  échantillons par nœud', x['echantillons_par_noeud'])
    print('écrit', ETAGE)


def seuils(lut):
    """Table de 4 096 sorties 8 bits (croissante) → 256 seuils 12 bits : dernière entrée qui donne au plus k."""
    lut = np.asarray(lut)
    return [max(0, int(np.searchsorted(lut, k, side='right')) - 1) for k in range(256)]


def ajuster(nom):
    """Matrice caméra du D200 pour le rendu `nom`, au moindre ΔE2000 moyen contre son modèle mesuré (voir en tête)."""
    import colour
    import films_nb
    import matrices_spectrales as ms
    from scipy.optimize import minimize
    m = json.loads((RECETTES / 'mesures' / COULEURS[nom]).read_text())
    K, T = np.array(m['K_XYZ_vers_lineaire']), np.array(m['courbe'])
    sens = ms.lire_camspec(CAMSPEC, 'Nikon D200')
    E = colour.SDS_ILLUMINANTS['D65'].copy().align(ms.FORME).values
    cmf = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer'].copy().align(ms.FORME).values
    R = films_nb.reflectances(400)
    rgb = (R * E) @ sens.T / (E @ sens.T)
    xyz, w = (R * E) @ cmf / (E @ cmf[:, 1]), E @ cmf / (E @ cmf[:, 1])
    S = colour.RGB_COLOURSPACES['sRGB']
    d65 = colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65']
    lab = lambda v: colour.XYZ_to_Lab(colour.RGB_to_XYZ(colour.models.eotf_sRGB(np.clip(v, 0, 1)), S, d65), d65)
    Tf = lambda x: np.interp(np.clip(x, 0, 1), np.linspace(0, 1, 4096), T)
    cible = lab(Tf((xyz @ K.T) / (K @ w)))
    B = BORNE / 512

    def mat(q):
        M = np.zeros((3, 3))
        M[:, :2] = q.reshape(3, 2)
        M[:, 2] = 1 - M[:, :2].sum(1)
        return M

    ecart = lambda M: colour.delta_E(lab(Tf(rgb @ M.T)), cible, method='CIE 2000')
    f = lambda q: ecart(mat(q)).mean() + 1e4 * np.sum(np.clip(np.abs(mat(q)) - B, 0, None) ** 2)
    M0 = np.array(m['matrice_D40']) @ passage_d40_d200()
    r = minimize(f, np.clip(M0, -B, B)[:, :2].ravel(), method='Nelder-Mead',
                 options={'maxiter': 6000, 'xatol': 1e-6, 'fatol': 1e-6})
    M = entiers(mat(r.x))
    assert np.abs(M).max() <= 1023
    e = ecart(M / 512)
    return {'matrice': M.tolist(),
            'ajustement_dE2000': {'mediane': round(float(np.median(e)), 2), 'moyenne': round(float(e.mean()), 2),
                                  'centile_90': round(float(np.percentile(e, 90)), 2)},
            'source': f'd40/recettes/mesures/{COULEURS[nom]} (K, courbe) appliqué au XYZ exact ; capteur : camspec Nikon D200 ; '
                      '424 réflectances (ColorChecker Ohta + 400 spectres lisses, graine 0), D65 ; d200/outils/d200_rendus.py ajuster'}


def ecrire_matrices():
    MATRICES.parent.mkdir(parents=True, exist_ok=True)
    d = {n: ajuster(n) for n in COULEURS}
    MATRICES.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    for n, x in d.items():
        print(n, x['matrice'], 'ΔE2000', x['ajustement_dE2000'])
    print('écrit', MATRICES)


def recette(nom, passage=None, b=None, variante='v1'):
    """Matrice caméra (×512), YCbCr BT.601 (×256), courbe (4 096 sorties 8 bits et 256 seuils), secteurs.
    variante : 'v1' (matrices.json, secteurs neutres, flashée en octobre 2026), 'fidele' (etage-v2.json : matrice et
    secteurs ajustés ensemble sur les paires du rendu d'origine), 'type' (fidèle, secteurs × TYPE[nom]).
    `passage` n'est plus utilisé (gardé pour les appelants)."""
    import d200_nb
    import films_nb
    b = sim.firmware() if b is None else b
    T = json.loads((RECETTES / 'mesures' / COULEURS[nom]).read_text())['courbe']
    m = np.array(json.loads(MATRICES.read_text())[nom]['matrice'])
    secteurs = list(NEUTRE)
    if variante != 'v1':
        e = json.loads(ETAGE.read_text())[nom]
        m = np.array(e['matrice'])
        f = TYPE[nom] if variante == 'type' else 1.0
        secteurs = [int(round(v * f)) for v in e['secteurs']]
    ref = sim.courbes(b)[COURBE_NORMALE].astype(float) * 4095 / 255
    c = d200_nb.epaule(films_nb.courbe_d40(T, ref))   # blanc atteint à la pleine échelle, comme les V1 du D40
    lut = np.maximum.accumulate(np.round(c * 255 / 4095).astype(int).clip(0, 255)).astype(np.uint8)
    s = seuils(lut)
    return {'matrice': m, 'ycc': YCC_601, 'lut': sim.courbe_seuils(s), 'seuils': s, 'secteurs': secteurs}


def rendre(cam, r):
    """Rendu simulé : matrice, courbe, YCbCr, puis l'étage à 16 secteurs du D200 (d200_etage.appliquer)."""
    import d200_etage
    lin = np.clip(cam @ np.asarray(r['matrice'], float).T / 512, 0, 1)
    y = np.asarray(r['lut'])[(lin * 4095).astype(np.int32)].astype(np.float32) @ (np.asarray(r['ycc'], float) / 256).T
    if list(r['secteurs']) != NEUTRE:
        forme = y.shape
        y = y.reshape(-1, 3)
        y[:, 1:] = d200_etage.appliquer(y[:, 1:], np.asarray(r['secteurs']).reshape(4, 16))
        y = y.reshape(forme)
    return sim.rgb(y)


def planche(nefs, sortie, largeur=700):
    """Une ligne par NEF, une colonne par rendu, chaque colonne titrée (rendu et entrée du menu qu'il remplace)."""
    from PIL import Image, ImageDraw
    import d200_nb
    import figures_v1 as fg
    b = sim.firmware()
    p = passage_d40_d200()
    rec = {n: recette(n, p, b) for n in COULEURS}
    films = {}
    for f in ('trix', 'hp5', 'fp4'):
        chemin = sim.FIRMWARE.parent / f'.d200-nb-{f}.json'
        chemin.write_text(json.dumps(d200_nb.fabriquer(f)))
        films[f] = sim.firmware(chemin)
        chemin.unlink()
    titres = ['JPEG du D200 actuel'] + [f'{NOMS[n]} (ex-{ENTREE[n]})' for n in list(COULEURS) + list(films)]
    lignes = []
    for nef in nefs:
        cam = sim.camera(nef)
        imgs = [sim.jpeg_aligne(nef, cam)] + [rendre(cam, rec[n]) for n in COULEURS] + [d200_nb.rendre(cam, films[f]) for f in films]
        vues = []
        for a in imgs:
            v = Image.fromarray((a * 255 + .5).astype(np.uint8))
            v.thumbnail((largeur, largeur))
            vues.append(v)
        lignes.append((pathlib.Path(nef).stem, vues))
    h = lignes[0][1][0].height
    marge, haut, gauche = 12, 60, 40
    im = Image.new('RGB', (gauche + len(titres) * (largeur + marge), haut + len(lignes) * (h + marge)), 'white')
    d = ImageDraw.Draw(im)
    police = fg.police(26, True)
    for k, t in enumerate(titres):
        x = gauche + k * (largeur + marge)
        d.text((x + (largeur - d.textlength(t, font=police)) / 2, 16), t, fill=(20, 20, 20), font=police)
    for i, (nom, vues) in enumerate(lignes):
        y = haut + i * (h + marge)
        for k, v in enumerate(vues):
            im.paste(v, (gauche + k * (largeur + marge), y))
        ligne = Image.new('RGB', (h, gauche - 8), 'white')
        ImageDraw.Draw(ligne).text((8, 4), nom, fill=(60, 60, 60), font=fg.police(20))
        im.paste(ligne.rotate(90, expand=True), (0, y))
    im.save(sortie, quality=88)
    print('écrit', sortie, '(colonnes : ' + ', '.join(titres) + ')')


def nikon_normal(cam, b, jeu=10, courbe=COURBE_NORMALE):
    """Normal de Nikon simulé (mode I, tons Normale, lumière du jour : jeu 10, courbe 3) avec ses secteurs
    (table à 0x38B6C0 + 160 · jeu, blocs 1 à 4 = valeurs 16 à 79)."""
    import struct
    import d200_etage
    v = struct.unpack('>24h', sim.lire(b, 0x384BF8 + 48 * jeu, 48))
    sec = np.array(struct.unpack('>80h', sim.lire(b, 0x38B6C0 + 160 * jeu, 160))[16:])
    lin = np.clip(cam @ (np.array(v[:9]).reshape(3, 3) / 512).T, 0, 1)
    y = sim.courbes(b)[courbe][(lin * 4095).astype(np.int32)].astype(np.float32) @ (np.array(v[9:18]).reshape(3, 3) / 256).T
    forme = y.shape
    y = y.reshape(-1, 3)
    y[:, 1:] = d200_etage.appliquer(y[:, 1:], sec.reshape(4, 16))
    return sim.rgb(y.reshape(forme))


def grille(lignes, titres, sortie, largeur=520, sous_titres=None):
    """Planche : une ligne par (nom, [images]), chaque colonne titrée dans l'image (titre, sous-titre)."""
    from PIL import Image, ImageDraw
    import figures_v1 as fg
    vues = []
    for nom, imgs in lignes:
        r = []
        for a in imgs:
            v = Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8))
            v.thumbnail((largeur, largeur))
            r.append(v)
        vues.append((nom, r))
    h = max(v[1][0].height for v in vues)
    marge, haut, gauche = 10, 84 if sous_titres else 52, 40
    im = Image.new('RGB', (gauche + len(titres) * (largeur + marge), haut + sum(v[1][0].height + marge for v in vues)), 'white')
    d = ImageDraw.Draw(im)
    p1, p2 = fg.police(24, True), fg.police(18)
    for k, t in enumerate(titres):
        x = gauche + k * (largeur + marge)
        d.text((x + (largeur - d.textlength(t, font=p1)) / 2, 12), t, fill=(20, 20, 20), font=p1)
        if sous_titres:
            st = sous_titres[k]
            d.text((x + (largeur - d.textlength(st, font=p2)) / 2, 48), st, fill=(90, 90, 90), font=p2)
    y = haut
    for nom, r in vues:
        for k, v in enumerate(r):
            im.paste(v, (gauche + k * (largeur + marge), y))
        bande = Image.new('RGB', (r[0].height, gauche - 8), 'white')
        ImageDraw.Draw(bande).text((8, 4), nom, fill=(60, 60, 60), font=fg.police(18))
        im.paste(bande.rotate(90, expand=True), (0, y))
        y += r[0].height + marge
    im.save(sortie, quality=90)
    print('écrit', sortie)


def planche_v2(nefs, sortie_couleur, sortie_nb, reduction=3):
    """Avant/après V2 : couleur (Normal de Nikon, Chrome et Positive en V1, V2 fidèle, V2 typée) et N&B (N&B de
    Nikon, Tri-X, HP5, FP4 en V1 et V2), sur les mêmes NEF."""
    import d200_nb
    b = sim.firmware()
    rec = {(n, v): recette(n, None, b, v) for n in COULEURS for v in ('v1', 'fidele', 'type')}
    tx = {}
    for ver in (1, 2):
        chemin = sim.FIRMWARE.parent / f'.d200-nb-trix-v{ver}.json'
        chemin.write_text(json.dumps(d200_nb.fabriquer('trix', ver)))
        tx[ver] = sim.firmware(chemin)
        chemin.unlink()
    import d200_preglages as P
    import films_nb
    import matrices_spectrales as ms
    cs = ms.lire_camspec(CAMSPEC, 'Nikon D200')
    nb = {}
    for f in ('hp5', 'fp4'):
        w, _ = films_nb.poids(f, cs)
        W = np.round(w * 512).astype(int)
        W[1] += 512 - W.sum()
        for ver in (1, 2):
            lut, _ = P.courbe_film(f, b, ver)
            nb[f, ver] = {'matrice': np.array([W] * 3), 'ycc': YCC_601, 'lut': np.array(lut, np.uint8), 'secteurs': list(NEUTRE)}
    lc, ln = [], []
    for nef in nefs:
        cam = sim.reduire(sim.camera(nef), reduction)
        nom = pathlib.Path(nef).stem.split('-')[-1]
        lc.append((nom, [nikon_normal(cam, b)] + [rendre(cam, rec[n, v]) for n in COULEURS for v in ('v1', 'fidele', 'type')]))
        ln.append((nom, [d200_nb.rendre(cam, b)] + [d200_nb.rendre(cam, tx[v]) for v in (1, 2)]
                   + [rendre(cam, nb[f, v]) for f in ('hp5', 'fp4') for v in (1, 2)]))
    grille(lc, ['Normal (Nikon)'] + [f'{NOMS[n]} {t}' for n in COULEURS for t in ('V1', 'V2 fidèle', 'V2 typé' if n == 'chrome' else 'V2 typée')],
           sortie_couleur, sous_titres=['référence'] + [f'ex-{ENTREE[n]}' + s for n in COULEURS
                                                        for s in (' (actuel)', ', étage ajusté', f', saturation ×{TYPE[n]:.1f}')])
    grille(ln, ['N&B (Nikon)'] + [f'{NOMS[f]} {v}' for f in ('trix', 'hp5', 'fp4') for v in ('V1', 'V2')], sortie_nb,
           sous_titres=['référence'] + [f'ex-{ENTREE[f]}' + s for f in ('trix', 'hp5', 'fp4')
                                       for s in (' (actuel)', ', ' + {'trix': 'papier dur', 'hp5': 'papier doux, noirs mats',
                                                                      'fp4': 'hautes lumières longues'}[f])])


def self_test():
    b = sim.firmware()
    for n in range(sim.N_COURBES):   # aller-retour seuils → table → seuils sur les 21 courbes d'usine
        import struct
        brut = struct.unpack('>256H', sim.lire(b, sim.COURBES + 0x200 * n, 0x200))
        t = sim.courbe_seuils(brut)
        assert (sim.courbe_seuils(seuils(t)) == t).all(), f'courbe {n}'
    p = passage_d40_d200()
    for n in COULEURS:
        r = recette(n, p, b)
        assert (r['matrice'].sum(1) == 512).all() and np.abs(r['matrice']).max() <= 1023, n
        assert len(r['seuils']) == 256 and all(0 <= x <= 4095 for x in r['seuils']) and np.all(np.diff(r['seuils']) >= 0), n
        assert r['secteurs'] == NEUTRE, n
    print('self-test OK : seuils des 21 courbes d’usine relus à l’identique ; Chrome et Positive dans les bornes, secteurs neutres')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('commande', nargs='?', choices=['planche', 'planche-v2', 'recette', 'ajuster', 'etage'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--sortie')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.commande == 'ajuster':
        return ecrire_matrices()
    if a.commande == 'etage':
        return ecrire_etage()
    if a.commande == 'planche-v2':
        return planche_v2(a.args, a.sortie + '-couleur.jpg', a.sortie + '-nb.jpg')
    if a.commande == 'planche':
        return planche(a.args, a.sortie)
    if a.commande == 'recette':
        r = recette(a.args[0])
        print('matrice /512', r['matrice'].tolist(), '\nYCbCr /256', r['ycc'].tolist(),
              '\nseuils', r['seuils'][:8], '…', r['seuils'][-8:], '\nsecteurs', r['secteurs'])
        return
    ap.print_help()


if __name__ == '__main__':
    sys.exit(main())
