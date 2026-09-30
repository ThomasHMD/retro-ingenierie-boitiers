#!/usr/bin/env python3
"""Images de la page du blog : la bibliothèque seulement, jamais le visage ni le pédalier.

Trois images par look, au même cadrage : l'image de départ (JPEG BASE STANDARD du boîtier), la cible calculée depuis le
NEF de cette même vue, et le JPEG du boîtier avec le Picture Control chargé. Le boîtier corrige la distorsion du JPEG, pas
le NEF : la cible est rééchantillonnée sur le cadrage du JPEG (similitude + distorsion radiale, points communs SIFT, ou
géométrie du lot 4 de modele.json pour la séance 4), vignetage corrigé comme le modèle au 28 mm. 1 200 px de large,
rendu à 2 400 puis réduit. Le modèle de distorsion ne tient qu'au centre (rapport §1.2) : le reste est recalé par un flot
optique dense (DIS) sur le JPEG de départ, contrôlé au centre et aux quatre coins. Un JPEG du boîtier décalé de plus de 2 px (à 1 200 px) par rapport au départ est refusé.

  figures_page_blog.py <status_A/> [--seance <dossier bibliotheque/>] [--x0 0.30 | --boite x0,y0,x1,y1] [--largeur 1200] [--sortie <dossier>]

--x0 : ne garder que la partie droite de l'image, à partir de cette fraction de la largeur (lot n° 2 : une chaise occupe
le quart gauche), même recadrage pour les trois images. --boite : recadrage quelconque, en fractions du JPEG tel
qu'enregistré (sans rotation). --largeur : largeur de sortie avant rotation. Les images sortent tournées selon
l'orientation EXIF du départ (vue en portrait : série de la fenêtre).

--seance : dossier d'un lot de `d750_lot_v2.sh` pris sur la bibliothèque (<dossier>/<K>/rangees/NN-NOM.{NEF,JPG}, lot v2 ou biblio) : départ, cibles et JPEG du
boîtier en une fois. Sans --seance : séance 4 d’octobre 2026, départ et cibles seulement. Sortie par défaut :
recherche/figures/page-blog/. Cibles comme d750_cibles et mesures_reelles.contexte ; KODACHROME VIF demande
D750_SPEKTRAFILM, PORTRA ESPRIT D750_LOOKS.
"""
import json
import pathlib
import subprocess
import sys

import numpy as np

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import mesures_reelles as mr  # noqa: E402  (fixe D750_LOOKS par défaut)
import d750_analyse as da  # noqa: E402
import d750_blocs as db  # noqa: E402
import d750_modele as dm  # noqa: E402

SEANCE4 = mr.RACINE / 'images' / 'd750' / '2026-10-seance-bibliotheque' / 'rangees'
SORTIE = mr.FIG / 'page-blog'
LARGEUR = 1200
# fichier → (clé de cible de la recette chargée, nom du Picture Control dans le boîtier)
LOOKS = {'tri-x': ('TRI-X', 'TRI-X'), 'classic-chrome': ('CLASSIC CHROME', 'CLASSIC_CHROME'),
         'hasselblad': ('HASSELBLAD', 'HASSELBLAD'), 'kodachrome': ('KODACHROME VIF', 'KODACHROME'),
         'portra-400': ('PORTRA ESPRIT', 'PORTRA_400'), 'classic-neg': ('CLASSIC NEG', 'CLASSIC_NEG'),
         'positive': ('POSITIVE', 'POSITIVE'), 'hp5': ('HP5', 'HP5+'), 'fp4': ('FP4', 'FP4+')}


def _exif(f):
    d = json.loads(subprocess.run(['exiftool', '-j', '-n', '-FocalLength', '-FNumber', str(f)], capture_output=True, text=True).stdout)[0]
    return d.get('FocalLength'), d.get('FNumber')


