#!/usr/bin/env python3
"""Analyse des séances de calibration du D750 (octobre 2026) : modèle du traitement JPEG, choix des bases, recettes v1.

Données : blocs uniformes de chaque vue, produits par d750_blocs.py à partir des lots de séance
(lot 1 pièce aux guitares, ISO auto ; lot 2 portrait ; lot 3 pédalier ; lot 4 bibliothèque ; lot 5 complément).
Chaque JPEG est comparé à son propre NEF. Les écarts sont des ΔE2000 (médiane, 90e centile).

  d750_analyse.py modele <dossier des .npz> <sortie.json>          bases, curseurs, courbe perso, Monochrome, filtres
  d750_analyse.py bases <dossier> <modele.json> <status_A/> <sortie.json>   meilleure base par profil couleur
  d750_analyse.py nb <dossier> <modele.json> <sortie.json>                   Tri-X, HP5, FP4 : filtre, WB (Tri-X), courbe
  d750_analyse.py balance <dossier> <modele.json> <status_A/> <sortie.json> "PROFIL:BASE,..." [--kelvins …] [--vm …]
      effet d'une WB fixe (kelvins) et du réglage fin vert-magenta
  d750_analyse.py validation <dossier> <modele.json> <status_A/> <sortie.json>   v0 photographiées, Portra actuel
  d750_analyse.py cible-paires <paires.npz> <sortie.json> [--wb-libre] [--look <profil.xmp>] [--lisse 0.3] [--grain]   rendu logiciel mesuré
      (Portra : le preset Portra ; avec --look, la table du profil est appliquée telle quelle, seule sa base est ajustée)
  d750_analyse.py recettes <bases.json> <nb.json> <validation.json> <balance.json> <recettes/d750-v1/>

Conventions :
- x = RVB capteur, noir soustrait, fraction de la pleine échelle, balance de la vue appliquée (vert = 1) ;
- rendu d'une base : code = étage_CbCr(T(V(r) · x · Mᵀ)), T même courbe sur R, V, B (d750_modele) ;
- saturation et teinte : gain et rotation globaux dans le plan CbCr (BT.601) ; courbe perso : table de 257 valeurs
  appliquée à la luma Y' (BT.601) en sortie de base, Cb et Cr inchangés (mesuré, voir le rapport) ;
- scène : XYZ = k · M_cam · V(r) · x, M_cam ajustée sur la mire d'Imaging Resource (D750, 164 plages), k tel que le
  gris de 18 % de cette mire soit à Y = 0,18 (calage du posemètre).
"""
import json
import pathlib
import sys

import numpy as np
from scipy.optimize import least_squares

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import d750_modele as dm  # noqa: E402

RACINE = ICI.parent
LOTS = {'lot1': {'nom': 'pièce aux guitares', 'vig': 'f18'}, 'lot2': {'nom': 'portrait', 'vig': 'f18'},
        'lot3': {'nom': 'pédalier', 'vig': None}, 'lot4': {'nom': 'bibliothèque', 'vig': 'f56'},
        'lot5': {'nom': 'complément (bibliothèque)', 'vig': 'f56'}}
BASES = ['STANDARD', 'NEUTRE', 'SATURE', 'MONOCHROME', 'PORTRAIT', 'PAYSAGE', 'UNIFORME']
COULEUR = [b for b in BASES if b != 'MONOCHROME']
COURT = {b: b[:8] for b in BASES}
APPRENTISSAGE = ['lot1', 'lot3', 'lot4']
# passe critique : au 28 mm, la distorsion radiale ajustée diverge au-delà de 0,7 du demi-diagonale (facteur 1,04 à 0,8,
# 1,26 au coin) et les blocs y sont mal recalés (écart du modèle 0,9 au centre, 5 au-delà de 0,8 au lot 4) : écartés
RAYON_MAX_28MM = 0.7   # le lot 2 (peau) reste à part pour le contrôle des bases
NE = len(dm.ETAGE_NEUTRE)


# --- données ------------------------------------------------------------------------------------------------
_CACHE = {}


def charger(dossier, lot):
    cle = (str(dossier), lot)
    if cle not in _CACHE:
        f = pathlib.Path(dossier) / f'{lot}.npz'
        if not f.exists():
            return None
        d = dict(np.load(f, allow_pickle=True))
        d['noms'] = [str(n) for n in d['noms']]
        _CACHE[cle] = d
    return _CACHE[cle]


def masque(d, k):
    """Blocs uniformes et non écrêtés de la vue k (côté JPEG comme côté NEF)."""
    j, js, r, rs, rm = d['jpg'][k], d['jpg_std'][k], d['raw'][k], d['raw_std'][k], d['raw_max'][k]
    ok = d['dedans'] & (rm < 0.9) & (j.min(1) > 2) & (j.max(1) < 253) & (r.min(1) > 2e-4)
    ok &= js.max(1) < np.maximum(2.5, 0.04 * j.mean(1))
    ok &= (rs / np.maximum(r, 1e-4)).max(1) < 0.08
    return ok


def vue(dossier, lot, nom, ref=None):
    d = charger(dossier, lot)
    if d is None or nom not in d['noms']:
        return None
    k = d['noms'].index(nom)
    m = masque(d, k)
    if LOTS[lot]['vig']:   # 28 mm, distorsion corrigée par le boîtier : recalage sûr seulement au centre (rapport §1.2)
        m &= d['rayon'] < RAYON_MAX_28MM
    for rnom in ([ref] if ref else []):
        if rnom in d['noms']:
            m &= masque(d, d['noms'].index(rnom))
    return dict(lot=lot, nom=nom, x=d['raw'][k][m].astype(float), j=d['jpg'][k][m].astype(float) / 255,
                r=d['rayon'][m].astype(float), vig=LOTS[lot]['vig'], idx=np.flatnonzero(m), centres=d['centres'][m])


def sous_ech(D, n, graine=0):
    rng = np.random.default_rng(graine)
    out = []
    for d in D:
        s = np.sort(rng.choice(len(d['x']), min(n, len(d['x'])), replace=False))
        out.append({**d, 'x': d['x'][s], 'j': d['j'][s], 'r': d['r'][s]})
    return out


# --- modèle d'une base ----------------------------------------------------------------------------------------
GROUPES_VIG = ['f18', 'f56']


def base_rendu(p, x, r=None, vig=None, mono=False):
    """p = dict(M (6) | w (3, Monochrome), courbe (28), etage (NE), vig {groupe: (a, b)}) → code sRGB (non écrêté)."""
    if vig and r is not None:
        x = x * dm.vignetage(p['vig'][vig], r)[:, None]
    if mono:
        y = dm.courbe(p['courbe'], x @ np.asarray(p['w']))
        return np.repeat(y[:, None], 3, 1)
    code = dm.courbe(p['courbe'], x @ dm.matrice(p['M']).T)
    return dm.etage(p['etage'], code)


def _paquet(q, mono, vig_fixe=None):
    i = 3 if mono else 6
    p = {'w': q[:3].tolist()} if mono else {'M': q[:6].tolist()}
    p['courbe'] = q[i:i + 28].tolist()
    i += 28
    if not mono:
        p['etage'] = q[i:i + NE].tolist()
        i += NE
    if vig_fixe is None:
        p['vig'] = {g: q[i + 2 * k:i + 2 * k + 2].tolist() for k, g in enumerate(GROUPES_VIG)}
    else:
        p['vig'] = vig_fixe
    return p


def ajuster_base(D, mono=False, vig_fixe=None, iters=500):
    cible = [dm.code_lab(d['j']) for d in D]
    q0 = np.r_[np.array([0.25, 0.65, 0.1]) if mono else np.zeros(6), dm.courbe_init(), [] if mono else np.zeros(NE),
               [] if vig_fixe else np.zeros(2 * len(GROUPES_VIG))]

    def res(q):
        p = _paquet(q, mono, vig_fixe)
        return np.concatenate([(dm.code_lab(np.clip(base_rendu(p, d['x'], d['r'], d['vig'], mono), 0, 1)) - c).ravel()
                               for d, c in zip(D, cible)])
    r = least_squares(res, q0, loss='soft_l1', f_scale=2, max_nfev=iters)
    return _paquet(r.x, mono, vig_fixe)


def ecart(p, d, mono=False, ops=None):
    code = base_rendu(p, d['x'], d['r'], d['vig'], mono)
    if ops:
        code = ops(code)
    return dm.de2000(dm.code_lab(np.clip(code, 0, 1)), dm.code_lab(d['j']))


