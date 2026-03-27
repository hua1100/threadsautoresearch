# Autoresearch Threads — 系統設計規格

## 概述

套用 Karpathy autoresearch 的自動實驗迴圈模式，應用在 Threads 貼文優化。系統全自動抓取素材、產出貼文、發佈、收割數據、分析學習、迭代改進。目標是最大化觸及（views），快速找到最佳貼文方向。

## 帳號現況

- Threads 追蹤者：44
- Instagram：無經營（0 追蹤者）
- 過去經驗：送工具/模板/教學文章的貼文表現較好
- 內容方向：AI 相關

## 兩階段策略

### Phase 1：探索模式（追蹤者 < 100）

- 每天 3-5 篇貼文，刻意分散不同維度組合
- 不做嚴格淘汰，用加權分數排序標記 top/bottom performers
- AI 分析趨勢，更新 resource.md
- 目標：快速找到有效方向，累積初始學習

### Phase 2：Tournament 模式（追蹤者 ≥ 100）

- 切換到官方 Threads Insights API
- 嚴格 baseline vs challenger
- Challenger 勝出門檻 > 10% 才能取代 baseline
- 每次 challenger 只變 1-2 個維度，確保能歸因
- 假設驗證框架

兩階段共用同一套 resource.md，學習不斷線。Phase 切換在每次迴圈開始時自動判斷。

## 系統架構

```
autoresearch_threads/
├── orchestrator/
│   ├── main.py              # 進入點，Phase 判斷 + 迴圈控制
│   ├── harvest.py           # 收割數據（Chrome DevTools MCP + 非官方 API）
│   ├── analyze.py           # AI 分析表現，提取學習
│   ├── generate.py          # AI 產出新貼文（吃素材 + resource.md）
│   ├── deploy.py            # 發佈到 Threads + 格式清理
│   ├── config.py            # 集中設定（env vars）
│   ├── notify.py            # Telegram Bot 通知
│   └── sources/
│       ├── x_curated.py     # 讀取 Telegram 轉發的 X.com 內容 + 策展檔案
│       ├── youtube.py       # 抓 YouTube 頻道新影片，用 ShiFu MCP transcribe_url 取逐字稿
│       └── github.py        # SSH 讀取使用者 GitHub 專案動態
│
├── prompts/
│   ├── program.md           # 生成規則（貼文風格、維度定義、Phase 規則）
│   ├── swipe_file.md        # 高表現貼文範例庫
│   └── resource.md          # 累積學習（自動更新）
│
├── data/
│   ├── posts.json           # 所有已發佈貼文記錄
│   ├── metrics.json         # 每篇貼文的數據追蹤
│   └── experiments.json     # 每輪實驗記錄
│
├── .github/workflows/
│   └── autoresearch.yml     # 每 12 小時觸發
│
└── .env                     # API keys、Threads 憑證
```

設計決策：
- 用 JSON 檔而非資料庫：前期資料量小，JSON + git 追蹤足夠
- 素材抓取獨立模組：每個來源一個 scraper，方便擴展
- prompts/ 和 data/ 分開：AI 知識庫 vs 原始數據，職責清楚

## 12 小時迴圈流程

每次迴圈依序執行 5 個階段：

### 1. SOURCE（抓素材）

- **x.com（策展模式）**：每次迴圈先用 Telegram `getUpdates` API 拉取使用者轉發的 X.com 好內容，append 到 `prompts/x_curated.md` 持久化，generate 時讀取作為素材
- **YouTube（8 個頻道）**：檢查新影片，有就用 ShiFu MCP `transcribe_url` 抓逐字稿，AI 提取可用素材
  - every.to
  - Lenny's Podcast
  - How I AI
  - a16z
  - Greg Isenberg
  - Stephen G. Pope
  - Y Combinator
  - Nick Saraev
- **GitHub**：用 SSH 檢查使用者 repo 最近 commit/PR

### 2. HARVEST（收割數據）

雙管齊下抓取已發佈貼文的表現數據：

**方法 A：Chrome DevTools MCP**
- 登入 Threads 網頁版
- 進到每篇貼文頁面抓取 views、likes、replies、reposts
- 優點：能拿到 views（核心指標）
- 缺點：需要維持登入 session

**方法 B：非官方 API（threads-api PyPI 套件）**
- 抓公開可見的 likes、replies、reposts
- 優點：穩定
- 缺點：可能拿不到 views

