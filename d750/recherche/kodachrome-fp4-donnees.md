# Kodachrome, FP4 Plus (et HP5, Tri-X) : données publiées et cibles chiffrées pour les Picture Control du D750

Recherche d’octobre 2026 pour le D750 « de production » de Thomas (firmware intact). Même démarche que [hp5-donnees-film.md](hp5-donnees-film.md), qui n'est pas modifié ici. Données numériques dans [`donnees-films/`](donnees-films/), outils dans [`outils/`](../outils/).

Conventions de statut (les mêmes que pour la HP5) :
- **vérifié** : lu dans une source citée, ou extrait tel quel d'un PDF ;
- **hypothèse** : déduction, lecture indirecte ou valeur non confirmée ;
- **calcul** : chiffre produit pour ce rapport à partir de sources vérifiées et d'hypothèses nommées à côté ; c'est une hypothèse chiffrée, pas une mesure.

Accès aux sources : depuis le conteneur, les sites de Kodak et d'Ilford répondent 403 (anti-robot) et la Wayback Machine coupe les connexions ; les fiches ont été lues dans les copies de 125px.com (archive de fiches techniques). Empreintes SHA-256 des PDF lus dans les JSON. Aucun binaire téléchargé n'a été exécuté ; le code des dépôts tiers a été lu, jamais lancé.

## Ce qui compte le plus

