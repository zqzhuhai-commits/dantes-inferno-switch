import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from numeric_font_probe import replace_labels
from lh2 import parse
from viv_overlay_hash import calculate

def sample(texts):
    n=len(texts);strings=b'';offsets=[]
    for t in texts:offsets.append(32+8*n+len(strings));strings+=t.encode()+b'\0'
    size=32+8*n+len(strings)
    p=struct.pack('>4s7I',b'2HCL',size,0x40000001,0,n,1,0,0)
    p+=struct.pack(f'>{n}I',*range(1,n+1))+struct.pack(f'>{n}I',*offsets)+strings;p+=bytes(-len(p)%4)
    return bytes.fromhex('6f6c73330000000c00020401')+struct.pack('>4sI4s',b'SHOC',len(p)+12,b'SDAT')+p

class NumericFontProbeTests(unittest.TestCase):
    def test_only_exact_plain_labels_change_and_offsets_stay_fixed(self):
        labels=['Options']*6+['Start Game']*2+['Continue']*2+['Keep %1\\n[b=RDUp]']
        original=sample(labels);f1=sample([{'Options':'选项','Start Game':'开始游戏','Continue':'继续'}.get(t,t) for t in labels])
        out=replace_labels(original,f1);a,b=parse(f1),parse(out)
        self.assertEqual(len(out),len(f1));self.assertEqual([r['offset'] for r in a],[r['offset'] for r in b]);self.assertEqual(a[-1],b[-1])
        self.assertEqual([r['source'] for r in b[:-1]],['[b=0]']*6+['[b=1]']*2+['[b=37]']*2)
        allowed=set()
        for row in a[:-1]:allowed.update(range(row['offset'],row['offset']+len(row['source'].encode())))
        self.assertTrue(all(x==y or i in allowed for i,(x,y) in enumerate(zip(f1,out))))
    def test_missing_labels_and_too_short_slots_rejected(self):
        with self.assertRaises(ValueError):replace_labels(sample(['Options']),sample(['选项']))
        labels=['Options']*6+['Start Game']*2+['Continue']*2
        with self.assertRaises(ValueError):replace_labels(sample(labels),sample(['X']*10))
    def test_independent_hash_matches_actual_overlay(self):
        import tempfile,hashlib
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source';p.write_bytes(b'A'*30)
            entries=[{'offset':3},{'offset':20}];payloads={0:b'123',1:b'4567'}
            size,digest=calculate(p,entries,payloads,'inplace')
            self.assertEqual(size,30);self.assertEqual(digest,hashlib.sha256(b'AAA123'+b'A'*14+b'4567'+b'A'*6).hexdigest())

if __name__=='__main__':unittest.main()
