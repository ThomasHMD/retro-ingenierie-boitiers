# D200 B 2.01 : choix du jeu de matrices, teinte, saturation

Lecture du pseudo-C `d200-tout.c` (numéros de ligne = lignes de ce fichier) et des octets de `B2000201.bin` (adresse − `0x50000` = offset fichier). Rien n'a été modifié dans le projet. Chaque fait porte un statut : **vérifié** (lu dans le code ou les octets, ou recalculé par script sur les octets) ou **hypothèse** (déduit, non lu tel quel).

Lecture faite en octobre 2026 par un agent (scripts jetables non gardés) ; note recopiée depuis le chantier Ghidra.

## 0. En trois phrases

1. Le numéro de jeu n'est pas lu dans un arbre opaque : c'est **`jeu = 42 × E + 7 × F + (6 − K)`** avec E = classe de traitement couleur (mode I/II/III × espace Adobe), F = « famille » d'éclairage (température de couleur estimée, classe d'illuminant, drapeau de l'octet `0xA1`), K = « cran » = numéro de courbe modulo 7. Vérifié sur 8 918 combinaisons (traduction mécanique de l'arbre, 0 écart).
2. **La teinte ne passe ni par un jeu ni par les secteurs** : `FUN_000d846a` (`0xD846A`) tourne les lignes Cb et Cr de la matrice YCbCr déjà choisie, avec une table de 7 rotations à `0x388318`. Vérifié ; elle reproduit vos angles mesurés à un décalage constant près.
3. **La saturation ne passe pas par le jeu** : elle choisit une colonne parmi 48 d'une table 1024 × 48 à `0x3A62DD`, copiée vers `0x5001EC00`. Auto/Normale/Modérée/Accentuée = colonnes de niveau 0 (Auto selon la scène)/0/7/6. Vérifié (chemin et valeurs), cohérent avec vos échelles 0,84 et 1,2.

## 1. Chaîne d'appel (vérifié)

