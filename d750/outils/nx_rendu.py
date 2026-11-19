#!/usr/bin/env python3
"""Développer un NEF par le moteur de NX Studio, sans interface, et le comparer au JPEG du boîtier.

Méthode reprise de gerard662/nikon-picture-control-matcher (MIT, Copyright (c) 2026 Gerry Needham ; `np3lib.py`,
fonctions `render` et `nksc`) : le binaire SaveProcess de NX Studio, lancé avec `TCJ <tâche.hyd>`, développe un NEF en
TIFF 16 bits sRGB en 2 à 3 s. Un Picture Control à essayer passe par un fichier annexe `.nksc` (XMP, Picture Control
en base64 dans `nine:NineEdits`, filtre `nikon::PictureControl`). Pas une fonction officielle de Nikon : une mise à
jour de NX Studio peut la casser (installé en novembre 2026, version 1.11.0, cask `nx-studio`).

Constaté en novembre 2026 sur le D750 (recherche/veille-picture-control-2026-11.md §4) : sans fichier annexe,
SaveProcess reprend les réglages enregistrés dans le NEF, mais pas le contrôle du vignetage du boîtier. La comparaison
retire donc un gain radial (1 + a r² + b r⁴, ajusté en lumière linéaire sur l'image) avant de mesurer.

Vignetage (trouvé en novembre 2026, rd-nikon-2026-11-formats-nx.md §3) : le filtre `nikon::Vignette` du fichier annexe
prend un paramètre explicite `<integer name="intensity">` ; sans filtre le moteur applique 50. Le réglage qui colle au JPEG du
D750 dépend de l'ouverture (AF-S 28 mm f/1,8G, contrôle « Normal ») : f/1,8 → 10 (profil radial plat à 1 %), f/5,6 à f/9 → 300
(coins à ±2 %, creux de 4 % à mi-rayon). Objectif sans CPU, contrôle « Off » : ne rien passer (le défaut est déjà juste).
`rendre(..., vignetage=10)`, `--vignetage 10`.

  nx_rendu.py rendre <NEF> <sortie.tif> [--pc <fichier .NP3/.NCP/.NP2>] [--largeur 6016] [--vignetage N]
  nx_rendu.py comparer <NEF> <JPEG du boîtier> [--pc …] [--vignetage N]   ΔE2000 par blocs de 32 px, vignetage retiré
  nx_rendu.py lot <dossier rangees/ : NN-NOM.NEF + .JPG> [--pc …] [--vignetage N] [--json sortie.json]   une ligne par vue
  nx_rendu.py --self-test        génération du .nksc et du .hyd sans NX, puis un rendu de contrôle si NX est installé
"""
import argparse
import base64
import glob
import json
import os
import subprocess
import sys
import tempfile
import warnings
from xml.sax.saxutils import escape

import numpy as np

warnings.filterwarnings('ignore')
import cv2  # noqa: E402
import colour  # noqa: E402

SAVEPROCESS = '/Applications/Nikon Software/NX Studio/NX Studio.app/Contents/MacOS/SaveProcess'
TRAVAIL = os.environ.get('NX_TRAVAIL', tempfile.gettempdir())   # dossier de travail, hors de tout dossier synchronisé


# Réglages du filtre Picture Control de l'annexe, par défaut ceux de gerard662 (NP3, PictureControl=16).
PC_DEFAUT = dict(SelectedPictureControl=0, AutoContrast=255, AutoSaturation=255, SelectedPictureControlVersion2=0,
                 SavedPicConProcess=0, PictureControl=16)
VIGNETAGE_DEFAUT = 50   # valeur appliquée par le moteur quand l'annexe n'a pas de filtre nikon::Vignette (mesuré en novembre 2026)


def options_pc(pc, options=None):
    """Réglages du filtre Picture Control pour `pc`. Un NP2 (version « 02xx », celle du D750 : le NEF porte
    PictureControlVersion 0200) est imposé avec SavedPicConProcess=1 : NX Studio rend alors le NP2 bit à bit comme le NEF qui
    porte les mêmes réglages (0 de différence sur 8 vues de la séance bibliothèque, novembre 2026) ; avec 0 il s'écarte de 1 à 1,8
    code. NCP et NP3 gardent PC_DEFAUT (comportement d'avant) : passer `pc_options={'SavedPicConProcess': 1}` pour les essais."""
    o = dict(PC_DEFAUT)
    if pc is not None and pc[:4] == b'NCP\0' and pc[12:14] == b'02':
        o['SavedPicConProcess'] = 1
    o.update(options or {})
    return o


