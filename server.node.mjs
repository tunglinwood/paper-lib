/**
 * Node.js static file server for Paper Library frontend.
 * Proxies /api/* and /papers/* to the backend.
 *
 * Usage:
 *   API_TARGET=http://127.0.0.1:9000 PORT=5173 node server.node.mjs
 */

import http from "http";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const API_TARGET = process.env.API_TARGET || "http://127.0.0.1:9000";
const PORT = parseInt(process.env.PORT || "5173", 10);

const MIME_TYPES = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "application/javascript",
  ".mjs": "application/javascript",
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

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

function getTargetUrl(reqUrl) {
  const backendUrl = new URL(API_TARGET);
  backendUrl.pathname = reqUrl.pathname;
  backendUrl.search = reqUrl.search;
  return backendUrl.toString();
}

async function proxyToBackend(req, res, targetUrl) {
  const backendUrl = new URL(targetUrl);
  const options = {
    hostname: backendUrl.hostname,
    port: backendUrl.port || (backendUrl.protocol === "https:" ? 443 : 80),
    path: backendUrl.pathname + backendUrl.search,
    method: req.method,
    headers: { ...req.headers },
  };

  delete options.headers.host;
  options.headers.host = backendUrl.host;

  const client = backendUrl.protocol === "https:" ? await import("https") : http;

  return new Promise((resolve, reject) => {
    const proxyReq = client.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
      proxyRes.on("end", resolve);
    });

    proxyReq.on("error", (err) => {
      console.error(`[PROXY ERROR] ${req.url}:`, err.message);
      if (!res.headersSent) {
        res.writeHead(502, { "Content-Type": "application/json", ...CORS_HEADERS });
        res.end(JSON.stringify({ error: "Backend unavailable", detail: err.message }));
      }
      reject(err);
    });

    if (req.method !== "GET" && req.method !== "HEAD") {
      req.pipe(proxyReq);
    } else {
      proxyReq.end();
    }
  });
}

function serveFile(res, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || "application/octet-stream";

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain" });
      res.end("Not Found");
      return;
    }
    res.writeHead(200, { "Content-Type": contentType });
    res.end(data);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (req.method === "OPTIONS") {
    res.writeHead(204, CORS_HEADERS);
    res.end();
    return;
  }

  try {
    if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/papers/")) {
      await proxyToBackend(req, res, getTargetUrl(url));
      return;
    }

    if (url.pathname === "/admin" || url.pathname === "/admin/") {
      const adminFile = path.join(__dirname, "admin.html");
      if (fs.existsSync(adminFile)) {
        serveFile(res, adminFile);
        return;
      }
    }

    if (url.pathname === "/admin.html") {
      res.writeHead(301, { Location: "/admin" });
      res.end();
      return;
    }

    const filePath = path.join(__dirname, url.pathname === "/" ? "index.html" : url.pathname);
    const resolvedPath = path.resolve(filePath);
    const rootPath = path.resolve(__dirname);

    if (!resolvedPath.startsWith(rootPath)) {
      res.writeHead(403, { "Content-Type": "text/plain" });
      res.end("Forbidden");
      return;
    }

    if (fs.existsSync(resolvedPath) && fs.statSync(resolvedPath).isFile()) {
      serveFile(res, resolvedPath);
      return;
    }

    const indexFile = path.join(__dirname, "index.html");
    if (fs.existsSync(indexFile)) {
      serveFile(res, indexFile);
      return;
    }

    res.writeHead(404, { "Content-Type": "text/plain" });
    res.end("Not Found");
  } catch (err) {
    console.error(`[SERVER ERROR] ${req.url}:`, err.message);
    if (!res.headersSent) {
      res.writeHead(500, { "Content-Type": "text/plain" });
      res.end("Internal Server Error");
    }
  }
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`\n📚 Paper Library Frontend Server (Node.js)`);
  console.log(`   Local:    http://localhost:${PORT}`);
  console.log(`   Network:  http://0.0.0.0:${PORT}`);
  console.log(`   Backend:  ${API_TARGET}`);
  console.log(`   Root:     ${__dirname}\n`);
});
