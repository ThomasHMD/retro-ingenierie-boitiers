#!/usr/bin/env python3
"""Menu Pip-Boy dans le firmware B du D40 : fabrique les patchs, étape par étape.

Cible : design/pipboy-planche.png (maquette validée). Chaque étape donne un patch au format de
patch.py (octets d'origine vérifiés) ; menu-pipboy.json les réunit avec menu-preglages.json.

  1 couleurs  palette 3 octets 0xD87C3 (223 entrées : fond, texte, barre, filets, onglets) et
              palette 0x1B0000 des pictogrammes (pipboy-palette.json) : noir et vert phosphore.
  2 textes    table C+D du français reconstruite dans la place libre (textes de longueur libre) :
              titres PRISE DE VUE, VISU, PERSO, CONFIG et libellés des nouvelles entrées.
  3 onglets   l'onglet Retouche disparaît : la navigation haut/bas saute de CONFIG à VISU
              (2 constantes de FUN_00131f8a) et la colonne ne dessine que 4 onglets (FUN_00146c48).
  4 menus     PRISE DE VUE à 7 entrées (Préréglage, Programme, ISO auto, Qualité, Balance des
              blancs, Taille, Réduction du bruit) ; écrans Programme, ISO auto (Marche, ISO mini,
              ISO maxi, Vitesse mini, Si trop sombre, valeurs à droite), Marche et Si trop sombre.
              Données dans la place des listes « Mon menu › Choisir les rubriques », dont l'option
              est retirée ; code dans la place libre (fonctions d'écran et d'entrée). Valeurs
              écrites (STD, RAP…, VIT, ISO, SOUS, L M S, BLOQ) dans une copie complétée de la
              planche 4.

Passe critique UX (design/critique-ux.md, tableau en tête) : couleurs de VISU et de l'écran
d'infos, libellés, aides (table B reconstruite), ISO auto lisible, ISO mini 200…1600, Menus
réduit à Complet, première ligne sous le titre.

  pipboy.py construire            écrit patchs/pipboy-1-couleurs.json … pipboy-4-menus.json et menu-pipboy.json
  pipboy.py asm                   listing du code ajouté
  pipboy.py --self-test

Adresses : ROM = offset du fichier + 0x40000 ; les données copiées en RAM au démarrage
(0x1544C4–0x15D528) y sont à ROM + 0x83B8BAEC (CARTE.md §2).
"""
import argparse
import json
import os
import pathlib
import struct
import sys

ICI = pathlib.Path(__file__).resolve().parent
PROJET = ICI.parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(PROJET))

import patch as patchpy  # noqa: E402
from chaines import Firmware  # noqa: E402

BASE = 0x40000
RAM = 0x83B8BAEC
PATCHS = PROJET / 'patchs'

# ---------------------------------------------------------------- couleurs

def ycc(r, g, b):
    y = 16 + 0.257 * r + 0.504 * g + 0.098 * b
    cb = 128 - 0.148 * r - 0.291 * g + 0.439 * b
    cr = 128 + 0.439 * r - 0.368 * g - 0.071 * b
    return bytes(max(0, min(255, round(v))) for v in (y, cb, cr))


VERT = (26, 255, 128)        # vert phosphore de la maquette
NOIR = (0, 0, 0)
FILET = (0, 110, 55)         # séparateurs, bordures
SOMBRE = (0, 38, 19)         # cases des onglets non choisis, fonds secondaires
VERT_DOUX = (14, 170, 85)    # numéros des réglages perso, texte grisé

PAL3 = 0xD87C3               # 223 entrées Y Cb Cr
# rôle de chaque entrée, relevé par sonde dans l'émulateur (luminance = numéro d'entrée)
ROLES = {
    NOIR: [0xC8, 0xCF, 0xCE, 0xD8, 0xAD, 0x78],
    VERT: [0xD2, 0x01, 0xD0, 0x1D, 0x1E, 0x1F, 0x20, 0x65, 0x66, 0x36, 0x93, 0xD9] + [i for i in range(0x21, 0x42) if i != 0x22],
    FILET: [0x12, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xC9, 0xDB, 0xDA, 0xA8, 0xDC],
    SOMBRE: [0xCC, 0xCD, 0xCA, 0xCB],
    VERT_DOUX: [0x24, 0xD1],
}
ROLES[VERT] += [0xB4, 0x8D]  # couleur imposée de la batterie (FUN_000a1302, écran d'infos graphique)
# passe critique UX (design/critique-ux.md, C14 à C17), entrées relevées par la même sonde
# (entrée i à Y = 16 + i, gris ; inverse exact de la conversion tronquée de Ecran.java) :
#  onglet VISU : 0x1C filet bleu sous le titre, 0x68 cadre brun-jaune du pictogramme de l'onglet ;
#  écran d'infos : 0x8B blanc (bandeau du bas ET valeurs RAW, AUTO, S, crochets : une seule entrée,
#  le bandeau devient donc une barre verte, comme la sélection des menus), 0xBA gris de « ◆Régler »
#  (→ noir : texte noir sur la barre), 0xBB remplissage des grands chiffres, 0xA5 disque beige du
#  cadran, 0x8E et 0xA6 graduations, 0x10 cercle intérieur, 0xA4 secteur grisé, 0x8A et 0x89
#  pictogrammes gris (P, ⊘N, note, éclair), 0xBE correction d'expo, 0x8F L, MF, [ ], 0x91 et 0x92
#  compteur de vues, 0x07 repère jaune
ROLES[VERT] += [0x1C, 0x68, 0x8B, 0x8E, 0xA6, 0x10, 0x07]
# chiffres de l'écran d'infos (photo du boîtier, octobre 2026 ; va avec l'étape 8) : fantômes des grands chiffres
# (0xBB) et du compteur (0x91) en vert très sombre, valeurs dans l'entrée 0x94 (vert), où l'étape 8 remappe le noir
ROLES[SOMBRE] += [0xBB, 0x91]
ROLES[VERT] += [0x94]
# mode Régler de l'écran d'infos (touche info) et ses listes de choix, jamais recolorés (photo et sonde du
# octobre 2026) ; entrées absentes des 35 écrans de menus sondés. 0x17 (texte de la case choisie, bleu marine
# sur la case verte) reste à Nikon : les écrans de la voie de secours s'en servent.
ROLES[NOIR] += [0x97, 0x98, 0xAC, 0xA1]   # fonds gris clairs (écran, panneau assombri, colonne) ; texte de la barre du bas
ROLES[VERT] += [0x9D, 0xA2, 0x86, 0x87, 0x88]   # valeurs de la colonne, titre (brun), case choisie (dégradé jaune 0x86-0x88)
ROLES[VERT_DOUX] += [0x9E, 0x8C, 0xB0]    # réglages grisés (L, MF, [ ]), colonne pendant un choix
ROLES[FILET] += [0x99, 0x9A, 0x9B, 0x9C, 0x9F, 0xA0]   # cadres, panneau grisé (chiffres, pictogrammes)
ROLES[NOIR] += [0xBA]
ROLES[SOMBRE] += [0xA5]
ROLES[VERT_DOUX] += [0x8A, 0x89, 0xBE, 0x8F, 0xA4, 0x92]
# 0x22 laissée à Nikon (octobre 2026) : c'est le fond des listes du jeu de couleurs Classique (premier flash :
# vert sur vert) ; les menus forcés en Graphique (étape 6) ne l'utilisent pas (sonde des 35 écrans).
# entrées 0x21–0x3F : dégradé de la barre de sélection (0x3F) et ses bords ; 0x24 = numéros
# des réglages perso, repris en vert doux ci-dessus (l'ordre du dict fait foi : VERT_DOUX en dernier)


def etape_couleurs(b):
    patchs = []
    avant = b[PAL3 - BASE:PAL3 - BASE + 3 * 223]
    apres = bytearray(avant)
    for couleur, entrees in ROLES.items():
        for i in entrees:
            apres[3 * i:3 * i + 3] = ycc(*couleur)
    patchs.append({'offset': hex(PAL3 - BASE), 'avant': {'hex': avant.hex()}, 'apres': {'hex': bytes(apres).hex()},
                   'texte': 'palette 0xD87C3 : fond noir, texte, titres, filets et barre de sélection vert phosphore'})
    ic = json.loads((PATCHS / 'pipboy-palette.json').read_text(encoding='utf-8'))['patchs']
    for p in ic:
        p = dict(p)
        p['texte'] = 'palette 0x1B0000 des pictogrammes teintée vert (pipboy-palette.json)'
        patchs.append(p)
    # batterie (demande de Thomas) : pictogrammes de la planche 0x4C (64 × 28) ; chaque tuile est
    # un calque d'une couleur. Contour et barres en vert (entrée 0x13 de la palette teintée, la plus
    # proche du vert phosphore), le liseré blanc intérieur (0x67) en noir (entrée 0).
    for ic in BATTERIE:
        a = icone_adresse(b, ic)
        n = (icone_adresse(b, ic + 1) - a) // 4
        for k in range(n):
            t = a + 4 * k + 1
            c = b[t - BASE]
            neuf = 0x00 if c == 0x67 else 0x13
            patchs.append(remplace(b, t, bytes([c]), bytes([neuf]),
                                   f'batterie {ic:#06x}, calque {k} : couleur {c:#04x} → {neuf:#04x}'))
    return patchs


TBL_ICONES = 0x157904
# niveaux de batterie : écran d'infos (0x81EA-0x81EC, 0x81F7-0x81F9, 0x8194, 0x8197), charge (0x8196),
# vide (0x81F3-0x81F6), choisis par FUN_000a1302 (l. 74050 de d40-tout.c) d'après 0x83CEE4D4
BATTERIE = [0x8194, 0x8196, 0x8197, 0x81EA, 0x81EB, 0x81EC, 0x81ED, 0x81F3, 0x81F4, 0x81F5, 0x81F6, 0x81F7, 0x81F8, 0x81F9]


def icone_adresse(b, ic):
    return struct.unpack('>I', b[TBL_ICONES + 4 * (ic & 0x7FFF) - BASE:][:4])[0]


# ---------------------------------------------------------------- textes

LANGUE = 4                       # français dans la table des langues 0x15C7A4
TABLE_LANGUES = 0x15C7A4
TEXTES = 0x3EA000                # table C+D française reconstruite (place libre)
ACC = {'é': b'\x81\x21', 'É': b'\x81\x0f', 'è': b'\x81\x20', 'à': b'\x81\x19', 'ê': b'\x81\x22',
       'î': b'\x81\x26', 'ô': b'\x81\x2a', '×': b'\x81\x15'}


def code_texte(s):
    out = bytearray()
    for c in s:
        out += ACC.get(c) or c.encode('ascii')
    return bytes(out)


# identifiants de texte (table D) réutilisés : libellés des listes « Mon menu › Choisir les
# rubriques » (inaccessibles une fois l'option retirée), aucun usage littéral dans le code
ID = {'programme': 0x19B, 'standard': 0x19D, 'rapide': 0x19E, 'portrait': 0x19F, 'street': 0x1A1,
      'profondeur': 0x1A3, 'pique': 0x1A5, 'sombre': 0x1A6, 's_vitesse': 0x1A7, 's_iso': 0x1A9,
      's_sous': 0x1AB, 'marche': 0x1AC}
NOUVEAUX_TEXTES = {
    # passe critique UX : C6, C7 (singulier, accord), C5 (Menus), C20 (CONFIG), C21 (PERSO 06),
    # point 16 de la critique (OFF / ON au lieu de Désactivée / Activée, comme la valeur à droite)
    0x0022: 'Préréglage', 0x002D: 'Personnalisé', 0x00AA: 'Menus', 0x00AB: 'Date et heure',
    0x00AC: 'Luminosité écran', 0x00AE: 'Langue', 0x020C: 'Style écran infos', 0x0215: 'Infos auto',
    0x0071: 'Sans carte', 0x0083: 'Bloqué', 0x0084: 'Autorisé', 0x0089: 'OFF', 0x008A: 'ON',
    0x0048: 'OFF', 0x0049: 'ON',     # Réduction du bruit, même règle
    ID['marche']: 'Marche',
    0x0000: 'VISU', 0x0021: 'PRISE DE VUE', 0x006D: 'PERSO', 0x00A8: 'CONFIG',
    0x0024: 'Qualité', 0x0074: 'ISO auto', 0x013F: 'ISO maxi', 0x0140: 'Vitesse mini',
    0x01F8: 'ISO mini',
    ID['programme']: 'Programme', ID['standard']: 'Standard', ID['rapide']: 'Sujet rapide',
    ID['portrait']: 'Portrait', ID['street']: 'Street', ID['profondeur']: 'Profondeur',
    ID['pique']: 'Piqué max', ID['sombre']: 'Si trop sombre', ID['s_vitesse']: 'Baisser la vitesse',
    ID['s_iso']: 'Monter en ISO', ID['s_sous']: 'Sous-exposer',
}


# aides (touche ?) : table B du français reconstruite elle aussi, pointeur B de la langue dans la
# table des langues (copiée en RAM et lue par langue_choisir, comme A et C). Format : 1er octet =
# nombre de lignes, lignes séparées par « \n ». Ids 0x4000 | numéro ; 141 aides d'origine (0 à 0x8C).
TEXTES_B = 0x3ED000              # place libre, après la table C+D
AIDE_NB_ORIG = 141
AIDE = {'preglage': 0x26, 'programme': 0x8D, 'isoauto': 0x8E, 'sombre': 0x8F, 'isomini': 0x90}
NOUVELLES_AIDES = {
    # une ligne par élément ; « Terme: » en début de ligne s'affiche surligné (comme les aides Nikon)
    # C9 : aide de la ligne Préréglage de PRISE DE VUE (était le texte générique de Nikon)
    AIDE['preglage']: ["Rendu des JPEG, NEF intact.", "N: Nikon d'origine.", "HB: Hasselblad.",
                       "CC: Classic Chrome.", "PF: Positive Film.", "TX, H5: N&B Tri-X, HP5.",
                       "Personnalisé: réglages fins de Nikon."],
    # C10
    AIDE['programme']: ["Choix de vitesse et ouverture.", "Rapide: 1/500 et plus.",
                        "Portrait: pleine ouverture, 1/125 et plus.", "Street: f/5,6, 1/250 et plus.", "Profondeur: f/11.",
                        "Piqué: meilleure ouverture de l'objectif."],
    AIDE['isoauto']: ["Le boîtier monte en ISO quand la vitesse descend sous la vitesse mini, "
                      "sans dépasser l'ISO maxi."],
    AIDE['sombre']: ["Quand la vitesse mini et l'ISO maxi sont atteints:", "Vitesse: baisser la vitesse.",
                     "ISO: monter au-delà du maxi.", "Sous: sous-exposer."],
    AIDE['isomini']: ["Sensibilité de départ: le boîtier ne descend jamais en dessous."],
}


def aide_texte(paragraphes, largeur=30):
    lignes = []
    for s in paragraphes:
        cur = ''
        for m in s.split():
            if cur and len(cur) + 1 + len(m) > largeur:
                lignes.append(cur)
                cur = m
            else:
                cur = f'{cur} {m}' if cur else m
        lignes.append(cur)
    return bytes([len(lignes)]) + b'\n'.join(code_texte(l) for l in lignes)


