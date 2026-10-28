#!/usr/bin/env python3
"""Préréglages du D200 (firmware B 2.01) : quatre entrées d'Optimiser l'image produisent chacune leur rendu JPEG.

Choix de Thomas (octobre 2026) : Normal (0) et Personnalisé (5) gardent le rendu de Nikon ; Moins net (1) → Chrome,
Saturé (2) → Positive, Très saturé (3) → FP4, Portrait (4) → HP5 ; Noir et blanc (6) → Tri-X par le patch de
données d200/patchs/d200-nb-trix.json (d200/outils/d200_nb.py), à combiner avec celui-ci.

Mécanisme : celui des préréglages V1 du D40 (d40/outils/preglages_v1.py), porté. Deux crochets, chacun par simple
changement de la constante d'un `LDI:32 #…,R12 ; CALL @R12` existant (appel sans créneau de délai, instruction
et suite inchangées) ; code et données dans la place libre 0x1765EA-0x17FFFF du secteur 0x170000, que chaque mise
à jour de Nikon programme (24 444 octets de Nikon), et non plus en 0x3FA000 : les secteurs de 8 Ko du haut n'ont
jamais d'octet de Nikon et peuvent être protégés en écriture (d200/recherche/d200-v1-relecture.md, constat 1).

1. preglage_reglages (0xCDFAE, FUN_000cd9a2 : appel de FUN_000cf86a, juste après FUN_000ce4fa qui traduit le
   menu en variables). Pour les 4 entrées, aux conditions ci-dessous, pose netteté _DAT_97be3dd4 = 4 (Moyenne +),
   saturation _DAT_97be3df8 = 1 (Normale), correction des tons _DAT_97be3e08 = 1 (Normale), comme le second
   crochet du D40, puis saute dans FUN_000cf86a (retour direct dans FUN_000cd9a2). Tout le calcul de Nikon en
   découle : jeu 42 E + 7 F + 3 et courbe 7 × groupe + 3 (cran Normale, plus de dépendance à la scène),
   registre de netteté 0x50010054, demi-mot 0x50010056, colonne Normale de la table de saturation (0x5001EC00),
   et la fiche (+0x4C) que FUN_000d93a6 réécrit. La teinte est déjà forcée à 0 par FUN_000ce4fa.
2. preglage_puce (0x5DA28, isp_chargerPuce : dernier appel, FUN_000dcff8 qui rend la table de saturation).
   Appelle FUN_000dcff8, puis, si le préréglage est actif, réécrit dans la puce déjà chargée par Nikon :
     - la matrice caméra (0x50010022, 9 demi-mots) : n° = famille d'éclairage F et espace (sRGB / Adobe) tirés
       du numéro de jeu que Nikon a rangé dans la fiche (+0x422) : jeu = 42 E + 7 F + (6 − K) ;
     - la matrice YCbCr (0x50010034) : BT.601 (Cb = Cr = 0 sur un gris) ;
     - les 4 × 16 secteurs (0x5001E400-0x5001E47F, ordre t1, t2, t3, t4 du D40) ;
     - les trois courbes (0x50018400, 0x5001A400, 0x5001C400) : 4 096 octets du rendu recopiés par
       FUN_0005debe, la fonction de Nikon qui recopie la courbe N&B ;
   et rend la table de saturation de Nikon, que isp_chargerPuce recopie elle-même en 0x5001EC00.
   Rien n'est écrit dans la fiche par ce crochet : la fiche garde les matrices et la courbe de Nikon.
Conditions (les deux crochets) : mode d'Optimiser = (fiche +0x4D & 0x1F) >> 1 dans {1, 2, 3, 4} ; chemin des
matrices en dur de Nikon inactif (_DAT_97be3dcc = 0, comme _DAT_83eb3d3c sur le D40). Crochet 2 en plus :
courbe intégrée (+0x424 < 23), jeu < 294 et d'un espace connu (E = 0, 2, 5, 6). Sinon : rendu de Nikon.

Données (d200/outils/d200_rendus.py, d40/outils/films_nb.py) :
  - Chrome, Positive : recette(nom) (matrice ×512 ajustée pour le D200, YCbCr BT.601, courbe 8 bits, secteurs neutres :
    l'étage du D200 ne se lit pas comme celui du D40, essai d’octobre 2026, voir d200_rendus) ;
    matrice déclinée par famille comme recettes_v1.decliner : M_F = M · N_1⁻¹ · N_F, N = matrices caméra de
    Nikon du groupe de l'entrée (E = 0 pour Moins net, 2 pour Saturé), référence F = 1 ; en Adobe RGB (bit 7 de
    +0x4D, E = 5 ou 6), M_F,adobe = N_F,adobe · N_F⁻¹ · M_F (le passage que Nikon fait lui-même). Un coefficient
    au-delà de BORNE est ramené en rapprochant la déclinaison de la matrice du jour (facteur t noté dans le patch).
  - FP4, HP5 : trois lignes égales = pondération du film × 512 (films_nb.poids, sensibilités camspec du D200),
    somme 512, mêmes pour toutes les familles (comme le N&B de Nikon et le patch Tri-X) ; secteurs neutres ;
    courbe = films_nb.courbe (construction de d200_nb.table_film, sans le facteur k).

  d200_preglages.py construire            d200/patchs/d200-preglages.json (format de d40/patch.py, "firmware": "D200B")
  d200_preglages.py build [--sortie DIR]  JSON combiné Tri-X + noms + préréglages et B2000201.BIN par d40/patch.py,
                                          dans DIR (défaut ~/Library/Caches/d40-emulateur/d200/firmwares/…)
  d200_preglages.py scenario              d200/emulateur/scenarios/preglages.txt (valeurs attendues écrites)
  d200_preglages.py asm                   listing du code ajouté (étiquettes, octets, désassemblage)
  d200_preglages.py --self-test
"""
import argparse
import json
import pathlib
import struct
import subprocess
import sys

sys.dont_write_bytecode = True  # pas de __pycache__ dans le dossier synchronisé
ICI = pathlib.Path(__file__).resolve().parent
PROJET = ICI.parent.parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(PROJET / 'd40'))
sys.path.insert(0, str(PROJET / 'd40' / 'outils'))
sys.path.insert(0, str(PROJET / 'd40' / 'outils'))

import numpy as np  # noqa: E402

