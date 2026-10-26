"""Independent hash model for fixed-slot and appended VIV payloads."""
import hashlib
import struct

def calculate(source,entries,payloads,placement):
    # Independent byte-stream model, not runtime.apply.
    size=source.stat().st_size;locations={};h=hashlib.sha256();pos=0
    if placement=='append':
        for i in sorted(payloads):
            size=(size+2047)&~2047;locations[i]=size;size+=(len(payloads[i])+2047)&~2047
    with source.open('rb') as f:
        while block:=f.read(8*1024*1024):
            data=bytearray(block)
            if placement=='inplace':
                for i,payload in payloads.items():
                    at=entries[i]['offset'];lo=max(pos,at);hi=min(pos+len(data),at+len(payload))
                    if hi>lo:data[lo-pos:hi-pos]=payload[lo-at:hi-at]
            elif pos==0:
                struct.pack_into('<I',data,4,size)
                for i,at in locations.items():struct.pack_into('>II',data,16+12*i,at,(len(payloads[i])+2047)&~2047)
            h.update(data);pos+=len(data)
    if placement=='append':
        for i in sorted(payloads):
            h.update(bytes(locations[i]-pos));h.update(payloads[i]);pos=locations[i]+len(payloads[i]);pad=(-pos)%2048;h.update(bytes(pad));pos+=pad
    if pos!=size:raise ValueError('Independent size calculation mismatch')
    return size,h.hexdigest()

