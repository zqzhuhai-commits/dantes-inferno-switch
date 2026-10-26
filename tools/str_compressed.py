"""Packet-aligned compressed FONT resource replacement for the E experiment.

Build-time encoding is separate: runtime only consumes verified 10fb packets.
"""
import struct
from refpack import decompress
from str_stream import BLOCK, chunks, unpack_selected


def reflow_compressed(data, replacements):
    # path -> (decoded bytes, sequence of individually compressed chunks)
    out = bytearray(data[:12])
    current = None
    seen = set()
    delta = 0

    def emit(chunk):
        if len(chunk) > BLOCK:
            raise ValueError('Compressed resource chunk exceeds packet')
        left = BLOCK - len(out) % BLOCK
        if len(chunk) > left:
            out.extend(bytes(left))
        out.extend(chunk)

    for _, chunk in chunks(data):
        if chunk[8:12] == b'SHDR':
            current = chunk[44:].split(b'\0')[1].decode('ascii')
            if current in replacements:
                if current in seen:
                    raise ValueError('Duplicate replacement path')
                seen.add(current)
                raw, packets = replacements[current]
                decoded = b''.join(decompress(p) for p in packets)
                if decoded != raw:
                    raise ValueError('Compressed asset round-trip mismatch')
                head = bytearray(chunk)
                delta += len(raw) - struct.unpack_from('>I', head, 40)[0]
                struct.pack_into('>I', head, 40, len(raw))
                emit(head)
                for packet in packets:
                    size = (16 + len(packet) + 3) & ~3
                    emit(struct.pack('>4sI4sI', b'SHOC', size, b'Rpak', len(packet))
                         + packet + bytes(size-16-len(packet)))
            else:
                emit(chunk)
        elif current not in replacements:
            emit(chunk)
    if seen != set(replacements):
        raise ValueError('Missing replacement resource')
    left = BLOCK - len(out) % BLOCK
    if left < 8:
        out.extend(bytes(left))
        left = BLOCK
    out.extend(struct.pack('>4sI', b'FILL', left) + bytes(left-8))
    expected = {p: value[0] for p, value in replacements.items()}
    if unpack_selected(out, expected) != expected:
        raise ValueError('Compressed STR reconstruction mismatch')
    return bytes(out), delta
