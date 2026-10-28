# Rétro-ingénierie boîtiers

**Donner une seconde vie aux vieux boîtiers : leur faire sortir, en JPEG direct, les rendus qu'on aime.**

Classic Chrome, Tri-X, HP5, Portra, Kodachrome, rendu Hasselblad, Positive du Ricoh… D'habitude, il faut acheter le boîtier qui les a, ou passer chaque photo dans Lightroom. Ce dépôt montre comment je les ai recréés dans trois vieux Nikon et un Pentax 645D, et donne la méthode pour le refaire sur un autre appareil :

- **Nikon D40** (2006) : son firmware a été cartographié, émulé sur le Mac puis modifié. Cinq looks remplacent les préréglages d'Optimiser l'image, avec un menu façon Pip-Boy ([captures de l'émulateur](d40/README.md#le-menu-pip-boy)) et de vrais programmes d'exposition. C'est la **V5**, flashée et utilisée sur mon boîtier.
- **Nikon D200** (2005) : même démarche que le D40, firmware modifié par données seulement. Cinq entrées d'Optimiser l'image deviennent Chrome, Positive, FP4, HP5 et Tri-X, menus en français ; son étage de couleur à 16 secteurs a été décodé en photographiant une roue de teintes. Flashé et validé sur mon boîtier.
- **Nikon D750** (2014) : on ne touche pas au firmware. Neuf Picture Control sont calculés et chargés **par USB** dans C-1 à C-9 ; l'ordinateur pilote le boîtier pendant les séances d'essai (écrire un réglage, déclencher, rapatrier NEF et JPEG, mesurer).
- **Pentax 645D** (2010) : moyen format, firmware seulement lu, jamais modifié. Quatre looks (Classic Chrome, Portra 400, Tri-X, HP5) sont chargés **par USB** dans son Custom Image, par une commande constructeur que l'on n'avait jamais pilotée.

Le principe est le même dans chaque cas : on mesure le rendu visé, on mesure ce que le boîtier sait faire, puis on calcule le réglage le plus proche et on le vérifie sur de vraies photos. La mesure est un écart de couleur perçu, le ΔE2000.

<img src="vues/comparaison/classic-chrome-4-appareils.jpg" width="800" alt="Le même cheval à ressort photographié par quatre appareils réglés sur le Classic Chrome">

*Quatre appareils qui visent le Classic Chrome : je vous mets au défi de dire quelle photo sort de quel appareil. JPEG sortis du boîtier, exposition et balance égalisées sur le gris du cheval pour compenser les éclaircies pendant la prise de vue.*

Le dépôt est fait pour être **donné à une IA** (Claude Code, Codex, Cursor…) avec la consigne « reproduis ceci sur mon boîtier » : voir [`AGENTS.md`](AGENTS.md) et [`METHODE.md`](METHODE.md).

> Auteur : Thomas Hammoudi, photographe. Travail fait avec Claude Code, en octobre 2026. Les textes sont en français.

## Télécharger

- **D40, V5 prête à flasher** (firmware Nikon modifié, fourni pour commodité, sans garantie ; droits de Nikon réservés) : [`d40-v5.zip`](https://github.com/ThomasHMD/retro-ingenierie-boitiers/releases/download/d40-v5/d40-v5.zip) (A 1.12 et B 1.11 modifiés, empreintes dans `SHA256SUMS.txt`). Ou la refaire soi-même depuis le firmware officiel : [`d40/README.md`](d40/README.md).
- **D200, firmware prêt à flasher** (même avertissement) : [`d200-v2.zip`](https://github.com/ThomasHMD/retro-ingenierie-boitiers/releases/download/d200-v2/d200-v2.zip) (B 2.01 modifié, empreinte dans `SHA256SUMS.txt`). Ou la refaire depuis le firmware officiel : [`d200/README.md`](d200/README.md).
- **D750, les neuf Picture Control** : dans le dépôt, [`d750/recettes/d750-v1/`](d750/recettes/d750-v1/README.md), à charger par USB : [`d750/README.md`](d750/README.md).
- **645D, les quatre recettes** : [`645d/recettes/`](645d/recettes/recettes-645d.json), à charger par USB : [`645d/README.md`](645d/README.md).

## Ce que ça fait

Un appareil enregistre deux fichiers à chaque déclenchement : le RAW, ce que le capteur a vu, et le JPEG, l'image qu'il fabrique à partir du RAW selon sa recette de couleurs (le Picture Control, chez Nikon). Pour chaque look, je calcule depuis le RAW à quoi la photo ressemblerait avec le film ou le boîtier imité : c'est la **cible**. Je cherche ensuite les réglages du Picture Control qui en rapprochent le plus le JPEG, je les envoie dans l'appareil par USB, puis je photographie la même scène et je compare le **JPEG sorti du boîtier** à la cible, zone par zone (ΔE : sous 2, la différence ne se voit que côte à côte et avec un œil exercé ; au-delà de 5, ce n'est plus tout à fait le même rendu). Un Picture Control change toutes les couleurs d'un coup, sans pouvoir en toucher une seule : certains looks s'imitent mieux que d'autres.

Ci-dessous, le D750 sur deux scènes d’octobre 2026, chaque look à sa balance des blancs. Ce sont des JPEG de démonstration, au même cadrage dans chaque ligne.

### La bibliothèque

Lumière du jour et LED à 5 600 K, 28 mm. L'image de départ, le JPEG du D750 en Standard, sans recette :

<img src="vues/bibliotheque/depart-standard.jpg" width="600" alt="départ : JPEG du D750 en Standard, bibliothèque">

| Look | Cible, calculée depuis le RAW | JPEG sorti du boîtier |
|---|---|---|
| **Kodachrome**<br>6 250 K<br>ΔE 3,4<br><sub>film modeling powered by spektrafilm</sub> | <img src="vues/bibliotheque/cible-kodachrome.jpg" width="300" alt="cible Kodachrome"> | <img src="vues/bibliotheque/boitier-kodachrome.jpg" width="300" alt="JPEG du boîtier, Kodachrome"> |
| **Classic Chrome**<br>5 600 K<br>ΔE 1,8 | <img src="vues/bibliotheque/cible-classic-chrome.jpg" width="300" alt="cible Classic Chrome"> | <img src="vues/bibliotheque/boitier-classic-chrome.jpg" width="300" alt="JPEG du boîtier, Classic Chrome"> |
| **Classic Neg**<br>5 600 K<br>ΔE 5,1 | <img src="vues/bibliotheque/cible-classic-neg.jpg" width="300" alt="cible Classic Neg"> | <img src="vues/bibliotheque/boitier-classic-neg.jpg" width="300" alt="JPEG du boîtier, Classic Neg"> |
| **Positive**<br>5 600 K<br>ΔE 2,9 | <img src="vues/bibliotheque/cible-positive.jpg" width="300" alt="cible Positive"> | <img src="vues/bibliotheque/boitier-positive.jpg" width="300" alt="JPEG du boîtier, Positive"> |
| **Portra 400**<br>5 600 K<br>ΔE 4,6<br><sub>d'après un preset acheté que j'aimais beaucoup</sub> | <img src="vues/bibliotheque/cible-portra-400.jpg" width="300" alt="cible Portra 400"> | <img src="vues/bibliotheque/boitier-portra-400.jpg" width="300" alt="JPEG du boîtier, Portra 400"> |
| **Hasselblad**<br>5 600 K<br>ΔE 2,5 | <img src="vues/bibliotheque/cible-hasselblad.jpg" width="300" alt="cible Hasselblad"> | <img src="vues/bibliotheque/boitier-hasselblad.jpg" width="300" alt="JPEG du boîtier, Hasselblad"> |
| **Tri-X**<br>10 000 K<br>ΔE 1,2<br><sub>d'après un preset acheté que j'aimais beaucoup</sub> | <img src="vues/bibliotheque/cible-tri-x.jpg" width="300" alt="cible Tri-X"> | <img src="vues/bibliotheque/boitier-tri-x.jpg" width="300" alt="JPEG du boîtier, Tri-X"> |
| **HP5+**<br>5 600 K<br>ΔE 3,2 | <img src="vues/bibliotheque/cible-hp5.jpg" width="300" alt="cible HP5+"> | <img src="vues/bibliotheque/boitier-hp5.jpg" width="300" alt="JPEG du boîtier, HP5+"> |
| **FP4+**<br>5 600 K<br>ΔE 2,6 | <img src="vues/bibliotheque/cible-fp4.jpg" width="300" alt="cible FP4+"> | <img src="vues/bibliotheque/boitier-fp4.jpg" width="300" alt="JPEG du boîtier, FP4+"> |

### La vue par la fenêtre

Bâtiment et ciel, 50 mm sur trépied, exposition calée sur le ciel. Les premières vues d'extérieur, prises à main levée en balance des blancs automatique, donnaient un ciel bizarre : jusqu'à 10 de ΔE pour le Kodachrome. Refaite dans les règles, chaque Picture Control à la balance des blancs pour laquelle il a été calculé, la scène tient (Kodachrome à 4,1, noir et blanc autour de 1), et le calcul prévoit le JPEG de l'appareil à 0,4 à 1,4 près, même dans le ciel. Le ciel bizarre venait de la balance automatique, pas des recettes. Départ :

<img src="vues/fenetre/depart-standard.jpg" width="300" alt="départ : JPEG du D750 en Standard, vue par la fenêtre">

| Look | Cible, calculée depuis le RAW | JPEG sorti du boîtier |
|---|---|---|
| **Kodachrome**<br>6 250 K<br>ΔE 4,1<br><sub>film modeling powered by spektrafilm</sub> | <img src="vues/fenetre/cible-kodachrome.jpg" width="220" alt="cible Kodachrome"> | <img src="vues/fenetre/boitier-kodachrome.jpg" width="220" alt="JPEG du boîtier, Kodachrome"> |
| **Classic Chrome**<br>5 600 K<br>ΔE 3,4 | <img src="vues/fenetre/cible-classic-chrome.jpg" width="220" alt="cible Classic Chrome"> | <img src="vues/fenetre/boitier-classic-chrome.jpg" width="220" alt="JPEG du boîtier, Classic Chrome"> |
| **Classic Neg**<br>5 600 K<br>ΔE 6,3 | <img src="vues/fenetre/cible-classic-neg.jpg" width="220" alt="cible Classic Neg"> | <img src="vues/fenetre/boitier-classic-neg.jpg" width="220" alt="JPEG du boîtier, Classic Neg"> |
| **Positive**<br>5 600 K<br>ΔE 2,1 | <img src="vues/fenetre/cible-positive.jpg" width="220" alt="cible Positive"> | <img src="vues/fenetre/boitier-positive.jpg" width="220" alt="JPEG du boîtier, Positive"> |
| **Portra 400**<br>5 600 K<br>ΔE 3,0<br><sub>d'après un preset acheté que j'aimais beaucoup</sub> | <img src="vues/fenetre/cible-portra-400.jpg" width="220" alt="cible Portra 400"> | <img src="vues/fenetre/boitier-portra-400.jpg" width="220" alt="JPEG du boîtier, Portra 400"> |
| **Hasselblad**<br>5 600 K<br>ΔE 3,1 | <img src="vues/fenetre/cible-hasselblad.jpg" width="220" alt="cible Hasselblad"> | <img src="vues/fenetre/boitier-hasselblad.jpg" width="220" alt="JPEG du boîtier, Hasselblad"> |
| **Tri-X**<br>10 000 K<br>ΔE 1,1<br><sub>d'après un preset acheté que j'aimais beaucoup</sub> | <img src="vues/fenetre/cible-tri-x.jpg" width="220" alt="cible Tri-X"> | <img src="vues/fenetre/boitier-tri-x.jpg" width="220" alt="JPEG du boîtier, Tri-X"> |
| **HP5+**<br>5 600 K<br>ΔE 1,0 | <img src="vues/fenetre/cible-hp5.jpg" width="220" alt="cible HP5+"> | <img src="vues/fenetre/boitier-hp5.jpg" width="220" alt="JPEG du boîtier, HP5+"> |
| **FP4+**<br>5 600 K<br>ΔE 1,2 | <img src="vues/fenetre/cible-fp4.jpg" width="220" alt="cible FP4+"> | <img src="vues/fenetre/boitier-fp4.jpg" width="220" alt="JPEG du boîtier, FP4+"> |

> **La balance des blancs fait partie de la recette : toujours en Kelvin, jamais en Auto.** Kodachrome **6 250 K**, Tri-X **10 000 K** (en noir et blanc aussi : la balance change le mélange des couleurs en gris), tous les autres **5 600 K**. En Auto, l'appareil déplace les couleurs à chaque photo et le look ne ressemble plus à sa cible.

Chiffres complets (p90, prévu contre mesuré, lumière mêlée) : [`d750/recherche/resultats-mesures.md`](d750/recherche/resultats-mesures.md) ; refaire les images : `d750/outils/figures_page_blog.py`.

### Le Nikon D200, en simulation

Simulation : mes photos du D200 en RAW, passées dans les tables du firmware modifié. Ce calcul retombe sur le JPEG du boîtier, au plancher de la mesure près ([`d200/README.md`](d200/README.md)). La roue de teintes montre le mieux l'écart entre Chrome et Positive.

| Normal (Nikon, d'origine) | Chrome | Positive |
|---|---|---|
| <img src="vues/d200/normal-interieur.jpg" width="250" alt="D200, normal interieur, simulation"> | <img src="vues/d200/chrome-interieur.jpg" width="250" alt="D200, chrome interieur, simulation"> | <img src="vues/d200/positive-interieur.jpg" width="250" alt="D200, positive interieur, simulation"> |
| <img src="vues/d200/normal-roue.jpg" width="250" alt="D200, normal roue, simulation"> | <img src="vues/d200/chrome-roue.jpg" width="250" alt="D200, chrome roue, simulation"> | <img src="vues/d200/positive-roue.jpg" width="250" alt="D200, positive roue, simulation"> |

| Noir et blanc (Nikon, d'origine) | Tri-X : papier dur | HP5 : papier doux, noirs mats | FP4 : contraste moyen |
|---|---|---|---|
| <img src="vues/d200/nb-nikon-interieur.jpg" width="190" alt="D200, nb nikon interieur, simulation"> | <img src="vues/d200/tri-x-interieur.jpg" width="190" alt="D200, tri x interieur, simulation"> | <img src="vues/d200/hp5-interieur.jpg" width="190" alt="D200, hp5 interieur, simulation"> | <img src="vues/d200/fp4-interieur.jpg" width="190" alt="D200, fp4 interieur, simulation"> |

### Le Pentax 645D, sur le pédalier

Même scène au trépied (45 mm, balance Auto), seul le Custom Image change d'une vue à l'autre. Le 645D enregistre dans chaque PEF un JPEG pleine taille rendu avec ses réglages : ce sont ces JPEG, réduits. Les écarts de la couleur sont mesurés contre les cibles du D750 ; en noir et blanc, contre les courbes des films.

| Look | Réglages au menu | JPEG sorti du boîtier |
|---|---|---|
| **Classic Chrome**<br>ΔE 1,9 | Naturel, teinte −2 | <img src="vues/pedalier/boitier-classic-chrome.jpg" width="300" alt="645D, Classic Chrome"> |
| **Portra 400**<br>ΔE 2,3<br><sub>d'après un preset acheté que j'aimais beaucoup</sub> | Lumineux, tout à 0 ; exposer −⅓ à −½ IL (ΔE contre le preset seul) | <img src="vues/pedalier/boitier-portra-400.jpg" width="300" alt="645D, Portra 400"> |
| **Tri-X 400**<br>écart 6,7 → 4,2 | Recette : Monochrome, filtre aucun, contraste +3. Vue : contraste +2 (seuls +2 et +4 ont été photographiés) | <img src="vues/pedalier/boitier-tri-x-400.jpg" width="300" alt="645D, Tri-X 400, contraste +2"> |
| **HP5 Plus**<br>écart 9,8 → 3,3 | Recette : Monochrome, filtre cyan, contraste +4. Vue : filtre cyan, contraste 0 | <img src="vues/pedalier/boitier-hp5-plus.jpg" width="300" alt="645D, HP5 Plus, filtre cyan"> |

En noir et blanc, le défaut du Monochrome d'origine est sa courbe trop plate : l'écart au film, en niveaux de gris sur 255, passe de 6,7 à 4,2 pour Tri-X et de 9,8 à 3,3 pour HP5 entre contraste 0 et +4 ; le filtre cyan rapproche HP5. La balance des blancs, elle, ne se règle pas par USB sur ce boîtier. Détail : [`645d/README.md`](645d/README.md) ; refaire les images : `645d/outils/645d_vues_demo.py`.

## Ce qui est fourni

| | Contenu |
|---|---|
| [`METHODE.md`](METHODE.md) | La méthode générale, d'un boîtier à l'autre : choisir les cibles, mesurer, modéliser le boîtier, calculer, vérifier dans une boucle d'essais |
| [`AGENTS.md`](AGENTS.md) ([`CLAUDE.md`](CLAUDE.md)) | La consigne pour une IA : « reproduis ceci sur ton boîtier », avec les garde-fous |
| [`d40/`](d40/README.md) | Comment on a fait (carte du firmware, émulateur, patchs des tables de couleur), `patch.py` et les patchs, `fabriquer_v5.py`, qui refait la V5 à partir du firmware officiel de Nikon, la procédure de flash et ses limites |
| [`d200/`](d200/README.md) | Le simulateur et les patchs des tables de rendu, l'étage couleur à 16 secteurs décodé, l'émulateur du moteur d'image, la V2 à refaire depuis le firmware officiel, la procédure de flash et de retour |
| [`d750/`](d750/README.md) | Les outils de pilotage USB (lire, écrire, effacer un Picture Control ; séances d'essai automatiques), les scripts d'analyse et de mesure, les neuf recettes chargées (`.json` et blocs), la procédure (séances, balance des blancs, préréglages d-1 à d-6) |
| [`645d/`](645d/README.md) | Le pilotage USB du Custom Image (poignée de main constructeur, écrire, déclencher, rapatrier), la mesure des filtres et des courbes, les quatre recettes et leurs plans de chargement, les outils de lecture du firmware |
| Releases [`d40-v5`](https://github.com/ThomasHMD/retro-ingenierie-boitiers/releases) et `d200-v2` | Les fichiers de la V5 du D40 (A 1.12 et B 1.11 modifiés) et de la V2 du D200 (B 2.01 modifié) prêts à flasher, pour qui ne veut pas les fabriquer |

## Les looks

| Look | D40 (V5, préréglage) | D750 (Picture Control) | Cible |
|---|---|---|---|
| Kodachrome | | C-1, à 6 250 K | simulation spectrale de la Kodachrome 64 (spektrafilm), chroma × 1,2 |
| Classic Chrome | Vivid | C-2 | JPEG d'un Fujifilm X-T4 (D40), LUT officielle Fujifilm (D750) |
| Classic Neg | | C-3 | LUT officielle Fujifilm |
| Positive | More Vivid | C-4 | paires RAW + JPEG d'un Ricoh GR III |
| Portra 400 | | C-5 | « esprit Portra » : entre mes scans de Portra 400 et un preset acheté que j'aimais beaucoup |
| Hasselblad | Soft | C-6 | paires RAW + JPEG d'un Hasselblad X2D (HNCS) |
| Tri-X | Portrait | C-7, à 10 000 K | d'après un preset acheté que j'aimais beaucoup, contrôlé sur la fiche Kodak |
| HP5+ | Black And White | C-8 | fiche Ilford (sensibilité spectrale, tirage grade 2) |
| FP4+ | | C-9 | fiche Ilford |

Les cibles sont des rendus que j'aime, pas des vérités : une HP5 change selon le scan, le développement et le traitement. La méthode permet de viser les siens.

## Écarts mesurés

ΔE2000 entre le JPEG sorti du boîtier et la cible du look, sur les zones uniformes de l'image (la scène étant lue dans le NEF de la même photo). **Médiane** : l'écart de la zone typique ; **p90** : celui des 10 % de zones les plus difficiles. Repères : sous 2, visible seulement côte à côte par un œil exercé ; 2 à 3, visible côte à côte ; au-delà de 5, ce n'est plus tout à fait le même rendu.

| Look | Boîtier | Médiane | p90 | Vues mesurées |
|---|---|---|---|---|
| Classic Chrome | D40 | 1,4 | 2,7 | 1 (cible X-T4 ; 3,6 contre la LUT Fujifilm) |
| Positive | D40 | 1,6 | 2,8 | 3 |
| Hasselblad | D40 | 2,7 | 3,8 | 1 |
| Tri-X | D40 | 0,5 | 2,8 | 4 |
| HP5+ | D40 | 2,7 | 4,6 | 11 |
| Kodachrome | D750 | 3,4 | 6,2 | 1 scène (cible spektrafilm Kodachrome 64, à 6 250 K) |
| Classic Chrome | D750 | 1,8 | 3,0 | 1 scène (cible : LUT Fujifilm) |
| Classic Neg | D750 | 5,1 | 6,9 | 1 scène (cible : LUT Fujifilm) |
| Positive | D750 | 2,9 | 4,8 | 1 scène |
| Portra 400 | D750 | 4,6 | 6,3 | 1 scène (cible : « esprit Portra », le preset Portra réglé) |
| Hasselblad | D750 | 2,5 | 4,0 | 1 scène |
| Tri-X | D750 | 1,2 | 1,7 | 1 scène (Tri-X v2, à 10 000 K) |
| HP5+ | D750 | 3,2 | 6,7 | 1 scène |
| FP4+ | D750 | 2,6 | 7,4 | 1 scène |

**Sur les 14 looks mesurés, 10 ont une médiane sous 3, et aucun ne dépasse 5,1.** Au D750, ce sont les neuf Picture Control tels qu'ils sont dans le boîtier (Tri-X v2 compris), photographiés en octobre 2026 sur une scène, une bibliothèque, sous une seule lumière (jour et LED à 5 600 K), et mesurés sur les mêmes 4 675 zones pour tous les looks. Le boîtier fait ce que le modèle prévoit (modèle contre JPEG : 0,9 à 1,9, Portra 2,5) : les écarts restants viennent des recettes et du format. Sous une lumière mêlée (jour et lampe chaude), HP5 et FP4 montent à 5,2 et 5,4. Une deuxième scène, la vue par une fenêtre (bâtiment et ciel, sur trépied), donne de 1,0 (HP5+) à 6,3 (Classic Neg) : images plus haut, « Ce que ça fait ». Le 645D (Classic Chrome 1,9, Portra 2,3, sur un pédalier peu coloré) est à part : [`645d/README.md`](645d/README.md). Les chiffres du D40 valent pour la V5 publiée (mêmes tables que la version photographiée, vérifié à l'octet).

Réserves, à garder en tête :
- peu de vues : une à onze par look au D40, deux scènes au D750, une bibliothèque (chiffres du tableau) et la vue par une fenêtre (Classic Neg et Portra dépendent beaucoup du contenu de la scène, HP5 et FP4 de la lumière) ;
- la « cible » est le rendu de référence choisi pour chaque look ; pour le Classic Chrome, le JPEG du X-T4 et la LUT de Fujifilm sont eux-mêmes à 3,9 l'un de l'autre ;
- seules les zones uniformes comptent : ni texture, ni netteté, ni grain ;
- le p90 suit les couleurs les plus vives : au D750, il passe de 1,7 (Tri-X) à 7,4 (FP4).

Ce qui ne descend pas, et pourquoi : un Picture Control du D750 n'a que des réglages globaux (une base, un gain et une rotation de couleur pour toutes les teintes à la fois, une courbe sur la luminosité). Il ne sait pas changer une couleur sans toucher les autres : Classic Neg, Positive et Portra butent là-dessus. Le D40, lui, a dans son firmware des matrices, des courbes et une correction par secteur de teinte : ses écarts restants sont des réglages, corrigeables. Le détail : [`d750/recherche/resultats-mesures.md`](d750/recherche/resultats-mesures.md).

## Démarrer

- **J'ai un D40** : [`d40/README.md`](d40/README.md). Télécharger les deux firmwares officiels chez Nikon, `python3 d40/fabriquer_v5.py <A 1.12> <B 1.11>`, vérifier les empreintes, flasher A puis B. Ou prendre les fichiers de la release.
- **J'ai un D200** : [`d200/README.md`](d200/README.md). Télécharger la mise à jour 2.01 chez Nikon, `python3 d40/patch.py d200/patchs/d200-v2.json`, vérifier l'empreinte, préparer une carte de retour, flasher le B. Ou prendre le fichier de la release.
- **J'ai un D750** : [`d750/README.md`](d750/README.md). Les neuf recettes se chargent par USB depuis un Mac (`picture_control.py bloc` puis `d750_ecrire.swift`, simulation par défaut).
- **J'ai un 645D** : [`645d/README.md`](645d/README.md). Les quatre recettes se chargent par USB depuis un Mac (`645d_seance.swift`, état sauvé avant, remis à la demande).
- **J'ai un autre boîtier** : donner ce dépôt à son IA avec [`AGENTS.md`](AGENTS.md). La plupart des boîtiers récents ont un équivalent du Picture Control (recettes Fujifilm, Custom Image Pentax, Image Control Ricoh…) ; certains vieux boîtiers ont un firmware ouvert à l'étude, comme le D40.

Prérequis : Python 3.10 ou plus (`pip install -r requirements.txt`) ; pour le D750, un Mac (les outils USB sont en Swift, avec ImageCaptureCore) ; pour l'émulateur du D40, un JDK 17 ou plus et `git`.

## Cadre légal

- **Le dépôt git ne contient aucun octet du firmware de Nikon.** Chacun télécharge le firmware officiel chez Nikon, et le patch s'y applique. Les patchs du D40 et du D200 ne contiennent pas les octets d'origine, seulement leur empreinte sha256 (pour vérifier qu'on part du bon fichier) et nos remplacements ; certains remplacements reprennent toutefois, modifiés, des éléments de Nikon : les tables françaises des menus et des aides, reconstruites ailleurs dans le fichier avec nos textes en plus (environ 32 Ko), une planche de caractères recopiée avec 13 glyphes ajoutés aux 21 d'origine, et les en-têtes du JPEG de fond de l'écran d'infos (remplacé par un fond noir). Le fichier `d40/recettes/v1/nikon.json` (copié dans `d750/recettes/v1/`) contient les tables couleur d'usine du D40 décodées (6 matrices, une courbe, les secteurs), qui servent de référence aux calculs : ce sont des données de Nikon, gardées parce que les calculs en ont besoin, et sur ces tables aussi les droits de Nikon restent à Nikon. Le pseudo-code décompilé n'est pas publié : `d40/desassemblage/regenerer.sh` le refait chez soi.
- **Les releases proposent en plus, pour commodité, la V5 du D40 et le firmware du D200 déjà patchés**, pour des boîtiers de près de vingt ans, sans aucune garantie. C'est un firmware Nikon modifié : sur ce fichier, les droits de Nikon restent à Nikon.
- **Les rendus sont analysés, puis portés sur d'autres appareils, sans reprendre le code des fabricants.** Aucune table, LUT ni profil d'un tiers n'est redistribué (LUT Fujifilm, presets Lightroom, tables spektrafilm) : on les mesure, et on publie le réglage calculé pour un autre boîtier. Pour le Tri-X et le Portra, la cible est un preset acheté que j'aimais beaucoup (« le preset Tri-X », « le preset Portra » dans les notes) : on imite son rendu pour un usage très particulier, le JPEG direct d'un boîtier ; aucun fichier ni code de ce preset n'est redistribué. Où trouver chaque source, et sous quelle licence : [`LICENCES-TIERS.md`](LICENCES-TIERS.md).
- **Le D750 n'est jamais modifié** : les Picture Control s'écrivent par la commande USB que Nikon prévoit pour ses propres logiciels, dans les emplacements de l'utilisateur.
- Flasher un firmware modifié se fait **à ses risques** : il peut rendre un boîtier inutilisable, et il fait sans doute tomber la garantie (un D40 n'en a plus depuis longtemps). Lire [`d40/README.md`](d40/README.md) ou [`d200/README.md`](d200/README.md) avant.

## Licence

Mon travail (textes, outils, recettes, patchs) est sous **[CC BY-NC-SA 4.0](LICENSE)** : vous pouvez le reprendre et le modifier en citant l'auteur, sans usage commercial, et en partageant vos versions aux mêmes conditions. Exceptions, qui gardent la licence de leur origine : l'émulateur du D40 (`d40/emulateur/java/` et la configuration du désassembleur), bâti sur nikon-firmware-tools, est sous GPL-3.0 ; un script Ghidra repris de ghidra-fr60 est sous Apache 2.0. Détail : [`LICENCES-TIERS.md`](LICENCES-TIERS.md).

Nikon, D40, D750, Picture Control, Fujifilm, Classic Chrome, Kodak, Kodachrome, Tri-X, Portra, Ilford, HP5, FP4, Hasselblad et Ricoh sont des marques de leurs propriétaires. Ce projet n'est lié à aucun d'eux.
