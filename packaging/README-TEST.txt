但丁的地狱 Switch 简体中文实机测试补丁 v0.1

内容：156 条菜单/教程等中文初稿，追加 421 个字形。剧情对话尚未翻译。本版用于验证中文显示、字体映射、换行和资源加载，不是完整汉化版。

一、准备
电脑需安装 Python 3.9 或更新版本（python.org，安装时启用 Tcl/Tk）。本工具运行不需要 pip 或第三方库。
关闭游戏，把 SD 卡连接电脑。确认文件为：switch/dantes-inferno-nx/game/bigfile0.viv。
原文件大小必须为 3,170,839,904 字节。SHA-256 与所有目标条目也会自动核对。不匹配会停止，不会尝试套用。
至少预留约 3.3 GB 空间。bigfile1.viv 不需要替换，NRO、NSP 和存档不变。

二、安装
解压整个补丁 ZIP，保留全部子目录。
Windows 双击“启动补丁工具.bat”，选择 SD 卡上的原始 bigfile0.viv。
保持自动备份安装勾选，点击开始；也可取消勾选，仅生成修改版另存。
工具先校验原版，再复制、追加文本/字库资源、更新索引与长度，校验整份新 VIV。
只有所有校验通过后，才将原版改名为 bigfile0.viv.original.时间.bak，并把新文件改为 bigfile0.viv。不要删除备份。
若使用另存模式，先备份原版，再将生成的 bigfile0_zh_test_v01.viv 改名为 bigfile0.viv 放回 game 目录。
若电脑找不到 Python，请先安装 Python；不要把本 ZIP 当作可直接覆盖 SD 卡的整包。

三、实机测试
游戏语言保持 English；正常使用已有启动程序。
先检查标题/主菜单、Options（选项）、Audio（音频）、字幕开关、亮度与存档界面。
进入游戏检查暂停菜单与操作教程，重点看：中文是否显示、英文是否仍正常、按键图标是否正确、换行/空行是否合理。
请反馈菜单截图、教程截图；如出现方框、字形错误、整段空白、错位或闪退，请同时保留日志。
本环境只做文件结构、资源重读、字形覆盖和整包字节校验，尚未在 Switch 上运行。生成成功不等于实机显示已通过。

四、恢复原版
关闭游戏。把当前 bigfile0.viv 改名为 bigfile0.zh-test.viv；再将同目录本工具生成的 .original.时间.bak 改回 bigfile0.viv。
NRO、NSP 与存档无需改动。不能用其他游戏或其他版本的 VIV 覆盖。

五、命令行（可选）
python patcher.py "原包路径/bigfile0.viv" "同目录/bigfile0_zh_test_v01.viv"
加 --install 可在完整验证后自动备份安装。

字库新增字形来自 Noto Sans SC，采用 SIL Open Font License 1.1；许可见 Licenses/NotoSansSC-OFL.txt。
