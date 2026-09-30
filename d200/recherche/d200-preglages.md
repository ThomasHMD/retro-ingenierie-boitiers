# D200 : quatre entrées d'Optimiser l'image, quatre rendus (préréglages)

Patch « préréglages » du firmware B 2.01 du D200, fait en octobre 2026 : Moins net, Saturé, Très saturé et Portrait produisent chacun leur propre rendu JPEG ; Normal et Personnalisé gardent celui de Nikon ; Noir et blanc devient Tri-X par le patch de données déjà prêt. **Rien n'a été flashé, le boîtier n'a pas été touché.** Chaque fait est marqué *vérifié* (lu dans les instructions ou les octets à l'adresse donnée, ou rejoué dans l'émulateur) ou *hypothèse*. Adresses processeur ; offset dans le fichier = adresse − `0x50000`.

Compagnons : [`d200-choix-des-tables.md`](d200-choix-des-tables.md) (chaîne d'appel, numéro de jeu, teinte, saturation), [`d200-firmware-image.md`](d200-firmware-image.md) (moteur d'image, N&B, mise à jour, place libre), [`../emulateur/d200/README.md`](../emulateur/README.md) (émulateur). Modèle porté : les préréglages V1 du D40 ([`../outils/preglages_v1.py`](../../d40/outils/preglages_v1.py), README § « V1 : code des préréglages »).

## 1. En bref

| Entrée du menu (valeur) | Rendu | Comment | Statut |
|---|---|---|---|
| Normal (0) | Nikon | crochets traversés sans rien changer | vérifié (émulateur) |
| Moins net (1) | **Chrome** | matrice, YCbCr, secteurs, courbe du rendu | vérifié (émulateur) |
| Saturé (2) | **Positive** | idem | vérifié (émulateur) |
| Très saturé (3) | **FP4** | N&B par la matrice (trois lignes égales), courbe du film | vérifié (émulateur) |
| Portrait (4) | **HP5** | idem | vérifié (émulateur) |
| Personnalisé (5) | Nikon | crochets traversés sans rien changer | vérifié (émulateur) |
| Noir et blanc (6) | **Tri-X** | patch de données `d200/patchs/d200-nb-trix.json` (pas les crochets) | vérifié (émulateur, inchangé) |

