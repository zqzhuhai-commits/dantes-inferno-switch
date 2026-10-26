# 但丁的地狱 Switch 简体中文汉化

## 当前进度下载

- [D v0.4 主菜单小批汉化测试包](checkpoints/Dante-Menu-D-v0.4.zip)：开始、继续、选项，共 22 条菜单记录；待实机验证。先恢复原版，再运行 RUN_D.bat。
- [C v0.3 最小主菜单字库测试包](checkpoints/Dante-Minimal-Font-C-v0.3.zip)：用户已确认“选项”正常显示。
- [A/B v0.2 启动诊断包](checkpoints/Dante-Startup-Diagnostic-v0.2.zip)：A 实机可进游戏且文字生效；B 实机可进游戏但中文为空白。
- [进度快照与下一步](checkpoints/PROGRESS.md) · [下载文件 SHA-256](checkpoints/SHA256SUMS.txt)

当前推荐测试 D v0.4；C 已确认显示正常。下方 v0.1–v0.3 章节保留开发历史，最新结果以进度快照为准。这是部分汉化测试包。原游戏包未上传。


目标：为用户本地原版资源制作简体中文文本与字库补丁。

## 当前进度（2026-10-26）

**实机问题：用户反馈 v0.1.1 在刚启动时黑屏转圈，无法进入主菜单。原因尚未确认；v0.1/v0.1.1 不能视为可运行汉化。请恢复原版，使用下方 v0.2 隔离诊断。**

已用用户本次游戏包验证 VIV 索引，导出英文全局表 3,310 条与对话表 1,852 条，共 5,162 条记录。已有 156 条全局菜单、教程与提示中文初稿；已完成固定条目长度的实验性文本回封与再解析。已制作 v0.1 实机测试工具包，完整 VIV 副本安装与整包校验通过；尚未进行游戏内或实机验证。测试版包含 156 条译文，剧情表尚未翻译。

- 已只读验证 bigfile0.viv 的 2,151 个条目、bigfile1.viv 的 3,724 个条目；所有条目的偏移与长度均在原包范围内。
- 已在 bigfile0.viv 定位 frontend 文本索引及字体路径。
- 外层 frontend_global.str、frontend_global.toc、frontend.toc 与原包对应资源 SHA-256 比对相同，不是已完成的汉化。
- 已在 bigfile0.viv 找到英文 inferno_global.en.lh2 与 inferno_dialog.en.lh2；对话表也包含制作花絮访谈等内容，尚未逐场景确认剧情字幕覆盖范围，不能认定只修改 bigfile0.viv 即可完成全游戏汉化。

## 已确认资源

| 资源 | 位置 / 说明 |
| --- | --- |
| frontend_global.toc | bigfile0 条目 171，偏移 1341638656，2048 字节 |
| frontend_global.str | bigfile0 条目 2095，偏移 1341640704，23986176 字节 |
| frontend.toc | bigfile0 条目 2102，偏移 1365626880，2048 字节 |
| frontend text 引用 | 45a95900、565b7b2c、693a4da8、79ec6fd4、87f9943c、98abb668、d99beb3c、e00af020、ea4e0d68、f0bd124c |
| 字体路径 | shared/fonts/minion_pro.tg4h、minion_pro.tg4d、minion_pro.inf |
| 语言引用 | levels/frontend/frontend/text/localereftable549004a0.txt、localereftable9c0fc174.txt |

上述 text 标识来自内部 TOC，不应直接视为 VIV 外层索引键。字体路径为容器内部引用，其格式及中文字形映射仍需解析。

## 工具

`tools/viv.py` 使用 Python 标准库，只读解析本地样本的 BIGH 变体：16 字节包头；本次完整原包证实包头文件长度为小端 uint32，条目数量/目录边界及每条 offset、size、key 为大端 uint32。key 为不透明标识，尚未验证哈希算法。工具校验目录与数据范围，提取时拒绝覆盖已有输出。新增批量提取、逐字节校验与多编码原文定位，使用 Python 3.9+，无需第三方依赖。

```powershell
python tools/viv.py "本地路径/bigfile0.viv" --output "local/bigfile0-index.json"
python tools/viv.py "本地路径/bigfile0.viv" --extract 2095 --output "local/frontend_global.str"
```

条目编号从 0 开始。当前工具不支持修改、回封或压缩数据解码，也不代表适用于所有 BIGH 文件。

### 游戏包到位后的操作