def table_aides(b_preglages):
    """Patchs de la table B du français reconstruite (aides d'origine + NOUVELLES_AIDES)."""
    fw = Firmware.__new__(Firmware)
    fw.b = bytes(b_preglages)
    ch = fw.chaines(LANGUE)
    n = max(NOUVELLES_AIDES) + 1
    morceaux = []
    for i in range(n):
        if i in NOUVELLES_AIDES:
            morceaux.append(aide_texte(NOUVELLES_AIDES[i]))
        else:
            assert i < AIDE_NB_ORIG
            morceaux.append(ch[('B', i)][1])
    ptr, data, a = bytearray(), bytearray(), TEXTES_B + 4 * (n + 1)
    for m in morceaux:
        ptr += struct.pack('>I', a)
        data += m
        a += len(m)
    ptr += struct.pack('>I', a)
    neuf = bytes(ptr + data)
    off = TEXTES_B - BASE
    avant = b_preglages[off:off + len(neuf)]
    assert avant == b'\xff' * len(neuf), 'place libre des aides occupée'
    assert TEXTES_B + len(neuf) <= GLYPHES, 'aides trop longues'
    pb = TABLE_LANGUES + 4 * (3 * LANGUE + 1)
    return [
        {'offset': hex(off), 'avant': {'hex': avant.hex()}, 'apres': {'hex': neuf.hex()},
         'texte': f'table B (aides) du français reconstruite ({n} aides dont {len(NOUVELLES_AIDES)} neuves, {len(neuf)} octets)'},
        {'offset': hex(pb - BASE), 'avant': {'hex': b_preglages[pb - BASE:pb - BASE + 4].hex()},
         'apres': {'hex': struct.pack('>I', TEXTES_B).hex()},
         'texte': 'pointeur B (aides) de la langue 4 (français) vers la table reconstruite'},
    ]


def etape_textes(b_preglages):
    """b_preglages : firmware avec menu-preglages.json appliqué (ses libellés sont repris)."""
    fw = Firmware.__new__(Firmware)
    fw.b = bytes(b_preglages)
    t = fw.tables(LANGUE)
    ch = fw.chaines(LANGUE)
    nc, nd = len(t['C']), len(t['D'])
    morceaux = []
    for i in range(nc):
        morceaux.append(ch[('C', i)][1])
    pre = {0x22, 0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x13C}  # libellés de menu-preglages, complétés d'espaces
    for i in range(nd):
        o = ch[('D', i)][1]
        if i in NOUVEAUX_TEXTES:
            o = code_texte(NOUVEAUX_TEXTES[i])
        elif i in pre:
            o = o.rstrip(b' ')
        morceaux.append(o)
    n = len(morceaux)
    pointeurs = TEXTES
    blob = TEXTES + 4 * (n + 1)
    ptr, data, a = bytearray(), bytearray(), blob
    for m in morceaux:
        ptr += struct.pack('>I', a)
        data += m
        a += len(m)
    ptr += struct.pack('>I', a)  # sentinelle : longueur de la dernière chaîne
    neuf = bytes(ptr + data)
    off = TEXTES - BASE
    avant = b_preglages[off:off + len(neuf)]
    assert avant == b'\xff' * len(neuf), 'place libre des textes occupée'
    pc = TABLE_LANGUES + 4 * (3 * LANGUE + 2)
    patchs = [
        {'offset': hex(off), 'avant': {'hex': avant.hex()}, 'apres': {'hex': neuf.hex()},
         'texte': f'table C+D du français reconstruite ({nc} + {nd} chaînes, {len(neuf)} octets)'},
        {'offset': hex(pc - BASE), 'avant': {'hex': b_preglages[pc - BASE:pc - BASE + 4].hex()},
         'apres': {'hex': struct.pack('>I', pointeurs).hex()},
         'texte': 'pointeur C de la langue 4 (français) vers la table reconstruite'},
        # la table D n'est pas déduite de C : langue_choisir (0x9B14E) la prend dans une constante
        # par langue (LDI:32 #0x2B124C,R11 en 0x9B174 pour le français)
        remplace(b_preglages, 0x9B176, struct.pack('>I', 0x2B124C), struct.pack('>I', TEXTES + 4 * nc),
                 'langue_choisir : pointeur D du français (constante du code) vers la table reconstruite'),
    ]
    return patchs + table_aides(b_preglages)


# ---------------------------------------------------------------- onglets

def mot(b, a, n=4):
    return b[a - BASE:a - BASE + n]


def remplace(b, adresse, avant, apres, texte):
    assert mot(b, adresse, len(avant)) == avant, (hex(adresse), mot(b, adresse, len(avant)).hex(), avant.hex())
    return {'offset': hex(adresse - BASE), 'avant': {'hex': avant.hex()}, 'apres': {'hex': apres.hex()}, 'texte': texte}


VISU, PDV, PERSO, CONFIG, RETOUCHE = (a + RAM for a in (0x1592D0, 0x1598E0, 0x15A380, 0x15AEC0, 0x15BDC0))


def etape_onglets(b):
    P = struct.pack
    return [
        remplace(b, 0x13208E, P('>I', RETOUCHE), P('>I', CONFIG),
                 'FUN_00131f8a, touche haut sur VISU : CONFIG au lieu de RETOUCHE'),
        remplace(b, 0x13218A, P('>I', RETOUCHE), P('>I', VISU),
                 'FUN_00131f8a, touche bas sur CONFIG : VISU au lieu de RETOUCHE'),
        remplace(b, 0x146DE0, bytes.fromhex('a858'), bytes.fromhex('a848'),
                 'FUN_00146c48 : CMP #5 → #4, la colonne ne dessine que 4 onglets'),
        remplace(b, 0x146CC6, bytes.fromhex('a858'), bytes.fromhex('a848'),
                 'FUN_00146c48 (mode 6) : CMP #5 → #4'),
    ]


# ---------------------------------------------------------------- assembleur FR (sous-ensemble)

COND = {'ra': 0, 'no': 1, 'eq': 2, 'ne': 3, 'c': 4, 'nc': 5, 'n': 6, 'p': 7, 'v': 8, 'nv': 9,
        'lt': 0xA, 'ge': 0xB, 'le': 0xC, 'gt': 0xD, 'ls': 0xE, 'hi': 0xF}


