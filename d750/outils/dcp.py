#!/usr/bin/env python3
"""Lit un profil Adobe .dcp (structure TIFF, magie « IIRC ») : nom, matrices,
courbe de tonalité, tables HueSatMap / LookTable. Lecture seule.

    python3 outils/dcp.py "<profil.dcp>" [--courbe] [--json]
"""
import json
import struct
import sys

TAGS = {50708: "UniqueCameraModel", 50721: "ColorMatrix1", 50722: "ColorMatrix2",
        50778: "CalibrationIlluminant1", 50779: "CalibrationIlluminant2",
        50936: "ProfileName", 50937: "ProfileHueSatMapDims", 50938: "ProfileHueSatMapData1",
        50939: "ProfileHueSatMapData2", 50940: "ProfileToneCurve", 50941: "ProfileEmbedPolicy",
        50964: "ForwardMatrix1", 50965: "ForwardMatrix2", 50981: "ProfileLookTableDims",
        50982: "ProfileLookTableData", 51107: "ProfileHueSatMapEncoding", 51108: "ProfileLookTableEncoding",
        51110: "DefaultBlackRender"}
TAILLES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8, 11: 4, 12: 8}


def lire(chemin):
    d = open(chemin, "rb").read()
    if d[:4] != b"IIRC":
        raise ValueError("pas un DCP (magie IIRC attendue)")
    off = struct.unpack_from("<I", d, 4)[0]
    n = struct.unpack_from("<H", d, off)[0]
    out = {}
    for i in range(n):
        tag, typ, cnt, val = struct.unpack_from("<HHII", d, off + 2 + 12 * i)
        taille = TAILLES[typ] * cnt
        pos = off + 2 + 12 * i + 8 if taille <= 4 else val
        brut = d[pos:pos + taille]
        if typ == 2:
            v = brut.rstrip(b"\0").decode("latin-1")
        elif typ == 11:
            v = list(struct.unpack(f"<{cnt}f", brut))
        elif typ == 10:
            v = [a / b for a, b in zip(*[iter(struct.unpack(f"<{2 * cnt}i", brut))] * 2)]
        elif typ == 3:
            v = list(struct.unpack(f"<{cnt}H", brut))
        elif typ == 4:
            v = list(struct.unpack(f"<{cnt}I", brut))
        else:
            v = brut.hex()
        out[TAGS.get(tag, str(tag))] = v
    return out


def main():
    p = lire(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(p))
        return
    for k, v in p.items():
        if isinstance(v, list) and len(v) > 12:
            print(f"{k}: {len(v)} valeurs")
        else:
            print(f"{k}: {v}")
    if "--courbe" in sys.argv and "ProfileToneCurve" in p:
        c = p["ProfileToneCurve"]
        pts = list(zip(c[::2], c[1::2]))
        print("courbe (échantillon) :", [(round(x * 255), round(y * 255)) for x, y in pts[:: max(1, len(pts) // 16)]])


if __name__ == "__main__":
    main()
