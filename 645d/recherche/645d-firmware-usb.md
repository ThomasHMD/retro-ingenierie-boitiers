# Pentax 645D : ce que l'USB et la carte permettent de régler (firmware 1.33, lecture statique)

octobre 2026. Règle de Thomas : **aucune modification du firmware du 645D, jamais**. Tout ce qui suit est du **réglage** : envoyer au boîtier, par USB ou par un fichier sur la carte, des valeurs que ses menus savent déjà prendre. Le firmware n'a été que lu (téléchargé, décodé, désassemblé hors du boîtier), jamais exécuté ni renvoyé.

Légende : **vérifié** = lu dans les octets ou le code du firmware (adresse donnée, base `0x10000000`), ou dans une source citée avec lien ; **hypothèse** = déduction, à confirmer sur le boîtier avant d'agir. Rapports voisins : `carte/645d.md` (menus, manuel, brouillage), [`d750-picture-control-usb.md`](../../d750/recherche/d750-picture-control-usb.md) (même démarche sur le D750), `carte-des-possibles.md`.

> **Vérifié sur le boîtier en octobre 2026** : [`645d-usb-et-reglages.md`](645d-usb-et-reglages.md). Une correction : `DeviceInfo` n'annonce toujours que 5 propriétés en mode constructeur, mais les 52 codes répondent quand on les interroge un par un. Le reste du §0 côté PTP est confirmé ; le côté SCSI n'a pas pu être essayé (macOS refuse l'interface de stockage).

## 0. En bref

- **Le 645D se pilote par USB, mais seulement après une poignée de main constructeur.** En PTP ordinaire, il n'annonce que 5 propriétés (batterie, date, trois propriétés MTP) et refuse d'écrire quoi que ce soit d'autre. Après l'opération **0x9001 SetPentaxVendorMode (0x0D, 0x12E08, 1)**, il annonce 52 propriétés et accepte d'écrire le Custom Image. Vérifié (code `0x106c5fa0`, `0x106d29ee`, `0x108209f0`).
- **Réglable par PTP (mode constructeur)** : le mode Custom Image (8 modes), sa saturation, sa teinte, son contraste, sa netteté, la bascule netteté fine, l'espace couleur, la qualité JPEG, le mode d'entraînement, l'artiste, le copyright. Vérifié (code). **Pas** la balance des blancs, ni High/Low Key, ni Contrast Highlight/Shadow. Vérifié (absence dans le répartiteur `0x106d29ee`).
- **Réglable par les commandes SCSI Pentax (mode MSC, protocole de pkTriggerCord)** : tout ce qui précède, plus **la balance des blancs (17 modes), son réglage fin par mode, et trois températures Kelvin de 2 500 à 10 000 K**. Vérifié (code `0x10615238`, sous-commandes `[18 10]`, `[18 11]`, `[18 24]`). Aucun logiciel ne le fait aujourd'hui pour le 645D.
- **Par fichier sur la carte** : `MODSET.487` (mode service) peut exporter (`DSP_USR_DAT_READ`) et réimporter (`DSP_USR_DAT_WRITE`) un bloc de 8 Ko de réglages utilisateur, `KB487.USR`. L'export est sans risque pour le boîtier ; l'import est la seule voie qui atteindrait **tous** les paramètres (Key, hautes lumières et ombres, filtre et virage Monochrome), mais il passe par le mode service, sans somme de contrôle vue. Vérifié (code `0x1066b6f4`, `0x1066b7b2`) ; contenu exact du bloc : hypothèse.
- **Les trois pistes** (détail §8) : 1) PTP mode constructeur, avec l'outil Swift déjà écrit, étendu d'une opération ; 2) export de `KB487.USR` pour cartographier les octets, puis import si Thomas l'accepte ; 3) client SCSI pour la balance des blancs et le Kelvin.

## 1. Source et méthode

