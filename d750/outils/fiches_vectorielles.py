#!/usr/bin/env python3
"""Courbes des fiches techniques de films lues directement dans le PDF, quand les graphiques y sont vectoriels.

Pas de numérisation à l'œil : les courbes sont des polylignes (ou des Bézier) du PDF ; on les convertit en unités
des axes par une calibration sur les graduations du graphique (coordonnées exactes du PDF). Précision : celle du
tracé de la fiche elle-même (les fiches Kodak de 1996 posent leurs points au centième de densité).

Fiches traitées (PDF non recopiés dans le dépôt, à télécharger) :
- Kodak E-55, décembre 1996, KODACHROME 25, 64 et 200 Professional (pages 5, 6, 7) :
  https://125px.com/docs/film/kodak/e55-1996_12.pdf
  Étiquettes d'axes en texte : calibration automatique (étiquette accrochée à la graduation la plus proche ;
  la barre des caractéristiques négatives, 3̄.0 = −3,0, est un petit trait tracé au-dessus du chiffre).
- Kodak F-4017, octobre 2021, TRI-X 320 et 400 (pages 8 et 9) :
  https://kodakprofessional.com/sites/default/files/wysiwyg/film/f4017_trix_320400.pdf
  Courbes identifiées par le motif de tirets de leur échantillon de légende.
- Ilford FP4 Plus (avril 2004, pages 1 et 4) et HP5 Plus (juillet 2004, pages 1 et 5) :
  https://125px.com/docs/film/ilford/FP4+-200404.pdf, https://125px.com/docs/film/ilford/HP5+-200407.pdf
  Étiquettes vectorisées (pas de texte) : valeurs des graduations données ici, lues sur la page rendue.
  Les fiches Harman de novembre 2018 reprennent les mêmes graphiques en image.

  fiches_vectorielles.py kodachrome <e55-1996_12.pdf> <sortie.json>
  fiches_vectorielles.py fp4 <FP4+-200404.pdf> <sortie.json>
  fiches_vectorielles.py hp5 <HP5+-200407.pdf> <sortie.json>
  fiches_vectorielles.py trix <f4017_trix_320400.pdf (octobre 2021)> <sortie.json>
  fiches_vectorielles.py brut <fichier.pdf> <page>     cadres, calibrations et courbes trouvés (contrôle)
"""
import json
import re
import sys

import numpy as np
import pymupdf

NUM = re.compile(r'^-?\d+(\.\d+)?$')


def _pt(q):
    return np.array([q.x, q.y])


def tirets(d):
    """Motif de tirets d'un tracé, normalisé (« plein » si aucun)."""
    m = re.findall(r'[\d.]+', (d.get('dashes') or '').split(']')[0])
    return ' '.join(f'{float(v):.1f}' for v in m) or 'plein'


