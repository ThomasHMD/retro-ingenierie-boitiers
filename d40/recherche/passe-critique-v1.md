# Passe critique de la V1 (octobre 2026)

Thomas, en octobre 2026 : « Fais une passe critique sur ton propre travail. Le coup des hautes lumières, c'était une évidence (pourquoi perdre de l'info ?) et t'aurais dû être proactif. »

Ce document recense ce que j'ai raté, pourquoi, et ce qui est corrigé dans la V1 livrée. Il recense aussi ce qui reste incertain avant le premier essai sur le boîtier. La revue des risques propres au firmware (zones mémoire, crochets, voie de secours) est dans [`revue-critique-v1-firmware.md`](revue-critique-v1-firmware.md).

## Ce que j'aurais dû voir plus tôt

| # | Raté | Pourquoi je l'ai raté | État dans la V1 |
|---|---|---|---|
| 1 | **Hautes lumières jetées.** La courbe de Nikon atteint 98 % du blanc dès −0,28 IL sous la saturation du capteur (entrée 3368 sur 4095). Le JPEG brûle 2 à 4 fois plus de surface que le capteur. | Les courbes ont été lues en octobre (`recettes/mesures/courbes-d40.svg`). J'ai cherché à copier le rendu d'autres boîtiers, sans me demander ce que le D40 jetait. Les courbes mesurées sur le X2D, le GR ou le X-T4 reproduisent leur propre gestion du blanc, pas la marge du capteur du D40. | Corrigé : épaule film sur les 5 rendus, le blanc n'est atteint qu'à la pleine échelle. Mesuré ensuite : 80 à 100 % du blanc qui reste vient d'un capteur déjà saturé. Le vrai levier est donc l'exposition, avec la correction à −2/3 IL que Thomas règle lui-même. |
| 2 | **Contraintes du matériel vérifiées trop tard.** Les matrices de Chrome et de Positive dépassaient la plage du registre de la puce (10 bits + signe, ±1023 à l'échelle 512). | L'ajustement des rendus et le code du firmware ont été menés en parallèle, sans que la borne du registre entre dans l'ajustement. Le contrôle du build l'a arrêté, et c'est tant mieux, mais trop tard. | Corrigé : ajustement sous contrainte, borne ajoutée au contrôle de format des recettes, simulateur écrêté à la même borne. |
| 3 | **Le préréglage Nikon recyclé fuyait.** Netteté, saturation (une table de 1 024 valeurs hors de la matrice YCbCr), un demi-mot de rôle inconnu réglé par la correction des tons, la teinte. | Le choix de « recycler » 5 emplacements Nikon était bon pour le menu, mais je n'ai pas fait l'inventaire de tout ce qu'un emplacement règle dans la puce. | Corrigé par un second crochet : netteté moyennement élevée, saturation normale, réglages de tons et de teinte neutres. Témoin sans crochet : échoue. |
| 4 | **La maquette validée n'était pas respectée.** Les onglets étaient restés en pictogrammes dans la colonne verticale de Nikon. | Le README le notait comme « chantier séparé », mais je ne l'ai pas dit clairement à Thomas au moment de lui montrer le rendu. | Corrigé : les onglets sont en mots dans un bandeau en haut (étape 5, `patchs/pipboy-5-onglets.json`), et les lignes en pleine largeur. Pas fait : la ligne de résumé en bas d'écran de la maquette, faute de place sous les 7 lignes. |
| 5 | **Liens non cliquables** dans mes réponses. | Chemins écrits depuis le dossier du shell, pas depuis la racine. | Contrôle automatique (`.claude/hooks/liens-cliquables.cjs`), qui bloque la réponse tant qu'un lien est cassé. |
| 6 | **L'écran de l'émulateur présenté comme l'écran du boîtier** (vu au premier flash, en octobre 2026, vidéo `doc-youtube/2026-10_131700.mp4`). Sur le boîtier : fond bleu marine et colonne claire au lieu du noir, sous-écrans aux lignes remplies de vert (texte illisible), écran d'infos sur fond clair. | Je savais que l'émulateur ne dessine que la couche du dessin et pas le fond de l'écran d'infos (`emulateur/README.md`). Je n'ai jamais comparé une capture de l'émulateur à une photo du vrai écran, et le tuto annonçait « fond noir, texte vert ». Les sondes flashées avant ne changeaient que des données, jamais l'interface : aucune vérité terrain n'existait. | En cours : comment le boîtier compose l'écran (fond, transparence), puis émulateur calé sur la vidéo avant toute correction. |

## Revue indépendante du firmware, et ce qui en a été fait
Un agent qui n'avait pas travaillé sur le code a relu le build, octet par octet et dans le désassemblage. Son rapport complet est [`revue-critique-v1-firmware.md`](revue-critique-v1-firmware.md). Il ne relève aucun point bloquant. Il classe 4 points en « risque » et 5 en « risque faible ». Les 4 risques sont traités avant le build final, le premier en partie (voir la dernière phrase de cette section) :

| Risque relevé | Ce qui est fait | Preuve |
|---|---|---|
| Le crochet lisait la balance dans une variable globale. En rafale, une photo pouvait prendre la balance de la précédente. | La balance est lue dans la fiche de la photo (+0x4FE), où Nikon la range déjà. | Le scénario `preglages-v1` croise deux fiches de balances différentes. Un témoin construit avec l'ancienne lecture échoue. |
| La voie de secours (Version du firmware puis mise à jour) n'avait jamais été testée. | Nouveau scénario `secours`, depuis chacun des 4 onglets mémorisés, jusqu'à la question « Mise à jour? ». | Code 0 sur la V1, sur le repli et sur l'ancien menu. |
| Le bandeau d'onglets détournait deux fonctions appelées par les écrans de mise à jour. | Un sas rend la main au code Nikon d'origine sur les écrans 104 à 106. | `secours` passe ; un témoin sans le sas échoue. |
| Plusieurs firmwares périmés circulaient. | Un seul build final, au sha256 noté dans le README, avec tous les scénarios rejoués sur ce fichier exact, plus un repli sans bandeau. | Voir README, « V1 à flasher ». |

**Risques faibles, et ce qui en est fait :**
- « Réinitialiser » ne remettait pas Programme ni Si trop sombre à zéro : corrigé (voir plus bas).
- Les matrices montent jusqu'à 995, contre 969 au plus chez Nikon. La borne du registre est 1023.
- Une retouche (D-Lighting) pourrait appliquer le préréglage une seconde fois. C'est une hypothèse ; un essai facultatif est prévu dans le tuto.
- Les libellés recyclés ne sont traduits qu'en français.
- Démarrage sur un boîtier réglé en menus Simple ou Mon menu (test 8.4 de la revue) : joué. Simple est l'état de départ de l'émulateur, d'où part le scénario `secours`. Mon menu a son scénario, `mon-menu` : les quatre onglets s'affichent, PRISE DE VUE garde la liste filtrée de Nikon (sans Programme ni ISO auto, comme le code le prévoit), et CONFIG › Menus › Complet ramène au menu complet. Code 0 sur la V1 et sur le repli. Le tuto demande quand même de passer sur Complet avant le flash, le cas le plus joué.
- L'aide « ? » des nouvelles entrées est en français, affichée dans l'émulateur (scénario `pipboy` : Préréglage, Programme, ISO auto). Seul un boîtier réglé dans une autre langue n'est pas joué : ces entrées et leur aide n'existent qu'en français (test 8.3).
- Les retouches (test 8.6) et des valeurs extrêmes de matrice (test 8.7) n'ont pas été jouées dans l'émulateur. Les retouches sont laissées à l'essai D-Lighting du tuto. Les recettes ne dépassent pas 995, sous la borne de 1023.
- Le noir et blanc de Nikon cède sa place à HP5.

Corrigé en plus : « Réinitialiser » remet maintenant Programme et Si trop sombre à leur valeur de départ (scénario `reinitialiser`). Reste une globale dans le crochet, le drapeau du chemin des matrices en dur. Nikon ne le range nulle part dans la fiche. Il ne gêne que s'il change entre le calcul d'une photo et le chargement de la puce.

## Ce qui reste différent du comportement de Nikon (voulu ou accepté)
- **Contraste adaptatif.** Nikon baisse le contraste d'un cran dans les scènes les plus lumineuses, et le resserre aux ISO les plus hautes (`CARTE.md`, « classe de scène », « classe d'ISO »). Les 5 rendus ont une seule courbe, quelles que soient la scène et l'ISO. L'épaule film compense en partie pour les scènes lumineuses. À regarder sur les photos de test de la scène D (ISO 1600).
- **Métadonnées.** Le NEF et le JPEG portent les réglages réellement appliqués (netteté, saturation), mais le nom d'optimisation d'image reste celui de l'emplacement Nikon recyclé. Lightroom n'en tient pas compte par défaut.
- **Programme, Si trop sombre, ISO auto** : réglables et mémorisés, sans effet sur l'exposition tant que le processeur A n'est pas modifié. Le tuto le dit en clair.

