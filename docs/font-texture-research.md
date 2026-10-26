# 多纹理字库研究快照（2026-10-26）

状态：尚未证实游戏 FONT v7 原生支持一套字库的多纹理页。不生成猜测页编号的安装包，避免再次造成启动故障。本轮被 F 的实机反馈插入，优先修正菜单文本表覆盖；后续继续查加载/绘制端。

## 直接观察

- 对原版 bigfile0/bigfile1 的明文 `shared\fonts\` 路径扫描，在 bigfile0 中看到 buttons 与 minion_pro 各自的 .inf/.tg4h/.tg4d，两套全局资源中各一份；bigfile1 此扫描没有匹配。明文扫描不能排除运行时构造路径、外部加载或其他压缩数据中的引用。
- minion_pro.inf 是 FONT v7，194 条 24 字节字形记录；buttons.inf 是同版结构，38 条记录。两者头中各有一个字体名，已有资源各配一张纹理。
- 0x44 开始的 256 个大端偏移项，在已解读格式中按码点高字节索引，指向每页 1,024 字节的字符查找存储。这里的“页”是 Unicode 查找页，不能作为纹理页支持证据。
- 两套原始字体的每条字形记录末尾 32 位字段全部为 0；该字段语义仍未知，不能擅自将它当作纹理编号并写 1。
- NRO 出现的 `[font] Texture`、ImFontAtlas 等字符串属于 ImGui 路径，不能拿来证明游戏内 FONT 渲染器支持多纹理。

## 上游源码

已定位公开上游 [VasilkovND/dantes-inferno-nx](https://github.com/VasilkovND/dantes-inferno-nx)。本轮读取的 main 为 55a40e309f4e6d6aaf9811fb9a15d51539d2e1e1。

- [PORTING.md](https://github.com/VasilkovND/dantes-inferno-nx/blob/55a40e309f4e6d6aaf9811fb9a15d51539d2e1e1/dante/PORTING.md) 描述：游戏逻辑来自用户 TU2 可执行文件生成的重编译代码；仓库不提交这些生成文件。
- [names.toml](https://github.com/VasilkovND/dantes-inferno-nx/blob/55a40e309f4e6d6aaf9811fb9a15d51539d2e1e1/dante/codegen/names.toml) 中现有命名主要用于图形着色器、音频、视频和蒙皮，没有已识别的游戏 FONT 加载/绘制钩子。
- [codegen.sh](https://github.com/VasilkovND/dantes-inferno-nx/blob/55a40e309f4e6d6aaf9811fb9a15d51539d2e1e1/dante/tools/codegen.sh) 使用 ReXGlue 和 Hell's Gate 的构建修补，从本地合法游戏文件生成代码及加载后的映像。
- 上传包的 NRO 构建路径包含 DanteInferno-SW/upstream/sdk。公开上游是可用的研究线索，不据此声称它与上传 NRO 为完全相同的源码版本。

分析样本 NRO SHA-256：`d0953820741932be15daf3ceac69071c226713b803ec569309b24c887a7c277c`。样本仅本地研究，不上传游戏执行文件或资源。

## 后续验证门槛

1. 获取/生成 TU2 映像与对应重编译函数，定位读取 FONT 名称、24 字节记录和字形 UV 的函数。
2. 追踪字体对象实际持有的纹理数量，以及绘制时是否存在按字形切换纹理的分支。
3. 若没有该机制，需要在加载/绘制钩子中实现外置中文纹理与映射，而非简单往 VIV 加文件。
4. 只有确认绑定关系后，才做第二张 512×256 纹理、一个汉字的最小测试；保留原纹理及既有资源位置，且仍须实机验证。

当前没有双纹理兼容性通过结果，没有新的可用 NRO，也没有可宣称生效的第二纹理补丁。
