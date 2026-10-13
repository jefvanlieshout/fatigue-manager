"use strict";
function updateEnergy() {
  const before = document.getElementById("energy_before");
  const after = document.getElementById("energy_after");
  if (!before || !after) return;
  const b = Number(before.value), a = Number(after.value);
  document.getElementById("before_value").textContent = String(b);
  document.getElementById("after_value").textContent = String(a);
  const nl = document.documentElement.lang.startsWith("nl");
  const delta = a - b;
  const result = document.getElementById("energy_delta");
  result.textContent = (delta > 0 ? "+" : "") + delta + " " + (nl ? "punten" : "points");
  result.classList.toggle("positive", delta > 0);
  result.classList.toggle("negative", delta < 0);
  document.getElementById("energy_description").textContent =
    delta > 0 ? (nl ? "Energie hersteld" : "Energy restored") :
    delta < 0 ? (nl ? "Energie verbruikt" : "Energy used") :
    (nl ? "Geen verandering" : "No change");
}
document.addEventListener("DOMContentLoaded", function () {
  const before = document.getElementById("energy_before");
  const after = document.getElementById("energy_after");
  if (before && after) {
    before.addEventListener("input", updateEnergy);
    after.addEventListener("input", updateEnergy);
    updateEnergy();
  }
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  // Selecting a timetable slot opens the small planning dialog.
  // Without dialog support or JavaScript, the link opens that day with a preselected time.
  const dialog = document.getElementById("quick-plan");
  if (dialog && typeof dialog.showModal === "function") {
    const dayInput = document.getElementById("quick-plan-day");
    const timeInput = document.getElementById("quick-plan-time");
    const nameInput = document.getElementById("quick-plan-name");
    const estimateInput = document.getElementById("quick-plan-delta");
    document.querySelectorAll(".calendar-slot-add").forEach(function (link) {
      link.addEventListener("click", function (event) {
        event.preventDefault();
        dayInput.value = link.dataset.day;
        timeInput.value = link.dataset.time;
        nameInput.value = "";
        estimateInput.value = "";
        dialog.querySelector("details").open = false;
        dialog.showModal();
        nameInput.focus();
      });
    });
    dialog.querySelector("[data-close-plan]").addEventListener("click", function () {
      dialog.close();
    });
    // Native dialog closes via Escape. Clicking its backdrop also closes it.
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) dialog.close();
    });
  }

  // Show a useful daytime range first while keeping midnight through 23:30
  // available by scrolling upward or downward.
  const scrollPane = document.getElementById("calendar-scroll");
  if (scrollPane) {
    const storageKey = "fatigue-week-position:" + scrollPane.dataset.week;
    let previousPosition = null;
    try {
      previousPosition = JSON.parse(sessionStorage.getItem(storageKey) || "null");
    } catch (_) {
      // The calendar works normally even when browser storage is unavailable.
    }
    if (previousPosition && Number.isFinite(previousPosition.top) &&
        Number.isFinite(previousPosition.left)) {
      scrollPane.scrollTop = previousPosition.top;
      scrollPane.scrollLeft = previousPosition.left;
    } else {
      const first = scrollPane.querySelector("[data-initial-scroll]");
      const header = scrollPane.querySelector("thead");
      if (first && header) {
        scrollPane.scrollTop = Math.max(0,
          first.getBoundingClientRect().top -
          scrollPane.getBoundingClientRect().top -
          header.getBoundingClientRect().height - 8);
      }
    }
    scrollPane.addEventListener("scroll", function () {
      try {
        sessionStorage.setItem(storageKey, JSON.stringify({
          top: scrollPane.scrollTop, left: scrollPane.scrollLeft
        }));
      } catch (_) {
        // Private mode or disabled storage should not interrupt planning.
      }
    }, { passive: true });
  }
});