import patch as patchpy  # noqa: E402
from preglages_v1 import AsmV1, signe_grandeur, decoder_signe_grandeur  # noqa: E402

BASE = 0x50000
PATCHS = PROJET / 'd200' / 'patchs'
SORTIE_JSON = PATCHS / 'd200-preglages.json'
AUTRES = [PATCHS / 'd200-nb-trix.json', PATCHS / 'd200-noms.json']    # à combiner (pas de chevauchement)
CACHE = pathlib.Path.home() / 'Library/Caches/d40-emulateur/d200'
SCENARIO = PROJET / 'd200' / 'emulateur' / 'scenarios' / 'preglages.txt'

# ---------------------------------------------------------------- adresses (processeur ; offset = adresse − 0x50000)
APPEL_CF86A = 0xCDFAE        # FUN_000cd9a2 : LDI:32 #0xCF86A,R12 ; CALL @R12 (sans créneau), après CALL FUN_000ce4fa
CF86A = 0xCF86A              # FUN_000cf86a : jeu, teinte, netteté, saturation, conversion vers la fiche
APPEL_SATURATION = 0x5DA28   # isp_chargerPuce : LDI:32 #0xDCFF8,R12 ; CALL @R12 (sans créneau), puis copie en 0x5001EC00
DCFF8 = 0xDCFF8              # FUN_000dcff8 : rend 0x97BE7F18 (colonne de saturation choisie)
COPIE_OCTETS = 0x5DEBE       # FUN_0005debe(R4 = octets, R5 = demi-mots, R6 = n) : copie de la courbe N&B
FICHE_POINTEUR = 0x97BE3E4C       # pointeur de la fiche, rangé par FUN_000cd9a2
NETTETE = 0x97BE3DD4         # 0 Auto, 1 Normale, 2 Faible, 3 Moyenne −, 4 Moyenne +, 5 Élevée, 6 Aucune
SATURATION = 0x97BE3DF8      # 0 Auto, 1 Normale, 2 Modérée, 3 Accentuée
TONS = 0x97BE3E08            # 0 Auto, 1 Normale, 2 Moins contrasté, 3 Plus contrasté, ≥ 4 Personnalisée
DCC = 0x97BE3DCC             # ≠ 0 : matrices en dur de Nikon (bit 4 de 0x9798D753, sans écrivain connu)
JEU, COURBE = 0x97BE0A14, 0x97BE0A18
MATRICE_CAM, MATRICE_YCC, SECTEURS = 0x50010022, 0x50010034, 0x5001E400
REG_COURBES = (0x50018400, 0x5001A400, 0x5001C400)
FICHE_MODE, FICHE_JEU, FICHE_COURBE = 0x4D, 0x422, 0x424
TBL_JEUX = 0x384BF8          # 294 jeux × 24 demi-mots (caméra 9, YCbCr 9, 6 autres)
TBL_COURBES = 0x3884D8       # 21 courbes × 256 seuils
N_JEUX = 294

CODE = 0x177000              # place libre 0x1765EA-0x17FFFF, secteur 0x170000 programmé par Nikon (relecture, constat 1)
TABLES = 0x177200
EMPLACEMENTS = 0x177400
FIN_LIBRE = 0x180000         # fin du secteur 0x170000
# Plages à ne jamais toucher (d200/recherche/d200-firmware-image.md §6), et plages jamais écrites par la mise à jour
INTERDIT = [(0xEFBF0, 0xF0000), (0x9A680, 0x9B14C), (0x54552, 0x54600), (0x15D284, 0x15D484),
            (0x15C72C, 0x15CA64), (0x15387C, 0x153910), (0x15E008, 0x15E108), (0x16C760, 0x16C764),
            (0x16CB18, 0x16CB1C), (0xF0000, 0x120000), (0x1D0000, 0x200000), (0x176600, 0x176700)]

# emplacement : 12 matrices caméra (F 0-5 sRGB, F 0-5 Adobe), YCbCr, secteurs, courbe 4 096 octets
OFF_MAT, OFF_YCC, OFF_SEC, OFF_COURBE = 0x000, 0x0D8, 0x0EA, 0x180
TAILLE = OFF_COURBE + 4096   # 0x1180
NETTETE_RENDUS, SATURATION_RENDUS, TONS_RENDUS = 4, 1, 1
BORNE = 1000                 # marge des matrices (registre : 1 023), comme recettes_v1

# (rendu, mode d'Optimiser, entrée de Nikon, E sRGB de l'entrée, E Adobe)
PREGLAGES = [('chrome', 1, 'Moins net', 0, 5), ('positive', 2, 'Saturé', 2, 6),
             ('fp4', 3, 'Très saturé', 2, 6), ('hp5', 4, 'Portrait', 0, 5)]
NOMS = {'chrome': 'Chrome', 'positive': 'Positive', 'fp4': 'FP4', 'hp5': 'HP5'}
YCC_601 = [77, 150, 29, -43, -85, 128, 128, -107, -21]
NEUTRE_SECTEURS = [256] * 16 + [0] * 16 + [0] * 16 + [256] * 16
# V2 (choix de Thomas en octobre 2026) : couleur « typée » (d200_rendus.recette, variante 'type' : matrice + étage ajustés
# sur les paires d'origine, (Cb, Cr) × 0,8 Chrome, × 1,2 Positive) ; N&B : tirage par film (d200_nb.TIRAGE).
# V1 (flashée en octobre 2026, d200/patchs/d200-v1.json) : VARIANTE = 'v1', VERSION_NB = 1.
VARIANTE, VERSION_NB = 'type', 2


def lire(b, a, n):
    return bytes(b[a - BASE:a - BASE + n])


def remplace(b, adresse, avant, apres, texte):
    assert lire(b, adresse, len(avant)) == avant, (hex(adresse), lire(b, adresse, len(avant)).hex(), avant.hex())
    return {'offset': hex(adresse - BASE), 'avant': {'hex': avant.hex()}, 'apres': {'hex': apres.hex()}, 'texte': texte}


def bloc(b, a, neuf, texte):
    avant = lire(b, a, len(neuf))
    assert avant == b'\xff' * len(neuf), f'place {a:#x} occupée'
    return {'offset': hex(a - BASE), 'avant': {'hex': avant.hex()}, 'apres': {'hex': neuf.hex()}, 'texte': texte}


