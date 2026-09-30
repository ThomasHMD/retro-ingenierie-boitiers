# D200 V2 : relecture indépendante avant flash

Relecture faite en octobre 2026, de 18:22 (heures lues par `date`), avant tout flash. Rien n'a été flashé, aucun fichier du projet n'a été modifié en dehors de ce rapport. Les fichiers de travail (refabrications, émulateur, scripts de contrôle, aperçu) sont dans `<dossier de travail>/relecture-v2/`.

- Fichier relu : `d200/build/v2/B2000201.BIN` (18:19:09), 3 932 160 octets, CRC `7a86`, sha256 **`428473ff8f915932327add759fd68dcec6c4c5ae2e0ce7b0c6530403e4aedbce`**.
- Recette : `d200/patchs/d200-v2.json` (18:19:09), 37 patchs.
- Référence : la V1 `d200/build/v1/B2000201.BIN`, sha256 `bb052a60…151d53`, relue (`d200-v1-relecture.md`) et flashée en octobre.

Marques : *vérifié* = lu dans les octets, rejoué ou recalculé ici, preuve citée ; *calculé* = résultat d'un modèle ou d'un simulateur, pas du boîtier ; *hypothèse* = déduit, non prouvé.

## Verdict : GO sur `428473ff8f915932327add759fd68dcec6c4c5ae2e0ce7b0c6530403e4aedbce`

La V2 est la V1 avec d'autres **données**, rien d'autre : 11 603 octets différents, tous dans la courbe N&B (Tri-X), les matrices et secteurs de Chrome et Positive, les courbes de FP4 et HP5, plus le CRC. Code, crochets, tables, textes et chaîne de mise à jour sont identiques à l'octet près à ceux de la V1. Toutes les valeurs sont dans les bornes des registres, au bon format, et dans l'enveloppe déjà passée par le boîtier (V1 et sondes 1 à 3). Le boîtier acceptera le fichier, la recette le refait à l'identique, l'émulateur est conforme sur ce fichier exact.

