# Émulateur du processeur B du D200 : appel des fonctions du moteur d'image

Fait en octobre 2026. Il exécute les vraies fonctions du firmware B 2.01 du D200 (d'origine, ou patché par `d40/patch.py`) dans le cœur FR de l'émulateur du D40, pour vérifier **avant un flash** ce que le firmware écrit dans les registres de sa puce d'image. Rien ne démarre : un scénario prépare la mémoire (la fiche de prise de vue), appelle la chaîne de prise de vue puis `isp_chargerPuce`, et compare ce qui est écrit. Point 2 du §7 « Avant un flash » de [`d200/recherche/d200-firmware-image.md`](../recherche/d200-firmware-image.md). Rien n'est flashé, le boîtier n'est pas touché.

Chaque fait est marqué *vérifié* (rejoué dans l'émulateur ou lu dans les instructions, à l'adresse donnée) ou *hypothèse*.

## Lancer

```
python3 d200/emulateur/d200emu.py verifier                    # tout, code de sortie 0 si conforme (64 s sur le Mac Studio)
python3 d200/emulateur/d200emu.py scenario nb-origine         # un scénario, firmware d'origine
python3 d200/emulateur/d200emu.py patch d200/patchs/d200-nb-trix.json nb-trix  # fabrique le firmware (d40/patch.py) puis joue le scénario
python3 d200/emulateur/d200emu.py combine preglages           # Tri-X + noms + préréglages (liste COMBINE), puis le scénario
python3 d200/emulateur/d200emu.py scenario couleur-origine --firmware <B2000201.BIN>
python3 d200/emulateur/d200emu.py desassembler 0xD93A6 48
```

- Prérequis : ceux de l'émulateur du D40 (JDK de Homebrew, clone de nikon-firmware-tools dans `~/Library/Caches/d40-emulateur/nft`), le binaire `~/Library/Caches/retro-ingenierie-boitiers/firmware/d200-201/B2000201.bin` (sha256 contrôlé avant chaque scénario joué sur l'original).
- Tout ce qui est compilé ou fabriqué va dans `~/Library/Caches/d40-emulateur/d200/` (option `--travail`) : `classes/`, `firmwares/<nom du patch>/B2000201.BIN`, `d200-combine.json` et `firmwares/d200-combine/` (le combiné Tri-X + noms + préréglages, réuni puis fabriqué par `d40/patch.py`, qui refuse un chevauchement). Rien n'est écrit dans `d200/build/` ni dans le dossier synchronisé.
- La compilation reprend seulement les deux classes de `java/` et le cœur FR (`javac -sourcepath`) ; elle est refaite quand un `.java` change. Le code du D40 (`d40/emulateur/java`, `d40emu.py`) n'est pas modifié : `d200emu.py` importe seulement `jdk()` et l'adresse du dépôt. `python3 d40/emulateur/d40emu.py verifier` rend toujours 0 (rejoué en octobre 2026).
- La JVM est lancée et attendue par le script : aucun processus ne reste derrière.
- Le scénario `nb-trix` vaut pour le patch Tri-X ; pour HP5 ou FP4, copier le scénario et changer les trois coefficients (51, 15, 255 ou 72, 34, 255) et les deux octets de courbe.

## Résultat de `verifier` (octobre 2026, préréglages compris)

| Essai | Firmware | Scénario | Code attendu | Résultat |
|---|---|---|---|---|
| a. N&B | d'origine | `nb-origine` | 0 | OK, 403 contrôles |
| b. N&B Tri-X | `d200/patchs/d200-nb-trix.json` par `d40/patch.py` (10 patchs, 3 940 octets, CRC `f84f`) | `nb-trix` | 0 | OK, 1 738 contrôles |
| b′. contre-épreuve | d'origine | `nb-trix` | 1 (doit échouer) | OK : 422 contrôles en échec |
| c. couleur | d'origine | `couleur-origine` | 0 | OK, 157 contrôles |
| c′. couleur | Tri-X | `couleur-origine` | 0 | OK : la couleur ne change pas |
| b″. N&B | combiné Tri-X + noms + préréglages | `nb-trix` | 0 | OK, 1 738 contrôles : le N&B reste Tri-X |
| d. préréglages | combiné | `preglages` | 0 | OK, 1 781 contrôles |
| d′. contre-épreuve | d'origine | `preglages` | 1 (doit échouer) | OK : 1 218 contrôles en échec |
| d″. contre-épreuve | Tri-X seul (sans crochets) | `preglages` | 1 (doit échouer) | OK : 1 218 contrôles en échec |
| garde, créneau de délai | d'origine + `LDI:32` posé en `0xD93D6` | `garde-delai` | 2 | OK |
| garde, noyau | d'origine | `garde-noyau` | 2 | OK (`get_tid` dans `FUN_0005d444`) |