def plage(p):
    o = int(p['offset'], 16) + BASE
    return o, o + len(bytes.fromhex(p['avant']['hex']) if isinstance(p['avant'], dict) else p['avant'])


# ---------------------------------------------------------------- données des rendus

def jeu_camera(b, jeu):
    return np.array(struct.unpack('>9h', lire(b, TBL_JEUX + 48 * jeu, 18))).reshape(3, 3) / 512


def matrice_nikon(b, E, F):
    """Matrice caméra de Nikon (/512) pour la classe E et la famille F (identique pour les 7 crans)."""
    return jeu_camera(b, 42 * E + 7 * F + 3)


def entiers(m):
    """3×3 (lignes = 1) → entiers ×512, lignes ramenées à 512 (colonne du milieu), comme d200_rendus.entiers."""
    e = np.round(np.asarray(m) * 512).astype(int)
    e[:, 1] += 512 - e.sum(1)
    return e


def decliner(M, b, E0, Ea):
    """12 matrices (F 0-5 sRGB, F 0-5 Adobe) ; t < 1 quand la déclinaison a dû être réduite (|coef| > BORNE)."""
    m = np.asarray(M) / 512
    ref = np.linalg.inv(matrice_nikon(b, E0, 1))
    srgb, adobe, reductions = [], [], {}
    for F in range(6):
        R = ref @ matrice_nikon(b, E0, F)
        t, mf = 1.0, None
        for _ in range(40):
            mf = m @ ((1 - t) * np.eye(3) + t * R)
            if np.abs(entiers(mf)).max() <= BORNE:
                break
            t -= 0.025
        assert np.abs(entiers(mf)).max() <= BORNE, f'famille {F} : matrice hors bornes même sans déclinaison'
        if t < 1:
            reductions[F] = round(t, 3)
        A = matrice_nikon(b, Ea, F) @ np.linalg.inv(matrice_nikon(b, E0, F))
        srgb.append(entiers(mf).ravel().tolist())
        adobe.append(entiers(A @ mf).ravel().tolist())
    return srgb + adobe, reductions


def courbe_film(film, b, version=2):
    """d200_nb.table_film sans le facteur k : 4 096 sorties 8 bits, entrée = gris linéaire (blanc capteur = 1)."""
    import d200_nb
    c, info = d200_nb.courbe_film(film, b, version)
    lut = np.maximum.accumulate(np.round(np.asarray(c) * 255 / 4095).astype(int).clip(0, 255))
    return lut.astype(int).tolist(), info


def rendus(b=None):
    """Les 4 emplacements, dans l'ordre de PREGLAGES : matrices (12 × 9), ycc, secteurs (64), courbe (4 096)."""
    import d200_rendus as dr
    import d200_simulateur as sim
    import films_nb
    import matrices_spectrales as ms
    b = sim.firmware() if b is None else b
    passage = dr.passage_d40_d200()
    cs = ms.lire_camspec(dr.CAMSPEC, 'Nikon D200')
    out = []
    for nom, mode, entree, E0, Ea in PREGLAGES:
        if nom in dr.COULEURS:
            r = dr.recette(nom, passage, b, VARIANTE)
            mats, red = decliner(r['matrice'], b, E0, Ea)
            d = {'matrices': mats, 'ycc': [int(v) for v in np.asarray(r['ycc']).ravel()],
                 'secteurs': [int(v) for v in r['secteurs']], 'courbe': [int(v) for v in r['lut']],
                 'jour': np.asarray(r['matrice']).ravel().tolist(), 'reductions': red,
                 'source': f'd200_rendus.recette({nom!r}, variante {VARIANTE!r}) : '
                           + ('matrice ajustée pour le D200 (d200/recettes/matrices.json), secteurs neutres'
                              if VARIANTE == 'v1' else 'matrice et 16 secteurs ajustés sur les paires d\'origine '
                              f'(d200/recettes/etage-v2.json){", (Cb, Cr) × " + str(dr.TYPE[nom]) if VARIANTE == "type" else ""}')
                           + f', courbe d40/recettes/mesures/{dr.COULEURS[nom]} ; '
                           f'déclinée sur les matrices de Nikon E = {E0} (sRGB) et {Ea} (Adobe)'
                           + (f' ; déclinaison réduite (t) : {red}' if red else '')}
        else:
            w, err = films_nb.poids(nom, cs)
            W = np.round(w * 512).astype(int)
            W[1] += 512 - W.sum()
            lut, info = courbe_film(nom, b, VERSION_NB)
            d = {'matrices': [W.tolist() * 3] * 12, 'ycc': list(YCC_601), 'secteurs': list(NEUTRE_SECTEURS),
                 'courbe': lut, 'jour': W.tolist() * 3, 'reductions': {}, 'poids': W.tolist(),
                 'source': f'films_nb.poids({nom!r}, camspec D200) = {(w / w.sum()).round(3).tolist()} (écart médian '
                           f'{err:.3f}) → {W.tolist()} ×3 ; courbe films_nb.courbe {info}'}
        verifier_rendu(nom, d)
        out.append(d)
    return out


def verifier_rendu(nom, d):
    assert len(d['matrices']) == 12 and all(len(m) == 9 for m in d['matrices']), nom
    for m in d['matrices']:
        assert all(abs(v) <= BORNE for v in m), (nom, m)
        assert all(sum(m[3 * i:3 * i + 3]) == 512 for i in range(3)), (nom, m)
    assert len(d['ycc']) == 9 and sum(d['ycc'][:3]) == 256 and sum(d['ycc'][3:6]) == 0 == sum(d['ycc'][6:]), nom
    assert len(d['secteurs']) == 64 and all(abs(v) <= 511 for v in d['secteurs']), nom
    c = d['courbe']
    assert len(c) == 4096 and all(0 <= v <= 255 for v in c) and all(x <= y for x, y in zip(c, c[1:])), nom


def emplacement_octets(d):
    out = bytearray()
    for m in d['matrices']:
        out += struct.pack('>9H', *(signe_grandeur(v, 0x400) for v in m))
    assert len(out) == OFF_YCC
    out += struct.pack('>9H', *(signe_grandeur(v, 0x200) for v in d['ycc']))
    assert len(out) == OFF_SEC
    out += struct.pack('>64H', *(signe_grandeur(v, 0x200) for v in d['secteurs']))
    out += b'\x00' * (OFF_COURBE - len(out))
    out += bytes(d['courbe'])
    assert len(out) == TAILLE
    return bytes(out)


