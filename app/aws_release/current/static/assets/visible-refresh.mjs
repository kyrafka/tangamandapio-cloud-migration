export function startVisibleRefresh(refresh, interval) {
  let timer;
  let running = false;
  let suspended = false;
  let failures = 0;
  const visible = () => !suspended && !document.hidden && navigator.onLine;

  function schedule(delay) {
    clearTimeout(timer);
    if (visible() && !running) timer = setTimeout(run, delay);
  }

  async function run() {
    if (!visible() || running) return;
    running = true;
    try {
      await refresh(AbortSignal.timeout(10000));
      failures = 0;
    } catch (error) {
      if (error.status === 401) {
        suspended = true;
        window.location.replace("/");
      }
      failures = Math.min(3, failures + 1);
    } finally {
      running = false;
      schedule(Math.min(60000, interval * 2 ** failures));
    }
  }

  document.addEventListener("visibilitychange", () => schedule(0));
  window.addEventListener("online", () => schedule(0));
  window.addEventListener("offline", () => clearTimeout(timer));
  window.addEventListener("pagehide", () => { suspended = true; clearTimeout(timer); });
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) { suspended = false; schedule(0); }
  });
  schedule(interval);
}
