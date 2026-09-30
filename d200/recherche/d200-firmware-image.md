# D200 : le firmware B 2.01, moteur d'image, noir et blanc et mise à jour

Carte du firmware B du D200 (version 2.01, celle du boîtier de Thomas) pour des patchs de données comme sur le D40. Lecture seule : **rien n'a été flashé**. Chaque fait est marqué *vérifié* (lu dans le code ou les octets, à l'adresse donnée) ou *hypothèse*. Les adresses sont celles du processeur, fichier chargé en `0x50000` : **offset dans le fichier = adresse − 0x50000**.

Compagnons : [`d200-ptp-usb.md`](d200-ptp-usb.md) (ce qui se règle par USB sans firmware), `perspectives-d200-xt4-d750.md` §1 (ouverture du paquet, comparaison avec le D40).

## 1. En bref

- **Rendu couleur** : chaîne matrice caméra → courbe par canal → matrice YCbCr → étage à 16 secteurs → table de saturation, chargée dans la puce d'image (registres `0x5001xxxx`) par `isp_chargerPuce` avant chaque photo. 294 jeux de matrices, 21 courbes. Le simulateur rejoue la chaîne sur un NEF : ΔE2000 médian de 1,3 à 2,7 contre le JPEG du boîtier sur six NEF de « Test D200 ». Vérifié.
- **Noir et blanc** : matrice et ligne Y écrites en dur dans le code, une courbe de 4 096 octets, aucun réglage. Sépia et cyanotype existent dans le code mais l'interface ne les propose pas. Vérifié.
- **Firmware V2 prêt en octobre 2026** (§11) : `d200/build/v2/B2000201.BIN`, sha256 `428473ff8f915932327add759fd68dcec6c4c5ae2e0ce7b0c6530403e4aedbce`, relu (GO) ; mêmes entrées que la V1, Chrome et Positive « typés » avec l'étage à 16 secteurs, Tri-X, HP5, FP4 avec un tirage par film.
- **Firmware V1 flashé en octobre 2026** (§10 ; premières vues : `d200/images/2026-10-test-v1/`, chaque entrée applique son rendu, mais Chrome et Positive, Tri-X, HP5 et FP4 sont trop proches entre eux : `d200-preglages.md` §7) : `d200/build/v1/B2000201.BIN`. Normal et Personnalisé gardent le rendu de Nikon ; Moins net → **Chrome**, Saturé → **Positive**, Très saturé → **FP4**, Portrait → **HP5**, Noir et blanc → **Tri-X** ; noms du menu et aides en français. 37 patchs, vérifiés dans l'émulateur registre par registre.
- **Séance USB d’octobre 2026** (bibliothèque et pédalier, 25 vues chacune, `d200/images/2026-10-seance-*`, `analyse.txt`) : N&B simulé fidèle (ΔE2000 médian 0,58 à 0,64) ; courbes perso envoyées reproduites (1,5 à 1,8) ; chaque choix du menu associé à sa courbe intégrée (§3). Vérifié.
- **Mise à jour** : même famille que le D40 (signature « Q220FirmwareSignature », CRC16 XMODEM, taille fixe 0x3C0000), aucun contrôle de version, flasheur qui réécrit trois plages fixes. Ce qu'il ne faut pas toucher est listé au §6. Vérifié.

## 2. Fichiers et outils

