# Lignes de programme, ISO auto et menus : recherche (octobre 2026)

Objet : des lignes de programme au choix façon Pentax (sujet rapide, portrait, profondeur de champ, piqué max), un ISO auto façon Fuji, et des menus pour choisir tout ça. Le menu des rendus couleur est traité ailleurs, comme la sécurité du flashage du A (`reecriture-firmware-materiel.md`).

Repères de confiance, comme dans `CARTE.md` : **vérifié** (lu dans le code, les données ou la source citée, puis recoupé), **probable** (indice fort), **déduit** (raisonnement de ma part, pas de lecture directe), **hypothèse** (à tester).

Sources du code : `a-tout.c` et `d40-tout.c` régénérés par `desassemblage/regenerer.sh` (dossier de travail de la session, hors du dépôt). Les adresses sont celles du processeur (A : offset + `0xC0000`, B : offset + `0x40000`). L'outil qui évalue les lignes transcrites ci-dessous, `lignes.py`, est resté dans le dossier de travail de la session et n'est pas dans le projet (consigne : ne rien ajouter d'autre).

---

## 1. Pentax : ce que font les lignes de programme

### Ce que disent les manuels officiels (vérifié)

- **645D** (*Menu Reference*, p. R15, menu A2 › Program Line) : six réglages : AUTO, Normal (défaut), Hi-speed Priority, DOF Priority (deep), DOF Priority (shallow), MTF Priority. Pour MTF, le manuel dit « prioritizes the best aperture value for the attached lens ». La ligne s'applique en P et en Sv, ou en TAv et M par le bouton vert si on l'a réglé ainsi (réglage perso 29). Source : https://www.ricoh-imaging.co.jp/english/support/man-pdf/645d_menu.pdf
- **645Z** : même menu (A2, p. R18, défaut Normal). https://www.ricoh-imaging.co.jp/english/support/man-pdf/645z_menu.pdf
- **K-5** (p. 102) et **K-1** (p. 46) : mêmes six réglages. Pour MTF, le K-1 dit « Sets the sharpest aperture of the attached lens when a D FA, DA, DA L, FA, or FA J lens is used », et le K-5 « most effective » avec ces familles. https://www.ricoh-imaging.co.jp/english/support/man-pdf/k-5.pdf, https://www.ricoh-imaging.co.jp/english/support/man-pdf/k-1.pdf
- **Aucun de ces manuels ne donne les courbes.** Le seul manuel Pentax numérique qui les trace est celui de l'***ist D*** (2003), pages 158 et 159 : quatre graphes vitesse × ouverture × IL, à ISO 200, avec un FA J 18-35 mm f/4-5.6 (une courbe à chaque bout du zoom). Source : https://www.ricoh-imaging.co.jp/english/support/man-pdf/istd.pdf

### Les courbes de l'*ist D, lues sur les graphes (vérifié pour l'allure, lecture à ±1/3 IL)

Axes du manuel : IL à ISO 200 = Tv + Av, comme dans le D40 (§2).

| Ligne | Faible lumière | Zone moyenne | Forte lumière |
|---|---|---|---|
| Normal | pleine ouverture (f/4 à f/5,6) jusqu'à 1/30–1/60 environ | ouverture et vitesse montent ensemble, la vitesse plus vite (environ f/8 à 1/125, f/16 à 1/4000) | à 1/4000 (vitesse maxi), l'ouverture ferme jusqu'à f/32 |
| Hi-speed | pleine ouverture | **reste à pleine ouverture jusqu'à 1/2000–1/4000**, avec seulement un petit cran vers 1/60 (changement d'ouverture du zoom) | ferme seulement en butée de vitesse |
| DOF (deep) | pleine ouverture jusqu'à 1/30–1/60 | **ferme très vite** (presque à vitesse constante) jusqu'à f/22–f/32 | vitesse qui monte, à f/22–f/32 |
| MTF | **ouverture fixe** (environ f/8 à 18 mm, f/6,7 à 35 mm) dès les vitesses lentes | ouverture fixe, seule la vitesse change | ferme seulement en butée de vitesse |

La ligne MTF est donc une **priorité ouverture déguisée**, réglée sur l'ouverture de meilleur piqué de l'objectif, qui n'en bouge pas tant que la vitesse le permet. DOF (shallow) est apparue après l'*ist D : manuels K-5, K-1 et 645D, mais pas de graphe.

### D'où viennent les données MTF (non résolu)

- Les manuels limitent l'effet aux objectifs à puce Pentax (FA, FA J, DA, D FA). Ça prouve que la donnée dépend de l'objectif identifié, mais pas où elle est stockée. Vérifié pour la limitation.
- Hypothèse lue sur des forums, sans source primaire : le manuel du PZ-1p (1991) disait que les données sont dans l'objectif FA lui-même (résumé de recherche web, PentaxForums et pentaxuser.com, pages inaccessibles en lecture directe). Je ne l'affirme pas.
- Aucune analyse publique du firmware Pentax ou de la ROM des objectifs KAF n'en donne le format (recherche d’octobre 2026, rien trouvé).
- **Pour le D40, la question ne se pose pas** : Nikon ne transmet aucune donnée MTF. On embarque notre propre table, indexée par l'identifiant d'objectif (§3). Le comportement à reproduire est celui des graphes, ce qui suffit sans désassembler un firmware Pentax.

