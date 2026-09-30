#!/usr/bin/env python3
"""Figures du rapport recherche/d750-analyse-seances.md (PNG, matplotlib), à partir des sorties de d750_analyse.py.

  d750_figures.py <dossier des .npz> <dossier des résultats (modele.json, bases.json, nb.json, balance.json)>
                  <status_A/> <dossier NEF du lot 3> <sortie>
"""
import json
import pathlib
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import d750_analyse as da  # noqa: E402
import d750_modele as dm  # noqa: E402

# palette catégorielle de référence (ordre fixe), surface et encres
SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
SURFACE, ENCRE, ENCRE2, GRILLE = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
COUL_BASE = dict(zip(['STANDARD', 'NEUTRE', 'SATURE', 'PORTRAIT', 'PAYSAGE', 'UNIFORME', 'MONOCHROME'], SERIES))
LIB = {'STANDARD': 'Standard', 'NEUTRE': 'Neutre', 'SATURE': 'Saturé', 'PORTRAIT': 'Portrait', 'PAYSAGE': 'Paysage',
       'UNIFORME': 'Uniforme', 'MONOCHROME': 'Monochrome'}
JEU_LIB = {'scene': 'scènes (lots 1, 3, 4)', 'peau': 'peau (lot 2)', 'mire': 'mire (164 plages)'}


def style(plt):
    plt.rcParams.update({'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
                         'axes.edgecolor': GRILLE, 'axes.labelcolor': ENCRE2, 'xtick.color': ENCRE2, 'ytick.color': ENCRE2,
                         'text.color': ENCRE, 'axes.grid': True, 'grid.color': GRILLE, 'grid.linewidth': 0.8,
                         'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 11, 'axes.titlesize': 13,
                         'axes.titleweight': 'bold', 'axes.titlelocation': 'left', 'legend.frameon': False})


def courbes_bases(m, sortie, plt):
    fig, ax = plt.subplots(figsize=(10, 6))
    Mc, k, _ = da.matrice_camera()
    il = np.linspace(-7, 2.5, 200)
    Y = 0.18 * 2 ** il
    for b in da.BASES:
        p = m['bases'][b]['parametres']
        x = np.repeat((Y / k)[:, None], 3, 1)
        c = da.base_rendu(p, x, None, None, b == 'MONOCHROME').mean(1)
        ax.plot(il, np.clip(c, 0, 1) * 255, color=COUL_BASE[b], lw=2, label=LIB[b])
    ir = json.loads((da.RACINE / 'recherche' / 'donnees-films' / 'd750-standard-ir.json').read_text(encoding='utf-8'))['courbe_standard']
    ax.scatter(np.log2(np.array(ir['Y_scene']) / 0.18), np.array(ir['code']) * 255, s=36, facecolor='none', edgecolor=ENCRE,
               lw=1.2, label='Standard, mire Imaging Resource (autre D750)', zorder=5)
    ax.set_xlabel('exposition de la scène, IL autour du gris de 18 %')
    ax.set_ylabel('code JPEG (0-255), gris neutre')
    ax.set_title('Courbe de tonalité des sept bases, mesurée NEF contre JPEG')
    ax.legend(loc='upper left', ncol=2)
    ax.set_ylim(0, 260)
    fig.tight_layout()
    fig.savefig(sortie, dpi=130)
    plt.close(fig)


def courbe_perso(m, sortie, plt):
    rows = [r for r in m['courbe_perso'] if r['courbe'] == 'S' and r['base'] != 'MONOCHROME']
    lab = [f"{LIB[r['base']]}\n{r['lot'].replace('lot', 'lot ')}" for r in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(10, 5.2))
    w = 0.26
    for i, (cle, nom, c) in enumerate((('sans_courbe', 'courbe ignorée', SERIES[7]), ('canaux', 'sur R, V, B (hypothèse v0)', SERIES[1]),
                                       ('luma', "sur la luma Y', Cb Cr inchangés", SERIES[0]))):
        v = [r[cle]['mediane'] for r in rows]
        ax.bar(x + (i - 1) * w, v, w * 0.92, color=c, label=nom)
    ax.set_xticks(x, lab)
    ax.set_ylabel('ΔE2000 médian, modèle contre JPEG')
    ax.set_title('Courbe perso en S : où le boîtier l’applique')
    ax.legend(loc='upper right')
    fig.tight_layout()
    fig.savefig(sortie, dpi=130)
    plt.close(fig)


def curseurs(m, sortie, plt):
    tab = da.tables_curseurs(m)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6))
    for b in da.COULEUR:
        t = tab[b]
        a1.plot(t['SAT']['crans_mesures'], np.exp(t['SAT']['valeurs']), '-o', color=COUL_BASE[b], lw=2, ms=6, label=LIB[b])
        a2.plot(t['TEI']['crans_mesures'], t['TEI']['valeurs'], '-o', color=COUL_BASE[b], lw=2, ms=6, label=LIB[b])
    a1.set_title('Saturation : gain sur Cb et Cr')
    a1.set_xlabel('cran')
    a1.set_ylabel('gain')
    a2.set_title('Teinte : rotation dans le plan CbCr')
    a2.set_xlabel('cran')
    a2.set_ylabel('degrés')
    a1.legend(loc='upper left')
    fig.tight_layout()
    fig.savefig(sortie, dpi=130)
    plt.close(fig)