# ---------------------------------------------------------------- code

def indice_jeu(jeu):
    """Numéro de matrice de l'emplacement pour un jeu de Nikon : F (sRGB, E = 0 ou 2), 6 + F (Adobe, E = 5 ou 6)."""
    E, F = jeu // 42, (jeu % 42) // 7
    return F if E in (0, 2) else 6 + F if E in (5, 6) else 0xFF


def code_crochets():
    s = AsmV1(CODE)
    # preglage_reglages : à la place de FUN_000cf86a dans FUN_000cd9a2 (RP = retour dans FUN_000cd9a2).
    # R0, R1, R2, R12, R13 seulement (libres, convention Fujitsu) ; pas de pile.
    s.label('preglage_reglages')
    s.ldi32(FICHE_POINTEUR, 1)
    s.ld(1, 1)                           # R1 = fiche de prise de vue
    s.ldi8(FICHE_MODE, 13)
    s.ldub13(1, 0)
    s.ldi8(0x1F, 2)
    s.and_(2, 0)
    s.lsr(1, 0)                          # R0 = mode d'Optimiser 0..15
    s.ldi32('tbl_emplacement', 2)
    s.add(0, 2)
    s.ldub(2, 0)                         # R0 = emplacement 0..3, 0xFF = rendu de Nikon
    s.cmpi(4, 0)
    s.b('ge', 'fin_reglages')
    s.ldi32(DCC, 2)                      # matrices en dur de Nikon : on n'y touche pas
    s.ld(2, 2)
    s.cmpi(0, 2)
    s.b('ne', 'fin_reglages')
    s.lsl(2, 0)                          # tbl_reglages : 4 octets par emplacement (netteté, saturation, tons, 0)
    s.ldi32('tbl_reglages', 2)
    s.add(0, 2)
    s.ldub(2, 0)
    s.ldi32(NETTETE, 1)
    s.st(0, 1)
    s.addi(1, 2)
    s.ldub(2, 0)
    s.ldi32(SATURATION, 1)
    s.st(0, 1)
    s.addi(1, 2)
    s.ldub(2, 0)
    s.ldi32(TONS, 1)
    s.st(0, 1)
    s.label('fin_reglages')
    s.ldi32(CF86A, 12)                   # FUN_000cf86a, qui rend directement à FUN_000cd9a2
    s.jmp_r(12)

    # preglage_puce : à la place de FUN_000dcff8 à la fin d'isp_chargerPuce (RP = 0x5DA30). R8 sauvé et rendu
    # (isp_chargerPuce s'en sert ensuite : R8 = 0x50010000), R9-R11 et R14 non touchés, R4 = table de saturation.
    s.label('preglage_puce')
    s.push_rp()
    s.push(8)
    s.appel(DCFF8)                       # R4 = table de saturation de Nikon (0x97BE7F18)
    s.push(4)
    s._w(0x2061)                         # LD @(R14,0x18),R1 : la fiche, rangée par le prologue d'isp_chargerPuce
    s.ldi8(FICHE_MODE, 13)
    s.ldub13(1, 0)
    s.ldi8(0x1F, 2)
    s.and_(2, 0)
    s.lsr(1, 0)
    s.ldi32('tbl_emplacement', 2)
    s.add(0, 2)
    s.ldub(2, 0)                         # R0 = emplacement
    s.cmpi(4, 0)
    s.b('ge', 'fin_puce')
    s.ldi20(FICHE_COURBE, 13)            # courbe intégrée seulement (< 23) : sinon rendu de Nikon
    s.ldub13(1, 2)
    s.ldi8(0x17, 3)
    s.cmp(3, 2)
    s.b('ge', 'fin_puce')
    s.ldi32(DCC, 2)
    s.ld(2, 2)
    s.cmpi(0, 2)
    s.b('ne', 'fin_puce')
    s.ldi20(FICHE_JEU, 13)               # jeu de Nikon pour CETTE photo, rangé dans sa fiche par FUN_000d93a6
    s.lduh13(1, 2)
    s.ldi20(N_JEUX, 3)
    s.cmp(3, 2)
    s.b('nc', 'fin_puce')                # ≥ 294 (N&B : 500) : rendu de Nikon
    s.ldi32('tbl_jeu', 3)
    s.add(2, 3)
    s.ldub(3, 2)                         # R2 = n° de matrice 0..11, 0xFF
    s.ldi8(12, 3)
    s.cmp(3, 2)
    s.b('nc', 'fin_puce')
    s.lsl(2, 0)
    s.ldi32('tbl_base', 3)
    s.add(0, 3)
    s.ld(3, 8)                           # R8 = début de l'emplacement
    s.mov(2, 3)                          # matrice : R8 + 18 n
    s.lsl(4, 3)
    s.lsl(1, 2)
    s.add(2, 3)
    s.add(8, 3)
    s.ldi32(MATRICE_CAM, 5)
    s.copie16(9, 3, 5, 6, 0, 'copie_matrice')
    s.ldi20(OFF_YCC, 3)
    s.add(8, 3)
    s.ldi32(MATRICE_YCC, 5)
    s.copie16(9, 3, 5, 6, 0, 'copie_ycc')
    s.ldi20(OFF_SEC, 3)
    s.add(8, 3)
    s.ldi32(SECTEURS, 5)
    s.copie16(64, 3, 5, 6, 0, 'copie_secteurs')
    for reg in REG_COURBES:              # FUN_0005debe(courbe, registre, 0x1000) : octets → demi-mots
        s.ldi20(OFF_COURBE, 4)
        s.add(8, 4)
        s.ldi32(reg, 5)
        s.ldi20(0x1000, 6)
        s.appel(COPIE_OCTETS)
    s.label('fin_puce')
    s.pop(4)                             # table de saturation de Nikon : isp_chargerPuce la copie en 0x5001EC00
    s.pop(8)
    s.pop_rp()
    s.ret()
    return s


def adresses_tables():
    return {'tbl_emplacement': TABLES + 0x10, 'tbl_reglages': TABLES + 0x20, 'tbl_base': TABLES + 0x30,
            'tbl_jeu': TABLES + 0x40}


