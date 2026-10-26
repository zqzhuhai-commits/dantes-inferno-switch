"""Offline D menu checkpoint builder; requires original source and C manifest."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parents[1]/'tools')]
import minimal_font_patcher as runtime
from package_release import build_package

def build(source,c_package,font,output):
    output.mkdir(exist_ok=False);(output/'tools').mkdir();(output/'font').mkdir()
    shutil.copytree(c_package/'Licenses',output/'Licenses')
    root=Path(__file__).resolve().parents[1]
    code=(root/'packaging/minimal_font_patcher.py').read_text().replace("MANIFEST_NAME='manifest-C.json'","MANIFEST_NAME='manifest-D.json'")
    (output/'patcher.py').write_text(code)
    for name in ['viv.py','lh2.py','lh2_build.py','str_stream.py','refpack.py','text_tokens.py','font_slot.py']:
        shutil.copyfile(root/'tools'/name,output/'tools'/name)
    for name in ['font.refpack','texture.refpack','preview.png']:shutil.copyfile(font/name,output/'font'/name)
    (output/'RUN_D.bat').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\npy -3 patcher.py\r\nif errorlevel 1 python patcher.py\r\npause\r\n')
    (output/'README-TEST.txt').write_text('''但丁的地狱 D 主菜单小批汉化 v0.4
C 已收到用户实机反馈：“选项”正常显示。D 新增“开始、继续”，尚待实机验证。
本轮：Options→选项、Start Game→开始、Continue→继续；Continue 后的字面量反斜杠 n 保留。两份全局表各 11 条，共 22 条文本记录。
仅启动菜单字库追加 6 个汉字，原有英文字形和像素保留，512×256 纹理、VIV 大小、索引、STR 区块位置不变。关卡字体尚未修改，进入关卡后的汉字可能缺失；不是全量汉化版。
1. 退出游戏，先把 C 或其他补丁恢复为原版 bigfile0.viv。不能叠加安装。
2. 解压到新目录，电脑安装 Python 3.9+（含 Tk），双击 RUN_D.bat，选择原版 bigfile0.viv。
3. 保持自动备份安装，生成校验完成后启动游戏，语言 English。
4. 测试启动、开始、继续、选项的显示及英文字符；进入/返回菜单是否正常。请保留原版备份。
恢复：退出游戏，将修改版改名，再把 .original.日期.bak 恢复为 bigfile0.viv。
需要约 3.3 GB 输出空间。只接受已校验的原版；全部校验通过后才备份安装。字体许可见 Licenses。
''')
    m=json.loads((c_package/'manifest-C.json').read_text());m.update(mode='D',version='0.4-menu-test',translations={'Options':'选项','Start Game':'开始','Continue':'继续','Continue\\n':'继续\\n'},text_changes_per_resource=11)
    runtime.BASE=output;entries,payloads=runtime.make_resources(source,m)
    h=hashlib.sha256();pos=0
    with source.open('rb') as f:
        while block:=f.read(8*1024*1024):
            changed=bytearray(block)
            for i,payload in payloads.items():
                at=entries[i]['offset'];lo=max(pos,at);hi=min(pos+len(block),at+len(payload))
                if hi>lo:changed[lo-pos:hi-pos]=payload[lo-at:hi-at]
            h.update(changed);pos+=len(block)
    m['output_sha256']=h.hexdigest()
    m['package_sha256']={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    (output/'manifest-D.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    (output/'manifest.json').write_text(json.dumps({'switch_tested':False,'version':'0.4-menu-test'}))
    build_package(output,Path(str(output)+'.zip'),'0.4-menu-test')
    print(json.dumps({'output_sha256':m['output_sha256'],'targets':list(payloads)},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('c_package',type=Path);p.add_argument('font',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.source,a.c_package,a.font,a.output)
