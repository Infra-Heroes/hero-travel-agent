/* German and English.
 *
 * The pages are written in German; that text is the key. For English, this file maps the
 * German sentence to its translation. Text in the page (text nodes, placeholder, title,
 * aria-label, meta description) is replaced once the page is loaded, and scripts ask
 * __("Deutscher Satz") for strings they build themselves.
 *
 * The language is the one the person chose (kept in localStorage), else the browser's.
 * Switching reloads the page: every string is then built in one language, with no half-
 * translated state to keep in step.
 */
(function () {
  "use strict";

  var KEY = "lang";

  function detect() {
    var saved = null;
    try { saved = window.localStorage.getItem(KEY); } catch (e) { /* private mode */ }
    if (saved === "de" || saved === "en") { return saved; }
    var nav = (navigator.language || "de").toLowerCase();
    return nav.indexOf("de") === 0 ? "de" : "en";
  }

  var lang = detect();
  document.documentElement.lang = lang;

  var EN = {
    // page titles and descriptions
    "Urlaubs-Agent: Reiseideen und Tagespläne": "Holiday agent: trip ideas and day plans",
    "Der Urlaubs-Agent schlägt dir drei passende Reiseziele vor und plant die Tage. Er bucht nichts.":
      "The holiday agent suggests three destinations that fit and plans the days. It books nothing.",
    "Urlaubs-Agent": "Holiday agent",
    "Impressum – Urlaubs-Agent": "Legal notice – Holiday agent",
    "Datenschutz – Urlaubs-Agent": "Privacy – Holiday agent",

    // landing
    "Dein persönlicher Reiseplaner": "Your personal trip planner",
    "Dein persönlicher Reiseplaner · bucht nichts, plant alles": "Your personal trip planner · books nothing, plans everything",
    "Zum Planer": "Open the planner",
    "Wohin soll die Reise gehen?": "Where do you want to go?",
    "Sag, wann du verreisen willst, mit wem und wie viel es kosten darf. Der Agent schlägt dir drei passende Ziele vor, mit Wetter, Anreise, Unterkunft und einer Kostenschätzung. Für das Ziel deiner Wahl plant er dir die Tage, bis zu zwei Wochen, samt Packliste und Kalenderdatei.":
      "Tell us when you want to travel, with whom and how much it may cost. The agent suggests three fitting destinations with weather, getting there, accommodation and a cost estimate. For the one you pick it plans the days, up to two weeks, with a packing list and a calendar file.",
    "Ideen finden:": "Find ideas:",
    "drei Ziele mit ehrlichen Einschränkungen": "three destinations, with honest caveats",
    "Tagesplan:": "Day plan:",
    "Vormittag, Nachmittag, Abend, Essen und Plan B bei Regen": "morning, afternoon, evening, food and a plan B for rain",
    "Meine Reisen:": "My trips:",
    "Pläne speichern, drucken, in den Kalender übernehmen": "save plans, print them, add them to your calendar",
    "Der Agent bucht nichts und verspricht keine Verfügbarkeit. Preise sind Schätzungen.":
      "The agent books nothing and promises no availability. Prices are estimates.",
    "Anmelden": "Sign in",
    "Du bist angemeldet": "You are signed in",
    "Ohne Passwort: Du bekommst einen Code per E-Mail.": "No password: we send you a code by e-mail.",
    "E-Mail-Adresse": "E-mail address",
    "Ich habe die": "I have read the",
    "Datenschutzerklärung": "privacy policy",
    "gelesen.": ".",
    "Code senden": "Send code",
    "Code aus der E-Mail": "Code from the e-mail",
    "Andere Adresse oder neuen Code": "Another address or a new code",
    "Mit der Anmeldung speichern wir deine E-Mail-Adresse, deine gespeicherten Reisen und wie oft du den Agenten nutzt. Mehr nicht.":
      "When you sign in we store your e-mail address, your saved trips and how often you use the agent. Nothing else.",
    "Bitte bestätige, dass du die Datenschutzerklärung gelesen hast.": "Please confirm that you have read the privacy policy.",
    "Bitte die Eingabe prüfen.": "Please check your input.",
    "Fehler": "Error",
    "Angemeldet als": "Signed in as",
    "Heute noch": "Left today:",
    "von": "of",
    "Anfragen": "requests",
    "Adresse": "Address",

    // app header and tabs
    "Demo-Modus": "Demo mode",
    "Abmelden": "Sign out",
    "Konto löschen": "Delete account",
    "Ideen finden": "Find ideas",
    "Tagesplan": "Day plan",
    "Meine Reisen": "My trips",
    "Konto und alle gespeicherten Reisen endgültig löschen?": "Delete your account and all saved trips for good?",
    "Das Löschen hat nicht geklappt. Bitte versuche es erneut oder schreib an info@infra-heroes.de.":
      "Deleting did not work. Please try again or write to info@infra-heroes.de.",

    // brief form
    "Wohin soll's gehen?": "Where to?",
    "So geht's": "How it works",
    "Sag, wann, wie lange, mit wem und wie viel es kosten darf. Je genauer, desto besser die Vorschläge.":
      "Say when, for how long, with whom and how much it may cost. The more precise, the better the suggestions.",
    "Wähle ein paar Vorlieben und schreibe unter „Sonstiges“, was dir wichtig ist (oder tippe auf einen Vorschlag).":
      "Pick a few interests and write what matters to you under “Other” (or tap a suggestion).",
    "Du bekommst drei Ziele. Für eins davon erstellst du den Tagesplan und exportierst ihn als PDF oder in deinen Kalender.":
      "You get three destinations. For one of them you create the day plan and export it as a PDF or to your calendar.",
    "Der Agent bucht nichts. Preise sind Schätzungen. Jede Anfrage zählt zu deinem Tageslimit.":
      "The agent books nothing. Prices are estimates. Every request counts towards your daily limit.",
    "Wann": "When",
    "Monat, Ferien oder Datum": "Month, holidays or date",
    "z. B. Herbstferien, Mai 2027": "e.g. autumn break, May 2027",
    "Nächte": "Nights",
    "1 bis 30": "1 to 30",
    "Budget gesamt (€)": "Total budget (€)",
    "für alle zusammen, inkl. Anreise": "for everyone, travel included",
    "Abreise ab": "Departing from",
    "Ort oder Flughafen": "Place or airport",
    "z. B. Frankfurt": "e.g. Frankfurt",
    "Erwachsene": "Adults",
    "Kinder": "Children",
    "Vorlieben": "Interests",
    "Sonstiges": "Other",
    "z. B. nicht zu weit fliegen, Kind 6 Jahre, gerne Natur": "e.g. not too far, child aged 6, nature preferred",
    "Vorschläge für Sonstiges": "Suggestions for “Other”",
    "3 Vorschläge holen": "Get 3 suggestions",
    "Beispiel ausfüllen": "Fill in an example",
    "Der Agent plant…": "The agent is planning…",
    "Das dauert einen Moment. Tagespläne brauchen bis zu zwei Minuten.": "This takes a moment. Day plans can take up to two minutes.",
    "Noch dabei. Längere Pläne brauchen etwas mehr Zeit.": "Still working. Longer plans take a little more time.",
    "Gleich geschafft. Bitte die Seite nicht schließen.": "Almost there. Please keep this page open.",
    "Es dauert ungewöhnlich lange. Wenn nichts kommt, bitte nochmal versuchen.": "It is taking unusually long. If nothing arrives, please try again.",
    "Der Server hat nicht richtig geantwortet": "The server did not answer properly",
    "Bitte gleich nochmal versuchen.": "Please try again in a moment.",
    "Keine Verbindung zum Server oder zu lange gewartet. Bitte nochmal versuchen.": "No connection to the server, or waited too long. Please try again.",
    "Speichere…": "Saving…",

    // plan form
    "Tagesplan erstellen": "Create day plan",
    "Ziel": "Destination",
    "z. B. Lissabon": "e.g. Lisbon",
    "Stadt oder Region, mit Land bei Verwechslung (Valencia, Spanien)": "City or region, with the country if it could be confused (Valencia, Spain)",
    "Tage": "Days",
    "Startdatum": "Start date",
    "Tempo": "Pace",
    "entspannt": "relaxed",
    "ausgewogen": "balanced",
    "aktiv": "active",
    "z. B. Ankunft erst abends, kein Auto": "e.g. arriving late, no car",

    // interests and note ideas
    "Strand": "Beach", "Natur": "Nature", "Wandern": "Hiking", "Kultur": "Culture", "Städte": "Cities",
    "Essen": "Food", "Familie": "Family", "Ruhe": "Quiet", "Abenteuer": "Adventure", "Wellness": "Wellness",
    "Mit Kleinkind, kurze Wege": "With a toddler, short distances",
    "Nicht zu weit fliegen": "Not too far to fly",
    "Ohne Mietwagen": "No rental car",
    "Mit Hund": "With a dog",
    "Barrierearm": "Step-free access",
    "Eher ruhig, wenig Touristen": "Rather quiet, few tourists",
    "Gutes Essen ist wichtig": "Good food matters",
    "Viel draußen, wenn möglich Wandern": "Lots of outdoors, hiking if possible",
    "Badewetter wichtig": "Swimming weather matters",
    "Kulturprogramm bei Regen": "Culture programme if it rains",
    "Ankunft erst abends": "Arriving in the evening",
    "Vegetarisch": "Vegetarian",
    "Nicht zu weit fliegen, Kind 6 Jahre": "Not too far to fly, child aged 6",

    // periods
    "Osterferien": "Easter holidays", "Pfingstferien": "Whitsun holidays", "Sommerferien": "Summer holidays",
    "Herbstferien": "Autumn break", "Weihnachtsferien": "Christmas holidays", "Wochenende": "Weekend",
    "Langes Wochenende": "Long weekend",
    "Januar": "January", "Februar": "February", "März": "March", "April": "April", "Mai": "May", "Juni": "June",
    "Juli": "July", "August": "August", "September": "September", "Oktober": "October", "November": "November",
    "Dezember": "December",

    // suggestions
    "Wetter": "Weather", "Anreise": "Getting there", "Unterkunft": "Accommodation", "Highlights": "Highlights",
    "Kostenschätzung": "Cost estimate", "Tagesplan dafür": "Day plan for this",
    "Vorschläge merken": "Save suggestions", "Gemerkt unter „Meine Reisen“": "Saved under “My trips”",
    "ca.": "approx.",
    "Ideen": "Ideas",
    "Reise": "Trip",

    // day plan
    "Vormittag": "Morning", "Nachmittag": "Afternoon", "Abend": "Evening",
    "Essen:": "Food:", "Bei Regen:": "If it rains:", "Wege:": "Getting around:",
    "Packliste": "Packing list",
    "Plan merken": "Save plan",
    "Tabellenansicht": "Table view",
    "Kartenansicht": "Card view",
    "Als PDF speichern": "Save as PDF",
    "Öffnet den Druckdialog: dort „Als PDF speichern“ wählen": "Opens the print dialog: choose “Save as PDF” there",
    "In Kalender": "To calendar",
    "In Kalender übernehmen": "Add to calendar",
    "Kalenderdatei (.ics), ganze Tage": "Calendar file (.ics), all-day entries",
    "Kalenderdatei (.ics), mit Uhrzeiten": "Calendar file (.ics), with times",
    "Google Kalender, pro Tag:": "Google Calendar, per day:",
    "Tag": "Day", "Datum": "Date", "Thema": "Theme", "Wetterfest": "Rain plan",
    "Tage in": "days in",

    // trips
    "Gespeicherte Vorschläge und Tagespläne. Nur du siehst sie.": "Saved suggestions and day plans. Only you can see them.",
    "Noch nichts gemerkt.": "Nothing saved yet.",
    "Löschen": "Delete",
    "Diese Reise löschen?": "Delete this trip?",
    "Heute noch": "Left today:",

    // footer and notice
    "Impressum": "Legal notice", "Datenschutz": "Privacy", "Startseite": "Home",
    "Hinweis zu Cookies": "Cookie notice",
    "Wir nutzen nur ein technisch notwendiges Cookie für deine Anmeldung. Kein Tracking, keine Werbung.":
      "We only use one technically necessary cookie for your sign-in. No tracking, no ads.",
    "Verstanden": "Got it"
  };

  // Strings the scripts compose out of several parts.
  function __(german) {
    if (lang === "de") { return german; }
    return Object.prototype.hasOwnProperty.call(EN, german) ? EN[german] : german;
  }

  function norm(s) { return s.replace(/\s+/g, " ").trim(); }

  var ATTRS = ["placeholder", "title", "aria-label", "alt"];

  function translateNode(root) {
    if (lang === "de") { return; }
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var node;
    var todo = [];
    while ((node = walker.nextNode())) { todo.push(node); }
    todo.forEach(function (n) {
      var parent = n.parentNode;
      if (!parent || /^(SCRIPT|STYLE)$/.test(parent.nodeName)) { return; }
      var key = norm(n.nodeValue);
      if (key && Object.prototype.hasOwnProperty.call(EN, key)) {
        var lead = /^\s/.test(n.nodeValue) ? " " : "";
        var trail = /\s$/.test(n.nodeValue) ? " " : "";
        n.nodeValue = lead + EN[key] + trail;
      }
    });
    var els = root.querySelectorAll ? root.querySelectorAll("*") : [];
    Array.prototype.forEach.call(els, function (el) {
      ATTRS.forEach(function (a) {
        var v = el.getAttribute(a);
        if (v && Object.prototype.hasOwnProperty.call(EN, norm(v))) { el.setAttribute(a, EN[norm(v)]); }
      });
    });
  }

  function translatePage() {
    if (lang === "de") { return; }
    translateNode(document.body);
    var t = document.title;
    if (Object.prototype.hasOwnProperty.call(EN, t)) { document.title = EN[t]; }
    var meta = document.querySelector('meta[name="description"]');
    if (meta && Object.prototype.hasOwnProperty.call(EN, meta.content)) { meta.content = EN[meta.content]; }
  }

  function addSwitch() {
    var host = document.querySelector(".top") || document.body;
    var box = document.createElement("div");
    box.className = "lang-switch";
    box.setAttribute("role", "group");
    box.setAttribute("aria-label", "Sprache / Language");
    ["de", "en"].forEach(function (code) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = code.toUpperCase();
      b.lang = code;
      b.setAttribute("aria-pressed", String(code === lang));
      b.addEventListener("click", function () {
        if (code === lang) { return; }
        try { window.localStorage.setItem(KEY, code); } catch (e) { /* choice lasts for this load only */ }
        window.location.reload();
      });
      box.appendChild(b);
    });
    host.appendChild(box);
  }

  window.__ = __;
  window.I18N = { lang: lang, translate: translateNode, __: __ };

  function start() {
    translatePage();
    addSwitch();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
