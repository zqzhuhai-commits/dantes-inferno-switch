"""Replace exactly one font body per resource in its existing STR chunk slot."""
import struct
from refpack import decompress
from str_stream import chunks,unpack_selected


def patch_slots(data,replacements):
    """replacements maps internal paths to complete 10fb compressed streams."""
    out=bytearray(data);current=None;headers={};bodies={}
    for at,chunk in chunks(data):
        tag=chunk[8:12]
        if tag==b'SHDR':
            current=chunk[44:].split(b'\0')[1].decode('ascii')
            if current in replacements:
                if current in headers:raise ValueError('Duplicate font resource')
                headers[current]=(at,chunk)
        elif current in replacements:bodies.setdefault(current,[]).append((at,chunk))
    expected={};delta=0
    for path,compressed in replacements.items():
        raw=decompress(compressed)
        if path not in headers or len(bodies.get(path,[]))!=1:raise ValueError('Expected one original font body')
        header_at,header=headers[path];at,body=bodies[path][0]
        if body[8:12] not in [b'SDAT',b'Rpak']:raise ValueError('Unsupported original font compression')
        size=len(body)
        if len(compressed)+16>size:raise ValueError('Compressed font exceeds original chunk capacity')
        replacement=struct.pack('>4sI4sI',b'SHOC',size,b'Rpak',len(compressed))+compressed
        replacement+=bytes(size-len(replacement))
        out[at:at+size]=replacement
        oldsize=struct.unpack_from('>I',header,40)[0]
        struct.pack_into('>I',out,header_at+40,len(raw));delta+=len(raw)-oldsize
        expected[path]=raw
    if len(out)!=len(data):raise ValueError('STR length changed')
    before=[(at,len(c)) for at,c in chunks(data)]
    after=[(at,len(c)) for at,c in chunks(out)]
    if before!=after:raise ValueError('STR chunk position or size changed')
    if unpack_selected(out,expected)!=expected:raise ValueError('Font slot reconstruction failed')
    return bytes(out),delta
