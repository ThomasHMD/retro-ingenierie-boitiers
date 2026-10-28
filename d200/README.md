# Nikon D200 : firmware modifié, cinq rendus en JPEG direct

Même démarche que pour le D40 : le firmware B 2.01 est cartographié, émulé, puis modifié **par données seulement** (tables de rendu, courbes, textes du menu), à partir du fichier officiel de Nikon. **V2 flashée et validée par l'auteur sur son boîtier (octobre 2026).**

## Télécharger ou refaire

- **Prête à flasher** (firmware Nikon modifié, fourni pour commodité, sans garantie ; droits de Nikon réservés) : [`d200-v2.zip`](https://github.com/ThomasHMD/retro-ingenierie-boitiers/releases/download/d200-v2/d200-v2.zip), avec son `LISEZMOI.txt`.
- **La refaire** depuis le firmware officiel : télécharger chez Nikon la mise à jour 2.01 du D200 (`F-D200-V201W.exe`), l'ouvrir avec `unar`, ranger `B2000201.bin` dans `~/Library/Caches/retro-ingenierie-boitiers/firmware/d200-201/` (ou le dossier de la variable `D200_FIRMWARE`), puis, depuis la racine du dépôt :

```bash
python3 d40/patch.py d200/patchs/d200-v2.json --sortie <dossier>
```

`patch.py` vérifie le sha256 du firmware officiel et chaque octet d'origine (par son empreinte), refuse tout patch hors des plages que la mise à jour réécrit ou dans le flasheur, recalcule le CRC et écrit `B2000201.BIN`, de sha256 `428473ff8f915932327add759fd68dcec6c4c5ae2e0ce7b0c6530403e4aedbce`.

## Flasher

1. Configuration › Version du firmware : lire **A 2.01 et B 2.01**. Toute autre version : ne pas flasher.
2. Batterie EN-EL3e pleine, ou adaptateur secteur : une coupure pendant l'écriture est le seul vrai risque de brique.
3. Préparer d'abord une **carte de retour** : une carte formatée dans le D200, avec seulement le `B2000201.bin` officiel de Nikon (sha256 `b7cee24dd2034645337cca500109d2ce987bee4ba8bfb521c3285c623f3407d1`) à la racine.
4. Carte de flash formatée dans le D200, `B2000201.BIN` modifié seul à la racine ; contrôler son sha256.
5. Configuration › Version du firmware › mise à jour › Oui ; ne rien toucher jusqu'au message de fin ; éteindre, rallumer.
6. Contrôle : Optimiser l'image affiche Normale, Chrome, Positive, FP4, HP5, Personnalisée, Tri-X.

Retour à Nikon : même procédure avec la carte de retour. Les rendus ne s'exécutent qu'à la prise de vue et les textes ne servent qu'aux menus : le menu Configuration reste joignable pour reflasher. Flasher un firmware modifié se fait à ses risques (voir le README principal, « Cadre légal »).

## Ce que fait la V2

| Entrée de Nikon | Devient | Cible |
|---|---|---|
| Normal, Personnalisé | inchangées | |
| Moins net | **Chrome** | Classic Chrome mesuré (paires RAW + JPEG) |
| Saturé | **Positive** | Positive Film mesuré (Ricoh GR III) |
| Très saturé | **FP4** | fiche Ilford |
| Portrait | **HP5** | fiche Ilford |
| Noir et blanc | **Tri-X** | d'après un preset acheté que j'aimais beaucoup, contrôlé sur la fiche Kodak |

La V2 ne change que des données (les quatre emplacements des rendus et la courbe Tri-X) et le CRC, aucun code ; tous les contrôles de l'émulateur passent ; une relecture indépendante l'a validée avant le flash : [`recherche/d200-v2-relecture.md`](recherche/d200-v2-relecture.md).

- **V1** : flashée et vérifiée vue par vue, mais les rendus se ressemblaient trop : Chrome et Positive à ΔE2000 médian 1,0 à 1,3 l'un de l'autre, les trois noir et blanc à 5 à 10 niveaux sur 255 les uns des autres.
- **Couleur, V2** : pour Chrome et Positive, la matrice et l'étage à 16 secteurs sont ajustés ensemble sur les paires RAW + JPEG des boîtiers d'origine. Les écarts les plus forts baissent (Chrome, 90e centile : 1,9 → 1,6 sur des images tenues à part). Puis un typage voulu : saturation × 0,8 pour Chrome, × 1,2 pour Positive, ce qui double l'écart entre les deux (de 2,4 à 5,4 et de 1,4 à 3,2 selon la vue).
- **Noir et blanc, V2** : chaque film a son propre papier de tirage, le gris de la scène gardé à 118.

  | Film | Tirage | Niveaux de −2 à +2 IL |
  |---|---|---|
  | Tri-X | papier dur, noirs profonds, blancs francs | 17 / 47 / 118 / 200 / 241 |
  | HP5 | papier doux, noirs mats | 55 / 78 / 118 / 162 / 203 |
  | FP4 | contraste moyen, hautes lumières longues | 34 / 64 / 118 / 180 / 224 |

Les rendus en images (simulations, qui retombent sur le JPEG du boîtier au plancher de la mesure près) : [`../README.md`](../README.md#le-nikon-d200-en-simulation).

## Ce qu'on a appris

- **L'étage couleur à 16 secteurs est décodé.** Une roue de 48 teintes photographiée par USB, puis trois sondes flashées (chacune ne change que des données, relue avant le flash : `patchs/d200-sonde-secteurs*.json`) : 16 nœuds tous les 22,5° de teinte dans le plan (Cb, Cr), chacun portant une matrice 2×2, avec interpolation linéaire entre deux nœuds voisins. L'écart entre le simulateur et le JPEG du boîtier, mesuré en (Cb, Cr), passe de 5,5-7,1 à 1,1-1,4, soit le plancher de la mesure (1,3 sur un témoin neutre) ; sur les réglages de Nikon, qui n'ont pas servi à construire le modèle, il baisse de 19 à 38 %. Code : [`outils/d200_etage.py`](outils/d200_etage.py) ; détail : [`recherche/d200-preglages.md`](recherche/d200-preglages.md) §7.
- Le firmware, ses tables d'image, ses textes et les zones à ne jamais toucher : [`recherche/d200-firmware-image.md`](recherche/d200-firmware-image.md) ; quelle table pour quel rendu : [`recherche/d200-choix-des-tables.md`](recherche/d200-choix-des-tables.md) ; ce que l'USB permet : [`recherche/d200-ptp-usb.md`](recherche/d200-ptp-usb.md).

## Dossiers

| Dossier | Contenu |
|---|---|
| [`outils/`](outils/) | simulateur du JPEG d'après les tables du firmware, étage à 16 secteurs, rendus couleur et noir et blanc, préréglages (patch combiné), textes du menu, pilotage USB (sondes, séances) |
| [`patchs/`](patchs/) | `d200-v2.json` (la V2 complète), ses morceaux, la V1 et les sondes de mesure ; octets de Nikon donnés par leur empreinte |
| [`recettes/`](recettes/) | `etage-v2.json` (matrices et 16 secteurs ajustés), `matrices.json` |
| [`emulateur/`](emulateur/README.md) | exécute les fonctions du moteur d'image du firmware dans le cœur FR de l'émulateur du D40, pour vérifier un patch avant le flash |
| [`desassemblage/`](desassemblage/) | symboles et scripts Ghidra pour refaire l'analyse depuis le firmware officiel |
| [`recherche/`](recherche/) | les rapports |
| [`sondes/usb/`](sondes/usb/) | lectures USB brutes du boîtier (réglages, banques, courbes), numéro de série effacé |

Les outils du D200 réutilisent ceux du D40 (`d40/outils/`, `d40/patch.py`, l'émulateur) et ses rendus mesurés (`d40/recettes/mesures/`).
