# D200 V1 : relecture adversariale avant flash

Relecture indépendante d’octobre 2026 (horodatage lu par `date`), faite avant tout flash. Fichier relu : `build/d200/v1/B2000201.BIN`, sha256 `402f00f5b0e3efb88af912548bec92b0b996e919a07f09d700ea0fdefdde92c9`. Rien n'a été flashé, rien n'a été modifié dans le projet (fichiers de travail hors du dépôt, dans le dossier temporaire de la session). *Vérifié* = lu dans les octets ou le désassemblage, ou rejoué, avec la preuve citée ; *hypothèse* = déduit, non prouvé par le binaire.

Outils : Python, `openssl`, `unar` ; Ghidra 12.2 avec le module FR60 (`fr60:BE:16:default`, base `0x50000`), lancé en ligne de commande avec un script de désassemblage linéaire écrit pour cette relecture ; le désassembleur de nikon-firmware-tools (`d200emu.py desassembler`), indépendant de Ghidra ; l'émulateur du projet. Rien n'a été installé.

## Verdict : GO sous condition

> **Mise à jour après le delta d’octobre** : la condition 1 est remplie. Verdict final : **GO** sur `build/d200/v1/B2000201.BIN`, sha256 `bb052a60…151d53`, en suivant la procédure de `d200-firmware-image.md` §10 telle qu'elle est écrite (preuves : section « Delta d’octobre », en fin de document). Ce qui suit est la relecture du fichier `402f…`.

Le fichier est propre : chaque octet changé est expliqué par la recette, la chaîne de mise à jour est intacte à l'octet près, le boîtier l'acceptera, et le code ajouté est correct (registres, pile, créneaux de délai, retour). **Un seul risque de brique est propre à ce patch** (constat 1). Il n'est pas prouvé, mais il se supprime à faible coût.

Conditions, dans l'ordre :

1. **Déplacer le bloc des préréglages** (code, tables, 4 emplacements : 18 642 octets, aujourd'hui en `0x3FA000-0x3FE9FF`) dans le secteur `0x170000-0x17FFFF`, par exemple en `0x177000-0x17B9FF`. Ensuite : refaire le JSON et le build, relancer `d200emu.py verifier`, et vérifier que **chaque secteur touché contient déjà des octets Nikon** (contrôle du constat 1). Si Thomas préfère flasher le fichier actuel, il prend sciemment le risque du constat 1, couvert seulement par le précédent du D40.
2. Flasher **ce fichier-là** (sha256 `402f…`, ou celui qui sortira de la condition 1), **jamais** le fichier du cache que désigne `d200-preglages.md` §9 (constat 2).
3. Avant le flash, lire au boîtier, dans Configuration › Version du firmware, **A 2.01 et B 2.01**. Aujourd'hui, la seule source est la parole de Thomas (octobre).
4. Batterie EN-EL3e pleine ou adaptateur secteur, carte formatée dans le D200, `B2000201.BIN` seul fichier `B200….BIN` à la racine. Avoir prête une seconde carte avec l'original (`build/d200/origine/B2000201.BIN`, sha256 `b7ce…07d1`).

## Constats, du plus grave au moins grave

### 1. Le bloc des préréglages est écrit dans trois secteurs que Nikon n'a jamais programmés sur le D200 (hypothèse ; gravité : brique si elle se réalise)

**Ce qui est vérifié.** Le V1 touche 10 secteurs de flash. Sept contiennent déjà des octets Nikon et sont donc programmés à chaque mise à jour officielle : `0x050000`, `0x0C0000`, `0x0D0000`, `0x170000`, `0x240000`, `0x250000`, `0x3B0000`. Trois n'ont **aucun** octet Nikon dans le 2.01 : les secteurs de 8 Ko `0x3FA000`, `0x3FC000` et `0x3FE000`. La mise à jour de Nikon les efface, puis ne les écrit jamais : le flasheur saute les mots `0xFFFF` (`FUN_0015c9c4` : `CMP R0=0xFFFF` puis sortie, `0x15C9D0-0x15C9DA`). Aucun écrivain de flash à l'exécution n'y va non plus. J'ai recensé tous les appels aux primitives `0x72BD4` (effacer) et `0x72BE6` (écrire) : 6 fonctions, qui visent `0x1D0000`, `0x1E0000`, `0x1F0000`, `0x410000`, `0x420000`, `0x430000` et `0x440000`.

**Ce qui fait craindre une protection (hypothèse).** La géométrie lue dans le code correspond à une puce de 4 Mo à secteurs d'amorce en haut :
- 8 secteurs de 8 Ko en `0x3F0000-0x3FFFFF` (table de la RAM `0x97984150`, recopiée de `0x1538CC` : départs `0x3F0000` à `0x3FE000`, tailles `0x2000`) ;
- commandes de la flash envoyées à `0x400AAA` et `0x400554` ;
- test `(adresse & 0x3F0000) == 0x3F0000` dans `FUN_0015c844`, qui vaut aussi pour `0x7F0000` ;
- journaux et réglages d'usine en `0x410000-0x44FFFF`, juste sous le début du firmware vu en miroir.

Sur ce type de puce (familles AMD et Fujitsu), la broche WP# tenue au niveau bas protège les **deux secteurs extrêmes** : ici `0x3FC000-0x3FFFFF`, où se trouvent la fin de Positive, FP4 et HP5. Si c'est le cas sur la carte du D200 :
- l'effacement de ces secteurs « réussit » sans rien faire (ils sont déjà vierges, le contrôle à blanc `FUN_0015c936` passe) ;
- la programmation, elle, échoue (`FUN_0015ca28` rend 0 au premier mot dont le bit 7 vaut 0), ainsi que la relecture ;
- le flasheur recommence trois fois (`0x15C756-0x15C802`), puis abandonne.

Or, à chaque essai, il efface d'abord `0x0E0000` (vecteurs), `0x050000-0x0DFFFF`, `0x120000-0x1CFFFF` et `0x200000-0x40FFFF`, et il n'écrit `0x050000-0x0EFFFF` **qu'en dernier**. Un échec en `0x3FC000` laisserait donc le boîtier sans vecteurs ni code principal. Seul resterait le chargeur, qui n'est pas dans le fichier et n'a jamais été lu.

Une mise à jour Nikon ne peut pas révéler cette protection : elle n'écrit jamais rien dans ces secteurs. Le firmware du D200 ne contient aucun code qui piloterait WP#.

**Pour.** Le B V5 du D40 (`build/d40/V5/2-ensuite-processeur-B/BD400111.BIN`, sha256 `bfa6eb0b…`, flashé en octobre au soir, « tout semble ok ») contient des données dans les 8 secteurs de 8 Ko, y compris `0x3FC000` (8 182 octets) et `0x3FE000` (1 404 octets). Son flasheur a les mêmes commandes (`0x400AAA`, `0x400554`) et la même découpe en `0x3F0000`, et l'original du D40 laisse aussi cette zone vierge. Sur le D40, ces secteurs se programment.

**Contre.** C'est une autre carte, d'une autre année, peut-être une autre puce. Rien dans le binaire du D200 ne prouve que ces deux secteurs se programment.

**Remède.** La place `0x1765EA-0x17FFFF` fait 39 446 octets. Elle est entièrement à `0xFF`, et aucune constante `LDI:32` du firmware ne vise au-delà de `0x176590` dans ce secteur. Elle se trouve dans le secteur `0x170000`, où Nikon a 24 444 octets et où le texte « Positive » du V1 est déjà placé (`0x176600`). Dans `outils/d200_preglages.py`, il suffit de changer `CODE`, `TABLES` et `EMPLACEMENTS`, par exemple `0x177000`, `0x177200` et `0x177400`, ce qui donne une fin à `0x17BA00`. La zone reste dans les plages réécrites par la mise à jour (`0x120000-0x1CFFFF`) et hors des zones interdites. Solution de repli moins bonne : `0x3F72A8-0x3FBFFF` (19 800 octets), hors des deux secteurs extrêmes mais jamais programmée par Nikon non plus.

### 2. Deux fichiers « combinés » circulent, et la doc des préréglages désigne le mauvais pour le flash (vérifié ; gravité : procédure)

- `recherche/d200-preglages.md` §2 annonce un combiné « 22 847 octets, CRC `0835`, sha256 `389a955b…` ». Son §9, étape 2, dit de flasher `~/Library/Caches/d40-emulateur/d200/firmwares/d200-preglages-combine/B2000201.BIN`. Ce fichier existe, avec le sha256 `389a955b…`. **Ce n'est pas** `build/d200/v1/B2000201.BIN` (`402f…`, CRC `6a7d`, 22 592 octets).
- Différences (`cmp` puis balayage) : données seulement, à savoir la courbe Tri-X `0x3B27D4-0x3B32DC` et les emplacements `0x3FA401-0x3FE9FF` (courbes sans l'épaule ajoutée ensuite), plus le CRC. Le code `0x3FA000-0x3FA16B` est identique.
- Ce fichier n'a été ni relu ici, ni joué par `d200emu.py verifier` (qui fabrique `d200-combine`, sha256 `402f…`). Il faut corriger le §2 et le §9 de `d200-preglages.md`, ou supprimer ce fichier du cache.

### 3. Les crochets ne s'exécutent pas au démarrage (hypothèse forte, étayée)

- Seuls trois blocs de code sont modifiés : `isp_chargerPuce` (`0x5DA2B-0x5DA2D`), `FUN_000cd9a2` (`0xCDFB1-0xCDFB3`) et `FUN_000d57e6` (`0xD7842-0xD789D`, patch N&B). Tous trois appartiennent à la chaîne d'image. Vérifié (rattachement de chaque octet à sa fonction d'après les en-têtes du pseudo-C Ghidra).
- Seuls appelants : `0x5D500` (`FUN_0005d444` → `isp_chargerPuce`) et `0x5D6B4` (`FUN_0005d616` → `FUN_000cd9a2`), d'après un balayage des octets (`LDI:32` et `CALL` relatifs). Ces deux fonctions viennent de `FUN_0005cc64` et de fonctions en `0x6Axxx-0x6Cxxx`. Vérifié.
- `FUN_0005cc64` est une tâche (mot de données en `0xE3060`, dans la table des tâches). Elle boucle sur `FUN_00051992`, qui attend des drapeaux et tire un travail d'une file de prises de vue, avant d'appeler `FUN_0005d616`. Au démarrage, la file est vide. Vérifié (lecture du code) ; l'absence de travail au démarrage est déduite.
- Fermeture des appels directs : depuis `reset` (27 fonctions) et depuis `reglages_lire`, aucune fonction modifiée n'est atteinte. Vérifié ; les appels indirects (tâches, tables) ne sont pas couverts, d'où « hypothèse ».
- Même s'ils s'exécutaient, les crochets sont bornés et ne peuvent pas boucler (constat 6).

### 4. Le boîtier acceptera le fichier, et la chaîne de mise à jour est intacte (vérifié)

Contrôles relus dans le code (pseudo-C et désassemblage), puis rejoués en Python sur le fichier patché :

| Contrôle | Code | Fichier patché |
|---|---|---|
| Taille exacte | `FUN_0009acac` : `+0x214 == 0x3C0000` | 3 932 160 = `0x3C0000` |
| Signature | `FUN_0009ae2c` : pointeur lu à l'offset `0x9FBF4`, 32 octets à (pointeur − `0x50000`) comparés jusqu'au NUL à la signature du firmware en cours | pointeur `0x16CAB0`, `Q220FirmwareSignature\0` : identique |
| Version | pointeur à `0x9FBF0`, 9 octets lus pour l'affichage seulement (aucune comparaison, ni dans `FUN_0009ae2c`, ni dans l'écran `FUN_0013a2b2`) | `Ver.2.01 ` (inchangée) |
| CRC | `FUN_0009a9fc` : `FUN_00054552(0x3C0000, 0x90000000) == 0`, table `0x15D284` | table du boîtier = XMODEM `0x1021` ; CRC du fichier entier = `0x0000` (fin `6a7d`) |
| Liaison A | commande `0x27`, réponse attendue en 500 tops (`FUN_0009ab86`) | inchangée |

