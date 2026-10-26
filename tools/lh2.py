"""Export observed uncompressed ols3/SHOC/SDAT/2HCL localization tables."""
import argparse
import csv
import hashlib
import struct
from pathlib import Path


def parse(data):
    if data[:12] != bytes.fromhex('6f6c73330000000c00020401'):
        raise ValueError('Unsupported ols3 header')
    cursor = 12
    tables = []
    while cursor + 8 <= len(data):
        tag, length = struct.unpack_from('>4sI', data, cursor)
        if tag not in (b'SHOC', b'FILL') or length < 8 or cursor + length > len(data):
            raise ValueError(f'Invalid chunk at {cursor:#x}')
        if tag == b'SHOC' and data[cursor+8:cursor+12] == b'SDAT':
            base = cursor + 12
            payload = data[base:cursor+length]
            if payload.startswith(b'2HCL'):
                tables.append(parse_table(payload, base))
        cursor += length
    if cursor != len(data) and any(data[cursor:]):
        raise ValueError('Nonzero trailing bytes')
    if len(tables) != 1:
        raise ValueError(f'Expected one uncompressed 2HCL table, found {len(tables)}')
    return tables[0]


def parse_table(data, base=0):
    if len(data) < 32:
        raise ValueError('Truncated table header')
    magic, size, flags, reserved, count, languages, extra, extra2 = struct.unpack_from('>4s7I', data)
    if magic != b'2HCL' or flags != 0x40000001 or languages != 1 or reserved or extra or extra2:
        raise ValueError('Unsupported 2HCL layout')
    table_end = 32 + count * 8
    if not table_end <= size <= len(data) or len(data) - size > 3:
        raise ValueError('Invalid table size')
    rows = []
    previous = -1
    for i in range(count):
        key = struct.unpack_from('>I', data, 32 + i * 4)[0]
        offset = struct.unpack_from('>I', data, 32 + count * 4 + i * 4)[0]
        if key <= previous or not table_end <= offset < size:
            raise ValueError('Invalid key order or string offset')
        end = data.find(b'\0', offset, size)
        if end < 0:
            raise ValueError('Unterminated string')
        text = data[offset:end].decode('utf-8')
        rows.append(dict(id=f'{key:08x}', offset=base+offset,
                         source=text, translation=''))
        previous = key
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('entry', type=Path, help='VIV entry previously extracted using viv.py')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.entry.read_bytes()
    rows = parse(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'offset', 'source', 'translation'])
        writer.writeheader()
        writer.writerows(rows)
    print(f'Exported {len(rows)} strings; source SHA-256: {hashlib.sha256(data).hexdigest()}')


if __name__ == '__main__':
    main()
