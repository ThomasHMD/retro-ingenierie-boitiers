#!/usr/bin/env python3
"""Préréglages V1 du D40 : chaque entrée du menu Préréglage produit son propre rendu JPEG.

Mécanisme (README, « V1 : code des préréglages ») : deux crochets dans le chemin de prise de vue.
Le premier : `FUN_0004b41c` (appelée à chaque photo par `FUN_0004b260`, juste avant le démarrage du moteur
d'image) charge la puce depuis la fiche de prise de vue, puis appelle `tonalite_construire` par
`LDI:32 #0x323C22,R12 ; CALL:D @R12` (0x4B5B2). On ne change que la constante de ce LDI:32 (4 octets,
aucune instruction ajoutée dans un créneau de délai) : elle pointe sur `preglage_crochet`, qui appelle
`tonalite_construire` lui-même, puis, si un préréglage V1 est actif, réécrit dans la puce :
  - la matrice caméra → RGB (0x40010022, 9 valeurs), choisie selon la balance comme Nikon ;
  - la matrice RGB → YCbCr (0x40010034, 9 valeurs) : neutre BT.601 par défaut (saturation 1, celle
    du simulateur), ou la clé `ycc` de la recette ;
  - les 4 × 16 valeurs de l'étage à 16 secteurs (0x4001E400-0x4001E47F), jeu choisi selon la balance ;
et rend l'adresse de SA courbe (4 096 valeurs) au lieu de la table de Nikon : le code de Nikon la copie
lui-même dans les trois tables de la puce (0x40018400, 0x4001A400, 0x4001C400). Les données brutes du NEF
ne sont pas touchées (rien n'est écrit dans la fiche ni dans les tampons RAM de Nikon par ce crochet).

Netteté et saturation (demande de Thomas, octobre 2026 : « que ça pique sans artefacts ») : second
crochet, même technique. `FUN_0031b22e` appelle `modesScene_reglages` par `LDI:32 #0x31ED1A,R12 ;
CALL @R12` (0x31B230) ; la constante pointe sur `preglage_reglages`, qui appelle `modesScene_reglages`
puis, pour un préréglage V1 (mêmes conditions), remplace la netteté `_DAT_83eb3d20` et la saturation
`_DAT_83eb3d44` choisies par le préréglage Nikon recyclé par celles de l'emplacement : par défaut
Moyennement élevée (4) et Normale (1), et la correction des tons `_DAT_83eb3d50` par Normal (1) : courbe
et YCbCr étant remplacées, elle ne fixait plus que le demi-mot 0x40010056 (valeur « Normal » de Nikon,
mêmes calculs). La teinte `_DAT_83eb3d34` n'agit que sur la YCbCr (remplacée) et vaut 0° dans les 5
préréglages recyclés : rien à faire. Nikon et Personnalisé gardent leurs réglages. Tout le reste du
calcul de Nikon en découle : netteté → `FUN_003229ca` (`_DAT_83eb3a84` → registre 0x40010054) ;
saturation → `FUN_003232d8` (table de 1 024 valeurs chargée en 0x4001EC00) ; la fiche suit comme pour
un réglage fait à la main (+0x2C netteté et saturation, +0x46D, +0x48B : mesuré dans l'émulateur). Les
données brutes du NEF ne changent pas ; ses métadonnées disent la netteté et la saturation appliquées.

Préréglage actif = mode d'optimisation de la fiche (`(+0x2D & 0x3F) >> 2`, recopié de 0x83CED225 par
FUN_0004793a) : 1 Hasselblad, 2 Chrome, 3 Positive, 4 Tri-X, 6 HP5 ; 0 Nikon et 5 Personnalisé gardent
le rendu d'usine. Seulement en P, S, A, M (`+0x5A >> 4` < 4) et sur le chemin normal des matrices
(`_DAT_83eb3d3c` = 0). Indice de balance = matrice Nikon de CETTE photo (0 à 17) modulo 6, lue dans la
fiche, +0x4FE : `image_parametres` y range `_DAT_83eb3ab4` juste après `couleur_chargerMatrice`
(FUN_0031b362), dans le bloc fiche +0x498 qu'il pointe par `_DAT_83eb3a48`. Pas la globale elle-même :
`FUN_0004b168` saute `image_parametres` quand la fiche a déjà ses paramètres (rafale, chemins de la
tâche 16), et la globale peut alors venir d'une autre photo (revue critique, octobre 2026).

Recettes : recettes/v1/<nom>.json, clés `matrices` (6 × 9 entiers, échelle 512, ordre de la ROM :
ligne par ligne), `courbe` (4 096 entiers 0..4095, entrée = signal linéaire 12 bits), `secteurs`
(6 × 64 entiers : tables 1 à 4 de 16 secteurs, neutre = 256, 0, 0, 256), facultatif `ycc` (9 entiers,
échelle 256), `nettete` (0 Auto, 1 Normale, 2 Faible, 3 Moyennement faible, 4 Moyennement élevée,
5 Élevée, 6 Aucune ; défaut 4) et `saturation` (0 Auto, 1 Normale, 2 Modérée, 3 Rehaussée ; défaut 1).
Une recette absente est remplacée par des données de test bien visibles (marquées
« test » dans le patch).

  preglages_v1.py construire     patchs/preglages-v1.json, et patchs/v1.json (menu-pipboy + V1)
  preglages_v1.py build          construire, puis build/v1/BD400111.BIN (patch.py : CRC, sha256)
  preglages_v1.py build --sortie DIR   tout (JSON et firmware) dans DIR, sans toucher patchs/ ni build/
  … --recettes DIR               autre dossier de recettes (vide : données de test)
  preglages_v1.py asm            listing du crochet
  preglages_v1.py --self-test
"""
import argparse
import hashlib
import json
import math
import pathlib
import struct
import subprocess
import sys

