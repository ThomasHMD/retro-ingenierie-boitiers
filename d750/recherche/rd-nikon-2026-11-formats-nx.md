# R&D Nikon de novembre 2026 : NP2, NP3, vignetage et généralité de NX Studio

Suite de `veille-picture-control-2026-11.md` §4. Code : `outils/picture_control.py` (NP2 écrit, NP3 lu), `outils/nx_rendu.py` (vignetage, annexe, lots). Rien n'a été chargé dans un boîtier. Environ 390 rendus SaveProcess en tout. Statuts : **mesuré** = chiffre issu d'un rendu ; **hypothèse** = non établi.

## 1. NP2 contre NCP dans NX Studio

**Aucun fichier .NP2 réel** n'existe sur ce Mac (cherché dans le dépôt, `references/nikonpc/brut/` qui ne contient que des décodages texte de NCP, et `/Library/Application Support/Nikon/` qui ne contient que deux `.NOP` de 2008). Le format NP2 écrit ici est donc reconstruit : cartes de la lecture existante + disposition des cartes du NP3 de gerard662 + essais dans NX. **Il n'a jamais été vérifié par Picture Control Utility 2 ni par le boîtier** (hypothèse). Ce qui est mesuré : NX Studio l'accepte et l'interprète comme le NEF.

### Format écrit (`ecrire_np2`)
Cartes type(4) longueur(4) données, fin = type 0 : 0x100 version `0200`, 0x200 nom ASCII 20 octets (l'ancien code lisait de l'UTF-16 : corrigé, le NP3 de gerard662 est en ASCII), 0x300 base (2 octets, mêmes identifiants que le NCP, Uniforme compris), 0x400 `0000`, 0x500 `FF01`, 0x600 accentuation, 0x700 clarté, 0x800 contraste, 0x900 luminosité, 0xA00 saturation, 0xB00 teinte, 0xC00 filtre, 0xD00 virage, 0xE00 force, puis 0x2 courbe (578 octets identiques au NCP). Carte réglage = (valeur, pas 4) avec valeur = 0x80 + 4 × points. Filtre et virage : (0x80 + indice, 0).

