// Scroll-position screenshots through the DevTools protocol, for effects that
// a plain `chrome --screenshot` cannot show (it always captures the top).
//   node tools/cdp_shots.mjs URL OUT_PREFIX WIDTH HEIGHT DPR y1 y2 ...
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, out, W, H, DPR, ...ys] = process.argv.slice(2);
const chrome = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const port = 9333;
const proc = spawn(chrome, ["--headless=new", "--no-sandbox", "--hide-scrollbars", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "cdp-"))}`, "about:blank"], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws;
for (let i = 0; i < 50 && !ws; i++) {
  try {
    const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
    const page = list.find((t) => t.type === "page");
    if (page) ws = new WebSocket(page.webSocketDebuggerUrl);
  } catch { await sleep(200); }
}
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;

await send("Emulation.setDeviceMetricsOverride", { width: +W, height: +H, deviceScaleFactor: +DPR, mobile: +W < 760 });
// this machine has Windows animations off, which the site honours; the
// shots need the effect on
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "no-preference" }] });
await send("Page.enable");
await send("Page.navigate", { url });
await sleep(2500);
await ev("document.documentElement.style.scrollBehavior='auto';document.querySelectorAll('.reveal').forEach(e=>e.classList.add('is-in'));1");
console.log("canvases:", await ev("[...document.querySelectorAll('canvas.spill')].map(c=>c.className+' '+c.width+'x'+c.height).join(' | ') || 'none'"),
  "webgl2:", await ev("!!document.createElement('canvas').getContext('webgl2')"),
  "reduce:", await ev("matchMedia('(prefers-reduced-motion: reduce)').matches"));
for (const y of ys) {
  await ev(`window.scrollTo(0, ${y === "max" ? "document.documentElement.scrollHeight" : y}); 1`);
  await sleep(+(process.env.WAIT || 1300));
  const real = await ev("Math.round(scrollY)");
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(`${out}_${y}.png`, Buffer.from(shot.result.data, "base64"));
  console.log("shot", y, "scrollY", real);
}
if (process.env.EVAL) console.log("eval:", JSON.stringify(await ev(process.env.EVAL)));
ws.close();
proc.kill();
process.exit(0);
