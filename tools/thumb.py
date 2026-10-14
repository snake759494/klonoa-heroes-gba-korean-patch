# tiny hand assembler for the subset of Thumb we need
def enc(instr):
    """returns list of u16"""
    i=instr.strip().lower().replace(",", " ").split()
    op=i[0]
    R=lambda s:int(s.strip("r").replace("lr","14").replace("pc","15").replace("sp","13"))
    def reg(s):
        s=s.strip()
        return {"lr":14,"pc":15,"sp":13,"sb":9,"sl":10,"fp":11,"ip":12}.get(s, int(s[1:]) if s.startswith("r") else None)
    imm=lambda s:int(s.replace("#",""),0)
    if op=="push" or op=="pop":
        regs=" ".join(i[1:]).strip("{}").replace("{","").replace("}","").split()
        m=0; lrpc=0
        for r in regs:
            r=r.strip()
            if "-" in r:
                a,b=r.split("-"); 
                for k in range(reg(a),reg(b)+1): m|=1<<k
            elif r=="lr": lrpc=1
            elif r=="pc": lrpc=1
            else: m|=1<<reg(r)
        return [(0xB400 if op=="push" else 0xBC00)|(lrpc<<8)|m]
    if op=="mov" and reg(i[1]) is not None and reg(i[2]) is not None:
        rd,rs=reg(i[1]),reg(i[2])
        if rd<8 and rs<8: return [0x1C00|(rs<<3)|rd]  # adds rd, rs, #0
        return [0x4600|((rd>>3)<<7)|(rs<<3)|(rd&7)]
    if op=="movs" and reg(i[2]) is None: return [0x2000|(reg(i[1])<<8)|imm(i[2])]
    if op in("lsls","lsrs","asrs") and len(i)==4:
        code={"lsls":0,"lsrs":1,"asrs":2}[op]; return [(code<<11)|(imm(i[3])<<6)|(reg(i[2])<<3)|reg(i[1])]
    if op=="adds" and len(i)==4 and reg(i[3]) is not None: return [0x1800|(reg(i[3])<<6)|(reg(i[2])<<3)|reg(i[1])]
    if op=="subs" and len(i)==4 and reg(i[3]) is not None: return [0x1A00|(reg(i[3])<<6)|(reg(i[2])<<3)|reg(i[1])]
    if op=="adds" and len(i)==4: return [0x1C00|(imm(i[3])<<6)|(reg(i[2])<<3)|reg(i[1])]
    if op=="subs" and len(i)==4: return [0x1E00|(imm(i[3])<<6)|(reg(i[2])<<3)|reg(i[1])]
    if op=="adds" and len(i)==3: return [0x3000|(reg(i[1])<<8)|imm(i[2])]
    if op=="subs" and len(i)==3: return [0x3800|(reg(i[1])<<8)|imm(i[2])]
    if op=="cmp" and reg(i[2]) is not None: return [0x4280|(reg(i[2])<<3)|reg(i[1])]
    if op=="ands": return [0x4000|(reg(i[2])<<3)|reg(i[1])]
    if op=="cmp": return [0x2800|(reg(i[1])<<8)|imm(i[2])]
    if op in("ldr","ldrh","ldrb","str","strh","strb"):
        # ldr rd, [rb, #imm]  or ldr rd, [rb, ro]
        s=instr.lower(); rd=reg(i[1]); inside=s[s.index("[")+1:s.index("]")].replace(","," ").split()
        rb=reg(inside[0]); off=inside[1] if len(inside)>1 else "#0"
        if off.startswith("#"):
            v=imm(off)
            if op=="ldr":
                if rb==15: return [0x4800|(rd<<8)|(v>>2)]
                if rb==13: return [0x9800|(rd<<8)|(v>>2)]
                return [0x6800|((v>>2)<<6)|(rb<<3)|rd]
            if op=="str":
                if rb==13: return [0x9000|(rd<<8)|(v>>2)]
                return [0x6000|((v>>2)<<6)|(rb<<3)|rd]
            if op=="ldrh": return [0x8800|((v>>1)<<6)|(rb<<3)|rd]
            if op=="strh": return [0x8000|((v>>1)<<6)|(rb<<3)|rd]
            if op=="ldrb": return [0x7800|(v<<6)|(rb<<3)|rd]
            if op=="strb": return [0x7000|(v<<6)|(rb<<3)|rd]
        ro=reg(off)
        base={"str":0x5000,"strh":0x5200,"strb":0x5400,"ldr":0x5800,"ldrh":0x5A00,"ldrb":0x5C00}[op]
        return [base|(ro<<6)|(rb<<3)|rd]
    if op in ("sub","add") and len(i)==3 and i[1]=="sp": return [(0xB080 if op=="sub" else 0xB000)|(imm(i[2])>>2)]
    if op=="bx": return [0x4700|(reg(i[1])<<3)]
    if op=="nop": return [0x46C0]
    raise ValueError(instr)
COND={"beq":0,"bne":1,"bcs":2,"bhs":2,"bcc":3,"blo":3,"bmi":4,"bpl":5,"bvs":6,"bvc":7,"bhi":8,"bls":9,"bge":10,"blt":11,"bgt":12,"ble":13}
def assemble(src, base):
    """two-pass; labels 'name:'; branches b/bxx label; '.word v'; 'ldr rX, =v' literal pool at end"""
    lines=[l.split(";")[0].strip() for l in src.splitlines()]; lines=[l for l in lines if l]
    # pass1: sizes
    labels={}; pc=base; items=[]; lits=[]
    for l in lines:
        if l.endswith(":"): labels[l[:-1]]=pc; continue
        if l.startswith(".word"): items.append(("word",l)); pc+=4; continue
        if l.startswith(".align"): 
            if pc&3: items.append(("nop",l)); pc+=2
            continue
        items.append(("ins",l)); pc+=2
    litbase=(pc+3)&~3
    # collect literals
    for k,l in items:
        if k=="ins" and "=" in l and l.split()[0]=="ldr": 
            v=l.split("=")[1].strip()
            if v not in lits: lits.append(v)
    out=bytearray(); pc=base
    def resolve(v): 
        v=v.strip()
        return labels[v] if v in labels else int(v,0)
    for k,l in items:
        if k=="word": out+=resolve(l.split()[1]).to_bytes(4,"little"); pc+=4; continue
        if k=="nop": out+=(0x46C0).to_bytes(2,"little"); pc+=2; continue
        op=l.split()[0]
        if op=="b" or op in COND:
            target=labels[l.split()[1]]; off=(target-(pc+4))>>1
            if op=="b": w=0xE000|(off&0x7FF)
            else: w=0xD000|(COND[op]<<8)|(off&0xFF)
            out+=w.to_bytes(2,"little"); pc+=2; continue
        if op=="ldr" and "=" in l:
            lhs,v=l.split("=",1); rd=int(lhs.split()[1].strip(",")[1:]); v=v.strip(); la=litbase+4*lits.index(v)
            off=la-((pc+4)&~3); w=0x4800|(rd<<8)|(off>>2); out+=w.to_bytes(2,"little"); pc+=2; continue
        for w in enc(l): out+=w.to_bytes(2,"little"); pc+=2
    while len(out)%4: out+=b'\x00'
    for v in lits: out+=resolve(v).to_bytes(4,"little")
    return bytes(out)
if __name__=="__main__":
    print(assemble("push {r4-r7,lr}\nldrb r0,[r2,#4]\nldr r3,=0x804e661\nbx r3\nfoo:\nb foo\n.word 0x12345678",0x8690000).hex())
