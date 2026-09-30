# Revue critique du firmware V1 (processeur B)

Revue indépendante, en lecture seule, avant le premier flash sur le boîtier (octobre 2026, d'après `date`). Le but est de chercher ce qui peut mal tourner sur le vrai D40, pas de confirmer que tout va bien.

**Fichiers revus**
- Original : `firmware/BD400111.bin` (3 997 696 octets, chargé à 0x40000 : offset = adresse − 0x40000).
- Build à deux crochets : `scratchpad/v1-code/build-nettete/BD400111.BIN`, sha256 `81b4b4fe…3f7687`. Revu en entier : diff octet par octet contre l'original et désassemblage de tout le code ajouté.
- Build aux vraies recettes, avec les tons : `scratchpad/verif-v1/vraies/BD400111.BIN`, sha256 `d3b85f5d8b15f4cb5a7408d0d4b42402a8a5643d158b11026040242719cac539`, CRC du fichier = 0. Revu par différence avec le build précédent. Les écarts se limitent à quatre zones :
  - la fin du crochet 2 (0x3F30E3–0x3F3138) ;
  - `tbl_reglages`, passée à 4 octets par emplacement (0x3F324A) ;
  - les données des 5 emplacements (0x3F3400–0x3FE578) ;
  - le CRC.
- **Non revu** : l'étape 5 « onglets en bandeau » (`outils/pipboy.py`, modifié). `patchs/pipboy-5-onglets.json` n'existe pas encore. Seule son architecture a été lue (§6.3).

**Légende** : **[V]** = vérifié dans le désassemblage ou les octets ; **[H]** = hypothèse (forte quand elle est indiquée comme telle).

## Synthèse

| # | Point | Verdict | Preuve courte | Correction proposée |
|---|---|---|---|---|
| 1 | Zones écrites | **OK** | Code et tables ajoutés dans de la place libre d'origine (0xFF), sans aucune référence Nikon. Modifications en place sur des données que Nikon lit déjà. Tout est dans les plages programmées par le flasheur. [V] | Rien. |
| 2 | Flash écrite à l'exécution | **OK** | Le boîtier écrit seulement 0x160000, 0x180000/0x190000, 0x1A0000, 0x410000/0x420000 et 0x430000. Nos zones 0x3E8000–0x40FFFF ne sont jamais effacées. [V] | Rien. |
| 3 | Persistance du bloc 10 (0x83CED24E/F) | **Risque faible** | Aucune somme de contrôle, longueur 0xC inchangée, octets jamais touchés par Nikon. [V] Programme et Si trop sombre survivent à « Réinitialiser ». [H forte] | Dire dans le tuto que « Réinitialiser » ne remet pas Programme ni Si trop sombre à zéro, ou les y ajouter. |
| 4a | Crochets : pile, registres, créneaux, largeur | **OK** | RP et R8 sauvés et rendus. Aucun créneau de délai dans le code ajouté. Écritures STH 16 bits comme chez Nikon. Crochet 2 avec les tons : ST 32 bits sur des variables que Nikon lit en 32 bits. [V] | Rien. |
| 4b | Crochet 1 : état lu dans des globales | **Risque** | L'indice de matrice `0x83EB3AB4` et le chemin spécial `0x83EB3D3C` sont lus au moment du chargement de la puce, pas dans la fiche de la photo. Si le développement est différé (rafale, retouche), ils peuvent venir d'une autre photo. [V] pour le code, [H] pour l'effet visible. | Tirer l'indice de la fiche, ou le ranger dans la fiche au moment de `image_parametres`. Ajouter le test émulateur §8.1. |
| 4c | Bornes des matrices | **Risque faible** | Le maximum vaut 995 (vraies recettes), contre 969 chez Nikon. La borne du registre est 1023. Aucun bit hors du masque 0x7FF. [V] Pas de saturation interne connue entre 969 et 1023. [H] | Garder la borne d'ajustement à ±1000 et contrôler la première photo de chaque rendu. |
| 5 | Chemins oubliés | **Risque faible** | Scènes, Auto, Nikon et Personnalisé : rendu d'usine. [V] Retouches (D-Lighting, Recadrer, Superposition) : le rendu V1 se réapplique en suivant le mode de la fiche, ce qui donne une double application possible. [H] | Test boîtier : D-Lighting sur un JPEG V1 (§5). Si les couleurs changent, exclure les retouches du crochet. |
| 6a | Voie de secours | **Risque** | Le code de mise à jour, le flasheur, le CRC, la signature et les écrans 105 et 106 sont inchangés. [V] Mais l'écran 105 n'est jamais atteint dans un scénario. Si un écran Pip-Boy plante à l'entrée, l'onglet mémorisé peut rendre CONFIG inatteignable. [H] | Scénario émulateur jusqu'à CONFIG › Version du firmware › Oui. Laisser le menu sur cet écran avant de flasher. Garder une carte avec l'original. |
| 6b | Étape 5 sur la voie de secours | **Risque (non revu)** | `ecran105_action` et `ecran106_action` appellent `FUN_00149220`. `ecran106_action` appelle aussi `FUN_0007d72a`. Ce sont deux des 11 fonctions que l'étape 5 détourne. [V] | Ne pas flasher l'étape 5 avant un scénario qui passe 105 et 106 jusqu'à la confirmation. Mieux : rendre la main au code Nikon d'origine sur les écrans 105 et 106. |
| 7a | CRC, taille, signature | **OK** | CRC16 XMODEM du fichier = 0. Taille 0x3D0000. « Q330FirmwareSignature » inchangée. [V] | Rien. |
| 7b | Autres langues, modes Simple et Mon menu | **Risque faible** | Hors du français, les libellés sont recyclés. Les aides 141–144 pointent sur des textes bien formés. [V] Mode Mon menu : l'entrée est retirée de la liste. [V] Effet au démarrage non testé. | Scénario en anglais et en mode Mon menu (§8.3, §8.4). |
| 7c | Procédure de build | **Risque** | `build/v1` (CRC 95c6) est périmé : 115 octets d'écart, pas de crochet 2. `patchs/preglages-v1.json` n'a pas le crochet 2. Les tons et l'étape 5 sont en cours. Plusieurs BIN circulent dans le scratchpad. [V] | Un seul build final. Noter son sha256. Rejouer tous les scénarios sur ce fichier exact. Flasher par étapes (§6.4). |

Aucun point bloquant trouvé dans ce qui a été revu.

## 1. Zones écrites

**Diff du build à deux crochets contre l'original** : 56 plages [V].

**Place libre**. Ces plages valaient toutes 0xFF dans l'original [V] :
- 0x3E8000–0x3E82B1 : code des menus Pip-Boy ;
- 0x3EA000–0x3EC4D9 et 0x3ED000–0x3F2904 : textes français relogés, glyphes ;
- 0x3F3000–0x3F312B : les deux crochets ;
- 0x3F3200–0x3F3251 : tables ;
- 0x3F3400–0x3FE57E : 5 emplacements de 0x2380 octets ;
- 0x400000–0x40351F : glyphes de valeurs.

Les données d'origine finissent à 0x3E66EB, sur la fin d'un JPEG (`ff d9`) [V]. Le code d'origine ne contient aucune LDI:32 vers 0x3E7000–0x40FFFF, à trois exceptions près, qui ne sont pas des accès à cette zone [V] :
- les masques et indicateurs 0x3FF000 et 0x400000 ;
- les adresses de commande de la flash.

**Modifications en place**. Nikon lit déjà toutes ces données, ce qui est voulu [V].

Code et constantes :
- 0x4B5B5–7 : constante du crochet 1 ;
- 0x31B233–5 : constante du crochet 2 ;
- 0x9B177–9 : pointeur D du français, 0x2B124C → 0x3EA07C ;
- 0x132090 et 0x13218C : navigation des onglets ;
- 0x143889 et 0x143899 : LDI #6 → #7 ;
- 0x146CC7 et 0x146DE1 : CMP #5 → #4.

Données :
- palettes 0xD87C3 et 0x1B0006–0x1B019F ;
- `TBL_N` 0x155BDD–0x155CB3 ;
- `tblEcrans` (0x1566F1, 0x1567C9, 0x156979, 0x15698C–0x1569BB) ;
- menus 0x1598DB–0x15BB3B ;
- table des langues 0x15C7D9–0x15C7DF (pointeurs B et C du français) ;
- descripteur de planche 0x1B01D9 et listes de tuiles 0x1B0697–0x1B1745 ;
- glyphes 0x20FF8C–0x2107FB.

Les anciens textes français 0x2B1D33–0x2B6496 sont réécrits, mais plus rien ne les lit une fois le pointeur 0x9B177 déplacé [V].

**Zone de menus recyclée 0x15B920–0x15BC3F**. C'est une zone de données initialisées : elle est copiée en RAM au démarrage, à +0x83B8BAEC. Ses lecteurs [V] :
- `ecran072/073/074_entree` : écrans recyclés ou inaccessibles ;
- `FUN_00146f44` : comparaisons d'adresses pour le crayon ;
- `FUN_00134788` et `ecran057_entree` : ils écrivent aux positions 0x15BC02 et 0x15BC30 de cette zone, hors des données Pip-Boy.

**Plages programmées par le flasheur** (CARTE §3) : 0x40000–0xEFFFF, 0x120000–0x15FFFF, 0x1B0000–0x40FFFF, et 0x160000 sous condition. Toutes nos zones y sont [V]. Aucun patch ne tombe dans 0xF0000–0x11FFFF ni dans 0x160000–0x1AFFFF [V]. L'étape 5 (code 0x40C000, données 0x40D000–0x40FFFD) reste dans 0x1B0000–0x40FFFF, juste avant le CRC à 0x40FFFE [V, d'après les constantes de `pipboy.py`].

