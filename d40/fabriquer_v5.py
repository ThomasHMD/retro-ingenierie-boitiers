#!/usr/bin/env python3
"""Fabrique la V5 du D40 (5 looks, menu Pip-Boy, Programmes réels en P) à partir du firmware officiel de Nikon.

Entrées : les deux téléchargements de Nikon, tels quels ou déjà extraits (l'ordre ne compte pas).
  - firmware A 1.12 : paquet « F-D40-V112W.exe » (https://downloadcenter.nikonimglib.com/en/download/fw/6.html),
    qui contient AD400112.bin ;
  - firmware B 1.11 : paquet « d40v111en.exe » (https://downloadcenter.nikonimglib.com/en/download/fw/119.html),
    qui contient BD400111.bin (et le A 1.11, inutile ici).
Les .exe sont des archives RAR auto-extractibles : elles s'ouvrent avec `unar` (brew install unar) ou `7z`, sans
rien exécuter. Un .bin déjà extrait est pris tel quel.

    python3 d40/fabriquer_v5.py <F-D40-V112W.exe ou AD400112.bin> <d40v111en.exe ou BD400111.bin> [--sortie DOSSIER]

Ce que fait le script :
  1. retrouve AD400112.bin et BD400111.bin, vérifie leur sha256 (ceux de Nikon, rien d'autre n'est accepté) et les
     range dans d40/firmware/ (hors git), où tous les outils du dossier d40/ les cherchent ;
  2. applique d40/patchs/a-programmes-112.json au A et d40/patchs/v5-programmes.json au B (patch.py : octets
     d'origine vérifiés par leur empreinte, CRC recalculé) ;
  3. écrit d40/build/V5/1-en-premier-processeur-A/AD400112.BIN et 2-ensuite-processeur-B/BD400111.BIN, puis
     vérifie qu'ils ont exactement les sha256 de la V5 flashée et testée par l'auteur.
Code de sortie 0 seulement si les deux empreintes sont les bonnes.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import patch as patchpy  # noqa: E402

V5 = {  # nom du fichier : (firmware d'origine, patchs, sous-dossier, sha256 attendu, CRC attendu)
    'AD400112.BIN': ('A112', 'a-programmes-112.json', '1-en-premier-processeur-A',
                     '45a686a71b65d964390c3d6d1095fd6e9bd5467d87bfa55b34e663b3ac8f9df2', 'ee7d'),
    'BD400111.BIN': ('B', 'v5-programmes.json', '2-ensuite-processeur-B',
                     'bfa6eb0b0e528cbc4bed37ff12c884b95029d1e5d85093e0dc43bb58c9efd1ba', '14b3'),
}
LISEZMOI = """V5 du D40 : 5 looks (Soft = Hasselblad, Vivid = Classic Chrome, More Vivid = Positive, Portrait = Tri-X,
Black And White = HP5), menu Pip-Boy, Programmes réels en P (Sujet rapide, Portrait, Street, Profondeur, Piqué max).
Pour un D40 en A 1.12 et B 1.11 (CONFIG > Version du firmware).
Deux flashs, dans l'ordre, chacun avec une carte qui ne contient que ce fichier, à la racine :
  1. 1-en-premier-processeur-A/AD400112.BIN : mise à jour du A (le boîtier doit marcher comme avant ensuite :
     faire une photo en P avant de continuer) ;
  2. 2-ensuite-processeur-B/BD400111.BIN : mise à jour du B (menus + looks + Programme envoyé au A).
Accumulateur plein. Ne pas éteindre pendant une mise à jour. Risque : un boîtier qui ne démarre plus (d40/README.md).
Retour à Nikon : choisir Programme > Standard, puis flasher les fichiers officiels de Nikon (A puis B).
sha256 :
  {a}  AD400112.BIN
  {b}  BD400111.BIN