ICI = pathlib.Path(__file__).resolve().parent
PROJET = ICI.parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(PROJET))

import patch as patchpy  # noqa: E402
import courbes  # noqa: E402
from pipboy import Asm, remplace, mot, PROG_OCTET, SOMBRE_OCTET  # noqa: E402

BASE = 0x40000
PATCHS = PROJET / 'patchs'
RECETTES = PROJET / 'recettes' / 'v1'

# ---------------------------------------------------------------- adresses
APPEL_TONALITE = 0x4B5B2          # LDI:32 #0x323C22,R12 dans FUN_0004b41c, suivi de CALL:D @R12
TONALITE = 0x323C22               # tonalite_construire(fiche) -> table 4 096 × 12 bits (0x83EB586C)
CODE = 0x3F3000                   # place libre après la table des aides de menu-pipboy (0x3F2905)
TABLES = 0x3F3200
EMPLACEMENTS = 0x3F3400
FIN_LIBRE = 0x400000              # planche de glyphes de menu-pipboy
MATRICE_CAM = 0x40010022          # registres de la puce (CARTE §7, recherche §1.2)
MATRICE_YCC = 0x40010034
SECTEURS = 0x4001E400
FICHE_INDICE = 0x4FE              # fiche +0x4FE : copie par image_parametres de _DAT_83eb3ab4 (matrice 0..17)
CHEMIN_SPECIAL = 0x83EB3D3C       # _DAT_83eb3d3c : ≠ 0 → matrices écrites en dur (pas de préréglage)
MATRICES_ROM = 0x332888           # tblMatricesCamRgb, 18 × 9 int16, échelle 512
APPEL_MODES = 0x31B230            # LDI:32 #0x31ED1A,R12 dans FUN_0031b22e, suivi de CALL @R12 (sans créneau)
MODES_SCENE = 0x31ED1A            # modesScene_reglages : netteté, tons, mode couleur, saturation, teinte
FICHE = 0x83EB5864                # _DAT_83eb5864 : pointeur de la fiche de prise de vue
NETTETE = 0x83EB3D20              # _DAT_83eb3d20 (0 Auto … 4 Moyennement élevée … 6 Aucune), lu par FUN_003229ca
SATURATION = 0x83EB3D44           # _DAT_83eb3d44 (0 Auto, 1 Normale, 2 Modérée, 3 Rehaussée), lu par FUN_003232d8
NETTETE_DEFAUT = 4                # Moyennement élevée, pour les 5 rendus (Thomas, octobre 2026)
SATURATION_DEFAUT = 1             # Normale : la saturation du rendu est dans sa matrice et ses secteurs
APPEL_REINIT = 0x135678           # LDI:32 #0x138546,R12 ; CALL @R12 à la fin de la remise à zéro des réglages perso
REINIT_ENVOI = 0x138546           # (FUN_00135570, « Réinitialiser » : Oui) : envoi des réglages perso au A
TONS = 0x83EB3D50                 # _DAT_83eb3d50, correction des tons (0 Auto, 1 Normal, 2 Moins de contraste … 6 Perso)
TONS_NORMAL = 1                   # la courbe et la YCbCr sont remplacées ; reste 0x40010056, fixé à sa valeur « Normal »

# emplacement : 6 matrices, 6 jeux de secteurs, matrice YCbCr, courbe (valeurs au format de la puce)
OFF_MAT, OFF_SEC, OFF_YCC, OFF_COURBE = 0x000, 0x06C, 0x36C, 0x380
TAILLE = OFF_COURBE + 2 * 4096    # 0x2380