## La chaîne jouée

| Étape | Fonction | Ce qu'elle fait | Statut |
|---|---|---|---|
| 1 | `FUN_0005d616` (`0x5D616`), R4 = fiche, R5 = 1 | appelée ainsi par la tâche de prise de vue `FUN_0005cc64` ; mode 0 si l'octet `0x35` de la fiche a le bit 7 à 0 (fiche pas encore traitée), mode 2 sinon ; appelle `FUN_000cd9a2` | vérifié |
| 2 | `FUN_000cd9a2` | range le pointeur de fiche en `0x97BE3E4C` ; en mode 0, mesures et balance (aucun appel au noyau : 460 000 instructions sans `INT`), puis `FUN_000ce4fa` et `FUN_000cf86a` | vérifié |
| 3 | `FUN_000ce4fa` | lit les octets `0x4C` à `0x4F` de la fiche ; Optimiser = 6 : `0x97BE3DBC` = 1 (N&B), `0x97BE3DB8` = bits 6-7 de `0x4E` (variante), teinte `0x97BE3DE8` = 3 | vérifié |
| 4 | `FUN_000cf86a` → `FUN_000d57e6` (isp_matricesEtNB) | choisit le jeu de matrices, range la matrice caméra (9 mots signés en `0x97BE09F0`) et Y, Cb, Cr (9 mots en `0x97BE09CC`) ; N&B : valeurs en dur, puis jeu forcé à 500 | vérifié |
| 5 | `FUN_000d846a` | recopie Y, Cb, Cr en `0x97BE09A8`, puis recalcule Cb et Cr (rotation de teinte, flottants logiciels), bornés à ±0x1FF ; Y n'est pas touché ; avec Cb = Cr = 0 (N&B) ils restent à 0 | vérifié |
| 6 | `FUN_000d93a6` | **conversion** des mots vers la fiche, `+0x33C` (caméra) et `+0x34E` (Y, Cb, Cr), voir plus bas ; aussi l'étage à 16 secteurs (`+0x37A` à `+0x419`) | vérifié |
| 7 | `isp_chargerPuce` (`0x5D716`), R4 = fiche | fiche `+0x33C` → registres `0x50010022` à `0x50010033`, `+0x34E` → `0x50010034` à `0x50010045` (copie de demi-mots, sans transformation) ; puis les courbes en `0x50018400`, `0x5001A400`, `0x5001C400` | vérifié |

`isp_chargerPuce` est appelée directement : son appelant réel, `FUN_0005d444`, l'appelle puis attend un drapeau du noyau (`get_tid`, `wai_flg`), non émulé (scénario `garde-noyau`). Ce que `FUN_0005d444` écrit avant (`0x5001FF04` à `0x5001FF14`, `0x50010002`, `0x50010004`) n'est donc pas contrôlé.

## Format des registres de matrice (le point à vérifier)

Relu dans les instructions de `FUN_000d93a6` (`0xD93E2` à `0xD9414`) et rejoué : **signe et module**, sans masque ni plafond.

| Matrice | Registres | Fiche | Bit de signe | Valeur positive | Valeur négative v | Plage portée |
|---|---|---|---|---|---|---|
| caméra (/512) | `0x50010022` + 2n, n = 0 à 8, ligne par ligne | `+0x33C` | bit 10 (`0x400`) | rangée telle quelle (`STH`, 16 bits bas) | `0x400 \| abs(v)` (`FUN_000cb07a`, `EXTUH`, `OR`) | −1023 à 1023 |
| Y, Cb, Cr (/256) | `0x50010034` + 2n | `+0x34E` | bit 9 (`0x200`) | telle quelle | `0x200 \| abs(v)` | −511 à 511 |

