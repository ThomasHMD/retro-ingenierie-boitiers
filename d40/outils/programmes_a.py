#!/usr/bin/env python3
"""Lignes de programme dans le processeur A du D40 (Programme du menu Pip-Boy : Sujet rapide, Portrait,
Street, Profondeur, Piqué max). Patch du firmware A 1.11 (`firmware/AD400111.bin`, et 1.12), mis au point dans
l'émulateur du A avant tout flash. Étude : recherche/etude-a/, recherche/programmes-expo-iso-auto.md.

Transport (aucun nouvel échange entre les processeurs) : l'octet ISO auto du bloc 0x05 (B 0x83CE974F,
A 0x3D25B : bit 7 marche, bits 4-6 ISO maxi, bits 0-3 vitesse mini 0-7). Quand un Programme p (1 à 5) est
choisi, le B envoie au A, dans sa copie du bloc seulement, bit 7 à 1 et le quartet bas à 8 + p (9 à 13) :
l'ISO auto est alors actif dans le A (le A recalcule 0x3D0BC bit 1 depuis le bit 7 avant chaque mesure,
FUN_000c802c), avec l'ISO maxi réglé par l'utilisateur. Côté B : outils/pipboy.py, étape 9.

Deux détours dans le A, rien au démarrage, rien dans la liaison, la mise à jour ou le noyau :
  - fonction de P (0xC60E2) : la constante de l'appel de la ligne d'usine (0xC60F4, LDI:20 #0xC41C2,R12)
    pointe sur `ligne_perso`. Quartet bas < 9 : saut à la ligne d'usine, rien ne change. Sinon la vitesse
    visée est Ev − Av cible ; la suite de la fonction de P (bornes de vitesse, butées de l'objectif) et
    l'ISO auto (FUN_000c471c) font le reste. Un plancher d'ouverture (0x3CCB9, ×8 en 1/48 IL, posé par
    expo_programme juste avant) garde l'ouverture visée : l'ISO monte au lieu d'ouvrir ;
  - vitesse mini de l'ISO auto (expo_limiterVitesse, lecture de la table 0xFA876 en 0xC452A) : saut à
    `vitesse_mini`, qui rend la table de Nikon pour 0 à 7, et la vitesse du Programme pour 9 à 13.

Code dans la place libre réécrite par la mise à jour (0xF2400-0xF2FFF, libre en 1.11 et en 1.12 ; jamais
0xF3000-0xF3AFF, le flasheur, ni 0xF4000-0xF7FFF, jamais écrite). Deux versions du A : 1.11 (le boîtier de
Thomas) et 1.12 (dernière de Nikon) ; en 1.12 le code est décalé de 0xF6 octets, la table des vitesses
mini et les variables utilisées ici sont aux mêmes adresses (seules les variables 0x3E1xx bougent, de 0x10 ;
vérifié octet par octet aux trois points d'accroche). Unités : 1/48 d'IL, Tv 0 = 1 s, Av 0 = f/1, Ev = Tv + Av.

  programmes_a.py construire     patchs/a-programmes.json (A 1.11) et patchs/a-programmes-112.json (A 1.12)
  programmes_a.py scenario       emulateur/scenarios/a-programmes.txt et a-programmes-112.txt (Standard comparé à Nikon)
  programmes_a.py --self-test
"""
import argparse
import json
import pathlib
import struct
import sys

ICI = pathlib.Path(__file__).resolve().parent
PROJET = ICI.parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(PROJET))

import patch as patchpy  # noqa: E402
from pipboy import Asm  # noqa: E402

BASE_A = 0xC0000
CODE = 0xF2400                   # place libre (0xFF) en 1.11 et en 1.12, réécrite par la mise à jour du A
FIN_LIBRE = 0xF3000              # le flasheur commence ici : ne jamais déborder
APPEL_LIGNE = 0xC60F4            # LDI:20 #0xC41C2,R12 ; CALL @R12 dans la fonction de P
LIGNE_USINE = 0xC41C2            # expo_ligneProgramme
LECTURE_VMINI = 0xC452A          # 8 octets : LDI:20 #0x3D25B,R12 ; LDUB @R12,R0 ; LDI:8 #0xF,R1
SUITE_VMINI = 0xC4546            # R4 = vitesse mini, utilisée à partir d'ici
TABLE_VMINI = 0xFA876            # isoAuto_vitessesMini : 8 vitesses (1/125 … 1 s)