1. **Les graphiques des fiches Kodak et de la fiche Ilford 2004 sont vectoriels.** Les courbes ont été lues directement dans le PDF (polylignes converties en unités d'axes), sans numérisation à l'œil : résidu de calibration nul sur les axes de densité, inférieur à 1 nm sur les longueurs d'onde. Deux numérisations indépendantes publiées (agx-emulsion, spectral_film_lut) concordent à 0,005 en densité et 0,01 en log sensibilité (médianes). Vérifié.
2. **Kodachrome 64, courbe neutre** : pente moyenne 1,42 à 1,52 (Status A), Dmin 0,18 à 0,20, latitude utile d'environ 3,6 IL (de Dmin + 0,2 à D 2,0). Un gris de 18 % exposé au posemètre sort à **D 0,99 au-dessus du blanc du film, soit L\* 38 (environ 90/255)** : la diapositive est dense. La courbe se transpose telle quelle en courbe perso. Vérifié (fiche) ; calage du gris : hypothèse ; rendu : calcul.
3. **Kodachrome, couleur : les dérives de teinte changent de signe selon la teinte** (modèle spectral sur la fiche, K64) : jaunes et verts tournent de +13 à +19° vers le cyan, bleus de −10°, magentas de −15°, rouges de −6°. Le meilleur réglage de teinte global vaut 0 ; teinte et saturation globales ne font gagner que 0,5 ΔE2000 médian (5,5 → 5,0). **Un Picture Control ne porte que la courbe et la densité du Kodachrome, pas sa palette.** Calcul.
4. **Le modèle ne sait pas chiffrer la saturation absolue** : sans effets inter-couches (non publiés pour le K-14), il rend le Kodachrome *moins* saturé que la scène (×0,79 à tonalité égale), ce que contredit sa réputation. La saturation se cale donc sur le boîtier, pas sur ce chiffre. Hypothèse forte, nommée.
5. **Gamme mesurée par Kodak sur du vrai Kodachrome** (mire IT8 Q-60K3, 1999) : chroma jusqu'à 68 dans les rouges, 102 dans les jaunes, 85 dans les verts, mais **23 au plus dans les bleus cyan (teintes 240 à 270°)** ; 11,7 % des plages sont hors sRGB, donc hors d'atteinte d'un JPEG sRGB. Vérifié (données Kodak) ; lecture : calcul.
6. **FP4 Plus : spectralement presque une HP5** (ΔL\* médian 1,1 entre les deux fiches). Mélange en sRGB linéaire **0,12 / 0,27 / 0,61**, très bleu ; comme pour la HP5, aucun filtre du Monochrome ne s'en approche, et « aucun » reste le moins mauvais (ΔL\* médian 7,5). Courbe Ilfotec HC 1+31 : pente 0,68 (HP5 : 0,59), voile 0,08, **épaule à D 1,87** environ 2,8 log au-dessus du point de vitesse. Vérifié (fiche) ; mélange et écarts : calcul.
7. **La fiche Ilford FP4 Plus en vigueur (novembre 2018) ne publie ni granularité, ni FTM, ni indice de contraste, et une seule courbe** (Ilfotec HC 1+31) ; ses deux graphiques sont ceux de la fiche 2004. Vérifié.
8. **HP5 et Tri-X relues de la même façon (§4)** : les numérisations à la main du projet étaient justes (écarts invisibles en JPEG, mélanges identiques à ±0,002). L'apport réel est la Tri-X selon le développement : huit courbes publiées (D-76 et T-MAX, 6 à 12 min), du rendu doux au rendu dur ; la courbe du D750 doit suivre le révélateur et le temps de Thomas. Vérifié (extraction) ; cibles : calcul.

## 1. Sources

| Source | URL | Date | Ce qu'elle donne exactement | Fiabilité |
|---|---|---|---|---|
| Kodak, *KODACHROME 25, 64, and 200 Professional Films*, E-55 | https://125px.com/docs/film/kodak/e55-1996_12.pdf | déc. 1996 (« Major Revision 12-96 ») | 8 p. ; par film : courbes caractéristiques R, V, B (Status A, lumière du jour), sensibilités spectrales des trois couches (D = 1,0 E.N.D.), densités spectrales des colorants normalisées (neutre visuel D = 1,0 sous 3 200 K), FTM, granularité RMS ; EI avec filtres, réciprocité, guides flash, filtrations fluorescent | fabricant ; graphiques vectoriels, extraits exactement. Vérifié |
| Kodak, E-55, révisions suivantes | https://125px.com/docs/film/kodak/e55-2003_08.pdf, https://125px.com/docs/film/kodak/e55-2009_06.pdf | août 2003, juin 2009 | mêmes courbes (mêmes extrêmes, mêmes maxima spectraux) ; 2009 : avis d'arrêt, Ektar 100 et E100G proposés en remplacement | vérifié |
| Kodak, E-55 officielle | copie d'archive repérée : https://web.archive.org/web/20190825122446/https://www.kodak.com/global/en/professional/support/techPubs/e55/e55.pdf | capture du 25/08/2019 | non lue (Wayback inaccessible depuis le conteneur) | hypothèse : identique à la 2009 |
| Kodak, *KODACHROME 64 and 200 Films*, E-88 (grand public) | https://125px.com/docs/film/kodak/e88-2009_06.pdf (et 1998, 2002, 2005) | 1998 à juin 2009 | 2009 : courbes K64 et K200 identiques à l'E-55 | vérifié |
| Kodak, mire IT8.7/1 Q-60K3, fichier K3199910.Q60 | https://github.com/gingerbeardman/Kodak-Q60-IT8-Reference-Files (dépôt de R&D, 04/03/2020) | lot d'oct. 1999, fichier du 08/03/2000 | XYZ et Lab (D50, référence opale ISO 5-2) de 264 plages, moyenne de lot, « Kodachrome product family » ; droits : Kodak | mesure fabricant ; donnée, pas un rendu de scène. Vérifié |
| Giorgianni, Madden, Kriss, *Digital Color Management*, 2e éd., Wiley, 2009, p. 335 | numérisation publiée dans agx-emulsion, dépôt de R&D (mars 2026), `agx_emulsion/data/densitometer/status_A/` | 2009 / 2026 | réponses spectrales Status A (R, V, B), linéaires | numérisation tierce ; sensibilité testée (§2.4). Hypothèse acceptable |
| A. Volpato, agx-emulsion puis spektrafilm | https://github.com/andreavolpato/spektrafilm (= agx-emulsion), dernier commit juin 2026 | 2025 à 2026 | profil `kodak_kodachrome_64.json` (v0.3.2, mai 2026) ; CSV d'origine numérisés sur l'E-88 de juin 2009 (commits 821a8d6, 8ee856d, février 2026) ; code GPL-3.0, profils CC BY-SA 4.0 | numérisation à la main de la fiche ; concorde avec l'extraction (0,005 en densité). Vérifié |
| J. Lohse, spectral_film_lut | https://github.com/JanLohse/spectral_film_lut, dépôt de R&D (octobre 2026) | 2026 | `reversal_film/kodachrome_64.py` : sensibilités, courbes, densités, FTM, RMS 10, numérisés (Status A) ; aussi tirages dye transfer ; licence MIT | concorde (0,009 en log sensibilité). Vérifié |
| W-Mai, filmr (Rust) | https://github.com/W-Mai/filmr, dépôt de R&D (mai 2026) | 2026 | préréglages Kodachrome 25 et 64 paramétriques : « RMS 7 », « Dmin 0,10 », « Dmax 3,6 », gamma 1,42 ; source : « Kodak Technical Data » sans précision | contredit la fiche (RMS 10, Dmin 0,18 à 0,20) : faible. Vérifié (lecture du code) |
| G'MIC, préréglages couleur « Kodachrome » (HaldCLUT) | https://gmic.eu/color_presets/ | non daté | LUT d'apparence, origine non documentée | goût ; non examiné en détail |
| Fuji X Weekly (R. Roesch), recettes Kodachrome 64 | https://fujixweekly.com/2019/08/02/my-fujifilm-x-t30-kodachrome-64-film-simulation-recipe/ ; https://fujixweekly.com/2020/09/02/with-other-film-simulations-kodachrome-64/ ; https://fujixweekly.com/2022/11/28/kodachrome-64-fujifilm-x-t5-x-trans-v ; https://fujixweekly.com/2024/01/25/mccurry-kodachrome-a-fujifilm-x-trans-iv-film-simulation-recipe | 2019 à 2024 | X-T30 : Classic Chrome, DR400, H +1, S +2, couleur 0, NR −4, netteté +2, grain faible, Color Chrome faible, WB lumière du jour R +2 B −5, +1/3 à +1 IL ; variante X100V (2020, R. Guzman) : DR200, H 0, S 0, couleur +2, clarté +3 | à l'œil, sans mesure ; lu par résumé de recherche, non relu dans la page |
| Wikipédia, *Kodachrome* | https://en.wikipedia.org/wiki/Kodachrome | lu en octobre 2026 | 1935 ; K-14 et Kodachrome 25 et 64 en 1974 ; arrêt : K25 2002, K200 2007, K64 annoncé le 22/06/2009 ; dernier traitement (Dwayne's Photo) le 30/12/2010 | secondaire ; dates seulement |
| Nikon, *D800 Technical Guide, Picture Control* | https://download.nikonimglib.com/archive3/lhXO000b2U4Z03mDIHM65Qpykj23/D800_TG_PC_(En)01.pdf | 2012 | curseur Teinte : négatif = rouges vers pourpre, bleus vers vert, verts vers jaune ; positif = l'inverse (rotation de la roue) | lu par résumé de recherche ; supposé valable pour le D750 : hypothèse |
| Hanson et al., *JOSA* 42, p. 663 à 669 (1952) | cité par des brevets Kodak et Fuji (USPTO 4788132, 6746834) | 1952 | origine du concept d'effet inter-image (saturation accrue par les couches voisines) | non lu ; contexte seulement |
| Ilford, *FP4 Plus*, Fact Sheet | https://125px.com/docs/film/ilford/FP4+-200404.pdf | avril 2004 | spectrogramme au tungstène 2 850 K et courbe caractéristique (Ilfotec HC 1+31, 8 min), vectoriels | fabricant ; extraits exactement. Vérifié |
| Ilford, *ILFORD FP4 Plus Technical Information* | officielle : https://www.ilfordphoto.com/amfile/file/download/file/1919/product/687/ ; lue : https://125px.com/docs/film/ilford/FP4-Plus_201811.pdf | nov. 2018 (PDF du 16/09/2019) | mêmes graphiques en image ; réciprocité t^1,26 ; temps de développement (31 révélateurs ou dilutions, EI 50 à 200) | vérifié |

Rien n'a été trouvé de publié sur la colorimétrie scène → diapositive du Kodachrome (mire photographiée sur Kodachrome avec ses valeurs, ou mesure de l'effet inter-image du K-14). C'est la donnée qui manque le plus. Vérifié (absence dans ces recherches, pas une preuve d'inexistence).

