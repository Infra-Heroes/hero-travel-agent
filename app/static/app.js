// Urlaubs-Agent page. Everything the model writes is set as textContent -
// never as HTML - so a suggestion can never inject markup into the page.

const INTERESTS = ["Strand", "Natur", "Wandern", "Kultur", "Städte", "Essen", "Familie", "Ruhe", "Abenteuer", "Wellness"];
const $ = (sel, root = document) => root.querySelector(sel);

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toast.t);
  toast.t = setTimeout(() => (el.hidden = true), 3500);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    ...options,
  });
  if (res.status === 401) {
    window.location.href = "/";
    throw new Error("Bitte anmelden.");
  }
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail) ? "Bitte die Eingaben prüfen." : body.detail;
    throw new Error(detail || `Fehler ${res.status}`);
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

const eur = (n) => new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);

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
    save.textContent = "Vorschläge merken";
    save.addEventListener("click", () =>
      busy(save, "Speichere…", async () => {
        const title = `Ideen: ${lastBrief?.when || "Reise"} (${data.suggestions.map((s) => s.destination.split(",")[0]).join(", ")})`;
        await api("/api/trips", { method: "POST", body: JSON.stringify({ title, kind: "suggestions", payload: data }) });
        toast("Gemerkt unter „Meine Reisen“");
      })
    );
    head.append(save);
  }
  target.append(head);

  const list = document.createElement("div");
  list.className = "suggestions";
  for (const s of data.suggestions) {
    const node = $("#t-suggestion").content.cloneNode(true);
    $(".dest", node).textContent = s.destination;
    $(".price", node).textContent = `ca. ${eur(s.total_estimate_eur)}`;
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
  busy(button, "Der Agent plant…", async () => {
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

// ── Day plan ─────────────────────────────────────────────────────────────────
function renderPlan(plan, target, { tripId = null } = {}) {
  target.replaceChildren();
  const wrap = document.createElement("div");
  wrap.className = "card plan";
  const h = document.createElement("h2");
  h.textContent = `${plan.days.length} Tage ${plan.destination}`;
  const ov = document.createElement("p");
  ov.textContent = plan.overview;
  const actions = document.createElement("div");
  actions.className = "actions";

  if (tripId) {
    const ics = document.createElement("a");
    ics.className = "button";
    ics.href = `/api/trips/${tripId}/calendar.ics`;
    ics.textContent = "In Kalender übernehmen";
    actions.append(ics);
  } else {
    const save = document.createElement("button");
    save.textContent = "Plan merken";
    save.addEventListener("click", () =>
      busy(save, "Speichere…", async () => {
        const trip = await api("/api/trips", {
          method: "POST",
          body: JSON.stringify({ title: `Tagesplan: ${plan.destination}`, kind: "plan", payload: plan }),
        });
        toast("Gemerkt unter „Meine Reisen“");
        renderPlan(plan, target, { tripId: trip.id });
      })
    );
    actions.append(save);
  }
  const print = document.createElement("button");
  print.textContent = "Drucken";
  print.addEventListener("click", () => window.print());
  actions.append(print);
  wrap.append(h, ov, actions);

  for (const d of plan.days) {
    const node = $("#t-day").content.cloneNode(true);
    $(".num", node).textContent = d.day;
    $(".theme", node).textContent = d.theme;
    $(".date", node).textContent = d.date;
    $(".morning", node).textContent = d.morning;
    $(".afternoon", node).textContent = d.afternoon;
    $(".evening", node).textContent = d.evening;
    $(".food", node).textContent = d.food_tip;
    $(".rain", node).textContent = d.bad_weather;
    $(".logistics", node).textContent = d.logistics;
    wrap.append(node);
  }
  const ph = document.createElement("h3");
  ph.textContent = "Packliste";
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
  busy(button, "Der Agent plant…", async () => {
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
      li.textContent = "Noch nichts gemerkt.";
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
      meta.textContent = new Date(t.created_at).toLocaleDateString("de-DE");
      const del = document.createElement("button");
      del.className = "ghost";
      del.textContent = "Löschen";
      del.addEventListener("click", async () => {
        if (!confirm("Diese Reise löschen?")) return;
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
    quota.textContent = `Heute noch ${me.remaining} von ${me.limit} Anfragen`;
    quota.hidden = false;
  } catch {
    /* api() already sent the page to the sign-in on a 401 */
  }
}
showMe();

$("#logout").addEventListener("click", async () => {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = "/";
});
