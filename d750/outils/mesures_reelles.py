#!/usr/bin/env python3
"""Écarts réels des looks (ΔE2000, JPEG du boîtier contre la cible) : test v1 du D750 et test du D40, octobre 2026.
Rapport : recherche/resultats-mesures.md. Méthode et cibles de recherche/d750-analyse-seances.md ; rien n'est écrit
dans un boîtier.

Trois comparaisons par vue, sur les blocs uniformes :
- mesuré   : JPEG du boîtier contre la cible, la scène étant prise dans le NEF de la même vue ;
- modèle   : rendu prévu (modèle du D750 ou simulateur du D40) contre le JPEG, ce que le modèle sait prédire ;
- prévu    : rendu prévu contre la cible, sur la même scène.

D750 (images/d750/2026-10-test-v1/, pédalier, 135 mm sans correction, lumière artificielle) : blocs comme
d750_blocs.extraire, points communs par OpenCV (SIFT + RANSAC) si scikit-image manque ; la scène est ramenée à la
balance 5 600 K lue dans le NEF (convention des cibles : la WB réglée ne change pas la scène). Les vues BASE STANDARD
des lots 1 à 4 refont les jeux d'évaluation du §5.1 (géométrie reprise de modele.json).
D40 (images/d40/2026-10-test-v1/, V3, mêmes tables de rendu que la V5) : simulateur.camera (balance du boîtier),
blocs de 6 × 6 en demi-résolution ; scène = M_D40_vers_XYZ des mesures camspec, échelle : gris rendu 118/255 par la
courbe IIIa Normal = Y 0,18. Cibles : celles du D750 (d750_cibles) ; HP5 : fiche Ilford et tirage (cible de la V1 du
D40) ; Classic Chrome : aussi le modèle des JPEG du X-T4 (cible de conception du D40).

  mesures_reelles.py d750 <travail/> <status_A/>       blocs, mesures, prévisions refaites, Tri-X v2 → <travail>/*.json
  mesures_reelles.py d40 <travail/>                    → <travail>/d40.json
  mesures_reelles.py planches <travail/> <status_A/>   recherche/figures/video-avant-apres-*.jpg (vidéo seulement)
  mesures_reelles.py publier <travail/>                résumés sans les blocs → recherche/donnees-films/mesures-reelles/
  mesures_reelles.py lot2 <travail/> <status_A/> [<dossier du lot> [--zone x0,y0,x1,y1]]   lot de contrôle n° 2 (octobre 2026 par défaut, ou une
                                                       série --bibliotheque) → <travail>/<nom du dossier>.json
  mesures_reelles.py isolees <travail/> <status_A/> <dossier>   vues isolées (rangees/NN-NOM, main levée, WB Auto) → <travail>/<nom>.json
  mesures_reelles.py nb_v2 <travail/> <blocs/> <status_A/> [<nom du lot>]   HP5+ et FP4+ : une courbe refaite avec ce lot aide-t-elle ?

Lot n° 2 (images/d750/2026-10-test-v2/, bibliothèque de jour, 28 mm f/5,6) : blocs du centre seulement (rayon < 0,7 :
le boîtier corrige la distorsion du JPEG, le recalage n'est sûr qu'au centre), vignetage f/5,6 du modèle appliqué à la
scène comme au rendu prévu. Recette de chaque vue = bloc réellement envoyé (blocs/NN.bin). Cibles des recettes chargées
(KODACHROME VIF : D750_SPEKTRAFILM ; PORTRA ESPRIT : D750_LOOKS).

D750_LOOKS (le preset Portra) : par défaut images/d750/portra-cibles/preset/.
"""
import json
import os
import pathlib
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
os.environ.setdefault('D750_LOOKS', str(RACINE / 'images' / 'd750' / 'portra-cibles' / 'preset'))
import d750_analyse as da  # noqa: E402
import d750_blocs as db  # noqa: E402
import d750_cibles as dc  # noqa: E402
import d750_modele as dm  # noqa: E402

TEST = RACINE / 'images' / 'd750' / '2026-10-test-v1'
D40 = RACINE / 'images' / 'd40' / '2026-10-test-v1'
MODELE = RACINE / 'recherche' / 'donnees-films' / 'd750-seances' / 'modele.json'
FIG = RACINE / 'recherche' / 'figures'
# vue du test → (cible, recette v1, bloc envoyé, WB réglée)
VUES = {
    'CLASSIC CHROME V1': ('CLASSIC CHROME', 'classic-chrome-v1', 'a-5600K/blocs/01.bin', 5600),
    'CLASSIC NEG V1': ('CLASSIC NEG', 'classic-neg-v1', 'a-5600K/blocs/02.bin', 5600),
    'FP4 V1': ('FP4', 'fp4-v1', 'a-5600K/blocs/03.bin', 5600),
    'HASSELBLAD V1': ('HASSELBLAD', 'hasselblad-v1', 'a-5600K/blocs/04.bin', 5600),
    'HP5 V1': ('HP5', 'hp5-v1', 'a-5600K/blocs/05.bin', 5600),
    'KODACHROME 5600K': ('KODACHROME', 'kodachrome-v1-variante-5600k', 'a-5600K/blocs/06.bin', 5600),
    'KODACHROME V1': ('KODACHROME', 'kodachrome-v1', 'b-5000K/blocs/07.bin', 5000),
    'PORTRA 400 V1': ('PORTRA', 'portra-400-v1', 'a-5600K/blocs/08.bin', 5600),
    'POSITIVE V1': ('POSITIVE', 'positive-v1', 'a-5600K/blocs/09.bin', 5600),
    'TRI-X V1': ('TRI-X', 'tri-x-v1', 'c-10000K/blocs/10.bin', 10000),
    'KODACHROME V1 A 5600K': ('KODACHROME', 'kodachrome-v1', 'b-5000K/blocs/07.bin', 5600),   # prise par erreur à 5 600 K
}
LOTS = {'lot1': 'scene-interieur', 'lot2': 'portrait', 'lot3': 'pedalier', 'lot4': 'bibliotheque'}