| Étape | Fonction (adresse, ligne) | Rôle |
|---|---|---|
| 0 | `FUN_0005d616` (`0x5D616`, l. 9694) | appelle la préparation de la fiche de prise de vue avec un mode 0, 1 ou 2 |
| 1 | `FUN_000cd9a2` (`0xCD9A2`, l. 94762) | enchaîne tout ce qui suit ; en mode 2 il relit au lieu de les recalculer les valeurs mémorisées dans la fiche (`0x5C0`, `0x5F0`, …) (retraitement d'une vue : hypothèse) ; le mode 3 impose `c` = `0x5A`, `e40` = 1 |
| 2 | `FUN_000ce09c` (`0xCE09C`, l. 94983) | lit ISO (`e3C`), drapeau `e38`, mesure de scène `e48` |
| 3 | `FUN_000ce4fa` (`0xCE4FA`, l. 95141) | lit les réglages d'Optimiser l'image (octets `0x4C` à `0x4F` de la fiche) et fixe `e00`, `e08`, netteté, saturation, teinte |
| 4 | `FUN_000cdfbe` (`0xCDFBE`, l. 94941) | lit le mode de balance des blancs (octet `0x56`) et le réglage fin |
| 5 | `FUN_000cf7b0` → `FUN_000d319a` → `FUN_000d31b0` (l. 98064) | classe la scène puis lit `ff4` (valeur de ton de la scène) dans la table `0x37ACD8` |
| 6 | `FUN_000cf7e8` (l. 95499) → `FUN_000d3348` (l. 98169) → `FUN_000d38a6` (l. 98347) | mélange `c` et `ff4` avec ceux de la vue précédente (pondérations `a74`, `a78`) |
| 7 | `FUN_000cf86a` (`0xCF86A`, l. 95553) | `d3bea` (classes) → `d3dea` (cran automatique) → `d3ee6` (numéro de courbe) → `d4108` (balance des blancs) → `d54ec` → **`d57e6` (jeu)** → **`d846a` (teinte)** → `d87fc` (netteté, bruit) → **`dd1ca` (saturation)** → `d93a6` (réécrit tout dans la fiche) |
| 8 | `isp_chargerPuce` (`0x5D716`, l. 9750) | recopie la fiche vers `0x5001xxxx` (matrices, secteurs `E400`-`E460`, courbes, `0x5001EC00`) |

Le numéro de jeu choisi est réécrit en fiche+`0x422` (16 bits) et le numéro de courbe en fiche+`0x424` (`FUN_000d93a6`, l. 102032-102033) ; ils sont aussi envoyés aux registres `0x500A0010` et `0x500A0012` (`FUN_0005ace8`, l. 7799-7800, usage non étudié). Je n'ai trouvé aucune copie de ce numéro dans la MakerNote : il n'est donc probablement pas relisible dans un NEF (hypothèse).

## 2. Question 1 : les variables de l'arbre

### 2.1 Table des variables

| Variable (RAM) | Nom ici | Ce que c'est | Écrite par (ligne) | Statut |
|---|---|---|---|---|
| `_DAT_97be0a14` | jeu | numéro du jeu de matrices, 0 à 293 | `FUN_000d57e6`, l. 99733-101076 | vérifié |
| `_DAT_97be0a18` | `a18` | numéro de courbe : 0-20 intégrée, **23 (`0x17`) = courbe perso** | `FUN_000d3ee6`, l. 98647-98778 | vérifié |
| `FUN_000cad3a(x, 7)` | `K` (« cran ») | **reste de la division** de `a18` par 7 (lu dans la boucle de division : valeur rendue = poids fort, remise à 0 si égale au diviseur ; seul usage cohérent : valeur 0-6) | l. 99719 | vérifié |
| `_DAT_97be3e00` | **`E`** | classe de traitement couleur, 7 valeurs (0, 1, 2, 5, 6 atteignables ; 3 et 4 jamais produites) | `FUN_000ce4fa`, l. 95159-95171, 95232-95275, 95283-95297 | vérifié (code) |
| `_DAT_97be3e38` | `e38` | 1 si `fiche[0xA1] & 0xC0` ≠ 0, sinon 0. Mène à la famille F5 et à la valeur 3 écrite en fiche+`0x5A8` | `FUN_000ce09c`, l. 95005-95011 ; l. 95308-95313 | vérifié (code) ; « flash déclenché » : **hypothèse** |
| `_DAT_97be1c3c` | `c` | indice 0-255 de la **teinte de l'éclairage** : bas = froid/bleu, haut = chaud/orangé (ensoleillé 84, ombre 21-52, incandescent 172-221) ; utilisé aussi pour indexer la table de gains `0x381AA8` par `255 − c` (l. 99049) | auto : `FUN_000d2ce2` (l. 97801), lissé par `FUN_000d38a6` (l. 98357) ; manuel : `FUN_000d83ec` (l. 101615), `FUN_000dd848` (l. 103300), `0x5A` pour PRE (l. 99723) | vérifié (origine et échelle) |
| `_DAT_00040e38` | `e40` | **classe d'illuminant 1 à 4** : en balance auto, indice du plus grand de quatre cumuls (`FUN_000d17cc`, l. 96960-97068, règles d'égalité incluses) ; en réglage manuel, lu dans une table (presque toujours 1) | `FUN_000d17cc` l. 97017-97068 ; `FUN_000d38a6` l. 98380 ; `FUN_000d83ec` l. 101616 ; `FUN_000dd848` l. 103301 | vérifié (origine) ; ce que sont les 4 classes : **hypothèse** (jour / ombre / fluo / autre) |
| `_DAT_97be3df4` | `df4` | mode de balance des blancs = `fiche[0x56] & 0x1F` : 0 auto, 1 incandescent, 2 fluo, 3 ensoleillé, 4 flash, 5 nuageux, 6 ombre, 7 K, 8 PRE | `FUN_000cdfbe`, l. 94948 | vérifié pour le codage 0 à 8 de l'octet ; l'attribution des noms aux numéros 1 à 6 est déduite de la table `0x3B36E0` (ombre 21-52 < nuageux 52-76 < ensoleillé 72-96 < incandescent 172-221) : hypothèse forte |
| `_DAT_97be3df0` | `df0` | réglage fin de la balance des blancs (quartet signé) | `FUN_000cdfbe`, l. 94949-94978 | vérifié |
| `_DAT_97be3dec` | `dec` | index de température K (octet `0x5B`) | `FUN_000cdfbe`, l. 94970 | vérifié |
| `_DAT_97be3e08` | `e08` | **Correction des tons** : 0 Auto, 1 Normale, 2 Moins contrasté, 3 Plus contrasté, ≥ 4 Personnalisée (`= (fiche[0x4C] & 0x1F) >> 2`) | `FUN_000ce4fa`, l. 95152, 95231-95274 | vérifié (code) ; concorde avec `0xD02B` de votre note PTP |
| `_DAT_97be3dd4` | `dd4` | **Netteté** (`fiche[0x4C] >> 5`), 0 Auto à 6 Aucune | l. 95226 | vérifié (code) ; correspondance menu : voir §2.3 |
| `_DAT_97be3df8` | `df8` | **Saturation** (`fiche[0x4C] & 3`) : 0 Auto, 1 Normale, 2 Modérée, 3 Accentuée | l. 95174 | vérifié par les valeurs de la table (§4) |
| `_DAT_97be3de8` | `de8` | **Teinte + 3** (`fiche[0x4F]` signé + 3), 0 à 6 | l. 95179 | vérifié |
| `_DAT_97be3dfc` | `dfc` | bit 7 de `fiche[0x4D]` | l. 95154 | lecture vérifiée ; sens « espace couleur Adobe RGB » : **hypothèse forte** (§2.4) |
| `_DAT_97be3e3c` | `e3C` | **sensibilité** en APEX × 12 : `0x3C` = ISO 100, `0x48` = 200, … `0x78` = 3200 (Hi-1) | `FUN_000ce09c` | vérifié par les bornes des classes (pas de 12 de `0x3C` à `0x78`) ; unité exacte : hypothèse |
| `_DAT_97be3e48` | `e48` | mesure de scène : moyenne pondérée de 5 octets signés de la fiche (`0x105` ×5, `0x106` ×2, `0x107` ×2, `0x108` ×3, `0x109` ×3) ÷ 15 + `0x80` | `FUN_000ce09c`, l. 94997-95002 | formule vérifiée ; signification (luminosité de 5 zones ?) : **hypothèse** |
| `_DAT_97be3e04` | `e04` | octet signé fiche+`0x90` | l. 95153 | lecture vérifiée ; nature non déterminée |
| `_DAT_97be0ff4` | `ff4` | « valeur de ton » de la scène 0-6, lue dans la table `0x37ACD8` (clé : `0xFF8×0x80 + 0x1004×8 + 0x100C + 0xFFC×0x20`) ; forcée à 0, 3 ou 6 si la correction des tons n'est pas Auto | `FUN_000d31b0` (l. 98071), lissage l. 98359-98362 ; forçage `FUN_000d3bea` | vérifié |
| `_DAT_97be3dcc` | `dcc` | bit 4 de `DAT_9798D753` | `FUN_000ce4fa`, l. 95177 | lecture vérifiée ; **aucun écrivain du bit 4 trouvé** (seuls les bits 6 et 7 sont écrits, l. 55797-55806) : hypothèse « toujours 0 », la branche matrices en dur (l. 101278-101580) serait morte |
| `_DAT_97be3dbc`, `_DAT_97be3db8` | N&B, variante | 1 pour « Noir et blanc » ; variante N&B/sépia/cyano (`fiche[0x4E] >> 6`) | l. 95228-95279 | vérifié |

