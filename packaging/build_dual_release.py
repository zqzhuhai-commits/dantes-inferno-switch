"""Package G2 dual-font coverage; original VIV is checked at installation."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packaging'))
from build_numeric_probe_release import build as build_g0
from package_release import build_package,package_files

def build(assets,output):
    build_g0(output);m=json.loads((output/'manifest-G0.json').read_text());(output/'manifest-G0.json').unlink();(output/'manifest.json').unlink();(output/'RUN_G0.bat').unlink()
    shutil.copytree(assets,output/'dual')
    for name in ('dual_text.py','dual_resources.py','str_compressed.py','lh2_build.py'):shutil.copyfile(ROOT/'tools'/name,output/'tools'/name)
    code=(output/'patcher.py').read_text().replace("MANIFEST_NAME='manifest-G0.json'","MANIFEST_NAME='manifest-G2.json'")
    start=code.index('def make_resources(source,manifest):');end=code.index('\n\ndef apply(',start)
    code=code[:start]+"def make_resources(source,manifest):\n    from dual_resources import make_resources as make_dual\n    return make_dual(source,manifest,BASE)\n"+code[end:]
    code=code.replace('    from numeric_font_probe import apply_numeric_probe\n','').replace('    payloads=apply_numeric_probe(source,entries,payloads)\n','')
    code=code.replace('G0 数字图标通道诊断','G2.1 双字库读取修正版').replace('F1 字库不变；开始/继续/选项临时显示数字图标','自动选择可装入原资源总容量的最大双字库方案').replace('准备数字字形通道诊断','构建双字库和非字幕译文')
    (output/'patcher.py').write_text(code);(output/'RUN_G2.bat').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\npy -3 patcher.py\r\nif errorlevel 1 python patcher.py\r\npause\r\n')
    m['targets'].append(dict(index=298,offset=1569507328,size=26869760,key='25c2710d',sha256='20971f33f1d08e743fc839a207633b8016a29164b5fe5a99d0226835535caa0d',kind='font'))
    m.update(version='0.8.1-G2.1-multiblock-fix',switch_tested=False)
    overview=json.loads((assets/'variants.json').read_text());largest=overview['variants'][-1]
    (output/'README-TEST.txt').write_text(f'''但丁的地狱 G2.1 v0.8.1 多块字体读取修正版

修复 G2 的 Expected one original font body 错误：合法多数据块字体资源会走受校验的原条目内重排路径；并非忽略容量或结构校验。
用户已确认 G0 可进入游戏，菜单数字标记变为按键图标。本包按要求直接扩大实际译文覆盖，不是两字探针。
普通字库 {overview['normal_glyphs']} 字形；第二字库最多追加 {largest['supplemental_glyphs']} 个汉字，原 38 个按键图标的记录与像素保留。两张纹理均保持 512×256，纹理头不变，按钮、颜色、占位符和换行先按人类译稿严格校验，再将溢出字编译为数字图标标记，并做反向还原验证。
最大方案每表 {largest['translated_ids_per_table']} 条译文，两份表共 {largest['translated_ids_per_table']*2} 处。保留 F1 菜单，包含已定位的全部 85 条带按钮标记的说明，进一步纳入可覆盖的技能/圣物/系统提示/其他非字幕文字。目标译稿共 {overview['target_ids']} 条，未覆盖条目明确列在 dual/62/plan.json 的 deferred 中，不会伪称全量完成；其余原文保留。对话字幕表 942 不改。
启动和关卡两个字体流都更新。能装入旧压缩槽位则原位写入；否则只在各自原 STR 条目总容量内重排压缩块，严格保留其他资源区块字节及顺序。VIV 索引、条目位置和长度、文件总大小保持原样。TOC 同步更新两套字体流和两份文本表的解码长度。
安装时从最大方案开始，选择实际能装入两套原 STR 总容量的版本；若较大方案不适配，会尝试较小字符集。实际选用方案和译文数量见 G2-build-report.json，stage=resource_preflight_only 表示报告仅记录资源准备，不代表游戏验证完成。

安装：退出游戏，恢复同一原版 bigfile0.viv，不能叠加 F1/F2/G0/G1。电脑需 Python 3.9+（含 Tk），解压运行 RUN_G2.bat，选择原版，预留约 3.3 GB。所有源包、补丁资产、输出整包与资源检查通过后才自动备份安装。保持游戏 English。
检查主菜单、选项、操作教程、关卡暂停/技能/圣物菜单和返回主菜单；留意汉字大小/混排/裁切、按钮图标、换行，以及关卡加载。恢复时将 .original.日期.bak 改回 bigfile0.viv。

没有新增第三张纹理或修改 NRO。新增数字汉字混排和 STR 内部重排尚未经过本轮实机验证。当前只有字体小样本，没有完整原 VIV，未做真实 VIV 端到端生成；工具在安装时核对固定原包/资源、独立预计算输出哈希，再核对完整输出。不能把静态与模型检查当作实机通过。
字体来源 Noto Sans SC，许可见 Licenses。原始私有字体样本不在此包中。
''')
    # Drop obsolete F1-only assets and rows; the dual directory is authoritative.
    shutil.rmtree(output/'font');shutil.rmtree(output/'translations')
    m['package_sha256']={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in package_files(output)}
    (output/'manifest-G2.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));(output/'manifest.json').write_text(json.dumps(dict(version=m['version'],switch_tested=False)))
    build_package(output,Path(str(output)+'.zip'),m['version']);print('Built',str(output)+'.zip')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('assets',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.assets,a.output)
