"""Build capacity-ranked dual-font assets and explicit non-subtitle coverage."""
import csv,json,struct,hashlib,sys
from collections import Counter
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from refpack import compress,decompress
from text_tokens import TOKENS,validate
from build_icon_cjk_probe import decode_texture,white_bc3_block,EXPECTED_FONT,EXPECTED_TEXTURE
from build_dense_menu_font import selected_rows
from dual_text import DualEncoder


def codepoints(inf):return {int.from_bytes(inf[0x454+i*24:0x456+i*24],'little') for i in range(struct.unpack_from('>H',inf,10)[0])}
def needed(row):return set(map(ord,TOKENS.sub('',row['translation'])))

def choose_extra(rows,normal,limit):
    extra=[];covered=set(normal)
    while len(extra)<limit:
        candidates=[r for r in rows if needed(r)-covered and len(needed(r)-covered)<=limit-len(extra)]
        if not candidates:break
        frequency=Counter(cp for r in candidates for cp in needed(r)-covered)
        row=min(candidates,key=lambda r:(len(needed(r)-covered),-sum(frequency[c] for c in needed(r)-covered),len(r['source']),r['id']))
        chars=sorted(needed(row)-covered,key=lambda c:(-frequency[c],c));extra.extend(chars);covered.update(chars)
    return extra

