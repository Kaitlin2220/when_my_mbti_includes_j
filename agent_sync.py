import sqlite3
import os
import shutil
from datetime import datetime
import re

# ==========================================
# 1. 配置区：定义你的 5 大核心工作流与关键词
# ==========================================
CATEGORIES = {
    "雅思": ["ielts", "雅思", "听力", "阅读", "写作", "口语", "listening", "reading", "writing", "speaking"],
    "毕业论文（性别政策）": ["性别政策", "stata", "数据", "merge", "did", "rdd", "回归", "补充数据", "广告", "匹配"],
    "小论文（证言）": ["证言", "小论文", "文献", "citiation"],
    "实习相关": ["实习", "简历", "产品视频", "面试", "笔试", "hr"],
    "其他": [] # 兜底选项
}

# ==========================================
# 2. 核心功能：静默读取 Windows 便笺数据库
# ==========================================
def fetch_sticky_notes():
    # Windows 10/11 便笺数据库默认路径
    db_path = os.path.expandvars(r'%LocalAppData%\Packages\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe\LocalState\plum.sqlite')
    temp_db = "temp_notes.sqlite"
    
    # 复制数据库以避开文件占用锁
    try:
        shutil.copy2(db_path, temp_db)
    except FileNotFoundError:
        print("未找到便笺数据库，请确认使用的是 Windows 自带便笺。")
        return []

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # 提取文本 (Note 表中的 Text 字段)
    cursor.execute("SELECT Text FROM Note WHERE Text IS NOT NULL")
    raw_notes = cursor.fetchall()
    conn.close()
    os.remove(temp_db)
    
    return [clean_note_text(note[0]) for note in raw_notes]

def clean_note_text(raw_text):
    """清洗便笺底层的 RTF/格式化标签，提取纯文本"""
    # 移除 \id=xxx, \ul=xxx 等系统自带的格式标签
    clean_text = re.sub(r'\\[a-zA-Z0-9=]+ ?', '', raw_text)
    # 移除多余的空行和首尾空格
    return '\n'.join([line.strip() for line in clean_text.split('\n') if line.strip()]).strip()

# ==========================================
# 3. 智能路由：根据关键词对便笺进行分类
# ==========================================
def categorize_notes(notes):
    categorized = {key: [] for key in CATEGORIES.keys()}
    
    for note in notes:
        if not note: continue
        assigned = False
        note_lower = note.lower()
        
        for cat, keywords in CATEGORIES.items():
            if cat == "其他": continue
            if any(kw in note_lower for kw in keywords):
                categorized[cat].append(note)
                assigned = True
                break # 匹配到第一个类别就跳出
                
        if not assigned:
            categorized["其他"].append(note)
            
    return categorized

# ==========================================
# 4. 闭环输出：生成 Markdown 每日复盘与明日规划
# ==========================================
def generate_daily_report(categorized_data):
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_filename = f"Daily_Report_{today_str}.md"
    
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(f"# 📅 {today_str} 每日复盘与明日规划\n\n")
        f.write("## 📊 宏观进度速览\n\n")
        
        for category, notes in categorized_data.items():
            if notes:
                f.write(f"### 📁 [{category}]\n")
                for note in notes:
                    # 将多行便笺转化为引用的待办格式
                    formatted_note = note.replace('\n', ' / ')
                    f.write(f"- [ ] {formatted_note}\n")
                f.write("\n")
                
        f.write("---\n")
        f.write("## 💡 每日想法 (Daily Thoughts)\n")
        f.write("> 请在此处写下今天的感悟、跑数据的卡点，或者新的研究灵感...\n\n")
        
    print(f"Extraction successful! Generated daily report: {report_filename}")
    return report_filename

if __name__ == "__main__":
    print("Agent is syncing notes in background...")
    notes = fetch_sticky_notes()
    if notes:
        categorized_data = categorize_notes(notes)
        generate_daily_report(categorized_data)
    else:
        print("No notes found.")