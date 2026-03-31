# Lazy Pack Worker (Cloudflare R2 + Worker) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy a Cloudflare Worker + R2 bucket that serves as LINE webhook, PDF download proxy with tracking, and stats API for the lazy pack system.

**Architecture:** A single Cloudflare Worker handles three routes: `POST /line/webhook` (LINE Messaging API events), `GET /lazy-packs/:keyword.pdf` (PDF serving + download count), `GET /api/stats/:keyword` (download/claim stats). R2 bucket stores PDFs, an index file, and analytics data.

**Tech Stack:** Cloudflare Workers (JavaScript/Wrangler), Cloudflare R2, LINE Messaging API

**Spec:** `docs/superpowers/specs/2026-03-31-lazy-pack-design.md`

**Prerequisite:** User must have a Cloudflare account and `wrangler` CLI installed. Run `npm install -g wrangler && wrangler login` before starting.

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `worker/wrangler.toml` | Worker + R2 binding config |
| Create | `worker/src/index.js` | Main Worker: router for all routes |
| Create | `worker/src/line-webhook.js` | LINE webhook handler (signature verify, keyword match, follow events) |
| Create | `worker/src/pdf-serve.js` | PDF download proxy with counter |
| Create | `worker/src/stats.js` | Stats API endpoint |
| Create | `worker/package.json` | Node project config |

---

### Task 1: Scaffold Worker project + R2 bucket

**Files:**
- Create: `worker/package.json`
- Create: `worker/wrangler.toml`

- [ ] **Step 1: Create worker directory and package.json**

```bash
mkdir -p worker/src
```

Create `worker/package.json`:

```json
{
  "name": "lazy-pack-worker",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "wrangler dev",
    "deploy": "wrangler deploy"
  },
  "devDependencies": {
    "wrangler": "^4.0.0"
  }
}
```

- [ ] **Step 2: Create wrangler.toml**

Create `worker/wrangler.toml`:

```toml
name = "lazy-pack-worker"
main = "src/index.js"
compatibility_date = "2026-03-31"

[[r2_buckets]]
binding = "BUCKET"
bucket_name = "lazy-packs"

[vars]
WORKER_BASE_URL = "https://lazy-pack-worker.<your-subdomain>.workers.dev"
```

- [ ] **Step 3: Create R2 bucket**

```bash
cd worker && npx wrangler r2 bucket create lazy-packs
```

Expected: `Created bucket 'lazy-packs'`

- [ ] **Step 4: Set LINE secrets**

```bash
npx wrangler secret put LINE_CHANNEL_SECRET
npx wrangler secret put LINE_CHANNEL_ACCESS_TOKEN
```

Enter the values when prompted.

- [ ] **Step 5: Install dependencies**

```bash
npm install
```

- [ ] **Step 6: Commit**

```bash
cd .. && git add worker/
git commit -m "chore: scaffold Cloudflare Worker project with R2 binding"
```

---

### Task 2: PDF serving + download tracking

**Files:**
- Create: `worker/src/pdf-serve.js`
- Create: `worker/src/index.js` (initial router)

- [ ] **Step 1: Create pdf-serve.js**

Create `worker/src/pdf-serve.js`:

```javascript
/**
 * Serve PDF from R2 and track download count.
 * Route: GET /lazy-packs/:keyword.pdf
 */
export async function handlePdfDownload(request, env) {
  const url = new URL(request.url);
  const path = url.pathname; // e.g. /lazy-packs/ai-agent.pdf
  const match = path.match(/^\/lazy-packs\/([a-z0-9-]+)\.pdf$/);

  if (!match) {
    return new Response("Not found", { status: 404 });
  }

  const keyword = match[1];
  const key = `lazy-packs/${keyword}.pdf`;

  const object = await env.BUCKET.get(key);
  if (!object) {
    return new Response("PDF not found", { status: 404 });
  }

  // Track download asynchronously (don't block response)
  const ctx = request.ctx || {};
  const trackPromise = trackDownload(env, keyword);
  if (ctx.waitUntil) {
    ctx.waitUntil(trackPromise);
  }

  return new Response(object.body, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `inline; filename="${keyword}.pdf"`,
      "Cache-Control": "public, max-age=3600",
    },
  });
}

async function trackDownload(env, keyword) {
  const statsKey = `analytics/downloads/${keyword}.json`;
  const existing = await env.BUCKET.get(statsKey);

  let stats = { downloads: 0, events: [] };
  if (existing) {
    try {
      stats = await existing.json();
    } catch {
      // corrupted, reset
    }
  }

  stats.downloads += 1;
  stats.events.push({
    timestamp: new Date().toISOString(),
  });

  // Keep only last 200 events to avoid unbounded growth
  if (stats.events.length > 200) {
    stats.events = stats.events.slice(-200);
  }

  await env.BUCKET.put(statsKey, JSON.stringify(stats));
}
```