```powershell
# 批量提取：输出目录必须尚不存在；使用编号与 key 命名，不推测原始文件名
python tools/viv.py "local/bigfile0.viv" --extract-all --output "local/bigfile0-unpacked"
python tools/viv.py "local/bigfile1.viv" --extract-all --output "local/bigfile1-unpacked"

# 对照原包逐条检查元数据、提取文件内容及 SHA-256
python tools/viv.py "local/bigfile0.viv" --verify "local/bigfile0-unpacked/manifest.json"

# 定位未压缩资源内的已知路径或文本；输出为 JSON Lines，含包内与条目内偏移
python tools/viv.py "local/bigfile0.viv" --find "minion_pro" --output "local/font-hits.jsonl"
python tools/viv.py "local/bigfile0.viv" --find "Continue" --encoding utf-16-be --output "local/text-hits.jsonl"
```

- `manifest.json` 记录每个条目的编号、key、偏移、大小、提取文件名与 SHA-256。
- 单条与批量提取均以二进制原样复制，不改变压缩内容；路径引用仅作线索，不用于创建文件路径。
- 包头 declared size 与实际大小不一致、条目重叠会记入 warnings。其语义未确认，不自动修复；越界条目则拒绝解析。
- 批量任务中断可能留下已完成条目，但不会生成成功清单；重新执行请使用新目录。单条复制失败会删除该次未完成文件。
- 搜索支持 ASCII、UTF-8、UTF-16 LE/BE，按条目流式处理；搜不到不能证明不存在文本，压缩或专用编码仍需解析。
- 已在本次原包验证 2,151 + 3,724 个 VIV 条目范围，并提取英文文本样本；批量提取/清单校验的完整流程仍仅通过模拟包测试。已完成有限布局的实验性文本条目回封，已另行制作测试字库和原包安装工具，实际中文渲染仍待实机验证。

### 工具测试

```powershell
python -m unittest discover -s tests -v
```

测试覆盖原样提取与校验、空条目、内容篡改、源包变更、拒绝覆盖、非法包头与越界、跨读取区块搜索、UTF-16 定位、清单路径检查和失败后的残留清理。模拟包不包含游戏资源。

## 后续工作

1. 扩展已验证的 ols3/SHOC/2HCL 文本解析，核对其余资源与不同场景副本。
2. 确认剧情字幕、菜单、物品说明等文本覆盖范围。
3. 继续补全翻译表与术语表，复核首批初稿，保留占位符和控制码。
4. 解析字体纹理、字符映射与排版参数，制作中文字库。
5. 生成可复现补丁，在资源副本上验证回封，再进行实机测试。

仓库只保存工具、格式说明与汉化工作成果。原版 VIV、XEX、NSP、提取的完整资源和本地扫描清单不上传。

## 本次文本解析成果

`tools/lh2.py` 只读解析已观察的 `ols3 → SHOC/SDAT → 2HCL` 单语言 UTF-8 表，不提供写入或回封。先用 VIV 工具提取条目，再导出 CSV。输出使用 UTF-8 BOM，包含 id、条目内 offset、source、translation；现有输出不会覆盖。

```powershell
python tools/viv.py "local/bigfile0.viv" --extract 752 --output "local/global-entry.bin"
python tools/lh2.py "local/global-entry.bin" --output "local/inferno_global.en.csv"
python tools/viv.py "local/bigfile0.viv" --extract 942 --output "local/dialog-entry.bin"
python tools/lh2.py "local/dialog-entry.bin" --output "local/inferno_dialog.en.csv"
```

本次编号适用于用户提供的资源版本，其他版本必须重新核对。解析器检查容器/区块边界、表大小、ID 严格递增、字符串偏移与终止符，不猜测未知布局。

| 条目 | 内部路径 | 记录数 | 提取条目 SHA-256 |
| --- | --- | ---: | --- |
| 752 | localization/inferno/inferno_global.en.lh2 | 3310 | 23dc9401f49c2f01ef5e9a42d34ff89f9278238cbe485a14199f9475cf7935a1 |
| 1437 | 同上，另一个场景副本 | 3310 | 与 752 相同 |
| 942 | localization/inferno/inferno_dialog.en.lh2 | 1852 | c53d56c75ba8a9471b5c7558f3115393ee0b9f8193ba2af3efbc7d158ee11c92 |

以上两种表中所有记录均已严格 UTF-8 解码，ID 在各表内唯一；两张表的 ID 仍应分别管理，不能假设跨表唯一。完整原文导出保留于本地，不上传完整原版资源。

首批翻译位于 `translations/global.zh-CN.menu.csv`：84 条记录、59 种原文，状态均为 draft；重复菜单项按各自 ID 保留，已核对 ID/原文及控制符。此文件是待复核翻译，不能直接复制到游戏目录使用。

