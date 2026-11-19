#!/usr/bin/env python3
"""Réajuster les recettes du D750 sur le VRAI moteur de Nikon (NX Studio, SaveProcess) au lieu de notre modèle.

Prototype de novembre 2026 (veille-picture-control-2026-11.md, §2 idée n° 2 ; rapport : recherche/rd-nikon-2026-11-ajustement-nx.md).
Méthode inspirée de gerard662/nikon-picture-control-matcher (MIT, Copyright (c) Gerard Needham) : Gauss-Newton borné, jacobien
par différences finies sur de vrais rendus, poids qui réduisent les pires blocs, pas 1 / 0,6 / 0,3, arrêt si le gain est
inférieur à 0,005, liste des réglages en butée. Le code est écrit ici.

Chaîne, pour une recette R et un NEF :
  NEF --NX Studio (Picture Control R imposé par un NCP, outils/nx_rendu.py)--> TIFF sRGB --blocs de 24 px (grille du JPEG)-->
  gain radial (vignetage du boîtier, ajusté une fois par NEF : NX tel quel contre JPEG du boîtier) --> ΔE2000 contre la cible
  du look, calculée depuis la scène lue dans le même NEF (blocs de mesures_reelles / d750_analyse, importés, non modifiés).

Entraînement : vues BASE STANDARD des lots de calibration `lot1` (pièce aux guitares, 28 mm f/1,8) et `lot4` (bibliothèque,
28 mm f/5,6). Tenue à part : la vue du test v1 (pédalier, 135 mm, lot 3 : même scène que le test) : le `lot3` n'entre donc
pas dans l'entraînement. Le NEF d'une vue du test v1 est celui de sa recette : seule la scène compte, la recette est
imposée par le NCP.

Paramètres ajustés : base (criblée une fois, une recette par candidate), saturation et teinte (au quart de point, en NP2 ; la passe 1 en NCP
les avait entiers), courbe perso = 9 nœuds d'écart ajoutés à la courbe v1
(interpolation monotone), en N&B : filtre et courbe.

  d750_ajuster_nx.py ajuster <recette> [<recette>…] [--sortie dossier] [--travail dossier]   (recettes : voir RECETTES)
  d750_ajuster_nx.py tout
  d750_ajuster_nx.py --self-test
"""
import argparse
import hashlib
import json
import os
import pathlib
import tempfile
import sys
import time

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
os.environ.setdefault('D750_LOOKS', str(RACINE / 'images' / 'd750' / 'portra-cibles' / 'preset'))

import picture_control as pc  # noqa: E402
import nx_rendu as nx  # noqa: E402

TRAVAIL = pathlib.Path(os.environ.get('NX_TRAVAIL', tempfile.gettempdir())) / 'ajuster-nx'   # hors de tout dossier synchronisé
V1 = RACINE / 'recettes' / 'd750-v1' / 'usb'
SORTIE = RACINE / 'recettes' / 'd750-nx' / 'usb'
LARGEUR = 3008          # SaveProcess demi-résolution : même durée (le décodage domine), blocs de 12 px au lieu de 24
BLOC = 24               # px du JPEG
NOEUDS_X = np.array([0.06, 0.15, 0.25, 0.37, 0.50, 0.62, 0.75, 0.87, 0.95]) * 255   # 9 nœuds d'écart de la courbe
BORNE_NOEUD = 40.0      # codes 0..255, écart maximal à la courbe v1
PAS_FD = 4.0            # codes, pas de différence finie (la courbe est écrite en 20 points entiers sur 8 bits)
BASES_COULEUR = {'Standard': 0x0001, 'Neutre': 0x03C2, 'Portrait': 0x0486}
FILTRES = ['aucun', 'jaune', 'orange', 'rouge', 'vert']

# nom court → (fichier v1, vue du test v1, profil de cible (d750_cibles), mono)
RECETTES = {
    'classic-chrome': ('classic-chrome-v1.json', 'CLASSIC CHROME V1', 'CLASSIC CHROME', False),
    'classic-neg': ('classic-neg-v1.json', 'CLASSIC NEG V1', 'CLASSIC NEG', False),
    'positive': ('positive-v1.json', 'POSITIVE V1', 'POSITIVE', False),
    'hasselblad': ('hasselblad-v1.json', 'HASSELBLAD V1', 'HASSELBLAD', False),
    'portra': ('portra-400-v2.json', 'PORTRA 400 V1', 'PORTRA ESPRIT', False),
    'hp5': ('hp5-v1.json', 'HP5 V1', 'HP5', True),
    'fp4': ('fp4-v1.json', 'FP4 V1', 'FP4', True),
}
JPEG_RECETTE = {'portra': 'portra-400-v1 (la vue a été prise avec la v1, la recette ajustée part de la v2 écrite dans le boîtier : pas comparable)'}
ENTRAINEMENT = [('lot1', 'scene-interieur'), ('lot4', 'bibliotheque')]


