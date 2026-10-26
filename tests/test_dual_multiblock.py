import struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
from test_font_slot import sample
from str_stream import chunks,unpack_selected,BLOCK
from refpack import compress
from dual_resources import fixed_stream

def multi(tags):
    old=sample();parts=list(chunks(old));head=parts[0][1];raw=b'old!'*128;out=old[:12]+head
    for tag,part in zip(tags,[raw[:256],raw[256:]]):
        if tag==b'SDAT':out+=struct.pack('>4sI4s',b'SHOC',12+len(part),tag)+part
        else:
            blob=compress(part);n=(16+len(blob)+3)&~3;out+=struct.pack('>4sI4sI',b'SHOC',n,tag,len(blob))+blob+bytes(n-16-len(blob))
    n=BLOCK-len(out);return out+struct.pack('>4sI',b'FILL',n)+bytes(n-8)

class MultiBlockFontTests(unittest.TestCase):
    def test_split_sdat_rpak_and_mixed_bodies_repack(self):
        path='shared\\fonts\\test.inf';raw=b'expanded font!'*100
        for tags in [(b'SDAT',b'SDAT'),(b'Rpak',b'Rpak'),(b'SDAT',b'Rpak')]:
            with self.subTest(tags=tags):
                old=multi(tags);out,delta,mode=fixed_stream(old,{path:compress(raw)})
                self.assertEqual(len(out),len(old));self.assertIn('repacked',mode);self.assertEqual(delta,len(raw)-512);self.assertEqual(unpack_selected(out,{path})[path],raw)
    def test_missing_font_is_not_silently_reflowed(self):
        with self.assertRaisesRegex(ValueError,'缺失'):fixed_stream(multi((b'SDAT',b'SDAT')),{'missing.inf':compress(b'new')})
    def test_reflow_capacity_limit_still_rejects(self):
        import random
        raw=random.Random(2).randbytes(BLOCK+512)
        with self.assertRaises(ValueError):fixed_stream(multi((b'SDAT',b'SDAT')),{'shared\\fonts\\test.inf':compress(raw)})

if __name__=='__main__':unittest.main()