- [ ] **Step 2: Create index.js with router**

Create `worker/src/index.js`:

```javascript
import { handlePdfDownload } from "./pdf-serve.js";

export default {
  async fetch(request, env, ctx) {
    // Attach ctx to request for waitUntil
    request.ctx = ctx;

    const url = new URL(request.url);
    const path = url.pathname;

    // PDF download: GET /lazy-packs/:keyword.pdf
    if (request.method === "GET" && path.startsWith("/lazy-packs/") && path.endsWith(".pdf")) {
      return handlePdfDownload(request, env);
    }

    return new Response("Not found", { status: 404 });
  },
};
```

- [ ] **Step 3: Test locally**

```bash
cd worker && npx wrangler dev
```

In another terminal:
```bash
curl -i http://localhost:8787/lazy-packs/test.pdf
```

Expected: `404` (no PDF uploaded yet, but router works)

- [ ] **Step 4: Commit**

```bash
cd .. && git add worker/src/
git commit -m "feat: add PDF serving with download tracking in Worker"
```

---

### Task 3: LINE webhook handler

**Files:**
- Create: `worker/src/line-webhook.js`
- Modify: `worker/src/index.js`

- [ ] **Step 1: Create line-webhook.js**

Create `worker/src/line-webhook.js`:

```javascript
/**
 * LINE Messaging API webhook handler.
 * Route: POST /line/webhook
 *
 * Handles:
 * - follow events: record new friend
 * - message events: match keyword → reply with PDF link
 */

export async function handleLineWebhook(request, env) {
  const body = await request.text();

  // Verify LINE signature
  const signature = request.headers.get("x-line-signature");
  if (!signature) {
    return new Response("Missing signature", { status: 401 });
  }

  const isValid = await verifySignature(body, signature, env.LINE_CHANNEL_SECRET);
  if (!isValid) {
    return new Response("Invalid signature", { status: 401 });
  }

  const data = JSON.parse(body);
  const events = data.events || [];

  for (const event of events) {
    if (event.type === "follow") {
      await handleFollow(event, env);
    } else if (event.type === "message" && event.message.type === "text") {
      await handleMessage(event, env);
    }
  }

  return new Response("OK", { status: 200 });
}

async function verifySignature(body, signature, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(body));
  const expected = btoa(String.fromCharCode(...new Uint8Array(sig)));
  return expected === signature;
}

async function handleFollow(event, env) {
  const userId = event.source.userId;
  await appendAnalytics(env, {
    type: "follow",
    user_id: userId,
    timestamp: new Date(event.timestamp).toISOString(),
  });
}

async function handleMessage(event, env) {
  const text = event.message.text.trim().toLowerCase();
  const replyToken = event.replyToken;

  // Load index from R2
  const indexObj = await env.BUCKET.get("lazy-packs/index.json");
  let packs = [];
  if (indexObj) {
    try {
      packs = await indexObj.json();
    } catch {
      packs = [];
    }
  }

  // Match keyword
  const matched = packs.find(
    (p) => p.keyword.toLowerCase() === text
  );

  if (matched) {
    await replyToLine(env, replyToken, [
      {
        type: "text",
        text: `🎁 這是你的懶人包「${matched.title}」\n👉 ${matched.url}`,
      },
    ]);

    await appendAnalytics(env, {
      type: "keyword_match",
      keyword: matched.keyword,
      user_id: event.source.userId,
      timestamp: new Date(event.timestamp).toISOString(),
    });
  } else {
    // List available packs
    let replyText = "目前沒有符合的懶人包。";
    if (packs.length > 0) {
      const list = packs.map((p) => `・輸入「${p.keyword}」→ ${p.title}`).join("\n");
      replyText = `目前可領取的懶人包：\n${list}`;
    }
    await replyToLine(env, replyToken, [{ type: "text", text: replyText }]);
  }
}

async function replyToLine(env, replyToken, messages) {
  await fetch("https://api.line.me/v2/bot/message/reply", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${env.LINE_CHANNEL_ACCESS_TOKEN}`,
    },
    body: JSON.stringify({ replyToken, messages }),
  });
}

