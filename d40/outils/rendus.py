#!/usr/bin/env python3
"""Rendus d'autres boîtiers (HNCS, Positive Film, Classic Chrome…) mesurés sur des paires RAW+JPEG et
ramenés à ce que le D40 sait faire : matrice 3x3 + courbe.

Référence : paires RAW+JPEG du boîtier (JPEG sorti du boîtier, pas un export Lightroom). Le RAW,
développé en XYZ D65 linéaire par LibRaw (matrice du boîtier connue de LibRaw, balance du boîtier),
donne la couleur de la scène ; le JPEG donne ce que le rendu en fait (espace lu dans son profil ICC :
Display P3 pour le X2D II, sRGB sinon). Échantillons : blocs uniformes du centre de l'image.

Modèle ajusté (ΔE2000, perte robuste) : code sRGB = T(K · XYZ · g_image), K matrice 3x3, T courbe
croissante partagée par les trois canaux, g_image un gain par photo (les boîtiers règlent la
luminosité photo par photo ; le D40 garde son exposition). Sortie en sRGB.

Pour le D40 : matrice firmware = K · M_D40, M_D40 = caméra équilibrée → XYZ D65 calculée sur ses
sensibilités spectrales (matrices_spectrales.py). Courbe : T, étirée pour qu'un gris rendu 118/255 par
la courbe de référence du D40 garde ce rendu (même exposition ; la luminosité propre au rendu n'est
pas mesurable par paires, chaque boîtier ayant sa mesure), écrite au format des courbes intégrées.

  rendus.py extraire <liste.tsv : RAW<tab>JPEG, ou RAW<tab>- pour l'aperçu intégré> <dossier d'échantillons>
  rendus.py ajuster <dossier d'échantillons> <camspec.txt> > recettes/mesures/<rendu>.json
  rendus.py patch recettes/mesures/<rendu>.json [--groupe 0] > patchs/<rendu>-groupe0.json
  rendus.py etage <dossier d’échantillons> <camspec.txt> [--lissage 1] [--borne-matrice 995] > <rendu>-etage.json
      même modèle + l'étage à 16 secteurs de teinte du D40 (simulateur.etage, 64 valeurs) : ΔE2000 avant / après,
      sur 3 images sur 4 (entraînement) et sur la 4e (tenue à part : seul le gain par image y est ajusté)
  rendus.py --self-test
"""
import argparse
import glob
import io
import json
import os
import pathlib
import struct
import sys
import warnings

import numpy as np

warnings.filterwarnings('ignore')
import colour  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import courbes  # noqa: E402
import matrices_spectrales as ms  # noqa: E402

D65 = ms.D65
P3 = colour.RGB_COLOURSPACES['Display P3']
SRGB = colour.RGB_COLOURSPACES['sRGB']
NK = 24
NOEUDS = np.geomspace(1e-4, 1.2, NK)


def eotf(v):
    return np.where(v <= 0.04045, v / 12.92, ((np.clip(v, 0, None) + 0.055) / 1.055) ** 2.4)


def espace_jpeg(im):
    icc = im.info.get('icc_profile')
    if icc:
        from PIL import ImageCms
        nom = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc))).strip()
        if 'P3' in nom:
            return 'Display P3'
        if 'Adobe' in nom:
            return 'Adobe RGB (1998)'
    return 'sRGB'


