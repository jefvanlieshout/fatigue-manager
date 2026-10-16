"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const page = document.getElementById("print-page");
  const count = Number(page.dataset.count) || 30;
  const rowMm = 186 / count; // 7mm top + 10mm header + 186mm grid + 7mm bottom = 210mm
  page.style.setProperty("--row-height", rowMm + "mm");
  // Keep 7.5pt names and 6pt times for ordinary 07:00–21:30 weeks.
  // Denser ranges need smaller text to fit 30-minute slots on one A4 page.
  page.classList.toggle("print-compact", rowMm < 5.6);
  page.classList.toggle("print-dense", rowMm < 4.5);
  const palette = {
    "energy-low": page.dataset.lowColor, "energy-medium": page.dataset.mediumColor,
    "energy-high": page.dataset.highColor, "energy-restored": "#579cc4",
    "energy-unknown": "#9daab5"
  };
  for (const item of page.querySelectorAll(".print-event")) {
    const span = Math.max(1, Math.min(count, Number(item.dataset.span) || 1));
    const columns = Math.max(1, Number(item.dataset.columns) || 1);
    const lane = Math.max(0, Number(item.dataset.lane) || 0);
    item.style.height = (span * rowMm - 0.4) + "mm";
    item.style.left = "calc(" + lane * 100 / columns + "% + 0.2mm)";
    item.style.width = "calc(" + 100 / columns + "% - 0.4mm)";
    const key = Object.keys(palette).find(k => item.classList.contains(k));
    const color = palette[key] || palette["energy-unknown"];
    item.style.borderLeftColor = color;
    item.style.backgroundColor = color + "30";
  }
  const button = document.getElementById("print-button");
  if (button) button.addEventListener("click", () => window.print());
});
