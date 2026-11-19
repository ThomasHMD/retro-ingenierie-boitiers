# D750 : recettes v3 (passe 3, validation croisée sur NX Studio)

Produit en novembre 2026 par `outils/d750_valider_nx.py` (rapport complet : [`recherche/rd-nikon-2026-11-passe3.md`](../../recherche/rd-nikon-2026-11-passe3.md)). **Chargées dans C-2 à C-5 en novembre 2026** (relecture identique à l'envoi ; blocs relus dans [`blocs/`](blocs/), historique dans [`HISTORIQUE.md`](../d750/HISTORIQUE.md)). Les dossiers v1, v2 et d750-nx ne sont pas touchés.

Seules les recettes qui passent la règle de décision (écrite avant les mesures, rapport §3) ont un fichier ici : **Classic Chrome (C-2), Classic Neg (C-3), Positive (C-4), Portra 400 (C-5)**. Hasselblad (C-6), HP5+ (C-8) et FP4+ (C-9) **restent comme dans le boîtier** : aucun fichier v3, aucune écriture. Kodachrome (C-1) et Tri-X (C-7) sont hors champ (cible absente du disque, WB 10 000 K).

Le nom affiché dans le boîtier est celui d'aujourd'hui, sans version (voir [`HISTORIQUE.md`](../d750/HISTORIQUE.md)). La recette de départ de chaque ajustement est celle qui est chargée : son bloc `bloc_recette(v1)` est identique octet pour octet à l'`apres_20n_0.bin` de l'historique (vérifié pour les 7 emplacements).

## Ce qui change par rapport à la v1 (réglages en points ; courbe en codes 0 à 255)

| C- | Fichier | Nom | Saturation v1 → v3 | Teinte v1 → v3 | Courbe (écart à la v1) | WB à régler |
|---|---|---|---|---|---|---|
| 2 | [`usb/classic-chrome-v3.json`](usb/classic-chrome-v3.json) / `.bin` | CLASSIC CHROME | −1 → **−1,25** | −2 → **−3** (limite) | au plus 3,4 (moyenne 1,4) | 5 600 K |
| 3 | [`usb/classic-neg-v3.json`](usb/classic-neg-v3.json) / `.bin` | CLASSIC NEG | 0 → **−1** | 0 → **−0,75** | au plus 7,4 (moyenne 2,6) | 5 600 K |
| 4 | [`usb/positive-v3.json`](usb/positive-v3.json) / `.bin` | POSITIVE | +2 → **+1,75** | −2 → **−3** (limite) | au plus 8,1 (moyenne 3,0) | 5 600 K |
| 5 | [`usb/portra-400-v3.json`](usb/portra-400-v3.json) / `.bin` | PORTRA 400 | +3 → **+2,75** | +2 → **+0,25** | au plus 8,7 (moyenne 3,0) | 5 600 K (U2) |

Base Standard, netteté et clarté inchangées. Contraste et luminosité « gérés par la courbe », comme la v1. La courbe est celle de la v1 plus 9 nœuds d'écart, puis ses 20 points d'ancrage (NX et le boîtier lisent ces points) ; l'écart à la v1 comprend ~0,3 à 0,7 code de remise sur les 20 points.

À noter : la teinte de Portra passe de +2 à +0,25 (1,75 point de moins), c'est le changement visible de cette série. Les deux teintes à −3 (Classic Chrome, Positive) sont à la limite du boîtier : le moteur en voudrait peut-être davantage.

## Chiffres de la validation croisée (ΔE2000 contre la cible, scènes tenues à part, moyenne des 7 scènes, chacune tenue une fois)

Actuelle (v1 dans le boîtier) → ajustée sans avoir vu la scène. Médiane, puis p90 entre parenthèses. Chaque scène sert en tenue à part une fois (3 plis), l'ajustement du pli n'utilisant que les autres scènes.

| Recette | Actuelle | Ajustée | Gain de médiane moyen des plis | Hausse de p90 moyenne des plis | Plis en perte | Décision |
|---|---|---|---|---|---|---|
| Classic Chrome | 2,35 (4,17) | **1,93 (3,80)** | 0,43 | −0,38 | 0 | garder |
| Classic Neg | 4,95 (7,17) | **4,73 (6,52)** | 0,22 (juste au-dessus du seuil de 0,2) | −0,64 | 0 | garder |
| Positive | 3,38 (5,78) | **2,54 (5,35)** | 0,83 | −0,44 | 0 | garder |
| Portra 400 | 3,78 (6,03) | **2,85 (4,70)** | 0,97 | −1,28 | 0 | garder |
| Hasselblad | 3,08 (5,17) | 2,92 (5,15) | 0,15 | −0,01 | 1 | recette actuelle |
| HP5+ | 2,28 (6,26) | 2,12 (5,92) | 0,13 | −0,31 | 1 | recette actuelle |
| FP4+ | 1,58 (6,93) | 1,58 (6,82) | −0,00 | −0,09 | 2 | recette actuelle |

Le détail par pli et par scène est dans [`resume.json`](resume.json) et dans le rapport. **Ces chiffres sont mesurés dans NX Studio, pas sur un JPEG de ces recettes sorti du boîtier** : NX reproduit le boîtier à 0,15 à 0,33 ΔE près en N&B, mais il reste un plancher de 1,0 à 1,5 ΔE en couleur (rapport de novembre, passe 2). Le gain est réel dans NX et vraisemblable pour le boîtier, pas démontré.

## Charger dans le boîtier : commandes prêtes, NON lancées

Sur le Mac relié au D750, dans le dossier `Photographie/logiciels/d40-firmware/`. Préconditions (`recherche/d750-picture-control-usb.md` §6) : boîtier allumé en P, S, A ou M, pas en prise de vue, câble USB branché, Photos et Transfert d'images fermés, **U1 et U2 ne doivent pas utiliser l'emplacement visé** (sinon refus 0x200F : U2 est prévu sur C-5, la Portra, d'après le README v1 : état actuel non relu ; si c'est le cas, le décaler avant et le remettre après). Chaque emplacement : une simulation (n'écrit rien), puis l'écriture avec `--remplacer` (l'emplacement est occupé ; l'ancien contenu est sauvé avant), la relecture se fait toute seule.

```
# C-2 CLASSIC CHROME
python3 outils/picture_control.py bloc recettes/d750-v3/usb/classic-chrome-v3.json /tmp/d750-C-2.bin   # doit afficher 610 octets
swift outils/d750_ecrire.swift ecrire recettes/d750-v3/usb/classic-chrome-v3.bin C-2                    # simulation
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

# C-5 PORTRA 400 (U2 est prévu sur C-5 : voir la précondition)
python3 outils/picture_control.py bloc recettes/d750-v3/usb/portra-400-v3.json /tmp/d750-C-5.bin
swift outils/d750_ecrire.swift ecrire recettes/d750-v3/usb/portra-400-v3.bin C-5
swift outils/d750_ecrire.swift ecrire recettes/d750-v3/usb/portra-400-v3.bin C-5 --ecrire --remplacer
# retour : swift outils/d750_ecrire.swift ecrire sondes/d750/usb/ecriture-2026-10.17/apres_205_0.bin C-5 --ecrire --remplacer
```

Pas de C-6, C-8, C-9 : ces trois recettes ne changent pas. Après chargement, contrôle par une photo de la scène du test v1 mesurée par `mesures_reelles.py`, puis mise à jour de l'historique par `d750_historique.py` (qui lit les journaux d'écriture).

Sha256 des blocs (10 premiers caractères) : Classic Chrome 14552d6403, Classic Neg 11d2c735fe, Positive 5bf9b2702f, Portra 400 104a75929b.