# (nom, valeur du mode d'optimisation, noms de fichier acceptés, entrée Nikon recyclée)
PREGLAGES = [
    ('hasselblad', 1, ('hasselblad', 'hncs'), 'Plus doux (SO)'),
    ('chrome', 2, ('chrome', 'classic-chrome'), 'Vif (VI)'),
    ('positive', 3, ('positive', 'positive-film'), 'Très vif (VI+)'),
    ('trix', 4, ('tri-x', 'trix'), 'Portrait (PO)'),
    ('hp5', 6, ('hp5', 'hp5-plus'), 'Noir et blanc (BW)'),
]
YCC_BT601 = [76, 151, 29, -43, -85, 128, 128, -107, -21]   # ligne Y de Nikon, chroma BT.601 (saturation 1)
NEUTRE_SECTEURS = [256] * 16 + [0] * 16 + [0] * 16 + [256] * 16


def signe_grandeur(v, bit):
    """Format des registres de la puce : grandeur + bit de signe (0x400 pour la matrice caméra,
    0x200 pour YCbCr et les secteurs), lu dans tonalite_choisirNumero (FUN_000becc2 = valeur absolue)."""
    v = int(round(v))
    assert abs(v) < bit, f'{v} ne tient pas sur {bit.bit_length() - 1} bits + signe'
    return (bit | -v) if v < 0 else v


def decoder_signe_grandeur(r, bit):
    return -(r & (bit - 1)) if r & bit else r


# ---------------------------------------------------------------- recettes

def matrices_rom(b, i0):
    return [list(struct.unpack('>9h', b[MATRICES_ROM + 18 * i - BASE:][:18])) for i in range(i0, i0 + 6)]


def luminance(m):
    """Les trois lignes = la luminance BT.601 de la matrice m (N&B par la matrice), somme 512."""
    l = [0.299 * m[j] + 0.587 * m[3 + j] + 0.114 * m[6 + j] for j in range(3)]
    r = [int(round(x)) for x in l]
    r[1] += 512 - sum(r)
    return r * 3


def recette_test(nom, b):
    """Données de test bien visibles, tant que la vraie recette n'existe pas."""
    c = courbes.courbes(b)
    ia, iiia = matrices_rom(b, 0), matrices_rom(b, 12)
    if nom == 'hasselblad':
        return {'matrices': ia, 'courbe': [round(4095 * (v / 4095) ** 0.7) for v in c[17]],
                'secteurs': [NEUTRE_SECTEURS] * 6, 'test': 'matrices Ia de Nikon, courbe 17 éclaircie (puissance 0,7)'}
    if nom == 'chrome':
        inv = [-256] * 16 + [0] * 32 + [-256] * 16
        return {'matrices': iiia, 'courbe': c[17], 'secteurs': [inv] * 6,
                'test': 'matrices IIIa, courbe 17, secteurs inversés (chroma × −1 : couleurs complémentaires)'}
    if nom == 'positive':
        return {'matrices': [m[6:9] + m[3:6] + m[0:3] for m in iiia], 'courbe': c[17],
                'secteurs': [NEUTRE_SECTEURS] * 6, 'test': 'matrices IIIa, lignes rouge et bleu échangées'}
    if nom == 'trix':
        return {'matrices': [luminance(m) for m in iiia], 'courbe': c[20], 'secteurs': [NEUTRE_SECTEURS] * 6,
                'test': 'N&B par la matrice (3 lignes = luminance), courbe 20 (plus de contraste)'}
    if nom == 'hp5':
        return {'matrices': [luminance(m) for m in iiia], 'courbe': c[0x32], 'secteurs': [NEUTRE_SECTEURS] * 6,
                'test': 'N&B par la matrice, courbe 0x32 (Normal du jeu N&B de Nikon)'}
    raise KeyError(nom)


def charger_recette(nom, fichiers, b, dossier=RECETTES):
    for f in fichiers:
        p = dossier / f'{f}.json'
        if p.exists():
            r = json.loads(p.read_text(encoding='utf-8'))
            r['source'] = str(p.relative_to(PROJET)) if p.is_relative_to(PROJET) else str(p)
            return r
    r = recette_test(nom, b)
    r['source'] = 'test'
    return r


