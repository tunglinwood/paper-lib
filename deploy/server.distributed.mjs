/**
 * Bun dev server — distributed deployment variant
 * Serves static files with HMR, proxies /api/* to REMOTE backend.
 *
 * Usage:
 *   API_TARGET=http://backend-server:9000 bun run --hot server.distributed.mjs
 *
 * Or set API_TARGET in your environment:
 *   export API_TARGET=http://backend-server:9000
 *   bun run --hot server.distributed.mjs
 */

// ─── Configuration ─────────────────────────────────────────────
// Backend API server URL — CHANGE THIS to your backend address
const API_TARGET = Bun.env.API_TARGET || "http://127.0.0.1:9000";
const PORT = parseInt(Bun.env.PORT || "5173", 10);

// ─── MIME Types ────────────────────────────────────────────────
const MIME_TYPES = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "application/javascript",
  ".json": "application/json",
  ".pdf": "application/pdf",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".eot": "application/vnd.ms-fontobject",
};

// ─── CORS Headers (for development only — nginx handles this in production) ───
const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

// ─── Server ────────────────────────────────────────────────────
const server = Bun.serve({
  port: PORT,
  hostname: "0.0.0.0",

  async fetch(req) {
    const url = new URL(req.url);

    // Handle CORS preflight
    if (req.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    // ─── Proxy paper HTML files to backend ───
    // (Only if not serving them locally)
    if (url.pathname.startsWith("/papers/") && Bun.env.PROXY_PAPERS === "1") {
      const target = `${API_TARGET}${url.pathname}${url.search}`;
      try {
        return await fetch(target, {
          method: req.method,
          headers: req.headers,
        });
      } catch (err) {
        console.error(`[PROXY ERROR] ${url.pathname}:`, err.message);
        return new Response("Backend unavailable", { status: 502 });
      }
    }

    // ─── Proxy API requests to backend ───
    if (url.pathname.startsWith("/api/")) {
      const target = `${API_TARGET}${url.pathname}${url.search}`;
      try {
        const response = await fetch(target, {
          method: req.method,
          headers: req.headers,
          body: req.method !== "GET" && req.method !== "HEAD" ? req.body : undefined,
          duplex: req.method !== "GET" && req.method !== "HEAD" ? "half" : undefined,
        });

        // Add CORS headers to API responses
        const newHeaders = new Headers(response.headers);
        for (const [key, value] of Object.entries(CORS_HEADERS)) {
          newHeaders.set(key, value);
        }

        return new Response(response.body, {
          status: response.status,
          statusText: response.statusText,
          headers: newHeaders,
        });
      } catch (err) {
        console.error(`[API PROXY ERROR] ${url.pathname}:`, err.message);
        return new Response(
          JSON.stringify({ error: "Backend unavailable", detail: err.message }),
          { status: 502, headers: { "Content-Type": "application/json", ...CORS_HEADERS } }
        );
      }
    }

    // ─── Serve admin app at /admin or /admin/ ───
    if (url.pathname === "/admin" || url.pathname === "/admin/") {
      const adminFile = Bun.file("./admin.html");
      if (await adminFile.exists()) {
        return new Response(adminFile, { headers: { "Content-Type": "text/html" } });
      }
    }

    // ─── Redirect old /admin.html bookmark to /admin ───
    if (url.pathname === "/admin.html") {
      return new Response(null, {
        status: 301,
        headers: { Location: "/admin" },
      });
    }

    // ─── Serve login app at /login or /login/ ───
    if (url.pathname === "/login" || url.pathname === "/login/") {
      const loginFile = Bun.file("./login.html");
      if (await loginFile.exists()) {
        return new Response(loginFile, { headers: { "Content-Type": "text/html" } });
      }
    }

    // ─── Redirect old /login.html bookmark to /login ───
    if (url.pathname === "/login.html") {
      return new Response(null, {
        status: 301,
        headers: { Location: "/login" },
      });
    }

    // ─── Serve static files from project root ───
    const filePath = "." + url.pathname;
    const file = Bun.file(filePath);
    if (await file.exists()) {
      const ext = filePath.slice(filePath.lastIndexOf("."));
      const contentType = MIME_TYPES[ext] || "application/octet-stream";
      return new Response(file, { headers: { "Content-Type": contentType } });
    }

    // ─── Fallback: serve index.html for SPA-like routing ───
    const index = Bun.file("./index.html");
    if (await index.exists()) {
      return new Response(index, { headers: { "Content-Type": "text/html" } });
    }

    return new Response("Not Found", { status: 404 });
  },

  development: Bun.argv.includes("--hot"),
});

console.log(`\n📚 Paper Library Frontend Server`);
console.log(`   Local:    http://localhost:${PORT}`);
console.log(`   Network:  http://0.0.0.0:${PORT}`);
console.log(`   Backend:  ${API_TARGET}`);
if (Bun.env.PROXY_PAPERS === "1") {
  console.log(`   Papers:   proxied to backend`);
} else {
  console.log(`   Papers:   served locally from ./papers/`);
}
console.log(`   HMR:      ${Bun.argv.includes("--hot") ? "enabled" : "disabled"}\n`);