- Pour les quatre rendus : **netteté Moyenne +** (4), **saturation Normale** (1), **correction des tons Normale** (1), teinte 0 (déjà forcée par Nikon), comme sur le D40. Vérifié (émulateur).
- Deux crochets de 4 octets (la constante d'un `LDI:32` existant), 364 octets de code, 18,5 Ko de tables et de données dans la place libre `0x177000`–`0x17BA00`, dans un secteur que chaque mise à jour de Nikon programme déjà (déplacé de `0x3FA000` en octobre, §5.1). Vérifié.
- Fichiers : [`../patchs/d200-preglages.json`](../patchs/d200-preglages.json) (8 patchs, 18 654 octets, `"firmware": "D200B"`), à combiner avec `d200-nb-trix.json` et `d200-noms.json` (aucun chevauchement : contrôlé par l'outil et par `d40/patch.py`). Firmware combiné fabriqué dans le cache seulement.
- `python3 d200/emulateur/d200emu.py verifier` rend **0** (11 essais) ; `python3 d40/emulateur/d40emu.py verifier` rend 0. Vérifié en octobre 2026.

## 2. Outil et commandes

| Commande | Effet |
|---|---|
| `python3 -B d200/outils/d200_preglages.py construire` | écrit `d200/patchs/d200-preglages.json` (octets d'origine vérifiés, place libre contrôlée à `0xFF`, aucune zone interdite) |
| `python3 -B d200/outils/d200_preglages.py build [--sortie DIR]` | combiné d'essai Tri-X + noms + préréglages par `d40/patch.py`, dans `~/Library/Caches/d40-emulateur/d200/firmwares/d200-preglages-combine/` par défaut ; refuse `d200/build/`. **Jamais à flasher** : le fichier à flasher est `d200/build/v2/` (§9) |
| `python3 -B d200/outils/d200_preglages.py scenario` | écrit `d200/emulateur/scenarios/preglages.txt` (valeurs attendues calculées depuis les données des rendus) |
| `python3 -B d200/outils/d200_preglages.py asm` | étiquettes, octets, puis désassemblage du code ajouté par l'émulateur |
| `python3 -B d200/outils/d200_preglages.py --self-test` | octets d'origine des deux sites, aucune instruction à créneau de délai dans le code ajouté, tables, données (lumière du jour = matrice de la recette, N&B = trois lignes égales), combinaison sans chevauchement, tables de Nikon intactes |
| `python3 d200/emulateur/d200emu.py combine preglages` | fabrique le combiné (Tri-X + noms + préréglages) dans le cache et joue le scénario |

Le fichier à flasher, et lui seul, depuis octobre 2026 : **`d200/build/v2/B2000201.BIN`** (V2, §5.4), fabriqué par `python3 -B d40/patch.py d200/patchs/d200-v2.json --sortie d200/build/v2` (37 patchs, mêmes sites que la V1), 22 688 octets changés (CRC compris), CRC `7a86`, sha256 `428473ff8f915932327add759fd68dcec6c4c5ae2e0ce7b0c6530403e4aedbce`, taille `0x3C0000` ; relu (GO, `d200-v2-relecture.md`) ; c'est le combiné que joue désormais `d200emu.py verifier` (mêmes `d200-nb-trix.json`, `d200-noms.json`, `d200-preglages.json`, régénérés en V2). Avant, la V1 (flashée en octobre) : `d200/build/v1/B2000201.BIN`, fabriqué par `python3 -B d40/patch.py d200/patchs/d200-v1.json --sortie d200/build/v1` (37 patchs = Tri-X + noms + préréglages), 22 592 octets changés (CRC compris), CRC `47a1`, sha256 `bb052a6017e3ac922164f55e0c36e03bc647d8f2eb5d5df06ffa5f7b3b151d53`, taille `0x3C0000`, CRC du fichier entier nul  ; refaire la V1 : `d200-v1.json` (les fichiers sources sont passés en V2). Les sha256 `389a955b…` (combiné du cache, courbes sans épaule) et `402f00f5…` (bloc en `0x3FA000`, relu en octobre) sont périmés. Vérifié.

## 3. Mécanisme : deux crochets

Même technique que le D40 : on ne change que la constante d'un `LDI:32 #fonction,R12` suivi de `CALL @R12` ; l'instruction, l'appel et ce qui suit restent ceux de Nikon. Les deux appels choisis sont **sans créneau de délai** (`971C`), comme `0x31B230` sur le D40. Vérifié (octets d'origine relus par le self-test).

| Crochet | Adresse (offset) | Octets d'origine | Octets patchés | Fonction remplacée | Code ajouté |
|---|---|---|---|---|---|
| réglages | `0xCDFAE` (`0x7DFAE`) | `9F8C 000C F86A` puis `971C` | `9F8C 0017 7000` | `FUN_000cf86a` (calcul du jeu, teinte, netteté, saturation, conversion vers la fiche), appelée par `FUN_000cd9a2` juste après `CALL FUN_000ce4fa` | `preglage_reglages` (`0x177000`, 96 octets) |
| puce | `0x5DA28` (`0xDA28`) | `9F8C 000D CFF8` puis `971C` | `9F8C 0017 7060` | `FUN_000dcff8` (rend la table de saturation `0x97BE7F18`), dernier appel d'`isp_chargerPuce` avant la copie en `0x5001EC00` | `preglage_puce` (`0x177060`, 268 octets) |

**Pourquoi là.** `FUN_000ce4fa` traduit le menu en variables (tableau §2.3 de la note) ; elle est appelée par un `CALL` relatif (`D2A6`, pas de constante à détourner) ; l'appel suivant, celui de `FUN_000cf86a`, passe par un `LDI:32`. Le crochet s'insère donc entre la traduction du menu et tout le calcul qui en dépend, dans les trois modes de `FUN_000cd9a2` (0, 1, 2, et le mode 3 du retraitement) : tous finissent par `FUN_000ce4fa` puis `FUN_000cf86a` (vérifié, l. 94762-94980 du pseudo-C). Côté puce, `FUN_000dcff8` est le dernier appel d'`isp_chargerPuce` : matrices, secteurs et courbes de Nikon sont déjà écrits, il ne reste que la copie de la table de saturation, que Nikon fait lui-même avec la valeur que le crochet rend (comme la courbe rendue par le crochet du D40).

**`preglage_reglages`** : lit la fiche par `_DAT_97be3e4c`, mode = (`+0x4D` & `0x1F`) >> 1 ; si le mode est 1 à 4 et `_DAT_97be3dcc` = 0, écrit netteté `0x97BE3DD4` = 4, saturation `0x97BE3DF8` = 1, tons `0x97BE3E08` = 1 (table de 4 octets par emplacement, `0x177220`) ; puis `LDI:32 #0xCF86A,R12 ; JMP @R12` : `FUN_000cf86a` rend directement à `FUN_000cd9a2`. R0, R1, R2, R12, R13 seulement, pas de pile. Vérifié (émulateur).

**`preglage_puce`** : sauve RP et R8 ; appelle `FUN_000dcff8` (R4 = table de saturation de Nikon, gardée sur la pile) ; lit la fiche par `LD @(R14,0x18),R1`, l'instruction même d'`isp_chargerPuce` (`0x5D8D0`), qui y range son argument ; si le mode est 1 à 4, la courbe intégrée (`+0x424` < 23), `_DAT_97be3dcc` = 0, le jeu (`+0x422`) < 294 et d'un espace connu, recopie depuis l'emplacement du rendu :

| Donnée | Vers | Taille | Choix |
|---|---|---|---|
| matrice caméra | `0x50010022` | 9 demi-mots, signe et module (bit `0x400`) | n° = `tbl_jeu[jeu]` : F si E = 0 ou 2, 6 + F si E = 5 ou 6 (Adobe), sinon rendu de Nikon |
| matrice YCbCr | `0x50010034` | 9 demi-mots (bit `0x200`) | une seule |
| secteurs | `0x5001E400`–`0x5001E47F` | 64 demi-mots (bit `0x200`) | **neutres** (256, 0, 0, 256) pour les quatre rendus depuis octobre (§7) |
| courbes R, V, B | `0x50018400`, `0x5001A400`, `0x5001C400` | 4 096 octets → 4 096 demi-mots | `FUN_0005debe(courbe, registre, 0x1000)`, la copie de Nikon pour la courbe N&B |

puis rend R4 = table de saturation de Nikon, restaure R8 et RP. R9 à R11 et R14 ne sont pas touchés (`isp_chargerPuce` se sert de R8 juste après : `0xEC00 + R8`). Vérifié (émulateur : pile rendue à chaque appel, profondeur 52 octets au lieu de 40).

**Le numéro de jeu porte la famille et l'espace.** `jeu = 42 E + 7 F + (6 − K)` (note, §2.5) : F = (jeu mod 42) div 7, E = jeu div 42. Le crochet le lit dans **la fiche de la photo** (`+0x422`, écrit par `FUN_000d93a6`), pas dans la globale `0x97BE0A14` : c'est la leçon du D40 (revue critique d’octobre, rafale). Une table de 294 octets (`0x177240`) donne le n° de matrice, sans division. Vérifié (scénario « deux photos, deux balances » : fiche A en ensoleillé puis fiche B en incandescent calculées, puis puce chargée pour A puis pour B : chacune reçoit sa matrice).

**Aucune instruction à créneau de délai** dans le code ajouté (ni `JMP:D`, `CALL:D`, `RET:D`, `Bcc:D`) : le self-test parcourt le code instruction par instruction, et l'émulateur arrête tout `LDI:32` ou saut posé dans un créneau (scénario `garde-delai`). Vérifié.

**Conditions et gardes.** Chemin des matrices en dur de Nikon (`_DAT_97be3dcc` ≠ 0, bit 4 de `0x9798D753`, sans écrivain connu) : aucun des deux crochets n'agit, comme `_DAT_83eb3d3c` sur le D40 ; dans ce chemin `FUN_000d57e6` ne pose même pas de numéro de jeu (vérifié, l. 101278). Jeu ≥ 294 (N&B : 500), jeu du mode II (E = 1), courbe perso (23) : rendu de Nikon. Vérifié (émulateur, sauf la courbe perso, inatteignable pour les quatre entrées : leurs tons sont forcés).

## 4. Ce qui change pour chaque entrée

| Entrée | Nikon : tons, netteté, saturation, E (sRGB / Adobe) | Patché | Jeu (ensoleillé) | Courbe |
|---|---|---|---|---|
| Moins net | Moins contrasté, Faible, Auto, 0 / 5 | Normale, Moyenne +, Normale | 13 → **10** | 0 → 3 (le crochet remplace ensuite par celle du rendu) |
| Saturé | Normale, Moyenne +, Accentuée, 2 / 6 | Normale, Moyenne +, Normale | 94 → 94 | 17 |
| Très saturé | Plus contrasté, Élevée, Accentuée, 2 / 6 | Normale, Moyenne +, Normale | 91 → **94** | 20 → 17 |
| Portrait | Auto (cran ≤ 4), Moyenne −, Auto, 0 / 5 | Normale, Moyenne +, Normale | variable → **10** | variable → 3 |

E n'est pas changé : il ne sert plus qu'à la netteté, au demi-mot `0x50010056` (« 6 autres » du jeu, selon l'ISO) et au choix de la matrice d'Adobe RGB. Le jeu et la courbe de Nikon ne dépendent plus de la scène (cran 3 fixe). Registres relevés dans l'émulateur (ensoleillé, ISO de la fiche à zéro) : netteté `0x50010054` Moins net `0x0069` → `0x0147`, Saturé `0x0147` inchangé ; `0x50010056` Moins net `0xFF70` → `0xFF86`. Pour chaque cas joué, `0x50010000`–`0x50010021`, `0x50010046`–`0x50010057` (netteté et `0x50010056` compris) et `0x5001E600`–`0x5001F3FF` (tables ISO et saturation) sont **identiques à ceux d'un Personnalisé réglé à la main** (netteté Moyenne +, tons Normale, saturation Normale, même mode couleur I ou III, même balance, même espace). Vérifié (émulateur).

**Saturation Normale : ne re-sature pas.** Colonne de niveau 0 de `0x3A62DD` (ISO 100, 1 024 octets, ligne lue comme l'amplitude de chroma, 128 = ×1 : hypothèse de lecture, valeurs vérifiées) :

| Ligne | 0 | 8 | 16 | 32 | 50 à 280 | 384 | 512 | 768 | 1023 |
|---|---|---|---|---|---|---|---|---|---|
| Normale | 76 | 80 | 90 | 115 | **128** | 125 | 118 | 98 | 89 |

Jamais au-dessus de 128 (aucun gain > 1), atténuation des chromas faibles (bruit autour du gris, plus forte à ISO élevé : 38 au lieu de 76 à la ligne 0 en ISO 1600) et des très fortes. Aucune colonne de la table n'est plate à 128 (vérifié sur les 48). C'est la saturation Normale de Nikon, comme sur le D40 ; une table plate à nous serait possible (le crochet rend déjà le pointeur), non faite : elle supprimerait aussi la réduction du bruit de chroma.

## 5. Données

### 5.1 Place utilisée (vérifié)

| Plage | Contenu | Taille |
|---|---|---|
| `0x177000`–`0x17716B` | code des deux crochets | 364 octets |
| `0x177200`–`0x177365` | « PREGLAGES-D200 », mode → emplacement (16), netteté/saturation/tons (4 × 4), adresses des emplacements (4 × 4), jeu → n° de matrice (294) | 358 octets |
| `0x177400`–`0x17B9FF` | 4 emplacements de `0x1180` octets : Chrome, Positive, FP4, HP5 | 17 920 octets |

Dans la place libre `0x1765EA`–`0x17FFFF` du secteur de 64 Ko `0x170000`, relue à `0xFF` avant écriture. Ce secteur porte 24 444 octets de Nikon (`0x170000`–`0x1765E9`) : chaque mise à jour officielle l'efface et le programme, il ne peut donc pas être protégé en écriture. Aucune constante `LDI:32` du firmware ne vise au-delà de `0x176590` dans ce secteur, et les seuls mots de 32 bits qui tombent dans `0x177000`–`0x17B9FF` sont des paires d'instructions (`0017 B750` dans le code de Nikon) ou des données compressées. Loin de `0xEFBF0`–`0xEFFFF`, de la chaîne de mise à jour et du flasheur, et de `0x176600`–`0x1766FF` (texte « Positive » de `d200-noms.json`). Un emplacement : 12 matrices (`+0x000`, 18 octets chacune), YCbCr (`+0x0D8`), secteurs (`+0x0EA`), courbe (`+0x180`, 4 096 octets).

Première place, abandonnée en octobre : `0x3FA000`–`0x3FE9FF`, dans trois secteurs de 8 Ko où Nikon n'écrit jamais rien. Les deux du haut (`0x3FC000`–`0x3FFFFF`) peuvent être verrouillés par la broche WP# de la puce flash ; le flasheur échouerait alors après avoir effacé le code principal (`d200/recherche/d200-v1-relecture.md`, constat 1). Depuis, `d40/patch.py` refuse tout patch du D200 dans un secteur sans octet de Nikon.

### 5.2 Matrices caméra (×512, lignes = 512, signe et module à l'écriture)

Couleur : `d200_rendus.recette(nom)` : matrice ajustée pour le capteur du D200 au moindre ΔE2000 contre le modèle mesuré du rendu (`d200/recettes/matrices.json`, |coefficient| ≤ 980), **sans secteurs** ; courbe de `d40/recettes/mesures/` avec épaule jusqu'au blanc. Déclinée comme `recettes_v1.decliner` : **M_F = M · N₁⁻¹ · N_F**, N = matrices caméra de Nikon du groupe de l'entrée (E = 0 pour Moins net, E = 2 pour Saturé), F = 1 (lumière du jour) en référence. Adobe RGB : **M_F,Adobe = N_F(E Adobe) · N_F⁻¹ · M_F**, le passage que Nikon fait entre ses propres jeux (lignes de somme 1, ≈ matrice sRGB → Adobe RGB). Borne voulue 1 000 (registre : 1 023) : au-delà, la déclinaison est rapprochée de la matrice du jour (M · ((1 − t) I + t N₁⁻¹ N_F)). Vérifié (calcul) ; la famille F = 5 (flash, hypothèse) a les matrices de F = 1, comme chez Nikon.

| Famille F (balance qui y mène) | Chrome (Moins net) | Positive (Saturé) |
|---|---|---|
| 0 (incandescent, c ≥ 157) | 861 −316 −33 / −11 572 −49 / 65 −221 668 | 820 −94 −214 / −152 803 −139 / −78 −15 605 |
| 1 (ensoleillé, nuageux, flash manuel) | **923 −407 −4 / 7 586 −81 / 52 −191 651** (= recette) | **923 −202 −209 / −115 856 −229 / −82 41 553** (= recette) |
| 2 (ombre) | 951 −461 22 / 13 645 −146 / 38 −156 630 | 973 −235 −226 / −85 942 −345 / −86 116 482 |
| 3 (fluo, classe 2) | 900 −347 −41 / 35 575 −98 / 53 −121 580 | 905 −230 −163 / −91 769 −166 / −82 64 530 |
| 4 (fluo, classe 3) | 1000 −495 7 / … (**t = 0,775**) | 1000 −315 −173 / … (**t = 0,725**) |
| 1, Adobe RGB | 642 −128 −2 / 23 560 −71 / 65 −153 600 | 627 83 −198 / −79 823 −232 / −58 85 485 |

**V2** (§5.4) : lumière du jour = matrice de `d200/recettes/etage-v2.json`, Chrome 980 −577 109 / 27 604 −119 / 84 −291 719, Positive 980 −269 −199 / −187 980 −281 / −95 46 561, déclinées de la même façon ; déclinaisons réduites : Chrome F2 t = 0,775, F4 t = 0,175 ; Positive F2 t = 0,2, F4 t = 0,175 (sous fluo de classe 3, la V2 ne garde que 17,5 % de la correction de Nikon : dominante possible, à voir sur une vue). Le tableau ci-dessus est celui de la V1. Calculé (`d200_preglages.py construire`), relu.

N&B : trois lignes égales = pondération du film (`films_nb.poids`, sensibilités camspec du D200) × 512, somme 512, **les mêmes pour les 12 matrices** (familles et Adobe : un gris reste gris) ; c'est ce que fait le N&B de Nikon (une seule matrice en dur) et le patch Tri-X.

| Film (entrée) | Pondération R, V, B | Écart médian au film | Lignes écrites |
|---|---|---|---|
| FP4 (Très saturé) | 0,199 ; 0,095 ; 0,706 | 3,8 % | 102, 48, 362 |
| HP5 (Portrait) | 0,158 ; 0,048 ; 0,794 | 5,3 % | 81, 24, 407 |

### 5.3 YCbCr, secteurs, courbes

- **YCbCr** : 77, 150, 29 / −43, −85, 128 / 128, −107, −21 (×256, BT.601 de `d200_rendus`) pour les quatre : Cb = Cr = 0 sur un gris, donc N&B exact pour FP4 et HP5. Teinte : forcée à 0 par Nikon pour les préréglages, et la matrice est écrite après la rotation (`FUN_000d846a`). Vérifié.
- **Secteurs** : neutres (256, 0, 0, 256) pour les quatre rendus (64 valeurs → `0x5001E400`, `E420`, `E440`, `E460`). Vérifié (copie). Raison : §7.
- **Courbes** : 4 096 octets (entrée linéaire 12 bits, sortie 8 bits). Chrome et Positive : `recette()['lut']` (déjà au format des 256 seuils de Nikon, développés). FP4 et HP5 : `films_nb.courbe(film, N&B de Nikon)` avec l'épaule de `d200_nb.epaule`, la construction de `d200_nb.table_film` sans le facteur k (la matrice n'a plus la limite des `LDI:8`). Gris moyen calé sur Nikon ; **blanc atteint (255) à la pleine échelle** pour les quatre et pour Tri-X, épaule des V1 du D40 (`recettes_v1.epaule`, compression douce dès −1,5 IL), ajoutée en octobre : avant, Chrome plafonnait à 250, Positive 252, FP4 250, HP5 245, Tri-X 243. Vérifié.
- Pourquoi des octets et pas les 256 seuils des courbes intégrées : `FUN_0005df82` écrit toujours 0 pour l'entrée 0 (sa boucle commence à la sortie 0), donc un pied de film relevé (5 ou 7) n'y tient pas ; la copie `FUN_0005debe` est exacte. Vérifié (instructions `0x5DF82`–`0x5DFB2`).

### 5.4 V2 (octobre 2026, en simulation, rien de flashé)

Retour de Thomas sur la V1 : les rendus couleur et N&B se ressemblent trop. Mesuré (`d200/images/2026-10-test-v1/LISEZMOI.txt`) : Chrome ↔ Positive ΔE2000 médian 1,4 à 2,4 sur ses vues ; Tri-X, HP5, FP4 à 5-10 niveaux sur 255.

- **Couleur, cause** : ce n'est pas un défaut de fidélité. Sur les paires RAW+JPEG des rendus d'origine (13 Classic Chrome, 24 Positive Film ; `rendus.py extraire`, copie des échantillons dans le chantier `2026-10-d200-v2/paires`), la V1 est déjà à ΔE2000 médian 1,0 (Chrome) et 1,1 (Positive) ; les deux modèles mesurés, appliqués aux mêmes scènes de Thomas, ne s'écartent que de 1,4 à 2,5. Ils divergent sur les couleurs saturées (rouges, oranges, violets, magentas : chroma × 0,63-1,11 pour Chrome contre × 1,06-1,34 pour Positive, réflectances spectrales sous D65), presque absentes des vues de test. Calculé (`d200_rendus`, prototypes d’octobre).
- **Couleur, V2 fidèle** : `d200_rendus.py etage` ajuste ensemble la matrice et les 64 valeurs de l'étage (modèle `d200_etage`, sondes 1 à 3) sur ces paires, avec un gain par image, 1 image sur 4 tenue à part ; écrit `d200/recettes/etage-v2.json`. Tenu à part : Chrome médiane 0,94 → 0,83, 90e centile 1,90 → 1,64 (entraînement 2,88 → 1,72) ; Positive 1,10 → 1,00, 2,73 → 2,54. Secteurs dans 0,5-1,8 (diagonale) et ±0,5 (termes croisés), soit |v| ≤ 285 (registre 511). Nœuds peu couverts par les paires (Chrome : jaunes, 180-225° ; Positive : 22-45°, 202-270°) : tenus par le lissage et le rappel au neutre. Calculé.
- **Couleur, V2 typée** : la fidèle, (Cb, Cr) × 0,8 pour Chrome et × 1,2 pour Positive par les secteurs (`d200_rendus.TYPE`). Écart Chrome ↔ Positive : 5,4 / 3,2 / 7,9 (5298 / 5300 / roue) contre 2,4 / 1,4 / 4,5 en V1. S'éloigne volontairement des rendus mesurés. Calculé.
- **N&B** : un tirage par film (`d200_nb.TIRAGE`, `films_nb.courbe(…, papier=…)`), gris de la scène toujours à 118. Niveaux de −2 à +2 IL : Tri-X 17, 47, 118, 200, 241 (papier dur, noirs profonds) ; HP5 55, 78, 118, 162, 203 (papier doux, noirs mats vers 37) ; FP4 34, 64, 118, 180, 224 (contraste moyen, hautes lumières longues). Calculé.
- Planches : `d200/images/2026-10-test-v1/comparaison-v2-couleur.jpg` et `comparaison-v2-nb.jpg` (`d200_rendus.py planche-v2`).
- **Choix de Thomas** (octobre 2026, 18:17) : « je préfère les V2 et les typés oui » → couleur typée, N&B V2 (`d200_preglages.VARIANTE = 'type'`, `VERSION_NB = 2`). Construite : `d200/patchs/d200-v2.json` → `d200/build/v2/` (§2), sha256 `428473ff8f915932327add759fd68dcec6c4c5ae2e0ce7b0c6530403e4aedbce`. Delta contre la V1 : données seulement (matrices et secteurs de Chrome et Positive, courbes de FP4, HP5 et Tri-X) et CRC, 11 603 octets ; code, tables, textes identiques. Émulateur : `verifier` code 0, `preglages` 1 781 contrôles sans échec. Relecture indépendante : GO sur ce sha256 (`d200-v2-relecture.md`). Carte écrite et sha256 contrôlé dessus en octobre.

## 6. Résultats de l'émulateur (octobre 2026)

`python3 d200/emulateur/d200emu.py verifier` → **code 0**, 64 s sur le Mac Studio :

| Essai | Firmware | Scénario | Attendu | Résultat |
|---|---|---|---|---|
| a. N&B | origine | `nb-origine` | 0 | OK, 403 contrôles |
| b. N&B Tri-X | Tri-X seul | `nb-trix` | 0 | OK, 1 738 contrôles |
| b′. contre-épreuve | origine | `nb-trix` | 1 | OK, 422 échecs |
| **b″. N&B** | **combiné** | `nb-trix` | 0 | **OK, 1 738 contrôles : toujours Tri-X** |
| c. couleur | origine | `couleur-origine` | 0 | OK, 157 contrôles |
| c′. couleur | Tri-X seul | `couleur-origine` | 0 | OK |
| **d. préréglages** | **combiné** (Tri-X + noms + préréglages) | `preglages` | 0 | **OK, 1 781 contrôles, 0 échec** |
| **d′. contre-épreuve** | origine | `preglages` | 1 | **OK, 1 218 échecs** |
| **d″. contre-épreuve** | Tri-X seul (sans crochets) | `preglages` | 1 | **OK, 1 218 échecs** |
| gardes | origine | `garde-delai`, `garde-noyau` | 2 | OK |

`python3 d40/emulateur/d40emu.py verifier` → code 0 (4 essais), rejoué en octobre 2026 : le D40 n'est pas touché.

**Ce que vérifie `preglages`** (chaque cas : registres et tampons remplis de `0xEE` avant l'appel, fiche neuve, `FUN_0005d616(fiche, 1)` puis `isp_chargerPuce(fiche)`, pile rendue, aucune garde) :

| Cas | Contrôles |
|---|---|
| Les 4 rendus × ensoleillé (F = 1) et incandescent (F = 0), sRGB ; Chrome et FP4 en ombre (F = 2), Positive en fluo (F = 4, déclinaison réduite) ; Chrome, Positive, HP5 en Adobe RGB (jeux 220, 255) ; Chrome en balance auto (fiche à zéro) | variables netteté 4, saturation 1, tons 1 ; jeu et courbe attendus (`42 E + 7 F + 3`, 3 ou 17) ; fiche `+0x4C` = `0x85` ; fiche `+0x33C` = matrice du jeu de Nikon (non touchée) ; registres caméra, YCbCr et 64 secteurs = valeurs écrites dans le scénario depuis les données du rendu ; 3 × 4 096 demi-mots de courbe = la courbe du rendu ; reste des registres, tables ISO et saturation = Personnalisé de référence |
| Normal (ensoleillé, incandescent, Adobe), Personnalisé (réglages de la fiche, mode III ; Normale mode I en Adobe), Noir et blanc Tri-X (ensoleillé, incandescent) | registres `0x50010000`–`0x50010057`, `0x50018400`–`0x5001F3FF` et fiche `+0x300`–`+0x45F` **identiques** à la même fiche jouée sans crochets (constantes de Nikon remises le temps du passage) |
| Deux photos, deux balances | fiches calculées l'une après l'autre (jeux 10 et 3), puces chargées ensuite : chacune sa matrice |
| Jeu 500 puis 52 posé dans la fiche | rendu de Nikon tel que la fiche le dit (caméra, YCbCr, secteurs, courbe intégrée 3) |
| Chemin des matrices en dur (bit 4 de `0x9798D753`) | identique sans crochets, `_DAT_97be3dcc` = 1 |

Coût : `isp_chargerPuce` passe de 96 667 à 183 255 instructions quand un rendu est actif (courbes de Nikon puis les nôtres, copies) ; +29 instructions quand le crochet laisse passer. Vérifié (compte de l'émulateur).

## 7. Ce qui reste hypothèse

| Point | Pourquoi | Comment le lever |
|---|---|---|
| **Étage à secteurs du D200 lu comme celui du D40** (blocs t1, t2, t3, t4 → `E400`…`E460`, nœuds du D40) | même famille de puce, mêmes adresses de blocs | **infirmé en pratique en octobre** : sur les vues de séance (mode I, ensoleillé, jeu 10, dont Nikon a modifié 6 secteurs), appliquer les secteurs de Nikon avec ce modèle éloigne le simulateur du JPEG du boîtier, dans tous les ordres essayés (ΔE2000 médian des 10 % de blocs les plus touchés : 1,8 sans, 2,2 à 3,0 avec). D'où des secteurs neutres et des matrices réajustées sans eux (`d200_rendus.py`). Pour les rouvrir : sonde comme sur le D40 (`d40/outils/sonde_secteurs.py`).<br>**Roue de teintes, octobre après le flash** (`d200/images/2026-10-roue-teintes/`, 4 vues par USB, écart (Cb, Cr) simulé contre JPEG sur les zones uniformes) : mode II plat à 2 % près ; modes I et III ne touchent presque que les cyans et les bleus (θ = atan2(Cr, Cb) de 280 à 345° : gain 0,94 à 1,07, ±4°), rien de visible dans les verts où le mode I a ses secteurs 10-11. Meilleure disposition cherchée sur le mode I (2 880 × 3 essais : départ, sens, ordre des blocs, transposée, transitions franches ou fondues, force) : secteur 0 vers 97°, sens décroissant, transitions fondues, **force moitié** de la lecture 2×2/256 ; mode I 1,329 → 1,229, contrôle sur le mode III (non ajusté) 1,128 → 1,022. Partielle, donc **sonde** : `d200/patchs/d200-sonde-secteurs.json` → `d200/build/sonde-secteurs/B2000201.BIN` (sha256 `3a959841…6832`, CRC `c953`), la V1 à 15 octets près : secteurs de Positive (Saturé) = 0 gris, 4 ×0,5, 8 rotation 45° (b1 181, b2 −181, b3 181, b4 181), 12 ×1,5, les autres neutres ; émulateur (`d200emu.py scenario preglages --firmware d200/build/sonde-secteurs/B2000201.BIN` ; `verifier`, lui, joue la V1, pas la sonde) : 40 écarts attendus, tous sur ces valeurs dans les 4 chargements de Positive, le reste conforme. Le ×1,5 (384) n'a aucun précédent chez Nikon (diagonales 170 à 256) : au pire une couleur fausse en Saturé, sans risque pour le boîtier. Relecture indépendante : GO (`d200-v1-relecture.md`, « Sonde d’octobre »).<br>**Sonde n° 1 flashée et photographiée en octobre** (`d200/images/2026-10-sonde-secteurs/`). Vérifié : l'étage est bien `[b1 b2 ; b3 b4] / 256` appliqué à (Cb, Cr), **non transposé** (rotation positive, crête +34° sur des tranches de 5,6°), **à pleine force** (secteur 0 : gain 0,07 au centre ; ×0,6 pour 0,5 ; ×1,3 à 1,4 pour 1,5, écrêtage compris) ; contrôle Moins net (secteurs neutres) plat à 2 % près hors des cyans. **Le premier secteur de chaque groupe de 4 est sur un axe** : 0 → −Cb (jaunes, 177°), 4 → +Cb (bleus, 357°), 8 → −Cr (cyans-verts, 268°), 12 → +Cr (rouges, 85°), à ±3° ; transition sur ±15 à 20° autour de chaque nœud. Ce modèle (nœuds, interpolation linéaire) ramène la sonde de 2,18 à 1,62 (plancher du contrôle : 1,32). **Ordre dans chaque groupe : non résolu** (sens décroissant pour le groupe 1, tiré des modes I et III de Nikon sur la roue ; le groupe 2 se contredit entre roue et séances). D'où la **sonde n° 2** : `d200/patchs/d200-sonde-secteurs-2.json` → `d200/build/sonde-secteurs-2/B2000201.BIN` (sha256 `91bbd9e3…cb6e8`, CRC `e07e`), secteurs de Positive en rampe, secteur s → chroma × (64 + 12 s)/256, sans rotation : le gain lu sur la roue donne directement le numéro du secteur à chaque teinte. Émulateur (`scenario preglages --firmware` sur la sonde 2) : 128 écarts attendus (32 valeurs × 4 chargements de Positive), rien ailleurs ; même zone de 128 octets que la sonde n° 1. Relecture indépendante : GO (`d200-v1-relecture.md`, « Sonde 2 d’octobre »).<br>**Sonde n° 2 flashée et photographiée** (`d200/images/2026-10-sonde-secteurs-2/carte.txt`, outil `d200/outils/d200_etage.py carte`) : gains justes aux nœuds connus (s0 0,27/0,25 ; s4 0,45/0,44 ; s8 0,62/0,625 ; s12 0,79/0,81 ; s14 0,92/0,91). Carte : s0 180°, s1 → s3 de 197 à 247° (vers les verts), s8 270°, s7 et s6 292 à 315°, s4 vers 355°, s14 vers 45°, s13 vers 79°, s12 90°. Brouillé : 100-160° (s ≈ 9 à 11, témoin lui-même à 0,82-0,88), 275-290° (s ≈ 9-10), 320-340° (s ≈ 3-5) ; pas de données de 0 à 35° (écrêtage). Une rampe ne donne que la moyenne des deux nœuds voisins, et le simulateur est moins juste dans les rouges et les cyans. D'où la **sonde n° 3** : `d200/patchs/d200-sonde-secteurs-3.json` → `d200/build/sonde-secteurs-3/B2000201.BIN` (sha256 `7b40a5d7…49b155`, CRC `2921`), numéro de secteur codé en binaire sur Chrome et Positive (matrice g·R(r) : g = 0,45 ou 1, r = ±20° ; Positive bits 0 et 1, Chrome bits 2 et 3) ; émulateur : 704 écarts, tous dans `0x5001E400`–`47F` des 11 chargements de Chrome et Positive. Relecture indépendante : GO (`d200-v1-relecture.md`, « Sonde 3 d’octobre »).<br>**Résolu en octobre (sonde n° 3 photographiée, `d200/images/2026-10-sonde-secteurs-3/`)** : 16 nœuds tous les 22,5° de θ = atan2(Cr, Cb), interpolation linéaire entre voisins ; nœud k → secteur `[4, 13, 14, 15, 12, 11, 10, 9, 0, 1, 2, 3, 8, 7, 6, 5][k]` : les axes −Cb (jaunes), +Cb (bleus), −Cr (cyans-verts), +Cr (rouges) portent les secteurs 0, 4, 8, 12 ; dans chaque quadrant, groupe g = 2·(Cr > 0) + (Cb > 0), secteurs 4g + 1 à 4g + 3 de l'axe Cb vers l'axe Cr (`d200/outils/d200_etage.py`, `NOEUDS`, `appliquer`). Écart (Cb, Cr) simulé/JPEG avec ce modèle : sonde 2 7,08 → 1,09, sonde 3 Saturé 5,47 → 1,37, Moins net 6,10 → 1,14 (plancher du témoin neutre : 1,31), sonde 1 2,18 → 1,63 ; décalage d'angle optimal 0 ± 3°. **Contrôle indépendant sur les réglages de Nikon** (jamais utilisés pour bâtir la carte) : mode I −19 à −38 % sur les 14 vues (roue et deux séances), qui rejoignent le plancher du mode II ; mode II inchangé (neutre) ; mode III −14 % sur la roue, 0 à −3 % sur les séances (peu de cyans-bleus dans ces scènes). L'étage est donc utilisable pour la V2 : le secteur 0 agit sur les jaunes, 1 à 3 sur les jaunes-verts à verts, 8 sur les cyans-verts, 7 à 5 sur les cyans à bleus, 4 sur les bleus, 13 à 15 sur les violets-magentas, 12 sur les rouges, 11 à 9 sur les rouges-oranges à oranges-jaunes |
| **Métadonnées du NEF** | les données brutes ne sont pas touchées (le moteur lit le tampon RAW, les crochets n'écrivent que la puce et quatre variables) ; la fiche, elle, change à `+0x4C` (netteté 4, tons 1, saturation 1 : vérifié) et garde le jeu, la courbe et les matrices de Nikon (`+0x33C`, `+0x422`, `+0x424` : vérifié). Les NEF de la séance d’octobre montrent que la MakerNote donne les valeurs effectives du préréglage (Saturé : Saturation « High », Moins net : ToneComp « Low ») et le nom de l'entrée (ImageOptimization « Soft », « Vivid », « Portrait ») ; la courbe `ContrastCurve` est la même dans les 6 NEF relus (le tampon de la courbe perso) | attendu après flash : ImageOptimization inchangé (nom Nikon de l'entrée), Sharpness, ToneComp et Saturation à Moyenne +, Normale, Normale ; ColorHue Mode1 ou Mode3 inchangé. Capture NX rendrait le NEF avec le traitement Nikon de l'entrée, pas Chrome (hypothèse) ; Lightroom ignore ces balises. L'aperçu JPEG intégré au NEF sort probablement de la même passe de la puce, donc avec le rendu (hypothèse). À contrôler avec `exiftool` sur le premier NEF pris |
| Le bit 7 de `+0x4D` est l'espace Adobe RGB | déduit des matrices (note §2.4) ; le crochet ne fait que suivre le passage que Nikon applique entre ses jeux E = 0/2 et 5/6 | une vue en Adobe RGB après flash |
| La puce lit le bit `0x400` (`0x200`) comme un signe | déjà hypothèse du patch N&B, cohérente avec le simulateur | une vue après flash |
| Familles et balances (incandescent = F0, ombre = F2, fluo = F3 ou F4, F5 = flash) | noms des modes 1 à 6 de l'octet `0x56` déduits des tables (note §2.6) ; les valeurs de F, elles, sont vérifiées dans l'émulateur | une vue par balance |
| Coût en temps (+86 600 instructions par chargement de la puce) | `isp_chargerPuce` est appelée par `FUN_0005d444` juste avant de lancer le moteur sur un tampon en mémoire, pas pendant la pose ; horloge du processeur B inconnue (de l'ordre de la milliseconde à 100 MHz) | rafale de 5 vues/s après flash |
| `_DAT_97be3dcc` lu en globale par le crochet de la puce | même réserve que sur le D40 ; ce chemin semble mort (aucun écrivain du bit 4) | sans objet tant qu'il l'est |
| Lecture « gain ×128 selon l'amplitude de chroma » de la table de saturation | la puce ne se lit pas | une vue Saturation Normale contre Accentuée sur une charte |

## 8. Risques relevés

1. **Secteurs** (§7) : neutres, donc sans risque de teintes déformées ; coût mesuré contre le modèle du rendu sur les deux scènes de séance : Chrome 0,5 à 0,7 ΔE2000 médian (contre 0,3 à 0,4 avec secteurs si le modèle du D40 avait été juste), Positive 0,2 à 0,3 (meilleur).
2. **Déclinaison réduite** : en ombre (F = 2) et en fluo de classe 3 (F = 4), la correction d'éclairage de Nikon n'est appliquée qu'en partie, sinon un coefficient dépasse 1 000 : Chrome F2 67 %, F4 17 % ; Positive F2 20 %, F4 45 %. En ombre, Positive garde donc surtout la matrice du jour (la balance des blancs, elle, est faite). Vérifié (`d200_preglages.py --self-test`).
3. **Blancs** : réglé en octobre (épaule, §5.3).
4. **Métadonnées** (§7) : un NEF Moins net dirait « Soft » avec une netteté Moyenne +, et un logiciel qui relit la MakerNote (Capture NX) ne retrouverait pas Chrome.
5. **Combinaison** : les trois patchs (Tri-X, noms, préréglages) ne se chevauchent pas et passent `d40/patch.py` ensemble (37 patchs). Retirer Tri-X laisse le N&B de Nikon sur l'entrée 6 ; retirer les préréglages laisse les noms nouveaux sur des rendus Nikon. Vérifié (combinaison) ; cohérence des noms : à Thomas.
6. Non couvert par l'émulateur : l'image elle-même (la puce n'est que de la mémoire), le chronométrage, les autres chemins qui chargeraient la puce sans `isp_chargerPuce` (aucun trouvé : dans le pseudo-C, seule `isp_chargerPuce` cite `0x50010022`, `0x5001E400` et les trois courbes ; une écriture par base + décalage échapperait à cette recherche), l'exécution du code en `0x177000` par le boîtier après flash (aucun code de Nikon n'est au-delà de `0x15CA56`).

## 9. Avant un flash (sur le go de Thomas seulement)

1. `python3 -B d200/outils/d200_preglages.py --self-test`, `construire`, `build`, puis `python3 d200/emulateur/d200emu.py verifier` : codes 0.
2. Fichier : `d200/build/v2/B2000201.BIN`, sha256 `428473ff8f915932327add759fd68dcec6c4c5ae2e0ce7b0c6530403e4aedbce` (§2), et aucun autre ; procédure complète : `d200-firmware-image.md` §10 et §11.
3. Premières vues : une par entrée (0 à 6) sur une charte en ensoleillé, puis Moins net en incandescent et en Adobe RGB ; comparer au simulateur (`d200_rendus.py planche`) ; `exiftool` sur un NEF pour les métadonnées ; une sonde de secteurs si Chrome ou Positive s'écarte.
