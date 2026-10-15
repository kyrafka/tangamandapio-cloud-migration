(() => {
  const allowedRoles = new Set(["admin", "operations"]);
  let observer;
  let verified = false;
  let currentRole = "";

  function addShortcut() {
    const target = document.querySelector(".topbar-meta");
    if (!target || target.querySelector(".platform-shortcut")) return;
    const link = document.createElement("a");
    link.className = "platform-shortcut";
    link.href = "/platform";
    link.textContent = "Nube y seguridad";
    link.setAttribute("aria-label", "Abrir el centro de nube, seguridad y usuarios");
    target.prepend(link);
  }

  function addAdministrationNavigation() {
    if (currentRole !== "admin") return;
    const nav = document.querySelector(".sidebar nav");
    if (!nav) return;
    Array.from(nav.querySelectorAll("button")).forEach((button) => {
      const label = button.querySelector(".nav-label")?.textContent?.trim() || button.textContent.trim();
      if (["Usuarios", "Empresas", "Usuarios y roles"].includes(label)) button.hidden = true;
    });
    if (!nav.querySelector(".work-nav-label")) {
      const heading = document.createElement("p");
      heading.className = "sidebar-group-label work-nav-label";
      heading.textContent = "Trabajo";
      nav.prepend(heading);
    }
    if (!nav.querySelector(".admin-nav-label")) {
      const heading = document.createElement("p");
      heading.className = "sidebar-group-label admin-nav-label";
      heading.textContent = "Administración";
      nav.append(heading);
    }
    if (!nav.querySelector(".admin-console-link")) {
      const link = document.createElement("a");
      link.className = "admin-console-link";
      link.href = "/administracion";
      link.setAttribute("aria-label", "Abrir administración general");
      link.title = "Administración";
      link.innerHTML = '<span class="nav-icon nav-icon-admin" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 20 7v5c0 5-3.4 8-8 10-4.6-2-8-5-8-10V7l8-4Z"/><path d="M12 8v8M8.5 12h7"/></svg></span><span class="nav-label">Administración</span>';
      if (window.location.pathname === "/administracion") link.setAttribute("aria-current", "page");
      nav.append(link);
    }
  }

  function refreshNavigation() {
    addShortcut();
    addAdministrationNavigation();
  }

  function verifyAfterPortalLoads() {
    if (verified || !document.querySelector(".topbar-meta")) return;
    verified = true;
    observer?.disconnect();
    fetch("/api/auth/session", { credentials: "same-origin", cache: "no-store" })
      .then((response) => response.ok ? response.json() : null)
      .then((session) => {
        if (!session?.authenticated || !allowedRoles.has(session.user?.role)) return;
        currentRole = session.user.role;
        const root = document.getElementById("root");
        if (!root) return;
        observer = new MutationObserver(refreshNavigation);
        observer.observe(root, { childList: true, subtree: true });
        refreshNavigation();
      })
      .catch(() => {});
  }

  const root = document.getElementById("root");
  if (root) {
    observer = new MutationObserver(verifyAfterPortalLoads);
    observer.observe(root, { childList: true, subtree: true });
    verifyAfterPortalLoads();
  }

  window.addEventListener("pagehide", () => observer?.disconnect(), { once: true });
})();
