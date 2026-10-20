# Changelog

## v0.2.18 — 2026-10-20

- Restored about two lines (2rem) of empty breathing room beneath the weekly calendar, without restoring the removed footer text.
- Made the compact mobile calendar a little shorter so its bottom spacing is visible on screen.
- CSS-only change, no data or database changes.


## v0.2.17 — 2026-10-20

- Removed the bottom-of-page energy disclaimer from the Week Planner and the shared tagline footer from the website to reclaim vertical space.
- No change to diary records, forecasting, printing, or database. No migration or GitHub Actions.


## v0.2.16 — 2026-10-20

- Starting-energy saves now apply from the selected day through Sunday, automatically filling the remaining week.
- A new morning reading on Tuesday or later updates only that day and the future days of the same week; earlier days stay unchanged.
- Clearing a day clears its remaining-week estimates; completed activities and recorded energy changes remain untouched.
- Added English/Dutch help text and two focused regression checks. No database migration or GitHub Actions.


## v0.2.15 — 2026-10-16

- Added a 7mm white safety inset to printed A4 weeks, protecting weekday names, outer columns and bottom slots from the ~5mm unprintable border of ordinary printers.
- Rebalanced the print table to 283mm wide and the hourly grid to 186mm high, keeping typical 07:00–21:30 activities at their larger print-only text sizes.
- Adaptively shrink activity text for very dense print ranges; clarified A4 landscape, actual-size, margin-free print settings in English and Dutch.
- Updated print asset cache versions, related tests, changelog and handover. No database migration or GitHub Actions.


## v0.2.14 — 2026-10-16

- Changed Calendar Settings “To” hours to inclusive for both screen and print, with English/Dutch guidance.
- Added support for From 0 / To 0 (midnight hour) and From 0 / To 23 (whole day through 23:30).
- Preserved internal exclusive end boundaries and all existing saved hour settings; no database migration.
- Added regression tests for round-trip values, full-day printing, and invalid ranges. No GitHub Actions.


## v0.2.13 — 2026-10-16

- Added a visible moon/sun toggle in the header, including the login screen, for user-controlled dark/light mode.
- Remember theme choice in browser-local storage; no automatic switching from OS preference or time of day.
- Styled the calendar, event cards, forms, dialogs, autocomplete, navigation and energy summaries for low-glare dark mode.
- Load same-origin theme bootstrap before CSS to prevent bright flash; keep printed A4 calendar on its own light stylesheet.
- Added English/Dutch accessible labels and local regression tests. No database migration, third-party dependencies or GitHub Actions.


## v0.2.12 — 2026-10-16

- Increased printed calendar activity-name font from 5.5 to 7.5 pt and time from 4.6 to 6 pt.
- Tightened event padding/line spacing; keep 30-minute event times legible and let longer event names wrap.
- Kept the on-screen Week Planner unchanged; added print-only CSS tests and bumped print stylesheet cache key.
- No database migration or GitHub Actions.


## v0.2.11 — 2026-10-16

- Changed Add Activity to a historical reference/index: samples are saved and used for estimates, but not displayed or counted as actual calendar events.
- Introduced SQLite v5→v6 `calendar_visible` classification, automatically keeping previously linked completed plans visible and preserving all legacy data.
- Adjusted event text/padding to avoid clipping the bottom of the time line.
- Shortened the A4 print weekday header to 10mm; removed redundant “Weekly planner” heading and week range.
- Removed Planned/Completed legend and sideways-swiping explanatory text above the week grid.
- Expanded regression tests and handover; no GitHub Actions.


## v0.2.10 — 2026-10-16

- Added each day's remaining-energy value beneath its name/date on the printed weekly planner.
- Reused the on-screen forecast logic, including unknown costs, estimates, unsaved morning values, and negative balances.
- Ensured whole-day totals include activities outside configured print hours.
- Resized A4 header and rows to keep a full landscape page without CSS margins.
- Updated print asset cache keys and regression tests. No database migration or GitHub Actions.


## v0.2.9 — 2026-10-15

- Removed the small '?' warning badge for calendar events without energy readings.
- Kept events usable as ordinary calendar appointments; only known energy changes contribute to the remaining-energy estimate (≈ indicates an incomplete/estimated figure).
- Cleaned unused styling, updated regression tests and documentation. No schema change or GitHub Actions.


## v0.2.8 — 2026-10-15

- Fixed intermittent Save clicks after choosing a previously used activity: stop picker from reopening on refocus and keep the suggestions out of the form's layout flow.
- Restyled the activity list into a small, light, keyboard-accessible search panel; suppress empty-input suggestions.
- Added remaining-energy estimate below each day's battery input: saved starting energy plus recorded actuals and estimated planned activity changes, without double-counting completed plans.
- Flag unknown energy costs instead of treating them as zero; show ≈ for estimates, preserve negative deficits, offer live preview when wake-up energy is typed.
- English/Dutch labels, tests, README and handover updated. No database migration or GitHub Actions.


## v0.2.7 — 2026-10-14

- Fixed the settings gear silently doing nothing; reliable modal opening and authenticated standalone settings-page fallback.
- Extracted the modal and fallback page's common settings form to prevent divergence.
- Registered gear click handling independently from calendar initialization, bumped static asset versions, and expanded regression tests.
- SQLite remains v5; no GitHub Actions.

## v0.2.6 — 2026-10-14

- Restored the editable starting-energy input directly beneath each weekday/date in the week calendar.
- Show only a 🔋 icon and numeric 0–100 input per day; press Enter to save, no visible Save button or helper text.
- Removed the separate energy dropdown and its browser-state code; compact layout on phones.
- Fixed the calendar-settings dialog being embedded in the page-title template block.
- Updated tests, docs and static asset cache version. No database migration or GitHub Actions.


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
