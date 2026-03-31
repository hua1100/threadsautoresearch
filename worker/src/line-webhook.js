/**
 * LINE Messaging API webhook handler.
 * Route: POST /line/webhook
 */
export async function handleLineWebhook(request, env) {
  const body = await request.text();

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

  const indexObj = await env.BUCKET.get("lazy-packs/index.json");
  let packs = [];
  if (indexObj) {
    try {
      packs = await indexObj.json();
    } catch {
      packs = [];
    }
  }

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

  if (events.length > 1000) {
    events = events.slice(-1000);
  }

  await env.BUCKET.put(key, JSON.stringify(events));
}