async function appendAnalytics(env, event) {
  const key = "analytics/line-events.json";
  const existing = await env.BUCKET.get(key);

  let events = [];
  if (existing) {
    try {
      events = await existing.json();
    } catch {
      events = [];
    }
  }

  events.push(event);

  // Keep last 1000 events
  if (events.length > 1000) {
    events = events.slice(-1000);
  }

  await env.BUCKET.put(key, JSON.stringify(events));
}
```

- [ ] **Step 2: Add LINE webhook route to index.js**

Update `worker/src/index.js`:

```javascript
import { handlePdfDownload } from "./pdf-serve.js";
import { handleLineWebhook } from "./line-webhook.js";

export default {
  async fetch(request, env, ctx) {
    request.ctx = ctx;

    const url = new URL(request.url);
    const path = url.pathname;

    // LINE webhook: POST /line/webhook
    if (request.method === "POST" && path === "/line/webhook") {
      return handleLineWebhook(request, env);
    }

    // PDF download: GET /lazy-packs/:keyword.pdf
    if (request.method === "GET" && path.startsWith("/lazy-packs/") && path.endsWith(".pdf")) {
      return handlePdfDownload(request, env);
    }

    return new Response("Not found", { status: 404 });
  },
};
```

- [ ] **Step 3: Commit**

```bash
cd .. && git add worker/src/
git commit -m "feat: add LINE webhook handler with keyword matching"
```

---

### Task 4: Stats API endpoint

**Files:**
- Create: `worker/src/stats.js`
- Modify: `worker/src/index.js`

- [ ] **Step 1: Create stats.js**

Create `worker/src/stats.js`:

```javascript
/**
 * Stats API for lazy pack analytics.
 * Route: GET /api/stats/:keyword  — per-pack download stats
 * Route: GET /api/stats/line      — LINE follow + keyword events summary
 */

export async function handleStats(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;

  // GET /api/stats/line — LINE event summary
  if (path === "/api/stats/line") {
    return getLineStats(env);
  }

  // GET /api/stats/:keyword — download stats for a specific pack
  const match = path.match(/^\/api\/stats\/([a-z0-9-]+)$/);
  if (match) {
    return getPackStats(env, match[1]);
  }

  return new Response("Not found", { status: 404 });
}

async function getPackStats(env, keyword) {
  const statsKey = `analytics/downloads/${keyword}.json`;
  const obj = await env.BUCKET.get(statsKey);

  if (!obj) {
    return Response.json({ keyword, downloads: 0, last_download: null });
  }

  const stats = await obj.json();
  const lastEvent = stats.events?.length > 0 ? stats.events[stats.events.length - 1] : null;

  return Response.json({
    keyword,
    downloads: stats.downloads || 0,
    last_download: lastEvent?.timestamp || null,
  });
}

