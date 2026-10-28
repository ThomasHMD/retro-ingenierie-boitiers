#!/usr/bin/env python3
"""Table 3D d'un film simulé par spektrafilm (A. Volpato, github.com/andreavolpato/spektrafilm), pour servir de cible.

spektrafilm n'est pas dans le dépôt (code GPLv3, profils CC BY-SA 4.0, tables sous licence propre) : il s'installe à part
et la table produite reste hors du dépôt, désignée par la variable d'environnement D750_SPEKTRAFILM (dossier).
Usage personnel ; crédit : « film modeling powered by spektrafilm ».

  python3 d750_spektrafilm.py <film (ex. kodak_kodachrome_64)> <sortie.npz> [--n 33] [--sans-couplers] [--ev 0]

Entrée de la table : scène XYZ D65 (gris de 18 % = 0,18) → ProPhoto RGB linéaire (Bradford) → log2(v / 0,18) ramené
de [-12, +4] sur [0, 1]. Sortie : CIELAB D65 du film inversible regardé directement (scan du film, `scan_film`),
effets spatiaux et aléatoires coupés (`lut_mode`), effets entre couches (DIR) actifs sauf --sans-couplers.
"""
import sys

import numpy as np

LOG_MIN, LOG_MAX = -12.0, 4.0


def encoder(xyz):
    import colour
    D65 = colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65']
    rgb = colour.XYZ_to_RGB(np.asarray(xyz, float), 'ProPhoto RGB', illuminant=D65, chromatic_adaptation_transform='Bradford')
    lg = np.log2(np.maximum(rgb, 0.18 * 2 ** LOG_MIN) / 0.18)
    return np.clip((lg - LOG_MIN) / (LOG_MAX - LOG_MIN), 0, 1)


def decoder(code):
    return 0.18 * 2.0 ** (np.asarray(code) * (LOG_MAX - LOG_MIN) + LOG_MIN)


def construire(film, n=33, couplers=True, ev=0.0, tuile=4):
    from spektrafilm import init_params, simulate
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
    p = init_params(film_profile=film)
    p.debug.lut_mode = True
    p.io.scan_film = True
    p.io.input_color_space = 'ProPhoto RGB'
    p.io.input_cctf_decoding = False
    p.camera.auto_exposure = False
    p.film_render.dir_couplers.active = couplers
    p.film_render.grain.active = False
    out = simulate(img, p)
    c = out[tuile // 2::tuile, tuile // 2::tuile].reshape(-1, 3)[:m]
    lab = dm.code_lab(np.clip(c, 0, 1)).reshape(n, n, n, 3)
    return {'lab': lab.astype(np.float32), 'film': film, 'couplers': couplers, 'ev': ev, 'log_min': LOG_MIN, 'log_max': LOG_MAX}


def cible(chemin, chroma=1.0):
    """Fonction XYZ → Lab lue dans une table produite par `construire` ; chroma : gain sur a*, b* (choix de goût)."""
    import fuji_lut as fl
    d = np.load(chemin)
    lut = d['lab']

    def f(xyz):
        L = fl.appliquer(lut, encoder(xyz))
        return np.stack([L[..., 0], chroma * L[..., 1], chroma * L[..., 2]], -1)
    return f


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        sys.exit(2)
    r = construire(a[0], n=int(a[a.index('--n') + 1]) if '--n' in a else 33, couplers='--sans-couplers' not in a,
                   ev=float(a[a.index('--ev') + 1]) if '--ev' in a else 0.0)
    np.savez_compressed(a[1], **r)
    print('écrit', a[1], r['lab'].shape)
