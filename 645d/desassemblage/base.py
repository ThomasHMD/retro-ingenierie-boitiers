import sys,struct,re,collections
b=open(sys.argv[1],'rb').read()
code=b[0xe8000:0x970000]
imms=[]
for m in re.finditer(rb'\x9f[\x80-\x8f]',code):
    o=m.start()
    if o%2: continue
    imms.append(struct.unpack_from('>I',code,o+2)[0])
print('ldi32',len(imms))
# string starts
strs=[m.start() for m in re.finditer(rb'[\x20-\x7e]{6,}\x00',b[0xe8000:0x970000])]
strs=set(s+0xe8000 for s in strs)
c=collections.Counter()
imset=collections.Counter(imms)
# candidate bases: imm - s, restricted to page aligned 0x1000
for v in imset:
    for s in list(strs)[:0]: pass
# faster: for a sample of strings, candidate
import random
sl=sorted(strs)
for s in sl[::7]:
    for v in imset:
        d=(v-s)&0xffffffff
        if d & 0xfff ==0: c[d]+=1
for d,n in c.most_common(10): print(hex(d),n)
