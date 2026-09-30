# callargs.py dec.bin target reg : pour chaque LDI:32 #target, cherche la dernière affectation LDI:8 de Rreg
# dans les 24 octets avant l'appel et dans le créneau de délai après le CALL:D.
import sys,struct,re,collections
b=open(sys.argv[1],'rb').read(); B=0x10000000
t=int(sys.argv[2],16); reg=int(sys.argv[3])
pat=b'\x9f'+bytes([0x80|12])+struct.pack('>I',t)
c=collections.Counter(); sites=collections.defaultdict(list)
i=0
while True:
    i=b.find(pat,i)
    if i<0: break
    if i%2==0:
        val=None
        # créneau : CALL:D @R12 = 9F1C puis instruction
        if b[i+6:i+8]==b'\x9f\x1c':
            h=(b[i+8]<<8)|b[i+9]
            if (h>>12)==0xC and (h&15)==reg: val=(h>>4)&0xff
        if val is None:
            for o in range(i-2,i-26,-2):
                h=(b[o]<<8)|b[o+1]
                if (h>>12)==0xC and (h&15)==reg: val=(h>>4)&0xff; break
                if (h>>8)==0x8B and (h&15)==reg: val='reg'; break
        c[val]+=1; sites[val].append(hex(B+i))
    i+=2
for k,v in sorted(c.items(),key=lambda x:str(x[0])):
    print(k if isinstance(k,str) or k is None else hex(k), v, ' '.join(sites[k][:6]))
