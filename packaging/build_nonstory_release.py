"""Build E non-story text/font package from the verified original VIV.

Runtime is standard-library only. Pillow and fontTools are build dependencies.
"""
import argparse,csv,hashlib,importlib.util,json,shutil,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'packaging')]
from viv import index
from str_stream import unpack_selected
from build_font import build as build_font
from refpack import compress,decompress
from text_tokens import TOKENS,validate
from package_release import build_package


def build(source,ttf,c_package,output):
    source,ttf,c_package,output=map(Path,(source,ttf,c_package,output))
    if output.exists() or Path(str(output)+'.zip').exists():raise ValueError('Output exists')
    expected='8e6035b2c03a12bb7492209776cd877176849cc2aa3362d29130e310326e0d4c'
    h=hashlib.sha256()
    with source.open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    if h.hexdigest()!=expected:raise ValueError('Original VIV checksum mismatch')
    entries=index(source)['entries'];targets=[];raw={}
    with source.open('rb') as f:
        for i in [2,171,298,302,752,1096,1437,2095,2102]:
            e=entries[i];f.seek(e['offset']);raw[i]=f.read(e['size'])
            targets.append(dict(e,sha256=hashlib.sha256(raw[i]).hexdigest(),kind='font' if i in [298,2095] else 'text' if i in [752,1437] else 'toc'))
    # TOC root decoded-size values connect the two global font streams.
    root_sizes={struct.unpack_from('>I',raw[i],20)[0] for i in [2,171,302,1096,2102]}
    for target in targets:
        if target['kind']=='font':
            # Derive the decoded aggregate from SHDR lengths, as stored in TOCs.
            from str_stream import chunks
            size=sum(struct.unpack_from('>I',c,40)[0] for _,c in chunks(raw[target['index']]) if c[8:12]==b'SHDR')
            if size not in root_sizes:raise ValueError('Font stream root size not found in TOC')
            target['decoded_size']=size
    output.mkdir();(output/'tools').mkdir();(output/'font').mkdir();(output/'translations').mkdir()
    names=['minion_pro.inf','minion_pro.tg4d','minion_pro.tg4h']
    paths=['shared\\fonts\\'+n for n in names]
    original=unpack_selected(raw[2095],paths)
    other=unpack_selected(raw[298],paths)
    if other!=original:raise ValueError('Gameplay and frontend font sources differ')
    table=ROOT/'translations/global.zh-CN.nonstory.csv'
    with table.open(encoding='utf-8-sig',newline='') as f:translations=list(csv.DictReader(f))
    chars=set()
    for r in translations:
        validate(r['source'],r['translation']);chars.update(TOKENS.sub('',r['translation']))
    inf,atlas,header,preview,font_report=build_font(original[paths[0]],original[paths[1]],original[paths[2]],ttf,chars,atlas_width=1024)
    # The original top-left bitmap and all original records must survive expansion.
    from PIL import Image
    if preview.crop((0,0,512,256)).tobytes()!=original[paths[1]]:raise ValueError('Original pixels changed')
    preview.save(output/'font/preview.png')
    config={}
    for name,data in zip(names,[inf,atlas,header]):
        config[name]=[]
        # Each packet uses at most 128 KiB decoded bytes. Multiple Rpak chunks
        # are a new compatibility surface; E must be validated on hardware.
        for i,at in enumerate(range(0,len(data),128*1024)):
            packet=compress(data[at:at+128*1024]);file=f'{name}.{i:03d}.refpack'
            if len(packet)+16>128*1024:raise ValueError('Compressed packet capacity exceeded')
            (output/'font'/file).write_bytes(packet);config[name].append(file)
    (output/'font/packets.json').write_text(json.dumps(config,indent=2))
    shutil.copyfile(table,output/'translations'/table.name)
    shutil.copytree(c_package/'Licenses',output/'Licenses')
    shutil.copyfile(ROOT/'packaging/nonstory_patcher.py',output/'patcher.py')
    for name in ['viv.py','lh2.py','lh2_build.py','str_stream.py','str_compressed.py','refpack.py','text_tokens.py']:
        shutil.copyfile(ROOT/'tools'/name,output/'tools'/name)
    (output/'RUN_E.bat').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\npy -3 patcher.py\r\nif errorlevel 1 python patcher.py\r\npause\r\n')
    (output/'README-TEST.txt').write_text('''但丁的地狱 E v0.5 非剧情文字汉化测试包

基于 D v0.4 的源码与文本格式，扩大非剧情文字覆盖。包括主菜单、选项、存档提示、教程、招式、魔法、圣物及说明、挑战、关卡名、怪物和亡魂图鉴介绍、制作人员职务等。
剧情对白与访谈字幕表完全不改；诗文、维吉尔叙事与但丁生平年表暂保留原文。工作人员真实姓名、公司/作品专名、版权标识、内部 Credits_ 键、数字和原版未知控制标记按原样保留。

重要：C 只有最小字库实机通过；D、E 未在本次环境实机验证。E 的扩展贴图及多段压缩字体流是新方案，不能视为 C/D 原槽位方案已经覆盖验证。请先备份再测试。不是全剧情汉化，也不是实机通过的正式版。

使用方法：
1. 完全退出游戏。恢复本游戏对应的原版 bigfile0.viv，不能在 A/B/C/D/E 上叠加。
2. 电脑安装 Python 3.9+（含 Tk）。本安装器只使用 Python 标准库。
3. 解压本包，双击 RUN_E.bat，选择原版 bigfile0.viv。预留至少 3.4 GB 输出空间。
4. 生成并通过整包校验后才备份安装，游戏内保持 English。
5. 测试主菜单、选项、教程、升级/圣物界面、关卡内暂停菜单，以及保存/读取、返回标题。查看有无空白、乱码、裁切或卡加载。
6. 如不能启动，退出游戏，将 E 资源改名，恢复 .original.日期.bak 为 bigfile0.viv。不要删除原版备份。

范围：仅 bigfile0.viv，两份英文全局表、两份字体流及五份对应 TOC；不修改 bigfile1、对白表、NRO、NSP、存档。
采用 1024×2048 A8 贴图，保留原英文字形记录和原纹理区域。资源放入 VIV 末尾并更新其索引，TOC 同步解码长度。以上结构变化都仍需实机验证。
字体：Noto Sans SC，SIL OFL 许可见 Licenses。
''',encoding='utf-8')
    m=dict(source_size=source.stat().st_size,source_sha256=expected,targets=targets,translation_files=['translations/'+table.name],version='0.5-E-nonstory-test',switch_tested=False)
    spec=importlib.util.spec_from_file_location('e_runtime',output/'patcher.py');runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
    _,payloads=runtime.make_resources(source,m)
    # Calculate the complete expected file independently of runtime.apply.
    locations={};end=source.stat().st_size
    for i in sorted(payloads):
        end=(end+2047)&~2047;locations[i]=end;end+=(len(payloads[i])+2047)&~2047
    h=hashlib.sha256();pos=0
    with source.open('rb') as f:
        while block:=f.read(8*1024*1024):
            if pos==0:
                block=bytearray(block);struct.pack_into('<I',block,4,end)
                for i,at in locations.items():struct.pack_into('>II',block,16+12*i,at,(len(payloads[i])+2047)&~2047)
            h.update(block);pos+=len(block)
    for i in sorted(payloads):
        h.update(bytes(locations[i]-pos));h.update(payloads[i]);pos=locations[i]+len(payloads[i]);padding=(-pos)%2048;h.update(bytes(padding));pos+=padding
    if pos!=end:raise ValueError('Output size calculation mismatch')
    m.update(output_size=end,output_sha256=h.hexdigest(),font_report=font_report,translated_rows=len(translations))
    m['package_sha256']={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    (output/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    build_package(output,Path(str(output)+'.zip'),'0.5-E-nonstory-test')
    print(json.dumps({k:m[k] for k in ['translated_rows','output_size','output_sha256','font_report']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('ttf',type=Path);p.add_argument('c_package',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.source,a.ttf,a.c_package,a.output)
