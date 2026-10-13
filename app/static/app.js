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

  // Render one event as a block spanning all selected half-hour rows.
  // CSSOM assignments work with our strict self-hosted style Content Security Policy.
  document.querySelectorAll(".calendar-event[data-span]").forEach(function (item) {
    const spans = Math.max(1, Math.min(48, Number(item.dataset.span)));
    const lanes = Math.max(1, Number(item.dataset.columns));
    const lane = Math.max(0, Number(item.dataset.lane));
    item.classList.add("calendar-event-positioned");
    item.style.height = (spans * 36 - 4) + "px";
    item.style.left = "calc(" + (lane * 100 / lanes) + "% + 3px)";
    item.style.width = "calc(" + (100 / lanes) + "% - 6px)";
  });

  const dialog = document.getElementById("quick-plan");
  if (dialog && typeof dialog.showModal === "function") {
    const dayInput = document.getElementById("quick-plan-day");
    const timeInput = document.getElementById("quick-plan-time");
    const endInput = document.getElementById("quick-plan-end");
    const nameInput = document.getElementById("quick-plan-name");
    const estimateInput = document.getElementById("quick-plan-delta");
    const modeInput = document.getElementById("quick-plan-mode");
    const actualFields = document.getElementById("quick-actual-fields");
    const beforeInput = document.getElementById("quick-energy-before");
    const afterInput = document.getElementById("quick-energy-after");
    const estimateSection = document.getElementById("quick-estimate-section");
    const submitButton = document.getElementById("quick-submit");
    const slots = Array.from(document.querySelectorAll(".calendar-slot-add"));

    function toMinutes(text) {
      const parts = text.split(":").map(Number);
      return parts[0] * 60 + parts[1];
    }
    function toTime(minutes) {
      const capped = Math.min(1439, Math.max(0, minutes));
      return String(Math.floor(capped / 60)).padStart(2, "0") + ":" +
        String(capped % 60).padStart(2, "0");
    }
    function setMode() {
      const completed = modeInput.value === "completed";
      actualFields.hidden = !completed;
      beforeInput.required = completed;
      afterInput.required = completed;
      estimateSection.hidden = completed;
      submitButton.textContent = completed ?
        submitButton.dataset.completeLabel : submitButton.dataset.planLabel;
    }
    function validateTimes() {
      const invalid = endInput.value !== "" && timeInput.value !== "" &&
        toMinutes(endInput.value) <= toMinutes(timeInput.value);
      endInput.setCustomValidity(invalid ?
        (document.documentElement.lang === "nl" ?
          "Eindtijd moet later dan starttijd zijn." :
          "End time must be later than start time.") : "");
    }
    modeInput.addEventListener("change", setMode);
    timeInput.addEventListener("change", validateTimes);
    endInput.addEventListener("change", validateTimes);
    function openPlan(day, start, end) {
      dayInput.value = day;
      timeInput.value = start;
      endInput.value = end || toTime(toMinutes(start) + 30);
      nameInput.value = "";
      estimateInput.value = "";
      beforeInput.value = "";
      afterInput.value = "";
      modeInput.value = "planned";
      estimateSection.open = false;
      setMode();
      validateTimes();
      dialog.showModal();
      nameInput.focus();
    }
    // Mouse/pen: drag across adjacent slots in the same column.
    // Touch: native swipe scrolling is preserved; tap once and set the end time.
    let drag = null;
    let suppressClick = false;
    function clearHighlight() {
      slots.forEach(slot => slot.classList.remove("slot-selected"));
    }
    function updateHighlight() {
      clearHighlight();
      if (!drag) return;
      const lo = Math.min(drag.start, drag.last);
      const hi = Math.max(drag.start, drag.last);
      slots.forEach(function (slot) {
        const minute = toMinutes(slot.dataset.time);
        if (slot.dataset.day === drag.day && minute >= lo && minute <= hi) {
          slot.classList.add("slot-selected");
        }
      });
    }
    slots.forEach(function (link) {
      link.addEventListener("pointerdown", function (event) {
        if (event.pointerType === "touch" || event.button !== 0) return;
        drag = { day: link.dataset.day, start: toMinutes(link.dataset.time),
                 last: toMinutes(link.dataset.time), moved: false };
        updateHighlight();
      });
      link.addEventListener("pointerenter", function () {
        if (!drag || drag.day !== link.dataset.day) return;
        const last = toMinutes(link.dataset.time);
        if (last !== drag.start) drag.moved = true;
        drag.last = last;
        updateHighlight();
      });
      link.addEventListener("click", function (event) {
        event.preventDefault();
        if (suppressClick) return;
        openPlan(link.dataset.day, link.dataset.time);
      });
    });
    document.addEventListener("pointerup", function () {
      if (!drag) return;
      const selected = drag;
      drag = null;
      clearHighlight();
      if (selected.moved) {
        const start = Math.min(selected.start, selected.last);
        const end = Math.max(selected.start, selected.last) + 30;
        suppressClick = true;
        openPlan(selected.day, toTime(start), toTime(end));
        setTimeout(function () { suppressClick = false; }, 0);
      }
    });
    document.addEventListener("pointercancel", function () {
      drag = null;
      clearHighlight();
    });
    dialog.querySelector("[data-close-plan]").addEventListener("click", function () {
      dialog.close();
    });
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) dialog.close();
    });
    setMode();
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