def tables_octets():
    emp = bytearray([0xFF] * 16)
    for k, (_, mode, _, _, _) in enumerate(PREGLAGES):
        emp[mode] = k
    t = b'PREGLAGES-D200\0\0' + bytes(emp)
    t += bytes([NETTETE_RENDUS, SATURATION_RENDUS, TONS_RENDUS, 0]) * len(PREGLAGES)
    t += b''.join(struct.pack('>I', EMPLACEMENTS + k * TAILLE) for k in range(len(PREGLAGES)))
    t += bytes(indice_jeu(j) for j in range(N_JEUX))
    return t


def assembler():
    s = code_crochets()
    s.labels.update(adresses_tables())
    return s, s.octets()


def instructions(code):
    """Adresses des instructions du code ajouté (LDI:32 = 6 octets, LDI:20 = 4, les autres 2 : seules formes émises)."""
    i, out = 0, []
    while i < len(code):
        m = struct.unpack('>H', code[i:i + 2])[0]
        out.append((CODE + i, m))
        i += 6 if (m & 0xFFF0) == 0x9F80 else 4 if (m & 0xFF00) == 0x9B00 else 2
    assert i == len(code)
    return out


def formes_retardees(code):
    """Instructions à créneau de délai (JMP:D, CALL:D, RET:D, Bcc:D) : il ne doit y en avoir aucune."""
    return [(hex(a), hex(m)) for a, m in instructions(code)
            if (m & 0xFFF0) in (0x9F00, 0x9F10) or m == 0x9F20 or (m & 0xF000) == 0xF000 or (m & 0xF800) == 0xD800]


# ---------------------------------------------------------------- patchs

def construire_patchs(b, donnees=None):
    s, code = assembler()
    assert CODE + len(code) <= TABLES, f'code de {len(code)} octets'
    tab = tables_octets()
    assert TABLES + len(tab) <= EMPLACEMENTS
    assert EMPLACEMENTS + len(PREGLAGES) * TAILLE <= FIN_LIBRE
    donnees = rendus(b) if donnees is None else donnees
    patchs = [
        remplace(b, APPEL_CF86A, bytes.fromhex('9f8c000cf86a'), bytes.fromhex('9f8c') + struct.pack('>I', s.labels['preglage_reglages']),
                 f'FUN_000cd9a2 : LDI:32 #0xCF86A (FUN_000cf86a) → #{s.labels["preglage_reglages"]:#x} (preglage_reglages : '
                 'netteté Moyenne +, saturation Normale, tons Normale pour les 4 rendus), CALL @R12 sans créneau, inchangé'),
        remplace(b, APPEL_SATURATION, bytes.fromhex('9f8c000dcff8'), bytes.fromhex('9f8c') + struct.pack('>I', s.labels['preglage_puce']),
                 f'isp_chargerPuce : LDI:32 #0xDCFF8 (FUN_000dcff8) → #{s.labels["preglage_puce"]:#x} (preglage_puce : '
                 'matrice, YCbCr, secteurs et courbes du rendu), CALL @R12 sans créneau, inchangé'),
        bloc(b, CODE, code, f'preglage_reglages et preglage_puce ({len(code)} octets)'),
        bloc(b, TABLES, tab, 'tables : signature, mode d\'Optimiser → emplacement, netteté/saturation/tons, adresses des '
                             '4 emplacements, jeu de Nikon (0-293) → n° de matrice (F, F + 6 en Adobe)'),
    ]
    for k, ((nom, mode, entree, E0, Ea), d) in enumerate(zip(PREGLAGES, donnees)):
        patchs.append(bloc(b, EMPLACEMENTS + k * TAILLE, emplacement_octets(d),
                           f'emplacement {k} « {NOMS[nom]} » (Optimiser = {mode}, ex-{entree}) : 12 matrices '
                           f'(F 0-5 sRGB, F 0-5 Adobe), YCbCr, secteurs, courbe 4 096 octets ; source {d["source"]}'))
    for p in patchs:
        a0, a1 = plage(p)
        assert not any(a0 < z1 and z0 < a1 for z0, z1 in INTERDIT), f'patch dans une zone interdite : {a0:#x}'
    return patchs, donnees


def charger_patchs(chemin):
    return json.loads(pathlib.Path(chemin).read_text(encoding='utf-8'))['patchs']


def sans_chevauchement(listes):
    plages = sorted((plage(p) + (n,)) for n, l in listes.items() for p in l)
    for (a0, a1, n0), (b0, b1, n1) in zip(plages, plages[1:]):
        assert a1 <= b0, f'chevauchement {n0} {a0:#x}-{a1:#x} et {n1} {b0:#x}-{b1:#x}'


def construire(ecrire=True):
    orig = bytes(patchpy.charger_original('D200B'))
    patchs, donnees = construire_patchs(orig)
    autres = {p.stem: charger_patchs(p) for p in AUTRES}
    sans_chevauchement({'d200-preglages': patchs, **autres})
    patchpy.appliquer(bytearray(orig), patchs + sum(autres.values(), []))   # octets d'origine vérifiés
    doc = {'firmware': 'D200B',
           'description': 'D200 B 2.01, préréglages (d200/outils/d200_preglages.py) : Moins net → Chrome, Saturé → Positive, '
                          'Très saturé → FP4, Portrait → HP5 ; crochets 0xCDFAE et 0x5DA28, code et données à '
                          f'{CODE:#x}-{EMPLACEMENTS + len(PREGLAGES) * TAILLE:#x}. Netteté Moyenne +, saturation et tons '
                          f'Normale. Couleur {VARIANTE}, N&B V{VERSION_NB}. À combiner avec d200-nb-trix.json (et d200-noms.json).',
           'patchs': patchs}
    if ecrire:
        SORTIE_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        n = sum(len(bytes.fromhex(p['apres']['hex'])) for p in patchs)
        print(f'{SORTIE_JSON.relative_to(PROJET)} : {len(patchs)} patchs, {n} octets')
        for (nom, mode, entree, _, _), d in zip(PREGLAGES, donnees):
            print(f'  {mode} {entree:<12} → {NOMS[nom]:<9} {d["source"]}')
    return doc, donnees


