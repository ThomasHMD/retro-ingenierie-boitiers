#!/bin/zsh
# Régénère toute l'analyse Ghidra du firmware B du D40 à partir du binaire et des scripts.
#   desassemblage/regenerer.sh <dossier de travail hors du dépôt> [--sans-analyse]
# Produit dans le dossier de travail : projet Ghidra (ghidra-proj/), d40-tout.c (pseudo-C de
# toutes les fonctions du B), a-tout.c (idem pour le A), appels-systeme.tsv ; dans desassemblage/ : ecrans.tsv, menus.txt, liaison-a.tsv. Prérequis : Ghidra (brew), JDK 25+, extension
# ghidra-fr60 installée (NOTES-TECHNIQUES.md, « Désassemblage »).
set -e
ICI=${0:A:h}
TRAVAIL=${1:?dossier de travail}
mkdir -p "$TRAVAIL/ghidra-proj"
G=$(brew --prefix ghidra)/libexec
export JAVA_HOME=${JAVA_HOME:-/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home}
SCRIPTS="$ICI/ghidra_scripts"
if [[ "$2" == "--sans-analyse" ]]; then
  ENTREE=(-process BD400111.bin -noanalysis)
else
  ENTREE=(-import "$ICI/../firmware/BD400111.bin" -overwrite -processor "fr60:BE:16:default"
          -loader BinaryLoader -loader-baseAddr 0x40000 -preScript D40Setup.java)
fi
python3 "$ICI/../outils/menus.py" ecrans > "$ICI/ecrans.tsv"
nice "$G/support/analyzeHeadless" "$TRAVAIL/ghidra-proj" D40 "${ENTREE[@]}" -scriptPath "$SCRIPTS" \
  -postScript ResolveUTronSyscallsScript.java \
  -postScript D40Noyau.java \
  -postScript D40Menus.java \
  -postScript D40Setup.java \
  -postScript D40Syscalls.java "$TRAVAIL/appels-systeme.tsv" \
  -postScript D40ExportC.java "$TRAVAIL/d40-tout.c" > "$TRAVAIL/regenerer.log" 2>&1
# Firmware A (processeur d'exposition, chargé à 0xC0000) : petit, toujours réimporté
nice "$G/support/analyzeHeadless" "$TRAVAIL/ghidra-proj" D40 -import "$ICI/../firmware/AD400111.bin" -overwrite   -processor "fr60:BE:16:default" -loader BinaryLoader -loader-baseAddr 0xC0000 -scriptPath "$SCRIPTS"   -preScript D40ASetup.java -postScript ResolveUTronSyscallsScript.java -postScript D40ASetup.java   -postScript D40ExportC.java "$TRAVAIL/a-tout.c" >> "$TRAVAIL/regenerer.log" 2>&1
python3 "$ICI/../outils/menus.py" arbre > "$ICI/menus.txt"
python3 "$ICI/../outils/liaison_a.py" --pseudo-c "$TRAVAIL/d40-tout.c" > "$ICI/liaison-a.tsv"
grep -E 'D40[A-Za-z]* :|ERROR' "$TRAVAIL/regenerer.log" | grep -v 'Pcode error' || true