"""


def sha(b):
    return hashlib.sha256(b).hexdigest()


def extraire(paquet, dossier):
    for outil in (['unar', '-q', '-f', '-o', str(dossier), str(paquet)], ['7z', 'x', '-y', f'-o{dossier}', str(paquet)]):
        if shutil.which(outil[0]):
            r = subprocess.run(outil, capture_output=True, text=True)
            if r.returncode == 0:
                return
    sys.exit(f"{paquet} : impossible de l'ouvrir. Installer unar (brew install unar) ou 7-Zip, ou extraire le .bin à la main")


def trouver(entrees):
    """Rend {clé de patch.py: octets} pour les originaux trouvés dans les fichiers donnés (ou leurs archives)."""
    voulus = {cle: s for cle, (_, s, _) in patchpy.ORIGINAUX.items()}
    trouves = {}
    with tempfile.TemporaryDirectory() as t:
        candidats = []
        for i, e in enumerate(entrees):
            e = Path(e)
            if not e.is_file():
                sys.exit(f'{e} introuvable')
            if e.suffix.lower() == '.bin':
                candidats.append(e)
            else:
                d = Path(t) / str(i)
                d.mkdir()
                extraire(e, d)
                candidats += [f for f in d.rglob('*') if f.is_file() and f.suffix.lower() == '.bin']
        for f in candidats:
            b = f.read_bytes()
            for cle, s in voulus.items():
                if sha(b) == s:
                    trouves[cle] = b
    return trouves


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('entrees', nargs='+', help='paquets Nikon (.exe) ou firmwares extraits (.bin)')
    ap.add_argument('--sortie', default=str(ICI / 'build' / 'V5'))
    a = ap.parse_args()
    trouves = trouver(a.entrees)
    for cle in ('A112', 'B'):
        if cle not in trouves:
            nom = patchpy.ORIGINAUX[cle][0].name
            sys.exit(f"{nom} (sha256 {patchpy.ORIGINAUX[cle][1][:12]}…) introuvable dans les fichiers donnés : "
                     "il faut le A 1.12 et le B 1.11 officiels de Nikon")
    patchpy.FIRMWARE.mkdir(parents=True, exist_ok=True)
    for cle, b in trouves.items():
        chemin = patchpy.ORIGINAUX[cle][0]
        if not chemin.is_file() or chemin.read_bytes() != b:
            chemin.write_bytes(b)
        print(f'original {cle:<4} {chemin.name} : sha256 conforme, rangé dans {patchpy.FIRMWARE}')
    sortie = Path(a.sortie)
    ok = True
    sommes = {}
    for nom, (cle, fichier, sous, attendu, crc) in V5.items():
        doc = json.loads((ICI / 'patchs' / fichier).read_text(encoding='utf-8'))
        assert doc.get('firmware', 'B') == cle, f'{fichier} : firmware {doc.get("firmware", "B")} au lieu de {cle}'
        mod = bytes(patchpy.appliquer(patchpy.charger_original(cle), doc['patchs']))
        d = sortie / sous
        d.mkdir(parents=True, exist_ok=True)
        (d / nom).write_bytes(mod)
        s = sha(mod)
        sommes[nom] = s
        bon = s == attendu and mod[-2:].hex() == crc and patchpy.crc16_xmodem(mod) == 0
        ok &= bon
        print(f'{sous}/{nom} : {len(doc["patchs"])} patchs, CRC {mod[-2:].hex()}, sha256 {s} '
              f'{"= V5 de référence" if bon else "DIFFÉRENT DE LA V5 DE RÉFÉRENCE"}')
    (sortie / 'LISEZMOI.txt').write_text(LISEZMOI.format(a=sommes['AD400112.BIN'], b=sommes['BD400111.BIN']),
                                         encoding='utf-8')
    if not ok:
        print('ÉCHEC : ne pas flasher ces fichiers')
        return 1
    print(f'V5 prête dans {sortie} (lire LISEZMOI.txt et d40/README.md avant de flasher)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
