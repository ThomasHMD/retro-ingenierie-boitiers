#!/usr/bin/env python3
"""Comparaison en images : pour chaque vue d'un lot photographié avec un Picture Control (v0 ou v1), la cible du profil,
le rendu prévu par le modèle pour la recette v1, et le JPEG réel du boîtier, sur la même scène (le NEF de la vue).

  d750_comparer.py <dossier du lot (plan.json, rangees/)> <résultats (modele.json)> <status_A/> <sortie/>
                   [--vues "CHROME V0,KODACHROME V1,..."]

Pour chaque vue : <sortie>/NN-NOM.png (trois panneaux et carte des écarts du boîtier à la cible) ; <sortie>/planche.png
(toutes les vues, réduites) ; <sortie>/ecarts.json (ΔE2000 médian et p90 sur toute l'image : boîtier contre cible,
prévu contre cible, boîtier contre prévu). Le preset acheté (Portra) est cherché dans D750_LOOKS.

La scène vue par la cible est celle que verrait le boîtier réglé à 5 600 K : si la vue a été prise avec une autre WB
(Kodachrome à 5 000 K, Tri-X à 10 000 K), ses coefficients (dans le NEF) sont ramenés à ceux de 5 600 K.
"""
import json
import pathlib
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import d750_analyse as da  # noqa: E402
import d750_blocs as db  # noqa: E402
import d750_modele as dm  # noqa: E402

RACINE = ICI.parent
# lot 1 (d750_blocs.py) : JPEG → NEF demi-résolution, AF-S 28 mm f/1,8 G, contrôle de la distorsion actif
GEOMETRIE_28MM = (1508.08096, 1008.04384, 0.50565, 0.00014, -0.01857, -0.21997, 0.60867)
WB_5600 = np.array([2.01953125, 1.0, 1.2734375])   # WB_RBLevels du D750 à 5 600 K (vérifié sur les 179 vues d’octobre 2026)
PROFIL = {'PORTRA SCANS': 'PORTRA SCANS', 'PORTRA REGLE': 'PORTRA REGLE', 'KODACHROME': 'KODACHROME', 'CHROME': 'CLASSIC CHROME', 'CLASSIC CHROME': 'CLASSIC CHROME', 'CLASSIC NEG': 'CLASSIC NEG',
          'POSITIVE': 'POSITIVE', 'PORTRA': 'PORTRA', 'HASSELBLAD': 'HASSELBLAD', 'TRI-X': 'TRI-X', 'HP5': 'HP5', 'FP4': 'FP4'}
V1 = {'KODACHROME': 'kodachrome-v1', 'CLASSIC CHROME': 'classic-chrome-v1', 'CLASSIC NEG': 'classic-neg-v1', 'POSITIVE': 'positive-v1',
      'PORTRA': 'portra-400-v1', 'PORTRA SCANS': 'portra-scans-v1', 'PORTRA REGLE': 'portra-regle-v1', 'HASSELBLAD': 'hasselblad-v1', 'TRI-X': 'tri-x-v1', 'HP5': 'hp5-v1', 'FP4': 'fp4-v1'}


def profil_de(nom):
    """Profil d'une vue de recette (v0, v1, variante 5600K, Portra actuel) ; None pour les vues de calibration."""
    n = nom.upper()
    if not (n.endswith(' V0') or n.endswith(' V1') or n.endswith('5600K') or n == 'PORTRA ACTUEL'):
        return None
    for cle in sorted(PROFIL, key=len, reverse=True):
        if nom.upper().startswith(cle):
            return PROFIL[cle]
    return None


def cibles(m, status_a):
    import d750_cibles as dc
    Mc, k, _ = da.matrice_camera()
    C = dc.toutes(status_a)
    C.update({'TRI-X': dc.cible_nb('preset_trix', dc.courbe_trix_preset()),
              'HP5': dc.cible_nb('hp5_fiche', da.courbe_hp5_scans(m, k)), 'FP4': dc.cible_nb('fp4_fiche', dc.courbe_film('fp4'))})
    return C, Mc, k


