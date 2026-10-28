# Émuler le processeur A du D40 : faisabilité (octobre 2026)

[V] = lu dans le code ou constaté dans l'émulateur ; [H] = hypothèse. Copie : `emul/emulateur/`, avec 4 classes ajoutées (`AEmu`, `AIo`, `ABoot`, `FakeB`, 940 lignes), des scénarios `a-*.txt` et un patch d'essai `emul/patchs-a/`. Classes du B intactes (`verifier` du B : 4 OK). Dépôt non modifié.

**Verdict.**
- La chaîne d'exposition du A est **testable dès maintenant** par appel direct, patchs compris, sous les gardes [V].
- La liaison fonctionne côté A avec un faux B, dans les deux sens [V].
- Le démarrage complet bute sur la mécanique et les capteurs ; il conditionne le branchement A + B.

## 1. Démarrage

Chargement à 0xC0000 ; PC = vecteur 0xFFFFC (0xC0042), TBR 0xFFC00, pile 0x3F26C ; RAM 0x3C000–0x3FFFF (16 Ko) ; registres 0x0000–0x10FF et 0x7000 [V].

Blocages successifs, et ce qui les lève [V] :

| Arrêt sans modèle | Cause | Traitement |
|---|---|---|
| boucle 0xC00B4, instruction 36 | stabilisation de l'horloge (0x482 bit 7) | forcé à 1 |
| saut en RAM 0x3EB80, garde « 0xFFFF » en 0x3EC48 (21 000) | le répartiteur REALOS (0xFF344) utilise le module de recherche de bit (0x3F4 → 0x3FC) | émulé |
| repos 0xFF01C dès 22 000 | aucune interruption : base de temps « 1 ms » (0x146/0x14A = 999, IRQ 0x2C, 0xC0444) | émulée, à 16 instructions par compte [H] |
| 0xCD65E | fin de conversion A/N (0x154 bit 6) | fin immédiate, valeur 0x200 |
| tâche 5 en `slp_tsk` (0xD488E), tâche 1 en `wai_flg` (0xC1208) | EEPROM série (0xB8–0xBF + DMA) : 1 Ko de réglages et d'étalonnage vers 0x3C000, somme en 0x3C37F | simulée au niveau des fonctions (0xD4894/0xD461E), image fabriquée |
| tâche 10 en 0xE56DC | fin de DMA (IRQ 0x2A) | DMA par blocs, 40 instructions par élément [H] |

Résultat (`a-boot-valide`, 40 M instructions en 3 s) [V] :
- 12 tâches statiques (table 0xFEB0C), dont 1 et 5 lancées d'office ; premier changement de tâche vers 20 600 instructions.
- `sta_tsk` 4/0xFFFF8082 à 36 000, mai à 721 000, 6/1 à 961 000 ; 2 500 IRQ 1 ms traitées.
- Appels au noyau : `set_flg` 11, `wai_flg` 8, `clr_flg` 7, `sta_tsk` 3. Aucune temporisation du noyau (0 `tslp_tsk` / `dly_tsk`) : tout le temps passe par l'IRQ 1 ms.

Restent trois blocages [V] :
- **Tâche 10** (capteurs) : boucle d'étalonnage 0xE4D50 (gains sur PDR4/5, 4 voies A/N, compteur 0xD4). Elle ne sort pas avec une valeur constante. `retour 0xE4D50 0` la saute (`a-boot-hle`).
- **Tâche 6** (mécanique) : attend un PPG monostable (0x1B0–0x1CB, IRQ 0x30–0x33), non émulé.
- **Tâche 1** attend la fin de la 6 (drapeau 4 bit 0x2000).

Les tâches 2, 3, 7, 9, 11 et 12 ne démarrent jamais ; la 4 (commandes du B, `molette_lire` → `expo_programme`) une seule fois.

Accès en 40 M instructions [V] :

| Bloc | Accès |
|---|---|
| ports | 2,8 M lectures, 2,8 M écritures |
| convertisseur A/N | 2,1 M lectures, 2,5 M écritures |
| compteur 0xD4 | 352 000 lectures |
| base 1 ms | 2 500 lectures, 2 508 écritures |
| ICR, DMA, PPG, liaison, série 0xC0 (objectif ? flash ?), horloge | à l'initialisation seulement |