def filtre_pc(pc, options=None):
    """Filtre `nikon::PictureControl` (XML) qui impose le Picture Control `pc` (octets .NP3, .NCP ou .NP2)."""
    o = options_pc(pc, options)
    s = base64.b64encode(pc).decode()
    lignes = [s[i:i + 60] for i in range(0, len(s), 60)]
    blob = '\n'.join(lignes) + '\n'
    reglages = ''.join(f'<{k}>{v}</{k}>' for k, v in o.items() if k != 'PictureControl')
    return ('<filter id="nikon::PictureControl"><active>true</active><parameters><Export>'
            f'<ExportData>{blob}</ExportData><ExportDataSize>{len(s) + len(lignes)}</ExportDataSize></Export>'
            f'{reglages}<PictureControl>{o["PictureControl"]}</PictureControl></parameters></filter>')


def filtre_vignetage(intensite):
    """Filtre `nikon::Vignette` : contrôle du vignetage. Le paramètre est explicite (`<integer name=…>`) ; la forme
    implicite `<intensity>` est lue sans effet. Sans filtre : 50. Le rendu varie de façon monotone (mesuré de −100 à 1000)."""
    return ('<filter id="nikon::Vignette"><active>true</active><parameters>'
            f'<integer name="intensity">{int(intensite)}</integer></parameters></filter>')


