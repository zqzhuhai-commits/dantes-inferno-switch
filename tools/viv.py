"""Read-only tools for Dante's observed BIGH variant (not generic EA BIG)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

CHUNK = 1024 * 1024


def index(path):
    with Path(path).open('rb') as f:
        header = f.read(16)
        if len(header) != 16:
            raise ValueError('Truncated header')
        magic = header[:4]
        declared = struct.unpack_from('<I', header, 4)[0]
        count, end = struct.unpack_from('>II', header, 8)
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
        # Aliases and overlaps are reported, not silently treated as corruption:
        # their meaning must be checked against the original game resources.
        warnings = []
        previous_end = end
        for item in sorted(records, key=lambda r: (r['offset'], r['size'])):
            if item['size'] and item['offset'] < previous_end:
                warnings.append(f"Entry {item['index']} overlaps another entry")
            previous_end = max(previous_end, item['offset'] + item['size'])
        if declared != size:
            warnings.append('Declared size differs from physical size; semantics unconfirmed')
        return dict(archive=Path(path).name, size=size, declared_size=declared,
                    index_end=end, warnings=warnings, entries=records)


def inspect(path):
    result = index(path)
    with Path(path).open('rb') as f:
        for item in result['entries']:
            f.seek(item['offset'])
            data = f.read(min(item['size'], 8192))
            item['head'] = data[:16].hex()
            # References only; never use untrusted container strings as filenames.
            item['paths'] = [s.decode('ascii') for s in
                             re.findall(rb'[\x20-\x7e]{6,}', data)
                             if b'\\' in s or b'/' in s]
    return result


def copy_entry(source, item, target):
    digest = hashlib.sha256()
    try:
        dest = target.open('xb')
    except FileExistsError:
        raise ValueError(f'Output already exists: {target}') from None
    try:
        with dest:
            source.seek(item['offset'])
            remaining = item['size']
            while remaining:
                data = source.read(min(remaining, CHUNK))
                if not data:
                    raise ValueError('Unexpected end of archive')
                dest.write(data)
                digest.update(data)
                remaining -= len(data)
    except BaseException:
        target.unlink()
        raise
    return dict(item, sha256=digest.hexdigest())


def extract(path, number, target):
    info = index(path)
    if not 0 <= number < len(info['entries']):
        raise ValueError('Entry index out of range')
    target = Path(target)
    if target.resolve() == Path(path).resolve():
        raise ValueError('Output cannot be the original archive')
    target.parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open('rb') as source:
        return copy_entry(source, info['entries'][number], target)


def extract_all(path, target):
    info = index(path)
    target = Path(target)
    # A fresh directory prevents overwrites, symlink traversal and mixed runs.
    target.mkdir(parents=True, exist_ok=False)
    manifest = dict(info, format_version=1, entries=[])
    with Path(path).open('rb') as source:
        for item in info['entries']:
            filename = f"{item['index']:06d}_{item['key']}.bin"
            record = copy_entry(source, item, target / filename)
            manifest['entries'].append(dict(record, file=filename))
    write_json(target / 'manifest.json', manifest)
    return manifest


def verify(path, manifest_path):
    """Compare extracted bytes and metadata against the current source archive."""
    info = index(path)
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('format_version') != 1:
        raise ValueError('Unsupported manifest version')
    if any(manifest.get(k) != info[k] for k in ('size', 'declared_size', 'index_end')):
        raise ValueError('Archive metadata mismatch')
    records = manifest.get('entries', [])
    if len(records) != len(info['entries']):
        raise ValueError('Manifest entry count mismatch')
    with Path(path).open('rb') as source:
        for item, record in zip(info['entries'], records):
            if any(record.get(k) != v for k, v in item.items()):
                raise ValueError(f"Entry metadata mismatch: {item['index']}")
            expected = f"{item['index']:06d}_{item['key']}.bin"
            if record.get('file') != expected:
                raise ValueError('Invalid manifest filename')
            extracted = manifest_path.parent / expected
            if extracted.is_symlink() or extracted.stat().st_size != item['size']:
                raise ValueError(f'Invalid extracted file: {expected}')
            digest = hashlib.sha256()
            source.seek(item['offset'])
            remaining = item['size']
            with extracted.open('rb') as f:
                while remaining:
                    n = min(remaining, CHUNK)
                    original, copied = source.read(n), f.read(n)
                    if len(original) != n or original != copied:
                        raise ValueError(f'Extracted bytes differ: {expected}')
                    digest.update(copied)
                    remaining -= n
            if digest.hexdigest() != record.get('sha256'):
                raise ValueError(f'Checksum mismatch: {expected}')
    return len(records)


def find(path, needle):
    """Stream literal byte searches, including matches across read boundaries."""
    if not needle or len(needle) > 4096:
        raise ValueError('Search must be 1..4096 encoded bytes')
    info = index(path)
    with Path(path).open('rb') as source:
        for item in info['entries']:
            source.seek(item['offset'])
            remaining, consumed, tail = item['size'], 0, b''
            while remaining:
                chunk = source.read(min(remaining, CHUNK))
                if not chunk:
                    raise ValueError('Unexpected end of archive')
                data = tail + chunk
                base = consumed - len(tail)
                start = 0
                while True:
                    pos = data.find(needle, start)
                    if pos < 0:
                        break
                    yield dict(index=item['index'], key=item['key'],
                               entry_offset=base + pos,
                               archive_offset=item['offset'] + base + pos)
                    start = pos + 1
                tail = data[-(len(needle) - 1):] if len(needle) > 1 else b''
                consumed += len(chunk)
                remaining -= len(chunk)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--extract', type=int, help='Zero-based entry index')
    mode.add_argument('--extract-all', action='store_true', help='Extract to a new directory')
    mode.add_argument('--verify', type=Path, metavar='MANIFEST')
    mode.add_argument('--find', help='Literal text to locate; JSON Lines output')
    parser.add_argument('--encoding', choices=['ascii', 'utf-8', 'utf-16-le', 'utf-16-be'], default='ascii')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.verify:
        print(f'Verified {verify(args.archive, args.verify)} entries against source')
    elif args.find is not None:
        needle = args.find.encode(args.encoding)
        # Open output before scanning to reject accidental overwrite early.
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x', encoding='utf-8') as f:
                for result in find(args.archive, needle):
                    f.write(json.dumps(result) + '\n')
        else:
            for result in find(args.archive, needle):
                print(json.dumps(result))
    else:
        if args.output is None:
            parser.error('--output is required for index/extraction')
        if args.extract_all:
            result = extract_all(args.archive, args.output)
            print(f"Extracted {len(result['entries'])} entries; manifest.json saved")
        elif args.extract is not None:
            print(json.dumps(extract(args.archive, args.extract, args.output)))
        else:
            result = inspect(args.archive)
            write_json(args.output, result)
            print(f"Validated {len(result['entries'])} entries")


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, UnicodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
