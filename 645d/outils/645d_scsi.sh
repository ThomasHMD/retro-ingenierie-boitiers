#!/bin/bash
# Lance 645d_scsi en root par la fenêtre d'autorisation de macOS (mot de passe tapé dans la fenêtre, rien dans le terminal).
# Attend que le 645D soit en MSC (vendeur 0x25FB, produit 0xF0), lit (lecture seule), rend les fichiers créés à l'utilisateur.
#   645d_scsi.sh [lire|lire-reglages]        (défaut : lire-reglages)
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
BIN="${TMPDIR:-/tmp}/645d_scsi"   # compilé hors du dépôt
SONDES="$(cd "$ICI/../sondes/usb" && pwd)"
ACTION="${1:-lire-reglages}"
[ -x "$BIN" ] || swiftc -O "$ICI/645d_scsi.swift" -o "$BIN" || exit 1
en_msc() { ioreg -r -c IOUSBHostDevice -d 1 -l -w0 | awk '/^\+-o/{v=0;p=0} /"idVendor" = 9723/{v=1} /"idProduct" = 240/{p=1} v&&p{f=1} END{exit !f}'; }
echo "$(date '+%H:%M:%S') j'attends le 645D en MSC (menu USB = MSC, boîtier allumé et branché)"
until en_msc; do sleep 2; done
rm -f /private/tmp/645d_scsi-journal.txt 2>/dev/null
echo "$(date '+%H:%M:%S') 645D en MSC : fenêtre de mot de passe de macOS"
sleep 3
osascript - "$BIN" "$ACTION" "$SONDES" "$(id -u):$(id -g)" <<'APPLESCRIPT'
on run argv
	set b to item 1 of argv
	set a to item 2 of argv
	set s to item 3 of argv
	set u to item 4 of argv
	do shell script (quoted form of b) & " " & a & "; c=$?; chown -R " & u & " " & (quoted form of s) & "/scsi-*; exit $c" with administrator privileges with prompt "Lecture du 645D par USB (lecture seule, aucun réglage changé) : macOS demande ton mot de passe."
end run
APPLESCRIPT
code=$?
echo "$(date '+%H:%M:%S') fin, code $code ; journal : $(ls -td "$SONDES"/scsi-* 2>/dev/null | head -1)/journal.txt"
echo "--- copie du journal (/private/tmp/645d_scsi-journal.txt) ---"; cat /private/tmp/645d_scsi-journal.txt 2>/dev/null
exit $code
