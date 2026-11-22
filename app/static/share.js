// The shared, read-only view of a trip: no account, no changes.
(function () {
  "use strict";
  const token = location.pathname.split("/").pop();
  const out = document.getElementById("out");
  const note = document.getElementById("note");
  const R = window.Render;

  document.getElementById("print").addEventListener("click", () => window.print());

  fetch(`/api/shared/${encodeURIComponent(token)}`, { headers: { Accept: "application/json", "X-Lang": window.I18N.lang } })
    .then(async (res) => {
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || __("Dieser Link ist abgelaufen oder wurde zurückgezogen."));
      return body;
    })
    .then((trip) => {
      document.getElementById("title").textContent = trip.title;
      document.title = `${trip.title} – Urlaubs-Agent`;
      note.textContent = `${__("Nur lesen, gültig bis")} ${new Date(trip.expires_at).toLocaleDateString(window.I18N.lang === "en" ? "en-GB" : "de-DE")}. ${__("Preise sind Schätzungen; gebucht ist nichts.")}`;
      const p = trip.payload;
      if (trip.kind === "plan") {
        const card = R.el("div", { className: "card plan" });
        card.append(R.el("h2", { textContent: `${p.days.length} ${__("Tage in")} ${p.destination}` }), R.el("p", { textContent: p.overview }), R.planBody(p));
        out.append(card);
      } else {
        out.append(R.el("p", { textContent: p.summary }), R.suggestions(p));
      }
    })
    .catch((err) => {
      note.textContent = err.message;
      document.getElementById("print").hidden = true;
    });
})();