def verifier_recette(nom, r):
    m, c, s = r['matrices'], r['courbe'], r['secteurs']
    assert len(m) == 6 and all(len(x) == 9 for x in m), f'{nom} : matrices = 6 × 9'
    assert len(c) == 4096, f'{nom} : courbe = 4 096 valeurs'
    assert len(s) == 6 and all(len(x) == 64 for x in s), f'{nom} : secteurs = 6 × 64'
    y = r.get('ycc', YCC_BT601)
    assert len(y) == 9, f'{nom} : ycc = 9 valeurs'
    avert = []
    for k, x in enumerate(m):
        for i in range(3):
            if abs(sum(x[3 * i:3 * i + 3]) - 512) > 8:
                avert.append(f'{nom} : matrice {k}, ligne {i} vaut {sum(x[3 * i:3 * i + 3])} (512 = blanc gardé)')
    assert 0 <= r.get('nettete', NETTETE_DEFAUT) <= 6, f'{nom} : nettete de 0 à 6'
    assert 0 <= r.get('saturation', SATURATION_DEFAUT) <= 3, f'{nom} : saturation de 0 à 3'
    if any(not 0 <= v <= 4095 for v in c):
        avert.append(f'{nom} : courbe hors de 0..4095, bornée')
    return avert


def emplacement_octets(r):
    out = bytearray()
    for x in r['matrices']:
        out += struct.pack('>9H', *(signe_grandeur(v, 0x400) for v in x))
    assert len(out) == OFF_SEC
    for x in r['secteurs']:
        out += struct.pack('>64H', *(signe_grandeur(v, 0x200) for v in x))
    assert len(out) == OFF_YCC
    out += struct.pack('>9H', *(signe_grandeur(v, 0x200) for v in r.get('ycc', YCC_BT601)))
    out += b'\x00' * (OFF_COURBE - len(out))
    out += struct.pack('>4096H', *(max(0, min(4095, int(round(v)))) for v in r['courbe']))
    assert len(out) == TAILLE
    return bytes(out)


# ---------------------------------------------------------------- code

class AsmV1(Asm):
    def add2(self, i, ri):
        assert -16 <= i < 0
        self._w(0xA500 | (i & 0xF) << 4 | ri)

    def copie16(self, n, src, dst, cpt, tmp, etiquette):
        """n demi-mots de @src vers @dst (src et dst avancent ; boucle sans créneau de délai)."""
        self.ldi8(n, cpt)
        self.label(etiquette)
        self.lduh(src, tmp)
        self.sth(tmp, dst)
        self.addi(2, src)
        self.addi(2, dst)
        self.add2(-1, cpt)
        self.b('ne', etiquette)


