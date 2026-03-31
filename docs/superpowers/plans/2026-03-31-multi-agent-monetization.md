# Multi-Agent 變現架構 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 擴展現有 Threads 自動發文系統為三 agent 架構，加入每週策略分析與電子報草稿生成，並透過 Claude Code（非純 API）作為 orchestrator。

**Architecture:** 新增 `prompts/strategy.md` 作為 agent 間溝通橋樑。Strategy Agent 每週分析數據並更新 strategy.md；Content Agent 讀入 strategy.md 決定是否加電子報 CTA；Newsletter Agent 生成 Substack 草稿並 email。三個 agent 均由 cron 觸發 `claude -p` 執行，以 `program.md`（根目錄）作為 Claude Code 操作手冊。

**Tech Stack:** Python 3.14, anthropic SDK, pathlib, subprocess（mail 指令）, cron

---

## 檔案地圖

| 動作 | 檔案 | 說明 |
|------|------|------|
| 新增 | `program.md` | 根目錄，Claude Code 操作手冊 |
| 新增 | `prompts/strategy.md` | 本週流量策略（Strategy Agent 寫，Content Agent 讀）|
| 新增 | `orchestrator/strategy_agent.py` | Strategy Agent：分析數據→更新 strategy.md |
| 新增 | `orchestrator/newsletter_agent.py` | Newsletter Agent：生成草稿→email |
| 新增 | `tests/test_strategy_agent.py` | Strategy Agent 測試 |
| 新增 | `tests/test_newsletter_agent.py` | Newsletter Agent 測試 |
| 新增 | `drafts/.gitkeep` | 草稿目錄 |
| 新增 | `logs/.gitkeep` | log 目錄 |
| 修改 | `orchestrator/config.py` | 新增 DRAFTS_DIR, LOGS_DIR, NEWSLETTER_EMAIL |
| 修改 | `orchestrator/generate.py` | 讀入 strategy.md，加入 CTA 維度選項 |

---

## Task 1：Config + 目錄建立

**Files:**
- Modify: `orchestrator/config.py:35-39`
- Create: `drafts/.gitkeep`
- Create: `logs/.gitkeep`

- [ ] **Step 1: 修改 config.py，加入新路徑與 email 設定**

```python
# orchestrator/config.py 末尾加入（在現有 DATA_DIR 行之後）
DRAFTS_DIR = BASE_DIR / "drafts"
LOGS_DIR = BASE_DIR / "logs"
NEWSLETTER_EMAIL = os.environ.get("NEWSLETTER_EMAIL", "")
```

- [ ] **Step 2: 建立目錄與 .gitkeep**

```bash
mkdir -p drafts logs
touch drafts/.gitkeep logs/.gitkeep
```

- [ ] **Step 3: 在 .env 加入 NEWSLETTER_EMAIL**

在 `.env` 檔案加入：
```
NEWSLETTER_EMAIL=your@email.com
```
（替換成你實際的 email）

- [ ] **Step 4: 確認 config 可正常匯入**

```bash
.venv/bin/python -c "from orchestrator.config import DRAFTS_DIR, LOGS_DIR, NEWSLETTER_EMAIL; print(DRAFTS_DIR, LOGS_DIR, NEWSLETTER_EMAIL)"
```

預期輸出：`.../autoresearch_threads/drafts .../autoresearch_threads/logs your@email.com`

- [ ] **Step 5: Commit**

```bash
git add orchestrator/config.py drafts/.gitkeep logs/.gitkeep
git commit -m "feat: add DRAFTS_DIR, LOGS_DIR, NEWSLETTER_EMAIL to config"
```

---

## Task 2：建立初始 `prompts/strategy.md`

**Files:**
- Create: `prompts/strategy.md`

- [ ] **Step 1: 建立預設 strategy.md**

```bash
cat > prompts/strategy.md << 'EOF'
# 本週流量策略（初始版本）

## 目標
衝觸及（系統剛啟動，先累積數據再決定導流時機）

## CTA 使用時機
本週暫不加電子報 CTA，等 Strategy Agent 首次執行後更新。

## CTA 文案參考
- 「這個主題我在電子報寫了完整版，連結在 bio」
- 「想要完整的 step-by-step？電子報裡有」

## 本週不加 CTA 的主題
- 所有主題（等待 Strategy Agent 更新）
EOF
```

