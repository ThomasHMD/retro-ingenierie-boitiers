#!/usr/bin/env python3
"""Base Standard du D750 mesurée sur un vrai couple NEF + JPEG, puis Picture Control d'essai calculés dessus.

Données : mire d'Imaging Resource « VFA » du D750 (ColorChecker 24 + ColorChecker SG 140 plages), ISO 100, Picture
Control Standard d'origine, D-Lighting actif désactivé, WB mesurée (preset), 24/09/2014. Fichiers non recopiés ici :
  https://old.imaging-resource.com/PRODS/nikon-d750/FULLRES/D750hVFAI00100.JPG
  https://old.imaging-resource.com/PRODS/nikon-d750/FULLRES/D750hVFAI00100.NEF
Références de la mire : X-Rite, valeurs « avant novembre 2014 » (colour-science), D50 adaptées en D65 (Bradford).

  d750_standard.py mesurer <JPG> <NEF> <sortie.json>       plages, courbe Standard, rendu par teinte, mode de courbe
  d750_standard.py cible <mesure.json> <cible> <sortie.json> courbe perso (après la base) + curseurs pour une cible :
                                                            CLASSIC-CHROME, CLASSIC-Neg., ... (fuji-lut), kodachrome_64
                                                            (avec --status-a), ou une cible N&B de films_nb (trix_g062_d76,
                                                            hp5_fiche, fp4) ; écrit aussi la table de 257 valeurs
  d750_standard.py ncp <cible.json> <NOM> <base> <fichier.NCP>   Picture Control d'essai (base : standard, monochrome)

Hypothèses (à valider sur le boîtier, voir recherche/d750-leviers-reglages.md §6) : la courbe perso s'applique après
la base, sur chaque canal ; au-dessus du blanc de la mire, la courbe Standard monte jusqu'à 255 à l'écrêtage du
capteur ; la base Monochrome a la même courbe que Standard ; le curseur Teinte est une rotation CIELAB.
"""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

# position des plages sur l'image 6016 × 4016 d'Imaging Resource (relevée sur l'image, vérifiée par superposition)
_S = 6016 / 1198


def _pt(cx, cy):
    return 255 * _S + cx * 0.5 * _S, 250 * _S + cy * 0.5 * _S


CC = [_pt(x, y) for y in (86, 178, 269, 358) for x in (78, 171, 264, 357, 449, 541)]
SG = {f'{"ABCDEFGHIJKLMN"[j]}{i + 1}': _pt(x, y) for i, y in enumerate(np.linspace(64, 389, 10))
      for j, x in enumerate(np.linspace(839, 1300, 14))}
SECTEURS = [('rouge', 0, 45), ('orange, peau', 45, 75), ('jaune', 75, 105), ('vert-jaune', 105, 135), ('vert', 135, 165),
            ('cyan-vert', 165, 200), ('cyan', 200, 235), ('bleu', 235, 290), ('violet', 290, 330), ('magenta', 330, 360)]


def _lab(code):
    import colour
    D65 = colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65']
    return colour.XYZ_to_Lab(colour.RGB_to_XYZ(np.clip(code, 0, 1), 'sRGB', apply_cctf_decoding=True), D65)


def _de(a, b):
    import colour
    return colour.delta_E(a, b, method='CIE 2000')


def _st(e):
    return {'mediane': round(float(np.median(e)), 2), 'p90': round(float(np.percentile(e, 90)), 2)}


