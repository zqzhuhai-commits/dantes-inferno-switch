import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'packaging/patcher.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'bigfile0.viv';self.output=self.root/'out.viv'
        self.original=b'BIGH'+struct.pack('<I',32)+struct.pack('>II',1,28)+struct.pack('>III',28,4,123)+b'abcd'
        self.source.write_bytes(self.original)
        expected=bytearray(self.original);struct.pack_into('<I',expected,4,4096);struct.pack_into('>II',expected,16,2048,2048)
        expected+=bytes(2048-len(expected))+b'new!'+bytes(2044)
        self.expected=bytes(expected)
        self.manifest=dict(source_size=32,source_sha256=hashlib.sha256(self.original).hexdigest(),
                           output_size=4096,output_sha256=hashlib.sha256(expected).hexdigest(),package_sha256={})
        (self.root/'manifest.json').write_text(json.dumps(self.manifest))
        self.base=patch.object(installer,'BASE',self.root);self.base.start();self.addCleanup(self.base.stop)
        self.resources=patch.object(installer,'make_resources',side_effect=lambda source,manifest:(installer.index(source)['entries'],{0:b'new!'}))
        self.resources.start();self.addCleanup(self.resources.stop)

    def test_end_to_end_autobackup(self):
        result,backup=installer.apply(self.source,self.output,True)
        self.assertEqual(result,self.source);self.assertEqual(backup.read_bytes(),self.original)
        self.assertEqual(self.source.read_bytes(),self.expected);self.assertFalse(self.output.exists())

    def test_wrong_hash_preserves_source(self):
        self.source.write_bytes(self.original[:-1]+b'x')
        with self.assertRaises(ValueError):installer.apply(self.source,self.output)
        self.assertFalse(self.output.exists());self.assertEqual(self.source.read_bytes(),self.original[:-1]+b'x')

    def test_cancel_and_output_collision(self):
        with self.assertRaises(ValueError):installer.apply(self.source,self.output,cancel=lambda:True)
        self.output.write_bytes(b'keep')
        with self.assertRaises(ValueError):installer.apply(self.source,self.output)
        self.assertEqual(self.output.read_bytes(),b'keep')

    def test_generated_hash_failure_removes_partial(self):
        self.manifest['output_sha256']='wrong';(self.root/'manifest.json').write_text(json.dumps(self.manifest))
        with self.assertRaises(ValueError):installer.apply(self.source,self.output)
        self.assertFalse(self.output.exists());self.assertFalse(Path(str(self.output)+'.partial').exists())
        self.assertEqual(self.source.read_bytes(),self.original)


if __name__=='__main__':unittest.main()
