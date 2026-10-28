# Écarts réels des looks : ce que sortent vraiment le D750 et le D40

Mesures d’octobre 2026 (D40, test v1 du D750) et d’octobre 2026 (D750, lot de contrôle n° 2 et sa reprise, recettes réellement chargées), chantier B de `PLAN-PUBLICATION.md`. Outil : [`outils/mesures_reelles.py`](../outils/mesures_reelles.py) ; chiffres complets : [`donnees-films/mesures-reelles/`](donnees-films/mesures-reelles/).

**Les chiffres du D750 sont ceux de la reprise du lot n° 2** : les neuf Picture Control tels qu'ils sont dans le boîtier ([`recettes/d750/HISTORIQUE.md`](../recettes/d750/HISTORIQUE.md)), Tri-X v2 compris, photographiés sur la bibliothèque sous une seule lumière (jour et LED à 5 600 K). Le lot n° 2 du matin, sous lumière mêlée (jour et lampe chaude), est détaillé plus bas. Le test v1 d’octobre (recettes d'avant la livraison) reste plus bas, pour l'historique.

Légende : **mesuré** = JPEG sorti du boîtier contre la cible du look, la scène étant lue dans le NEF de la même photo ; **prévu** = rendu calculé par le modèle du boîtier contre la cible.

## Le tableau

ΔE2000 entre le JPEG et la cible, sur les zones uniformes de l'image (blocs de 24 × 24 px au D750, de 12 × 12 px au D40). Médiane, et 90e centile (p90 : 90 % des zones font mieux).

| Look | Boîtier | Médiane | p90 | Source |
|---|---|---|---|---|
| Kodachrome | D750 | 3,4 | 6,2 | reprise, WB 6 250 K ; cible : spektrafilm Kodachrome 64, chroma × 1,2 |
| Classic Chrome | D750 | 1,8 | 3,0 | reprise ; cible : LUT officielle Fujifilm |
| Classic Chrome | D40 | 1,4 | 2,7 | DSC_6262, 1 vue ; cible : JPEG Classic Chrome du X-T4 (3,6 contre la LUT, voir plus bas) |
| Classic Neg | D750 | 5,1 | 6,9 | reprise ; cible : LUT officielle Fujifilm |
| Positive | D750 | 2,9 | 4,8 | reprise ; cible : JPEG Positive Film du GR III |
| Positive | D40 | 1,6 | 2,8 | 3 vues (1,5 à 1,9) |
| Portra 400 | D750 | 4,6 | 6,3 | reprise ; cible : « esprit Portra » (le preset Portra réglé) |
| Hasselblad | D750 | 2,5 | 4,0 | reprise ; cible : JPEG du X2D |
| Hasselblad | D40 | 2,7 | 3,8 | DSC_6261, 1 vue |
| Tri-X | D750 | 1,2 | 1,7 | reprise, Tri-X v2, WB 10 000 K ; cible : le preset Tri-X |
| Tri-X | D40 | 0,5 | 2,8 | 4 vues (0,4 à 0,5, et 2,5 sur une) |
| HP5+ | D750 | 3,2 | 6,7 | reprise ; cible : fiche Harman, tonalité des scans de Thomas |
| HP5+ | D40 | 2,7 | 4,6 | 11 vues (1,1 à 3,7) ; cible : fiche Harman, tirage grade 2 |
| FP4+ | D750 | 2,6 | 7,4 | reprise ; cible : fiche Harman |

Le D40 n'a ni Kodachrome, ni Classic Neg, ni Portra, ni FP4. D750 : la bibliothèque sous une seule lumière (4 675 blocs du centre, les mêmes pour tous les looks) ; D40 : 1 à 11 photos par look.

**14 looks mesurés** (9 au D750, 5 au D40) : **10 ont une médiane sous 3** (les 5 du D40 ; au D750, Tri-X, Classic Chrome, Hasselblad, FP4 et Positive), aucun ne dépasse 5,1. Au-dessus : Classic Neg (5,1), Portra (4,6), Kodachrome (3,4) et HP5 (3,2) au D750. Le boîtier fait ce que le modèle prévoit (modèle contre JPEG : 0,9 à 1,9, Portra 2,5) : les écarts viennent des recettes, pas d'un comportement imprévu du boîtier.