# --- opérateurs du Picture Control -------------------------------------------------------------------------
def op_cbcr(code, gain=1.0, rot_deg=0.0):
    ycc = code @ dm.YCC.T
    t = np.radians(rot_deg)
    cb, cr = ycc[:, 1], ycc[:, 2]
    return np.c_[ycc[:, 0], gain * (np.cos(t) * cb - np.sin(t) * cr), gain * (np.sin(t) * cb + np.cos(t) * cr)] @ dm.YCC_INV.T


def op_courbe_luma(code, lut):
    """Courbe perso (257 valeurs 0..1) sur la luma Y' (BT.601), Cb et Cr inchangés."""
    ycc = np.clip(code, 0, 1) @ dm.YCC.T
    y2 = np.interp(np.clip(ycc[:, 0], 0, 1), np.linspace(0, 1, 257), lut)
    return np.c_[y2, ycc[:, 1:]] @ dm.YCC_INV.T


def op_courbe_canaux(code, lut):
    return np.interp(np.clip(code, 0, 1), np.linspace(0, 1, 257), lut)


def ajuster_op_cbcr(code, j):
    cl = dm.code_lab(j)
    r = least_squares(lambda q: (dm.code_lab(np.clip(op_cbcr(code, np.exp(q[0]), q[1]), 0, 1)) - cl).ravel(), [0, 0],
                      loss='soft_l1', f_scale=2)
    return float(np.exp(r.x[0])), float(r.x[1])


def lut_libre(code, j, mode='luma', n=16):
    """Courbe monotone (n nœuds réguliers en code) qui mène `code` à `j` : effet d'un curseur tonal mesuré."""
    xs = np.linspace(0, 1, n)
    cl = dm.code_lab(j)
    op = op_courbe_luma if mode == 'luma' else op_courbe_canaux

    def lut(q):
        y = np.cumsum(np.r_[np.exp(q[0]) - 1e-3, np.exp(q[1:])])
        return np.interp(np.linspace(0, 1, 257), xs, y)
    q0 = np.r_[np.log(1e-3), np.log(np.full(n - 1, 1 / (n - 1)))]
    r = least_squares(lambda q: (dm.code_lab(np.clip(op(code, lut(q)), 0, 1)) - cl).ravel(), q0, loss='soft_l1', f_scale=2)
    return lut(r.x)


def lut_recette(recette_json):
    """Table de 257 valeurs (0..1) de la courbe d'une recette USB, ou None."""
    import picture_control as pc
    f = pathlib.Path(recette_json)
    b = pc.bloc_recette(json.loads(f.read_text(encoding='utf-8')), str(f.parent))
    r = pc.lire_bloc_ptp(b)
    return r, (np.array(r['lut']) / 32767 if r.get('courbe') else None)


S_POINTS = [[0, 0], [64, 44], [128, 128], [192, 212], [255, 255]]


def modele(dossier, sortie):
    import picture_control as pc
    out = {'lots': {}, 'bases': {}, 'curseurs': {}, 'courbe_perso': [], 'contraste': [], 'filtres': {}, 'v0': []}
    for lot in LOTS:
        d = charger(dossier, lot)
        if d is not None:
            out['lots'][lot] = {**LOTS[lot], 'vues': len(d['noms']), 'blocs_grille': int(d['dedans'].sum()),
                                'geometrie': np.round(d['geometrie'], 5).tolist(), 'recalage': json.loads(str(d['qualite']))}
    # 1. Standard d'abord : il fixe le vignetage (même objectif, même ouverture pour toutes les bases)
    P = {}
    for b in ['STANDARD'] + [b for b in BASES if b != 'STANDARD']:
        mono = b == 'MONOCHROME'
        D = [v for lot in APPRENTISSAGE if (v := vue(dossier, lot, f'BASE {b}'))]
        p = ajuster_base(sous_ech(D, 2500), mono=mono, vig_fixe=None if b == 'STANDARD' else P['STANDARD']['vig'])
        P[b] = p
        ev = {}
        for lot in LOTS:
            v = vue(dossier, lot, f'BASE {b}')
            if v:
                ev[lot] = {**dm.stats(ecart(p, v, mono)), 'n': len(v['x'])}
        out['bases'][b] = {'parametres': p, 'ecart_modele': ev}
        print(b, json.dumps(ev), flush=True)
    # 2. saturation et teinte : gain et rotation CbCr appliqués à la sortie modélisée de la base, vue par vue
    for b in COULEUR:
        rows = []
        for lot in LOTS:
            for cle, crans in (('SAT', (-3, -1, 1, 3)), ('TEI', (-3, -1, 1, 3))):
                for c in crans:
                    v = vue(dossier, lot, f'{COURT[b]} {cle}{c:+d}')
                    if not v:
                        continue
                    code = base_rendu(P[b], v['x'], v['r'], v['vig'])
                    g, t = ajuster_op_cbcr(code, v['j'])
                    e0 = dm.de2000(dm.code_lab(np.clip(code, 0, 1)), dm.code_lab(v['j']))
                    e1 = dm.de2000(dm.code_lab(np.clip(op_cbcr(code, g, t), 0, 1)), dm.code_lab(v['j']))
                    rows.append({'lot': lot, 'curseur': cle, 'cran': c, 'gain_cbcr': round(g, 3), 'rotation_deg': round(t, 2),
                                 'ecart_sans': dm.stats(e0), 'ecart_avec': dm.stats(e1)})
        out['curseurs'][b] = rows
        print(b, [(r['lot'], r['curseur'], r['cran'], r['gain_cbcr'], r['rotation_deg'], r['ecart_avec']['mediane']) for r in rows], flush=True)
    # 3. courbe perso : identité et S, appliquées à la sortie de la base, sur la luma ou par canal
    luts = {'ID': np.linspace(0, 1, 257), 'S': np.array(pc.lut_points(S_POINTS)) / 32767}
    for b in ('STANDARD', 'NEUTRE', 'MONOCHROME', 'PORTRAIT'):
        for lot in LOTS:
            for c, lut in luts.items():
                v = vue(dossier, lot, f'{COURT[b]} COURBE {c}')
                if not v:
                    continue
                mono = b == 'MONOCHROME'
                code = base_rendu(P[b], v['x'], v['r'], v['vig'], mono)
                row = {'base': b, 'lot': lot, 'courbe': c, 'sans_courbe': dm.stats(ecart(P[b], v, mono))}
                for mode, op in (('luma', op_courbe_luma), ('canaux', op_courbe_canaux)):
                    row[mode] = dm.stats(dm.de2000(dm.code_lab(np.clip(op(code, lut), 0, 1)), dm.code_lab(v['j'])))
                out['courbe_perso'].append(row)
                print('courbe', row, flush=True)
    # 4. contraste : la courbe libre qui explique chaque cran (luma ou canaux)
    for b in ('STANDARD', 'MONOCHROME'):
        for lot in APPRENTISSAGE:
            for c in (-3, 3):
                v = vue(dossier, lot, f'{COURT[b]} CON{c:+d}')
                if not v:
                    continue
                mono = b == 'MONOCHROME'
                code = base_rendu(P[b], v['x'], v['r'], v['vig'], mono)
                row = {'base': b, 'lot': lot, 'cran': c, 'sans': dm.stats(ecart(P[b], v, mono))}
                for mode, op in (('luma', op_courbe_luma), ('canaux', op_courbe_canaux)):
                    lut = lut_libre(code, v['j'], mode)
                    row[mode] = dm.stats(dm.de2000(dm.code_lab(np.clip(op(code, lut), 0, 1)), dm.code_lab(v['j'])))
                    row[f'lut_{mode}_par_32'] = np.round(lut[::32] * 255, 1).tolist()
                out['contraste'].append(row)
                print('contraste', {k: v for k, v in row.items() if 'lut' not in k}, flush=True)
    # 5. Monochrome : mélange de chaque filtre (poids sur x, le capteur équilibré), courbe commune à la base
    for f in ('AUCUN', 'JAUNE', 'ORANGE', 'ROUGE', 'VERT'):
        nom = 'BASE MONOCHROME' if f == 'AUCUN' else f'MONOCHRO {f}'
        D = [v for lot in (['lot4'] if f == 'AUCUN' else ['lot5']) if (v := vue(dossier, lot, nom))]
        if not D:
            continue
        cible = [dm.code_lab(d['j']) for d in D]
        pm = P['MONOCHROME']

        def res(w):
            q = {**pm, 'w': w.tolist()}
            return np.concatenate([(dm.code_lab(np.clip(base_rendu(q, d['x'], d['r'], d['vig'], True), 0, 1)) - c).ravel()
                                   for d, c in zip(D, cible)])
        w = least_squares(res, np.asarray(pm['w']), loss='soft_l1', f_scale=2).x
        e = np.concatenate([ecart({**pm, 'w': w.tolist()}, d, True) for d in D])
        out['filtres'][f] = {'poids_capteur': np.round(w, 4).tolist(), 'somme': round(float(w.sum()), 4), 'ecart': dm.stats(e),
                             'lot': D[0]['lot']}
        print('filtre', f, out['filtres'][f], flush=True)
    pathlib.Path(sortie).write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    return out



