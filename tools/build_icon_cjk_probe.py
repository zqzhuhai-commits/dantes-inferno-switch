"""Offline G1: append two numeric CJK glyphs to original buttons FONT.

Retains original glyph records, texture dimensions/header and every BC3 block
outside two previously transparent, block-aligned regions. Pillow is build-only.
"""
import hashlib,io,json,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from refpack import compress,decompress

EXPECTED_FONT='d9a0596e1135c48e11bc3bc8193201d6821304af43ce4fcc1b1cd35ffbcd79d1'
EXPECTED_TEXTURE='729d5775dfc69f4d748f88f6b2d09e8dc7768e58bf42a1b8865796cb58e9f6ec'

def swap16(data):
    if len(data)%2:raise ValueError('Odd texture byte count')
    out=bytearray(data);out[::2]=data[1::2];out[1::2]=data[::2];return bytes(out)

def decode_texture(data):
    if len(data)!=131072:raise ValueError('Expected 512x256 BC3')
    header=b'DDS '+struct.pack('<7I',124,0x81007,256,512,len(data),0,0)+bytes(44)
    header+=struct.pack('<II4s5I',32,4,b'DXT5',0,0,0,0,0)+struct.pack('<5I',0x1000,0,0,0,0)
    return Image.open(io.BytesIO(header+swap16(data))).convert('RGBA')

def white_bc3_block(alpha):
    if len(alpha)!=16:raise ValueError('Expected 4x4 alpha')
    palette=[255,0]+[((7-i)*255)//7 for i in range(1,7)]
    bits=0
    for i,value in enumerate(alpha):bits|=min(range(8),key=lambda k:abs(value-palette[k]))<<(3*i)
    # Constant white color; interpolate alpha using the normal BC3 palette.
    return swap16(bytes([255,0])+bits.to_bytes(6,'little')+struct.pack('<HHI',0xffff,0xffff,0))

def build(font,texture,ttf):
    if hashlib.sha256(font).hexdigest()!=EXPECTED_FONT or hashlib.sha256(texture).hexdigest()!=EXPECTED_TEXTURE:raise ValueError('Original buttons assets differ')
    if font[:4]!=b'FONT' or struct.unpack_from('>HHI',font,8)!=(7,38,0x454):raise ValueError('Unexpected buttons FONT')
    start=0x454;end=start+38*24
    if struct.unpack_from('>I',font,64)[0]!=end or len(font[end:])!=1028 or any(font[end:]):raise ValueError('Unexpected lookup storage')
    original=decode_texture(texture);alpha=original.getchannel('A');positions=[]
    rects=[tuple(v//16 for v in struct.unpack_from('>4H',font,start+i*24+12)) for i in range(38)]
    for y in range(0,229,4):
        for x in range(304,485,4):
            if alpha.crop((x,y,x+28,y+28)).getbbox() is not None:continue
            if any(x<x1 and x+28>x0 and y<y1 and y+28>y0 for x0,y0,x1,y1 in rects):continue
            if any(x<xx+28 and x+28>xx and y<yy+28 and y+28>yy for xx,yy in positions):continue
            positions.append((x,y))
            if len(positions)==2:break
        if len(positions)==2:break
    if len(positions)!=2:raise ValueError('No two safe blank texture cells')
    face=ImageFont.truetype(str(ttf),24)
    if hasattr(face,'set_variation_by_axes'):face.set_variation_by_axes([500])
    out=bytearray(texture);records=[];allowed=set()
    for cp,char,(x,y) in zip((38,39),'中文',positions):
        tile=Image.new('L',(28,28));box=face.getbbox(char);w,h=box[2]-box[0],box[3]-box[1]
        if w>24 or h>24:raise ValueError('CJK bitmap exceeds 24px cell')
        ImageDraw.Draw(tile).text((2-box[0]+(24-w)//2,2-box[1]+(24-h)//2),char,font=face,fill=255)
        for by in range(0,28,4):
            for bx in range(0,28,4):
                at=(((y+by)//4)*128+(x+bx)//4)*16
                block=[tile.getpixel((bx+dx,by+dy)) for dy in range(4) for dx in range(4)]
                out[at:at+16]=white_bc3_block(block);allowed.update(range(at,at+16))
        # Use existing square-button geometry for this diagnostic. This is a
        # probe of the icon path; text metrics/line breaking are not yet solved.
        records.append(cp.to_bytes(2,'little')+struct.pack('>HHHhh4HI',41,41,43,2,5,(x+2)*16,(y+2)*16,(x+26)*16,(y+26)*16,0))
    head=bytearray(font[:start]);struct.pack_into('>H',head,10,40);struct.pack_into('>I',head,64,end+48)
    newfont=head+font[start:end]+b''.join(records)+font[end:];struct.pack_into('>I',newfont,4,len(newfont))
    if newfont[start:end]!=font[start:end]:raise ValueError('Original glyph records changed')
    if any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(texture,out))):raise ValueError('Texture changed outside cells')
    preview=decode_texture(out)
    for i in range(38):
        x0,y0,x1,y1=rects[i]
        if original.crop((x0,y0,x1,y1)).tobytes()!=preview.crop((x0,y0,x1,y1)).tobytes():raise ValueError('Existing icon pixels changed')
    report=dict(glyphs_before=38,glyphs_after=40,added_numeric_ids=[38,39],test_text='中文',atlas=[512,256],format='DXT5/BC3, 16-bit byte swapped',cells=positions,original_glyph_records_preserved=True,original_icon_pixels_preserved=True,texture_header_unchanged=True,font_decoded_delta=48,geometry='existing square-button 41x41, advance 43; hardware size pending')
    return bytes(newfont),bytes(out),preview,report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('sample_directory',type=Path);p.add_argument('ttf',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False)
    inf,dat,img,report=build((a.sample_directory/'buttons.inf').read_bytes(),(a.sample_directory/'buttons.tg4d').read_bytes(),a.ttf)
    for name,data in [('buttons-font.refpack',compress(inf)),('buttons-texture.refpack',compress(dat))]:
        (a.output/name).write_bytes(data);report[name+'_size']=len(data)
    (a.output/'font-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));img.save(a.output/'preview-private.png')
    print(json.dumps(report,ensure_ascii=False))
