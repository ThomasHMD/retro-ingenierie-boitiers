#!/usr/bin/env python3
"""Émulateur du processeur B du Nikon D40 : lanceur.

Compile l'émulateur (sources Java de emulateur/java + cœur FR de nikon-firmware-tools) dans un
dossier de travail hors du dépôt, puis le lance sur un firmware et un scénario.

    python3 emulateur/d40emu.py verifier                      # les 4 tests, code de sortie 0 si tout va bien
    python3 emulateur/d40emu.py scenario menu                 # scénario emulateur/scenarios/menu.txt
    python3 emulateur/d40emu.py scenario menu --firmware build/BD400111.BIN
    python3 emulateur/d40emu.py patch patchs/pipboy-palette.json menu-fr   # fabrique le firmware (patch.py) puis le teste
    python3 emulateur/d40emu.py desassembler 0x143B46 20 [--firmware ...]

Options communes : --travail DIR (défaut ~/Library/Caches/d40-emulateur), --nft DIR (clone de
nikon-firmware-tools, défaut <travail>/nft), --cloner (le cloner s'il manque), --sortie DIR.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
PROJET = ICI.parent
ORIGINAL_A = PROJET / "firmware" / "AD400111.bin"
ORIGINAL = PROJET / "firmware" / "BD400111.bin"
DEPOT_NFT = "https://github.com/simeonpilgrim/nikon-firmware-tools"


def jdk():
    for p in ("/opt/homebrew/opt/openjdk@17/bin", "/opt/homebrew/opt/openjdk/bin"):
        if Path(p, "javac").exists():
            return Path(p)
    j = shutil.which("javac")
    if not j:
        sys.exit("javac introuvable : il faut un JDK 17 ou plus récent")
    return Path(j).parent


def compiler(travail, nft, cloner):
    emu = nft / "Java" / "Emulator"
    if not (emu / "src" / "main").exists():
        if not cloner:
            sys.exit(f"cœur FR introuvable dans {nft}\n  git clone {DEPOT_NFT} {nft}\n  (ou relancer avec --cloner)")
        subprocess.run(["git", "clone", "--depth", "1", DEPOT_NFT, str(nft)], check=True)
    classes = travail / "classes"
    sources = sorted((ICI / "java").glob("*.java"))
    tampon = classes / ".compile"
    if tampon.exists() and all(s.stat().st_mtime < tampon.stat().st_mtime for s in sources):
        return classes
    gen = travail / "gen" / "com" / "nikonhacker"
    gen.mkdir(parents=True, exist_ok=True)
    modele = (emu / "src" / "template" / "com" / "nikonhacker" / "ApplicationInfo.java").read_text()
    (gen / "ApplicationInfo.java").write_text(
        modele.replace("@APPNAME@", "NikonEmulator").replace("@APPVERSION@", "d40").replace("@BUILDTIME@", "d40"))
    if classes.exists():
        shutil.rmtree(classes)  # dossier créé par ce script, hors du dépôt
    classes.mkdir(parents=True)
    cp = os.pathsep.join(str(j) for j in sorted((emu / "lib").glob("*.jar")))
    print("compilation de l'émulateur…", file=sys.stderr)
    r = subprocess.run([str(jdk() / "javac"), "-nowarn", "-encoding", "UTF-8",
                        "-sourcepath", f"{emu / 'src' / 'main'}{os.pathsep}{travail / 'gen'}",
                        "-cp", cp, "-d", str(classes)] + [str(s) for s in sources],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stdout + r.stderr)
    tampon.touch()
    return classes


def lancer(args, firmware, extra, classe="Boot"):
    travail = Path(args.travail).expanduser()
    nft = Path(args.nft).expanduser() if args.nft else travail / "nft"
    classes = compiler(travail, nft, args.cloner)
    cp = os.pathsep.join([str(classes)] + [str(j) for j in sorted((nft / "Java" / "Emulator" / "lib").glob("*.jar"))])
    cmd = [str(jdk() / "java"), "-cp", cp, "com.nikonhacker.emu." + classe, str(firmware)] + extra
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
    """Applique un patch avec patch.py (vérifie les octets d'origine, recalcule le CRC)."""
    dest = Path(travail).expanduser() / "firmwares" / Path(patch_json).stem
    subprocess.run([sys.executable, str(PROJET / "patch.py"), str(patch_json), "--sortie", str(dest)], check=True)
    return dest / "BD400111.BIN"


# Octet 0x83CED0FF : les deux réglages Style écran infos (bits 6-7 et 4-5 ; 0 Classique, 1 Graphique,
# 2 Fond d'écran), bit 0 gardé à sa valeur de départ. Recherche : recherche/ecran-reel-composition.md.
STYLES = {"classique": 0x01, "graphique": 0x51, "fond": 0xA1}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--travail", default="~/Library/Caches/d40-emulateur")
    ap.add_argument("--nft")
    ap.add_argument("--cloner", action="store_true")
    ap.add_argument("--firmware", default=str(ORIGINAL))
    ap.add_argument("--sortie")
    ap.add_argument("--verbeux", action="store_true", help="journal du faux A et du moteur 2D")
    ap.add_argument("--style", choices=list(STYLES) + ["tous"], default="classique",
                    help="CONFIG › Style écran infos simulé (défaut : classique, le réglage du boîtier de Thomas) ; "
                         "« tous » joue le scénario en classique puis en graphique")
    ap.add_argument("--firmware-a", help="firmware du processeur A (défaut : firmware/AD400111.bin)")
    ap.add_argument("commande", choices=["scenario", "patch", "crochet", "verifier", "desassembler", "compiler",
                                         "a-scenario", "a-desassembler", "a-demarrer", "a-verifier"])
    ap.add_argument("arguments", nargs="*")
    args = ap.parse_args()
    travail = Path(args.travail).expanduser()

    def sortie(nom):
        return args.sortie or str(travail / "sorties" / nom)

    opts = ["--verbeux"] if args.verbeux else []
    styles = ["classique", "graphique"] if args.style == "tous" else [args.style]

    def jouer(fw, sc, nom):
        """Joue le scénario dans chaque style demandé ; captures dans <sortie>/<style>/ si plusieurs."""
        codes = []
        for st in styles:
            dossier = sortie(nom) if len(styles) == 1 else str(Path(sortie(nom)) / st)
            print(f"\n===== {Path(sc).stem}, style {st}", flush=True)
            codes.append(lancer(args, fw, ["--script", str(sc), "--sortie", dossier,
                                           "--style", hex(STYLES[st])] + opts))
        if len(styles) > 1:
            print("\n===== bilan des styles")
            for st, c in zip(styles, codes):
                print(f"{'OK   ' if c == 0 else 'ÉCHEC'} {st} (code {c})")
        return max(codes)
    if args.commande == "compiler":
        compiler(travail, Path(args.nft).expanduser() if args.nft else travail / "nft", args.cloner)
        return 0
    # processeur A (étude d’octobre 2026, recherche/etude-a/emulation.md) : AEmu, AIo, ABoot, FakeB
    fw_a = args.firmware_a or str(ORIGINAL_A)
    if args.commande == "a-desassembler":
        return lancer(args, fw_a, ["--disasm"] + args.arguments[:2], "ABoot")
    if args.commande == "a-demarrer":   # a-demarrer [N] : le A seul depuis son reset (--verbeux : E/S)
        return lancer(args, fw_a, ["--max", args.arguments[0] if args.arguments else "20M"]
                      + (["--io"] if args.verbeux else []), "ABoot")
    if args.commande == "a-scenario":
        return lancer(args, fw_a, ["--script", str(scenario_path(args.arguments[0]))], "ABoot")
    if args.commande == "a-verifier":   # les essais du A, avec le code de sortie attendu
        tests = [("ligne de P appelée directement (7 cas, 14 contrôles)", "a-ligne-p", 0),
                 ("chaîne complète expo_programme, ISO auto", "a-expo-programme", 0),
                 ("patch voie 1 (constante) et voie 2 (ligne perso en 0xF3910)", "a-patch-ligne", 0),
                 ("patch fautif, LDI:32 dans un créneau de délai (doit être refusé)", "a-garde-delai", 2),
                 ("démarrage, EEPROM simulée", "a-boot-valide", 0),
                 ("liaison B→A, commande 0x05", "a-liaison-05", 0),
                 ("liaison A→B, commande 0x14", "a-liaison-14", 0)]
        bilan = []
        for titre, sc, attendu in tests:
            print(f"\n===== {titre}", flush=True)
            bilan.append((titre, lancer(args, fw_a, ["--script", str(scenario_path(sc))], "ABoot"), attendu))
        # firmware A fabriqué par patch.py (octets d'origine vérifiés, CRC recalculé), puis joué tel quel
        dest = fabriquer(ICI / "tests" / "a-sujet-rapide.json", travail)
        titre = "firmware A patché par patch.py (tests/a-sujet-rapide.json)"
        print(f"\n===== {titre}", flush=True)
        bilan.append((titre, lancer(args, str(dest.parent / "AD400111.BIN"),
                                    ["--script", str(scenario_path("a-firmware-patche"))], "ABoot"), 0))
        # lignes de programme (outils/programmes_a.py), A 1.11 et A 1.12 : le patch du projet, puis la contre-épreuve
        # sur le A de Nikon
        for version, suffixe, nom, nikon in (("1.11", "", "AD400111.BIN", ORIGINAL_A),
                                             ("1.12", "-112", "AD400112.BIN", PROJET / "firmware" / "AD400112.bin")):
            dest = fabriquer(PROJET / "patchs" / f"a-programmes{suffixe}.json", travail)
            sc = str(scenario_path(f"a-programmes{suffixe}"))
            for titre, fw, attendu in ((f"lignes de programme, A {version}, patchs/a-programmes{suffixe}.json (120 cas)",
                                        dest.parent / nom, 0),
                                       (f"les mêmes cas sur le A {version} de Nikon (doivent échouer)", nikon, 1)):
                print(f"\n===== {titre}", flush=True)
                bilan.append((titre, lancer(args, str(fw), ["--script", sc], "ABoot"), attendu))
        print("\n===== bilan du A")
        for titre, code, attendu in bilan:
            print(f"{'OK   ' if code == attendu else 'ÉCHEC'} {titre} (code {code}, attendu {attendu})")
        return 0 if all(c == a for _, c, a in bilan) else 1
    if args.commande == "desassembler":
        return lancer(args, args.firmware, ["--disasm"] + args.arguments[:2])
    if args.commande == "scenario":
        sc = scenario_path(args.arguments[0] if args.arguments else "demarrage")
        return jouer(args.firmware, sc, sc.stem)
    if args.commande in ("patch", "crochet"):
        fw = fabriquer(args.arguments[0], travail)
        sc = scenario_path(args.arguments[1] if len(args.arguments) > 1 else "menu")
        return jouer(fw, sc, Path(args.arguments[0]).stem)
    if args.commande == "verifier":
        tests = [
            ("démarrage, firmware d'origine", ORIGINAL, "demarrage", 0),
            ("menus et touches, firmware d'origine", ORIGINAL, "menu", 0),
            ("crochet valide (tests/crochet-menu.json)", ICI / "tests" / "crochet-menu.json", "crochet", 0),
            ("crochet fautif, ldi:32 dans un créneau de délai (doit être refusé)",
             ICI / "tests" / "crochet-delai-interdit.json", "crochet", 2),
        ]
        bilan = []
        for titre, src, sc, attendu in tests:
            fw = fabriquer(src, travail) if str(src).endswith(".json") else src
            print(f"\n===== {titre}", flush=True)
            code = lancer(args, fw, ["--script", str(scenario_path(sc)), "--sortie", sortie(Path(src).stem + "-" + sc),
                                     "--style", hex(STYLES[styles[0]])] + opts)
            bilan.append((titre, code, attendu))
        print("\n===== bilan")
        ok = True
        for titre, code, attendu in bilan:
            bon = code == attendu
            ok &= bon
            print(f"{'OK   ' if bon else 'ÉCHEC'} {titre} (code {code}, attendu {attendu})")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
