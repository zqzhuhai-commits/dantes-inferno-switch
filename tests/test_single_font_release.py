import csv,hashlib,io,json,sys,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from refpack import decompress
from text_tokens import TOKENS,validate
from test_dense_menu_release import unpack_glyphs

class SingleFontTests(unittest.TestCase):
    def test_capacity_coverage_and_preserved_f1_rendering(self):
        with zipfile.ZipFile(ROOT/'checkpoints/Dante-F3-Single-Font-v0.6.3.zip') as z:
            p='Dante-F3-Single-Font-v0.6.3/'
            glyphs,rects=unpack_glyphs(decompress(z.read(p+'font/font.refpack')),decompress(z.read(p+'font/texture.refpack')))
            self.assertEqual(len(glyphs),771)
            self.assertLessEqual(len(z.read(p+'font/font.refpack')),9860);self.assertLessEqual(len(z.read(p+'font/texture.refpack')),39228)
            for i,(x,y,b,d) in enumerate(rects):self.assertFalse(any(x<bb and b>xx and y<dd and d>yy for xx,yy,bb,dd in rects[:i]))
            with zipfile.ZipFile(ROOT/'checkpoints/Dante-F1-Menu-Fix-v0.6.1.zip') as old:
                q='Dante-F1-Menu-Fix-v0.6.1/font/'
                original,_=unpack_glyphs(decompress(old.read(q+'font.refpack')),decompress(old.read(q+'texture.refpack')))
            for cp,v in original.items():self.assertEqual(glyphs[cp],v)
            rows=list(csv.DictReader(io.StringIO(z.read(p+'translations/global.zh-CN.menu-controls.csv').decode('utf-8-sig'))));self.assertEqual(len(rows),906)
            for r in rows:validate(r['source'],r['translation']);self.assertTrue(set(map(ord,TOKENS.sub('',r['translation'])))<=set(glyphs))
            with (ROOT/'translations/global.zh-CN.menu-controls.csv').open(encoding='utf-8-sig',newline='') as f:core=list(csv.DictReader(f))
            actual={r['id']:r['translation'] for r in rows}
            for r in core:self.assertEqual(actual[r['id']],r['translation'])
    def test_original_level_stream_and_no_dual_runtime(self):
        with zipfile.ZipFile(ROOT/'checkpoints/Dante-F3-Single-Font-v0.6.3.zip') as z:
            p='Dante-F3-Single-Font-v0.6.3/';m=json.loads(z.read(p+'manifest-F3.json'));code=z.read(p+'patcher.py').decode()
            self.assertEqual([t['index'] for t in m['targets'] if t['kind']=='font'],[2095])
            self.assertNotIn('dual_resources',code);self.assertNotIn('apply_numeric_probe',code);self.assertIn('patch_slots(raw,fonts)',code)
            self.assertNotIn('fonts\\\\buttons',code);self.assertNotIn('reflow(',code)
            for name,digest in m['package_sha256'].items():self.assertEqual(hashlib.sha256(z.read(p+name)).hexdigest(),digest)