`patch.py` complète par des espaces un « après » plus court que l'« avant ». Les 143 patchs de `v1.json` ont des longueurs égales, donc rien n'est complété par erreur [V].

## 2. Flash écrite à l'exécution

**Commandes de flash**. Les séquences de type AMD (0x400AAA/0x400554 et 0x4AAAA/0x45554) n'existent que dans le bloc du flasheur 0x15C000–0x15DFFF. Elles sont copiées et exécutées en RAM [V]. Les trampolines RAM ne sont appelés que par les deux sites d'origine [V].

**Écritures à l'exécution** [V] :
- 0x160000 : fond d'écran ;
- 0x180000 et 0x190000 : journal des réglages ;
- 0x1A0000 : 0x2468 octets, sites 0x8F67C et 0xA91FC ;
- 0x410000 et 0x420000 : second journal (données 0x8385D900, table 0xD5588) ;
- 0x430000 : 0x64 octets, site 0x9322C.

**Secteurs**. Ils font 64 Ko, sauf pour (adr & 0x3F0000) == 0x3F0000 : 8 secteurs de 8 Ko (table 0x83CE0154/0x83CE0174) [V]. Aucun effacement ne vise 0x3E0000–0x40FFFF [V]. Les crochets et les emplacements (0x3F3000–0x3FE57E) sont dans les secteurs de 8 Ko, qui ne sont jamais effacés hors mise à jour [V]. L'étape 5 est dans le secteur 0x400000–0x40FFFF. Le secteur écrit à l'exécution le plus proche est 0x410000, distinct [V].

