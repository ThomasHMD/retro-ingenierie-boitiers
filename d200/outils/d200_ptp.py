"""Décodage d'une sonde USB du D200 (d200/outils/d200_ptp.swift) : réglages, plages, courbe perso.

Usage :
  python3 d200/outils/d200_ptp.py <dossier de sonde> [chemin de ptp.h de libgphoto2]
Écrit <dossier>/releve.tsv (un réglage par ligne) et affiche la courbe perso décodée.
Les noms viennent de libgphoto2 (camlibs/ptp2/ptp.h), par défaut dans le cache de d40/outils/references.sh.
Ne parle à aucun boîtier. Résultats : d200/recherche/d200-ptp-usb.md.
"""
import os
import re
import struct
import sys

CACHE_PTP_H = os.path.expanduser("~/Library/Caches/retro-ingenierie-boitiers/libgphoto2/camlibs/ptp2/ptp.h")
# taille et format struct des types PTP simples
TYPES = {1: ("INT8", "<b"), 2: ("UINT8", "<B"), 3: ("INT16", "<h"), 4: ("UINT16", "<H"),
         5: ("INT32", "<i"), 6: ("UINT32", "<I"), 7: ("INT64", "<q"), 8: ("UINT64", "<Q")}


def noms_ptp(chemin):
    """Noms des réglages d'après ptp.h : standard (PTP_DPC_) et Nikon (PTP_DPC_NIKON_), le premier nom l'emporte."""
    noms = {}
    if not chemin or not os.path.exists(chemin):
        return noms
    for m in re.finditer(r"#define\s+PTP_DPC_(NIKON_)?(\w+)\s+0x([0-9A-Fa-f]{4})\b", open(chemin, encoding="latin-1").read()):
        code = int(m.group(3), 16)
        nikon = bool(m.group(1))
        if (code >= 0xD000) == nikon:
            noms.setdefault(code, m.group(2))
    return noms


def valeur(d, i, t):
    """Lit une valeur de type t à l'indice i ; renvoie (valeur, indice suivant)."""
    if t in TYPES:
        f = TYPES[t][1]
        return struct.unpack_from(f, d, i)[0], i + struct.calcsize(f)
    if t == 0xFFFF:  # chaîne PTP : longueur en caractères (u8) puis UTF-16LE
        n = d[i]
        s = d[i + 1:i + 1 + 2 * n].decode("utf-16-le", "replace").rstrip("\x00")
        return s, i + 1 + 2 * n
    if t & 0x4000:  # tableau : u32 nombre puis éléments
        n = struct.unpack_from("<I", d, i)[0]
        i += 4
        el = []
        for _ in range(n):
            v, i = valeur(d, i, t & 0x3FFF)
            el.append(v)
        return el, i
    raise ValueError(f"type 0x{t:04x} inconnu")


def lire_desc(d):
    """DevicePropDesc PTP : code, type, accès, défaut, courant, forme (0 aucune, 1 plage, 2 énumération)."""
    code, t, acces = struct.unpack_from("<HHB", d, 0)
    defaut, i = valeur(d, 5, t)
    courant, i = valeur(d, i, t)
    forme = d[i] if i < len(d) else 0
    i += 1
    detail = None
    if forme == 1:
        mini, i = valeur(d, i, t)
        maxi, i = valeur(d, i, t)
        pas, i = valeur(d, i, t)
        detail = (mini, maxi, pas)
    elif forme == 2:
        n = struct.unpack_from("<H", d, i)[0]
        i += 2
        detail = []
        for _ in range(n):
            v, i = valeur(d, i, t)
            detail.append(v)
    nom_type = TYPES.get(t, ("STR",))[0] if t in TYPES or t == 0xFFFF else f"A{TYPES.get(t & 0x3FFF, ('?',))[0]}"
    return {"code": code, "type": nom_type, "acces": "écriture" if acces == 1 else "lecture",
            "defaut": defaut, "courant": courant, "forme": ["aucune", "plage", "énum"][forme] if forme < 3 else str(forme),
            "detail": detail}


def texte(v):
    if isinstance(v, list):
        return "[" + " ".join(str(x) for x in v[:40]) + (" …" if len(v) > 40 else "") + "]"
    if isinstance(v, str):
        return "« " + v + " »"
    return str(v)


def courbe(d):
    """Bloc de 0x90C5 / 0x90C6 (0x844 octets, firmware 2.01) : 68 octets d'entête puis 2 048 valeurs sur 8 bits.
    Entête : 6 octets de préambule, puis la structure PTPNIKONCurveData de libgphoto2 (axes, gamma, nombre de points,
    points). Le boîtier n'utilise la table que si les octets 0 et 1 sont tous deux non nuls ; sinon il prend sa courbe
    d'usine (B2000201.bin à 0x17329C). Preuves : d200/recherche/d200-ptp-usb.md."""
    ent, table = d[:68], d[68:]
    return {"taille": len(d), "entete": ent, "valide": ent[0] != 0 and ent[1] != 0, "table": table,
            "axes": tuple(ent[6:10]), "gamma": ent[10] + ent[11] / 100, "points": [tuple(ent[13 + 2 * k:15 + 2 * k]) for k in range(min(ent[12], 19))]}


def main():
    dossier = sys.argv[1]
    noms = noms_ptp(sys.argv[2] if len(sys.argv) > 2 else CACHE_PTP_H)
    lignes = ["code\tnom libgphoto2\ttype\taccès\tcourant\tdéfaut\tforme\tplage ou valeurs"]
    for f in sorted(os.listdir(dossier)):
        if not (f.startswith("prop_") and f.endswith(".bin")):
            continue
        p = lire_desc(open(os.path.join(dossier, f), "rb").read())
        detail = texte(list(p["detail"])) if p["forme"] == "plage" else texte(p["detail"]) if p["detail"] is not None else ""
        lignes.append(f"0x{p['code']:04X}\t{noms.get(p['code'], '?')}\t{p['type']}\t{p['acces']}\t"
                      f"{texte(p['courant'])}\t{texte(p['defaut'])}\t{p['forme']}\t{detail}")
    open(os.path.join(dossier, "releve.tsv"), "w").write("\n".join(lignes) + "\n")
    print("\n".join(lignes))
    for f in sorted(os.listdir(dossier)):
        if f.startswith("courbe_") and f.endswith(".bin"):
            c = courbe(open(os.path.join(dossier, f), "rb").read())
            print(f"\n{f} : {c['taille']} octets ; entête {c['entete'].hex(' ')}")
            print(f"  courbe perso {'VALIDE (utilisée)' if c['valide'] else 'absente : le boîtier prend sa courbe d’usine'}"
                  f" ; axes {c['axes']}, gamma {c['gamma']}, points {c['points']}")
            t = c["table"]
            print(f"  table : {len(t)} valeurs 8 bits ; échantillons tous les 128 : {[t[i] for i in range(0, len(t), 128)]}")


if __name__ == "__main__":
    main()
