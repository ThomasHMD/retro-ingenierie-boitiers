# D750 : ce que font vraiment les Picture Control, et les neuf profils qui en découlent

Analyse des séances de calibration d’octobre 2026 (cinq lots, 179 vues NEF + JPEG). Firmware C 1.15. Rien n'a été écrit dans le boîtier pour cette analyse.

Légende : **vérifié** = mesuré sur les paires NEF + JPEG de Thomas (chiffre et lot donnés) ; **calcul** = résultat d'un modèle ajusté sur ces mesures, appliqué à une situation non photographiée ; **hypothèse** = déduction à confirmer.

Repères pour lire les écarts (ΔE2000, comme dans [d750-leviers-reglages.md](d750-leviers-reglages.md)) : sous 1, invisible ; 2 à 3, visible seulement côte à côte ; au-delà de 5, saute aux yeux. On donne toujours la médiane et le 90e centile (p90). Critère de réussite fixé plus tôt : médiane sous 2 et p90 sous 4.

## En bref

| Question | Réponse | Statut |
|---|---|---|
| Comment le boîtier fait-il un JPEG ? | Matrice 3 × 3, puis **la même courbe sur R, V et B**, puis un étage de chroma (gain et rotation selon la teinte) dans le plan CbCr. Ce modèle redonne le JPEG à 0,7 à 1,3 de ΔE médian selon la base et la scène | vérifié (lots 1, 3, 4 ; contrôle sur le lot 2) |
| Une courbe identité redonne-t-elle la base ? | **Oui**, exactement, sur les quatre bases testées et dans tous les lots. Le premier constat (« plus chaude et plus contrastée ») venait d'un changement de lumière entre les deux vues du lot 1 (+20 % de rouge et +10 % de vert au capteur, ISO auto passé de 1 800 à 1 250) | vérifié |
| Où s'applique la courbe perso ? | **Après** toute la base (matrice, courbe de tonalité, étage de chroma), sur la **luma Y'** du JPEG (BT.601), Cb et Cr inchangés. Elle ne change que la clarté, jamais la teinte ni la saturation | vérifié (S : 0,74 à 1,5 de ΔE contre 1,3 à 3,9 si on l'applique par canal) |
| Saturation et teinte ? | Gain sur Cb et Cr (×0,60 à −3, ×1,43 à +3 sur Standard ; Portrait deux fois plus doux) et rotation dans le plan CbCr (environ 2° par cran, identique pour toutes les bases) | vérifié |
| Meilleure base pour Classic Chrome ? | **Standard**, saturation −1, teinte −2, avec courbe : 1,3 (p90 2,6) sur les scènes, 0,9 sur la peau. Neutre fait moins bien (1,46). Standard l'emporte sur chacun des quatre lots | calcul sur mesures |
| Les neuf recettes | **Première livraison** dans [`recettes/d750-v1/`](../recettes/d750-v1/) (octobre 2026), après le lot de test : Kodachrome et Portra passent à leur v2 (nouvelles cibles, §3.5 bis et §3.6 bis), les sept autres gardent leurs réglages. Classic Chrome, Tri-X et FP4 atteignent ou frôlent le critère sur les scènes ; Positive, Hasselblad, Kodachrome, Portra et HP5 sont entre 2,2 et 2,8 ; Classic Neg reste à 4,4, pour des raisons qu'un Picture Control ne peut pas corriger | calcul ; le modèle a prédit le boîtier à 0,5 à 1,4 près au lot de test |
| Portra (U2) | v2 : cible « esprit Portra » (le preset Portra tel que Thomas le règle, mesuré sur 22 paires, tiré à 65 % vers ses scans Portra 400). Recette : **Standard, saturation +3, teinte +2**, courbe : 2,8 sur les scènes, 1,7 sur la peau. La v1 visait le preset Portra pur, mal mesuré dans les ombres (§3.6 bis) | calcul sur mesures |
| Balance des blancs U1 / U2 | U1 (Tri-X) : **10 000 K**. U2 (Portra) : **5 600 K** | calcul |
| Passe critique : reste-t-il des points à gagner ? | **Non.** Quarts de cran, courbe plus fine, poids accru des teintes rares, réglage fin vert-magenta : aucun ne gagne plus de 0,1. La seule correction, une colorimétrie plus juste (racine-polynôme), change les chiffres de 0,1 à 0,4 sans changer un seul réglage. Le vert est la limite commune à tous les profils (§7) | calcul |
| Faut-il un 3e lot ? | **Pas de lot de calibration en plus.** Le lot de contrôle des v1 a été fait : le modèle prédit le boîtier à 0,5 à 1,4 de ΔE médian selon la recette | vérifié (lot de test v1) |

---

## 1. Données et méthode

### 1.1 Les cinq lots

| Lot | Scène | Objectif, ouverture | ISO | Corrections d'objectif | Vues | Blocs uniformes (vue 1) |
|---|---|---|---|---|---|---|
| 1 | pièce aux guitares, lumière du jour | 28 mm f/1,8 G à f/1,8 | auto (1 250 à 2 000) | vignetage Normal, distorsion auto | 47 | 17 742 |
| 2 | un visage | 28 mm à f/1,8 | 200 | idem | 24 | 22 405 (dont 278 de peau) |
| 3 | pédalier, objets très colorés | 135 mm manuel (sans puce) à f/4 | 200 | aucune | 47 | 17 947 |
| 4 | bibliothèque, lumière mêlée (jour et LED chaude) | 28 mm à f/5,6 | 200 | vignetage Normal, distorsion auto | 47 | 8 646 |
| 5 | complément sur la bibliothèque | 28 mm à f/5,6 | 200 | idem | 14 | 10 702 |

Tous en WB 5 600 K fixe, D-Lighting actif coupé, sRGB (vérifié dans les NEF : `WB_RBLevels` 2,0195 / 1,2734 sur les 179 vues).

### 1.2 Chaque JPEG face à son propre NEF

Outil : [`outils/d750_blocs.py`](../outils/d750_blocs.py).

1. **Recalage.** Le JPEG est recadré, et redressé quand le contrôle de la distorsion est actif. Sur la vue 1 de chaque lot, des points communs sont repérés entre le NEF (demi-résolution, quadrilles 2 × 2) et le JPEG (SIFT, puis tri RANSAC). On en déduit la correspondance JPEG → NEF : similitude plus distorsion radiale (trois termes).
   - Résidu médian : 0,03 px au lot 3, sans correction ; environ 1 px aux lots 1, 4 et 5. C'est la limite de la demi-résolution, négligeable devant des blocs de 24 px.
   - Le visage du lot 2 offre trop peu de points (26) : la distorsion y est reprise du lot 1, même objectif.
   - Contrôle visuel par damier NEF / JPEG (`d750_blocs.py controle`).
2. **Blocs.** La grille est faite de blocs de 24 × 24 px du JPEG. Pour chaque bloc : moyenne du JPEG, et moyenne du NEF aux mêmes points. Le NEF est pris noir soustrait, en fraction de la pleine échelle, avec la balance des blancs de la vue (vert = 1).
3. **Tri.** On ne garde que les blocs uniformes des deux côtés : écart-type JPEG sous 2,5 codes ou 4 %, écart-type NEF sous 8 %. Les blocs écrêtés sont écartés (NEF au-dessus de 90 % de la pleine échelle, JPEG à 0-2 ou 253-255). Le tri est fait vue par vue, donc un sujet qui bouge ou une lumière qui change ne fausse rien.

### 1.3 Couleurs de la scène et exposition

Pour comparer un rendu à une cible, il faut la couleur réelle de chaque bloc.
- **Matrice capteur → XYZ.** Elle est ajustée sur la mire d'Imaging Resource prise avec un autre D750 (164 plages, [`d750-standard-ir.json`](donnees-films/d750-standard-ir.json)), avec la contrainte qu'un neutre reste neutre. Écart à la mire : 1,6 de ΔE médian, 3,7 au p90. Calcul.
- **Échelle d'exposition.** Elle est fixée par la même mire : le gris de 18 % se trouve à 8,5 % de la pleine échelle du capteur (vert), soit 3,6 IL sous l'écrêtage. C'est le calage du posemètre, celui de la v0.
- **Passe critique (§7.2).** Une racine-polynôme d'ordre 2 remplace ensuite cette matrice pour les cibles : 1,20 au lieu de 1,62 en validation croisée, et surtout moins de biais sur les verts. Les chiffres des §3 et §4 sont ceux de la première passe ; ceux du §5.1 sont recalculés.
- **Contrôle croisé.** La courbe de Standard mesurée ici redonne celle de la mire d'Imaging Resource, prise avec un autre boîtier, avec un écart médian de 2,8 codes (figure 1). Vérifié.

### 1.4 Les cibles

Outil : [`outils/d750_cibles.py`](../outils/d750_cibles.py). Chaque cible transforme la couleur de la scène en image rendue.

| Profil | Cible | Statut |
|---|---|---|
| Classic Chrome, Classic Neg | LUT officielles Fujifilm F-Log2 (`fuji-lut/`) | données officielles |
| Positive (GR III), Hasselblad (X2D) | modèles matrice + courbe mesurés sur paires RAW + JPEG ([`recettes/mesures/`](../recettes/mesures/)) ; ces modèles reproduisent les JPEG d'origine à 1,0 (Positive) et 2,0 (Hasselblad). Le gris de 18 % est rendu à 118/255, convention des recettes V1 du D40 | mesure ; calage du gris : hypothèse |
| Kodachrome | modèle spectral de la fiche Kodak E-55 ([`kodachrome.py`](../outils/kodachrome.py)), calage du posemètre (diapositive dense). Le spectre de chaque couleur est reconstruit depuis son RVB par les spectres de base de Mallett et Yuksel (2019) ; une couleur hors du gamut sRGB est ramenée au bord | modèle (sans effets inter-couches) |
| Tri-X | mélange et courbe du preset Tri-X vérifiés sur ses exports ([`recettes/v1/tri-x.json`](../recettes/v1/tri-x.json)) | mesure |
| HP5 | mélange de la fiche Ilford et tonalité de ses scans HP5 retouchés (centiles de perspectives §3.3), appliquée au rendu de son « TRI-X » actuel | mesure ; correspondance des centiles : hypothèse (le D-Lighting Auto de ses JPEG brouille le départ) |
| FP4 | mélange et courbe de la fiche Ilford (Ilfotec HC) | fiche |
| Portra 400 | Preset Portra (profil Base) : vraie table du profil (lue dans son .xmp, qui reste hors du dépôt) posée sur la base d'Adobe Camera Raw, elle-même ajustée sur 20 paires NEF du D750 + export (§3.6) | mesure |

### 1.5 Les trois jeux d'évaluation

- **Scènes** : 2 500 blocs tirés au hasard dans chacun des lots 3, 4 et 1 (7 500 blocs).
- **Peau** : 278 blocs du visage (lot 2), pris dans la boîte du visage avec une couleur de peau dans le JPEG Standard.
- **Mire** : les 164 plages de la mire d'Imaging Resource, avec leur couleur de référence, pour le rendu cible.

Chaque jeu pèse autant dans les optimisations. La mire contient des couleurs plus saturées que tout ce qu'on photographie d'ordinaire : son p90 est toujours le plus élevé.

---

## 2. Le traitement du boîtier

Outil : [`outils/d750_analyse.py`](../outils/d750_analyse.py) (`modele`), briques dans [`outils/d750_modele.py`](../outils/d750_modele.py).

### 2.1 Les sept bases

Modèle ajusté pour chaque base sur les lots 1, 3 et 4 ; le lot 2 est tenu à part.

```
code JPEG = étage_CbCr( T( V(r) · M · x ) )
```

- x : RVB du capteur, balance des blancs de la vue appliquée ;
- M : matrice 3 × 3, un neutre reste neutre ;
- T : une courbe croissante, la même sur R, V et B ;
- étage_CbCr : gain et rotation de la chroma qui varient avec la teinte (série de Fourier d'ordre 2), comme l'étage à 16 secteurs du D40 ;
- V(r) : correction de vignetage du boîtier, ajustée sur Standard puis fixée pour les autres bases.

| Base | lot 1 | lot 2 (tenu à part) | lot 3 | lot 4 |
|---|---|---|---|---|
| Standard | 0,90 (1,91) | 1,73 (2,54) | 0,73 (1,46) | 1,12 (3,84) |
| Neutre | 0,96 (1,88) | 1,45 (3,13) | 0,81 (1,45) | 1,02 (3,21) |
| Saturé | 1,36 (2,59) | 1,98 (3,22) | 1,24 (2,22) | 1,34 (4,20) |
| Monochrome | 0,97 (1,35) | 1,26 (1,81) | 0,17 (0,35) | 1,21 (3,42) |
| Portrait | 0,89 (1,80) | 1,64 (2,70) | 0,83 (1,37) | 1,10 (3,30) |
| Paysage | 1,15 (2,21) | 1,81 (3,17) | 1,09 (1,81) | 1,33 (4,18) |
| Uniforme | 0,80 (1,94) | 1,18 (2,63) | 0,75 (1,39) | 0,96 (3,35) |

ΔE2000 médian (p90), modèle contre JPEG. Vérifié.

**Même courbe sur les trois canaux, et non sur la luminance.** Sur Standard (lot 3), le modèle « même courbe sur R, V, B » fait 0,74 ; « courbe sur la luminance seule », 1,77 ; avec l'étage de chroma, 0,59 contre 0,92. Vérifié. La v0 n'avait qu'un indice dans ce sens (2,56 contre 2,68 sur la mire d'Imaging Resource).

**Plancher de 0,7 à 1,2 sur les lots pris au 28 mm.** Même en Monochrome, le JPEG porte une légère teinte (a* −0,5, b* +0,5 en médiane) dans les lots 1, 2 et 4, pas au lot 3 (135 mm, sans correction d'objectif). La correction de vignetage du boîtier semble la produire. Elle n'est pas modélisée et pèse environ 0,7 de ΔE ; elle ne change aucune conclusion. Hypothèse sur la cause.

**Courbes de tonalité** (figure 1, code JPEG d'un gris en fonction de l'exposition, gris de 18 % = 0 IL) :

| IL | −5 | −4 | −3 | −2 | −1 | 0 | +1 | +2 | +2,3 |
|---|---|---|---|---|---|---|---|---|---|
| Standard | 5 | 10 | 20 | 40 | 74 | 122 | 175 | 225 | 239 |
| Neutre | 11 | 18 | 31 | 51 | 82 | 121 | 167 | 212 | 224 |
| Saturé | 2 | 3 | 12 | 31 | 67 | 117 | 174 | 221 | 234 |
| Monochrome | 5 | 8 | 16 | 34 | 69 | 123 | 176 | 221 | 228 |
| Portrait | 6 | 14 | 28 | 51 | 82 | 124 | 172 | 218 | 230 |
| Paysage | 1 | 2 | 10 | 30 | 64 | 114 | 171 | 220 | 231 |
| Uniforme | 21 | 31 | 43 | 61 | 85 | 119 | 162 | 210 | 224 |

Vérifié de −5 à +2,3 IL. Au-delà, les blocs uniformes non écrêtés manquent : la montée au blanc n'est pas mesurée.

!Courbes des sept bases

*Figure 1. Courbe de chaque base, modèle ajusté sur les blocs ; cercles : Standard mesuré sur la mire d'Imaging Resource (autre D750).*

### 2.2 Saturation et teinte

Chaque vue « curseur » est comparée à la sortie modélisée de sa base, calculée depuis son propre NEF. L'écart résiduel est la part que l'opérateur n'explique pas.

| Base | Saturation −3 | −1 | +1 | +3 | Teinte −3 | −1 | +1 | +3 |
|---|---|---|---|---|---|---|---|---|
| Standard | ×0,60 | ×0,88 | ×1,15 | ×1,43 | −6,1° | −2,4° | +1,6° | +5,8° |
| Neutre | ×0,60 | ×0,87 | ×1,15 | ×1,46 | −6,2° | −2,4° | +1,6° | +5,8° |
| Saturé | ×0,55 | | | ×1,44 | −6,2° | | | +5,8° |
| Portrait | ×0,82 | | | ×1,23 | −6,0° | | | +6,1° |
| Paysage | ×0,55 | | | ×1,37 | −5,9° | | | +6,1° |
| Uniforme | ×0,60 | | | ×1,53 | −6,1° | | | +6,0° |

Gain sur Cb et Cr, rotation dans le plan CbCr, médiane des lots 1, 3, 4 et 5 (le lot 2 est trop peu coloré pour ces mesures). Les crans ±1 ne sont mesurés que sur Standard et Neutre (lot 5) ; ailleurs, ±1 et ±2 sont interpolés. Vérifié pour les crans mesurés, calcul pour les autres.

- **Où ça agit.** Un gain et une rotation uniques dans le plan CbCr expliquent la vue à 0,5-0,6 près (−3) et à 1,2 près (+3, où les couleurs les plus vives sortent du gamut). Le même opérateur en CIELAB fait moins bien : pour SAT −3, 0,63 et un p90 de 3,3 au lieu de 0,97 (lot 3, contrôle exploratoire). Vérifié.
- **Teinte.** Rotation de toutes les couleurs dans le même sens : en +, les rouges vont vers l'orange et les bleus vers le violet. L'effet n'est pas symétrique autour de 0 (−2,4° à −1, +1,6° à +1).
- **Figure 2.**

!Curseurs

### 2.3 Contraste

Un cran de contraste équivaut à une courbe appliquée à la luma, pas par canal (Standard, lot 3 : 0,91 contre 2,98 à −3 ; 1,00 contre 2,52 à +3). Vérifié. Courbe mesurée, entrée et sortie en codes :

| entrée | 0 | 32 | 64 | 96 | 128 | 160 | 192 | 224 | 256 |
|---|---|---|---|---|---|---|---|---|---|
| Standard −3 | 0 | 51 | 80 | 104 | 126 | 150 | 175 | 206 | 241 |
| Standard +3 | 9 | 21 | 43 | 85 | 129 | 172 | 208 | 236 | 249 |
| Monochrome +3 | 3 | 18 | 46 | 79 | 123 | 168 | 203 | 232 | 255 |

Lot 3. C'est ce qu'ajoute le contraste +3 de ton « TRI-X » actuel (§4.2).

### 2.4 La courbe perso

| Base, lot | Courbe identité : sans courbe | avec | Courbe en S : courbe ignorée | sur R, V, B | **sur la luma** |
|---|---|---|---|---|---|
| Standard, lot 1 | 0,82 | 0,82 | 2,29 | 3,92 | **0,80** |
| Standard, lot 3 | 0,70 | 0,70 | 3,64 | 1,34 | **0,74** |
| Standard, lot 4 | 1,33 | 1,33 | 3,52 | 3,86 | **1,50** |
| Neutre, lot 1 | 0,95 | 0,95 | 1,77 | 3,83 | **0,98** |
| Neutre, lot 3 | 0,81 | 0,81 | 4,18 | 1,68 | **0,85** |
| Neutre, lot 4 | 1,19 | 1,19 | 3,17 | 3,80 | **1,27** |
| Portrait, lot 2 / lot 5 | 1,61 / 1,12 | idem | 2,55 (lot 5) | 3,32 | **1,41** |
| Monochrome, lots 1 / 3 / 4 | 0,97 / 0,17 / 1,20 | idem | 2,23 / 3,70 / 3,98 | = luma | **0,99 / 0,15 / 1,20** |

ΔE2000 médian. La courbe en S est appliquée à la sortie modélisée de la base, qui ne voit jamais la vue avec courbe. Vérifié.

!Courbe perso

*Figure 3. La courbe en S, appliquée là où le boîtier l'applique (luma) ou par canal (hypothèse de la v0).*

Conclusions :
- **Une courbe identité ne change rien**, à 0,01 près, sur Standard, Neutre, Portrait et Monochrome, dans tous les lots. Vérifié. La courbe perso **ne remplace pas** la courbe de la base.
- **Le premier constat de la séance s'explique par la lumière.** Au lot 1, entre BASE STANDARD et STANDARD COURBE ID, le capteur a reçu 20 % de rouge et 10 % de vert de plus (rapport médian des NEF 1,20 / 1,10 / 1,00), et l'ISO auto est passé de 1 800 à 1 250. Le JPEG suit la scène, pas la courbe. Vérifié.
- **Où elle s'applique.** Après la matrice, la courbe de la base et l'étage de chroma, sur la luma Y' du JPEG (BT.601, codes gamma), Cb et Cr inchangés. Une couleur vive garde donc sa chroma quand la courbe l'assombrit : une courbe ne peut ni saturer ni désaturer, ni corriger une teinte. Vérifié.
- **Contraste et luminosité** passent à « géré par la courbe » (lu dans le firmware, `d750-picture-control-usb.md` §4.2).
- **Saturation et teinte avec courbe.** Le modèle les combine avec la courbe sans qu'elles se gênent : la courbe agit sur Y', les curseurs sur Cb et Cr. Hypothèse : aucune vue de la séance n'avait à la fois une courbe et une saturation ou une teinte différente de 0. Le lot de contrôle (§6) le vérifie.

### 2.5 Monochrome et filtres

Mélange de canaux de chaque filtre, mesuré contre le JPEG (lots 4 et 5, même scène) et ramené en sRGB linéaire (somme 1) pour le comparer aux cibles :

| Filtre | R / V / B (sRGB linéaire) | Écart du modèle |
|---|---|---|
| Aucun | 0,23 / 0,41 / 0,36 | 1,20 |
| Jaune | 0,35 / 0,48 / 0,18 | 1,23 |
| Orange | 0,48 / 0,35 / 0,17 | 1,22 |
| Rouge | 0,68 / 0,22 / 0,10 | 1,23 |
| Vert | 0,20 / 0,56 / 0,24 | 1,26 |
| *Cible du preset Tri-X* | *0,28 / 0,52 / 0,19* | |
| *Fiche Ilford HP5+* | *0,10 / 0,24 / 0,67* | |

Vérifié (mesure) ; la conversion en sRGB linéaire passe par la matrice du §1.3 (calcul).

- **« Aucun » n'est pas la luminance Rec.709** (0,21 / 0,72 / 0,07), contrairement à l'hypothèse de perspectives §3.3. Il garde beaucoup plus de bleu. C'est une bonne nouvelle pour les films, tous plus sensibles au bleu que l'œil.
- **Orange.** Le mélange mesuré ici (0,48 / 0,35 / 0,17) diffère de celui des 60 NEF « TRI-X » (0,57 / 0,34 / 0,09) ; le D-Lighting Auto de ces photos et la conversion par une autre matrice expliquent sans doute l'écart. L'ordre des filtres est le même. Hypothèse.
- **Balance des blancs.** En Monochrome, le gris est calculé après la balance des blancs : une WB fixe plus chaude que la lumière retire du bleu au mélange, une WB plus froide en ajoute (§4).

### 2.6 Les hypothèses de la v0, confrontées

| Hypothèse ([`recettes/d750-v0/README.md`](../recettes/d750-v0/README.md)) | Verdict |
|---|---|
| La courbe perso s'applique après la base, sur chaque canal | **Après la base : oui. Sur chaque canal : non**, sur la luma (§2.4). La v0 a été calculée par canal : ses courbes déforment les couleurs vives autrement que prévu |
| Au-dessus du blanc de la mire, la courbe Standard monte jusqu'à 255 à l'écrêtage | non tranché : mesuré jusqu'à 239 à +2,3 IL, au-delà pas de blocs non écrêtés |
| La base Monochrome a la même courbe que Standard | **à peu près** : Monochrome est plus sombre de 2 à 6 codes entre −4 et −2 IL, et de 4 à 11 codes au-dessus de +2 IL (§2.1) |
| Le boîtier utilise la table de 257 valeurs | compatible avec les mesures (la courbe en S prédite depuis la table : 0,74), non tranché : les 20 points d'ancrage de l'entête décrivent la même courbe |

### 2.7 Le modèle complet prédit-il un vrai Picture Control ? Les v0 photographiées

Chaque v0 est simulée (base + curseurs + courbe sur la luma) depuis le NEF de sa vue, puis comparée à son JPEG. C'est un test indépendant : les v0 ne servent pas à l'ajustement.

| Vue | lot 1 | lot 2 | lot 3 | lot 4 |
|---|---|---|---|---|
| CHROME V0 | 1,05 | 1,95 | 0,94 | 1,43 |
| CLASSIC NEG V0 | 1,13 | 1,74 | 0,89 | 1,43 |
| KODACHROME V0 | 1,19 | 1,95 | 1,15 | 2,12 |
| TRI-X DDX V0 | 1,03 | | 0,47 | 1,26 |
| HP5 DDX V0 | 1,07 | | 0,46 | 1,24 |
| FP4 DDX V0 | 1,02 | | 0,44 | 1,23 |

ΔE2000 médian, modèle contre JPEG. Vérifié : le modèle prédit un Picture Control avec courbe à la précision du modèle de la base.

Écart **réel** des v0 à leur cible (JPEG du boîtier contre cible, scène du lot 3) : Chrome 3,1 (p90 6,0), Classic Neg 4,8 (6,5), Kodachrome 7,1 (10,3). Vérifié. C'est le point de départ de la v1.

---

## 3. Meilleure base par profil couleur

Pour chaque profil et chaque base, la saturation, la teinte et une courbe perso à 16 nœuds sont optimisées ensemble contre la cible. Les crans continus sont ensuite arrondis aux deux crans entiers voisins et la courbe est réajustée. Outil : `d750_analyse.py bases`.

!Bases par profil

*Figure 4. ΔE2000 médian de la meilleure recette par base, WB 5 600 K (Portra : §3.6). Pour le Kodachrome, voir §3.5 : avec une WB à 5 000 K, c'est Neutre qui est retenu.*

### 3.1 Classic Chrome (question de Thomas)

| Base | Crans sat. / teinte | Base brute, scènes | Scènes | Peau | Mire |
|---|---|---|---|---|---|
| **Standard** | −1 / −2 | 3,50 | **1,15 (2,71)** | **1,31 (1,60)** | **2,30 (7,18)** |
| Portrait | −1 / −2 | 4,38 | 1,67 (2,94) | 1,69 (2,09) | 2,57 (7,49) |
| Saturé | −1 / −2 | 3,47 | 1,60 (3,15) | 1,44 (2,01) | 2,56 (8,85) |
| Paysage | 0 / −1 | 2,39 | 1,87 (3,96) | 0,67 (0,93) | 2,80 (11,19) |
| Neutre | 0 / −2 | 3,56 | 1,46 (3,39) | 1,80 (2,14) | 2,87 (8,56) |
| Uniforme | +1 / −2 | 3,25 | 1,39 (4,02) | 1,55 (2,61) | 3,26 (8,54) |

Lot par lot, scène seule, médiane (p90) : Standard 1,11 (1,94), 1,35 (3,28), 1,09 (3,25), et 1,46 (3,41) sur le lot 5, qui n'a pas servi à l'optimisation. Neutre : 1,41, 1,71, 1,27, 1,80. **Standard l'emporte partout.**

Réponse : **Standard**, pas Neutre. Neutre part de plus près en tonalité (courbe plus douce), mais une fois saturation, teinte et courbe optimisées, il reste derrière Standard sur les trois jeux et sur chaque lot. La raison tient à ce que la courbe et les curseurs ne peuvent pas changer : la matrice et l'étage de chroma propres à chaque base, qui placent les couleurs de Standard plus près de celles de Classic Chrome (explication probable, non isolée). Calcul sur mesures.

Gain par rapport à la v0 mesurée sur le pédalier : de 3,1 à environ 1,3. Hors d'atteinte : les verts et cyans saturés de la mire (p90 de 7), que Classic Chrome éteint plus que Standard, de façon différente selon la teinte.

### 3.2 Classic Neg

Meilleure base : Standard, saturation 0, teinte 0 : 3,97 (5,95) sur les scènes, 1,88 sur la peau, 4,75 sur la mire. Toutes les bases restent entre 3,5 et 4,5. La LUT de Classic Neg change teinte et saturation différemment selon la couleur et la clarté ; une rotation unique, un gain unique et une courbe sur la luma n'y arrivent pas, quelle que soit la base. Une autre WB n'aide pas (au mieux 3,97 à 5 600 K, 4,05 à 6 250 K). **Hors d'atteinte d'un Picture Control.** Calcul.

### 3.3 Positive (GR III)

Standard, saturation +2, teinte −2 : 2,47 (4,13) sur les scènes, 1,06 sur la peau, 2,58 sur la mire. Base brute : 3,07 (scènes), 6,40 (peau). La saturation continue voulue (×1,26) se place entre les crans +1 et +2. Calcul.

### 3.4 Hasselblad (X2D)

Standard, saturation +1, teinte −3 : 2,43 (3,70) sur les scènes, **0,68** sur la peau, 4,14 sur la mire. La rotation continue voulue (−6,2°) touche la butée de −3 crans : le curseur de teinte est au bout. Neutre et Portrait font un peu mieux sur les scènes (2,14 et 2,18) mais nettement moins bien sur la peau (1,30 et 1,18). Calcul.

### 3.5 Kodachrome

À 5 600 K, toutes les bases demandent saturation −3 et teinte −3, en butée, et restent vers 4,0 à 4,7 sur les scènes. La cible veut des neutres plus froids que la scène : la WB est le levier qui manque.

| Base, WB | 4 500 K | **5 000 K** | 5 300 K | 5 600 K | 6 250 K |
|---|---|---|---|---|---|
| Neutre | 3,08 | **2,41 (4,00) ; peau 0,58 ; mire 2,68** | 3,17 | 4,16 | 6,30 |
| Standard | 2,84 | 2,37 (4,04) ; peau 0,80 ; mire 2,76 | 3,67 | 4,74 | 6,92 |
| Paysage | 3,32 | 2,20 (4,23) ; peau 1,70 ; mire 3,37 | 3,24 | 4,30 | 6,37 |

ΔE2000 médian sur les scènes, sauf mention. Le passage de 5 600 à 5 000 K vaut 21 mired, soit environ **4 crans vers B** du réglage fin (5 mired par cran : hypothèse). C'est ce que la v0 avait prévu (B3 à B5). Calcul ; la conversion kelvins → coefficients est calculée depuis la matrice du §1.3, à vérifier sur les `WB_RBLevels` d'un NEF pris à 5 000 K.

Retenu pour C-1 : **Neutre, saturation −2, teinte −3, à utiliser avec WB 5 000 K** (ou 5 600 K et réglage fin B4). Une variante calculée pour 5 600 K est fournie (Paysage, −3 / −3, 4,30 sur les scènes). Le Picture Control ne mémorise pas la WB : il faudra la régler à la main en passant en Kodachrome.

Réserve sur la cible : le modèle spectral n'a pas d'effets inter-couches. Avec la diapositive au calage du posemètre, l'image est sombre (gris vers 90/255) : c'est voulu, c'est la densité d'une diapositive.

#### 3.5 bis Kodachrome v2 : cible spektrafilm (octobre 2026)

Au lot de test, Thomas trouve la v1 pas assez saturée. Recherche : aucune mesure publique de vraie Kodachrome (le K-14 n'est plus développé). Le passage diapositive projetée → écran (CIECAM02, fond sombre → fond tamisé) réduit la chroma (× 0,94 à 0,96) au lieu de l'augmenter : pas d'argument physique pour saturer davantage. En revanche, la cible v1 avait deux défauts nets face à la simulation de spektrafilm (A. Volpato ; profil `kodak_kodachrome_64`, effets inter-couches compris) :

| Sur la mire | v1 (Mallett, sans inter-couches) | spektrafilm |
|---|---|---|
| Gris de 18 % | L\* 38, b\* −6 (froid) | L\* 49, b\* +2 (légèrement chaud) |
| Chroma des rouges (médiane) | 19 | 45 |

Le manque de saturation perçu venait de là : rouges ternes et image sombre et froide. Nouvelle cible : spektrafilm, table 3D (`outils/d750_spektrafilm.py`, hors dépôt : variable `D750_SPEKTRAFILM`). La WB optimale passe du froid au chaud.

Trois variantes calculées (base Standard, ΔE2000 médian prévu contre chaque cible) :

| Variante | Cible | WB | Saturation, teinte | Scènes | Peau | Mire |
|---|---|---|---|---|---|---|
| **Vif (retenue)** | spektrafilm, chroma × 1,2 (choix de goût) | 6 250 K | −1, −3 | 2,81 | 0,60 | 3,26 |
| Spektrafilm | spektrafilm tel quel | 5 880 K | −2, −2 | 2,12 | 1,45 | 2,70 |
| Dense | spektrafilm, diapositive sous-exposée de ½ IL | 5 880 K | −2, −3 | **1,68** | 0,98 | **2,14** |

Retenue par Thomas sur aperçus : **Vif**. La **Dense** est gardée en réserve : c'est la cible que le boîtier suit le mieux (meilleure des trois sur les trois jeux) ; elle garde les rouges de spektrafilm avec une partie de la densité de la v1, conforme à la pratique de la diapositive (sous-exposer un peu pour saturer). À 6 250 K elle donne 2,04 / 0,53 / 2,21 ; à 5 560 K, 2,41 / 1,93 / 3,15. Une piste non calculée : dense et chroma × 1,2 ensemble.

Pour la recalculer :

```
spkenv/bin/python outils/d750_spektrafilm.py kodak_kodachrome_64 $D750_SPEKTRAFILM/kodak_kodachrome_64_ev-0.5.npz --ev -0.5
python3 outils/d750_analyse.py balance <blocs> <modele.json> <status_A> bal-koda-dense.json 'KODACHROME DENSE:STANDARD' --kelvins 5880
```

Les WB 5 880 et 6 250 K sont des pas de 10 mired (170 et 160 mired) ; que le D750 les propose exactement reste à vérifier sur le boîtier.

---

### 3.6 Portra 400 (le preset Portra)

**La cible.** Le preset Portra est un profil « Look » de Lightroom : une table de couleurs 32 × 32 × 32 en Adobe RGB gamma 2,2, appliquée par-dessus le développement d'Adobe (profil Adobe Standard du D750 et sa courbe). Sur les gris, la table seule donne le caractère attendu : ombres un peu froides, tons moyens presque inchangés, hautes lumières chaudes. Vérifié (lecture du .xmp, `d750_cibles.table_look`).

Les données (session locale, octobre 2026) :
- `portra-cibles.zip` : les trois profils du dossier du preset Portra (Base, Creative, Under) et ses préréglages ; 481 scans Portra 400 et 73 aperçus retouchés ;
- `portra-paires.zip` : **20 NEF du D750** (Picture Control « Portra 400 », visages, de jour), chacun développé dans Camera Raw de Photoshop 2026 avec Adobe Standard, le preset Portra à 100 %, WB « As Shot », l'exposition de ton catalogue, et tout le reste à 0.

**Le modèle de la cible** (`d750_analyse.py cible-paires --look`) :
- la vraie table du preset est appliquée telle quelle ; seule la base d'Adobe est ajustée sur les paires (matrice 3 × 3 et courbe sur les trois canaux), avec un gain d'exposition par photo ;
- reproduction des exports : **0,88 (p90 1,88)**, et **0,86 (2,14) sur les cinq photos tenues à part**. Vérifié ;
- contrôles :
  - les gains retrouvés redonnent les expositions de ton catalogue (−0,10, −0,06, −0,11, +0,80 pour +0,78, +0,77 pour +0,76) ;
  - le premier essai, avec un modèle libre au lieu de la table, ne faisait que 2,45 sur les photos tenues à part et partait en vrille sur les couleurs absentes des paires (magenta presque gris) ;
  - la table est bien celle de « Base » du preset Portra. Ton préréglage « B1 Base » appelle un autre identifiant de profil, introuvable dans le dossier.

Le preset Portra sans aucun réglage est **contrasté** : ombres profondes bouchées (21 % des blocs des exports ont un canal sous 3/255), rouges et bleus plus saturés que la scène, blancs chauds. Ta façon de l'utiliser (ombres relevées, noirs, vibrance) n'est pas dans la cible : c'est le preset Portra lui-même.

**Meilleure base** (WB 5 600 K) :

| Base | Crans sat. / teinte | Scènes | Peau | Mire |
|---|---|---|---|---|
| **Standard** | +2 / +2 | **3,17 (8,31)** | **2,22 (2,76)** | 4,99 (10,19) |
| Neutre | +3 / +2 | 3,33 (9,62) | 2,65 | 4,86 |
| Saturé | +1 / +2 | 3,44 (8,94) | 3,11 | 4,78 |
| Portrait | +3 / +2 | 3,39 (8,49) | 3,91 | 5,09 |
| Paysage | +2 / +3 | 3,47 (8,78) | 3,10 | 5,07 |
| Uniforme | +3 / +2 | 3,30 (10,32) | 3,57 | 5,88 |
| *« Portra 400 » actuel (Portrait, +1 / −1, luminosité +1)* | | *5,95 (13,36)* | *8,21* | *6,90* |

Calcul sur mesures. Standard l'emporte, y compris sur la peau ; ton Portra actuel est deux fois plus loin du preset Portra sur les scènes et quatre fois sur la peau.

**Ce qui reste.** Dans l'écart de 3,2, la clarté est juste (écart de L* médian sous 2 dans chaque tranche de clarté) et la saturation aussi (écart de chroma sous 3). Ce qui manque est la teinte, qui change avec la clarté : ombres vers le bleu-vert, hautes lumières vers le jaune-orangé (écart de 5,6 entre L* 15 et 35 et de 5,9 au-dessus de L* 70, contre 2,3 à 2,7 dans les tons moyens). C'est un virage partiel (split toning), et un Picture Control n'a qu'une rotation de teinte pour toute l'image. **Hors d'atteinte.** Calcul.

**WB pour U2.** Une autre WB ne compense pas ce virage : 5 600 K reste le meilleur compromis (3,17 sur les scènes). À 6 250 K, la peau se rapproche (1,47), mais les scènes s'éloignent (4,69). Pour un mode portrait, c'est un choix possible : 6 250 K si la peau prime, 5 600 K pour tout le reste. Calcul.

**Contrôle avec les scans de l'auteur Portra 400** (`d750_analyse.py scans`, signature seulement, sans scène de référence) :
- 73 scans retouchés : L* médian 60, noirs doux (p5 à 10), blanc jamais pur (p99 à 94) ;
- 481 scans bruts : L* médian 51 ;
- les gris sont légèrement chauds dans toutes les tranches (b* +1 à +4), ombres comprises.

Tes Portra retouchées sont donc plus claires et plus douces que le preset Portra pur, et sans ombres froides. Si c'est ce rendu-là que tu veux au boîtier, la cible devient « preset Portra + tes réglages habituels » : une autre série d'exports, avec tes réglages, suffirait à la calculer.

#### 3.6 bis Portra v2 : « esprit Portra » (octobre 2026)

Demande de Thomas : un équilibre entre ses Portra scannées et le preset Portra tel qu'il le règle, avec plus de poids au film.

**Un défaut de mesure, corrigé.** Les exports du preset Portra ont du grain. Le filtre d'uniformité des blocs (écart-type du JPEG sous 2,5 niveaux) rejetait donc presque tous les blocs sous le gris moyen : 5 blocs gardés sur 20 266 à −2 IL, 658 sur 33 897 au gris. La courbe n'était mesurée que sur les hautes lumières, et devinée en dessous : un saut de L\* 5 à 44 en un diaphragme pour la cible réglée, des noirs bouchés pour le preset Portra pur. Vérifié. Correction : `cible-paires --grain` (seuil porté à 8 niveaux, l'uniformité restant assurée par le critère sur le NEF) et `--lisse 0.3` (pénalité sur les sauts de pente de la courbe). La v1 Portra visait donc une cible faussée dans les ombres : les « noirs bouchés » qu'a vus Thomas en viennent au moins en partie.

**La cible.** Le preset Portra avec les réglages de Thomas, mesuré sur 22 paires NEF + export (`portra-preset-regle.json` : 2,25 en ajustement, 3,59 sur les photos tenues à part ; modèle libre, sans la table du preset). Puis mélange « esprit Portra » ([`portra-esprit.json`](donnees-films/d750-seances/portra-esprit.json), `d750_cibles.melange_film`), poids 0,65 vers le film : clarté ramenée centile par centile des exports (L\* 10,6 / 34,6 / 57,6 / 72,4 / 85,6 / 91,4) vers les scans retouchés (9,8 / 36,2 / 60 / 77,2 / 89,6 / 94,2), et teinte des tons neutres vers celle des scans ; les couleurs saturées gardent celles des exports.

**Meilleure base** (WB 5 600 K), ΔE2000 médian (p90) :

| Base | Crans sat. / teinte | Scènes | Peau | Mire |
|---|---|---|---|---|
| **Standard** | +3 / +2 | **2,79 (5,36)** | **1,66** | 4,16 |
| Neutre | +3 / +1 | 2,59 (5,37) | 4,12 | 4,07 |
| Portrait | +3 / +1 | 2,77 (5,90) | 4,67 | 3,95 |
| Uniforme | +3 / +2 | 3,20 (7,10) | 3,71 | 3,97 |
| Paysage | +3 / +3 | 3,38 (5,88) | 3,00 | 4,71 |
| Saturé | +3 / +2 | 3,51 (6,13) | 2,50 | 4,77 |

Retenu : **Standard, +3, +2**, WB 5 600 K en U2 (PORTRA 400 V2). Calcul sur mesures. La saturation est en butée (+3).

## 4. Noir et blanc

Pour chaque profil : filtre (aucun, jaune, orange, rouge, vert), WB et courbe perso optimisés contre la cible. La WB n'est explorée en grand que pour Tri-X (U1) ; HP5 et FP4 vont dans des emplacements C, sans WB mémorisée.

### 4.1 Tri-X (U1)

| Filtre, WB | Scènes | Peau | Mire |
|---|---|---|---|
| **Aucun, 10 000 K** | **0,44 (1,97)** | 0,55 (1,18) | 1,08 (5,11) |
| Aucun, 8 000 K | 0,53 (2,32) | 0,58 (1,38) | 1,16 (5,56) |
| Aucun, 5 600 K | 0,83 (2,87) | 0,63 (1,55) | 1,43 (5,98) |
| Vert, 10 000 K | 0,48 (2,44) | 0,69 (1,70) | 0,94 (4,15) |
| Jaune, 5 600 K | 0,75 (2,25) | 0,83 (1,11) | 0,85 (5,45) |
| Orange, 5 600 K (ton réglage actuel, avec la courbe v1) | 2,34 (6,58) | 2,53 (3,79) | 2,19 (15,11) |
| Rouge, 5 600 K | 5,23 (12,02) | 3,34 (6,63) | 4,84 (25,68) |

Calcul sur mesures. **Filtre aucun, WB 10 000 K** (le maximum du boîtier) : le critère est tenu. Contre-intuitif mais cohérent avec perspectives §3.3 : « aucun » a trop de bleu pour le preset, et une WB chaude en retire. L'optimum est au bord de la plage : un réglage fin vers A (ambre) pourrait encore aider, non testé. Revers connu : le NEF s'ouvre orangé dans Lightroom tant qu'on ne remet pas la WB.

### 4.2 HP5

Meilleur : **filtre aucun** : 2,36 (7,97) sur les scènes, 0,83 sur la peau, 3,11 sur la mire, à 5 600 K. Le p90 reste haut : la fiche Ilford veut deux tiers de bleu (0,67), le boîtier en donne au mieux 0,36. Ciels et bleus restent trop sombres. Une WB plus froide aiderait : 1,92 (6,00) à 4 000 K. **Hors d'atteinte : la sensibilité au bleu de la HP5.** La tonalité, elle, est calée sur tes scans (gris moyen nettement plus clair que ton TRI-X actuel, blancs jamais purs).

### 4.3 FP4

Meilleur : **filtre aucun** : 2,12 (5,44) sur les scènes, 0,57 sur la peau, 2,90 sur la mire, à 5 600 K ; 1,69 (4,08) à 4 000 K. Même limite que la HP5, en moins marqué. Le premier relevé de tes scans FP4 (bien plus clairs, 20 aperçus seulement) n'est pas utilisé : signal trop faible, et trop lié aux sujets. La courbe suit donc la fiche Ilford.

---

## 5. Les neuf recettes (première livraison)

Fichiers : [`recettes/d750-v1/usb/*.json`](../recettes/d750-v1/usb/), au format de la v0 (`picture_control.py bloc`), avec leur résumé [`resume.json`](../recettes/d750-v1/resume.json) et un [README](../recettes/d750-v1/README.md). Les courbes sont des tables de 257 valeurs (`"lut"`), calculées pour la luma.

### 5.1 Tableau

| C- | Nom | Base | Sat. | Teinte | Filtre | Netteté, clarté | WB conseillée | Scènes | Peau | Mire |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | KODACHROME V2 | Standard | −1 | −3 | | 4, +1 | **6 250 K** | 2,81 (4,85) | 0,60 | 3,26 |
| 2 | CLASSIC CHROME V1 | Standard | −1 | −2 | | 3, 0 | 5 600 K | 1,29 (2,56) | 0,93 | 2,27 |
| 3 | CLASSIC NEG V1 | Standard | 0 | 0 | | 3, 0 | 5 600 K | 4,16 (6,04) | 1,59 | 4,77 |
| 4 | POSITIVE V1 | Standard | +2 | −2 | | 3, 0 | 5 600 K | 2,62 (4,31) | 1,15 | 2,61 |
| 5 | PORTRA 400 V2 (U2) | Standard | +3 | +2 | | 4, 0 | **5 600 K** | 2,79 (5,36) | 1,66 | 4,16 |
| 6 | HASSELBLAD V1 | Standard | +1 | −3 | | 3, 0 | 5 600 K | 2,30 (3,82) | 1,07 | 4,14 |
| 7 | TRI-X V1 (U1) | Monochrome | | | aucun | 5, +1 | **10 000 K** | 0,46 (1,89) | 0,45 | 1,06 |
| 8 | HP5 V1 | Monochrome | | | aucun | 4, −1 | 5 600 K | 2,42 (8,26) | 0,84 | 3,14 |
| 9 | FP4 V1 | Monochrome | | | aucun | 4, 0 | 5 600 K | 2,18 (5,59) | 0,58 | 2,90 |

Kodachrome et Portra : v2, contre leurs nouvelles cibles (§3.5 bis, §3.6 bis). Pour les sept autres, la livraison garde les réglages ci-dessous, avec des courbes recalculées après la correction des coins au 28 mm ; les chiffres à jour sont dans [`resume.json`](../recettes/d750-v1/resume.json) (Classic Chrome 1,35, Classic Neg 4,41, Positive 2,36, Hasselblad 2,23, Tri-X 0,44, HP5 2,19, FP4 2,11 sur les scènes).

Écarts prévus contre la cible, ΔE2000 médian (p90), avec la colorimétrie de la passe critique (§7) : les réglages sont ceux de la première passe, les chiffres bougent de 0,1 à 0,4. Ce sont des prévisions : calcul sur mesures, à contrôler (§6). Les écarts « scènes » sont mesurés sur les blocs qui ont servi à l'optimisation, donc un peu optimistes ; le lot 5 tenu à part donne pour Classic Chrome 1,46 au lieu de 1,15 (première passe).

Netteté et clarté ne sont pas mesurées par les séances (blocs uniformes). Elles reprennent les Picture Control de l'auteur actuels quand ils existent (Kodachrome 4 et +1, Tri-X 5 et +1, HP5 4 et −1, Portra 4 et 0), sinon la valeur par défaut de Standard (3) et une clarté nulle.

!Aperçus

*Figure 5. Pédalier (lot 3) : à gauche la cible, à droite le JPEG prévu par le modèle pour chaque recette, depuis le même NEF.*

### 5.2 Ce qui reste hors d'atteinte d'un Picture Control

Un Picture Control n'a que des réglages globaux : une base, un gain et une rotation de chroma uniques, une courbe sur la luma. Pas de matrice, pas de correction par teinte, pas de courbe par canal. Concrètement :
- **Classic Neg** : changements de teinte et de saturation qui dépendent de la couleur et de la clarté. Écart de 4 qui ne descendra pas avec un Picture Control.
- **Hasselblad et Positive** : la rotation voulue touche la butée (−3 pour Hasselblad) ; les couleurs saturées de la mire restent loin (p90 6,6 et 8,5).
- **Kodachrome** : sans WB plus froide, 4 à 4,7 ; avec, 2,4. Le reste demanderait des corrections par teinte.
- **HP5, FP4** : la sensibilité au bleu des films (§4.2).
- **Toutes** : les couleurs très vives sortent du gamut sRGB du JPEG, d'où les p90 de la mire.

### 5.3 Le Portra

Calculé sur la cible du preset Portra (§3.6) : **Standard, saturation +2, teinte +2, courbe**, WB 5 600 K en U2. Netteté 4 et clarté 0, reprises de ton « Portra 400 » actuel (Portrait, saturation +1, teinte −1, luminosité +1, que le modèle reproduit à 0,98 une fois mesurée la luminosité +1). Écart prévu au preset Portra : 3,2 sur les scènes et 2,2 sur la peau, contre 6,0 et 8,2 pour le réglage actuel. La part qui reste est le virage ombres froides / hautes lumières chaudes du preset Portra.

### 5.4 Balance des blancs pour U1 et U2

| Mode | Profil | WB fixe conseillée | Pourquoi | Statut |
|---|---|---|---|---|
| U1 | TRI-X V1 | **10 000 K** | retire du bleu au mélange « aucun », qui en a trop pour le preset : de 0,83 à 0,44 | calcul |
| U2 | PORTRA 400 V1 | **5 600 K** (6 250 K si la peau prime) | meilleur compromis contre le preset Portra : 3,17 sur les scènes, 2,22 sur la peau ; 6 250 K : 4,69 et 1,47 | calcul |

Hors modes U : Kodachrome à 5 000 K (§3.5), les autres à 5 600 K, la WB de la séance et du calcul. HP5 et FP4 gagneraient à une WB froide (4 000 K), mais ce n'est pas un réglage qu'on garde en emplacement C.

---

## 6. Faut-il un 3e lot ?

**Pas de lot de calibration en plus.** Les bases, les curseurs, les filtres et la courbe perso sont mesurés et le modèle prédit les v0 photographiées à 0,5-1,4 de ΔE. Un lot de plus n'apporterait que :
- les crans de saturation ±2 et ±1 des bases autres que Standard et Neutre, interpolés aujourd'hui. Seuls Neutre −2 (Kodachrome) et Standard +2 (Positive) servent, entre deux crans mesurés ;
- la montée au blanc au-delà de +2,3 IL ;
- la luminosité, qui ne sert plus à aucune recette.

**Un lot court de contrôle, en revanche, oui, avant d'écrire C-1 à C-9.** Il vérifie trois choses que la séance n'a pas pu voir :
1. saturation et teinte combinées à une courbe (hypothèse du §2.4) ;
2. la conversion kelvins → coefficients (Kodachrome à 5 000 K, Tri-X à 10 000 K), à lire dans les `WB_RBLevels` des NEF ;
3. l'écart réel de chaque recette à sa cible.

Plan prêt : `python3 outils/d750_seance.py plan <dossier> --lot v1`, 10 vues (les neuf recettes et la variante 5 600 K du Kodachrome), dans C-9 comme les séances.
- **Scène** : le pédalier (lot 3 : 135 mm, sans correction d'objectif, le meilleur ajustement), puis si possible le visage.
- **WB** : 5 600 K, sauf pour KODACHROME V1 (5 000 K) et TRI-X V1 (10 000 K). L'outil ne règle pas la WB : il faut la changer à la main avant ces deux vues, ou faire un passage par WB.

L'analyse de ce lot est déjà écrite : `d750_analyse.py validation` compare chaque vue au modèle et à sa cible. Si les écarts mesurés suivent ceux du §5.1 (à 0,5 près), les recettes v1 sont les définitives.

**Lot de contrôle fait** (photographié en octobre 2026 au soir, analysé en octobre avec `outils/mesures_reelles.py`) : résultats dans [`resultats-mesures.md`](resultats-mesures.md). Huit recettes suivent leur prévision à 0,6 près ; le Tri-X non, parce que les gains réels de la WB à 10 000 K (R 1,308, B 0,804, lus dans le NEF) sont plus chauds que ceux calculés ici : v2 proposée dans [`recettes/d750-v2/`](../recettes/d750-v2/README.md). Le cran −2 de saturation de Neutre, interpolé, vaut en réalité un gain de 0,80 (0,72 prévu). Saturation et teinte se combinent bien avec la courbe (hypothèse du §2.4 vérifiée).

---

## 7. Passe critique

Demandée par Thomas après les aperçus (« le vert est assez différent sur ta Portra ») : peut-on encore gagner des points ?

### 7.1 Où se loge l'écart : par teinte

Écart prévu contre la cible, par secteur de teinte de la cible (scènes et mire), recettes v1. Outil : `d750_analyse.ecarts_par_teinte`.

| Profil | rouge | orange, peau | jaune | vert | cyan | bleu | neutres |
|---|---|---|---|---|---|---|---|
| Classic Chrome | 1,8 | 1,3 | 4,1 | **3,7** | 3,5 | 4,3 | 1,1 |
| Classic Neg | 4,4 | 3,5 | 5,5 | **10,4** | 2,7 | 6,2 | 5,0 |
| Positive | 2,4 | 3,0 | 3,2 | **6,2** | 2,2 | 4,7 | 1,4 |
| Hasselblad | 2,6 | 1,8 | 2,6 | **4,7** | 4,5 | 5,5 | 2,8 |
| Portra | 4,7 | 2,3 | 4,1 | **13,0** | | 6,0 | 3,9 |
| Kodachrome (5 000 K) | 5,0 | 1,8 | 3,3 | **5,6** | | 4,5 | 2,5 |

ΔE2000 médian, colorimétrie du §7.2. Calcul.

**Le vert est le point faible de tous les profils.** Le D750 rend les verts plus jaunes (9 à 21°), plus saturés (×1,15 à 1,55) et, pour le Portra, plus clairs (+11 de L*) que toutes les cibles.
- Ce n'est pas le modèle du boîtier : ses verts sont reproduits à 0,19 près. Vérifié.
- Une partie venait de ma conversion capteur → couleur réelle (§7.2), corrigée.
- Le reste est la base elle-même : la saturation et la teinte sont réglées pour toute l'image d'un seul coup, et la courbe ne touche que la clarté. Rendre les verts plus sombres et plus bleutés sans toucher la peau n'est pas possible avec un Picture Control. C'est pour le Portra que ça se voit le plus : le preset Portra assombrit et éteint les verts plus que toutes les autres cibles.

### 7.2 Ce qui a été essayé

| Piste | Résultat | Retenue ? |
|---|---|---|
| **Colorimétrie de la scène** : racine-polynôme d'ordre 2 au lieu de la matrice 3 × 3 (neutres contraints) | mire : 1,20 en validation croisée (4 plis) contre 1,62 ; biais des verts 4,0° → 1,6°, cyan-verts 7,8° → 2,9° | **oui** : cibles plus justes ; les réglages des neuf recettes ne changent pas, les écarts prévus bougent de 0,1 à 0,4 (§5.1) |
| Quarts de cran de saturation et de teinte (le bloc USB les accepte) | l'optimum continu ne fait pas mieux que les crans entiers (Classic Chrome 1,29 continu contre 1,15 entier, première passe ; idem ailleurs à 0,1 près) | non : rien à gagner, et l'effet des quarts sur le boîtier n'est pas vérifié |
| Courbe plus fine (24 ou 32 nœuds au lieu de 16) | ±0,05 | non |
| Poids accru des teintes rares (verts) dans l'optimisation | Portra : vert 13,0 → 10,7, mais scènes 3,2 → 3,9 et peau 2,2 → 4,0 ; Classic Chrome : vert 3,7 → 3,6 pour 1,26 → 1,51 sur les scènes | non : perd plus qu'il ne gagne |
| Réglage fin vert-magenta de la WB (U2, Portra) | aucun décalage ne bat 5 600 K sans réglage fin | non |
| Réglage fin vert-magenta (U1, Tri-X) | +0,1 (plus de vert) : 0,44 au lieu de 0,46 sur les scènes | non : sous la précision, et l'effet d'un cran G-M n'est pas mesuré |
| Kodachrome : WB 4 700 à 5 300 K, réglage fin vert-magenta | 4 700 K Standard : 2,02 sur les scènes mais 1,49 sur la peau et 3,37 sur la mire ; 5 000 K Neutre reste le meilleur ensemble | non |
| Tri-X : filtre vert au lieu de aucun, à 10 000 K | 0,49 (1,72) contre 0,46 (1,89) : écart de score de 0,05 | non : ex aequo, on garde « aucun » |

**Conclusion : la v1 est au plafond de ce qu'un Picture Control peut faire contre ces cibles.** Les écarts qui restent viennent de ce que le Picture Control n'a pas : une correction par teinte (les verts) et un virage selon la clarté (Portra, Classic Neg). Seul le lot de contrôle (§6) peut encore faire bouger les recettes, s'il montre un écart entre le modèle et le boîtier.

## 8. Reproduire

```
# vos lots, rangés par d750_seance.py ranger, dans data/lotN
python3 outils/d750_blocs.py extraire data/lot1 blocs/lot1.npz           # idem lots 3, 4, 5
python3 outils/d750_blocs.py extraire data/lot2 blocs/lot2.npz --distorsion -0.0165,-0.22803,0.61979
python3 outils/d750_analyse.py modele blocs res/modele.json
python3 outils/d750_analyse.py bases blocs res/modele.json status_A res/bases.json
python3 outils/d750_analyse.py nb blocs res/modele.json res/nb.json
python3 outils/d750_analyse.py balance blocs res/modele.json status_A res/balance.json "KODACHROME:PAYSAGE,KODACHROME:NEUTRE,KODACHROME:STANDARD,HP5:AUCUN,FP4:AUCUN,CLASSIC NEG:STANDARD"
python3 outils/d750_analyse.py validation blocs res/modele.json status_A res/validation.json
python3 outils/d750_analyse.py recettes res/bases.json,res/bases-portra-esprit.json res/nb.json res/validation.json res/balance-kodachrome-spektrafilm.json recettes/d750-v1   # livraison d’octobre (Kodachrome et Portra v2)
python3 outils/d750_figures.py blocs res status_A data/lot3/rangees/01-BASE_STANDARD.NEF recherche/figures
```

Passe critique : les mêmes commandes avec la colorimétrie par défaut (racine-polynôme, `COLORIMETRIE` dans `d750_analyse.py`) ; `balance … --kelvins … --vm …` pour le réglage fin vert-magenta, `evaluer_recettes` et `ecarts_par_teinte` pour les tableaux du §8.

Les sorties de cette analyse (`modele.json`, `bases.json`, `nb.json`, `balance.json`, `validation.json`) sont dans [`donnees-films/d750-seances/`](donnees-films/d750-seances/) : les recettes et les figures s'en refont sans les images.

Portra : `d750_blocs.py paires <dossier des paires> blocs/portra.npz`, puis `d750_analyse.py cible-paires blocs/portra.npz recherche/donnees-films/d750-seances/portra-preset.json --look "<profil Base du preset Portra>.xmp"`, et `bases … PORTRA`. Le preset Portra n'est pas dans le dépôt (aucun fichier ni code de ce preset n'est redistribué) : les commandes qui calculent la cible Portra le cherchent dans le dossier de la variable d'environnement `D750_LOOKS`.

`status_A/` : réponses Status A d'agx-emulsion , voir l'en-tête de `kodachrome.py`. Le lot 2 reprend la distorsion du lot 1 (trop peu de points sur le visage). Durée totale sur 4 cœurs : environ 1 h 30, dont 40 min d'extraction des blocs.