字体进度：frontend_global.str 内的 minion_pro.inf 对应 SDAT/FONT，minion_pro.tg4d 对应 Rpak。`tools/refpack.py` 已将此 Rpak 中的 10fb 数据解码为 131,072 字节纹理数据。FONT 头给出 194 条记录、起始偏移 0x454，边界 0x1684 与每条 24 字节相符；Unicode 字符映射、纹理布局和中文渲染仍待确认。

## 特殊符号保护与实验性回封

`tools/text_tokens.py` 对译文执行保守检查：

- `%1`、`%2`、printf 格式、`%`、`{s}`、`{n}`、未知方括号/花括号/尖括号内容均按原始大小写和顺序保留。
- `[b=RDUp]`、`[b=Lstick]` 等按钮标记不会改写为另一种大小写或按键名称；颜色标记同样不翻译。
- 字面量 `\n` 与实际 LF、CR、CRLF 分别检查，连续空行数量不得改变，标记不得跨越换行移动。
- 保留 0x1e、0x1f、NBSP、不换行/零宽字符等；禁止在译文中插入 NUL 终止符。不调用 strip、Unicode 归一化或转义解码。

新增 `translations/global.zh-CN.tutorial.csv`：72 条教程、存档提示与章节引文初稿。与菜单表共计 156 条，均通过完整特殊符号校验，尚待游戏语境和排版复核。

`tools/lh2_build.py` 是实验性条目重建器，只接受已观察的 SHDR → SDAT/2HCL → FILL 布局。校验 ID、原文及控制符后重算字符串偏移、2HCL/SHDR 长度与 FILL，在固定条目容量内重新解析验证；容量不足、来源不匹配或符号改变时拒绝输出。空译文表示未翻译，禁止隐式删除。该工具不修改 VIV、字体或原始输入。

```powershell
python tools/lh2_build.py "local/global-entry.bin" "translations/global.zh-CN.menu.csv" --output "local/global-zh-experimental.bin"
```

真实样本验证：合并 156 条译文后，条目仍为 131,072 字节，重新导出的所有 ID 与译文一致，未翻译记录原文不变。此结果只证明工具内部的字节与结构检查通过；尚未验证游戏加载器对实验文件的接受情况，不能当作可安装补丁。26 项自动测试覆盖解析、解码、回封容量及控制符错误等情况。

## v0.1 实机测试包（2026-10-26）