def extraire(liste, sortie, F=8):
    import rawpy
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = None
    os.makedirs(sortie, exist_ok=True)

    def red(a):
        h, w = a.shape[0] // F * F, a.shape[1] // F * F
        return a[:h, :w].reshape(h // F, F, w // F, F, *a.shape[2:])

    for ligne in pathlib.Path(liste).read_text().splitlines():
        if not ligne.strip():
            continue
        raw, j_chemin = ligne.split('\t')
        out = os.path.join(sortie, os.path.splitext(os.path.basename(j_chemin))[0] + '.npz')
        if os.path.exists(out):
            continue
        try:
            x = rawpy.imread(raw).postprocess(half_size=True, output_color=rawpy.ColorSpace.XYZ, gamma=(1, 1),
                                              no_auto_bright=True, use_camera_wb=True, output_bps=16)
        except rawpy.LibRawError as e:
            print('RAW illisible par LibRaw, écarté', raw, e)
            continue
        x = x.astype(np.float32) / 65535
        clip = red((x > 0.98).any(2)).any((1, 3))
        if j_chemin == '-':  # aperçu intégré au RAW (3FR du X2D : rendu du boîtier, Display P3 sans profil)
            im = Image.open(io.BytesIO(rawpy.imread(raw).extract_thumb().data))
            espace, j_chemin = 'Display P3', raw
            out = os.path.join(sortie, os.path.splitext(os.path.basename(raw))[0] + '-apercu.npz')
            if os.path.exists(out):
                continue
        else:
            im = Image.open(j_chemin)
            espace = espace_jpeg(im)
        j = ImageOps.exif_transpose(im).convert('RGB')
        if j.width < x.shape[1] * 0.9:  # JPEG plus petit que le RAW : on ramène le RAW à sa taille
            from scipy.ndimage import zoom
            z = j.width / x.shape[1]
            x = np.clip(zoom(x, (z, z, 1), order=1), 0, 1)
            clip = red((x > 0.98).any(2)).any((1, 3))
        f = round(j.width / x.shape[1])
        j = np.asarray(j.reduce(f) if f > 1 else j).astype(np.float32) / 255
        if (j.shape[1] > j.shape[0]) != (x.shape[1] > x.shape[0]):
            print('orientation incohérente', j_chemin)
            continue
        # le JPEG ne doit pas dépasser le RAW : on recadre son centre si besoin
        dy, dx = max(0, j.shape[0] - x.shape[0] + 2 * F), max(0, j.shape[1] - x.shape[1] + 2 * F)
        j = j[dy // 2:j.shape[0] - (dy - dy // 2), dx // 2:j.shape[1] - (dx - dx // 2)]
        xr, jr = red(x), red(j)
        xm, jm = xr.mean((1, 3)), jr.mean((1, 3))
        xs = xr[..., 1].std((1, 3)) / (xm[..., 1] + 1e-3)
        js = jr.mean(-1).std((1, 3)) / (jm.mean(-1) + 1e-2)
        # recalage : le JPEG est un peu recadré, on cherche le décalage sur la luminance log
        A, B = np.log(xm[..., 1] + 1e-4), np.log(jm.mean(-1) + 1e-3)
        H, W = B.shape
        cy, cx = (A.shape[0] - H) // 2, (A.shape[1] - W) // 2
        p = B[H // 6:-H // 6, W // 6:-W // 6]
        p = (p - p.mean()) / p.std()
        best = (-9, 0, 0)
        for dy in range(-cy - 8, cy + 9):
            for dx in range(-cx - 8, cx + 9):
                y0, x0 = cy + dy + H // 6, cx + dx + W // 6
                q = A[max(y0, 0):y0 + p.shape[0], max(x0, 0):x0 + p.shape[1]]
                if y0 < 0 or x0 < 0 or q.shape != p.shape:
                    continue
                c = (p * (q - q.mean()) / q.std()).mean()
                if c > best[0]:
                    best = (c, dy, dx)
        c, dy, dx = best
        # zone commune aux deux images (le décalage peut faire sortir le JPEG du RAW d'un bloc)
        y0, x0 = cy + dy, cx + dx
        ya, yb = max(0, -y0), min(H, A.shape[0] - y0)
        xa, xb = max(0, -x0), min(W, A.shape[1] - x0)
        X, S, C = (a[y0 + ya:y0 + yb, x0 + xa:x0 + xb] for a in (xm, xs, clip))
        jm, js = jm[ya:yb, xa:xb], js[ya:yb, xa:xb]
        ok = (S < 0.04) & (js < 0.04) & ~C & (jm.max(-1) < 0.985) & (X[..., 1] > 1e-4)
        yy, xx = np.mgrid[ya:yb, xa:xb]
        ok &= ((yy - H / 2) / H) ** 2 + ((xx - W / 2) / W) ** 2 < 0.16  # centre : ni vignetage ni distorsion
        if c < 0.9:
            print('recalage douteux, écarté', j_chemin, f'{c:.2f}')
            continue
        np.savez(out, X=X[ok], J=jm[ok], corr=c, espace=espace)
        print(os.path.basename(j_chemin), espace, f'corrélation {c:.3f}, {ok.sum()} blocs', flush=True)


def courbe(p, v):
    y = np.concatenate([[0], np.cumsum(np.exp(p))])
    y = y / y[-1]
    return np.clip(np.interp(np.log(np.clip(v, 1e-5, None)), np.log(np.r_[1e-5, NOEUDS]), y), 0, 1)


def charger(dossier, par_image=1000, graine=0):
    rng = np.random.default_rng(graine)
    X, J, I, E = [], [], [], set()
    fs = sorted(glob.glob(os.path.join(dossier, '*.npz')))
    for k, f in enumerate(fs):
        d = np.load(f)
        s = rng.choice(len(d['X']), min(len(d['X']), par_image), replace=False)
        X.append(d['X'][s]); J.append(d['J'][s]); I.append(np.full(len(s), k))
        E.add(str(d['espace']) if 'espace' in d else 'Display P3')  # premiers échantillons HNCS : P3
    assert len(E) == 1, f'espaces mélangés : {E}'
    return np.concatenate(X).astype(float), np.concatenate(J).astype(float), np.concatenate(I), fs, E.pop()


def ajuster(dossier, camspec):
    from scipy.optimize import least_squares
    X, J, I, fs, espace = charger(dossier)
    nI = len(fs)
    cible = colour.XYZ_to_Lab(colour.RGB_to_XYZ(eotf(J), colour.RGB_COLOURSPACES[espace], D65), D65)

    def lab(q, X, I):
        K = q[:9].reshape(3, 3)
        g = np.exp(q[9 + NK:])[I] if len(q) > 9 + NK else 1
        out = courbe(q[9:9 + NK], (X @ K.T) * np.atleast_1d(g)[..., None] if np.ndim(g) else X @ K.T)
        return colour.XYZ_to_Lab(colour.RGB_to_XYZ(eotf(out), SRGB, D65), D65)

    f = lambda q: (lab(q, X, I) - cible).ravel()
    q = np.r_[(SRGB.matrix_XYZ_to_RGB * 3).ravel(), np.zeros(NK)]
    q = least_squares(f, q, loss='soft_l1', f_scale=3, max_nfev=300).x       # 1) sans gains
    q = least_squares(f, np.r_[q, np.zeros(nI)], loss='soft_l1', f_scale=3, max_nfev=300).x  # 2) avec
    med = np.median(q[9 + NK:])  # gain médian = 1 (luminosité moyenne de HNCS), reporté dans K
    q[:9] *= np.exp(med)
    q[9 + NK:] -= med
    e = colour.delta_E(lab(q, X, I), cible, method='CIE 2000')
    K = q[:9].reshape(3, 3)
    # D40 : caméra équilibrée → XYZ D65 (sensibilités EPFL), puis K
    sens = ms.lire_camspec(camspec)
    rgb, xyz, _ = ms.donnees(sens, 'D65')
    M = ms.ajuster(rgb, xyz)
    KM = K @ M
    blanc = KM.sum(1)  # sortie de K·M pour le blanc parfait (1, 1, 1)
    g_blanc = blanc.mean()
    # transfert : même rendu de la ColorChecker par le D40 qu'à partir de son XYZ exact
    ref = lab(np.r_[q[:9 + NK]], xyz, np.zeros(24, int))
    d40 = lab(np.r_[KM.ravel(), q[9:9 + NK]], rgb, np.zeros(24, int))
    e_transfert = colour.delta_E(d40, ref, method='CIE 2000')
    v = np.linspace(0, 1, 4096)
    # en dessous du 1er centile des blocs mesurés, la courbe n'est pas mesurée : droite jusqu'au noir
    x0 = float(np.percentile((X @ K.T * np.exp(q[9 + NK:])[I][:, None]).mean(1), 1)) / g_blanc
    T = courbe(q[9:9 + NK], v * g_blanc)
    T = np.where(v < x0, v / x0 * np.interp(x0, v, T), T)
    return {
        'source': f'{nI} paires RAW+JPEG ({dossier}), JPEG {espace}, {len(X)} blocs ; D40 : camspec (Jiang et al. 2013)',
        'ajustement_dE2000': {'mediane': round(float(np.median(e)), 2), 'moyenne': round(float(e.mean()), 2),
                              'centile_90': round(float(np.percentile(e, 90)), 2)},
        'gains_par_image_IL': {os.path.basename(f)[:-4]: round(float(g / np.log(2)), 2) for f, g in zip(fs, q[9 + NK:])},
        'K_XYZ_vers_lineaire': K.round(5).tolist(),
        'M_D40_vers_XYZ': M.round(5).tolist(),
        'matrice_D40': (KM / blanc[:, None]).round(5).tolist(),
        'teinte_du_blanc': (blanc / g_blanc).round(4).tolist(),
        'gain_blanc': round(float(g_blanc), 5),
        'transfert_colorchecker_dE2000': {'moyenne': round(float(e_transfert.mean()), 2), 'max': round(float(e_transfert.max()), 2)},
        # courbe en entrée 0..1 = sortie de matrice_D40 (blanc = 1) ; T(gain_blanc · teinte · v)
        'entree_min_mesuree': round(x0, 5),
        'courbe': T.round(6).tolist(),
    }


# --- Étage à 16 secteurs (V1, octobre 2026) -----------------------------------------------------------------
BORNES_T = {'diag': (0.6, 1.6), 'croise': (-0.4, 0.4)}  # t1, t4 / 256 et t2, t3 / 256 : pas de « sapin de Noël »


def _sim():
    import simulateur
    return simulateur


def _lab_srgb(v):
    return colour.XYZ_to_Lab(colour.RGB_to_XYZ(eotf(np.clip(v, 0, 1)), SRGB, D65), D65)


def declinaisons():
    """F₁₃⁻¹ · F_n pour les 6 emplacements de balance IIIa (12 à 17) : la matrice livrée à l'emplacement n vaut
    M_D40 · F₁₃⁻¹ · F_n (recettes_v1.decliner)."""
    sm = _sim()
    F, _ = sm.tables(sm.firmware())
    return [np.linalg.inv(F[13]) @ F[n] for n in range(12, 18)]


def penalite_matrice(K, M, A, borne, poids):
    """Coefficients (échelle 512) des 6 matrices déclinées de K·M (lignes ramenées au blanc) au-delà de `borne` :
    résidus poids · max(0, |c| − borne), nuls sous la borne."""
    KM = K @ M
    D = KM / KM.sum(1)[:, None]
    c = 512 * np.concatenate([(D @ a).ravel() for a in A])
    return poids * np.maximum(0, np.abs(c) - borne)


def ajuster_etage(dossier, camspec, lissage=1.0, par_image=600, graine=0, iterations=200, borne_matrice=None):
    """Ajuste K (3x3), la courbe T (NK nœuds) et un jeu de 64 valeurs de l'étage, plus un gain par image :
    code sRGB = étage(T(K · XYZ · g_image)). Régularisation : écart entre secteurs voisins (t/256, poids `lissage`)
    et rappel vers le neutre (poids lissage/5), en racine du nombre d'échantillons pour rester à l'échelle des ΔE.
    Données : 3 images sur 4 en entraînement, la 4e tenue à part (on n'y ajuste que son gain).
    borne_matrice : |coefficient| maximal (échelle 512) des 6 matrices déclinées pour le D40 ; le registre de la puce
    n'accepte que 10 bits + signe (≤ 1 023). Contrainte par pénalité, dans toutes les passes ; la saturation que la
    matrice ne peut plus porter passe à la courbe et à l'étage."""
    from scipy.optimize import least_squares
    from scipy.sparse import lil_matrix
    sm = _sim()
    X, J, I, fs, espace = charger(dossier, par_image, graine)
    cible = colour.XYZ_to_Lab(colour.RGB_to_XYZ(eotf(J), colour.RGB_COLOURSPACES[espace], D65), D65)
    test_img = np.arange(len(fs)) % 4 == 3
    tr, te = ~test_img[I], test_img[I]
    ordre = np.argsort(sm.NOEUDS)  # voisins en angle
    neutre = np.array(sm.NEUTRE, float) / 256

    def sortie(K, pc, jeu, X, g):
        lin = courbe(pc, (X @ K.T) * g[:, None])
        return sm.etage(lin, None if jeu is None else np.asarray(jeu) * 256)

    def modele(q, avec_etage, Xs, Is, imgs):
        K = q[:9].reshape(3, 3); pc = q[9:9 + NK]
        o = 9 + NK
        jeu = None
        if avec_etage:
            jeu = q[o:o + 64]; o += 64
        g = np.ones(len(fs)); g[imgs] = np.exp(q[o:o + len(imgs)])
        return sortie(K, pc, jeu, Xs, g[Is]), jeu

    def regul(jeu, n):
        if jeu is None:
            return np.zeros(0)
        t = jeu.reshape(4, 16)[:, ordre]
        d = np.diff(np.c_[t, t[:, :1]], axis=1).ravel()
        return np.sqrt(n) * lissage * np.r_[d, 0.2 * (jeu - neutre)]

    sens = ms.lire_camspec(camspec)
    rgb, xyz, _ = ms.donnees(sens, 'D65')
    M = ms.ajuster(rgb, xyz)
    A = declinaisons()

    def pen(q, n):
        if borne_matrice is None:
            return np.zeros(0)
        return penalite_matrice(q[:9].reshape(3, 3), M, A, borne_matrice, np.sqrt(n))

    imgs_tr = np.flatnonzero(~test_img)
    # 1re passe sans gain par image (comme ajuster()), sinon des images partent loin et ne reviennent pas
    def ajuste_global():
        Xs, cs = X[tr], cible[tr]
        f = lambda q: np.r_[(_lab_srgb(sortie(q[:9].reshape(3, 3), q[9:], None, Xs, np.ones(len(Xs)))) - cs).ravel(), pen(q, len(Xs))]
        q0 = np.r_[(SRGB.matrix_XYZ_to_RGB * 3).ravel(), np.zeros(NK)]
        return least_squares(f, q0, loss='soft_l1', f_scale=3, max_nfev=iterations).x

    def ajuste(avec_etage, q0=None, poids=None):
        """Sans étage : perte robuste (soft_l1). Avec étage : moindres carrés pondérés (poids robustes tirés de
        l'ajustement sans étage), pour que la régularisation reste quadratique (voisins lisses, pas de marches)."""
        imgs = imgs_tr
        Xs, Is, cs = X[tr], I[tr], cible[tr]
        n = len(Xs)
        wv = np.ones(3 * n) if poids is None else np.repeat(poids, 3)

        def f(q):
            out, jeu = modele(q, avec_etage, Xs, Is, imgs)
            return np.r_[wv * (_lab_srgb(out) - cs).ravel(), regul(jeu, n), pen(q, n)]
        if q0 is None:
            q0 = np.r_[(SRGB.matrix_XYZ_to_RGB * 3).ravel(), np.zeros(NK), neutre if avec_etage else [], np.zeros(len(imgs))]
        ng = 9 + NK + (64 if avec_etage else 0)
        lb = np.full(len(q0), -np.inf); ub = np.full(len(q0), np.inf)
        if avec_etage:
            for k in range(4):
                b = BORNES_T['diag' if k in (0, 3) else 'croise']
                lb[9 + NK + 16 * k:9 + NK + 16 * k + 16], ub[9 + NK + 16 * k:9 + NK + 16 * k + 16] = b
            q0 = np.clip(q0, lb + 1e-9, ub - 1e-9)
        # parcimonie : le gain d'une image ne touche que ses échantillons
        nr = 3 * n + (len(regul(q0[9 + NK:9 + NK + 64], n)) if avec_etage else 0) + len(pen(q0, n))
        S = lil_matrix((nr, len(q0)), dtype=int)
        S[:, :ng] = 1
        pos = {im: k for k, im in enumerate(imgs)}
        lignes = np.repeat(np.arange(n), 3) * 3 + np.tile(np.arange(3), n)
        colonnes = ng + np.repeat(np.array([pos[i] for i in Is]), 3)
        S[lignes, colonnes] = 1
        r = least_squares(f, q0, jac_sparsity=S, loss='linear' if avec_etage else 'soft_l1', f_scale=3,
                          max_nfev=iterations, bounds=(lb, ub), x_scale='jac')
        return r.x

    def ecart_test(q, avec_etage):
        """Tenue à part : modèle figé, seul le gain de chaque image testée est ajusté (exposition)."""
        from scipy.optimize import minimize_scalar
        imgs = np.flatnonzero(test_img)
        es = []
        for im in imgs:
            m = I == im
            if m.sum() == 0:
                continue
            def e(lg):
                qq = np.r_[q[:9 + NK + (64 if avec_etage else 0)], np.full(len(np.flatnonzero(~test_img)), 0.0)]
                K = qq[:9].reshape(3, 3); pc = qq[9:9 + NK]; jeu = qq[9 + NK:9 + NK + 64] if avec_etage else None
                out = sortie(K, pc, jeu, X[m], np.full(m.sum(), np.exp(lg)))
                return colour.delta_E(_lab_srgb(out), cible[m], method='CIE 2000')
            lg = minimize_scalar(lambda lg: np.median(e(lg)), bounds=(-2, 2), method='bounded').x
            es.append(e(lg))
        return np.concatenate(es)

    def ecart_train(q, avec_etage):
        out, _ = modele(q, avec_etage, X[tr], I[tr], np.flatnonzero(~test_img))
        return colour.delta_E(_lab_srgb(out), cible[tr], method='CIE 2000')

    q_av = ajuste(False, np.r_[ajuste_global(), np.zeros(len(imgs_tr))])
    e_av = np.linalg.norm(_lab_srgb(modele(q_av, False, X[tr], I[tr], imgs_tr)[0]) - cible[tr], axis=1)
    poids = (1 + (e_av / 3) ** 2) ** -0.25  # poids IRLS de la perte soft_l1 (f_scale 3)
    q_ap = ajuste(True, np.r_[q_av[:9 + NK], neutre, q_av[9 + NK:]], poids)
    stats = lambda e: {'mediane': round(float(np.median(e)), 2), 'centile_90': round(float(np.percentile(e, 90)), 2)}
    res = {'avant': {'entrainement': stats(ecart_train(q_av, False)), 'tenu_a_part': stats(ecart_test(q_av, False))},
           'apres': {'entrainement': stats(ecart_train(q_ap, True)), 'tenu_a_part': stats(ecart_test(q_ap, True))}}
    # transfert au D40, comme ajuster() : matrice K·M_D40 (lignes = blanc), courbe T(gain_blanc · v)
    K = q_ap[:9].reshape(3, 3); pc = q_ap[9:9 + NK]; jeu = q_ap[9 + NK:9 + NK + 64]
    KM = K @ M
    blanc = KM.sum(1); g_blanc = blanc.mean()
    gains = q_ap[9 + NK + 64:]
    Xtr = X[tr]
    x0 = float(np.percentile((Xtr @ K.T * np.exp(gains)[np.searchsorted(np.flatnonzero(~test_img), I[tr])][:, None]).mean(1), 1)) / g_blanc
    v = np.linspace(0, 1, 4096)
    T = courbe(pc, v * g_blanc)
    T = np.where(v < x0, v / x0 * np.interp(x0, v, T), T)
    # transfert ColorChecker avec l'étage
    ref = _lab_srgb(sortie(K, pc, jeu, xyz, np.ones(24)))
    d40 = _lab_srgb(sortie(KM, pc, jeu, rgb, np.ones(24)))
    e_tr = colour.delta_E(d40, ref, method='CIE 2000')
    jeu_int = np.round(jeu * 256).astype(int)
    return {'source': f'{len(fs)} paires ({dossier}), JPEG {espace} ; tenues à part : 1 image sur 4 ({int(test_img.sum())})',
            'lissage': lissage, 'borne_matrice': borne_matrice, 'dE2000': res,
            'coef_max_declines': int(np.ceil(np.abs(512 * np.concatenate([(KM / blanc[:, None] @ a).ravel() for a in A])).max())),
            'transfert_colorchecker_dE2000': {'moyenne': round(float(e_tr.mean()), 2), 'max': round(float(e_tr.max()), 2)},
            'matrice_D40': (KM / blanc[:, None]).round(5).tolist(), 'teinte_du_blanc': (blanc / g_blanc).round(4).tolist(),
            'entree_min_mesuree': round(x0, 5), 'courbe': T.round(6).tolist(), 'secteurs': jeu_int.tolist(),
            'parametres': {'K': K.tolist(), 'courbe_noeuds': pc.tolist(), 'etage': jeu.tolist(), 'gains': gains.tolist(),
                           'images_tenues_a_part': np.flatnonzero(test_img).tolist(), 'graine': graine, 'par_image': par_image},
            'voisins_max': int(np.abs(np.diff(np.c_[jeu_int.reshape(4, 16)[:, ordre], jeu_int.reshape(4, 16)[:, ordre][:, :1]], axis=1)).max())}


def noter_courbes_d40(dossier, mesure, courbes, seuil=2 ** -1.5):
    """ΔE2000 d'un ajustement `rendus.py etage` (mesure = son JSON, avec 'parametres') quand on remplace sa courbe
    par des courbes au format D40 (4 096 valeurs 0..4095, entrée = sortie de la matrice D40, blanc capteur = 1),
    par exemple la même avec une épaule. Retour : {nom: {entrainement, tenu_a_part} × {tout, hors_hautes_lumieres}},
    « hautes lumières » = un canal au-dessus de `seuil` (−1,5 IL sous la pleine échelle) à l'entrée de la courbe."""
    from scipy.optimize import minimize_scalar
    sm = _sim()
    pa = mesure['parametres']
    X, J, I, fs, espace = charger(dossier, pa['par_image'], pa['graine'])
    cible = colour.XYZ_to_Lab(colour.RGB_to_XYZ(eotf(J), colour.RGB_COLOURSPACES[espace], D65), D65)
    K, pc, jeu = np.array(pa['K']), np.array(pa['courbe_noeuds']), np.array(pa['etage']) * 256
    test = np.zeros(len(fs), bool); test[pa['images_tenues_a_part']] = True
    g = np.ones(len(fs)); g[~test] = np.exp(pa['gains'])
    # facteur d'échelle entre l'entrée de T (ajustement) et celle de la courbe D40 : T(x) = C(x / S) / 4095
    C0 = np.asarray(courbes[next(iter(courbes))], float)
    xs = np.geomspace(0.05, 0.6, 50)
    T0 = courbe(pc, xs)
    S = float(np.median([np.interp(t, C0 / 4095, np.arange(4096) / 4095) for t in T0] / np.maximum(xs, 1e-9)) ** -1)
    v = np.arange(4096) / 4095
    sortie = lambda C, Xs, gs: sm.etage(np.interp(np.clip((Xs @ K.T) * gs[:, None] / S, 0, 1), v, np.asarray(C, float) / 4095), jeu)
    lab = lambda o: colour.XYZ_to_Lab(colour.RGB_to_XYZ(eotf(np.clip(o, 0, 1)), SRGB, D65), D65)
    # gains des images tenues à part : ajustés avec la première courbe, puis gardés (on isole l'effet de la courbe)
    for k in np.flatnonzero(test):
        m = I == k
        if m.any():
            e = lambda lg: np.median(colour.delta_E(lab(sortie(C0, X[m], np.full(m.sum(), np.exp(lg)))), cible[m], method='CIE 2000'))
            g[k] = np.exp(minimize_scalar(e, bounds=(-3, 3), method='bounded').x)
    haut = ((X @ K.T) * g[I][:, None] / S).max(1) > seuil
    res = {'facteur_entree': round(S, 4), 'part_hautes_lumieres': round(float(haut.mean()), 3)}
    for nom, C in courbes.items():
        e = colour.delta_E(lab(sortie(C, X, g[I])), cible, method='CIE 2000')
        st = lambda m: round(float(np.median(e[m])), 2) if m.any() else None
        res[nom] = {'entrainement': {'tout': st(~test[I]), 'hors_hautes_lumieres': st(~test[I] & ~haut), 'hautes_lumieres': st(~test[I] & haut)},
                    'tenu_a_part': {'tout': st(test[I]), 'hors_hautes_lumieres': st(test[I] & ~haut), 'hautes_lumieres': st(test[I] & haut)}}
    return res


def patch(chemin_mesure, groupe=0):
    G = {'matrices': range(6 * groupe, 6 * groupe + 6), 'courbes': range(7 * groupe, 7 * groupe + 7), 'reference': 7 * groupe + 3}
    m = json.loads(pathlib.Path(chemin_mesure).read_text())
    b = courbes.FIRMWARE.read_bytes()
    fw = courbes.courbes(b)
    ref = np.array(fw[G['reference']], float)
    T = np.array(m['courbe']) * 4095
    # même exposition que le D40 : un gris que la courbe de référence rend 118/255 (le gris 18 % en sRGB)
    # garde ce rendu ; T est étirée en entrée pour passer par ce point, sa forme (le contraste) reste HNCS.
    v = np.arange(4096) / 4095
    gris = 118 / 255 * 4095
    k = int(np.searchsorted(ref, gris))
    x_T = np.interp(gris, T, v)
    etire = np.interp(v * x_T / (k / 4095), v, T)
    patchs, ecarts = [], []
    pt = lambda adr, avant, apres: {'offset': hex(adr - courbes.BASE), 'avant': {'hex': avant.hex()}, 'apres': {'hex': apres.hex()}}
    for n in G['courbes']:
        cible = np.clip(etire + (np.array(fw[n], float) - ref), 0, 4095)  # garde l'écart des crans de tonalité
        cible = np.maximum.accumulate(cible)
        y0, y1, octets, ecart, y = courbes.encoder(list(cible))
        ecarts.append(ecart)
        d, a0, a1 = courbes.emplacement(n)
        patchs += [pt(d, courbes.lire(b, d, courbes.N_OCTETS), octets), pt(a0, courbes.lire(b, a0), bytes([y0])),
                   pt(a1, courbes.lire(b, a1), bytes([y1]))]
    mat = np.array(m['matrice_D40'])
    entiers = np.round(mat * 512).astype(int)
    entiers[:, 1] += 512 - entiers.sum(1)  # lignes = 512 exactement (le blanc reste blanc)
    neuf = struct.pack('>9h', *entiers.ravel())
    for n in G['matrices']:
        a = ms.MATRICES + 18 * n
        patchs.append(pt(a, courbes.lire(b, a, 18), neuf))
    return {'description': f"{pathlib.Path(chemin_mesure).stem} en mode couleur {['Ia', 'II', 'IIIa'][groupe]} : matrices {G['matrices'].start}-{G['matrices'].stop - 1} = {entiers.tolist()} ; courbes {G['courbes'].start}-{G['courbes'].stop - 1} = "
                           f"HNCS + écart des crans de tonalité du D40, gris 118/255 à l'entrée {k}/4095 comme la courbe "
                           f"{G['reference']} ; écart d'encodage max {max(ecarts):.1f}/4095 ; ajustement "
                           f"{m['ajustement_dE2000']}, transfert ColorChecker {m['transfert_colorchecker_dE2000']}",
            'patchs': patchs}


def self_test():
    p = np.zeros(NK)
    v = np.linspace(0, 1.2, 50)
    c = courbe(p, v)
    assert (np.diff(c) >= 0).all() and c[0] == 0 and abs(c[-1] - 1) < 1e-9
    assert abs(eotf(np.array([1.0]))[0] - 1) < 1e-9
    print('self-test OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['extraire', 'ajuster', 'patch', 'etage'])
    ap.add_argument('--lissage', type=float, default=1.0)
    ap.add_argument('--borne-matrice', type=float, help='|coef| max des matrices déclinées, échelle 512 (registre : 1 023)')
    ap.add_argument('args', nargs='*')
    ap.add_argument('--groupe', type=int, default=0, help='mode couleur : 0 Ia, 1 II, 2 IIIa (celui du préréglage Normal)')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.action == 'extraire':
        extraire(*a.args)
    elif a.action == 'ajuster':
        print(json.dumps(ajuster(*a.args), ensure_ascii=False, indent=1))
    elif a.action == 'etage':
        print(json.dumps(ajuster_etage(a.args[0], a.args[1], a.lissage, borne_matrice=a.borne_matrice), ensure_ascii=False))
    elif a.action == 'patch':
        print(json.dumps(patch(a.args[0], a.groupe), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.exit(main())
