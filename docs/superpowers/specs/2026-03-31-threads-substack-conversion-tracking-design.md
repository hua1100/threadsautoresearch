# Threads → Substack 轉換追蹤閉環

## 目標

建立 Threads 貼文到 Substack 電子報的完整導流閉環：自動追蹤轉換率、協調電子報主題與 CTA 貼文、自動在留言放連結，並將轉換數據回饋到策略決策中。

## 核心設計原則

- **電子報優先**：先有電子報主題和草稿，CTA 貼文才跟上
- **自動偵測**：系統自動偵測 Substack 新文章發佈，不需手動通知
- **數據驅動**：Threads → Substack 轉換率回饋到 Strategy Agent 的決策

## 週期流程

```
週一 08:30  Strategy Agent
            ├─ 分析 7 天數據 + Threads→Substack 轉換率
            ├─ 決定「本週電子報主題」
            └─ 寫入 strategy.md

週一 09:00  Newsletter Agent
            ├─ 讀 strategy.md 的電子報主題
            ├─ 以該主題為核心生成草稿
            ├─ Email 草稿給作者
            └─ 建立 newsletter_status.json (status: "draft")

作者審稿 → 發佈到 Substack

每 12 小時  Content Agent
            ├─ 啟動時查 Substack 最新文章
            ├─ 偵測到新文章 → 更新 newsletter_status.json (status: "published", url: ...)
            ├─ 生成貼文時：主題相關 + 有已發佈電子報 → 可標記「電子報CTA」
            └─ Deploy 時：電子報CTA 貼文 → 自動留言放連結
```

## 改動清單

### 1. 新增 `data/newsletter_status.json`

追蹤當週電子報生命週期的狀態檔。

```json
{
  "week": "2026-03-31",
  "topic": "AI Agent 的真實成本",
  "status": "published",
  "url": "https://hualeee.substack.com/p/ai-agent-cost",
  "published_at": "2026-03-31T10:30:00Z"
}
```

狀態流轉：
- Newsletter Agent 建立 → `status: "draft"`，填入 `week` 和 `topic`
- Content Agent 偵測到新文章 → `status: "published"`，填入 `url` 和 `published_at`
- 下週一 Newsletter Agent 覆蓋為新的 draft

### 2. `orchestrator/substack_client.py` — 多維度 growth sources + 偵測新文章

**fetch_snapshot 改動：**

growth_sources 從只抓 Traffic 改為同時抓 Traffic 和 Subscribers 兩個維度。新增 `threads_funnel` 摘要欄位。

```json
{
  "date": "2026-03-31",
  "subscribers": 31,
  "total_email": 27,
  "open_rate": 25.9,
  "growth_sources": [
    {"source": "threads.net", "traffic": 2, "new_subscribers": 0},
    {"source": "direct", "traffic": 33, "new_subscribers": 3},
    {"source": "linkedin.com", "traffic": 17, "new_subscribers": 0}
  ],
  "threads_funnel": {
    "traffic": 2,
    "new_subscribers": 0,
    "conversion_rate": 0.0
  }
}
```

解析邏輯：
- 遍歷 `sourceMetrics`，對每個 source 找到 `Traffic` 和 `Subscribers` 的 metric total
- `threads_funnel` 獨立提取 `threads.net` 來源的數據
- `conversion_rate = new_subscribers / traffic`（traffic=0 時為 0）

**新增 fetch_latest_post：**

```python
def fetch_latest_post(self) -> dict | None:
    posts = self._get("/api/v1/archive", params={"sort": "new", "limit": 1})
    if posts:
        return {
            "title": posts[0]["title"],
            "url": posts[0]["canonical_url"],
            "date": posts[0]["post_date"],
        }
    return None
```

### 3. `orchestrator/threads_client.py` — 留言回覆

**create_post 加 reply_to_id 參數：**

```python
def create_post(text: str, reply_to_id: str | None = None) -> str | None:
    payload = {
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN,
    }
    if reply_to_id:
        payload["reply_to_id"] = reply_to_id
    ...
```

**新增 reply_to_post：**

```python
def reply_to_post(media_id: str, text: str) -> str | None:
    creation_id = create_post(text, reply_to_id=media_id)
    if not creation_id:
        return None
    time.sleep(30)
    return publish_post(creation_id)
```

### 4. `orchestrator/deploy.py` — 電子報 CTA 自動留言

發佈成功後的新邏輯：

