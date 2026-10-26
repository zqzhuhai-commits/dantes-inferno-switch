"""G2 capacity-checked dual-font resources, both startup and level copies."""
from pathlib import Path
import csv,hashlib,json,struct
from viv import index
from lh2_build import rebuild
from refpack import decompress
from dual_text import DualEncoder
from font_slot import patch_slots
from str_stream import chunks,unpack_selected
from str_compressed import reflow_compressed


def unchanged_chunks(data,replacements):
    current=None;result=[]
    for at,c in chunks(data):
        if c[8:12]==b'SHDR':current=c[44:].split(b'\0')[1].decode('ascii')
        if current not in replacements:result.append(c)
    return result

def fixed_stream(data,compressed):
    try:
        out,delta=patch_slots(data,compressed);return out,delta,'original_chunk_slots'
    except ValueError as e:
        if 'capacity' not in str(e):raise
    replacements={p:(decompress(blob),[blob]) for p,blob in compressed.items()}
    out,delta=reflow_compressed(data,replacements)
    end=max(at+len(c) for at,c in chunks(out));fill=len(data)-end
    if fill<8:raise ValueError('Repacked FONT stream exceeds original VIV entry capacity')
    out=out[:end]+struct.pack('>4sI',b'FILL',fill)+bytes(fill-8)
    if len(out)!=len(data):raise ValueError('STR total length changed')
    if unpack_selected(out,replacements)!={p:v[0] for p,v in replacements.items()}:raise ValueError('Repacked font reconstruction differs')
    if unchanged_chunks(data,replacements)!=unchanged_chunks(out,replacements):raise ValueError('Unrelated STR resource bytes changed')
    return out,delta,'compressed_chunks_repacked_inside_original_entry'

def adjust_toc(raw,number,font_delta,text_delta):
    data=bytearray(raw)
    if data[:4]!=bytes.fromhex('9cba7b28'):raise ValueError('TOC magic differs')
    n=struct.unpack_from('>H',data,8)[0]
    if 16+n*20>len(data):raise ValueError('TOC truncated')
    root=text=False
    for i in range(n):
        at=16+i*20;ptr,size=struct.unpack_from('>II',data,at)
        if ptr+8>len(data):raise ValueError('TOC pointer out of bounds')
        key=struct.unpack_from('>I',data,ptr)[0]
        if i==0 and key==0:
            stream=2095 if number in (171,2102) else 298
            expected=31156141 if stream==2095 else 40055388
            if size!=expected:raise ValueError('Original root decoded size differs')
            struct.pack_into('>I',data,at+4,size+font_delta[stream]);root=True
        elif key==0xe00af020:
            if size!=116272:raise ValueError('Original text decoded size differs')
            struct.pack_into('>I',data,at+4,size+text_delta);text=True
    if not root or not text:raise ValueError('Required TOC references missing')
    return bytes(data)

def make_resources(source,manifest,base):
    entries=index(source)['entries'];old={}
    with Path(source).open('rb') as f:
        for t in manifest['targets']:
            e=entries[t['index']]
            if any(e[k]!=t[k] for k in ('key','size','offset')):raise ValueError('VIV target index differs')
            f.seek(e['offset']);raw=f.read(e['size'])
            if hashlib.sha256(raw).hexdigest()!=t['sha256']:raise ValueError('Original target checksum differs')
            old[e['index']]=raw
    overview=json.loads((base/'dual/variants.json').read_text());attempts=[]
    for option in reversed(overview['variants']):
        folder=base/'dual'/option['name'];plan=json.loads((folder/'plan.json').read_text());result={};deltas={};placement={}
        compressed={f'shared\\fonts\\minion_pro.{ext}':(base/'dual'/name).read_bytes() for ext,name in [('inf','font.refpack'),('tg4d','texture.refpack')]}
        if plan['supplemental_glyphs']:
            compressed.update({f'shared\\fonts\\buttons.{ext}':(folder/name).read_bytes() for ext,name in [('inf','buttons-font.refpack'),('tg4d','buttons-texture.refpack')]})
        try:
            for stream in (2095,298):result[stream],deltas[stream],placement[stream]=fixed_stream(old[stream],compressed)
        except ValueError as e:
            if 'capacity' not in str(e):raise
            attempts.append(dict(option=option['name'],reason=str(e)));continue
        encoder=DualEncoder(plan['normal_codepoints'],{int(k):v for k,v in plan['icon_map'].items()})
        with (folder/'translations.csv').open(encoding='utf-8-sig',newline='') as f:translations=list(csv.DictReader(f))
        for row in translations:encoder.validate_row(row)
        for table in (752,1437):result[table]=rebuild(old[table],translations,encoder.encode)
        if result[752]!=result[1437]:raise ValueError('Global table copies differ')
        size=struct.unpack_from('>I',result[752],0x90)[0]
        text_delta=size-116272
        for toc in (2,171,302,1096,2102):result[toc]=adjust_toc(old[toc],toc,deltas,text_delta)
        report=dict(version=manifest['version'],selected_variant=option['name'],target_ids=overview['target_ids'],translated_ids_per_table=len(translations),total_replacements=2*len(translations),deferred_ids=len(plan['deferred']),supplemental_glyphs=plan['supplemental_glyphs'],normal_glyphs=len(plan['normal_codepoints']),placement=placement,skipped_capacity_options=attempts,viv_index_unchanged=True,output_size_unchanged=True,subtitle_table_942_unchanged=True,stage='resource_preflight_only',actual_2hcl_size=size,estimated_2hcl_size=plan['estimated_2hcl_size'],switch_tested=False)
        try:(base/'G2-build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        except OSError:pass
        return entries,result
    raise ValueError('两套字库都无法装入原 STR 条目容量，原文件未修改。'+json.dumps(attempts,ensure_ascii=False))
