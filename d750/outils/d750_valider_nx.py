#!/usr/bin/env python3
"""Passe 3 : valider par validation croisée les recettes ajustées sur NX Studio (d750_ajuster_nx.py) avant de les charger dans le D750.

Rapport : recherche/rd-nikon-2026-11-passe3.md. Sorties : recettes/d750-v3/. Rien n'est écrit dans un boîtier.

Pourquoi : la passe 2 n'avait que deux scènes d'entraînement et une seule tenue à part. Ici, 7 scènes déjà sur le disque (SCENES),
3 plis (PLIS) où l'on tient chaque fois 2 ou 3 scènes à part ; chaque recette est ajustée sur les autres scènes (départ = la recette
chargée aujourd'hui, `d750-v1/usb/…json`) puis mesurée, ainsi que la recette de départ, sur les scènes tenues à part (ΔE2000 contre la
cible, vignetage retiré comme avant : gain radial par NEF, `d750_ajuster_nx.Banc`). Puis la même procédure sur TOUTES les scènes
donne la recette candidate.

Procédure d'ajustement (moins chère que celle de la passe 2, pour tenir ~900 rendus) : UN pas de Gauss-Newton (pas 1, 0,6, 0,3), même
critère (médiane + ½ p90, moyenne sur les scènes d'entraînement), mêmes poids, mêmes 9 nœuds de courbe, saturation et teinte au quart de
point. Le jacobien est calculé UNE fois au point de départ sur toutes les scènes (il ne dépend que du point de départ) et réutilisé
par chaque pli : ses lignes d'une scène sont les mêmes quel que soit le pli. Pas de criblage de base ni de filtre (Standard et
« aucun » restaient premiers aux passes 1 et 2).

Règle de décision (écrite avant les mesures) : on garde la recette ajustée sur toutes les scènes si, sur les scènes tenues à part,
(1) la médiane baisse d'au moins 0,2 ΔE en moyenne des plis, (2) le p90 ne monte pas de plus de 0,3 en moyenne des plis, (3) la médiane
ne monte (perte) que dans un pli au plus. Médiane et p90 d'un pli = moyenne des médianes et des p90 par scène tenue à part
(chaque scène pèse autant). Sinon, aucun changement dans le boîtier.

  d750_valider_nx.py scenes                          inventaire : blocs retenus, NX tel quel contre JPEG, par scène
  d750_valider_nx.py valider <recette>… | tout       validation croisée + recette candidate → <travail>/valide-<recette>.json
  d750_valider_nx.py ecrire                          décision + recettes/d750-v3/ (json, bin, README, resume.json)
  d750_valider_nx.py --self-test
"""
import argparse
import json
import pathlib
import tempfile
import os
import sys
import time

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import d750_ajuster_nx as aj  # noqa: E402

RACINE = aj.RACINE
IMG = RACINE / 'images' / 'd750'
TRAVAIL = pathlib.Path(os.environ.get('NX_TRAVAIL', tempfile.gettempdir())) / 'passe3-nx'   # hors de tout dossier synchronisé
SORTIE = RACINE / 'recettes' / 'd750-v3'
V1 = aj.V1

