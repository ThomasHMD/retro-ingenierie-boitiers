#!/usr/bin/env python3
"""Kodachrome 25, 64, 200 : rendu d'une scène reconstruit d'après la fiche Kodak E-55 (décembre 1996), puis
traduit en cibles pour un Picture Control (courbe neutre, saturation, dérives de teinte, dominante des neutres).

Données : recherche/donnees-films/kodachrome-e55-1996.json (courbes extraites du PDF vectoriel par
fiches_vectorielles.py). Réponses Status A : numérisation de Giorgianni, Madden et Kriss, *Digital Color
Management* (Wiley, 2009), p. 335, publiée dans agx-emulsion (A. Volpato, GPL-3.0, dépôt de R&D,
agx_emulsion/data/densitometer/status_A/responsivity_{r,g,b}.csv) ; non recopiée ici, dossier en argument :
  git clone --filter=blob:none --no-checkout https://github.com/andreavolpato/agx-emulsion
  git -C agx-emulsion show e418a25:agx_emulsion/data/densitometer/status_A/responsivity_r.csv > status_A/responsivity_r.csv (idem g, b)

Modèle (spectral, une couche = un colorant, sans effets inter-couches) :
1. exposition de chaque couche : réflectance × lumière du jour D55 × sensibilité spectrale de la couche (fiche,
   courbes à D = 1,0 ; nulle hors du tracé), rapportée à celle d'un gris neutre ; le gris de 18 % reçoit
   log H = log10(q·K/S) (étalonnage des posemètres ISO 2720, q = 0,65, K = 12,5 : hypothèse de calage) ;
2. courbes caractéristiques Status A (intégrales, exposition neutre) converties en quantités de colorant
   (densités analytiques) en résolvant, pour chaque log H, D_StatusA(Σ a_j · colorant_j) = (R, V, B) ;
3. chaque couche suit sa courbe analytique selon sa propre exposition ; densité spectrale = Σ a_j · colorant_j ;
4. vue sur visionneuse 5 000 K (D50), blanc = film à la densité minimale (comme un scan équilibré sur le
   blanc du film), adaptation Bradford vers D65 ; comparaison en CIELAB D65 à la scène vue sous D55 adaptée en D65.

  kodachrome.py <status_A/> [--film kodachrome_64|tous] [--json sortie.json]
  kodachrome.py <status_A/> --self-test
"""
import argparse
import json
import pathlib
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent.parent
DONNEES = ICI / 'recherche' / 'donnees-films' / 'kodachrome-e55-1996.json'
L = np.arange(400, 701, 5).astype(float)  # grille spectrale commune
ISO = {'kodachrome_25': 25, 'kodachrome_64': 64, 'kodachrome_200': 200}
Q, K = 0.65, 12.5


def charger(film, statusA):
    import colour
    d = json.loads(DONNEES.read_text(encoding='utf-8'))[film]
    cc = d['courbes_caracteristiques']
    ss = d['sensibilites_spectrales']
    dd = d['densites_colorants']
    log_h = np.arange(-3.2, 1.21, 0.01)
    courbes = np.stack([np.interp(log_h, *np.array(cc[c]).T) for c in 'RGB'], 1)  # tenue aux extrémités
    sens = np.stack([10 ** np.interp(L, *np.array(ss[k]).T, left=-np.inf, right=-np.inf)
                     for k in ('couche_cyan_rouge', 'couche_magenta_vert', 'couche_jaune_bleu')], 1)
    colorants = np.stack([np.interp(L, *np.array(dd[k]).T) for k in ('cyan', 'magenta', 'jaune')], 1)
    neutre = np.interp(L, *np.array(dd['neutre_visuel']).T)
    rep = []
    for c in 'rgb':
        a = np.loadtxt(pathlib.Path(statusA) / f'responsivity_{c}.csv', delimiter=',')
        a = a[np.argsort(a[:, 0])]
        rep.append(np.interp(L, a[:, 0], a[:, 1], left=0, right=0))
    D55 = colour.SDS_ILLUMINANTS['D55'].copy().align(colour.SpectralShape(400, 700, 5)).values
    D50 = colour.SDS_ILLUMINANTS['D50'].copy().align(colour.SpectralShape(400, 700, 5)).values
    cmf = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer'].copy().align(colour.SpectralShape(400, 700, 5)).values
    return {'log_h': log_h, 'courbes': courbes, 'sens': sens, 'colorants': colorants, 'neutre': neutre,
            'statusA': np.stack(rep, 1), 'D55': D55, 'D50': D50, 'cmf': cmf, 'iso': ISO[film]}


def status_a(m, dens):
    """Densités Status A (R, V, B) de densités spectrales (..., n_lambda)."""
    T = 10 ** -np.asarray(dens)
    R = m['statusA']
    return -np.log10((T @ R) / R.sum(0))


