/* Minimal static file server for local preview. Usage: node dev-server.js [--port N] [--host H] */
"use strict";
const http = require("http");
const fs = require("fs");
const path = require("path");

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i !== -1 && process.argv[i + 1]) return process.argv[i + 1];
  const eq = process.argv.find((a) => a.startsWith(name + "="));
  return eq ? eq.split("=")[1] : fallback;
}
const port = Number(arg("--port", process.env.PORT || 7100));
const host = arg("--host", process.env.HOST || "127.0.0.1");
const root = __dirname;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
};

http.createServer((req, res) => {
  let urlPath = decodeURIComponent(req.url.split("?")[0]);

  if (urlPath.startsWith("/api/kalshi/")) {
    const kalshiPath = urlPath.slice("/api/kalshi/".length);
    const targetUrl = `https://api.elections.kalshi.com/trade-api/v2/${kalshiPath}`;
    fetch(targetUrl, { headers: { "User-Agent": "RatesDecisions/1.0" } })
      .then((r) => r.text())
      .then((body) => {
        res.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-store",
        });
        res.end(body);
      })
      .catch((err) => {
        res.writeHead(502, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: err.message }));
      });
    return;
  }

  if (urlPath === "/") urlPath = "/index.html";
  const file = path.normalize(path.join(root, urlPath));
  if (!file.startsWith(root)) { res.writeHead(403); res.end(); return; }
  fs.readFile(file, (err, buf) => {
    if (err) { res.writeHead(404); res.end("not found"); return; }
    res.writeHead(200, {
      "Content-Type": MIME[path.extname(file)] || "application/octet-stream",
      "Cache-Control": "no-store",
    });
    res.end(buf);
  });
}).listen(port, host, () => {
  console.log(`Rates_decisions preview → http://${host}:${port}/`);
});
