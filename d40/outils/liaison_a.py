#!/usr/bin/env python3
"""Commandes de la liaison série entre le firmware B et le processeur A (D40, B v1.11).

Table tblCommandesA à 0xE482C (vérifié) : 48 commandes de 16 octets {tampon RAM, longueur,
sens, fonction de fin}. Sens : 1 = le B envoie le tampon au A, 0 = le B reçoit dans le tampon,
2 = longueur variable (commandes 0x00, 0x0F, 0x20, 0x21). La tâche 14 envoie le numéro de la
commande sur la liaison série 0 (SDIR0), puis les données ; la fonction de fin est appelée après.
Les appelants viennent du pseudo-C (desassemblage/regenerer.sh) s'il est donné.

  liaison_a.py [--pseudo-c d40-tout.c]
  liaison_a.py --self-test
"""
import argparse
import collections
import re
import struct
import sys

from chaines import Firmware

TABLE = 0xE482C
NB = 0x30
SENS = {0: 'A→B', 1: 'B→A', 2: 'variable'}


def commandes(fw):
    res = []
    for n in range(NB):
        tampon, longueur, sens, fin = struct.unpack('>4I', fw.octets(TABLE + 16 * n, 16))
        res.append({'n': n, 'tampon': tampon, 'longueur': longueur, 'sens': sens, 'fin': fin})
    return res


def appelants(chemin):
    """{numéro de commande: {fonctions qui l'envoient}} d'après les appels à 0xA9A50."""
    d, cur = collections.defaultdict(set), None
    for l in open(chemin, encoding='utf-8', errors='replace'):
        m = re.match(r'//@@ [0-9a-f]+ (\S+)', l)
        if m:
            cur = m.group(1)
        for a in re.findall(r'(?:liaisonA_envoyerCommande|FUN_000a9a50)\((0x[0-9a-f]+|\d+)\)', l):
            d[int(a, 0)].add(cur)
    return d


def self_test():
    c = commandes(Firmware())
    assert (c[7]['tampon'], c[7]['longueur'], c[7]['sens']) == (0x83CE957B, 9, 1), c[7]
    assert (c[0x14]['tampon'], c[0x14]['longueur'], c[0x14]['sens']) == (0x83CE9823, 13, 0), c[0x14]
    assert all(x['sens'] in SENS for x in c)
    print('self-test OK')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pseudo-c')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    app = appelants(a.pseudo_c) if a.pseudo_c else {}
    print('commande\ttampon\tlongueur\tsens\tfin\tappelants')
    for x in commandes(Firmware()):
        f = sorted(app.get(x['n'], ()))
        print(f"{x['n']:#04x}\t{x['tampon']:#010x}\t{x['longueur']}\t{SENS[x['sens']]}\t{x['fin']:#x}\t"
              f"{len(f)} {' '.join(f[:6])}{' …' if len(f) > 6 else ''}")


if __name__ == '__main__':
    sys.exit(main())
