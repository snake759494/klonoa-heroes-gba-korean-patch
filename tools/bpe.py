# Byte-pair-encoding codec used by Klonoa Heroes resource loader (decoder at 0x804e428)
import struct
def decode(src, maxout=None):
    size=struct.unpack_from("<I",src,0)[0]; pos=8; out=bytearray()
    if maxout is None: maxout=struct.unpack_from("<I",src,4)[0]
    if size>len(src) or maxout<=0 or maxout>0x200000: raise ValueError("bad header")
    while pos<size:
        if len(out)>maxout: raise ValueError("overrun")
        left=list(range(256)); right=[0]*256; c=0
        while c<256:
            b=src[pos]; pos+=1
            if b>127: c+=b-127; b=0
            if c==256: break
            for _ in range(b+1):
                left[c]=src[pos]; pos+=1
                if c!=left[c]: right[c]=src[pos]; pos+=1
                c+=1
        n=src[pos]<<8|src[pos+1]; pos+=2
        stack=[]
        while n>0 or stack:
            if len(out)>maxout or len(stack)>512: raise ValueError("overrun")
            if stack: b=stack.pop()
            else: b=src[pos]; pos+=1; n-=1
            if left[b]==b: out.append(b)
            else: stack.append(right[b]); stack.append(left[b])
    return bytes(out)
def encode_literal(data, block=0x4000):
    """valid stream with no pair substitutions (each block: FF 80 FE + BE16 len + raw)"""
    body=bytearray()
    for i in range(0,len(data),block):
        chunk=data[i:i+block]
        body+=bytes([0xff,0x80,0xfe])+struct.pack(">H",len(chunk))+chunk
    return struct.pack("<II",8+len(body),len(data))+bytes(body)

def encode(data, block=0x400):
    """BPE-encode data in independently coded blocks; the decoder resets its table at each block."""
    from collections import Counter
    body=bytearray()
    for base in range(0,len(data),block):
        seq=list(data[base:base+block]); rules={}; assigned=set(); depth={}
        while True:
            counts=Counter(zip(seq,seq[1:]))
            if not counts: break
            referenced={v for pair in rules.values() for v in pair}
            code=next((c for c in range(255,-1,-1) if c not in assigned and c not in seq and c not in referenced),None)
            if code is None: break
            best=None; best_count=2
            for pair,freq in counts.most_common():
                if max(depth.get(pair[0],0),depth.get(pair[1],0))>=128: continue
                n=0; i=0
                while i<len(seq)-1:
                    if (seq[i],seq[i+1])==pair: n+=1; i+=2
                    else: i+=1
                if n>best_count: best_count=n; best=pair
                if n==freq: break
            if best is None: break
            compressed=[]; i=0
            while i<len(seq):
                if i+1<len(seq) and (seq[i],seq[i+1])==best:
                    compressed.append(code); i+=2
                else:
                    compressed.append(seq[i]); i+=1
            if len(seq)-len(compressed)<3: break
            rules[code]=best; assigned.add(code); depth[code]=max(depth.get(best[0],0),depth.get(best[1],0))+1; seq=compressed

        # A byte above 0x7f advances the dictionary cursor and then defines
        # one entry at the new position. An advance to 256 terminates the table.
        table=bytearray(); c=0
        while c<256:
            if c in rules:
                end=c
                while end<256 and end in rules and end-c<128: end+=1
                table.append(end-c-1)
                for k in range(c,end): table.extend(rules[k])
                c=end
                continue
            nxt=min((k for k in rules if k>c),default=None)
            if nxt is None:
                distance=256-c
                if distance<=128:
                    table.append(127+distance); c=256
                else:
                    table.extend((255,c+128)); c+=129  # skip 128 and define identity at that code
                continue
            distance=nxt-c
            if distance<=128:
                table.append(127+distance); table.extend(rules[nxt]); c=nxt+1
            else:
                table.extend((255,c+128)); c+=129  # skip 128 and define identity at that code
        body.extend(table); body.extend(struct.pack(">H",len(seq))); body.extend(bytes(seq))
    return struct.pack("<II",8+len(body),len(data))+bytes(body)