Chien de garde (0x480/0x485) jamais écrit [V].

## 2. Liaison avec le B

**Côté A** [V] :
- Table des 48 commandes en 0xFB528 (12 octets : longueur A→B, longueur B→A, 2 octets ?, variable, tampon). Exemples :
  - 0x05 : 14 octets B→A, tampon 0x3E53F, variable 0x3D259 ;
  - 0x14 : 13 octets A→B (0x3D2B7) ;
  - 0x24 : 196 octets A→B ;
  - 0x1C : 132 octets A→B.
- Série 0 (0x60–0x63), SMR0 = 0xB2 (0xDA868) : synchrone, horloge émise, donc A maître (cohérent avec 0xB8 chez le B [H]).
- Tâche 8 (0xD9F90), lancée par l'interruption externe 4. Chaque front descendant « B prêt » fait émettre un octet au A (0xDA4C8), si PDR0 bit 4 = 0.
- Lignes : PDR9 bit 1 = B allumé (la liaison n'est armée qu'alors) ; PDR E bit 3 = requête du A.
- Bitmaps : 0x3D210 pour les envois en attente, 0x3D218 pour les réceptions, traitées par la tâche 4 (0xD1C22 : 0x3E53F → 0x3D259).
- Le A **complémente chaque octet reçu** (0xDA556), pas ceux qu'il émet.

