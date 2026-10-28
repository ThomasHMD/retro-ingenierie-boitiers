> Rapport d’octobre 2026. Ses fichiers utiles sont copiés dans `recherche/ecran-reel/` (outils `coins2.py` et `comparer.py`, scénarios `sc-*.txt`, planches, patch d'essai `essai-style1.json`) ; les chemins `…/scratchpad/ecran-reel/` ci-dessous y renvoient. Les firmwares d'essai ne sont pas copiés (à refaire depuis le patch).

> **Suite (octobre 2026, soir)** : Thomas a choisi le style Graphique partout. Retenus : la correction B (menus) et la correction C (fond JPEG noir), plus le forçage de l'écran d'infos en Graphique (`0x9B874`). Le §4.1 est fait (`--style` de l'émulateur). Détail et contrôles : README, « Premier flash et reprise dans le cloud ».

# Écran réel du D40 contre l'émulateur : pourquoi le menu Pip-Boy est bleu, blanc et vert sur le boîtier

Enquête d’octobre 2026, firmware flashé `build/v1-sans-bandeau/BD400111.BIN` (sha256 `49b40233…`, refait à l'identique par `patch.py patchs/v1-sans-bandeau.json`). Aucun fichier du projet n'a été modifié ; tout ce qui a été produit est dans ce dossier (`ecran-reel/`). **[V]** = vérifié (code lu, octets, trace de l'émulateur) ; **[H]** = hypothèse.

## En une phrase

Il n'y a ni plan vidéo caché, ni transparence, ni image sous les menus : **les menus du D40 ont deux jeux de couleurs, choisis par le réglage « Style écran infos »** (Classique = jeu 0, Graphique ou Fond d'écran = jeu 1). L'émulateur démarre en Graphique (jeu 1), le boîtier de Thomas est en Classique (jeu 0), et le patch de couleurs Pip-Boy n'a recoloré que le jeu 1, plus une plage 0x21–0x41 qui attrape par accident le fond des listes du jeu 0. Mis en Classique (`poke8 0x83CED0FF 0x00`), l'émulateur reproduit le boîtier : fond bleu marine, colonne claire, lignes des sous-écrans vertes, écran d'infos clair (planche `planche-boitier-vs-emulateur.png`).

## 1. Comment l'écran est composé

### Chaîne d'affichage [V, traces de l'émulateur et pseudo-C]

1. **Tout est dessiné dans le tampon d'interface** (OSD) pointé par `0x83CE0230` (= `0x83BD6510`) : 640×480, Y puis Cb (+0x4B000) et Cr (+0x5DC00) en 320×240. Le CPU y écrit (`rectangle_remplir` `0x7D72A`, textes, icônes, `osd_tracerBloc`) ; le moteur 2D `0x40060000` n'y fait que l'effacement plein écran (`osd_effacer` `0x7D5FA`, commande `0x47vv`, vv = octet Y, Cb ou Cr de la palette `0xD87C3`) et, en style Graphique seulement, des copies de rectangles (commande `0x4600`, voir plus bas).
2. **Le moteur de redimensionnement `0x40020000` recopie l'OSD dans une image d'écran** (`FUN_00069730` pour le LCD, `FUN_00069808` pour la sortie vidéo, appelées par la tâche 18). Programmation dans `FUN_00060172` : **source = `0x4002100C`, destination = `0x40021008`** (la CARTE §7 dit l'inverse : à corriger), largeur/hauteur de destination `0x40020008`/`0x40020006`, pas source `0x40021006`, pas destination `0x40021004`, pas de l'échelle `0x4002000C`/`0x4002000A` (8.8, calculés par `0xBE78C`), valeur de remplissage `0x4002002E` (0x00 pour Y, 0x80 pour Cb/Cr), mode par la table `0xD0638`.
   - LCD : Y 640×480 → 960×240 dans un tampon intermédiaire `0x83A2E900` (pas 0x3C0) puis deuxième passe (`0x6A6F8`, registres `0x40020038`–`0x4002004C`) vers l'image d'écran ; Cb et Cr 320×240 → 480×120.
   - Vidéo : 640×480 → 640×432 centré à (32, 24) dans une image 720×480 (`+0x43A8`).
3. **Deux images d'écran en alternance**, `0x83A66D10` et `0x83AE6510`, d'abord remplies de noir par le moteur 2D (commandes `0x6F00` Y = 0 et `0x6F80` C = 0x80, `FUN_000698d4`, `FUN_000699da`).
4. **Le contrôleur d'affichage `0x40040000` lit une seule image** : adresse Y `0x40040308`, décalages Cb/Cr `0x4004030C`/`0x40040310` (LCD : 0x38400 et 0x46500), taille `0x40040318`/`0x4004031A` (LCD : 960×240 ; vidéo : 720×480), marche `0x40040300` = 0x4002 (LCD) ou 0x4000 (vidéo), sortie `0x40040004` = 0x4000 (`FUN_00069b22`, tâche 18). Matrice YCbCr→RGB en `0x40040044`–`0x4004004C`, recopiée (`FUN_00069ade`) d'un bloc de réglages pointé par `0x83EB3A44` (+0x16A), valeurs par défaut en ROM `0xE252E` : `40 00 5A | 40 EA D3 | 40 71 FF | 00`, soit /64 : R = Y + 1,406 Cr ; G = Y − 0,344 Cb − 0,703 Cr ; B = Y + 1,766 Cb. C'est la conversion JFIF **pleine échelle**, sans décalage de 16 [H fort : rôle déduit des valeurs ; un boîtier réel peut avoir des valeurs calibrées différentes].

**Pas de plan sous l'OSD, pas de couleur clé, pas d'alpha matériel** : le seul registre d'adresse de plan écrit est `0x40040308`, et l'image d'écran ne reçoit que du noir puis l'OSD redimensionné [V pour les écrans tracés : démarrage, écran d'infos, menus ; H pour la visualisation et le menu Retouche, non tracés]. La transparence n'existe qu'en logiciel : bit 0 des glyphes de `osd_tracerBloc` non écrit (CARTE §9), et sauvegarde/restauration de rectangles par le moteur 2D (Graphique).

### D'où viennent le bleu marine et la colonne claire [V]

Ce sont des **remplissages du CPU (et un effacement du moteur 2D) avec des entrées de la palette `0xD87C3`**, choisies dans des tables à deux colonnes (style 0, style 1) :

- `style_courant` (`0x4C1C2`) rend 0 ou 1 : `*(0x83CE987C) != 0` [V, désassemblage] ; `0x83CE987C` est écrit par `FUN_0004c1d4` = bits 6-7 de `0x83CED0FF` si `(0x83CE98D9 >> 4) ≤ 3`, sinon bits 4-5 [V]. Ces deux champs sont les deux réglages « Style écran infos » (P, S, A, M et Prog. résultat optimal : 0 Classique, 1 Graphique, 2 Fond d'écran, `desassemblage/menus.txt` écrans 77-78) [V pour les valeurs 0/1/2, H pour l'attribution exacte des bits 6-7 aux modes P, S, A, M]. `0x83CE987C` n'apparaît que deux fois dans le binaire (`0x4C1C4`, `0x4C1E4`) : seul `style_courant` le lit [V].
- L'émulateur démarre avec `0x83CED0FF = 0x51` (Graphique partout) [V, `peek`]. Le boîtier de Thomas est en Classique pour le mode où il était [V par la reproduction ci-dessous].

Rôles relevés (traces `watchw` sur des points de l'écran, appelants lus) :

| Table | Rôle | Style 0 (boîtier) | Style 1 (émulateur) |
|---|---|---|---|
| `0xD8758` | effacement plein écran (`osd_effacer`, commande 0x47E3/0x4780/0x477B en style 0) **= fond de la colonne des onglets** | **0x13** blanc (237, 249, 245), non recoloré | 0xAD → noir |
| `0xD8724` | fond du menu (`menu_fond`, RP `0x146F0E`) et case de l'onglet actif | **0x17** bleu marine (15, 21, 42), non recoloré | 0xC8 → noir |
| `0xD8728` | filet de la colonne | 0x19 ardoise | 0xC9 → vert filet |
| `0xD872C`/`0xD8738`, `0xD8730`/`0xD8734` | cases des onglets inactifs (`FUN_00147464`) | 0x50/0x4F, 0x4E/0x4D gris clairs, non recolorés | 0xCA…0xCD → vert sombre |
| `0xD873C` | lignes des écrans de tête (`FUN_001483dc`) et bande de retrait à gauche des listes (`FUN_001478ae`, RP `0x1478E4`) | **0x51** ardoise (44, 47, 67), non recoloré | 0xCE → noir |
| `0xD8740` | **zone de liste des sous-écrans** (`FUN_00148484`, RP `0x1484D6`) | **0x22, recoloré en vert** | 0xCF → noir |
| `0xD8744` | texte | 0x01 → vert | 0xD2 → vert |
| `0xD8748` | texte grisé | 0x0D gris, non recoloré | 0xD1 → vert doux |
| `0xD8750` | titre | 0x12 → vert filet | 0xD0 → vert |

Tableau complet des 40 tables (`0xD8720`–`0xD87BC`) avec couleurs d'origine et V1 : `tables-roles.txt`.

**Écran d'infos** : `FUN_0009b7ae` calcule son propre style (`0x83CEE4BF`, même formule sur `0x83CED0FF`) [V] :
- Classique (0) : tout au CPU avec les entrées 0x6E (panneau cyan clair), 0x75, 0x76, 0x49, 0x4A, 0x22, plus 0x17/0x19/0x51 ; **aucun JPEG, aucune copie 0x46xx** (journal du moteur 2D) [V]. C'est le « fond clair blanc / bleu ciel » de la vidéo : l'écran Classique de Nikon, que le patch n'a presque pas touché.
- Graphique (1) : `FUN_000a6d70(0x22)` recopie en RAM le **JPEG de `0xDFBB2`** (9 730 octets, 640×480 : dégradé gris clair avec un disque gris et une bande à droite, extrait `jpeg/0dfbb2.jpg`), le décode avec le codec `0x40030000` (`FUN_000690a4` ; sorties Y `0x83902900`, Cb `+0x4B000`, Cr `+0x25800` : 4:2:2 planaire) puis le pose dans l'OSD par le moteur de redimensionnement, l'entrée 0x22 servant de valeur de remplissage [V pour le code, H pour le rôle de 0x22]. Ensuite le fond est sauvé (`0x4600` OSD → `0x83B65D10`) et restauré par rectangles (52 copies `0x4600` au démarrage). **Sur le boîtier en Graphique, l'écran d'infos Pip-Boy aura donc ce fond gris clair**, pas le noir de l'émulateur [H pour le rendu, V pour le chargement].
- Fond d'écran (2) : `FUN_000ab24e` (fond utilisateur, flash `0x160010`) et une bande en 0xB1 [V].

## 2. Pourquoi les lignes des sous-écrans sont vertes

Ordre de dessin d'un sous-écran (Programme), relevé par `watchw` sur les points (400, 160) et (120, 160) en style 0 [V] :
1. `menu_fond` remplit en 0x17 (Y = 0x23) ;
2. `FUN_00148484` remplit toute la zone de liste {x 0x2A, y 0x28 ou 0x43, l 0x10B, h 0xC4 ou 0xA8 unités} avec `0xD8740[style]` → **0x22, vert (Y = 0xA4)** ;
3. `FUN_001478ae` repeint la bande de retrait de chaque ligne (0x2C unités = 88 points) en `0xD873C[style]` → **0x51 ardoise (Y = 0x3A)** : c'est la bande bleu marine à gauche ;
4. le texte est tracé en `0xD8744[style]` = 0x01 → vert sur vert, illisible ; la ligne choisie reçoit la barre (dégradé 0x21–0x41, vert) et le texte noir : seule lisible.

La primitive est `rectangle_remplir` (`0x7D72A`, CPU), pas le dégradé `0x7E0A0`. **Ce que nos patchs ont changé** : `outils/pipboy.py` met en vert `list(range(0x21, 0x42))` (rôles relevés par sonde dans l'émulateur, donc en style 1 seulement, pour le dégradé de la barre) ; 0x22, 0x32, 0x33, 0x34 sont aussi des couleurs du style 0 (fond de liste et autres rôles), passées en vert par accident. Toutes les entrées propres au style 1 (0xC8–0xDE, 0xAD, 0x93) ont été recolorées, presque aucune du style 0 [V, `tables-roles.txt`].

**Ce que l'émulateur fait différemment du matériel pour ces points : rien.** Le dessin est le même code ; seul le réglage de départ diffère. Avec `poke8 0x83CED0FF 0x00`, l'émulateur montre exactement l'image du boîtier [V : `sorties/comp-00/programme.png`, `preglage.png`].

Détail de la vidéo : à 13,5 s, « Portrait » et « Street » sont à demi visibles parce que la barre change de ligne pendant la pose (rémanence du LCD) [H].

## 3. Corrections possibles

### A. Sans flasher : régler le boîtier
CONFIG › Style écran infos › les deux lignes sur **Graphique**. Les menus deviennent ceux de l'émulateur (style 1) [V dans l'émulateur, H sur le boîtier]. Prix : l'écran d'infos Graphique aura le fond JPEG gris clair de Nikon sous les éléments verts.

### B. Firmware, 2 octets : menus toujours dans le style 1 (essayé dans l'émulateur)
`0x4C1CE` (offset fichier `0xC1CE`) : `C0 04` (`LDI:8 #0,R4`, créneau de délai du `BEQ:D`) → **`C0 14`** (`LDI:8 #1,R4`). `style_courant` rend alors 1 sur les deux chemins. L'instruction changée reste un `LDI:8`, permis dans un créneau de délai (les gardes de l'émulateur passent).
- Essai `essai-style1.json` = `v1-sans-bandeau.json` + ce patch (145 patchs, sans chevauchement), firmware `fw-essai-style1/BD400111.BIN` (CRC `e8a3`, à ne pas flasher en l'état) [V].
- En Classique (`0x83CED0FF = 0x00`) : PRISE DE VUE, Programme, Préréglage, PERSO, aide : **0 point différent** des captures en style 1 ; l'écran d'infos reste Classique (0 point différent de l'écran Classique) [V].
- Scénario `secours` joué en Classique : firmware flashé 91 contrôles OK et 20 échecs (tous des couleurs de points de l'OSD, la navigation vers Version du firmware et « Mise à jour ? » passe : 60 contrôles de pointeur et de mode OK) ; firmware essai 111/111 [V]. La voie de secours fonctionne donc déjà sur le boîtier, seules ses couleurs diffèrent.
- Les 126 appelants de `style_courant` sont du code d'interface (122 entre `0x120000` et `0x153000`, plus `0x5A76C`, `0x7EDF4` aide_effacer, `0x7F414`) ; l'écran d'infos ne l'utilise pas [V pour la liste des appelants et les deux occurrences de `0x83CE987C` ; H : pas d'autre lecteur par adresse calculée, rôle de `0x5A76C` non lu].

Variante sans code : recopier dans les tables `0xD8720`–`0xD87BF` la colonne style 1 sur la colonne style 0 (et le bloc d'icônes par style `0xD97C4`, pas 0x30). Plus long, et il peut exister d'autres tables par style : B est plus sûr.

### C. Écran d'infos Graphique noir (données seulement)
Remplacer le JPEG `0xDFBB2` (offset `0x9FBB2`, 0x2602 octets, suivi immédiatement d'autres données en `0xE21B4` : pas de place en plus) par un fond Pip-Boy sombre **de même structure** : JPEG de base, 640×480, Y 2×1 / Cb 1×1 / Cr 1×1 (4:2:2), une DQT à 2 tables, DHT standard (418 octets), sans APP0 ni intervalle de reprise [V pour la structure d'origine]. Un fond uni ou presque tient en 2 à 4 Ko. La longueur 0x2602 est codée deux fois (`LDI:20` en `0xA6DB4` et `0xA6DE0`) : garder la longueur et compléter par des zéros après EOI [H : le codec s'arrête à EOI], ou changer les deux constantes. Non testable dans l'émulateur tant que le codec n'est pas émulé (§4).

### D. Écran d'infos Classique au vert (facultatif)
Recolorer ses entrées (0x6E, 0x75, 0x76, 0x49, 0x4A, 0x22, 0x17, 0x19, 0x51…). Avec B, les menus n'utilisent plus les entrées du style 0, mais d'autres écrans peuvent les partager : à sonder d'abord, comme pour la V1, avec l'émulateur en Classique [H].

### E. Le noir
Le contrôleur convertit en pleine échelle [H fort] : l'entrée « noire » 10 80 80 (Y = 16) donne (16, 16, 16) sur le LCD, un gris très sombre. Pour un noir franc, Y = 0 (comme l'entrée 0x00 `00 80 80`) [H].

## 4. Ce qu'il faut ajouter à l'émulateur

Par ordre d'utilité :
1. **Le style écran infos comme paramètre** (fait sans rien changer au code : `poke8 0x83CED0FF <v>` à 1 M instructions, avec la langue). Jouer chaque scénario d'interface en Classique (`0x01`) et en Graphique (`0x51`, valeur de départ de l'émulateur), voire Fond d'écran (`0xA1`) ; par défaut, les réglages du boîtier de Thomas. Mes essais ont utilisé `0x00`, qui change aussi le bit 0 (autre réglage, non identifié) : sans effet sur les menus (l'essai B à `0x00` est identique au point près aux captures à `0x51`) [V], effet sur l'écran d'infos non vérifié. Un `expect8` de couleur ne vaut que pour un style. C'est la seule correction nécessaire pour retrouver ce que filme Thomas [V].
2. **Codec JPEG `0x40030000`** : au lancement (`0x40030F20` ← 0x4001), lire le JPEG en `0x40030F28` (longueur passée à `FUN_000690a4`, 0x2602 ici), le décoder (ImageIO, puis RVB → YCbCr pleine échelle, ou un décodeur qui rend le YCbCr brut) et écrire Y, Cb, Cr en 4:2:2 planaire aux adresses `0x40030F10`, `0x40030F14`, `0x40030F18` ; lever l'état prêt. Donne les fonds Graphique et Fond d'écran.
3. **Moteur de redimensionnement `0x40020000`** : un vrai changement d'échelle (plus proche voisin suffit) avec les registres du §1 (source `0x4002100C`, destination `0x40021008`, pas, tailles, remplissage `0x4002002E`). Nécessaire pour que le JPEG décodé arrive dans l'OSD, et pour l'image d'écran LCD.
4. **Moteur 2D, commande `0x46xx`** (copie de rectangle : source `0x40060094` pas `0x4006008C`, destination `0x40060098` pas `0x4006008E`, taille `0x40060090`×`0x40060092` ; `0x40060084` = 0 et `0x40060088` = 0xFFFFFFFF, sans doute couleur clé et masque [H]) et `0x6Fxx` (remplissage, comme `0x47xx`). Aujourd'hui ni l'une ni l'autre n'agit (seuls `0x47xx` et le bit 0x2000 sans 0x4000 sont émulés) : sauvegarde et restauration du fond de l'écran d'infos Graphique, d'où les restes signalés dans le README de l'émulateur.
5. **Capture « ce que montre le LCD »** : lire l'image désignée par `0x40040308` (+ `0x4004030C`, `0x40040310`, taille `0x40040318`×`0x4004031A`) et convertir avec la matrice `0x40040044`–`0x4004004C` (pleine échelle) au lieu de la conversion BT.601 à décalage 16 de `Ecran.java`. Garder la capture de l'OSD (plus nette) pour les contrôles de points.

## 5. Vérifier contre les images du boîtier

Outils écrits pour cette enquête (dossier `recherche/ecran-reel/outils/`, à reprendre dans le projet si utile) :
- `coins2.py <photo>` : trouve les 4 coins de l'écran (masque teinte bleue ou verte, ou très clair peu saturé ; la peau est exclue) ; à corriger à la main quand un doigt mord sur un coin (écran d'infos à 8,5 s).
- `comparer.py <photo> <4 coins> <sortie> <capture>…` : redresse l'écran en 640×480 (les lignes, la colonne et le titre tombent au point près sur l'émulateur) et classe une grille 32×24 en vert, bleu, clair, sombre, robuste à l'exposition du téléphone ; score = part des cases de même classe.

Résultats (images redressées dans `frames/redresse-*.png`, planche `planche-boitier-vs-emulateur.png`) [V] :

| Image du boîtier | Émulateur Classique (0x00) | Émulateur Graphique (0x51) |
|---|---|---|
| 10,5 s PRISE DE VUE | 72 % | 5 % |
| 13,5 s Programme | 84 % | 11 % |
| 23,5 s Préréglage | 76 % | 12 % |
| 28,5 s PERSO | 55 % (reflet sur la droite, réglages perso différents) | 3 % |
| 8,5 s écran d'infos | 61 % (bandeau « Objectif non monté », que le faux A n'envoie pas) | 2 % |

Un contrôle mécanique possible : pour chaque capture de référence du boîtier, un seuil (par exemple 70 % en Classique) et un écart d'au moins 40 points avec l'autre style.

## 6. À corriger dans la doc (non fait, lecture seule)

- CARTE §9 : « style = `FUN_0004c1c2` » → c'est le réglage Style écran infos (0 Classique, 1 Graphique ou Fond d'écran) ; les rôles relevés et la palette Pip-Boy ne valent que pour le style 1.
- CARTE (redim_lancer, symboles) : source `0x4002100C`, destination `0x40021008`, et non l'inverse.
- README de l'émulateur, limite 1 : le fond JPEG n'existe qu'en Graphique (et Fond d'écran) ; en Classique l'écran d'infos est entièrement dessiné au CPU et l'émulateur le rend fidèlement. Le moteur de redimensionnement ne sert pas qu'au LCD : il pose aussi les JPEG décodés dans l'OSD.
- README, « Ce qu'un test réussi prouve » : ajouter que les couleurs ne valent que pour le style simulé.

## Fichiers (tous dans ce dossier)

- `planche-boitier-vs-emulateur.png` : boîtier redressé, émulateur Classique, émulateur Graphique, 5 écrans.
- `planche-styles.png` : les 6 écrans dans les deux styles.
- `tables-roles.txt` : les 40 tables de couleurs, couleurs d'origine et V1.
- `essai-style1.json`, `fw-essai-style1/BD400111.BIN` : essai de la correction B (ne pas flasher sans passer par le build du projet).
- `jpeg/` : les JPEG intégrés (`0dfbb2.jpg` fond Graphique, `160010.jpg` fond d'écran d'usine, `152940.jpg` PictBridge, `0e8fe4.jpg`).
- Scénarios `sc-*.txt`, journaux `log-*.txt`, captures `sorties/`.
