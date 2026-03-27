#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地任务看板 - 白底马卡龙色卡版
v3.0 新增：一周日历条 | 移除：同步便笺功能
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
    "雅思": r"C:\Users\王莹\Documents\雅思",
    "毕业论文（性别政策）": r"D:\Zhilian_zhaopin",
    "小论文（证言）": r"C:\Users\王莹\Desktop\MC_Relational_Testimonies",
    "实习相关": r"C:\Users\王莹\Desktop\研究生相关\求职相关",
    "其他": r"C:\Users\王莹\Desktop"
}

CATEGORIES = {
    "雅思": {"icon": "🎯", "color": COLORS['accent']},
    "毕业论文（性别政策）": {"icon": "📊", "color": COLORS['blue']},
    "小论文（证言）": {"icon": "📝", "color": COLORS['peach']},
    "实习相关": {"icon": "💼", "color": "#7CB342"},
    "其他": {"icon": "📌", "color": COLORS['text_tertiary']}
}

KEYWORDS = {
    "雅思": ["ielts", "雅思", "听力", "阅读", "写作", "口语"],
    "毕业论文（性别政策）": ["性别政策", "stata", "数据", "merge", "did", "rdd", "回归"],
    "小论文（证言）": ["证言", "小论文", "文献", "citation"],
    "实习相关": ["实习", "简历", "面试", "sql", "牛客", "戴师兄"],
    "其他": []
}

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# ==========================================
# 日历事件数据引擎
# 存储格式：calendar_events.json
# { "2026-03-25": [{"title": "组会", "time": "14:00"}, ...], ... }
# ==========================================
CALENDAR_FILE = "calendar_events.json"
CALENDAR_SECTION_PREFIX = "## 📆 Markdown 日历视图"
CALENDAR_NOTE = "> 把当天最关键的交付或提醒写进格子里，配合下方看板即可完成“月历 + 任务”的联动。"


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

