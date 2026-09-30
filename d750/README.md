# Nikon D750 : neuf Picture Control calculés et chargés par USB

Le firmware n'est pas touché. Le D750 accepte, par la commande USB que Nikon prévoit pour Camera Control Pro (PTP `0x90CD` SetPicCtrlData), un Picture Control complet dans ses emplacements C-1 à C-9 : une base, des crans, un nom, et une courbe perso de 257 points. Ce dossier contient les outils qui le pilotent depuis un Mac, l'analyse qui a mesuré ce que fait chaque réglage, et les neuf recettes qui en sortent.

| C- | Nom dans le boîtier | Base | Saturation, teinte / filtre | Balance des blancs | Recette |
|---|---|---|---|---|---|
| 1 | KODACHROME | Standard | −1, −3 | **6 250 K**, à régler à la main (préréglage d-1) | [`kodachrome-v2.json`](recettes/d750-v1/usb/kodachrome-v2.json) |
| 2 | CLASSIC CHROME | Standard | −1, −2 | 5 600 K | [`classic-chrome-v1.json`](recettes/d750-v1/usb/classic-chrome-v1.json) |
| 3 | CLASSIC NEG | Standard | 0, 0 | 5 600 K | [`classic-neg-v1.json`](recettes/d750-v1/usb/classic-neg-v1.json) |
| 4 | POSITIVE | Standard | +2, −2 | 5 600 K | [`positive-v1.json`](recettes/d750-v1/usb/positive-v1.json) |
| 5 | PORTRA 400 | Standard | +3, +2 | **5 600 K**, dans U2 | [`portra-400-v2.json`](recettes/d750-v1/usb/portra-400-v2.json) |
| 6 | HASSELBLAD | Standard | +1, −3 | 5 600 K | [`hasselblad-v1.json`](recettes/d750-v1/usb/hasselblad-v1.json) |
| 7 | TRI-X | Monochrome | filtre aucun | **10 000 K**, dans U1 | [`tri-x.json`](recettes/d750-v2/usb/tri-x.json) (Tri-X v2, [`recettes/d750-v2/`](recettes/d750-v2/README.md) ; la v1 : [`tri-x-v1.json`](recettes/d750-v1/usb/tri-x-v1.json)) |
| 8 | HP5+ | Monochrome | filtre aucun | 5 600 K | [`hp5-v1.json`](recettes/d750-v1/usb/hp5-v1.json) |
| 9 | FP4+ | Monochrome | filtre aucun | 5 600 K | [`fp4-v1.json`](recettes/d750-v1/usb/fp4-v1.json) |