- Exemples relevés : −223 → `0x04DF`, −9 → `0x0409`, 542 → `0x021E`, −335 → `0x054F`, −50 (Cb) → `0x0232`. Vérifié.
- **Rien ne borne une valeur positive** : 1023 → `0x03FF`, mais 1024 → `0x0400`, qui tombe sur le bit de signe (scénario `nb-origine`, « limite du format »). Vérifié pour ce que le firmware écrit ; que la puce lise alors −0 est une hypothèse. Seuls Cb et Cr passent par une borne (±0x1FF dans `FUN_000d846a`).
- Que la puce lise bien bit 10 (bit 9) comme le signe : hypothèse, cohérente avec le simulateur `d200/outils/d200_simulateur.py`, qui interprète les registres ainsi et reproduit le N&B du boîtier à ΔE2000 médian 0,58 à 0,64.
- Les courbes : 4 096 demi-mots par canal, valeur 0 à 255. En N&B, les 4 096 octets de `0x3B22DD` recopiés un par un (`FUN_0005debe`), la même table sur R, V, B ; en couleur, les 256 seuils de la courbe intégrée développés par `FUN_0005df82`. Vérifié.

## Ce que chaque scénario vérifie

Une commande `expect…` ratée donne le code 1 ; une garde, le code 2. Avant chaque appel, les mots `0x97BE09CC` à `0x97BE0A13`, la fiche `+0x33C` à `+0x35F` et les registres de matrices et de courbes sont remplis de `0xEE` : une valeur que le code n'aurait pas écrite fait échouer le contrôle.

### a. `nb-origine` : N&B, firmware d'origine (vérifié)