# --- paramétrage ↔ NCP --------------------------------------------------------------------------------------------
def courbe_decalee(lut0, delta):
    """Courbe v1 + écart de 9 nœuds (codes 0..255, interpolation monotone PCHIP nulle aux extrémités).

    NX Studio ne lit PAS la table de 257 valeurs d'un NCP mais ses 20 points d'ancrage entiers (vérifié en novembre 2026 : une
    table modifiée entre les points, ancrages inchangés, donne un rendu identique à l'octet près) : la courbe est donc définie
    par ces 20 points, la table de 257 valeurs en est tirée par `lut_points` (monotone, comme celle du boîtier)."""
    from scipy.interpolate import PchipInterpolator
    pts = pc.points_courbe([int(v) for v in lut0])
    xs = np.array([x for x, _ in pts], float)
    y0 = np.array([y for _, y in pts], float)
    d = np.clip(np.asarray(delta, float), -BORNE_NOEUD, BORNE_NOEUD)
    y = y0 + PchipInterpolator(np.r_[0, NOEUDS_X, 255], np.r_[0, d, 0])(xs)
    y = np.maximum.accumulate(np.clip(np.round(y), 0, 255))
    return pc.lut_points(list(zip(xs.tolist(), y.tolist())))


def quart(v):
    """Arrondi au quart de point (pas du boîtier), dans les bornes de BORNES_PTP (saturation, teinte)."""
    return float(np.clip(round(float(v) * 4) / 4, -3, 3))


def en_ncp(p):
    """Paramètres → octets d'un .NCP (curseurs entiers ; contraste et luminosité « gérés par la courbe »). Passe 1, gardé pour comparaison."""
    lut = courbe_decalee(p['lut0'], p['delta'])
    cur = {'accentuation': p.get('accentuation', 0), 'contraste': 'courbe', 'luminosite': 'courbe'}
    if p['mono']:
        cur.update(saturation=None, teinte=None, filtre=FILTRES.index(p['filtre']), virage=0, force_virage=None)
        base = 0x064D
    else:
        cur.update(saturation=int(round(p['saturation'])), teinte=int(round(p['teinte'])), filtre=None, virage=None, force_virage=None)
        base = BASES_COULEUR[p['base']]
    return pc.ecrire_ncp(p['nom'][:19], base, cur, lut)


def en_np2(p):
    """Paramètres → octets d'un .NP2 (quarts de point, clarté, table de 257 valeurs) : NX le rend comme le NEF qui porte les mêmes réglages."""
    lut = courbe_decalee(p['lut0'], p['delta'])
    reg = {'accentuation': p.get('accentuation', 0), 'clarte': p.get('clarte', 0)}
    if p['mono']:
        reg.update(filtre=FILTRES.index(p['filtre']))
        base = 0x064D
    else:
        reg.update(saturation=quart(p['saturation']), teinte=quart(p['teinte']))
        base = BASES_COULEUR[p['base']]
    return pc.ecrire_np2(p['nom'][:19], base, reg, lut)


def en_pc(p):
    return en_ncp(p) if p.get('fmt') == 'ncp' else en_np2(p)


def en_recette_usb(p):
    """Même format que d750-v1/usb/*.json (lut de 257 valeurs, curseurs en points)."""
    reg = {'accentuation': p.get('accentuation', 0), 'clarte': p.get('clarte', 0)}
    if p['mono']:
        reg['filtre'] = p['filtre']
    else:
        reg.update(saturation=quart(p['saturation']), teinte=quart(p['teinte']))
    return {'nom': p['nom'], 'base': 'Monochrome' if p['mono'] else p['base'], 'reglages': reg,
            'courbe': {'lut': courbe_decalee(p['lut0'], p['delta'])}}


