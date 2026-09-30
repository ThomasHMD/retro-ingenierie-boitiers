# usage: imm.py dec.bin val [val...] : LDI:20 / LDI:32 chargeant exactement ces valeurs
import sys,struct,re
b=open(sys.argv[1],'rb').read()
BASE=0x10000000
vals=set(int(v,16) for v in sys.argv[2:])
for o in range(0xe8000,0x970000,2):
    if b[o]==0x9b:
        v=((b[o+1]>>4)<<16)|(b[o+2]<<8)|b[o+3]
        if v in vals: print('LDI20',hex(BASE+o),'r%d'%(b[o+1]&15),hex(v))
    elif b[o]==0x9f and (b[o+1]>>4)==8:
        v=struct.unpack_from('>I',b,o+2)[0]
        if v in vals: print('LDI32',hex(BASE+o),'r%d'%(b[o+1]&15),hex(v))
