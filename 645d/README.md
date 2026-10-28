# Pentax 645D : looks argentiques par réglage, en USB

**Le firmware du 645D n'est jamais modifié.** Tout passe par des réglages que les menus du boîtier savent déjà prendre (le Custom Image), envoyés par USB. Le firmware 1.33 n'a été que lu, hors du boîtier, pour comprendre ce que l'USB accepte.

## Ce qui est dans le boîtier (octobre 2026, vérifié par l'EXIF)

| Où (nom du menu, fixe) | Recette | Réglages au menu |
|---|---|---|
| Naturel (mode actif) | **Classic Chrome** | teinte −2, le reste à 0 |
| Lumineux | **Portra 400** (exposer −⅓ à −½ IL) | tout à 0 |
| Monochrome | **Tri-X 400** | filtre aucun, virage 0, contraste +3, netteté +2 |
| Molette USER | **HP5 Plus** | Monochrome, filtre cyan, virage 0, contraste +4, netteté +2 |
| Portrait, Paysage, Vibrant, Atténué, Inversion film | inchangés | |

Valeurs USB et écarts mesurés : [`recettes/recettes-645d.json`](recettes/recettes-645d.json). Les noms des modes ne se changent pas (ils sont dans le firmware). Les recettes tiennent après un arrêt par l'interrupteur, **pas après un retrait de la batterie** : il faut alors les recharger.

Le rendu, sur une même scène au trépied : [`../README.md`](../README.md#ce-que-ça-fait), section « Ce que ça fait ».

## Ce qu'on a appris

Détail et niveau de preuve de chaque fait : [`recherche/645d-usb-et-reglages.md`](recherche/645d-usb-et-reglages.md) (mesuré sur le boîtier) et [`recherche/645d-firmware-usb.md`](recherche/645d-firmware-usb.md) (lecture du firmware).

- **Le 645D se pilote par USB après une poignée de main constructeur** : `0x9001 SetPentaxVendorMode (0x0D, 0x12E08, 1)`. Ensuite le Custom Image entier s'écrit (mode, saturation, teinte, contraste, netteté ; en Monochrome filtre et virage), chaque mode garde ses valeurs, et le boîtier se déclenche (`0x9011 (0, 2, 0)`). Aucun logiciel connu ne le faisait (ni pkTriggerCord ni libgphoto2 ne connaissent le 645D).
- **Une vue déclenchée par USB n'est pas écrite sur la carte** : elle n'existe que dans la mémoire du boîtier, à rapatrier avant de fermer la session.
- **Piège** : la première écriture qui suit une vue, dans la même session, fige l'USB du boîtier (batterie à retirer). Une session neuve par vue l'évite (`645d_seance.swift` le fait).
- **Le PEF embarque un JPEG pleine taille** rendu avec le Custom Image : chaque vue est une paire RAW ↔ rendu, la mesure se fait sans RAW+ ni mire.
- **Noir et blanc** : le défaut du Monochrome d'origine est sa courbe trop plate (ombres grises, hautes lumières ternes). Contraste +3 à +4 réduit l'écart à Tri-X et HP5 de moitié ou plus. Les 9 filtres sont mesurés (poids R/V/B) : aucun pour Tri-X, cyan pour HP5 ; il manque un « bleu clair » que le boîtier n'a pas.
- **Couleur** : Classic Chrome à ΔE 1,9 (Naturel teinte −2), Portra à 2,3 (Lumineux à 0), sur une scène peu colorée (peau, ciel, feuillage non vérifiés).
- **Le préréglage USER garde son propre Custom Image** : c'est le 2e emplacement Monochrome (HP5). Il s'enregistre au menu A4, pas par USB.
- **Hors d'atteinte du PTP** : balance des blancs et Kelvin, High/Low Key, contraste des hautes lumières et des ombres, exposition. La balance passerait par le mode MSC (commandes SCSI Pentax) : la capture du boîtier marche en root, mais macOS refuse ensuite d'ouvrir son interface de stockage (`0xe00002e2`) ; reste la voie de libusb, non essayée.

## Charger ou annuler les recettes

Boîtier allumé, menu R2 « USB Connection » = PTP, branché, Photos et Transfert d'images fermés. Depuis la racine du dépôt, avec un dossier de travail `$T` (le plan y écrit ses vues) :

```bash
swiftc -O 645d/outils/645d_seance.swift -o "$T/645d_seance"
cp -R 645d/recettes/charger "$T/" && "$T/645d_seance" "$T/charger" --sauver && "$T/645d_seance" "$T/charger"
```

- `charger/` : Portra, Classic Chrome, Tri-X, puis Naturel actif (4 vues de contrôle).
- HP5 en USER : `hp5-pour-user/` (Monochrome HP5 actif), **A4 › Enregistrer mode USER** au menu, puis `retour-trix/`.
- Annuler : `645d_seance <dossier> --remettre` remet l'état sauvé par `--sauver`.
- Éteindre ensuite par l'interrupteur.

## Dossiers

| Dossier | Contenu |
|---|---|
| [`outils/`](outils/) | `645d_ptp.swift` (sonde en lecture seule), `645d_etat.swift` (relevé et suivi de l'état), `645d_seance.swift` (sauver, plan de vues, remettre, rapatrier), `645d_mesure.py` (poids des filtres, courbes, comparaison aux films), `645d_vues_demo.py` (vues de démonstration tirées des PEF), `645d_scsi.swift` + `645d_scsi.sh` (client SCSI Pentax en MSC, lecture seule, bloqué par macOS) |
| [`recettes/`](recettes/) | les recettes et les plans qui les chargent |
| [`desassemblage/`](desassemblage/README.md) | outils de lecture du firmware (déobfuscation, Ghidra FR60, interpréteur FR) |
| [`recherche/`](recherche/) | les deux rapports |
| [`sondes/usb/`](sondes/usb/) | lectures USB brutes du boîtier, séances et essais MSC (numéro de série effacé) ; résultats `nb-mesure-2.json`, `couleur-mesure-2.json` |

Outils partagés avec le D750 : [`../d750/outils/raw_lineaire.swift`](../d750/outils/raw_lineaire.swift) (RAW → RVB linéaire), cibles des films dans [`../d750/recherche/donnees-films/`](../d750/recherche/donnees-films/) et [`../d750/outils/d750_cibles.py`](../d750/outils/d750_cibles.py).

## Pistes

- Une vue de Tri-X à contraste +3 : +3 est chargé, seuls +2 et +4 sont mesurés.
- Une scène colorée (bibliothèque, visage) pour valider Portra et Classic Chrome sur la peau, le ciel, le feuillage.
- Mesurer High/Low Key et le contraste des hautes lumières et des ombres (au menu) pour aller plus près des films.
- MSC : essayer la voie de libusb (API USB d'IOKit, ré-énumération en capture) pour lire puis régler la balance des blancs.
- Export `MODSET.487` (`DSP_USR_DAT_READ`, lecture seule) : le boîtier écrit ses réglages sur la carte sans rien changer.
