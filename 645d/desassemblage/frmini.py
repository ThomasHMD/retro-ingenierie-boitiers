# Mini-interpréteur FR (sous-ensemble) pour exécuter des fonctions feuilles du firmware 645D.
# Usage en module : run(b, addr, regs) -> regs ; b = octets du fichier décodé (base 0x10000000).
import struct, sys

BASE = 0x10000000
M = 0xFFFFFFFF


def s32(v):
    v &= M
    return v - (1 << 32) if v & 0x80000000 else v


class Unk(Exception):
    pass


def run(b, pc, regs=None, maxsteps=5000, mem=None):
    R = [0] * 16 if regs is None else list(regs)
    R[15] = 0x80F00000
    N = Z = V = C = 0
    mem = mem if mem is not None else {}

    def h(a):
        o = a - BASE
        return (b[o] << 8) | b[o + 1]

    def w(a):
        o = a - BASE
        return struct.unpack_from('>I', b, o)[0]

    def setcmp(x, y):  # flags of x - y
        nonlocal N, Z, V, C
        r = (x - y) & M
        N = r >> 31
        Z = int(r == 0)
        V = int(((x ^ y) & (x ^ r)) >> 31 & 1)
        C = int((x & M) < (y & M))

    def cond(c):
        return [1, 0, Z, not Z, C, not C, N, not N, V, not V,
                N ^ V, not (N ^ V), (N ^ V) or Z, not ((N ^ V) or Z), C or Z, not (C or Z)][c]

    pending = None  # (target) to apply after delay slot
    steps = 0
    while steps < maxsteps:
        steps += 1
        op = h(pc)
        npc = pc + 2
        jump = None
        delayed = False
        hi = op >> 8
        if op == 0x9720:  # RET
            jump = 'RET'
        elif op == 0x9F20:
            jump = 'RET'; delayed = True
        elif hi == 0x9B:  # LDI:20
            r = op & 15; R[r] = ((op >> 4) & 15) << 16 | h(pc + 2); npc = pc + 4
        elif (op & 0xFFF0) == 0x9F80:
            R[op & 15] = w(pc + 2); npc = pc + 6
        elif (op >> 12) == 0xC:
            R[op & 15] = (op >> 4) & 0xFF
        elif hi == 0xAA:  # CMP Rj,Ri
            setcmp(R[op & 15], R[(op >> 4) & 15])
        elif hi == 0xA8:  # CMP #u4,Ri
            setcmp(R[op & 15], (op >> 4) & 15)
        elif hi == 0xA9:  # CMP2 #s4 (negative)
            setcmp(R[op & 15], ((op >> 4) & 15) - 16 & M)
        elif hi == 0xA4:  # ADD #u4,Ri
            x = R[op & 15]; y = (op >> 4) & 15; r = (x + y) & M; R[op & 15] = r; N = r >> 31; Z = int(r == 0)
        elif hi == 0xA5:  # ADD2 #-16..-1
            x = R[op & 15]; y = ((op >> 4) & 15) - 16; r = (x + y) & M; R[op & 15] = r; N = r >> 31; Z = int(r == 0)
            C = int(x + (y & M) > M)
        elif hi == 0xA6:  # ADD Rj,Ri
            r = (R[op & 15] + R[(op >> 4) & 15]) & M; R[op & 15] = r; N = r >> 31; Z = int(r == 0)
        elif hi == 0xAC:  # SUB Rj,Ri
            setcmp(R[op & 15], R[(op >> 4) & 15]); R[op & 15] = (R[op & 15] - R[(op >> 4) & 15]) & M
        elif hi == 0xAE:  # SUBN Rj,Ri
            R[op & 15] = (R[op & 15] - R[(op >> 4) & 15]) & M
        elif hi == 0xA0:  # ADDN #u4,Ri
            R[op & 15] = (R[op & 15] + ((op >> 4) & 15)) & M
        elif hi == 0xA1:  # ADDN2 #-16..-1
            R[op & 15] = (R[op & 15] + ((op >> 4) & 15) - 16) & M
        elif hi == 0xA2:  # ADDN Rj,Ri
            R[op & 15] = (R[op & 15] + R[(op >> 4) & 15]) & M
        elif hi == 0x8B:  # MOV Rj,Ri
            R[op & 15] = R[(op >> 4) & 15]
        elif (op & 0xFFF0) == 0x97B0:  # EXTUH
            R[op & 15] &= 0xFFFF
        elif (op & 0xFFF0) == 0x9790:  # EXTUB
            R[op & 15] &= 0xFF
        elif (op & 0xFFF0) == 0x97A0:  # EXTSH
            v = R[op & 15] & 0xFFFF; R[op & 15] = (v - 0x10000 if v & 0x8000 else v) & M
        elif (op & 0xFFF0) == 0x9700:  # JMP @Ri
            jump = R[op & 15]
        elif (op & 0xFFF0) == 0x9F00:
            jump = R[op & 15]; delayed = True
        elif 0xE0 <= hi <= 0xFF:
            c = (op >> 8) & 15
            rel = op & 0xFF
            rel = rel - 256 if rel & 0x80 else rel
            t = pc + 2 + rel * 2
            delayed = hi >= 0xF0
            jump = t if cond(c) else None
            if jump is None and delayed:
                # le créneau s'exécute quand même ; on continue simplement
                pass
        elif op == 0x9FA0:  # NOP
            pass
        else:
            raise Unk('op %04x @ %x' % (op, pc))
        if pending is not None:
            t = pending; pending = None
            if t == 'RET':
                return R
            pc = t
            continue
        if jump is not None and delayed:
            pending = jump
            pc = npc
            continue
        if jump is not None:
            if jump == 'RET':
                return R
            pc = jump
            continue
        pc = npc
    raise Unk('trop de pas')


if __name__ == '__main__':
    b = open(sys.argv[1], 'rb').read()
    f = int(sys.argv[2], 16)
    for a in sys.argv[3:]:
        regs = [0] * 16; regs[5] = int(a, 16)
        print(a, hex(run(b, f, regs)[4]))