# --- géométrie sans scikit-image ----------------------------------------------------------------------------
def _proj(cj, nrm):
    def proj(p, q):
        u = (q - cj) / nrm
        r2 = (u ** 2).sum(1, keepdims=True)
        u = u * (1 + p[4] * r2 + p[5] * r2 ** 2 + p[6] * r2 ** 3)
        c, s = np.cos(p[3]), np.sin(p[3])
        return np.c_[c * u[:, 0] - s * u[:, 1], s * u[:, 0] + c * u[:, 1]] * p[2] * nrm + p[:2]
    return proj


def geometrie_cv(nef, jpg, distorsion=None):
    """Même modèle que d750_blocs.geometrie (similitude + distorsion radiale), points communs par OpenCV."""
    import cv2
    from scipy.optimize import least_squares
    g_r = db._gris(nef.mean(2) / max(np.percentile(nef.mean(2), 99.5), 1e-6))
    g_j = cv2.resize(jpg.mean(2) / 255, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    sift, det = cv2.SIFT_create(), []
    for im in (g_r, g_j):
        im8 = (np.clip(cv2.resize(im, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), 0, 1) * 255).astype(np.uint8)
        kp, des = sift.detectAndCompute(im8, None)
        det.append((np.array([k.pt for k in kp]) / 0.5, des))
    m = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True).match(det[1][1], det[0][1])
    pj, pr = det[1][0][[x.queryIdx for x in m]] * 2, det[0][0][[x.trainIdx for x in m]]
    A, inl = cv2.estimateAffinePartial2D(pj, pr, method=cv2.RANSAC, ransacReprojThreshold=3, maxIters=5000)
    pj, pr = pj[inl.ravel() > 0], pr[inl.ravel() > 0]
    cj = np.array([jpg.shape[1], jpg.shape[0]]) / 2
    proj = _proj(cj, np.hypot(*cj))
    p0 = np.r_[A @ np.r_[cj, 1], np.hypot(A[0, 0], A[1, 0]), np.arctan2(A[1, 0], A[0, 0]), 0, 0, 0]
    res = least_squares(lambda p: (proj(p, pj) - pr).ravel(), p0, loss='soft_l1', f_scale=1)
    err = np.hypot(*(proj(res.x, pj) - pr).T)
    return res.x, proj, dict(points=int(len(pj)), residu_median_px=float(np.median(err)), residu_p95_px=float(np.percentile(err, 95)))


def _lier(dossier, vues):
    """Dossier de lot pour d750_blocs.extraire : plan.json + rangees/NN-NOM.{NEF,JPG} en liens (rien n'est copié)."""
    (dossier / 'rangees').mkdir(parents=True, exist_ok=True)
    for n, (nom, src) in enumerate(vues, 1):
        for e in ('NEF', 'JPG'):
            dst = dossier / 'rangees' / f"{n:02d}-{nom.replace(' ', '_')}.{e}"
            if not dst.exists():
                os.symlink(f'{src}.{e}', dst)
    (dossier / 'plan.json').write_text(json.dumps({'vues': [{'numero': n, 'nom': v[0]} for n, v in enumerate(vues, 1)]}))


def extraire(travail):
    try:
        import skimage  # noqa: F401
    except ImportError:
        db.geometrie = geometrie_cv
    plan = json.loads((TEST / 'plan-complet.json').read_text())['vues']
    vues = [(v['nom'], TEST / 'rangees' / f"{v['numero']:02d}-{v['nom'].replace(' ', '_')}") for v in plan]
    vues.append(('KODACHROME V1 A 5600K', TEST / 'essais-kodachrome-v1-a-5600K' / '07-KODACHROME_V1'))
    _lier(travail / 'lot_test', vues)
    if not (travail / 'blocs' / 'test.npz').exists():
        (travail / 'blocs').mkdir(parents=True, exist_ok=True)
        db.extraire(str(travail / 'lot_test'), str(travail / 'blocs' / 'test.npz'))
    m = json.loads(MODELE.read_text())
    for lot, dos in LOTS.items():   # vues BASE STANDARD des jeux d'évaluation, géométrie d'origine
        if (travail / 'blocs' / f'{lot}.npz').exists():
            continue
        p = np.array(m['lots'][lot]['geometrie'])
        db.geometrie = lambda nef, jpg, distorsion=None, p=p: (p, _proj(np.array([jpg.shape[1], jpg.shape[0]]) / 2,
                                                                         np.hypot(jpg.shape[1], jpg.shape[0]) / 2), {'reprise': 'modele.json'})
        _lier(travail / f'lot_{lot}', [('BASE STANDARD', RACINE / 'images' / 'd750' / f'2026-10-seance-{dos}' / 'rangees' / '01-BASE_STANDARD')])
        db.extraire(str(travail / f'lot_{lot}'), str(travail / 'blocs' / f'{lot}.npz'))


# --- D750 ---------------------------------------------------------------------------------------------------
def contexte(status_a):
    m = json.loads(MODELE.read_text())
    P = {b: m['bases'][b]['parametres'] for b in da.BASES}
    P['_filtres'] = {f: d['poids_capteur'] for f, d in m['filtres'].items()}
    Mc, k, st = da.matrice_camera()
    C = dc.toutes(str(status_a))
    C.update({'TRI-X': dc.cible_nb('preset_trix', dc.courbe_trix_preset()),
              'HP5': dc.cible_nb('hp5_fiche', da.courbe_hp5_scans(m, k)), 'FP4': dc.cible_nb('fp4_fiche', dc.courbe_film('fp4'))})
    return m, P, da.tables_curseurs(m), Mc, k, st, C


