(() => {
  let observer;
  let verified = false;

  function addShortcut() {
    const target = document.querySelector(".topbar-meta");
    if (!target || target.querySelector(".erp-shortcut")) return;
    const link = document.createElement("a");
    link.className = "erp-shortcut";
    link.href = "/erp";
    link.textContent = "ERP y correo";
    link.setAttribute("aria-label", "Abrir ERP corporativo y correo interno");
    target.prepend(link);
  }

  function verifyAfterPortalLoads() {
    if (verified || !document.querySelector(".topbar-meta")) return;
    verified = true;
    observer?.disconnect();
    fetch("/api/auth/session", { credentials: "same-origin", cache: "no-store" })
      .then((response) => response.ok ? response.json() : null)
      .then((session) => {
        const role = session?.user?.role;
        if (!session?.authenticated || !role || role === "customer") return;
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
