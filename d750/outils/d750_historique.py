#!/usr/bin/env python3
"""Historique des Picture Control écrits dans le D750 (C-1 à C-9), refait depuis les journaux de d750_ecrire.swift
(sondes/d750/usb/ecriture-*/ : contenu avant, bloc envoyé, contenu relu après). Chaque écriture y laisse son dossier : il
suffit de relancer ce script pour que recettes/d750/HISTORIQUE.md soit à jour, rien n'est tenu à la main.

  d750_historique.py              réécrit recettes/d750/HISTORIQUE.md
  d750_historique.py --verifier   code 1 si HISTORIQUE.md n'est pas à jour
  d750_historique.py --comparer <dossier de d750_ptp.swift> [<dossier du lot>]   le boîtier relu contient-il ce que dit
      l'historique ? (code 1 sinon). Avec le dossier du lot : C-9 portant une vue de séance est accepté si un avant_c9.bin
      du lot contient ce que dit l'historique (passage coupé ; la reprise de d750_seance.swift remet C-9).

Revenir à un état : `swift outils/d750_ecrire.swift ecrire <fichier .bin de la table> C-n` (simulation), puis avec
`--ecrire --remplacer`. Les séances de calibration (d750_seance.swift) n'écrivent que C-9 et le remettent comme avant :
elles ne figurent pas ici.
"""
import glob
import hashlib
import os
import pathlib
import sys

ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
import picture_control as pc  # noqa: E402

USB = RACINE / 'sondes' / 'd750' / 'usb'
SORTIE = RACINE / 'recettes' / 'd750' / 'HISTORIQUE.md'
# d'où vient chaque bloc (sha256, 10 premiers caractères) ; un bloc absent d'ici est marqué « source à noter »
SOURCES = {
    '211ef3ff35': 'réglage de Thomas, avant le projet', '756065ee40': 'réglage de Thomas, avant le projet',
    '7693e53eb2': 'réglage de Thomas, avant le projet', '77b6f62d5d': 'réglage de Thomas, avant le projet',
    '0f291c6bed': 'réglage de Thomas, avant le projet', 'fbea51fd81': 'réglage de Thomas, avant le projet',
    'ee3ab9eb85': 'Kodachrome v2 « vif » (cible spektrafilm × 1,2, WB 6 250 K), livraison d’octobre : `recettes/d750-v1/usb/kodachrome-v2.json`',
    '6c9a5a2457': 'Portra 400 v2 « esprit Portra », livraison d’octobre : `recettes/d750-v1/usb/portra-400-v2.json`',
    '84c713a2fa': 'Kodachrome v2 « vif », renommé sans version : `recettes/d750-v1/usb/kodachrome-v2.json`',
    '386743f90b': 'Portra 400 v2 « esprit Portra », renommé sans version : `recettes/d750-v1/usb/portra-400-v2.json`',
    '9f742fd580': 'Tri-X v2 (filtre aucun, courbe pour les gains réels de la WB à 10 000 K), `recettes/d750-v2/usb/tri-x.bin`',
}
LIVRAISON_V1 = 'première livraison d’octobre, recette v1 à courbe recalculée (`recettes/d750-v1/usb/`)'
RENOMME = 'même recette, renommée sans version (`recettes/d750-v1/usb/`)'
SOURCES.update({h: LIVRAISON_V1 for h in ('18f634f844', '1c732167d7', '16166240b4', '3a0f275ba6', '644b455b4c', 'd69e004783', '30a7b4aac6')})
SOURCES.update({h: RENOMME for h in ('a5e0c5f4e1', '78243f9ed1', '15397862f9', 'a9f2b16dfe', '27b0d557a6', 'c0c76b1152', 'c57325f623')})


def lire(f):
    b = open(f, 'rb').read()
    r = pc.lire_bloc_ptp(b)
    if not r.get('nom'):
        return None
    h = hashlib.sha256(b).hexdigest()[:10]
    if r['base'] == 'Monochrome':
        reg = f"filtre {r.get('filtre')}, contraste {r.get('contraste'):+g}"
    else:
        reg = f"saturation {r.get('saturation'):+g}, teinte {r.get('teinte'):+g}"
    reg += f", netteté {r.get('accentuation'):g}, clarté {r.get('clarte'):+g}" + (', courbe' if r.get('courbe') else '')
    source = SOURCES.get(h, 'source à noter')
    return dict(nom=r['nom'], base=r['base'], reglages=reg, sha=h, fichier=os.path.relpath(f, RACINE), source=source)


def ecritures():
    out = []
    for d in sorted(glob.glob(str(USB / 'ecriture-*'))):
        j = pathlib.Path(d, 'journal.txt')
        if not j.exists() or 'MODE ÉCRITURE' not in j.read_text(encoding='utf-8', errors='replace'):
            continue
        quand = os.path.basename(d).split('-', 1)[1]
        for f in sorted(glob.glob(os.path.join(d, 'apres_2??_0.bin'))):
            c = int(f[-9:-6]) - 200
            av = os.path.join(d, f'avant_{200 + c}_0.bin')
            out.append(dict(date=f'{quand[6:8]}/{quand[4:6]}/{quand[:4]} {quand[9:11]} h {quand[11:13]}', dossier=os.path.basename(d),
                            emplacement=c, avant=lire(av) if os.path.exists(av) else None, apres=lire(f)))
    return out