def bases_profils(b, sortie, plt):
    profils = list(b['profils'])
    fig, axes = plt.subplots(1, len(profils), figsize=(3.4 * len(profils), 5.2))
    for ax, p in zip(axes, profils):
        rows = sorted(b['profils'][p], key=lambda r: da.COULEUR.index(r['base']))
        y = np.arange(len(rows))
        for i, j in enumerate(('scene', 'peau', 'mire')):
            ax.barh(y + (i - 1) * 0.26, [r['ecarts'][j]['mediane'] for r in rows], 0.24, color=SERIES[[0, 4, 3][i]],
                    label=JEU_LIB[j])
        best = min(rows, key=lambda r: r['score'])
        ax.set_yticks(y, [f"{LIB[r['base']]}{' ◀' if r is best else ''}" for r in rows])
        for t, r in zip(ax.get_yticklabels(), rows):
            t.set_fontweight('bold' if r is best else 'normal')
        ax.set_title(p.title())
        ax.set_xlabel('ΔE2000 médian')
        ax.axvline(2, color=ENCRE2, lw=1, ls='--')
        ax.invert_yaxis()
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=3)
    fig.suptitle('Meilleure base par profil (saturation, teinte et courbe optimisées ; ◀ retenue)', x=0.01, ha='left',
                 fontweight='bold')
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(sortie, dpi=130)
    plt.close(fig)


def apercus(dossier_blocs, res, status_a, nef_lot3, sortie, plt):
    """Pédalier (lot 3) : cible et rendu prévu de chaque recette v1, à partir du NEF de la vue 1."""
    import d750_blocs as db
    import d750_cibles as dc
    m = json.loads((res / 'modele.json').read_text(encoding='utf-8'))
    b = json.loads((res / 'bases.json').read_text(encoding='utf-8'))
    n = json.loads((res / 'nb.json').read_text(encoding='utf-8'))
    resume = json.loads((da.RACINE / 'recettes' / 'd750-v1' / 'resume.json').read_text(encoding='utf-8'))
    P = {k: m['bases'][k]['parametres'] for k in da.BASES}
    tab = da.tables_curseurs(m)
    Mc, k, _ = da.matrice_camera()
    nef, wb, _ = db.nef_demi(str(nef_lot3))
    x = (nef * wb)[::6, ::6]
    h, w = x.shape[:2]
    X = x.reshape(-1, 3).astype(float)
    xyz = da.scene_xyz(X, Mc, k)
    cib = dc.toutes(status_a)
    vues = []
    for r in resume:
        p = r['profil']
        if p in b['profils']:
            if r.get('kelvin'):
                bal = json.loads((res / 'balance.json').read_text(encoding='utf-8'))
                row = next(q for q in bal if q['profil'] == p and q['base'] == r['base'] and q['kelvin'] == r['kelvin'])
                code = da.base_rendu(P[r['base']], X * da.gains_kelvin(r['kelvin'], Mc))
            else:
                row = next(q for q in b['profils'][p] if q['base'] == r['base'])
                code = da.base_rendu(P[r['base']], X)
            pred = da.rendu_recette(code, da.curseur(tab, r['base'], 'SAT', row['saturation']),
                                    da.curseur(tab, r['base'], 'TEI', row['teinte']), np.array(row['lut_257']))
            cible = dm.lab_code(cib[p](xyz))
        elif p in n['profils']:
            row = next(q for q in n['profils'][p]['essais'] if q['filtre'] == r['filtre'] and q['kelvin'] == r['kelvin'])
            g = da.gains_kelvin(r['kelvin'], Mc)
            pm = {**P['MONOCHROME'], 'w': (np.array(m['filtres'][r['filtre']]['poids_capteur']) * g).tolist()}
            pred = da.rendu_recette(da.base_rendu(pm, X, mono=True), 1, 0, np.array(row['lut_257']))
            if p == 'TRI-X':
                f = dc.cible_nb('preset_trix', dc.courbe_trix_preset())
            elif p == 'HP5':
                f = dc.cible_nb('hp5_fiche', da.courbe_hp5_scans(m, k))
            else:
                f = dc.cible_nb('fp4_fiche', dc.courbe_film('fp4'))
            cible = dm.lab_code(f(xyz))
        else:
            continue
        if r.get('kelvin') and p in b['profils']:
            r = {**r, 'nom': f"{r['nom']} (WB {r['kelvin']} K)"}
        elif p == 'TRI-X':
            r = {**r, 'nom': f"{r['nom']} (WB {r['kelvin']} K)"}
        vues.append((r['nom'], np.clip(cible, 0, 1).reshape(h, w, 3), np.clip(pred, 0, 1).reshape(h, w, 3)))
    fig, axes = plt.subplots(len(vues), 2, figsize=(9, 3.05 * len(vues)))
    for (nom, c, p), (a1, a2) in zip(vues, axes):
        a1.imshow(c)
        a2.imshow(p)
        for a in (a1, a2):
            a.set_xticks([]); a.set_yticks([]); a.grid(False)
            for s in a.spines.values():
                s.set_visible(False)
        a1.set_title(f'{nom} : cible', fontsize=11)
        a2.set_title('D750, rendu prévu par le modèle', fontsize=11)
    fig.tight_layout()
    fig.savefig(sortie, dpi=90)
    plt.close(fig)


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    style(plt)
    blocs, res, status_a, nef3, out = (pathlib.Path(a) for a in sys.argv[1:6])
    out.mkdir(parents=True, exist_ok=True)
    m = json.loads((res / 'modele.json').read_text(encoding='utf-8'))
    b = json.loads((res / 'bases.json').read_text(encoding='utf-8'))
    courbes_bases(m, out / 'd750-courbes-bases.png', plt)
    courbe_perso(m, out / 'd750-courbe-perso.png', plt)
    curseurs(m, out / 'd750-curseurs.png', plt)
    bases_profils(b, out / 'd750-bases-par-profil.png', plt)
    apercus(blocs, res, status_a, nef3, out / 'd750-apercus-v1.png', plt)


if __name__ == '__main__':
    main()
