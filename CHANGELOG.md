# Changelog

## v0.2.5 — 2026-10-13

- Unified activity-name suggestions from completed, planned and recurring activities, with a single searchable picker.
- Moved daily starting-energy inputs out of calendar headers into a collapsible battery strip; Enter saves, no visible Save button or "Default 0" explanation.
- Hid the Insights navigation tab, preserving existing data and route.
- Configurable on-screen hours (default 06–23) and A4 print hours (default 07–22).
- Kept today green and replaced the current-time indicator with a plain continuous red line, fixing the half-hour rollover jump.
- Removed deletion-confirmation popups.
- Added ⚙ settings for energy-consumption thresholds and color choices; distinguishes real readings, estimates, energy recovery and missing data.
- Added a dedicated full-bleed A4 landscape printable weekly calendar (CSS @page margin:0).
- SQLite v4→v5 migration for persisted preferences, updated regression tests, README and handover. No GitHub Actions.


## v0.2.4 — 2026-10-13

- Mobile weekly planner: compact header, minimal text above timetable, maximized calendar viewport and easier scrolling.
- Tap a planned or completed event to edit/delete directly; recurring occurrences support skip-once and delete-series actions.
- Live red line marking current time in today's column; updates every 15 seconds and highlights today's date.
- Unrecorded daily energy defaults visually to 0 rather than 100; no synthetic diary measurement is saved.
- Daily, weekday, weekly and custom-day repeating tasks with optional end date; per-occurrence modifications and completion.
- SQLite v3→v4 migration adds compact recurring series and exception tables, without changing existing diary and plans.
- Regression tests and bilingual copy updated; no GitHub Actions.


## v0.2.3 — 2026-10-13

- Fix click-and-hold calendar range selection using pointer movement and grid coordinates rather than unreliable link hover events; support auto-scrolling for long ranges.
- Prevent browser-native link dragging; maintain touch scrolling, keyboard selection, and timed form fallback.
- Offer previously recorded Add Activity names through both a datalist and an explicit recent-activity dropdown in week planner.
- Show 100 as the adjustable default starting energy for every day/week without fabricating stored energy readings. Recorded values always win.
- English/Dutch UI updates, tests, README and handover. SQLite stays at v3; no GitHub Actions.


## v0.2.2 — 2026-10-13

- Drag-select multiple contiguous half-hour slots on desktop, or choose a start and end time in the phone-friendly form.
- Display activities as single spanning blocks with their full start/end times, placing overlapping events in parallel lanes.
- Calendar quick-add can either schedule a future task or record a completed task with actual before/after energy (0–100).
- Preserve simple tracker while adding an optional actual end-time input in its hidden timing section.
- Transactional SQLite v2→v3 migration to add end times to plans and diary entries; existing records retained.
- Add duration, overlapping event, completed diary and migration tests. No GitHub Actions.


## v0.2.1 (2026-10-13)

- Full weekly timetable: seven days across, hours along the side, 30-minute time cells.
- Quick-add planned activity when choosing a time slot, with a prefilled day and time.
- Displays existing diary entries and scheduled plans at their recorded times; handles untimed plans.
- Daily starting-energy inputs remain visible in each day header.
- Mobile scrolling, accessible native planning dialog and a no-JavaScript fallback.
- Local regression tests and updated docs. No schema change or GitHub Actions.


## v0.2.0 (2026-10-13)

- Weekly planner, independent daily starting-energy entries (including 0 or unknown).
- Create/edit/remove planned activities, optional time and personal estimate, record completed activity without duplicate diary entries.
- Daily energy timeline showing observations only; activity insights with median, range and sample counts.
- English and Dutch UI selection (English default) without adding complexity to the tracker.
- Transactional SQLite v1→v2 schema migration; regression tests, README and handover updates.
- Same LXC and manual GitHub deployment; no GitHub Actions.

## v0.1.1 (2026-10-13)

- Fix missing Jinja `endblock` in authenticated main page (HTTP 500 immediately after login).
- Add automatic HTML template compilation checks to local tests, install and update steps.

## v0.1.0 (2026-10-13)

- First Dutch activity and energy tracker.
- Daily history, edit/delete, CSV export.
- Private SQLite storage and password login.
- Proxmox deployment, manual updates, backups and project handover.