# --- scène : colorimétrie et échelle d'exposition -----------------------------------------------------------
def mire_ir():
    """Mire d'Imaging Resource (D750, 164 plages) : x (même convention que les blocs), XYZ de référence (D65)."""
    d = json.loads((RACINE / 'recherche' / 'donnees-films' / 'd750-standard-ir.json').read_text(encoding='utf-8'))
    X, R = np.array(d['XYZ']), np.array(d['raw_equilibre'])
    w = R[18]
    k = X[18, 1] / (d['blanc_mire_fraction_pleine_echelle'] * w[1] / w.max())   # Y par fraction de la pleine échelle (V)
    return R / k, X, k, d['noms']


COLORIMETRIE = 'poly'   # passe critique : la racine-polynôme bat la 3 × 3 en validation croisée sur la mire (1,20 contre 1,62)


def traits(x):
    """Termes de la racine-polynôme d'ordre 2 (Finlayson et al., 2015) : R, V, B, √RV, √VB, √RB (homogène de degré 1 :
    même rendu à toute exposition)."""
    x = np.clip(np.asarray(x, float), 0, None)
    return np.c_[x, np.sqrt(x[:, 0] * x[:, 1]), np.sqrt(x[:, 1] * x[:, 2]), np.sqrt(x[:, 0] * x[:, 2])]


def cam_xyz(x, Mc):
    """x (capteur équilibré) → XYZ, par la matrice 3 × 3 ou la racine-polynôme 3 × 6."""
    return x @ Mc.T if Mc.shape[1] == 3 else traits(x) @ Mc.T


def matrice_camera(forme=None):
    """M_cam : x équilibré → XYZ D65 (Y = fraction · k), ajustée en CIELAB sur la mire, un neutre restant neutre.
    forme '3x3' (matrice) ou 'poly' (racine-polynôme, 3 × 6, par défaut : COLORIMETRIE)."""
    xm, X, k, _ = mire_ir()
    lab = dm.xyz_lab(X)
    blanc = dm.M709.sum(1)
    n = 3 if (forme or COLORIMETRIE) == '3x3' else 6

    def M(q):
        A = q.reshape(3, n - 1)
        return np.c_[A, blanc - A.sum(1)]   # lignes : un neutre (tous termes égaux) → blanc D65
    q0 = np.array([[0.73, 0.16], [0.24, 1.0], [0.03, -0.26]])
    q0 = np.c_[q0, np.zeros((3, n - 3))] if n == 6 else q0
    q0 = np.c_[q0[:, :2], q0[:, 2:]] if n == 3 else np.c_[q0[:, :2], np.zeros((3, 1)), q0[:, 2:4]]
    q0 = q0[:, :n - 1].ravel()
    r = least_squares(lambda q: (dm.xyz_lab(k * cam_xyz(xm, M(q))) - lab).ravel(), q0, loss='soft_l1', f_scale=2)
    Mc = M(r.x)
    return Mc, k, dm.stats(dm.de2000(dm.xyz_lab(k * cam_xyz(xm, Mc)), lab))


def scene_xyz(x, Mc, k, vigp=None, r=None, vig=None):
    if vig and vigp is not None:
        x = x * dm.vignetage(vigp[vig], r)[:, None]
    return k * cam_xyz(x, Mc)


def peau(d):
    """Blocs de peau du lot 2 : boîte du visage (relevée sur la vue 1) et couleur de peau dans le JPEG Standard."""
    c = d['centres']
    lab = dm.code_lab(d['j'])
    h = np.degrees(np.arctan2(lab[:, 2], lab[:, 1]))
    C = np.hypot(lab[:, 1], lab[:, 2])
    boite = (c[:, 0] > 2400) & (c[:, 0] < 3750) & (c[:, 1] > 1250) & (c[:, 1] < 2450)
    return boite & (h > 25) & (h < 80) & (C > 8) & (C < 50) & (lab[:, 0] > 25)



# --- rendu d'une recette ------------------------------------------------------------------------------------
LOTS_CURSEURS = ('lot1', 'lot3', 'lot4', 'lot5')   # lot 2 : visage peu coloré, gain et rotation mal déterminés


def tables_curseurs(m):
    """Par base : gain CbCr par cran de saturation, rotation (degrés) par cran de teinte ; médiane des lots, 0 → neutre,
    crans non mesurés interpolés (ln du gain, rotation) entre les crans mesurés voisins."""
    out = {}
    for b, rows in m['curseurs'].items():
        rows = [r for r in rows if r['lot'] in LOTS_CURSEURS]
        t = {}
        for cle, champ in (('SAT', 'gain_cbcr'), ('TEI', 'rotation_deg')):
            mes = {0: 0.0}
            for c in sorted({r['cran'] for r in rows if r['curseur'] == cle}):
                v = [r[champ] for r in rows if r['curseur'] == cle and r['cran'] == c]
                mes[c] = float(np.median(np.log(v) if cle == 'SAT' else v))
            cr = np.array(sorted(mes))
            val = np.array([mes[c] for c in cr])
            t[cle] = {'crans_mesures': cr.tolist(), 'valeurs': val.tolist()}
        out[b] = t
    return out


def curseur(tab, b, cle, c):
    t = tab[b][cle]
    v = float(np.interp(c, t['crans_mesures'], t['valeurs']))
    return float(np.exp(v)) if cle == 'SAT' else v


def lut_q(q):
    """Courbe perso : 16 nœuds réguliers (codes), croissante, dans [0, 1] ; 257 valeurs."""
    y = np.minimum(np.cumsum(np.r_[np.exp(q[0]) - 1e-3, np.exp(q[1:])]), 1)
    return np.interp(np.linspace(0, 1, 257), np.linspace(0, 1, len(q)), y)


def q_lut(lut, n=16):
    y = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, 257), lut)
    d = np.maximum(np.diff(y), 1e-4)
    return np.log(np.r_[max(y[0], 0) + 1e-3, d])


def rendu_recette(code_base, gain=1.0, rot=0.0, lut=None):
    c = op_cbcr(code_base, gain, rot)
    return np.clip(op_courbe_luma(c, lut) if lut is not None else c, 0, 1)



# --- jeux d'évaluation ------------------------------------------------------------------------------------
SECTEURS = [('rouge', 0, 45), ('orange, peau', 45, 75), ('jaune', 75, 105), ('vert-jaune', 105, 135), ('vert', 135, 165),
            ('cyan-vert', 165, 200), ('cyan', 200, 235), ('bleu', 235, 290), ('violet', 290, 330), ('magenta', 330, 360)]
JEUX = ('scene', 'peau', 'mire')


def jeux(dossier, m, n_scene=2500, graine=0):
    """x (et rayon, vignetage) des trois jeux : scène (lots 3, 4, 1 : vue BASE STANDARD), peau (lot 2), mire IR."""
    out = {}
    sc = [v for lot in ('lot3', 'lot4', 'lot1') if (v := vue(dossier, lot, 'BASE STANDARD'))]
    sc = sous_ech(sc, n_scene, graine)
    out['scene'] = {'x': np.concatenate([v['x'] for v in sc]), 'r': np.concatenate([v['r'] for v in sc]),
                    'vig': np.concatenate([[v['vig'] or ''] * len(v['x']) for v in sc]), 'lot': np.concatenate([[v['lot']] * len(v['x']) for v in sc])}
    v = vue(dossier, 'lot2', 'BASE STANDARD')
    k = peau(v)
    out['peau'] = {'x': v['x'][k], 'r': v['r'][k], 'vig': np.array([v['vig']] * int(k.sum())), 'lot': np.array(['lot2'] * int(k.sum()))}
    xm, X, kk, noms = mire_ir()
    out['mire'] = {'x': xm, 'r': np.zeros(len(xm)), 'vig': np.array([''] * len(xm)), 'lot': np.array(['ir'] * len(xm)), 'XYZ': X}
    return out


def base_jeu(P, b, J):
    """Sortie modélisée de la base b pour un jeu (vignetage par groupe)."""
    mono = b == 'MONOCHROME'
    out = np.zeros((len(J['x']), 3))
    for g in set(J['vig']):
        k = J['vig'] == g
        out[k] = base_rendu(P[b], J['x'][k], J['r'][k], g or None, mono)
    return out


def xyz_jeu(J, Mc, k, vigp):
    if 'XYZ' in J:
        return J['XYZ']
    out = np.zeros((len(J['x']), 3))
    for g in set(J['vig']):
        s = J['vig'] == g
        out[s] = scene_xyz(J['x'][s], Mc, k, vigp, J['r'][s], g or None)
    return out