Fiche à zéro, octet `0x4D` = `0x0C` (Optimiser = 6), `0x4E` = 0.
- `0x97BE09F0` = 744, −223, −9, −41, 656, −103, −23, −7, 542 ; `0x97BE09CC` = 76, 151, 29, puis six 0 ; `0x97BE0A14` = 500.
- Fiche `+0x33C` et registres `0x50010022` = `02E8 04DF 0409 0429 0290 0467 0417 0407 021E` ; `+0x34E` et `0x50010034` = `004C 0097 001D` puis six `0000` ; chaque demi-mot recalculé depuis le mot source (`expectconv`) et registres identiques à la fiche octet par octet.
- Courbes : `0x50018400`, `0x5001A400`, `0x5001C400` = les 4 096 octets de `0x3B22DD` (premier 0, dernier 255).
- Étage à 16 secteurs neutralisé : `0x5001E400` et `0x5001E460` = 16 × `0x00FF`, `0x5001E420` et `0x5001E440` = 16 × 0.
- Balayage du LDI:8 du coefficient [2] (`0xD7850`, suivi d'`EXTSB`) de 0 à 255, chaîne complète rejouée à chaque valeur : le registre `0x50010026` vaut le signe et module de la valeur étendue en signe (127 → `0x007F`, 128 → `0x0480`, 255 → `0x0401`). C'est ce que donnerait le patch **sans** les `NOP`.
- Limite du format : 1023 et 1024 posés dans le LDI:20 du coefficient [0] (voir ci-dessus).

### b. `nb-trix` : N&B, firmware patché Tri-X (vérifié)

- `0x97BE09F0` = 121, 65, 255, 121, 65, 255, −23, −7, 542 : **255 est rangé positif**, les `NOP` ont bien remplacé les `EXTSB` ; `0x97BE09CC` = 128, 128, 0, puis six 0.
- Registres `0x50010022` = `0079 0041 00FF 0079 0041 00FF 0417 0407 021E` ; `0x50010034` = `0080 0080 0000` puis six `0000`.
- Courbes : les 4 096 octets de `0x3B22DD` du firmware patché, sur R, V, B ; premier `0x09` et dernier `0xF3`, ceux de la courbe Tri-X du JSON.
- Étage à 16 secteurs : identique au N&B d'origine.
- **Balayages** des six LDI:8 du patch, v = 0 à 255, chaîne complète (`FUN_0005d616` puis `isp_chargerPuce`) à chaque valeur : coefficients [2], [3], [5] de la matrice (`0xD7850`, `0xD7858`, `0xD7868`, registres `0x50010026`, `0x50010028`, `0x5001002C`) et ligne Y (`0xD7888`, `0xD7892`, `0xD789C`, registres `0x50010034` à `0x50010038`) : le registre vaut v pour les 256 valeurs, 128 → `0x0080`, 255 → `0x00FF`. Ni signe, ni troncature. Les instructions sont remises ensuite et la chaîne redonne les valeurs du patch.
- Variante sépia (octet `0x4E` = `0x40`, absente des menus), branche voisine du patch : matrice (152, 302, 58) sur les trois lignes, Y, Cb, Cr = (256, 0, 0 ; 0, −256, 0 ; 0, 0, 256), registres `0098 012E 003A` ×3 et `0100 0000 0000 0000 0300 0000 0000 0000 0100`, courbes `0x39DB30`, `0x39EB30`, `0x39FB30` sur R, V, B : identiques sur les deux firmwares. Les tables de V et B finissent à 0 : avec cette matrice YCbCr, elles portent sans doute le virage (Cb, Cr) selon la luminance, nul dans les blancs (hypothèse, utile pour un patch qui garderait le N&B Nikon et détournerait la sépia).
- Aucune garde déclenchée, pile rendue à chaque appel (profondeur maximale 364 octets pour `FUN_0005d616`, 40 pour `isp_chargerPuce`).
- **b′** : joué sur le firmware d'origine, ce scénario échoue (422 contrôles sur 1 738, dont les trois balayages de la matrice dès v = 128) : les contrôles distinguent bien les deux firmwares.

### c. `couleur-origine` : un jeu de `tblMatrices` jusqu'aux registres (vérifié)

Cinq fiches, une par cas. Pour chaque cas : numéro de jeu (`0x97BE0A14`) et de courbe (`0x97BE0A18`), registres de la caméra = les demi-mots 0 à 8 du jeu convertis (bit 10), registres Y, Cb, Cr = les demi-mots 9 à 17 convertis (bit 9), courbes = la courbe intégrée développée sur R, V, B.

| Cas | Octets de la fiche | Jeu, courbe | Ce qui arrive dans les registres |
|---|---|---|---|
| c1 | `0x4D` = 0 (Normal) | 11, 2 | les 18 demi-mots du jeu 11, convertis ; caméra `02C9 04C8 0401 041A 0264 044A 0408 0426 022E` |
| c2 | `0x4D` = 2 (Optimiser = 1) | 13, 0 | jeu 13 converti |
| c3 | `0x4D` = 4 (Optimiser = 2) | 94, 17 | jeu 94 converti : `02EF 054F 0060 0446 0298 0452 040A 0006 0204` (−335 et un 96 positif) |
| c4 | `0x4D` = 6 (Optimiser = 3) | 91, 20 | jeu 91 converti |
| c5 | `0x4D` = `0x0A` (Personnalisé), `0x4F` = +3 (teinte +9) | 11, 2 | caméra et ligne Y du jeu 11 telles quelles ; **Cb et Cr recalculés** par `FUN_000d846a` (−63, −119, 183 ; 154, −124, −29 au lieu de −50, −130, 180 ; 159, −114, −45), puis convertis : `023F 0277 00B7 009A 027C 021D` |

- La conversion est la même qu'en N&B : **une entrée de la table arrive convertie en signe et module, sans autre changement**, sauf Cb et Cr quand la teinte n'est pas neutre. Les 6 derniers demi-mots du jeu ne vont pas dans ces registres (non suivis). Vérifié.
- Les numéros de jeu sont ceux que l'émulateur donne avec une fiche à zéro (mesures nulles, `0x97BE1C3C` = 85) : ils dépendent des mesures dans le boîtier. Les courbes 0, 17, 20 pour Optimiser = 1, 2, 3 concordent avec la séance d’octobre (Moins net 0, Saturé 17, Très saturé 20) ; les noms des modes 1 à 3 en viennent (hypothèse).
- **c′** : les mêmes cas sur le firmware Tri-X donnent les mêmes registres : le patch ne touche pas la couleur.

### d. `preglages` : les quatre rendus d'Optimiser l'image (vérifié)

Scénario écrit par `python3 -B d200/outils/d200_preglages.py scenario` (ne pas l'éditer à la main) : les valeurs attendues viennent des données des rendus (Chrome, Positive, FP4, HP5), converties en signe et module ; les courbes attendues sont posées en RAM libre (`0x97F80000`). Détail, adresses et résultats : [`d200/recherche/d200-preglages.md`](../recherche/d200-preglages.md) §6.
- Moins net, Saturé, Très saturé, Portrait en ensoleillé (F = 1) et incandescent (F = 0), plus ombre, fluo (F = 4), Adobe RGB et balance auto : variables netteté 4, saturation 1, tons 1 ; jeu `42 E + 7 F + 3` ; registres caméra, YCbCr, 64 secteurs et 3 courbes = le rendu ; reste des registres, tables ISO et saturation = un Personnalisé réglé à la main joué juste avant.
- Normal, Personnalisé, Noir et blanc : registres et fiche identiques à la même fiche jouée **sans crochets** (macros `sans_crochets` et `avec_crochets` : les deux constantes de Nikon remises le temps du passage, puis celles du firmware joué ; sur le firmware d'origine, rien ne change, d'où l'échec attendu de d′).
- Deux photos, deux balances (chaque fiche porte son jeu) ; jeu 500 ou 52 dans la fiche et chemin des matrices en dur : rendu de Nikon.

### Gardes

- `garde-delai` : `LDI:32` posé en mémoire dans le créneau du `BRA:D` de `0xD93D4` : arrêt, code 2.
- `garde-noyau` : `FUN_0005d444` atteint `get_tid` : arrêt, code 2.

## La fiche de prise de vue

- C'est l'argument R4 de `FUN_0005d616` et d'`isp_chargerPuce` ; `FUN_000cd9a2` range son adresse en `0x97BE3E4C`. Dans le boîtier, elle sort des files `0x979DAF3C` et `0x979DAF44` de `FUN_00051992` (adresse dynamique, hypothèse) ; l'émulateur la pose en `0x97F00000` (`0x97E00000` + n × `0x10000` en couleur), à zéro sauf les octets cités.
- Octets lus par la chaîne avant d'être écrits (commande `lectures`, vérifié) : `+0x30` à `+0x33`, `+0x35`, `+0x4C` à `+0x4F`, `+0x54`, `+0x56`, `+0x57`, `+0x7C`, `+0x8E` à `+0x90`, `+0xA1`, `+0x105` à `+0x109`, `+0x10B` à `+0x10E`, `+0x110` à `+0x169`, `+0x16E`, `+0x174`, `+0x175`, `+0x199` à `+0x19B`, `+0x1EE` à `+0x1F3`, `+0x6B0`.
- Rôle connu (lu dans `FUN_000ce4fa`, `FUN_0005d616`, `FUN_000cd9a2`) : `0x4D` bits 1 à 4 = mode d'Optimiser (6 = N&B, 5 = Personnalisé), bits 5-6 et 7 = mode couleur ; `0x4E` bits 6-7 = variante N&B ; `0x4F` = teinte (−3 à +3, signé) ; `0x4C` = autres réglages ; `0x35` bit 7 = fiche déjà traitée (mode 2 au second passage, remis à 0 par les balayages pour rejouer le même chemin) ; `0x6B0` = 1 retraitement (mode 3), 2 pas de calcul. Vérifié (code).
- Le N&B n'est pris que si `0x97BE3DCC` = 0, soit le bit 4 de l'octet `0x9798D753` : aucune écriture de ce bit n'apparaît dans le pseudo-C (seuls les bits 6 et 7, par `FUN_000994d8`). Il vaut 0 dans l'émulateur, très probablement aussi dans le boîtier (hypothèse).

## Ce qui est émulé, bouché

| Bloc | Traitement |
|---|---|
| Cœur FR (instructions, créneaux de délai) | nikon-firmware-tools, comme le D40 |
| ROM `0x50000` à `0x40FFFF` | le fichier B2000201.bin ; une écriture du code y déclenche une garde |
| RAM `0x9xxxxxxx`, `0x4xxxx`, registres `0x5001xxxx`, `0x5006xxxx`, `0x5009xxxx` | mémoire simple, mise à zéro, allouée à la demande ; aucun périphérique |
| Noyau µITRON (`INT #0x40`) | **non émulé** : garde ; `noyau ok` le remplace par un retour E_OK journalisé (pas utilisé par les scénarios livrés) |
| Interruptions, minuteries, démarrage | absents (interruptions masquées pendant un `appel`) |
| Pile des appels | privée, `0x9FFF0000`, hors de la RAM réelle supposée (`0x90000000` à `0x97FFFFFF`) ; retour fictif `0x9FFFFFF0` |

Gardes (code 2) : instruction non définie ou `0xFFFF` ; saut, appel, retour ou instruction de plusieurs mots dans un créneau de délai ; PC hors ROM et RAM, ou dans `0xF0000` à `0x11FFFF` et `0x1D0000` à `0x1FFFFF` (jamais écrites par la mise à jour) ; écriture en ROM ; `INT` ; pile non rendue ; plus de 50 M instructions sans retour.

## Langage des scénarios (`scenarios/*.txt`)

Une commande par ligne, `#` commente. Nombres : `0x…` en hexadécimal, sinon décimal signé (`-223`) ; c'est différent du D40, où tout est lu en hexadécimal.

| Commande | Effet |
|---|---|
| `appel <adr> [r4 r5 r6 r7]` | exécuter une fonction jusqu'à son retour (comme le D40) ; affiche instructions, R4, profondeur de pile |
| `retour <adr> <v>` | la fonction rend aussitôt v |
| `peek`, `peek16`, `peek32 <adr> [n]` | afficher octets, demi-mots, mots (valeur signée entre parenthèses) |
| `poke8`, `poke16`, `poke32 <adr> <v>…`, `remplir <adr> <n> <octet>`, `copier <src> <dst> <n>`, `charger <fichier> <adr>` | écrire (aussi en ROM, pour poser une instruction) |
| `expect8`, `expect16`, `expect32 <adr> <v>…` | vérifier une ou plusieurs valeurs consécutives |
| `expectegal <a> <b> <n>` | n octets identiques |
| `expectdemi <demi> <octets> <n>` | n demi-mots égaux à n octets (courbe recopiée) |
| `expectcourbe <demi> <seuils>` | 4 096 demi-mots = 256 seuils développés (réécrit indépendamment de `FUN_0005df82`) |
| `expectconv <reg> <src> <n> <taille> <bit>` | n demi-mots = signe et module des n valeurs signées de taille 2 ou 4 en src ; échec si une valeur dépasse le format |
| `lectures <nom> <adr> <n>`, `bilanlectures` | octets lus par le code avant qu'il ne les écrive |
| `watch <adr>…`, `watchw <adr> <n> [max]` | passages du PC, écritures dans une plage |
| `macro <nom>` … `fin`, `jouer <nom>` | retenir et rejouer une suite de commandes |
| `balayage <macro> <ldi8> <de> <à> <reg> <bit> brut\|signe` | pour chaque v : poser `LDI:8 #v` en ldi8, jouer la macro sans rien afficher, comparer le registre à v (brut) ou au signe et module de v étendu en signe ; l'instruction est remise à la fin |
| `noyau ok\|garde`, `dis <adr> <n>`, `regs`, `titre <texte>` | |

Fichiers : `d200emu.py` (lanceur), `java/D200Emu.java` (mémoire, gardes, traceur de lectures), `java/D200Boot.java` (scénarios), `scenarios/`.

## Risques relevés pour le patch N&B

1. **`NOP` à la place d'`EXTSB`** : sans risque. Les trois coefficients concernés arrivent dans les registres tels quels pour toute valeur de 0 à 255 (balayages), 255 → `0x00FF`. Avec l'`EXTSB` d'origine, 255 donnerait `0x0401` (−1/512) et 128 `0x0480` (−128/512) : c'est ce que les `NOP` évitent. Vérifié.
2. **Pas de plafond sur les valeurs positives** : un coefficient caméra de 1024 ou plus (512 ou plus pour Y, Cb, Cr) déborde sur le bit de signe sans alerte. Les patchs Tri-X, HP5 et FP4 restent sous 256 ; un futur patch qui écrirait un LDI:20 ou un LDI:32 au-delà de 1023 serait faux en silence. Vérifié.
3. La ligne 2 de la matrice (−23, −7, 542) garde ses `EXTSB` et reste correcte (`0417 0407 021E`) ; la ligne Y (128, 128, 0) n'a pas besoin d'`EXTSB` (le LDI:8 d'origine de 151 n'en a pas). Vérifié.
4. Le patch ne touche que la branche N&B neutre : couleur identique (c′), variante sépia identique (rejouée dans `nb-trix`) ; cyanotype (`0x97BE3DB8` = 2) hors des octets du patch (lu, non rejoué).
5. Les lignes 0 et 1 font 441/512 : le blanc sort à 0,861 du plein, compensé par la courbe (entrée divisée par k, §5 de la recherche). Voulu, pas un défaut.
6. Non couvert par l'émulateur : la façon dont la puce lit réellement ces registres (hypothèse ci-dessus), le reste du traitement (JPEG, netteté, `FUN_0005d444`), les autres chemins (retraitement d'un NEF, `FUN_00061ea0`), le chronométrage. Le choix du jeu en couleur dépend des mesures, nulles ici.

## Limites et suites possibles

- Le noyau n'est pas émulé : toute fonction qui attend un drapeau ou un sémaphore s'arrête sur la garde (ou, avec `noyau ok`, continue sur un E_OK qui n'est qu'une hypothèse).
- La fiche est à zéro hors des octets de mode : une fiche relevée dans le boîtier (mesures, balance) rendrait le choix du jeu de matrices réaliste ; la méthode serait de lire la fiche par USB ou depuis la MakerNote d'un NEF (non étudié).
- Le nom des modes d'Optimiser 1 à 4 vient de la concordance des courbes avec la séance d’octobre, pas d'une lecture des menus.
