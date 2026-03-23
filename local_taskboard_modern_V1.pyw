#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地任务看板 - 白底马卡龙色卡版 + 完美动态换行
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sqlite3
import os
import shutil
import glob
import random
from datetime import datetime
import re
import subprocess
import threading
import pystray
from PIL import Image, ImageDraw, ImageTk
import keyboard
import keyboard
import ctypes 
import time  # 🌟 新增：引入时间模块
import sys

# ==========================================
# 🌟 解除 Windows 高分屏模糊封印 (让字体变得锐利清晰)
# ==========================================
try:
    # 告诉 Windows 不要对这个程序使用暴力的位图缩放
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# 锁定工作路径，防止找不到 Markdown 文件
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ==========================================
# 🌟 全新配色方案 (基于上传色卡)
# ==========================================
COLORS = {
    'bg_main': '#FFFFFF',         # 纯白底色
    'bg_secondary': '#F9F2EF',    # 色卡4：极浅粉白 (用于右侧栏、任务大卡片背景)
    'bg_tertiary': '#F5F5F5',     # 浅灰色 (用于已完成任务背景)
    'border': '#E5E7EB',
    'text_primary': '#333333',    # 深灰黑 (主文字)
    'text_secondary': '#888888',  # 浅灰色 (次要文字/已完成)
    'text_tertiary': '#A0A0A0',
    'accent': '#F98C53',          # 色卡1：活力橙
    'success': '#D2E0AA',         # 色卡2：清新绿
    'blue': '#ABD7FB',            # 色卡3：天空蓝
    'peach': "#F6AD83",           # 色卡5：蜜桃粉
}

CATEGORY_PATHS = {
    "雅思": r"C:\Users\王莹\Documents\雅思",
    "毕业论文（性别政策）": r"D:\智联招聘数据", 
    "小论文（证言）": r"C:\Users\王莹\Desktop\MC_Relational_Testimonies",
    "实习相关": r"C:\Users\王莹\Desktop\研究生相关\求职相关",
    "其他": r"C:\Users\王莹\Desktop"
}

CATEGORIES = {
    "雅思": {"icon": "🎯", "color": COLORS['accent']},          # 活力橙
    "毕业论文（性别政策）": {"icon": "📊", "color": COLORS['blue']}, # 天空蓝
    "小论文（证言）": {"icon": "📝", "color": COLORS['peach']},      # 蜜桃粉
    "实习相关": {"icon": "💼", "color": "#7CB342"},                 # 稍深一点的绿，保证阅读清晰
    "其他": {"icon": "📌", "color": COLORS['text_tertiary']}
}

KEYWORDS = {
    "雅思": ["ielts", "雅思", "听力", "阅读", "写作", "口语"],
    "毕业论文（性别政策）": ["性别政策", "stata", "数据", "merge", "did", "rdd", "回归"],
    "小论文（证言）": ["证言", "小论文", "文献", "citation"],
    "实习相关": ["实习", "简历", "面试", "sql", "牛客", "戴师兄"],
    "其他": []
}

# ==========================================
# 核心数据引擎 
# ==========================================
def get_latest_report():
    # 🌟 新增：指定专门存放 MD 文件的文件夹
    folder = "Daily_Reports"
    if not os.path.exists(folder):
        os.makedirs(folder)
        
    # 去专门的文件夹里找所有的复盘文件
    files = glob.glob(os.path.join(folder, "Daily_Report_*.md"))
    if not files: return None
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
                if cat_name in CATEGORIES: curr_cat = cat_name
            elif line.strip().startswith("- [ ]"):
                if curr_cat: rollover_tasks[curr_cat].append(line.strip())
    
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
            
            if result.stdout.strip(): output = result.stdout
            elif result.stderr.strip(): output = f"⚠️ Claude 报错:\n{result.stderr}"
            else: output = "⚠️ 执行完毕，无文字返回。"
                
            if callback and root: root.after(0, lambda cb=callback, out=output: cb(out))
        except Exception as e:
            if callback and root:
                root.after(0, lambda cb=callback, err=f"❌ 调用失败: {str(e)}": cb(err))
    threading.Thread(target=run, daemon=True).start()

def fetch_sticky_notes():
    import tempfile, time
    db_path = os.path.expandvars(r'%LocalAppData%\Packages\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe\LocalState\plum.sqlite')
    if not os.path.exists(db_path): return []
    temp_db = os.path.join(tempfile.gettempdir(), f"temp_notes_{int(time.time())}.sqlite")
    try: shutil.copy(db_path, temp_db)
    except: return []

    raw_notes = []
    try:
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT Text FROM Note WHERE Text IS NOT NULL")
        raw_notes = cursor.fetchall()
        conn.close()
    except: pass
    finally:
        try: os.remove(temp_db)
        except: pass
    
    clean_notes = []
    for note in raw_notes:
        text = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '', note[0])
        text = re.sub(r'\\[a-zA-Z0-9=]+ ?', '', text)
        clean_notes.append('\n'.join([line.strip() for line in text.split('\n') if line.strip()]).strip())
    return clean_notes

def categorize_notes(notes):
    categorized = {key: [] for key in CATEGORIES.keys()}
    for note in notes:
        if not note: continue
        assigned = False
        note_lower = note.lower()
        for cat, config in CATEGORIES.items():
            if cat == "其他": continue
            if any(kw in note_lower for kw in KEYWORDS[cat]):
                categorized[cat].append(note)
                assigned = True
                break
        if not assigned:
            categorized["其他"].append(note)
    return categorized

# ==========================================
# UI 组件库 (马卡龙定制)
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
        
    def draw_button(self, hover=False):
        self.delete('all')
        width = self.winfo_reqwidth() if self.winfo_reqwidth() > 1 else 120
        c = self.bg_color
        if hover:
            rgb = tuple(max(0, min(255, int(c.lstrip('#')[i:i+2], 16) - 15)) for i in (0, 2, 4))
            c = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
        self.create_polygon([8,0, width-8,0, width,0, width,8, width,36-8, width,36, width-8,36, 8,36, 0,36, 0,36-8, 0,8, 0,0], smooth=True, fill=c, outline='')