| Fait | Statut |
|---|---|
| Firmware officiel le plus récent : **1.33**, `645v133.zip` (sha256 `6529bf7121556bc89c4b6e1c0f893b131d1ae52e89ff579aece0fefe57bfc886`), contient `fwdc207b.bin` de 17 301 504 octets (sha256 `faa8f38aa9dd8908a07a0e91bcfe2deca86f68c1d2b97044c72fc1c19c063d8e`) | vérifié ([page Ricoh](https://www.ricoh-imaging.co.jp/english/support/digital/645d_s.html), [archive](https://www.ricoh-imaging.co.jp/english/support/digital/firmware/645v133.zip)) |
| Décodage : XOR de `pfwtool`, grand-boutiste, section 1 de `0x100` à `0x1000000`, section 2 à partir de `0x1000080` (début de bloc `0x80`). Résultat sha256 `08e07c0e6d0767c28839a079ab6eff89b59cb27828e63ed15e4f00c227003647` ; somme des mots de 32 bits nulle sur le fichier et sur la section 2 | vérifié (script `pfw_deobf.py` repris du rapport `carte/645d.md`) |
| Cœur Fujitsu FR grand-boutiste, image chargée en `0x10000000`, code de `0x100e8000` à `0x10970000` ; données initialisées du fichier (`0x4fa4` à `0x14000`) recopiées en RAM à partir de `0x80000000` (adresse RAM = décalage fichier + `0x7fffb05c`) | vérifié (désassemblage cohérent, tables PTP retrouvées par ces adresses, §3) |
| En-tête en clair : `0x10` = 487 (code modèle des fichiers `KB487…`, `MODSET.487`), `0x14` = **`0x00012E08`** (identifiant de modèle, même famille que ceux de pkTriggerCord : 645Z = `0x13010`) ; `0x74` : `25FB 00F0 00F1` (vendeur USB Pentax `0x25FB`, deux PID probables, MSC et PTP) ; chaînes `PENTAX`, `645D`, `DSC_645D` | vérifié (octets) ; rôle des deux PID : hypothèse |
| Outils : Python lancé en `-I`, Ghidra 12.2 avec le module FR60 (sans analyse automatique, décompilation fonction par fonction), un petit interpréteur FR écrit pour l'occasion (`frmini.py`) pour calculer type, accès et plage des propriétés PTP | vérifié |
| Aucun outil installé ; aucun ne manquait. Pas d'émulateur FR complet : seules des fonctions feuilles ont été exécutées | vérifié |

Scripts et décompilations : [`../desassemblage/`](../desassemblage/README.md) (rapatriés en octobre). Le firmware décodé et le projet Ghidra restent dans un dossier de travail hors du dépôt (`<dossier de travail>`), à refaire depuis le fichier officiel si besoin.

## 2. Architecture : une seule mécanique interne, trois portes d'entrée

| Fait | Statut |
|---|---|
| Le firmware exécute des **commandes internes numérotées (groupe, numéro)**, exactement celles du protocole SCSI documenté par pkTriggerCord (`[18 1B]` = Image Tone, `[18 20]` = saturation…). La fonction `0x108204b2(ctx, groupe, numéro, nb_args, args, …)` les lance ; elle rend une valeur non nulle en cas de succès | vérifié (code ; [protocole pkTriggerCord](https://github.com/asalamon74/pktriggercord/blob/master/pentax_scsi_protocol.md)) |
| **Porte 1, PTP ordinaire** : opérations standard (lecture des images). Propriétés annoncées : `5001`, `5011`, `D406`, `D407`, `D303`. `GetDevicePropDesc` ne répond que pour ces cinq ; `SetDevicePropValue` n'accepte que `D406`, tout le reste rend `0x200F` (accès refusé) | vérifié (code `0x106c5fa0`, `0x106d29ee` ; listes `0xa7b8`, `0xa822`) |
| **Porte 2, PTP mode constructeur** : ouverte par `0x9001`. Les propriétés `5004`, `5014`, `5015`, `D013`, `D020` à `D029`, `D032` deviennent lisibles et écrivables ; chaque écriture est traduite en commande interne du groupe `0x18` (tableau §4) | vérifié (code `0x106d29ee` et ses appelés `0x106d2c58` à `0x106d3372`) |
| **Porte 3, SCSI Pentax en mode MSC** (opcode `0xF0`, sous-commandes `0x24` envoi de commande, `0x4F` arguments, `0x26` état, `0x49` lecture du résultat, comme pkTriggerCord) : le gestionnaire du groupe `0x18` (`0x10615238`) exécute 33 numéros, dont ceux de la balance des blancs que le PTP n'expose pas | gestionnaire et numéros : vérifié (code) ; chemin USB MSC jusqu'à ce gestionnaire : hypothèse forte (même numérotation, signatures `USBC`/`USBS` présentes), à confirmer sur le boîtier |
| Le groupe `0x18` refuse tout (`0x84`) si une condition d'état n'est pas remplie (`0x10659670(…, 2)` doit rendre 2 ou 3) ; sens exact inconnu (mode PC actif ? écran de connexion ?) | condition : vérifié (code) ; sens : hypothèse |
| Les groupes `0x20`/`0x21` (« Write Setting » / « Read Setting » de pkTriggerCord, réglages de fonctions personnalisées par décalage) **n'existent pas** sur le 645D : le groupe `0x20` n'accepte que le numéro 0, le `0x21` les numéros 1 à 4, et ils partent vers l'autre processeur | vérifié (code `0x10605dfa`, `0x1060bac0`, `0x1060baca`) |
| Aucune opération PTP ne relaie une commande interne choisie par l'ordinateur : chacune des six opérations constructeur appelle des commandes fixes | vérifié (code des six gestionnaires, §3) |

## 3. Opérations PTP attendues

`GetDeviceInfo` rend une liste différente selon le mode (`0x106d0c6a` choisit la liste d'après l'indicateur de mode constructeur, octet `+0x308` du contexte PTP). Vérifié (code et listes `0xa7b8`, `0xa7e6`).

| Code | Nom | Mode ordinaire | Mode constructeur | Ce que fait le 645D | Statut |
|---|---|---|---|---|---|
| `1001` à `100D`, `1014` à `1016`, `101B` | GetDeviceInfo, OpenSession, CloseSession, GetStorageIDs, GetStorageInfo, GetNumObjects, GetObjectHandles, GetObjectInfo, GetObject, GetThumb, SendObjectInfo, SendObject, GetDevicePropDesc, GetDevicePropValue, SetDevicePropValue, GetPartialObject | oui | oui | standard | vérifié (listes) |
| `100B` DeleteObject, `100F` FormatStore | | oui | **non** | retirés en mode constructeur | vérifié (listes) |
| `9801`, `9802`, `9803`, `9805` | MTP : GetObjectPropsSupported, GetObjectPropDesc, GetObjectPropValue, GetObjectPropList | oui | oui | propriétés d'objets `DC01`… | vérifié (listes, `0x106d11d2`) |
| **`9001`** | **SetPentaxVendorMode** (nom d'IMAGE Transmitter 2) | oui | oui | 3 paramètres : **`0x0000000D`** (identifiant constructeur Pentax de PTP), **`0x00012E08`** (doit égaler le mot `0x10000014` de l'en-tête), **mode 0 ou 1**. Sinon `0x201D`. Lance en interne `[00 00]` Set Connect Mode, puis `[00 09]` avec 2 | vérifié (code `0x108209f0`, `0x108208ce` ; nom : chaînes d'IT2 `requestSendSetPentaxVenderMode:modelNumber:vendorMode:`) |
| `900F` | GetAllConditions (probable) | non | oui | rend l'état complet `[00 08]` (`0x6d` mots) complété de deux réglages | code : vérifié (`0x10820e92`) ; nom : hypothèse (IT2 : `receiveGetAllConditions:inData:vendorMode:modelNumber:`) |
| `9011` | InitiatePentaxCapture (probable) | non | oui | 3 paramètres bornés (≤ 2, ≤ 3, ≤ 1), déclenche via le groupe `0x10` | code : vérifié (`0x10821140`, `0x10821316`) ; nom : hypothèse |
| `9012` | TerminatePentaxCapture (probable) | non | oui | `[10 0C]` puis `[10 0D]` | code : vérifié (`0x10820c12`) ; nom : hypothèse |
| `9003`, `9004` | (SetCardWritingMode, InvokeCameraTask ?) | non | oui | `9003` : un paramètre transmis à `0x106c42d6` ; `9004` : un paramètre de 0 à 3 converti en deux indicateurs | code : vérifié (`0x10820658`, `0x10820adc`) ; noms : hypothèse |

Évènements annoncés : `4002` à `4005` (objet ajouté ou retiré, stockage ajouté ou retiré). Formats : `3000`, `3001`, `3006`, `3800`, `3801` (JPEG), `380D` (TIFF). Vérifié (listes `0xa81a`, `0xa89a`).

## 4. Propriétés PTP attendues

En mode constructeur, la liste annoncée a 55 entrées (52 codes distincts), lue en `0xa82c`. Type, accès et forme calculés en exécutant les fonctions du firmware `0x1081f59c`, `0x1081f8d8`, `0x1081fbea` ; commande interne relevée dans les gestionnaires d'écriture. Vérifié, sauf mention.

| Code | Nom (PTP ou déduit) | Type, accès | Écriture déclenche | Lecture vient de | Statut du nom |
|---|---|---|---|---|---|
| `5001` BatteryLevel | | UINT8, R, plage | | | vérifié (PTP) |
| `5004` CompressionSetting (qualité JPEG) | | UINT8, RW, liste | `[18 13]` | bloc `[18 00]` mot `0x19` | vérifié (PTP + code) |
| `5005` WhiteBalance | | UINT16, **R seulement**, liste | (aucune) | | vérifié |
| `5007`, `5008`, `500A` à `5010`, `5012`, `5013`, `501C` | FNumber, FocalLength, FocusMode, ExposureMeteringMode, FlashMode, ExposureTime, ExposureProgramMode, ExposureIndex, ExposureBiasCompensation, CaptureDelay, StillCaptureMode, FocusMeteringMode | lecture seule | | | vérifié (PTP) |
| `5011` DateTime | | STR, RW | | | vérifié |
| **`5014` Contrast** | contraste du Custom Image courant | UINT8, RW, liste | `[18 22]` (paramètre 3) | mot `0x1E` | vérifié |
| **`5015` Sharpness** | netteté du Custom Image courant | UINT8, RW, liste | `[18 21]` (paramètre 4) | mot `0x1D` | vérifié |
| `501E` Artist, `501F` CopyrightInfo | | STR, RW | | | vérifié (PTP) |
| `D001` à `D005` | tableaux d'état (`[00 04]`+`[00 06]`+`[00 07]`, `[00 01]`, `[00 08]` complet, `[1A 00]`, `[1A 01]`) | AUINT32, R | | | contenu : vérifié (code `0x106c66ec`) ; sens de chaque mot : hypothèse (proche de pkTriggerCord) |
| `D006`, `D011`, `D012`, `D014` à `D017`, `D01A`, `D01B`, `D01F`, `D030`, `D031` | inconnus | type non résolu ; annoncés RW sauf `D006`, `D016` | **refusé** (`0x200F`) : absents du répartiteur d'écriture | | vérifié (refus) ; rôle : inconnu |
| `D013` | mode d'entraînement | UINT32, RW, liste | `[18 1C]` | mot `0x0E` | vérifié (code + enum pkTriggerCord) |
| **`D020`** | **mode Custom Image** (codes USB 0 à 7) | UINT8, RW, liste | `[18 1B]` | mot `0x1B` | vérifié |
| **`D021`** | **saturation** (0 à 8) | UINT8, RW, liste | `[18 20]` (paramètre 1) | mot `0x1C` | vérifié |
| **`D022`** | **teinte** (0 à 8) | UINT8, RW, liste | `[18 25]` (paramètre 2) | mot `0x36` | vérifié |
| `D023` | inconnu | UINT8, RW annoncé | **toujours refusé** (`0x201C`) : le gestionnaire lit l'octet et rend 0 | | vérifié (désassemblage `0x106d314c`) |
| `D024` | doublon de `D021` côté boîtier (filtre Monochrome pour le logiciel ?) | UINT8, RW, liste | `[18 20]` | mot `0x1C` | code : vérifié ; rôle : hypothèse |
| `D025` | doublon de `D022` (virage Monochrome pour le logiciel ?) | UINT8, RW, liste | `[18 25]` | | code : vérifié ; rôle : hypothèse |
| `D026` | **netteté fine** oui/non (paramètre 6) | UINT8, RW, 0 ou 1 | `[18 26]` | mot `0x37` | code : vérifié ; nom : hypothèse forte (manuel : « Sharpness ou Fine Sharpness ») |
| `D027` | réglage `0x3B` oui/non (correction des hautes lumières ?) | UINT8, RW, 0 ou 1 | `[18 27]` | réglage `0x3B`, mot `0x39` du bloc `[18 00]` (chemin de lecture PTP non suivi) | code : vérifié ; nom : hypothèse |
| `D028` | inconnu | UINT8, RW annoncé | **toujours refusé** (`0x201C`) | | vérifié (`0x106d32f0`) |
| `D029` | espace couleur (sRGB / AdobeRGB) | UINT32, RW, liste | `[18 23]` | réglage `0x5A`, mot `0x1F` du bloc (chemin de lecture PTP non suivi) | vérifié (code + pkTriggerCord) |
| `D032` | préfixe des noms de fichiers | STR, RW | écrit « `_` » + 3 caractères | | code : vérifié ; nom : hypothèse forte (`IMGP` / `_IGP`) |
| `D303`, `D406`, `D407` | UseDeviceStageFlag, SessionInitiatorInfo, PerceivedDeviceType (MTP) | | | | vérifié (ptp.h) |

Les valeurs 0 à 8 des réglages ±4 se lisent probablement −4 à +4 avec 4 = 0 (hypothèse, à confirmer en lisant la valeur après un réglage au menu).

## 5. Réglages d'image dans le firmware

### 5.1 Custom Image : 8 modes × 10 paramètres, par banque

| Fait | Statut |
|---|---|
| Chaque mode garde ses propres valeurs : un octet par paramètre à `base + banque × 0x412 + 0x178 + mode × 10 + paramètre` ; le mode courant est un mot de 16 bits à `+0x170` de la banque. Deux copies sont écrites à chaque fois (`ctx+0x14` et `ctx+0xC`) | vérifié (code `0x1060112c`, `0x10601154`, `0x1066e5de`) |
| La **banque** vaut par défaut l'octet `ctx+0x11B8` ; tous les réglages (Custom Image et autres) sont rangés par banque | vérifié (code `0x1066e5de`, `0x1066f114`) |
| Une banque = la position **USER** du barillet, l'autre le réglage normal : on pourrait donc garder **deux Monochrome** (Tri-X et HP5), un par banque | hypothèse (le manuel ne décrit qu'un emplacement USER, `carte/645d.md`) |
| Codes USB du mode (pkTriggerCord) : 0 Natural, 1 Bright, 2 Portrait, 3 Landscape, 4 Vibrant, 5 Monochrome, 6 Muted, 7 Reversal Film ; conversion interne 0→0, 1→1, 2→2, 3→3, 4→4, 5→7, 6→5, 7→6 | conversion : vérifié (`0x106181b2`) ; noms : vérifié (pkTriggerCord, et 8 modes au manuel) |
| Paramètres atteints par USB : **1** saturation (`[18 20]`), **2** teinte (`[18 25]`), **3** contraste (`[18 22]`), **4** netteté (`[18 21]`), **6** booléen (`[18 26]`) | vérifié (code `0x10616d06`, `0x10616e94`, `0x10616dae`, `0x10616d5a`, `0x10616ee8`) |
| Paramètres **sans commande USB** : **0** (High/Low Key ?), **5**, **7** (booléen), **8**, **9**. Le manuel en annonce justement cinq de plus que ceux de l'USB : High/Low Key, Contrast Highlight, Contrast Shadow, la bascule contraste simple / hautes lumières et ombres, le filtre et le virage Monochrome | indices et absence : vérifié (`0x107eb52a` lit les 10 ; accesseurs `0x107a56f8` à `0x107a5a64`) ; correspondance indice ↔ nom : hypothèse |
| Le filtre et le virage Monochrome partagent peut-être les cases saturation (1) et teinte (2), puisque le manuel retire saturation et teinte en Monochrome et que le PTP a deux propriétés jumelles (`D024`, `D025`) pointant sur les mêmes commandes | hypothèse ; c'est le premier point à trancher sur le boîtier (§9) |
| Une table de valeurs par défaut existe par mode (jusqu'à 29 entrées), lue par le développement RAW dans le boîtier (`0x107934da`) | vérifié (code) ; valeurs : non lues |

### 5.2 Balance des blancs

| Fait | Statut |
|---|---|
| 17 modes : 0 auto, 1 lumière du jour, 2 ombre, 3 nuageux, 4 à 6 fluorescents, 7 tungstène, 8 flash, 9 à 11 manuel 1 à 3, 12 à 14 **Kelvin 1 à 3**, 15 fluorescent L, 16 CTE. `[18 10]` les choisit (réglage interne `0x0B`, et mémorise le sous-type dans `0x0C`, `0x0D`, `0x0E`) | code : vérifié (`0x106166ca`) ; noms : vérifié ([pkTriggerCord](https://github.com/asalamon74/pktriggercord/blob/master/pentax_scsi_protocol.md)) |
| **Réglage fin par mode** : `[18 11] (mode, a, b)` écrit deux réglages propres au mode (table de 17 lignes en `0x108b9db0` : mode 0 → réglages `0x0F`/`0x10`, … , mode 16 → `0x23`/`0x24`). Le bloc `[18 00]` relit ceux du mode courant (mots `0x15`, `0x16`). Aucun contrôle de plage dans le gestionnaire | vérifié (code `0x1061674e`, `0x10615cd8`) ; axes (vert-magenta, bleu-ambre ±7) et codage : hypothèse |
| **Kelvin** : `[18 24] (case 0 à 2, valeur en K)` arrondit au premier échelon ≥ valeur d'une table de 89 échelons de 2 500 à 10 000 K et range l'indice dans le réglage `0x2D`, `0x30` ou `0x33`. La table mêle les pas de 100 K et les pas de 20 mireds (2 630, 2 780, 2 940, 3 130, 3 330, 3 570, 3 850, 4 170, 4 550, 5 560, 6 250, 7 140, 8 330 K) | vérifié (octets `0x108b47d8`, code `0x10616e38`, `0x105f8b4a`) |
| La balance des blancs **n'est pas** réglable par PTP sur le 645D, même en mode constructeur (`5005` en lecture seule, aucune propriété `D0xx` vers `[18 10]`, `[18 11]`, `[18 24]`) | vérifié (code `0x106d29ee`) |

### 5.3 Bloc de réglages `[18 00]` (58 mots de 32 bits)

Lecture sans effet de bord ; c'est ce que lit `GetDevicePropValue` en mode constructeur. Mots identifiés (vérifié, code `0x10615cd8` et `0x106c66ec`) : `0x0E` entraînement, `0x14` mode de balance des blancs, `0x15`/`0x16` réglage fin du mode courant, `0x17` à `0x1A` format et qualité (`0x19` = qualité JPEG), `0x1B` mode Custom Image, `0x1C` saturation, `0x1D` netteté, `0x1E` contraste, `0x1F` espace couleur, `0x35` température Kelvin courante (en K), `0x36` teinte, `0x37` paramètre 6, `0x39` réglage `0x3B`. Les autres mots (exposition, ISO, AF) n'ont pas été nommés.

### 5.4 Autres données lisibles

| Fait | Statut |
|---|---|
| Six matrices 3 × 3 en entiers de 16 bits, lignes de somme 256, répétées trois fois en `0x613c` et `0x813c` (par exemple `444 −182 −6 / −18 304 −30 / −8 −61 325`) | vérifié (octets) ; rôle (matrices couleur par mode, éclairage ou espace) : hypothèse ; utiles au simulateur, pas à modifier |
| Aucune table de poids R/V/B de filtre Monochrome trouvée sous forme de matrice à lignes égales | vérifié (absence, balayage `scan_mono.py`) ; les poids restent à mesurer (méthode du §A.3 de `carte/645d.md`) |
| `SYSPARAM.TXT` (carte) ne règle que des paramètres de service capteur et bruit (`FORCENR`, `SENSORREG0`…, `FORCE_FINE_SHARPNESS`), rien sur les courbes ou les couleurs | vérifié (chaînes `0x944868` à `0x944dd4`) |
| Les filtres numériques de lecture existent dans le code (`DigitalFilterMonotone`, `Retro`, `Custom`, `BaseMake`, `HighContrast`…) | vérifié (chaînes) ; ils s'appliquent après coup, image par image |

## 6. Fichiers lus ou écrits sur la carte

| Fichier | Rôle | Statut |
|---|---|---|
| `MODSET.487` | Fichier de commandes de service, une par ligne : `DEBUG_MODE EN/DIS`, `SCRIPT_EN_MODE EN/DIS`, `OPEN_DEBUG_MENU`, `USR_DAT_CLEAR`, `DSP_USR_DAT_READ`, `DSP_USR_DAT_WRITE`, `CPU_ADJ_DAT_READ/WRITE`, `DSP_ADJ_DAT_READ/WRITE`, `CPU_ROM_STORE`, `DSP_ROM_STORE`, `REGION_CODE 0` à `5`, `CRE_RECOVERY_FW`, tests | chaînes : vérifié (`0x942994` à `0x942d24`) ; effet de chaque ligne : non testé |
| **`KB487.USR`** | **Bloc de 8 Ko (0x2000) de réglages utilisateur.** `DSP_USR_DAT_READ` lit la zone non volatile n° 2 et l'écrit sur la carte ; `DSP_USR_DAT_WRITE` lit le fichier (refusé s'il ne fait pas exactement 0x2000 octets), l'écrit dans la zone n° 2, puis recharge les réglages | vérifié (code `0x1066b6f4`, `0x1066b7b2` ; les deux lignes sont reconnues par `0x1080025c` et exécutées par `0x108008a6`, nom de fichier `C:\KB%03d.USR`) ; aucune somme de contrôle vue à l'import : vérifié dans ces deux fonctions, pas plus loin ; contenu = Custom Image, balance des blancs, etc. : hypothèse (rechargement des réglages juste après) |
| `AUTORUN.487`, `CHKDAT.487` | Interpréteur de scripts de service (`#DEFINE`, `GOTO`, `IF`, `WHILE`, `WAIT`, `PRINT`, `FILEOUT`, `TIMERON`…), activé par `SCRIPT_EN_MODE EN` ; messages « Command Not Support », « Command is Rejected » | chaînes : vérifié ; qu'un script envoie des commandes `[18 xx]` : hypothèse forte |
| `SYSPARAM.TXT` | Paramètres de service capteur et bruit (§5.4) | vérifié (chaînes) |
| `KB487ADJ.CSV`, `KB487.ADJ`, `KB487CPU.ADJ`, `KB487CPU.BIN`, `KB487DSP.BIN`, `KB487CAM.LOG`, `KB487INF.TXT` | Réglages d'usine (étalonnages) et sauvegardes de mémoire | chaînes : vérifié ; **à ne jamais réécrire** |
| `FWDC207B.BIN`, `KB487.BIN`, `LENSCPU.bin` | Mises à jour de firmware (boîtier, processeur secondaire, objectif) | vérifié (chaînes) ; **hors sujet, interdit** |

Le fil PentaxForums « Debug mode MODSET file 645D » dit que `MODSET.487` ouvre un menu de débogage sans code ([fil](https://www.pentaxforums.com/forums/48-pentax-medium-format/128289-debug-mode-modset-file-645d.html)) : non vérifié (page inaccessible), cohérent avec les chaînes.

## 7. Logiciels Pentax et libres

| Logiciel | 645D ? | Ce qu'il envoie | Statut |
|---|---|---|---|
| IMAGE Transmitter (1), 2012, payant, Windows 7 / Mac OS X, USB 2.0 | oui, fait pour lui | déclenchement à distance et transfert ; le communiqué ne cite aucun autre réglage | vérifié ([communiqué Ricoh](https://www.ricoh-imaging.co.jp/english/news/announce/20120208_2.html)) ; vendu sur CD-ROM, aucun paquet téléchargeable trouvé, donc rien lu |
| IMAGE Transmitter 2, v2.6.2 du 28/04/2023 | **non** (645Z, K-1, K-3 III…) | même famille d'opérations : `SetPentaxVendorMode(modelNumber, vendorMode)`, `GetAllConditions`, `InitiatePentaxCapture`, `SetCardWritingMode`, `InvokeCameraTask` ; gère `saturation`, `hue`, `key`, `contrast`, `exContrastHightLight`, `exContrastShadow`, `sharpness`, `fineSharpness`, `filterEffect`, `monotoneToning` | vérifié (chaînes du binaire Mac, lu sans l'installer ni le lancer ; [page Ricoh](https://www.ricoh-imaging.co.jp/english/support/digital/image_transmitter2_mac.html)) |
| Digital Camera Utility 4 (4.40 Windows, 4.41 Mac) | oui | développement RAW sur ordinateur ; pas de pilotage décrit | vérifié (page de téléchargements Ricoh) |
| REMOTE Assistant 3.51 | non (K10D, K20D) | | vérifié |
| libgphoto2 (`camlibs/ptp2`, branche master) | **non** : aucun 645 ; seule propriété Pentax décrite : `0xD00F` vitesse (Ricoh) | | vérifié (`library.c`, `ptp.h`) |
| pkTriggerCord | **non** : aucun identifiant `0x12E08` (645Z = `0x13010`) ; il parle le protocole SCSI du §2, porte 3 | | vérifié (`pslr_model.c`) |

## 8. Pistes pour charger des rendus

### Piste 1 : PTP mode constructeur, avec la sonde Swift existante (la plus rapide)

Ajouter à [`../outils/645d_ptp.swift`](../outils/645d_ptp.swift) (ImageCaptureCore, déjà utilisé pour envoyer `0x90CD` au D750) : `0x9001 (0x0D, 0x12E08, 1)`, puis `SetDevicePropValue` sur `D020` (mode), `D021` (saturation), `D022` (teinte), `5014` (contraste), `5015` (netteté), `D026` (netteté fine), puis `0x9001 (0x0D, 0x12E08, 0)`. Un rendu = 5 à 6 octets. Rien d'autre à installer. Couvre : la base de chaque rendu couleur (Muted ou Natural pour Portra, Reversal Film pour Kodachrome) et, si le filtre et le virage partagent les cases 1 et 2, le Monochrome entier sauf Key et hautes lumières / ombres. Ne couvre pas : balance des blancs, Key, Contrast Highlight / Shadow. Statut : mécanisme vérifié (code) ; comportement réel du boîtier : à confirmer (§9).

### Piste 2 : `KB487.USR`, d'abord en export seul (la plus complète)

1) `MODSET.487` avec la seule ligne `DSP_USR_DAT_READ` : le boîtier écrit `KB487.USR` sur la carte, sans toucher à ses réglages (vérifié, code). 2) Changer **un** paramètre au menu (par exemple Monochrome, filtre Bleu), réexporter, comparer les deux fichiers : chaque octet du Custom Image, de la Key, des hautes lumières et ombres, du filtre, du virage, du réglage fin de balance des blancs se retrouve ainsi, banque par banque. C'est la calibration « un réglage, un octet » du D750. 3) Seulement si Thomas l'accepte : réimporter un fichier modifié (`DSP_USR_DAT_WRITE`) pour charger un rendu complet d'un coup, avec `USR_DAT_CLEAR` comme retour aux réglages d'usine. C'est encore du réglage (aucun octet de firmware), mais par le mode service et sans somme de contrôle vue : un octet hors plage irait droit dans les réglages. Statut : export et import vérifiés (code) ; nécessité de `DEBUG_MODE EN` avant ces lignes : inconnue ; contenu du bloc : hypothèse.

### Piste 3 : client SCSI (balance des blancs et Kelvin sans mode service)

Un petit client du protocole pkTriggerCord (`[18 10]` mode, `[18 11]` réglage fin, `[18 24]` Kelvin, plus tout le Custom Image du §5.1) en mode USB MSC. pkTriggerCord lui-même refuse un identifiant inconnu : il faudrait déclarer `0x12E08` côté ordinateur (aucun changement dans le boîtier). Sous macOS, envoyer une commande SCSI constructeur à une carte montée demande de la démonter et un accès IOKit particulier ; sous Linux, pkTriggerCord le fait déjà. Statut : commandes vérifiées (code) ; acceptation réelle en MSC et faisabilité sous macOS : hypothèse.

### Autres voies

- **Développement RAW dans le boîtier** : rejoue les 10 paramètres Custom Image sur un PEF ; sans risque, manuel, c'est l'outil de mesure (poids des filtres Bleu et Cyan contre la fiche HP5). Vérifié (manuel, code `0x107934da`).
- **Script `AUTORUN`** : remettrait un rendu à chaque allumage. Hypothèse, mode service.

### Ce que chaque rendu demande, et par où

| Rendu | Réglages | Piste 1 (PTP) | Piste 2 (fichier) | Piste 3 (SCSI) |
|---|---|---|---|---|
| Tri-X | Monochrome, filtre (aucun ou Cyan léger), contraste fort, hautes lumières / ombres, Key, netteté | mode, contraste, netteté ; filtre si case 1 | tout | comme piste 1 |
| HP5 | Monochrome, filtre **Bleu ou Cyan**, contraste modéré, virage 0 | idem | tout | comme piste 1 |
| Portra 400 | Muted ou Portrait, saturation −1/−2, contraste bas, teinte ±1, **balance chaude par réglage fin** | tout sauf la balance | tout | tout |
| Kodachrome | Reversal Film ou Vibrant, saturation et contraste +, **Kelvin fixe** | tout sauf la balance | tout | tout |

## 9. À confirmer sur le boîtier branché

1. **Avec la sonde telle quelle** (PTP ordinaire, lecture seule) : `GetDeviceInfo` doit annoncer 23 opérations (dont `9001`) et **5 propriétés seulement** (`5001`, `5011`, `D303`, `D406`, `D407`) ; le `--balayage` sur `0xD000`-`0xD2FF` doit échouer partout ailleurs (`0x200A` ou réponse vide). C'est attendu, pas une panne. Prévision : vérifié (code `0x106c5fa0`, `0x106c61ec`).
2. **Ouvrir le mode constructeur** : `0x9001` avec `0x0000000D`, `0x00012E08`, `1`. Attendu : réponse `0x2001` ; un autre identifiant rend `0x201D`. Puis `GetDeviceInfo` : 26 opérations (avec `900F`, `9011`, `9012`, `9003`, `9004`, sans `100B` ni `100F`) et 55 propriétés. Cette opération change un mode de connexion, pas un réglage ; elle doit être ajoutée volontairement à la liste blanche `lectures` de la sonde. Refermer par `0x9001 (0x0D, 0x12E08, 0)`.
3. **Lire** (`GetDevicePropDesc`) `D013`, `D020` à `D029`, `D032`, `5004`, `5005`, `5014`, `5015` : plages, valeurs par défaut et courantes ; vérifier le codage 0 à 8 = −4 à +4.
4. **Trancher le Monochrome** : régler au menu Monochrome, filtre Bleu, virage +2 ; relire `D021`, `D022`, `D024`, `D025`. Si `D024` = indice du Bleu et `D025` = virage, filtre et virage sont dans les cases 1 et 2 et la piste 1 suffit au noir et blanc.
5. **Écriture** (seulement avec l'accord de Thomas) : écrire `D021` sur un mode peu utilisé, vérifier à l'écran, remettre la valeur ; éteindre et rallumer pour voir si la valeur tient (fonction Memory) ; recommencer sur le barillet en USER pour savoir si la banque change.
6. **Mode MSC** (menu R2 « USB Connection ») : le volume apparaît-il, `[00 04]` (identité) rend-il `0x12E08` ? Sans client SCSI, ce point attend la piste 3.
7. **Export `KB487.USR`** (piste 2, étape 1) : taille 8 192 octets attendue ; deux exports successifs sans changement doivent être identiques.

## 10. Limites

- Analyse statique seulement : aucun réglage n'a été envoyé, aucun paquet USB observé. Les noms `900F`, `9011`, `9012`, `9003`, `9004` viennent des chaînes d'IT2, pas du code du 645D.
- Le chemin interne entre l'opcode SCSI `0xF0` et le gestionnaire du groupe `0x18` n'a pas été suivi instruction par instruction.
- Les indices Custom Image 0, 5, 7, 8, 9 ne sont pas nommés ; la piste 2 les nomme sans risque.
- `D011`, `D012`, `D014` à `D017`, `D01A`, `D01B`, `D01F`, `D030`, `D031` : annoncées mais ni typées ni écrivables par le code lu ; leur lecture sur le boîtier dira ce qu'elles contiennent.

## Sources

- Firmware 1.33 : [page Ricoh 645D](https://www.ricoh-imaging.co.jp/english/support/digital/645d_s.html).
- Protocole SCSI Pentax : [pkTriggerCord, `pentax_scsi_protocol.md`](https://github.com/asalamon74/pktriggercord/blob/master/pentax_scsi_protocol.md), [`pslr_model.c`](https://raw.githubusercontent.com/asalamon74/pktriggercord/master/pslr_model.c).
- PTP : [libgphoto2 `camlibs/ptp2`](https://github.com/gphoto/libgphoto2/tree/master/camlibs/ptp2) (`ptp.h`, `library.c`).
- IMAGE Transmitter 2 : [page Mac](https://www.ricoh-imaging.co.jp/english/support/digital/image_transmitter2_mac.html), [page Windows](https://www.ricoh-imaging.co.jp/english/support/digital/image_transmitter2_win.html) ; IMAGE Transmitter (1) : [communiqué du 08/02/2012](https://www.ricoh-imaging.co.jp/english/news/announce/20120208_2.html) ; compatibilités : [PentaxForums](https://www.pentaxforums.com/reviews/pentax-image-transmitter-2/compatibility.html).
- Mode service : [fil « Debug mode MODSET file 645D »](https://www.pentaxforums.com/forums/48-pentax-medium-format/128289-debug-mode-modset-file-645d.html).
- Menus et manuel du 645D : voir `carte/645d.md`.