**Concurrence**. Les écritures se font sous `loc_cpu`. Aucune tâche ne tourne pendant ce temps, donc les crochets ne peuvent pas lire la flash en cours de programmation [V].

**Mise à jour**. Le flasheur efface tout, puis programme. Il finit par 0x40000–0xEFFFF, le code [V]. Une coupure en cours de mise à jour fait le même dégât qu'avec un firmware Nikon : V1 n'y change rien.

## 3. Persistance de Programme et Si trop sombre (bloc 10)

**Format du journal** [V] :
- enregistrements `{id u16, longueur u16, données}`, validés par 0xAA55 avec un compteur de génération ;
- **aucune somme de contrôle des données** ;
- un enregistrement n'est relu que si sa longueur égale celle de `tblBlocsReglages`. Celle du bloc 10 vaut 0xC, inchangée ;
- un bloc modifié se détecte par comparaison octet par octet entre la RAM et la flash. Changer 0x24E ou 0x24F déclenche donc bien une réécriture.

**Octets inutilisés par Nikon** [V]. Aucun accès à 0x83CED24E ni à 0x83CED24F, d'après trois recherches :
- grep du pseudo-C ;
- suivi des registres chargés avec une base entre 0x83CE9000 et 0x83CED253, sur 600 instructions. Témoin positif : 18 accès retrouvés sur des octets voisins connus ;
- appels qui passent un pointeur dans 0x83CED000–0x83CED24F : ce ne sont que des copies de noms de 5 octets.

