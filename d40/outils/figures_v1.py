#!/usr/bin/env python3
"""Figures de la V1 des rendus (recettes/v1/), en 1920 × 1080, légendes en français, PIL seul.

  figures_v1.py etage <valid-etage.txt>          ΔE par NEF des sondes : étage neutre / étage simulé
  figures_v1.py sonde <nef> <patch.json>          un NEF de sonde : boîtier, simulé sans étage, simulé avec
  figures_v1.py roue                              les 16 secteurs sur la roue des teintes (avant / après ajustement)
  figures_v1.py secteurs                          ce que l'étage fait pour Hasselblad, Chrome, Positive (recettes/v1)
  figures_v1.py ecarts                            ΔE2000 avant / après l'étage, entraînement et tenu à part
  figures_v1.py nb <camspec.txt>                  Tri-X et HP5 : courbes et mélanges de canaux
  figures_v1.py --self-test
"""
import argparse
import pathlib
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import simulateur as sm  # noqa: E402

ICI = pathlib.Path(__file__).resolve().parent.parent
V1 = ICI / 'recettes' / 'v1'
W, H = 1920, 1080
POLICE = '/System/Library/Fonts/Supplemental/Arial.ttf'
GRAS = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'


def police(t, gras=False):
    return ImageFont.truetype(GRAS if gras else POLICE, t)


def titre(d, texte, sous=None):
    d.text((60, 40), texte, fill=(20, 20, 20), font=police(46, True))
    if sous:
        d.text((60, 104), sous, fill=(90, 90, 90), font=police(28))


def barres(chemin, groupes, series, titre_, sous, unite='ΔE2000 médian', vmax=None, legende_pied=None, fmt='{:.1f}'):
    """groupes : libellés ; series : [(nom, couleur, valeurs)]."""
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    titre(d, titre_, sous)
    G, D, Hh, B = 140, 60, 200, 170
    vmax = vmax or max(max(v) for _, _, v in series) * 1.15
    sy = lambda y: Hh + (1 - y / vmax) * (H - Hh - B)
    for y in np.arange(0, vmax + 1e-9, 1 if vmax <= 8 else 2):
        d.line((G, sy(y), W - D, sy(y)), fill=(230, 230, 230), width=2)
        d.text((G - 50, sy(y) - 14), f'{y:g}', fill=(60, 60, 60), font=police(26))
    d.text((G - 80, Hh - 40), unite, fill=(60, 60, 60), font=police(26))
    n = len(groupes)
    larg = (W - G - D) / n
    bl = larg * 0.8 / len(series)
    for i, g in enumerate(groupes):
        x0 = G + i * larg + larg * 0.1
        for k, (nom, col, vals) in enumerate(series):
            v = vals[i]
            d.rectangle((x0 + k * bl, sy(v), x0 + (k + 1) * bl - 4, sy(0)), fill=col)
            if larg > 90:
                d.text((x0 + k * bl + 2, sy(v) - 30), fmt.format(v), fill=(40, 40, 40), font=police(22 if larg < 200 else 28))
        f = police(22 if larg < 120 else 28)
        tw = d.textlength(g, font=f)
        d.text((G + i * larg + larg / 2 - tw / 2, sy(0) + 12), g, fill=(30, 30, 30), font=f)
    x = G
    y_leg = H - 100 if legende_pied else H - 70
    for nom, col, _ in series:
        d.rectangle((x, y_leg + 2, x + 34, y_leg + 32), fill=col)
        d.text((x + 46, y_leg), nom, fill=(30, 30, 30), font=police(30))
        x += 60 + d.textlength(nom, font=police(30)) + 40
    if legende_pied:
        d.text((G, H - 52), legende_pied, fill=(110, 110, 110), font=police(26))
    im.save(chemin)


def fig_etage(fichier):
    lignes = [l for l in pathlib.Path(fichier).read_text().splitlines() if 'ΔE2000' in l]
    noms, a, b = [], [], []
    for l in lignes:
        m = re.match(r'(\S+) (\S+) : ΔE2000 médiane étage neutre ([\d.]+) → étage du patch ([\d.]+)', l)
        nom, mode = m.group(1), {'Mode1a': 'Ia', 'Mode2': 'II'}[m.group(2)]
        noms.append(nom.replace('.NEF', '').replace('DSC_', '').replace('_DSC', '') + f'\n{mode}')
        a.append(float(m.group(3))); b.append(float(m.group(4)))
    noms = [n.split('\n')[0] for n in noms]
    barres(V1 / 'etage-validation.png', noms,
           [('simulateur sans l’étage', (190, 190, 190), a), ('simulateur avec l’étage à 16 secteurs', (40, 110, 200), b)],
           'L’étage à 16 secteurs ajouté au simulateur',
           'Écart entre le JPEG du D40 flashé (sondes 1 et 2) et le simulateur, photo par photo : plus bas = plus fidèle',
           legende_pied='6219–6233 : sonde 1 (Ia) · 6243–6247 : sonde 2 (Ia) · 6248–6251 : sonde 2 (II)')


