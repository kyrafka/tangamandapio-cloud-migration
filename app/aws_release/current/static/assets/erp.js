import { parseInventoryCsv } from "./catalogCsv.js";

(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = {
    csrf: "", user: null, access: { permissions: [], role_labels: {} }, section: "",
    overview: null, partners: [], products: [], sales: [], purchases: [], finance: [], users: [],
    mail: [], recipients: [], mailStatus: null, folder: "inbox", selectedMail: null, busy: false,
    catalogRows: [], catalogFileName: "", catalogError: "", catalogImporting: false,
  };
  const roleLabels = { customer: "Cliente", sales: "Comercial", warehouse: "Operaciones WMS", operations: "Operaciones TI", admin: "Administración", auditor: "Auditoría" };
  const money = new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" });
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  const pen = (value) => money.format(Number(value || 0));
  const date = (value) => value ? new Date(value).toLocaleString("es-PE") : "—";
  const has = (permission) => state.user?.role === "admin" || state.access.permissions?.includes(permission);

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (options.body) headers.set("Content-Type", "application/json");
    if (options.method && options.method !== "GET" && state.csrf) headers.set("X-CSRF-Token", state.csrf);
    const response = await fetch(path, { ...options, headers, credentials: "same-origin", cache: "no-store" });
    const payload = response.status === 204 ? null : await response.json().catch(() => ({}));
    if (!response.ok) {
      const errors = {
        authentication_required: "Tu sesión terminó. Vuelve a iniciar sesión en el portal.",
        insufficient_role: "Tu rol del portal no tiene acceso a esta acción.",
        erp_permission_required: "Tu administrador todavía no asignó ese permiso ERP.",
        internal_recipient_not_found: "La cuenta destinataria no está activa.",
        invalid_partner: "Revisa el tipo, razón social, identificador y correo del socio.",
        customer_required: "Elige un cliente antes de guardar el pedido.",
        supplier_required: "Elige un proveedor antes de guardar la orden.",
        product_not_found: "El SKU no está dado de alta en el catálogo ERP.",
        wms_unavailable_or_sku_missing: "Azure WMS no está disponible o no reconoce el SKU.",
        csrf_token_required: "La sesión cambió. Actualiza la página e inténtalo otra vez.",
      };
      throw new Error(errors[payload?.error] || payload?.error || `No se pudo completar la acción (${response.status}).`);
    }
    return payload;
  }

  function announce(message, tone = "error") {
    const alert = $("#erp-alert");
    alert.textContent = message;
    alert.dataset.tone = tone === "success" ? "ok" : tone;
    alert.hidden = false;
    clearTimeout(announce.timer);
    announce.timer = setTimeout(() => { alert.hidden = true; }, 6500);
  }

  function chip(value, tone = "") {
    return `<span class="erp-chip"${tone ? ` data-tone="${tone}"` : ""}>${esc(value)}</span>`;
  }

  function empty(text) { return `<div class="erp-empty">${esc(text)}</div>`; }
  function sectionHeading(kicker, title, copy = "", action = "") {
    return `<div class="erp-section-head"><div><p class="eyebrow">${esc(kicker)}</p><h2>${esc(title)}</h2>${copy ? `<p>${esc(copy)}</p>` : ""}</div>${action}</div>`;
  }

  const tabs = () => [
    ["overview", "Resumen", has("reports:read")],
    ["masters", "Maestros", has("master:read")],
    ["sales", "Ventas", has("sales:read")],
    ["purchases", "Compras", has("purchase:read")],
    ["finance", "Finanzas", has("finance:read")],
    ["access", "Accesos", state.user?.role === "admin"],
    ["mail", "Correo interno", true],
  ].filter((item) => item[2]);

  function renderTabs() {
    const unread = Number(state.overview?.unread_messages || 0);
    $("#erp-tabs").innerHTML = `${tabs().map(([key, label]) => `<button class="erp-tab" type="button" role="tab" aria-selected="${state.section === key}" data-action="section" data-section="${key}">${esc(label)}${key === "mail" && unread ? `<span class="tab-count">${unread}</span>` : ""}</button>`).join("")}<button class="erp-tab" type="button" data-action="refresh" ${state.busy ? "disabled" : ""}>${state.busy ? "Actualizando…" : "Actualizar"}</button>`;
  }

  async function loadSection(section = state.section) {
    state.busy = true;
    renderTabs();
    $("#erp-content").innerHTML = `<div class="erp-loading"><span class="erp-spinner" aria-hidden="true"></span> Cargando ${esc(section)}…</div>`;
    try {
      if (section === "overview") state.overview = await api("/api/erp/overview");
      if (section === "masters") {
        const [partners, productState] = await Promise.all([api("/api/erp/partners"), api("/api/erp/products")]);
        state.partners = partners; state.products = productState.products || []; state.wms = productState.wms;
      }
      if (section === "sales") {
        const [orders, partners, productState] = await Promise.all([api("/api/erp/sales/orders"), api("/api/erp/partners"), api("/api/erp/products")]);
        state.sales = orders; state.partners = partners; state.products = productState.products || []; state.wms = productState.wms;
      }
      if (section === "purchases") {
        const [orders, partners, productState] = await Promise.all([api("/api/erp/purchases/orders"), api("/api/erp/partners"), api("/api/erp/products")]);
        state.purchases = orders; state.partners = partners; state.products = productState.products || []; state.wms = productState.wms;
      }
      if (section === "finance") {
        const [docs, overview, partners] = await Promise.all([api("/api/erp/finance/documents"), api("/api/erp/overview"), api("/api/erp/partners")]);
        state.finance = docs; state.overview = overview; state.partners = partners;
      }
      if (section === "access") state.users = await api("/api/erp/users");
      if (section === "mail") await loadMail();
      renderSection();
    } catch (error) {
      $("#erp-content").innerHTML = `<section class="erp-card">${sectionHeading("No se pudo cargar", "Revisa tu acceso")}${empty(error.message)}<div class="erp-actions"><button class="erp-button" data-action="refresh" type="button">Reintentar</button><a class="erp-button" href="/">Volver al portal</a></div></section>`;
      announce(error.message);
    } finally {
      state.busy = false;
      renderTabs();
      updateWmsState();
    }
  }

  async function loadMail() {
    const [messages, recipients, mailStatus] = await Promise.all([
      api(`/api/erp/mail?folder=${state.folder}`), api("/api/erp/mail/users"), api("/api/erp/mail/status"),
    ]);
    state.mail = messages; state.recipients = recipients; state.mailStatus = mailStatus;
    if (state.selectedMail && !messages.some((item) => item.id === state.selectedMail.id)) state.selectedMail = null;
  }

  function updateWmsState() {
    const wms = state.wms || state.overview?.wms;
    const status = wms?.status || "consultando";
    const node = $("#erp-wms-state");
    node.dataset.state = status === "connected" ? "ok" : status === "consultando" ? "loading" : "error";
    const label = status === "connected" ? `Azure WMS · ${wms.mode === "demo-inventory-ledger" ? "demostración" : "conectado"}` : `Azure WMS · ${status}`;
    node.innerHTML = `<i class="status-dot"></i><span>${esc(label)}</span>`;
  }

  function renderSection() {
    renderTabs();
    const content = $("#erp-content");
    if (state.section === "overview") content.innerHTML = renderOverview();
    else if (state.section === "masters") content.innerHTML = renderMasters();
    else if (state.section === "sales") content.innerHTML = renderOrders("sales");
    else if (state.section === "purchases") content.innerHTML = renderOrders("purchases");
    else if (state.section === "finance") content.innerHTML = renderFinance();
    else if (state.section === "access") content.innerHTML = renderAccess();
    else if (state.section === "mail") content.innerHTML = renderMail();
    updateWmsState();
  }

  function renderOverview() {
    const m = state.overview?.metrics || {};
    const metrics = [
      has("sales:read") && `<article class="erp-kpi"><small>Pedidos de venta</small><strong>${m.sales_orders ?? "—"}</strong><span>Documentos ERP</span></article>`,
      has("purchase:read") && `<article class="erp-kpi"><small>Órdenes de compra</small><strong>${m.purchase_orders ?? "—"}</strong><span>Seguimiento de recepción</span></article>`,
      has("finance:read") && `<article class="erp-kpi"><small>Cuentas por cobrar</small><strong>${pen(m.open_receivables)}</strong><span>Saldo abierto en soles</span></article>`,
      has("finance:read") && `<article class="erp-kpi"><small>Cuentas por pagar</small><strong>${pen(m.open_payables)}</strong><span>Saldo abierto en soles</span></article>`,
    ].filter(Boolean).join("");
    return `<div class="erp-kpis">${metrics}</div><div class="erp-grid erp-grid--three">
      <section class="erp-card">${sectionHeading("Propiedad de datos", "El ERP coordina; Azure mantiene el inventario", "Pedidos, precios, socios y documentos financieros se guardan en la base administrada por AWS. Las existencias se consultan en Azure y no se duplican aquí.")}
        <p class="erp-note">${esc(state.overview?.wms?.note || "El inventario es un ledger ficticio de laboratorio. Las ventas y recepciones muestran el flujo técnico, no stock comercial real.")}</p>
      </section>
      <section class="erp-card">${sectionHeading("Mensajería", "Correo interno del portal", "Mensajes entre cuentas internas, con bandeja de entrada, enviados y confirmación de lectura.")}<button class="erp-button erp-button--primary" type="button" data-action="section" data-section="mail">Abrir buzón · ${Number(state.overview?.unread_messages || 0)} sin leer</button><p class="erp-note">No crea buzones de Internet ni envía por SMTP; todo queda privado dentro del portal.</p></section>
    </div>`;
  }

  function renderMasters() {
    const partners = state.partners.length ? `<div class="erp-table-wrap"><table class="erp-table"><thead><tr><th>Razón social</th><th>Tipo</th><th>RUC / ID</th><th>Contacto</th></tr></thead><tbody>${state.partners.map((p) => `<tr><td><strong>${esc(p.name)}</strong></td><td>${esc(p.kind)}</td><td>${esc(p.tax_id || "—")}</td><td>${esc(p.email || p.phone || "—")}</td></tr>`).join("")}</tbody></table></div>` : empty("Aún no hay clientes o proveedores.");
    const products = state.products.length ? `<div class="erp-table-wrap"><table class="erp-table"><thead><tr><th>SKU</th><th>Producto</th><th>Venta</th><th>Compra</th><th>Disponible en Azure</th></tr></thead><tbody>${state.products.map((p) => `<tr><td class="erp-mono">${esc(p.sku)}</td><td>${esc(p.name)}<small>${esc(p.unit)}</small></td><td>${pen(p.sale_price)}</td><td>${pen(p.purchase_cost)}</td><td>${p.on_hand == null ? "No disponible" : esc(p.on_hand)}</td></tr>`).join("")}</tbody></table></div>` : empty("El catálogo ERP empieza vacío.");
    const partnerForm = has("master:write") ? `<form class="erp-form" data-form="partner"><label>Tipo<select name="kind"><option value="customer">Cliente</option><option value="supplier">Proveedor</option><option value="both">Cliente y proveedor</option></select></label><label>Razón social<input name="name" maxlength="160" required /></label><label>RUC / identificador<input name="tax_id" maxlength="32" /></label><div class="erp-form-row"><label>Correo<input name="email" type="email" maxlength="254" /></label><label>Teléfono<input name="phone" maxlength="40" /></label></div><label>Dirección<input name="address" maxlength="240" /></label><button class="erp-button erp-button--primary" type="submit">Guardar socio</button></form>` : `<p class="erp-disabled">Tu rol tiene acceso de consulta, sin edición de maestros.</p>`;
    const productForm = has("master:write") ? `<form class="erp-form" data-form="product"><label>SKU<input name="sku" maxlength="40" pattern="[A-Za-z0-9_-]{3,40}" placeholder="SKU-..." required /></label><label>Nombre<input name="name" maxlength="180" required /></label><div class="erp-form-row"><label>Unidad<input name="unit" maxlength="32" value="unidad" required /></label><label>Precio de venta (S/) <input name="sale_price" type="number" min="0" max="1000000" step="0.01" required /></label></div><label>Costo de compra (S/)<input name="purchase_cost" type="number" min="0" max="1000000" step="0.01" required /></label><button class="erp-button erp-button--primary" type="submit">Guardar producto</button></form>` : "";
    const catalogImport = has("master:write") ? `<section class="erp-card catalog-import"><div><p class="eyebrow">Carga masiva · datos sintéticos</p><h2>Importar catálogo desde Excel</h2><p>Descarga la plantilla Excel, edítala y guárdala como CSV UTF-8 para cargarla. Se valida todo el archivo antes de sincronizarlo.</p><p class="erp-note">El saldo inicial solo se usa para SKU nuevos. Actualizar un SKU conserva su saldo actual.</p><a class="erp-button" href="/templates/plantilla_catalogo_sintetico.xlsx" download>Plantilla Excel</a> <a class="erp-button" href="/templates/inventario_sintetico.csv" download>Plantilla CSV</a></div><div class="catalog-import-controls"><label>Archivo CSV UTF-8<input id="erp-catalog-file" type="file" accept=".csv,text/csv" /></label>${state.catalogFileName && !state.catalogError ? `<small>${esc(state.catalogFileName)} · ${state.catalogRows.length} productos validados</small>` : ""}${state.catalogError ? `<p class="erp-alert" role="alert">${esc(state.catalogError)}</p>` : ""}${state.catalogRows.length ? `<div class="catalog-preview"><strong>Vista previa · ${state.catalogRows.length} filas</strong><span>${state.catalogRows.slice(0, 5).map((item) => `${esc(item.sku)} · ${item.initial_stock} iniciales`).join(" | ")}${state.catalogRows.length > 5 ? " · y más" : ""}</span></div><button class="erp-button erp-button--primary" type="button" data-action="import-catalog" ${state.catalogImporting ? "disabled" : ""}>${state.catalogImporting ? "Sincronizando…" : `Importar ${state.catalogRows.length} productos`}</button>` : ""}</div></section>` : "";
    return `<div class="erp-stack"><section class="erp-card">${sectionHeading("Relaciones comerciales", "Clientes y proveedores", "Maestros que usan Ventas y Compras.", chip(`${state.partners.length} socios`))}${partners}</section>
      ${has("master:write") ? `<div class="erp-grid"><section class="erp-card">${sectionHeading("Alta de socio", "Registrar un cliente o proveedor")}${partnerForm}</section><section class="erp-card">${sectionHeading("Catálogo comercial", "Dar de alta un SKU")}${productForm}</section></div>` : ""}
      ${catalogImport}
      <section class="erp-card">${sectionHeading("Catálogo comercial", "Productos y disponibilidad", "El precio/costo pertenece al ERP; el saldo solo se lee desde Azure WMS.", chip(`${state.products.length} productos`))}${products}<p class="erp-note">${esc(state.wms?.note || "Crear un SKU aquí no lo crea en Azure. El catálogo del WMS debe reconocer el SKU antes de vender o recibir.")}</p></section></div>`;
  }

  async function handleCatalogFile(event) {
    if (event.target.id !== "erp-catalog-file") return;
    const file = event.target.files?.[0];
    state.catalogRows = []; state.catalogError = ""; state.catalogFileName = file?.name || "";
    if (!file) return renderSection();
    if (file.size > 1_000_000) state.catalogError = "El archivo supera el límite de 1 MB.";
    else {
      try { state.catalogRows = parseInventoryCsv(await file.text()); }
      catch (error) { state.catalogError = error.message; }
    }
    renderSection();
  }

  function eligiblePartners(type) {
    const kinds = type === "sales" ? ["customer", "both"] : ["supplier", "both"];
    return state.partners.filter((p) => p.active && kinds.includes(p.kind));
  }

  function orderForm(type) {
    const sales = type === "sales";
    const partners = eligiblePartners(type);
    const products = state.products.filter((p) => p.active);
    if (!has(sales ? "sales:write" : "purchase:write")) return `<p class="erp-note">Este perfil puede consultar el flujo, pero no crear documentos.</p>`;
    if (!partners.length) return `<p class="erp-note">Registra primero un ${sales ? "cliente" : "proveedor"} en Maestros.</p>`;
    const options = products.map((p) => `<option value="${esc(p.sku)}">${esc(p.name)} · ${esc(p.sku)}${p.on_hand == null ? "" : ` · ${esc(p.on_hand)} disp.`}</option>`).join("");
    return `<form class="erp-form" data-form="order" data-type="${type}"><label>${sales ? "Cliente" : "Proveedor"}<select name="partner_id" required><option value="">Selecciona una empresa</option>${partners.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join("")}</select></label><div class="erp-section-head"><div><p class="eyebrow">Detalle</p><h3>Productos</h3></div><button class="erp-button erp-button--quiet" type="button" data-action="add-line">Añadir línea</button></div><div class="erp-lines">${orderLine(options)}</div><p class="erp-note">${sales ? "Azure validará el stock disponible." : "Al recibir la mercadería, registra la recepción para enviar el evento al WMS."} Los movimientos actuales son de demostración.</p><button class="erp-button erp-button--primary" type="submit" ${products.length ? "" : "disabled"}>${sales ? "Registrar y enviar al WMS" : "Emitir orden de compra"}</button></form>`;
  }

  function orderLine(options) {
    return `<div class="erp-line"><label>SKU<select name="sku" required><option value="">Selecciona</option>${options}</select></label><label>Cantidad<input name="quantity" type="number" min="1" max="1000" step="1" value="1" required /></label><button class="erp-button erp-button--quiet" data-action="remove-line" type="button" aria-label="Quitar línea">×</button></div>`;
  }

  function renderOrderRows(type) {
    const orders = type === "sales" ? state.sales : state.purchases;
    if (!orders.length) return empty(`Todavía no hay ${type === "sales" ? "ventas" : "órdenes de compra"}.`);
    return `<div class="erp-table-wrap"><table class="erp-table"><thead><tr><th>Documento</th><th>${type === "sales" ? "Cliente" : "Proveedor"}</th><th>Detalle</th><th>Estado WMS</th><th>Total</th><th>Acción</th></tr></thead><tbody>${orders.map((o) => {
      const lines = (o.items || []).map((item) => `${esc(item.sku)} × ${esc(item.quantity)}`).join(", ");
      const tone = /completed|received/.test(o.status) ? "ok" : /rejected/.test(o.status) ? "bad" : "warn";
      const action = type === "sales"
        ? (!["completed_demo", "completed", "rejected"].includes(o.status) ? `<button class="erp-button" type="button" data-action="refresh-order" data-type="sales" data-id="${o.id}">Consultar Azure</button>` : "—")
        : o.status === "ordered" ? `<button class="erp-button" type="button" data-action="receive-purchase" data-id="${o.id}">Registrar recepción</button>` : o.status === "receipt_pending" ? `<button class="erp-button" type="button" data-action="refresh-order" data-type="purchases" data-id="${o.id}">Consultar Azure</button>` : "—";
      return `<tr><td><strong>${esc(o.reference)}</strong><small>${date(o.created_at)}</small></td><td>${esc(o.partner_name)}</td><td>${lines || "—"}</td><td>${chip(o.status, tone)}</td><td>${pen(o.total)}</td><td>${action}</td></tr>`;
    }).join("")}</tbody></table></div>`;
  }

  function renderOrders(type) {
    const sales = type === "sales";
    return `<div class="erp-grid"><section class="erp-card">${sectionHeading(sales ? "Ciclo comercial" : "Abastecimiento", sales ? "Pedidos de venta" : "Órdenes de compra", sales ? "Pedido persistido en AWS y evento de cumplimiento enviado a Azure." : "Orden, recepción y evento de entrada al WMS.", chip((sales ? state.sales : state.purchases).length + " documentos"))}${renderOrderRows(type)}</section><section class="erp-card">${sectionHeading("Nuevo documento", sales ? "Registrar venta" : "Crear orden")}${orderForm(type)}</section></div>`;
  }

  function renderFinance() {
    const m = state.overview?.metrics || {};
    const rows = state.finance.length ? `<div class="erp-table-wrap"><table class="erp-table"><thead><tr><th>Referencia</th><th>Tipo / socio</th><th>Concepto</th><th>Vence</th><th>Estado</th><th>Monto</th><th></th></tr></thead><tbody>${state.finance.map((doc) => `<tr><td class="erp-mono">${esc(doc.reference)}</td><td>${doc.kind === "receivable" ? "Por cobrar" : "Por pagar"}<small>${esc(doc.partner_name || "Sin socio")}</small></td><td>${esc(doc.description)}</td><td>${esc(doc.due_date || "—")}</td><td>${chip(doc.status, doc.status === "paid" ? "ok" : "warn")}</td><td>${pen(doc.amount)}</td><td>${has("finance:write") && doc.status === "open" ? `<button class="erp-button" type="button" data-action="settle" data-id="${doc.id}">${doc.kind === "receivable" ? "Registrar cobro" : "Registrar pago"}</button>` : "—"}</td></tr>`).join("")}</tbody></table></div>` : empty("No hay documentos financieros aún.");
    const suppliers = state.partners.filter((p) => p.active && ["supplier", "both"].includes(p.kind));
    const form = has("finance:write") ? `<form class="erp-form" data-form="expense"><label>Concepto<input name="description" maxlength="180" required /></label><label>Proveedor<select name="partner_id"><option value="">Sin proveedor asociado</option>${suppliers.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join("")}</select></label><div class="erp-form-row"><label>Referencia<input name="reference" maxlength="80" placeholder="Se genera automáticamente" /></label><label>Monto (S/)<input name="amount" type="number" min="0.01" max="10000000" step="0.01" required /></label></div><label>Vencimiento<input name="due_date" type="date" /></label><button class="erp-button erp-button--primary" type="submit">Registrar gasto</button></form>` : `<p class="erp-disabled">Tu rol puede consultar, pero no registrar ni liquidar documentos.</p>`;
    return `<div class="erp-kpis"><article class="erp-kpi"><small>Cuentas por cobrar abiertas</small><strong>${pen(m.open_receivables)}</strong><span>Ventas confirmadas por WMS</span></article><article class="erp-kpi"><small>Cuentas por pagar abiertas</small><strong>${pen(m.open_payables)}</strong><span>Compras recibidas y gastos</span></article><article class="erp-kpi"><small>Documentos</small><strong>${state.finance.length}</strong><span>Máximo 200 recientes</span></article><article class="erp-kpi"><small>Moneda operativa</small><strong>PEN</strong><span>Soles peruanos</span></article></div><div class="erp-grid"><section class="erp-card">${sectionHeading("Tesorería básica", "Cobros y pagos", "Seguimiento operativo; no reemplaza contabilidad ni comprobantes tributarios.")}${rows}<p class="erp-note">El ERP crea cuentas por cobrar/pagar al confirmarse una venta/recepción; el estado de laboratorio no es un asiento contable.</p></section><section class="erp-card">${sectionHeading("Nuevo egreso", "Registrar gasto")}${form}</section></div>`;
  }

  function renderAccess() {
    const roles = Object.entries(state.access.role_labels || {});
    if (!state.users.length) return `<section class="erp-card">${sectionHeading("Acceso", "No hay cuentas internas")}${empty("Crea las cuentas en el administrador del portal y luego asigna sus permisos ERP aquí.")}</section>`;
    return `<section class="erp-card">${sectionHeading("Control de acceso", "Permisos ERP por cuenta", "Estos permisos son independientes del rol general del portal.", chip(`${state.users.length} cuentas`))}<div class="erp-table-wrap"><table class="erp-table erp-access-table"><thead><tr><th>Cuenta</th><th>Rol portal</th>${roles.map(([, label]) => `<th>${esc(label)}</th>`).join("")}</tr></thead><tbody>${state.users.map((user) => `<tr><td><strong>${esc(user.username)}</strong><small>${esc(user.company || "")}</small></td><td>${esc(roleLabels[user.role] || user.role)}</td>${roles.map(([key, label]) => `<td><label class="erp-access-check"><input class="erp-check" type="checkbox" data-action="role-toggle" data-user="${user.id}" data-role="${esc(key)}" aria-label="${esc(label)} para ${esc(user.username)}" ${user.erp_roles.includes(key) ? "checked" : ""} ${user.role === "admin" && key === "erp_admin" ? "disabled" : ""} /></label></td>`).join("")}</tr>`).join("")}</tbody></table></div><p class="erp-note">El administrador del portal mantiene siempre el permiso Administración ERP. No asignes privilegios financieros o de maestros a cuentas que no los requieran.</p></section>`;
  }

  function renderMail() {
    const folders = `<aside class="erp-mail-folders" aria-label="Carpetas"><button class="erp-button ${state.folder === "inbox" ? "erp-button--primary" : "erp-button--quiet"}" type="button" data-action="mail-folder" data-folder="inbox">Entrada</button><button class="erp-button ${state.folder === "sent" ? "erp-button--primary" : "erp-button--quiet"}" type="button" data-action="mail-folder" data-folder="sent">Enviados</button><button class="erp-button" type="button" data-action="compose">Redactar</button></aside>`;
    const status = state.mailStatus?.smtp_configured ? "SMTP configurado" : "Solo buzón del portal";
    const testButton = state.user?.role === "admin" && state.mailStatus?.smtp_configured ? `<button class="erp-button" type="button" data-action="test-smtp">Probar SMTP</button>` : "";
    const previewLink = ["localhost", "127.0.0.1"].includes(location.hostname) && state.mailStatus?.smtp_configured ? `<a class="erp-button" href="http://localhost:8025" target="_blank" rel="noreferrer">Ver correo de prueba</a>` : "";
    const list = state.mail.length ? state.mail.map((m) => `<button class="erp-mail-row ${m.unread ? "unread" : ""}" type="button" data-action="open-mail" data-id="${m.id}" aria-current="${state.selectedMail?.id === m.id}"><strong>${esc(state.folder === "inbox" ? m.sender : m.recipient)}</strong><span>${esc(m.subject)}</span><small>${date(m.created_at)} · ${m.smtp_status === "accepted_by_smtp" ? "SMTP aceptó copia" : m.smtp_status === "smtp_failed" ? "SMTP no disponible" : m.smtp_status === "recipient_address_missing" ? "Cuenta sin dirección SMTP" : "Buzón del portal"}</small></button>`).join("") : empty(state.folder === "inbox" ? "Tu bandeja de entrada está vacía." : "Aún no enviaste mensajes.");
    const message = state.compose ? renderCompose() : state.selectedMail ? `<p class="eyebrow">${state.folder === "inbox" ? `De ${esc(state.selectedMail.sender)}` : `Para ${esc(state.selectedMail.recipient)}`}</p><h3>${esc(state.selectedMail.subject)}</h3><small>${date(state.selectedMail.created_at)}${state.selectedMail.read_at ? " · leído" : ""} · ${state.selectedMail.smtp_status === "accepted_by_smtp" ? "SMTP aceptó copia" : state.selectedMail.smtp_status === "smtp_failed" ? "SMTP no disponible" : "Buzón del portal"}</small><p class="erp-mail-body">${esc(state.selectedMail.body)}</p>` : `<div class="erp-empty">Elige un mensaje o redacta uno nuevo.</div>`;
    return `<section class="erp-card">${sectionHeading("Mensajería privada", "Buzón interno", "El mensaje queda guardado en el portal; si hay un relay configurado, se envía también una copia SMTP.", chip(status))}<div class="erp-actions erp-mail-transport-actions">${testButton}${previewLink}</div><div class="erp-mail-layout">${folders}<div class="erp-mail-list" aria-label="Mensajes">${list}</div><article class="erp-mail-reading">${message}</article></div><p class="erp-note">La aceptación SMTP no garantiza entrega final. Para correo público se necesitan buzones reales, dominio verificado y políticas SPF/DKIM/DMARC.</p></section>`;
  }

  function renderCompose() {
    const people = state.recipients.filter((item) => item.id !== state.user.id);
    if (!people.length) return `<div class="erp-empty">No hay otra cuenta interna activa para recibir mensajes.</div>`;
    return `<form class="erp-form" data-form="mail"><p class="eyebrow">Nuevo mensaje interno</p><label>Para<select name="recipient_id" required><option value="">Selecciona una cuenta</option>${people.map((person) => `<option value="${person.id}">${esc(person.username)}</option>`).join("")}</select></label><label>Asunto<input name="subject" maxlength="160" required /></label><label>Mensaje<textarea name="body" maxlength="20000" rows="7" required></textarea></label><div class="erp-actions"><button class="erp-button erp-button--primary" type="submit">Enviar al buzón</button><button class="erp-button erp-button--quiet" type="button" data-action="cancel-compose">Cancelar</button></div></form>`;
  }

  function formObject(form) { return Object.fromEntries(new FormData(form).entries()); }

  async function submitForm(form) {
    const values = formObject(form);
    const type = form.dataset.form;
    if (type === "partner") {
      await api("/api/erp/partners", { method: "POST", body: JSON.stringify(values) });
      announce("Socio comercial guardado.", "success");
      return loadSection("masters");
    }
    if (type === "product") {
      values.sale_price = Number(values.sale_price); values.purchase_cost = Number(values.purchase_cost);
      await api("/api/erp/products", { method: "POST", body: JSON.stringify(values) });
      announce("Producto guardado. El saldo sigue bajo la autoridad del WMS.", "success");
      return loadSection("masters");
    }
    if (type === "order") {
      const lines = $$(".erp-line", form).map((line) => ({ sku: $("[name=sku]", line).value, quantity: Number($("[name=quantity]", line).value) }));
      const path = form.dataset.type === "sales" ? "/api/erp/sales/orders" : "/api/erp/purchases/orders";
      const result = await api(path, { method: "POST", body: JSON.stringify({ partner_id: Number(values.partner_id), items: lines }) });
      announce(`${form.dataset.type === "sales" ? "Venta" : "Orden de compra"} ${result.reference} guardada. Estado: ${result.status}.`, "success");
      return loadSection(form.dataset.type);
    }
    if (type === "expense") {
      values.amount = Number(values.amount); values.partner_id = values.partner_id ? Number(values.partner_id) : null;
      const result = await api("/api/erp/finance/expenses", { method: "POST", body: JSON.stringify(values) });
      announce(`Gasto ${result.reference} registrado.`, "success");
      return loadSection("finance");
    }
    if (type === "mail") {
      values.recipient_id = Number(values.recipient_id);
      const result = await api("/api/erp/mail", { method: "POST", body: JSON.stringify(values) });
      state.compose = false; state.folder = "sent"; state.selectedMail = null;
      announce(result.smtp_status === "accepted_by_smtp" ? "Mensaje guardado; el relay SMTP aceptó la copia." : result.smtp_status === "smtp_failed" ? "Mensaje guardado en el portal; SMTP no aceptó la copia." : "Mensaje guardado en el buzón interno.", result.smtp_status === "smtp_failed" ? "warning" : "success");
      return loadSection("mail");
    }
  }

  async function handleAction(event) {
    const action = event.target.closest("[data-action]");
    if (!action) return;
    const kind = action.dataset.action;
    try {
      if (kind === "section") {
        state.section = action.dataset.section; state.compose = false; state.selectedMail = null;
        renderTabs(); await loadSection(state.section);
      } else if (kind === "refresh") {
        await loadSection(state.section);
      } else if (kind === "import-catalog") {
        if (!state.catalogRows.length || state.catalogImporting) return;
        state.catalogImporting = true; renderSection();
        try {
          const result = await api("/api/erp/products/import", { method: "POST", body: JSON.stringify({ products: state.catalogRows }) });
          state.catalogRows = []; state.catalogFileName = ""; state.catalogError = "";
          await loadSection("masters");
          announce(`Carga lista: ${result.created} SKU nuevos y ${result.updated} actualizados. Los saldos existentes se conservaron.`, "success");
        } catch (error) {
          state.catalogError = error.message; announce(error.message); renderSection();
        } finally { state.catalogImporting = false; renderSection(); }
      } else if (kind === "add-line") {
        const form = action.closest("form");
        const options = state.products.filter((p) => p.active).map((p) => `<option value="${esc(p.sku)}">${esc(p.name)} · ${esc(p.sku)}${p.on_hand == null ? "" : ` · ${esc(p.on_hand)} disp.`}</option>`).join("");
        $(".erp-lines", form).insertAdjacentHTML("beforeend", orderLine(options));
      } else if (kind === "remove-line") {
        const lines = $$(".erp-line", action.closest("form"));
        if (lines.length > 1) action.closest(".erp-line").remove();
      } else if (kind === "refresh-order") {
        const base = action.dataset.type === "sales" ? "sales" : "purchases";
        const result = await api(`/api/erp/${base}/orders/${action.dataset.id}/refresh`, { method: "POST" });
        announce(`Azure respondió: ${result.status}${result.wms_result?.note ? ` · ${result.wms_result.note}` : ""}`, result.status.includes("completed") || result.status.includes("received") ? "success" : "warning");
        await loadSection(base);
      } else if (kind === "receive-purchase") {
        const result = await api(`/api/erp/purchases/orders/${action.dataset.id}/receive`, { method: "POST" });
        announce(`Recepción enviada. Estado actual: ${result.status}.`, "success"); await loadSection("purchases");
      } else if (kind === "settle") {
        await api(`/api/erp/finance/documents/${action.dataset.id}/settle`, { method: "POST" });
        announce("Documento marcado como pagado/cobrado.", "success"); await loadSection("finance");
      } else if (kind === "mail-folder") {
        state.folder = action.dataset.folder; state.compose = false; state.selectedMail = null; await loadSection("mail");
      } else if (kind === "compose") {
        state.compose = true; state.selectedMail = null; await loadSection("mail");
      } else if (kind === "cancel-compose") {
        state.compose = false; await loadSection("mail");
      } else if (kind === "open-mail") {
        state.selectedMail = state.mail.find((item) => item.id === Number(action.dataset.id)) || null;
        if (state.folder === "inbox" && state.selectedMail && !state.selectedMail.read_at) {
          await api(`/api/erp/mail/${state.selectedMail.id}/read`, { method: "POST" });
          state.selectedMail.read_at = new Date().toISOString();
          state.selectedMail.unread = false;
          state.overview = state.overview || await api("/api/erp/overview");
          state.overview.unread_messages = Math.max(0, Number(state.overview.unread_messages || 0) - 1);
        }
        renderSection();
      } else if (kind === "test-smtp") {
        const result = await api("/api/erp/mail/smtp-test", { method: "POST" });
        announce(`Prueba aceptada por el relay SMTP (${result.message_id}).`, "success");
      }
    } catch (error) { announce(error.message); }
  }

  async function handleSubmit(event) {
    const form = event.target.closest("form[data-form]");
    if (!form) return;
    event.preventDefault();
    const submit = $("button[type=submit]", form);
    if (!form.reportValidity()) return;
    if (submit) { submit.disabled = true; submit.dataset.originalText = submit.textContent; submit.textContent = "Guardando…"; }
    try { await submitForm(form); }
    catch (error) { announce(error.message); }
    finally { if (submit?.isConnected) { submit.disabled = false; submit.textContent = submit.dataset.originalText || "Guardar"; } }
  }

  async function handleRoleChange(event) {
    const input = event.target.closest('input[data-action="role-toggle"]');
    if (!input) return;
    const person = state.users.find((user) => user.id === Number(input.dataset.user));
    if (!person) return;
    const roles = new Set(person.erp_roles);
    if (input.checked) roles.add(input.dataset.role); else roles.delete(input.dataset.role);
    input.disabled = true;
    try {
      await api(`/api/erp/users/${person.id}/roles`, { method: "PUT", body: JSON.stringify({ roles: [...roles] }) });
      person.erp_roles = [...roles]; announce(`Permisos actualizados para ${person.username}.`, "success");
    } catch (error) {
      input.checked = !input.checked; announce(error.message);
    } finally { input.disabled = person.role === "admin" && input.dataset.role === "erp_admin"; }
  }

  async function start() {
    document.documentElement.dataset.theme = localStorage.getItem("tangamandapio-theme") || "light";
    $("#erp-content").addEventListener("click", handleAction);
    $("#erp-content").addEventListener("submit", handleSubmit);
    $("#erp-content").addEventListener("change", (event) => { handleRoleChange(event); void handleCatalogFile(event); });
    $("#erp-tabs").addEventListener("click", handleAction);
    try {
      const session = await api("/api/auth/session");
      state.csrf = session.csrf_token || "";
      if (!session.authenticated) {
        $("#erp-identity").textContent = "Sesión no iniciada";
        $("#erp-content").innerHTML = `<section class="erp-card">${sectionHeading("Acceso requerido", "Inicia sesión en el portal")}${empty("Este módulo usa la misma cuenta y sesión del portal. Vuelve al inicio de sesión y ábrelo después de entrar.")}<a class="erp-button erp-button--primary" href="/">Ir al portal</a></section>`;
        return;
      }
      state.user = session.user;
      if (state.user.role === "customer") throw new Error("El ERP y el correo interno son exclusivos para cuentas corporativas.");
      $("#erp-identity").textContent = `${state.user.username} · ${roleLabels[state.user.role] || state.user.role}`;
      state.access = await api("/api/erp/access");
      const candidates = tabs();
      state.section = candidates.some((item) => item[0] === "overview") ? "overview" : "mail";
      await loadSection(state.section);
    } catch (error) {
      $("#erp-identity").textContent = "Acceso limitado";
      $("#erp-content").innerHTML = `<section class="erp-card">${sectionHeading("No disponible", "No se pudo abrir el módulo")}${empty(error.message)}<a class="erp-button" href="/">Volver al portal</a></section>`;
      announce(error.message);
    }
  }

  window.addEventListener("DOMContentLoaded", start, { once: true });
})();