ISO_A = 0x3D25B                  # copie A de l'octet ISO auto du B (0x83CE974F)
EV = 0x3CCC2                     # Ev mesuré à l'ISO de base (1/48 IL)
OUV_MAX = 0x3D100                # ouverture maxi de l'objectif : Av = ×4
FOCALE = 0x3D0F0                 # focale codée : f = 5·2^(x/24) mm
PLANCHER = 0x3CCB9               # plancher d'ouverture (×8), lu par FUN_000c4680

# Programmes : valeur du quartet = 8 + p (p = 0x83CED24E côté B, 0 = Standard).
# (nom, Av cible, plancher : garder l'ouverture (l'ISO monte d'abord), vitesse mini de l'ISO auto)
# Av : f/5,6 = 240, f/8 = 288, f/11 ≈ 336 (f/11,3, multiple de 8 pour le plancher) ; Tv : 1/125 = 336,
# 1/250 = 384, 1/500 = 432. « focale » : 1/(focale × 1,5) = 2·x + 140 (recherche/programmes-expo-iso-auto.md).
PROGRAMMES = {
    9: ('Sujet rapide', 0, False, 0x1B0),      # pleine ouverture (butée de l'objectif), ISO pour tenir 1/500
    10: ('Portrait', 0, False, 0x150),         # pleine ouverture, ISO pour tenir 1/125
    11: ('Street', 240, True, 0x180),          # f/5,6, ISO pour tenir 1/250
    12: ('Profondeur', 336, True, 'focale'),   # f/11, ISO pour tenir 1/focale
    13: ('Piqué max', 'pique', True, 'focale'),  # pleine ouverture + 2 IL, bornée f/5,6 à f/8, ISO à 1/focale
}
PIQUE_ECART, PIQUE_MIN, PIQUE_MAX = 96, 240, 288


VERSIONS = {   # firmware (clé de patch.py), décalage du code par rapport à la 1.11, suffixe des fichiers produits
    '1.11': ('A', 0, ''),
    '1.12': ('A112', 0xF6, '-112'),
}
RAM_3E1 = {0: 0, 0xF6: 0x10}   # en 1.12 les variables 0x3E1xx sont décalées de 0x10 (le reste de la RAM est en place)


def code(dec=0):
    s = Asm(CODE)
    # --- ligne_perso : appelée (CALL) par la fonction de P à la place de la ligne d'usine ; rend Tv dans R4.
    # R8-R11 appartiennent à l'appelant ; R0-R7, R12, R13 libres (convention Fujitsu).
    s.label('ligne_perso')
    s.ldi(ISO_A, 12)
    s.ldub(12, 0)
    s.ldi8(0x0F, 1)
    s.and_(1, 0)                         # R0 = quartet bas
    s.cmpi(9, 0)
    s.b('lt', 'usine')
    s.cmpi(14, 0)
    s.b('ge', 'usine')
    s.ldi(EV, 12)
    s.lduh(12, 4)
    s.extsh(4)                           # R4 = Ev
    s.ldi(OUV_MAX, 12)
    s.ldub(12, 2)
    s.lsl(2, 2)                          # R2 = Av max de l'objectif (pleine ouverture)
    for v, (nom, av, plancher, _) in PROGRAMMES.items():
        s.cmpi(v, 0)
        s.b('eq', f'p{v}')
    s.b('ra', 'usine')
    for v, (nom, av, plancher, _) in PROGRAMMES.items():
        s.label(f'p{v}')
        if av == 'pique':
            s.mov(2, 3)
            s.ldi(PIQUE_ECART, 1)
            s.add(1, 3)                  # R3 = Av max + 2 IL
            s.ldi(PIQUE_MIN, 1)
            s.cmp(1, 3)
            s.b('ge', f'p{v}_min')
            s.mov(1, 3)
            s.label(f'p{v}_min')
            s.ldi(PIQUE_MAX, 1)
            s.cmp(1, 3)
            s.b('le', f'p{v}_max')
            s.mov(1, 3)
            s.label(f'p{v}_max')
        else:
            s.ldi(av, 3)
        s.b('ra', 'plancher' if plancher else 'fin')
    # plancher = max(plancher posé par expo_programme, Av cible / 8)
    s.label('plancher')
    s.mov(3, 1)
    s.lsr(3, 1)
    s.ldi(PLANCHER, 12)
    s.ldub(12, 5)
    s.cmp(5, 1)
    s.b('le', 'fin')
    s.stb(1, 12)
    s.label('fin')
    s.sub(3, 4)                          # R4 = Ev − Av cible
    s.ret()
    s.label('usine')
    s.ldi(LIGNE_USINE + dec, 12)
    s.jmp_r(12)                          # saut : la ligne d'usine rend directement à la fonction de P

    # --- vitesse_mini : atteinte par JMP depuis 0xC452A (expo_limiterVitesse, ISO auto actif, ni S ni M) ;
    # rend R4 = vitesse mini, puis saute en 0xC4546. Ne touche que R0, R1, R4, R12, R13 (comme l'original).
    s.align()
    s.label('vitesse_mini')
    s.ldi(ISO_A, 12)
    s.ldub(12, 0)
    s.ldi8(0x0F, 1)
    s.and_(1, 0)
    s.cmpi(8, 0)
    s.b('lt', 'vm_table')
    for v, (nom, _, _, tv) in PROGRAMMES.items():
        s.cmpi(v, 0)
        s.b('eq', f'vm{v}')
    s.ldi(0x150, 4)                      # 8, 14, 15 : sans Programme, 1/125 (valeur sûre)
    s.b('ra', 'vm_retour')
    for v, (nom, _, _, tv) in PROGRAMMES.items():
        s.label(f'vm{v}')
        if tv == 'focale':
            s.ldi(FOCALE, 12)
            s.ldub(12, 4)
            s.lsl(1, 4)
            s.ldi(140, 1)
            s.add(1, 4)                  # 1/(focale × 1,5)
        else:
            s.ldi(tv, 4)
        s.b('ra', 'vm_retour')
    s.label('vm_table')                  # lecture d'origine (0xC4534-0xC453E)
    s.ldi(TABLE_VMINI, 13)
    s.lsl(1, 0)
    s.lduh13(0, 4)
    s.extsh(4)
    s.label('vm_retour')
    s.ldi(SUITE_VMINI + dec, 12)
    s.jmp_r(12)
    return s


