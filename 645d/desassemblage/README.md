# 645D : outils de lecture du firmware 1.33

Lecture seule, hors du boîtier : rien n'est jamais renvoyé au 645D. Résultats dans [`../recherche/645d-firmware-usb.md`](../recherche/645d-firmware-usb.md).

Tout se refait depuis le fichier officiel `fwdc207b.bin` (Ricoh Imaging, version 1.33), à télécharger chez Ricoh. Le firmware décodé, le projet Ghidra et les sorties des outils vont dans un dossier de travail désigné par `P645_CHANTIER` : ce sont des dérivés du code de Ricoh.

| Fichier | Rôle |
|---|---|
| `pfw_deobf.py` | défait le brouillage XOR du fichier de mise à jour : `python3 -I pfw_deobf.py fwdc207b.bin dec.bin be 0x100 0x1000080`. Réécriture Python de l'étape « deobfuscate » de [pfwtool](https://github.com/twang2218/pentax-firmware-tool) : **GPL-2.0** ([`COPYING`](COPYING)) |
| `base.py`, `str_range.py`, `find_ptp.py`, `xref.py`, `xref2.py`, `imm.py`, `callargs.py` | repérage : base mémoire `0x10000000`, plages de textes, table des opérations PTP, références croisées, constantes immédiates, arguments d'appel |
| `frmini.py`, `proptable.py` | petit interpréteur Fujitsu FR (sous-ensemble) et table des 52 propriétés PTP qu'il en tire (type, accès, plage) |
| `scan_mono.py`, `scan_triplets.py` | recherche de matrices de mélange Monochrome ou de triplets de poids (aucune trouvée : les poids ont été mesurés sur le boîtier) |
| `P645Listing.java`, `P645Decomp.java`, `liste.sh`, `deco.sh` | Ghidra 12.2 en ligne de commande, module FR60, sans analyse automatique : listing ou décompilation d'une plage d'adresses (`P645_CHANTIER=… ./deco.sh sortie.c 0x10615238`) |

Piège connu : le module FR60 de Ghidra étend mal le signe de `ADDN2 #i4` (les octets `a1 4c` valent −12, pas +12) ; vérifier à la main tout décalage de pile négatif.