def fig_sonde(nef, patch):
    b = sm.firmware(patch)
    mats, cs = sm.tables(b)
    jeux = sm.jeux_secteurs(b)
    r = sm.reglages(nef)
    g = sm.GROUPE[r['mode']]
    n = sm.MATRICE_DEFAUT[g]
    cam = sm.camera(nef, tourner=False)
    base = sm.rendre(cam, mats[n], cs[7 * g + sm.CRAN[r['tons']]], sm.SATURATION.get(r['saturation'], 1))
    vues = [('D40 flashé (JPEG du boîtier)', np.asarray(sm.jpeg_boitier(nef).resize((cam.shape[1], cam.shape[0]), Image.BOX), np.float32) / 255),
            ('Simulateur sans l’étage', base),
            ('Simulateur avec l’étage', sm.etage(base, jeux[n]))]
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    titre(d, 'Sonde des secteurs : le simulateur reproduit le boîtier',
          'Une teinte sur deux coupée dans le firmware (secteurs impairs) : la roue sort avec des rayons gris')
    w = (W - 4 * 40) // 3
    for k, (t, a) in enumerate(vues):
        p = Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8))
        p = p.crop((0, 0, int(p.width * 0.52), p.height))  # la roue seule (le reste de l'écran photographié n'apporte rien)
        p = p.resize((w, int(w * p.height / p.width)), Image.LANCZOS)
        x = 40 + k * (w + 40)
        im.paste(p, (x, 170))
        d.text((x, 170 + p.height + 14), t, fill=(30, 30, 30), font=police(32, True))
    im.save(V1 / 'etage-sonde-avant-apres.jpg', quality=92)


def fig_roue():
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    titre(d, 'Les 16 secteurs de teinte du D40', 'Plan Cb/Cr (YCbCr BT.601) : numéro du secteur au centre de sa teinte')
    cx, cy, R = 700, 600, 400
    yy, xx = np.mgrid[-R:R, -R:R]
    rr = np.hypot(xx, yy) / R
    th = np.arctan2(-yy, xx)
    cb, cr = 0.22 * rr * np.cos(th), 0.22 * rr * np.sin(th)
    rgb = np.clip(sm.rgb(np.full_like(cb, .55), cb, cr), 0, 1)
    rgb[rr > 1] = 1
    im.paste(Image.fromarray((rgb * 255).astype(np.uint8)), (cx - R, cy - R))
    for k, a in enumerate(sm.NOEUDS_V0):
        t = np.radians(a)
        d.line((cx, cy, cx + R * np.cos(t), cy - R * np.sin(t)), fill=(150, 150, 150), width=2)
    for k, a in enumerate(sm.NOEUDS):
        t = np.radians(a)
        d.line((cx, cy, cx + (R + 10) * np.cos(t), cy - (R + 10) * np.sin(t)), fill=(20, 20, 20), width=4)
        tx, ty = cx + (R + 50) * np.cos(t), cy - (R + 50) * np.sin(t)
        s = str(k)
        f = police(34, True)
        d.text((tx - d.textlength(s, font=f) / 2, ty - 20), s, fill=(20, 20, 20), font=f)
    x = 1250
    lignes = ['Trait noir : centre d’un secteur (ajusté', 'sur les deux sondes, octobre 2026)',
              'Trait gris : lecture d’avant (sonde 1 seule)', '',
              'Secteur 0 = 184° (jaune-vert), et non 163° :', 'la première lecture était décalée d’un cran.', '',
              'Entre deux traits, le boîtier mélange', 'les réglages des deux secteurs voisins.', '',
              'Rouge ≈ 104° (secteur 13)', 'Jaune ≈ 166° (secteur 15)', 'Vert ≈ 223–246° (secteurs 2–3)',
              'Bleu ≈ 346° (secteur 7)', 'Magenta ≈ 44° (secteur 10)']
    for i, l in enumerate(lignes):
        d.text((x, 230 + 44 * i), l, fill=(40, 40, 40), font=police(30))
    im.save(V1 / 'roue-secteurs.png')


