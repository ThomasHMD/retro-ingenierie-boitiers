# R&D Nikon, novembre 2026, passe 3 : valider par validation croisée les recettes du D750 avant de les charger

Suite de [`rd-nikon-2026-11-ajustement-nx.md`](rd-nikon-2026-11-ajustement-nx.md) (passe 2, NP2) et de [`rd-nikon-2026-11-formats-nx.md`](rd-nikon-2026-11-formats-nx.md). Décision de Thomas : charger dans le boîtier les recettes améliorées, **sans nouvelle prise de vue**, en validant avec les RAW déjà sur le disque. Code : [`outils/d750_valider_nx.py`](../outils/d750_valider_nx.py) (nouveau ; `d750_ajuster_nx.py`, `nx_rendu.py` et `picture_control.py` ne sont pas modifiés). Sorties : [`recettes/d750-v3/`](../recettes/d750-v3/README.md). Rien n'a été chargé, publié, commité ni flashé ; aucune commande n'a été envoyée au boîtier. Statuts : **mesuré** = sorti d'un calcul de cette séance ; **hypothèse** = non testé.

## En bref
- **Chargées ensuite** : les quatre recettes v3 ont été écrites dans C-2 à C-5 en novembre 2026 (relecture identique à l'envoi, `recettes/d750/HISTORIQUE.md`).
- **Quatre recettes changent, trois restent.** Classic Chrome, Classic Neg, Positive et Portra 400 passent la règle de décision (écrite avant les mesures, §3). Hasselblad, HP5+ et FP4+ ne la passent pas : **aucun changement dans le boîtier** pour C-6, C-8, C-9.
- Sur les scènes tenues à part (médiane ΔE2000 contre la cible, moyenne des 7 scènes), actuelle → ajustée : Classic Chrome 2,35 → 1,93, Classic Neg 4,95 → 4,73 (limite : gain 0,22 pour un seuil de 0,2), Positive 3,38 → 2,54, Portra 3,78 → 2,85. Le p90 baisse pour les quatre.
- Le chiffre est mesuré **dans NX Studio**, pas sur un JPEG sorti du boîtier avec ces recettes (limites, §6).
- Commandes de chargement prêtes pour C-2, C-3, C-4, C-5 (§7), **non lancées**.

## 1. Scènes
Une scène = un NEF par lieu et lumière, avec son JPEG du boîtier (nécessaire au gain radial par NEF, comme avant) et ses blocs uniformes de 24 px (même masque que `mesures_reelles.py` / `d750_analyse.py`, rayon < 0,7 au 28 mm). Le NEF est développé par NX avec la recette imposée en NP2 (`SavedPicConProcess=1`), donc la recette du NEF d'origine n'a pas d'importance. Cible calculée depuis la scène lue dans le même NEF, comme dans la passe 2. **Sept scènes retenues** (blocs retenus, part des blocs, NX tel quel contre le JPEG du boîtier, gain radial retiré, médiane) :

| Scène (identifiant) | Prise de vue (EXIF) | Blocs (part) | NX / JPEG |
|---|---|---|---|
| guitares | pièce aux guitares, séance d’octobre (lot 1) : 28 mm, f/1,8, 1/160 s, ISO 1800 | 14 686 (23 %) | 1,73 |
| portrait | séance d’octobre (lot 2) : 28 mm, f/1,8, 1/160 s, ISO 200 | 18 592 (29 %) | 1,21 |
| bibliotheque-soir | séance d’octobre (lot 4) : 28 mm, f/5,6, 1/10 s, ISO 200 | 5 568 (9 %) | 0,79 |
| pedalier | test v1 = lot 3 : 135 mm sans CPU, f/4, 1/10 s, ISO 200 (vue 01 CLASSIC CHROME V1, blocs communs aux 11 vues) | 5 212 (8 %) | 0,94 |
| bibliotheque-jour | test v2 d’octobre (`2026-10-test-v2-bibliotheque`, vue 01 BASE STANDARD) : 28 mm, f/5,6, 1/20 s, ISO 200 | 7 148 (11 %) | 1,21 |
| exterieur | octobre (vue 08 CLASSIC CHROME) : 28 mm, f/8, 1/250 s, ISO 200, WB Auto | 7 763 (12 %) | 0,92 |
| fenetre | octobre (vue 01 BASE STANDARD) : 50 mm, f/5,6, 1/1000 s, ISO 200, vertical ; blocs du battant ouvert seulement (x 0,04 à 0,66, y 0,33 à 0,86 du JPEG enregistré : la vitre du haut, à reflets, est exclue comme le disent les notes de la série), rayon < 0,6 | 4 741 (7 %) | 0,93 |

Les identifiants « soir » et « jour » ne sont que des étiquettes de séance : la lumière n'a pas été mesurée (EXIF : 1/10 s contre 1/20 s au même diaphragme et au même ISO). Les deux bibliothèques sont le même lieu : elles sont tenues à part **ensemble** (un même pli) pour qu'aucun livre ne fuie de l'entraînement vers la tenue. Les blocs ne sont pas équilibrés (guitares + portrait = 52 % des blocs) : le critère d'acceptation pèse chaque scène autant, mais les équations normales du pas de Gauss-Newton pèsent par bloc ; je n'ai pas essayé d'autre pondération. Portrait et fenêtre ont une chroma médiane basse (4,9 et 4,5 contre 16 pour le pédalier).

**Exclues** :
- `2026-10-seance-complement` (lot 5) : même bibliothèque, même séance que le lot 4 (mêmes réglages EXIF) ; pas de vue BASE STANDARD, la scène est la même.
- `2026-10-seance-pedalier` (lot 3) : même pédalier que le test v1 (déjà compté).
- `2026-10-test-v2` (5600/…) : même bibliothèque et même séance que `test-v2-bibliotheque` (cadrage un peu différent), déjà compté une fois.
- `portra-paires/` : d'après son LISEZMOI, les JPEG sont des exports Adobe Camera Raw (look du preset acheté), pas des JPEG du boîtier : pas de gain radial possible « comme avant », et ce sont des photos de visage de la même série.
- Le lot 1 existe (`seance-scene-interieur`) : retenu (guitares).

Choix de la vue de l'extérieur : la balance est celle du NEF (WB Auto, daylight), **sans la ramener à 5 600 K** : NX développe avec la balance du NEF, la cible doit donc partir de la même scène (la convention du test v1, ramener à 5 600 K, ne s'applique pas ici). La fenêtre (50 mm) n'a pas de modèle de vignetage dans l'analyse : rayon limité à 0,6 pour que le gain radial absorbe ce qui reste.

