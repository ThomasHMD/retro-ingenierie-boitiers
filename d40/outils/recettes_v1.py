#!/usr/bin/env python3
"""V1 des préréglages couleur du D40 : écrit recettes/v1/<nom>.json pour Nikon, Hasselblad, Chrome, Positive,
Tri-X et HP5, puis la planche de comparaison.

Format (lu par le code du firmware qui choisit les tables selon le préréglage) :
  matrices : 6 × 9 int (échelle 512, chaque ligne vaut 512), une par emplacement de balance, dans l'ordre des
             tables d'usine du groupe IIIa (n° 12 à 17 de 0x332888) ;
  courbe   : 4 096 int, 0..4095, même échelle que les courbes d'usine décodées (courbes.py ; IIIa Normal = n° 17) ;
  secteurs : 6 × 64 int (t1[16], t2[16], t3[16], t4[16], échelle 256), un jeu par emplacement de balance ;
  delta_e, sources, notes ; pour les 5 préréglages, courbe_sans_epaule (la mesure seule), epaule, seuil_blanc_250_il.

Épaule (pas pour Nikon) : blanc (4095) atteint seulement à la pleine échelle, compression douce dès −1,5 IL ; une
courbe mesurée qui a déjà la sienne est gardée, seul son dernier sixième d'IL monte jusqu'au blanc (voir epaule).

Déclinaison des 6 matrices : les tables d'usine changent d'un emplacement de balance à l'autre (correction
propre à chaque éclairage, choisie par le boîtier). On garde ces écarts : M_n = M_rendu · F_13⁻¹ · F_n, où F_n
est la matrice d'usine IIIa n (12 à 17) et F_13 celle que le simulateur prend pour la lumière du jour (la plus
proche des JPEG du boîtier en moyenne). En lumière du jour (emplacement 13), on obtient donc exactement la
matrice du rendu ; ailleurs, la même correction d'éclairage que Nikon. Pour le noir et blanc, la ligne de
pondération w devient w · F_13⁻¹ · F_n, recopiée sur les trois lignes (sortie grise).

  recettes_v1.py ecrire --cc <cc-etage.json> --pf <pf-etage.json> --hncs <hncs-etage.json> --trix <trix-preset.json>
                        --camspec <camspec.txt> --look <profil du preset Tri-X>.xmp
  recettes_v1.py planche <nef>…          recettes/v1/comparaison.jpg (+ une planche 1080p par NEF)
  recettes_v1.py hautes <nef>…           part de blancs (≥ 250) : JPEG du boîtier, Nikon, préréglages sans / avec épaule
  recettes_v1.py planche-hautes <nef>…   recettes/v1/hautes-lumieres-<nef>.jpg (zone la plus brûlée, capteur saturé en rouge)
  recettes_v1.py sous-exposition <nef>…  recettes/v1/sous-exposition-2-3-IL.jpg (gain 2^(−2/3) sur le RAW, épaule)
  recettes_v1.py --self-test             contrôle des fichiers écrits (format, lignes = 512, bornes des registres :
                                         matrice ≤ 1 000 (registre 1 023), secteurs ≤ 511) + cas qui doivent échouer
"""
import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import films_nb  # noqa: E402
import simulateur as sm  # noqa: E402

ICI = pathlib.Path(__file__).resolve().parent.parent
V1 = ICI / 'recettes' / 'v1'
ORDRE = ['nikon', 'hasselblad', 'chrome', 'positive', 'tri-x', 'hp5']
NOMS = {'nikon': 'Nikon (IIIa d’usine)', 'hasselblad': 'Hasselblad (HNCS)', 'chrome': 'Classic Chrome',
        'positive': 'Positive Film', 'tri-x': 'Tri-X 400', 'hp5': 'HP5 Plus'}
EMPLACEMENTS = range(12, 18)
REF = 13


EPAULE_IL = -1.5