Réserves (aucune n'est bloquante pour les octets) :
1. **Procédure** : la doc désigne encore la V1 comme « seul fichier à flasher » (`d200-firmware-image.md` §10, `d200-preglages.md` §2 et §9). Aucun document du projet ne cite le sha256 de la V2. Au flash, contrôler sur la carte **`428473ff…aedbce`**, pas `bb052a60…`. Le reste du §10 s'applique tel quel (A 2.01 / B 2.01, batterie pleine, carte de retour). Constat 9.
2. **Choix « typée »** : la V2 est construite avec la variante typée (Chrome (Cb, Cr) × 0,8, Positive × 1,2). `d200-preglages.md` §5.4 dit que le choix fidèle / typée revient à Thomas ; seul un commentaire du code (`d200_preglages.py`, « choix de Thomas en octobre 2026 ») dit qu'il l'a fait. À confirmer par Thomas. Constat 8.
3. **Rendu, pas boîtier** : sous fluo de classe 3 (F = 4), Chrome et Positive n'appliquent plus que 17,5 % de la correction d'éclairage de Nikon (Positive : 45 % en V1) ; HP5 a des noirs mats à 37/255 voulus. Constat 7.

## Constats

### 1. Le BIN se refait à l'identique depuis la recette (vérifié)

- `python3 -B d40/patch.py d200/patchs/d200-v2.json --sortie <temporaire>` : 37 patchs, 22 688 octets changés depuis l'origine (CRC compris), CRC `7a86`, sha256 `428473ff…aedbce`. `cmp` : **identique** à `d200/build/v2/B2000201.BIN`. `controler_d200` (plages réécrites, zones interdites, aucun secteur vierge) passe : code 0.
- Même commande sur `d200-v1.json` : sha256 `bb052a60…`, identique à `d200/build/v1/`. `patch.py --self-test` : OK.
- Original : `d200/build/origine/B2000201.BIN` et le cache `~/Library/Caches/retro-ingenierie-boitiers/firmware/d200-201/B2000201.bin` sont identiques, sha256 `b7cee24d…07d1`.
- **Reconstruction indépendante de `patch.py`** (script à moi : application des 37 patchs avec contrôle des octets `avant`, CRC16 XMODEM calculé bit à bit, sans la table de `patch.py`) : même fichier, même sha256.
- **Régénération depuis les outils** (en mémoire, sans écrire) : `d200_preglages.rendus()` + `emplacement_octets()` redonnent les 4 emplacements du BIN octet pour octet ; `d200_nb.fabriquer('trix', 2)` redonne la courbe Tri-X ; `assembler()` et `tables_octets()` redonnent le code et les tables. Réglages des outils : `VARIANTE = 'type'`, `VERSION_NB = 2`.
- La recette est exactement `d200-nb-trix.json` (10) + `d200-noms.json` (19) + `d200-preglages.json` (8), dans cet ordre (offset, avant, après). Aucun chevauchement entre patchs. Les 6 blocs posés en place libre ont un `avant` entièrement à `0xFF`.
- Self-tests : `d200_preglages.py`, `d200_nb.py`, `d200_etage.py` : OK (code 0).

### 2. Taille, CRC, signature, version : le boîtier acceptera le fichier (vérifié)

| Contrôle de la mise à jour (`d200-firmware-image.md` §6) | V2 |
|---|---|
| Taille exacte `0x3C0000` | 3 932 160 |
| CRC16 XMODEM du fichier entier = 0 | `0x0000` (calcul bit à bit), CRC en gros-boutiste à la fin : `7a86` = CRC des 3 932 158 premiers octets |
| Signature : pointeur en `0xEFBF4` | `0x16CAB0`, `Q220FirmwareSignature\0`, identique à l'origine |
| Version : pointeur en `0xEFBF0` | `0x16CAC8`, `Ver.2.01 `, identique à l'origine |

### 3. Différences V1 → V2 : 11 603 octets, tous dans des données (vérifié)

Comparaison octet par octet des deux fichiers (238 plages contiguës) :

| Zone (adresses processeur) | Contenu | Octets différents | Sûr ? |
|---|---|---|---|
| `0x3B22DD-0x3B32DC` | courbe N&B de Nikon remplacée par Tri-X (patch 10), lue seulement par `FUN_000dcf50` pour le mode Noir et blanc | 3 223 / 4 096 | oui : même place, même format, déjà patchée en V1 |
| `0x177400-0x1774D7` | Chrome : 12 matrices caméra | 140 / 216 | oui : données copiées dans la puce, constat 4 |
| `0x1774EA-0x177569` | Chrome : 64 secteurs | 128 / 128 | oui |
| `0x178580-0x178657` | Positive : 12 matrices caméra | 111 / 216 | oui |
| `0x17866A-0x1786E9` | Positive : 64 secteurs | 87 / 128 | oui |
| `0x179880-0x17A87F` | FP4 : courbe | 3 870 / 4 096 | oui |
| `0x17AA00-0x17B9FF` | HP5 : courbe | 4 042 / 4 096 | oui |
| `0x40FFFE-0x40FFFF` | CRC (`47a1` → `7a86`) | 2 / 2 | oui |
| **hors de ces zones** | | **0** | |

Inchangés entre V1 et V2 : YCbCr et bourrage des 4 emplacements, courbes de Chrome et Positive, matrices, YCbCr et secteurs de FP4 et HP5.

Côté recette, seuls 5 patchs diffèrent de `d200-v1.json` (n° 10, 34, 35, 36, 37), par leur `apres` et leur texte ; `offset` et `avant` sont identiques.

### 4. Données décodées des quatre emplacements (vérifié)

Décodage direct du BIN, format de `d200-preglages.md` §3 : matrices en signe et module bit `0x400`, YCbCr et secteurs en signe et module bit `0x200`, courbe de 4 096 octets à `+0x180`.

**Format, pour les 4 emplacements** :
- 48 matrices : aucun demi-mot au-dessus de `0x7FF`, aucun « zéro négatif » `0x0400`, **aucune valeur en complément à deux** ; |coefficient| ≤ 1 000 (registre 1 023) ; les 144 lignes valent 512.
- YCbCr : BT.601 (77, 150, 29 / −43, −85, 128 / 128, −107, −21), lignes 256, 0, 0 : un gris reste gris. Négatifs codés `0x22B`, `0x255`, `0x26B`, `0x215`.
- Secteurs : aucun demi-mot au-dessus de `0x3FF`, aucun `0x0200`, |v| ≤ 317 (registre 511).
- Bourrage `+0x16A-+0x17F` : 22 octets à 0 partout.
- Courbes : 4 096 entrées, croissantes au sens large, de leur pied à 255.
- Aucun signe de décalage : les sommes de lignes (512, 256, 0, 0) casseraient au moindre décalage de 2 octets ; les adresses de `tbl_base` (`0x177230`) valent `0x177400`, `0x178580`, `0x179700`, `0x17A880`, comme en V1 ; la fin est en `0x17B9FF`.

**Chrome** (Moins net) :
- Matrice du jour (F = 1, sRGB) : 980 −577 109 / 27 604 −119 / 84 −291 719, égale à `d200/recettes/etage-v2.json`. Maximum 1 000 (F = 2). Adobe : maximum 739.
- Secteurs (b1 / b2 / b3 / b4) : diagonale b1 166 à 181, b4 210 à 228 ; termes croisés b2 −8 à −23, b3 −11 à −59. Ce sont les valeurs d'`etage-v2.json` × 0,8 arrondies.
- Déclinaisons réduites : F = 2 à 77,5 %, F = 4 à 17,5 %.

**Positive** (Saturé) :
- Matrice du jour : 980 −269 −199 / −187 980 −281 / −95 46 561, égale à `etage-v2.json`. Maximum 1 000 (F = 4). Adobe : maximum 973.
- Secteurs : diagonale b1 306 à 317, b4 276 à 287 ; termes croisés b2 −13 à +10, b3 −11 à 0. Valeurs d'`etage-v2.json` × 1,2.
- Déclinaisons réduites : F = 2 à 20 %, F = 4 à 17,5 % (45 % en V1).

**FP4** (Très saturé) : 12 matrices identiques, trois lignes 102, 48, 362 (inchangées) ; secteurs neutres ; courbe de 6 à 255 (V1 : 5 à 255).

**HP5** (Portrait) : trois lignes 81, 24, 407 (inchangées) ; secteurs neutres ; courbe de **37** à 255 (V1 : 7), noirs mats voulus par le tirage (`d200_nb.TIRAGE`, R 1,45, dmax 1,75).

**Tri-X** (`0x3B22DD`, patch de données) : 4 096 entrées croissantes, de 0 à 255, 255 atteint à l'entrée 3 496 (k = 0,861 : 4 095 × k ≈ 3 526). Octets voisins (`…59595959` avant, `4c4c4d4d` après) identiques à l'origine : pas de débordement. Instructions de la matrice et de la ligne Y (`0xD7840-0xD789D`) identiques à la V1 (121, 65, 255 ; 128, 128, 0).

### 5. Zones interdites, place libre, code : rien de touché (vérifié)

- **Identiques à l'origine** : `0xEFBF0-0xEFFFF` (pointeurs, vecteurs), `0x9A680-0x9B14A` (chaîne de mise à jour), `0x54552-0x54751`, `0x15D284-0x15D483` (table CRC), `0x15C72C-0x15CA63` (flasheur), toute la section `.data` `0x15387C-0x15C72B` (tables du flasheur comprises), `0x15E008-0x15E107`, `0x16C760-0x16C85F`, `0x16CB18-0x16CC17`, `0x16CAB0-0x16CAFF`, reset `0xDF48A-0xDFAAF`, relais `0x72BC0-0x72C0F`, `0xF0000-0x11FFFF`, `0x1D0000-0x1FFFFF`, table PTP `0x8D164-0x8D3E2`, jeux de matrices, courbes intégrées et table de saturation de Nikon.
- **Identiques à la V1** : code `0x177000-0x17716B`, tables `0x177200-0x177365` (signature `PREGLAGES-D200`, mode → emplacement `ff 00 01 02 03 ff…`, réglages `04 01 01 00` × 4), crochets `0xCDFAE` (`9F8C 0017 7000`, puis `971C`) et `0x5DA28` (`9F8C 0017 7060`, puis `971C`), instructions N&B, textes français, pointeur de l'id 252, texte « Positive » en `0x176600`. Le désassembleur de l'émulateur donne les mêmes 127 instructions sur les deux fichiers (diff vide), sans aucune forme `:D`, fin par `RET` en `0x17716A`. La relecture du code de la V1 (`d200-v1-relecture.md`, constats 3 et 6, delta D2) vaut donc pour la V2.
- **Place libre** : à `0xFF` dans le fichier V2 : `0x1765EA-0x1765FF`, `0x176612-0x176FFF`, `0x17716C-0x1771FF`, `0x177366-0x1773FF`, `0x17BA00-0x1CFFFF`, et `0x3F72A8-0x40FFFD` (les secteurs jamais programmés `0x3F8000-0x3FFFFF` sont intacts). Dans l'origine, Nikon finit en `0x1765E9`.
- **Secteurs touchés** (origine → V2) : `0x050000`, `0x0C0000`, `0x0D0000`, `0x170000` (24 444 octets de Nikon), `0x240000`, `0x250000`, `0x3B0000`, `0x400000` (le CRC de Nikon). Les mêmes 8 que la V1, tous programmés par chaque mise à jour officielle.

### 6. Émulateur (vérifié)

- `python3 -B d200/emulateur/d200emu.py --travail <temporaire> verifier` : **code de sortie 0**, 11 essais conformes. Le combiné qu'il fabrique depuis les recettes actuelles a le sha256 **`428473ff…aedbce`** : c'est bien le fichier relu.
  - a : 403 contrôles ; b et b″ : 1 738 ; c et c′ : 157 ; d : 1 781, 0 échec.
  - Contre-épreuves : b′ 420 échecs (la doc dit 422) ; d′ et d″ 1 218 échecs chacune.
  - Gardes : code 2. Pile d'`isp_chargerPuce` : 52 octets au lieu de 40, rendue à chaque appel.
- Sur le fichier lui-même : `scenario preglages --firmware d200/build/v2/B2000201.BIN` : code 0, 1 781 contrôles, 0 échec. `scenario nb-trix --firmware d200/build/v2/B2000201.BIN` : code 0, 1 738 contrôles (premier demi-mot de courbe `0x0000`, dernier `0x00FF`).
- **Contre-épreuve à moi** : le même scénario `preglages` joué sur la V1 échoue avec 812 écarts, dans les matrices caméra (`0x50010022-0x50010032`), les secteurs (`0x5001E4xx`) et les courbes. Le scénario contrôle donc bien les données de la V2, pas celles de la V1.
- **Limite** : les valeurs attendues du scénario sont écrites par `d200_preglages.py scenario` depuis les mêmes données que le patch. L'émulateur prouve que le code copie ces données au bon endroit, pas qu'elles sont saines ; c'est l'objet du constat 4, fait indépendamment sur les octets.

### 7. Risques pour le boîtier et pour le rendu

**Pour le boîtier : rien de nouveau** (vérifié côté octets et code, hypothèse forte côté puce).
- Le chemin des données est celui de la V1 : boucles `LDUH`/`STH` et `FUN_0005debe`, sans calcul, sans indice, sans saut qui dépende d'une valeur. Une valeur inattendue ne peut toucher que les pixels.
- Enveloppe déjà passée par le boîtier : secteurs jusqu'à 384 et termes croisés ±181 (sonde 1, photos prises), ±88 (sonde 3) ; la V2 va jusqu'à 317 et −59. Matrices jusqu'à 1 000 : comme la V1 (Chrome V1 aussi à 1 000). Courbes au même format que la V1.
- Code exécuté en `0x177000` : déjà fait par le boîtier avec la V1 et les sondes 1 à 3, d'après leurs photos (`d200-v1-relecture.md`, U2).
- Seule voie de brique identifiée, inchangée : une coupure pendant l'écriture.

**Pour le rendu** (calculé, simulateur `d200_rendus.rendre` alimenté par les octets décodés du BIN, sur `THM_5298.NEF` ; aperçu `apercu-v1-v2.jpg` dans le dossier temporaire) :
- Rien d'absurde : Chrome plus froid et plus sourd que la V1, Positive plus chaud et plus saturé, FP4 et HP5 plus doux, Tri-X plus contrasté. Gris neutres par construction (lignes de 512, YCbCr BT.601).
- Positive écrête un peu plus dans les noirs saturés (1,3 % des pixels avec un canal à 0, contre 0,2 % en V1) : effet du × 1,2.
- Gain de bruit de chroma par ligne de matrice : Chrome 2,32 (V1 2,17), Positive 2,07 (V1 2,08), contre au plus 1,84 pour les 294 jeux de Nikon. Le × 0,8 des secteurs de Chrome le compense en partie. À regarder à haut ISO, sans risque pour le boîtier.
- Fluo de classe 3 (F = 4) : déclinaison réduite à 17,5 % pour Chrome et Positive (Positive : 45 % en V1). La balance des blancs reste faite par Nikon, mais la correction de couleur de cet éclairage est presque absente : dominante possible sous ces tubes.
- Ce simulateur utilise le modèle de l'étage (`d200_etage`) qui a servi à l'ajustement : il ne prouve pas la fidélité, seulement l'absence d'aberration.

### 8. Variante couleur : « typée », à confirmer par Thomas (vérifié pour les octets ; décision non vérifiable)

Les secteurs du BIN sont ceux d'`etage-v2.json` × 0,8 (Chrome) et × 1,2 (Positive), soit `d200_rendus.TYPE`. La recette (« Chrome et Positive “typés” ») et le code (`VARIANTE = 'type'`) le disent. `d200-preglages.md` §5.4 écrit encore « Le choix fidèle / typée revient à Thomas avant toute construction ». Si Thomas voulait la fidèle, ce fichier n'est pas le bon : les octets ne changent pas de sûreté, seulement de rendu.

### 9. Documentation et procédure (vérifié)

- `d200-firmware-image.md` §10 : « `d200/build/v1/B2000201.BIN` … **Seul fichier à flasher** ; tout autre sha256 est périmé ». `d200-preglages.md` §2 et §9 : idem, `bb052a60…`. La recherche de `428473`, `build/v2` et `d200-v2` dans le projet ne trouve que la recette. Suivre le §10 à la lettre ferait contrôler `bb052a60…` sur la carte et refuser la V2. Il faut mettre à jour ces trois passages, ou au minimum contrôler `428473ff8f915932327add759fd68dcec6c4c5ae2e0ce7b0c6530403e4aedbce` sur la carte au moment du flash.
- Le reste du §10 s'applique tel quel : A 2.01 / B 2.01, batterie pleine, carte de retour.
- Retour arrière : la chaîne de mise à jour de la V2 est identique à celle de Nikon. On revient à la V1 (`bb052a60…`, déjà flashée et bonne) ou à l'origine (`b7cee24d…`) depuis le même menu. Quel que soit le firmware en place aujourd'hui (V1 ou une sonde), sa chaîne de mise à jour est celle de Nikon (relectures précédentes).

### 10. Points mineurs (sans effet sur les octets)

- La note du patch 10 dit seulement « courbe N&B trix » ; la description de `d200-nb-trix.json` précise bien « tirage V2 » (R 0,75, dmax 2,15).
- `d200-preglages.md` §5.2 donne pour la V1 des matrices du jour (Chrome 923 −407 −4…, Positive 923 −202 −209…) qui ne sont pas celles du BIN V1 (980 −443 −25… et 950 −220 −218…, celles de `d200/recettes/matrices.json`). Ce tableau est périmé.
- Contre-épreuve b′ : 420 échecs, la doc en annonce 422.

## Ce qui reste hypothèse

- Les accès aux registres de la puce par adresse calculée (non suivis).
- Le chargeur de démarrage `0x0F0000-0x11FFFF` (absent du fichier).
- Une coupure d'alimentation pendant l'écriture : seule voie de brique connue.
- La fidélité réelle des rendus V2 sur le boîtier (le simulateur ne s'appuie que sur le modèle de l'étage).