Zones identiques à l'octet près entre l'origine et le V1 :
- `0xEFBF0-0xEFFFF` (pointeurs, vecteurs) ; `0x9A680-0x9B14A` (chaîne de mise à jour) ; `0x54552-0x54751` ;
- `0x15D284-0x15D483` (table CRC) ; `0x15C72C-0x15CA63` (flasheur) ; **toute la section `.data` `0x15387C-0x15C72B`** (tables du flasheur comprises) ;
- `0x15E008-0x15E107` ; `0x16C760-0x16C85F` ; `0x16CB18-0x16CC17` ; `0x16CAB0-0x16CAFF` (signature et version) ;
- `0xDF48A-0xDFAAF` (reset) ; `0x72BC0-0x72C0F` (relais vers le flasheur en RAM) ; `0xF0000-0x11FFFF` ; `0x1D0000-0x1FFFFF`.

Le reset ne fait que deux copies de la ROM vers la RAM : `.data`, de `0x15387C` (`0x8EB0` octets) vers `0x97984100`, et le flasheur, de `0x15C72C` (`0x338` octets) vers `0x9798CFB0` (`0xDF808-0xDF842`). Ni `0x176600` ni `0x3FA000` n'y sont.

Le CRC16 n'est appelé que par la mise à jour (`0x9AA58` pour B, `0x9AAA0` pour A) ; sa table n'est lue que par lui (`0x5455E`). Aucune autre somme de contrôle de la ROM n'a été trouvée.

**Comparaison avec le D40 V5.** Même famille : signature « Q330… » contre « Q220… », CRC16 XMODEM du fichier entier égal à 0, taille fixe, version affichée seulement. Mêmes contrôles par `patch.py`. Mais l'émulateur du D40 **démarre** le firmware, dessine les menus et joue la voie de secours sur le fichier exact. Celui du D200 ne démarre rien : il appelle des fonctions isolées. La validation du D200 est donc plus faible côté démarrage et menus. Cette faiblesse est compensée par le fait qu'aucune fonction de menu, de démarrage ou de mise à jour n'est modifiée ici (seulement des données de texte).

### 5. Différences complètes : tout est expliqué par la recette (vérifié)

- 293 plages contiguës, **22 592 octets** différents : 22 590 viennent des 37 patchs, et les 2 octets de `0x40FFFE-0x40FFFF` sont le CRC. « Origine + 37 patchs + CRC recalculé » redonne le fichier à l'octet près. **Aucun octet inexpliqué.**
- Ventilation : 9 patchs de code N&B (`0xD7840-0xD789D`), 1 courbe Tri-X (`0x3B22DD-0x3B32DC`), 18 textes français (`0x257B50-0x2595A7`), 1 pointeur (`0x2469F0`), 1 texte en place libre (`0x176600-0x176611`), 2 constantes de crochet (`0xCDFB0`, `0x5DA2A`), 1 bloc de code (`0x3FA000-0x3FA16B`), 1 bloc de tables (`0x3FA200-0x3FA365`) et 4 emplacements (`0x3FA400-0x3FE9FF`).
- Tous sont dans les plages réécrites (`0x050000-0x0EFFFF`, `0x120000-0x1CFFFF`, `0x200000-0x40FFFF`) et hors des zones interdites du §6.
- Rien ne touche les gestionnaires USB/PTP : la table PTP est en `0x8D164-0x8D3E2`, et les seules fonctions modifiées sont celles du constat 3.

