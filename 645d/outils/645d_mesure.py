#!/usr/bin/env python3
"""Mesure du rendu du Pentax 645D (séances par USB, 645d_seance.swift) : le JPEG pleine taille intégré à chaque PEF
(JpgFromRaw, rendu par le boîtier avec son Custom Image) est comparé à son propre RAW, développé en sRGB linéaire par
d750/outils/raw_lineaire.swift (décodeur de macOS, sans courbe, balance de la prise de vue). Même démarche que le D750
(d750/outils/d750_analyse.py) : blocs uniformes, chaque JPEG contre son RAW, donc indépendant de la lumière de la scène.

  645d_mesure.py extraire <dossier> <raw_lineaire>   blocs de chaque vue → <dossier>/blocs/<vue>.npz (vues.tsv ou images/)
  645d_mesure.py nb <dossier> <sortie.json>          Monochrome : poids R, V, B de chaque filtre, courbe de chaque contraste,
                                                     rendu le plus proche de la Tri-X et de la HP5 (fiches, données-films)
  645d_mesure.py --self-test

Modèle Monochrome : gris JPEG = T(w · x), x = RVB linéaire (sRGB, balance de la vue), w = poids des canaux (somme 1),
T croissante (régression isotone). w dépend du filtre, T du contraste (mesuré sur le filtre « aucun »).
Cibles : d750/recherche/donnees-films/hp5-trix-cibles.json (mélange en sRGB linéaire D65, courbe film + tirage par IL,
gris à 118/255). La comparaison laisse libre le placement du gris (l'exposition, ou High/Low Key au menu) et le donne.
"""
import json
import pathlib
import subprocess
import sys

import numpy as np

RACINE = pathlib.Path(__file__).resolve().parents[2]
CIBLES = RACINE / "d750/recherche/donnees-films/hp5-trix-cibles.json"
FILTRES = ["aucun", "vert", "jaune", "orange", "rouge", "magenta", "bleu", "cyan", "infrarouge"]
ECHELLE = 0.125
BLOC = 8          # pixels du rendu réduit (64 × 64 pixels du capteur)


def vues(dossier):
    """(nom de la vue, chemin du PEF) pour chaque PEF rapatrié par 645d_seance.swift (images/NN-nom-THAMxxxx.PEF)."""
    return [(p.stem.rsplit("-", 1)[0], p) for p in sorted((pathlib.Path(dossier) / "images").glob("[0-9][0-9]-*.PEF"))]


