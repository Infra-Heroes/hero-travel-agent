// Drawing suggestions and day plans, for the planner (app.js) and the shared,
// read-only page (share.js). Everything the model wrote is set as textContent,
// never as HTML.

(function () {
  "use strict";

  const lang = () => window.I18N.lang;
  const eur = (n) =>
    new Intl.NumberFormat(lang() === "en" ? "en-GB" : "de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);

  /** el("p", {className: "x"}, "text", child) */
  function el(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === "dataset") Object.assign(node.dataset, v);
      else if (k in node) node[k] = v;
      else node.setAttribute(k, v);
    }
    for (const c of children) if (c != null) node.append(c);
    return node;
  }

  // ── Suggestions ──────────────────────────────────────────────────────────────

  /** opts: onToPlan(destination), votes {destination: 1|-1}, onVote(destination, vote) */
  function suggestions(data, opts = {}) {
    const list = el("div", { className: "suggestions" });
    for (const s of data.suggestions) {
      const card = el("article", { className: "card suggestion" });
      card.append(
        el("header", {}, el("h3", { className: "dest", textContent: s.destination }), el("span", { className: "price", textContent: `${__("ca.")} ${eur(s.total_estimate_eur)}` })),
        el("p", { className: "why", textContent: s.why_it_fits }),
        el(
          "dl",
          { className: "facts" },
          el("div", {}, el("dt", { textContent: __("Wetter") }), el("dd", { textContent: s.weather })),
          el("div", {}, el("dt", { textContent: __("Anreise") }), el("dd", { textContent: s.getting_there })),
          el("div", {}, el("dt", { textContent: __("Unterkunft") }), el("dd", { textContent: s.accommodation }))
        ),
        el("h4", { textContent: __("Highlights") })
      );
      const hl = el("ul", { className: "highlights" });
      for (const h of s.highlights) hl.append(el("li", { textContent: h }));
      const tbody = el("tbody");
      for (const c of s.cost_estimate) tbody.append(el("tr", {}, el("td", { textContent: c.item }), el("td", { textContent: eur(c.eur) })));
      card.append(
        hl,
        el("details", {}, el("summary", { textContent: __("Kostenschätzung") }), el("table", { className: "costs" }, tbody)),
        el("p", { className: "caveat", textContent: s.caveat })
      );
      const actions = el("div", { className: "actions" });
      if (opts.onVote) actions.append(voteButtons(s.destination, opts));
      if (opts.onToPlan) {
        const b = el("button", { className: "primary to-plan", textContent: __("Tagesplan dafür") });
        b.addEventListener("click", () => opts.onToPlan(s.destination));
        actions.append(b);
      }
      if (actions.children.length) card.append(actions);
      list.append(card);
    }
    return list;
  }

  function voteButtons(destination, opts) {
    const box = el("span", { className: "votes", role: "group", "aria-label": __("Wie gefällt dir das?") });
    const state = { v: (opts.votes || {})[destination] || 0 };
    const mk = (v, label, title) => {
      const b = el("button", { type: "button", className: "vote", textContent: label, title, "aria-label": title });
      b.addEventListener("click", async () => {
        const next = state.v === v ? 0 : v;
        try {
          await opts.onVote(destination, next);
          state.v = next;
          paint();
        } catch (err) {
          /* the caller shows the error */
        }
      });
      return b;
    };
    const up = mk(1, "👍", __("Gefällt mir"));
    const down = mk(-1, "👎", __("Gefällt mir nicht"));
    const paint = () => {
      up.setAttribute("aria-pressed", String(state.v === 1));
      down.setAttribute("aria-pressed", String(state.v === -1));
    };
    paint();
    box.append(up, down);
    return box;
  }

  // ── Day plan ─────────────────────────────────────────────────────────────────

  function factsBox(plan) {
    const f = plan.facts;
    if (!f || (!f.weather && !(f.holidays || []).length)) return null;
    const box = el("div", { className: "facts-box" });
    box.append(el("h3", { textContent: __("Fakten zum Reisezeitraum") }));
    if (f.weather) {
      const w = f.weather;
      box.append(
        el("p", {
          textContent: `${__("Wetter dieser Tage in den letzten")} ${w.years} ${__("Jahren")}: ${Math.round(w.temp_min_c)}–${Math.round(w.temp_max_c)} °C, ${__("Regen an")} ${Math.round(w.rainy_days_share * 100)} % ${__("der Tage")}.`,
        })
      );
    }
    const hol = f.holidays || [];
    if (hol.length) {
      const ul = el("ul", { className: "holidays" });
      for (const h of hol) {
        const what = h.kind === "public" ? __("Feiertag") : __("Schulferien");
        const when = h.start === h.end ? h.start : `${h.start} – ${h.end}`;
        ul.append(el("li", { textContent: `${what}${h.regional ? ` (${__("regional")})` : ""}: ${h.name}, ${when}` }));
      }
      box.append(ul);
    }
    box.append(el("small", { className: "muted", textContent: __("Quellen: Open-Meteo (gemessene Werte), OpenHolidays.") }));
    return box;
  }

  const SLOT_COLOR = { morning: "#e8a33d", afternoon: "#2f7fbf", evening: "#7a4fb3" };

  /** A Leaflet map with the day's places; returns null without places or without Leaflet. */
  function map(plan, onDay) {
    const all = plan.days.flatMap((d) => (d.places || []).map((p) => ({ ...p, day: d.day })));
    if (!all.length || !window.L) return null;
    const box = el("div", { className: "map-box" });
    const filter = el("div", { className: "map-days", role: "group", "aria-label": __("Tag auf der Karte") });
    const area = el("div", { className: "map", role: "img", "aria-label": __("Karte der Orte") });
    box.append(filter, area, el("small", { className: "muted", textContent: __("Ungefähre Lage, vom Agenten angegeben. Kartendaten © OpenStreetMap-Mitwirkende.") }));
    let leaflet = null;
    let layer = null;
    const draw = (day) => {
      if (!leaflet) return;
      layer.clearLayers();
      const shown = all.filter((p) => !day || p.day === day);
      const pts = [];
      for (const p of shown) {
        pts.push([p.lat, p.lon]);
        window.L.circleMarker([p.lat, p.lon], { radius: 7, color: SLOT_COLOR[p.slot], weight: 2, fillOpacity: 0.7 })
          .bindTooltip(`${__("Tag")} ${p.day}: ${p.name}`)
          .addTo(layer);
      }
      if (day && pts.length > 1) window.L.polyline(pts, { color: "#555", weight: 2, dashArray: "4 6" }).addTo(layer);
      if (pts.length) leaflet.fitBounds(pts, { padding: [24, 24], maxZoom: 15 });
      filter.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.day) === (day || 0))));
    };
    const mk = (day, label) => {
      const b = el("button", { type: "button", className: "chip-btn", textContent: label, dataset: { day: String(day) } });
      b.addEventListener("click", () => {
        draw(day);
        if (day && onDay) onDay(day);
      });
      filter.append(b);
    };
    mk(0, __("Alle Tage"));
    for (const d of plan.days) if ((d.places || []).length) mk(d.day, `${__("Tag")} ${d.day}`);
    // Leaflet needs the element in the page and with a size: wait for both, a few
    // seconds at most (a tab in the background may not draw frames for a while).
    let tries = 0;
    const init = () => {
      if (!area.isConnected || !area.offsetWidth) {
        if (tries++ < 300) setTimeout(init, 50);
        return;
      }
      leaflet = window.L.map(area, { scrollWheelZoom: false });
      window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: "© OpenStreetMap",
      }).addTo(leaflet);
      layer = window.L.layerGroup().addTo(leaflet);
      draw(0);
    };
    setTimeout(init, 0);
    box.show = draw;
    return box;
  }

  function checksFor(plan, day) {
    return (plan.checks || []).filter((c) => c.day === day);
  }

  /** opts: onRefine(day, wish) -> Promise (planner only) */
  function dayCard(plan, d, opts) {
    const card = el("article", { className: "day", id: `day-${d.day}` });
    card.append(
      el("header", {}, el("span", { className: "num", textContent: d.day }), el("h3", { className: "theme", textContent: d.theme }), el("span", { className: "date muted", textContent: d.date })),
      el(
        "ol",
        { className: "slots" },
        el("li", {}, el("span", { textContent: __("Vormittag") }), el("p", { textContent: d.morning })),
        el("li", {}, el("span", { textContent: __("Nachmittag") }), el("p", { textContent: d.afternoon })),
        el("li", {}, el("span", { textContent: __("Abend") }), el("p", { textContent: d.evening }))
      ),
      el("p", { className: "extra" }, el("b", { textContent: __("Essen:") }), " ", d.food_tip),
      el("p", { className: "extra" }, el("b", { textContent: __("Bei Regen:") }), " ", d.bad_weather),
      el("p", { className: "extra muted" }, el("b", { textContent: __("Wege:") }), " ", d.logistics)
    );
    const route = (plan.routes || []).find((r) => r.day === d.day);
    if (route) card.append(el("p", { className: "extra muted", textContent: `${__("Geschätzte Wege:")} ${route.km} km, ${__("etwa")} ${route.minutes} min` }));
    const checks = checksFor(plan, d.day);
    if (checks.length) {
      const ul = el("ul", { className: "checks" });
      for (const c of checks) ul.append(el("li", { className: `check ${c.level}`, textContent: c.text }));
      card.append(ul);
    }
    if (opts.onRefine) card.append(refineForm(d, opts));
    return card;
  }

  function refineForm(d, opts) {
    const box = el("details", { className: "refine" });
    const form = el("form");
    const input = el("input", { name: "wish", required: true, minLength: 3, maxLength: 300, placeholder: __("z. B. entspannter, mehr für Kinder, ohne Museum") });
    const go = el("button", { type: "submit", className: "primary", textContent: __("Tag neu planen") });
    form.append(el("label", {}, __("Was soll anders werden?"), input), el("div", { className: "actions" }, go));
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      opts.onRefine(d.day, input.value.trim(), go);
    });
    box.append(el("summary", { textContent: __("Diesen Tag anpassen") }), form);
    return box;
  }

  /** The body of a plan: facts, map, days, packing list. */
  function planBody(plan, opts = {}) {
    const frag = document.createDocumentFragment();
    const facts = factsBox(plan);
    if (facts) frag.append(facts);
    const warn = (plan.checks || []).filter((c) => c.level === "warn").length;
    if (warn) frag.append(el("p", { className: "check warn summary", textContent: `${warn} ${__("Hinweise zur Machbarkeit, siehe die Tage.")}` }));
    const days = el("div", { className: "days" });
    const m = map(plan, (day) => document.getElementById(`day-${day}`)?.scrollIntoView({ behavior: "smooth", block: "start" }));
    if (m) frag.append(m);
    for (const d of plan.days) days.append(dayCard(plan, d, opts));
    frag.append(days);
    const pl = el("ul", { className: "packing" });
    for (const item of plan.packing_list) pl.append(el("li", {}, el("input", { type: "checkbox" }), " " + item));
    frag.append(el("h3", { textContent: __("Packliste") }), pl);
    frag.days = days;
    return frag;
  }

  window.Render = { el, eur, suggestions, planBody };
})();
