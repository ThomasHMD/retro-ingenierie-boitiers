# Réécrire le firmware du D40 : ce que le matériel permet vraiment

Recherche d’octobre 2026, pour le menu « Préréglage couleur » (Normal Nikon, Hasselblad, Classic Chrome, Positive Film, HP5, Tri-X…). Rien n'a été flashé, rien n'a été installé, aucun autre fichier du projet n'a été modifié.

Légende : **[lu]** = lu dans le code ou les données du firmware B v1.11 (adresses processeur, fonctions de `d40-tout.c` régénérable par `desassemblage/regenerer.sh`) ; **[source]** = source extérieure citée ; **[déduit]** = raisonnement à partir de faits lus ; **[estimé]** = chiffre calculé sur des hypothèses explicites, à mesurer.

Sources locales : `CARTE.md`, `README.md`, `recherche/emulation-faisabilite.md`, `recherche/traitement-image-depuis-2006.md` ; clone de nikon-firmware-tools dans `<dossier de travail>/nft/` (noté `nft/`) ; pages du wiki nikonhacker.com récupérées sur la Wayback Machine (le site renvoie 404 depuis 2025).

---

## Résumé

1. **La puce d'image du D40 est bien plus riche que ce que Nikon en utilise.** Le moteur de traitement (bloc `0x40010000`) a, en plus de ce qu'on connaissait : **trois tables de tonalité indépendantes de 4 096 entrées, une par canal R, G, B** (Nikon y copie la même courbe trois fois), et **un étage de chroma à 16 secteurs** (4 tables de 16 valeurs, chargées à chaque photo, **toutes neutres dans les 18 jeux d'usine**). Ce dernier a la forme d'une correction de saturation et de teinte par secteur de teinte. [lu ; sens exact de l'étage 16 secteurs : déduit, à confirmer par un essai]
2. **L'image complète passe par la mémoire en YCbCr 4:2:2 planaire** (Y 3 008 × 2 000, Cb et Cr 1 504 × 2 000, 12,2 Mo) entre le traitement (tâche 8) et l'encodeur JPEG matériel (tâche 9), qui la relit en mémoire. On peut donc intercaler une étape logicielle, et le point d'accroche est une table de pointeurs (`0xC6220`). [lu]
3. **Un traitement logiciel par pixel sur le CPU est possible mais lent** : 1,5 à 3,5 s par photo pour une table 2D sur la chroma, 15 à 30 s pour une vraie LUT 3D pleine résolution. [estimé] Il ne sert que pour le résidu, si l'étage 16 secteurs ne suffit pas.
4. **Aucun projet n'a touché au traitement couleur d'un Nikon** : Nikon Hacker a modifié des débits vidéo, la compression NEF/JPEG, le « star eater », la batterie. Mais ils ont **injecté du code dans l'espace libre** (NEF sans perte, « True Dark Current » avec une entrée de menu réaffectée sur le D5100) : c'est exactement la technique dont on a besoin. [source]
5. **Deux boîtiers de l'équipe ont été bloqués** (D5100, D3100) par des patchs de code en test ; le D5100 n'a jamais été récupéré. Cause connue : une instruction interdite dans le créneau de retard d'un branchement FR. [source]
6. **Architecture recommandée** : un seul crochet dans le chemin de prise de vue (après le chargement des tables du moteur, `0x4B41C`), qui réécrit les registres du moteur depuis la fiche du préréglage choisi ; « Normal » ne passe pas par le crochet. Rien au démarrage, rien dans la mise à jour.

---

## 1. Le matériel du D40

### 1.1 Les deux processeurs et la puce d'image

| Élément | Ce qu'on sait | Statut |
|---|---|---|
| Processeur B | Cœur Fujitsu FR intégré à la puce d'image Nikon (pas une puce séparée) ; REALOS/FR « COPYRIGHT(C) FUJITSU 1994-1999 » dans le firmware | [lu] chaîne du firmware |
| Puce d'image | **Nikon EI-137**, « basée sur l'ancien Milbeaut M-3 en 180 nm », cœur **FR-71**, « sans DSP, mémoire plus lente, fonctions réduites », commune aux D40, D40x, D80, D60, D3000 | [source] [Wikipedia, Expeed](https://en.wikipedia.org/wiki/Expeed) (cite une revue Photo.net du D80) ; source secondaire |
| Cousins | Même famille de blocs que l'Expeed 2 du D5100 : `0x4001xxxx` moteur de dématriçage, `0x40020000` convertisseur de résolution, `0x40030000` JPEG, `0x40060000` concentrateur du coprocesseur image, `0x40090000` Huffman | [source] wiki nikonhacker « Understanding Firmware » (Wayback, 23/03/2023) ; [lu] le D40 écrit aux mêmes adresses |
| DSP FR-V | Le D5100 a deux cœurs DSP (registres `0x401C0000`, `0x401D0000`). **Le code du D40 n'y accède jamais** (aucune adresse `0x401C…`/`0x401D…` parmi ~1 800 accès matériels relevés). Cohérent avec « sans DSP » | [lu] |
| Processeur A | Second FR, exposition, molette, flash (CARTE §10) | [lu] |
| Fréquence du CPU | Non trouvée. Le tic du noyau est la minuterie 0, rechargée à 33 000 avec l'horloge périphérique / 2 (`0xC1314`, juste avant `set_tim`) : **si** le tic vaut 1 ms (valeur usuelle, non vérifiée), l'horloge périphérique est à **66 MHz**. Le Milbeaut M-4 de 2006 (90 nm) tourne à 108–132 MHz pour le CPU et 54–66 MHz pour le traitement d'image ([Fujitsu, 12/07/2006](https://info.archives.global.fujitsu/global/about/resources/news/press-releases/2006/0712-01.html)) ; le M-3 est plus ancien. **Fourchette retenue : 66 à 133 MHz.** | [estimé] |
| Cache | Cache d'instructions activé au reset (`0x3E7 = 3`, `0x3E0 = 0xC7000002` dans `reset`, `0xC0F90`). Cache de données : inconnu | [lu] / point ouvert |
| Calcul flottant | Pas d'unité flottante : le réglage de teinte passe par des routines de calcul flottant logiciel (`0xBE352`, `0xBE968`, `0xBEB22`… appelées par `0x322606`) | [lu] fonctions, [déduit] pas de FPU |
| Mémoire vive | SDRAM à `0x80000000` ; le code utilise des adresses jusqu'à `0x83ED5B08` (piles des tâches). **64 Mo** probables. Mémoire interne `0x68000000` : ~3,5 Ko utilisés (variables du noyau), taille inconnue (128 Ko sur le D5100) | [lu] adresses ; [déduit] taille |
| Tampon d'image | Une image L en YCbCr 4:2:2 planaire : Y à `base + 0x2F90`, Cb à `+ 0x5CF590`, Cr à `+ 0x8B5890` ; Y 6 080 000 octets (pas de ligne 3 040), Cb et Cr 3 040 000 (pas 1 520) ; table des tailles `0xC62D0` (largeur, hauteur, pas) : L 3008×2000 (chroma 1504×2000), M 2256×1496 (chroma 1128×1496), aperçu 570×375 | [lu] `0x4B260`, `0x4883A`, table `0xC62D0` |
| Flash | Firmware B de 4 Mo chargé en `0x40000`–`0x40FFFF` ; libre et écrit par la mise à jour : **164 Ko** à `0x3E7000`, 16 Ko à `0xEB000`, 8 Ko à `0x15E000` (CARTE §3). Récupérable : les 13 langues inutiles (~36 Ko chacune, CARTE §5), soit ~470 Ko | [lu] |
| Chargeur de démarrage | `0x0F0000`–`0x11FFFF` jamais écrit par la mise à jour, vecteurs de mise sous tension à `0xFFC00` (CARTE §3). Sur le D5100, `0xE0000`–`0xFFFFF` est une **ROM de démarrage interne** « avec une fonction de récupération si la mise à jour échoue », que le flasheur saute | [lu] D40 ; [source] wiki « Understanding Firmware » pour le D5100 ; [déduit] même schéma sur le D40 |

### 1.2 Le moteur de traitement d'image : les étages réellement câblés

Tout passe par une fonction lancée **à chaque photo** : `0x4B260` donne au moteur l'adresse du RAW (`0x4001FF08`) et des trois plans de sortie (`0x4001FF0C/10/14` = les plans Y, Cb, Cr ci-dessus), puis appelle `0x4B41C`, qui charge les tables, puis démarre le moteur (`0x4001FF00 = 0x4000`). [lu]

Ce que `0x4B41C` écrit (champs de la fiche de prise de vue pointée par `_DAT_83eb5864`, remplie par `tonalite_choisirNumero` `0x3234BE` et `couleur_chargerMatrice` `0x320CD8`) :

| Registre du moteur | Taille | Contenu chargé par Nikon | Usage pour nous | Statut |
|---|---|---|---|---|
| `0x40012400`, `0x40014400`, `0x40016400` (+ `0x40010400`, `0x40010200`) | 3 × 4 096 (+ 4 096, 256) | Tables fixes chargées au démarrage par `isp_chargerTablesFixes` (`0x4BE82`) : carré, racine carrée, droite | Linéarisation d'entrée, à laisser | [lu] valeurs ; rôle [déduit] |
| `0x40010006`–`0x40010020` | 14 valeurs | Champs `+0x388`–`+0x3A2` (balance des blancs, niveaux ?) | À laisser | [lu] ; rôle inconnu |
| **`0x40010022`** | 9 | **Matrice caméra → RGB** (`+0x3A4`, depuis `tblMatricesCamRgb` `0x332888`, ou `tblMatrices3` en N&B) | Matrice du préréglage | [lu] |
| **`0x40018400`, `0x4001A400`, `0x4001C400`** | **3 × 4 096** | **La même courbe de tonalité copiée trois fois** (`tonalite_construire` → `0x83EB586C`) | **Une courbe par canal** : virage des ombres, courbes « film » par couche, N&B viré | [lu] la triple copie ; [déduit] une table par canal |
| **`0x40010034`** | 9 | **Matrice RGB → YCbCr avec saturation** (`+0x3B6`, `0x33270E`) ; le réglage Teinte la fait tourner (cos/sin de `0x331AF0`, `0x322606`) | Saturation globale, teinte globale | [lu] |
| **`0x4001E400`, `0x4001E420`, `0x4001E440`, `0x4001E460`** | **4 × 16** | Champs `+0x3DC`, `+0x3FC`, `+0x41C`, `+0x43C`, depuis `0x331E0E` (18 jeux de 64 valeurs, un par matrice caméra 0–17). **Les 18 jeux valent tous : table 1 = 256 partout, tables 2 et 3 = 0, table 4 = 256.** Hors chemin normal, `couleur_chargerMatrice` écrit les mêmes valeurs en dur | **Correction par secteur de teinte** : 16 secteurs × une matrice 2×2 sur (Cb, Cr) (lecture « [256 0 ; 0 256] = identité »), ou 16 secteurs × (gain, décalage) sur deux axes. Dans les deux lectures : saturation et teinte réglables secteur par secteur | [lu] structure et valeurs ; [déduit] le sens, **à confirmer** |
| `0x4001E600` | 256 | Table choisie par la classe d'ISO (`+0x467`, `0x3209DE`) | Réduction du bruit (probable), à laisser | [lu] ; rôle [déduit] |
| `0x4001E800`, `0x4001EA00`, `0x4001FC00` | 3 × 256 | Choisies par ISO × netteté (`0x3229CA`) | Accentuation (probable), réglable par préréglage | [lu] ; rôle [déduit] |
| `0x4001EC00` | 1 024 | `+0x46C`, 48 tables compressées à `0x34052B` (et une autre famille en N&B) | Inconnu (table de luminance ?) | [lu] ; rôle inconnu |

Ce qu'**il n'y a pas** : aucune LUT 3D, aucune table indexée par la teinte **et** la luminosité, aucun étage dont la réponse dépend de la saturation de façon non linéaire. [lu : aucune autre table chargée par `0x4B41C`]

### 1.3 Les autres moteurs utiles

- **Convertisseur de résolution `0x40020000`** (mémoire → mémoire) : matrice 3×4 (avec décalage) et **trois tables de 256 valeurs**, une par canal (`0x40020400`, `0x40020500`, `0x40020600`). Retouche › Monochrome s'en sert : `menu_action_12DFD4` (Noir et blanc, Sépia, Cyanotype) → `0x65E0C`, matrices `0xD06E0` (Y gardé, chroma × 25/256), `0xD06C8`, `0xD06B0`, tables `0xD3E95`… ; et l'affichage s'en sert pour passer de YCbCr à RGB (`0xD06F8` = BT.601, `redim_chargerCourbes8bits` `0x66510`). [lu] Utilité pour nous : une seconde passe matérielle 8 bits (courbes par canal + matrice) sur une image déjà développée, gratuite en temps CPU, sans sélectivité de teinte.
- **Encodeur JPEG `0x40030000`** : lit Y, Cb, Cr en mémoire (`0x49A7C`, paramètres 4 à 6), avec une boucle de régulation de taille (`0x4A164` : cible = taille / 16, / 8 ou / 4 selon la qualité). [lu]
- **Histogramme `0x40060000`** (`histogramme_lire` `0x12337E`). [lu, CARTE §2]

### 1.4 Ce que ça change

On pensait n'avoir que matrice + une courbe + saturation et teinte globales. On a en plus **trois courbes par canal** et **un étage par secteur de teinte**, tous deux en 12 bits dans le matériel, à pleine vitesse. Le décalage des bleus vers le cyan de Classic Chrome (−14 à −17° autour de 245–265°, README) et ses désaturations par famille de teintes (magentas × 0,66–0,72, verts × 0,73–0,75, cyans × 0,89–0,96) sont précisément ce qu'un étage à 16 secteurs sait faire. Gain en ΔE2000 : **non chiffré** tant que le sens de l'étage (bornes des secteurs, interpolation entre secteurs) n'est pas mesuré (§7).

---

## 2. Ce que la communauté a fait

### 2.1 Nikon Hacker et Nikon Patch (Simeon Pilgrim, coldtobi, Vicne…)

- **Modèles couverts** : D3100 et suivants (D5100, D7000, D3200, D5200, D7100, D3300, D5300, D5500, D600–D810, D4, D5, D500, D750…), plus D300 et D300s (seulement le « star eater »). **Rien pour le D40, D40x, D60, D80, D3000.** [lu] `nft/Nikon-Patch/LocalUI/*.cs` ; `nft/wiki/cameras/camera_matrix.csv:13` (ligne du D40 : aucune puce renseignée, seulement « wiring diagram » et le module AF CAM530).
- **Catalogue des patchs** (47 intitulés, comptés dans les `.cs`) : débits et durées vidéo, HDMI propre, mise en veille de la visée écran, batterie non Nikon, « Disable Nikon Star Eater », « True Dark Current », **« NEF Compression Off / Lossless »**, **« Jpeg Compression - Quality (vs. Space) »** (une seule instruction, `D5100.cs:107`), langues. **Aucun patch ne touche aux matrices, courbes ou au rendu couleur.** [lu]
- **Code ajouté** : oui, dans l'espace libre (`0xFF`) du firmware.
  - NEF sans perte du D5100 : `ldi:32 #0x37AF1E, r12 ; jmp @r12` à la place de deux instructions, puis un bout de code dans l'espace libre qui refait le travail écrasé et revient (`D5100.cs:43-63`). Retiré ensuite pour le D5100 parce qu'il ne marchait pas correctement (version 1.8, d'après le [blog de Simeon Pilgrim](https://simeonpilgrim.com/blog/2012/11/22/nikon-patch-1-7/), lu via un résumé de recherche).
  - « True Dark Current - Menu based » : **réaffecte l'entrée de menu Espace couleur** (libellés « Sensor RAW Enable! » en place de « Adobe RGB ») et ajoute 44 octets de code dans une zone `0xFF` (`0x20C450`) (`D5100.cs:226-251`). C'est le modèle de ce qu'on veut faire avec « Optimiser l'image ».
- **Outils** : désassembleur Dfr, émulateur Java (cœur FR complet, câblé pour D5100/D7000), correctifs GNU binutils et gcc 3.4.5 pour FR80 (`nft/GNU Patches/`), méthode « écrire en assembleur, assembler, réinsérer, redésassembler, comparer » ([wiki Firmware Development](https://nikonhacker.com/wiki/Firmware_Development), Wayback 09/03/2022).
- **Pixels traités sur le CPU** : aucun exemple trouvé. Le seul calcul d'image côté CPU vu dans le D40 est le flottant logiciel des matrices (une fois par photo, pas par pixel). [lu / source : rien trouvé]
- **Pourquoi personne n'a fait le D40** : la FAQ dit qu'ils restent sur le modèle où ils ont le plus de connaissances, et que « injecter du nouveau code n'est pas facile » ([Patching FAQ](https://nikonhacker.com/wiki/Patching_FAQ), Wayback 23/03/2023).

### 2.2 Magic Lantern (Canon DIGIC) et CHDK

D'après la présentation de Michael Zöller au 30C3 (28/12/2013, [PDF](https://fahrplan.events.ccc.de/congress/2013/Fahrplan/system/attachments/2246/original/Magic_Lantern_30C3.pdf)) :
- ML « tourne en RAM seulement, pas besoin de flasher quoi que ce soit » ; il s'accroche au démarrage du firmware Canon, réduit ses réserves de mémoire, s'insère dans ses tâches, lance les siennes et dessine son propre menu (diapo 8.1).
- Deux façons de l'exécuter : un faux fichier de mise à jour `.fir` dont le chargeur est remplacé par ML, ou un drapeau « BOOTDISK » en flash qui fait charger `AUTOEXEC.BIN` par le chargeur de démarrage, **sans vérification** (diapos 8.2 et 8.3). Le drapeau est la seule écriture en flash ([wiki ML](https://wiki.magiclantern.fm/my_own_sandbox)).
- Matériel DIGIC 4/5 : ARM946E à 200 MHz, 8 Ko de cache, moteurs dédiés (JPEG/H.264, EDMAC) (diapo 7.1). Le RAW vidéo est la combinaison « histogrammes RAW + DMA + écriture carte », pas du calcul par pixel sur le CPU ; tout le développement se fait ensuite sur ordinateur (diapo 6.3).
- CHDK (compacts Canon) a inspiré la méthode de démarrage de ML (diapo 4.2).

Leçons pour un Nikon de 2006 :
1. **Le D40 n'a ni drapeau de démarrage ni chargement depuis la carte connus.** Sa mise à jour charge le fichier en `0x81000000`, vérifie taille, signature et CRC, puis appelle le flasheur **du firmware en place** : le fichier n'exécute rien (CARTE §3). Pas de méthode « .fir » possible avec le firmware d'origine. Nikon : « contrairement aux Canon, on ne peut pas lancer de modifications depuis la carte SD » ([Thom Hogan, dslrbodies](https://dslrbodies.com/cameras/nikon-and-dslr-camera-faq/has-the-nikon-firmware-been.html)). [lu + source]
2. **Mais on peut fabriquer l'équivalent** : un petit chargeur, flashé une fois, qui lit un fichier de la carte en RAM et l'exécute, **déclenché par une action dans un menu, jamais au démarrage**. Le firmware sait déjà lire un fichier en `0x81000000` (`0x6C2E2`, appelé par la mise à jour). On itère ensuite sur le code sans reflasher. [déduit]
3. **Se servir des moteurs, pas du CPU** : ML, avec un ARM à 200 MHz et du cache, ne fait pas de rendu couleur par pixel ; le D40 a un CPU plus lent, sans DSP. [source + déduit]

---

## 3. Traitement logiciel sur le CPU après la puce

### 3.1 Est-ce possible ?

Oui [lu] :
- tâche 8 : le moteur écrit l'image en YCbCr 4:2:2 planaire en mémoire (`0x4B260`) ;
- tâche 9 (`tsk09_prio07`, `0x47D10`) : appelle l'étape d'encodage par une **table de pointeurs** `0xC6220` (8 entrées : `0x48B3E`, `0x48CAC`×3, `0x4883A`, `0x48CAC`×3), indice = octet `+0x41 & 7` de la fiche de prise de vue ;
- l'étape `0x4883A` encode l'image pleine (même `base + 0x2F90 / 0x5CF590 / 0x8B5890`), puis l'aperçu 576×376 et la vignette 160×120 à partir d'un autre tampon.

Remplacer un pointeur de `0xC6220` par une fonction qui traite les plans puis saute à la fonction d'origine est un **patch de données** (4 octets) plus du code dans l'espace libre. À noter : l'aperçu et la vignette viennent d'un autre tampon, il faudrait les traiter aussi (petits : 0,2 Mpx).

### 3.2 Combien de temps ? [estimé]

Hypothèses : CPU entre 66 et 133 MHz (§1.1) ; une instruction simple par cycle ; `MUL` 5 cycles, `MULH` 3 cycles (`nft/Java/Emulator/src/main/com/nikonhacker/disassembly/fr/FrInstructionSet.java:1582` et `:1714`) ; pas de cache de données (inconnu, cas défavorable) ; calcul entier seulement.

| Traitement | Unités à traiter | Cycles par unité | Total | Durée par photo L |
|---|---|---|---|---|
| Table 2D (Cb, Cr) 33×33, bilinéaire, table en mémoire interne (2,2 Ko) | 3,0 M paires Cb/Cr | 50–80 | 150–240 M | **1,1 à 3,6 s** |
| Table 3D (Ȳ, Cb, Cr) 9×17×17, tétraédrique, à la résolution de la chroma | 3,0 M paires | 120–180 | 360–540 M | **2,7 à 8 s** |
| Vraie LUT 3D RGB 17³ ou 33³, tétraédrique, pleine résolution (YCbCr → RGB → LUT → YCbCr) | 6,0 M pixels | 250–400 | 1,5–2,4 G | **11 à 36 s** |

Lecture : une table de chroma (correction de teinte et saturation, comme l'étage à 16 secteurs mais plus fine) tient en quelques secondes ; une LUT 3D complète transforme chaque photo en une attente de l'ordre de la demi-minute. Le JPEG part sur la carte après ce délai ; la rafale (2,5 im/s) et la vidange du tampon s'allongent d'autant. À mesurer sur le boîtier (temps entre deux écritures carte), ou en comptant les cycles dans l'émulateur Java de nikon-firmware-tools, qui les compte déjà (`FrEmulator.java:70-104`).

### 3.3 Faut-il le faire ?

Pas en premier. Le matériel couvre matrice, courbes par canal, saturation et teinte globales, et saturation-teinte par secteur, en 12 bits et sans temps perdu. La passe CPU ne se justifie que si, une fois l'étage 16 secteurs mesuré, le ΔE2000 restant d'un préréglage (par exemple sa dépendance à la luminosité) vaut quelques secondes par photo. Une variante sans attente au déclenchement : une commande « Développer en <préréglage> » dans le menu Retouche, appliquée après coup.

---

## 4. Ajouter des tables et du code

### 4.1 Où mettre les données

- 164 Ko à `0x3E7000`, 16 Ko à `0xEB000`, 8 Ko à `0x15E000` (CARTE §3) ; ~470 Ko de plus en retirant 13 langues sur 15.
- Taille d'un préréglage [estimé] : 6 matrices caméra (une par type de lumière, comme Nikon) 108 o ; 3 courbes au format compressé de Nikon (`courbe_decoder`, 2 047 o chacune) 6 Ko ; matrice YCbCr 18 o ; secteurs 128 o ; netteté et divers < 100 o. **~6,5 Ko par préréglage**, soit plus de 20 préréglages dans les 164 Ko.
- Tampons RAM pour décoder les courbes : la courbe est déjà décodée dans `0x83EB586C` (8 Ko) ; il en faut deux de plus (16 Ko de SDRAM libre, à trouver, §8).

### 4.2 Comment faire pointer chaque préréglage vers ses tables

Trois voies, de la moins à la plus intrusive :

1. **Données seules, dans les tables de Nikon** (déjà fait pour HNCS et Classic Chrome, `patchs/`) : remplacer les matrices 0–5 et courbes 0–6 du mode Ia, plus, nouveau, les 6 jeux de secteurs correspondants (`0x331E0E + 128 × 0…5`). Limite : un seul préréglage couleur par mode couleur (Ia libre, II si on accepte l'AdobeRGB), une seule courbe par cran de contraste, pas de courbes par canal.
2. **Un seul crochet dans `0x4B41C`** (recommandé, §5) : à la fin du chargement des tables, si le préréglage choisi n'est pas « Normal », réécrire les registres `0x40010022`, `0x40010034`, `0x40018400`/`0x4001A400`/`0x4001C400`, `0x4001E400`–`0x4001E47F` (et éventuellement `0x4001E800`…) depuis la fiche du préréglage. Technique de Nikon Hacker : remplacer deux instructions par `ldi:32 #crochet, r12 ; jmp @r12` (`D5100.cs:43-63`), le crochet refait ce qui a été écrasé.
3. **Réécrire les fonctions de choix** (`couleur_chargerMatrice`, `tonalite_construire`, `modesScene_reglages`) pour lire une table de préréglages : plus de code modifié, aucun avantage sur la voie 2.

### 4.3 Le menu

- « Optimiser l'image » range sa valeur dans le quartet haut de `0x83CE957F` (0 à 6, CARTE §5 bis) : **4 bits, donc 16 valeurs possibles**. Les valeurs 7 à 15 sont libres si ni le B ni le A ne les refusent (le bloc part au A par la commande 0x07, qui le garde sans doute en EEPROM). Hypothèse à tester.
- Libellés : tables D de chaque langue (`chaines.py`), en reconstruisant la table d'une langue dans l'espace libre pour des textes plus longs (CARTE §5).
- Nouvelles entrées : réutiliser des entrées existantes (modèle « True Dark Current ») ou copier le menu en RAM (patch de code, CARTE §5 bis).

---

## 5. Architecture recommandée

```
NEF (inchangé) ─┐
                │ tâche 8, à chaque photo
RAW ──► moteur 0x4001xxxx : linéarisation ─► matrice caméra (9) ─► 3 courbes R,G,B (3×4096)
                ─► matrice YCbCr + saturation (9) ─► 16 secteurs (4×16) ─► netteté / bruit
                ─► Y, Cb, Cr en SDRAM (12,2 Mo)
                         │ tâche 9
                         └─► [option : passe CPU, crochet table 0xC6220] ─► encodeur JPEG 0x40030000 ─► carte
```

- **Préréglage = une fiche dans l'espace libre** : identifiant de libellé, drapeau N&B, 6 matrices caméra (ou 1), 3 courbes compressées, 1 matrice YCbCr, 64 valeurs de secteurs, réglages de netteté. Les courbes, matrices et secteurs sont **calculés hors du boîtier** par le simulateur, en minimisant le ΔE2000 contre la cible (HNCS, LUT Fujifilm, mesures).
- **Crochet H1 (unique, obligatoire)** dans `0x4B41C`, chemin de prise de vue seulement. « Normal » ne l'emprunte pas : rendu Nikon intact, et témoin permanent.
- **N&B (HP5, Tri-X)** : chemin N&B de Nikon (`d1c = 1`), matrice `tblMatrices3` remplacée par un mélange de canaux tiré des sensibilités spectrales du D40 (`matrices_spectrales.py`) et de celles du film, courbe du film ; un virage léger est possible avec les 3 courbes par canal.
- **Valeur du menu** : 0 = Normal Nikon, 1 à 6 et éventuellement 7 à 15 = préréglages.
- **Crochet H2 (optionnel)** dans la table `0xC6220` pour une passe CPU de chroma, seulement si §3 la justifie.
- **Chargeur H0 (optionnel, plus tard)** : charge `D40EXT.BIN` depuis la carte sur une action de menu, pour mettre au point le code sans reflasher.
- **Intouchables** : le reset et tout le démarrage, la mise à jour (`maj_*`, flasheur `0x15CBE2`), le chemin de menu jusqu'à « Version du firmware », la tâche 4 qui écrit les réglages en flash, le firmware A.

Ce qui en sort : le JPEG et l'aperçu intégré au NEF (même moteur) prennent le rendu ; les données RAW du NEF ne changent pas. Les métadonnées « Optimiser l'image » du NEF portent la valeur du menu ; Capture NX ne connaîtra pas les préréglages (sans objet pour Lightroom).

---

## 6. Sécurité du flash

### 6.1 Ce qui peut arriver

- **Patch de données raté** (courbe, matrice, texte) : rendu faux, le boîtier démarre, on reflashe l'original par le menu (README, « Flasher »). Risque faible. [déduit]
- **Patch de code qui plante au démarrage** : boîtier mort. C'est ce qui est arrivé au D5100 de Simeon Pilgrim : « ne démarre plus, la LED ne clignote même plus », cause « une séquence d'instructions assembleur incorrecte » (instruction de type B avant une de type C dans un créneau de retard), réparation Nikon = carte mère à 50 % du prix du boîtier, récupération par JTAG envisagée et jamais rapportée ; et un D3100 de l'équipe ([Bricked My Camera](https://simeonpilgrim.com/blog/2013/05/23/bricked-my-camera/) ; [Patching FAQ](https://nikonhacker.com/wiki/Patching_FAQ) : « The original camera is being used to learn how to recover dead gear, but presently is still dead »). [source]
- **Coupure pendant le flash** : la FAQ interdit les batteries non Nikon et l'alimentation secteur pendant une mise à jour. [source]
- **Nikon ne débloque pas un boîtier dont il voit le firmware modifié.** [source] [dslrbodies](https://dslrbodies.com/cameras/nikon-and-dslr-camera-faq/has-the-nikon-firmware-been.html)
- **Mode de récupération du D40** : rien de documenté. Sur le D5100, la ROM de démarrage interne a une fonction de récupération en cas de mise à jour ratée [source, wiki] ; elle n'a pas sauvé le D5100 de Simeon, dont le firmware était valide mais plantait [déduit : elle doit ne réagir qu'à un firmware invalide]. Un « Menu maintenu à l'allumage, sans carte » circule pour les D3000 ([iFixit](https://ru.ifixit.com/Answers/View/873412/I+accidentally+flashed+a+Nikon+D300+firmware+to+an+D3000+Camera)), sans aucune confirmation : à ne pas compter dessus.

### 6.2 Règles qui en découlent

1. **Aucun code au démarrage.** Tout crochet est dans un chemin déclenché par l'utilisateur (prise de vue, action de menu). S'il plante, le boîtier démarre quand même, les menus marchent, on reflashe l'original.
2. **Ne jamais toucher** au démarrage, à la mise à jour, au chemin de menu de la mise à jour, à la tâche 4, au firmware A.
3. **Crochet testé hors boîtier** : assemblé avec les binutils FR (correctifs de `nft/GNU Patches/`), relu dans Ghidra et Dfr, **exécuté dans le cœur FR de l'émulateur Java** sur une fiche de prise de vue fabriquée (le cœur vérifie les créneaux de retard et compte les cycles ; étape 3 de `emulation-faisabilite.md`).
4. **Contrôle des créneaux de retard** : `patch.py` doit refuser une instruction interdite dans le créneau d'un `jmp:d`/`call:d`/`ret:d` (la cause du D5100 mort). À ajouter avant tout patch de code.
5. Batterie EN-EL9 Nikon pleine, jamais d'alimentation secteur ; le firmware d'origine prêt sur une seconde carte.
6. Patch de code : sur un D40 d'occasion qu'on accepte de perdre (prix non vérifié ici).

---

## 7. Ordre des étapes, du moins risqué au plus risqué

| # | Étape | Flash ? | Risque | But |
|---|---|---|---|---|
| 0 | Étendre le simulateur : 3 courbes par canal, étage 16 secteurs (deux lectures possibles), puis optimiser HNCS, Classic Chrome, Positive Film avec ces étages | non | nul | Chiffrer le gain en ΔE2000 de chaque étage avant de flasher |
| 1 | Flasher `pipboy-menus.json` (texte seul), revenir à l'original | oui | faible | Valider la chaîne de flash et le retour |
| 2 | **Sonde secteurs** (données seules) : dans les 6 jeux du mode Ia (`0x331E0E`), un secteur sur deux à gain nul ; photographier une roue de teintes en Ia et en IIIa (témoin) | oui | faible | Confirmer l'étage, mesurer les bornes des 16 secteurs, l'interpolation, l'ordre des 4 tables |
| 3 | Premier préréglage en données seules : matrices + courbes + secteurs de Classic Chrome dans le mode Ia | oui | faible | Mesurer le ΔE2000 réel contre le simulateur |
| 4 | Crochet H1 dans `0x4B41C` (code, chemin de prise de vue), d'abord avec un seul effet visible (courbe bleue différente) ; testé dans l'émulateur | oui | moyen | Courbes par canal, puis fiches de préréglage |
| 5 | Menu : libellés, valeurs 0–6, puis tester 7–15 | oui | moyen | Le menu « Préréglage couleur » |
| 6 | Passe CPU H2 (table de chroma) si l'étape 0/3 montre un résidu qui le vaut ; mesure du temps par photo | oui | moyen | ΔE résiduel |
| 7 | Chargeur H0 (code depuis la carte sur action de menu) | oui | moyen à élevé | Itérer sans reflasher |

---

## 8. Points ouverts

1. **Sens exact de l'étage à 16 secteurs** : matrice 2×2 ou gain + décalage, comment le secteur est calculé (angle de Cb/Cr ?), interpolation entre secteurs, avant ou après la matrice YCbCr. Étape 2. Raccourci sans risque : **comparer avec le firmware du D80** (même puce EI-137 selon Wikipedia), où Nikon a peut-être rempli ces tables. Téléchargement chez Nikon ([page D80 v1.11](https://downloadcenter.nikonimglib.com/en/download/fw/8.html), `F-D80-V111W.exe`, ~1,13 Mo) **non fait : à demander à Thomas**.
2. **Les trois tables 4 096 sont-elles bien R, G, B**, dans cet ordre, et la courbe est-elle avant la matrice YCbCr ? Étape 4.
3. **Fréquence du CPU** et présence d'un cache de données : à mesurer (boucle chronométrée dans le crochet, ou durée du tic noyau).
4. **SDRAM libre** pour deux tables de 8 Ko et, plus tard, le code chargé depuis la carte : cartographier l'occupation de `0x80000000`–`0x83FFFFFF` (le tampon `0x81000000` de la mise à jour sert-il aussi aux images ?).
5. **Valeurs 7 à 15 d'« Optimiser l'image »** acceptées par le A et par le B ?
6. Rôle de la table de 1 024 valeurs (`0x4001EC00`) et des registres `0x40010006`–`0x40010020` et `0x40010046`–`0x40010056`.
7. **La ROM de démarrage du D40** : existe-t-elle à `0xF0000`–`0xFFFFF`, a-t-elle un mode de récupération, comment le déclencher ? Aucune source.
8. Le JTAG ou le mode débogueur des FR (Fujitsu DSU) comme filet de récupération : aucune réussite publiée sur un Nikon.
9. La chaîne d'outils : version des binutils FR à compiler (correctifs pour 2.22 et 2.24.51 dans `nft/GNU Patches/`) ; un compilateur C récent pour FR n'est pas vérifié ici.
10. Le capteur (ICX413 ?) et la puce exacte : aucune photo de carte mère du D40 trouvée ; le manuel de réparation existe (« wiring diagram » dans `camera_matrix.csv:13`) mais n'a pas été lu.

---

## Sources

- Firmware B v1.11 du D40, décompilé (`d40-tout.c`, régénérable) : fonctions `0x4B260`, `0x4B41C`, `0x4BE82`, `0x320CD8`, `0x3234BE`, `0x322606`, `0x3209DE`, `0x3229CA`, `0x324020`–`0x324124`, `0x47D10`, `0x4883A`, `0x49A7C`, `0x4A164`, `0x65E0C`, `0x66510`, `0xC0F90`, `0xC1314` ; données `0x331E0E`, `0x332888`, `0x33270E`, `0x331AF0`, `0xC6220`, `0xC62D0`, `0xD056C`, `0xD06F8`.
- `CARTE.md` §2, §3, §5, §5 bis, §7, §10 ; `README.md` (Classic Chrome décortiqué, HNCS) ; `recherche/emulation-faisabilite.md`.
- nikon-firmware-tools : `Nikon-Patch/LocalUI/D5100.cs:43-63, 107, 226-251, 271, 277`, `D300.cs`, `D3100.cs` ; `wiki/cameras/camera_matrix.csv:13` ; `Java/Emulator/.../disassembly/fr/FrInstructionSet.java:23-30, 1582, 1714` ; `Java/Emulator/.../emu/FrEmulator.java:70-104` ; `GNU Patches/`.
- Wiki nikonhacker.com (Wayback Machine) : [Understanding Firmware](https://nikonhacker.com/wiki/Understanding_Firmware) (23/03/2023), [Patching FAQ](https://nikonhacker.com/wiki/Patching_FAQ) (23/03/2023), [Firmware Development](https://nikonhacker.com/wiki/Firmware_Development) (09/03/2022), [Patch limitations](https://nikonhacker.com/wiki/Patch_limitations) (23/03/2023). La page « D40 » du wiki est vide.
- [Simeon Pilgrim, Bricked My Camera](https://simeonpilgrim.com/blog/2013/05/23/bricked-my-camera/) (23/05/2013).
- [Wikipedia, Expeed](https://en.wikipedia.org/wiki/Expeed) ; [Wikipedia, Milbeaut](https://en.wikipedia.org/wiki/Milbeaut) ; [Fujitsu, Milbeaut M-4, 12/07/2006](https://info.archives.global.fujitsu/global/about/resources/news/press-releases/2006/0712-01.html).
- [Magic Lantern, 30C3, 28/12/2013](https://fahrplan.events.ccc.de/congress/2013/Fahrplan/system/attachments/2246/original/Magic_Lantern_30C3.pdf) ; [wiki Magic Lantern](https://wiki.magiclantern.fm/my_own_sandbox).
- [Thom Hogan, Has the Nikon firmware been hacked yet?](https://dslrbodies.com/cameras/nikon-and-dslr-camera-faq/has-the-nikon-firmware-been.html).
- [iFixit, D300 firmware flashed onto a D3000](https://ru.ifixit.com/Answers/View/873412/I+accidentally+flashed+a+Nikon+D300+firmware+to+an+D3000+Camera).
