# D750 : historique des Picture Control C-1 à C-9

Fichier refait par `python3 outils/d750_historique.py` depuis les journaux d'écriture (`sondes/d750/usb/ecriture-*/`) : ne pas l'éditer à la main. Revenir à n'importe quel état : `swift outils/d750_ecrire.swift ecrire <fichier .bin> C-n` (simulation), puis avec `--ecrire --remplacer`. Les séances de test n'écrivent que C-9 et le remettent comme avant.

## Dans le boîtier aujourd'hui

| Emplacement | Nom | Base | Réglages | Source | Écrit le | Bloc (pour y revenir) |
|---|---|---|---|---|---|---|
| C-1 | KODACHROME | Standard | saturation -1, teinte -3, netteté 4, clarté +1, courbe | Kodachrome v2 « vif », renommé sans version : `recettes/d750-v1/usb/kodachrome-v2.json` | octobre 2026 | `sondes/d750/usb/ecriture-2026-10.14/apres_201_0.bin` (sha 84c713a2fa) |
| C-2 | CLASSIC CHROME | Standard | saturation -1, teinte -2, netteté 3, clarté +0, courbe | même recette, renommée sans version (`recettes/d750-v1/usb/`) | octobre 2026 | `sondes/d750/usb/ecriture-2026-10.19/apres_202_0.bin` (sha a5e0c5f4e1) |
| C-3 | CLASSIC NEG | Standard | saturation +0, teinte +0, netteté 3, clarté +0, courbe | même recette, renommée sans version (`recettes/d750-v1/usb/`) | octobre 2026 | `sondes/d750/usb/ecriture-2026-10.16/apres_203_0.bin` (sha 78243f9ed1) |
| C-4 | POSITIVE | Standard | saturation +2, teinte -2, netteté 3, clarté +0, courbe | même recette, renommée sans version (`recettes/d750-v1/usb/`) | octobre 2026 | `sondes/d750/usb/ecriture-2026-10.16/apres_204_0.bin` (sha 15397862f9) |
| C-5 | PORTRA 400 | Standard | saturation +3, teinte +2, netteté 4, clarté +0, courbe | Portra 400 v2 « esprit Portra », renommé sans version : `recettes/d750-v1/usb/portra-400-v2.json` | octobre 2026 | `sondes/d750/usb/ecriture-2026-10.17/apres_205_0.bin` (sha 386743f90b) |
| C-6 | HASSELBLAD | Standard | saturation +1, teinte -3, netteté 3, clarté +0, courbe | même recette, renommée sans version (`recettes/d750-v1/usb/`) | octobre 2026 | `sondes/d750/usb/ecriture-2026-10.17/apres_206_0.bin` (sha a9f2b16dfe) |
| C-7 | TRI-X | Monochrome | filtre aucun, contraste +0, netteté 5, clarté +1, courbe | Tri-X v2 (filtre aucun, courbe pour les gains réels de la WB à 10 000 K), `recettes/d750-v2/usb/tri-x.bin` | octobre 2026 | `sondes/d750/usb/ecriture-2026-10.29/apres_207_0.bin` (sha 9f742fd580) |
| C-8 | HP5+ | Monochrome | filtre aucun, contraste +0, netteté 4, clarté -1, courbe | même recette, renommée sans version (`recettes/d750-v1/usb/`) | octobre 2026 | `sondes/d750/usb/ecriture-2026-10.18/apres_208_0.bin` (sha c0c76b1152) |
| C-9 | FP4+ | Monochrome | filtre aucun, contraste +0, netteté 4, clarté +0, courbe | même recette, renommée sans version (`recettes/d750-v1/usb/`) | octobre 2026 | `sondes/d750/usb/ecriture-2026-10.18/apres_209_0.bin` (sha c57325f623) |

## Toutes les écritures

