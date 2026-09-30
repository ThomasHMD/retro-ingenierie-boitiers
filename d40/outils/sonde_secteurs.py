#!/usr/bin/env python3
"""Mesure de la sonde des secteurs de teinte (patchs/sonde-secteurs-ia.json) sur des NEF du D40.

Pour chaque NEF, le JPEG du boîtier (dans le NEF) est comparé au rendu attendu du firmware
d'origine (outils/simulateur.py) : rapport de chroma et décalage de teinte, en fonction de l'angle
de teinte dans le plan Cb/Cr. Les NEF en IIIa (non patché) servent de témoin pour corriger le biais
du simulateur. Puis ajustement du modèle : 16 nœuds (un sur deux coupé), interpolation linéaire
entre nœuds, angle calculé sur (Cb, k·Cr) après rotation a, nœud 0 à phi.

  python3 -P outils/sonde_secteurs.py sondes/sonde-1/*/*.NEF [--figure recettes/mesures/sonde-secteurs-resultat.png]
"""
import argparse, pathlib, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import simulateur as sm


def ycc(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return -.168736 * r - .331264 * g + .5 * b, .5 * r - .418688 * g - .081312 * b


def mesure(nef, mats, cs):
    from PIL import Image
    r = sm.reglages(nef)
    g = sm.GROUPE[r['mode']]
    cam = sm.camera(nef, tourner=False)
    sim = sm.rendre(cam, mats[sm.MATRICE_DEFAUT[g]], cs[7 * g + sm.CRAN[r['tons']]], sm.SATURATION.get(r['saturation'], 1))
    J = np.asarray(sm.jpeg_boitier(nef).resize((cam.shape[1], cam.shape[0]), Image.BOX), np.float32) / 255
    F = 4
    h, w = J.shape[0] // F * F, J.shape[1] // F * F
    bl = lambda a: a[:h, :w].reshape(h // F, F, w // F, F, 3)
    jb, sb = bl(J), bl(sim)
    ok = (jb.std((1, 3)).mean(-1) < .02) & (sb.mean((1, 3)).max(-1) < .97) & (sb.mean((1, 3)).min(-1) > .02)
    cbs, crs = ycc(sb.mean((1, 3))[ok])
    cbj, crj = ycc(jb.mean((1, 3))[ok])
    c = np.hypot(cbs, crs)
    k = c > .06
    th = np.degrees(np.arctan2(crs, cbs))[k] % 360
    return r['mode'], th, np.hypot(cbj, crj)[k] / c[k], ((np.degrees(np.arctan2(crj, cbj))[k] - th + 180) % 360) - 180


def modele(p, th):
    k, phi, a = p
    t = np.radians(th + a)
    x = ((np.degrees(np.arctan2(k * np.sin(t), np.cos(t))) - phi) % 360) / 22.5
    i = np.floor(x).astype(int)
    f = x - i
    garde = lambda j: (j % 2 == 0).astype(float)
    return garde(i) * (1 - f) + garde(i + 1) * f


def noeuds(p):
    k, phi, a = p
    ap = np.radians(phi + 22.5 * np.arange(16))
    return (np.degrees(np.arctan2(np.sin(ap) / k, np.cos(ap))) - a) % 360


def main():
    from scipy.optimize import minimize
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('nefs', nargs='+')
    ap.add_argument('--figure')
    a = ap.parse_args()
    mats, cs = sm.tables(sm.firmware())
    m = {'Mode1a': [], 'Mode3a': []}
    for nef in a.nefs:
        if sm.reglages(nef)['mode'] not in m:
            continue
        mode, th, ra, dt = mesure(nef, mats, cs)
        m[mode].append((th, ra, dt))
        print(f'{pathlib.Path(nef).name} {mode} : {len(th)} blocs, chroma ×{np.median(ra):.2f}, rotation {np.median(dt):+.1f}°')
    cat = lambda L, i: np.concatenate([x[i] for x in L])
    tI, rI, tC, rC = cat(m['Mode1a'], 0), cat(m['Mode1a'], 1), cat(m['Mode3a'], 0), cat(m['Mode3a'], 1)
    b = np.arange(0, 361, 2)
    c = (b[:-1] + b[1:]) / 2
    med = lambda t, r: np.array([np.median(r[(t >= b[i]) & (t < b[i + 1])]) if ((t >= b[i]) & (t < b[i + 1])).sum() > 20 else np.nan for i in range(180)])
    ctrl = med(tC, rC)
    ctrl = np.where(np.isnan(ctrl), np.nanmedian(ctrl), ctrl)
    norm = rI / np.interp(tI, c, ctrl, period=360)
    cout = lambda p: np.median(np.abs(modele(p, tI) - norm))
    best = min((minimize(cout, [k, phi, r0], method='Nelder-Mead') for k in (.7, 1, 1.4) for phi in range(0, 45, 5) for r0 in (0, 30, 60)), key=lambda r: r.fun)
    print(f'modèle : k = {best.x[0]:.2f}, phi = {best.x[1]:.1f}°, a = {best.x[2]:.1f}° ; écart médian {best.fun:.3f}')
    print('nœuds (angle Cb/Cr) :', ' '.join(f'{v:.0f}' for v in noeuds(best.x)))
    if a.figure:
        figure(a.figure, c, med(tI, norm), best.x)


def figure(chemin, c, prof, p):
    """Courbe mesurée (points) et modèle (trait rouge), bande des teintes en bas ; PIL seul."""
    from PIL import Image, ImageDraw, ImageFont
    W, H, G, D, Hh, B = 1320, 520, 70, 20, 50, 90
    sx = lambda x: G + x / 360 * (W - G - D)
    sy = lambda y: Hh + (1.25 - y) / 1.35 * (H - Hh - B)
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 16)
    for x in range(360):
        t = np.radians(x)
        cb, cr = .12 * np.cos(t), .12 * np.sin(t)
        col = tuple(int(255 * v) for v in np.clip([.5 + 1.402 * cr, .5 - .344136 * cb - .714136 * cr, .5 + 1.772 * cb], 0, 1))
        d.rectangle((sx(x), sy(-.1), sx(x + 1), sy(-.1) + 18), fill=col)
    for j, v in enumerate(noeuds(p)):
        d.line((sx(v), sy(1.2), sx(v), sy(-.1)), fill=(150, 150, 150) if j % 2 == 0 else (220, 220, 220))
    for y in (0, .5, 1):
        d.line((G, sy(y), W - D, sy(y)), fill=(235, 235, 235))
        d.text((G - 40, sy(y) - 9), f'{y:.1f}', fill='black', font=f)
    xx = np.linspace(0, 360, 1441)
    d.line([(sx(x), sy(y)) for x, y in zip(xx, modele(p, xx))], fill=(220, 30, 30), width=2)
    for x, y in zip(c, prof):
        if not np.isnan(y):
            d.ellipse((sx(x) - 3, sy(y) - 3, sx(x) + 3, sy(y) + 3), fill='black')
    for x in range(0, 361, 45):
        d.text((sx(x) - 10, sy(-.1) + 24), f'{x}°', fill='black', font=f)
    d.text((G, 12), 'Sonde des secteurs du D40, mode Ia : chroma gardée selon la teinte (angle dans le plan Cb/Cr)', fill='black', font=f)
    d.text((G, H - 34), 'points : JPEG du boîtier / rendu attendu, corrigé par le témoin IIIa    rouge : modèle à 16 nœuds, un sur deux coupé, interpolation linéaire    traits gris : nœuds', fill=(80, 80, 80), font=f)
    im.save(chemin)

if __name__ == '__main__':
    main()
