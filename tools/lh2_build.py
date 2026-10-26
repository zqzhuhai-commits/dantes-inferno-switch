"""Experimental fixed-slot LH2 entry rebuild; does not patch a VIV or a font."""
import argparse
import csv
from pathlib import Path
import struct
from lh2 import parse
from text_tokens import validate


def rebuild(data, translations, encoder=None):
    rows = parse(data)
    known = {row['id']: row for row in rows}
    seen = set()
    replacements = {}
    for row in translations:
        key = row['id']
        if key in seen or key not in known:
            raise ValueError(f'Duplicate or unknown string ID: {key}')
        seen.add(key)
        if row['source'] != known[key]['source']:
            raise ValueError(f'Stale source text: {key}')
        text = row['translation']
        if text == '':
            continue  # Blank means untranslated, not deletion.
        try:
            validate(row['source'], text)
        except ValueError as exc:
            raise ValueError(f'{key}: {exc}') from exc
        replacements[key] = encoder(text) if encoder is not None else text
    if not replacements:
        return data
    # Narrow to the observed SHDR, SDAT, trailing FILL layout. Do not relocate
    # unrelated chunks or guess length/hash fields in an unknown container.
    shdr = 12
    shdr_len = struct.unpack_from('>I', data, shdr+4)[0]
    sdat = shdr + shdr_len
    if data[shdr:shdr+4] != b'SHOC' or data[shdr+8:shdr+12] != b'SHDR':
        raise ValueError('Expected SHDR')
    if data[sdat:sdat+4] != b'SHOC' or data[sdat+8:sdat+16] != b'SDAT2HCL':
        raise ValueError('Expected uncompressed SDAT/2HCL')
    old_chunk_len = struct.unpack_from('>I', data, sdat+4)[0]
    old_size = struct.unpack_from('>I', data, sdat+16)[0]
    fill = sdat + old_chunk_len
    if data[fill:fill+4] != b'FILL' or struct.unpack_from('>I', data, fill+4)[0] != len(data)-fill:
        raise ValueError('Expected a single trailing FILL chunk')
    if shdr_len < 44 or struct.unpack_from('>I', data, shdr+40)[0] != old_size:
        raise ValueError('SHDR size field does not match 2HCL size')
    count = len(rows)
    text_data = bytearray()
    offsets = []
    for row in rows:
        offsets.append(32 + count*8 + len(text_data))
        text_data.extend(replacements.get(row['id'], row['source']).encode('utf-8') + b'\0')
    payload = bytearray(data[sdat+12:sdat+44])
    payload.extend(struct.pack(f'>{count}I', *(int(r['id'], 16) for r in rows)))
    payload.extend(struct.pack(f'>{count}I', *offsets))
    payload.extend(text_data)
    size = len(payload)
    struct.pack_into('>I', payload, 4, size)
    payload.extend(b'\0' * (-size % 4))
    new_fill = len(data) - sdat - 12 - len(payload)
    if new_fill < 8:
        raise ValueError('Translated table exceeds fixed VIV entry capacity')
    prefix = bytearray(data[:sdat])
    struct.pack_into('>I', prefix, shdr+40, size)
    result = bytes(prefix) + struct.pack('>4sI4s', b'SHOC', len(payload)+12, b'SDAT') + payload
    result += struct.pack('>4sI', b'FILL', new_fill) + b'\0' * (new_fill-8)
    exported = parse(result)
    if len(result) != len(data) or len(exported) != count:
        raise ValueError('Rebuild length or count mismatch')
    for before, after in zip(rows, exported):
        if before['id'] != after['id'] or after['source'] != replacements.get(before['id'], before['source']):
            raise ValueError('Rebuild round-trip mismatch')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('entry', type=Path)
    parser.add_argument('translations', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with args.translations.open(encoding='utf-8-sig', newline='') as f:
        translations = list(csv.DictReader(f))
    result = rebuild(args.entry.read_bytes(), translations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as f:
        f.write(result)
    print(f'Rebuilt and reparsed {len(result)} bytes; experimental entry only, not an installable patch')


if __name__ == '__main__':
    main()
