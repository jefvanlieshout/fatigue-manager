# Fatigue Manager — Handover

Updated: 2026-10-16 — v0.2.15 printer-safe A4 print layout.

## Background and core requirement

Project created for a family member managing fatigue and using an MS clinic-inspired paper activity/energy diary. Existing apps were judged overwhelming, including unrelated features such as pain tracking. The most important goal is a simple, sleek mobile experience that costs very little energy to use.

Core flow: activity name, subjective energy before (0–100), energy after (0–100), save. Changes and daily history should be clear. Optional advanced features must remain **opt-in or hidden**, and NEVER clutter the primary screen. Interface is currently Dutch in v0.1.1; English-default with a Dutch language switch is planned. No medical diagnosis, clinical energy budget or deterministic battery accounting.

## Implementation v0.1

- Python FastAPI backend + Jinja2 templates + plain CSS/JS; no SPA, Node or Docker.
- SQLite database, version 1, table entries: id, activity_name, energy_before, energy_after, occurred_at (UTC ISO), created_at (UTC ISO).
- Dutch responsive activity form, live energy difference, optional local date/time (Europe/Brussels).
- Suggestions from recent activity names, day navigation, history, edit, delete, CSV export.
- Single-user password login (scrypt hash), signed session, CSRF on mutations, basic security headers.
- Systemd managed service; private data in /var/lib/fatigue-manager.
- Proxmox host CT creation script, in-container install script, manual Git pull/update script and backup/restore.
- Local pytest tests; no GitHub Actions.

## Hosting requirements

User has an EPYC/ASRock Rack ROMED8-2T Proxmox server with existing VMs/LXCs, including GridLab LXC 109, TrueNAS VM and services. Do not alter these. Use separate LXC, suggested ID 120, one vCPU, 512MB RAM, 8GB disk, Debian 12/13 unprivileged. **Actual free CTID, Proxmox storage identifiers and bridge must be checked on host**. Scripts have safe defaults but are not yet deployed on server. See docs/DEPLOYMENT.md.

GitHub is public. Only source, docs and scripts belong there—never health records, password hashes, backups or .env.

## Follow-up roadmap

1. Test initial mobile UX directly with family member; prioritize ease of use and accessibility.
2. Optional historical calendar and low-noise graphs, hidden until requested.
3. Per-activity distributions with medians, range and sample sizes, avoiding false precision.
4. Optional recurring activities (sleep, cooking, waking) and fixed/movable plans.
5. Optional planner suggesting gentler schedules while emphasizing uncertainty and personal choice.
6. Implement language choice (English default, Dutch optional) and separately secured family accounts as planned in docs/I18N_MULTIUSER_PLAN.md; current v0.1 remains a single private diary.

## Maintenance / future agent notes

- On server: updates via /opt/fatigue-manager/scripts/update.sh as root, after reviewing changes.
- Before each schema change: database backup; forward migration with PRAGMA user_version.
- Test with python -m pytest -q in a venv before deployment.
- Verify startup, login, add/edit/delete, date boundaries (including DST), CSV export, backups and restoration.
- No GitHub Actions; keep release process manual.
- User confirmed v0.1.1 login now works on their installed Proxmox LXC (2026-10-13). Provisioning scripts were not independently tested here.
- Keep main UI simple as new optional features are added.

## Hotfix v0.1.1 — 2026-10-13

First live installation exposed HTTP 500 after successful login: `app/templates/index.html` omitted the closing Jinja `{% endblock %}`. Appended the missing tag. Added `scripts/check-templates.py`, invoked in install/update, and a pytest regression test to prevent further undetected template syntax errors. Current release should be updated in the LXC via `bash /opt/fatigue-manager/scripts/update.sh`. This fix is not yet verified on the actual LXC; if login still fails, capture `journalctl -u fatigue-manager -n 80 --no-pager`.

## Approved next steps (planning only, 2026-10-13)

The user requests English and Dutch with English preferred, plus private accounts for multiple people. The complete two-release design, migration plan, security rules and tests are in [docs/I18N_MULTIUSER_PLAN.md](docs/I18N_MULTIUSER_PLAN.md). No application behavior changed in this planning commit.

## Stage 2 + Stage 3 development: weekly planner and insights (v0.2.0)

Implementation is committed in v0.2.0, but must still be **validated on the owner's LXC**; do not claim deployment without confirmation.

