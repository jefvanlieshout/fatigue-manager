"use strict";
/* Fatigue Manager: explicit browser-local light/dark choice. No automatic mode. */
(function () {
  const STORAGE_KEY = "fatigue-manager-theme";
  const root = document.documentElement;

  function readTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
    } catch (_) {
      return "light"; // Private modes and blocked storage still work.
    }
  }

  function applyTheme(theme) {
    const dark = theme === "dark";
    root.dataset.theme = dark ? "dark" : "light";
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", dark ? "#101b1c" : "#edf5f0");
    const toggle = document.getElementById("theme-toggle");
    if (toggle) {
      const nextLabel = dark ? toggle.dataset.lightLabel : toggle.dataset.darkLabel;
      toggle.setAttribute("aria-label", nextLabel);
      toggle.setAttribute("aria-pressed", String(dark));
      toggle.title = nextLabel;
    }
  }

  // Execute in <head> BEFORE the stylesheet to avoid a bright flash at night.
  applyTheme(readTheme());

  document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("theme-toggle");
    applyTheme(readTheme());
    if (!toggle) return;
    toggle.addEventListener("click", function () {
      const next = root.dataset.theme === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch (_) {
        // Manual toggle still works for this page if storage is disabled.
      }
      applyTheme(next);
    });
  });

  // Keep two tabs of the same site consistent after a manual change.
  window.addEventListener("storage", function (event) {
    if (event.key === STORAGE_KEY || event.key === null) applyTheme(readTheme());
  });
})();