### 2.2 Numéro de courbe et cran (vérifié, `FUN_000d3ee6`, l. 98636-98782)

`a18 = 7 × a28 + cran` où `a28` = groupe (0 mode I, 1 mode II, 2 mode III, tiré de `E` : 0→0, 1→1, 2→2, 3→0, 4→2, 5→0, 6→2, l. 98574-98593) et `cran` dépend de `e08` :

| `e08` | cran |
|---|---|
| 0 (Auto) | `a1C`, lu dans la table automatique `0x37BCD8` (voir plus bas) |
| 1 (Normale) | 3 |
| 2 (Moins contrasté) | 0 |
| 3 (Plus contrasté) | 6 |
| ≥ 4 (Personnalisée) | `a18 = 23` (courbe perso), donc `K = 23 mod 7 = 2` pour le jeu |

Portrait (Optimiser = 4) limite ensuite `a18` : cran ≤ 4 pour les groupes I et III, 7 à 11 pour le groupe II (l. 98755-98782).

**Cran automatique** (`FUN_000d3dea`, `0xD3DEA`, l. 98599 ; table `0x37BCD8`, 5 880 mots, fin exactement à `0x3818B8` où commence la table suivante) : clé = `e38×2940 + a2C×3 + a28 + a38×12 + a34×84 + a30×588`, cran = bits 3-5 du mot. Variables de clé : `a28` groupe de courbes, `a2C` classe 0-3 de `e04`, `a38` valeur de ton `ff4` (0-6), `a34` classe 0-6 de `e48` (seuils `0x80, 0x8C, 0x98, 0xAA, 0xB6, 0xC2`), `a30` classe d'ISO 0-4 (seuils `0x3C, 0x48, 0x54, 0x60, 0x6D`). Dans les données, le cran suit `a38` à un cran près (moyenne 0,4 / 1,2 / 1,9 / 2,9 / 3,9 / 4,9 / 5,5 pour `a38` = 0…6) : **c'est la source de « courbe 2 puis 1 » pour Normal et Portrait** dans votre note.

### 2.3 Du menu d'Optimiser l'image aux variables (vérifié, `FUN_000ce4fa`, l. 95226-95297)

| Optimiser (PTP `0xD140`) | tons `e08` | netteté `dd4` | saturation `df8` | teinte | `E` (sRGB / Adobe) |
|---|---|---|---|---|---|
| 0 Normal | 0 Auto | 0 Auto | 0 Auto | forcée 0 | 0 / 5 |
| 1 Moins net | 2 Moins contrasté | 2 Faible | 0 Auto | forcée 0 | 0 / 5 |
| 2 Saturé | 1 Normale | 4 Moyenne + | 3 Accentuée | forcée 0 | 2 / 6 |
| 3 Très saturé | 3 Plus contrasté | 5 Élevée | 3 Accentuée | forcée 0 | 2 / 6 |
| 4 Portrait | 0 Auto (cran ≤ 4) | 3 Moyenne − | 0 Auto | forcée 0 | 0 / 5 |
| 5 Personnalisé | de la fiche | de la fiche | de la fiche | de la fiche | selon mode couleur : voir §2.4 |
| 6 N&B | 1 | 1 | 1 | forcée 0 | matrices en dur (§2.7) |

La numérotation de la netteté (0 Auto, 1 Normale, 2 Faible, 3 Moyenne −, 4 Moyenne +, 5 Élevée, 6 Aucune) est celle de votre note PTP : les valeurs que le code donne aux préréglages (Moins net = 2, Portrait = 3, Saturé = 4, Très saturé = 5) y tombent juste, ce qui la confirme (hypothèse forte).

### 2.4 Calcul de `E` (vérifié pour le code, hypothèse pour le sens du bit 7)

Pour « Personnalisé » : `dfc` = bit 7 de `fiche[0x4D]`, `m` = bits 5-6 (0 mode I, 1 mode II, 2 mode III ; réécrits depuis `a28` par la table `0x3BC11C = (0, 1, 2)`, l. 102174).

| `dfc` | m = 0 (I) | m = 1 (II) | m = 2 (III) |
|---|---|---|---|
| 0 | `E` = 0 | `E` = 2 (cas dégénéré, refusé par le PTP) | `E` = 2 |
| 1 | `E` = 5 | `E` = 1 | `E` = 6 |

Pour les préréglages, `E` vaut d'abord 0 ou 2 (tableau §2.3), puis `dfc` = 1 le transforme en 5 ou 6 (l. 95281-95297).

**Pourquoi je pense que `dfc` = espace couleur Adobe RGB.** J'ai calculé M(E=5) · M(E=0)⁻¹ et M(E=6) · M(E=2)⁻¹ sur les matrices caméra de la table : on retrouve la matrice sRGB → Adobe RGB linéaire (0,715 0,285 0 / 0 1 0 / 0 0,041 0,959) à 0,03-0,09 près, lignes de somme 1. Les jeux E = 5 et 6 sont donc des versions « Adobe RGB » des modes I et III, et le mode II (E = 1) n'existe qu'avec `dfc` = 1, ce qui rejoint le refus PTP du mode II en sRGB. Vos ajustements vont dans le même sens : mode II ajusté sur 66 et 52 (plage E = 1), mode III sur 93 et 94 (plage E = 2, donc `dfc` = 0), référence mode I sur 8 et 9 (plage E = 0).

### 2.5 L'arbre résumé : conditions → numéro de jeu (vérifié)

**`jeu = 42 × E + 7 × F + (6 − K)`**, avec K = `a18 mod 7`.