### Essais dans NX (mesuré)
- Version `0100` avec cartes NP2 : ignoré (rendu = NEF tel quel). Version `0200` ou `0210` : lu. Variante avec les cartes 0xF00 à 0x1D00 du NP3 en plus : rejetée en silence (retombe sur un Standard à zéro). Piège : un NP2 mal formé ressemble à un rendu normal.
- **Le réglage de l'annexe qui compte est `SavedPicConProcess`** (version du traitement Picture Control). Avec 0 (valeur de gerard662), NCP et NP2 donnent exactement le même rendu et s'écartent du « tel quel » de 1,0 à 1,8 code (ΔE médian 0,8 à 1,05). Avec 1 (2 donne pareil), **le NP2 rend bit à bit le NEF** : écart 0,000 en ΔE et en codes. `SelectedPictureControlVersion2`, `SelectedPictureControl` et `PictureControl` (0, 1, 2, 4, 8, 17, 32) : sans effet. Le NEF porte d'ailleurs `PictureControlVersion 0200`.
- Témoins négatifs (NP2, process 1, vue 01) : base Neutre +2,6 ΔE, saturation −3 +4,1, contraste +3 +3,3, luminosité +1,5 +6,2, clarté +5 +2,0 : les cartes sont bien lues, ce n'est pas un repli sur le NEF. Accentuation 9 : effet minime (0,4 code), sa carte est lue (le bruit haute fréquence monte) sans changer la couleur.
- NP2 process 1 contre NEF tel quel, **0,000 sur 12 vues** : 01, 02, 04, 05, 07 (Uniforme), 08 (sat −3), 11 (teinte +3), 33 (contraste +3), 35 (mono contraste +3), 36 (courbe identité), 42 (CHROME_V0, courbe + accentuation 3, bloc `blocs/42.bin`), 47 (TRI-X, courbe mono).
- NCP process 1 contre NEF : exact sur Neutre (02) et Portrait (05), **0,34 à 0,45 ΔE d'écart sur Standard et Monochrome** (01, 36, 42, 04, 35, 47). Cohérent avec l'hypothèse « le NCP porte les bases Picture Control version 1 » : les bases Standard et Monochrome diffèrent en version 2 (hypothèse ; le mécanisme n'est pas vu).

Médiane ΔE2000 contre le JPEG du boîtier (`comparer`, vignetage 300, gain radial retiré) :

| vue | NEF tel quel = NP2 (process 1) | NCP process 0 | NCP process 1 |
|---|---|---|---|
| 01 Standard | 0,76 | 0,84 | 0,96 |
| 02 Neutre | 0,60 | 1,04 | 0,60 |
| 05 Portrait | 0,45 | 0,94 | 0,45 |
| 36 Standard courbe identité | 0,86 | 0,95 | 1,11 |
| 42 CHROME_V0 | 0,71 | 1,15 | 0,92 |
| 04, 35, 47 (mono) | 0,92 / 0,95 / 0,96 | non mesuré | 1,12 / 1,12 / 1,14 |

**Conclusion** : pour reproduire le boîtier dans NX, imposer un **NP2 avec `SavedPicConProcess=1`**. `nx_rendu.rendre` le fait seul quand le Picture Control passé est un NP2 ; NCP et NP3 gardent l'ancien comportement (`pc_options={'SavedPicConProcess': 1}` pour essayer). Les 1 à 1,7 code observés au début ne venaient pas du format mais de ce réglage de l'annexe.

Hypothèses restantes : « auto » (0x00) rend comme dans un NCP et donne des écarts énormes dans SaveProcess (ΔE 12 à 19 : pas d'analyse de scène) ; le marqueur « courbe » d'une carte (0x01 ou 0xFF ou 0 explicite) est indifférent quand la courbe est présente (mesuré, 0,000) ; le virage mono est écrit comme le NCP et rend la même teinte à 0,5 code près (mesuré sépia force 4) mais les cartes 0xC00 à 0xE00 d'un vrai NP2 peuvent différer.

## 2. Lecture NP3

`picture_control.py lire fichier.NP3` : saturation (0x1E00), Color Blender (0x1F00 : 8 teintes × teinte, chroma, luminosité + 4 octets de fin), Color Grading (0x2000 : 3 zones × teinte en degrés, chroma, luminosité ; fondu, équilibre), courbe (0x2, mêmes 257 valeurs que le NCP), cartes communes. Disposition d'après `np3lib.py` de gerard662 (MIT, attribution dans le code). Testé sur ses deux modèles, copiés dans `references/gerard662/` (avec LISEZMOI et sa licence) : le premier se lit avec saturation −3, rouge (−6, +9, +17), fondu 78, teinte des hautes lumières 116° ; le second tombe sur des zéros et fondu 50, comme prévu. Les valeurs sont celles du fichier (v − 0x80), pas l'affichage du boîtier (hypothèse : unités ≠ affichage). Octets non compris : cartes 0x400, 0x500, 0xF00 à 0x1D00, 4 octets après le Color Blender, 6 octets du Color Grading (gardés en hexadécimal).

## 3. Vignetage dans NX

- Le filtre s'appelle `nikon::Vignette`. Son paramètre est **explicite** : `<integer name="intensity">N</integer>` dans `<parameters>`. La forme implicite `<intensity>N</intensity>` (celle que suggère l'ordre des chaînes de `libRome2`) est lue sans aucun effet, de même que `<double name=…>` (10 essais, tous à écart nul : au début mon harnais relisait en plus un fichier de sortie périmé, corrigé). Sans filtre, le moteur applique 50 (mesuré : rendu identique à `intensity=50`).
- Effet monotone : coin/centre contre le JPEG à f/5,6 : −100 → 0,48 ; 0 → 0,60 ; 50 → 0,66 ; 100 → 0,73 ; 1000 → 2,10. Le contrôle ne passe pas par `.hyd` (aucune clé dans SaveProcess).
- **Le bon réglage dépend de l'ouverture** (AF-S 28 mm f/1,8G, contrôle « Normal », ISO 200) :

| condition | défaut (50) : coin NX / JPEG | meilleur réglage | profil radial NX / JPEG après réglage |
|---|---|---|---|
| f/1,8 (séance portrait, 01) | 1,41 (NX sur-corrige) | **10** (rms 0,010) | plat à ±1 % : 1,00 à 0,99 |
| f/5,6 (bibliothèque, 01) | 0,67 | **≈ 300** (rms 0,028) | creux de 4 % à mi-rayon, coin 1,02 |
| f/9 (extérieur, 03) | 0,86 | **300** (rms 0,026) | creux de 4 %, coin 1,01 |
| objectif manuel sans CPU 135 mm f/4, contrôle « Off » | 1,00 | **ne rien passer** | plat (1,000 à 1,005) |

  Avec le réglage adapté, l'écart coins / centre disparaît (à ±2 % près en coin ; à f/5,6 et f/9 il reste un creux de 4 % à mi-rayon : la forme du correctif de NX n'est pas celle du boîtier, hypothèse). Le gain radial de `comparer` s'ajuste encore (0,15 à 0,25 en r²) à f/5,6 : « sans gain radial » n'est donc atteint qu'à f/1,8 et sur l'objectif manuel ; à f/5,6 le ΔE sans gain passe de 1,45 (réglage 200) à 0,91 (300).