- [ ] **Step 2: 確認檔案存在**

```bash
cat prompts/strategy.md
```

- [ ] **Step 3: Commit**

```bash
git add prompts/strategy.md
git commit -m "feat: add initial strategy.md template"
```

---

## Task 3：修改 `generate.py` 讀入 strategy.md

**Files:**
- Modify: `orchestrator/generate.py:28-109`
- Test: `tests/test_generate.py`

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_generate.py` 裡加入這個測試（找到既有測試檔案加在末尾）：

```python
def test_generate_includes_strategy_in_prompt():
    """generate() 應將 strategy.md 內容傳入 prompt"""
    analysis = {
        "round_number": 1,
        "learnings": "",
        "scored_posts": [],
        "analysis": "test",
    }
    sources = {"youtube": [], "github": [], "x": []}

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='[{"text":"test","dimensions":{"content_type":"工具分享","strategy":"1","tone":"輕鬆口語","cta":"無CTA","source":"test"},"hypothesis":"test"}]')]

    with patch("orchestrator.generate.anthropic") as mock_anthropic, \
         patch("orchestrator.generate._read_prompt") as mock_read:

        def fake_read(filename):
            if filename == "strategy.md":
                return "## 本週流量策略\n導流電子報"
            return ""

        mock_read.side_effect = fake_read
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        generate(analysis, sources)

        call_args = mock_client.messages.create.call_args
        prompt_content = call_args[1]["messages"][0]["content"]
        assert "本週流量策略" in prompt_content
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
.venv/bin/pytest tests/test_generate.py::test_generate_includes_strategy_in_prompt -v
```

預期：FAILED（`strategy.md` 尚未被讀入）

- [ ] **Step 3: 修改 generate.py，加入 strategy.md 讀取**

在 `orchestrator/generate.py` 的 `generate()` 函數中：

將這段（第 28-31 行）：
```python
def generate(analysis: dict, sources: dict) -> list[dict]:
    program = _read_prompt("program.md")
    swipe = _read_prompt("swipe_file.md")
    resource = _read_prompt("resource.md")
```

改為：
```python
def generate(analysis: dict, sources: dict) -> list[dict]:
    program = _read_prompt("program.md")
    swipe = _read_prompt("swipe_file.md")
    resource = _read_prompt("resource.md")
    strategy = _read_prompt("strategy.md")
```

並在 prompt 字串（第 65 行 `prompt = f"""{program}`）中，在 `## 高表現範例庫` 之前插入：

```python
    prompt = f"""{program}

## 本週流量策略
{strategy}

## 高表現範例庫
{swipe}
```

同時更新 prompt 末段的 CTA 欄位說明，把 `"cta": "無CTA|留言互動|分享給朋友"` 改為：

```python
      "cta": "無CTA|留言互動|分享給朋友|電子報CTA",
```

- [ ] **Step 4: 執行測試確認通過**

```bash
.venv/bin/pytest tests/test_generate.py::test_generate_includes_strategy_in_prompt -v
```

預期：PASSED

- [ ] **Step 5: 跑全部測試確認沒有 regression**

```bash
.venv/bin/pytest tests/ -q
```

預期：全部通過

- [ ] **Step 6: Commit**

```bash
git add orchestrator/generate.py tests/test_generate.py
git commit -m "feat: inject strategy.md into generate prompt, add 電子報CTA option"
```

---

## Task 4：建立 `strategy_agent.py`

**Files:**
- Create: `orchestrator/strategy_agent.py`
- Create: `tests/test_strategy_agent.py`

- [ ] **Step 1: 寫失敗測試**

建立 `tests/test_strategy_agent.py`：

```python
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