def epaule(C, il=EPAULE_IL, queue_il=1 / 6, tolerance_il=0.1):
    """Épaule de type film : la courbe garde sa forme jusqu'à `il` IL sous la pleine échelle, puis rejoint le blanc
    (4095) seulement à la pleine échelle (entrée 4095), en compression douce dans le domaine des IL :
    S = y0 + (4095 − y0) · (1 − e^(−k t)) / (1 − e^(−k)), t = (IL − il) / (−il) ; valeur et pente raccordées en `il`.
    Une courbe mesurée qui a déjà son épaule (elle atteint 250/255 au plus `tolerance_il` IL avant S) est gardée : seul son
    dernier `queue_il` d'IL monte jusqu'au blanc si elle s'arrête dessous (ajout (4095 − C(1)) · s², valeur et pente
    raccordées). Sinon (courbe qui brûle plus tôt que S, ou qui n'atteint jamais 250/255), S remplace le haut."""
    from scipy.optimize import brentq
    C = np.asarray(C, float)
    v = np.arange(4096) / 4095
    f = lambda u: np.interp(2.0 ** u, v, C)
    y0 = f(il)
    pente = (f(il + 0.05) - f(il - 0.05)) / 0.1 * (-il)  # par unité de t
    A = 4095 - y0
    m = pente / A
    g = lambda k: (k / (1 - np.exp(-k)) if abs(k) > 1e-9 else 1.0) - m
    k = brentq(g, -30, 30) if g(-30) < 0 < g(30) else (30 if m > 1 else -30)
    u = np.log2(np.maximum(v, 1e-9))
    tt = np.clip((u - il) / (-il), 0, 1)
    sh = y0 + A * (np.expm1(-k * tt) / np.expm1(-k) if abs(k) > 1e-9 else tt)
    sc, ss = seuil_blanc_il(C), seuil_blanc_il(sh)
    if sc is not None and sc >= ss - tolerance_il:  # la mesure a déjà son épaule
        vq = 2.0 ** -queue_il
        sh = C + (4095 - C[-1]) * np.clip((v - vq) / (1 - vq), 0, 1) ** 2
    out = np.where(v > 2.0 ** il, sh, C)
    out = np.maximum.accumulate(np.clip(np.round(out), 0, 4095)).astype(int)
    out[-1] = 4095
    return out


def seuil_blanc_il(C, seuil=250 / 255):
    """Entrée (en IL sous la pleine échelle) à partir de laquelle la courbe rend ≥ seuil."""
    C = np.asarray(C)
    i = int(np.argmax(C >= seuil * 4095)) if (C >= seuil * 4095).any() else None
    return None if i is None else round(float(np.log2(max(i, 1) / 4095)), 2)


def entiers(m):
    """Matrice (lignes = 1) → 9 int à l'échelle 512, chaque ligne ramenée à 512 exactement (colonne du milieu)."""
    e = np.round(np.asarray(m) * 512).astype(int)
    e[:, 1] += 512 - e.sum(1)
    assert np.abs(e).max() < 32768
    return e.ravel().tolist()


def decliner(M, F):
    return [entiers(np.asarray(M) @ np.linalg.inv(F[REF]) @ F[n]) for n in EMPLACEMENTS]