## 2. Procédure (différences avec la passe 2)
Même chaîne de mesure que la passe 2 (rendu NX en NP2, blocs, gain radial par NEF, ΔE2000 contre la cible, `d750_ajuster_nx.Banc` réutilisé), même critère (médiane + ½ p90, moyenne sur les scènes d'entraînement), mêmes poids, mêmes 9 nœuds de courbe, saturation et teinte au quart de point. Départ = la recette **chargée aujourd'hui** (les fichiers `d750-v1/usb/…json` ; leur bloc est identique octet pour octet à l'`apres_20n_0.bin` de l'historique pour C-2, 3, 4, 5, 6, 8, 9 : vérifié).

Pour tenir ~900 rendus (763 utilisés), la procédure est **plus légère que celle de la passe 2** :
- **un seul pas de Gauss-Newton** (recherche de pas 1 / 0,6 / 0,3 ; le pas 1 a été retenu dans tous les plis et dans tous les ajustements complets), au lieu de deux itérations ;
- **pas de criblage de base ni de filtre** (Standard et « aucun » restaient premiers aux passes 1 et 2) ;
- le jacobien (différences finies sur de vrais rendus NX) est calculé **une seule fois** au point de départ sur les 7 scènes ; ses lignes d'une scène ne dépendent pas du pli, chaque pli en prend les scènes d'entraînement. Cela fait 112 rendus par recette en couleur (98 en N&B), au lieu de ~400.

Ce qui est validé est cette procédure ; la recette candidate est la même procédure sur les 7 scènes.

## 3. Règle de décision (écrite avant les mesures, `d750_valider_nx.py`, constantes `SEUIL_MEDIANE`, `SEUIL_P90`, `PERTES_MAX`)
Trois plis, chaque scène tenue à part exactement une fois : {guitares, exterieur}, {portrait, pedalier}, {bibliotheque-soir, bibliotheque-jour, fenetre}. Médiane et p90 d'un pli = moyenne, sur ses scènes tenues à part, de la médiane et du p90 de chaque scène. On **garde la recette ajustée sur toutes les scènes** seulement si :
1. la médiane baisse d'au moins **0,2 ΔE en moyenne des plis** ;
2. le p90 ne monte pas de plus de **0,3 en moyenne des plis** ;
3. la médiane ne monte (perte) que dans **un pli au plus**.
Sinon, **aucun changement dans le boîtier**. Interprétation figée avant les mesures : « p90 en moyenne des plis » ; en lecture plus stricte (un seul pli dont le p90 monte de plus de 0,3), le verdict ne change pour aucune des quatre recettes gardées (la hausse maximale d'un pli y est négative) ; la lecture stricte exclurait HP5+ (pli 2 : +0,34), déjà refusée.

## 4. Résultats (ΔE2000 contre la cible ; scènes tenues à part)

| Recette | Actuelle : médiane (p90) | Ajustée : médiane (p90) | Gain de médiane (moy. des plis) | Hausse de p90 (moy. des plis) | Plis en perte | Décision |
|---|---|---|---|---|---|---|
| Classic Chrome (C-2) | 2,35 (4,17) | **1,93 (3,80)** | 0,43 | −0,38 | 0 | **garder la nouvelle** |
| Classic Neg (C-3) | 4,95 (7,17) | **4,73 (6,52)** | 0,22 | −0,64 | 0 | **garder la nouvelle** (juste) |
| Positive (C-4) | 3,38 (5,78) | **2,54 (5,35)** | 0,83 | −0,44 | 0 | **garder la nouvelle** |
| Portra 400 (C-5) | 3,78 (6,03) | **2,85 (4,70)** | 0,97 | −1,28 | 0 | **garder la nouvelle** |
| Hasselblad (C-6) | 3,08 (5,17) | 2,92 (5,15) | 0,15 | −0,01 | 1 | recette actuelle (gain < 0,2) |
| HP5+ (C-8) | 2,28 (6,26) | 2,12 (5,92) | 0,13 | −0,31 | 1 | recette actuelle (gain < 0,2) |
| FP4+ (C-9) | 1,58 (6,93) | 1,58 (6,82) | −0,00 | −0,09 | 2 | recette actuelle (deux plis en perte) |

(Médiane et p90 = moyenne des 7 scènes, chacune tenue à part une fois, ajustement du pli sans elle.)

Par pli (moyenne des scènes tenues à part du pli : médiane actuelle → ajustée ; entre parenthèses le p90 ; puis gain de médiane et variation du p90) :

| Recette | Pli 1 (guitares, extérieur) | Pli 2 (portrait, pédalier) | Pli 3 (2 bibliothèques, fenêtre) |
|---|---|---|---|
| Classic Chrome | 2,75 → 2,40 (p90 4,80 → 4,30) ; Δ 0,35, p90 −0,49 | 1,63 → 1,10 (p90 2,77 → 2,49) ; Δ 0,53, p90 −0,28 | 2,56 → 2,16 (p90 4,68 → 4,33) ; Δ 0,40, p90 −0,35 |
| Classic Neg | 4,60 → 4,43 (p90 5,97 → 5,76) ; Δ 0,18, p90 −0,21 | 4,76 → 4,53 (p90 8,40 → 7,43) ; Δ 0,23, p90 −0,97 | 5,32 → 5,07 (p90 7,15 → 6,41) ; Δ 0,25, p90 −0,74 |
| Positive | 4,02 → 3,58 (p90 6,90 → 6,72) ; Δ 0,44, p90 −0,19 | 3,35 → 2,17 (p90 4,59 → 3,87) ; Δ 1,17, p90 −0,72 | 2,98 → 2,08 (p90 5,83 → 5,42) ; Δ 0,90, p90 −0,41 |
| Hasselblad | 3,80 → 3,82 (p90 6,39 → 6,53) ; Δ -0,02, p90 +0,14 | 2,02 → 1,70 (p90 4,32 → 4,20) ; Δ 0,32, p90 −0,12 | 3,30 → 3,14 (p90 4,92 → 4,87) ; Δ 0,15, p90 −0,04 |
| Portra 400 | 3,68 → 2,60 (p90 5,04 → 3,75) ; Δ 1,08, p90 −1,29 | 3,77 → 2,67 (p90 5,78 → 4,83) ; Δ 1,10, p90 −0,94 | 3,85 → 3,13 (p90 6,84 → 5,25) ; Δ 0,72, p90 −1,59 |
| HP5+ | 1,58 → 1,58 (p90 3,42 → 2,72) ; Δ -0,01, p90 −0,70 | 2,93 → 2,82 (p90 8,96 → 9,30) ; Δ 0,11, p90 +0,34 | 2,31 → 2,02 (p90 6,36 → 5,79) ; Δ 0,29, p90 −0,57 |
| FP4+ | 1,56 → 1,30 (p90 4,28 → 4,36) ; Δ 0,27, p90 +0,08 | 1,48 → 1,74 (p90 9,45 → 9,31) ; Δ -0,26, p90 −0,14 | 1,66 → 1,67 (p90 7,02 → 6,80) ; Δ -0,01, p90 −0,22 |

Médiane par scène tenue à part, actuelle → ajustée :

| Scène | Classic Chrome | Classic Neg | Positive | Hasselblad | Portra 400 | HP5+ | FP4+ |
|---|---|---|---|---|---|---|---|
| guitares | 2,47 → 2,13 | 4,81 → 5,20 | 2,75 → 2,17 | 1,42 → 1,46 | 4,34 → 2,93 | 1,68 → 1,77 | 2,49 → 2,16 |
| portrait | 1,25 → 0,84 | 5,40 → 5,06 | 3,31 → 2,07 | 2,70 → 2,27 | 4,65 → 3,69 | 3,39 → 3,43 | 0,72 → 0,79 |
| bibliotheque-soir | 1,51 → 1,30 | 4,81 → 4,88 | 2,78 → 1,76 | 2,79 → 2,71 | 3,22 → 3,03 | 3,29 → 3,29 | 2,94 → 3,38 |
| pedalier | 2,00 → 1,36 | 4,12 → 4,00 | 3,39 → 2,28 | 1,34 → 1,14 | 2,89 → 1,65 | 2,47 → 2,22 | 2,23 → 2,69 |
| bibliotheque-jour | 2,21 → 1,78 | 5,15 → 4,96 | 3,02 → 1,98 | 2,91 → 2,55 | 4,23 → 3,26 | 2,91 → 2,24 | 1,05 → 1,19 |
| exterieur | 3,03 → 2,66 | 4,39 → 3,65 | 5,28 → 4,99 | 6,17 → 6,17 | 3,02 → 2,26 | 1,47 → 1,40 | 0,63 → 0,43 |
| fenetre | 3,98 → 3,41 | 6,00 → 5,37 | 3,13 → 2,52 | 4,19 → 4,17 | 4,11 → 3,10 | 0,72 → 0,52 | 1,00 → 0,44 |

Lecture : Classic Chrome, Positive et Portra gagnent dans les trois plis et sur les 7 scènes ; le gain du Classic Neg est faible (5 scènes sur 7 baissent, deux montent : guitares +0,39 et bibliothèque du soir +0,07) mais de même signe dans les trois plis, avec un p90 qui baisse nettement : à 0,02 du seuil, c'est le cas limite de la série, il passe la règle telle qu'écrite. Hasselblad : le gain vient du portrait et du pédalier ; sur la scène de l'extérieur (6,17) rien ne bouge. HP5+ et FP4+ (N&B, courbe seule) : aucun gain stable, FP4+ perd dans deux plis, comme à la passe 2 (surajustement). **Ajustées sur les 7 scènes (en échantillon, ce n'est pas une validation)**, la médiane moyenne baisse de : Classic Chrome 2,35 → 1,85 (0,50 ; 0,43 en tenue à part), Classic Neg 4,95 → 4,52 (0,43 ; 0,22), Positive 3,38 → 2,39 (0,99 ; 0,83), Portra 3,78 → 2,67 (1,11 ; 0,97), Hasselblad 3,07 → 2,77 (0,30 ; 0,15), HP5+ 2,28 → 1,64 (0,63 ; 0,13), FP4+ 1,58 → 1,38 (0,20 ; 0,00). L'écart entre les deux gains est faible pour les couleurs qui passent (Positive, Portra, Classic Chrome) et fort pour HP5+ et Classic Neg : c'est le surajustement que la validation croisée devait attraper.

## 5. Ce qui change pour les quatre recettes retenues (par rapport à la v1 chargée)
Base Standard, netteté, clarté inchangées. Saturation, teinte (quarts de point), courbe (9 nœuds, remise sur les 20 points d'ancrage).

| C- | Saturation | Teinte | Courbe (écart à la v1, codes 0 à 255) |
|---|---|---|---|
| 2 Classic Chrome | −1 → −1,25 | −2 → −3 (limite du boîtier) | max 3,4, moyenne 1,4 |
| 3 Classic Neg | 0 → −1 | 0 → −0,75 | max 7,4, moyenne 2,6 |
| 4 Positive | +2 → +1,75 | −2 → −3 (limite du boîtier) | max 8,1, moyenne 3,0 |
| 5 Portra 400 | +3 → +2,75 | +2 → +0,25 | max 8,7, moyenne 3,0 |

Le changement le plus visible attendu : la teinte de Portra (1,75 point de moins). Les écrits (`d750-v3/usb/<recette>-v3.json` et `.bin`) ont le nom affiché d'aujourd'hui sans version (CLASSIC CHROME, CLASSIC NEG, POSITIVE, PORTRA 400), 610 octets (`picture_control.py bloc` : exit 0). **Contrôles faits** : le NP2 de chaque JSON est octet pour octet celui que NX a rendu pendant l'ajustement (`np2_recette(json) == en_np2(candidate)`), et le bloc relu (`lire_bloc_ptp`) porte le même nom, la même base, les mêmes saturation, teinte, accentuation, clarté et la même table.

## 6. Limites (à lire)
1. **Mesuré dans NX, pas sur le boîtier.** Les cibles sont celles de la passe 2 ; les écarts sont NX contre cible. NX reproduit le boîtier à 0,9 à 1,4 ΔE en médiane en couleur (plancher présent aussi avec NX « tel quel », cause non cherchée) et à 0,15 à 0,33 en N&B (passe 2). Un gain de 0,4 à 1,0 est donc **vraisemblable** pour le boîtier, pas démontré ; le sens est le seul point assuré par construction.
2. NX lit les 20 points d'ancrage de la courbe, pas la table de 257 valeurs (passe 2) ; le boîtier, lui, lit la table : l'écart entre les deux est de 0,3 à 0,7 code en moyenne (v1) et s'ajoute à l'écart à la v1 du tableau §5.
3. Sept scènes, dont deux (guitares, portrait) font 52 % des blocs ; trois plis seulement ; un seul pas de Gauss-Newton. Les écarts de médiane sous 0,2 à 0,3 ne sont pas à interpréter. Classic Neg est à 0,02 du seuil.
4. Deux teintes à la limite du boîtier (−3 : Classic Chrome, Positive) : le moteur en voudrait peut-être plus, que le boîtier ne permet pas.
5. Extérieur : cible à la balance du NEF (WB Auto), vignetage `f56` du modèle au 28 mm f/8 (l'analyse n'a que f/1,8 et f/5,6). Fenêtre : 50 mm, aucun modèle de vignetage, rayon < 0,6.
6. Les cibles restent des modèles (LUT Fuji, rendus mesurés, preset acheté, fiches Ilford) : on réduit l'écart à un modèle, pas à un film. Kodachrome (cible absente du disque) et Tri-X (WB 10 000 K) hors champ.
7. Cible Portra « esprit Portra » (`D750_LOOKS`), pas un Portra réel.
8. Aucune vérification sur le boîtier : après chargement, une photo de la scène du test v1 mesurée par `mesures_reelles.py` dira ce que valent ces chiffres.

## 7. Charger dans le boîtier : commandes (NON lancées)
Préconditions (`recherche/d750-picture-control-usb.md` §6) : boîtier allumé en P, S, A ou M, hors prise de vue, câble USB, Photos et Transfert d'images fermés, U1 et U2 ne doivent pas utiliser l'emplacement visé (refus 0x200F sinon). **U2 est prévu sur C-5** (README v1, état actuel non relu) : pour Portra, décaler U2 avant et le remettre après. Depuis `Photographie/logiciels/d40-firmware/` ; chaque emplacement : relecture du bloc, simulation (n'écrit rien), écriture avec `--remplacer` (l'emplacement est occupé ; l'ancien contenu est sauvé et relu), retour en arrière par le bloc écrit en octobre.

```
# C-2 CLASSIC CHROME
python3 outils/picture_control.py bloc recettes/d750-v3/usb/classic-chrome-v3.json /tmp/d750-C-2.bin
swift outils/d750_ecrire.swift ecrire recettes/d750-v3/usb/classic-chrome-v3.bin C-2
swift outils/d750_ecrire.swift ecrire recettes/d750-v3/usb/classic-chrome-v3.bin C-2 --ecrire --remplacer
# retour : swift outils/d750_ecrire.swift ecrire sondes/d750/usb/ecriture-2026-10.19/apres_202_0.bin C-2 --ecrire --remplacer

# C-3 CLASSIC NEG
python3 outils/picture_control.py bloc recettes/d750-v3/usb/classic-neg-v3.json /tmp/d750-C-3.bin
swift outils/d750_ecrire.swift ecrire recettes/d750-v3/usb/classic-neg-v3.bin C-3
swift outils/d750_ecrire.swift ecrire recettes/d750-v3/usb/classic-neg-v3.bin C-3 --ecrire --remplacer
# retour : swift outils/d750_ecrire.swift ecrire sondes/d750/usb/ecriture-2026-10.16/apres_203_0.bin C-3 --ecrire --remplacer

# C-4 POSITIVE
python3 outils/picture_control.py bloc recettes/d750-v3/usb/positive-v3.json /tmp/d750-C-4.bin
swift outils/d750_ecrire.swift ecrire recettes/d750-v3/usb/positive-v3.bin C-4
swift outils/d750_ecrire.swift ecrire recettes/d750-v3/usb/positive-v3.bin C-4 --ecrire --remplacer
# retour : swift outils/d750_ecrire.swift ecrire sondes/d750/usb/ecriture-2026-10.16/apres_204_0.bin C-4 --ecrire --remplacer

# C-5 PORTRA 400
python3 outils/picture_control.py bloc recettes/d750-v3/usb/portra-400-v3.json /tmp/d750-C-5.bin
swift outils/d750_ecrire.swift ecrire recettes/d750-v3/usb/portra-400-v3.bin C-5
swift outils/d750_ecrire.swift ecrire recettes/d750-v3/usb/portra-400-v3.bin C-5 --ecrire --remplacer
# retour : swift outils/d750_ecrire.swift ecrire sondes/d750/usb/ecriture-2026-10.17/apres_205_0.bin C-5 --ecrire --remplacer
```
Pas de commande pour C-6, C-8, C-9 (inchangés), ni C-1, C-7. Après écriture : `python3 outils/d750_historique.py` refait `HISTORIQUE.md` depuis les journaux.

## 8. Budget, contrôles, nettoyage
- **763 rendus SaveProcess** (7 « tel quel » pour les gains radiaux, 112 × 5 couleur + 98 × 2 N&B ; plus 2 petits rendus du self-test de `d750_ajuster_nx.py`), un seul à la fois, `nice -n 10`, ~18 min de rendu. Moins que les 900 prévus ; le pas 0,3 aurait été coupé au-delà de 760 rendus dans le processus (non atteint, aucun pli n'a dépassé le pas 1).
- Self-tests : `d750_valider_nx.py --self-test` OK (plis, règle, bloc des recettes v3), `d750_ajuster_nx.py --self-test` OK (non modifié), `picture_control.py --self-test` OK. Aucune correction de bug dans `nx_rendu.py` ni `picture_control.py`.
- Temporaires dans `$NX_TRAVAIL/passe3-nx/` (par défaut le dossier temporaire du système : blocs, cache des rendus, `valide-*.json`), mis à la corbeille à la fin.
- Reproduire : `python3 outils/d750_valider_nx.py scenes` puis `valider tout` puis `ecrire`, sous `nice -n 10`.
