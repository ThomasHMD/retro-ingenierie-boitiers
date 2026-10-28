#!/usr/bin/env python3
"""Vues de démonstration du 645D : le JPEG pleine taille embarqué dans chaque PEF de la séance de mesure (rendu du boîtier,
Custom Image du moment), réduit à 1600 px et sans aucune métadonnée (ni EXIF, ni XMP, ni commentaire).

  python3 645d/outils/645d_vues_demo.py <dossier des PEF de mesure> <sortie>

Une vue par look, toutes de la même scène sur trépied (le pédalier) : seuls les réglages changent. Les recettes Tri-X
(contraste +3) et HP5 (contraste +4) n'ont pas de vue exacte : on montre la plus proche, mesurée, et la légende le dit.
Demande : exiftool (extraction du JPEG) et Pillow.
"""
import io
import pathlib
import subprocess
import sys

from PIL import Image

VUES = {   # nom publié : début du nom du PEF (plan de 645d/sondes/usb/seance-…/plan-mesure-2.json)
    'depart-naturel': '18-mode-0',                 # Naturel, tout à 0 : la référence couleur
    'boitier-classic-chrome': '29-naturel-teinte-2',   # recette exacte : Naturel, teinte −2
    'boitier-portra-400': '19-mode-1',             # recette exacte : Lumineux, tout à 0
    'depart-monochrome': '01-mono-filtre-0-aucun',  # Monochrome d'origine : la référence noir et blanc
    'boitier-tri-x-400': '12-mono-contraste-6',     # contraste +2 (la recette est à +3)
    'boitier-hp5-plus': '08-mono-filtre-7-cyan',    # filtre cyan, contraste 0 (la recette est à +4)
}
COTE = 1600


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    source, sortie = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    sortie.mkdir(parents=True, exist_ok=True)
    for nom, debut in VUES.items():
        pef = next(source.glob(f'{debut}-*.PEF'))
        jpeg = subprocess.run(['exiftool', '-b', '-JpgFromRaw', str(pef)], capture_output=True, check=True).stdout
        im = Image.open(io.BytesIO(jpeg)).convert('RGB')
        im.thumbnail((COTE, COTE), Image.LANCZOS)
        im.save(sortie / f'{nom}.jpg', 'JPEG', quality=85, optimize=True)   # Pillow n'écrit aucune métadonnée par défaut
        print(f'{nom}.jpg  ← {pef.name}  {im.size[0]} × {im.size[1]}')


if __name__ == '__main__':
    main()