def fond_roue(R, rayon_max=0.22, y=.55):
    yy, xx = np.mgrid[-R:R, -R:R]
    rr = np.hypot(xx, yy) / R
    th = np.arctan2(-yy, xx)
    rgb = np.clip(sm.rgb(np.full_like(rr, y), rayon_max * rr * np.cos(th), rayon_max * rr * np.sin(th)), 0, 1)
    rgb = 0.35 + 0.65 * rgb  # pâli pour que les flèches se lisent
    rgb[rr > 1] = 1
    return Image.fromarray((rgb * 255).astype(np.uint8))


def fig_secteurs():
    import json
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    titre(d, 'Ce que l’étage à 16 secteurs fait à chaque teinte',
          'Flèche : où va une couleur moyennement saturée (départ = point, arrivée = pointe), plan Cb/Cr ; longueur des flèches ×3')
    R, k_rayon = 270, 0.16
    for i, (nom, lib) in enumerate((('hasselblad', 'Hasselblad (HNCS)'), ('chrome', 'Classic Chrome'), ('positive', 'Positive Film'))):
        r = json.loads((V1 / f'{nom}.json').read_text())
        jeu = r['secteurs'][1]
        cx, cy = 330 + i * 630, 560
        im.paste(fond_roue(R), (cx - R, cy - R))
        f = police(34, True)
        d.text((cx - d.textlength(lib, font=f) / 2, cy + R + 30), lib, fill=(20, 20, 20), font=f)
        for a in np.arange(0, 360, 7.5):
            t1, t2, t3, t4 = [float(v[0]) for v in sm.coefficients(np.array([a], float), jeu)]
            cb, cr = k_rayon * np.cos(np.radians(a)), k_rayon * np.sin(np.radians(a))
            cb2, cr2 = t1 * cb + t2 * cr, t3 * cb + t4 * cr
            cb3, cr3 = cb + 3 * (cb2 - cb), cr + 3 * (cr2 - cr)
            s = R / 0.22
            x0, y0, x1, y1 = cx + s * cb, cy - s * cr, cx + s * cb3, cy - s * cr3
            d.line((x0, y0, x1, y1), fill=(20, 20, 20), width=3)
            d.ellipse((x0 - 4, y0 - 4, x0 + 4, y0 + 4), fill=(20, 20, 20))
            ang = np.arctan2(y1 - y0, x1 - x0)
            if np.hypot(x1 - x0, y1 - y0) > 6:
                for da in (np.radians(150), -np.radians(150)):
                    d.line((x1, y1, x1 + 12 * np.cos(ang + da), y1 + 12 * np.sin(ang + da)), fill=(20, 20, 20), width=3)
    d.text((60, H - 60), 'Flèche vers le centre : couleur désaturée ; vers l’extérieur : plus saturée ; de côté : teinte qui tourne.',
           fill=(90, 90, 90), font=police(28))
    im.save(V1 / 'secteurs-rendus.png')


def fig_ecarts():
    import json
    groupes, s = [], {k: [] for k in ('aa', 'ap', 'ta', 'tp')}
    for nom, lib in (('hasselblad', 'Hasselblad'), ('chrome', 'Classic Chrome'), ('positive', 'Positive Film')):
        e = json.loads((V1 / f'{nom}.json').read_text())['delta_e']['ajustement_paires_dE2000']
        groupes.append(lib)
        s['aa'].append(e['avant']['entrainement']['mediane']); s['ap'].append(e['apres']['entrainement']['mediane'])
        s['ta'].append(e['avant']['tenu_a_part']['mediane']); s['tp'].append(e['apres']['tenu_a_part']['mediane'])
    barres(V1 / 'ecarts-rendus.png', groupes,
           [('sans étage', (200, 200, 200), s['aa']), ('avec étage', (120, 160, 210), s['ap']),
            ('sans étage, tenues à part', (150, 150, 150), s['ta']), ('avec étage, tenues à part', (30, 90, 180), s['tp'])],
           'Rendus mesurés : ce que gagne l’étage à 16 secteurs',
           'Écart médian entre le rendu du boîtier d’origine et sa copie pour le D40 (paires RAW + JPEG de Thomas)', vmax=2.5,
           legende_pied='« Sans étage » = matrice + courbe. Tenues à part : 1 photo sur 4, jamais vue pendant l’ajustement. '
                        'ΔE2000 < 1 : à peine visible.', fmt='{:.2f}')


