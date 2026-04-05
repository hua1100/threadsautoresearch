# Competitor Scout 設計文件

**日期：** 2026-04-05
**目標：** 爬取競品 AI 帳號貼文，分析格式策略，輔助優化 generate prompt

---

## 背景

目前 autoresearch_threads 的素材來源（YouTube、GitHub、Telegram 轉發）導致生成貼文主題同質化嚴重。需要引入競品帳號的格式觀察，讓 AI 在生成時能參考高表現帳號的發文結構。

---

## 架構

```
python -m orchestrator.competitor_scout
  │
  ├─ [1] X 帳號發現（自動）
  │     用 apify/twitter-scraper 搜尋關鍵字
  │     關鍵字：["AI tools", "AI tutorial", "AI workflow"]
  │     取最近 7 天高互動貼文（likes + retweets 總和排名）→ 抽出作者帳號
  │     過濾條件：followers > 500k 視為名人，排除
  │     取 top 5-10 帳號作為分析對象
  │
  ├─ [2] 爬蟲層（Apify HTTP API）
  │     Threads: apify/threads-scraper
  │       帳號：@prompt_case, @iamraven.tw, @aiposthub
  │       每帳號最近 50 篇貼文
  │     X: apify/twitter-scraper
  │       帳號：步驟 1 發現的 top N 帳號
  │       每帳號最近 50 篇貼文
  │     timeout：3 分鐘 / actor，超時跳過並記錄 warning
  │
  ├─ [3] 分析層（Claude claude-sonnet-4-6）
  │     per-account 分析：
  │       - 平均貼文長度（字數區間分佈）
  │       - 換行/段落習慣（單句換行 vs 段落式 vs 條列）
  │       - Emoji 使用頻率與位置（開頭/結尾/穿插）
  │       - Hook 句型分類（提問型/數字型/預言型/故事型/衝突型）
  │       - 內容類型分佈（工具介紹/教學步驟/趨勢新聞/觀點辯論）
  │       - CTA 模式（有無、位置、句式）
  │     跨帳號綜合歸納：
  │       - 3-5 條「高表現帳號共同格式規則」
  │       - 與目前自身貼文格式的差距點
  │
  ├─ [4] 輸出層
  │     data/competitor_raw.json（原始爬蟲資料備份）
  │     data/competitor_report.md（人讀分析報告）
  │
  └─ [5] 確認閘
        CLI 詢問是否 patch strategy.md
        若是 → 追加「競品格式觀察」區塊到 prompts/strategy.md
        Telegram 通知：競品分析報告已就緒
```

---

## 新增檔案

| 檔案 | 用途 |
|------|------|
| `orchestrator/competitor_scout.py` | 主模組，可獨立執行 |
| `orchestrator/apify_client.py` | Apify HTTP API 封裝 |
| `data/competitor_raw.json` | 原始爬蟲資料（git ignore） |
| `data/competitor_report.md` | 分析報告 |

---

## 設定變更

**`.env` 新增：**
```
APIFY_API_TOKEN=your_token_here
```

**`config.py` 新增：**
```python
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")

COMPETITOR_THREADS_ACCOUNTS = [
    "prompt_case",
    "iamraven.tw",
    "aiposthub",
]

COMPETITOR_X_SEARCH_KEYWORDS = [
    "AI tools",
    "AI tutorial",
    "AI workflow",
]

COMPETITOR_POSTS_PER_ACCOUNT = 50
COMPETITOR_X_TOP_N = 5          # 發現步驟取幾個帳號
COMPETITOR_X_MAX_FOLLOWERS = 500_000  # 超過視為名人，排除
```

---

## 費用估算

| 步驟 | 預估成本 |
|------|---------|
| Threads 3 帳號 × 50 篇 | ~$0.10 |
| X 搜尋 + top 5 帳號爬取 | ~$0.20 |
| **每次執行合計** | **~$0.30** |

---

## 執行方式

```bash
# 手動執行（不進入主輪迴）
python -m orchestrator.competitor_scout

# 執行後 CLI 詢問：
# > 分析完成。是否更新 prompts/strategy.md？[y/N]
```

---

## 錯誤處理

- Apify actor timeout（3 分鐘）→ 跳過該帳號，記錄 warning，繼續其他帳號
- Apify API 錯誤 → 印出錯誤，不中斷整個流程
- 爬取結果為空 → 跳過分析，報告中標注「無資料」
- Claude 分析失敗 → 保留原始資料，不更新 strategy.md

---

## 不在本次範圍內

- 整合進 `main.py` 主輪迴（未來可選）
- 自動排程（未來可加 cron）
- 爬取貼文的互動數據（本次只分析文字格式）
