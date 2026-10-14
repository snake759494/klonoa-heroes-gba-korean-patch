"""Native sprite CT resources missed by the previous tilemap-only graphics audit."""
import struct
import numpy as np
import bpe,ctgfx,gfx_ko
SPEAKERS=['크로노아','간츠','판고','로로','포프카','대무녀','무녀','카랄','파멜라','치플','괴물','조커','쟝가','가렌','나하툼','???','바루','디그로','월장로','주민','마을사람','할아버지','괴물','괴물','볼크병','응가포코','로봇','괴물','포로','안내방송','달주민','폴리스','안나','푸치','스스무','바치','돈짱','캇짱','모시군','모지짱','모네짱','산드라','발키리','길','카이','아저씨','마메트']
AREAS=['바람마을 벚꽃고개','바람마을 동쪽초원','클레아 사원','종의 언덕','종의 언덕 기슭','중앙 가도','간스톤 채석장','브리갈 동쪽가도','마그나 목장','크로노아의 집','마을 외곽','자그케틀 국경','자그케틀 해안','수상 시장','자그케틀 곶','자그케틀 만','파멜라의 둥지','자그레네 해협','문즈 마을','문즈 유적 서문','문즈 유적 동문','문즈 유적 감옥','포로의 피라미드','죽음의 덫 피라미드','수수께끼 피라미드','천공사원 기슭','천공사원','천공사원 정원','천공사원 공중운하','천공사원 도서관','천공사원 안쪽','천공사원 성역','볼크 공장지대','볼크 공장 A구역','볼크 공장 B구역','볼크 공장 C구역','볼크군 로켓기지','우주','달 표면','월면인의 마을','월면 돔','루나 베이스','입구','의무실','순찰 관제센터','코어 구역','꿈의 밑바닥','가렌의 방','샛길','나하트의 어둠','자작나무 1번가','엉겅퀴 광장','큰길','자그케틀 항구','발굴 캠프','천공사원 내전','새벽 광장','월면인 숙소']

def native_write(raw,img):
    c=ctgfx.parse(raw); assert c['msize']==0
    out=bytearray(raw)
    for y in range(c['mh']):
        for x in range(c['mw']):
            a=c['tiles']+(y*c['mw']+x)*32
            out[a:a+32]=gfx_ko._pack_tile(img[y*8:y*8+8,x*8:x*8+8],4)
    return out

def mapped_write(raw,img):
    _,entries,c=ctgfx.image(raw)
    out=bytearray(raw[:c['map']]+b'\0'*2048+raw[c['map']:])
    struct.pack_into('<I',out,0x10,c['tsize']+2048)
    struct.pack_into('<I',out,0x1c,c['map']+2048)
    return gfx_ko.rebuild_ct(out,img,entries,ctgfx.parse(out),True)[0]

