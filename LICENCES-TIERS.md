# Licences et sources tierces

Tout ce qui n'est pas listé ici est le travail de Thomas Hammoudi, sous [CC BY-NC-SA 4.0](LICENSE). Restent à Nikon : les tables d'usine du D40 décodées dans `d40/recettes/v1/nikon.json` (et sa copie sous `d750/`), gardées parce que les calculs en ont besoin, et les textes, glyphes et en-têtes que reprennent certains patchs (voir le README, « Cadre légal »).

## Dans le dépôt, sous une autre licence

| Fichiers | Licence | Pourquoi |
|---|---|---|
| `d40/emulateur/java/*.java`, `d200/emulateur/java/*.java`, `d40/desassemblage/bd400111.dfr.txt` | **GPL-3.0** ([`d40/emulateur/COPYING`](d40/emulateur/COPYING)) | l'émulateur est écrit dans le paquet de [nikon-firmware-tools](https://github.com/simeonpilgrim/nikon-firmware-tools) (Simeon Pilgrim et les auteurs de Nikon Hacker) et compilé avec ses sources, que `d40emu.py --cloner` télécharge ; la configuration du désassembleur est tirée de celle du D80 du même projet |
| `645d/desassemblage/pfw_deobf.py` | **GPL-2.0** ([`645d/desassemblage/COPYING`](645d/desassemblage/COPYING), en-tête du fichier) | réécriture en Python de l'étape « deobfuscate » de [pfwtool](https://github.com/twang2218/pentax-firmware-tool) (Tao Wang), lue dans ses sources |
| `d40/desassemblage/ghidra_scripts/ResolveUTronSyscallsScript.java` | **Apache 2.0** (en-tête du fichier) | copie corrigée d'un script de [ghidra-fr60](https://github.com/desrdev/ghidra-fr60) (Darren Thompson), lui-même dérivé de Ghidra |

## Hors du dépôt : à récupérer soi-même

| Source | Sert à | Où | Licence, conditions |
|---|---|---|---|
| Firmware D40 A 1.12 et B 1.11 | fabriquer la V5 | Nikon : [A 1.12](https://downloadcenter.nikonimglib.com/en/download/fw/6.html), [B 1.11](https://downloadcenter.nikonimglib.com/en/download/fw/119.html) | conditions de Nikon, acceptées au téléchargement ; jamais redistribué ici |
| Firmware D750 C 1.15 | étude du format USB (`d750_firmware.py`) ; inutile pour charger les recettes | Nikon, centre de téléchargement | idem |
| LUT F-Log2 de Fujifilm (Classic Chrome, Classic Neg…) | cibles Classic Chrome et Classic Neg | [Fujifilm, LUT F-Log2](https://www.fujifilm-x.com/global/support/download/lut/) | conditions de Fujifilm ; non redistribuées |
| spektrafilm (A. Volpato) | cible Kodachrome 64 (table 3D) | [github.com/andreavolpato/spektrafilm](https://github.com/andreavolpato/spektrafilm) | code GPL-3.0, profils CC BY-SA 4.0, tables sous leur propre licence ; crédit : « film modeling powered by spektrafilm » ; ni le code ni les tables ne sont ici |
| agx-emulsion (A. Volpato) | réponses densitométriques Status A (`kodachrome.py`) | [github.com/andreavolpato/agx-emulsion](https://github.com/andreavolpato/agx-emulsion), commit `e418a25` | GPL-3.0 ; données lues, non recopiées |
| Presets Lightroom Tri-X et Portra | cibles Tri-X et Portra | un preset acheté que j'aimais beaucoup, vendu en ligne | produit commercial : on imite son rendu pour un usage très particulier, le JPEG direct d'un boîtier ; aucun fichier ni code de ce preset n'est redistribué : ni le profil, ni sa table 3D, ni l'ajustement d'un modèle sur sa table. Sont publiés des réglages calculés à partir de mesures faites avec ces profils : pour le Tri-X, le mélange de canaux et la courbe déduits des exports (`d40/recettes/v1/tri-x.json`) ; pour le Portra, des centiles de clarté et de teinte d'exports du preset Portra (`d750-seances/portra-esprit.json`, `bases-portra-esprit.json`) |
| Base camspec (Jiang, Liu, Gu, Süsstrunk, 2013) | sensibilités spectrales du D40 | « What is the space of spectral sensitivity functions for digital color cameras? », WACV 2013 ; base sur Zenodo (3245883) | CC BY-NC-SA ; non recopiée ici |
| Mire d'Imaging Resource prise au D750 | matrice capteur → XYZ du D750 | Imaging Resource, banc d'essai du D750 | mesures publiées dans `d750/recherche/donnees-films/d750-standard-ir.json` (chiffres seuls, pas l'image) |
| Fiches techniques Kodak (Tri-X F-4017, Kodachrome E-55) et Harman (HP5+, FP4+) | cibles noir et blanc, Kodachrome | sites de Kodak Alaris et d'Ilford Harman (liens dans `films_nb.py`, `kodachrome.py`) | courbes relevées publiées en chiffres ; les PDF ne sont pas ici |
| Documents du SDK Nikon (D5000, Z 50) | format du Picture Control par USB | dépôts publics cités dans `d750/recherche/d750-picture-control-usb.md` §2 ; `d750/outils/references.sh` les rapatrie | marqués « Confidential » par Nikon : cités par section, jamais recopiés |
| Ghidra, ghidra-fr60, nikon-firmware-tools, libgphoto2, Capstone | désassemblage, émulation, codes PTP | liens dans `d40/NOTES-TECHNIQUES.md` et `d750/outils/references.sh` | leurs licences |

## Marques

Nikon, D40, D750, Picture Control, Camera Control Pro, Fujifilm, Classic Chrome, Classic Neg, Kodak, Kodachrome, Tri-X, Portra, Ilford, HP5, FP4, Hasselblad, HNCS, Ricoh, GR et Lightroom sont des marques de leurs propriétaires. Ce projet n'est lié à aucun d'eux ; les noms des looks désignent le rendu visé, pas un produit.
