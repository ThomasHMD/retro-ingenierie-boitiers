#!/usr/bin/env python3
"""Ouvrir le firmware officiel du D750 pour l'analyse statique (rien n'est modifié, rien n'est envoyé à un boîtier).

  d750_firmware.py extraire <F-D750-V115M.dmg | D750_0115.bin> <dossier> [--tables Firmware.cs]
        sort D750_0115.bin d'un .dmg (UDIF zlib, HFS+), le déchiffre et écrit ses modules (a…bin, b…bin)
        (outils/references.sh installe tout et le fait pour un firmware posé dans le cache)
  d750_firmware.py ptp <b1010_115a.bin>                 table des commandes PTP 0x90xx / 0x92xx / 0x94xx
  d750_firmware.py dis <b1010_115a.bin> <adresse> [n]   désassemble n instructions Thumb (littéraux résolus)
  d750_firmware.py appels <b1010_115a.bin> <adresse>…   BL / BLX qui visent ces adresses

Firmware.cs (par défaut celui du cache de references.sh) : `firmware decode/firmware decode/Firmware.cs` de
nikon-firmware-tools (github.com/simeonpilgrim), qui porte
les trois tables XOR ; l'entête de 0x20 octets reste en clair, l'index des tables part du début du fichier, le répertoire
(à 0x20, gros-boutiste : nombre, taille, puis 32 octets par module ; début compté depuis le début du fichier) suit
nikon-fw-key-tool (github.com/WonderLantern).
La partie B se charge à 0x90020000 (nikon-firmware-tools, IDA_files/D750/D750_Setup_RAM_1.10.idc). dis : pip install capstone.
Vérifié en octobre 2026 sur C 1.15 (sha256 du .bin 6c1dfadc…44859) et C 1.10.
"""
import binascii, os, plistlib, re, struct, sys, zlib, bz2

BASE_B = 0x90020000
CACHE = os.environ.get('RETRO_CACHE') or os.path.expanduser('~/Library/Caches/retro-ingenierie-boitiers' if sys.platform == 'darwin' else '~/.cache/retro-ingenierie-boitiers')
TABLES = os.path.join(CACHE, 'nikon-firmware-tools', 'firmware decode', 'firmware decode', 'Firmware.cs')


def dmg_vers_bin(chemin):
    d = open(chemin, 'rb').read()
    xo, xl = struct.unpack('>QQ', d[-512:][0xd8:0xe8])
    img = bytearray()
    for b in plistlib.loads(d[xo:xo + xl])['resource-fork']['blkx']:
        m = b['Data']
        debut, dat = struct.unpack('>Q', m[8:16])[0], struct.unpack('>Q', m[0x18:0x20])[0]
        for i in range(struct.unpack('>I', m[0xc8:0xcc])[0]):
            t, _, s, sc, co, cl = struct.unpack('>IIQQQQ', m[0xcc + 40 * i:0xcc + 40 * (i + 1)])
            c = d[dat + co:dat + co + cl]
            if t == 0xffffffff or t == 0x7ffffffe: continue
            bloc = {0x80000005: lambda: zlib.decompress(c), 0x80000006: lambda: bz2.decompress(c), 1: lambda: c}.get(t, lambda: b'\0' * (sc * 512))()
            pos = (debut + s) * 512
            img[len(img):pos] = b'\0' * max(0, pos - len(img))
            img[pos:pos + len(bloc)] = bloc
    hplus = img.find(b'H+\x00\x04'); vol = hplus - 0x400
    taille_bloc = struct.unpack('>I', img[hplus + 0x28:hplus + 0x2c])[0]
    for m in re.finditer(re.escape('_0'.encode('utf-16-be')), img):   # enregistrement du catalogue « D750_0nnn.bin »
        p = m.start() - 8
        n = struct.unpack('>H', img[p - 2:p])[0]
        nom = img[p:p + 2 * n].decode('utf-16-be', 'replace')
        r = p + 2 * n
        if re.fullmatch(r'D750_0\d{3}\.bin', nom) and struct.unpack('>h', img[r:r + 2])[0] == 2:
            taille = struct.unpack('>Q', img[r + 88:r + 96])[0]
            ext = [struct.unpack('>II', img[r + 104 + 8 * k:r + 112 + 8 * k]) for k in range(8)]
            return nom, b''.join(img[vol + s * taille_bloc:vol + (s + c) * taille_bloc] for s, c in ext if c)[:taille]
    raise SystemExit('pas de D750_0nnn.bin dans le .dmg')


