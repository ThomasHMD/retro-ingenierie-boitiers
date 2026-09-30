#!/usr/bin/env python3
"""Courbes de tonalité du firmware B du D40 (v1.11).

Lu dans le code (CARTE.md §7) : `0x323C22` construit la table de tonalité de 4 096 entrées
(12 bits) d'après l'octet +0x466 des réglages de la prise de vue (numéro de courbe) :
  - 0 à 20  : courbes intégrées, jeu 1, données à 0x34BC56 + n × 0x7FF,
              valeurs de départ y0 = [0x34BC41 + n], y1 = [0x34BC2C + n] ;
  - 0x17    : courbe perso (tampon RAM, ou défaut d'usine 0xDB20C / 0xDC250) ;
  - 0x2F à 0x35 : jeu 2, données à 0x348433 + (n − 0x2F) × 0x7FF,
              y0 = [0x34842C + n − 0x2F], y1 = [0x348425 + n − 0x2F].
Codage (`0x324306`) : 2 047 octets, deux quartets chacun ; y[k] = 2·y[k−1] − y[k−2] + (q − 8).
Une table de corrections signées (0x33692E) est ensuite ajoutée, entrée par entrée.

  courbes.py liste                  # résumé des 28 courbes (points à 1/8, 1/4, 1/2…)
  courbes.py json > courbes.json    # 4 096 points par courbe
  courbes.py svg > courbes.svg      # tracé
  courbes.py --self-test
"""
import argparse
import json
import pathlib
import struct

ICI = pathlib.Path(__file__).resolve().parent.parent
FIRMWARE = ICI / 'firmware' / 'BD400111.bin'
BASE = 0x40000
N_OCTETS = 0x7FF


def lire(b, a, n=1):
    return b[a - BASE:a - BASE + n]


def decoder(b, donnees, y0, y1):
    y = [y0, y1]
    for o in lire(b, donnees, N_OCTETS):
        for q in (o >> 4, o & 0xF):
            y.append((2 * y[-1] - y[-2] + q - 8) & 0xFFFF)
    return y


def encoder(cible):
    """Inverse de decoder : 4 096 valeurs cibles -> (y0, y1, 2 047 octets). Suivi glouton de la
    position avec une dérivée seconde bornée à [-8, 7] ; renvoie aussi l'écart max à la cible."""
    y = [int(round(cible[0])), int(round(cible[1]))]
    assert 0 <= y[0] <= 255 and 0 <= y[1] <= 255, 'les deux premières valeurs doivent tenir sur un octet'
    qs = []
    for k in range(2, 4096):
        pred = 2 * y[-1] - y[-2]
        # vise la cible en tenant compte de la vitesse : amortit pour éviter les oscillations
        vise = cible[k] + (cible[k] - cible[k - 1]) - (pred - y[-1])
        q = max(-8, min(7, int(round((cible[k] - pred) * 0.6 + (vise - pred) * 0.4))))
        q = max(q, min(7, y[-1] - pred))          # jamais décroissante
        y.append(pred + q)
        qs.append(q + 8)
    octets = bytes((qs[i] << 4) | qs[i + 1] for i in range(0, len(qs), 2))
    ecart = max(abs(a - b) for a, b in zip(y, cible))
    return y[0], y[1], octets, ecart, y


def emplacement(n):
    """(adresse des données, adresse de y0, adresse de y1) de la courbe intégrée n."""
    if 0 <= n <= 20:
        return 0x34BC56 + n * N_OCTETS, 0x34BC41 + n, 0x34BC2C + n
    if 0x2F <= n <= 0x35:
        k = n - 0x2F
        return 0x348433 + k * N_OCTETS, 0x34842C + k, 0x348425 + k
    raise ValueError(f'pas de courbe intégrée n° {n}')


