# AutoResearch Threads — Mac Mini 交接文件

## 系統概述

自動化 Threads 貼文系統，套用 Karpathy autoresearch 的實驗迴圈模式。
每 12 小時自動：抓素材 → 收割數據 → AI 分析 → 產出貼文 → 發佈。

## 快速設定（5 分鐘）

### Step 1: Clone repo

```bash
git clone https://github.com/hua1100/threadsautoresearch.git
cd threadsautoresearch
```

### Step 2: 建立 Python 環境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: 設定 .env

```bash
cp .env.example .env
```

填入以下值：

| 變數 | 值 | 備註 |
|------|---|------|
| `THREADS_ACCESS_TOKEN` | `THAA...` | 到 2026-05-26 過期，過期後需重新生成 |
| `THREADS_USER_ID` | `26707161045541246` | |
| `ANTHROPIC_API_KEY` | `sk-ant-api03...` | |
| `TELEGRAM_BOT_TOKEN` | `8680258862:AAFC3oO4wOzJM31yrnqZQjTaG5kRhglEDBU` | @Threader111bot |
| `TELEGRAM_CHAT_ID` | `8282278089` | |
| `YOUTUBE_API_KEY` | `AIzaSyAx...` | Google Cloud Console |

所有值都在原本那台電腦的 `.env` 檔案裡，直接複製過來即可。

### Step 4: 驗證能跑

```bash
source .venv/bin/activate
python -m orchestrator.main
```

應該會看到 `[0/5] Phase 1 | ...` 到 `✅ 迴圈完成`。

### Step 5: 設定 Claude Code Scheduled Trigger

在 Mac Mini 上安裝 Claude Code 後，設定 scheduled trigger 每 12 小時跑一次。

## 架構說明

```
orchestrator/
├── main.py              # 主迴圈入口
├── config.py            # 環境變數設定
├── threads_client.py    # Threads API（發文 + 抓 insights）
├── harvest.py           # 收割貼文數據
├── harvest_browser.py   # Chrome DevTools 抓數據（需 MCP）
├── harvest_api.py       # Threads API 抓數據（需 100+ 追蹤者）
├── analyze.py           # AI 分析 + 評分
├── generate.py          # AI 產出新貼文
├── deploy.py            # 發佈到 Threads
├── notify.py            # Telegram 通知 + 收訊息
└── sources/
    ├── youtube.py       # YouTube Data API 偵測新影片
    ├── github.py        # 掃本地 git repo 活動
    └── x_curated.py     # Telegram 轉發素材 + YouTube 自動逐字稿
```

## 12 小時迴圈流程

```
1. SOURCE   — 抓 YouTube 新影片、本地 GitHub commit、Telegram 轉發內容
2. HARVEST  — 收割已發佈貼文的 views/likes/replies
3. ANALYZE  — AI 分析哪些策略表現好，提取 learnings
4. GENERATE — AI 根據素材 + learnings 產出 3-5 篇新貼文
5. DEPLOY   — 發佈到 Threads，Telegram 通知
```

## 素材來源

### 自動
- **YouTube**（8 頻道）：every.to, Lenny's Podcast, How I AI, a16z, Greg Isenberg, Stephen G. Pope, Y Combinator, Nick Saraev
- **GitHub**：掃描 `/Users/hua` 底下所有 git repo 的最近 commit

### 手動
- **Telegram @Threader111bot**：轉發 X.com 推文或 YouTube URL
  - YouTube URL 會自動抓逐字稿
  - 所有內容累積在 `prompts/x_curated.md`

## 學習累積

- `prompts/resource.md` — 每輪自動 append 學習記錄
- 已驗證規則會被標記，AI 產出時必須遵守
- 假設追蹤：H1-H7 待驗證

## 貼文策略（14 種）

1. 偏激言論開頭  2. 報年齡自介  3. 懶人包整理  4. 打賭預測
5. 逆向反差  6. 煽動情緒  7. 數字開頭  8. 新手教學
9. 討論賺錢  10. 勾起好奇  11. 蹭名人流量  12. 講故事
13. 筆戰爭議  14. 列點文

每篇貼文會標記使用的策略（如 "1+7"），方便後續分析哪些策略組合表現最好。

## 兩階段策略

- **Phase 1**（追蹤者 < 100）：探索模式，多方向測試
- **Phase 2**（追蹤者 ≥ 100）：Tournament 模式，baseline vs challenger

## 注意事項

### Threads Token 過期
Token 到 **2026-05-26** 過期。過期前需要重新生成：
1. 去 developers.facebook.com → 你的 App → Threads API
2. 生成新 token
3. 更新 `.env` 裡的 `THREADS_ACCESS_TOKEN`
4. 更新 GitHub Secrets（如果還在用 GitHub Actions）

### GitHub Actions
目前 GitHub Actions 也有設定（每 12 小時跑），如果用 Claude Code Scheduled 取代，可以去 repo Settings → Actions → 停用 workflow，避免重複發文。

### 新增 YouTube 頻道
編輯 `orchestrator/sources/youtube.py` 的 `CHANNEL_IDS` dict，加入新的 channel ID。

### 新增素材來源
在 `orchestrator/sources/` 下建新模組，然後在 `orchestrator/main.py` 的 `fetch_sources()` 裡加入。