- The original activity tracker remains the default screen. Planner and insights are additional navigation links.
- Week cards show recorded diary entries and planned activities; **every day has its own optional 0–100 starting-energy input**. Blank means unknown (NOT 0).
- Each day also has a page with completed activity history, starting-energy editing, and planning/editing/removing/completing tasks with optional time and personal energy estimate.
- Completing a plan records a real before/after diary entry in a single DB transaction and marks the plan complete. Duplicate completion is rejected. Deleting a linked diary entry reopens its plan.
- Activity insights: median energy difference, min/max, sample count, grouped by case-insensitive activity name. Estimates have no guarantees or medical standing. No carryover or daily energy "budget" is modeled.
- Interface translation: English is the default, Dutch can be selected via header controls and saved in a language cookie (account-specific preferences await multiuser).
- SQLite `PRAGMA user_version` migrates 1→2 at startup: creates `daily_energy(day,starting_energy,updated_at)` and `planned_activities(id,scheduled_day,scheduled_time,activity_name,expected_delta,status,linked_entry_id,created_at)`. Existing diary entries are retained.
- Planner currently uses the SAME authenticated single-user diary. Multiuser separation is a **separate future v0.3 milestone**; don't add accounts before authorization, account ownership and security tests.
- Runtime remains FastAPI+Jinja2+SQLite in the SAME LXC. GitHub is still public (do NOT upload user data), and NO GitHub Actions.
- Tests added in `tests/test_planner.py` for migration, zero vs missing morning energy, plan completion, cross-site request safeguards, translations, week starts and analytics.
- For upgrade: existing `scripts/update.sh` takes a SQLite backup, updates Git checkout, and restarts the service (migration at startup). **Copy a verified backup outside the LXC** before updating. Run local tests and verify data after reboot.
- On real device, evaluate screen spacing and whether the 7 daily energy inputs are easy to use. Do not clutter the simple tracker.

## v0.2.1 timetable implementation — 2026-10-13

Request: Show the COMPLETE week in a calendar, days across the top and hours down the left, and let a user choose a day/time to plan an activity.

Changes:
- Week view now uses a 7-column table with 48 half-hour slots per day, covering every hour (00:00 to 23:30).
- Each day header shows editable starting energy (0–100; blank means missing), plus any untimed planned activities.
- The timetable shows existing diary entries at their recorded local time and plans at their scheduled time. Grouping into 30-minute slots is visual ONLY; actual times remain unchanged. Completed plans are represented once via their diary record.
- Click an empty or available time slot to open a native, accessible dialog prefilled with date/time; enter an activity name and optionally an estimated energy change. A non-JavaScript fallback goes to the normal day page with its date/time preselected.
- Python: app/planner.py has calendar_slot(), calendar_week(), recorded timestamps, selected-time fallback, and a view=week return path on the plan creation route.
- UI: app/templates/planner/week.html; app/templates/planner/day.html, app/static/app.js and style.css.
- English/Dutch: new calendar translation labels in app/i18n.py.
- Responsive: all seven columns remain present; smaller screens scroll horizontally, hours scroll vertically. Sticky day/time headers; initially scroll near 07:00.
- Tests: tests/test_week_timetable.py checks days/hours, slot fallback, activity placement, untimed items, login requirements and saved daily energy.
- SQLite remains version 2. No migration, new service, public data exposure or GitHub Actions. Existing single-user login remains in place. Different private accounts are still NOT available.
- For deployment into existing Fatigue Manager LXC: copy a backup outside the LXC, run bash scripts/update.sh in /opt/fatigue-manager, then run Python pytest locally and smoke-test the planner on phone/desktop. The assistant has not accessed the running LXC, so live deployment/test status remains unconfirmed.

## v0.2.2: multi-slot activities + full diary input inside weekly calendar

User requested: select multiple adjacent half-hour/hour calendar slots for one longer activity, and enter the same actual energy-before/energy-after values from the diary within the week planner.

