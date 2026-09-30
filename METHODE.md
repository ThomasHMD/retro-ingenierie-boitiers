# La méthode, d'un boîtier à l'autre

Ce document décrit la démarche suivie sur le D40 et le D750, écrite pour qu'une IA (ou une personne patiente) la rejoue sur un autre boîtier. Les deux cas réels servent d'exemples, avec leurs fichiers. La consigne de travail pour une IA est dans [`AGENTS.md`](AGENTS.md).

Le but : **un JPEG sorti du boîtier aussi proche que possible d'un rendu qu'on aime**, mesuré, pas jugé à l'œil seul.

## 0. Ce que le boîtier laisse régler

Tout commence par l'inventaire de ce qui est réglable, et par quelle voie. Trois familles, de la plus sûre à la plus risquée :

| Voie | Exemple | Ce qu'on peut changer | Risque |
|---|---|---|---|
| **Réglages du menu** | recettes Fujifilm, Custom Image Pentax, Image Control Ricoh, Picture Control Nikon réglé à la main | quelques crans (saturation, teinte, contraste, netteté, filtre N&B) | aucun |
| **Réglages par USB ou par fichier** | Picture Control du D750 par la commande PTP 0x90CD, fichiers `.NCP` sur la carte, courbe perso du D40 (0x90C6) | les mêmes, plus une courbe libre (257 points au D750), plus vite et sans erreur de saisie | très faible : un emplacement de l'utilisateur, effaçable |
| **Firmware** | D40 : tables de matrices, de courbes et de secteurs de teinte, code des préréglages | presque tout ce que fait la chaîne de traitement d'image | réel : un boîtier qui ne démarre plus |

Sources pour cet inventaire : le manuel, les menus du boîtier, la table des commandes USB (libgphoto2, documents du SDK du fabricant, le firmware lui-même), les projets existants (Nikon Hacker, Magic Lantern, Nikon Patch…). Exemples : [`d750/recherche/d750-picture-control-usb.md`](d750/recherche/d750-picture-control-usb.md) (format exact du bloc Picture Control, lu dans le firmware), [`d40/CARTE.md`](d40/CARTE.md) (carte du firmware du D40).

**Règle** : prendre la voie la moins risquée qui suffit. Le D750 n'a jamais été modifié ; le D40 n'avait pas d'autre voie pour des couleurs (son mode Personnalisé ne règle que trois crans de saturation et une courbe).

## 1. Choisir les cibles

Une cible est une fonction : couleur de la scène → couleur rendue. Il faut pouvoir la calculer pour n'importe quelle couleur. Les sources possibles, toutes utilisées ici :

| Source | Ce qu'on en tire | Exemples |
|---|---|---|
| **Paires RAW + JPEG d'un autre boîtier** | un modèle du rendu (matrice, courbe, correction par teinte) ajusté sur des milliers de zones | Hasselblad X2D (HNCS), Ricoh GR III (Positive), Fujifilm X-T4 (Classic Chrome) : [`d40/outils/rendus.py`](d40/outils/rendus.py), résultats dans [`d40/recettes/mesures/`](d40/recettes/mesures/) |
| **LUT officielles** | le rendu lui-même, en 3D | LUT F-Log2 de Fujifilm pour Classic Chrome et Classic Neg ([`d750/outils/fuji_lut.py`](d750/outils/fuji_lut.py) ; les LUT se téléchargent chez Fujifilm) |
| **Réglages Lightroom analysés** | un profil ou un preset appliqué à des RAW, exporté, puis mesuré sur les paires RAW + export | Tri-X et Portra d'après des profils du commerce ([`d40/outils/films_nb.py`](d40/outils/films_nb.py) `paires`, [`d750/outils/d750_cibles.py`](d750/outils/d750_cibles.py)) ; on publie le réglage calculé, jamais le profil |
| **Scans de ses propres films** | la tonalité qu'on aime vraiment (centiles de clarté, dominante des neutres) | « esprit Portra » : couleurs d'un profil tirées vers mes scans de Portra 400 ; tonalité de mes scans de HP5 |
| **Fiches techniques des films** | sensibilité spectrale, courbe caractéristique, colorants | Tri-X (Kodak F-4017), HP5+ et FP4+ (Ilford), Kodachrome (Kodak E-55) : [`d40/outils/films_nb.py`](d40/outils/films_nb.py), [`d750/outils/kodachrome.py`](d750/outils/kodachrome.py), extraction des courbes des PDF vectoriels par [`d750/outils/fiches_vectorielles.py`](d750/outils/fiches_vectorielles.py) |
| **Simulateurs de films** | une cible spectrale complète, effets entre couches compris | spektrafilm pour la Kodachrome 64 ([`d750/outils/d750_spektrafilm.py`](d750/outils/d750_spektrafilm.py)) |