本轮新增 `tools/build_font.py`、`tools/str_stream.py` 和 `packaging/patcher.py`。安装流程参考 [DeadSpace2-Switch-Xbox360 v0.4](https://github.com/zqzhuhai-commits/DeadSpace2-Switch-Xbox360/tree/main/current/v0.4)：核对原资源、复制 VIV、追加新资源、更新索引/总长度，成功验证后才备份安装。

- 字库原有 194 个字形与像素/度量保持不变；新增 421 个 Unicode 字形，合计 615 个。原纹理已确认为 512×256 的线性 A8，扩展为 512×1024。新字形采用 Noto Sans SC Medium，并附 SIL OFL 许可。
- FONT 字符码为 UTF-16 LE 单码元，度量/坐标字段为大端；新增字形重新分配对应 Unicode 页的运行时查找存储。完整字符映射仍需通过游戏加载验证。
- 同步更新两个字体流（条目 298、2095）、两份英文全局表（752、1437）及五份相关 TOC（2、171、302、1096、2102）；仅修改 bigfile0.viv，bigfile1/NRO/NSP/存档不变。
- STR 按 128 KiB 包边界重新排布，新增字库使用未压缩 SDAT 分块；验证每个区块不跨包，且重新提取后的三项字体资源与生成输入逐字节一致。
- 标准库 Python 图形安装器包含原包/目标资源/补丁资产/输出整包 SHA-256 校验、另存模式、取消、自动备份安装与失败清理。电脑需要 Python 3.9+（含 Tk），运行安装器不需要第三方依赖。
- 测试用补丁不包含原版 VIV 或 NRO；在用户电脑上从其原包重建需要的资源。

| 验证项 | 结果 |
| --- | --- |
| 原包长度 | 3,170,839,904 字节 |
| 原包 SHA-256 | 8e6035b2c03a12bb7492209776cd877176849cc2aa3362d29130e310326e0d4c |
| 输出长度 | 3,223,353,344 字节 |
| 输出 SHA-256 | 700ede90a4680aad45d310ac82e2db3bac976642f5fa32ad8f283bc7a5a84f2e |
| 完整原包副本端到端生成、整包校验、9 项资源重读 | 通过 |
| 615 字形尺寸、UV 边界及译文字形覆盖 | 通过 |
| 自动测试 | 33 项通过，含模拟包备份安装与失败清理 |
| Windows 图形界面运行、Switch 中文显示与稳定性 | 尚未验证 |

下载包内附测试步骤与还原说明。v0.1 是部分文本及字库验证包，不能称为完整汉化或实机通过版。原版备份请保留。

## v0.1.1 工具修复

修复用户截图中的 `FileNotFoundError: __pycache__/patcher.cpython-312.pyc`。v0.1 的临时打包脚本误把 Python 缓存写入清单，但 ZIP 排除了这些文件，导致原包修改前的资产检查失败。这是打包缺陷，与 VIV 资源不匹配无关。

`packaging/package_release.py` 现在使用同一文件列表生成校验清单与 ZIP，排除所有层级的 `__pycache__`、`.pyc`、`.pyo`，并直接校验 ZIP 中每项文件的哈希。新增回归测试验证：包含不同 Python 版本缓存的工作目录，打包后在完全无缓存的新目录仍能通过全部资产检查。自动测试总计 35 项。v0.1.1 汉化资源及目标 VIV 输出哈希与 v0.1 相同。

## v0.2 启动卡住隔离诊断

用户反馈：打补丁后刚打开游戏，停在黑屏加载页，右下角旋转图标持续转动。此前文件结构和自建解析器校验不足以证明游戏加载器兼容，根因目前未确定。

`packaging/diagnostic_patcher.py` 复用原包校验、复制、输出整包验证与自动备份流程，但只在两个原始英文全局表的字符串槽位内修改 6 个 Options 标签。不更新 VIV 索引、文件长度、TOC 或 STR，不更改字库，不追加资源。

- A：Options → TEST-A!，7 字节原位替换，验证最低限度的英文文本修改。
- B：Options → 选项，6 字节 UTF-8 加零填充，保留全部字符串偏移、表长度及原字库。可能出现缺字，重点观察是否能够加载。
- 两版均只接受已核对的原版 VIV，禁止叠加到 v0.1.1 或彼此叠加。先恢复原版确认可启动，再只测试 A；A 正常后才在原版上测试 B。
- A/B 都已从干净 ZIP 完整生成 3,170,839,904 字节 VIV 并通过预计算整包哈希校验；36 项自动测试通过。此结果仍不是 Switch 实机通过。

A 输出 SHA-256：`7dd9ee70b9c414467eb4e40594a0056f9fb530911648997a7e698fae5b93f3c3`。

B 输出 SHA-256：`2b119f287e41a01215c17785ab15169edc16ab3c0b1f9c5526786f3e01e3dec0`。

## v0.3 C：两字主菜单字库实验

用户实机反馈：A 可进入游戏且 TEST-A! 生效；B 可进入游戏，但 Options 位置为空白。由此确认 A/B 的原位文本修改可加载；空白与原字库缺少相应字形相符，但字符映射及完整字库路径仍需实机验证。

C 沿用 B 的原位中文文本，仅在启动字体流追加“选、项”两个字形：

- 字形从 194 增至 196，原 194 条记录与原纹理已用像素均保留。新增字形放在空白区，纹理仍为 512×256；tg4h 完全不改动。
- 新增 `tools/refpack_compact.py` 离线编码器和 `tools/font_slot.py`。字体压缩数据 2,944 字节，纹理压缩数据 37,588 字节，均进入启动流原有 SHOC 槽位；不重排 STR，不移动其他区块。
- 只处理启动字体流 2095、两份 B 文本 752/1437，以及启动 TOC 171/2102；其他关卡字库保持原样，所以本轮只验证主菜单。
- FONT 解码长度增加 2,096 字节，对应两份启动 TOC 的根资源内存长度同步更新。VIV 索引、总长度、各资源位置保持原样。
- `packaging/minimal_font_patcher.py` 使用已生成的压缩资产，安装仍仅依赖 Python 标准库和 Tk；离线字库生成依赖见 `packaging/requirements-build.txt`。

C 不是全量汉化或已通过实机的修复版。需要先恢复原版再测试，不能在 A/B 上叠加。目标输出长度 3,170,839,904 字节，预计算 SHA-256：`9e5b9452ef954cc3d7fd85c18e79d3e97f3bd59682bbffe8a3439b9913a626e4`。自动测试 40 项通过，覆盖编码解码往返、原槽位容量、字体资源重读与原位文本约束。
