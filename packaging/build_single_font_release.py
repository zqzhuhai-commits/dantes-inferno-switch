"""F3: dense single-font expansion, fixed startup slots, original level font."""
import csv,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'packaging')]
from build_dense_menu_font import build as build_font,selected_rows
from build_dense_menu_release import build as build_f2
from package_release import build_package,package_files
from text_tokens import TOKENS,validate
from PIL import Image
EXTRA=[31649,32599,38463,20182,29702,26354,26415,28145,24072,36523,27515,36861,30417,29238,23041,32654,20891,31185,36807,25102,35745,32822,36138,26263,37324,31471,24322,20146,23548,27807,24207,25351]
README='''但丁的地狱 F3 v0.6.3：单字库紧凑扩展版

针对 G2.1 能进菜单、开始游戏读条卡死的实机反馈，回到 F1/F2 的原位写入路线。只改启动流 2095 的 minion_pro 普通字库；buttons 字库和关卡字体流 298 完全保留原版，不执行 STR 重排，不追加资源。读条卡死的确切根因仍未确定，本包尚待实机验证。

普通字库 771 字形，512×256，12px、两倍几何大小、4 级透明度。按字形高度/宽度排序、紧凑分行排布；原 F1 字形的像素和字距保持一致。字体压缩 9728/9860 字节，纹理 31612/39228 字节。剩余纹理空间不等于可用字数：字体记录及 Unicode 查找页也占用压缩槽位。
每份英文表收录 906 条非字幕译文，两份合计 1812 处；包括已有菜单和全部已定位的 85 条带按键标记说明。非剧情目标共 1664 条，尚有 758 条未收录。保留按键、颜色、占位符及换行，不用 [b=数字] 承载中文。字幕和剧情不改。

请完全退出游戏，恢复原版 bigfile0.viv，不能叠加 G2.1 或其他补丁。解压运行 RUN_F3.bat，选择原版；需 Python 3.9+（含 Tk）及约 3.3GB 空间。成功校验后备份安装，语言设为 English。优先测试开始新游戏/继续存档是否完成读条，再检查教程和暂停页。
恢复：退出游戏，将本次 .original.日期.bak 恢复为 bigfile0.viv。

限制：为隔离关卡流修改，本版不改 298，进入关卡后若游戏切换到原版字体，新增中文可能缺字；906 是写入覆盖数，并非已实机确认的显示数。当前工作环境没有完整原版 VIV，未做真实整包生成和实机验证。NRO/NSP/bigfile1 不改。
'''

def build(sample,ttf,output):
    core=selected_rows(ROOT)
    inf,atlas,ci,ca,report=build_font(sample.read_bytes(),ttf,[r['translation'] for r in core]+[''.join(map(chr,EXTRA))])
    import struct
    cps={int.from_bytes(inf[0x454+i*24:0x456+i*24],'little') for i in range(report['glyphs'])}
    with (ROOT/'translations/global.zh-CN.nonstory.csv').open(encoding='utf-8-sig',newline='') as f:rows={r['id']:r for r in csv.DictReader(f)}
    rows.update({r['id']:r for r in core})
    accepted=[r for r in rows.values() if set(map(ord,TOKENS.sub('',r['translation'])))<=cps]
    for r in accepted:validate(r['source'],r['translation'])
    accepted.sort(key=lambda r:r['id'])
    report.update(translated_ids_per_table=len(accepted),target_nonstory_ids=len(rows),deferred_ids=len(rows)-len(accepted),level_font_modified=False,icon_font_modified=False)
    assets=output.parent/(output.name+'-assets');assets.mkdir(exist_ok=False)
    (assets/'font.refpack').write_bytes(ci);(assets/'texture.refpack').write_bytes(ca)
    Image.frombytes('L',(512,256),atlas).save(assets/'preview.png')
    (assets/'font-report.json').write_text(json.dumps(report,indent=2))
    with (assets/'global.zh-CN.menu-controls.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['id','source','translation','status']);w.writeheader();w.writerows(accepted)
    build_f2(assets,output)
    m=json.loads((output/'manifest-F2.json').read_text());(output/'manifest-F2.json').unlink();(output/'manifest.json').unlink();(output/'RUN_F2.bat').unlink()
    code=(output/'patcher.py').read_text().replace('manifest-F2.json','manifest-F3.json').replace('F2 菜单与操作说明测试','F3 单字库紧凑扩展').replace('F1 菜单 + 按键操作说明；仍为 512×256 原位字库','单字库 771 字形，906 条译文；关卡字库保持原版')
    code=code.replace('from str_stream import reflow,unpack_selected','from str_stream import unpack_selected').replace('诊断包生成成功，请测试能否进入主菜单','F3 补丁生成成功，请测试进入关卡及教程')
    (output/'patcher.py').write_text(code)
    (output/'RUN_F3.bat').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\npy -3 patcher.py\r\nif errorlevel 1 python patcher.py\r\npause\r\n')
    (output/'README-TEST.txt').write_text(README)
    m.update(version='0.6.3-F3-single-font-dense',switch_tested=False)
    assert 298 not in [t['index'] for t in m['targets']]
    m['package_sha256']={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in package_files(output)}
    (output/'manifest-F3.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));(output/'manifest.json').write_text(json.dumps(dict(version=m['version'],switch_tested=False)))
    build_package(output,Path(str(output)+'.zip'),m['version']);print(json.dumps(report))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('sample',type=Path);p.add_argument('ttf',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.sample,a.ttf,a.output)
