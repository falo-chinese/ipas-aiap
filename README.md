# iPAS AI應用規劃師 2026 備考 Workspace

## 這個 repo 用來做什麼
這是 Pam 準備 **iPAS AI應用規劃師初級** 考試的備考系統，不是程式專案，而是讀書計畫、進度追蹤、錯題本、行事曆的集中管理處。

- 考試名稱：iPAS AI應用規劃師初級
- 目標考試日期：**2026/8/15**
- 備考期間：2026/7/6 – 2026/8/15
- 科目一：人工智慧基礎概論
- 科目二：生成式 AI 應用與規劃
- 讀書策略：官方範圍打底 → 考古題高頻名詞刷熟 → 用工作場景轉成情境題

## 資料夾說明

| 路徑 | 內容 |
| --- | --- |
| `docs/study-plan.md` | 7/6–8/15 每週讀書計畫 |
| `docs/google-drive-structure.md` | 建議的 Google Drive 資料夾結構 |
| `docs/today-checklist.md` | 今天要完成的事項 |
| `templates/progress-tracker.csv` | 每日進度追蹤表（匯入 Google Sheets） |
| `templates/error-log.csv` | 錯題本模板（匯入 Google Sheets） |
| `templates/concept-card.csv` | 高頻名詞記憶卡模板（匯入 Google Sheets 或 Anki） |
| `calendar/ipas-study-calendar.ics` | 可直接匯入 Google Calendar 的讀書提醒事件 |

## 每日／每週怎麼用

1. 每天讀書前先看 `docs/study-plan.md` 對應這週的任務。
2. 刷完題後，把結果填進 `templates/progress-tracker.csv`（或已匯入 Sheets 的版本）。
3. 錯題立刻記進 `templates/error-log.csv`，標好錯題類型與下次複習日。
4. 每整理出一個高頻名詞，就加一張卡進 `templates/concept-card.csv`。
5. `calendar/ipas-study-calendar.ics` 只需匯入一次，之後 Google Calendar 會自動提醒。

## 目前狀態
本次由 Claude 接續產出所有檔案內容；GitHub Pages、Google Drive、Sheets 已完成初版部署。接下來以每週執行、刷題、錯題整理與考前複習為主。
