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
});
