#!/usr/bin/env python3
"""Table 3D d'un film simulé par spektrafilm (A. Volpato, github.com/andreavolpato/spektrafilm), pour servir de cible.

spektrafilm n'est pas dans le dépôt (code GPLv3, profils CC BY-SA 4.0, tables sous licence propre) : il s'installe à part
et la table produite reste hors du dépôt, désignée par la variable d'environnement D750_SPEKTRAFILM (dossier).
Usage personnel ; crédit : « film modeling powered by spektrafilm ».

  python3 d750_spektrafilm.py <film (ex. kodak_kodachrome_64)> <sortie.npz> [--n 33] [--sans-couplers] [--ev 0]
                              [--papier <profil>] [--surex <IL>]

Entrée de la table : scène XYZ D65 (gris de 18 % = 0,18) → ProPhoto RGB linéaire (Bradford) → log2(v / 0,18) ramené
de [-12, +4] sur [0, 1]. Sortie : CIELAB D65 du film inversible regardé directement (scan du film, `scan_film`),
effets spatiaux et aléatoires coupés (`lut_mode`), effets entre couches (DIR) actifs sauf --sans-couplers.
Rendu ABSOLU : la lumière transmise ou réfléchie rapportée à l'illuminant de visée (D50), le support sans image n'est
donc pas blanc (L* 83 à 88). La table garde aussi le blanc et le noir du support (`blanc`, `noir` : densités d'image 0
et maximales, lues par le même scan), pour le rendu RELATIF de `cible(…, relatif_=True)` (octobre 2026 ; le recalage du gris
à 118/255 qui le suit pour les cibles du X-T4 est fait dans xt4_cibles).
Négatif (--papier, octobre 2026, pour les cibles du X-T4) : spektrafilm n'inverse pas un négatif (`scan_film` rend le
négatif orangé tel quel) ; le seul chemin positif est le tirage : agrandisseur (TH-KG3, filtres neutres de la base de
spektrafilm, gris de 18 % neutre au tirage), papier, puis lecture du tirage sous son illuminant (D50). Le papier
conseillé par le profil du film est dans `info.target_print` (Ektar : Portra Endura ; Pro 400H : Crystal Archive II).
--surex : négatif surexposé de N IL à la prise de vue PUIS tiré normalement (exposition du tirage compensée, comme au
labo : `camera.exposure_compensation_ev` et `enlarger.print_exposure_compensation`). Le mode table de spektrafilm forçant
ces deux réglages à zéro, ses coupures (effets spatiaux, aléatoires, corrections dépendant de l'image) sont alors faites
à la main. --ev, lui, décale seulement l'entrée (diapositive sur- ou sous-exposée, regardée telle quelle).
"""
import sys

import numpy as np

LOG_MIN, LOG_MAX = -12.0, 4.0
# Bradford (adaptation chromatique du blanc du support au blanc D65)
M_BRADFORD = np.array([[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]])


def encoder(xyz):
    import colour
    D65 = colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65']
    rgb = colour.XYZ_to_RGB(np.asarray(xyz, float), 'ProPhoto RGB', illuminant=D65, chromatic_adaptation_transform='Bradford')
    lg = np.log2(np.maximum(rgb, 0.18 * 2 ** LOG_MIN) / 0.18)
    return np.clip((lg - LOG_MIN) / (LOG_MAX - LOG_MIN), 0, 1)


def decoder(code):
    return 0.18 * 2.0 ** (np.asarray(code) * (LOG_MAX - LOG_MIN) + LOG_MIN)


def parametres(film, papier=None, couplers=True, surex=0.0):
    from spektrafilm import init_params
    p = init_params(film_profile=film, **({'print_profile': papier} if papier else {}))
    p.io.scan_film = papier is None
    p.io.input_color_space = 'ProPhoto RGB'
    p.io.input_cctf_decoding = False
    p.camera.auto_exposure = False
    p.film_render.dir_couplers.active = couplers
    p.film_render.grain.active = False
    if surex:
        # ce que fait lut_mode (params_builder.digest_params), sans remettre l'exposition à zéro
        p.debug.lut_mode = False
        p.debug.deactivate_spatial_effects = True
        p.debug.deactivate_stochastic_effects = True
        p.camera.exposure_compensation_ev = float(surex)
        p.enlarger.print_exposure_compensation = True
        p.enlarger.print_exposure = 1.0
        p.film_render.halation.boost_ev = 0.0
        p.scanner.white_correction = False
        p.scanner.black_correction = False
        p.scanner.unsharp_mask = (0.0, 0.0)
    else:
        p.debug.lut_mode = True
    return p