def test_load_recent_experiments_filters_by_date():
    from orchestrator.strategy_agent import load_recent_experiments

    now = datetime.now(timezone.utc)
    recent = now.isoformat()
    old = (now - timedelta(days=10)).isoformat()

    experiments = [
        {"harvested_at": recent, "results": [], "analysis": "new"},
        {"harvested_at": old, "results": [], "analysis": "old"},
    ]

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        (data_dir / "experiments.json").write_text(json.dumps(experiments))

        with patch("orchestrator.strategy_agent.DATA_DIR", data_dir):
            result = load_recent_experiments(days=7)

    assert len(result) == 1
    assert result[0]["analysis"] == "new"


def test_run_writes_strategy_md():
    from orchestrator.strategy_agent import run

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# 本週流量策略\n## 目標\n導流電子報")]

    with tempfile.TemporaryDirectory() as tmp:
        prompts_dir = Path(tmp) / "prompts"
        prompts_dir.mkdir()
        data_dir = Path(tmp) / "data"
        data_dir.mkdir()
        (data_dir / "experiments.json").write_text("[]")

        with patch("orchestrator.strategy_agent.anthropic") as mock_anthropic, \
             patch("orchestrator.strategy_agent.DATA_DIR", data_dir), \
             patch("orchestrator.strategy_agent.PROMPTS_DIR", prompts_dir):

            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.Anthropic.return_value = mock_client

            run()

        strategy_path = prompts_dir / "strategy.md"
        assert strategy_path.exists()
        assert "本週流量策略" in strategy_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
.venv/bin/pytest tests/test_strategy_agent.py -v
```

預期：ImportError（模組不存在）

- [ ] **Step 3: 建立 strategy_agent.py**

建立 `orchestrator/strategy_agent.py`：

```python
"""Strategy Agent: 分析過去 7 天數據，更新 prompts/strategy.md"""
import json
import anthropic
from datetime import datetime, timezone, timedelta
from orchestrator.config import ANTHROPIC_API_KEY, DATA_DIR, PROMPTS_DIR


