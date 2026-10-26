import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('lh2', Path(__file__).resolve().parents[1] / 'tools/lh2.py')
lh2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lh2)


def sample():
    texts = ['Continue', '字幕 %1\\n'].copy()
    strings = b''
    offsets = []
    for text in texts:
        offsets.append(48 + len(strings))
        strings += text.encode('utf-8') + b'\0'
    payload = struct.pack('>4s7I', b'2HCL', 48+len(strings), 0x40000001, 0, 2, 1, 0, 0)
    payload += struct.pack('>4I', 10, 20, *offsets) + strings
    payload += b' ' * (-len(payload) % 4)
    return bytes.fromhex('6f6c73330000000c00020401') + struct.pack('>4sI4s', b'SHOC', 12+len(payload), b'SDAT') + payload


class LH2Tests(unittest.TestCase):
    def test_export_preserves_ids_utf8_and_controls(self):
        rows = lh2.parse(sample())
        self.assertEqual([r['id'] for r in rows], ['0000000a', '00000014'])
        self.assertEqual(rows[1]['source'], '字幕 %1\\n')
        self.assertEqual(rows[0]['offset'], 72)

    def test_reject_truncation(self):
        with self.assertRaises(ValueError):
            lh2.parse(sample()[:-2])

    def test_reject_offset_outside_table(self):
        d = bytearray(sample())
        struct.pack_into('>I', d, 24+32+8, 1)
        with self.assertRaises(ValueError):
            lh2.parse(d)

    def test_reject_duplicate_id(self):
        d = bytearray(sample())
        struct.pack_into('>I', d, 24+32+4, 10)
        with self.assertRaises(ValueError):
            lh2.parse(d)

    def test_reject_unknown_format(self):
        with self.assertRaises(ValueError):
            lh2.parse(b'not a container')


if __name__ == '__main__':
    unittest.main()