**Faux B** [V dans l'émulateur] :
- **B→A 0x05**, 19 octets échangés :

  ```
  B : 05 0E <14 octets> 83 00 00
  A : 00 × 18, puis FF
  ```

  Somme acceptée (0x3E51A = 0xFF). Après `appel 0xD1C22`, **0x3D25B reçoit l'octet ISO auto du B** : la correspondance 974D ↔ d259, « probable », est vérifiée.
- **A→B 0x14** :

  ```
  A : 14 0D 30 5A … 54
  ```

  Le B doit rendre 0xFF au dernier octet, sinon le A réessaie 4 fois.
- Le faux B émet ~octet. Inverseur sur la ligne, ou B qui complémente : [H], à trancher avec le vrai B. Les délais (200 et 300 instructions) sont arbitraires [H].

## 3. Tester une ligne sans tout émuler

Ces fonctions ne touchent que la RAM [V] : pas besoin du démarrage.

| | Variables |
|---|---|
| Entrées | mode `3C3C0`, flash `3C3C1`, décalage `3C3C4`, `3E1E0`, ISO `3E1EE`, correction `3D0B2`, mesure `3CF68` (ou Ev `3CCC2`), focale `3D0F0`, ouvertures `3D100`/`3D0F3`, à puce `3D0E6`, plancher `3CCB9`, ISO auto `3D0BC`/`3D25B` |
| Sorties | Tv `3CCC0`, Av `3CCBE` (1/48 IL) ; finales `3CCB2`/`3CCB4` (moitiés) ; ISO `3CCBC` |

**Fonction de P (0xC60E2)**, 50 mm f/1,8 (`a-ligne-p`, 14 contrôles OK) [V] :
- conforme à la ligne d'usine : Ev 4 → 1/5 f/1,8 ; Ev 8 → 1/32 f/2,8 ; Ev 12 → 1/128 f/5,6 ; Ev 16 → 1/512 f/11 ;
- Tv0 1/256 à 80 mm, 1/512 à 202 mm ;
- butée à 1/4000 f/16 pour Ev 22.

Coût : 280 instructions et 44 octets de pile.

**Chaîne complète (0xC3F84)** (`a-expo-programme`, `a-balayage`) [V] :
- Ev 12 : 1/125 f/5,6, ISO 200.
- Près de la pleine ouverture, 0xC46BE retire 1/6 IL : Ev 6 donne Tv 188 et Av 92. `lignes.py` l'ignore.
- ISO auto (maxi 800, vitesse mini 1/125) : Ev 6 → ISO 800, 1/72 f/1,8.

Coût : 500 à 1 000 instructions, 60 octets de pile.

**Patchs** (`a-patch-ligne`) [V] :
- **Voie 1** : l'immédiat en 0xC430C passe de 0x150 à 0x1B0. Ev 12 donne alors 1/512 f/2,8.
- **Voie 2** : 10 instructions en 0xF3910, appelées par 0xC60F4 (« Sujet rapide », Tv = Ev − 4·d100). Ev 12 → 1/1290 f/1,8 ; Ev 16 → 1/4000 f/4.
- Le même patch en JSON (`"firmware": "A"`) passe par le vrai `patch.py`. Le `AD400111.BIN` produit, joué par `--firmware-a`, donne les mêmes valeurs.

## 4. Gardes

| Garde | Pour le A |
|---|---|
| Instruction non définie / 0xFFFF | telle quelle [V] (elle a révélé la recherche de bit manquante) |
| Créneau de délai interdit | telle quelle [V] : `a-garde-delai` s'arrête en 0xF391A, code 2 |
| Hors code | carte refaite : flash 0xC0000–0xFFBFF, RAM 0x3C000–0x3FFFF [V]. Zone « jamais écrite par la mise à jour » : inconnue pour le A (autre enquête) [H] |
| **Pile par tâche** (nouvelle) | haut = mot 5 de 0xFEB0C + 0x50 [V] ; piles contiguës [H] ; 176 à 384 octets ; mesuré t1 96/384, t4 68/288, t6 104/288, t10 80/368 [V]. La RAM est pleine jusqu'à 0x3FFFC : c'est le risque propre au A |
| **Écriture du code en flash** (nouvelle) | ajoutée |

## 5. Effort

| Palier | État | Reste |
|---|---|---|
| Chaîne appelable | **atteint** : `appel`, `balayage`, `--firmware-a`, `a-verifier` | 1 à 2 h : une table attendue par ligne perso |
| A qui démarre | noyau, 5 tâches, EEPROM, liaison | PPG monostable, mécanique (tâche 6 simulée ou sautée), saut de l'étalonnage, faux objectif (série 0xC0). **300 à 500 lignes, 2 à 3 jours [H]** |
| A + B branchés | non commencé | pont et lanceur commun, 250 à 350 lignes (fil B 0x50000106.4 → INT4 du A ; SODR du A → SIDR et IRQ 0x1B du B ; ~SODR du B → A ; PDR E.3 → INT1 du B [H]). **3 à 6 jours [H]**, après le palier précédent : les blocs que le B attend au démarrage (0x11, 0x14, 0x19) viennent de la tâche 4 |

## 6. Recommandation

1. **Développer la voie 2 tout de suite sur la chaîne appelable** : ligne générique et AUTO 1/f en JSON du A, une grille Ev × focale × ISO auto par `--firmware-a`, `a-verifier` sous les gardes.
2. **Compléter le démarrage jusqu'à la tâche 4 seulement**, pour mesurer la pile réelle de `molette_lire` → `expo_programme`, le principal risque restant.
3. **Brancher A + B en dernier**, pour l'écran « Programme » du B. Le transport 0x05 → `3D25B` est déjà prouvé côté A.

**Suite, octobre 2026 (nuit)** : le point 1 est fait (`outils/programmes_a.py`, scénarios `a-programmes` et `a-programmes-112`, `a-verifier` 12 sur 12 ; README, « Programme réel, mis au point dans l'émulateur »). Le point 3 est remplacé par deux demi-ponts fidèles plutôt qu'un vrai branchement : côté B, un faux A qui renvoie en écho la trame reçue sur le fil et garde un bloc d'avant l'extinction (`etata`), et le démarrage réel du B (`entree 0x50000105 0x02`) ; côté A, le vrai A face à un faux B. Le point 2 reste ouvert.

## 7. Rejouer

Depuis la racine du dépôt (compilation dans `~/Library/Caches/d40-emulateur`, ou `--travail <dossier>`) :

```
python3 emulateur/d40emu.py a-verifier                # 12 essais du A, code 0
python3 emulateur/d40emu.py a-scenario a-ligne-p      # puis a-balayage, a-expo-programme, a-patch-ligne
python3 emulateur/d40emu.py a-scenario a-garde-delai  # code 2 attendu
python3 emulateur/d40emu.py a-scenario a-boot-valide  # ou a-boot-ff, a-boot-hle
python3 emulateur/d40emu.py a-scenario a-liaison-05   # puis a-liaison-14
python3 emulateur/d40emu.py --verbeux a-demarrer 2M   # journal des E/S
python3 outils/programmes_a.py --self-test            # puis construire, scenario
python3 emulateur/d40emu.py verifier                  # le B
```
