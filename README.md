# my成长计划 — 本地任务看板

> 一个陪伴我打怪的桌面看板，集成 Claude AI、成就系统与成长雷达图。

![Platform](https://img.shields.io/badge/Platform-Windows-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 隐私说明

- 本仓库包含本地化的任务看板源码，部分版本或历史可能包含用户本地路径或任务内容。
- 已创建并推送去私密化副本 `local_taskboard_modern_V2_sanitized.pyw`，该文件保留功能实现但移除了个人路径与具体任务文本（使用占位分类）。
- 如果需要彻底从远程历史移除敏感信息，请谨慎选择重写历史并强制 push 的方式（此操作会影响协作者）。


## 功能概览

### 界面预览

![看板主界面](screenshots/overview.png)
![日历添加日程](screenshots/calendar_create.png)
![成就时间轴](screenshots/achievement.png)
![成长雷达图](screenshots/growth.png)

### 任务管理
- **五大分类**：雅思、毕业论文（性别政策）、小论文（证言）、实习相关、其他
- **自动结转**：每天首次启动，未完成的任务自动从昨天抄写到今天
- **Markdown 驱动**：所有进度保存在 `Daily_Reports/Daily_Report_YYYY-MM-DD.md`，纯文本、版本可控
- **左右面板可拖拽**：任务区和助手区宽度自由调节

### AI 助手「小克」
- 内嵌 Claude API 交互，回答任务相关问题
- **22:30 自动复盘**：弹出今日总结 + 明日建议（温暖有梗，带 emoji）
- **隐藏指令**：
  - `【MOVE:关键词|YYYY-MM-DD】` — 任务改期
  - `【SPLIT:关键词|步骤1,步骤2】` — 任务拆解
  - `【CREATE_FILE:文件名】` + 代码块 — 生成脚本文件

### 一周日历条
- 横向展示本周 7 天，点击任意格子添加日程
- 日程信息实时同步写入当天的 Markdown 日历视图
- 有时间点的事件优先显示，支持左右翻周

### 成就解锁
- 两条路径：**找工作**（8 节点）/ **毕业**（7 节点）
- 点击横向时间轴节点切换解锁状态
- 解锁时调用 Claude 生成专属祝贺语弹窗

### 成长雷达图
- 六维评估：学习力 / 情绪 / 执行 / 人际 / 创新 / 健康
- 每次「入复盘」后，Claude 自动分析复盘内容并更新对应维度分值
- 雷达图可视化，支持刷新

### 每日仪式
- **语录**：每日 Claude 自动生成一条鼓励语录，保存到 `Daily_Quotes/`
- **盲盒插图**：每日随机从 `illustrations/` 展示两张图片

### 系统集成
- **Alt+Q** 全局热键：显示/隐藏窗口
- **系统托盘**：最小化后常驻右下角
- **单例锁**：防止重复启动
- **Windows 高分屏适配**

---

## 安装与运行

### 依赖

```bash
pip install tkinter-tooltip matplotlib numpy pystray pillow keyboard
```

> 部分库为 Python 标准库内置（tkinter、json、subprocess、threading 等）

### 运行

```bash
python local_taskboard_modern_V2.pyw
```

或双击运行。

### Claude CLI 集成

本应用依赖本地已安装的 `claude` CLI（ Anthropic 官方工具）进行 AI 对话。请确保：
- `claude` 命令可在终端中执行
- 首次使用已通过 `claude auth` 完成认证

---

## 文件结构

```
├── local_taskboard_modern_V2.pyw   # 主程序（单文件，~2000 行）
├── night_review.py                 # 独立复盘脚本（备用）
├── achievement.json                 # 成就解锁数据（自动生成）
├── growth_data.json                 # 成长雷达图数据（自动生成）
├── calendar_events.json             # 日历事件数据（自动生成）
├── tray_icon.png                    # 托盘图标
├── cat_logo.ico                     # 应用图标
│
├── Daily_Reports/                   # 每日 Markdown 进度文件
│   └── Daily_Report_YYYY-MM-DD.md
├── Daily_Quotes/                    # 每日语录存档
│   └── Quote_YYYY-MM-DD.txt
├── illustrations/                   # 盲盒插图库（放入 .png/.jpg 即可）
│
├── Archive/                         # 已完成任务归档
└── character/                       # 字体文件（宅在家麦克笔等）
```

---

## 自定义配置

### 分类路径（第 62–68 行）

```python
CATEGORY_PATHS = {
  "分类1": r"C:\Path\To\分类1",
  "分类2": r"D:\Path\To\分类2",
  "分类3": r"C:\Path\To\分类3",
  "分类4": r"C:\Path\To\分类4",
  "分类5": r"C:\Path\To\分类5"
}
```

修改路径后，点击分类标题旁的「📂 目录」按钮可直接打开对应文件夹。

### 配色方案（第 44–60 行）

```python
COLORS = {
    'bg_main': '#FFFFFF',       # 主背景：白底
    'accent': '#F98C53',        # 强调色：马卡龙橙
    'success': '#D2E0AA',       # 成功/完成色
    'blue': '#ABD7FB',          # 蓝色系
    'peach': '#F6AD83',         # 桃粉色
}
```

---

## 技术栈

| 组件 | 技术 |
|---|---|
| GUI 框架 | Tkinter（Python 标准库） |
| 图表渲染 | Matplotlib |
| 系统托盘 | pystray + PIL |
| 全局热键 | keyboard |
| AI 集成 | Claude CLI（subprocess 调用） |
| 数据存储 | 纯文本 Markdown + JSON |
| 平台 | Windows（高 DPI 适配） |

---

## 设计理念

本看板服务于研究生的多线任务困境：**毕业论文 / 小论文 / 实习**多条主线并行。核心设计原则：

1. **反拖延优先**：AI 助手在晚 22:30 自动介入，用温暖+极客的语气帮用户复盘，拒绝说教
2. **零认知负担**：任务直接写在 Markdown 里，不需要数据库迁移，随时可以 git diff 回溯
3. **成长可见化**：成就时间轴和雷达图让漫长旅途有节点感
4. **纯本地优先**：所有数据存在本地，不依赖任何云服务（Claude 调用除外）

---

## License

MIT — 可自由使用、修改、分发。