def nksc(pc=None, vignetage=None, pc_options=None):
    """Fichier annexe NX Studio (texte XMP) qui impose le Picture Control `pc` (octets) et/ou l'intensité du contrôle
    du vignetage. D'après gerard662 (MIT) pour l'enveloppe et le filtre Picture Control."""
    filtres = (filtre_pc(pc, pc_options) if pc is not None else '') + (filtre_vignetage(vignetage) if vignetage is not None else '')
    esc = escape('<userData>' + filtres + '</userData>').replace('\n', '&#xA;')
    return f'''<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.5.0">
   <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about="" xmlns:sdc="http://ns.nikon.com/sdc/1.0/" xmlns:ast="http://ns.nikon.com/asteroid/1.0/" xmlns:astype="http://ns.nikon.com/asteroid/Types/1.0/" xmlns:nine="http://ns.nikon.com/nine/1.0/">
         <sdc:about>nikon sidecar/1.0</sdc:about>
         <sdc:version>1.1.0</sdc:version>
         <sdc:appversion>1.10 M</sdc:appversion>
         <sdc:appname>NX Studio</sdc:appname>
         <ast:about>core-asteroid-tags</ast:about>
         <ast:version>11.0.0.3000</ast:version>
         <nine:about>nine-tags</nine:about>
         <nine:version>2.0.0</nine:version>
         <nine:NineEdits>{esc}</nine:NineEdits>
      </rdf:Description>
   </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''


def tache_hyd(nef, sortie, sidecar=None, largeur=6016):
    """Texte du fichier de tâche `.hyd` donné à `SaveProcess TCJ`."""
    lignes = [f'InputFile={os.path.abspath(nef)}', f'OutputFile={os.path.abspath(sortie)}']
    if sidecar:
        lignes.append(f'SidecarFile={sidecar}')
    lignes += ['Format=FileType_TIFF', 'TiffOption=ColorType_RGB16', 'JpegQuality=100', f'ConvertWidth={largeur}',
               f'ConvertHeight={largeur}', 'ConvertTosRGB=1', 'UsePreview=0', 'ApplicationName=NX_Studio', 'DevelopColorMode=0',
               'UpScaleRawSize=0', 'DynamicRange=0', 'HeifOption=0', 'IsUseRGBProfileInstead=0', 'TaskTypeSet=0']
    return '\n'.join(lignes) + '\n'


def rendre(nef, sortie=None, pc=None, largeur=6016, vignetage=None, pc_options=None):
    """Développe `nef` (Picture Control `pc` en octets, ou les réglages du NEF). Renvoie l'image sRGB en flottants 0..1.
    `vignetage` : intensité du contrôle du vignetage (None = défaut du moteur, 50 ; D750 + 28 mm f/1,8G : 10 à f/1,8, 300 de f/5,6 à f/9).
    `pc_options` : réglages du filtre Picture Control de l'annexe (PC_DEFAUT), pour les essais."""
    os.makedirs(TRAVAIL, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=TRAVAIL) as d:
        out = sortie or os.path.join(d, 'o.tif')
        sc = None
        if pc is not None or vignetage is not None:
            sc = os.path.join(d, 's.nksc')
            open(sc, 'w', encoding='utf8').write(nksc(pc, vignetage, pc_options))
        job = os.path.join(d, 'j.hyd')
        open(job, 'w').write(tache_hyd(nef, out, sc, largeur))
        r = subprocess.run([SAVEPROCESS, 'TCJ', job], capture_output=True, text=True, timeout=300)
        if not os.path.exists(out):
            raise RuntimeError('SaveProcess n’a rien produit : ' + (r.stdout + r.stderr)[-400:])
        return cv2.imread(out, cv2.IMREAD_UNCHANGED)[..., ::-1].astype(np.float32) / 65535


def lire_jpeg(p):
    return cv2.imread(p, cv2.IMREAD_COLOR)[..., ::-1].astype(np.float32) / 255


def _lin(v):
    return np.where(v <= 0.04045, v / 12.92, ((np.clip(v, 0, None) + 0.055) / 1.055) ** 2.4)


def _enc(v):
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.clip(v, 0, None) ** (1 / 2.4) - 0.055)


def blocs(img, s=32):
    h, w = img.shape[0] // s * s, img.shape[1] // s * s
    r = img[:h, :w].reshape(h // s, s, w // s, s, 3)
    yy, xx = np.mgrid[0:h // s, 0:w // s]
    ray = np.hypot((yy + .5) * s - h / 2, (xx + .5) * s - w / 2) / np.hypot(h / 2, w / 2)
    return r.mean((1, 3)), r.std((1, 3)).mean(-1), ray


def comparer(nx, jpeg, s=32):
    """ΔE2000 par blocs uniformes ; vignetage (gain radial en linéaire) retiré du rendu NX avant mesure."""
    A, _, r = blocs(nx, s)
    B, sb, _ = blocs(jpeg, s)
    ok = (sb < 0.02) & (B.max(-1) < 0.97) & (B.min(-1) > 0.02) & (A.max(-1) < 0.97)
    la, lb, rr = _lin(A[ok]).mean(-1), _lin(B[ok]).mean(-1), r[ok]
    X = np.stack([np.ones_like(rr), rr ** 2, rr ** 4], 1)
    c = np.linalg.lstsq(X * la[:, None], lb, rcond=None)[0]   # lb ≈ la · (c0 + c1 r² + c2 r⁴)
    g = (X @ c)[:, None]
    A2 = np.clip(_enc(_lin(A[ok]) * g), 0, 1)
    lab = lambda v: colour.XYZ_to_Lab(colour.sRGB_to_XYZ(v))
    d = colour.delta_E(lab(A2), lab(B[ok]), method='CIE 2000')
    d0 = colour.delta_E(lab(A[ok]), lab(B[ok]), method='CIE 2000')
    centre = rr < 0.4
    return dict(blocs=int(ok.sum()), med=float(np.median(d)), p90=float(np.percentile(d, 90)), med_brut=float(np.median(d0)),
                med_centre_brut=float(np.median(d0[centre])), gain=[round(float(v), 3) for v in c],
                ecart_codes=[round(float(v), 1) for v in (A2 - B[ok]).mean(0) * 255])


def profil_radial(nx_img, jpeg, nb=8):
    """Rapport rendu NX / JPEG du boîtier (lumière linéaire) par anneaux du centre vers le coin, ramené à 1 au centre.
    1 partout = même vignetage ; le coin à 0,67 = le rendu NX par défaut sur le D750 (28 mm f/5,6), 1,02 avec vignetage=300 à f/5,6."""
    A, B = _lin(nx_img).mean(-1), _lin(jpeg).mean(-1)
    h, w = A.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - h / 2, xx - w / 2) / np.hypot(h / 2, w / 2)
    out = np.array([A[(r >= k / nb) & (r < (k + 1) / nb)].mean() / B[(r >= k / nb) & (r < (k + 1) / nb)].mean() for k in range(nb)])
    return [round(float(v), 4) for v in out / out[0]]


def exif(nef):
    """Objectif, focale, ouverture, ISO, vignetage du boîtier (exiftool)."""
    r = subprocess.run(['exiftool', '-json', '-Lens', '-LensID', '-FocalLength', '-FNumber', '-ISO', '-VignetteControl', '-ExposureTime',
                        '-WhiteBalance', nef], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)[0]
    except Exception:
        return {}


def _ligne(nom, res):
    return (f"{nom:28s} blocs {res['blocs']:5d}  ΔE00 méd {res['med']:.2f}  p90 {res['p90']:.2f}  "
            f"(sans retrait du vignetage {res['med_brut']:.2f}, centre {res['med_centre_brut']:.2f})  écart RVB {res['ecart_codes']}")


def lot(dossier, pc=None, largeur=6016, vignetage=None, sortie_json=None, pas=1, imprimer=True):
    """Une ligne par vue (NN-NOM.NEF + .JPG) ; `pas` > 1 ne prend qu'une vue sur `pas`. Renvoie la liste des résultats
    (comparer + profil radial + exif) et l'écrit en JSON si `sortie_json`, vue après vue (reprise possible à la main)."""
    res = []
    for nef in sorted(glob.glob(os.path.join(dossier, '*.NEF')))[::pas]:
        j = nef[:-4] + '.JPG'
        if not os.path.exists(j):
            continue
        img, jp = rendre(nef, None, pc, largeur, vignetage), lire_jpeg(j)
        c = comparer(img, jp)
        c.update(vue=os.path.basename(j), profil_radial=profil_radial(img, jp), exif=exif(nef), vignetage=vignetage)
        res.append(c)
        if imprimer:
            print(_ligne(c['vue'], c), flush=True)
        if sortie_json:
            json.dump(res, open(sortie_json, 'w'), ensure_ascii=False, indent=1)
    return res


def self_test():
    """Sans NX : annexe .nksc et tâche .hyd ; avec NX : un rendu de contrôle (le vignetage 300 doit éclaircir les coins)."""
    import re
    import html
    ok = True
    sc = nksc(b'NCP\0' + bytes(40), vignetage=300)
    nine = html.unescape(re.search(r'<nine:NineEdits>(.*?)</nine:NineEdits>', sc, re.S).group(1))
    ok &= nine.startswith('<userData><filter id="nikon::PictureControl">') and '<integer name="intensity">300</integer>' in nine
    ok &= nine.count('<filter ') == 2 and '<SavedPicConProcess>0</SavedPicConProcess>' in nine   # octets « NCP\0 » seuls : pas un NP2
    ok &= '<filter id="nikon::Vignette">' not in nksc(b'abc') and nksc(b'abc') == nksc(b'abc', None)
    np2 = b'NCP\0\0\0\x01\x00\0\0\0\x040200' + bytes(8)
    ok &= options_pc(np2)['SavedPicConProcess'] == 1 and options_pc(np2, {'SavedPicConProcess': 0})['SavedPicConProcess'] == 0
    ok &= options_pc(b'NCP\0\0\0\x01\x00\0\0\0\x040100' + bytes(8))['SavedPicConProcess'] == 0 and options_pc(None)['SavedPicConProcess'] == 0
    h = tache_hyd('/x/a.NEF', '/x/o.tif', '/x/s.nksc', 3000).splitlines()
    ok &= h[0] == 'InputFile=/x/a.NEF' and 'SidecarFile=/x/s.nksc' in h and 'ConvertWidth=3000' in h and 'TaskTypeSet=0' in h
    ok &= 'SidecarFile' not in tache_hyd('/x/a.NEF', '/x/o.tif')
    g = np.full((64, 64, 3), 0.5, np.float32)
    ok &= profil_radial(g, g) == [1.0] * 8
    ok &= comparer(g, g, 32)['med'] < 1e-6
    print('self-test (sans NX)', 'OK' if ok else 'ÉCHEC')
    nef = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'd750', 'images', '2026-10-seance-bibliotheque',
                       'rangees', '01-BASE_STANDARD.NEF')
    if not os.path.exists(SAVEPROCESS):
        print('self-test (NX) : SaveProcess absent, rendu ignoré')
    elif not os.path.exists(nef):
        print('self-test (NX) : NEF de contrôle absent, rendu ignoré')
    else:
        a, b = rendre(nef, largeur=1500), rendre(nef, largeur=1500, vignetage=300)
        r = lambda im: float(_lin(im[:60, :90]).mean() / _lin(im[im.shape[0] // 2 - 30:im.shape[0] // 2 + 30, im.shape[1] // 2 - 45:im.shape[1] // 2 + 45]).mean())
        print(f'self-test (NX) rapport coin/centre : défaut {r(a):.3f}, vignetage=300 {r(b):.3f}')
        ok &= a.shape == b.shape and r(b) > r(a) + 0.05
    print('self-test', 'OK' if ok else 'ÉCHEC')
    return ok


def main():
    if '--self-test' in sys.argv:
        sys.exit(0 if self_test() else 1)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('commande', choices=['rendre', 'comparer', 'lot'])
    ap.add_argument('args', nargs='+')
    ap.add_argument('--pc')
    ap.add_argument('--largeur', type=int, default=6016)
    ap.add_argument('--vignetage', type=int)
    ap.add_argument('--json')
    ap.add_argument('--pas', type=int, default=1, help='lot : une vue sur N')
    a = ap.parse_args()
    if not os.path.exists(SAVEPROCESS):
        sys.exit('SaveProcess introuvable : brew install --cask nx-studio')
    pc = open(a.pc, 'rb').read() if a.pc else None
    if a.commande == 'rendre':
        rendre(a.args[0], a.args[1], pc, a.largeur, a.vignetage)
    elif a.commande == 'comparer':
        print(_ligne(os.path.basename(a.args[1]), comparer(rendre(a.args[0], None, pc, a.largeur, a.vignetage), lire_jpeg(a.args[1]))))
    else:
        lot(a.args[0], pc, a.largeur, a.vignetage, a.json, a.pas)


if __name__ == '__main__':
    main()
