# 懶人包自動生成 + LINE 導流閉環

## 目標

高表現 Threads 貼文自動生成懶人包 PDF，在 Threads 留言引導用戶加入 LINE 官方帳號，輸入關鍵字領取。全程自動化，並追蹤完整漏斗數據。

## 核心流程

```
觸發（自動 Top1 / Telegram 手動）
  │
  ├─ Claude 生成懶人包內容（Markdown）
  ├─ Pencil MCP 設計排版 → 匯出 PDF
  ├─ 上傳 PDF 到 Cloudflare R2
  ├─ 記錄到 data/lazy_packs.json
  ├─ Threads 原貼文留言引導加 LINE
  ├─ LINE Messaging API 設定關鍵字回覆
  └─ Telegram 通知你「懶人包已上線」
```

## 追蹤漏斗

```
Threads 貼文觸及（views）
  → 懶人包留言曝光（replies）
    → LINE 新好友（follow 事件）
      → 關鍵字領取（message 事件）
        → PDF 實際下載（Worker 計數）
```

每一層都有數據回饋到 Strategy Agent。

---

## 1. 觸發機制

### 自動觸發（每週 Top 1）

Strategy Agent 每週一分析時，挑出上週表現最好的貼文（score 最高且 views >= 5000）。如果該貼文尚未生成過懶人包（不在 `lazy_packs.json` 中），觸發生成。

views 門檻值可在 `.env` 設定（`LAZY_PACK_MIN_VIEWS=5000`），初期可調低測試。

### 手動觸發（Telegram）

Content Agent 的 `fetch_incoming_messages` 已經會收 Telegram 訊息。新增規則：

- 訊息格式：`懶人包 <media_id>` 或 `懶人包 <permalink>`
- 收到後觸發懶人包生成流程
- 如果該貼文已有懶人包，回覆「已存在」+ 連結

## 2. 懶人包內容生成

### Claude 生成

新增 `orchestrator/lazy_pack_agent.py`，呼叫 Claude 生成內容：

**輸入：**
- 原貼文全文
- 貼文的 dimensions（content_type, source 等）
- 相關素材（如果 source 是 youtube，嘗試拉原始 transcript）

**Prompt 方向：**
```
你是一個 AI 內容整理師。根據以下 Threads 貼文，生成一份「懶人包」。

原貼文：{text}
素材來源：{source_material}

格式要求：
1. 標題（吸引人的懶人包標題）
2. 核心概念（1-2 句話總結）
3. 重點整理（5-8 個，每個一句標題 + 2-3 句說明）
4. 行動建議（具體可執行的 1-3 步）
5. 一句話總結

繁體中文，800-1500 字。

同時產出：
- keyword：一個簡短的英文關鍵字（如 ai-agent），用於 LINE 觸發和檔名
- title：懶人包標題
```

**輸出：** JSON 包含 `content`（Markdown）、`keyword`、`title`

### PDF 生成

新增 `orchestrator/pdf_generator.py`：

1. 使用 Pencil MCP 設計懶人包模板（品牌風格、排版）
2. 將 Claude 生成的 Markdown 內容填入模板
3. 匯出為 PDF
4. 暫存到 `data/lazy_packs/{keyword}.pdf`

PDF 設計包含：
- 品牌 header（帳號名稱 / logo）
- 標題區
- 核心概念區
- 重點列表（編號 + 說明）
- 行動建議區
- Footer：LINE 官方帳號 QR code + Threads 帳號

## 3. PDF 存儲 + 下載追蹤

### Cloudflare R2 + Worker

部署一個 Cloudflare Worker，負責：

**PDF 上傳（從 Python 呼叫）：**
- `orchestrator/r2_client.py` 封裝上傳邏輯
- 使用 S3 兼容 API（R2 支持 S3 協議）上傳 PDF
- 上傳路徑：`lazy-packs/{keyword}.pdf`

**下載追蹤（Worker 端）：**
```
GET /lazy-packs/{keyword}.pdf
  → Worker 記錄下載事件（keyword, timestamp, user-agent）
  → 寫入 R2 的 analytics/{keyword}.json（追加）
  → 302 redirect 到 R2 的實際 PDF 檔案
```

或更簡單的方式：Worker 直接從 R2 讀取 PDF 回傳，同時計數。

**統計 API（供 Strategy Agent 拉取）：**
```
GET /lazy-packs/{keyword}/stats
  → 回傳 { "downloads": 47, "last_download": "2026-03-31T..." }
```

### R2 bucket 設定

- Bucket 名稱：`lazy-packs`
- 不開啟公開存取（透過 Worker 控制）
- Worker 綁定自定義域名或使用 `*.workers.dev`

## 4. Threads 留言引導

懶人包生成完成後，使用現有的 `threads_client.reply_to_post()` 在原貼文留言：

```
🎁 這篇的完整懶人包整理好了！
加入我的 LINE 官方帳號，輸入「{keyword}」立刻領取 👇
{LINE_ADD_FRIEND_URL}
```

留言文案可由 Claude 根據原貼文風格動態生成（未來迭代），初期用固定模板。

## 5. LINE Messaging API 整合

### 新增 `orchestrator/line_client.py`

封裝 LINE Messaging API：

**回覆訊息：**
```python
def reply_message(reply_token: str, text: str) -> None
def reply_pdf_link(reply_token: str, keyword: str, pdf_url: str) -> None
```

