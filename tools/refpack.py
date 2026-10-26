"""Bounded decoder for the observed 10fb RefPack stream variant."""


def decompress(data, max_output=64 * 1024 * 1024):
    if len(data) < 5 or data[:2] != b'\x10\xfb':
        raise ValueError('Unsupported RefPack header')
    expected = int.from_bytes(data[2:5], 'big')
    if expected > max_output:
        raise ValueError('RefPack output exceeds limit')
    out = bytearray()
    cursor = 5

    def take(n):
        nonlocal cursor
        if cursor + n > len(data):
            raise ValueError('Truncated RefPack stream')
        block = data[cursor:cursor+n]
        cursor += n
        return block

    while True:
        control = take(1)[0]
        if control >= 0xfc:
            literal, count, distance = control & 3, 0, 0
            stop = True
        elif control >= 0xe0:
            literal, count, distance = ((control & 31) + 1) * 4, 0, 0
            stop = False
        elif control >= 0xc0:
            b, c, d = take(3)
            literal = control & 3
            count = ((control & 12) << 6) + d + 5
            distance = ((control & 16) << 12) + (b << 8) + c + 1
            stop = False
        elif control >= 0x80:
            b, c = take(2)
            literal = b >> 6
            count = (control & 63) + 4
            distance = ((b & 63) << 8) + c + 1
            stop = False
        else:
            b = take(1)[0]
            literal = control & 3
            count = ((control & 28) >> 2) + 3
            distance = ((control & 96) << 3) + b + 1
            stop = False
        if len(out) + literal + count > expected:
            raise ValueError('RefPack output exceeds declared size')
        out.extend(take(literal))
        if count:
            if distance > len(out):
                raise ValueError('RefPack reference before output start')
            for _ in range(count):
                out.append(out[-distance])
        if stop:
            break
    if len(out) != expected or cursor != len(data):
        raise ValueError('RefPack size or consumed length mismatch')
    return bytes(out)
