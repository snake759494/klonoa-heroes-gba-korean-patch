# Klonoa Heroes Korean patch builder
# - expands ROM to 32MB, relocates font container with native 8-pixel Hangul cells (Galmuri11-Condensed, unscaled)
# - hooks 0x8031cfc (message id -> text ptr) to remap original text ptr -> translated text (binary search table)
import struct, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from thumb import assemble
from charmap import CH2CODE, CODE2CH
import hangul_glyphs
ROOT=os.path.normpath(os.path.join(os.path.dirname(__file__),".."))
ORIG=os.path.join(ROOT,"Klonoa Heroes - Densetsu no Star Medal (Japan).gba")
FONT_CONT=0x29666c; FONT_CONT_END=0x29c72c; FONT_OFF=0xc0; ORIG_BANDS=12
NEW_SIZE=0x2000000
GLYPHMAP=os.path.join(ROOT,"work","glyphmap.json")
class Rom:
    def __init__(s):
        s.d=bytearray(open(ORIG,"rb").read()); s.d+=b'\0'*(NEW_SIZE-len(s.d))
        s.free=0x1000000
    def u32(s,a,v): struct.pack_into("<I",s.d,a,v)
    def alloc(s,n,align=4):
        s.free=(s.free+align-1)&~(align-1); a=s.free; s.free+=n; return a
    def save(s,p): open(p,"wb").write(s.d)
