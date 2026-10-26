# 但丁的地狱 Switch 简体中文汉化

目标：为用户本地原版资源制作简体中文文本与字库补丁。

## 当前进度（2026-10-26）

处于资源格式分析阶段，尚无可安装汉化补丁，尚未导出可翻译文本，未进行实机验证。

- 已只读验证 bigfile0.viv 的 2,151 个条目、bigfile1.viv 的 3,724 个条目；所有条目的偏移与长度均在原包范围内。
- 已在 bigfile0.viv 定位 frontend 文本索引及字体路径。
- 外层 frontend_global.str、frontend_global.toc、frontend.toc 与原包对应资源 SHA-256 比对相同，不是已完成的汉化。
- 尚未确定剧情字幕位置，不能认定只修改 bigfile0.viv 即可完成全游戏汉化。

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

`tools/viv.py` 使用 Python 标准库，只读解析本地样本的 BIGH 变体：16 字节大端包头，每条目录由大端 offset、size、key 三个 uint32 构成。key 为不透明标识，尚未验证哈希算法。工具校验目录与数据范围，提取时拒绝覆盖已有输出。新增批量提取、逐字节校验与多编码原文定位，使用 Python 3.9+，无需第三方依赖。

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
- 当前新增功能仅通过模拟包测试，等待用户原始资源验证。没有新增已翻译文本，也未解决 STR/TOC、字体映射或回封格式。

### 工具测试

```powershell
python -m unittest discover -s tests -v
```

测试覆盖原样提取与校验、空条目、内容篡改、源包变更、拒绝覆盖、非法包头与越界、跨读取区块搜索、UTF-16 定位、清单路径检查和失败后的残留清理。模拟包不包含游戏资源。

## 后续工作

1. 解析 TOC 与 STR 容器关系，导出真实原文及稳定字符串 ID。
2. 确认剧情字幕、菜单、物品说明等文本覆盖范围。
3. 建立翻译表与术语表，保留占位符和控制码。
4. 解析字体纹理、字符映射与排版参数，制作中文字库。
5. 生成可复现补丁，在资源副本上验证回封，再进行实机测试。

仓库只保存工具、格式说明与汉化工作成果。原版 VIV、XEX、NSP、提取的完整资源和本地扫描清单不上传。
