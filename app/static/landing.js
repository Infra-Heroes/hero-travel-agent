// The public page: sign in with an e-mail address and a one-time code.
// Nothing the server sends is ever set as HTML, only as text.

const $ = (sel) => document.querySelector(sel);
const ask = $("#ask");
const enter = $("#enter");
const message = $("#message");

function say(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
  message.hidden = !text;
}

async function post(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? "Bitte die Eingabe prüfen." : data.detail;
    throw new Error(detail || `Fehler ${res.status}`);
  }
  return data;
}

function busy(form, on) {
  form.querySelectorAll("button").forEach((b) => (b.disabled = on));
}

// Already signed in: offer the planner instead of the form.
fetch("/api/me", { headers: { Accept: "application/json" } })
  .then((res) => (res.ok ? res.json() : null))
  .then((me) => {
    if (!me) return;
    $("#open-app").hidden = false;
    $("#signin-title").textContent = "Du bist angemeldet";
    ask.hidden = true;
    say(`Angemeldet als ${me.email}. Heute noch ${me.remaining} von ${me.limit} Anfragen.`);
  })
  .catch(() => {});

ask.addEventListener("submit", async (event) => {
  event.preventDefault();
  say("");
  if (!$("#privacy").checked) {
    say("Bitte bestätige, dass du die Datenschutzerklärung gelesen hast.", true);
    return;
  }
  busy(ask, true);
  try {
    const email = $("#email").value.trim();
    const answer = await post("/api/auth/request", { email });
    $("#sent").textContent = `${answer.message} Adresse: ${email}`;
    ask.hidden = true;
    enter.hidden = false;
    $("#code").focus();
  } catch (err) {
    say(err.message, true);
  } finally {
    busy(ask, false);
  }
});

enter.addEventListener("submit", async (event) => {
  event.preventDefault();
  say("");
  busy(enter, true);
  try {
    await post("/api/auth/verify", { email: $("#email").value.trim(), code: $("#code").value.trim() });
    window.location.href = "/app";
  } catch (err) {
    say(err.message, true);
    busy(enter, false);
  }
});

$("#again").addEventListener("click", () => {
  enter.hidden = true;
  ask.hidden = false;
  $("#code").value = "";
  say("");
});