def ecrire(cc, pf, hncs, trix, camspec, look):
    b = sm.firmware()
    F, cs = sm.tables(b)
    jeux = sm.jeux_secteurs(b)
    c17 = [int(v) for v in cs[17]]
    V1.mkdir(parents=True, exist_ok=True)
    rec = {'nikon': {'matrices': [entiers(F[n]) for n in EMPLACEMENTS], 'courbe': c17,
                     'secteurs': [jeux[n] for n in EMPLACEMENTS],
                     'delta_e': {'simulateur_vs_jpeg_boitier': 'ΔE2000 médian 0,9 à 2,8 sur 12 NEF en IIIa (README, Simulateur)'},
                     'sources': ['Firmware D40 B 1.11 : matrices IIIa n° 12 à 17 (0x332888), courbe n° 17 (IIIa, tons Normal), '
                                 'jeux de secteurs 12 à 17 (0x331E0E, neutres en usine)'],
                     'notes': 'Tables d’usine du mode IIIa, inchangées.'}}
    mesures = {'hasselblad': (hncs, 'recettes/mesures/hncs.json : 132 images du X2D II 100C (33 paires RAW+JPEG, 99 RAW avec aperçu intégré)'),
               'chrome': (cc, 'recettes/mesures/classic-chrome.json : 13 paires RAW+JPEG du X-T4 (une séance)'),
               'positive': (pf, 'recettes/mesures/positive-film.json : 40 paires RAW+JPEG du Ricoh GR III (DR Off)')}
    for nom, (chemin, src) in mesures.items():
        m = json.loads(pathlib.Path(chemin).read_text())
        courbe = films_nb.courbe_d40(m['courbe'], c17)
        rec[nom] = {'matrices': decliner(m['matrice_D40'], F), 'courbe': courbe.tolist(),
                    'secteurs': [list(map(int, m['secteurs']))] * 6,
                    'delta_e': {'ajustement_paires_dE2000': m['dE2000'], 'transfert_colorchecker_D40_dE2000': m['transfert_colorchecker_dE2000'],
                                'lecture': '« avant » = matrice + courbe seules, « après » = avec l’étage à 16 secteurs ; '
                                           'tenu à part = 1 image sur 4, jamais vue par l’ajustement (seul son gain d’exposition y est ajusté)'
                                           + (f' ; ajustement contraint : |coefficient| ≤ {m["borne_matrice"]:.0f}/512 sur les 6 matrices '
                                              'déclinées (registre de la puce : 1 023)' if m.get('borne_matrice') else '')},
                    'sources': [src, 'Ajustement : outils/rendus.py etage (matrice, courbe, 16 secteurs, gain par image, voisins lissés)',
                                'Transfert au D40 : sensibilités spectrales camspec (Jiang et al. 2013, EPFL, CC BY-NC-SA)',
                                'Étage à 16 secteurs : sondes 1 et 2 (README, V1 : rendus)'],
                    'notes': 'Courbe étirée en entrée pour qu’un gris rendu 118/255 par la courbe IIIa Normal garde ce rendu '
                             '(même exposition que le D40). Teinte du blanc du rendu non transportée (lignes = 512).'}
    # Tri-X : preset acheté, vérifié sur les exports de Thomas
    t = json.loads(pathlib.Path(trix).read_text())
    w_srgb, (xd, diag), _ = films_nb.melange_look(look)
    courbe_tx = films_nb.courbe_d40(t['courbe_livree'], c17)
    w = np.asarray(t['poids_D40'])
    sens = films_nb.ms.lire_camspec(camspec)
    w_fiche, e_fiche = films_nb.poids('trix', sens)
    rec['tri-x'] = {'matrices': [entiers(np.tile(r[:1], (3, 1))) for r in
                                 [np.atleast_2d(w @ np.linalg.inv(F[REF]) @ F[n]) for n in EMPLACEMENTS]],
                    'courbe': np.maximum.accumulate(courbe_tx).tolist(), 'secteurs': [[0] * 64] * 6,
                    'delta_e': {'paires_preset_dE2000': {'melange_du_profil_courbe_ajustee': t['dE2000_melange_du_profil'],
                                                           'melange_libre_courbe_ajustee': t['dE2000_melange_libre']},
                                'lecture': 'Exports JPEG de Thomas développés avec le preset Tri-X (16 paires RAW + JPEG, '
                                           '645D, D750, X2D, GR III), gain d’exposition par image. Courbe livrée : '
                                           + json.dumps(t['dE2000_courbe_livree']) + ' ; diagonale du profil ∘ courbe IIIa seule : '
                                           + json.dumps(t['dE2000_courbe_composee']) + ' (ombres trop bouchées) ; courbe IIIa sans le preset : '
                                           + json.dumps(t['dE2000_courbe_IIIa_sans_preset'])},
                    'ombres': {'exports_preset_pct_pixels_sous_2_et_10_pourcent': t['exports_pct_pixels_sous_2_et_10_pourcent'],
                               'lecture': 'Mêmes RAW passés par la recette : 1,2 % et 8,2 % (médianes), contre 4,7 % et 13,2 % avec la seule '
                                          'composition diagonale ∘ courbe IIIa (corrigé en octobre 2026).'},
                    'poids_D40_RGB': w.round(4).tolist(),
                    'controle_fiche_kodak': {'poids_D40_RGB': w_fiche.round(4).tolist(), 'ecart_median_relatif': round(e_fiche, 3),
                                             'lecture': 'La fiche Kodak (sensibilité par énergie) donne un film bien plus sensible au bleu que le preset acheté.'},
                    'sources': ['Preset Tri-X acheté (profil Look de Lightroom), un preset que l’auteur aimait beaucoup : on imite son rendu pour un usage très particulier, aucun fichier ni code n’en est redistribué. '
                                'Rien du contenu brut du profil n’est recopié : seulement le mélange de canaux qui en est déduit '
                                f'(sRGB linéaire {[round(v, 3) for v in w_srgb]}) et sa courbe composée avec celle du D40.',
                                'Vérification : exports JPEG de Thomas (catalogue Lightroom, champ Look = le preset Tri-X), outils/films_nb.py paires',
                                'Contrôle : Kodak Professional Tri-X 320 et 400, fiche F-4017 (octobre 2021)'],
                    'notes': 'Noir et blanc par la matrice seule (trois lignes identiques) et l’étage à zéro (t1..t4 = 0 : '
                             'chroma nulle). Courbe : au-dessus de 0,25 (signal linéaire, blanc = 1), diagonale du preset acheté '
                             'appliquée à la courbe IIIa Normal ; sous 0,12, courbe lue sur les histogrammes des exports (les ombres '
                             'que Lightroom et Thomas ouvrent) ; raccord entre les deux ; gris rendu 118/255 comme le D40.'}
    w_hp5, e_hp5 = films_nb.poids('hp5', sens)
    c_hp5, info = films_nb.courbe('hp5', c17)
    rec['hp5'] = {'matrices': [entiers(np.tile(np.atleast_2d(w_hp5 @ np.linalg.inv(F[REF]) @ F[n]), (3, 1))) for n in EMPLACEMENTS],
                  'courbe': c_hp5.tolist(), 'secteurs': [[0] * 64] * 6,
                  'delta_e': {'ajustement_spectral_ecart_median_relatif': round(e_hp5, 3),
                              'lecture': 'Pas de cible mesurée (aucun preset HP5, pas de paires) : écart relatif médian entre '
                                         'la réponse du film et sa reconstitution par le RGB du D40, sur 624 réflectances (ColorChecker + spectres lisses).'},
                  'poids_D40_RGB': w_hp5.round(4).tolist(), 'tirage': info,
                  'sources': ['Ilford HP5 Plus, fiche technique Harman (2010) : spectrogramme au tungstène 2 850 K, courbe caractéristique '
                              '(Ilfotec HC 1+31, 6 min 30, 20 °C)', 'Sensibilités du D40 : camspec (Jiang et al. 2013)',
                              'Tirage : papier grade 2 (ISO 6846, R 1,10), Dmin 0,05, Dmax 2,10 ; outils/films_nb.py'],
                  'notes': 'Lecture du spectrogramme incertaine (hauteur prise comme réponse linéaire au tungstène, puis divisée par '
                           'le corps noir à 2 850 K) : film très sensible au bleu, ciels clairs, peaux et verts plus sombres.'}
    import re
    import rendus
    dossier = lambda s: re.search(r'\((/[^)]*)\)', s).group(1)
    for nom in ORDRE[1:]:  # épaule pour les 5 préréglages, pas pour Nikon
        rec[nom]['courbe_sans_epaule'] = rec[nom]['courbe']
        rec[nom]['courbe'] = epaule(rec[nom]['courbe']).tolist()
        rec[nom]['seuil_blanc_250_il'] = {'sans_epaule': seuil_blanc_il(rec[nom]['courbe_sans_epaule']),
                                          'avec_epaule': seuil_blanc_il(rec[nom]['courbe'])}
        cs_ = {'sans_epaule': rec[nom]['courbe_sans_epaule'], 'avec_epaule': rec[nom]['courbe']}
        if nom in mesures:
            m = json.loads(pathlib.Path(mesures[nom][0]).read_text())
            rec[nom]['delta_e']['epaule_dE2000'] = rendus.noter_courbes_d40(dossier(m['source']), m, cs_)
        elif nom == 'tri-x':
            rec[nom]['delta_e']['epaule_dE2000'] = films_nb.noter_courbes_paires(dossier(t['source']), look, cs_)
        propre = rec[nom]['seuil_blanc_250_il']['sans_epaule'] is not None and np.array_equal(
            np.asarray(rec[nom]['courbe'][:3648]), np.asarray(rec[nom]['courbe_sans_epaule'][:3648]))
        rec[nom]['epaule'] = (('La courbe mesurée a déjà son épaule (250/255 atteint au plus 0,1 IL avant l’épaule générique) : gardée '
                               'telle quelle, seul le dernier sixième d’IL monte jusqu’au blanc (4095 à la pleine échelle).') if propre else
                              (f'Épaule de type film : courbe mesurée jusqu’à {EPAULE_IL} IL sous la pleine échelle, puis compression '
                               'douce jusqu’au blanc, atteint seulement à la pleine échelle.')) + (
                              ' recettes_v1.epaule ; « courbe_sans_epaule » : la courbe mesurée seule ; seuil_blanc_250_il : entrée, '
                              'en IL sous la pleine échelle, à partir de laquelle la courbe rend 250/255 ou plus.')
    for nom in ORDRE:
        r = rec[nom]
        r = {'nom': NOMS[nom], **r}
        (V1 / f'{nom}.json').write_text(json.dumps(r, ensure_ascii=False, indent=1))
    controler()