def mesurer(jpg_path, nef_path):
    import colour
    import rawpy
    from PIL import Image
    from scipy.optimize import least_squares
    jpg = np.asarray(Image.open(jpg_path).convert('RGB'), np.float64) / 255
    raw = rawpy.imread(nef_path)
    cfa = raw.raw_image_visible.astype(np.float64)
    col = raw.raw_colors_visible
    bl, wl = np.array(raw.black_level_per_channel, float), float(raw.white_level)
    wb = np.array(raw.camera_whitebalance[:3], float)
    dy, dx = (cfa.shape[0] - jpg.shape[0]) // 2, (cfa.shape[1] - jpg.shape[1]) // 2

    def plage(x, y, r):
        x, y = int(round(x)), int(round(y))
        c = cfa[y + dy - r:y + dy + r, x + dx - r:x + dx + r]
        k = col[y + dy - r:y + dy + r, x + dx - r:x + dx + r]
        v = [(c[(k == ch) | ((k == 3) & (ch == 1))].mean() - bl[ch]) / (wl - bl[ch]) for ch in range(3)]
        return jpg[y - r:y + r, x - r:x + r].reshape(-1, 3).mean(0), np.array(v)

    ref_cc = colour.CCS_COLOURCHECKERS['ColorChecker24 - Before November 2014']
    ref_sg = colour.CCS_COLOURCHECKERS['ColorCheckerSG - Before November 2014']
    noms = list(ref_cc.data) + list(ref_sg.data)
    mes = [plage(x, y, 40) for x, y in CC] + [plage(*SG[n], 16) for n in ref_sg.data]
    J = np.array([m[0] for m in mes])
    Rw = np.array([m[1] for m in mes]) * wb
    D50 = colour.xy_to_XYZ(colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D50'])
    D65 = colour.xy_to_XYZ(colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65'])
    XYZ = colour.adaptation.chromatic_adaptation_VonKries(
        colour.xyY_to_XYZ(np.array(list(ref_cc.data.values()) + list(ref_sg.data.values()))), D50, D65, 'Bradford')
    Rw *= XYZ[18, 1] / Rw[18, 1]
    lab_ref, lab_jpg = colour.XYZ_to_Lab(XYZ, colour.XYZ_to_xy(D65)), _lab(J)
    neutres = np.hypot(lab_ref[:, 1], lab_ref[:, 2]) < 4
    o = np.argsort(XYZ[neutres, 1])
    Yn, Cn = XYZ[neutres, 1][o], np.maximum.accumulate(J[neutres].mean(1)[o])
    blanc_raw = float((np.array(mes[18][1]) * wb / wb[1]).max())  # canal le plus haut du blanc, en fraction de la pleine échelle
    res = {'source': 'Imaging Resource, D750hVFAI00100 (NEF + JPEG Standard, ISO 100, ADL désactivé, WB preset)',
           'wb_fichier': wb.tolist(), 'noms': noms, 'XYZ': XYZ.round(5).tolist(), 'raw_equilibre': Rw.round(6).tolist(),
           'jpg': J.round(5).tolist(), 'blanc_mire_fraction_pleine_echelle': round(blanc_raw, 4),
           'courbe_standard': {'Y_scene': Yn.round(5).tolist(), 'code': Cn.round(5).tolist()}}
    # rendu de Standard contre la mire, par teinte
    Cr, Cj = np.hypot(*lab_ref[:, 1:].T), np.hypot(*lab_jpg[:, 1:].T)
    hr = np.degrees(np.arctan2(lab_ref[:, 2], lab_ref[:, 1])) % 360
    dh = (np.degrees(np.arctan2(lab_jpg[:, 2], lab_jpg[:, 1])) - hr + 180) % 360 - 180
    res['standard_contre_mire'] = {'dE2000': _st(_de(lab_jpg, lab_ref)), 'secteurs': [
        {'secteur': n, 'n': int(m.sum()), 'teinte_deg': round(float(np.median(dh[m])), 1),
         'chroma_x': round(float(np.median(Cj[m] / Cr[m])), 2), 'dL': round(float(np.median(lab_jpg[m, 0] - lab_ref[m, 0])), 1)}
        for n, a, b in SECTEURS for m in [(Cr > 10) & (hr >= a) & (hr < b)] if m.sum()]}
    # mode de la courbe de la base : matrice libre puis même courbe sur R, V, B, ou courbe sur la luminance seule
    S = courbe_standard(res)
    M0 = np.linalg.lstsq(Rw, colour.XYZ_to_RGB(XYZ, 'sRGB'), rcond=None)[0].T

    def sortie(p, mode):
        lin = Rw @ p.reshape(3, 3).T
        if mode == 'canaux':
            return _lab(S(np.clip(lin, 1e-4, None)))
        xyz = colour.RGB_to_XYZ(np.clip(lin, 1e-5, None), 'sRGB')
        Y = np.maximum(xyz[:, 1], 1e-5)
        return colour.XYZ_to_Lab(xyz * (colour.cctf_decoding(S(Y), 'sRGB') / Y)[:, None], colour.XYZ_to_xy(D65))
    res['mode_courbe_base'] = {}
    for mode in ('canaux', 'luminance'):
        r = least_squares(lambda p: (sortie(p, mode) - lab_jpg).ravel(), M0.ravel(), loss='soft_l1', f_scale=2)
        res['mode_courbe_base'][mode] = {**_st(_de(sortie(r.x, mode), lab_jpg)), 'max': round(float(_de(sortie(r.x, mode), lab_jpg).max()), 2)}
        if mode == 'canaux':
            res['matrice_modele'] = r.x.reshape(3, 3).round(6).tolist()
    return res


def courbe_standard(m):
    """Y scène → code sRGB de la base Standard ; au-dessus du blanc de la mire, raccord linéaire en log jusqu'à 255
    à l'écrêtage du capteur (hypothèse)."""
    c = m['courbe_standard']
    Yclip = m['XYZ'][18][1] / m['blanc_mire_fraction_pleine_echelle']
    lx = np.r_[np.log(c['Y_scene']), np.log(Yclip)]
    ly = np.r_[c['code'], 1.0]
    return lambda v: np.interp(np.log(np.maximum(v, 1e-4)), lx, ly)


def _cible_tonale_et_lab(cible, m, status_a=None):
    """(T : Y scène → code cible, Lab cible des plages ou None, masque des plages évaluées)."""
    import colour
    XYZ = np.array(m['XYZ'])
    n = len(XYZ)
    if cible.startswith('kodachrome'):
        import kodachrome as k
        km = k.charger(cible, status_a)
        a = k.analytiques(km)
        R, nn = k.reflectances_test(n=0)
        Rt = np.clip(R * 0.18 / R[nn.index('neutral 5 (.70 D)')].mean(), 0, 1)
        lab_t = np.full((n, 3), np.nan)
        lab_t[:24] = k.lab(k.rendu(km, a, Rt)[0])
        il = np.arange(-9, 5.001, 0.05)
        Yt = k.rendu(km, a, np.repeat((0.18 * 2.0 ** il)[:, None], len(k.L), 1))[0][:, 1]
        return (lambda y: colour.cctf_encoding(np.interp(np.log2(np.maximum(y, 1e-6) / 0.18), il, Yt), 'sRGB'),
                lab_t, np.arange(n) < 24)
    import films_nb as fn
    fn.fiches_exactes()
    if cible in fn.CC:  # noir et blanc : courbe film + tirage, pas de cible couleur
        t = fn.cible_tonale(cible)
        lin, code = fn.eotf(np.linspace(0, 1, 257)), np.array(t['table_257_entree_srgb_codee'])
        return lambda y: np.interp(np.clip(y, 0, 1), lin, code), None, None
    else:
        import fuji_lut as fl
        lut = fl.lire_cube(cible)
        lab_t = fl.affichage_vers_lab(fl.rendre(lut, np.clip(XYZ @ np.linalg.inv(fl.M_709_VERS_XYZ).T, 0, None)))
        yt = np.geomspace(1e-4, 3.0, 400)
        tg = fl.rendre(lut, np.repeat(yt[:, None], 3, 1)).mean(1)
        return lambda y: np.interp(np.log(np.maximum(y, 1e-4)), np.log(yt), tg), lab_t, np.ones(n, bool)


def cible(m, nom, status_a=None):
    from scipy.optimize import minimize
    S = courbe_standard(m)
    T, lab_t, sel = _cible_tonale_et_lab(nom, m, status_a)
    yy = np.geomspace(1e-4, m['XYZ'][18][1] / m['blanc_mire_fraction_pleine_echelle'], 800)
    xs, idx = np.unique(S(yy), return_index=True)
    ys = np.maximum.accumulate(T(yy)[idx])
    C = lambda c: np.interp(c, xs, ys)
    x257 = np.linspace(0, 1, 257)
    res = {'cible': nom, 'base': 'Standard (mesurée) ; Monochrome supposée de même courbe',
           'courbe_perso_257': np.clip(C(x257), 0, 1).round(5).tolist(),
           'courbe_perso_par_16': [[int(round(a * 255)), int(round(float(C(a)) * 255))] for a in x257[::16]]}
    if lab_t is None:
        return res
    J = np.array(m['jpg'])

    def rendu(code, kc, rot):
        L = _lab(C(code))
        h = np.arctan2(L[:, 2], L[:, 1]) + np.radians(rot)
        Cc = np.hypot(L[:, 1], L[:, 2]) * kc
        return np.stack([L[:, 0], Cc * np.cos(h), Cc * np.sin(h)], 1)
    de = lambda L: _de(L[sel], lab_t[sel])
    res['n_plages'] = int(sel.sum())
    res['standard_brut'] = _st(de(_lab(J)))
    res['courbe_seule'] = _st(de(rendu(J, 1, 0)))
    r1 = minimize(lambda q: np.median(de(rendu(J, *q))), [1, 0], method='Nelder-Mead',
                  options={'initial_simplex': [[1, 0], [0.8, 0], [1, 5]]})
    res['courbe_saturation_teinte'] = {**_st(de(rendu(J, *r1.x))), 'chroma_x': round(float(r1.x[0]), 2), 'teinte_deg': round(float(r1.x[1]), 1)}
    # décalage de WB simulé par le modèle de la base (matrice + courbe par canal)
    Rw, M = np.array(m['raw_equilibre']), np.array(m['matrice_modele'])
    base = lambda g: S(np.clip((Rw * g) @ M.T, 1e-4, None))
    best = None
    for lr in np.arange(-0.3, 0.31, 0.1):
        for lb in np.arange(-0.3, 0.31, 0.1):
            g = np.array([np.exp(lr), 1, np.exp(lb)])
            r = minimize(lambda q: np.median(de(rendu(base(g), *q))), r1.x, method='Nelder-Mead',
                         options={'initial_simplex': [r1.x, r1.x + [0.1, 0], r1.x + [0, 5]], 'maxiter': 150})
            if best is None or r.fun < best[0]:
                best = (r.fun, [lr, lb, *r.x])
    x0 = best[1]
    f = lambda p: np.median(de(rendu(base(np.array([np.exp(p[0]), 1, np.exp(p[1])])), p[2], p[3])))
    r2 = minimize(f, x0, method='Nelder-Mead', options={'initial_simplex': [x0] + [np.add(x0, d) for d in (
        [0.05, 0, 0, 0], [0, 0.05, 0, 0], [0, 0, 0.05, 0], [0, 0, 0, 3])]})
    g = np.array([np.exp(r2.x[0]), 1, np.exp(r2.x[1])])
    res['modele_base_sans_wb'] = _st(de(rendu(base(np.ones(3)), *r1.x)))
    res['avec_wb_modele'] = {**_st(de(rendu(base(g), r2.x[2], r2.x[3]))), 'gain_R': round(float(g[0]), 3),
                             'gain_B': round(float(g[2]), 3), 'chroma_x': round(float(r2.x[2]), 2), 'teinte_deg': round(float(r2.x[3]), 1),
                             # ≈ −0,035 de ln(R/B) par cran A-B vers B (pente des capteurs Nikon de substitution, d750_leviers.py)
                             'crans_A_B_approx': round(float(np.log(g[0] / g[2]) / -0.0353), 1)}
    return res


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    if a[0] == 'mesurer':
        r = mesurer(a[1], a[2])
        pathlib.Path(a[3]).write_text(json.dumps(r, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({k: r[k] for k in ('standard_contre_mire', 'mode_courbe_base')}, ensure_ascii=False, indent=1))
    elif a[0] == 'cible':
        sa = a[a.index('--status-a') + 1] if '--status-a' in a else None
        r = cible(json.loads(pathlib.Path(a[1]).read_text(encoding='utf-8')), a[2], sa)
        pathlib.Path(a[3]).write_text(json.dumps(r, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({k: v for k, v in r.items() if k != 'courbe_perso_257'}, ensure_ascii=False))
    elif a[0] == 'ncp':
        import picture_control as pc
        r = json.loads(pathlib.Path(a[1]).read_text(encoding='utf-8'))
        lut = np.maximum.accumulate(np.round(np.array(r['courbe_perso_257']) * 32767)).astype(int).tolist()
        base = {'standard': 0x0001, 'monochrome': 0x064D}[a[3]]
        curseurs = {'accentuation': 3, 'contraste': 'courbe', 'luminosite': 'courbe'}  # accentuation : défaut de Standard
        if base == 0x064D:
            curseurs.update(saturation=None, teinte=None, filtre=0, virage=0, force_virage=None)
        else:
            curseurs.update(saturation=0, teinte=0, filtre=None, virage=None, force_virage=None)
        pathlib.Path(a[4]).write_bytes(pc.ecrire_ncp(a[2], base, curseurs, lut))
        print('écrit', a[4])
    return 0


if __name__ == '__main__':
    sys.exit(main())
