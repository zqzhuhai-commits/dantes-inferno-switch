import sys
from pathlib import Path
import struct
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from font_slot import patch_slots
from str_stream import BLOCK,unpack_selected
from refpack import compress


def sample():
    path=b'shared\\fonts\\test.inf';raw=b'old!'*128
    head=bytearray(b'SHOC'+bytes(4)+b'SHDR'+bytes(28)+struct.pack('>I',len(raw))+b'test\0'+path+b'\0')
    head+=bytes(-len(head)%4);struct.pack_into('>I',head,4,len(head))
    body=struct.pack('>4sI4s',b'SHOC',len(raw)+12,b'SDAT')+raw
    data=bytes.fromhex('6f6c73330000000c00020401')+head+body
    left=BLOCK-len(data);return data+struct.pack('>4sI',b'FILL',left)+bytes(left-8)


class SlotTests(unittest.TestCase):
    def test_larger_decoded_font_fits_original_compressed_slot(self):
        old=sample();path='shared\\fonts\\test.inf';raw=b'new-larger-font!'*80
        result,delta=patch_slots(old,{path:compress(raw)})
        self.assertEqual(len(result),len(old));self.assertEqual(delta,len(raw)-512)
        self.assertEqual(unpack_selected(result,{path})[path],raw)
        self.assertEqual(old[:12],result[:12])

    def test_oversized_compressed_payload_and_missing_path(self):
        import random
        raw=random.Random(1).randbytes(2000)
        with self.assertRaisesRegex(ValueError,'capacity'):patch_slots(sample(),{'shared\\fonts\\test.inf':compress(raw)})
        with self.assertRaises(ValueError):patch_slots(sample(),{'missing':compress(b'x')})


if __name__=='__main__':unittest.main()
