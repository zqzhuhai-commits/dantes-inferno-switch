"""Keep F1's 12px/four-alpha rendering, remove fixed-cell packing waste."""
import csv,hashlib,json,struct,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
from text_tokens import TOKENS,validate
from refpack import compress,decompress


def selected_rows(root):
    with (root/'translations/global.zh-CN.fixed-menu.csv').open(encoding='utf-8-sig',newline='') as f:rows={r['id']:r for r in csv.DictReader(f)}
    with (root/'translations/global.zh-CN.nonstory.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            if '[b=' in row['source'] and row['id'] not in rows:rows[row['id']]=row
    for row in rows.values():validate(row['source'],row['translation'])
    return sorted(rows.values(),key=lambda r:r['id'])

def build(original_font,ttf,texts):
    if original_font[:4]!=b'FONT' or struct.unpack_from('>HHI',original_font,8)!=(7,194,0x454):raise ValueError('Unexpected original minion FONT')
    cps={int.from_bytes(original_font[0x454+i*24:0x456+i*24],'little') for i in range(194)}
    for t in texts:cps.update(map(ord,TOKENS.sub('',t)))
    if any(cp<32 or cp>65535 for cp in cps):raise ValueError('Unsupported codepoint')
    if cps-set(TTFont(ttf).getBestCmap()):raise ValueError('Missing source glyph')
    face=ImageFont.truetype(str(ttf),12);face.set_variation_by_axes([500]);tiles={}
    for cp in sorted(cps):
        box=face.getbbox(chr(cp));w,h=box[2]-box[0],box[3]-box[1]
        tile=Image.new('L',(max(w,1),max(h,1)));ImageDraw.Draw(tile).text((-box[0],-box[1]),chr(cp),font=face,fill=255)
        if w>12:tile=tile.resize((12,max(h,1)));w=12
        if h>15:raise ValueError('Glyph exceeds F1 height')
        tiles[cp]=(tile,w,h)
    # Height-sorted first-fit shelves, one transparent pixel between glyphs.
    shelves=[];positions={}
    for cp,(tile,w,h) in sorted(tiles.items(),key=lambda kv:(-max(kv[1][2],1),-max(kv[1][1],1),kv[0])):
        cw,ch=max(w,1)+1,max(h,1)+1
        row=next((r for r in shelves if r['height']>=ch and r['x']+cw<=512),None)
        if row is None:
            y=sum(r['height'] for r in shelves)
            if y+ch>256:raise ValueError(f'Atlas full after {len(positions)}/{len(cps)} glyphs')
            row=dict(x=0,y=y,height=ch);shelves.append(row)
        positions[cp]=(row['x'],row['y']);row['x']+=cw
    img=Image.new('L',(512,256));records=[]
    for cp in sorted(cps):
        tile,w,h=tiles[cp];x,y=positions[cp];img.paste(tile,(x,y));advance=int(round(face.getlength(chr(cp))*2))+1
        records.append(cp.to_bytes(2,'little')+struct.pack('>HHHhh4HI',w*2,h*2,advance,0,33-h*2,x*16,y*16,(x+w)*16,(y+h)*16,0))
    head=bytearray(original_font[:0x454]);end=0x454+len(records)*24
    struct.pack_into('>H',head,10,len(records));struct.pack_into('>I',head,64,end);head[0x44:0x444]=bytes(1024)
    pages=sorted({cp>>8 for cp in cps})
    for i,page in enumerate(pages):struct.pack_into('>I',head,0x44+page*4,4+i*1024)
    inf=head+b''.join(records)+bytes(4+len(pages)*1024);struct.pack_into('>I',inf,4,len(inf))
    atlas=bytes(round(v/85)*85 for v in img.tobytes());ci,ca=compress(bytes(inf)),compress(atlas)
    report=dict(glyphs=len(cps),font_decoded_size=len(inf),font_compressed=len(ci),texture_compressed=len(ca),font_slot_capacity=9860,texture_slot_capacity=39228,atlas=[512,256],bitmap_pixels=12,geometry_scale=2,alpha_levels=4,used_height=sum(r['height'] for r in shelves))
    if len(ci)>9860 or len(ca)>39228:raise ValueError('Compressed assets exceed verified frontend capacities: '+str(report))
    return bytes(inf),atlas,ci,ca,report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('original_font',type=Path);p.add_argument('ttf',type=Path);p.add_argument('output',type=Path);a=p.parse_args();rows=selected_rows(Path(__file__).resolve().parents[1]);a.output.mkdir(exist_ok=False)
    inf,atlas,ci,ca,report=build(a.original_font.read_bytes(),a.ttf,[r['translation'] for r in rows]);report['translated_ids_per_table']=len(rows)
    for n,d in [('font.refpack',ci),('texture.refpack',ca)]:(a.output/n).write_bytes(d)
    with (a.output/'global.zh-CN.menu-controls.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['id','source','translation','status']);w.writeheader();w.writerows(rows)
    Image.frombytes('L',(512,256),atlas).save(a.output/'preview.png');(a.output/'font-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
