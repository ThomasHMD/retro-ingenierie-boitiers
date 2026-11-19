# R&D Nikon, novembre 2026 : réajuster les recettes du D750 sur le vrai moteur de Nikon (NX Studio)

Suite de `veille-picture-control-2026-11.md` (§2 idée n° 2, §4). Prototype : [`outils/d750_ajuster_nx.py`](../outils/d750_ajuster_nx.py) (`--self-test` OK). Sorties : `recettes/d750-nx/` (`usb/<recette>-nx.json` au format v1, `.NCP`, `resume.json`). Rien n'a été chargé dans un boîtier, ni publié, ni commité. Les recettes v1 et v2 ne sont pas touchées.

Statuts : **mesuré** = chiffre sorti d'un calcul de cette séance ; **hypothèse** = pas testé.

## En bref
> **Passe 2 (NP2) en bas de page : elle remplace les conclusions de la passe 1 (NCP) ci-dessous.** Le biais du chemin NCP est levé par le NP2 (`SavedPicConProcess=1`), voir `rd-nikon-2026-11-formats-nx.md`. La passe 1 est gardée telle quelle pour comparaison (`d750-nx/usb/*-nx-ncp.*`, `resume-ncp.json`).

- La boucle marche : rendus NX Studio réels dans un Gauss-Newton borné, 53 à 68 rendus par recette (environ 490 rendus en tout, avec essais et contrôles).
- **Le bon repère est le JPEG du boîtier, pas NX v1** : NX (NCP v1) s'écarte déjà du boîtier de 0,8 à 2,1. APRÈS contre le boîtier (médiane, vue tenue à part) : **Hasselblad 1,93 contre 2,60 et Positive 2,19 contre 3,21 sont crédibles** (le chemin NCP y est proche du JPEG, 1,17 et 1,30) ; **Classic Neg 2,66 contre 3,67 en médiane seulement** (p90 en hausse) ; **Classic Chrome 1,38 contre 1,56 est sous l'erreur du chemin NCP (2,10) : non établi** ; **HP5 2,62 contre 2,66 : aucun gain** (l'ajustement rattrape le biais du chemin NCP, 3,74 au départ) ; **FP4 3,54 contre 2,46 : pire** ; Portra : pas d'amélioration (2,27 contre 2,05 pour NX v1), pas de repère boîtier comparable.
- **Rien n'est démontré pour le boîtier** : l'écart NX (NCP) contre boîtier est du même ordre que les gains. Ne rien charger avant un essai réel. Détail dans « Limites ».

## Méthode
**Chaîne de mesure.** Pour une image : NX Studio développe le NEF avec le Picture Control imposé par un NCP (`outils/nx_rendu.py`, largeur 3 008 px : même durée qu'à 6 016, le décodage domine) ; moyennes par blocs de 24 px sur la grille du JPEG, mêmes blocs retenus que `mesures_reelles.py` / `d750_analyse.py` (importés, non modifiés : `extraire`, `masque`, `vue`, `matrice_camera`, cibles de `d750_cibles.py`) ; gain radial (1 + a r² + b r⁴ en linéaire) ajusté **une fois par NEF** (NX tel quel contre JPEG du boîtier), réutilisé pour tous les essais de ce NEF ; ΔE2000 contre la cible, calculée en CIELAB depuis la scène lue dans le même NEF (vignetage du modèle appliqué aux lots 28 mm, comme les jeux d'évaluation).

**Contrôle d'alignement** (mesuré ; lot1 est le moins bon : le gain radial y va à l'inverse de lot4, JPEG environ 28 % plus sombre que NX à r = 0,7 contre 14 % plus clair, et NX tel quel n'y tient que 1,73 : le recalage au 28 mm n'y est pas vérifié, sans effet sur la vue tenue à part dont le gain vaut 1). NX tel quel contre JPEG sur ces blocs, médiane : lot1 1,73 (4,07 sans le gain), lot4 0,79 (1,71 sans), vues du test v1 : 0,94 à 1,43 en couleur, **0,15 et 0,20 en N&B**. Au 135 mm de la vue test, le gain radial est neutre (1,00 ± 0,04, comme prévu : pas de correction du vignetage au boîtier avec cet objectif manuel).

