document.addEventListener("submit", (event) => {
  const form = event.target;
  const danger = form.closest(".danger");
  if (!danger) return;
  const message = form.matches("[action*='/delete']")
    ? "Diesen Eintrag wirklich endgueltig loeschen? Diese Aktion entfernt auch zugehoerige Daten."
    : "Diese Aktion setzt die Webpanel-Konfiguration zurueck. Fortfahren?";
  if (!confirm(message)) event.preventDefault();
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  const form = event.target.closest?.("form.login-form");
  if (!form) return;
  event.preventDefault();
  form.requestSubmit();
});

document.addEventListener("click", (event) => {
  const tab = event.target.closest(".gm-tab");
  if (tab) {
    const id = tab.dataset.tab;
    document.querySelectorAll(".gm-tab").forEach((item) => item.classList.toggle("active", item.dataset.tab === id));
    document.querySelectorAll(".gm-tab-panel").forEach((item) => item.classList.toggle("active", item.dataset.tabPanel === id));
    document.querySelectorAll("input[name='active_tab']").forEach((input) => {
      input.value = id;
    });
    try { sessionStorage.setItem("wowpanel.gmActiveTab", id); } catch {}
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
    saveFavorites(favorites);
    return;
  }
  const card = event.target.closest("[data-command]");
  if (!card) return;
  const input = document.querySelector("input[name='command']");
  if (input) {
    input.value = card.dataset.command;
    input.focus();
    input.closest("form")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});

document.addEventListener("mouseover", (event) => {
  const item = event.target.closest(".raw-command-chips [data-command]");
  const tooltip = document.querySelector("#gmTooltip");
  if (!item || !tooltip) return;
  const syntax = item.dataset.syntax || item.dataset.command;
  const summary = item.dataset.summary || "Fuehrt diesen AzerothCore-Befehl aus.";
  const output = item.dataset.output || "Die Antwort erscheint oben im Webpanel in der Ergebnisbox.";
  const notes = item.dataset.notes || "";
  tooltip.innerHTML = `
    <strong>${escapeHtml(syntax)}</strong>
    <dl>
      <dt>Was passiert?</dt><dd>${escapeHtml(summary)}</dd>
      <dt>Syntax</dt><dd><code>${escapeHtml(syntax)}</code></dd>
      <dt>Ausgabe</dt><dd>${escapeHtml(output)}</dd>
      ${notes ? `<dt>Hinweis</dt><dd>${escapeHtml(notes)}</dd>` : ""}
    </dl>`;
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
  const workbench = document.querySelector(".gm-workbench[data-server-favorites]");
  if (workbench && !workbench.dataset.favoritesLoaded) {
    workbench.dataset.favoritesLoaded = "1";
    try {
      const serverFavorites = JSON.parse(workbench.dataset.serverFavorites || "[]");
      const localFavorites = JSON.parse(localStorage.getItem("wowpanel.gmFavorites") || "[]");
      const merged = new Set([...serverFavorites, ...localFavorites]);
      localStorage.setItem("wowpanel.gmFavorites", JSON.stringify([...merged]));
      if (localFavorites.length && localFavorites.length !== serverFavorites.length) {
        setTimeout(() => saveFavorites(merged), 0);
      }
      return merged;
    } catch {}
  }
  try {
    return new Set(JSON.parse(localStorage.getItem("wowpanel.gmFavorites") || "[]"));
  } catch {
    return new Set();
  }
}

function saveFavorites(favorites) {
  const csrf = document.querySelector("input[name='csrf']")?.value;
  if (!csrf) return;
  fetch("/gm/favorites", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ csrf, favorites: [...favorites].join(",") }),
  }).catch(() => {});
}

function syncFavorites() {
  const favorites = readFavorites();
  document.querySelectorAll(".favorite-toggle").forEach((button) => {
    const active = favorites.has(button.dataset.favorite);
    button.classList.toggle("active", active);
    button.textContent = active ? "â˜…" : "â˜†";
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
document.addEventListener("DOMContentLoaded", () => {
  if (document.querySelector(".ah-style-page")) {
    document.body.classList.add("items-browser-active");
  }
  const params = new URLSearchParams(window.location.search);
  const id = params.get("tab") || sessionStorage.getItem("wowpanel.gmActiveTab");
  if (!id) return;
  document.querySelectorAll(".gm-tab").forEach((item) => item.classList.toggle("active", item.dataset.tab === id));
  document.querySelectorAll(".gm-tab-panel").forEach((item) => item.classList.toggle("active", item.dataset.tabPanel === id));
  document.querySelectorAll("input[name='active_tab']").forEach((input) => {
    input.value = id;
  });
});

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-auto-submit='true']").forEach((form) => {
    let timer = null;
    const submit = (delay = 0) => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const page = form.querySelector("input[name='page']");
        if (page) page.value = "1";
        form.requestSubmit();
      }, delay);
    };
    form.querySelectorAll("input,select").forEach((field) => {
      if (field.type === "hidden") return;
      field.addEventListener("change", () => submit(0));
      field.addEventListener("input", () => submit(450));
    });
  });
});

document.addEventListener("input", (event) => {
  if (event.target.id !== "configFilter") return;
  const needle = event.target.value.toLowerCase();
  document.querySelectorAll(".config-row,.main-config-field").forEach((row) => {
    row.style.display = row.dataset.search.toLowerCase().includes(needle) ? "grid" : "none";
  });
});