**合併邏輯**：
- Views → 優先方法 A
- Likes/Replies/Reposts → 兩邊取較大值
- 任一方法失敗 → 降級到另一個繼續運作

同時抓取追蹤者數量，用於 Phase 切換判斷。≥ 100 時 Telegram 通知並自動切換到官方 Insights API。

### 3. ANALYZE（分析）

**加權分數計算**：
```
score = views × 0.6 + likes × 0.2 + replies × 0.2
```
各指標先做 min-max 正規化再加權。

**AI 分析維度**：
- 內容類型、Hook 風格、格式長度、語氣、素材來源、發文時間
- 標記 top/bottom performers
- 提取 2-3 條 actionable learnings
- 更新假設狀態（validated / disproven / pending）

### 4. GENERATE（產出新貼文）

AI 讀取：
1. `program.md`（生成規則）
2. `swipe_file.md`（範例庫）
3. `resource.md`（累積學習）
4. 本輪抓到的素材

產出 3-5 篇貼文，每篇包含：
- 貼文內容（500 字元以內，自然流暢）
- 標記維度（內容類型、hook 風格、格式、語氣、CTA、素材來源）
- Hypothesis（這篇在測試什麼）

Phase 1：刻意分散不同維度組合
Phase 2：基於 baseline，challenger 只變 1-2 個維度

### 5. DEPLOY（發佈）

使用 Threads 官方 API 發佈（發文不需要 100 追蹤者門檻）。

**格式清理（critical）**：
- 移除 literal `\n\n` 字串
- 確保換行用真正的 newline character
- 移除多餘空行、頭尾空白
- AI 生成 prompt 明確要求自然流暢文字，不加格式標記

**排程分散發佈**：
```
迴圈 A（08:00 台灣時間觸發）：
  09:00 發第 1 篇
  11:00 發第 2 篇
  13:00 發第 3 篇

迴圈 B（20:00 台灣時間觸發）：
  21:00 發第 4 篇
  23:00 發第 5 篇
```

寫入 posts.json 記錄發佈時間、內容、hypothesis、維度標記。

## 貼文維度定義

| 維度 | 選項 |
|------|------|
| 內容類型 | 工具分享、開發心得、教學知識點、新聞/趨勢、觀點/辯論 |
| 素材來源 | x.com、YouTube（各頻道）、GitHub（各 repo） |
| Hook 風格 | 提問型、數據型、故事型、爭議型、清單型、送資源型 |
| 格式 | 短句（<100字）、中篇（100-300字）、長文（300-500字） |
| 語氣 | 專業分析、輕鬆口語、急迫感、教學口吻 |
| CTA | 無 CTA、追蹤我、留言互動、分享給朋友 |

## 學習累積機制

### resource.md 結構

```markdown
# Threads Auto Research — 累積學習

## 已驗證規則
<!-- 被 2+ 輪數據驗證的規則，生成時必須遵守 -->

## 待驗證假設
<!-- 每輪嘗試推進至少一個假設 -->

## 實驗記錄
<!-- 每輪自動 append -->
```

### 累積流程

1. 每輪 `analyze.py` 用 AI 分析後，自動 append 新的 Round 記錄到 resource.md
2. 假設被 2+ 輪支持 → 升級到「已驗證規則」
3. 假設被否定 → 標記 disproven 並記錄原因
4. `generate.py` 每次生成前必讀 resource.md

### 初始學習（來自使用者經驗）

- 送資源型貼文（工具/模板/教學）觸及表現較好

## 通知

使用 Telegram Bot API，每次迴圈結束後發送：
- 上一輪各篇貼文表現（views、likes、replies、score）
- 本輪學習摘要
- 新產出的貼文內容 + hypothesis
- 目前追蹤者數量
- Phase 切換時額外通知

## 排程

GitHub Actions：
```yaml
schedule:
  - cron: '0 0 * * *'   # UTC 00:00 = 台灣 08:00
  - cron: '0 12 * * *'  # UTC 12:00 = 台灣 20:00
```

## 技術棧

- 語言：Python 3.12
- 排程：GitHub Actions
- AI：Claude API（分析 + 生成）
- 發佈：Threads 官方 API
- 數據收割：Chrome DevTools MCP + threads-api（非官方）
- YouTube 逐字稿：ShiFu MCP `transcribe_url`
- 通知：Telegram Bot API
- 儲存：JSON 檔 + git 版控
- GitHub 存取：SSH
