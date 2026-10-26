import csv
import io
import struct
import sys
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from refpack import decompress
from text_tokens import TOKENS,validate
from build_fixed_menu_font import build


class FixedMenuTests(unittest.TestCase):
    def test_fixed_assets_cover_all_menu_characters_and_fit_slots(self):
        path=ROOT/'checkpoints/Dante-Fixed-Menu-F-v0.6.zip'
        with zipfile.ZipFile(path) as z:
            base='Dante-Fixed-Menu-F-v0.6/'
            font=z.read(base+'font/font.refpack');tex=z.read(base+'font/texture.refpack')
            rows=list(csv.DictReader(io.StringIO(z.read(base+'translations/global.zh-CN.fixed-menu.csv').decode('utf-8-sig'))))
        self.assertLessEqual(len(font),9860);self.assertLessEqual(len(tex),39228)
        self.assertEqual(len(decompress(tex)),512*256)
        raw=decompress(font);start=struct.unpack_from('>I',raw,12)[0];n=struct.unpack_from('>H',raw,10)[0]
        cps={int.from_bytes(raw[start+i*24:start+i*24+2],'little') for i in range(n)}
        for row in rows:
            validate(row['source'],row['translation'])
            self.assertFalse({ord(c) for c in TOKENS.sub('',row['translation'])}-cps)

    def test_capacity_exceeded_is_rejected_before_raster_generation(self):
        with zipfile.ZipFile(ROOT/'checkpoints/Dante-Minimal-Font-C-v0.3.zip') as z:
            raw=bytearray(decompress(z.read('Dante-Minimal-Font-C-v0.3/font/font.refpack')))
        struct.pack_into('>H',raw,10,194)
        with self.assertRaisesRegex(ValueError,'capacity'):
            build(raw,'not-read.ttf',[''.join(chr(0x4e00+i) for i in range(650))])

    def test_original_character_coverage_is_preserved(self):
        def codes(font):
            start=struct.unpack_from('>I',font,12)[0];n=struct.unpack_from('>H',font,10)[0]
            return [int.from_bytes(font[start+i*24:start+i*24+2],'little') for i in range(n)]
        with zipfile.ZipFile(ROOT/'checkpoints/Dante-Minimal-Font-C-v0.3.zip') as z:
            original=codes(decompress(z.read('Dante-Minimal-Font-C-v0.3/font/font.refpack')))[:194]
        with zipfile.ZipFile(ROOT/'checkpoints/Dante-Fixed-Menu-F-v0.6.zip') as z:
            current=codes(decompress(z.read('Dante-Fixed-Menu-F-v0.6/font/font.refpack')))
        self.assertTrue(set(original)<=set(current))


if __name__=='__main__':unittest.main()
