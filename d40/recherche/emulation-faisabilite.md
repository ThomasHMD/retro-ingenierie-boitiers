# Faire tourner le firmware B du D40 en local : étude de faisabilité

Étude d’octobre 2026. Rien n'a été installé ni modifié hors de ce fichier. Légende : **[lu]** = lu dans le code ou les données de cette machine, **[web]** = vérifié sur GitHub aujourd'hui, **[supposé]** = raisonnement non testé. Aucune durée en heures : les coûts sont en « paliers » (S, M, L, XL) et en nombre de fichiers ou de lignes à écrire.

Sources locales : `CARTE.md` et `README.md` de ce dossier ; clone de nikon-firmware-tools dans `<dossier de travail>/nft/` (désigné `nft/` plus bas), dossier `nft/Java/Emulator/src/main/com/nikonhacker/` (désigné `nh/`).

## Résumé en dix lignes

1. L'émulateur de nikon-firmware-tools contient un **vrai cœur FR complet** (jeu d'instructions, délais de branchement, interruptions, minuteries, liaison série, ports). Son adresse de reset par défaut est **0x40000, la même que le D40** [lu : `nh/disassembly/fr/FrCPUState.java:14`].
2. Mais l'assemblage « boîtier » est **câblé en dur pour le D5100/D7000** : un FR (Expeed 2) relié à un Toshiba TX19A (TMP19A), capteur IMX071, ST95040, face avant du D5100 [lu : `nh/emu/EmulationFramework.java`]. Aucun fichier de config, aucun code pour le D40 (ni pour le D80/D90, malgré `conf/BD800111.dfr.txt` qui ne sert qu'au désassembleur).
3. Le D40 a **deux FR** (B et A), pas FR + TX. L'émulateur ne sait relier que FR + TX ; le A du D40 est un FR : il faut soit un « faux A » scripté, soit un second cœur FR (modification structurelle).
4. **Démarrage complet du B (jusqu'à l'écran de menu) : faisable mais long et incertain** (palier XL). Le risque principal : les boucles d'attente sur des registres matériels que personne n'a documentés pour le D40.
5. **L'option la plus rentable : exécuter seulement les fonctions de dessin** (texte, icônes, blocs) dans le cœur FR de l'émulateur Java, en lui donnant la RAM initialisée à la main, pour produire un PNG de menu (palier M). Les fonctions de dessin sont des routines pures sur la mémoire, sans appel noyau.
6. Variante encore moins chère et la plus robuste pour **tes besoins réels** (palette, polices, textes, icônes) : réimplémenter le rendu en Python à partir des données (palier S à M). C'est le meilleur rapport coût/fiabilité, et elle sert aussi de contrôle croisé de l'option 5.
7. Unicorn, QEMU, MAME : **aucun ne gère le FR** [web]. Ghidra (EmulatorHelper) peut exécuter des fonctions isolées avec le module fr60, mais avec moins de garanties que le cœur de l'émulateur Java.
8. Pour le **rendu image**, un simulateur Python du pipeline (matrices, courbes, YCbCr, JPEG) appliqué à un NEF est **plus pertinent que l'émulation** : tout ce dont il a besoin est déjà extrait (courbes décodées, matrices, tables). L'émulation du moteur d'image matériel est hors de portée.
9. À installer, si on suit la recommandation : `rawpy` (via pip) pour lire les NEF, éventuellement rien d'autre (Pillow et numpy sont déjà là ; `outils/raw_lineaire.swift` lit déjà les RAW avec CoreImage, sans installation).
10. Ordre recommandé : (1) rendu Python des menus, (2) simulateur de rendu image validé sur paires NEF+JPEG, (3) exécution des fonctions de dessin dans le cœur FR, (4) seulement si ces trois ne suffisent pas, démarrage complet.

## 1. L'émulateur de nikon-firmware-tools

### Ce que c'est