# Plages des registres de la puce (preglages_v1.signe_grandeur : grandeur + bit de signe) : matrice 10 bits + signe
# (|coef| ≤ 1 023 à l'échelle 512), secteurs 9 bits + signe (≤ 511). Marge voulue pour les matrices : 1 000.
REGISTRE_MATRICE, MARGE_MATRICE, REGISTRE_SECTEURS = 1023, 1000, 511


def verifier(nom, r):
    """Contrôle d'une recette ; ValueError au premier défaut (avant le build, qui les refuserait)."""
    def exiger(cond, msg):
        if not cond:
            raise ValueError(f'{nom} : {msg}')
    m, c, sec = r['matrices'], r['courbe'], r['secteurs']
    exiger(len(m) == 6 and all(len(x) == 9 for x in m), 'matrices = 6 × 9')
    exiger(all(sum(x[3 * i:3 * i + 3]) == 512 for x in m for i in range(3)), 'chaque ligne de matrice vaut 512')
    cmax = max(abs(v) for x in m for v in x)
    exiger(cmax <= REGISTRE_MATRICE, f'coefficient de matrice {cmax} > {REGISTRE_MATRICE} (registre : 10 bits + signe)')
    exiger(cmax <= MARGE_MATRICE, f'coefficient de matrice {cmax} > {MARGE_MATRICE} (marge sous les 1 023 du registre)')
    exiger(len(c) == 4096 and min(c) >= 0 and max(c) <= 4095, 'courbe = 4 096 valeurs de 0 à 4 095')
    exiger(all(y >= x for x, y in zip(c, c[1:])), 'courbe non croissante')
    if nom != 'nikon':
        exiger(c[-1] == 4095 and c[-200] < 4095, 'épaule (blanc à la pleine échelle seulement)')
        k = int(4095 * 2 ** EPAULE_IL)
        exiger(c[:k - 2] == r['courbe_sans_epaule'][:k - 2], 'la courbe ne change qu’au-dessus de l’épaule')
    exiger(len(sec) == 6 and all(len(x) == 64 for x in sec), 'secteurs = 6 × 64')
    smax = max(abs(v) for x in sec for v in x)
    exiger(smax <= REGISTRE_SECTEURS, f'valeur de secteur {smax} > {REGISTRE_SECTEURS} (registre : 9 bits + signe)')
    exiger('delta_e' in r and bool(r['sources']), 'delta_e et sources')
    if nom in ('tri-x', 'hp5'):
        exiger(all(x[0:3] == x[3:6] == x[6:9] for x in m) and all(set(x) == {0} for x in sec), 'N&B : trois lignes égales, étage à zéro')


