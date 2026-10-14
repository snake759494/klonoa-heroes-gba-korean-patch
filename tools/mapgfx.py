# Map-screen UI graphics (tag resources at 0x2f9870): BG0B (tilemaps + 691 tiles), BG0W (world banners), BG0V (place banners), BG0P (palettes)
import struct, numpy as np
TAGT=0x2f9870
def tag_entries(rom):
    out=[]; i=0
    while True:
        tag,sub,size,off=struct.unpack_from("<4I",rom,TAGT+16*i)
        if tag==0xffffffff: return out
        out.append((struct.pack("<I",tag).decode("latin1"),sub,size,TAGT+off)); i+=1
def find(rom,tag,sub=0):
    for t,s,size,a in tag_entries(rom):
        if t==tag and s==sub: return a,size
    return None
def pal(rom,sub):
    a,_=find(rom,"BG0P",sub)
    ws=struct.unpack_from("<16H",rom,a)
    return [((w&31)<<3,((w>>5)&31)<<3,((w>>10)&31)<<3) for w in ws]
def tile_px(buf,o):
    t=np.frombuffer(bytes(buf[o:o+32]),dtype=np.uint8); return np.stack([t&15,t>>4],1).reshape(8,8)
def bg0b(rom):
    a,size=find(rom,"BG0B"); return a,size
