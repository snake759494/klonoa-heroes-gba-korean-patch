# 'AN' sprite animation resource: header [AN][u16 nframes?][u16][u32 size][u32 anim_off][u32 tiles_off]...
# frames 'AF' -> 'AS' piece lists: 16-byte pieces [s8 x][s8 y][u16 attr0 shape][u16 attr1 size][u16 ?][u16 ?][u16 ?][u16 tile*32][u16 0]
import struct, numpy as np
SIZES={(0,0):(8,8),(0,1):(16,16),(0,2):(32,32),(0,3):(64,64),(1,0):(16,8),(1,1):(32,8),(1,2):(32,16),(1,3):(64,32),(2,0):(8,16),(2,1):(8,32),(2,2):(16,32),(2,3):(32,64)}
def pieces(b, af):
    assert b[af:af+2]==b"AF"
    aso=af+struct.unpack_from("<I",b,af+0x10)[0]
    assert b[aso:aso+2]==b"AS", hex(aso)
    n=b[aso+3]; out=[]
    for i in range(n):
        e=aso+0x10+16*i
        x,y=struct.unpack_from("<bb",b,e); a0,a1=struct.unpack_from("<HH",b,e+2)
        chunk=struct.unpack_from("<H",b,e+12)[0]>>5   # byte offset of the first tile / 32
        shape=a0>>14; size=a1>>14; w,h=SIZES[(shape,size)]
        out.append(dict(x=x,y=y,w=w,h=h,chunk=chunk,raw=b[e:e+16].hex()))
    return out