- Option ajoutée : `nx_rendu.rendre(..., vignetage=N)` (défaut `None` = comportement d'avant), `--vignetage N` en ligne de commande. Le réglage « juste » par ouverture/objectif n'est pas calculé : à choisir (table ci-dessus). Pas de loi d'ouverture trouvée avec trois points ; ISO élevé non résolu (voir §4).

## 4. Généralité sur les lots D750

NX tel quel (réglages du NEF) contre JPEG du boîtier, ΔE2000 médian par blocs de 32 px, gain radial retiré. Une médiane par vue, puis médiane et pire vue du lot. Données par vue (avec EXIF, profil radial, gain) : `recherche/rd-nikon-2026-11-lots-nx/`.

| lot | vues | objectif, ouverture, ISO | vignetage passé | médiane des vues | pire vue |
|---|---|---|---|---|---|
| séance bibliothèque | 47 (toutes) | 28 mm f/1,8G, f/5,6, 200 | 300 | **0,72** | 1,01 (09 STANDARD SAT+3) |
| séance complément | 14 (toutes) | idem | 300 | **0,86** | 0,93 |
| extérieur octobre | 9 (toutes) | 28 mm, f/8 à f/10, 200 | 300 | **0,82** | 1,16 (PORTRA 400) |
| séance portrait | 12 sur 24 | 28 mm, f/1,8, 200 | 10 | **0,96** | 1,38 (KODACHROME V0) |
| séance scène intérieur | 12 sur 47 | 28 mm, f/1,8, ISO 1250 à 2000 | 10 | **1,07** | 1,63 (09 STANDARD SAT+3) |
| séance pédalier | 12 sur 47 | 135 mm sans CPU, f/4, 200, contrôle Off | défaut | **0,35** | 0,71 (SATURE SAT+3) |
| test v1 (recettes v1) | 5 sur 10 | idem pédalier | défaut | **0,42** | 0,75 (POSITIVE V1) |

(Échantillons : une vue sur 2 ou 4 pour tenir le budget de rendus. Les passes complètes à 300 sur portrait, scène intérieur, pédalier et test v1 sont aussi dans `vignetage300-complet/` mais à 300 le vignetage est faux pour f/1,8 et l'objectif manuel : leurs ΔE bruts, 2,2 à 10 « sans gain », n'ont pas de sens ; leurs ΔE avec gain radial valent 0,95 / 2,22 / 1,24 / 1,55.)

Lecture :
- **Le rendu de NX colle au JPEG à ≈ 0,4 à 1,1 ΔE sur tous les lots**, mêmes ordres de grandeur que la bibliothèque (0,5 à 1,6 notée au départ). Pas de dépendance nette à la scène ou à l'objectif en dehors du vignetage.
- Écart qui monte : ISO 1250 à 2000 (scène intérieur, médiane 1,07, pire 1,63) contre 0,96 à f/1,8 ISO 200. Le profil radial à ISO élevé n'est plus plat avec le réglage 10 (coin 0,83 contre 0,99 à ISO 200), donc soit le correctif du boîtier dépend de l'ISO ou de l'exposition, soit le bruit élevé biaise la mesure (hypothèse non tranchée).
- Meilleurs lots : pédalier et test v1 (objectif sans CPU, pas de vignetage appliqué, 0,35 et 0,42). Cela suggère que le gros de l'écart restant aux autres lots vient de la correction du vignetage et de ses résidus, pas du Picture Control (hypothèse).
- Limites : un seul boîtier, deux objectifs, ISO 200 dans la plupart des lots, scènes de studio.

## 5. Self-tests
- `python3 outils/picture_control.py --self-test` : OK (ajout : NP2 aller-retour, mono, courbe identique octet à octet à celle du NCP, bornes, NP3 de gerard662 si présents).
- `python3 outils/nx_rendu.py --self-test` : OK (annexe `.nksc` et `.hyd` sans NX, choix du process pour NP2, rendu de contrôle : le vignetage 300 éclaircit le coin de 0,31 à 0,49 du centre à 1 500 px).

## 6. API (inchangée pour l'autre agent)
`nx_rendu.rendre(nef, sortie=None, pc=None, largeur=6016, vignetage=None, pc_options=None)` ; `comparer(nx, jpeg, s=32)` et `lire_jpeg(p)` inchangés ; `nksc(pc)` reste valable (octet pour octet identique au précédent). Nouveautés : `ecrire_np2`, `np2_recette`, `lire_np3`, `profil_radial`, `exif`, `lot(..., sortie_json, pas)`, CLI `picture_control.py np2 recette.json sortie.NP2`. `ecrire_ncp`, `bloc_recette`, `lut_points`, `BASES`, `BORNES_PTP` intacts.

## 7. À faire / incertain
- Un NP2 réel (Picture Control Utility 2 sur un PC, ou export d'un boîtier) pour valider l'écriture hors NX.
- Loi du réglage de vignetage selon ouverture et ISO (trois ouvertures mesurées, une seule vue chacune).
- Ouvrir NX Studio à la main sur un NEF avec la case du vignetage cochée et lire le `.nksc` écrit donnerait la vérité terrain de la plage du curseur (non fait, aucune interface lancée).