def depuis_rampe(chemin, colonne, ref, base=None):
    """Courbe 12 bits depuis une rampe de gris (IL autour du gris 18 %, sortie 0-255).
    Le gris est placé là où la courbe de référence du D40 rend la même valeur que le neutre de la
    rampe à 0 IL : on garde l'exposition du boîtier.
    base=None : courbe absolue de la simulation (blancs gris : le Fuji garde ~6 IL au-dessus du
    gris, le D40 ~3,5). base='provia' : courbe de référence du D40 + (simulation − provia), ce qui
    garde la montée au blanc du D40 et ne transporte que l'écart de la simulation."""
    import math
    rampe = json.loads(pathlib.Path(chemin).read_text())['gris']
    il = [r['IL'] for r in rampe]
    gris_sortie = next(r['neutre'] for r in rampe if r['IL'] == 0) / 255 * 4095
    g = next(k for k in range(4096) if ref[k] >= gris_sortie) / 4095
    def val(e):
        if e <= il[0]:
            return rampe[0][colonne]
        if e >= il[-1]:
            return 255
        i = max(j for j in range(len(il)) if il[j] <= e)
        t = (e - il[i]) / (il[i + 1] - il[i])
        return rampe[i][colonne] * (1 - t) + rampe[i + 1][colonne] * t
    def v(e, col):
        nonlocal colonne
        sauve, colonne = colonne, col
        r = val(e)
        colonne = sauve
        return r
    out = [0.0]
    for k in range(1, 4096):
        e = math.log2((k / 4095) / g)
        if base is None:
            out.append(v(e, colonne) / 255 * 4095)
        else:
            out.append(ref[k] + (v(e, colonne) - v(e, base)) / 255 * 4095)
    out = [max(0.0, min(4095.0, x)) for x in out]
    for k in range(1, 4096):                      # croissante, sinon le rendu se replie
        out[k] = max(out[k], out[k - 1])
    return out, g


