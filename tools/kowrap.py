# Korean line wrapper for Klonoa Heroes dialogue: cell widths (all glyphs=1 native 8-pixel cell), max cells per line
import re
TOK=re.compile(r'(<[0-9A-F]{4}>.|<[A-Z]+>)')
def cw(ch):
    return 1  # Native 8-pixel cell, including Korean syllables.

def wrap(text, cells=24):
    """free text (no manual breaks) -> list of lines within cell budget, breaking at spaces"""
    words=text.split(' '); lines=[]; cur=''; w=0
    for word in words:
        ww=sum(cw(c) for c in word)
        if cur=='' : cur=word; w=ww; continue
        if w+1+ww<=cells: cur+=' '+word; w+=1+ww
        else: lines.append(cur); cur=word; w=ww
    if cur: lines.append(cur)
    return lines
def width(line): return sum(cw(c) for c in re.sub(r'<[0-9A-F]{4}>.|<[A-Z]+>','',line))
if __name__=="__main__":
    print(wrap("세상에는 아직 아무도 본 적 없는, 별의 반짝임을 지닌 전설의 메달이 있다고 한다.",24))