def texte():
    E = ecritures()
    etat = {}
    for e in E:
        etat[e['emplacement']] = e
    L = ['# D750 : historique des Picture Control C-1 à C-9', '',
         'Fichier refait par `python3 outils/d750_historique.py` depuis les journaux d\'écriture (`sondes/d750/usb/ecriture-*/`) : '
         'ne pas l\'éditer à la main. Revenir à n\'importe quel état : `swift outils/d750_ecrire.swift ecrire <fichier .bin> C-n` '
         '(simulation), puis avec `--ecrire --remplacer`. Les séances de test n\'écrivent que C-9 et le remettent comme avant.', '',
         '## Dans le boîtier aujourd\'hui', '',
         '| Emplacement | Nom | Base | Réglages | Source | Écrit le | Bloc (pour y revenir) |', '|---|---|---|---|---|---|---|']
    for c in range(1, 10):
        e = etat.get(c)
        if not e:
            L.append(f'| C-{c} | (jamais écrit par l\'outil) | | | | | |')
            continue
        a = e['apres']
        L.append(f"| C-{c} | {a['nom']} | {a['base']} | {a['reglages']} | {a['source']} | {e['date']} | `{a['fichier']}` (sha {a['sha']}) |")
    L += ['', '## Toutes les écritures', '', '| Date | Emplacement | Avant | Après | Bloc d\'avant (pour y revenir) |', '|---|---|---|---|---|']
    for e in E:
        av = e['avant']
        L.append(f"| {e['date']} | C-{e['emplacement']} | {av['nom'] + ' (' + av['source'] + ')' if av else 'vide'} | {e['apres']['nom']} "
                 f"(sha {e['apres']['sha']}) | {'`' + av['fichier'] + '`' if av else 'effacer : `d750_ecrire.swift effacer C-' + str(e['emplacement']) + '`'} |")
    L += ['', '## Hors Picture Control', '',
          '- Préréglages de balance d-1 à d-3 : commentaires « KODACHROME 6250K », « TRI-X 10000K », « PORTRA 400 5600K » écrits le '
          'octobre 2026 (`sondes/d750/usb/ecriture-2026-10.20/`, anciens commentaires sauvés en `avant_d02*.bin`). Les valeurs se '
          'chargent par le menu.',
          '- Modes U1 et U2 : réglés à la main dans le boîtier, non relus par USB.',
          '- Recettes v2 : [`recettes/d750-v2/`](../d750-v2/README.md) (Tri-X v2 écrit en C-7 en octobre 2026 au début du lot n° 2).', '']
    return '\n'.join(L)


def comparer(dossier, lot=None):
    etat = {}
    for e in ecritures():
        etat[e['emplacement']] = e['apres']
    ecart = 0
    for c in range(1, 10):
        f = pathlib.Path(dossier, f'pictctrl_{200 + c}_0.bin')
        try:
            lu = lire(f) if f.exists() and f.stat().st_size else None
        except Exception:   # noqa: BLE001 (réponse d'erreur du boîtier pour un emplacement vide)
            lu = None
        attendu = etat.get(c)
        same = (lu and attendu and lu['sha'] == attendu['sha']) or (lu is None and attendu is None)
        if not same and c == 9 and lot and attendu:
            sauves = [f for f in pathlib.Path(lot).glob('*/avant_c9.bin') if hashlib.sha256(f.read_bytes()).hexdigest()[:10] == attendu['sha']]
            if sauves:
                same = True
                print(f"C-9 : vue de séance laissée par un passage coupé ; l'original est dans {sauves[0]}, la reprise le remettra")
                continue
        ecart += not same
        print(f"C-{c} : {'conforme' if same else 'DIFFÉRENT'} : lu {lu['nom'] + ' ' + lu['sha'] if lu else 'vide ou absent'}, "
              f"historique {attendu['nom'] + ' ' + attendu['sha'] if attendu else 'vide'}")
    print('boîtier conforme à l’historique' if not ecart else f'{ecart} emplacement(s) différent(s) : écrits hors de l’outil, à noter')
    return ecart


if __name__ == '__main__':
    if len(sys.argv) in (3, 4) and sys.argv[1] == '--comparer':
        sys.exit(1 if comparer(*sys.argv[2:]) else 0)
    t = texte()
    if '--verifier' in sys.argv:
        ok = SORTIE.exists() and SORTIE.read_text(encoding='utf-8') == t
        print('HISTORIQUE.md à jour' if ok else 'HISTORIQUE.md à refaire : python3 outils/d750_historique.py')
        sys.exit(0 if ok else 1)
    SORTIE.write_text(t, encoding='utf-8')
    print(SORTIE)
