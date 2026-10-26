"""Offline compact RefPack encoder; NumPy is a build-time dependency only."""
from collections import deque
import numpy as np
from refpack import decompress


def compress_compact(data,max_chain=512):
    n=len(data)
    if n>0xffffff:raise ValueError('24-bit output size exceeded')
    matches=[];positions={}
    for i in range(n):
        lengths=[0,0,0];distances=[0,0,0]
        limit=min(1028,n-i)
        if limit>=3:
            key=data[i:i+3];q=positions.get(key,())
            for previous in reversed(q):
                distance=i-previous
                if distance>131072:break
                if lengths[2]>=limit and (lengths[1]>=min(67,limit) or distance>16384) and (lengths[0]>=min(10,limit) or distance>1024):break
                best=min(lengths[2],limit-1)
                if best>=3 and data[previous+best]!=data[i+best] and distance>16384:continue
                low,high=3,limit
                while low<high:
                    mid=(low+high+1)//2
                    if data[previous:previous+mid]==data[i:i+mid]:low=mid
                    else:high=mid-1
                for k,(maxdistance,cap) in enumerate([(1024,10),(16384,67),(131072,1028)]):
                    count=min(low,cap)
                    if distance<=maxdistance and count>lengths[k]:lengths[k]=count;distances[k]=distance
            positions.setdefault(key,deque(maxlen=max_chain)).append(i)
        matches.append((lengths,distances))
    costs=np.full(n+1,1<<40,dtype=np.int64);costs[n]=1
    choices=[None]*(n+1);choices[n]=('end',0,0,0)
    literal_lengths=np.arange(4,113,4,dtype=np.int64)
    for i in range(n-1,-1,-1):
        best=1<<40;choice=None
        if n-i<=3:best=1+n-i;choice=('end',n-i,0,0)
        runs=literal_lengths[literal_lengths<=n-i]
        if len(runs):
            values=costs[i+runs]+runs+1;k=int(np.argmin(values))
            if int(values[k])<best:best=int(values[k]);choice=('lit',int(runs[k]),0,0)
        for literal in range(min(3,n-i)+1):
            at=i+literal
            if at==n:continue
            lengths,distances=matches[at]
            for kind,(minimum,command) in enumerate([(3,2),(4,3),(5,4)]):
                maximum=lengths[kind]
                if maximum<minimum:continue
                values=costs[at+minimum:at+maximum+1];offset=int(np.argmin(values));count=minimum+offset
                cost=int(values[offset])+command+literal
                if cost<best:best=cost;choice=(kind,literal,count,distances[kind])
        costs[i]=best;choices[i]=choice
    out=bytearray(b'\x10\xfb'+n.to_bytes(3,'big'));i=0
    while True:
        kind,literal,count,distance=choices[i]
        if kind=='end':out.append(0xfc+literal);out.extend(data[i:]);break
        if kind=='lit':out.append(0xe0+literal//4-1);out.extend(data[i:i+literal]);i+=literal;continue
        d=distance-1
        if kind==0:out.extend([((d>>8)<<5)|((count-3)<<2)|literal,d&255])
        elif kind==1:out.extend([0x80|(count-4),(literal<<6)|(d>>8),d&255])
        else:
            length=count-5;out.extend([0xc0|((d>>16)<<4)|((length>>8)<<2)|literal,(d>>8)&255,d&255,length&255])
        out.extend(data[i:i+literal]);i+=literal+count
    if decompress(out,max_output=n)!=data:raise ValueError('Compact encoder round-trip failed')
    return bytes(out)