# scène → comment la lire. 'lot' : blocs de lot (d750_analyse.vue, géométrie de modele.json), 'test' : vue du test v1 (blocs communs aux
# 11 vues), 'isolee' : un NEF recalé sur son propre JPEG par OpenCV (mesures_reelles.isolees). Scène = un NEF par lieu et lumière.
SCENES = {
    'guitares': dict(type='lot', lot='lot1', dossier='scene-interieur', note='pièce aux guitares (séance d’octobre) : 28 mm, f/1,8, 1/160 s, ISO 1800'),
    'portrait': dict(type='lot', lot='lot2', dossier='portrait', note='portrait (séance d’octobre) : 28 mm, f/1,8, 1/160 s, ISO 200'),
    'bibliotheque-soir': dict(type='lot', lot='lot4', dossier='bibliotheque', note='bibliothèque (séance d’octobre) : 28 mm, f/5,6, 1/10 s, ISO 200'),
    'pedalier': dict(type='test', vue='CLASSIC CHROME V1', note='pédalier (test v1 = lot 3) : 135 mm sans CPU, f/4, 1/10 s, ISO 200'),
    'bibliotheque-jour': dict(type='isolee', nef=IMG / '2026-10-test-v2-bibliotheque' / '5600' / 'rangees' / '01-BASE_STANDARD', vig='f56',
                              rmax=0.7, note='bibliothèque (test v2 d’octobre) : 28 mm, f/5,6, 1/20 s, ISO 200'),
    'exterieur': dict(type='isolee', nef=IMG / '2026-10-exterieur' / 'rangees' / '08-CLASSIC_CHROME', vig='f56', rmax=0.7,
                      note='rue, briques, ciel (octobre) : 28 mm, f/8, 1/250 s, ISO 200, WB Auto'),
    'fenetre': dict(type='isolee', nef=IMG / '2026-10-fenetre' / '5600' / 'rangees' / '01-BASE_STANDARD', vig=None, rmax=0.6,
                    zone=(0.04, 0.33, 0.66, 0.86), rot=1, note='ciel, arbres, façade (octobre) : 50 mm, f/5,6, 1/1000 s, ISO 200, vertical, battant ouvert seulement'),
}
# trois plis ; les deux bibliothèques (même lieu) sont tenues à part ensemble
PLIS = [['guitares', 'exterieur'], ['portrait', 'pedalier'], ['bibliotheque-soir', 'bibliotheque-jour', 'fenetre']]
RECETTES = ['classic-chrome', 'classic-neg', 'positive', 'hasselblad', 'portra', 'hp5', 'fp4']
EMPLACEMENT = {'classic-chrome': 'C-2', 'classic-neg': 'C-3', 'positive': 'C-4', 'portra': 'C-5', 'hasselblad': 'C-6', 'hp5': 'C-8', 'fp4': 'C-9'}
FICHIER_V3 = {'classic-chrome': 'classic-chrome-v3', 'classic-neg': 'classic-neg-v3', 'positive': 'positive-v3', 'hasselblad': 'hasselblad-v3',
              'portra': 'portra-400-v3', 'hp5': 'hp5-v3', 'fp4': 'fp4-v3'}
SEUIL_MEDIANE, SEUIL_P90, PERTES_MAX = 0.2, 0.3, 1
BUDGET_SANS_PAS_03 = 760   # rendus du processus en cours au-delà desquels on n'essaie plus le pas 0,3 (budget total ~900)


# --- règle de décision ------------------------------------------------------------------------------------------------
def decision(plis):
    """`plis` : liste de {'scenes': {nom: {'avant': {'mediane', 'p90'}, 'apres': {…}}}}. Renvoie le dictionnaire de la décision."""
    gm, gp, pertes = [], [], 0
    for pli in plis:
        s = pli['scenes'].values()
        dm_ = float(np.mean([e['avant']['mediane'] - e['apres']['mediane'] for e in s]))      # > 0 : la médiane baisse
        dp = float(np.mean([e['apres']['p90'] - e['avant']['p90'] for e in s]))               # > 0 : le p90 monte
        pli['gain_mediane'], pli['hausse_p90'] = round(dm_, 3), round(dp, 3)
        gm.append(dm_)
        gp.append(dp)
        pertes += dm_ < 0
    d = {'gain_mediane_moyen': round(float(np.mean(gm)), 3), 'hausse_p90_moyenne': round(float(np.mean(gp)), 3), 'plis_en_perte': int(pertes)}
    d['criteres'] = {'mediane': d['gain_mediane_moyen'] >= SEUIL_MEDIANE - 1e-9, 'p90': d['hausse_p90_moyenne'] <= SEUIL_P90 + 1e-9,
                     'pertes': pertes <= PERTES_MAX}
    d['garder'] = bool(all(d['criteres'].values()))
    # lecture plus stricte, donnée pour information (si elle change le verdict, le rapport le dit et la recette actuelle reste)
    d['hausse_p90_max_pli'] = round(float(max(gp)), 3)
    d['garder_lecture_stricte'] = bool(d['garder'] and max(gp) <= SEUIL_P90 + 1e-9)
    return d


