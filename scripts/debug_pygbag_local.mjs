import http from "node:http";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import playwright from "file:///C:/Users/alvin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.js";

const root = path.resolve("web/river_crossing/build/web");
const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".png": "image/png",
  ".apk": "application/octet-stream",
  ".gz": "application/gzip",
};

const server = http.createServer(async (request, response) => {
  try {
    const urlPath = decodeURIComponent(new URL(request.url ?? "/", "http://127.0.0.1").pathname);
    const relativePath = urlPath === "/" ? "index.html" : urlPath.slice(1);
    const filePath = path.resolve(root, relativePath);
    if (!filePath.startsWith(root)) {
      response.writeHead(403);
      response.end("Forbidden");
      return;
    }

    const content = await fs.readFile(filePath);
    response.writeHead(200, {
      "Content-Type": mimeTypes[path.extname(filePath)] ?? "application/octet-stream",
    });
    response.end(content);
  } catch (error) {
    response.writeHead(404);
    response.end(String(error));
  }
});

await new Promise((resolve) => server.listen(8030, "127.0.0.1", resolve));

const { chromium } = playwright;
const browser = await chromium.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true,
});
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
const messages = [];
page.on("console", (message) => messages.push(`${message.type()}: ${message.text()}`));
page.on("pageerror", (error) => messages.push(`pageerror: ${error.message}`));
page.on("requestfailed", (request) => messages.push(`requestfailed: ${request.url()} ${request.failure()?.errorText}`));

await page.goto("http://127.0.0.1:8030/index.html?-i", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(15000);
await page.mouse.click(640, 360);
await page.waitForTimeout(60000);

const snapshot = await page.evaluate(() => ({
  title: document.title,
  bodyText: document.body.innerText,
  canvasCount: document.querySelectorAll("canvas").length,
  canvasVisible: [...document.querySelectorAll("canvas")].map((canvas) => ({
    width: canvas.width,
    height: canvas.height,
    style: canvas.getAttribute("style"),
  })),
}));

console.log(JSON.stringify({ snapshot, messages }, null, 2));
await page.screenshot({ path: "web/river_crossing/build/debug-page.png", fullPage: true });
await browser.close();
server.close();