def elements(page, bezier_pas=20, legendes=None):
    """Segments isolés (graduations, grilles, barres), cadres, polylignes (courbes, ≥ 12 points). Si `legendes` est
    une liste, on y range les petits segments horizontaux tiretés ou pleins (échantillons de légende) avec leur motif."""
    lignes, cadres, courbes = [], [], []
    for d in page.get_drawings():
        it = d['items']
        seuls = all(i[0] == 'l' for i in it) and all(abs(a[2].x - b[1].x) + abs(a[2].y - b[1].y) > 1e-3
                                                        for a, b in zip(it, it[1:]))  # segments non enchaînés
        if (len(it) <= 2 and all(i[0] == 'l' for i in it)) or seuls or any(i[0] == 're' for i in it):
            # segments seuls, ou cadre tracé avec ses graduations dans le même chemin (fiches Ilford)
            lignes += [(i[1], i[2]) for i in it if i[0] == 'l']
            if legendes is not None and len(it) <= 2 and it[0][0] == 'l' and abs(it[0][1].y - it[-1][2].y) < 0.01 \
                    and 8 < abs(it[-1][2].x - it[0][1].x) < 60:
                legendes.append({'y': it[0][1].y, 'x0': min(it[0][1].x, it[-1][2].x), 'x1': max(it[0][1].x, it[-1][2].x),
                                 'tirets': tirets(d)})
            for i in it:
                if i[0] == 're' and d.get('color') is not None:  # cadre tracé, pas un fond rempli
                    cadres.append(i[1])
                    lignes += [(i[1].tl, i[1].tr), (i[1].bl, i[1].br), (i[1].tl, i[1].bl), (i[1].tr, i[1].br)]
            continue
        pts = []
        for i in it:
            if i[0] == 'l':
                a, b = _pt(i[1]), _pt(i[2])
                if not pts or np.abs(pts[-1] - a).sum() > 1e-3:
                    pts.append(a)
                pts.append(b)
            elif i[0] == 'c':
                a, c1, c2, b = map(_pt, i[1:5])
                if not pts or np.abs(pts[-1] - a).sum() > 1e-3:
                    pts.append(a)
                for t in np.linspace(0, 1, bezier_pas + 1)[1:]:
                    pts.append((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * b)
        if len(pts) >= 12:
            courbes.append({'pts': np.array(pts), 'epaisseur': d.get('width') or 0, 'tirets': tirets(d)})
    return lignes, cadres, courbes


def etiquettes(page):
    out = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                t = s['text'].strip()
                if NUM.match(t):
                    out.append((t, pymupdf.Rect(s['bbox'])))
    return out


def calibrer(cadre, etiq, lignes, axe):
    """Calibration linéaire (ou log10 si les étiquettes couvrent plus de 1,5 décade) d'un axe, par moindres carrés
    sur les couples (valeur, graduation) ; les couples incohérents (écart > 0,12 % de l'étendue) sont écartés."""
    fr = cadre
    paires = []
    for t, r in etiq:
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        if axe == 'x' and fr.y1 - 2 < r.y0 < fr.y1 + 14 and fr.x0 - 15 < cx < fr.x1 + 15:
            c = cx
        elif axe == 'y' and fr.x0 - 30 < r.x1 < fr.x0 + 2 and fr.y0 - 10 < cy < fr.y1 + 10:
            c = cy
        else:
            continue
        v = float(t)
        for a, b in lignes:  # barre au-dessus du premier chiffre : caractéristique négative
            if abs(a.y - b.y) < 0.01 and 1.5 < abs(b.x - a.x) < 6 and r.y0 - 1.5 < a.y < r.y0 + 2.5 \
                    and r.x0 - 1 < min(a.x, b.x) < r.x0 + 4:
                e = int(abs(v))
                v = -e + (abs(v) - e)
                break
        best = None
        for a, b in lignes:
            if axe == 'x' and abs(a.x - b.x) < 0.01 and min(a.y, b.y) < fr.y1 + 1 and max(a.y, b.y) > fr.y1 - 8:
                dd = abs(a.x - c)
            elif axe == 'y' and abs(a.y - b.y) < 0.01 and min(a.x, b.x) < fr.x0 + 8 and max(a.x, b.x) > fr.x0 - 1:
                dd = abs(a.y - c)
            else:
                continue
            if dd < 4 and (best is None or dd < best[0]):
                best = (dd, a.x if axe == 'x' else a.y)
        paires.append((v, best[1] if best else c))
    paires = sorted(set(paires), key=lambda q: q[1])
    vals = [q[0] for q in paires]
    if axe == 'x' and len(vals) > 3 and 0.0 in vals and vals[0] > 0 and vals[0] > vals[1]:
        # étiquettes 4.0 3.0 2.0 1.0 0.0 1.0 : la barre des caractéristiques négatives n'est pas un trait séparé
        # (fiches Kodak récentes) ; tout ce qui est à gauche de 0,0 est négatif
        c0 = paires[vals.index(0.0)][1]
        paires = [(-v if c < c0 else v, c) for v, c in paires]
    return ajuster(sorted(set(paires), key=lambda q: q[1]))


def ajuster(paires, log=None):
    v = np.array([q[0] for q in paires], float)
    c = np.array([q[1] for q in paires], float)
    if log is None:
        log = bool(np.all(v > 0) and len(v) > 4 and v.max() / v.min() >= 30)
    vv = np.log10(v) if log else v
    garde = np.ones(len(v), bool)
    tol = 0.0012 * (vv.max() - vv.min())
    while True:
        k = np.polyfit(c[garde], vv[garde], 1)
        res = np.abs(vv - np.polyval(k, c))
        r = np.where(garde, res, -1)
        if r.max() <= tol or garde.sum() <= 3:
            break
        garde[np.argmax(r)] = False
    return {'pente': float(k[0]), 'origine': float(k[1]), 'log': log,
            'graduations': [[float(a), round(float(b), 3)] for a, b, g in zip(v, c, garde) if g],
            'ecartees': [[float(a), round(float(b), 3)] for a, b, g in zip(v, c, garde) if not g],
            'residu_max': float(res[garde].max())}


def vers_unites(cal, c):
    v = cal['pente'] * np.asarray(c) + cal['origine']
    return 10 ** v if cal['log'] else v


def graphiques(page):
    """Graphiques d'une page à étiquettes texte : cadre, calibrations, courbes en unités des axes, motifs de tirets,
    textes et échantillons de légende situés dans le cadre ou juste au-dessus (titre)."""
    leg = []
    lignes, cadres, courbes = elements(page, legendes=leg)
    etiq = etiquettes(page)
    textes = [(t, r) for b in page.get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans']
              for t, r in [(s['text'].strip(), pymupdf.Rect(s['bbox']))] if t]
    out = []
    for fr in cadres:
        if not (80 < fr.width < 500 and fr.height > 80):
            continue
        dedans = [c for c in courbes if fr.x0 - 1 <= c['pts'][:, 0].min() and c['pts'][:, 0].max() <= fr.x1 + 1
                  and fr.y0 - 1 <= c['pts'][:, 1].min() and c['pts'][:, 1].max() <= fr.y1 + 1]
        if not dedans:
            continue
        cx, cy = calibrer(fr, etiq, lignes, 'x'), calibrer(fr, etiq, lignes, 'y')
        dans = lambda r, haut=0: fr.x0 - 80 <= r.x0 and r.x1 <= fr.x1 + 80 and fr.y0 - haut <= r.y0 and r.y1 <= fr.y1
        txt = [(t, r) for t, r in textes if dans(r, 45)]
        legende = []
        for e in leg:
            if fr.x0 < e['x0'] and e['x1'] < fr.x1 and fr.y0 < e['y'] < fr.y1:
                lab = [t for t, r in txt if abs((r.y0 + r.y1) / 2 - e['y']) < 3 and 0 < r.x0 - e['x1'] < 15]
                if lab:
                    legende.append((lab[0], e['tirets']))
        out.append({'cadre': fr, 'cal_x': cx, 'cal_y': cy, 'brut': [c['pts'] for c in dedans],
                    'tirets': [c['tirets'] for c in dedans], 'textes': [t for t, r in txt], 'legende': legende,
                    'courbes': [np.c_[vers_unites(cx, c['pts'][:, 0]), vers_unites(cy, c['pts'][:, 1])] for c in dedans]})
    return out


def _arrondi(a, n=4):
    return [[round(float(x), n), round(float(y), n)] for x, y in a]


def kodachrome(pdf):
    """E-55 (1996) : pages 5 (K25), 6 (K64), 7 (K200)."""
    doc = pymupdf.open(pdf)
    films = {}
    for nom, n in (('kodachrome_25', 5), ('kodachrome_64', 6), ('kodachrome_200', 7)):
        g = graphiques(doc[n - 1])
        sortie = {'page': n}
        for gr in g:
            cs = gr['courbes']
            cal = {'x': {k: gr['cal_x'][k] for k in ('graduations', 'ecartees', 'residu_max', 'log')},
                   'y': {k: gr['cal_y'][k] for k in ('graduations', 'ecartees', 'residu_max', 'log')}}
            ys = [q[0] for q in gr['cal_y']['graduations']]
            if gr['cal_x']['log']:  # FTM
                sortie['ftm'] = {'unites': 'fréquence (cycles/mm), réponse (%)', 'calibration': cal,
                                 'points': _arrondi(cs[0], 3)}
            elif max(ys) >= 4:  # courbes caractéristiques : R au-dessus, puis G, puis B (densité au pied gauche)
                ordre = np.argsort([-c[np.argmin(c[:, 0]), 1] for c in cs])
                sortie['courbes_caracteristiques'] = {
                    'unites': 'log H (lux·s), densité Status A', 'calibration': cal,
                    **{k: _arrondi(cs[i][np.argsort(cs[i][:, 0])]) for k, i in zip('RGB', ordre)}}
            elif min(ys) < 0:  # sensibilités spectrales : par longueur d'onde du maximum
                ordre = np.argsort([c[np.argmax(c[:, 1]), 0] for c in cs])
                sortie['sensibilites_spectrales'] = {
                    'unites': 'nm, log10 sensibilité (1 / exposition en erg/cm² pour D = 1,0 E.N.D.)', 'calibration': cal,
                    **{k: _arrondi(cs[i][np.argsort(cs[i][:, 0])], 3) for k, i in
                       zip(('couche_jaune_bleu', 'couche_magenta_vert', 'couche_cyan_rouge'), ordre)}}
            else:  # densités spectrales des colorants : le neutre visuel ne descend pas sous 0,5
                neutre = int(np.argmax([c[:, 1].min() for c in cs]))
                autres = [i for i in range(len(cs)) if i != neutre]
                ordre = sorted(autres, key=lambda i: cs[i][np.argmax(cs[i][:, 1]), 0])
                sortie['densites_colorants'] = {
                    'unites': 'nm, densité spectrale diffuse (colorants normalisés : neutre visuel D = 1,0 sous 3 200 K)',
                    'calibration': cal, 'neutre_visuel': _arrondi(cs[neutre][np.argsort(cs[neutre][:, 0])]),
                    **{k: _arrondi(cs[i][np.argsort(cs[i][:, 0])]) for k, i in zip(('jaune', 'magenta', 'cyan'), ordre)}}
        films[nom] = sortie
    return films


def _graduations_cadre(lignes, fr, valeurs_x, valeurs_y, cote_y='droite'):
    """Graduations d'un graphique sans étiquettes texte : petits traits sous le cadre (x) et du côté donné (y)."""
    gx = sorted({round(a.x, 3) for a, b in lignes if abs(a.x - b.x) < 0.01 and max(a.y, b.y) > fr.y1 + 1
                 and min(a.y, b.y) > fr.y1 - 1 and fr.x0 - 1 < a.x < fr.x1 + 1})
    bord = fr.x1 if cote_y == 'droite' else fr.x0
    gy = sorted({round(a.y, 3) for a, b in lignes if abs(a.y - b.y) < 0.01 and abs(min(abs(a.x - bord), abs(b.x - bord))) < 0.5
                 and abs(a.x - b.x) < 5 and fr.y0 < a.y < fr.y1})
    assert len(gx) == len(valeurs_x) and len(gy) == len(valeurs_y), (gx, gy)
    return (ajuster(list(zip(valeurs_x, gx)), False), ajuster(list(zip(sorted(valeurs_y, reverse=True), gy)), False))


# Fiches Ilford vectorielles : (page, valeurs des graduations x et y, zone verticale du graphique en points ; les
# pages des courbes portent aussi l'abaque des températures, tracé du même trait épais)
ILFORD = {'fp4': (('spectrogramme', 1, [400, 450, 500, 550, 600, 650], [1.0, 0.5], (0, 900)),
                  ('courbe_caracteristique', 4, [1, 2, 3, 4], [2.0, 1.0], (550, 900))),
          'hp5': (('spectrogramme', 1, [400, 450, 500, 550, 600, 650], [1.0, 0.5], (0, 900)),
                  ('courbe_caracteristique', 5, [1, 2, 3, 4], [2.0, 1.0], (300, 445)))}


def ilford(pdf, film='fp4'):
    """Fiches Ilford de 2004 : FP4 Plus (avril, pages 1 et 4), HP5 Plus (juillet, pages 1 et 5)."""
    doc = pymupdf.open(pdf)
    out = {}
    for cle, n, vx, vy, (haut, bas) in ILFORD[film]:
        lignes, cadres, courbes = elements(doc[n - 1])
        trait = [c['pts'] for c in courbes if c['epaisseur'] > 1.4 and c['pts'][:, 1].min() > haut and c['pts'][:, 1].max() < bas]
        assert len(trait) == 1, len(trait)
        p = trait[0]
        fr = [f for f in cadres if f.x0 - 2 <= p[:, 0].min() and p[:, 0].max() <= f.x1 + 2
              and f.y0 - 2 <= p[:, 1].min() and p[:, 1].max() <= f.y1 + 2 and f.width < 300][0]
        cx, cy = _graduations_cadre(lignes, fr, vx, vy)
        xy = np.c_[vers_unites(cx, p[:, 0]), vers_unites(cy, p[:, 1])]
        out[cle] = {'page': n, 'cadre_bas_en_unites_y': round(float(vers_unites(cy, fr.y1)), 4),
                    'cadre_gauche_en_unites_x': round(float(vers_unites(cx, fr.x0)), 4),
                    'calibration': {'x': {k: cx[k] for k in ('graduations', 'residu_max')},
                                    'y': {k: cy[k] for k in ('graduations', 'residu_max')}},
                    'points': _arrondi(xy[np.argsort(xy[:, 0])], 4)}
    return out


def _par_legende(g):
    """Courbes d'un graphique rangées par l'étiquette de légende de même motif de tirets (motif unique seulement)."""
    motifs = [m for _, m in g['legende']]
    out = {}
    for lab, m in g['legende']:
        k = [i for i, t in enumerate(g['tirets']) if t == m]
        if motifs.count(m) == 1 and len(k) == 1:
            c = g['courbes'][k[0]]
            out[lab] = _arrondi(c[np.argsort(c[:, 0])])
    return out


def trix(pdf):
    """Kodak F-4017 (octobre 2021), pages 8 et 9 : courbes caractéristiques par révélateur et temps, sensibilité
    spectrale (deux densités), indice de contraste en fonction du temps."""
    doc = pymupdf.open(pdf)
    out = {'courbes_caracteristiques': {}}
    for n in (8, 9):
        for g in graphiques(doc[n - 1]):
            tout = ' '.join(g['textes'])
            cal = {'x': {k: g['cal_x'][k] for k in ('graduations', 'ecartees', 'residu_max')},
                   'y': {k: g['cal_y'][k] for k in ('graduations', 'ecartees', 'residu_max')}}
            if g['textes'] and g['textes'][0].startswith('Spectral'):
                out['sensibilites_spectrales'] = {'unites': 'nm, log10 sensibilité (1 / exposition en erg/cm²)',
                                                  'page': n, 'calibration': cal, **_par_legende(g)}
            elif g['textes'] and g['textes'][0].startswith('Contrast Index'):
                out['indice_de_contraste'] = {'unites': 'temps de développement (min), indice de contraste', 'page': n,
                                              'calibration': cal, 'note': 'motifs de tirets ambigus (HC-110 B et D-76 1+1, '
                                              'XTOL 1+1 et T-MAX RS) : seules les courbes à motif unique sont gardées',
                                              **_par_legende(g)}
            elif 'Characteristic' in tout:
                titre = next(t for t in g['textes'] if 'Film /' in t)
                fmt = 'tri-x_320_plan' if '320TXP' in titre else ('tri-x_400_120' if '120' in titre else 'tri-x_400_35mm')
                rev = 'T-MAX' if 'T-MAX' in tout else ('D-76' if 'D-76' in tout else ('HC-110_B' if 'HC-110' in tout else '?'))
                out['courbes_caracteristiques'][f'{fmt}_{rev}'] = {
                    'unites': 'log H (lux·s), densité diffuse visuelle', 'page': n, 'calibration': cal, **_par_legende(g)}
    return out


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    action, pdf, arg = sys.argv[1:4]
    if action == 'brut':
        for g in graphiques(pymupdf.open(pdf)[int(arg) - 1]):
            print('cadre', [round(v, 1) for v in g['cadre']], 'x', g['cal_x']['graduations'], 'y', g['cal_y']['graduations'])
            print('   textes', g['textes'][:6], 'légende', g['legende'])
            for c, t in zip(g['courbes'], g['tirets']):
                print(f'   {len(c)} points, x {c[:, 0].min():.3f}..{c[:, 0].max():.3f}, y {c[:, 1].min():.3f}..{c[:, 1].max():.3f}, tirets {t}')
        return 0
    res = {'kodachrome': kodachrome, 'trix': trix, 'fp4': lambda p: ilford(p, 'fp4'), 'hp5': lambda p: ilford(p, 'hp5')}[action](pdf)
    with open(arg, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False)
    return 0


if __name__ == '__main__':
    sys.exit(main())