def d750(travail, status_a):
    import picture_control as pc
    extraire(travail)
    m, P, tab, Mc, k, st, C = contexte(status_a)
    d = dict(np.load(travail / 'blocs' / 'test.npz', allow_pickle=True))
    noms = [str(n) for n in d['noms']]
    commun = np.logical_and.reduce([da.masque(d, i) for i in range(len(noms))])   # mêmes blocs pour toutes les vues
    ref = d['wb'][noms.index('CLASSIC CHROME V1')]
    lab_cc = dm.code_lab(d['jpg'][0][commun] / 255)
    sature = np.hypot(lab_cc[:, 1], lab_cc[:, 2]) >= 40   # objets très colorés (vert du pédalier surtout)
    out = {'colorimetrie_mire': st, 'blocs_communs': int(commun.sum()), 'part_blocs_chroma_40_et_plus': round(float(sature.mean()), 3), 'vues': []}
    for i, n in enumerate(noms):
        prof, fr, fb, K = VUES[n]
        r, _ = da.lut_recette(RACINE / 'recettes' / 'd750-v1' / 'usb' / f'{fr}.json')
        envoye = pc.lire_bloc_ptp((TEST / fb).read_bytes())
        x, j = d['raw'][i][commun].astype(float), d['jpg'][i][commun].astype(float) / 255
        L = C[prof](k * da.cam_xyz(x * (ref / d['wb'][i]), Mc))
        pred, _ = da.rendu_complet(P, tab, r, dict(x=x, j=j, r=None, vig=None))
        Lj, Lp = dm.code_lab(j), dm.code_lab(pred)
        e = dm.de2000(Lj, L)
        cb, cp = np.hypot(*Lj[:, 1:].T), np.hypot(*Lp[:, 1:].T)
        dh = (np.degrees(np.arctan2(Lj[:, 2], Lj[:, 1]) - np.arctan2(Lp[:, 2], Lp[:, 1])) + 180) % 360 - 180
        row = {'vue': n, 'profil': prof, 'recette': fr, 'bloc_envoye_identique': all(envoye.get(c) == r.get(c) for c in ('base', 'saturation', 'teinte', 'filtre', 'lut') if c in r),
               'kelvin': K, 'gains_wb_nef_sur_5600': np.round(d['wb'][i] / ref, 4).tolist(), 'gains_wb_calcules': np.round(da.gains_kelvin(K, Mc), 4).tolist(),
               'mesure': dm.stats(e), 'mesure_sans_objets_satures': dm.stats(e[~sature]),
               'modele_contre_jpeg': dm.stats(dm.de2000(Lp, Lj)), 'prevu': dm.stats(dm.de2000(Lp, L)),
               'jpeg_moins_modele': {'dL': round(float(np.median(Lj[:, 0] - Lp[:, 0])), 2),
                                     'teinte_deg': round(float(np.median(dh[cp > 10])), 1) if (cp > 10).any() else None,
                                     'chroma_x': round(float(np.median(cb[cp > 10] / cp[cp > 10])), 3) if (cp > 10).any() else None},
               'secteurs_mesure': da.ecarts_par_teinte(Lj, L)}
        out['vues'].append(row)
        print(n, row['mesure'], 'modèle', row['modele_contre_jpeg'], 'prévu', row['prevu'], flush=True)
    (travail / 'd750.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    prevision(travail, status_a, {K: d['wb'][noms.index(v)] / ref for v, K in (('KODACHROME V1', 5000), ('TRI-X V1', 10000))})


def prevision(travail, status_a, gains_nef):
    """Écarts prévus du §5.1 refaits ici, puis avec les gains de WB lus dans les NEF (5 000 et 10 000 K), puis Tri-X v2."""
    R = json.loads((RACINE / 'recettes' / 'd750-v1' / 'resume.json').read_text())

    def rec(nom, profil, base, fichier, kelvin=5600, filtre=None):
        r, lut = da.lut_recette(RACINE / 'recettes' / 'd750-v1' / fichier)
        return {'nom': nom, 'profil': profil, 'base': base, 'saturation': r.get('saturation'), 'teinte': r.get('teinte'),
                'filtre': filtre, 'kelvin': kelvin, 'lut_257': lut}
    L = [rec(i['nom'], i['profil'], i['base'], f"usb/{i['nom'].lower().replace(' ', '-')}.json", i.get('kelvin', 5600), i.get('filtre')) for i in R]
    k5 = next(i for i in R if i['profil'] == 'KODACHROME')['variante_5600K']
    L.append(rec('KODACHROME 5600K', 'KODACHROME', k5['base'], k5['fichier']))
    dossier = str(travail / 'blocs')
    out = {'gains_nef': {str(K): np.round(g, 4).tolist() for K, g in gains_nef.items()},
           'calcules': da.evaluer_recettes(dossier, str(MODELE), str(status_a), L)}
    calc = da.gains_kelvin
    da.gains_kelvin = lambda K, Mc, ref=5600: np.asarray(gains_nef[K]) if K in gains_nef else calc(K, Mc, ref)
    out['avec_gains_nef'] = da.evaluer_recettes(dossier, str(MODELE), str(status_a), [r for r in L if r['kelvin'] in gains_nef])
    m, P, tab, Mc, k, st, C = contexte(status_a)
    J = da.jeux(dossier, m)
    xyz = {j: da.xyz_jeu(J[j], Mc, k, P['STANDARD']['vig']) for j in da.JEUX}
    Lc = [C['TRI-X'](xyz[j]) for j in da.JEUX]
    essais = []
    for filt in m['filtres']:
        for K in (10000, 5600):
            pm = {**P['MONOCHROME'], 'w': (np.array(m['filtres'][filt]['poids_capteur']) * da.gains_kelvin(K, Mc)).tolist()}
            codes = [da.base_jeu({**P, 'MONOCHROME': pm}, 'MONOCHROME', J[j]) for j in da.JEUX]
            _, _, lut = da.optimiser(codes, Lc, 1, 0, fixer=True)
            n = da.noter(codes, Lc, 1, 0, lut)
            essais.append({'filtre': filt, 'kelvin': K, 'ecarts': n, 'score': round(da.score(n), 3), 'lut_257': np.round(lut, 5).tolist()})
    da.gains_kelvin = calc
    out['trix_v2'] = sorted(essais, key=lambda e: e['score'])
    for r in out['calcules'] + out['avec_gains_nef']:
        r.pop('secteurs', None)
    (travail / 'prevision.json').write_text(json.dumps(out, ensure_ascii=False, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)))
    print('Tri-X v2', [(e['filtre'], e['kelvin'], e['ecarts']['scene']['mediane'], e['score']) for e in out['trix_v2'][:3]])