def controler():
    for nom in ORDRE:
        verifier(nom, json.loads((V1 / f'{nom}.json').read_text()))
    print('recettes v1 : format OK')


def self_test():
    """Contrôle des fichiers écrits, puis cas fabriqués qui doivent échouer (bornes des registres)."""
    import copy
    controler()
    base = json.loads((V1 / 'nikon.json').read_text())
    cas = {'matrice 1 100': lambda r: r['matrices'][2].__setitem__(slice(0, 3), [1100, -500, -88]),
           'matrice 1 010 (registre oui, marge non)': lambda r: r['matrices'][0].__setitem__(slice(0, 3), [1010, -410, -88]),
           'secteur 600': lambda r: r['secteurs'][4].__setitem__(48 + 13, 600),
           'secteur −512': lambda r: r['secteurs'][1].__setitem__(20, -512)}
    for lib, f in cas.items():
        r = copy.deepcopy(base)
        f(r)
        try:
            verifier('nikon', r)
        except ValueError as e:
            assert ('matrice' in lib) == ('matrice' in str(e)), (lib, e)
            continue
        raise AssertionError(f'cas « {lib} » accepté à tort')
    r = copy.deepcopy(base)
    r['matrices'][0][0:3] = [1000, -400, -88]
    r['secteurs'][0][0] = 511
    verifier('nikon', r)  # aux bornes : accepté
    print('recettes v1 : bornes des registres OK (4 cas refusés, 1 accepté)')