def exif(pef):
    champs = ["ImageTone", "MonochromeFilterEffect", "MonochromeToning", "Saturation", "Hue", "Contrast", "Sharpness",
              "ExposureTime", "FNumber", "ISO", "WhiteBalance", "HighLowKeyAdj", "FineSharpness", "ContrastHighlightShadowAdj"]
    r = subprocess.run(["exiftool", "-j", "-n"] + [f"-{c}" for c in champs] + [str(pef)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)[0]


def charger_paire(pef, raw_lineaire, tmp):
    import cv2
    tmp.mkdir(parents=True, exist_ok=True)
    jpg, tif = tmp / (pef.stem + ".jpg"), tmp / (pef.stem + ".tif")
    with open(jpg, "wb") as f:
        subprocess.run(["exiftool", "-b", "-JpgFromRaw", str(pef)], stdout=f, check=True)
    subprocess.run([raw_lineaire, str(pef), str(tif), str(ECHELLE)], capture_output=True, check=True)
    lin = cv2.imread(str(tif), cv2.IMREAD_UNCHANGED)[..., [2, 1, 0]].astype(np.float64) / 65535.0
    j = cv2.imread(str(jpg), cv2.IMREAD_COLOR)[..., ::-1]
    j = cv2.resize(j, (lin.shape[1], lin.shape[0]), interpolation=cv2.INTER_AREA).astype(np.float64)
    jpg.unlink(); tif.unlink()
    return lin, j


def decalage(lin, j, rayon=6):
    """Décalage entier (dy, dx) qui aligne le JPEG sur le RAW (recadrages un peu différents)."""
    a = np.power(np.clip(lin.mean(2), 0, 1), 1 / 2.2)
    b = j.mean(2) / 255.0
    m = rayon
    a0 = a[m:-m, m:-m]
    a0 = (a0 - a0.mean()) / a0.std()
    best = (-2.0, 0, 0)
    for dy in range(-rayon, rayon + 1):
        for dx in range(-rayon, rayon + 1):
            b0 = b[m + dy:b.shape[0] - m + dy, m + dx:b.shape[1] - m + dx]
            b0 = (b0 - b0.mean()) / b0.std()
            c = float((a0 * b0).mean())
            if c > best[0]:
                best = (c, dy, dx)
    return best


def blocs(lin, j, dy, dx):
    h, w = lin.shape[:2]
    m = 8
    x, y, sx = [], [], []
    for i in range(m, h - m - BLOC, BLOC):
        for k in range(m, w - m - BLOC, BLOC):
            a = lin[i:i + BLOC, k:k + BLOC].reshape(-1, 3)
            b = j[i + dy:i + dy + BLOC, k + dx:k + dx + BLOC].reshape(-1, 3)
            x.append(a.mean(0)); y.append(b.mean(0)); sx.append(a.std(0).max() / max(a.mean(), 1e-6))
    return np.array(x), np.array(y), np.array(sx)


def extraire(dossier, raw_lineaire):
    d = pathlib.Path(dossier)
    (d / "blocs").mkdir(exist_ok=True)
    ref = None
    for nom, pef in vues(d):
        sortie = d / "blocs" / f"{nom}.npz"
        if sortie.exists():
            continue
        lin, j = charger_paire(pef, raw_lineaire, d / "tmp")
        c, dy, dx = decalage(lin, j)
        x, y, sx = blocs(lin, j, dy, dx)
        e = exif(pef)
        np.savez_compressed(sortie, x=x, y=y, sx=sx, exif=json.dumps(e), decalage=[dy, dx, c])
        print(f"{nom}: {len(x)} blocs, décalage {dy},{dx} (corrélation {c:.3f}), {e.get('ImageTone')} filtre {e.get('MonochromeFilterEffect')} "
              f"contraste {e.get('Contrast')} ISO {e.get('ISO')} {e.get('ExposureTime')} s")


def pav(y):
    """Régression isotone croissante (pool adjacent violators), y déjà trié selon l'abscisse."""
    vals, poids, tailles = [], [], []
    for yi in y:
        vals.append(float(yi)); poids.append(1.0); tailles.append(1)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            t = poids[-2] + poids[-1]
            vals[-2] = (vals[-2] * poids[-2] + vals[-1] * poids[-1]) / t
            poids[-2] = t; tailles[-2] += tailles[-1]
            vals.pop(); poids.pop(); tailles.pop()
    return np.repeat(vals, tailles)


def ajuster_nb(x, g):
    """Poids w (somme 1) et courbe T isotone : g ≈ T(x · w). Rend w, (s trié, T(s)), écart RMS en niveaux."""
    from scipy.optimize import minimize

    def cout(p):
        w = np.array([p[0], p[1], 1 - p[0] - p[1]])
        s = x @ w
        o = np.argsort(s)
        return float(np.mean((g[o] - pav(g[o])) ** 2))
    r = minimize(cout, [0.3, 0.59], method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-4, "maxiter": 400})
    w = np.array([r.x[0], r.x[1], 1 - r.x[0] - r.x[1]])
    s = x @ w
    o = np.argsort(s)
    return w, (s[o], pav(g[o])), float(np.sqrt(r.fun))


def selection(dossier):
    d = pathlib.Path(dossier) / "blocs"
    out = {}
    for p in sorted(d.glob("*.npz")):
        z = np.load(p)
        out[p.stem] = {"x": z["x"], "y": z["y"], "sx": z["sx"], "exif": json.loads(str(z["exif"]))}
    return out


