# Traitement d'image d'appareil photo depuis 2006 : ce qui est transposable au D40

Recherche documentaire d’octobre 2026. Contexte et contraintes : [`CARTE.md`](../CARTE.md) §7. On ne change que des **données** (18 matrices caméra→RGB, courbes 4 096 points 12 bits, 21 matrices RGB→YCbCr, table de correction 8 bits, tables de quantification JPEG, constantes des modes scène). Pas de 3D LUT, pas de code nouveau.

Légende : **[établi]** = source citée ou lu dans le code ; **[mesuré ici]** = expérience faite pendant cette recherche ; **[probable]** / **[spéculatif]** = déduction, à vérifier sur le boîtier.

Principe directeur (exigence du propriétaire) : aucune « jolie couleur » arbitraire. Chaque piste doit reposer sur un principe reconnu (colorimétrie CIE, adaptation chromatique, espace de travail linéaire, modèle d'apparence, théorie du signal) **et** se mesurer (ΔE2000, SSIM/butteraugli/SSIMULACRA2, OECF). Les « effets sapin de Noël » (saturation poussée, teintes décalées pour faire « cinéma », courbes par canal très contrastées) sont écartés explicitement : voir §9.

---

## 0. Trois corrections sur les hypothèses de départ

1. **Le capteur n'est peut-être pas un ICX493.** La littérature trouvée donne l'ICX493AQA comme un CCD APS-C de 4 610 × 3 080 pixels à 5,12 µm (≈ 14 Mpx, caméra astro QHY10, [rk.edu.pl](https://rk.edu.pl/astro/kamery-ccd/matryca/icx493aqa/)), ce qui ne colle pas avec les 3 008 × 2 000 du D40. La famille D70/D50 est basée sur l'ICX413AQ (6,15 Mpx, cellule 7,8 µm, interline, obturateur mécanique requis, [DPReview 2002](https://www.dpreview.com/articles/9510183425/sonyicx413), fiche marquée « non confirmée »). Aucune source retrouvée ne nomme la puce du D40 ; le pas de 23,7 mm / 3 008 ≈ 7,9 µm est compatible avec la famille ICX413. **À vérifier (démontage, ou référence dans les chaînes du firmware) avant d'écrire « ICX493 » dans la doc.**
2. **Le D40 n'a pas de NEF non compressé** : « Compressed only » (Bill Claff, [photonstophotos](https://www.photonstophotos.net/NikonInfo/NEF_Compression.htm)). La compression est **avec perte** (§6).
3. **Les gains « jpegli −35 % » ne viennent pas des tables** (§1, expérience).

---

## 1. Tables de quantification JPEG

### Ce que c'est
Un JPEG baseline stocke deux tables 8×8 (luminance, chrominance) ; le décodeur lit les tables dans le fichier. Le D40 utilise les tables d'exemple de l'Annexe K (1992), mises à l'échelle (sans doute) selon Fine/Normal/Basic (tailles mesurées sur échantillons : 6 Mpx Fine 2,43 Mo, Normal 1,47 Mo, Basic 0,75 Mo, [Photography Blog](https://www.photographyblog.com/pages/reviews/reviews_nikon_d40_2.php) ; le mode de mise à l'échelle dans le firmware est **à lire**, CARTE n'a que les tables de base `0xA23C4`/`0xA2404`).

### Ce qui a progressé depuis
- **mozjpeg** propose 6 tables prédéfinies : 0 = Annexe K, 1 = plate, 2 = réglée MS-SSIM (Kodak), 3 = Robidoux/ImageMagick (défaut de mozjpeg), 4 = réglée PSNR-HVS-M, 5 = Klein/Silverstein/Carney 1992 ([README mozjpeg](https://source-hub.etos-pro.ru/mozilla/mozjpeg/raw/branch/master/README-mozilla.txt), [libvips](https://www.libvips.org/API/8.17/method.Image.jpegsave.html)). Le gros du gain de mozjpeg vient de la **quantification en treillis** (trellis, jusqu'à ≈ 15 % d'après les notes de [libjpeg-turbo](https://libjpeg-turbo.org/About/Mozjpeg)) et des Huffman optimisés : **inutilisable sur l'encodeur matériel** (codeur de bloc fixe, Huffman standard probable).
- **jpegli** (Google, [blog](https://opensource.googleblog.com/2024/04/introducing-jpegli-new-jpeg-coding-library.html)) revendique « +35 % de taux de compression à haute qualité » : étude de préférence humaine (Cloudinary CID22), comparée à libjpeg-turbo et MozJPEG, **débit à qualité égale non chiffré réglage par réglage**. Les ingrédients : (a) matrices choisies par optimisation sur un mélange de métriques psychovisuelles, (b) **quantification adaptative** par bloc (heuristiques de JPEG XL), (c) **zone morte / zero-bias** ajustée selon la fréquence et la distance, (d) calcul interne >8 bits. (b), (c) et (d) sont du **code d'encodeur** ; seul (a) est une donnée.

### Lu dans le code (`google/jpegli`, `lib/jpegli/quant.cc`) [établi]
- `kBaseQuantMatrixYCbCr` (3 × 64 flottants) × `kGlobalScaleYCbCr = 1,7397` × `distance` donne la table finale : `q[k] = round(distance × base[k] × 1,7397)`, bornée à 1..255 en baseline.
- Les valeurs de zero-bias (`kZeroBiasMulYCbCrLQ/HQ`, `kZeroBiasOffsetYCbCrAC`) et `DistanceToScale` (non-linéarité au-delà de distance 1,5) sont du réglage d'encodeur, pas de la table.
- À distance 1,0 la table Y de jpegli est **presque plate** (2 à 11) alors que l'Annexe K à Q90 monte à 24 en hautes fréquences : jpegli compense par la zone morte et l'AQ, pas par la table. Sa table Cb contient des valeurs non monotones (jusqu'à 195, un 179 isolé), conçues pour fonctionner avec ses seuils : à ne pas copier telle quelle.

### Expérience [mesuré ici]
Encodage Pillow/libjpeg, 4:2:0, Huffman standard (donc exactement ce que peut faire un encodeur à tables fixes), 3 photos réduites de moitié et rognées à 2 000 × 1 500, tables Annexe K (Q 50 à 98) contre tables jpegli (distance 3,0 à 0,2), SSIM calculé par fenêtre 7×7, interpolé à débit égal (1,0 / 1,9 / 3,2 bpp, soit environ Basic / Normal / Fine du D40) :

| Débit | SSIM luma Annexe K (3 images) | SSIM luma tables jpegli | SSIM chroma Annexe K | SSIM chroma jpegli |
|---|---|---|---|---|
| 1,0 bpp | .9748 / .9874 / .9878 | .9761 / .9886 / .9889 | .9714 / .9950 / .9724 | .9668 / .9951 / .9699 |
| 1,9 bpp | .9827 / .9904 / .9912 | .9864 / .9916 / .9916 | .9772 / .9949 / .9796 | .9738 / .9955 / .9771 |
| 3,2 bpp | .9898 / .9909 / .9925 | .9921 / .9938 / .9934 | .9825 / .9950 / .9835 | .9788 / .9953 / .9813 |

Lecture : à débit égal, la table Y de jpegli gagne **+0,001 à +0,004 de SSIM luma** (petit mais constant), la table de chrominance est **un peu pire** (−0,000 à −0,004). Équivalent en débit : de l'ordre de **quelques % seulement**, très loin des 35 %. Limites de l'expérience : 3 images, sources déjà JPEG (biais), SSIM seul (pas de butteraugli/SSIMULACRA2, non installés), pas de photos du D40. **Conclusion établie par mesure : changer les tables seules, sans AQ ni zone morte, ne reproduit pas jpegli.** Un banc plus sérieux est facile : [libjxl/jpegli](https://github.com/google/jpegli) fournit `cjpegli` et butteraugli/ssimulacra2 dans libjxl.

### Gain attendu / à modifier / risque
- **Gain** : luma +0,2 à 0,4 % de SSIM à débit égal, ou, à qualité égale, quelques % de poids. Invisible à l'œil dans la plupart des cas. Un gain **visible** n'existe qu'en acceptant plus d'octets (table plus fine en hautes fréquences à débit constant de carte).
- **Table** : `0xA23C4` (Y) et `0xA2404` (C). Il faut d'abord lire comment Fine/Normal/Basic modifient ces tables (facteur d'échelle ? contrôle de débit par taille ?) : si le firmware ajuste les tables pour atteindre une taille cible, changer la base décale tout.
- **Risque** : faible pour la compatibilité (tables écrites dans le fichier), mais le gain est faible : **« peut-être »**, après lecture de la logique d'échelle. Sous-échantillonnage de chrominance (4:2:0 ou 4:2:2) : non vérifié sur D40 ; si c'est du 4:2:0, la chroma est déjà fortement sacrifiée et la table C compte moins.

---

## 2. Courbes de tonalité et « rendu film » : ce qui a changé depuis 2006

### Ce qui a progressé [établi]
- **Séparer scène et affichage** : traitement en RGB linéaire « scene-referred », puis mise en forme vers l'affichage par une fonction sigmoïde ; courbe en S avec **épaule douce** (roll-off) plutôt que genou dur.
- **Filmic** (Blender, 2018), **filmic RGB** de darktable/Ansel (A. Pierre), **sigmoid** (darktable 4.8), **AgX** (T. Sobotka, Blender 4) ; **ACES RRT/ODT** (cinéma, 2014+).
- **Problème des courbes par canal** : appliquer la même courbe à R, G, B tord les teintes (« notorious six ») et sature à l'approche du blanc ; l'ACES est jugé « étonnamment mauvais » à ce sujet par un développeur Blender (forum), AgX désature volontairement vers le blanc ([discussion Blender](https://devtalk.blender.org/t/blender-support-for-aces-academy-color-encoding-system/13972/209), [CG Cookie](https://cgcookie.com/comments/388687/replies/new), sources de seconde main). Les JPEG des boîtiers sont réputés faire du **par canal** (hue twist, [pixls.us](https://discuss.pixls.us/t/exposure-tone-curves-profiles-per-brand-or-camera/23367/40)) ; la même discussion note que la correspondance de rendu Fuji passe par des LUT couleur, pas par la courbe seule.

### Ce que le D40 permet exactement
La table de tonalité du D40 est une **fonction 1D appliquée par canal** (4 096 entrées 12 bits, entrée linéaire probable). C'est donc **exactement** le cas « per-channel » : tout ce qui est une fonction scalaire de l'intensité linéaire est reproductible à l'identique, sans erreur d'échantillonnage (une entrée par niveau de 12 bits). Ce qui dépend des trois canaux simultanément ne l'est pas.

### Gain attendu
- Épaule douce : **récupération de détail et de transition dans les 1,5 à 2 IL supérieurs** au lieu d'un écrêtage dur ou d'un genou brutal. Mesurable : pente de l'OECF au-dessus de 80 % du blanc, nombre de codes 8 bits distincts dans les hautes lumières, absence de plateau (palier) avant l'écrêtage.
- Le D40 a ≈ 11 EV de plage sur capteur ([apotelyt/DxO](https://apotelyt.com/camera-specs/nikon-d40-sensor-dr), secondaire) : le rendu actuel place le gris moyen (≈ 3 à 3,5 IL de marge selon CARTE) bas ; il y a de la place pour une épaule plus longue sans écraser les moyens tons.
- Les contrôles mathématiques de référence : continuité C1 (pente et valeur) à la jonction latitude/épaule ; dérivée positive partout ; pente au gris moyen fixée (contraste de référence).

### Modification
Remplacer les courbes d'un groupe (déjà prévu, `courbes.py patch`). Aucune nouvelle capacité. **Risque : faible** (le patch est un remplacement de données + le décodeur d'encodage est vérifié à l'octet près).

### Pièges (rigueur)
- **Teintes** : si la courbe est plus raide dans les ombres/moyens que le blanc, la saturation apparente (rapport max/min des canaux) change à la fois en ombres et en hautes lumières ; avec une courbe par canal un ton orangé peut virer vers le jaune en s'approchant du blanc (hue skew). Atténuer : épaule douce **peu raide**, saturation compensée par la matrice YCbCr (voir §3).
- **Surround** : un rendu « 1:1 » colorimétrique paraît plat en vision écran/papier ; l'œil compense mal une surface lumineuse par rapport à un environnement sombre (effets Hunt et Bartleson-Breneman, [glossaire Colorfront](https://engine.colorfront.cloud/glossary-of-terms), [Broadcast Bridge](https://thebroadcastbridge.com/content/entry/15535/is-gamma-still-needed-part-3)). Le gain d'un « bon » rendu n'est donc pas « moins de contraste » mais un contraste **choisi** (γ système ≈ 1,1 à 1,3 pour écran) : à justifier par une mesure, pas par goût.
- **Mesure du gain** : OECF (ISO 14524) avec un step wedge photographié ; Lab de 24 patchs ; courbe L* contre exposition ; comparaison à une cible (par exemple une courbe filmic paramétrée) par l'erreur L2 sur L*, et ΔE2000 résiduel sur patchs saturés pour montrer l'absence de dérive de teinte.

---

## 3. Matrices couleur et saturation

### Ce qui a progressé [établi]
- **Profil DNG/DCP double illuminant** : deux matrices (une pour StdA ≈ 2856 K, une pour D65), interpolées selon la température de couleur estimée ([discussion pixls.us](https://discuss.pixls.us/t/are-custom-color-matrices-still-relevant/35071) ; Adobe DNG spec). Le D40 fait déjà une version **discrète** : 18 matrices choisies par mode couleur et par type de lumière.
- **Mesure sur ColorChecker 24 patchs** et optimisation : un profil matrice seul atteint en pratique un ΔE2000 moyen autour de 3 sur la cible ([pixls.us](https://discuss.pixls.us/t/how-do-i-use-dcamprof-to-color-match-to-the-color-target-values/42788/8)) ; une LUT fait mieux sur cible mais pas « exact », et le mieux est d'utiliser les **sensibilités spectrales** du capteur plutôt qu'une mire ([DCamProf](https://rawtherapee.com/mirror/dcamprof/dcamprof-old-news.html)).
- **Adaptation chromatique** : Bradford (ICC) ou CAT16 (CIECAM16) pour ramener l'illuminant de prise de vue au point blanc D65 (sRGB) ou D50 (Adobe RGB/ICC). darktable utilise CAT16 par défaut ([channelmixerrgb.c](https://github.com/darktable-org/darktable/blob/master/src/iop/channelmixerrgb.c)).
- **Régression avancée** : corrections polynomiales (Cheung 2004), **root-polynomial** (Finlayson 2015, invariante à l'exposition) dans `colour.matrix_colour_correction` ([colour-science](https://colour.readthedocs.io/en/latest/generated/colour.characterisation.matrix_colour_correction_Finlayson2015.html)). Ces ordres élevés sont **non linéaires** donc non applicables au D40 (matrice 3×3 seulement).

### Matrice de référence existante [établi pour la valeur, probable pour la lecture]
LibRaw, `src/tables/colordata.cpp` : **Nikon D40** `{ 6992,-1668,-806,-8138,15748,2543,-874,850,7897 }` (÷10 000, matrice XYZ→caméra de type DNG pour illuminant D65 probable, issue du DNG Converter d'Adobe via dcraw). Ramenée en caméra→sRGB (D65, blanc → (1,1,1)) : lignes (1,6347 −0,5944 −0,0404 / −0,0097 1,3014 −0,2917 / 0,0076 −0,2194 1,2118), somme des lignes = 1. **Valeurs de contrôle** : comparer à la matrice « lumière du jour » du firmware (mode IIIa `g+4` ou `g+0`, §7 CARTE) pour savoir si les matrices Nikon sont déjà colorimétriques ou stylisées. Non vérifié ici (l'ordre WB/matrice dans le D40 n'est pas établi).

### Ce qui ne passe pas
- **Saturation dépendant de la luminance, de la teinte ou de la saturation** (2.5D LUT de DCamProf, HueSatMap de DCP) : non-linéaire → **impossible** sans code. Les 21 matrices RGB→YCbCr n'offrent qu'une saturation globale par niveau de contraste.
- Modèles d'apparence (CIECAM02/16) : non linéaires.

### Ce qu'on peut faire
1. **Re-fitter les matrices** : pour chaque illuminant utile (lumière du jour ≈ D55 à D65, ombre, nuageux, tungstène, fluo), photographier une mire ColorChecker + un neutre ; lire les valeurs RAW linéaires (`dcraw -D -4 -T`, NEF → linéaire, hors courbe) ; résoudre la matrice 3×3 qui minimise **ΔE2000** (pas les moindres carrés RGB) avec contrainte « lignes sommant à 1 » (conservation du neutre, donc pas de dérive de balance des blancs) ; ajouter la CAT vers D65. Contrôler que les valeurs négatives/hors gamut restent bornées.
2. Matrice **colorimétrique exacte** (sRGB) = base de comparaison (voir §4).
3. Saturation : utiliser les 21 matrices YCbCr uniquement pour un facteur **uniforme et justifié** (par exemple compensation du desaturating de l'épaule, ou +/− Chroma par la mesure C* ΔE).

### Gain attendu / risque
- Gain : un ΔE2000 moyen sur ColorChecker proche de 2–3 contre une valeur inconnue pour les matrices Nikon (qui sont volontairement stylisées : à mesurer d'abord ; **si elles sont déjà proches, le gain est nul** et le propriétaire a bien raison de ne pas tout casser).
- Risque : moyen (couleur peau). Garde-fou : conserver un ΔE2000 maximum sur peau (patchs 1–2) ≤ celui de l'origine.

---

## 4. Option « profil linéaire » (point 3 de la demande)

### Intérêt réel
Un JPEG « neutre » (colorimétrie exacte, OETF standard, aucune saturation ni contraste ajouté, netteté et réduction de bruit minimales) sert de **base de retouche** et de **banc de mesure** : on isole ce que fait chaque réglage. C'est aussi le seul état où ΔE2000 contre la mire a un sens non ambigu. Pour un photographe qui développe le NEF, l'intérêt est limité (le NEF reste la vraie base) ; pour le JPEG direct, le résultat est **volontairement terne** (voir « surround », §2), donc ce n'est pas un mode à garder en prise de vue courante.

### Pièges [établi, calculé ici]
Un JPEG 8 bits **ne doit pas être linéaire**. Nombre de codes disponibles par bande d'1 IL sous le blanc (calcul exact) :

| Bande | codes sRGB 8 bits | codes linéaires 8 bits |
|---|---|---|
| 0 à −1 IL | 68 | 128 |
| −1 à −2 | 51 | 64 |
| −2 à −3 | 37 | 32 |
| −3 à −4 | 29 | 16 |
| −4 à −5 | 21 | 8 |
| −5 à −6 | 16 | 4 |
| −6 à −7 | 12 | 2 |
| −7 à −8 | 9 | 1 |
| −8 à −9 | 6 | 0 |

En linéaire 8 bits le code 1 vaut −8 IL, et le pas de luminosité vaut **3,5 ΔL\*** à Y = 0,002 (visible, posterisation franche) contre 0,27 ΔL\* en sRGB. Donc : **pas de linéaire 8 bits**. Le « neutre » correct est la **courbe de transfert sRGB** (IEC 61966-2-1 : segment linéaire de pente 12,92 jusqu'à 0,0031308, puis 1,055·x^(1/2,4)−0,055) ; elle donne ≈ 12 EV de plage sur 8 bits avec un pas ≤ 0,5 ΔL\* jusqu'à −7 IL.

Un encodage **log** donne un nombre de codes constant par IL (≈ 25 si on code 10 IL sur 255) : bon pour pousser les ombres en retouche, mais (a) tout décodeur ordinaire l'affiche très plat, (b) 25 codes/IL dans les moyens tons est **moins** que le sRGB (≈ 50 à 70), donc plus de posterisation dans les dégradés de ciel. Pour un JPEG 8 bits, **le sRGB exact est le meilleur compromis** ; un log n'est utile qu'avec un pipeline de retouche 16 bits qui sait le décoder, ce qui n'est pas le cas d'un JPEG ordinaire.

### Comment l'obtenir dans les tables du D40 [probable, à vérifier]
1. **Courbe** : remplir la table de tonalité de 4 096 entrées avec `y = 4095·OETF_sRGB(x/4095)`, en supposant (a) entrée linéaire (CARTE, probable) et (b) aucune gamma ultérieure. **À vérifier absolument** : le rôle des tables matérielles racine/carré (`0xC860C`/`0xC660C`) est une hypothèse ; si une racine suit la courbe, la sortie sera trop claire. Test : photographier un step wedge, lire l'OECF.
   - Repère de CARTE : le Normal donne 124/255 à 1/8 de l'échelle, alors que l'OETF sRGB donne 98/255 (0,3849). La courbe usine est donc **plus claire de ≈ 26 codes dans les tons moyens-bas** (gain d'exposition et/ou S). Le « blanc » (valeur 4095) correspond-il à la saturation du capteur ou à un gain de marge (WB) ? À mesurer avant de caler la courbe neutre.
2. **Matrice caméra→RGB** : colorimétrique, §3, avec CAT vers D65, une par type de lumière, lignes sommant à 1.
3. **RGB→YCbCr** : choisir (ou ajouter) la matrice dont les coefficients valent le JFIF/BT.601 exact (0,299 / 0,587 / 0,114 ; Cb, Cr = 0,564·(B−Y), 0,713·(R−Y)). Vérifier par une lecture des 21 matrices lesquelles sont standard (la matrice « Normal » pour le niveau 3 du groupe est le candidat).
4. **Table de correction 8 bits** (`0x33692E`, colonne `+0x6AE`) : doit être **nulle** (ou neutre) pour la colonne utilisée. Rôle encore hypothétique (D-Lighting ? ISO ?).
5. **Netteté, réduction de bruit, correction d'aberration** : non pilotables par des données ; utiliser « Personnalisé » avec netteté 0 ; la réduction de bruit en longue pose/ISO haut reste active.
6. **Mode couleur** : sRGB (Ia ou IIIa) ; ne pas utiliser II (AdobeRGB) pour un profil « neutre » à moins d'étiqueter la sortie en Adobe RGB.

### Mesure
ΔE2000 par patch du ColorChecker, courbe OECF contre sRGB (écart max en codes), saturation relative C* des patchs saturés contre la cible, uniformité du gris (a\*, b\* des 6 patchs neutres < 1).

---

## 4 bis. Bruit, netteté : ce qui est faisable sans code

[Spéculatif sur le firmware, établi sur la physique.]
- **Aucune table de netteté ou de réduction de bruit n'est connue** dans CARTE : seules des **constantes** par mode scène (netteté « Auto/Faible/Normal/Moy. élevée/Élevée », contraste, saturation, teinte). On peut changer **lequel** des paliers est choisi par mode, pas le noyau de filtrage.
- Une courbe de tonalité plus raide dans les ombres **amplifie le bruit** autant que le signal (ratio inchangé) mais le rend plus visible ; une courbe plus plate dans les ombres cache le bruit **en perdant** du détail. C'est un arbitrage lisible sur l'OECF et sur le SNR mesuré (ISO 15739), pas un gain.
- Lecture bruit : le D40X a été estimé à 18 e⁻ de bruit de lecture à ISO 100 et 9 e⁻ à ISO 800 (message de forum, non vérifié, [dpreview](https://www.dpreview.com/forums/post/25893129)) ; pour le D50, 13,4 e⁻ à ISO 200 et ≈ 30 500 e⁻ de saturation ([Clarkvision](https://clarkvision.com/articles/evaluation-nikon-d50)) : donnée la plus proche du D40, à ne pas attribuer au D40 sans mesure.
- **Conclusion** : promettre « moins de bruit » ou « plus de netteté » via les tables serait une fausse promesse. Un seul levier réel : choisir un palier de netteté plus bas par défaut (moins de halos) et laisser le NEF pour le travail fin.

---

## 5. Rendu du capteur CCD et « look CCD »

- **Établi (physique générale)** : le blooming est un débordement de charge vers les pixels voisins ; les CCD interline ont des drains de débordement vertical qui échangent sensibilité contre immunité ([brevets, ex. US7808538](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/7808538)). L'ICX413AQ est un interline « frame readout » exigeant un obturateur mécanique ([DPReview](https://www.dpreview.com/articles/9510183425/sonyicx413)). Le smear (traînée verticale sous une source ponctuelle) est typique des CCD interline ; son importance sur le D40 n'est **pas mesurée ici**.
- **Établi (mesures)** : le D40 est annoncé à ≈ 11,0 EV (DxO via apotelyt, secondaire) ; base ISO 200 ; les valeurs de bruit de lecture pour le D40 lui-même n'ont pas été trouvées (voir §4 bis).
- **Le « rendu CCD » est surtout un rendu de traitement** : les discussions convergent sur le profil couleur, la balance des blancs et le traitement du boîtier plus que sur le capteur ([MPB](https://www.mpb.com/en-ie/content/kit-guides/learn-differences-between-ccd-and-cmos-sensors), [dpreview](https://www.dpreview.com/forums/post/53985689), [Photrio](https://www.photrio.com/forum/threads/ccd-vs-cmos.202674/page-2) : avis, pas des mesures). Les filtres couleur du CCD de 2006 (réponses spectrales plus étroites et plus saturées) sont la seule différence **physique** crédible sur la couleur, mais non documentée pour ce capteur.
- **Conséquence pratique** : pour retrouver ce rendu, mesurer la réponse spectrale effective (matrice caméra→XYZ) et la courbe d'usine, **ne pas inventer** de dérive de teinte « chaude ». Les 18 matrices Nikon d'origine **sont** le rendu. Les remplacer par des matrices neutres supprimera ce que les utilisateurs appellent le « look ». Décision de goût : à tester côte à côte avant.

---

## 6. NEF : compression avec perte et NEF sans perte

### Établi
- D40/D40X/D70 : NEF **uniquement compressé**, table d'encodage de **683 valeurs**, première valeur manquante 216 (Bill Claff, [photonstophotos](https://www.photonstophotos.net/NikonInfo/NEF_Compression.htm)). La première étape est **avec perte**, la seconde (Huffman sur les écarts) sans perte ; la table suit le « CIE Lightness » (moins de précision dans les hautes lumières). La table est **stockée dans le fichier** (balises MakerNote `0x8c` et `0x96`, [libopenraw](https://libopenraw.pages.freedesktop.org/formats/nef)). dcraw la décode (`nikon_compressed_load_raw`) ; Majid parle de « 12 bits ramenés à ≈ 9,4 bits de résolution » ([blog.majid.info](https://blog.majid.info/is-the-nikon-d70-nef-raw-format-truly-lossless/)).
- Tests visuels : aucune différence visible à l'écran ou en recadrage 100 %, taille ≈ moitié (16 → 8 Mo sur D200, [regex.info](https://regex.info/blog/photo-tech/nef-compression)) ; l'effet n'apparaît qu'en forte remontée des hautes lumières (postérisation possible, Claff).
- Des appareils plus récents (Z50, etc.) proposent « Lossless » qui saute l'étape de table (Claff).

### Estimation (spéculatif, ordre de grandeur) 
Entre 216 et 4 095 il reste 467 pas pour 3 879 niveaux : pas moyen ≈ 8 DN, sûrement plus élevé aux plus hauts niveaux. Bruit photonique à 3 000 DN avec 7,45 e⁻/DN (D50, [Clarkvision](https://clarkvision.com/articles/evaluation-nikon-d50)) : σ ≈ √(3000 × 7,45)/7,45 ≈ 20 DN, bruit de quantification ≈ pas/√12 ≈ 2 à 4 DN. **Quantification ≪ bruit** : c'est pourquoi c'est « visuellement sans perte ». Le D40 n'est pas plus sensible aux hautes lumières que ça.

### NEF sans perte : faisable ?
- **Table plus fine** : la table de 683 valeurs est une donnée côté firmware (position inconnue, à chercher : écrire/lire la balise `0x8c`). La rallonger exige que le codeur de Huffman accepte les écarts plus grands ; le décodeur dcraw choisit l'arbre de Huffman selon des octets de version et décode avec la table du fichier. Faisable **seulement si** le codeur lit la table depuis la RAM sans largeur figée. **Spéculatif, à ne pas promettre.**
- **NEF non compressé** : un nouveau chemin d'écriture (code), donc hors périmètre « données ».
- **Intérêt réel** : faible (quantification ≪ bruit sauf cas extrême de relevage de hautes lumières), **sauf** si le propriétaire fait systématiquement du grand relevé d'ombres/hautes lumières (rare à 12 bits, ISO ≥ 200).

---

## 7. Fouille du code d'Ansel et de darktable (point 2 de la demande)

Dépôts clonés (octobre 2026) : `darktable-org/darktable` (ff93cf6) et `aurelienpierreeng/ansel` (2fadf8a), plus `LibRaw/LibRaw`, `google/jpegli`, `libjxl/libjxl`. RawTherapee (`rtengine/dcp.cc`), DCamProf (Lumariver), OpenCV `ccm` (opencv_contrib `mcc`) et colour-science : documentation consultée, **code non lu** ici.

### Carte des modules et verdict de réduction
Critère : « réductible » = équivalent à (matrice 3×3 caméra→RGB) → (courbe 1D par canal) → (matrice 3×3 RGB→YCbCr), avec la contrainte du D40 que la courbe est **linéaire en entrée, encodée en sortie**, et que la deuxième matrice agit **après** la courbe.

| Module / fichier | Fonctions clés | Réductible ? | Pourquoi |
|---|---|---|---|
| `src/iop/colorin.c` (darktable et Ansel) | `_process_cmatrix_bm`, `_cmatrix_fastpath_simple` | **Oui** | Profil d'entrée « matrice » = 3×3 caméra→XYZ→espace de travail, précalculable (`cmatrix`/`nmatrix`/`lmatrix`). |
| `src/iop/channelmixerrgb.c` (« color calibration ») | `make_RGB_to_CAT16_LMS`, `CAT16_adapt_D50`, `DT_ADAPTATION_CAT16/BRADFORD`, `illuminant_to_XYZ` | **Oui** (en mode matrice) | La CAT est linéaire en LMS : CAT + matrice caméra = 1 matrice 3×3 par illuminant. Les modes « illuminant détecté », « spectral », « CCT continu » ne tiennent que par discrétisation (18 cases du D40). Les contrôles de gamut/chroma du module sont non linéaires. |
| `src/iop/filmicrgb.c` (darktable et Ansel) | `log_tonemapping_v2`, `filmic_spline` (poly/rationnelle, toe/latitude/shoulder), `filmic_split_v4` (**par canal**), `RGB_tone_mapping_v4` | **Oui, mode « RGB, aucun »** | `log_tonemapping_v2` + `filmic_spline` + `output_power` = une fonction scalaire de x : tabulable en 4 096 entrées 12 bits sans perte. |
| idem | `norm_tone_mapping_v4`, `filmic_chroma_v4/v5`, `get_pixel_norm`, ratios RGB | **Non** | La courbe s'applique à une **norme** (max RGB, puissance, luminance), puis on remultiplie les rapports RGB : dépend des 3 canaux. |
| idem | `RGB_to_Ych`, `filmic_desaturate_v4`, `gamut_check_RGB`, `gamut_mapping` (espace Kirk/Filmlight Yrg, LMS 2006) | **Non** | Désaturation et correction de gamut non linéaires, par pixel. |
| idem | `reconstruct_highlights`, `wavelets_reconstruct_ratios` | **Non** | Filtrage spatial par ondelettes. |
| `src/iop/sigmoid.c` (darktable) | `_generalized_loglogistic_sigmoid`, `_compute_curve`, `process_loglogistic_per_channel` | **Oui si `preserve hue` = 0 et insets/rotations = 0** | Forme fermée à 6 paramètres (contraste, skew, noir/blanc cible…) : 1D. L'**atténuation/rotation des primaires** (`_calculate_adjusted_primaries`) donne une matrice **avant** la courbe : repliable dans la matrice caméra. La « purity recovery » est une matrice **après** la courbe **en linéaire d'affichage** : non repliable exactement dans la matrice YCbCr, qui agit après un encodage (approximation à contrôler). |
| idem | `_preserve_hue_and_energy`, `_pixel_channel_order`, mode `RGB ratio` | **Non** | Tri des canaux min/mid/max par pixel : non linéaire multicanal. |
| `src/iop/agx.c` (darktable seulement ; **absent d'Ansel**) | `_apply_log_encoding`, `_apply_curve` (toe/shoulder, `_scaled_sigmoid`), `_agx_tone_mapping`, `_agx_look`, `_calculate_auto_gamma` | **En partie** | Log + sigmoïde + `pow(gamma)` par canal = 1D tabulable ; `inset` (3 coefficients par défaut 0,2946 / 0,2586 / 0,1464) = matrice avant courbe, repliable. `_agx_look` (slope/lift/power + `luma + sat·(c − luma)`) : la saturation est **un 3×3 en domaine encodé**, donc **équivalente aux 21 matrices YCbCr du D40** (au choix de pondérations de luminance près). `outset` (`rendering_to_pipe`) est appliqué **après** linéarisation (`powf(.., gamma)`) : non repliable exactement. `restore_hue` (HSV) : non. |
| `src/iop/basecurve.c` | tableaux de courbes Nikon/Canon **issus de JPEG de boîtiers**, mode « preserve colors » | **Oui** (par canal) | Même idée que la courbe usine. À utiliser comme **témoin** (courbes d'usine mesurées de boîtiers). |
| `src/iop/colorbalancergb.c`, `toneequal.c`, `exposure.c` | saturation/chroma en Ych, masque guidé, exposition | **Non** (colorbalance), **Oui** (exposition = gain, absorbé par la courbe) | `toneequal` est spatial. |

### Ce qu'Ansel apporte de plus
Ansel (fork) ne contient pas sigmoid ni AgX (vérifié par grep) ; son `filmicrgb.c` (5 860 lignes) contient les mêmes fonctions `filmic_desaturate_v1/v2`, `filmic_split`, `filmic_chroma` (version de filmic non vérifiée). Pas de gain de code par rapport à darktable pour notre usage ; la documentation d'A. Pierre (scene-referred) est la référence conceptuelle (travail en linéaire, contraste appliqué en espace log, ancrage sur le gris 18,45 %).

### Conclusion de la fouille
Tout ce qui est « courbe par canal + matrices précalculées » est transposable. Tout ce qui **évalue une norme, trie les canaux, passe par Ych/HSV, filtre spatialement ou corrige le gamut** ne l'est pas. Le sous-ensemble transposable correspond à : **filmic RGB mode « RGB »**, **sigmoid par canal sans préservation de teinte**, **AgX sans outset ni restauration de teinte**, **color calibration en matrice**, **colorin matrice**.

---

## 8. Autres projets GitHub utiles

- **LibRaw** (`src/tables/colordata.cpp`) : matrice D40 ci-dessus ; pas de profil double illuminant pour le D40.
- **google/jpegli** (`lib/jpegli/quant.cc`) : tables et facteurs lus (§1).
- **libjxl** : butteraugli, SSIMULACRA2 pour la mesure perceptuelle (à compiler pour mesurer le gain des tables).
- **RawTherapee / DCamProf** ([doc](https://rawtherapee.com/mirror/dcamprof/dcamprof-old-news.html)) : fabrication de DCP à partir de mire, opérateur de reproduction de tons « neutre », compression de gamut avant LUT (`-k`). Le D40 ne peut pas suivre la LUT, mais **la partie matrice** d'un profil DCamProf peut servir de matrice D40.
- **colour-science** : régressions (Cheung 2004, Finlayson 2015), ΔE2000, CAT16/Bradford, courbes OETF : outil de calcul et de mesure.
- **OpenCV `ccm`** (`cv::ccm::ColorCorrectionModel`, contrib `mcc`) : détection automatique de mire ColorChecker et ajustement de matrice en espaces linéaires : utile pour automatiser l'étape de mesure (non testé ici).

---

## 9. Mythes et fausses bonnes idées

1. **« Le D40 produirait de meilleures couleurs avec une LUT 3D film »** : le pipeline n'a pas de LUT 3D ; imiter une LUT par une courbe par canal + matrices crée des **dérives de teinte** (hue skew), le contraire d'un rendu rigoureux.
2. **« Effet sapin de Noël »** : saturation globale plus forte, bleus/verts déplacés « pour que ça claque » : aucun principe colorimétrique, rejeté. Toute modification de saturation doit se justifier par une cible mesurée (ΔE2000, C\*).
3. **« jpegli = −35 % de poids avec nos tables »** : faux sans AQ et zone morte (§1 : mesure).
4. **« Un NEF sans perte changera l'image »** : à 12 bits avec bruit photonique, la quantification de la table 683 est ≪ bruit (§6).
5. **« Le look CCD vient du capteur »** : surtout du traitement ; les avis (forums) divergent, aucune étude trouvée.
6. **« JPEG linéaire = neutre = meilleur à retoucher »** : en 8 bits, posterisation des ombres (3,5 ΔL\* par code à Y = 0,002). Utiliser sRGB (§4).
7. **« ACES/AgX améliorerait le JPEG »** : le gain est de tenue des hautes lumières colorées (HDR scène-référé 16–20 IL). Le D40 a ≈ 11 EV et un JPEG 8 bits : l'épaule douce suffit, un AgX complet (inset/outset) n'est pas réductible.
8. **« Modifier la netteté/le bruit par les tables »** : pas de données connues (§4 bis).
9. **« Exposer à droite »** : sans rapport avec le firmware ; ne pas le confondre avec un rendu.
10. **« Mesurer sur un seul patch gris »** : insuffisant ; il faut la mire 24 patchs et un wedge.

---

## 10. Classement final

### À faire
1. **Banc de mesure (wedge ISO 14524 + ColorChecker + lecture RAW linéaire)** : tout le reste en dépend ; dire vrai sur l'entrée de la courbe, le rôle des tables racine/carré et la matrice réelle. Pas de risque pour le boîtier.
2. **Profil neutre « sRGB exact »** (courbe OETF + matrices colorimétriques CAT-D65 + YCbCr JFIF) : référence de mesure et base de retouche, fait sans code, vérifiable (ΔE2000, OECF).
3. **Épaule douce à pente raisonnable dans les courbes** (remplacement de données, forme sigmoïde/filmic par canal, continuité C1) : gain visible sur les hautes lumières, risque faible, vérifié à l'octet.
4. **Re-fit ΔE2000 des matrices** pour les 2 ou 3 illuminants les plus utilisés, avec lignes sommant à 1 : principe colorimétrique clair ; seulement après la mesure de l'existant (si Nikon est déjà proche, ne pas toucher).

### Peut-être
1. **Table de quantification Y inspirée de jpegli** (garder la chroma Annexe K) : +0,001 à 0,004 SSIM luma à débit égal, mesuré sur 3 images ; vaut un test sur de vraies images D40 avec butteraugli, après lecture de la logique Fine/Normal/Basic.
2. **Pré-matrice « inset » AgX repliée dans la matrice caméra** : désature légèrement les couleurs hors gamut avant courbe ; bénéfice incertain sur un JPEG 8 bits, à comparer par ΔE sur patchs saturés.
3. **Matrices YCbCr pour un facteur de saturation justifié** (compensation de l'épaule) : mesurable, mais à utiliser avec parcimonie.
4. **Table NEF plus fine (683 → plus)** : seulement si on retrouve la table dans le firmware et si le codeur suit ; gain invisible sinon.

### À éviter
1. **« Rendu film » par imitation de LUT 3D** (Fuji, Kodak) : impossible proprement, dérive de teinte garantie.
2. **JPEG linéaire ou log 8 bits comme mode de sortie** : posterisation des ombres (calcul §4) ou rendu plat illisible hors pipeline dédié.
3. **Modifier netteté/bruit « à la louche »** : aucune donnée connue, fausse promesse.
4. **Prétendre au gain de jpegli, AgX complet, ACES ou 10 bits** : code d'encodeur ou non linéaire, hors périmètre.
5. **Toucher aux 18 matrices sans mesure préalable** ni fixer le « look CCD » par intuition.

---

## Sources principales

- jpegli : [blog Google](https://opensource.googleblog.com/2024/04/introducing-jpegli-new-jpeg-coding-library.html), [`google/jpegli` quant.cc](https://github.com/google/jpegli/blob/main/lib/jpegli/quant.cc)
- mozjpeg : [README](https://source-hub.etos-pro.ru/mozilla/mozjpeg/raw/branch/master/README-mozilla.txt), [libjpeg-turbo / mozjpeg](https://libjpeg-turbo.org/About/Mozjpeg), [libvips](https://www.libvips.org/API/8.17/method.Image.jpegsave.html)
- NEF : [Claff](https://www.photonstophotos.net/NikonInfo/NEF_Compression.htm), [Majid](https://blog.majid.info/is-the-nikon-d70-nef-raw-format-truly-lossless/), [regex.info](https://regex.info/blog/photo-tech/nef-compression), [libopenraw](https://libopenraw.pages.freedesktop.org/formats/nef)
- Capteur : [DPReview ICX413](https://www.dpreview.com/articles/9510183425/sonyicx413), [ICX493 (rk.edu.pl)](https://rk.edu.pl/astro/kamery-ccd/matryca/icx493aqa/), [Clarkvision D50](https://clarkvision.com/articles/evaluation-nikon-d50), [apotelyt D40](https://apotelyt.com/camera-specs/nikon-d40-sensor-dr)
- Rendu CCD : [DPReview CCD vs CMOS](https://www.dpreview.com/forums/post/53985689), [Photrio](https://www.photrio.com/forum/threads/ccd-vs-cmos.202674/page-2), [MPB](https://www.mpb.com/en-ie/content/kit-guides/learn-differences-between-ccd-and-cmos-sensors)
- Tonalité : [discussion Blender ACES/AgX](https://devtalk.blender.org/t/blender-support-for-aces-academy-color-encoding-system/13972/209), [pixls.us tone curves](https://discuss.pixls.us/t/exposure-tone-curves-profiles-per-brand-or-camera/23367/40), [Broadcast Bridge, surround](https://thebroadcastbridge.com/content/entry/15535/is-gamma-still-needed-part-3), [glossaire Colorfront](https://engine.colorfront.cloud/glossary-of-terms)
- Couleur : [pixls.us matrices](https://discuss.pixls.us/t/are-custom-color-matrices-still-relevant/35071), [DCamProf](https://rawtherapee.com/mirror/dcamprof/dcamprof-old-news.html), [colour-science](https://colour.readthedocs.io/en/latest/generated/colour.characterisation.matrix_colour_correction_Finlayson2015.html), [LibRaw colordata](https://github.com/LibRaw/LibRaw/blob/master/src/tables/colordata.cpp)
- Code : [darktable](https://github.com/darktable-org/darktable) (`src/iop/{filmicrgb,sigmoid,agx,channelmixerrgb,colorin,basecurve}.c`), [Ansel](https://github.com/aurelienpierreeng/ansel)

**Non vérifié dans cette recherche** : identité exacte du CCD du D40 ; position des tables NEF/1D du firmware ; mise à l'échelle des tables de quantification par Fine/Normal/Basic ; sous-échantillonnage chroma du D40 ; ordre exact WB → matrice ; rôle des tables racine/carré ; code de RawTherapee, OpenCV ccm, colour-science (docs lues seulement).