def load_recent_experiments(days: int = 7) -> list[dict]:
    path = DATA_DIR / "experiments.json"
    if not path.exists():
        return []
    experiments = json.loads(path.read_text(encoding="utf-8"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for exp in experiments:
        ts = exp.get("harvested_at", "")
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                recent.append(exp)
        except (ValueError, TypeError):
            pass
    return recent


def run() -> None:
    experiments = load_recent_experiments(days=7)
    resource = ""
    resource_path = PROMPTS_DIR / "resource.md"
    if resource_path.exists():
        resource = resource_path.read_text(encoding="utf-8")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    exp_summary = json.dumps(experiments, ensure_ascii=False, indent=2)

    prompt = f"""你是一個 Threads 內容策略師。分析過去 7 天的貼文數據，制定本週流量策略。

## 過去 7 天實驗數據
{exp_summary}

## 累積學習
{resource}

請制定本週策略，輸出以下格式的 Markdown（直接輸出，不要有前綴說明）：

# 本週流量策略（{date_str} 更新）

## 目標
[衝觸及 / 導流電子報（主題：XXX）] 以及原因（1-2 句）

## CTA 使用時機
當貼文主題涉及以下任一時加電子報 CTA：
- [主題 A]
- [主題 B]

## CTA 文案參考
- [範例 1]
- [範例 2]

## 本週不加 CTA 的主題
- [主題列表]"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    strategy = response.content[0].text.strip()
    (PROMPTS_DIR / "strategy.md").write_text(strategy, encoding="utf-8")
    print(f"[STRATEGY] strategy.md updated ({len(strategy)} chars)")


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: 執行測試確認通過**

```bash
.venv/bin/pytest tests/test_strategy_agent.py -v
```

預期：2 passed

- [ ] **Step 5: 跑全部測試**

```bash
.venv/bin/pytest tests/ -q
```

預期：全部通過

- [ ] **Step 6: Commit**

```bash
git add orchestrator/strategy_agent.py tests/test_strategy_agent.py
git commit -m "feat: add strategy_agent.py with 7-day analysis and strategy.md output"
```

---

## Task 5：建立 `newsletter_agent.py`

**Files:**
- Create: `orchestrator/newsletter_agent.py`
- Create: `tests/test_newsletter_agent.py`

- [ ] **Step 1: 寫失敗測試**

建立 `tests/test_newsletter_agent.py`：

```python
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


def test_run_saves_draft_file():
    from orchestrator.newsletter_agent import run

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# 電子報標題\n\n這是草稿內容")]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        (data_dir / "experiments.json").write_text("[]")
        (prompts_dir / "strategy.md").write_text("# 策略\n## 目標\n導流電子報")
        (prompts_dir / "swipe_file.md").write_text("# Swipe File\n範例貼文")

        with patch("orchestrator.newsletter_agent.anthropic") as mock_anthropic, \
             patch("orchestrator.newsletter_agent.DATA_DIR", data_dir), \
             patch("orchestrator.newsletter_agent.PROMPTS_DIR", prompts_dir), \
             patch("orchestrator.newsletter_agent.DRAFTS_DIR", drafts_dir), \
             patch("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "test@test.com"), \
             patch("orchestrator.newsletter_agent.subprocess.run") as mock_run:

            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.Anthropic.return_value = mock_client
            mock_run.return_value = MagicMock(returncode=0)

            run()

        draft_files = list(drafts_dir.glob("newsletter_*.md"))
        assert len(draft_files) == 1
        content = draft_files[0].read_text(encoding="utf-8")
        assert "電子報標題" in content


def test_run_sends_email():
    from orchestrator.newsletter_agent import run

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# 電子報\n草稿內容")]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        (data_dir / "experiments.json").write_text("[]")
        (prompts_dir / "strategy.md").write_text("# 策略")
        (prompts_dir / "swipe_file.md").write_text("")

        with patch("orchestrator.newsletter_agent.anthropic") as mock_anthropic, \
             patch("orchestrator.newsletter_agent.DATA_DIR", data_dir), \
             patch("orchestrator.newsletter_agent.PROMPTS_DIR", prompts_dir), \
             patch("orchestrator.newsletter_agent.DRAFTS_DIR", drafts_dir), \
             patch("orchestrator.newsletter_agent.NEWSLETTER_EMAIL", "test@test.com"), \
             patch("orchestrator.newsletter_agent.subprocess.run") as mock_run:

            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.Anthropic.return_value = mock_client
            mock_run.return_value = MagicMock(returncode=0)

            run()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0][0] == "mail"
        assert "test@test.com" in call_args[0][0]
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
.venv/bin/pytest tests/test_newsletter_agent.py -v
```

預期：ImportError（模組不存在）

- [ ] **Step 3: 建立 newsletter_agent.py**

建立 `orchestrator/newsletter_agent.py`：

```python
"""Newsletter Agent: 生成 Substack 草稿並 email 給作者"""
import json
import subprocess
import anthropic
from datetime import datetime, timezone, timedelta
from orchestrator.config import (
    ANTHROPIC_API_KEY, DATA_DIR, PROMPTS_DIR, DRAFTS_DIR, NEWSLETTER_EMAIL
)


def _load_recent_experiments(days: int = 7) -> list[dict]:
    path = DATA_DIR / "experiments.json"
    if not path.exists():
        return []
    experiments = json.loads(path.read_text(encoding="utf-8"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for exp in experiments:
        ts = exp.get("harvested_at", "")
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                recent.append(exp)
        except (ValueError, TypeError):
            pass
    return recent


def run() -> None:
    strategy = ""
    strategy_path = PROMPTS_DIR / "strategy.md"
    if strategy_path.exists():
        strategy = strategy_path.read_text(encoding="utf-8")

    swipe = ""
    swipe_path = PROMPTS_DIR / "swipe_file.md"
    if swipe_path.exists():
        swipe = swipe_path.read_text(encoding="utf-8")

    experiments = _load_recent_experiments(days=7)
    top_posts = sorted(
        [post for exp in experiments for post in exp.get("results", [])],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )[:5]
    top_summary = json.dumps(top_posts, ensure_ascii=False, indent=2)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    prompt = f"""你是一個 AI 電子報作者，為 Substack 電子報（hualeee.substack.com）撰寫本週內容。

## 本週 Threads 策略
{strategy}

## 高表現貼文範例庫
{swipe}

## 本週最佳表現貼文數據
{top_summary}

請撰寫一篇完整的電子報草稿：
- 是 Threads 最高互動主題的「深度版本」
- 繁體中文
- 格式：標題、引言、正文（3-5 個小節）、結語
- 字數：800-1200 字

只輸出電子報正文，不要額外說明。"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    draft = response.content[0].text.strip()

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = DRAFTS_DIR / f"newsletter_{date_str}.md"
    draft_path.write_text(draft, encoding="utf-8")
    print(f"[NEWSLETTER] Draft saved to {draft_path}")

    subject = f"[電子報草稿] {date_str}"
    body = f"本週 Top 5 貼文數據：\n{top_summary[:500]}\n\n---草稿---\n\n{draft}"
    result = subprocess.run(
        ["mail", "-s", subject, NEWSLETTER_EMAIL],
        input=body.encode("utf-8"),
        capture_output=True,
    )
    if result.returncode == 0:
        print(f"[NEWSLETTER] Email sent to {NEWSLETTER_EMAIL}")
    else:
        print(f"[NEWSLETTER] Email failed: {result.stderr.decode()}")


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: 執行測試確認通過**

```bash
.venv/bin/pytest tests/test_newsletter_agent.py -v
```

預期：2 passed

- [ ] **Step 5: 跑全部測試**

```bash
.venv/bin/pytest tests/ -q
```

預期：全部通過

- [ ] **Step 6: Commit**

```bash
git add orchestrator/newsletter_agent.py tests/test_newsletter_agent.py
git commit -m "feat: add newsletter_agent.py with draft generation and email delivery"
```

---

## Task 6：建立根目錄 `program.md`（Claude Code 操作手冊）

**Files:**
- Create: `program.md`

- [ ] **Step 1: 建立 program.md**

建立根目錄 `program.md`：

```markdown
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
```

- [ ] **Step 2: 確認 program.md 存在於根目錄**

```bash
ls -la program.md
wc -l program.md
```

預期：檔案存在，行數 > 50

- [ ] **Step 3: Commit**

```bash
git add program.md
git commit -m "feat: add root program.md as Claude Code instruction manual"
```

---

## Task 7：設定 crontab

**Files:**
- 無（修改系統 crontab）

- [ ] **Step 1: 備份現有 crontab**

```bash
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d).txt
cat /tmp/crontab_backup_$(date +%Y%m%d).txt
```

- [ ] **Step 2: 確認 claude CLI 路徑**

```bash
which claude
```

記下完整路徑（例如 `/usr/local/bin/claude`），下一步會用到。

- [ ] **Step 3: 編輯 crontab**

```bash
crontab -e
```

加入以下三行（把 `/usr/local/bin/claude` 替換成上一步查到的路徑）：

```bash
# autoresearch_threads - Content Agent
0 8,20 * * * cd /Users/hua/autoresearch_threads && /usr/local/bin/claude -p "讀 program.md，執行 Content Agent" >> logs/content-$(date +\%Y-\%m-\%d).log 2>&1

# autoresearch_threads - Strategy Agent (每週一 08:30)
30 8 * * 1 cd /Users/hua/autoresearch_threads && /usr/local/bin/claude -p "讀 program.md，執行 Strategy Agent" >> logs/strategy-$(date +\%Y-\%m-\%d).log 2>&1

# autoresearch_threads - Newsletter Agent (每週一 09:00)
0 9 * * 1 cd /Users/hua/autoresearch_threads && /usr/local/bin/claude -p "讀 program.md，執行 Newsletter Agent" >> logs/newsletter-$(date +\%Y-\%m-\%d).log 2>&1
```

> **注意**：如果原本有跑 `python -m orchestrator.main` 的 cron，這一步可以移除或 comment out，因為 Content Agent 會接管。

- [ ] **Step 4: 確認 crontab 已更新**

```bash
crontab -l | grep autoresearch
```

預期：看到三行新設定

- [ ] **Step 5: 手動測試 Content Agent 可以被 claude 執行**

```bash
cd /Users/hua/autoresearch_threads && claude -p "讀 program.md，列出三個 agent 的名稱即可，不要實際執行任何東西"
```

預期：Claude Code 輸出三個 agent 名稱，確認 claude CLI 可正常讀到 program.md

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: complete multi-agent monetization pipeline setup"
```
