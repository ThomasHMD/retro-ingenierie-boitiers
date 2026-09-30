#!/usr/bin/env python3
"""Séances de calibration du D750 : paires NEF + JPEG ramenées à des blocs uniformes, chaque JPEG face à son propre NEF.

Pour un lot (lot de séance, avec plan.json et rangees/NN-NOM.{NEF,JPG}) :
1. géométrie : le JPEG du boîtier est recadré, et redressé quand le contrôle auto de la distorsion est actif. On cherche,
   sur la vue 1, des points communs entre le NEF (demi-résolution, dématriçage par quadrilles 2 × 2) et le JPEG
   (SIFT + RANSAC), puis on ajuste JPEG → NEF = similitude + distorsion radiale (k1, k2, k3) sur les points retenus ;
2. blocs : grille de 24 × 24 px du JPEG ; pour chaque bloc, moyenne du JPEG (codes 0..255) et du NEF (fraction de la
   pleine échelle, noir soustrait, balance des blancs de la vue appliquée, vert = 1) échantillonné aux mêmes points ;
   écart-type de chaque côté (le tri des blocs uniformes se fait à l'analyse) ; rayon normalisé (vignetage) ;
3. une ligne par vue : même grille, même géométrie (trépied), NEF et JPEG de la vue elle-même.

  d750_blocs.py extraire <dossier du lot> <sortie.npz> [--bloc 24] [--distorsion k1,k2,k3]   (distorsion imposée : scène
      trop peu texturée, reprise d'un lot pris au même objectif)
  d750_blocs.py controle <dossier du lot> <sortie.png>    superposition NEF / JPEG recalés (contrôle visuel)
  d750_blocs.py paires <dossier NN-nom.NEF + NN-nom.JPG> <sortie.npz>   NEF du D750 face à l'export d'un autre rendu

Aucune donnée de la release n'est recopiée dans le dépôt : seuls les blocs (moyennes) servent à l'analyse.
"""
import json
import os
import sys

import numpy as np