# --- D40 ----------------------------------------------------------------------------------------------------
LOOKS40 = {'Soft': ('HASSELBLAD', 'hasselblad'), 'Vivid': ('CLASSIC CHROME', 'chrome'), 'More Vivid': ('POSITIVE', 'positive'),
           'Portrait': ('TRI-X', 'tri-x'), 'Black And White': ('HP5', 'hp5')}


def contexte_d40():
    M = np.array(json.loads((RACINE / 'recettes' / 'mesures' / 'hncs.json').read_text())['M_D40_vers_XYZ'])
    nk = np.array(json.loads((RACINE / 'recettes' / 'v1' / 'nikon.json').read_text())['courbe']) / 4095
    v_gris = float(np.interp(118 / 255, nk, np.linspace(0, 1, 4096)))
    C = {'HASSELBLAD': dc.rendu_mesure('hncs.json')[0], 'CLASSIC CHROME': dc.fuji('CLASSIC-CHROME'),
         'CLASSIC CHROME (X-T4)': dc.rendu_mesure('classic-chrome.json')[0], 'POSITIVE': dc.rendu_mesure('positive-film.json')[0],
         'TRI-X': dc.cible_nb('preset_trix', dc.courbe_trix_preset()), 'HP5': dc.cible_nb('hp5_fiche', dc.courbe_film('hp5'))}
    return M, 0.18 / (v_gris * (M @ np.ones(3))[1]), C


