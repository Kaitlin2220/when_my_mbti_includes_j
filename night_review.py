#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import glob
import subprocess
from datetime import datetime

# 锁定脚本执行路径
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def get_today_report():
    today_str = datetime.now().strftime("%Y-%m-%d")
    filepath = f"Daily_Report_{today_str}.md"
    return filepath if os.path.exists(filepath) else None

def main():
    filepath = get_today_report()
    if not filepath:
        return # 如果今天没有生成看板文件，则静默退出

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 防止重复复盘（如果今晚已经执行过，就不再执行）
    if any("## 🌙 晚间 AI 管家复盘" in line for line in lines):
        return

    # 提取今天已完成和未完成的任务
    completed = []
    pending = []
    for line in lines:
        if "- [x]" in line:
            completed.append(line.replace("- [x]", "").strip())
        elif "- [ ]" in line:
            pending.append(line.replace("- [ ]", "").strip())

    # 构建发送给 Claude 的专属指令
    prompt = (
        "作为我的专属科研与学习管家，请根据以下情况写一段150字左右的晚间复盘日志。"
        "语气要温和、鼓励，肯定我的成就，并对没做完的任务给出明天的微小建议。"
        "直接输出正文，不要任何废话。如果今天完全没有完成的任务，请温柔地鼓励我好好休息。"
        f"今天完成的任务：{'; '.join(completed) if completed else '无'}。"
        f"今天未完成的任务：{'; '.join(pending) if pending else '无'}。"
    )

    # 消除引号转义问题，确保在命令行完美执行
    safe_prompt = prompt.replace('"', '\\"')
    command = f'claude "{safe_prompt}"'

    try:
        # 静默唤醒 Claude 进行思考和总结
        result = subprocess.run(
            command, capture_output=True, text=True, encoding='utf-8',
            errors='ignore', shell=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        output = result.stdout.strip() if result.stdout.strip() else result.stderr.strip()
        
        if output:
            # 将充满温度的文字，永远刻印在今天的 Markdown 文件最底部
            with open(filepath, "a", encoding="utf-8") as f:
                f.write("\n\n## 🌙 晚间 AI 管家复盘\n\n")
                f.write(output + "\n")
                
            # 利用 Windows 原生命令，在屏幕右下角弹出一个极简的小提示框
            os.system('msg %username% "🌙 主人，今天的晚间复盘已生成，请在看板中查看。晚安，早点休息！"')

    except Exception as e:
        print(f"晚间复盘执行失败: {e}")

if __name__ == "__main__":
    main()