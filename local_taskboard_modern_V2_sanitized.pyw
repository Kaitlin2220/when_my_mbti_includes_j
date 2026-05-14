#!/usr/bin/env python3# -*- coding: utf-8 -*-
"""
本地任务看板 - 白底马卡龙色卡版
v3.0 新增：一周日历条 | 移除：同步便笺功能

去私密化副本：保留完整功能，但将任务分类、路径与文本替换为通用占位。
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import json
import os
import shutil
import glob
import random
from datetime import datetime, timedelta
import re
import subprocess
import threading
import pystray
from PIL import Image, ImageDraw, ImageTk
import keyboard
import ctypes
import time
import sys
import calendar
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ==========================================
# 解除 Windows 高分屏模糊封印
# ==========================================
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ==========================================
# 全局配色方案
# ==========================================
COLORS = {
    'bg_main': '#FFFFFF',
    'bg_secondary': '#F9F2EF',
    'bg_tertiary': '#F5F5F5',
    'border': '#E5E7EB',
    'text_primary': '#333333',
    'text_secondary': '#888888',
    'text_tertiary': '#A0A0A0',
    'accent': '#F98C53',
    'success': '#D2E0AA',
    'blue': '#ABD7FB',
    'peach': "#F6AD83",
    'today_bg': '#FFF3EC',       # 今天的日历格背景
    'today_border': '#F98C53',   # 今天的边框高亮色
    'event_dot': '#F98C53',      # 普通任务圆点
    'event_timed': '#ABD7FB',    # 有时间点事件圆点
}

CATEGORY_PATHS = {
    "分类1": r"C:\placeholder\分类1",
    "分类2": r"C:\placeholder\分类2",
    "分类3": r"C:\placeholder\分类3",
    "分类4": r"C:\placeholder\分类4",
    "其他": r"C:\placeholder\其他"
}

CATEGORIES = {
    "分类1": {"icon": "🎯", "color": COLORS['accent']},
    "分类2": {"icon": "📊", "color": COLORS['blue']},
    "分类3": {"icon": "📝", "color": COLORS['peach']},
    "分类4": {"icon": "💼", "color": "#7CB342"},
    "其他": {"icon": "📌", "color": COLORS['text_tertiary']}
}

KEYWORDS = {
    "分类1": [],
    "分类2": [],
    "分类3": [],
    "分类4": [],
    "其他": []
}

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# ==========================================
# 日历事件数据引擎
# 存储格式：calendar_events.json
# { "2026-03-25": [{"title": "组会", "time": "14:00"}, ...], ... }
# ==========================================
CALENDAR_FILE = "calendar_events.json"
ACHIEVEMENT_FILE = "achievement.json"
CALENDAR_SECTION_PREFIX = "## 📆 Markdown 日历视图"
CALENDAR_NOTE = '> 把当天最关键的交付或提醒写进格子里，配合下方看板即可完成「月历 + 任务」的联动。'

DEFAULT_ACHIEVEMENTS = {
    "路径1": {
        "节点1": False,
        "节点2": False,
        "节点3": False,
        "节点4": False,
        "节点5": False,
        "节点6": False,
        "节点7": False
    },
    "路径2": {
        "节点1": False,
        "节点2": False,
        "节点3": False,
        "节点4": False,
        "节点5": False,
        "节点6": False,
        "节点7": False,
    }
}

# ==========================================
# 成长雷达图数据引擎
# ==========================================
GROWTH_FILE = "growth_data.json"
GROWTH_DIMS = ["学习力", "情绪", "执行", "人际", "创新", "健康"]
GROWTH_INIT = 30

def load_growth_data():
    if os.path.exists(GROWTH_FILE):
        try:
            with open(GROWTH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {dim: GROWTH_INIT for dim in GROWTH_DIMS}

def save_growth_data(data):
    with open(GROWTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _sanitize_calendar_text(text):
    return text.replace("|", "/").replace("\n", " ").strip()


def _event_snippets_for_cell(events):
    snippets = []
    for ev in events:
        title = ev.get("title", "").strip()
        if not title:
            continue
        display = f"{ev['time']} {title}" if ev.get("time") else title
        display = _sanitize_calendar_text(display)
        if len(display) > 14:
            display = display[:14] + "…"
        snippets.append(display)
        if len(snippets) == 2:
            break
    return snippets


def build_monthly_calendar_block(year, month, events):
    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(year, month)
    lines = [
        f"{CALENDAR_SECTION_PREFIX}（{year} 年 {month:02d} 月）",
        "| Sun | Mon | Tue | Wed | Thu | Fri | Sat |",
        "| --- | --- | --- | --- | --- | --- | --- |"
    ]
    for week in weeks:
        row_cells = []
        for day in week:
            if not day:
                row_cells.append(" ")
                continue
            date_str = f"{year}-{month:02d}-{day:02d}"
            cell_text = str(day)
            snippets = _event_snippets_for_cell(events.get(date_str, []))
            if snippets:
                cell_text += " <br>" + "<br>".join(snippets)
            row_cells.append(cell_text)
        lines.append("| " + " | ".join(row_cells) + " |")
    lines.append("")
    lines.append(CALENDAR_NOTE)
    lines.append("")
    return "\n".join(lines)

def load_calendar_events():
    if os.path.exists(CALENDAR_FILE):
        try:
            with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_calendar_events(events):
    with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def load_achievements():
    if os.path.exists(ACHIEVEMENT_FILE):
        try:
            with open(ACHIEVEMENT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 检查 key 数量是否和当前默认值一致，不一致则重置（节点定义变了）
            needs_reset = False
            for path in DEFAULT_ACHIEVEMENTS:
                old_keys = set(data.get(path, {}).keys())
                new_keys = set(DEFAULT_ACHIEVEMENTS[path].keys())
                if old_keys != new_keys:
                    needs_reset = True
                    break
            if needs_reset:
                data = {path: dict(DEFAULT_ACHIEVEMENTS[path]) for path in DEFAULT_ACHIEVEMENTS}
                save_achievements(data)
            else:
                for path in DEFAULT_ACHIEVEMENTS:
                    if path not in data:
                        data[path] = dict(DEFAULT_ACHIEVEMENTS[path])
                    for node in DEFAULT_ACHIEVEMENTS[path]:
                        if node not in data[path]:
                            data[path][node] = False
            return data
        except:
            return dict(DEFAULT_ACHIEVEMENTS)
    return dict(DEFAULT_ACHIEVEMENTS)

def save_achievements(data):
    with open(ACHIEVEMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==========================================
# Markdown 日报引擎
# ==========================================
def get_latest_report():
    folder = "Daily_Reports"
    if not os.path.exists(folder):
        os.makedirs(folder)
    files = glob.glob(os.path.join(folder, "Daily_Report_*.md"))
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def create_today_report_with_rollover(today_filepath, previous_filepath):
    today_str = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# 📅 {today_str} 每日复盘与明日规划\n\n", "## 📊 宏观进度速览\n\n"]

    rollover_tasks = {cat: [] for cat in CATEGORIES.keys()}
    if previous_filepath and os.path.exists(previous_filepath):
        with open(previous_filepath, "r", encoding="utf-8") as f:
            prev_lines = f.readlines()
        curr_cat = None
        for line in prev_lines:
            if line.startswith("### 📁 ["):
                cat_name = line.split("[")[1].split("]")[0]
                if cat_name in CATEGORIES:
                    curr_cat = cat_name
            elif line.strip().startswith("- [ ]"):
                if curr_cat:
                    rollover_tasks[curr_cat].append(line.strip())

    for cat in CATEGORIES.keys():
        lines.extend([f"### 📁 [{cat}]\n"])
        for task in rollover_tasks[cat]:
            lines.append(f"{task}\n")
        lines.append("\n")

    with open(today_filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return today_filepath

def call_claude(prompt, callback=None, root=None, work_dir=None,
                session_id=None, system_prompt=None):
    def run():
        try:
            # --system-prompt 不是合法的 CLI 参数，中文传命令行会导致路径报错。
            # 改为把 system prompt 拼入 stdin 正文头部，彻底规避编码问题。
            actual_input = prompt
            if system_prompt and not session_id:
                actual_input = f"[系统设定]\n{system_prompt}\n[用户消息]\n{prompt}"

            cmd_parts = ['cmd', '/c', 'claude', '-p', '--output-format', 'json']
            if session_id:
                cmd_parts += ['--resume', session_id]
            if work_dir and os.path.exists(work_dir):
                cmd_parts += ['--add-dir', work_dir]

            result = subprocess.run(
                cmd_parts,
                input=actual_input.encode('utf-8'),
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            # 手动解码：优先 UTF-8，失败则 GBK（中文 Windows cmd 默认编码）
            def _decode(b):
                try:
                    return b.decode('utf-8')
                except UnicodeDecodeError:
                    return b.decode('gbk', errors='replace')

            raw = _decode(result.stdout).strip()
            stderr_txt = _decode(result.stderr).strip()

            new_session_id = None
            output = ''
            if raw:
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        output = data.get('result', '') or data.get('content', '') or raw
                        new_session_id = data.get('session_id')
                    else:
                        output = raw
                except json.JSONDecodeError:
                    output = raw
            elif stderr_txt:
                output = f"⚠️ Claude 报错:\n{stderr_txt}"
            else:
                output = "⚠️ 执行完毕，无文字返回。"
            if callback and root:
                root.after(0, lambda cb=callback, out=output, sid=new_session_id: cb(out, sid))
        except Exception as e:
            if callback and root:
                root.after(0, lambda cb=callback, err=f"❌ 调用失败: {str(e)}": cb(err, None))
    threading.Thread(target=run, daemon=True).start()


# ==========================================
# UI 组件库
# ==========================================
class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, bg_color, fg_color='#333333', **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.command = command
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.text = text
        self.config(bg=COLORS['bg_main'], height=36, cursor='hand2')
        self.draw_button()
        self.bind('<Button-1>', lambda e: self.on_click())
        self.bind('<Enter>', lambda e: self.draw_button(hover=True))
        self.bind('<Leave>', lambda e: self.draw_button(hover=False))
        self.chat_history = []   # 多轮对话历史

    def draw_button(self, hover=False):
        self.delete('all')
        width = self.winfo_reqwidth() if self.winfo_reqwidth() > 1 else 120
        c = self.bg_color
        if hover:
            rgb = tuple(max(0, min(255, int(c.lstrip('#')[i:i+2], 16) - 15)) for i in (0, 2, 4))
            c = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
        self.create_polygon(
            [8, 0, width-8, 0, width, 0, width, 8, width, 36-8, width, 36,
             width-8, 36, 8, 36, 0, 36, 0, 36-8, 0, 8, 0, 0],
            smooth=True, fill=c, outline=''
        )
        self.create_text(width//2, 18, text=self.text, fill=self.fg_color, font=('宅在家麥克筆', 11))

    def on_click(self):
        if self.command:
            self.command()


# ==========================================
# 日历事件弹窗
# ==========================================
class EventDialog(tk.Toplevel):
    """点击某一天时弹出的事件管理窗口"""
    def __init__(self, parent, date_str, events, on_save):
        super().__init__(parent)
        self.date_str = date_str
        self.events = list(events)  # 当天所有事件的副本
        self.on_save = on_save

        # 解析日期用于显示
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = WEEKDAY_CN[dt.weekday()]
        display = dt.strftime(f"%m月%d日  {weekday}")

        self.title(f"📅 {display}")
        self.configure(bg=COLORS['bg_main'])
        self.resizable(False, False)
        self.grab_set()  # 模态

        # 居中显示
        self.geometry("360x460")
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 360) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 460) // 2
        self.geometry(f"360x460+{x}+{y}")

        self._enter_pressed_once = False
        self._build_ui(display)

    def _build_ui(self, display):
        # 标题
        tk.Label(
            self, text=f"📅  {display}",
            font=('宅在家麥克筆', 14, 'bold'),
            bg=COLORS['bg_main'], fg=COLORS['text_primary']
        ).pack(pady=(18, 6), padx=20, anchor='w')

        tk.Frame(self, bg=COLORS['border'], height=1).pack(fill=tk.X, padx=20, pady=(0, 10))

        # 已有事件列表
        list_frame = tk.Frame(self, bg=COLORS['bg_main'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        tk.Label(
            list_frame, text="当天日程",
            font=('宅在家麥克筆', 11),
            bg=COLORS['bg_main'], fg=COLORS['text_secondary']
        ).pack(anchor='w', pady=(0, 6))

        self.event_listbox_frame = tk.Frame(list_frame, bg=COLORS['bg_main'])
        self.event_listbox_frame.pack(fill=tk.BOTH, expand=True)
        self._refresh_event_list()

        tk.Frame(self, bg=COLORS['border'], height=1).pack(fill=tk.X, padx=20, pady=(10, 8))

        # 添加区域
        add_frame = tk.Frame(self, bg=COLORS['bg_main'])
        add_frame.pack(fill=tk.X, padx=20, pady=(0, 6))

        tk.Label(
            add_frame, text="添加日程",
            font=('宅在家麥克筆', 11),
            bg=COLORS['bg_main'], fg=COLORS['text_secondary']
        ).pack(anchor='w', pady=(0, 6))

        row1 = tk.Frame(add_frame, bg=COLORS['bg_main'])
        row1.pack(fill=tk.X, pady=(0, 6))

        # 时间输入（可留空表示全天事件）
        tk.Label(row1, text="时间:", font=('宅在家麥克筆', 10), bg=COLORS['bg_main'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        self.time_entry = tk.Entry(
            row1, width=7,
            font=('Microsoft YaHei', 10),
            relief=tk.SOLID, bd=1,
            bg=COLORS['bg_tertiary'], fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary']
        )
        self.time_entry.insert(0, "14:00")
        self.time_entry.pack(side=tk.LEFT, padx=(4, 14), ipady=4)
        self.time_entry.bind('<Return>', self._handle_enter_press)
        self.time_entry.bind('<Key>', self._reset_enter_state)

        tk.Label(row1, text="事项:", font=('宅在家麥克筆', 10), bg=COLORS['bg_main'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        self.title_entry = tk.Entry(
            row1,
            font=('Microsoft YaHei', 10),
            relief=tk.SOLID, bd=1,
            bg=COLORS['bg_main'], fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary']
        )
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self.title_entry.bind('<Return>', self._handle_enter_press)
        self.title_entry.bind('<Key>', self._reset_enter_state)

        btn_row = tk.Frame(add_frame, bg=COLORS['bg_main'])
        btn_row.pack(fill=tk.X, pady=(4, 0))

        ModernButton(btn_row, "➕ 添加", self._add_event, bg_color=COLORS['success'], fg_color='#333333', width=160).pack(side=tk.LEFT)
        ModernButton(btn_row, "✅ 完成", self._save_and_close, bg_color=COLORS['accent'], fg_color='#FFFFFF', width=160).pack(side=tk.RIGHT)

    def _refresh_event_list(self):
        for w in self.event_listbox_frame.winfo_children():
            w.destroy()

        if not self.events:
            tk.Label(
                self.event_listbox_frame,
                text="今天暂无日程，点击下方添加～",
                font=('宅在家麥克筆', 10),
                bg=COLORS['bg_main'], fg=COLORS['text_tertiary']
            ).pack(anchor='w', pady=8)
            return

        # 按有无时间排序：有时间的先按时间排，无时间的放后面
        timed = sorted([e for e in self.events if e.get("time")], key=lambda x: x["time"])
        untimed = [e for e in self.events if not e.get("time")]
        sorted_events = timed + untimed

        for idx, ev in enumerate(sorted_events):
            row = tk.Frame(self.event_listbox_frame, bg=COLORS['bg_main'])
            row.pack(fill=tk.X, pady=2)

            # 彩色圆点
            dot_color = COLORS['event_timed'] if ev.get("time") else COLORS['success']
            dot = tk.Canvas(row, width=8, height=8, bg=COLORS['bg_main'], highlightthickness=0)
            dot.create_oval(1, 1, 7, 7, fill=dot_color, outline='')
            dot.pack(side=tk.LEFT, padx=(0, 6), pady=6)

            time_str = ev.get("time", "全天")
            display_text = f"{time_str}  {ev['title']}"
            tk.Label(
                row, text=display_text,
                font=('Microsoft YaHei', 10),
                bg=COLORS['bg_main'], fg=COLORS['text_primary'],
                anchor='w'
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

            # 删除按钮
            del_lbl = tk.Label(row, text="✖", font=('Microsoft YaHei', 9), bg=COLORS['bg_main'], fg=COLORS['text_tertiary'], cursor='hand2')
            del_lbl.pack(side=tk.RIGHT, padx=(6, 0))
            del_lbl.bind('<Enter>', lambda e, b=del_lbl: b.config(fg=COLORS['accent']))
            del_lbl.bind('<Leave>', lambda e, b=del_lbl: b.config(fg=COLORS['text_tertiary']))
            # 注意：用原始 idx 在 self.events 中对应删除，需要用 ev 的引用
            del_lbl.bind('<Button-1>', lambda e, ev_ref=ev: self._delete_event(ev_ref))

    def _add_event(self):
        title = self.title_entry.get().strip()
        if not title:
            return False
        time_raw = self.time_entry.get().strip()
        # 简单格式验证：接受 HH:MM，或留空（全天）
        time_val = ""
        if time_raw and time_raw != "留空=全天":
            if re.match(r'^\d{1,2}:\d{2}$', time_raw):
                parts = time_raw.split(":")
                time_val = f"{int(parts[0]):02d}:{parts[1]}"
            else:
                messagebox.showwarning("格式提示", "时间格式请填写 HH:MM，例如 14:30\n或直接清空表示全天事件。", parent=self)
                return False

        self.events.append({"title": title, "time": time_val})
        self.title_entry.delete(0, tk.END)
        self._refresh_event_list()
        self._enter_pressed_once = False
        return True

    def _delete_event(self, ev_ref):
        self.events = [e for e in self.events if e is not ev_ref]
        self._refresh_event_list()

    def _save_and_close(self):
        self.on_save(self.date_str, self.events)
        self.destroy()

    def _handle_enter_press(self, event=None):
        if self._enter_pressed_once:
            self._save_and_close()
            return "break"
        added = self._add_event()
        if added:
            self._enter_pressed_once = True
        return "break"

    def _reset_enter_state(self, event):
        if event.keysym == 'Return':
            return
        self._enter_pressed_once = False


# ==========================================
# 成就解锁弹窗（横向时间轴版）
# ==========================================
class AchievementsDialog(tk.Toplevel):
    NODE_COLORS = {
        "路径1": '#F98C53',   # 橙色
        "路径2": '#7CB342',      # 绿色
    }
    UNLOCKED_FILL = '#F98C53'
    LOCKED_FILL = '#E5E7EB'
    LOCKED_BORDER = '#CCCCCC'
    AXIS_COLOR = '#D1D5DB'
    LABEL_BG = '#F9F2EF'

    def __init__(self, parent, achievements_data, on_save):
        super().__init__(parent)
        self.achievements_data = achievements_data
        self.on_save = on_save
        self.title("🏆 成就解锁")
        self.configure(bg=COLORS['bg_main'])
        self.grab_set()
        self.geometry("900x420")
        self.resizable(False, False)
        self._node_frames = {}
        self.update_idletasks()  # 渲染窗口，使 winfo_width 可用
        self._build_ui()

    def _build_ui(self):
        tk.Label(
            self, text="🏆 成就解锁",
            font=('Microsoft YaHei', 16, 'bold'),
            bg=COLORS['bg_main'], fg=COLORS['text_primary']
        ).pack(pady=(18, 2))
        tk.Label(
            self, text="点击节点切换解锁状态 ✨",
            font=('Microsoft YaHei', 9),
            bg=COLORS['bg_main'], fg=COLORS['text_tertiary']
        ).pack(pady=(0, 10))

        self.content = tk.Frame(self, bg=COLORS['bg_main'])
        self.content.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 10))

        self._path_widgets = {}
        for path_name in ["路径1", "路径2"]:
            row_frame = tk.Frame(self.content, bg=COLORS['bg_main'])
            row_frame.pack(fill=tk.X, pady=(0, 18))
            self._path_widgets[path_name] = row_frame
            self._render_timeline(row_frame, path_name)

        ModernButton(
            self, "✅ 完成",
            self._save_and_close,
            bg_color=COLORS['success'], fg_color='#333333', width=200
        ).pack(pady=(8, 16))

    def _render_timeline(self, parent, path_name):
        # 路径标题
        icon = "💼" if path_name == "路径1" else "📚"
        tk.Label(
            parent, text=f"{icon}  {path_name}",
            font=('Microsoft YaHei', 12, 'bold'),
            bg=COLORS['bg_main'], fg=self.NODE_COLORS[path_name]
        ).pack(anchor='w', pady=(0, 6))

        nodes = self.achievements_data.get(path_name, {})
        node_names = list(nodes.keys())
        n = len(node_names)
        if n == 0:
            return

        # 动态计算宽度：内容区实际宽度 - 滚动条余量
        try:
            avail_w = self.content.winfo_width()
            if avail_w < 500:
                avail_w = 820
            else:
                avail_w -= 10
        except Exception:
            avail_w = 820

        canvas_h = 80
        canvas = tk.Canvas(parent, width=avail_w, height=canvas_h, bg=COLORS['bg_main'],
                           highlightthickness=0, cursor='hand2')
        canvas.pack(fill=tk.X)

        w = avail_w  # 可用宽度
        step = w / (n - 1) if n > 1 else w
        radius = 9
        axis_y = 28

        for i, node_name in enumerate(node_names):
            unlocked = nodes[node_name]
            cx = i * step

            # 轴线
            if i > 0:
                prev_unlocked = nodes[node_names[i - 1]]
                line_color = self.NODE_COLORS[path_name] if (unlocked or prev_unlocked) else self.AXIS_COLOR
                canvas.create_line((i - 1) * step, axis_y, cx, axis_y,
                                  fill=line_color, width=3)

            # 节点圆
            fill = self.NODE_COLORS[path_name] if unlocked else self.LOCKED_FILL
            outline = self.NODE_COLORS[path_name] if unlocked else self.LOCKED_BORDER
            oval = canvas.create_oval(cx - radius, axis_y - radius,
                                      cx + radius, axis_y + radius,
                                      fill=fill, outline=outline, width=2)
            # 内部符号
            if unlocked:
                canvas.create_text(cx, axis_y, text="✓", fill='white',
                                  font=('Microsoft YaHei', 9, 'bold'))
            else:
                canvas.create_text(cx, axis_y, text="○", fill='#AAAAAA',
                                  font=('Microsoft YaHei', 8))

            # 节点名（斜下方）
            canvas.create_text(cx, axis_y + 22, text=node_name,
                              fill=COLORS['text_primary'],
                              font=('Microsoft YaHei', 10),
                              anchor='n')

            # 点击区域（扩大热区）
            hit = canvas.create_oval(cx - 14, axis_y - 14, cx + 14, axis_y + 14,
                                    fill='', outline='')
            canvas.tag_bind(hit, '<Button-1>',
                            lambda e, p=path_name, n=node_name: self._toggle_node(p, n))
            canvas.tag_bind(hit, '<Enter>', lambda e, c=canvas: c.config(cursor='hand2'))
            canvas.tag_bind(hit, '<Leave>', lambda e, c=canvas: c.config(cursor=''))

    def _toggle_node(self, path_name, node_name):
        was_locked = not self.achievements_data[path_name][node_name]
        self.achievements_data[path_name][node_name] = not self.achievements_data[path_name][node_name]
        save_achievements(self.achievements_data)
        # 重绘该路径
        row_frame = self._path_widgets[path_name]
        for widget in row_frame.winfo_children():
            widget.destroy()
        self._render_timeline(row_frame, path_name)
        # 解锁时弹出祝贺
        if was_locked:
            self._show_congrats_popup(path_name, node_name)

    def _show_congrats_popup(self, path_name, node_name):
        """调 Claude 生成祝贺语，然后弹窗"""
        path_icon = "💼" if path_name == "路径1" else "📚"
        prompt = (
            f"用户刚刚解锁了成就！\n"
            f"路径：{path_icon} {path_name}\n"
            f"成就：「{node_name}」\n\n"
            f"请用温暖、有趣、有点极客感的语气，写一句恭喜话（不超过40字，带1-2个emoji）。"
            f"直接输出一句话，不要解释。"
        )

        def run():
            try:
                safe_prompt = prompt.replace('"', '\\"')
                result = subprocess.run(
                    f'claude -p "{safe_prompt}"',
                    capture_output=True, text=True, encoding='utf-8',
                    errors='ignore', shell=True, creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=60
                )
                congrats_msg = result.stdout.strip() or f"🎉 恭喜解锁「{node_name}」！继续加油！"
                self.after(0, lambda m=congrats_msg: self._show_congrats_dialog(m, node_name))
            except Exception:
                self.after(0, lambda: self._show_congrats_dialog(
                    f"🎉 恭喜解锁「{node_name}」！继续加油！", node_name))

        threading.Thread(target=run, daemon=True).start()

    def _show_congrats_dialog(self, message, node_name):
        popup = tk.Toplevel(self)
        popup.configure(bg=COLORS['bg_main'])
        popup.resizable(False, False)
        popup.grab_set()
        popup.attributes('-topmost', True)
        popup.geometry("360x200")
        popup.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 360) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 200) // 2
        popup.geometry(f"360x200+{x}+{y}")

        # 标题
        tk.Label(
            popup, text="🎊 成就解锁！",
            font=('Microsoft YaHei', 16, 'bold'),
            bg=COLORS['bg_main'], fg='#F98C53'
        ).pack(pady=(24, 8))

        # 成就名
        tk.Label(
            popup, text=f"「{node_name}」",
            font=('Microsoft YaHei', 13),
            bg=COLORS['bg_main'], fg=COLORS['text_primary']
        ).pack()

        # AI 生成的祝贺语
        tk.Label(
            popup, text=message,
            font=('Microsoft YaHei', 11),
            bg=COLORS['bg_main'], fg=COLORS['text_secondary'],
            wraplength=300, justify='center'
        ).pack(pady=(10, 16))

        # 关闭按钮
        btn = tk.Frame(popup, bg=COLORS['accent'], cursor='hand2', padx=16, pady=6)
        btn.pack()
        tk.Label(
            btn, text="✨ 继续前行",
            font=('Microsoft YaHei', 10, 'bold'),
            bg=COLORS['accent'], fg='white'
        ).pack()
        btn.bind('<Button-1>', lambda e: popup.destroy())
        for w in [popup]:
            w.bind('<Button-1>', lambda e: popup.destroy())
            w.bind('<Escape>', lambda e: popup.destroy())

    def _save_and_close(self):
        self.on_save(self.achievements_data)
        self.destroy()


# ==========================================
# 成长雷达图弹窗
# ==========================================
class GrowthRecordDialog(tk.Toplevel):
    def __init__(self, parent, growth_data, on_close=None):
        super().__init__(parent)
        self.growth_data = growth_data
        self.on_close_callback = on_close
        self.title("🌱 成长记录")
        self.configure(bg=COLORS['bg_main'])
        self.grab_set()
        self.geometry("640x520")
        self.resizable(False, False)

        # 计算居中
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 640) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 520) // 2
        self.geometry(f"640x520+{x}+{y}")

        self._fig = None
        self._canvas = None
        self._build_ui()
        self._draw_radar()

    def _build_ui(self):
        # 标题
        tk.Label(
            self, text="🌱 成长雷达图",
            font=('宅在家麥克筆', 16, 'bold'),
            bg=COLORS['bg_main'], fg=COLORS['text_primary']
        ).pack(pady=(16, 2))

        tk.Label(
            self, text="每一次复盘，都在悄悄重塑你的轮廓 ✨",
            font=('851tegakizatsu', 9),
            bg=COLORS['bg_main'], fg=COLORS['accent']
        ).pack(pady=(0, 8))

        # 图表区域
        chart_frame = tk.Frame(self, bg=COLORS['bg_main'])
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 6))

        self._canvas_frame = tk.Frame(chart_frame, bg=COLORS['bg_main'])
        self._canvas_frame.pack()

        # 说明
        tk.Label(
            self, text="💡 每次「入复盘」后，Claude 会自动分析并更新雷达图",
            font=('851tegakizatsu', 9),
            bg=COLORS['bg_main'], fg=COLORS['text_tertiary']
        ).pack(pady=(0, 8))

        # 底部
        btn_frame = tk.Frame(self, bg=COLORS['bg_main'])
        btn_frame.pack(pady=(0, 12))

        ModernButton(
            btn_frame, "🔄 刷新",
            self._draw_radar,
            bg_color=COLORS['blue'], fg_color='#333333', width=160
        ).pack(side=tk.LEFT, padx=(0, 10))

        ModernButton(
            btn_frame, "✅ 关闭",
            self._close,
            bg_color=COLORS['success'], fg_color='#333333', width=160
        ).pack(side=tk.RIGHT, padx=(10, 0))

    def _draw_radar(self):
        # 清除旧图
        for widget in self._canvas_frame.winfo_children():
            widget.destroy()

        labels = GROWTH_DIMS
        values = [max(0, min(100, self.growth_data.get(d, 0))) for d in labels]
        num_vars = len(labels)

        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        values_plot = values + [values[0]]
        angles += angles[:1]

        fig_w, fig_h = 5.5, 4.5
        self._fig = plt.figure(figsize=(fig_w, fig_h), facecolor=COLORS['bg_main'])
        ax = self._fig.add_subplot(111, polar=True, facecolor=COLORS['bg_main'])

        # 背景网格（5层：20/40/60/80/100）
        max_val = 100
        for grid_val in [20, 40, 60, 80, 100]:
            ax.plot(angles, [grid_val] * (num_vars + 1), color='#E5E7EB', linewidth=0.8, zorder=1)

        # 数据多边形
        ax.fill(angles, values_plot, color='#F98C53', alpha=0.25, zorder=2)
        ax.plot(angles, values_plot, color='#F98C53', linewidth=2.5, marker='o',
                markersize=8, markerfacecolor='#F98C53', markeredgecolor='white',
                markeredgewidth=1.5, zorder=3)

        # 维度标签
        label_font = matplotlib.font_manager.FontProperties(
            fname='C:/Windows/Fonts/msyh.ttc', size=11
        )
        for i, (angle, label, val) in enumerate(zip(angles[:-1], labels, values)):
            ax.text(angle, max_val + 5, f"{label}\n{int(val)}分",
                     ha='center', va='center',
                     fontproperties=label_font,
                     color=COLORS['text_primary'], fontsize=9, zorder=4)

        ax.set_ylim(0, max_val)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels([], fontsize=7, color='#CCCCCC')
        ax.set_xticks([])
        ax.spines['polar'].set_color('#E5E7EB')
        ax.grid(color='#F0F0F0', linewidth=0.5)
        ax.set_facecolor(COLORS['bg_main'])
        self._fig.tight_layout(pad=0.5)

        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self._canvas = FigureCanvasTkAgg(self._fig, master=self._canvas_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack()
        self._canvas._tkcanvas.configure(bg=COLORS['bg_main'])

    def _close(self):
        if self._fig:
            plt.close(self._fig)
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()


# ==========================================
# 主应用
# ==========================================
class TaskBoardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("wy成长计划")
        self.root.geometry("1200x860")
        self.root.minsize(900, 660)
        self.root.configure(bg=COLORS['bg_main'])

        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        self.root.bind("<Escape>", lambda e: self.hide_window())

        self.filepath = None
        self.file_lines = []
        self.tasks_data = {cat: [] for cat in CATEGORIES}
        self.selected_task = None
        self.checkbox_vars = []
        self.task_labels = []
        self.chat_history = []  # 和 Claude 的多轮对话上下文（备用，实际由 CLI session 维护）
        self.claude_session_id = None  # CLI 会话 ID，用于 --resume 续接上下文
        self.claude_status_var = tk.StringVar(value="🟢 Claude 空闲")
        self._claude_status_timer = None

        # 日历事件数据
        self.calendar_events = load_calendar_events()
        self.achievements_data = load_achievements()
        self.growth_data = load_growth_data()
        # 日历格子 Canvas 引用（用于刷新）
        self._day_cells = {}
        self.calendar_week_offset = 0

        self.create_widgets()
        self.load_data()
        self.load_daily_quote()

        self.setup_tray()
        self.setup_hotkey()
        self.setup_auto_review_timer()

    # ==========================================
    # 一周日历条
    # ==========================================
    def create_calendar_bar(self, parent):
        """
        在顶栏正下方渲染一条横向七天日历。
        每格显示：周几 / 日期 / 最多 2 条事件摘要（有时间点的优先）
        点击任意格子 -> 弹出 EventDialog
        """
        for child in parent.winfo_children():
            child.destroy()

        today = datetime.now().date()
        reference_date = today + timedelta(weeks=self.calendar_week_offset)
        monday = reference_date - timedelta(days=reference_date.weekday())
        week_end = monday + timedelta(days=6)

        nav_frame = tk.Frame(parent, bg=COLORS['bg_main'])
        nav_frame.pack(fill=tk.X, pady=(0, 6))

        btn_style = dict(font=('宅在家麥克筆', 8), bg=COLORS['bg_secondary'], fg=COLORS['text_primary'], bd=0, cursor='hand2', padx=12, pady=6)
        tk.Button(nav_frame, text="← 上一周", command=lambda: self.shift_calendar_week(-1), **btn_style).pack(side=tk.LEFT)

        label_text = f"{monday.strftime('%m/%d')} - {week_end.strftime('%m/%d')}"
        if self.calendar_week_offset == 0:
            label_text += "  本周"
        elif self.calendar_week_offset < 0:
            label_text += f"  ({abs(self.calendar_week_offset)} 周前)"
        else:
            label_text += f"  ({self.calendar_week_offset} 周后)"
        tk.Label(
            nav_frame,
            text=label_text,
            font=('宅在家麥克筆', 10),
            bg=COLORS['bg_main'],
            fg=COLORS['text_primary']
        ).pack(side=tk.LEFT, expand=True)

        tk.Button(nav_frame, text="下一周 →", command=lambda: self.shift_calendar_week(1), **btn_style).pack(side=tk.RIGHT)

        bar = tk.Frame(parent, bg=COLORS['bg_main'])
        bar.pack(fill=tk.X)
        for col in range(7):
            bar.grid_columnconfigure(col, weight=1, uniform="week")
        bar.grid_rowconfigure(0, weight=1)

        self._day_cells.clear()

        for i in range(7):
            day = monday + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            is_today = (day == today)

            cell_bg = COLORS['today_bg'] if is_today else COLORS['bg_main']
            border_color = COLORS['today_border'] if is_today else COLORS['border']

            pad = (0, 4) if i < 6 else (0, 0)
            cell_outer = tk.Frame(bar, bg=border_color, highlightthickness=0, padx=1, pady=1)
            cell_outer.grid(row=0, column=i, sticky="nsew", padx=pad)

            cell = tk.Frame(cell_outer, bg=cell_bg, cursor='hand2')
            cell.pack(fill=tk.BOTH, expand=True)

            # 周几标签
            wd_label = tk.Label(
                cell,
                text=WEEKDAY_CN[i],
                font=('宅在家麥克筆', 8),
                bg=cell_bg,
                fg=COLORS['today_border'] if is_today else COLORS['text_secondary']
            )
            wd_label.pack(pady=(6, 0))

            # 日期数字（今天加圆圈高亮）
            date_lbl = tk.Label(
                cell,
                text=str(day.day),
                font=('宅在家麥克筆', 10, 'bold') if is_today else ('宅在家麥克筆', 11),
                bg=cell_bg,
                fg=COLORS['today_border'] if is_today else COLORS['text_primary']
            )
            date_lbl.pack()

            # 事件摘要区
            ev_frame = tk.Frame(cell, bg=cell_bg)
            ev_frame.pack(fill=tk.X, padx=4, pady=(2, 6))

            self._day_cells[day_str] = (cell, ev_frame, cell_bg)
            self._render_cell_events(day_str, ev_frame, cell_bg)

            # 点击整格弹出事件管理
            for widget in [cell, wd_label, date_lbl, ev_frame]:
                widget.bind('<Button-1>', lambda e, ds=day_str: self.open_event_dialog(ds))

            # 悬停高亮
            hover_bg = '#FFF8F5' if is_today else '#FAFAFA'
            for widget in [cell, wd_label, date_lbl, ev_frame]:
                widget.bind('<Enter>', lambda e, c=cell, bg=hover_bg: c.config(bg=bg))
                widget.bind('<Leave>', lambda e, c=cell, bg=cell_bg: c.config(bg=bg))

    def _render_cell_events(self, day_str, ev_frame, cell_bg):
        """渲染某天格子里的事件摘要（最多显示 2 条）"""
        for w in ev_frame.winfo_children():
            w.destroy()

        events = self.calendar_events.get(day_str, [])
        # 有时间点的优先显示
        timed = sorted([e for e in events if e.get("time")], key=lambda x: x["time"])
        untimed = [e for e in events if not e.get("time")]
        sorted_ev = timed + untimed

        for ev in sorted_ev[:2]:
            row = tk.Frame(ev_frame, bg=cell_bg)
            row.pack(fill=tk.X, pady=1)

            dot_color = COLORS['event_timed'] if ev.get("time") else COLORS['success']
            dot = tk.Canvas(row, width=6, height=6, bg=cell_bg, highlightthickness=0)
            dot.create_oval(0, 0, 6, 6, fill=dot_color, outline='')
            dot.pack(side=tk.LEFT, pady=3)

            time_prefix = f"{ev['time']} " if ev.get("time") else ""
            title_short = (ev['title'][:6] + "…") if len(ev['title']) > 6 else ev['title']
            tk.Label(
                row,
                text=f"{time_prefix}{title_short}",
                font=('Microsoft YaHei', 7),
                bg=cell_bg,
                fg=COLORS['text_secondary'],
                anchor='w'
            ).pack(side=tk.LEFT)

            row.bind('<Button-1>', lambda e, ds=day_str: self.open_event_dialog(ds))

        # 如果还有更多事件，显示省略提示
        if len(events) > 2:
            tk.Label(
                ev_frame,
                text=f"+{len(events)-2} 项",
                font=('Microsoft YaHei', 7),
                bg=cell_bg,
                fg=COLORS['text_tertiary']
            ).pack(anchor='w')

    def open_event_dialog(self, day_str):
        events = self.calendar_events.get(day_str, [])
        EventDialog(self.root, day_str, events, self._on_events_saved)

    def _on_events_saved(self, day_str, new_events):
        """EventDialog 保存后的回调"""
        if new_events:
            self.calendar_events[day_str] = new_events
        elif day_str in self.calendar_events:
            del self.calendar_events[day_str]
        save_calendar_events(self.calendar_events)
        self.sync_markdown_calendar_section()
        # 刷新对应格子
        if day_str in self._day_cells:
            _, ev_frame, cell_bg = self._day_cells[day_str]
            self._render_cell_events(day_str, ev_frame, cell_bg)

    def _open_achievements(self):
        AchievementsDialog(self.root, self.achievements_data, self._on_achievements_saved)

    def _on_achievements_saved(self, data):
        self.achievements_data = data

    def _open_growth_record(self):
        GrowthRecordDialog(self.root, self.growth_data)

    def _analyze_review_and_update_growth(self, review_text):
        """将复盘内容发送给 Claude 分析，更新雷达图维度"""
        dims_str = "、".join(GROWTH_DIMS)
        prompt = (
            f"你是我的成长分析师，直接输出分析结果，不要任何多余文字。\n\n"
            f"用户复盘内容：「{review_text}」\n\n"
            f"雷达图6个维度（初始30分，满分100）：{dims_str}\n\n"
            f"输出格式（只输出这一行）：\n"
            f"【成长分析】维度A:+N,维度B:+N\n\n"
            f"示例：「打了羽毛球」→ 【成长分析】健康:+3\n"
            f"示例：「完成Stata merge」→ 【成长分析】学习力:+3,执行:+2\n"
            f"示例：「和朋友吵架了」→ 【成长分析】人际:-2,情绪:-1\n"
            f"无明显变化：输出【成长分析】无变化"
        )

        def analysis_callback(response, _sid=None):
            if "⚠️" in response:
                self.append_chat("🌱 雷达图更新", "分析失败，稍后重试", COLORS['accent'])
                return
            self._apply_growth_analysis(response)

        call_claude(prompt, analysis_callback, self.root)

    def _apply_growth_analysis(self, response):
        """解析 Claude 的分析结果并更新雷达图数据"""
        # 提取【成长分析】段落（如果 Claude 夹杂了解释文字）
        analysis_block = response
        if '【成长分析】' in response:
            start = response.index('【成长分析】')
            analysis_block = response[start:].split('\n')[0]

        # 维度别名映射（兼容 Claude 可能用的不同说法）
        DIM_ALIASES = {
            "学习力": ["学习力", "学习", "学习能力"],
            "情绪": ["情绪", "情绪管理", "心理健康"],
            "执行": ["执行", "执行力", "行动力"],
            "人际": ["人际", "人际关系", "人际沟通", "社交"],
            "创新": ["创新", "创新能力", "创造力", "创意"],
            "健康": ["健康", "身体健康", "体能", "运动", "体质"],
        }

        changes = []
        for dim, aliases in DIM_ALIASES.items():
            for alias in aliases:
                pattern = rf'{re.escape(alias)}:([+-]\d+)'
                match = re.search(pattern, analysis_block)
                if match:
                    delta = int(match.group(1))
                    old_val = self.growth_data.get(dim, GROWTH_INIT)
                    new_val = max(0, min(100, old_val + delta))
                    if new_val != old_val:
                        self.growth_data[dim] = new_val
                        sign = '+' if delta > 0 else ''
                        changes.append(f"{dim} {sign}{delta}")
                    break  # 找到匹配就跳过该维度的其他别名

        if changes:
            save_growth_data(self.growth_data)
            self.append_chat(
                "🌱 雷达图更新",
                " | ".join(changes),
                COLORS['accent']
            )
        else:
            self.append_chat(
                "🌱 雷达图更新",
                "无变化",
                COLORS['text_secondary']
            )

    def shift_calendar_week(self, delta_weeks):
        self.calendar_week_offset += delta_weeks
        self.create_calendar_bar(self.calendar_block)

    # ==========================================
    # 主界面构建
    # ==========================================
    def create_widgets(self):
        # === 顶栏：日期 + 语录 + 盲盒图 ===
        top_bar = tk.Frame(self.root, bg=COLORS['bg_main'])
        top_bar.pack(fill=tk.X, padx=20, pady=(15, 8))

        left_ctrl = tk.Frame(top_bar, bg=COLORS['bg_main'])
        left_ctrl.pack(side=tk.LEFT, fill=tk.Y)

        date_frame = tk.Frame(left_ctrl, bg=COLORS['bg_main'])
        date_frame.pack(anchor='w')

        tk.Label(
            date_frame,
            text=datetime.now().strftime("%Y年%m月%d日"),
            font=('宅在家麥克筆', 16, 'bold'),
            bg=COLORS['bg_main'], fg=COLORS['text_primary']
        ).pack(side=tk.LEFT, padx=(0, 20))

        self.quote_label = tk.Label(
            left_ctrl,
            text="💡 正在呼叫 Claude 获取今日灵感...",
            font=('851tegakizatsu', 10, 'italic'),
            fg=COLORS['accent'], bg=COLORS['bg_main']
        )
        self.quote_label.pack(anchor='w', pady=(8, 0))

        # 右上角每日双图盲盒 + 成就按钮
        self.img_frame = tk.Frame(top_bar, bg=COLORS['bg_main'])
        self.img_frame.pack(side=tk.RIGHT, padx=(0, 10))
        self.img_label_1 = tk.Label(self.img_frame, bg=COLORS['bg_main'])
        self.img_label_1.pack(side=tk.LEFT, padx=5)
        self.img_label_2 = tk.Label(self.img_frame, bg=COLORS['bg_main'])
        self.img_label_2.pack(side=tk.LEFT, padx=5)

        self.achievement_btn = ModernButton(
            top_bar, "🏆 成就",
            self._open_achievements,
            bg_color=COLORS['peach'], fg_color='#333333', width=90
        )
        self.achievement_btn.pack(side=tk.RIGHT, padx=(0, 10), pady=(0, 4))

        self.growth_btn = ModernButton(
            top_bar, "🌱 成长",
            self._open_growth_record,
            bg_color='#B2DFDB', fg_color='#333333', width=90
        )
        self.growth_btn.pack(side=tk.RIGHT, padx=(0, 10), pady=(0, 4))

        self.load_daily_illustrations()

        # === 一周日历条（顶栏下方，内容区上方）===
        self.calendar_block = tk.Frame(self.root, bg=COLORS['bg_main'])
        self.calendar_block.pack(fill=tk.X, padx=20, pady=(0, 12))
        self.create_calendar_bar(self.calendar_block)

        # 细分割线
        tk.Frame(self.root, bg=COLORS['border'], height=1).pack(fill=tk.X, padx=20, pady=(0, 12))

        # === 主内容区（左任务 + 右助手）===
        content = tk.PanedWindow(
            self.root, orient=tk.HORIZONTAL,
            bg=COLORS['bg_main'], bd=0, sashwidth=8, sashcursor="sb_h_double_arrow"
        )
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # 左侧任务区
        left_wrapper = tk.Frame(content, bg=COLORS['bg_main'])
        content.add(left_wrapper, minsize=400, stretch="always")

        self.left_panel = tk.Frame(left_wrapper, bg=COLORS['bg_main'])
        self.left_panel.pack(fill=tk.BOTH, expand=True, padx=(0, 15))

        self.canvas = tk.Canvas(self.left_panel, bg=COLORS['bg_main'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.left_panel, orient=tk.VERTICAL, command=self.canvas.yview)
        self.task_container = tk.Frame(self.canvas, bg=COLORS['bg_main'])

        self.task_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.task_container, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def on_panel_resize(event):
            canvas_width = event.width - 20
            if canvas_width > 0:
                self.canvas.itemconfig(self.canvas_window, width=canvas_width)
            wrap_width = canvas_width - 80
            if wrap_width > 50 and hasattr(self, 'task_labels'):
                for lbl in self.task_labels:
                    try:
                        lbl.config(wraplength=wrap_width)
                    except:
                        pass

        self.left_panel.bind('<Configure>', on_panel_resize)

        def on_mousewheel(event):
            x, y = self.root.winfo_pointerxy()
            widget = self.root.winfo_containing(x, y)
            if widget and str(widget).startswith(str(self.left_panel)):
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.root.bind("<MouseWheel>", on_mousewheel)

        # 右侧 Claude 助手区
        right_panel = tk.Frame(content, bg=COLORS['bg_secondary'])
        content.add(right_panel, minsize=350, width=420, stretch="never")

        tk.Label(
            right_panel, text="呼叫小克",
            font=('宅在家麥克筆', 14),
            bg=COLORS['bg_secondary'], fg=COLORS['text_primary']
        ).pack(anchor='w', padx=20, pady=(15, 10))

        self.claude_status_label = tk.Label(
            right_panel,
            textvariable=self.claude_status_var,
            font=('851tegakizatsu', 9),
            bg=COLORS['bg_secondary'], fg=COLORS['text_secondary']
        )
        self.claude_status_label.pack(anchor='w', padx=20, pady=(0, 6))

        self.selected_task_label = tk.Label(
            right_panel, text="未选择任务",
            font=('宅在家麥克筆', 9),
            bg=COLORS['bg_secondary'], fg=COLORS['text_secondary'],
            wraplength=380, justify=tk.LEFT
        )
        self.selected_task_label.pack(anchor='w', padx=20, pady=(0, 15))

        custom_frame = tk.Frame(right_panel, bg=COLORS['bg_secondary'])
        custom_frame.pack(fill=tk.X, padx=15, pady=(5, 6))

        # 任务分类选择（+任务时用）
        cat_row = tk.Frame(custom_frame, bg=COLORS['bg_secondary'])
        cat_row.pack(fill=tk.X, pady=(0, 4))
        tk.Label(cat_row, text="分类：", font=('851tegakizatsu', 10), bg=COLORS['bg_secondary'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        self.cat_combo = ttk.Combobox(
            cat_row, values=list(CATEGORIES.keys()),
            state="readonly", width=14, font=('851tegakizatsu', 10)
        )
        self.cat_combo.current(3)
        self.cat_combo.pack(side=tk.LEFT)

        self.unified_input = tk.Entry(
            custom_frame,
            font=('Microsoft YaHei', 10),
            relief=tk.SOLID, bd=1,
            bg=COLORS['bg_main'], fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary']
        )
        self.unified_input.pack(fill=tk.X, pady=(0, 6), ipady=6)
        self.unified_input.bind('<Return>', lambda e: self._handle_unified_input())

        btn_row = tk.Frame(custom_frame, bg=COLORS['bg_secondary'])
        btn_row.pack(fill=tk.X)
        ModernButton(btn_row, "问小克", self._on_ask_claude, bg_color=COLORS['accent'], fg_color='#FFFFFF', width=125).pack(side=tk.LEFT, padx=(0, 4))
        ModernButton(btn_row, "入复盘", self._on_save_review, bg_color=COLORS['peach'], fg_color='#333333', width=125).pack(side=tk.LEFT, padx=(0, 4))
        ModernButton(btn_row, "+ 任务", self._on_add_task, bg_color=COLORS['success'], fg_color='#333333', width=125).pack(side=tk.RIGHT)

        self.claude_output = scrolledtext.ScrolledText(
            right_panel,
            font=('Microsoft YaHei', 10),
            wrap=tk.WORD, relief=tk.FLAT,
            bg=COLORS['bg_main'], fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary']
        )
        self.claude_output.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    # ==========================================
    # 数据加载与任务渲染
    # ==========================================
    def load_data(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        folder = "Daily_Reports"
        if not os.path.exists(folder):
            os.makedirs(folder)
        today_filepath = os.path.join(folder, f"Daily_Report_{today_str}.md")

        if not os.path.exists(today_filepath):
            latest_file = get_latest_report()
            self.filepath = create_today_report_with_rollover(today_filepath, latest_file)
        else:
            self.filepath = today_filepath

        with open(self.filepath, "r", encoding="utf-8") as f:
            self.file_lines = f.readlines()

        current_report_text = "".join(self.file_lines)
        if not all(f"### 📁 [{cat}]" in current_report_text for cat in CATEGORIES):
            self.filepath = create_today_report_with_rollover(today_filepath, None)
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.file_lines = f.readlines()

        self.ensure_monthly_calendar_section()

        start_idx, end_idx = -1, -1
        for i, line in enumerate(self.file_lines):
            if "## 📊 宏观进度速览" in line:
                start_idx = i
            elif line.startswith("### 📁 [") and start_idx != -1 and end_idx == -1:
                end_idx = i

        if start_idx != -1 and end_idx != -1 and hasattr(self, 'review_text'):
            review_content = "".join(self.file_lines[start_idx + 1:end_idx]).strip()
            self.review_text.delete('1.0', tk.END)
            self.review_text.insert('1.0', review_content)

        if not hasattr(self, "task_order_map"):
            self.task_order_map = {}
        category_order_next = {cat: 0 for cat in CATEGORIES}
        for (cat_name, _), order_val in self.task_order_map.items():
            if cat_name in category_order_next:
                category_order_next[cat_name] = max(category_order_next[cat_name], order_val + 1)

        self.tasks_data = {cat: [] for cat in CATEGORIES}
        current_cat = None

        for i, line in enumerate(self.file_lines):
            if line.startswith("### 📁 ["):
                cat_name = line.split("[")[1].split("]")[0]
                if cat_name in CATEGORIES:
                    current_cat = cat_name
            elif line.strip().startswith("- [ ]") or line.strip().startswith("- [x]"):
                if current_cat:
                    is_completed = "[x]" in line[:10].lower()
                    text = line.strip()[5:].strip()
                    key = (current_cat, text)
                    if key not in self.task_order_map:
                        self.task_order_map[key] = category_order_next[current_cat]
                        category_order_next[current_cat] += 1
                    self.tasks_data[current_cat].append({
                        "text": text,
                        "is_completed": is_completed,
                        "line_index": i,
                        "order": self.task_order_map[key],
                        "category": current_cat
                    })
        self.render_ui_tasks()

    def ensure_monthly_calendar_section(self):
        self.sync_markdown_calendar_section()

    def sync_markdown_calendar_section(self):
        today = datetime.now()
        block_content = build_monthly_calendar_block(today.year, today.month, self.calendar_events)
        block_lines = block_content.splitlines(keepends=True)
        start_idx, end_idx = self._find_calendar_section_range()
        if start_idx is None:
            header_idx = next(
                (i for i, line in enumerate(self.file_lines) if line.strip().startswith("## 📊 宏观进度速览")),
                None
            )
            if header_idx is None:
                return
            insert_pos = header_idx + 1
            self.file_lines[insert_pos:insert_pos] = block_lines
        else:
            self.file_lines[start_idx:end_idx] = block_lines
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.writelines(self.file_lines)

    def _find_calendar_section_range(self):
        start_idx = next(
            (i for i, line in enumerate(self.file_lines) if line.strip().startswith(CALENDAR_SECTION_PREFIX)),
            None
        )
        if start_idx is None:
            return None, None
        end_idx = start_idx + 1
        while end_idx < len(self.file_lines):
            stripped = self.file_lines[end_idx].strip()
            if stripped.startswith("- ") or self.file_lines[end_idx].startswith("### 📁 ["):
                break
            end_idx += 1
        return start_idx, end_idx

    def save_shared_review(self):
        txt = self.unified_input.get().strip()
        if not txt: return
        self.save_shared_review_with_text(txt)
        self.unified_input.delete(0, tk.END)

    def save_shared_review_with_text(self, new_text):
        start_idx, end_idx = -1, -1
        for i, line in enumerate(self.file_lines):
            if "## 📊 宏观进度速览" in line:
                start_idx = i
            elif line.startswith("### 📁 [") and start_idx != -1 and end_idx == -1:
                end_idx = i
        if start_idx != -1 and end_idx != -1:
            time_str = datetime.now().strftime("%H:%M")
            note_line = f"- 🕒 [{time_str}] {new_text}\n"
            self.file_lines.insert(end_idx, note_line)
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.writelines(self.file_lines)
            self.append_chat("📝 系统广播:", f"已将随笔存入今日文档：{new_text}", COLORS['peach'])
            self._analyze_review_and_update_growth(new_text)

    def add_new_task(self):
        txt = self.unified_input.get().strip()
        if not txt: return
        self.add_new_task_with_text(txt)
        self.unified_input.delete(0, tk.END)

    def add_new_task_with_text(self, text):
        cat = self.cat_combo.get()
        cat_header = f"### 📁 [{cat}]\n"
        if cat_header in self.file_lines:
            idx = self.file_lines.index(cat_header)
            self.file_lines.insert(idx + 1, f"- [ ] {text}\n")
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.writelines(self.file_lines)
            self.load_data()

    def delete_task(self, task):
        if not messagebox.askyesno("确认删除", f"确定要彻底删除这个任务吗？\n\n「{task['text']}」"):
            return
        idx = task["line_index"]
        del self.file_lines[idx]
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.writelines(self.file_lines)
        self.load_data()

    def execute_task_transfer(self, keyword, target_date):
        task_line = None
        current_cat = None
        target_cat = "其他"
        new_lines = []
        for line in self.file_lines:
            if line.startswith("### 📁 ["):
                current_cat = line.split("[")[1].split("]")[0]
                new_lines.append(line)
            elif line.strip().startswith("- [ ]") and keyword.lower() in line.lower():
                task_line = line
                if current_cat:
                    target_cat = current_cat
            else:
                new_lines.append(line)
        if not task_line:
            self.append_chat("⚠️ 系统拦截:", f"转移失败。未找到包含「{keyword}」的未完成任务。", COLORS['accent'])
            return
        self.file_lines = new_lines
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.writelines(self.file_lines)
        if len(target_date) < 8:
            target_date = f"2026-{target_date.replace('.', '-').replace('/', '-')}"
            if len(target_date.split('-')[1]) == 1:
                parts = target_date.split('-')
                target_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        target_filepath = os.path.join("Daily_Reports", f"Daily_Report_{target_date}.md")
        if os.path.exists(target_filepath):
            with open(target_filepath, "r", encoding="utf-8") as f:
                target_lines = f.readlines()
        else:
            target_lines = [f"# 📅 {target_date} 每日复盘与明日规划\n\n", "## 📊 宏观进度速览\n\n"]
            for cat in CATEGORIES.keys():
                target_lines.extend([f"### 📁 [{cat}]\n", "\n"])
        insert_idx = -1
        for i, line in enumerate(target_lines):
            if line.startswith(f"### 📁 [{target_cat}]"):
                insert_idx = i + 1
                break
        if insert_idx != -1:
            target_lines.insert(insert_idx, task_line)
        else:
            target_lines.extend([f"### 📁 [{target_cat}]\n", task_line, "\n"])
        with open(target_filepath, "w", encoding="utf-8") as f:
            f.writelines(target_lines)
        self.load_data()
        self.append_chat("✅ 系统广播:", f"空间跃迁成功！「{keyword}」已被转移至 {target_date}。", COLORS['success'])

    def execute_task_split(self, keyword, sub_tasks_str):
        sub_tasks = [t.strip() for t in re.split(r'[,，]', sub_tasks_str) if t.strip()]
        if not sub_tasks:
            return
        new_lines = []
        found = False
        for line in self.file_lines:
            if not found and line.strip().startswith("- [ ]") and keyword.lower() in line.lower():
                for st in sub_tasks:
                    new_lines.append(f"- [ ] {st}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            self.append_chat("⚠️ 系统拦截:", f"拆解失败。未找到包含「{keyword}」的未完成任务。", COLORS['accent'])
            return
        self.file_lines = new_lines
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.writelines(self.file_lines)
        self.load_data()
        self.append_chat("🧬 细胞分裂完成:", f"任务「{keyword}」已拆解为 {len(sub_tasks)} 个小步骤！", COLORS['success'])

    def execute_create_file(self, filename, code_content):
        work_dir = self.get_current_task_dir()
        if not work_dir:
            work_dir = "Generated_Codes"
            if not os.path.exists(work_dir):
                os.makedirs(work_dir)
        filepath = os.path.join(work_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code_content)
            self.append_chat("💾 实体化成功:", f"已生成文件：{filename}\n保存路径：{work_dir}", COLORS['blue'])
        except Exception as e:
            self.append_chat("⚠️ 实体化失败:", f"保存文件时遇到问题：{e}", COLORS['accent'])

    def toggle_task(self, task):
        idx = task["line_index"]
        line = self.file_lines[idx]
        if "- [ ]" in line:
            self.file_lines[idx] = line.replace("- [ ]", "- [x]", 1)
        elif "- [x]" in line:
            self.file_lines[idx] = line.replace("- [x]", "- [ ]", 1)
        category = task.get("category")
        if category:
            self.reorder_category_tasks_in_file(category)
        else:
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.writelines(self.file_lines)
        self.load_data()

    def reorder_category_tasks_in_file(self, category):
        cat_header = f"### 📁 [{category}]"
        header_idx = next(
            (i for i, line in enumerate(self.file_lines) if line.startswith(cat_header)),
            None
        )
        if header_idx is None:
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.writelines(self.file_lines)
            return

        task_indices = []
        end_idx = header_idx + 1
        while end_idx < len(self.file_lines):
            line = self.file_lines[end_idx]
            if line.startswith("### 📁 ["):
                break
            if line.strip().startswith("- ["):
                task_indices.append(end_idx)
            end_idx += 1

        if not task_indices:
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.writelines(self.file_lines)
            return

        sortable_tasks = []
        for idx in task_indices:
            line = self.file_lines[idx]
            text = line.strip()[5:].strip()
            key = (category, text)
            order_val = self.task_order_map.get(key, 0)
            is_completed = "- [x]" in line[:10].lower()
            sortable_tasks.append((is_completed, order_val, line))

        sortable_tasks.sort(key=lambda item: (item[0], item[1]))
        for idx, (_, _, new_line) in zip(task_indices, sortable_tasks):
            self.file_lines[idx] = new_line

        with open(self.filepath, "w", encoding="utf-8") as f:
            f.writelines(self.file_lines)

    def render_ui_tasks(self):
        for widget in self.task_container.winfo_children():
            widget.destroy()
        self.checkbox_vars.clear()
        self.task_labels = []

        for category, tasks in self.tasks_data.items():
            if not tasks:
                continue
            ordered_tasks = sorted(
                tasks,
                key=lambda t: (t["is_completed"], t.get("order", 0))
            )
            cat_card = tk.Frame(
                self.task_container, bg=COLORS['bg_secondary'],
                highlightthickness=1, highlightbackground=COLORS['border']
            )
            cat_card.pack(fill=tk.X, pady=(0, 12))

            cat_title_frame = tk.Frame(cat_card, bg=COLORS['bg_secondary'])
            cat_title_frame.pack(fill=tk.X, padx=20, pady=10)

            tk.Label(
                cat_title_frame,
                text=f"{CATEGORIES[category]['icon']}  {category}",
                font=('宅在家麥克筆', 12),
                bg=COLORS['bg_secondary'],
                fg=CATEGORIES[category]['color']
            ).pack(side=tk.LEFT)

            folder_path = CATEGORY_PATHS.get(category, "")
            if folder_path and os.path.exists(folder_path):
                ModernButton(
                    cat_title_frame, "📂 目录",
                    lambda p=folder_path: os.startfile(p),
                    bg_color=COLORS['peach'], width=100
                ).pack(side=tk.RIGHT)

            for task in ordered_tasks:
                bg_color = COLORS['bg_tertiary'] if task["is_completed"] else COLORS['bg_main']
                task_inner = tk.Frame(cat_card, bg=bg_color)
                task_inner.pack(fill=tk.X, padx=2, pady=1)

                var = tk.BooleanVar(value=task["is_completed"])
                self.checkbox_vars.append(var)

                del_btn = tk.Label(task_inner, text="✖", font=('851tegakizatsu', 10), bg=bg_color, fg=COLORS['text_tertiary'], cursor='hand2')
                del_btn.pack(side=tk.RIGHT, padx=(10, 20))
                del_btn.bind('<Enter>', lambda e, b=del_btn: b.config(fg=COLORS['accent']))
                del_btn.bind('<Leave>', lambda e, b=del_btn: b.config(fg=COLORS['text_tertiary']))
                del_btn.bind('<Button-1>', lambda e, t=task: self.delete_task(t))

                cb = tk.Checkbutton(
                    task_inner, variable=var,
                    command=lambda t=task: self.toggle_task(t),
                    bg=bg_color, activebackground=bg_color,
                    selectcolor=bg_color, borderwidth=0, cursor='hand2'
                )
                cb.pack(side=tk.LEFT, padx=(30, 20), pady=10)

                lbl = tk.Label(
                    task_inner, text=task["text"],
                    font=('851tegakizatsu', 11),
                    bg=bg_color,
                    fg=COLORS['text_secondary'] if task["is_completed"] else COLORS['text_primary'],
                    justify=tk.LEFT, cursor='hand2'
                )
                lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
                self.task_labels.append(lbl)

                if task["is_completed"]:
                    lbl.config(font=('851tegakizatsu', 11, 'overstrike'))
                lbl.bind('<Button-1>', lambda e, t=task["text"]: self.select_task(t))

    # ==========================================
    # Claude 交互
    # ==========================================
    def load_daily_quote(self):
        quote_folder = "Daily_Quotes"
        if not os.path.exists(quote_folder):
            os.makedirs(quote_folder)
        today_str = datetime.now().strftime("%Y-%m-%d")
        quote_file = os.path.join(quote_folder, f"Quote_{today_str}.txt")
        if os.path.exists(quote_file):
            with open(quote_file, "r", encoding="utf-8") as f:
                quote = f.read().strip()
            self.quote_label.config(text=f"💡 {quote}")
            return

        def fetch_quote():
            prompt = "请用一句话鼓励一位正在处理复杂任务、容易焦虑的研究生，请你带一个emoji，直接输出这句话，绝对不要任何废话，字数控制在30字以内。"
            command = f'claude "{prompt.replace(chr(34), chr(92)+chr(34))}"'
            try:
                result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                output = result.stdout.strip()
                if output:
                    with open(quote_file, "w", encoding="utf-8") as f:
                        f.write(output)
                    self.root.after(0, lambda: self.quote_label.config(text=f"💡 {output}"))
                else:
                    self.root.after(0, lambda: self.quote_label.config(text="💡 面对数据的繁杂，保持内心的平静。"))
            except:
                self.root.after(0, lambda: self.quote_label.config(text="💡 面对数据的繁杂，保持内心的平静。"))

        threading.Thread(target=fetch_quote, daemon=True).start()

    def get_current_task_dir(self):
        if not self.selected_task:
            return None
        for cat, tasks in self.tasks_data.items():
            for t in tasks:
                if t["text"] == self.selected_task:
                    return CATEGORY_PATHS.get(cat)
        return None

    def select_task(self, task_text):
        self.selected_task = task_text
        self.selected_task_label.config(text=f"📌 {task_text}")
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(task_text)
            self.root.update()
        except Exception:
            pass

    def append_chat(self, sender, text, color):
        self.claude_output.insert(tk.END, f"{sender}\n", "sender")
        self.claude_output.insert(tk.END, f"{text}\n\n", "text")
        self.claude_output.tag_config("sender", font=('851tegakizatsu', 10, 'bold'), foreground=COLORS['accent'])
        self.claude_output.tag_config("text", foreground=color)
        self.claude_output.see(tk.END)

    def _set_claude_status(self, text):
        self.claude_status_var.set(text)
        if getattr(self, '_claude_status_timer', None) and self.root:
            self.root.after_cancel(self._claude_status_timer)
            self._claude_status_timer = None

    def _handle_unified_input(self):
        """回车默认触发问小克"""
        self._on_ask_claude()

    def _on_ask_claude(self):
        self.ask_custom()

    def _on_save_review(self):
        txt = self.unified_input.get().strip()
        if not txt: return
        self.unified_input.delete(0, tk.END)
        self.save_shared_review_with_text(txt)

    def _on_add_task(self):
        txt = self.unified_input.get().strip()
        if not txt: return
        self.unified_input.delete(0, tk.END)
        self.add_new_task_with_text(txt)

    def ask_custom(self):
        txt = self.unified_input.get().strip()
        if not txt: return
        self.unified_input.delete(0, tk.END)
        self.ask_custom_with_text(txt)

    def ask_custom_with_text(self, txt):
        self.append_chat("👤 wy:", txt, COLORS['text_secondary'])

        # 仅在首次会话时传入系统提示；后续 --resume 自动携带历史
        sys_prompt = None
        if not self.claude_session_id:
            sys_prompt = (
                "你是一个高级日程管家与反拖延助理，服务对象是研究生，"
                "核心任务：分类1、分类2、分类3、分类4。"
                "隐藏能力：若用户要改期任务，回复中包含【MOVE:关键词|YYYY-MM-DD】；"
                "若要拆解任务，包含【SPLIT:关键词|步骤1,步骤2】；"
                "若要写代码文件，先输出【CREATE_FILE:文件名】再给```代码块。"
                "语言极度简洁，带emoji，不要废话。"
            )

        self._set_claude_status("⏳ Claude 正在思考...")
        if self.root:
            if self._claude_status_timer:
                self.root.after_cancel(self._claude_status_timer)
            self._claude_status_timer = self.root.after(
                15000,
                lambda: self.claude_status_var.set("⌛ Claude 还在排队，网络可能较慢…")
            )
        call_claude(
            txt,
            self.show_claude_response,
            self.root,
            session_id=self.claude_session_id,
            system_prompt=sys_prompt
        )


    def show_claude_response(self, response, new_session_id=None):
        # 保存 session_id，供下一轮 --resume 使用
        if new_session_id:
            self.claude_session_id = new_session_id

        clean_response = response

        match_move = re.search(r'【MOVE:(.*?)\|(.*?)】', clean_response)
        if match_move:
            clean_response = clean_response.replace(match_move.group(0), "").strip()
            self.root.after(0, lambda: self.execute_task_transfer(match_move.group(1).strip(), match_move.group(2).strip()))

        match_split = re.search(r'【SPLIT:(.*?)\|(.*?)】', clean_response)
        if match_split:
            clean_response = clean_response.replace(match_split.group(0), "").strip()
            self.root.after(0, lambda: self.execute_task_split(match_split.group(1).strip(), match_split.group(2).strip()))

        match_file = re.search(r'【CREATE_FILE:(.*?)】', clean_response)
        if match_file:
            filename = match_file.group(1).strip()
            clean_response = clean_response.replace(match_file.group(0), "").strip()
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', clean_response, re.DOTALL)
            if code_blocks:
                code_content = code_blocks[-1].strip()
                self.root.after(0, lambda f=filename, c=code_content: self.execute_create_file(f, c))

        if clean_response.strip():
            self.append_chat("🤖 小克:", clean_response.strip(), COLORS['text_primary'])
        else:
            self.append_chat("🤖 小克:", "处理完成，这次没有文字回复。", COLORS['text_secondary'])

        self._set_claude_status("🟢 Claude 空闲")

    # ==========================================
    # 系统托盘 & 热键 & 自动复盘
    # ==========================================
    def load_daily_illustrations(self):
        img_folder = "illustrations"
        if not os.path.exists(img_folder):
            os.makedirs(img_folder)
        valid_exts = ('*.png', '*.jpg', '*.jpeg')
        all_imgs = []
        for ext in valid_exts:
            all_imgs.extend(glob.glob(os.path.join(img_folder, ext)))
        if len(all_imgs) >= 2:
            today_seed = datetime.now().strftime("%Y-%m-%d")
            random.seed(today_seed)
            selected_imgs = random.sample(all_imgs, 2)
            random.seed()
            labels = [self.img_label_1, self.img_label_2]
            self.header_img_tks = []
            for i in range(2):
                try:
                    pil_img = Image.open(selected_imgs[i])
                    target_height = 80
                    ratio = target_height / pil_img.height
                    target_width = int(pil_img.width * ratio)
                    pil_img = pil_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(pil_img)
                    self.header_img_tks.append(img_tk)
                    labels[i].config(image=img_tk)
                except Exception:
                    labels[i].config(text="[图片损坏]", fg=COLORS['text_tertiary'])
        else:
            self.img_label_1.config(text="[请在 illustrations 文件夹放入图片]", font=('851tegakizatsu', 9), fg=COLORS['border'])

    def hide_window(self):
        self.root.withdraw()

    def show_window(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)
        self.root.after(0, lambda: self.root.attributes('-topmost', True))
        self.root.after(100, lambda: self.root.attributes('-topmost', False))
        self.root.after(0, self.root.lift)
        self.root.after(0, self.root.focus_force)

    def toggle_window(self):
        if self.root.state() in ('withdrawn', 'iconic'):
            self.show_window()
        else:
            self.hide_window()

    def quit_app(self, icon, item):
        icon.stop()
        self.root.destroy()
        os._exit(0)

    def setup_tray(self):
        def create_image():
            icon_path = "tray_icon.png"
            if os.path.exists(icon_path):
                try:
                    return Image.open(icon_path)
                except Exception:
                    pass
            image = Image.new('RGB', (64, 64), color=(255, 255, 255))
            d = ImageDraw.Draw(image)
            d.ellipse((10, 10, 54, 54), fill=(249, 140, 83))
            return image

        menu = pystray.Menu(
            pystray.MenuItem("显示看板 (Alt+Q)", self.show_window),
            pystray.MenuItem("完全退出", self.quit_app)
        )
        self.tray_icon = pystray.Icon("TaskBoard", create_image(), "wy成长计划", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def setup_hotkey(self):
        try:
            keyboard.add_hotkey('alt+q', self.toggle_window)
        except:
            pass

    def auto_ai_review(self):
        self.show_window()
        completed, pending = [], []
        for cat, tasks in self.tasks_data.items():
            for t in tasks:
                if t['is_completed']:
                    completed.append(f"[{cat}] {t['text']}")
                else:
                    pending.append(f"[{cat}] {t['text']}")
        prompt = "现在是晚上10点半。这是我今天的任务进度： "
        prompt += f"✅已完成：{', '.join(completed) if completed else '无'}。 "
        prompt += f"⏳未完成：{', '.join(pending) if pending else '无'}。 "

        start_idx, end_idx = -1, -1
        for i, line in enumerate(self.file_lines):
            if "## 📊 宏观进度速览" in line:
                start_idx = i
            elif line.startswith("### 📁 [") and start_idx != -1 and end_idx == -1:
                end_idx = i
        review_text = ""
        if start_idx != -1 and end_idx != -1:
            review_text = "".join(self.file_lines[start_idx + 1:end_idx]).strip()
        if review_text:
            clean_review = review_text.replace('\n', ' ')
            prompt += f"📝我的今日随笔：{clean_review}。 "
        prompt += "请作为我的极客 AI 助手，用温暖、鼓励的语气（带emoji）帮我总结今天的工作，夸夸我的努力，并为明天未完成的任务给出简短、专业的建议。绝对不要废话。"
        self.append_chat("⏰ 小克有话说:", "wy，现在是晚上 22:30 啦！已为您自动召唤 Claude 查阅今日进度...", COLORS['accent'])
        call_claude(prompt, self.show_claude_response, self.root,
                    session_id=self.claude_session_id)

    def setup_auto_review_timer(self):
        def time_checker():
            triggered_today = False
            while True:
                now_str = datetime.now().strftime("%H:%M")
                if now_str == "22:30" and not triggered_today:
                    self.root.after(0, self.auto_ai_review)
                    triggered_today = True
                elif now_str == "01:30":
                    triggered_today = False
                time.sleep(30)

        threading.Thread(target=time_checker, daemon=True).start()


# ==========================================
# 程序入口（单例锁）
# ==========================================
if __name__ == "__main__":
    mutex_name = "wy_TaskBoard_SingleInstance_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    if last_error == 183:
        ctypes.windll.user32.MessageBoxW(
            0,
            "看板已经在后台运行啦！\n请直接按 Alt+Q 唤醒，或在右下角系统托盘找我哦~",
            "温馨提示", 0x40
        )
        sys.exit(0)

    root = tk.Tk()
    app = TaskBoardApp(root)
    root.mainloop()