class Asm:
    """Assembleur à deux passes pour le Fujitsu FR (encodages vérifiés sur le désassembleur de
    nikon-firmware-tools : voir self-test et `pipboy.py asm`)."""

    def __init__(self, org):
        self.org = org
        self.items = []      # (adresse, octets | (kind, label, ...))
        self.labels = {}
        self.pc = org

    def _w(self, *mots):
        for m in mots:
            self.items.append((self.pc, struct.pack('>H', m & 0xFFFF)))
            self.pc += 2

    def label(self, nom):
        assert nom not in self.labels, nom
        self.labels[nom] = self.pc

    def align(self, n=4):
        while self.pc % n:
            self.nop()

    def data16(self, v):
        self._w(v)

    def data32(self, v):
        self._w(v >> 16, v)

    def ldi32(self, v, ri):
        if isinstance(v, str):
            self.items.append((self.pc, ('ldi32', v, ri)))
            self.pc += 6
        else:
            self._w(0x9F80 | ri, (v >> 16) & 0xFFFF, v & 0xFFFF)

    def ldi8(self, v, ri):
        assert 0 <= v <= 0xFF
        self._w(0xC000 | v << 4 | ri)

    def ld(self, rj, ri):      self._w(0x0400 | rj << 4 | ri)   # LD @Rj,Ri
    def lduh(self, rj, ri):    self._w(0x0500 | rj << 4 | ri)
    def ldub(self, rj, ri):    self._w(0x0600 | rj << 4 | ri)
    def ld13(self, rj, ri):    self._w(0x0000 | rj << 4 | ri)   # LD @(R13,Rj),Ri
    def lduh13(self, rj, ri):  self._w(0x0100 | rj << 4 | ri)
    def ldub13(self, rj, ri):  self._w(0x0200 | rj << 4 | ri)
    def st(self, ri, rj):      self._w(0x1400 | rj << 4 | ri)   # ST Ri,@Rj
    def sth(self, ri, rj):     self._w(0x1500 | rj << 4 | ri)
    def stb(self, ri, rj):     self._w(0x1600 | rj << 4 | ri)
    def st13(self, ri, rj):    self._w(0x1000 | rj << 4 | ri)   # ST Ri,@(R13,Rj)
    def sth13(self, ri, rj):   self._w(0x1100 | rj << 4 | ri)
    def stb13(self, ri, rj):   self._w(0x1200 | rj << 4 | ri)
    def add(self, rj, ri):     self._w(0xA600 | rj << 4 | ri)
    def addi(self, i, ri):     assert 0 <= i <= 15; self._w(0xA400 | i << 4 | ri)
    def cmp(self, rj, ri):     self._w(0xAA00 | rj << 4 | ri)
    def cmpi(self, i, ri):     assert 0 <= i <= 15; self._w(0xA800 | i << 4 | ri)
    def mov(self, rj, ri):     self._w(0x8B00 | rj << 4 | ri)
    def lsl(self, u, ri):      assert 0 <= u <= 15; self._w(0xB400 | u << 4 | ri)
    def lsr(self, u, ri):      assert 0 <= u <= 15; self._w(0xB000 | u << 4 | ri)
    def and_(self, rj, ri):    self._w(0x8200 | rj << 4 | ri)   # AND Rj,Ri
    def or_(self, rj, ri):     self._w(0x9200 | rj << 4 | ri)   # OR Rj,Ri : Ri ← Ri | Rj
    def extsh(self, ri):       self._w(0x97A0 | ri)
    def extub(self, ri):       self._w(0x9790 | ri)
    def call_r(self, ri):      self._w(0x9710 | ri)
    def jmp_r(self, ri):       self._w(0x9700 | ri)
    def ret(self):             self._w(0x9720)
    def push_rp(self):         self._w(0x1781)
    def pop_rp(self):          self._w(0x0781)
    def push(self, ri):        self._w(0x1700 | ri)
    def pop(self, ri):         self._w(0x0700 | ri)
    def nop(self):             self._w(0x9FA0)
    def bandl(self, u, ri):    self._w(0x8000 | u << 4 | ri)
    def bandh(self, u, ri):    self._w(0x8100 | u << 4 | ri)
    def borl(self, u, ri):     self._w(0x9000 | u << 4 | ri)
    def borh(self, u, ri):     self._w(0x9100 | u << 4 | ri)
    def sub(self, rj, ri):     self._w(0xAC00 | rj << 4 | ri)   # SUB Rj,Ri : Ri ← Ri − Rj
    def add2(self, i, ri):     assert -16 <= i <= -1; self._w(0xA500 | (i & 0xF) << 4 | ri)
    def extuh(self, ri):       self._w(0x97B0 | ri)

    def addsp(self, s):
        assert s % 4 == 0 and -512 <= s <= 508
        self._w(0xA300 | (s // 4) & 0xFF)

    def ldi20(self, v, ri):
        assert 0 <= v <= 0xFFFFF
        self._w(0x9B00 | (v >> 16) << 4 | ri, v & 0xFFFF)

    def ldi(self, v, ri):
        """Constante numérique : LDI:8, LDI:20 ou LDI:32 selon la taille."""
        if 0 <= v <= 0xFF:
            self.ldi8(v, ri)
        elif 0 <= v <= 0xFFFFF:
            self.ldi20(v, ri)
        else:
            self.ldi32(v & 0xFFFFFFFF, ri)

    def brut(self, octets):
        """Données brutes (longueur paire)."""
        octets = bytes(octets)
        if len(octets) % 2:
            octets += b'\x00'
        for i in range(0, len(octets), 2):
            self._w(octets[i] << 8 | octets[i + 1])

    def b(self, cond, label):
        self.items.append((self.pc, ('b', label, COND[cond])))
        self.pc += 2

    def appel(self, cible):
        """CALL absolu par R12 (R12 écrasé)."""
        self.ldi32(cible, 12)
        self.call_r(12)

    def octets(self):
        out = bytearray()
        for a, x in self.items:
            if isinstance(x, bytes):
                out += x
            elif x[0] == 'b':
                cible = self.labels[x[1]]
                d = (cible - (a + 2)) // 2
                assert -128 <= d <= 127, f'branchement trop loin vers {x[1]}'
                out += struct.pack('>H', 0xE000 | x[2] << 8 | (d & 0xFF))
            elif x[0] == 'ldi32':
                v = self.labels[x[1]]
                out += struct.pack('>HI', 0x9F80 | x[2], v)
        return bytes(out)


# ---------------------------------------------------------------- menus

CODE = 0x3E8000                  # code ajouté (place libre, jamais utilisée par Nikon)
ZONE = (0x15B920, 0x15BAF0)      # listes « Mon menu › Choisir les rubriques » Retouche + Config
ZONE2 = (0x15BAF0, 0x15BC40)     # liste « Choisir les rubriques » de Réglages perso (même sort)
TBL_ECRANS = 0x156644
TBL_N = 0x154CAC                 # enregistrements par numéro d'entrée (12 octets), RAM 0x83CE0798
MENU_COURANT = 0x83CEE49C
PDV_HDR = 0x1598E0
PDV_ENTREES_ORIG = 0x159900
ENTREE_SOUS_MENU = 0x143EE4      # fonction d'enregistrement : entrer dans le sous-menu de l'entrée
SURBRILLANCE = 0x132D0C          # FUN_00132d0c(index) : place la surbrillance (avec défilement)
ENVOI_CMD5 = 0x138546            # envoie le bloc 0x83CE974D (14 octets) au processeur A
ISO_OCTET = 0x83CE974F           # ISO auto : bit 7 marche, bits 4-6 ISO maxi, bits 0-3 vitesse mini
ISO_SENS_OCTET = 0x83CE957D      # sensibilité : 0x48 = 200, +12 par IL (0x78 = HI 1), lu par 0x146316
POS_7 = 0x15C580 + RAM           # positions de la liste à 7 lignes (menu Configuration)
POS_HAUT = 0x15C528 + RAM        # 7 lignes sous le titre (x 88, y 43…211) : celles de Préréglage (C13)
POS_SOUS = 0x15C560 + RAM        # 5 lignes sous le sous-titre (y 71…183) : écrans à fil d'Ariane (C11, C13)
ISO_SENS = 0x159960              # menu Sensibilité ISO (devient ISO mini)
ISO_SENS_ENTREE = 0x146316
ISO_MAXI = 0x15AA10
ISO_VITESSE = 0x15A970
ECRAN_PROG, ECRAN_ISO, ECRAN_SOMBRE, ECRAN_MARCHE = 70, 71, 72, 73   # écrans « Mon menu » recyclés
ECRAN_ISO_SENS, ECRAN_CSM = 32, 68
CSM_CONFIG = 0x15B850            # menu « Menu CSM/Config. » : Simple, Complet, Mon menu
ATTR_VALEURS = 0x0002            # attribut d'en-tête : sous-écran, valeur (pictogramme) à droite
ATTR_CHOIX = 0x0010              # sous-écran, liste de choix (celui des écrans Nikon)
# Programme et Si trop sombre, gardés à l'extinction (V1, octobre 2026) : deux octets libres du bloc de
# réglages n° 10 (0x83CED248, 12 octets) de la table 0xD5364, que la tâche 4 écrit en flash (0x180000 /
# 0x190000, journal) à l'extinction et que FUN_0006b44c relit au démarrage, comme le mode couleur
# (bloc 2) ou la langue (bloc 1). Aucune référence à 0x83CED24E ni 0x83CED24F dans le code (C de Ghidra
# et constantes du binaire) ; la valeur relue est bornée avant usage (un ancien firmware a pu y écrire).
PROG_OCTET = 0x83CED24E          # 0 Standard … 5 Piqué max
SOMBRE_OCTET = 0x83CED24F        # 0 baisser la vitesse, 1 monter en ISO, 2 sous-exposer
PROG_MAX, SOMBRE_MAX = 5, 2

# numéros d'entrée recyclés (listes « Mon menu », 0x144–0x17C)
N = {'programme': 0x144, 'isoauto': 0x145, 'prog0': 0x146, 'iso_non': 0x14C, 'iso_oui': 0x14D,
     'iso_mini': 0x14E, 'iso_maxi': 0x14F, 'iso_vitesse': 0x150, 'sombre': 0x151, 'sombre0': 0x152,
     'marche': 0x155}


def disposition():
    lieu = {}
    a = ZONE[0]
    # tailles inchangées depuis la v1 (iso garde 0x80 pour 5 entrées) ; la case « valeurs » n'est plus
    # lue depuis la V1 (choix rangés dans le bloc de réglages sauvegardé, voir PROG_OCTET)
    for nom, taille in (('pdv', 7 * 16), ('prog', 0x20 + 6 * 16), ('iso', 0x20 + 6 * 16),
                        ('sombre', 0x20 + 3 * 16), ('valeurs', 16)):
        lieu[nom] = a
        a += taille
    assert a <= ZONE[1], hex(a)
    # pas d'en-tête à l'adresse d'origine 0x15BAF0 : Nikon y reconnaît la liste « Choisir les
    # rubriques » de Réglages perso et dessine le crayon de l'onglet à côté du titre
    a = ZONE2[0] + 0x10
    for nom, taille in (('marche', 0x20 + 2 * 16),):
        lieu[nom] = a
        a += taille
    assert a <= ZONE2[1], hex(a)
    return lieu


def entree(icone, libelle, aide, f6, numero, sous_menu):
    return struct.pack('>HHHHHHI', icone, libelle, aide, f6, 1, numero, sous_menu)


def entete(titre, sous_titre, attr, nb, ecran, parent, positions, entrees):
    return struct.pack('>HHHHHHHHHHIII', titre, sous_titre, attr, 1, nb, nb, 0, 0, 0, ecran,
                       parent, positions, entrees)


# pictogrammes de valeur (ISO auto, C4) : listes Nikon, dans l'ordre des réglages
ICONES_ISO = [0x8036, 0x803C, 0x8040, 0x8035, 0x8044]                 # 200 400 800 1600 HI 1
ICONES_MAXI = [0x803C, 0x803C, 0x8040, 0x8035] + [0x8035] * 4          # bits 4-6 : 1 = 400 … 3 = 1600
ICONES_VIT = [0x80BE, 0x80C6, 0x80C3, 0x80BF, 0x80C7, 0x80C4, 0x80C1, 0x80CE] + [0x80C3] * 8   # 1/125 … 1 s


def code_menus(lieu):
    """Fonctions ajoutées. Registres : R0-R7, R12, R13 libres (convention du compilateur Fujitsu)."""
    L = {k: v + RAM for k, v in lieu.items()}
    s = Asm(CODE)

    def borner(ri, maxi, tmp, nom):
        """Ri = 0 si Ri > maxi (valeur relue de la flash, peut-être écrite par un autre firmware)."""
        s.ldi8(maxi, tmp)
        s.cmp(tmp, ri)
        s.b('le', nom)
        s.ldi8(0, ri)
        s.label(nom)

    # --- écran 14 (PRISE DE VUE) : entrée d'origine, puis la liste à 7 entrées
    s.label('pdv_entree')
    s.push_rp()
    s.appel(0x143B46)                    # ecran014_entree d'origine (valeurs dans l'ancienne liste)
    s.ldi32(PDV_HDR + RAM, 4)
    s.ldi8(0x1C, 13)
    s.ld13(4, 0)
    s.ldi32(0x83CE06B8, 1)               # « Mon menu » actif : liste filtrée par Nikon, on n'y touche pas
    s.cmp(1, 0)
    s.b('eq', 'pdv_fin')
    s.ldi32(L['pdv'], 6)
    s.st13(6, 4)                         # +1C : nouvelle liste
    s.ldi8(7, 1)
    s.ldi8(0x08, 13)
    s.sth13(1, 4)                        # +8 : 7 sélectionnables (FUN_0014385c, patché, dit aussi 7)
    s.ldi8(0x0A, 13)
    s.sth13(1, 4)                        # +A : 7 entrées
    s.ldi32(PDV_ENTREES_ORIG + RAM, 5)
    for k, m in ((0, 0), (1, 3), (2, 5), (3, 4), (5, 6)):   # valeurs : ancien rang → nouveau
        s.ldi8(16 * k, 13)
        s.lduh13(5, 1)
        s.ldi8(16 * m, 13)
        s.sth13(1, 6)
    s.ldi32(ISO_OCTET, 0)                # ISO auto : pictogramme OFF (0x80AB) ou ON (0x80AC)
    s.ldub(0, 1)
    s.ldi8(0x80, 2)
    s.extub(1)
    s.ldi32(0x80AB, 3)
    s.cmp(2, 1)
    s.b('lt', 'pdv_off')
    s.addi(1, 3)
    s.label('pdv_off')
    s.ldi8(0x20, 13)
    s.sth13(3, 6)
    s.ldi32(PROG_OCTET, 0)               # Programme : pictogramme du programme choisi
    s.ldub(0, 1)
    borner(1, PROG_MAX, 2, 'pdv_prog_ok')
    s.lsl(1, 1)
    s.ldi32('icones_prog', 0)
    s.add(0, 1)
    s.lduh(1, 1)
    s.ldi8(0x10, 13)
    s.sth13(1, 6)
    s.label('pdv_fin')
    s.pop_rp()
    s.ret()

    # --- entrée des écrans Programme et Si trop sombre : surbrillance = valeur rangée
    for nom, octet, maxi in (('prog', PROG_OCTET, PROG_MAX), ('sombre', SOMBRE_OCTET, SOMBRE_MAX)):
        s.label(f'{nom}_entree')
        s.ldi32(octet, 0)
        s.ldub(0, 4)
        borner(4, maxi, 1, f'{nom}_borne')
        s.ldi32(SURBRILLANCE, 12)
        s.jmp_r(12)                      # FUN_00132d0c(R4), retour direct à l'appelant
        # --- action d'une entrée : ranger l'index choisi, revenir au menu parent
        s.label(f'{nom}_choix')
        s.ldi32(MENU_COURANT, 4)
        s.ld(4, 0)
        s.ldi8(0x0E, 13)
        s.lduh13(0, 1)
        s.ldi8(0x0C, 13)
        s.lduh13(0, 2)
        s.add(2, 1)
        s.ldi32(octet, 3)
        s.stb(1, 3)
        s.ldi8(0x14, 13)
        s.ld13(0, 0)
        s.st(0, 4)
        s.ret()

    # --- ISO auto (C4) : chaque ligne reçoit le pictogramme de sa valeur ; la surbrillance reste où
    # elle est (retour d'un sous-écran). R1 = indice dans la table, posé à +0 de l'entrée.
    def poser(table, k):
        s.lsl(1, 1)
        s.ldi32(table, 0)
        s.add(0, 1)
        s.lduh(1, 1)
        s.ldi8(16 * k, 13)
        s.sth13(1, 6)

    s.label('iso_entree')
    s.ldi32(L['iso'] + 0x20, 6)
    s.ldi32(ISO_OCTET, 0)                # ligne 0 : marche (bit 7)
    s.ldub(0, 1)
    s.lsr(7, 1)
    poser('icones_marche', 0)
    s.ldi32(ISO_SENS_OCTET, 0)           # ligne 1 : ISO mini = sensibilité réglée
    s.ldub(0, 2)
    s.ldi8(0, 1)
    for k, seuil in enumerate((0x54, 0x60, 0x6C, 0x78)):
        s.ldi8(seuil, 3)
        s.cmp(3, 2)
        s.b('lt', 'iso_sens_ok')
        s.addi(1, 1)
    s.label('iso_sens_ok')
    poser('icones_iso', 1)
    s.ldi32(ISO_OCTET, 0)                # ligne 2 : ISO maxi (bits 4-6)
    s.ldub(0, 1)
    s.lsr(4, 1)
    s.ldi8(7, 2)
    s.and_(2, 1)
    poser('icones_maxi', 2)
    s.ldi32(ISO_OCTET, 0)                # ligne 3 : vitesse mini (bits 0-3)
    s.ldub(0, 1)
    s.ldi8(0xF, 2)
    s.and_(2, 1)
    poser('icones_vit', 3)
    s.ldi32(SOMBRE_OCTET, 0)             # ligne 4 : Si trop sombre
    s.ldub(0, 1)
    s.ldi8(3, 2)
    s.and_(2, 1)
    poser('icones_sombre', 4)
    s.ret()

    # --- ISO auto › Marche : surbrillance sur OFF ou ON
    s.label('marche_entree')
    s.ldi32(ISO_OCTET, 0)
    s.ldub(0, 4)
    s.lsr(7, 4)
    s.ldi32(SURBRILLANCE, 12)
    s.jmp_r(12)
    # --- OFF / ON (comme l'action d'origine 0x136454 : octet, drapeau, envoi au A), retour à ISO auto
    s.label('iso_choix')
    s.push_rp()
    s.ldi32(MENU_COURANT, 4)
    s.ld(4, 0)
    s.ldi8(0x0C, 13)
    s.lduh13(0, 1)
    s.ldi32(ISO_OCTET, 5)
    s.ldi32(0x83CED100, 6)
    s.cmpi(0, 1)
    s.b('ne', 'iso_oui')
    s.bandh(0x7, 5)                      # bit 7 à 0
    s.bandl(0xB, 6)                      # 0x83CED100 bit 2 à 0
    s.b('ra', 'iso_envoi')
    s.label('iso_oui')
    s.borh(0x8, 5)
    s.borl(0x4, 6)
    s.label('iso_envoi')
    s.appel(ENVOI_CMD5)
    s.ldi32(MENU_COURANT, 4)
    s.ld(4, 0)
    s.ldi8(0x14, 13)
    s.ld13(0, 0)
    s.st(0, 4)
    s.pop_rp()
    s.ret()

    # --- ISO mini (C12) : écran Sensibilité ISO de Nikon, liste ramenée à 200…1600 (la liste part de
    # l'entrée 200, 4 entrées). La fonction d'origine calcule la surbrillance par rapport au début de
    # la liste (donc juste) mais retire une entrée sélectionnable en P, S, A, M (pour griser
    # « Automatique ») : on la rend, on borne l'indice à 0…3 et on replace la surbrillance.
    s.label('isomini_entree')
    s.push_rp()
    s.appel(ISO_SENS_ENTREE)
    s.ldi32(ISO_SENS + RAM, 5)
    s.ldi8(4, 1)
    s.ldi8(0x08, 13)
    s.sth13(1, 5)                        # +8 : 4 sélectionnables
    s.ldi32(MENU_COURANT, 0)
    s.ld(0, 0)
    s.ldi8(0x0C, 13)
    s.lduh13(0, 4)
    s.extsh(4)
    s.ldi8(3, 2)
    s.cmp(2, 4)
    s.b('le', 'isomini_pas_trop')
    s.mov(2, 4)
    s.label('isomini_pas_trop')
    s.cmpi(0, 4)
    s.b('ge', 'isomini_pose')
    s.ldi8(0, 4)
    s.label('isomini_pose')
    s.appel(SURBRILLANCE)
    s.pop_rp()
    s.ret()

    # --- Menus (C5) : une seule entrée, Complet
    s.label('csm_entree')
    s.ldi8(0, 4)
    s.ldi32(SURBRILLANCE, 12)
    s.jmp_r(12)

    s.align(4)
    for nom, table in (('icones_prog', ICONES_PROG), ('icones_marche', [0x80AB, 0x80AC]),
                       ('icones_iso', ICONES_ISO), ('icones_maxi', ICONES_MAXI), ('icones_vit', ICONES_VIT),
                       ('icones_sombre', ICONES_SOMBRE + [ICONES_SOMBRE[0]])):
        s.label(nom)
        for ic in table:
            s.data16(ic)
    return s


# ---------------------------------------------------------------- pictogrammes de valeur

# Valeurs écrites (C8, C22, C21, et Si trop sombre pour C4) : glyphes 80 × 40 de la planche 4, celle de
# OFF, ON, AUTO, LOCK (capitales de 32 points, lignes 4 à 35, centrées). La planche n'a pas de place :
# ses 21 glyphes sont recopiés dans la place libre (GLYPHES), suivis des nouveaux, et son descripteur
# (0x1B01A0 + 12 × 4) pointe sur la copie. Les glyphes d'origine restent en place.
PLANCHES = 0x1B01A0
PLANCHE_VAL = 4
GLYPHES = 0x400000               # place libre (après les aides)
COULEUR_VALEUR = 0x4B            # couleur des valeurs (OFF, RAW…) dans la palette 0x1B0000
# pictogrammes recyclés : les 6 de l'onglet Retouche (0x8173–0x8178, plus dessinés depuis l'étape 3)
# pour Programme ; HI 0.3 / 0.5 / 0.7 (0x8041–0x8043 : le D40 n'a que HI 1, aucune entrée de menu ni
# code ne les cite) pour Si trop sombre ; taille d'image (0x811B–0x811D, C22) et LOCK (0x8010, C21)
# redessinés en lettres
ICONES_PROG = list(range(0x8173, 0x8179))
MOTS_PROG = ['STD', 'RAP', 'PORT', 'STR', 'PROF', 'PIQ']
ICONES_SOMBRE = [0x8041, 0x8042, 0x8043]
MOTS_SOMBRE = ['VIT', 'ISO', 'SOUS']
VALEURS_ECRITES = (list(zip(ICONES_PROG, MOTS_PROG)) + list(zip(ICONES_SOMBRE, MOTS_SOMBRE))
                   + [(0x811B, 'L'), (0x811C, 'M'), (0x811D, 'S'), (0x8010, 'BLOQ')])


def pictos_valeurs(b):
    import icones
    desc = PLANCHES + 12 * PLANCHE_VAL
    l, h, rl = b[desc - BASE], b[desc - BASE + 1], b[desc - BASE + 6] >> 3
    assert (l, h, rl) == (80, 40, 10)
    donnees = struct.unpack('>I', mot(b, desc + 8))[0]
    taille = h * rl
    n0 = (struct.unpack('>I', mot(b, PLANCHES + 12 * (PLANCHE_VAL - 1) + 8))[0] - donnees) // taille
    assert n0 == 21, n0              # données de la planche 3 juste après celles de la planche 4
    pl = {'l': l, 'h': h, 'octets_ligne': rl}
    neuf = bytearray(b[donnees - BASE:donnees - BASE + n0 * taille])
    patchs = []
    for k, (ic, motv) in enumerate(VALEURS_ECRITES):
        g = n0 + k
        neuf += icones.dessiner(motv, pl)
        a = icone_adresse(b, ic)
        nb = (icone_adresse(b, ic + 1) - a) // 4
        tuile = bytes([0x00, COULEUR_VALEUR, 0x80 | PLANCHE_VAL, g])
        patchs.append(remplace(b, a, mot(b, a, 4 * nb), tuile * nb, f'pictogramme {ic:#06x} → valeur « {motv} » (planche 4, glyphe {g:#x})'))
    off = GLYPHES - BASE
    assert b[off:off + len(neuf)] == b'\xff' * len(neuf)
    patchs.insert(0, {'offset': hex(off), 'avant': {'hex': b[off:off + len(neuf)].hex()}, 'apres': {'hex': bytes(neuf).hex()},
                      'texte': f'planche 4 (valeurs 80 × 40) recopiée et complétée : {n0} glyphes d\'origine + {len(VALEURS_ECRITES)} mots'})
    patchs.insert(1, remplace(b, desc + 8, struct.pack('>I', donnees), struct.pack('>I', GLYPHES),
                              'descripteur de la planche 4 : données vers la copie complétée'))
    return patchs


def etape_menus(b):
    lieu = disposition()
    s = code_menus(lieu)
    code = s.octets()
    lab = s.labels
    L = {k: v + RAM for k, v in lieu.items()}
    patchs = []
    off = CODE - BASE
    assert b[off:off + len(code)] == b'\xff' * len(code)
    assert CODE + len(code) <= TEXTES
    patchs.append({'offset': hex(off), 'avant': {'hex': b[off:off + len(code)].hex()}, 'apres': {'hex': code.hex()},
                   'texte': f'code ajouté ({len(code)} octets) : entrée de PRISE DE VUE, écrans Programme, ISO auto, '
                            'Marche, Si trop sombre, ISO mini, Menus'})

    A = {k: 0x4000 | v for k, v in AIDE.items()}
    # données dans la zone recyclée
    o = mot(b, PDV_ENTREES_ORIG, 96)
    ent = [o[16 * i:16 * i + 16] for i in range(6)]
    pdv = (ent[0]
           + entree(0xFFFF, ID['programme'], A['programme'], 4, N['programme'], L['prog'])
           + entree(0xFFFF, 0x0074, A['isoauto'], 4, N['isoauto'], L['iso'])
           + ent[1] + ent[3] + ent[2] + ent[5])
    prog = entete(ID['programme'], 0xFFFF, ATTR_CHOIX, 6, ECRAN_PROG, PDV_HDR + RAM, POS_HAUT, L['prog'] + 0x20)
    for i, k in enumerate(('standard', 'rapide', 'portrait', 'street', 'profondeur', 'pique')):
        prog += entree(0xFFFF, ID[k], A['programme'], 0, N['prog0'] + i, 0)
    # ISO auto (C4) : marche et réglages, valeur à droite (f6 = 5 : pictogramme affiché)
    iso = entete(0x0074, 0xFFFF, ATTR_VALEURS, 5, ECRAN_ISO, PDV_HDR + RAM, POS_HAUT, L['iso'] + 0x20)
    iso += entree(0x80AB, 0x0074, A['isoauto'], 5, N['marche'], L['marche'])
    iso += entree(0x8036, 0x01F8, A['isomini'], 5, N['iso_mini'], ISO_SENS + RAM)
    iso += entree(0x803C, 0x013F, 0x4082, 5, N['iso_maxi'], ISO_MAXI + RAM)
    iso += entree(0x80BE, 0x0140, 0x4047, 5, N['iso_vitesse'], ISO_VITESSE + RAM)
    iso += entree(ICONES_SOMBRE[0], ID['sombre'], A['sombre'], 5, N['sombre'], L['sombre'])
    iso += bytes(16)
    # fil d'Ariane identique dans les sous-écrans de l'ISO auto (C11) : titre ISO auto, sous-titre
    sombre = entete(0x0074, ID['sombre'], ATTR_CHOIX, 3, ECRAN_SOMBRE, L['iso'], POS_SOUS, L['sombre'] + 0x20)
    for i, k in enumerate(('s_vitesse', 's_iso', 's_sous')):
        sombre += entree(0xFFFF, ID[k], A['sombre'], 0, N['sombre0'] + i, 0)
    valeurs = bytes(16)                  # case réservée (ex-valeurs rangées, plus lue depuis la V1)
    zone = pdv + prog + iso + sombre + valeurs
    assert len(zone) == sum((7 * 16, 0x80, 0x80, 0x50, 16))
    za = ZONE[0]
    patchs.append({'offset': hex(za - BASE), 'avant': {'hex': mot(b, za, len(zone)).hex()}, 'apres': {'hex': zone.hex()},
                   'texte': 'nouvelles listes (PRISE DE VUE 7 entrées, Programme, ISO auto, Si trop sombre) et valeurs rangées, '
                            'à la place des listes « Mon menu › Choisir les rubriques » Retouche et Configuration'})
    marche = entete(0x0074, ID['marche'], ATTR_CHOIX, 2, ECRAN_MARCHE, L['iso'], POS_SOUS, L['marche'] + 0x20)
    marche += entree(0xFFFF, 0x0089, A['isoauto'], 0, N['iso_non'], 0)
    marche += entree(0xFFFF, 0x008A, A['isoauto'], 0, N['iso_oui'], 0)
    za = lieu['marche']
    patchs.append({'offset': hex(za - BASE), 'avant': {'hex': mot(b, za, len(marche)).hex()}, 'apres': {'hex': marche.hex()},
                   'texte': 'écran ISO auto › Marche (OFF, ON), à la place de la liste « Mon menu › Choisir les rubriques » Réglages perso'})

    # en-tête PRISE DE VUE : 7 lignes visibles (positions du menu Configuration) ; la liste et les
    # compteurs sont posés par pdv_entree à chaque affichage
    patchs.append(remplace(b, PDV_HDR + 0x18, struct.pack('>I', 0x15C4A0 + RAM), struct.pack('>I', POS_7),
                           'PRISE DE VUE : positions à 7 lignes'))
    patchs.append(remplace(b, PDV_HDR + 0x1C, struct.pack('>I', PDV_ENTREES_ORIG + RAM), struct.pack('>I', L['pdv']),
                           'PRISE DE VUE : nouvelle liste d\'entrées'))
    patchs.append(remplace(b, PDV_HDR + 0x08, struct.pack('>HH', 6, 6), struct.pack('>HH', 7, 7),
                           'PRISE DE VUE : 7 entrées'))
    # FUN_0014385c recompte PRISE DE VUE à chaque passage (menu Complet ou Simple : 6, constante) et
    # écrasait le 7 de pdv_entree : Réduction du bruit était affichée mais inaccessible (vu dans
    # l'émulateur pendant la passe critique). La boucle qui suit marque les entrées de la liste
    # (+0x1C, notre liste à 7 dès le démarrage).
    for a in (0x143888, 0x143898):
        patchs.append(remplace(b, a, bytes.fromhex('c060'), bytes.fromhex('c070'),
                               f'FUN_0014385c ({a:#x}) : LDI:8 #6 → #7, PRISE DE VUE compte 7 entrées'))
    # parents : ISO mini, ISO maxi, Vitesse mini reviennent dans le nouvel ISO auto
    for hdr, ancien, nom in ((ISO_SENS, PDV_HDR + RAM, 'ISO mini'), (ISO_MAXI, 0x15A910 + RAM, 'ISO maxi'),
                             (ISO_VITESSE, 0x15A910 + RAM, 'Vitesse mini')):
        patchs.append(remplace(b, hdr + 0x14, struct.pack('>I', ancien), struct.pack('>I', L['iso']),
                               f'{nom} : retour vers le nouvel écran ISO auto'))
    # ISO maxi : 3 choix serrés sous le sous-titre, sans ligne vide entre eux (C13) ; Vitesse mini
    # garde les siennes (6 lignes depuis y 71, liste qui défile)
    patchs.append(remplace(b, ISO_MAXI + 0x18, struct.pack('>I', 0x15C510 + RAM), struct.pack('>I', POS_SOUS),
                           'ISO maxi : choix serrés sous le sous-titre'))
    # Réduction du bruit : ses 2 choix sous le titre, sans ligne vide (C13)
    patchs.append(remplace(b, 0x1598C0 + 0x18, struct.pack('>I', 0x15C578 + RAM), struct.pack('>I', POS_HAUT),
                           'Réduction du bruit : positions de Préréglage'))
    # ISO mini (C11, C12, C13) : titre ISO auto / sous-titre ISO mini ; liste à partir de 200, 4 entrées
    patchs.append(remplace(b, ISO_SENS, struct.pack('>HH', 0x01F8, 0xFFFF), struct.pack('>HH', 0x0074, 0x01F8),
                           'ISO mini : titre « ISO auto », sous-titre « ISO mini »'))
    patchs.append(remplace(b, ISO_SENS + 8, struct.pack('>HH', 6, 6), struct.pack('>HH', 4, 4),
                           'ISO mini : 4 entrées (ni Automatique ni HI 1)'))
    patchs.append(remplace(b, ISO_SENS + 0x18, struct.pack('>II', 0x15C520 + RAM, 0x159980 + RAM),
                           struct.pack('>II', POS_SOUS, 0x159990 + RAM),
                           'ISO mini : choix serrés sous le sous-titre, liste à partir de l\'entrée 200'))

    # écrans recyclés (70 à 73 : « Mon menu › Choisir les rubriques »)
    for ecran, entree_f, action in ((ECRAN_PROG, lab['prog_entree'], 0x130EE4),
                                    (ECRAN_ISO, lab['iso_entree'], 0x130EE4),
                                    (ECRAN_SOMBRE, lab['sombre_entree'], 0x130EE4),
                                    (ECRAN_MARCHE, lab['marche_entree'], 0x130EE4)):
        a = TBL_ECRANS + 12 * ecran
        patchs.append(remplace(b, a, mot(b, a, 12), struct.pack('>HHII', 0x9808, 0, entree_f, action),
                               f'écran {ecran} : fonctions d\'entrée et d\'action du nouveau menu'))
    # écran 14 (PRISE DE VUE) : notre entrée, qui appelle celle d'origine
    a = TBL_ECRANS + 12 * 14 + 4
    patchs.append(remplace(b, a, struct.pack('>I', 0x143B46), struct.pack('>I', lab['pdv_entree']),
                           'écran 14 (PRISE DE VUE) : fonction d\'entrée enveloppée'))
    a = TBL_ECRANS + 12 * ECRAN_ISO_SENS + 4
    patchs.append(remplace(b, a, struct.pack('>I', ISO_SENS_ENTREE), struct.pack('>I', lab['isomini_entree']),
                           'écran 32 (ISO mini) : fonction d\'entrée enveloppée (liste réduite)'))
    a = TBL_ECRANS + 12 * ECRAN_CSM + 4
    patchs.append(remplace(b, a, struct.pack('>I', 0x13A254), struct.pack('>I', lab['csm_entree']),
                           'écran 68 (Menus) : surbrillance sur l\'unique entrée Complet'))

    # enregistrements des numéros d'entrée recyclés : +0 état, +2 message, +4 drapeaux, +8 fonction
    def rec(n, etat, msg, f, texte):
        a = TBL_N + 12 * n
        return remplace(b, a, mot(b, a, 12), struct.pack('>HHHHI', etat, msg, 1, 0, f), texte)
    patchs.append(rec(N['programme'], 8, 0xFFFF, ENTREE_SOUS_MENU, 'entrée Programme → sous-menu'))
    patchs.append(rec(N['isoauto'], 8, 0xFFFF, ENTREE_SOUS_MENU, 'entrée ISO auto → sous-menu'))
    for i in range(6):
        patchs.append(rec(N['prog0'] + i, 0xA, 0x604A, lab['prog_choix'], f'Programme {i} : ranger le choix'))
    patchs.append(rec(N['iso_non'], 0xA, 0x604A, lab['iso_choix'], 'ISO auto OFF'))
    patchs.append(rec(N['iso_oui'], 0xA, 0x604A, lab['iso_choix'], 'ISO auto ON'))
    for k in ('marche', 'iso_mini', 'iso_maxi', 'iso_vitesse', 'sombre'):
        patchs.append(rec(N[k], 8, 0xFFFF, ENTREE_SOUS_MENU, f'{k} → sous-menu'))
    for i in range(3):
        patchs.append(rec(N['sombre0'] + i, 0xA, 0x604A, lab['sombre_choix'], f'Si trop sombre {i} : ranger le choix'))

    patchs += pictos_valeurs(b)

    # Menus (C5) : « Mon menu » et « Simple » retirés, la liste part de Complet (1 entrée)
    patchs.append(remplace(b, CSM_CONFIG + 8, struct.pack('>HH', 3, 3), struct.pack('>HH', 1, 1),
                           'Menus : une seule option, Complet (Simple et Mon menu retirés)'))
    patchs.append(remplace(b, CSM_CONFIG + 0x18, struct.pack('>II', 0x15C570 + RAM, 0x15B870 + RAM),
                           struct.pack('>II', POS_HAUT, 0x15B880 + RAM),
                           'Menus : positions de Préréglage, liste à partir de Complet'))
    return patchs


# ---------------------------------------------------------------- onglets en bandeau (étape 5)

# Maquette : les onglets en mots dans un bandeau en haut, les lignes en pleine largeur. Nikon
# dessine la colonne des onglets à gauche (x < 0x28 unités ; 1 unité = 2 points de l'écran
# 640 × 480) et le menu à droite. L'étape 5 détourne 6 primitives de dessin : tant qu'un écran à
# onglets est affiché, ce qui se dessine entre x = 0x28 et 0xF0 unités glisse de 0x20 unités à
# gauche ; ce qui est à droite (valeurs, barre de défilement) ne bouge pas, une case qui déborde
# à droite s'élargit d'autant. Le fond part de x = 0, le filet vertical de la colonne disparaît,
# l'aide « ? » monte en haut à droite. Le titre (FUN_00146f44), la colonne (onglets_dessiner) et
# l'onglet actif (FUN_0014777c) sont remplacés par le bandeau : mots dessinés d'avance en DIN
# Condensed Bold, cadre ouvert autour de l'onglet choisi, filet de base ; sous le bandeau, le
# titre du sous-écran en capitales (petite police DIN tracée lettre par lettre).
BANDEAU = 0x40C000               # code (place libre, après les glyphes de valeurs qui finissent à 0x403520)
BANDEAU_DONNEES = 0x40D000       # données : mots, cadres, petite police
FIN_LIBRE = 0x40FFFE             # CRC du fichier juste après
VARS = 0x83CE75CC                # case « valeurs » de l'étape 4 (16 octets à zéro en RAM, plus lus depuis la V1)
DIALOGUE, PROF, MUET, SECOURS = VARS + 2, VARS + 3, VARS + 4, VARS + 5
ECRANS_SECOURS = (104, 105, 106)  # CONFIG › Version du firmware (105) › Version/MAJ (106) › mise à jour (104)
MODE_UI = 0x83CED23A             # u16 : 5 = menus
ONGLET = 0x83CE3FE8              # octet : 0 VISU, 1 PRISE DE VUE, 2 PERSO, 3 CONFIG, 4 Retouche
ATTR_ECRANS = 0x83CE2130         # 12 octets par écran : +0 attributs (0x8000 = à onglets, 0x1000 = curseur sur les onglets)
NB_ECRANS = 170
STYLE = 0x4C1C2                  # FUN_0004c1c2 : indice de style des tables de couleurs
TRACER = 0x7BD56                 # osd_tracerBloc(x, y, données, bits par ligne ; pile : hauteur, Y, Cb, Cr)
TABLES_TEXTE = 0x83CE3FEC        # pointeurs des tables D, C, B, A (bits 13-15 de l'identifiant)
T_FOND, T_TEXTE, T_GRIS, T_TITRE = 0xD8724, 0xD8744, 0xD8748, 0xD8750   # couleurs par style (demi-mots)
L_U, S_U, D_U = 0x28, 0xF0, 0x20  # décalage : x de L à S (unités) → x − D
AIDE_X, AIDE_Y = 0x122, 2        # case de l'aide « ? » (0x1B × 0x1B unités), d'origine en (6, 0xCF)
BANDEAU_DROITE = 0x120           # le bandeau s'arrête avant la case de l'aide
MOTS = [(1, 'PRISE DE VUE'), (0, 'VISU'), (2, 'PERSO'), (3, 'CONFIG')]   # (onglet Nikon, mot), ordre du bandeau
MOT_X0, MOT_ECART, MOT_Y, MOT_H, MOT_CAP = 24, 32, 8, 28, 24   # points ; capitales aux lignes 2 à 25
CADRE_Y, FILET_Y = 4, 40         # haut du cadre, filet de base (points)
SOUS_X, SOUS_Y, GL_H, GL_CAP, GL_HAUT = 24, 48, 28, 17, 5      # titre du sous-écran : capitales lignes 5 à 21
GLYPHES_SOUS = (' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' + "%'()+,-./=?:!&" + 'ÀÂÇÉÈÊÎÔÙÑ×')
ACCENTS_SOUS = {0x07: 'À', 0x19: 'À', 0x1B: 'Â', 0x0D: 'Ç', 0x1F: 'Ç', 0x0F: 'É', 0x21: 'É', 0x20: 'È',
                0x22: 'Ê', 0x26: 'Î', 0x2A: 'Ô', 0x2D: 'Ù', 0x27: 'Ñ', 0x15: '×', 0x12: 'O', 0x0A: 'A'}
# fonctions détournées : adresse, octets d'entrée déplacés dans le tremplin (aucun saut du
# firmware ne vise l'intérieur de ces octets, vérifié)
CROCHETS = {
    'rect': (0x7D72A, '8f30c02d01409b010280'),          # rectangle_remplir(rect unités, couleur)
    'degrade': (0x7E0A0, '8ff017810f189f88000d87c3'),   # dégradé (rect unités, couleurs)
    'cde2': (0x7CDE2, '8e098ff017810f08'),              # texte : pile 8 mots, x en points au mot 2
    'd00e': (0x7D00E, '8e0d8ff017810f08'),              # texte : pile 6 mots, x en points au mot 1
    'icone': (0x7C904, '8e0f8ff017810f08'),             # icone_dessiner : x, y en points dans R6, R7 ; pile 2 mots
    'f5e4': (0x7F5E4, '8e038ff017810f07'),              # texte de FUN_0013e58c : pile 5 mots, x en unités au mot 1
    'titre': (0x146F44, '8e0c8ff017810f09'),            # titre du menu
    'onglets': (0x146C48, '8ff017810f069f8c83ce3fe806ca'),   # onglets_dessiner
    'onglet_actif': (0x14777C, '8fe017810f019f8c83ce3fe806c9'),   # onglet actif, R4 = 0 curseur dessus, 1 dans la liste
    'message1': (0x149220, '170817810f018b48'),         # messages (« pas de carte »…) : dessinés sans décalage
    'message2': (0x14947C, '170817810f018b48'),
}


def rendu_ligne(texte, cap, haut, h, largeur=None):
    """Texte en DIN Condensed Bold, capitales de `cap` points à partir de la ligne `haut`, 1 bit
    par point (bit fort à gauche), largeur arrondie à l'octet. Rend (avance, bits par ligne, octets)."""
    from PIL import Image, ImageDraw, ImageFont
    import icones
    taille = 8
    while True:
        f = ImageFont.truetype(icones.POLICE, taille)
        x0, y0, x1, y1 = f.getbbox('H')
        if y1 - y0 >= cap:
            break
        taille += 1
    avance = f.getlength(texte)
    w = largeur or (int(avance) + 2 + 7) // 8 * 8
    m = 16
    grand = Image.new('L', (w + 2 * m, h + 2 * m), 0)
    ImageDraw.Draw(grand).text((m + 1, m + haut - y0), texte, font=f, fill=255)
    im = grand.crop((m, m, m + w, m + h))
    seuil = lambda v: 255 if v >= 128 else 0  # noqa: E731
    assert grand.point(seuil).histogram()[255] == im.point(seuil).histogram()[255], \
        f'« {texte} » déborde de sa case'
    px = im.load()
    data = bytearray()
    for y in range(h):
        v = 0
        for x in range(w):
            v = v << 1 | (px[x, y] >= 128)
        data += v.to_bytes(w // 8, 'big')
    return avance, w, bytes(data)


def pair(v):
    v = int(-(-v // 1))
    return v + (v & 1)


def donnees_bandeau():
    """Données à BANDEAU_DONNEES : mots (16 octets chacun : onglet, x, bits par ligne, hauteur,
    adresse du dessin, adresse du cadre), cadres (case du curseur puis 6 traits, en unités),
    tables de la petite police (ASCII, accents 0x81 xx, avances), glyphes 16 × 28, dessins des mots."""
    mots, x = [], MOT_X0
    for onglet, texte in MOTS:
        avance, w, data = rendu_ligne(texte, MOT_CAP, 2, MOT_H)
        la = pair(avance)
        mots.append({'onglet': onglet, 'texte': texte, 'x': x, 'la': la, 'w': w, 'data': data})
        x += la + MOT_ECART
    assert x - MOT_ECART + 12 < 2 * BANDEAU_DROITE, x
    u = lambda p: p // 2  # noqa: E731
    for m in mots:
        xa, la = m['x'], m['la']
        xl, xr = xa - 10, xa + la + 8
        m['cadre'] = [
            (u(xa - 6), u(CADRE_Y + 2), u(la + 12), u(FILET_Y - CADRE_Y - 4)),   # case du curseur
            (u(xl), u(CADRE_Y), 1, u(FILET_Y + 2 - CADRE_Y)),                  # trait gauche
            (u(xl), u(CADRE_Y), 3, 1),                                         # amorce gauche
            (u(xr), u(CADRE_Y), 1, u(FILET_Y + 2 - CADRE_Y)),                  # trait droit
            (u(xr) - 2, u(CADRE_Y), 3, 1),                                     # amorce droite
            (4, u(FILET_Y), u(xl) - 4, 1),                                     # filet à gauche
            (u(xr), u(FILET_Y), BANDEAU_DROITE - u(xr), 1),                    # filet à droite
        ]
    glyphes, avances = [], []
    for c in GLYPHES_SOUS:
        avance, w, data = rendu_ligne(c, GL_CAP, GL_HAUT, GL_H, largeur=16)
        glyphes.append(data)
        avances.append(round(avance) + (2 if c == ' ' else 0))
    asc = bytearray(b'\xff' * 128)
    for c in range(0x20, 0x7F):
        ch = {'`': "'"}.get(chr(c), chr(c).upper())
        if ch in GLYPHES_SOUS:
            asc[c] = GLYPHES_SOUS.index(ch)
    acc = bytearray(b'\xff' * 64)
    for code, ch in ACCENTS_SOUS.items():
        acc[code] = GLYPHES_SOUS.index(ch)

    a = {'tab_mots': BANDEAU_DONNEES}
    a['cadres'] = a['tab_mots'] + 16 * len(mots)
    a['asc'] = a['cadres'] + 7 * 8 * len(mots)
    a['acc'] = a['asc'] + 128
    a['avances'] = a['acc'] + 64
    a['glyphes'] = a['avances'] + (len(avances) + 3) // 4 * 4
    a['dessins'] = a['glyphes'] + GL_H * 2 * len(glyphes)
    blob = bytearray()
    p = a['dessins']
    dessins = bytearray()
    for k, m in enumerate(mots):
        m['adresse'] = p + len(dessins)
        dessins += m['data']
        dessins += b'\x00' * (-len(dessins) % 4)
    for k, m in enumerate(mots):
        blob += struct.pack('>BBHHHII', m['onglet'], 0, m['x'], m['w'], MOT_H, m['adresse'], a['cadres'] + 56 * k)
    for m in mots:
        for r in m['cadre']:
            assert all(0 <= v < 0x200 for v in r) and r[2] > 0 and r[3] > 0, r
            blob += struct.pack('>HHHH', *r)
    blob += asc + acc + bytes(avances) + b'\x00' * (-len(avances) % 4)
    blob += b''.join(glyphes) + dessins
    assert BANDEAU_DONNEES + len(blob) == a['dessins'] + len(dessins)
    return bytes(blob), a, mots


def code_bandeau(a):
    """Code ajouté à BANDEAU : garde, enveloppes des primitives, bandeau, tremplins."""
    s = Asm(BANDEAU)

    # actif : R0 = 1 si un écran à onglets est affiché (décaler), 2 si muet (colonne Nikon
    # redessinée pour ses effets seulement), 0 sinon ; R4-R7 intacts
    s.label('actif')
    s.ldi32(VARS, 12)
    s.ldi8(MUET - VARS, 13); s.ldub13(12, 0); s.cmpi(0, 0); s.b('eq', 'ac_1')
    s.ldi8(2, 0); s.ret()
    s.label('ac_1')
    s.ldi8(PROF - VARS, 13); s.ldub13(12, 0); s.cmpi(0, 0); s.b('ne', 'ac_non')       # appel imbriqué
    s.ldi8(DIALOGUE - VARS, 13); s.ldub13(12, 0); s.cmpi(0, 0); s.b('ne', 'ac_non')   # message en cours
    s.ldi32(MODE_UI, 12); s.lduh(12, 0); s.cmpi(5, 0); s.b('ne', 'ac_non')
    s.ldi32(ONGLET, 12); s.ldub(12, 0); s.cmpi(3, 0); s.b('hi', 'ac_non')
    s.ldi32(MENU_COURANT, 12); s.ld(12, 1)
    s.ldi32(0x83CE0000, 0); s.mov(1, 2); s.sub(0, 2); s.ldi20(0x20000, 0); s.cmp(0, 2); s.b('nc', 'ac_non')
    s.ldi8(0x12, 13); s.lduh13(1, 0)
    s.ldi8(NB_ECRANS, 2); s.cmp(2, 0); s.b('nc', 'ac_non')
    s.mov(0, 2); s.lsl(1, 2); s.add(0, 2); s.lsl(2, 2)
    s.ldi32(ATTR_ECRANS, 13); s.lduh13(2, 0)
    s.ldi20(0x8000, 2); s.and_(2, 0); s.b('eq', 'ac_non')
    s.ldi8(1, 0); s.ret()
    s.label('ac_non')
    s.ldi8(0, 0); s.ret()

    # etat : R4 = 1 si le curseur est dans la liste, 0 s'il est sur les onglets (attribut 0x1000 de l'écran)
    s.label('etat')
    s.ldi32(MENU_COURANT, 12); s.ld(12, 1); s.ldi8(0x12, 13); s.lduh13(1, 0)
    s.mov(0, 2); s.lsl(1, 2); s.add(0, 2); s.lsl(2, 2)
    s.ldi32(ATTR_ECRANS, 13); s.lduh13(2, 4)
    s.lsr(12, 4); s.ldi8(1, 0); s.and_(0, 4); s.ret()

    # encre : R0 = entrée de la palette 0xD87C3 → Y, Cb, Cr dans les mots 1 à 3 de la pile de l'appelant
    s.label('encre')
    s.mov(0, 1); s.lsl(1, 1); s.add(0, 1); s.ldi32(PAL3, 12); s.add(12, 1)
    for k, off in enumerate((4, 8, 12)):
        s.ldub(1, 2); s.ldi8(off, 13); s.st13(2, 15)
        if k < 2:
            s.addi(1, 1)
    s.ret()

    def role(table, ri=0):  # couleur du rôle pour le style courant (R10 = style × 2)
        s.ldi32(table, 12); s.mov(10, 13); s.lduh13(12, ri)

    def rect_const(r, table):
        for off, v in zip((0, 2, 4, 6), r):
            s.ldi(v, 0); s.ldi8(16 + off, 13); s.sth13(0, 15)
        s.ldi8(16, 0); s.mov(15, 4); s.add(0, 4)
        role(table, 5)
        s.appel('tr_rect')

    # bandeau(R4 = 0 si le curseur est sur les onglets, 1 s'il est dans la liste ; c'est l'attribut
    # 0x1000 de l'écran, que FUN_00131f8a efface en changeant d'onglet). Pile : 0-15 arguments de osd_tracerBloc,
    # 16-23 rectangle, 24 état, 28 glyphe ou compteur
    s.label('bandeau')
    s.push_rp(); s.push(8); s.push(9); s.push(10); s.push(11)
    s.addsp(-40)
    s.ldi8(24, 13); s.st13(4, 15)
    s.appel(STYLE); s.lsl(1, 4); s.mov(4, 10)
    s.ldi32(ONGLET, 12); s.ldub(12, 9)
    u_bas = (FILET_Y + 4) // 2                  # bandeau : y 0 à 43 points ; titre du sous-écran : 44 à 75
    rect_const((0, 0, BANDEAU_DROITE, u_bas), T_FOND)
    s.ldi32(a['tab_mots'], 8)
    s.label('bm_mot')
    s.ldub(8, 0); s.cmp(9, 0); s.b('ne', 'bm_inactif')
    s.ldi8(24, 13); s.ld13(15, 0); s.cmpi(0, 0); s.b('ne', 'bm_normal')
    s.ldi8(12, 13); s.ld13(8, 4); role(T_TITRE, 5); s.appel('tr_rect')     # curseur sur les onglets : case pleine
    role(T_FOND); s.b('ra', 'bm_dessin')
    s.label('bm_normal')
    role(T_TEXTE); s.b('ra', 'bm_dessin')
    s.label('bm_inactif')
    role(T_GRIS)
    s.label('bm_dessin')
    s.appel('encre')
    s.ldi8(6, 13); s.lduh13(8, 0); s.st(0, 15)
    s.ldi8(2, 13); s.lduh13(8, 4)
    s.ldi8(MOT_Y, 5)
    s.ldi8(8, 13); s.ld13(8, 6)
    s.ldi8(4, 13); s.lduh13(8, 7)
    s.appel(TRACER)
    s.ldub(8, 0); s.cmp(9, 0); s.b('ne', 'bm_suivant')
    s.ldi8(12, 13); s.ld13(8, 11); s.addi(8, 11)                            # cadre : 6 traits
    s.ldi8(6, 0); s.ldi8(28, 13); s.st13(0, 15)
    s.label('bm_cadre')
    s.mov(11, 4); role(T_TITRE, 5); s.appel('tr_rect')
    s.addi(8, 11)
    s.ldi8(28, 13); s.ld13(15, 0); s.add2(-1, 0); s.st13(0, 15); s.b('ne', 'bm_cadre')
    s.label('bm_suivant')
    s.addi(15, 8); s.addi(1, 8)
    s.ldi32(a['tab_mots'] + 16 * len(MOTS), 0); s.cmp(0, 8); s.b('ne', 'bm_mot')
    # titre du sous-écran (menu dont le parent, +0x14, n'est pas nul)
    rect_const((0, u_bas, BANDEAU_DROITE, 38 - u_bas), T_FOND)     # jusqu'à 75 : la 1re ligne commence à 76 (0x26 unités)
    s.ldi32(MENU_COURANT, 12); s.ld(12, 0)
    s.ldi8(0x14, 13); s.ld13(0, 1); s.cmpi(0, 1); s.b('eq', 'bm_fin')
    s.lduh(0, 1); s.ldi20(0xFFFF, 2); s.cmp(2, 1); s.b('eq', 'bm_fin')
    s.mov(1, 2); s.lsr(13, 2); s.lsl(2, 2); s.ldi32(TABLES_TEXTE, 12); s.add(12, 2); s.ld(2, 2)
    s.ldi20(0x1FFF, 3); s.and_(3, 1); s.lsl(2, 1); s.add(1, 2)
    s.ld(2, 8); s.addi(4, 2); s.ld(2, 9)                                    # R8 début, R9 fin de la chaîne
    s.ldi8(SOUS_X, 11)
    s.label('bs_car')
    s.cmp(9, 8); s.b('nc', 'bm_fin')
    s.ldub(8, 0); s.addi(1, 8)
    s.cmpi(0xF, 0); s.b('ne', 'bs_1')
    s.addi(1, 8); s.b('ra', 'bs_car')                                      # 0x0F n : choix de police
    s.label('bs_1')
    s.cmpi(0xA, 0); s.b('ne', 'bs_2')
    s.ldi8(0x20, 0); s.b('ra', 'bs_ascii')                                 # retour à la ligne : espace
    s.label('bs_2')
    s.ldi8(0x81, 1); s.cmp(1, 0); s.b('ne', 'bs_3')
    s.ldub(8, 0); s.addi(1, 8); s.ldi8(0x3F, 1); s.and_(1, 0)               # accent 0x81 xx
    s.ldi32(a['acc'], 12); s.mov(0, 13); s.ldub13(12, 0); s.b('ra', 'bs_glyphe')
    s.label('bs_3')
    s.ldi8(0x80, 1); s.cmp(1, 0); s.b('c', 'bs_ascii')
    s.addi(1, 8); s.b('ra', 'bs_car')                                      # autre planche (2 octets) : sautée
    s.label('bs_ascii')
    s.ldi32(a['asc'], 12); s.mov(0, 13); s.ldub13(12, 0)
    s.label('bs_glyphe')
    s.ldi8(0xFF, 1); s.cmp(1, 0); s.b('eq', 'bs_car')
    s.ldi8(28, 13); s.st13(0, 15)
    role(T_GRIS); s.appel('encre')
    s.ldi8(GL_H, 0); s.st(0, 15)
    s.ldi8(28, 13); s.ld13(15, 0)
    s.mov(0, 6); s.lsl(6, 6); s.mov(0, 1); s.lsl(3, 1); s.sub(1, 6)          # 56 octets par glyphe
    s.ldi32(a['glyphes'], 12); s.add(12, 6)
    s.mov(11, 4); s.ldi8(SOUS_Y, 5); s.ldi8(16, 7)
    s.appel(TRACER)
    s.ldi8(28, 13); s.ld13(15, 0); s.ldi32(a['avances'], 12); s.mov(0, 13); s.ldub13(12, 0); s.add(0, 11)
    s.ldi20(2 * BANDEAU_DROITE - 16, 0); s.cmp(0, 11); s.b('lt', 'bs_car')
    s.label('bm_fin')
    s.addsp(40); s.pop(11); s.pop(10); s.pop(9); s.pop(8); s.pop_rp(); s.ret()

    def sas(nom):
        """Voie de secours (mise à jour du firmware, écrans 104 à 106) : la fonction d'origine telle
        quelle, avant tout le reste. Ne servent que R0, R1, R12, R13 et les drapeaux (libres à l'entrée
        d'une fonction), rien n'est écrit sur la pile ; seul le verrou SECOURS (octet à nous) change. Le
        verrou, posé sur ces écrans, tient jusqu'au retour sur l'écran de tête d'un onglet (parent nul) :
        tout ce qui est dessiné entre-temps passe aussi tel quel."""
        s.ldi32(MENU_COURANT, 12); s.ld(12, 1)
        s.ldi32(0x83CE0000, 0); s.mov(1, 13); s.sub(0, 13); s.ldi20(0x20000, 0); s.cmp(0, 13)
        s.ldi32(SECOURS, 12)
        s.b('nc', nom + '_hors')                                          # pas un menu
        s.ldi8(0x12, 13); s.lduh13(1, 0)                                  # numéro d'écran
        s.ldi8(ECRANS_SECOURS[0], 13); s.cmp(13, 0); s.b('c', nom + '_menu')
        s.ldi8(ECRANS_SECOURS[-1], 13); s.cmp(13, 0); s.b('hi', nom + '_menu')
        s.ldi8(1, 13); s.stb(13, 12); s.b('ra', nom + '_direct')           # écran de secours : verrou posé
        s.label(nom + '_menu')
        s.ldub(12, 13); s.cmpi(0, 13); s.b('eq', nom + '_normal')
        s.ldi8(0x14, 13); s.ld13(1, 13); s.cmpi(0, 13); s.b('ne', nom + '_direct')   # verrou, sous-écran
        s.ldi8(0, 13); s.stb(13, 12); s.b('ra', nom + '_normal')           # écran de tête : verrou levé
        s.label(nom + '_hors')
        s.ldub(12, 13); s.cmpi(0, 13); s.b('eq', nom + '_normal')
        s.label(nom + '_direct')
        s.ldi32('tr_' + nom, 12); s.jmp_r(12)
        s.label(nom + '_normal')

    # enveloppes des primitives : voie de secours → tremplin ; rien à faire → tremplin ; muet → retour ;
    # sinon copie des arguments de pile, décalage, appel du tremplin (PROF = 1 : les appels imbriqués
    # passent tels quels)
    def enveloppe(nom, k, carte, extra=0):
        s.label('env_' + nom)
        sas(nom)
        s.push_rp()
        s.appel('actif')
        s.cmpi(1, 0); s.b('eq', nom + '_carte')
        s.cmpi(2, 0); s.b('eq', nom + '_muet')
        s.pop_rp(); s.ldi32('tr_' + nom, 12); s.jmp_r(12)
        s.label(nom + '_muet')
        s.pop_rp(); s.ret()
        s.label(nom + '_carte')
        F = 4 * k + extra
        if F:
            s.addsp(-F)
        for i in range(k):
            s.ldi8(F + 4 + 4 * i, 13); s.ld13(15, 0); s.ldi8(4 * i, 13); s.st13(0, 15)
        carte(nom)
        s.ldi32(PROF, 12); s.ldi8(1, 0); s.stb(0, 12)
        s.appel('tr_' + nom)
        s.ldi32(PROF, 12); s.ldi8(0, 0); s.stb(0, 12)
        s.label(nom + '_retour')
        if F:
            s.addsp(F)
        s.pop_rp(); s.ret()

    def decaler(r, fin, bas, haut, d):  # registre r : x de [bas, haut) → x − d
        s.ldi(bas, 2); s.cmp(2, r); s.b('lt', fin)
        s.ldi(haut, 2); s.cmp(2, r); s.b('ge', fin)
        s.ldi(d, 2); s.sub(2, r)
        s.label(fin)

    def mot_pile(i, bas, haut, d):
        def carte(nom):
            s.ldi8(4 * i, 13); s.ld13(15, 1)
            decaler(1, nom + '_d', bas, haut, d)
            s.ldi8(4 * i, 13); s.st13(1, 15)
        return carte

    def carte_rect(special):
        def carte(nom):
            for off in (0, 2, 4, 6):                  # copie du rectangle (celui de l'appelant reste intact)
                s.ldi8(off, 13); s.lduh13(4, 0); s.sth13(0, 15)
            s.mov(15, 4)
            s.ldi8(0, 13); s.lduh13(4, 0); s.extsh(0)
            s.ldi8(4, 13); s.lduh13(4, 1); s.extsh(1)
            if special:
                s.ldi8(0x26, 2); s.cmp(2, 0); s.b('ne', nom + '_s1')     # filet vertical (0x26, 0, 2, 0xF0)
                s.ldi8(6, 13); s.lduh13(4, 3); s.ldi8(0xF0, 2); s.cmp(2, 3); s.b('eq', nom + '_retour')
                s.label(nom + '_s1')
                s.cmpi(6, 0); s.b('ne', nom + '_s2')                     # case de l'aide (6, 0xCF)
                s.ldi8(2, 13); s.lduh13(4, 3); s.ldi8(0xCF, 2); s.cmp(2, 3); s.b('ne', nom + '_s2')
                s.ldi(AIDE_X, 0); s.ldi8(0, 13); s.sth13(0, 4)
                s.ldi(AIDE_Y, 0); s.ldi8(2, 13); s.sth13(0, 4)
                s.b('ra', nom + '_fini')
                s.label(nom + '_s2')
            s.ldi8(L_U, 2); s.cmp(2, 0); s.b('ne', nom + '_g1')          # x = 0x28 : fond, part de 0
            s.add(2, 1); s.ldi8(0, 0); s.b('ra', nom + '_ecrit')
            s.label(nom + '_g1')
            s.b('lt', nom + '_fini')
            s.ldi8(S_U, 2); s.cmp(2, 0); s.b('ge', nom + '_fini')
            s.mov(0, 3); s.add(1, 3); s.ldi8(S_U, 2); s.cmp(2, 3); s.b('le', nom + '_g2')
            s.ldi8(D_U, 2); s.add(2, 1)                                  # déborde à droite : bord droit fixe
            s.label(nom + '_g2')
            s.ldi8(D_U, 2); s.sub(2, 0)
            s.label(nom + '_ecrit')
            s.ldi8(0, 13); s.sth13(0, 4); s.ldi8(4, 13); s.sth13(1, 4)
            s.label(nom + '_fini')
        return carte

    def carte_icone(nom):
        s.cmpi(12, 6); s.b('ne', 'ic_g')                                   # aide « ? » (12, 414) points
        s.ldi(414, 2); s.cmp(2, 7); s.b('ne', 'ic_g')
        s.ldi(2 * AIDE_X, 6); s.ldi(2 * AIDE_Y, 7); s.b('ra', 'ic_fin')
        s.label('ic_g')
        decaler(6, 'ic_fin', 2 * L_U, 2 * S_U, 2 * D_U)

    enveloppe('rect', 0, carte_rect(True), extra=8)
    enveloppe('degrade', 0, carte_rect(False), extra=8)
    enveloppe('cde2', 8, mot_pile(2, 2 * L_U, 2 * S_U, 2 * D_U))
    enveloppe('d00e', 6, mot_pile(1, 2 * L_U, 2 * S_U, 2 * D_U))
    enveloppe('icone', 2, carte_icone)
    enveloppe('f5e4', 5, mot_pile(1, L_U, S_U, D_U))

    for nom, apres in (('titre', ['etat']), ('onglets', ['muet', 'etat']), ('onglet_actif', [])):
        s.label('env_' + nom)
        sas(nom)
        s.push_rp(); s.appel('actif'); s.cmpi(1, 0); s.b('eq', nom + '_b')
        s.pop_rp(); s.ldi32('tr_' + nom, 12); s.jmp_r(12)
        s.label(nom + '_b')
        if 'muet' in apres:  # colonne Nikon redessinée sans rien tracer (ses calculs d'état restent)
            s.ldi32(MUET, 12); s.ldi8(1, 0); s.stb(0, 12)
            s.appel('tr_' + nom)
            s.ldi32(MUET, 12); s.ldi8(0, 0); s.stb(0, 12)
        if 'etat' in apres:
            s.appel('etat')
        s.appel('bandeau')
        s.pop_rp(); s.ret()

    for nom in ('message1', 'message2'):
        s.label('env_' + nom)
        sas(nom)
        s.push_rp()
        s.ldi32(DIALOGUE, 12); s.ldub(12, 0); s.push(0)
        s.ldi8(1, 0); s.stb(0, 12)
        s.appel('tr_' + nom)
        s.pop(1); s.ldi32(DIALOGUE, 12); s.stb(1, 12)
        s.pop_rp(); s.ret()

    for nom, (adr, dep) in CROCHETS.items():
        s.label('tr_' + nom)
        s.brut(bytes.fromhex(dep))
        s.ldi32(adr + len(dep) // 2, 12); s.jmp_r(12)
    return s


# navigation ▲▼ sur les onglets dans l'ordre du bandeau (PRISE DE VUE, VISU, PERSO, CONFIG) :
# 5 constantes de FUN_00131f8a (les 2 de l'étape 3, 0x13208E et 0x13218A, restent)
NAV_BANDEAU = [
    (0x132084, VISU, PDV, '▲ : test « sur VISU » → « sur PRISE DE VUE » (va à CONFIG, constante de l\'étape 3)'),
    (0x13209E, PDV, VISU, '▲ : test « sur PRISE DE VUE » → « sur VISU » (va à PRISE DE VUE)'),
    (0x132132, VISU, CONFIG, '▼ : test « sur VISU » → « sur CONFIG » (va à PRISE DE VUE)'),
    (0x13214C, PDV, VISU, '▼ : test « sur PRISE DE VUE » → « sur VISU » (va à PERSO)'),
    (0x132180, CONFIG, PDV, '▼ : test « sur CONFIG » → « sur PRISE DE VUE » (va à VISU, constante de l\'étape 3)'),
]


def etape_bandeau(b):
    blob, a, mots = donnees_bandeau()
    s = code_bandeau(a)
    code = s.octets()
    assert BANDEAU + len(code) <= BANDEAU_DONNEES, hex(BANDEAU + len(code))
    assert BANDEAU_DONNEES + len(blob) <= FIN_LIBRE, hex(BANDEAU_DONNEES + len(blob))
    patchs = []
    for adr, octets, texte in ((BANDEAU, code, 'code du bandeau : garde, enveloppes des primitives, bandeau, tremplins'),
                               (BANDEAU_DONNEES, blob, 'données du bandeau : mots PRISE DE VUE, VISU, PERSO, CONFIG '
                                                       '(DIN Condensed Bold), cadres, petite police des titres de sous-écran')):
        o = adr - BASE
        assert b[o:o + len(octets)] == b'\xff' * len(octets), hex(adr)
        patchs.append({'offset': hex(o), 'avant': {'hex': b[o:o + len(octets)].hex()}, 'apres': {'hex': octets.hex()},
                       'texte': texte})
    for nom, (adr, dep) in CROCHETS.items():
        n = len(dep) // 2
        saut = struct.pack('>HIH', 0x9F8C, s.labels['env_' + nom], 0x970C) + b'\x9f\xa0' * ((n - 8) // 2)
        patchs.append(remplace(b, adr, bytes.fromhex(dep), saut, f'entrée de {adr:#x} ({nom}) → enveloppe du bandeau'))
    for adr, avant, apres, texte in NAV_BANDEAU:
        patchs.append(remplace(b, adr, struct.pack('>I', avant), struct.pack('>I', apres), 'FUN_00131f8a, ' + texte))
    return patchs


# ---------------------------------------------------------------- style Graphique forcé (étape 6)

# Premier flash (octobre 2026) : le boîtier était réglé en Style écran infos Classique, qui choisit le jeu de
# couleurs 0 des menus et l'écran d'infos Classique ; le Pip-Boy n'avait recoloré que le jeu 1 (Graphique),
# celui de l'émulateur. Enquête : recherche/ecran-reel-composition.md. On force les deux en Graphique.
STYLE_COURANT = 0x4C1CE      # créneau du BEQ:D de style_courant (0x4C1C2) : LDI:8 #0,R4
INFOS_STYLE = 0x9B874        # FUN_0009b7ae : BLE (style ≤ 2 gardé) puis LDI:8 #0,R0 ; STB R0,@R9 (0x83CEE4BF)
FOND_JPEG = 0xDFBB2          # fond de l'écran d'infos Graphique : JPEG 640 × 480, 0x2602 octets (FUN_000a6d70)
FOND_LONGUEUR = 0x2602


def jpeg_segments(j):
    """Segments d'en-tête (marqueur compris) jusqu'au SOS, et les données compressées qui suivent."""
    i, segs = 2, []
    while True:
        m, n = j[i + 1], int.from_bytes(j[i + 2:i + 4], 'big')
        segs.append(j[i:i + 2 + n])
        if m == 0xDA:
            return segs, j[i + 2 + n:]
        i += 2 + n


def tables_huffman(segs):
    out = []
    for s in segs:
        if s[1] == 0xC4:
            k = 4
            while k < len(s):
                n = sum(s[k + 1:k + 17])
                out.append(s[k:k + 17 + n])
                k += 17 + n
    return out


def fond_noir(orig):
    """JPEG noir (Y 16, Cb Cr 128 : le noir de la palette) aux en-têtes de l'original, octet pour octet :
    même DQT, SOF0 (4:2:2), DHT, SOS ; seules les données compressées changent. Complété par des zéros
    après EOI jusqu'à 0x2602 octets, la longueur que le code passe au décodeur (inchangée)."""
    import io
    from PIL import Image
    j = mot(orig, FOND_JPEG, FOND_LONGUEUR)
    segs, _ = jpeg_segments(j)
    q = Image.open(io.BytesIO(j)).quantization
    bio = io.BytesIO()
    Image.new('YCbCr', (640, 480), tuple(ycc(*NOIR))).save(bio, 'JPEG', qtables=q, subsampling=1,
                                                          optimize=False, progressive=False)
    segs_p, scan = jpeg_segments(bio.getvalue())
    sof = [s for s in segs if s[1] == 0xC0]
    assert sof == [s for s in segs_p if s[1] == 0xC0] and segs[-1] == segs_p[-1], 'SOF ou SOS différent'
    assert tables_huffman(segs) == tables_huffman(segs_p), 'tables de Huffman différentes'
    neuf = j[:2] + b''.join(segs) + scan   # SOI + en-têtes d'origine + données
    assert neuf.endswith(b'\xff\xd9') and len(neuf) <= FOND_LONGUEUR
    return neuf + bytes(FOND_LONGUEUR - len(neuf)), len(neuf)


def etape_style(orig):
    neuf, n = fond_noir(orig)
    return [
        remplace(orig, STYLE_COURANT, bytes.fromhex('c004'), bytes.fromhex('c014'),
                 'style_courant (0x4C1C2) rend toujours 1 : menus dans le jeu de couleurs Graphique, celui du '
                 'Pip-Boy, quel que soit CONFIG › Style écran infos (créneau de délai : LDI:8 #0 → #1, '
                 'reste un LDI:8)'),
        remplace(orig, INFOS_STYLE, bytes.fromhex('ec02c000'), bytes.fromhex('9fa0c010'),
                 'écran d\'infos (FUN_0009b7ae) : style 0x83CEE4BF toujours 1, Graphique (BLE → NOP, '
                 'LDI:8 #0 → #1 ; aucun créneau de délai)'),
        remplace(orig, FOND_JPEG, mot(orig, FOND_JPEG, FOND_LONGUEUR), neuf,
                 f'fond de l\'écran d\'infos Graphique : JPEG gris clair de Nikon → noir ({n} octets, en-têtes '
                 f'identiques à l\'original, zéros après EOI)'),
    ]


# ---------------------------------------------------------------- navigation du bandeau (étape 7)

# Retour de Thomas après le flash (octobre 2026) : avec des onglets posés à l'horizontale, ▲▼ pour en
# changer et ◀ pour y revenir ne se devinent pas. Le répartiteur des écrans de tête (menu_action_131636)
# appelle FUN_00131f8a au niveau des onglets (CALL en 0x131F60) et FUN_00132286 au niveau de la liste
# (CALL en 0x131F76, retour 0x131F78), selon le bit 0x1000 de 0x83CE2130 + 12 × (menu + 0x12).
# Codes des touches relevés dans l'émulateur : ▼ 0x1000, ▲ 0x2000, ◀ 0x4000, ▶ 0x8000, OK 0x20000000.
# Menu courant + 0xC : ligne visible (demi-mot), + 0xE : défilement (vu dans CONFIG : 5 et 3 après 8 ▼) ;
# les menus de tête sont alignés sur 4 octets, le mot + 0xC est nul seulement sur la vraie première ligne.
NAV = 0x40F000                   # place libre (0xFF d'origine), après les données du bandeau (fin 0x40E447)
ONGLETS_TOUCHE = 0x131F8A        # niveau onglets ; seul appelant : menu_action_131636
LISTE_TOUCHE = 0x132286          # niveau liste (menu_ok) ; appelée aussi par les sous-écrans
LISTE_RETOUR_TETE = 0x131F78     # adresse de retour quand l'appel vient d'une liste de tête
NAV_CROCHETS = {                 # entrée détournée : 8 octets d'origine déplacés (aucun relatif au PC)
    'onglets': (ONGLETS_TOUCHE, '8ff017810f028b5b'),   # STM1 ; ST RP,@-R15 ; ENTER #8 ; MOV R5,R11
    'liste': (LISTE_TOUCHE, '17058ff017810f02'),       # ST R5,@-R15 ; STM1 ; ST RP,@-R15 ; ENTER #8
}
# niveau onglets : ◀ ▶ changent d'onglet dans l'ordre du bandeau, ▼ entre dans la liste, ▲ ne fait rien
NAV_ONGLETS = [(0x4000, 0x2000), (0x8000, 0x1000), (0x1000, 0x8000), (0x2000, 0x4000)]


def code_navigation():
    s = Asm(NAV)
    # onglets : R4 = touche ; R12, R13 libres à l'entrée (ABI)
    s.label('env_onglets')
    for k, (avant, apres) in enumerate(NAV_ONGLETS):
        s.ldi(avant, 12)
        s.cmp(12, 4)
        s.b('eq', f'on_{k}')
    s.b('ra', 'tr_onglets')
    for k, (avant, apres) in enumerate(NAV_ONGLETS):
        s.label(f'on_{k}')
        s.ldi(apres, 4)
        s.b('ra', 'tr_onglets')
    s.label('tr_onglets')
    s.brut(bytes.fromhex(NAV_CROCHETS['onglets'][1]))
    s.ldi32(ONGLETS_TOUCHE + 8, 12)
    s.jmp_r(12)
    # liste de tête : ▲ sur la première ligne remonte au bandeau (comme ◀) au lieu d'aller en bas
    s.align()
    s.label('env_liste')
    s.brut(b'\xb7\x1c')                      # MOV RP,R12
    s.ldi32(LISTE_RETOUR_TETE, 13)
    s.cmp(13, 12)
    s.b('ne', 'tr_liste')                    # sous-écran : rien ne change
    s.ldi(0x2000, 12)
    s.cmp(12, 4)
    s.b('ne', 'tr_liste')
    s.ldi32(MENU_COURANT, 12)
    s.ld(12, 12)                             # R12 = menu courant
    s.ldi8(0x0C, 13)
    s.ld13(12, 12)                           # R12 = ligne visible (menu + 0xC) et défilement (+0xE)
    s.cmpi(0, 12)                            # les deux à 0 : vraie première ligne
    s.b('ne', 'tr_liste')
    s.ldi(0x4000, 4)                         # ◀ : retour aux onglets (code de Nikon)
    s.label('tr_liste')
    s.brut(bytes.fromhex(NAV_CROCHETS['liste'][1]))
    s.ldi32(LISTE_TOUCHE + 8, 12)
    s.jmp_r(12)
    return s


def etape_navigation(orig):
    s = code_navigation()
    code = s.octets()
    assert NAV + len(code) <= FIN_LIBRE
    assert all(c == 0xFF for c in mot(orig, NAV, len(code)))
    patchs = [remplace(orig, NAV, mot(orig, NAV, len(code)), code,
                       'navigation du bandeau : touches remappées au niveau des onglets, ▲ en haut d\'une liste '
                       'de tête vers le bandeau (code dans la place libre)')]
    for nom, (adr, dep) in NAV_CROCHETS.items():
        assert mot(orig, adr, 8).hex() == dep, nom
        patchs.append(remplace(orig, adr, bytes.fromhex(dep),
                               struct.pack('>HIH', 0x9F8C, s.labels['env_' + nom], 0x970C),
                               f'{adr:#x} : entrée détournée vers env_{nom} (LDI:32 #…,R12 ; JMP @R12)'))
    return patchs


# ---------------------------------------------------------------- chiffres de l'écran d'infos (étape 8)

# Photo du boîtier (octobre 2026) : vitesse, ouverture et compteur illisibles. Nikon dessine chaque chiffre
# en deux passes (FUN_0009f2d0, FUN_0009fd66, FUN_000a06f0…) : le fantôme « 8 » (remplissage 0xBB, ou 0x91
# pour le compteur, contour par la structure passée en dernier paramètre), puis la valeur, remplie en 0
# (noir) en P et dans d'autres modes (0x94 ailleurs), cernée en 0x01. Sombre sur le fond JPEG gris clair de
# Nikon ; sur notre fond noir, des 8 verts pleins et des trous noirs. L'entrée 0 est le noir de tout l'écran,
# 0x93 (contour des fantômes) le fond des aides : on remappe à l'entrée des deux fonctions de dessin des
# chiffres, appelées seulement par l'écran d'infos (0x9E910-0xA7294) :
#   remplissage 0 → CHIFFRE_ALLUME (0x94, passée en vert à l'étape 1) ;
#   remplissage 0xBB ou 0x91 (fantôme, passées en vert très sombre à l'étape 1) → sans contour.
CHIFFRES = 0x40F100              # place libre, après le code de l'étape 7
CHAINE_CHIFFRES = 0x7B59E        # (R4-R7, pile : +0x10 couleur, +0x18 structure du contour)
GLYPHE_INFOS = 0x7B9C8           # (R4-R7, pile : +0x0C couleur, +0x14 structure du contour)
CHIFFRE_ALLUME = 0x94
FANTOMES = (0xBB, 0x91)
CHIFFRES_CROCHETS = {
    'chaine': (CHAINE_CHIFFRES, '8e0e8ff017810f0c', 0x10, 0x18),   # STM0 (R4-R6) ; STM1 ; ST RP ; ENTER #0x30
    'glyphe': (GLYPHE_INFOS, '8e0c8ff017810f0b', 0x0C, 0x14),      # STM0 (R4, R5) ; STM1 ; ST RP ; ENTER #0x2C
}


def code_chiffres():
    s = Asm(CHIFFRES)
    for nom, (adr, dep, couleur, contour) in CHIFFRES_CROCHETS.items():
        s.align()
        s.label('env_' + nom)                # R12, R13 libres à l'entrée (ABI) ; R15 = 5e paramètre
        s.ldi8(couleur, 13)
        s.ld13(15, 12)                       # R12 = couleur de remplissage
        s.cmpi(0, 12)
        s.b('ne', f'{nom}_fantome')
        s.ldi(CHIFFRE_ALLUME, 12)            # noir de Nikon → vert des valeurs
        s.st13(12, 15)
        s.b('ra', 'tr_' + nom)
        s.label(f'{nom}_fantome')
        for k, f in enumerate(FANTOMES):
            s.ldi(f, 13)
            s.cmp(13, 12)
            s.b('eq', f'{nom}_sans_contour')
        s.b('ra', 'tr_' + nom)
        s.label(f'{nom}_sans_contour')
        s.ldi32('contour_nul', 12)
        s.ldi8(contour, 13)
        s.st13(12, 15)                       # structure du contour : échelle 0, aucun décalage tracé
        s.label('tr_' + nom)
        s.brut(bytes.fromhex(dep))
        s.ldi32(adr + 8, 12)
        s.jmp_r(12)
    s.align()
    s.label('contour_nul')                   # {type, ?, échelle (demi-mot), couleur (demi-mot)} : tout à 0
    s.brut(bytes(8))
    return s


def etape_chiffres(orig):
    s = code_chiffres()
    code = s.octets()
    assert NAV + len(code_navigation().octets()) <= CHIFFRES and CHIFFRES + len(code) <= FIN_LIBRE
    assert all(c == 0xFF for c in mot(orig, CHIFFRES, len(code)))
    patchs = [remplace(orig, CHIFFRES, mot(orig, CHIFFRES, len(code)), code,
                       'chiffres de l\'écran d\'infos : valeur remplie en noir → 0x94 (vert), fantômes 0xBB / 0x91 '
                       'sans contour (code dans la place libre)')]
    for nom, (adr, dep, _, _) in CHIFFRES_CROCHETS.items():
        assert mot(orig, adr, 8).hex() == dep, nom
        patchs.append(remplace(orig, adr, bytes.fromhex(dep),
                               struct.pack('>HIH', 0x9F8C, s.labels['env_' + nom], 0x970C),
                               f'{adr:#x} : entrée détournée vers env_{nom} (LDI:32 #…,R12 ; JMP @R12)'))
    return patchs


# ---------------------------------------------------------------- Programme envoyé au processeur A (étape 9)

# Le Programme (0x83CED24E, 0 Standard … 5 Piqué max) n'agissait pas sur l'exposition, calculée par le A.
# Avec le patch du A (outils/programmes_a.py, patchs/a-programmes.json), le A lit le Programme dans le
# quartet bas de l'octet ISO auto du bloc 0x05 (B 0x83CE974F, A 0x3D25B) : valeurs 9 à 13 = 8 + Programme,
# bit 7 = ISO auto actif. Le réglage ISO auto du menu n'est jamais touché : seule la COPIE envoyée change.
#   - liaisonA_preparer (0xA9516) recopie le bloc à envoyer en 0x83CEE85A ; la somme de contrôle est faite
#     octet par octet à l'émission (0xAA9F4-0xAAA02) : on retouche la copie juste après, pour la commande 5 ;
#   - le A renvoie le bloc en écho (commande 0x06, 0x83CE975B), que le B compare au sien (fin 0xA9BF4, et
#     FUN_00132c3e qui renvoie tant qu'ils diffèrent, 500 tics au plus) : on remet l'octet du B dans l'écho
#     quand il porte notre retouche ;
#   - le choix d'un Programme (prog_choix, étape 4) envoie la commande 5 (liaisonA_envoyerCommande, en file),
#     puisque le bloc du B, lui, n'a pas changé ;
#   - le Programme ne part qu'en P (quartet bas de 0x83CE974D = 0) : en S, A, M et en scène, le A reçoit l'octet
#     de l'utilisateur, tel quel. Tourner la molette change ce quartet et envoie la commande 5 (FUN_0004c2b0 →
#     FUN_001342a0 → FUN_00138546, vérifié dans l'émulateur) : le A suit le mode à chaque cran.
# Sans le patch du A, un A de Nikon lirait 9 à 13 hors de sa table de vitesses mini : ne pas flasher cette
# étape sans le A correspondant (ou choisir Standard avant de revenir au A d'origine).
LIAISON_CODE = 0x40F200          # place libre, après l'étape 8
PREPARER = 0xA9516               # liaisonA_preparer
FIN_06 = 0xA9BF4                 # fonction de fin de la commande 0x06 (écho du bloc 0x05)
ENVOYER_CMD = 0xA9A50            # liaisonA_envoyerCommande(n)
CMD_EN_COURS = 0x83CEE960        # commande préparée par liaisonA_preparer
COPIE_ENVOI = 0x83CEE85A         # données recopiées pour l'envoi
ECHO_05 = 0x83CE975B             # tampon de la commande 0x06 (écho de 0x05)
PROG_MAX_A = 5
MODE_P = 0                       # 0x83CE974D & 0xF : mode de la molette (0 P, 1 S, 2 A, 3 M, scènes ensuite)
LIAISON_CROCHETS = {             # entrée détournée : octets d'origine déplacés (aucun relatif au PC)
    'preparer': (PREPARER, '8f709f8583cee960'),          # STM1 (R9-R11) ; LDI:32 #0x83CEE960,R5
    'fin06': (FIN_06, '8fe017819f8483ce975b'),           # STM1 ; ST RP,@-R15 ; LDI:32 #0x83CE975B,R4 (10 octets)
}


def code_liaison(prog_choix, reinit):
    s = Asm(LIAISON_CODE)

    def surcharge(dest, tmp):
        """dest ← octet ISO auto modifié : bit 7, ISO maxi de l'utilisateur, quartet bas = 8 + Programme.
        Entrée : R1 = 8 + Programme, R0 = octet de l'utilisateur."""
        s.mov(0, dest)
        s.ldi8(0x70, tmp)
        s.and_(tmp, dest)
        s.ldi8(0x80, tmp)
        s.or_(tmp, dest)
        s.or_(1, dest)

    def programme(saut):
        """R1 = 8 + Programme ; saute à `saut` si Standard ou hors bornes."""
        s.ldi32(PROG_OCTET, 12)
        s.ldub(12, 1)
        s.cmpi(0, 1)
        s.b('eq', saut)
        s.cmpi(PROG_MAX_A + 1, 1)
        s.b('ge', saut)
        s.addi(8, 1)

    # --- liaisonA_preparer : appel complet, puis retouche de la copie de la commande 5 ; R4 (résultat) gardé
    s.label('env_preparer')
    s.push_rp()
    s.appel('tr_preparer')
    s.ldi32(CMD_EN_COURS, 12)
    s.ldub(12, 0)
    s.cmpi(5, 0)
    s.b('ne', 'preparer_fin')
    programme('preparer_fin')
    s.ldi32(COPIE_ENVOI, 12)             # mode de la molette (quartet bas du 1er octet) : Programme en P seulement
    s.ldub(12, 0)
    s.ldi8(0x0F, 13)
    s.and_(13, 0)
    s.cmpi(MODE_P, 0)
    s.b('ne', 'preparer_fin')
    s.ldi32(COPIE_ENVOI + 2, 12)
    s.ldub(12, 0)
    surcharge(2, 13)
    s.stb(2, 12)
    s.label('preparer_fin')
    s.pop_rp()
    s.ret()
    s.label('tr_preparer')
    s.brut(bytes.fromhex(LIAISON_CROCHETS['preparer'][1]))
    s.ldi32(PREPARER + 8, 12)
    s.jmp_r(12)

    # --- fin de 0x06 : la fonction d'origine recopie l'écho du A dans le bloc du B (le A fait référence) ;
    # un quartet bas de 8 ou plus n'existe que par notre retouche (le B ne règle que 0 à 7) : l'écho reprend
    # alors l'octet du B, qui reste celui du menu, que le Programme soit actif ou non (A et B désaccordés).
    # Au démarrage, le B relit son bloc en flash (0x83CED254 → 0x83CE974D, FUN_0004044c) puis envoie 5 : un écho
    # arrivé avant cette relecture est écrasé par elle (scénario programme-a-demarrage)
    s.align()
    s.label('env_fin06')
    s.ldi32(ECHO_05 + 2, 12)
    s.ldub(12, 1)
    s.ldi8(0x0F, 13)
    s.and_(13, 1)
    s.cmpi(8, 1)
    s.b('lt', 'tr_fin06')
    s.ldi32(ISO_OCTET, 13)
    s.ldub(13, 0)
    s.stb(0, 12)
    s.label('tr_fin06')
    s.brut(bytes.fromhex(LIAISON_CROCHETS['fin06'][1]))
    s.ldi32(FIN_06 + 10, 12)
    s.jmp_r(12)

    # --- choix d'un Programme : action d'origine (étape 4), puis commande 5 en file ; R4 rendu tel quel
    s.align()
    s.label('env_prog')
    s.push_rp()
    s.appel('tr_prog')
    s.push(4)
    s.ldi8(5, 4)
    s.appel(ENVOYER_CMD)
    s.pop(4)
    s.pop_rp()
    s.ret()
    s.label('tr_prog')
    s.brut(bytes.fromhex(PROG_CHOIX_DEBUT))
    s.ldi32(prog_choix + 8, 12)
    s.jmp_r(12)

    # --- Réinitialiser (preglage_reinit, préréglages V1) : envoie au A puis remet le Programme à Standard ;
    # le bloc du B n'ayant pas changé, FUN_00132c3e n'enverrait plus rien : commande 5 en file, après coup
    s.align()
    s.label('env_reinit')
    s.push_rp()
    s.appel('tr_reinit')
    s.push(4)
    s.ldi8(5, 4)
    s.appel(ENVOYER_CMD)
    s.pop(4)
    s.pop_rp()
    s.ret()
    s.label('tr_reinit')
    s.brut(bytes.fromhex(REINIT_DEBUT))
    s.ldi32(reinit + 8, 13)              # R13 : les octets rejoués viennent de charger R12 (CALL @R12 qui suit)
    s.jmp_r(13)
    return s


PROG_CHOIX_DEBUT = '9f8483cee49c0440'   # prog_choix (étape 4) : LDI:32 #0x83CEE49C,R4 ; LD @R4,R0
REINIT_DEBUT = '17819f8c00138546'       # preglage_reinit (préréglages V1) : ST RP,@-R15 ; LDI:32 #0x138546,R12


def etape_liaison(orig):
    prog_choix = code_menus(disposition()).labels['prog_choix']
    import preglages_v1
    reinit = preglages_v1.assembler()[0].labels['preglage_reinit']
    s = code_liaison(prog_choix, reinit)
    code = s.octets()
    assert LIAISON_CODE + len(code) <= FIN_LIBRE
    assert all(c == 0xFF for c in mot(orig, LIAISON_CODE, len(code)))
    patchs = [remplace(orig, LIAISON_CODE, mot(orig, LIAISON_CODE, len(code)), code,
                       'Programme vers le A : copie du bloc 0x05 retouchée, écho 0x06 remis, envoi au choix '
                       '(code dans la place libre)')]
    for nom, (adr, dep) in LIAISON_CROCHETS.items():
        assert mot(orig, adr, len(dep) // 2).hex() == dep, nom
        neuf = struct.pack('>HIH', 0x9F8C, s.labels['env_' + nom], 0x970C) + b'\x9f\xa0' * ((len(dep) // 2 - 8) // 2)
        patchs.append(remplace(orig, adr, bytes.fromhex(dep), neuf,
                               f'{adr:#x} : entrée détournée vers env_{nom} (LDI:32 #…,R12 ; JMP @R12)'))
    # prog_choix est du code de l'étape 4 : l'octet d'origine à vérifier est celui du firmware avec l'étape 4
    patchs.append({'offset': hex(prog_choix - BASE), 'avant': {'hex': PROG_CHOIX_DEBUT},
                   'apres': {'hex': struct.pack('>HIH', 0x9F8C, s.labels['env_prog'], 0x970C).hex()},
                   'texte': f'prog_choix ({prog_choix:#x}, étape 4) : entrée détournée vers env_prog'})
    patchs.append({'offset': hex(reinit - BASE), 'avant': {'hex': REINIT_DEBUT},
                   'apres': {'hex': struct.pack('>HIH', 0x9F8C, s.labels['env_reinit'], 0x970C).hex()},
                   'texte': f'preglage_reinit ({reinit:#x}, préréglages V1) : entrée détournée vers env_reinit'})
    return patchs


# ---------------------------------------------------------------- assemblage

def appliquer(b, patchs):
    return bytes(patchpy.appliquer(bytearray(b), patchs))


def construire(ecrire=True):
    orig = bytes(patchpy.charger_original())
    pre = json.loads((PATCHS / 'menu-preglages.json').read_text(encoding='utf-8'))['patchs']
    b_pre = appliquer(orig, pre)
    # les libellés des étapes 2 à 5 sont dessinés en DIN Condensed (police du Mac) : ailleurs (session cloud),
    # on reprend les JSON déjà construits, pour ne pas graver d'autres glyphes dans le firmware
    import icones
    police = os.path.exists(icones.POLICE)
    etapes = [
        ('pipboy-1-couleurs', 'Menu Pip-Boy, étape 1 : couleurs (palettes 0xD87C3 et 0x1B0000), données seules.',
         etape_couleurs(orig)),
        ('pipboy-2-textes', 'Menu Pip-Boy, étape 2 : table de textes du français reconstruite (titres PRISE DE VUE, VISU, '
                            'PERSO, CONFIG ; libellés des nouvelles entrées) et table des aides, données seules. Suppose menu-preglages.json.',
         etape_textes(b_pre) if police else None),
        ('pipboy-3-onglets', 'Menu Pip-Boy, étape 3 : onglet Retouche retiré (navigation et colonne des onglets), '
                             '4 constantes de code.', etape_onglets(orig) if police else None),
        ('pipboy-4-menus', 'Menu Pip-Boy, étape 4 : PRISE DE VUE à 7 entrées, écrans Programme, ISO auto (valeurs à '
                           'droite), Marche, Si trop sombre, ISO mini, Menus ; valeurs écrites (données + code ajouté '
                           'dans la place libre).', etape_menus(orig) if police else None),
        ('pipboy-5-onglets', 'Menu Pip-Boy, étape 5 : onglets en mots dans un bandeau en haut (PRISE DE VUE, VISU, PERSO, '
                             'CONFIG), plus de colonne à gauche, lignes en pleine largeur, titre du sous-écran sous le '
                             'bandeau, aide « ? » en haut à droite ; navigation ▲▼ dans l\'ordre du bandeau. Code et '
                             'données dans la place libre (0x40C000), 11 entrées de fonctions détournées, 5 constantes.',
         etape_bandeau(orig) if police else None),
        ('pipboy-6-style', 'Menu Pip-Boy, étape 6 (après le premier flash) : menus et écran d\'infos forcés en '
                           'style Graphique, quel que soit CONFIG › Style écran infos, et fond JPEG de l\'écran '
                           'd\'infos remplacé par un fond noir. 2 + 2 octets de code, données.',
         etape_style(orig)),
        ('pipboy-7-navigation', 'Menu Pip-Boy, étape 7 (après le premier flash) : navigation suivant le bandeau. '
                                'Sur les onglets, ◀ ▶ changent d\'onglet, ▼ entre dans la liste (OK aussi), ▲ ne '
                                'fait rien ; ▲ sur la première ligne d\'une liste de tête remonte au bandeau. '
                                'Suppose l\'étape 5. Deux entrées détournées, code dans la place libre (0x40F000).',
         etape_navigation(orig)),
        ('pipboy-8-chiffres', 'Menu Pip-Boy, étape 8 (photo du boîtier) : chiffres de l\'écran d\'infos lisibles. '
                              'Valeurs (remplies en noir par Nikon) en vert, fantômes « 8 » en vert très sombre '
                              'sans contour. Deux entrées détournées (0x7B59E, 0x7B9C8), code à 0x40F100 ; '
                              'couleurs 0x94, 0xBB, 0x91 à l\'étape 1.',
         etape_chiffres(orig)),
        ('pipboy-9-programme-a', 'Menu Pip-Boy, étape 9 : le Programme envoyé au processeur A (quartet bas de l\'octet '
                                 'ISO auto de la copie du bloc 0x05 = 8 + Programme, bit 7 = ISO auto). Sans effet sans '
                                 'le patch du A (patchs/a-programmes.json), à ne pas flasher sans lui. Suppose l\'étape 4.',
         etape_liaison(orig)),
    ]
    tout = list(pre)
    docs = {}
    # étape 9 : écrite à part, hors de menu-pipboy.json (elle ne va qu'avec le A patché, build/V5/)
    a_part = {'pipboy-9-programme-a'}
    for nom, desc, p in etapes:
        if p is None:   # police absente : patchs déjà construits, repris tels quels
            p = json.loads((PATCHS / f'{nom}.json').read_text(encoding='utf-8'))['patchs']
            print(f'{nom} : police {icones.POLICE} absente, patchs/{nom}.json repris tel quel')
        docs[nom] = {'description': desc, 'patchs': p}
        if nom not in a_part:
            tout += p
    docs['menu-pipboy'] = {'description': 'Menu Pip-Boy complet (maquette design/pipboy-planche.png) : menu-preglages.json '
                                          '+ étapes 1 à 8 de outils/pipboy.py (l\'étape 9 est à part). Boîtier en français.', 'patchs': tout}
    appliquer(orig, tout)  # vérifie qu'il n'y a ni chevauchement ni octet d'origine faux
    if ecrire:
        for nom, doc in docs.items():
            (PATCHS / f'{nom}.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            print(f'patchs/{nom}.json : {len(doc["patchs"])} patchs')
    return docs


def self_test():
    a = Asm(0x1000)
    a.label('x')
    a.ldi32(0x83CEE49C, 4)
    a.ldi8(0x1C, 13)
    a.ld13(4, 0)
    a.b('eq', 'x')
    a.push_rp()
    a.pop_rp()
    a.ret()
    assert a.octets().hex() == '9f8483cee49cc1cd0040e2fa178107819720', a.octets().hex()
    assert ycc(0, 0, 0) == bytes([16, 128, 128])
    docs = construire(ecrire=False)
    b = appliquer(bytes(patchpy.charger_original()), docs['menu-pipboy']['patchs'])
    pc = struct.unpack('>I', b[TABLE_LANGUES + 4 * (3 * LANGUE + 2) - BASE:][:4])[0]
    assert pc == TEXTES

    def d(i):
        a0, a1 = struct.unpack('>II', b[pc + 4 * (31 + i) - BASE:][:8])
        return b[a0 - BASE:a1 - BASE]
    assert d(0x21) == b'PRISE DE VUE', d(0x21)
    assert d(0x22).startswith(b'Pr\x81\x21r\x81\x21glage'), d(0x22)
    assert d(ID['pique']) == b'Piqu\x81\x21 max'
    orig = Firmware()
    ch = orig.chaines(LANGUE)
    assert d(0x23) == ch[('D', 0x23)][1]          # chaîne non touchée recopiée telle quelle
    assert d(0x22) == b'Pr\x81\x21r\x81\x21glage' and d(0x2D) == b'Personnalis\x81\x21'
    # aides : table B reconstruite, aides d'origine recopiées, nouvelles aides en place
    pb = struct.unpack('>I', b[TABLE_LANGUES + 4 * (3 * LANGUE + 1) - BASE:][:4])[0]
    assert pb == TEXTES_B

    def aide(i):
        a0, a1 = struct.unpack('>II', b[pb + 4 * i - BASE:][:8])
        return b[a0 - BASE:a1 - BASE]
    assert aide(0x47) == ch[('B', 0x47)][1]
    assert aide(AIDE['programme'])[0] == aide(AIDE['programme']).count(b'\n') + 1
    assert b'Rapide:' in aide(AIDE['programme'])
    assert all(len(l) <= 40 for i in NOUVELLES_AIDES for l in aide(i)[1:].split(b'\n'))
    # planche 4 : descripteur vers la copie, glyphes d'origine identiques
    desc = PLANCHES + 12 * PLANCHE_VAL
    assert struct.unpack('>I', b[desc + 8 - BASE:][:4])[0] == GLYPHES
    assert b[GLYPHES - BASE:GLYPHES - BASE + 21 * 400] == orig.b[0x27107C - BASE:0x27107C - BASE + 21 * 400]
    # code : pas de chevauchement avec les textes
    code = code_menus(disposition()).octets()
    assert CODE + len(code) <= TEXTES
    # étape 5 : chaque fonction détournée saute à son enveloppe, qui commence par le sas de la voie
    # de secours ; chaque tremplin = les octets d'origine déplacés, puis le saut à la suite d'origine
    import icones
    if not os.path.exists(icones.POLICE):
        print(f'étape 5 non recontrôlée : police {icones.POLICE} absente')
    else:
        blob, a, mots = donnees_bandeau()
        s = code_bandeau(a)
        assert BANDEAU + len(s.octets()) <= BANDEAU_DONNEES and BANDEAU_DONNEES + len(blob) <= FIN_LIBRE
        assert b[BANDEAU_DONNEES - BASE:BANDEAU_DONNEES - BASE + len(blob)] == blob
        debut_sas = struct.pack('>HI', 0x9F8C, MENU_COURANT)
        for nom, (adr, dep) in CROCHETS.items():
            n = len(dep) // 2
            assert b[adr - BASE:adr - BASE + 8] == struct.pack('>HIH', 0x9F8C, s.labels['env_' + nom], 0x970C), nom
            assert b[adr - BASE + 8:adr - BASE + n] == b'\x9f\xa0' * ((n - 8) // 2), nom
            e = s.labels['env_' + nom] - BASE
            assert b[e:e + 6] == debut_sas, nom
            t = s.labels['tr_' + nom] - BASE
            assert b[t:t + n + 8] == bytes.fromhex(dep) + struct.pack('>HIH', 0x9F8C, adr + n, 0x970C), nom
        assert b[VARS - RAM - BASE:VARS - RAM - BASE + 6] == bytes(6)   # drapeaux à zéro au démarrage
        assert all(c == 0 for c in b[0x15BAE0 - BASE:0x15BAF0 - BASE])
        for adr, avant, apres, texte in NAV_BANDEAU:
            assert b[adr - BASE:adr - BASE + 4] == struct.pack('>I', apres)
        assert [m['texte'] for m in mots] == ['PRISE DE VUE', 'VISU', 'PERSO', 'CONFIG']
    # étape 6 : style Graphique forcé, fond noir décodable et uniforme, 0x22 laissée à Nikon
    import io
    from PIL import Image
    assert b[STYLE_COURANT - BASE:STYLE_COURANT - BASE + 2] == bytes.fromhex('c014')
    assert b[INFOS_STYLE - BASE:INFOS_STYLE - BASE + 4] == bytes.fromhex('9fa0c010')
    fond = b[FOND_JPEG - BASE:FOND_JPEG - BASE + FOND_LONGUEUR]
    im = Image.open(io.BytesIO(fond))
    im.draft('YCbCr', im.size)
    assert im.size == (640, 480) and im.layer == [(1, 2, 1, 0), (2, 1, 1, 1), (3, 1, 1, 1)]
    assert im.convert('YCbCr').getextrema() == ((16, 16), (128, 128), (128, 128))
    o = bytes(patchpy.charger_original())
    assert b[PAL3 - BASE + 3 * 0x22:PAL3 - BASE + 3 * 0x23] == o[PAL3 - BASE + 3 * 0x22:PAL3 - BASE + 3 * 0x23]
    # étape 7 : entrées détournées vers leur enveloppe, tremplins = octets d'origine puis retour juste après
    s = code_navigation()
    code = s.octets()
    assert b[NAV - BASE:NAV - BASE + len(code)] == code
    for nom, (adr, dep) in NAV_CROCHETS.items():
        assert b[adr - BASE:adr - BASE + 8] == struct.pack('>HIH', 0x9F8C, s.labels['env_' + nom], 0x970C), nom
        t = s.labels['tr_' + nom] - NAV
        assert code[t:t + 16] == bytes.fromhex(dep) + struct.pack('>HIH', 0x9F8C, adr + 8, 0x970C), nom
    mots = [struct.unpack('>H', code[i:i + 2])[0] for i in range(0, len(code), 2)]
    assert not any(m in (0x9F0C, 0x9F1C) or (m & 0xF000) == 0xF000 for m in mots)   # aucun créneau de délai
    print('self-test OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['construire', 'asm'])
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.action == 'construire':
        construire()
    elif a.action == 'asm':
        s = code_menus(disposition())
        for k, v in sorted(s.labels.items(), key=lambda t: t[1]):
            print(f'{v:#08x} {k}')
        print(s.octets().hex())
    else:
        ap.print_help()


if __name__ == '__main__':
    sys.exit(main())
