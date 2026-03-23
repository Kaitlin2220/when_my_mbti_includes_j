# Changelog

## 2026-03-23
- Automated the monthly calendar block generation and ensured every Daily Report stays in sync with `calendar_events.json`, eliminating manual edits and keeping the Markdown view consistent with the app ([local_taskboard_modern_V2.pyw](local_taskboard_modern_V2.pyw)).
- Polished the calendar UI by enforcing uniform cell sizing and wiring in week-navigation controls so the in-app timeline can slide across weeks without reopening the app ([local_taskboard_modern_V2.pyw](local_taskboard_modern_V2.pyw)).
- Synced calendar event updates back into the Markdown reports during load to keep the textual dashboard current whenever the assistant starts ([local_taskboard_modern_V2.pyw](local_taskboard_modern_V2.pyw)).
- Audited the workspace assets and confirmed unused bootstrap scripts/icons so only the active V2 taskboard artifacts remain in focus for future cleanups (workspace root).
- Added stable per-task ordering metadata plus Markdown re-write logic so checking a task automatically pushes it to the bottom of its category, while unchecking restores its original spot ([local_taskboard_modern_V2.pyw](local_taskboard_modern_V2.pyw)).