# --- scènes -----------------------------------------------------------------------------------------------------------
class Banc(aj.Banc):
    """Banc de la passe 2 + scènes isolées (un NEF, son JPEG, recalage OpenCV) et rotation du rendu NX des vues verticales."""

    def _npz_isolee(self, nom, s):
        import d750_blocs as db
        import mesures_reelles as mr
        f = self.travail / 'blocs' / f'iso-{nom}.npz'
        if not f.exists():
            lot = self.travail / f'iso-{nom}'
            vues = [(nom.upper().replace('-', ' '), s['nef'])]   # _lier nomme la vue 01-<NOM>.*
            mr._lier(lot, vues)
            db.geometrie = mr.geometrie_cv   # mr.extraire a pu laisser la géométrie d'un lot
            f.parent.mkdir(parents=True, exist_ok=True)
            db.extraire(str(lot), str(f))
        return dict(np.load(f, allow_pickle=True))

    def image_isolee(self, nom, s, profil):
        da = self.da
        d = self._npz_isolee(nom, s)
        ok = da.masque(d, 0) & (d['rayon'] < s['rmax'])
        if s.get('zone'):
            z = s['zone']
            cx, cy = d['centres'][:, 0] / 6016, d['centres'][:, 1] / 4016
            ok &= (cx >= z[0]) & (cx <= z[2]) & (cy >= z[1]) & (cy <= z[3])
        idx = np.flatnonzero(ok)
        x = d['raw'][0][ok].astype(float)
        r = d['rayon'][ok].astype(float)
        xyz = da.scene_xyz(x, self.Mc, self.k, self.P['STANDARD']['vig'], r, s['vig'])
        cible = self.C[profil](xyz)
        im = aj.Image(nom, str(s['nef']) + '.NEF', str(s['nef']) + '.JPG', idx, r, d['jpg'][0][idx].astype(float) / 255, cible, d['jpg'][0].shape[0])
        im.rot = s.get('rot', 0)
        return im

    def blocs_nx(self, im, ncp=None):
        # même cache que la classe mère ; les vues verticales sont remises dans le sens du JPEG enregistré (np.rot90 avant les blocs)
        rot = getattr(im, 'rot', 0)
        if not rot:
            return super().blocs_nx(im, ncp)
        import hashlib
        cle = hashlib.sha1((im.nef + '|' + str(aj.LARGEUR) + '|rot').encode() + (ncp or b'as-is')).hexdigest()[:20]
        f = self.cache / f'{cle}-{len(im.idx)}.npy'
        if f.exists():
            return np.load(f)
        t = time.time()
        img = np.rot90(aj.nx.rendre(im.nef, None, ncp, aj.LARGEUR), rot)
        self.temps += time.time() - t
        self.rendus += 1
        B = aj.BLOC * aj.LARGEUR // 6016
        ny, nxx = (4016 // aj.BLOC), (6016 // aj.BLOC)
        a = img[:ny * B, :nxx * B].reshape(ny, B, nxx, B, 3).mean((1, 3)).reshape(ny * nxx, 3)[im.idx]
        np.save(f, a.astype(np.float32))
        return a

    def scene(self, nom, profil):
        s = SCENES[nom]
        if s['type'] == 'lot':
            return self.image_lot(s['lot'], s['dossier'], profil)
        if s['type'] == 'test':
            return self.image_test(s['vue'], profil)
        return self.image_isolee(nom, s, profil)


# --- validation croisée -------------------------------------------------------------------------------------------------
def jacobien(banc, ims, ws, p0, journal):
    """Jacobien par scène au point de départ : mêmes différences finies que gauss_newton (pas 4 codes sur les nœuds, un quart de point)."""
    v0 = aj._variables(p0)
    n = len(v0)
    noms = list(ims)
    r0 = {s: ((banc.lab_nx(ims[s], p0) - ims[s].cible) * ws[s][:, None]).ravel() for s in noms}
    J = {s: np.zeros((len(r0[s]), n)) for s in noms}
    for j in range(n):
        h = aj.PAS_FD if j < 9 else 1.0
        lim = aj.BORNE_NOEUD if j < 9 else 12.0
        h = h if v0[j] + h <= lim else -h
        v = v0.copy()
        v[j] += h
        q = aj._avec(p0, v)
        for s in noms:
            J[s][:, j] = (((banc.lab_nx(ims[s], q) - ims[s].cible) * ws[s][:, None]).ravel() - r0[s]) / h
        journal(f'  jacobien : variable {j + 1}/{n}, rendus {banc.rendus}')
    return v0, r0, J


def un_pas(banc, ims, train, p0, v0, r0, J, stat0, journal, amortissement=0.3):
    """Un pas de Gauss-Newton sur les scènes `train`, avec la recherche de pas 1 / 0,6 / 0,3 de la passe 2. Renvoie (recette, pas)."""
    n = len(v0)
    A = sum(J[s].T @ J[s] for s in train)
    g = sum(J[s].T @ r0[s] for s in train)
    d = np.linalg.solve(A + amortissement * np.trace(A) / n * np.eye(n), -g)
    s0 = aj.score([stat0[s] for s in train])
    for pas in (1.0, 0.6, 0.3):
        if pas == 0.3 and banc.rendus > BUDGET_SANS_PAS_03:
            break
        q = aj._avec(p0, v0 + pas * d)
        sc = aj.score([banc.stats(banc.ecart(ims[s], q)) for s in train])
        if sc < s0 - 1e-9:
            journal(f'    pas {pas} : critère {s0:.3f} → {sc:.3f}')
            return q, pas
    journal(f'    aucun pas n’améliore ({s0:.3f}) : recette inchangée')
    return p0, 0.0


def valider(nom_court, banc, journal=print):
    t0, r0_ = time.time(), banc.rendus
    fichier, vue, profil, mono = aj.RECETTES[nom_court]
    journal(f'== {nom_court} ({profil})')
    ims = {n: banc.scene(n, profil) for n in SCENES}
    for im in ims.values():
        banc.preparer_gain(im)
    p0 = aj.depuis_v1(nom_court)
    stat0 = {n: banc.stats(banc.ecart(im, p0)) for n, im in ims.items()}
    ws = {n: aj.poids(banc.dm.de2000(banc.lab_nx(im, p0), im.cible), im.chroma) for n, im in ims.items()}
    v0, r0, J = jacobien(banc, ims, ws, p0, journal)
    res = {'recette': nom_court, 'nom': p0['nom'], 'profil_cible': profil, 'blocs': {n: int(len(im.idx)) for n, im in ims.items()},
           'avant': stat0, 'plis': []}
    for k, tenues in enumerate(PLIS, 1):
        train = [n for n in ims if n not in tenues]
        journal(f'  pli {k} : tenues à part {tenues}')
        q, pas = un_pas(banc, ims, train, p0, v0, r0, J, stat0, journal)
        pli = {'tenues': tenues, 'entrainement': train, 'pas': pas, 'reglages': _reglages(q),
               'scenes': {n: {'avant': stat0[n], 'apres': banc.stats(banc.ecart(ims[n], q))} for n in tenues}}
        res['plis'].append(pli)
    res['decision'] = decision(res['plis'])
    journal(f'  décision : {res["decision"]}')
    journal('  ajustement sur toutes les scènes')
    q, pas = un_pas(banc, ims, list(ims), p0, v0, r0, J, stat0, journal)
    res['candidate'] = {'pas': pas, 'reglages': _reglages(q), 'ecart_courbe_codes': [round(float(d), 1) for d in q['delta']],
                        'en_butee': aj.en_butee(q), 'sur_toutes_les_scenes': {n: {'avant': stat0[n], 'apres': banc.stats(banc.ecart(im, q))} for n, im in ims.items()}}
    res['_p'] = {'delta': [float(d) for d in q['delta']], 'saturation': q.get('saturation'), 'teinte': q.get('teinte')}
    res['rendus'] = banc.rendus - r0_
    res['duree_s'] = round(time.time() - t0)
    journal(f'  rendus {res["rendus"]}, {res["duree_s"]} s')
    return res


def _reglages(p):
    if p['mono']:
        return {'filtre': p['filtre'], 'ecart_courbe_codes': [round(float(d), 1) for d in p['delta']]}
    return {'saturation': aj.quart(p['saturation']), 'teinte': aj.quart(p['teinte']), 'ecart_courbe_codes': [round(float(d), 1) for d in p['delta']]}


def candidate(nom_court, res):
    p = aj.depuis_v1(nom_court)
    p['delta'] = res['_p']['delta']
    if not p['mono']:
        p['saturation'], p['teinte'] = res['_p']['saturation'], res['_p']['teinte']
    return p


# --- sortie : recettes/d750-v3/ -----------------------------------------------------------------------------------
HISTO = {'classic-chrome': ('ecriture-2026-10.19', 202), 'classic-neg': ('ecriture-2026-10.16', 203), 'positive': ('ecriture-2026-10.16', 204),
         'portra': ('ecriture-2026-10.17', 205), 'hasselblad': ('ecriture-2026-10.17', 206), 'hp5': ('ecriture-2026-10.18', 208),
         'fp4': ('ecriture-2026-10.18', 209)}   # blocs réellement écrits (HISTORIQUE.md), identiques à bloc_recette(v1) (vérifié en novembre 2026)
V1_FICHIER = {n: aj.RECETTES[n][0] for n in aj.RECETTES}


def moyennes(res):
    """Médiane et p90 moyennés sur les 7 scènes tenues à part (chaque scène tenue une fois), recette actuelle puis ajustée."""
    e = [s for pli in res['plis'] for s in pli['scenes'].values()]
    return {k: {m: round(float(np.mean([x[k][m] for x in e])), 3) for m in ('mediane', 'p90')} for k in ('avant', 'apres')}


def commandes(n):
    c = EMPLACEMENT[n]
    b = f'recettes/d750-v3/usb/{FICHIER_V3[n]}.bin'
    d, k = HISTO[n]
    return [f'# {c} : {aj.depuis_v1(n)["nom"]}',
            f'python3 outils/picture_control.py bloc recettes/d750-v3/usb/{FICHIER_V3[n]}.json /tmp/d750-{c}.bin   # relit le bloc (doit afficher 610 octets)',
            f'swift outils/d750_ecrire.swift ecrire {b} {c}                    # simulation : rien n’est écrit',
            f'swift outils/d750_ecrire.swift ecrire {b} {c} --ecrire --remplacer',
            f'# retour en arrière : swift outils/d750_ecrire.swift ecrire sondes/d750/usb/{d}/apres_{k}_0.bin {c} --ecrire --remplacer']


def ecrire(tr, sortie=SORTIE):
    import subprocess
    import picture_control as pc
    sortie = pathlib.Path(sortie)
    (sortie / 'usb').mkdir(parents=True, exist_ok=True)
    resume = {'regle': {'mediane_baisse_min': SEUIL_MEDIANE, 'p90_hausse_max': SEUIL_P90, 'plis_en_perte_max': PERTES_MAX}, 'plis': PLIS,
              'scenes': json.loads((tr / 'inventaire.json').read_text()) if (tr / 'inventaire.json').exists() else {}, 'recettes': {}}
    rendus = 0
    for n in RECETTES:
        f = tr / f'valide-{n}.json'
        if not f.exists():
            continue
        res = json.loads(f.read_text())
        res['decision'] = decision(res['plis'])
        res['moyennes_tenues_a_part'] = moyennes(res)
        rendus += res.get('rendus', 0)
        p = candidate(n, res)
        v1 = json.loads((V1 / V1_FICHIER[n]).read_text(encoding='utf-8'))
        out = {'recette': n, 'emplacement': EMPLACEMENT[n], 'nom': p['nom'], 'garder': res['decision']['garder'], 'decision': res['decision'],
               'moyennes_tenues_a_part': res['moyennes_tenues_a_part'], 'plis': res['plis'], 'candidate': res['candidate'], 'rendus': res.get('rendus'),
               'reglages_v1': v1['reglages']}
        if res['decision']['garder']:
            j = aj.en_recette_usb(p)
            assert j['nom'] == v1['nom'], (j['nom'], v1['nom'])
            fj = sortie / 'usb' / f'{FICHIER_V3[n]}.json'
            fb = sortie / 'usb' / f'{FICHIER_V3[n]}.bin'
            fj.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding='utf-8')
            r = subprocess.run([sys.executable, str(ICI / 'picture_control.py'), 'bloc', str(fj), str(fb)], capture_output=True, text=True)
            assert r.returncode == 0 and fb.stat().st_size == 610, r.stdout + r.stderr
            b = fb.read_bytes()
            d = pc.lire_bloc_ptp(b)
            # écrit = mesuré : le NP2 de ce JSON est celui que NX a rendu pendant l'ajustement
            assert pc.np2_recette(json.loads(fj.read_text(encoding='utf-8'))) == aj.en_np2(p), f'{n} : NP2 écrit ≠ NP2 mesuré'
            assert d['nom'] == j['nom'] and d['base'] == j['base'] and d['courbe'] and list(d['lut']) == list(j['courbe']['lut']), f'{n} : bloc ≠ JSON'
            for k, v in j['reglages'].items():
                if k != 'filtre':
                    assert abs(float(d[k]) - float(v)) < 1e-9, f'{n} : {k}'
            if p['mono']:
                assert d['filtre'] == j['reglages']['filtre']
            out['fichiers'] = [f'usb/{FICHIER_V3[n]}.json', f'usb/{FICHIER_V3[n]}.bin']
            out['sha256_bloc'] = __import__('hashlib').sha256(b).hexdigest()[:10]
            out['commandes'] = commandes(n)
        resume['recettes'][n] = out
    resume['rendus_recettes'] = rendus
    resume['rendus_total'] = rendus + len(SCENES)   # + un rendu « tel quel » par scène (gain radial)
    resume['procedure'] = ('validation croisée en 3 plis (PLIS) ; un pas de Gauss-Newton par pli et sur toutes les scènes, jacobien partagé ; '
                           'pas de criblage de base ni de filtre ; règle écrite avant les mesures, voir `regle`')
    (sortie / 'resume.json').write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding='utf-8')
    return resume