def analytiques(m):
    """Quantités de colorant (C, M, J) le long de l'échelle neutre, pour chaque log H de la fiche."""
    from scipy.optimize import least_squares
    C = m['colorants']
    a = np.zeros((len(m['log_h']), 3))
    x0 = m['courbes'][0] * 0.8
    for i, cible in enumerate(m['courbes']):
        r = least_squares(lambda x: status_a(m, C @ x) - cible, x0, bounds=(0, 10), xtol=1e-10, ftol=1e-10)
        a[i] = x0 = r.x
    return a


def exposition_relative(m, R):
    """log10 de l'exposition de chaque couche (C, M, J) par rapport au gris de 18 %, sous D55."""
    E = m['D55']
    return np.log10(((R * E) @ m['sens']) / ((0.18 * E) @ m['sens']))


def rendu(m, a_courbes, R, decalage_il=0.0, visee='D50'):
    """XYZ (D65, Y blanc du film = 1) des transparences de réflectances R (n, n_lambda), vues sous `visee`
    (D50 : visionneuse 5 000 K de la fiche ; P3200 : corps noir 3 200 K, projecteur halogène)."""
    import colour
    S = m['D50'] if visee == 'D50' else colour.sd_blackbody(3200, colour.SpectralShape(400, 700, 5)).values
    log_gris = np.log10(Q * K / m['iso']) + decalage_il * np.log10(2)
    lh = log_gris + exposition_relative(m, R)
    a = np.stack([np.interp(lh[:, j], m['log_h'], a_courbes[:, j]) for j in range(3)], 1)
    dens = a @ m['colorants'].T
    T = 10 ** -dens
    xyz = (T * S) @ m['cmf']
    a_min = a_courbes[np.argmax(m['log_h'])]
    blanc = (10 ** -(a_min @ m['colorants'].T) * S) @ m['cmf']
    xyz, blanc = xyz / blanc[1], blanc / blanc[1]
    D65 = colour.xy_to_XYZ(colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65'])
    return colour.adaptation.chromatic_adaptation_VonKries(xyz, blanc, D65, 'Bradford'), a


def scene(m, R):
    import colour
    xyz = (R * m['D55']) @ m['cmf']
    blanc = m['D55'] @ m['cmf']
    xyz, blanc = xyz / blanc[1], blanc / blanc[1]
    D65 = colour.xy_to_XYZ(colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65'])
    return colour.adaptation.chromatic_adaptation_VonKries(xyz, blanc, D65, 'Bradford')


def lab(xyz):
    import colour
    return colour.XYZ_to_Lab(xyz, colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65'])


def srgb8(xyz):
    import colour
    rgb = colour.XYZ_to_RGB(xyz, 'sRGB', apply_cctf_encoding=True)
    return np.clip(rgb, 0, 1) * 255


def reflectances_test(n=600, graine=0):
    """ColorChecker (Ohta, 24) puis spectres lisses aléatoires, comme films_nb.reflectances (même graine)."""
    import colour
    forme = colour.SpectralShape(400, 700, 5)
    cc = colour.SDS_COLOURCHECKERS['ColorChecker N Ohta']
    noms = list(cc.keys())
    R = [sd.copy().align(forme).values for sd in cc.values()]
    rng = np.random.default_rng(graine)
    for _ in range(n):
        r = np.full(len(L), rng.uniform(0.02, 0.3))
        for _ in range(rng.integers(1, 4)):
            r += rng.uniform(0.1, 0.8) * np.exp(-0.5 * ((L - rng.uniform(380, 740)) / rng.uniform(15, 90)) ** 2)
        R.append(np.clip(r, 0.01, 0.98))
    return np.array(R), noms


SECTEURS = [('rouge', 0, 45), ('orange, peau', 45, 75), ('jaune', 75, 105), ('vert-jaune', 105, 135),
            ('vert', 135, 165), ('cyan-vert', 165, 200), ('cyan', 200, 235), ('bleu', 235, 290),
            ('violet', 290, 330), ('magenta', 330, 360)]


def analyser(statusA, film='kodachrome_64'):
    m = charger(film, statusA)
    a = analytiques(m)
    res = {'film': film, 'iso': m['iso'], 'log_h_gris_18': round(float(np.log10(Q * K / m['iso'])), 3)}

    # contrôle du modèle de colorants : Status A de l'échelle reconstruite contre la fiche, et somme des
    # colorants normalisés contre le « neutre visuel » de la fiche
    err = np.abs(status_a(m, a @ m['colorants'].T) - m['courbes'])
    res['controle'] = {'ecart_statusA_max': round(float(err.max()), 4),
                       'somme_colorants_contre_neutre_visuel_ecart_max': round(float(np.abs(m['colorants'].sum(1) - m['neutre']).max()), 3)}

    # 1. échelle de gris : de -7 à +4 IL autour du gris de 18 %
    il = np.arange(-7, 4.01, 1 / 3)
    gris = np.repeat((0.18 * 2.0 ** il)[:, None], len(L), 1)
    for visee in ('D50', 'P3200'):
        xyz_g, _ = rendu(m, a, gris, visee=visee)
        lab_g, s8 = lab(xyz_g), srgb8(xyz_g)
        res[f'echelle_de_gris_{visee}'] = [
            {'IL': round(float(e), 2), 'L': round(float(p[0]), 1), 'a': round(float(p[1]), 1), 'b': round(float(p[2]), 1),
             'srgb8': [round(float(v), 1) for v in q], 'densite_visuelle_sur_dmin': round(float(-np.log10(max(x[1], 1e-9))), 3)}
            for e, p, q, x in zip(il, lab_g, s8, xyz_g)]
    # échelle fine pour la courbe neutre (Y film en fonction de l'exposition de la scène)
    il_f = np.arange(-9, 5.001, 0.05)
    xyz_gf, _ = rendu(m, a, np.repeat((0.18 * 2.0 ** il_f)[:, None], len(L), 1))
    res['courbe_neutre'] = {'IL': il_f.round(2).tolist(), 'Y_film_sur_blanc': xyz_gf[:, 1].round(6).tolist()}
    res['cible_tonale'] = cible_tonale(il_f, xyz_gf[:, 1])

    # 2. couleurs : mire et 600 spectres lisses
    R, noms = reflectances_test()
    expo = 0.18 / R[noms.index('neutral 5 (.70 D)')].mean()  # gris de la mire ramené à 18 %
    Rt = np.clip(R * expo, 0, 1)
    xyz_s = scene(m, Rt)
    ls = lab(xyz_s)
    # référence « même tonalité » : chromaticité de la scène, luminance passée dans la courbe neutre du film
    Yref = np.interp(np.log2(np.maximum(xyz_s[:, 1], 1e-6) / 0.18), il_f, xyz_gf[:, 1])
    lt = lab(xyz_s * (Yref / np.maximum(xyz_s[:, 1], 1e-6))[:, None])
    for visee in ('D50', 'P3200'):
        for de_il in (0.0, -1 / 3, 1 / 3):
            xyz_f, _ = rendu(m, a, Rt, de_il, visee)
            lf = lab(xyz_f)
            cle = visee + ('' if de_il == 0 else f'_{de_il:+.2f}IL')
            res[f'comparaison_{cle}'] = {'contre_scene': _comparer(ls, lf, noms), 'contre_scene_meme_tonalite': _comparer(lt, lf, noms)}
    lf = lab(rendu(m, a, Rt)[0])

    # 3. ce qu'un réglage global peut porter, à partir de la référence de même tonalité (le Picture Control a déjà
    #    sa courbe) : un facteur de chroma et une rotation de teinte uniformes ; on note l'écart qui reste
    ct, ht = np.hypot(lt[:, 1], lt[:, 2]), np.degrees(np.arctan2(lt[:, 2], lt[:, 1]))
    def modele(k, rot):
        h = np.radians(ht + rot)
        return np.stack([lt[:, 0], k * ct * np.cos(h), k * ct * np.sin(h)], 1)
    from scipy.optimize import minimize
    r = minimize(lambda p: np.median(_de(modele(*p), lf)), [1.1, 0.0], method='Nelder-Mead')
    k_opt, rot_opt = r.x
    res['reglage_global'] = {'chroma_x': round(float(k_opt), 2), 'rotation_teinte_deg': round(float(rot_opt), 1),
                             'dE2000_courbe_seule': _stats(_de(modele(1.0, 0.0), lf)),
                             'dE2000_courbe_saturation_teinte': _stats(_de(modele(k_opt, rot_opt), lf))}
    return res


def cible_tonale(il_f, Y):
    """Courbe neutre en sortie sRGB codée (luminance seule, blanc du film = 255). Deux calages : posemètre (gris de
    18 % exposé à q·K/S, le rendu dense de la diapositive) et gris de 18 % ramené à 118/255 (exposition décalée).
    Table de 257 valeurs : entrée sRGB codée de la scène (blanc 1,0 = gris 18 % + 2,47 IL), si le boîtier rendait la
    scène en sRGB pur avant la courbe (hypothèse, à remplacer par la courbe de base mesurée du D750)."""
    oetf = lambda y: np.where(y <= 0.0031308, 12.92 * y, 1.055 * np.clip(y, 0, None) ** (1 / 2.4) - 0.055)
    eotf = lambda v: np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    lY = np.log2(np.maximum(Y, 1e-9))
    il_118 = float(np.interp(np.log2(eotf(118 / 255)), lY, il_f))  # IL de la scène qui sort à 118 au calage posemètre
    x = np.linspace(0, 1, 257)
    il_x = np.log2(np.maximum(eotf(x), 1e-9) / 0.18)
    out = {'surexposition_IL_pour_gris_118': round(il_118, 2)}
    for cle, dec in (('calage_posemetre', 0.0), ('gris_118', il_118)):
        f = lambda e: oetf(np.interp(e + dec, il_f, Y))
        out[cle] = {'par_IL': [[round(float(e), 2), round(float(f(e)) * 255, 1)] for e in np.arange(-7, 4.01, 1 / 3)],
                    'table_257_entree_srgb_codee': f(il_x).round(4).tolist()}
    return out


def _comparer(ref, lf, noms):
    """Écarts film - référence : mire (24 patchs), puis secteurs de teinte (600 spectres + mire, chroma > 10)."""
    cr, cf = np.hypot(ref[:, 1], ref[:, 2]), np.hypot(lf[:, 1], lf[:, 2])
    hr, hf = np.degrees(np.arctan2(ref[:, 2], ref[:, 1])) % 360, np.degrees(np.arctan2(lf[:, 2], lf[:, 1])) % 360
    dh = (hf - hr + 180) % 360 - 180
    out = {'mire': [{'patch': n, 'ref_Lab': [round(float(v), 1) for v in s], 'kodachrome_Lab': [round(float(v), 1) for v in f],
                     'dL': round(float(f[0] - s[0]), 1), 'chroma_x': round(float(c1 / c0), 2) if c0 > 5 else None,
                     'teinte_deg': round(float(h), 1) if c0 > 5 else None, 'dE2000': round(float(e), 1)}
                    for n, s, f, c0, c1, h, e in zip(noms, ref[:24], lf[:24], cr[:24], cf[:24], dh[:24], _de(ref[:24], lf[:24]))]}
    ok = cr > 10
    out['secteurs'] = []
    for nom, h0, h1 in SECTEURS:
        k = ok & (hr >= h0) & (hr < h1)
        if k.sum() >= 3:
            out['secteurs'].append({'secteur': nom, 'teinte_ref': [h0, h1], 'n': int(k.sum()),
                                    'decalage_teinte_median': round(float(np.median(dh[k])), 1),
                                    'chroma_x_median': round(float(np.median(cf[k] / cr[k])), 2),
                                    'dL_median': round(float(np.median(lf[k, 0] - ref[k, 0])), 1)})
    out['global'] = {'chroma_x_median': round(float(np.median(cf[ok] / cr[ok])), 2),
                     'decalage_teinte_median_abs': round(float(np.median(np.abs(dh[ok]))), 1),
                     'dE2000': _stats(_de(ref, lf))}
    return out


def _de(a, b):
    import colour
    return colour.delta_E(a, b, method='CIE 2000')


def _stats(e):
    return {'mediane': round(float(np.median(e)), 1), 'centile_90': round(float(np.percentile(e, 90)), 1)}


def self_test(statusA):
    m = charger('kodachrome_64', statusA)
    assert m['sens'].shape == (len(L), 3) and np.isfinite(m['courbes']).all()
    a = analytiques(m)
    assert np.abs(status_a(m, a @ m['colorants'].T) - m['courbes']).max() < 0.01
    xyz, _ = rendu(m, a, np.full((1, len(L)), 0.18))
    assert 30 < lab(xyz)[0, 0] < 70
    print('self-test OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('statusA')
    ap.add_argument('--film', default='kodachrome_64', choices=list(ISO) + ['tous'])
    ap.add_argument('--json')
    ap.add_argument('--self-test', action='store_true')
    o = ap.parse_args()
    if o.self_test:
        return self_test(o.statusA)
    if o.film == 'tous':
        res = {f: analyser(o.statusA, f) for f in ISO}
        if o.json:
            pathlib.Path(o.json).write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
        for f, r in res.items():
            print(f, r['cible_tonale']['surexposition_IL_pour_gris_118'], r['reglage_global'])
        return
    res = analyser(o.statusA, o.film)
    if o.json:
        pathlib.Path(o.json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    for g in res['echelle_de_gris_D50'][::3]:
        print(g)
    for cle, v in res.items():
        if cle.startswith('comparaison_'):
            for ref in ('contre_scene', 'contre_scene_meme_tonalite'):
                print(cle, ref, v[ref]['global'])
                for sct in v[ref]['secteurs']:
                    print('   ', sct)
    print(res['reglage_global'], res['controle'])


if __name__ == '__main__':
    sys.exit(main())
