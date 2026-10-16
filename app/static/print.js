"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const page = document.getElementById("print-page");
  const count = Number(page.dataset.count) || 30;
  const rowMm = 181 / count; // 12mm title + 17mm header + 181mm grid = full 210mm
  page.style.setProperty("--row-height", rowMm + "mm");
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
