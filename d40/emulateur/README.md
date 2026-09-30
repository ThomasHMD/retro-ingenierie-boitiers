# Émulateur du processeur B du D40

Fait en octobre 2026. Il exécute le vrai code de `firmware/BD400111.bin` (ou d'un firmware patché) : démarrage, noyau REALOS, 24 tâches, écran d'infos, menus, touches. On voit à l'écran ce que le boîtier dessinerait, et un crochet de code peut être essayé avant de flasher.

## Paliers atteints

| Palier | État | Preuve |
|---|---|---|
| 1. Démarrage jusqu'au noyau et aux tâches | **atteint** | 16 tâches lancées (`sta_tsk`) entre 1,16 et 1,8 M instructions, dont l'interface (16) ; plus de 1 500 appels au noyau en 60 M instructions, sans exception |
| 2. L'interface se dessine, capture PNG | **atteint** | écran d'infos de prise de vue dessiné par la tâche 16 vers 63 M instructions ; menus capturés (`scenarios/menu.txt`) |
| 3. Touches simulées, navigation | **atteint** | MENU, haut, bas, gauche, droite, OK : on entre dans « Optimize image », on choisit « Softer », OK : l'octet `0x83CE957F` passe à `0x10` et le menu revient avec « SO » ; puis retour à « Normal » |
| 4. Un crochet de code s'exécute sans planter | **atteint dans l'émulateur** | `tests/crochet-menu.json` (`ldi:32 #0x3E7000, r12 ; jmp @r12` dans `ecran014_entree`) tourne 3 fois, le menu continue ; `tests/crochet-delai-interdit.json` (le cas Nikon Hacker, `ldi:32` dans un créneau de délai) est refusé |

```
$ python3 emulateur/d40emu.py verifier
…
===== bilan
OK    démarrage, firmware d'origine (code 0, attendu 0)
OK    menus et touches, firmware d'origine (code 0, attendu 0)
OK    crochet valide (tests/crochet-menu.json) (code 0, attendu 0)
OK    crochet fautif, ldi:32 dans un créneau de délai (doit être refusé) (code 2, attendu 2)
```
Code de sortie 0 si les quatre résultats sont ceux attendus. 21 s pour les quatre sur le Mac Studio (37 à 45 millions d'instructions FR par seconde).

## Lancer

Prérequis : un JDK 17 ou plus (celui de Homebrew est trouvé tout seul), `git`, Python 3. L'émulateur écrit lui-même ses PNG.

```
python3 emulateur/d40emu.py --cloner verifier            # 1re fois : clone nikon-firmware-tools et compile
python3 emulateur/d40emu.py scenario menu                # captures dans ~/Library/Caches/d40-emulateur/sorties/menu/
python3 emulateur/d40emu.py scenario menu-fr --firmware build/BD400111.BIN
python3 emulateur/d40emu.py patch patchs/pipboy-palette.json menu-fr   # patch.py dans le cache, puis le scénario
python3 emulateur/d40emu.py desassembler 0x143B46 20
```

- `--style classique|graphique|fond|tous` (octobre 2026) : réglage CONFIG › Style écran infos simulé, écrit en `0x83CED0FF` à 1 M instructions (`0x01`, `0x51`, `0xA1` ; bit 0 laissé à sa valeur de départ). Défaut `classique`, le réglage du boîtier de Thomas. `tous` joue le scénario en Classique puis en Graphique, captures dans `<sortie>/<style>/`, code de sortie le pire des deux. `verifier` joue dans le premier style demandé.
- Tout ce qui est compilé, cloné ou capturé va dans `--travail` (défaut `~/Library/Caches/d40-emulateur`, hors du dépôt) ; `--sortie` choisit le dossier des PNG. `--verbeux` affiche chaque échange avec le faux A et chaque commande du moteur 2D.
- La compilation ne prend dans nikon-firmware-tools que les classes nécessaires (`javac -sourcepath`), Ant n'est pas utile. Elle est refaite quand un `.java` de `java/` change.
- `patch` passe par `patch.py` (octets d'origine vérifiés, CRC recalculé) ; le firmware produit reste dans le cache, rien n'est écrit dans `build/`.
- La JVM est lancée et attendue par le script : aucun processus ne reste derrière.

### Scénarios (`scenarios/*.txt`)

Une commande par ligne, `#` commente. Durées en instructions (`K`, `M`).

| Commande | Effet |
|---|---|
| `run 70M` | exécuter |
| `press <touche> [appui] [attente]` | appuyer (4M par défaut), relâcher, attendre (4M) |
| `down` / `up <touche>` | enfoncer / relâcher |
| `png <fichier>` | capture du tampon d'interface (YCbCr 4:2:0 640×480, pointeur `0x83CE0230`) |
| `a <cmd> [octets]` | le faux A envoie une commande, avec ses données |
| `peek`, `poke8`, `expect8`, `expect32min` | lire, écrire, vérifier la RAM (un `expect` raté donne le code 1) |
| `watch <adr>…` | journaliser chaque passage du PC (avec RP et R4) |
| `watchw <adr> <long hex> [max]` | journaliser les écritures dans une plage de mémoire (`java/Surveillance.java`) |
| `sys on` | tracer les appels au noyau |
| `poke32`, `expect16`, `remplir <adr> <n> <octet>` | écrire un mot, vérifier un demi-mot, remplir une zone |
| `expectegal <a> <b> <n>` | vérifier que n octets en a et en b sont identiques (registres de la puce contre une table de la ROM) |
| `copier <src> <dst> <n>` | recopier n octets (décimal, ou 0x…) : garder ce que la puce a reçu dans un cas de référence, pour un `expectegal` plus loin (octobre 2026) |
| `appel <adr> [r4 r5 r6 r7]` | exécuter une fonction du firmware jusqu'à son retour, comme un CALL : interruptions masquées, pile à part (`0x83FF0000`), registres, PS et PC rendus ; garde si la pile n'est pas rendue (V1, octobre 2026) |
| `jusqua8 <adr> <octet> <touche> <max>` | appuyer sur la touche (4M, puis 16M d'attente) tant que l'octet n'a pas la valeur, au plus `max` fois ; échec (code 1) si elle n'est pas atteinte. Sert à aller sur un onglet ou en haut d'une liste quel que soit le point de départ (octobre 2026) |
| `ybrut <fichier>` | plan Y brut du tampon d'interface (640 × 480 octets) ; avec une palette de sonde (entrée i en gris de luminance connue), dit quelle entrée de `0xD87C3` peint chaque point (octobre 2026) |
| `onglet <n>` | aller à l'onglet n (`0x83CE3FE8` : 0 VISU, 1 PRISE DE VUE, 2 PERSO, 3 CONFIG) depuis la ligne des onglets, avec ▶ si le firmware a la navigation du bandeau (entrée `0x131F8A` détournée), ▼ sinon : un même scénario sert aux deux navigations. Pour entrer dans la liste, `press ok` (les deux) (octobre 2026) |
| `retour <adr> <valeur>` | la fonction en `adr` rend aussitôt `valeur` dans R4, à chaque appel (ex. `retour 0xAB5CC 1` : `maj_chercherFichiers` « trouve » un fichier de mise à jour sans carte) |
| `expecta <cmd> <i> <octet>` | octet i de la dernière trame de la commande reçue du B par le faux A, sur le fil (octobre 2026) |
| `raza`, `expectcomptea <cmd> <min> <max>` | remettre à zéro, puis vérifier le nombre d'envois d'une commande par le B (tentatives perdues dans une collision non comptées) |
| `etata <cmd> <octets…>` | bloc que le faux A a déjà reçu (gardé d'avant l'extinction) : il le renvoie en écho (0x06 pour 0x05) tant que le B n'a rien envoyé d'autre |
| `entree <adr> <ou> [<et>]` | broches d'entrée d'un port : valeur lue = (mémoire & et) \| ou. `entree 0x50000105 0x02` fait prendre au démarrage la branche de `FUN_0004044c` où le B relit ses réglages perso en flash (`0x83CED254` → `0x83CE974D`) et les envoie au A (commandes 1, 7 et 5) ; sans elle, l'émulateur prend l'autre branche et le B n'envoie rien au A au démarrage. Celle du boîtier est probablement la première (hypothèse) |

Touches (`java/Touches.java`) : `menu`, `ok`, `play`, `up`, `down`, `left`, `right` sont vérifiées à l'écran ; `b08` = aide « ? » maintenue (vérifié, `scenarios/preglages-fr.txt`) ; `info`, `b01`, `a0_01` (quitte le menu vers l'écran d'infos, déclencheur à mi-course ?), `a0_02`, `a0_04`, `a1_01`, `a1_02`, `a1_10`, `a2_80` restent à nommer. Il faut tenir une touche au moins deux scrutations de la tâche 15 (une toutes les 1,3 M instructions) : d'où les 4M.

Scénario des préréglages V1 : `preglages-v1.txt` (README, « V1 : code des préréglages ») : chaque préréglage choisi au menu, puis la chaîne de prise de vue jouée par `appel` (`0x4793A`, `0x31A0F8`, `0x4B41C`) et les registres de la puce comparés aux tables par `expectegal` ; netteté, saturation et tons de chaque rendu (variables, registres `0x40010054`–`57`, table `0x4001EC00`) comparés à un Personnalisé réglé à la main, gardé par `copier` ; teinte ±9° : page `0x40010000` identique hors YCbCr ; Programme et Si trop sombre relus. Deux fiches de balances différentes (A puis B calculées, puce chargée pour A puis pour B) : chacune garde sa balance. À jouer avec `--firmware <build V1>/BD400111.BIN` (151 contrôles, code 0). Scénario `reinitialiser.txt` : PERSO › Réinitialiser › Oui remet Programme et Si trop sombre à 0 (on pose le menu PERSO depuis la colonne des onglets, juste après le démarrage, pour ne pas dépendre de leur ordre).

Scénarios du menu Pip-Boy : `pipboy.txt` (tous les écrans et les aides, 6 valeurs rangées vérifiées par `expect8` : Programme, marche, ISO mini, ISO maxi, vitesse mini, Si trop sombre) et `pipboy-batterie.txt` (niveaux de batterie envoyés par `a 2d`, octet 19). À jouer avec `patch patchs/menu-pipboy.json`.

Scénario `ecran-infos.txt` (octobre 2026, étape 8) : chiffres de l'écran d'infos (valeur verte, fantôme sombre), mode Régler (touche `info`) et liste de choix sur fond noir, case choisie verte. Les deux firmwares.

Scénario `navigation.txt` (octobre 2026, étape 7) : dans CONFIG, ▲ remonte le défilement avant de quitter la liste (ligne visible `+0xC` et défilement `+0xE` du menu), seule la vraie première ligne renvoie au bandeau ; dans le sous-écran Programme, ▲ en haut boucle en bas comme chez Nikon. Firmware avec bandeau seulement.

Scénario de la voie de secours : `secours.txt` (octobre 2026) : depuis chacun des 4 onglets mémorisés, CONFIG › Version du firmware (écran 105) puis « Mise à jour ? » (écran 106, curseur sur Non), sans répondre, et retour. Menus passés en Complet d'abord (le démarrage est en Simple, sans Version du firmware), `retour 0xAB5CC 1` (pas de carte), batterie mise à `0xC0` en `0x83CE950C`. À chaque étape : pointeur de menu `0x83CEE49C`, mode `0x83CED23A` = 5, et 3 ou 4 points de l'écran (colonne de Nikon présente, titre, barre). Captures `secours-<onglet>-105.png` et `-106.png`. Doit rendre 0 sur tout firmware, avec ou sans bandeau ; un bandeau sans sas le fait échouer. Le scénario `pipboy.txt` contrôle aussi le bandeau de l'étape 5 (6 `expect8` dans le tampon d'écran, plus 3 sur son pointeur, qui vaut `0x83BD6510` dans l'émulateur).

Scénarios du Programme envoyé au A (octobre 2026, étape 9 ; `--firmware build/V5/2-ensuite-processeur-B/BD400111.BIN`) : `programme-a.txt` (22 contrôles : la commande 5 part au choix d'un Programme, la copie envoyée porte bit 7 et 8 + Programme, l'octet ISO auto du B n'est pas touché, l'écho 0x06 est remis, Standard renvoie l'octet de l'utilisateur, Réinitialiser aussi) et `programme-a-demarrage.txt` (démarrage réel par `entree`, le faux A ayant gardé un bloc avec Programme : l'octet ISO auto de l'utilisateur, relu en flash, sort intact et le A reçoit le Programme ; puis la molette par `a 14` : en A, M et en scène le A reçoit l'octet de l'utilisateur, en P le Programme ; **doit échouer** sur le B de Nikon, et sur un B qui enverrait le Programme dans tous les modes). Côté A : `a-programmes.txt` et `a-programmes-112.txt` (120 cas chacun, écrits par `outils/programmes_a.py scenario`), joués par `a-verifier`.

Langue : `poke8 0x83CED0FC 0x18` avant 1,8 M instructions met l'interface en français (`menu-fr.txt`). Codes vus à l'écran : 0 allemand, 1 anglais (défaut), 2 espagnol, 3 français, 4 italien.

## Processeur A (étude d’octobre 2026)

Rapport : [`recherche/etude-a/emulation.md`](../recherche/etude-a/emulation.md). Classes `AEmu.java` (mémoire du A, chargé à `0xC0000`, gardes), `AIo.java` (périphériques : attente d'horloge, recherche de bit `0x3F4`, base de temps 1 ms, A/N, EEPROM série simulée au niveau des fonctions, DMA par blocs), `ABoot.java` (lanceur et scénarios du A), `FakeB.java` (faux B pour la liaison).

```
python3 emulateur/d40emu.py a-verifier              # 12 essais du A, code 0 si tous ont le résultat attendu
python3 emulateur/d40emu.py a-scenario a-ligne-p    # la fonction de P appelée directement, sur 7 cas
python3 emulateur/d40emu.py a-demarrer 40M          # le A seul depuis son reset
python3 emulateur/d40emu.py a-desassembler 0xC60E2 30
```

Ce qui marche : la chaîne d'exposition appelée directement (`appel`), conforme à la ligne d'usine (14 contrôles) ; un patch de ligne fabriqué par `patch.py` puis joué tel quel ; la liaison côté A avec le faux B (commande 0x05 reçue, 0x14 envoyée) ; le démarrage jusqu'au noyau et 5 tâches. Ce qui manque : la fin du démarrage (temporisateur PPG, mécanique, faux objectif), d'où la tâche 4 (commandes du B, appel d'`expo_programme`) qui ne tourne qu'une fois, et le branchement du vrai A sur le vrai B. `tests/a-sujet-rapide.json` est un essai, **pas un patch à flasher** : il place du code en `0xF3910`, dans la zone du flasheur du A (`0xF3000`–`0xF3AFF`), à ne jamais toucher (voir `recherche/etude-a/mise-a-jour-et-recuperation.md`).

**Faux A paramétrable** (variables d'environnement, défaut inchangé) : `D40_FAUXA=muet|silencieux`, `D40_FAUXA_SANS=03,14,19`, `D40_FAUXA_SEUL=14,19`, `D40_FAUXA_MAJ=1` (le faux A joue le côté A de la mise à jour du A : 0x0D, blocs de 128 octets par 0x0F, compte rendu 0x0E ; `D40_FAUXA_FICHIER`, `D40_FAUXA_STATUT`, `D40_FAUXA_BLOCS`). Scénarios `fauxa-*.txt` : `fauxa-maj-a` (mise à jour du A jouée, blocs identiques au fichier, code 0), `fauxa-muet-105` (avec `D40_FAUXA=muet`, **doit échouer** : sans A, le B n'atteint pas les menus), `fauxa-batterie-106`, `fauxa-ligne-haute`. Commande de scénario `charger <fichier> <adr>`.

## Comment c'est fait

Choix : le cœur FR Java de nikon-firmware-tools (jeu d'instructions complet avec créneaux de délai, interruptions, testé par ses auteurs) plutôt qu'un émulateur Python, trop lent pour un démarrage de plusieurs dizaines de millions d'instructions. De ce dépôt on ne reprend que `FrEmulator`, `FrCPUState`, `DebuggableMemory`, `FrInterruptController` et le désassembleur ; la plate-forme D5100 (`EmulationFramework`, périphériques, interface Swing) n'est pas utilisée. Le reste est écrit pour le D40, dans `java/` (paquet `com.nikonhacker.emu` pour accéder au contexte de l'émulateur) :

| Fichier | Rôle |
|---|---|
| `D40Emu.java` | mémoire (firmware à `0x40000`, RAM allouée à la demande), reset `0xC0F90` (le code règle lui-même TBR = `0xEFC00` et la pile), boucle d'exécution, traçage des appels au noyau (`INT #0x40`), **gardes**, désassembleur |
| `D40Io.java` | périphériques (ci-dessous) |
| `FakeA.java` | faux processeur A |
| `Touches.java`, `Ecran.java` | touches ; conversion du tampon en PNG (BT.601) |
| `Boot.java` | lanceur et langage des scénarios |

### Périphériques : ce qui est émulé, simulé, bouché

| Bloc | Traitement | Confiance |
|---|---|---|
| RAM `0x68000000`, `0x81000000`, `0x83xxxxxx` | mémoire simple, mise à zéro | — |
| Minuteries à recharge `0x48`/`0x50`/`0x58` (TMRLR, TMR, TMCSR) | émulées (diviseur, recharge, UF, interruptions 0x18-0x1A). La minuterie 0 est le tic du noyau, la 1 la scrutation des touches, la 2 la garde de la liaison A | vérifié par le fonctionnement |
| DICR `0x44` (interruption retardée 0x3F du noyau) | émulé | vérifié |
| ICR `0x440`-`0x47F` | lus en mémoire par le contrôleur d'interruptions | vérifié |
| Liaison série 0 (`0x60` SSR0, `0x61` données, `0x62` SCR0, `0x63` SMR0), poignée de main `0x50000106` bit 4, interruption 0x1B | émulée octet par octet : chaque poignée de main produit, 400 instructions plus tard, l'octet du faux A | vérifié (protocole lu dans `0xAA8CC`-`0xAAD8C`) |
| Interruptions externes `0x38` EIRR, `0x39` ENIR, `0x3A` ELVR (vecteurs 0x1E-0x25) | canal 0 = synchro de trame, levée toutes les 1 M instructions ; canal 1 = ligne de requête du A | probable (rôle du canal 0 déduit de la tâche 18) |
| Port `0x50000102` bit 3 | parité de trame, basculée à chaque synchro | probable |
| Port `0x5000010C` | touches du B, actives à 0 | vérifié |
| Moteur 2D `0x40060000` (commande `0x80`, pas `0x8C`/`0x8E`, taille `0x90`/`0x92`, source `0x94`, destination `0x98`, état `0x32`, interruption 0x24) | remplissage `0x47xx` émulé ; copie (bit `0x2000`) émulée par hypothèse ; autres commandes (`0x46xx`, `0x6Fxx`) : fin immédiate sans effet | remplissage vérifié par l'image |
| Redimensionnement `0x40020000` (démarrage bit 3 de `0x40020000`, état `0x40021FFE`, interruption 0x28) | **bouché** : fin immédiate, rien n'est calculé. Il ne sert qu'à recopier l'interface vers l'écran LCD ; la capture lit directement le tampon d'interface | vérifié pour le mécanisme |
| Codec JPEG `0x40030000` | **bouché** : `0x400` répond prêt (`0xC000`) ; aucune décompression | — |
| Tout le reste (`0x40010000`, `0x40040000`, `0x40070000`, `0x400E0000`, `0x5C00xxxx`, `0x64000000`) | comme de la RAM | — |

### Le faux A

Le B parle au A par la tâche 14 (CARTE §10 bis). Le protocole, lu dans les gestionnaires de réception (`tblLiaisonA_etatsRx` `0xE4B3C`), est reproduit en lisant l'état de l'automate du B (`0x83CEE964`) quand l'octet arrive :
- le B envoie son numéro de commande ; le A répond **en même temps** par sa propre requête (0 = rien) ;
- commande du B (sens B→A) : longueur, données, complément de la somme ; le A répond n = 0 puis un octet de contrôle tel que la somme de tout ce qu'il a envoyé fasse `0xFF` ;
- commande du A (A→B) : n (longueur de `tblCommandesA`), n octets, contrôle ;
- le A signale une requête par un front montant sur sa ligne (canal 1 de `0x38`).

Ce que le faux A envoie (hypothèses rendues nécessaires par le code, sauf mention) :
- au démarrage, les blocs d'état 0x11, 0x08, 0x03, 0x02, 0x04, 0x06, 0x0A, 0x0C, 0x0E, 0x15, 0x16, 0x1A, 0x1C, 0x23-0x29, 0x14, 0x19, tous à zéro sauf `0x83CE9831` bit 3 (la tâche 21 l'attend) ; **0x14 et 0x19 sont indispensables** : leurs fonctions de fin posent les bits 0x80000 et 0x100 du drapeau 3 que la tâche 15 (touches) attend ;
- quand les deux envoient une commande au même octet (collision), celle du A passe et le B renvoie la sienne plus tard : vu au démarrage réel (B 0x01 contre les blocs d'état du A, B 0x05 contre 0x08). Le faux A ne compte pas la tentative perdue et n'y répond pas ; avant en octobre 2026, il répondait 0x06 à chaque 0x05 perdu, d'où une boucle sans fin (3 339 envois en 70 M instructions) ;
- l'écho (0x06 pour 0x05, 0x08 pour 0x07, 0x0A pour 0x09) reprend la trame reçue sur le fil, comme le vrai A, et non la mémoire du B : l'écart compte dès que le B retouche la copie envoyée (étape 9) ;
- 0x2D après 0x2C (l'interface l'attend avant de dessiner) ; 0x08 après 0x07, avec les réglages que le B vient d'envoyer (le menu attend le drapeau 9 bit 0x400000 posé par la fin de 0x08 : sans cet écho, l'interface reste figée après OK) ; 0x06 après 0x05 et 0x0A après 0x09 par symétrie, non vérifiés ;
- les touches du A passent par la commande 0x11.

Conséquence visible : des réglages à zéro, d'où les « 888 » de l'écran d'infos (vitesse, ouverture, vues restantes inconnues).

### Gardes (le test qui compte pour le flash)

Avant chaque instruction, `D40Emu.verifier()` arrête l'émulation (code 2) si :
- l'instruction n'est pas définie, ou vaut `0xFFFF` (flash vide : c'est un `BHI:D` sur lui-même, le boîtier tournerait en rond) ;
- une instruction de saut, d'appel, de retour, d'interruption ou de plusieurs mots (`LDI:32`, `LDI:20`, …) est dans un créneau de délai ;
- le PC sort de la ROM `0x40000`-`0x40FFFF` et de la RAM, ou entre dans `0x0F0000`-`0x11FFFF` ou `0x170000`-`0x1AFFFF` (jamais écrites par la mise à jour : leur contenu réel est inconnu).

Le firmware d'origine passe toutes les gardes sur les scénarios fournis.

## Ce qu'un test réussi prouve, et ce qu'il ne prouve pas

- Il prouve que le code ajouté s'enchaîne correctement (encodage, retour, registres rendus, créneaux de délai) et que l'interface continue de vivre après, **dans les chemins que le scénario parcourt**.
- Il ne prouve rien pour le matériel : moteur d'image, JPEG, carte, flash, chronométrage réel (la fréquence du FR n'est pas mesurée : « 1 M instructions » n'est pas une durée connue). La prise de vue n'est pas émulée : un crochet dans son chemin (`0x4B41C`) n'est atteint qu'en appelant soi-même les fonctions par `appel` (scénario `preglages-v1`), et le moteur d'image n'étant que de la mémoire, on vérifie ce qui est écrit dans ses registres, pas l'image.
- **Les couleurs ne valent que pour le style simulé** (octobre 2026) : les menus ont deux jeux de couleurs et l'écran d'infos deux dessins, choisis par CONFIG › Style écran infos (`0x83CED0FF`). L'émulateur démarre en Graphique (`0x51`) ; le premier boîtier flashé était en Classique, et tous les scénarios passaient alors que l'écran réel était bleu marine et vert sur vert. D'où l'option `--style` (défaut `classique`, le réglage du boîtier de Thomas) et `--style tous` : un `expect8` de couleur n'a de valeur que joué dans les styles que le boîtier peut avoir.
- **Le démarrage émulé n'est pas celui du boîtier** (octobre 2026) : la broche `0x50000105` bit 1 est lue à 0, et `FUN_0004044c` prend alors la branche où le B ne relit pas ses réglages perso en flash et n'envoie ni 1, ni 7, ni 5 au A. Le boîtier prend très probablement l'autre (hypothèse : sinon le A ne recevrait jamais les réglages gardés par le B). `entree 0x50000105 0x02` la force ; tous les scénarios n'ont pas été rejoués ainsi, seulement `programme-a-demarrage`.
- **Le A et le B ne tournent jamais ensemble** : côté B, un faux A ; côté A, le vrai A face à un faux B. Une erreur commune aux deux faux (ordre des commandes au démarrage, contenu des blocs d'état) passerait inaperçue.
- L'adresse du compteur du crochet de test (`0x83D80000`) n'est jamais touchée dans l'émulateur, ce qui ne prouve pas qu'elle est libre dans le boîtier. Les deux patchs de `tests/` ne sont pas faits pour être flashés.

## Constats utiles au reste du projet

- `patchs/pipboy-palette.json` (palette `0x1B0000`) ne change que **les icônes** (onglets en vert) ; le fond, le texte et la surbrillance des menus n'en dépendent pas. Ils viennent sans doute de la palette de 3 octets `0xD87C3` (CARTE §9), à essayer.
- Le firmware `build/BD400111.BIN` (titres Pip-Boy) démarre et affiche STAT, DATA, PIP-BOY 3000 en français (`scenario menu-fr --firmware build/BD400111.BIN`).
- Symboles ajoutés à `desassemblage/symboles.tsv` en octobre 2026 : touches, liaison A (gestionnaires et tables d'états), moteur 2D, redimensionnement, `ui_demarrer`, `langue_appliquer`.

## Limites et prochaines étapes

1. **Fond de l'écran d'infos** : en Graphique (et Fond d'écran) seulement, c'est une image JPEG (`0xDFBB2`) décodée par le codec `0x40030000`, non émulé, puis posée dans le tampon d'interface par le moteur de redimensionnement `0x40020000`, non émulé non plus (il ne sert donc pas qu'au LCD) ; l'écran d'infos garde des restes de l'écran précédent. En Classique, l'écran d'infos est entièrement dessiné par le processeur et l'émulateur le rend fidèlement. Ce qu'il faudrait émuler, registre par registre : `recherche/ecran-reel-composition.md` §4. Depuis l'étape 6 du Pip-Boy, ce JPEG est un fond noir uni : l'émulateur montre donc ce que le boîtier devrait afficher, sauf si le décodeur du boîtier refuse le nouveau fichier.
2. **Données du A plus réalistes** (commandes 0x08, 0x14, 0x1C, 0x24) pour un écran d'infos plausible et pour tester les menus qui dépendent du mode (molette en scène, etc.).
3. **Visualisation** (touche `play`) : demande une carte mémoire (contrôleur `0x5C00xxxx` ou `0x6400xxxx`) et le JPEG.
4. **Chronométrage** : mesurer la fréquence du FR (tic du noyau : `TMRLR0 = 0x80E8` à φ/2) pour convertir les instructions en temps.
5. Un instantané de l'état après le démarrage (70 M instructions, 2 s) accélérerait les scénarios ; pas nécessaire pour l'instant.
