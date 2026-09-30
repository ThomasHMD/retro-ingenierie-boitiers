# Consigne pour une IA : reproduis ceci sur ton boîtier

Tu travailles pour une personne qui veut que **son** boîtier sorte en JPEG direct un rendu qu'elle aime (un film, une simulation d'un autre appareil, ses propres scans). Ce dépôt contient quatre cas menés jusqu'au bout, un Nikon D40 et un Nikon D200 (firmware modifié), un Nikon D750 et un Pentax 645D (réglages chargés par USB), et la méthode générale : [`METHODE.md`](METHODE.md). Lis-la en entier avant de proposer quoi que ce soit.

## Par où commencer

1. **Demande** : quel boîtier (modèle exact, version du firmware lue dans son menu), quel système d'exploitation, quels looks, et quelles sources de cible elle possède (paires RAW + JPEG d'un autre appareil, profils ou presets Lightroom, scans de ses films, rien).
2. **Si c'est un D40, un D200, un D750 ou un 645D**, tout est prêt : suis [`d40/README.md`](d40/README.md), [`d200/README.md`](d200/README.md), [`d750/README.md`](d750/README.md) ou [`645d/README.md`](645d/README.md). Pour un D750, les neuf recettes se chargent telles quelles ; pour viser d'autres cibles ou d'autres goûts, refais les séances et l'analyse.
3. **Sinon**, fais l'inventaire du §0 de la méthode pour son boîtier : ce qui se règle dans les menus, par USB (table des commandes PTP du fabricant, libgphoto2, documents du SDK), par fichier sur la carte, et si le firmware est accessible (téléchargeable, chiffré ou non, somme de contrôle). Écris cet inventaire dans un fichier avec, pour chaque fait, sa source et son niveau de preuve (vérifié, probable, hypothèse). Propose ensuite la voie la moins risquée qui suffit, et attends son accord.
4. **Déroule la méthode** : cibles (§1), mesure de la scène (§2), modèle du boîtier à partir d'une séance d'essais (§4), calcul des recettes (§5), boucle sur le boîtier (§6), tableau des écarts mesurés (§8). Reprends les outils du dépôt plutôt que de tout réécrire : ils sont écrits pour le D40 et le D750 et s'adaptent plus ou moins : `d750_blocs.py` (recalage JPEG / RAW, blocs uniformes), `kodachrome.py`, `films_nb.py`, `fuji_lut.py` et `rendus.py` (cibles) valent pour tout boîtier qui fait des RAW ; `d750_modele.py` et `d750_analyse.py` supposent un Picture Control et les cinq lots de l'auteur (noms `lot1` à `lot5`, groupes de vignetage de ses objectifs : `d750_analyse.py`, en tête) ; `mesures_reelles.py` et `d750_standard.py` sont câblés sur les dossiers et la mire de l'auteur, à réécrire. Il n'y a pas d'outil générique pour la matrice capteur → XYZ d'un autre boîtier : l'ajuster sur une mire (comme `d750_standard.py`) ou la calculer d'après camspec (`matrices_spectrales.py`).

## Règles (non négociables)

- **Rien n'est écrit dans un boîtier sans un « oui » explicite de la personne, pour cette écriture-là.** Les outils d'écriture simulent par défaut : lance toujours la simulation d'abord et montre ce qui serait écrit.
- **Avant toute écriture : sauver l'état** (contenu de l'emplacement, réglage actif), **après : relire** et comparer à l'envoi. Tiens un historique qui permet de revenir à chaque état.
- **Firmware** : jamais flasher un fichier qui n'a pas d'abord tourné dans un émulateur ou qui n'est pas identique à l'octet près à un fichier déjà testé. Étudie la récupération avant (que se passe-t-il si le boîtier ne démarre plus ?) et dis le risque en clair. Ne touche jamais au code de démarrage, au flasheur ni au noyau. Si un patch doit passer par la liaison entre processeurs (la V5 le fait : étape 9, `d40/patchs/pipboy-9-programme-a.json`), il ne modifie que ce qui part sur le fil dans un cas précis, il est rejoué dans l'émulateur des deux côtés, et le code ajouté à l'autre processeur reste dormant tant qu'on ne l'appelle pas.
- **Ne mets rien de propriétaire dans un dépôt** : ni firmware du fabricant, ni pseudo-code décompilé, ni LUT, profil ou table d'un tiers. Publie des empreintes, des mesures, des réglages calculés, et le lien vers la source officielle. Les outils qui fabriquent des patchs (`d40/outils/pipboy.py`, `preglages_v1.py`, `programmes_a.py`) écrivent les octets d'origine en clair dans `d40/patchs/` : ne commite jamais leur sortie telle quelle (le dépôt n'en garde que l'empreinte). Un binaire modifié ne se distribue que si la personne le décide, en disant que les droits du fabricant restent les siens.
- **Les photos de la personne restent chez elle** : ne les mets dans aucun dépôt, aucun envoi. Les lectures brutes du boîtier ne se partagent qu'avec son numéro de série effacé (il est dans le DeviceInfo USB).
- **Dis ce qui est mesuré** : sépare toujours « prévu » (calculé) et « mesuré » (JPEG sorti du boîtier), avec la médiane, le p90, le nombre de vues et la cible. Un écart qui ne descend pas est une information : explique la limite du format plutôt que de forcer.
- Travaille dans un dossier hors du dépôt pour les images et les fichiers lourds (`--travail`, `<chantier>` dans les commandes).

