# D750 : Picture Control d'essai v0 (JPEG boîtier)

But : la plus grande fidélité possible à la cible **dès le JPEG du boîtier**, sans Lightroom. Ces six fichiers sont une première version calculée, pas encore validée sur le boîtier : ils servent d'abord à vérifier que le D750 accepte nos NCP et que la courbe agit comme prévu.

Calcul : [`outils/d750_standard.py`](../../outils/d750_standard.py), sur la base Standard d'un vrai D750 mesurée sur la mire d'Imaging Resource (NEF + JPEG, ColorChecker 24 + SG 140 plages ; données dans [`recherche/donnees-films/d750-standard-ir.json`](../../recherche/donnees-films/d750-standard-ir.json)). Explications : [`recherche/d750-leviers-reglages.md`](../../recherche/d750-leviers-reglages.md) §6.

| Fichier | Nom dans le boîtier | Base | Cible | Écart prévu (ΔE2000 médian sur la mire) | Réglage à faire en plus |
|---|---|---|---|---|---|
| PICCON41.NCP | CHROME V0 | Standard | Fujifilm Classic Chrome (LUT officielle) | 2,2 (Standard brut : 6,0) | rien |
| PICCON42.NCP | CLASSIC NEG V0 | Standard | Fujifilm Classic Neg. (LUT officielle) | 4,6 (Standard brut : 5,4) | rien |
| PICCON43.NCP | KODACHROME V0 | Standard | Kodachrome 64 (modèle spectral de la fiche Kodak) | 6,0 ; **3,1 avec la WB** | **WB lumière du jour, réglage fin B3 à B5** (à la main, ou dans U1/U2) |
| PICCON44.NCP | TRI-X DDX V0 | Monochrome, filtre aucun | Tri-X, DD-X à contraste normal (pente 0,62), tirage grade 2 | courbe seule | WB fixe vers 8 000 K (rapport *perspectives* §3.3) |
| PICCON45.NCP | HP5 DDX V0 | Monochrome, filtre aucun | HP5, courbe Ilford (même contraste que DD-X) | courbe seule | WB fixe 10 000 K |
| PICCON46.NCP | FP4 DDX V0 | Monochrome, filtre aucun | FP4+, courbe Ilford (Ilfotec HC) | courbe seule | WB fixe 10 000 K |

Tous : contraste et luminosité « gérés par la courbe », saturation et teinte à 0, accentuation 3. Le calage d'exposition est celui du posemètre (le Kodachrome sort donc dense, comme une diapositive : gris moyen vers 90/255).

## Charger les fichiers

### Par USB (méthode prévue)

Outil : [`outils/d750_ecrire.swift`](../../outils/d750_ecrire.swift), mode d'emploi complet et garde-fous dans [`recherche/d750-picture-control-usb.md`](../../recherche/d750-picture-control-usb.md) §6. Une recette par profil dans [`usb/`](usb/) : elle reprend la courbe du `.NCP` à l'octet près, avec les mêmes réglages.

1. Boîtier en P, S, A ou M, hors U1 / U2, câble branché, Photos et Transfert d'images fermés.
2. Fabriquer le bloc : `python3 outils/picture_control.py bloc recettes/d750-v0/usb/tri-x.json /tmp/tri-x.bin`
3. Simulation (n'écrit rien) : `swift outils/d750_ecrire.swift ecrire /tmp/tri-x.bin C-4`
4. Écriture : la même commande avec `--ecrire`. L'outil refuse un emplacement déjà occupé (ajouter `--remplacer` seulement si c'est voulu) et sauve l'ancien contenu avant d'écrire.

Commencer par **un seul** profil : l'écriture par USB n'a encore jamais été lancée sur le boîtier (§6 du rapport USB, point non vérifié sur la phase de données). Si la relecture est identique et la photo cohérente, enchaîner les autres.

### Par la carte (secours)

1. Copier les `.NCP` dans le dossier `NIKON/CUSTOMPC/` de la carte du **logement 1**.
2. Menu Prise de vue › Gérer Picture Control › Charger/enregistrer › Copier vers l'appareil, puis choisir un emplacement libre C-1 à C-9 (manuel D750, p. 171 à 174).

Si le boîtier refuse un fichier, c'est le format NCP écrit par `picture_control.py` qui est en cause : copier sur la carte un Picture Control fait dans le boîtier (même menu, Copier sur la carte), pour qu'on compare les octets.

### Dans les deux cas

D-Lighting actif : désactivé. Espace couleur : sRGB. Contrôle du vignetage : désactivé.

## Ce qu'il faut rapporter

Pour chaque profil, **NEF + JPEG** de la même vue :
- une scène colorée en plein jour, avec des neutres (mur blanc ou gris, ombre noire), du ciel, de la peau, du rouge, du jaune et du vert ;
- pour le Kodachrome, la même vue avec le réglage fin à 0, B3 et B5.

Chaque JPEG se compare à son propre NEF : la lumière peut changer d'une vue à l'autre. Ces paires suffisent pour vérifier la courbe, mesurer le mode d'application (luminance ou canaux) et corriger la v1.

## Hypothèses de la v0

Confrontées aux séances d’octobre 2026 dans [`recherche/d750-analyse-seances.md`](../../recherche/d750-analyse-seances.md) §2.6 : la courbe perso s'applique bien après la base, mais **sur la luma**, pas sur chaque canal. Les v0 sont remplacées par [`recettes/d750-v1/`](../d750-v1/).

- La courbe perso s'applique après la base, sur chaque canal (indice favorable sur la mire : 2,6 contre 2,7 ΔE médian, 4,8 contre 5,4 au 90e centile).
- Au-dessus du blanc de la mire, la courbe Standard monte jusqu'à 255 à l'écrêtage du capteur.
- La base Monochrome a la même courbe que Standard (non mesurée).
- Le boîtier utilise la table de 257 valeurs (et non les seuls 20 points d'ancrage).