def blocs_d40(nef, recette, F=6, gain=1.0):
    from PIL import Image
    import simulateur as sm
    cam = sm.camera(nef, half=True, tourner=False) * gain
    J = np.asarray(Image.open(nef.with_suffix('.JPG')).convert('RGB').resize((cam.shape[1], cam.shape[0]), Image.BOX), np.float32) / 255
    mat, courbe, jeu = sm.recette(RACINE / 'recettes' / 'v1' / f'{recette}.json', 1)
    sim = sm.rendre(cam, mat, courbe, 1.0, jeu)
    h, w = cam.shape[0] // F * F, cam.shape[1] // F * F
    bl = lambda a: a[:h, :w].reshape(h // F, F, w // F, F, 3)
    jb, cb = bl(J), bl(cam)
    jm, cm, sm_ = jb.mean((1, 3)).reshape(-1, 3), cb.mean((1, 3)).reshape(-1, 3), bl(sim).mean((1, 3)).reshape(-1, 3)
    js, cs = jb.std((1, 3)).reshape(-1, 3), cb.std((1, 3)).reshape(-1, 3)
    ok = (js.max(1) < np.maximum(2.5 / 255, 0.04 * jm.mean(1))) & (jm.min(1) > 2 / 255) & (jm.max(1) < 253 / 255)
    ok &= ((cs / np.maximum(cm, 1e-4)).max(1) < 0.08) & (cm.max(1) < 0.9) & (cm.min(1) > 2e-4)
    return jm[ok], sm_[ok], cm[ok]


def d40(travail):
    M, ech, C = contexte_d40()
    ex = {l.split('\t')[0][:-4]: l.rstrip('\n').split('\t') for l in open(RACINE / 'sondes' / 'v1' / 'test-10' / 'exif.tsv', encoding='utf-8')}
    out = {'vues': [], 'looks': {}}
    E = {}
    for nef in sorted(D40.glob('*.NEF')):
        e = ex.get(nef.stem)
        if not e or e[14] not in LOOKS40 or e[2] == 'Not Defined':   # mode Auto : rendu Nikon
            continue
        prof, recette = LOOKS40[e[14]]
        jm, s, cm = blocs_d40(nef, recette)
        xyz = cm @ M.T * ech
        Lj, Ls = dm.code_lab(jm), dm.code_lab(s)
        row = {'nef': nef.stem, 'preglage': e[14], 'profil': prof, 'flash': e[8].startswith('Fired'), 'iso': e[5], 'blocs': len(jm),
               'simulateur_contre_jpeg': dm.stats(dm.de2000(Ls, Lj)), 'jpeg_moins_simulateur_dL': round(float(np.median(Lj[:, 0] - Ls[:, 0])), 2)}
        if prof == 'HP5':   # mode N&B : le boîtier applique un gain vert de 1,082 (WB notée « … 1.082 1.082 ») que LibRaw retire
            jm2, s2, _ = blocs_d40(nef, recette, gain=1.082)
            row['simulateur_contre_jpeg_gain_1082'] = dm.stats(dm.de2000(dm.code_lab(s2), dm.code_lab(jm2)))
        for c in [prof] + (['CLASSIC CHROME (X-T4)'] if prof == 'CLASSIC CHROME' else []):
            L = C[c](xyz)
            em, ep = dm.de2000(Lj, L), dm.de2000(Ls, L)
            row[c] = {'mesure': dm.stats(em), 'prevu': dm.stats(ep), 'secteurs_mesure': da.ecarts_par_teinte(Lj, L)}
            E.setdefault(c, []).append((em, ep))
        out['vues'].append(row)
        print(nef.stem, e[14], {c: row[c]['mesure'] for c in row if isinstance(row[c], dict) and 'mesure' in row[c]}, flush=True)
    for c, v in E.items():
        out['looks'][c] = {'vues': len(v), 'blocs': int(sum(len(a) for a, _ in v)), 'mesure': dm.stats(np.concatenate([a for a, _ in v])),
                           'prevu': dm.stats(np.concatenate([b for _, b in v])), 'mediane_par_vue': [dm.stats(a)['mediane'] for a, _ in v]}
        print(c, out['looks'][c])
    (travail / 'd40.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))


# --- planches pour la vidéo -----------------------------------------------------------------------------------
def _reduire(a, f):
    h, w = a.shape[0] // f * f, a.shape[1] // f * f
    return a[:h, :w].reshape(h // f, f, w // f, f, 3).mean((1, 3))


def _planche(cible, jpeg, titre, sous, ecart, sortie):
    from PIL import Image, ImageDraw
    import figures_v1 as fg
    im = Image.new('RGB', (1920, 1080), (18, 18, 18))
    d = ImageDraw.Draw(im)
    d.text((60, 30), titre, fill=(240, 240, 240), font=fg.police(46, True))
    d.text((60, 92), sous, fill=(170, 170, 170), font=fg.police(26))
    W, H = 880, 800
    for i, (a, t) in enumerate(((cible, 'Cible : le rendu visé'), (jpeg, 'JPEG sorti du boîtier'))):
        p = Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8))
        p.thumbnail((W, H - 60), Image.LANCZOS)
        im.paste(p, (60 + i * (W + 40) + (W - p.width) // 2, 150))
        d.text((60 + i * (W + 40) + (W - d.textlength(t, font=fg.police(30))) / 2, 150 + p.height + 14), t, fill=(230, 230, 230), font=fg.police(30))
    d.text((60, 1020), ecart, fill=(120, 230, 140), font=fg.police(30, True))
    im.save(sortie, quality=92)
    print(sortie.name)


def planches(travail, status_a):
    from PIL import Image
    import simulateur as sm
    virg = lambda v: f'{v:.1f}'.replace('.', ',')
    m, P, tab, Mc, k, st, C = contexte(status_a)
    R = {r['vue']: r for r in json.loads((travail / 'd750.json').read_text())['vues']}
    T = TEST / 'rangees'
    _, wref, _ = db.nef_demi(str(T / '01-CLASSIC_CHROME_V1.NEF'))
    for vue, f, nom, wb in [('KODACHROME V1', '07-KODACHROME_V1', 'Kodachrome', 'WB 5 000 K'), ('CLASSIC CHROME V1', '01-CLASSIC_CHROME_V1', 'Classic Chrome', ''),
                            ('CLASSIC NEG V1', '02-CLASSIC_NEG_V1', 'Classic Neg', ''), ('POSITIVE V1', '09-POSITIVE_V1', 'Positive', ''),
                            ('PORTRA 400 V1', '08-PORTRA_400_V1', 'Portra 400', ''), ('HASSELBLAD V1', '04-HASSELBLAD_V1', 'Hasselblad', ''),
                            ('TRI-X V1', '10-TRI-X_V1', 'Tri-X', 'WB 10 000 K'), ('HP5 V1', '05-HP5_V1', 'HP5+', ''), ('FP4 V1', '03-FP4_V1', 'FP4+', '')]:
        prof = VUES[vue][0]
        nef, _, _ = db.nef_demi(str(T / f'{f}.NEF'))
        x = _reduire(nef[4:2012, 4:3012] * wref, 3)   # JPEG (6016 × 4016) → NEF demi-résolution : décalage de 4, échelle 1/2 (géométrie mesurée)
        cible = dm.lab_code(C[prof](k * da.cam_xyz(x.reshape(-1, 3), Mc))).reshape(x.shape)
        j = _reduire(db.jpeg(str(T / f'{f}.JPG'))[:4014, :6012] / 255, 6)
        r = R[vue]['mesure']
        _planche(cible, j[:cible.shape[0], :cible.shape[1]], f'{nom} · Nikon D750',
                 f'Picture Control calculé, chargé par USB · test d’octobre 2026, lumière artificielle · {wb or "WB 5 600 K"}',
                 f'Écart mesuré : ΔE2000 médian {virg(r["mediane"])} (90 % des zones sous {virg(r["p90"])})',
                 FIG / f'video-avant-apres-d750-{prof.lower().replace(" ", "-")}.jpg')
    M, ech, C40 = contexte_d40()
    R40 = {r['nef']: r for r in json.loads((travail / 'd40.json').read_text())['vues']}
    for nef, nom, cle, note in [('DSC_6261', 'Hasselblad', 'HASSELBLAD', 'Soft'), ('DSC_6262', 'Classic Chrome', 'CLASSIC CHROME (X-T4)', 'Vivid'),
                                ('DSC_6301', 'Positive', 'POSITIVE', 'More Vivid'), ('DSC_6266', 'Tri-X', 'TRI-X', 'Portrait'),
                                ('DSC_6272', 'HP5+', 'HP5', 'Black And White')]:
        cam = sm.camera(D40 / f'{nef}.NEF', half=True, tourner=False)
        cible = dm.lab_code(C40[cle](cam.reshape(-1, 3) @ M.T * ech)).reshape(cam.shape)
        jp = Image.open(D40 / f'{nef}.JPG')
        rot = {3: 2, 6: 3, 8: 1}.get(jp.getexif().get(274, 1), 0)
        j = np.asarray(jp.convert('RGB').resize((cam.shape[1], cam.shape[0]), Image.BOX), np.float32) / 255
        r = R40[nef][cle]['mesure']
        _planche(np.rot90(cible, rot), np.rot90(j, rot), f'{nom} · Nikon D40',
                 f'Firmware modifié (rendus de la V1, identiques en V5), préréglage {note} · {nef}, octobre 2026',
                 f'Écart mesuré : ΔE2000 médian {virg(r["mediane"])} (90 % des zones sous {virg(r["p90"])})',
                 FIG / f"video-avant-apres-d40-{cle.split(' (')[0].lower().replace(' ', '-')}.jpg")


def optique(nef):
    """(groupe de vignetage, rayon max des blocs) d'après l'objectif noté dans le NEF : 28 mm (distorsion corrigée par le
    boîtier, recalage sûr au centre, vignetage mesuré à f/1,8 et f/5,6) ; autre objectif (135 mm manuel des lots 3 et du
    test v1) : ni vignetage ni limite de rayon, comme pour le pédalier."""
    import subprocess
    d = json.loads(subprocess.run(['exiftool', '-j', '-n', '-FocalLength', '-FNumber', str(nef)], capture_output=True, text=True).stdout)[0]
    if abs(d.get('FocalLength', 0) - 28) < 1:
        return ('f18' if d.get('FNumber', 5.6) < 4 else 'f56'), da.RAYON_MAX_28MM
    return None, 9.0


LOT2 = RACINE / 'images' / 'd750' / '2026-10-test-v2'
CIBLE_LOT2 = {'CLASSIC CHROME': 'CLASSIC CHROME', 'CLASSIC NEG': 'CLASSIC NEG', 'POSITIVE': 'POSITIVE', 'PORTRA 400': 'PORTRA ESPRIT',
              'HASSELBLAD': 'HASSELBLAD', 'HP5+': 'HP5', 'FP4+': 'FP4', 'KODACHROME': 'KODACHROME VIF', 'TRI-X': 'TRI-X',
              'TRI-X V2': 'TRI-X'}


def lot2(travail, status_a, dossier=LOT2, zone=None):
    """zone : (x0, y0, x1, y1) en fractions du JPEG tel qu'enregistré (sans rotation) ; seuls les blocs dedans comptent."""
    import picture_control as pc
    import d750_cibles as dc
    try:
        import skimage  # noqa: F401
    except ImportError:
        db.geometrie = geometrie_cv
    dossier = pathlib.Path(dossier).resolve()
    nom = 'lot2' if dossier == LOT2 else dossier.name
    vues, blocs = [], {}
    for K in sorted((int(f.parent.name) for f in dossier.glob('*/plan.json')), key=lambda K: (K != 5600, K)):
        for v in json.loads((dossier / str(K) / 'plan.json').read_text())['vues']:
            vues.append((v['nom'], dossier / str(K) / 'rangees' / f"{v['numero']:02d}-{v['nom'].replace(' ', '_')}"))
            blocs[v['nom']] = (pc.lire_bloc_ptp((dossier / str(K) / v['bloc']).read_bytes()), K)
    base = vues.pop(next(i for i, v in enumerate(vues) if v[0] == 'BASE STANDARD'))
    vues.insert(0, base)   # extraire recale sur la première vue
    _lier(travail / nom, vues)
    npz = travail / 'blocs' / f'{nom}.npz'
    if not npz.exists():
        npz.parent.mkdir(parents=True, exist_ok=True)
        db.extraire(str(travail / nom), str(npz))
    m, P, tab, Mc, k, st, C = contexte(status_a)
    C.update({c: f for c, f in dc.toutes(str(status_a)).items() if c not in C})
    d = dict(np.load(npz, allow_pickle=True))
    noms = [str(n) for n in d['noms']]
    # mêmes blocs pour tous les looks : uniformes et non écrêtés dans BASE STANDARD et chaque look (pas dans les vues de WB
    # ni de crans, dont l'écrêtage ne concerne pas les looks), au centre
    commun = np.logical_and.reduce([da.masque(d, i) for i, n in enumerate(noms) if n in CIBLE_LOT2 or n == 'BASE STANDARD'])
    gv, rmax = optique(vues[0][1].with_suffix('.NEF'))
    commun &= d['rayon'] < rmax
    if zone:
        W, H = 6016, 4016
        cx, cy = d['centres'][:, 0] / W, d['centres'][:, 1] / H
        commun &= (cx >= zone[0]) & (cx <= zone[2]) & (cy >= zone[1]) & (cy <= zone[3])
    r_ = d['rayon'][commun].astype(float)
    vig = P['STANDARD']['vig']
    ref = d['wb'][noms.index('BASE STANDARD')]
    out = {'lot': str(dossier.resolve().relative_to(RACINE)) if RACINE in dossier.resolve().parents else str(dossier), 'colorimetrie_mire': st, 'blocs_communs': int(commun.sum()), 'looks': [], 'wb': [], 'crans': []}
    for i, n in enumerate(noms):
        r, K = blocs[n]
        x, j = d['raw'][i][commun].astype(float), d['jpg'][i][commun].astype(float) / 255
        g_nef = d['wb'][i] / ref
        if K != 5600:
            out['wb'].append({'vue': n, 'kelvin': K, 'gains_nef_sur_5600': np.round(g_nef, 4).tolist(),
                              'gains_calcules': np.round(da.gains_kelvin(K, Mc), 4).tolist()})
        v = dict(x=x, j=j, r=r_, vig=gv)
        if n in CIBLE_LOT2:
            prof = CIBLE_LOT2[n]
            L = C[prof](da.scene_xyz(x / g_nef, Mc, k, vig, r_, gv))
            pred, _ = da.rendu_complet(P, tab, r, v)
            Lj, Lp = dm.code_lab(j), dm.code_lab(np.clip(pred, 0, 1))
            row = {'vue': n, 'cible': prof, 'kelvin': K, 'mesure': dm.stats(dm.de2000(Lj, L)),
                   'modele_contre_jpeg': dm.stats(dm.de2000(Lp, Lj)), 'prevu': dm.stats(dm.de2000(Lp, L)),
                   'secteurs_mesure': da.ecarts_par_teinte(Lj, L)}
            out['looks'].append(row)
            print(n, 'mesuré', row['mesure'], 'modèle', row['modele_contre_jpeg'], 'prévu', row['prevu'], flush=True)
        elif n.startswith('STANDARD '):
            code = da.base_rendu(P['STANDARD'], x, r_, gv)
            g, t = da.ajuster_op_cbcr(code, j)
            cle = 'SAT' if r['saturation'] else 'TEI'
            cran = r['saturation'] or r['teinte']
            row = {'vue': n, 'curseur': cle, 'cran': cran, 'mesure': {'gain_cbcr': round(float(g), 3), 'rotation_deg': round(float(t), 2)},
                   'modele': da.curseur(tab, 'STANDARD', cle, cran),
                   'ecart_modele_contre_jpeg': dm.stats(dm.de2000(dm.code_lab(np.clip(da.rendu_recette(code, da.curseur(tab, 'STANDARD', 'SAT', r['saturation']),
                                                                                                         da.curseur(tab, 'STANDARD', 'TEI', r['teinte']), None), 0, 1)),
                                                                   dm.code_lab(j)))}
            out['crans'].append(row)
            print(n, row['mesure'], 'modèle', round(row['modele'], 3), flush=True)
    for w in out['wb']:
        print('WB', w['vue'], w['kelvin'], 'NEF', w['gains_nef_sur_5600'], 'calcul', w['gains_calcules'])
    (travail / f'{nom}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)))



def isolees(travail, status_a, dossier):
    """Vues prises une à une (main levée, exposition et WB du boîtier) : chaque JPEG recalé sur son propre NEF, blocs du
    centre. Recette = le Picture Control chargé du même nom (dernier bloc écrit, d750_historique). Deux cibles : scène
    ramenée à 5 600 K (convention des recettes : la WB réglée fait partie du rendu) et scène à la WB du boîtier (le
    Picture Control seul, sans l'écart de WB)."""
    import picture_control as pc
    import d750_cibles as dc
    import d750_historique as dh
    try:
        import skimage  # noqa: F401
    except ImportError:
        db.geometrie = geometrie_cv
    dossier = pathlib.Path(dossier).resolve()
    charges = {}
    for e in dh.ecritures():
        charges[e['apres']['nom'].upper()] = pc.lire_bloc_ptp((RACINE / e['apres']['fichier']).read_bytes())
    m, P, tab, Mc, k, st, C = contexte(status_a)
    C.update({c: f for c, f in dc.toutes(str(status_a)).items() if c not in C})
    ref = np.array([2.01953125, 1.0, 1.2734375])   # WB 5 600 K du D750 (WB_RBLevels des NEF des lots, R V B)
    out = {'dossier': str(dossier.relative_to(RACINE)) if RACINE in dossier.parents else str(dossier), 'vues': []}
    for f in sorted((dossier / 'rangees').glob('*.NEF')):
        nom = f.stem.split('-', 1)[1].replace('_', ' ')
        r = charges[nom]
        lot = travail / dossier.name / f.stem
        _lier(lot, [(nom, f.with_suffix(''))])
        npz = travail / 'blocs' / dossier.name / f'{f.stem}.npz'
        if not npz.exists():
            npz.parent.mkdir(parents=True, exist_ok=True)
            db.extraire(str(lot), str(npz))
        d = dict(np.load(npz, allow_pickle=True))
        gv, rmax = optique(f)
        ok = da.masque(d, 0) & (d['rayon'] < rmax)
        x, j, r_ = d['raw'][0][ok].astype(float), d['jpg'][0][ok].astype(float) / 255, d['rayon'][ok].astype(float)
        wb = d['wb'][0]
        prof = CIBLE_LOT2[nom]
        Lj = dm.code_lab(j)
        L56 = C[prof](da.scene_xyz(x * ref / wb, Mc, k, P['STANDARD']['vig'], r_, gv))
        Lwb = C[prof](da.scene_xyz(x, Mc, k, P['STANDARD']['vig'], r_, gv))
        pred, _ = da.rendu_complet(P, tab, r, dict(x=x, j=j, r=r_, vig=gv))
        Lp = dm.code_lab(np.clip(pred, 0, 1))
        row = {'vue': f.stem, 'cible': prof, 'blocs': int(ok.sum()), 'wb_sur_5600': np.round(wb / ref, 4).tolist(),
               'mesure_5600K': dm.stats(dm.de2000(Lj, L56)), 'mesure_wb_boitier': dm.stats(dm.de2000(Lj, Lwb)),
               'modele_contre_jpeg': dm.stats(dm.de2000(Lp, Lj)), 'prevu_wb_boitier': dm.stats(dm.de2000(Lp, Lwb))}
        out['vues'].append(row)
        print(f.stem, 'blocs', row['blocs'], '5600K', row['mesure_5600K'], 'WB boîtier', row['mesure_wb_boitier'], 'modèle', row['modele_contre_jpeg'], flush=True)
    (travail / f'{dossier.name}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)))


def nb_v2(travail, blocs, status_a, lot='lot2'):
    """HP5+ et FP4+ : au lot n° 2, écart de 5,2 et 5,4, tout en clarté. Une courbe refaite aide-t-elle ? Mêmes jeux que la livraison (scène des lots 1, 3, 4 ; peau ; mire) plus un quatrième, la scène du lot n° 2 (vue
    BASE STANDARD, blocs du centre) ; chaque jeu pèse autant. Filtre essayé parmi les cinq, WB 5 600 K, courbe refaite.
    Recette écrite dans recettes/d750-v2/usb/ seulement si le score gagne plus de 0,2. Résultat d’octobre 2026 : non (rapport)."""
    m, P, tab, Mc, k, st, C = contexte(status_a)
    J = da.jeux(str(blocs), m)
    d = dict(np.load(travail / 'blocs' / f'{lot}.npz', allow_pickle=True))
    ok = da.masque(d, 0) & (d['rayon'] < da.RAYON_MAX_28MM)
    s = np.sort(np.random.default_rng(0).choice(int(ok.sum()), min(2500, int(ok.sum())), replace=False))
    J['scene_lot2'] = {'x': d['raw'][0][ok].astype(float)[s], 'r': d['rayon'][ok].astype(float)[s], 'vig': np.array(['f56'] * len(s))}
    jeux = list(da.JEUX) + ['scene_lot2']
    xyz = {j: da.xyz_jeu(J[j], Mc, k, P['STANDARD']['vig']) for j in jeux}
    note = lambda codes, L, lut: {j: dm.stats(dm.de2000(dm.code_lab(da.rendu_recette(c, 1, 0, lut)), l)) for j, c, l in zip(jeux, codes, L)}
    score = lambda n: float(np.mean([n[j]['mediane'] for j in jeux]) + 0.25 * np.mean([n[j]['p90'] for j in jeux]))
    out = {}
    for prof, f1, nom in (('HP5', 'hp5-v1', 'hp5'), ('FP4', 'fp4-v1', 'fp4')):
        L = [C[prof](xyz[j]) for j in jeux]
        r1 = json.loads((RACINE / 'recettes' / 'd750-v1' / 'usb' / f'{f1}.json').read_text())
        lut1 = np.array(r1['courbe']['lut']) / 32767
        pm1 = {**P['MONOCHROME'], 'w': m['filtres'][r1['reglages']['filtre'].upper()]['poids_capteur']}
        n1 = note([da.base_jeu({**P, 'MONOCHROME': pm1}, 'MONOCHROME', J[j]) for j in jeux], L, lut1)
        essais = []
        for filt in m['filtres']:
            pm = {**P['MONOCHROME'], 'w': m['filtres'][filt]['poids_capteur']}
            codes = [da.base_jeu({**P, 'MONOCHROME': pm}, 'MONOCHROME', J[j]) for j in jeux]
            _, _, lut = da.optimiser(codes, L, 1, 0, fixer=True)
            n = note(codes, L, lut)
            essais.append({'filtre': filt, 'ecarts': n, 'score': round(score(n), 3), 'lut': lut})
            print(prof, filt, round(score(n), 3), {j: n[j]['mediane'] for j in jeux}, flush=True)
        e = min(essais, key=lambda e: e['score'])
        if e['score'] < score(n1) - 0.2:   # une v2 seulement si elle gagne nettement (sinon : précision du modèle)
            r2 = {**r1, 'reglages': {**r1['reglages'], 'filtre': e['filtre'].lower()}, 'courbe': {'lut': da.lut_entiers(e['lut'])}}
            (RACINE / 'recettes' / 'd750-v2' / 'usb' / f'{nom}.json').write_text(json.dumps(r2, ensure_ascii=False))
        out[prof] = {'v1': {'filtre': r1['reglages']['filtre'], 'ecarts': n1, 'score': round(score(n1), 3)},
                     'v2': {'filtre': e['filtre'].lower(), 'ecarts': e['ecarts'], 'score': e['score']},
                     'essais': [{k: v for k, v in x.items() if k != 'lut'} for x in essais]}
        print(prof, 'v1', out[prof]['v1']['score'], {j: n1[j]['mediane'] for j in jeux}, '→ v2', e['filtre'], e['score'], flush=True)
    (travail / 'nb_v2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))


def publier(travail):
    """Résumés (sans blocs ni courbes) dans recherche/donnees-films/mesures-reelles/ : ce que cite le rapport."""
    dst = RACINE / 'recherche' / 'donnees-films' / 'mesures-reelles'
    dst.mkdir(parents=True, exist_ok=True)
    for f in ('d750.json', 'd40.json', 'lot2.json'):
        if (travail / f).exists():
            (dst / f).write_text((travail / f).read_text())
    p = json.loads((travail / 'prevision.json').read_text())
    for e in p['trix_v2']:
        e.pop('lut_257', None)
    for r in p['calcules'] + p['avec_gains_nef']:
        r.pop('lut_257', None)
    (dst / 'prevision.json').write_text(json.dumps(p, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == 'd750':
        d750(pathlib.Path(a[1]), pathlib.Path(a[2]))
    elif len(a) == 2 and a[0] == 'd40':
        d40(pathlib.Path(a[1]))
    elif len(a) == 3 and a[0] == 'planches':
        planches(pathlib.Path(a[1]), pathlib.Path(a[2]))
    elif len(a) == 4 and a[0] == 'isolees':
        isolees(pathlib.Path(a[1]), pathlib.Path(a[2]), pathlib.Path(a[3]))
    elif len(a) in (4, 5) and a[0] == 'nb_v2':
        nb_v2(pathlib.Path(a[1]), pathlib.Path(a[2]), pathlib.Path(a[3]), *a[4:])
    elif len(a) in (3, 4, 6) and a[0] == 'lot2':
        z = tuple(float(v) for v in a[5].split(',')) if len(a) == 6 and a[4] == '--zone' else None
        lot2(pathlib.Path(a[1]), pathlib.Path(a[2]), *(pathlib.Path(x) for x in a[3:4]), zone=z)
    elif len(a) == 2 and a[0] == 'publier':
        publier(pathlib.Path(a[1]))
    else:
        print(__doc__)
        sys.exit(2)
