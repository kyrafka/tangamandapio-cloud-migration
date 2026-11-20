const readMethods = new Set(["GET", "HEAD", "OPTIONS"]);

export function createPortalApi(messages, fetcher = globalThis.fetch.bind(globalThis)) {
  let csrfToken = "";
  let sessionRequest;

  async function request(path, options = {}) {
    if (!path.startsWith("/api/") || path.includes("\\")) {
      throw new TypeError("El destino debe ser una ruta de la API del portal.");
    }

    const { includeMeta = false, ...fetchOptions } = options;
    const method = (fetchOptions.method || "GET").toUpperCase();
    const writes = !readMethods.has(method);
    if (writes && !csrfToken) {
      sessionRequest ??= request("/api/auth/session").finally(() => { sessionRequest = undefined; });
      await sessionRequest;
    }

    const headers = new Headers(fetchOptions.headers);
    headers.set("Accept", "application/json");
    if (fetchOptions.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    if (writes && csrfToken) headers.set("X-CSRF-Token", csrfToken);

    const response = await fetcher(path, {
      ...fetchOptions, method, headers, credentials: "same-origin", cache: "no-store",
    });
    const payload = response.status === 204 ? null : await response.json().catch(() => ({}));
    if (!response.ok) {
      const code = payload?.error || payload?.status || `HTTP ${response.status}`;
      const label = Object.hasOwn(messages, code) ? messages[code] : code;
      throw Object.assign(new Error(label), { status: response.status, code });
    }
    if (payload?.csrf_token) csrfToken = payload.csrf_token;
    if (path === "/api/auth/logout") csrfToken = "";
    return includeMeta ? { payload, headers: response.headers } : payload;
  }

  return request;
}
