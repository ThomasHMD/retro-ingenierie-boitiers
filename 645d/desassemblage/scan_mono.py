# Matrices 3x3 (int16 grand-boutiste) dont les trois lignes sont identiques et somment à S : mélanges Monochrome possibles.
import sys, struct
b = open(sys.argv[1], 'rb').read()
lim = int(sys.argv[2], 16) if len(sys.argv) > 2 else len(b)
hits = []
for o in range(0, min(lim, len(b)) - 18, 2):
    v = struct.unpack_from('>9h', b, o)
    r = v[0:3]
    if r == v[3:6] == v[6:9] and sum(r) in (256, 1024, 4096) and len(set(r)) > 1 and min(r) >= -512:
        hits.append((o, sum(r), r))
for h in hits[:80]:
    print(hex(h[0]), h[1], h[2])
print(len(hits))
