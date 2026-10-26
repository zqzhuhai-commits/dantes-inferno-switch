import struct
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from lh2 import parse
from lh2_build import rebuild
from test_lh2 import sample


def container():
    raw = sample()
    size = struct.unpack_from('>I', raw, 28)[0]
    shdr = bytearray(struct.pack('>4sI4s', b'SHOC', 44, b'SHDR') + b'\0' * 32)
    struct.pack_into('>I', shdr, 40, size)
    return raw[:12] + shdr + raw[12:] + struct.pack('>4sI', b'FILL', 8192) + b'\0' * 8184


class RebuildTests(unittest.TestCase):
    def test_roundtrip_and_untouched_rows(self):
        data = container()
        result = rebuild(data, [dict(id='0000000a',source='Continue',translation='继续游戏')])
        rows = parse(result)
        self.assertEqual(rows[0]['source'],'继续游戏')
        self.assertEqual(rows[1]['source'],'字幕 %1\\n')
        self.assertEqual(len(result),len(data))
        self.assertEqual(rebuild(data,[]),data)

    def test_reject_bad_tokens_stale_and_duplicate_rows(self):
        data = container()
        for rows in [[dict(id='00000014',source='字幕 %1\\n',translation='字幕 %1\n')],
                     [dict(id='0000000a',source='wrong',translation='继续')],
                     [dict(id='ffffffff',source='wrong',translation='继续')],
                     [dict(id='0000000a',source='Continue',translation='继续')]*2]:
            with self.assertRaises(ValueError):rebuild(data,rows)

    def test_capacity_limit(self):
        with self.assertRaisesRegex(ValueError,'capacity'):
            rebuild(container(), [dict(id='0000000a',source='Continue',translation='字'*10000)])


if __name__ == '__main__':
    unittest.main()