À noter pour chaque cible : d'où elle vient, sa licence, et ce qu'elle suppose (calage du gris, lumière). Deux cibles d'un même look peuvent différer : le Classic Chrome des JPEG du X-T4 et celui de la LUT de Fujifilm sont à 3,9 de ΔE l'un de l'autre. Choisir, et le dire.

## 2. Mesurer la scène

On compare des couleurs de **la scène réelle** rendues par le boîtier et par la cible. La scène se lit dans le RAW de la même photo :

1. **RAW linéaire** : noir soustrait, en fraction de la pleine échelle, balance des blancs de la vue ([`d750/outils/d750_blocs.py`](d750/outils/d750_blocs.py), `rawpy`).
2. **Capteur → XYZ** : une matrice ajustée sur une mire photographiée par le même modèle (D750 : mire d'Imaging Resource, 164 plages, puis une racine-polynôme d'ordre 2 pour moins de biais sur les verts), ou calculée d'après les sensibilités spectrales du capteur (D40 : base camspec, Jiang et al. 2013, [`d40/outils/matrices_spectrales.py`](d40/outils/matrices_spectrales.py)).
3. **Échelle d'exposition** : où tombe le gris de 18 % (D750 : 8,5 % de la pleine échelle) ; c'est elle qui permet de rendre la scène avec la courbe de la cible.
4. **Zones uniformes** : le JPEG est recalé sur le RAW (points communs SIFT + RANSAC, distorsion radiale), puis découpé en blocs (24 × 24 px au D750) ; on garde les blocs uniformes des deux côtés et non écrêtés. Des milliers de blocs par vue, vue par vue.

## 3. Le ΔE2000

L'écart entre deux couleurs tel que l'œil le perçoit (CIE 2000) : 0 = identique. Repères : sous 1 invisible ; 1 à 2 visible côte à côte par un œil exercé ; 2 à 3 visible côte à côte ; 3 à 5 visible pour tous, même famille de rendu ; au-delà de 5, autre rendu.

On donne toujours **la médiane** (la zone typique) et **le p90** (les 10 % de zones les plus difficiles, souvent les couleurs les plus vives), sur trois jeux de poids égal : des scènes variées, de la peau, une mire. Et on sépare toujours **prévu** (calculé par le modèle du boîtier) et **mesuré** (JPEG réellement sorti du boîtier).

## 4. Modéliser le boîtier

Pour calculer un réglage, il faut savoir ce que le boîtier fait de chaque réglage. On le mesure, on ne le suppose pas :

- **Séance d'essais pilotée** (D750) : l'ordinateur écrit un réglage d'essai dans un emplacement, déclenche, rapatrie NEF + JPEG, recommence ; 47 réglages en une séance, sans toucher le boîtier ([`d750/outils/d750_seance.py`](d750/outils/d750_seance.py) + [`d750_seance.swift`](d750/outils/d750_seance.swift)). Plusieurs scènes (couleurs vives, peau, lumière mêlée), ISO et balance fixes.
- **Ajuster un modèle** sur ces paires : au D750, matrice 3 × 3, puis la même courbe sur R, V et B, puis gain et rotation de la chroma ; la courbe perso s'applique après, sur la luma seule ([`d750/outils/d750_modele.py`](d750/outils/d750_modele.py), [`d750_analyse.py`](d750/outils/d750_analyse.py)). Ce modèle redonne le JPEG à 0,7 à 1,3 de ΔE médian.
- **Lire le firmware** quand il est accessible (D40) : courbes, matrices et tables décodées puis vérifiées en les réencodant à l'octet près ([`d40/outils/courbes.py`](d40/outils/courbes.py)), simulateur du JPEG à partir du NEF ([`d40/outils/simulateur.py`](d40/outils/simulateur.py)), sondes : un firmware « données seules » qui change une table de façon reconnaissable, photographié, pour établir ce que fait chaque table.
- **Confronter chaque hypothèse** : une courbe identité redonne-t-elle la base ? Le modèle prédit-il un vrai réglage jamais vu ? Noter chaque fait avec son niveau de preuve : vérifié, probable, hypothèse.

## 5. Calculer la recette

