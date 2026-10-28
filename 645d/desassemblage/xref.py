# usage: xref.py dec.bin lo hi  -> LDI:32 and raw 32-bit words referencing [lo,hi]
import sys,struct,re
b=open(sys.argv[1],'rb').read()
lo,hi=int(sys.argv[2],16),int(sys.argv[3],16)
BASE=0x10000000
for m in re.finditer(rb'\x9f[\x80-\x8f]',b):
    o=m.start()
    if o%2: continue
    v=struct.unpack_from('>I',b,o+2)[0]
    if lo<=v<=hi: print('LDI32 at',hex(BASE+o),'r%d'%(b[o+1]&15),'->',hex(v))
for o in range(0,len(b)-3,4):
    v=struct.unpack_from('>I',b,o)[0]
    if lo<=v<=hi: print('WORD at',hex(BASE+o),'->',hex(v))