def fig_nb(camspec):
    import json
    import films_nb as fn
    m, cs = sm.tables(sm.firmware())
    c17 = np.asarray(cs[17], float)
    courbes = [('Nikon IIIa (couleur, référence)', (170, 170, 170), c17),
               ('Tri-X 400 (preset acheté, livré)', (20, 20, 20), np.asarray(json.loads((V1 / 'tri-x.json').read_text())['courbe'], float)),
               ('Tri-X 400 (fiche Kodak + tirage grade 2)', (120, 120, 120), fn.courbe('trix', c17)[0].astype(float)),
               ('HP5 Plus (fiche Ilford + tirage grade 2, livré)', (30, 90, 180), np.asarray(json.loads((V1 / 'hp5.json').read_text())['courbe'], float))]
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    titre(d, 'Tri-X et HP5 dans le D40', 'Gauche : courbe de tons (signal du capteur en IL → valeur du JPEG). Droite : part de chaque canal dans le gris.')
    G, B0, X1, Y0 = 120, 960, 1080, 200
    v_gris = 0.115
    E1 = float(np.log2(1 / v_gris))  # pleine échelle du capteur
    ev = np.linspace(-7, E1, 400)
    sx = lambda e: G + (e + 7) / (E1 + 7) * (X1 - G)
    sy = lambda y: B0 - y / 255 * (B0 - Y0)
    for y in (0, 64, 128, 192, 255):
        d.line((G, sy(y), X1, sy(y)), fill=(232, 232, 232), width=2)
        d.text((G - 60, sy(y) - 14), str(y), fill=(80, 80, 80), font=police(24))
    for e in range(-7, 4):
        d.line((sx(e), Y0, sx(e), B0), fill=(240, 240, 240), width=1)
        d.text((sx(e) - 14, B0 + 10), f'{e:+d}' if e else '0', fill=(80, 80, 80), font=police(24))
    d.line((sx(E1), Y0, sx(E1), B0), fill=(200, 120, 120), width=2)
    d.text((sx(E1) - 210, B0 - 300), 'pleine échelle', fill=(170, 80, 80), font=police(24))
    d.text((sx(E1) - 210, B0 - 272), 'du capteur', fill=(170, 80, 80), font=police(24))
    d.text((G + 200, B0 + 44), 'IL par rapport au gris moyen (0 = gris 18 % exposé normalement)', fill=(80, 80, 80), font=police(24))
    for k, (lib, col, c) in enumerate(courbes):
        v = np.clip(v_gris * 2 ** ev, 0, 1)
        y = np.interp(v * 4095, np.arange(4096), c) / 4095 * 255
        d.line([(sx(a), sy(b)) for a, b in zip(ev, y)], fill=col, width=5 if k != 0 else 3)
        d.rectangle((G + 20, Y0 + 10 + 40 * k, G + 54, Y0 + 30 + 40 * k), fill=col)
        d.text((G + 64, Y0 + 4 + 40 * k), lib, fill=(30, 30, 30), font=police(26))
    # mélanges
    sens = fn.ms.lire_camspec(camspec)
    tx = json.loads((V1 / 'tri-x.json').read_text())
    poids = [('Tri-X (preset acheté)', tx['poids_D40_RGB']), ('Tri-X (fiche Kodak)', tx['controle_fiche_kodak']['poids_D40_RGB']),
             ('HP5 (fiche Ilford)', json.loads((V1 / 'hp5.json').read_text())['poids_D40_RGB']),
             ('Nikon N&B d’usine (mesuré)', [0.40 / 1.08, 0.61 / 1.08, 0.07 / 1.08])]
    x0, y0, bw = 1200, 230, 600
    for k, (lib, w) in enumerate(poids):
        y = y0 + k * 170
        d.text((x0, y), lib, fill=(30, 30, 30), font=police(28, True))
        x = x0
        for c, col, nm in zip(w, ((210, 60, 50), (60, 160, 70), (50, 90, 210)), 'RVB'):
            ww = max(c, 0) * bw
            d.rectangle((x, y + 44, x + ww, y + 104), fill=col)
            if ww > 60:
                d.text((x + 8, y + 58), f'{nm} {c * 100:.0f} %', fill='white', font=police(26, True))
            x += ww
    d.text((x0, y0 + 4 * 170), 'Part de chaque canal du capteur (balance faite)', fill=(90, 90, 90), font=police(24))
    im.save(V1 / 'noir-et-blanc.png')


def self_test():
    assert pathlib.Path(POLICE).exists() and pathlib.Path(GRAS).exists()
    r = fond_roue(50)
    assert r.size == (100, 100)
    a = np.asarray(r)
    assert a[0, 0].tolist() == [255, 255, 255] and a[50, 50].std() < 30  # coin blanc, centre gris
    print('self-test OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['etage', 'sonde', 'roue', 'secteurs', 'ecarts', 'nb'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    {'etage': fig_etage, 'sonde': fig_sonde, 'roue': fig_roue, 'secteurs': fig_secteurs, 'ecarts': fig_ecarts,
     'nb': fig_nb}[a.action](*a.args)


if __name__ == '__main__':
    main()
