#!/usr/bin/env python3
"""Fabrique un firmware B (ou A) modifié pour le Nikon D40 (ou le D200, "firmware": "D200B"), prêt à flasher.

Part du firmware officiel de Nikon rangé dans d40/firmware/ (BD400111.bin, AD400111.bin ou AD400112.bin, vérifié
par son sha256 ; `fabriquer_v5.py` l'y range), applique les patchs (remplacements à longueur égale, octets
d'origine vérifiés), recalcule le CRC16 XMODEM des 2 derniers octets et écrit BD400111.BIN (ou AD4001xx.BIN).
Les offsets sont ceux du fichier (adresse - 0x40000 pour le B, adresse - 0xC0000 pour le A).

    python3 d40/patch.py d40/patchs/pipboy-menus.json            # écrit d40/build/BD400111.BIN
    python3 d40/patch.py d40/patchs/pipboy-menus.json --sortie "/Volumes/NIKON D40"
    python3 d40/patch.py d200/patchs/d200-v2.json --sortie <dossier>   # D200 : B2000201.BIN (défaut : d200/build/)
    python3 d40/patch.py --self-test

Format d'un patch :
    {"offset": "0x2722d8", "avant": {"sha256": "…", "longueur": 18}, "apres": "PIP-BOY 3000"}
« avant » décrit les octets du firmware officiel à cet endroit. Dans ce dépôt, il est donné par son empreinte
sha256 et sa longueur : le patch se vérifie sur le firmware de Nikon sans en contenir un seul octet. Les outils
qui fabriquent des patchs (outils/pipboy.py…) écrivent, eux, les octets en clair (texte ASCII, ou
{"hex": "..."}) : les deux formes sont acceptées.
« apres » plus court est complété par des espaces : les chaînes du firmware n'ont pas de terminateur, leur
longueur est fixée ailleurs.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
FIRMWARE = Path(os.environ.get('D40_FIRMWARE', ICI / 'firmware'))
# D200 2.01 : paquet officiel F-D200-V201W.exe de Nikon, ouvert avec `unar` (dossier D200Update/), B2000201.bin et
# A2000201.bin rangés ici (là où d200/outils/d200_simulateur.py les cherche aussi)
FIRMWARE_D200 = Path(os.environ.get('D200_FIRMWARE', Path.home() / 'Library/Caches/retro-ingenierie-boitiers/firmware/d200-201'))
# le boîtier cherche BD40????.BIN puis AD40????.BIN à la racine de la carte (CARTE.md §3)
ORIGINAUX = {
    "B": (FIRMWARE / "BD400111.bin",
          "b9df48d461e875dce4ba84da88164af170dfc48ad9f7674859623bad0401032e", "BD400111.BIN"),
    "A": (FIRMWARE / "AD400111.bin",
          "ff96a874d3a22f9c18c610bd5bf55f4e6a53603c865fdb8e913a1d53591db5c9", "AD400111.BIN"),
    # firmware A 1.12 (dernière mise à jour de Nikon, A seul) : "firmware": "A112" dans le JSON
    "A112": (FIRMWARE / "AD400112.bin",
             "0cc92921d6b2ad5d5cfa070abeebdd9aaca224d326e42a26339e3ac384270394", "AD400112.BIN"),
    # D200 2.01 : "firmware": "D200B" ou "D200A" ; offsets = adresse - 0x50000 pour le B ; le boîtier cherche
    # B200????.BIN et A200????.BIN (d200/recherche/d200-firmware-image.md)
    "D200B": (FIRMWARE_D200 / "B2000201.bin",
              "b7cee24dd2034645337cca500109d2ce987bee4ba8bfb521c3285c623f3407d1", "B2000201.BIN"),
    "D200A": (FIRMWARE_D200 / "A2000201.bin",
              "7143a2a9c2cd62ac46585d1e1703fc4fddadb2487a4ac80f213b1fa769689f58", "A2000201.BIN"),
}

_TABLE = []
for _i in range(256):
    _c = _i << 8
    for _ in range(8):
        _c = ((_c << 1) ^ 0x1021) & 0xFFFF if _c & 0x8000 else (_c << 1) & 0xFFFF
    _TABLE.append(_c)


def crc16_xmodem(data):
    crc = 0
    for b in data:
        crc = ((crc << 8) & 0xFFFF) ^ _TABLE[((crc >> 8) ^ b) & 0xFF]
    return crc


def octets(champ, valeur):
    if isinstance(valeur, dict) and "hex" in valeur:
        return bytes.fromhex(valeur["hex"])
    if isinstance(valeur, str):
        return valeur.encode("ascii")
    sys.exit(f"{champ} : texte ASCII ou {{\"hex\": \"...\"}} attendu, pas {valeur!r}")


def longueur_avant(avant):
    return avant["longueur"] if isinstance(avant, dict) and "sha256" in avant else len(octets("avant", avant))


def avant_conforme(data, off, avant):
    """Les octets du firmware à `off` sont-ils ceux que le patch attend ?"""
    n = longueur_avant(avant)
    vus = bytes(data[off:off + n])
    if isinstance(avant, dict) and "sha256" in avant:
        return len(vus) == n and hashlib.sha256(vus).hexdigest() == avant["sha256"]
    return vus == octets("avant", avant)


def charger_original(firmware="B"):
    chemin, sha, _ = ORIGINAUX[firmware]
    if not chemin.is_file():
        if firmware.startswith("D200"):
            sys.exit(f"{chemin} absent : télécharger F-D200-V201W.exe chez Nikon, l'ouvrir avec unar et ranger "
                     f"{chemin.name} dans {chemin.parent} (ou D200_FIRMWARE)")
        sys.exit(f"{chemin} absent : télécharger le firmware officiel chez Nikon, puis python3 d40/fabriquer_v5.py "
                 "(voir d40/README.md)")
    data = chemin.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        sys.exit(f"{chemin} n'est pas le firmware {firmware} d'origine attendu (sha256 différent)")
    if crc16_xmodem(data[:-2]) != int.from_bytes(data[-2:], "big"):
        sys.exit("CRC de l'original incohérent : le calcul du CRC est faux")
    return bytearray(data)


def appliquer(data, patchs):
    for n, p in enumerate(patchs, 1):
        off = int(p["offset"], 16)
        lg = longueur_avant(p["avant"])
        apres = octets("apres", p["apres"])
        if len(apres) > lg:
            sys.exit(f"patch {n} : « apres » ({len(apres)} octets) plus long que « avant » ({lg})")
        apres = apres.ljust(lg, b" ")
        if off + lg > len(data) - 2:
            sys.exit(f"patch {n} : déborde sur le CRC final")
        if not avant_conforme(data, off, p["avant"]):
            sys.exit(f"patch {n} : à {hex(off)}, les octets ne sont pas ceux du firmware d'origine attendu "
                     "(autre version, ou patch déjà appliqué ?)")
        data[off:off + lg] = apres
    data[-2:] = crc16_xmodem(data[:-2]).to_bytes(2, "big")
    return data


# D200 B (d200/recherche/d200-firmware-image.md §6) : plages que le flasheur réécrit, et zones à ne jamais toucher (chaîne
# de mise à jour, flasheur et ses tables, pointeurs de signature et de version). Un patch ailleurs que dans les plages
# réécrites ne serait pas flashé ; un patch dans une zone interdite peut empêcher toute mise à jour suivante.
D200_ECRITS = [(0x050000, 0x0EFFFF), (0x120000, 0x1CFFFF), (0x200000, 0x40FFFF)]
D200_INTERDITS = [(0xEFBF0, 0xEFFFF, "pointeurs de signature et de version, vecteurs"),
                  (0x9A680, 0x9B14A, "chaîne de mise à jour"), (0x54552, 0x54751, "CRC16 de la mise à jour"),
                  (0x15D284, 0x15D483, "table du CRC16"), (0x15C72C, 0x15CA63, "flasheur"),
                  (0x15387C, 0x15390B, "tables du flasheur"), (0x15E008, 0x15E107, "commandes vers le processeur A"),
                  (0x16C760, 0x16C85F, "chaîne de mise à jour (données)"), (0x16CB18, 0x16CC17, "chaîne de mise à jour (données)")]


def secteur_d200(a):
    """Secteur de flash de l'adresse : 8 Ko en 0x3F0000-0x3FFFFF (secteurs d'amorce en haut), 64 Ko ailleurs."""
    taille = 0x2000 if 0x3F0000 <= a < 0x400000 else 0x10000
    return a - a % taille, taille


def controler_d200(patchs, orig=None):
    for n, p in enumerate(patchs, 1):
        a = int(p["offset"], 16) + 0x50000
        b = a + longueur_avant(p["avant"]) - 1
        if not any(lo <= a and b <= hi for lo, hi in D200_ECRITS):
            sys.exit(f"patch {n} ({hex(a)}-{hex(b)}) : hors des plages réécrites par la mise à jour du D200")
        # Un secteur sans aucun octet de Nikon n'a jamais été programmé par une mise à jour officielle : il peut être
        # protégé en écriture, et le flasheur échouerait après avoir effacé le code principal
        # (d200/recherche/d200-v2-relecture.md).
        s = a - a % 0x2000 if orig is not None else None
        while orig is not None and s <= b:
            s, taille = secteur_d200(s)
            if all(x == 0xFF for x in orig[s - 0x50000:s - 0x50000 + taille]):
                sys.exit(f"patch {n} ({hex(a)}-{hex(b)}) : secteur {hex(s)} sans aucun octet de Nikon, jamais programmé")
            s += taille
        for lo, hi, quoi in D200_INTERDITS:
            if a <= hi and b >= lo:
                sys.exit(f"patch {n} ({hex(a)}-{hex(b)}) : touche {quoi} ({hex(lo)}-{hex(hi)}), interdit")


def differences(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def self_test():
    orig = bytes(charger_original())
    nul = appliquer(bytearray(orig), [])
    assert bytes(nul) == orig, "sans patch, le fichier doit ressortir identique"
    p = [{"offset": "0x2722d8", "avant": "MENU CONFIGURATION", "apres": "TEST"}]
    mod = appliquer(bytearray(orig), p)
    assert mod[0x2722d8:0x2722d8 + 18] == b"TEST" + b" " * 14
    assert crc16_xmodem(mod[:-2]) == int.from_bytes(mod[-2:], "big")
    assert differences(orig[:-2], mod[:-2]) <= 18
    # même patch, octets d'origine donnés par leur empreinte
    h = {"sha256": hashlib.sha256(b"MENU CONFIGURATION").hexdigest(), "longueur": 18}
    assert bytes(appliquer(bytearray(orig), [dict(p[0], avant=h)])) == bytes(mod)
    for mauvais in ([{"offset": "0x2722d8", "avant": "MENU CONFIGURATIOX", "apres": "A"}],
                    [{"offset": "0x2722d8", "avant": "MENU", "apres": "TROP LONG"}],
                    [{"offset": "0x2722d9", "avant": h, "apres": "A"}]):
        try:
            appliquer(bytearray(orig), mauvais)
        except SystemExit:
            pass
        else:
            raise AssertionError(f"patch invalide accepté : {mauvais}")
    for cle in ("A", "A112", "D200B", "D200A"):
        if ORIGINAUX[cle][0].is_file():
            a = bytes(charger_original(cle))
            assert bytes(appliquer(bytearray(a), [])) == a, f"firmware {cle} : sans patch, fichier identique"
    for mauvais in (0xEFC00, 0x9A700, 0x15C800, 0x100000, 0x1D8000):   # D200 : interdit (3) puis jamais flashé (2)
        try:
            controler_d200([{"offset": hex(mauvais - 0x50000), "avant": {"hex": "00"}, "apres": {"hex": "01"}}])
        except SystemExit:
            pass
        else:
            raise AssertionError(f"patch D200 à {hex(mauvais)} accepté")
    controler_d200([{"offset": hex(0x177000 - 0x50000), "avant": {"hex": "ff"}, "apres": {"hex": "00"}}])
    print("self-test OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("patchs", nargs="?", help="fichier JSON de patchs")
    ap.add_argument("--sortie", help="dossier de sortie (racine de la carte SD possible) ; défaut : d40/build/ ou d200/build/")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.patchs:
        ap.error("fichier de patchs manquant")
    doc = json.loads(Path(args.patchs).read_text(encoding="utf-8"))
    firmware = doc.get("firmware", "B")
    orig = bytes(charger_original(firmware))
    patchs = doc["patchs"]
    if firmware == "D200B":
        controler_d200(patchs, orig)
    mod = appliquer(bytearray(orig), patchs)
    sortie = Path(args.sortie) if args.sortie else (ICI.parent / "d200" / "build" if firmware.startswith("D200") else ICI / "build")
    sortie.mkdir(parents=True, exist_ok=True)
    cible = sortie / ORIGINAUX[firmware][2]
    cible.write_bytes(mod)
    print(f"{len(patchs)} patch(s), {differences(orig, mod)} octets changés (CRC compris)")
    print(f"CRC {mod[-2:].hex()} -> {cible}")
    print(f"sha256 {hashlib.sha256(mod).hexdigest()}")


if __name__ == "__main__":
    main()