def depuis_v1(nom_court):
    fichier, vue, profil, mono = RECETTES[nom_court]
    r = json.loads((V1 / fichier).read_text(encoding='utf-8'))
    reg = r['reglages']
    p = {'nom': r['nom'], 'mono': mono, 'base': r['base'], 'lut0': list(r['courbe']['lut']), 'delta': [0.0] * 9,
         'accentuation': reg.get('accentuation', 0), 'clarte': reg.get('clarte', 0), 'vue': vue, 'profil': profil}
    if mono:
        p['filtre'] = reg.get('filtre', 'aucun')
    else:
        p.update(saturation=reg.get('saturation', 0), teinte=reg.get('teinte', 0))
    return p


def np2_du_bloc(vue):
    """NP2 de la recette réellement envoyée au boîtier pour cette vue du test v1 (blocs/NN.bin), décodée puis réécrite en NP2 : sert à
    prouver que le chemin NX reproduit le boîtier avec la recette chargée (pour Portra, ce n'est pas la v2 écrite aujourd'hui)."""
    import mesures_reelles as mr
    r = pc.lire_bloc_ptp((mr.TEST / mr.VUES[vue][2]).read_bytes())
    reg = {'accentuation': r['accentuation'], 'clarte': r['clarte']}
    if r['monochrome']:
        reg['filtre'] = FILTRES.index(r['filtre'])
        base = 0x064D
    else:
        reg.update(saturation=r['saturation'], teinte=r['teinte'])
        base = BASES_COULEUR[r['base']]
    return pc.ecrire_np2(r['nom'][:19], base, reg, r['lut'] if r['courbe'] else None)


def en_butee(p):
    """Réglages au bout de leur plage : nœuds de la courbe, saturation, teinte (BORNES_PTP du boîtier)."""
    out = []
    for i, d in enumerate(p['delta']):
        if abs(d) >= BORNE_NOEUD - 0.5:
            out.append(f'courbe, nœud {i + 1} (x = {NOEUDS_X[i]:.0f}) : {d:+.0f} codes')
    if not p['mono']:
        for k in ('saturation', 'teinte'):
            b = pc.BORNES_PTP[k]
            if quart(p[k]) in (b[0], b[1]):
                out.append(f'{k} : {p[k]:+g} (limite du boîtier {b[0]:+g} à {b[1]:+g})')
    return out


# --- couleur ---------------------------------------------------------------------------------------------------------
def _lin(v):
    return np.where(v <= 0.04045, v / 12.92, ((np.clip(v, 0, None) + 0.055) / 1.055) ** 2.4)


def _enc(v):
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.clip(v, 0, None) ** (1 / 2.4) - 0.055)


def ajuster_gain(A, B, r):
    """Gain radial c0 + c1 r² + c2 r⁴ (linéaire) tel que A·gain ≈ B (même ajustement que nx_rendu.comparer)."""
    la, lb = _lin(A).mean(-1), _lin(B).mean(-1)
    X = np.stack([np.ones_like(r), r ** 2, r ** 4], 1)
    return np.linalg.lstsq(X * la[:, None], lb, rcond=None)[0]


def appliquer_gain(A, r, c):
    X = np.stack([np.ones_like(r), r ** 2, r ** 4], 1)
    return np.clip(_enc(_lin(A) * (X @ c)[:, None]), 0, 1)


def poids(dE, chroma):
    """Poids de gerard662 : couleurs de tous les jours (1 sous 45, 0,6 sous 60, 0,3 au-delà), pires blocs réduits."""
    wc = np.where(chroma < 45, 1.0, np.where(chroma < 60, 0.6, 0.3))
    return np.sqrt(wc) / np.sqrt(dE + 0.5)


def score(s):
    """Critère d'ajustement et d'acceptation d'un pas : médiane + la moitié du p90 (moyenne sur les images)."""
    return float(np.mean([e['mediane'] + 0.5 * e['p90'] for e in s]))


# --- une image : blocs, cible, rendu ---------------------------------------------------------------------------------
class Image:
    """NEF + JPEG du boîtier + blocs retenus + cible : tout ce qu'il faut pour noter un rendu NX."""

    def __init__(self, nom, nef, jpg, idx, rayon, jpeg_blocs, cible_lab, grille):
        self.nom, self.nef, self.jpg, self.idx, self.rayon = nom, str(nef), str(jpg), idx, rayon
        self.jpeg_blocs, self.cible, self.grille = jpeg_blocs, cible_lab, grille
        self.gain = None
        self.chroma = np.hypot(cible_lab[:, 1], cible_lab[:, 2])