def supplemental(font,texture,ttf,chars):
    if hashlib.sha256(font).hexdigest()!=EXPECTED_FONT or hashlib.sha256(texture).hexdigest()!=EXPECTED_TEXTURE:raise ValueError('Original icon samples differ')
    image=decode_texture(texture);alpha=image.getchannel('A');rects=[tuple(v//16 for v in struct.unpack_from('>4H',font,0x454+i*24+12)) for i in range(38)];cells=[]
    for y in range(0,241,4):
        for x in range(0,497,4):
            if any(x<b and x+16>a and y<d and y+16>c for a,c,b,d in rects):continue
            if any(x<xx+16 and x+16>xx and y<yy+16 and y+16>yy for xx,yy in cells):continue
            if alpha.crop((x,y,x+16,y+16)).getbbox() is not None:continue
            cells.append((x,y))
    if len(chars)>len(cells):raise ValueError('Supplemental glyphs exceed safe blank cells')
    face=ImageFont.truetype(str(ttf),12);face.set_variation_by_axes([500]);data=bytearray(texture);records=[]
    for i,(cp,(x,y)) in enumerate(zip(chars,cells)):
        box=face.getbbox(chr(cp));w,h=box[2]-box[0],box[3]-box[1];tile=Image.new('L',(max(w,1),max(h,1)));ImageDraw.Draw(tile).text((-box[0],-box[1]),chr(cp),font=face,fill=255)
        if w>12:tile=tile.resize((12,max(h,1)));w=12
        if h>15:raise ValueError('Supplemental glyph too tall')
        cell=Image.new('L',(16,16));cell.paste(tile,(1,0));cell=cell.point(lambda v:round(v/85)*85)
        for by in range(0,16,4):
            for bx in range(0,16,4):
                at=(((y+by)//4)*128+(x+bx)//4)*16;values=[cell.getpixel((bx+dx,by+dy)) for dy in range(4) for dx in range(4)];data[at:at+16]=white_bc3_block(values)
        records.append((38+i).to_bytes(2,'little')+struct.pack('>HHHhh4HI',w*2,h*2,int(round(face.getlength(chr(cp))*2))+1,0,33-h*2,(x+1)*16,y*16,(x+1+w)*16,(y+h)*16,0))
    end=0x454+38*24;head=bytearray(font[:0x454]);struct.pack_into('>H',head,10,38+len(chars));struct.pack_into('>I',head,64,end+len(records)*24)
    inf=head+font[0x454:end]+b''.join(records)+font[end:];struct.pack_into('>I',inf,4,len(inf));out=decode_texture(data)
    for a,c,b,d in rects:
        if image.crop((a,c,b,d)).tobytes()!=out.crop((a,c,b,d)).tobytes():raise ValueError('Original icon pixels changed')
    assert inf[0x454:end]==font[0x454:end]
    return bytes(inf),bytes(data),cells[:len(chars)]

def coverage(rows,core,normal,icons):
    encoder=DualEncoder(normal,icons);eligible=[];deferred=[]
    for row in rows:
        if needed(row)<=normal|set(icons):
            encoder.validate_row(row);eligible.append(row)
        else:deferred.append(dict(id=row['id'],reason='glyph_missing'))
    # Work within the observed 116272-byte original 2HCL and 131072-byte entry.
    # Mandatory F1/menu-controls rows are retained; add other eligible rows
    # in order of UTF-8 delta so extra icon markup cannot overrun the entry.
    accepted=[r for r in eligible if r['id'] in core]
    size=116272+sum(len(encoder.encode(r['translation']).encode())-len(r['source'].encode()) for r in accepted)
    if size>130924:raise ValueError('Mandatory menu/control table exceeds entry')
    for row in sorted((r for r in eligible if r['id'] not in core),key=lambda r:(len(encoder.encode(r['translation']).encode())-len(r['source'].encode()),r['id'])):
        delta=len(encoder.encode(row['translation']).encode())-len(row['source'].encode())
        if size+delta>130924:deferred.append(dict(id=row['id'],reason='table_capacity'));continue
        accepted.append(row);size+=delta
    return sorted(accepted,key=lambda r:r['id']),deferred,size

def build(root,sample,primary,ttf,output):
    output.mkdir(exist_ok=False);normal_inf=decompress((primary/'font.refpack').read_bytes());normal=codepoints(normal_inf)
    with (root/'translations/global.zh-CN.nonstory.csv').open(encoding='utf-8-sig',newline='') as f:allrows={r['id']:r for r in csv.DictReader(f)}
    core_rows=selected_rows(root);core={r['id'] for r in core_rows};allrows.update({r['id']:r for r in core_rows});rows=list(allrows.values())
    extra=choose_extra(rows,normal,62);font=(sample/'buttons.inf').read_bytes();texture=(sample/'buttons.tg4d').read_bytes();variants=[]
    for size in (0,2,8,16,32,48,62):
        chars=extra[:size];name=f'{len(chars):02d}';folder=output/name;folder.mkdir()
        inf,data,cells=supplemental(font,texture,ttf,chars);ci,ct=compress(inf),compress(data)
        if size:
            (folder/'buttons-font.refpack').write_bytes(ci);(folder/'buttons-texture.refpack').write_bytes(ct)
        mapping={cp:38+i for i,cp in enumerate(chars)};accepted,deferred,table_size=coverage(rows,core,normal,mapping)
        with (folder/'translations.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['id','source','translation','status']);w.writeheader();w.writerows(accepted)
        plan=dict(name=name,normal_codepoints=sorted(normal),icon_map={str(k):v for k,v in mapping.items()},translated_ids_per_table=len(accepted),deferred=deferred,estimated_2hcl_size=table_size,supplemental_glyphs=len(chars),font_compressed=len(ci) if size else 0,texture_compressed=len(ct) if size else 0,cells=cells)
        (folder/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2));variants.append({k:plan[k] for k in ['name','translated_ids_per_table','estimated_2hcl_size','supplemental_glyphs','font_compressed','texture_compressed']});print(variants[-1],flush=True)
    for name in ('font.refpack','texture.refpack','font-report.json'):(output/name).write_bytes((primary/name).read_bytes())
    (output/'variants.json').write_text(json.dumps(dict(target_ids=len(rows),normal_glyphs=len(normal),variants=variants),indent=2))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('sample',type=Path);p.add_argument('primary',type=Path);p.add_argument('ttf',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(Path(__file__).resolve().parents[1],a.sample,a.primary,a.ttf,a.output)