**推播訊息（未來可用）：**
```python
def push_message(user_id: str, text: str) -> None
```

### Cloudflare Worker 作為 LINE Webhook

LINE webhook 需要公開 HTTPS endpoint。複用 Cloudflare Worker：

```
POST /line/webhook
  → 驗證 signature（Channel Secret）
  → 解析事件：
    - follow 事件 → 記錄新好友（寫入 R2 analytics）
    - message 事件 → 比對關鍵字：
      - 匹配 → 回覆 PDF 下載連結
      - 不匹配 → 回覆預設訊息（「目前可用的懶人包：...」）
```

**關鍵字比對邏輯：**
- Worker 啟動時從 R2 讀取 `lazy-packs/index.json`（懶人包清單）
- 用戶輸入的文字去匹配 keyword
- 匹配成功 → 回覆：「這是你的懶人包 👉 {download_url}」

**`lazy-packs/index.json`（存在 R2）：**
```json
[
  {
    "keyword": "ai-agent",
    "title": "AI Agent 完整攻略懶人包",
    "url": "https://worker域名/lazy-packs/ai-agent.pdf"
  }
]
```

每次生成新懶人包時，`lazy_pack_agent.py` 上傳 PDF 後同時更新這個 index。

### LINE 統計數據

Worker 記錄到 R2 的 `analytics/line-events.json`：

```json
[
  {"type": "follow", "user_id": "U...", "timestamp": "2026-03-31T..."},
  {"type": "keyword_match", "keyword": "ai-agent", "user_id": "U...", "timestamp": "2026-03-31T..."}
]
```

Strategy Agent 可定期拉取這些統計。

## 6. 數據回饋到 Strategy Agent

Strategy Agent 的 prompt 新增「懶人包漏斗」section：

```
## 懶人包漏斗
- 本週生成：1 份（AI Agent 完整攻略）
- Threads 留言曝光：原貼文 replies +15
- LINE 新好友：+32
- 關鍵字領取：47 次
- PDF 下載：39 次
- 轉換率：留言→LINE 加入 213%（因為會擴散）
```

這讓 Strategy Agent 能判斷：
- 哪類主題的懶人包效果好
- 是否要增加/減少懶人包頻率
- CTA 文案是否需要調整

## 7. 完整觸發流程（時序）

### 自動觸發（週一）

```
08:30 Strategy Agent
  ├─ 分析數據，找到上週 Top 1（views >= 5000）
  ├─ 如果 Top 1 不在 lazy_packs.json → 觸發生成
  └─ 寫入 strategy.md 提到懶人包

08:35 Lazy Pack Agent（被 Strategy Agent 呼叫）
  ├─ Claude 生成內容 + keyword
  ├─ Pencil MCP 設計 → PDF
  ├─ 上傳 R2 + 更新 index.json
  ├─ Threads 留言引導
  ├─ 記錄 lazy_packs.json
  └─ Telegram 通知

持續  LINE Worker
  ├─ 接收 follow 事件 → 記錄
  ├─ 接收關鍵字 → 回覆 PDF 連結
  └─ 記錄所有事件到 analytics
```

### 手動觸發

```
你 → Telegram 傳「懶人包 <media_id>」
  ↓
Content Agent 收到 → 觸發 Lazy Pack Agent
  ↓
（同上流程）
```

## 新增檔案清單

| 檔案 | 職責 |
|------|------|
| `orchestrator/lazy_pack_agent.py` | 懶人包生成主流程（Claude 生成 + 觸發 PDF + 上傳 + 留言） |
| `orchestrator/line_client.py` | LINE Messaging API 封裝（回覆、推播） |
| `orchestrator/r2_client.py` | Cloudflare R2 S3 兼容 API 封裝（上傳 PDF、更新 index） |
| `orchestrator/pdf_generator.py` | Pencil MCP 模板設計 + PDF 匯出 |
| `data/lazy_packs.json` | 懶人包紀錄（keyword, url, claims 等） |
| `data/lazy_packs/` | PDF 本地暫存 |
| `worker/` | Cloudflare Worker（LINE webhook + PDF 下載追蹤 + 統計 API） |

## 新增 .env 變數

```
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_CHANNEL_SECRET=...
LINE_ADD_FRIEND_URL=https://line.me/R/ti/p/@你的帳號
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=lazy-packs
LAZY_PACK_MIN_VIEWS=5000
```

## 新增依賴

```
boto3>=1.34.0       # S3 兼容 API 操作 R2
weasyprint>=60.0    # Markdown → PDF（備選，看 Pencil 匯出能力）
```

## 測試計劃

| 測試檔 | 涵蓋範圍 |
|--------|---------|
| `test_lazy_pack_agent.py` | 觸發邏輯、Claude prompt 組裝、重複偵測、Telegram 手動觸發解析 |
| `test_line_client.py` | API 呼叫封裝、signature 驗證 |
| `test_r2_client.py` | PDF 上傳、index.json 更新 |
| `test_pdf_generator.py` | Markdown → PDF 轉換 |
| Worker 測試 | Cloudflare Worker 的 LINE webhook 處理、下載追蹤、統計 API |

## 不在本次範圍

- LINE Rich Menu 設計（未來可做選單式懶人包列表）
- 懶人包付費版（免費版引流，付費版深度內容）
- 多語言支持
- 懶人包過期機制
