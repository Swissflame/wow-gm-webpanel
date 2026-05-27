document.addEventListener("submit", (event) => {
  const form = event.target;
  const danger = form.closest(".danger");
  if (danger && !confirm("Diese Aktion setzt die Webpanel-Konfiguration zurück. Fortfahren?")) {
    event.preventDefault();
  }
});

document.addEventListener("click", (event) => {
  const tab = event.target.closest(".gm-tab");
  if (tab) {
    const id = tab.dataset.tab;
    document.querySelectorAll(".gm-tab").forEach((item) => item.classList.toggle("active", item.dataset.tab === id));
    document.querySelectorAll(".gm-tab-panel").forEach((item) => item.classList.toggle("active", item.dataset.tabPanel === id));
    return;
  }
  const favorite = event.target.closest(".favorite-toggle");
  if (favorite) {
    const favorites = readFavorites();
    const id = favorite.dataset.favorite;
    if (favorites.has(id)) favorites.delete(id);
    else favorites.add(id);
    localStorage.setItem("wowpanel.gmFavorites", JSON.stringify([...favorites]));
    syncFavorites();
    return;
  }
  const card = event.target.closest("[data-command]");
  if (!card) return;
  const input = document.querySelector("input[name='command']");
  if (input) {
    input.value = card.dataset.command;
    input.focus();
    input.scrollIntoView({ behavior: "smooth", block: "center" });
  }
});

document.addEventListener("mouseover", (event) => {
  const item = event.target.closest(".raw-command-chips [data-command]");
  const tooltip = document.querySelector("#gmTooltip");
  if (!item || !tooltip) return;
  const help = item.dataset.help || "Keine Beschreibung vorhanden.";
  const syntax = item.dataset.syntax || item.dataset.command;
  tooltip.innerHTML = `<strong>${syntax}</strong><pre>${escapeHtml(help)}</pre>`;
  tooltip.hidden = false;
});

document.addEventListener("mousemove", (event) => {
  const tooltip = document.querySelector("#gmTooltip");
  if (!tooltip || tooltip.hidden) return;
  const x = Math.min(event.clientX + 18, window.innerWidth - tooltip.offsetWidth - 18);
  const y = Math.min(event.clientY + 18, window.innerHeight - tooltip.offsetHeight - 18);
  tooltip.style.left = `${x}px`;
  tooltip.style.top = `${y}px`;
});

document.addEventListener("mouseout", (event) => {
  if (!event.target.closest(".raw-command-chips [data-command]")) return;
  const tooltip = document.querySelector("#gmTooltip");
  if (tooltip) tooltip.hidden = true;
});

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function readFavorites() {
  try {
    return new Set(JSON.parse(localStorage.getItem("wowpanel.gmFavorites") || "[]"));
  } catch {
    return new Set();
  }
}

function syncFavorites() {
  const favorites = readFavorites();
  document.querySelectorAll(".favorite-toggle").forEach((button) => {
    const active = favorites.has(button.dataset.favorite);
    button.classList.toggle("active", active);
    button.textContent = active ? "★" : "☆";
  });
  const target = document.querySelector("#favoriteActions");
  const empty = document.querySelector("#favoriteEmpty");
  if (!target) return;
  target.innerHTML = "";
  document.querySelectorAll(".action-card[data-action-id]").forEach((card) => {
    if (!favorites.has(card.dataset.actionId)) return;
    const clone = card.cloneNode(true);
    target.appendChild(clone);
  });
  if (empty) empty.style.display = target.children.length ? "none" : "block";
}

document.addEventListener("DOMContentLoaded", syncFavorites);

document.addEventListener("input", (event) => {
  if (event.target.id !== "configFilter") return;
  const needle = event.target.value.toLowerCase();
  document.querySelectorAll(".config-row").forEach((row) => {
    row.style.display = row.dataset.search.toLowerCase().includes(needle) ? "grid" : "none";
  });
});
