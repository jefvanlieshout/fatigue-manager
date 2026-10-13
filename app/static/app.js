"use strict";

function updateEnergy() {
  const before = document.getElementById("energy_before");
  const after = document.getElementById("energy_after");
  if (!before || !after) return;

  const b = Number(before.value);
  const a = Number(after.value);
  document.getElementById("before_value").textContent = String(b);
  document.getElementById("after_value").textContent = String(a);

  for (const slider of [before, after]) {
    const value = Number(slider.value);
    slider.style.setProperty("--position", value + "%");
  }

  const delta = a - b;
  const result = document.getElementById("energy_delta");
  result.textContent = (delta > 0 ? "+" : "") + delta + " punten";
  result.classList.toggle("positive", delta > 0);
  result.classList.toggle("negative", delta < 0);
  const description = document.getElementById("energy_description");
  description.textContent =
    delta > 0 ? "Energie hersteld" :
    delta < 0 ? "Energie verbruikt" : "Geen verandering";
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
});