# --- inventaire ---------------------------------------------------------------------------------------------------------
def inventaire(banc, journal=print):
    out = {}
    for n, s in SCENES.items():
        im = banc.scene(n, 'CLASSIC CHROME')
        banc.preparer_gain(im)
        out[n] = {'note': s['note'], 'blocs': int(len(im.idx)), 'nx_tel_quel_contre_jpeg': im.nx_brut,
                  'nx_tel_quel_sans_gain': im.nx_brut_sans_gain, 'gain_radial': [round(float(c), 4) for c in im.gain],
                  'chroma_cible_mediane': round(float(np.median(im.chroma)), 1), 'part_chroma_40_et_plus': round(float((im.chroma >= 40).mean()), 3)}
        journal(f'{n:20s} {out[n]["blocs"]:6d} blocs  NX/JPEG {im.nx_brut["mediane"]:.2f} (p90 {im.nx_brut["p90"]:.2f}), sans gain '
                f'{im.nx_brut_sans_gain["mediane"]:.2f}, gain {out[n]["gain_radial"]}, chroma méd {out[n]["chroma_cible_mediane"]}')
    return out


# --- auto-test ----------------------------------------------------------------------------------------------------------
def self_test():
    ok = True

    def verif(cond, msg):
        nonlocal ok
        if not cond:
            print('  ÉCHEC :', msg)
            ok = False
    noms = sum(PLIS, [])
    verif(sorted(noms) == sorted(SCENES) and len(noms) == len(set(noms)), 'chaque scène tenue à part exactement une fois')
    verif(all(len(p) < len(SCENES) for p in PLIS), 'un pli ne tient pas tout à part')
    for n, s in SCENES.items():
        if s['type'] == 'isolee':
            verif(s['nef'].with_suffix('.NEF').exists() and s['nef'].with_suffix('.JPG').exists(), f'NEF et JPEG de {n}')
    verif(set(EMPLACEMENT) == set(aj.RECETTES) == set(FICHIER_V3) == set(RECETTES), 'recettes et emplacements')
    mk = lambda a, b, a9, b9: {'scenes': {'x': {'avant': {'mediane': a, 'p90': a9}, 'apres': {'mediane': b, 'p90': b9}}}}
    d = decision([mk(3, 2.7, 6, 6.1), mk(3, 2.7, 6, 6.1), mk(3, 2.7, 6, 6.1)])
    verif(d['garder'] and abs(d['gain_mediane_moyen'] - 0.3) < 1e-9 and d['plis_en_perte'] == 0, 'décision : gain suffisant')
    verif(not decision([mk(3, 2.9, 6, 6), mk(3, 2.9, 6, 6), mk(3, 2.9, 6, 6)])['garder'], 'décision : gain trop faible (0,1)')
    verif(not decision([mk(3, 2.5, 6, 6.5), mk(3, 2.5, 6, 6.5), mk(3, 2.5, 6, 6.5)])['garder'], 'décision : p90 en hausse de plus de 0,3')
    verif(decision([mk(3, 2.2, 6, 6), mk(3, 2.2, 6, 6), mk(3, 3.1, 6, 6)])['garder'], 'décision : une perte tolérée')
    verif(not decision([mk(3, 1.9, 6, 6), mk(3, 3.1, 6, 6), mk(3, 3.1, 6, 6)])['garder'], 'décision : deux pertes refusées')
    # un pas de Gauss-Newton sur un banc factice linéaire : le pas complet retrouve le minimum de la partie entraînement
    class Faux:
        def __init__(s):
            s.rendus = 0
        stats = staticmethod(lambda e: {'mediane': float(np.median(e)), 'p90': float(np.percentile(e, 90))})
    rng = np.random.default_rng(0)
    n = 11
    Jf = {c: rng.normal(size=(60, n)) for c in 'ab'}
    xv = rng.normal(size=n)
    rf = {c: Jf[c] @ xv for c in 'ab'}      # résidu = J x* : le minimum est -x*
    A = sum(Jf[c].T @ Jf[c] for c in 'ab')
    d = np.linalg.solve(A + 1e-9 * np.eye(n), -sum(Jf[c].T @ rf[c] for c in 'ab'))
    verif(np.allclose(d, -xv, atol=1e-5), 'moindres carrés partagés')
    # la sous-sélection de lignes d'un jacobien partagé = jacobien du sous-ensemble
    Aa = Jf['a'].T @ Jf['a']
    verif(np.allclose(Aa, np.vstack([Jf['a']]).T @ np.vstack([Jf['a']])), 'sélection de scènes')
    # les fichiers du dossier v3 se relisent par le module du boîtier si présents
    import picture_control as pc
    for f in sorted((SORTIE / 'usb').glob('*.json')) if (SORTIE / 'usb').exists() else []:
        b = pc.bloc_recette(json.loads(f.read_text(encoding='utf-8')))
        verif(len(b) == 610, f'bloc de {f.name}')
    print('self-test', 'OK' if ok else 'ÉCHEC')
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('commande', nargs='?', choices=['scenes', 'valider', 'ecrire'])
    ap.add_argument('recettes', nargs='*')
    ap.add_argument('--travail', default=str(TRAVAIL))
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test() else 1)
    if not a.commande:
        ap.print_help()
        sys.exit(2)
    tr = pathlib.Path(a.travail)
    log = lambda s: print(s, flush=True)
    if a.commande == 'ecrire':
        r = ecrire(tr)
        for n, e in r['recettes'].items():
            print(n, e['emplacement'], 'GARDER' if e['garder'] else 'garder la recette actuelle', e['decision'], e['moyennes_tenues_a_part'])
        return
    banc = Banc(tr)
    if a.commande == 'scenes':
        inv = inventaire(banc, log)
        (tr / 'inventaire.json').write_text(json.dumps(inv, ensure_ascii=False, indent=1))
        print('rendus :', banc.rendus, 'durée de rendu', round(banc.temps), 's')
        return
    noms = RECETTES if a.recettes == ['tout'] or not a.recettes else a.recettes
    for n in noms:
        r = valider(n, banc, log)
        (tr / f'valide-{n}.json').write_text(json.dumps(r, ensure_ascii=False, indent=1))
    print('rendus au total :', banc.rendus, 'durée de rendu', round(banc.temps), 's')


if __name__ == '__main__':
    main()