def rendu(nom, cam, emplacement=1, sans_epaule=False):
    mat, courbe, jeu = sm.recette(V1 / f'{nom}.json', emplacement)
    if sans_epaule and nom != 'nikon':
        courbe = json.loads((V1 / f'{nom}.json').read_text())['courbe_sans_epaule']
    return sm.rendre(cam, mat, courbe, 1.0, jeu)


def planche(nefs):
    from PIL import Image, ImageDraw, ImageFont
    import figures_v1 as fg
    lignes = []
    for nef in nefs:
        cam = sm.camera(nef, half=True)
        vues = [(NOMS[n], Image.fromarray((rendu(n, cam) * 255 + .5).astype(np.uint8))) for n in ORDRE]
        # planche 1080p par NEF : 3 × 2
        im = Image.new('RGB', (1920, 1080), 'white')
        d = ImageDraw.Draw(im)
        d.text((40, 18), f'Six préréglages, une photo du D40 ({pathlib.Path(nef).stem})', fill=(20, 20, 20), font=fg.police(38, True))
        cw, ch = 600, 470
        for k, (t, v) in enumerate(vues):
            p = v.copy(); p.thumbnail((cw, ch - 50))
            x, y = 40 + (k % 3) * (cw + 20), 80 + (k // 3) * ch
            im.paste(p, (x + (cw - p.width) // 2, y))
            d.text((x + (cw - d.textlength(t, font=fg.police(30))) / 2, y + p.height + 6), t, fill=(30, 30, 30), font=fg.police(30))
        im.save(V1 / f'comparaison-{pathlib.Path(nef).stem}.jpg', quality=90)
        lignes.append(vues)
    # planche complète : une ligne par NEF, une colonne par préréglage
    cw = 480
    hs = []
    for vues in lignes:
        v = vues[0][1]
        hs.append(int(cw * v.height / v.width))
    H = 90 + sum(h + 16 for h in hs)
    W = 20 + len(ORDRE) * (cw + 12)
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    for k, n in enumerate(ORDRE):
        t = NOMS[n]
        d.text((20 + k * (cw + 12) + (cw - d.textlength(t, font=fg.police(30, True))) / 2, 30), t, fill=(20, 20, 20), font=fg.police(30, True))
    y = 90
    for vues, h in zip(lignes, hs):
        for k, (t, v) in enumerate(vues):
            im.paste(v.resize((cw, h), Image.LANCZOS), (20 + k * (cw + 12), y))
        y += h + 16
    im.save(V1 / 'comparaison.jpg', quality=90)
    print('planche', im.size)


def saturation_raw(nef):
    """Masque, sur la grille demi-taille de LibRaw (non tournée), des pixels dont un photosite du carré 2×2 est saturé."""
    import rawpy
    r = rawpy.imread(str(nef))
    a = r.raw_image_visible.astype(np.float32)
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    sat = (a[:h, :w] >= 0.98 * r.white_level).reshape(h // 2, 2, w // 2, 2).any((1, 3))
    return sat


def hautes_lumieres(nefs, seuil=250 / 255):
    """Part des pixels ≥ 250 sur les trois canaux : JPEG du boîtier (dans le NEF), Nikon simulé, chaque préréglage sans
    et avec épaule ; et, pour les blancs restants avec épaule, la part due à l'écrêtage par la balance seule
    (un canal à 1 après la balance, aucun photosite saturé) et au capteur saturé."""
    from PIL import Image
    res = {}
    for nef in nefs:
        cam = sm.camera(nef, half=True, tourner=False)
        sat = saturation_raw(nef)
        hh, ww = min(sat.shape[0], cam.shape[0]), min(sat.shape[1], cam.shape[1])
        cam, sat = cam[:hh, :ww], sat[:hh, :ww]
        J = np.asarray(sm.jpeg_boitier(nef).resize((ww, hh), Image.BOX), np.float32) / 255
        blanc = lambda a: float(100 * (a >= seuil).all(-1).mean())
        clip_bal = (cam >= 0.999).any(-1) & ~sat
        d = {'raw_sature_pct': round(float(100 * sat.mean()), 1), 'ecretage_balance_seule_pct': round(float(100 * clip_bal.mean()), 1),
             'jpeg_boitier': round(blanc(J), 1), 'nikon_simule': round(blanc(rendu('nikon', cam)), 1)}
        for n in ORDRE[1:]:
            avec = rendu(n, cam)
            b = (avec >= seuil).all(-1)
            d[n] = {'sans_epaule': round(blanc(rendu(n, cam, sans_epaule=True)), 1), 'avec_epaule': round(float(100 * b.mean()), 1),
                    'dont_capteur_sature': round(float(100 * (b & sat).sum() / max(b.sum(), 1)), 0),
                    'dont_balance_seule': round(float(100 * (b & clip_bal).sum() / max(b.sum(), 1)), 0)}
        res[pathlib.Path(nef).stem] = d
    return res


def planche_hautes(nefs):
    """Planche 1080p par NEF sur la zone la plus brûlée : Nikon, Hasselblad sans puis avec épaule ; photosites saturés
    du RAW en rouge, Tri-X sans puis avec épaule. Part de blanc = pixels ≥ 250 sur les trois canaux, dans le cadre."""
    from PIL import Image, ImageDraw
    from scipy.ndimage import uniform_filter
    import figures_v1 as fg
    import rawpy
    for nef in nefs:
        cam = sm.camera(nef, half=True, tourner=False)
        sat = saturation_raw(nef)
        hh, ww = min(sat.shape[0], cam.shape[0]), min(sat.shape[1], cam.shape[1])
        cam, sat = cam[:hh, :ww], sat[:hh, :ww]
        k = {3: 2, 5: 1, 6: -1}.get(rawpy.imread(str(nef)).sizes.flip, 0)
        cam, sat = np.rot90(cam, k).copy(), np.rot90(sat, k).copy()
        nik = rendu('nikon', cam)
        rouge = np.where(sat[..., None], np.array([0.85, 0.1, 0.1], np.float32), nik)
        brule = uniform_filter((nik >= 250 / 255).all(-1).astype(float), size=(nik.shape[0] // 3, nik.shape[1] // 3))
        cy, cx = np.unravel_index(np.argmax(brule), brule.shape)
        h, w = nik.shape[0] // 2, int(nik.shape[0] // 2 * 600 / 430)
        y0, x0 = int(np.clip(cy - h // 2, 0, nik.shape[0] - h)), int(np.clip(cx - w // 2, 0, nik.shape[1] - w))
        cad = lambda a: Image.fromarray((np.clip(a[y0:y0 + h, x0:x0 + w], 0, 1) * 255 + .5).astype(np.uint8)).resize((600, 430), Image.LANCZOS)
        vues = [('Nikon (IIIa d’usine)', nik), ('Hasselblad sans épaule', rendu('hasselblad', cam, sans_epaule=True)),
                ('Hasselblad avec épaule', rendu('hasselblad', cam)), ('Capteur saturé (en rouge)', rouge),
                ('Tri-X sans épaule', rendu('tri-x', cam, sans_epaule=True)), ('Tri-X avec épaule', rendu('tri-x', cam))]
        im = Image.new('RGB', (1920, 1080), 'white')
        d = ImageDraw.Draw(im)
        d.text((40, 16), f'Hautes lumières : une épaule de film ({pathlib.Path(nef).stem}, zone la plus brûlée)', fill=(20, 20, 20), font=fg.police(36, True))
        for k, (t, a) in enumerate(vues):
            x, y = 40 + (k % 3) * 620, 80 + (k // 3) * 495
            im.paste(cad(a), (x, y))
            if a is rouge:
                pc = 100 * sat[y0:y0 + h, x0:x0 + w].mean()
                d.text((x, y + 436), f'{t} : {pc:.0f} % du cadre', fill=(30, 30, 30), font=fg.police(28))
                continue
            pc = 100 * (a[y0:y0 + h, x0:x0 + w] >= 250 / 255).all(-1).mean()
            d.text((x, y + 436), f'{t} : {pc:.0f} % de blanc', fill=(30, 30, 30), font=fg.police(28))
        im.save(V1 / f'hautes-lumieres-{pathlib.Path(nef).stem}.jpg', quality=90)


def planche_sous_exposition(nefs, il=-2 / 3):
    """Planche 1080p : une ligne par NEF, Hasselblad à 0 IL, Hasselblad et Tri-X à `il` (gain 2^il sur le RAW, épaule,
    aucune remontée des tons moyens). Les zones saturées du RAW n'ont pas de détail à rendre : elles deviennent un gris
    clair uni, là où une vraie prise à `il` aurait du détail (sauf au-delà de −il IL au-dessus de la saturation)."""
    from PIL import Image, ImageDraw
    import figures_v1 as fg
    g = 2.0 ** il
    im = Image.new('RGB', (1920, 1080), 'white')
    d = ImageDraw.Draw(im)
    d.text((40, 16), f'Sous-exposer de {abs(il):.2f} IL avec l’épaule, sans remonter les tons moyens'.replace('0.67', '2/3'),
           fill=(20, 20, 20), font=fg.police(36, True))
    hl = (1080 - 80) // len(nefs)
    for i, nef in enumerate(nefs):
        cam = sm.camera(nef, half=True)
        vues = [('Hasselblad, 0 IL', rendu('hasselblad', cam)), ('Hasselblad, −2/3 IL', rendu('hasselblad', cam * g)),
                ('Tri-X, −2/3 IL', rendu('tri-x', cam * g))]
        for k, (t, a) in enumerate(vues):
            p_ = Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8))
            p_.thumbnail((600, hl - 66))
            x, y = 40 + k * 620, 76 + i * hl
            im.paste(p_, (x + (600 - p_.width) // 2, y))
            y_ = a @ np.array([.2126, .7152, .0722], np.float32)
            pc = 100 * (a >= 250 / 255).all(-1).mean()
            d.text((x, y + p_.height + 4), f'{pathlib.Path(nef).stem} · {t}', fill=(20, 20, 20), font=fg.police(26, True))
            d.text((x, y + p_.height + 34), f'médiane {255 * np.median(y_):.0f}/255, blanc (≥ 250) {pc:.0f} %',
                   fill=(40, 40, 40), font=fg.police(24))
    im.save(V1 / 'sous-exposition-2-3-IL.jpg', quality=90)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['ecrire', 'planche', 'hautes', 'planche-hautes', 'sous-exposition'])
    ap.add_argument('args', nargs='*')
    for k in ('cc', 'pf', 'hncs', 'trix', 'camspec', 'look'):
        ap.add_argument('--' + k)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.action == 'ecrire':
        ecrire(a.cc, a.pf, a.hncs, a.trix, a.camspec, a.look)
    elif a.action == 'hautes':
        print(json.dumps(hautes_lumieres(a.args), ensure_ascii=False, indent=1))
    elif a.action == 'planche-hautes':
        planche_hautes(a.args)
    elif a.action == 'sous-exposition':
        planche_sous_exposition(a.args)
    else:
        planche(a.args)


if __name__ == '__main__':
    sys.exit(main())
