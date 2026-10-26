import sys,random
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from refpack import compress,decompress
from refpack_compact import compress_compact


class EncoderTests(unittest.TestCase):
    def test_greedy_roundtrip(self):
        for raw in [b'',b'a',b'abc',b'abcd',bytes(6000),b'word'*2000,random.Random(4).randbytes(4000)]:
            self.assertEqual(decompress(compress(raw)),raw)

    def test_compact_roundtrip_and_size(self):
        for raw in [b'',b'abc',b'abcd'*150,random.Random(9).randbytes(128)]:
            result=compress_compact(raw)
            self.assertEqual(decompress(result),raw)
            self.assertLessEqual(len(result),len(compress(raw)))


if __name__=='__main__':unittest.main()
