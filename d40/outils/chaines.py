#!/usr/bin/env python3
"""Chaînes des menus et messages du firmware B du D40 (v1.11).

Structure (vérifiée sur le binaire) : table des langues à 0x15C7A4, 15 langues × 3 pointeurs
vers des tables de pointeurs de chaînes :
  A  messages (266 entrées) : 1er octet = nombre de lignes, « \\n » entre les lignes ;
  B  aides des modes et réglages (141 entrées), même format ;
  C  titres des aides des modes scène (31 entrées), même format ;
  D  libellés des menus (le reste, jusqu'à la première valeur hors du bloc de texte ; la table
     D commence 31 pointeurs après C, langue_choisir la range à part en 0x83CE3FEC) :
     chaînes mises bout à bout sans terminateur ni octet de nombre de lignes.
Identifiant de texte utilisé par le code (16 bits, FUN_0007c1a0) : bits 13-15 = table
(0x0000 D, 0x2000 C, 0x4000 B, 0x6000 A), bits 0-12 = numéro. Ex. 0x0022 = « Optimize image ».
La longueur d'une chaîne = distance à la chaîne suivante dans l'ordre des adresses.
Accents : 2 octets, 0x81 puis un code (0x81 0x21 = é, 0x81 0x0F = É) ; la table ACCENTS
est complétée au fil des relevés, un octet inconnu s'affiche « {81xx} ».

  chaines.py langues
  chaines.py liste [--langue 1] [--table D]
  chaines.py cherche "MENU" [--langue 4]
  chaines.py --self-test
"""
import argparse
import pathlib
import struct
import sys

ICI = pathlib.Path(__file__).resolve().parent.parent
FIRMWARE = ICI / 'firmware' / 'BD400111.bin'
BASE = 0x40000
TABLE_LANGUES = 0x15C7A4
NB_LANGUES = 15
TAILLE_A, TAILLE_B, TAILLE_C = 266, 141, 31
ACCENTS = {0x0A: 'Ã', 0x0D: 'Ç', 0x0F: 'É', 0x12: 'Ó', 0x15: '×', 0x19: 'à', 0x20: 'è', 0x21: 'é'}  # relevés par le contexte (FR, ES, PT)


class Firmware:
    def __init__(self, chemin=FIRMWARE):
        self.b = pathlib.Path(chemin).read_bytes()

    def mot(self, a):
        return struct.unpack('>I', self.b[a - BASE:a - BASE + 4])[0]

    def octets(self, a, n):
        return self.b[a - BASE:a - BASE + n]

    def tables(self, langue):
        a, b, c = (self.mot(TABLE_LANGUES + 4 * (3 * langue + k)) for k in range(3))
        ta = [self.mot(a + 4 * i) for i in range(TAILLE_A)]
        tb = [self.mot(b + 4 * i) for i in range(TAILLE_B)]
        bas, haut = min(ta + tb), max(ta)
        # bloc de texte de la langue : des libellés (C, D) aux messages (A) ; D s'arrête au premier
        # pointeur hors de ce bloc
        tc, i = [], 0
        while True:
            p = self.mot(c + 4 * i)
            if not (c < p < haut + 0x2000):
                break
            tc.append(p)
            i += 1
        return {'A': ta, 'B': tb, 'C': tc[:TAILLE_C], 'D': tc[TAILLE_C:]}

    def chaines(self, langue):
        """{(table, id): (adresse, octets)}. Règle du firmware (accesseurs vers 0x7C50E) :
        la chaîne id va de table[id] à table[id + 1]. Exceptions : la dernière entrée d'une
        table et C30, bornées par la chaîne suivante en mémoire."""
        t = self.tables(langue)
        debuts = sorted(set(t['A'] + t['B'] + t['C'] + t['D']))
        suivante = {d: f for d, f in zip(debuts, debuts[1:])}
        res = {}
        for nom, liste in t.items():
            for i, p in enumerate(liste):
                f = liste[i + 1] if i + 1 < len(liste) else None
                if f is None or f <= p:
                    f = suivante.get(p)
                if f is None:
                    n = self.octets(p, 400).find(b'\x00')
                    f = p + (n if n > 0 else 1)
                res[(nom, i)] = (p, self.octets(p, f - p))
        return res


def texte(o):
    s, i = [], 0
    while i < len(o):
        x = o[i]
        if x == 0x81 and i + 1 < len(o):
            s.append(ACCENTS.get(o[i + 1], '{81%02x}' % o[i + 1]))
            i += 2
            continue
        s.append(chr(x) if 0x20 <= x < 0x7f else ('⏎' if x == 0x0a else '{%02x}' % x))
        i += 1
    return ''.join(s)


def self_test():
    fw = Firmware()
    en = fw.chaines(1)
    assert en[('A', 0)][1] == b'\x01Done.', en[('A', 0)]
    assert texte(en[('D', 0)][1]) == 'PLAYBACK MENU', en[('D', 0)]
    assert texte(en[('D', 0x22)][1]) == 'Optimize image', en[('D', 0x22)]
    fr = fw.chaines(4)
    assert any(texte(o) == 'MENU CONFIGURATION' for _, o in fr.values())
    assert any(o == b'MENU R\x81\x0fGLAGES PERSO.' for _, o in fr.values())
    print('self-test OK')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', nargs='?', choices=['langues', 'liste', 'cherche'])
    ap.add_argument('motif', nargs='?')
    ap.add_argument('--langue', type=int)
    ap.add_argument('--table', choices=['A', 'B', 'C', 'D'])
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    fw = Firmware()
    if a.action == 'langues':
        for l in range(NB_LANGUES):
            t = fw.tables(l)
            print(l, ' '.join(f"{k}:{len(v)}" for k, v in t.items()), texte(fw.chaines(l)[('D', 0)][1]))
        return
    langues = [a.langue] if a.langue is not None else range(NB_LANGUES)
    for l in langues:
        for (tab, i), (p, o) in sorted(fw.chaines(l).items()):
            if a.table and tab != a.table:
                continue
            t = texte(o)
            if a.action == 'cherche' and a.motif.lower() not in t.lower():
                continue
            tid = {'D': 0x0000, 'C': 0x2000, 'B': 0x4000, 'A': 0x6000}[tab] | i
            print(f"{l}\t{tab}{i}\t{tid:#06x}\t{p:#08x}\t{len(o)}\t{t}")


if __name__ == '__main__':
    sys.exit(main())
