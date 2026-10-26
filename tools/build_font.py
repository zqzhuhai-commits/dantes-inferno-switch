"""Build Dante's v7 FONT and linear A8 atlas while retaining original glyphs."""
import argparse
import csv
import json
from pathlib import Path
import struct
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont


def build(font_data, atlas_data, texture_header, ttf, characters):
    if font_data[:4] != b'FONT' or struct.unpack_from('>H',font_data,8)[0] != 7:
        raise ValueError('Unsupported FONT')
    count = struct.unpack_from('>H',font_data,10)[0]
    start = struct.unpack_from('>I',font_data,12)[0]
    if start != 0x454 or struct.unpack_from('>I',font_data,64)[0] != start+count*24:
        raise ValueError('Unexpected FONT record layout')
    width,height = struct.unpack_from('>HH',texture_header,32)
    if (width,height) != (512,256) or len(atlas_data) != width*height:
        raise ValueError('Expected original 512x256 linear A8 texture')
    if struct.unpack_from('>I',texture_header,24)[0] != 89:
        raise ValueError('Expected A8 texture format')
    records = [font_data[start+i*24:start+(i+1)*24] for i in range(count)]
    existing = {int.from_bytes(r[:2],'little') for r in records}
    needed = sorted(set(map(ord,characters))-existing)
    if any(cp>65535 or cp<32 for cp in needed):
        raise ValueError('Only BMP printable additions supported')
    face = TTFont(ttf); cmap=face.getBestCmap()
    if any(cp not in cmap for cp in needed):
        raise ValueError('Source font lacks required characters')
    cell=28;columns=width//cell
    newheight=height
    while newheight < height+((len(needed)+columns-1)//columns)*cell:
        newheight*=2
    if newheight>2048 or count+len(needed)>65535:
        raise ValueError('Font capacity exceeded')
    atlas=Image.new('L',(width,newheight));atlas.paste(Image.frombytes('L',(width,height),atlas_data),(0,0))
    draw=ImageDraw.Draw(atlas);font=ImageFont.truetype(str(ttf),24)
    if hasattr(font,'set_variation_by_axes'):font.set_variation_by_axes([500])
    for i,cp in enumerate(needed):
        x=(i%columns)*cell+2;y=height+(i//columns)*cell+2
        char=chr(cp);box=font.getbbox(char)
        # Draw each CJK glyph into a 24px cell, baseline consistent with the
        # original font's 33px baseline. Original metrics and pixels untouched.
        draw.text((x-box[0],y-box[1]),char,font=font,fill=255)
        w,h=box[2]-box[0],box[3]-box[1]
        if w>26 or h>26:raise ValueError(f'Glyph exceeds cell: {char} {w}x{h}')
        records.append(cp.to_bytes(2,'little')+struct.pack('>HHHhh4HI',w,h,26,0,33-h,x*16,y*16,(x+w)*16,(y+h)*16,0))
    header=bytearray(font_data[:start]);newcount=len(records);glyphend=start+24*newcount
    struct.pack_into('>H',header,10,newcount);struct.pack_into('>I',header,64,glyphend)
    pages=sorted({int.from_bytes(r[:2],'little')>>8 for r in records})
    header[0x44:0x444]=bytes(1024)
    for i,page in enumerate(pages):struct.pack_into('>I',header,0x44+page*4,4+i*1024)
    lookup=bytes(4+1024*len(pages))
    result=header+b''.join(records)+lookup
    struct.pack_into('>I',result,4,len(result))
    tg4h=bytearray(texture_header);struct.pack_into('>I',tg4h,28,width*newheight)
    struct.pack_into('>HH',tg4h,32,width,newheight)
    return bytes(result),atlas.tobytes(),bytes(tg4h),atlas,dict(original=count,added=len(needed),glyphs=newcount,atlas=[width,newheight],codepoints=needed)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--font',type=Path,required=True);p.add_argument('--translations',type=Path,nargs='+',required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    x=args.source.read_bytes()
    # Offsets pinned to the verified frontend_global.str sample.
    from refpack import decompress
    size=struct.unpack_from('>I',x,0xd06ed4+12)[0]
    texture=decompress(x[0xd06ed4+16:0xd06ed4+16+size])
    chars=set()
    for table in args.translations:
        with table.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                from text_tokens import TOKENS
                chars.update(TOKENS.sub('',row['translation']))
    result=build(x[0x16c78f4:0x16c78f4+0x2688],texture,x[0xd06e14:0xd06e78],args.font,chars)
    inf,dat,hdr,atlas,report=result
    for name,data in [('minion_pro.inf',inf),('minion_pro.tg4d',dat),('minion_pro.tg4h',hdr)]:
        (args.output/name).write_bytes(data)
    atlas.save(args.output/'font-preview.png')
    (args.output/'font-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='codepoints'}))


if __name__=='__main__':main()
