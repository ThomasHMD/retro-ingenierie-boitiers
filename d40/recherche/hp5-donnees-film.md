# HP5 Plus (et Tri-X 400) : données du film, grain, et ce que le D750 peut imiter par réglage

Recherche d’octobre 2026 pour le D750 « de production » de Thomas (firmware intact). Prolonge perspectives-d200-xt4-d750.md §3.2 et §3.3, qui n'est pas modifié ici.

Conventions de statut :
- **vérifié** : lu dans une source citée en fin de section ;
- **hypothèse** : déduction, lecture indirecte ou valeur non confirmée ;
- **calcul** : chiffre produit pour ce rapport à partir de sources vérifiées et d'hypothèses nommées à côté ; c'est une hypothèse chiffrée, pas une mesure.

Les calculs ont été faits dans le dossier jetable de la session (scripts `filtre_bleu.py`, `filtre_pre.py`, `grain_vs_bruit.py`, non conservés) ; la méthode est décrite à chaque fois pour pouvoir les refaire.

## Verdicts par aspect

| Aspect | Atteignable par réglage, et comment | Écart chiffré | Hors d'atteinte sans firmware | Statut |
|---|---|---|---|---|
| Sensibilité spectrale, cible Tri-X « preset acheté » | Monochrome sans filtre, balance des blancs (WB) fixe 8 000 à 10 000 K (§3.3) | ΔL\* médian 1,3 (§3.3) | rien d'important | vérifié (calcul du §3.3) |
| Sensibilité spectrale, cible fiche Kodak Tri-X | même réglage (WB 10 000 K) ; un filtre 80A avec blanc mesuré à travers (PRE) n'apporte presque rien de plus | 5,3 (§3.3) ; 80A + PRE : 4,9 à 5,1 (−1,8 IL) | le reste de l'écart | calcul (capteurs Nikon de substitution) |
| Sensibilité spectrale, cible fiche Ilford HP5 | réglage seul : WB 10 000 K, 0,13 de bleu (§3.3). **Nouveau** : filtre bleu de conversion + blanc PRE mesuré à travers | réglage seul : 7,9 ; 80A + PRE : 7,2 à 7,4 (−1,8 IL) ; 80A + 80B + PRE : 5,3 à 5,7 (−3,3 IL) ; filtre sans PRE : aucun gain | le bleu de la fiche (0,67) | calcul, à vérifier sur le boîtier |
| Courbe film puis tirage | courbe perso 20 points sur base Monochrome, D-Lighting actif désactivé, contraste et luminosité à 0 | D40 : ΔE médian 1,0 à 1,6 avec courbe ajustée ; D750 : 1,9 avec une courbe commune (§3.2) | effets locaux du développement ; JPEG 8 bits | vérifié (capacité) ; fidélité : hypothèse |
| Grain : quantité | ISO élevé, réduction du bruit ISO désactivée | à Hi 2 (ISO 51 200), bruit « visible » (basse fréquence) 1,9 à 2,6 fois plus faible que HP5 poussé à 1 600 ; égalité vers ISO 280 000 à 500 000 | la quantité, surtout à ISO modéré | calcul |
| Grain : répartition par tonalité | aucune | à grain égal au gris moyen, bruit 3,8 à 6,5 fois trop fort à −3 IL, 3 à 5 fois trop faible à +3 et +4 IL | tout | calcul (sur mesures publiées) |
| Grain : texture et distribution | partielle : taille L, réduction du bruit désactivée | amas du film 13 à 25 µm, soit 2 à 4 pixels du D750 ; asymétrie du film qui change de signe avec la densité, absente du bruit capteur | amas, asymétrie | vérifié (mesures) ; comparaison : hypothèse |
| Netteté, effets de bord | accentuation et clarté, à calibrer sur une mire | FTM Tri-X (D-76) de 110 à 115 % vers 5 à 10 cycles/mm | effet de bord qui suit la densité locale | vérifié (fiche) ; imitation : hypothèse |
| Halo | rien dans le boîtier | non chiffré par les fiches ; HP5 120 et plan ont un dos anti-halo | tout | vérifié (absences) |
| Vignetage | Contrôle du vignetage désactivé : reste celui de l'objectif | à mesurer | rien | vérifié (manuel) ; équivalence au film : hypothèse |

**Relecture d’octobre 2026 (session D750)** : sources contrôlées (dépôt grainifier et profil `hp5-plus-ei1600.json` : σ_D 0,048 au voile, conforme ; DOI de Zenodo, Zhang 2023, Lesné 2025 et Bartleson 1985 : résolus). Deux corrections :
- **U1 et U2** (vérifié par Thomas en octobre 2026) : U2 est le mode portrait RAW + JPEG de Thomas (il recevra le Portra), U1 son noir et blanc (il recevra le Tri-X v2). Le tableau du §5.6, qui mettait Tri-X en U1 et HP5 en U2, est corrigé : la HP5 n'a pas de mode U, donc pas de balance des blancs ni de blanc PRE qui lui soient propres, sauf à la mettre en U2 à la place du Tri-X.
- **Grain dans les ombres (§3.5)** : le calcul prend une pente du négatif constante. Or vers −3 IL, le négatif est dans son pied de courbe (D ≈ 0,3), où la pente baisse : rapporté à la scène, le grain du film y est plus fort que la colonne « Film » ne le dit. L'excès de bruit du D750 à −3 IL (3,8 à 6,5 fois) est donc surestimé ; le sens reste (trop dans les ombres, pas assez dans les clairs, où le négatif est en partie droite). Le contrôle par la RMS 17 de Tri-X passe par la loi de Selwyn jusqu'au pixel de 6 µm, plus petit que les amas de grain : il surestime le grain par pixel, d'où son « ISO 600 000 ». Les ISO équivalents sont un ordre de grandeur ; la série grain du mode d'emploi (`tutos/d750-profils-nb.html`, partie 6) les mesure.

**Décision de Thomas (octobre 2026)** : pas de filtre devant l'objectif, pas de grain par l'ISO, pas de ColorChecker. Les §5.1 (filtres), §5.3 (grain) et les séances A (filtres), C et F du §5.7 sont donc écartés ; la cible HP5 devient ses propres scans HP5 retouchés dans Lightroom.

**Ce qui compte le plus :**
1. **La fiche Ilford actuelle (novembre 2018) ne publie ni granularité, ni FTM, ni pouvoir résolvant, ni indice de contraste, et une seule courbe caractéristique (Ilfotec HC 1+31).** Les courbes par révélateur demandées n'existent pas chez Ilford ; seuls les temps de développement jusqu'à EI 3 200 sont publiés. Vérifié.
2. **Le grain du film n'est pas « maximal dans les tons bas du négatif »** : mesuré sur HP5 poussé à 1 600, l'écart type de densité monte du voile (0,048) à un plateau de 0,09 à 0,10 entre D 1,0 et 2,3. Ramené à l'exposition de la scène, il est presque constant d'une tonalité à l'autre, alors que le bruit photonique décroît comme la racine de l'exposition. Ce désaccord de forme ne se corrige par aucun réglage. Vérifié (mesures grainifier) ; comparaison : calcul.
3. **Même à Hi 2, le D750 a trop peu de grain « visible »** : par pixel il égale HP5@1600 scanné, mais le grain du film est corrélé sur 2 à 4 pixels, ce qui double son poids aux fréquences que l'œil voit. Calcul.
4. **Un filtre bleu sur l'objectif ne sert que si le blanc est mesuré à travers lui (PRE).** Avec une WB fixe, il n'ajoute presque rien. Avec un PRE, par rapport au meilleur réglage sans accessoire (WB 10 000 K, ΔL\* médian 7,9 au §3.3), un 80A (−1,8 IL) ne gagne qu'environ 0,5 point ; un 80A + 80B (−3,3 IL) environ 2,4 points (5,3 à 5,7). Seule piste nouvelle vers le bleu de HP5 sans firmware, coûteuse en lumière. Calcul (modèles un peu différents de ceux du §3.3 : ordre de grandeur), à vérifier sur le boîtier.
5. **La forme de la FTM Tri-X (au-dessus de 100 % à basse fréquence) est un effet de bord du révélateur**, imitable en partie par une accentuation de rayon moyen ; la clarté et l'accentuation de Nikon n'ont pas de rayon documenté, donc il faut mesurer (mire à bord incliné).

## 1. Données fabricant

### 1.1 HP5 Plus : fiche Ilford en vigueur