---

## 2. Les lignes de programme du D40 (firmware A)

### Unités (vérifié par recoupement)

Tout le calcul se fait en **1/48 d'IL**, en grandeurs APEX :
- `ccc0` = **Tv**, la vitesse : 0 = 1 s, `0x240` = 576 = 12 IL = 1/4000 s, `-0xF0` = 30 s. Vérifié (tables de `expo_limiterVitesse`, CARTE §10).
- `ccbe` = **Av**, l'ouverture : 0 = f/1, 96 = f/2, 192 = f/4, 288 = f/8. Vérifié : `ccbe = ccc2 − ccc0` dans toutes les fonctions de mode (`0xC488E`, `0xC60E2`…).
- `ccc2` = **Ev = Tv + Av** à l'ISO courant, calculé par `FUN_000c4064` (`0xC4064`) : mesure (`cf68`) + 8 × Sv (`e1ee`) − 8 × correction (`d0b2`), plus de petites corrections. Le D40 raisonne donc exactement comme les graphes Pentax (IL à l'ISO courant).
- **Sv** (`e1ee`, octet en 1/6 d'IL) : 36 = ISO 200, 42 = 400, 48 = 800, 54 = 1600, 60 = 3200 (Sv APEX × 6). Vérifié : la table `0xFA86C` vaut 36, 42, 48, 54, 60, et `FUN_000c4064` force 36 (`0x24`) en mode scène.
- **Données de l'objectif**, copiées du bloc reçu de l'objectif par la fonction en a-tout.c l.10940–11100 :
  - `d0f0` = focale actuelle (`d132`) ;
  - `d100` = ouverture maxi effective (`d13b`, + correction `d16d`) ;
  - `d0f3` = étendue des diaphragmes (`d135`).
  
  Leur codage est **celui des LensData Nikon** (ExifTool `Nikon.pm` 13.55, tables `LensData01`, l.5441–5452 : focale = 5·2^(x/24), ouverture = 2^(x/24), `LensFStops` = x/12). Il colle à l'usage dans le code : `d100 × 4` est un Av en 1/48 (`FUN_000c4680`), et l'ouverture mini vaut `d100 + d0f3` (même fonction). Probable.
  
  Conséquence : les seuils `d0f0 < 0x54` et `< 0x73` valent **56,6 mm** et **138 mm** de focale réelle. Déduit.

### Comment une ligne est représentée (vérifié)

**Pas de table de points : du code**, avec les constantes dans les instructions. Une « fonction de ligne » choisit un segment par comparaisons successives de Ev, et chaque segment porte trois constantes :

```
Tv = Tv0 + pente × (Ev − Ev0) / 256       pente 0xFF = 1 (ouverture constante), 0x80 = ½, 0x55 = ⅓, 0 = Tv constant
```

Le choix du segment dépend aussi de l'état du flash (`0x3C3C1 & 0x1F` = 3, 5 ou 0xD) et, pour certaines lignes, de la focale (seuils 57 et 138 mm). La fonction pose en plus un **plancher d'ouverture** `ccb9`, en 1/6 d'IL : 0x0C = f/2, 0x12 = f/2,8, 0x18 = f/4, 0 = aucun. Puis la chaîne commune s'applique, la même pour toutes les lignes (`0xC488E` en est le modèle) :
1. Tv = ligne(Ev), borné par `FUN_000c4bb4` (`0xC4BB4`) entre −`0x150` et `0x240` sans flash, et entre la vitesse mini et la vitesse de synchro au flash ;
2. Av = Ev − Tv, borné par `FUN_000c4680` (`0xC4680`) entre max(ouverture maxi de l'objectif, plancher `ccb9`) et l'ouverture mini ;
3. Tv = Ev − Av, borné à nouveau.

C'est le mécanisme Pentax : la ligne donne une vitesse cible, l'ouverture suit, et les butées de l'objectif décident.

### Qui appelle quoi (vérifié ; correction de `symboles-A.tsv`)

- `expo_programme` (`0xC3F84`) : Ev, puis `expo_programmeMode`, puis **soit** `FUN_000c471c` (l'ISO auto de P, S, A et M), **soit**, en scène avec le bit 0 de `0x3E1E0`, une des huit fonctions nommées aujourd'hui `progScene_*`.
- **Les `progScene_*` ne sont pas des lignes de programme : c'est l'ISO auto des modes scène.** Elles ne touchent qu'à `ccbc` (l'ISO choisi, en 1/6 d'IL : `'$'` = 0x24 = 200, `'*'` = 0x2A = 400, `'0'` = 0x30 = 800) et à `ccb2` (Tv/2). Exemple, `progScene_auto` (`0xC58D6`) avec moins de 57 mm, sans flash :
  - vitesse calculée à ISO 200 ≥ 1/125 : ISO 200 ;
  - entre 1/60 et 1/125 : l'ISO monte (200 à 400) pour tenir 1/125 ;
  - entre 1/15 et 1/60 : ISO 400, vitesse +1 IL ;
  - entre 1/8 et 1/15 : 400 à 800 ;
  - en dessous : ISO 800, vitesse +2 IL.
  
  Les seuils montent d'1 IL entre 57 et 138 mm, et d'1 IL encore au-delà. **Le D40 a donc déjà une vitesse mini liée à la focale, mais seulement en mode Auto de scène.** Vérifié (a-tout.c l.5438–5527).
- **Les vraies lignes des scènes** sont la série de `expo_programmeMode` : chaque `FUN_` ci-dessous appelle sa fonction de courbe. Vérifié.

| Code A | Mode | Fonction | Courbe |
|---|---|---|---|
| 15 | Auto | `0xC488E` | `0xC48E0` |
| 14 | Auto sans flash | `0xC5616` | `0xC5674` (= Auto) |
| 13 | Portrait | `0xC4C90` | `0xC4CE2` |
| 12 | Paysage | `0xC4DB8` | `0xC4E0A` |
| 11 | Enfant | `0xC4FDE` | `0xC5034` |
| 10 | Sport | `0xC519A` | `0xC51F0` |
| 9 | Gros plan | `0xC52E8` | `0xC533E` |
| 8 | Portrait de nuit | `0xC54E6` | `0xC5544` |

- **P** (`0xC60E2`) appelle `expo_ligneProgramme` (`0xC41C2`), puis applique le décalage de programme (`c3c4 × 8`) au second tour. `expo_ligneProgramme` est une ligne à deux pentes autour d'un point (Ev0, Tv0) : pour P sans flash, Ev0 = 12 IL, pentes ½ et ½, et Tv0 = 1/125 (moins de 57 mm), 1/250 (57 à 138 mm) ou 1/500 (au-delà). Elle contient aussi des variantes par mode scène, utilisées quand le bit 0 de `0x3E1E0` vaut 0. Vérifié.
- Le bit 0 de `0x3E1E0` est posé à `0x11` quand la molette passe de P/S/A/M à une scène (`molette_lire`, a-tout.c l.7836–7840), effacé ailleurs. Hypothèse : c'est l'« ISO Auto des scènes » du menu ISO. Il force ISO 200 comme base (`FUN_000c4064`) et coupe l'ISO auto du menu Réglages perso (`d0bc &= ~2`).
- S (`0xC617E`), A (`0xC61BC`) et M (`0xC61FA`) ne font que borner la valeur choisie. Vérifié.

### Les lignes d'usine, sans flash (vérifié pour la transcription, calcul par `lignes.py`)

Avec le 50 mm f/1,8G (ISO de base, sans l'ISO auto, IL à l'ISO courant) :

| Ligne | IL 4 | IL 6 | IL 8 | IL 10 | IL 12 | IL 14 | IL 16 |
|---|---|---|---|---|---|---|---|
| P (< 57 mm) | 1/5 f/1,8 | 1/16 f/2 | 1/30 f/2,8 | 1/60 f/4 | 1/125 f/5,6 | 1/250 f/8 | 1/500 f/11 |
| P (> 138 mm, avec f/1,8 théorique) | 1/5 f/1,8 | 1/20 f/1,8 | 1/80 f/1,8 | 1/250 f/2 | 1/500 f/2,8 | 1/1000 f/4 | 1/2000 f/5,6 |
| Auto (< 57 mm) | 1/4 f/2 | 1/8 f/2,8 | 1/23 f/3,4 | 1/45 f/4,8 | 1/125 f/5,6 | 1/250 f/8 | 1/500 f/11 |
| Portrait | 1/2 f/2,8 | 1/8 f/2,8 | 1/30 f/2,8 | 1/125 f/2,8 | 1/500 f/2,8 | 1/2000 f/2,8 | 1/4000 f/4 |
| Paysage | 1 s f/4,8 | 1/2 f/5,6 | 1/6 f/6,7 | 1/19 f/7,3 | 1/54 f/8,7 | 1/160 f/10 | 1/500 f/11 |
| Enfant | 1/2 f/2,8 | 1/8 f/2,8 | 1/30 f/2,8 | 1/60 f/4 | 1/125 f/5,6 | 1/360 f/6,7 | 1/720 f/9,5 |
| Sport | 1/4 f/2 | 1/16 f/2 | 1/60 f/2 | 1/250 f/2 | 1/400 f/3,2 | 1/1000 f/4 | 1/1600 f/6,3 |
| Gros plan (< 57 mm) | 1/5 f/1,8 | 1/16 f/2 | 1/30 f/2,8 | 1/30 f/5,6 | 1/60 f/8 | 1/250 f/8 | 1/1000 f/8 |

Ce qu'on en tire (déduit) :
- **Portrait** du D40 est une priorité ouverture **figée à f/2,8** (plancher `ccb9 = 0x12`) : sur un f/1,8, il n'ouvre jamais en grand. Sur le 18-55, il reste à pleine ouverture (f/3,5).
- **Sport** est déjà une ligne « vitesse » à la Pentax : pleine ouverture jusqu'à 1/250, puis une pente d'un tiers. Mais son plancher (f/2) bloque, lui aussi, l'ouverture d'un f/1,8.
- **Gros plan** a des paliers de vitesse constante (1/30, 1/60) où seule l'ouverture bouge : un embryon de ligne « profondeur ».
- Aucune ligne ne vise une ouverture choisie selon l'objectif.

### Ce qu'il faut écrire pour des lignes perso

Deux voies.

**Voie 1 : retoucher les constantes d'une scène existante** (patch de code « à taille égale »). On réécrit les immédiats `Tv0`, `Ev0`, la pente et `ccb9` d'une fonction de courbe. Exemples :
- **Sport → « Sujet rapide »** : `ccb9` de `0x0C` à 0 (pleine ouverture d'un f/1,8), et premier seuil de `0x1E0` à `0x240` pour rester ouvert jusqu'à 1/1000 environ.
- **Portrait → « Portrait 1/125 »** : `ccb9` de `0x12` à 0, pour une vraie grande ouverture. Le 1/125 mini se règle dans `progScene_portrait` (`0xC5A2E`), qui fait monter l'ISO aujourd'hui sous 1/500 (seuils `0xD8`/`0xC1` en Tv/2, 1/24 d'IL) : on les ramène à `0xA8` (1/125).
- **Gros plan → « Profondeur »** : un plancher `ccb9` à `0x24` (f/8), le palier Tv repris.

Limites de cette voie :
- Ce sont des modes scène, avec leurs contraintes : rendu image imposé par le B (`modesScene_reglages`, CARTE §7), flash auto, zone AF imposée, ISO auto de scène plafonné à 800, correction d'exposition non proposée en scène (manuel du D40, à revérifier).
- Il faut vérifier dans le listing assembleur que chaque immédiat tient dans le même encodage (`LDI:8`, `LDI:20` ou `LDI:32` du FR), sinon le patch change de taille. Point ouvert.

**Voie 2 : une ligne générique pilotée par des données** (patch de code, une fois). Une fonction écrite dans la place libre du A (§6) remplace l'appel à `expo_ligneProgramme` dans `0xC60E2` quand une ligne perso est active. Elle lit un descripteur de 8 à 12 octets par ligne : un ou deux segments (Tv0, Ev0, pente), une **règle d'ouverture cible** (pleine ouverture, valeur fixe, table MTF par objectif), un plancher et un plafond d'ouverture, et une **vitesse mini pour l'ISO auto** (fixe, ou k/focale). Ensuite, ajouter une ligne ne touche plus que des données. Les quatre lignes voulues :

| Ligne | Règle | En chiffres D40 (1/48 IL) |
|---|---|---|
| Sujet rapide | pleine ouverture ; Tv = Ev − Av max ; ferme seulement en butée 1/4000 ; ISO auto avec vitesse mini 1/500 | cible Av = 0, laissée à la butée de l'objectif par `FUN_000c4680` ; Tv mini ISO auto = `0x1B0` |
| Portrait 1/125 | pleine ouverture (option plafond f/2 contre la mollesse d'un f/1,8) ; ISO qui monte sous 1/125 ; ferme au-delà de 1/4000 | Av cible = Av max ; Tv mini = `0x150` |
| Profondeur | f/11 visé ; si Tv < 1/focale, ISO qui monte ; à l'ISO maxi, rouvre jusqu'à f/8 avant de ralentir | Av cible = `0x14C` (f/11), repli `0x120` (f/8) |
| Piqué max (MTF) | Av = table[objectif][focale] ; repli : Av max + 2 IL, borné à f/5,6–f/8 ; ISO auto à 1/focale | 2 octets par point de focale |

Pour « Sujet rapide » et « Portrait », on peut viser plus simplement Av = 0 (f/1) : `FUN_000c4680` ramène l'ouverture à la butée de l'objectif, puis Tv = Ev − Av max. C'est ce qui donne « pleine ouverture quel que soit l'objectif » sans connaître l'objectif. Déduit du code de la chaîne commune.

**Vitesse mini « AUTO » = 1/focale, en une ligne de code** (déduit) : Tv(1/f) = 48·log2(f). Avec f = 5·2^(x/24) (codage Nikon de `d0f0`) et la focale équivalente 24×36 (×1,5), on obtient **Tv = 2·`d0f0` + 140** (+48 par cran de sécurité). Contrôle : 50 mm donne `d0f0` = 80, Tv = 300, soit 1/76 s ≈ 1/(50 × 1,5).

---

## 3. Piqué max sur D40

### Ce que l'objectif transmet

Les champs Nikon des LensData (ExifTool `Nikon.pm`, `LensData01`, vérifié dans la source) : `LensIDNumber`, `LensFStops`, focales mini et maxi, ouverture maxi à chaque bout, version du microcontrôleur (`MCUVersion`), et, pour les objectifs récents, focale actuelle, distance de mise au point, ouverture maxi effective, pupille de sortie. L'identifiant complet d'ExifTool (`LensID`) est formé de 8 octets : `LensIDNumber`, `LensFStops`, focale mini, focale maxi, ouverture maxi aux deux bouts, `MCUVersion`, `LensType` (note de `%nikonLensIDs`).

Côté A, le bloc de l'objectif arrive en `0x3D122`–`0x3D14B` et la focale, l'ouverture maxi et l'étendue en sont tirées (§2). Probable. **Quel octet du bloc est le `LensIDNumber` n'est pas encore lu** : point ouvert. Le B le connaît forcément, puisqu'il l'écrit dans l'EXIF. Les blocs A → B de 132 et 196 octets (commandes `0x1C`, `0x24`, CARTE §10 bis) sont les candidats. Hypothèse.

**Aucune donnée MTF ne transite.** Une table embarquée est indispensable.

### Les objectifs

Relevé sur l'EXIF des photos de l'auteur : surtout le 18-55 mm, puis le 55-200 mm et le 50 mm f/1,8 (`LensIDNumber` 148, 137, 176).

### Ouverture de meilleur piqué (mesures Photozone ; choix déduit)

| Objectif | Mesures (centre / bord, LW/PH) | Ouverture retenue |
|---|---|---|
| 18-55 II, boîtier D7000 | 18 mm : f/5,6 2730/2213, **f/8 2710/2427** ; 24 mm : f/8 2695/2405 ; 35 mm : f/5,6 2631/2229, f/8 2573/2264 ; 55 mm : **f/8 2585/2199** | f/8 partout (f/5,6 acceptable à 35 mm) |
| 55-200 sans VR | 55 mm : f/8 2122/1975 ; 100 mm : f/5,6 2003/1771, f/8 1981/1795 ; 200 mm : f/5,6 1945/1770, f/8 1945/1782 | f/8 partout |
| 50 f/1,8G, boîtier D3x, plein format | **f/5,6** : 3958/3532 (le meilleur centre et le meilleur bord) | f/5,6 |
| Tamron 35 f/1,8 VC, boîtier D7200 | f/4 : 3645/2921 ; **f/5,6 : 3596/2930** | f/5,6 (f/4 pour le centre seul) |

Sources :
- 18-55 II : https://photozone.de/nikon--nikkor-aps-c-lens-tests/758-nikkor18553556ii?start=1 (graphe `nikkor_1855_3556II_d7000/mtf.png`) ;
- 55-200 : https://photozone.de/nikon--nikkor-aps-c-lens-tests/245-nikkor-af-s-55-200mm-f4-56-g-ed-dx-review--test-report?start=1 ;
- 50 mm : https://photozone.de/nikon_ff/631-nikkorafs5018ff?start=1 ;
- Tamron : https://photozone.de/nikon--nikkor-aps-c-lens-tests/1024-tamron35f18vcdx?start=1.

Photozone avertit que ses chiffres ne se comparent pas d'un boîtier à l'autre. Seul compte ici le classement des ouvertures pour un même objectif.

**Le capteur du D40 décale l'optimum vers f/8** (déduit). Ses photosites font 7,9 µm (23,7 mm / 3 008 px). La tache d'Airy (2,44·λ·N, λ = 0,55 µm) fait 10,7 µm à f/8 et 14,8 µm à f/11 : la diffraction gêne plus tard que sur les boîtiers de test, à 16–36 Mpx. Les ouvertures retenues sont donc des bornes basses. f/8 est sûr partout, f/11 commence à adoucir (environ 2 photosites).

**Réaliste ?** Oui, sans réserve sur la taille : 4 objectifs × 1 à 4 points de focale × 2 octets, moins de 50 octets. La table se lit par `LensIDNumber`, avec un repli pour un objectif inconnu : pleine ouverture + 2 IL, bornée à f/5,6–f/8. Ça reproduit le comportement Pentax sans donnée constructeur. On n'a pas besoin de DxOMark : Photozone couvre les quatre objectifs.

---

## 4. ISO auto

### Où il vit (vérifié)

- **B** : les menus, et un seul octet de réglage, **`0x83CE974F`** :
  - bit 7 : ISO auto actif ;
  - bits 4-6 : ISO maxi (1 = 400, 2 = 800, 3 = 1600 dans le menu) ;
  - bits 0-3 : indice de vitesse mini (0 = 1/125 à 7 = 1 s).
  
  Lu par `ecran049_entree` (`0x1363DA`), `ecran062_entree` (`0x136548`) et `ecran063_entree` (`0x1366BE`). Les valeurs hors plage sont remises d'office par `FUN_00134118` (`0x134118`, à l'entrée du menu Réglages perso : ISO maxi > 3 → 3, vitesse > 7 → 2) et par le `default` de `ecran063_entree` (→ 2, 1/30).
- **Transport** : l'octet fait partie du bloc de 14 octets de la **commande 0x05** (B → A, `0x83CE974D`). Preuve : le gestionnaire PTP `FUN_0039c966` (`0x39C966`) réécrit les bits 0-3 puis appelle `liaisonA_envoyerCommande(5)` (d40-tout.c l.190284). Vérifié.
- **A** : la copie de l'octet est **`0x3D25B`** (même codage : `& 0xF` → `isoAuto_vitessesMini`, `(& 0x7F) >> 4` → table des ISO maxi, bit 7 testé avant d'activer, a-tout.c l.8040). Probable : la copie elle-même n'est pas lue, l'identité des codages l'est. Le calcul est entièrement dans le A :
  - `FUN_000c4064` : plafonne l'ISO de départ à l'ISO maxi ;
  - `expo_limiterVitesse` : vitesse mini, sauf en S et M ;
  - **`FUN_000c471c` (`0xC471C`), la montée en ISO** ;
  - `progScene_*` : l'ISO auto des scènes.
- **Correction pour `CARTE.md` §10** : la table des ISO maxi est à **`0xFA86C`** (et non `0xFA868`) : 5 valeurs, 200, 400, 800, 1600, 3200, lues par `FUN_000c4064` et `FUN_000c471c`. Vérifié. Le menu n'en propose que trois (400, 800, 1600).

### Ce qu'il fait (vérifié, sauf mention)

1. **ISO de base = l'ISO réglé par l'utilisateur** (`e1ee = c3cb`, a-tout.c l.8048). C'est le « DEFAULT SENSITIVITY » de Fuji, déjà là. L'ISO auto est coupé en scène, et si l'ISO réglé est HI 1 (`c3cb ≥ 0x37`).
2. Le programme (ou S, A, M) calcule Tv et Av à cet ISO. `expo_limiterVitesse` relève Tv à la vitesse mini en P et A.
3. `FUN_000c46de` calcule le manque d'exposition, `(Ev − Tv − Av)/2`. Ensuite, `FUN_000c471c` :
   - monte l'ISO du manque (en 1/6 d'IL), borné entre ISO 200 et min(ISO maxi, **`0x36` = 1600, plafond codé en dur**) ;
   - si le plafond est atteint, reporte le reste sur la vitesse (bornée à 30 s et 1/4000) : la vitesse descend alors sous la mini.
   
   Le paramètre de `FUN_000c471c` est perdu par le décompilateur (registre). Que ce soit le manque d'exposition est probable.
4. Inactif sans objectif à puce (`d0e6 = 0`) et quand le flash part. Probable.

L'ordre est donc déjà le bon, celui de Fuji : ouvrir, puis descendre jusqu'à la vitesse mini, puis monter en ISO, puis passer sous la vitesse mini. Fuji le décrit ainsi pour la X-Pro2 : https://fujifilm-dsc.com/en-int/manual/x-pro2/menu_shooting/iso_auto_setting/. On y trouve DEFAULT, MAX et MIN SHUTTER SPEED de 1/500 à 1/4 s ou AUTO (≈ 1/focale), et trois jeux AUTO1–3.

### Ce qu'il faut réécrire

| Changement | Où | Nature |
|---|---|---|
| Vitesses mini plus rapides (1/500, 1/250, 1/125, 1/60, 1/30, 1/15…) | `0xFA876` (A) + libellés D323–D330 (B, CARTE §10) | données |
| ISO maxi 800 / 1600 / 3200 au lieu de 400 / 800 / 1600 | valeurs d'indice 1–3 de `0xFA86C` (A) + libellés (B) | données |
| Lever le plafond 1600 | immédiat `0x36` dans `FUN_000c471c` (A) | constante de code |
| Vitesse mini AUTO = 1/focale (×1, ×2) | `expo_limiterVitesse` (A) : indices 8–15 → Tv = 2·`d0f0` + 140 (+48·k) | code (≈ 10 instructions + saut) |
| Accepter les indices 8–15 | `FUN_00134118` (limite 7) et `ecran063_entree` (B) | constantes, puis écran |
| Jeux façon Fuji AUTO1–3 | voir §5 : un « préréglage » = ligne + vitesse mini, dans le même octet | code A et B |

L'ISO mini des jeux Fuji existe déjà : c'est l'ISO réglé. Inutile d'y toucher (efficience).

---

## 5. Menus : arborescence proposée

### Idée centrale : un seul choix, « Programme », qui porte la ligne et l'ISO auto

Le quartet bas de `0x83CE974F` (vitesse mini) a **8 valeurs libres (8–15)** et voyage déjà jusqu'au A par la commande 0x05. Proposition : 0–7 gardent leur sens (vitesses fixes, retouchées) ; **8–15 = préréglages « Programme »**, chacun = une ligne (§2, voie 2) + sa règle de vitesse mini. Pas de nouveau transport entre les processeurs. La ligne et l'ISO auto se choisissent d'un geste, comme les jeux AUTO1–3 de Fuji. Déduit ; reste à vérifier qu'aucune autre fonction du B n'interprète ce quartet, ce que le relevé des 32 usages de `974F` suggère.

```
PRISE DE VUE
  Rendu couleur ............ (autre chantier : ex-Optimiser l'image)
  Programme ................ Standard (Nikon) · Sujet rapide · Portrait 1/125 · Profondeur · Piqué max
  ISO ...................... 200 … HI 1 (= ISO de base de l'ISO auto, inchangé)
  Qualité · Taille · Balance des blancs · Réduction du bruit (inchangés)
RÉGLAGES PERSO
  ISO auto ................. Non · Oui
     ISO maxi .............. 800 · 1600 · 3200
     Vitesse mini .......... 1/500 · 1/250 · 1/125 · 1/60 · 1/30 · AUTO 1/f · AUTO 1/2f · 1/15
  (le reste inchangé ; signal sonore libéré)
CONFIGURATION › Réglages perso/Config › Mon menu   (réglage officiel du D40 : n'afficher que ce qui sert)
```

### Places à recycler et coût

| Besoin | Place proposée | Coût |
|---|---|---|
| Entrée « Programme » (5 choix) | **le menu Retouche** (écran 144, 6 entrées, inutilisé) devient la liste des programmes ; l'entrée de la racine Prise de vue qui y mène prend la place de « Réduction du bruit » ou passe par « Mon menu ». Autre choix : le sous-menu « Vitesse mini » (8 entrées, écran 63) relibellé, si l'on accepte que Programme et vitesse mini partagent la liste | données (libellés, icônes, sous-menu, CARTE §5 bis) **+ code B** : une fonction d'entrée (surbrillance depuis `974F & 0xF`) et une d'action (écrire `974F`, `liaisonA_envoyerCommande(5)`), sur le modèle de `FUN_0039c966`, dans les 164 Ko libres du B |
| Libellés plus longs (« Portrait 1/125 », « Piqué max ») | table D de la langue reconstruite dans la place libre (CARTE §5) | données |
| ISO maxi et vitesses mini relibellées | menus existants, écrans 62 et 63 | données (libellés) + 2 constantes de `FUN_00134118` |
| Simplifier l'affichage | « Mon menu » du D40 (entrées « Select items », écrans 72 et 73) | **rien, réglage officiel** |
| Choix à la molette (sans menu) | `molette_versMode` (`0xFAB38`, données) : envoyer une position de scène peu utilisée vers un des codes de mode libres **4 à 7**. Le A les traite comme P/S/A/M (bit 3 nul : correction d'exposition, ISO auto du menu, rendu de l'utilisateur), et `expo_programmeMode` les envoie vers la ligne P | données + un `switch` dans la ligne générique (A) ; **inconnu : ce que le B fait d'un code 4 à 7** (icône, EXIF, conversion « code A − 4 » des scènes). Hypothèse, à tester en premier |

---

## 6. Architecture proposée

- **A (exposition)** :
  - une fonction `ligne_perso(Ev)` dans la place libre ;
  - des descripteurs de lignes (données) ;
  - une table MTF par `LensIDNumber` (données) ;
  - l'extension de `expo_limiterVitesse` (AUTO 1/f) ;
  - deux points d'accroche : dans `0xC60E2` (P), si `(d25b & 0xF) ≥ 8`, appeler `ligne_perso` au lieu de `expo_ligneProgramme` ; dans `expo_limiterVitesse`, la vitesse mini du préréglage.
  
  Place libre du A, relevée dans le fichier (runs de `0xFF`) : `0xF390C`–`0xF7FFF` (18 Ko), `0xF2256`–`0xF2FFF` (3,4 Ko), `0xFE0DC`–`0xFEAFF` (2,6 Ko). **Corrigé en octobre 2026** (`recherche/etude-a/mise-a-jour-et-recuperation.md` §5) : `0xF3000`–`0xF3AFF` est le flasheur et `0xF4000`–`0xF7FFF` n'est jamais écrite ; restent `0xF2256`–`0xF2FFF`, `0xF3B00`–`0xF3FFF` et `0xFE0DC`–`0xFEAFF`. Que la mise à jour du A écrive bien ces zones et qu'elles ne servent pas en marche : hypothèse, dossier de l'autre agent (`reecriture-firmware-materiel.md`).
- **B (interface)** : les deux écrans « Programme », les libellés, le relèvement des limites de validation, l'affichage du programme actif sur l'écran d'infos (plus tard).
- **Lien** : l'octet `974F`/`d25b`, déjà transmis. Rien à ajouter à la liaison.

---

## 7. Étapes, de la moins risquée à la plus risquée

1. **Aucun flashage** : « Mon menu » pour alléger l'interface tout de suite. Et lire les octets `974D`–`975A` par PTP (gphoto2, à demander avant installation) pour confirmer leur codage.
2. **Simulateur hors boîtier** : garder `lignes.py` (dossier de travail) comme banc. Y ajouter les lignes perso et l'ISO auto, et sortir des tableaux IL → vitesse, ouverture, ISO pour valider les choix de Thomas avant toute écriture.
3. **Données A seules** : nouvelles vitesses mini (`0xFA876`), nouvelles valeurs d'ISO maxi (`0xFA86C`), libellés B correspondants. Premier flashage du A : son risque propre est traité par l'autre agent.
4. **Constantes de code A à taille égale** : plafond `0x36` → `0x3C` ; « Sujet rapide » et « Portrait 1/125 » obtenus en retouchant Sport et Portrait (voie 1). Vérifier l'encodage de chaque `LDI` dans le listing (`D40Listing.java` sur le A).
5. **Code A** : ligne générique, AUTO 1/f, préréglages 8–15. Test possible **sans toucher aux menus du B**, en écrivant la valeur par PTP (`FUN_0039c966`) si son contrôle de plage l'accepte (point ouvert). Ne pas ouvrir le menu Réglages perso pendant ce test : `FUN_00134118` remettrait 2.
6. **Table MTF** : localiser le `LensIDNumber` dans le bloc objectif du A, puis brancher la règle « piqué max ».
7. **Code B** : écrans « Programme », libellés reconstruits, limites de `FUN_00134118`. Molette vers les codes 4–7 en option, après un essai qui montre comment le B réagit.

## 8. Points ouverts

- Rôle exact du bit 0 de `0x3E1E0` (ISO Auto des scènes ?) et argument perdu de `FUN_000c471c` : à lire en assembleur.
- Position du `LensIDNumber` dans le bloc `0x3D122`–`0x3D14B` du A ; correspondance exacte du bloc de la commande 0x05 (`974D`… ↔ `d259`…).
- Encodage des immédiats à patcher (`LDI:8`, `:20` ou `:32`) dans les fonctions de courbe.
- Comportement du B devant un code de mode 4 à 7, et devant une vitesse mini 8–15 (affichage, EXIF, PTP).
- Les zones `0xFF` du A sont-elles écrites par la mise à jour et libres en marche ?
- Correction d'exposition en mode scène sur D40 : à revérifier dans le manuel Nikon (conditionne la voie 1).
- Les ouvertures MTF viennent de boîtiers de 16 à 36 Mpx : à recaler sur le D40 par une série de photos à f/4, f/5,6, f/8 et f/11, sur mire ou façade, avec chaque objectif.
- Symboles à corriger dans `desassemblage/symboles-A.tsv` (non modifié ici, consigne) : `progScene_*` → `isoAutoScene_*` ; nommer `0xC48E0`… `0xC5674` `ligneScene_*`, `0xC471C` `isoAuto_monter`, `0xC4680` `expo_bornerOuverture`, `0xC4BB4` `expo_bornerVitesseScene`, `0xFA86C` `isoAuto_sensibilitesMax` (adresse corrigée, vérifié).

---

## 9. Réalisé en octobre 2026 (émulateur, non flashé)

Les lignes de Thomas (Sujet rapide, Portrait, Street, Profondeur, Piqué max) tournent dans l'émulateur du A, par la voie 2 réduite à l'essentiel : pas de descripteurs ni de table MTF, une fonction `ligne_perso` qui vise une ouverture par Programme et laisse la fonction de P, ses butées et l'ISO auto de Nikon faire le reste. Détail, contrôles, limites et paliers de flash : README, « Programme réel, mis au point dans l'émulateur ». Points de ce document tranchés :
- correspondance du bloc 0x05 : `974D` ↔ `0x3D259`, octet par octet (vérifié, `a-liaison-05`) ;
- comportement du B devant une vitesse mini 8 à 15 : sans objet, le B ne les voit jamais (seule la copie envoyée les porte ; l'écho du A est remis à la valeur du B) ;
- zones `0xFF` du A : voir la correction ci-dessus ; le code est en `0xF2400`, libre en 1.11 et 1.12 ;
- « Piqué max » sans MTF : pleine ouverture + 2 IL, bornée à f/5,6–f/8, faute d'identifiant d'objectif localisé.
Le Programme n'agit qu'en P : le B ne l'envoie que si le mode du bloc 0x05 vaut P (README). Restent ouverts : le `LensIDNumber` dans le bloc objectif du A et la réouverture de Profondeur à f/8 au plafond d'ISO.
