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
