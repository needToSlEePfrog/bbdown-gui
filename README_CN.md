# BBDown GUI

一个为 [BBDown](https://github.com/nilaoda/BBDown) 打造的图形化界面，基于 Python + tkinter，让你不用敲命令行也能轻松下载 B 站视频。

## 功能

- **一键解析**：粘贴视频链接或 BV 号，自动获取标题、分 P、画质、编码等信息
- **灵活下载**：支持完整视频、仅视频、仅音频、弹幕、字幕、封面，可多选同时下载
- **画质 / 编码选择**：解析后自动填充可选画质与编码，也可手动指定
- **分 P 控制**：全部下载或指定范围，支持分 P 间隔延迟
- **多种解析模式**：默认 / TV 端 / APP 端 / 国际版一键切换
- **字幕模式**：普通字幕、AI 字幕、跳过字幕三选一
- **下载加速**：支持 aria2c 多线程下载，可自定义参数
- **账号登录**：扫码登录 WEB / TV 账号，下载会员内容
- **命令预览**：实时生成并展示即将执行的 BBDown 命令，所见即所得
- **输出日志**：下载过程实时输出，方便排查问题

## 截图

<!-- 在这里放你的截图 -->
<!-- ![主界面](screenshots/main.png) -->

## 使用前提

1. **Python 3.7+**（tkinter 通常已内置）
2. **BBDown.exe** — 从 [BBDown Releases](https://github.com/nilaoda/BBDown/releases) 下载，放在与 `bbdown_gui.py` 同一目录下
3. **ffmpeg**（推荐）— 混流需要，确保在 PATH 中或在 GUI 中手动指定路径

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/你的用户名/bbdown-gui.git
cd bbdown-gui

# 把 BBDown.exe 放到这个目录下

# 运行
python bbdown_gui.py
```

## 使用方法

1. 启动程序后，在「视频地址/BV号」中粘贴链接
2. 点击「一键解析」获取视频信息
3. 在各选项卡中按需调整设置（画质、编码、分 P、字幕等）
4. 点击「开始下载」

## 项目结构

```
bbdown-gui/
├── bbdown_gui.py    # 主程序（单文件）
├── README_CN.md        # 本文件
├── README.md     # English README
└── LICENSE          # MIT License
```

## 许可证

[MIT License](LICENSE)

## 致谢

- [BBDown](https://github.com/nilaoda/BBDown) — 本项目依赖的命令行下载工具
- [nilaoda](https://github.com/nilaoda) — BBDown 作者