class Glyphs:
    """Hangul syllable -> one code, allocated from 0x180 upward (band 12+)."""
    def __init__(s):
        # One syllable occupies one original 8-pixel cell. Rebuild deterministically.
        s.map={}; s.next=0x180
    def codes(s,ch):
        if ch not in s.map:
            s.map[ch]=[s.next]; s.next+=1
        return s.map[ch]
    def install(s,rom):
        """relocate font containers (resource index 16,17,18 of table 0x28fd20) into the expanded area and append hangul bands
        to the 12-band fonts (16 and 18). The index table offsets are patched, so no code patch is needed."""
        n_codes=s.next; bands=max(ORIG_BANDS,(n_codes+31)//32)
        IDX=0x28fd20
        offs=[struct.unpack_from("<I",rom.d,IDX+4*k)[0] for k in range(16,20)]
        bases=[IDX+o for o in offs]
        base16=None
        for k,(st,en) in enumerate(zip(bases[:3],bases[1:4])):
            idx=16+k; size=en-st
            fsize=struct.unpack_from("<I",rom.d,st+0x10)[0]; foff=struct.unpack_from("<I",rom.d,st+0x14)[0]
            is12=(fsize==0x6000); is8=(fsize==0x2000)
            extra=(bands-ORIG_BANDS)*0x800 if is12 else (max(0,n_codes*0x20-fsize) if is8 else 0)
            alloc=size+extra+0x10
            nb=rom.alloc(alloc,0x10)
            rom.d[nb:nb+size]=rom.d[st:en]
            if is12:
                font=nb+foff
                for ch,cl in s.map.items():
                    tiles=[hangul_glyphs.native_cell(ch)]
                    for code,(t,b_) in zip(cl,tiles):
                        o=font+(code>>5)*0x800+(code&31)*32
                        rom.d[o:o+32]=t; rom.d[o+0x400:o+0x420]=b_
                struct.pack_into("<I",rom.d,nb+0x10,bands*0x800)
                if base16 is None: base16=nb
            if is8:
                font=nb+foff
                for ch,cl in s.map.items():
                    o=font+cl[0]*32; rom.d[o:o+32]=hangul_glyphs.small_glyph(ch)
                    for c in cl[1:]: o=font+c*32; rom.d[o:o+32]=bytes(32)
                # keep the header size field (0x2000): the game bulk-copies that many bytes (VRAM); hangul tiles are fetched per code from ROM
            rom.u32(IDX+4*idx,nb-IDX)
            print("container",idx,"->",hex(nb),"size",hex(size),"font12" if is12 else "")
        json.dump(s.map,open(GLYPHMAP,"w",encoding="utf-8"),ensure_ascii=False,indent=0)
        return base16,bands
CTRL={"<END>":0xffff,"<CLR>":0xfffe,"<PAGE>":0xfff7,"<WAIT>":0xfff6,"\n":0xfffd}
def encode(g,text):
    """translated text with markup -> u16 words (no END appended unless present)"""
    out=[]; i=0
    while i<len(text):
        ch=text[i]
        if ch=="<":
            j=text.index(">",i); tag=text[i:j+1]; i=j+1
            if tag in CTRL: out.append(CTRL[tag]); continue
            out.append(int(tag[1:-1],16)); continue
        i+=1
        if ch=="\n": out.append(0xfffd); continue
        if ch==" ": out.append(0xa0); continue
        if '\uac00'<=ch<='\ud7a3' or ch in "…·": out+=g.codes(ch); continue
        if ch in ",.!?'\"()-:;": out+=g.codes(ch); continue
        if ch in CH2CODE: out.append(CH2CODE[ch]); continue
        # ascii -> full-width
        if ord(ch)<0x80:
            fw=chr(ord(ch)+0xfee0)
            if fw in CH2CODE: out.append(CH2CODE[fw]); continue
        raise KeyError(ch)
    return out
SEARCH="""
push {r4, r5, r6, r7, lr}
mov r4, r0
lsrs r1, r0, #24
cmp r1, #2
beq ram
cmp r1, #3
beq ram
b romsearch
ram:
ldrh r5, [r4, #0]
ldrh r3, [r4, #2]
lsls r3, r3, #16
adds r5, r5, r3
ldr r2, =RAMTABLE
ldr r6, [r2, #0]
adds r2, #4
movs r7, #0
rbs:
cmp r7, r6
bhs rscan
adds r1, r7, r6
lsrs r1, r1, #1
lsls r3, r1, #3
lsls r0, r1, #2
adds r3, r3, r0
adds r3, r3, r2
ldr r0, [r3, #0]
cmp r0, r5
bhs rhi
adds r7, r1, #1
b rbs
rhi:
mov r6, r1
b rbs
rscan:
ldr r0, =RAMTABLE
ldr r6, [r0, #0]
rsloop:
cmp r7, r6
bhs done
lsls r3, r7, #3
lsls r0, r7, #2
adds r3, r3, r0
adds r3, r3, r2
ldr r0, [r3, #0]
cmp r0, r5
bne done
push {r5, r6}
ldr r0, [r3, #4]
mov r1, r4
cl:
ldrh r5, [r0, #0]
ldrh r6, [r1, #0]
cmp r5, r6
bne clne
adds r0, #2
adds r1, #2
ldr r6, =0xffff
cmp r5, r6
bne cl
pop {r5, r6}
ldr r0, [r3, #8]
pop {r4, r5, r6, r7, pc}
clne:
pop {r5, r6}
adds r7, #1
b rsloop
romsearch:
ldr r2, =TABLE
ldr r6, [r2, #0]
adds r2, #4
movs r5, #0
loop:
cmp r5, r6
bge rommiss
adds r1, r5, r6
lsrs r1, r1, #1
lsls r3, r1, #3
lsls r0, r1, #2
adds r3, r3, r0
adds r3, r3, r2
ldr r0, [r3, #0]
cmp r0, r4
beq found
bhi upper
adds r5, r1, #1
b loop
upper:
mov r6, r1
b loop
found:
ldr r0, [r3, #8]
ldrh r1, [r4, #0]
lsls r2, r0, #16
lsrs r2, r2, #16
cmp r1, r2
bne rommiss
ldrh r1, [r4, #2]
lsrs r2, r0, #16
cmp r1, r2
bne rommiss
ldr r0, [r3, #4]
pop {r4, r5, r6, r7, pc}
rommiss:
lsrs r0, r4, #24
cmp r0, #8
beq ram
cmp r0, #9
beq ram
b done
done:
mov r0, r4
pop {r4, r5, r6, r7, pc}
"""
# hook1: replaces 0x8031cfc (id -> text ptr), tail-calls SEARCH
HOOK="""
adds r0, #0xb4
lsls r1, r1, #16
asrs r1, r1, #14
ldr r0, [r0, #0]
adds r0, r0, r1
ldr r1, [r0, #0]
lsls r1, r1, #2
adds r0, r0, r1
ldr r3, =SEARCH
bx r3
"""
CALL="""
mov r4, pc
adds r4, #7
mov lr, r4
ldr r4, =SEARCH
bx r4
"""
# hook2: replaces 0x802ebb8 (ctx, text)
HOOK2="""
push {r4, r5, r6, lr}
mov r5, r0
mov r0, r1
"""+CALL+"""
mov r4, r0
mov r0, r5
ldr r3, =0x802eae9
mov r6, pc
adds r6, #5
mov lr, r6
bx r3
str r4, [r5, #0x14]
str r4, [r5, #0x10]
str r4, [r5, #0xc]
str r4, [r5, #8]
movs r0, #1
str r0, [r5, #0x1c]
pop {r4, r5, r6, pc}
"""
# Prologue hooks for functions starting with the standard sequence
#   push {r4-r7,lr}; mov r7,sl; mov r6,sb; mov r5,r8; push {r5,r6,r7}; sub sp,#N   (entry E, 4-byte aligned)
# Entry patch keeps the original push, then: ldr r4,[pc,#4]; bx r4; nop; .word hook  (r4 is already saved -> no
# caller register is lost). The hook redoes the rest of the prologue, remaps the text argument via SEARCH and
# continues at E+12. (The old stub loaded r4 before the push and destroyed the caller's r4 -> chapter-list hang.)
PROLOGUE_HOOKS=[(0x80252d8,2),(0x805712c,2),(0x802569c,0),(0x8025470,2)]
def prologue_hook_src(E,textreg,subsp):
    others=", ".join("r%d"%r for r in (0,1,2,3) if r!=textreg)
    src="""
mov r7, sl
mov r6, sb
mov r5, r8
push {r5, r6, r7}
sub sp, #%d
push {%s}
""" % (subsp,others)
    if textreg: src+="mov r0, r%d\n" % textreg
    src+=CALL
    if textreg: src+="mov r%d, r0\n" % textreg
    src+="""
pop {%s}
ldr r4, =0x%x
bx r4
""" % (others,E+12+1)
    return src

# Leaf-function hooks (entry stub ldr r3,[pc]; bx r3 -- r3 is scratch in these functions)
# 0x8025760 strlen-to-line-end (centering/max width), 0x80255b4 line count (tutorial scroll limit): measure the translated text.
STRLEN="""
push {r4, lr}
"""+CALL+"""
movs r3, #0
ldr r4, =0xffff
ldr r2, =0xfffd
sl_loop:
ldrh r1, [r0, #0]
cmp r1, r4
beq sl_end
cmp r1, r2
beq sl_end
adds r3, #1
adds r0, #2
b sl_loop
sl_end:
mov r0, r3
pop {r4, pc}
"""
LINES="""
push {r4, r5, lr}
"""+CALL+"""
movs r4, #0
movs r3, #0
ldr r2, =0xffff
ldr r5, =0xfffd
ldrh r1, [r0, #0]
cmp r1, r2
beq ln_end
ln_loop:
cmp r1, r5
bne ln_char
adds r3, #1
movs r4, #0
b ln_next
ln_char:
movs r4, #1
ln_next:
adds r0, #2
ldrh r1, [r0, #0]
cmp r1, r2
bne ln_loop
ln_end:
adds r0, r3, r4
pop {r4, r5, pc}
"""
# 0x8025a30(template, placeholder code, replacement, out): remap template AND replacement (e.g. boss/item names).
# Entry keeps the original push {r4-r7,lr}; stub at +2; continue at +12 with r4=template, r7=repl, r6=code, r0=[r4].
FORMAT="""
push {r1, r2, r3}
"""+CALL+"""
pop {r1, r2, r3}
push {r0, r1, r3}
mov r0, r2
"""+CALL+"""
mov r2, r0
pop {r0, r1, r3}
adds r4, r0, #0
adds r7, r2, #0
lsls r1, r1, #16
lsrs r6, r1, #16
ldrh r0, [r4, #0]
ldr r1, =0x8025a3d
bx r1
"""
# 0x8056508(font,dst,code) copies one 8x8 tile (font+[font+0x14]+code*0x20 -> dst). The 8x8-font loops of both renderers
# call it once per code; hangul right halves (odd code >= 0x180) must be skipped there, identified by the return address
# (0x80571b5: loop of 0x805712c with r4 dst/r6 map/sl count; 0x8025377: loop of 0x80252d8 with r5 dst/r4 col/[sp] width).
# BL cannot reach the expanded area, so the function entry itself is redirected here (patch_entry, r3 scratch).
from kowrap import wrap, width
CELLS=22; MAXLINES=3
def layout(ko, cells=CELLS, maxlines=MAXLINES):
    """Auto layout: pages split by <PAGE><CLR>/<PAGE>/<CLR>; within a page, units split by <WAIT>.
    Lines are wrapped to `cells`; if a page exceeds `maxlines`, it is split at the latest <WAIT> boundary that fits,
    otherwise hard-split at line boundary. Manual newlines are kept. Returns (text, warnings)."""
    import re
    ko=re.sub(r"<PAGE>(?!<CLR>)\n?", "<PAGE><CLR>", ko)
    warn=[]
    PAGE=re.compile(r'(<PAGE><CLR>|<PAGE>|<CLR>|<END>)')
    def render_units(units):
        """units: list of strings (unit text incl. leading <WAIT> token except first). returns list of lines (strings incl. tokens)"""
        lines=[]; cur=''; curw=0
        def flush():
            nonlocal cur,curw
            lines.append(cur); cur=''; curw=0
        for u in units:
            segs=u.split("\n")
            for si,seg in enumerate(segs):
                if si>0: flush()
                # tokenize seg into markup tokens and words
                parts=re.split(r'(<[0-9A-F]{4}>.|<WAIT>)',seg)
                for p in parts:
                    if not p: continue
                    if re.fullmatch(r'<[0-9A-F]{4}>.|<WAIT>',p): cur+=p; continue
                    words=re.split(r'( +)',p)
                    for w in words:
                        if w=='': continue
                        if w.isspace():
                            if cur and not cur.endswith(' '): cur+=' '; curw+=len(w)
                            continue
                        ww=width(w)
                        if ww<=cells and curw+ww<=cells:
                            cur+=w; curw+=ww
                        else:
                            cur=cur.rstrip(' '); curw=width(cur)
                            if cur: flush()
                            # Never let one unbroken word (most often a scream or sound effect)
                            # escape the line-width limit. Split only between Unicode characters,
                            # so each native Hangul cell remains intact.
                            if ww<=cells:
                                cur=w; curw=ww
                            else:
                                for ch in w:
                                    cw=width(ch)
                                    if cur and curw+cw>cells: flush()
                                    cur+=ch; curw+=cw
        flush()
        # drop trailing empty line produced by trailing newline
        while lines and lines[-1]=='' and len(lines)>1: lines.pop()
        return [l.rstrip(' ') if not l.strip()=='' else l for l in lines]
    def nlines(lines): return len(lines)
    def do_page(text):
        """returns list of page strings (already wrapped)"""
        if text.startswith("\n"):   # newline that serves as the parameter of a preceding <PAGE>: keep, don't count
            pages=do_page(text[1:]); pages[0]="\n"+pages[0]; return pages
        units=re.split(r'(?=<WAIT>)',text)
        units=[u for u in units if u!='']
        lines=render_units(units)
        def sentence_split(text):
            """split at the latest sentence or authored line boundary that fits; None if impossible"""
            cuts=[m.end() for m in re.finditer(r'[.!?…」』)](?=[ \n])',text)]
            cuts += [m.end() for m in re.finditer(r'\n',text)]
            for c in sorted(set(cuts),reverse=True):
                first=text[:c].rstrip(" \n"); rest=text[c:].lstrip(" \n")
                if not rest or not first.strip(): continue
                if not re.sub(r'<FFFC>.','',first).strip(): continue
                first_lines=render_units([first])
                if 1<=nlines(first_lines)<=maxlines:
                    return ["\n".join(first_lines)]+do_page(rest)
            return None
        if nlines(lines)<=maxlines or len(units)<=1:
            if nlines(lines)>maxlines:
                r=sentence_split(text)
                if r: return r
                out=[]
                for k in range(0,len(lines),maxlines): out.append("\n".join(lines[k:k+maxlines]))
                warn.append("hard split: %r"%text[:30]); return out
            return ["\n".join(lines)]
        for k in range(1,len(units)):
            first=units[:-k]; rest=units[-k:]
            fl=render_units(first)
            if nlines(fl)<=maxlines:
                rest_text="".join(rest)
                rest_text=re.sub(r'^<WAIT>\n?','',rest_text)  # page break replaces the wait
                return ["\n".join(fl)]+do_page(rest_text)
        r=sentence_split(text)
        if r: return r
        # fallback hard split
        out=[]
        for k in range(0,len(lines),maxlines): out.append("\n".join(lines[k:k+maxlines]))
        warn.append("hard split: %r"%text[:30]); return out
    parts=PAGE.split(ko); out=[]
    for p in parts:
        if p=='' : continue
        if PAGE.fullmatch(p): out.append(p); continue
        pages=do_page(p)
        out.append("<PAGE><CLR>".join(pages))
    return "".join(out),warn
def ui_pairs(g):
    """Address-based Korean entries; extracted Japanese template is not distributed."""
    return [tuple(x) for x in json.load(open(os.path.join(ROOT,'work','tr','ui_addresses.json'),encoding='utf-8'))]

def ram_pairs(g):
    """work/tr/ko_ram.py: R = {ram_addr_hex: (jp, ko)}; text lives in EWRAM (loaded from compressed resources); remapped by address+check words"""
    import importlib.util
    out=[]
    for fn in ("ko_ram.py","ko_credits.py","ko_extra.py","ko_encyclopedia.py"):
        p=os.path.join(ROOT,"work","tr",fn)
        if not os.path.exists(p): continue
        spec=importlib.util.spec_from_file_location("r",p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        for k,(jp,ko) in m.R.items():
            if ko: out.append((int(k,16),jp,ko))
    return out
MASTER=0x267940
def pf_entries(buf,t):
    """'Pf' table: [u16 tag][u16 n][n sizes][n offsets][data] -> list of absolute entry offsets"""
    n=struct.unpack_from("<h",buf,t+2)[0]
    offs=struct.unpack_from("<%dI"%n,buf,t+4+4*n); base=t+4+8*n
    return [base+o for o in offs]
def resolve_block_path(rom,path):
    """path[0] = master table entry; following indices walk 'Pf' tables, BPE blocks are decoded on the way.
    returns (buffer, offset)"""
    import bpe
    buf=bytes(rom.d[:0x1000000]); off=pf_entries(buf,MASTER)[path[0]]
    for i in path[1:]:
        if buf[off:off+2]!=b"Pf":
            size=struct.unpack_from("<I",buf,off)[0]; buf=bpe.decode(buf[off:off+size]); off=0
        off=pf_entries(buf,off)[i]
    return buf,off
def block_words(rom,path):
    buf,off=resolve_block_path(rom,path); out=[]
    while True:
        w=struct.unpack_from("<H",buf,off)[0]; off+=2; out.append(w)
        if w==0xffff: return out
def block_pairs(rom,g):
    """(jp words incl. FFFF, ko text) for texts inside compressed blocks: ko_houses.S/R, ko_tutorial.TUT"""
    import importlib.util
    from kowrap import wrap
    out=[]
    def load(fn):
        p=os.path.join(ROOT,"work","tr",fn)
        if not os.path.exists(p): return None
        spec=importlib.util.spec_from_file_location(fn[:-3],p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
    h=load("ko_houses.py")
    if h:
        for path,ko in h.S.items(): out.append((block_words(rom,path),ko))
        for k,(jp,ko) in h.R.items(): out.append((encode(g,jp)+[0xffff],ko))
    e=load("ko_encyclopedia.py")
    if e:
        NL=chr(10)
        for i,(name,desc) in e.ENC.items():
            out.append((block_words(rom,(4,i,2)),name))
            out.append((block_words(rom,(4,i,4)),NL.join(wrap(desc,17))))
    t=load("ko_tutorial.py")
    if t:
        for i,(title,body) in t.TUT.items():
            out.append((block_words(rom,(8,6,i,0)),title))
            NL=chr(10)
            paras=body.strip(NL).split(NL*2)
            text=(NL*2).join(NL.join(wrap(" ".join(pp.split(NL)),20)) for pp in paras)
            out.append((block_words(rom,(8,6,i,1)),text))
    return out
def ui_name_pairs():
    """single-line UI names (jp, ko) for content matching of RAM copies (e.g. item names inserted by the formatter)"""
    import importlib.util
    p=os.path.join(ROOT,"work","tr","ko_ui.py")
    spec=importlib.util.spec_from_file_location("u2",p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return [(jp,ko) for jp,ko in m.U.items() if ko]
def build_messages(rom,g,tr):
    """returns (table addr, count). table: u32 count, then entries (orig u32, new u32, check u32=first two u16 words of orig)"""
    pairs=[]
    def add(orig,ko,jpwords=None):
        ws=encode(g,ko)
        if ws[-1]!=0xffff: ws.append(0xffff)
        data=b''.join(struct.pack("<H",w) for w in ws)
        na=rom.alloc(len(data),4); rom.d[na:na+len(data)]=data
        if jpwords is None:
            jpwords=struct.unpack_from("<2H",rom.d,orig) if orig<0x1000000 else (0,0)
        chk=jpwords[0]|(jpwords[1]<<16)
        pairs.append((0x8000000+orig if orig<0x1000000 else orig, 0x8000000+na, chk))
    for a,ko in (ui_pairs(g) if not os.environ.get("NO_UI") else []): add(a,ko)
    ramrows=[]; seen={}
    for a,jp,ko in ram_pairs(g):
        jw=encode(g,jp)+[0xffff]
        if a>=0x2000000:
            key=tuple(jw)
            if key in seen:
                if seen[key]!=ko: print("WARN duplicate RAM jp with different ko:",jp)
                continue
            seen[key]=ko
            ws=encode(g,ko)+[0xffff]; data=b''.join(struct.pack("<H",w) for w in ws)
            na=rom.alloc(len(data),4); rom.d[na:na+len(data)]=data
            jd=b''.join(struct.pack("<H",w) for w in jw)
            ja=rom.alloc(len(jd),4); rom.d[ja:ja+len(jd)]=jd
            ramrows.append((jw[0]|(jw[1]<<16),0x8000000+ja,0x8000000+na))
        else:
            add(a,ko,jw[:2])
    def ramrow(jw,ko):
        key=tuple(jw)
        if key in seen:
            if seen[key]!=ko: print("WARN duplicate RAM jp with different ko:",jw[:6])
            return
        seen[key]=ko
        ws=encode(g,ko)+[0xffff]; data=b''.join(struct.pack("<H",w) for w in ws)
        na=rom.alloc(len(data),4); rom.d[na:na+len(data)]=data
        jd=b''.join(struct.pack("<H",w) for w in jw)
        ja=rom.alloc(len(jd),4); rom.d[ja:ja+len(jd)]=jd
        ramrows.append((jw[0]|(jw[1]<<16),0x8000000+ja,0x8000000+na))
    for jw,ko in block_pairs(rom,g): ramrow(jw,ko)
    for jp,ko in ui_name_pairs():
        try: ramrow(encode(g,jp)+[0xffff],ko)
        except KeyError: pass
    for k,ko in tr.items():
        if not ko: continue
        ko,warn=layout(ko)
        for w in warn: print("WARN",k,w)
        add(int(k,16),ko)
    # Inventory code reads these relative pointers inline, then walks the
    # multi-line text itself. Relocate the source entry before it is split.
    replacements={o-0x08000000:n-0x08000000 for o,n,check in pairs}
    root=0x28fd20
    for index in range(0x3f,0x49):
        slot=root+4+4*index
        old=root+struct.unpack_from('<I',rom.d,slot)[0]
        if old in replacements:
            rom.u32(slot,replacements[old]-root)
            print('inventory source',hex(index),hex(old),'->',hex(replacements[old]))
    pairs.sort()
    tbl=rom.alloc(4+12*len(pairs),4)
    rom.u32(tbl,len(pairs))
    for i,(o,nw,chk) in enumerate(pairs): rom.u32(tbl+4+12*i,o); rom.u32(tbl+8+12*i,nw); rom.u32(tbl+12+12*i,chk)
    ramrows.sort(key=lambda r:r[0])
    rt=rom.alloc(4+12*len(ramrows),4); rom.u32(rt,len(ramrows))
    for i,(k0,jp,nw) in enumerate(ramrows): rom.u32(rt+4+12*i,k0); rom.u32(rt+8+12*i,jp); rom.u32(rt+12+12*i,nw)
    srch=SEARCH.replace("RAMTABLE","0x%x"%(0x8000000+rt)).replace("TABLE","0x%x"%(0x8000000+tbl))
    sa=rom.alloc(len(assemble(srch,0)),4); rom.d[sa:sa+len(assemble(srch,0))]=assemble(srch,0x8000000+sa)
    S="0x%x"%(0x8000000+sa+1)
    def place(src):
        code=assemble(src.replace("SEARCH",S),0); a=rom.alloc(len(code),4); rom.d[a:a+len(code)]=assemble(src.replace("SEARCH",S),0x8000000+a); return a
    h1=place(HOOK); h2=place(HOOK2)
    def patch_entry(site,target,reg=3):
        # ldr rN,[pc,#0]; bx rN; .word target|1   (reg 3 for plain functions; reg 4 when r3 is an argument)
        rom.d[site:site+4]=bytes([0x00,0x48|reg,0x00|(reg<<3),0x47]); rom.u32(site+4,0x8000000+target+1)
    # Native one-code glyphs use the unmodified tile copier; no odd-code skipping.
    # 0x8031cfc: 18-byte body -> ldr r3,[pc]; bx r3; .word
    patch_entry(0x31cfc,h1)
    if not os.environ.get("NO_HOOK2"): patch_entry(0x2ebb8,h2)
    # Original prologue: push r4-r6/lr; mov r4,0; ldrh r3,[r0]; ldr r5,=FFFF.
    # Preserve all arguments and caller registers before SEARCH.
    linehook = place("""
push {r4, r5, r6, lr}
push {r1, r2, r3}
"""+CALL+"""
pop {r1, r2, r3}
movs r4, #0
ldrh r3, [r0, #0]
ldr r5, =0xffff
ldr r6, =0x8025799
bx r6
""")
    patch_entry(0x25790,linehook)
    ph=[]
    if not os.environ.get("NO_LEAF"):
        assert rom.d[0x25760:0x25764]==bytes.fromhex("10b50023") and rom.d[0x255b4:0x255b8]==bytes.fromhex("30b50024"), "leaf entry"
        patch_entry(0x25760,place(STRLEN),3); patch_entry(0x255b4,place(LINES),3)
        assert rom.d[0x25a30:0x25a3c]==bytes.fromhex("f0b5041c171c09040e0c2088"), "format entry"
        fm=place(FORMAT); rom.d[0x25a32:0x25a38]=bytes.fromhex("014c2047c046"); rom.u32(0x25a38,0x8000000+fm+1)
    if not os.environ.get("NO_HOOK3"):
        for E,treg in PROLOGUE_HOOKS:
            o=E-0x8000000
            assert o%4==0 and rom.d[o:o+10]==bytes.fromhex("f0b557464e464546e0b4") and rom.d[o+11]==0xb0, hex(E)
            h=place(prologue_hook_src(E,treg,rom.d[o+10]*4)); ph.append(h)
            rom.d[o+2:o+8]=bytes.fromhex("014c2047c046"); rom.u32(o+8,0x8000000+h+1)
    print("search",hex(sa),"hooks",hex(h1),hex(h2),[hex(x) for x in ph],"table",hex(tbl),"ramrows",len(ramrows))
    return tbl,len(pairs),ph
def apply_fixed_records(rom,g,path,recsize=0x50):
    """in-place fixed-size string records: {addr_hex: ko}; text must fit in recsize/2-1 words"""
    import importlib.util
    if not os.path.exists(path): return 0
    spec=importlib.util.spec_from_file_location("s",path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    n=0
    for k,ko in m.S.items():
        a=int(k,16); ws=encode(g,ko)+[0xffff]
        if len(ws)>recsize//2: print("WARN sys string too long",k,ko); continue
        if width(ko)>22: print("WARN sys string wider than 22 cells:",k,ko,width(ko))
        data=b''.join(struct.pack("<H",w) for w in ws); data+=b'\0'*(recsize-len(data))
        rom.d[a:a+recsize]=data; n+=1
    return n
if __name__=="__main__":
    rom=Rom(); g=Glyphs()
    if not os.environ.get("NO_SYS"): print("sys strings",apply_fixed_records(rom,g,os.path.join(ROOT,"work","tr","ko_sys.py")))
    trp=os.path.join(ROOT,"work","tr","messages_ko.json")
    tr=json.load(open(trp,encoding="utf-8")) if os.path.exists(trp) else {}
    tbl,n,_=build_messages(rom,g,tr)
    base,bands=g.install(rom)
    if not os.environ.get("NO_GFX"):
        import gfx_ko; print("gfx banners",len(gfx_ko.apply(rom.d, alloc=rom.alloc)))
    out=os.path.join(ROOT,"work",os.environ.get("OUT","test.gba")); rom.save(out)
    # 패치된 ROM은 항상 원본 ROM과 같은 폴더(프로젝트 루트)에도 둔다
    import shutil
    final=os.path.join(ROOT,"Klonoa Heroes - Densetsu no Star Medal (Korean).gba")
    if not os.environ.get("OUT"):
        try: shutil.copyfile(out,final); print("copied to",final)
        except OSError as e: print("WARN: could not copy next to the original ROM (in use?):",e)
    print("messages",n,"glyph chars",len(g.map),"bands",bands,"font base",hex(base),"free",hex(rom.free))
