# Crontab Setup（目標伺服器）

在目標伺服器上設定三個 agent 的排程。

## 前置確認

```bash
# 確認 claude CLI 路徑
which claude

# 確認專案路徑
ls /path/to/autoresearch_threads/program.md
```

## 新增 crontab

執行 `crontab -e`，加入以下三行（將 `/usr/local/bin/claude` 替換成 `which claude` 查到的路徑，將 `/path/to/autoresearch_threads` 替換成實際專案路徑）：

```
# autoresearch_threads agents

# Content Agent：每天 08:00 和 20:00
0 8,20 * * * cd /path/to/autoresearch_threads && /usr/local/bin/claude -p "讀 program.md，執行 Content Agent" >> /path/to/autoresearch_threads/logs/content-$(date +\%Y-\%m-\%d).log 2>&1

# Strategy Agent：每週一 08:30
30 8 * * 1 cd /path/to/autoresearch_threads && /usr/local/bin/claude -p "讀 program.md，執行 Strategy Agent" >> /path/to/autoresearch_threads/logs/strategy-$(date +\%Y-\%m-\%d).log 2>&1

# Newsletter Agent：每週一 09:00
0 9 * * 1 cd /path/to/autoresearch_threads && /usr/local/bin/claude -p "讀 program.md，執行 Newsletter Agent" >> /path/to/autoresearch_threads/logs/newsletter-$(date +\%Y-\%m-\%d).log 2>&1
```

## 注意事項

- `%` 在 crontab 裡必須轉義為 `\%`（如上面的 `\%Y-\%m-\%d`）
- 確認伺服器上 `claude` CLI 已登入（`claude --version` 可執行）
- 確認 `.env` 裡的 `NEWSLETTER_EMAIL` 已填入真實 email
- 如果原本有 `python -m orchestrator.main` 的舊排程，Content Agent 已取代它，可以移除

## 驗證

設定完後確認：
```bash
crontab -l | grep autoresearch
```

應看到三行排程。

## 手動測試 claude 可讀到 program.md

```bash
cd /path/to/autoresearch_threads && claude -p "讀 program.md，列出三個 agent 的名稱即可，不要實際執行任何東西"
```