Implementation:
- Calendar displays one time-spanning event from start to end (rather than repeated separate events); ranges rounded to 30-minute grid boundaries for VISUAL display only. Persist original exact HH:MM times, no duplication. Overlapping events are separated into lanes by a greedy interval allocator (group by contiguous overlap).
- Desktop: pointer/mouse drag across slots in the same day highlights the selected range and opens quick-add with start=min(selected) and end=last selected slot + 30 minutes. Phone: touch scrolling is preserved; tap start then choose end time in form. Keyboard/screen reader: click/focus the start slot and set end in the form. No third-party frontend library.
- Native quick-add dialog has activity name, date, start/end time, and Plan for later versus Already completed. Planned mode may include an optional estimated energy change; completed mode REQUIRES actual before and after energy readings (0–100), stored as a normal diary entry. Never treat estimates as recorded data.
- Existing Day Planner create/edit now accepts an optional end time and shows ranges. Mark-completed flow can record actual ending time. Original tracker remains minimalist; its already-collapsed optional time section gains an actual ending-time input, with correct saving/edit support.
- Schema v3, transactional and repeatable: add nullable planned_activities.end_time (HH:MM) and entries.ended_at (UTC ISO). Existing v1/v2 entries and plans are retained, with unspecified end times where unknown. app/main.py now allows v3. v3 migration runs once at startup under DB transaction, including older v1 databases.
- Backend: app/planner.py adds interval validators, calendar layout duration and overlap metadata, direct POST /planner/create, and end-time storage. Existing /planner/plans and /planner/plans/{id}/edit accept optional end_time. app/main.py entry add/edit accepts optional ended_at.
- UI: app/templates/planner/week.html and day.html, app/templates/index.html, app/static/app.js and style.css, app/i18n.py EN/NL.
- Tests: tests/test_duration.py plus migrated test_planner.py expects schema v3. Test old schema upgrade, 2.5-hour span, no duplicate plan records, actual energy logger, overlap lanes, missing readings, invalid ranges, edit ending times, initial week behavior. Run ALL pytest locally; NOT GitHub Actions.
- Limits: one-day activities only (start<end, same local date), no split across midnight yet. Planned times are not evidence of actual energy; energy remains subjective.
- SINGLE USER still: multiple independent private accounts are a future security release. Never use shared login for separate sensitive diaries. GitHub public, no health data or secrets in it.
- Proxmox deployment still manual: take off-LXC backup, cd /opt/fatigue-manager && bash scripts/update.sh, run python -m pytest -q in test venv, manually try planner on desktop + phone. The assistant cannot confirm actual deployment until user tests it.

## v0.2.3 — Drag-select reliability, saved activity dropdown, daily 100 default (2026-10-13)

User reported click-and-hold dragging over multiple slots DID NOT WORK in v0.2.2. The old implementation relied on `pointerenter` on successive anchor links; browser-native anchor dragging/text selection can interfere.

Fix:
- `app/static/app.js`: mouse/pen `pointerdown` on a blank calendar slot cancels link/text dragging, captures the pointer, and tracks `pointermove` using geometrical position within the timetable's actual day column and half-hour row. A selection highlight covers contiguous slots. On `pointerup`, the quick-add dialog opens with earliest selected start and latest selected end, whether dragging upwards or downwards. Near top/bottom, auto-scroll continues selecting longer ranges; pointer cancellation and browser blur clean up. Suppress the follow-up synthetic click to avoid opening the dialog twice.
- Touch devices preserve native swipe scrolling; a simple tap still opens the form, with manual end-time selection. Keyboard activation of a time slot is unchanged. Native anchor dragstart is explicitly suppressed. Calendar selection CSS is more visible.
- `app/planner.py`: week template context now includes the same `suggestions()` values derived from diary entries used by the main Add Activity screen.
- `app/templates/planner/week.html`: activity name offers a native datalist and a visible dropdown of previously recorded activity names. Selection fills the free-text name field; brand-new activities can always be typed.
- Daily starting energy: for every unrecorded day, both week and day forms **display 100/100 as an editable default**. Existing 0–100 recorded values remain unchanged. A short explanatory label distinguishes default/unconfirmed 100 from an actual saved morning reading; no database rows are created for the default. Saving 100 explicitly records a real value. There is no inferred weekly energy bank.
- `app/i18n.py`: EN/NL text for the dropdown, defaults and drag instructions. `tests/test_week_interactions.py` validates the week default semantics, actual saving, suggestions and presence of drag handlers.
- No database migration. Schema remains v3, service and Proxmox LXC unchanged, no GitHub Actions. Existing single-user restrictions still apply.
- Browser reload/hard refresh after upgrade may be needed to avoid old cached app.js. Check actual click-hold and drag selection on desktop and tapping on phone. Run all local pytest after `bash scripts/update.sh`. Preserve an off-LXC backup before updating.

This commit provides the implementation but does NOT confirm browser-interaction testing on the user's actual devices.

## v0.2.4 — Mobile-first weekly calendar + live now indicator + recurring tasks

User feedback:
- Too much explanatory text and header clutter on phones above the timetable.
- Editing/deleting activities from the weekly calendar previously required too many steps.
- A red line should follow the current time down the current day column.
- Change the unrecorded daily starting-energy default from 100 to 0.
- Add recurring activities.