**Entraînement et tenue à part** (choix). Entraînement : vues BASE STANDARD de `lot1` (pièce aux guitares, 28 mm f/1,8, 14 686 blocs) et `lot4` (bibliothèque, 28 mm f/5,6, 5 568 blocs, rayon < 0,7 comme dans `da.vue`). Tenue à part : la vue du test v1 de la recette (pédalier, 135 mm, 5 212 blocs communs). Pourquoi ce sens : le test v1 est la mesure de référence du boîtier (chiffres de `resultats-mesures.md` / `d750.json`), et `lot3` est le même pédalier : **`lot3` est écarté de l'entraînement** pour qu'aucune scène ne fuie. Scènes très différentes (intérieur et bibliothèque contre pédalier aux verts saturés) : le test est sévère. Une seule scène tenue à part : les écarts sous 0,3 ne sont pas significatifs.

**Paramètres** (ce que le NCP laisse passer).
- **Base** : criblée par un rendu par candidate (Standard, Neutre, Portrait ; en N&B : filtre aucun, jaune, orange, rouge, vert). On ne change que si le critère gagne plus de 0,3. Résultat : Standard et « aucun » gardent la tête (HP5 : vert 5,31 contre 5,40, sous le seuil de 0,3). Le criblage favorise Standard par construction : la courbe v1 a été faite pour elle.
- **Saturation et teinte : entiers seulement.** `ecrire_ncp` stocke un octet par curseur : le quart de point du boîtier (BORNES_PTP) ne passe pas par le NCP. Un tour de voisins ±1 (rendus réels) avant et après la courbe. Le quart de point demanderait un écrivain NP2 (hypothèse : NX l'accepte, non testé).
- **Courbe perso** : 9 nœuds d'écart (x = 6, 15, 25, 37, 50, 62, 75, 87, 95 % de l'échelle) ajoutés aux 20 points de la courbe v1, interpolation monotone (PCHIP), bornés à ±40 codes, rendue croissante.
- **Gauss-Newton** : jacobien par différences finies sur de vrais rendus (pas de 4 codes), résidus L, a, b pondérés comme gerard662 (√W / √(ΔE + 0,5), W = 1 / 0,6 / 0,3 sous 45 / 60 / au-delà de chroma), amortissement de Tikhonov, pas 1 puis 0,6 puis 0,3, 2 itérations au plus, arrêt si le gain est < 0,005 ; critère d'acceptation : médiane + ½ p90, moyenné sur les images d'entraînement. Aucun nœud en butée dans les 7 ajustements.
- **APRÈS** : la recette finale arrondie (celle qui est écrite) est re-rendue, jamais le dernier état interne.

## Résultat (ΔE2000 médian, p90 entre parenthèses ; vue tenue à part = test v1, pédalier)

| Recette | Boîtier v1 contre cible | NX v1 contre cible (AVANT) | NX ajusté contre cible (APRÈS) | Rendus | Réglages : v1 → ajusté | En butée |
|---|---|---|---|---|---|---|
| Classic Chrome | 1,56 (3,79) | 2,01 (2,75) | **1,38 (3,72)** | 68 | sat −1, teinte −2 → 0, −2 | aucun |
| Classic Neg | 3,67 (10,05) | 3,74 (8,68) | **2,66 (10,11)** | 63 | 0, 0 → +1, −1 | aucun |
| Positive | 3,21 (5,53) | 3,52 (7,57) | **2,19 (6,99)** | 65 | +2, −2 → +2, −2 | aucun |
| Hasselblad | 2,60 (4,75) | 2,54 (4,23) | **1,93 (3,15)** | 63 | +1, −3 → +2, −2 | aucun |
| Portra (v2 écrite, cible « esprit Portra ») | n.c. | 2,05 (4,77) | 2,27 (4,65) | 61 | +3, +2 → +3, 0 | saturation +3 (limite du boîtier) |
| HP5+ | 2,66 (11,49) | 3,74 (10,39) | **2,62 (10,39)** | 53 | filtre aucun, courbe seule | aucun |
| FP4+ | 2,46 (15,61) | 3,24 (9,67) | 3,54 (8,87) | 57 | filtre aucun, courbe seule | aucun |

