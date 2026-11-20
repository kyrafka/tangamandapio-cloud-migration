import { createPortalApi } from "./portal-api.mjs";

(() => {
  const get = (id) => document.getElementById(id);
  const roleGuides = {
    customer: "Cliente B2B · Registra pedidos y consulta los de tu empresa.",
    sales: "Ventas · Registra pedidos y sigue las confirmaciones de almacén.",
    warehouse: "Almacén · Revisa pedidos pendientes, líneas y el resultado de inventario.",
    operations: "Operaciones TI · Revisa las colas y reintenta entregas pendientes.",
    auditor: "Auditoría · Consulta la secuencia y los eventos registrados.",
    admin: "Administración · Registra pedidos, supervisa las colas y recupera entregas.",
  };
  const messages = {
    received: "Pedido registrado", pending: "Pendiente de envío a almacén", queued: "Recibido por almacén · pendiente de procesar",
    processed: "Procesado por almacén", needs_items: "Requiere líneas de SKU y cantidad", review: "Requiere revisión",
  };
  const errors = {
    authentication_required: "Tu sesión terminó. Vuelve al portal para ingresar.",
    order_not_found: "El pedido no está disponible para tu cuenta.",
    insufficient_role: "Tu rol no permite esta acción.",
    invalid_order_items: "Revisa los SKU, elimina los duplicados y usa cantidades entre 1 y 1.000.",
  };
  let role, records = [], selected, detail, loadNumber = 0;

  function node(tag, value, className) {
    const element = document.createElement(tag);
    element.textContent = value;
    if (className) element.className = className;
    return element;
  }

  const request = createPortalApi(errors);

  function announce(message, error = false) {
    get("notice").hidden = false;
    get("notice").dataset.error = String(error);
    get("notice").textContent = message;
  }

  function formatDate(time) {
    const date = new Date(time || "");
    return Number.isNaN(date.valueOf()) ? "Sin hora registrada" : new Intl.DateTimeFormat("es-PE", { dateStyle: "short", timeStyle: "short" }).format(date);
  }

  function renderList() {
    const search = get("search").value.trim().toLocaleLowerCase();
    const container = get("order-list");
    const filtered = records.filter((record) => [record.id, record.reference, record.customer].map((value) => value ?? "").join(" ").toLocaleLowerCase().includes(search));
    container.replaceChildren();
    for (const order of filtered) {
      const button = node("button", order.reference || `Pedido #${order.id}`);
      button.type = "button";
      button.setAttribute("aria-current", String(selected === order.id));
      button.append(node("small", `${order.customer} · ${formatDate(order.created_at)}`));
      button.addEventListener("click", () => loadOrder(order.id));
      container.append(button);
    }
    if (filtered.length === 0) container.append(node("p", search ? "Sin resultados para esta búsqueda." : "Aún no hay pedidos."));
  }

  async function refreshList() {
    get("order-list").setAttribute("aria-busy", "true");
    try {
      records = await request("/api/orders");
      renderList();
    } finally {
      get("order-list").setAttribute("aria-busy", "false");
    }
  }

  function renderOrder(record) {
    const container = get("order-detail");
    const flow = node("ol", "", "flow");
    const reached = record.stage === "processed" ? 3 : record.queued_at || ["queued", "needs_items"].includes(record.stage) ? 2 : 1;
    const steps = [
      ["Pedido registrado", formatDate(record.order.created_at)],
      ["Entrega a almacén", record.queued_at ? formatDate(record.queued_at) : reached >= 2 ? "Recibido" : "Pendiente"],
      ["Resultado de almacén", record.processed_at ? formatDate(record.processed_at) : "Pendiente de confirmación"],
    ];
    steps.forEach(([title, description], index) => {
      const step = node("li", "");
      if (index < reached) step.dataset.state = "complete";
      if (index === Math.min(2, reached)) step.setAttribute("aria-current", "step");
      step.append(node("strong", title), node("small", description));
      flow.append(step);
    });
    const title = `${record.order.reference || `Pedido #${record.order.id}`} · ${messages[record.stage]}`;
    const result = node("p", title, "result");
    result.dataset.state = record.stage;
    container.replaceChildren(result, node("p", record.order.customer), flow);
    if (record.verification === "unavailable") container.append(node("p", "Almacén no respondió. Se conserva la última etapa registrada por el portal."));
    if (record.simulated) container.append(node("p", "Resultado del inventario de demostración."));
    if (record.items.length) {
      const items = node("ul", "");
      for (const item of record.items) items.append(node("li", `${item.sku} · ${item.quantity} unidades`));
      container.append(items);
    }
    if (record.technical) {
      const technical = node("details", "", "technical");
      const signal = record.technical;
      technical.append(node("summary", "Registro técnico"), node("p", `Evento ${signal.event_id} · ${signal.attempts} intento(s)`));
      if (signal.last_error) technical.append(node("p", `Último error: ${signal.last_error}`));
      if (signal.wms_status) technical.append(node("p", `Resultado WMS: ${signal.wms_status}`));
      container.append(technical);
    }
    get("verify").hidden = !record.actions.verify;
    get("retry").hidden = !record.actions.retry;
    get("detail-actions").hidden = !record.actions.verify && !record.actions.retry;
  }

  async function loadOrder(id, verify = false) {
    const sequence = ++loadNumber;
    selected = id;
    if (!verify) detail = null;
    const url = new URL(location.href);
    url.searchParams.set("pedido", id);
    history.replaceState(null, "", url);
    for (const button of [get("verify"), get("retry")]) button.disabled = true;
    if (!verify) get("order-detail").replaceChildren(node("p", "Consultando pedido…"));
    renderList();
    try {
      const record = await request(`/api/orders/${id}/tracking${verify ? "?verify=1" : ""}`);
      if (sequence !== loadNumber) return;
      detail = record;
      renderOrder(record);
    } catch (error) {
      if (sequence !== loadNumber) return;
      if (!verify) get("detail-actions").hidden = true;
      announce(error.message, true);
    } finally {
      if (sequence === loadNumber) for (const button of [get("verify"), get("retry")]) button.disabled = false;
    }
  }

  function addLine() {
    const lines = get("order-lines");
    if (lines.children.length >= 20) return;
    const line = get("line-template").content.cloneNode(true);
    line.querySelector(".remove-line").addEventListener("click", (event) => {
      if (lines.children.length <= 1) return;
      event.currentTarget.closest(".line").remove();
      get("add-line").disabled = false;
      get("add-line").focus();
    });
    lines.append(line);
    get("add-line").disabled = lines.children.length >= 20;
  }

  async function saveOrder(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const items = data.getAll("sku").map((sku, index) => ({ sku, quantity: Number(data.getAll("quantity")[index]) }));
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      const created = await request("/api/orders", { method: "POST", body: JSON.stringify({ customer: data.get("customer"), reference: data.get("reference"), total: Number(data.get("total")), items }) });
      form.reset();
      get("order-lines").replaceChildren();
      addLine();
      get("new-order").open = false;
      announce(`Pedido #${created.id} registrado. Puedes seguir su avance aquí.`);
      await refreshList();
      await loadOrder(created.id);
    } catch (error) { announce(error.message, true); }
    finally { button.disabled = false; }
  }

  async function queueHealth() {
    const button = get("check-health");
    button.disabled = true;
    try {
      const result = await request("/api/platform/fulfillment-health");
      const fallback = "Sin lectura";
      const lines = [
        `Outbox AWS · ${result.outbox.pending} pendientes · ${result.outbox.exhausted} agotaron sus intentos`,
        result.outbox.oldest ? `Pedido más antiguo en espera · ${formatDate(result.outbox.oldest)}` : "Outbox al día",
        `Azure · ${result.azure_queue.pending ?? fallback} en cola · ${result.azure_queue.poison ?? fallback} en cola de fallidos`,
        `Consulta ${formatDate(result.checked_at)}`,
      ];
      get("health-details").replaceChildren(...lines.map((text) => node("p", text)));
    } catch (error) { announce(error.message, true); }
    finally { button.disabled = false; }
  }

  async function init() {
    const theme = localStorage.getItem("tangamandapio-theme");
    const prefersDark = matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = theme === "dark" || (!theme && prefersDark) ? "dark" : "light";
    const session = await request("/api/auth/session");
    role = session.user?.role;
    if (!session.authenticated || !roleGuides[role]) { location.replace("/"); return; }
    const operator = ["operations", "admin"].includes(role);
    get("role-summary").textContent = roleGuides[role];
    get("health").hidden = !operator;
    get("operations-link").hidden = !operator;
    get("new-order").hidden = !["customer", "sales", "admin"].includes(role);
    get("search").addEventListener("input", renderList);
    get("refresh-list").addEventListener("click", () => refreshList().catch((error) => announce(error.message, true)));
    get("verify").addEventListener("click", () => loadOrder(selected, true));
    get("retry").addEventListener("click", async () => {
      const eventId = detail?.technical?.event_id;
      const orderId = selected;
      if (!eventId || !detail.actions.retry || !confirm("¿Reintentar el envío de este pedido a almacén?")) return;
      get("retry").disabled = true;
      try {
        await request(`/api/outbox/${encodeURIComponent(eventId)}/retry`, { method: "POST", body: "{}" });
        if (orderId === selected) await loadOrder(orderId);
        announce("Intento registrado.");
      } catch (error) { announce(error.message, true); }
      finally { get("retry").disabled = false; }
    });
    get("check-health").addEventListener("click", queueHealth);
    get("add-line").addEventListener("click", () => { addLine(); get("order-lines").lastElementChild.querySelector("input").focus(); });
    get("order-form").addEventListener("submit", saveOrder);
    addLine();
    await refreshList();
    const requested = Number(new URLSearchParams(location.search).get("pedido"));
    if (Number.isSafeInteger(requested) && requested > 0) await loadOrder(requested);
    else if (records.length) await loadOrder(records[0].id);
  }

  init().catch((error) => announce(error.message, true));
})();