## 2. Kodachrome

### 2.1 Données de la fiche E-55 (1996)

Extraction : [`outils/fiches_vectorielles.py`](../outils/fiches_vectorielles.py) ; données complètes : [`donnees-films/kodachrome-e55-1996.json`](donnees-films/kodachrome-e55-1996.json) (points bruts de chaque courbe, calibrations, conditions, chiffres du texte).

| | Kodachrome 25 (PKM) | Kodachrome 64 (PKR) | Kodachrome 200 (PKL) | Statut |
|---|---|---|---|---|
| EI lumière du jour ; 3 200 K + 80A ; 3 400 K + 80B | 25 ; 6 ; 8 | 64 ; 16 ; 20 | 200 ; 50 ; 64 | vérifié |
| Granularité RMS diffuse (D 1,0, 48 µm) | 9 | 10 | 16 | vérifié |
| Exposition des courbes | 1/25 s | 1/50 s | 1/100 s + ND 0,20 | vérifié |
| Dmin R / V / B | 0,18 / 0,16 / 0,16 | 0,18 / 0,19 / 0,20 | 0,21 / 0,20 / 0,20 | vérifié |
| Densité au bout gauche du tracé R / V / B (pas encore le palier de Dmax) | 3,77 / 3,46 / 3,36 à log H −1,8 | 3,68 / 3,45 / 3,33 à −2,4 | 3,51 / 3,22 / 3,14 à −2,81 | vérifié |
| Pente moyenne R / V / B (Dmin + 0,2 à D 2,0) | 1,56 / 1,48 / 1,40 | 1,52 / 1,49 / 1,42 | 1,44 / 1,46 / 1,39 | calcul |
| Pente maximale | 2,2 à 2,4 | 2,2 à 2,4 | 2,2 à 2,5 | calcul |
| Étendue Dmin + 0,2 → D 2,0 (V) | 1,11 log (3,7 IL) | 1,08 log (3,6 IL) | 1,10 log (3,7 IL) | calcul |
| Étendue Dmin + 0,1 → D 3,0 (V) | 1,79 log (5,9 IL) | 1,74 log (5,8 IL) | 1,81 log (6,0 IL) | calcul |
| Maxima de sensibilité (bleu / vert / rouge) | 427 / 551 / 649 nm | 423 / 551 / 649 nm | 438 / 555 / 661 nm | vérifié |
| Largeur à mi-hauteur (bleu / vert / rouge) | 420 à 458 / 530 à 583 / 616 à 661 nm | 412 à 458 / 530 à 572 / 627 à 661 nm | 413 à 468 / 530 à 571 / 627 à 674 nm | calcul |
| Maxima des colorants (jaune / magenta / cyan) | 444 / 540 / 641 nm | 442 / 540 / 642 nm | 445 / 540 / 645 nm | vérifié |
| FTM : maximum ; 50 % | 139 % à 8 c/mm ; 42 c/mm | 123 % à 9 c/mm ; 38 c/mm | identique au 64 sur la fiche (graphique repris, hypothèse) | vérifié (lecture) |
| Réciprocité | 1/10 et 1 s : +1/2 IL | 1/10 s : +1/3 IL ; 1 s : CC05R | 1/10 s : +1/2 IL ; 1 s : CC10Y | vérifié |
| Poussé | déconseillé | déconseillé | EI 500 et 800 ; dérive magenta-rouge | vérifié |

Remarques :
- Les courbes R sont 0,1 à 0,3 plus denses que B dans les tons moyens (K64 à log H −0,9 : 1,45 / 1,27 / 1,16) alors que le neutre visuel de la fiche lit R 1,19, V 1,10, B 1,06 en Status A pour D 1,0 : l'échelle neutre de la fiche a un peu plus de cyan qu'un neutre visuel. Calcul (Status A de Giorgianni).
- La fiche dit que les trois Kodachrome se scannent avec « une seule échelle de tons et une seule correction couleur ». Vérifié.
- Le bouclage du modèle est bon : la somme des trois colorants normalisés redonne le « neutre visuel » de la fiche à 0,03 près, et ce neutre est bien neutre sous D50 comme sous 3 200 K (a\*, b\* à ±0,7). Calcul.

### 2.2 Méthode du modèle

[`outils/kodachrome.py`](../outils/kodachrome.py), résultats dans [`donnees-films/kodachrome-cibles.json`](donnees-films/kodachrome-cibles.json).