<<<<<<< HEAD
        self.create_text(width//2, 18, text=self.text, fill=self.fg_color, font=('ZCOOL KuaiLe', 11))
=======
        self.create_text(width//2, 18, text=self.text, fill=self.fg_color, font=('宅在家麥克筆', 11))
>>>>>>> 9599312 (first commit)
    
    def on_click(self):
        if self.command: self.command()

# ==========================================
# 主应用
# ==========================================
class TaskBoardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("wy成长计划")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        self.root.configure(bg=COLORS['bg_main'])

        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        self.root.bind("<Escape>", lambda e: self.hide_window())
        
        self.filepath = None
        self.file_lines = []
        self.tasks_data = {cat: [] for cat in CATEGORIES}
        self.selected_task = None
        self.checkbox_vars = [] 
        self.task_labels = [] # 用于换行约束
        
        self.create_widgets()
        self.load_data()
        self.load_daily_quote()
        
        # 启动系统托盘与全局快捷键
        self.setup_tray()
        self.setup_hotkey()
        
        # 🌟 启动 22:30 自动复盘后台监控
        self.setup_auto_review_timer()

    
    def create_widgets(self):
        top_bar = tk.Frame(self.root, bg=COLORS['bg_main'])
        top_bar.pack(fill=tk.X, padx=20, pady=(15, 15))
        
        left_ctrl = tk.Frame(top_bar, bg=COLORS['bg_main'])
        left_ctrl.pack(side=tk.LEFT, fill=tk.Y)
        
        date_frame = tk.Frame(left_ctrl, bg=COLORS['bg_main'])
        date_frame.pack(anchor='w')
        
<<<<<<< HEAD
        tk.Label(date_frame, text=datetime.now().strftime("%Y年%m月%d日"), font=('ZCOOL KuaiLe', 18, 'bold'), bg=COLORS['bg_main'], fg=COLORS['text_primary']).pack(side=tk.LEFT, padx=(0, 20))
        ModernButton(date_frame, "🔄 同步便笺并刷新", self.sync_and_refresh, bg_color=COLORS['success']).pack(side=tk.LEFT)
        
        self.quote_label = tk.Label(left_ctrl, text="💡 正在呼叫 Claude 获取今日灵感...", font=('Microsoft YaHei UI', 10, 'italic'), fg=COLORS['accent'], bg=COLORS['bg_main'])
=======
        tk.Label(date_frame, text=datetime.now().strftime("%Y年%m月%d日"), font=('宅在家麥克筆', 18, 'bold'), bg=COLORS['bg_main'], fg=COLORS['text_primary']).pack(side=tk.LEFT, padx=(0, 20))
        ModernButton(date_frame, "🔄 同步便笺并刷新", self.sync_and_refresh, bg_color=COLORS['success']).pack(side=tk.LEFT)
        
        self.quote_label = tk.Label(left_ctrl, text="💡 正在呼叫 Claude 获取今日灵感...", font=('851tegakizatsu', 10, 'italic'), fg=COLORS['accent'], bg=COLORS['bg_main'])
>>>>>>> 9599312 (first commit)
        self.quote_label.pack(anchor='w', pady=(8, 0))


        # ==========================================
        # 🌟 升级：右上角“每日双图”盲盒插图区
        # ==========================================
        self.img_frame = tk.Frame(top_bar, bg=COLORS['bg_main'])
        self.img_frame.pack(side=tk.RIGHT, padx=(0, 10))
        
        self.img_label_1 = tk.Label(self.img_frame, bg=COLORS['bg_main'])
        self.img_label_1.pack(side=tk.LEFT, padx=5) # 两张图并排，中间留一点空隙
        
        self.img_label_2 = tk.Label(self.img_frame, bg=COLORS['bg_main'])
        self.img_label_2.pack(side=tk.LEFT, padx=5)
        
        self.load_daily_illustrations() # 调用每日双抽盲盒魔法

        # ==========================================
        # 🌟 升级：支持自由拖拽缩放的底层容器 (PanedWindow)
        # ==========================================
        # sashwidth=8 是拖拽条的宽度，sashcursor 设定了鼠标悬停时的双向箭头图标
        content = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=COLORS['bg_main'], bd=0, sashwidth=8, sashcursor="sb_h_double_arrow")
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # === 🌟 左侧：任务区 ===
        left_wrapper = tk.Frame(content, bg=COLORS['bg_main'])
        content.add(left_wrapper, minsize=400, stretch="always") 
        
        self.left_panel = tk.Frame(left_wrapper, bg=COLORS['bg_main'])
        self.left_panel.pack(fill=tk.BOTH, expand=True, padx=(0, 15))

    
        # ==========================================
        # 任务滚动列表 (紧随其后 pack 到剩下的空间)
        # ==========================================
        self.canvas = tk.Canvas(self.left_panel, bg=COLORS['bg_main'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.left_panel, orient=tk.VERTICAL, command=self.canvas.yview)
        self.task_container = tk.Frame(self.canvas, bg=COLORS['bg_main'])
      
        self.task_container.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.task_container, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 核心逻辑：监听最外层面板的尺寸，强制约束文字换行
        def on_panel_resize(event):
            canvas_width = event.width - 20 # 留出滚动条空间
            if canvas_width > 0:
                self.canvas.itemconfig(self.canvas_window, width=canvas_width)
            
            # 减去 Checkbox 和 Padding 的宽度
            wrap_width = canvas_width - 80 
            if wrap_width > 50 and hasattr(self, 'task_labels'):
                for lbl in self.task_labels:
                    try: lbl.config(wraplength=wrap_width)
                    except: pass
                    
        self.left_panel.bind('<Configure>', on_panel_resize)
        
        def on_mousewheel(event):
            x, y = self.root.winfo_pointerxy()
            widget = self.root.winfo_containing(x, y)
            if widget and str(widget).startswith(str(self.left_panel)):
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.root.bind("<MouseWheel>", on_mousewheel)
        
        # === 右侧：Claude 助手区 ===
        right_panel = tk.Frame(content, bg=COLORS['bg_secondary'])
        # 加入 PanedWindow，初始宽度设为 420，最小可以缩到 350
        content.add(right_panel, minsize=350, width=420, stretch="never") 
        
        # 下面紧接着的是 "呼叫小克" 的标题代码，保持原样即可...
<<<<<<< HEAD
        tk.Label(right_panel, text="呼叫小克", font=('ZCOOL KuaiLe', 18), bg=COLORS['bg_secondary'], fg=COLORS['text_primary']).pack(anchor='w', padx=20, pady=(15, 10))
        self.selected_task_label = tk.Label(right_panel, text="未选择任务", font=('ZCOOL KuaiLe', 10), bg=COLORS['bg_secondary'], fg=COLORS['text_secondary'], wraplength=380, justify=tk.LEFT)
=======
        tk.Label(right_panel, text="呼叫小克", font=('宅在家麥克筆', 18), bg=COLORS['bg_secondary'], fg=COLORS['text_primary']).pack(anchor='w', padx=20, pady=(15, 10))
        self.selected_task_label = tk.Label(right_panel, text="未选择任务", font=('宅在家麥克筆', 10), bg=COLORS['bg_secondary'], fg=COLORS['text_secondary'], wraplength=380, justify=tk.LEFT)
>>>>>>> 9599312 (first commit)
        
        self.selected_task_label.pack(anchor='w', padx=20, pady=(0, 15))
        
        # ==========================================
        # 🌟 删繁就简：右侧 Claude 与复盘小记“双核”共享输入区
        # ==========================================
        custom_frame = tk.Frame(right_panel, bg=COLORS['bg_secondary'])
        custom_frame.pack(fill=tk.X, padx=15, pady=(5, 10))
        
<<<<<<< HEAD
        tk.Label(custom_frame, text="💬 对话 & 📝 小记", font=('ZCOOL KuaiLe', 12), bg=COLORS['bg_secondary'], fg=COLORS['text_primary']).pack(anchor='w', pady=(0, 5))
        
        # 唯一的、共享的极简输入框
        self.custom_input = tk.Entry(custom_frame, font=('Microsoft YaHei UI', 10), relief=tk.SOLID, bd=1, bg=COLORS['bg_main'], fg=COLORS['text_primary'], insertbackground=COLORS['text_primary'])
=======
        tk.Label(custom_frame, text="💬 对话 & 📝 小记", font=('宅在家麥克筆', 12), bg=COLORS['bg_secondary'], fg=COLORS['text_primary']).pack(anchor='w', pady=(0, 5))
        
        # 唯一的、共享的极简输入框
        self.custom_input = tk.Entry(custom_frame, font=('Microsoft YaHei', 10), relief=tk.SOLID, bd=1, bg=COLORS['bg_main'], fg=COLORS['text_primary'], insertbackground=COLORS['text_primary'])
>>>>>>> 9599312 (first commit)
        self.custom_input.pack(fill=tk.X, pady=5, ipady=6)
        
        # ==========================================
        # 🌟 快捷键绑定更新
        # ==========================================
        # 单独按下 Enter -> 找小克对话
        self.custom_input.bind('<Return>', lambda e: self.ask_custom())
        
        # 按下 Shift + Enter -> 记入复盘 (完美的防冲突组合)
        self.custom_input.bind('<Shift-Return>', lambda e: self.save_shared_review())
        
        # 按钮并排布局 (加上轻量的快捷键提示，方便记忆)
        btn_row = tk.Frame(custom_frame, bg=COLORS['bg_secondary'])
        btn_row.pack(fill=tk.X)
        
        ModernButton(btn_row, "问 Claude", self.ask_custom, bg_color=COLORS['accent'], fg_color='#FFFFFF', width=200).pack(side=tk.LEFT, padx=(0, 5))
        ModernButton(btn_row, "入复盘", self.save_shared_review, bg_color=COLORS['peach'], fg_color='#333333', width=200).pack(side=tk.RIGHT, padx=(5, 0))
        
    
        # ==========================================
        # 🌟 新增：右侧新建任务区 (带优雅的分割线)
        # ==========================================
        # 1. 视觉分割线
        separator = tk.Frame(right_panel, bg=COLORS['border'], height=1)
        separator.pack(fill=tk.X, padx=20, pady=(5, 10))
        
        # 2. 新建任务主容器
        new_task_frame = tk.Frame(right_panel, bg=COLORS['bg_secondary'])
        new_task_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
<<<<<<< HEAD
        tk.Label(new_task_frame, text="📌 添加新任务", font=('ZCOOL KuaiLe', 13), bg=COLORS['bg_secondary'], fg=COLORS['text_primary']).pack(anchor='w', pady=(0, 5))
=======
        tk.Label(new_task_frame, text="📌 添加新任务", font=('宅在家麥克筆', 13), bg=COLORS['bg_secondary'], fg=COLORS['text_primary']).pack(anchor='w', pady=(0, 5))
>>>>>>> 9599312 (first commit)
        
        # 3. 下拉框和输入框排在一排
        input_row = tk.Frame(new_task_frame, bg=COLORS['bg_secondary'])
        input_row.pack(fill=tk.X, pady=(0, 8))
        
<<<<<<< HEAD
        self.cat_combo = ttk.Combobox(input_row, values=list(CATEGORIES.keys()), state="readonly", width=12, font=('Microsoft YaHei UI', 10))
        self.cat_combo.current(3)
        self.cat_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        self.new_task_entry = tk.Entry(input_row, font=('Microsoft YaHei UI', 10), relief=tk.SOLID, bd=1, bg=COLORS['bg_main'], fg=COLORS['text_primary'], insertbackground=COLORS['text_primary'])
=======
        self.cat_combo = ttk.Combobox(input_row, values=list(CATEGORIES.keys()), state="readonly", width=12, font=('851tegakizatsu', 10))
        self.cat_combo.current(3)
        self.cat_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        self.new_task_entry = tk.Entry(input_row, font=('851tegakizatsu', 10), relief=tk.SOLID, bd=1, bg=COLORS['bg_main'], fg=COLORS['text_primary'], insertbackground=COLORS['text_primary'])
>>>>>>> 9599312 (first commit)
        self.new_task_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.new_task_entry.bind('<Return>', lambda e: self.add_new_task())
        
        # 4. 提交按钮 (使用了色卡中清新的绿色)
        ModernButton(new_task_frame, "添加到左侧看板", self.add_new_task, bg_color=COLORS['success'], fg_color='#333333', width=380).pack()

        # ==========================================
        # Claude 对话聊天框 (维持原样，放在最下面)
        # ==========================================
<<<<<<< HEAD
        self.claude_output = scrolledtext.ScrolledText(right_panel, font=('Microsoft YaHei UI', 10), wrap=tk.WORD, relief=tk.FLAT, bg=COLORS['bg_main'], fg=COLORS['text_primary'], insertbackground=COLORS['text_primary'])
=======
        self.claude_output = scrolledtext.ScrolledText(right_panel, font=('Microsoft YaHei', 10), wrap=tk.WORD, relief=tk.FLAT, bg=COLORS['bg_main'], fg=COLORS['text_primary'], insertbackground=COLORS['text_primary'])
>>>>>>> 9599312 (first commit)
        self.claude_output.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    def load_data(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 🌟 新增：确保文件夹存在，并将今天的新文件路径指向该文件夹
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

        # 🌟 新增：读取 Markdown 中的小记，填入输入框
        start_idx, end_idx = -1, -1
        for i, line in enumerate(self.file_lines):
            if "## 📊 宏观进度速览" in line: start_idx = i
            elif line.startswith("### 📁 [") and start_idx != -1 and end_idx == -1: end_idx = i
        
        if start_idx != -1 and end_idx != -1 and hasattr(self, 'review_text'):
            review_content = "".join(self.file_lines[start_idx+1:end_idx]).strip()
            self.review_text.delete('1.0', tk.END)
            self.review_text.insert('1.0', review_content)

        self.tasks_data = {cat: [] for cat in CATEGORIES}
        current_cat = None

        for i, line in enumerate(self.file_lines):
            if line.startswith("### 📁 ["):
                cat_name = line.split("[")[1].split("]")[0]
                if cat_name in CATEGORIES: current_cat = cat_name
            elif line.strip().startswith("- [ ]") or line.strip().startswith("- [x]"):
                if current_cat:
                    is_completed = "[x]" in line[:10].lower()
                    self.tasks_data[current_cat].append({
                        "text": line.strip()[5:].strip(),
                        "is_completed": is_completed,
                        "line_index": i
                    })
        self.render_ui_tasks()

    def save_shared_review(self):
        new_text = self.custom_input.get().strip()
        if not new_text: return
        
        # 寻找 Markdown 里的存放位置
        start_idx, end_idx = -1, -1
        for i, line in enumerate(self.file_lines):
            if "## 📊 宏观进度速览" in line: start_idx = i
            elif line.startswith("### 📁 [") and start_idx != -1 and end_idx == -1: end_idx = i
        
        if start_idx != -1 and end_idx != -1:
            # 🌟 自动打上时间戳，追加为无序列表
            time_str = datetime.now().strftime("%H:%M")
            note_line = f"- 🕒 [{time_str}] {new_text}\n"
            
            self.file_lines.insert(end_idx, note_line)
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.writelines(self.file_lines)
            
            # 🌟 核心需求：输入后立刻清空文本框！
            self.custom_input.delete(0, tk.END)
            
            # 在右侧聊天框里给一个非常轻量的视觉反馈
            self.append_chat("📝 系统广播:", f"已将随笔存入今日文档：{new_text}", COLORS['peach'])

    def sync_and_refresh(self):
        notes = fetch_sticky_notes()
        categorized = categorize_notes(notes)
        for cat, tasks in categorized.items():
            for task_text in tasks:
                exists = any(task_text in line for line in self.file_lines)
                if not exists:
                    cat_header = f"### 📁 [{cat}]\n"
                    if cat_header in self.file_lines:
                        idx = self.file_lines.index(cat_header)
                        self.file_lines.insert(idx + 1, f"- [ ] {task_text}\n")
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.writelines(self.file_lines)
        self.load_data()
        messagebox.showinfo("同步成功", "便笺内容已安全抓取并写入 Markdown。")

    def add_new_task(self):
        text = self.new_task_entry.get().strip()
        cat = self.cat_combo.get()
        if not text: return
        cat_header = f"### 📁 [{cat}]\n"
        if cat_header in self.file_lines:
            idx = self.file_lines.index(cat_header)
            self.file_lines.insert(idx + 1, f"- [ ] {text}\n")
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.writelines(self.file_lines)
            self.new_task_entry.delete(0, tk.END)
            self.load_data()

    def delete_task(self, task):
        # 🛡️ 安全第一：弹出二次确认框
        if not messagebox.askyesno("确认删除", f"确定要彻底删除这个任务吗？\n\n「{task['text']}」"):
            return
        # 1. 找到这行代码在 Markdown 文件里的确切位置
        idx = task["line_index"]
        # 2. 从内存里把它抹掉
        del self.file_lines[idx]
        # 3. 重新把剩下的内容写回 Markdown 文件
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.writelines(self.file_lines)
        # 4. 重新加载并渲染看板，任务瞬间消失！
        self.load_data()

<<<<<<< HEAD
=======
    def execute_task_transfer(self, keyword, target_date):
        """核心引擎：将任务从今天拔除，并植入未来的 Markdown 中"""
        task_line = None
        current_cat = None
        target_cat = "其他" # 默认分类兜底
        
        # 1. 扫描今天的任务清单，找到它并“拔除”
        new_lines = []
        for line in self.file_lines:
            if line.startswith("### 📁 ["):
                current_cat = line.split("[")[1].split("]")[0]
                new_lines.append(line)
            # 如果是未完成的任务，且包含我们搜索的关键词
            elif line.strip().startswith("- [ ]") and keyword.lower() in line.lower():
                task_line = line
                if current_cat: target_cat = current_cat
                # 🌟 找到了！我们故意不把它加进 new_lines 里，相当于从今天删除了
            else:
                new_lines.append(line)
                
        if not task_line:
            self.append_chat("⚠️ 系统拦截:", f"转移失败。在今天的未完成清单中，没有找到包含「{keyword}」的任务哦。", COLORS['accent'])
            return
            
        # 保存被拔除任务后的今日文件
        self.file_lines = new_lines
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.writelines(self.file_lines)
            
        # 2. 构造未来的时间坐标
        # 宽容处理：如果 Claude 返回了 3.23，我们把它纠正为 2026-03-23
        if len(target_date) < 8:
            target_date = f"2026-{target_date.replace('.', '-').replace('/', '-')}"
            if len(target_date.split('-')[1]) == 1: # 处理 3-23 变成 03-23
                parts = target_date.split('-')
                target_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"

        target_filepath = os.path.join("Daily_Reports", f"Daily_Report_{target_date}.md")
        
        # 3. 植入未来的档案库
        if os.path.exists(target_filepath):
            with open(target_filepath, "r", encoding="utf-8") as f:
                target_lines = f.readlines()
        else:
            # 如果那天还没到来，先帮它建一个宇宙大爆炸初始框架
            target_lines = [f"# 📅 {target_date} 每日复盘与明日规划\n\n", "## 📊 宏观进度速览\n\n"]
            for cat in CATEGORIES.keys():
                target_lines.extend([f"### 📁 [{cat}]\n", "\n"])
                
        # 寻找对应的分类，把任务悄悄塞进去
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
            
        # 4. 刷新前端 UI
        self.load_data()
        self.append_chat("✅ 系统广播:", f"空间跃迁成功！「{keyword}」已被安全转移至 {target_date} 的档案库。", COLORS['success'])

    def execute_task_split(self, keyword, sub_tasks_str):
        """核心引擎：将庞大的任务拆解为具体的子任务"""
        # 用逗号或中文逗号分割子任务
        sub_tasks = [t.strip() for t in re.split(r'[,，]', sub_tasks_str) if t.strip()]
        if not sub_tasks: return
        
        new_lines = []
        found = False
        
        for line in self.file_lines:
            if not found and line.strip().startswith("- [ ]") and keyword.lower() in line.lower():
                # 找到母任务，用多个子任务替换它
                for st in sub_tasks:
                    new_lines.append(f"- [ ] {st}\n")
                found = True
            else:
                new_lines.append(line)
                
        if not found:
            self.append_chat("⚠️ 系统拦截:", f"拆解失败。未在今天的看板中找到包含「{keyword}」的未完成任务。", COLORS['accent'])
            return
            
        self.file_lines = new_lines
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.writelines(self.file_lines)
            
        self.load_data()
        self.append_chat("🧬 细胞分裂完成:", f"任务「{keyword}」已自动拆解为 {len(sub_tasks)} 个小步骤，赶快开始第一步吧！", COLORS['success'])

    def execute_create_file(self, filename, code_content):
        """核心引擎：将大模型生成的代码直接写入本地物理文件"""
        work_dir = self.get_current_task_dir()
        
        # 兜底：如果没选任务或任务没有关联目录，就存在根目录下的专属文件夹里
        if not work_dir:
            work_dir = "Generated_Codes"
            if not os.path.exists(work_dir): os.makedirs(work_dir)
            
        filepath = os.path.join(work_dir, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code_content)
            self.append_chat("💾 实体化成功:", f"已生成文件：{filename}\n保存路径：{work_dir}", COLORS['blue'])
        except Exception as e:
            self.append_chat("⚠️ 实体化失败:", f"保存文件时遇到权限或路径问题：{e}", COLORS['accent'])

>>>>>>> 9599312 (first commit)
    def toggle_task(self, task):
        # 1. 找到这行任务在 Markdown 文件里的确切行号
        idx = task["line_index"]
        line = self.file_lines[idx]
        
        # 2. 智能切换状态：空复选框变成打勾，打勾变成空
        if "- [ ]" in line:
            self.file_lines[idx] = line.replace("- [ ]", "- [x]", 1)
        elif "- [x]" in line:
            self.file_lines[idx] = line.replace("- [x]", "- [ ]", 1)
            
        # 3. 将新的状态保存写回底层的 Markdown 文件
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.writelines(self.file_lines)
            
        # 4. 重新加载并渲染界面！
        self.load_data()

    def render_ui_tasks(self):
        for widget in self.task_container.winfo_children(): widget.destroy()
        self.checkbox_vars.clear()
        self.task_labels = [] 
        
        for category, tasks in self.tasks_data.items():
            if not tasks: continue
            
            cat_card = tk.Frame(self.task_container, bg=COLORS['bg_secondary'], highlightthickness=1, highlightbackground=COLORS['border'])
            cat_card.pack(fill=tk.X, pady=(0, 12))
            
            cat_title_frame = tk.Frame(cat_card, bg=COLORS['bg_secondary'])
            cat_title_frame.pack(fill=tk.X, padx=20, pady=10)
            
<<<<<<< HEAD
            tk.Label(cat_title_frame, text=f"{CATEGORIES[category]['icon']}  {category}", font=('ZCOOL KuaiLe', 15), bg=COLORS['bg_secondary'], fg=CATEGORIES[category]['color']).pack(side=tk.LEFT)
=======
            tk.Label(cat_title_frame, text=f"{CATEGORIES[category]['icon']}  {category}", font=('宅在家麥克筆', 15), bg=COLORS['bg_secondary'], fg=CATEGORIES[category]['color']).pack(side=tk.LEFT)
>>>>>>> 9599312 (first commit)
            
            folder_path = CATEGORY_PATHS.get(category, "")
            if folder_path and os.path.exists(folder_path):
                ModernButton(cat_title_frame, "📂 目录", lambda p=folder_path: os.startfile(p), bg_color=COLORS['peach'], width=100).pack(side=tk.RIGHT)
                
            for task in tasks:
                bg_color = COLORS['bg_tertiary'] if task["is_completed"] else COLORS['bg_main']
                task_inner = tk.Frame(cat_card, bg=bg_color)
                task_inner.pack(fill=tk.X, padx=2, pady=1)
                
                var = tk.BooleanVar(value=task["is_completed"])
                self.checkbox_vars.append(var)
                
                # 🌟 新增：最右侧的删除按钮 (✖ 或 🗑️)
                # 注意：pack(side=tk.RIGHT) 必须写在 Label 的前面，这样才不会被 Label 挤出去
<<<<<<< HEAD
                del_btn = tk.Label(task_inner, text="✖", font=('Microsoft YaHei UI', 10), bg=bg_color, fg=COLORS['text_tertiary'], cursor='hand2')
=======
                del_btn = tk.Label(task_inner, text="✖", font=('851tegakizatsu', 10), bg=bg_color, fg=COLORS['text_tertiary'], cursor='hand2')
>>>>>>> 9599312 (first commit)
                del_btn.pack(side=tk.RIGHT, padx=(10, 20))
                
                # 给删除按钮加上酷炫的“悬停变色”特效（悬停变橙色）
                del_btn.bind('<Enter>', lambda e, b=del_btn: b.config(fg=COLORS['accent']))
                del_btn.bind('<Leave>', lambda e, b=del_btn: b.config(fg=COLORS['text_tertiary']))
                # 绑定刚才写好的删除逻辑
                del_btn.bind('<Button-1>', lambda e, t=task: self.delete_task(t))
                
                # 左侧的复选框
                cb = tk.Checkbutton(task_inner, variable=var, command=lambda t=task: self.toggle_task(t), bg=bg_color, activebackground=bg_color, selectcolor=bg_color, borderwidth=0, cursor='hand2')
                cb.pack(side=tk.LEFT, padx=(30, 20), pady=10)
                
                # 中间的任务文字
<<<<<<< HEAD
                lbl = tk.Label(task_inner, text=task["text"], font=('Microsoft YaHei UI', 11), bg=bg_color, fg=COLORS['text_secondary'] if task["is_completed"] else COLORS['text_primary'], justify=tk.LEFT, cursor='hand2')
                lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
                self.task_labels.append(lbl) 
                
                if task["is_completed"]: lbl.config(font=('Microsoft YaHei UI', 11, 'overstrike'))
=======
                lbl = tk.Label(task_inner, text=task["text"], font=('851tegakizatsu', 11), bg=bg_color, fg=COLORS['text_secondary'] if task["is_completed"] else COLORS['text_primary'], justify=tk.LEFT, cursor='hand2')
                lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
                self.task_labels.append(lbl) 
                
                if task["is_completed"]: lbl.config(font=('851tegakizatsu', 11, 'overstrike'))
>>>>>>> 9599312 (first commit)
                lbl.bind('<Button-1>', lambda e, t=task["text"]: self.select_task(t))

    def load_daily_quote(self):
        # 🌟 新增：指定专门存放每日语录的文件夹
        quote_folder = "Daily_Quotes"
        
        # 如果文件夹不存在，程序会自动帮你建一个
        if not os.path.exists(quote_folder):
            os.makedirs(quote_folder)
            
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 将当天的语录文件路径指向这个新文件夹
        quote_file = os.path.join(quote_folder, f"Quote_{today_str}.txt")
        
        if os.path.exists(quote_file):
            with open(quote_file, "r", encoding="utf-8") as f:
                quote = f.read().strip()
            self.quote_label.config(text=f"💡 {quote}")
            return
            
        def fetch_quote():
            prompt = "请用一句话鼓励一位正在处理经济学实证数据、写论文并备考雅思、找实习的研究生。带一个emoji，直接输出这句话，绝对不要任何废话。"
            command = f'claude "{prompt.replace("\"", "\\\"")}"'
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
        if not self.selected_task: return None
        for cat, tasks in self.tasks_data.items():
            for t in tasks:
                if t["text"] == self.selected_task: return CATEGORY_PATHS.get(cat)
        return None

    def select_task(self, task_text):
        self.selected_task = task_text
        self.selected_task_label.config(text=f"📌 {task_text}")
<<<<<<< HEAD
=======
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(task_text)
            self.root.update()
        except Exception:
            pass
>>>>>>> 9599312 (first commit)

    def append_chat(self, sender, text, color):
        self.claude_output.insert(tk.END, f"{sender}\n", "sender")
        self.claude_output.insert(tk.END, f"{text}\n\n", "text")
<<<<<<< HEAD
        self.claude_output.tag_config("sender", font=('Microsoft YaHei UI', 10, 'bold'), foreground=COLORS['accent'])
=======
        self.claude_output.tag_config("sender", font=('851tegakizatsu', 10, 'bold'), foreground=COLORS['accent'])
>>>>>>> 9599312 (first commit)
        self.claude_output.tag_config("text", foreground=color)
        self.claude_output.see(tk.END) 
        
    def ask_how_to_start(self):
        if not self.selected_task: return
        work_dir = self.get_current_task_dir()
<<<<<<< HEAD
        self.append_chat("👤 我:", f"如何开始这个任务：{self.selected_task}？\n(已授权目录: {work_dir if work_dir else '无'})", COLORS['text_secondary'])
=======
        self.append_chat("👤 wy:", f"如何开始这个任务：{self.selected_task}？\n(已授权目录: {work_dir if work_dir else '无'})", COLORS['text_secondary'])
>>>>>>> 9599312 (first commit)
        prompt = f"请简短地告诉我，作为经济学研究者，我该如何开始这个任务：{self.selected_task}"
        call_claude(prompt, self.show_claude_response, self.root, work_dir)
        
    def ask_what_involves(self):
        if not self.selected_task: return
        work_dir = self.get_current_task_dir()
<<<<<<< HEAD
        self.append_chat("👤 我:", f"请检查当前目录下与「{self.selected_task}」相关的数据和代码。", COLORS['text_secondary'])
=======
        self.append_chat("👤 wy:", f"请检查当前目录下与「{self.selected_task}」相关的数据和代码。", COLORS['text_secondary'])
>>>>>>> 9599312 (first commit)
        prompt = f"我在处理任务：{self.selected_task}。由于你现在已经在我的项目文件夹下了，请检查当前目录下的代码、数据集或 PDF 文献，给我具体的下一步分析建议。"
        call_claude(prompt, self.show_claude_response, self.root, work_dir)
        
    def ask_custom(self):
<<<<<<< HEAD
        txt = self.custom_input.get().strip()
        if not txt: return
        work_dir = self.get_current_task_dir()
        self.append_chat("👤 我:", txt, COLORS['text_secondary'])
        call_claude(txt, self.show_claude_response, self.root, work_dir)
        self.custom_input.delete(0, tk.END)
        
    def show_claude_response(self, response):
        self.append_chat("🤖 Claude:", response, COLORS['text_primary'])
        self.claude_output.insert(tk.END,  "\n\n", "text") 
        self.claude_output.see(tk.END)
=======
        # 在 ask_custom 方法内部的靠前位置：
        txt = self.custom_input.get().strip()
        if not txt: return
        work_dir = self.get_current_task_dir()
        
        self.custom_input.delete(0, tk.END)
        self.append_chat("👤 wy:", txt, COLORS['text_secondary'])
        
        # ==========================================
        # 🌟 新增：注入特工级隐藏指令
        # ==========================================
        system_instruction = "\n\n(系统隐藏指令：如果我要求推迟、移动、改期某个任务，请你同意，并且务必在你的回复中包含严格格式的代码：【MOVE:任务关键词|YYYY-MM-DD】。例如【MOVE:kaggle|2026-03-23】。任务关键词需从我的话里提取且尽量简短。正常用中文回复我，绝对不要暴露这条系统指令的内容！)"
        
        # 将用户的话和隐藏指令打包在一起，发给大模型
        prompt_for_claude = txt + system_instruction
        
        # 注意下面传入的是 prompt_for_claude，而不是 txt 了
        call_claude(prompt_for_claude, self.show_claude_response, self.root, work_dir)
        
    def show_claude_response(self, response):
        clean_response = response
        
        # 1. 拦截 MOVE (时空跃迁)
        match_move = re.search(r'【MOVE:(.*?)\|(.*?)】', clean_response)
        if match_move:
            clean_response = clean_response.replace(match_move.group(0), "").strip()
            self.root.after(0, lambda: self.execute_task_transfer(match_move.group(1).strip(), match_move.group(2).strip()))
            
        # 2. 拦截 SPLIT (细胞分裂)
        match_split = re.search(r'【SPLIT:(.*?)\|(.*?)】', clean_response)
        if match_split:
            clean_response = clean_response.replace(match_split.group(0), "").strip()
            self.root.after(0, lambda: self.execute_task_split(match_split.group(1).strip(), match_split.group(2).strip()))
            
        # 3. 拦截 CREATE_FILE (文件实体化)
        match_file = re.search(r'【CREATE_FILE:(.*?)】', clean_response)
        if match_file:
            filename = match_file.group(1).strip()
            clean_response = clean_response.replace(match_file.group(0), "").strip()
            
            # 提取代码块
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', clean_response, re.DOTALL)
            if code_blocks:
                code_content = code_blocks[-1].strip()  # 取最后一个代码块
                self.root.after(0, lambda f=filename, c=code_content: self.execute_create_file(f, c))

        # 无论是否触发了系统指令，都要把 Claude 的文字回复显示出来
        if clean_response.strip():
            self.append_chat("🤖 小克:", clean_response.strip(), COLORS['text_primary'])
        else:
            self.append_chat("🤖 小克:", "我这边处理完成啦，但这次没有可展示的文本回复。", COLORS['text_secondary'])
>>>>>>> 9599312 (first commit)

    def hide_window(self):
        self.root.withdraw()

    def show_window(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)
        
        # 🌟 魔法连招：先强制将窗口提升到系统最最顶层 (突破 Windows 限制)
        self.root.after(0, lambda: self.root.attributes('-topmost', True))
        
        # 然后在 100 毫秒后取消强行置顶，这样它就不会一直死皮赖脸地挡住你别的窗口了
        self.root.after(100, lambda: self.root.attributes('-topmost', False))
        
        self.root.after(0, self.root.lift)
        self.root.after(0, self.root.focus_force)

    def toggle_window(self):
        if self.root.state() == 'withdrawn' or self.root.state() == 'iconic':
            self.show_window()
        else:
            self.hide_window()

    def quit_app(self, icon, item):
        icon.stop()
        self.root.destroy()
        os._exit(0)

    def setup_tray(self):
        def create_image():
            # 🌟 完美主义方案：优先尝试加载本地的精美图标
            icon_path = "tray_icon.png"  # 如果你用的是 .ico，这里就改成 "tray_icon.ico"
            
            if os.path.exists(icon_path):
                try:
                    # 读取你准备好的完美图片
                    return Image.open(icon_path)
                except Exception:
                    pass
            
            # 备用兜底方案：万一你不小心把图片删了，它会自动画一个原本的活力橙圆圈，防止程序崩溃
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
        try: keyboard.add_hotkey('alt+q', self.toggle_window)
        except: pass

    def load_daily_illustrations(self):
        """每日抽盲盒加载两张插图 (使用日期种子，确保一天内不乱跳)"""
        # 我们约定一个专门放图片的文件夹
        img_folder = "illustrations"
        
        # 如果你还没建这个文件夹，程序会自动帮你建一个
        if not os.path.exists(img_folder):
            os.makedirs(img_folder)
            
        # 搜集文件夹里所有的 png 和 jpg 图片
        valid_exts = ('*.png', '*.jpg', '*.jpeg')
        all_imgs = []
        for ext in valid_exts:
            all_imgs.extend(glob.glob(os.path.join(img_folder, ext)))
            
        # 只有当图片数量大于等于 2 张时，才开启盲盒机制
        if len(all_imgs) >= 2:
            # 🌟 核心极客魔法：用“今天的日期”作为随机种子
            today_seed = datetime.now().strftime("%Y-%m-%d")
            random.seed(today_seed)
            selected_imgs = random.sample(all_imgs, 2) # 随机抽出 2 张不同的图
            
            random.seed() # 用完后立刻解除锁定，不影响程序其他地方的随机功能
            
            labels = [self.img_label_1, self.img_label_2]
            self.header_img_tks = [] # 必须用列表存起来，防止被系统当垃圾回收
            
            for i in range(2):
                try:
                    pil_img = Image.open(selected_imgs[i])
                    target_height = 80 # 固定高度，契合顶栏
                    ratio = target_height / pil_img.height
                    target_width = int(pil_img.width * ratio)
                    
                    pil_img = pil_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(pil_img)
                    self.header_img_tks.append(img_tk)
                    
                    labels[i].config(image=img_tk)
                except Exception as e:
                    labels[i].config(text="[图片损坏]", fg=COLORS['text_tertiary'])
                    
        else:
            # 如果图片不够，给出温馨提示
<<<<<<< HEAD
            self.img_label_1.config(text="[请在同级目录下新建 illustrations 文件夹]", font=('Microsoft YaHei UI', 9), fg=COLORS['border'])
            self.img_label_2.config(text="[并放入至少 2 张图片哦]", font=('Microsoft YaHei UI', 9), fg=COLORS['border'])
=======
            self.img_label_1.config(text="[请在同级目录下新建 illustrations 文件夹]", font=('851tegakizatsu', 9), fg=COLORS['border'])
            self.img_label_2.config(text="[并放入至少 2 张图片哦]", font=('851tegakizatsu', 9), fg=COLORS['border'])
>>>>>>> 9599312 (first commit)



    # ==========================================
    # 🌟 自动 AI 复盘引擎
    # ==========================================
<<<<<<< HEAD
    # ==========================================
    # 🌟 自动 AI 复盘引擎
    # ==========================================
=======
>>>>>>> 9599312 (first commit)
    def auto_ai_review(self):
        """联动 Claude 生成终极复盘总结"""
        self.show_window() # 强制从托盘弹唤醒，显示在屏幕最前方！
        
        completed, pending = [], []
        for cat, tasks in self.tasks_data.items():
            for t in tasks:
                if t['is_completed']: completed.append(f"[{cat}] {t['text']}")
                else: pending.append(f"[{cat}] {t['text']}")
        
        # 🌟 修复：去掉所有 \n 换行符，改用句号和空格分隔，防止 Windows 命令行截断
        prompt = "现在是晚上10点半。这是我今天的任务进度： "
        prompt += f"✅已完成：{', '.join(completed) if completed else '无'}。 "
        prompt += f"⏳未完成：{', '.join(pending) if pending else '无'}。 "
        
        start_idx, end_idx = -1, -1
        for i, line in enumerate(self.file_lines):
            if "## 📊 宏观进度速览" in line: start_idx = i
            elif line.startswith("### 📁 [") and start_idx != -1 and end_idx == -1: end_idx = i
            
        review_text = ""
        if start_idx != -1 and end_idx != -1:
            review_text = "".join(self.file_lines[start_idx+1:end_idx]).strip()
            
        if review_text: 
            # 必须把随笔里的换行符也替换掉，防止用户输入的回车搞崩命令行
            clean_review = review_text.replace('\n', ' ')
            prompt += f"📝我的今日随笔：{clean_review}。 "
        
        prompt += "请作为我的极客 AI 助手，用温暖、鼓励的语气（带emoji）帮我总结今天的工作，夸夸我的努力，并为我明天未完成的任务给出一点简短、专业的建议。绝对不要废话。"
        
        # 在聊天框里打印出仪式感的提示语
        self.append_chat("⏰ 小克有话说:", "wy，现在是晚上 22:30 啦！已为您自动召唤 Claude 查阅今日进度...", COLORS['accent'])
        call_claude(prompt, self.show_claude_response, self.root)

    def setup_auto_review_timer(self):
        """后台隐形时钟：每天 22:30 准时触发"""
        def time_checker():
            triggered_today = False
            while True:
                now_str = datetime.now().strftime("%H:%M")
                if now_str == "22:30" and not triggered_today:
                    # 时间一到，扔给主线程去执行弹窗和调用
                    self.root.after(0, self.auto_ai_review)
                    triggered_today = True
                elif now_str == "01:30":
                    triggered_today = False # 过了午夜，重置触发器
                time.sleep(30) # 每半分钟看一眼时间
                
        threading.Thread(target=time_checker, daemon=True).start()

if __name__ == "__main__":
    # ==========================================
    # 🌟 新增：Windows 单例锁 (防止程序多开)
    # ==========================================
    mutex_name = "wy_TaskBoard_SingleInstance_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    
    # 183 代表 ERROR_ALREADY_EXISTS (已经有一个实例在运行了)
    if last_error == 183:
        # 弹出一个原生提示框提醒自己
        ctypes.windll.user32.MessageBoxW(0, "看板已经在后台运行啦！\n请直接按 Alt+Q 唤醒，或在右下角系统托盘找我哦~", "温馨提示", 0x40)
        sys.exit(0) # 自动结束这个多余的克隆体

    # 正常启动程序
    root = tk.Tk()
    app = TaskBoardApp(root)
    root.mainloop()