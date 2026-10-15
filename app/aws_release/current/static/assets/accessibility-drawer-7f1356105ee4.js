(() => {
  let previousOpen;

  const syncDrawer = () => {
    const shell = document.querySelector(".auth-minimal");
    const drawer = document.getElementById("access-sidebar");
    if (!shell || !drawer) return;

    const isOpen = shell.classList.contains("drawer-open");
    drawer.inert = !isOpen;
    if (isOpen) {
      drawer.removeAttribute("aria-hidden");
    } else {
      drawer.setAttribute("aria-hidden", "true");
    }

    if (previousOpen === true && !isOpen) {
      requestAnimationFrame(() => {
        shell.querySelector(".access-drawer-trigger")?.focus({ preventScroll: true });
      });
    } else if (previousOpen === false && isOpen) {
      requestAnimationFrame(() => {
        drawer.querySelector('input[autocomplete="username"]')?.focus({ preventScroll: true });
      });
    }

    previousOpen = isOpen;
  };

  const observer = new MutationObserver(syncDrawer);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
    childList: true,
    subtree: true,
  });
  syncDrawer();
})();
