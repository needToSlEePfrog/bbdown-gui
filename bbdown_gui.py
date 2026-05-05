import os
import re
import sys
import shutil
import locale
import threading
import subprocess
import tkinter as tk
from queue import Empty, Queue
from tkinter import filedialog, messagebox, scrolledtext, ttk


def get_bbdown_path():
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(script_dir, "BBDown.exe")


def get_default_work_dir():
    return os.path.dirname(get_bbdown_path())


def normalize_display_values(values):
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def get_process_encoding():
    if sys.platform == "win32":
        return locale.getpreferredencoding(False) or "gb18030"
    return "utf-8"


class BBDownGUI:
    AUTO_CHOICE = "自动（推荐）"
    DEFAULT_SINGLE_TEMPLATE = "<videoTitle>/<videoTitle>"
    DEFAULT_MULTI_TEMPLATE = "<videoTitle>/[P<pageNumberWithZero>]<pageTitle>"
    SUBTITLE_NORMAL = "normal"
    SUBTITLE_AI = "ai"
    SUBTITLE_SKIP = "skip"
    TASK_SUFFIXES = {
        "full": "_<dfn>_full-video",
        "video": "_<dfn>_video-only",
        "audio": "_audio-only",
        "danmaku": "_danmaku",
        "subtitle": "_subtitle",
        "cover": "_cover",
    }
    API_OPTIONS = {
        "自动（推荐）": "",
        "TV端": "-tv",
        "APP端": "-app",
        "国际版": "-intl",
    }
    API_EXPLANATIONS = {
        "自动（推荐）": "默认模式，先用这个；只有默认解析失败或结果不理想时再切换。",
        "TV端": "适合少数默认模式拿不到理想清晰度时尝试。",
        "APP端": "适合个别资源在 APP 接口下表现更稳定的情况。",
        "国际版": "主要给国际版内容使用，平时通常用不到。",
    }
    CODEC_EXPLANATIONS = {
        "自动（推荐）": "让 BBDown 自己选，最省心；如果你不确定，就保持这个。",
        "AVC": "兼容性最好，老设备和老播放器最稳。",
        "HEVC": "通常更省体积，但兼容性略低于 AVC。",
        "AV1": "压缩效率高，但老设备可能播放吃力。",
    }
    QUALITY_AUTO_EXPLANATION = "默认让 BBDown 自动选；如果你有明确需求，再手动指定画质。"
    PAGE_RE = re.compile(
        r"^\[.*?\]\s-\sP(?P<index>\d+):\s\[(?P<cid>\d+)\]\s\[(?P<title>.*?)\]\s\[(?P<duration>.*?)\]$"
    )
    STREAM_RE = re.compile(
        r"^\s+\d+\.\s\[(?P<quality>.*?)\]\s\[(?P<resolution>\d+x\d+)\]\s\[(?P<codec>[^\]]+)\]\s"
        r"\[(?P<fps>.*?)\]\s\[(?P<bitrate>.*?)\]\s\[(?P<size>.*?)\]$"
    )
    AUDIO_RE = re.compile(r"^\s+\d+\.\s\[(?P<codec>.*?)\]\s\[(?P<bitrate>.*?)\]\s\[(?P<size>.*?)\]$")
    TITLE_RE = re.compile(r"视频标题:\s(?P<title>.*)$")
    PAGE_COUNT_RE = re.compile(r"共计\s(?P<count>\d+)\s个分P")

    def __init__(self, root):
        self.root = root
        self.root.title("BBDown GUI")
        self.root.resizable(True, True)

        self.parse_result = None
        self.worker_thread = None
        self.output_queue = Queue()

        self._build_variables()
        self._build_ui()
        self._bind_updates()
        self.refresh_path_hints()
        self.update_page_controls()
        self.update_dynamic_controls(None)
        self.update_option_help()
        self.update_cmd()
        self.poll_queue()

    def _build_variables(self):
        self.url_var = tk.StringVar()
        self.api_var = tk.StringVar(value=self.AUTO_CHOICE)
        self.quality_var = tk.StringVar(value=self.AUTO_CHOICE)
        self.codec_var = tk.StringVar(value=self.AUTO_CHOICE)
        self.video_ascending_var = tk.BooleanVar(value=False)
        self.audio_ascending_var = tk.BooleanVar(value=False)
        self.interactive_var = tk.BooleanVar(value=False)

        self.full_video_var = tk.BooleanVar(value=True)
        self.video_only_var = tk.BooleanVar(value=False)
        self.audio_only_var = tk.BooleanVar(value=False)
        self.download_danmaku_var = tk.BooleanVar(value=False)
        self.download_subtitle_var = tk.BooleanVar(value=False)
        self.download_cover_var = tk.BooleanVar(value=False)
        self.parse_only_var = tk.BooleanVar(value=False)
        self.subtitle_mode_var = tk.StringVar(value=self.SUBTITLE_NORMAL)
        self.skip_mux_var = tk.BooleanVar(value=False)

        self.page_all_var = tk.BooleanVar(value=True)
        self.page_start_var = tk.IntVar(value=1)
        self.page_end_var = tk.IntVar(value=1)
        self.delay_var = tk.StringVar(value="")
        self.show_all_var = tk.BooleanVar(value=False)
        self.fp_var = tk.StringVar(value=self.DEFAULT_SINGLE_TEMPLATE)
        self.mfp_var = tk.StringVar(value=self.DEFAULT_MULTI_TEMPLATE)

        self.workdir_var = tk.StringVar(value=get_default_work_dir())
        self.ffmpeg_var = tk.StringVar(value="")
        self.mp4box_var = tk.StringVar(value="")
        self.aria2c_var = tk.StringVar(value="")
        self.upos_var = tk.StringVar(value="")
        self.use_mp4box_var = tk.BooleanVar(value=False)
        self.use_aria2_var = tk.BooleanVar(value=False)
        self.multi_thread_var = tk.BooleanVar(value=True)
        self.force_http_var = tk.BooleanVar(value=False)
        self.aria2cargs_var = tk.StringVar(value="-x16 -s16 -j16 -k 5M")

        self.cookie_var = tk.StringVar(value="")
        self.token_var = tk.StringVar(value="")
        self.ua_var = tk.StringVar(value="")
        self.lang_var = tk.StringVar(value="")

        self.bphost_var = tk.StringVar(value="")
        self.ephost_var = tk.StringVar(value="")
        self.area_var = tk.StringVar(value="")
        self.debug_var = tk.BooleanVar(value=False)
        self.hs_var = tk.BooleanVar(value=False)
        self.pcdn_var = tk.BooleanVar(value=False)
        self.frh_var = tk.BooleanVar(value=False)
        self.archive_file_var = tk.StringVar(value="")
        self.cfg_var = tk.StringVar(value="")

        self.parse_title_var = tk.StringVar(value="未解析")
        self.parse_status_var = tk.StringVar(value="等待输入链接")
        self.api_help_var = tk.StringVar(value=self.API_EXPLANATIONS[self.AUTO_CHOICE])
        self.quality_help_var = tk.StringVar(value=self.QUALITY_AUTO_EXPLANATION)
        self.codec_help_var = tk.StringVar(value=self.CODEC_EXPLANATIONS[self.AUTO_CHOICE])

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=6, pady=6)

        self.t1 = self.make_tab(notebook, "基本")
        self.t2 = self.make_tab(notebook, "下载内容")
        self.t3 = self.make_tab(notebook, "分P / 文件名")
        self.t4 = self.make_tab(notebook, "路径 / 工具")
        self.t5 = self.make_tab(notebook, "账号")
        self.t6 = self.make_tab(notebook, "高级")

        self.build_basic_tab()
        self.build_download_tab()
        self.build_page_tab()
        self.build_path_tab()
        self.build_account_tab()
        self.build_advanced_tab()
        self.build_bottom_area()

    def make_tab(self, notebook, label):
        frame = ttk.Frame(notebook, padding=6)
        notebook.add(frame, text=label)
        return frame

    def lrow(self, parent, row, label, widget, hint=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
        widget.grid(row=row, column=1, sticky="ew", pady=3)
        if hint:
            ttk.Label(parent, text=hint, foreground="#555").grid(
                row=row, column=2, sticky="w", padx=(6, 0), pady=3
            )
        parent.columnconfigure(1, weight=1)

    def build_basic_tab(self):
        url_row = ttk.Frame(self.t1)
        url_row.grid(row=0, column=1, sticky="ew", pady=3)
        self.t1.columnconfigure(1, weight=1)
        ttk.Label(self.t1, text="视频地址/BV号：").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(url_row, text="一键解析", command=self.parse_video_info).pack(side="left", padx=(6, 0))

        self.api_cb = ttk.Combobox(
            self.t1,
            textvariable=self.api_var,
            state="readonly",
            values=list(self.API_OPTIONS.keys()),
        )
        self.lrow(self.t1, 1, "解析模式：", self.api_cb)
        ttk.Label(self.t1, textvariable=self.api_help_var, foreground="#555", wraplength=520).grid(
            row=1, column=2, sticky="w", padx=(6, 0), pady=3
        )

        self.quality_cb = ttk.Combobox(
            self.t1, textvariable=self.quality_var, state="readonly", values=[self.AUTO_CHOICE]
        )
        self.lrow(self.t1, 2, "画质优先级：", self.quality_cb)
        ttk.Label(self.t1, textvariable=self.quality_help_var, foreground="#555", wraplength=520).grid(
            row=2, column=2, sticky="w", padx=(6, 0), pady=3
        )

        self.codec_cb = ttk.Combobox(
            self.t1, textvariable=self.codec_var, state="readonly", values=[self.AUTO_CHOICE]
        )
        self.lrow(self.t1, 3, "编码优先级：", self.codec_cb)
        ttk.Label(self.t1, textvariable=self.codec_help_var, foreground="#555", wraplength=520).grid(
            row=3, column=2, sticky="w", padx=(6, 0), pady=3
        )

        info_frame = ttk.LabelFrame(self.t1, text="解析结果")
        info_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        info_frame.columnconfigure(1, weight=1)
        ttk.Label(info_frame, text="标题：").grid(row=0, column=0, sticky="nw", padx=(6, 6), pady=4)
        ttk.Label(info_frame, textvariable=self.parse_title_var, wraplength=520).grid(
            row=0, column=1, sticky="w", padx=(0, 6), pady=4
        )
        ttk.Label(info_frame, text="状态：").grid(row=1, column=0, sticky="nw", padx=(6, 6), pady=4)
        ttk.Label(info_frame, textvariable=self.parse_status_var, wraplength=520).grid(
            row=1, column=1, sticky="w", padx=(0, 6), pady=4
        )

        ck_frame = ttk.Frame(self.t1)
        ck_frame.grid(row=5, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Checkbutton(ck_frame, text="交互选清晰度(-ia)", variable=self.interactive_var).pack(side="left", padx=4)
        ttk.Checkbutton(ck_frame, text="视频升序", variable=self.video_ascending_var).pack(side="left", padx=4)
        ttk.Checkbutton(ck_frame, text="音频升序", variable=self.audio_ascending_var).pack(side="left", padx=4)

    def build_download_tab(self):
        ttk.Label(self.t2, text="下载类型：").grid(row=0, column=0, sticky="nw", pady=3)
        rf = ttk.Frame(self.t2)
        rf.grid(row=0, column=1, columnspan=2, sticky="w", pady=3)
        ttk.Checkbutton(rf, text="完整视频", variable=self.full_video_var).pack(side="left", padx=3)
        ttk.Checkbutton(rf, text="仅视频", variable=self.video_only_var).pack(side="left", padx=3)
        ttk.Checkbutton(rf, text="仅音频", variable=self.audio_only_var).pack(side="left", padx=3)
        ttk.Checkbutton(rf, text="下载弹幕", variable=self.download_danmaku_var).pack(side="left", padx=3)
        ttk.Checkbutton(rf, text="下载字幕", variable=self.download_subtitle_var).pack(side="left", padx=3)
        ttk.Checkbutton(rf, text="下载封面", variable=self.download_cover_var).pack(side="left", padx=3)
        ttk.Checkbutton(rf, text="解析", variable=self.parse_only_var).pack(side="left", padx=3)

        ttk.Separator(self.t2, orient="horizontal").grid(row=1, column=0, columnspan=3, sticky="ew", pady=6)
        ck = ttk.Frame(self.t2)
        ck.grid(row=2, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Checkbutton(ck, text="跳过混流", variable=self.skip_mux_var).pack(side="left", padx=4)
        ttk.Label(
            ck,
            text="可多选；程序会按勾选项目顺序执行，并自动加后缀避免同名覆盖。",
            foreground="#555",
        ).pack(side="left", padx=10)

        subtitle_frame = ttk.LabelFrame(self.t2, text="字幕")
        subtitle_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        ttk.Radiobutton(
            subtitle_frame,
            text="下载普通字幕",
            variable=self.subtitle_mode_var,
            value=self.SUBTITLE_NORMAL,
        ).pack(anchor="w", padx=8, pady=(6, 2))
        ttk.Radiobutton(
            subtitle_frame,
            text="下载AI字幕（实验性，可能错配）",
            variable=self.subtitle_mode_var,
            value=self.SUBTITLE_AI,
        ).pack(anchor="w", padx=8, pady=2)
        ttk.Radiobutton(
            subtitle_frame,
            text="跳过全部字幕",
            variable=self.subtitle_mode_var,
            value=self.SUBTITLE_SKIP,
        ).pack(anchor="w", padx=8, pady=(2, 6))
        ttk.Label(
            subtitle_frame,
            text=(
                "普通字幕优先使用视频自带字幕；AI字幕会显式传入 --skip-ai false。"
                "如果某些视频的 AI 字幕内容串片或不准确，建议切回“下载普通字幕”或“跳过全部字幕”。"
            ),
            foreground="#555",
            wraplength=660,
        ).pack(anchor="w", padx=8, pady=(0, 8))

    def build_page_tab(self):
        page_frame = ttk.LabelFrame(self.t3, text="分P选择")
        page_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=4)
        page_frame.columnconfigure(1, weight=1)

        ttk.Checkbutton(page_frame, text="全部分P", variable=self.page_all_var, command=self.update_page_controls).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=6, pady=4
        )
        ttk.Label(page_frame, text="起始P：").grid(row=1, column=0, sticky="w", padx=(6, 6), pady=4)
        self.page_start_spin = tk.Spinbox(page_frame, from_=1, to=1, width=8, textvariable=self.page_start_var)
        self.page_start_spin.grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(page_frame, text="结束P：").grid(row=1, column=2, sticky="w", padx=(12, 6), pady=4)
        self.page_end_spin = tk.Spinbox(page_frame, from_=1, to=1, width=8, textvariable=self.page_end_var)
        self.page_end_spin.grid(row=1, column=3, sticky="w", pady=4)
        ttk.Label(page_frame, text="先解析后会自动更新最大分P数", foreground="#555").grid(
            row=2, column=0, columnspan=4, sticky="w", padx=6, pady=(0, 4)
        )

        self.lrow(self.t3, 1, "分P间隔(秒)：", ttk.Entry(self.t3, textvariable=self.delay_var), "留空则不设置")
        ttk.Checkbutton(self.t3, text="展示所有分P标题", variable=self.show_all_var).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=4
        )

        ttk.Separator(self.t3, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="ew", pady=6)
        self.lrow(
            self.t3,
            4,
            "单P文件名模板：",
            ttk.Entry(self.t3, textvariable=self.fp_var),
            "默认: <videoTitle>/<videoTitle>",
        )
        self.lrow(
            self.t3,
            5,
            "多P文件名模板：",
            ttk.Entry(self.t3, textvariable=self.mfp_var),
            "默认: <videoTitle>/[P<pageNumberWithZero>]<pageTitle>",
        )
        ttk.Label(
            self.t3,
            text="当前默认会先创建与视频同名的文件夹，再把视频、字幕、弹幕等相关文件放进去。",
            foreground="#555",
            wraplength=680,
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(2, 4))
        vars_hint = (
            "可用变量: <videoTitle> <pageNumber> <pageTitle> <bvid> <dfn> <res> <fps> "
            "<videoCodecs> <ownerName> <videoDate>"
        )
        ttk.Label(self.t3, text=vars_hint, foreground="#555", wraplength=680).grid(
            row=7, column=0, columnspan=3, sticky="w", pady=4
        )

    def build_path_tab(self):
        self.add_path_row(self.t4, 0, "工作目录：", self.workdir_var, browse_mode="dir", hint="默认就是 BBDown 当前目录")
        self.add_path_row(self.t4, 1, "ffmpeg 路径：", self.ffmpeg_var, browse_mode="file", hint="留空时使用 PATH")
        self.add_path_row(self.t4, 2, "mp4box 路径：", self.mp4box_var, browse_mode="file")
        self.add_path_row(self.t4, 3, "aria2c 路径：", self.aria2c_var, browse_mode="file")
        self.lrow(self.t4, 4, "upos 服务器：", ttk.Entry(self.t4, textvariable=self.upos_var))
        self.lrow(
            self.t4,
            5,
            "aria2c 附加参数：",
            ttk.Entry(self.t4, textvariable=self.aria2cargs_var),
            "默认: -x16 -s16 -j16 -k 5M",
        )

        ck = ttk.Frame(self.t4)
        ck.grid(row=6, column=0, columnspan=3, sticky="w", pady=6)
        ttk.Checkbutton(ck, text="使用MP4Box混流", variable=self.use_mp4box_var).pack(side="left", padx=4)
        ttk.Checkbutton(ck, text="使用aria2c下载", variable=self.use_aria2_var).pack(side="left", padx=4)
        ttk.Checkbutton(ck, text="多线程(-mt)", variable=self.multi_thread_var).pack(side="left", padx=4)
        ttk.Checkbutton(ck, text="强制HTTP", variable=self.force_http_var).pack(side="left", padx=4)

        hint_box = ttk.LabelFrame(self.t4, text="当前环境")
        hint_box.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(10, 4))
        hint_box.columnconfigure(1, weight=1)
        ttk.Label(hint_box, text="BBDown：").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.bbdown_hint = ttk.Label(hint_box, text="", wraplength=640)
        self.bbdown_hint.grid(row=0, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(hint_box, text="默认输出：").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.output_dir_hint = ttk.Label(hint_box, text="", wraplength=640)
        self.output_dir_hint.grid(row=1, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(hint_box, text="ffmpeg：").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.ffmpeg_hint = ttk.Label(hint_box, text="", wraplength=640)
        self.ffmpeg_hint.grid(row=2, column=1, sticky="w", padx=6, pady=4)

    def build_account_tab(self):
        ttk.Label(
            self.t5,
            text="如果同目录的 BBDown.data 已保存登录信息，通常无需手动填写下面这些内容。",
            foreground="#555",
            wraplength=700,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=4)
        self.lrow(self.t5, 1, "Cookie：", ttk.Entry(self.t5, textvariable=self.cookie_var))
        self.lrow(self.t5, 2, "Access Token：", ttk.Entry(self.t5, textvariable=self.token_var))
        self.lrow(self.t5, 3, "User-Agent：", ttk.Entry(self.t5, textvariable=self.ua_var))
        self.lrow(self.t5, 4, "音频语言代码：", ttk.Entry(self.t5, textvariable=self.lang_var), "如 chi, jpn")

        row = ttk.Frame(self.t5)
        row.grid(row=5, column=0, columnspan=3, sticky="w", pady=8)
        ttk.Button(row, text="扫码登录 WEB账号", command=lambda: self.do_login("login")).pack(side="left", padx=4)
        ttk.Button(row, text="扫码登录 TV账号", command=lambda: self.do_login("logintv")).pack(side="left", padx=4)

    def build_advanced_tab(self):
        ttk.Label(self.t6, text="这些选项一般不需要改，除非你已经明确知道用途。", foreground="#555").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=4
        )
        self.lrow(self.t6, 1, "BiliPlus host：", ttk.Entry(self.t6, textvariable=self.bphost_var))
        self.lrow(self.t6, 2, "BiliPlus ep-host：", ttk.Entry(self.t6, textvariable=self.ephost_var))
        area_cb = ttk.Combobox(self.t6, textvariable=self.area_var, state="readonly", values=["", "hk", "tw", "th"])
        self.lrow(self.t6, 3, "area：", area_cb, "仅港澳台区域内容常用")

        ck = ttk.Frame(self.t6)
        ck.grid(row=4, column=0, columnspan=3, sticky="w", pady=6)
        ttk.Checkbutton(ck, text="调试日志", variable=self.debug_var).pack(side="left", padx=4)
        ttk.Checkbutton(ck, text="隐藏流列表", variable=self.hs_var).pack(side="left", padx=4)
        ttk.Checkbutton(ck, text="允许PCDN", variable=self.pcdn_var).pack(side="left", padx=4)
        ttk.Checkbutton(ck, text="强制替换Host", variable=self.frh_var).pack(side="left", padx=4)

        self.add_path_row(self.t6, 5, "记录已下载文件：", self.archive_file_var, browse_mode="save", hint="为空则不启用")
        self.add_path_row(self.t6, 6, "配置文件：", self.cfg_var, browse_mode="file", hint="默认会使用 BBDown.config")

    def build_bottom_area(self):
        bottom = ttk.Frame(self.root, padding=(6, 0, 6, 6))
        bottom.pack(fill="both", expand=True)

        ttk.Label(bottom, text="生成的命令：").pack(anchor="w")
        self.cmd_text = tk.Text(bottom, height=4, state="disabled", wrap="word", font=("Consolas", 9), bg="#f8f8f8")
        self.cmd_text.pack(fill="x", pady=(0, 6))

        btn_row = ttk.Frame(bottom)
        btn_row.pack(anchor="w", pady=2)
        ttk.Button(btn_row, text="开始下载", command=self.run_download).pack(side="left", padx=4)
        ttk.Button(btn_row, text="重置所有", command=self.clear_all).pack(side="left", padx=4)

        ttk.Label(bottom, text="输出日志：").pack(anchor="w", pady=(4, 0))
        self.log_text = scrolledtext.ScrolledText(bottom, height=14, state="disabled", font=("Consolas", 9), bg="white")
        self.log_text.pack(fill="both", expand=True)

    def add_path_row(self, parent, row, label, variable, browse_mode="file", hint=None):
        frame = ttk.Frame(parent)
        frame.columnconfigure(0, weight=1)
        entry = ttk.Entry(frame, textvariable=variable)
        entry.grid(row=0, column=0, sticky="ew")
        ttk.Button(frame, text="...", width=4, command=lambda: self.choose_path(variable, browse_mode)).grid(
            row=0, column=1, padx=(6, 0)
        )
        self.lrow(parent, row, label, frame, hint)

    def choose_path(self, variable, mode):
        if mode == "dir":
            path = filedialog.askdirectory()
        elif mode == "save":
            path = filedialog.asksaveasfilename(
                title="选择记录文件",
                defaultextension=".txt",
                filetypes=[("Text", "*.txt"), ("All Files", "*.*")],
            )
        else:
            path = filedialog.askopenfilename()
        if path:
            variable.set(path)

    def _bind_updates(self):
        variables = [
            self.url_var,
            self.api_var,
            self.quality_var,
            self.codec_var,
            self.video_ascending_var,
            self.audio_ascending_var,
            self.interactive_var,
            self.full_video_var,
            self.video_only_var,
            self.audio_only_var,
            self.download_danmaku_var,
            self.download_subtitle_var,
            self.download_cover_var,
            self.parse_only_var,
            self.subtitle_mode_var,
            self.skip_mux_var,
            self.page_all_var,
            self.page_start_var,
            self.page_end_var,
            self.delay_var,
            self.show_all_var,
            self.fp_var,
            self.mfp_var,
            self.workdir_var,
            self.ffmpeg_var,
            self.mp4box_var,
            self.aria2c_var,
            self.upos_var,
            self.use_mp4box_var,
            self.use_aria2_var,
            self.multi_thread_var,
            self.force_http_var,
            self.aria2cargs_var,
            self.cookie_var,
            self.token_var,
            self.ua_var,
            self.lang_var,
            self.bphost_var,
            self.ephost_var,
            self.area_var,
            self.debug_var,
            self.hs_var,
            self.pcdn_var,
            self.frh_var,
            self.archive_file_var,
            self.cfg_var,
        ]
        for var in variables:
            var.trace_add("write", lambda *_: self.update_cmd())

    def refresh_path_hints(self):
        bbdown = get_bbdown_path()
        self.bbdown_hint.config(text=bbdown if os.path.exists(bbdown) else f"未找到: {bbdown}")
        output_dir = self.workdir_var.get().strip() or get_default_work_dir()
        self.output_dir_hint.config(text=output_dir)
        ffmpeg_path = shutil.which("ffmpeg")
        self.ffmpeg_hint.config(text=ffmpeg_path if ffmpeg_path else "PATH 中未找到 ffmpeg")

    def update_option_help(self):
        self.api_help_var.set(self.API_EXPLANATIONS.get(self.api_var.get(), self.API_EXPLANATIONS[self.AUTO_CHOICE]))

        if self.quality_var.get() == self.AUTO_CHOICE:
            self.quality_help_var.set(self.QUALITY_AUTO_EXPLANATION)
        elif self.quality_var.get():
            self.quality_help_var.set(f"当前会优先下载 {self.quality_var.get()}；只有你明确要固定画质时才需要改。")
        else:
            self.quality_help_var.set(self.QUALITY_AUTO_EXPLANATION)

        self.codec_help_var.set(
            self.CODEC_EXPLANATIONS.get(self.codec_var.get(), self.CODEC_EXPLANATIONS[self.AUTO_CHOICE])
        )

    def build_base_args(self):
        url = self.url_var.get().strip()
        if not url:
            return None, "请填写视频地址或BV号"

        args = [url]
        api_arg = self.API_OPTIONS.get(self.api_var.get(), "")
        if api_arg:
            args.append(api_arg)
        if self.quality_var.get() and self.quality_var.get() != self.AUTO_CHOICE:
            args += ["-q", self.quality_var.get()]
        if self.codec_var.get() and self.codec_var.get() != self.AUTO_CHOICE:
            args += ["-e", self.codec_var.get().lower()]

        if self.interactive_var.get():
            args.append("-ia")
        if self.video_ascending_var.get():
            args.append("--video-ascending")
        if self.audio_ascending_var.get():
            args.append("--audio-ascending")
        if self.skip_mux_var.get():
            args.append("--skip-mux")

        if not self.page_all_var.get():
            start = self.page_start_var.get()
            end = self.page_end_var.get()
            if end < start:
                end = start
                self.page_end_var.set(end)
            page_expr = str(start) if start == end else f"{start}-{end}"
            args += ["-p", page_expr]
        if self.delay_var.get().strip():
            args += ["--delay-per-page", self.delay_var.get().strip()]
        if self.show_all_var.get():
            args.append("--show-all")

        if self.workdir_var.get().strip():
            args += ["--work-dir", self.workdir_var.get().strip()]
        if self.ffmpeg_var.get().strip():
            args += ["--ffmpeg-path", self.ffmpeg_var.get().strip()]
        if self.mp4box_var.get().strip():
            args += ["--mp4box-path", self.mp4box_var.get().strip()]
        if self.aria2c_var.get().strip():
            args += ["--aria2c-path", self.aria2c_var.get().strip()]
        if self.upos_var.get().strip():
            args += ["--upos-host", self.upos_var.get().strip()]
        if self.use_mp4box_var.get():
            args.append("--use-mp4box")
        if self.use_aria2_var.get():
            args.append("-aria2")
        if self.multi_thread_var.get():
            args.append("-mt")
        if self.force_http_var.get():
            args.append("--force-http")
        if self.aria2cargs_var.get().strip():
            args += ["--aria2c-args", self.aria2cargs_var.get().strip()]

        if self.cookie_var.get().strip():
            args += ["-c", self.cookie_var.get().strip()]
        if self.token_var.get().strip():
            args += ["-token", self.token_var.get().strip()]
        if self.ua_var.get().strip():
            args += ["-ua", self.ua_var.get().strip()]
        if self.lang_var.get().strip():
            args += ["--language", self.lang_var.get().strip()]

        if self.bphost_var.get().strip():
            args += ["--host", self.bphost_var.get().strip()]
        if self.ephost_var.get().strip():
            args += ["--ep-host", self.ephost_var.get().strip()]
        if self.area_var.get():
            args += ["--area", self.area_var.get()]
        if self.debug_var.get():
            args.append("--debug")
        if self.hs_var.get():
            args.append("-hs")
        if self.pcdn_var.get():
            args.append("--allow-pcdn")
        if self.frh_var.get():
            args.append("--force-replace-host")
        if self.archive_file_var.get().strip():
            args += ["--save-archives-to-file", self.archive_file_var.get().strip()]
        if self.cfg_var.get().strip():
            args += ["--config-file", self.cfg_var.get().strip()]

        return args, None

    def add_name_templates(self, args, mode_key):
        single_base = self.fp_var.get().strip() or self.DEFAULT_SINGLE_TEMPLATE
        multi_base = self.mfp_var.get().strip() or self.DEFAULT_MULTI_TEMPLATE
        suffix = self.TASK_SUFFIXES.get(mode_key, "")
        return args + ["-F", f"{single_base}{suffix}", "-M", f"{multi_base}{suffix}"]

    def build_download_commands(self):
        base_args, err = self.build_base_args()
        if err:
            return None, err

        commands = []
        if self.full_video_var.get():
            commands.append(("完整视频", self.add_name_templates(base_args.copy(), "full")))
        if self.video_only_var.get():
            commands.append(("仅视频", self.add_name_templates(base_args.copy() + ["--video-only"], "video")))
        if self.audio_only_var.get():
            commands.append(("仅音频", self.add_name_templates(base_args.copy() + ["--audio-only"], "audio")))
        if self.download_danmaku_var.get():
            commands.append(("下载弹幕", self.add_name_templates(base_args.copy() + ["--danmaku-only"], "danmaku")))
        if self.download_subtitle_var.get() and self.subtitle_mode_var.get() != self.SUBTITLE_SKIP:
            sub_args = base_args.copy() + ["--sub-only"]
            if self.subtitle_mode_var.get() == self.SUBTITLE_AI:
                sub_args += ["--skip-ai", "false"]
            commands.append(("下载字幕", self.add_name_templates(sub_args, "subtitle")))
        if self.download_cover_var.get():
            commands.append(("下载封面", self.add_name_templates(base_args.copy() + ["--cover-only"], "cover")))
        if self.parse_only_var.get():
            commands.append(("解析", base_args.copy() + ["-info"]))

        if not commands:
            return None, "请至少勾选一个下载类型"
        return commands, None

    def log(self, text, reset=False):
        self.log_text.config(state="normal")
        if reset:
            self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.log_text.update_idletasks()

    def update_cmd(self):
        self.update_option_help()
        self.refresh_path_hints()
        commands, err = self.build_download_commands()
        self.cmd_text.config(state="normal")
        self.cmd_text.delete("1.0", tk.END)
        if err:
            self.cmd_text.insert(tk.END, err)
        else:
            bbdown = get_bbdown_path()
            lines = []
            for index, (label, args) in enumerate(commands, start=1):
                lines.append(f"[{index}] {label}")
                lines.append(subprocess.list2cmdline([bbdown] + args))
            self.cmd_text.insert(tk.END, "\n".join(lines))
        self.cmd_text.config(state="disabled")

    def update_page_controls(self):
        state = "disabled" if self.page_all_var.get() else "normal"
        self.page_start_spin.config(state=state)
        self.page_end_spin.config(state=state)
        self.update_cmd()

    def update_dynamic_controls(self, result):
        self.parse_result = result
        qualities = [self.AUTO_CHOICE] + (result["qualities"] if result else [])
        codecs = [self.AUTO_CHOICE] + (result["codecs"] if result else [])
        self.quality_cb.config(values=qualities, state="readonly")
        self.codec_cb.config(values=codecs, state="readonly")
        if self.quality_var.get() not in qualities:
            self.quality_var.set(self.AUTO_CHOICE)
        if self.codec_var.get() not in codecs:
            self.codec_var.set(self.AUTO_CHOICE)

        page_count = result["page_count"] if result else 1
        self.page_start_spin.config(from_=1, to=max(1, page_count))
        self.page_end_spin.config(from_=1, to=max(1, page_count))
        if self.page_start_var.get() > page_count:
            self.page_start_var.set(1)
        if self.page_end_var.get() > page_count:
            self.page_end_var.set(page_count)
        if self.page_start_var.get() < 1:
            self.page_start_var.set(1)
        if self.page_end_var.get() < self.page_start_var.get():
            self.page_end_var.set(self.page_start_var.get())
        self.update_page_controls()
        self.update_option_help()

    def parse_video_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请先填写视频地址或BV号")
            return
        bbdown = get_bbdown_path()
        if not os.path.exists(bbdown):
            messagebox.showerror("找不到 BBDown.exe", f"未找到：{bbdown}")
            return
        self.parse_status_var.set("正在解析，请稍候...")
        self.log(f"执行解析：{subprocess.list2cmdline([bbdown, url, '-info'])}\n\n", reset=True)
        self.start_process(
            [bbdown, url, "-info"],
            mode="parse",
            cwd=os.path.dirname(bbdown),
        )

    def run_download(self):
        commands, err = self.build_download_commands()
        if err:
            messagebox.showwarning("提示", err)
            return
        bbdown = get_bbdown_path()
        if not os.path.exists(bbdown):
            messagebox.showerror("找不到 BBDown.exe", f"未找到：{bbdown}")
            return
        lines = []
        for index, (label, args) in enumerate(commands, start=1):
            lines.append(f"任务 {index}: {label}")
            lines.append(subprocess.list2cmdline([bbdown] + args))
        self.log("执行下载：\n" + "\n".join(lines) + "\n\n", reset=True)
        self.start_process(commands, mode="download", cwd=os.path.dirname(bbdown))

    def do_login(self, cmd):
        bbdown = get_bbdown_path()
        if not os.path.exists(bbdown):
            messagebox.showerror("找不到 BBDown.exe", f"未找到：{bbdown}")
            return
        self.log(f"执行登录：{subprocess.list2cmdline([bbdown, cmd])}\n\n", reset=True)
        self.start_process([bbdown, cmd], mode="login", cwd=os.path.dirname(bbdown))

    def start_process(self, command, mode, cwd):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("忙碌中", "当前已有任务在运行，请等待完成后再试。")
            return

        def worker():
            lines = []
            try:
                process_encoding = get_process_encoding()
                tasks = [("单次任务", command)] if mode != "download" else command
                bbdown = get_bbdown_path()
                last_returncode = 0
                for index, task in enumerate(tasks, start=1):
                    if mode == "download":
                        label, args = task
                        full_command = [bbdown] + args
                    else:
                        label = f"任务 {index}"
                        full_command = task
                    self.output_queue.put(("line", f"\n===== {label} =====\n"))
                    proc = subprocess.Popen(
                        full_command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding=process_encoding,
                        errors="replace",
                        cwd=cwd,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    )
                    assert proc.stdout is not None
                    for line in proc.stdout:
                        lines.append(line)
                        self.output_queue.put(("line", line))
                    proc.wait()
                    last_returncode = proc.returncode
                    if proc.returncode != 0:
                        break
                self.output_queue.put(("done", {"mode": mode, "returncode": last_returncode, "output": "".join(lines)}))
            except Exception as exc:
                self.output_queue.put(("error", str(exc)))

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def poll_queue(self):
        try:
            while True:
                kind, payload = self.output_queue.get_nowait()
                if kind == "line":
                    self.log(payload)
                elif kind == "done":
                    self.handle_process_done(payload)
                elif kind == "error":
                    self.log(f"\n运行出错：{payload}\n")
        except Empty:
            pass
        self.root.after(100, self.poll_queue)

    def handle_process_done(self, payload):
        mode = payload["mode"]
        returncode = payload["returncode"]
        output = payload["output"]
        self.log(f"\n[退出码: {returncode}]\n")
        if mode == "parse" and returncode == 0:
            result = self.parse_info_output(output)
            self.update_dynamic_controls(result)
            self.parse_title_var.set(result["title"] or "未识别到标题")
            status_parts = [f"共 {result['page_count']} 个分P"]
            if result["qualities"]:
                status_parts.append(f"画质: {', '.join(result['qualities'])}")
            if result["codecs"]:
                status_parts.append(f"编码: {', '.join(result['codecs'])}")
            self.parse_status_var.set("；".join(status_parts))
        elif mode == "parse":
            self.parse_status_var.set("解析失败，请检查日志")

    def parse_info_output(self, output):
        title = ""
        pages = []
        qualities = []
        codecs = []
        audio_streams = []
        page_count = 1

        for raw_line in output.splitlines():
            line = raw_line.rstrip("\n")
            title_match = self.TITLE_RE.match(line)
            if title_match:
                title = title_match.group("title").strip()
                continue
            if not title and "视频标题:" in line:
                title = line.split("视频标题:", 1)[1].strip()
                continue

            page_match = self.PAGE_RE.match(line)
            if page_match:
                pages.append(
                    {
                        "index": int(page_match.group("index")),
                        "cid": page_match.group("cid"),
                        "title": page_match.group("title"),
                        "duration": page_match.group("duration"),
                    }
                )
                continue

            page_count_match = self.PAGE_COUNT_RE.match(line)
            if page_count_match:
                page_count = int(page_count_match.group("count"))
                continue

            stream_match = self.STREAM_RE.match(line)
            if stream_match:
                qualities.append(stream_match.group("quality").strip())
                codecs.append(stream_match.group("codec").strip())
                continue

            audio_match = self.AUDIO_RE.match(line)
            if audio_match:
                audio_streams.append(
                    {
                        "codec": audio_match.group("codec").strip(),
                        "bitrate": audio_match.group("bitrate").strip(),
                        "size": audio_match.group("size").strip(),
                    }
                )

        if pages:
            page_count = max(page_count, max(page["index"] for page in pages))

        return {
            "title": title,
            "pages": pages,
            "page_count": page_count,
            "qualities": normalize_display_values(qualities),
            "codecs": normalize_display_values(codecs),
            "audio_streams": audio_streams,
        }

    def clear_all(self):
        for var, default in [
            (self.url_var, ""),
            (self.api_var, self.AUTO_CHOICE),
            (self.quality_var, self.AUTO_CHOICE),
            (self.codec_var, self.AUTO_CHOICE),
            (self.video_ascending_var, False),
            (self.audio_ascending_var, False),
            (self.interactive_var, False),
            (self.full_video_var, True),
            (self.video_only_var, False),
            (self.audio_only_var, False),
            (self.download_danmaku_var, False),
            (self.download_subtitle_var, False),
            (self.download_cover_var, False),
            (self.parse_only_var, False),
            (self.subtitle_mode_var, self.SUBTITLE_NORMAL),
            (self.skip_mux_var, False),
            (self.page_all_var, True),
            (self.page_start_var, 1),
            (self.page_end_var, 1),
            (self.delay_var, ""),
            (self.show_all_var, False),
            (self.fp_var, self.DEFAULT_SINGLE_TEMPLATE),
            (self.mfp_var, self.DEFAULT_MULTI_TEMPLATE),
            (self.workdir_var, get_default_work_dir()),
            (self.ffmpeg_var, ""),
            (self.mp4box_var, ""),
            (self.aria2c_var, ""),
            (self.upos_var, ""),
            (self.use_mp4box_var, False),
            (self.use_aria2_var, False),
            (self.multi_thread_var, True),
            (self.force_http_var, False),
            (self.aria2cargs_var, "-x16 -s16 -j16 -k 5M"),
            (self.cookie_var, ""),
            (self.token_var, ""),
            (self.ua_var, ""),
            (self.lang_var, ""),
            (self.bphost_var, ""),
            (self.ephost_var, ""),
            (self.area_var, ""),
            (self.debug_var, False),
            (self.hs_var, False),
            (self.pcdn_var, False),
            (self.frh_var, False),
            (self.archive_file_var, ""),
            (self.cfg_var, ""),
        ]:
            var.set(default)
        self.parse_title_var.set("未解析")
        self.parse_status_var.set("等待输入链接")
        self.update_dynamic_controls(None)
        self.update_cmd()


def main():
    root = tk.Tk()
    BBDownGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