def code_crochet():
    """preglage_crochet(R4 = fiche) : remplace l'appel de tonalite_construire dans FUN_0004b41c.
    Registres : R0-R7, R12, R13 libres (convention Fujitsu, déjà écrasés par tonalite_construire) ;
    R8 sauvé et rendu ; R4 = table de tonalité rendue (Nikon ou celle du préréglage)."""
    s = AsmV1(CODE)
    s.label('preglage_crochet')
    s.push_rp()
    s.push(8)
    s.mov(4, 8)                          # R8 = fiche de prise de vue
    s.appel(TONALITE)                    # tonalite_construire(fiche) : R4 = table de Nikon
    s.ldi8(0x5A, 13)                     # P, S, A, M seulement (quartet haut de +0x5A < 4)
    s.ldub13(8, 0)
    s.lsr(4, 0)
    s.cmpi(4, 0)
    s.b('ge', 'fin')
    s.ldi32(CHEMIN_SPECIAL, 1)           # matrices en dur de Nikon : on n'y touche pas
    s.ld(1, 1)
    s.cmpi(0, 1)
    s.b('ne', 'fin')
    s.ldi8(0x2D, 13)                     # mode d'optimisation (bits 2-5 de +0x2D)
    s.ldub13(8, 0)
    s.lsr(2, 0)
    s.ldi8(0xF, 1)
    s.and_(1, 0)
    s.ldi32('tbl_emplacement', 1)
    s.add(0, 1)
    s.ldub(1, 0)                         # R0 = emplacement 0..4, 0xFF = rendu Nikon
    s.cmpi(5, 0)
    s.b('ge', 'fin')
    s.ldi20(FICHE_INDICE, 13)            # matrice Nikon de cette photo (0..17), rangée dans sa fiche
    s.ldub13(8, 1)
    s.ldi8(18, 2)
    s.cmp(2, 1)
    s.b('nc', 'fin')                     # ≥ 18 (non signé) : valeur inattendue, rendu Nikon
    s.ldi32('tbl_k', 2)
    s.add(1, 2)
    s.ldub(2, 1)                         # R1 = k (0..5)
    s.ldi32('tbl_base', 2)
    s.lsl(2, 0)
    s.add(0, 2)
    s.ld(2, 2)                           # R2 = début de l'emplacement
    s.mov(1, 3)                          # matrice caméra : R2 + 18 k
    s.lsl(4, 3)
    s.mov(1, 5)
    s.lsl(1, 5)
    s.add(5, 3)
    s.add(2, 3)
    s.ldi32(MATRICE_CAM, 5)
    s.copie16(9, 3, 5, 6, 0, 'copie_matrice')
    s.mov(1, 3)                          # secteurs : R2 + 0x6C + 128 k, 64 valeurs d'un coup
    s.lsl(7, 3)
    s.add(2, 3)
    s.ldi8(OFF_SEC, 5)
    s.add(5, 3)
    s.ldi32(SECTEURS, 5)
    s.copie16(64, 3, 5, 6, 0, 'copie_secteurs')
    s.ldi32(OFF_YCC, 3)                  # matrice YCbCr de l'emplacement
    s.add(2, 3)
    s.ldi32(MATRICE_YCC, 5)
    s.copie16(9, 3, 5, 6, 0, 'copie_ycc')
    s.ldi32(OFF_COURBE, 4)               # courbe de l'emplacement : Nikon la copie dans les 3 tables
    s.add(2, 4)
    s.label('fin')
    s.pop(8)
    s.pop_rp()
    s.ret()

    # preglage_reglages : remplace l'appel de modesScene_reglages dans FUN_0031b22e (qui pose R4 = 1
    # après le retour). R0-R2, R12, R13 utilisés, rien à sauver d'autre que RP.
    s.label('preglage_reglages')
    s.push_rp()
    s.appel(MODES_SCENE)                 # réglages du préréglage Nikon, comme d'origine
    s.ldi32(FICHE, 1)
    s.ld(1, 1)                           # R1 = fiche de prise de vue
    s.ldi8(0x5A, 13)                     # P, S, A, M seulement
    s.ldub13(1, 0)
    s.lsr(4, 0)
    s.cmpi(4, 0)
    s.b('ge', 'fin_reglages')
    s.ldi32(CHEMIN_SPECIAL, 2)           # même condition que preglage_crochet (posée par modesScene_reglages)
    s.ld(2, 2)
    s.cmpi(0, 2)
    s.b('ne', 'fin_reglages')
    s.ldi8(0x2D, 13)                     # mode d'optimisation → emplacement
    s.ldub13(1, 0)
    s.lsr(2, 0)
    s.ldi8(0xF, 2)
    s.and_(2, 0)
    s.ldi32('tbl_emplacement', 2)
    s.add(0, 2)
    s.ldub(2, 0)
    s.cmpi(5, 0)
    s.b('ge', 'fin_reglages')
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
    s.pop_rp()
    s.ret()

    # preglage_reinit : « Réinitialiser » (réglages perso, Oui) remet aussi Programme à Standard et Si trop
    # sombre à sa valeur de départ (0, baisser la vitesse), comme au premier démarrage. Remplace le second
    # appel de 0x138546 de FUN_00135570 (sans créneau) ; R4-R7 passent tels quels, R0 et R12 libres.
    s.label('preglage_reinit')
    s.push_rp()
    s.appel(REINIT_ENVOI)
    s.ldi32(PROG_OCTET, 12)
    s.ldi8(0, 0)
    s.stb(0, 12)
    assert SOMBRE_OCTET == PROG_OCTET + 1
    s.addi(1, 12)
    s.stb(0, 12)
    s.pop_rp()
    s.ret()
    return s


def tables_octets(reglages=None):
    """reglages : [(netteté, saturation)] par emplacement (défaut : Moyennement élevée, Normale) ; tons Normal
    pour tous (TONS_NORMAL), 4e octet nul."""
    reglages = reglages or [(NETTETE_DEFAUT, SATURATION_DEFAUT)] * len(PREGLAGES)
    emp = bytearray([0xFF] * 16)
    for k, (_, mode, _, _) in enumerate(PREGLAGES):
        emp[mode] = k
    t = b'PREGLAGES-V1\0\0\0\0' + bytes(emp)
    t += bytes(i % 6 for i in range(18)) + b'\0\0'
    t += b''.join(struct.pack('>I', EMPLACEMENTS + k * TAILLE) for k in range(len(PREGLAGES)))
    t += b''.join(bytes([n, sat, TONS_NORMAL, 0]) for n, sat in reglages)
    return t


def adresses_tables(code):
    """Les étiquettes tbl_* sont posées dans TABLES ; le code y renvoie par LDI:32."""
    return {'tbl_emplacement': TABLES + 16, 'tbl_k': TABLES + 32, 'tbl_base': TABLES + 52,
            'tbl_reglages': TABLES + 72}


def assembler():
    s = code_crochet()
    s.labels.update(adresses_tables(s))
    return s, s.octets()