Toutes : contraste et luminosité gérés par la courbe, D-Lighting actif désactivé, espace sRGB. Les blocs exacts tels que relus dans le boîtier après écriture sont dans [`recettes/d750-v1/blocs/`](recettes/d750-v1/blocs/) et, pour le Tri-X v2, [`recettes/d750-v2/blocs/`](recettes/d750-v2/blocs/) (identiques, à l'octet près, à ce que fabrique `picture_control.py bloc` depuis les `.json`). Écarts prévus et détail : [`recettes/d750-v1/README.md`](recettes/d750-v1/README.md) ; écarts mesurés (lot de contrôle d’octobre 2026) : [`recherche/resultats-mesures.md`](recherche/resultats-mesures.md).

> **La balance des blancs fait partie de la recette : toujours en Kelvin, jamais en Auto.** Kodachrome **6 250 K**, Tri-X **10 000 K**, tous les autres **5 600 K**. Un Picture Control ne mémorise pas la balance des blancs, et chaque recette a été calculée pour une température donnée : en Auto, le boîtier déplace les couleurs à chaque photo et le look ne ressemble plus à sa cible (par la fenêtre, à main levée en Auto, le Kodachrome était à 10 de ΔE ; sur trépied à 6 250 K, à 4,1 : images dans [`../README.md`](../README.md), « Ce que ça fait »).

Tri-X et Portra gardent leur balance dans les modes utilisateur U1 et U2 ; pour le Kodachrome, il faut la régler (préréglage d-1).

## Prérequis

- Un Mac, Swift (`xcode-select --install`) ; les outils parlent au boîtier par ImageCaptureCore, sans rien installer d'autre.
- Python 3.10 ou plus, `pip install -r ../requirements.txt` (pour fabriquer les blocs : rien d'autre que la bibliothèque standard) ; `exiftool` pour ranger les séances (`brew install exiftool`).
- D750 en firmware C 1.15 (c'est celui qui a été lu ; la 1.10 a la même logique, [`recherche/d750-picture-control-usb.md`](recherche/d750-picture-control-usb.md) §7).
- Boîtier allumé, câble USB, mode P, S, A ou M, **pas en prise de vue ni en U1 / U2** (sinon refus `0x2019` ou `0x200F`), Photos et Transfert d'images fermés.

## Charger les neuf recettes

Depuis la racine du dépôt (zsh ou bash) :

```
while read n nom; do
  python3 d750/outils/picture_control.py bloc d750/recettes/$nom.json /tmp/d750-C$n.bin
  swift d750/outils/d750_ecrire.swift ecrire /tmp/d750-C$n.bin C-$n            # simulation : rien n'est écrit
done <<FIN
1 d750-v1/usb/kodachrome-v2
2 d750-v1/usb/classic-chrome-v1
3 d750-v1/usb/classic-neg-v1
4 d750-v1/usb/positive-v1
5 d750-v1/usb/portra-400-v2
6 d750-v1/usb/hasselblad-v1
7 d750-v2/usb/tri-x
8 d750-v1/usb/hp5-v1
9 d750-v1/usb/fp4-v1
FIN
```

Si les neuf simulations sont propres, relancer la boucle en ajoutant `--ecrire` à la ligne `swift` (et `--remplacer` pour un emplacement déjà occupé : la simulation le signale ; l'ancien contenu est sauvé avant). L'outil relit chaque emplacement après écriture et le compare à l'envoi. Chaque lancement laisse un journal dans `d750/sondes/d750/usb/ecriture-<date>/` (hors git) : contenu d'avant, bloc envoyé, contenu relu. Revenir en arrière : `swift d750/outils/d750_ecrire.swift ecrire <dossier>/avant_20n_0.bin C-n --ecrire --remplacer`, ou effacer : `… effacer C-n --ecrire`, ou le menu du boîtier.

Ensuite, dans le boîtier :
- **U1** : C-7 TRI-X, balance 10 000 K ; **U2** : C-5 PORTRA 400, balance 5 600 K (menu Configuration › Enregistrer réglages utilisateur) ;
- contrôle : menu Prise de vue › Régler le Picture Control : C-1 à C-9 portent les noms du tableau.

## Balance des blancs : préréglages d-1 à d-6

Le D750 a six préréglages manuels de balance (d-1 à d-6). Par USB, leurs **commentaires** s'écrivent (propriétés `0xD021` à `0xD024`, `0xD038`, `0xD039`), leurs **valeurs** non (lecture seule ; `0x90C9` SetPreWBData n'est pas documentée). Sur mon boîtier : d-1 « KODACHROME 6250K », d-2 « TRI-X 10000K », d-3 « PORTRA 400 5600K ». La valeur se charge par le menu : prendre une photo à la bonne température (mode K), puis Balance des blancs › Pré-réglage manuel › choisir le préréglage › Choisir une photo. Détail : [`recherche/d750-picture-control-usb.md`](recherche/d750-picture-control-usb.md) §10.

## Refaire les recettes pour soi (séances d'essais)

C'est la boucle de [`../METHODE.md`](../METHODE.md), automatisée :

1. **Préparer** : trépied, scène fixe (couleurs variées ; une séance sur un visage pour la peau), mode M, ISO fixe, mise au point manuelle, balance des blancs en mode K, D-Lighting actif coupé, NEF + JPEG fine, ni U1 ni U2.
2. **Plan** : `python3 d750/outils/d750_seance.py plan <chantier>/lot1` écrit `plan.json` et un bloc par vue (les sept bases, les crans de saturation, teinte et contraste, des courbes d'essai ; `--lot portrait`, `--lot complement`, `--lot v1`, `--lot v2-<K>` pour les autres lots).
3. **Séance** : `swift d750/outils/d750_seance.swift <chantier>/lot1 --simulation`, puis sans `--simulation`. Pour chaque vue : bloc écrit dans C-9, activé, déclenché, NEF et JPEG rapatriés ; à la fin, C-9 et le Picture Control actif sont remis comme avant. `--kelvin N` règle la température pour la séance ; `--depuis N` reprend après une coupure. Si C-9 contient déjà un Picture Control qui n'est pas une vue de séance (c'est le cas dès que les neuf recettes sont chargées), l'outil s'arrête : ajouter `--remplacer`, il le sauve dans `avant_c9.bin` et le remet à la fin. À la reprise (`--depuis N`), l'outil relit le contenu d'origine dans `avant_c9.bin` au lieu de le réécrire : C-9 retrouve bien son état de départ.
4. **Ranger** : `python3 d750/outils/d750_seance.py ranger <chantier>/lot1` classe chaque fichier d'après le nom du Picture Control noté dedans (le NEF arrive quelques secondes après le JPEG).
5. **Analyser** : extraction des blocs uniformes, modèle du boîtier, meilleures bases, noir et blanc, balance, validation, recettes : commandes dans [`recherche/d750-analyse-seances.md`](recherche/d750-analyse-seances.md) §8 (`d750_blocs.py`, `d750_analyse.py`), à lancer depuis `d750/` et à écrire hors du dépôt (`blocs/`, `res/`). Elles supposent les cinq lots de l'auteur (`lot1` à `lot5`, objectifs et vignetage : en tête de `d750_analyse.py`) : pour d'autres scènes ou d'autres objectifs, adapter ces constantes. Les résultats de mes séances (`modele.json`, `bases.json`, `nb.json`, `balance.json`, `validation.json`) sont dans [`recherche/donnees-films/d750-seances/`](recherche/donnees-films/d750-seances/) : les recettes s'en refont sans les images.
6. **Contrôler** : charger, photographier les recettes chargées, mesurer (`mesures_reelles.py`, écrit pour les lots de test de l'auteur : chemins `images/…` et recettes v1 en tête du fichier, à adapter). Le lot de contrôle [`outils/d750_lot_v2.sh`](outils/d750_lot_v2.sh) enchaîne tout : relit C-1 à C-9 et s'arrête si le boîtier diffère de l'historique, charge le Tri-X v2, puis six passages à six températures (19 vues). Protocole : [`recettes/d750-v2/README.md`](recettes/d750-v2/README.md).

Tenir l'historique de son boîtier : `python3 d750/outils/d750_historique.py` refait `recettes/d750/HISTORIQUE.md` depuis les journaux d'écriture (celui du dépôt est celui de mon boîtier) ; `--comparer <lecture>` confronte une lecture du boîtier (`swift d750/outils/d750_ptp.swift <dossier>`, lecture seule) à l'historique.

Cibles qui ne sont pas dans le dépôt (voir [`../LICENCES-TIERS.md`](../LICENCES-TIERS.md)) : LUT F-Log2 de Fujifilm (dossier `fuji-lut/` à la racine de `d750/`), réponses Status A d'agx-emulsion (en-tête de [`outils/kodachrome.py`](outils/kodachrome.py)), table Kodachrome de spektrafilm (variable `D750_SPEKTRAFILM`, [`outils/d750_spektrafilm.py`](outils/d750_spektrafilm.py)), profils Lightroom pour Tri-X et Portra (variable `D750_LOOKS`).

## Les outils

| Outil | Rôle | Écrit dans le boîtier ? |
|---|---|---|
| `picture_control.py` | fichiers NCP / NP2 ; `ptp` décode un bloc lu ; `bloc` fabrique un bloc depuis une recette `.json` (refuse toute valeur hors des plages du boîtier) ; `--self-test` | non |
| `d750_ptp.swift` | sonde en lecture seule : DeviceInfo, propriétés, C-1 à C-9, capacités | non |
| `d750_ecrire.swift` | écrire, effacer, activer un Picture Control perso ; simulation par défaut, `--ecrire` pour écrire | oui, C-1 à C-9 seulement |
| `d750_seance.py` + `d750_seance.swift` | séances d'essais pilotées (plan, prise de vue, rapatriement, rangement) | C-9, remis comme avant |
| `d750_lot_v2.sh` | lot de contrôle n° 2 | C-7 (Tri-X v2) et C-9 |
| `d750_historique.py` | historique de C-1 à C-9 et comparaison à une lecture | non |
| `d750_blocs.py`, `d750_modele.py`, `d750_analyse.py`, `d750_cibles.py`, `d750_figures.py`, `d750_comparer.py`, `d750_leviers.py`, `d750_standard.py` | analyse des séances, modèle du boîtier, cibles, recettes | non |
| `mesures_reelles.py` | écarts réels : JPEG du boîtier contre la cible | non |
| `kodachrome.py`, `d750_spektrafilm.py`, `films_nb.py`, `fiches_vectorielles.py`, `fuji_lut.py`, `dcp.py`, `matrices_spectrales.py` | cibles : fiches Kodak et Ilford, spektrafilm, LUT Fujifilm, profils DNG | non |
| `d750_firmware.py`, `references.sh` | ouvrir le firmware officiel (déchiffrement, CRC, table PTP, désassemblage) et rapatrier les références tierces, pour l'étude seulement | non |
| `raw_lineaire.swift` | développer un RAW (NEF, RAF…) en sRGB linéaire par le décodeur de macOS, comme référence « scène » | non |

Le format exact du bloc (octet par octet, plages acceptées, règles d'écriture, codes de réponse) et la preuve de chaque point : [`recherche/d750-picture-control-usb.md`](recherche/d750-picture-control-usb.md).
