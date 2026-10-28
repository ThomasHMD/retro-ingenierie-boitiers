#!/bin/sh
# Lot de contrôle n° 2 du D750 (de jour). Dans l'ordre :
#   1. relire C-1 à C-9 (lecture seule) et les comparer à recettes/d750/HISTORIQUE.md : un écart arrête tout ;
#   2. charger le Tri-X v2 en C-7 (recettes/d750-v2/usb/tri-x.bin ; ancien bloc sauvé, historique refait) s'il n'y est pas ;
#   3. les passages de d750_seance.swift, un par température de couleur, réglée par USB (--kelvin) puis remise.
# Scène : la bibliothèque, 28 mm à f/5,6, cadrage de la séance 4 (vignetage connu ; le lot v2 contient aussi toutes les vues
# de la page du blog). Lot v2 : 19 vues, six passages. --bibliotheque : série courte seule (lot biblio, 10 vues, trois passages). Contenu des lots : d750_seance.py, plan_v2 et plan_biblio.
# Les passages n'écrivent que C-9, remis comme avant à la fin de chacun.
#   sh outils/d750_lot_v2.sh <dossier de travail hors du dépôt> [--bibliotheque] [--simulation]
# À faire à la main : trépied, scène fixe de jour, cadrage, molette sur M de préférence, pas en U1/U2, Photos et Transfert
# d'images fermés. Le reste est réglé par USB au départ (d750_preparer.swift : WB en mode K, ISO 200, D-Lighting coupé,
# NEF + JPEG fine, f/5,6 ; vitesse : VITESSE=1/15 sh …) et remis comme avant à la fin.
# Reprise après coupure : relancer, les passages déjà rangés (rangees/ complet) sont sautés.
set -e
ICI="$(cd "$(dirname "$0")" && pwd)"
D="$1"; shift || true
[ -n "$D" ] || { sed -n '2,13p' "$0"; exit 2; }
LOT=v2; KS="5600 6250 10000 4000 5000 8000"; SIM=""
for a in "$@"; do
  case "$a" in
    --bibliotheque) LOT=biblio; KS="5600 6250 10000"; D="$D/bibliotheque" ;;
    --simulation) SIM=--simulation ;;
  esac
done
# 0. réglages de séance par USB (état de départ sauvé dans $D/preparation/avant-reglages.json)
swift "$ICI/d750_preparer.swift" "$D/preparation" ${VITESSE:+--vitesse "$VITESSE"} $SIM
# 1. relecture, toujours refaite (le boîtier a pu changer depuis la dernière fois)
R="$D/boitier-$(date +%Y%m%d-%H%M%S)"
swift "$ICI/d750_ptp.swift" "$R"
python3 "$ICI/d750_historique.py" --comparer "$R" "$D" || { echo "Boîtier différent de recettes/d750/HISTORIQUE.md : arrêt."; exit 1; }
# 2. Tri-X v2 en C-7
TRIX="$ICI/../recettes/d750-v2/usb/tri-x.bin"
if cmp -s "$R/pictctrl_207_0.bin" "$TRIX"; then
  echo "== C-7 : Tri-X v2 déjà chargé"
elif [ -n "$SIM" ]; then
  swift "$ICI/d750_ecrire.swift" ecrire "$TRIX" C-7
else
  swift "$ICI/d750_ecrire.swift" ecrire "$TRIX" C-7 --ecrire --remplacer
  python3 "$ICI/d750_historique.py"
fi
# 3. les passages
for K in $KS; do
  P="$D/$K"
  python3 "$ICI/d750_seance.py" plan "$P" --lot "$LOT-$K"
  if [ -d "$P/rangees" ] && python3 "$ICI/d750_seance.py" ranger "$P" >/dev/null 2>&1; then
    echo "== $K K : déjà fait"; continue
  fi
  echo "== $K K"
  swift "$ICI/d750_seance.swift" "$P" --kelvin "$K" --remplacer $SIM   # C-9 porte FP4+ : sauvé, remis à la fin de chaque passage
  [ -n "$SIM" ] || python3 "$ICI/d750_seance.py" ranger "$P"
done
# 4. réglages de Thomas remis
[ -n "$SIM" ] || swift "$ICI/d750_preparer.swift" "$D/preparation" --remettre
