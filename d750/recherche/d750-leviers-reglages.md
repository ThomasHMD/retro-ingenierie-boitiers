# D750 sans firmware : les leviers qu'on n'exploite pas encore

Recherche d’octobre 2026, à la demande de Thomas (« avec les réglages qu'on a, on doit pouvoir aller plus loin »). Le D750 reste un boîtier de production : rien ici ne touche au firmware. **Cadre fixé par Thomas** : la plus grande fidélité à la cible dès le JPEG du boîtier, pour se passer de Lightroom ; tout ce qui se fait après la prise de vue (menu Retouche) est écarté ; révélateur de référence pour le noir et blanc : DD-X.

Critère de réussite retenu : ΔE2000 **médian sous 2 et 90e centile sous 4** contre la cible. Un écart de 1 se voit côte à côte, 2 à 3 passe inaperçu sur une image regardée seule, au-delà de 5 il saute aux yeux (ordres de grandeur usuels, à prendre comme repères). Prolonge [kodachrome-fp4-donnees.md](kodachrome-fp4-donnees.md) et perspectives-d200-xt4-d750.md §3.

Conventions de statut : **vérifié** (lu dans une source citée), **hypothèse**, **calcul** (chiffre produit ici à partir de sources vérifiées et d'hypothèses nommées).

Source principale des fonctions : *Nikon D750 User's Manual* (anglais, 537 p., copie lue : https://manuals.coolblue.de/04/nikon-d750.pdf, SHA-256 661d20c6…5019). Les numéros de page cités sont ceux du manuel imprimé.

## En bref

| Levier | Ce qu'il apporte | Statut | Reste à faire |
|---|---|---|---|
| **Courbe perso calculée sur la vraie base Standard** (§6) | Classic Chrome : de 6,0 (Standard brut) à **2,2** ΔE médian avec la seule courbe ; Kodachrome 64 : de 15,7 à 6,0 | calcul sur un vrai D750 (mire Imaging Resource) | Picture Control d'essai prêts : [`recettes/d750-v0/`](../recettes/d750-v0/) |
| **Balance des blancs décalée comme matrice couleur** | Kodachrome 64 : 3 à 5 crans vers B (≈ +15 à +25 mired) font passer l'écart de 5,3 à **3,1** sur la vraie base Standard (de 4,9 à 3,8 sur capteurs de substitution). Classic Chrome et Classic Neg : gain faible ou nul sur la vraie base | calcul | voir à l'œil, puis mesurer |
| **Mode d'application de la courbe** (luminance seule ou chaque canal R, V, B) | décisif selon la cible (Classic Chrome : 2,3 contre 4,0 sur capteurs de substitution) ; sur la vraie base Standard, le modèle « par canal » colle mieux au JPEG (2,6 contre 2,7 en médiane, 4,8 contre 5,4 au 90e centile) | indice (§6), pas une preuve | confirmé par les essais v0 |
| **Réglages au quart de cran** | saturation, teinte, contraste, etc. réglables par 0,25 avec la molette secondaire : 4 fois plus fin que les crans entiers | vérifié (manuel p. 167, 170) | vérifier que les NP2 écrits par `picture_control.py` gardent les quarts |
| Menu Retouche (intensificateurs R, V, B, traitement NEF, superposition de NEF, filtres) | existe (vérifié, p. 400 à 417) | **écarté par Thomas** : après la prise de vue, autant passer par Lightroom | rien |
| **HDR JPEG (deux vues)** | latitude des hautes lumières façon négatif | fonction : vérifié (p. 177) ; pas de NEF, sujet immobile | essai |
| **Mesure pondérée hautes lumières** + courbe calée en conséquence | exposer « pour les hautes lumières » comme un négatif, puis relever par la courbe | vérifié (p. 139, objectifs G, E et D) ; calage : calcul à faire | une série d'exposition |
| **Espace Adobe RGB** | récupère une partie des 12 % de couleurs Kodachrome hors sRGB | fonction : vérifié (p. 314) ; gain : hypothèse | gestion des couleurs à suivre à l'export |
| Picture Control optionnels « D2X Mode » | aucun | **fermé** : réservés aux D3, D3X, D300 et D700 (aide Picture Control Utility 2) | rien |
| Courbes R, V, B séparées | aucun | **fermé** : une seule courbe (aide PCU2, format NCP) | rien |
| Creative Picture Control (20 rendus) | aucun | **fermé** : D780, D6 et boîtiers Z seulement (aide PCU2) | rien |

Avis : la voie la plus rentable est maintenant **les Picture Control d'essai v0** ([`recettes/d750-v0/`](../recettes/d750-v0/)) : ils sont calculés sur la base Standard d'un vrai D750, et les paires NEF + JPEG que Thomas en tirera trancheront à la fois l'acceptation des fichiers NCP, le mode de courbe et la WB du Kodachrome. Pour Classic Chrome, la cible est presque atteinte en médiane ; il reste le 90e centile (6,3), dû aux bleus et aux cyans que Standard pousse vers le violet.

## 1. La balance des blancs comme matrice couleur

**Principe** (hypothèse cohérente avec la chaîne de traitement d'un boîtier) : la WB est un gain par canal appliqué au signal du capteur, *avant* la matrice capteur → sRGB. Si l'on décale ces gains volontairement, on ne fait pas qu'ajouter une dominante : la matrice transforme ce décalage en déformation de teinte différente selon les couleurs. C'est la seule « matrice » qu'on puisse toucher sans firmware.

**Calcul** ([`outils/d750_leviers.py`](../outils/d750_leviers.py), résultats dans [`donnees-films/d750-leviers-wb.json`](donnees-films/d750-leviers-wb.json)) : 600 spectres naturels + ColorChecker, lumière du jour ; capteurs de substitution Nikon D3X, D700 et D5100 (base camspec ; aucune donnée publiée pour le D750) ; matrice du boîtier approchée par ajustement ; cible = Kodachrome (modèle spectral, §2 de *kodachrome-fp4*) ou LUT Fujifilm officielles. Pour chaque cible : la courbe neutre de la cible, puis saturation et teinte globales, puis le décalage de WB. Écart ΔE2000 médian (90e centile).

| Cible | Courbe seule | + saturation, teinte | + WB décalée | WB optimale (crans du D750) | Saturation | Statut |
|---|---|---|---|---|---|---|
| Kodachrome 64, courbe en luminance | 5,3 à 5,5 | 4,9 à 5,0 | **3,8 (7,5 à 7,8)** | **B 4 à 5**, G-M ≈ 0 | ≈ 0,8 | calcul |
| Kodachrome 64, courbe par canal | 6,2 à 6,4 | 4,4 à 4,5 | **3,1 à 3,3 (7,2 à 7,6)** | **B 5 à 6**, G-M ≈ 0 | ≈ 0,7 | calcul |
| Kodachrome 25 | 5,2 à 6,5 | 3,8 à 4,5 | 2,9 à 3,8 | B 2,5 à 3, G ½ | 0,6 à 0,8 | calcul |
| Kodachrome 200 | 5,6 à 6,8 | 4,3 à 4,9 | 3,2 à 3,6 | B 4,5 à 5,5, G ½ | 0,6 à 0,8 | calcul |
| Classic Chrome, courbe en luminance | 5,3 | 3,9 à 4,0 | 3,8 à 3,9 | A 1 à 1,5 (inutile) | ≈ 0,7 | calcul |
| Classic Chrome, courbe par canal | 2,9 à 3,0 | **2,3** | 2,1 à 2,2 | ≈ 0 | ≈ 0,9 | calcul |
| Classic Neg, courbe en luminance | 7,0 à 7,3 | 6,1 à 6,3 | 5,4 à 5,5 | A 3 à 4, G-M ≈ +½ | ≈ 0,7 | calcul |
| Classic Neg, courbe par canal | 6,4 à 6,6 | 5,1 | 4,7 à 4,9 | A 3, G-M ≈ +½ | ≈ 0,8 | calcul |

Fourchettes : les trois capteurs. Le résultat Kodachrome est stable d'un capteur à l'autre (B 4 à 6) : c'est un effet de la cible, pas du capteur.

Lecture :
- **Kodachrome : la WB froide est le levier le plus fort trouvé.** Elle reproduit à la fois la dominante froide des tons moyens prévue par la fiche et une partie des dérives de teinte (jaunes et verts vers le cyan). Sur le boîtier : WB lumière du jour avec réglage fin **B5**, ou WB en Kelvin réglée vers 4 800 K en plein soleil. Elle ne voyage qu'avec U1 ou U2 ; sinon, elle se règle à la main. Réserve : la cible est un modèle, et la mire Kodak Q-60K3 montre des clairs plutôt verts, pas bleus (*kodachrome-fp4* §2.4). **À valider à l'œil avant de l'adopter.**
- **La saturation optimale est inférieure à 1 partout.** Pour le Kodachrome, ça vient du modèle (sans effets inter-couches, il sous-estime la saturation : chiffre non fiable). Pour les Fuji, c'est la LUT elle-même : Classic Chrome et Classic Neg sont réellement désaturés.
- **Classic Neg veut une WB chaude** (A 3) avec une teinte tournée de +6 à +12° (sens Nikon « positif » : rouges vers orange, verts vers bleu, bleus vers pourpre ; manuel D800, hypothèse pour le D750). **Non confirmé sur la vraie base Standard** (§6) : le gain y est faible et instable.
- **Classic Chrome n'a pas besoin de la WB**, mais dépend fortement du mode de courbe (§2).
- Teinte optimale avec WB : entre −3 et +3° pour le Kodachrome, donc curseur Teinte à 0.

## 2. Le mode d'application de la courbe perso

L'aide de Picture Control Utility 2 dit que la courbe perso est une seule courbe d'entrée-sortie, « calculée en 16 bits » (255 traité comme 65 535). Vérifié (pages « About Custom Curve » et « About Level Adjustment », nikonimglib.com/npcu/onlinehelp/en/pc010000.html et pc009000.html). Conséquence utile : relever les ombres par la courbe ne crée pas de marches dans les dégradés à cause de la courbe elle-même (hypothèse raisonnable ; le bruit du capteur reste).

Ce que l'aide ne dit pas : **la courbe agit-elle sur la luminance seule, ou sur chaque canal R, V, B ?** Une courbe en S appliquée canal par canal augmente aussi la saturation et décale certaines teintes ; appliquée sur la luminance, elle laisse les couleurs presque intactes. Le calcul du §1 montre que ça change tout pour Classic Chrome (2,3 contre 4,0 ΔE). C'est le premier test à faire (§5, test 1).

## 3. Ce que le boîtier propose et qu'on n'utilise pas

Tout est vérifié dans le manuel du D750 ; les effets sont à mesurer.

- **Quart de cran** (p. 167, 170) : chaque réglage du Picture Control (y compris la saturation du virage en monochrome) peut se régler par 0,25 avec la molette secondaire. Le format NP2 stocke des valeurs fractionnaires (`picture_control.py` : valeur = (v − 0x80) × pas / 16).
- **Virage du monochrome** (p. 169 et 170) : teinte du N&B avec saturation réglable au quart. Piste pour imiter un papier baryté chaud sous la HP5 ou la Tri-X, au plus bas niveau. Effet en b\* : à mesurer.
- **Menu Retouche** (p. 400 à 417) : copies créées dans le boîtier à partir d'une photo déjà prise. **Écarté par Thomas** (après la prise de vue, autant passer par Lightroom) ; gardé ici pour mémoire.
  - Effets de filtre : skylight, filtre chaud, **intensificateur de rouge, de vert ou de bleu**, étoiles, **flou doux**. Les intensificateurs sont la seule saturation par teinte du boîtier ; le flou doux, une piste pour le halo des hautes lumières.
  - Équilibre colorimétrique (vert, bleu, ambre, magenta), avec histogrammes R, V, B.
  - **Superposition** de deux NEF avec un gain de 0,1 à 2,0 chacun : une vue nette + une vue défocalisée à faible gain = halo de type film (hypothèse, essai sur trépied).
  - **Traitement NEF** : refaire le JPEG d'un NEF dans le boîtier avec un autre Picture Control, une autre WB, une autre exposition. On choisit donc le film après coup, sans ordinateur.
  - Monochrome : copies N&B, sépia ou cyanotype.
- **Exposition multiple** (p. 216 à 220) : 2 à 10 vues, gain automatique (1/n) ou non. Le D750 n'a pas les modes « éclaircir » ou « assombrir » des boîtiers récents. Vérifié.
- **HDR** (p. 177) : deux vues combinées en JPEG, force réglable, pas de NEF, pas de flash. Piste pour la latitude du négatif dans les hautes lumières (portrait Portra, Classic Neg) ; à juger sur des sujets immobiles.
- **Mesure pondérée hautes lumières** (p. 139, objectifs G, E et D) : l'exposition protège les hautes lumières ; la courbe perso relève ensuite les tons moyens. C'est exactement la logique d'un négatif. La courbe devra être calée sur le décalage d'exposition que produit ce mode : à mesurer (test 3).
- **Adobe RGB** (p. 314) : gamme plus large que sRGB pour les couleurs saturées du Kodachrome, à condition que la chaîne d'affichage gère le profil.

Ce qui est fermé (vérifié) :
- **D2X Mode** (trois rendus couleur optionnels de Nikon) : utilisables seulement sur D3, D3X, D300 et D700 (aide PCU2, « Importing Custom Picture Control »).
- **Creative Picture Control** : D780, D6 et boîtiers Z (aide PCU2, « What You Can Do »).
- **Courbes R, V, B séparées** : n'existent pas dans PCU2 ni dans le format NCP.

## 4. Tri-X en DD-X (ou en Rodinal)

Révélateurs utilisés par l'auteur pour la Tri-X : Ilfotec DD-X, et le Rodinal par le passé.

Données : Kodak ne publie pas de courbe Tri-X en DD-X ni en Rodinal ; Ilford ne publie pas la Tri-X dans sa fiche DD-X. Vérifié. La fiche Ilford des révélateurs liquides (juin 2010, copie MACO, https://www.macodirect.de/media/pdf/bc/c9/ce/ILC20_datenblatt_e.pdf) précise que ses temps visent un contraste « normal, typiquement autour d'un G-barre de 0,62 ». En DD-X 1+4 à 20 °C : HP5 à EI 400 9 min, FP4+ à EI 125 10 min. Vérifié.

**Choix de Thomas : DD-X.** Cible proposée pour la Tri-X en DD-X (et en Rodinal) à leurs temps conseillés : la courbe Kodak interpolée à la **pente moyenne 0,62** (entre D-76 8 et 10 min, ou entre T-MAX 7 et 9 min : les deux donnent le même résultat à 0,5/255 près). Hypothèse : à temps conseillé, ces révélateurs visent le même contraste. Le Rodinal donne en plus un grain plus marqué et plus d'effet de bord, ce que la courbe ne porte pas. Sortie 8 bits par IL autour du gris (calcul ; [`donnees-films/hp5-trix-cibles.json`](donnees-films/hp5-trix-cibles.json), `trix_g062_d76`) :

| | −3 IL | −2 IL | −1 IL | 0 | +1 IL | +2 IL |
|---|---|---|---|---|---|---|
| **Tri-X, DD-X ou Rodinal (pente 0,62)** | 13 | 28 | 59 | 117 | 185 | 228 |
| Tri-X T-MAX 6 min (cible actuelle du projet) | 20 | 36 | 67 | 118 | 178 | 221 |
| HP5, fiche (Ilfotec HC ; DD-X visé au même contraste) | 14 | 27 | 57 | 117 | 183 | 226 |

Lecture : à développement « normal Ilford », la Tri-X est un peu plus contrastée que la cible actuelle du projet (T-MAX 6 min, pente 0,54) et presque identique à la HP5. Pour la HP5 en DD-X, la courbe de la fiche reste la bonne cible (même contraste visé).

## 5. Protocole : quatre tests qui débloquent tout

Tout en NEF + JPEG fine, trépied, même scène colorée (ColorChecker si disponible, sinon une scène avec rouge, jaune, vert, ciel, peau, neutres), D-Lighting actif désactivé.

1. **Mode de la courbe** (le plus important) : Picture Control Neutre, courbe perso linéaire, puis la même avec une courbe en S forte (par exemple 64 → 40, 192 → 216). Si les couleurs saturées gagnent en chroma avec la courbe en S, la courbe agit canal par canal ; si elles gardent leur chroma à luminance égale, elle agit sur la luminance. Mesure sur les JPEG (ΔC\* par plage). Ce test fixe la méthode de calcul pour les neuf profils.
2. **Curseur Teinte et curseur Saturation** : Neutre, teinte −3, 0, +3 (puis ±1), saturation −3, 0, +3. Mesure : rotation en degrés CIELAB par cran, uniforme ou non selon les teintes.
3. **WB Kodachrome** : même scène en lumière du jour, WB lumière du jour avec réglage fin A-B à 0, B3 et B5, avec le Picture Control Kodachrome. Jugement à l'œil d'abord, puis mesure des neutres. En parallèle, mesure pondérée hautes lumières contre matricielle, pour connaître le décalage d'exposition à intégrer à la courbe.
4. **Virage du monochrome** (pour un papier chaud sous HP5 ou Tri-X) : virage sépia au niveau le plus bas, au quart de cran. Mesure du b\* obtenu.

Les essais v0 ([`recettes/d750-v0/README.md`](../recettes/d750-v0/README.md)) couvrent les tests 1 et 3 avec de vrais profils.

## 6. La base Standard mesurée sur un vrai D750

Données : mire d'Imaging Resource photographiée avec un D750 le 24/09/2014 (ColorChecker 24 + ColorChecker SG 140 plages + échelle de gris), en NEF et en JPEG, Picture Control Standard d'origine, D-Lighting actif désactivé, WB mesurée, ISO 100 (EXIF lu sur la page d'Imaging Resource). Vérifié. Fichiers : https://old.imaging-resource.com/PRODS/nikon-d750/FULLRES/D750hVFAI00100.JPG et `.NEF` (non recopiés). Mesures : [`donnees-films/d750-standard-ir.json`](donnees-films/d750-standard-ir.json) ; outil : [`outils/d750_standard.py`](../outils/d750_standard.py).

**Courbe de Standard** (gris de la mire) : gris à 18 % → 121/255, blanc de la mire (Y 0,91) → 242, Y 0,065 → 56, Y 0,02 → 28. Vérifié (mesure).

**Rendu de Standard contre la mire** (même luminance de blanc, teinte en degrés CIELAB, calcul) :

| Secteur | rouge | orange, peau | jaune | vert-jaune | vert | cyan-vert | cyan | bleu | violet | magenta |
|---|---|---|---|---|---|---|---|---|---|---|
| Teinte | +5,6° | +0,3° | +3,3° | −0,5° | −4,8° | +14,6° | +24,7° | +12,9° | −1,3° | +2,1° |
| Chroma | ×1,00 | ×1,01 | ×0,90 | ×0,96 | ×0,89 | ×0,69 | ×0,89 | ×1,31 | ×1,22 | ×1,01 |

Standard pousse les rouges vers l'orange, les cyans vers le bleu et sature les bleus. Ça recoupe la description d'Imaging Resource (« reds shifted slightly toward orange, cyan toward blue »). Écart médian de Standard à la mire : 4,8 ΔE.

**Mode de courbe de la base** : une matrice libre suivie de la même courbe sur R, V, B reproduit le JPEG à 2,56 ΔE médian (4,83 au 90e centile, 8,0 au max) ; suivie d'une courbe sur la luminance seule, à 2,68 (5,41 ; 9,1). Indice en faveur du « par canal », pas une preuve. Calcul.

**Meilleur Picture Control sur base Standard** (courbe perso calculée = cible ∘ Standard⁻¹, appliquée par canal ; saturation et teinte modélisées en CIELAB ; WB simulée par le modèle de la base) :

| Cible | Plages | Standard brut | Courbe seule | + saturation, teinte | + WB | WB |
|---|---|---|---|---|---|---|
| Classic Chrome | 164 | 6,0 (8,0) | **2,2 (6,3)** | 1,9 (6,5) | 1,6 (6,1) | ≈ 0 |
| Classic Neg | 164 | 5,4 (10,9) | 4,6 (10,9) | 4,2 (10,1) | 4,2 à 4,6 | A 0 à 3, instable |
| Kodachrome 64 | 24 | 15,7 (21,5) | 6,0 (11,0) | 5,3 (11,4) | **3,1 (6,3)** | B 3 environ |

Médiane (90e centile), ΔE2000 ; calcul. Les cibles noir et blanc (Tri-X DD-X, HP5, FP4) n'ont que leur courbe : la base Monochrome est supposée avoir la courbe de Standard (non mesurée).

Lecture : avec la seule courbe, Classic Chrome atteint le critère en médiane mais pas au 90e centile (les bleus et cyans de Standard restent trop violets et trop saturés : un curseur Teinte négatif ou la base Neutre pourrait aider, à mesurer). Le Kodachrome a besoin de la WB décalée pour passer sous 3,5. Classic Neg reste loin (4,2) : sa palette demande des corrections par teinte que la base Standard ne donne pas ; une autre base est à essayer.

## Ce qui reste incertain

- La chaîne couleur réelle du D750 (sensibilités, matrice, traitement par base) : capteurs de substitution ici. L'ordre de grandeur et le sens des résultats tiennent sur trois capteurs ; les valeurs exactes non.
- La cible Kodachrome est un modèle sans effets inter-couches : la WB B5 et la saturation optimale sont à valider à l'œil.
- Le curseur Teinte est modélisé comme une rotation CIELAB uniforme : à vérifier (test 2).
- L'effet réel du virage, non documenté par Nikon : à mesurer (test 4).
- Les autres bases (Neutre, Uniforme, Portrait, Paysage, Saturé, Monochrome) ne sont pas mesurées : la v0 ne repose que sur Standard. Raccourci possible sans prise de vue : ouvrir le NEF d'Imaging Resource dans NX Studio, l'exporter avec chaque base et chaque cran, et vérifier d'abord que NX Studio redonne le JPEG du boîtier en Standard (hypothèse : même traitement).