La fiche en ligne est datée de **novembre 2018** (6 pages, PDF créé le 28/11/2018) ; c'est toujours celle que sert le lien officiel (captures de la Wayback Machine de février et d'août 2026, lue dans celle d’août 2026). Le site d'Ilford bloque les téléchargements automatisés, d'où la lecture par l'archive. Vérifié. Le projet utilisait la version d'avril 2010 (`films_nb.py`) : **le spectrogramme et la courbe caractéristique sont les mêmes dans les deux versions** (vérifié à l'œil, graphiques superposables), donc la numérisation de `films_nb.py` reste valable.

| Donnée | Contenu de la fiche 2018 | Statut |
|---|---|---|
| Sensibilité spectrale | « Wedge spectrogram » au tungstène 2 850 K, sans valeurs numériques, sans courbe à densité fixe | vérifié |
| Courbe caractéristique | **une seule** : Ilfotec HC 1+31, 6 min 30 à 20 °C, agitation intermittente, dite représentative du 35 mm, du 120 et du plan | vérifié |
| Courbes ID-11, DD-X, Microphen, Perceptol | **absentes** | vérifié (absence) |
| Pente moyenne de cette courbe | 0,59 entre voile + 0,1 et 1,5 log plus loin ; 0,64 entre voile + 0,2 et 2,0 log plus loin ; voile 0,165 ; pas d'épaule jusqu'à D 2,1, soit environ 3 log (10 IL) de partie utile | calcul (sur la numérisation `films_nb.py`) |
| Indice de contraste, G-barre | non publiés | vérifié (absence) |
| Sensibilité | ISO 400/27° ; la plage d'EI conseillée vient d'une « évaluation pratique », pas du point de pied de courbe de la norme ISO. La version 2010 disait au contraire que l'ISO était mesuré en ID-11 | vérifié |
| Poussé | bonne qualité annoncée jusqu'à EI 3 200 en DD-X, Ilfotec HC, Microphen, Ilfotec RT Rapid | vérifié |
| Réciprocité | aucune correction de 1/10 000 à ½ s ; au-delà, temps corrigé = temps mesuré puissance 1,31 (10 s → 20 s ; 30 s → 86 s ; 60 s → 213 s) | vérifié (formule) ; exemples : calcul |
| Granularité, pouvoir résolvant, FTM | **absents** de la fiche 2018 et de celle de 2010 | vérifié (absence) |
| Support | 35 mm : acétate 0,125 mm, la fiche ne parle pas d'anti-halo ; 120 : acétate 0,110 mm avec dos anti-halo qui s'éclaircit au développement ; plan : polyester 0,180 mm, idem | vérifié |

Temps de développement, cuve à spirale, 20 °C, en minutes, par EI (vérifié, fiche 2018 ; extrait) :

| Révélateur | Dilution | EI 400 | 800 | 1 600 | 3 200 |
|---|---|---|---|---|---|
| Ilfotec DD-X | 1+4 | 9 | 10 | 13 | 20 |
| ID-11 | stock | 7½ | 10½ | 14 | non donné |
| ID-11 | 1+1 | 13 | 16½ | non donné | non donné |
| Microphen | stock | 6½ | 8 | 11 | 16 |
| Ilfotec HC | 1+31 | 6½ | 9½ | 14 | non donné |
| Kodak D-76 | stock | 7½ | 9½ | 12½ | non donné |
| Kodak HC-110 | B | 5 | 7½ | 11 | non donné |
| Kodak Xtol | stock | 8 | 11 | 14 | 19 |
| Agfa Rodinal | 1+25 | 6 | 8 | non donné | non donné |
| Perceptol | stock, EI 250 | 13 | | | |

Choix conseillés par Ilford (vérifié) : meilleure qualité à EI 400 et 800, DD-X ou ID-11 stock ; à 1 600 et 3 200, DD-X ou Microphen stock ; grain le plus fin, DD-X ou Perceptol ; netteté maximale, Ilfosol 3 (1+9) ou ID-11 (1+3).

Granularité de HP5 : aucune valeur Ilford trouvée. Les notes du projet grainifier citent « HP5+ ≈ 10 à 12 » sans source primaire ; à ne pas utiliser (hypothèse invérifiable). La seule mesure chiffrée trouvée est celle de grainifier sur HP5 poussé à 1 600 (§3.2).

### 1.2 Tri-X 400 : fiche Kodak F-4017

Version en ligne : **octobre 2021** (révision 10-21, Kodak Alaris), sur kodakprofessional.com ; aucune version plus récente trouvée. Vérifié. Wikipedia indique que Tri-X est distribué directement par Eastman Kodak depuis janvier 2026 (lu dans un extrait de recherche) : la fiche pourrait changer. Hypothèse.

| Donnée | Contenu | Statut |
|---|---|---|
| Granularité RMS diffuse | **17** (« fine ») pour Tri-X 400, 16 pour Tri-X 320 ; HC-110 dilution B, 20 °C ; lue à une densité nette de 1,0, ouverture de 48 µm, grossissement ×12 | vérifié |
| Origine de ce 17 | la fiche de septembre 2002 précise : mesuré sur l'**ancienne** émulsion (Tri-X Pan), HC-110 B 7 min 30 jusqu'à un indice de contraste de 0,56, jugé valable pour la nouvelle ; FTM et sensibilité spectrale venaient du film cinéma Tri-X Pan 5063. La fiche 2021 reprend le chiffre sans cette mention | vérifié (2002) ; mêmes données en 2021 : hypothèse |
| FTM | D-76 grande cuve, densitométrie diffuse visuelle. Lue sur le graphique (±10 %) : environ 110 % à 2,5 c/mm, maximum 113 à 115 % vers 5 à 10 c/mm, 100 % vers 25 c/mm, 55 % à 50 c/mm, 25 % à 70 c/mm (fin de la courbe) | vérifié (graphique) ; valeurs : lecture |
| Pouvoir résolvant | seulement « High resolving power », sans chiffre (2021 comme 2002) | vérifié (absence) |
| Courbes caractéristiques | révélateur T-MAX, petite cuve, 6, 7, 9 et 11 min, 35 mm et 120 ; courbes d'indice de contraste par révélateur ; les temps visent un indice de contraste de **0,56** | vérifié |
| Pente de la courbe 6 min numérisée | 0,54 à 0,58, cohérente avec 0,56 | calcul (`films_nb.py`) |
| Sensibilité spectrale | log de la sensibilité pour D = 0,3 et D = 1,0 au-dessus du voile, exposition de 0,5 s (le projet utilise la courbe D = 1,0) | vérifié |
| Temps normaux (EI 400, petite cuve, 20 °C) | T-MAX 6 ; T-MAX RS 4½ ; HC-110 B 3¾ ; D-76 6¾ ; D-76 1:1 9¾ ; Xtol 7 ; Xtol 1:1 9 | vérifié |
| Poussé (petite cuve, 20 °C), EI 1 600 / 3 200 | T-MAX 8¾ / non recommandé (8¼ à 24 °C) ; T-MAX RS 7¾ / 9½ ; HC-110 B 6 / non donné ; D-76 9½ / 11 ; D-76 1:1 13¼ / 16 ; Xtol 9¾ / 11½ ; Xtol 1:1 13¼ / 15½ | vérifié |
| Effet du poussé | sous-exposition d'1 IL possible en traitement normal ; poussé de 2 à 3 IL : plus de contraste et de grain, moins de détail dans les ombres (qualitatif, sans chiffre) | vérifié |
| Réciprocité | 1/100 000 s : +1 IL, développement +20 % ; 1/10 000 : +½ IL, +15 % ; 1/1 000 : rien, +10 % ; 1/100 à 1/10 : rien ; 1 s : +1 IL (ou 2 s), −10 % ; 10 s : +2 IL (50 s), −20 % ; 100 s : +3 IL (1 200 s), −30 % | vérifié |
| Facteurs de filtre (lumière du jour / tungstène) | n° 8 jaune 2 / 1,5 ; n° 11 vert-jaune 4 / 3 ; n° 15 jaune foncé 2,5 / 1,5 ; n° 25 rouge 8 / 5 ; n° 47 bleu 6 / 12 ; n° 58 vert 6 / 6 ; polariseur 2,5 | vérifié |

Les facteurs de filtre sont une mesure indirecte de la sensibilité spectrale, faisable sur le D750 avec les mêmes filtres (protocole §5.7).

### 1.3 Comparaison

| | HP5 Plus (Ilford, 2018) | Tri-X 400 (Kodak, 2021) |
|---|---|---|
| Sensibilité spectrale | spectrogramme au tungstène, sans chiffres | courbes chiffrées D = 0,3 et 1,0 |
| Mélange équivalent en sRGB linéaire (lumière du jour) | 0,10 à 0,12 / 0,21 à 0,24 / 0,67 | 0,17 à 0,18 / 0,30 à 0,31 / 0,52 |
| Courbe | 1 (Ilfotec HC 1+31), pente ≈ 0,59 à 0,64 | 4 temps en T-MAX, CI visé 0,56 |
| Granularité | non publiée | 17 (données de l'ancienne émulsion) |
| FTM | non publiée | publiée (D-76) |
| Pouvoir résolvant | non publié | non chiffré |
| Réciprocité | puissance 1,31 au-delà de ½ s | table de 1/100 000 à 100 s |
| Poussé | temps jusqu'à EI 3 200 | temps jusqu'à EI 3 200 |

Statut des mélanges : calcul (§3.3 du rapport précédent et recalcul de cette session, à 0,02 près).

### Sources de la section 1
- Ilford, *HP5 PLUS Technical Information*, novembre 2018. Lien officiel : https://www.ilfordphoto.com/amfile/file/download/file/1903/product/691/ (bloqué aux robots) ; lu via la copie Wayback d’août 2026 : https://web.archive.org/web/20260803233234/https://www.ilfordphoto.com/amfile/file/download/file/1903/product/691/?___store=ilford_brochure&___from_store=ilford_uk ; consulté en octobre 2026.
- Ilford, *HP5 Plus Technical Information*, avril 2010, copie https://mail.kennethleegallery.com/pdf/HP5Plus.pdf, consultée en octobre 2026.
- Kodak Alaris, *Kodak Professional Tri-X 320 and 400 Films*, publication F-4017, octobre 2021, https://kodakprofessional.com/sites/default/files/wysiwyg/film/f4017_trix_320400.pdf, consultée en octobre 2026.
- Eastman Kodak Company, *Kodak Professional Tri-X 320 and 400 Films*, publication F-4017, septembre 2002, https://125px.com/docs/unsorted/kodak/f4017.pdf, consultée en octobre 2026.
- Wikipedia, *Kodak Tri-X*, https://en.wikipedia.org/wiki/Kodak_Tri-X (distribution depuis janvier 2026 ; lu dans un extrait de recherche, page non ouverte).
- Projet : `outils/films_nb.py` (numérisation des courbes HP5 et Tri-X, octobre 2026).

## 2. Bases de données de mires et jeux de données

Recherche : OpenAlex, Crossref, GitHub, Zenodo, recherche web. **Aucun jeu public de mires (ColorChecker, coin de gris, mire de résolution) photographiées sur HP5 ou Tri-X avec des scans linéaires téléchargeables n'a été trouvé.** C'est un « pas trouvé », pas un « n'existe pas ». Vérifié (pour les recherches faites).

| Ressource | Contenu | Licence | Utilisable ? |
|---|---|---|---|
| **grainifier, profils et jeu de données** (P. Fyhr, 2026) | statistiques de grain mesurées sur scans RAW linéaires (Nikon Coolscan V, 4 000 dpi, 6,35 µm par pixel) : HP5 Plus à EI 1 600 (494 vues, 13 films ; référence en un passage : 114 vues) et Kodak Double-X ; σ de densité par tranche de densité, spectre de bruit 2-D, autocorrélation, asymétrie. Jeu de données Zenodo : 728 vues, statistiques par carreau, sans image | logiciel MIT ; données CC BY 4.0 | **oui, pour le grain de HP5 poussé** (pas à EI 400, pas Tri-X pour l'instant). Seule cible quantitative de grain HP5 trouvée. Vérifié (README, notes, profil JSON) |
| grainifier, logiciel | mesure les mêmes statistiques sur des scans RAW linéaires de l'utilisateur | MIT | **oui** pour profiler un film de référence tourné par Thomas (§5.7). Vérifié |
| 35mmc, « rainbow test » (Sroyon, 2023) | bandes de couleur affichées sur un écran, photographiées sur HP5 et d'autres films ; sur HP5 le jaune sort le plus clair et le bleu plus clair que le vert | article ; pas de fichiers bruts | qualitatif seulement ; test facile à refaire sur le D750. Vérifié |
| spektrafilm (ex agx-emulsion, A. Volpato) | modèle physique négatif + tirage, courbes de fiches numérisées ; profils de films **couleur** seulement (liste du dépôt en juillet 2026 : aucun N&B) | GPL-3.0 | méthode de référence, pas de données N&B. Vérifié |
| camspec (Jiang et al., 2013) | sensibilités spectrales de 28 appareils, dont Nikon D3X, D3, D700, D300s, D5100, D200, D40, D50, D80, D90 ; **pas de D750** | usage de recherche | sert ici de substitut au D750 (calculs §5.1). Vérifié (fichier) |
| FilmGrainStyle740k (InterDigital, Ameur et al., 2023) | paires image sans grain / avec grain pour l'apprentissage | publié pour la communauté (résumé) ; non commercial et grain **synthétique** d'après les notes de grainifier | non (pas du vrai film). Vérifié (résumé) ; licence et nature : hypothèse |
| Code de Newson et al. | rendu de grain par modèle booléen | GPLv3 (d'après les notes de grainifier) | modèle, pas données. Hypothèse (licence non relue) |
| ProMist-5K (2026) | paires d'images avec et sans filtre de diffusion Pro-Mist | dataset annoncé sur Kaggle | hors sujet film ; utile seulement pour un effet de halo par filtre. Vérifié (titre, sujet) |
| Film-GAN (Gong et al., 2023, cité par grainifier) | transfert de style numérique → film, dont HP5 | fermé | non. Hypothèse (non retrouvé) |
| Fiches Kodak et Ilford | courbes en graphiques | droits des fabricants | déjà numérisées dans `films_nb.py`. Vérifié |
| Paires du preset acheté de Thomas (projet) | RAW du D750 + exports du preset Tri-X | privées | utilisables, mais ce sont des **émulations**, pas du film. Vérifié (§3.2) |

Jeux académiques de paires numérique / film : aucun trouvé pour le noir et blanc ; ceux trouvés traitent du grain synthétique (InterDigital) ou d'autres effets (ProMist-5K). Vérifié (recherches faites).

### Sources de la section 2
- Fyhr P. (2026). *grainifier: real film grain measured from scans, applied to digital images*, v0.1.0. Zenodo, DOI 10.5281/zenodo.22171276 (concept 10.5281/zenodo.22171275). Dépôt https://github.com/grainifier/grainifier (README.md, docs/research-notes.md d’août 2026, profil `grainifier/profiles/hp5-plus-ei1600.json`), consulté en octobre 2026. Jeu de données : DOI 10.5281/zenodo.22170495 (d'après le README, non téléchargé).
- Sroyon (2023). *Spectral Sensitivity of B&W Film: A Deep Dive into Orthochromatic, Panchromatic and All the Rest*. 35mmc, 02/05/2023, https://www.35mmc.com/?p=48886, consulté en octobre 2026.
- Volpato A. *spektrafilm* (ex agx-emulsion), https://github.com/andreavolpato/spektrafilm, GPL-3.0, arborescence lue en octobre 2026.
- Jiang J., Liu D., Gu J., Süsstrunk S. (2013). *What is the space of spectral sensitivity functions for digital color cameras?* IEEE Workshop on Applications of Computer Vision (WACV). Référence reprise de `outils/matrices_spectrales.py` ; fichier `camspec.txt` d'une session précédente.
- Ameur Z., Demarty C.-H., Le Meur O., Ménard D., François E. (2023). Style-based film grain analysis and synthesis. *Proceedings of the 14th ACM Multimedia Systems Conference*, 229-238. DOI 10.1145/3587819.3590992.
- *ProMist-5K: A Comprehensive Dataset for Digital Emulation of Cinematic Pro-Mist Filter Effects* (2026). arXiv 2601.19295 ; ICASSP 2026, DOI 10.1109/ICASSP55912.2026.11460866.

## 3. Grain

### 3.1 Normes et mesures

| Mesure | Ce qu'elle dit | Statut |
|---|---|---|
| **ISO 10505:2009**, granularité RMS des films | écart type de densité dû aux seuls grains développés ; films à tons continus N&B et couleur sur support transparent ; grossissements de vision 5× à 12× ; **exclut l'estimation du spectre de Wiener** ; confirmée en 2025 | vérifié (page ISO) |
| Convention Kodak | densité nette 1,0, ouverture circulaire de 48 µm, ×12, densitométrie diffuse ; chiffre ×1 000 (17 = σ_D de 0,017) | vérifié (F-4017) ; facteur 1 000 : notes de grainifier |
| Loi de Selwyn (1935) | σ_D × racine de l'aire de l'ouverture ≈ constante, tant que l'ouverture dépasse la taille des amas : c'est ce qui permet de comparer des mesures faites à des pas différents | vérifié (Haugh 1963 en traite ; texte de Selwyn non relu) |
| Spectre de Wiener (NPS) | répartition de la variance par fréquence spatiale ; Tyrrell et al. (1993) en tirent la granularité du négatif, puis celle du tirage par l'équation de Doerner | vérifié (résumé) |
| Granularité → granulation perçue | Jones et Higgins (série JOSA 1947-1951) ; Bartleson (1985) : la granulation perçue varie comme le carré de la granularité visuelle, d'où une échelle en « bits » (×2 de granularité = 2 unités) | vérifié (résumés) |
| Print Grain Index (Kodak) | échelle perceptive sur tirage par agrandisseur diffus : 25 = seuil de visibilité, 4 unités = plus petite différence perçue par 90 % des observateurs, vision à 14 pouces ; pas comparable à la RMS ; Kodak l'emploie pour la couleur, pas pour Tri-X | vérifié (fiche E-29) |
| Pouvoir résolvant | ISO 6328:2000, toujours en vigueur | vérifié (page ISO) |
| Côté numérique | ISO 15739:2023 : bruit en fonction du signal et dynamique des appareils numériques, mire de l'ISO 14524 | vérifié (page ISO) |

### 3.2 Données publiées sur le grain de HP5 et de Tri-X

| Film, traitement | Donnée | Statut |
|---|---|---|
| Tri-X 400, HC-110 B, EI 400 | RMS 17 (ancienne émulsion, voir §1.2) | vérifié |
| Tri-X 400 poussé à 1 600 ou 3 200 | « plus de grain », sans chiffre | vérifié |
| HP5 Plus, tous révélateurs | aucun chiffre Ilford ; seulement « grain le plus fin » en DD-X ou Perceptol | vérifié |
| **HP5 Plus à EI 1 600, labo, scan Coolscan 4 000 dpi** (grainifier) | σ de densité par pixel de 6,35 µm : 0,048 au voile (D 0,05) ; 0,082 à D 0,55 ; 0,089 à D 1,05 ; 0,095 à D 1,55 ; 0,097 à D 2,05 ; 0,091 à D 2,25 ; au-delà de D 2,4, bruit du scanner | vérifié (profil JSON) |
| idem, asymétrie | +0,93 au voile, ≈ 0 vers D 1,1, −0,34 vers D 2,3 : ce que prévoit un modèle booléen quand le taux de couverture passe 50 % ; aplatissement ≈ 2,9 à 3,0 (presque gaussien) | vérifié |
| idem, structure | autocorrélation au décalage 1 : 0,59 à 0,65 en x, 0,40 à 0,47 en y ; ≈ 0 au décalage 4 ; aire de corrélation 3,7 à 4,1 px², soit des amas de 13 à 25 µm ; anisotropie due en partie au scanner | vérifié |
| idem, granularité « à la Selwyn » | σ ramenée à l'ouverture de 48 µm : 0,025 à 0,029 pour D 1 à 2, soit une « RMS » de 25 à 28 (scanner à lumière dirigée : peut gonfler le chiffre, d'après l'auteur) | vérifié (notes) ; recalcul de cette session : 0,0256 (calcul) |
| idem, dispersion | d'un film à l'autre, σ à D 1,0 va de 0,067 à 0,124 (×1,8), en partie selon le développement, en partie selon la netteté du scan (passage unique contre trois passages) | vérifié |
| idem, sur le positif scanné | écart type du log10 de la luminance : 0,137 à L 0,04 ; 0,080 à 0,10 ; 0,040 à 0,22 ; 0,037 à 0,40 ; 0,026 à 0,60 ; 0,018 à 0,79 (positif VueScan / Negative Lab Pro) | vérifié |
| Deux films 400 N&B (tabulaire et classique) de EI 400 à 3 200 (Jacobson et al., 1989) | granularité, FTM, efficacité quantique, spectres de Wiener mesurés ; le classement subjectif suit mieux un critère signal sur bruit que la granularité | vérifié (résumé) ; chiffres : non accessibles |
| Révélateurs à effets de bord (Zengerle, 1983) | ils augmentent aussi la granularité ; pour Tri-X, le gain de netteté est mangé par le grain | vérifié (résumé) |

En L\* (calcul sur la ligne « positif scanné » ci-dessus, pente de L\* en fonction du log de Y) : 4,2 à Y 0,04 ; 3,3 à 0,10 ; 2,2 à 0,22 ; 2,4 à 0,40 ; 1,95 à 0,60 ; 1,5 à 0,79. Le grain du **scan** est le plus visible dans les ombres.

**Correction de la prémisse « grain maximal dans les tons moyens et bas du négatif »** :
- en densité du négatif, c'est l'inverse : faible au voile, plateau de D 1,0 à 2,3 (tons moyens et hautes lumières de la scène). Vérifié (grainifier). Dehancer décrit la même chose pour ses négatifs (grain fort dans les hautes lumières, où la densité est maximale). Vérifié ;
- ce que l'œil voit dépend du passage au positif. Scan à inversion linéaire puis gamma : maximum dans les ombres (ligne ci-dessus). Vérifié. Tirage sur papier : le pied et l'épaule du papier écrasent les deux extrémités, donc maximum attendu dans les tons moyens. Hypothèse (logique de la courbe du papier ; aucune mesure publiée trouvée).

### 3.3 Modèles de synthèse de grain

| Modèle | Principe | Intérêt ici | Statut |
|---|---|---|---|
| Newson, Delon, Galerne (2017) ; Newson et al. (IPOL, 2017) | modèle booléen non homogène : disques de Poisson dont la densité suit le niveau de gris, filtrés puis évalués par Monte-Carlo ; indépendant de la résolution | référence physique ; lent | vérifié (résumés) |
| Zhang, Wang, Tian, Pappas (2023) | moyenne et covariance du modèle booléen filtré en forme close, rendu en bruit gaussien corrélé un million de fois plus vite ; **formules pour estimer les paramètres sur des scans** | régime « grains individuels invisibles », celui des scans 4 000 dpi | vérifié (résumé) |
| Lesné, Gousseau, Ladjal, Newson (2025) | petit réseau entraîné sur des paires synthétiques du modèle de Newson | imite la texture | vérifié (métadonnées) ; détails : notes grainifier |
| Stephenson et Saunders (2007) | mesurer le spectre de bruit du film à plusieurs densités, puis filtrer un bruit blanc | approche par les données la plus simple | hypothèse (cité par grainifier, non relu) |
| Norkin et Birkbeck (2018), AV1 | modèle autorégressif, force du grain fonction de l'intensité, estimé sur image bruitée moins débruitée | estimation réutilisable | vérifié (résumé) |
| Ameur et al. (2023, IEEE TIP ; 2023, MMSys) | réseaux pour retirer, analyser, synthétiser le grain | grain d'entraînement synthétique | vérifié (résumés) |
| Geigel et Musgrave (1997) | simulation du tirage N&B : réponse en densité, sensibilité spectrale, résolution, granularité, à partir de données empiriques | ancêtre de la chaîne « film puis tirage » | vérifié (résumé) |
| **grainifier (2026)** | grain synthétisé **en densité du négatif** avec σ_D(D), asymétrie et spectre 2-D mesurés, puis ramené au positif par la pente de la courbe de scan ; contrôle en boucle fermée : σ à 1 %, asymétrie à 0,01 ; contre un vrai scan HP5@1600 : 10 à 25 % d'écart à toutes les tonalités | le plus proche de la cible HP5 ; logiciel, pas réglage | vérifié (README, notes) |
| Dehancer | grain procédural « physique », réglable par zones (ombres, tons moyens, hautes lumières), mode négatif (plus de grain dans les hautes lumières) ou positif ; équations non publiées | | vérifié (pages Dehancer) |

### 3.4 Taille du grain d'un 24×36 sur le capteur du D750

- Pas du D750 : 5,97 µm (6 016 pixels sur 35,9 mm, capteur de 35,9 × 24,0 mm d'après le manuel) ; fréquence de Nyquist 84 cycles/mm. Vérifié (manuel) ; pas et Nyquist : calcul.
- Amas de grain de HP5@1600 vus au scanner : 13 à 25 µm, soit **2,2 à 4,2 pixels du D750**. Calcul sur mesure vérifiée. Le D750 échantillonne donc assez fin pour porter un grain de 24×36 à l'échelle 1, comme le dit aussi grainifier (« une image de 24 Mpx reçoit le grain du 35 mm »). Vérifié (README) ; conséquence : calcul.
- L'autocorrélation mesurée (0,6 au décalage 1, 0,10 à 0,13 au décalage 2) équivaut à un bruit blanc flouté par une gaussienne d'écart type ≈ 0,7 pixel de 6,35 µm, soit ≈ 4,4 µm (flou du scanner compris). Calcul (le modèle prédit 0,13 au décalage 2, mesuré 0,10 à 0,17).
- Taille des cristaux d'argent de HP5 : non publiée, pas trouvée.
- Échelle de vision : l'ouverture Kodak de 48 µm vaut 8 pixels du D750 ; à ×12 (tirage proche de l'A3) elle couvre 0,58 mm sur le tirage. Calcul. Pour un 20×25 cm (×7 à ×8,5) vu à 30 cm, une minute d'arc (≈ 0,09 mm) correspond à 11 µm sur le négatif, environ 2 pixels. Hypothèse (acuité d'une minute d'arc, non relue ici). La granulation se voit donc comme une marbrure étalée sur plusieurs amas : c'est le **niveau basse fréquence** du spectre de bruit (σ × racine de l'aire, loi de Selwyn) qui compte, pas l'écart type par pixel. Hypothèse cohérente avec les conventions ISO 10505 et Kodak.

### 3.5 Le bruit du D750 à ISO élevé peut-il imiter le grain de HP5 ?

Méthode du calcul (`grain_vs_bruit.py`) : on ramène le grain du film et le bruit du capteur à la même grandeur, l'écart type du log10 de l'exposition de la scène. Une même courbe de tonalité multiplie ensuite les deux par la même pente, donc les rapports ci-dessous valent quel que soit le tirage final.
- Film : σ_D(D) de grainifier (HP5@1600, pixel de 6,35 µm) divisé par la pente du négatif γ ; γ entre 0,6 et 0,8 (hypothèse ; grainifier prend 0,8 par défaut, la fiche donne ≈ 0,6 à EI 400) ; gris moyen à D 0,9 (hypothèse, d'après le placement des tons de grainifier : L 0,24 ↔ D 0,99).
- D750 : bruit photonique plus bruit de lecture de 3 électrons (hypothèse) ; capacité de 81 593 électrons à ISO 100 (tableau Astropix d'après sensorgen, lu dans un extrait de recherche : hypothèse) ; gris moyen 3 IL sous la saturation du RAW (hypothèse). Une erreur de 20 % sur la capacité ne change les ISO équivalents que de 20 %, rien qui renverse les conclusions.

**Dépendance à la tonalité** (écart type relatif à celui du gris moyen, dans l'espace de la scène) :

| IL par rapport au gris | Film HP5@1600 | D750 ISO 6 400 | ISO 25 600 | ISO 51 200 (Hi 2) |
|---|---|---|---|---|
| −3 | 0,77 à 0,88 | 3,3 | 4,3 | 5,0 |
| −2 | 0,90 à 0,95 | 2,2 | 2,5 | 2,8 |
| −1 | 0,93 à 0,95 | 1,45 | 1,5 | 1,6 |
| 0 | 1 | 1 | 1 | 1 |
| +1 | 1,04 à 1,05 | 0,70 | 0,67 | 0,65 |
| +2 | 1,06 | 0,49 | 0,46 | 0,44 |
| +3 | 1,07 à 1,10 | 0,35 | 0,32 | 0,30 |
| +4 | 1,09 à 1,10 | 0,24 | 0,23 | 0,21 |

Calcul. Le grain du film est presque constant (légèrement croissant) avec l'exposition ; le bruit du capteur décroît comme la racine de l'exposition, plus vite encore dans les ombres à cause du bruit de lecture. **À grain égal au gris moyen, le D750 en a 3,8 à 6,5 fois trop à −3 IL et 3 à 5 fois trop peu à +3 et +4 IL.** Une courbe de tonalité ne corrige pas cela : elle change le bruit et les tons ensemble.

**Quantité** (gris moyen) :

| | σ du log de l'exposition par pixel | Rapport film / D750 en basse fréquence |
|---|---|---|
| HP5@1600 (pixel de 6,35 µm) | 0,107 (γ 0,8) à 0,143 (γ 0,6) | |
| D750 ISO 6 400 | 0,035 | 6,5 à 8,6 |
| D750 ISO 12 800 | 0,051 | 4,5 à 5,9 |
| D750 ISO 25 600 | 0,076 | 3,0 à 4,0 |
| D750 ISO 51 200 (Hi 2) | 0,117 | 1,9 à 2,6 |

Calcul. Par pixel, Hi 2 égale à peu près le film scanné ; mais le grain du film est corrélé (aire de corrélation ≈ 4 px², donc un facteur ≈ 2 de plus en basse fréquence), alors que le bruit du capteur est supposé blanc (hypothèse : le dématriçage le corrèle un peu, la réduction du bruit le lisse ; à mesurer). **Il faudrait ISO 280 000 à 500 000 pour égaler HP5@1600 aux fréquences que l'œil voit**, 2,5 à 3,3 IL au-delà de Hi 2. Contrôle indépendant avec la RMS 17 de Tri-X à EI 400 (pente 0,56 à 0,6, densité 1,0 placée ≈ 1,3 IL au-dessus du gris, hypothèse) : même ordre de grandeur, ≈ ISO 600 000. Calcul.

Réduire la taille d'image (M, S) ne change rien à ce niveau basse fréquence : moyenner un bruit blanc baisse l'écart type par pixel mais laisse σ × racine de l'aire constant (loi de Selwyn). Calcul.

**Spectre et texture.** Grain du film : amas de 2 à 4 pixels du D750, spectre décroissant dès le quart de la fréquence de Nyquist du scan. Bruit du capteur : proche du blanc au pas du pixel, avant dématriçage. En vue à 100 %, le bruit de Hi 2 paraît donc plus fin que le grain d'un scan HP5. Hypothèse pour le D750 (non mesuré) ; vérifié pour le film.

**Distribution.** Le grain du film change d'asymétrie avec la densité (+0,9 près du voile, −0,34 vers D 2,3 : points sombres isolés dans les ombres du négatif, trous clairs dans les zones denses). Le bruit photonique suit une loi de Poisson, très proche d'une gaussienne dès quelques dizaines d'électrons, sans ce renversement. Vérifié (film) ; capteur : hypothèse (physique générale).

**Monochrome et bruit de chrominance.** Le Monochrome du D750 calcule un gris pondéré des trois canaux équilibrés ; la marbrure colorée disparaît, mais le bruit indépendant de chaque canal s'ajoute en quadrature, pondéré par le carré de son poids. Un poids négatif (le filtre orange retire 0,13 du canal bleu, §3.3) ajoute donc du bruit au lieu d'en retirer, et les filtres qui chargent le rouge (orange, rouge) prennent le canal qui reçoit le moins de lumière en plein jour. Hypothèse (calcul de propagation, non chiffré faute des poids exacts du filtre « aucun »).

**Réduction du bruit.** D'après le manuel du D750, la réduction du bruit ISO sur « Désactivée » réduit encore le bruit « si nécessaire », jamais plus que sur « Faible ». Vérifié. Le bruit qu'on récupère n'est donc jamais brut ; son spectre est à mesurer.

**Preuve qu'un fabricant y arrive, mais avec un traitement dédié.** Fujifilm décrit sa simulation ACROS comme un **autre algorithme de réduction du bruit** qui transforme le bruit du capteur en texture de grain, plus marqué quand l'ISO monte, absent des hautes lumières et « comme du film » dans les basses lumières ; il le dit tributaire de son processeur X-Processor Pro. Vérifié. Le D750 n'a pas ce traitement ; c'est exactement la partie hors d'atteinte sans firmware. Hypothèse (rien de tel dans le manuel ni dans les chaînes du firmware, §3.1 du rapport précédent).

**Curiosité vérifiée : la superposition d'images.** Le menu Retouche du D750 combine deux NEF du même boîtier, chacun avec un gain de 0,1 à 2,0, à partir des données RAW (manuel p. 403-404). Vérifié. On pourrait y superposer une « plaque de grain » : un NEF au rapport 1:1 d'une plage uniforme d'un vrai négatif HP5 (le grain du 24×36 tombe alors à l'échelle 1 sur le capteur). Mais l'opération est une addition : grain d'amplitude constante en lumière linéaire, donc encore plus fort dans les ombres que le bruit photonique, plus un voile à retirer par la courbe ; photo par photo, après la prise. Hypothèse : intéressant pour la texture, faux pour la répartition par tonalité.

### 3.6 Verdict grain
- **Texture à 100 %** : proche à Hi 1 et Hi 2 en amplitude par pixel, plus fine que le film. Hypothèse (calcul plus mesure à faire).
- **Quantité visible à taille de tirage** : insuffisante à tous les ISO pour HP5 poussé ; pour HP5 à EI 400, l'écart dépend du tirage, non mesuré ici. Calcul et hypothèse.
- **Répartition par tonalité** : fausse, et c'est structurel : trop de bruit dans les ombres, pas assez dans les tons clairs. Calcul.
- Conclusion : **le bruit du D750 donne un « grain numérique de haute sensibilité », pas un grain HP5.** Le vrai grain HP5 demande un traitement par pixel (firmware, §3.4 du rapport précédent, ou logiciel type grainifier, Dehancer).

### Sources de la section 3
- ISO 10505:2009, *Photography: Root mean square granularity of photographic films: Method of measurement*, https://www.iso.org/standard/50747.html, consultée en octobre 2026.
- ISO 6328:2000, *Photography: Photographic materials: Determination of ISO resolving power*, https://www.iso.org/standard/22022.html, consultée en octobre 2026.
- ISO 15739:2023, *Photography: Electronic still-picture imaging: Noise measurements*, https://www.iso.org/standard/82233.html, consultée en octobre 2026.
- Eastman Kodak Company, *Kodak Pro 100T Film*, publication E-29, avril 1999 (définition du Print Grain Index), https://125px.com/docs/unsorted/kodak/e29.pdf, consultée en octobre 2026.
- Haugh E. F. (1963). A Structural Theory for the Selwyn Granularity Coefficient. *The Journal of Photographic Science* 11, 65-68. DOI 10.1080/00223638.1963.11736901.
- Jones L. A., Higgins G. C. (1947). Photographic Granularity and Graininess III: Some Characteristics of the Visual System of Importance in the Evaluation of Graininess and Granularity. *Journal of the Optical Society of America* 37, 217. DOI 10.1364/JOSA.37.000217.
- Bartleson C. J. (1985). Predicting Graininess from Granularity. *The Journal of Photographic Science* 33, 117-126. DOI 10.1080/00223638.1985.12035784.
- Tyrrell M., Jacobson R., Pointer M., Attridge G. (1993). A Study of Colour-Film Granularity and Print-Image Graininess. *The Journal of Photographic Science* 41, 48-55. DOI 10.1080/00223638.1993.11738479.
- Jacobson R. E., Axford N. R., Jones I., Ford A. M. (1989). Image Quality and Extended Development of Tabular Grain and Conventional Photographic Emulsions. *The Journal of Photographic Science* 38(4-5), 140-143. DOI 10.1080/00223638.1989.11737092.
- Zengerle P. L. (1983). *The Effect of Developer Composition on Adjacency Effects in Black and White Photography: Metol vs Phenidone*. Mémoire, Rochester Institute of Technology, https://scholarworks.rit.edu/theses/6659.
- Newson A., Delon J., Galerne B. (2017). A Stochastic Film Grain Model for Resolution-Independent Rendering. *Computer Graphics Forum* 36(8), 684-699. DOI 10.1111/cgf.13159.
- Newson A., Faraj N., Galerne B., Delon J. (2017). Realistic Film Grain Rendering. *Image Processing On Line* 7, 165-183. DOI 10.5201/ipol.2017.192.
- Zhang K., Wang J., Tian D., Pappas T. N. (2023). Film Grain Rendering and Parameter Estimation. *ACM Transactions on Graphics* 42(4), 1-14. DOI 10.1145/3592127.
- Lesné G., Gousseau Y., Ladjal S., Newson A. (2025). Neural Film Grain Rendering. *Computer Graphics Forum* 44(2). DOI 10.1111/cgf.70076.
- Stephenson I., Saunders A. (2007). Simulating Film Grain using the Noise-Power Spectrum. *Theory and Practice of Computer Graphics* (Eurographics UK). Non relu ; lien donné par grainifier : https://diglib.eg.org/bitstreams/372ec0ad-ff80-497b-81b0-2dd8d7021e48/download.
- Norkin A., Birkbeck N. (2018). Film Grain Synthesis for AV1 Video Codec. *2018 Data Compression Conference*, 3-12. DOI 10.1109/DCC.2018.00008.
- Ameur Z., Hamidouche W., François E., Radosavljević M., Menard D., Demarty C.-H. (2023). Deep-Based Film Grain Removal and Synthesis. *IEEE Transactions on Image Processing* 32, 5046-5059. DOI 10.1109/TIP.2023.3308726.
- Ameur Z. et al. (2023), MMSys, voir section 2.
- Geigel J., Musgrave F. K. (1997). A model for simulating the photographic development process on digital images. *SIGGRAPH '97*, 135-142. DOI 10.1145/258734.258813.
- Fyhr P. (2026), grainifier, voir section 2 (profil HP5@1600, notes du 29 et août 2026).
- Dehancer, *Film Grain*, https://dehancer.com/learn/article/grain, consulté en octobre 2026.
- Fujifilm, *The Newest Film Simulation « ACROS »*, X Stories, https://www.fujifilm-x.com/en-us/stories/the-newest-film-simulation-acros/, consulté en octobre 2026.
- Nikon, *D750 User's Manual* (6MB24611-01) : réduction du bruit ISO p. 317, contrôle du vignetage p. 315, superposition d'images p. 403-404, Hi 2 = ISO 51 200. Copie texte d'une session précédente.
- Astropix, *Camera Technical Specs* (tableau d'après sensorgen et Bill Claff : D750, capacité 81 593 e⁻, bruit de lecture 3,3 e⁻, rendement quantique 51 %, pas 5,97 µm), https://astropix.com/html/cameras/camera_technical_specs.html. Lu dans un extrait de recherche, page non ouverte.

## 4. Comment les émulateurs commerciaux construisent leurs modèles

Seulement ce qui est documenté ; tout vient des éditeurs eux-mêmes, aucune mesure indépendante de fidélité trouvée.

| Outil | Ce qui est documenté | Statut |
|---|---|---|
| **Dehancer** | profils construits en **échantillonnant le vrai support** : chaque film exposé à −2 IL, normal et +2 IL ; négatifs **tirés optiquement** sur papier (filtres couleur à l'agrandisseur), tirages contrôlés au spectrophotomètre ou au densitomètre puis **scannés** ; un profil = trois états interpolés ; exemple Portra 800 : 26 épreuves pour 3 cibles. Mire non nommée, appareil de prise non nommé, rien sur le N&B dans l'article de méthode. Grain : modèle procédural « physique », réglable par zones, équations non publiées | vérifié (pages Dehancer) |
| **FilmConvert** | profilage de chaque capteur (valeur enregistrée pour chaque couleur) et de chaque film, puis une table par couple appareil/film (19 films, plus de 1 000 tables en 2013) ; **grain scanné en 6K sur ArriScan chez Weta Digital** ; plus de grain dans les zones denses du négatif. Mires non nommées | vérifié (entretien de N. Stanford, 2013) |
| **le preset acheté** | profils Lightroom construits à partir de **scans 35 mm Frontier « calibrés »**, couleur par tables de plusieurs milliers de points ; cibles Portra 400, Gold 200, Pro 400H, Tri-X | hypothèse : lu seulement sur des pages miroirs ; le site officiel n'a pas répondu (erreur 429) |
| **RNI** | « vrais films numérisés avec la meilleure science de la couleur » ; profils caméra séparés qui ne contiennent aucun effet créatif ; tests sur de nombreux boîtiers et lumières. Rien sur les mires, le scan ou le grain | vérifié (FAQ RNI ; affirmation de l'éditeur) |
| **VSCO** | effets « construits à partir de scans de film » (PetaPixel, 2021) ; un test indépendant (E. Jelley, 2015) trouve qu'il faut beaucoup retoucher pour coller à ses propres scans | hypothèse : lu dans des extraits de recherche, articles non ouverts |
| **Fujifilm ACROS** | courbe plus dure des tons moyens aux hautes lumières, plus douce dans les ombres, dynamique inchangée ; grain obtenu en transformant le bruit du capteur par un algorithme de réduction du bruit propre à ACROS, plus fort quand l'ISO monte, absent des hautes lumières. **Aucune donnée du film Acros publiée** (ni spectre, ni courbe) | vérifié (Fujifilm X Stories) |

Ce qu'on en retient pour le D750 :
- Personne ne documente l'usage de mires N&B photographiées sur HP5 ou Tri-X. Dehancer et FilmConvert mesurent le film réel (tirages, scans) ; le preset acheté et VSCO partent de scans de laboratoire, donc d'un rendu scanner (Frontier) autant que d'un film. Vérifié et hypothèse, selon les lignes.
- La cible « Tri-X du preset acheté » de Thomas est donc un Tri-X **scanné au Frontier**, pas la fiche Kodak : cela explique son mélange proche d'une luminance (§3.3). Hypothèse.
- Le seul fabricant d'appareil qui imite un grain le fait par un traitement dédié du bruit (Fujifilm). Vérifié.

### Sources de la section 4
- Safarova N., Svinarchuk D., Kosenko P., Novak D. *How we build film profiles*, blog Dehancer (sans date), https://blog.dehancer.com/articles/how-we-build-film-profiles/, consulté en octobre 2026 ; *The building process for Kodak Portra 160VC film profile*, https://blog.dehancer.com/2019/03/11/189 (lu dans un extrait de recherche).
- Dehancer, *Film Grain*, https://dehancer.com/learn/article/grain, consulté en octobre 2026.
- Karpowicz J. (14/08/2013). *Achieve That « Film Look » with Digital by Using FilmConvert*. ProVideo Coalition, https://www.provideocoalition.com/achieve-that-film-look-with-digital-by-using-filmconvert/, consulté en octobre 2026.
- Really Nice Images, *FAQ*, https://reallyniceimages.com/faq.html, consultée en octobre 2026 ; Coleman A. (18/03/2021). Review of RNI's All Films pack. Fstoppers, https://www.fstoppers.com/reviews/analog-look-lightroom-review-rnis-all-films-pack-554798.
- PetaPixel (19/10/2021). *VSCO Introduces More than 100 New Film-Inspired Photo Effects*, https://petapixel.com/2021/10/19/vsco-introduces-more-than-100-new-film-inspired-photo-effects ; Jelley E. (01/09/2015). *Comparing a VSCO Film Emulation to the Actual Film*, https://petapixel.com/2015/09/01/comparing-a-vsco-film-emulation-to-the-actual-film (extraits de recherche).
- Fujifilm, *The Newest Film Simulation « ACROS »*, voir section 3.

## 5. Verdict par aspect pour le D750 réglé, et protocole de mesure

### 5.1 Sensibilité spectrale (le bleu)

Rappel (§3.3, vérifié par calcul) : les quatre filtres du Monochrome retirent du bleu ; le meilleur réglage (aucun filtre, WB 10 000 K) donne 0,13 de bleu contre 0,67 pour la fiche HP5, ΔL\* médian 7,9.

**Calcul nouveau : un filtre bleu physique devant l'objectif.** Modèle : filtre de conversion idéal, défini par son décalage en mireds (transmission proportionnelle au rapport de deux corps noirs, approximation de Wien) ; 80A ≈ −131 mired (3 200 → 5 500 K), 80B ≈ −112, 80C ≈ −81 (valeurs usuelles, non relues ici : hypothèse). Réponse du Monochrome « aucun » : soit la luminance ȳ (même hypothèse que le §3.3), soit la meilleure approximation de la luminance par trois Nikon de la base camspec (D3X, D700, D5100), faute de données du D750. 600 couleurs naturelles, lumière du jour D65, exposition égale.

| Configuration | ΔL\* méd. / 90e c. contre HP5 | Mélange sRGB linéaire | Perte |
|---|---|---|---|
| sans filtre (base) | 8,6 à 9,0 / 19,8 à 20,0 | 0,21 / 0,72 / 0,07 | 0 |
| 80A, WB fixe à la lumière | 7,8 (ȳ) ; 8,4 à 8,5 (Nikon) / 17,4 à 18,3 | 0,13 / 0,79 / 0,08 (Nikon) | 1,8 IL |
| meilleur filtre seul, WB fixe | 6,1 (ȳ, −350 mired, −4,7 IL) ; 8,0 à 8,2 (Nikon) | | 2,5 à 4,7 IL |
| **80A + blanc PRE mesuré à travers** | **7,2 à 7,4 / 15,8 à 16,3** | 0,15 / 0,68 à 0,70 / 0,16 à 0,17 | 1,8 IL |
| **80A + 80B (−250 mired) + PRE** | **5,3 à 5,7 / 11,4 à 12,4** | 0,09 / 0,60 à 0,64 / 0,27 à 0,31 | 3,3 à 3,4 IL |
| −350 mired + PRE | 3,2 à 3,9 / 7,7 à 9,4 | 0,05 / 0,50 à 0,56 / 0,40 à 0,45 | 4,6 à 4,7 IL |

Calcul. Contre la fiche Kodak Tri-X : base 6,4 à 6,5 ; 80A + PRE 4,9 à 5,1 ; −250 mired + PRE 2,8 à 3,3.

Pourquoi le PRE change tout (hypothèse cohérente avec le calcul) : avec une WB fixe, le filtre multiplie toute la réponse grise par sa transmission, mais cette réponse est presque nulle dans le bleu (proche de la luminance) ; il n'y a rien à relever. Avec un blanc mesuré à travers le filtre, le boîtier rééquilibre les canaux, et ce qui reste du filtre est une inclinaison **à l'intérieur** de chaque canal vers les courtes longueurs d'onde : la formule grise, inchangée, voit alors davantage de bleu et de cyan.

Limites : capteurs de substitution, formule grise du « aucun » supposée être une luminance, filtres réels différents du modèle (fuite possible dans le rouge lointain), mesure PRE peut-être refusée par le boîtier au-delà de sa plage (hypothèses). Le 80A seul est dans la marge du raisonnable (1,8 IL : en plein jour à ISO 400, rien de gênant). Le double filtre coûte 3,3 IL et reste à mi-chemin de HP5.

Comparaison au meilleur réglage sans accessoire (WB 10 000 K : 7,9 contre HP5 au §3.3, modèle un peu différent) : le 80A + PRE ne gagne qu'environ 0,5 point, le double filtre environ 2,4 points. Ordre de grandeur (calcul).

Verdict : **HP5 fidèle à la fiche : hors d'atteinte. HP5 « à moitié chemin » : peut-être atteignable avec un 80A + 80B et un blanc PRE, au prix de 3,3 IL** ; le 80A seul ne vaut pas mieux que la WB à 10 000 K. À vérifier en priorité (§5.7, séance A). Tri-X du preset acheté : déjà atteint par réglage (§3.3), pas besoin de filtre (il ferait dépasser la cible).

### 5.2 Courbe de tonalité, film puis tirage

- Atteignable : la chaîne négatif + tirage est une fonction globale et monotone de l'exposition ; la courbe perso du Picture Control (20 points, table de 257 valeurs appliquée après la courbe de base et le gamma) peut la porter, D-Lighting actif désactivé pour qu'elle reste fixe. Vérifié (capacité, §3.2) ; fidélité : hypothèse, chiffrée sur le D40 (ΔE médian 1,0 à 1,6 avec courbe ajustée) et sur le D750 (1,9 avec une courbe commune sur 4 photos).
- Cibles : HP5, Ilfotec HC 1+31, pente ≈ 0,59 à 0,64 et 3 log de partie droite sans épaule ; Tri-X, T-MAX, indice de contraste 0,56 ; papier de grade 2 (étendue d'exposition 1,10 log, ISO 6846, comme dans `films_nb.py`). Vérifié (fiches) et calcul.
- Hors d'atteinte : les effets de voisinage du développement (densité qui dépend du voisinage), le contraste local d'un tirage maquillé ; la dynamique au-dessus du gris : un négatif encaisse 10 IL de surexposition, le capteur coupe net. D'où l'exposition « pour les hautes lumières » (correction d'exposition négative) et le relèvement par la courbe, qui fait monter le bruit des ombres (§3.5). Hypothèse.
- Poussé (EI 1 600, 3 200) : plus de contraste et moins de détail dans les ombres (fiches, qualitatif, vérifié) ; sans courbe publiée du HP5 poussé, la courbe se cale sur des références (scans de Thomas). Hypothèse.

### 5.3 Grain
Voir §3.6. Réglage le moins mauvais si l'on veut du grain : ISO Hi 1 à Hi 2 en lumière faible (le grain vient avec la sensibilité, comme sur film), réduction du bruit ISO désactivée, taille L, JPEG Fine qualité optimale. Ce qu'on obtient : un bruit plus fin que le grain HP5, trop fort dans les ombres, trop faible dans les tons clairs. Hors d'atteinte : la forme du grain par tonalité, les amas, l'asymétrie. Hypothèse (calcul).

### 5.4 Netteté et effets de bord du révélateur
- Ce que montre la fiche Kodak : FTM au-dessus de 100 % (113 à 115 %) entre 5 et 10 cycles/mm, retour à 100 % vers 25 c/mm : c'est la signature d'un effet de bord (accélération du développement près des contours). Vérifié (graphique), interprétation : hypothèse cohérente avec Zengerle (1983) et Cline (1982, fonctions d'étalement chimique).
- Échelle sur le D750 : 5 à 10 c/mm sur le négatif = périodes de 100 à 200 µm, soit 17 à 34 pixels ; la bosse correspond donc à une accentuation de **grand rayon** (une dizaine de pixels), faible (+15 %). Calcul. La « clarté » de Nikon (contraste local) est la candidate naturelle ; l'« accentuation » agit sur quelques pixels. Les rayons ne sont pas documentés par Nikon : hypothèse, à mesurer.
- Hors d'atteinte : l'effet de bord du film dépend de la densité locale et de l'épuisement du révélateur ; la clarté du boîtier est un filtre fixe. Révélateurs à effet de bord = plus de grain (Zengerle) : le D750 ne lie pas les deux. Hypothèse.
- À 50 c/mm le film Tri-X (D-76) est vers 55 % ; le D750 avec un bon objectif à cette fréquence est inconnu ici (à mesurer). La perte à l'agrandissement ou au scan s'y ajoute côté film. Hypothèse.

### 5.5 Halo et vignetage
- Halo : HP5 120 et plan ont un dos anti-halo ; la fiche 35 mm n'en dit rien ; aucune fiche ne chiffre le halo. Vérifié. Le D750 n'a aucune fonction de halo ou de diffusion. Vérifié (manuel, chaînes du firmware). Un filtre de diffusion devant l'objectif donne un voile autour des hautes lumières, mais baisse le contraste partout : un autre effet. Hypothèse.
- Vignetage : Contrôle du vignetage sur Désactivé laisse le vignetage naturel de l'objectif (fonction réservée aux objectifs G, E et D, plus visible à pleine ouverture). Vérifié (manuel). Équivalent à un boîtier argentique avec le même objectif, à ceci près que les microlentilles du capteur peuvent assombrir un peu plus les bords à grande ouverture. Hypothèse.

### 5.6 Réglages proposés (mise à jour du tableau du §3.3)

| | Tri-X v2 (U1, corrigé à la relecture) | HP5 (emplacement C, sans mode U) |
|---|---|---|
| Base, filtre | Monochrome, aucun | Monochrome, aucun |
| WB | fixe 8 000 K | sans accessoire : 10 000 K ; **variante à tester : 80A + 80B sur l'objectif et blanc PRE mesuré à travers sur une carte grise** (−3,3 IL ; à valider, §5.7 A) |
| D-Lighting actif | désactivé | désactivé |
| Tonalité | courbe perso calée sur le preset | courbe perso plus douce (fiche ou scans de Thomas) |
| Clarté, accentuation | +1, 5 en attendant la mesure SFR | −1, 4 en attendant la mesure SFR |
| Réduction du bruit ISO | désactivée | désactivée |
| Contrôle du vignetage | désactivé | désactivé |
| Taille, qualité | L, Fine qualité optimale | L, Fine qualité optimale |
| ISO | selon la lumière ; Hi 1 et Hi 2 pour l'aspect « poussé » | idem |

Statut : proposition (hypothèse). La WB et le blanc PRE de la colonne HP5 ne tiennent que si la HP5 passe en U1 à la place du Tri-X ; sinon ils se règlent à la main. Que U1 garde un blanc PRE (d-1 à d-6) comme il garde une WB Kelvin : hypothèse à vérifier sur le boîtier.

### 5.7 Protocole de mesure : quoi photographier

Tout en NEF + JPEG Fine L, trépied, objectif fixe (le 50 mm habituel), Picture Control de test à contraste 0, luminosité 0, clarté 0, accentuation 0, D-Lighting désactivé, sauf mention.

**A. Bleu (séance prioritaire)** : ColorChecker Classic 24 et carte grise, plein soleil puis ombre, f/8, ISO 400.
1. Monochrome aucun, jaune, orange, rouge, vert ; WB 5 000, 8 000 et 10 000 K.
2. Même chose avec un 80A (puis 80A + 80B) devant l'objectif : d'abord WB 5 000 K, puis blanc PRE mesuré à travers le filtre sur la carte grise.
3. Facteurs de filtre : carte grise seule, sans filtre puis à travers un filtre bleu n° 47 (ou équivalent) et un vert n° 58 ; noter de combien d'IL la carte s'assombrit dans le JPEG Monochrome. Kodak donne pour Tri-X 6 (≈ 2,6 IL) au bleu et 6 au vert en lumière du jour (vérifié) ; un D750 réglé comme une luminance devrait donner bien plus au bleu (hypothèse).
4. En bonus, le test de 35mmc : bandes de couleur sur l'écran ; sur HP5, le bleu sort plus clair que le vert (vérifié) ; sur le D750 réglé, voir si l'ordre se renverse.

Calcul : gris de chaque patch contre le gris prévu pour HP5 et Tri-X (sensibilités des fiches × réflectances du ColorChecker × éclairage, comme `films_nb.poids`), après égalisation des 6 neutres ; ΔL\* médian et maximal sur les 18 patchs colorés. Réussite : 80A + PRE sous 7, double filtre sous 6 (les calculs le prévoient).

**B. Courbe** : carte grise uniforme, exposée de −6 à +4 IL par tiers (ou un coin de gris transmissif type Stouffer à 21 plages sur table lumineuse) : donne la courbe réelle du boîtier pour chaque réglage (méthode ISO 14524). Comparer à la cible (négatif de la fiche + papier de grade 2, ou exports de Thomas) ; écart RMS en L\* par plage.

**C. Grain** : carte grise défocalisée, cadrée plein champ, de −3 à +3 IL autour du gris par pas de 1 IL, à ISO 1 600, 3 200, 6 400, 12 800, 25 600, Hi 1, Hi 2 ; réduction du bruit désactivée puis Faible ; tailles L et S. Mesures par tonalité : écart type en L\* et en log, autocorrélation aux décalages 1 et 2, spectre radial, asymétrie. Comparer à grainifier HP5@1600 ramené au même positif (§3.5). Réussite : écart du rapport de grain par tonalité ; c'est ce chiffre qui tranchera « grain numérique » ou non.

**D. Netteté** : mire à bord incliné (lame de rasoir sur table lumineuse, ou mire ISO 12233 imprimée), au centre, f/5,6, avec accentuation 0, 3, 5, 7 et clarté −2, 0, +2, +5. Calcul de la FTM par bord incliné (par exemple MTF Mapper, outil libre : hypothèse sur son adéquation) ; chercher le réglage qui reproduit la bosse de 110 à 115 % entre 5 et 10 c/mm de la fiche Tri-X sans l'étendre au-delà de 25 c/mm.

**E. Vignetage et halo** : ciel couvert à travers un diffuseur opalin, à f/1,8, 2,8 et 5,6, Contrôle du vignetage désactivé puis Normal ; une lampe nue de nuit, pour voir s'il y a quoi que ce soit autour des hautes lumières.

**F. La référence qui manque : un vrai film.** Un film HP5 (et un Tri-X) dans un boîtier argentique à monture F avec le même objectif, mêmes mires (A, B, D) et la carte grise de C ; développement connu (ID-11 stock 7 min 30 à 20 °C, ou DD-X 9 min, fiche Ilford) ; scan **RAW linéaire** (VueScan RAW DNG sur scanner à film, ou le D750 lui-même avec un macro 1:1 sur table lumineuse, qui échantillonne le grain à 5,97 µm, assez pour des amas de 2 à 4 pixels). Avec grainifier, ce film donne σ_D(D), le spectre et l'asymétrie de **HP5 à EI 400 dans le révélateur de Thomas** : la cible de grain qui n'existe nulle part en données publiées. Les patchs du ColorChecker donnent en même temps la vraie réponse spectrale de HP5, à comparer à la fiche.

### Sources de la section 5
- Rapport perspectives-d200-xt4-d750.md, §3.2 et §3.3 (mesures d’octobre 2026 sur 66 NEF du D750, mélanges des filtres, réglages proposés).
- Kodak Alaris, F-4017 (2021) et Ilford, HP5 Plus (2018), voir section 1.
- Nikon, *D750 User's Manual*, voir section 3.
- Zengerle P. L. (1983), voir section 3 ; Cline D. S. (1982). *Prediction of Small-Scale Densities Using the Chemical and Optical Spread Functions*. Mémoire, Rochester Institute of Technology, https://scholarworks.rit.edu/theses/6469.
- Fyhr P. (2026), grainifier, voir section 2.
- Sroyon (2023), 35mmc, voir section 2.
- Jiang J. et al. (2013), camspec, voir section 2.

## Ce qui reste incertain
- La formule grise réelle du Monochrome « aucun » et du filtre « vert » du D750 : aucun NEF de Thomas ne les utilise ; tous les calculs de filtre bleu en dépendent (séance A).
- Les vraies courbes de transmission des filtres 80A et 80B achetés, et si le D750 accepte un blanc PRE à travers eux.
- Le spectre du bruit du D750 après dématriçage et réduction « désactivée » : supposé blanc ici.
- Le grain de HP5 à EI 400 : aucune donnée publiée ; seule la mesure de HP5 poussé à 1 600 existe, au scanner, avec un écart de 1,8 fois d'un film à l'autre.
- La provenance des données Tri-X de 2021 (granularité, FTM, spectre), qui viennent de l'ancienne émulsion d'après la fiche de 2002.
- La pente du HP5 poussé (0,6 à 0,8 pris ici) et la place du gris moyen sur le négatif, qui fixent les ISO équivalents à ±0,5 IL environ.
