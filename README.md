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

`tools/viv.py` 使用 Python 标准库，只读解析本地样本的 BIGH 变体：16 字节大端包头，每条目录由大端 offset、size、key 三个 uint32 构成。key 为不透明标识，尚未验证哈希算法。工具校验目录与数据范围，提取时拒绝覆盖已有输出。

```powershell
python tools/viv.py "本地路径/bigfile0.viv" --output "local/bigfile0-index.json"
python tools/viv.py "本地路径/bigfile0.viv" --extract 2095 --output "local/frontend_global.str"
```

条目编号从 0 开始。当前工具不支持修改、回封或压缩数据解码，也不代表适用于所有 BIGH 文件。

## 后续工作

1. 解析 TOC 与 STR 容器关系，导出真实原文及稳定字符串 ID。
2. 确认剧情字幕、菜单、物品说明等文本覆盖范围。
3. 建立翻译表与术语表，保留占位符和控制码。
4. 解析字体纹理、字符映射与排版参数，制作中文字库。
5. 生成可复现补丁，在资源副本上验证回封，再进行实机测试。

仓库只保存工具、格式说明与汉化工作成果。原版 VIV、XEX、NSP、提取的完整资源和本地扫描清单不上传。
