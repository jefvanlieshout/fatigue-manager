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
    const kindInput = document.getElementById("quick-event-kind");
    const idInput = document.getElementById("quick-event-id");
    const repeatSection = document.getElementById("quick-repeat-section");
    const repeatInput = document.getElementById("quick-repeat");
    const repeatDays = document.getElementById("quick-repeat-days");
    const repeatUntil = document.getElementById("quick-repeat-until");
    const manageActions = document.getElementById("quick-manage-actions");
    const deleteSeriesButton = document.getElementById("quick-delete-series");
    const dialogTitle = document.getElementById("quick-plan-title");
    const quickForm = document.getElementById("quick-plan-form");
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
      if (completed && kindInput.value === "new") {
        repeatInput.value = "none";
        setRepeatDays();
      }
      repeatSection.hidden = completed || kindInput.value !== "new";
      modeInput.options[0].disabled = kindInput.value === "recorded";
      submitButton.textContent = kindInput.value === "new" ?
        (completed ? submitButton.dataset.completeLabel : submitButton.dataset.planLabel) :
        submitButton.dataset.editLabel;
    }
    function setRepeatDays() {
      repeatDays.hidden = repeatInput.value !== "custom";
    }
    repeatInput.addEventListener("change", setRepeatDays);
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
      kindInput.value = "new";
      idInput.value = "0";
      dayInput.readOnly = false;
      dialogTitle.textContent = submitButton.dataset.newTitle;
      repeatInput.value = "none";
      repeatUntil.value = "";
      repeatSection.open = false;
      repeatSection.hidden = false;
      repeatDays.querySelectorAll('input[type="checkbox"]').forEach(box => box.checked = false);
      setRepeatDays();
      manageActions.hidden = true;
      nameInput.value = "";
      const priorActivity = document.getElementById("quick-recent-activity");
      if (priorActivity) priorActivity.value = "";
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
    function editEvent(link) {
      const data = link.dataset;
      const when = data.eventStart || "09:00";
      openPlan(data.eventDay, when, data.eventEnd || toTime(toMinutes(when) + 30));
      kindInput.value = data.eventKind;
      idInput.value = data.eventId;
      dialogTitle.textContent = submitButton.dataset.editTitle;
      nameInput.value = data.eventName || "";
      const priorActivity = document.getElementById("quick-recent-activity");
      if (priorActivity) priorActivity.value = "";
      estimateInput.value = data.eventEstimate || "";
      beforeInput.value = data.eventBefore || "";
      afterInput.value = data.eventAfter || "";
      modeInput.value = data.eventKind === "recorded" ? "completed" : "planned";
      dayInput.readOnly = data.eventKind === "recurring";
      manageActions.hidden = false;
      deleteSeriesButton.hidden = data.eventKind !== "recurring";
      setMode();
      nameInput.focus();
    }
    document.querySelectorAll(".calendar-event[data-event-kind]").forEach(function(link) {
      link.addEventListener("click", function(event) {
        event.preventDefault();
        editEvent(link);
      });
    });
    quickForm.addEventListener("submit", function(event) {
      const action = event.submitter && event.submitter.value;
      if (action !== "delete_one" && action !== "delete_series") return;
      const isSeries = action === "delete_series";
      const nl = document.documentElement.lang === "nl";
      const message = isSeries ?
        (nl ? quickForm.dataset.confirmSeriesNl : quickForm.dataset.confirmSeriesEn) :
        (nl ? quickForm.dataset.confirmDeleteNl : quickForm.dataset.confirmDeleteEn);
      if (!window.confirm(message)) event.preventDefault();
    });
    // Select a range by POSITION, not pointerenter: browsers otherwise start
    // dragging the anchor element and stop emitting events on successive links.
    // Touch remains native scrolling; users can tap and edit start/end manually.
    const scrollPane = document.getElementById("calendar-scroll");
    const tbody = scrollPane ? scrollPane.querySelector(".calendar-table tbody") : null;
    let drag = null;
    let mousePosition = null;
    let autoScrollFrame = null;
    let suppressClickUntil = 0;

    const recentSelect = document.getElementById("quick-recent-activity");
    if (recentSelect) {
      recentSelect.addEventListener("change", function () {
        if (recentSelect.value) nameInput.value = recentSelect.value;
        nameInput.focus();
      });
    }
    function clearHighlight() {
      slots.forEach(slot => slot.classList.remove("slot-selected"));
    }
    function highlightRange() {
      if (!drag) return;
      const first = Math.min(drag.startIndex, drag.lastIndex);
      const last = Math.max(drag.startIndex, drag.lastIndex);
      for (const slot of slots) {
        const row = slot.closest("tr");
        slot.classList.toggle("slot-selected",
          slot.dataset.day === drag.day && row &&
          row.sectionRowIndex >= first && row.sectionRowIndex <= last);
      }
    }
    function hoverAt(x, y) {
      if (!drag || !tbody || !tbody.rows.length) return;
      const columnCell = tbody.rows[0].cells[drag.column];
      if (!columnCell) return;
      const colRect = columnCell.getBoundingClientRect();
      // Never change the selected day while dragging.
      if (x < colRect.left || x >= colRect.right) return;
      const bounds = tbody.getBoundingClientRect();
      const rowHeight = tbody.rows[0].getBoundingClientRect().height;
      if (!rowHeight) return;
      const rowIndex = Math.max(0, Math.min(tbody.rows.length - 1,
        Math.floor((y - bounds.top) / rowHeight)));
      if (rowIndex !== drag.lastIndex) {
        drag.lastIndex = rowIndex;
        highlightRange();
      }
    }
    function stopAutoScroll() {
      if (autoScrollFrame !== null) cancelAnimationFrame(autoScrollFrame);
      autoScrollFrame = null;
    }
    function autoScroll() {
      if (!drag || !scrollPane || !mousePosition) {
        autoScrollFrame = null;
        return;
      }
      const rect = scrollPane.getBoundingClientRect();
      const margin = 50;
      if (mousePosition.y >= rect.top && mousePosition.y < rect.top + margin) {
        scrollPane.scrollTop -= 11;
      } else if (mousePosition.y < rect.bottom && mousePosition.y > rect.bottom - margin) {
        scrollPane.scrollTop += 11;
      }
      hoverAt(mousePosition.x, mousePosition.y);
      autoScrollFrame = requestAnimationFrame(autoScroll);
    }
    function finishDrag(event) {
      if (!drag || (event && event.pointerId !== drag.pointerId)) return;
      if (event) hoverAt(event.clientX, event.clientY);
      const current = drag;
      drag = null;
      mousePosition = null;
      stopAutoScroll();
      clearHighlight();
      if (scrollPane) scrollPane.classList.remove("calendar-selecting");
      // Complete a single click or a multi-slot drag on release.
      // Ignore the synthetic link click that might follow this pointerup.
      suppressClickUntil = Date.now() + 400;
      const begin = Math.min(current.startIndex, current.lastIndex);
      const finish = Math.max(current.startIndex, current.lastIndex);
      const start = slotsForDay(current.day)[begin];
      const last = slotsForDay(current.day)[finish];
      if (start && last) {
        openPlan(current.day, start.dataset.time,
          toTime(toMinutes(last.dataset.time) + 30));
      }
    }
    function slotsForDay(day) {
      return slots.filter(slot => slot.dataset.day === day);
    }
    slots.forEach(function (link) {
      // Disable the browser's native drag-and-drop of <a href="...">.
      link.draggable = false;
      link.addEventListener("dragstart", event => event.preventDefault());
      link.addEventListener("pointerdown", function (event) {
        if (event.pointerType === "touch" || event.button !== 0) return;
        event.preventDefault(); // prevents native text selection / anchor dragging
        const row = link.closest("tr");
        const cell = link.closest("td.calendar-cell");
        drag = {
          pointerId: event.pointerId, day: link.dataset.day,
          column: cell.cellIndex, startIndex: row.sectionRowIndex,
          lastIndex: row.sectionRowIndex
        };
        mousePosition = { x: event.clientX, y: event.clientY };
        if (scrollPane) scrollPane.classList.add("calendar-selecting");
        try { link.setPointerCapture(event.pointerId); } catch (_) { /* optional */ }
        highlightRange();
        if (autoScrollFrame === null) autoScrollFrame = requestAnimationFrame(autoScroll);
      });
      link.addEventListener("click", function (event) {
        event.preventDefault();
        if (Date.now() < suppressClickUntil) return;
        // Keyboard and touch both still support quick-add.
        openPlan(link.dataset.day, link.dataset.time);
      });
    });
    document.addEventListener("pointermove", function (event) {
      if (!drag || event.pointerId !== drag.pointerId) return;
      mousePosition = { x: event.clientX, y: event.clientY };
      hoverAt(event.clientX, event.clientY);
    });
    document.addEventListener("pointerup", finishDrag);
    document.addEventListener("pointercancel", function () {
      drag = null;
      mousePosition = null;
      stopAutoScroll();
      clearHighlight();
      if (scrollPane) scrollPane.classList.remove("calendar-selecting");
    });
    window.addEventListener("blur", function () {
      drag = null;
      mousePosition = null;
      stopAutoScroll();
      clearHighlight();
      if (scrollPane) scrollPane.classList.remove("calendar-selecting");
    });
    dialog.querySelector("[data-close-plan]").addEventListener("click", function () {
      dialog.close();
    });
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) dialog.close();
    });
    setMode();
  }

  // This is a visual clock only; no location or activity data leaves the browser.
  function brusselsNow() {
    const parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/Brussels", year: "numeric", month: "2-digit",
      day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
      hourCycle: "h23"
    }).formatToParts(new Date());
    const get = type => parts.find(part => part.type === type).value;
    return {
      day: get("year") + "-" + get("month") + "-" + get("day"),
      hour: Number(get("hour")), minute: Number(get("minute")),
      second: Number(get("second"))
    };
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
    const now = brusselsNow();
    const todayHeader = scrollPane.querySelector('.calendar-day-head[data-day="' + now.day + '"]');
    if (previousPosition && Number.isFinite(previousPosition.top) &&
        Number.isFinite(previousPosition.left)) {
      scrollPane.scrollTop = previousPosition.top;
      scrollPane.scrollLeft = previousPosition.left;
    } else {
      const hourSlot = String(now.hour).padStart(2, "0") + ":" +
        (now.minute < 30 ? "00" : "30");
      const todayCell = scrollPane.querySelector(
        '.calendar-cell[data-day="' + now.day + '"][data-time="' + hourSlot + '"]');
      const first = todayCell || scrollPane.querySelector("[data-initial-scroll]");
      const header = scrollPane.querySelector("thead");
      if (first && header) {
        scrollPane.scrollTop = Math.max(0,
          first.getBoundingClientRect().top -
          scrollPane.getBoundingClientRect().top -
          header.getBoundingClientRect().height - 70);
      }
      if (todayHeader && window.matchMedia("(max-width: 750px)").matches) {
        scrollPane.scrollLeft = Math.max(0, todayHeader.offsetLeft - 76);
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

    const marker = document.createElement("span");
    marker.className = "calendar-now-marker";
    marker.setAttribute("aria-hidden", "true");
    marker.textContent = document.documentElement.lang === "nl" ? "Nu" : "Now";
    let activeCell = null;
    let activeHeader = null;
    function moveNowLine() {
      const current = brusselsNow();
      const slot = String(current.hour).padStart(2, "0") + ":" +
        (current.minute < 30 ? "00" : "30");
      const cell = scrollPane.querySelector(
        '.calendar-cell[data-day="' + current.day + '"][data-time="' + slot + '"]');
      const dayHeader = scrollPane.querySelector(
        '.calendar-day-head[data-day="' + current.day + '"]');
      if (activeHeader !== dayHeader) {
        if (activeHeader) activeHeader.classList.remove("calendar-today");
        if (dayHeader) dayHeader.classList.add("calendar-today");
        activeHeader = dayHeader;
      }
      if (!cell) {
        marker.remove();
        activeCell = null;
        return; // The visible week doesn't include the current date.
      }
      if (cell !== activeCell) {
        cell.appendChild(marker);
        activeCell = cell;
      }
      const fraction = ((current.minute % 30) * 60 + current.second) / 1800;
      const height = cell.getBoundingClientRect().height || 36;
      marker.style.top = (fraction * height) + "px";
    }
    moveNowLine();
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) moveNowLine();
    });
    // Fifteen-second updates with a matching CSS transition look gradual.
    setInterval(moveNowLine, 15000);
  }
});
