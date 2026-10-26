"""Build F frontend menu package without moving any VIV/STR resource slot."""
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
    (output/'RUN_F.bat').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\npy -3 patcher.py\r\nif errorlevel 1 python patcher.py\r\npause\r\n')
    (output/'README-TEST.txt').write_text('''但丁的地狱 F v0.6 原位启动菜单汉化测试

E v0.5 实机卡在启动加载界面，不要继续叠加 E。本包改用固定尺寸、固定槽位方案。
硬约束：A8 纹理 512×256，tg4h 纹理头完全不改；字体和纹理各一个压缩段，写回原槽位；STR 所有 SHOC 区块的偏移和长度不变；VIV 总长度、索引、全部资源位置不变。只改启动菜单字体流 2095、启动英文全局表 752 和对应 TOC 171/2102。

范围：346 条启动全局文本 ID、280 种菜单/界面标签及常用提示，包括开始、继续、选项、音量、字幕、教程开关、画面、存读档、服装和特典等；同表其他文本保持原文。
关卡英文全局表 1437 和关卡字库 298 不改，暂停、关卡内升级/圣物等仍可能是英文。这不是所有菜单均已汉化的版本。关卡 FONT 压缩槽仅 2,940 字节，本字库无法在不移动资源的条件下写入。其他文本保留 E 译稿，后续再研究方案，不在本包中强行扩大字库。

为了容纳菜单汉字，重新排列原有全部字符与新增汉字，共 612 字形。字体改为 Noto Sans SC，12 像素栅格配合两倍字形几何度量，4 级透明度；因此英文风格和抗锯齿也会变化，中文是否清晰、显示尺寸和排版都需实机确认。此方案保持纹理尺寸与资源位置，不承诺保留旧字形记录或旧纹理像素。

安装：退出游戏，恢复原版 bigfile0.viv，不可叠加任何测试包。电脑安装 Python 3.9+（含 Tk）。解压到新目录，运行 RUN_F.bat，选择原版，预留约 3.3 GB 输出空间。全部校验通过后才备份安装。游戏语言保持 English。
测试：能否过加载到主菜单；开始/继续/选项是否显示；选项内音量、字幕、教程、画面和返回按钮；存读档及返回标题。请反馈有无缺字、模糊、大小异常或裁切。
若卡住或显示异常，退出游戏，将 F 资源改名，恢复 .original.日期.bak 为 bigfile0.viv。无需改动 NRO/NSP/bigfile1 或存档。

本包未实机验证，是按固定尺寸及位置要求制作的候选版本，不能称为已修复。字体许可见 Licenses。
''',encoding='utf-8')
    targets=[t for t in c['targets'] if t['index'] in (171,752,2095,2102)]
    m=dict(version='0.6-F-fixed-menu-test',source_size=c['source_size'],source_sha256=c['source_sha256'],output_size=c['source_size'],targets=targets,switch_tested=False)
    spec=importlib.util.spec_from_file_location('fixed',output/'patcher.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    entries,payloads=p.make_resources(source,m)
    _,digest=calculate(source,entries,payloads,'inplace');m['output_sha256']=digest
    m['package_sha256']={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    (output/'manifest-F.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    (output/'manifest.json').write_text(json.dumps(dict(version=m['version'],switch_tested=False),indent=2))
    build_package(output,Path(str(output)+'.zip'),m['version']);print(digest)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('c_package',type=Path);p.add_argument('font',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.source,a.c_package,a.font,a.output)