- Les colonnes « boîtier » sont celles de `d750.json` (JPEG du test v1 contre cible), recalculées ici sur les mêmes blocs : elles retombent aux centièmes sur Classic Chrome (1,56 / 3,79), Classic Neg, Positive, Hasselblad et FP4 ; HP5 donne 2,66 (11,49) contre 2,75 (11,19) dans `d750.json` (cause non cherchée). **Portra n.c.** : la vue du test v1 a été prise avec la v1 de Portra et l'ancienne cible ; la recette ajustée part de la v2 écrite dans le boîtier et de la cible « esprit Portra » : le JPEG de cette vue ne correspond pas (5,45 serait un chiffre sans sens). Le Portra de la reprise du lot 2 (bibliothèque, autre scène) est à 4,6.
- Nombre de rendus : Classic Chrome affiche 68 (essai avec un critère à ¼ de p90, rejoué ensuite depuis le cache) ; les autres 53 à 63 en passe unique. Total de la passe finale : 363 rendus (619 s de rendu) ; avec l'essai, les contrôles et les sondes, environ 490.
- Entraînement, médiane avant → après (lot1 / lot4) : Classic Chrome 2,24→1,44 / 2,02→1,84 ; Classic Neg 4,13→2,69 / 5,05→5,24 ; Positive 1,96→1,61 / 2,82→2,10 ; Hasselblad 2,37→1,46 / 3,47→2,98 ; Portra 2,77→1,64 / 3,59→3,18 ; HP5 1,69→0,96 / 2,94→1,96 ; FP4 2,46→1,86 / 3,21→3,52. L'entraînement baisse presque toujours ; la tenue à part baisse moins et deux fois remonte (Portra, FP4) : surajustement aux deux scènes d'entraînement, en particulier en N&B (courbe seule) où le critère se règle sur la tonalité de deux pièces.
- **Réglages en butée** : un seul, la saturation +3 de Portra (le format ne permet pas plus ; la cible en demande peut-être davantage, comme dans l'analyse §5.2). Les 9 nœuds de courbe restent à moins de 15 codes du v1 (le plus fort : +14,7 sur Portra, +12,7 sur HP5, +10,4 sur Classic Neg, au nœud x = 75 %).
- Ce que l'ajustement ne peut pas toucher : le p90 (blocs de chroma élevée : le vert du pédalier) ne bouge pas ou monte. Une base, une saturation, une teinte et une courbe de luma n'ont pas de correction par teinte (limite du format, `d750-analyse-seances.md` §5.2). Les ajustements gagnent surtout sur la médiane : la luma et l'équilibre global.

## Limites (à lire avant de s'en servir)
1. **Le rendu NX d'un NCP n'est pas celui du boîtier** (mesuré). NX (NCP de la recette v1) contre le JPEG du boîtier, sur la même vue : Classic Chrome 2,10, Classic Neg 1,91, Hasselblad 1,17, Positive 1,30, HP5 1,10, FP4 0,80. NX relisant les réglages du NEF : 0,94, 1,08, 1,30, 1,43, 0,15, 0,20. Écart décomposé, NCP contre NX relisant le NEF, par tiers de luminosité : **L plus sombre de 0,4 à 0,6 en couleur, de 0,6 à 1,6 en N&B ; chroma à 83 % (Classic Chrome), 91 à 96 % (Hasselblad)** de celle du rendu du boîtier. Corollaire direct : pour Classic Chrome le JPEG du boîtier (saturation −1, teinte −2) est mieux imité par un NCP à saturation 0 et teinte −3 (0,73) que par le même −1, −2 (2,08) ; l'ajustement a donc choisi 0 et −2 : **il compense un défaut du NCP dans NX, qui n'existe peut-être pas dans le boîtier**. Causes essayées : la saturation ou la teinte seules (sans courbe, saturation ±3 et teinte ±3 : le NCP suit le boîtier à 0,2 près), la courbe seule (saturation et teinte à 0 : 1,2 contre 1,06). Deux effets, à ne pas confondre : (a) un **décalage de tons dès qu'une courbe passe par le NCP**, y compris en N&B où il n'y a ni saturation ni teinte (HP5 : 0,15 avec le NEF, 1,10 avec le NCP, L de −0,6 à −1,6 par tiers) ; (b) un **déficit de chroma quand courbe et curseurs de couleur sont combinés** (sans courbe, ou courbe seule à saturation 0, le NCP suit le boîtier). Cause réelle inconnue. Pistes non testées : écrire un NP2 (Picture Control 2) au lieu d'un NCP ; la clarté (absente du NCP : HP5 v1 a −1) ; l'ordre courbe / saturation dans le chemin NCP de NX.
2. **NX lit les 20 points d'ancrage d'un NCP, pas la table de 257 valeurs** (mesuré : une table modifiée de 3,7 codes entre les points, ancrages inchangés, rend à l'identique, 0,0 code d'écart). La courbe est donc définie ici par ses 20 points entiers et la table en est tirée (`lut_points`, écart à la table v1 : 0,3 à 0,7 code en moyenne, 4,2 au plus sur FP4). Que le boîtier et NX suivent alors la même courbe est une **hypothèse** : elle suppose que NX interpole les 20 points comme `lut_points`, ce qui n'est pas testé ; le décalage de tons en N&B (limite 1, effet a) suggère que non, et ce point est peut-être la cause de cet effet. Un rendu de contrôle suffirait : NCP à courbe identité contre NCP v1 sur la vue HP5, pour lire la courbe réelle de NX (non fait).
3. **Une seule scène tenue à part, un seul objectif et une seule lumière**, et seulement deux scènes d'entraînement : les écarts de moins de 0,3 ne sont pas à interpréter. Le p90 se dégrade pour Classic Chrome (2,75 → 3,72) et Classic Neg (8,68 → 10,11) : le critère d'ajustement (médiane + ½ p90 sur les scènes d'entraînement) ne protège pas les couleurs vives d'une autre scène.
4. **Pas de quart de point** (curseurs entiers du NCP) ; pas de clarté, pas d'accentuation vraie (sans effet sur des blocs uniformes).
5. **Non faits** : Kodachrome (la cible exige les réponses Status A d'agx-emulsion et les tables spektrafilm : absentes du disque ; je n'ai rien téléchargé sans accord) ; Tri-X (la recette est pensée pour une WB de 10 000 K, les lots d'entraînement sont à 5 600 K : l'ajuster sur eux n'aurait pas de sens). Classic Chrome, Classic Neg, Positive, Hasselblad : cibles de `d750_cibles.py` inchangées.
6. **Les cibles restent des modèles** (LUT Fuji, rendus mesurés, preset acheté, fiches Ilford) : on réduit l'écart au modèle de la cible, pas à un film.
7. Aucune vérification sur le boîtier : ni chargement, ni photographie.

## Ce qui reste à faire (dans l'ordre)
1. Lever la limite n° 1 : un NP2 écrit à la main (ou un NCP sans courbe + courbe par un autre chemin) donne-t-il un rendu NX égal à celui du boîtier ? Test à faire sur 1 à 2 vues à 5 rendus (Classic Chrome, Hasselblad) : l'écart à viser est celui de NX relisant le NEF (0,9 à 1,4). Tant que ce n'est pas fait, un ajustement NX ne vaut que pour NX.
2. Si NX est corrigé : refaire passer les 7 recettes, avec lot3 en entraînement et une autre scène (extérieur ou fenêtre d’octobre) tenue à part, et un critère qui surveille le p90 de la tenue.
3. Seulement ensuite, charger une recette `-nx` dans un emplacement C par `d750_ecrire.swift`, sur décision de Thomas, la photographier et la mesurer avec `mesures_reelles.py` comme les recettes v1.

## Reproduire
`python3 outils/d750_ajuster_nx.py tout` (ou `ajuster classic-chrome positive …`), dans ce dossier, sous `nice -n 10`, un seul SaveProcess à la fois. Temporaires : `$NX_TRAVAIL/ajuster-nx/` (par défaut le dossier temporaire du système) (blocs des lots refaits à la première exécution par `mesures_reelles.extraire`, cache des rendus). Méthode d'ajustement : gerard662/nikon-picture-control-matcher (MIT) ; code écrit ici.

## Passe 2, NP2 (novembre 2026)

**Changement** : le Picture Control imposé à NX est un **NP2** (`picture_control.ecrire_np2`, `nx_rendu.rendre` passe `SavedPicConProcess=1`). Il porte les quarts de point, la clarté et la table de 257 valeurs. Même protocole que la passe 1 : entraînement lot1 + lot4 (BASE STANDARD), tenue à part = vue du test v1 (lot3 exclu), gain radial par NEF ajusté sur « NX tel quel contre JPEG », recette finale arrondie re-rendue pour l'APRÈS. L'option NCP reste dans le script (`fmt='ncp'`).

**Ce qui change dans l'ajustement** : saturation et teinte sont ajustées **au quart de point** dans les bornes de `BORNES_PTP` (±3), dans le même Gauss-Newton que les 9 nœuds de courbe (11 variables en couleur, 9 en N&B ; différences finies : 4 codes, un quart de point) ; plus de tour de voisins entiers. Base et filtre criblés comme avant (Standard et « aucun » restent premiers : HP5 vert 5,82 contre 5,69). 2 itérations au plus, critère médiane + ½ p90. **Mesuré** : NX lit encore les 20 points d'ancrage de la courbe, pas la table, même en NP2 (table modifiée entre les points, rendu identique à 0,0 code) ; les quarts de point agissent (0,66 code d'écart moyen pour 0,25 point de saturation).

### Preuve que le chemin reproduit le boîtier (vue tenue à part, médiane ΔE2000 contre le JPEG du boîtier, p90 entre parenthèses)

| Recette | NX v1 (NP2) | NX tel quel (NEF) | NCP v1 (passe 1) | NP2 de la recette réellement chargée |
|---|---|---|---|---|
| Classic Chrome | 0,98 (2,32) | 0,94 (2,32) | 2,10 (2,50) | 0,94 |
| Classic Neg | 1,16 (2,53) | 1,08 (2,56) | 1,91 (2,74) | 1,08 |
| Positive | 1,47 (2,86) | 1,43 (2,87) | 1,30 (3,99) | 1,43 |
| Hasselblad | 1,31 (2,59) | 1,30 (2,58) | 1,17 (2,89) | 1,30 |
| Portra (v2 écrite, ≠ vue) | 5,08 (non comparable) | 1,33 | 4,41 | **1,33 (2,91)** |
| HP5+ | 0,32 (0,61) | 0,15 (0,40) | 1,10 (1,93) | 0,15 |
| FP4+ | 0,33 (0,95) | 0,20 (0,72) | 0,80 (1,36) | 0,20 |

Le NP2 rend la recette comme le NEF qui la porte (colonnes 2 et 5 égales aux centièmes), le biais du NCP en couleur disparaît (Classic Chrome 2,10 → 0,98, Classic Neg 1,91 → 1,16) et le N&B devient presque exact (0,15 à 0,33). **Reste un plancher de 1,0 à 1,5 ΔE en couleur** entre NX et le JPEG, présent aussi avec NX tel quel : ce n'est pas le chemin NP2 mais le moteur de NX contre le boîtier (vignetage, bruit, version des bases : cause non cherchée). Pour Portra, la vue a été prise avec la v1 : la preuve se fait avec la recette réellement chargée (`blocs/08.bin`), qui tombe à 1,33.

### Résultat de l'ajustement (vue tenue à part, médiane ΔE2000 contre la cible, p90 entre parenthèses)

| Recette | Boîtier v1 | NX v1 (NP2) | NX ajusté (NP2) | Rendus | Réglages v1 → ajusté (saturation, teinte) | En butée | Verdict |
|---|---|---|---|---|---|---|---|
| Classic Chrome | 1,56 (3,79) | 2,00 (3,67) | **1,38 (3,56)** | 57 | −1, −2 → −1,25, −3 | teinte −3 | plausible |
| Classic Neg | 3,67 (10,05) | 4,17 (10,36) | **3,33 (9,22)** | 57 | 0, 0 → −0,75, −1,5 | aucun | modeste, plausible |
| Positive | 3,21 (5,53) | 3,47 (5,31) | **2,20 (4,93)** | 57 | +2, −2 → +1,5, −3 | teinte −3 | meilleur résultat |
| Hasselblad | 2,60 (4,75) | 1,35 (5,03) | 1,13 (5,21) | 57 | +1, −3 → +1, −3 | teinte −3 | non significatif |
| Portra (v2 écrite) | n.c. | 2,99 (5,99) | **1,88 (5,58)** | 57 | +3, +2 → +3, −0,75 | saturation +3 | plausible |
| HP5+ | 2,66 (11,49) | 2,76 (11,93) | 2,39 (12,50) | 53 | courbe seule | aucun | marginal |
| FP4+ | 2,46 (15,61) | 2,45 (16,69) | 3,40 (15,73) | 53 | courbe seule | aucun | **pire, garder la v1** |

- Rendus de la passe 2 : 391 (≈ 800 pour toute la séance avec la passe 1 : la contrainte de ~500 vaut pour cette passe). Entraînement, médiane avant → après (lot1 / lot4) : Classic Chrome 2,47→1,87 / 1,51→1,29 ; Classic Neg 4,81→3,95 / 4,81→4,99 ; Positive 2,75→1,96 / 2,78→1,95 ; Hasselblad 1,42→1,38 / 2,79→2,69 ; Portra 4,34→2,07 / 3,22→2,94 ; HP5 1,68→1,01 / 3,29→2,16 ; FP4 2,49→1,81 / 2,94→3,66.
- Courbe : nœuds à moins de 15 codes de la v1 (le plus fort +13 sur Portra, +14 sur HP5, au nœud x = 75 %) ; aucun nœud en butée. Butées : la **teinte −3** pour Classic Chrome, Positive et Hasselblad (le moteur voudrait plus de décalage), la saturation +3 de Portra.
- Lecture : en couleur l'ajustement apporte 0,2 à 1,3 ΔE sur la médiane, dans le sens attendu, alors que le plancher NX/boîtier est de 1,0 à 1,5 : le gain est réel dans NX, vraisemblable pour le boîtier mais pas démontré (le plancher est un biais d'un seul sens sur une scène, mais on ne l'a pas mesuré recette par recette sur les recettes ajustées). En N&B, où NX reproduit le boîtier à 0,15–0,33, les chiffres valent pour le boîtier : HP5 gagne peu (et le p90 monte), FP4 perd (surajustement à deux scènes). Le p90 ne baisse nettement que pour Positive et Classic Neg : les couleurs vives restent hors de portée d'un Picture Control (§5.2).
- Surajustement : une scène tenue à part seulement, deux d'entraînement, aucune validation croisée : les écarts sous 0,3 (Hasselblad, HP5) ne sont pas à interpréter.
- Non faits (inchangé) : Kodachrome (cible absente du disque), Tri-X (WB 10 000 K).
- **Avant tout chargement** : photographier une recette `-nx` (Positive d'abord) sur la même scène que le test v1 et la mesurer par `mesures_reelles.py`. Les recettes `usb/<recette>-nx.json` s'écrivent au format v1 (quarts de point dans `reglages`) et se chargent par `d750_ecrire.swift` ; les `.NP2` sont ceux que NX a rendus.
