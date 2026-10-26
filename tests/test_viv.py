import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('viv', Path(__file__).resolve().parents[1] / 'tools/viv.py')
viv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(viv)


class VivTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = self.root / 'sample.viv'

    def make_archive(self, payloads):
        end = 16 + 12 * len(payloads)
        offset = end
        rows = []
        for i, data in enumerate(payloads):
            rows.append(struct.pack('>III', offset, len(data), 0x12340000 + i))
            offset += len(data)
        self.archive.write_bytes(struct.pack('>4sIII', b'BIGH', offset, len(payloads), end)
                                 + b''.join(rows) + b''.join(payloads))

    def test_roundtrip_and_tamper(self):
        self.make_archive([b'hello', b'', b'font/path\x00' * 9])
        before = self.archive.read_bytes()
        out = self.root / 'out'
        manifest = viv.extract_all(self.archive, out)
        self.assertEqual(viv.verify(self.archive, out / 'manifest.json'), 3)
        self.assertEqual(before, self.archive.read_bytes())
        copied = out / manifest['entries'][0]['file']
        copied.write_bytes(b'jello')
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            viv.verify(self.archive, out / 'manifest.json')

    def test_search_chunk_boundaries_and_encodings(self):
        self.make_archive([b'xxxxabcabc', '字幕'.encode('utf-16-be'), b'aaaaa'])
        with patch.object(viv, 'CHUNK', 5):
            self.assertEqual([r['entry_offset'] for r in viv.find(self.archive, b'abc')], [4, 7])
            self.assertEqual([r['entry_offset'] for r in viv.find(self.archive, b'aaa')], [0, 1, 2])
            self.assertEqual([r['index'] for r in viv.find(self.archive, '字幕'.encode('utf-16-be'))], [1])
            self.assertEqual(len(list(viv.find(self.archive, b'a'))), 7)
        with self.assertRaises(ValueError):
            list(viv.find(self.archive, b''))

    def test_no_overwrite(self):
        self.make_archive([b'hello'])
        target = self.root / 'existing'
        target.write_bytes(b'keep')
        with self.assertRaises(ValueError):
            viv.extract(self.archive, 0, target)
        self.assertEqual(target.read_bytes(), b'keep')
        with self.assertRaises(ValueError):
            viv.extract(self.archive, 0, self.archive)
        directory = self.root / 'out'
        directory.mkdir()
        with self.assertRaises(FileExistsError):
            viv.extract_all(self.archive, directory)

    def test_malformed_ranges(self):
        self.archive.write_bytes(b'BIGH')
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            viv.index(self.archive)
        self.make_archive([b'hello'])
        data = bytearray(self.archive.read_bytes())
        struct.pack_into('>I', data, 16, len(data) + 10)
        self.archive.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'Invalid entry'):
            viv.index(self.archive)

    def test_bad_index_extent_and_wrong_magic(self):
        self.archive.write_bytes(struct.pack('>4sIII', b'BIGH', 16, 10, 16))
        with self.assertRaisesRegex(ValueError, 'index extent'):
            viv.index(self.archive)
        self.archive.write_bytes(struct.pack('>4sIII', b'BIGF', 16, 0, 16))
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            viv.index(self.archive)

    def test_source_change_and_manifest_path(self):
        self.make_archive([b'hello'])
        out = self.root / 'out'
        viv.extract_all(self.archive, out)
        self.make_archive([b'jello'])
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            viv.verify(self.archive, out / 'manifest.json')
        import json
        manifest = json.loads((out / 'manifest.json').read_text())
        manifest['entries'][0]['file'] = '../sample.viv'
        (out / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'filename'):
            viv.verify(self.archive, out / 'manifest.json')

    def test_failed_copy_removes_partial_file(self):
        import io
        target = self.root / 'partial'
        with self.assertRaisesRegex(ValueError, 'Unexpected end'):
            viv.copy_entry(io.BytesIO(b'abc'), dict(offset=0, size=10), target)
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