def _tourner(f):
    """Rotation d'affichage d'après l'orientation EXIF (6 : 90° horaire, 8 : 90° antihoraire, 3 : 180°)."""
    from PIL import Image
    o = json.loads(subprocess.run(['exiftool', '-j', '-n', '-Orientation', str(f)], capture_output=True, text=True).stdout)[0].get('Orientation', 1)
    t = {3: Image.ROTATE_180, 6: Image.ROTATE_270, 8: Image.ROTATE_90}.get(o)
    return (lambda im: im.transpose(t)) if t else (lambda im: im)


def _gris(im):
    return np.asarray(im.convert('L'), np.float32) / 255


def decalage(a, b):
    """Décalage (px) entre deux images de même taille, par corrélation de phase sur les bords (couleur et N&B comparables)."""
    import cv2
    ga, gb = (cv2.Laplacian(cv2.GaussianBlur(_gris(x), (0, 0), 1.5), cv2.CV_32F) for x in (a, b))
    (dx, dy), _ = cv2.phaseCorrelate(ga, gb)
    return float(np.hypot(dx, dy))


def flot_dense(depart, rendu):
    """Flot du départ vers le rendu (px de la grille), sur les bords (laplacien), égalisés : couleur et tonalité comptent peu."""
    import cv2
    a, b = ((cv2.createCLAHE(3, (8, 8)).apply((_gris(x) * 255).astype(np.uint8))) for x in (depart, rendu))
    return cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM).calc(a, b, None)