| Date | Emplacement | Avant | Après | Bloc d'avant (pour y revenir) |
|---|---|---|---|---|
| octobre 2026 | C-1 | Kodachrome (réglage de Thomas, avant le projet) | KODACHROME V2 (sha ee3ab9eb85) | `sondes/d750/usb/ecriture-2026-10.10/avant_201_0.bin` |
| octobre 2026 | C-2 | TRI-X (réglage de Thomas, avant le projet) | CLASSIC CHROME V1 (sha 18f634f844) | `sondes/d750/usb/ecriture-2026-10.10/avant_202_0.bin` |
| octobre 2026 | C-3 | Portra 400 (réglage de Thomas, avant le projet) | CLASSIC NEG V1 (sha 1c732167d7) | `sondes/d750/usb/ecriture-2026-10.11/avant_203_0.bin` |
| octobre 2026 | C-4 | TRI-X Foret (réglage de Thomas, avant le projet) | POSITIVE V1 (sha 16166240b4) | `sondes/d750/usb/ecriture-2026-10.11/avant_204_0.bin` |
| octobre 2026 | C-5 | TRI-X Paysage (réglage de Thomas, avant le projet) | PORTRA 400 V2 (sha 6c9a5a2457) | `sondes/d750/usb/ecriture-2026-10.12/avant_205_0.bin` |
| octobre 2026 | C-6 | HP5+ (réglage de Thomas, avant le projet) | HASSELBLAD V1 (sha 3a0f275ba6) | `sondes/d750/usb/ecriture-2026-10.12/avant_206_0.bin` |
| octobre 2026 | C-7 | vide | TRI-X V1 (sha 644b455b4c) | effacer : `d750_ecrire.swift effacer C-7` |
| octobre 2026 | C-8 | vide | HP5 V1 (sha d69e004783) | effacer : `d750_ecrire.swift effacer C-8` |
| octobre 2026 | C-9 | vide | FP4 V1 (sha 30a7b4aac6) | effacer : `d750_ecrire.swift effacer C-9` |
| octobre 2026 | C-1 | KODACHROME V2 (Kodachrome v2 « vif » (cible spektrafilm × 1,2, WB 6 250 K), livraison d’octobre : `recettes/d750-v1/usb/kodachrome-v2.json`) | KODACHROME (sha 84c713a2fa) | `sondes/d750/usb/ecriture-2026-10.14/avant_201_0.bin` |
| octobre 2026 | C-3 | CLASSIC NEG V1 (première livraison d’octobre, recette v1 à courbe recalculée (`recettes/d750-v1/usb/`)) | CLASSIC NEG (sha 78243f9ed1) | `sondes/d750/usb/ecriture-2026-10.16/avant_203_0.bin` |
| octobre 2026 | C-4 | POSITIVE V1 (première livraison d’octobre, recette v1 à courbe recalculée (`recettes/d750-v1/usb/`)) | POSITIVE (sha 15397862f9) | `sondes/d750/usb/ecriture-2026-10.16/avant_204_0.bin` |
| octobre 2026 | C-5 | PORTRA 400 V2 (Portra 400 v2 « esprit Portra », livraison d’octobre : `recettes/d750-v1/usb/portra-400-v2.json`) | PORTRA 400 (sha 386743f90b) | `sondes/d750/usb/ecriture-2026-10.17/avant_205_0.bin` |
| octobre 2026 | C-6 | HASSELBLAD V1 (première livraison d’octobre, recette v1 à courbe recalculée (`recettes/d750-v1/usb/`)) | HASSELBLAD (sha a9f2b16dfe) | `sondes/d750/usb/ecriture-2026-10.17/avant_206_0.bin` |
| octobre 2026 | C-7 | TRI-X V1 (première livraison d’octobre, recette v1 à courbe recalculée (`recettes/d750-v1/usb/`)) | TRI-X (sha 27b0d557a6) | `sondes/d750/usb/ecriture-2026-10.18/avant_207_0.bin` |
| octobre 2026 | C-8 | HP5 V1 (première livraison d’octobre, recette v1 à courbe recalculée (`recettes/d750-v1/usb/`)) | HP5+ (sha c0c76b1152) | `sondes/d750/usb/ecriture-2026-10.18/avant_208_0.bin` |
| octobre 2026 | C-9 | FP4 V1 (première livraison d’octobre, recette v1 à courbe recalculée (`recettes/d750-v1/usb/`)) | FP4+ (sha c57325f623) | `sondes/d750/usb/ecriture-2026-10.18/avant_209_0.bin` |
| octobre 2026 | C-2 | CLASSIC CHROME V1 (première livraison d’octobre, recette v1 à courbe recalculée (`recettes/d750-v1/usb/`)) | CLASSIC CHROME (sha a5e0c5f4e1) | `sondes/d750/usb/ecriture-2026-10.19/avant_202_0.bin` |
| octobre 2026 | C-7 | TRI-X (même recette, renommée sans version (`recettes/d750-v1/usb/`)) | TRI-X (sha 9f742fd580) | `sondes/d750/usb/ecriture-2026-10.29/avant_207_0.bin` |

## Hors Picture Control

- Préréglages de balance d-1 à d-3 : commentaires « KODACHROME 6250K », « TRI-X 10000K », « PORTRA 400 5600K » écrits en octobre 2026 (`sondes/d750/usb/ecriture-2026-10.20/`, anciens commentaires sauvés en `avant_d02*.bin`). Les valeurs se chargent par le menu.
- Modes U1 et U2 : réglés à la main dans le boîtier, non relus par USB.
- Recettes v2 : [`recettes/d750-v2/`](../d750-v2/README.md) (Tri-X v2 écrit en C-7 en octobre 2026 au début du lot n° 2).
