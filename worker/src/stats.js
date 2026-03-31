/**
 * Stats API for lazy pack analytics.
 * Route: GET /api/stats/:keyword  — per-pack download stats
 * Route: GET /api/stats/line      — LINE follow + keyword events summary
 */
export async function handleStats(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;

  if (path === "/api/stats/line") {
    return getLineStats(env);
  }

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