def nb(dossier, sortie):
    V = selection(dossier)
    mono = {k: v for k, v in V.items() if str(v["exif"].get("ImageTone")) in ("5", "Monochrome") or "mono" in k}
    if not mono:
        sys.exit("aucune vue Monochrome dans les blocs")
    # blocs uniformes et non saturés dans toutes les vues Monochrome (masque commun : même scène, trépied)
    n = min(len(v["x"]) for v in mono.values())
    masque = np.ones(n, bool)
    for v in mono.values():
        masque &= (v["sx"][:n] < 0.06) & (v["x"][:n].max(1) < 0.9) & (v["x"][:n].min(1) > 0.002)
        masque &= (v["y"][:n].mean(1) > 4) & (v["y"][:n].mean(1) < 250)
    print(f"{masque.sum()} blocs communs sur {n}")
    cibles = json.loads(CIBLES.read_text())
    films = {"Tri-X": ("trix", cibles["melange_srgb_lineaire_D65"]["trix_fiche_D1.0"]),
             "HP5": ("hp5", cibles["melange_srgb_lineaire_D65"]["hp5_fiche"])}
    res = {"blocs": int(masque.sum()), "vues": {}}
    courbes = {}
    for k, v in sorted(mono.items()):
        x, y = v["x"][:n][masque], v["y"][:n][masque]
        g = y.mean(1)
        neutre = float(np.abs(y[:, 0] - y[:, 2]).mean())
        w, (s, t), rms = ajuster_nb(x, g)
        e = v["exif"]
        res["vues"][k] = {"poids_rvb": [round(float(a), 3) for a in w], "ecart_rms_niveaux": round(rms, 2),
                          "virage_R_moins_B": round(float((y[:, 0] - y[:, 2]).mean()), 2), "ecart_canaux": round(neutre, 2),
                          "exif": {c: e.get(c) for c in ("MonochromeFilterEffect", "MonochromeToning", "Contrast", "ISO", "ExposureTime")}}
        courbes[k] = (s, t)
        print(f"{k:28s} poids R {w[0]:+.3f} V {w[1]:+.3f} B {w[2]:+.3f}  RMS {rms:5.2f}  R−B {res['vues'][k]['virage_R_moins_B']:+.1f}")
    # simulation : pour chaque film, rendu film des blocs contre rendu boîtier (filtre f × contraste c), gris libre
    x0 = V[sorted(mono)[0]]["x"][:n][masque]
    res["films"] = {}
    contrastes = {k: c for k, c in ((k, int(k.rsplit("-", 1)[1])) for k in mono if "contraste" in k)}
    filtre0 = next((k for k in mono if "filtre-0" in k), None)
    if filtre0:
        contrastes[filtre0] = 4
    for nomf, (cle, wf) in films.items():
        par_il = np.array(cibles["cible_tonale"][cle]["par_IL"])
        sf = x0 @ np.array(wf)
        ev_f = np.log2(np.maximum(sf, 1e-6) / np.median(sf))
        meilleurs = []
        for kf in (k for k in mono if "filtre-" in k):
            sc = x0 @ np.array(res["vues"][kf]["poids_rvb"])
            for kc, c in contrastes.items():
                s, t = courbes[kc]
                ycam = np.interp(sc, s, t)          # rendu du boîtier : filtre kf, contraste c, exposition de la séance
                # film exposé au mieux (d = place du gris médian de la scène sur la courbe du film, en IL)
                best = min((float(np.sqrt(np.mean((ycam - np.interp(ev_f + d, par_il[:, 0], par_il[:, 1])) ** 2))), float(d))
                           for d in np.arange(-2.0, 2.01, 0.05))
                meilleurs.append({"filtre": kf, "contraste": c - 4, "rms_niveaux": round(best[0], 2), "gris_film_IL": round(best[1], 2)})
        meilleurs.sort(key=lambda m: m["rms_niveaux"])
        res["films"][nomf] = {"poids_cible": wf, "classement": meilleurs[:8]}
        print(f"\n{nomf} (cible {wf}) :")
        for m in meilleurs[:5]:
            print(f"  {m['filtre']:28s} contraste {m['contraste']:+d}  écart {m['rms_niveaux']:5.2f} niveaux")
    pathlib.Path(sortie).write_text(json.dumps(res, indent=1, ensure_ascii=False))


def self_test():
    rng = np.random.default_rng(1)
    x = rng.uniform(0.01, 0.8, (800, 3))
    w = np.array([0.1, 0.25, 0.65])
    g = 255 * np.power(x @ w / 0.8, 1 / 2.2)
    w2, _, rms = ajuster_nb(x, g)
    assert np.allclose(w2, w, atol=0.02), w2
    assert rms < 1.0
    assert np.all(np.diff(pav(np.array([1, 3, 2, 4.0]))) >= 0)
    print("self-test OK")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--self-test"]:
        self_test()
    elif a[:1] == ["extraire"] and len(a) == 3:
        extraire(a[1], a[2])
    elif a[:1] == ["nb"] and len(a) == 3:
        nb(a[1], a[2])
    else:
        print(__doc__); sys.exit(2)
