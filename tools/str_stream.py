"""Reflow observed ols3 SHOC streams on 128KiB packet boundaries."""
import struct

BLOCK=131072


def chunks(data):
    if data[:12]!=bytes.fromhex('6f6c73330000000c00020401'):
        raise ValueError('Unsupported STR header')
    pos=12
    while pos<len(data):
        if data[pos:pos+4]==b'\0'*4:
            end=min(((pos//BLOCK)+1)*BLOCK,len(data))
            if any(data[pos:end]):raise ValueError('Invalid packet padding')
            pos=end;continue
        if pos+8>len(data):raise ValueError('Truncated chunk')
        tag,size=struct.unpack_from('>4sI',data,pos)
        if size<8 or pos+size>len(data):raise ValueError('Invalid chunk size')
        if tag==b'FILL':
            if any(data[pos+8:pos+size]):raise ValueError('Nonzero FILL')
        elif tag==b'SHOC':
            if size<12 or pos//BLOCK!=(pos+size-1)//BLOCK:raise ValueError('Chunk crosses packet')
            yield pos,data[pos:pos+size]
        else:raise ValueError('Unknown chunk')
        pos+=size


def reflow(data,replacements):
    out=bytearray(data[:12]);current=None;seen=set();delta=0
    def emit(chunk):
        if len(chunk)>BLOCK:raise ValueError('Oversize packet')
        left=BLOCK-len(out)%BLOCK
        if len(chunk)>left:out.extend(bytes(left))
        out.extend(chunk)
    for offset,chunk in chunks(data):
        tag=chunk[8:12]
        if tag==b'SHDR':
            fields=chunk[44:].split(b'\0')
            if len(fields)<2:raise ValueError('Missing resource path')
            current=fields[1].decode('ascii')
            if current in replacements:
                if current in seen:raise ValueError('Duplicate resource path')
                seen.add(current);payload=replacements[current]
                original_size=struct.unpack_from('>I',chunk,40)[0]
                delta+=len(payload)-original_size
                header=bytearray(chunk);struct.pack_into('>I',header,40,len(payload));emit(header)
                # Independent SDAT chunks fit within packets, same as original
                # engine streaming convention. Only the final payload is padded.
                at=0
                while at<len(payload):
                    left=BLOCK-len(out)%BLOCK
                    if left<16:out.extend(bytes(left));left=BLOCK
                    n=min(len(payload)-at,(left-12)&~3)
                    part=payload[at:at+n];part+=bytes(-len(part)%4)
                    emit(struct.pack('>4sI4s',b'SHOC',12+len(part),b'SDAT')+part)
                    at+=n
            else:emit(chunk)
        elif current not in replacements:emit(chunk)
    if seen!=set(replacements):raise ValueError('Replacement resource not found')
    left=BLOCK-len(out)%BLOCK
    if left<8:out.extend(bytes(left));left=BLOCK
    out.extend(struct.pack('>4sI',b'FILL',left)+bytes(left-8))
    list(chunks(out))
    return bytes(out),delta


def unpack_selected(data,paths):
    result={};current=None;size=0;parts=[]
    def flush():
        if current in paths:
            payload=b''.join(parts)
            if len(payload)<size:raise ValueError('Truncated resource')
            result[current]=payload[:size]
    for _,chunk in chunks(data):
        tag=chunk[8:12]
        if tag==b'SHDR':
            flush();current=chunk[44:].split(b'\0')[1].decode('ascii')
            size=struct.unpack_from('>I',chunk,40)[0];parts=[]
        elif current in paths:
            if tag==b'SDAT':parts.append(chunk[12:])
            elif tag==b'Rpak':
                from refpack import decompress
                n=struct.unpack_from('>I',chunk,12)[0]
                parts.append(decompress(chunk[16:16+n]))
            else:raise ValueError('Unsupported selected compression')
    flush()
    if set(result)!=set(paths):raise ValueError('Missing selected resources')
    return result
