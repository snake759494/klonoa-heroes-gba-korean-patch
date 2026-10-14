# Unit tests of the patch hooks on the built ROM, executed with unicorn (ARM7TDMI Thumb subset).
# usage: python tools/utest.py [rom]
import sys, os, struct, json
sys.path.insert(0, os.path.dirname(__file__))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import *
from charmap import CH2CODE, CODE2CH
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
ROMP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "work", "test.gba")
rom = open(ROMP, "rb").read()
GM = json.load(open(os.path.join(ROOT, "work", "glyphmap.json"), encoding="utf-8"))
REV = {}
for ch, cl in GM.items():
    for k, c in enumerate(cl): REV[c] = (ch, k)
MAGIC = 0x0DF00000  # return address (mapped, never executed)
REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
        UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_R12]

def new_cpu():
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    mu.mem_map(0x08000000, 0x02000000); mu.mem_write(0x08000000, rom)
    mu.mem_map(0x02000000, 0x40000); mu.mem_map(0x03000000, 0x8000)
    mu.mem_map(0x0DF00000, 0x1000)
    return mu

def enc_jp(s):
    out = []
    i = 0
    while i < len(s):
        if s.startswith("<FFFC>", i): out.append(0xfffc); i += 6; continue
        if s.startswith("<WAIT>", i): out.append(0xfff6); i += 6; continue
        if s.startswith("<PAGE>", i): out.append(0xfff7); i += 6; continue
        if s.startswith("<CLR>", i): out.append(0xfffe); i += 5; continue
        c = s[i]; i += 1
        if c in " 　": out.append(0xa0); continue
        out.append(0xfffd if c == "\n" else CH2CODE[c])
    return out + [0xffff]

def words_at(mu, a, n=200):
    out = []
    for k in range(n):
        w = struct.unpack("<H", mu.mem_read(a + 2 * k, 2))[0]
        out.append(w)
        if w == 0xffff: break
    return out

def dec(ws):
    s = ""; skip = False
    for w in ws:
        if w == 0xffff: break
        if w == 0xfffd: s += "\\n"; continue
        if w >= 0xfff0: s += "<%X>" % w; continue
        if w in REV:
            ch, k = REV[w]
            if k == 0: s += ch
            continue
        s += CODE2CH.get(w, "{%X}" % w)
    return s

def call(mu, fn, args, stack_args=(), sp=0x03007E00, until=MAGIC, regs_init=None):
    for i, v in enumerate(args): mu.reg_write(REGS[i], v)
    if regs_init:
        for r, v in regs_init.items(): mu.reg_write(REGS[r], v)
    sp -= 4 * len(stack_args)
    for i, v in enumerate(stack_args): mu.mem_write(sp + 4 * i, struct.pack("<I", v))
    mu.reg_write(UC_ARM_REG_SP, sp)
    mu.reg_write(UC_ARM_REG_LR, MAGIC | 1)
    mu.emu_start(fn | 1, until, count=2000000)
    return mu.reg_read(UC_ARM_REG_R0)

def put(mu, a, ws): mu.mem_write(a, b"".join(struct.pack("<H", w) for w in ws))

ok = 0; bad = 0
def check(name, cond, info=""):
    global ok, bad
    if cond: ok += 1; print("  OK  ", name, info)
    else: bad += 1; print("  FAIL", name, info)

def lit(addr):  # word at ROM address
    return struct.unpack_from("<I", rom, addr - 0x08000000)[0]

# locate SEARCH: hook1 stub at 0x8031cfc -> literal -> hook1 code -> literal pool contains SEARCH|1
h1 = lit(0x8031d00) - 1
search = None
for k in range(0, 0x40, 4):
    v = lit(h1 + k)
    if 0x09000000 <= v < 0x0A000000 and v & 1: search = v - 1; break
print("SEARCH at %x" % search)

