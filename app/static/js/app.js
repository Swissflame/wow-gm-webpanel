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
  }
});

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
