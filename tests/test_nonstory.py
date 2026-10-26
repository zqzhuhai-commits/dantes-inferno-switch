import csv
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'),str(Path(__file__).resolve().parent)]
from refpack import compress
from str_compressed import reflow_compressed
from str_stream import chunks, unpack_selected, BLOCK
from test_font_slot import sample
from text_tokens import validate


class NonstoryTests(unittest.TestCase):
    def test_multi_packet_font_reconstruction(self):
        path = 'shared\\fonts\\test.inf'
        raw = b'first-block'*12000 + b'second-block'*12000
        packets = [compress(raw[i:i+65536]) for i in range(0,len(raw),65536)]
        result,delta = reflow_compressed(sample(),{path:(raw,packets)})
        self.assertEqual(unpack_selected(result,{path})[path],raw)
        self.assertEqual(delta,len(raw)-512)
        self.assertEqual(len(result)%BLOCK,0)
        for at,chunk in chunks(result):
            self.assertEqual(at//BLOCK,(at+len(chunk)-1)//BLOCK)

    def test_corrupt_or_missing_font_asset_rejected(self):
        path = 'shared\\fonts\\test.inf'
        with self.assertRaises(ValueError):
            reflow_compressed(sample(),{path:(b'expected',[compress(b'wrong')])})
        with self.assertRaisesRegex(ValueError,'Missing'):
            reflow_compressed(sample(),{'missing':(b'x',[compress(b'x')])})

    def test_complete_translation_table_preserves_ids_and_tokens(self):
        with (ROOT/'translations/global.zh-CN.nonstory.csv').open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        self.assertGreater(len(rows),1500)
        self.assertEqual(len(rows),len({r['id'] for r in rows}))
        for r in rows:
            self.assertTrue(r['translation'])
            validate(r['source'],r['translation'])
        sources={r['source']:r['translation'] for r in rows}
        for s in ('Options','Start Game','Continue','Save game','Relics','Magic','Tutorials','Quit Game'):
            self.assertIn(s,sources)
        self.assertEqual(sources['Continue\\n'],'继续\\n')


if __name__=='__main__':unittest.main()
