"""Offline two-glyph FONT experiment, retaining the 512x256 A8 atlas."""
import json
from pathlib import Path
import struct
from PIL import Image,ImageFont,ImageDraw
from refpack_compact import compress_compact
from refpack import compress,decompress


def build(inf,atlas_bytes,ttf):
    count=struct.unpack_from('>H',inf,10)[0];start=struct.unpack_from('>I',inf,12)[0]
    if inf[:4]!=b'FONT' or count!=194 or start!=0x454 or len(atlas_bytes)!=512*256:
        raise ValueError('Unexpected original font')
    original=[inf[start+i*24:start+(i+1)*24] for i in range(count)]
    rects=[tuple(v//16 for v in struct.unpack('>HHHhh4HI',r[2:])[5:9]) for r in original]
    atlas=Image.frombytes('L',(512,256),atlas_bytes);draw=ImageDraw.Draw(atlas)
    face=ImageFont.truetype(str(ttf),24);face.set_variation_by_axes([500])
    records=list(original)
    for char,x,y in [('选',32,224),('项',64,224)]:
        box=face.getbbox(char);w,h=box[2]-box[0],box[3]-box[1]
        if w>26 or h>26:raise ValueError('Glyph exceeds reserved blank area')
        if any(x<x1 and x+w>x0 and y<y1 and y+h>y0 for x0,y0,x1,y1 in rects):raise ValueError('Glyph overlaps original atlas')
        draw.text((x-box[0],y-box[1]),char,font=face,fill=255)
        records.append(ord(char).to_bytes(2,'little')+struct.pack('>HHHhh4HI',w,h,26,0,33-h,x*16,y*16,(x+w)*16,(y+h)*16,0))
    header=bytearray(inf[:start]);end=start+len(records)*24
    struct.pack_into('>H',header,10,len(records));struct.pack_into('>I',header,64,end)
    header[0x44:0x444]=bytes(1024)
    pages=sorted({int.from_bytes(r[:2],'little')>>8 for r in records})
    for i,page in enumerate(pages):struct.pack_into('>I',header,0x44+page*4,4+i*1024)
    result=header+b''.join(records)+bytes(4+len(pages)*1024);struct.pack_into('>I',result,4,len(result))
    assert result[start:start+count*24]==inf[start:start+count*24]
    # Original pixels are preserved outside the two reserved rectangles.
    changed=atlas.tobytes()
    allowed={(y+dy)*512+x+dx for x,y in [(32,224),(64,224)] for dy in range(26) for dx in range(26)}
    assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(atlas_bytes,changed)))
    return bytes(result),changed,atlas


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--font',type=Path,required=True);p.add_argument('--atlas',type=Path,required=True)
    p.add_argument('--ttf',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    inf,dat,atlas=build(args.font.read_bytes(),args.atlas.read_bytes(),args.ttf)
    for name,data in [('font.inf',inf),('font.a8',dat)]: (args.output/name).write_bytes(data)
    atlas.save(args.output/'preview.png')
    (args.output/'font.refpack').write_bytes(compress_compact(inf,max_chain=4096))
    compressed=compress_compact(dat);(args.output/'texture.refpack').write_bytes(compressed)
    print(json.dumps(dict(font_size=len(inf),font_compressed=(args.output/'font.refpack').stat().st_size,texture_compressed=len(compressed),texture_capacity=39228)))