Implementation:
- Mobile CSS scoped to .shell.wide trims explanatory text, compacts header/navigation, expands the scrollable calendar to nearly full available viewport height, and retains horizontal week scrolling.
- Clicking an existing scheduled or completed calendar block opens the same lightweight modal already used for new activities, populated with current values. Edit or delete directly; recorded values remain actual (not plans). For a recurring occurrence, edit just that day, skip only that occurrence, or delete the complete series.
- Client-only Europe/Brussels red current-time bar sits within today's half-hour slot and moves every 15 seconds with CSS transitions; today's header receives a subtle highlight. No such marker when viewing another week. Auto-focus today's day/time on small screens unless a saved scroll position exists.
- Day and week starting-energy inputs show an editable 0 when not yet recorded; **no database record is inserted until Save is used**. Existing real daily values (including 0 and 100) are preserved.
- Recurrences are rules rather than thousands of copied plans: daily, Mon-Fri, weekly based on starting weekday, or selected weekdays, optionally limited by until_date. Each occurrence can be modified, skipped or completed via an exception record. A completed occurrence creates a real diary entry; it disappears as a planned occurrence. Deleting a series preserves all completed history.
- SQLite v3 -> v4 migration creates recurring_rules and recurring_exceptions tables, while preserving existing entries, day energy, plans and their timestamps. Initialization repeatable, wrapped in SQLite transactions.
- New app/recurrence.py contains database migration, limited date-range expansion and validation. app/calendar_actions.py handles authenticated, CSRF-protected create/edit/delete/complete for one-off plans, diary entries and recurring instances. app/planner.py merges generated recurrences into calendar/day views. app/main.py allows schema v4 and reopens occurrence when its linked diary entry is deleted.
- Updated app/templates/planner/week.html, day.html, app/static/app.js/style.css and app/i18n.py for English/Dutch.
- New tests/test_recurring_calendar.py covers migration, repetition, single skip/edit/complete, deleting a series, editing/removing one-off and recorded items, default 0 and mobile indicator. Old tests expecting default 100 or schema v3 were updated.
- No third-party calendar dependency, no telemetry, no GitHub Actions, no new LXC. Still SINGLE-USER: future multiuser account isolation remains separate and is NOT delivered by v0.2.4.

Deployment: back up database to the NAS/off-container location before running existing `bash scripts/update.sh` from /opt/fatigue-manager inside the LXC. On successful restart SQLite PRAGMA user_version should equal 4. Test the full pytest suite, login and calendar on a real phone, tap-to-edit/delete, red marker, repeat patterns and skip/delete series. If rollback is needed, use a matching pre-update backup alongside prior code. Code was not run on the user's Proxmox by the assistant and local test execution there is not confirmed.

## v0.2.5: Requested calendar UX and printable week (2026-10-13)

The user requested:
- Remember calendar-added activity names as well as Add Activity diary names; simplify the multiple-choice suggestions UI.
- Remove starting energy from the weekly grid header; place a battery icon by its input; save with Enter, no visible Save button; remove the 'Default 0' explanation.
- Hide Insights navigation for now (route still exists).
- Default calendar 06:00–23:00, adjustable in a gear. Default A4 print window 07:00–22:00, independently adjustable.
- Keep today green. Replace the red marker with a plain line (no "Now" or circles), fix backwards jump at half-hour rollover.
- Delete immediately without browser confirmation.
- Gear icon between Week Planner and EN/NL. Configurable low/medium/high energy-used thresholds + colors; defaults <=10 green, 11–20 orange, >20 red. Recorded actuals vs planned estimates clearly distinct.
- A Print Week link produces full-bleed A4 landscape (297×210mm; @page margin:0), separate print stylesheet/scripts, no page UI. Physical printer margins may override CSS.

Implementation:
- `app/main.py::suggestions()` combines activity names from `entries`, `planned_activities` and `recurring_rules` and case-insensitively deduplicates them.
- `app/templates/planner/week.html`: separate collapsible energy drawer; individual per-day Enter-to-save forms with 🔋 icon and hidden submit; clean dropdown results; color data classes; settings dialog; print link. `app/templates/base.html`: hide Insights link, add small gear, cache-bump asset query.
- `app/static/app.js`: single searchable picker limited to 6 matched options; CSSOM event coloring; dialog opening; no delete confirm; single now marker positioned continuously in the scroll coordinate system instead of re-parented to half-hour cells; green today header; settings modal.
- `app/preferences.py`: validated, SQLite-backed thresholds, color strings, screen/print hour ranges, default settings (10,20; green/orange/red; 6–23; print7–22); energy class mapping. `app/settings_routes.py`: authenticated CSRF-protected settings POST and print GET.
- `app/planner.py`: generate only configured timetable rows, list entries outside the display range rather than losing them, add color buckets and predicted flag. `app/recurrence.py`: permits v5 schema without regressing v4.
- `app/templates/planner/print.html`, `app/static/print.css`, `print.js`: dedicated landscape A4 rendering, 0 browser page margin in @page CSS, time-window scaling.
- SQLite schema v4→v5 adds `app_preferences` only; no destructive change to user data. `app/main.py` accepts version 5, recurring init only increments version3→4, then preferences migrates4→5. Still single-user/private.
- Local tests: update legacy expectations to 06–23 and no default-energy hint; add `tests/test_calendar_preferences.py` for color bands/settings validation, CSRF/auth, print output and shared activity suggestions; fix test login helpers to use rotated post-login CSRF token.
- NO GitHub Actions, no additional LXC, no credentials or health records committed. Changes are made in public GitHub code only; actual Proxmox server was NOT modified here.