- Dossier `nft/Java/Emulator/` : application Swing (396 fichiers Java), construite par Ant (`build.xml`), « Java 1.7 » d'après `Readme.txt`, bibliothèques dans `lib/` (xstream 1.4.2, jgraphx, miglayout, rsyntaxtextarea…) [lu]. Lancement par `batch/startEmulator.sh`. Il devrait se compiler comme Dfr l'a été (JDK 17 + `javac` direct), mais ce n'est pas testé [supposé].
- Le `Readme.txt` renvoie à `nikonhacker.com/wiki/NikonEmulator` pour le mode d'emploi. **La page est introuvable aujourd'hui** (404 depuis `WebFetch`) : je n'ai donc pas pu lire la doc ni le forum. Tout ce qui suit vient du code. Le `README.md` racine du dépôt dit seulement « outils utilisés pour la rétro-ingénierie des Nikon D5100, D7000 » [lu].
- Le dossier `nft/wiki/cameras/camera_matrix.csv` donne les processeurs connus : D90 = MB91F637 (FR), D7000 et D5100 = TMP19A44 (TX) + ASIC « EL-154 » ; **la case du D40 est vide** (D40 : 2006, CCD 3008×2000, sans données de processeur) [lu].

### Quels boîtiers

- Pris en charge de bout en bout : **D5100 et D7000**, deux puces : `Constants.CHIP_FR = 0` (Expeed, le B) et `CHIP_TX = 1` (le TMP19A qui gère touches, mécanique, viseur) [lu : `nh/Constants.java`, `EmulationFramework.java`]. `Constants` mentionne aussi `CHIP_ARM = 2` (désassemblage seulement).
- Preuve du câblage D5100 dans `EmulationFramework.java` :
  - FR : `Imx071` (capteur) relié à la liaison CSIO1, `Ei155` (pont capteur) à la CSIO0 ;
  - TX : EEPROM `St95040`, pilote de LCD de viseur, chargeur de flash `Nhhs2`, monture F, `D5100FrontPanel` (touches câblées sur les broches PG0-PG4, PA0-PA3…, avec les références de billes du boîtier D5100 en commentaire), miroir ;
  - `data/D5100-eeprom.bin` et `D3100-eeprom.bin` sont des vidages d'EEPROM fournis.
- Le code dit lui-même « this is D5100 specific. Make it generic » (TODO, ligne 527) [lu].

### Jusqu'où : écran, menus, boutons