EQUILIBRE = 0   # passe critique : 0,5 (poids d'un bloc = blocs de son secteur^−0,5) testé, rejeté (rapport §7) ; 0 = chaque bloc pèse autant


def secteur(L, chroma_min=10):
    """Indice du secteur de teinte (SECTEURS) de chaque couleur Lab, len(SECTEURS) pour les neutres."""
    h = np.degrees(np.arctan2(L[:, 2], L[:, 1])) % 360
    i = np.searchsorted([b for _, _, b in SECTEURS], h, side='right')
    return np.where(np.hypot(L[:, 1], L[:, 2]) > chroma_min, np.minimum(i, len(SECTEURS) - 1), len(SECTEURS))


def poids_jeu(L, alpha=None):
    """Poids par bloc d'un jeu (somme des carrés = 1 : chaque jeu pèse autant), plus fort pour les teintes rares."""
    alpha = EQUILIBRE if alpha is None else alpha
    s = secteur(L)
    n = np.bincount(s, minlength=len(SECTEURS) + 1)[s].astype(float)
    w = n ** -alpha
    return w / np.sqrt((w ** 2).sum())


def optimiser(codes, cibles, gain0=1.0, rot0=0.0, fixer=False, lut0=None, n=16):
    """Saturation (gain), teinte (rotation) et courbe perso (luma) qui rapprochent les sorties de base `codes` (liste par
    jeu) des cibles Lab ; chaque jeu pèse autant, et dans un jeu les teintes rares pèsent plus (EQUILIBRE).
    fixer=True : gain et rotation imposés (crans entiers)."""
    poids = [poids_jeu(L)[:, None] for L in cibles]
    q0 = q_lut(np.linspace(0, 1, 257) if lut0 is None else lut0, n)

    def res(q):
        g, t, l = (gain0, rot0, q) if fixer else (np.exp(q[0]), q[1], q[2:])
        lut = lut_q(l)
        return np.concatenate([(w * (dm.code_lab(rendu_recette(c, g, t, lut)) - L)).ravel() for c, L, w in zip(codes, cibles, poids)])
    x0 = q0 if fixer else np.r_[np.log(gain0), rot0, q0]
    r = least_squares(res, x0, loss='soft_l1', f_scale=2, max_nfev=300)
    if fixer:
        return gain0, rot0, lut_q(r.x)
    return float(np.exp(r.x[0])), float(r.x[1]), lut_q(r.x[2:])


def noter(codes, cibles, g, t, lut):
    return {j: dm.stats(dm.de2000(dm.code_lab(rendu_recette(c, g, t, lut)), L)) for j, c, L in zip(JEUX, codes, cibles)}


def score(n):
    return float(np.mean([n[j]['mediane'] for j in JEUX]) + 0.25 * np.mean([n[j]['p90'] for j in JEUX]))


def cran_le_plus_proche(tab, b, cle, v):
    crans = np.arange(-3, 4)
    vals = np.array([curseur(tab, b, cle, c) for c in crans])
    if cle == 'SAT':
        vals, v = np.log(vals), np.log(v)
    o = np.argsort(np.abs(vals - v))[:2]
    return [int(crans[i]) for i in o]


def bases(dossier, chemin_modele, status_a, sortie, profils=None):
    import d750_cibles as dc
    m = json.loads(pathlib.Path(chemin_modele).read_text(encoding='utf-8'))
    P = {b: m['bases'][b]['parametres'] for b in BASES}
    tab = tables_curseurs(m)
    Mc, k, st = matrice_camera()
    J = jeux(dossier, m)
    xyz = {j: xyz_jeu(J[j], Mc, k, P['STANDARD']['vig']) for j in JEUX}
    cibles = dc.toutes(status_a)
    out = {'camera': {'M_cam': Mc.round(5).tolist(), 'k': k, 'ecart_mire': st}, 'n': {j: len(J[j]['x']) for j in JEUX},
           'curseurs': tab, 'profils': {}}
    for nom, f in cibles.items():
        if profils and nom not in profils:
            continue
        L = [f(xyz[j]) for j in JEUX]
        rows = []
        for b in COULEUR:
            codes = [base_jeu(P, b, J[j]) for j in JEUX]
            brut = noter(codes, L, 1, 0, None)
            g, t, lut = optimiser(codes, L)
            cont = noter(codes, L, g, t, lut)
            best = None
            for cs in cran_le_plus_proche(tab, b, 'SAT', g):
                for ch in cran_le_plus_proche(tab, b, 'TEI', t):
                    gg, tt = curseur(tab, b, 'SAT', cs), curseur(tab, b, 'TEI', ch)
                    _, _, l2 = optimiser(codes, L, gg, tt, fixer=True, lut0=lut)
                    n = noter(codes, L, gg, tt, l2)
                    if best is None or score(n) < best[0]:
                        best = (score(n), cs, ch, l2, n)
            _, cs, ch, l2, n = best
            rows.append({'base': b, 'brut': brut, 'continu': {'gain': round(g, 3), 'rotation_deg': round(t, 2), **cont},
                         'saturation': cs, 'teinte': ch, 'ecarts': n, 'score': round(best[0], 3),
                         'lut_257': np.round(l2, 5).tolist()})
            print(nom, b, cs, ch, json.dumps(n), flush=True)
        rows.sort(key=lambda r: r['score'])
        out['profils'][nom] = rows
        pathlib.Path(sortie).write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    return out



# --- noir et blanc -----------------------------------------------------------------------------------------
def gains_kelvin(K, Mc, ref=5600):
    """Gains (R, V, B) que la WB réglée à K applique en plus de celle à `ref`, sur x : c(ref) / c(K), c = RVB capteur
    équilibré de l'illuminant (lumière du jour CIE au-dessus de 4 000 K, corps noir en dessous). Calcul, à vérifier sur
    les coefficients notés dans un NEF pris à K (WB_RBLevels)."""
    import colour

    def xyz(T):
        xy = colour.temperature.CCT_to_xy_CIE_D(T) if T >= 4000 else colour.temperature.CCT_to_xy_Planck(T) \
            if hasattr(colour.temperature, 'CCT_to_xy_Planck') else colour.temperature.CCT_to_xy_Kang2002(T)
        return colour.xy_to_XYZ(xy)
    M3 = Mc if Mc.shape[1] == 3 else matrice_camera('3x3')[0]
    c = lambda T: np.linalg.solve(M3, xyz(T))
    g = c(ref) / c(K)
    return g / g[1]


def lut_trix_actuel(m):
    """« TRI-X » actuel de Thomas : Monochrome, filtre orange, contraste +3 (courbe du cran mesurée, luma)."""
    rows = [r for r in m['contraste'] if r['base'] == 'MONOCHROME' and r['cran'] == 3]
    t = np.median([r['lut_luma_par_32'] for r in rows], 0) / 255
    return np.interp(np.linspace(0, 1, 257), np.arange(0, 257, 32) / 256, t)   # table relevée tous les 32 crans


CENTILES = {   # perspectives-d200-xt4-d750.md §3.3 (L*, médiane par image) : JPEG « TRI-X » actuel → scans retouchés
    'jpeg_trix_actuel': [2, 11, 37, 64, 80, 90], 'hp5_scans': [8, 32, 60, 79, 90, 94], 'trix_scans': [5, 23, 50, 72, 89, 96]}


def courbe_hp5_scans(m, k):
    """Cible tonale HP5 « à la Thomas » : la tonalité du TRI-X actuel (Monochrome + contraste +3, sans D-Lighting)
    ramenée centile par centile sur ses scans HP5 retouchés. Renvoie Y scène → code."""
    pm = m['bases']['MONOCHROME']['parametres']
    w = np.array(m['filtres']['ORANGE']['poids_capteur'])
    lut = lut_trix_actuel(m)
    Lq = np.array(CENTILES['jpeg_trix_actuel'], float)
    Lh = np.array(CENTILES['hp5_scans'], float)

    def f(Y):
        c = dm.courbe(pm['courbe'], np.asarray(Y) / k * w.sum())
        c = np.interp(np.clip(c, 0, 1), np.linspace(0, 1, 257), lut)
        L = dm.code_lab(np.repeat(c[..., None], 3, -1))[..., 0]
        L2 = np.interp(L, np.r_[0, Lq, 100], np.r_[0, Lh, 100])
        return dm.lab_code(np.stack([L2, 0 * L2, 0 * L2], -1))[..., 0]
    return f