Deploy: backup SQLite outside LXC first, then inside /opt/fatigue-manager as root run `bash scripts/update.sh`. Startup migration should reach PRAGMA user_version 5. Check local pytest and test on phone and laptop, especially the red-line rollover at XX:29→XX:30 and print margins/print scaling on the actual printer. If rollback is needed, restore the pre-update matching database backup and source revision. 

## v0.2.6 — Battery input directly below each day, no drawer (2026-10-14)

The user explicitly asked to remove the separate starting-energy dropdown because it is clunky and return the battery input to each day heading in the week calendar. Keep ONLY a small 🔋 icon and one editable 0–100 input under each day/date. Press Enter to save; no visible Save button and no helper text.

Implementation:
- `app/templates/planner/week.html`: remove `<details id="energy-drawer">` and the strip of seven forms; place each POST /planner/energy form inside its corresponding `th.calendar-day-head` below the weekday/date anchor. Includes CSRF token, day value, view=week, visually hidden submit button so Enter performs the native form submission and screen readers retain a save action. Retain default unsaved zero; actual saved day readings remain unchanged.
- Moved the `calendar-settings` dialog from a previously malformed Jinja `block title` to the bottom of `block content` so settings display properly rather than becoming part of the HTML page title.
- `app/static/style.css`: compact per-day inline icon/number styling on desktop/mobile; remove obsolete dropdown styling.
- `app/static/app.js`: remove obsolete energy drawer storage toggling; no new JavaScript required for Enter-save.
- `app/templates/base.html`: cache-bump CSS and JS to v0.2.6.
- `tests/test_calendar_preferences.py`: assert seven forms in their own day-header cells, battery icons, hidden submit buttons and no drawer.
- Updated README, CHANGELOG, HANDOVER. No DB schema change (v5), no new routes or dependencies, no GitHub Actions.

Deployment remains manual via `cd /opt/fatigue-manager && bash scripts/update.sh` inside existing LXC, with an external backup and local pytest recommended. After deployment verify with mouse/keyboard (Enter) on PC and phone, including preservation of each day’s value after navigation. Never upload private diary data to GitHub.

## v0.2.7 — Fix nonfunctional gear (2026-10-14)

User reported tapping the ⚙ gear in the weekly planner did nothing. Root cause found in the v0.2.5 template: the settings dialog was mistakenly embedded in the Jinja page TITLE block, rather than in the HTML body. v0.2.6 moved it into the correct CONTENT block. To prevent future silent failures, v0.2.7 also makes the gear an actual link to `GET /planner/settings?week=<monday>`, with the JavaScript opening the existing modal instead when available. A small standalone settings page provides fallback without JavaScript/dialog support. `app/templates/planner/_settings_form.html` is a shared settings form used by the modal and standalone page; the same authenticated POST handler saves changes. The settings modal handler is registered independently at the beginning of app.js so other calendar JS cannot block it. URL-versioned static JS/CSS bumped to v0.2.7. Tests cover GET authentication, link/modal presence and shared fields. No database change (v5), no service change, no Github Actions. Deploy via the usual LXC update script and hard refresh if needed.

## v0.2.8 — Picker bugfix + per-day remaining-energy outlook (2026-10-15)

User reported: clicking a suggested existing activity and then Save intermittently failed to create the calendar entry, whereas clicking outside the name panel first sometimes worked. The old `app/static/app.js` picker handler hid the popup, then immediately called `nameInput.focus()`; the `focus` handler immediately ran `showSuggestions()`, reopening the overlay. Because the panel was in normal document flow, it shifted and intercepted subsequent clicks.

Fix:
- `app/static/app.js`: suggestion selection prevents pointer-driven focus stealing, hides the list, and only returns keyboard focus to name input with a one-time focus suppression. Clears suggestions on form submission. The popup stays hidden on empty input, has Escape and ArrowDown keyboard affordances.
- `app/templates/planner/week.html`: compact single list with a small caption and separated selectable activity buttons. Place `activity-name-field` as a relative positioning root.
- `app/static/style.css`: suggestions are positioned as an absolute dropdown over the form, not pushing down dates, energy fields or Save; soft-light theme, proper hover/focus/mobile rules.