def projeter(p, q, W, H, rmax=0.7):
    """JPEG → NEF demi-résolution (paramètres de d750_blocs.geometrie), distorsion figée au-delà de rmax : le polynôme
    ajusté diverge vers les coins (rapport §1.2) ; le 28 mm n'a qu'environ 1 % de distorsion en barillet."""
    cj = np.array([W, H]) / 2
    nrm = np.hypot(*cj)
    u = (q - cj) / nrm
    r2 = np.minimum((u ** 2).sum(1, keepdims=True), rmax ** 2)
    u = u * (1 + p[4] * r2 + p[5] * r2 ** 2 + p[6] * r2 ** 3)
    c, s_ = np.cos(p[3]), np.sin(p[3])
    return np.c_[c * u[:, 0] - s_ * u[:, 1], s_ * u[:, 0] + c * u[:, 1]] * p[2] * nrm + p[:2]


def image_vue(dossier, k_vue, nom, pas=6):
    """NEF de la vue rééchantillonné sur la grille du JPEG (un pixel sur `pas`), JPEG réduit, rayon, WB de la vue."""
    from scipy.ndimage import map_coordinates
    f = lambda e: str(pathlib.Path(dossier) / 'rangees' / f"{k_vue:02d}-{nom.replace(' ', '_')}.{e}")
    nef, wb, _ = db.nef_demi(f('NEF'))
    jp = db.jpeg(f('JPG'))
    p, proj, qual = db.geometrie(nef * wb, jp)
    if qual['points'] < 200:   # scène peu texturée (visage) : géométrie complète du lot 1 (même boîtier, même 28 mm)
        p, qual = np.array(GEOMETRIE_28MM), {**qual, 'geometrie': 'lot 1 (trop peu de points)'}
    from scipy.ndimage import uniform_filter
    nef = uniform_filter(nef, size=(pas // 2, pas // 2, 1))   # moyenne sur la zone de chaque pixel de sortie (bruit)
    H, W = jp.shape[:2]
    yy, xx = np.mgrid[pas // 2:H:pas, pas // 2:W:pas]
    q = projeter(p, np.c_[xx.ravel(), yy.ravel()], W, H)
    x = np.stack([map_coordinates(nef[..., c], [q[:, 1], q[:, 0]], order=1, mode='nearest') for c in range(3)], -1) * wb
    j = uniform_filter(jp, size=(pas, pas, 1))[pas // 2:H:pas, pas // 2:W:pas].reshape(-1, 3) / 255   # même lissage que le NEF
    cj = np.array([W, H]) / 2
    r = np.hypot(*((np.c_[xx.ravel(), yy.ravel()] - cj) / np.hypot(*cj)).T)
    return x.astype(float), j, r, xx.shape, wb, qual


def vignetage_de(nef):
    """Groupe de correction du vignetage de la vue (lu par exiftool) : None si le contrôle est coupé, sinon d'après
    l'ouverture (modèle ajusté à f/1,8 et à f/5,6, objectif de 28 mm)."""
    import subprocess
    r = json.loads(subprocess.run(['exiftool', '-j', '-VignetteControl', '-FNumber', nef], capture_output=True, text=True).stdout)[0]
    if str(r.get('VignetteControl', 'Off')) == 'Off':
        return None
    return 'f18' if float(r.get('FNumber', 5.6)) < 2.8 else 'f56'


def comparer(dossier, res, status_a, sortie, vues=None):
    from PIL import Image, ImageDraw, ImageFont
    m = json.loads((pathlib.Path(res) / 'modele.json').read_text(encoding='utf-8'))
    P = {b: m['bases'][b]['parametres'] for b in da.BASES}
    P['_filtres'] = {f: d['poids_capteur'] for f, d in m['filtres'].items()}
    tab = da.tables_curseurs(m)
    C, Mc, k = cibles(m, status_a)
    plan = json.loads((pathlib.Path(dossier) / 'plan.json').read_text(encoding='utf-8'))['vues']
    sortie = pathlib.Path(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    try:
        police = ImageFont.truetype('DejaVuSans.ttf', 22)
    except OSError:
        police = ImageFont.load_default()
    resultats, vignettes = [], []
    for v in plan:
        nom = v['nom']
        prof = profil_de(nom)
        if prof is None or (vues and nom not in vues):
            continue
        x, j, r, forme, wb, qual = image_vue(dossier, v['numero'], nom)
        vig = vignetage_de(str(pathlib.Path(dossier) / 'rangees' / f"{v['numero']:02d}-{nom.replace(' ', '_')}.NEF"))
        g = (wb / WB_5600) / (wb / WB_5600)[1]          # WB de la vue par rapport à 5 600 K
        x5600 = x / g
        lab_c = C[prof](da.scene_xyz(x5600, Mc, k, P['STANDARD']['vig'], r, vig))
        rec, _ = da.lut_recette(RACINE / 'recettes' / 'd750-v1' / 'usb' / f'{V1[prof]}.json')
        # la vue v1 a été prise à la WB conseillée : sa propre WB est déjà dans x ; pour une vue v0 (5 600 K), on applique
        # la WB conseillée de la recette v1 pour la prévision
        resume = {e['profil']: e for e in json.loads((RACINE / 'recettes' / 'd750-v1' / 'resume.json').read_text(encoding='utf-8'))}
        Kv1 = (resume.get(prof) or {}).get('kelvin') or 5600
        x_pred = x if 'V1' in nom.upper() else x5600 * da.gains_kelvin(Kv1, Mc)
        pred, _ = da.rendu_complet(P, tab, rec, {'x': x_pred, 'r': r, 'vig': vig})
        lab_p = dm.code_lab(pred)
        lab_j = dm.code_lab(j)
        e_jc = dm.de2000(lab_j, lab_c)
        row = {'vue': nom, 'profil': prof, 'boitier_contre_cible': dm.stats(e_jc),
               'prevu_v1_contre_cible': dm.stats(dm.de2000(lab_p, lab_c)),
               'boitier_contre_prevu_v1': dm.stats(dm.de2000(lab_j, lab_p)) if 'V1' in nom.upper() else None,
               'recalage': qual}
        resultats.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        h, w = forme
        im = lambda lab: Image.fromarray((np.clip(dm.lab_code(lab), 0, 1).reshape(h, w, 3) * 255).astype(np.uint8))
        carte = np.clip(e_jc / 10, 0, 1).reshape(h, w)
        carte = Image.fromarray((np.stack([carte, carte * 0.35, 1 - carte], -1) * 255).astype(np.uint8))
        panneaux = [(f'Cible {prof.title()}', im(lab_c)), ('Rendu prévu, recette v1', im(lab_p)),
                    (f'Boîtier : {nom}', Image.fromarray((j.reshape(h, w, 3) * 255).astype(np.uint8))),
                    ('Écart boîtier / cible (bleu 0, rouge ≥ 10)', carte)]
        planche = Image.new('RGB', (2 * w + 30, 2 * h + 110), (252, 252, 251))
        d = ImageDraw.Draw(planche)
        for i, (titre, p_) in enumerate(panneaux):
            ox, oy = 10 + (i % 2) * (w + 10), 40 + (i // 2) * (h + 35)
            planche.paste(p_, (ox, oy))
            d.text((ox, oy - 30), titre, fill=(20, 20, 20), font=police)
        bc, pc_ = row['boitier_contre_cible'], row['prevu_v1_contre_cible']
        d.text((10, 2 * h + 80), f"ΔE2000 médian (p90) : boîtier / cible {bc['mediane']} ({bc['p90']}) ; prévu v1 / cible "
                                 f"{pc_['mediane']} ({pc_['p90']})", fill=(60, 60, 60), font=police)
        f = sortie / f"{v['numero']:02d}-{nom.replace(' ', '_')}.png"
        planche.save(f)
        vignettes.append(planche.resize((planche.width // 2, planche.height // 2)))
    if vignettes:
        W = max(v.width for v in vignettes)
        tout = Image.new('RGB', (W, sum(v.height for v in vignettes)), (252, 252, 251))
        y = 0
        for v in vignettes:
            tout.paste(v, (0, y))
            y += v.height
        tout.save(sortie / 'planche.png')
    (sortie / 'ecarts.json').write_text(json.dumps(resultats, ensure_ascii=False, indent=1), encoding='utf-8')
    return resultats


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 4:
        print(__doc__)
        sys.exit(2)
    comparer(*a[:4], vues=a[a.index('--vues') + 1].split(',') if '--vues' in a else None)
