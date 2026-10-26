"""Reproducible G0 package from the pinned F1 ZIP; no original game needed."""
import argparse,csv,hashlib,json,shutil,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packaging'))
from package_release import build_package
F1_SHA='a4cf44527bed8eb399d6057468705bf60e6faaa8f0d8b19042316beb126ec578'

def build(output):
    original=ROOT/'checkpoints/Dante-F1-Menu-Fix-v0.6.1.zip'
    if output.exists():raise ValueError('Output directory exists')
    if hashlib.sha256(original.read_bytes()).hexdigest()!=F1_SHA:raise ValueError('Pinned F1 package changed')
    with zipfile.ZipFile(original) as z:
        prefix='Dante-F1-Menu-Fix-v0.6.1/'
        manifest=json.loads(z.read(prefix+'manifest.json'))
        for name,digest in manifest['package_sha256'].items():
            if hashlib.sha256(z.read(prefix+name)).hexdigest()!=digest:raise ValueError('F1 ZIP hash mismatch')
        for item in z.infolist():
            if item.is_dir():continue
            path=Path(item.filename)
            if path.parts[0]!=prefix[:-1] or '..' in path.parts:raise ValueError('Unsafe ZIP member')
            target=output/Path(*path.parts[1:]);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item))
    for name in ('RUN_F1.bat','manifest-F1.json','manifest.json','validation-report.json'):(output/name).unlink()
    for name in ('numeric_font_probe.py','viv_overlay_hash.py','collect_font_evidence.py'):shutil.copyfile(ROOT/'tools'/name,output/'tools'/name)
    code=(output/'patcher.py').read_text()
    old="    notify('准备最小文本诊断',0,1);entries,payloads=make_resources(source,manifest)"
    new="""    notify('准备数字字形通道诊断',0,1);entries,payloads=make_resources(source,manifest)
    from numeric_font_probe import apply_numeric_probe
    from viv_overlay_hash import calculate
    payloads=apply_numeric_probe(source,entries,payloads)
    if cancel():raise ValueError('已取消。原文件未修改。')
    notify('独立计算预期输出校验值',0,1)
    calculated_size,manifest['output_sha256']=calculate(source,entries,payloads,'inplace')
    if calculated_size!=manifest['output_size']:raise ValueError('预期输出大小不匹配')"""
    if code.count(old)!=1:raise ValueError('Unexpected F1 installer version')
    code=code.replace(old,new).replace("MANIFEST_NAME='manifest-F1.json'","MANIFEST_NAME='manifest-G0.json'")
    code=code.replace('F1 v0.6.1','G0 v0.7.0 数字图标诊断').replace('F1 菜单','G0 数字图标诊断')
    code=code.replace('F1 原位菜单修正版','G0 数字图标通道诊断').replace('512×256、原槽位与资源位置不变；仅启动菜单，关卡菜单暂留英文','F1 字库不变；开始/继续/选项临时显示数字图标')
    (output/'patcher.py').write_text(code)
    readme='''但丁的地狱 G0 v0.7.0：第二字库数字标记通道诊断

F1 v0.6.1 已由用户确认可正常进入游戏，菜单有汉化。G0 以仓库中的 F1 包为基线，仅将三个菜单标签暂时改为数字图标标记：
开始游戏 → [b=1]
继续 → [b=37]
选项 → [b=0]
可能显示原有按键图标；出现图标即表示该菜单走到了图标字体通道。空白、方框、原样显示标记均需反馈，不能视为成功。本包没有新增汉字或第三张纹理，不能称为完整扩容方案。

F1 的字体、纹理、其余译文保持原样。原图标字体也完全不改，不占用或替换现有操作图标。数字编号是否被当前构建识别、图标缩放和排版是否正常仍待实机验证。
安装：完全退出游戏，恢复原版 bigfile0.viv，不能叠加 F1。电脑需要 Python 3.9+（含 Tk），解压后运行 RUN_G0.bat，选择原版。预留约 3.3 GB。成功校验后才备份安装。
请拍摄主菜单和一个带操作按键提示的页面；留意三个标签位置是图标、空白还是标记原文，其他中文和操作图标是否正常。恢复时把本次 .original.日期.bak 改回 bigfile0.viv。

当前分析环境没有原版 VIV，本包未做真实 VIV 端到端生成或实机验证。安装器校验固定的原版和 F1 资产，先独立计算预期输出哈希，再复制、原位替换并核对输出整包哈希。此动态哈希用于检查生成一致性，不是独立实机兼容证据。

继续制作中文字库所需的小样本：恢复原版后运行 COLLECT_FONT_EVIDENCE.bat，选择同一原版，生成 Dante-Private-Font-Evidence.zip。只含两套字体资源和校验报告，不含整份游戏，工具不联网。请通过对话提供此私有样本，不要提交公开仓库。
另需上一轮字体加载/绘制分析报告或对应函数片段；当前仓库没有该结果，尚未在本轮复核地址。无需为这一步重传整个游戏包。
'''
    (output/'README-TEST.txt').write_text(readme)
    for name,script in [('RUN_G0.bat','patcher.py'),('COLLECT_FONT_EVIDENCE.bat','tools\\collect_font_evidence.py')]:
        (output/name).write_bytes(('@echo off\r\ncd /d "%~dp0"\r\npy -3 '+script+'\r\nif errorlevel 1 python '+script+'\r\npause\r\n').encode())
    with zipfile.ZipFile(original) as z:m=json.loads(z.read(prefix+'manifest-F1.json'))
    m.update(version='0.7.0-G0-numeric-icon-probe',switch_tested=False,output_sha256_mode='calculated_before_writing',baseline_f1_zip_sha256=hashlib.sha256(original.read_bytes()).hexdigest())
    m.pop('output_sha256');m['package_sha256']={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'manifest-G0.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    (output/'manifest.json').write_text(json.dumps({'version':m['version'],'switch_tested':False}))
    build_package(output,Path(str(output)+'.zip'),m['version'])
    with zipfile.ZipFile(original) as old,zipfile.ZipFile(Path(str(output)+'.zip')) as new:
        for item in old.namelist():
            relative=item[len(prefix):]
            if relative.startswith(('font/','Licenses/','translations/')):
                if old.read(item)!=new.read(output.name+'/'+relative):raise ValueError('F1 baseline asset changed')
    print('Built',Path(str(output)+'.zip'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);build(p.parse_args().output)
