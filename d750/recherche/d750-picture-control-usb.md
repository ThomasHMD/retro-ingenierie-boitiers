# Picture Control du D750 par USB : format exact, courbe perso, séquences de lecture et d'écriture

Recherche d’octobre 2026. Analyse statique seulement : aucune commande n'a été envoyée à un boîtier, aucun firmware n'a été modifié ni flashé. Le firmware officiel a été ouvert dans le bac à sable du cloud, en lecture seule.

Légende : **vérifié** = lu dans le code désassemblé (adresse donnée), dans un document cité ou dans les octets lus sur le D750 de Thomas ; **hypothèse** = déduction, à confirmer avant d'agir.

Les adresses sont celles du processeur pour la partie B du firmware **C 1.15** (celle du boîtier de Thomas), chargée à `0x90020000`. La 1.10 a la même logique, décalée (§7).

---

## 1. En bref

| Question | Réponse | Statut |
|---|---|---|
| Où est la courbe perso ? | **Dans le bloc de 0x90CC / 0x90CD lui-même.** Sans courbe, le bloc fait 32 octets et l'octet 31 vaut 0 ; avec une courbe, l'octet 31 vaut 1 et 578 octets suivent : **610 octets**. Il n'y a pas d'autre commande, ce qui explique l'absence de CurveDownload / CurveUpload (0x90C5 / 0x90C6 n'existent pas dans la table PTP du D750) | vérifié (firmware, doc Nikon) |
| Les 578 octets ? | 64 octets d'entête puis 257 valeurs sur 16 bits, **gros-boutistes**. C'est **octet pour octet** le contenu de l'enregistrement de type 2 d'un fichier `.NCP` | vérifié (firmware : même inversion d'octets dans le chargeur NCP et dans le PTP) |
| Rôle du second paramètre ? | Lecture (0x90CC) : **DefaultFlag**, 0 = réglage courant, 1 = réglage par défaut (celui de l'enregistrement). Écriture (0x90CD) : **ModifiedFlag**, 0 = nouvel enregistrement (courant et défaut), 1 = retouche du courant seulement. Aucune autre valeur n'est acceptée, et il faut exactement deux paramètres | vérifié (firmware, doc Nikon) |
| Pourquoi p2 ne changeait que Monochrome, Kodachrome et TRI-X ? | Ce sont les trois Picture Control retouchés après coup : leur réglage courant diffère de celui enregistré (par exemple TRI-X enregistré en filtre rouge, utilisé en orange) | vérifié (octets lus) ; histoire des retouches : déduite |
| L'octet 23 « inconnu » des couleurs ? | **QuickAdjustFlag** (accentuation rapide active) ; l'octet 24 est sa valeur. Le boîtier refuse l'accentuation rapide sur un Picture Control perso | vérifié |
| Peut-on écrire C-7 avec une courbe ? | Oui, en une commande : 0x90CD (207, 0) avec un bloc de 610 octets. Outil du §6 (`d750_ecrire.swift`), vérifié sur le boîtier au §9 | vérifié (chemin du code) ; effet réel sur le boîtier : à confirmer |
| Avant toute écriture USB | Une vérification sans écriture USB est possible : charger un `.NCP` avec courbe par la carte (menu du boîtier), puis le relire par 0x90CC (§5) | proposition |

Correction d'une erreur antérieure : `conf/b750103a.dfr.txt` de nikon-firmware-tools, cité comme « firmware B 1.03 du D750 », décrit en réalité le **D7000** (première ligne du fichier : « describes the D7000 "B" firmware, ver 1.03 »). Ses adresses 0x00132648 et 0x0013294A ne valent pas pour le D750. Vérifié.

---

## 2. Sources et méthode

| Source | Ce qu'elle apporte | Où |
|---|---|---|
| Doc USB du SDK Nikon du **D5000** (`D5000UsbMtpE_01.doc`, §5.2.30 à 5.2.33, §6.4, §9.1) | Format du bloc de la génération Picture Control 1 (31 octets + 578 de courbe), MonochromeFlag, CustomFlag, CustomCurveFlag, format de la courbe, DefaultFlag et ModifiedFlag, codes de réponse | dépôt public [RITMechArch/MechArch](https://github.com/RITMechArch/MechArch), `lib/D5000 SDK/Command/English/` |
| Doc USB du SDK Nikon du **Z 50** (`Z 50UsbMtpE_04.pdf`, §6.2.2.39 à 6.2.2.42, §9.8, §9.9) | Même famille de commandes, version récente : courbe à 578 octets, paramètre facultatif « menu photo / menu vidéo » | dépôt public [cuzelac/nikon-z50-prusa](https://github.com/cuzelac/nikon-z50-prusa), `docs/sdk/Command/English/` |
| Exemple du SDK (`Function.c`, D5000) | Numérotation 1 à 6, 101 à 104, 201 à 209 ; taille maximale du bloc : 609 octets | même dépôt MechArch, `Type0003CtrlSample(Win)/Function.c`, `MAX_PIC_CTRL_DATA_SIZE` |
| Doc MAID du SDK Z 50 (`MAID3Type0025(E).pdf`, §3.39) | `NkMAIDPicCtrlData` : `ulPicCtrlItem`, `ulSize` (614 au plus sur Z 50), `bModifiedFlag` (false = enregistrement, true = retouche), `pData` = le même bloc | dépôt nikon-z50-prusa, `docs/sdk/Module/Documents/English/` |
| Firmware **C 1.15** | Vérité terrain pour le D750 | `F-D750-V115M.dmg` fourni par Thomas ; `D750_0115.bin` sha256 `6c1dfadc…44859` (identique à celui de la session précédente) ; partie B `b1010_115a.bin` sha256 `791b371a…1c98e` |
| Firmware **C 1.10** | Contrôle : scripts IDA publics écrits pour cette version | `F-D750-V110W.exe`, dépôt [ternera/nikon-firmware-and-software](https://github.com/ternera/nikon-firmware-and-software) |
| nikon-firmware-tools | Tables XOR (`firmware decode/Firmware.cs`), carte mémoire et tables PTP du D750 1.10 (`IDA_files/D750/D750_Setup_RAM_1.10.idc`, `D750_PTP_1.10.idc`) | [simeonpilgrim/nikon-firmware-tools](https://github.com/simeonpilgrim/nikon-firmware-tools) |
| libgphoto2 | Noms des codes, « 2 params, data in / out » (`camlibs/ptp2/ptp.h`, l. 586 à 596) ; aucune implémentation de 0x90CC / 0x90CD | [gphoto/libgphoto2](https://github.com/gphoto/libgphoto2) |
| Sonde d’octobre 2026 | 32 blocs de 32 octets lus sur le D750 de Thomas | `sondes/d750/usb/2026-10.5/` |

Les documents Nikon portent la mention « Confidential » et « Do Not Copy » : ils sont cités par section, leurs tableaux ne sont pas recopiés ici. Aucune source publique trouvée n'utilise 0x90CC ou 0x90CD (recherche de code GitHub : libgphoto2, DslrDashboard, airnef, remoteyourcam ne font que nommer les codes). Pas de doc USB du D750 lui-même trouvée en ligne.

**Méthode** (reproductible avec [`outils/d750_firmware.py`](../outils/d750_firmware.py)) : extraction du `.bin` depuis le `.dmg` (UDIF zlib, HFS+), déchiffrement XOR à trois tables (entête de 0x20 octets en clair, index compté depuis le début du fichier), découpage en trois modules (`a1010_011100.bin`, `_wma_ver01.00.00`, `b1010_115a.bin`), **CRC16 des trois modules correct**, ce qui valide le déchiffrement ; désassemblage Thumb-2 avec Capstone 5.0.7 ; recherche des appels par décodage des BL / BLX. Le site de Nikon et la Wayback Machine sont bloqués par le réseau de cette session : la 1.15 vient du `.dmg` de Thomas.

---

## 3. Les commandes Picture Control du D750

Table PTP de la partie B (entrées de 0x1C octets : code, sens des données, puis pointeurs vers réception, contrôle, exécution, fin ; même structure que `ptp_entry_A` de `D750_PTP_1.10.idc`). Vérifié.

| Code | Entrée | Paramètres (exactement) | Données | Contrôle / exécution |
|---|---|---|---|---|
| 0x90CC GetPicCtrlData | `0x9120AFE8` | 2 : n°, DefaultFlag (0 ou 1) | boîtier → hôte, 32 ou 610 octets | `0x9026A516` / `0x9026AC38` → `0x9026AA10` |
| 0x90CD SetPicCtrlData | `0x9120B004` | 2 : n°, ModifiedFlag (0 ou 1) | hôte → boîtier | réception `0x900E2D32`, contrôle `0x9026A8AC` (dont validation du bloc `0x9026A6BC`), exécution `0x9026AFF2` → `0x9026AD9E` |
| 0x90CE DelCstPicCtrl | `0x9120B020` | 1 : n° (perso seulement) | aucune | `0x9026A516` / `0x9026B002` |
| 0x90CF GetPicCtrlCapability | `0x9120B03C` | 1 : n° | boîtier → hôte, 39 octets | `0x9026A516` / `0x9026B03C` |
| 0x940D | `0x9120B26C` | 3 : n°, DefaultFlag, mode (0 ou 1) | boîtier → hôte | mêmes fonctions que 0x90CC |
| 0x940E | `0x9120B288` | 4 : n°, ModifiedFlag, format (0 ou 1), mode (0 ou 1) | hôte → boîtier | mêmes fonctions que 0x90CD |
| 0x940F | `0x9120B2A4` | 1 : n°, mode forcé à 1 | aucune | `0x9026A5F6` puis comme 0x90CE |
| 0x9410 | `0x9120B2C0` | 1 : n°, mode forcé à 1 | 39 octets | `0x9026A5F6` puis comme 0x90CF |

- **0x940D à 0x9410** sont annoncés par le D750 (DeviceInfo de la sonde) mais nommés nulle part (absents de libgphoto2 et des docs Nikon trouvées). Ils réutilisent les gestionnaires de 0x90CC à 0x90CF avec un « mode » en plus. Mode 1 = second jeu d'index (50 à 69 au lieu de 0 à 19, table `0x9123E0E0 + 0x50`). **Hypothèse** : mode 1 = Picture Control du menu vidéo, comme le paramètre facultatif « ShootingMode » du Z 50 (§6.2.2.39) et les capacités `MoviePictureControlData` du module SDK du D750 ([liste publiée](https://github.com/number1nippon/SKD750Control/blob/main/docs/D750Capabilities.txt)). Le paramètre « format » de 0x940E choisit la conversion des valeurs (§4.3).
- **Numéros acceptés** (table `0x9123E0E0`, vérifié) : 1 à 7 (usine : Standard, Neutre, Saturé, Monochrome, Portrait, Paysage, Uniforme), 101 à 104 (Picture Control « optionnels », emplacements réservés), 201 à 209 (C-1 à C-9). Types (même table + 0x3C) : 0 usine couleur, 1 Monochrome, 2 optionnel, 3 perso.
- **Codes de réponse** lus dans les contrôles (vérifié) : 0x2001 OK ; 0x2006 nombre de paramètres faux ; 0x201D paramètre invalide (n° inconnu, p2 > 1, règles du ModifiedFlag, bloc refusé) ; 0x2019 boîtier occupé (`0x90131EA4`, hypothèse : prise de vue en cours) ; 0x200F accès refusé (`0x90131EEC`, hypothèse : réglage verrouillé, par exemple Picture Control utilisé par U1 ou U2, comme le dit la doc Z 50 pour l'effacement) ; 0x2002 erreur de lecture de la courbe stockée (`0x9026AC0E`) ; 0x2007 transfert incomplet.

---

## 4. Le bloc de données

### 4.1 Disposition (identique en lecture et en écriture)

Petit-boutiste pour les champs (aucun ne dépasse un octet sauf le nom et la courbe). Valeurs « en points » codées en **quarts de point signés**, −128 (0x80) = Auto. Vérifié par le constructeur de 0x90CC (`0x9026AA10` à `0x9026ABFC`), le lecteur de 0x90CD (`0x9026AD9E`, `0x9026ACD2` couleur, `0x9026AD64` monochrome, `0x9026AC42` fin commune), et recoupé avec les 32 blocs lus et les métadonnées des NEF de Thomas.

| Octet | Couleur | Monochrome | Plage acceptée en écriture (C 1.15, `0x9026A6BC`) |
|---|---|---|---|
| 0 | base : 1 Standard, 2 Neutre, 3 Saturé, 4 Monochrome, 5 Portrait, 6 Paysage, 7 Uniforme (101-104 optionnels) ; 0 = emplacement vide | idem | doit exister ; 0 a un sens particulier en retouche (§4.4) |
| 1 | MonochromeFlag = 0 | = 1 | doit correspondre à la base (`0x9026A72A`) |
| 2 | CustomFlag : 0 usine, 1 perso, 2 vide (lecture) | idem | 0 ou 1 ; **1 obligatoire** pour C-1 à C-9 (`0x9026A752`) |
| 3 à 22 | nom, 20 octets ASCII, terminé par un zéro (19 caractères utiles) | idem | caractères 0x20 à 0x7E (`0x9026A768`) |
| 23 | QuickAdjustFlag (0 / 1) | filtre : 0 aucun, 1 jaune, 2 orange, 3 rouge, 4 vert | couleur : 0 ou 1, **0 obligatoire en perso** (`0x9026A7DA`) ; filtre 0 à 4 |
| 24 | accentuation rapide, −2 à +2 (entier) | virage : 0 N&B, 1 sépia, 2 cyanotype, 3 rouge, 4 jaune, 5 vert, 6 bleu-vert, 7 bleu, 8 violet-bleu, 9 rouge-violet | −2 à +2 si le drapeau est mis ; virage 0 à 9 |
| 25 | saturation | force du virage | saturation −3 à +3 ou Auto ; force 1 à 7, lue seulement si virage ≠ 0 |
| 26 | teinte | réservé (0) | teinte −3 à +3, pas d'Auto |
| 27 | accentuation (netteté) | idem | 0 à 9 ou Auto |
| 28 | contraste | idem | −3 à +3 ou Auto |
| 29 | luminosité | idem | −1,5 à +1,5, pas d'Auto |
| 30 | clarté | idem | −5 à +5 ou Auto (lue seulement au format 1, §4.3) |
| 31 | **CustomCurveFlag** : 0 / 1 | idem | voir §4.2 |
| 32 à 609 | **CustomCurveData**, présent seulement si l'octet 31 vaut 1 | idem | voir §4.2 |

Toutes les plages sont exprimées en points ; dans le bloc, multiplier par 4 (accentuation 5 → 0x14, contraste +3 → 0x0C, luminosité +1,5 → 0x06). Quand l'accentuation rapide est active, le boîtier ignore les octets 25 à 30 et prend les valeurs de son préréglage (`0x9026AC42`, branche `r6 ≠ 0`), comme le décrit la doc D5000 (§5.2.31).

Différences avec le D5000 (doc §6.4) : le D750 ajoute la **clarté** en octet 30 (d'où 32 octets au lieu de 31, et 610 au lieu de 609) et passe en quarts de point. Les octets 0 à 29 ont la même place.

Recoupement avec les NEF (relevé de perspectives-d200-xt4-d750.md §3.2) : « TRI-X » (C-2) = filtre orange, accentuation 5, contraste +3, luminosité 0, clarté +1 ; « HP5+ » (C-6) = jaune, 4, +1, 0, −1 ; « Kodachrome » (C-1) = accentuation 4, contraste +1, clarté +1 (plus saturation +2 et teinte +1). Les trois concordent avec les NEF. Vérifié (`python3 outils/picture_control.py ptp sondes/d750/usb/2026-10.5/pictctrl_202_0.bin`).

### 4.2 La courbe perso

Lecture (`0x9026AB8E` à `0x9026AC08`, vérifié) : le boîtier ne met l'octet 31 à 1 que pour un Picture Control **perso** dont le contraste interne vaut « géré par la courbe » (valeur interne 0x01, la même convention que dans un NCP) ; il lit alors la courbe stockée (`0x90129EE8`), inverse l'ordre des octets des 257 valeurs (boucle `rev16` à `0x9026ABE8`) et ajoute les 578 octets. Les 32 blocs lus sur le D750 de Thomas ont tous l'octet 31 à 0 : aucun de ses Picture Control n'a de courbe, ce que disaient déjà les NEF (champ `ContrastCurve` vide).

Écriture (`0x9026AEBA` à `0x9026AEE8` pour un nouvel enregistrement, `0x9026AF74` à `0x9026AFB4` pour une retouche, vérifié) :
- octet 31 = 1 : le contraste et la luminosité internes passent à « géré par la courbe » (`0x9026AEC0`, `0x9026AEC4`), quels que soient les octets 28 et 29 ; les 578 octets sont copiés, les 257 valeurs remises dans l'ordre interne (`rev16`), puis enregistrés par `0x90129D96` (mémoire de réglages : identifiant 0xF314 et numéro d'emplacement pour C-1 à C-9 du menu photo) ;
- octet 31 = 0 lors d'un nouvel enregistrement : la courbe stockée est effacée (578 zéros, `0x9026AE9C`) ;
- octet 31 = 0 lors d'une retouche : la courbe en place n'est pas touchée ;
- sur un Picture Control d'usine, la courbe n'est jamais lue ni stockée (seul le chemin des types 3 la traite), ce que dit aussi la doc D5000.

Format des 578 octets (doc D5000 §9.1, Z 50 §9.8.17.1 ; vérifié pour la taille et l'ordre des octets) :

| Octets | Contenu |
|---|---|
| 0 à 63 | entête réservé à l'hôte. Celui des logiciels Nikon : `0x49 0x30` (« I0 »), point noir d'entrée, maximum d'entrée, minimum et maximum de sortie, gamma (partie entière, centièmes), nombre de points (2 à 20), puis jusqu'à 20 couples (x, y) sur 8 bits, le reste à zéro. Nikon précise que le boîtier n'interprète pas ces octets mais que deux d'entre eux lui servent à savoir si l'entête est présent |
| 64 à 577 | 257 valeurs sur 16 bits, **gros-boutistes**, 15 bits utiles (0 à 32767) |

**Preuve de l'ordre des octets** : le chargeur de `.NCP` depuis la carte (`0x90129FE0` : contrôle de la signature « NCP » à `0x9012C870`, lecture des enregistrements type et longueur en gros-boutiste avec `rev`, exigence d'une longueur 0x242 pour le type 2 à `0x9012A0AA`) lit les 578 octets, applique **la même** inversion des 257 valeurs (`0x9012C836`) puis les enregistre avec la même fonction `0x90129D96` (appel à `0x9012A090`). Le PTP applique cette inversion dans les deux sens. Donc le bloc PTP porte la courbe dans l'ordre du fichier NCP, gros-boutiste, alors que la doc Nikon annonce par défaut des champs petit-boutistes. Conséquence pratique : les 578 octets d'un NCP fait par Picture Control Utility (ou par `picture_control.ecrire_ncp`) se recopient tels quels dans le bloc. Vérifié (code) ; contrôle sur le boîtier : §5.

Ce qui n'a pas été trouvé : le contrôle des « deux octets » de l'entête annoncé par Nikon n'apparaît dans aucun des chemins lus (PTP, chargeur NCP, enregistrement). Il est sans doute ailleurs (traitement d'image, ou affichage de la courbe dans le menu). Garder l'entête Nikon, comme le fait `picture_control.py`, évite la question. Hypothèse.

### 4.3 Conversion des valeurs (vérifié)

- Interne = valeur + 0x80, comme dans un NCP ; 0x00 = Auto ; 0x01 = géré par la courbe ; 0xFF = sans objet.
- Lecture (`0x9026B1F6`) : 0x00 → −128 (Auto), 0x01 et 0xFF → 0, sinon valeur − 0x80. Un contraste « courbe » se lit donc 0.
- Écriture par 0x90CD (`0x9026A69C`) : −128 → Auto, sinon valeur + 0x80 (quarts de point).
- Écriture par 0x940E au format 0 (`0x9026A6AA`) : valeur × 4 + 0x80, c'est-à-dire des points entiers, et l'octet 30 (clarté) n'est pas lu (`0x9026A88C`). **Hypothèse** : compatibilité avec l'ancien bloc de 31 octets du D5000.

### 4.4 Règles d'écriture de 0x90CD (vérifié, `0x9026A938` à `0x9026A99C` et `0x9026AD9E`)

- **Usine (1 à 7)** : ModifiedFlag doit valoir 1 (sinon 0x201D). Seul le réglage courant change ; le boîtier compare ensuite courant et défaut (10 octets, `0x9026AF5E`) et pose un drapeau « modifié » (hypothèse : l'astérisque du menu).
- **Perso (201 à 209), ModifiedFlag 0** : accepté que l'emplacement soit vide **ou déjà occupé** (aucun contrôle d'existence) : un enregistrement neuf **remplace** l'ancien. Le boîtier écrit base, drapeaux, nom, réglages, courbe, puis recopie le courant dans le défaut (`0x9026AEB4`). Conforme à la doc MAID (« initial registration » met à jour courant et défaut).
- **Perso, ModifiedFlag 1** : l'emplacement doit exister (sinon 0x201D). La base envoyée doit être celle de l'enregistrement (doc Z 50 : sinon accès refusé).
- **Base 0 avec ModifiedFlag 1** : appel direct de `0x90129D40` sur le nom (`0x9026AE26`). **Hypothèse** : simple renommage.
- La taille de la phase de données n'est contrôlée nulle part dans ces fonctions : le boîtier lit 32 octets, puis 578 de plus si l'octet 31 vaut 1. Il faut donc envoyer exactement 32 ou 610 octets cohérents avec l'octet 31.

### 4.5 GetPicCtrlCapability (0x90CF)

39 octets (`0x9026B03C`, vérifié pour la taille et l'ordre de remplissage) : un drapeau de validité (0 et tout à zéro si la base est Monochrome, `0x9026B060`), 7 octets de capacités (sélectionnable 0x80, Auto 0x01), la position par défaut de l'accentuation rapide, puis 5 groupes de 6 valeurs (une par cran de l'accentuation rapide, −2 à +2). Nom exact de chaque octet : hypothèse, par analogie avec la doc D5000 (§5.2.33) et Z 50 (§9.9). Inutile pour la courbe, utile pour connaître les plages par base.

---

## 5. Lecture seule de plus, à lancer par Thomas

### 5.1 Le script mis à jour

`swift outils/d750_ptp.swift` (même usage qu'avant ; non compilé dans cette session, faute de Swift sous Linux). Il n'envoie que des lectures :

| Commande | Pourquoi | Fichiers |
|---|---|---|
| 0x1001 GetDeviceInfo | comme avant | `deviceinfo.bin` |
| 0x90CA GetVendorPropCodes | les réglages Nikon (0xD200 Picture Control actif, 0xD201, D-Lighting actif, etc.) ne figurent pas dans DeviceInfo, d'où leur absence dans la sonde d’octobre | `vendorprops.bin` |
| 0x1014 GetDevicePropDesc | les réglages de la liste, standard et Nikon | `prop_xxxx.bin` |
| 0x90CC (n, 0 et 1) | comme avant, avec le décodage (longueur, perso ou vide, nom, courbe) | `pictctrl_n_p.bin` |
| 0x90CF (n) | capacités par base | `picctrlcap_n.bin` |
| 0x940D (n, 0, mode 0 et 1) | vérifier que mode 0 redonne 0x90CC et voir ce que donne mode 1 (vidéo ?) | `pictctrl940d_n_mode.bin` |

Décodage d'un fichier : `python3 outils/picture_control.py ptp <fichier.bin>`.

Attendu (prédiction tirée du firmware, à confirmer) : blocs de 32 octets identiques à la sonde d’octobre ; 39 octets pour 0x90CF, à zéro pour les bases Monochrome ; 0x940D en mode 0 identique à 0x90CC.

### 5.2 Le test décisif, sans aucune écriture USB (au choix de Thomas)

But : vérifier sur le boîtier le format de la courbe avant d'écrire quoi que ce soit par câble.

1. Fabriquer un `.NCP` Monochrome avec une courbe nette (par exemple avec `picture_control.ecrire_ncp`, ou Picture Control Utility 2), le copier dans `NIKON/CUSTOMPC/` de la carte du logement 1.
2. Sur le boîtier : Gérer le Picture Control, Charger/enregistrer, Copier vers l'appareil, emplacement **C-7** (vide). C'est la fonction normale du menu, la même que pour un profil acheté ; elle passe par le chargeur NCP et la fonction d'enregistrement décrits au §4.2.
3. Relancer `swift outils/d750_ptp.swift`.
4. Résultat attendu : `pictctrl_207_0.bin` fait **610 octets**, son octet 31 vaut 1, et ses octets 32 à 609 sont égaux aux 578 octets de l'enregistrement de type 2 du NCP :

```
python3 -c "
import sys; sys.path.insert(0, 'outils'); import picture_control as pc
b = open(sys.argv[1], 'rb').read(); n = pc.lire_ncp(open(sys.argv[2], 'rb').read())
print(len(b), b[31], pc.lire_bloc_ptp(b)['lut'] == n['courbe']['lut'])" pictctrl_207_0.bin MONFICHIER.NCP
```

Si c'est le cas, le format est confirmé sur le boîtier lui-même (et le NCP écrit par `picture_control.py` est validé au passage). Le Picture Control C-7 s'efface ensuite depuis le même menu.

---

## 6. Écrire un Picture Control : l'outil `d750_ecrire.swift`

Outil écrit en octobre 2026, avant tout essai sur le boîtier ; il y a été lancé depuis (§9). Vérifié sous Linux contre un faux D750 en mémoire (mêmes commandes, mêmes codes de réponse) : simulation sans écriture, refus d'un emplacement occupé, écriture puis relecture identique, effacement, activation.

**Ce que cela touche** : un emplacement de Picture Control perso, dans la mémoire de réglages, par la commande prévue par Nikon (celle de Camera Control Pro). Le firmware ne change pas d'un octet : c'est un réglage au sens du projet. Pire cas réaliste : un Picture Control raté dans un emplacement, à effacer depuis le menu ou par l'outil.

**Mode d'emploi** (à faire après le §5.2) :

1. **Préconditions** : boîtier en P, S, A ou M, pas en prise de vue, pas en U1 / U2 (évite 0x2019 et 0x200F), câble USB branché, Photos et Transfert d'images fermés.
2. **Recette** : un petit fichier JSON, par exemple [`recettes/d750/exemple-tri-x-courbe.json`](../recettes/d750/exemple-tri-x-courbe.json) (format seulement, pas une recette réglée) :
   ```
   {"nom": "TRI-X COURBE", "base": "Monochrome",
    "reglages": {"filtre": "aucun", "accentuation": 5, "clarte": 1},
    "courbe": {"points": [[0, 0], [64, 52], [192, 200], [255, 255]]}}
   ```
   Réglages en points (pas de 0,25) ; courbe au choix par `points` (x, y de 0 à 255, interpolation monotone), `lut` (257 valeurs de 0 à 32767) ou `ncp` (un `.NCP` fait par Picture Control Utility, dont la courbe est reprise à l'octet près). Sans `courbe`, pas de courbe perso.
3. **Bloc** : `python3 outils/picture_control.py bloc recettes/d750/exemple-tri-x-courbe.json /tmp/c7.bin` (affiche le contenu décodé ; refuse toute valeur hors des plages du §4.1).
4. **Simulation** (par défaut, n'écrit rien) : `swift outils/d750_ecrire.swift ecrire /tmp/c7.bin C-7`. L'outil vérifie que c'est un D750, lit C-7 (courant et défaut, sauvés), contrôle la forme du bloc et dit ce qu'il enverrait.
5. **Écriture** : la même commande avec `--ecrire`. 0x90CD (207, 0) avec le bloc, puis relecture de C-7 (courant et défaut) comparée à l'envoi, octet par octet, en ignorant les octets 28 et 29 si la courbe est présente (contraste et luminosité relus à 0). `--activer` choisit ensuite ce Picture Control (SetDevicePropValue 0xD200 = 207).
6. **Contrôle visuel** : une photo, et comparer le JPEG au NEF.
7. **Retour en arrière** : `swift outils/d750_ecrire.swift effacer C-7 --ecrire` (0x90CE), ou le menu du boîtier ; un emplacement remplacé se restaure avec son `avant_20n_0.bin` : `swift outils/d750_ecrire.swift ecrire <dossier>/avant_207_0.bin C-7 --ecrire --remplacer`.

**Garde-fous de l'outil** : C-1 à C-9 seulement (jamais un Picture Control d'usine) ; emplacement occupé refusé sans `--remplacer` (ModifiedFlag 0 l'écraserait sans prévenir, §4.4) ; refus si le boîtier n'est pas un D750 ou n'annonce pas les commandes ; bloc refusé avant tout envoi si sa forme est fausse (longueur, base, drapeaux, nom, accentuation rapide, cohérence de l'octet 31, entête « I0 » de la courbe). Chaque lancement laisse un dossier `sondes/d750/usb/ecriture-<date>/` : `journal.txt`, contenu avant, bloc, contenu après.

**Point non vérifié** : la phase de données sortante est passée à ImageCaptureCore sans entête PTP (usage des projets publics, par exemple [Obscura](https://github.com/jordanlucero/Obscura)). Si macOS la cadrait autrement, l'octet 0 reçu ne serait pas une base valide et le boîtier refuserait le bloc (0x201D, §4.1) sans rien écrire ; la relecture le montrerait.

Pour la calibration automatique envisagée dans le rapport précédent : chaque essai est une réécriture de C-7 par 0x90CD (207, 0), suivie d'une relecture, sans toucher C-1 à C-6.

---

## 7. Ce qui reste incertain

| Point | Statut | Comment trancher |
|---|---|---|
| Format confirmé sur le boîtier (610 octets, courbe gros-boutiste) | code lu, pas observé | §5.2 |
| Contrôle des deux octets d'entête de la courbe | non trouvé dans les chemins lus | garder l'entête Nikon (`picture_control.py` le fait) |
| Mode 1 de 0x940D à 0x9410 = vidéo | hypothèse | §5.1 (comparer avec le menu vidéo du boîtier) |
| Sens exact des conditions 0x2019 et 0x200F | hypothèse | sans importance si les préconditions du §6 sont respectées |
| Taille maximale acceptée par la réception USB | non vue (tampon commun `0x901AA072`) | 610 octets sont sous les 614 du Z 50 ; sans risque attendu |
| 1.10 contre 1.15 | même table, mêmes contrôles : gestionnaires décalés de −0x48C en 1.10 (`0x9026A08A` pour le contrôle, `0x9026A7AC` pour 0x90CC), 3 216 octets identiques sur 3 360 dans la zone, écarts sur les appels et les littéraux, non examinés un à un | sans objet pour Thomas (1.15) |

---

## 8. Outils et références

Installation sur le Mac ou dans une session cloud, une fois (et pour mettre à jour) : `bash outils/references.sh`. Il range les docs Nikon du SDK et leur version texte dans `references/` (hors git, index dans `references/README.md`), clone les dépôts tiers et installe Capstone dans `~/Library/Caches/retro-ingenierie-boitiers/`, et extrait le firmware D750 posé dans `~/Library/Caches/retro-ingenierie-boitiers/firmware/`.

- [`outils/d750_ptp.swift`](../outils/d750_ptp.swift) : la sonde, en lecture seule (§5.1).
- [`outils/d750_ecrire.swift`](../outils/d750_ecrire.swift) : écrire ou effacer un Picture Control perso (§6), simulation par défaut.
- [`outils/picture_control.py`](../outils/picture_control.py) : `ptp` (décoder un bloc lu), `bloc` (fabriquer un bloc depuis une recette), NCP ; auto-test qui reconstruit à l'octet près le bloc « TRI-X » lu sur le D750 et vérifie que la courbe du bloc est celle du NCP. Ne parle à aucun boîtier.
- [`outils/d750_firmware.py`](../outils/d750_firmware.py) : extraction du `.dmg`, déchiffrement avec contrôle des CRC, table PTP, désassemblage, recherche d'appels. Exemple : `~/Library/Caches/retro-ingenierie-boitiers/venv/bin/python3 outils/d750_firmware.py dis ~/Library/Caches/retro-ingenierie-boitiers/firmware/d750-115/b1010_115a.bin 9026aa10 150`.

---

## 9. Vérifié sur le boîtier : séance d’octobre 2026

Première écriture réelle, sur le D750 de Thomas (C 1.15), par [`outils/d750_seance.swift`](../outils/d750_seance.swift) et le plan de [`outils/d750_seance.py`](../outils/d750_seance.py) : 47 Picture Control écrits l'un après l'autre dans C-9 (SetPicCtrlData 0x90CD (209, 0)), chacun activé (0xD200 = 209), photographié (InitiateCaptureRecInMedia 0x9207 (0xFFFFFFFF, 0), sur la carte) et rapatrié (NEF + JPEG, GetObject 0x1009).

| Point du §7 | Résultat |
|---|---|
| Format confirmé sur le boîtier | **Vérifié** : 35 blocs de 32 octets et 12 de 610 octets (courbe) acceptés (0x2001), chacun relu identique à l'envoi (octets 28 et 29 exceptés quand la courbe est présente, comme prévu) |
| Phase de données sortante sans entête PTP (ImageCaptureCore) | **Vérifié** : c'est le bon cadrage |
| ModifiedFlag 0 sur un emplacement occupé | **Vérifié** : remplace l'ancien Picture Control sans erreur |
| Effet de la courbe | **Vérifié** sur les NEF ([d750-analyse-seances.md](d750-analyse-seances.md) §2.4) : une courbe identité redonne exactement la base ; la courbe perso s'applique après la base, sur la luma Y' du JPEG, Cb et Cr inchangés. Le constat du jour (« plus chaude et plus contrastée ») venait d'un changement de lumière entre les deux vues du lot 1 |
| Remise en état | **Vérifié** : C-9 effacé (0x90CE), Picture Control actif remis à 203 (Portra), C-1 à C-6 jamais touchés |

À savoir pour la prochaine séance : le JPEG et le NEF d'une vue n'arrivent pas en même temps (le NEF suit de quelques secondes) ; la première version de l'outil a donc classé chaque vue avec un temps de retard. Corrigé dans l'outil (attente des deux fichiers, aucun fichier repris deux fois) ; pour cette séance, `d750_seance.py ranger` a reclassé les fichiers d'après le nom du Picture Control noté dans chacun (47 vues complètes sur 47). L'ISO auto était resté actif (1 250 à 2 000) : chaque JPEG se compare à son propre NEF.

Lot 2, même jour : 24 vues sur le un visage (`d750_seance.py plan <dossier> --lot portrait` : bases, saturation et teinte sur Standard, Neutre, Portrait, courbe identité sur Portrait, trois v0 couleur, et son « Portra 400 » de C-3 recopié tel quel sous le nom PORTRA ACTUEL), ISO 200 fixe, 5 600 K. 24 vues complètes sur 24 avec l'outil corrigé, même release GitHub.

Lots 3 et 4, même jour, plan complet (47 vues chacun) sur des scènes colorées (pédalier de guitare, dos de livres), 1/10 s, ISO 200, 5 600 K, puis un complément de 14 vues (`--lot complement` : filtres Monochrome, crans ±1, courbes sur Portrait). 155 vues en tout, toutes complètes. Le retard d'une vue réapparaît parfois en fin de séance : la dernière vue reste alors sur la carte, `--rapatrier 4` la récupère (journal à part, `journal-rapatriement.txt`), et `ranger` remet tout en ordre.

## 10. Préréglages manuels de balance des blancs d-1 à d-6 (sonde d’octobre 2026)

Lecture seule de 0xD010 à 0xD03F (`sondes/d750/usb/2026-10-sonde-balance/`) :

- 0xD01F : préréglage choisi (UINT8, 1 à 6), modifiable ;
- 0xD021 à 0xD024, puis 0xD038 et 0xD039 : commentaires de d-1 à d-6 (chaîne de 36 caractères, remplie d'espaces), **modifiables** ;
- 0xD026 à 0xD029, puis 0xD03E et 0xD03F : valeurs des préréglages (UINT32, deux gains 16 bits), **lecture seule** ; les six valaient 0x01F30157 (jamais mesurés) ;
- 0x90C9 SetPreWBData est annoncée, mais son format n'est pas documenté : pas essayée.

Écrit par USB (0x1016) et relu : d-1 « KODACHROME 6250K », d-2 « TRI-X 10000K », d-3 « PORTRA 400 5600K » (`ecriture-2026-10.20/`, avec le script). La valeur se charge par le menu : photo prise à la bonne température, puis Pré-réglage manuel › Choisir une photo.
