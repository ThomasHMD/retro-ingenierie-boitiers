#!/usr/bin/env python3
"""Arbre des menus du firmware B du D40 (v1.11), lu dans les données copiées en RAM.

Structure (vérifiée sur le binaire et dans le code, voir CARTE.md §5 bis) :
  menu = en-tête de 32 octets suivi de ses entrées de 16 octets, en ROM 0x1544C4–0x15D528
  (en RAM à ROM + 0x83B8BAEC, c'est l'adresse RAM qu'on trouve dans les pointeurs).
  En-tête : +0 titre, +2 sous-titre (identifiants de texte), +4 attributs, +6 ?, +8 nombre
    d'entrées sélectionnables, +A nombre d'entrées stockées, +12 numéro d'écran (indice dans
    tblEcrans 0x156644), +14 menu parent, +18 positions à l'écran (liste de u32 x<<16|y),
    +1C entrées (= en-tête + 0x20).
  Entrée : +0 icône, +2 libellé, +4 aide (identifiants de texte), +6 ?, +8 ?, +A numéro
    d'entrée (suit l'ordre des entrées), +C sous-menu (0 = aucun).
  tblEcrans[n] (12 octets) : +0 attributs, +4 fonction d'entrée (affichage), +8 fonction d'action.
Identifiant de texte (16 bits) : bits 13-15 = table, bits 0-12 = numéro (FUN_0007c1a0) :
  0x0000 libellés D, 0x2000 titres C, 0x4000 aides B, 0x6000 messages A.

  menus.py arbre [--langue 1]
  menus.py tsv > menus.tsv
  menus.py ecrans
  menus.py --self-test
"""
import argparse
import struct
import sys

from chaines import BASE, Firmware, texte

RAM = 0x83B8BAEC
DONNEES = (0x1544C4, 0x15D528)
TBL_ECRANS = 0x156644


class Menus:
    def __init__(self, langue=1):
        self.fw = Firmware()
        self.ch = self.fw.chaines(langue)
        self.menus = self._trouver()

    def h(self, a):
        return struct.unpack('>H', self.fw.octets(a, 2))[0]

    def w(self, a):
        return self.fw.mot(a)

    def libelle(self, tid):
        if tid == 0xFFFF:
            return '—'
        cle = {0x0000: 'D', 0x2000: 'C', 0x4000: 'B', 0x6000: 'A'}[tid & 0xE000]
        o = self.ch.get((cle, tid & 0x1FFF))
        if o is None:
            return f'?{tid:04x}'
        t = texte(o[1])
        return t[4:] if cle != 'D' and t.startswith('{') else t

    def _trouver(self):
        res = {}
        for a in range(DONNEES[0] & ~0xF, DONNEES[1] - 0x20, 0x10):
            if self.w(a + 0x1C) == a + 0x20 + RAM and self.h(a + 0x10) == 0:
                n = self.h(a + 0xA)
                entrees = []
                for i in range(n):
                    e = a + 0x20 + 0x10 * i
                    sm = self.w(e + 0xC)
                    entrees.append({'adresse': e, 'icone': self.h(e), 'libelle': self.h(e + 2),
                                    'aide': self.h(e + 4), 'numero': self.h(e + 0xA),
                                    'sous_menu': sm - RAM if sm else 0})
                p = self.w(a + 0x14)
                res[a] = {'adresse': a, 'titre': self.h(a), 'sous_titre': self.h(a + 2),
                          'attributs': self.h(a + 4), 'nb': self.h(a + 8), 'ecran': self.h(a + 0x12),
                          'parent': p - RAM if p else 0, 'positions': self.w(a + 0x18) - RAM,
                          'entrees': entrees}
        return res

    def titre(self, m):
        return self.libelle(m['titre']) + ('' if m['sous_titre'] == 0xFFFF else ' › ' + self.libelle(m['sous_titre']))

    def ecran(self, n):
        a = TBL_ECRANS + 12 * n
        return {'attributs': self.h(a), 'entree': self.w(a + 4), 'action': self.w(a + 8)}

    def racines(self):
        return [m for m in self.menus.values() if m['parent'] not in self.menus]

    def arbre(self, m=None, prof=0, vus=None):
        vus = set() if vus is None else vus
        lignes = []
        if m is None:
            for r in self.racines():
                lignes += self.arbre(r, 0, vus)
            return lignes
        if m['adresse'] in vus:
            return lignes
        vus.add(m['adresse'])
        e = self.ecran(m['ecran'])
        titre = self.titre(m)
        lignes.append(f"{'  ' * prof}[{m['adresse']:#08x} écran {m['ecran']} entrée {e['entree']:#x} action {e['action']:#x}] {titre}")
        for i, x in enumerate(m['entrees']):
            lignes.append(f"{'  ' * (prof + 1)}{i}. {self.libelle(x['libelle'])}  (id {x['libelle']:#06x}, icône {x['icone']:#06x}, n° {x['numero']:#x})")
            if x['sous_menu'] in self.menus:
                lignes += self.arbre(self.menus[x['sous_menu']], prof + 2, vus)
        return lignes


def self_test():
    m = Menus(1)
    opt = m.menus[0x159DC0]
    assert m.libelle(opt['titre']) == 'Optimize image', opt
    assert [m.libelle(x['libelle']) for x in opt['entrees']] == [
        'Normal', 'Softer', 'Vivid', 'More vivid', 'Portrait', 'Black-and-white', 'Custom']
    perso = m.menus[opt['entrees'][6]['sous_menu']]
    assert perso['parent'] == 0x159DC0 and perso['ecran'] == 16
    couleur = m.menus[0x159F60]
    assert [m.libelle(x['libelle']) for x in couleur['entrees']][1] == '{93}{01}(AdobeRGB)'
    assert m.ecran(couleur['ecran'])['entree'] == 0x14483C
    print(f'self-test OK ({len(m.menus)} menus)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', nargs='?', choices=['arbre', 'tsv', 'ecrans'], default='arbre')
    ap.add_argument('--langue', type=int, default=1)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    m = Menus(a.langue)
    if a.action == 'arbre':
        print('\n'.join(m.arbre()))
    elif a.action == 'tsv':
        print('menu\tecran\tparent\ttitre\tentree\tid_libelle\tlibelle\ticone\tsous_menu')
        for x in m.menus.values():
            for i, e in enumerate(x['entrees']):
                print(f"{x['adresse']:#x}\t{x['ecran']}\t{x['parent']:#x}\t{m.libelle(x['titre'])}\t{i}\t"
                      f"{e['libelle']:#06x}\t{m.libelle(e['libelle'])}\t{e['icone']:#06x}\t{e['sous_menu']:#x}")
    else:
        for n in range(max(x['ecran'] for x in m.menus.values()) + 1):
            e = m.ecran(n)
            noms = sorted({m.titre(x) for x in m.menus.values() if x['ecran'] == n})
            print(f"{n}\t{e['attributs']:#06x}\t{e['entree']:#x}\t{e['action']:#x}\t{' | '.join(noms)}")


if __name__ == '__main__':
    sys.exit(main())
