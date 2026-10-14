# Fatigue Manager — Handover

Updated: 2026-10-14 — v0.2.6 compact weekday energy controls. Repository: https://github.com/jefvanlieshout/fatigue-manager

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
