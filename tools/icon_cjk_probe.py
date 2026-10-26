"""G1 in-place two-glyph buttons-font probe on top of the F1 payloads."""
from pathlib import Path
import hashlib,json,struct
from font_slot import patch_slots
from str_stream import chunks,unpack_selected
from numeric_font_probe import replace_labels
from refpack import decompress

PATH='shared\\fonts\\buttons.'
FONT_SHA='d9a0596e1135c48e11bc3bc8193201d6821304af43ce4fcc1b1cd35ffbcd79d1'
TEXTURE_SHA='729d5775dfc69f4d748f88f6b2d09e8dc7768e58bf42a1b8865796cb58e9f6ec'

def patch_icon_stream(data,compressed):
    originals=unpack_selected(data,{PATH+'inf',PATH+'tg4d'})
    if hashlib.sha256(originals[PATH+'inf']).hexdigest()!=FONT_SHA or hashlib.sha256(originals[PATH+'tg4d']).hexdigest()!=TEXTURE_SHA:raise ValueError('原图标字体不匹配')
    inf=decompress(compressed[PATH+'inf']);old=originals[PATH+'inf'];start=0x454;end=start+38*24
    if len(inf)!=len(old)+48 or struct.unpack_from('>HHI',inf,8)!=(7,40,start) or inf[start:end]!=old[start:end]:raise ValueError('新增字形结构或原字形校验失败')
    if [int.from_bytes(inf[end+i*24:end+i*24+2],'little') for i in range(2)]!=[38,39]:raise ValueError('测试字形编号不匹配')
    current=None;capacities={}
    for at,c in chunks(data):
        if c[8:12]==b'SHDR':current=c[44:].split(b'\0')[1].decode('ascii')
        elif current in compressed:
            if current in capacities:raise ValueError('图标资源不是单区块')
            capacities[current]=len(c)-16
    for path,blob in compressed.items():
        if path not in capacities:raise ValueError('缺少原图标资源')
        if len(blob)>capacities[path]:raise ValueError(f'{path} 原槽位容量 {capacities[path]} 字节，新数据需要 {len(blob)} 字节；已停止，原文件未修改。请提供本错误截图。')
    result,delta=patch_slots(data,compressed)
    if delta!=48:raise ValueError('图标字库解码长度变化不匹配')
    return result,capacities

def adjust_probe_toc(data):
    if data[:4]!=bytes.fromhex('9cba7b28'):raise ValueError('TOC 标识不匹配')
    ptr,size=struct.unpack_from('>II',data,16)
    if ptr+4>len(data) or struct.unpack_from('>I',data,ptr)[0]!=0:raise ValueError('TOC 根引用不匹配')
    out=bytearray(data);struct.pack_into('>I',out,20,size+48);return bytes(out)

def apply_icon_cjk_probe(source,entries,payloads,base):
    result=dict(payloads)
    compressed={PATH+'inf':(base/'font/buttons-font.refpack').read_bytes(),PATH+'tg4d':(base/'font/buttons-texture.refpack').read_bytes()}
    result[2095],caps=patch_icon_stream(payloads[2095],compressed)
    try:
        (base/'G1-slot-report.json').write_text(json.dumps({'stage':'preflight','buttons_slots':caps,'compressed_sizes':{k:len(v) for k,v in compressed.items()},'note':'preflight only; not a hardware result'},ensure_ascii=False,indent=2),encoding='utf-8')
    except OSError:pass
    for number in (171,2102):result[number]=adjust_probe_toc(payloads[number])
    with Path(source).open('rb') as f:
        for number in (752,1437):
            e=entries[number];f.seek(e['offset']);raw=f.read(e['size'])
            result[number]=replace_labels(raw,payloads[number],{'Options':'[b=38]','Start Game':'[b=39]'},{'Options':6,'Start Game':2})
    if result[752]!=result[1437]:raise ValueError('两份探针文本不一致')
    for number in result:
        if len(result[number])!=entries[number]['size']:raise ValueError('资源长度改变')
    return result