def mot(b, adr, n):
    return b[adr - BASE_A:adr - BASE_A + n]


def remplace(b, adr, avant, apres, texte):
    assert mot(b, adr, len(avant)) == avant, (hex(adr), mot(b, adr, len(avant)).hex(), avant.hex())
    return {'offset': hex(adr - BASE_A), 'avant': {'hex': avant.hex()}, 'apres': {'hex': apres.hex()}, 'texte': texte}


def construire_patchs(orig, dec=0):
    s = code(dec)
    c = s.octets()
    assert CODE + len(c) <= FIN_LIBRE, hex(CODE + len(c))
    assert set(mot(orig, CODE, len(c))) == {0xFF}
    ligne, vmini = s.labels['ligne_perso'], s.labels['vitesse_mini']
    assert ligne < 0x100000 and vmini < 0x100000            # atteignables par LDI:20
    return [
        remplace(orig, CODE, mot(orig, CODE, len(c)), c,
                 f'ligne_perso et vitesse_mini ({len(c)} octets, place libre {CODE:#x}-{FIN_LIBRE - 1:#x})'),
        remplace(orig, APPEL_LIGNE + dec, struct.pack('>HH', 0x9BCC, (LIGNE_USINE + dec) & 0xFFFF),
                 struct.pack('>HH', 0x9B0C | (ligne >> 16) << 4, ligne & 0xFFFF),
                 'fonction de P : LDI:20 #0xC41C2 (ligne d\'usine) → #ligne_perso, CALL @R12 inchangé'),
        remplace(orig, LECTURE_VMINI + dec, bytes.fromhex('9b3cd25b06c0c0f1'),
                 struct.pack('>HHHH', 0x9B0C | (vmini >> 16) << 4, vmini & 0xFFFF, 0x970C, 0x9FA0),
                 'expo_limiterVitesse : lecture de la vitesse mini de l\'ISO auto → JMP vitesse_mini (8 octets, '
                 'hors créneau de délai ; LDI:20 #vitesse_mini,R12 ; JMP @R12 ; NOP)'),
    ]


def construire(ecrire=True, version='1.11'):
    cle, dec, suffixe = VERSIONS[version]
    orig = bytes(patchpy.charger_original(cle))
    patchs = construire_patchs(orig, dec)
    doc = {'firmware': cle,
           'description': f'Lignes de programme (Sujet rapide, Portrait, Street, Profondeur, Piqué max) dans le A {version}, '
                          'activées par le quartet bas 9 à 13 de l\'octet ISO auto envoyé par le B (étape 9 du '
                          'Pip-Boy). Mise au point dans l\'émulateur du A ; flash à décider (recherche/etude-a/).',
           'patchs': patchs}
    if ecrire:
        nom = f'a-programmes{suffixe}.json'
        (PROJET / 'patchs' / nom).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'patchs/{nom} : {len(patchs)} patchs, code {len(patchs[0]["apres"]["hex"]) // 2} octets')
    return doc


