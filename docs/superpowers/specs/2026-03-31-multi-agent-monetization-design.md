# Multi-Agent 變現架構設計

**日期**：2026-03-31
**狀態**：已確認，待實作

## 背景

現有系統是單一 Python pipeline（SOURCE → HARVEST → ANALYZE → GENERATE → DEPLOY），每 12 小時自動跑一輪，純粹優化 Threads 互動數據。

目標是擴展成「流量漏斗」思維：Threads 觸及 → 導流電子報 → 變現。電子報平台為 Substack（hualeee.substack.com）。

## 整體架構

```
┌─────────────────────────────────────────────────────┐
│              program.md（根目錄）                    │
│       Claude Code 的操作手冊，可自主執行             │
└──────────┬──────────────┬──────────────┬────────────┘
           │              │              │
    每12小時執行      每週一執行        每週一執行
           │              │              │
    ┌──────▼──────┐ ┌─────▼──────┐ ┌───▼──────────┐
    │Content Agent│ │Strategy    │ │Newsletter    │
    │（現有流程）  │ │Agent（新增）│ │Agent（新增） │
    └──────┬──────┘ └─────┬──────┘ └───┬──────────┘
           │              │              │
      發 Threads 貼文  寫 strategy.md  生成草稿
      (部分帶電子報CTA) (流量目標)     → email 給你
```

所有 Agent 透過 launchd 在本地觸發，執行 `claude -p "讀 program.md，執行 [Agent 名稱]"`。Python 程式碼是工具，Claude Code 是大腦。

## 新增檔案

| 檔案 | 用途 |
|------|------|
| `program.md` | 根目錄，Claude Code 操作手冊 |
| `prompts/strategy.md` | 當前流量目標與 CTA 指示（Strategy Agent 寫，Content Agent 讀）|
| `drafts/newsletter_YYYY-MM-DD.md` | Newsletter Agent 生成的草稿 |
| `logs/` | 各 Agent 執行日誌 |
| `~/Library/LaunchAgents/com.autoresearch.*.plist` | launchd 排程設定 |

## Agent 1：Content Agent

**觸發**：launchd，每天 08:00 和 20:00

**Claude Code 執行步驟**：
1. 讀 `program.md` 了解系統
2. 讀 `prompts/strategy.md` 取得本週流量目標
3. 執行 `python -m orchestrator.main` 跑完整 pipeline
4. 確認發布成功，如有錯誤自行修復後重試

**關鍵變化**：generate.py 生成貼文時要讀入 `strategy.md`，根據本篇主題判斷是否加電子報 CTA。

## Agent 2：Strategy Agent

**觸發**：launchd，每週一 08:30

**輸入**：
- `data/experiments.json`（過去 7 天數據）
- `data/posts.json`（貼文詳情含維度）
- `prompts/resource.md`（累積學習）

**Claude Code 執行步驟**：
1. 讀取過去 7 天 experiments.json
2. 分析哪些維度（content_type、strategy、tone）跟表現正相關
3. 判斷本週流量漏斗目標：衝觸及 vs 導流電子報
4. 如導流，決定適合當電子報鉤子的主題
5. 更新 `prompts/strategy.md`

**`strategy.md` 格式**：
```markdown
# 本週流量策略（YYYY-MM-DD 更新）

## 目標
[衝觸及 / 導流電子報（主題：XXX）]

## CTA 使用時機
當貼文主題涉及以下任一時加 CTA：
- [主題 A]
- [主題 B]

## CTA 文案參考
[2-3 條範例]

## 本週不加 CTA 的主題
[列舉]
```

## Agent 3：Newsletter Agent

**觸發**：launchd，每週一 09:00（Strategy Agent 完成後）

**輸入**：
- `prompts/strategy.md`（本週主題方向）
- `prompts/swipe_file.md`（高表現貼文）
- `data/experiments.json`（過去 7 天）

**Claude Code 執行步驟**：
1. 讀取上述三個檔案
2. 判斷本週適合延伸的電子報主題
3. 生成完整草稿，存到 `drafts/newsletter_YYYY-MM-DD.md`
4. 用 `mail` 指令寄給指定 email，附上草稿內容與本週 Threads 數據摘要

**電子報定位**：深度版本，Threads 貼文是預告，電子報是同主題完整分析。

**不自動發布到 Substack**：Substack 無官方 API，先做「生成草稿 → email → 手動發布」流程。

## program.md 結構

```markdown
# autoresearch_threads

## 系統概述
Threads 觸及 → 電子報導流 → 變現漏斗

## 檔案地圖
- orchestrator/   Python 工具模組（直接呼叫）
- prompts/        策略文件（讀寫）
- data/           數據（只讀）
- drafts/         電子報草稿（寫入）
- logs/           執行日誌

## Agent 1：Content Agent（每 12 小時）
## Agent 2：Strategy Agent（每週一 08:30）
## Agent 3：Newsletter Agent（每週一 09:00）

## 成功指標
## 禁止事項
```

## cron 排程

加入 crontab（`crontab -e`）：

```bash
# Content Agent：每天 08:00 和 20:00
0 8,20 * * * cd /Users/hua/autoresearch_threads && claude -p "讀 program.md，執行 Content Agent" >> logs/content-$(date +\%Y-\%m-\%d).log 2>&1

# Strategy Agent：每週一 08:30
30 8 * * 1 cd /Users/hua/autoresearch_threads && claude -p "讀 program.md，執行 Strategy Agent" >> logs/strategy-$(date +\%Y-\%m-\%d).log 2>&1

# Newsletter Agent：每週一 09:00
0 9 * * 1 cd /Users/hua/autoresearch_threads && claude -p "讀 program.md，執行 Newsletter Agent" >> logs/newsletter-$(date +\%Y-\%m-\%d).log 2>&1
```

## 實作順序

1. 建立 `program.md`（根目錄）
2. 建立 `prompts/strategy.md` 初始版本
3. 修改 `orchestrator/generate.py` 讀入 strategy.md 並決定 CTA
4. 建立 `orchestrator/strategy_agent.py`（供 Claude Code 呼叫的 CLI 工具）
5. 建立 `orchestrator/newsletter_agent.py`
6. 建立 `drafts/` 目錄
7. 建立 `logs/` 目錄
8. 設定 crontab 三條排程
9. 遷移現有 Content Agent 排程（Python → claude -p）
