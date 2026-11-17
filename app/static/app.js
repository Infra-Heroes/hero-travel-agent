// Urlaubs-Agent page. Everything the model writes is set as textContent -
// never as HTML - so a suggestion can never inject markup into the page.

const INTERESTS_DE = ["Strand", "Natur", "Wandern", "Kultur", "Städte", "Essen", "Familie", "Ruhe", "Abenteuer", "Wellness"];
const INTERESTS = INTERESTS_DE.map((x) => __(x));
const $ = (sel, root = document) => root.querySelector(sel);

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toast.t);
  toast.t = setTimeout(() => (el.hidden = true), 3500);
}

const body401 = __("Anmelden");

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", Accept: "application/json", "X-Lang": window.I18N.lang },
    ...options,
  });
  if (res.status === 401) {
    window.location.href = "/";
    throw new Error(body401);
  }
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail) ? __("Bitte die Eingabe prüfen.") : body.detail;
    throw new Error(detail || `${__("Fehler")} ${res.status}`);
  }
  return body;
}

// ── Tabs ─────────────────────────────────────────────────────────────────────
function showTab(name) {
  document.querySelectorAll('[role="tab"]').forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
  document.querySelectorAll(".panel").forEach((p) => (p.hidden = p.id !== `tab-${name}`));
  if (name === "trips") loadTrips();
}
document.querySelectorAll('[role="tab"]').forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));

// ── Interest chips ───────────────────────────────────────────────────────────
document.querySelectorAll("fieldset.chips").forEach((fs) => {
  for (const name of INTERESTS) {
    const label = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.name = "interests";
    box.value = name;
    label.append(box, " " + name);
    fs.append(label);
  }
});

function formData(form) {
  const data = {};
  for (const el of form.elements) {
    if (!el.name || el.name === "interests") continue;
    if (el.value === "") continue;
    data[el.name] = el.type === "number" ? Number(el.value) : el.value;
  }
  data.lang = window.I18N.lang;
  data.interests = [...form.querySelectorAll('input[name="interests"]:checked')].map((c) => c.value);
  return data;
}

async function busy(button, label, fn) {
  const old = button.textContent;
  button.disabled = true;
  button.textContent = label;
  try {
    return await fn();
  } catch (err) {
    toast(err.message);
  } finally {
    button.disabled = false;
    button.textContent = old;
    // Every request uses up one of today's: show what is left.
    if (typeof showMe === "function") showMe();
  }
}

const eur = (n) => new Intl.NumberFormat(window.I18N.lang === "en" ? "en-GB" : "de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);

// ── Autocomplete and help ────────────────────────────────────────────────────
const MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"];
function whenOptions() {
  const now = new Date();
  const out = ["Osterferien", "Pfingstferien", "Sommerferien", "Herbstferien", "Weihnachtsferien", "Wochenende", "Langes Wochenende"].map((x) => __(x));
  for (let i = 1; i <= 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
    out.push(`${__(MONTHS[d.getMonth()])} ${d.getFullYear()}`);
  }
  return out;
}
const ORIGINS = ["Frankfurt", "München", "Berlin", "Hamburg", "Köln/Bonn", "Düsseldorf", "Stuttgart", "Hannover", "Nürnberg", "Leipzig", "Dresden", "Bremen", "Dortmund", "Wien", "Zürich"];
const DESTINATIONS = ["Lissabon, Portugal", "Porto, Portugal", "Algarve, Portugal", "Barcelona, Spanien", "Mallorca, Spanien", "Teneriffa, Spanien", "Valencia, Spanien", "Andalusien, Spanien", "Rom, Italien", "Sizilien, Italien", "Toskana, Italien", "Amalfiküste, Italien", "Kreta, Griechenland", "Athen, Griechenland", "Paris, Frankreich", "Provence, Frankreich", "Amsterdam, Niederlande", "Kopenhagen, Dänemark", "Wien, Österreich", "Prag, Tschechien", "Budapest, Ungarn", "Dubrovnik, Kroatien", "Istrien, Kroatien", "Malta", "Zypern", "Island", "Norwegen, Fjorde", "Schottland", "Irland", "Madeira, Portugal", "Marrakesch, Marokko", "Istanbul, Türkei"];
const NOTE_IDEAS_DE = [
  "Mit Kleinkind, kurze Wege",
  "Nicht zu weit fliegen",
  "Ohne Mietwagen",
  "Mit Hund",
  "Barrierearm",
  "Eher ruhig, wenig Touristen",
  "Gutes Essen ist wichtig",
  "Viel draußen, wenn möglich Wandern",
  "Badewetter wichtig",
  "Kulturprogramm bei Regen",
  "Ankunft erst abends",
  "Vegetarisch",
];
const NOTE_IDEAS = NOTE_IDEAS_DE.map((x) => __(x));

function fillList(id, values) {
  const dl = document.getElementById(id);
  for (const v of values) {
    const o = document.createElement("option");
    o.value = v;
    dl.append(o);
  }
}
fillList("dl-when", whenOptions());
fillList("dl-origin", ORIGINS);
fillList("dl-dest", DESTINATIONS);

// Tap a suggestion to add it to "Sonstiges" (once, comma separated).
document.querySelectorAll(".ideas").forEach((box) => {
  const form = box.closest("form");
  for (const text of NOTE_IDEAS) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "idea";
    b.textContent = "+ " + text;
    b.addEventListener("click", () => {
      const area = form.elements.notes;
      const parts = area.value.split(/[,\n]/).map((x) => x.trim()).filter(Boolean);
      if (!parts.includes(text)) parts.push(text);
      area.value = parts.join(", ");
      area.focus();
    });
    box.append(b);
  }
});

