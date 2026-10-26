import sys
from pathlib import Path
import struct
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from str_stream import reflow,unpack_selected,chunks,BLOCK


def example():
    path=b'shared\\fonts\\test.inf'
    shdr=struct.pack('>4sI4s',b'SHOC',44+4+len(path)+1,b'SHDR')+bytes(28)+struct.pack('>I',4)+b'one\0'+path+b'\0'
    # Pad the resource header to a 4 byte boundary.
    shdr+=bytes(-len(shdr)%4)
    shdr=shdr[:4]+struct.pack('>I',len(shdr))+shdr[8:]
    sdat=struct.pack('>4sI4s',b'SHOC',16,b'SDAT')+b'abcd'
    out=bytes.fromhex('6f6c73330000000c00020401')+shdr+sdat
    left=BLOCK-len(out)
    return out+struct.pack('>4sI',b'FILL',left)+bytes(left-8)


class StreamTests(unittest.TestCase):
    def test_reflow_large_resource_and_packet_bounds(self):
        old=example();path='shared\\fonts\\test.inf';payload=b'new!'*100000
        result,delta=reflow(old,{path:payload})
        self.assertEqual(delta,len(payload)-4)
        self.assertEqual(unpack_selected(result,{path})[path],payload)
        self.assertEqual(len(result)%BLOCK,0)
        self.assertTrue(all(off//BLOCK==(off+len(c)-1)//BLOCK for off,c in chunks(result)))

    def test_unmodified_resource_retained(self):
        old=example();result,delta=reflow(old,{})
        self.assertEqual(unpack_selected(old,{'shared\\fonts\\test.inf'}),unpack_selected(result,{'shared\\fonts\\test.inf'}))
        self.assertEqual(delta,0)

    def test_missing_replacement_and_invalid_chunks(self):
        with self.assertRaises(ValueError):reflow(example(),{'wrong':b'no'})
        with self.assertRaises(ValueError):list(chunks(b'wrong'))


if __name__=='__main__':unittest.main()
