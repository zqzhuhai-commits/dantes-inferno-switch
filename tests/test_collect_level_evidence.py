import hashlib,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import collect_level_evidence as c

class LevelEvidenceTests(unittest.TestCase):
    def test_read_only_selected_entries_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'original.viv';out=Path(d)/'evidence.zip';data=b'level stream sample';digest=hashlib.sha256(data).hexdigest()
            with src.open('wb') as f:f.seek(64);f.write(data);f.truncate(3170839904)
            stamp=src.stat().st_mtime_ns
            with patch.object(c,'TARGETS',{0:(64,len(data),'00000001',digest)}),patch.object(c,'index',return_value={'entries':[dict(offset=64,size=len(data),key='00000001')]}):
                c.collect(src,out)
                with zipfile.ZipFile(out) as z:self.assertEqual(z.read('0.bin'),data);self.assertEqual(json.loads(z.read('level-evidence.json'))['entries'][0]['sha256'],digest)
                saved=out.read_bytes()
                with self.assertRaises(ValueError):c.collect(src,out)
                self.assertEqual(out.read_bytes(),saved)
            self.assertEqual(src.stat().st_mtime_ns,stamp)
    def test_wrong_original_rejected_before_zip_creation(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'original.viv';out=Path(d)/'evidence.zip'
            with src.open('wb') as f:f.truncate(3170839904)
            with patch.object(c,'TARGETS',{0:(64,4,'00000001','0'*64)}),patch.object(c,'index',return_value={'entries':[dict(offset=64,size=4,key='00000001')]}):
                with self.assertRaises(ValueError):c.collect(src,out)
            self.assertFalse(out.exists())