## Le ΔE, pour quelqu'un qui n'en a jamais entendu parler

Le ΔE (delta E) mesure l'écart entre deux couleurs tel que l'œil le perçoit : 0, c'est la même couleur. La version 2000 (ΔE2000) corrige les défauts des anciennes formules, qui exagéraient les écarts dans les couleurs vives et les sous-estimaient dans les gris et les bleus. Repères :
- **sous 1** : invisible, même pour un œil exercé ;
- **1 à 2** : visible seulement par un œil entraîné, les deux images côte à côte ;
- **2 à 3** : visible côte à côte, pas quand on regarde une image seule ;
- **3 à 5** : visible côte à côte pour tout le monde, la « famille » de rendu reste la même ;
- **au-delà de 5** : saute aux yeux, ce n'est plus tout à fait le même rendu.

On compare l'image entière, zone par zone. La **médiane**, c'est l'écart de la zone typique ; le **p90**, celui des zones les plus difficiles (souvent les couleurs les plus vives).


## D750 : la reprise du lot n° 2 (octobre 2026, une seule lumière)

**Les photos.** `images/d750/2026-10-test-v2-bibliotheque/` : la bibliothèque, chaise retirée, cadrage complet, lampe de la pièce éteinte, lumière du jour et LED à 5 600 K. 28 mm, f/5,6, 1/20 s, ISO 200, mode M, D-Lighting coupé, NEF + JPEG fine. Série courte : BASE STANDARD et les neuf Picture Control chargés (Tri-X v2 en C-7), chacun à sa WB. Boîtier relu avant, conforme à l'historique ; rien écrit hors de C-9, remis à la fin. Même méthode que le lot n° 2 (4 675 blocs du centre).

| Look (chargé) | Mesuré | Prévu à la livraison | Prévu sur cette scène | Modèle contre JPEG | Lot n° 2 (lumière mêlée) |
|---|---|---|---|---|---|
| Kodachrome (6 250 K) | 3,44 (6,15) | 2,8 | 2,84 | 0,97 | 3,52 |
| Classic Chrome | 1,75 (3,02) | 1,4 | 1,37 | 1,14 | 2,36 |
| Classic Neg | 5,08 (6,89) | 4,4 | 5,55 | 1,17 | 3,80 |
| Positive | 2,89 (4,77) | 2,4 | 2,14 | 1,91 | 3,51 |
| Portra 400 | 4,59 (6,29) | 2,8 | 4,20 | 2,46 | 4,07 |
| Hasselblad | 2,45 (3,96) | 2,2 | 2,68 | 1,49 | 3,23 |
| Tri-X v2 (10 000 K) | 1,17 (1,72) | 0,33 | 0,43 | 1,01 | 1,96 |
| HP5+ | 3,21 (6,73) | 2,2 | 2,52 | 1,10 | 5,15 |
| FP4+ | 2,55 (7,36) | 2,1 | 2,30 | 0,94 | 5,41 |

ΔE2000 médian (p90). Ce qu'on en tire :
- **Une seule lumière, et l'essentiel rentre dans les prévisions** : six looks sur neuf sont à moins de 0,7 du prévu de la livraison. Tri-X v2 à 1,2 ; HP5 et FP4 reviennent de 5,2-5,4 à 3,2 et 2,6, ce qui confirme que la lumière mêlée du matin était en cause (le Monochrome voit les lumières chaudes et froides autrement que ces films).
- **HP5+ et FP4+ : pas de v2** (décision de Thomas, octobre 2026). Une courbe refaite avec la reprise dans le calcul gagnerait sur les scènes (prévu HP5 2,2 → 1,5, FP4 2,1 → 1,5) mais perdrait sur la peau (0,9 → 1,4 et 0,6 → 1,0) : gain global faible, choix de goût.
- **Classic Neg (5,1) et Portra (4,6) montent** : sur cette scène, la recette elle-même les prévoit à 5,6 et 4,2, et le boîtier suit le modèle (1,2 et 2,5). Ces deux looks dépendent beaucoup du contenu de la scène : ils changent teinte et saturation selon la couleur, ce qu'un Picture Control ne sait pas faire (voir « Ce qui ne descend pas »).

