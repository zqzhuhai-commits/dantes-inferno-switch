"""Build F1 duplicate-table menu package without moving any VIV/STR resource slot."""
import argparse,csv,hashlib,importlib.util,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'packaging')]
from viv import index
from package_release import build_package
from viv_overlay_hash import calculate


def build(source,c_package,font,output):
    if output.exists():raise ValueError('Output exists')
    c=json.loads((c_package/'manifest-C.json').read_text());h=hashlib.sha256()
    with source.open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    if h.hexdigest()!=c['source_sha256']:raise ValueError('Original checksum mismatch')
    output.mkdir();(output/'font').mkdir();(output/'translations').mkdir();(output/'tools').mkdir()
    shutil.copytree(c_package/'Licenses',output/'Licenses')
    for name in ['font.refpack','texture.refpack','preview.png','font-report.json']:shutil.copyfile(font/name,output/'font'/name)
    shutil.copyfile(ROOT/'translations/global.zh-CN.fixed-menu.csv',output/'translations/global.zh-CN.fixed-menu.csv')
    shutil.copyfile(ROOT/'packaging/fixed_menu_patcher.py',output/'patcher.py')
    for name in ['viv.py','lh2.py','lh2_build.py','str_stream.py','refpack.py','text_tokens.py','font_slot.py']:shutil.copyfile(ROOT/'tools'/name,output/'tools'/name)
    (output/'RUN_F1.bat').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\npy -3 patcher.py\r\nif errorlevel 1 python patcher.py\r\npause\r\n')
    (output/'README-TEST.txt').write_text((ROOT/'packaging/README-F1.txt').read_text(encoding='utf-8'),encoding='utf-8')
    all_entries=index(source)['entries'];targets=[]
    with source.open('rb') as f:
        for i in [2,171,302,752,1096,1437,2095,2102]:
            item=all_entries[i];f.seek(item['offset']);data=f.read(item['size'])
            targets.append(dict(item,kind='text' if i in (752,1437) else 'font' if i==2095 else 'toc',sha256=hashlib.sha256(data).hexdigest()))
    m=dict(version='0.6.1-F1-menu-table-fix',source_size=c['source_size'],source_sha256=c['source_sha256'],output_size=c['source_size'],targets=targets,switch_tested=False)
    spec=importlib.util.spec_from_file_location('fixed',output/'patcher.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    entries,payloads=p.make_resources(source,m)
    _,digest=calculate(source,entries,payloads,'inplace');m['output_sha256']=digest
    m['package_sha256']={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    (output/'manifest-F1.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    (output/'manifest.json').write_text(json.dumps(dict(version=m['version'],switch_tested=False),indent=2))
    build_package(output,Path(str(output)+'.zip'),m['version']);print(digest)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('c_package',type=Path);p.add_argument('font',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.source,a.c_package,a.font,a.output)
