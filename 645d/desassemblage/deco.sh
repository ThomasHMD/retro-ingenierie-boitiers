#!/bin/zsh
# deco.sh <sortie.c> <adresse> ...  : décompile dans le projet Ghidra existant (sans analyse)
C="${P645_CHANTIER:?dossier de travail hors du dépôt : work/dec.bin et ghidra-proj/ (voir README)}"
G=$(brew --prefix ghidra)/libexec
export JAVA_HOME=/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home
OUT=$1; shift
nice "$G/support/analyzeHeadless" "$C/ghidra-proj" P645 -process dec.bin -noanalysis -scriptPath "$(cd "$(dirname "$0")" && pwd)" -postScript P645Decomp.java "$OUT" "$@" > "$C/work/ghidra-last.log" 2>&1
grep -E "ERROR|Exception" "$C/work/ghidra-last.log" | head -5
cat "$OUT"