Famille F (ordre de test de l'arbre, mêmes seuils que le code : `c < 0x9D` et `c > 0x33`) :

| Condition | F | Lecture |
|---|---|---|
| `e38` ≠ 0 | **5** | « flash » (hypothèse) |
| `e38` = 0, `e40` ∈ {1, 4}, `c` ≥ 157 | 0 | éclairage chaud (incandescent) |
| `e38` = 0, `e40` ∈ {1, 4}, 52 ≤ `c` ≤ 156 | **1** | éclairage moyen (ensoleillé, nuageux, flash manuel, jour auto) |
| `e38` = 0, `e40` ∈ {1, 4}, `c` ≤ 51 | 2 | éclairage froid (ombre) |
| `e38` = 0, `e40` = 2, `c` ≤ 156 | 3 | classe d'illuminant 2 (fluorescent en réglage manuel : 6 des 7 types) |
| `e38` = 0, `e40` ∉ {1, 2, 4} (en pratique 3), `c` ≤ 156 | 4 | classe d'illuminant 3 (un seul type de fluo en manuel) |
| `e38` = 0, `e40` ∈ {2, 3}, `c` ≥ 157 | 0 | (le chaud l'emporte) |

Numéro de base `42 × E + 7 × F` ; on ajoute `6 − K` (K = 6 donne la base, K = 0 donne base + 6) :

| E | F0 | F1 | F2 | F3 | F4 | F5 |
|---|---|---|---|---|---|---|
| 0 (I sRGB) | 0 | 7 | 14 | 21 | 28 | 35 |
| 1 (II Adobe) | 42 | 49 | 56 | 63 | 70 | 77 |
| 2 (III sRGB) | 84 | 91 | 98 | 105 | 112 | 119 |
| 3, 4 | jamais atteints : jeux 126 à 209, vides dans la table | | | | | |
| 5 (I Adobe) | 210 | 217 | 224 | 231 | 238 | 245 |
| 6 (III Adobe) | 252 | 259 | 266 | 273 | 280 | 287 |

L'arbre contient des branches pour les 294 jeux (0 à 293 sans trou), mais celles de E = 3 et 4 (84 jeux) ne sont jamais activées : aucun chemin de `FUN_000ce4fa` ne produit ces valeurs.

### 2.6 D'où viennent `c` et `e40` selon la balance des blancs (vérifié)

Au début de `FUN_000d57e6` (l. 99717-99732), si le mode n'est pas Auto, `c` et `e40` sont **remplacés** par des valeurs de tables, puis restaurés à la sortie (l. 101581-101582). Le jeu ne dépend donc pas de ce que la balance des blancs calcule vraiment en mode manuel.

| Mode | `c` | `e40` |
|---|---|---|
| Auto (0) | calculé sur la scène (`FUN_000d4160`, `d2ce2`), lissé avec la vue précédente | argmax de 4 cumuls |
| 1 à 6 (manuel) | `0x3B36E0[7×ligne + réglage fin]` | `0x3B370A[…]` |
| 7 (K) | 84 (table `0x39B07D` : 31 fois 84) | 1 |
| 8 (PRE) | `0x5A` = 90 | 1 |

Lignes de `0x3B36E0` (ligne = f(`df4`) : 6→0, 5→1, 3→2, 1→3, 2→4, 4→5 ; colonnes = réglage fin −3 à +3, lecture centrée sur le milieu de la ligne) :

| Mode | `c` pour −3 … +3 | `e40` |
|---|---|---|
| Ombre | 21, 24, 27, 32, 38, 45, 52 | 1 |
| Nuageux | 52, 56, 60, 64, 68, 72, 76 | 1 |
| **Ensoleillé** | **72, 76, 81, 84, 90, 93, 96** | **1** |
| Incandescent | 172, 179, 184, 192, 201, 210, 221 | 1 |
| Fluorescent (7 types de lampe) | 43, 54, 90, 119, 144, 192, 221 | 2, 2, 2, **3**, 2, 2, 2 |
| Flash | 46, 50, 54, 58, 62, 66, 70 | 1 |

Statut : valeurs vérifiées dans les octets ; la lecture centrée (réglage fin signé) est une hypothèse (le pseudo-C montre `& 0xF` pour les quartets bas), sans effet à réglage fin 0 : dans les deux lectures on tombe sur 84 pour Ensoleillé.

**Conséquence pour votre séance (Ensoleillé, réglage fin 0, sans flash)** : `c` = 84, `e40` = 1, donc **F = 1 pour toutes les photos**. Pour chaque réglage du menu, le jeu attendu est donc `42 × E + 7 + 6 − K`, sans dépendance à la scène sauf par K quand la correction des tons est Auto.

### 2.7 Structure interne de la table de 294 jeux (vérifié, calculé sur les octets)

| Contenu d'un jeu | Dépend de | Remarque |
|---|---|---|
| matrice caméra 3×3 (9 mots) | `E` et `F` seulement | identique pour les 7 crans ; F5 = F1 pour toutes les valeurs de `E` (même matrice) |
| matrice YCbCr (9 mots) | `E` et K seulement | identique pour les 6 familles ; ligne Y toujours (0,297 0,590 0,113) |
| 6 derniers mots (« autres ») | K (et `E`, `F`) | une valeur par classe d'ISO 100, 200, 400, 800, 1600, 3200 ; interpolés par `FUN_000dd27e` (l. 102979) vers le registre `0x50010056` ; rôle non établi (hypothèse : réglage de bruit chroma dépendant de l'ISO) |
| 5 blocs de 16 secteurs | `E` (I/III contre II) et `F` | voir §3.4 |

Le **cran** K module la **saturation de la matrice YCbCr** : pour E = 0, F = 1, l'échelle de (Cb, Cr) est 1,170 / 1,092 / 1,057 / 1,000 / 0,968 / 0,918 / 0,852 pour K = 0 à 6 (jeux 13 à 7). C'est la compensation de la saturation que la courbe plus contrastée ajoute ; elle explique que votre mesure trouve (Cb, Cr) « inchangé » entre tons Normale et Plus contrasté (hypothèse sur l'intention, chiffres vérifiés).

Cas particuliers :
- **Noir et blanc** (`dbc` = 1, l. 101133-101276) : matrice caméra, ligne Y, secteurs et table de saturation écrasés en dur après le chargement du jeu. Déjà documenté dans votre §4.
- **`dcc` ≠ 0** (l. 101278-101580) : trois matrices complètes en dur par groupe `a28`. Branche probablement jamais prise (voir `dcc`, §2.1).

### 2.8 Pourquoi « le jeu qui reproduit le mieux change d'une scène à l'autre »

| Cause | Statut | Effet |
|---|---|---|
| Tons = Auto (Normal, Portrait, ou Personnalisé en Auto) : K suit `a1C`, qui dépend de la scène (`ff4`, luminosité `e48`, ISO, `e04`, flash) et est **mélangé avec la vue précédente** (`FUN_000d38a6`, l. 98357-98362) | vérifié | le jeu varie de ±1 à ±3 crans, soit ±15 % sur l'échelle de chroma |
| Balance des blancs Auto : `c` et `e40` calculés sur la scène, lissés avec la vue précédente | vérifié (code) | saute de famille F ; les matrices caméra de deux familles diffèrent de 0,12 à 0,28 sur un élément |
| Saturation Auto (Normal, Moins net, Portrait) : le niveau de gain varie de 0 à 6 avec `e48` | vérifié (§4) | échelle de chroma ×1,0 à ×1,3 selon la scène, **hors jeu** |
| Votre ajustement n'a que les 294 jeux pour absorber un gain de saturation, une rotation de teinte et une courbe : il choisit le voisin au bon gain | hypothèse | explique que « Saturé » (prévu 94) ressorte en 19 et 97 et « Très saturé » (prévu 91) en 15 et 93, jeux de chroma plus forte ; et que « Modérée » ressorte en 7 et « Accentuée » en 12 (prévu 10) : jeux de chroma plus faible, puis plus forte |
| Mélange d'une vue à l'autre (poids `a74`, `a78`) | vérifié (code), nature temporelle : hypothèse | une même scène peut donner un cran différent selon la vue précédente |

À réglages explicites (tons Normale/Moins/Plus, balance Ensoleillé, saturation Normale), le jeu est **constant** : 10, 13, 7 pour E = 0 ; 94, 97, 91 pour E = 2.

Comparaison avec vos ajustements (F = 1, sRGB sauf mode II) :

| Réglage | jeu prévu par le code | jeux ajustés (bibliothèque, pédalier) |
|---|---|---|
| Personnalisé de référence (tons Normale, mode I) | 10 | 8, 9 |
| Moins net ; Personnalisé tons Moins contrasté | 13 | 11, 12 |
| Personnalisé tons Plus contrasté | 7 | 21, 7 |
| Mode couleur II (Adobe) | 52 | 66, 52 |
| Mode couleur III | 94 | 93, 94 |
| Saturé | 94 | 19, 97 |
| Très saturé | 91 | 15, 93 |
| Normal, Portrait (courbes 2, 1) | 11, 12 | 9, 11 |
| Saturation Modérée / Accentuée (courbe 3) | 10 | 72, 7 / 26, 12 |

Les ajustements tombent soit sur la valeur prévue, soit sur un voisin d'une même famille (mêmes matrices, chroma différent) : **les prévisions du code sont cohérentes avec les mesures, les écarts s'expliquent par la saturation et la teinte non modélisées dans l'ajustement**. Hypothèse. Test simple : refaire l'ajustement en le limitant aux 7 jeux de la famille prévue (F = 1) et en laissant libres un gain de chroma (table de saturation) et un angle (table de teinte).

Les lignes « Mode couleur III ; Saturé » de votre note (même rotation +6 à +7°, même échelle 1,09) s'expliquent aussi : mode III et Saturé/Très saturé partagent **les mêmes jeux E = 2**.

## 3. Question 2 : comment la teinte est appliquée

### 3.1 Lecture (vérifié)

`fiche[0x4F]` (octet signé, −3 à +3) → `_DAT_97be3de8` = valeur + 3 (`FUN_000ce4fa`, l. 95179) → écrit en retour en fiche+`0x4F` et `0x45F` (`FUN_000d93a6`, l. 102178-102180). Pour tous les préréglages sauf Personnalisé, la teinte est forcée à 3, c'est-à-dire 0 (l. 95234, 95242, …) : **la teinte n'agit qu'en Personnalisé**. Le lien entre la propriété PTP `0xD02D` (−9 à +9 par pas de 3) et l'octet `0x4F` n'a pas été cherché (il est vraisemblablement valeur ÷ 3).

### 3.2 Application : `FUN_000d846a` (`0xD846A`, l. 101621-101755) (vérifié)

Après le choix du jeu, la fonction recopie la matrice YCbCr vivante (`0x97BE09CC`, 9 entiers) dans `0x97BE09A8`, puis, pour la ligne Cb (`09D8…09E0`) et la ligne Cr (`09E4…09EC`), calcule en virgule flottante logicielle :

```
Cb' = t1 × Cb + t2 × Cr
Cr' = t3 × Cb + t4 × Cr          (ligne Y inchangée, résultat borné à ±0x1FF)
```

où `t1…t4` = `int16` de la table **`0x388318`** divisés par 10 000, à l'indice `((E × 4 + i) × 7 + h) × 2` avec `h` = teinte + 3 (0 à 6). Les valeurs finales sont écrites en fiche+`0x34E` (signe-module, bit 9 = signe) puis chargées par `isp_chargerPuce` dans `0x50010034`…

Table (identique pour les sept valeurs de `E`, vérifié sur les octets ; fin à `0x3884A0`, juste avant la table de courbes `0x3884D8`) :

| Menu | h | t1 = t4 | t2 | t3 | angle α = atan(t2/t1) | (Cb, Cr) tourne de |
|---|---|---|---|---|---|---|
| −9 | 0 | 0,9921 | +0,1253 | −0,1254 | +7,20° | −7,20° |
| −6 | 1 | 0,9969 | +0,0784 | −0,0785 | +4,50° | −4,50° |
| −3 | 2 | 0,9993 | +0,0366 | −0,0367 | +2,10° | −2,10° |
| 0 | 3 | 1,0000 | 0 | 0 | 0 | 0 |
| +3 | 4 | 0,9994 | −0,0332 | +0,0331 | −1,90° | +1,90° |
| +6 | 5 | 0,9980 | −0,0620 | +0,0619 | −3,55° | +3,55° |
| +9 | 6 | 0,9961 | −0,0872 | +0,0871 | −5,00° | +5,00° |

Déterminant 1,000 à 2·10⁻⁴ près : **rotation pure, pas de changement de saturation** (vous trouvez une échelle de 0,96 à 1,01). L'échelle est non linéaire : environ 0,9 degré par degré de menu près de −9, 0,5 près de +9, 0,6 en moyenne.

Concordance avec vos mesures (angle mesuré moins angle de la table, par pas du menu −9 … +9) :
- pédalier : −7,8 / −4,9 / −2,4 / +1,0 / +2,9 / +4,3 contre −7,2 / −4,5 / −2,1 / +1,9 / +3,55 / +5,0 : écarts −0,6, −0,4, −0,3, −0,9, −0,65, −0,7 (constants à ±0,3°) ;
- bibliothèque : −5,3 / −2,7 / −0,5 / +3,7 / +5,3 / +6,4 : écarts +1,9, +1,8, +1,6, +1,8, +1,75, +1,4 (constants à ±0,25°).

La forme (pas inégaux, compression vers +9) est celle de la table ; le décalage constant, différent d'une scène à l'autre, est le reste de votre ajustement (jeu voisin de pente chroma différente). Vérifié (concordance numérique), mécanisme confirmé par le code.

### 3.3 Ce que la teinte ne touche pas (vérifié)

- Pas de choix de jeu : `de8` n'intervient ni dans l'arbre ni dans `FUN_000dd27e`.
- Pas d'écriture vers `0x5001E400`-`E47F` : les secteurs viennent uniquement du jeu (§3.4).
- Elle est appliquée **après** le jeu et ne change donc pas la matrice caméra ni les secteurs.
- Pas de dépendance de la rotation à `E` : les sept copies de la table sont identiques, on peut donc les modifier séparément.

### 3.4 Format des 16 secteurs

Table `0x38B6C0` (offset fichier `0x33B6C0`) : par jeu, **160 octets = 80 `int16` gros-boutistes = 5 blocs de 16**. Fin de table à `0x396E80` (294 × 160). Vérifié.

| Bloc | Offset dans le jeu | Destination RAM → fiche → registre | Valeurs neutres | Contenu observé |
|---|---|---|---|---|
| 0 | `+0x00` | `0x97BE0868` → fiche `0x37A` → **non chargé** par `isp_chargerPuce` | 0 | toujours 0 dans les 294 jeux |
| 1 | `+0x20` | `0x97BE0828` → `0x39A` → **`0x5001E400`** | 256 | 184 à 256 |
| 2 | `+0x40` | `0x97BE07E8` → `0x3BA` → **`0x5001E420`** | 0 | −94 à +3 |
| 3 | `+0x60` | `0x97BE07A8` → `0x3DA` → **`0x5001E440`** | 0 | −96 à +1 |
| 4 | `+0x80` | `0x97BE0768` → `0x3FA` → **`0x5001E460`** | 256 | 170 à 256 |

Écriture en fiche en signe-module sur 10 bits (`valeur négative → |v| | 0x200`, `FUN_000d93a6`, l. 102049-102105). La valeur 256 (0x100) est le neutre des blocs 1 et 4 ; les branches en dur du code (l. 101278-101580) utilisent 255 comme neutre pour ces blocs.

**Vérifié en octobre 2026 par trois sondes flashées** (`d200-preglages.md` §7) : la matrice 2×2 ci-dessous est juste, non transposée, à pleine force ; en revanche les secteurs ne sont pas des tranches à partir de +Cb : 16 nœuds tous les 22,5°, interpolés, secteurs 0, 4, 8, 12 sur les axes −Cb, +Cb, −Cr, +Cr (carte dans `d200/outils/d200_etage.py`). Hypothèse d'origine : pour chaque secteur s (0 à 15), les quatre mots forment une matrice 2×2 appliquée à (Cb, Cr) : `[bloc1 bloc2 ; bloc3 bloc4] / 256`, neutre = identité. Les valeurs non neutres ont bien cette allure (diagonale 170-256, termes croisés −96 à 3), mais le branchement exact est dans la puce. Si les 16 secteurs sont des tranches de 22,5° du plan (Cb, Cr) à partir de +Cb (hypothèse aussi), les secteurs corrigés (4 à 7 et 10-11 pour le mode I) couvrent les rouges-oranges-jaunes (Cr > 0, Cb < 0) et les verts (Cr < 0, Cb < 0).

Ensembles de secteurs réellement distincts : **6 seulement** sur 294 jeux, constants sur les 7 crans :

| Ensemble | Jeux concernés (E, F) | Secteurs non neutres |
|---|---|---|
| mode I, F0 | (0, 0), (5, 0) | 10, 11 (bloc1 184, 214 ; bloc2 −57, −19 ; bloc3 −15, −6 ; bloc4 250, 244) |
| **mode I, F1** | (0, 1), (5, 1) | 4 à 7, 10, 11 (par ex. secteur 5 : 245, −94, −14, 237) |
| mode I, F2 | (0, 2), (5, 2) | 10, 11 |
| mode III, F0 | (2, 0), (6, 0) | 10, 11 |
| **mode III, F1** | (2, 1), (6, 1) | 5 à 7 (par ex. secteur 6 : 230, −54, −45, 221) |
| neutre | tout le reste (mode II, F3, F4, F5, mode III F2…) | aucun |

Pour votre séance (Ensoleillé) : mode I et III ont leurs secteurs F1, le mode II n'en a pas, et rien ne dépend de la teinte.

## 4. Question 3 : la saturation

### 4.1 Chemin (vérifié)

`df8` (`fiche[0x4C] & 3`) → `FUN_000dd1ca` (`0xDD1CA`, l. 102934) → `FUN_000dd084` (`0xDD084`, l. 102848) → copie d'**une colonne** de la table `DAT_003A62DD` (1 024 lignes × 48 colonnes, stride `0x30`) vers `0x97BE7F18` (`FUN_000dcff8` rend cette adresse) → `isp_chargerPuce` la recopie en 1 024 mots vers **`0x5001EC00`** (l. 9838-9839). La table finit à `0x3B22DD`, début de la courbe N&B (`0x3B22DD`) : cohérent avec vos symboles.

Choix de la colonne :

| `df8` | Menu | Colonne = 8 × (classe d'ISO) + niveau | Lecture du niveau |
|---|---|---|---|
| 0 | Auto | niveau lu dans `0x3A5CCB[e48 × 6 + classe d'ISO]` (256 × 6 octets) | niveau 0 si `e48` < `0xAB`, puis 1 (`0xAB`), 2 (`0xB3`), 3 (`0xBA`), 4 (`0xC2`), 5 (`0xCA`), 6 dès `0xD7` |
| 1 | Normale | niveau 0 | |
| 2 | Modérée | niveau **7** | |
| 3 | Accentuée | niveau **6** | |

Sélection en `0x3A62CB` : lignes `df8 − 1` = (0, 8, 16, 24, 40, 40), (7, 15, 23, 31, 47, 47), (6, 14, 22, 30, 46, 46) pour les six classes d'ISO (100, 200, 400, 800, 1600, 3200). Les colonnes 32 à 39 ne sont jamais choisies. Entre deux classes d'ISO (écart `e3C − 0x3C − 12 × classe`, en douzièmes d'IL), `FUN_000dd084` (l. 102856-102929) prend la colonne de la classe supérieure pour un écart de 6, 8 ou 10, et celle de la classe inférieure dans tous les autres cas (0 à 5, impairs compris).

### 4.2 Contenu (vérifié ; lecture « gain ×128 » : hypothèse)

Gain en fonction de l'indice de ligne (0 à 1023, que je lis comme l'amplitude de chroma, hypothèse), ISO 100, 128 = ×1 :

| Ligne | 8 | 32 | 64 | 128 | 256 | 512 | 768 | 1023 |
|---|---|---|---|---|---|---|---|---|
| niveau 0 (Normale) | 80 | 115 | 128 | 128 | 128 | 118 | 98 | 89 |
| niveau 6 (Accentuée) | 80 | 117 | 157 | 166 | 137 | 124 | 100 | 89 |
| niveau 7 (Modérée) | 80 | 108 | 108 | 108 | 108 | 103 | 94 | 89 |

Le niveau 7 est un **plateau à 108/128 = 0,84** (vos 0,82 à 0,84) ; le niveau 6 monte à 1,23-1,30 pour les chromas faibles à moyens puis revient vers 1 (vos 1,16 à 1,21 en moyenne). Les niveaux 1 à 5 sont intermédiaires entre 0 et 6 ; ils ne sont atteints que par le mode Auto. À ISO élevé, le début de courbe est plus bas (43 contre 80 à la ligne 8, ISO 1600) : réduction de la chroma des tons quasi neutres.

### 4.3 Ce qui reste hors du chemin de saturation

- **Le jeu** : sa matrice YCbCr porte une échelle de chroma qui dépend de K et de `E` (§2.7), pas du réglage de saturation.
- **Le mode couleur** : III est plus saturé que I parce que ses jeux le sont, indépendamment de `df8`.
- Préréglages : Saturé et Très saturé forcent `df8` = 3 ; Normal, Moins net, Portrait forcent `df8` = 0 (Auto, donc dépendant de la scène par `e48`) ; N&B force 1 puis écrase la table par `0x3B32DD` (l. 102967-102972).

## 5. Question 4 : ressources utilisées par une seule entrée d'Optimiser l'image

Méthode : j'ai simulé `FUN_000ce4fa` + `FUN_000d3ee6` (cran Auto compris, toutes les valeurs de cran de la table) pour les 7 préréglages et pour Personnalisé (4 réglages de tons × 3 modes couleur, `dfc` = 0 ou 1), puis noté qui atteint quoi (`reach.py`). Statut : vérifié (sur le code lu).

| Ressource | Atteinte par | Remplaçable seule ? |
|---|---|---|
| **N&B** : matrice et ligne Y en dur (`0xD7840`-`0xD78A6`), courbe `0x3B22DD`, table de saturation `0x3B32DD`, secteurs forcés | N&B uniquement | **oui** (déjà exploité dans votre §5) |
| **Jeux E = 1 (42 à 83)** et **courbes 7 à 13** (groupe II) | **Personnalisé + mode couleur II** uniquement (les préréglages ne produisent jamais E = 1 ni le groupe II) | **oui**, mais le mode II suppose `dfc` = 1 (Adobe RGB, hypothèse) : le JPEG sort alors en Adobe RGB |
| Table de rotation de teinte `0x388318` | Personnalisé uniquement (préréglages : teinte forcée 0) | **oui**, et par valeur de `E` séparément |
| Colonnes de saturation de niveau 7 (7, 15, 23, 31, 47) | Personnalisé + Modérée uniquement | oui |
| Colonnes de niveau 1 à 5 | mode Auto de la saturation (Normal, Moins net, Portrait, Personnalisé en Auto) | non, partagé entre ces entrées |
| Colonnes de niveau 0 | Personnalisé + Normale, et le mode Auto quand `e48` < `0xAB` | non |
| Colonnes de niveau 6 | Saturé, Très saturé, Personnalisé + Accentuée | non |
| Courbes 14 à 20 / jeux E = 2 | Saturé (courbe 17, cran 3), Très saturé (courbe 20, cran 6) **et** Personnalisé mode III (tous crans) | non : un préréglage n'est qu'un cas particulier de Personnalisé |
| Courbes 0 à 6 / jeux E = 0 | Normal (crans 0 à 6 en Auto), Moins net (cran 0), Portrait (crans 0 à 4), Personnalisé mode I | non ; seuls les crans 5 et 6 échappent à Moins net et Portrait |
| Jeux E = 5 et 6 | les mêmes entrées qu'E = 0 et 2, avec l'espace Adobe | réservés à l'espace Adobe, pas à une entrée |
| Courbe 23 (perso) et K = 2 | Personnalisé + tons « Personnalisée » | oui pour la courbe ; le jeu (cran 2) est partagé avec les crans 2 automatiques |
| Jeux E = 3 et 4 (126 à 209) | **aucune entrée** (jamais produits) | libres mais inutilisables sans changer le code |
| Familles F0, F2, F3, F4 (toutes valeurs de E) | seulement par balance Incandescent/Ombre/Fluorescent/Flash (cas bas) ou Auto | indépendantes de l'Optimiser, mais atteignables par la balance Auto |

Conclusion : **aucun jeu ni aucune courbe n'est propre à un seul préréglage** (hors N&B). Normal, Moins net et Portrait partagent les jeux E = 0 et diffèrent par le cran et la netteté ; Saturé, Très saturé et le mode III partagent les jeux E = 2. Les ressources sans collision sont celles de **Personnalisé + mode II** (jeux 42 à 83, courbes 7 à 13), la table de teinte, et les colonnes de saturation de niveau 7.

## 6. Autres constats utiles

- Les trois autres tables à 256 entrées chargées en `0x5001E600`, `E800`, `EA00` (`FUN_000dcfe0`, `dcfb0`, `dcfc8` ; `0x3A22CB`, `0x3A1557`, `0x3A0B57`, 10 jeux chacune) sont choisies par l'ISO (fiche+`0x425`, `0x427`, `0x426` ; `FUN_000d54ec` et `FUN_000d87fc`) : rien à voir avec l'Optimiser, mais elles influencent le rendu à ISO élevé.
- La netteté et le bruit (`FUN_000d87fc`, `0xD87FC`) passent par `0x38AED8` (10 mots par jeu de paramètres), `0x38B3D8` et `0x384818`/`0x384058`/`0x383C78` (selon les bits 5-6 de l'octet `0x56` (réglage non identifié, réduction du bruit : hypothèse)). Hors questions, non détaillé.
- Les offsets fichier utiles : jeux `0x334BF8` (+ 48 × n), rotation de teinte `0x338318`, secteurs `0x33B6C0` (+ 160 × n), table de cran automatique `0x32BCD8`, valeur de ton de scène `0x32ACD8`, balance manuelle `0x3636E0` et `0x36370A`, colonnes de saturation `0x3562DD` (+ colonne ; stride 48), sélecteurs `0x355CCB` et `0x3562CB`, courbes `0x3384D8` (+ `0x200` × n).

## 7. Ce qui reste incertain (à ne pas écrire comme un fait)

| Point | Pourquoi | Comment le lever |
|---|---|---|
| Sens exact de `e38` (flash ?) | octet `fiche[0xA1]` bits 6-7 non tracé jusqu'à une source | chercher l'écrivain de l'octet de statut de flash dans la fiche, ou une prise avec flash et lecture de la famille F5 |
| Signification des quatre classes `e40` et de `e48`, `e04` | la mesure de scène vient de `FUN_000ceb7c`/`FUN_000cfc38` (non lus en détail) | lire ces deux fonctions |
| Lecture signée du réglage fin de la balance des blancs | `& 0xF` dans le pseudo-C pour les quartets bas | lire l'assemblage de `FUN_000cdfbe` ; sans effet à réglage fin 0 |
| `dfc` = Adobe RGB | déduit des matrices (M5 ≈ A · M0) et du refus PTP du mode II | tracer l'écrivain de l'octet fiche+`0x4D` bit 7 côté interface/PTP |
| Rôle des 6 derniers mots d'un jeu (par ISO) | seul `FUN_000dd27e` les lit, la puce ne se lit pas | comparer deux ISO à jeu fixe |
| Format exact des 16 secteurs (matrice 2×2, angle de chaque secteur) | le calcul est dans la puce | mesurer un patch coloré avec un jeu à secteurs non neutres et le même sans |
| Branche `dcc` ≠ 0 | pas d'écrivain du bit 4 trouvé, mais l'écriture par pointeur n'est pas excluable | chercher les écritures par structure sur `DAT_9798D750`+3 |
| Lissage avec la vue précédente (`a74`, `a78`) | nature temporelle déduite de `FUN_000d3348` (commence par comparer deux horodatages, `0xA98` et `0xB5C`) | lire `FUN_000d3348` en entier ; à tester par deux prises rapprochées en tons Auto |
