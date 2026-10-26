import hashlib,importlib.util,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parents[1]/'tools')]
from test_diagnostic_patcher import sample
spec=importlib.util.spec_from_file_location('menu',Path(__file__).resolve().parents[1]/'packaging/minimal_font_patcher.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MenuPatchTests(unittest.TestCase):
    def run_patch(self,translations):
        data=sample();item=dict(index=0,key='00000001',size=len(data),offset=0)
        target=dict(item,kind='text',sha256=hashlib.sha256(data).hexdigest())
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source';source.write_bytes(data)
            with patch.object(m,'index',return_value={'entries':[item]}):
                return data,m.make_text_resources(source,dict(mode='D',targets=[target],translations=translations,text_changes_per_resource=7))[1][0]
    def test_preserves_offsets_and_tokens(self):
        before,after=self.run_patch({'Options':'选项','Keep %1\\n[b=RDUp]':'留 %1\\n[b=RDUp]'})
        a,b=m.parse(before),m.parse(after)
        self.assertEqual(len(before),len(after));self.assertEqual([r['offset'] for r in a],[r['offset'] for r in b])
        self.assertEqual(b[-1]['source'],'留 %1\\n[b=RDUp]')
    def test_rejects_token_loss_and_capacity_overflow(self):
        for text in ['留 %1[b=RDUp]','超过原文容量的很多中文字 %1\\n[b=RDUp]']:
            with self.assertRaises(ValueError):self.run_patch({'Options':'选项','Keep %1\\n[b=RDUp]':text})

if __name__=='__main__':unittest.main()