## Carte du dépôt

| Chemin | Ce qu'on y trouve |
|---|---|
| [`METHODE.md`](METHODE.md) | la méthode générale, à suivre |
| [`d40/README.md`](d40/README.md) | D40 : comment on a fait, fabriquer la V5 depuis le firmware officiel, flasher, limites |
| [`d40/CARTE.md`](d40/CARTE.md), [`d40/NOTES-TECHNIQUES.md`](d40/NOTES-TECHNIQUES.md) | carte du firmware (chaque fait avec son niveau de confiance) ; journal technique complet du chantier |
| `d40/patch.py`, `d40/patchs/`, `d40/fabriquer_v5.py` | patcher le firmware officiel (octets d'origine vérifiés par empreinte), refaire la V5 |
| `d40/outils/`, `d40/emulateur/`, `d40/desassemblage/` | décoder les tables, simuler le JPEG, fabriquer les patchs, émuler le firmware, régénérer l'analyse Ghidra |
| [`d750/README.md`](d750/README.md) | D750 : charger les recettes, séances d'essais, balance des blancs, mesure |
| `d750/outils/` | USB (Swift, macOS), analyse et mesure (Python) |
| `d750/recettes/` | recettes (`.json`) et blocs chargés (`.bin`), historique du boîtier de l'auteur |
| `d750/recherche/` | format USB du Picture Control, analyse des séances, résultats mesurés |
| [`d200/README.md`](d200/README.md) | D200 : firmware modifié par données (V2 flashée), patchs à appliquer au firmware officiel avec `d40/patch.py`, étage couleur à 16 secteurs décodé, émulateur du moteur d'image |
| [`645d/README.md`](645d/README.md) | 645D : Custom Image par USB (mode constructeur Pentax), recettes, mesure des filtres et des courbes, lecture du firmware |

Les notes de recherche citent les dossiers `images/` de l'auteur (photos) : les mêmes commandes s'appliquent aux tiens. Ses lectures USB du D750 (réglages, Picture Control avant et après chaque écriture, journaux) sont dans `d750/sondes/d750/usb/`, numéro de série effacé : un point de départ pour comprendre un autre boîtier. Même chose pour le 645D dans `645d/sondes/usb/`.

## Environnement

- Python 3.10 ou plus : `pip install -r requirements.txt`.
- D750 : macOS (ImageCaptureCore) et Swift (`xcode-select --install`). Sous Linux, libgphoto2 donne les mêmes commandes PTP, mais les outils sont à réécrire.
- D40 : `python3 d40/fabriquer_v5.py` range le firmware officiel dans `d40/firmware/` (hors git), où tous les outils du D40 le cherchent. Émulateur : JDK 17 ou plus et `git` (`python3 d40/emulateur/d40emu.py --cloner verifier`). Désassemblage : Ghidra et l'extension ghidra-fr60.
- Sources tierces (LUT Fujifilm, Status A d'agx-emulsion, spektrafilm, docs du SDK Nikon) : à récupérer soi-même, voir [`LICENCES-TIERS.md`](LICENCES-TIERS.md) ; les outils les attendent en argument ou dans une variable d'environnement (`D750_SPEKTRAFILM`, `D750_LOOKS`).
- Auto-tests rapides : `python3 d750/outils/picture_control.py --self-test` (sans rien d'autre) ; `python3 d40/patch.py --self-test` et `python3 d40/outils/courbes.py --self-test` demandent le firmware officiel dans `d40/firmware/`.
- Outils système : `exiftool` (rangement des séances, simulateur du D40), `unar` ou `7z` (paquets Nikon), Ghidra, un JDK 25 et l'extension ghidra-fr60 pour régénérer le désassemblage (`d40/desassemblage/regenerer.sh`).
