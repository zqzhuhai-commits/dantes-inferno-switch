import hashlib,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import icon_cjk_probe as runtime
from build_icon_cjk_probe import white_bc3_block,decode_texture,swap16
from refpack import compress
from str_stream import chunks,unpack_selected,BLOCK

def synthetic_assets(capacity=60000):
    font=bytearray(3048);font[:4]=b'FONT';struct.pack_into('>IHHI',font,4,3048,7,38,0x454);struct.pack_into('>I',font,64,2020)
    for i in range(38):font[0x454+i*24:0x456+i*24]=i.to_bytes(2,'little')
    new=bytearray(font[:2020]+(38).to_bytes(2,'little')+bytes(22)+(39).to_bytes(2,'little')+bytes(22)+font[2020:]);struct.pack_into('>IHH',new,4,3096,7,40);struct.pack_into('>I',new,64,2068)
    texture=bytes(131072);out=bytearray(bytes.fromhex('6f6c73330000000c00020401'))
    for ext,raw,cap in [('inf',bytes(font),1000),('tg4d',texture,capacity)]:
        path=runtime.PATH+ext;head=bytearray(b'SHOC'+bytes(4)+b'SHDR'+bytes(28)+struct.pack('>I',len(raw))+b'buttons\0'+path.encode()+b'\0');head+=bytes(-len(head)%4);struct.pack_into('>I',head,4,len(head));blob=compress(raw)
        out+=head+struct.pack('>4sI4sI',b'SHOC',cap+16,b'Rpak',len(blob))+blob+bytes(cap-len(blob))
    out+=struct.pack('>4sI',b'FILL',BLOCK-len(out))+bytes(BLOCK-len(out)-8)
    return bytes(out),bytes(font),bytes(new),texture

class IconCjkTests(unittest.TestCase):
    def test_bc3_alpha_and_white_color_with_word_endianness(self):
        values=[0,255,36,72,109,145,182,218]*2;block=white_bc3_block(values)
        data=block+bytes(131072-16);im=decode_texture(data)
        for i,a in enumerate(values):
            rgba=im.getpixel((i%4,i//4));self.assertEqual(rgba[:3],(255,255,255));self.assertLessEqual(abs(rgba[3]-a),1)
        self.assertEqual(swap16(swap16(data)),data)
    def test_in_place_font_expansion_and_capacity_guard(self):
        data,old,new,texture=synthetic_assets();compressed={runtime.PATH+'inf':compress(new),runtime.PATH+'tg4d':compress(texture)}
        with patch.object(runtime,'FONT_SHA',hashlib.sha256(old).hexdigest()),patch.object(runtime,'TEXTURE_SHA',hashlib.sha256(texture).hexdigest()):
            result,caps=runtime.patch_icon_stream(data,compressed)
            self.assertEqual([(a,len(c)) for a,c in chunks(data)],[(a,len(c)) for a,c in chunks(result)])
            self.assertEqual(unpack_selected(result,{runtime.PATH+'inf'})[runtime.PATH+'inf'],new)
            bad=dict(compressed);bad[runtime.PATH+'tg4d']=b'x'*60001
            with self.assertRaisesRegex(ValueError,'60000'):runtime.patch_icon_stream(data,bad)
    def test_toc_only_updates_root_decoded_length(self):
        data=bytearray(64);data[:4]=bytes.fromhex('9cba7b28');struct.pack_into('>II',data,16,48,1234)
        out=runtime.adjust_probe_toc(data);self.assertEqual(struct.unpack_from('>I',out,20)[0],1282);self.assertEqual(data[:20],out[:20]);self.assertEqual(data[24:],out[24:])

if __name__=='__main__':unittest.main()