# ---------------------------------------------------------------- patchs

def bloc(b, a, neuf, texte):
    off = a - BASE
    avant = b[off:off + len(neuf)]
    assert avant == b'\xff' * len(neuf), f'place {a:#x} occupée'
    return {'offset': hex(off), 'avant': {'hex': avant.hex()}, 'apres': {'hex': neuf.hex()}, 'texte': texte}


def construire_patchs(b, dossier=RECETTES):
    s, code = assembler()
    assert CODE + len(code) <= TABLES
    assert EMPLACEMENTS + len(PREGLAGES) * TAILLE <= FIN_LIBRE
    recettes = [charger_recette(nom, fichiers, b, dossier) for nom, _, fichiers, _ in PREGLAGES]
    reglages = [(r.get('nettete', NETTETE_DEFAUT), r.get('saturation', SATURATION_DEFAUT)) for r in recettes]
    tab = tables_octets(reglages)
    assert TABLES + len(tab) <= EMPLACEMENTS
    patchs = [
        remplace(b, APPEL_TONALITE, bytes.fromhex('9f8c00323c22'), bytes.fromhex('9f8c') + struct.pack('>I', CODE),
                 f'FUN_0004b41c : LDI:32 #0x323C22 (tonalite_construire) → #{CODE:#x} (preglage_crochet), '
                 'instruction et créneau de délai inchangés'),
        remplace(b, APPEL_MODES, bytes.fromhex('9f8c0031ed1a'),
                 bytes.fromhex('9f8c') + struct.pack('>I', s.labels['preglage_reglages']),
                 f'FUN_0031b22e : LDI:32 #0x31ED1A (modesScene_reglages) → #{s.labels["preglage_reglages"]:#x} '
                 '(preglage_reglages : netteté, saturation et tons des 5 rendus), CALL @R12 sans créneau, inchangé'),
        remplace(b, APPEL_REINIT, bytes.fromhex('9f8c00138546'),
                 bytes.fromhex('9f8c') + struct.pack('>I', s.labels['preglage_reinit']),
                 f'FUN_00135570 (Réinitialiser) : LDI:32 #0x138546 → #{s.labels["preglage_reinit"]:#x} (preglage_reinit : '
                 'Programme et Si trop sombre remis à 0), CALL @R12 sans créneau, inchangé'),
        bloc(b, CODE, code, f'preglage_crochet, preglage_reglages et preglage_reinit ({len(code)} octets) : matrice, YCbCr, secteurs '
                            'et courbe du préréglage actif ; sa netteté, sa saturation, tons Normal'),
        bloc(b, TABLES, tab, 'tables du crochet : signature, mode d\'optimisation → emplacement, indice → balance, '
                             'adresses des 5 emplacements, netteté, saturation et tons de chacun'),
    ]
    sources, avert = {}, []
    for k, ((nom, mode, fichiers, nikon), r) in enumerate(zip(PREGLAGES, recettes)):
        avert += verifier_recette(nom, r)
        sources[nom] = r['source'] if r['source'] != 'test' else 'test : ' + r['test']
        patchs.append(bloc(b, EMPLACEMENTS + k * TAILLE, emplacement_octets(r),
                           f'emplacement {k} « {nom} » (mode {mode}, ex-{nikon}) : 6 matrices, 6 jeux de secteurs, '
                           f'YCbCr, courbe ; netteté {reglages[k][0]}, saturation {reglages[k][1]} ; '
                           f'source {sources[nom]}'))
    return patchs, sources, avert


