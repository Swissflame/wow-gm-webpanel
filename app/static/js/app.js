document.addEventListener("submit", (event) => {
  const form = event.target;
  const danger = form.closest(".danger");
  if (danger && !confirm("Diese Aktion setzt die Webpanel-Konfiguration zurück. Fortfahren?")) {
    event.preventDefault();
  }
});

document.addEventListener("click", (event) => {
  const card = event.target.closest("[data-command]");
  if (!card) return;
  const input = document.querySelector("input[name='command']");
  if (input) {
    input.value = card.dataset.command;
    input.focus();
  }
});

document.addEventListener("input", (event) => {
  if (event.target.id !== "configFilter") return;
  const needle = event.target.value.toLowerCase();
  document.querySelectorAll(".config-row").forEach((row) => {
    row.style.display = row.dataset.search.toLowerCase().includes(needle) ? "grid" : "none";
  });
});