def noir_et_blanc(dossier, chemin_modele, sortie):
    import d750_cibles as dc
    m = json.loads(pathlib.Path(chemin_modele).read_text(encoding='utf-8'))
    P = {b: m['bases'][b]['parametres'] for b in BASES}
    Mc, k, _ = matrice_camera()
    J = jeux(dossier, m)
    xyz = {j: xyz_jeu(J[j], Mc, k, P['STANDARD']['vig']) for j in JEUX}
    pm = P['MONOCHROME']
    cibles = {
        'TRI-X': (dc.cible_nb('preset_trix', dc.courbe_trix_preset()), 'mélange et courbe du preset Tri-X'),
        'HP5': (dc.cible_nb('hp5_fiche', courbe_hp5_scans(m, k)), 'mélange de la fiche Ilford, tonalité de ses scans HP5'),
        'FP4': (dc.cible_nb('fp4_fiche', dc.courbe_film('fp4')), 'mélange et courbe de la fiche Ilford (Ilfotec HC)'),
    }
    kelvins = [5000, 5600, 6250, 7100, 8000, 9100, 10000]
    out = {'kelvins': kelvins, 'gains_kelvin': {K: gains_kelvin(K, Mc).round(4).tolist() for K in kelvins}, 'profils': {}}
    for nom, (f, desc) in cibles.items():
        L = [f(xyz[j]) for j in JEUX]
        rows = []
        for filt, fd in m['filtres'].items():
            for K in (kelvins if nom == 'TRI-X' else [5600]):
                g = gains_kelvin(K, Mc)
                p = {**pm, 'w': (np.array(fd['poids_capteur']) * g).tolist()}
                codes = [base_jeu({**P, 'MONOCHROME': p}, 'MONOCHROME', J[j]) for j in JEUX]
                _, _, lut = optimiser(codes, L, 1, 0, fixer=True)
                n = {j: {**dm.stats(dm.de2000(dm.code_lab(rendu_recette(c, 1, 0, lut)), Lj))} for j, c, Lj in zip(JEUX, codes, L)}
                rows.append({'filtre': filt, 'kelvin': K, 'ecarts': n, 'score': round(score(n), 3), 'lut_257': np.round(lut, 5).tolist()})
                print(nom, filt, K, json.dumps(n), flush=True)
        rows.sort(key=lambda r: r['score'])
        out['profils'][nom] = {'cible': desc, 'essais': rows}
        pathlib.Path(sortie).write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    return out



# --- validation : les v0 et le Portra actuel, photographiés --------------------------------------------------
V0 = {'CHROME V0': ('chrome', 'CLASSIC CHROME'), 'CLASSIC NEG V0': ('classic-neg', 'CLASSIC NEG'),
      'KODACHROME V0': ('kodachrome', 'KODACHROME'), 'TRI-X DDX V0': ('tri-x', None), 'HP5 DDX V0': ('hp5', None),
      'FP4 DDX V0': ('fp4', None)}


def rendu_complet(P, tab, r, v):
    """Rendu modélisé d'une recette lue (bloc décodé r) sur la vue v."""
    b = r['base'].upper().replace('É', 'E')
    mono = b == 'MONOCHROME'
    p = P[b]
    if mono:
        f = ['AUCUN', 'JAUNE', 'ORANGE', 'ROUGE', 'VERT'][['aucun', 'jaune', 'orange', 'rouge', 'vert'].index(r['filtre'])]
        p = {**p, 'w': P['_filtres'][f]}
    code = base_rendu(p, v['x'], v['r'], v['vig'], mono)
    g = 1.0 if mono else curseur(tab, b, 'SAT', r['saturation'])
    t = 0.0 if mono else curseur(tab, b, 'TEI', r['teinte'])
    lut = np.array(r['lut']) / 32767 if r.get('courbe') else None
    return rendu_recette(code, g, t, lut), b


def validation(dossier, chemin_modele, status_a, sortie):
    import d750_cibles as dc
    import picture_control as pc
    m = json.loads(pathlib.Path(chemin_modele).read_text(encoding='utf-8'))
    P = {b: m['bases'][b]['parametres'] for b in BASES}
    P['_filtres'] = {f: d['poids_capteur'] for f, d in m['filtres'].items()}
    tab = tables_curseurs(m)
    Mc, k, _ = matrice_camera()
    cibles = dc.toutes(status_a)
    out = {'v0': [], 'portra_actuel': {}}
    for lot in ('lot1', 'lot2', 'lot3', 'lot4'):
        for nom, (fich, cible) in V0.items():
            v = vue(dossier, lot, nom)
            if not v:
                continue
            r, _ = lut_recette(RACINE / 'recettes' / 'd750-v0' / 'usb' / f'{fich}.json')
            pred, b = rendu_complet(P, tab, r, v)
            row = {'lot': lot, 'vue': nom, 'modele_contre_jpeg': dm.stats(dm.de2000(dm.code_lab(pred), dm.code_lab(v['j'])))}
            if cible:
                L = cibles[cible](scene_xyz(v['x'], Mc, k, P['STANDARD']['vig'], v['r'], v['vig']))
                row['jpeg_contre_cible'] = dm.stats(dm.de2000(dm.code_lab(v['j']), L))
                row['base_brute_contre_cible'] = dm.stats(dm.de2000(dm.code_lab(np.clip(base_rendu(P['STANDARD'], v['x'], v['r'], v['vig']), 0, 1)), L))
            out['v0'].append(row)
            print(json.dumps(row), flush=True)
    # Portra actuel : Portrait, saturation +1, teinte −1, luminosité +1 (non mesurée : courbe libre ajustée)
    v = vue(dossier, 'lot2', 'PORTRA ACTUEL')
    r = pc.lire_bloc_ptp((pathlib.Path(dossier).parent / 'data' / 'lot2' / 'blocs' / '24.bin').read_bytes()) \
        if (pathlib.Path(dossier).parent / 'data' / 'lot2' / 'blocs' / '24.bin').exists() else \
        {'base': 'Portrait', 'saturation': 1.0, 'teinte': -1.0, 'courbe': False}
    code = base_rendu(P['PORTRAIT'], v['x'], v['r'], v['vig'])
    g, t = curseur(tab, 'PORTRAIT', 'SAT', r['saturation']), curseur(tab, 'PORTRAIT', 'TEI', r['teinte'])
    c = op_cbcr(code, g, t)
    e0 = dm.de2000(dm.code_lab(np.clip(c, 0, 1)), dm.code_lab(v['j']))
    lut = lut_libre(c, v['j'], 'luma')
    e1 = dm.de2000(dm.code_lab(np.clip(op_courbe_luma(c, lut), 0, 1)), dm.code_lab(v['j']))
    out['portra_actuel'] = {'reglages': {k2: r[k2] for k2 in ('base', 'saturation', 'teinte', 'accentuation', 'contraste', 'luminosite', 'clarte') if k2 in r},
                            'sans_luminosite': dm.stats(e0), 'avec_courbe_luminosite': dm.stats(e1),
                            'lut_luminosite_plus1_257': np.round(lut, 5).tolist()}
    print('portra', out['portra_actuel']['sans_luminosite'], out['portra_actuel']['avec_courbe_luminosite'], np.round(lut[::32] * 255, 1))
    pathlib.Path(sortie).write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    return out



KELVINS = (4000, 4500, 5000, 5300, 5600, 6250, 7100, 8000, 10000)


def balance(dossier, chemin_modele, status_a, sortie, essais, kelvins=KELVINS, vm=(0.0,)):
    """Effet d'une WB fixe différente de 5 600 K (la scène, elle, ne change pas) : essais = [(profil, base ou filtre)].
    vm : décalages vert-magenta, en ln du gain du vert capteur (> 0 : plus de vert, image plus magenta), l'axe G-M du
    réglage fin (pas d'un cran : à lire dans les WB_RBLevels d'un NEF). Pour les profils N&B, cibles de noir_et_blanc."""
    import d750_cibles as dc
    m = json.loads(pathlib.Path(chemin_modele).read_text(encoding='utf-8'))
    P = {b: m['bases'][b]['parametres'] for b in BASES}
    tab = tables_curseurs(m)
    Mc, k, _ = matrice_camera()
    J = jeux(dossier, m)
    xyz = {j: xyz_jeu(J[j], Mc, k, P['STANDARD']['vig']) for j in JEUX}
    nb = {'HP5': lambda: dc.cible_nb('hp5_fiche', courbe_hp5_scans(m, k)), 'FP4': lambda: dc.cible_nb('fp4_fiche', dc.courbe_film('fp4')),
          'TRI-X': lambda: dc.cible_nb('preset_trix', dc.courbe_trix_preset())}
    out = []
    for profil, b in essais:
        f = nb[profil]() if profil in nb else dc.toutes(status_a)[profil]
        L = [f(xyz[j]) for j in JEUX]
        for K, v in [(K, v) for K in kelvins for v in vm]:
            g = gains_kelvin(K, Mc) * np.array([1, np.exp(v), 1])
            if profil in nb:
                p = {**P['MONOCHROME'], 'w': (np.array(m['filtres'][b]['poids_capteur']) * g).tolist()}
                codes = [base_jeu({**P, 'MONOCHROME': p}, 'MONOCHROME', {**J[j]}) for j in JEUX]
                gg, tt, lut = optimiser(codes, L, 1, 0, fixer=True)
                cs = ch = None
            else:
                codes = [base_jeu(P, b, {**J[j], 'x': J[j]['x'] * g}) for j in JEUX]
                g0, t0, lut = optimiser(codes, L)
                cs = int(np.clip(np.round(np.interp(np.log(g0), tab[b]['SAT']['valeurs'], tab[b]['SAT']['crans_mesures'])), -3, 3))
                ch = int(np.clip(np.round(np.interp(t0, tab[b]['TEI']['valeurs'], tab[b]['TEI']['crans_mesures'])), -3, 3))
                gg, tt = curseur(tab, b, 'SAT', cs), curseur(tab, b, 'TEI', ch)
                _, _, lut = optimiser(codes, L, gg, tt, fixer=True, lut0=lut)
            n = noter(codes, L, gg, tt, lut)
            out.append({'profil': profil, 'base': b, 'kelvin': K, 'vert_magenta': v, 'saturation': cs, 'teinte': ch, 'ecarts': n,
                        'score': round(score(n), 3), 'lut_257': np.round(lut, 5).tolist()})
            print(profil, b, K, v, cs, ch, json.dumps(n), flush=True)
        pathlib.Path(sortie).write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    return out



