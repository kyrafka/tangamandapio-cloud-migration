import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const readAsset = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

for (const [path, field, validValue, invalidValue] of [
  ["../static/admin/index.html", "slug", "distribuidor-norte", "Distribuidor Norte"],
  ["../static/assets/erp.js", "sku", "ABC-123_4", "ABC+123"],
  ["../../../web/src/main.jsx", "slug", "cliente-b2b", "cliente/b2b"],
]) {
  test(`${path} uses a valid HTML pattern for ${field}`, () => {
    const source = readAsset(path);
    const candidates = [...source.matchAll(/pattern="([^"]+)"/g)];
    assert.equal(candidates.length, 1);
    const expression = new RegExp(`^(?:${candidates[0][1]})$`, "v");
    assert.equal(expression.test(validValue), true);
    assert.equal(expression.test(invalidValue), false);
  });
}

const adminSource = readAsset("../static/assets/admin-console.js");

for (const [formId, endpoint] of [
  ["user-form", "/api/admin/users"],
  ["company-form", "/api/admin/companies"],
  ["alert-form", "/api/admin/alarm-subscriptions"],
]) {
  test(`${formId} resets and refreshes after the submit event has finished`, async () => {
    const prefix = `$("#${formId}").addEventListener("submit", `;
    const offset = adminSource.indexOf(prefix);
    assert.notEqual(offset, -1);
    const start = offset + prefix.length;
    const end = adminSource.indexOf("\n      });", start);
    assert.notEqual(end, -1);
    let resets = 0;
    let refreshes = 0;
    const notices = [];
    const form = { querySelector: () => ({}), reset: () => { resets += 1; } };
    const event = { currentTarget: form, preventDefault() {} };
    const refresh = () => { refreshes += 1; };
    const handler = vm.runInNewContext(`(${adminSource.slice(start, end + 8)})`, {
      FormData: class { get() { return "1"; } },
      api: async (url, options) => {
        if (options?.method === "POST") assert.equal(url, endpoint);
        return {};
      },
      notice: (...args) => notices.push(args),
      setBusy() {},
      loadUsers: refresh,
      loadAlerts: refresh,
      renderCompanies: refresh,
      fillCompanyOptions() {},
      state: {},
      $() {},
    });
    const submission = handler(event);
    event.currentTarget = null;
    await submission;
    assert.equal(notices[0]?.[1], undefined, notices[0]?.[0]);
    assert.equal(resets, 1);
    assert.equal(refreshes, 1);
  });
}
