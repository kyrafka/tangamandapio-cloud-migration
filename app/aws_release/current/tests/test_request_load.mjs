import assert from "node:assert/strict";
import { test } from "node:test";
import { runRequestLoad } from "../static/assets/request-load.mjs";

test("stops immediately on rate limiting and sticks to the portal endpoint", async (t) => {
  const paths = [];
  t.mock.method(globalThis, "fetch", async (path, options) => {
    paths.push([path, options.cache, options.credentials]);
    return new Response(null, { status: 429 });
  });
  const result = await runRequestLoad({ rate: 5, seconds: 3 });
  assert.deepEqual(paths, [["/api", "no-store", "omit"]]);
  assert.deepEqual([result.sent, result.failed, result.reason], [1, 1, "limited"]);
});

test("reports the responses it received and stops sending when cancelled", async (t) => {
  const stop = new AbortController();
  t.mock.method(globalThis, "fetch", async () => new Response(null, { status: 200 }));
  setTimeout(() => stop.abort(), 500);
  const result = await runRequestLoad({ rate: 8, seconds: 3, signal: stop.signal });
  assert.ok(result.sent > 0 && result.sent <= 4);
  assert.equal(result.succeeded, result.sent);
  assert.equal(result.reason, "stopped");
});

test("rejects settings above the rate or time limit even outside the form", async () => {
  await assert.rejects(runRequestLoad({ rate: 116, seconds: 60 }), RangeError);
  await assert.rejects(runRequestLoad({ rate: 115, seconds: 300 }), RangeError);
  await assert.rejects(runRequestLoad({ rate: 20, seconds: 301 }), RangeError);
});

test("allows the higher rate and keeps more than 24 requests in flight", async (t) => {
  const stop = new AbortController();
  let sent = 0;
  t.mock.method(globalThis, "fetch", async (_path, { signal }) => {
    sent++;
    if (sent === 30) queueMicrotask(() => stop.abort());
    return new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => reject(signal.reason), { once: true });
    });
  });
  const result = await runRequestLoad({ rate: 115, seconds: 1, signal: stop.signal });
  assert.equal(result.reason, "stopped");
  assert.ok(result.sent >= 30);
});