class Banc:
    """Contexte commun : cibles, géométrie, cache et compteur de rendus."""

    def __init__(self, travail=TRAVAIL):
        import d750_analyse as da
        import d750_cibles as dc
        import d750_modele as dm
        self.da, self.dc, self.dm = da, dc, dm
        self.travail = pathlib.Path(travail)
        self.cache = self.travail / 'cache'
        if not (self.travail / 'blocs' / 'lot4.npz').exists():   # blocs (JPEG, NEF) des lots : géométrie par OpenCV, une fois
            import mesures_reelles as mr
            mr.extraire(self.travail)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.rendus = 0
        self.temps = 0.0
        m = json.loads((RACINE / 'recherche' / 'donnees-films' / 'd750-seances' / 'modele.json').read_text())
        self.m = m
        self.P = {b: m['bases'][b]['parametres'] for b in da.BASES}
        self.Mc, self.k, self.st = da.matrice_camera()
        C = dc.toutes(None)     # sans Kodachrome : la cible (Status A d'agx-emulsion, spektrafilm) n'est pas sur ce disque
        C.update({'TRI-X': dc.cible_nb('preset_trix', dc.courbe_trix_preset()),
                  'HP5': dc.cible_nb('hp5_fiche', da.courbe_hp5_scans(m, self.k)), 'FP4': dc.cible_nb('fp4_fiche', dc.courbe_film('fp4'))})
        self.C = C
        self._test = None

    # -- images -----------------------------------------------------------------------------------------------------
    def _jpeg_blocs(self, k, idx, d):
        return d['jpg'][k][idx].astype(float) / 255

    def image_test(self, vue, profil):
        da, dm = self.da, self.dm
        if self._test is None:
            d = dict(np.load(self.travail / 'blocs' / 'test.npz', allow_pickle=True))
            noms = [str(n) for n in d['noms']]
            commun = np.logical_and.reduce([da.masque(d, i) for i in range(len(noms))])   # mêmes blocs que mesures_reelles
            self._test = (d, noms, commun)
        d, noms, commun = self._test
        i = noms.index(vue)
        ref = d['wb'][noms.index('CLASSIC CHROME V1')]
        x = d['raw'][i][commun].astype(float) * (ref / d['wb'][i])
        cible = self.C[profil](self.k * da.cam_xyz(x, self.Mc))
        plan = json.loads((RACINE / 'images' / 'd750' / '2026-10-test-v1' / 'plan-complet.json').read_text())['vues']
        n = next(v['numero'] for v in plan if v['nom'] == vue)
        base = RACINE / 'images' / 'd750' / '2026-10-test-v1' / 'rangees' / f"{n:02d}-{vue.replace(' ', '_')}"
        idx = np.flatnonzero(commun)
        return Image(vue, str(base) + '.NEF', str(base) + '.JPG', idx, d['rayon'][commun].astype(float),
                     self._jpeg_blocs(i, idx, d), cible, d['jpg'][i].shape[0])

    def image_lot(self, lot, dossier, profil):
        da = self.da
        v = da.vue(str(self.travail / 'blocs'), lot, 'BASE STANDARD')
        d = da.charger(str(self.travail / 'blocs'), lot)
        J = {'x': v['x'], 'r': v['r'], 'vig': np.array([v['vig'] or ''] * len(v['x']))}
        xyz = da.xyz_jeu(J, self.Mc, self.k, self.P['STANDARD']['vig'])
        cible = self.C[profil](xyz)
        base = RACINE / 'images' / 'd750' / f'2026-10-seance-{dossier}' / 'rangees' / '01-BASE_STANDARD'
        return Image(f'{lot} BASE STANDARD', str(base) + '.NEF', str(base) + '.JPG', v['idx'], v['r'],
                     self._jpeg_blocs(0, v['idx'], d), cible, d['jpg'][0].shape[0])

    # -- rendu -------------------------------------------------------------------------------------------------------
    def blocs_nx(self, im, ncp=None):
        """Moyennes par bloc du rendu NX (codes 0..1) aux blocs retenus de `im`, sans gain. Cache disque par (NEF, NCP)."""
        cle = hashlib.sha1((im.nef + '|' + str(LARGEUR)).encode() + (ncp or b'as-is')).hexdigest()[:20]
        f = self.cache / f'{cle}-{len(im.idx)}.npy'
        if f.exists():
            return np.load(f)
        t = time.time()
        img = nx.rendre(im.nef, None, ncp, LARGEUR)   # un NP2 passe SavedPicConProcess=1 tout seul (nx_rendu.options_pc)
        self.temps += time.time() - t
        self.rendus += 1
        B = BLOC * LARGEUR // 6016
        H, W = img.shape[:2]
        ny, nxx = (4016 // BLOC), (6016 // BLOC)
        a = img[:ny * B, :nxx * B].reshape(ny, B, nxx, B, 3).mean((1, 3)).reshape(ny * nxx, 3)[im.idx]
        np.save(f, a.astype(np.float32))
        return a

    def preparer_gain(self, im):
        """Gain radial de ce NEF : NX tel quel (réglages du NEF) contre le JPEG du boîtier."""
        A = self.blocs_nx(im, None)
        im.gain = ajuster_gain(A, im.jpeg_blocs, im.rayon)
        im.nx_brut = self.stats(self.dm.de2000(self.dm.code_lab(appliquer_gain(A, im.rayon, im.gain)), self.dm.code_lab(im.jpeg_blocs)))
        im.nx_brut_sans_gain = self.stats(self.dm.de2000(self.dm.code_lab(A), self.dm.code_lab(im.jpeg_blocs)))

    def stats(self, e):
        return {'mediane': float(np.median(e)), 'p90': float(np.percentile(e, 90)), 'blocs': int(len(e))}

    def lab_nx(self, im, p_ou_ncp):
        ncp = p_ou_ncp if isinstance(p_ou_ncp, (bytes, type(None))) else en_pc(p_ou_ncp)
        A = appliquer_gain(self.blocs_nx(im, ncp), im.rayon, im.gain)
        return self.dm.code_lab(A)

    def ecart(self, im, p):
        L = self.lab_nx(im, p)
        return self.dm.de2000(L, im.cible)

    def noter(self, ims, p):
        return [self.stats(self.ecart(im, p)) for im in ims]

    def reference_boitier(self, im):
        """JPEG du boîtier contre la cible, mêmes blocs."""
        return self.stats(self.dm.de2000(self.dm.code_lab(im.jpeg_blocs), im.cible))


# --- ajustement ------------------------------------------------------------------------------------------------------
def residus(banc, ims, p):
    """Vecteur pondéré (L, a, b de l'écart NX − cible), poids de gerard662 recalculés sur l'état courant."""
    r = []
    for im in ims:
        L = banc.lab_nx(im, p)
        dE = banc.dm.de2000(L, im.cible)
        r.append(((L - im.cible) * poids(dE, im.chroma)[:, None]).ravel())
    return np.concatenate(r)


def residus_avec_poids(banc, ims, p, ws):
    return np.concatenate([((banc.lab_nx(im, p) - im.cible) * w[:, None]).ravel() for im, w in zip(ims, ws)])


def poids_courants(banc, ims, p):
    return [poids(banc.dm.de2000(banc.lab_nx(im, p), im.cible), im.chroma) for im in ims]


def _variables(p):
    """Vecteur ajusté : 9 nœuds de courbe (codes) puis, en couleur, saturation et teinte en quarts de point (4 par point : même ordre
    de grandeur que les codes)."""
    v = list(p['delta'])
    if not p['mono']:
        v += [4 * p['saturation'], 4 * p['teinte']]
    return np.array(v, float)


def _avec(p, v):
    q = dict(p, delta=[float(x) for x in np.clip(v[:9], -BORNE_NOEUD, BORNE_NOEUD)])
    if not p['mono']:
        q['saturation'], q['teinte'] = quart(v[9] / 4), quart(v[10] / 4)
    return q


def gauss_newton(banc, ims, p, iters=2, amortissement=0.3, journal=print):
    """Courbe (9 nœuds) et, en couleur, saturation et teinte au quart de point. Jacobien par différences finies sur de vrais
    rendus NX (pas de 4 codes, 1 quart de point), pas 1, 0,6, 0,3, arrêt si le gain est < 0,005."""
    s0 = score(banc.noter(ims, p))
    for it in range(iters):
        v0 = _variables(p)
        n = len(v0)
        ws = poids_courants(banc, ims, p)
        r0 = residus_avec_poids(banc, ims, _avec(p, v0), ws)
        J = np.zeros((len(r0), n))
        for j in range(n):
            h = PAS_FD if j < 9 else 1.0
            lim = BORNE_NOEUD if j < 9 else 12.0
            h = h if v0[j] + h <= lim else -h
            v = v0.copy()
            v[j] += h
            J[:, j] = (residus_avec_poids(banc, ims, _avec(p, v), ws) - r0) / h
        A = J.T @ J
        lam = amortissement * np.trace(A) / n
        d = np.linalg.solve(A + lam * np.eye(n), -J.T @ r0)
        mieux = None
        for pas in (1.0, 0.6, 0.3):
            q = _avec(p, v0 + pas * d)
            s = score(banc.noter(ims, q))
            if s < s0 - 1e-9:
                mieux = (q, s, pas)
                break
        if mieux is None:
            journal(f'  GN {it + 1} : aucun pas n’améliore ({s0:.3f}), arrêt')
            break
        gain = s0 - mieux[1]
        journal(f'  GN {it + 1} : pas {mieux[2]} → critère {s0:.3f} → {mieux[1]:.3f} (gain {gain:.3f}), rendus {banc.rendus}')
        p, s0 = mieux[0], mieux[1]
        if gain < 0.005:
            break
    return p


def pas_entiers(banc, ims, p, journal=print):
    """Saturation et teinte (entiers) : un tour de voisins ±1, on garde le meilleur s'il améliore le critère."""
    s0 = score(banc.noter(ims, p))
    meilleur = (s0, p)
    for k in ('saturation', 'teinte'):
        for dv in (-1, 1):
            v = p[k] + dv
            if not pc.BORNES_PTP[k][0] <= v <= pc.BORNES_PTP[k][1]:
                continue
            q = dict(p, **{k: v})
            s = score(banc.noter(ims, q))
            if s < meilleur[0] - 1e-9:
                meilleur = (s, q)
    journal(f'  entiers : {s0:.3f} → {meilleur[0]:.3f} (saturation {meilleur[1]["saturation"]:+d}, teinte {meilleur[1]["teinte"]:+d})')
    return meilleur[1]


def cribler_base(banc, ims, p, journal=print):
    """Une recette par base candidate (courbe, saturation, teinte de la v1) ; on ne change que si l'écart gagne plus de 0,3."""
    s0 = score(banc.noter(ims, p))
    essais = {p['base']: s0}
    meilleur = (s0, p)
    for b in BASES_COULEUR:
        if b == p['base']:
            continue
        q = dict(p, base=b)
        s = essais[b] = score(banc.noter(ims, q))
        if s < meilleur[0] - 0.3:
            meilleur = (s, q)
    journal(f'  bases : { {k: round(v, 2) for k, v in essais.items()} } → {meilleur[1]["base"]}')
    return meilleur[1], essais


def cribler_filtre(banc, ims, p, journal=print):
    s0 = score(banc.noter(ims, p))
    essais = {p['filtre']: s0}
    meilleur = (s0, p)
    for f in FILTRES:
        if f == p['filtre']:
            continue
        q = dict(p, filtre=f)
        s = essais[f] = score(banc.noter(ims, q))
        if s < meilleur[0] - 0.3:
            meilleur = (s, q)
    journal(f'  filtres : { {k: round(v, 2) for k, v in essais.items()} } → {meilleur[1]["filtre"]}')
    return meilleur[1], essais


def ajuster(nom_court, banc, sortie, journal=print):
    fichier, vue, profil, mono = RECETTES[nom_court]
    t0, r0 = time.time(), banc.rendus
    journal(f'== {nom_court} ({profil})')
    ims = [banc.image_lot(lot, dos, profil) for lot, dos in ENTRAINEMENT]
    tenue = banc.image_test(vue, profil)
    for im in ims + [tenue]:
        banc.preparer_gain(im)
    p = depuis_v1(nom_court)
    res = {'recette': nom_court, 'nom': p['nom'], 'profil_cible': profil, 'fichier_v1': fichier, 'entrainement': [im.nom for im in ims],
           'tenue_a_part': vue, 'blocs_tenue_a_part': int(len(tenue.idx)),
           'blocs_entrainement': [int(len(im.idx)) for im in ims], 'verification_NX_contre_JPEG': {
               im.nom: {'avec_gain': im.nx_brut, 'sans_gain': im.nx_brut_sans_gain, 'gain_radial': [round(float(c), 4) for c in im.gain]} for im in ims + [tenue]}}
    res['boitier_v1_contre_cible_tenue'] = banc.reference_boitier(tenue)
    res['recette_du_jpeg_de_la_vue'] = JPEG_RECETTE.get(nom_court, 'v1 (celle qu’on ajuste)')
    jl = banc.dm.code_lab(tenue.jpeg_blocs)
    res['nx_np2_v1_contre_jpeg_tenue'] = banc.stats(banc.dm.de2000(banc.lab_nx(tenue, p), jl))
    res['nx_ncp_v1_contre_jpeg_tenue'] = banc.stats(banc.dm.de2000(banc.lab_nx(tenue, dict(p, fmt='ncp')), jl))
    res['nx_tel_quel_contre_jpeg_tenue'] = tenue.nx_brut
    res['nx_np2_recette_chargee_contre_jpeg_tenue'] = banc.stats(banc.dm.de2000(banc.dm.code_lab(
        appliquer_gain(banc.blocs_nx(tenue, np2_du_bloc(vue)), tenue.rayon, tenue.gain)), jl))
    res['avant'] = {'tenue': banc.noter([tenue], p)[0], 'entrainement': dict(zip([im.nom for im in ims], banc.noter(ims, p)))}
    journal(f'  avant : tenue {res["avant"]["tenue"]}  entraînement {res["avant"]["entrainement"]}')
    if mono:
        p, res['filtres'] = cribler_filtre(banc, ims, p, journal)
    else:
        p, res['bases'] = cribler_base(banc, ims, p, journal)
    p = gauss_newton(banc, ims, p, journal=journal)
    # APRÈS : recette finale arrondie (celle qui sera écrite), re-rendue
    res['apres'] = {'tenue': banc.noter([tenue], p)[0], 'entrainement': dict(zip([im.nom for im in ims], banc.noter(ims, p)))}
    res['reglages'] = {k: (quart(p[k]) if k in ('saturation', 'teinte') else p[k]) for k in (('filtre',) if mono else ('base', 'saturation', 'teinte'))}
    res['ecart_courbe_codes'] = [round(float(d), 1) for d in p['delta']]
    res['en_butee'] = en_butee(p)
    res['rendus'] = banc.rendus - r0
    res['duree_s'] = round(time.time() - t0)
    journal(f'  après : tenue {res["apres"]["tenue"]}  entraînement {res["apres"]["entrainement"]}  rendus {res["rendus"]}')
    sortie = pathlib.Path(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    out = en_recette_usb(p)
    (sortie / f'{nom_court}-nx.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    (sortie / f'{nom_court}-nx.NP2').write_bytes(en_np2(p))
    res['fichier'] = f'usb/{nom_court}-nx.json'
    return res


# --- auto-test -------------------------------------------------------------------------------------------------------
def self_test():
    ok = True

    def verif(cond, msg):
        nonlocal ok
        if not cond:
            print('  ÉCHEC :', msg)
            ok = False
    p = depuis_v1('classic-chrome')
    # 1. aller-retour paramétrage ↔ NCP
    r = pc.lire(en_ncp(p))
    verif(r['base'] == 'Standard' and r['curseurs']['saturation'] == p['saturation'] and r['curseurs']['teinte'] == p['teinte']
          and r['curseurs']['contraste'] == 'courbe', 'curseurs NCP')
    verif(max(abs(a - b) for a, b in zip(r['courbe']['lut'], p['lut0'])) * 255 / 32767 < 3, 'courbe v1 retrouvée (écart nul) à 3 codes près')
    verif(len(r['courbe']['points']) == 20, '20 points d’ancrage écrits')
    # 1 bis. NP2 : quarts de point, clarté, base, courbe
    q = pc.lire(en_np2(dict(p, saturation=-0.75, teinte=1.25, clarte=1)))
    verif(q['format'] == 'NP2' and q['cartes']['base'] == 'Standard' and len(q['courbe']['lut']) == 257, 'NP2 base et courbe')
    verif(abs(q['cartes']['saturation'] + 0.75) < 1e-9 and abs(q['cartes']['teinte'] - 1.25) < 1e-9 and q['cartes']['clarte'] == 1, 'quarts de point dans le NP2')
    verif(quart(0.6) == 0.5 and quart(9) == 3 and quart(-9) == -3, 'arrondi au quart de point et bornes')
    verif(pc.lire(en_np2(depuis_v1('hp5')))['cartes']['base'] == 'Monochrome', 'NP2 mono')
    v = _variables(p)
    verif(len(v) == 11 and len(_variables(depuis_v1('hp5'))) == 9 and _avec(p, v)['saturation'] == p['saturation'], 'variables d’ajustement')
    # 2. courbe : monotone, bornée, écart appliqué
    rng = np.random.default_rng(1)
    for _ in range(50):
        d = rng.uniform(-80, 80, 9)
        l = courbe_decalee(p['lut0'], d)
        verif(len(l) == 257 and min(l) >= 0 and max(l) <= 32767 and all(b >= a for a, b in zip(l, l[1:])), 'courbe monotone et bornée')
        pc.ecrire_ncp('X', 1, {}, l)   # ne doit pas lever
    q = dict(p, delta=[0, 0, 0, 0, 20, 0, 0, 0, 0])
    verif(abs(courbe_decalee(p['lut0'], q['delta'])[128] - p['lut0'][128] - 20 * 32767 / 255) < 700, 'écart du nœud central')
    # 3. butée
    verif(en_butee(dict(p, delta=[40] + [0] * 8, saturation=3)) != [], 'butée détectée')
    verif(en_butee(p) == [] or 'saturation' not in ' '.join(en_butee(p)), 'pas de butée à tort')
    # 4. recette USB relisible par le module du boîtier
    b = pc.bloc_recette(en_recette_usb(dict(p, delta=[5] * 9)))
    verif(len(b) == 610 and pc.lire_bloc_ptp(b)['base'] == 'Standard', 'bloc USB')
    pm = depuis_v1('hp5')
    verif(pc.lire(en_ncp(pm))['base'] == 'Monochrome', 'NCP mono')
    verif(pc.lire_bloc_ptp(pc.bloc_recette(en_recette_usb(pm)))['filtre'] == 'aucun', 'bloc USB mono')
    # 5. poids et gain
    verif(poids(np.array([0.0, 5.0]), np.array([10.0, 70.0]))[0] > poids(np.array([0.0, 5.0]), np.array([10.0, 70.0]))[1], 'pires blocs réduits')
    A = np.random.default_rng(0).uniform(0.2, 0.8, (500, 3))
    rr = np.random.default_rng(1).uniform(0, 1, 500)
    c = np.array([0.95, 0.02, 0.1])
    B = appliquer_gain(A, rr, c)
    verif(np.allclose(ajuster_gain(A, B, rr), c, atol=0.01), 'gain radial retrouvé')
    # 6. avec NX : un rendu rapide
    if os.path.exists(nx.SAVEPROCESS):
        nef = RACINE / 'images' / 'd750' / '2026-10-test-v1' / 'rangees' / '01-CLASSIC_CHROME_V1.NEF'
        if nef.exists():
            a = nx.rendre(str(nef), None, en_np2(p), 1504)
            b2 = nx.rendre(str(nef), None, en_np2(dict(p, saturation=p['saturation'] + 2)), 1504)
            verif(a.shape[1] == 1504 and 0.05 < a.mean() < 0.95, 'rendu NX plausible')
            verif(np.abs(a - b2).mean() > 1e-3, 'la saturation du NP2 change le rendu NX')
            print('  rendu NX rapide : OK')
    else:
        print('  NX absent : rendu non testé')
    print('self-test', 'OK' if ok else 'ÉCHEC')
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('commande', nargs='?', choices=['ajuster', 'tout'])
    ap.add_argument('recettes', nargs='*')
    ap.add_argument('--sortie', default=str(SORTIE))
    ap.add_argument('--travail', default=str(TRAVAIL))
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test() else 1)
    if not a.commande:
        ap.print_help()
        sys.exit(2)
    noms = list(RECETTES) if a.commande == 'tout' else a.recettes
    banc = Banc(a.travail)
    resume = pathlib.Path(a.sortie).parent / 'resume.json'
    tous = json.loads(resume.read_text(encoding='utf-8')) if resume.exists() else {}
    p1 = resume.parent / 'resume-ncp.json'
    passe1 = json.loads(p1.read_text(encoding='utf-8')) if p1.exists() else {}
    for n in noms:
        tous[n] = ajuster(n, banc, a.sortie, lambda s: print(s, flush=True))
        if n in passe1:
            tous[n]['passe_1_ncp'] = {k: passe1[n].get(k) for k in ('avant', 'apres', 'reglages', 'en_butee', 'rendus', 'fichier')}
        resume.parent.mkdir(parents=True, exist_ok=True)
        resume.write_text(json.dumps(tous, ensure_ascii=False, indent=1), encoding='utf-8')
    print('rendus au total :', banc.rendus, 'durée de rendu', round(banc.temps), 's')


if __name__ == '__main__':
    main()
