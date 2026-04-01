# autoresearch_threads

AI 驅動的 Threads 內容系統，目標是「Threads 觸及 → 電子報導流 → 變現」。

## 系統概述

每 12 小時自動發佈 Threads 貼文（Content Agent），每週一分析數據並更新策略（Strategy Agent），並生成電子報草稿（Newsletter Agent）。

**重要：執行 Python 指令時，一律使用 `.venv/bin/python` 而非 `python` 或 `python3`。**

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
1. 執行 `.venv/bin/python -m orchestrator.strategy_agent`，閱讀輸出的數據
2. 根據數據，**你自己分析**過去 7 天的貼文表現，制定本週流量策略
3. 將策略直接寫入 `prompts/strategy.md`，格式如下：

```markdown
# 本週流量策略（YYYY-MM-DD 更新）

## 目標
[衝觸及 / 導流電子報] 以及原因

## 核心策略
[基於數據的具體策略，包含哪些類型要多發、哪些結構有效、需要測試什麼新方向]

## 本週貼文配置
[表格：類型 × 數量 × Hook 結構 × 是否加 CTA]

## CTA 使用時機
當貼文主題涉及以下任一時加電子報 CTA：
- [主題列表]

## CTA 文案參考
- [2-3 個範例]

## 本週不加 CTA 的主題
- [主題列表]

## 本週電子報主題
[一句話描述，基於最高互動的貼文方向]
```

4. 寫入 `data/newsletter_status.json`：`{"week": "YYYY-MM-DD", "topic": "電子報主題", "status": "pending"}`

### 成功標準
- `prompts/strategy.md` 已更新，包含「本週流量策略」標題
- 策略基於實際數據，不是泛泛而談
- `data/newsletter_status.json` 已更新

### 禁止事項
- 不要修改 `data/` 下的 JSON 檔案（除了 newsletter_status.json）
- 不要編造數據，只用 Python 輸出的真實數據

---

## Agent 3：Newsletter Agent（每週一 09:00）

### 你要做的事
1. 確認 Strategy Agent 已執行（`prompts/strategy.md` 已更新）
2. 執行 `.venv/bin/python -m orchestrator.newsletter_agent`，閱讀輸出的數據
3. 根據數據，**你自己撰寫**一篇完整的電子報草稿：
   - 繁體中文
   - 格式：標題、引言、正文（3-5 個小節）、結語
   - 字數：800-1200 字
   - 基於本週電子報主題和 Top 貼文內容寫深度版本
   - 語氣：像跟朋友聊天，不要太正式
4. 將草稿寫入 `drafts/newsletter_YYYY-MM-DD.md`
5. 發送 Telegram 通知：`.venv/bin/python -c "from orchestrator.newsletter_agent import send_telegram; send_telegram('📰 電子報草稿已生成，請查看 drafts/ 資料夾')"` 

### 成功標準
- `drafts/` 下有今天日期的 newsletter 檔案
- 檔案字數 > 500 字
- Telegram 通知已發送

### 禁止事項
- 不要直接發佈到 Substack（需要人工審核）
- 不要刪除舊的草稿檔案
- 不要修改 `data/` 下任何檔案

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