**« Réinitialiser »**. Les remises à zéro Nikon (`FUN_001437ea`, `FUN_00143478`) ne touchent pas ces deux octets. Programme et Si trop sombre gardent donc leur valeur [H forte : lu dans le code, pas exécuté]. C'est un écart d'interface, pas un danger.

**Premier démarrage** [V] : la zone est dans le BSS (0x83CE9018–0x83D02147), mis à zéro au démarrage. Le code des menus borne la valeur lue. Avec le journal de l'ancien firmware, ces octets valaient 0, puisque Nikon ne les écrit jamais : le premier démarrage après le flash donne donc 0/0 [H forte].

## 4. Les deux crochets

### 4.1 Crochet 1 : `preglage_crochet` (0x3F3000)

**Site d'appel 0x4B5B2**, dans `isp_chargerPuce` [V] :
- la séquence est LDI:32, CALL:D @R12, puis MOV R10,R4 dans le créneau de délai. Seule la constante change, le créneau reste celui de Nikon ;
- au retour, MOV R4,R10, et les copies de courbe qui suivent utilisent R10 ;
- R8 (0x40010000) et R9 (fiche + 0x26C) sont préservés.

**Corps** [V] :
1. ST RP, ST R8, MOV R4,R8, appel de la fonction d'origine 0x323C22.
2. Tests :
   - mode PSAM (+0x5A>>4 < 4) ;
   - `_DAT_83eb3d3c` == 0 ;
   - mode d'optimisation → emplacement (table 0x3F3210) ;
   - indice `_DAT_83eb3ab4` < 18, par BNC (non signé) ;
   - `k` = table 0x3F3220, base = table 0x3F3234.
3. Copies STH 16 bits :
   - 9 valeurs vers 0x40010022 (matrice caméra, signe + grandeur bit 0x400) ;
   - 64 vers 0x4001E400 (secteurs, bit 0x200) ;
   - 9 vers 0x40010034 (YCbCr, bit 0x200).
4. R4 = base + 0x380 (courbe), puis LD @R15+,R8 ; LD @R15+,RP ; RET.

Aucun créneau de délai, aucune instruction de plusieurs mots en position interdite [V]. Les écritures ont la même largeur que celles de Nikon sur ces registres [V].

**Valeurs** [V] :
- vraies recettes : maximum de la matrice 995 (emplacements 1 et 2), 979 (emplacement 0), 309 et 415 (les deux N&B) ;
- aucun bit hors du masque 0x7FF ;
- secteurs ≤ 0x21E ;
- YCbCr BT.601 identique pour les 5.

Nikon monte au plus à 969. La borne du registre (1023) est respectée, et le générateur l'assure (`signe_grandeur` avec assert). Rien ne dit qu'une étape interne de la puce sature entre 969 et 1023 [H] : risque faible.

**Contexte** [V] : le crochet est appelé depuis la tâche de développement (tâche 8) et depuis les chemins `FUN_0004ae0e`, `FUN_0004ae5e` et `FUN_0004aeae` (retouches). Jamais en interruption. Le crochet n'écrit aucune variable statique, seulement des registres de la puce. Une ré-entrée ne laisserait donc pas d'état incohérent.

**Risque (4b)** [V pour le code] :
- l'indice de matrice `_DAT_83eb3ab4` (0 à 17) et `_DAT_83eb3d3c` sont des **globales** ;
- `image_parametres` les pose pour la photo en cours ;
- `FUN_0004b168` saute `image_parametres` si la fiche a déjà ses paramètres (+0x1D & 0x40). C'est le cas des chemins venus de la tâche 16 et de la rafale ;
- `isp_chargerPuce` peut alors tourner avec les globales d'une autre photo.

