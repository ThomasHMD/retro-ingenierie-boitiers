# Carte du firmware B du D40 (v1.11)

Référence de travail, établie les 23 et octobre 2026. Chaque fait porte son niveau de confiance :
**vérifié** (lu dans le code ou les données, recoupé), **probable** (un indice fort, pas de preuve complète), **hypothèse** (piste à tester). Les adresses sont celles du processeur : adresse = offset dans `firmware/BD400111.bin` + `0x40000`.

Les symboles vérifiés ou probables sont dans [`desassemblage/symboles.tsv`](desassemblage/symboles.tsv) (adresse, nom, type, confiance, preuve), appliqués à Ghidra par `D40Setup.java`. Tout se régénère depuis le binaire :

```
desassemblage/regenerer.sh <dossier de travail hors du dépôt>                 # import + analyse complète
desassemblage/regenerer.sh <dossier de travail hors du dépôt> --sans-analyse  # projet déjà analysé
```

Sortie : `d40-tout.c` (pseudo-C des 3 188 fonctions du B, chacune précédée de `//@@ adresse nom appelants:`), `a-tout.c` (les 1 133 du A), `appels-systeme.tsv` (~1 620 appels au noyau, avec la fonction appelante), le projet Ghidra ; et dans `desassemblage/` : `ecrans.tsv`, `menus.txt` (arbre des menus), `liaison-a.tsv` (commandes vers le A). Depuis zéro : 1 min 30 sur le Mac Studio (vérifié en octobre 2026).

## 1. Plan du fichier (4 Mo, chargé de 0x40000 à 0x40FFFF)

| Plage | Contenu | Confiance |
|---|---|---|
| 0x040000–0x0C3FFF | Code principal (tâches, PTP, interface, fichiers, flash) | vérifié |
| 0x0C1400–0x0C35FF | Noyau temps réel REALOS (Softune, µITRON 3) | vérifié |
| 0x0C3A88 | Table du CRC16 | vérifié |
| 0x0C4000–0x0E2FFF | Données : courbes, tables PTP (0xD9EC4…), chaînes de service | vérifié |
| 0x0E4B80–0x0E4BD8 | Noms de fichiers : fond d'écran, `AD40????.BIN`, `BD40????.BIN`, `A:\MISC\AUTPRINT.MRK` | vérifié |
| 0x0EA85C–0x0EAE03 | Configuration du noyau (tâches, sémaphores, drapeaux) | vérifié |
| 0x0EB000–0x0EFBEF | Vide (0xFF), **écrit** par la mise à jour : 16 Ko utilisables | vérifié |
| 0x0EFBF0–0x0EFFFF | Pointeurs version et signature, table des 256 vecteurs (0xEFC00) | vérifié |
| 0x0F0000–0x11FFFF | 0xFF dans le fichier, **jamais écrit** par la mise à jour (voir §3) | vérifié |
| 0x120000–0x152FFF | Code (deuxième bloc : interface, menus, lecture) | vérifié |
| 0x1544C4–0x15D528 | Données initialisées, copiées en RAM au démarrage : menus (0x158500–0x15C000), écrans (0x156644), pilote flash, langues | vérifié |
| 0x15E000–0x15FFFF | Vide, écrit par la mise à jour : 8 Ko utilisables | vérifié |
| 0x160000–0x16FFFF | Fond d'écran perso : en-tête 16 octets + JPEG | vérifié |
| 0x170000–0x1AFFFF | 0xFF dans le fichier, **jamais écrit** par la mise à jour | vérifié |
| 0x1B0000–0x28AFFF | Graphismes : palette (0x1B0000), planches de glyphes (descripteurs 0x1B01A0), polices (largeurs à 0x1B05E4 et 0x1B064C), icônes | vérifié (palette, polices) |
| 0x28B000–0x31FFFF | Textes des 15 langues (messages, aides, libellés) | vérifié |
| 0x30E000–0x325FFF | Code du traitement d'image (matrices, modes scène) | vérifié |
| 0x325000–0x393FFF | Données du traitement d'image (matrices 0x331B98, 0x33270E, 0x332888 ; tables d'index) | vérifié |
| 0x394000–0x3A3FFF | Code appelé depuis le PTP (0x90C0, 0x90C2, 0x90CA) | probable |
| 0x3A4000–0x3E6FFF | Données | — |
| 0x3E7000–0x40FFFD | Vide (0xFF), **écrit** par la mise à jour : 164 Ko utilisables | vérifié |
| 0x40FFFE | CRC16 du fichier, sur 2 octets | vérifié |

## 2. Démarrage et mémoire

- **Reset** (`0xC0F90`, vecteur 0) : règle le bus et les puces mémoire, met à zéro le BSS (`0x83CE9018`–`0x83D02147`), copie les données initialisées de la ROM `0x1544C4`–`0x15D528` vers la RAM `0x83CDFFB0`–`0x83CE9014` (décalage constant **RAM = ROM + 0x83B8BAEC**), puis appelle `0xC1610`. Vérifié.
- Conséquence : beaucoup d'adresses `0x83CExxxx` du code désignent des tables en ROM. Exemple : la table des langues est à `0x15C7A4` en ROM et à `0x83CE8290` en RAM.
- **Mémoire** : `0x68000000` = RAM interne (variables du noyau, blocs de contrôle des tâches) ; `0x83xxxxxx` = RAM externe (variables, piles des tâches de `0x83EB9308` à `0x83ED5B08`) ; `0x81000000` = grande zone tampon (le fichier de mise à jour y est chargé en entier). Vérifié.
- **Registres matériels** (blocs lus dans le code) : `0x40010000` (tables de conversion du traitement d'image, chargées par `0x4BE82`), `0x40020000`–`0x40021FFF` (moteur de redimensionnement avec matrice 3×4 et deux tables 8 bits), `0x40030000`, `0x40040000`, `0x40060000` (838 accès, 50 fonctions ; calcule un histogramme de 256 cases, lu à `0x40060400` par `0x12337E`), `0x40070000` (contrôleur mémoire, réglé par le reset), `0x400E0000`, `0x50000000` (ports du processeur). Rôle exact de chaque bloc : hypothèse.
- **Réglages gardés à l'extinction** (vérifié, octobre 2026) : 12 blocs de RAM décrits par `tblBlocsReglages` (`0xD5364`, {adresse, longueur}), dont le mode couleur et le mode d'optimisation (bloc 2, `0x83CED21A`), la langue (bloc 1, `0x83CED0F8`), les réglages perso (bloc 3) et les deux courbes perso. Journal en flash à `0x180000` / `0x190000` (zone jamais écrite par la mise à jour) : `reglages_sauver` (`0x6B708`, via `0x403FA`, tâche 4) n'écrit que les blocs changés, `reglages_lire` (`0x6B44C`) les recopie au démarrage si la longueur est la bonne. Le menu Pip-Boy V1 y range Programme et Si trop sombre (`0x83CED24E/F`, bloc 10, octets jamais cités par le code Nikon). PERSO › Réinitialiser (écran 37, action `0x135536` → `reglagesPerso_reinitialiser`, `0x135570`) remet les réglages perso, des bits du bloc 10 et `0x83CE974D`, puis envoie deux fois les réglages au A (`0x138546`) ; la V1 y remet aussi Programme et Si trop sombre à 0 (`preglage_reinit`, vérifié dans l'émulateur, scénario `reinitialiser`).

## 3. Mise à jour du firmware : ce qui est vérifié, ce qui est écrit