# --- recettes v1 --------------------------------------------------------------------------------------------
# netteté et clarté : non mesurées par les séances (blocs uniformes) ; reprises des Picture Control actuels de Thomas
# quand il en a un (sonde USB d’octobre 2026), sinon accentuation 3 (défaut de Standard) et clarté 0
# (emplacement, cible, nom dans le boîtier, fichier, netteté et clarté). Thomas veut des noms sans version dans le
# boîtier (octobre 2026) : la version est dans le nom du fichier et dans resume.json.
EMPLACEMENTS = [
    ('C-1', 'KODACHROME VIF', 'KODACHROME', 'kodachrome-v2', {'accentuation': 4, 'clarte': 1}),   # rapport §3.5 bis
    ('C-2', 'CLASSIC CHROME', 'CLASSIC CHROME', 'classic-chrome-v1', {'accentuation': 3, 'clarte': 0}),
    ('C-3', 'CLASSIC NEG', 'CLASSIC NEG', 'classic-neg-v1', {'accentuation': 3, 'clarte': 0}),
    ('C-4', 'POSITIVE', 'POSITIVE', 'positive-v1', {'accentuation': 3, 'clarte': 0}),
    ('C-5', 'PORTRA ESPRIT', 'PORTRA 400', 'portra-400-v2', {'accentuation': 4, 'clarte': 0}),   # rapport §3.6 bis
    ('C-6', 'HASSELBLAD', 'HASSELBLAD', 'hasselblad-v1', {'accentuation': 3, 'clarte': 0}),
    ('C-7', 'TRI-X', 'TRI-X', 'tri-x-v1', {'accentuation': 5, 'clarte': 1}),
    ('C-8', 'HP5', 'HP5+', 'hp5-v1', {'accentuation': 4, 'clarte': -1}),
    ('C-9', 'FP4', 'FP4+', 'fp4-v1', {'accentuation': 4, 'clarte': 0}),
]
VARIANTES = []   # première livraison (octobre 2026) : pas de variante ; ex. ('PORTRA SCANS', 'PORTRA SCANS V1', {...})
NOM_BASE = {'STANDARD': 'Standard', 'NEUTRE': 'Neutre', 'SATURE': 'Saturé', 'MONOCHROME': 'Monochrome', 'PORTRAIT': 'Portrait',
            'PAYSAGE': 'Paysage', 'UNIFORME': 'Uniforme'}


def lut_entiers(lut):
    v = np.round(np.clip(np.asarray(lut), 0, 1) * 32767).astype(int)
    return np.maximum.accumulate(v).tolist()


# WB conseillée et recette calculée pour elle (balance.json). v1 : Kodachrome Mallett, Neutre à 5 000 K ; v2 : cible
# spektrafilm +20 %, Standard à 6 250 K (rapport §3.5 bis)
WB_CHOIX = {'KODACHROME VIF': ('STANDARD', 6250)}
# Tri-X (U1) : « vert » et « aucun » à 10 000 K sont à 0,05 de score (1,26 et 1,31), sous la précision du modèle ; on garde « aucun »
NB_CHOIX = {'TRI-X': ('AUCUN', 10000)}


def recettes(chemin_bases, chemin_nb, chemin_validation, dossier_sortie, choix=None, chemin_balance=None):
    """Écrit une recette USB par emplacement (format de recettes/d750-v0/usb) et resume.json (écarts prévus).
    choix : {profil: base} pour imposer une base (sinon la meilleure du classement) ; chemin_balance : recettes
    calculées pour une autre WB (WB_CHOIX), la recette à 5 600 K est alors écrite en variante."""
    import picture_control as pc
    B = {'profils': {}}   # chemin_bases : un fichier de `bases`, ou plusieurs séparés par des virgules
    for c in str(chemin_bases).split(','):
        B['profils'].update(json.loads(pathlib.Path(c).read_text(encoding='utf-8'))['profils'])
    N = json.loads(pathlib.Path(chemin_nb).read_text(encoding='utf-8'))
    V = json.loads(pathlib.Path(chemin_validation).read_text(encoding='utf-8'))
    Wb = json.loads(pathlib.Path(chemin_balance).read_text(encoding='utf-8')) if chemin_balance else []
    choix = choix or {}
    sortie = pathlib.Path(dossier_sortie)
    (sortie / 'usb').mkdir(parents=True, exist_ok=True)
    resume = []
    for slot, profil, nom, fichier, fixes in EMPLACEMENTS:
        info = {'emplacement': slot, 'profil': profil, 'nom': nom, 'fichier': f'usb/{fichier}.json',
                'version': fichier.rsplit('-', 1)[1]}
        if profil in WB_CHOIX and Wb:
            bw, K = WB_CHOIX[profil]
            r = next(x for x in Wb if x['profil'] == profil and x['base'] == bw and x['kelvin'] == K and not x.get('vert_magenta'))
            rec = {'nom': nom, 'base': NOM_BASE[bw], 'reglages': {**fixes, 'saturation': r['saturation'], 'teinte': r['teinte']},
                   'courbe': {'lut': lut_entiers(r['lut_257'])}}
            info.update(base=bw, saturation=r['saturation'], teinte=r['teinte'], kelvin=K, ecarts_prevus=r['ecarts'])
            if profil in B['profils']:   # variante à 5 600 K, si la cible a aussi été passée à `bases`
                r5 = B['profils'][profil][0]
                var = {'nom': f'{nom} 5600K'[:19], 'base': NOM_BASE[r5['base']],
                       'reglages': {**fixes, 'saturation': r5['saturation'], 'teinte': r5['teinte']}, 'courbe': {'lut': lut_entiers(r5['lut_257'])}}
                fv = f"{fichier}-variante-5600k.json"
                (sortie / 'usb' / fv).write_text(json.dumps(var, ensure_ascii=False), encoding='utf-8')
                info['variante_5600K'] = {'fichier': f'usb/{fv}', 'base': r5['base'], 'saturation': r5['saturation'],
                                          'teinte': r5['teinte'], 'ecarts_prevus': r5['ecarts']}
        elif profil in B['profils']:
            rows = B['profils'][profil]
            r = next(x for x in rows if x['base'] == choix[profil]) if profil in choix else rows[0]
            rec = {'nom': nom, 'base': NOM_BASE[r['base']],
                   'reglages': {**fixes, 'saturation': r['saturation'], 'teinte': r['teinte']},
                   'courbe': {'lut': lut_entiers(r['lut_257'])}}
            info.update(base=r['base'], saturation=r['saturation'], teinte=r['teinte'], ecarts_prevus=r['ecarts'], base_brute=r['brut'])
        elif profil in N['profils']:
            f0, K0 = NB_CHOIX.get(profil, (None, 5600))
            r = next(x for x in N['profils'][profil]['essais'] if x['kelvin'] == K0 and (f0 is None or x['filtre'] == f0))
            rec = {'nom': nom, 'base': 'Monochrome', 'reglages': {**fixes, 'filtre': r['filtre'].lower()},
                   'courbe': {'lut': lut_entiers(r['lut_257'])}}
            info.update(base='MONOCHROME', filtre=r['filtre'], kelvin=r['kelvin'], ecarts_prevus=r['ecarts'], cible=N['profils'][profil]['cible'])
        else:   # Portra : traduction fidèle du Portra actuel, faute de cible (voir le rapport)
            pa = V['portra_actuel']['reglages']
            rec = {'nom': nom, 'base': 'Portrait', 'reglages': {**fixes, 'saturation': pa.get('saturation', 1), 'teinte': pa.get('teinte', -1),
                                                               'contraste': pa.get('contraste', 0), 'luminosite': pa.get('luminosite', 1)}}
            info.update(base='PORTRAIT', reprise_du_portra_actuel=pa)
        b = pc.bloc_recette(rec)
        r2 = pc.lire_bloc_ptp(b)
        info['octets'] = len(b)
        (sortie / 'usb' / f"{fichier}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding='utf-8')
        resume.append(info)
        print(slot, nom, len(b), {k: r2[k] for k in r2 if k not in ('lut', 'courbe_entete')}, flush=True)
    # variantes à départager au lot de contrôle (Portra : options 1 et 2, rapport §3.6)
    for profil, nom, fixes in VARIANTES:
        if profil not in B['profils']:
            continue
        r = B['profils'][profil][0]
        rec = {'nom': nom, 'base': NOM_BASE[r['base']], 'reglages': {**fixes, 'saturation': r['saturation'], 'teinte': r['teinte']},
               'courbe': {'lut': lut_entiers(r['lut_257'])}}
        pc.bloc_recette(rec)
        f = f"{nom.lower().replace(' ', '-')}.json"
        (sortie / 'usb' / f).write_text(json.dumps(rec, ensure_ascii=False), encoding='utf-8')
        resume.append({'emplacement': 'variante', 'profil': profil, 'nom': nom, 'base': r['base'], 'saturation': r['saturation'],
                       'teinte': r['teinte'], 'ecarts_prevus': r['ecarts'], 'base_brute': r['brut'], 'fichier': f'usb/{f}'})
        print('variante', nom, r['base'], r['saturation'], r['teinte'], flush=True)
    (sortie / 'resume.json').write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding='utf-8')
    return resume



