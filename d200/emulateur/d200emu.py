#!/usr/bin/env python3
"""Émulateur du processeur B du Nikon D200 (firmware B 2.01) : appel de fonctions, lanceur.

Même cœur FR que l'émulateur du D40 (d40/emulateur/d40emu.py, nikon-firmware-tools), classes propres au D200
dans d200/emulateur/java. Rien ne démarre : un scénario prépare la mémoire, appelle les fonctions du firmware
et vérifie ce qu'elles écrivent (variables, fiche de prise de vue, registres de la puce d'image 0x5001xxxx).

    python3 d200/emulateur/d200emu.py verifier                 # N&B, couleur, préréglages : code 0 si conforme
    python3 d200/emulateur/d200emu.py scenario nb-origine      # scénario d200/emulateur/scenarios/nb-origine.txt
    python3 d200/emulateur/d200emu.py scenario nb-origine --firmware <B2000201.BIN>
    python3 d200/emulateur/d200emu.py patch d200/patchs/d200-nb-trix.json nb-trix   # d40/patch.py dans le cache, puis le scénario
    python3 d200/emulateur/d200emu.py combine preglages        # Tri-X + noms + préréglages (COMBINE), puis le scénario
    python3 d200/emulateur/d200emu.py desassembler 0xD7830 50 [--firmware ...]

Tout ce qui est compilé ou fabriqué va dans --travail (défaut ~/Library/Caches/d40-emulateur/d200, hors du dépôt).
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
PROJET = ICI.parent.parent
sys.path.insert(0, str(PROJET / 'd40' / 'emulateur'))
sys.dont_write_bytecode = True  # pas de __pycache__ dans le dossier synchronisé
import d40emu  # noqa: E402  (jdk() et dépôt de nikon-firmware-tools, rien d'autre)

ORIGINAL = Path.home() / "Library/Caches/retro-ingenierie-boitiers/firmware/d200-201/B2000201.bin"
# firmware combiné de « verifier » : N&B Tri-X, noms du menu, préréglages (d200/outils/d200_preglages.py)
COMBINE = ["d200-nb-trix.json", "d200-noms.json", "d200-preglages.json"]
SHA_ORIGINAL = "b7cee24dd2034645337cca500109d2ce987bee4ba8bfb521c3285c623f3407d1"


def compiler(travail, nft, cloner):
    emu = nft / "Java" / "Emulator"
    if not (emu / "src" / "main").exists():
        if not cloner:
            sys.exit(f"cœur FR introuvable dans {nft}\n  git clone {d40emu.DEPOT_NFT} {nft}\n  (ou relancer avec --cloner)")
        subprocess.run(["git", "clone", "--depth", "1", d40emu.DEPOT_NFT, str(nft)], check=True)
    classes = travail / "classes"
    sources = sorted((ICI / "java").glob("*.java"))
    tampon = classes / ".compile"
    if tampon.exists() and all(s.stat().st_mtime < tampon.stat().st_mtime for s in sources):
        return classes
    gen = travail / "gen" / "com" / "nikonhacker"
    gen.mkdir(parents=True, exist_ok=True)
    modele = (emu / "src" / "template" / "com" / "nikonhacker" / "ApplicationInfo.java").read_text()
    (gen / "ApplicationInfo.java").write_text(
        modele.replace("@APPNAME@", "NikonEmulator").replace("@APPVERSION@", "d200").replace("@BUILDTIME@", "d200"))
    if classes.exists():
        shutil.rmtree(classes)  # dossier créé par ce script, hors du dépôt
    classes.mkdir(parents=True)
    cp = os.pathsep.join(str(j) for j in sorted((emu / "lib").glob("*.jar")))
    print("compilation de l'émulateur du D200…", file=sys.stderr)
    r = subprocess.run([str(d40emu.jdk() / "javac"), "-nowarn", "-encoding", "UTF-8",
                        "-sourcepath", f"{emu / 'src' / 'main'}{os.pathsep}{travail / 'gen'}",
                        "-cp", cp, "-d", str(classes)] + [str(s) for s in sources],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stdout + r.stderr)
    tampon.touch()
    return classes


def lancer(args, firmware, extra):
    travail = Path(args.travail).expanduser()
    nft = Path(args.nft).expanduser() if args.nft else Path("~/Library/Caches/d40-emulateur/nft").expanduser()
    classes = compiler(travail, nft, args.cloner)
    cp = os.pathsep.join([str(classes)] + [str(j) for j in sorted((nft / "Java" / "Emulator" / "lib").glob("*.jar"))])
    cmd = [str(d40emu.jdk() / "java"), "-cp", cp, "com.nikonhacker.emu.D200Boot", str(firmware)] + extra
    return subprocess.run(cmd).returncode  # attend la fin de la JVM : aucun processus ne reste


def scenario_path(nom):
    p = Path(nom)
    if p.exists():
        return p
    p = ICI / "scenarios" / f"{nom}.txt"
    if not p.exists():
        sys.exit(f"scénario introuvable : {nom}")
    return p


def fabriquer(patch_json, travail):
    """Applique un patch avec d40/patch.py (octets d'origine et sha256 vérifiés, CRC recalculé), dans le cache."""
    dest = Path(travail).expanduser() / "firmwares" / Path(patch_json).stem
    subprocess.run([sys.executable, str(PROJET / "d40/patch.py"), str(patch_json), "--sortie", str(dest)], check=True)
    return dest / "B2000201.BIN"


def combiner(noms, travail):
    """Un JSON qui réunit les patchs de plusieurs fichiers de d200/patchs/ (même firmware), écrit dans le cache, puis
    fabriqué par d40/patch.py (qui refuse un chevauchement : octets d'origine vérifiés patch par patch)."""
    doc = {"firmware": "D200B", "description": "combiné : " + ", ".join(noms), "patchs": []}
    for n in noms:
        d = json.loads((PROJET / "d200" / "patchs" / n).read_text(encoding="utf-8"))
        if d.get("firmware") != "D200B":
            sys.exit(f"{n} : pas un patch du D200 B")
        doc["patchs"] += d["patchs"]
    j = Path(travail).expanduser() / "d200-combine.json"
    j.parent.mkdir(parents=True, exist_ok=True)
    j.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return fabriquer(j, travail)


def controler_original():
    if not ORIGINAL.exists():
        sys.exit(f"firmware d'origine introuvable : {ORIGINAL}")
    if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != SHA_ORIGINAL:
        sys.exit(f"{ORIGINAL} n'est pas le B 2.01 d'origine (sha256 différent)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--travail", default="~/Library/Caches/d40-emulateur/d200")
    ap.add_argument("--nft", help="clone de nikon-firmware-tools (défaut : celui de l'émulateur du D40)")
    ap.add_argument("--cloner", action="store_true")
    ap.add_argument("--firmware", default=str(ORIGINAL))
    ap.add_argument("commande", choices=["verifier", "scenario", "patch", "combine", "desassembler", "compiler"])
    ap.add_argument("arguments", nargs="*")
    args = ap.parse_args()
    travail = Path(args.travail).expanduser()

    if args.commande == "compiler":
        compiler(travail, Path(args.nft or "~/Library/Caches/d40-emulateur/nft").expanduser(), args.cloner)
        return 0
    if args.commande == "desassembler":
        return lancer(args, args.firmware, ["--disasm"] + args.arguments[:2])
    if args.commande == "scenario":
        if args.firmware == str(ORIGINAL):
            controler_original()
        return lancer(args, args.firmware, ["--script", str(scenario_path(args.arguments[0]))])
    if args.commande == "patch":
        fw = fabriquer(args.arguments[0], travail)
        return lancer(args, fw, ["--script", str(scenario_path(args.arguments[1]))])
    if args.commande == "combine":
        fw = combiner(COMBINE, travail)
        return lancer(args, fw, ["--script", str(scenario_path(args.arguments[0]))])
    if args.commande == "verifier":
        controler_original()
        trix = fabriquer(PROJET / "d200" / "patchs" / "d200-nb-trix.json", travail)
        comb = combiner(COMBINE, travail)
        tests = [
            ("a. N&B, firmware d'origine", ORIGINAL, "nb-origine", 0),
            ("b. N&B, firmware patché Tri-X (d200/patchs/d200-nb-trix.json)", trix, "nb-trix", 0),
            ("b'. contre-épreuve : les contrôles Tri-X sur le firmware d'origine (doivent échouer)", ORIGINAL, "nb-trix", 1),
            ("b''. N&B, firmware combiné : toujours Tri-X", comb, "nb-trix", 0),
            ("c. couleur, firmware d'origine", ORIGINAL, "couleur-origine", 0),
            ("c'. couleur, firmware patché Tri-X (le patch ne touche pas la couleur)", trix, "couleur-origine", 0),
            ("d. préréglages, firmware combiné Tri-X + noms + préréglages", comb, "preglages", 0),
            ("d'. contre-épreuve : les contrôles des préréglages sur le firmware d'origine (doivent échouer)", ORIGINAL, "preglages", 1),
            ("d''. contre-épreuve : sur le firmware Tri-X seul, sans les crochets (doivent échouer)", trix, "preglages", 1),
            ("garde : LDI:32 posé dans un créneau de délai (doit être arrêté)", ORIGINAL, "garde-delai", 2),
            ("garde : appel au noyau non émulé (doit être arrêté)", ORIGINAL, "garde-noyau", 2),
        ]
        bilan = []
        for titre, fw, sc, attendu in tests:
            print(f"\n===== {titre}", flush=True)
            bilan.append((titre, lancer(args, fw, ["--script", str(scenario_path(sc))]), attendu))
        print("\n===== bilan du D200")
        for titre, code, attendu in bilan:
            print(f"{'OK   ' if code == attendu else 'ÉCHEC'} {titre} (code {code}, attendu {attendu})")
        return 0 if all(c == a for _, c, a in bilan) else 1


if __name__ == "__main__":
    sys.exit(main())