# ---------------------------------------------------------------- scénario de contrôle (émulateur du A)

OBJECTIFS = {'50 mm f/1,8': (0x50, 0x14, 0x4C), '18 mm f/3,5 (zoom 18-55)': (0x2C, 0x2B, 0x30)}
CAS_EV = (2, 6, 10, 14, 18)
CAS_VALEURS = (0xB0, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD)   # ISO auto, ISO maxi 1600 ; Standard puis les 5 Programmes


def etat(focale, ouv, etendue, flash, valeur, ev, dec=0):
    """Pokes d'un cas : P, objectif à puce, ISO 200, ISO auto actif ; Ev en IL → mesure cf68 (FUN_000c4064)."""
    corr = 0 if ouv >> 1 < 7 else 8 if ouv >> 1 > 12 else 4
    cf68 = ev * 48 - 8 * 0x24 + corr
    r = RAM_3E1[dec]
    return [f'poke8 0x3C3C0 0', f'poke8 0x3C3C1 {flash}', 'poke8 0x3C3C4 0', f'poke8 {0x3E1E0 + r:#x} 0', 'poke8 0x3D0E6 1',
            f'poke8 0x3D0F0 {focale:#x}', f'poke8 0x3D100 {ouv:#x}', f'poke8 0x3D0F3 {etendue:#x}', 'poke8 0x3D0B2 0',
            'poke8 0x3D105 0', f'poke8 {0x3E1EE + r:#x} 0x24', 'poke8 0x3D0BC 2', f'poke8 0x3D25B {valeur:#x}',
            f'poke16 0x3CF68 {cf68 & 0xFFFF:#x}', f'appel {0xC3F84 + dec:#x}']


def cas():
    for nom, (f, o, e) in OBJECTIFS.items():
        for flash in (0, 3):
            for v in CAS_VALEURS:
                for ev in CAS_EV:
                    yield nom, f, o, e, flash, v, ev


def mesurer(firmware, dec=0):
    """Joue tous les cas dans l'émulateur du A et rend [(ccb2, ccb4, ccbc)] (Tv/2, Av/2, ISO)."""
    import subprocess
    import tempfile
    lignes = ['run 2M']
    for _, f, o, e, flash, v, ev in cas():
        lignes += etat(f, o, e, flash, v, ev, dec) + ['peek 0x3CCB2 4', 'peek 0x3CCBC 1']
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as t:
        t.write('\n'.join(lignes) + '\n')
    r = subprocess.run([sys.executable, str(PROJET / 'emulateur' / 'd40emu.py'), 'a-scenario', t.name,
                        '--firmware-a', str(firmware)], capture_output=True, text=True)
    vals = [l.split(':')[1].split() for l in r.stdout.splitlines() if l.startswith('  3CCB2 :') or l.startswith('  3CCBC :')]
    out = []
    for i in range(0, len(vals), 2):
        b = [int(x, 16) for x in vals[i]]
        out.append((b[0] << 8 | b[1], b[2] << 8 | b[3], int(vals[i + 1][0], 16)))
    return out


def ecrire_scenario(firmware_patche, version='1.11'):
    """emulateur/scenarios/a-programmes.txt : Standard comparé au A de Nikon, Programmes figés (validés à la main
    en octobre 2026 : ouverture visée, vitesse mini, ISO, exposition juste)."""
    cle, dec, suffixe = VERSIONS[version]
    nikon = mesurer(patchpy.ORIGINAUX[cle][0], dec)
    patche = mesurer(firmware_patche, dec)
    assert len(nikon) == len(patche) == len(list(cas()))
    l = ['# Processeur A : lignes de programme (outils/programmes_a.py, patchs/a-programmes.json), chaîne complète',
         '# expo_programme (0xC3F84). Écrit par « programmes_a.py scenario » : Standard (quartet 0) doit rendre',
         '# exactement les valeurs du A de Nikon ; les Programmes (9 à 13) les valeurs validées à la main.',
         '# À jouer avec --firmware-a sur le A patché (a-verifier le fabrique).',
         'run 2M']
    for (nom, f, o, e, flash, v, ev), n, p in zip(cas(), nikon, patche):
        if v == 0xB0:
            assert n == p, (nom, flash, ev, n, p)        # Standard : identique au A de Nikon
        prog = PROGRAMMES.get(v & 0xF, ('Standard',))[0]
        l.append(f'# {prog}, {nom}, {"flash" if flash else "sans flash"}, Ev {ev}')
        l += etat(f, o, e, flash, v, ev, dec)
        l += [f'expect16 0x3CCB2 {p[0]:#06x}', f'expect16 0x3CCB4 {p[1]:#06x}', f'expect8 0x3CCBC {p[2]:#04x}']
    nom = f'a-programmes{suffixe}.txt'
    l[3] = f'# À jouer avec --firmware-a sur le A {version} patché (a-verifier le fabrique).'
    (PROJET / 'emulateur' / 'scenarios' / nom).write_text('\n'.join(l) + '\n', encoding='utf-8')
    print(f'emulateur/scenarios/{nom} : {len(nikon)} cas, dont '
          f'{sum(1 for c in cas() if c[5] == 0xB0)} Standard identiques au A de Nikon')


