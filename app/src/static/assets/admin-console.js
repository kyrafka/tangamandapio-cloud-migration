(() => {
  const roleLabels = {
    admin: "Administrador",
    operations: "Operaciones TI",
    sales: "Comercial",
    warehouse: "Operador WMS",
    auditor: "Auditor",
    customer: "Cliente B2B",
  };
  const safeMethods = new Set(["GET", "HEAD", "OPTIONS"]);
  const state = { csrf: "", user: null, section: "users", users: [], companies: [], subscriptions: [] };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
  }

  async function api(path, options = {}) {
    const method = String(options.method || "GET").toUpperCase();
    if (!safeMethods.has(method) && !state.csrf) await api("/api/auth/session");
    const headers = new Headers(options.headers || {});
    if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    if (!safeMethods.has(method) && state.csrf) headers.set("X-CSRF-Token", state.csrf);
    const response = await fetch(path, { ...options, method, headers, credentials: "same-origin", cache: "no-store" });
    const body = response.status === 204 ? null : await response.json().catch(() => ({}));
    if (body?.csrf_token) state.csrf = body.csrf_token;
    if (!response.ok) {
      const labels = {
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
      };
      const code = body?.error || `HTTP ${response.status}`;
      throw Object.assign(new Error(labels[code] || code), { status: response.status, code });
    }
    return body;
  }

  function notice(message, tone = "success") {
    const box = $("#admin-notice");
    box.textContent = message;
    box.dataset.tone = tone;
    box.hidden = false;
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
        <td><strong>${escapeHtml(user.username)}</strong><small>${user.must_change_password ? "Cambio de clave pendiente" : `Creada ${new Date(user.created_at).toLocaleDateString("es-PE")}`}</small></td>
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

  async function loadSection(section) {
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
      state.csrf = session.csrf_token || "";
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
      $("#user-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = event.currentTarget.querySelector("button[type=submit]");
        const form = new FormData(event.currentTarget);
        setBusy(button, true, "Creando…");
        try {
          await api("/api/admin/users", { method: "POST", body: JSON.stringify({ username: form.get("username"), password: form.get("password"), role: form.get("role"), company_id: Number(form.get("company_id")) }) });
          event.currentTarget.reset();
          notice("Cuenta creada. El usuario deberá cambiar la contraseña temporal al ingresar.");
          await loadUsers();
        } catch (error) { notice(error.message, "error"); }
        finally { setBusy(button, false); }
      });
      $("#company-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = event.currentTarget.querySelector("button[type=submit]");
        const form = new FormData(event.currentTarget);
        setBusy(button, true, "Creando…");
        try {
          await api("/api/admin/companies", { method: "POST", body: JSON.stringify({ name: form.get("name"), slug: form.get("slug") }) });
          event.currentTarget.reset();
          notice("Empresa creada y lista para asignar a sus cuentas.");
          state.companies = await api("/api/admin/companies");
          renderCompanies();
          fillCompanyOptions($("#new-user-company"));
        } catch (error) { notice(error.message, "error"); }
        finally { setBusy(button, false); }
      });
      $("#alert-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = event.currentTarget.querySelector("button[type=submit]");
        const email = new FormData(event.currentTarget).get("email");
        setBusy(button, true, "Enviando…");
        try {
          const result = await api("/api/admin/alarm-subscriptions", { method: "POST", body: JSON.stringify({ email }) });
          event.currentTarget.reset();
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