def call_claude(prompt, callback=None, root=None, work_dir=None):
    def run():
        try:
            safe_prompt = prompt.replace('"', '\\"')
            if work_dir and os.path.exists(work_dir):
                command = f'cd /d "{work_dir}" && claude "{safe_prompt}"'
            else:
                command = f'claude "{safe_prompt}"'
            result = subprocess.run(
                command, capture_output=True, text=True, encoding='utf-8',
                errors='ignore', shell=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.stdout.strip():
                output = result.stdout
            elif result.stderr.strip():
                output = f"⚠️ Claude 报错:\n{result.stderr}"
            else:
                output = "⚠️ 执行完毕，无文字返回。"
            if callback and root:
                root.after(0, lambda cb=callback, out=output: cb(out))
        except Exception as e:
            if callback and root:
                root.after(0, lambda cb=callback, err=f"❌ 调用失败: {str(e)}": cb(err))
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
        self.chat_history = []  # 和 Claude 的多轮对话上下文
        self.claude_status_var = tk.StringVar(value="🟢 Claude 空闲")
        self._claude_status_timer = None

        # 日历事件数据
        self.calendar_events = load_calendar_events()
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

        # 右上角每日双图盲盒
        self.img_frame = tk.Frame(top_bar, bg=COLORS['bg_main'])
        self.img_frame.pack(side=tk.RIGHT, padx=(0, 10))
        self.img_label_1 = tk.Label(self.img_frame, bg=COLORS['bg_main'])
        self.img_label_1.pack(side=tk.LEFT, padx=5)
        self.img_label_2 = tk.Label(self.img_frame, bg=COLORS['bg_main'])
        self.img_label_2.pack(side=tk.LEFT, padx=5)
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
        custom_frame.pack(fill=tk.X, padx=15, pady=(5, 10))

        tk.Label(
            custom_frame, text="💬 对话 & 📝 小记",
            font=('宅在家麥克筆', 10),
            bg=COLORS['bg_secondary'], fg=COLORS['text_primary']
        ).pack(anchor='w', pady=(0, 5))

        self.custom_input = tk.Entry(
            custom_frame,
            font=('Microsoft YaHei', 10),
            relief=tk.SOLID, bd=1,
            bg=COLORS['bg_main'], fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary']
        )
        self.custom_input.pack(fill=tk.X, pady=5, ipady=6)
        self.custom_input.bind('<Return>', lambda e: self.ask_custom())
        self.custom_input.bind('<Shift-Return>', lambda e: self.save_shared_review())

        btn_row = tk.Frame(custom_frame, bg=COLORS['bg_secondary'])
        btn_row.pack(fill=tk.X)
        ModernButton(btn_row, "问 Claude", self.ask_custom, bg_color=COLORS['accent'], fg_color='#FFFFFF', width=200).pack(side=tk.LEFT, padx=(0, 5))
        ModernButton(btn_row, "入复盘", self.save_shared_review, bg_color=COLORS['peach'], fg_color='#333333', width=200).pack(side=tk.RIGHT, padx=(5, 0))

        separator = tk.Frame(right_panel, bg=COLORS['border'], height=1)
        separator.pack(fill=tk.X, padx=20, pady=(5, 10))

        new_task_frame = tk.Frame(right_panel, bg=COLORS['bg_secondary'])
        new_task_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        tk.Label(
            new_task_frame, text="📌 添加新任务",
            font=('宅在家麥克筆', 10),
            bg=COLORS['bg_secondary'], fg=COLORS['text_primary']
        ).pack(anchor='w', pady=(0, 5))

        input_row = tk.Frame(new_task_frame, bg=COLORS['bg_secondary'])
        input_row.pack(fill=tk.X, pady=(0, 8))

        self.cat_combo = ttk.Combobox(
            input_row, values=list(CATEGORIES.keys()),
            state="readonly", width=12, font=('851tegakizatsu', 10)
        )
        self.cat_combo.current(3)
        self.cat_combo.pack(side=tk.LEFT, padx=(0, 10))

        self.new_task_entry = tk.Entry(
            input_row, font=('851tegakizatsu', 10),
            relief=tk.SOLID, bd=1,
            bg=COLORS['bg_main'], fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary']
        )
        self.new_task_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.new_task_entry.bind('<Return>', lambda e: self.add_new_task())

        ModernButton(
            new_task_frame, "添加到左侧看板", self.add_new_task,
            bg_color=COLORS['success'], fg_color='#333333', width=380
        ).pack()

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
        new_text = self.custom_input.get().strip()
        if not new_text:
            return
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
            self.custom_input.delete(0, tk.END)
            self.append_chat("📝 系统广播:", f"已将随笔存入今日文档：{new_text}", COLORS['peach'])

    def add_new_task(self):
        text = self.new_task_entry.get().strip()
        cat = self.cat_combo.get()
        if not text:
            return
        cat_header = f"### 📁 [{cat}]\n"
        if cat_header in self.file_lines:
            idx = self.file_lines.index(cat_header)
            self.file_lines.insert(idx + 1, f"- [ ] {text}\n")
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.writelines(self.file_lines)
            self.new_task_entry.delete(0, tk.END)
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
            prompt = "请用一句话鼓励一位正在处理经济学实证数据写论文、并备考雅思、找实习的研究生，该实习生容易焦虑，请你带一个emoji，直接输出这句话，绝对不要任何废话。"
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

    def ask_custom(self):
        txt = self.custom_input.get().strip()
        if not txt: return
        self.custom_input.delete(0, tk.END)
        self.append_chat("👤 wy:", txt, COLORS['text_secondary'])

        system_prompt = (
            "你是一个高级日程管家与反拖延助理，服务对象是经济学研究生，"
            "核心任务：雅思备考、毕业论文(DID/RDD)、小论文(证言)、实习准备。"
            "隐藏能力：若用户要改期任务，回复中包含【MOVE:关键词|YYYY-MM-DD】；"
            "若要拆解任务，包含【SPLIT:关键词|步骤1,步骤2】；"
            "若要写代码文件，先输出【CREATE_FILE:文件名】再给```代码块。"
            "语言极度简洁，带emoji，不要废话。"
        )
        self.chat_history.append({"role": "user", "content": txt})
        prompt_text = self._build_claude_prompt(system_prompt)
        self._set_claude_status("⏳ Claude 正在思考...")
        if self.root:
            if self._claude_status_timer:
                self.root.after_cancel(self._claude_status_timer)
            self._claude_status_timer = self.root.after(
                15000,
                lambda: self.claude_status_var.set("⌛ Claude 还在排队，网络可能较慢…")
            )
        call_claude(prompt_text, self.show_claude_response, self.root)

    def _build_claude_prompt(self, system_prompt):
        history_snippets = []
        for msg in self.chat_history[-6:]:  # 控制上下文长度，降低等待时间
            role = "用户" if msg["role"] == "user" else "助手"
            history_snippets.append(f"{role}: {msg['content']}")
        history_block = "\n".join(history_snippets) if history_snippets else "(暂无历史)"
        lines = [
            system_prompt.strip(),
            "",
            "--- 对话历史 ---",
            history_block,
            "",
            "助手:"
        ]
        return "\n".join(lines)


    def show_claude_response(self, response):
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

        # 把小克的回复也存入历史
        self.chat_history.append({"role": "assistant", "content": clean_response.strip()})
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
        call_claude(prompt, self.show_claude_response, self.root)

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