def detail_lots(dossier, chemin_modele, chemin_bases, status_a, profil):
    """Écarts par lot (scène) des recettes optimisées de chaque base pour un profil : la base retenue l'est-elle partout ?"""
    import d750_cibles as dc
    m = json.loads(pathlib.Path(chemin_modele).read_text(encoding='utf-8'))
    B = json.loads(pathlib.Path(chemin_bases).read_text(encoding='utf-8'))['profils'][profil]
    P = {b: m['bases'][b]['parametres'] for b in BASES}
    tab = tables_curseurs(m)
    Mc, k, _ = matrice_camera()
    f = dc.toutes(status_a)[profil]
    out = {}
    for lot in ('lot1', 'lot3', 'lot4', 'lot5'):
        v = vue(dossier, lot, 'BASE STANDARD') or vue(dossier, lot, 'STANDARD SAT-1')
        L = f(scene_xyz(v['x'], Mc, k, P['STANDARD']['vig'], v['r'], v['vig']))
        for r in B:
            code = base_rendu(P[r['base']], v['x'], v['r'], v['vig'])
            pred = rendu_recette(code, curseur(tab, r['base'], 'SAT', r['saturation']), curseur(tab, r['base'], 'TEI', r['teinte']),
                                 np.array(r['lut_257']))
            out.setdefault(r['base'], {})[lot] = dm.stats(dm.de2000(dm.code_lab(pred), L))
    return out



# --- cible mesurée sur paires NEF + export (Portra : le preset Portra) ---------------------------------------
def cible_paires(chemin_npz, sortie, wb_libre=False, graine=0, par_image=1500, look=None, lisse=0.0, grain=False):
    """Modèle d'un rendu logiciel à partir de paires NEF du D750 + JPEG exporté :
    Lab = étage_CbCr(T(K · XYZ_scène · g_image)), K 3 × 3, T courbe croissante (même sur les trois canaux), g_image un
    gain d'exposition par photo. Avec `look` (profil Look de Lightroom connu, ex. le preset Portra) : seule la base que
    Lightroom met sous le Look est ajustée (T(K · XYZ) en Adobe RGB gamma 2,2, sans étage), puis la vraie table est
    appliquée ; la cible tient alors sur toutes les couleurs, même celles absentes des paires. Autres paramètres :
    gain d'exposition par photo (réglages d'exposition du logiciel), et si wb_libre un gain R et B par photo (WB changée
    dans le logiciel). Une photo sur quatre est tenue à part (seuls ses gains sont ajustés). Le gain médian est reporté dans
    K : la luminosité moyenne des exports devient celle de la cible.
    lisse : pénalité sur les variations de pente de la courbe d'un nœud à l'autre (sans elle, la courbe peut sauter dans
    les tons où les paires ont peu de blocs, ex. un saut de L* 5 à 44 sur un diaphragme dans les ombres).
    grain : exports avec du grain (ex. le preset Portra) ; le seuil d'uniformité du JPEG passe de 2,5 à 8 niveaux, sinon presque
    tous les blocs sous le gris moyen sont rejetés (l'uniformité reste assurée par le critère sur le NEF)."""
    d = dict(np.load(chemin_npz, allow_pickle=True))
    Mc, k, _ = matrice_camera()
    j, js, x, xs, xm, img = d['jpg'], d['jpg_std'], d['raw'], d['raw_std'], d['raw_max'], d['image']
    ok = (xm < 0.9) & (j.min(1) > 2) & (j.max(1) < 253) & (x.min(1) > 2e-4)
    ok &= js.max(1) < np.maximum(8 if grain else 2.5, 0.04 * j.mean(1))
    ok &= (xs / np.maximum(x, 1e-4)).max(1) < 0.08
    rng = np.random.default_rng(graine)
    ids = np.unique(img[ok])
    garde = np.concatenate([rng.choice(np.flatnonzero(ok & (img == i)), min(par_image, int((ok & (img == i)).sum())), replace=False)
                            for i in ids])
    X = k * cam_xyz(x[garde], Mc)
    L = dm.code_lab(j[garde] / 255)
    I = np.searchsorted(ids, img[garde])
    test = ids[3::4]
    tr = ~np.isin(ids[I], test)
    nI = len(ids)
    nw = 2 * nI if wb_libre else 0
    if look:
        import d750_cibles as dc
        table = dc.table_look(look)
        K0 = np.linalg.inv(dc.M_ARGB_XYZ)
    else:
        K0 = np.linalg.inv(dm.M709)

    def sortie_(q, X, I):
        K = q[:9].reshape(3, 3)
        g = np.exp(q[9 + 28 + NE:9 + 28 + NE + nI])[I]
        lin = (X @ K.T) * g[:, None]
        if wb_libre:
            w = q[9 + 28 + NE + nI:].reshape(nI, 2)[I]
            lin = lin * np.c_[np.exp(w[:, 0]), np.ones(len(I)), np.exp(w[:, 1])]
        if look:
            return dc.appliquer_look(table, dm.courbe(q[9:9 + 28], lin))
        return dm.etage(q[9 + 28:9 + 28 + NE], dm.courbe(q[9:9 + 28], lin))

    q0 = np.r_[K0.ravel(), dm.courbe_init(), np.zeros(NE), np.zeros(nI), np.zeros(nw)]
    res = lambda q, m: (dm.code_lab(np.clip(sortie_(q, X[m], I[m]), 0, 1)) - L[m]).ravel()
    utiles = dm.NOEUDS * 2.5 < 1   # nœuds sous l'écrêtage de la courbe de départ
    pen = lambda q: lisse * np.sqrt(tr.sum()) * np.diff(q[9:9 + 28][utiles])
    q = least_squares(lambda q: np.r_[res(q, tr), pen(q)], q0, loss='soft_l1', f_scale=2, max_nfev=600).x
    # photos tenues à part : seuls leurs gains (et WB) bougent
    libres = np.r_[9 + 28 + NE + np.flatnonzero(np.isin(ids, test))]
    if wb_libre:
        libres = np.r_[libres, [9 + 28 + NE + nI + 2 * i + c for i in np.flatnonzero(np.isin(ids, test)) for c in (0, 1)]]

    def res_test(v):
        qq = q.copy()
        qq[libres] = v
        return res(qq, ~tr)
    if (~tr).any():   # départ au gain médian des photos d'ajustement (sinon images écrêtées, gradient nul)
        g0 = 9 + 28 + NE + np.flatnonzero(np.isin(ids, test))
        q[g0] = np.median(np.delete(q[9 + 28 + NE:9 + 28 + NE + nI], np.flatnonzero(np.isin(ids, test))))
        q[libres] = least_squares(res_test, q[libres], loss='soft_l1', f_scale=2).x
    med = np.median(q[9 + 28 + NE:9 + 28 + NE + nI])
    q[:9] *= np.exp(med)
    q[9 + 28 + NE:9 + 28 + NE + nI] -= med
    e = dm.de2000(dm.code_lab(np.clip(sortie_(q, X, I), 0, 1)), L)
    out = {'source': pathlib.Path(chemin_npz).name, 'photos': int(nI), 'blocs': int(len(X)), 'wb_libre': wb_libre,
           'look': pathlib.Path(look).name if look else None, 'lisse': lisse, 'grain': grain,
           'ajustement': dm.stats(e[tr]), 'tenu_a_part': dm.stats(e[~tr]) if (~tr).any() else None,
           'K': q[:9].reshape(3, 3).round(6).tolist(), 'courbe': q[9:9 + 28].tolist(), 'etage': q[9 + 28:9 + 28 + NE].tolist(),
           'gains_il': (q[9 + 28 + NE:9 + 28 + NE + nI] / np.log(2)).round(2).tolist()}
    pathlib.Path(sortie).write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({c: out[c] for c in ('photos', 'blocs', 'ajustement', 'tenu_a_part', 'gains_il')}), flush=True)
    return out