- **Écran** : `FrLcd` convertit en RGB un tampon YCbCr de la mémoire du FR, avec **des adresses D5100 écrites en dur** : Y à `0xCE57DC60`, Cb à +0x64000, Cr à +2×0x64000, 640×480, format 4:2:2 [lu : `nh/emu/peripherials/lcd/fr/FrLcd.java`]. La fenêtre `ScreenEmulatorFrame` reçoit pourtant les adresses Y/Cb/Cr, la largeur et la hauteur en paramètres et les montre dans des champs modifiables [lu]. Pour le D40 il suffit donc de pointer sur le tampon (lu à `0x83CE0230`, CARTE §9), **mais** la conversion suppose du 4:2:2 : le D40 est en 4:2:0 (chroma 320×240 à +0x4B000 et +0x5DC00). Correction : une dizaine de lignes dans `updateImage` (répéter chaque ligne de chroma pour deux lignes de luminance).
- **Boutons** : seul `D5100FrontPanel` existe (côté TX). Pour le D40, les touches sont lues par le A ou le B (non établi ; le B a des ports `0x50000104`…) : il faudrait un panneau D40 (une classe, mais il faut d'abord savoir quelles broches) [supposé].
- **Menus** : rien n'indique que l'équipe ait fait tourner un menu complet ; le projet sert surtout à tracer l'exécution, inspecter les tâches ITRON (`nh/itron/fr/`) et les périphériques. Je n'ai pas trouvé de capture ni de doc affirmant l'inverse [non vérifié, faute de wiki].

### Processeur A et liaison série

- Pour les deux puces : `interconnectChipSerialPorts` relie les séries du FR à celles du TX, `interconnectChipIoPorts` relie des ports, `connectLcdScreenRelatedPins` et `connectFrontPanelPins` des broches [lu : `EmulationFramework.java` ~l. 450-470]. Cet « autre processeur » est un **TX19A émulé** (`TxEmulator`).
- Sur le D40, la liaison B↔A est le port série 0 du FR en mode synchrone, avec poignée de main sur `0x50000104` bit 6 et `0x50000106` (CARTE §10 bis) ; l'autre bout est un **FR** (firmware A, chargé à `0xC0000`). L'émulateur code en dur `platform[CHIP_FR]` et `platform[CHIP_TX]` : lui faire accepter deux FR est une refonte du tableau de plates-formes (`emulator[chip]`, `isImageLoaded[chip]`, préférences par puce), pas un réglage.
- Option réaliste : **ne pas émuler le A**, brancher à la place du TX un `SerialDevice` Java (modèle : `DummySerialDevice`, `SpiSlaveDevice`, `Ei155`) qui répond aux 48 commandes de `tblCommandesA` (0xE482C) avec des réglages plausibles (mode molette via la commande 0x14, réglages via 0x08…) [supposé]. Le format exact des octets sur le fil n'est pas encore décodé (CARTE §10 bis dit « à lire en assembleur ») : c'est un prérequis.

### Périphériques déjà modélisés, utilisables ou non pour le D40

Blocs d'adresses écoutés par l'émulateur FR [lu : `nh/emu/memory/listener/fr/`] et leur correspondance avec ce que CARTE.md a vu dans le B du D40 :

| Émulateur (D5100) | Contenu | Vu dans le B du D40 (CARTE §2) |
|---|---|---|
| `0x4002xxxx`, `0x400Fxxxx` (Expeed4002) | convertisseur de résolution | `0x40020000` : moteur de redimensionnement (matrice 3×4, tables 8 bits) |
| `0x4003xxxx` (40X3) | codec JPEG | `0x40030000` (rôle non établi) ; JPEG matériel appelé par `0x49A7C` |
| `0x4006xxxx` (Expeed4006) | à vérifier | `0x40060000` : histogramme 256 cases |
| `0x4018xxxx` | à vérifier | non vu |
| `0x5000xxxx` | ports d'E/S | `0x50000000` : ports |
| `0x6300xxxx`/`0x6400xxxx` | contrôleurs SD | non vu |
| `0x6B00xxxx` | circuit d'interruptions partagé | non vu |
| `0x0000_00xx` (ExpeedIoListener) | minuteries 16/32 bits, séries 0x60…, ICR 0x440 | minuterie 2 et SMR0 à adresses du FR (`TMRLR2`, `SMR0`) : même famille |

La famille de registres est donc **proche** (même découpage 0x4002 / 0x4003 / 0x4006 / 0x5000), mais pas identique : le D40 utilise aussi `0x40010000` (tables de conversion), `0x40040000`, `0x40070000` (contrôleur mémoire), `0x400E0000` que l'émulateur ne connaît pas. Conséquence [supposé] : un registre non connu se comporte comme de la RAM simple. C'est suffisant pour les écritures, mais **toute boucle qui attend un bit d'état du matériel tourne à l'infini**.

### Ce qu'il faudrait pour un D40 (travail, par palier)

1. Une plate-forme « D40-B » dans `EmulationFramework` (ou une classe voisine) : FR seul, RAM aux adresses `0x68000000` (interne), `0x83000000`… (externe, ≥ 0x3E0000 octets), `0x81000000` (tampon) ; image chargée à `0x40000` (déjà le défaut) ; palier M.
2. Vecteur de reset à `0xEFC00` (table des 256 vecteurs, vecteur 0 → `0xC0F90`) : l'émulateur utilise `RESET_ADDRESS = 0x40000` comme PC initial et non le vecteur ; il faut fixer le PC et le registre de base de la table (TBR) pour que les interruptions retrouvent `0xEFC00` [supposé, à lire dans `FrCPUState`/`FrInterruptController`] ; palier S.
3. Contrôleur mémoire `0x40070000`, minuteries, série 0 : modèles de base existent ; il faudra **faire exécuter le reset jusqu'à `0xC1610` et noter chaque attente matérielle** en lisant les journaux de registres (l'émulateur sait les consigner) ; palier L, nombre de boucles inconnu.
4. Faux A (voir plus haut) ; palier L.
5. LCD : adapter `updateImage` en 4:2:0 et adresses par pointeur ; palier S.
6. Tout ce qui précède avant d'avoir l'**interface** : la tâche 16 (interface, 0x14D804) dépend du noyau REALOS qui, lui, est du code FR ordinaire (INT #0x40, gestionnaire `0xC1586`) : l'émulateur l'exécute tel quel s'il implémente `INT` ; pas d'émulation de syscalls haut niveau (l'émulateur lit les structures ITRON mais exécute le vrai noyau) [lu : `nh/itron/*` sont des vues, pas des remplaçants].
7. Moteur d'image (resize, JPEG, histogramme, tables 0x40010000) : `FrJpegCodec` (580 lignes) et `FrResolutionConverter` (323 lignes) ont été écrits pour le D5100 ; leur compatibilité avec le D40 est **inconnue**. Pour la lecture d'une photo (écran de visualisation), cela compte ; pour les menus, non.

Estimation globale d'un boot jusqu'à un menu affiché : **palier XL** (des dizaines d'itérations « lancer, trouver la boucle bloquée, modéliser le registre »). Aucune garantie d'y arriver, car les registres du D40 ne sont pas documentés ailleurs que dans ta propre carte. [supposé]

### Piège de maintenance

Le dépôt est vivant par le haut (dernier commit local : une mise à jour de dépendance du patcher JS, juillet 2026 [lu]) mais l'émulateur Java date d'avant 2015 environ (xstream 1.4.2, Java 1.7) [supposé d'après les bibliothèques]. Il compilera, mais sans mainteneur.

## 2. Autres options

| Outil | FR supporté ? | Verdict |
|---|---|---|
| **Unicorn** | Non. Architectures : ARM, ARM64, M68K, MIPS, PowerPC, RISC-V, SPARC, S390X, TriCore, x86 [web : README et `qemu/target` du dépôt unicorn-engine, 2026-10 : `arm i386 m68k mips ppc riscv s390x sparc tricore`] | Inutilisable sans écrire un cœur FR dans QEMU/TCG (palier XL) |
| **QEMU** | Non. `target/` : `alpha arm avr hexagon hppa i386 loongarch m68k microblaze mips or1k ppc riscv rx s390x sh4 sparc tricore xtensa` [web] | Idem |
| **MAME** | Un dossier `src/devices/cpu/fr` existe (Fujitsu FR, par AJR) mais le fichier dit « Currently this device is just a stub with no actual execution core » : **désassembleur seulement** [web : `fr.cpp`, `frdasm.cpp`] | Pas d'exécution |
| **GDB sim / binutils** | Le port `fr30` existe dans binutils pour le FR30 (assembleur/désassembleur ; Ghidra le nomme « fr30 » en nom externe) ; le dossier `sim/fr30` renvoie 404 sur GitHub [web] | Pas de simulateur utilisable |
| **Ghidra EmulatorHelper** | Oui, via le module `ghidra-fr60` déjà installé (`~/Library/ghidra/ghidra_12.2_PUBLIC/Extensions/ghidra-fr60`, jeu d'instructions FR60 en SLEIGH, 1 348 lignes dans `fr60.sinc`, `delayslot(1)` présent pour les branchements) [lu] | Utilisable pour des fonctions isolées (voir ci-dessous) |
| **Cœur FR de l'émulateur Java** | Oui, complet, avec tests (`nh/../test/.../FrEmulatorTest.java`) [lu] | Meilleur moteur d'exécution disponible |

### Ghidra EmulatorHelper en détail

- **Pour** : déjà installé (Ghidra 12.2, `brew`), projet D40 déjà analysé (`regen-complet/ghidra-proj`), symboles déjà posés ; on écrit un script (Java via `analyzeHeadless`, ou Python via PyGhidra) qui crée l'`EmulatorHelper`, écrit des registres et de la mémoire, fixe le PC, exécute jusqu'au retour, puis lit la mémoire [supposé, API standard de Ghidra].
- **Contre** :
  - le journal de régénération (`regen-complet/regenerer.log`) montre déjà des erreurs de p-code dans le noyau (`Unable to resolve constructor at 000c1d3e`, `Program does not contain referenced instruction: 000c262e`) : le module FR60 n'est pas parfait, les instructions rares ou le chevauchement d'instructions (avertissements « overlaps instruction » dans le pseudo-C) peuvent faire échouer [lu] ;
  - le coprocesseur est « complètement neutralisé » d'après le readme du module [lu] ;
  - `INT #0x40` n'a pas de sémantique utile : il faut intercepter chaque appel noyau ;
  - lenteur : p-code interprété instruction par instruction ; suffisant pour quelques milliers de fonctions de dessin, pas pour un boot.
- **Verdict** : bon pour tester **une** fonction (ex. `texte_afficherLignes`) en étape intermédiaire, moins fiable que le cœur Java pour une chaîne d'appels. Palier M.

## 3. L'approche « partielle » : dessiner un menu sans démarrer le boîtier

### Ce que dessinent les fonctions (lu dans `d40-tout.c`)

- `osd_tracerBloc` (`0x7BD56`) : calcule l'adresse de destination dans le tampon `*(0x83CE0230)` (ligne de `0x280` octets pour la luminance, chrominance à `+0x4B000` avec `(x>>1) + (y>>1)*0x140`), copie un bloc de bitmap 1 bit par pixel dans une zone de travail en RAM interne (`0x68000A55`) par `FUN_0004532a` (simple copie mémoire), puis `FUN_0007be46` écrit pixel par pixel Y, Cb, Cr là où le bit est à 1 (valeurs passées en paramètres 6, 7, 8). Aucun appel noyau. **Entièrement déterministe.**
- `icone_dessiner` (`0x7C904`) : parcourt la liste de tuiles de l'icône (`tblIcones`, 4 octets par tuile), cherche la planche dans les descripteurs à `0x83CE3FDC` (12 octets, largeur/hauteur/bits par pixel/données), prend la couleur dans la palette `0x83CE3FD8` (= `0x1B0000`) puis appelle `osd_tracerBloc` (ou `FUN_0007C044` pour l'agrandi ×2). Aucun appel noyau.
- `texte_parIdentifiant` (`0x7C1A0`) : choisit la table (bits 13-15 de l'identifiant → D, C, B ou A selon `0x83CE3FEC/3FF0/3FF4/3FF8`), puis `texte_afficherLignes`. Pas d'appel noyau dans ce qui a été lu (la suite du corps n'a pas été lue en entier : **à vérifier**).

### Option 3a : exécuter ces fonctions dans le cœur FR

Principe [supposé] :
1. Mémoire : charger `BD400111.bin` à `0x40000` ; copier à la main `0x1544C4–0x15D528` vers `0x83CDFFB0` (décalage constant `0x83B8BAEC`, CARTE §2) ; mettre à zéro le BSS (`0x83CE9018`–`0x83D02147`) ; allouer `0x68000000` (RAM interne, variables du dessin) et un tampon d'écran de 640×480 + 2×320×240 octets dont l'adresse est écrite dans `0x83CE0230`.
2. Appeler la routine voulue (PC, registres R4-R7 pour les paramètres, retour dans RP) et exécuter jusqu'au retour. Le cœur Java expose un `main` qui charge un binaire et fixe le PC (`FrEmulator.main`, qui est cependant incomplet : il crée l'émulateur sans lancer la boucle ; il faut un petit programme de test comme `FrEmulatorTest`).
3. Convertir le tampon en PNG (Y/Cb/Cr → RGB, comme `FrLcd.updateImage`).

Ce qui rend la chose fiable : on exécute **exactement** le code du boîtier sur ses vraies données (donc toute modification de palette, d'icône, de table de texte ou de police faite par `patch.py` y est prise en compte, y compris si le patch change le code).

Ce qui rend la chose coûteuse : pour dessiner un **écran de menu entier**, il faut soit appeler la fonction qui compose l'écran (`ecranNNN_entree`, le moteur de menu, qui lit les réglages et peut appeler le noyau), soit reproduire à la main la séquence « titre, lignes, icônes, curseur » à partir de `ecrans.tsv`/`menus.txt`. La première voie ramène aux appels noyau (sémaphores, drapeaux) à simuler ; la seconde revient à réécrire la mise en page, donc à faire de la 3b avec un moteur d'exécution en plus. [supposé]

Palier : M pour une fonction (texte ou icône) ; L pour un écran complet piloté par la vraie logique de menu.

### Option 3b : réimplémentation Python

Ce qui est **déjà établi** (CARTE §9, §5, §5 bis) et suffit pour un premier rendu :
- palette 104 × `00 Y Cb Cr` (`outils/palette.py` sait déjà la lire et convertir) ;
- tampon de sortie 640×480, 4:2:0 ;
- glyphes : planches de descripteurs à `0x1B01A0`, largeurs des caractères à `0x1B064C` (1 octet) et `0x1B05E4` (2 octets, `0x81 xx`) ;
- icônes : `tblIcones` `0x157904` (tuiles de 4 octets : position en quartets, indice de couleur, planche, glyphe) ;
- textes : `outils/chaines.py` donne déjà les chaînes par langue et par identifiant ;
- arbre des menus : `outils/menus.py` + `desassemblage/ecrans.tsv`, `menus.txt` (positions à l'écran dans l'en-tête de menu `+0x18`).

Ce qui **manque** (à décoder une fois, en lisant `texte_afficherLignes`, `0x7C440` et les fonctions d'écran) :
- le format exact d'une planche de glyphes (organisation des bits, hauteur, interligne) ;
- la mise en page : alignements, coupures de ligne, couleur du curseur et de la surbrillance, ombrage ;
- l'habillage de chaque écran (titres, barres, pictogrammes de molette) quand ils sont dessinés par du code et non par une table.

Fiabilité : très bonne **sur ce qui est dans les données** (palette, texte, icônes), moyenne sur la **disposition** (tant qu'on n'a pas comparé à une vraie photo d'écran du D40). Un écran de menu rendu doit être comparé à une capture réelle du boîtier (photo de l'écran) : c'est le seul vrai test, à prévoir avant de s'y fier.

Palier : S pour « palette + une icône + une chaîne » ; M pour un écran de liste de menu complet ; L pour tous les écrans, mais les écrans les plus utiles à tes modifications (Optimiser l'image, les 7 rendus, la liste des modes) sont des listes simples.

### Lequel choisir

| Critère | 3a (exécuter les fonctions) | 3b (réimplémenter en Python) |
|---|---|---|
| Fidélité aux modifications de code | exacte | nulle (suit les données seulement) |
| Fidélité à la mise en page | exacte pour les primitives ; à reconstruire pour l'écran | à déduire |
| Risque technique | gap p-code (Ghidra) ou compilation d'un émulateur Java ancien | faible |
| Réemploi | un bac à sable pour la suite (autres fonctions, boot) | scripts Python simples, relançables à chaque patch |
| Dépendances | JDK 17 (déjà là), compilation du clone | Pillow, numpy (déjà là) |
| Coût | M à L | S à M |

**Recommandation : commencer par 3b, puis 3a sur les primitives seulement**, pour s'en servir comme **test d'étalonnage** : le rendu Python doit donner les mêmes pixels que l'exécution des vraies fonctions (`osd_tracerBloc`, `icone_dessiner`). Si les deux concordent sur 20 ou 30 cas, 3b est validé sans photo de l'écran. [supposé]

## 4. Rendu image : simulateur Python plutôt qu'émulation

### Pourquoi c'est plus pertinent

Ce que tu veux prévisualiser (courbe de tonalité, mode couleur, saturation, teinte, netteté) dépend d'un pipeline déjà décrit dans CARTE §7 :
- matrices caméra → RGB : `0x332888`, `0x33270E`, `0x331B98`, 18 matrices choisies par mode couleur et lumière ;
- table de tonalité 4 096 entrées sur 12 bits, construite par `tonalite_construire` (`0x323C22`) à partir de 21 courbes + 7 courbes + la courbe perso, correction fine `0x33692E`, déjà décodées par `outils/courbes.py` (qui ré-encode à l'octet près) ;
- 21 matrices YCbCr (contraste et saturation liés) ;
- tables de quantification JPEG standard (`0xA23C4`, `0xA2404`).

Émuler ce pipeline reviendrait à émuler en plus **le matériel** (`0x40010000`, `0x40020000`, `0x40060000`, le codec JPEG), dont les registres ne sont documentés nulle part ; les périphériques de l'émulateur Java, écrits pour le D5100, ne correspondent pas [supposé]. Le simulateur Python n'a besoin que des **tables**, qui sont lues et vérifiées.

### Ce qui manque encore pour un simulateur exact [supposé]

- le moment où s'appliquent la balance des blancs et le gain (avant ou après la matrice ?) ;
- la netteté (`sharpening`, réglage 0-6) et la réduction de bruit : algorithmes matériels, **non lus** ; à approcher puis à caler sur des paires ;
- le dématriçage (matériel) : LibRaw en donne un équivalent, pas un identique ;
- l'entrée de la courbe : CARTE dit « très probablement linéaire 12 bits » (probable, pas prouvé) ;
- les 21 matrices YCbCr et l'ordre exact des opérations (matrice, courbe, YCbCr).

### Décodage du NEF

- **Ce qui est déjà là sans rien installer** : `outils/raw_lineaire.swift` (CoreImage `CIRAWFilter`, sortie TIFF 16 bits linéaire sRGB, réduction). Limite : le décodeur macOS applique **sa** balance des blancs et **sa** matrice ; la sortie n'est pas « capteur brut » mais « scène linéaire », ce qui perturbe un calage fin [supposé].
- **À installer, recommandé** : `rawpy` (`python3 -m pip install --break-system-packages rawpy`, paquet roue qui embarque LibRaw ; règle de ta mémoire : `--break-system-packages`). Il permet de récupérer **le tableau brut Bayer 12 bits**, les noirs, les coefficients de balance des blancs du NEF, et une sortie linéaire sans courbe (`gamma=(1,1)`, `no_auto_bright=True`, `output_color=raw`, `user_wb` explicite). LibRaw gère les NEF du D40 (12 bits, compressés) [supposé, la prise en charge du D40 par LibRaw est ancienne et standard ; à confirmer au premier fichier]. Pourquoi : c'est la seule voie pour appliquer **sa propre matrice** (celle du firmware) au lieu de celle de macOS.
- `dcraw` n'est pas nécessaire (pas installé ; rawpy fait mieux). `exiftool` est déjà là (`/opt/homebrew/bin/exiftool`) pour lire les réglages d'une prise (WB, Optimiser l'image, mode couleur, NEF compressé).
- Pillow et numpy sont déjà présents. Pas besoin de scipy pour une première version.

### Validation

1. Corpus : des **paires NEF + JPEG fin** enregistrées en RAW+JPEG au même instant sur ton D40 (le JPEG est le rendu du boîtier). Il en faut surtout pour : Optimiser l'image Normal / Plus doux / Vif / Très vif / Portrait / Noir et blanc, mode couleur Ia / II / IIIa, avec une scène à gris neutres (mire grise ou ColorChecker) pour séparer la courbe de la couleur.
2. Mesure : sur des cases de la mire, comparer la valeur du JPEG du boîtier à celle du simulateur, en espace Lab : ΔE2000 par case et sur l'image réduite (par exemple 1/8) pour s'affranchir de la netteté. Seuil cible à fixer avant de mesurer (par exemple moyenne < 2, maximum < 5) ; il se discute, ce n'est pas une norme.
3. Séparer les erreurs : (a) courbe seule sur les gris (ΔL), (b) matrice sur les couleurs, (c) saturation et teinte, (d) netteté en dernier, sur un bord incliné.
4. Contrôle d'indépendance : **valider sur des prises qui n'ont pas servi au calage** (une moitié pour caler, une moitié pour tester).
5. Contrôle interne déjà disponible : le recoupement des courbes (la courbe 17 décodée coïncide avec la courbe perso d'usine, CARTE §7) montre que la partie « courbe » est exacte ; tout écart restant vient de la matrice, du blanc, de la netteté ou du dématriçage.

Palier : M pour un premier simulateur sans netteté (matrice caméra + courbe + YCbCr + JPEG), L avec calage de la netteté et de la réduction du bruit.

Le même simulateur sert d'**aperçu des recettes** (`patchs/classic-chrome-groupe0.json`, courbes sorties de `courbes.py patch`) avant de flasher : c'est le gain principal pour ton but de départ.

## 5. Conclusion chiffrée

Notes de rentabilité : valeur = utilité pour prévisualiser tes modifications (1 à 5), coût en paliers, risque d'échec.

| Rang | Étape | Valeur | Coût | Risque | Ce qu'on obtient |
|---|---|---|---|---|---|
| 1 | **Simulateur de rendu image** en Python (rawpy + tables du firmware), validé sur 5 à 10 paires NEF+JPEG | 5 | M (L avec netteté) | Faible à moyen : netteté, dématriçage et ordre des opérations non lus | Aperçu fiable d'un rendu film avant flash, comparaison chiffrée avec le boîtier |
| 2 | **Rendu Python des menus** : palette, polices, textes, icônes, listes de menus | 4 | S pour un écran, M pour les listes | Faible sur les données ; moyen sur la disposition (à comparer à une photo de l'écran) | PNG de l'écran de menu pour palette, libellés, icônes, longueurs de chaînes (qui dépassent ou non) |
| 3 | **Étalonnage par exécution** des primitives (`osd_tracerBloc`, `icone_dessiner`, `texte_parIdentifiant`) dans le cœur FR Java (ou Ghidra EmulatorHelper en repli) | 3 | M | Moyen : initialisation de la RAM à la main, appels cachés dans le corps de `texte_afficherLignes` | Preuve que l'étape 2 dessine les mêmes pixels que le vrai code ; sert aussi si on modifie du code |
| 4 | **Exécution de l'écran complet** (moteur de menu piloté par la vraie logique) | 3 | L | Élevé : appels noyau, dépendances à l'état (réglages reçus du A) | Rendu d'un écran sans réécrire sa disposition |
| 5 | **Démarrage complet** du B dans l'émulateur Java (plate-forme D40, faux A, boucles matérielles) | 5 en principe, 2 en pratique | XL | Très élevé : registres du D40 non documentés, boucles d'attente, A à simuler, pas de wiki lisible | Boîtier virtuel avec touches ; seul moyen de tester du code (pas des données) |
| 6 | Unicorn / QEMU / MAME avec cœur FR neuf | 1 | XL | Très élevé | Rien que l'étape 5 n'apporte déjà |

Décisions à prendre dans l'ordre :
- Faire 1 puis 2 sans attendre : ensemble ils couvrent ce que tes patchs actuels modifient (courbes, matrices, palette, textes, icônes).
- Faire 3 **seulement** si, en 2, un rendu d'écran ne ressemble pas à la photo de l'écran réel : c'est le moyen de savoir si l'erreur vient de la mise en page ou des données.
- Ne lancer 5 que si tu passes aux **patchs de code** (nouvelle entrée de menu, mode Street, ISO auto), où la seule alternative est de flasher à l'aveugle. Pour les patchs de données, 1 et 2 suffisent, et la voie reste à faible risque (le chargeur de démarrage n'est jamais écrasé, CARTE §3).

## 6. Risques et incertitudes

- **Wiki et forum nikonhacker.com** : page `NikonEmulator` en 404 ; aucune lecture du forum. Les conclusions sur l'émulateur viennent donc du code, pas de retours d'usage. Une version archivée (Wayback Machine, règle « lien mort = Wayback » de ta mémoire) pourrait confirmer jusqu'où les auteurs sont allés (écran, menus) ; à tenter avant de lancer l'étape 5.
- **Compatibilité de l'Expeed du D40 avec celui du D5100** : même famille de blocs (0x4002, 0x4003, 0x4006, 0x5000), mais deux générations d'écart (le D40 date de 2006) ; hypothèse, pas vérifiée registre par registre.
- **Liaison B↔A** : format sur le fil non décodé ; sans lui, pas de faux A fiable.
- **Corps de `texte_afficherLignes`** et fonctions de mise en page `0x7C440` : non lus dans cette étude ; ils peuvent cacher un appel noyau ou une dépendance à un état.
- **Prise en charge du D40 par LibRaw** : présumée, à confirmer sur un vrai NEF avant tout calage.
- **Aucun installé** : `rawpy` seul est recommandé ; Java (JDK 17 et 25), Ghidra 12.2 avec le module fr60, Pillow, numpy et exiftool sont déjà présents.