Chaîne complète lue dans le code (vérifié) :
1. `maj_chercherFichiers` (`0xAB5CC`) cherche `BD40????.BIN`, sinon `AD40????.BIN`, à la racine de la carte.
2. `majB_ouvrir` (`0xABBFE`) exige une taille de **0x3D0000 octets** exactement.
3. `majB_verifierSignature` (`0xABCE4`) suit le pointeur à `0xEFBF4` et compare 32 octets à « **Q330FirmwareSignature** » (Q330 = nom de code interne du D40), puis lit 9 octets de version via le pointeur `0xEFBF0`.
4. `maj_executer` (`0xAB88E`) charge tout le fichier à `0x81000000`, calcule le CRC16 (`0x44CCC`, polynôme 0x1021, table `0xC3A88`) sur le fichier entier CRC compris : il doit valoir 0. Puis prévient l'autre processeur et saute au flasheur.
5. Le **flasheur** (`0x15CBE2`, exécuté depuis la RAM à `0x83CE86CE` parce qu'on ne lit pas la flash pendant qu'on l'efface) efface et programme **uniquement** :
   - `0x040000`–`0x0EFFFF` ;
   - `0x120000`–`0x15FFFF` ;
   - `0x1B0000`–`0x40FFFF` ;
   - `0x160000`–`0x16FFFF` (fond d'écran) seulement si l'en-tête de 16 octets en flash **diffère** de celui du nouveau fichier **et** n'est pas `NIKOND40_WP_USER` (comparaison `0x15D3AA`). Un fond d'écran perso survit donc à la mise à jour, et le fond d'usine n'est réécrit que si sa version change (`WPVER01` → autre chose).

Conséquences :
- **Les zones `0x0F0000`–`0x11FFFF` et `0x170000`–`0x1AFFFF` ne sont jamais écrites.** Dans le boîtier, elles contiennent autre chose que les 0xFF du fichier. Les vecteurs du processeur à la mise sous tension sont à `0xFFC00` (valeur par défaut du FR), dans cette zone : il y a très probablement un **chargeur de démarrage** à part, jamais mis à jour, et des données propres au boîtier (réglages, étalonnage d'usine). Probable. Bonne nouvelle pour le risque : un firmware B raté n'écrase pas ce chargeur.
- **Espace libre réellement utilisable pour des ajouts** (écrit par la mise à jour) : 164 Ko à `0x3E7000`–`0x40FFFD`, 16 Ko à `0xEB000`–`0xEFBEF`, 8 Ko à `0x15E000`–`0x15FFFF`. Rien ailleurs.
- Ce que `patch.py` doit respecter : taille inchangée, pointeurs `0xEFBF0` et `0xEFBF4` intacts, CRC recalculé. C'est déjà le cas.
- La branche A (`AD40`, 0x40002 octets, CRC aussi vérifié) envoie le fichier à l'autre processeur (`0xABA80`) puis redémarre. Probable.
- **Le chemin dans le menu** (vérifié dans l'émulateur, scénario `secours`, octobre 2026) : CONFIG › Version du firmware = **écran 105** (menu RAM `0x83CE6B2C`, ROM `0x15B040`). Son entrée « Version/MAJ » n'existe à l'écran que si `maj_chercherFichiers` a rendu 1 (fichier trouvé sur la carte) : sans carte, l'écran ne montre que la version. Elle ouvre l'**écran 106** (`0x83CE6B6C`, ROM `0x15B080`, Non / Oui, surbrillance sur Non), à condition que la batterie suffise : octet `0x83CE950C`, bits 6-7 = 3. Oui mène à l'**écran 104** (exécution). `ecran105_action` et `ecran106_action` appellent `message_afficher` (`0x149220`) et `rectangle_remplir` (`0x7D72A`) : toute modification de l'interface doit laisser ces écrans au code d'origine (c'est ce que fait le sas du bandeau, README « Menu Pip-Boy »). Le flasheur, lui, n'appelle rien en ROM.

## 4. Noyau temps réel REALOS

- Appel système : `INT #0x40`, numéro négatif dans R12 (convention µITRON/Softune). Le gestionnaire (`0xC1586`) saute à `0xC157E + table[R12]`. 56 appels implémentés, nommés `krn_<appel>` par `D40Noyau.java` ; les numéros correspondent à la liste du module ghidra-fr60. Vérifié.
- Objets **statiques** (pas de `cre_tsk`) : descripteurs en ROM `{u16 nombre, u16 taille, éléments}`, lus par `0xC275E`. **24 tâches, 29 sémaphores, 15 drapeaux d'événements**, aucune boîte aux lettres, aucun pool, aucun gestionnaire cyclique. Vérifié.
- Appels les plus utilisés : `set_flg` 458, `clr_flg` 423, `wai_flg` 217, `sig_sem` 87, `wai_sem` 77, `tslp_tsk` 68, `dly_tsk` 66, `sta_tsk` 29. Les tâches se parlent presque uniquement par drapeaux d'événements.
- Contre-vérification de la table : pour 11 tâches (1, 2, 3, 8, 12, 13, 14, 18, 20, 21, 23), l'appel `sta_tsk(n)` est à 4 à 18 octets de l'entrée lue dans la table ; les autres sont démarrées depuis le même module. La tâche 17 est lancée de 4 endroits (`0x9BA5C`…).

| Tâche | Priorité | Entrée | Haut de pile | Pile | Rôle |
|---|---|---|---|---|---|
| 1 | 12 | 0x6D8D0 | 0x83EB9308 | | |
| 2 | 10 | 0xAAECE | 0x83EB9B08 | 0x800 | |
| 3 | 16 | 0x406FE | 0x83EB9F08 | 0x400 | la moins prioritaire (tâche de fond) |
| 4 | **1** | 0x400F0 | 0x83EBA708 | 0x800 | la plus prioritaire ; écrit en flash, chaînes `SYSTEMFIXADJUST`, `END_OF_Q330_CONFIG` : réglages du boîtier (probable) |
| 5 | 3 | 0x45624 | 0x83EBC708 | 0x2000 | |
| 6 | 2 | 0x4653E | 0x83EBCB08 | 0x400 | |
| 7 | 5 | 0x45F1A | 0x83EBCF08 | 0x400 | |
| 8 | 7 | 0x4A8A6 | 0x83EBEF08 | 0x2000 | **traitement d'image** : atteint les matrices couleur, les modes scène, les tables matérielles (probable) |
| 9 | 7 | 0x47D10 | 0x83EC0F08 | 0x2000 | |
| 10 | 7 | 0x47E86 | 0x83EC1308 | 0x400 | |
| 11 | 7 | 0x48464 | 0x83EC1708 | 0x400 | |
| 12 | 13 | 0x77686 | 0x83EC3708 | 0x2000 | chaînes `A:\DCIM` : fichiers images (hypothèse) |
| 13 | 13 | 0x776D2 | 0x83EC5708 | 0x2000 | |
| 14 | 4 | 0xA9280 | 0x83EC5B08 | 0x400 | **liaison série avec le processeur A** (vérifié, détail en §10 bis) |
| 15 | 8 | 0x4D896 | 0x83EC7B08 | 0x2000 | |
| 16 | 10 | 0x14D804 | 0x83ECAB08 | 0x3000 | **interface** : choix de la langue, histogramme, 800 fonctions atteintes (probable) |
| 17 | 10 | 0x123606 | 0x83ECAF08 | 0x400 | |
| 18 | 8 | 0x694B2 | 0x83ECB308 | 0x400 | |
| 19 | 11 | 0x9343C | 0x83ECD308 | 0x2000 | |
| 20 | 9 | 0x78670 | 0x83ED1308 | 0x4000 | **carte mémoire** : formatage, `NO NAME`, `NIKON D40`, `A:\DCIM` (probable) |
| 21 | 6 | 0x8E32E | 0x83ED3308 | 0x2000 | |
| 22 | 7 | 0x89A8C | 0x83ED5308 | 0x2000 | |
| 23 | 8 | 0x8BE7C | 0x83ED5708 | 0x400 | |
| 24 | 8 | 0x936E0 | 0x83ED5B08 | 0x400 | |

Les rôles viennent des fonctions et chaînes atteignables depuis chaque entrée (graphe d'appels du pseudo-C). Les gestionnaires PTP sont appelés par pointeur, donc invisibles dans ce graphe.

## 5. Textes et langues

- **Table des langues** à `0x15C7A4` (RAM `0x83CE8290`) : 15 langues × 3 pointeurs. `langue_choisir` (`0x9B14E`) recopie le triplet de la langue choisie dans `0x83CE3FF8` (A), `0x83CE3FF4` (B), `0x83CE3FF0` (C), et pose en `0x83CE3FEC` une quatrième table, D, qui commence 31 pointeurs après C. Vérifié pour les 15 langues. Le numéro de langue du menu n'est pas l'indice de la table (cas 1 → indice 3, finnois).
- Ordre dans la table : 0 allemand, 1 anglais, 2 espagnol, 3 finnois, 4 français, 5 italien, 6 et 7 (japonais, coréen ?), 8 néerlandais, 9 polonais, 10 portugais, 11 russe, 12 suédois, 13 et 14 (chinois ?). Les 11 langues latines et le russe sont vérifiés sur le titre du menu Visualisation ; 6, 7, 13, 14 sont des hypothèses.
- Quatre tables par langue : **A** 266 messages, **B** 141 aides, **C** 31 titres d'aide des modes scène, **D** 602 libellés des menus (`D0` = `MENU VISUALISATION`, `D34` = « Optimiser l'image »). A, B et C commencent par un octet « nombre de lignes », les lignes sont séparées par `\n` ; D n'a pas cet octet. Vérifié.
- **Identifiant de texte** (16 bits, `texte_parIdentifiant` `0x7C1A0`) : bits 13 à 15 = la table (`0x0000` D, `0x2000` C, `0x4000` B, `0x6000` A), bits 0 à 12 = le numéro. Exemple : `0x0022` = « Optimize image », `0x4049` = son aide. C'est ce que les menus stockent. Vérifié.
- **Règle de longueur** lue dans les accesseurs (vers `0x7C50E`) : la chaîne `n` va de `table[n]` à `table[n+1]`. Il n'y a pas de terminateur. Vérifié.
- **Conséquence pour l'interface** : une chaîne plus longue ne tient pas en place, mais on peut **reconstruire toute la table d'une langue** dans l'espace libre (`0x3E7000`, 164 Ko ; une langue fait ~36 Ko), avec des textes de longueur libre, et faire pointer le triplet de la langue dessus. C'est la voie pour renommer, et plus tard ajouter, des entrées de menu. Probable (le principe est vérifié, pas encore testé sur le boîtier).
- Accents : 2 octets, `0x81` puis un code (`0x21` é, `0x0F` É, `0x19` à, `0x20` è, `0x15` ×, `0x12` Ó, `0x0D` Ç, `0x0A` Ã, `0x1F` ç, `0x22` ê, `0x27` ñ, relevés par le contexte). Tout octet ≥ `0x80` ouvre une séquence de 2 octets ; `0x0F n` change de police (relevé en écrivant les titres du bandeau, étape 5 du Pip-Boy).
- Outil : `outils/chaines.py` (`langues`, `liste --langue 4 --table D`, `cherche "MENU"`, `--self-test`) ; la 3ᵉ colonne de `liste` est l'identifiant de texte.

## 5 bis. Menus

Tout l'arbre est dans des données (ROM `0x158530`–`0x15C440`, copiées en RAM), aucun menu n'est construit par du code. Vérifié sur le binaire et par les fonctions des écrans. Outil : `outils/menus.py` (`arbre`, `tsv`, `ecrans`, `--self-test`) ; arbre complet en anglais dans `desassemblage/menus.txt`, écrans dans `desassemblage/ecrans.tsv`.

- **173 menus, 576 entrées, 143 écrans.** Racines : Visualisation (`0x1592D0`), Prise de vue (`0x1598E0`), Réglages perso (`0x15A380`), Configuration (`0x15AEC0`), Retouche (`0x15BDC0`), plus Langue, PictBridge et ses réglages.
- **En-tête de menu, 32 octets** : `+0` titre, `+2` sous-titre (identifiants de texte, `0xFFFF` = aucun), `+4` attributs, `+8` nombre d'entrées sélectionnables, `+0xA` nombre d'entrées stockées, `+0x12` **numéro d'écran**, `+0x14` menu parent, `+0x18` positions à l'écran (liste de `x<<16 | y`), `+0x1C` pointeur vers les entrées (= en-tête + 0x20). Les pointeurs sont des adresses RAM (ROM + `0x83B8BAEC`).
- **Entrée, 16 octets** : `+0` icône (`0x8xxx`, indice dans `tblIcones` `0x157904`), `+2` libellé, `+4` aide, `+0xA` numéro d'entrée global, `+0xC` sous-menu (0 = aucun).
- **`tblEcrans`** (`0x156644`, 170 × 12 octets, RAM `0x83CE2130`) indexée par le numéro d'écran : `+0` attributs, `+4` fonction d'entrée, `+8` fonction d'action. Le menu courant est pointé par `0x83CEE49C` ; l'entrée en surbrillance est en `+0xC`. `D40Menus.java` crée et nomme les 167 fonctions (`ecranNNN_entree`, `ecranNNN_action`, `menu_action_XXXXXX` quand elle est partagée) ; Ghidra ne les trouvait pas seul.
- **Les valeurs ne sont pas les positions** : la fonction d'entrée de chaque écran lit le réglage dans un octet de réglages et place la surbrillance. Exemple vérifié, Optimiser l'image (`ecran014_entree`, quartet haut de `0x83CE957F`) : 0 Normal, 1 Plus doux, 2 Vif, 3 Très vif, 4 Portrait, **5 Personnalisé, 6 Noir et blanc**, alors qu'à l'écran le Noir et blanc vient avant le Personnalisé.
- Réglages du Personnalisé (octets `0x83CED224`–`0x83CED226`, même codage que les octets `+0x2C`–`+0x2E` lus par le traitement d'image, vérifié écran par écran) :

| Réglage | Champ | Valeurs |
|---|---|---|
| Netteté | `+0x2C` bits 5-7 (`d20`) | 0 Auto, 1 Normal, 2 Faible, 3 Moyennement faible, 4 Moyennement élevée, 5 Élevée, 6 Aucune |
| Correction des tons | `+0x2C` bits 2-4 (`d50`) | 0 Auto, 1 Normal, 2 Moins de contraste, 3 Moyennement faible, 4 Moyennement élevée, 5 Plus de contraste, 6 Personnalisée |
| Saturation | `+0x2C` bits 0-1 (`d44`) | 0 Auto, 1 Normale, 2 Modérée, 3 Rehaussée |
| Mode couleur | `+0x2D` bits 6-7 | 1 Ia, 2 II, 0 IIIa |
| Teinte | `+0x2E` (`d34` − 3) | −3 à +3, sans doute par pas de 3° (probable) |

- **Attributs d'écran** (`tblEcrans +0`, lus en `0x83CE2130 + 12 × écran`) : bit `0x8000` = écran à onglets (`FUN_00146a08` dessine alors le fond et la colonne par `menu_fond` `0x146EE2`, et efface l'aide « ? » par `0x7EDF4`) ; bit `0x1000` = curseur dans la liste (à 0, il est sur les onglets ; `onglets_navigation` le remet à 0 au changement d'onglet). Vérifié dans l'émulateur.
- **Onglet courant** : octet `0x83CE3FE8` (0 VISU, 1 PRISE DE VUE, 2 PERSO, 3 CONFIG). **Mode d'interface** : mot `0x83CED23A`, qui vaut 5 tant qu'un menu est affiché (vérifié tout au long des scénarios ; les autres valeurs ne sont pas relevées).
- **Les en-têtes sont modifiés en marche** (`ecran019_entree` réécrit `+8`), d'où leur place en RAM. Les données initialisées sont suivies du BSS : on ne peut pas y ajouter un menu. Deux voies pour une entrée de plus : **réutiliser une entrée peu utile** (changer libellé, icône, sous-menu et la fonction d'écran : patch de données seulement), ou copier un nouveau menu dans de la RAM libre au démarrage (patch de code). Hypothèse, rien de testé.

## 6. USB et PTP

- Descripteurs USB à `0x156E60` et `0x156E84` : Nikon (VID `0x04B0`), produits `0x0414` (PTP, connu de libgphoto2) et `0x0413` (stockage de masse, probable). Vérifié pour les valeurs.
- Trois tables d'opérations (opcode, 2 octets nuls, adresse du gestionnaire), toutes nommées dans `symboles.tsv` : **19 standard** à `0xD9F54` (dont `InitiateCapture` 0x100E et `FormatStore`), **12 Nikon** 0x90C0–0x90CB à `0xD9EEC` (dont `InitiateCaptureRecInSdram` 0x90C0, `AfDrive`, `CurveDownload` 0x90C5, `CurveUpload` 0x90C6, `GetVendorPropCodes`), **4 MTP** à `0xD9EC4`. Vérifié.
- La présence de 0x100E et 0x90C0 avec du vrai code suggère que la **prise de vue pilotée par USB** existe dans le boîtier. Hypothèse, à tester avec gphoto2.

## 7. Traitement d'image

**Courbe de tonalité perso** (vérifié) :
- Format du bloc : **0x1044 octets = 68 octets d'en-tête + 2 048 valeurs 16 bits** (une table complète, sortie sur 12 bits, 0 à 4095).
- `ptp90C5_CurveDownload` (`0x85072`) renvoie le tampon RAM `0x83E89310` s'il est rempli, sinon une courbe d'usine en ROM à `0xDC250` (en-tête vide, table en S de 9 à 4095).
- Un second bloc identique à `0xDB20C` (table de 14 à 4095), non référencé directement.
- Puisque le boîtier stocke la table entière, on peut envoyer **n'importe quelle forme de courbe** par `ptp90C6_CurveUpload`, pas seulement 19 points. Probable (reste à le vérifier en relisant une courbe envoyée).

**Courbes de tonalité intégrées** (vérifié, `outils/courbes.py`) :
- `tonalite_construire` (`0x323C22`) remplit la table de tonalité de **4 096 entrées sur 12 bits** en RAM à `0x83EB586C`, d'après le numéro de courbe (octet `+0x466` des réglages de la prise de vue). Puis elle ajoute, entrée par entrée, une correction signée sur 8 bits lue dans `0x33692E` (colonne choisie par l'octet `+0x6AE`).
- Numéros 0 à 20 : 21 courbes compressées à `0x34BC56` (2 047 octets chacune). Numéros 0x2F à 0x35 : 7 autres à `0x348433`. Numéro 0x17 : la courbe perso.
- **Format** (`courbe_decoder`, `0x324306`) : deux valeurs de départ sur un octet (tables `0x34BC41`/`0x34BC2C`, et `0x34842C`/`0x348425`), puis une « dérivée seconde » sur 4 bits par point : `y[k] = 2·y[k−1] − y[k−2] + (q − 8)`.
- Preuve que le décodage est juste : la courbe 17 décodée coïncide avec la courbe perso d'usine `0xDC250`, et la 50 avec `0xDB20C`. Le format perso garde un point sur deux ; l'écart est de 1/4095 au plus, sur les points interpolés. De plus, `courbes.py --self-test` réencode les courbes Nikon à l'octet près.
- Organisation : des groupes de 7 niveaux de contraste, le plus doux en premier, le « Normal » au milieu (3, 10, 17, 50). Le numéro vaut **`7 × groupe + niveau`**, et ce même numéro choisit aussi la matrice YCbCr (21 matrices) : contraste et saturation vont ensemble.
  - Le groupe (`cd4`) vient du réglage `d48` : 0, 3 et 5 donnent le groupe 0 ; 1 donne le groupe 1 ; 2, 4 et 6 donnent le groupe 2. **Groupe 0 = Ia, groupe 1 = II, groupe 2 = IIIa** (vérifié, voir « Mode couleur » ci-dessous).
  - Le niveau (`cc4`, 0 à 6) sort de la grande table de paramètres `0x32AE90` (`parametres_lire` `0x31F6B8` : 5 880 entrées de 32 bits, indice `cd8·3 + cd4 + ce4·12 + ce0·84 + cdc·588 + s·2940`, niveau dans les bits 3-5). Vérifié :
    - la correction des tons donne une classe de contraste `ce4` (`couleur_parametresYcc`) : Moins de contraste → 0, Moyennement faible → 1, Normal → 3, Moyennement élevée → 5, Plus de contraste → 6, Auto → une classe calculée (`0x83EB3E54`), Personnalisée → 3 (la courbe perso remplace de toute façon la courbe) ;
    - le niveau vaut cette classe, moins 1 dans la classe de scène la plus lumineuse (`ce0 = 6`), et resserré à 1–5 dans la classe d'ISO la plus haute (`cdc = 4`). Les niveaux 2 et 4 ne servent donc qu'en Auto et dans ces corrections.
    - Exemple : Normal en Ia → courbe 3 ; Plus de contraste en IIIa → courbe 20.
  - Le jeu 2 (47 à 53) sert quand l'octet `+0x2D` indique le mode d'optimisation 6, qui est le **Noir et blanc** (vérifié par le menu, §5 bis). Sa courbe perso a son propre tampon (`0x83E882CC`, défaut `0xDB20C`).
- L'entrée est très probablement **linéaire** (12 bits du capteur) : le Normal rend 124/255 à 1/8 de la pleine échelle, la place habituelle du gris moyen avec ~3 IL de marge. Probable.
- **Conséquence : un rendu film sans USB.** On remplace les courbes d'un groupe par une courbe encodée, avec `patch.py`. `courbes.py patch` fabrique le JSON à partir d'une mesure de `recettes/mesures/` : courbe Normal du D40 + écart (simulation − Provia). Ainsi la montée au blanc reste celle du D40 (la courbe Fuji brute laisse les blancs gris, car le Fuji garde ~6 IL au-dessus du gris contre ~3,5 au D40). Premier patch : `patchs/classic-chrome-groupe0.json` (courbes 0 à 6, écart d'encodage 1,9/4095, non testé). Le groupe 0 sert au **mode couleur Ia** : Personnalisé réglé en Ia, Plus doux, Portrait, et les modes scène Portrait, Enfant, Portrait de nuit (vérifié par les tables ci-dessous). Normal, Vif, Très vif, Auto et Paysage n'y touchent pas : ils servent de témoin. Tracé : `recettes/mesures/courbes-d40.svg`.

**Matrices** : voir le README, « La couleur dans le firmware » (`0x332888`, `0x33270E`, `0x331B98`) ; chargées par la tâche 8. Choix de la matrice caméra → RGB (`couleur_chargerMatrice`, vérifié pour la logique) :
- 3 groupes de 6 selon `d48` : 3 → matrices 0 à 5, 1 → 6 à 11, 4 → 12 à 17 ; 0 et 2 ne changent rien ici.
- Dans un groupe (base `g`), selon le type de lumière (`cd0`) et une valeur bornée à 0x33 et 0x9D (`eb8`, sans doute la température de couleur) :
  - `g+0` : `eb8` ≥ 0x9D ;
  - `g+1` : `cd0` = 1 ou 4, entre les deux bornes ;
  - `g+2` : `cd0` = 1 ou 4, `eb8` ≤ 0x33 ;
  - `g+3` : `cd0` = 2 ;
  - `g+4` : autre `cd0` ;
  - `g+5` : si `_DAT_83eb5854` ≠ 0.

**Mode couleur ↔ `d48` ↔ matrices et courbes** (vérifié de bout en bout) :
1. le menu Mode couleur (`ecran019_entree`) range le choix dans les bits 6-7 de `0x83CED225` : Ia = 1, II = 2, IIIa = 0 ;
2. le traitement d'image lit les mêmes bits dans `+0x2D` (`modesScene_reglages`) : 1 → `d48 = 3`, 2 → `d48 = 1`, 0 → `d48 = 4` ;
3. au retour, `tblModeCouleurBits` (`0x3251C4` : `01 02 00`) réécrit ces bits depuis le groupe `cd4`, la boucle est cohérente.

| Mode couleur | Bits | `d48` | Matrices caméra | Courbes (groupe) |
|---|---|---|---|---|
| Ia (sRGB) | 1 | 3 | 0 à 5 | 0 à 6 (0) |
| II (AdobeRGB) | 2 | 1 | 6 à 11 (proches de l'identité) | 7 à 13 (1) |
| IIIa (sRGB) | 0 | 4 | 12 à 17 | 14 à 20 (2) |

**Préréglages d'Optimiser l'image** (`modesScene_reglages`, vérifié ; valeurs selon le tableau du §5 bis) :

| Mode (valeur) | Netteté | Tons | Couleur | Saturation | Teinte |
|---|---|---|---|---|---|
| Normal (0) | Auto | Auto | IIIa | Auto | 0 |
| Plus doux (1) | Faible | Moins de contraste | Ia | Auto | 0 |
| Vif (2) | Moy. élevée | Normal | IIIa | Rehaussée | 0 |
| Très vif (3) | Élevée | Plus de contraste | IIIa | Rehaussée | 0 |
| Portrait (4) | Moy. faible | Auto | Ia | Auto | 0 |
| Personnalisé (5) | réglages de l'utilisateur | | | | |
| Noir et blanc (6) | Normal | Normal | Ia | Normale | 0 ; `d1c = 1` (chemin N&B, `tblMatrices3`), `d18` = bit 0 de `+0x2D` |

**Modes scène** : code `+0x5A >> 4` côté B, de 4 à 11 ; 0 à 3 = P, S, A, M. Le même code est dans `0x83CE9823` (quartet haut), reçu du A par la commande 0x14 (§10 bis). Balance des blancs forcée en Auto (`cfc = cf8 = 0`).

| Code B | Code A | Mode | Netteté | Tons | Couleur | Saturation | Teinte | Zone AF | Flash |
|---|---|---|---|---|---|---|---|---|---|
| 11 | 15 | Auto | Auto | Auto | IIIa | Normale | 0 | sujet le plus proche | auto |
| 10 | 14 | Auto (flash désactivé) | Auto | Auto | IIIa | Normale | 0 | sujet le plus proche | coupé |
| 9 | 13 | Portrait | Moy. faible | Auto | Ia | Normale | 0 | sujet le plus proche | auto |
| 8 | 12 | Paysage | Moy. élevée | Auto | IIIa | Normale | 0 | sujet le plus proche | coupé |
| 7 | 11 | Enfant | Normal | Auto | Ia | Rehaussée | +1 cran | sujet le plus proche | auto |
| 6 | 10 | Sport | Moy. élevée | Auto | IIIa | Normale | 0 | dynamique | coupé |
| 5 | 9 | Gros plan | Normal | Normal | IIIa | Normale | 0 | point sélectif | auto |
| 4 | 8 | Portrait de nuit | Moy. faible | Normal | Ia | Normale | 0 | sujet le plus proche | auto, synchro lente |

Identité des codes : vérifiée par recoupement, chaque ligne collant au manuel du D40 sur quatre points indépendants (zone AF de `modeScene_appliquerDefauts`, flash coupé de `flash_modesScene`, vitesse mini au flash d'`expo_limiterVitesse`, ordre physique de la molette dans `molette_versMode`) ; le mode Portrait reprend la netteté, les tons et la couleur du préréglage « Portrait » d'Optimiser l'image (saturation Normale au lieu d'Auto). Assistance AF coupée en Sport et Paysage (bit 0x40 de `0x83CE974E`). Le code B vaut le code A moins 4 pour les scènes (probable : la conversion elle-même n'est pas lue).

**Un mode « Street »** : remplacer les constantes d'une branche de `modesScene_reglages` (couleur, courbes, netteté) et, côté A, la ligne de programme et la vitesse mini du mode (§10). Candidat : un mode scène peu utilisé, par exemple Enfant (code B 7).

**Chargement de la puce à chaque photo** (vérifié, joué dans l'émulateur en octobre 2026, scénario `preglages-v1`) : `fiche_copierReglages` (`0x4793A`, tâche 5) recopie les réglages dans la fiche de prise de vue (+0x2C = `0x83CED224`… : +0x2D porte le mode couleur, bits 6-7, et le **mode d'optimisation, bits 2-5**, tels que les range le menu dans `0x83CED225`) ; `image_parametres` (`0x31A0F8`) calcule tout (`modesScene_reglages`, `couleur_chargerMatrice`, `tonalite_choisirNumero`) ; `isp_lancer` (`0x4B260`) appelle `isp_chargerPuce` (`0x4B41C`), qui copie la fiche dans les registres puis appelle `tonalite_construire` (`0x4B5B2`). Format des registres de matrice et de secteurs : **signe + grandeur** (bit 0x400 pour la matrice caméra, 0x200 pour YCbCr et secteurs). L'indice `_DAT_83eb3ab4` choisit à la fois la matrice caméra et le jeu de secteurs. **Ce que la fiche garde de la photo** (vérifié en octobre 2026) : `FUN_0004b168` n'appelle `image_parametres` que si la fiche n'a pas déjà ses paramètres (+0x73C ≠ 2 et, sauf demande, +0x1D bit 0x40 à 0 ; il pose ce bit après, `0x4B252`) ; sinon la puce est chargée depuis la fiche telle quelle, et les globales peuvent être celles d'une autre photo. Juste après `FUN_0031b362`, `image_parametres` recopie dans le bloc fiche +0x498 (pointé par `_DAT_83eb3a48`) une série de globales de la photo : +0x66 (fiche **+0x4FE**) = `_DAT_83eb3ab4`, +0x67 = `_DAT_83eb3ab0`, +0x68 = `_DAT_83eb3ab4` encore. Les fiches se copient d'un bloc (boucles de 0x734 ou 0x738 octets, dont `0x5BC50`, qui pose ensuite le bit 0x40). Le chemin des matrices en dur (`_DAT_83eb3d3c`) n'est pas recopié ; il laisse `_DAT_83eb3ab4` tel quel et met la matrice « lumière du jour » du groupe (n° 1 ou 13). Crochet des préréglages V1 sur cet appel : README, « V1 : code des préréglages ».

**Netteté, saturation, tons et teinte dans la puce** (mesuré dans l'émulateur en octobre 2026) : la netteté `_DAT_83eb3d20` (`+0x2C` bits 5-7, ou constante du préréglage) donne, par `FUN_003229ca`, le demi-mot `_DAT_83eb78ae` → fiche +0x3D8 → registre `0x40010054` (Moyennement élevée : `0x012C` en Ia, `0x0156` en IIIa, `0x010E` en N&B ; Auto en IIIa, scène de l'émulateur : `0x00D5`) ; le demi-mot suivant, `0x40010056` (`_DAT_83eb78be`), suit les tons, pas la netteté ni la saturation : `FUN_00322504` (appelée à `0x321D28`) l'interpole dans la table `0x3471FC`, ligne = `_DAT_83eb3aac`, posé dans le code du choix des matrices (`0x3211DE`–`0x321720`) et qui suit les tons (Normal 4, Moins de contraste 7, Plus de contraste 1, mesuré), colonne = `_DAT_83eb5858` borné à 120, par pas de 12 à partir de 60 (probablement l'ISO, en 1/12 d'IL) ; en N&B (`d1c`), table fixe `0x3471ED`. Mesuré : Ia Normal `0x0087`, Moins de contraste `0x0057`, Plus de contraste `0x0000` ; IIIa Normal `0x006F`, Plus de contraste `0x004B` ; N&B `0x0015`. Plus le contraste monte, plus la valeur baisse. **Rôle non établi** : le code du B ne fait que la calculer et l'envoyer à la puce, rien n'en dit l'usage (contraste ou niveau du noir : ni l'un ni l'autre ne se lit dans le code). La teinte (`_DAT_83eb3d34`, lue par `FUN_00322606`) n'agit que sur la matrice YCbCr : sur un Personnalisé en Ia, les 12 pages d'entrées-sorties touchées ont été comparées entre 0° et +9°, seuls `0x4001003B`–`0x40010045` changent ; les tons ne changent que la YCbCr, `0x40010057` et les trois courbes. La saturation `_DAT_83eb3d44` choisit, par `FUN_003232d8`, la table de 1 024 valeurs chargée en `0x4001EC00` (Rehaussée et Modérée la changent ; Auto suit la luminosité ; le N&B a la sienne) : elle agit donc aussi hors de la matrice YCbCr.

**Tables matérielles chargées au démarrage** (`0x4BE82`, vérifié) :
- `0xCA60C` (256 valeurs, droite 0→4095) vers `0x40010200` ;
- `0xC860C` (4 096 valeurs, racine carrée) vers `0x40010400` ;
- `0xC660C` (4 096 valeurs, carré) vers `0x40012400`, `0x40014400` et `0x40016400`, une par canal sans doute.

C'est le codage racine / carré classique d'un pipeline 12 bits. Rôle précis : hypothèse.

**Famille de 21 courbes 8 bits** à `0xD2750`–`0xD3B50` (256 octets chacune) : de très sombre à très claire, identité au milieu (`0xD3150`). Elles sont chargées par `0x66510` dans le moteur `0x40020000`, deux à la fois, choisies par deux tables d'index (`0xD3C50`, `0xD3CC9`, grille de 11 colonnes). Vérifié pour le mécanisme. Usage (D-Lighting, luminosité de retouche ou d'affichage ?) : hypothèse.

**Compression JPEG** : tables de quantification standard à `0xA23C4` (luminance) et `0xA2404` (chrominance). L'encodeur matériel est appelé par `0x49A7C` (640×480 pour le fond d'écran). Vérifié pour les tables.

**Modes scène** : `modesScene_reglages` (`0x31ED1A`), tableaux plus haut.

## 8. Fond d'écran perso

`fondEcran_enregistrer` (`0xAB3D8`, vérifié) :
1. redimensionne l'image choisie en 640×480 (YCbCr 4:2:2) ;
2. l'encode en JPEG avec l'encodeur matériel ;
3. efface le bloc flash de 64 Ko à `0x160000` ;
4. y écrit l'en-tête `NIKOND40_WP_USER` puis le JPEG à `0x160010` (65 520 octets au plus).

Le fichier d'usine contient à cet endroit `NIKOND40_WPVER01` et un JPEG de 16 Ko : c'est le fond d'écran d'origine. **On peut donc mettre un fond Pip-Boy d'usine dans le firmware** : remplacer ce JPEG **et changer la version de l'en-tête** (par exemple `NIKOND40_WPVER02`), sinon le flasheur ne réécrit pas le bloc (§3). Il ne le réécrit pas non plus si un fond perso est enregistré : le supprimer avant, ou passer par « Choisir le fond d'écran » avec une image, ce qui ne demande aucun flashage. Probable. Les routines flash (`flash_effacer` `0x6B40C`, `flash_ecrire` `0x6B41E`) tournent depuis la RAM.

## 9. Interface : palette et polices

- **Polices** : `0x1B064C` = largeur de chaque caractère sur 1 octet, `0x1B05E4` = pointeurs vers les largeurs des caractères sur 2 octets (`0x81 xx`…), lus par la mise en page du texte (`0x7C440`…). Vérifié.
- **Palette** à `0x1B0000` (vérifié) : 104 entrées de 4 octets `00 Y Cb Cr`. Preuve : `icone_dessiner` (`0x7C904`) prend la couleur de chaque tuile dans la table pointée par `0x83CE3FD8`, qui vaut `0x1B0000` (initialisée depuis la ROM `0x1584EC`) ; `osd_tracerBloc` (`0x7BD56`) écrit l'octet 1 dans le plan de luminance et les octets 2 et 3 dans les deux plans de chrominance. L'ordre Cb puis Cr est confirmé par les valeurs : l'entrée 1 (`46 58 F6`) est exactement le rouge pur (235, 0, 0) en BT.601. Une seconde palette de 3 octets à `0xD87C3` sert quand l'appelant impose une couleur. Le test `pipboy-palette.json` reste à faire pour voir quelles zones de l'écran changent.
- **Écran d'interface** : tampon YCbCr 4:2:0 en `0x83CE0230` (pointeur) : luminance 640×480 (ligne de `0x280` octets), puis deux plans de chrominance 320×240 à `+0x4B000` et `+0x5DC00`. Vérifié pour le format.
- **Icônes** (vérifié pour le mécanisme) : `tblIcones` (`0x157904`, RAM `0x83CE33F0`) donne pour chaque icône une liste de tuiles de 4 octets : position (quartets), indice de couleur dans la palette, planche et numéro de glyphe. Les descripteurs de planches (12 octets : largeur, hauteur, bits par pixel en `+6`, données en `+8`) commencent à `0x1B01A0` (pointeur `0x83CE3FDC`). Les entrées de menu y renvoient par leur numéro d'icône `0x8xxx`.
- **Primitives de dessin du menu** (arguments relevés à l'entrée dans l'émulateur, 1 unité = 2 points) : `rectangle_remplir` (`0x7D72A`, R4 = case {x, y, largeur, hauteur} en unités, R5 = couleur de `0xD87C3`) ; dégradé de la barre de sélection (`0x7E0A0`, même case) ; textes `0x7CDE2` (x en points au mot 2 de la pile), `0x7D00E` (x en points au mot 1), `0x7F5E4` (appelé par `FUN_0013e58c`, x en unités au mot 1) ; `icone_dessiner` (`0x7C904`, x et y en points dans R6 et R7) ; `osd_tracerBloc` (`0x7BD56`, R4 x, R5 y en points, R6 données 1 bit par point, poids fort d'abord, flux continu, 0 = transparent ; R7 = points par ligne ; pile : hauteur, Y, Cb, Cr). Vérifié (le bandeau du Pip-Boy est tracé avec).
- **Couleurs du menu** : tables indexées par 2 × style, style = `FUN_0004c1c2` (`style_courant`) = réglage CONFIG › Style écran infos : 0 en Classique, 1 en Graphique ou Fond d'écran (`0x83CE987C`, posé par `FUN_0004c1d4` d'après `0x83CED0FF`, bits 6-7 ou 4-5). Vérifié en octobre 2026, après le premier flash ([`recherche/ecran-reel-composition.md`](recherche/ecran-reel-composition.md)). Chaque table a donc deux colonnes, jeu 0 et jeu 1 ; les rôles ci-dessous et la palette Pip-Boy ont été relevés dans le jeu 1 seulement, d'où les menus bleu marine et vert du premier flash (boîtier en Classique). Depuis l'étape 6 du Pip-Boy, `style_courant` rend toujours 1 (`0x4C1CE` : `C0 04` → `C0 14`). Tables : fond `0xD8724`, filet de la colonne `0xD8728`, texte `0xD8744`, gris `0xD8748`, titre `0xD8750`, case de l'aide `0xD8758`. Les valeurs sont des indices de la palette `0xD87C3`. Vérifié.
- **Fonctions du menu nommées** : `menu_fond` (`0x146EE2`, fond et filet vertical de la colonne en x = 0x26), `menu_titre` (`0x146F44`, identifiant de texte, couleur), sous-titre (`0x147216`, probable), `onglet_actifDessiner` (`0x14777C`), `aide_icone` (`0x7ED4E`, pictogramme `0x8157`/`0x8158` en (6, 0xCF) unités), `aide_effacer` (`0x7EDF4`, case (6, 0xCF, 0x1B, 0x1B)), messages centrés `0x149220` et `0x14947C`.
- **Détourner une fonction d'interface** (étape 5 du Pip-Boy) : 8 octets à l'entrée, `LDI:32 #nouvelle,R12 ; JMP @R12` (NOP pour finir) ; le tremplin rejoue les instructions déplacées puis `LDI:32 #suite,R12 ; JMP @R12`. R12 et R13 sont libres à l'entrée d'une fonction (ABI : R0-R3, R12, R13 jetables ; R8-R11 conservés), R0 et R1 aussi quand le code d'origine les écrit avant de les lire (relu dans le code des 11 fonctions détournées). Dans l'émulateur, le tampon d'écran pointé par `0x83CE0230` vaut toujours `0x83BD6510`.
- **Écran d'infos de prise de vue** : son propre style, `0x83CEE4BF`, calculé par `FUN_0009b7ae` avec la même formule (0 Classique, 1 Graphique, 2 Fond d'écran ; plus de 2 → 0). Classique : tout est dessiné par le processeur (panneau cyan clair 0x6E, colonne 0x22, chiffres 0x71-0x74…), aucun JPEG. Graphique : fond JPEG 640 × 480 de `0xDFBB2` (0x2602 octets, 4:2:2, une DQT à deux tables, DHT standard), recopié en RAM par `FUN_000a6d70`, décodé par le codec `0x40030000` (`FUN_000690a4`, longueur `LDI:20` en `0xA6DE0`) et posé dans le tampon d'interface par le moteur `0x40020000`. Vérifié pour le code (recherche/ecran-reel-composition.md). Étape 6 du Pip-Boy : style forcé à 1 (`0x9B874` : `EC 02 C0 00` → `9F A0 C0 10`) et JPEG remplacé par un fond noir aux mêmes en-têtes.
- Les écrans et menus : §5 bis.

## 10. Firmware A : l'exposition

Le D40 a deux processeurs. Le B (ce fichier) gère l'image, l'interface, les fichiers, l'USB. **Le A calcule l'exposition** : aucune table de vitesses dans le B, et la liste des vitesses mini de l'ISO auto est dans le A. Vérifié pour l'ISO auto, probable pour le reste (mesure, autofocus, obturateur).

- `firmware/AD400111.bin` : 262 146 octets, en-tête `01 11 00 00 08 02 14 10` puis « D40 Firmware A Copyright Nikon Corp. ». Processeur FR lui aussi, avec son propre REALOS (« Softune REALOS/FR » en clair, 724 appels `INT #0x40`). Vérifié.
- **Chargé à `0xC0000`** : les 256 vecteurs sont à la fin du fichier (`0xFFC00`, l'adresse par défaut du FR), le dernier (reset) vaut `0xC0042`. Vérifié. Ghidra : 1 133 fonctions, script `D40ASetup.java`, symboles dans `desassemblage/symboles-A.tsv`.
- Contient aussi « CIPHERUNICORN-S COPYRIGHT (C) NEC CORPORATION 2006 », un chiffrement par blocs de NEC. Usage inconnu (authentification d'un accessoire ?). Hypothèse.
- CRC16 final identique au B (même calcul). `patch.py` sait maintenant patcher le A (`"firmware": "A"` dans le JSON, offset = adresse − `0xC0000`).

**Mise à jour du A et récupération** (vérifié en octobre 2026, [`recherche/etude-a/mise-a-jour-et-recuperation.md`](recherche/etude-a/mise-a-jour-et-recuperation.md)) :
- Côté B : `maj_chercherFichiers` prend `BD40????.BIN`, sinon `AD40????.BIN` (`majA_ouvrir` `0xABC6E`) ; taille 0x40002 (CRC du fichier entier vérifié) ou 0x40000 (**aucun contrôle**) ; commande **0x0D**, puis le A tire le fichier par blocs de 128 octets (**0x0F**, numéro de bloc), compte rendu **0x0E** (0x42 succès ; erreur : extinction sans nouvel essai).
- Côté A : 0x0D reçue → `0xCEDF4` (accord ou refus) → `0xCEE4C` → tâche 2 (`0xF8136`) → `0xF8000` arrête les tâches, recopie le **flasheur `0xF3000`–`0xF3AFF`** en RAM (`0x3D400`) et y saute ; il efface et réécrit `0xC0000`–`0xEFFFF`, `0xF0000`–`0xF3FFF`, `0xF8000`–`0xFFFFF` (reset, noyau, vecteurs, lui-même) et garde `0xF4000`–`0xF7FFF` (clés propres au boîtier, lues par `0xC1E92`) si l'octet 0x40 du fichier vaut 1.
- **Pas de chargeur protégé** : un A modifié qui ne démarre plus ne peut pas être reflashé par la carte. Et le B dépend du A : sans les commandes 0x14 et 0x19 l'interface ne démarre pas (tâche 15, attente sans délai), les flèches viennent du A (0x11), la batterie aussi (0x03, condition de l'écran « Mise à jour ? »). Vérifié dans l'émulateur avec un faux A muet.
- Place réellement libre et réécrite par la mise à jour : `0xF2256`–`0xF2FFF`, `0xF3B00`–`0xF3FFF`, `0xFE0DC`–`0xFEAFF` (7,2 Ko). `0xF4000`–`0xF7FFF` n'est jamais écrite.
- v1.12 de Nikon (`firmware/AD400112.bin`, en-tête `01 12 01 00 09 01 16 13`) : même format, flasheur et copieur identiques à l'octet près.

**ISO auto et vitesse mini** (vérifié) :
- Table `isoAuto_vitessesMini` à `0xFA876` : `336, 288, 240, 192, 144, 96, 48, 0`, en 1/48 d'IL avec 0 = 1 s. Ce sont les 8 choix du menu dans l'ordre (1/125, 1/60, 1/30, 1/15, 1/8, 1/4, 1/2, 1 s ; libellés D323 à D330 du B, identifiants `0x0143` à `0x014A`).
- `expo_limiterVitesse` (`0xC441E`) borne la vitesse entre un minimum et un maximum :
  - maximum `0x240` = 576 = 1/4000 s, ou une autre limite dans les modes flash ;
  - minimum selon le mode d'exposition (`DAT_0003c3c0 & 0xF`) : mode 8 → 1 s, mode 9 → 1/125 s, modes 10 à 15 → 1/60 s, sinon 30 s ; avec l'ISO auto actif (`DAT_0003d0bc & 2`), la valeur de la table à l'indice réglé par l'utilisateur (`DAT_0003d25b`).
  - Le minimum par mode ne joue **que si le flash part** (état `0x3C3C1 & 0x1F` = 3, 5 ou 0xD ; le maximum devient alors la vitesse de synchro, `expo_vitesseMaxFlash`) : Portrait de nuit 1 s, Gros plan 1/125 s, autres scènes 1/60 s, P et A 1/60 s (30 s en synchro lente), S et M 30 s. C'est le tableau du manuel du D40. Sans flash : 30 s, ou la table de l'ISO auto si elle est active (pas en S ni en M). Vérifié.
- Juste avant la table : `36, 42, 48, 54, 60` (pas de 6, soit 1 IL en 1/6 d'IL) : probablement les sensibilités max de l'ISO auto, ISO 200 à 3200. Hypothèse.

**Recette pour un ISO auto façon Fuji** (non testée) :
1. Remplacer les 8 valeurs du A par des vitesses plus rapides, par exemple 1/500 à 1/4 : `432, 384, 336, 288, 240, 192, 144, 96`.
2. Réécrire les libellés D323 à D330 du B. Ils sont contigus (43 octets en anglais) : « 1/500 », « 1/250 »… tiennent dans la place, en déplaçant les pointeurs D324 à D330 dans la table D de chaque langue.

Une vitesse mini « auto » liée à la focale demanderait du code dans le A (la focale y est connue). Le risque est propre au A : s'il ne démarre plus, la mesure et l'obturateur sont perdus. On ne sait pas encore si le B peut le reflasher dans cet état.

**Modes, flash et programmes** (côté A) :
- `molette_lire` (`0xC802C`) : code de mode `0x3C3C0` = `molette_versMode[position]` (`0xFAB38` : `00 01 02 03 08 09 0A 0B 0C 0D 0E 0F`). Bit 3 = mode scène. Codes : 0 P, 1 S, 2 A, 3 M, 8 Portrait de nuit, 9 Gros plan, 10 Sport, 11 Enfant, 12 Paysage, 13 Portrait, 14 Auto sans flash, 15 Auto : les positions 0 à 11 suivent le tour de la molette (P S A M, puis les scènes de Portrait de nuit à Auto). Vérifié pour la table ; identités par recoupement (§7).
- **Flash** : réglage choisi (`0x3C3C6`) → comportement, par `flash_modesPSAM` (`0xFAB44`, 4 × 5) et `flash_modesScene` (`0xFAB58`, 8 × 5) ; bits 1 second rideau, 2 synchro lente, 4 atténuation des yeux rouges, 8 flash coupé. En scène, les lignes Sport, Paysage, Auto sans flash valent toutes 8 ; Portrait de nuit est en synchro lente. Vérifié pour les tables, sens des bits probable (il colle aux 5 modes flash du manuel en P et A : normal, yeux rouges, yeux rouges + lente, lente, second rideau + lente).
- **Programme d'exposition** : `expo_programme` (`0xC3F84`) puis une fonction par mode : P `0xC60E2`, S `0xC617E`, A `0xC61BC`, M `0xC61FA` (toutes bornées par `expo_limiterVitesse`) ; en scène, deux séries de 8 fonctions : `0xC488E`…`0xC5616`, chacune appelant sa ligne `ligneScene_*` (`0xC48E0`…`0xC5674`, du code et non une table : segments choisis selon Ev, avec une pente), et `0xC58D6`…`0xC5F82` (`isoAutoScene_*`, l'ISO auto des scènes ; anciennement nommées `progScene_*` à tort). Choix par le bit 0 de `0x3E1E0` (rôle exact inconnu). Unités vérifiées : 1/48 IL, Tv 0 = 1 s, Av 96 = f/2, Ev = Tv + Av à l'ISO courant. `expo_ligneProgramme` (`0xC41C2`) : en P sans flash, deux pentes ½ autour de Ev 12, Tv0 = 1/125, 1/250 ou 1/500 selon la focale (seuils 57 et 138 mm). Portrait plafonne à f/2,8 et Sport à f/2. ISO auto : tout est calculé dans le A, le B n'envoie qu'un octet (`0x83CE974F`, commande 0x05) ; plafond 1600 codé en dur. Détail, lignes perso, MTF, menus : [`recherche/programmes-expo-iso-auto.md`](recherche/programmes-expo-iso-auto.md).
- **Lignes de programme du projet** (patch du A, `outils/programmes_a.py`, mis au point dans l'émulateur, non flashé ; vérifié dans l'émulateur) : la fonction de P appelle sa ligne par `LDI:20 #0xC41C2,R12 ; CALL @R12` en `0xC60F4` (constante détournée vers `ligne_perso`, `0xF2400`) ; `expo_limiterVitesse` lit la vitesse mini de l'ISO auto en `0xC452A`–`0xC453E` (`isoAuto_vitessesMini[0x3D25B & 0xF]`, R4 utilisé dès `0xC4546` ; détour vers `vitesse_mini`, `0xF2480`). Plancher d'ouverture `0x3CCB9` (×8, lu par `FUN_000c4680`, qui borne Av entre ce plancher et Av max = `0x3D100` × 4), focale codée `0x3D0F0` (f = 5·2^(x/24) mm ; 1/(f × 1,5) en Tv = 2x + 140). Des 14 lectures de `0x3D25B` (LDI:20), seule `0xC452A` lit le quartet bas ; les autres, le bit 7 (ISO auto actif) ou les bits 4-6 (ISO maxi, tables `0xFA86C` et `0xFDE3E`). Lu au-delà de ses 8 cases, le tableau de Nikon rend `0x000C` ou `0x40xx` (quartets 9 à 15). En 1.12 : même code décalé de 0xF6 octets, variables `0x3E1xx` décalées de 0x10, reste de la RAM et tables aux mêmes adresses.
- **Autofocus** : la zone AF est réglée dans le B (`modeScene_appliquerDefauts`, §7) et envoyée au A. Le pilotage du module AF lui-même n'est pas localisé.

## 10 bis. Liaison entre le B et le A

Tâche 14 (`tsk14_prio04`, `0xA9280`), vérifié pour la mécanique :
- **Liaison série 0 du FR en mode synchrone** (`SMR0 = 0xB8`, `SCR0`, données dans `SDIR0`), minuterie 2 comme délai de garde (`TMRLR2 = 32999`), lignes de poignée de main sur les ports `0x50000104` (bit 6, le A est prêt) et `0x50000106`/`0x50000305`.
- **48 commandes** (0x00 à 0x2F) décrites par `tblCommandesA` (`0xE482C`, 16 octets) : tampon en RAM, longueur, sens (1 = le B envoie, 0 = le B reçoit, 2 = longueur variable), fonction de fin. Liste complète avec les appelants : `outils/liaison_a.py --pseudo-c d40-tout.c`, résultat dans `desassemblage/liaison-a.tsv`.
- **Échange** : une tâche du B appelle `liaisonA_envoyerCommande(n)` ; la commande entre dans la file `0x83CEE4FC` (drapeau `0x80` ; `0x40` si elle y est déjà, pour la renvoyer). La tâche 14 envoie le numéro de commande, puis la longueur et les données (copiées dans `0x83CEE85A`) avec une somme de contrôle par addition (probable) ; à la réception, les octets (`0x83CEE75A`) sont recopiés dans le tampon de la commande ; puis la fonction de fin est appelée. Le A peut lui-même demander une commande (`0x83CEE961`) : les 28 commandes « A → B » n'ont aucun appelant dans le B.
- **Bloc 0x05 et son écho** (vérifié, octobre 2026, code et émulateur) : `liaisonA_preparer` (`0xA9516`) recopie le bloc à envoyer en `0x83CEE85A` ; la somme de contrôle est faite octet par octet à l'émission (`0xAA9F4`–`0xAAA02`). Le A répond par 0x06 (`0x83CE975B`, 14 octets, copie de son bloc `0x3D259` faite en `0x3D267`) ; la fin de 0x06 (`0xA9BF4`) compare au bloc du B, et s'ils diffèrent **recopie l'écho dans le bloc du B** (le A fait foi), puis renvoie 5 ; `FUN_00132c3e` renvoie aussi tant que les deux diffèrent (500 tics). À la réception de 0x08, `0xA9D88` recopie `0x83CED100` bit 2 dans le bit 7 de `0x83CE974F` quand l'ISO change et renvoie 5. **Démarrage** (`FUN_0004044c`, tâche 4, branche `0x50000105` bit 1 = 1) : le B recopie sa sauvegarde `0x83CED254` (14 octets, bloc 3 des réglages gardés, écrite par `FUN_000403fa` depuis `0x83CE974D`) dans `0x83CE974D`, puis envoie 1, 7 et 5 ; c'est le B qui fait foi au démarrage. Côté A, table des commandes vers `0xFB528`, 12 octets par commande (variable, tampon de liaison, longueurs reçue et envoyée, délai ; ordre des champs probable) : 5 = `0x3D259` ← `0x3E53F`, 14 octets reçus ; 6 = `0x3D267` → `0x3E54D`, 14 octets envoyés.
- Commandes repérées (probable) :
  - **0x07**, B → A, 9 octets à `0x83CE957B` (21 appelants) : les réglages de prise de vue (qualité `957C`, balance `957E`, Optimiser l'image dans le quartet haut de `957F`) ; **0x08**, A → B, 9 octets à `0x83CE9572` : sans doute le même bloc relu, le A gardant les réglages (hypothèse : c'est lui qui a l'EEPROM) ;
  - **0x05**, B → A, 14 octets à `0x83CE974D` (30 appelants) : réglages perso, dont le mode (`974D`), l'assistance AF (`974E` bit 6), la zone AF (`9759`) ;
  - **0x0B**, B → A, 4 octets à `0x83CE971D` (35 appelants) : la commande la plus envoyée, rôle inconnu ;
  - **0x14**, A → B, 13 octets à `0x83CE9823` : contient le code de mode de la molette (quartet haut de `9823`) ;
  - **0x24**, A → B, 196 octets à `0x83CE9652`, et **0x1C**, 132 octets à `0x83CE976F` : les plus gros blocs reçus (mesure ? informations objectif ?), à décoder.
- Le format exact des octets sur le fil (ordre, somme de contrôle) est dans les gestionnaires d'interruption de la liaison série, mal décompilés : à lire en assembleur si on veut écouter la liaison.

## 11. Pas encore cartographié

- Le contenu des commandes 0x0B, 0x1C, 0x24 et des autres blocs A → B ; le format octet par octet sur le fil (§10 bis).
- Les unités de `expo_ligneProgramme` et le rôle du bit 0 de `0x3E1E0` (§10) ; le pilotage du module autofocus dans le A.
- Les deux autres champs de la table de paramètres (bits 6-10 et 11-15) et le calcul de la classe Auto des tons.
- Le rôle des tâches sans indice.
- Les régions `0x2D0000`–`0x2D2FFF` (sans doute du texte pris pour du code) et `0x394000` (code appelé par le PTP).
