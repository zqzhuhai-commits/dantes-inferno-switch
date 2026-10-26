import importlib.util
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('f1',ROOT/'packaging/fixed_menu_patcher.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def toc(root_size):
    data=bytearray(160)
    data[:4]=bytes.fromhex('9cba7b28')
    struct.pack_into('>H',data,8,2)
    struct.pack_into('>5I',data,16,128,root_size,0,0,0)
    struct.pack_into('>5I',data,36,136,116272,0x100,0,152)
    struct.pack_into('>I',data,136,0xe00af020)
    return bytes(data)


class MenuTableReferenceTests(unittest.TestCase):
    def test_frontend_references_track_text_and_font_deltas(self):
        for number in (171,2102):
            result=m.adjust_menu_toc(toc(31156141),number,-48,83760)
            self.assertEqual(struct.unpack_from('>I',result,20)[0],31156141+83760)
            self.assertEqual(struct.unpack_from('>I',result,40)[0],116272-48)

    def test_other_references_keep_unchanged_font_stream_size(self):
        for number in (2,302,1096):
            original=toc(0x263325c)
            result=m.adjust_menu_toc(original,number,-48,83760)
            self.assertEqual(result[16:36],original[16:36])
            self.assertEqual(struct.unpack_from('>I',result,40)[0],116272-48)

    def test_unknown_reference_or_wrong_original_size_is_rejected(self):
        with self.assertRaises(ValueError):m.adjust_menu_toc(toc(31156141),999,1,2)
        with self.assertRaises(ValueError):m.adjust_menu_toc(toc(31156141),2,1,2)


if __name__=='__main__':unittest.main()