## Ce que personne n'a encore vérifié (le premier essai le dira)
- L'image réelle : l'émulateur ne rend pas d'image. Le simulateur reproduit le JPEG du boîtier à environ 1,3 ΔE en Ia, mais les rendus V1 n'ont jamais été produits par la puce.
- L'écriture en flash à l'extinction et la relecture au démarrage (persistance de Programme).
- Le comportement pendant une vraie prise de vue : les fonctions du crochet ont été appelées à la main dans l'émulateur, dans l'ordre lu dans le code.
- La lecture, par le vrai boîtier, des zones ajoutées en fin de firmware.

## Fragilités des rendus
- Chrome repose sur 13 paires RAW + JPEG d'une seule séance du X-T4.
- HP5 n'a aucune cible mesurée : il vient des fiches Ilford, et la lecture du spectrogramme est incertaine.
- Tri-X est mesuré contre le preset Tri-X sur les exports de Thomas (ΔE 1,03), noirs bouchés compris : c'est le caractère du profil.
- Seuls 2 NEF du D40 sont marqués gardés dans Lightroom ; les planches utilisent aussi le jeu de validation du simulateur.

## Questions ouvertes (sans effet attendu sur le premier essai)
- **Le rôle du demi-mot `0x40010056`** : Nikon le règle depuis la correction des tons. Le second crochet l'écrit avec la valeur du réglage Normal, celle d'un D40 d'origine. On ne sait toujours pas ce qu'il commande.
- **Le drapeau `0x83EB3D3C`** (chemin des matrices en dur) : c'est la seule globale que le crochet lit encore. `modesScene_reglages` le tire, à chaque photo, du bit 2 de `0x83CE974C`, un réglage du boîtier et non de la photo. Nikon ne le recopie pas dans la fiche : `FUN_0004793a` recopie ce bloc à partir de `0x83CE974D`. Il ne peut donc être faux que si ce réglage change dans les menus entre la prise de vue et le développement d'une même photo. Le risque est négligeable, et une correction toucherait au code qui charge la puce : on laisse tel quel.
- **`FUN_001437ea`** : une autre remise à zéro de Nikon, dont le déclencheur n'est pas établi. Elle ne remet pas Programme et Si trop sombre à zéro. Si un jour ils reviennent à zéro sans qu'on ait choisi Réinitialiser, chercher par là.
- **La ligne de résumé en bas d'écran**, prévue par la maquette, n'est pas faite.