def recaler(img, flot):
    import cv2
    H, W = flot.shape[:2]
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    return cv2.remap(img, gx + flot[..., 0], gy + flot[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def decalages(a, b, c=160, marge=110):
    """Décalage (px) au centre et aux quatre coins, par corrélation de phase sur des fenêtres de c px."""
    import cv2
    ga, gb = (cv2.Laplacian(cv2.GaussianBlur(_gris(x), (0, 0), 1.5), cv2.CV_32F) for x in (a, b))
    H, W = ga.shape
    out = []
    for y, x in ((H // 2, W // 2), (marge, marge), (marge, W - marge), (H - marge, marge), (H - marge, W - marge)):
        s = slice(y - c // 2, y + c // 2), slice(x - c // 2, x + c // 2)
        (dx, dy), _ = cv2.phaseCorrelate(np.ascontiguousarray(ga[s]), np.ascontiguousarray(gb[s]))
        out.append(float(np.hypot(dx, dy)))
    return out


def main(status_a, seance=None, sortie=SORTIE, x0=0.0, boite=None, largeur=LARGEUR):
    from PIL import Image
    from scipy.ndimage import map_coordinates
    import d750_cibles as dc
    m, P, tab, Mc, k, st, C = mr.contexte(status_a)
    C.update({c: f for c, f in dc.toutes(str(status_a)).items() if c not in C})
    sortie.mkdir(parents=True, exist_ok=True)
    src = (next((pathlib.Path(seance) / '5600' / 'rangees').glob('*-BASE_STANDARD.NEF')).with_suffix('') if seance
           else SEANCE4 / '01-BASE_STANDARD')
    jpg = Image.open(f'{src}.JPG').convert('RGB')
    W, H = jpg.size
    boite = tuple(round(f * s) for f, s in zip(boite, (W, H, W, H))) if boite else (round(x0 * W), 0, W, H)
    c0, r0 = boite[:2]
    LARGEUR = largeur
    h = round(LARGEUR * (boite[3] - r0) / (boite[2] - c0))
    tourner = _tourner(f'{src}.JPG')
    depart = jpg.crop(boite).resize((LARGEUR, h), Image.LANCZOS)
    tourner(depart).save(sortie / 'depart-standard.jpg', quality=90)
    nef, wb, _ = db.nef_demi(f'{src}.NEF')
    cj = np.array([W, H]) / 2
    proj = mr._proj(cj, np.hypot(*cj))
    if seance:
        p, _, info = mr.geometrie_cv(nef, np.asarray(jpg, np.float32))
        print('géométrie :', info)
    else:
        p = np.array(m['lots']['lot4']['geometrie'])
    # grille de rendu (2 × 1 200 px) en coordonnées du JPEG plein format → coordonnées du NEF demi-résolution
    n = 2 * LARGEUR
    ys, xs = np.mgrid[0:2 * h, 0:n].astype(np.float64)
    q = np.c_[c0 + (xs.ravel() + .5) * (boite[2] - c0) / n, r0 + (ys.ravel() + .5) * (boite[3] - r0) / (2 * h)]
    xy = proj(p, q)
    x = np.stack([map_coordinates(nef[..., c], [xy[:, 1], xy[:, 0]], order=1, mode='nearest') for c in range(3)], -1) * wb
    focale, ouverture = _exif(f'{src}.NEF')
    if focale and abs(focale - 28) < 1:   # vignetage mesuré au 28 mm seulement (f/1,8 et f/5,6)
        r = np.hypot(*((q - cj) / np.hypot(*cj)).T)
        x = x * dm.vignetage(m['bases']['STANDARD']['parametres']['vig']['f18' if ouverture < 4 else 'f56'], r)[:, None]
    xyz = k * da.cam_xyz(x, Mc)
    # recalage fin : flot optique du départ vers un rendu de la scène (Hasselblad, proche du Standard en tonalité)
    ref = Image.fromarray((np.clip(dm.lab_code(C['HASSELBLAD'](xyz)).reshape(2 * h, n, 3), 0, 1) * 255 + .5).astype(np.uint8))
    flot = flot_dense(jpg.crop(boite).resize((n, 2 * h), Image.LANCZOS), ref)
    for f, (cle, _) in LOOKS.items():
        if cle not in C:
            print(f'{f} : cible {cle} absente (variable d’environnement ?)')
            continue
        code = dm.lab_code(C[cle](xyz)).reshape(2 * h, n, 3)
        im = Image.fromarray(recaler((np.clip(code, 0, 1) * 255 + .5).astype(np.uint8), flot)).resize((LARGEUR, h), Image.LANCZOS)
        tourner(im).save(sortie / f'cible-{f}.jpg', quality=90)
        print(f'cible-{f}.jpg (décalage au centre et aux coins : {", ".join(f"{d:.1f}" for d in decalages(depart, im))} px)')
    if seance:
        boitier(seance, depart, sortie, boite, tourner)


def boitier(seance, depart, sortie, boite=None, tourner=lambda im: im):
    """JPEG du boîtier de la série bibliothèque, refusé si son cadrage s'écarte de celui du départ."""
    from PIL import Image
    trouves = {f.stem.split('-', 1)[1]: f for f in pathlib.Path(seance).glob('*/rangees/*.JPG')}
    for f, (_, nom) in LOOKS.items():
        if nom == 'TRI-X' and 'TRI-X_V2' in trouves:   # lot v2 : « TRI-X » y est l'ancien, le chargé s'appelle « TRI-X V2 »
            nom = 'TRI-X_V2'
        if nom not in trouves:
            print(f'boitier-{f}.jpg : vue {nom} absente de la série')
            continue
        im = Image.open(trouves[nom]).convert('RGB')
        im = (im.crop(boite) if boite else im).resize(depart.size, Image.LANCZOS)
        d = decalage(depart, im)
        if d > 2:
            print(f'boitier-{f}.jpg REFUSÉ : cadrage décalé de {d:.1f} px par rapport au départ ({trouves[nom]})')
            continue
        tourner(im).save(sortie / f'boitier-{f}.jpg', quality=90)
        print(f'boitier-{f}.jpg ← {trouves[nom].name} (décalage {d:.1f} px)')


if __name__ == '__main__':
    a = sys.argv[1:]
    opt = {a[i]: a[i + 1] for i in range(len(a) - 1) if a[i].startswith('--')}
    pos = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or not a[i - 1].startswith('--'))]
    if len(pos) != 1:
        sys.exit(__doc__)
    main(pathlib.Path(pos[0]), opt.get('--seance'), pathlib.Path(opt.get('--sortie', SORTIE)), float(opt.get('--x0', 0)),
         [float(v) for v in opt['--boite'].split(',')] if '--boite' in opt else None, int(opt.get('--largeur', LARGEUR)))