## D750 : vues d'extérieur (octobre 2026, main levée)

**Les photos.** `images/d750/2026-10-exterieur/` : neuf vues de Thomas, une par Picture Control chargé, à main levée, exposition automatique, WB Auto (≈ 5 800 K, pas la WB prévue du Tri-X ni du Kodachrome), 28 mm, ISO 200. Chaque JPEG face à son NEF ; données : [`exterieur.json`](donnees-films/mesures-reelles/exterieur.json).

| Vue | Mesuré (scène à 5 600 K) | Mesuré (WB du boîtier) | Modèle contre JPEG |
|---|---|---|---|
| FP4+ | 0,92 | 0,94 | 0,85 |
| Tri-X v2 | 1,05 | 1,00 | 0,98 |
| HP5+ | 1,44 | 1,65 | 0,88 |
| Portra 400 | 3,07 | 2,23 | 2,45 |
| Classic Chrome | 3,27 | 2,35 | 4,60 |
| Positive | 4,64 | 3,22 | 2,43 |
| Hasselblad | 4,38 | 4,14 | 2,95 |
| Classic Neg | 6,89 | 4,85 | 3,77 |
| Kodachrome | 10,14 | 9,15 | 2,71 |

**À lire avec précaution : ce test mesure surtout le ciel.** Seules les zones uniformes comptent ; dehors, ce sont presque toutes du ciel (50 à 75 % des blocs, L\* 74 à 90 dans le JPEG), à des luminances de scène 2 à 3 fois plus hautes que tout ce qui a servi au calcul (Y médian 0,6 à 1,1, contre 0,2 aux lots de calibration). Ni le modèle (jusqu'à 4,6) ni les recettes n'ont été calés dans ces hautes lumières : c'est là que le ciel peut sortir « bizarre » (écarts surtout dans les cyans, 5 à 12). Le noir et blanc tient (0,9 à 1,4). Pour conclure sur le ciel, une série sur trépied a suivi (section suivante) : elle ne confirme pas ce décrochage.

## D750 : le ciel par la fenêtre (octobre 2026, trépied, mesuré)

**Les photos.** `images/d750/2026-10-fenetre/` : série courte de `d750_lot_v2.sh --bibliotheque` pilotée par USB, 50 mm sur trépied calé sur la fenêtre, f/5,6, 1/1 000 s, ISO 200, mode M, exposition calée sur l'extérieur (intérieur bouché). Dix vues : BASE STANDARD et les neuf Picture Controls chargés, chacun à sa WB (Kodachrome 6 250 K, Tri-X v2 10 000 K, les autres 5 600 K). Réglages de Thomas remis à la fin. Seuls comptent les blocs du battant ouvert, sans vitre (x 0,06 à 0,64, y 0,34 à 0,84 du JPEG, option `--zone`) : 6 235 blocs, dont 5 748 de ciel (Y de scène > 0,5). Données : [`fenetre.json`](donnees-films/mesures-reelles/fenetre.json).

| Look | Mesuré, médian (p90) | Modèle contre JPEG | Reprise (intérieur) |
|---|---|---|---|
| HP5+ | 1,0 (2,2) | 1,0 | 3,2 |
| Tri-X v2 | 1,1 (1,8) | 1,0 | 1,2 |
| FP4+ | 1,2 (3,3) | 1,0 | 2,6 |
| Positive | 2,1 (3,6) | 0,8 | 2,9 |
| Portra 400 | 3,0 (4,5) | 1,2 | 4,6 |
| Hasselblad | 3,1 (3,9) | 0,7 | 2,5 |
| Classic Chrome | 3,4 (4,8) | 1,3 | 1,8 |
| Kodachrome | 4,1 (4,7) | 0,5 | 3,4 |
| Classic Neg | 6,3 (7,3) | 0,8 | 5,1 |

**Ce que ça dit.** Le ciel ne décroche pas : sur trépied, exposé pour lui et à la bonne WB, Kodachrome est à 4,1 (pas 10), et le ciel seul (Y > 0,5) donne les mêmes écarts que le reste de la zone. Surtout, le modèle reproduit le JPEG du boîtier à 0,4 à 1,4 jusque dans ces hautes lumières : courbes et matrices tiennent, **pas de recalibrage à faire**. Les écarts restants sont ceux des recettes elles-mêmes (le « prévu » du calcul, 0,4 à 5,7, suit le mesuré), les mêmes qu'en intérieur à ±1. Les gros écarts des vues à main levée venaient donc de leurs conditions (WB Auto, exposition automatique), pas du ciel. Le noir et blanc est meilleur ici qu'en intérieur : un ciel n'a presque qu'une couleur, le mélange des couleurs du mode Monochrome n'y pèse pas. Calcul : WB du Tri-X à 10 000 K, gains du NEF R 1,31 / B 0,80 contre 1,18 / 0,76 calculés (écart déjà connu, sans effet sur le N&B).

## D750 : le lot de contrôle n° 2 (octobre 2026, lumière mêlée, recettes chargées)

**Les photos.** `images/d750/2026-10-test-v2/` : bibliothèque de jour (lampes de la pièce allumées), 28 mm, f/5,6, 1/15 s, ISO 200, mode M, D-Lighting coupé, NEF + JPEG fine. Avant la prise : boîtier relu, conforme à l'historique, puis Tri-X v2 écrit en C-7. Chaque vue : le bloc envoyé dans C-9 (octets des Picture Control chargés, ou cran à tester), WB réglée par USB. 19 vues en six passages. Une chaise occupe le quart gauche (cadrage différent de la séance 4).

**Méthode.** Celle du test v1, avec deux différences dues au 28 mm : blocs du centre seulement (rayon < 0,7 ; le boîtier corrige la distorsion du JPEG, le recalage n'est sûr qu'au centre), vignetage f/5,6 du modèle appliqué à la scène. Les mêmes 3 847 blocs pour tous les looks. Recette de chaque vue = le bloc réellement envoyé.

| Look (chargé) | Mesuré | Prévu à la livraison (scènes des lots 1, 3, 4) | Prévu sur cette scène | Modèle contre JPEG |
|---|---|---|---|---|
| Kodachrome (6 250 K) | 3,52 (5,32) | 2,8 | 2,95 | 0,97 |
| Classic Chrome | 2,36 (4,04) | 1,4 | 1,67 | 0,81 |
| Classic Neg | 3,80 (5,45) | 4,4 | 3,95 | 0,88 |
| Positive | 3,51 (6,20) | 2,4 | 2,81 | 1,43 |
| Portra 400 | 4,07 (6,03) | 2,8 | 3,30 | 2,07 |
| Hasselblad | 3,23 (4,64) | 2,2 | 2,90 | 1,13 |
| Tri-X v2 (10 000 K) | 1,96 (3,79) | 0,33 | 1,21 | 1,19 |
| *ancien Tri-X (10 000 K)* | *2,70 (4,37)* | *0,4* | *1,70* | *1,19* |
| HP5+ | 5,15 (9,46) | 2,2 | 4,87 | 1,10 |
| FP4+ | 5,41 (11,79) | 2,1 | 5,35 | 1,06 |

ΔE2000 médian (p90). Ce qu'on en tire :
- **Le boîtier suit le modèle** (dernière colonne, 0,8 à 1,4 ; Portra 2,1). Le mesuré est le prévu sur cette scène plus l’erreur du modèle (−0,2 à +0,8).
- **Cette scène est plus dure que celles du calcul** : le prévu y est plus haut que le prévu de la livraison pour presque tous les looks. Lumière mêlée (jour et lampes chaudes), beaucoup de blancs et de dos de livres.
- **Tri-X v2 confirmé** : 1,96 contre 2,70 pour l'ancien, sur les mêmes blocs (−0,7, comme prévu : 1,21 contre 1,70). Il reste en C-7.
- **HP5+ et FP4+ : le mélange des couleurs, pas la courbe.** L'écart est tout en clarté (en noir et blanc, il n'y a qu'elle), et la recette prévoit le même défaut (4,9 et 5,4). À gris égal dans la scène, les zones orangées (éclairées par les lampes) sortent plus claires que la cible (+3 à +4 L\*), les autres plus sombres (−7 L\*) : le Monochrome du D750 voit plus le rouge et moins le bleu que ces films, et une courbe unique ne peut pas corriger les deux sens à la fois. Vérifié : une courbe refaite avec ce lot dans le calcul (`mesures_reelles.py nb_v2`, cinq filtres essayés) ne gagne rien (score HP5 4,68 → 4,72, FP4 4,53 → 4,51 ; le filtre « aucun » reste le meilleur). Sur la vue Standard de la séance 4 (même pièce, éclairage du soir), la même recette HP5 est prévue à 2,8 : l'écart dépend surtout du mélange des lumières.

**Gains réels de la WB** (rapportés à 5 600 K, lus dans les NEF ; R / B, V = 1) :

| WB réglée | Mesuré | Calculé | Écart |
|---|---|---|---|
| 4 000 K | 0,785 / 1,233 | 0,834 / 1,305 | −6 % / −6 % |
| 5 000 K | 0,944 / 1,089 | 0,949 / 1,084 | −0,5 % / +0,5 % |
| 6 250 K | 1,052 / 0,939 | 1,045 / 0,933 | +0,7 % / +0,6 % |
| 8 000 K | 1,184 / 0,868 | 1,128 / 0,823 | +5 % / +5 % |
| 10 000 K | 1,308 / 0,804 | 1,184 / 0,757 | +10 % / +6 % |

Le calcul tient entre 5 000 et 6 250 K ; au-delà, le boîtier va plus loin que la formule de la lumière du jour. Le Kodachrome (6 250 K) n'est pas concerné ; les recettes futures prendront ces gains mesurés.

**Crans de Standard** (gain CbCr pour la saturation, rotation pour la teinte ; jamais photographiés avant) :

| Cran | Mesuré | Modèle (interpolé) |
|---|---|---|
| saturation +2 | gain 1,282 | 1,258 |
| saturation +2,5 | gain 1,353 | 1,322 |
| teinte −2 | −4,7° | −4,2° |
| teinte −2,5 | −5,7° | −5,1° |
| teinte +2 | +3,4° | +3,8° |

Les demi-crans fonctionnent : le boîtier les applique, à mi-chemin entre les crans entiers. L'interpolation du modèle est juste à 2,5 % près pour le gain et 0,6° pour la rotation.

## D750 : le test de contrôle des recettes v1 (octobre 2026, historique : recettes d'avant la livraison)

**Les photos.** `images/d750/2026-10-test-v1/` : pédalier, même cadrage et réglages que le lot 3 (135 mm sans correction d'objectif, f/4, ISO 200, D-Lighting coupé), mais **le soir, en lumière artificielle**. Chaque recette écrite dans C-9 par USB, photographiée, puis effacée. WB 5 600 K, sauf Kodachrome (5 000 K) et Tri-X (10 000 K). Une vue de plus : le Kodachrome v1 pris par erreur à 5 600 K. Vérifié : les 11 blocs envoyés au boîtier sont identiques aux recettes (`bloc_envoye_identique`).

**Méthode.** Celle de [`d750-analyse-seances.md`](d750-analyse-seances.md) : blocs uniformes, chaque JPEG face à son NEF (recalage 0,3 px), colorimétrie racine-polynôme du §7.2, cibles de `d750_cibles.py`. Les mêmes 5 212 blocs pour toutes les vues. La scène est ramenée à la balance 5 600 K lue dans le NEF, comme pour le calcul des recettes (la WB réglée change le JPEG, pas la scène).

| Look | Mesuré | Prévu au §5.1 (jour, scènes des lots 1, 3, 4) | Prévu sur la scène du test | Modèle contre JPEG |
|---|---|---|---|---|
| Kodachrome (5 000 K) | 2,82 (4,83) | 2,57 (4,07) | 2,10 | 1,24 |
| Classic Chrome | 1,56 (3,79) | 1,29 (2,56) | 1,27 | 1,08 |
| Classic Neg | 3,67 (10,05) | 4,16 (6,04) | 3,96 | 1,18 |
| Positive | 3,21 (5,53) | 2,62 (4,31) | 2,87 | 1,26 |
| Portra 400 | 2,78 (12,35) | 3,16 (8,24) | 2,55 | 1,18 |
| Hasselblad | 2,60 (4,75) | 2,30 (3,82) | 1,77 | 1,13 |
| Tri-X (10 000 K) | 1,49 (3,90) | 0,46 (1,89) | 1,29 | 0,86 |
| HP5+ | 2,75 (11,19) | 2,42 (8,26) | 2,94 | 0,74 |
| FP4+ | 2,46 (15,61) | 2,18 (5,59) | 2,65 | 0,36 |
| *Kodachrome, variante 5 600 K* | *4,72 (5,82)* | *4,4* | *3,95* | *1,24* |
| *Kodachrome v1 pris à 5 600 K* | *5,70 (6,89)* | | *5,03* | *1,54* |

ΔE2000 médian (p90). Les prévisions du §5.1 sont refaites ici à l'identique pour la peau et la mire, à 0,35 près pour les scènes (blocs réextraits).

Ce que le test établit :
- **Huit recettes sur neuf suivent leur prévision** à 0,6 près (critère du §6 : 0,5 ; Positive à +0,59). Les écarts mesurés valent donc aussi pour ces huit recettes, à la scène près.
- **Le Tri-X ne la suit pas**, et la cause est trouvée : à 10 000 K, le boîtier applique des gains R / B de 1,308 / 0,804 (lus dans le NEF) au lieu des 1,184 / 0,757 calculés. Le mélange est plus chaud que prévu, la courbe ne lui va plus : 1,19 sur les scènes et 2,85 sur la peau au lieu de 0,44 et 0,45 (modèle d'avant la correction des coins du 28 mm). **v2 proposée** ([`recettes/d750-v2/`](../recettes/d750-v2/README.md)) : courbe refaite pour les gains réels, filtre aucun, calculée avec le modèle de la livraison (coins du 28 mm corrigés) : 0,33 (scènes), 0,64 (peau), 0,77 (mire). Avec ce modèle, le Tri-X chargé en C-7 fait 0,74 et 1,24 avec les gains réels (0,44 et 0,62 prévus). À 5 000 K, gains calculés et réels concordent (0,949 / 1,084 contre 0,944 / 1,089).
- **Saturation et teinte combinées à une courbe** (hypothèse du §2.4) : le modèle redonne ces JPEG à 1,1-1,3 (1,5 pour le Kodachrome pris à 5 600 K ; 0,4-0,9 en noir et blanc), au niveau de son plancher sur les lots au 28 mm. Vérifié.
- **Le cran −2 de saturation de Neutre** (Kodachrome), interpolé dans le modèle, est plus saturé que prévu : gain mesuré 0,80 à 0,81 (deux vues) au lieu de 0,72. Écart prévu du Kodachrome corrigé : 2,84 sur les scènes, 1,41 sur la peau (au lieu de 2,52 et 0,85). Piste, non écrite : le gain voulu (0,68) tombe entre −3 et −2 ; un demi-cran (−2,5, accepté par le bloc USB, effet non mesuré) le donnerait. Le cran −3 entier fait moins bien (peau 2,43).
- **Sous cette lumière, le modèle tourne les teintes de 2 à 3° de trop** en couleur à 5 600 K (JPEG − modèle : −1,9 à −2,9°), pas à 5 000 K (+0,1°). C'est ce qui fait passer Hasselblad et Kodachrome de 1,8-2,1 prévus à 2,6-2,8 mesurés. Le modèle a été ajusté en lumière du jour : écart lié à la lumière (hypothèse), pas aux recettes, donc rien à corriger dans celles-ci sans un test de jour.
- **La pédale vert vif en noir et blanc** : le boîtier la rend 10 à 15 L* plus claire que le modèle et que la cible (11 % des blocs). C'est tout le p90 de HP5 et FP4. Cause non trouvée ; hypothèse : le gris est calculé après un écrêtage des couleurs très saturées.

## D40 : les cinq looks de la V5

**Les photos.** `images/d40/2026-10-test-v1/`, prises avec la V3 (fiche EXIF dans `sondes/v1/test-10/exif.tsv`) ; on garde les 20 NEF pris en P, S, A ou M avec un préréglage (en mode Auto, rendu Nikon). Balance auto, lumière mêlée (lampes, fin de jour, flash sur 6 vues). La V5 a les mêmes tables de rendu, vérifié à l'octet (`patchs/preglages-v1.json` dans `build/V5/`) ; seuls 8 octets du code des préréglages y sont repris par l'étape 9 (Programme).

**Méthode.** La scène vient du NEF : RVB du D40 (balance du boîtier) → XYZ par la matrice des sensibilités camspec (`recettes/mesures/*.json`), échelle d'exposition calée sur le D40 (un gris rendu 118/255 par la courbe IIIa Normal vaut 18 %). Cibles : les mêmes qu'au D750 (Hasselblad et Positive : modèles mesurés sur paires RAW + JPEG du X2D et du GR III ; Tri-X : le preset Tri-X), sauf HP5 (fiche Harman et tirage grade 2, la cible de la V1 du D40) et Classic Chrome (voir plus bas). « Prévu » = simulateur du D40 avec les tables de la V1.

| Look (préréglage) | Vues | Mesuré | Simulateur contre JPEG | Prévu |
|---|---|---|---|---|
| Hasselblad (Soft) | 1 | 2,71 (3,81) | 1,26 | 2,85 |
| Classic Chrome (Vivid), cible JPEG X-T4 | 1 | 1,42 (2,74) | 1,44 | 1,13 |
| Classic Chrome (Vivid), cible LUT Fujifilm | 1 | 3,59 (4,52) | 1,44 | 4,48 |
| Positive (More Vivid) | 3 | 1,64 (2,83) | 1,07 à 1,61 | 0,86 |
| Tri-X (Portrait) | 4 | 0,53 (2,84) | 0,38 à 2,49 | 0,01 |
| HP5+ (Black And White) | 11 | 2,65 (4,59) | 1,20 à 3,59 | 0,16 |

Ce que le test établit :
- **Le HP5 sort 0,11 IL trop clair, et c'est le mode N&B de Nikon.** En Black And White, le boîtier note ses gains de balance avec un vert à 1,082 au lieu de 1 ; LibRaw, et donc le simulateur, ramène le vert à 1, ce qui revient à retirer un gain de 1,082 sur toute l'image. Avec ce gain, le simulateur redonne le JPEG à 0,2-1,2 au lieu de 1,2-3,6 (JPEG plus clair de 2 à 4 L*). Presque tout l'écart du HP5 vient de là : une V6 pourrait compenser sa courbe (entrée divisée par 1,082). Le Tri-X, rangé dans un préréglage couleur (Portrait), n'a pas ce gain.
- **Tri-X : 0,4 à 0,5 sur trois vues, 2,5 sur la quatrième** (DSC_6258, autre lumière : balance auto R 2,43 / B 1,18 contre 2,34 / 1,35 sur les trois autres) : JPEG plus sombre de 3 L* que le simulateur. Hypothèse : la balance auto y a choisi un autre emplacement de matrice (la matrice déclinée n° 16 redonne mieux le JPEG que la n° 13 du simulateur, 1,7 contre 2,5).
- **Hasselblad : l'écart est le blanc.** La cible HNCS a un blanc teinté (a* −3, b* +4,5 sur les neutres) que la V1 ne transporte pas, par choix (« lignes = 512 », README du projet) : 3,1 sur les neutres, 1 à 3,4 sur les couleurs courantes.
- **Classic Chrome : deux cibles qui ne s'accordent pas.** Le D40 a été calé sur les JPEG du X-T4, le D750 sur la LUT vidéo officielle de Fujifilm. Sur la même scène, ces deux « Classic Chrome » sont à 3,9 l'un de l'autre (4,2 sur le pédalier du D750). Chaque boîtier tient sa propre cible (1,4 et 1,6) ; le D40 est à 3,6 de la LUT, le D750 à 4,4 du JPEG du X-T4.
- **Simulateur contre boîtier** : 1,1 à 1,6 en couleur, comme sa validation d’octobre (0,9 à 2,8 en IIIa). Le simulateur suppose l'emplacement de balance du jour ; la balance auto en choisit d'autres sous les lampes.

## Ce qui ne descend pas, et pourquoi

**Au D750, la limite est le Picture Control.** Il n'offre que des réglages globaux : une base (une matrice et une courbe de Nikon), un gain et une rotation de la couleur appliqués à toutes les teintes d'un coup, une courbe sur la seule luminosité. Ni matrice libre, ni correction par teinte, ni courbe par canal.
- **Classic Neg (5,1 à la reprise, 3,8 sous lumière mêlée)** : le film change teinte et saturation différemment selon la couleur et la clarté (au test v1 : verts à 10,9 de ΔE, rouges à 5,1 ; au lot n° 2, jaunes à 7,7). Une rotation unique ne peut pas faire ça.
- **Positive (2,9) et Hasselblad (2,5)** : même limite sur les verts et les cyans, et la rotation de teinte voulue pour Hasselblad est en butée (−3). Au lot n° 2 (lumière mêlée), le gros de l'écart du Hasselblad est sur les blancs et les gris (3,6) : la cible garde le blanc légèrement teinté du X2D, que le boîtier ne fait pas (a\* +2,4, b\* −1,8).
- **Portra (4,6 à la reprise, p90 6,3)** : au lot n° 2, les tons orangés (5,1, teinte décalée de 9°) ; au test v1, le preset Portra rend les verts plus sombres et plus bleutés que tout ce que le boîtier sait faire (13,9 sur les verts), et vire les ombres au froid et les hautes lumières au chaud ; le Picture Control n'a qu'une teinte pour toute l'image.
- **HP5 et FP4 (3,2 et 2,6 à la reprise ; 5,2 et 5,4 sous lumière mêlée)** : ces films voient beaucoup de bleu et peu de rouge ; les filtres du Monochrome Nikon n'ajoutent jamais de bleu (au mieux 36 %, la fiche HP5 en veut 67 %). Sous une lumière mêlée (jour et lampes chaudes), l'écart se voit en clarté, dans un sens ou dans l'autre selon la couleur de la lumière : aucune courbe ne le rattrape (vérifié).
- **Le vert, partout** : le D750 rend les verts plus jaunes et plus saturés que toutes les cibles, et rien ne permet de les reprendre sans toucher la peau.

**Au D40, la limite n'est pas le format** (matrice, courbe et correction par secteur de teinte sont dans les tables du firmware) : ce sont des détails de réglage, corrigeables dans une V6 (gain du mode N&B pour le HP5, blanc teinté du Hasselblad, emplacement de balance).

## Limites de ces mesures

- **Une scène au D750**, la bibliothèque, sous deux éclairages : une seule lumière à 5 600 K (reprise, chiffres retenus) et lumière mêlée (lot n° 2). Le contenu de la scène compte surtout pour Classic Neg et Portra ; l'éclairage, surtout pour HP5 et FP4.
- **Une seule vue** pour Hasselblad et Classic Chrome au D40.
- La « scène » est calculée depuis le NEF (matrice du capteur ajustée sur une mire : 1,2 de ΔE en validation croisée au D750, sensibilités camspec au D40). Une erreur de cette conversion change la cible, pas le JPEG.
- Seules les zones uniformes comptent : les textures, la netteté et le grain ne sont pas mesurés.


## Refaire

```
python3 outils/mesures_reelles.py d750 <travail/> <status_A/>      # blocs, mesures, prévisions refaites, Tri-X v2 (≈ 5 min)
python3 outils/mesures_reelles.py d40 <travail/>
python3 outils/mesures_reelles.py planches <travail/> <status_A/>
python3 outils/mesures_reelles.py publier <travail/>               # → donnees-films/mesures-reelles/
python3 outils/mesures_reelles.py lot2 <travail/> <status_A/> [images/d750/2026-10-test-v2-bibliotheque]   # lot n° 2 ou sa reprise (D750_SPEKTRAFILM)
```

`prevision.json` garde le classement Tri-X v2 du modèle d'avant la correction des coins du 28 mm (filtre vert en tête) ; la v2 retenue dans `recettes/d750-v2/` a été recalculée avec le `modele.json` actuel (filtre aucun).

`<travail/>` hors du dépôt ; `status_A/` : réponses Status A d'agx-emulsion (en-tête de `kodachrome.py`) ; cible du preset Portra : variable `D750_LOOKS`. Sans scikit-image, les points communs se cherchent par OpenCV.
