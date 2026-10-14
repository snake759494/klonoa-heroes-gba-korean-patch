# Build 8x16 4bpp half-glyph tiles (game font format: color1=body, color2=shadow at +1,+1) from Galmuri14 BDF.
import sys,os; sys.path.insert(0,os.path.dirname(__file__))
import bdf
FONT=os.path.join(os.path.dirname(__file__),"..","work","fonts","Galmuri14.bdf")
_G=None
def glyphs():
    global _G
    if _G is None: _G=bdf.load(FONT)
    return _G
def bitmap16(ch, top=1):
    """16x16 body bitmap (list of 16 rows of 16 bits) for a full-width char, unscaled Galmuri14, left-aligned +1px"""
    g=glyphs()[ord(ch)]; w,h,x,y=g["bbx"]; wb=(w+7)//8*8
    rows=[[0]*16 for _ in range(16)]
    # vertical: glyph height h (<=14); place so that baseline y offset respected: bottom row at top+14-1 - y
    base=top+14  # row below the 14px box
    for i,r in enumerate(g["rows"]):
        yy=base-(y+h)+i
        if not (0<=yy<16): continue
        for xx in range(w):
            if (r>>(wb-1-xx))&1:
                px=x+xx
                if 0<=px<16: rows[yy][px]=1
    return rows
def with_shadow(rows):
    out=[[0]*16 for _ in range(16)]
    for yy in range(16):
        for xx in range(16):
            if rows[yy][xx]: out[yy][xx]=1
    for yy in range(16):
        for xx in range(16):
            if rows[yy][xx] and yy+1<16 and xx+1<16 and out[yy+1][xx+1]==0: out[yy+1][xx+1]=2
    return out
def half_glyph(ch):
    """8x16 single-cell glyph for narrow chars (ascii punctuation etc) from Galmuri14; returns (top,bot) or None if too wide"""
    g=glyphs().get(ord(ch))
    if g is None: return None
    w,h,x,y=g["bbx"]
    if w>7: return None
    rows=[[0]*16 for _ in range(16)]; wb=(w+7)//8*8; base=15
    for i,r in enumerate(g["rows"]):
        yy=base-(y+h)+i
        if not (0<=yy<16): continue
        for xx in range(w):
            if (r>>(wb-1-xx))&1 and 0<=xx<8: rows[yy][xx]=1
    px=with_shadow(rows)
    top=bytearray(); bot=bytearray()
    for yy in range(16):
        for xx in range(0,8,2): (top if yy<8 else bot).append(px[yy][xx]|(px[yy][xx+1]<<4))
    return bytes(top),bytes(bot)
def halves(ch):
    """returns (left,right) each 64 bytes: 4bpp 8x8 top tile + 8x8 bottom tile (game layout: top at +0, bottom at +0x400 handled by caller)"""
    px=with_shadow(bitmap16(ch))
    res=[]
    for half in range(2):
        top=bytearray(); bot=bytearray()
        for yy in range(16):
            row=bytearray()
            for xx in range(0,8,2):
                a=px[yy][half*8+xx]; b=px[yy][half*8+xx+1]; row.append(a|(b<<4))
            (top if yy<8 else bot).extend(row)
        res.append((bytes(top),bytes(bot)))
    return res
if __name__=="__main__":
    from PIL import Image
    s="크로노아 히어로즈 전설의 스타메달 가나다뷁"
    img=Image.new("RGB",(len(s)*16,16),(40,40,120))
    for i,ch in enumerate(s):
        if ch==" ": continue
        px=with_shadow(bitmap16(ch))
        for yy in range(16):
            for xx in range(16):
                v=px[yy][xx]
                if v: img.putpixel((i*16+xx,yy),(255,255,255) if v==1 else (60,60,60))
    img.resize((img.width*3,48),Image.NEAREST).save("out/hangul_preview.png"); print("ok")

# ---- 8x8 small bold font (container 17) : Galmuri7, unscaled, shadow at +1,+1 ----
FONT7=os.path.join(os.path.dirname(__file__),"..","work","fonts","Galmuri7.bdf")
_G7=None
def glyphs7():
    global _G7
    if _G7 is None: _G7=bdf.load(FONT7)
    return _G7
def small_glyph(ch):
    """32-byte 4bpp 8x8 tile of ch from Galmuri7 (7x7 box + shadow). blank tile if missing."""
    rows=[[0]*8 for _ in range(8)]
    g=glyphs7().get(ord(ch))
    if g is not None:
        w,h,x,y=g["bbx"]; wb=(w+7)//8*8; base=7   # baseline row index 7 (descent 1 -> y=-1 sits on row 7)
        for i,r in enumerate(g["rows"]):
            yy=base-(y+h)+i
            if not (0<=yy<8): continue
            for xx in range(w):
                if (r>>(wb-1-xx))&1:
                    px=x+xx
                    if 0<=px<8: rows[yy][px]=1
    out=[[0]*8 for _ in range(8)]
    for yy in range(8):
        for xx in range(8):
            if rows[yy][xx]: out[yy][xx]=1
    for yy in range(8):
        for xx in range(8):
            if rows[yy][xx] and yy+1<8 and xx+1<8 and out[yy+1][xx+1]==0: out[yy+1][xx+1]=2
    t=bytearray()
    for yy in range(8):
        for xx in range(0,8,2): t.append(out[yy][xx]|(out[yy][xx+1]<<4))
    return bytes(t)


_G11C=None
def native_cell(ch):
    """Unscaled Galmuri11 Condensed, 7x11 ink in original 8x16 storage."""
    global _G11C
    if _G11C is None:
        _G11C=bdf.load(os.path.join(os.path.dirname(FONT),"Galmuri11-Condensed.bdf"))
    g=_G11C[ord(ch)]; w,h,x,y=g['bbx']; wb=(w+7)//8*8
    assert w <= 7, (ch,w)
    rows=[[0]*16 for _ in range(16)]
    for row,bits in enumerate(g['rows']):
        yy=12-(y+h)+row
        for xx in range(w):
            if 0<=yy<16 and 0<=x+xx<8 and bits & (1<<(wb-1-xx)):
                rows[yy][x+xx]=1
    px=with_shadow(rows); data=bytearray()
    for yy in range(16):
        for xx in range(0,8,2):data.append(px[yy][xx]|px[yy][xx+1]<<4)
    return bytes(data[:32]),bytes(data[32:])
