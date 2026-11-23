export const maxRequestsPerSecond = 150;
export const maxRunSeconds = 300;
export const maxRequestsPerRun = 28500;
const maxInFlight = 56;
const maxCredit = 4;

export async function runRequestLoad({ rate, seconds, signal, progress = () => {} }) {
  if (!Number.isInteger(rate) || rate < 1 || rate > maxRequestsPerSecond ||
      !Number.isInteger(seconds) || seconds < 1 || seconds > maxRunSeconds ||
      rate * seconds > maxRequestsPerRun) {
    throw new RangeError("Carga fuera de los límites del ensayo.");
  }
  const pending = new AbortController();
  const started = performance.now();
  let lastTick = started;
  let credit = 0;
  let sent = 0;
  let succeeded = 0;
  let failed = 0;
  let inFlight = 0;
  let consecutiveErrors = 0;
  let reason;

  const snapshot = () => ({ sent, succeeded, failed, reason,
    elapsed: Math.min(seconds, (performance.now() - started) / 1000) });

  return new Promise((resolve) => {
    function finish(cause) {
      if (reason) return;
      reason = cause;
      clearInterval(ticker);
      clearInterval(reporter);
      signal?.removeEventListener("abort", cancel);
      pending.abort();
      resolve(snapshot());
    }

    function cancel() { finish("stopped"); }

    async function send() {
      sent++;
      inFlight++;
      let status;
      try {
        const response = await fetch("/api", { cache: "no-store", credentials: "omit", redirect: "error",
          signal: AbortSignal.any([pending.signal, AbortSignal.timeout(3000)]) });
        status = response.status;
        await response.arrayBuffer();
      } catch { status = 0; }
      inFlight--;
      if (reason) return;
      if (status === 200) {
        succeeded++;
        consecutiveErrors = 0;
      } else {
        failed++;
        consecutiveErrors++;
        if (status === 403 || status === 429) finish("limited");
        else if (consecutiveErrors >= 3 || (failed >= 5 && failed / (succeeded + failed) > .05)) finish("errors");
      }
    }

    const ticker = setInterval(() => {
      const now = performance.now();
      if (now - started >= seconds * 1000) { finish("complete"); return; }
      credit = Math.min(maxCredit, credit + (now - lastTick) * rate / 1000);
      lastTick = now;
      while (!reason && credit >= 1 && inFlight < maxInFlight && sent < rate * seconds) {
        credit--;
        void send();
      }
    }, 20);
    const reporter = setInterval(() => progress(snapshot()), 1000);
    signal?.addEventListener("abort", cancel, { once: true });
    if (signal?.aborted) cancel();
  });
}
