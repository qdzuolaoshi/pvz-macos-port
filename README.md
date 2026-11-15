# pvz-macos-port

把 Windows 版《植物大战僵尸》（1.0.0.1051，含中文汉化第一版，以及在这个 exe 上改出来的「95版」）移植成 **Apple Silicon Mac 原生应用** 的完整方案：基于开源引擎 [PvZ-Portable](https://github.com/wszqkzqk/PvZ-Portable) 的补丁、打包脚本、分析工具和移植指南。

> 本仓库**不包含任何游戏文件**（main.pak、图片、音效、字体、文字、图标等）。你需要自己合法拥有 Windows 版游戏，构建时从你本机的游戏文件读取资源，生成的应用仅供个人使用。游戏版权归 PopCap / EA 及汉化、改版作者所有。

## 做了什么

**数据兼容（1051 汉化版）**
- 读取 1051 自带的 32 位 `compiled/*.compiled` 动画定义；补齐年度版才有的资源占位。
- 汉化版在 Windows 上用 `gdi42.dll` 以 GDI 字体绘制所有文字：移植版用游戏自带的 `fzse_gbk.ttf`（方正少儿）还原，并模拟 gdi42 的字号、偏移、阴影、内凹染色和描边；按 GBK 字节宽度排版换行。
- 修正文字文件开头多一个空格导致的「]豌豆射手」等问题；起名只允许英文字母、数字和空格（与原版一致）。

**95版改动**：逆向分析 95 版 exe 的补丁，在引擎里以 `PVZ_95` 编译开关重新实现其玩法改动，原版不受影响。

**Mac 上的优化**
- **Retina 高清**：开启 HiDPI，按屏幕实际像素绘制；中文字按实际分辨率光栅化，布局不变；鼠标坐标单独换算。
- **清晰滤镜**：放大的图片用 Catmull-Rom 着色器采样（预乘 alpha、防止接缝），并按每帧开销自动降级，保证 60 帧。
- **阳光数字**：在纸框内居中；95 版阳光上限 20 亿，超长数字按比例缩小。
- **高清封面**：迷你游戏、解谜、生存模式封面可换成 AI 放大的 2/3/4 倍图（需用 `tools/thumbs/` 从你自己的游戏文件生成，本仓库不附带）。
- **窗口 4:3 锁定**：拖动只能等比例缩放，任何大小都没有黑边；双击标题栏、系统平铺后会自动调回 4:3。
- **全屏**：保持原版 4:3，上下撑满、两侧黑边；勾选框、⌥Option+Return、绿色按钮 / ⌃⌘F 都能切换并保持同步。
- **流畅度**：进关卡前预加载全部动画定义；限制卡顿后的逻辑追帧；减少音频锁等待；自适应垂直同步。
- **测试钩子**：环境变量 `PVZP_TEST_SCRIPT` 驱动的脚本化测试（模拟输入、截图、帧时间、卡顿日志），正常游戏时完全不启用。

完整方法、每个问题的原因与修法、以及精简的验收流程见 [docs/PORTING_GUIDE.md](docs/PORTING_GUIDE.md)（英文）。

## 构建

需要：Apple Silicon Mac（macOS 13+）、Xcode Command Line Tools、Homebrew 的 `cmake ninja dylibbundler jpeg-turbo libopenmpt libpng sdl2 sdl3`、Python 3。

```bash
# 1) 获取上游引擎（固定在提交 1e1742e）并打上本仓库的补丁
zsh scripts/get_engine.sh

# 2) 把你自己的 Windows 游戏文件放到 ./game（或用 PVZ_GAME_DIR 指定），
#    其中要有 main.pak、properties/LawnStrings.txt、fzse_gbk.ttf 和汉化的散装文件夹，
#    95 版需要的是同一套数据。

# 3) 构建两个应用（加 --install 会装进「应用程序」）
zsh scripts/build_apps.sh [--install]
```

可选：把自己做的图标放到 `icons/orig.icns`、`icons/p95.icns`；把用 `tools/thumbs/regenerate.sh` 生成的高清封面放到 `overrides/images/`。

存档位置：`~/Library/Application Support/io.github.wszqkzqk/PvZ1051-Mac/` 和 `.../PvZ95-Mac/`，两个版本互不影响。

## 目录

| 路径 | 内容 |
|---|---|
| `patches/pvz-portable-macos.patch` | 对上游 PvZ-Portable `1e1742e` 的完整补丁（68 个文件） |
| `scripts/get_engine.sh` | 克隆上游并打补丁 |
| `scripts/build_apps.sh` | 编译两个版本、组装资源、打包成 .app、签名、可选安装 |
| `tools/` | `pak_tool.py`（main.pak 解包）、`pediff.py` / `pvzdis.py`（exe 补丁对比与反汇编，需要 pefile、capstone）、`legacy_compiled.py`、`runtest.sh`（测试脚本运行器）、`thumbs/`（高清封面生成） |
| `docs/PORTING_GUIDE.md` | 移植指南 |

## 许可

补丁和本仓库的代码遵循 **LGPL-3.0-or-later**（与 PvZ-Portable 相同，见 [LICENSE](LICENSE) 和 [COPYING](COPYING)）。`stb_truetype.h` 为 MIT / 公有领域双许可。游戏本身及其资源不在本仓库内，也不在上述许可范围内。

---

## English summary

A complete recipe for running the Windows *Plants vs. Zombies* 1.0.0.1051 (including the Chinese fan translation and the "95" mod built on that exe) as a native Apple Silicon macOS app: a patch for the open-source [PvZ-Portable](https://github.com/wszqkzqk/PvZ-Portable) engine, packaging scripts, analysis tools and a porting guide. **No game files are included**; build from your own copy of the game. Highlights: 1051 legacy data mode and GDI-style CJK text, the 95 mod's gameplay behind `PVZ_95`, Retina rendering with crisp text and a Catmull-Rom magnification filter, a centred auto-fitting sun counter, optional AI-upscaled covers, a windowed 4:3 aspect lock, 4:3 pillarboxed fullscreen, stutter fixes and a scripted test hook. See [docs/PORTING_GUIDE.md](docs/PORTING_GUIDE.md).