def apply(rom,alloc):
    report=[]
    # Ending cards: scene table 1, entries 24/25. Keep the original CT tile
    # dimensions and palette; grow tile storage only by the required 8-tile step.
    root=0x7d9d38
    for i,text in [(24,'이야기 끝'),(25,'모든 모험 끝')]:
        a=root+struct.unpack_from('<I',rom,root+4+4*i)[0]
        raw=bpe.decode(rom[a:a+struct.unpack_from('<I',rom,a)[0]])
        img,entries,c=ctgfx.image(raw)
        original=img.copy()
        img[36:57,:240]=0
        m,_=gfx_ko.line_mask(text,'Galmuri14')
        assert m.shape[0]<=16 and m.shape[1]<=130
        x=(240-m.shape[1])//2;y=39
        # Native pixels, black outline and white body, matching the original.
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                gfx_ko.draw(img,m,x+dx,y+dy,7)
        gfx_ko.draw(img,m,x,y,1)
        assert np.array_equal(img[:36],original[:36])
        assert np.array_equal(img[57:],original[57:])
        for extra in range(0,2049,256):
            expanded=bytearray(raw[:c['map']]+b'\0'*extra+raw[c['map']:])
            struct.pack_into('<I',expanded,0x10,c['tsize']+extra)
            struct.pack_into('<I',expanded,0x1c,c['map']+extra)
            try:
                rebuilt,used=gfx_ko.rebuild_ct(expanded,img,entries,ctgfx.parse(expanded),True)
                break
            except ValueError:
                if extra==2048:raise
        data=bpe.encode_literal(rebuilt);new=alloc(len(data),4)
        rom[new:new+len(data)]=data
        struct.pack_into('<I',rom,root+4+4*i,new-root)
        report.append({'kind':'ending','id':i,'text':text,'address':new,'tiles':used})
    # These Pf containers are themselves compressed. Rebuild the nested table,
    # then relocate the whole parent so its relative child offsets stay valid.
    import build
    master=0x267940
    for parent,changes in [(8,[(4,'START:메뉴')]),(9,[(1,'마메트 하우스')]),(10,[(1,'모메트 하우스'),(3,'완료')])]:
        a,_,_=gfx_ko.pf_entry_addr(rom,master,parent)
        compressed=rom[a:a+2]!=b'Pf'
        if compressed:
            data=bytearray(bpe.decode(rom[a:a+struct.unpack_from('<I',rom,a)[0]]));table=0
        else:
            data=rom;table=a
        for index,text in changes:
            child,base,n=gfx_ko.pf_entry_addr(data,table,index)
            if data[child:child+2]==b'CT':
                c=ctgfx.parse(data[child:child+32]);raw=bytes(data[child:child+c['map']+c['msize']]);child_compressed=False
            else:
                raw=bpe.decode(data[child:child+struct.unpack_from('<I',data,child)[0]]);child_compressed=True
            img,_,c=ctgfx.image(raw)
            if index==1:
                region=img[5:24,5:c['w']-5];region[np.isin(region,[15,9])]=11
                m,_=gfx_ko.line_mask(text,'Galmuri11-Condensed');gfx_ko.draw(img,m,(c['w']-m.shape[1])//2,9,15,9)
            elif parent==8:
                img[:]=0;m,_=gfx_ko.line_mask(text,'Galmuri7');gfx_ko.draw(img,m,0,0,1,7)
            else:
                img[np.isin(img,[1,2])]=4;m,_=gfx_ko.line_mask(text,'Galmuri7');gfx_ko.draw(img,m,(16-m.shape[1])//2,4,1,2)
            rebuilt=mapped_write(raw,img)
            if child_compressed:rebuilt=bpe.encode_literal(rebuilt)
            new=(len(data)+3)&~3 if compressed else alloc(len(rebuilt),4)
            if compressed:data.extend(b'\0'*(new-len(data)));data.extend(rebuilt)
            else:data[new:new+len(rebuilt)]=rebuilt
            struct.pack_into('<I',data,table+4+4*index,len(rebuilt))
            struct.pack_into('<I',data,table+4+4*n+4*index,new-base)
            report.append({'kind':'house_menu','path':[parent,index],'text':text})
        if compressed:gfx_ko.pf_ct_store(rom,master,parent,data,alloc)
    for a in [0x2dc480,0x2dc5c0,0x2dc6e0]:
        c=ctgfx.parse(rom[a:a+32]);raw=bytes(rom[a:a+c['tiles']+c['tsize']]);img,_,_=ctgfx.image(raw)
        img[np.isin(img,[4,7,8,9,10,11])]=6
        for y,text,body,shadow in [(0,'클리어',4,5),(8,'UP',8,9)]:
            m,_=gfx_ko.line_mask(text,'Galmuri7');gfx_ko.draw(img,m,(32-m.shape[1])//2,y,body,shadow)
        rom[a:a+len(raw)]=native_write(raw,img);report.append({'kind':'clear_up_badge','address':a})
    a=0x2db158;c=ctgfx.parse(rom[a:a+32]);raw=bytes(rom[a:a+c['tiles']+c['tsize']]);img,_,_=ctgfx.image(raw)
    img[6:21,5:131]=3;img[23:40,7:129]=6
    m,_=gfx_ko.line_mask('아이템이 가득합니다!','Galmuri11-Condensed');gfx_ko.draw(img,m,(136-m.shape[1])//2,7,1,5)
    for x,y,text in [(16,24,'무기'),(80,24,'방어구'),(16,32,'장신구'),(80,32,'소비품')]:
        m,_=gfx_ko.line_mask(text,'Galmuri7');gfx_ko.draw(img,m,x,y,1,5)
    rom[a:a+len(raw)]=native_write(raw,img);report.append({'kind':'inventory_full','address':a})
    root_shop=0x2dd5a8;a=0x2dd62c;c=ctgfx.parse(rom[a:a+32]);raw=bytes(rom[a:a+c['map']+c['msize']]);img,_,_=ctgfx.image(raw)
    img[96:104,0:74]=5;m,_=gfx_ko.line_mask('남은 능력치','Galmuri7');gfx_ko.draw(img,m,1,96,2,7)
    data=mapped_write(raw,img);new=alloc(len(data),4);rom[new:new+len(data)]=data;struct.pack_into('<I',rom,root_shop+4,new-root_shop)
    report.append({'kind':'shop_panel','address':new})
    # The six effects share letter animations. Rewrite each complete sequence
    # so a reused Japanese syllable cannot impose the wrong Korean meaning.
    effects=[(0x37ed8,[0,4,12],[0,2,255]),(0x37eea,[1,9,12],[1,2,255]),(0x37ef8,[3,7,8],[3,2,255]),(0x37f04,[10,4,12],[4,2,255]),(0x37f16,[4,5,2,6],[5,2,255,255]),(0x37f2c,[1,12,11],[6,7,2])]
    for start,old,new in effects:
        for j,(before,after) in enumerate(zip(old,new)):
            addr=start+4*j
            assert rom[addr:addr+2]==bytes([before,0x20]),hex(addr)
            rom[addr]=after
    an=gfx_ko.tp_entry(rom,14)
    frame_offsets=[0x84,0x11c,0x1b4,0x24c,0x2e4,0x37c,0x414,0x4ac,0x544,0x5dc,0x674,0x70c,0x7a4]
    for i,off in enumerate(frame_offsets):
        img,cells,tiles=gfx_ko.an_frame(rom,an,off);img[:]=0
        if i<8:
            m,_=gfx_ko.line_mask(['퍽','툭','!','휙','헛','챙','획','득'][i],'Galmuri11-Bold')
            canvas=np.zeros_like(img,dtype=bool);x=(16-m.shape[1])//2;canvas[2:2+m.shape[0],x:x+m.shape[1]]=m
            outline=gfx_ko.grow(canvas,1);shadow=np.zeros_like(canvas);shadow[1:,1:]=outline[:-1,:-1]
            img[shadow]=10;img[outline]=11;img[canvas]=7
        gfx_ko.an_commit(rom,img,cells,tiles)
        _,alternate,tiles=gfx_ko.an_frame(rom,an,off+0x34)
        gfx_ko.an_commit(rom,img,alternate,tiles)
    report.append({'kind':'battle_effects','text':['퍽!','툭!','휙!','헛!','챙!','획득!'],'sequence_address':0x37ed8})
    small=[(0x29640c,'SP 필살',11,3,12),(0x2dd368,'특가',13,9,10),(0x2dd428,'저주',13,9,10),(0x2dd4e8,'품절',13,9,10),(0x2ddc94,'START:능력 설정',0,1,2)]
    for a,text,bg,body,shadow in small:
        c=ctgfx.parse(rom[a:a+32]);raw=bytes(rom[a:a+c['tiles']+c['tsize']]);img,_,_=ctgfx.image(raw)
        img[(img==body)|(img==shadow)]=bg
        m,_=gfx_ko.line_mask(text,'Galmuri7');assert m.shape[1]+1<=c['w']
        gfx_ko.draw(img,m,(c['w']-m.shape[1])//2,0,body,shadow)
        rom[a:a+len(raw)]=native_write(raw,img);report.append({'kind':'small_label','text':text,'address':a})
    # Seven shop themes share the same four stat-heading positions and indices.
    for a in [3011352,3017636,3025776,3033212,3040648,3046260,3053152]:
        c=ctgfx.parse(rom[a:a+32]);raw=bytes(rom[a:a+c['tiles']+c['tsize']]);img,_,_=ctgfx.image(raw)
        img[:]=14
        for j,text in enumerate(['AT 공격','SP 필살','DF 방어','AG 민첩']):
            m,_=gfx_ko.line_mask(text,'Galmuri7');assert m.shape[1]+1<=48
            gfx_ko.draw(img,m,48*j,0,1,12)
        rom[a:a+len(raw)]=native_write(raw,img);report.append({'kind':'shop_stats','address':a})
    import mapgfx
    a,_=mapgfx.bg0b(rom)
    for tile,text,body in [(0x28,'크로노아',10),(0x2d,'간츠',7),(0x32,'판고',13)]:
        img=np.full((8,40),3,np.uint8);m,_=gfx_ko.line_mask(text,'Galmuri7')
        gfx_ko.draw(img,m,0,0,body,1)
        for j in range(5):gfx_ko.write_tile(rom,a+0x1b90+32*(tile+j),img[:,8*j:8*j+8])
        report.append({'kind':'map_hud_name','text':text,'tile':tile})
    footers=[(0x29450c,'캐릭터 전환','능력 전환',1,9,8),(0x2948ec,'능력 전환','캐릭터 전환',1,9,8),(0x294ccc,'캐릭터 전환','소지품 정리',14,13,8),(0x2950ac,'소지품 정리','캐릭터 전환',14,13,8),(0x29548c,'능력 설정','소지품 정리',11,13,8),(0x29586c,'소지품 정리','능력 설정',11,13,8)]
    for a,left,right,bg,body,shadow in footers:
        c=ctgfx.parse(rom[a:a+32]);raw=bytes(rom[a:a+c['tiles']+c['tsize']]);img,_,_=ctgfx.image(raw)
        # Preserve the original L/R icons at each edge; redraw both text runs.
        img[:,24:216]=bg
        for text,x in [(left,27),(right,216-gfx_ko.line_mask(right,'Galmuri7')[0].shape[1])]:
            m,_=gfx_ko.line_mask(text,'Galmuri7');gfx_ko.draw(img,m,x,0,body,shadow)
        rom[a:a+len(raw)]=native_write(raw,img)
        report.append({'kind':'footer','address':a,'text':left+' / '+right})
    for a,x0,x1 in [(0x295c4c,28,88),(0x29602c,0,60)]:
        c=ctgfx.parse(rom[a:a+32]);raw=bytes(rom[a:a+c['tiles']+c['tsize']]);img,_,_=ctgfx.image(raw)
        img[:,x0:x1]=14;m,_=gfx_ko.line_mask('캐릭터 전환','Galmuri7');gfx_ko.draw(img,m,x0,0,15,8)
        rom[a:a+len(raw)]=native_write(raw,img);report.append({'kind':'character_footer','address':a})
    # Three sprite pieces compose each 80 x 16 inventory category tab.
    root=0x28fd20
    panels={0:[(144,1,212,8,'중요 아이템',2,3,9),(98,73,164,80,'가진 아이템',2,3,9),(98,81,164,88,'가진 돌',2,3,9),(3,113,56,121,'남은 능력치',2,3,9)],1:[(96,17,158,25,'AT 공격력',11,3,12),(96,89,158,97,'DF 방어력',11,3,12),(96,113,162,121,'AG 민첩성',11,3,12),(3,113,56,121,'남은 능력치',11,3,12)]}
    for index,labels in panels.items():
        a=root+struct.unpack_from('<I',rom,root+4+4*index)[0]
        c=ctgfx.parse(rom[a:a+32]);raw=bytes(rom[a:a+c['map']+c['msize']]);img,_,_=ctgfx.image(raw)
        if index==0:
            # The old first label casts its shadow onto the orange lower border.
            old=img[74:75,98:164];old[old==12]=4
        for x,y,x1,y1,text,bg,body,shadow in labels:
            reg=img[y:y1,x:x1];reg[(reg==body)|(reg==shadow)]=bg
            m,_=gfx_ko.line_mask(text,'Galmuri7');assert m.shape[1]+1<=x1-x
            gfx_ko.draw(img,m,x,y,body,shadow)
        data=mapped_write(raw,img);new=alloc(len(data),4);rom[new:new+len(data)]=data
        struct.pack_into('<I',rom,root+4+4*index,new-root)
        report.append({'kind':'inventory_panel','index':index,'address':new})
    for index,text in [(0x2b,'무기'),(0x2c,'방어구'),(0x2d,'장신구'),(0x2e,'소비 아이템'),(0x2f,'중요 아이템')]:
        sub=root+struct.unpack_from('<I',rom,root+4+index*4)[0]
        parts=[];images=[]
        for j in range(3):
            a=sub+struct.unpack_from('<I',rom,sub+4+4*j)[0]
            c=ctgfx.parse(rom[a:a+32]);raw=bytes(rom[a:a+c['tiles']+c['tsize']]);im,_,_=ctgfx.image(raw)
            parts.append((a,raw,c['w']));images.append(im)
        img=np.concatenate(images,axis=1);img[(img==1)|(img==5)]=3
        m,_=gfx_ko.line_mask(text,'Galmuri11-Condensed')
        assert m.shape[1]+12<=img.shape[1]
        gfx_ko.draw(img,m,(img.shape[1]-m.shape[1])//2,2,1,5)
        x=0
        for a,raw,w in parts: rom[a:a+len(raw)]=native_write(raw,img[:,x:x+w]);x+=w
        report.append({'kind':'inventory_tab','text':text,'index':index})
    for a,text in [(0x2d9b18,'사용'),(0x2d9cb8,'버리기'),(0x2d9e58,'예'),(0x2d9ff8,'아니오'),(0x2da198,'타이틀로'),(0x2da438,'지역 이동'),(0x2da6d8,'비전 지도'),(0x2da978,'히스토리아'),(0x2dac18,'능력 설정'),(0x2daeb8,'저장')]:
        c=ctgfx.parse(rom[a:a+32]);raw=bytes(rom[a:a+c['tiles']+c['tsize']]);img,_,_=ctgfx.image(raw)
        img[(img==1)|(img==5)]=3
        m,_=gfx_ko.line_mask(text,'Galmuri11-Condensed');assert m.shape[1]+12<=c['w']
        gfx_ko.draw(img,m,(c['w']-m.shape[1])//2,2,1,5)
        rom[a:a+len(raw)]=native_write(raw,img)
        report.append({'kind':'menu_button','text':text,'address':a})
    names=[('크로노아',[0x2c76bc,0x2c777c,0x2c781c,0x2c78bc,0x2c791c,0x2c797c]),('간츠',[0x2c79f8,0x2c7ab8,0x2c7b58,0x2c7bf8,0x2c7c58,0x2c7cb8]),('판고',[0x2c7d34,0x2c7df4,0x2c7e94,0x2c7f34,0x2c7f94,0x2c7ff4])]
    for text,addresses in names:
        img=np.zeros((24,48),np.uint8);parts=[]
        for i,a in enumerate(addresses):
            c=ctgfx.parse(rom[a:a+32]);raw=bytes(rom[a:a+c['tiles']+c['tsize']]);q,_,_=ctgfx.image(raw)
            y=0 if i<3 else 16;x=(i%3)*16
            img[y:y+c['h'],x:x+16]=q;parts.append((a,raw,y,x,c['h']))
        img[(img==4)|(img==5)]=6
        m,_=gfx_ko.line_mask(text,'Galmuri11-Condensed')
        gfx_ko.draw(img,m,(48-m.shape[1])//2,6,4,5)
        for a,raw,y,x,h in parts: rom[a:a+len(raw)]=native_write(raw,img[y:y+h,x:x+16])
        report.append({'kind':'hud_name','text':text,'addresses':addresses})
    saves=[(0x2f6c04,'게임 데이터를 저장합니다.'),(0x2f7024,'저장 중입니다.'),(0x2f72c4,'저장했습니다.'),(0x2f76e4,'저장 데이터를 지울까요?'),(0x2f7b84,'진행할까요?'),(0x2f7e24,'저장하지 못했습니다.'),(0x2f8244,'저장 데이터가 손상됐습니다.'),(0x2f8664,'저장 데이터를 지웠습니다.'),(0x2f8b04,'전원을 끄거나'),(0x2f8f24,'카트리지를 빼지'),(0x2f9344,'마세요.')]
    for a,text in saves:
        c=ctgfx.parse(rom[a:a+32]);size=c['tiles']+c['tsize']
        raw=bytes(rom[a:a+size]);img,_,_=ctgfx.image(raw)
        img[:]=7
        m,_=gfx_ko.line_mask(text,'Galmuri11-Condensed')
        assert m.shape[1]+1<=c['w'],(text,m.shape,c['w'])
        gfx_ko.draw(img,m,(c['w']-m.shape[1])//2,2,4,5)
        rom[a:a+size]=native_write(raw,img)
        report.append({'kind':'save','text':text,'address':a})
    root=0x89f0fc
    for i,text in enumerate(SPEAKERS):
        a=root+struct.unpack_from('<I',rom,root+4+4*i)[0]
        raw=bytes(rom[a:a+0x140]);img,_,c=ctgfx.image(raw)
        assert img.shape==(16,32)
        img[:]=0
        m,_=gfx_ko.line_mask(text,'Galmuri11-Condensed')
        assert m.shape[1]<=32,(i,text,m.shape)
        gfx_ko.draw(img,m,0,1,1,2)
        rom[a:a+len(raw)]=native_write(raw,img)
        report.append({'kind':'speaker','id':i,'text':text,'address':a})
    root=0x8a398c
    for i,text in enumerate(AREAS):
        a=root+struct.unpack_from('<I',rom,root+4+4*i)[0]
        raw=bpe.decode(rom[a:a+struct.unpack_from('<I',rom,a)[0]])
        idx,_,c=ctgfx.image(raw)
        img=np.concatenate([idx[j*24:(j+1)*24] for j in range(3)],axis=1)
        # Interior blue is palette 1; retain all original bevel pixels.
        img[4:20,4:92]=1
        m,_=gfx_ko.line_mask(text,'Galmuri11-Condensed')
        assert m.shape[1]<=88,(i,text,m.shape)
        gfx_ko.draw(img,m,(96-m.shape[1])//2,6,9,2)
        packed=np.concatenate([img[:,j*32:(j+1)*32] for j in range(3)],axis=0)
        data=bpe.encode_literal(native_write(raw,packed));new=alloc(len(data),4)
        rom[new:new+len(data)]=data;struct.pack_into('<I',rom,root+4+4*i,new-root)
        report.append({'kind':'area','id':i,'text':text,'address':new})
    return report
