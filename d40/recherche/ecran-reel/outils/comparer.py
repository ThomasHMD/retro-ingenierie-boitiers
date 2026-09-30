"""Compare une image du boîtier (redressée sur 4 coins) à des captures de l'émulateur.

Classement de chaque case d'une grille (32 x 24 cases de 20 x 20 points) en classes de teinte
robustes à l'exposition du téléphone : vert, bleu (marine/ardoise), clair (blanc, gris clair,
cyan pâle), sombre (noir). Score = part des cases de même classe.
usage : comparer.py <photo> x0,y0 x1,y1 x2,y2 x3,y3 <sortie_redressee.png> <emu1.png> [<emu2.png> ...]
coins dans l'ordre haut-gauche, haut-droite, bas-droite, bas-gauche.
"""
import sys, cv2, numpy as np

def redresser(photo, coins, sortie):
    im = cv2.imread(photo)
    src = np.float32(coins)
    dst = np.float32([[0, 0], [639, 0], [639, 479], [0, 479]])
    M = cv2.getPerspectiveTransform(src, dst)
    r = cv2.warpPerspective(im, M, (640, 480))
    cv2.imwrite(sortie, r)
    return r

def classes(img_bgr, auto=True):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    if auto:  # normalise l'exposition : la case la plus claire de l'image vaut 1
        v = v / max(np.percentile(v, 99), 1e-3)
    out = np.zeros((24, 32), dtype='<U6')
    for j in range(24):
        for i in range(32):
            sl = (slice(j * 20 + 4, j * 20 + 16), slice(i * 20 + 4, i * 20 + 16))
            hh, ss, vv = np.median(h[sl]), np.median(s[sl]), np.median(v[sl])
            if ss > 0.3 and 190 <= hh <= 260 and vv >= 0.08:
                c = 'bleu'    # marine et ardoise, même très sombres (noir du LCD bleuté)
            elif vv < 0.18:
                c = 'sombre'
            elif ss > 0.35 and 90 <= hh <= 170:
                c = 'vert'
            elif vv > 0.6 and ss < 0.35:
                c = 'clair'
            elif 170 < hh < 200 and vv > 0.6:
                c = 'clair'   # cyan pâle du panneau Classique
            else:
                c = 'autre'
            out[j, i] = c
    return out

photo = sys.argv[1]
coins = [tuple(map(float, p.split(','))) for p in sys.argv[2:6]]
r = redresser(photo, coins, sys.argv[6])
cp = classes(r)
for emu in sys.argv[7:]:
    ce = classes(cv2.imread(emu), auto=False)
    ok = (cp == ce)
    print(f'{emu.split("/")[-2]}/{emu.split("/")[-1]} : {100 * ok.mean():.1f} % des cases de même classe')
    for k in ['vert', 'bleu', 'clair', 'sombre']:
        print(f'   {k:6s} photo {np.sum(cp == k):4d}  émulateur {np.sum(ce == k):4d}')
