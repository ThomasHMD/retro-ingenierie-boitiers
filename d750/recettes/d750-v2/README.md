# D750 : Tri-X v2 proposé, et le lot de contrôle n° 2

Calculé en octobre 2026. **Tri-X v2 écrit en C-7 en octobre 2026**, au début du lot n° 2 (pris le même jour : `images/d750/2026-10-test-v2/`). Ce que contient le boîtier, et comment revenir à n'importe quel état : [`recettes/d750/HISTORIQUE.md`](../d750/HISTORIQUE.md). Mesures : [`recherche/resultats-mesures.md`](../../recherche/resultats-mesures.md).

## Tri-X v2

Le Tri-X a été calculé avec des gains de balance des blancs **calculés** pour 10 000 K ; le NEF du test v1 donne les gains **réels**, plus chauds :

| Gains à 10 000 K, rapportés à 5 600 K | R | B |
|---|---|---|
| calculés | 1,184 | 0,757 |
| lus dans le NEF du test v1 (`WB_RBLevels`) | **1,308** | **0,804** |

Calcul fait avec le modèle de la livraison chargée dans le boîtier (`recherche/donnees-films/d750-seances/modele.json`, coins du 28 mm corrigés) :

| | Scènes | Peau | Mire |
|---|---|---|---|
| TRI-X chargé en C-7, gains calculés (ce qui était prévu) | 0,44 | 0,62 | 0,88 |
| TRI-X chargé en C-7, gains réels (ce qu'il fait) | 0,74 | 1,24 | 0,86 |
| **Tri-X v2** : filtre aucun, courbe refaite pour les gains réels | **0,33** | **0,64** | **0,77** |

ΔE2000 médian prévu ([`resume.json`](resume.json)). Fichiers : [`usb/tri-x.json`](usb/tri-x.json) et le bloc [`usb/tri-x.bin`](usb/tri-x.bin) (610 octets, nom « TRI-X » sans version, Monochrome, netteté 5, clarté +1 ; WB 10 000 K en U1, inchangée). Une première version (filtre vert), calculée avec le modèle d'avant la correction des coins, est remplacée par celle-ci.

**Chargé en C-7 au début du lot n° 2** (décision de Thomas, octobre 2026 : tout charger d'un coup) : `d750_lot_v2.sh` l'écrit avec `d750_ecrire.swift --ecrire --remplacer`, qui sauve l'ancien TRI-X (`avant_207_0.bin`), puis refait l'historique. Revenir en arrière : l'historique donne le bloc d'avant.

## Lot de contrôle n° 2

Pourquoi : le test v1 d’octobre a été pris le soir, en lumière artificielle, avec les recettes v1 d'avant la livraison ; le boîtier contient depuis la livraison (Kodachrome et Portra en v2, courbes des sept autres recalculées). Ce lot mesure **ce qui est vraiment dans le boîtier**, de jour, plus ce que les recettes utilisent sans l'avoir mesuré.

| WB | Vues |
|---|---|
| 5 600 K | les 7 Picture Control chargés en C-2 à C-6, C-8, C-9 (octets identiques au boîtier) ; BASE STANDARD ; Standard saturation +2, teinte −2, teinte +2 (crans utilisés par Positive, Classic Chrome, Portra, jamais photographiés) ; deux demi-crans, saturation +2,5 et teinte −2,5 (le bloc accepte les quarts de point, effet jamais mesuré) |
| 6 250 K | KODACHROME chargé (C-1) ; la vue dit aussi si le boîtier règle bien 6 250 K |
| 10 000 K | l'ancien TRI-X (octets d’octobre, envoyé dans C-9) et TRI-X V2 |
| 4 000, 5 000, 8 000 K | une vue Standard chacune : gains réels de la WB, pour ne plus les calculer |

19 vues en six passages enchaînés seuls : chaque vue passe par C-9 (remis comme avant à la fin), la WB est réglée par USB puis remise. Avant tout, l'outil relit C-1 à C-9 et **s'arrête si le boîtier diffère de l'historique**, puis charge le Tri-X v2 en C-7.

**Le lot v2 pris sur la bibliothèque contient déjà toutes les vues de la page** (BASE STANDARD, les neuf chargés, TRI-X V2). La série courte ci-dessous ne sert que si le lot principal est pris ailleurs. **Série bibliothèque** : les exemples de la page du blog ne montrent que la bibliothèque, jamais le visage ni le pédalier. BASE STANDARD (l'image de départ) puis les neuf Picture Control tels que chargés, Tri-X v2 compris, chacun à sa WB : 10 vues, trois passages (5 600, 6 250, 10 000 K). **Ces vues sont à prendre** : aucun JPEG du boîtier n'existe sur la bibliothèque avec les recettes chargées.

**Préparation** : de jour, **la bibliothèque** (28 mm à f/5,6, cadrage de la séance 4 : vignetage mesuré, et comparaison possible avec le lot 4 ; la page du blog ne montre que cette scène), trépied, mode M, ISO 200 fixe, exposition réglée sur la scène, mise au point manuelle, WB en mode K, D-Lighting actif coupé, NEF + JPEG fine, ni U1 ni U2, Photos et Transfert d'images fermés, D750 branché en USB.

**Réglages faits par USB** (octobre 2026, `outils/d750_preparer.swift`) : balance des blancs en mode K, ISO 200 sans ISO auto, D-Lighting actif coupé, NEF + JPEG fine, f/5,6, vitesse au choix (`--vitesse 1/15`) ; état de départ sauvé dans `avant-reglages.json`, remis par `--remettre` ; `--essai` prend une vue Standard à 5 600 K pour vérifier cadrage et exposition. Restent physiques : trépied, cadrage, molette sur M (relevée, pas exigée).

**Lancer** (dossier de travail hors du dépôt) :

```
mkdir -p "<chantier>"
sh outils/d750_lot_v2.sh "<chantier>/lot" --simulation
sh outils/d750_lot_v2.sh "<chantier>/lot"
sh outils/d750_lot_v2.sh "<chantier>/lot" --bibliotheque
```

Images de la page du blog, après la série bibliothèque : `python3 outils/figures_page_blog.py <Status A> --seance "<chantier>/lot/bibliotheque"` (départ, cibles et JPEG du boîtier, même cadrage ; voir `recherche/figures/page-blog/LISEZMOI.md`).

Reprise après coupure : relancer la même commande, les passages déjà rangés sont sautés. Les images vont ensuite dans `images/d750/AAAA-MM-JJ-test-v2/` ; analyse avec `outils/mesures_reelles.py`, à adapter au lot n° 2.

**En option, même séance** : relancer le lot sur un visage (peau) ; et le D40 sur la même scène, NEF + JPEG fine, mode P, WB « Ensoleillé », deux vues dans chacun des cinq préréglages (Hasselblad et Classic Chrome n'avaient qu'une vue au test d’octobre).

**Prêt pour l'analyse (octobre 2026)** : les fichiers de la livraison (recettes, cibles, `modele.json` corrigé) sont dans le dossier ; spektrafilm 0.3.4 est installé hors du dépôt (`<dossier de travail>`, Python 3.13), table Kodachrome 64 dans `…/tables/` : `export D750_SPEKTRAFILM="<dossier de travail>"`. Contrôle : gris de 18 % à L* 49,3, b* +2,0, comme au rapport §3.5 bis.

Piste non écrite, pour l'ancien Kodachrome v1 (Neutre) : le cran −2 de saturation vaut en réalité un gain de 0,80 (0,72 interpolé) ; le demi-cran −2,5 donnerait le gain voulu (0,68). Le lot n° 2 mesure les demi-crans sur Standard.
