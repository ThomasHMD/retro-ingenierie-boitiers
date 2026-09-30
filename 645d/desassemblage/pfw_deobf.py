# SPDX-License-Identifier: GPL-2.0-only (voir COPYING) : algorithme de pfwtool (Tao Wang), réécrit en Python.
# Reimplementation (Python) of the "deobfuscate" step of pfwtool (twang2218/pentax-firmware-tool, GPL-2.0), read from its index.js.
# Usage: python3 -I pfw_deobf.py <input.bin> <output.bin> <endian: be|le> <start1> <section2base>
import sys, struct
inp, outp, endian, start1, base2 = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4],0), int(sys.argv[5],0)
buf = bytearray(open(inp,'rb').read())
fmt = '>I' if endian=='be' else '<I'
M32 = 0xFFFFFFFF
def rd(o): return struct.unpack_from(fmt, buf, o)[0]
def wr(o,v): struct.pack_into(fmt, buf, o, v & M32)
def calc_key(iv):
    t0 = (iv[0] + (~iv[2] & M32)) & M32
    t1 = (iv[1] + (~iv[3] & M32)) & M32
    t = [t0, t1, (~t0)&M32, (~t1)&M32]
    key=[0]*0x20
    for i in range(4):
        for j in range(4):
            key[i+8*j+0] = (t[i] + iv[j] - 1) & M32
            key[i+8*j+4] = (t[i] - iv[j] - 1) & M32
    return key
def deobf(base, iv_off, start, length):
    iv=[rd(base+iv_off+4*k) for k in range(4)]
    key=calc_key(iv)
    assert start%0x80==0 and length%0x80==0, (start,length)
    for b in range(length//0x80):
        pos = b*0x80 + start
        for i in range(0x20):
            o = base + pos + 4*i
            wr(o, rd(o) ^ ((key[i] - pos) & M32))
n=len(buf)
deobf(0, 0, start1, base2 - start1)
deobf(base2, 0, 0x100 if len(sys.argv)<7 else int(sys.argv[6],0), n - base2 - (0x100 if len(sys.argv)<7 else int(sys.argv[6],0)))
open(outp,'wb').write(buf)
print("written", outp, len(buf))
