import hashlib,importlib.util,json,struct,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'packaging')]
import build_numeric_probe_release as builder
import numeric_font_probe,viv_overlay_hash

class ProbeReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name);cls.package=cls.root/'G0'
        builder.build(cls.package)
        spec=importlib.util.spec_from_file_location('g0_runtime',cls.package/'patcher.py');cls.runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.runtime)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_clean_zip_has_every_checked_asset_and_correct_title(self):
        with zipfile.ZipFile(str(self.package)+'.zip') as z:
            manifest=json.loads(z.read('G0/manifest-G0.json'))
            for name,digest in manifest['package_sha256'].items():self.assertEqual(hashlib.sha256(z.read('G0/'+name)).hexdigest(),digest)
            self.assertNotIn(b'F1 \xe5\x8e\x9f\xe4\xbd\x8d\xe8\x8f\x9c\xe5\x8d\x95\xe4\xbf\xae\xe6\xad\xa3\xe7\x89\x88',z.read('G0/patcher.py'))
    def execute_synthetic(self,wrong_hash=False):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'bigfile0.viv';out=root/'out.viv'
            original=b'BIGH'+struct.pack('<I',32)+struct.pack('>II',1,28)+struct.pack('>III',28,4,123)+b'abcd';src.write_bytes(original)
            (root/'manifest-G0.json').write_text(json.dumps(dict(source_size=32,source_sha256=hashlib.sha256(original).hexdigest(),output_size=32,package_sha256={})))
            m=self.runtime
            with patch.object(m,'BASE',root),patch.object(m,'make_resources',side_effect=lambda s,x:(m.index(s)['entries'],{0:b'new!'})),patch.object(numeric_font_probe,'apply_numeric_probe',side_effect=lambda s,e,p:p):
                if wrong_hash:
                    with patch.object(viv_overlay_hash,'calculate',return_value=(32,'wrong')):
                        with self.assertRaises(ValueError):m.apply(src,out,True)
                    self.assertEqual(src.read_bytes(),original);self.assertFalse(out.exists());self.assertFalse(Path(str(out)+'.partial').exists())
                else:
                    result,backup=m.apply(src,out,True)
                    self.assertEqual(src.read_bytes(),original[:-4]+b'new!');self.assertEqual(backup.read_bytes(),original)
    def test_synthetic_installer_build_and_backup(self):self.execute_synthetic()
    def test_synthetic_hash_failure_keeps_original(self):self.execute_synthetic(True)

if __name__=='__main__':unittest.main()