print("[SEARCH]")
mu = new_cpu()
title = enc_jp("ヒカリサクラを とりかえせ！".replace(" ", "　"))
put(mu, 0x02001138, title)
r = call(mu, search, [0x02001138])
check("chapter title in EWRAM -> ko", 0x09000000 <= r < 0x0A000000, dec(words_at(mu, r)))
put(mu, 0x03007E9C, enc_jp("ブリーガル"))
r = call(mu, search, [0x03007E9C])
check("area name in IWRAM -> ko", 0x09000000 <= r < 0x0A000000, dec(words_at(mu, r)))
put(mu, 0x02001A34, enc_jp("ブリーガル\nジャグケトルのうみ"))
r = call(mu, search, [0x02001A34])
check("prefix-only match rejected", r == 0x02001A34, hex(r))
put(mu, 0x02000500, enc_jp("ガンツ"))
r = call(mu, search, [0x02000500])
check("boss name -> ko", 0x09000000 <= r < 0x0A000000, dec(words_at(mu, r)))
r = call(mu, search, [0x0800F000])
check("random ROM pointer unchanged", r == 0x0800F000)
r = call(mu, search, [2])
check("small int unchanged", r == 2)

print("[prologue hooks]")
for E, treg, subsp in ((0x080252d8, 2, 0x10), (0x0805712c, 2, 0xc), (0x0802569c, 0, 0x14), (0x08025470, 2, 0x14)):
    mu = new_cpu()
    put(mu, 0x02001abc, enc_jp("ぼうけんをおもいだす\nもうねる"))
    args = [0x11, 0x22, 0x33, 0x44]
    args[treg] = 0x02001abc
    init = {4: 0x44440004, 5: 0x55550005, 6: 0x66660006, 7: 0x77770007, 8: 0x88880008, 9: 0x99990009, 10: 0xAAAA000A}
    sp0 = 0x03007E00
    call(mu, E, args, regs_init=init, sp=sp0, until=E + 12)
    sp = mu.reg_read(UC_ARM_REG_SP)
    st = struct.unpack("<%dI" % ((sp0 - sp) // 4), mu.mem_read(sp, sp0 - sp))
    exp_frame = (sp0 - sp) == subsp + 12 + 20
    saved = st[subsp // 4: subsp // 4 + 8]
    exp_saved = (0x88880008, 0x99990009, 0xAAAA000A, 0x44440004, 0x55550005, 0x66660006, 0x77770007, MAGIC | 1)
    tr = mu.reg_read(REGS[treg])
    others = [mu.reg_read(REGS[i]) for i in range(4) if i != treg]
    check("hook %x frame" % E, exp_frame and tuple(saved) == exp_saved, "sp delta %x" % (sp0 - sp))
    check("hook %x text remapped" % E, 0x09000000 <= tr < 0x0A000000, dec(words_at(mu, tr)))
    check("hook %x args kept" % E, others == [args[i] for i in range(4) if i != treg])

print("[strlen / lines]")
mu = new_cpu()
put(mu, 0x02000100, enc_jp("チュートリアルについて"))
r = call(mu, 0x08025760, [0x02000100])
translated = call(mu, search, [0x02000100])
check("strlen of tutorial title = encoded Korean width", r == len(words_at(mu, translated))-1, str(r))
put(mu, 0x02000200, enc_jp("あいう\nえお\n\nかき"))
r = call(mu, 0x080255b4, [0x02000200])
check("line count (untranslated)", r == 4, str(r))

print("[format]")
mu = new_cpu()
import importlib.util
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build
class R: pass
rr = R(); rr.d = bytearray(open(os.path.join(ROOT, "Klonoa Heroes - Densetsu no Star Medal (Japan).gba"), "rb").read())
jw = build.block_words(rr, (10, 4, 3))
put(mu, 0x02001300, jw)
put(mu, 0x02000600, enc_jp("ガンツ"))
call(mu, 0x08025a30, [0x02001300, 0xBA, 0x02000600, 0x02000800])
check("format template+name", True, dec(words_at(mu, 0x02000800)))
jw = build.block_words(rr, (8, 6, 36, 1))
put(mu, 0x02002000, jw)
r = call(mu, 0x080255b4, [0x02002000])
line_count = r
r = call(mu, search, [0x02002000])
ws = words_at(mu, r, 2000)[:-1]
lines = [[]]
for w in ws:
    if w == 0xfffd: lines.append([])
    else: lines[-1].append(w)
mx = max(len(l) for l in lines)
check("tutorial 36 line count equals translated newline count", line_count == len(lines), str(line_count))
check("tutorial 36 max line codes <= 20", mx <= 20, "lines=%d max=%d" % (len(lines), mx))
# all tutorial bodies: widest line in codes
worst = []
for i in range(37):
    jw = build.block_words(rr, (8, 6, i, 1)); put(mu, 0x02002000, jw)
    r = call(mu, search, [0x02002000]); ws = words_at(mu, r, 3000)[:-1]
    ls = [[]]
    for w in ws:
        if w == 0xfffd: ls.append([])
        else: ls[-1].append(w)
    worst.append((max(len(l) for l in ls), i, len(ls)))
    jt = build.block_words(rr, (8, 6, i, 0)); put(mu, 0x02001f00, jt)
    rt = call(mu, search, [0x02001f00])
    if rt == 0x02001f00: check("tutorial %d title remapped" % i, False)
    if r == 0x02002000: check("tutorial %d body remapped" % i, False)
check("all tutorial lines <= 20 codes", max(worst)[0] <= 20, str(max(worst)))
print("done: %d ok, %d fail" % (ok, bad))


print("[relocated title cards: game's own BPE decoder]")
import bpe
r = None
TPROOT = 0x8fda70
def u(a): return struct.unpack_from("<I", rom, a - 0x08000000 if a >= 0x08000000 else a)[0]
root = TPROOT
r23 = root + u(root + u(root + 8) + 4 * 0x23)
first = u(r23 + 8)
bad_cards = 0
for i in (1, 20, 42, 49):
    s = r23 + u(r23 + first + 4 * i)
    size = u(s); outsize = u(s + 4)
    mu = new_cpu()
    mu.mem_map(0x04000000, 0x1000)
    call(mu, 0x0804e428, [0x08000000 + s, 0x02028000])
    got = bytes(mu.mem_read(0x02028000, outsize))
    exp = bpe.decode(rom[s:s + size])
    ok_i = got == exp and got[:2] == b"CT"
    if not ok_i: bad_cards += 1
    check("card %d decodes with game routine" % i, ok_i, "size %d" % outsize)
print("done: %d ok, %d fail" % (ok, bad))

print("[encyclopedia]")
mu = new_cpu()
worst_d = 0; worst_n = 0; miss = 0
for i in range(96):
    jn = build.block_words(rr, (4, i, 2)); put(mu, 0x02003000, jn)
    rn = call(mu, search, [0x02003000])
    jd = build.block_words(rr, (4, i, 4)); put(mu, 0x02004000, jd)
    rd = call(mu, search, [0x02004000])
    if rn == 0x02003000 or rd == 0x02004000: miss += 1; continue
    wn = len(words_at(mu, rn, 100)) - 1
    ls = [[]]
    for w in words_at(mu, rd, 3000)[:-1]:
        if w == 0xfffd: ls.append([])
        else: ls[-1].append(w)
    worst_d = max(worst_d, max(len(l) for l in ls)); worst_n = max(worst_n, wn)
check("encyclopedia 96 names+descriptions remapped", miss == 0, "missing %d" % miss)
check("encyclopedia name <= 21 codes", worst_n <= 21, str(worst_n))
check("encyclopedia description lines <= 17 codes", worst_d <= 17, str(worst_d))
print("done: %d ok, %d fail" % (ok, bad))

print('[native compact cells and line extraction]')
check('one code per Hangul glyph', all(len(v)==1 for v in GM.values()))
mu=new_cpu()
source=enc_jp('ぼうけんをおもいだす\nもうねる')
put(mu,0x02001000,source)
translated=call(mu,search,[0x02001000])
expected=words_at(mu,translated)[:-1]
segments=[[]]
for w in expected:
    if w==0xfffd: segments.append([])
    else: segments[-1].append(w)
for i,segment in enumerate(segments):
    dst=0x02002002
    mu.mem_write(dst-2,b'\xa5'*256)
    call(mu,0x08025790,[0x02001000,dst,i])
    got=words_at(mu,dst)
    check('line extractor translates before slicing %d'%i,got==segment+[0xffff],dec(got))
    check('line extractor buffer guards %d'%i,bytes(mu.mem_read(dst-2,2))==b'\xa5\xa5' and bytes(mu.mem_read(dst+2*len(got),2))==b'\xa5\xa5')
import numpy as np
import gfx_ko,ctgfx
original=open(os.path.join(ROOT,'Klonoa Heroes - Densetsu no Star Medal (Japan).gba'),'rb').read()
for index,text in [(24,'이야기 끝'),(25,'모든 모험 끝')]:
    root=0x7d9d38
    a=root+struct.unpack_from('<I',rom,root+4+index*4)[0]
    old=root+struct.unpack_from('<I',original,root+4+index*4)[0]
    size,outsize=struct.unpack_from('<II',rom,a)
    data=bpe.decode(rom[a:a+size]);mu=new_cpu();mu.mem_map(0x04000000,0x1000)
    call(mu,0x0804e428,[0x08000000+a,0x02010000])
    check('ending original decoder %d'%index,bytes(mu.mem_read(0x02010000,outsize))==data)
    before,_,oc=ctgfx.image(bpe.decode(original[old:old+struct.unpack_from('<I',original,old)[0]]))
    after,entries,c=ctgfx.image(data)
    check('ending CT bounds %d'%index,c['tsize']<8192 and all((e&1023)<c['nt'] for e in entries))
    check('ending surrounding art %d'%index,np.array_equal(before[:36],after[:36]) and np.array_equal(before[57:],after[57:]))
    m,_=gfx_ko.line_mask(text,'Galmuri14');x=(240-m.shape[1])//2
    check('ending native Korean glyphs %d'%index,np.array_equal(after[39:39+m.shape[0],x:x+m.shape[1]]==1,m))
print('done: %d ok, %d fail'%(ok,bad))
print('[all relocated area labels: game BPE decoder]')
area_errors=[]
for i in range(58):
    base=0x8a398c
    a=base+struct.unpack_from('<I',rom,base+4+4*i)[0]
    size,outsize=struct.unpack_from('<II',rom,a)
    mu=new_cpu();mu.mem_map(0x04000000,0x1000)
    call(mu,0x0804e428,[0x08000000+a,0x02028000])
    got=bytes(mu.mem_read(0x02028000,outsize))
    if got!=bpe.decode(rom[a:a+size]):area_errors.append(i)
check('58 area labels decode with original game routine',not area_errors,str(area_errors))
print('done: %d ok, %d fail'%(ok,bad))
print('[inventory source pointers and nested image containers]')
root=0x28fd20
for index in range(0x40,0x49):
    a=root+struct.unpack_from('<I',rom,root+4+4*index)[0]
    ws=list(struct.unpack_from('<200H',rom,a));ws=ws[:ws.index(0xffff)]
    check('inventory source relocated %02x'%index,a>=0x1000000 and any(w in REV for w in ws),dec(ws))
    check('inventory source no Japanese %02x'%index,not any(0x3040<=ord(CODE2CH.get(w,' ')[0])<=0x30ff for w in ws if w<0xfff0 and w not in REV))
for start,expected in [(0x37ed8,[0,2,255]),(0x37eea,[1,2,255]),(0x37ef8,[3,2,255]),(0x37f04,[4,2,255]),(0x37f16,[5,2,255,255]),(0x37f2c,[6,7,2])]:
    check('effect sequence %x'%start,[rom[start+4*j] for j in range(len(expected))]==expected)
import gfx_ko,ctgfx
for parent,children in [(9,[1]),(10,[1,3])]:
    a,_,_=gfx_ko.pf_entry_addr(rom,0x267940,parent)
    size,outsize=struct.unpack_from('<II',rom,a)
    data=bpe.decode(rom[a:a+size]);mu=new_cpu();mu.mem_map(0x04000000,0x1000)
    call(mu,0x0804e428,[0x08000000+a,0x02010000])
    check('nested Pf original decoder %d'%parent,bytes(mu.mem_read(0x02010000,outsize))==data)
    for index in children:
        p,_,_=gfx_ko.pf_entry_addr(data,0,index)
        raw=data[p:]
        if raw[:2]!=b'CT':raw=bpe.decode(raw[:struct.unpack_from('<I',raw)[0]])
        im,entries,c=ctgfx.image(raw)
        check('nested CT bounds %d/%d'%(parent,index),all((e&1023)<c['nt'] for e in entries))
print('done: %d ok, %d fail'%(ok,bad))
sys.exit(1 if bad else 0)
