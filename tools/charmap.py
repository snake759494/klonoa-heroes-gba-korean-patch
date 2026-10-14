# code->char map for Klonoa Heroes 8x16 font (32 glyphs per band, font at ROM 0x29672c)
BANDS=[
"あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみ",
"むめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶ",
"べぼぱぴぷぺぽぁぃぅぇぉっゃゅょアイウエオカキクケコサシスセソタ",
"チツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンガギ",
"グゲゴザジズゼゾダヂヅデドバビブベボパピプペポァィゥェォッャュョ",
"　ヴ０１２３４５６７８９ー、。！？＋－×％／～＆「」♡♪♭ヰヱ※",
"ゔＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ：…＜＞．",
"（）・『』【】Ｔ`Ｌ㈱゛゜",
"月夢日晴春年幸古信夕村寺天空院今丘安心立入金色光花実力魂方法目前",
"気台場負名明朝決先大欠点面若人正列上世界原国小予想行不近中口者穴",
"外悪送追本々消間赤水初会少空足元宇宙作伝説巨化自信差一歩工業都市",
"先生見三二打発急火全国出回借木代的令当了時話高声男川分",
]
CODE2CH={}
for b,s in enumerate(BANDS):
    for c,ch in enumerate(s): CODE2CH[b*32+c]=ch
CH2CODE={ch:c for c,ch in CODE2CH.items() if ch!="　"}
CTRLNAMES={0xffff:"<END>",0xfffe:"<CLR>",0xfffd:"\n",0xfff7:"<PAGE>",0xfff6:"<WAIT>"}
def decode(words):
    out=[]
    for w in words:
        if w==0xa0: out.append(" ")
        elif w in CTRLNAMES: out.append(CTRLNAMES[w])
        elif w>=0x8000: out.append("<%04X>"%w)
        elif w in CODE2CH: out.append(CODE2CH[w])
        else: out.append("{%X}"%w)
    return "".join(out)
