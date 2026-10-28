#!/bin/zsh
# Régénère l'analyse Ghidra du firmware B du D200 (2.01) à partir du binaire et des scripts, comme
# d40/desassemblage/regenerer.sh pour le D40.
#   d200/desassemblage/regenerer.sh <dossier de travail hors du dépôt> [--sans-analyse]
# Le binaire est pris dans le cache : ~/Library/Caches/retro-ingenierie-boitiers/firmware/d200-201/B2000201.bin
# (paquet officiel F-D200-V201W.exe ouvert avec unar ; sha256 dans d40/recherche/perspectives-d200-xt4-d750.md §1.1).
# Produit dans le dossier de travail : projet Ghidra (ghidra-proj/), d200-tout.c (pseudo-C de toutes
# les fonctions, chacune précédée de « //@@ adresse nom appelants: »), appels-systeme.tsv, regenerer.log.
# Prérequis : Ghidra (brew), JDK 25+, extension ghidra-fr60 (NOTES-TECHNIQUES.md, « Désassemblage »).
set -e
ICI=${0:A:h}
TRAVAIL=${1:?dossier de travail}
BIN=${D200_B:-$HOME/Library/Caches/retro-ingenierie-boitiers/firmware/d200-201/B2000201.bin}
mkdir -p "$TRAVAIL/ghidra-proj"
G=$(brew --prefix ghidra)/libexec
export JAVA_HOME=${JAVA_HOME:-/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home}
# scripts du D200 ici, scripts communs (noyau, export du pseudo-C) dans ceux du D40 ; Ghidra lit les deux dossiers
SCRIPTS="$ICI/ghidra_scripts;$ICI/../../d40/desassemblage/ghidra_scripts"
if [[ "$2" == "--sans-analyse" ]]; then
  ENTREE=(-process B2000201.bin -noanalysis)
else
  ENTREE=(-import "$BIN" -overwrite -processor "fr60:BE:16:default"
          -loader BinaryLoader -loader-baseAddr 0x50000 -preScript D200Setup.java)
fi
nice "$G/support/analyzeHeadless" "$TRAVAIL/ghidra-proj" D200 "${ENTREE[@]}" -scriptPath "$SCRIPTS" \
  -postScript ResolveUTronSyscallsScript.java \
  -postScript D200Setup.java \
  -postScript D40Syscalls.java "$TRAVAIL/appels-systeme.tsv" \
  -postScript D40ExportC.java "$TRAVAIL/d200-tout.c" > "$TRAVAIL/regenerer.log" 2>&1
grep -E 'D200Setup :|D40ExportC :|ERROR' "$TRAVAIL/regenerer.log" | grep -v 'Pcode error' || true
