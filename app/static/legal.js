/* Footer with the legal links and a one-line cookie notice.
 *
 * The only cookie is the login session, which needs no consent, so this is a notice, not a
 * choice. It is shown once per browser; the choice to hide it is kept in localStorage. */
(function () {
  "use strict";

  var footer = document.createElement("footer");
  footer.className = "legal-footer";
  footer.innerHTML =
    '<a href="/impressum">' + __("Impressum") + '</a> · <a href="/datenschutz">' + __("Datenschutz") + "</a>";
  document.body.appendChild(footer);

  var KEY = "cookie-notice-seen";
  var seen = false;
  try { seen = window.localStorage.getItem(KEY) === "1"; } catch (e) { /* private mode: show it */ }
  if (seen) { return; }

  var bar = document.createElement("div");
  bar.className = "notice-bar";
  bar.setAttribute("role", "region");
  bar.setAttribute("aria-label", __("Hinweis zu Cookies"));
  bar.innerHTML =
    "<span>" + __("Wir nutzen nur ein technisch notwendiges Cookie für deine Anmeldung. Kein Tracking, keine Werbung.") +
    ' <a href="/datenschutz">' + __("Datenschutz") + "</a></span>";
  var ok = document.createElement("button");
  ok.type = "button";
  ok.className = "primary";
  ok.textContent = __("Verstanden");
  ok.addEventListener("click", function () {
    bar.hidden = true;
    try { window.localStorage.setItem(KEY, "1"); } catch (e) { /* hidden for this visit */ }
  });
  bar.appendChild(ok);
  document.body.appendChild(bar);
})();