Remaining-energy feature:
- `app/planner.py::daily_energy_projection` combines the saved daily starting score with **actual recorded** `energy_after - energy_before` for diary activities plus **estimated** differences for *uncompleted* planned or recurring activities. Uses plan `expected_delta` when set, otherwise historical median for the matching recorded activity name. Already-completed plans are excluded upstream by `week_data` so no double counting. Each day includes `net`, `remaining`, `estimated_count`, `unknown_count`, `is_estimate`. Negative residual is preserved to flag an overfull day.
- `app/templates/planner/week.html`: small `remaining` text below each day's energy input; projected values marked with ≈, '?' warns that N unknown-cost plans were excluded; if morning energy is not saved, shows — instead of treating placeholder 0 as a measurement.
- `app/static/app.js`: recalculates preview immediately when the user edits the energy input, but **only the existing Enter-to-save form** persists the new reading. Typed but unsaved default remains distinct from stored data.
- `app/i18n.py`: bilingual English/Dutch labels and explanations. `tests/test_remaining_energy.py`: arithmetic, missing estimates, historical medians, completion not duplicated, deficit display, picker regression checks.
- The original diary, recurrence, energy color thresholds, A4 print, settings gear, green current day and red time line remain unchanged.
- No database migration, additional services, extra LXC, credential changes, or GitHub Actions. SQLite schema remains v5, single-user mode still applies.

Verification: deploy via existing manual update script after backup, run local pytest, then select a known activity and immediately click Save on both phone and desktop. Enter 80 wake-up energy and verify the remaining score changes; then complete a plan and check that it is counted exactly once. Actual browser test remains to be done on user's devices, and screenshots should contain no sensitive diary data.

## v0.2.9 — Remove unknown-energy warning badge (2026-10-15)

The user and their mother also use Fatigue Manager as an ordinary calendar, so not every planned item needs an energy reading. Remove the small '?' unknown-energy badge beneath each weekday. `app/templates/planner/week.html` no longer renders `remaining-unknown`; redundant CSS removed. `daily_energy_projection` still omits unknown costs and marks the resulting number with ≈ when estimated/incomplete, rather than assuming unknown cost equals zero. Test expectations adjusted to assert no '?' badge and a correct approximately-marked remaining value. Asset cache version bumped to 0.2.9. No DB or recurrence changes. Run `bash scripts/update.sh` inside the existing LXC and local pytest; no GitHub Actions.


## v0.2.10 — Remaining-energy forecast in A4 print headers (2026-10-16)

User and mother requested printing the total energy left **below each weekday name**, matching the Week Planner screen.

- `app/settings_routes.py::print_week` computes `daily_energy_projection(day)` from `app/planner.py` for all seven days **before** calling `calendar_week(days, print_start, print_end)`. This ensures actual diary energy deltas and scheduled/planned deltas outside the printed hour range still count, using the EXACT same logic as the interactive planner; completed plans are not double-counted.
- `app/templates/planner/print.html` adds an unobtrusive `print-energy-remaining` line beneath each weekday date. Shows `≈` on estimated/incomplete totals, `— left` when morning energy has not been saved, and retains negative totals with `print-energy-deficit` styling. No question badge for ordinary calendar events without energy readings.
- `app/static/print.css`: header increased from 11 to 17mm; font and spacing tuned. `print.js` uses 181mm of grid rows instead of 187mm to preserve 12+17+181=210mm A4 landscape height; `@page margin:0` remains.
- Bumped print CSS/JS asset versions to 0.2.10; updated `tests/test_calendar_preferences.py` to verify seven printed totals, a mixed day with events outside the printing range, unknown-cost appointment, negative total, unset day, parity with screen, and layout constants.
- **No schema, security, account, recurrence or GitHub Actions changes**. Requires normal manual update in Fatigue Manager LXC; the assistant has not deployed or executed live browser/print tests.

Run the Python suite locally and smoke-test printing at A4 landscape (100% scale; physical printer borderless support varies).


## v0.2.11 — Separate Add Activity reference samples from calendar events (2026-10-16)

User and mother clarified: **Add Activity is an energy reference/index input**. They do not want creating or editing one of these samples to automatically show it in the weekly or printed calendar, or count toward the day's remaining energy. Planner-created or planner-completed events must still appear.