def support(p):
    """Codes sRGB (absolus) du support sans image (densités 0 : blanc) et à densité maximale (noir), par le scan même
    de la table : film pour une diapositive, papier pour un tirage."""
    from spektrafilm.runtime.params_builder import digest_params
    from spektrafilm.runtime.process import Simulator
    s = Simulator(digest_params(p))
    pr = s._pipeline   # point d'injection public de la topologie (process(…, inject=…)), pas exposé par Simulator
    if p.io.scan_film:
        tap, dmax = 'cmy_film', np.nanmax(p.film.data.density_curves, axis=0)
    else:
        tap, dmax = 'cmy_print', np.nanmax(p.print.data.density_curves, axis=0)
    cmy = np.stack([np.zeros(3), dmax])[None]
    return np.asarray(pr.process(cmy, inject=tap)).reshape(2, 3)


def construire(film, n=33, couplers=True, ev=0.0, tuile=4, papier=None, surex=0.0):
    """papier : None = film inversible regardé directement ; sinon le profil du papier de tirage (négatif).
    surex : surexposition du négatif à la prise de vue, compensée au tirage (IL)."""
    from spektrafilm import simulate
    sys.path.insert(0, __file__.rsplit('/', 1)[0])
    import d750_modele as dm
    g = np.linspace(0, 1, n)
    B, G, R = np.meshgrid(g, g, g, indexing='ij')           # ordre [b][g][r] de fuji_lut.appliquer
    rgb = decoder(np.stack([R, G, B], -1).reshape(-1, 3)) * 2.0 ** ev   # lut_mode remet la compensation à 0 : on l'applique ici
    m = len(rgb)
    w = int(np.ceil(np.sqrt(m)))
    img = np.full((w * tuile, w * tuile, 3), 0.18, np.float32)
    for i, c in enumerate(rgb):
        y, x = divmod(i, w)
        img[y * tuile:(y + 1) * tuile, x * tuile:(x + 1) * tuile] = c
    p = parametres(film, papier, couplers, surex)
    out = simulate(img, p)
    c = out[tuile // 2::tuile, tuile // 2::tuile].reshape(-1, 3)[:m]
    lab = dm.code_lab(np.clip(c, 0, 1)).reshape(n, n, n, 3)
    bn = dm.code_lab(np.clip(support(parametres(film, papier, couplers, surex)), 0, 1))
    return {'lab': lab.astype(np.float32), 'film': film, 'couplers': couplers, 'ev': ev, 'log_min': LOG_MIN, 'log_max': LOG_MAX,
            'papier': papier or '', 'surex': float(surex), 'blanc': bn[0].astype(np.float32), 'noir': bn[1].astype(np.float32)}


def relatif(lab, blanc):
    """Lab absolu → Lab relatif au blanc du support : adaptation chromatique de Bradford du blanc du support (luminance
    comprise) vers le blanc D65 (Y = 1) ; le blanc du support sort à L* 100, a* = b* = 0. Le noir n'est pas recalé
    (pas de compensation du point noir) : il reste celui du support, éclairci du même facteur."""
    sys.path.insert(0, __file__.rsplit('/', 1)[0])
    import d750_modele as dm
    xw = dm.lab_xyz(np.asarray(blanc, float))
    M = np.linalg.inv(M_BRADFORD) @ np.diag((M_BRADFORD @ dm.BLANC) / (M_BRADFORD @ xw)) @ M_BRADFORD
    return dm.xyz_lab(dm.lab_xyz(lab) @ M.T)


def cible(chemin, chroma=1.0, relatif_=False):
    """Fonction XYZ → Lab lue dans une table produite par `construire` ; chroma : gain sur a*, b* (choix de goût, après le
    passage en relatif) ; relatif_ : blanc du support → L* 100 (il faut une table qui garde `blanc`)."""
    import fuji_lut as fl
    d = np.load(chemin)
    lut = d['lab']
    if relatif_ and 'blanc' not in d:
        raise ValueError(f'{chemin} : table sans blanc du support, à refaire avec d750_spektrafilm.py')
    blanc = d['blanc'] if relatif_ else None

    def f(xyz):
        L = fl.appliquer(lut, encoder(xyz))
        if blanc is not None:
            L = relatif(L, blanc)
        return np.stack([L[..., 0], chroma * L[..., 1], chroma * L[..., 2]], -1)
    return f


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        sys.exit(2)
    r = construire(a[0], n=int(a[a.index('--n') + 1]) if '--n' in a else 33, couplers='--sans-couplers' not in a,
                   ev=float(a[a.index('--ev') + 1]) if '--ev' in a else 0.0,
                   papier=a[a.index('--papier') + 1] if '--papier' in a else None,
                   surex=float(a[a.index('--surex') + 1]) if '--surex' in a else 0.0)
    np.savez_compressed(a[1], **r)
    print('écrit', a[1], r['lab'].shape, 'blanc', np.round(r['blanc'], 1), 'noir', np.round(r['noir'], 1))
