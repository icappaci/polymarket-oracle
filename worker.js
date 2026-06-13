/**
 * Cloudflare Worker — Polymarket Oracle endpoint
 *
 * Serves a signed JSON snapshot of Polymarket markets and top wallets.
 * The snapshot is rebuilt and pushed to GitHub every minute by a cron job
 * (see DEPLOY.md). This worker fetches the latest version from GitHub raw
 * and caches it at the edge for 30 seconds.
 *
 * Deploy:
 *   wrangler login
 *   wrangler deploy
 *
 * Free tier limits:
 *   - 100,000 requests/day
 *   - 10ms CPU/request
 *   - 1MB response
 */

// Public raw URL of the signed snapshot — updated every minute by the cron.
const SNAPSHOT_URL = "https://raw.githubusercontent.com/icappaci/polymarket-oracle/main/public/snapshot.json";

// Edge cache window: don't re-fetch GitHub more often than this.
const CACHE_TTL = 30;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: corsHeaders(),
      });
    }

    if (url.pathname === "/snapshot.json" || url.pathname === "/") {
      return handleSnapshot(request, ctx);
    }

    if (url.pathname === "/health") {
      return jsonResponse({
        status: "ok",
        endpoint: "polymarket-oracle-mvp",
        upstream: SNAPSHOT_URL,
        ts_unix: Math.floor(Date.now() / 1000),
      });
    }

    return jsonResponse({
      error: "not_found",
      paths: ["/", "/snapshot.json", "/health"],
    }, 404);
  },
};

async function handleSnapshot(request, ctx) {
  // Use Cloudflare's built-in edge cache
  const cacheKey = new Request(SNAPSHOT_URL, { method: "GET" });
  const cache = caches.default;

  let response = await cache.match(cacheKey);
  if (!response) {
    const upstream = await fetch(SNAPSHOT_URL, {
      cf: { cacheTtl: CACHE_TTL, cacheEverything: true },
    });
    if (!upstream.ok) {
      return jsonResponse({
        error: "upstream_unavailable",
        status: upstream.status,
      }, 502);
    }
    const body = await upstream.text();
    response = new Response(body, {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": `public, max-age=${CACHE_TTL}`,
        ...corsHeaders(),
        "x-cache": "MISS",
      },
    });
    ctx.waitUntil(cache.put(cacheKey, response.clone()));
  } else {
    response = new Response(response.body, response);
    response.headers.set("x-cache", "HIT");
  }
  return response;
}

function corsHeaders() {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET, OPTIONS",
    "access-control-max-age": "86400",
  };
}

function jsonResponse(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...corsHeaders(),
    },
  });
}
