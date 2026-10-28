# D750 : première livraison des Picture Control (C-1 à C-9)

Livraison d’octobre 2026, calculée à partir des cinq lots de calibration et du lot de test v1. Méthode, chiffres et limites : [`recherche/d750-analyse-seances.md`](../../recherche/d750-analyse-seances.md).

| C- | Fichier | Nom dans le boîtier | Base | Saturation, teinte / filtre | WB à régler | Écart prévu (scènes, médiane) |
|---|---|---|---|---|---|---|
| 1 | [`kodachrome-v2.json`](usb/kodachrome-v2.json) | KODACHROME | Standard | −1, −3 | **6 250 K** | 2,8 ; peau 0,6 (cible spektrafilm +20 %, §3.5 bis) |
| 2 | [`classic-chrome-v1.json`](usb/classic-chrome-v1.json) | CLASSIC CHROME | Standard | −1, −2 | 5 600 K | 1,4 |
| 3 | [`classic-neg-v1.json`](usb/classic-neg-v1.json) | CLASSIC NEG | Standard | 0, 0 | 5 600 K | 4,4 (hors critère) |
| 4 | [`positive-v1.json`](usb/positive-v1.json) | POSITIVE | Standard | +2, −2 | 5 600 K | 2,4 |
| 5 | [`portra-400-v2.json`](usb/portra-400-v2.json) | PORTRA 400 | Standard | +3, +2 | **5 600 K** (U2) | 2,8 ; peau 1,7 (cible « esprit Portra », §3.6) |
| 6 | [`hasselblad-v1.json`](usb/hasselblad-v1.json) | HASSELBLAD | Standard | +1, −3 | 5 600 K | 2,2 |
| 7 | [`tri-x-v1.json`](usb/tri-x-v1.json) | TRI-X | Monochrome | filtre aucun | **10 000 K** (U1) | 0,4 |
| 8 | [`hp5-v1.json`](usb/hp5-v1.json) | HP5+ | Monochrome | filtre aucun | 5 600 K | 2,2 (p90 8 : bleus) |
| 9 | [`fp4-v1.json`](usb/fp4-v1.json) | FP4+ | Monochrome | filtre aucun | 5 600 K | 2,1 |

Dans le boîtier, les noms sont sans version (choix de Thomas) ; la version de chaque profil est dans le nom du fichier et dans `resume.json` : Kodachrome et Portra sont à leur deuxième cible (la v1 de chacun a été photographiée au lot de test, puis corrigée). Les sept autres gardent les réglages photographiés au lot de test ; leurs courbes sont recalculées après la correction des coins au 28 mm (écart de courbe au plus 0,05 de la pleine échelle). Le détail des écarts (peau, mire, p90) est dans [`resume.json`](resume.json).

Tous : contraste et luminosité « gérés par la courbe », D-Lighting actif désactivé, espace sRGB. Le Picture Control ne mémorise pas la WB : la régler à la main pour Kodachrome (6 250 K) ; Tri-X et Portra la gardent dans U1 et U2.

Reproduire (résultats de calcul dans `recherche/donnees-films/d750-seances/`) : `python3 outils/d750_analyse.py recettes $D/bases.json,$D/bases-portra-esprit.json $D/nb.json $D/validation.json $D/balance-kodachrome-spektrafilm.json recettes/d750-v1` (cibles spektrafilm et preset Portra hors dépôt : `D750_SPEKTRAFILM`, `D750_LOOKS`).

## Charger dans le boîtier

Sur le Mac relié au D750 (boîtier allumé, pas en prise de vue, U1 et U2 ne doivent pas utiliser l'emplacement visé, sinon refus 0x200F) :

```
cd <dépôt>/d750
while read n nom; do
  python3 outils/picture_control.py bloc recettes/d750-v1/usb/$nom.json /tmp/d750-C$n.bin
  swift outils/d750_ecrire.swift ecrire /tmp/d750-C$n.bin C-$n            # simulation : rien n'est écrit
done <<FIN
1 kodachrome-v2
2 classic-chrome-v1
3 classic-neg-v1
4 positive-v1
5 portra-400-v2
6 hasselblad-v1
7 tri-x-v1
8 hp5-v1
9 fp4-v1
FIN
```

Si les neuf simulations sont propres, relancer la boucle avec `--ecrire` (et `--remplacer` pour un emplacement déjà occupé, la simulation le signale ; l'ancien contenu est sauvé avant). L'outil relit chaque emplacement après écriture et compare à l'envoi. Mode d'emploi détaillé : [`recherche/d750-picture-control-usb.md`](../../recherche/d750-picture-control-usb.md) §6.

Contrôle sur le boîtier : menu Prise de vue, Régler le Picture Control : C-1 à C-9 portent les noms ci-dessus.

Mesures : le test d’octobre 2026 (`images/d750/2026-10-test-v1/`, analysé en octobre par `outils/mesures_reelles.py`, [`recherche/resultats-mesures.md`](../../recherche/resultats-mesures.md)) a photographié les recettes v1 **d'avant** cette livraison. Ce qui est chargé se mesure au lot de contrôle n° 2, avec le Tri-X v2 (gains réels de la WB à 10 000 K) : [`recettes/d750-v2/`](../d750-v2/README.md).

**Chargée en octobre 2026** par la session locale : neuf écritures 0x2001, relecture identique à l'envoi (journaux `sondes/d750/usb/ecriture-2026-10.10` à `-224032`). Les anciens profils de C-1 à C-6 (Kodachrome, TRI-X, Portra 400, TRI-X Forêt, TRI-X Paysage, HP5+) sont sauvés dans les `avant_20n_*.bin` du premier passage. À refaire par Thomas dans le menu : U1 sur C-7 (10 000 K), U2 sur C-5 (5 600 K).
