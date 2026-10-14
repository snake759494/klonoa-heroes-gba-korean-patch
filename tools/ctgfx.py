# 'CT' graphic container (loader 0x804e594 etc.):
#  +0 'CT' +2 w +4 h +6 bpp(u8) +7 npal(u8) +8 pal_off(u32) +0xc ntiles(u16)|?(u16) +0x10 tiles_size +0x14 tiles_off +0x18 map_size +0x1c map_off
import struct, numpy as np
def parse(b):
    assert b[:2]==b"CT"
    w,h=struct.unpack_from("<HH",b,2); bpp=b[6]; npal=b[7]
    palo,ntw,ts,to,ms,mo=struct.unpack_from("<6I",b,8)
    return dict(w=w,h=h,bpp=bpp,npal=npal,pal=palo,tsize=ts,tiles=to,msize=ms,map=mo,mw=w//8,mh=h//8,nt=ts//(32 if bpp==4 else 64))
def palette(b,c,bank=0):
    n=16 if c["bpp"]==4 else 256
    out=[]
    for i in range(n):
        o=c["pal"]+2*(bank*16+i) if c["bpp"]==4 else c["pal"]+2*i
        if o+2>len(b): out.append((255,0,255)); continue
        w=struct.unpack_from("<H",b,o)[0]; out.append(((w&31)<<3,((w>>5)&31)<<3,((w>>10)&31)<<3))
    return out
def tile_px(b,o,bpp):
    if bpp==4:
        t=np.frombuffer(bytes(b[o:o+32]),dtype=np.uint8); return np.stack([t&15,t>>4],1).reshape(8,8).copy()
    return np.frombuffer(bytes(b[o:o+64]),dtype=np.uint8).reshape(8,8).copy()
def image(b):
    """returns (index image HxW, map entries list) using the container's own map; tile numbers are relative"""
    c=parse(b); tsz=32 if c["bpp"]==4 else 64
    img=np.zeros((c["h"],c["w"]),np.uint8); ents=[]
    for r in range(c["mh"]):
        for q in range(c["mw"]):
            e=struct.unpack_from("<H",b,c["map"]+2*(r*c["mw"]+q))[0] if c["msize"] else r*c["mw"]+q; ents.append(e)
            t=e&0x3ff
            if t>=c["nt"]: continue
            px=tile_px(b,c["tiles"]+t*tsz,c["bpp"])
            if e&0x400: px=px[:,::-1]
            if e&0x800: px=px[::-1,:]
            img[r*8:r*8+8,q*8:q*8+8]=px
    return img,ents,c
def render(b,out=None,scale=2):
    from PIL import Image
    img,ents,c=image(b)
    pals=[palette(b,c,k) for k in range(max(1,c["npal"]))]
    im=Image.new("RGB",(c["w"],c["h"]))
    for r in range(c["mh"]):
        for q in range(c["mw"]):
            e=ents[r*c["mw"]+q]; P=pals[(e>>12)%len(pals)] if c["bpp"]==4 else pals[0]
            for y in range(8):
                for x in range(8): im.putpixel((q*8+x,r*8+y),P[img[r*8+y,q*8+x]])
    if out: im.resize((c["w"]*scale,c["h"]*scale),Image.NEAREST).save(out)
    return c