La fiche garde l'information de balance en +0x3A4 [H forte], mais le crochet ne la lit pas. Effet possible [H] : en rafale avec la balance auto, la matrice d'une photo peut venir de la balance de la précédente. Ce serait une dérive de teinte, pas un plantage.

Correction : tirer `k` de la fiche (+0x3A4, ou un octet libre de la fiche rempli par un troisième crochet après `couleur_chargerMatrice`, `FUN_0031b362`). Test : §8.1.

### 4.2 Crochet 2 : `preglage_reglages` (0x3F30C8)

**Site 0x31B22E**, dans `FUN_0031b22e` [V] : ST RP ; LDI:32 ; CALL @R12, sans créneau ; LD RP ; LDI #1,R4 ; RET. Seul appelant : `image_parametres` (0x31A64E).

**Corps**, désassemblé dans le build aux vraies recettes [V] :
1. ST RP, appel de `modesScene_reglages` (0x31ED1A).
2. R1 = *(0x83EB5864), puis les mêmes tests que le crochet 1. `_DAT_83eb3d3c` est lu **après** `modesScene_reglages`, qui la pose : ici, l'ordre est le bon.
3. Emplacement < 5 (CMP #5 + BGE : signé, mais R0 vient d'un LDUB, donc il vaut de 0 à 255).
4. `tbl_reglages` (0x3F3248, 4 octets par emplacement) : ST 32 bits de la netteté dans 0x83EB3D20, de la saturation dans 0x83EB3D44 et des tons dans 0x83EB3D50.
5. LD @R15+,RP ; RET.

Registres touchés : R0–R2, R12, R13, tous libres dans la convention Softune [V].

**Largeur** [V] : dans le pseudo-C, Nikon n'accède à ces trois variables qu'en 32 bits (`_DAT_83eb3d20`, `_DAT_83eb3d44`, `_DAT_83eb3d50`). Aucun accès à un octet ou un demi-mot intérieur (0x…51 à 0x…53, 0x…21 à 0x…23, 0x…45 à 0x…47). Nikon recopie les tons dans la fiche +0x2C, bits 2 à 4 (`(tons & 7) << 2`). Les métadonnées diront donc « Normal ».

**Tables** [V] : `04 01 01 00` × 5, c'est-à-dire netteté Moyennement élevée, saturation Normale, tons Normal. Les emplacements Nikon non recyclés valent 0xFF dans la table d'emplacements, donc le crochet ne s'applique pas.

**Émulateur**. Le scénario `preglages-v1` rejoué sur le build à deux crochets donne 136 contrôles réussis et 5 échecs. Les 5 échecs portent sur l'octet des tons 0x83EB3D53 et sur l'octet +3 de la netteté 0x40010054. Ils sont attendus : le scénario a été mis à jour pour les tons après ce build. Ce n'est pas un défaut [V]. Le scénario n'a pas été rejoué sur le build aux vraies recettes dans cette revue.

## 5. Chemins oubliés

- **Auto et scènes** (+0x5A>>4 ≥ 4) : les deux crochets sortent tout de suite. Rendu Nikon [V].
- **Nikon et Personnalisé** : emplacement 0xFF, rendu d'usine [V]. Mode couleur II et mode couleur ne sont réglables qu'en Personnalisé, donc aucun conflit avec V1 [V].
- **N&B d'usine** : son emplacement (mode 6) est recyclé en HP5. Plus de N&B Nikon d'origine [V]. C'est voulu, mais le tuto doit le dire.
- **D-Lighting, Recadrer, Superposition, fond d'écran** (écrans 110, 116, 142, 158, 160, 166) : `isp_lancer` redéveloppe toujours depuis le RAW (tables 0xC656C–0xC65FC, tailles du capteur 0xBE0×0x7D0…), par `FUN_0004ae0e`, `FUN_0004ae5e` et `FUN_0004aeae` [V]. Le crochet 1 y joue donc, d'après le mode de la fiche, sous la réserve 4b. C'est le comportement voulu, puisque le JPEG retouché garde le rendu V1 [H forte].
- **Monochrome, Filtres** : ils passent probablement par le moteur de redimensionnement 0x40020000, sans la matrice [H].
- **Double application** [H] : test sur le boîtier. Appliquer D-Lighting à un JPEG pris en Chrome. Si les couleurs se décalent par rapport à l'original, le rendu a été appliqué deux fois. Il faudra alors exclure les chemins de retouche du crochet 1.
- **NEF seul et NEF+JPEG** : les données RAW ne sont pas touchées. L'aperçu embarqué dans le NEF sort en rendu V1 [H forte]. Les métadonnées gardent le nom d'optimisation de l'emplacement Nikon recyclé, avec la netteté et la saturation réellement appliquées (`passe-critique-v1.md`).
- **Aperçu et vignettes** : ils sont produits par le même développement, donc en rendu V1 [H forte].

## 6. Voie de secours (Version du firmware, mise à jour)

### 6.1 Ce qui n'a pas changé [V]

- Le code de mise à jour, le flasheur, le contrôle du CRC et de la signature, les noms de fichiers attendus.
- Les en-têtes de menu 0x15AEC0, 0x15B040 et 0x15B080.
- Les entrées 105 (« Firmware version », 0x140FE4/0x141014) et 106 (« Version up », 0x141376/0x141398) de `tblEcrans`.
- La table A des messages.
- Les libellés français relogés sont identiques : « Version du firmware », « Version/MAJ », Oui, Non.

Deux flashs de sondes ont réussi sur le boîtier : une mise à jour de même version depuis un firmware modifié est acceptée. Les crochets ne jouent qu'au développement d'une image, pas sur ces écrans [V].

### 6.2 Ce qui n'est pas prouvé

- Le scénario `pipboy` atteint l'onglet CONFIG, mais **aucun scénario n'ouvre l'écran 105**, encore moins la confirmation de 106 [V].
- Si un écran Pip-Boy plante à son entrée et que MENU rouvre le dernier onglet mémorisé, l'utilisateur ne peut plus atteindre CONFIG [H]. Le menu ne sert alors plus à rien, et la voie de secours avec.

### 6.3 Étape 5 (non revue) : elle met du code modifié sur la voie de secours

L'étape 5 détourne 11 fonctions de dessin par des tremplins :
- `FUN_0007d72a` (rect, 424 appels dans le pseudo-C) ;
- `FUN_0007e0a0` (dégradé) ;
- `FUN_0007cde2` et `FUN_0007d00e` ;
- `FUN_0007c904` (icône) ;
- `FUN_0007f5e4` ;
- `FUN_00146f44` (titre) ;
- `FUN_00146c48` et `FUN_0014777c` (onglets) ;
- `FUN_00149220` et `FUN_0014947c` (messages).

Or [V] :
- `ecran105_action` appelle `FUN_00149220` ;
- `ecran106_action` appelle `FUN_00149220` et `FUN_0007d72a` ;
- `FUN_0007d72a` a 117 appelants, ce qui en fait une primitive commune à presque tous les écrans.

Avec l'étape 5, un défaut de ce code empêcherait donc d'afficher la confirmation de mise à jour. Les variables de l'étape 5 (`VARS` = 0x83CE75CC) sont la copie RAM de 0x15BAE0, une case de l'étape 4 que la V1 ne lit plus, d'après le commentaire de `pipboy.py` [non vérifié].

Correction :
- dans chaque tremplin de l'étape 5, rendre la main à la fonction Nikon d'origine quand l'écran courant est 105 ou 106 ;
- à défaut, un scénario émulateur qui va jusqu'à « Oui » de 106 avec l'étape 5 ;
- ne pas flasher l'étape 5 avant.

### 6.4 Recours si le menu plante

**Avant de flasher** [H, précautions] :
- laisser le menu ouvert sur CONFIG › Version du firmware : c'est l'écran rouvert par MENU au démarrage ;
- préparer une seconde carte SD avec l'original `BD400111.bin` et `AD400111.bin` ;
- flasher par étapes : menu Pip-Boy seul, retour à l'original, puis V1. Chaque étape prouve que la voie de secours marche depuis le firmware modifié.

Aucun autre recours connu en dehors du menu : ni combinaison de touches au démarrage, ni mise à jour automatique depuis la carte [H : non recherché en détail dans cette revue]. Sinon, il reste le SAV Nikon ou la reprogrammation matérielle de la NOR. Un firmware de vidage de la flash, flashé une fois, donnerait une image de référence du boîtier réel [suggestion].

## 7. Autres risques

- **CRC et contrôles** [V] :
  - CRC16 XMODEM du fichier entier = 0 (octets 0x40FFFE–0x40FFFF), pour le build à deux crochets comme pour le build aux vraies recettes ;
  - taille 0x3D0000 ;
  - signature « Q330FirmwareSignature » à sa place, par les pointeurs 0xEFBF0/0xEFBF4 ;
  - aucun autre contrôle d'intégrité vu sur le code ou les données [H : pas de recherche exhaustive].
- **Autres langues** [V] :
  - les entrées recyclées affichent des libellés Nikon d'autres menus ;
  - les aides 141–144 = B[141..144] = C[0..3] : ce sont les titres d'aide des modes scène, des chaînes bien formées, sans pointeur hors table ;
  - pas de plantage attendu, mais une interface incohérente hors du français.
- **Mode Mon menu** : la liste Nikon est filtrée depuis 0x83CE53EC et l'entrée Mon menu en est retirée [V]. Un boîtier réglé en Mon menu avant le flash démarre dans un mode dont l'entrée n'existe plus [H : risque faible, à tester §8.4]. Le mode Simple n'a pas été testé.
- **Premier démarrage avec les réglages de l'ancien firmware** : les longueurs du journal sont inchangées, donc tous les blocs sont relus [V]. Programme et Si trop sombre valent 0 (§3). Un boîtier réglé sur le N&B d'usine passe en HP5 [V].
- **Procédure** [V] :
  - `build/BD400111.BIN` est daté d’octobre ;
  - `build/v1` (CRC 95c6) n'a pas le crochet 2 et diffère de 115 octets du build revu ;
  - `patchs/preglages-v1.json` n'a pas le crochet 2 ;
  - au moins six BIN différents existent dans le scratchpad (`build-nettete`, `build-tons`, `build-temoin-reglages`, `verif-v1/vraies`, `bandeau/fw/menu4`, `menu5`).

  Le risque est de flasher un fichier qui n'est pas celui qui a été testé. Correction :
  - régénérer un seul build final dans `build/v1` depuis `patchs/v1.json` à jour ;
  - noter son sha256 dans le README ;
  - rejouer tous les scénarios sur ce fichier exact ;
  - copier sur la carte ce fichier, et contrôler son sha256 sur la carte.

## 8. Tests à ajouter à l'émulateur

1. **Globale périmée (4b)**. Fiche A avec l'indice de matrice k = 1, `image_parametres` sur une fiche B avec k = 4, puis `isp_chargerPuce` sur A. Résultat attendu : la matrice de A (k = 1) dans 0x40010022. Le test doit échouer avec le crochet actuel, sinon l'hypothèse est fausse.
2. **Voie de secours**. Navigation MENU → CONFIG → Version du firmware (105) → Version/MAJ (106) → écran de confirmation, sans valider. À faire sur le build V1, puis sur le build avec l'étape 5.
3. **Langue anglaise**. Toutes les entrées Pip-Boy, avec la touche ? (aide) sur chaque nouvelle entrée.
4. **Démarrage en mode Mon menu et en mode Simple**, avec la RAM préremplie comme par l'ancien firmware.
5. **Relecture du bloc 10** depuis un journal écrit par l'original (octets 0x24E et 0x24F à 0), puis à 3 et 1, puis « Réinitialiser » : constater que les valeurs restent.
6. **Retouches**. D-Lighting, Recadrer et fond d'écran par `appel` sur une fiche V1 : relever les registres de la puce et compter les passages dans le crochet 1.
7. **Valeurs extrêmes**. Une recette synthétique à ±1023 et une à 0 : le crochet écrit exactement ces valeurs.
8. **Rejouer tout** (`pipboy`, `preglages-v1` et les scénarios de navigation) sur le build final, identifié par son sha256.
