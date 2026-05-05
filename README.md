[README_EN.md](https://github.com/user-attachments/files/27385568/README_EN.md)
# BBDown GUI

A graphical interface for [BBDown](https://github.com/nilaoda/BBDown), built with Python and tkinter. Download Bilibili videos without touching the command line.


## Features

- **One-click parsing** — Paste a video URL or BV ID to fetch title, pages, quality, and codec info automatically
- **Flexible downloads** — Full video, video-only, audio-only, danmaku, subtitles, and cover art, with multi-select support
- **Quality & codec selection** — Auto-populated after parsing; manual override available
- **Multi-part (P) control** — Download all parts or a specific range, with optional per-part delay
- **Multiple API modes** — Default / TV / APP / International, switchable in one click
- **Subtitle modes** — Normal subtitles, AI-generated subtitles, or skip entirely
- **Download acceleration** — aria2c support with customizable arguments
- **Account login** — QR code login for WEB / TV accounts to access premium content
- **Live command preview** — See the exact BBDown command that will be executed
- **Real-time log output** — Monitor download progress and debug issues on the fly

## Screenshots

<!-- Add your screenshots here -->
<!-- ![Main interface](screenshots/main.png) -->

## Prerequisites

1. **Python 3.7+** (tkinter is usually bundled)
2. **BBDown.exe** — Download from [BBDown Releases](https://github.com/nilaoda/BBDown/releases) and place it in the same directory as `bbdown_gui.py`
3. **ffmpeg** (recommended) — Required for muxing; make sure it's in your PATH or specify the path in the GUI

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-username/bbdown-gui.git
cd bbdown-gui

# Place BBDown.exe in this directory

# Run
python bbdown_gui.py
```

## Usage

1. Launch the app and paste a video URL or BV ID
2. Click **Parse** to fetch video info
3. Adjust settings across tabs (quality, codec, page range, subtitles, etc.)
4. Click **Download**

## Project Structure

```
bbdown-gui/
├── bbdown_gui.py    # Main application (single file)
├── README.md        # 中文说明
├── README_EN.md     # This file
└── LICENSE          # MIT License
```

## License

[MIT License](LICENSE)

## Acknowledgements

- [BBDown](https://github.com/nilaoda/BBDown) — The CLI tool this project wraps
- [nilaoda](https://github.com/nilaoda) — Creator of BBDown