1. Exposition de chaque couche : réflectance × lumière du jour D55 × sensibilité de la couche (courbes de la fiche, nulle hors du tracé), rapportée à un gris neutre. Le gris de 18 % reçoit log H = log10(q·K/S) = log10(0,65 × 12,5 / ISO), soit −0,90 pour le K64 (étalonnage des posemètres ISO 2720). **Hypothèse** : le texte d'ISO 2240 (sensibilité des inversibles) n'est pas en accès libre, d'où ce calage ; il est testé à ±1/3 IL.
2. Courbes Status A intégrales converties en quantités de colorant (densités analytiques) : pour chaque log H, on résout D_StatusA(Σ a_j · colorant_j) = (R, V, B) ; écart résiduel nul.
3. Chaque couche suit sa propre courbe selon sa propre exposition ; densité spectrale = Σ a_j · colorant_j. **Hypothèse forte : pas d'effet inter-couches.** Le K-14 en a probablement (le premier révélateur noir et blanc agit sur les trois couches), mais rien n'est publié pour le chiffrer.
4. Visionnage : visionneuse 5 000 K (D50, ce que dit la fiche) ou projecteur à 3 200 K (variante « P3200 ») ; blanc = film à Dmin, adapté en D65 (Bradford), comme un scan équilibré sur le blanc du film. Scène : vue sous D55, adaptée en D65. Comparaison en CIELAB D65.
5. Couleurs testées : ColorChecker (Ohta) et 600 spectres lisses aléatoires (les mêmes que `films_nb.reflectances`). Deux références : la scène telle quelle, et la scène « à même tonalité » (sa chromaticité, sa luminance passée dans la courbe neutre du film), qui isole ce que le film fait aux couleurs au-delà de sa courbe.

### 2.3 Courbe tonale neutre (cible chiffrée)

Sortie sRGB codée (luminance, blanc du film = 255) en fonction de l'exposition de la scène en IL autour du gris de 18 %. Calcul. Deux calages : **posemètre** (densité réelle de la diapositive) et **gris à 118** (exposition décalée de +0,55 IL pour le K64, +0,60 pour le K25, +0,57 pour le K200, pour que le gris sorte comme sur un rendu standard). Colonne de référence : la scène codée en sRGB sans courbe.

| IL | sRGB pur | K25 posemètre | K64 posemètre | K200 posemètre | K25 gris 118 | K64 gris 118 | K200 gris 118 |
|---|---|---|---|---|---|---|---|
| −4 | 21 | 4 | 5 | 6 | 5 | 6 | 7 |
| −3 | 33 | 7 | 8 | 9 | 13 | 14 | 14 |
| −2 | 60 | 20 | 21 | 21 | 33 | 35 | 35 |
| −1 | 85 | 45 | 49 | 48 | 70 | 70 | 71 |
| 0 | 118 | 88 | 90 | 90 | 118 | 118 | 118 |
| +1 | 162 | 139 | 143 | 140 | 171 | 172 | 169 |
| +2 | 221 | 190 | 194 | 191 | 215 | 217 | 216 |
| +3 | 255 (coupé) | 229 | 232 | 232 | 247 | 246 | 246 |

Lecture : à calage égal du gris, le Kodachrome a nettement plus de contraste que la scène codée en sRGB (−1 IL : 70 contre 85 ; +1 IL : 172 contre 162), des ombres qui s'effondrent sous −3 IL, et une épaule douce jusqu'à +3 IL. Les trois films ont presque la même courbe (écart ≤ 4/255), comme le dit la fiche. Table de 257 valeurs (entrée sRGB codée) pour les deux calages dans le JSON (`cible_tonale`), **sous l'hypothèse que la base du boîtier rend la scène en sRGB pur** : à recomposer avec la courbe de base mesurée du D750 (étape de calibration du mode d'emploi).

### 2.4 Couleur : saturation et dérives de teinte (calcul, K64 en tête)

Par secteur de teinte de la scène (600 spectres + mire, chroma > 10), film contre scène « à même tonalité », visionneuse D50 ; teinte en degrés CIELAB (positif = sens rouge → jaune → vert → bleu) :

| Secteur (teinte scène) | K64 : décalage de teinte | K64 : chroma × | K25 : teinte | K200 : teinte | K64 sous 3 200 K : teinte, chroma |
|---|---|---|---|---|---|
| rouge (0 à 45°) | −5,7° | 0,86 | +8,1° | +2,5° | −4,0°, 0,89 |
| orange, peau (45 à 75°) | +5,9° | 0,63 | +17,6° | +12,8° | +6,3°, 0,64 |
| jaune (75 à 105°) | +12,9° | 0,67 | +15,3° | +15,2° | +14,9°, 0,68 |
| vert-jaune (105 à 135°) | +17,1° | 0,69 | +11,7° | +15,1° | +21,0°, 0,73 |
| vert (135 à 165°) | +19,1° | 0,74 | +11,6° | +13,9° | +23,0°, 0,81 |
| cyan-vert (165 à 200°) | +13,7° | 0,83 | +11,0° | +11,7° | +15,8°, 0,94 |
| cyan (200 à 235°) | +1,1° | 0,90 | +1,0° | +2,9° | +0,2°, 1,01 |
| bleu (235 à 290°) | −10,3° | 0,83 | −6,3° | −11,7° | −13,4°, 0,90 |
| violet (290 à 330°) | −6,3° | 0,85 | −5,6° | −10,5° | −6,9°, 0,84 |
| magenta (330 à 360°) | −15,2° | 0,74 | −8,0° | −15,5° | −13,0°, 0,75 |
| **global (médiane)** | **10,2° en valeur absolue** | **0,79** | 10,6° | 10,7° | 11,6°, 0,83 |

