#!/bin/bash
# Rapatrie la doc technique et les outils tiers des recherches D750 (Picture Control par USB, firmware), sur le Mac ou dans
# une session cloud. Relancer met à jour. Rien n'est envoyé à un boîtier.
#   bash outils/references.sh
# Où ça va (index : references/README.md) :
#   references/          docs Nikon du SDK (.pdf, .doc) et leur version texte : hors git (licence du SDK Nikon, documents
#                        marqués « Confidential »)
#   ~/Library/Caches/retro-ingenierie-boitiers (Mac) ou ~/.cache/retro-ingenierie-boitiers (ailleurs), ou $RETRO_CACHE : dépôts tiers clonés,
#                        Python avec Capstone, firmware D750 extrait ; tout se refait avec ce script
# Firmware : poser F-D750-V115M.dmg (ou .exe déjà ouvert en D750_0115.bin) dans le cache, dossier firmware/, puis relancer.
set -euo pipefail
ICI="$(cd "$(dirname "$0")/.." && pwd)"
REF="$ICI/references"
if [ -n "${RETRO_CACHE:-}" ]; then CACHE="$RETRO_CACHE"
elif [ "$(uname)" = Darwin ]; then CACHE="$HOME/Library/Caches/retro-ingenierie-boitiers"
else CACHE="$HOME/.cache/retro-ingenierie-boitiers"; fi
mkdir -p "$REF/nikon-sdk" "$REF/texte" "$CACHE/firmware"

# clone partiel d'un dépôt GitHub public : seulement les chemins utiles
clone() {
    local depot=$1 dest=$CACHE/$2; shift 2
    if [ -d "$dest/.git" ]; then git -C "$dest" pull -q --ff-only || echo "  (mise à jour de $depot impossible, copie gardée)"
    else
        git clone -q --depth 1 --filter=blob:none --sparse "https://github.com/$depot" "$dest"
        git -C "$dest" sparse-checkout set --no-cone "$@"
    fi
    echo "  $depot -> $dest"
}
echo "Dépôts tiers :"
clone simeonpilgrim/nikon-firmware-tools nikon-firmware-tools '/README.md' '/firmware decode/' '/IDA_files/D750/' '/Java/Emulator/conf/b750103a.dfr.txt' '/nfiles/'
clone WonderLantern/nikon-fw-key-tool nikon-fw-key-tool '/*'
clone gphoto/libgphoto2 libgphoto2 '/camlibs/ptp2/ptp.h' '/camlibs/ptp2/ptp.c' '/camlibs/ptp2/config.c'
clone RITMechArch/MechArch sdk-d5000 '/lib/D5000 SDK/Command/English/' '/lib/D5000 SDK/Module/Mac/Documents/English/' \
    '/lib/D5000 SDK/Module/Mac/Header Files/' '/lib/D5000 SDK/Module/Win/Sample Program/Type0003CtrlSample(Win)/'
clone cuzelac/nikon-z50-prusa sdk-z50 '/docs/sdk/Command/English/' '/docs/sdk/Module/Documents/English/' '/docs/sdk/Module/Mac/Header Files/'
clone number1nippon/SKD750Control skd750control '/docs/' '/PROJECT_CONTEXT.md'
clone Pinksert/Nikon-Picture-Control-NCP-Analysis ncp-analysis '/*'

echo "Docs Nikon du SDK -> $REF/nikon-sdk :"
copie() { if [ -f "$1" ]; then cp -p "$1" "$REF/nikon-sdk/$2"; echo "  $2"; else echo "  manquant : $2"; fi; }
copie "$CACHE/sdk-d5000/lib/D5000 SDK/Command/English/D5000UsbMtpE_01.doc" "D5000 UsbMtp (commandes USB).doc"
copie "$CACHE/sdk-d5000/lib/D5000 SDK/Command/English/D5000PcModeE_01.doc" "D5000 PcMode.doc"
copie "$CACHE/sdk-d5000/lib/D5000 SDK/Module/Mac/Documents/English/MAID3Type0003(E).pdf" "D5000 MAID3 Type0003.pdf"
copie "$CACHE/sdk-d5000/lib/D5000 SDK/Module/Win/Sample Program/Type0003CtrlSample(Win)/Function.c" "D5000 exemple Function.c"
copie "$CACHE/sdk-z50/docs/sdk/Command/English/Z 50UsbMtpE_04.pdf" "Z 50 UsbMtp (commandes USB).pdf"
copie "$CACHE/sdk-z50/docs/sdk/Module/Documents/English/MAID3(E).pdf" "MAID3 (generique).pdf"
copie "$CACHE/sdk-z50/docs/sdk/Module/Documents/English/MAID3Type0025(E).pdf" "Z 50 MAID3 Type0025.pdf"

echo "Versions texte (pour chercher dedans) -> $REF/texte :"
for f in "$REF"/nikon-sdk/*; do
    t="$REF/texte/$(basename "${f%.*}").txt"
    [ -f "$t" ] && [ "$t" -nt "$f" ] && continue
    case "$f" in
        *.doc) if command -v textutil >/dev/null; then textutil -convert txt -output "$t" "$f"
               elif command -v soffice >/dev/null; then soffice --headless --convert-to txt:Text --outdir "$REF/texte" "$f" >/dev/null 2>&1; fi ;;
        *.pdf) if command -v pdftotext >/dev/null; then pdftotext -layout "$f" "$t"
               elif [ "$(uname)" = Darwin ]; then
                   printf 'import PDFKit\nlet d = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1]))\nprint(d?.string ?? "")\n' > "$CACHE/pdf_texte.swift"
                   swift "$CACHE/pdf_texte.swift" "$f" > "$t"; fi ;;
        *) cp -p "$f" "$t" ;;
    esac
    if [ -f "$t" ]; then echo "  $(basename "$t")"; else echo "  pas de conversion pour $(basename "$f")"; fi
done

echo "Python avec Capstone (désassemblage) -> $CACHE/venv :"
[ -x "$CACHE/venv/bin/python3" ] || python3 -m venv "$CACHE/venv"
"$CACHE/venv/bin/python3" -m pip install -q --upgrade capstone && "$CACHE/venv/bin/python3" -c "import capstone; print('  capstone', capstone.__version__)"

TABLES="$CACHE/nikon-firmware-tools/firmware decode/firmware decode/Firmware.cs"
for f in "$CACHE"/firmware/F-D750-V*M.dmg "$CACHE"/firmware/D750_0*.bin; do
    [ -f "$f" ] || continue
    v=$(basename "$f" | sed -E 's/.*V?([0-9]{3,4}).*/\1/; s/^0//')
    dest="$CACHE/firmware/d750-$v"
    [ -d "$dest" ] && continue
    echo "Firmware $(basename "$f") -> $dest :"
    "$CACHE/venv/bin/python3" "$ICI/outils/d750_firmware.py" extraire "$f" "$dest" --tables "$TABLES"
done
echo "Terminé. Index : references/README.md ; analyse : recherche/d750-picture-control-usb.md"
