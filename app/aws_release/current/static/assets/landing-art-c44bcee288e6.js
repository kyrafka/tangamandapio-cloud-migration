(() => {
  const reveal = () => {
    requestAnimationFrame(() => {
      document.documentElement.classList.add("landing-art-ready");
    });
  };

  let started = false;
  const startWhenNeeded = () => {
    if (started) return true;
    const hero = document.querySelector(".auth-minimal .brand-pane");
    let preload = document.querySelector("link[data-landing-art]");
    if (!hero && !preload) return false;
    if (!preload) {
      preload = document.createElement("link");
      preload.rel = "preload";
      preload.as = "image";
      preload.type = "image/svg+xml";
      preload.fetchPriority = "high";
      preload.href = "/images/tangamandapio-operations.svg";
      preload.dataset.landingArt = "";
      document.head.append(preload);
    }

    started = true;
    const image = new Image();
    image.decoding = "async";
    image.src = preload.href;

    if (typeof image.decode === "function") {
      image.decode().then(reveal, reveal);
    } else {
      image.addEventListener("load", reveal, { once: true });
      image.addEventListener("error", reveal, { once: true });
    }
    return true;
  };

  if (!startWhenNeeded()) {
    const observer = new MutationObserver(() => {
      if (startWhenNeeded()) observer.disconnect();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }
})();