def courbes(b):
    res = {}
    for n in range(21):
        res[n] = decoder(b, 0x34BC56 + n * N_OCTETS, lire(b, 0x34BC41 + n)[0], lire(b, 0x34BC2C + n)[0])
    for n in range(0x2F, 0x36):
        k = n - 0x2F
        res[n] = decoder(b, 0x348433 + k * N_OCTETS, lire(b, 0x34842C + k)[0], lire(b, 0x348425 + k)[0])
    for nom, a in (('perso_defaut_1', 0xDB250), ('perso_defaut_2', 0xDC294)):
        t = struct.unpack('>2048H', lire(b, a, 4096))
        res[nom] = [t[i // 2] if i % 2 == 0 else (t[i // 2] + t[min(i // 2 + 1, 2047)]) // 2 for i in range(4096)]
    return res


def self_test():
    c = courbes(FIRMWARE.read_bytes())
    for n, y in c.items():
        assert len(y) == 4096, n
        assert all(0 <= v <= 4095 for v in y), f'courbe {n} hors de 0..4095'
        assert all(y[i] <= y[i + 1] for i in range(4095)), f'courbe {n} non croissante'
    b = FIRMWARE.read_bytes()
    for n in (0, 17, 50):
        d, a0, a1 = emplacement(n)
        y0, y1, octets, ecart, _ = encoder(c[n])
        assert ecart == 0 and octets == lire(b, d, N_OCTETS) and (y0, y1) == (lire(b, a0)[0], lire(b, a1)[0]), n
    print(f'self-test OK : {len(c)} courbes, toutes croissantes dans 0..4095 ; réencodage exact')


def svg(c):
    l, h, m = 520, 520, 40
    coul = ['#1b6ef3', '#e5484d', '#30a46c', '#f76b15', '#8e4ec6', '#12a594', '#d6409f']
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {l + 2 * m} {h + 2 * m}" font-family="sans-serif" font-size="11">',
           f'<rect width="100%" height="100%" fill="#fff"/><rect x="{m}" y="{m}" width="{l}" height="{h}" fill="none" stroke="#999"/>',
           ]
    # abscisse en IL (log2 de l'entrée, de 1/1024 à la pleine échelle) : les ombres deviennent lisibles
    import math
    ks = sorted({int(round(4095 * 2 ** (-10 + 10 * i / 300))) for i in range(301)} - {0})
    x = lambda k: m + l * (math.log2(k / 4095) + 10) / 10
    for e in range(-10, 1):
        out.append(f'<line x1="{x(4095 * 2 ** e):.1f}" y1="{m}" x2="{x(4095 * 2 ** e):.1f}" y2="{m + h}" stroke="#eee"/>'
                   f'<text x="{x(4095 * 2 ** e) - 6:.1f}" y="{m + h + 14}" fill="#666">{e}</text>')
    for i, (n, y) in enumerate(c.items()):
        pts = ' '.join(f'{x(k):.1f},{m + h - h * y[k] / 4095:.1f}' for k in ks)
        out.append(f'<polyline fill="none" stroke="{coul[i % len(coul)]}" stroke-width="1" points="{pts}"><title>{n}</title></polyline>')
    for i, n in enumerate(c):
        out.append(f'<text x="{m + 8}" y="{m + 16 + 14 * i}" fill="{coul[i % len(coul)]}">{n}</text>')
    out.append(f'<text x="{m}" y="{m - 12}">Courbes de tonalité du D40 (firmware B 1.11) : sortie 12 bits selon l\'entrée en IL sous la pleine échelle</text></svg>')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', nargs='?', choices=['liste', 'json', 'svg', 'patch'])
    ap.add_argument('--numero', help='patch : courbe(s) intégrée(s) à remplacer, « 0-6 » ou « 0,7,14 »')
    ap.add_argument('--rampe', help='patch : JSON de mesure (recettes/mesures/*.json, clé « gris »)')
    ap.add_argument('--colonne', default='simulation')
    ap.add_argument('--reference', type=int, default=17, help='courbe du D40 qui fixe le gris (et la base)')
    ap.add_argument('--base', default='provia', help="colonne retranchée (écart à la référence) ; « aucune » = courbe absolue")
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    c = courbes(FIRMWARE.read_bytes())
    if a.action == 'patch':
        b = FIRMWARE.read_bytes()
        cible, g = depuis_rampe(a.rampe, a.colonne, c[a.reference], None if a.base == 'aucune' else a.base)
        y0, y1, octets, ecart, y = encoder(cible)
        assert all(y[i] <= y[i + 1] for i in range(4095)) and 0 <= min(y) and max(y) <= 4095, 'courbe encodée invalide'
        numeros = []
        for morceau in a.numero.split(','):
            debut, _, fin = morceau.partition('-')
            numeros += range(int(debut), int(fin or debut) + 1)
        pt = lambda adr, avant, apres: {'offset': hex(adr - BASE), 'avant': {'hex': avant.hex()}, 'apres': {'hex': apres.hex()}}
        patchs = []
        for n in numeros:
            d, a0, a1 = emplacement(n)
            patchs += [pt(d, lire(b, d, N_OCTETS), octets), pt(a0, lire(b, a0), bytes([y0])), pt(a1, lire(b, a1), bytes([y1]))]
        doc = {'description': f'Courbes {a.numero} remplacées par « {a.colonne} » de {a.rampe} ; gris à {g:.4f} de la pleine '
                              f'échelle ; courbe {a.reference} du D40 + ({a.colonne} − {a.base}) ; écart max {ecart:.1f}/4095',
               'patchs': patchs}
        print(json.dumps(doc, ensure_ascii=False, indent=1))
        return
    if a.action == 'json':
        print(json.dumps({str(k): v for k, v in c.items()}))
    elif a.action == 'svg':
        print(svg(c))
    else:
        for n, y in c.items():
            pts = [y[int(f * 4095)] for f in (0, 1 / 64, 1 / 32, 1 / 16, 1 / 8, 1 / 4, 1 / 2, 3 / 4, 1)]
            print(f'{n!s:>15}', pts)


if __name__ == '__main__':
    main()
