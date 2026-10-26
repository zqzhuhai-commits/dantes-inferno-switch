import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from refpack import decompress


def stream(size, commands):
    return b'\x10\xfb' + size.to_bytes(3, 'big') + commands


class RefPackTests(unittest.TestCase):
    def test_literal_and_stop(self):
        self.assertEqual(decompress(stream(7, b'\xe0abcd\xffxyz')), b'abcdxyz')

    def test_short_overlapping_reference(self):
        self.assertEqual(decompress(stream(8, b'\xe0abcd\x04\x00\xfc')), b'abcddddd')

    def test_medium_reference(self):
        self.assertEqual(decompress(stream(8, b'\xe0abcd\x80\x00\x03\xfc')), b'abcdabcd')

    def test_long_reference(self):
        self.assertEqual(decompress(stream(9, b'\xe0abcd\xc0\x00\x03\x00\xfc')), b'abcdabcda')

    def test_invalid_and_truncated_streams(self):
        for bad in [b'bad', stream(7,b'\xe0ab'), stream(1,b'\x00\x00\xfc'),
                    stream(1,b'\xfc'), stream(0,b'\xfcjunk')]:
            with self.assertRaises(ValueError):decompress(bad)
        with self.assertRaises(ValueError):decompress(stream(100,b''),max_output=10)


if __name__ == '__main__':
    unittest.main()
