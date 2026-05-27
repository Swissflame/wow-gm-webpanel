document.addEventListener("submit", (event) => {
  const form = event.target;
  const danger = form.closest(".danger");
  if (danger && !confirm("Diese Aktion setzt die Webpanel-Konfiguration zurück. Fortfahren?")) {
    event.preventDefault();
  }
});
