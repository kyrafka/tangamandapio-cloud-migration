import { createPortalApi } from "/assets/portal-api.mjs";
import { startVisibleRefresh } from "/assets/visible-refresh.mjs";
import * as requestLoad from "/assets/request-load.mjs";

const { maxRequestsPerSecond, maxRunSeconds, runRequestLoad } = requestLoad;
const maxRequestsPerRun = requestLoad.maxRequestsPerRun ?? maxRequestsPerSecond * maxRunSeconds;

(() => {
  // Older cached pages still load this controller as a separate asset.
  if (!document.querySelector("#scaling-stop")) {
    const current = new URL(window.location.href);
    if (!current.searchParams.has("actualizar-vista")) {
      const fresh = new URL("/administracion?actualizar-vista=1", current.origin);
      window.location.replace(fresh);
    } else {
      const warning = document.querySelector("#admin-notice");
      if (warning) {
        warning.textContent = "La vista quedó desactualizada. Abre Administración desde el portal.";
        warning.dataset.tone = "error";
        warning.hidden = false;
      }
    }
    return;
  }

  const roleLabels = {
    admin: "Administrador",
    operations: "Operaciones TI",
    sales: "Comercial",
    warehouse: "Operador WMS",
    auditor: "Auditor",
    customer: "Cliente B2B",
  };
  const state = { user: null, section: "users", users: [], companies: [], subscriptions: [] };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
  }

  const api = createPortalApi({
    authentication_required: "La sesión terminó. Vuelve a ingresar.",
    insufficient_role: "Esta acción requiere una cuenta administradora.",
    csrf_token_required: "La sesión de seguridad cambió. Actualiza la página e inténtalo de nuevo.",
    invalid_alarm_email: "Escribe un correo válido.",
    alarm_notifications_not_configured: "El tema de alarmas no está configurado en este entorno.",
    alarm_service_access_denied: "El rol de AWS no permite administrar esta suscripción.",
    alarm_service_unavailable: "AWS SNS no respondió. Comprueba el servicio e inténtalo de nuevo.",
    alarm_subscription_not_found: "La suscripción ya no existe o no pertenece a este tema.",
    alarm_subscription_pending_confirmation: "Confirma primero la suscripción desde el correo recibido.",
    username_already_exists: "Ya existe una cuenta con ese usuario.",
    company_slug_already_exists: "Ya existe una empresa con ese identificador.",
    cannot_remove_last_admin: "No puedes quitar el último administrador activo.",
    cannot_remove_own_admin_access: "No puedes quitar tu propia cuenta administradora.",
    backup_too_large: "La copia excede el límite del panel. Usa el respaldo completo de PostgreSQL.",
    backup_storage_unavailable: "No se pudo acceder al almacenamiento del respaldo.",
    scaling_not_configured: "Este entorno no tiene un grupo de escalado configurado.",
    scaling_unavailable: "AWS no pudo consultar el grupo de escalado.",
    technical_tests_unavailable: "Este entorno todavía no tiene resultados registrados.",
  });

  function notice(message, tone = "success") {
    const box = $("#admin-notice");
    box.textContent = message;
    box.dataset.tone = tone;
    box.hidden = false;
    box.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "nearest" });
  }

  function hideNotice() { $("#admin-notice").hidden = true; }

  function setBusy(button, busy, label = "Procesando…") {
    if (!button) return;
    if (busy) {
      button.dataset.originalText = button.textContent;
      button.textContent = label;
      button.disabled = true;
    } else {
      button.textContent = button.dataset.originalText || button.textContent;
      button.disabled = false;
    }
  }

  function badge(text, tone) {
    return `<span class="admin-status ${tone}">${escapeHtml(text)}</span>`;
  }

  function fillRoleOptions(select, current = "customer") {
    select.innerHTML = Object.entries(roleLabels).map(([value, label]) =>
      `<option value="${value}" ${value === current ? "selected" : ""}>${label}</option>`).join("");
  }

  function fillCompanyOptions(select, current = "") {
    const options = state.companies.map((company) =>
      `<option value="${company.id}" ${String(company.id) === String(current) ? "selected" : ""}>${escapeHtml(company.name)}</option>`);
    select.innerHTML = `<option value="">Selecciona una empresa</option>${options.join("")}`;
  }

  function updateSummary() {
    $("#active-user-count").textContent = state.users.filter((user) => user.active).length || "0";
    $("#company-count").textContent = state.companies.length || "0";
    $("#confirmed-alert-count").textContent = state.subscriptions.filter((item) => item.status === "confirmed").length || "0";
  }

  async function loadUsers() {
    const [users, companies] = await Promise.all([
      api("/api/admin/users"),
      api("/api/admin/companies"),
    ]);
    state.users = users;
    state.companies = companies;
    renderUsers();
    renderCompanies();
    fillCompanyOptions($("#new-user-company"));
    fillRoleOptions($("#new-user-role"));
    updateSummary();
  }

  function renderUsers() {
    const body = $("#users-rows");
    $("#users-count").textContent = `${state.users.length} cuentas`;
    $("#users-empty").hidden = state.users.length > 0;
    body.innerHTML = state.users.map((user) => {
      const roleOptions = Object.entries(roleLabels).map(([value, label]) =>
        `<option value="${value}" ${value === user.role ? "selected" : ""}>${label}</option>`).join("");
      const companyOptions = state.companies.map((company) =>
        `<option value="${company.id}" ${Number(company.id) === Number(user.company_id) ? "selected" : ""}>${escapeHtml(company.name)}</option>`).join("");
      return `<tr data-user-row="${user.id}">
        <td><strong>${escapeHtml(user.username)}</strong><small>${user.must_change_password ? "Usa una clave temporal" : `Creada ${new Date(user.created_at).toLocaleDateString("es-PE")}`}</small></td>
        <td><select data-user-role aria-label="Rol de ${escapeHtml(user.username)}">${roleOptions}</select></td>
        <td><select data-user-company aria-label="Empresa de ${escapeHtml(user.username)}">${companyOptions}</select></td>
        <td><select data-user-active aria-label="Acceso de ${escapeHtml(user.username)}"><option value="true" ${user.active ? "selected" : ""}>Activo</option><option value="false" ${!user.active ? "selected" : ""}>Suspendido</option></select></td>
        <td><div class="admin-table-actions"><button class="admin-button primary" type="button" data-action="save-user" data-id="${user.id}">Guardar</button>${user.id === state.user?.id ? "" : `<button class="admin-button secondary" type="button" data-action="reset-password" data-id="${user.id}">Restablecer clave</button>`}</div></td>
      </tr>`;
    }).join("");
    updateSummary();
  }

  function renderCompanies() {
    const body = $("#companies-rows");
    $("#companies-count").textContent = `${state.companies.length} empresas`;
    $("#companies-empty").hidden = state.companies.length > 0;
    body.innerHTML = state.companies.map((company) => `<tr>
      <td><strong>${escapeHtml(company.name)}</strong></td>
      <td><code>${escapeHtml(company.slug)}</code></td>
      <td>${Number(company.users) || 0}</td>
      <td>${new Date(company.created_at).toLocaleDateString("es-PE")}</td>
    </tr>`).join("");
    updateSummary();
  }

  async function loadAlerts() {
    const result = await api("/api/admin/alarm-subscriptions");
    state.subscriptions = result.subscriptions || [];
    renderAlerts();
    updateSummary();
  }

  function renderAlerts() {
    const body = $("#alerts-rows");
    $("#alerts-count").textContent = `${state.subscriptions.length} destinatarios`;
    $("#alerts-empty").hidden = state.subscriptions.length > 0;
    body.innerHTML = state.subscriptions.map((item) => {
      const pending = item.status !== "confirmed";
      return `<tr>
        <td><strong>${escapeHtml(item.endpoint)}</strong></td>
        <td>${badge(pending ? "Pendiente de confirmar" : "Confirmado", pending ? "pending" : "confirmed")}</td>
        <td>${pending ? `<span class="admin-form-hint">Confirma desde el mensaje enviado.</span>` : `<button class="admin-button danger" type="button" data-action="remove-alert" data-arn="${escapeHtml(item.subscription_arn)}">Dar de baja</button>`}</td>
      </tr>`;
    }).join("");
    updateSummary();
  }

  async function loadAudit() {
    const rows = await api("/api/audit");
    $("#audit-count").textContent = `${rows.length} eventos`;
    $("#audit-empty").hidden = rows.length > 0;
    $("#audit-rows").innerHTML = rows.map((entry) => `<tr>
      <td>${new Date(entry.created_at).toLocaleString("es-PE")}</td>
      <td>${escapeHtml(entry.actor)}</td>
      <td><code>${escapeHtml(entry.action)}</code></td>
      <td>${escapeHtml(entry.subject_type)} ${escapeHtml(entry.subject_id || "")}</td>
    </tr>`).join("");
  }

  function friendlyDate(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("es-PE");
  }

  let backupListVersion = 0;
  let backupAWSConfigured = false;
  const backupSnapshots = {};

  async function loadBackups(signal = AbortSignal.timeout(10000)) {
    const version = ++backupListVersion;
    const checked = $("#backup-checked");
    let backups;
    try {
      backups = await api("/api/admin/backups", { signal });
    } catch (error) {
      if (version === backupListVersion && checked) {
        checked.textContent = "No se pudo actualizar el catálogo. Se conserva la última lectura.";
      }
      throw error;
    }
    if (version !== backupListVersion) return;
    const create = $("#backup-create");
    backupAWSConfigured = backups.aws.configured;
    create.disabled = !backupAWSConfigured || create.dataset.saving === "true";
    if (checked) checked.textContent = `Última consulta ${new Date().toLocaleTimeString("es-PE")}`;
    for (const [source, listing] of Object.entries(backups)) {
      const target = $(`#backup-${source}`);
      const snapshot = JSON.stringify(listing);
      if (backupSnapshots[source] === snapshot) continue;
      const activeLink = target.contains(document.activeElement) ? document.activeElement.href : null;
      backupSnapshots[source] = snapshot;
      if (!listing.items.length) {
        target.textContent = listing.error ? "Almacenamiento temporalmente inaccesible." :
          listing.configured ? "Aún no hay copias guardadas." : "Almacenamiento sin configurar.";
        continue;
      }
      target.innerHTML = `<div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>Copia</th><th>Fecha</th><th>Tamaño</th><th>Archivo</th></tr></thead><tbody>${listing.items.map((item, index) =>
        `<tr><td><strong>${escapeHtml(item.name)}</strong>${index === 0 ? " · Última copia" : ""}</td><td>${escapeHtml(friendlyDate(item.date))}</td><td>${Number(item.bytes).toLocaleString("es-PE")} B</td><td><a class="admin-button secondary" href="/api/admin/backups/${source}/${encodeURIComponent(item.name)}">Descargar</a></td></tr>`
      ).join("")}</tbody></table></div>`;
      if (activeLink) Array.from(target.querySelectorAll("a")).find((link) => link.href === activeLink)?.focus({ preventScroll: true });
    }
  }

  async function loadTechnicalTests() {
    const report = await api("/api/admin/technical-tests");
    $("#technical-date").textContent = `Corte: ${friendlyDate(report.observed_at)}.`;
    $("#technical-rows").innerHTML = report.checks.map(({name, result, scope}) =>
      `<tr><td>${escapeHtml(name)}</td><td>${escapeHtml(result)}</td><td>${escapeHtml(scope)}</td></tr>`
    ).join("");
  }

  async function probePrivateWms(event) {
    const button = event.currentTarget;
    const status = $("#technical-wms-status");
    button.disabled = true;
    status.textContent = "Consultando las colas de Azure…";
    const started = performance.now();
    try {
      const {azure_queue: queue} = await api("/api/platform/fulfillment-health");
      const latency = Math.round(performance.now() - started);
      const states = {ok: "Colas disponibles", degraded: "Información parcial", unavailable: "Colas sin respuesta"};
      status.textContent = `${states[queue.status] || states.unavailable}. ${latency} ms. ` +
        `Pendientes: ${queue.pending ?? "sin dato"}. Fallidos: ${queue.poison ?? "sin dato"}.`;
    } catch (error) {
      status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }

  let scalingGroup;
  let scalingRun;
  let scalingBaseline;
  async function loadScaling(signal) {
    const form = $("#scaling-form");
    const status = $("#scaling-status");
    const policy = $("#scaling-policy");
    try {
      scalingGroup = await api("/api/admin/scaling", { signal });
      const { healthy, desired, minimum, maximum, requests_per_target, request_target_active, restore_at } = scalingGroup;
      status.textContent = `${healthy} en servicio y sanas · capacidad deseada ${desired} · rango ${minimum} a ${maximum}.`;
      if (restore_at) policy.textContent = `Hay un cambio manual anterior programado hasta ${friendlyDate(restore_at)}.`;
      else if (request_target_active) {
        const target = new Intl.NumberFormat("es-PE").format(requests_per_target);
        const totalRate = Math.floor(requests_per_target * desired / 60) + 1;
        const limit = totalRate > maxRequestsPerSecond ? ` El panel aporta hasta ${maxRequestsPerSecond} por segundo.` : "";
        policy.textContent = `Objetivo de AWS: ${target} solicitudes por minuto por instancia. Con ${desired} instancias, el tráfico total debe llegar a unas ${totalRate} solicitudes por segundo de forma sostenida para superar el objetivo.${limit}`;
      } else policy.textContent = "La política de escalado por solicitudes está inactiva.";
      if (scalingBaseline !== undefined) {
        $("#scaling-observed").textContent = `Desde el inicio del ensayo: ${scalingBaseline} → ${desired} instancias deseadas.`;
      }
    } catch (error) {
      scalingGroup = undefined;
      status.textContent = error.message;
      policy.textContent = "";
    } finally {
      form.querySelector("button[type=submit]").disabled = Boolean(scalingRun || !scalingGroup?.request_target_active || scalingGroup.restore_at);
    }
  }

  async function startScalingLoad(event) {
    event.preventDefault();
    if (scalingRun || !scalingGroup?.request_target_active || scalingGroup.restore_at || document.hidden) return;
    const form = event.currentTarget;
    const rate = form.elements.rate.valueAsNumber;
    const seconds = form.elements.minutes.valueAsNumber * 60;
    const submit = form.querySelector("button[type=submit]");
    const stop = $("#scaling-stop");
    const status = $("#scaling-traffic");
    const controller = new AbortController();
    const render = ({ sent, succeeded, failed, elapsed, reason }) => {
      const labels = { complete: "Carga finalizada", stopped: "Carga detenida",
        limited: "Carga detenida por el límite de tráfico", errors: "Carga detenida por errores" };
      const pace = elapsed > 0 ? (sent / elapsed).toFixed(1) : "0";
      const pending = sent - succeeded - failed;
      const unanswered = pending ? ` · ${pending} ${reason ? "sin respuesta al detener" : "en curso"}` : "";
      status.textContent = `${labels[reason] || "Enviando solicitudes"} · ${sent} enviadas (${pace}/s) · ${succeeded} correctas · ${failed} con error${unanswered}.`;
    };
    scalingRun = controller;
    submit.disabled = form.elements.rate.disabled = form.elements.minutes.disabled = true;
    stop.disabled = false;
    try {
      const run = async () => {
        scalingBaseline = scalingGroup?.desired;
        $("#scaling-observed").textContent = "";
        render({sent: 0, succeeded: 0, failed: 0, elapsed: 0});
        render(await runRequestLoad({ rate, seconds, signal: controller.signal, progress: render }));
      };
      if (navigator.locks) {
        await navigator.locks.request("tangamandapio-admin-load", { ifAvailable: true }, async (lock) => {
          if (lock) await run();
          else status.textContent = "Ya hay un ensayo en otra pestaña.";
        });
      } else await run();
    } catch (error) {
      status.textContent = error.message;
    } finally {
      scalingRun = undefined;
      stop.disabled = true;
      form.elements.rate.disabled = form.elements.minutes.disabled = false;
      if (state.section === "scaling") await loadScaling();
    }
  }

  async function loadSection(section) {
    if (section !== "scaling") scalingRun?.abort();
    hideNotice();
    state.section = section;
    $$("[data-section]").forEach((button) => button.setAttribute("aria-current", button.dataset.section === section ? "page" : "false"));
    $$("[data-view]").forEach((view) => { view.hidden = view.dataset.view !== section; });
    try {
      if (section === "users") await loadUsers();
      if (section === "companies") {
        state.companies = await api("/api/admin/companies");
        renderCompanies();
      }
      if (section === "alerts") await loadAlerts();
      if (section === "backups") await loadBackups();
      if (section === "scaling") await loadScaling();
      if (section === "technical") await loadTechnicalTests();
      if (section === "audit") await loadAudit();
    } catch (error) {
      if (error.status === 401) { window.location.replace("/"); return; }
      notice(error.message, "error");
    }
  }

  async function handleUserAction(event) {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const row = button.closest("[data-user-row]");
    const userId = Number(button.dataset.id);
    if (button.dataset.action === "save-user") {
      const current = state.users.find((user) => user.id === userId);
      if (!current) return;
      setBusy(button, true, "Guardando…");
      try {
        const payload = {
          role: $("[data-user-role]", row).value,
          company_id: Number($("[data-user-company]", row).value),
          active: $("[data-user-active]", row).value === "true",
        };
        await api(`/api/admin/users/${userId}`, { method: "PATCH", body: JSON.stringify(payload) });
        notice(`Se actualizó el acceso de ${current.username}. Las sesiones anteriores quedaron revocadas.`);
        await loadUsers();
      } catch (error) { notice(error.message, "error"); }
      finally { setBusy(button, false); }
    }
    if (button.dataset.action === "reset-password") {
      const current = state.users.find((user) => user.id === userId);
      if (!current || !window.confirm(`¿Generar una nueva clave temporal para ${current.username}? La clave anterior dejará de funcionar.`)) return;
      setBusy(button, true, "Generando…");
      try {
        const result = await api(`/api/admin/users/${userId}/reset-password`, { method: "POST", body: JSON.stringify({}) });
        const credential = $("#temporary-credential");
        credential.innerHTML = `<div><p class="eyebrow">Clave temporal · se muestra una sola vez</p><strong>${escapeHtml(current.username)}</strong><code>${escapeHtml(result.temporary_password)}</code><small>Compártela por un canal seguro. Al ingresar se exigirá cambiarla.</small></div><button class="admin-button secondary" type="button" data-action="copy-password">Copiar clave</button>`;
        credential.hidden = false;
        notice("Clave temporal generada. Cópiala ahora y compártela por un canal seguro.");
        await loadUsers();
      } catch (error) { notice(error.message, "error"); }
      finally { setBusy(button, false); }
    }
  }

  async function handleAlertAction(event) {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    if (button.dataset.action === "copy-password") {
      const credential = $("#temporary-credential code")?.textContent || "";
      try { await navigator.clipboard.writeText(credential); notice("Clave copiada al portapapeles."); }
      catch { notice("No se pudo copiar automáticamente. Selecciona la clave y cópiala manualmente.", "error"); }
    }
    if (button.dataset.action === "remove-alert") {
      const target = button.closest("tr")?.querySelector("td strong")?.textContent || "este destinatario";
      if (!window.confirm(`¿Dar de baja ${target} de las alarmas del portal?`)) return;
      setBusy(button, true, "Dando de baja…");
      try {
        await api("/api/admin/alarm-subscriptions", {
          method: "DELETE",
          body: JSON.stringify({ subscription_arn: button.dataset.arn }),
        });
        notice("El destinatario fue dado de baja del tema de alarmas.");
        await loadAlerts();
      } catch (error) { notice(error.message, "error"); }
      finally { setBusy(button, false); }
    }
  }

  async function start() {
    try {
      const session = await api("/api/auth/session");
      if (!session.authenticated || session.user?.role !== "admin") { window.location.replace("/"); return; }
      state.user = session.user;
      $("#admin-identity").textContent = `${session.user.username} · Administrador`;
      const savedTheme = window.localStorage.getItem("tangamandapio-theme");
      document.documentElement.dataset.theme = savedTheme === "dark" ? "dark" : "light";
      $("#admin-theme").addEventListener("click", () => {
        const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        document.documentElement.dataset.theme = theme;
        try { window.localStorage.setItem("tangamandapio-theme", theme); } catch {}
      });
      $$("[data-section]").forEach((button) => button.addEventListener("click", () => loadSection(button.dataset.section)));
      $$("[data-reload]").forEach((button) => button.addEventListener("click", () => loadSection(button.dataset.reload)));
      $("#users-rows").addEventListener("click", handleUserAction);
      $("#temporary-credential").addEventListener("click", handleAlertAction);
      $("#alerts-rows").addEventListener("click", handleAlertAction);
      startVisibleRefresh((signal) => state.section === "backups" && loadBackups(signal), 60000);
      $("#backup-create").addEventListener("click", async (event) => {
        const button = event.currentTarget;
        button.dataset.saving = "true";
        setBusy(button, true, "Guardando…");
        try {
          const result = await api("/api/admin/backups", { method: "POST" });
          notice(`Copia guardada en AWS con ${result.events} eventos outbox.`);
          await loadBackups();
        } catch (error) { notice(error.message, "error"); }
        finally {
          delete button.dataset.saving;
          setBusy(button, false);
          button.disabled = !backupAWSConfigured;
        }
      });
      $("#technical-wms-probe").addEventListener("click", probePrivateWms);
      const scalingForm = $("#scaling-form");
      function updateLoadLimit() {
        const minutes = Math.min(5, Math.max(1, scalingForm.elements.minutes.valueAsNumber || 1));
        const max = Math.min(maxRequestsPerSecond, Math.floor(maxRequestsPerRun / (minutes * 60)));
        scalingForm.elements.rate.max = max;
        const hint = $("#scaling-load-limit");
        if (hint) hint.textContent = `Con ${minutes} min puedes enviar hasta ${max} solicitudes/s.`;
      }
      updateLoadLimit();
      scalingForm.elements.minutes.addEventListener("input", updateLoadLimit);
      scalingForm.addEventListener("submit", startScalingLoad);
      $("#scaling-stop").addEventListener("click", () => scalingRun?.abort());
      document.addEventListener("visibilitychange", () => { if (document.hidden) scalingRun?.abort(); });
      window.addEventListener("pagehide", () => scalingRun?.abort());
      startVisibleRefresh((signal) => state.section === "scaling" && loadScaling(signal), 20000);
      $("#user-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const button = form.querySelector("button[type=submit]");
        const values = new FormData(form);
        setBusy(button, true, "Creando…");
        try {
          await api("/api/admin/users", { method: "POST", body: JSON.stringify({ username: values.get("username"), password: values.get("password"), role: values.get("role"), company_id: Number(values.get("company_id")) }) });
          form.reset();
          notice("Cuenta creada. El usuario deberá cambiar la contraseña temporal al ingresar.");
          await loadUsers();
        } catch (error) { notice(error.message, "error"); }
        finally { setBusy(button, false); }
      });
      $("#company-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const button = form.querySelector("button[type=submit]");
        const values = new FormData(form);
        setBusy(button, true, "Creando…");
        try {
          await api("/api/admin/companies", { method: "POST", body: JSON.stringify({ name: values.get("name"), slug: values.get("slug") }) });
          form.reset();
          notice("Empresa creada y lista para asignar a sus cuentas.");
          state.companies = await api("/api/admin/companies");
          renderCompanies();
          fillCompanyOptions($("#new-user-company"));
        } catch (error) { notice(error.message, "error"); }
        finally { setBusy(button, false); }
      });
      $("#alert-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const button = form.querySelector("button[type=submit]");
        const email = new FormData(form).get("email");
        setBusy(button, true, "Enviando…");
        try {
          const result = await api("/api/admin/alarm-subscriptions", { method: "POST", body: JSON.stringify({ email }) });
          form.reset();
          notice(result.already_exists ? "Ese correo ya está suscrito o esperando confirmación." : "Se envió el correo de confirmación. El destinatario debe aceptarlo antes de recibir avisos.");
          await loadAlerts();
        } catch (error) { notice(error.message, "error"); }
        finally { setBusy(button, false); }
      });
      await loadSection("users");
    } catch (error) {
      notice(error.message || "No se pudo validar la sesión.", "error");
      if (error.status === 401) window.location.replace("/");
    }
  }

  start();
})();