function setChecked(form, names) {
  form.querySelectorAll('input[name="interests"]').forEach((c) => (c.checked = names.includes(c.value)));
}
$("#example-brief").addEventListener("click", () => {
  const f = $("#brief");
  f.when.value = whenOptions()[0];
  f.nights.value = 7;
  f.budget_eur.value = 2500;
  f.origin.value = "Frankfurt";
  f.adults.value = 2;
  f.children.value = 1;
  setChecked(f, ["Strand", "Natur", "Familie"]);
  f.notes.value = __("Nicht zu weit fliegen, Kind 6 Jahre");
});
$("#example-plan").addEventListener("click", () => {
  const f = $("#planform");
  f.destination.value = window.I18N.lang === "en" ? "Lisbon, Portugal" : "Lissabon, Portugal";
  f.days.value = 4;
  f.adults.value = 2;
  f.children.value = 0;
  f.pace.value = "ausgewogen";
  setChecked(f, ["Kultur", "Essen", "Städte"]);
  f.notes.value = __("Ohne Mietwagen");
});

// ── Suggestions ──────────────────────────────────────────────────────────────
let lastBrief = null;

function renderSuggestions(data, target, { saveable = true } = {}) {
  target.replaceChildren();
  const head = document.createElement("div");
  head.className = "result-head";
  const p = document.createElement("p");
  p.textContent = data.summary;
  head.append(p);
  if (saveable) {
    const save = document.createElement("button");
    save.textContent = __("Vorschläge merken");
    save.addEventListener("click", () =>
      busy(save, __("Speichere…"), async () => {
        const title = `${__("Ideen")}: ${lastBrief?.when || __("Reise")} (${data.suggestions.map((s) => s.destination.split(",")[0]).join(", ")})`;
        await api("/api/trips", { method: "POST", body: JSON.stringify({ title, kind: "suggestions", payload: data }) });
        toast(__("Gemerkt unter „Meine Reisen“"));
      })
    );
    head.append(save);
  }
  target.append(head);

  const list = document.createElement("div");
  list.className = "suggestions";
  for (const s of data.suggestions) {
    const node = $("#t-suggestion").content.cloneNode(true);
    window.I18N.translate(node);
    $(".dest", node).textContent = s.destination;
    $(".price", node).textContent = `${__("ca.")} ${eur(s.total_estimate_eur)}`;
    $(".why", node).textContent = s.why_it_fits;
    $(".weather", node).textContent = s.weather;
    $(".getting", node).textContent = s.getting_there;
    $(".stay", node).textContent = s.accommodation;
    const hl = $(".highlights", node);
    for (const h of s.highlights) {
      const li = document.createElement("li");
      li.textContent = h;
      hl.append(li);
    }
    const tbody = $(".costs tbody", node);
    for (const c of s.cost_estimate) {
      const tr = document.createElement("tr");
      const a = document.createElement("td");
      const b = document.createElement("td");
      a.textContent = c.item;
      b.textContent = eur(c.eur);
      tr.append(a, b);
      tbody.append(tr);
    }
    $(".caveat", node).textContent = s.caveat;
    $(".to-plan", node).addEventListener("click", () => prefillPlan(s.destination));
    list.append(node);
  }
  target.append(list);
}