| Quoi | Où |
|---|---|
| Binaire B 2.01 (hors du dépôt, paquet Nikon ouvert avec `unar`) | `~/Library/Caches/retro-ingenierie-boitiers/firmware/d200-201/B2000201.bin` |
| Analyse Ghidra (projet, pseudo-C de tout le firmware) | `d200/desassemblage/regenerer.sh <dossier hors du dépôt>` ; symboles dans [`symboles.tsv`](../desassemblage/symboles.tsv), appliqués par `D200Setup.java` |
| Pseudo-C des passages lus | [`d200/desassemblage/`](../desassemblage/regenerer.sh) : courbe perso (`ptp-courbe.c`, `lecteurs-courbe.c`, `expansion-courbe.c`, `courbe-2.c`, `appelant.c`), balance (`prewb.c`), mise à jour (`maj-lot1.c`, `maj-flasheur.c`, `maj-ecrivains.c`, `maj-liaisonA.c`) |
| Simulateur | [`d200/outils/d200_simulateur.py`](../outils/d200_simulateur.py) : `rendu`, `valider`, `--self-test` |
| Choix des tables (jeu de matrices, courbe, teinte, saturation), lu dans le code en octobre | [`d200-choix-des-tables.md`](d200-choix-des-tables.md) |
| Émulateur par appel de fonctions (fiche posée en RAM, registres de la puce relus) | [`d200/emulateur/README.md`](../emulateur/README.md) : `python3 d200/emulateur/d200emu.py verifier` |
| Rendus couleur au format du D200, planche titrée | [`d200/outils/d200_rendus.py`](../outils/d200_rendus.py) : `recette`, `planche`, `--self-test` ; figure |
| Patchs N&B films | [`d200/outils/d200_nb.py`](../outils/d200_nb.py) : `patch <film>`, `planche <nef> <sortie>`, `--self-test` ; JSON dans `d200/patchs/d200-nb-{trix,hp5,fp4}.json` |
| Séance de calibration par USB | [`d200/outils/d200_seance.py`](../outils/d200_seance.py) : `plan <dossier>`, `analyser <dossier>` ; prise de vue : [`d200/outils/d200_seance.swift`](../outils/d200_seance.swift) `<dossier> [--depuis N]` |
| Fabrication du fichier à flasher | `python3 d40/patch.py d200/patchs/d200-nb-trix.json --sortie <dossier>` (`"firmware": "D200B"`, sha256 de l'original contrôlé, CRC recalculé) |

## 3. Moteur d'image (couleur)

| Étage | Données | Statut |
|---|---|---|
| Chargement | `isp_chargerPuce` (`0x5D716`) recopie la fiche de prise de vue dans les registres `0x5001xxxx` (le D40 utilise `0x4001xxxx`), puis les trois courbes | vérifié |
| Matrice caméra | 3×3, ×512, signe et module sur 11 bits ; table de **294 jeux** à `0x384BF8` (24 demi-mots par jeu : caméra 9, YCbCr 9, 6 autres) ; jeux 126 à 209 vides ; numéro du jeu choisi dans `FUN_000d57e6` (variable `0x97BE0A14`) | vérifié |
| Courbe de tonalité | une table de 4 096 entrées par canal (entrée linéaire 12 bits, sortie 8 bits), copiée vers `0x50018400`, `0x5001A400`, `0x5001C400` ; **21 courbes** intégrées à `0x3884D8`, 256 seuils 16 bits chacune, développées par `FUN_0005df82` ; numéro = 7 × groupe + cran (`FUN_000d3ee6`) ; courbe perso : §5 de [`d200-ptp-usb.md`](d200-ptp-usb.md) | vérifié |
| Matrice YCbCr | 3×3, ×256 (Y, Cb, Cr), même jeu que la matrice caméra | vérifié |
| 16 secteurs de teinte | 4 blocs de 16 demi-mots copiés vers `0x5001E400`, `E420`, `E440`, `E460` depuis la fiche (décalages `0x39A` à `0x419`) ; tables à `0x38B6C0` (0x50 demi-mots par jeu) | vérifié (copie) ; **format et carte vérifiés par trois sondes** en octobre : matrice 2×2 `[b1 b2 ; b3 b4]/256` sur (Cb, Cr), 16 nœuds tous les 22,5°, interpolés (`d200-preglages.md` §7, `d200/outils/d200_etage.py`) |
| Saturation | table à `0x5001EC00` | vérifié (adresse) ; format : hypothèse |

**Ce que fait chaque réglage** (séance d’octobre 2026, `d200_seance.py analyser`, deux scènes) :

| Réglage | Courbe intégrée (bibliothèque, pédalier) | Jeu de matrices | (Cb, Cr) par rapport à Personnalisé de référence |
|---|---|---|---|
| Normal, Portrait | 2, 1 (Correction des tons Auto : le cran suit la scène) | 9, 11 | — |
| Moins net ; Personnalisé tons Moins contrasté | 0, 0 | 11, 12 | — |
| Personnalisé de référence (tons Normale, mode I, saturation Normale) | 3, 3 | 8, 9 | référence |
| Personnalisé tons Plus contrasté | 6, 6 | 21, 7 | inchangé |
| Mode couleur II (Adobe RGB) | 10, 10 | 66, 52 | échelle 0,69 et 0,81 (Adobe RGB codé) |
| Mode couleur III ; Saturé | 17, 17 | 93, 94 ; 19, 97 | rotation +6 à +7°, échelle 1,09 |
| Très saturé | 20, 20 | 15, 93 | — |
| Saturation Modérée, Accentuée | 3, 3 | 72, 7 ; 26, 12 | échelle 0,82 à 0,84 ; 1,16 à 1,21 |
| Teinte −9, −6, −3, +3, +6, +9 | 3 | sans rapport | rotation −5,3 / −2,7 / −0,5 / +3,7 / +5,3 / +6,4° (bibliothèque) ; −7,8 / −4,9 / −2,4 / +1,0 / +2,9 / +4,3° (pédalier), échelle 0,96 à 1,01 |

- **Courbes** : stables d'une scène à l'autre et conformes à « numéro = 7 × groupe + cran » : groupe = mode couleur (I : 0 à 6, II : 7 à 13, III : 14 à 20), cran 0 = Moins contrasté, 3 = Normale, 6 = Plus contrasté, 1 et 2 pour Auto. Vérifié.
- **Jeux de matrices** : **jeu = 42 × E + 7 × F + (6 − K)**, E = classe couleur (mode I, II, III, et variantes Adobe RGB), F = famille d'éclairage (selon la balance des blancs : chaud, moyen, froid, deux classes de fluo, flash), K = numéro de courbe modulo 7 ; E = 3 et 4 jamais produits (jeux 126 à 209 vides). Les préréglages Normal, Moins net, Saturé, Très saturé et Portrait ne sont que des Personnalisé réglés d'avance (`FUN_000ce4fa`) : **aucune table n'appartient à un seul préréglage**. Le jeu de l'ajustement change d'une scène à l'autre parce que les tons Auto choisissent leur cran selon la scène et que l'ajustement ne dispose pas de la saturation ni de la teinte. Détail : [`d200-choix-des-tables.md`](d200-choix-des-tables.md). Vérifié (code ; traduction de l'arbre rejouée sur 8 918 cas).
- **Teinte** : `FUN_000d846a` tourne les lignes Cb et Cr de la matrice YCbCr déjà choisie (table de 7 rotations à `0x388318` : −7,2 / −4,5 / −2,1 / 0 / +1,9 / +3,55 / +5,0°), seulement en Personnalisé ; ni jeu ni secteur touché. Les angles mesurés sur les JPEG (environ 0,6° par degré du menu, décalés selon la scène) s'y accordent. Vérifié (code et mesure).
- **Saturation** : une colonne parmi 48 de la table 1 024 × 48 à `0x3A62DD`, copiée vers `0x5001EC00` (`FUN_000dd1ca`) ; Normale, Modérée (plateau 0,84), Accentuée (jusqu'à ×1,30), Auto selon la scène. Vérifié.
- **Courbe perso d'usine** (`0x17329C`) : envoyée telle quelle en Personnalisée, elle **n'égale pas** la courbe Normale (3) : plus sombre dans les ombres et les tons moyens (sortie 89 contre 104 au quart de l'entrée, 139 contre 151 à la moitié). Vérifié (vue 20 : ΔE2000 1,80 avec la courbe envoyée, 4,57 avec la 3).

**Simulateur** (`d200_simulateur.py valider`) : pour chaque NEF, LibRaw donne le RGB caméra équilibré par la balance du boîtier ; la meilleure courbe et le meilleur jeu de matrices sont cherchés, puis comparés au JPEG du boîtier embarqué dans le NEF : **ΔE2000 médian 1,29 à 2,71** sur les six NEF de « Test D200 » (blocs uniformes). Non simulés : secteurs, saturation, netteté, bruit. Vérifié.

## 4. Noir et blanc

Choisi quand le mode d'Optimiser l'image vaut 6 (bits 1 à 4 de l'octet `0x4D` de la fiche).

| Élément | Où | Valeur d'origine | Statut |
|---|---|---|---|
| Matrice caméra N&B | instructions `LDI` dans `FUN_000d57e6`, `0xD7840` à `0xD7880` | (744, −223, −9 ; −41, 656, −103 ; −23, −7, 542) / 512 | vérifié |
| Ligne Y | `LDI:8` à `0xD7888`, `0xD7892`, `0xD789C` | (76, 151, 29) / 256 ; Cb = Cr = 0 | vérifié |
| Courbe | `0x3B22DD`, 4 096 octets, **la même sur R, V, B** ; seule référence : `FUN_000dcf50` (`0xDCF52`), appelée seulement par `isp_chargerPuce` | courbe N&B Nikon | vérifié |
| Variante | octet `0x4E` de la fiche, bits 6-7, traduit par la table `0x162978` = (0, 1, 2, 0) : 0 = N&B, 1 = sépia (tables `0x39DB30`, `0x39EB30`, `0x39FB30`), 2 = cyanotype (`0x3A2CCB`, `0x3A3CCB`, `0x3A4CCB`) | toujours 0 depuis les menus | vérifié (code) |

Le virage sépia ou cyanotype n'est atteignable que dans le chemin de retraitement d'un NEF (`FUN_00061ea0`, `0x622D8`) ; les menus du boîtier ne le proposent pas (manuel p. 45). Un patch qui l'ouvrirait en prise de vue toucherait aussi la matrice YCbCr (Cb, Cr) : pas étudié. Hypothèse.

## 5. Patch « film N&B » (Tri-X, HP5, FP4)

**Principe** (le même que les rendus film du D40) : le gris = courbe(film) appliquée à une somme pondérée du RGB caméra qui reproduit la sensibilité spectrale du film.

1. **Pondération** : `films_nb.poids` ajuste (R, V, B) du RGB caméra équilibré pour reproduire la réponse du film sur des réflectances naturelles, sous D65, avec les sensibilités spectrales du D200 (camspec, Jiang et al. 2013). Poids ≥ 0, somme 1.
2. **Matrice** : lignes 0 et 1 de la matrice caméra N&B = k × pondération × 512. Trois des six coefficients sont chargés par `LDI:8` suivi de `EXTSB` (extension de signe, plage −128 à 127) : l'`EXTSB` est remplacé par `NOP` pour obtenir 0 à 255. k ramène le plus grand coefficient à 255.
3. **Ligne Y** = (128, 128, 0) / 256 : Y = R′ = V′, le canal bleu sort du calcul.
4. **Courbe** : `films_nb.courbe` (film, puis tirage sur papier grade 2), gris moyen calé sur celui du N&B Nikon d'origine, entrée divisée par k.

| Film | Pondération R, V, B | Écart médian au film | k | Coefficients écrits |
|---|---|---|---|---|
| Tri-X | 0,274 ; 0,148 ; 0,578 | 4,3 % | 0,861 | 121, 65, 255 |
| HP5 | 0,158 ; 0,048 ; 0,794 | 5,3 % | 0,627 | 51, 15, 255 |
| FP4 | 0,199 ; 0,095 ; 0,706 | 3,8 % | 0,705 | 72, 34, 255 |

**Patch** : 10 remplacements à longueur égale (6 instructions de la matrice, 3 de la ligne Y, la courbe), environ 4 000 octets changés avec le CRC. Tous dans les plages réécrites par la mise à jour et hors de la chaîne de mise à jour (§6). `d200_nb.py --self-test` relit les instructions d'origine, applique le patch Tri-X et contrôle les lignes obtenues. Vérifié.

**Rendus simulés** sur les six NEF de « Test D200 » (de gauche à droite : N&B Nikon, Tri-X, HP5, FP4) :

!N&B Nikon, Tri-X, HP5, FP4

Le feuillage s'assombrit (films plus sensibles au bleu qu'au vert), les ombres se ferment en HP5, le FP4 a l'épaule la plus douce.

**Limites** :
- Le N&B simulé est **validé** sur les JPEG N&B du boîtier (séance d’octobre, deux scènes, début et fin de lot) : ΔE2000 médian 0,58 à 0,64, 90e centile 3,0 à 5,5. Outils : [`d200/outils/d200_seance.py`](../outils/d200_seance.py) (plan) et [`d200/outils/d200_seance.swift`](../outils/d200_seance.swift) (prise de vue), 25 vues par scène sur trépied, bibliothèque et pédalier comme le D750 : les 7 choix d'Optimiser l'image, les crans de Personnalisé (tons, mode couleur, saturation, teinte de −9 à +9 pour l'étage à 16 secteurs), 5 courbes perso (usine, linéaire, Classic Chrome, Hasselblad, Positive), le N&B au début et à la fin ; réglages et courbe de départ remis et relus à la fin. Séance faite en octobre (`d200/images/2026-10-seance-*`) ; analyse : `d200_seance.py analyser <dossier>` (N&B, couleur, courbes perso, teinte), résultats au §3.
- `NOP` à la place d'`EXTSB` : chaque coefficient suit le même motif, `LDI` vers R0, `EXTSB R0` pour les négatifs, puis `ST R0` dans un mot de la mémoire vive (`0x97BE09F0` + 4 n pour la matrice, `0x97BE09CC` et suivants pour la ligne Y) ; l'`EXTSB` ne sert qu'à la valeur rangée juste après. Vérifié (octets `0xD783A`–`0xD78AE`). Conversion vers les registres (`FUN_000d93a6`) : signe et grandeur, bit 0x400 pour la matrice caméra, 0x200 pour Y, Cb, Cr, valeur positive rangée telle quelle. **Rejoué dans l'émulateur en octobre** : le patch Tri-X arrive dans les registres (`0x50010022` = 0x79, 0x41, 0xFF deux fois puis la 3e ligne d'origine ; `0x50010034` = 0x80, 0x80, 0) et chacun des six coefficients balayé de 0 à 255 donne v dans le registre ; avec l'`EXTSB` d'origine, 255 aurait donné −1/512. Aucun plafond sur les valeurs positives : un coefficient au-delà de 1 023 tomberait sur le bit de signe sans alerte. Vérifié (émulateur, `d200/emulateur/README.md`).
- Le patch remplace le N&B Nikon : pour garder les deux, il faudrait détourner une autre entrée (sépia, ou une courbe intégrée inutilisée). Pas étudié.

## 6. Mise à jour et flasheur

Lu en octobre 2026 dans le firmware installé (c'est lui qui contrôle et flashe le nouveau fichier). Pseudo-C : `d200/desassemblage/maj-*.c`. Vérifié sauf mention.

**Chaîne** :
- Recherche à la racine de la carte (`0x9A680`, parcours `0x9B0B0`, casse ignorée) : `B200????.BIN`, sinon `A200????.BIN`, sinon `_WT3????.BIN` (émetteur WT-3). Le premier trouvé gagne. Lancée depuis l'écran Version du menu Configuration.
- Contrôles du B (`0x9ACAC`) : taille **exactement 0x3C0000** ; mot à `0xEFBF4` → 32 octets comparés à la signature du firmware en cours (« Q220FirmwareSignature », zéro compris) ; pointeur `0xEFBF0` → 9 octets de version, **pour l'affichage seulement** : une version égale ou plus ancienne passe.
- Contrôles du A (`0x9AD1E`) : taille 0x40000 ou 0x40002, version à l'offset 0x200, pas de signature.
- Exécution (`0x9A9FC`) : fichier chargé en RAM à `0x90000000`, **CRC16 XMODEM sur tout le fichier = 0** (`0x54552`, table `0x15D284`) ; commande `0x27` au processeur A, qui doit répondre `0x28` ; sauvegarde des réglages ; saut au flasheur en RAM.

**Flasheur** (copié au démarrage de `0x15C72C` vers la RAM `0x9798CFB0`, 0x338 octets) : flash de type AMD, secteurs de 64 Ko (8 Ko dans `0x3F0000`–`0x3FFFFF`), effacement vérifié puis écriture relue, séquence fixe recommencée jusqu'à 3 fois :
1. efface `0x0E0000`–`0x0EFFFF` (vecteurs, pointeurs de signature et de version), puis `0x050000`–`0x0DFFFF`, `0x120000`–`0x1CFFFF`, `0x200000`–`0x40FFFF` ;
2. écrit `0x120000`–`0x1CFFFF`, puis `0x200000`–`0x40FFFF`, puis **en dernier** `0x050000`–`0x0EFFFF`.

**Jamais écrits par la mise à jour** : `0x0F0000`–`0x11FFFF` (chargeur de démarrage, hypothèse forte), `0x1D0000`–`0x1FFFFF` (journal des réglages en deux copies à `0x1D0000` et `0x1E0000`, configuration d'usine « Q220 » à `0x1F0000`), au-delà de `0x410000` (second journal, réglages d'usine `SYSTEMFIXADJUST` à `0x430000`). Les octets du fichier dans ces plages comptent dans le CRC mais ne sont pas flashés. Le flasheur sert aussi à chaque sauvegarde de réglages.

**Place libre réellement flashée** : `0x0E3600`–`0x0EFBEF` (≈ 50 Ko), `0x1765EA`–`0x1CFFFF` (≈ 358 Ko), `0x3F72A8`–`0x3F7FFF` (3 Ko) et `0x400000`–`0x40FFFD` (≈ 64 Ko, secteur qui ne porte que le CRC). **À éviter** : `0x3F8000`–`0x3FFFFF`, quatre secteurs de 8 Ko où Nikon n'écrit aucun octet. Ils sont effacés à chaque mise à jour mais jamais programmés, et rien ne prouve qu'ils se programment : la broche WP# de la puce peut verrouiller les deux du haut, et le flasheur échouerait alors après avoir effacé le code principal (relecture d’octobre, [`d200-v1-relecture.md`](d200-v1-relecture.md), constat 1). Octets de Nikon par secteur de 8 Ko, de `0x3F0000` à `0x3FE000` : 8 150, 8 144, 8 140, 4 746, puis 0, 0, 0, 0.

**Règles pour un B modifié** (contrôlées par `d40/patch.py` : taille, original, CRC, et depuis octobre les points 3 à 5 et les plages réécrites, `controler_d200`) :
1. Nom `B2000201.BIN` à la racine de la carte, seul fichier `B200….BIN`.
2. Taille 3 932 160 octets ; CRC16 XMODEM = 0, CRC en gros-boutiste à la fin.
3. Ne toucher ni `0xEFBF0`–`0xEFFFF` (pointeurs, vecteurs), ni la signature, ni les caractères 4, 6 et 7 de la version (envoyés au processeur A au démarrage, commande `0x10` ; usage côté A non lu).
4. Ne toucher ni la chaîne de mise à jour (`0x9A680`–`0x9B14A`, `0x54552`, `0x15D284`), ni le flasheur (`0x15C72C`–`0x15CA63`), ni ses tables (`0x1538CC`, `0x1538EC`, section de données `0x15387C`), ni la table des commandes vers A (`0x15E008`), ni les pointeurs de journal (`0x16C760`, `0x16CB18`).
5. N'écrire que dans un secteur qui porte déjà au moins un octet de Nikon (secteurs de 64 Ko, de 8 Ko en `0x3F0000`–`0x3FFFFF`) : ceux-là sont programmés à chaque mise à jour officielle.

**Le risque** : un B qui casse cette chaîne empêche toute mise à jour suivante, y compris le retour au firmware Nikon ; ne resterait que le chargeur, non lu. Le patch N&B ne touche aucune de ces zones (instructions `0xD7840`–`0xD78A0`, table `0x3B22DD`–`0x3B32DC`).

## 7. Avant un flash (sur le go de Thomas seulement)

1. ~~Valider le N&B du simulateur sur un vrai JPEG N&B du D200~~ : fait en octobre (§5).
2. ~~Rejouer `FUN_000d57e6` et `isp_chargerPuce` patchées dans un émulateur FR~~ : fait en octobre pour le N&B (`d200emu.py verifier`, code 0).
3. Renommer les entrées du menu : **patch prêt** `d200/patchs/d200-noms.json` (19 patchs, 400 octets, fabriqué par `d200/outils/d200_textes.py renommer d200/patchs/d200-noms-entree.json --repointer --zone 0x176600`) : en français, Moins nette → Chrome, Saturée → Positive (texte plus long, placé en `0x176600`, pointeur de la table changé), Plus saturée → FP4, Portrait → HP5, Noir et blanc → Tri-X, et leurs lignes d'aide ; Normale et Personnalisée inchangées (choix de Thomas en octobre). Autres langues inchangées. Aspect à l'écran : non vu (§9).
4. Code des préréglages vérifié dans l'émulateur (`d200emu.py verifier`, 11 essais) : fait en octobre.
5. Flasher `d200/build/v1/B2000201.BIN` seul (le A ne change pas), sur le go de Thomas : procédure et retour arrière au §10.

## 8. Ce qui reste incertain

- Le chargeur `0x0F0000`–`0x11FFFF` : contrôle-t-il la signature avant de démarrer ? Non lu.
- Ce que le processeur A fait des caractères de version reçus au démarrage.
- Sens exact des quatre blocs à 16 secteurs et format de la table de saturation.
- Sens des classes d'éclairage `e40`, du drapeau de l'octet `0xA1` (flash ?), de la mesure de scène `e48` ([`d200-choix-des-tables.md`](d200-choix-des-tables.md) §7).
- La puce lit-elle le bit 0x400 ou 0x200 comme un signe (cohérent avec le simulateur, non lu dans le matériel).

## 9. Textes du menu

Lu en octobre 2026 dans le B 2.01 (octets et pseudo-C Ghidra), rien n'est flashé. Outil : [`d200/outils/d200_textes.py`](../outils/d200_textes.py) (`langues`, `chercher`, `lister`, `id`, `optimiser`, `renommer`, `--self-test`). *Vérifié* = lu dans le code ou les octets, à l'adresse donnée ; *hypothèse* = déduit, pas lu. Adresses du processeur (offset dans le fichier = adresse moins `0x50000`).

### 9.1 En bref

- Les textes de 13 langues sont dans 13 tables de 2395 pointeurs. L'identifiant de texte est l'indice dans la table, le même dans toutes les langues. Il n'y a **pas de fonction unique de résolution** : le code lit partout `*(u32 *)(0x9799112C + 4 × identifiant)`. Vérifié.
- Les chaînes d'une langue se suivent **sans trou**, dans l'ordre inverse des identifiants : la chaîne i occupe exactement de son pointeur au pointeur de la chaîne i-1. La place disponible est donc la longueur de la chaîne actuelle, `0xFFFF` compris. Vérifié sur les 13 × 2395 chaînes (`--self-test`).
- Un nom plus court se termine plus tôt. Un nom plus long **est possible** : on écrit le texte dans une zone libre et on change le pointeur de la table (les 364 chaînes concernées n'ont aucune autre référence dans le binaire). Vérifié (octets) ; effet à l'écran non testé.
- Les 7 noms d'Optimiser l'image sont les identifiants 214, 251, 252, 253, 217, 221, 254 ; leur aide occupe les identifiants 506 à 522. Autres copies du nom : pictogrammes (bitmaps) et trois familles de chaînes ASCII 8 bits (§9.5).
- Place en français (caractères, terminateur déduit) : Normale 7, Moins nette 11, Saturée 7, Plus saturée 12, Portrait 8, Personnalisée 13, Noir et blanc 13. Largeur : voir §9.6.

### 9.2 Comment le firmware trouve une chaîne

| Élément | Où et comment | Statut |
|---|---|---|
| Tables de langue | 13 tables de 2395 pointeurs 32 bits gros-boutistes (tableau ci-dessous) | vérifié |
| Identifiant | indice 0 à 2394 ; même texte dans les 13 langues (254 = « Noir et blanc » en français, « Black-and-white » en anglais, etc.) | vérifié |
| Rangement des chaînes | juste après la table, ordre inverse des identifiants, jointives : la chaîne i va du pointeur i au pointeur i-1 ; la plus haute (id 0) finit au début de la table suivante, à 2 octets près | vérifié |
| Format d'une chaîne | mots de 16 bits gros-boutistes, fin `0xFFFF` (compté dans la place) | vérifié |
| Choix de la langue | `FUN_001389E4` (`0x1389E4`) lit les bits 3 à 6 de l'octet `0x9799106A` (0 à 12) et range l'adresse de la table dans le mot RAM `0x9799112C` ; valeur inconnue = anglais | vérifié |
| Résolution d'un identifiant | pas de fonction : `*(u32 *)(0x9799112C + 4 × id)` est écrit en ligne à chaque appel (plus de 100 endroits), puis le pointeur va au traceur `FUN_00085224` (`0x85224`, trace jusqu'à `0xFFFF`) ou au calcul de largeur `FUN_00085D68` (`0x85D68`) | vérifié |
| Ligne de menu | `FUN_00143DA4` (`0x143DA4`) : icône = mot +0 de l'entrée, libellé = identifiant au mot +2 ; un identifiant `0xE001` ou plus appelle une fonction de la table `0x17165C` (texte calculé) | vérifié |
| Titre et sous-titre d'un écran | `FUN_0014321C` (`0x14321C`) : identifiants aux mots 12 et 13 de l'en-tête de menu | vérifié |
| Copie en RAM des chaînes | aucune : le pointeur de la table ROM est lu à chaque affichage | vérifié (traceur et largeur lisent le pointeur reçu) |

| Code | Sélecteur | Langue | Table de pointeurs | Chaînes | Statut de la langue |
|---|---|---|---|---|---|
| de | 0 | allemand | `0x21F3D0`-`0x22193B` | `0x22193C`-`0x233F05` | vérifié (texte) |
| en | 1 | anglais | `0x233F08`-`0x236473` | `0x236474`-`0x2465FF` | vérifié |
| es | 2 | espagnol | `0x29A504`-`0x29CA6F` | `0x29CA70`-`0x2AE357` | vérifié |
| **fr** | **3** | **français** | **`0x246600`-`0x248B6B`** | **`0x248B6C`-`0x25ABD7`** | vérifié (texte) ; sélecteur 3 pour le boîtier de Thomas : déduit |
| it | 4 | italien | `0x26661C`-`0x268B87` | `0x268B88`-`0x27A503` | vérifié |
| nl | 5 | néerlandais | `0x286548`-`0x288AB3` | `0x288AB4`-`0x29A503` | vérifié |
| pt | 6 | portugais | `0x35D894`-`0x35FDFF` | `0x35FE00`-`0x3713F9` | vérifié |
| ru | 7 | russe | `0x341708`-`0x343C73` | `0x343C74`-`0x35400B` | vérifié (cyrillique lisible) |
| sv | 8 | suédois | `0x20D188`-`0x20F6F3` | `0x20F6F4`-`0x21F3CF` | vérifié |
| zh1 | 9 | chinois | `0x35400C`-`0x356577` | `0x356578`-`0x35D893` | hypothèse (langue déduite des « oui/non » à un caractère) |
| zh2 | 10 | chinois | `0x3713FC`-`0x373967` | `0x373968`-`0x37ACD5` | hypothèse (simplifié ou traditionnel : non distingués) |
| ja | 11 | japonais | `0x27A504`-`0x27CA6F` | `0x27CA70`-`0x286545` | hypothèse (« oui/non » à 2 et 3 caractères) |
| ko | 12 | coréen | `0x25ABD8`-`0x25D143` | `0x25D144`-`0x26661B` | hypothèse (« oui/non » à 1 et 3 caractères) |

La cellule du pointeur de l'identifiant i dans la langue L est `base(L) + 4 × i` (français : `0x246600 + 4 × i`).

### 9.3 Codage des caractères

| Caractère | Code 16 bits | Statut |
|---|---|---|
| Espace, ponctuation, lettres ASCII | `0x200` + code ASCII (`0x220` espace à `0x27E`) ; police proportionnelle des menus | vérifié |
| Chiffres 0 à 9 | `0x230` à `0x239` (« 3872x2592/10,0M », « 2500 K ») | vérifié |
| Minuscules accentuées | `0x280` à, `0x281` á, `0x282` â, `0x283` ã, `0x284` ä, `0x285` ç, `0x286` è, `0x287` é, `0x288` ê, `0x289` ë, `0x28A` ò, `0x28B` ó, `0x28C` ô, `0x28D` õ, `0x28E` ö, `0x28F` ù, `0x290` ú, `0x291` û, `0x292` ü, `0x293` í, `0x294` å, `0x295` î, `0x296` ì | vérifié (mots lus dans les 8 langues latines) |
| Autres | `0x297` ï, `0x298` ≈ | hypothèse (forme du glyphe seule) |
| Majuscules accentuées | `0x201` À, `0x202` Á, `0x203` Â, `0x204` Ã, `0x205` Ä, `0x206` Ç, `0x207` È, `0x208` É, `0x209` Ê, `0x20A` Ë, `0x20C` Ó, `0x20E` Õ, `0x20F` Ö, `0x211` Ú, `0x213` Ü, `0x219` Í, `0x21B` Å, `0x21F` Ñ | vérifié (mots lus) ; `0x20B` Ò, `0x20D` Ô, `0x210` Ù, `0x212` Û : hypothèse (forme) |
| Divers | `0x214` ß, `0x215` Ø, `0x216` ñ, `0x217` ¡, `0x218` ¿, `0x21A` º | vérifié (« Weißabgleich », « Ø10mm », « Español », « N° version ») |
| Cyrillique | majuscules `0x2A0` + rang (А à Я, Ё en 6e), minuscules `0x2D0` + rang | vérifié (« Нормальный », « Мягче ») |
| Police fixe | code inférieur à `0x100` : ASCII brut, avance 11 px (le « : » des lignes d'aide, les titres 0 à 3) ; les accents de cette police ne sont pas relevés | vérifié (traceur) ; accents : non lu |
| Pictogrammes | `0xF001` à `0xFEFF` : table `0x2AE598` (lignes, colonnes, tuile) ; `0xFF0D` à `0xFF41` : autre traceur (`FUN_00087508`) | vérifié (appels) ; sens des `0xFFxx` : hypothèse |
| Chinois, japonais, coréen | codes `0x0300` à `0x0F7F` : tuiles de polices à part (avance 21 px) | vérifié (codes), caractères non décodés |

Police des menus : glyphe de 40 × 40 points du tampon (20 unités d'écran, écran de 320 × 240 unités) à `0x3219F8 + 200 × (code & 0xFF)`, 5 octets par ligne, bit de poids fort à gauche ; avance de chaque glyphe dans la table de 256 mots `0x2AE398` (par exemple espace 5, `i` 7, `e` 11, `m` 17, `W` 19). Vérifié (lecture de `FUN_00085224`, `FUN_00085D68` et rendu des glyphes).

### 9.4 Optimiser l'image : les 7 entrées

**Structure** (vérifié) : le menu de choix est copié en RAM en `0x9798A428` ; ses 7 entrées de 20 octets sont en ROM à `0x159BE0 + 0x14 × k` (RAM `0x9798A464`, décalage ROM vers RAM `0x97830884`). Champs d'une entrée : +0 icône, +2 libellé, +4 = 1, +8 texte de l'astuce à droite de la ligne en surbrillance (9 = « OK », 8 = flèche seule pour Personnalisée, `0xD` = vide), +A attributs (3), +C premier identifiant de l'aide (`0x1FA`), +E nombre de lignes d'aide (21 ; 0 pour le noir et blanc), +0x10 action (`0x13CBBC` pour les 7). L'action range le rang de l'entrée (0 Normal, 1 Softer, 2 Vivid, 3 More vivid, 4 Portrait, 5 Custom, 6 N&B) dans les bits 1 à 4 de l'octet `0x97991159 + 0x5A × banque de menu P/vue` ; `FUN_0013CB90` le relit pour placer la surbrillance.

**Libellés en français** (la table est celle du boîtier de Thomas) :

| Entrée (anglais) | Entrée de menu | Id | Cellule du pointeur | Chaîne | Octets | Caractères max | Largeur | Texte | Statut |
|---|---|---|---|---|---|---|---|---|---|
| Normal | `0x159BE0` | 214 (`0xD6`) | `0x246958` | `0x259598` | 16 | 7 | 77 px | Normale | vérifié |
| Softer | `0x159BF4` | 251 (`0xFB`) | `0x2469EC` | `0x259292` | 24 | 11 | 112 px | Moins nette | vérifié |
| Vivid | `0x159C08` | 252 (`0xFC`) | `0x2469F0` | `0x259282` | 16 | 7 | 70 px | Saturée | vérifié |
| More vivid | `0x159C1C` | 253 (`0xFD`) | `0x2469F4` | `0x259268` | 26 | 12 | 111 px | Plus saturée | vérifié |
| Portrait | `0x159C30` | 217 (`0xD9`) | `0x246964` | `0x25955A` | 18 | 8 | 70 px | Portrait | vérifié |
| Custom | `0x159C44` | 221 (`0xDD`) | `0x246974` | `0x2594F2` | 28 | 13 | 127 px | Personnalisée | vérifié |
| Black-and-white | `0x159C58` | 254 (`0xFE`) | `0x2469F8` | `0x25924C` | 28 | 13 | 117 px | Noir et blanc | vérifié |

**Libellés dans les 13 langues** : adresse de la chaîne et, entre parenthèses, le nombre de caractères que la place permet (terminateur déjà retiré). Commande : `d200_textes.py optimiser --langue toutes`. Vérifié.

| Langue | Normal | Softer | Vivid | More vivid | Portrait | Custom | Black-and-white |
|---|---|---|---|---|---|---|---|
| de | `0x232912` (6) Normal | `0x23261E` (7) Weicher | `0x23260C` (8) Brillant | `0x2325FA` (8) Intensiv | `0x2328DC` (7) Porträt | `0x232888` (17) Benutzerdefiniert | `0x2325E2` (11) Schwarzweiß |
| en | `0x245256` (6) | `0x244FE6` (6) | `0x244FDA` (5) | `0x244FC4` (10) | `0x245226` (8) | `0x2451EC` (6) | `0x244FA4` (15) |
| es | `0x2ACCF6` (6) | `0x2ACA48` (5) Suave | `0x2ACA3A` (6) Vívida | `0x2ACA24` (10) Más vívida | `0x2ACCCA` (7) Retrato | `0x2ACC7C` (13) Personalizado | `0x2ACA06` (14) Blanco y negro |
| **fr** | `0x259598` (7) | `0x259292` (11) | `0x259282` (7) | `0x259268` (12) | `0x25955A` (8) | `0x2594F2` (13) | `0x25924C` (13) |
| it | `0x278F5A` (7) Normale | `0x278CC0` (4) Soft | `0x278CB2` (6) Satura | `0x278C9C` (10) Più satura | `0x278F20` (8) Ritratto | `0x278ED2` (14) Personalizzata | `0x278C80` (13) Bianco & Nero |
| nl | `0x298F80` (7) Normaal | `0x298CEE` (7) Zachter | `0x298CDC` (8) Levendig | `0x298CBE` (14) Extra levendig | `0x298F4C` (7) Portret | `0x298F0C` (5) Eigen | `0x298CAA` (9) Zwart-wit |
| pt | `0x36FD80` (6) Normal | `0x36FABA` (5) Suave | `0x36FAAA` (7) Vividez | `0x36FA90` (12) Mais vividez | `0x36FD4C` (7) Retrato | `0x36FCFE` (13) Personalizada | `0x36FA72` (14) Preto e Branco |
| ru | `0x352AF8` (10) | `0x352822` (5) | `0x352816` (5) | `0x352804` (8) | `0x352ABC` (7) | `0x352A68` (13) | `0x3527EC` (11) |
| sv | `0x21E0FE` (6) Normal | `0x21DE86` (7) Mjukare | `0x21DE74` (8) Intensiv | `0x21DE54` (15) Extra förstärkt | `0x21E0C8` (8) Porträtt | `0x21E090` (4) Egen | `0x21DE40` (9) Svartvitt |
| zh1 | `0x35CF60` (2) | `0x35CE5C` (2) | `0x35CE56` (2) | `0x35CE4E` (3) | `0x35CF48` (4) | `0x35CF22` (6) | `0x35CE48` (2) |
| zh2 | `0x37A3AA` (2) | `0x37A2AC` (2) | `0x37A2A6` (2) | `0x37A29C` (4) | `0x37A396` (2) | `0x37A374` (4) | `0x37A296` (2) |
| ja | `0x2859A2` (2) | `0x285834` (4) | `0x28582A` (4) | `0x28581C` (6) | `0x285980` (6) | `0x28594A` (6) | `0x285816` (2) |
| ko | `0x265B26` (2) | `0x2659E2` (4) | `0x2659D8` (4) | `0x2659C8` (7) | `0x265B0C` (2) | `0x265AE0` (6) | `0x2659C2` (2) |

**Lignes d'aide** (touche d'aide du menu ; mêmes identifiants dans toutes les langues, adresses par `optimiser --langue toutes`). Le nom est au début de la première ligne de chaque paragraphe, suivi du « : » de la police fixe. Le noir et blanc n'a pas d'aide (nombre de lignes 0). Les 21 lignes `0x1FA` à `0x20E` forment une seule page ; les identifiants 523 à 526 sont vides. Les adresses ci-dessous sont celles du français. Vérifié (texte et adresses) ; le rôle « une page de 21 lignes affichée pour tout le menu » vient des champs +C et +E des entrées, la fonction qui dessine l'aide n'est pas lue : hypothèse.

| Id | Cellule | Chaîne | Octets | Car. max | Largeur | Texte français | Entrée |
|---|---|---|---|---|---|---|---|
| 506 | `0x246DE8` | `0x257E3A` | 46 | 22 | 223 px | Normale`:` convient pour | Normal |
| 507 | `0x246DEC` | `0x257E0C` | 46 | 22 | 192 px | des sujets très variés | Normal |
| 508 | `0x246DF0` | `0x257DDA` | 50 | 24 | 228 px | Moins nette`:` adoucit les | Softer |
| 509 | `0x246DF4` | `0x257DA8` | 50 | 24 | 219 px | contours et le contraste | Softer |
| 510 | `0x246DF8` | `0x257D84` | 36 | 17 | 179 px | Saturée`:` augmente | Vivid |
| 511 | `0x246DFC` | `0x257D5C` | 40 | 19 | 158 px | le contraste et la | Vivid |
| 512 | `0x246E00` | `0x257D32` | 42 | 20 | 185 px | saturation pour des | Vivid |
| 513 | `0x246E04` | `0x257D02` | 48 | 23 | 209 px | images nettes et vives. | Vivid |
| 514 | `0x246E08` | `0x257CD4` | 46 | 22 | 220 px | Plus saturée`:` augmente | More vivid |
| 515 | `0x246E0C` | `0x257CA4` | 48 | 23 | 210 px | contraste et saturation | More vivid |
| 516 | `0x246E10` | `0x257C76` | 46 | 22 | 218 px | pour des images encore | More vivid |
| 517 | `0x246E14` | `0x257C44` | 50 | 24 | 208 px | plus nettes, plus vives. | More vivid |
| 518 | `0x246E18` | `0x257C12` | 50 | 24 | 225 px | Portrait`:` contraste doux | Portrait |
| 519 | `0x246E1C` | `0x257BE0` | 50 | 24 | 215 px | pour portraits naturels, | Portrait |
| 520 | `0x246E20` | `0x257BB0` | 48 | 23 | 206 px | effet trois dimensions. | Portrait |
| 521 | `0x246E24` | `0x257B82` | 46 | 22 | 213 px | Personnalisée`:` réglage | Custom |
| 522 | `0x246E28` | `0x257B50` | 50 | 24 | 224 px | personnalisé des teintes | Custom |

Le « : » est le caractère `0x3A` de la police fixe (notation `` `: `` dans l'outil), pas le `0x23A` de la police proportionnelle.

**Autres copies du même mot ou de la même chaîne** (ce qu'il ne faut pas confondre, ni oublier) :

| Id | Rôle | Français | Anglais | Statut |
|---|---|---|---|---|
| 221 | libellé de l'entrée Personnalisée (`0x159C44`) **et** sous-titre de l'écran Personnalisée (en-tête de menu `0x156850`, mots `00D5 00DD` : titre « Optimisation image », sous-titre « Personnalisée ») : une seule chaîne pour les deux | `0x2594F2` | `0x2451EC` | vérifié |
| 236 | libellé « Personnalisée » de la Correction des tons (entrée `0x156760`) : autre option, autre identifiant | `0x259394` | `0x2450DC` | vérifié |
| 540 | ligne d'aide de la Correction des tons (« L'option "Personnalisée"... ») | `0x257988` | `0x2438D2` | vérifié (texte), rôle : hypothèse |
| 248 | « Noir et blanc » du menu Monochrome (`0x156544` : Noir et blanc, Sépia, Cyanotype) ; aucun pointeur du binaire ne vise ce menu (structure RAM `0x97986D8C`) : il n'est pas atteignable | `0x2592B8` | `0x245014` | vérifié (entrée) ; inatteignable : hypothèse forte |
| 213 | titre « Optimisation image » (écran de choix et en-tête des sous-menus) : pas un des 7 | `0x2595A8` | `0x245264` | vérifié |
| 225, 233, 243 | « Normale » de la netteté, des tons et de la saturation | | | vérifié : à ne pas renommer |
| 215, 216, 218, 219, 220 | Plus saturée, High Key, Couleurs chaudes, Artistique, Naturelle : libellés d'une autre génération de menus ; aucune entrée de menu ne les référence (balayage des entrées) | | | vérifié |

### 9.5 Abréviations, pictogrammes et chaînes ASCII

| Où le nom ou son abréviation s'affiche | Quoi | Statut |
|---|---|---|
| Écrans de contrôle (haut, arrière) | LCD à segments : aucun texte d'Optimiser l'image. Le viseur n'a que l'indicateur N&B (manuel p. 6) | vérifié (manuel) |
| Menu Prise de vue (liste de premier niveau) | la ligne « Optimisation image » **prend l'icône du choix courant** (entrée 4 du tableau RAM `0x9798A7E4` rempli par `FUN_0013ADE0` d'après l'icône de l'entrée choisie) ; aucun texte | vérifié |
| Liste d'Optimiser l'image | colonne d'icônes à gauche des libellés (x = 44) | vérifié |
| Page 2 des données de visualisation | ligne « DEVELOPMENT : » = chaîne ASCII de la **famille B** ci-dessous, **en anglais quelle que soit la langue** | vérifié (code) |
| Fichiers JPEG et NEF | étiquette Nikon « ImageOptimization » (étiquette `0x00A9`), **familles A et C** ci-dessous | écriture et lecture vérifiées (tables d'étiquettes `0x16E374` et `0x16B694`) ; nom de l'étiquette : hypothèse |

**Pictogrammes** (bitmaps, pas du texte ; communs à toutes les langues). Chacun est formé de 2 tuiles de 40 × 40 points (200 octets) : l'appareil à gauche, les lettres à droite. Vérifié (rendu des tuiles) ; lettres lues sur le rendu.

| Entrée | Code | Entrée de la table `0x2AE598` | Police | Tuile des lettres | Lettres |
|---|---|---|---|---|---|
| Normal | `0xF040` | `0x2AE694` | 5 | `0x3043A8` | N |
| Softer | `0xF15F` | `0x2AEB10` | 9 | `0x2ED7E8` | SO |
| Vivid | `0xF041` | `0x2AE698` | 5 | `0x304538` | VI |
| More vivid | `0xF160` | `0x2AEB14` | 9 | `0x2ED978` | VI+ (hypothèse sur le plus) |
| Portrait | `0xF043` | `0x2AE6A0` | 5 | `0x304858` | PO |
| Custom | `0xF047` | `0x2AE6B0` | 5 | `0x304E98` | pictogramme, pas de lettres |
| Black-and-white | `0xF048` | `0x2AE6B4` | 5 | `0x305028` | BW |

**Chaînes ASCII 8 bits** (anglais seulement, indépendantes de la langue) :

| Famille | Adresses | Créneau | Rôle | Statut |
|---|---|---|---|---|
| **B**, affichage | table de 7 pointeurs `0x16BC90` (indice = rang 0 à 6) : NORMAL `0x16BD34`, SOFT `0x16BD2C`, VIVID `0x16BD24`, MORE VIVID `0x16BD18`, PORTRAIT `0x16BD0C`, CUSTOM `0x16BD04`, BLACK AND WHITE `0x16BCF4` | 8, 8, 8, 12, 12, 8, 16 octets (NUL compris) ; copiée dans un tampon de 16 octets, 15 colonnes visibles | `FUN_0006F0F2` (`0x6F0F2`) copie la chaîne dans le bloc RAM `0x9798E348 + 0x1B4` ; `FUN_00121E90` (`0x121E90`) l'affiche à droite de « DEVELOPMENT : ». Le bloc est refait à l'affichage de chaque image d'après le rang lu dans le fichier : toutes les images prennent le nouveau nom, anciennes comprises | vérifié (code) ; « refait pour toutes les images » : hypothèse |
| **A**, lecture des fichiers | VIVID `0x16AF84`, MORE VIVID `0x16AF74`, PORTRAIT `0x16AF64`, SOFT `0x16AF54`, CUSTOM `0x16AF44`, BLACK AND WHITE `0x16AF34` (pas de 16 octets ; NORMAL = cas par défaut) | 16 octets | `FUN_0006651E` (`0x6651E`, étiquette `0x00A9` dans la table de lecture `0x16B630`) compare la chaîne lue dans le fichier à ces constantes et en tire le rang | vérifié (code) ; **à ne pas modifier** |
| **C**, écriture dans les fichiers | NORMAL `0x16D18C` (défaut) et `0x16D1FC`, BLACK AND WHITE `0x16D19C`, CUSTOM `0x16D1AC`, PORTRAIT `0x16D1BC`, MORE VIVID `0x16D1CC`, VIVID `0x16D1DC`, SOFT `0x16D1EC` | 16 octets (compte `0x10` de l'étiquette) | `FUN_0007EF28` (`0x7EF28`, table d'écriture `0x16E374`) écrit la chaîne du rang dans le fichier | vérifié (code) ; **à ne pas modifier** : le boîtier relit ses fichiers avec la famille A |

Conséquence : pour que la page de données affiche « TRI-X », on ne change que la famille B ; les familles A et C sont un format de fichier (Capture NX, Lightroom et exiftool lisent la chaîne écrite).

### 9.6 Règles pour renommer sans risque

1. **Nom plus court ou égal** : écrire les codes puis `0xFFFF`, et remplir le reste de la place avec `0xFFFF` (l'outil le fait). Caractères permis = octets / 2 - 1. Les octets restants ne sont jamais lus.
2. **Nom plus long** : écrire la chaîne (même codage, `0xFFFF` final, adresse paire) dans une zone libre du §6 (`0x0E3600`-`0x0EFBEF`, `0x1765EA`-`0x1CFFFF`, `0x3F72A8`-`0x3F7FFF` ; octets d'origine `0xFF` ; **jamais** `0xEFBF0`-`0xEFFFF` ni les secteurs vierges `0x3F8000`-`0x3FFFFF`, §6 point 5), puis remplacer par la nouvelle adresse le pointeur de 4 octets de la table de la langue (cellule `base + 4 × id`). Possible parce que le pointeur est relu à chaque affichage et que les 364 chaînes concernées (28 identifiants × 13 langues) n'ont aucune autre référence dans le binaire (recherche de leurs adresses sur 4 octets). La table et les zones libres sont dans les plages réécrites par la mise à jour (`0x200000`-`0x40FFFF`). L'outil place les textes à partir de `0x3F7300` (option `--zone`).
3. **Un identifiant = un endroit** : « Normale », « Portrait » existent sous d'autres identifiants dans d'autres menus (`chercher` les liste tous) ; ne renommer que ceux du §9.4.
4. **Nom dans l'aide** : le nom est répété au début de la ligne d'aide (§9.4) ; le renommer aussi, sinon le menu dit « Tri-X » et l'aide « Moins nette ». Le « : » doit rester le caractère de la police fixe. Une ligne d'aide peut atteindre 265 px (maximum d'usine en anglais), le français d'usine va jusqu'à 228 px.
5. **Personnalisée** (id 221) sert aussi de sous-titre de l'écran Personnalisée : une seule chaîne à changer ; ne pas toucher l'id 236 (option de la Correction des tons).
6. **Langues** : changer au moins le français (table `0x246600`) ; les autres langues gardent les anciens noms.
7. **Largeur** : le libellé est tracé en x = 88 dans la barre de sélection (x de 42 à 309), avec l'astuce « OK » (46 px) alignée à droite de la ligne en surbrillance. Affichables en usine dans cette liste : « Black-and-white » 154 px (ligne à astuce « OK ») et « Benutzerdefiniert » 163 px (ligne Personnalisée, astuce de 20 px). Limite calculée : 309 - 2 - 46 - 88 = 173 px avec « OK ». Vérifié (formules lues) ; limite non essayée à l'écran. Largeurs des noms voulus : Tri-X 47 px, HP5 35, FP4 31, Chrome 70, Positive 73, Hasselblad 99 : tous passent. Une lettre fait en moyenne 10 à 11 px, soit 15 à 16 lettres de large.
8. **Caractères** : uniquement ceux du §9.3 ; l'outil refuse un caractère sans code (`<xxxx>` pour un code brut).
9. **Famille B** (page de données) : 15 caractères au plus, majuscules par habitude, et le créneau d'origine de 8 octets accepte 7 caractères (« TRI-X », « CHROME » passent) ; au-delà, repointer la table `0x16BC90` (non géré par l'outil).
10. Rien n'est vérifiable avant un flash en dehors de la lecture des octets : le patch produit est contrôlé (octets d'origine, CRC) mais jamais essayé sur le boîtier.

Place offerte par le français, pour mémoire : Normale 7, Saturée 7 (« Chrome » passe, « Positive » et « Hasselblad » demandent `--repointer`), Portrait 8 (« Positive » passe), Moins nette 11 et Plus saturée 12 (« Hasselblad » passe), Personnalisée 13 et Noir et blanc 13.

### 9.7 Outil

```
python3 d200/outils/d200_textes.py langues
python3 d200/outils/d200_textes.py chercher "Noir et blanc"          # 0x25924C (fr:254) et 0x2592B8 (fr:248)
python3 d200/outils/d200_textes.py lister 0x25924C 2                  # décode 2 chaînes consécutives
python3 d200/outils/d200_textes.py id fr 254                          # par identifiant
python3 d200/outils/d200_textes.py optimiser --langue toutes          # les 7 entrées et leur aide
python3 d200/outils/d200_textes.py renommer noms.json --sortie d200/patchs/d200-noms.json [--repointer] [--avec d200/patchs/d200-nb-trix.json]
python3 d40/patch.py d200/patchs/d200-noms.json --sortie <dossier>        # fabrique le B (jamais flashé sans le go de Thomas)
python3 d200/outils/d200_textes.py --self-test
```

`noms.json` : `{"fr:254": "Tri-X", "0x259292": "Chrome", "0x16BD34": "CHROME"}` (clé = adresse d'une chaîne, ou `langue:id`, ou créneau ASCII de la famille B). Un nom qui ne tient pas est refusé, sauf `--repointer`. `--avec` ajoute les patchs d'un fichier existant (par exemple le N&B Tri-X) et refuse un chevauchement. Contrôles : le self-test relit « Noir et blanc » en `0x25924C`, vérifie les 13 tables, l'aller-retour de codage sur les langues latines et le russe, applique un patch court, un patch repointé et un créneau ASCII par `d40/patch.py` (CRC à zéro).

### 9.8 Ce qui reste incertain

- Rendu à l'écran des noms les plus longs (limite de 173 px calculée, pas vue) et des lignes d'aide modifiées.
- Fonction qui dessine la page d'aide (21 lignes, hypothèse), et effet exact d'un identifiant d'aide vide (`0xD`).
- Que la page 2 des données refasse sa chaîne depuis le rang pour les anciennes images (famille B) : lu dans `FUN_0006F0F2`, mais la source du rang (relecture du fichier) n'est pas suivie jusqu'au bout.
- Sélecteur de langue réel du boîtier de Thomas (3 attendu) ; langue exacte des tables chinoises, japonaise, coréenne.
- Accents de la police fixe, glyphes `0x297` et `0x298`, majuscules `0x20B`, `0x20D`, `0x210`, `0x212`.
- Un contrôle d'intégrité des textes par le chargeur (non lu, comme pour le reste du chargeur, §8).

## 10. Firmware V1 du D200 (octobre 2026)

**Flashé en octobre 2026** sur le go de Thomas (EXIF des premières vues : Ver.2.01) ; premières vues dans `d200/images/2026-10-test-v1/`.

| | |
|---|---|
| Fichier | `d200/build/v1/B2000201.BIN`, 3 932 160 octets, CRC `47a1`, sha256 `bb052a6017e3ac922164f55e0c36e03bc647d8f2eb5d5df06ffa5f7b3b151d53`. Remplacé par la V2 (§11) pour tout nouveau flash ; tout autre sha256 est périmé (`402f00f5…` : bloc des préréglages en `0x3FA000`, déplacé ; `389a955b…` : combiné d'essai du cache) |
| Recette | `d200/patchs/d200-v1.json` (37 patchs, 22 592 octets changés) = `d200-nb-trix.json` + `d200-noms.json` + `d200-preglages.json` ; refaire : `python3 d40/patch.py d200/patchs/d200-v1.json --sortie d200/build/v1` |
| Place | code et données des préréglages en `0x177000`–`0x17BA00`, dans le secteur `0x170000` que Nikon programme (24 444 octets à lui). En octobre, la relecture a fait sortir le bloc de `0x3FA000`–`0x3FEA00` (secteurs jamais programmés, §6 point 5). Différence avec `402f…` : le bloc déplacé à l'identique, sauf 9 adresses internes relogées, les constantes des deux crochets et le CRC |
| Retour au firmware Nikon | `d200/build/origine/B2000201.BIN`, sha256 `b7cee24dd2034645337cca500109d2ce987bee4ba8bfb521c3285c623f3407d1` (le 2.01 de Nikon, même nom, version égale acceptée, §6) |

**Ce que fait chaque entrée d'Optimiser l'image** (choix de Thomas en octobre : Normal et Personnalisé gardés, Hasselblad laissé de côté) :

| Entrée (menu) | Nom affiché | Rendu | Mécanisme | Vérifié |
|---|---|---|---|---|
| 0 Normal | Normale | Nikon | inchangé | émulateur (identique au firmware d'origine) |
| 1 Moins net | Chrome | Classic Chrome mesuré (X-T4) | crochets ([`d200-preglages.md`](d200-preglages.md)) : matrice ajustée pour le D200, YCbCr BT.601, secteurs neutres, courbe avec épaule ; netteté Moyenne +, saturation Normale | émulateur |
| 2 Saturé | Positive | Positive Film mesuré (Ricoh GR III) | idem | émulateur |
| 3 Très saturé | FP4 | Ilford FP4 Plus | crochets : trois lignes de matrice = pondération du film, courbe film + tirage | émulateur |
| 4 Portrait | HP5 | Ilford HP5 Plus | idem | émulateur |
| 5 Personnalisé | Personnalisée | Nikon (réglages à la main, courbe perso par USB) | inchangé | émulateur |
| 6 Noir et blanc | Tri-X | Kodak Tri-X | données (§5), sans crochet | émulateur |

**Écarts attendus** (ΔE2000 médian) : recette contre le vrai rendu (photos tenues à part) Chrome 0,67, Positive 0,97 ; matrice du D200 contre le modèle du rendu, 424 réflectances : Chrome 1,27, Positive 0,72 ; sur les deux scènes de séance : Chrome 0,5 à 0,7, Positive 0,2 à 0,3. Aperçu simulé, colonnes titrées : figure ; menu dessiné avec la police du firmware : figure.

**Contrôles passés** (refaits après le déplacement) : `python3 d200/emulateur/d200emu.py verifier` code 0, sur un combiné de même sha256 que le fichier à flasher (11 essais : N&B d'origine 403 contrôles, Tri-X 1 738, couleur 157 × 2, préréglages sur le firmware combiné 1 781, trois contre-épreuves qui échouent comme attendu, deux gardes) ; `d40/emulateur/d40emu.py verifier` code 0 ; `d40/patch.py` (original, CRC, plages réécrites, zones interdites, aucun secteur vierge : les 8 secteurs touchés portent déjà des octets de Nikon) ; self-tests de `d200_nb`, `d200_rendus`, `d200_preglages`, `d200_textes`, `d200_seance`.

**Flasher** (Thomas, au boîtier) :
1. Configuration › Version du firmware : lire **A 2.01 et B 2.01**. Toute autre version : ne pas flasher (le fichier est construit sur le B 2.01).
2. Batterie EN-EL3e pleine, ou adaptateur secteur (pas d'interruption pendant l'écriture : c'est le seul vrai risque de brique).
3. Préparer d'abord une **carte de retour** : une seconde carte, formatée dans le D200, avec seulement `d200/build/origine/B2000201.BIN` (sha256 `b7ce…07d1`) à la racine.
4. Carte de flash formatée dans le D200 ; copier `d200/build/v1/B2000201.BIN` à sa racine, seul fichier `B200….BIN` ; contrôler le sha256 `bb052a60…151d53` sur la carte.
5. Configuration › Version du firmware › mise à jour › Oui ; ne rien toucher jusqu'au message de fin ; éteindre, rallumer.
6. Contrôle : Optimiser l'image affiche Normale, Chrome, Positive, FP4, HP5, Personnalisée, Tri-X.
7. Premières vues : une par entrée, en lumière du jour, NEF + JPEG ; les comparer au simulateur (`d200_rendus.py planche`) ; puis Chrome en lumière artificielle.

**Retour arrière** : même procédure avec la carte de retour (`d200/build/origine/B2000201.BIN`). Les crochets ne s'exécutent qu'à la prise de vue et les textes ne servent qu'aux menus : même si un rendu posait problème, le menu Configuration reste joignable pour reflasher (hypothèse forte : le démarrage n'appelle aucune des fonctions détournées).

**Limites connues** :
- Étage à 16 secteurs laissé neutre : il ne se lit pas comme celui du D40 (§3 de [`d200-preglages.md`](d200-preglages.md), §7) ; Chrome y perd un peu de fidélité.
- En ombre et en fluo de classe 3, la correction d'éclairage de Nikon n'est appliquée qu'en partie pour Chrome et Positive (bornes des registres).
- Métadonnées du NEF : elles gardent le nom Nikon de l'entrée (« Moins net », etc.) et la netteté imposée ; Capture NX ne connaît pas Chrome.
- Lecture du bit de signe des registres par la puce, coût du crochet en temps réel (183 000 instructions de plus par photo, horloge inconnue) : non mesurés sur le boîtier.

## 11. Firmware V2 du D200 (octobre 2026)

| | |
|---|---|
| Fichier | `d200/build/v2/B2000201.BIN`, 3 932 160 octets, CRC `7a86`, sha256 `428473ff8f915932327add759fd68dcec6c4c5ae2e0ce7b0c6530403e4aedbce`. **Seul fichier à flasher** |
| Recette | `d200/patchs/d200-v2.json` (37 patchs, 22 688 octets changés) ; refaire : `python3 -B d40/patch.py d200/patchs/d200-v2.json --sortie d200/build/v2` |
| Contenu | la V1, avec d'autres données dans les quatre emplacements et la courbe Tri-X : Chrome et Positive « typés » (matrice et étage à 16 secteurs ajustés sur les paires d'origine, (Cb, Cr) × 0,8 et × 1,2), Tri-X, HP5 et FP4 avec un tirage par film. Choix de Thomas : [`d200-preglages.md`](d200-preglages.md) §5.4 |
| Delta contre la V1 | 11 603 octets, tous dans les données des emplacements (`0x177400`–`0x17BA00`), la courbe N&B (`0x3B22DD`) et le CRC ; code, crochets, tables, textes identiques |
| Contrôles | `d200emu.py verifier` code 0 sur un combiné de même sha256 ; scénario `preglages` 1 781 contrôles sans échec ; relecture indépendante GO : [`d200-v2-relecture.md`](d200-v2-relecture.md) |
| Carte | écrite en octobre, sha256 contrôlé sur la carte, éjectée |

**Flasher** : la procédure du §10, avec ce fichier et ce sha256 (contrôler `428473ff…aedbce` sur la carte, pas `bb052a60…`). **Retour arrière** : la V1 (`d200/build/v1/`, relue) ou le firmware de Nikon (`d200/build/origine/`).

**À voir sur les premières vues** : une par entrée en lumière du jour ; Chrome ou Positive sous fluo de classe 3 (déclinaison réduite à 17,5 %, dominante possible) ; noirs de HP5 vers 37/255 (voulu).

