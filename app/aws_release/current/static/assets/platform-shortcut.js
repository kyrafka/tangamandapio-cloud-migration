(() => {
  const allowedRoles = new Set(["admin", "operations"]);
  let observer;
  let verified = false;

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

  function verifyAfterPortalLoads() {
    if (verified || !document.querySelector(".topbar-meta")) return;
    verified = true;
    observer?.disconnect();
    fetch("/api/auth/session", { credentials: "same-origin", cache: "no-store" })
      .then((response) => response.ok ? response.json() : null)
      .then((session) => {
        if (!session?.authenticated || !allowedRoles.has(session.user?.role)) return;
        const root = document.getElementById("root");
        if (!root) return;
        observer = new MutationObserver(addShortcut);
        observer.observe(root, { childList: true, subtree: true });
        addShortcut();
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
