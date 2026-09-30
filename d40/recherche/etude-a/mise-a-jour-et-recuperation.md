# Mise à jour du processeur A du D40 : peut-on revenir en arrière ?

octobre 2026. [V] vérifié dans le code (adresses B = offset + 0x40000, A = offset + 0xC0000) ou dans l'émulateur du B, [S] source externe, [H] hypothèse.

## Verdict

**Pas de voie de secours indépendante du A.** Le code qui reçoit et écrit le nouveau firmware est celui du A en place : sa liaison, sa tâche 2, et un flasheur rangé dans sa flash, effacé puis réécrit à chaque mise à jour. Il n'y a ni chargeur protégé ni zone de démarrage préservée [V]. Le B a besoin d'un A vivant pour démarrer son interface, pour les flèches, pour la batterie, et même pour flasher le B [V]. **Un A qui ne démarre pas, c'est un boîtier perdu pour la carte** ; il ne resterait que la reprogrammation matérielle [H].

## 1. Chemin de mise à jour

**Côté B** (lu, puis joué dans l'émulateur, §3) :
1. `maj_chercherFichiers` (0xAB5CC) prend `BD40????.BIN` s'il existe, sinon `AD40????.BIN`, ouvert par `majA_ouvrir` (0xABC6E). Taille **0x40000 ou 0x40002** ; 6 octets d'en-tête lus pour l'affichage (0x83CEE984). Ni signature ni comparaison de version [V].
2. L'écran 106 n'ouvre que si l'octet de batterie **0x83CE950C** a ses bits 6-7 à 3 (ou à 1 avec bits bas < 2). Sinon, message 0x6020 ou 0x6021. **Cet octet vient du A** (commande 0x03) [V].
3. Oui : `0x1416DC` lance `maj_executer` (0xAB88E). Le fichier est chargé en 0x81000000. **CRC16 du fichier entier = 0, seulement si la taille vaut 0x40002** ; à 0x40000, aucun contrôle [V].
4. `0xABA80` met 0x40 dans 0x83CE950B, envoie la **commande 0x0D**, puis attend la **0x0E** (0x83CE9508), **sans délai de garde** :
   - bit 3 : refus, retour au menu ;
   - bit 1 : succès, réglages sauvés, 5 s, extinction (`0x40064(0xFFEF)`) ;
   - bit 2 : erreur, **extinction sans nouvel essai** [V].
5. Pendant le transfert, la fin de 0x0E (0xAA1EC) met la tâche 14 en mode transfert. Le A demande chaque bloc par la **commande 0x0F** : n = 2 et numéro N (états 0xE–0x10, 0xAAC62–0xAAD02). Le B renvoie **128 octets de 0x81000000 + N×128**, sans contrôle de borne, puis une somme [V].

**Côté A** (v1.11) :
1. 0x0D arrive en 0x3D295. `0xCEDF4` répond dans 0x3D296 : bit 6 accord, bit 3 refus (0x3D0A9 bit 7). Puis `0xCEE4C` → `0xF8114` lance la **tâche 2** (0xF8136) [V].
2. `0xF8000` arrête les tâches 1 et 4–11, met ILM à 0x10, **recopie 0xF3000–0xF3AFF en RAM à 0x3D400** et y saute [V].
3. Le flasheur demande le bloc 0 et lit l'**octet 0x40 du nouveau fichier** :
   - à 1 (v1.11 et v1.12) : il écrit 0xC0000–0xEFFFF, 0xF0000–0xF3FFF et 0xF8000–0xFFFFF, et **garde 0xF4000–0xF7FFF** ;
   - sinon : il écrit tout, cette zone comprise [V].
4. Il efface d'abord toutes ces zones (AA/55/80/AA/55/30 en 0xD5557/0xCAAAB, registres 0x7000/0x7004, au plus 10 essais), puis programme bloc par bloc en surveillant DQ7 [V].
5. Il rend compte par 0x0E : 0x42 si tout va bien, sinon 0x14 (effacement), 0x24 (programmation) ou 0x04 (liaison). Puis il **boucle sans redémarrer** en écrivant 0x11 en 0x57D, probablement le chien de garde [V].

Écrits : offsets 0x00000–0x33FFF et 0x38000–0x3FFFF (1 920 blocs), reset et noyau compris ; le CRC ne va pas au A [V].

**Zone 0xF4000–0xF7FFF.** 0xFF dans les fichiers, données propres au boîtier dans l'appareil : `0xC1E92` y lit deux clés (0xF4000, 0xF4028) pour le chiffrement NEC CIPHERUNICORN (0xF1B74) [V]. Leur usage est inconnu [H].

## 2. La v1.12

Téléchargée : `F-D40-V112W.exe` (archive RAR, ouverte avec `unar`) → `AD400112.bin`, 262 146 octets [S][Nikon](https://downloadcenter.nikonimglib.com/en/download/fw/6.html). Comparée à la 1.11 [V] :
- en-tête `01 12 01 00 09 01 16 13` (contre `01 11 00 00 08 02 14 10`) ;
- octet 0x40 à 1, CRC16 du fichier entier = 0, 0xF4000–0xF7FFF à 0xFF, reset en 0xC0042 ;
- **flasheur et copieur identiques à l'octet près** ;
- le reste est recompilé.

Image brute des 256 Ko suivie du CRC ; flasheur figé. La version affichée vient des octets 0–2 du A (`0xD1AD2`) [V]. Nikon demande un B en 1.11 et prévient qu'une coupure peut endommager le boîtier [S][guide](https://nikonimglib.com/europe/kdb/en/2009/27321/En/d40d40xa_win_en_ABF.html).

## 3. Le B a besoin du A : essais dans l'émulateur

Firmware B d'origine, copie de l'émulateur, faux A paramétrable [V] :

| Faux A | Interface | Écran 105 | Écran 106 |
|---|---|---|---|
| normal | oui | oui | refusé si 950C = 0 ; ouvert à 0xC0 |
| muet | **non** (rien n'est dessiné, 12 tâches sur 17) | non | non |
| liaison active, aucun envoi | non | non | non |
| sans 0x14 ni 0x19 | non | non | non |
| sans 0x03 | oui | oui | **refusé (batterie)** |
| mise à jour jouée | — | — | blocs identiques au fichier ; 0x42 → succès, 0x24 → erreur |

- La tâche 15 attend 0x14 et 0x19 **sans délai de garde** (`wai_flg` en 0x4D96C) [V].
- **Les flèches viennent du A** (commande 0x11) ; seuls MENU et OK sont des touches du B [V].
- **La mise à jour du B exige aussi l'accord du A** : `0xAB9F8` abandonne au bout de 500 tics [V].
- 0x14 et 0x19 seules ne suffisent pas (moment d'envoi, probablement) [H].

## 4. Verdict selon la panne

| Panne du A modifié | Retour par la carte | Confiance |
|---|---|---|
| **Ne démarre pas** (avant la liaison ou l'envoi de 0x14/0x19) | **Impossible**, ni pour le A ni pour le B. Reste le mode de programmation série des FR à flash Fujitsu (broches MD et reset) [S][Fujitsu](https://www.mikrocontroller.net/attachment/529777/FLASHMCUProgrammerforFR.pdf), si la puce en est une et si les broches sont accessibles [H], ou la carte mère | élevée |
| **Plante plus tard** | Possible si le plantage survient **après** qu'on a ouvert le menu (avec les flèches du A) et lancé la mise à jour, liaison, tâche 2, copieur et flasheur étant intacts. Le flasheur tourne interruptions masquées [V]. Si le plantage vient d'un travail périodique (mesure, interruption 0xC0444), on revient au cas précédent [H] | moyenne |
| **Répond mal** | Batterie fausse : mise à jour refusée. Flèches cassées : menu inaccessible. 0x0D acceptée puis silence : le B attend sans fin ; on éteint sans dommage si l'effacement n'a pas commencé [V] | moyenne |
| Coupure ou erreur pendant l'écriture | Boîtier perdu, comme avec la mise à jour Nikon [V] | élevée |

Antécédents [S] :
- Aucun patch connu du A pour les D40, D40x, D60, D80, D3000 ou D5000. Les patchs « bloc 0 » de Nikon Patch (A des D3100, D3200, D5100 : batteries, LCD) visent une autre puce (`nft/Nikon-Patch/LocalUI/D3100.cs`, `D5100.cs`).
- Simeon Pilgrim a perdu son D5100 avec un patch de test : « doesn't boot anymore », JTAG envisagé, carte mère à 50 % du neuf ([blog](https://simeonpilgrim.com/blog/2013/05/23/bricked-my-camera/)). Aucune récupération documentée.
- Le wiki Nikon Hacker n'existe plus que sur archive.org ([annonce](https://simeonpilgrim.com/blog/2023/11/20/nikonhacker.com%20update/)). **La Wayback Machine est injoignable d'ici** (connexion coupée) : non relu.

## 5. Conditions pour garder la voie de retour

1. **Ne jamais toucher** :
   - au reset (0xC0042) ;
   - au noyau et aux vecteurs (0xFEB00–0xFFFFF) ;
   - à la liaison côté A (table vers 0xFB52C, 0xCEDF4, 0xCEE4C) et aux commandes 0x02, 0x03, 0x11, 0x14, 0x19 ;
   - à la tâche 2 et au copieur (0xF8000–0xF8964) ;
   - au **flasheur 0xF3000–0xF3AFF** ;
   - à l'interruption 0xC0444.
2. **Octet 0x40 à 0x01 et zone 0xF4000–0xF7FFF jamais utilisée** : elle n'est jamais écrite. Les « 18 Ko libres » de `programmes-expo-iso-auto.md` en contiennent 16 inutilisables. Restent libres et sans référence [V] : 0xF2256–0xF2FFF, 0xF3B00–0xF3FFF et 0xFE0DC–0xFEAFF, soit 7,2 Ko.
3. Fichier de **0x40002 octets avec CRC**, jamais 0x40000 (accepté sans contrôle). Vérifier que seuls les octets voulus diffèrent de l'original.
4. Aucun code modifié au démarrage ni dans la liaison : le mettre derrière un **interrupteur envoyé par le B, non mémorisé, éteint par défaut**. Ainsi, un A planté redémarre sur le code d'origine. Un réglage mémorisé et renvoyé au démarrage (0x05, 0x07) transformerait un plantage en plantage au démarrage [H, fondé sur V].
5. Côté B, garder intacts les écrans 104–106, 0xAB5CC–0xABC6E, la tâche 14 et les tables 0xE482C et 0xE4B3C.
6. Monter par paliers, accumulateur plein et sans `BD40*.BIN` sur la carte :
   1. reflasher le A d'origine ;
   2. flasher un A ne changeant que des données, avec une version repère (en-tête, octet 1) visible sur l'écran 105 ;
   3. revenir à l'original ;
   4. seulement ensuite, passer au code.

## 6. Inconnues et moyen le moins risqué

| Inconnue | Moyen |
|---|---|
| Puce du A, programmation série, broches accessibles | Marquages sur les photos de la carte mère (iFixit, manuel de réparation) |
| Le flasheur du A face à un fichier modifié | Jouer 0xCEDF4 → 0xF8000 → 0xF3000 dans l'émulateur du A (autre enquête), avec un faux B et une flash simulée |
| Le vrai B face à un A muet ; boucle 0xA93B4 (ligne du A haute : la tâche 14 clignote) | Émulateur : envois retardés, 0x50000104 forcé dans `D40Io` |
| Clés en 0xF4000 ; condition de refus (0x3D0A9 bit 7) ; chien de garde 0x57D | Lecture du code du A |

Fichiers : `scripts/`, `emu/` (faux A, scénarios), `sorties/*/journal.txt`, `telechargement/extrait/D40Update/AD400112.bin`, à côté de ce rapport. Dépôt non modifié.
