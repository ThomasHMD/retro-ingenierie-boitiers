# usage: xref2.py dec.bin addr [addr...] -> LDI:32 imm, 32-bit words, CALL rel11
import sys,struct,re
b=open(sys.argv[1],'rb').read()
BASE=0x10000000
targets=set(int(a,16) for a in sys.argv[2:])
for m in re.finditer(rb'\x9f[\x80-\x8f]',b):
    o=m.start()
    if o%2: continue
    v=struct.unpack_from('>I',b,o+2)[0]
    if v in targets: print('LDI32',hex(BASE+o),'r%d'%(b[o+1]&15),'->',hex(v))
for o in range(0,len(b)-3,4):
    v=struct.unpack_from('>I',b,o)[0]
    if v in targets: print('WORD',hex(BASE+o),'->',hex(v))
for o in range(0xe8000,0x970000,2):
    h=(b[o]<<8)|b[o+1]
    if 0xd000<=h<=0xdfff:
        r=h&0x7ff
        if r&0x400: r-=0x800
        t=BASE+o+2+r*2
        if t in targets: print('CALL' if h<0xd800 else 'CALL:D',hex(BASE+o),'->',hex(t))