def nef_demi(chemin):
    """NEF en demi-résolution : R, V (moyenne des deux), B par quadrille 2 × 2 ; fraction de la pleine échelle, noir
    soustrait, sans balance des blancs. Renvoie (image H/2 × W/2 × 3, balance du fichier (R, V, B, V = 1), blanc)."""
    import rawpy
    r = rawpy.imread(chemin)
    a = r.raw_image_visible.astype(np.float32)
    c = r.raw_colors_visible
    bl = np.array(r.black_level_per_channel, np.float32)
    wl = float(r.white_level)
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    out = np.zeros((h // 2, w // 2, 3), np.float32)
    n = np.zeros(3, np.float32)
    for dy in (0, 1):
        for dx in (0, 1):
            k = int(c[dy, dx])
            ch = {0: 0, 1: 1, 2: 2, 3: 1}[k]
            out[..., ch] += (a[dy:h:2, dx:w:2] - bl[k]) / (wl - bl[k])
            n[ch] += 1
    out /= n
    wb = np.array(r.camera_whitebalance[:3], float)
    return out, wb / wb[1], (a.max() - bl.max()) / (wl - bl.max())


def jpeg(chemin):
    from PIL import Image
    return np.asarray(Image.open(chemin).convert('RGB'), np.float32)


def _gris(x):
    return np.clip(x, 0, None) ** (1 / 2.2)


def geometrie(nef, jpg, distorsion=None):
    """Paramètres JPEG (pleine résolution) → NEF (demi-résolution) : [cx, cy, s, theta, k1, k2, k3] autour du centre du JPEG."""
    from skimage.feature import SIFT, match_descriptors
    from skimage.measure import ransac
    from skimage.transform import SimilarityTransform, rescale
    from scipy.optimize import least_squares
    g_r = _gris(nef.mean(2) / max(np.percentile(nef.mean(2), 99.5), 1e-6))
    g_j = rescale(jpg.mean(2) / 255, 0.5, anti_aliasing=True)
    # sous-échantillonnage supplémentaire pour la détection (vitesse), puis remise à l'échelle
    f = 0.5
    det = []
    for im in (rescale(g_r, f, anti_aliasing=True), rescale(g_j, f, anti_aliasing=True)):
        s = SIFT(n_octaves=4, n_scales=3)
        s.detect_and_extract(np.clip(im, 0, 1))
        det.append((s.keypoints[:, ::-1] / f, s.descriptors))   # (x, y) en demi-résolution
    m = match_descriptors(det[1][1], det[0][1], max_ratio=0.75, cross_check=True)
    pj, pr = det[1][0][m[:, 0]] * 2, det[0][0][m[:, 1]]   # JPEG pleine résolution, NEF demi-résolution
    mod, inl = ransac((pj, pr), SimilarityTransform, min_samples=3, residual_threshold=3, max_trials=5000)
    pj, pr = pj[inl], pr[inl]
    cj = np.array([jpg.shape[1], jpg.shape[0]]) / 2
    nrm = np.hypot(*cj)

    def proj(p, q):
        u = (q - cj) / nrm
        r2 = (u ** 2).sum(1, keepdims=True)
        u = u * (1 + p[4] * r2 + p[5] * r2 ** 2 + p[6] * r2 ** 3)
        c, s = np.cos(p[3]), np.sin(p[3])
        return np.c_[c * u[:, 0] - s * u[:, 1], s * u[:, 0] + c * u[:, 1]] * p[2] * nrm + p[:2]
    p0 = np.r_[mod(cj[None])[0], mod.scale, mod.rotation, 0, 0, 0]
    if distorsion is not None:   # peu de points (scène peu texturée) : distorsion reprise d'un autre lot, même objectif
        k = np.asarray(distorsion, float)
        r4 = least_squares(lambda p: (proj(np.r_[p, k], pj) - pr).ravel(), p0[:4], loss='soft_l1', f_scale=1)
        res = type(r4)(x=np.r_[r4.x, k])
    else:
        res = least_squares(lambda p: (proj(p, pj) - pr).ravel(), p0, loss='soft_l1', f_scale=1)
    err = np.hypot(*(proj(res.x, pj) - pr).T)
    return res.x, proj, dict(points=int(len(pj)), residu_median_px=float(np.median(err)), residu_p95_px=float(np.percentile(err, 95)))


def extraire(dossier, sortie, B=24, sous=6, distorsion=None):
    from scipy.ndimage import map_coordinates
    plan = json.load(open(os.path.join(dossier, 'plan.json'), encoding='utf-8'))['vues']
    noms = [v['nom'] for v in plan]
    fichier = lambda k, n, e: os.path.join(dossier, 'rangees', f"{k:02d}-{n.replace(' ', '_')}.{e}")
    nef, wb, _ = nef_demi(fichier(1, noms[0], 'NEF'))
    jp = jpeg(fichier(1, noms[0], 'JPG'))
    p, proj, qual = geometrie(nef * wb, jp, distorsion)
    print('géométrie', np.round(p, 5).tolist(), qual, flush=True)
    H, W = jp.shape[:2]
    ny, nx = H // B, W // B
    # points d'échantillonnage : sous × sous par bloc, au centre de sous-cases
    o = (np.arange(sous) + 0.5) * B / sous
    gy, gx = np.meshgrid(np.arange(ny) * B, np.arange(nx) * B, indexing='ij')
    forme = (ny, nx, sous, sous)
    py = np.broadcast_to(gy[..., None, None] + o[:, None], forme).reshape(-1)
    px = np.broadcast_to(gx[..., None, None] + o[None, :], forme).reshape(-1)
    q = proj(p, np.c_[px, py])
    cj = np.array([W, H]) / 2
    centres = np.c_[(gx + B / 2).ravel(), (gy + B / 2).ravel()]
    rayon = np.hypot(*((centres - cj) / np.hypot(*cj)).T)
    dedans = ((q[:, 0] > 1) & (q[:, 0] < nef.shape[1] - 2) & (q[:, 1] > 1) & (q[:, 1] < nef.shape[0] - 2)).reshape(ny * nx, -1).all(1)
    R, J, Rs, Js, WB, CL = [], [], [], [], [], []
    for k, n in enumerate(noms, 1):
        if k > 1:
            nef, wb, _ = nef_demi(fichier(k, n, 'NEF'))
            jp = jpeg(fichier(k, n, 'JPG'))
        jb = jp[:ny * B, :nx * B].reshape(ny, B, nx, B, 3).transpose(0, 2, 1, 3, 4).reshape(ny * nx, B * B, 3)
        J.append(jb.mean(1)); Js.append(jb.std(1))
        rv = np.stack([map_coordinates(nef[..., c], [q[:, 1], q[:, 0]], order=1, mode='nearest') for c in range(3)], -1)
        rb = rv.reshape(ny * nx, sous * sous, 3)
        CL.append(rb.max(1).max(1))   # maximum brut du bloc (avant balance) : repère d'écrêtage
        rb = rb * wb
        R.append(rb.mean(1)); Rs.append(rb.std(1)); WB.append(wb)
        print(f'{k:2d} {n}', flush=True)
    np.savez_compressed(sortie, noms=np.array(noms), raw=np.array(R, np.float32), raw_std=np.array(Rs, np.float32),
                        jpg=np.array(J, np.float32), jpg_std=np.array(Js, np.float32), raw_max=np.array(CL, np.float32),
                        wb=np.array(WB), rayon=rayon.astype(np.float32), centres=centres.astype(np.float32), dedans=dedans,
                        geometrie=p, qualite=json.dumps(qual), bloc=B)


def paires(dossier, sortie, B=24, sous=6):
    """Paires d'un autre rendu (NEF du D750 + JPEG exporté par un logiciel, ex. le preset Portra dans Lightroom) :
    dossier/NN-nom.NEF + dossier/NN-nom.JPG. Géométrie ajustée paire par paire (recadrage, redimensionnement, correction
    d'objectif du logiciel) ; JPEG converti en sRGB d'après son profil ICC. Mêmes blocs que `extraire`, plus l'indice
    de la paire."""
    import glob
    from scipy.ndimage import map_coordinates
    from scipy.ndimage import zoom
    nefs = sorted(glob.glob(os.path.join(dossier, '*.NEF')) + glob.glob(os.path.join(dossier, '*.nef')))
    R, J, Rs, Js, CL, I, RAY, Q = [], [], [], [], [], [], [], []
    for n, f in enumerate(nefs):
        base = os.path.splitext(f)[0]
        fj = next((base + e for e in ('.JPG', '.jpg', '.jpeg', '.JPEG') if os.path.exists(base + e)), None)
        if fj is None:
            print('sans JPEG :', f)
            continue
        nef, wb, _ = nef_demi(f)
        jp = jpeg_srgb(fj)
        if jp.shape[1] < 3000:   # export réduit : remis à l'échelle de la pleine résolution pour la recherche de points
            k = 6016 / jp.shape[1]
            jp = zoom(jp, (k, k, 1), order=1)
        try:
            p, proj, qual = geometrie(nef * wb, jp)
        except Exception as e:   # noqa: BLE001
            print('géométrie impossible :', f, e)
            continue
        if qual['points'] < 50:
            print('trop peu de points :', f, qual)
            continue
        H, W = jp.shape[:2]
        ny, nx = H // B, W // B
        o = (np.arange(sous) + 0.5) * B / sous
        gy, gx = np.meshgrid(np.arange(ny) * B, np.arange(nx) * B, indexing='ij')
        forme = (ny, nx, sous, sous)
        py = np.broadcast_to(gy[..., None, None] + o[:, None], forme).reshape(-1)
        px = np.broadcast_to(gx[..., None, None] + o[None, :], forme).reshape(-1)
        q = proj(p, np.c_[px, py])
        dedans = ((q[:, 0] > 1) & (q[:, 0] < nef.shape[1] - 2) & (q[:, 1] > 1) & (q[:, 1] < nef.shape[0] - 2)).reshape(ny * nx, -1).all(1)
        jb = jp[:ny * B, :nx * B].reshape(ny, B, nx, B, 3).transpose(0, 2, 1, 3, 4).reshape(ny * nx, B * B, 3)
        rv = np.stack([map_coordinates(nef[..., c], [q[:, 1], q[:, 0]], order=1, mode='nearest') for c in range(3)], -1)
        rb = rv.reshape(ny * nx, sous * sous, 3)
        cj = np.array([W, H]) / 2
        centres = np.c_[(gx + B / 2).ravel(), (gy + B / 2).ravel()]
        m = dedans
        J.append(jb.mean(1)[m]); Js.append(jb.std(1)[m]); CL.append(rb.max(1).max(1)[m])
        rb = rb * wb
        R.append(rb.mean(1)[m]); Rs.append(rb.std(1)[m]); I.append(np.full(int(m.sum()), n))
        RAY.append(np.hypot(*((centres - cj) / np.hypot(*cj)).T)[m]); Q.append({'nef': os.path.basename(f), **qual})
        print(os.path.basename(f), qual, flush=True)
    np.savez_compressed(sortie, raw=np.concatenate(R).astype(np.float32), raw_std=np.concatenate(Rs).astype(np.float32),
                        jpg=np.concatenate(J).astype(np.float32), jpg_std=np.concatenate(Js).astype(np.float32),
                        raw_max=np.concatenate(CL).astype(np.float32), image=np.concatenate(I), rayon=np.concatenate(RAY).astype(np.float32),
                        qualite=json.dumps(Q))


def jpeg_srgb(chemin):
    """JPEG en codes sRGB (0..255), converti depuis son profil ICC s'il en a un autre (Display P3, Adobe RGB…)."""
    import io
    from PIL import Image, ImageCms
    im = Image.open(chemin).convert('RGB')
    icc = im.info.get('icc_profile')
    if icc:
        src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        if 'srgb' not in (ImageCms.getProfileDescription(src) or '').lower():
            im = ImageCms.profileToProfile(im, src, ImageCms.createProfile('sRGB'), outputMode='RGB')
    return np.asarray(im, np.float32)


def controle(dossier, sortie):
    """Damier NEF / JPEG recalés, sur la vue 1, pour juger le recalage à l'œil."""
    from PIL import Image
    from scipy.ndimage import map_coordinates
    plan = json.load(open(os.path.join(dossier, 'plan.json'), encoding='utf-8'))['vues']
    n = plan[0]['nom'].replace(' ', '_')
    nef, wb, _ = nef_demi(os.path.join(dossier, 'rangees', f'01-{n}.NEF'))
    jp = jpeg(os.path.join(dossier, 'rangees', f'01-{n}.JPG'))
    p, proj, qual = geometrie(nef * wb, jp)
    H, W = jp.shape[:2]
    yy, xx = np.mgrid[0:H:4, 0:W:4]
    q = proj(p, np.c_[xx.ravel(), yy.ravel()])
    g = map_coordinates(_gris(nef.mean(2) * 4), [q[:, 1], q[:, 0]], order=1).reshape(xx.shape)
    j = jp[::4, ::4].mean(2) / 255
    dam = ((yy // 64 + xx // 64) % 2).astype(bool)
    Image.fromarray((np.clip(np.where(dam, g, j), 0, 1) * 255).astype(np.uint8)).save(sortie)
    print(qual)


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) >= 3 and a[0] == 'extraire':
        extraire(a[1], a[2], B=int(a[a.index('--bloc') + 1]) if '--bloc' in a else 24,
                 distorsion=[float(x) for x in a[a.index('--distorsion') + 1].split(',')] if '--distorsion' in a else None)
    elif len(a) == 3 and a[0] == 'paires':
        paires(a[1], a[2])
    elif len(a) == 3 and a[0] == 'controle':
        controle(a[1], a[2])
    else:
        print(__doc__)
        sys.exit(2)
