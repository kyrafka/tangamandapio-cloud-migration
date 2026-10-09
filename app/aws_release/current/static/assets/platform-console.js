(() => {
  const roles = {
    customer: "Cliente B2B",
    sales: "Comercial",
    warehouse: "Operador WMS",
    operations: "Operaciones TI",
    admin: "Administrador",
    auditor: "Auditor",
  };
  const allowedRoles = ["customer", "sales", "warehouse", "operations", "admin", "auditor"];
  const $ = (selector) => document.querySelector(selector);
  const state = { csrf: "", role: "", window: 60, loading: false, inventory: [] };

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  async function request(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (options.body) headers.set("Content-Type", "application/json");
    if (state.csrf && options.method && options.method !== "GET") {
      headers.set("X-CSRF-Token", state.csrf);
    }
    const response = await fetch(path, {
      ...options,
      headers,
      credentials: "same-origin",
      cache: "no-store",
    });
    const payload = response.status === 204 ? null : await response.json().catch(() => ({}));
    if (!response.ok) {
      const errorCode = payload?.error || payload?.status;
      const message = {
        authentication_required: "La sesión terminó. Vuelve a iniciar sesión.",
        insufficient_role: "Tu rol no puede realizar esta acción.",
        cannot_remove_last_admin: "No se puede desactivar al último administrador activo.",
        cannot_remove_own_admin_access: "No puedes quitarte tu propio acceso de administrador.",
        use_self_service_password_change: "Usa el cambio de contraseña de tu propia cuenta.",
        not_configured: "La consulta a Azure no está configurada en este entorno.",
        unavailable: "Azure no está disponible ahora; el evento permanece en la cola de AWS.",
        azure_event_not_found: "Azure todavía no registra este evento.",
        event_not_found: "El evento ya no existe en la cola local.",
        invalid_demo_sku: "El SKU no pertenece al catálogo de laboratorio.",
        invalid_demo_quantity: "La cantidad debe ser un número entero entre 1 y 10.",
        insufficient_demo_stock: "No hay suficiente stock demo para esa cantidad.",
        azure_inventory_unavailable: "No se pudo consultar el inventario de Azure; no se creó el pedido.",
      }[errorCode] || errorCode || `Error ${response.status}`;
      throw new Error(message);
    }
    return payload;
  }

  function announce(message, tone = "error") {
    const alert = $("#platform-alert");
    alert.textContent = message;
    alert.dataset.tone = tone;
    alert.hidden = false;
    window.clearTimeout(announce.timer);
    announce.timer = window.setTimeout(() => { alert.hidden = true; }, 7000);
  }

  function formatted(value, unit = "", digits = 1) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "Sin datos";
    return `${new Intl.NumberFormat("es-PE", { maximumFractionDigits: digits }).format(value)}${unit}`;
  }

  function metric(cloudwatch, key) {
    return cloudwatch?.metrics?.[key] || null;
  }

  function latest(cloudwatch, key) {
    const item = metric(cloudwatch, key);
    return item && item.latest !== undefined ? item.latest : null;
  }

  function renderMetricTiles(cloudwatch) {
    const container = $("#cloud-metrics");
    container.replaceChildren();
    const definitions = [
      ["Solicitudes ALB", "alb_requests", (v) => formatted(v, "", 0), "Suma del último intervalo consultado"],
      ["Latencia p95", "alb_p95", (v) => formatted(Number(v) * 1000, " ms", 0), "Tiempo de respuesta del destino"],
      ["Errores 5xx", "alb_5xx", (v) => formatted(v, "", 0), "Errores producidos por la aplicación"],
      ["Destinos saludables", "alb_healthy", (v) => formatted(v, "", 0), "Instancias que reciben tráfico"],
      ["CPU de RDS", "rds_cpu", (v) => formatted(v, "%", 1), "Uso promedio de base de datos"],
      ["Conexiones RDS", "rds_connections", (v) => formatted(v, "", 0), "Conexiones concurrentes"],
      ["WAF bloqueadas", "waf_blocked", (v) => formatted(v, "", 0), "Solicitudes detenidas en el perímetro"],
      ["Instancias en servicio", "asg_in_service", (v) => formatted(v, "", 0), "Dato solo si existe un ASG asociado"],
    ];
    for (const [label, key, render, note] of definitions) {
      const data = metric(cloudwatch, key);
      const tile = element("article", "metric-tile");
      tile.append(element("small", "", label), element("strong", "", data ? render(data.latest) : "No configurado"));
      tile.append(element("span", "", data?.points?.length ? note : `${note} · sin serie reciente`));
      container.append(tile);
    }
  }

  function renderChart(target, first, second, firstLabel, secondLabel, firstScale = (v) => v) {
    const container = $(target);
    container.replaceChildren();
    const seriesA = first?.points || [];
    const seriesB = second?.points || [];
    if (!seriesA.length && !seriesB.length) {
      container.append(element("div", "chart-empty", "Aún no hay datos de CloudWatch para este recurso."));
      return;
    }
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 640 160");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", `${firstLabel}${secondLabel ? ` y ${secondLabel}` : ""}, últimos periodos`);
    for (const y of [24, 58, 92, 126]) {
      const line = document.createElementNS(svg.namespaceURI, "line");
      line.setAttribute("x1", "30"); line.setAttribute("x2", "630");
      line.setAttribute("y1", String(y)); line.setAttribute("y2", String(y));
      line.setAttribute("class", "chart-grid"); svg.append(line);
    }
    const pathFor = (points, scale) => {
      if (!points.length) return "";
      const normalized = points.slice(-60);
      const max = Math.max(1, ...normalized.map((point) => Math.max(0, scale(point.value))));
      return normalized.map((point, index) => {
        const x = 32 + (index / Math.max(1, normalized.length - 1)) * 592;
        const y = 128 - (Math.max(0, scale(point.value)) / max) * 104;
        return `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(" ");
    };
    for (const [points, scale, className, label] of [
      [seriesA, firstScale, "chart-line-primary", firstLabel],
      [seriesB, (value) => Number(value), "chart-line-secondary", secondLabel],
    ]) {
      if (!label || !points.length) continue;
      const path = document.createElementNS(svg.namespaceURI, "path");
      path.setAttribute("d", pathFor(points, scale)); path.setAttribute("class", className);
      path.setAttribute("aria-label", label); svg.append(path);
    }
    const legend = element("div", "chart-legend");
    if (seriesA.length) legend.append(element("span", "legend-primary", firstLabel));
    if (seriesB.length && secondLabel) legend.append(element("span", "legend-secondary", secondLabel));
    container.append(svg, legend);
  }

  function detailRow(label, value) {
    const row = element("div", "detail-row");
    row.append(element("span", "", label), element("strong", "", value));
    return row;
  }

  function setChip(selector, label, stateName) {
    const node = $(selector);
    node.textContent = label;
    node.dataset.state = stateName;
  }

  function renderOverview(data, azure) {
    const cw = data.cloudwatch || {};
    const source = $("#cloud-source");
    const sourceCopy = {
      ok: "Datos reales consultados desde CloudWatch.",
      partial: "CloudWatch respondió con series parciales; revisa el periodo y los recursos configurados.",
      no_data: "CloudWatch respondió, pero no hay puntos recientes para los recursos configurados.",
      not_configured: "CloudWatch todavía no tiene configurados los identificadores de recursos para esta aplicación.",
      access_denied: "El rol de la aplicación aún no tiene permisos de lectura de métricas CloudWatch.",
      unavailable: "CloudWatch no respondió. El portal y sus datos de negocio siguen separados de esta consulta.",
    }[cw.status] || "Estado de telemetría no disponible.";
    source.dataset.state = cw.status === "ok" ? "ok" : cw.status === "unavailable" || cw.status === "access_denied" ? "error" : "warning";
    source.lastElementChild.textContent = sourceCopy;
    renderMetricTiles(cw);
    renderChart("#traffic-chart", metric(cw, "alb_requests"), null, "Solicitudes", "");
    renderChart("#latency-chart", metric(cw, "alb_p95"), metric(cw, "alb_5xx"), "Latencia p95", "Errores 5xx", (value) => Number(value));
    $("#traffic-note").textContent = cw.status === "ok" ? `Ventana: ${cw.window_minutes} min. Los huecos representan periodos sin métricas publicadas, no tráfico inventado.` : sourceCopy;
    $("#latency-note").textContent = cw.status === "ok" ? "Cada línea muestra su propia tendencia; no compares sus alturas. La latencia p95 se presenta en milisegundos en la tarjeta." : "No se generan valores de ejemplo cuando el proveedor no entrega métricas.";

    const capacity = $("#capacity-details"); capacity.replaceChildren();
    const healthy = latest(cw, "alb_healthy");
    const unhealthy = latest(cw, "alb_unhealthy");
    const inService = latest(cw, "asg_in_service");
    const desired = latest(cw, "asg_desired");
    capacity.append(
      detailRow("Destinos saludables", healthy === null ? "Sin datos" : formatted(healthy, "", 0)),
      detailRow("Destinos no saludables", unhealthy === null ? "Sin datos" : formatted(unhealthy, "", 0)),
      detailRow("ASG · en servicio / deseadas", inService === null || desired === null ? "No configurado" : `${formatted(inService, "", 0)} / ${formatted(desired, "", 0)}`),
    );
    setChip("#capacity-state", healthy === null ? "Sin dato" : Number(healthy) > 0 ? "Tráfico con destinos" : "Sin destinos", healthy === null ? "warning" : Number(healthy) > 0 ? "ok" : "error");

    const database = $("#database-details"); database.replaceChildren();
    database.append(
      detailRow("Motor conectado", data.security.database === "postgresql" ? "PostgreSQL" : "SQLite · demo local"),
      detailRow("CPU actual", latest(cw, "rds_cpu") === null ? "Sin datos" : formatted(latest(cw, "rds_cpu"), "%", 1)),
      detailRow("Conexiones actuales", latest(cw, "rds_connections") === null ? "Sin datos" : formatted(latest(cw, "rds_connections"), "", 0)),
    );
    setChip("#database-state", data.security.database === "postgresql" ? "RDS" : "Demo", data.security.database === "postgresql" ? "ok" : "warning");

    const security = $("#security-details"); security.replaceChildren();
    security.append(
      detailRow("CSRF y roles", "Activos en backend"),
      detailRow("Cookie HttpOnly", data.security.session_cookie_httponly ? "Sí" : "No"),
      detailRow("Cookie Secure", data.security.session_cookie_secure ? "Sí" : "Pendiente de TLS propio"),
      detailRow("Solicitudes bloqueadas", latest(cw, "waf_blocked") === null ? "WAF sin métrica conectada" : formatted(latest(cw, "waf_blocked"), "", 0)),
      detailRow("Grabación de audio", data.security.recordings_enabled ? "Consentimiento requerido" : "Deshabilitada"),
    );
    const secure = data.security.session_cookie_secure;
    setChip("#security-state", secure ? "Controles activos" : "Revisión HTTPS", secure ? "ok" : "warning");

    const wmsDetails = $("#wms-details"); wmsDetails.replaceChildren();
    const wmsStatus = azure?.status || "unavailable";
    wmsDetails.append(
      detailRow("Servicio", azure?.provider || "Azure Function"),
      detailRow("Conectividad", wmsStatus === "connected" ? "Endpoint responde" : wmsStatus === "not_configured" ? "No configurado" : "Sin conexión"),
      detailRow("Modo de inventario", "Ledger ficticio · SKU demo con descuento idempotente"),
    );
    setChip("#wms-state", wmsStatus === "connected" ? "Conectado" : wmsStatus === "not_configured" ? "Demo local" : "Sin conexión", wmsStatus === "connected" ? "ok" : "warning");
  }

  function createSelect(label, value, options) {
    const select = document.createElement("select");
    select.setAttribute("aria-label", label);
    for (const [optionValue, optionText] of options) {
      const option = document.createElement("option");
      option.value = optionValue; option.textContent = optionText;
      option.selected = String(value) === String(optionValue);
      select.append(option);
    }
    return select;
  }

  function showTemporaryPassword(username, password) {
    const box = $("#temporary-password");
    box.replaceChildren();
    box.append(element("span", "", `Contraseña temporal para ${username} · se muestra solo ahora:`));
    box.append(element("code", "", password));
    const copy = element("button", "platform-button", "Copiar contraseña");
    copy.type = "button";
    copy.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(password); announce("Contraseña copiada. Entrégala por un canal seguro y pide que la cambien al iniciar.", "success"); }
      catch { announce("No se pudo acceder al portapapeles; selecciona y copia el valor visible."); }
    });
    box.append(copy); box.hidden = false;
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderUsers(users, companies) {
    const body = $("#users-table-body");
    body.replaceChildren();
    $("#users-empty").hidden = users.length > 0;
    const companyOptions = companies.map((company) => [company.id, company.name]);
    for (const user of users) {
      const row = document.createElement("tr");
      const identity = document.createElement("td");
      identity.append(element("strong", "", user.username), element("small", "", `${roles[user.role] || user.role}${user.must_change_password ? " · cambio de clave pendiente" : ""}`));
      const roleCell = document.createElement("td");
      const role = createSelect(`Rol de ${user.username}`, user.role, allowedRoles.map((key) => [key, roles[key]])); roleCell.append(role);
      const companyCell = document.createElement("td");
      const company = createSelect(`Empresa de ${user.username}`, user.company_id, companyOptions); companyCell.append(company);
      const statusCell = document.createElement("td");
      const statusLabel = element("label", "user-status");
      const active = document.createElement("input"); active.type = "checkbox"; active.checked = user.active; active.setAttribute("aria-label", `Cuenta activa: ${user.username}`);
      statusLabel.append(active, element("span", "", user.active ? "Activa" : "Desactivada"));
      active.addEventListener("change", () => { statusLabel.lastElementChild.textContent = active.checked ? "Activa" : "Desactivada"; });
      statusCell.append(statusLabel);
      const actions = document.createElement("td");
      const save = element("button", "", "Guardar cambios"); save.type = "button";
      save.addEventListener("click", async () => {
        save.disabled = true;
        try {
          await request(`/api/admin/users/${user.id}`, { method: "PATCH", body: JSON.stringify({ role: role.value, company_id: Number(company.value), active: active.checked }) });
          announce(`Se actualizaron los permisos de ${user.username}; sus sesiones anteriores fueron revocadas.`, "success");
          await refreshUsers();
        } catch (error) { announce(error.message); }
        finally { save.disabled = false; }
      });
      const reset = element("button", "", "Restablecer clave"); reset.type = "button";
      reset.disabled = user.id === state.currentUserId;
      reset.title = reset.disabled ? "Usa el cambio de contraseña de tu cuenta" : "Emite una contraseña temporal de un solo uso";
      reset.addEventListener("click", async () => {
        if (!window.confirm(`¿Emitir una contraseña temporal para ${user.username}? La sesión existente se revocará.`)) return;
        reset.disabled = true;
        try {
          const result = await request(`/api/admin/users/${user.id}/reset-password`, { method: "POST", body: "{}" });
          showTemporaryPassword(user.username, result.temporary_password);
          announce(`Se emitió una contraseña temporal para ${user.username}.`, "success");
        } catch (error) { announce(error.message); }
        finally { reset.disabled = false; }
      });
      actions.append(save, reset);
      row.append(identity, roleCell, companyCell, statusCell, actions);
      body.append(row);
    }
  }

  async function refreshUsers() {
    const [users, companies] = await Promise.all([request("/api/admin/users"), request("/api/admin/companies")]);
    renderUsers(users, companies);
  }

  function renderOutbox(events) {
    const body = $("#outbox-table-body");
    body.replaceChildren();
    $("#outbox-empty").hidden = events.length > 0;
    for (const event of events) {
      const row = document.createElement("tr");
      const identity = document.createElement("td");
      identity.append(element("strong", "", event.event_id), element("small", "", `Pedido #${event.order_id} · ${event.created_at || "fecha no disponible"}`));
      const delivery = document.createElement("td");
      delivery.append(element("strong", "", event.status || "desconocido"), element("small", "", `${Number(event.attempts) || 0} intento(s)${event.delivered_at ? ` · entregado ${event.delivered_at}` : ""}`));
      const result = document.createElement("td");
      result.append(element("span", "fulfillment-result", "Sin consultar"));
      const actions = document.createElement("td");
      const check = element("button", "", "Consultar Azure");
      check.type = "button";
      check.addEventListener("click", async () => {
        check.disabled = true;
        result.replaceChildren(element("span", "fulfillment-result", "Consultando…"));
        try {
          const payload = await request(`/api/outbox/${encodeURIComponent(event.event_id)}/fulfillment-status`);
          const label = payload.simulated ? `${payload.fulfillment_status} · DEMO` : payload.fulfillment_status;
          result.replaceChildren(element("strong", "", label));
          if (payload.note) result.append(element("small", "", payload.note));
          announce(payload.simulated ? "Azure actualizó el inventario ficticio de laboratorio; no representa existencias de un ERP real." : "Se consultó el estado final del evento en Azure.", payload.simulated ? "warning" : "success");
        } catch (error) {
          result.replaceChildren(element("span", "fulfillment-result", error.message));
        } finally { check.disabled = false; }
      });
      actions.append(check);
      if (["admin", "operations"].includes(state.role) && event.status !== "delivered") {
        const retry = element("button", "", "Reintentar entrega");
        retry.type = "button";
        retry.addEventListener("click", async () => {
          if (!window.confirm(`¿Reintentar ahora el envío del evento ${event.event_id} al WMS?`)) return;
          retry.disabled = true;
          try {
            const payload = await request(`/api/outbox/${encodeURIComponent(event.event_id)}/retry`, { method: "POST", body: "{}" });
            announce(`Reintento solicitado: ${payload.status || "respuesta recibida"}.`, "success");
            await refreshOutbox();
          } catch (error) { announce(error.message); }
          finally { retry.disabled = false; }
        });
        actions.append(retry);
      }
      row.append(identity, delivery, result, actions);
      body.append(row);
    }
  }

  async function refreshOutbox() {
    renderOutbox(await request("/api/outbox"));
  }

  function renderInventory(inventory) {
    state.inventory = Array.isArray(inventory.items) ? inventory.items : [];
    const body = $("#wms-inventory-body");
    const select = $("#wms-demo-sku");
    body.replaceChildren();
    select.replaceChildren();
    for (const item of state.inventory) {
      const row = document.createElement("tr");
      row.append(
        element("td", "", item.name),
        element("td", "", item.sku),
        element("td", "", new Intl.NumberFormat("es-PE").format(item.on_hand)),
        element("td", "", new Intl.NumberFormat("es-PE", { style: "currency", currency: item.currency || "PEN" }).format(item.unit_price)),
      );
      body.append(row);
      const option = document.createElement("option");
      option.value = item.sku;
      option.textContent = `${item.name} · ${item.on_hand} ${item.unit || "unid."}`;
      option.disabled = Number(item.on_hand) < 1;
      select.append(option);
    }
    const available = state.inventory.some((item) => Number(item.on_hand) > 0);
    const selectedItem = state.inventory.find((item) => item.sku === select.value);
    if (!selectedItem || Number(selectedItem.on_hand) < 1) {
      select.value = state.inventory.find((item) => Number(item.on_hand) > 0)?.sku || "";
    }
    const chip = $("#wms-inventory-state");
    chip.textContent = available ? "Stock demo" : "Sin existencias";
    chip.dataset.state = available ? "ok" : "warning";
    select.disabled = !available;
    $("#wms-demo-quantity").disabled = !available;
    $("#wms-demo-submit").disabled = !available;
    updateDemoProductNote();
  }

  function updateDemoProductNote() {
    const item = state.inventory.find((product) => product.sku === $("#wms-demo-sku").value);
    const quantity = $("#wms-demo-quantity");
    const max = Math.max(1, Math.min(10, Number(item?.on_hand) || 1));
    quantity.max = String(max);
    if (Number(quantity.value) > max) quantity.value = String(max);
    const note = $("#wms-demo-product-note");
    note.textContent = item
      ? `Precio de laboratorio: ${new Intl.NumberFormat("es-PE", { style: "currency", currency: item.currency || "PEN" }).format(item.unit_price)} por ${item.unit}. Máximo por pedido: ${max}.`
      : "El pedido aparecerá en el outbox después de generarlo.";
  }

  async function refreshInventory() {
    const button = $("#wms-inventory-refresh");
    button.disabled = true;
    try {
      const inventory = await request("/api/wms/inventory");
      renderInventory(inventory);
      return inventory;
    } catch (error) {
      const chip = $("#wms-inventory-state");
      chip.textContent = "Sin conexión";
      chip.dataset.state = "error";
      $("#wms-inventory-body").replaceChildren();
      $("#wms-demo-sku").replaceChildren(new Option("Inventario no disponible", ""));
      $("#wms-demo-sku").disabled = true;
      $("#wms-demo-quantity").disabled = true;
      $("#wms-demo-submit").disabled = true;
      announce(error.message, "warning");
      throw error;
    } finally { button.disabled = false; }
  }

  function showWmsResult(message, tone = "success") {
    const result = $("#wms-demo-result");
    result.textContent = message;
    result.dataset.tone = tone;
    result.hidden = false;
  }

  async function waitForWmsResult(eventId) {
    for (let attempt = 0; attempt < 7; attempt += 1) {
      if (attempt) await new Promise((resolve) => window.setTimeout(resolve, 1100));
      try {
        const result = await request(`/api/outbox/${encodeURIComponent(eventId)}/fulfillment-status`);
        if (result.fulfillment_status && result.fulfillment_status !== "pending") return result;
      } catch (error) {
        if (!/Azure todavía no registra este evento/i.test(error.message)) throw error;
      }
    }
    return null;
  }

  async function createDemoOrder(event) {
    event.preventDefault();
    const button = $("#wms-demo-submit");
    const sku = $("#wms-demo-sku").value;
    const quantity = Number($("#wms-demo-quantity").value);
    button.disabled = true;
    $("#wms-demo-result").hidden = true;
    try {
      const order = await request("/api/wms/demo-orders", {
        method: "POST",
        body: JSON.stringify({ sku, quantity }),
      });
      showWmsResult(`Pedido ${order.reference} guardado en AWS (S/ ${Number(order.total).toFixed(2)}). Evento ${order.event_id}: ${order.fulfillment?.status || "pendiente"}. Consultando Azure…`);
      await refreshOutbox();
      const outcome = await waitForWmsResult(order.event_id);
      if (!outcome) {
        showWmsResult(`Pedido ${order.reference} quedó durable en AWS. Azure aún lo procesa; actualiza el resultado en “Entregas al WMS”.`, "warning");
        return;
      }
      if (outcome.fulfillment_status === "demo_fulfillment_completed") {
        showWmsResult(`Pedido ${order.reference} procesado. Azure descontó ${quantity} unidad(es) de ${sku} del stock ficticio.`);
        await refreshInventory();
      } else {
        showWmsResult(`Pedido ${order.reference}: ${outcome.fulfillment_status}. ${outcome.note || "Revisa el detalle del evento."}`, "warning");
        await refreshInventory();
      }
    } catch (error) {
      showWmsResult(error.message, "error");
      announce(error.message);
    } finally {
      button.disabled = !state.inventory.some((item) => Number(item.on_hand) > 0);
    }
  }

  async function refresh() {
    if (state.loading) return;
    state.loading = true;
    $("#platform-refresh").disabled = true;
    try {
      const [data, azure] = await Promise.all([
        request(`/api/platform/overview?window=${state.window}`),
        fetch("/api/multicloud", { credentials: "same-origin", cache: "no-store" })
          .then((response) => response.json())
          .catch(() => ({ status: "unavailable" })),
      ]);
      renderOverview(data, azure);
      await refreshOutbox();
      await refreshInventory().catch(() => null);
      if (state.role === "admin") await refreshUsers();
      $("#updated-at").textContent = `Actualizado ${new Date().toLocaleString("es-PE", { dateStyle: "medium", timeStyle: "short" })}`;
    } catch (error) { announce(error.message); }
    finally { state.loading = false; $("#platform-refresh").disabled = false; }
  }

  async function start() {
    try {
      const session = await request("/api/auth/session");
      state.csrf = session.csrf_token || "";
      if (!session.authenticated || !["admin", "operations"].includes(session.user?.role)) {
        window.location.replace("/"); return;
      }
      state.role = session.user.role;
      state.currentUserId = session.user.id;
      document.documentElement.dataset.theme = window.localStorage.getItem("tangamandapio-theme") || "light";
      $("#platform-identity").textContent = `${session.user.username} · ${roles[session.user.role]}`;
      $("#users-section").hidden = state.role !== "admin";
      for (const button of document.querySelectorAll("[data-window]")) {
        button.addEventListener("click", () => {
          state.window = Number(button.dataset.window);
          for (const sibling of document.querySelectorAll("[data-window]")) sibling.setAttribute("aria-pressed", sibling === button ? "true" : "false");
          refresh();
        });
      }
      $("#platform-refresh").addEventListener("click", refresh);
      $("#outbox-refresh").addEventListener("click", () => refreshOutbox().catch((error) => announce(error.message)));
      $("#wms-inventory-refresh").addEventListener("click", () => refreshInventory().catch(() => null));
      $("#wms-demo-sku").addEventListener("change", updateDemoProductNote);
      $("#wms-demo-quantity").addEventListener("input", updateDemoProductNote);
      $("#wms-demo-form").addEventListener("submit", createDemoOrder);
      $("#users-refresh").addEventListener("click", () => refreshUsers().catch((error) => announce(error.message)));
      await refresh();
    } catch (error) {
      announce(error.message);
      if (/sesión terminó/i.test(error.message)) window.setTimeout(() => window.location.replace("/"), 1200);
    }
  }

  start();
})();
