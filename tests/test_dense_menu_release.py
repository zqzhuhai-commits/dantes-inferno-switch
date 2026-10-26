import csv,hashlib,io,json,struct,sys,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from refpack import decompress
from text_tokens import validate,TOKENS

def unpack_glyphs(inf,atlas):
    out={};rects=[]
    for i in range(struct.unpack_from('>H',inf,10)[0]):
        at=0x454+i*24;cp=int.from_bytes(inf[at:at+2],'little');r=struct.unpack_from('>HHHhh4HI',inf,at+2);x0,y0,x1,y1=[v//16 for v in r[5:9]]
        if not (0<=x0<=x1<=512 and 0<=y0<=y1<=256):raise ValueError('UV outside atlas')
        pixels=b''.join(atlas[y*512+x0:y*512+x1] for y in range(y0,y1));out[cp]=(r[:5]+r[9:],pixels)
        if x0<x1 and y0<y1:rects.append((x0,y0,x1,y1))
    return out,rects

class DenseMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.z=zipfile.ZipFile(ROOT/'checkpoints/Dante-F2-Menu-Controls-v0.6.2.zip');cls.prefix='Dante-F2-Menu-Controls-v0.6.2/'
        cls.inf=decompress(cls.z.read(cls.prefix+'font/font.refpack'));cls.atlas=decompress(cls.z.read(cls.prefix+'font/texture.refpack'))
    @classmethod
    def tearDownClass(cls):cls.z.close()
    def test_f1_all_existing_metrics_and_bitmaps_retained(self):
        with zipfile.ZipFile(ROOT/'checkpoints/Dante-F1-Menu-Fix-v0.6.1.zip') as z:
            p='Dante-F1-Menu-Fix-v0.6.1/font/';old,rects=unpack_glyphs(decompress(z.read(p+'font.refpack')),decompress(z.read(p+'texture.refpack')))
        new,rects=unpack_glyphs(self.inf,self.atlas)
        self.assertEqual(len(old),612);self.assertEqual(len(new),739)
        for cp,values in old.items():self.assertEqual(new[cp],values,hex(cp))
    def test_no_overlap_and_actual_capacities(self):
        glyphs,rects=unpack_glyphs(self.inf,self.atlas)
        for i,(x0,y0,x1,y1) in enumerate(rects):
            self.assertFalse(any(x0<b and x1>a and y0<d and y1>c for a,c,b,d in rects[:i]))
        self.assertEqual(len(self.atlas),512*256);self.assertLessEqual(len(self.z.read(self.prefix+'font/font.refpack')),9860);self.assertLessEqual(len(self.z.read(self.prefix+'font/texture.refpack')),39228)
    def test_all_selected_ids_tokens_and_glyphs(self):
        rows=list(csv.DictReader(io.StringIO(self.z.read(self.prefix+'translations/global.zh-CN.menu-controls.csv').decode('utf-8-sig'))));self.assertEqual(len(rows),429)
        selected={r['id']:r for r in rows};glyphs,_=unpack_glyphs(self.inf,self.atlas)
        with (ROOT/'translations/global.zh-CN.nonstory.csv').open(encoding='utf-8-sig',newline='') as f:
            instructions=[r for r in csv.DictReader(f) if '[b=' in r['source']]
        self.assertEqual(len(instructions),85);self.assertTrue(all(r['id'] in selected for r in instructions))
        for r in rows:
            validate(r['source'],r['translation']);self.assertFalse(set(map(ord,TOKENS.sub('',r['translation'])))-set(glyphs))
    def test_clean_package_complete_no_numeric_probe_in_installer(self):
        manifest=json.loads(self.z.read(self.prefix+'manifest-F2.json'))
        for path,digest in manifest['package_sha256'].items():self.assertEqual(hashlib.sha256(self.z.read(self.prefix+path)).hexdigest(),digest,path)
        code=self.z.read(self.prefix+'patcher.py').decode();self.assertNotIn('apply_numeric_probe',code);self.assertIn("MANIFEST_NAME='manifest-F2.json'",code)

if __name__=='__main__':unittest.main()
