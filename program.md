# autoresearch_threads

AI 驅動的 Threads 內容系統，目標是「Threads 觸及 → 電子報導流 → 變現」。

## 系統概述

每 12 小時自動發佈 Threads 貼文（Content Agent），每週一分析數據並更新策略（Strategy Agent），並生成電子報草稿（Newsletter Agent）。

## 檔案地圖

| 路徑 | 用途 | 可修改？ |
|------|------|----------|
| `prompts/program.md` | Threads 貼文生成規則 | 是 |
| `prompts/strategy.md` | 本週流量策略與 CTA 指示 | 是（Strategy Agent 負責更新）|
| `prompts/resource.md` | 累積學習（每輪自動 append）| 是 |
| `prompts/swipe_file.md` | 高表現貼文範例庫 | 是 |
| `data/experiments.json` | 所有輪次數據 | 否（只讀）|
| `data/posts.json` | 已發佈貼文記錄 | 否（只讀）|
| `drafts/` | 電子報草稿 | 是（Newsletter Agent 寫入）|
| `logs/` | 執行日誌 | 否（只讀）|
| `orchestrator/` | Python 工具模組 | 謹慎修改 |

## Agent 1：Content Agent（每天 08:00, 20:00）

### 你要做的事
1. 讀取 `prompts/strategy.md` 確認本週流量目標
2. 執行 `python -m orchestrator.main`
3. 觀察輸出，確認發布成功（輸出中有「✅ 迴圈完成」）
4. 如果失敗，讀取錯誤訊息，嘗試修復後重試一次
5. 如果重試仍失敗，停止並記錄錯誤

### 成功標準
- 至少 1 篇貼文成功發佈
- 無 uncaught exception

### 禁止事項
- 不要修改 `data/` 下的任何 JSON 檔案
- 不要直接呼叫 Threads API
- 不要跳過 harvest 步驟

---

## Agent 2：Strategy Agent（每週一 08:30）

### 你要做的事
1. 執行 `python -m orchestrator.strategy_agent`
2. 確認 `prompts/strategy.md` 已更新（檢查修改時間或內容）
3. 讀取新的 strategy.md，確認格式正確（有「目標」、「CTA 使用時機」兩個 section）

### 成功標準
- `prompts/strategy.md` 修改時間為今天
- 檔案包含「本週流量策略」標題

### 禁止事項
- 不要手動編輯 strategy.md（讓 Python script 生成）
- 不要修改 `data/` 下任何檔案

---

## Agent 3：Newsletter Agent（每週一 09:00）

### 你要做的事
1. 確認 Strategy Agent 已執行（`prompts/strategy.md` 已更新）
2. 執行 `python -m orchestrator.newsletter_agent`
3. 確認草稿已生成：`ls drafts/newsletter_*.md`
4. 確認 email 已發送（輸出中有「Email sent」）

### 成功標準
- `drafts/` 下有今天日期的 newsletter 檔案
- 檔案字數 > 500 字

### 禁止事項
- 不要直接發佈到 Substack（需要人工審核）
- 不要刪除舊的草稿檔案

---

## 手動執行方式

你可以隨時用以下 prompt 手動叫我執行特定 agent：

```
讀 program.md，現在執行 Strategy Agent
讀 program.md，現在執行 Newsletter Agent
讀 program.md，現在執行 Content Agent
```

## 指標追蹤

- **Content Agent**：每輪發佈篇數、追蹤者數（在 Telegram 通知裡）
- **Strategy Agent**：strategy.md 更新頻率
- **Newsletter Agent**：`drafts/` 目錄裡的草稿數