$("#brief").addEventListener("submit", (e) => {
  e.preventDefault();
  const button = $("#brief button[type=submit]");
  busy(button, __("Der Agent plant…"), async () => {
    lastBrief = formData(e.target);
    const data = await api("/api/suggest", { method: "POST", body: JSON.stringify(lastBrief) });
    renderSuggestions(data, $("#ideas-out"));
  });
});

function prefillPlan(destination) {
  const form = $("#planform");
  form.destination.value = destination;
  if (lastBrief) {
    form.days.value = Math.min(lastBrief.nights + 1, 14);
    form.adults.value = lastBrief.adults;
    form.children.value = lastBrief.children || 0;
    form.querySelectorAll('input[name="interests"]').forEach((c) => (c.checked = lastBrief.interests.includes(c.value)));
  }
  showTab("plan");
  form.scrollIntoView({ behavior: "smooth" });
}

// ── Exports: calendar, Google Calendar, PDF ─────────────────────────────────
const pad = (n) => String(n).padStart(2, "0");
const ymd = (d) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
function dayDate(day) {
  const d = new Date(`${day.date}T00:00:00`);
  return Number.isNaN(d.getTime()) ? null : d;
}
const icsText = (t) => String(t).replace(/\\/g, "\\\\").replace(/;/g, "\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
function foldLine(line) {
  // RFC 5545: at most 75 octets per line, continuation lines start with a space.
  const out = [];
  let rest = line;
  while (rest.length > 70) {
    out.push(rest.slice(0, 70));
    rest = " " + rest.slice(70);
  }
  out.push(rest);
  return out.join("\r\n");
}

/** Calendar file. timed=false: one all-day entry per day; true: morning, afternoon and evening. */
function planToIcs(plan, { timed }) {
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//InfraHeroes//Urlaubs-Agent//DE", "CALSCALE:GREGORIAN"];
  const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z";
  const slots = [
    [__("Vormittag"), "morning", "100000", "123000"],
    [__("Nachmittag"), "afternoon", "140000", "180000"],
    [__("Abend"), "evening", "190000", "220000"],
  ];
  for (const day of plan.days) {
    const d = dayDate(day);
    if (!d) continue;
    const next = new Date(d.getTime() + 86400000);
    const uid = `${ymd(d)}-${day.day}-${Math.abs([...plan.destination].reduce((a, c) => a * 31 + c.charCodeAt(0), 7) | 0)}@urlaubs-agent`;
    const extra = `${__("Essen:")} ${day.food_tip}\n${__("Bei Regen:")} ${day.bad_weather}\n${__("Wege:")} ${day.logistics}`;
    if (!timed) {
      lines.push(
        "BEGIN:VEVENT", `UID:${uid}`, `DTSTAMP:${stamp}`, `DTSTART;VALUE=DATE:${ymd(d)}`, `DTEND;VALUE=DATE:${ymd(next)}`,
        `SUMMARY:${icsText(`${__("Tag")} ${day.day}: ${day.theme} (${plan.destination})`)}`,
        `DESCRIPTION:${icsText(`${__("Vormittag")}: ${day.morning}\n${__("Nachmittag")}: ${day.afternoon}\n${__("Abend")}: ${day.evening}\n${extra}`)}`,
        "END:VEVENT"
      );
    } else {
      for (const [label, key, from, to] of slots) {
        lines.push(
          "BEGIN:VEVENT", `UID:${uid.replace("@", `-${key}@`)}`, `DTSTAMP:${stamp}`,
          `DTSTART:${ymd(d)}T${from}`, `DTEND:${ymd(d)}T${to}`,
          `SUMMARY:${icsText(`${label}: ${day[key].slice(0, 60)}`)}`,
          `DESCRIPTION:${icsText(`${__("Tag")} ${day.day} (${day.theme}, ${plan.destination})\n${day[key]}\n${extra}`)}`,
          "END:VEVENT"
        );
      }
    }
  }
  lines.push("END:VCALENDAR");
  return lines.map(foldLine).join("\r\n") + "\r\n";
}

function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const slug = (t) => t.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "reise";

function googleLink(plan, day) {
  const d = dayDate(day);
  if (!d) return null;
  const next = new Date(d.getTime() + 86400000);
  const q = new URLSearchParams({
    action: "TEMPLATE",
    text: `${__("Tag")} ${day.day}: ${day.theme} (${plan.destination})`,
    dates: `${ymd(d)}/${ymd(next)}`,
    details: `${__("Vormittag")}: ${day.morning}\n${__("Nachmittag")}: ${day.afternoon}\n${__("Abend")}: ${day.evening}\n${__("Essen:")} ${day.food_tip}\n${__("Bei Regen:")} ${day.bad_weather}`,
  });
  return `https://calendar.google.com/calendar/render?${q}`;
}

function planTable(plan) {
  const table = document.createElement("table");
  table.className = "plan-table";
  const cols = [[__("Tag"), (d) => `${d.day}`], [__("Datum"), (d) => d.date], [__("Thema"), (d) => d.theme], [__("Vormittag"), (d) => d.morning], [__("Nachmittag"), (d) => d.afternoon], [__("Abend"), (d) => d.evening], [__("Essen"), (d) => d.food_tip], [__("Bei Regen:").replace(":", ""), (d) => d.bad_weather], [__("Wege:").replace(":", ""), (d) => d.logistics]];
  const head = table.createTHead().insertRow();
  for (const [name] of cols) {
    const th = document.createElement("th");
    th.textContent = name;
    th.scope = "col";
    head.append(th);
  }
  const body = table.createTBody();
  for (const d of plan.days) {
    const tr = body.insertRow();
    for (const [name, get] of cols) {
      const td = tr.insertCell();
      td.textContent = get(d);
      td.dataset.label = name;
    }
  }
  return table;
}

// ── Day plan ─────────────────────────────────────────────────────────────────
function renderPlan(plan, target, { tripId = null } = {}) {
  target.replaceChildren();
  const wrap = document.createElement("div");
  wrap.className = "card plan";
  const h = document.createElement("h2");
  h.textContent = `${plan.days.length} ${__("Tage in")} ${plan.destination}`;
  const ov = document.createElement("p");
  ov.textContent = plan.overview;
  const actions = document.createElement("div");
  actions.className = "actions";

  if (tripId) {
    const ics = document.createElement("a");
    ics.className = "button";
    ics.href = `/api/trips/${tripId}/calendar.ics`;
    ics.textContent = __("In Kalender übernehmen");
    actions.append(ics);
  } else {
    const save = document.createElement("button");
    save.textContent = __("Plan merken");
    save.addEventListener("click", () =>
      busy(save, __("Speichere…"), async () => {
        const trip = await api("/api/trips", {
          method: "POST",
          body: JSON.stringify({ title: `${__("Tagesplan")}: ${plan.destination}`, kind: "plan", payload: plan }),
        });
        toast(__("Gemerkt unter „Meine Reisen“"));
        renderPlan(plan, target, { tripId: trip.id });
      })
    );
    actions.append(save);
  }
  const view = document.createElement("button");
  view.type = "button";
  view.className = "ghost";
  view.textContent = __("Tabellenansicht");
  actions.append(view);

  const pdf = document.createElement("button");
  pdf.type = "button";
  pdf.textContent = __("Als PDF speichern");
  pdf.title = __("Öffnet den Druckdialog: dort „Als PDF speichern“ wählen");
  pdf.addEventListener("click", () => {
    // The print stylesheet shows the plan only; the browser turns it into a PDF.
    const old = document.title;
    document.title = `${__("Tagesplan")} ${plan.destination}`;
    window.print();
    document.title = old;
  });
  actions.append(pdf);

  const cal = document.createElement("details");
  cal.className = "menu";
  const sum = document.createElement("summary");
  sum.textContent = __("In Kalender");
  cal.append(sum);
  const menu = document.createElement("div");
  menu.className = "menu-body";
  const mk = (label, fn) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "link";
    b.textContent = label;
    b.addEventListener("click", fn);
    return b;
  };
  menu.append(
    mk(__("Kalenderdatei (.ics), ganze Tage"), () => download(`reise-${slug(plan.destination)}.ics`, planToIcs(plan, { timed: false }), "text/calendar")),
    mk(__("Kalenderdatei (.ics), mit Uhrzeiten"), () => download(`reise-${slug(plan.destination)}-zeiten.ics`, planToIcs(plan, { timed: true }), "text/calendar"))
  );
  const g = document.createElement("div");
  g.className = "google";
  const gl = document.createElement("span");
  gl.className = "muted";
  gl.textContent = __("Google Kalender, pro Tag:");
  g.append(gl);
  for (const d of plan.days) {
    const url = googleLink(plan, d);
    if (!url) continue;
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = `${__("Tag")} ${d.day}`;
    g.append(a);
  }
  if (g.children.length > 1) menu.append(g);
  cal.append(menu);
  actions.append(cal);
  wrap.append(h, ov, actions);

  const days = document.createElement("div");
  days.className = "days";
  const tableBox = document.createElement("div");
  tableBox.className = "table-box";
  tableBox.hidden = true;
  tableBox.append(planTable(plan));
  view.addEventListener("click", () => {
    const toTable = tableBox.hidden;
    tableBox.hidden = !toTable;
    days.hidden = toTable;
    view.textContent = toTable ? __("Kartenansicht") : __("Tabellenansicht");
    wrap.classList.toggle("as-table", toTable);
  });
  wrap.append(days, tableBox);

  for (const d of plan.days) {
    const node = $("#t-day").content.cloneNode(true);
    window.I18N.translate(node);
    $(".num", node).textContent = d.day;
    $(".theme", node).textContent = d.theme;
    $(".date", node).textContent = d.date;
    $(".morning", node).textContent = d.morning;
    $(".afternoon", node).textContent = d.afternoon;
    $(".evening", node).textContent = d.evening;
    $(".food", node).textContent = d.food_tip;
    $(".rain", node).textContent = d.bad_weather;
    $(".logistics", node).textContent = d.logistics;
    days.append(node);
  }
  const ph = document.createElement("h3");
  ph.textContent = __("Packliste");
  const pl = document.createElement("ul");
  pl.className = "packing";
  for (const item of plan.packing_list) {
    const li = document.createElement("li");
    const box = document.createElement("input");
    box.type = "checkbox";
    li.append(box, " " + item);
    pl.append(li);
  }
  wrap.append(ph, pl);
  target.append(wrap);
}