def dechiffrer(raw, firmware_cs):
    src = open(firmware_cs, encoding='utf-8-sig').read()
    t = [[int(x, 16) & 0xFF for x in re.findall(r'0x[0-9a-fA-F]+', re.search(n + r'\s*=\s*\{(.*?)\};', src, re.S).group(1))]
         for n in ('Xor_Ord1', 'Xor_Ord2', 'Xor_Ord3')]
    d = bytearray(raw)
    for i in range(0x20, len(d)):
        d[i] ^= t[0][i & 0xFF] ^ t[1][(i >> 8) & 0xFF] ^ t[2][(i >> 16) & 0xFF]
    n = struct.unpack('>I', d[0x20:0x24])[0]
    mods = []
    for c in range(n):
        o = 0x30 + 32 * c
        debut, lon = struct.unpack('>II', d[o + 16:o + 24])
        mods.append((d[o:o + 16].split(b'\0')[0].decode('ascii'), bytes(d[debut:debut + lon])))
    return mods


def table_ptp(b):
    """Entrées de 0x1C octets : code, sens des données (1 = vers l'hôte), ?, réception, contrôle, exécution, fin."""
    for i in range(0, len(b) - 0x1C, 4):
        w = struct.unpack('<7I', b[i:i + 0x1C])
        if w[0] >> 8 in (0x90, 0x92, 0x94) and all(p == 0 or BASE_B <= p < BASE_B + len(b) for p in w[3:]) and any(w[4:6]):
            yield BASE_B + i, w


def dis(b, adresse, n=60):
    try: import capstone
    except ImportError: raise SystemExit(f'Capstone absent : lancer avec {CACHE}/venv/bin/python3 (installé par outils/references.sh)')
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB); md.detail = True
    a = adresse & ~1
    for ins in md.disasm(b[a - BASE_B:a - BASE_B + 4 * n], a):
        lit = ''
        if ins.mnemonic.startswith('ldr') and '[pc' in ins.op_str:
            for op in ins.operands:
                if op.type == capstone.arm.ARM_OP_MEM and op.mem.base == capstone.arm.ARM_REG_PC:
                    o = ((ins.address + 4) & ~3) + op.mem.disp - BASE_B
                    if 0 <= o < len(b) - 3: lit = '  ; =0x%08x' % struct.unpack('<I', b[o:o + 4])[0]
        print('%08x  %-8s %s%s' % (ins.address, ins.mnemonic, ins.op_str, lit))
        n -= 1
        if not n: break


def appels(b, cibles):
    hw = struct.unpack('<%dH' % (len(b) // 2), b[:len(b) // 2 * 2])
    for k in range(len(hw) - 1):
        h1, h2 = hw[k], hw[k + 1]
        if h1 & 0xF800 != 0xF000 or h2 & 0xC000 != 0xC000: continue
        s = (h1 >> 10) & 1
        off = (s << 24) | ((1 - (((h2 >> 13) & 1) ^ s)) << 23) | ((1 - (((h2 >> 11) & 1) ^ s)) << 22) | ((h1 & 0x3FF) << 12) | ((h2 & 0x7FF) << 1)
        off -= (1 << 25) if s else 0
        pc = BASE_B + 2 * k + 4
        t = pc + off if h2 & 0x1000 else (pc & ~3) + off
        if t in cibles: print('%08x -> %08x %s' % (BASE_B + 2 * k, t, 'bl' if h2 & 0x1000 else 'blx'))


if __name__ == '__main__':
    a = sys.argv[1:]
    tables = TABLES
    if '--tables' in a:
        k = a.index('--tables'); tables = a[k + 1]; del a[k:k + 2]
    if len(a) == 3 and a[0] == 'extraire':
        if not os.path.exists(tables): raise SystemExit(f'tables XOR introuvables ({tables}) : lancer bash outils/references.sh')
        if a[1].lower().endswith('.dmg'): nom, raw = dmg_vers_bin(a[1])
        else: nom, raw = os.path.basename(a[1]), open(a[1], 'rb').read()
        os.makedirs(a[2], exist_ok=True)
        open(os.path.join(a[2], nom), 'wb').write(raw)
        for m, contenu in dechiffrer(raw, tables):
            crc = 'CRC bon' if binascii.crc_hqx(contenu, 0) == 0 else 'CRC FAUX : déchiffrement raté'   # CRC16 0x1021 final, gros-boutiste
            print(m, len(contenu), crc); open(os.path.join(a[2], m), 'wb').write(contenu)
    elif len(a) == 2 and a[0] == 'ptp':
        for adr, w in table_ptp(open(a[1], 'rb').read()): print('%04x @%08x ' % (w[0], adr) + ' '.join('%08x' % x for x in w[1:]))
    elif len(a) in (3, 4) and a[0] == 'dis':
        dis(open(a[1], 'rb').read(), int(a[2], 16), int(a[3]) if len(a) == 4 else 60)
    elif len(a) >= 3 and a[0] == 'appels':
        appels(open(a[1], 'rb').read(), {int(x, 16) & ~1 for x in a[2:]})
    else:
        print(__doc__); sys.exit(2)