def build(sortie=None):
    doc, _ = construire()
    sortie = pathlib.Path(sortie).expanduser() if sortie else CACHE / 'firmwares' / 'd200-preglages-combine'
    assert not str(sortie.resolve()).startswith(str((PROJET / 'd200' / 'build').resolve())), 'jamais dans d200/build/'
    sortie.mkdir(parents=True, exist_ok=True)
    tout = {'firmware': 'D200B',
            'description': 'D200 B 2.01 combiné : Tri-X (d200-nb-trix.json) + noms (d200-noms.json) + préréglages '
                           '(d200-preglages.json). Jamais flashé.',
            'patchs': sum((charger_patchs(p) for p in AUTRES), []) + doc['patchs']}
    j = sortie / 'd200-combine.json'
    j.write_text(json.dumps(tout, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    r = subprocess.run([sys.executable, str(PROJET / 'd40/patch.py'), str(j), '--sortie', str(sortie)], capture_output=True, text=True)
    print(r.stdout + r.stderr, end='')
    if r.returncode:
        return r.returncode
    d = (sortie / 'B2000201.BIN').read_bytes()
    assert len(d) == 0x3C0000 and patchpy.crc16_xmodem(d) == 0, 'taille ou CRC faux'
    print('contrôle : taille 0x3C0000, CRC du fichier entier = 0 (comme le vérifie la mise à jour)')
    return 0


# ---------------------------------------------------------------- scénario de l'émulateur

FICHES = 0x97D00000          # une fiche par cas, + 0x1000 × n (RAM sans usage dans le pseudo-C)
REF = 0x97F90000             # registres de référence (0x50010000 : 0x58 octets ; 0x50018400-0x5001F3FF en +0x100)
COURBES_ATTENDUES = 0x97F80000   # courbe attendue de chaque rendu, 4 096 octets, + 0x1000 × emplacement
SAUVE = 0x97F7FF00           # constantes des deux LDI:32 du firmware joué
WB = {'ensoleille': (3, 1), 'incandescent': (1, 0), 'ombre': (6, 2), 'fluo': (2, 4), 'auto': (0, 1)}


def h16(v):
    return f'0x{v & 0xFFFF:04X}'


def scenario(donnees, b):
    L = ['# Préréglages du D200 (d200/outils/d200_preglages.py scenario, ne pas éditer à la main) : registres de la puce pour',
         '# Optimiser = 0 à 6, sur le firmware combiné (Tri-X + noms + préréglages). Valeurs attendues écrites ici depuis',
         '# les données des rendus (d200_rendus.recette, films_nb), converties en signe et module ; références',
         '# « Personnalisé réglé à la main » et « sans crochets » jouées dans le même scénario (constantes d\'origine',
         '# remises en place le temps du passage, puis celles du firmware joué). Joué sur le firmware d\'origine, ce',
         '# scénario doit échouer (code 1) : contre-épreuve de « verifier ».', '',
         'macro temoins',
         'remplir 0x97BE09CC 0x48 0xEE',
         'remplir 0x50010000 0x58 0xEE',
         'remplir 0x50018400 0x7000 0xEE           # courbes, secteurs, tables ISO, saturation (jusqu\'à 0x5001F3FF)',
         'fin',
         'macro sans_crochets                      # constantes de Nikon (sur le firmware d\'origine : rien ne change)',
         f'copier {APPEL_CF86A + 2:#x} {SAUVE:#x} 4',
         f'copier {APPEL_SATURATION + 2:#x} {SAUVE + 4:#x} 4',
         f'poke32 {APPEL_CF86A + 2:#x} {CF86A:#010x}',
         f'poke32 {APPEL_SATURATION + 2:#x} {DCFF8:#010x}',
         'fin',
         'macro avec_crochets                      # constantes du firmware joué',
         f'copier {SAUVE:#x} {APPEL_CF86A + 2:#x} 4',
         f'copier {SAUVE + 4:#x} {APPEL_SATURATION + 2:#x} 4',
         'fin',
         'macro garder                             # registres de la référence',
         f'copier 0x50010000 {REF:#x} 0x58',
         f'copier 0x50018400 {REF + 0x100:#x} 0x7000',
         'fin', '']
    L.append('titre courbes attendues des 4 rendus, posées en RAM libre')
    for k, d in enumerate(donnees):
        a = COURBES_ATTENDUES + 0x1000 * k
        for i in range(0, 4096, 64):
            L.append(f'poke8 {a + i:#x} ' + ' '.join(str(v) for v in d['courbe'][i:i + 64]))
    n = [0]

    def fiche():
        f = FICHES + 0x1000 * n[0]
        n[0] += 1
        return f

    def poser(f, mode, wb, adobe, octet4c=None, couleur=0):
        L.append(f'remplir {f:#x} 0x800 0')
        if octet4c is not None:
            L.append(f'poke8 {f + 0x4C:#x} {octet4c:#04x}')
        L.append(f'poke8 {f + 0x4D:#x} {(mode << 1) | couleur | (0x80 if adobe else 0):#04x}')
        L.append(f'poke8 {f + 0x56:#x} {wb}')

    def attendre_rendu(k, d, slot):
        m = d['matrices'][slot]
        L.append(f'expect16 {MATRICE_CAM:#x} ' + ' '.join(h16(signe_grandeur(v, 0x400)) for v in m) + f'   # {m}')
        L.append(f'expect16 {MATRICE_YCC:#x} ' + ' '.join(h16(signe_grandeur(v, 0x200)) for v in d['ycc']))
        for blk in range(4):
            L.append(f'expect16 {SECTEURS + 0x20 * blk:#x} ' + ' '.join(h16(signe_grandeur(v, 0x200)) for v in d['secteurs'][16 * blk:16 * blk + 16]))
        for reg in REG_COURBES:
            L.append(f'expectdemi {reg:#x} {COURBES_ATTENDUES + 0x1000 * k:#x} 4096')

    def identite(titre, mode, wb, adobe, octet4c=None, couleur=0):
        """Les crochets laissent passer : registres et fiche identiques à ceux de la même fiche sans crochets."""
        L.extend(['', f'titre {titre}', 'jouer sans_crochets', 'jouer temoins'])
        fr = fiche()
        poser(fr, mode, wb, adobe, octet4c, couleur)
        L.extend([f'appel 0x5D616 {fr:#x} 1', f'appel 0x5D716 {fr:#x}', 'jouer garder', 'jouer avec_crochets', 'jouer temoins'])
        f = fiche()
        poser(f, mode, wb, adobe, octet4c, couleur)
        L.extend([f'appel 0x5D616 {f:#x} 1', f'appel 0x5D716 {f:#x}',
                  f'expectegal 0x50010000 {REF:#x} 0x58',
                  f'expectegal 0x50018400 {REF + 0x100:#x} 0x7000      # courbes, secteurs, tables ISO, saturation',
                  f'expectegal {f + 0x300:#x} {fr + 0x300:#x} 0x160     # fiche : matrices, secteurs, jeu, courbe, réglages'])

    def preglage(k, wbnom, adobe, autre=''):
        nom, mode, entree, E0, Ea = PREGLAGES[k]
        d = donnees[k]
        wb, F = WB[wbnom]
        E = Ea if adobe else E0
        jeu, courbe = 42 * E + 7 * F + 3, 7 * (0 if E0 == 0 else 2) + 3
        slot = F + (6 if adobe else 0)
        couleur = 0x40 if E0 == 2 else 0
        L.extend(['', f'titre Optimiser = {mode} ({entree}) → {NOMS[nom]}, balance {wbnom} (F = {F}), '
                      f'{"Adobe RGB" if adobe else "sRGB"} : jeu {jeu}, courbe {courbe}, matrice n° {slot}{autre}',
                  '# référence : Personnalisé réglé à la main (netteté Moyenne +, tons Normale, saturation Normale, '
                  f'mode couleur {"III" if E0 == 2 else "I"}), sans crochets',
                  'jouer sans_crochets', 'jouer temoins'])
        fr = fiche()
        poser(fr, 5, wb, adobe, 0x85, couleur)
        L.extend([f'appel 0x5D616 {fr:#x} 1', f'expect32 {JEU:#x} {jeu} {courbe}', f'appel 0x5D716 {fr:#x}',
                  'jouer garder', 'jouer avec_crochets', 'jouer temoins'])
        f = fiche()
        poser(f, mode, wb, adobe)
        L.extend([f'appel 0x5D616 {f:#x} 1',
                  f'expect32 {NETTETE:#x} {NETTETE_RENDUS}                # netteté Moyenne +',
                  f'expect32 {SATURATION:#x} {SATURATION_RENDUS}                # saturation Normale',
                  f'expect32 {TONS:#x} {TONS_RENDUS}                # tons Normale',
                  f'expect32 {JEU:#x} {jeu} {courbe}',
                  f'expect8 {f + 0x4C:#x} 0x85               # fiche (+0x4C) : netteté 4, tons 1, saturation 1',
                  f'expectconv {f + 0x33C:#x} {TBL_JEUX + 48 * jeu:#x} 9 2 0x400   # la fiche garde la matrice de Nikon',
                  f'appel 0x5D716 {f:#x}'])
        attendre_rendu(k, d, slot)
        L.extend([f'expectegal 0x50010000 {REF:#x} 0x22                 # avant la matrice caméra : comme la référence',
                  f'expectegal 0x50010046 {REF + 0x46:#x} 0x12          # dont netteté (0x50010054) et 0x50010056',
                  f'expectegal 0x5001E600 {REF + 0x100 + 0x6200:#x} 0xE00      # tables ISO et saturation (0x5001EC00)'])
        return f

    # 1. les 4 rendus, deux familles, sRGB
    for k in range(4):
        for wbnom in ('ensoleille', 'incandescent'):
            preglage(k, wbnom, False)
    # 2. autres familles, Adobe RGB, balance auto
    preglage(0, 'ombre', False)
    preglage(1, 'fluo', False, ' (déclinaison réduite)' if 4 in donnees[1]['reductions'] else '')
    preglage(2, 'ombre', False)
    preglage(0, 'ensoleille', True)
    preglage(1, 'incandescent', True)
    preglage(3, 'ensoleille', True)
    preglage(0, 'auto', False, ', fiche à zéro')
    # 3. Normal, Personnalisé, N&B : les crochets laissent tout passer
    for wbnom in ('ensoleille', 'incandescent'):
        wb, F = WB[wbnom]
        identite(f'Normal (Optimiser = 0), balance {wbnom} : identique sans crochets', 0, wb, False)
        identite(f'Personnalisé (Optimiser = 5), réglages de la fiche, balance {wbnom} : identique sans crochets', 5, wb,
                 False, 0x66, 0x40)
        identite(f'Noir et blanc (Optimiser = 6, Tri-X), balance {wbnom} : identique sans crochets', 6, wb, False)
    identite('Normal (Optimiser = 0), Adobe RGB : identique sans crochets', 0, 3, True)
    identite('Personnalisé (Optimiser = 5), Normale, mode I, Adobe RGB : identique sans crochets', 5, 3, True, 0x85, 0)
    # 4. deux photos, deux familles : chaque fiche porte son jeu
    k, d = 0, donnees[0]
    L.extend(['', 'titre deux photos, deux balances : fiches calculées l\'une après l\'autre, puces chargées ensuite',
              'jouer avec_crochets'])
    fa, fb = fiche(), fiche()
    poser(fa, 1, 3, False)
    poser(fb, 1, 1, False)
    L.extend([f'appel 0x5D616 {fa:#x} 1', f'appel 0x5D616 {fb:#x} 1', f'expect16 {fa + FICHE_JEU:#x} 10', f'expect16 {fb + FICHE_JEU:#x} 3',
              'jouer temoins', f'appel 0x5D716 {fa:#x}'])
    attendre_rendu(k, d, 1)
    L.extend(['jouer temoins', f'appel 0x5D716 {fb:#x}'])
    attendre_rendu(k, d, 0)
    # 5. gardes du crochet : jeu hors table, mode II, matrices en dur
    L.extend(['', 'titre jeu hors table (500) puis jeu du mode II (52) dans la fiche : rendu de Nikon tel que la fiche le dit'])
    f = fiche()
    poser(f, 1, 3, False)
    L.extend([f'appel 0x5D616 {f:#x} 1'])
    for jeu in (500, 52):
        L.extend(['jouer temoins', f'poke16 {f + FICHE_JEU:#x} {jeu}', f'appel 0x5D716 {f:#x}',
                  f'expectegal {MATRICE_CAM:#x} {f + 0x33C:#x} 36            # caméra et YCbCr : la fiche',
                  f'expectegal 0x5001E400 {f + 0x39A:#x} 0x80              # secteurs : la fiche',
                  f'expectcourbe 0x50018400 {TBL_COURBES + 0x200 * 3:#x}         # courbe intégrée 3 de Nikon'])
    identite('Moins net, chemin des matrices en dur (bit 4 de 0x9798D753) : identique sans crochets', 1, 3, False)
    i = len(L) - 1
    while not L[i].startswith('jouer sans_crochets'):
        i -= 1
    L.insert(i, 'poke8 0x9798D753 0x10')
    L.extend(['expect32 0x97BE3DCC 1', 'poke8 0x9798D753 0'])
    L.append('')
    return '\n'.join(L)


def ecrire_scenario():
    import d200_simulateur as sim
    b = sim.firmware()
    texte = scenario(rendus(b), b)
    SCENARIO.write_text(texte, encoding='utf-8')
    print(f'{SCENARIO.relative_to(PROJET)} : {texte.count(chr(10)) + 1} lignes')


# ---------------------------------------------------------------- self-test

def self_test():
    for bit in (0x200, 0x400):
        assert all(decoder_signe_grandeur(signe_grandeur(v, bit), bit) == v for v in range(-bit + 1, bit))
    orig = bytes(patchpy.charger_original('D200B'))
    # les deux appels d'origine : LDI:32 puis CALL @R12 (sans créneau), et l'instruction qui suit
    assert lire(orig, APPEL_CF86A - 2, 12).hex() == 'd2a69f8c000cf86a971c9f90'      # CALL ce4fa ; LDI:32 ; CALL @R12 ; LEAVE
    assert lire(orig, APPEL_SATURATION, 10).hex() == '9f8c000dcff8971c9b05'        # LDI:32 ; CALL @R12 ; LDI:20 #0xEC00
    assert lire(orig, DCFF8, 8).hex() == '9f8497be7f189720'                        # LDI:32 #0x97BE7F18,R4 ; RET
    assert lire(orig, 0x5D724, 2).hex() == '206a'                                  # LD @(R14,0x18),R10 : la fiche
    s, code = assembler()
    assert not formes_retardees(code), formes_retardees(code)
    assert b'\x20\x61' in code                                                    # LD @(R14,0x18),R1, comme Nikon
    # tables : mode → emplacement, jeu → matrice
    t = tables_octets()
    assert [t[0x10 + m] for _, m, _, _, _ in PREGLAGES] == [0, 1, 2, 3] and t[0x10] == t[0x15] == t[0x16] == 0xFF
    assert [indice_jeu(j) for j in (3, 10, 11, 13, 87, 94, 52, 126, 213, 220, 255, 262, 293)] == \
           [0, 1, 1, 1, 0, 1, 0xFF, 0xFF, 6, 7, 6, 7, 11]
    import d200_simulateur as sim
    b = sim.firmware()
    donnees = rendus(b)
    import d200_rendus as dr
    for (nom, *_), d in zip(PREGLAGES, donnees):
        if nom in dr.COULEURS:   # lumière du jour, sRGB : exactement la matrice de la recette
            assert d['matrices'][1] == d['jour'] == d['matrices'][5], nom
            assert d['secteurs'] == [int(v) for v in dr.recette(nom, None, b, VARIANTE)['secteurs']]
        else:                    # N&B : trois lignes égales, somme 512, YCbCr BT.601 → Cb = Cr = 0
            assert all(m == d['poids'] * 3 for m in d['matrices']) and sum(d['poids']) == 512
            assert d['secteurs'] == NEUTRE_SECTEURS
    patchs, _ = construire_patchs(orig, donnees)
    autres = {p.stem: charger_patchs(p) for p in AUTRES}
    sans_chevauchement({'d200-preglages': patchs, **autres})
    bp = bytes(patchpy.appliquer(bytearray(orig), patchs + sum(autres.values(), [])))
    assert struct.unpack('>I', lire(bp, APPEL_CF86A + 2, 4))[0] == s.labels['preglage_reglages']
    assert struct.unpack('>I', lire(bp, APPEL_SATURATION + 2, 4))[0] == s.labels['preglage_puce']
    for k, d in enumerate(donnees):
        e = EMPLACEMENTS + k * TAILLE
        assert list(lire(bp, e + OFF_COURBE, 4096)) == d['courbe']
        m = [decoder_signe_grandeur(v, 0x400) for v in struct.unpack('>9H', lire(bp, e + 18 * 7, 18))]
        assert m == d['matrices'][7]
    # rien d'autre que les crochets et la place libre : tables de Nikon (jeux, courbes, secteurs, saturation) intactes
    for a0, a1 in ((TBL_JEUX, TBL_JEUX + 48 * N_JEUX), (TBL_COURBES, TBL_COURBES + 0x200 * 21), (0x38B6C0, 0x396E80),
                   (0x3A62DD, 0x3B22DD)):
        assert lire(bp, a0, a1 - a0) == lire(orig, a0, a1 - a0)
    fin = EMPLACEMENTS + len(PREGLAGES) * TAILLE
    red = {NOMS[n]: d['reductions'] for (n, *_), d in zip(PREGLAGES, donnees) if d['reductions']}
    print(f'self-test OK : crochets 0xCDFAE et 0x5DA28, code {len(code)} octets à {CODE:#x}, tables à {TABLES:#x}, '
          f'4 emplacements de {TAILLE:#x} octets ({EMPLACEMENTS:#x}-{fin:#x}) ; combiné avec Tri-X et noms sans '
          f'chevauchement ; déclinaisons réduites : {red or "aucune"}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['construire', 'build', 'scenario', 'asm'])
    ap.add_argument('--sortie', help='build : dossier du JSON combiné et du firmware (hors d200/build/)')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.action == 'construire':
        construire()
    elif a.action == 'build':
        return build(a.sortie)
    elif a.action == 'scenario':
        ecrire_scenario()
    elif a.action == 'asm':
        s, code = assembler()
        for k, v in sorted(s.labels.items(), key=lambda t: t[1]):
            print(f'{v:#08x} {k}')
        print(code.hex())
        fw = CACHE / 'firmwares' / 'd200-preglages-combine' / 'B2000201.BIN'
        if fw.exists():
            print(f'\ndésassemblage par l\'émulateur ({fw}) :', flush=True)
            subprocess.run([sys.executable, str(PROJET / 'd200' / 'emulateur' / 'd200emu.py'), '--firmware', str(fw),
                            'desassembler', hex(CODE), str(len(instructions(code)))])
        else:
            print('(désassemblage : lancer d’abord « d200_preglages.py build »)')
    else:
        ap.print_help()


if __name__ == '__main__':
    sys.exit(main())
