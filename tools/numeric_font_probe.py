"""G0 bounded markup probe, applied after the known F1 resource builder.

This intentionally adds markup only to three plain labels; it is not a general
translation-token exception and does not alter any font or executable.
"""
import struct
from pathlib import Path
from lh2 import parse
from text_tokens import signature
from str_stream import unpack_selected

PROBES={'Options':'[b=0]','Start Game':'[b=1]','Continue':'[b=37]'}
EXPECTED={'Options':6,'Start Game':2,'Continue':2}

def replace_labels(original,f1_data,probes=PROBES,expected=EXPECTED):
    old=parse(original);rows=parse(f1_data)
    if len(old)!=len(rows):raise ValueError('F1 text count differs')
    out=bytearray(f1_data);counts=dict.fromkeys(probes,0)
    for before,row in zip(old,rows):
        if before['id']!=row['id']:raise ValueError('F1 string IDs differ')
        label=before['source']
        if label not in probes:continue
        if signature(label):raise ValueError('Probe requires plain original label')
        replacement=probes[label].encode();raw=row['source'].encode();at=row['offset']
        if len(replacement)>len(raw):raise ValueError('Probe exceeds F1 string slot')
        if f1_data[at:at+len(raw)+1]!=raw+b'\0':raise ValueError('Invalid F1 string boundary')
        out[at:at+len(raw)]=replacement+bytes(len(raw)-len(replacement));counts[label]+=1
    if counts!=expected:raise ValueError('Unexpected probe label counts')
    after=parse(out)
    for before,prior,new in zip(old,rows,after):
        want=probes.get(before['source'],prior['source'])
        if new['id']!=prior['id'] or new['offset']!=prior['offset'] or new['source']!=want:
            raise ValueError('Probe round-trip mismatch')
    if len(out)!=len(f1_data):raise ValueError('Probe changed table size')
    return bytes(out)

def apply_numeric_probe(source,entries,payloads):
    result=dict(payloads)
    # Check both font streams have the observed 38-glyph icon font. Numeric
    # parser behavior remains a hardware hypothesis, even with this bound.
    with Path(source).open('rb') as f:
        for number in (298,2095):
            entry=entries[number];f.seek(entry['offset']);raw=f.read(entry['size'])
            path='shared\\fonts\\buttons.inf'
            font=unpack_selected(raw,{path})[path]
            if font[:4]!=b'FONT' or struct.unpack_from('>HH',font,8)!=(7,38):
                raise ValueError('Unexpected original buttons font')
        for number in (752,1437):
            entry=entries[number];f.seek(entry['offset']);raw=f.read(entry['size'])
            result[number]=replace_labels(raw,payloads[number])
    if result[752]!=result[1437]:raise ValueError('Probe table copies differ')
    for number in payloads:
        if number not in (752,1437) and result[number]!=payloads[number]:
            raise ValueError('Probe changed non-text F1 resource')
    return result