def construire(ecrire=True, dossier=RECETTES, sortie=None):
    """sortie : dossier où écrire les JSON (défaut patchs/)."""
    cible = pathlib.Path(sortie) if sortie else PATCHS
    orig = bytes(patchpy.charger_original())
    patchs, sources, avert = construire_patchs(orig, dossier)
    pip = json.loads((PATCHS / 'menu-pipboy.json').read_text(encoding='utf-8'))['patchs']
    tout = pip + patchs
    patchpy.appliquer(bytearray(orig), tout)       # ni chevauchement ni octet d'origine faux
    doc_v1 = {'description': 'Préréglages V1 (outils/preglages_v1.py) : crochet dans FUN_0004b41c, 5 rendus '
                             '(matrices par balance, courbe, secteurs, YCbCr). Sources : '
                             + ' ; '.join(f'{n} = {s}' for n, s in sources.items()), 'patchs': patchs}
    doc_tout = {'description': 'V1 : menu Pip-Boy (menu-pipboy.json) + préréglages V1 (preglages-v1.json).',
                'patchs': tout}
    for a in avert:
        print('attention :', a)
    if ecrire:
        for nom, doc in (('preglages-v1', doc_v1), ('v1', doc_tout)):
            cible.mkdir(parents=True, exist_ok=True)
            (cible / f'{nom}.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            print(f'{cible / nom}.json : {len(doc["patchs"])} patchs')
        for n, s in sources.items():
            print(f'  {n:<11} {s}')
    return doc_v1, doc_tout


def build(sortie=None, dossier=RECETTES):
    """sortie : dossier unique pour les JSON et le firmware (défaut : patchs/ et build/v1/)."""
    construire(dossier=dossier, sortie=sortie)
    json_v1 = (pathlib.Path(sortie) if sortie else PATCHS) / 'v1.json'
    sortie = pathlib.Path(sortie) if sortie else PROJET / 'build' / 'v1'
    r = subprocess.run([sys.executable, str(PROJET / 'patch.py'), str(json_v1), '--sortie', str(sortie)],
                       capture_output=True, text=True)
    print(r.stdout + r.stderr, end='')
    if r.returncode:
        return r.returncode
    f = sortie / 'BD400111.BIN'
    d = f.read_bytes()
    assert len(d) == 0x3D0000 and patchpy.crc16_xmodem(d) == 0, 'taille ou CRC faux'
    print(f'contrôle : taille 0x3D0000, CRC du fichier entier = 0 (comme le vérifie maj_executer)')
    if json_v1 == PATCHS / 'v1.json':
        return repli() or programmes()
    return 0


V5 = PROJET / 'build' / 'V5'
V5_A = V5 / '1-en-premier-processeur-A'     # A 1.12 de Thomas (CONFIG › Version du firmware : A 1.12, B 1.11)
V5_B = V5 / '2-ensuite-processeur-B'
LISEZMOI_V5 = """V5 : Programmes réels (Sujet rapide, Portrait, Street, Profondeur, Piqué max), en P seulement.
Deux flashs, dans l'ordre, chacun avec une carte qui ne contient que ce fichier, à la racine :
  1. 1-en-premier-processeur-A/AD400112.BIN : mise à jour du A (le boîtier doit marcher comme avant ensuite :
     faire une photo en P avant de continuer) ;
  2. 2-ensuite-processeur-B/BD400111.BIN : mise à jour du B (menus V4 + Programme envoyé au A).
Accumulateur plein. Ne pas éteindre pendant une mise à jour.
Retour à Nikon : choisir Programme › Standard, puis flasher firmware/AD400112.bin et firmware/BD400111.bin.
"""


def programmes():
    """build/V5/ : la paire à flasher pour que Programme agisse, dans l'ordre : le A 1.12 patché
    (patchs/a-programmes-112.json, outils/programmes_a.py), puis le B de la V4 + l'étape 9
    (patchs/pipboy-9-programme-a.json)."""
    v1 = json.loads((PATCHS / 'v1.json').read_text(encoding='utf-8'))
    e9 = json.loads((PATCHS / 'pipboy-9-programme-a.json').read_text(encoding='utf-8'))
    doc = {'description': 'V5 : V4 + étape 9 (Programme envoyé au A, en P) ; à flasher après le A de la V5 (V5/1-en-premier-processeur-A/)',
           'patchs': v1['patchs'] + e9['patchs']}
    (PATCHS / 'v5-programmes.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    code = 0
    for j, dest in (('a-programmes-112.json', V5_A), ('v5-programmes.json', V5_B)):
        r = subprocess.run([sys.executable, str(PROJET / 'patch.py'), str(PATCHS / j), '--sortie', str(dest)],
                           capture_output=True, text=True)
        print(r.stdout + r.stderr, end='')
        code |= r.returncode
    (V5 / 'LISEZMOI.txt').write_text(LISEZMOI_V5, encoding='utf-8')
    return code


def repli():
    """patchs/v1-sans-bandeau.json et build/v1-sans-bandeau/ : la V1 moins le bandeau d'onglets (étape 5) et
    la navigation qui le suppose (étape 7), sans chevauchement."""
    v1 = json.loads((PATCHS / 'v1.json').read_text(encoding='utf-8'))
    cle = lambda p: (p['offset'], p['apres']['hex'])
    retires = {cle(p) for nom in ('pipboy-5-onglets', 'pipboy-7-navigation')
               for p in json.loads((PATCHS / f'{nom}.json').read_text(encoding='utf-8'))['patchs']}
    doc = {'description': "V1 sans le bandeau d'onglets (patchs/v1.json moins patchs/pipboy-5-onglets.json et "
                          "pipboy-7-navigation.json) : firmware de repli",
           'patchs': [p for p in v1['patchs'] if cle(p) not in retires]}
    (PATCHS / 'v1-sans-bandeau.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    r = subprocess.run([sys.executable, str(PROJET / 'patch.py'), str(PATCHS / 'v1-sans-bandeau.json'), '--sortie',
                        str(PROJET / 'build' / 'v1-sans-bandeau')], capture_output=True, text=True)
    print(r.stdout + r.stderr, end='')
    return r.returncode


# ---------------------------------------------------------------- self-test

def self_test():
    assert signe_grandeur(-446, 0x400) == 0x5BE and signe_grandeur(928, 0x400) == 0x3A0   # vus dans l'émulateur
    assert signe_grandeur(-54, 0x200) == 0x236 and decoder_signe_grandeur(0x236, 0x200) == -54
    for bit in (0x200, 0x400):
        assert all(decoder_signe_grandeur(signe_grandeur(v, bit), bit) == v for v in range(-bit + 1, bit))
    orig = bytes(patchpy.charger_original())
    s, code = assembler()
    # le LDI:32 d'origine et son créneau : CALL:D @R12 puis MOV R10,R4
    assert mot(orig, APPEL_TONALITE, 10).hex() == '9f8c00323c229f1c8ba4'
    # l'appel de modesScene_reglages : CALL @R12 sans créneau, puis LD @R15+,RP et LDI:8 #1,R4
    assert mot(orig, APPEL_MODES, 12).hex() == '9f8c0031ed1a971c0781c014'
    # le second envoi au A de la remise à zéro des réglages perso : CALL @R12 sans créneau
    assert mot(orig, APPEL_REINIT, 8).hex() == '9f8c00138546971c'
    # aucune instruction de saut dans le code ajouté n'utilise de créneau de délai (formes :D absentes)
    mots = [struct.unpack('>H', code[i:i + 2])[0] for i in range(0, len(code), 2)]
    assert not any(m in (0x9F0C, 0x9F1C, 0x9F20) or (m & 0xF000) == 0xF000 or (m & 0xF800) == 0xD800 for m in mots)
    vide = pathlib.Path('/nonexistent-recettes')
    patchs, sources, _ = construire_patchs(orig, vide)
    assert all(v.startswith('test') for v in sources.values())
    b = bytes(patchpy.appliquer(bytearray(orig), patchs))
    assert struct.unpack('>I', b[APPEL_TONALITE + 2 - BASE:][:4])[0] == CODE
    assert struct.unpack('>I', b[APPEL_MODES + 2 - BASE:][:4])[0] == s.labels['preglage_reglages']
    assert struct.unpack('>I', b[APPEL_REINIT + 2 - BASE:][:4])[0] == s.labels['preglage_reinit']
    assert b[TABLES + 72 - BASE:TABLES + 92 - BASE] == bytes([NETTETE_DEFAUT, SATURATION_DEFAUT, TONS_NORMAL, 0] * 5)
    t = b[TABLES + 16 - BASE:TABLES + 32 - BASE]
    assert [t[m] for _, m, _, _ in PREGLAGES] == [0, 1, 2, 3, 4] and t[0] == t[5] == 0xFF
    # Tri-X de test : trois lignes identiques, somme 512 → gris
    e = EMPLACEMENTS + 3 * TAILLE
    m = [decoder_signe_grandeur(v, 0x400) for v in struct.unpack('>9H', b[e - BASE:][:18])]
    assert m[0:3] == m[3:6] == m[6:9] and sum(m[0:3]) == 512
    c = courbes.courbes(orig)
    assert list(struct.unpack('>4096H', b[e + OFF_COURBE - BASE:][:8192])) == c[20]
    assert EMPLACEMENTS + len(PREGLAGES) * TAILLE <= FIN_LIBRE
    print(f'self-test OK : crochet {len(code)} octets à {CODE:#x}, 5 emplacements de {TAILLE:#x} octets '
          f'({EMPLACEMENTS:#x}–{EMPLACEMENTS + 5 * TAILLE:#x})')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['construire', 'build', 'asm'])
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--sortie', help='build : dossier des JSON et du firmware (hors patchs/ et build/)')
    ap.add_argument('--recettes', type=pathlib.Path, default=RECETTES,
                    help='dossier des recettes (défaut recettes/v1 ; dossier vide = données de test)')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.action == 'construire':
        construire(dossier=a.recettes, sortie=a.sortie)
    elif a.action == 'build':
        return build(a.sortie, a.recettes)
    elif a.action == 'asm':
        s, code = assembler()
        for k, v in sorted(s.labels.items(), key=lambda t: t[1]):
            print(f'{v:#08x} {k}')
        print(code.hex())
    else:
        ap.print_help()


if __name__ == '__main__':
    sys.exit(main())