$("#planform").addEventListener("submit", (e) => {
  e.preventDefault();
  const button = $("#planform button[type=submit]");
  busy(button, __("Der Agent plant…"), async () => {
    const plan = await api("/api/plan", { method: "POST", body: JSON.stringify(formData(e.target)) });
    renderPlan(plan, $("#plan-out"));
  });
});

// ── Saved trips ──────────────────────────────────────────────────────────────
async function loadTrips() {
  const ul = $("#trips");
  try {
    const { trips } = await api("/api/trips");
    ul.replaceChildren();
    if (!trips.length) {
      const li = document.createElement("li");
      li.className = "muted";
      li.textContent = __("Noch nichts gemerkt.");
      ul.append(li);
      return;
    }
    for (const t of trips) {
      const li = document.createElement("li");
      const open = document.createElement("button");
      open.className = "link";
      open.textContent = t.title;
      open.addEventListener("click", async () => {
        const trip = await api(`/api/trips/${t.id}`);
        const out = $("#trip-out");
        if (trip.kind === "plan") renderPlan(trip.payload, out, { tripId: trip.id });
        else renderSuggestions(trip.payload, out, { saveable: false });
        out.scrollIntoView({ behavior: "smooth" });
      });
      const meta = document.createElement("span");
      meta.className = "muted";
      meta.textContent = new Date(t.created_at).toLocaleDateString(window.I18N.lang === "en" ? "en-GB" : "de-DE");
      const del = document.createElement("button");
      del.className = "ghost";
      del.textContent = __("Löschen");
      del.addEventListener("click", async () => {
        if (!confirm(__("Diese Reise löschen?"))) return;
        await api(`/api/trips/${t.id}`, { method: "DELETE" });
        $("#trip-out").replaceChildren();
        loadTrips();
      });
      li.append(open, meta, del);
      ul.append(li);
    }
  } catch (err) {
    toast(err.message);
  }
}

api("/healthz").then((h) => ($("#demo").hidden = !h.demo)).catch(() => {});

// Who is signed in, and how many requests are left today.
async function showMe() {
  try {
    const me = await api("/api/me");
    $("#me").textContent = me.email;
    const quota = $("#quota");
    quota.textContent = `${__("Heute noch")} ${me.remaining} ${__("von")} ${me.limit} ${__("Anfragen")}`;
    quota.hidden = false;
  } catch {
    /* api() already sent the page to the sign-in on a 401 */
  }
}
showMe();

$("#delete-account").addEventListener("click", async () => {
  if (!window.confirm(__("Konto und alle gespeicherten Reisen endgültig löschen?"))) return;
  const res = await fetch("/api/me", { method: "DELETE" });
  if (res.ok) window.location.href = "/";
  else window.alert(__("Das Löschen hat nicht geklappt. Bitte versuche es erneut oder schreib an info@infra-heroes.de."));
});

$("#logout").addEventListener("click", async () => {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = "/";
});
