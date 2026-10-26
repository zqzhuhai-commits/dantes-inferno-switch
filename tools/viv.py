"""Read-only index/extraction tool for the observed Dante BIGH variant."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

def index(path):
    with Path(path).open('rb') as f:
        header = f.read(16)
        if len(header) != 16:
            raise ValueError('Truncated header')
        magic, declared, count, end = struct.unpack('>4sIII', header)
        if magic != b'BIGH' or count > 1000000:
            raise ValueError('Unsupported archive')
        size = f.seek(0, 2)
        if end < 16 + count * 12 or end > size:
            raise ValueError('Invalid index extent')
        f.seek(16)
        records = []
        for i in range(count):
            offset, length, key = struct.unpack('>III', f.read(12))
            if offset < end or offset + length > size:
                raise ValueError(f'Invalid entry {i}')
            records.append(dict(index=i, offset=offset, size=length, key=f'{key:08x}'))
        return dict(archive=Path(path).name, size=size, declared_size=declared,
                    index_end=end, entries=records)

def inspect(path):
    result = index(path)
    with Path(path).open('rb') as f:
        for item in result['entries']:
            f.seek(item['offset'])
            data = f.read(min(item['size'], 8192))
            item['head'] = data[:16].hex()
            if data.startswith(bytes.fromhex('9cba7b28')):
                item['paths'] = [s.decode('ascii') for s in
                                 re.findall(rb'[\x20-\x7e]{6,}', data)
                                 if b'\\' in s]
    return result

def extract(path, number, target):
    info = index(path)
    if not 0 <= number < len(info['entries']):
        raise ValueError('Entry index out of range')
    item = info['entries'][number]
    target = Path(target)
    if target.resolve() == Path(path).resolve():
        raise ValueError('Output cannot be the original archive')
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with Path(path).open('rb') as source, target.open('xb') as dest:
        source.seek(item['offset'])
        remaining = item['size']
        while remaining:
            data = source.read(min(remaining, 1024 * 1024))
            if not data:
                raise ValueError('Unexpected end of archive')
            dest.write(data)
            digest.update(data)
            remaining -= len(data)
    return dict(item, sha256=digest.hexdigest())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--extract', type=int, help='Zero-based entry index')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.extract is None:
        result = inspect(args.archive)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Validated {len(result['entries'])} entries")
    else:
        print(json.dumps(extract(args.archive, args.extract, args.output)))