```python
if media_id and post.get("dimensions", {}).get("cta") == "電子報CTA":
    newsletter = read_json(DATA_DIR / "newsletter_status.json")
    if isinstance(newsletter, dict) and newsletter.get("status") == "published":
        url = newsletter["url"]
        reply_text = f"完整深度分析在這裡 👉 {url}"
        threads_client.reply_to_post(media_id, reply_text)
```

如果 newsletter_status 不是 published 狀態，跳過留言（不 crash）。

### 5. `prompts/program.md` — CTA 維度新增選項

第 50 行的 cta 選項改為：

```
| cta | 無CTA、留言互動、分享給朋友、電子報CTA |
```

### 6. `orchestrator/strategy_agent.py` — 轉換率數據 + 電子報主題

**Prompt 新增 threads_funnel section：**

當 substack_snapshot 存在且有 threads_funnel 時，加入：

```
## Threads → 電子報轉換漏斗
- Threads 導流：{traffic} 次點擊
- 新增訂閱：{new_subscribers}
- 轉換率：{conversion_rate}%
```

**輸出格式新增一個 section：**

在 prompt 的輸出格式要求中加入：

```
## 本週電子報主題
[一句話描述本週電子報要寫的主題，基於最高互動的貼文方向]
```

**strategy.md 寫完後，初始化 newsletter_status.json：**

讀取剛寫完的 strategy.md，提取電子報主題，寫入 `newsletter_status.json`：

```json
{
  "week": "2026-03-31",
  "topic": "從 strategy.md 提取的主題",
  "status": "pending"
}
```

用 `pending` 而非 `draft`，因為 Newsletter Agent 還沒跑。

### 7. `orchestrator/newsletter_agent.py` — 主題導向草稿

**讀取電子報主題：**

從 `newsletter_status.json` 讀取 `topic`，如果沒有就 fallback 到原本的 top 5 方式。

**Prompt 改動：**

原本：「根據本週最佳表現貼文寫電子報」
改為：「本週電子報主題是 {topic}，以此為核心，參考相關的高表現貼文寫深度版本」

**建立後更新 status：**

草稿儲存後，更新 `newsletter_status.json` 的 `status` 為 `"draft"`。

### 8. `orchestrator/main.py` — 自動偵測新電子報

在 `run()` 中，harvest 之前新增偵測步驟：

```python
def check_newsletter_status():
    """自動偵測 Substack 新文章，更新 newsletter_status.json"""
    if not SUBSTACK_SID:
        return
    newsletter = read_json(DATA_DIR / "newsletter_status.json")
    if not isinstance(newsletter, dict):
        return
    if newsletter.get("status") == "published":
        return  # 已經是 published，不需再查

    client = SubstackClient(subdomain=SUBSTACK_SUBDOMAIN, sid=SUBSTACK_SID)
    latest = client.fetch_latest_post()
    if not latest:
        return

    # 比對：如果最新文章的 url 跟紀錄的不同，代表有新電子報
    if latest["url"] != newsletter.get("url"):
        newsletter["status"] = "published"
        newsletter["url"] = latest["url"]
        newsletter["published_at"] = latest["date"]
        write_json(DATA_DIR / "newsletter_status.json", newsletter)
        print(f"[NEWSLETTER] 偵測到新電子報: {latest['title']}")
```

注意：這裡有一個邊界情況 — 如果你在 Substack 發了一篇跟本週主題無關的文章，系統也會把它當作已發佈。可以接受，因為 CTA 連結指向的是你最新的文章，內容相關性由你在審稿時把關。

## 測試計劃

| 測試檔 | 新增測試 |
|--------|---------|
| `test_substack_client.py` | growth_sources 含 traffic+new_subscribers；threads_funnel 計算正確；fetch_latest_post 回傳結構 |
| `test_deploy.py` | 電子報CTA 貼文 + published status → 呼叫 reply_to_post；非 published → 不留言 |
| `test_threads_client.py` | create_post 帶 reply_to_id；reply_to_post 完整流程 |
| `test_newsletter_agent.py` | 草稿基於 topic 生成；newsletter_status 更新為 draft |
| `test_strategy_agent.py` | prompt 包含 threads_funnel；strategy.md 含電子報主題；newsletter_status 初始化 |
| `test_main.py` | check_newsletter_status 偵測新文章更新 status；已 published 不重複查 |

## 不在本次範圍

- Substack 自動發佈（仍需人工審稿）
- UTM 追蹤（Substack 免費版不支持）
- 留言文案動態生成（先用固定模板）
