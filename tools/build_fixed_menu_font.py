"""Repack all original codepoints plus selected menu glyphs into 512x256 A8.

This changes raster design: 12px bitmap glyphs are mapped to doubled FONT
metrics, with four alpha levels. Hardware must confirm scale and legibility.
"""
import argparse,csv,json,struct,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
from refpack import compress
from text_tokens import TOKENS


def build(original_font,ttf,translations):
    if original_font[:4]!=b'FONT' or struct.unpack_from('>H',original_font,8)[0]!=7:raise ValueError('Unexpected font')
    start=struct.unpack_from('>I',original_font,12)[0];count=struct.unpack_from('>H',original_font,10)[0]
    if start!=0x454 or count!=194:raise ValueError('Unexpected original glyph layout')
    codepoints={int.from_bytes(original_font[start+i*24:start+i*24+2],'little') for i in range(count)}
    for text in translations:codepoints.update(ord(c) for c in TOKENS.sub('',text))
    if len(codepoints)>624:raise ValueError('Fixed 512x256 atlas capacity exceeded')
    cmap=TTFont(ttf).getBestCmap()
    if codepoints-set(cmap):raise ValueError('Source font lacks required characters')
    face=ImageFont.truetype(str(ttf),12);face.set_variation_by_axes([500])
    img=Image.new('L',(512,256));records=[]
    for i,cp in enumerate(sorted(codepoints)):
        x=(i%39)*13;y=(i//39)*16;char=chr(cp);box=face.getbbox(char)
        width,height=box[2]-box[0],box[3]-box[1]
        if height>15 or y+height>256:raise ValueError('Glyph exceeds fixed cell')
        tile=Image.new('L',(max(width,1),max(height,1)))
        ImageDraw.Draw(tile).text((-box[0],-box[1]),char,font=face,fill=255)
        if width>12:tile=tile.resize((12,max(height,1)));width=12
        img.paste(tile,(x,y))
        advance=int(round(face.getlength(char)*2))+1
        records.append(cp.to_bytes(2,'little')+struct.pack('>HHHhh4HI',width*2,height*2,advance,0,33-height*2,x*16,y*16,(x+width)*16,(y+height)*16,0))
    head=bytearray(original_font[:start]);end=start+len(records)*24
    struct.pack_into('>H',head,10,len(records));struct.pack_into('>I',head,64,end)
    head[0x44:0x444]=bytes(1024);pages=sorted({cp>>8 for cp in codepoints})
    for i,page in enumerate(pages):struct.pack_into('>I',head,0x44+page*4,4+i*1024)
    inf=head+b''.join(records)+bytes(4+len(pages)*1024);struct.pack_into('>I',inf,4,len(inf))
    atlas=bytes(round(v/85)*85 for v in img.tobytes())
    a,b=compress(bytes(inf)),compress(atlas)
    if len(a)>9860 or len(b)>39228:raise ValueError('Compressed assets exceed original frontend slots')
    return bytes(inf),atlas,a,b,dict(glyphs=len(codepoints),font_compressed=len(a),texture_compressed=len(b),atlas=[512,256],bitmap_pixels=12,geometry_scale=2,alpha_levels=4)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('original_inf',type=Path);p.add_argument('ttf',type=Path);p.add_argument('translations',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    with a.translations.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    a.output.mkdir(exist_ok=False);inf,atlas,ci,ca,report=build(a.original_inf.read_bytes(),a.ttf,[r['translation'] for r in rows])
    for name,data in [('font.refpack',ci),('texture.refpack',ca)]:(a.output/name).write_bytes(data)
    Image.frombytes('L',(512,256),atlas).save(a.output/'preview.png')
    (a.output/'font-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
