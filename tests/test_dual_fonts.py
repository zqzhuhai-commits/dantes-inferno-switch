import csv,hashlib,io,json,struct,sys,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
from dual_text import DualEncoder
from dual_resources import fixed_stream,adjust_toc
from refpack import compress,decompress
from str_stream import unpack_selected,chunks
from test_font_slot import sample
from lh2_build import rebuild
from text_tokens import validate

class DualFontTests(unittest.TestCase):
    def test_encoding_round_trip_and_original_tokens_keep_order_and_lines(self):
        e=DualEncoder(set(map(ord,'A %1文字。')), {ord('中'):38})
        text='中文 %1\\n[b=RDLeft][c=RESET]A';encoded=e.encode(text)
        self.assertEqual(encoded,'[b=38]文 %1\\n[b=RDLeft][c=RESET]A');self.assertEqual(e.decode(encoded),text);validate(text,e.decode(encoded))
        with self.assertRaises(ValueError):e.encode('未覆盖')
        with self.assertRaises(ValueError):e.encode('[b=38]')
    def test_repack_inside_original_length_preserves_other_chunks(self):
        import random
        data=sample();raw=random.Random(2).randbytes(2048);path='shared\\fonts\\test.inf'
        out,delta,mode=fixed_stream(data,{path:compress(raw)})
        self.assertEqual(len(out),len(data));self.assertEqual(delta,2048-512);self.assertIn('repacked',mode);self.assertEqual(unpack_selected(out,{path})[path],raw)
    def test_toc_updates_both_font_streams_and_text_actual_size(self):
        def toc(root):
            data=bytearray(160);data[:4]=bytes.fromhex('9cba7b28');struct.pack_into('>H',data,8,2);struct.pack_into('>II',data,16,128,root);struct.pack_into('>II',data,36,136,116272);struct.pack_into('>I',data,136,0xe00af020);return data
        for idx,old in [(171,31156141),(2102,31156141),(2,40055388),(302,40055388),(1096,40055388)]:
            data=adjust_toc(toc(old),idx,{2095:100,298:200},-20)
            self.assertEqual(struct.unpack_from('>I',data,20)[0],old+(100 if idx in (171,2102) else 200));self.assertEqual(struct.unpack_from('>I',data,40)[0],116252)
    def test_package_all_variants_compiled_rows_and_limits(self):
        with zipfile.ZipFile(ROOT/'checkpoints/Dante-G2-Dual-Font-v0.8.0.zip') as z:
            p='Dante-G2-Dual-Font-v0.8.0/';overview=json.loads(z.read(p+'dual/variants.json'));manifest=json.loads(z.read(p+'manifest-G2.json'))
            for path,digest in manifest['package_sha256'].items():self.assertEqual(hashlib.sha256(z.read(p+path)).hexdigest(),digest,path)
            previous=0
            for option in overview['variants']:
                plan=json.loads(z.read(p+'dual/'+option['name']+'/plan.json'));e=DualEncoder(plan['normal_codepoints'],{int(k):v for k,v in plan['icon_map'].items()})
                rows=list(csv.DictReader(io.StringIO(z.read(p+'dual/'+option['name']+'/translations.csv').decode('utf-8-sig'))))
                self.assertGreaterEqual(len(rows),previous);previous=len(rows);self.assertEqual(len(rows),plan['translated_ids_per_table']);self.assertLessEqual(plan['estimated_2hcl_size'],130924)
                self.assertEqual(len(rows)+len(plan['deferred']),overview['target_ids'])
                for row in rows:self.assertEqual(e.decode(e.validate_row(row)),row['translation'])
                if option['supplemental_glyphs']:
                    inf=decompress(z.read(p+'dual/'+option['name']+'/buttons-font.refpack'))
                    self.assertEqual(struct.unpack_from('>H',inf,10)[0],38+option['supplemental_glyphs']);self.assertEqual(len(decompress(z.read(p+'dual/'+option['name']+'/buttons-texture.refpack'))),131072)
            self.assertEqual(previous,1066)
            self.assertEqual(len(manifest['targets']),9);self.assertIn(298,[t['index'] for t in manifest['targets']])

if __name__=='__main__':unittest.main()
