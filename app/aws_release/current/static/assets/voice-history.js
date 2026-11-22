import { createPortalApi } from "./portal-api.mjs";

const request = createPortalApi({
  invalid_history_range: "Elige dos fechas válidas en orden, hasta hoy y con un máximo de 31 días.",
});
const clock = new Intl.DateTimeFormat("es-PE", { dateStyle: "short", timeStyle: "short", timeZone: "America/Lima" });
const statuses = {
  ringing: "Sonando", accepted: "En curso", ended: "Finalizada",
  rejected: "Rechazada", cancelled: "Cancelada", expired: "Sin respuesta",
};

function addHistory(card) {
  const panel = document.createElement("details");
  panel.className = "history-picker voice-history-picker";
  panel.innerHTML = `<summary>Histórico de llamadas</summary>
    <form class="history-form">
      <label>Desde<input type="date" name="from" required></label>
      <label>Hasta<input type="date" name="to" required></label>
      <button type="submit">Buscar llamadas</button>
      <small>Hora de Lima · hasta 31 días por consulta.</small>
    </form>
    <p role="status"></p>
    <div class="table-wrap" hidden><table>
      <thead><tr><th scope="col">Fecha</th><th scope="col">Dirección</th><th scope="col">Extensión</th><th scope="col">Estado</th></tr></thead>
      <tbody></tbody>
    </table></div>
    <nav class="history-pages" aria-label="Páginas del historial" hidden>
      <button type="button" data-step="-1">Anterior</button>
      <span></span>
      <button type="button" data-step="1">Siguiente</button>
    </nav>`;
  card.after(panel);
  const form = panel.querySelector("form");
  const status = panel.querySelector('[role="status"]');
  const results = panel.querySelector(".table-wrap");
  const rows = panel.querySelector("tbody");
  const pager = panel.querySelector("nav");
  const previous = pager.querySelector("[data-step='-1']");
  const next = pager.querySelector("[data-step='1']");
  const submit = form.querySelector("button");
  const today = new Intl.DateTimeFormat("fr-CA", { timeZone: "America/Lima", year: "numeric", month: "2-digit", day: "2-digit" }).format();
  for (const input of form.querySelectorAll("input")) input.max = today;
  let selection;
  let page = 1;
  let loading = false;

  async function load(target) {
    if (loading || !selection) return;
    loading = true;
    submit.disabled = true;
    pager.hidden = true;
    results.hidden = true;
    status.textContent = "Consultando llamadas…";
    try {
      const data = await request(`/api/voice/calls?${new URLSearchParams({ ...selection, page: target })}`, { signal: AbortSignal.timeout(10000) });
      if (!Array.isArray(data.calls)) throw new Error("Histórico temporalmente no disponible.");
      if (!panel.isConnected) return;
      page = data.page;
      rows.replaceChildren();
      for (const call of data.calls) {
        const row = rows.insertRow();
        row.insertCell().textContent = clock.format(new Date(call.created_at));
        row.insertCell().textContent = call.direction === "incoming" ? "Entrante" : "Saliente";
        row.insertCell().textContent = `${call.peer.username} · Ext. ${call.peer.extension}`;
        row.insertCell().textContent = statuses[call.status] || call.status;
      }
      status.textContent = data.calls.length ? `${selection.from} a ${selection.to}` : "No hay llamadas en estas fechas.";
      results.hidden = !data.calls.length;
      pager.hidden = !data.has_more && page === 1;
      pager.querySelector("span").textContent = `Página ${page}`;
      previous.disabled = page === 1;
      next.disabled = !data.has_more;
    } catch (error) {
      status.textContent = error.status === 401 ? "Vuelve a iniciar sesión." : error.message;
    } finally {
      loading = false;
      submit.disabled = false;
    }
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    selection = Object.fromEntries(new FormData(form));
    load(1);
  });
  previous.addEventListener("click", () => load(page - 1));
  next.addEventListener("click", () => load(page + 1));
}

const root = document.querySelector("#root");
function mount() {
  const card = root?.querySelector(".voice-history");
  if (card?.querySelector("h2")?.textContent === "Llamadas recientes" && !card.nextElementSibling?.matches(".voice-history-picker")) {
    addHistory(card);
  } else if (!card) {
    root?.querySelector(".voice-history-picker")?.remove();
  }
}
if (root) {
  const observer = new MutationObserver(mount);
  observer.observe(root, { childList: true, subtree: true });
  mount();
}
