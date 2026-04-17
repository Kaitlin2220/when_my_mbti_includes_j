# Changelog

## 2026-04-17
- **真·多轮对话持久化**：重构了 Claude 问答调用逻辑（`call_claude`），从过去低效的手动截取记录拼接，全面切换到了利用 Claude CLI 原生的 `-p --output-format json --resume <session_id>` 对话会话机制。此更新彻底解决了「AI 无法读取上文」的问题，现在小克能准确记忆前后文聊天脉络并提供连贯建议了（`local_taskboard_modern_V2.pyw`）。
- **紧急热修复**：清理了文件头部因误触多打的字符从而引发程序在启动时报 `NameError` 的问题（`local_taskboard_modern_V2.pyw`）。

## 2026-04-06
- **成就解锁系统**：新增横向时间轴成就页面，两条路径（💼 找工作 / 📚 毕业），点击节点切换解锁状态，数据持久化到 `achievement.json`；解锁时弹出 AI 生成的专属祝贺弹窗（`AchievementsDialog`，`local_taskboard_modern_V2.pyw`）。
- **成长雷达图**：新增六维成长雷达图（学习力、情绪、执行、人际、创新、健康），点击顶栏「🌱 成长」按钮弹出 matplotlib 渲染的雷达图，数据存 `growth_data.json`（`GrowthRecordDialog`，`local_taskboard_modern_V2.pyw`）。
- **自动成长分析**：每次「入复盘」后自动调用 Claude 分析复盘内容，更新雷达图对应维度（别名映射支持健康/运动/体能等说法），结果输出到聊天框（`_analyze_review_and_update_growth`，`local_taskboard_modern_V2.pyw`）。
- **统一输入区**：右侧面板合并为单个输入框 + 三个按钮（问小克 / 入复盘 / + 任务），分类下拉框在输入框上方（`unified_input`，`local_taskboard_modern_V2.pyw`）。
- **成就数据自动重置**：节点定义变更时自动检测并重置 `achievement.json`（`load_achievements`，`local_taskboard_modern_V2.pyw`）。

## 2026-03-28
- Introduced Claude memory persistence so the taskboard assistant can recall prior context and preferences across sessions, enabling warmer, more relevant guidance during reviews ([CLAUDE.md](CLAUDE.md)).
- Streamlined the assistant response pipeline to cut turnaround time for UI console replies, keeping the taskboard interactions snappier when juggling multiple task lists ([local_taskboard_modern_V2.pyw](local_taskboard_modern_V2.pyw)).

- Introduced Claude memory persistence so the taskboard assistant can recall prior context and preferences across sessions, enabling warmer, more relevant guidance during reviews ([CLAUDE.md](CLAUDE.md)).
- Streamlined the assistant response pipeline to cut turnaround time for UI console replies, keeping the taskboard interactions snappier when juggling multiple task lists ([local_taskboard_modern_V2.pyw](local_taskboard_modern_V2.pyw)).

## 2026-03-23
- Automated the monthly calendar block generation and ensured every Daily Report stays in sync with `calendar_events.json`, eliminating manual edits and keeping the Markdown view consistent with the app ([local_taskboard_modern_V2.pyw](local_taskboard_modern_V2.pyw)).
- Polished the calendar UI by enforcing uniform cell sizing and wiring in week-navigation controls so the in-app timeline can slide across weeks without reopening the app ([local_taskboard_modern_V2.pyw](local_taskboard_modern_V2.pyw)).
- Synced calendar event updates back into the Markdown reports during load to keep the textual dashboard current whenever the assistant starts ([local_taskboard_modern_V2.pyw](local_taskboard_modern_V2.pyw)).
- Audited the workspace assets and confirmed unused bootstrap scripts/icons so only the active V2 taskboard artifacts remain in focus for future cleanups (workspace root).
- Added stable per-task ordering metadata plus Markdown re-write logic so checking a task automatically pushes it to the bottom of its category, while unchecking restores its original spot ([local_taskboard_modern_V2.pyw](local_taskboard_modern_V2.pyw)).