async function getLineStats(env) {
  const key = "analytics/line-events.json";
  const obj = await env.BUCKET.get(key);

  if (!obj) {
    return Response.json({ follows: 0, keyword_matches: 0, by_keyword: {} });
  }

  const events = await obj.json();

  let follows = 0;
  const byKeyword = {};

  for (const e of events) {
    if (e.type === "follow") {
      follows++;
    } else if (e.type === "keyword_match") {
      const kw = e.keyword || "unknown";
      byKeyword[kw] = (byKeyword[kw] || 0) + 1;
    }
  }

  const totalMatches = Object.values(byKeyword).reduce((a, b) => a + b, 0);

  return Response.json({
    follows,
    keyword_matches: totalMatches,
    by_keyword: byKeyword,
  });
}
```

- [ ] **Step 2: Add stats routes to index.js**

Update `worker/src/index.js`:

```javascript
import { handlePdfDownload } from "./pdf-serve.js";
import { handleLineWebhook } from "./line-webhook.js";
import { handleStats } from "./stats.js";

export default {
  async fetch(request, env, ctx) {
    request.ctx = ctx;

    const url = new URL(request.url);
    const path = url.pathname;

    // LINE webhook: POST /line/webhook
    if (request.method === "POST" && path === "/line/webhook") {
      return handleLineWebhook(request, env);
    }

    // PDF download: GET /lazy-packs/:keyword.pdf
    if (request.method === "GET" && path.startsWith("/lazy-packs/") && path.endsWith(".pdf")) {
      return handlePdfDownload(request, env);
    }

    // Stats API: GET /api/stats/...
    if (request.method === "GET" && path.startsWith("/api/stats/")) {
      return handleStats(request, env);
    }

    return new Response("Not found", { status: 404 });
  },
};
```

- [ ] **Step 3: Commit**

```bash
cd .. && git add worker/src/
git commit -m "feat: add stats API for download and LINE analytics"
```

---

### Task 5: Deploy and configure LINE webhook

**Files:**
- No new files — deployment steps

- [ ] **Step 1: Deploy Worker**

```bash
cd worker && npx wrangler deploy
```

Expected: Deployed to `https://lazy-pack-worker.<subdomain>.workers.dev`

Note the URL — this is your `WORKER_BASE_URL`.

- [ ] **Step 2: Initialize empty index.json in R2**

```bash
echo '[]' > /tmp/index.json
npx wrangler r2 object put lazy-packs/lazy-packs/index.json --file /tmp/index.json --content-type application/json
```

- [ ] **Step 3: Configure LINE webhook URL**

Go to LINE Developers Console → your channel → Messaging API settings → Webhook URL:

Set to: `https://lazy-pack-worker.<subdomain>.workers.dev/line/webhook`

Enable "Use webhook".

- [ ] **Step 4: Verify webhook**

Click "Verify" in LINE console. Expected: success (200 OK).

- [ ] **Step 5: Test with a manual PDF upload**

Create a test PDF and upload:

```bash
echo "test" | npx wrangler r2 object put lazy-packs/lazy-packs/test.pdf --file /dev/stdin --content-type application/pdf
```

Update index:
```bash
echo '[{"keyword":"test","title":"測試懶人包","url":"https://lazy-pack-worker.<subdomain>.workers.dev/lazy-packs/test.pdf"}]' > /tmp/index.json
npx wrangler r2 object put lazy-packs/lazy-packs/index.json --file /tmp/index.json --content-type application/json
```

Now send "test" to your LINE bot — it should reply with the PDF link.

Verify download tracking:
```bash
curl https://lazy-pack-worker.<subdomain>.workers.dev/api/stats/test
```

Expected: `{"keyword":"test","downloads":0,"last_download":null}` (or 1 if you opened the PDF)

- [ ] **Step 6: Add WORKER_BASE_URL to .env**

Add to `/Users/hua/threadsautoresearch/.env`:

```
WORKER_BASE_URL=https://lazy-pack-worker.<subdomain>.workers.dev
```

- [ ] **Step 7: Clean up test data and commit**

```bash
npx wrangler r2 object delete lazy-packs/lazy-packs/test.pdf
echo '[]' > /tmp/index.json
npx wrangler r2 object put lazy-packs/lazy-packs/index.json --file /tmp/index.json --content-type application/json
```

```bash
cd .. && git add worker/ .env
git commit -m "feat: deploy lazy-pack Worker with LINE webhook and stats API"
```
