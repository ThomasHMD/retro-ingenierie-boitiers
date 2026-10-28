import sys
lines=open(sys.argv[1],errors='replace').read().splitlines()
ranges=[(int(a,16),int(b,16)) for a,b in (r.split('-') for r in sys.argv[2:])]
for l in lines:
    l=l.strip()
    if not l: continue
    off,_,s=l.partition(' ')
    try: o=int(off,16)
    except: continue
    if any(a<=o<=b for a,b in ranges):
        print(off,s[:120])