def scans(dossier, sortie=None, cote=600):
    """Signature d'un film sur des scans (ex. Portra 400 de Thomas) : centiles de L* et teinte des tons neutres
    (chroma < 12) par tranche de clarté, médiane par image puis médiane des images. Aucune scène de référence : c'est un
    contrôle de tendance (ombres froides ou chaudes, hautes lumières, densité), pas une cible couleur par couleur."""
    import glob
    from d750_blocs import jpeg_srgb
    fs = sorted(glob.glob(str(pathlib.Path(dossier) / '*.jp*g')) + glob.glob(str(pathlib.Path(dossier) / '*.JP*G')))
    tranches = [(5, 25), (25, 45), (45, 65), (65, 85), (85, 98)]
    C, T = [], []
    for f in fs:
        a = jpeg_srgb(f)
        k = max(1, int(max(a.shape[:2]) / cote))
        lab = dm.code_lab(a[::k, ::k].reshape(-1, 3) / 255)
        C.append(np.percentile(lab[:, 0], [5, 25, 50, 75, 95, 99]))
        ch = np.hypot(lab[:, 1], lab[:, 2])
        row = []
        for lo, hi in tranches:
            m = (lab[:, 0] >= lo) & (lab[:, 0] < hi) & (ch < 12)
            row.append(np.median(lab[m, 1:], 0) if m.sum() > 200 else [np.nan, np.nan])
        T.append(row)
    C, T = np.array(C), np.array(T, float)
    out = {'images': len(fs), 'L_centiles_5_25_50_75_95_99': np.round(np.median(C, 0), 1).tolist(),
           'neutres_a_b_par_tranche_L': {f'{lo}-{hi}': np.round(np.nanmedian(T[:, i], 0), 2).tolist() for i, (lo, hi) in enumerate(tranches)}}
    print(json.dumps(out, ensure_ascii=False))
    if sortie:
        pathlib.Path(sortie).write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    return out



# --- passe critique ------------------------------------------------------------------------------------------
def ecarts_par_teinte(Lp, Lt, chroma_min=10):
    """Écart prévu contre cible par secteur de teinte de la cible : ΔE2000 médian, décalage de teinte (degrés, prévu −
    cible), rapport de chroma, écart de L*."""
    Ct, Cp = np.hypot(*Lt[:, 1:].T), np.hypot(*Lp[:, 1:].T)
    ht = np.degrees(np.arctan2(Lt[:, 2], Lt[:, 1])) % 360
    dh = (np.degrees(np.arctan2(Lp[:, 2], Lp[:, 1])) - ht + 180) % 360 - 180
    e = dm.de2000(Lp, Lt)
    out = []
    for nom, a, b in SECTEURS:
        m = (Ct > chroma_min) & (ht >= a) & (ht < b)
        if m.sum() >= 15:
            out.append({'secteur': nom, 'n': int(m.sum()), 'dE': round(float(np.median(e[m])), 2),
                        'teinte_deg': round(float(np.median(dh[m])), 1), 'chroma_x': round(float(np.median(Cp[m] / Ct[m])), 2),
                        'dL': round(float(np.median(Lp[m, 0] - Lt[m, 0])), 1)})
    m = Ct <= chroma_min
    out.append({'secteur': 'neutres', 'n': int(m.sum()), 'dE': round(float(np.median(e[m])), 2),
                'da': round(float(np.median(Lp[m, 1] - Lt[m, 1])), 1), 'db': round(float(np.median(Lp[m, 2] - Lt[m, 2])), 1),
                'dL': round(float(np.median(Lp[m, 0] - Lt[m, 0])), 1)})
    return out



def evaluer_recettes(dossier, chemin_modele, status_a, recettes):
    """Écarts d'une liste de recettes (dicts : profil, base, saturation, teinte, lut_257, kelvin, vert_magenta, filtre)
    contre leur cible, avec la colorimétrie et les jeux courants : par jeu, et par secteur de teinte (scène + mire)."""
    import d750_cibles as dc
    m = json.loads(pathlib.Path(chemin_modele).read_text(encoding='utf-8'))
    P = {b: m['bases'][b]['parametres'] for b in BASES}
    tab = tables_curseurs(m)
    Mc, k, _ = matrice_camera()
    J = jeux(dossier, m)
    xyz = {j: xyz_jeu(J[j], Mc, k, P['STANDARD']['vig']) for j in JEUX}
    C = dc.toutes(status_a)
    C.update({'TRI-X': dc.cible_nb('preset_trix', dc.courbe_trix_preset()),
              'HP5': dc.cible_nb('hp5_fiche', courbe_hp5_scans(m, k)), 'FP4': dc.cible_nb('fp4_fiche', dc.courbe_film('fp4'))})
    out = []
    for r in recettes:
        g = gains_kelvin(r.get('kelvin') or 5600, Mc) * np.array([1, np.exp(r.get('vert_magenta') or 0), 1])
        L, Lp = {}, {}
        for j in JEUX:
            L[j] = C[r['profil']](xyz[j])
            if r['base'] == 'MONOCHROME':
                pm = {**P['MONOCHROME'], 'w': (np.array(m['filtres'][r['filtre']]['poids_capteur']) * g).tolist()}
                code = base_jeu({**P, 'MONOCHROME': pm}, 'MONOCHROME', J[j])
                Lp[j] = dm.code_lab(rendu_recette(code, 1, 0, np.array(r['lut_257'])))
            else:
                code = base_jeu(P, r['base'], {**J[j], 'x': J[j]['x'] * g})
                Lp[j] = dm.code_lab(rendu_recette(code, curseur(tab, r['base'], 'SAT', r['saturation']),
                                                  curseur(tab, r['base'], 'TEI', r['teinte']), np.array(r['lut_257'])))
        res = {j: dm.stats(dm.de2000(Lp[j], L[j])) for j in JEUX}
        sect = ecarts_par_teinte(np.r_[Lp['scene'], Lp['mire']], np.r_[L['scene'], L['mire']])
        out.append({**{c: r.get(c) for c in ('nom', 'profil', 'base', 'saturation', 'teinte', 'filtre', 'kelvin', 'vert_magenta')},
                    'ecarts': res, 'score': round(score(res), 3), 'secteurs': sect})
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'modele':
        modele(a[1], a[2])
    elif a and a[0] == 'validation':
        validation(a[1], a[2], a[3], a[4])
    elif a and a[0] == 'balance':
        balance(a[1], a[2], a[3], a[4], [tuple(e.split(':')) for e in a[5].split(',')],
                kelvins=[int(v) for v in a[a.index('--kelvins') + 1].split(',')] if '--kelvins' in a else KELVINS,
                vm=[float(v) for v in a[a.index('--vm') + 1].split(',')] if '--vm' in a else (0.0,))
    elif a and a[0] == 'recettes':
        recettes(a[1], a[2], a[3], a[5], chemin_balance=a[4])
    elif a and a[0] == 'cible-paires':
        cible_paires(a[1], a[2], wb_libre='--wb-libre' in a, look=a[a.index('--look') + 1] if '--look' in a else None,
                     lisse=float(a[a.index('--lisse') + 1]) if '--lisse' in a else 0.0, grain='--grain' in a)
    elif a and a[0] == 'scans':
        scans(a[1], a[2] if len(a) > 2 else None)
    elif a and a[0] == 'nb':
        noir_et_blanc(a[1], a[2], a[3])
    elif a and a[0] == 'bases':
        bases(a[1], a[2], a[3], a[4], a[5].split(',') if len(a) > 5 else None)
    else:
        print(__doc__)
        sys.exit(2)
