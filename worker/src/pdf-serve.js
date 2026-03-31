/**
 * Serve PDF from R2 and track download count.
 * Route: GET /lazy-packs/:keyword.pdf
 */
export async function handlePdfDownload(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;
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

  if (stats.events.length > 200) {
    stats.events = stats.events.slice(-200);
  }

  await env.BUCKET.put(statsKey, JSON.stringify(stats));
}
