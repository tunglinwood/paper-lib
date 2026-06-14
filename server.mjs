/**
 * Bun dev server — serves static files with HMR, proxies /api/* to backend.
 */
const API_TARGET = "http://127.0.0.1:9000";
const PORT = parseInt(Bun.env.PORT || "5173", 10);

const MIME_TYPES = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "text/javascript",
  ".json": "application/json",
  ".pdf": "application/pdf",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

const server = Bun.serve({
  port: PORT,
  hostname: "0.0.0.0",

  async fetch(req) {
    const url = new URL(req.url);

    // Proxy paper HTML files to backend
    if (url.pathname.startsWith("/papers/")) {
      const target = `${API_TARGET}${url.pathname}${url.search}`;
      return fetch(target, {
        method: req.method,
        headers: req.headers,
      });
    }

    // Proxy API requests to backend
    if (url.pathname.startsWith("/api/")) {
      const target = `${API_TARGET}${url.pathname}${url.search}`;
      return fetch(target, {
        method: req.method,
        headers: req.headers,
        body: req.body,
        duplex: "half",
      });
    }

    // Serve admin app at /admin or /admin/
    if (url.pathname === "/admin" || url.pathname === "/admin/") {
      const adminFile = Bun.file("./admin.html");
      if (await adminFile.exists()) {
        return new Response(adminFile, { headers: { "Content-Type": "text/html" } });
      }
    }

    // Redirect old /admin.html bookmark to /admin
    if (url.pathname === "/admin.html") {
      return new Response(null, {
        status: 301,
        headers: { Location: "/admin" },
      });
    }

    // Serve static files from project root
    const filePath = "." + url.pathname;
    const file = Bun.file(filePath);
    if (await file.exists()) {
      const ext = filePath.slice(filePath.lastIndexOf("."));
      const contentType = MIME_TYPES[ext] || "application/octet-stream";
      return new Response(file, { headers: { "Content-Type": contentType } });
    }

    // Fallback: try index.html for SPA-like routing
    const index = Bun.file("./index.html");
    if (await index.exists()) {
      return new Response(index, { headers: { "Content-Type": "text/html" } });
    }

    return new Response("Not Found", { status: 404 });
  },

  development: Bun.argv.includes("--hot"),
});

console.log(`Frontend dev server running on http://0.0.0.0:${PORT}`);
