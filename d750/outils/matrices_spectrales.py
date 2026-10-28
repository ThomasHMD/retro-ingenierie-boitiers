#!/usr/bin/env python3
"""Matrices couleur du D40 calculées d'après ses sensibilités spectrales mesurées (sans ColorChecker).

Source des sensibilités : base camspec, Jiang, Liu, Gu, Süsstrunk, « What is the space of spectral
sensitivity functions for digital color cameras? », WACV 2013 (EPFL), Zenodo 3245883, CC BY-NC-SA 4.0.
33 valeurs par canal, 400 à 720 nm par pas de 10 nm. Le fichier n'est pas recopié ici : chemin en argument.

Méthode : réflectances spectrales de la ColorChecker (colour-science, mesures Ohta) × illuminant →
RGB caméra (équilibré sur le blanc parfait) et XYZ (CIE 1931 2°, adapté en D65 par Bradford) ;
matrice 3x3 qui garde le blanc, ajustée au moindre ΔE2000 moyen. Puis on note les 18 matrices du
firmware (0x332888, échelle 512, caméra → sRGB linéaire) sur le même critère.

  matrices_spectrales.py <camspec.txt>              matrices et ΔE2000 par illuminant
  matrices_spectrales.py <camspec.txt> --self-test
"""
import argparse
import pathlib
import struct
import sys

import numpy as np
import colour
from scipy.optimize import minimize

ICI = pathlib.Path(__file__).resolve().parent.parent
FIRMWARE = ICI / 'firmware' / 'BD400111.bin'
BASE = 0x40000
MATRICES = 0x332888
FORME = colour.SpectralShape(400, 720, 10)
XYZ_VERS_SRGB = colour.RGB_COLOURSPACES['sRGB'].matrix_XYZ_to_RGB
D65 = colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65']


def lire_camspec(chemin, nom='Nikon D40'):
    lignes = pathlib.Path(chemin).read_text().splitlines()
    i = [k for k, l in enumerate(lignes) if l.strip() == nom][0]
    return np.array([[float(v) for v in lignes[i + 1 + c].split()] for c in range(3)])  # 3 × 33


def matrices_firmware():
    b = FIRMWARE.read_bytes()
    o = MATRICES - BASE
    return [np.array(struct.unpack('>9h', b[o + 18 * n:o + 18 * n + 18])).reshape(3, 3) / 512 for n in range(18)]


def donnees(sens, illuminant):
    """RGB caméra équilibré et XYZ D65 (Y blanc = 1) des 24 patchs."""
    cmf = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer'].copy().align(FORME).values  # 33 × 3
    E = colour.SDS_ILLUMINANTS[illuminant].copy().align(FORME).values
    cc = colour.SDS_COLOURCHECKERS['ColorChecker N Ohta']
    R = np.array([sd.copy().align(FORME).values for sd in cc.values()])  # 24 × 33
    rgb = (R * E) @ sens.T
    rgb /= E @ sens.T  # blanc parfait = (1, 1, 1) : équivaut à la balance des blancs
    xyz = (R * E) @ cmf / (E @ cmf[:, 1])
    blanc = E @ cmf / (E @ cmf[:, 1])
    xyz = colour.adaptation.chromatic_adaptation_VonKries(xyz, blanc, colour.xy_to_XYZ(D65), 'Bradford')
    return rgb, xyz, list(cc.keys())


def de2000(xyz_a, xyz_b):
    return colour.delta_E(colour.XYZ_to_Lab(xyz_a, D65), colour.XYZ_to_Lab(xyz_b, D65), method='CIE 2000')


def ajuster(rgb, xyz):
    """Matrice caméra → XYZ D65 qui envoie (1,1,1) sur le blanc D65, au moindre ΔE2000 moyen."""
    w = colour.xy_to_XYZ(D65)
    m0 = np.linalg.lstsq(rgb, xyz, rcond=None)[0].T

    def mat(p):
        m = np.zeros((3, 3))
        m[:, :2] = p.reshape(3, 2)
        m[:, 2] = w - m[:, :2].sum(1)
        return m

    f = lambda p: de2000(rgb @ mat(p).T, xyz).mean()
    r = minimize(f, m0[:, :2].ravel(), method='Nelder-Mead', options={'maxiter': 20000, 'xatol': 1e-7, 'fatol': 1e-7})
    return mat(r.x)


def noter_srgb(m_srgb, rgb, xyz):
    """ΔE2000 d'une matrice caméra → sRGB linéaire (convention du firmware)."""
    return de2000(rgb @ (np.linalg.inv(XYZ_VERS_SRGB) @ m_srgb).T, xyz)


def rapport(sens):
    fw = matrices_firmware()
    for ill in ('D65', 'D50', 'A'):
        rgb, xyz, noms = donnees(sens, ill)
        m = ajuster(rgb, xyz)
        ms = XYZ_VERS_SRGB @ m
        e = de2000(rgb @ m.T, xyz)
        print(f'— illuminant {ill} : matrice caméra → sRGB linéaire (×512, lignes = 512)')
        print('  ' + ' | '.join(' '.join(f'{v:6.0f}' for v in l) for l in ms * 512))
        print(f'  ΔE2000 moyen {e.mean():.2f}, max {e.max():.2f} ({noms[int(e.argmax())]})')
        notes = sorted((noter_srgb(f, rgb, xyz).mean(), n) for n, f in enumerate(fw) if n < 6)
        print('  matrices firmware 0–5 (mode Ia, sRGB) : ' + ', '.join(f'n° {n} {v:.2f}' for v, n in notes))
    return m


def self_test(chemin):
    sens = lire_camspec(chemin)
    assert sens.shape == (3, 33) and sens[1].max() == 1
    fw = matrices_firmware()
    assert all(abs(f.sum(1) - 1).max() < 0.01 for f in fw), 'lignes ≠ 512'
    rgb, xyz, _ = donnees(sens, 'D65')
    assert abs(xyz[18][1] - 0.9).max() < 0.05  # patch blanc ≈ Y 0,9
    m = ajuster(rgb, xyz)
    assert de2000(rgb @ m.T, xyz).mean() < 3
    print('self-test OK')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('camspec')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test(a.camspec)
    rapport(lire_camspec(a.camspec))


if __name__ == '__main__':
    sys.exit(main())