Pour chaque look : chercher, dans ce que le format permet, le réglage qui minimise le ΔE2000 médian (et tient le p90) entre le rendu prévu et la cible, sur les trois jeux. Au D750 : base, crans de saturation et de teinte, filtre N&B, courbe sur 257 points, balance des blancs ([`d750_analyse.py`](d750/outils/d750_analyse.py) `bases`, `nb`, `balance`, `recettes`). Au D40 : matrices par balance, courbe 12 bits, 16 secteurs de teinte, matrice YCbCr ([`d40/outils/recettes_v1.py`](d40/outils/recettes_v1.py), [`preglages_v1.py`](d40/outils/preglages_v1.py)).

Garder une partie des images à part pour la validation. Écrire, pour chaque recette, l'écart prévu et ce qui l'empêche de descendre (une limite du format n'est pas une erreur de calcul).

## 6. La boucle sur le boîtier

1. **Simuler** l'écriture d'abord : l'outil dit ce qu'il enverrait, ne touche à rien ([`d750_ecrire.swift`](d750/outils/d750_ecrire.swift) sans `--ecrire` ; au D40, l'émulateur, [`d40/emulateur/`](d40/emulateur/README.md)).
2. **Sauver avant d'écrire** (l'ancien contenu de l'emplacement), **écrire**, **relire** et comparer à l'envoi, octet par octet.
3. **Tenir l'historique** : ce qui est dans chaque emplacement, quand, et le bloc d'avant pour revenir en arrière ([`d750_historique.py`](d750/outils/d750_historique.py)). Avant un nouveau lot, relire le boîtier et s'arrêter s'il diffère de l'historique.
4. **Photographier** les recettes chargées (séance de contrôle : [`d750_lot_v2.sh`](d750/outils/d750_lot_v2.sh)) et **mesurer** le JPEG contre la cible ([`d750/outils/mesures_reelles.py`](d750/outils/mesures_reelles.py)).
5. Si le mesuré s'écarte du prévu (critère fixé avant : 0,5 de ΔE ; au D750, à la reprise d’octobre 2026, six recettes sur neuf sont à moins de 0,7 de leur prévision, sept sur neuf si la prévision est refaite sur la scène photographiée), chercher pourquoi avant de corriger : au D750, le Tri-X s'écartait parce que le boîtier applique à 10 000 K d'autres gains de balance que ceux calculés ; la v2 est refaite sur les gains lus dans le NEF (chargée, elle mesure 1,2 pour 0,3 prévu).
6. Recommencer jusqu'à ce que le mesuré suive le prévu ; alors seulement, annoncer des chiffres.

## 7. Le firmware, quand il n'y a pas d'autre voie

Ce qu'il a fallu pour le D40, dans l'ordre (détail : [`d40/README.md`](d40/README.md), [`d40/CARTE.md`](d40/CARTE.md)) :

1. **Le fichier officiel** : téléchargé chez le fabricant ; chiffré ou non ? Somme de contrôle (D40 : CRC16 XMODEM final), signature, taille exacte, ce que la mise à jour réécrit et ce qu'elle ne touche jamais.
2. **La carte** : désassemblage (Ghidra, extension du processeur, scripts de symboles), un fait par ligne avec sa preuve et son niveau de confiance, régénérable de zéro ([`d40/desassemblage/`](d40/desassemblage/)).
3. **L'émulateur** : faire tourner le vrai firmware sur l'ordinateur (démarrage, menus, touches, captures d'écran) pour essayer chaque patch avant de flasher ; une batterie de scénarios rejouée à chaque modification.
4. **Des données avant du code** : changer des tables (textes, couleurs, courbes, matrices) avant d'ajouter un crochet ; un crochet minimal, au plus près de l'endroit où le firmware choisit, sans changer ce qu'il range dans le RAW.
5. **La récupération** : savoir avant de flasher ce qui permet de revenir en arrière. Au D40, un firmware B raté se reflashe ; un firmware A qui ne démarre plus, non : le patch du A est dormant par défaut et activé seulement par le B.
6. **Un patch vérifiable** : appliqué au fichier officiel, octets d'origine vérifiés, résultat identique à l'octet près à ce qui a été testé ([`d40/patch.py`](d40/patch.py), [`d40/fabriquer_v5.py`](d40/fabriquer_v5.py)).

## 8. Dire ce qui est mesuré

Un tableau unique : look, boîtier, médiane, p90, mesuré ou prévu, nombre de vues, cible. Les réserves à côté (peu de vues, une seule lumière, cibles qui ne s'accordent pas, zones uniformes seulement). Exemple : [`d750/recherche/resultats-mesures.md`](d750/recherche/resultats-mesures.md).