Ce qui ressort, par ordre de solidité :
- **Sens des dérives** (les trois films, les deux visionnages) : jaunes, verts et cyan-verts tournent vers le cyan de +11 à +23° ; bleus, violets et magentas tournent dans l'autre sens, de −6 à −15° ; les cyans ne bougent pas. Les rouges hésitent (−6° sur le K64, +8° sur le K25). Calcul.
- **Saturation relative** : les bleus, cyans et rouges gardent le plus de chroma (0,83 à 0,90), les jaunes et oranges en perdent le plus (0,63 à 0,67). Plages de la mire (K64, à même tonalité) : ciel bleu ×1,29, bleu ×1,17, rouge ×1,10 ; jaune ×0,86, vert ×0,85, feuillage ×0,85. Calcul.
- **Peau** : peau claire ×0,68 (plus pâle), teinte −8° sur le K64 (plus rose) mais +9° sur le K25 et +6° sur le K200 ; peau foncée ×0,99. Le signe change d'un film à l'autre : non robuste. Calcul.
- **Valeur absolue de la saturation** : non fiable (voir point 4 de « Ce qui compte le plus »). Contre la scène brute, le film est en outre plus sombre de 10 L\* en médiane (densité au posemètre), d'où ΔE2000 médian 10,8 ; à même tonalité, 5,5. Calcul.
- **Neutres** (K64, D50, blanc du film) : légère dominante froide dans les tons moyens (gris de 18 % : a\* −1,1, b\* −6,2 ; +1 IL : −3,5, −4,7), rien dans les noirs. Avec la réponse Status A décalée de ±5 nm, b\* du gris va de −4,8 à −7,5 : le sens tient. K25 et K200 : plus faible et plus vert (a\* −2 à −3, b\* −2). Calcul.
- **Contrôle par la mire Q-60K3** (gris d'une diapositive Kodachrome mesurés par Kodak, ramenés au blanc du film) : clairs nettement verts (a\* −12 à −14 vers L\* 75 à 85, b\* +2 à +4), ombres magenta-bleues (a\* +3 à +5, b\* −3 à −4,5). Même sens que le modèle sur a\* (vert dans les clairs, magenta dans les ombres), amplitudes plus fortes. Réserve : une mire IT8 est fabriquée à des densités visées, pas photographiée ; c'est un indice sur ce que donnent les colorants, pas une mesure du rendu d'un gris de scène. Vérifié (données) ; interprétation : hypothèse.

Sensibilité : à ±1/3 IL, le chroma relatif bouge de 0,02 et les décalages de teinte de 1° environ. Calcul.

### 2.5 Gamme mesurée (mire Q-60K3, Kodak)

Chroma maximal par secteur de teinte, blanc du film ramené en D65 (calcul sur [K3199910.Q60](https://github.com/gingerbeardman/Kodak-Q60-IT8-Reference-Files)) :

| Teinte (°) | 0 à 30 | 30 à 60 | 60 à 90 | 90 à 120 | 120 à 150 | 150 à 180 | 180 à 210 | 210 à 240 | 240 à 270 | 270 à 300 | 300 à 330 | 330 à 360 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C\* max | 68 | 75 | 102 | 89 | 85 | 71 | 58 | 38 | **23** | 67 | 73 | 80 |
| L\* à ce max | 40 | 28 | 84 | 85 | 60 | 60 | 74 | 53 | 21 | 30 | 35 | 46 |

Lecture : les colorants Kodachrome savent faire des rouges, magentas, jaunes et verts très saturés, des bleus violacés profonds, mais **pas de bleu-cyan saturé** (ciel « azur ») : c'est la contrainte la plus caractéristique de la palette, cohérente avec le décalage des bleus vers le violet. 28 des 240 plages colorées (11,7 %) sont hors sRGB : le JPEG sRGB du D750 ne peut pas les rendre (Adobe RVB en élargirait une partie : hypothèse). Vérifié (données) ; lecture : calcul.

### 2.6 Ce qu'un Picture Control peut et ne peut pas reproduire

| Trait du Kodachrome | Réglage global | Verdict | Statut |
|---|---|---|---|
| Courbe neutre (contraste fort, ombres denses, épaule douce) | courbe perso, table §2.3 | atteignable | calcul (cible) ; fidélité : à mesurer |
| Densité de la diapositive au posemètre (gris à L\* 38) | courbe calée « posemètre », ou correction d'exposition | atteignable ; c'est un choix | hypothèse |
| Saturation globale | curseur Saturation | atteignable, mais **valeur à caler sur le boîtier** : le modèle ne la chiffre pas de façon fiable | hypothèse |
| Dérives de teinte (jaunes et verts vers le cyan, bleus et magentas vers le violet et le rouge) | curseur Teinte : rotation uniforme de toute la roue (fiche technique Nikon D800) | **hors d'atteinte** : signes opposés selon les secteurs ; rotation optimale 0° | calcul |
| Saturation par secteur (bleus et rouges tenus, jaunes et oranges éteints) | aucun | hors d'atteinte | calcul |
| Dominante des neutres selon la tonalité (clairs verts, ombres magenta) | WB (seulement en U1 ou U2) : décalage unique | hors d'atteinte, sauf une dominante moyenne | calcul et données Kodak |
| Gamme (11,7 % hors sRGB ; pas de bleu-cyan saturé) | aucun ; la limite basse (bleu-cyan faible) s'imite mal par la saturation globale | hors d'atteinte | calcul |
| Netteté (FTM 123 à 139 % vers 8 c/mm) | accentuation, clarté | partiel, à mesurer comme pour la HP5 (§5.4 du rapport HP5) | hypothèse |

Chiffre de synthèse (K64, référence à même tonalité, calcul) : courbe seule ΔE2000 médian 5,5 (90e centile 10,3) ; courbe + meilleure saturation et teinte globales 5,0 (9,0). **Ce que la courbe ne fait pas, le reste des curseurs ne le rattrape presque pas.**

Avis : le Kodachrome sera le moins fidèle des neuf profils. Ce qu'on peut tenir : la courbe, la densité et un niveau de saturation choisi à l'œil sur les essais. La palette elle-même (bleus violacés, jaunes et verts tirés vers le cyan, peaux pâles) demande une correction par secteur de teinte, ce qui suppose le firmware (les 16 secteurs de la V1 du D40) ou un post-traitement. Les recettes Fujifilm « Kodachrome 64 » font d'ailleurs pareil : Classic Chrome, une WB décalée vers le rouge et le jaune (R +2, B −5) et de la saturation, sans prétendre aux dérives par teinte.

## 3. Ilford FP4 Plus

### 3.1 Données de la fiche

Données complètes : [`donnees-films/fp4-plus.json`](donnees-films/fp4-plus.json) (points des deux courbes, calibrations, temps de développement de la fiche 2018).

| Donnée | Contenu | Statut |
|---|---|---|
| Fiche en vigueur | Ilford, novembre 2018 (PDF du 16/09/2019), 6 p. ; graphiques en image, identiques à ceux de la fiche Ilford d'avril 2004, elle vectorielle | vérifié (graphiques superposables à l'œil) |
| Sensibilité | ISO 125/22°, mesurée en ID-11 à 20 °C ; EI 50 à 200 conseillés (« évaluation pratique », pas le point de pied de la norme) ; latitude annoncée : +6 IL, −2 IL | vérifié |
| Sensibilité spectrale | « Wedge spectrogram » au tungstène 2 850 K, sans valeurs ; lu comme pour la HP5 (hauteur relative linéaire, zéro aux graduations 0,5 et 1,0) : 0,39 à 400 nm, 0,58 à 440, 0,65 à 500, 0,75 à 540, maximum 0,97 vers 605 nm, coupure à 664 nm | courbe : vérifié ; lecture linéaire : hypothèse |
| Courbe caractéristique | **une seule** : rouleau, Ilfotec HC 1+31, 8 min à 20 °C, agitation intermittente | vérifié |
| Voile ; point de vitesse | 0,081 ; log H relatif 1,23 | calcul (lecture) |
| Pente moyenne | 0,68 (voile + 0,1 à +1,5 log) ; HP5 dans la même méthode : 0,59 ; Tri-X (T-MAX) : 0,54 | calcul |
| Épaule | densité 1,87 atteinte vers log H 4,0 (2,8 log, soit 9 IL, au-dessus du point de vitesse), plate ensuite | vérifié (tracé) |
| Granularité, FTM, pouvoir résolvant, indice de contraste | absents (2004 et 2018) | vérifié (absence) |
| Réciprocité | rien de 1/10 000 à 1/2 s ; au-delà, temps corrigé = temps mesuré^1,26 (10 s → 18 s ; 30 s → 73 s) | vérifié (formule) ; exemples : calcul |
| Supports | 135 : acétate 0,125 mm (la fiche ne parle pas d'anti-halo) ; 120 : 0,110 mm, dos anti-halo ; plan : polyester 0,180 mm, dos anti-halo | vérifié |
| Temps (min, 20 °C, EI 125) | ID-11 stock 8½ ; 1+1 11 ; DD-X 1+4 10 ; HC 1+31 8 ; Perceptol stock 12 ; Rodinal 1+50 15 ; D-76 stock 8 ; Xtol 8½ (extrait ; table complète dans le JSON) | vérifié |

### 3.2 Mélange de canaux (sRGB linéaire)

Méthode : celle de `films_nb.poids` (§3.3 du rapport *perspectives*), avec des « sensibilités » sRGB (CIE 1931 → sRGB), 600 couleurs naturelles, lumière du jour D65 ; poids positifs, somme 1. Le calcul retrouve exactement les mélanges publiés pour la Tri-X (0,17 / 0,31 / 0,52) et la HP5 (0,10 / 0,24 / 0,67). Commande : `films_nb.py srgb`.

| Cible | R | V | B | Écart résiduel (ΔL\* méd. / 90e c.) | Statut |
|---|---|---|---|---|---|
| **FP4 Plus (fiche 2004)** | **0,12** | **0,27** | **0,61** | 0,6 / 2,3 | calcul |
| FP4 Plus, zéro du spectrogramme pris au bas du cadre | 0,12 | 0,26 | 0,62 | 0,7 / 2,5 | calcul (variante) |
| HP5 Plus | 0,10 | 0,24 | 0,67 | | calcul |
| Tri-X 400 | 0,17 | 0,31 | 0,52 | | calcul |

FP4 contre HP5 : ΔL\* médian 1,1 (90e centile 2,5) ; contre Tri-X : 1,4 (3,3). Le choix de lecture du spectrogramme ne change presque rien. Calcul.

Écart des réglages du D750 à la cible FP4 (ΔL\* médian / 90e centile, 600 couleurs, exposition égale) :

| Réglage | FP4 | HP5 (contrôle, §3.3 : 12,2 ; 10,2 ; 8,8) | Statut |
|---|---|---|---|
| Filtre orange (mélange mesuré sur 60 NEF) | 10,9 / 24,0 | 11,8 / 26,2 | calcul |
| Filtre jaune (mesuré, 3 NEF) | 9,2 / 21,1 | 10,2 / 23,5 | calcul |
| Filtre rouge (mesuré, 2 NEF) | 16,2 / 36,7 | 16,5 / 39,1 | calcul |
| Aucun (hypothèse : luminance Rec.709) | 7,5 / 17,7 | 8,6 / 19,8 | calcul |
| Mélange du preset Tri-X | 6,5 / 15,2 | 7,7 / 17,5 | calcul |

Mes écarts reproduisent le tableau du §3.3 de *perspectives* à 0,4 point près (même méthode, réflectances régénérées). Le réglage « aucun + WB fixe 10 000 K », meilleur pour la HP5 (7,9), n'a pas été recalculé faute du modèle de matrice du D750 : par analogie, environ 6,5 à 7 pour la FP4. Hypothèse.

### 3.3 Courbe tonale (film + tirage, cible chiffrée)

Méthode de `films_nb.courbe` (négatif de la fiche, papier grade 2 ISO 6846 d'étendue 1,10 log, gris de 18 % placé 1,0 log au-dessus du point de vitesse et tiré à 118/255), avec en référence la scène codée en sRGB. Commande : `films_nb.py tonale`. Épaule de la FP4 tenue plate au-delà du tracé (la HP5 et la Tri-X sont prolongées par leur pente). Calcul.

| IL | sRGB pur | FP4 Plus | HP5 Plus | Tri-X 400 |
|---|---|---|---|---|
| −4 | 21 | 6 | 9 | 13 |
| −3 | 33 | 12 | 14 | 20 |
| −2 | 60 | 25 | 28 | 35 |
| −1 | 85 | 53 | 58 | 65 |
| 0 | 118 | 117 | 117 | 117 |
| +1 | 162 | 194 | 180 | 177 |
| +2 | 221 | 237 | 225 | 222 |

La FP4 tirée sur grade 2 est la plus contrastée des trois : ombres plus profondes, clairs plus vite blancs. La table de 257 valeurs (entrée sRGB codée, même hypothèse de base sRGB pure qu'au §2.3) est dans [`donnees-films/fp4-cibles.json`](donnees-films/fp4-cibles.json).

### 3.4 Ce qui est atteignable sur le D750

- **Courbe** : oui, en courbe perso sur base Monochrome, D-Lighting actif désactivé (comme la HP5, §5.2 du rapport HP5). Calcul (cible) ; fidélité : à mesurer.
- **Sensibilité spectrale** : non. Le bleu de la fiche (0,61) est aussi loin des filtres du Monochrome que celui de la HP5 ; « aucun » est le moins mauvais, une WB fixe chaude aide un peu. Thomas a écarté les filtres devant l'objectif (décision d’octobre 2026), donc pas de 80A + 80B. Calcul.
- **Grain** : rien à ajouter au §3.6 du rapport HP5 ; la fiche FP4 ne publie aucune donnée de grain. Vérifié (absence).
- **Cible de Thomas** : ses 124 scans FP4+ dans Lightroom restent la référence de goût, à mesurer comme les scans HP5 (tonalité par centiles, dossier jetable) depuis son ordinateur ; ils ne sont pas accessibles depuis le cloud.

## 4. HP5 Plus et Tri-X 400 au même niveau de précision

Demande de Thomas (octobre 2026). Même extraction directe dans les PDF vectoriels : fiche Ilford HP5 Plus de juillet 2004 (les graphiques de la fiche Ilford 2018 sont les mêmes, en image ; voir [hp5-donnees-film.md](hp5-donnees-film.md) §1.1) et fiche Kodak F-4017 d'octobre 2021, celle que `films_nb.py` utilise déjà. Données : [`donnees-films/hp5-plus.json`](donnees-films/hp5-plus.json), [`donnees-films/tri-x-f4017-2021.json`](donnees-films/tri-x-f4017-2021.json) ; cibles : [`donnees-films/hp5-trix-cibles.json`](donnees-films/hp5-trix-cibles.json). Dans `films_nb.py`, la fonction `fiches_exactes()` ajoute ces données sans toucher aux constantes existantes.

**Les numérisations à la main du projet étaient bonnes.** Comparées aux courbes exactes (calcul) :

| | Courbe caractéristique (écart de densité, médian / max) | Spectre (médian / max) | Effet sur le mélange sRGB | Effet sur la courbe tonale (ΔL\*, médian / max) |
|---|---|---|---|---|
| Tri-X (T-MAX 6 min, D = 1,0) | 0,012 / 0,019 | 0,010 / 0,12 log à 650 nm (flanc de coupure) | 0,167 / 0,312 / 0,521 → identique | 0,02 / 0,08 |
| HP5 (Ilfotec HC 1+31) | 0,003 / 0,018 | 0,010 / 0,09 à 385 nm | 0,097 / 0,236 / 0,667 → 0,096 / 0,238 / 0,666 | 0,01 / 0,16 |

Donc rien à corriger dans les recettes existantes : les écarts sont sous ce qu'un JPEG 8 bits distingue. Vérifié (extraction) ; effets : calcul.

**Ce que la précision apporte vraiment : la Tri-X selon le développement.** La fiche Kodak publie huit courbes pour la Tri-X 400 en 35 mm (et autant en 120), ce que la HP5 n'a pas. Cible tonale par développement, même chaîne que §3.3 (papier grade 2, gris tiré à 118/255) ; sortie 8 bits par IL autour du gris (calcul) :

| Développement (20 °C) | Voile | Pente moyenne | −3 IL | −2 IL | −1 IL | 0 | +1 IL | +2 IL |
|---|---|---|---|---|---|---|---|---|
| D-76, 6 min | 0,27 | 0,47 | 28 | 43 | 72 | 118 | 175 | 217 |
| D-76, 8 min | 0,29 | 0,56 | 18 | 33 | 64 | 117 | 181 | 224 |
| D-76, 10 min | 0,30 | 0,67 | 10 | 24 | 55 | 117 | 188 | 231 |
| D-76, 12 min | 0,32 | 0,79 | 5 | 15 | 46 | 117 | 196 | 237 |
| T-MAX, 6 min (cible actuelle) | 0,31 | 0,54 | 20 | 36 | 67 | 118 | 178 | 221 |
| T-MAX, 7 min | 0,33 | 0,59 | 15 | 30 | 62 | 117 | 182 | 226 |
| T-MAX, 9 min | 0,36 | 0,71 | 8 | 20 | 52 | 117 | 192 | 235 |
| T-MAX, 11 min | 0,38 | 0,84 | 4 | 12 | 43 | 117 | 203 | 242 |
| HP5, Ilfotec HC 1+31, 6 min 30 (seule courbe Ilford) | 0,17 | 0,60 | 14 | 27 | 57 | 117 | 183 | 226 |
| FP4, Ilfotec HC 1+31, 8 min (seule courbe Ilford) | 0,08 | 0,68 | 12 | 25 | 53 | 117 | 194 | 237 |

Lecture : d'un développement à l'autre, la Tri-X va d'un rendu doux (D-76 6 min, les ombres restent ouvertes) à un rendu très dur (T-MAX 11 min). Le choix de la courbe pour le D750 dépend donc du révélateur et du temps que Thomas utilise (ou qu'il veut évoquer), pas seulement du film. Temps conseillés par la fiche à EI 400 et 20 °C : T-MAX 6 min (petite cuve), D-76 6¾ min (petite cuve) ou 7¾ min (grande cuve), soit entre les courbes D-76 6 et 8 min. Vérifié (tableaux p. 3). La fiche donne aussi l'indice de contraste en fonction du temps (D-76 : 0,48 à 5,4 min, 0,82 à 10,8 min ; XTOL : 0,34 à 3,25 min, 0,98 à 14 min ; T-MAX RS : 0,51 à 0,99 entre 3,25 et 13 min) ; les courbes T-MAX, HC-110, D-76 1+1 et XTOL 1+1 n'ont pas pu être séparées sans ambiguïté (motifs de tirets répétés ou trop courts). Vérifié (extraction) ; tirage : calcul.

Sensibilité spectrale de la Tri-X : la fiche donne deux courbes (D = 0,3 et D = 1,0 au-dessus du voile). Le mélange sRGB change un peu selon celle qu'on prend : 0,17 / 0,31 / 0,52 (D = 1,0, retenu jusqu'ici) contre 0,19 / 0,34 / 0,47 (D = 0,3). Curiosité : sur le graphique, la courbe légendée D = 1,0 est la plus haute, alors qu'il faut plus de lumière pour atteindre D = 1,0 que D = 0,3 ; légende peut-être inversée. Ça ne change que l'échelle, pas la forme retenue. Vérifié (graphique) ; interprétation : hypothèse.

Pour la HP5, rien de plus n'est publié par Ilford (une seule courbe, pas de spectre chiffré, pas de grain) : le niveau de précision atteint ici est le plafond de ce que donnent les fiches. Le reste viendra des scans HP5 de Thomas (cible déjà mesurée dans *perspectives* §3.3).

Suite (octobre 2026) : la Tri-X en DD-X ou en Rodinal, les révélateurs de Thomas, est traitée dans [d750-leviers-reglages.md](d750-leviers-reglages.md) §4 (courbe interpolée au contraste « normal » d'Ilford, pente 0,62).

## 5. Fichiers produits et reproduction

| Fichier | Contenu |
|---|---|
| [`donnees-films/kodachrome-e55-1996.json`](donnees-films/kodachrome-e55-1996.json) | K25, K64, K200 : courbes caractéristiques, sensibilités, colorants, FTM (points bruts du PDF), calibrations, conditions, chiffres du texte |
| [`donnees-films/kodachrome-cibles.json`](donnees-films/kodachrome-cibles.json) | échelles de gris (D50, 3 200 K), courbe neutre, cibles tonales (257 valeurs, deux calages), comparaisons mire et secteurs (±1/3 IL), réglage global |
| [`donnees-films/fp4-plus.json`](donnees-films/fp4-plus.json) | spectrogramme et courbe (points bruts), calibrations, chiffres du texte, temps de développement 2018 |
| [`donnees-films/fp4-cibles.json`](donnees-films/fp4-cibles.json) | mélanges sRGB (FP4, HP5, Tri-X), écarts des réglages du D750, cibles tonales des trois films |
| [`donnees-films/tri-x-f4017-2021.json`](donnees-films/tri-x-f4017-2021.json) | Tri-X 400 (35 mm, 120 ; T-MAX et D-76, quatre temps chacun), Tri-X 320 plan (HC-110 B), sensibilités D = 0,3 et 1,0, indice de contraste |
| [`donnees-films/hp5-plus.json`](donnees-films/hp5-plus.json) | HP5 Plus : spectrogramme et courbe (points bruts, fiche 2004) |
| [`donnees-films/hp5-trix-cibles.json`](donnees-films/hp5-trix-cibles.json) | mélanges sRGB (constantes contre fiches exactes), cibles tonales par développement de la Tri-X |
| [`outils/fiches_vectorielles.py`](../outils/fiches_vectorielles.py) | extraction des courbes vectorielles (E-55 1996, F-4017 2021, FP4 et HP5 2004) |
| [`outils/kodachrome.py`](../outils/kodachrome.py) | modèle spectral et cibles ; auto-test |
| [`outils/films_nb.py`](../outils/films_nb.py) | FP4 ajoutée (constantes de la fiche), `fiches_exactes()` (données des PDF, variantes de développement), actions `srgb` et `tonale` |

Refaire : télécharger les PDF (URL ci-dessus), puis `fiches_vectorielles.py kodachrome|trix|fp4|hp5 <pdf> sortie.json` ; récupérer les réponses Status A (commande dans l'en-tête de `kodachrome.py`), puis `kodachrome.py <status_A/> --film tous --json …`. Le calcul d'écarts de la FP4 (tableau du §3.2) s'est fait dans le dossier jetable (script `fp4_ecarts.py`, non conservé) : `films_nb.reflectances`, `films_nb.sens_srgb`, L\* de la réponse du film contre L\* du mélange, à blanc égal.

## Ce qui reste incertain

- **L'effet inter-image du K-14** : non publié ; sans lui, le modèle sous-estime la saturation et peut-être déforme certaines teintes. C'est la limite principale des §2.4 et 2.6.
- **La réponse Status A** vient d'une numérisation tierce d'un livre ; le sens de la dominante des neutres résiste à ±5 nm, pas son amplitude exacte.
- **Le calage du gris** (q·K/S) : ISO 2240 non lue. L'erreur vraisemblable est de l'ordre de 0,1 log (1/3 IL), testée.
- **Le visionnage** : visionneuse 5 000 K adaptée au blanc du film ; une projection en salle noire (adaptation et contraste perçu différents) n'est pas modélisée.
- **Le spectrogramme FP4** : lu en hauteur linéaire comme celui de la HP5 ; un spectrogramme à coin est en principe proportionnel au log de la sensibilité, mais l'étendue du coin n'est pas donnée. La variante « zéro au bas du cadre » ne change rien (§3.2) ; la lecture logarithmique n'a pas pu être chiffrée.
- **La base du D750** : les tables de 257 valeurs supposent une base qui rend la scène en sRGB pur ; il faut les recomposer avec la courbe de base mesurée (calibration du mode d'emploi).
- **Une vraie mesure scène → Kodachrome** (mire photographiée sur Kodachrome avec ses valeurs) : rien trouvé de publié.
