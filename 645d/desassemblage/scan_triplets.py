# Cherche des tables de triplets (R, V, B) de même somme : poids de filtres Monochrome possibles.
import sys, struct
b = open(sys.argv[1], 'rb').read()
res = []
for size, fmt in ((2, '>h'), (4, '>i'), (1, 'b')):
    step = size * 3
    for start in range(0, len(b) - step * 9, size):
        rows = []
        o = start
        while o + step <= len(b) and len(rows) < 16:
            t = [struct.unpack_from(fmt, b, o + size * k)[0] for k in range(3)]
            rows.append(t); o += step
        s = sum(rows[0])
        if s not in (64, 100, 128, 255, 256, 512, 1000, 1023, 1024, 2048, 4095, 4096, 8192, 16384, 32768, 65536, 10000):
            continue
        n = 0
        for r in rows:
            if sum(r) == s and max(r) <= s * 2 and min(r) >= -s and len(set(r)) > 1:
                n += 1
            else:
                break
        if n >= 6:
            res.append((n, size, start, s, rows[:n]))
seen = set()
for n, size, start, s, rows in sorted(res, key=lambda x: -x[0])[:40]:
    key = (start // 64, size)
    if key in seen: continue
    seen.add(key)
    print(n, size, hex(start), s, rows)
