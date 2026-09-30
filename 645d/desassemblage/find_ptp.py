import sys,struct,re
b=open(sys.argv[1],'rb').read()
# find positions of 0x1001 BE halfword aligned, then check for 0x1002 within 64 bytes and 0x1003
for m in re.finditer(rb'\x10\x01',b):
    o=m.start()
    if o%2: continue
    w=b[o:o+256]
    p2=w.find(b'\x10\x02'); p3=w.find(b'\x10\x03'); p4=w.find(b'\x10\x04')
    if 0<p2<64 and p2<p3<128 and p3<p4 and p2%2==0 and p3%2==0:
        stride=p2
        print(hex(o), 'addr',hex(0x10000000+o),'stride',stride, w[:64].hex())
