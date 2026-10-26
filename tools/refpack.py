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


def compress(data):
    """Greedy encoder for the same bounded 10fb variant, verified by decode."""
    from collections import deque
    if len(data)>0xffffff:raise ValueError('RefPack 24-bit length exceeded')
    out=bytearray(b'\x10\xfb'+len(data).to_bytes(3,'big'))
    positions={};pending=bytearray();pos=0
    def remember(i):
        if i+3<=len(data):
            q=positions.setdefault(data[i:i+3],deque(maxlen=4096));q.append(i)
    def literals(final=False):
        while len(pending)>=4:
            n=min(len(pending)//4*4,112)
            out.append(0xe0+(n//4)-1);out.extend(pending[:n]);del pending[:n]
        if final:out.append(0xfc+len(pending));out.extend(pending);pending.clear()
    while pos<len(data):
        best=0;distance=0
        if pos+3<=len(data):
            q=positions.get(data[pos:pos+3],())
            limit=min(1028,len(data)-pos)
            for previous in reversed(q):
                dist=pos-previous
                if dist>131072:break
                # Long form is also valid at short distances, so inspect the
                # full limit and choose its appropriate command below.
                cap=limit
                if best>=cap:break
                if best>=3 and data[previous+best]!=data[pos+best]:continue
                n=3
                while n<cap and data[previous+n]==data[pos+n]:n+=1
                if (n>=5 or n>=4 and dist<=16384 or n>=3 and dist<=1024) and n>best:
                    best=n;distance=dist
                    if n==limit:break
        if best:
            literals();literal=len(pending);dist=distance-1
            if best<=10 and distance<=1024:
                out.extend([((dist>>8)<<5)|((best-3)<<2)|literal,dist&255])
            elif best<=67 and distance<=16384:
                out.extend([0x80|(best-4),(literal<<6)|(dist>>8),dist&255])
            else:
                if best<5:raise ValueError('Invalid long match')
                length=best-5
                out.extend([0xc0|((dist>>16)<<4)|((length>>8)<<2)|literal,(dist>>8)&255,dist&255,length&255])
            out.extend(pending);pending.clear()
            for i in range(pos,pos+best):remember(i)
            pos+=best
        else:
            pending.append(data[pos]);remember(pos);pos+=1
            if len(pending)>=115:literals()
    literals(final=True)
    if decompress(out,max_output=len(data))!=data:raise ValueError('RefPack encoder round-trip failed')
    return bytes(out)
