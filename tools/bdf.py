# minimal BDF reader: returns {codepoint: (dwidth, bbx(w,h,x,y), rows[list of int])}
def load(path):
    glyphs={}; cur=None
    with open(path,encoding="utf-8",errors="replace") as f:
        it=iter(f)
        for line in it:
            if line.startswith("STARTCHAR"): cur={"rows":[]}
            elif line.startswith("ENCODING"): cur["enc"]=int(line.split()[1])
            elif line.startswith("DWIDTH"): cur["dw"]=int(line.split()[1])
            elif line.startswith("BBX"):
                w,h,x,y=map(int,line.split()[1:5]); cur["bbx"]=(w,h,x,y)
            elif line.startswith("BITMAP"):
                h=cur["bbx"][1]
                for _ in range(h): cur["rows"].append(int(next(it).strip() or "0",16))
            elif line.startswith("ENDCHAR"):
                if cur.get("enc",-1)>=0: glyphs[cur["enc"]]=cur
                cur=None
    return glyphs
def render(g, ascent):
    """returns list of strings (rows) positioned with baseline at 'ascent' from top; height ascent+descent"""
    w,h,x,y=g["bbx"]; rows=g["rows"]; wb=(w+7)//8*8
    out={}
    for i,r in enumerate(rows):
        yy=ascent-(y+h)+i
        out[yy]=[(r>>(wb-1-xx))&1 for xx in range(wb)][:w]
    return out
if __name__=="__main__":
    import sys
    for path,asc in (("work/fonts/Galmuri11.bdf",14),("work/fonts/Galmuri14.bdf",0)):
        G=load(path); g=G[ord("가")]; print(path,"dw",g["dw"],"bbx",g["bbx"],"n",len(G))
        for r in g["rows"]: print(format(r,"0%db"%((g["bbx"][0]+7)//8*8)).replace("0",".").replace("1","#")[:g["bbx"][0]])
        g=G[ord("뷁")]; print("뷁 dw",g["dw"],"bbx",g["bbx"])
        g=G[ord("A")]; print("A dw",g["dw"],"bbx",g["bbx"])