- Schema: **v5→v6**, transactional, idempotent migration in `initialize_planner_database()` after existing v1-v5 migrations. Adds `entries.calendar_visible INTEGER NOT NULL DEFAULT 0 CHECK(...)`. New `/entries` samples are explicitly `0`; `/planner/create`, `/planner/calendar-event`, and `/planner/plans/{id}/complete` actual diary events are explicitly `1`. All calendar-created diary entries continue to contribute to activity medians; reference samples remain in the index/export and contribute to estimates.
- `week_data()` fetches **only** `calendar_visible=1` diary entries; as a consequence, remaining-energy projections exclude reference samples. `main.activity_rows()` fetches **only** `calendar_visible=0` so the index shows only references. `estimate_stats()` and `suggestions()` still use all entries and plans for better estimates and autocomplete.
- Legacy migration: known completed one-off activities (`planned_activities.linked_entry_id`) and completed recurring occurrences (`recurring_exceptions.linked_entry_id`) are backfilled to visible=1. **Old directly completed calendar activities without a linked plan are indistinguishable from Add Activity records** and are classified as reference samples (visible=0). Their data are preserved; this limitation is documented to the user. Do not silently delete rows, change dates/values, or guess origins.
- Older migrations: `main.init_db` accepts 6; `recurrence.init_recurrence_db` accepts 6; `preferences.init_preferences` accepts 6 and only raises user_version from 4 to 5, NEVER downgrades v6.
- Week UI: removed entire `calendar-legend` with “Planned”, “Completed”, and the sideways-scroll mobile hint; kept the scrollable seven-day grid. `style.css` moves calendar event title/time nearer top and slightly increases available block height via app.js to prevent cropped times.
- Print UI: removed redundant print-title containing “Weekly planner”/week range, compressed header from 17mm to **10mm**, increased body grid from 181mm to **200mm** (total 210mm = A4 landscape). Keeps seven weekday names, dates and remaining-energy projections; print.js computes event heights from the new row measurement. Print CSS still asks for full A4 and zero margins, subject to printer limits.
- Browser asset versions bumped to 0.2.11; no GitHub Actions or new LXC.
- Updated regression tests and new `tests/test_reference_samples.py` verify reference not printed/plotted/counting, planner actual visible and counted, v5 migration/backfill and idempotency, and removal of clutter.
- Deployment: **back up SQLite to off-LXC storage first**; run `cd /opt/fatigue-manager && bash scripts/update.sh`, then run pytest locally and check a reference sample, planned/recorded calendar entry, and A4 print. `PRAGMA user_version` should report 6. For rollback restore both matching code and v5 DB backup.


## v0.2.12 — Print-only larger name and time fonts (2026-10-16)

User and mother wanted to use the spare vertical space in printed events for more readable text, **without** changing the interactive calendar. This update modifies ONLY `app/static/print.css` typography and its versioned link in `app/templates/planner/print.html`. Activity name: **5.5pt → 7.5pt**. Activity time: **4.6pt → 6pt**. Tighten event padding from `.14mm .4mm` to `.08mm .35mm`; reduce time's top margin from `.15mm` to `.05mm`. One-slot/30-minute event names use one line with text-overflow ellipsis to prioritize keeping the time legible; multi-slot names can wrap. Keep print-page size 297×210mm, header 10mm, 200mm timetable, existing print-hour configuration and energy totals. No edits to `app/static/style.css` or other interactive Week Planner styles.
- New assertions in `tests/test_calendar_preferences.py` check print font sizes, padding, asset cache version, and that the screen-specific stylesheet is independent.
- Print CSS URL changed to `?v=0.2.12`; print JS unchanged.
- No database schema update (still v6), no new LXC/services, no GitHub Actions or account changes.
- Deploy manually using the established LXC update script. Verify output in actual A4 landscape print preview, especially one-slot entries, overlap lanes and long names. Browser PDF/physical printer rendering has not been confirmed by the assistant.

## v0.2.13 — User-controlled night mode (2026-10-16)

User and mother requested a clearly visible **sun/moon header toggle** because the bright interface is uncomfortable at night. Explicit requirement: **do NOT switch automatically**.

