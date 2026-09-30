# D200 par USB (PTP) : ce qu'on peut régler sans toucher au firmware

Recherche d’octobre 2026, sur le D200 de Thomas (firmware A et B 2.01), branché au Mac Studio en USB, mode PTP. **Lecture seule** : aucune commande d'écriture n'a été envoyée (ni SetDevicePropValue `0x1016`, ni CurveUpload `0x90C6`, ni SetPreWBData `0x90C9`). Aucun firmware modifié ni flashé. Le firmware 2.01 a été retéléchargé chez Nikon (accord de Thomas) et ouvert en lecture seule dans Ghidra, hors du dépôt.

Légende : **vérifié** = lu sur le boîtier (fichier de sonde cité), dans le code désassemblé (adresse donnée) ou dans le manuel ; **hypothèse** = déduction, à confirmer avant d'agir.

Adresses : processeur, partie B chargée en `0x50000` (offset fichier = adresse − `0x50000`).

---

## 1. En bref

| Question | Réponse | Statut |
|---|---|---|
| Ce qui est réglable par USB | 151 réglages Nikon et 17 standard annoncés, presque tous en écriture : Optimiser l'image et ses 5 réglages perso, balance des blancs (mode, température, réglage fin, noms d-0 à d-4), banques A à D (choix et noms), réglages perso a1 à f6, flash. Plus la **courbe perso** (`0x90C6`) et les **valeurs** des préréglages de balance (`0x90C9`) | vérifié (sonde, code) |
| Courbe perso : par banque ou unique ? | **Unique** : un seul tampon de `0x844` octets, une seule entrée dans la table de sauvegarde des réglages, et `0x90C5` / `0x90C6` refusent tout paramètre. Ce qui est par banque, c'est le choix « Correction des tons : Personnalisée » | vérifié (code, sonde) |
| Format de la courbe | **0x844 octets = 68 d'entête + 2 048 valeurs sur 8 bits**. Le boîtier ne l'utilise que si les octets 0 et 1 de l'entête sont non nuls ; sinon il prend sa courbe d'usine | vérifié (code) |
| Courbe actuelle du boîtier | **Aucune** : entête à zéro, table remplie de résidus jamais écrits (motif `0x5A`, puis `0x00`, puis `0xFF`). « Personnalisée » vaut donc aujourd'hui la courbe d'usine | vérifié (sonde, code) |
| Coût de l'outil d'envoi `0x90C6` | Petit : la sonde actuelle plus une commande sortante sans paramètre, 2 116 octets, aucune validation côté boîtier (§6) | vérifié (code) ; outil : à écrire |
| Une plage plus large que les menus ? | **Aucune** dans les réglages annoncés, et **aucun réglage caché** parmi les 856 codes non annoncés balayés. Deux vraies marges : la courbe perso (forme libre) et `0x90C9` (gains de balance libres jusqu'à ×8) | vérifié (sonde, code) ; effet de `0x90C9` : à voir |
| N&B | Toujours sans réglage : le rendu N&B prend ses propres tables et **ignore la courbe perso** (§5.4) | vérifié (code) |

---

## 2. Méthode et fichiers

| Élément | Où |
|---|---|
| Sonde, lecture seule (GetDeviceInfo, GetVendorPropCodes, GetDevicePropDesc sur chaque réglage, CurveDownload) ; filtre sur le nom « D200 » et refus de tout code d'écriture | [`d200/outils/d200_ptp.swift`](../outils/d200_ptp.swift) (`--balayage` : codes non annoncés aussi) |
| Décodage (relevé en TSV, courbe) | [`d200/outils/d200_ptp.py`](../outils/d200_ptp.py) `<dossier> [ptp.h]` |
| Sonde 1 | [`d200/sondes/usb/2026-10.21/`](../sondes/usb/2026-10.21/resume.txt) : `deviceinfo.bin`, `vendorprops.bin`, 168 `prop_xxxx.bin`, `courbe_90c5_sans.bin`, [`releve.tsv`](../sondes/usb/2026-10.21/releve.tsv) |
| Sonde 2 (même chose + balayage de `0x5000`-`0x50FF` et `0xD000`-`0xD2FF`) | [`d200/sondes/usb/2026-10.22/`](../sondes/usb/2026-10.22/resume.txt), `journal-balayage.txt` ; courbe identique octet pour octet, réglages identiques (sauf l'heure et la cellule) |
| Firmware 2.01 | `~/Library/Caches/retro-ingenierie-boitiers/firmware/d200-201/` (hors du dépôt) ; sha256 identiques à perspectives §1.1 |
| Pseudo-C des fonctions lues | `d200/desassemblage/`, script [`D200Fonctions.java`](../desassemblage/ghidra_scripts/D200Fonctions.java) (import sans analyse, base `0x50000`, processeur `fr60:BE:16:default`) |
| Noms des codes | libgphoto2 `camlibs/ptp2/ptp.h` et `config.c` (version GitHub d’octobre 2026) ; manuel du D200 (p. 39, 45-48, 61, 107, 125) |

---

## 3. Ce que le boîtier annonce

- **Identité** : « Nikon Corporation », D200, « V2.01 », extension Nikon `0xA`. Vérifié.
- **30 commandes** : les 19 standard de la table (dont InitiateCapture `0x100E`, GetDevicePropDesc `0x1014`, SetDevicePropValue `0x1016`), et les 11 Nikon `0x90C0` à `0x90CA` (Capture en SDRAM, AfDrive, SetControlMode, DelImageSDRAM, GetLargeThumb, CurveDownload, CurveUpload, GetEvent `0x90C7`, DeviceReady, SetPreWBData, GetVendorPropCodes). **Aucune commande Picture Control** (`0x90CC` et suivantes) : normal, le D200 est d'avant les Picture Control. Vérifié.
- **11 événements**, **17 réglages standard**, **151 réglages Nikon** (`0x90CA`). Vérifié.
- **Balayage** : GetDevicePropDesc sur les 856 codes non annoncés de `0x5000`-`0x50FF` et `0xD000`-`0xD2FF` : tous refusés (`0x2006`). Le boîtier n'a pas de réglage caché accessible par ce chemin. Vérifié.

---

## 4. Les réglages qui comptent pour le rendu

Ordre des valeurs : le firmware ne nomme rien, les tables de libgphoto2 sont celles d'autres boîtiers (D70 : 8 choix pour Optimiser, 7 pour la correction des tons, alors que le D200 en a 7 et 5). L'ordre retenu est celui des menus du manuel, **calé par la valeur d'usine** que renvoie chaque descripteur (Auto ou Normal par défaut, d'après le manuel). Statut de la correspondance : hypothèse forte, à confirmer d'un coup d'œil sur le menu.

| Code | Réglage | Plage annoncée | Valeur actuelle (banque A) | Menu (manuel) |
|---|---|---|---|---|
| `0xD140` | Optimiser l'image | 0 à 6 | **5 = Personnalisé** | Normal, Moins net, Saturé, Très saturé, Portrait, Personnalisé, N&B (p. 45) |
| `0xD02A` | Netteté | 0 à 6 | 4 = Moyenne + | Auto, Normale, Faible, Moyenne −, Moyenne +, Élevée, Aucune (p. 46) |
| `0xD02B` | Correction des tons | 0 à 4 | 3 = Plus contrasté | Auto, Normale, Moins contrasté, Plus contrasté, Personnalisée (p. 47) |
| `0xD02C` | Mode couleur | 0 à 2 | 0 = I | I, II (Adobe RGB), III (p. 47) ; II refusé tant que l'espace couleur est en sRGB (réponse `0x200F`, octobre 2026) : régler l'espace couleur d'abord |
| `0xD142` | Saturation | 0 à 3 | 0 = Auto | Auto, Normale (usine = 1), Modérée, Accentuée (p. 48) |
| `0xD02D` | Teinte | −9 à +9, pas de 3 | 0 | ±9° par pas de 3° (p. 48) |
| `0xD032` | Espace couleur | 0 à 1 | 0 = sRGB | sRGB, Adobe RGB |

Toutes ces plages sont exactement celles des menus. Vérifié (sonde, manuel).

### 4.1 Balance des blancs

| Code | Réglage | Plage | Actuel |
|---|---|---|---|
| `0x5005` | mode | Auto, Ensoleillé, Fluo, Incandescent, Flash, Nuageux (`0x8010`), Ombre (`0x8011`), Température (`0x8012`), Pré-réglage (`0x8013`) | Auto |
| `0xD017` à `0xD01D` | réglage fin par mode | −3 à +3 | 0 partout |
| `0xD01E` | température, en index | 0 à 30 (les 31 températures du menu) | 20 |
| `0xD01F` | pré-réglage choisi | 0 à 4 = d-0 à d-4 | d-0 |
| `0xD020` à `0xD024` | **commentaires** de d-0 à d-4 | chaîne de 36 caractères, en écriture | d-1 = « STUDIO_100 », les autres vides |
| `0xD025` à `0xD029` | **valeurs** de d-0 à d-4 | UINT32 en **lecture seule** : deux gains 16 bits, 256 = ×1 (usine `0x01000100`) | d-0 1,69 / 1,52 ; d-1 1,77 / 1,57 ; d-2 1,61 / 2,13 ; d-3 1,17 / 1,42 ; d-4 1,80 / 1,40 |

Vérifié (sonde). Les cinq préréglages ont été mesurés un jour (aucun n'est à la valeur d'usine). Quel gain est le rouge et lequel le bleu : hypothèse (rouge en haut, comme on l'attend d'un d-2 mesuré en lumière chaude, bleu plus fort). Manuel p. 39 : les préréglages sont **communs aux quatre banques**.

Les valeurs ne s'écrivent pas par `0x1016`, mais par **SetPreWBData `0x90C9`** (§7).

### 4.2 Banques

| Code | Réglage | Actuel |
|---|---|---|
| `0xD010` | banque du menu Prise de vue (0 à 3 = A à D) | A |
| `0xD011` à `0xD014` | noms A à D (20 caractères) | A = « /.. », B = « STUDIO1 » (effacé en octobre, §4.2 ter), C et D vides |
| `0xD040` | banque des réglages perso (0 à 3) | A |
| `0xD041` à `0xD044` | noms | A = « Standard », B = « Nuit », C et D vides |
| `0xD015`, `0xD045` | remise à zéro de la banque courante | (commande, pas un état) |

Vérifié (sonde). Les réglages d'Optimiser l'image du §4 sont ceux de la banque de prise de vue **active** : la lecture d'une autre banque demanderait de la changer (écriture de `0xD010`, ou geste au menu). Manuel p. 125 : chaque banque garde tous les réglages du menu Prise de vue.

### 4.2 bis Banque de réglages perso B « Nuit » (lue en octobre 2026)

Lue par [`d200/outils/d200_banque.swift`](../outils/d200_banque.swift) `reglages-perso B` : passage sur B, lecture des 168 réglages, retour sur A vérifié ([`d200/sondes/usb/banque-reglages-perso-B-2026-10.23/`](../sondes/usb/banque-reglages-perso-B-2026-10.23/journal.txt)). Ordre des valeurs : celui des menus du manuel (p. 148-172), hypothèse forte.

| Réglage perso | « Standard » (A) | « Nuit » (B) |
|---|---|---|
| a1 Priorité en AF-C | Déclenchement | Déclenchement + mise au point |
| a8 Sélection du point AF | En boucle | Sans boucle |
| b1 ISO auto | Oui, plafond 400 | Non (plafond d'usine 1 600) |
| b5 Correction d'exposition facile | Oui (molette seule) | Non |
| c4 Retardateur | 10 s | 2 s |
| d1 Signal sonore | Coupé | Aigu |
| d5 Temporisation miroir levé | Non | **Oui** |
| f4 Bouton FUNC | Mesure matricielle | Flash coupé |

Tout le reste (dont Optimiser l'image, qui dépend des banques Prise de vue) est identique. Lecture : B est une banque de pose longue sur pied (retardateur court, miroir levé avant l'ouverture, ISO fixe, pas de flash).

**Effet de bord constaté** : l'aller-retour a remis la correction d'exposition de +5,0 IL à 0. Avec b5 sur Oui dans « Standard », la correction se règle à la molette seule ; c'est sans doute ainsi que le +5 était arrivé (hypothèse). L'outil compare désormais tous les réglages avant et après l'aller-retour et signale ce qui a changé.

### 4.2 ter Banques Prise de vue B, C et D (lues en octobre 2026, nom de B effacé)

Lue par `d200_banque.swift prise-de-vue B`, retour sur A vérifié, aucun réglage changé par l'aller-retour ([`journal`](../sondes/usb/banque-prise-de-vue-B-2026-10.24/journal.txt)). **Le nom seul est réglé** : tout le reste est à la valeur d'usine.

| Réglage | « /.. » (A) | « STUDIO1 » (B) |
|---|---|---|
| Qualité d'image | 6 (NEF + JPEG fine, hypothèse) | 1 = usine (JPEG Normal, hypothèse) |
| Optimiser l'image | Personnalisé | Normal |
| Netteté | Moyenne + | Auto |
| Correction des tons | Plus contrasté | Auto |
| Saturation | Auto | Normale |
| Compression JPEG | Qualité optimale | Priorité à la taille (usine) |
| Réduction du bruit en pose longue | Oui | Non |
| Vues en rafale avant saturation | 10 (suit la qualité) | 25 |

Balance des blancs, ISO, espace couleur : identiques dans les deux. Le préréglage de blanc d-1 « STUDIO_100 » (§4.1) est commun aux banques : il n'appartient pas à B.

C et D, lues de même ([C](../sondes/usb/banque-prise-de-vue-C-2026-10.25/journal.txt), [D](../sondes/usb/banque-prise-de-vue-D-2026-10.26/journal.txt)) : **identiques à B**, réglages d'usine, sans nom. B ne servait donc à rien : à la demande de Thomas, son nom a été effacé (`d200_banque.swift nommer prise-de-vue B ""`, relu, [journal](../sondes/usb/banque-nom-prise-de-vue-B-2026-10.27/journal.txt)). Les trois banques B, C, D sont maintenant vierges ; A reste la banque de tous les jours.

### 4.3 À signaler

- **Correction d'exposition `0x5010` = +5,0 IL** (5000, plage ±5 IL par tiers), en mode A (`0x500E` = 3). Lu tel quel ; à vérifier sur l'écran de contrôle, ce serait un réglage oublié. Vérifié (lecture) ; cause : inconnue.
- Les réglages perso a1 à f6 (AF, mesure, réglage fin de l'exposition b7 de −6 à +6 sixièmes, bracketing, flash commandeur) et qualité, ISO, ISO auto, réduction du bruit : tous dans le relevé, plages égales aux menus.

---

## 5. La courbe perso

### 5.1 Les deux commandes (vérifié, `ptp-courbe.c`)

| Code | Gestionnaire | Comportement |
|---|---|---|
| `0x90C5` CurveDownload | `0x8D164` | exige un conteneur de commande de 12 octets, donc **aucun paramètre** (sinon `0x2006`, vu sur la sonde avec un paramètre) ; renvoie les `0x844` octets du tampon RAM `0x97BD0B14`, **tels quels**, sans contrôle ni courbe de remplacement (le D40, lui, renvoie une courbe d'usine si son tampon est vide) |
| `0x90C6` CurveUpload | `0x8D1C0` | aucun paramètre ; si le boîtier est occupé (`0x3000000C` bit 0 ou `0x9799156C` bit 4), il vide la phase de données et répond `0x2019` ; sinon il reçoit **jusqu'à `0x844` octets** directement dans le même tampon et répond `0x2001` (ou `0x2007` si le transfert échoue). **Aucune validation du contenu** |
| `0x90C7` | `0x8D268` | c'est GetEvent (file d'événements), comme le dit libgphoto2, pas une commande de courbe |

### 5.2 Format (vérifié, sauf mention)

| Octets | Contenu |
|---|---|
| 0 à 5 | préambule ; **les octets 0 et 1 doivent être non nuls** pour que la courbe soit utilisée (`0x5DEDE`, `0x5DF30`). Valeurs écrites par Nikon Capture : inconnues (hypothèse : sans effet au-delà de ce test) |
| 6 à 67 | la structure `PTPNIKONCurveData` de libgphoto2 après son préambule : début et fin des axes X et Y, gamma (partie entière, centièmes), nombre de points, points (x, y sur 8 bits). Le boîtier ne s'en sert que pour la recopier dans chaque NEF : `0x7E3D4` écrit « I », `0x10`, puis les octets 6 à 67, puis la table développée (`0x1040` octets en tout, hypothèse : la balise ContrastCurve des notes Nikon) |
| 68 à 2 115 | **2 048 valeurs de sortie sur 8 bits** (0 à 255) |

Au rendu, la table est développée en 4 096 entrées sur 16 bits (chaque valeur, puis la moyenne avec la suivante, `0x5DF30`) : entrée sur 12 bits, sortie sur 8. La forme est donc **libre point par point**, pas limitée aux 19 ou 20 points de Nikon Capture.

**Courbe d'usine** (`0x17329C`, 2 048 octets, entête vide devant) : 0, 63, 105, 136, 157, 173… 255 aux entrées 0, 128, 256… C'est une courbe de transfert complète, gamma compris (un quart de la sortie dès 6 % de l'entrée) : **l'entrée de la table est linéaire**. Hypothèse forte (forme de la courbe). D'après le manuel (p. 47, « sans courbe perso, Personnalisée vaut Normale »), c'était la courbe Normale : **infirmé en octobre 2026**, envoyée telle quelle elle rend plus sombre que la courbe Normale intégrée (ombres et tons moyens ; [`d200-firmware-image.md`](d200-firmware-image.md) §3). L'entrée linéaire est confirmée (vue « linéaire » reproduite à ΔE2000 1,5 à 1,6).

Conséquence pratique : une courbe « à la Lightroom », pensée en espace gamma, doit être **composée** avec la courbe d'usine : table[i] = f(usine[i]). La courbe identité redonne alors exactement le rendu actuel.

### 5.3 Où elle vit (vérifié)

- Un seul tampon RAM, `0x97BD0B14`, de `0x844` octets.
- Il figure dans la table des zones de réglages sauvegardées (`0x16C768`, 12 entrées (adresse, taille) ; la courbe est la 7e : `97 BD 0B 14 08 44`). Au démarrage, `0x72C06` recopie chaque zone depuis la plus récente de deux copies ; si aucune des deux copies n'existe pour la zone de la courbe (drapeau `0x9798E90A`), il **remet à zéro ses 68 octets d'entête** (et pas la table). C'est exactement l'état lu sur le boîtier : entête nul, table de résidus.
- Donc une courbe envoyée **survit à l'extinction** (hypothèse forte : la zone est dans la table de sauvegarde ; moment exact de l'écriture en mémoire non lu). Éteindre normalement à l'interrupteur, sans retirer la batterie, après un envoi.

### 5.4 Quand elle s'applique (vérifié, `appelant.c`, `0x5D716`)

La fonction qui charge le moteur d'image avant chaque photo remplit **trois tables** (`0x50018400`, `0x5001A400`, `0x5001C400`, une par canal R, V, B) :

1. si le mode d'image vaut 6 (hypothèse : N&B), trois tables propres au N&B, choisies par un index de 2 bits (`0x162978`), **jamais la courbe perso** ;
2. sinon, si le numéro de courbe est inférieur à `0x17` : une des courbes intégrées (Auto, Normale, Moins, Plus contrasté) ;
3. sinon (numéro `0x17`, comme la courbe perso du D40) : **la courbe perso, la même sur les trois canaux** ;
4. dernier cas, une table copiée depuis les réglages de la vue (rôle non lu).

La courbe perso agit donc sur R, V et B séparément mais à l'identique : elle change contraste et luminosité, et, parce qu'elle est appliquée par canal, un peu la saturation. Elle ne peut pas teinter (pas de courbe par canal), et elle ne touche jamais au N&B.

Piste pour plus tard (firmware) : l'index de 2 bits du N&B donne quatre jeux de trois tables, ce qui colle avec le groupe « Monochrome : Noir et blanc, Sépia, Cyanotype » des textes du firmware (perspectives §1.1). Hypothèse.

---

## 6. Ce que coûterait l'outil d'envoi `0x90C6`

| Pièce | Travail | Statut |
|---|---|---|
| Fabriquer le bloc | Python : entête (octets 0 et 1 non nuls, axes 0-255, gamma 1,00, les points de la courbe pour l'archive dans le NEF), puis 2 048 valeurs = f(courbe d'usine), f donnée par points ou par une LUT | petit, réutilise `courbes.py` / `picture_control.py` |
| Envoyer | Swift : `d200_ptp.swift` + une commande sortante sans paramètre (comme `d750_ecrire.swift` le fait pour `0x90CD`), puis relecture par `0x90C5` et comparaison octet par octet | petit ; le cadrage sortant d'ImageCaptureCore est déjà validé sur le D750 |
| Garde-fous | filtre « D200 », taille exactement 2 116, octets 0 et 1 non nuls, sauvegarde de la courbe en place avant tout envoi, simulation par défaut | comme `d750_ecrire.swift` |
| Retour en arrière | renvoyer `courbe_90c5_sans.bin` (entête nul) : le boîtier revient à la courbe d'usine | vérifié (code : entête nul = courbe ignorée) |

Risque : un mauvais bloc ne peut que donner une mauvaise courbe dans Personnalisé (rien n'est vérifié par le boîtier, mais rien d'autre n'est touché : le tampon est isolé, la taille bornée à `0x844` par le gestionnaire). Le firmware ne change pas d'un octet : c'est un réglage au sens du projet.

Le même outil sert au D40 en changeant la taille (`0x1044`, 2 048 valeurs sur 16 bits, sortie 12 bits, [CARTE §7](../../d40/CARTE.md)).

---

## 7. Les valeurs de balance par `0x90C9` (vérifié, `prewb.c`, `0x8D3E2`)

SetPreWBData, 3 paramètres :

| Paramètre | Rôle | Contrôle |
|---|---|---|
| p1 | n° du préréglage, 0 à 4 (d-0 à d-4) | `< 5`, sinon `0x2006` |
| p2 | deux gains de 16 bits (moitié haute, moitié basse), 256 = ×1 ; le vert est fixé à 256 | chacun `< 0x800` (×8), sinon `0x2006` |
| p3 | taille d'une phase de données facultative (au plus `0x3600` = 13 824 octets, hypothèse : la vignette de la photo de référence montrée au menu) | 0 = pas de données |

C'est ce que faisait Nikon Capture pour « copier une balance vers le boîtier » (manuel p. 39). Intérêt : **une balance exacte et reproductible**, sans charte grise, et des gains hors de ce que donnent les menus (températures 2 500 à 10 000 K, réglage fin ±3) : dominante chaude ou froide franche, ou ni l'une ni l'autre (gains à ×1, rendu vert du capteur brut). Effet réel sur les JPEG : à voir.

---

## 8. Les looks atteignables sans firmware

| Look | Comment | Limite |
|---|---|---|
| Courbe d'un film en couleur (épaule douce, noirs relevés, contraste « Classic Chrome », « Portra ») | courbe perso composée avec la courbe d'usine, en Personnalisé, Correction des tons Personnalisée | même courbe sur R, V, B : ni virage des ombres, ni dominante par zone de tons |
| Couleur plus douce ou plus franche | mode couleur I ou III, saturation Modérée ou Accentuée, teinte ±9° | rien entre les crans |
| Dominante voulue | préréglage de balance aux gains choisis (`0x90C9`), nommé par son commentaire | une dominante globale, pas par zone de tons |
| Une recette par banque | banques A à D : chacune son Optimiser l'image et son choix de balance | **une seule courbe perso pour les quatre banques** ; les préréglages d-0 à d-4 sont communs |
| N&B | « Noir et blanc » d'Optimiser l'image, tel quel | ni filtre, ni virage, ni courbe : Tri-X ou HP5 restent hors d'atteinte sans firmware |

---

## 9. Écritures possibles (à faire seulement sur le go de Thomas)

1. **Courbe d'essai** : sauver la courbe actuelle (déjà fait, `courbe_90c5_sans.bin`), envoyer une courbe nette et lisible (par exemple noirs relevés à 20 / 255), relire par `0x90C5`, faire une photo en Personnalisé › Correction des tons › Personnalisée, comparer le JPEG au NEF, puis **renvoyer la courbe d'origine** et relire. Prérequis : écrire l'outil du §6.
2. **Préréglage de balance** : écrire dans **d-4** (le moins utilisé ? à demander) des gains connus par `0x90C9`, photo, puis remettre ses gains lus (1,80 / 1,40, voir `prop_d029.bin`). Prérequis : savoir quel gain est le rouge (le test le dit), et choisir un préréglage que Thomas accepte de perdre ou de restaurer.
3. **Recettes complètes par banque** (après les deux tests) : C et D sont vides, on y range deux recettes nommées (Optimiser l'image, balance, nom de banque par `0xD013`, `0xD014`).
4. Vérification sans rien écrire par USB : passer à la main sur la banque B au menu, relancer la sonde, revenir sur A. La courbe relue doit être identique (preuve sur le boîtier de l'unicité) et les réglages du §4 donnent ceux de la banque B.

---

## 10. Ce qui reste incertain

| Point | Statut | Comment trancher |
|---|---|---|
| Ordre des valeurs de Optimiser, Netteté, Correction des tons, Saturation | hypothèse forte (calée sur les valeurs d'usine) | un coup d'œil au menu de la banque A (Personnalisé, Moyenne +, Plus contrasté, Auto ?) |
| Entrée de la table linéaire, courbe d'usine = Normale | entrée linéaire : vérifié (séance d’octobre) ; courbe d'usine = Normale : **faux** | essai 1 du §9 (courbe identité composée = rendu identique) |
| Persistance de la courbe à l'extinction | hypothèse forte | essai 1, en éteignant le boîtier avant la relecture |
| Rouge / bleu dans les gains de balance | hypothèse | essai 2 |
| Correction d'exposition à +5 IL | lu, cause inconnue | écran de contrôle |
| Mode d'image 6 = N&B, index de 2 bits = Monochrome caché | hypothèse | firmware, plus tard |