### 6. Le code ajouté est correct (vérifié)

Deux désassembleurs indépendants, Ghidra FR60 et nikon-firmware-tools, donnent **les mêmes 127 instructions** pour `0x3FA000-0x3FA16A`.

- **Sites des crochets.** On ne change que la constante d'un `LDI:32 #…,R12` : en `0xCDFAE` (suivi de `CALL @R12`, `971C`, appel sans créneau ; l'instruction précédente est `CALL 0xCE4FA`, `D2A6`, sans créneau) et en `0x5DA28` (suivi de `971C` ; l'instruction précédente, `_ADD R8,R5`, est le créneau du `CALL:D` en `0x5DA24`, mais le `LDI:32` vient après). Les formes d'instruction sont inchangées.
- **`preglage_reglages`** (`0x3FA000-0x3FA05F`).
  - Registres : R0, R1, R2, R13 et R12 seulement. Pas de pile. R4 à R7 sont intacts, donc les arguments arrivent tels quels à `FUN_000cf86a`.
  - Sortie : `LDI:32 #0xCF86A,R12 ; JMP @R12` (`970C`, sans créneau). Le RP du `CALL @R12` d'origine est conservé, et `FUN_000cf86a` (prologue `STM1 (R8,R9)`) rend la main à `0xCDFB6`, où l'appelant ne lit plus que la pile.
  - Pointeur de fiche : `_DAT_97be3e4c`, écrit par `FUN_000cd9a2` dès son entrée (`_DAT_97be3e4c = param_1`), donc toujours celui de la fiche en cours.
  - Les trois variables écrites (`0x97BE3DD4`, `0x97BE3DF8`, `0x97BE3E08`) ne font partie d'aucun des 12 blocs sauvegardés en flash (`tblBlocsReglages`, `0x16C768`).
- **`preglage_puce`** (`0x3FA060-0x3FA16B`).
  - Pile : `ST RP`, `ST R8`, `CALL FUN_000dcff8`, puis `ST R4` ; trois dépilements ; `RET` (`9720`, sans créneau). La pile est rendue équilibrée.
  - `FUN_000dcff8` se réduit à `LDI:32 #0x97BE7F18,R4 ; RET` : pas d'argument sur la pile, donc le décalage de 8 octets est sans effet.
  - La fiche est relue par `LD @(FP,0x18),R1`, avec le FP d'`isp_chargerPuce`. Son prologue (`ST R4,@-SP ; STM1 (R8-R11) ; ST RP ; ENTER #0x10`, `0x5D716`) place l'argument à FP+0x18. Aucune instruction `ST …,@(R14,…)` n'existe dans `0x5D716-0x5DA45`, et Nikon relit lui-même `@(FP,0x18)` en `0x5D8D0`.
  - Au retour, R4 vaut la table de Nikon et R8 est rétabli : `isp_chargerPuce` s'en sert juste après (`0x5DA30-0x5DA3A` : copie de `R4` vers `R8+0xEC00`).
  - R9 à R11 et R14 ne sont jamais écrits. `FUN_0005debe` n'utilise que R0 et R4 à R6.
- **Créneaux de délai.** Aucune forme `:D` (`JMP:D`, `CALL:D`, `RET:D`, `Bcc:D`) dans le code ajouté. Branchements : `BGE`, `BNE`, `BNC` (préfixe `E`). L'émulateur arrête en outre tout `LDI:32` posé dans un créneau (garde jouée, code 2 attendu, obtenu).
- **Boucles bornées** : 9, 9 et 64 itérations (`ADD2 #-1` puis `BNE`), et trois appels de `FUN_0005debe` avec R6 = `0x1000`. Pas de boucle possible.
- **Index bornés** :
  - mode : `(octet & 0x1F) >> 1` ≤ 15, sur une table de 16 octets ;
  - jeu : `< 294`, test non signé `BNC` ;
  - n° de matrice : `< 12` ;
  - emplacement : 0 à 3.
- **Largeur des champs de fiche** : Nikon écrit `+0x424` en octet (`STB` à `0xD93C6`) et `+0x422` en demi-mot (`STH` à `0xD93D0`) ; le crochet les lit en `LDUB` et `LDUH`.
- **Tables** : mode → emplacement `ff 00 01 02 03 ff…` ; réglages `04 01 01 00` × 4 ; bases `0x3FA400`, `0x3FB580`, `0x3FC700`, `0x3FD880` ; table des jeux conforme à F, 6 + F ou `0xFF` pour les 294 entrées.
- **Données** : coefficients ≤ 1 000 en valeur absolue, sans bit au-delà de 11 ; lignes de somme 512 ; YCbCr BT.601 ; secteurs neutres ; courbes croissantes de 0 (ou 5, 7) à 255. La zone est à `0xFF` autour (`0x3FA16C-0x3FA1FF`, `0x3FA366-0x3FA3FF`, `0x3FEA00-0x40FFFD`).
- **Patch N&B** (Ghidra, origine contre patché, `0xD7830-0xD78B0`) : seules des valeurs immédiates changent, et trois `EXTSB` deviennent `NOP` (`9FA0`). Longueurs conservées, aucun branchement à créneau autour.
- **Exécution en `0x3FA000`.** La zone est écrite par le flasheur et lue par Nikon (textes, tables en `0x2xxxxx-0x3Bxxxx`), et le FR n'a pas de protection d'exécution. Mais **aucun code Nikon du D200 n'est au-delà de `0x15CA56`** (2 697 fonctions). Sur le D200, exécuter du code à cette adresse serait une première : hypothèse forte, appuyée sur le D40, qui exécute du code ajouté en `0x3E8000` et `0x40F000`. La condition 1 rapproche le code de la zone de Nikon.

### 7. Textes du menu : dans les bornes (vérifié)

Contrôle sur la table française (`0x246600 + 4 × id`) : le créneau d'une chaîne va de son pointeur à celui de la chaîne id − 1.

| Id | Avant → après | Créneau (octets) | Caractères avant / après | Largeur px avant / après |
|---|---|---|---|---|
| 251 | Moins nette → Chrome | 24 | 11 / 6 | 113 / 71 |
| 252 | Saturée → Positive (repointé en `0x176600`) | 16 → 18 en zone libre | 7 / 8 | 71 / 74 |
| 253 | Plus saturée → FP4 | 26 | 12 / 3 | 112 / 32 |
| 217 | Portrait → HP5 | 18 | 8 / 3 | 71 / 36 |
| 254 | Noir et blanc → Tri-X | 28 | 13 / 5 | 118 / 48 |
| 508-520 | 13 lignes d'aide | 36 à 50 | ≤ créneau | maximum 244 (508) |

- Chaque nouvelle chaîne finit par `0xFFFF` dans son créneau, et le reste du créneau est à `0xFFFF`.
- Le pointeur suivant (id − 1) est inchangé. Dans la table française, **seul le pointeur 252 change**. Les 7 autres tables latines sont intactes.
- `0x176600` : `0250 026F 0273 0269 0274 0269 0276 0265 FFFF`, adresse paire, suivie de `0xFF`.
- Largeurs (police `0x2AE398`, deux-points de la police fixe = 11 px) : toutes sous les maximums d'usine, qui sont 164 px pour les 7 libellés (« Benutzerdefiniert ») et 265 px pour les lignes d'aide (anglais, id 519). Mes largeurs dépassent d'1 px celles de la doc ; c'est sans conséquence.
- Les ids 221 et 236 (Personnalisée), et les textes de l'écran de mise à jour (ids 1753, 1754 et 2342, lus par `FUN_0013a2b2`), sont inchangés.
- Hypothèse : rien n'a jamais dessiné une chaîne située hors du bloc de sa langue. Le traceur lit jusqu'à `0xFFFF`, et la doc affirme qu'aucun code ne calcule de longueur par différence de pointeurs ; je ne l'ai pas prouvé. Si le traceur ne savait pas la dessiner, l'effet resterait cosmétique et limité au sous-menu Optimiser l'image en français.

### 8. Reproductibilité et émulateur (vérifié)

- Original : `build/d200/origine/B2000201.BIN` est identique à l'octet près au `B2000201.bin` que j'ai réextrait du paquet `F-D200-V201W.exe` (RAR, `D200Update/`, fichiers datés du 02/09/2008), sha256 `b7cee24d…407d1`. La signature Authenticode du paquet est **valide** : l'empreinte SHA1 du PE recalculée (`de62ead4…5ee6`) est égale à celle qui est signée, `openssl smime -verify -noverify` répond « Verification successful », et le signataire est « NIKON CORPORATION » (VeriSign Class 3 Code Signing 2004). La chaîne de certificats n'est pas vérifiée (certificats expirés).
- `python3 -B patch.py patchs/d200-v1.json --sortie <temporaire>` : 37 patchs, 22 592 octets, CRC `6a7d`, sha256 **`402f00f5…de92c9`**, identique à `build/d200/v1`. `patch.py --self-test` : OK.
- `python3 -B emulateur/d200/d200emu.py --travail <temporaire> verifier` : **code de sortie 0**, 11 essais conformes. Le firmware combiné qu'il joue a le sha256 `402f…`, c'est donc bien le fichier relu.
  - a : 403 contrôles. b et b″ : 1 738. c et c′ : 157. d : 1 781, 0 échec.
  - Contre-épreuves b′ : 421 échecs ; d′ et d″ : 668 échecs chacune (la doc annonce 1 218 : écart de doc, sans effet).
  - Gardes : code 2.
  - Pile d'`isp_chargerPuce` : 52 octets au lieu de 40.

### 9. Retour arrière (point 6 de la demande)

**Ce qui est prouvé.**
- La voie de retour est le code de Nikon, intact : le constat 4 couvre la chaîne de mise à jour, le flasheur et sa copie au reset, `.data`, la signature, la version et la table CRC.
- Depuis les écrans de mise à jour et la chaîne `FUN_0009a680`, `FUN_0009a9fc`, `FUN_0013a2b2`, `FUN_00139ee0` et `FUN_000503ca`, la fermeture des appels directs parcourt 223 fonctions, sans atteindre aucune fonction modifiée ni aucune fonction de la chaîne d'image.
- Les crochets ne tournent que pour une image traitée, dans la tâche d'image.
- La version n'est pas comparée, donc l'original 2.01 est accepté par-dessus le V1 2.01.
- Différence avec le piège du D40 (« ces écrans appellent deux des fonctions détournées ») : ici, aucune fonction de menu n'est détournée.

**Ce qui reste hypothèse.**
- Appels indirects non couverts.
- Comportement réel de la puce d'image avec nos valeurs. Une erreur figerait la prise de vue, pas le menu.
- Chargeur de démarrage non lu.

**Si un rendu plante.**
1. Retirer la batterie et rallumer : au démarrage, rien n'appelle les crochets.
2. Ne pas déclencher. Si besoin, mettre Optimiser l'image sur Normale ; en mode 0, les crochets laissent passer, ce qui est vérifié dans l'émulateur (registres identiques à Nikon).
3. Si le sous-menu Optimiser l'image se comporte mal en français, passer la langue en anglais par le menu Configuration : la table anglaise est intacte.
4. Mettre la carte qui contient seulement l'original (sha256 `b7ce…`), puis Configuration › Version du firmware › mise à jour.

**Ce qui ne se rattrape pas.** Un flash qui échoue en cours d'écriture : coupure d'alimentation, ou le risque du constat 1. C'est la seule voie de brique identifiée.

### 10. Points mineurs

- Coût en temps : +86 600 instructions par chargement de la puce quand un rendu est actif, selon l'émulateur. Non mesuré sur le boîtier, et ce n'est pas une voie de brique.
- Pile : +12 octets dans `preglage_puce`, sur une tâche de 8 Ko (pas de `0x2000` entre deux entrées consécutives de la table des tâches, hypothèse de lecture).
- La langue du boîtier est supposée être le français (sélecteur 3, déduit) : dans une autre langue, les noms ne changent pas.
- Ids 217 et 251 à 254 : je n'ai pas cherché s'ils servent ailleurs que dans Optimiser l'image. Effet cosmétique seulement.

## Ce que je n'ai pas pu vérifier

- **Le câblage de WP# et l'identité de la puce flash du D200** (constat 1). Seule une photo de la carte ou une lecture d'identifiant (commande `0x90`, absente du firmware) le dirait.
- Le chargeur `0x0F0000-0x11FFFF` : il est absent du fichier (tout `0xFF`), et l'on ne sait pas s'il contrôle quelque chose ou s'il sait se rattraper après un flash raté. Aucune somme de contrôle de l'image n'existe dans l'en-tête (`0xEFBF0-0xEFBFF` : deux pointeurs puis `0xFF`). Le D40 a démarré avec 8 719 octets modifiés dans sa zone de code `0x40000-0xEFFFF`.
- Le démarrage complet et le dessin des menus du D200 par son propre code : l'émulateur du D200 ne démarre pas le firmware.
- Les appels indirects (tables de tâches, pointeurs de fonctions) au-delà des références que Ghidra a résolues.
- La version A et B réellement installée sur le boîtier, et sa langue.
- Le comportement de la puce d'image (bit de signe, temps de traitement) et le rendu à l'écran des nouveaux noms.

## Delta d’octobre : bloc des préréglages déplacé en `0x177000`

Relu en octobre 2026, à partir de (heure lue par `date`). Fichier : `build/d200/v1/B2000201.BIN` (daté 12:36:29), sha256 `bb052a6017e3ac922164f55e0c36e03bc647d8f2eb5d5df06ffa5f7b3b151d53`, CRC `47a1`, comparé à `402f…` et à l'origine. Comme précédemment, rien n'a été flashé ni modifié dans le projet, en dehors de ce rapport.

### Verdict après le delta : GO

La condition 1 est levée : plus aucun octet du V1 n'est écrit dans un secteur que Nikon n'a jamais programmé. Les conditions 2 à 4 font maintenant partie de la procédure (`d200-firmware-image.md` §10, étapes 1 à 4) : lire A 2.01 / B 2.01, batterie pleine, carte de retour prête, sha256 contrôlé sur la carte. Il suffit de la suivre telle quelle.

### D1. Le diff entre `402f…` et `bb05…` ne porte que sur le déplacement (vérifié)

- Référence `402f…` : la recette d'origine n'existe plus (`patchs/d200-preglages.json` a été réécrit). J'ai donc repris la copie que j'avais fabriquée par `patch.py` lors de la première relecture, dans mon dossier temporaire ; son sha256 a été recontrôlé (`402f…`).
- Ancien contre nouveau : 23 plages, 36 768 octets, tous dans quatre groupes :
  - l'ancienne zone `0x3FA000-0x3FE9FF`, revenue **identique à l'origine** (toute la place `0x3F72A8-0x40FFFD` est de nouveau à `0xFF`) ;
  - la nouvelle zone `0x177000-0x17B9C4` ;
  - 4 octets de crochets (`0x5DA2B-0x5DA2C`, `0xCDFB1-0xCDFB2`) ;
  - le CRC final (`6a7d` devient `47a1`).
- Liste des octets changés hors de ces groupes : vide. Origine contre nouveau : toujours 293 plages et 22 592 octets.
- **Le nouveau bloc est l'ancien, octet pour octet**, à 9 mots de 32 bits près, qui sont des adresses relogées (ancienne − `0x3FA000` + `0x177000`) :
  - 5 immédiats de `LDI:32` dans le code (`+0x14`, `+0x30`, `+0x7C`, `+0xB0`, `+0xC2` : tables `…210`, `…220`, `…210`, `…240`, `…230`) ;
  - les 4 pointeurs de la table des emplacements (`+0x230-+0x23F` : `0x177400`, `0x178580`, `0x179700`, `0x17A880`).
  - Emplacements, tables (mode, réglages, jeux) et signature `PREGLAGES-D200` : identiques.

### D2. Toutes les références visent la nouvelle zone (vérifié)

- Crochets (Ghidra) : `0xCDFAE` `LDI:32 #0x177000,R12` puis `CALL @R12` (`971C`) ; `0x5DA28` `LDI:32 #0x177060,R12` puis `971C`. Instructions voisines inchangées.
- Code déplacé, avec deux désassembleurs (Ghidra FR60 et nikon-firmware-tools) : 127 instructions, mêmes frontières, aucune forme `:D`. Face à l'ancien, seules 5 instructions diffèrent, et ce sont les 5 `LDI:32` de tables ; les branchements sont identiques en relatif.
- `LDI:32` du nouveau code : `0x177210`, `0x177220`, `0x177230`, `0x177240`, plus les constantes de Nikon (`0xCF86A`, `0xDCFF8`, `0x5DEBE`, RAM `0x97BE…`, puce `0x5001…`). Plus aucune en `0x3FAxxx`.
- Balayage du fichier entier, sur tout mot de 32 bits aligné sur 2 (immédiats et pointeurs) :
  - vers `0x3FA000-0x3FFFFF` : 1 424 dans l'origine, 1 424 dans le nouveau, **aucun ajouté**. Ce sont ceux de Nikon : la table des secteurs du flasheur en `0x1538E0`, plus des coïncidences dans les données. L'ancien V1 en avait 1 435, dont 11 à nous.
  - vers `0x177000-0x17B9FF` : 17 dans l'origine, 28 dans le nouveau, et les 11 ajoutés sont exactement les 2 crochets, les 5 `LDI:32` et les 4 pointeurs. Les 17 de l'origine ne sont pas des références : 11 sont dans le code et se lisent comme des paires d'instructions (`c38d` `LDI:8 #0x38,AC`, puis `LD @(AC,R1),R7` et `EXTSH R5` ou `MOV MDL,R0`), désassemblées par Ghidra depuis le début de `0x1291A4`, `0x144320`, `0x144AE0` et `0x1462F4`. Les 6 autres sont dans les données : 3 mal alignées (`0x166BEA`, `0x1720D6`, `0x3C2E9E`), donc illisibles comme mot par le FR, et 3 au milieu de données qui n'ont rien d'une table de pointeurs (`0x3C88C8`, `0x3F1F70`, `0x3F4DD8` : aucun voisin ne ressemble à une adresse).

### D3. La nouvelle zone était libre, et c'est un secteur que Nikon programme (vérifié, sauf mention)

- Origine : `0x177000-0x17B9FF` tout à `0xFF`, comme toute la place `0x1765EA-0x1CFFFF`. Marges du nouveau fichier : `0x176612-0x176FFF` et `0x17BA00-0x1CFFFF` à `0xFF`. Aucun chevauchement : le texte « Positive » occupe `0x176600-0x176611`, le bloc commence en `0x177000`, et la donnée de Nikon finit en `0x1765E9`.
- Le secteur `0x170000-0x17FFFF` contient 24 444 octets de Nikon et se trouve dans la plage `0x120000-0x1CFFFF`, que le flasheur efface et écrit à chaque mise à jour.
- Secteurs touchés par le V1 : `0x050000`, `0x0C0000`, `0x0D0000`, `0x170000`, `0x240000`, `0x250000`, `0x3B0000`, plus `0x400000` (le CRC, où Nikon écrit le sien). **Aucun n'est vierge dans l'origine.**
- `patch.py` refuse désormais un patch dans un secteur vierge. J'ai relu ce contrôle dans `controler_d200` : chaque secteur est arrondi à son début, 8 Ko en `0x3F0000-0x3FFFFF`, 64 Ko ailleurs. Essai : un patch en `0x3FC000` est refusé (code 1, « secteur 0x3fc000 sans aucun octet de Nikon »).
- Démarrage : le reset ne recopie que `.data` (`0x15387C-0x15C72B`) et le flasheur (`0x15C72C-0x15CA63`), et ce code est identique à l'origine. La nouvelle zone n'est ni recopiée ni lue au démarrage. La table de Nikon la plus proche, en `0x176590`, est celle des puissances de dix en double précision (au plus 9 entrées, bornées par l'exposant ; boucle lue dans le pseudo-C, référence en `0xCCE84`), suivie des puissances de deux jusqu'à `0x1765E9`. Hypothèse forte : aucune lecture de Nikon n'atteint `0x177000`, mais les accès par base et décalage calculés n'ont pas tous été suivis.
- Exécution : le code est désormais dans le même secteur que des données de Nikon, mais toujours au-delà de la dernière fonction de Nikon (`0x15CA56`). Ce point reste une hypothèse forte (§6), inchangée. L'émulateur l'exécute.

### D4. Acceptation, reproductibilité, émulateur (vérifié)

- Taille `0x3C0000` ; signature `Q220FirmwareSignature\0` (pointeur `0x16CAB0`) ; version `Ver.2.01 ` ; CRC du fichier entier calculé avec la table du boîtier = `0x0000` (fin `47a1`). Toutes les zones sensibles listées au constat 4 sont identiques à l'origine.
- `python3 -B patch.py patchs/d200-v1.json --sortie <temporaire>` : 37 patchs, 22 592 octets, CRC `47a1`, sha256 `bb052a60…151d53`, **identique à `build/d200/v1`**. `patch.py --self-test` : OK.
- `patchs/d200-preglages.json` (12:39:19) et `patch.py` (12:39:07) sont plus récents que le build (12:36:29). C'est sans effet : `d200-v1.json` reste exactement `d200-nb-trix.json` + `d200-noms.json` + `d200-preglages.json` (37 patchs, mêmes offset, avant et après), et la refabrication redonne `bb05…`.
- `python3 -B emulateur/d200/d200emu.py --travail <temporaire> verifier` : **code de sortie 0**, 11 essais conformes. Le combiné joué a le sha256 `bb05…`. Résultats : d, 1 781 contrôles et 0 échec ; contre-épreuves d′ et d″, 668 échecs chacune ; gardes, code 2 ; pile d'`isp_chargerPuce` 52 octets.

### D5. La doc désigne ce fichier et ce sha256, et eux seuls (vérifié)

- `d200-firmware-image.md` §10 : `build/d200/v1/B2000201.BIN`, CRC `47a1`, sha256 `bb052a60…`, « Seul fichier à flasher ». `402f…` et `389a…` y sont marqués périmés. La procédure inclut A 2.01 / B 2.01, la batterie, la carte de retour (sha256 `b7ce…`) et le contrôle du sha256 sur la carte.
- `d200-preglages.md` : §2 et §9, `bb05…` et aucun autre ; le combiné du cache y est marqué « Jamais à flasher ». Ce fichier du cache a d'ailleurs été refait (12:39) et vaut maintenant `bb05…` : il n'existe plus de fichier périmé à confondre.
- Recherche de `402f00f5`, `389a955b` et `d200-preglages-combine` dans la doc et les outils : ils n'y apparaissent que marqués périmés, ou comme dossier d'essai.
- Les « 8 secteurs touchés » du §10 correspondent à mes 7 secteurs plus celui du CRC.

### Ce qui reste hypothèse après le delta

Inchangé et sans lien avec le déplacement : l'exécution du code ajouté par le boîtier (au-delà de `0x15CA56`), le chargeur de démarrage, une coupure pendant l'écriture, le comportement de la puce d'image, et les appels indirects. Le seul risque de brique propre au patch (constat 1) a disparu.

## Sonde d’octobre : étage à secteurs de l'entrée Saturé

Relecture faite en octobre 2026 vers 15:45. Les chemins de cette section suivent le rangement d’octobre, à partir de `Photographie/logiciels/retro-ingenierie-boitiers/`. Les sections précédentes gardent les anciens chemins ; la table de passage est `correspondance-2026-10.tsv`.

- Fichier relu : `d200/build/sonde-secteurs/B2000201.BIN`, sha256 `3a959841159907c58530fd9b7a54ebff17507d9d7a55d99be6fdef3da58c6832`, CRC `c953`.
- Recette : `d200/patchs/d200-sonde-secteurs.json`.
- Base : la V1 `d200/build/v1/B2000201.BIN`, sha256 `bb052a60…151d53`.

### Verdict sur la sonde : GO

C'est la V1, modifiée sur 15 octets de données dans la table des secteurs de l'emplacement Positive (Saturé), plus le CRC. Aucun octet de code, aucun pointeur.

Ces valeurs ne sont lues que par une boucle de copie, puis écrites dans 10 registres de la puce d'image. Aucun calcul ne les utilise.

Le boîtier acceptera le fichier. La recette le refait à l'identique.

### S1. Diff contre la V1 : 15 octets dans la table Saturé, plus le CRC (vérifié)

La comparaison octet par octet des deux fichiers (même taille, `0x3C0000`) trouve 17 différences :
- 15 entre `0x17866A` et `0x1786E3` ;
- 2 en `0x40FFFE-0x40FFFF`, le CRC, qui passe de `47a1` à `c953`.

La zone `0x17866A-0x1786E9` correspond à l'emplacement 1 (`0x178580`), décalage `+0xEA` : ce sont ses 64 demi-mots de secteurs. Le diff touche 10 de ces demi-mots, décodés en signe et grandeur (bit `0x200`) :

| Secteur | Bloc 1 | Bloc 2 | Bloc 3 | Bloc 4 | Effet annoncé |
|---|---|---|---|---|---|
| 0 | `0x17866A` : 256 → 0 | 0 | 0 | `0x1786CA` : 256 → 0 | gris |
| 4 | `0x178672` : 256 → 128 | 0 | 0 | `0x1786D2` : 256 → 128 | saturation × 0,5 |
| 8 | `0x17867A` : 256 → 181 | `0x17869A` : 0 → −181 (`0x02B5`) | `0x1786BA` : 0 → 181 | `0x1786DA` : 256 → 181 | rotation de 45° (181 / 256 = cos 45°, déterminant 0,9998) |
| 12 | `0x178682` : 256 → 384 (`0x0180`) | 0 | 0 | `0x1786E2` : 256 → 384 | saturation × 1,5 |

Les 12 autres secteurs restent neutres (256, 0, 0, 256).

**Ce qui n'a pas changé**, relu octet par octet :
- le reste de l'emplacement 1 : matrices, YCbCr, courbe ;
- les emplacements 0, 2 et 3, dont les secteurs sont neutres ;
- le code `0x177000-0x17716B` ;
- les tables `0x177200` ;
- les deux crochets ;
- les pointeurs de signature et de version.

**Lien entre l'entrée Saturé et cet emplacement.** La table `0x177210` donne `ff 00 01 02 03`, donc le mode 2 (Saturé) pointe vers l'emplacement 1. Son adresse, lue en `0x177234`, vaut `0x00178580`.

**La recette.** Elle compte 37 patchs, comme `d200-v1.json`. Un seul diffère : le n° 34 (offset `0x128580`, emplacement 1), et seulement par son champ `apres`, sur ces 15 octets. Les champs `avant` et `offset` sont identiques.

### S2. Ces valeurs ne peuvent rien provoquer de grave (vérifié côté code ; hypothèse forte côté puce)

**Le format.** Aucun demi-mot des quatre emplacements n'a de bit au-dessus de `0x3FF`. Les grandeurs valent 0, 128, 181 et 384, toutes au plus égales à 511.

**Une seule lecture.** Dans `preglage_puce`, la boucle `0x177102-0x17711A` fait 64 fois `LDUH @R3,R0` puis `STH R0,@R5`. Elle lit à l'emplacement + `0xEA` (`R3`) et écrit à partir de `0x5001E400` (`R5`), avec `R6` = `0x40` comme compteur. Ce code est identique à la V1 (désassemblé dans le fichier de la sonde).
- La valeur n'est ni additionnée, ni multipliée, ni divisée.
- Elle ne sert pas d'indice et ne décide d'aucun saut. Un zéro ou 384 ne peut donc causer ni division par zéro, ni débordement de registre du processeur, ni accès hors table.
- Elle ne passe ni par la fiche de prise de vue, ni par la RAM : ni l'EXIF ni un autre code de Nikon ne la voient.

**Personne ne relit ces registres.** Nikon écrit les mêmes registres de la même manière, dans `isp_chargerPuce` (`0x5D85C-0x5D8CE`) : quatre boucles `LDUH`/`STH` de 16 demi-mots, base `0x50010000` + `0xE400`, `E420`, `E440`, `E460`. J'ai balayé tout le fichier à la recherche de constantes qui visent `0x5001E000-0x5001E4FF` :
- en `LDI:32` : seule la nôtre, en `0x17710A` ;
- en `LDI:20`, décalages `0xE400-0xE47F` : seules ces quatre-là.

Aucun code de Nikon ne relit donc ces registres par une constante. Les adresses calculées n'ont pas été suivies.

**Côté puce, ce qui a déjà servi :**
- **0 sur la diagonale** : c'est la sonde 1 du D40 (t1 = t4 = 0), flashée en octobre. Le boîtier a démarré et a pris 26 photos (`d40/JOURNAL.md`).
- **128** : c'est la sonde 2 du D40 (table 2 = 128 partout), flashée en octobre elle aussi. Les diagonales de Nikon sur le D200 descendent à 170.
- **−181 en terme croisé** : Nikon écrit déjà des termes croisés négatifs avec le bit `0x200`, jusqu'à −96 (`d200-choix-des-tables.md` §3.4). 181 sort de cette plage mais reste sous 256.
- **384 (× 1,5) n'a aucun précédent.** Nikon ne dépasse jamais 256 sur ses 294 jeux, et les sondes du D40 non plus. Le champ a au moins 9 bits de grandeur, puisque le neutre 256 (`0x100`) en a besoin, et `0x180` y tient.

Si la puce lisait cette valeur autrement (écrêtage, repli), l'effet resterait dans les pixels du secteur 12 : une couleur fausse ou saturée sur les photos en Saturé.

Hypothèse forte : un coefficient d'un étage de calcul fixe ne peut ni bloquer la puce, ni atteindre la flash ou le code. De plus, ces registres sont réécrits à chaque vue.

**Portée.** Seule l'entrée Saturé est touchée. Les autres entrées se comportent comme la V1, et rien ne s'exécute au démarrage (constat 3 inchangé).

### S3. Acceptation, reproductibilité, émulateur (vérifié)

**Acceptation.**
- Taille `0x3C0000`.
- Signature `Q220FirmwareSignature\0`, par le pointeur `0x16CAB0` lu en `0x9FBF4`.
- Version `Ver.2.01 `.
- CRC16 XMODEM du fichier entier = `0x0000` (fin `c953`).
- Hors des 15 octets et du CRC, tout est identique à la V1, donc toutes les zones sensibles du constat 4 le sont aussi.

**Reproductibilité.**
- `python3 -B d40/patch.py d200/patchs/d200-sonde-secteurs.json --sortie <temporaire>` donne 37 patchs, 22 592 octets changés, CRC `c953` et sha256 `3a959841…6832`. `cmp` le trouve **identique au fichier de `d200/build/sonde-secteurs/`**.
- `controler_d200` passe : aucun secteur vierge. Le diff touche deux secteurs : `0x170000`, qui porte 24 444 octets de Nikon, et `0x400000`, celui du CRC, où Nikon écrit le sien.
- `patch.py --self-test` : code 0.

**Émulateur.**
- `python3 -B d200/emulateur/d200emu.py --travail <temporaire> verifier` sort avec le **code 0**, 11 essais conformes. Attention : il joue le combiné refait depuis les recettes de la V1 (sha256 `bb05…`), pas la sonde.
- Sur la sonde elle-même, `scenario preglages --firmware <sonde>` exécute tout sans arrêt de garde : 1 781 contrôles et **40 écarts, tous attendus**. Ce sont les 10 registres `5001E400`, `E408`, `E410`, `E418`, `E430`, `E450`, `E460`, `E468`, `E470` et `E478`, dans les 4 cas Positive : ensoleillé, incandescent et fluo en sRGB, incandescent en Adobe RGB. Chaque écart porte la valeur de la sonde, par exemple `E430` = `0x02B5` et `E418` = `0x0180`.
- Chrome, FP4, HP5 et les cas rendus par Nikon sont conformes.

**Retour arrière.** La chaîne de mise à jour est identique, octet pour octet, à celle de la V1. On revient en flashant `d200/build/v1/B2000201.BIN` (`bb05…`) ou l'origine (`b7ce…`) depuis le même menu.

### Points mineurs (sans effet sur les octets)

- Dans la recette de la sonde, le `texte` du patch n° 34 dit encore « secteurs neutres », copié de la V1. La `description` de la recette, elle, annonce bien la sonde.
- La doc ne dit pas la même chose sur le flash de la V1 : `d200/recherche/d200-firmware-image.md` la donne encore « prête, jamais flashée » (l. 11 et 351), alors que `d200-preglages.md` (l. 162) décrit des mesures « après le flash ». Je n'ai rien corrigé.
- Ce que `d200-preglages.md` (l. 162) dit de la sonde est exact : 15 octets, valeurs (181, −181, 181, 181), CRC `c953`, sha256, 40 écarts dans l'émulateur.

### Ce qui reste hypothèse pour la sonde

- Comment la puce interprète 384 : au pire, l'image est touchée ; le boîtier, non.
- Les accès aux registres par adresse calculée.
- Le reste est inchangé depuis le delta : exécution du code ajouté au-delà de `0x15CA56`, chargeur de démarrage, coupure pendant l'écriture.

## Sonde 2 d’octobre : rampe de gain sur les secteurs de Saturé

Relecture faite en octobre 2026 vers 16:35.

- Fichier relu : `d200/build/sonde-secteurs-2/B2000201.BIN` (16:15:30), sha256 `91bbd9e36819b198a7e3083703df28ef79ff71d295c5171be24c69d19a8cb6e8`, CRC `e07e`.
- Recette : `d200/patchs/d200-sonde-secteurs-2.json` (16:15:30).
- Comparé à la V1 (`bb05…`) et à la sonde 1 (`3a95…`).

### Verdict sur la sonde 2 : GO

Par rapport à la V1, seuls changent les 64 octets des secteurs de l'emplacement Positive (Saturé) et le CRC.

Toutes les valeurs sont positives, inférieures au neutre 256, sans terme croisé. Elles restent dans ce que les sondes du D40 ont déjà fait passer, et sont moins risquées que la sonde 1 : ni 384, ni valeur négative.

Acceptation, refabrication et émulateur sont conformes.

### T1. Diff : la table des secteurs de Saturé et le CRC, rien d'autre (vérifié)

**Contre la V1** : 66 octets, de `0x17866A` à `0x1786E9` puis `0x40FFFE-0x40FFFF`. Aucun octet hors de cette table et du CRC.

**Contre la sonde 1** : 63 octets, tous dans la même table et le CRC (`c953` → `e07e`).

Comme pour la sonde 1, rien d'autre ne bouge :
- le code `0x177000-0x17716B` et les tables `0x177200` sont identiques. La table mode → emplacement vaut toujours `ff 00 01 02 03`, et l'adresse de l'emplacement 1, en `0x177234`, vaut toujours `0x00178580` ;
- les crochets, les pointeurs de signature et de version, les emplacements 0, 2 et 3 (secteurs neutres), ainsi que les matrices, le YCbCr et la courbe de l'emplacement 1, sont identiques.

**La recette.** Elle compte 37 patchs, comme `d200-v1.json`. Seul le n° 34 (offset `0x128580`, emplacement 1) diffère : par son champ `apres`, sur 64 octets entre `0x17866A` et `0x1786E9`, et par son `texte`, qui annonce désormais la rampe.

### T2. Valeurs : rampe de 64 à 244, sans signe ni terme croisé (vérifié côté code ; hypothèse forte côté puce)

Décodage en signe et grandeur (bit `0x200`) des 64 demi-mots :
- **blocs 1 et 4** (diagonale) : secteur s = 64 + 12 s, soit 64, 76, 88, … 232, 244 (`0x0040` à `0x00F4`). Le gain de chroma va donc de 0,25 à 0,95 ;
- **blocs 2 et 3** : 0 partout.

Aucun bit au-dessus de `0xFF` : pas de bit de signe, pas de bit `0x100`, rien au-delà de `0x3FF`.

**Côté code.** Le chemin est celui de la sonde 1 (S2) : la seule lecture est la boucle `LDUH`/`STH` de `0x177102-0x17711A`, vers `0x5001E400-0x5001E47F`. Il n'y a aucun calcul sur la valeur, et aucun code de Nikon ne relit ces registres par une constante.

**Côté puce, ce qui a déjà servi :**
- toute la plage 0 à 256 sur une table : sonde 2 du D40, rampe 256 · j / 15, flashée en octobre ; le boîtier a démarré et pris ses photos (`d40/JOURNAL.md`) ;
- le gain 0 : sonde 1 du D40 ;
- 128 : sonde 2 du D40, en terme croisé ;
- chez Nikon sur le D200 : diagonales de 170 à 256.

Les valeurs de la sonde 2, de 64 à 244, sont toutes dans cette enveloppe. Au pire, une couleur différente de l'attendu sur les photos en Saturé. Rien n'atteint le code ni la flash.

### T3. Acceptation, reproductibilité, émulateur (vérifié)

**Acceptation.**
- Taille `0x3C0000`.
- Signature `Q220FirmwareSignature\0`, par le pointeur `0x16CAB0`.
- Version `Ver.2.01 `.
- CRC16 XMODEM du fichier entier = `0x0000` (fin `e07e`).
- Hors de la table et du CRC, tout est identique à la V1, zones sensibles du constat 4 comprises.

**Reproductibilité.** La recette existe dans `d200/patchs/`.
- `python3 -B d40/patch.py d200/patchs/d200-sonde-secteurs-2.json --sortie <temporaire>` donne 37 patchs, CRC `e07e` et sha256 `91bbd9e3…a8cb6e8`. `cmp` le trouve **identique au fichier de `d200/build/sonde-secteurs-2/`**.
- `controler_d200` passe.
- La recette de la sonde 1, retouchée (le `texte` du patch n° 34, mon point mineur), redonne toujours `3a95…`.

**Émulateur.** `d200emu.py --firmware <sonde 2> scenario preglages` s'exécute sans arrêt de garde : 1 781 contrôles et **128 écarts, tous attendus**.
- Ce sont les 32 registres de diagonale, `5001E400-5001E41E` et `5001E460-5001E47E`, dans les 4 cas Positive : ensoleillé, incandescent et fluo en sRGB, incandescent en Adobe RGB.
- Chacun porte la valeur de la rampe, de `0x0040` à `0x00F4`.
- Les termes croisés (`E420-E45E`) restent à 0 et sont conformes, comme Chrome, FP4, HP5 et les cas rendus par Nikon.

**Retour arrière.** Inchangé : même chaîne de mise à jour, puis la V1 (`bb05…`) ou l'origine (`b7ce…`) depuis le même menu.

### Ce qui reste hypothèse pour la sonde 2

Les mêmes points que pour la sonde 1 : les accès aux registres par adresse calculée, l'exécution du code ajouté au-delà de `0x15CA56`, le chargeur de démarrage, une coupure pendant l'écriture.

La lecture d'une valeur au-delà de 256 ne se pose plus ici : aucune n'en dépasse.

## Sonde 3 d’octobre : numéro de secteur codé en binaire, Chrome et Positive

Relecture faite en octobre 2026 vers 16:50.

- Fichier relu : `d200/build/sonde-secteurs-3/B2000201.BIN` (16:45:43), sha256 `7b40a5d7a83cb85e9d967be1fdfe76a516118b927d52aa57c4a525daa549b155`, CRC `2921`.
- Recette : `d200/patchs/d200-sonde-secteurs-3.json` (16:45:43).
- Comparé à la V1 (`bb05…`), à la sonde 1 (`3a95…`) et à la sonde 2 (`91bb…`).
- La note de l'auteur (`d200-sondes-secteurs.md`, section « Sonde n° 3 ») a servi de point de départ. Chaque affirmation ci-dessous est refaite sur les octets.

### Verdict sur la sonde 3 : GO

Seuls changent les 128 octets de secteurs des emplacements Chrome et Positive, et le CRC.

Les valeurs négatives sont codées comme Nikon les écrit lui-même dans la puce : signe et grandeur, bit `0x200`.

Les grandeurs, au plus 241, restent dans l'enveloppe des sondes 1 et 2, qui ont été flashées puis ont produit des photos.

Acceptation, refabrication et émulateur sont conformes.

### U1. Diff : deux tables de secteurs et le CRC, rien d'autre (vérifié)

Zones permises : `0x1774EA-0x177569` (Chrome, `0x177400` + `0xEA`), `0x17866A-0x1786E9` (Positive, `0x178580` + `0xEA`) et le CRC.

| Contre | Octets différents | Chrome | Positive | CRC | Hors de ces zones |
|---|---|---|---|---|---|
| V1 `bb05…` | 226 | 112 | 112 | 2 | aucun |
| sonde 1 `3a95…` | 221 | 112 | 107 | 2 | aucun |
| sonde 2 `91bb…` | 194 | 112 | 80 | 2 | aucun |

Les 224 octets annoncés, plus le CRC (`47a1` → `2921` depuis la V1), sont exacts.

**Ce qui n'a pas changé** :
- le code ;
- la table mode → emplacement (`ff 00 01 02 03`) ;
- les adresses des emplacements en `0x177230` (`0x177400`, `0x178580`, `0x179700`, `0x17A880`) ;
- les crochets ;
- les matrices, le YCbCr et les courbes de tous les emplacements ;
- les secteurs de FP4 et HP5, qui restent neutres.

**La recette.** Elle compte 37 patchs, comme `d200-v1.json`. Seuls diffèrent :
- le n° 33 (`0x127400`, Chrome) : `apres` sur 112 octets entre `0x1774EA` et `0x177569`, et `texte` ;
- le n° 34 (`0x128580`, Positive) : `apres` sur 112 octets entre `0x17866A` et `0x1786E9`, et `texte`.

### U2. Valeurs, négatifs et termes croisés (vérifié côté code et format ; puce : précédents réels)

**Décodage.** Les 128 demi-mots modifiés ne prennent que quatre grandeurs : 241, 108, 88 et 39.
- 241 = 256 · cos 20°, 88 = 256 · sin 20°, et 108 et 39 valent 0,45 fois ces deux valeurs.
- Chaque secteur est donc soit une rotation de ±20° de gain 1,00, soit la même rotation de gain 0,45.
- Positive : le bit 0 du numéro de secteur règle le gain, le bit 1 la rotation.
- Chrome : le bit 2 règle le gain, le bit 3 la rotation.

**Codage des négatifs.** Les négatifs valent `0x0258` (−88) et `0x0227` (−39) : bit de signe `0x200` plus la grandeur, sans complément à deux. Aucun demi-mot n'a de bit au-dessus de `0x3FF`, et aucun « zéro négatif » `0x0200` n'apparaît.

**Le même codage que Nikon.** L'émulateur relève les valeurs que le firmware d'origine écrit lui-même dans les registres de termes croisés (contre-épreuve d′ de `verifier`, firmware `b7ce…`) :
- bloc 2 (`E420-E43E`) : de −94 à +3 ;
- bloc 3 (`E440-E45E`) : de −96 à +1 ;
- toutes en signe et grandeur : `0x025E`, `0x0260`, et **`0x0258`, exactement notre −88** ;
- diagonales de 170 à 256.

Notre table est copiée de la flash vers les registres sans conversion, par la boucle `LDUH`/`STH` de `0x177102-0x17711A`. Elle doit donc être déjà au format des registres, et elle l'est. Aucun code ne fait de calcul sur ces valeurs (S2).

**Précédents dans la puce du D200.**
- La sonde 1 contenait 0, 128, 181, −181 en terme croisé et 384. D'après `d200/images/2026-10-sonde-secteurs/LISEZMOI.txt`, elle a été flashée. Une photo en Saturé y figure : JPEG pleine taille 3872 × 2592, `ImageOptimization` = Vivid, prise en octobre:58 (exiftool).
- La sonde 2 (rampe de 64 à 244) a donné de même un JPEG Vivid, pris:26.

La sonde 3 reste dans cette enveloppe : |v| ≤ 241 sur la diagonale et 88 en terme croisé, contre 384 et 181 pour la sonde 1. Seule nouveauté : les secteurs non neutres de Chrome, dont les registres sont les mêmes que ceux de Positive.

**Effet attendu.** Des couleurs fausses en Moins net et en Saturé tant que la sonde 3 est en place. Les autres entrées sont inchangées.

### U3. Acceptation, reproductibilité, émulateur (vérifié)

**Acceptation.**
- Taille `0x3C0000`.
- Signature `Q220FirmwareSignature\0`, par le pointeur `0x16CAB0`.
- Version `Ver.2.01 `.
- CRC16 XMODEM du fichier entier = `0x0000` (fin `2921`).
- Hors des deux tables et du CRC, tout est identique à la V1.

**Reproductibilité.** `python3 -B d40/patch.py d200/patchs/d200-sonde-secteurs-3.json --sortie <temporaire>` donne 37 patchs, CRC `2921` et sha256 `7b40a5d7…549b155`. `cmp` le trouve **identique au fichier de `d200/build/sonde-secteurs-3/`**. `controler_d200` passe.

**Émulateur.** `d200emu.py --firmware <sonde 3> scenario preglages` s'exécute sans arrêt de garde : 1 781 contrôles et **704 écarts**, tous dans `5001E400-5001E47F`.
- Il y a 64 écarts par chargement, sur 11 chargements :
  - 5 cas Chrome : ensoleillé, incandescent et ombre en sRGB, ensoleillé en Adobe RGB, balance auto ;
  - 4 cas Positive ;
  - les 2 chargements Chrome du cas « deux photos ».
- Chaque écart porte exactement la valeur de la table de la sonde pour son emplacement.
- FP4, HP5 et les rendus de Nikon : aucun écart.

**Retour arrière.** Inchangé : la V1 (`bb05…`) ou l'origine (`b7ce…`), depuis le même menu.

### Ce qui reste hypothèse pour la sonde 3

- Les accès aux registres par adresse calculée.
- L'exécution du code ajouté au-delà de `0x15CA56` (déjà faite par le boîtier avec les sondes 1 et 2, d'après leurs photos).
- Le chargeur de démarrage.
- Une coupure pendant l'écriture.
