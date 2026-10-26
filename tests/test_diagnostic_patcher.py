import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
spec=importlib.util.spec_from_file_location('diagnostic',Path(__file__).resolve().parents[1]/'packaging/diagnostic_patcher.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)


def sample():
    texts=['Options']*6+['Keep %1\\n[b=RDUp]']
    n=len(texts);strings=b'';offsets=[]
    for text in texts:offsets.append(32+8*n+len(strings));strings+=text.encode()+b'\0'
    size=32+8*n+len(strings)
    payload=struct.pack('>4s7I',b'2HCL',size,0x40000001,0,n,1,0,0)
    payload+=struct.pack(f'>{n}I',*range(1,n+1))+struct.pack(f'>{n}I',*offsets)+strings
    payload+=bytes(-len(payload)%4)
    return bytes.fromhex('6f6c73330000000c00020401')+struct.pack('>4sI4s',b'SHOC',len(payload)+12,b'SDAT')+payload


class DiagnosticTests(unittest.TestCase):
    def test_ascii_and_chinese_keep_every_offset_and_other_byte(self):
        data=sample();item=dict(index=0,key='00000001',size=len(data),offset=0)
        target=dict(item,sha256=hashlib.sha256(data).hexdigest())
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source';source.write_bytes(data)
            with patch.object(d,'index',return_value={'entries':[item]}):
                for mode,expected in [('A','TEST-A!'),('B','选项')]:
                    entries,payloads=d.make_resources(source,dict(mode=mode,targets=[target]))
                    result=payloads[0];before=d.parse(data);after=d.parse(result)
                    self.assertEqual(len(data),len(result))
                    self.assertEqual([r['offset'] for r in before],[r['offset'] for r in after])
                    allowed=set()
                    for old,new in zip(before,after):
                        if old['source']=='Options':
                            self.assertEqual(new['source'],expected)
                            allowed.update(range(old['offset'],old['offset']+7))
                        else:self.assertEqual(old,new)
                    self.assertTrue(all(a==b or i in allowed for i,(a,b) in enumerate(zip(data,result))))


if __name__=='__main__':unittest.main()
