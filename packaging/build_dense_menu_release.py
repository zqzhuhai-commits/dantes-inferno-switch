"""F2: F1 plus all translated button-marked instructions, dense 12px atlas."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packaging'))
from build_numeric_probe_release import build as build_g0
from package_release import build_package,package_files

def build(font,output):
    build_g0(output)
    m=json.loads((output/'manifest-G0.json').read_text());(output/'manifest-G0.json').unlink();(output/'manifest.json').unlink();(output/'RUN_G0.bat').unlink()
    for name in ['font.refpack','texture.refpack','preview.png','font-report.json']:shutil.copyfile(font/name,output/'font'/name)
    (output/'translations/global.zh-CN.fixed-menu.csv').unlink()
    shutil.copyfile(font/'global.zh-CN.menu-controls.csv',output/'translations/global.zh-CN.menu-controls.csv')
    code=(output/'patcher.py').read_text().replace("MANIFEST_NAME='manifest-G0.json'","MANIFEST_NAME='manifest-F2.json'")
    code=code.replace('    from numeric_font_probe import apply_numeric_probe\n','').replace('    payloads=apply_numeric_probe(source,entries,payloads)\n','')
    code=code.replace('global.zh-CN.fixed-menu.csv','global.zh-CN.menu-controls.csv').replace('G0 数字图标通道诊断','F2 菜单与操作说明测试').replace('F1 字库不变；开始/继续/选项临时显示数字图标','F1 菜单 + 按键操作说明；仍为 512×256 原位字库').replace('准备数字字形通道诊断','准备菜单与按键说明')
    (output/'patcher.py').write_text(code)
    (output/'RUN_F2.bat').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\npy -3 patcher.py\r\nif errorlevel 1 python patcher.py\r\npause\r\n')
    (output/'README-TEST.txt').write_text('''但丁的地狱 F2 v0.6.2：菜单与按键操作说明测试

F1 v0.6.1 已由用户确认可以进入游戏、菜单已有汉化。F2 保留 F1 全部 346 条菜单/提示译文，合入已定位到的 85 条含 [b=...] 的操作说明（其中 2 条原已收录），合计每表 429 条 ID，两表共 858 处。按钮标记、颜色、占位符、真实/字面换行逐条校验。
字库共 739 字形，仍用 12px 位图、两倍几何大小、4 级透明度。改用紧凑排布，F1 已有 612 字形逐字像素、大小、字距均相同，仅 UV 位置变化。字体 9390 字节，原槽位容量 9860；纹理 30268 字节，容量 39228。512×256、纹理头、VIV 索引和文件大小、全部 STR 区块位置保持不变。buttons 图标字体完全不改，不使用数字图标探针。

安装：完全退出游戏，恢复同一原版 bigfile0.viv，不能叠加 F1/G0/G1。电脑需 Python 3.9+（含 Tk），解压运行 RUN_F2.bat，选择原版，预留约 3.3 GB。校验成功后才自动备份安装。游戏语言保持 English。
测试：主菜单、选项页、开场教程/按键说明、进入关卡后的暂停菜单、返回主菜单；留意是否缺字、按钮丢失、文字裁切或加载卡住。请提供操作说明截图。
恢复：退出游戏，将 .original.日期.bak 恢复为 bigfile0.viv，或恢复此前保留的 F1。

范围限制：这不是所有菜单和所有非剧情文字的完成版。已收录全部 85 条已定位到的含按键标记说明，但不代表已发现所有操作提示；不含按钮标记的说明和更广的技能/圣物文字尚待继续。剧情、图鉴等不在本轮。
仅启动字体流 2095 替换为新字库；关卡字体流 298 没有改，若运行中使用另一套字库，教程或暂停页仍可能缺字。不能仅凭文本写入即宣称关卡中文可显示。
当前只有原字体样本，没有整份原 VIV；本包未做真实 VIV 端到端生成或实机测试。安装器核对固定原包、原资源及补丁资产，写入前独立计算预期输出哈希，写入后核对整包与各资源。结构与模型验证不等于游戏兼容。NRO/NSP/bigfile1 不改。
''')
    m.update(version='0.6.2-F2-dense-menu-controls',switch_tested=False)
    m['package_sha256']={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in package_files(output)}
    (output/'manifest-F2.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));(output/'manifest.json').write_text(json.dumps(dict(version=m['version'],switch_tested=False)))
    build_package(output,Path(str(output)+'.zip'),m['version']);print('Built F2',str(output)+'.zip')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('font',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.font,a.output)