- `app/templates/base.html`: sun/moon button appears consistently on login, tracker/index, Week Planner and settings, adjacent to language selector; localized `aria-label`/title and `aria-pressed`. A dedicated same-origin `/static/theme.js?v=0.2.13` is loaded synchronously **in the head BEFORE the main stylesheet** to apply a stored preference before first render. `style.css` and `app.js` versioned asset URLs also bump to 0.2.13.
- `app/static/theme.js` (new): stores only `dark`/`light` in browser-local `localStorage` key `fatigue-manager-theme`; defaults to light; no time detection, OS color-scheme detection, scheduling or external requests. If storage fails, manual toggle works in the current page view. Updates `html[data-theme]`, button accessible label/pressed state, and browser theme-color meta; watches storage changes so tabs remain synchronized.
- `app/static/style.css`: `html[data-theme="dark"]` adds an accessible low-glare palette across body, panels, text, fields, buttons, calendar cells/sticky headers, activity cards, now line, today's green highlight, dialogs, autocomplete, remaining energy, planner and index. Includes responsive toggle sizing in the existing crowded mobile header. Dark styles are placed **after** prior styles so CSS precedence overrides hard-coded backgrounds while allowing custom activity-energy palette colors.
- `app/i18n.py`: new English/Dutch labels for Switch to dark/light.
- The print template uses **only** `app/static/print.css` and `print.js`, so print pages stay light (A4, readable, without dark ink usage) regardless of website theme.
- New `tests/test_theme.py`: toggle visible on login and authenticated routes, early theme script load, correct localized/accessibility content, manual local persistence, no automatic behavior, dark coverage of main views, and independent light print.
- No database or API migration (schema **v6**), added packages, separate LXC, telemetry, third-party assets, GitHub Actions, or user/health data in repository.

Deployment remains manual: back up as normally, run `cd /opt/fatigue-manager && bash scripts/update.sh`. Verify sun/moon toggle, refresh persistence, phone layout, the dialog and calendar colors, login, and printed A4 paper. Only static/source tests were possible here; actual browser/visual contrast checks should be performed on a real phone/desktop.


## v0.2.14 — Inclusive end-hour settings (2026-10-16)

User noted the confusing `To (hour, exclusive)` and wanted midnight selectable. The shared `app/templates/planner/_settings_form.html` now uses `To (hour, inclusive)`, numeric 0–23, displaying persisted `prefs.day_end - 1` and `prefs.print_end - 1` for both calendar-visible and print-visible hours. An English/Dutch hint makes the boundaries explicit: From 0 includes midnight 00:00; To 23 includes 23:00 and 23:30, ending at the next midnight.

The POST handler `app/settings_routes.py::update_settings` converts submitted inclusive values back into the existing exclusive storage (`day_end + 1`, `print_end + 1`) before calling `save_preferences` and existing range validation. Crucially: **do not convert values in `calendar_week`, `load_preferences`, or the client time-line**; all consume exclusive end boundaries as before. A stored end 23 is presented as To 22 and renders slots through 22:30, preserving prior settings. A selected To 23 is stored as 24 and renders through 23:30. From 0 To 0 stores [0,1) and renders 00:00/00:30. Existing DB remains schema v6, no migration, no GitHub Actions. Week modal and no-JS standalone fallback both use the shared partial.

Regression tests in `tests/test_calendar_preferences.py` verify old-setting round trips, saved exclusive boundaries, both To=0 and To=23, 48-slot full-day print, invalid ranges returning HTTP 422 without saving, and parity between screen and print. Before releasing, run local pytest and check the browser's settings gear / print view.


## v0.2.15 — Fix clipping from physical printer margins (2026-10-16)

User found ~5mm printer nonprintable edges cutting off weekday names, side cells, and the bottom of printed weekly calendars (07:00–21:30). Root cause: `print.css` placed the full 297×210mm grid directly at the physical page edges with `@page margin:0`; ordinary printers cannot print edge-to-edge.

- `app/static/print.css`: Keep the full 297×210mm physical A4 page in landscape, **inset all calendar content by 7mm** via `.print-page{padding:7mm}` in normal and print views. The table is now **283mm wide** with a 12mm time column, and seven day columns sharing 271mm. Effective usable vertical space is 196mm: 10mm weekday/remaining-energy heading and 186mm timetable. White edge protects print content from normal hardware printer margins.
- `app/static/print.js`: Row height becomes `186 / count` millimeters, with all event positions using it. **30 rows** (From 7, To 21, inclusive = 07:00 to 21:30) yield 6.2mm each and keep **7.5pt names / 6pt times**. Dense grids shrink only print event type when per-row height falls below 5.6mm, and again below 4.5mm for 24-hour/48-row sheets.
- `app/templates/planner/print.html`: Cache versions for print CSS/JS are `0.2.15`.
- `app/i18n.py`: English and Dutch on-screen print tips now say **A4 landscape, 100%, no browser margins, headers/footers off**. Avoid Fill Page; browser Fit to printable area only if needed on an unusual printer. Enable Background graphics for color coding.
- Updated simple static tests for margins, row geometry, density, and print assets; also refreshed older regression assertions with stale CSS cache versions.
- No database migration, activity changes, interactive calendar styling changes, external packages, live LXC updates, or GitHub Actions. Deploy with existing user-controlled `bash scripts/update.sh`. Confirm via the browser preview and one physical printer/PDF test; print capabilities vary by driver.