def self_test():
    for version, (cle, dec, _) in VERSIONS.items():
        orig = bytes(patchpy.charger_original(cle))
        s = code(dec)
        c = s.octets()
        # aucune forme à créneau de délai dans le code ajouté (CALL:D, JMP:D, RET:D, Bcc:D)
        mots = [struct.unpack('>H', c[i:i + 2])[0] for i in range(0, len(c), 2)]
        assert not any(m in (0x9F0C, 0x9F1C, 0x9F20) or (m & 0xF000) == 0xF000 for m in mots)
        # les deux points d'accroche sont ceux attendus (et hors créneau de délai)
        assert mot(orig, APPEL_LIGNE + dec, 6) == struct.pack('>HHH', 0x9BCC, (LIGNE_USINE + dec) & 0xFFFF, 0x971C)
        assert mot(orig, LECTURE_VMINI + dec - 2, 2).hex() == 'e20b'        # BEQ (sans créneau) juste avant
        assert mot(orig, LECTURE_VMINI + dec, 16).hex() == '9b3cd25b06c0c0f182109bfda876b410'
        assert mot(orig, SUITE_VMINI + dec - 2, 2) == mot(patchpy.charger_original('A'), SUITE_VMINI - 2, 2)
        # la ligne d'usine, la fonction de P et expo_limiterVitesse de la 1.12 sont celles de la 1.11, décalées :
        # mot à mot identiques, à une adresse près (code +0xF6, variables 0x3E1xx +0x10)
        a111 = bytes(patchpy.charger_original('A'))
        for adr, n in ((LIGNE_USINE, 0x80), (0xC60E2, 0x80), (0xC441E, 0x168)):
            x, y = mot(a111, adr, n), mot(orig, adr + dec, n)
            ecarts = {(y[i] << 8 | y[i + 1]) - (x[i] << 8 | x[i + 1]) for i in range(0, n, 2)}
            assert ecarts <= {0, dec, RAM_3E1[dec]}, (version, hex(adr), ecarts)
        b = bytes(patchpy.appliquer(bytearray(orig), construire_patchs(orig, dec)))
        assert struct.unpack('>H', b[APPEL_LIGNE + dec + 2 - BASE_A:][:2])[0] == s.labels['ligne_perso'] & 0xFFFF
        # rien hors des trois zones
        diff = [i for i in range(len(orig) - 2) if orig[i] != b[i]]
        zones = [(CODE, CODE + len(c)), (APPEL_LIGNE + dec, APPEL_LIGNE + dec + 4),
                 (LECTURE_VMINI + dec, LECTURE_VMINI + dec + 8)]
        assert all(any(lo <= i + BASE_A < hi for lo, hi in zones) for i in diff)
        print(f'self-test {version} OK : code {len(c)} octets en {CODE:#x}, ligne_perso {s.labels["ligne_perso"]:#x}, '
              f'vitesse_mini {s.labels["vitesse_mini"]:#x}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['construire', 'scenario'])
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.action == 'construire':
        for v in VERSIONS:
            construire(version=v)
        return 0
    if a.action == 'scenario':
        import subprocess
        import tempfile
        for v, (cle, _, _) in VERSIONS.items():
            doc = construire(ecrire=False, version=v)
            d = pathlib.Path(tempfile.mkdtemp())
            (d / 'p.json').write_text(json.dumps(doc), encoding='utf-8')
            subprocess.run([sys.executable, str(PROJET / 'patch.py'), str(d / 'p.json'), '--sortie', str(d)], check=True,
                           capture_output=True)
            ecrire_scenario(d / patchpy.ORIGINAUX[cle][2], v)
        return 0
    ap.print_help()


if __name__ == '__main__':
    sys.exit(main())
