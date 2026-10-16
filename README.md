# Fatigue Manager — Energiedagboek

A small, private, mobile-first activity and energy diary (English by default, with Dutch selectable). Designed for people who want to learn what uses or restores their energy, without overwhelming app features.

## Current release: v0.2.14 — inclusive calendar-hour settings

- Activity name, starting energy (0–100), ending energy (0–100).
- Immediate energy-change feedback.
- Automatic date/time with optional editing.
- Day-by-day diary; edit/delete entries; reuse recent activity names.
- CSV export; local SQLite database; one password login.
- Week calendar with all seven days across the top and all 24 hours along the left, using 30-minute time slots.
- Click a slot to open a small form with the chosen date and time filled in; choose an end time to make a longer activity.
- On desktop, **click and hold a free time slot, drag downward or upward over multiple half-hours, then release**. The start and end fields are populated automatically. Native browser link-dragging is suppressed and the timetable can auto-scroll when selecting a long range.
- On mobile, tap a starting time slot and choose the ending time in the form; touch scrolling remains uninterrupted.
- While planning, select a previously entered activity from the **Recent activities** dropdown or type a new name. This list comes from the existing Add Activity diary.
- Choose **Plan for later** (optional estimate) or **Already completed** (actual before/after energy values). Completed activities go directly into the same diary as the original tracker.
- Plans and recorded activities appear at their selected or actual times; untimed plans remain visible.
- On phones, scroll horizontally to see every day and vertically to see all hours.
- Each day starts with **0/100 visibly prefilled** in the week and day forms until someone confirms their starting-energy reading. An unconfirmed default is NOT automatically saved to the database. Saving a chosen value (including 0) records that day's real reading.
- Plan activities with an optional time and estimated energy change, edit/remove plans, and mark them complete with actual readings.
- Day view: reported energy timeline without guessing missing values.
- Insights: case-insensitive activity grouping; median, min/max and sample count.
- English/Dutch language selector, using one lightweight template system.
- FastAPI, Jinja2, plain CSS/JavaScript. No Docker, Node, telemetry, AI, GitHub Actions, or cloud account.
- No medical diagnosis: energy ratings are subjective, not objective battery capacity.

All future features should be opt-in or hidden until wanted. Keep the main logging screen minimal.

## Installation

Full Proxmox instructions: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

On the Proxmox host, clone the repo and run scripts/proxmox-create-lxc.sh with an unused VMID (120 is the suggested default). This provisions a Debian LXC.

Inside the new LXC:

    apt-get update && apt-get install -y git
    git clone https://github.com/jefvanlieshout/fatigue-manager.git /opt/fatigue-manager
    cd /opt/fatigue-manager
    bash scripts/install.sh

Choose a strong password when asked. Open http://LXC-IP:8080 on a trusted private LAN only. See deployment guide for HTTPS/Tailscale and backups.

To update inside LXC as root:

    cd /opt/fatigue-manager
    bash scripts/update.sh

## Development and local tests

Python 3.11+ recommended.

    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements-dev.txt
    python -m pytest -q

For manual local execution, provide environment variables FATIGUE_PASSWORD_HASH, FATIGUE_SESSION_SECRET, FATIGUE_DB_PATH before running uvicorn app.main:app. Generate password hashes with app.main.hash_password.

## Docs

- [Deployment](docs/DEPLOYMENT.md)
- [Project handover](HANDOVER.md)
- [English/Dutch + safe multi-user roadmap](docs/I18N_MULTIUSER_PLAN.md)
- [Changelog](CHANGELOG.md)

## Roadmap

1. Activity tracker and history (current).
2. Weekly calendar and activity history (**implemented**).
3. Personal energy observations and simple estimates (**implemented; no predictive model**).
4. Optional recurring routines and more advanced activity planning.
5. Optional assisted schedule suggestions.

The app is currently **single-user**; separate private accounts are planned, not implemented. Do not use the same login for people who must not see each other's records.

Before updating to v0.2, use the included update script as root: it backs up the SQLite database before the automatic v1 → v2 migration. Ensure backups are also copied outside the LXC.

Do not commit .env secrets, SQLite records, backup files, or real health data to the public repository.

### Calendar interaction

The timetable initially scrolls near 07:00; earlier and later hours remain available. Events retain their actual timestamps, even when visually grouped into a half-hour row. A time-slot link works without JavaScript by opening the existing day form with date and time prefilled. v0.2.2 includes a backed-up SQLite v2→v3 migration adding optional activity end times and continues to use the existing LXC, SQLite and manual GitHub updates.

### Logging from the weekly calendar

Click/tap a time cell (or drag over a contiguous block using a mouse). The quick-add form now contains an activity name, day, start time, end time, and a status selector. **Plan for later** saves the schedule without treating estimated energy as fact. **Already completed** asks for the two real 0–100 energy readings and creates an ordinary diary entry. For planned tasks, use the existing day planner to record actual values on completion.

Durations must have an end time after the start time, **within the same day** for now. Scheduled estimates never overwrite actual diary readings. If JS is unavailable, click a slot to use the day planning form with time preselected. The original activity tracker stays lightweight; its optional timing section now also accepts an actual end time.

Before deploying v0.2.2, copy a SQLite backup outside the LXC. The update script creates another backup and runs the automatic schema v2→v3 migration on service startup. After updating, check the calendar, add/edit a long activity, and run local pytest. Existing recordings and plans are preserved.

### v0.2.3 UI behavior

The 0-point default is only a starting value for convenience, never an assertion that a person is fully rested. A previously recorded 0–100 reading overrides it on that date. New weeks show the same 0-point initial value for all seven days. The application does not use a weekly energy bank or infer how someone should feel.

If mouse selection doesn't work after updating, hard-refresh the browser (Ctrl+Shift+R) to load the new JavaScript. Browser-specific drag behavior still needs a real-device test. The update is a frontend and query-only change; SQLite schema stays at v3.

## v0.2.4 — Mobile calendar and recurring activities

The weekly calendar now prioritizes the timetable on narrow screens: hides long help text, reduces header/navigation spacing, keeps the whole seven-day layout scrollable, and initially focuses the current day when viewing the current week.

A slim **red Now line** marks the current time in the current day column. It moves every 15 seconds using the browser's Europe/Brussels time. The line only appears when the viewed week contains today; the current day header is highlighted. No live-time tracking is uploaded to a service.

Tap an existing planned or completed activity to edit it or delete it **directly in the calendar dialog**, instead of navigating away. The same dialog allows marking a scheduled activity completed, with actual before/after energy readings.

### Repeating activities

When creating a plan, expand **Repeat this task (optional)** and choose:
- Every day
- Weekdays (Monday–Friday)
- Every week on the starting weekday
- Custom selected weekdays

An optional until-date stops the schedule; otherwise it continues. Only the requested week is generated on demand, so recurring tasks do not create an unlimited number of database rows.

A repeating occurrence can be edited or skipped for **that day only**, or the entire series can be removed. Completing an occurrence creates one actual diary entry and prevents that occurrence being generated again; already recorded entries remain when the series is deleted. The recurring task UI is only available in the planner, leaving the main activity tracker simple.

For convenience, every unrecorded day shows **0/100 by default** until a real morning value is saved. This does **not** write fake measurements to the database, and saved values take precedence.

### Update and data safety

**This release upgrades SQLite schema v3 to v4** (new recurring rule and exception tables). The existing diary and planned activity tables remain, and the app continues to use the same dedicated Proxmox LXC. Back up your database outside the LXC before updating; run `bash scripts/update.sh` as root, then run the local pytest suite and test the calendar on phone and desktop.

The application still has only **one shared login**. Independent private user accounts remain a separate future milestone. No GitHub Actions, external JS framework, public user registration or external calendar service.

## v0.2.5 — simpler planner, custom energy colors, A4 printing

The planner now focuses on the weekly timetable. **Insights is hidden from the navigation** (underlying feature/data unchanged).

- Activity suggestions combine names from Add Activity, calendar plans, and recurring schedules. A **single searchable list** appears under the activity name; it shows up to six matching activities at a time.
- Each day’s starting-energy rating now appears as **🔋 [0–100] immediately beneath its weekday name/date**, inside the timetable header. Press **Enter** to save that day's value. There is no visible Save button, extra helper label, or separate drawer. The default is still 0/100 and is NOT a stored measurement until submitted.
- Weekday columns and the time axis are compact. Default visible time: **06:00 up to 23:00** (the final slot starts at 22:30). Any planned activity outside the view is kept and listed in that day’s header; nothing is removed from storage.
- Today is highlighted **green**. The thin **red current-time line** has no text or end circles and progresses continuously. It only appears in the correct local day column while that hour is visible.
- Deleting an activity or repeat skips the confirmation popup. Use with care: deletion is immediate. Recorded history for completed repeating events is preserved when deleting the repeating schedule.
- The ⚙ **Calendar settings** gear, between Week Planner navigation and the EN/NL switch, configures energy-color cutoffs and colors, on-screen start/end hours, and separate printing hours.
- Energy colors use actual `energy_before - energy_after` for completed diary entries and available estimated changes for planned entries (shown with `~`). Default: **0–10 points used green; 11–20 orange; 21+ red**. A restoring activity gets blue; an unknown cost gets grey. Users can adjust both boundaries and the low/medium/high colors. Neither estimates nor the 0 starting-energy placeholder count as clinical measurements.
- **Print week** opens a dedicated A4 landscape page. Its default hours are **07:00 up to 22:00**; adjust in settings. Print CSS requests `@page { size: A4 landscape; margin: 0 }` and lays out the full 297×210 mm page, without app navigation. Browser/printer hardware may still impose non-printable edges, margins or scaling; choose 100% scaling, A4 landscape, and no browser headers/footers where available.

### Update

**This release upgrades SQLite from v4 to v5**, adding one `app_preferences` row. Earlier diary entries, planned activities and recurring tasks are preserved. Keep the existing LXC and use the manual update script (no GitHub Actions):

```bash
cd /opt/fatigue-manager
bash scripts/backup.sh
bash scripts/update.sh
```

Copy a verified backup outside the LXC before upgrading. Test the new gear settings and print view from the browser, and run `python -m pytest -q` with `requirements-dev.txt` installed. If rolling back to pre-v5 code, restore its corresponding pre-migration backup. Full instructions: docs/DEPLOYMENT.md.

## v0.2.6 — Direct battery input under each weekday

The separate starting-energy dropdown/drawer was removed in response to usability feedback. Every weekday column now includes only a small 🔋 icon and its editable 0–100 number input directly below the day name and date. Press Enter to save; the underlying authenticated, CSRF-protected daily-energy endpoint is unchanged and continues to store the value for that day only. An unsaved default of 0 remains just a placeholder, not a recorded measurement.

The layout is compact on mobile. A page-template bug was fixed as part of the update: the gear/settings dialog was moved out of the HTML page-title block and back into the visible content. There are no database migrations in v0.2.6 (SQLite remains schema v5). After running `bash scripts/update.sh`, the stylesheet and browser script will reload with versioned asset URLs. The rest of the weekly planner is unchanged.

## v0.2.7 — Settings gear reliability hotfix

The gear in the Week Planner now has a reliable fallback: with JavaScript it opens the calendar settings modal; without JavaScript (or if the modal fails), it opens `/planner/settings?week=YYYY-MM-DD`, an authenticated, CSRF-protected settings page offering the same saved preferences. The shared form is in `app/templates/planner/_settings_form.html` so both paths stay in sync. The settings dialog remains in the template's visible content, not the page title. This is a UI-only update: SQLite stays at v5. No GitHub Actions.

## v0.2.8 — Activity lookup reliability and daily remaining energy

The weekly calendar now shows a small **remaining-energy estimate** below each weekday's 🔋 starting-energy input.

- A saved morning energy rating is the starting point. For example: start at 80, complete an activity using 15 points, and plan one expected to use 25 more → **≈40 left**.
- Completed diary entries contribute their **actual** before/after difference. Uncompleted one-off and recurring tasks contribute either their explicitly entered expected difference or a median from earlier completed activities with the same name. **Completed plans are never counted a second time**.
- Activities with no known energy change are excluded from the arithmetic and marked with a **?**, with an explanation. If any future/unknown values are involved, the number is prefixed with **≈**. Negative totals are left negative to make an overfull schedule obvious.
- The app does not invent a starting-energy measurement: if only the unsaved default 0 appears, the forecast shows **—** until someone enters their own rating. Typing a value shows a live preview immediately; **Enter still saves** as before.
- These are personal, subjective planning estimates—not medical advice or a physical battery calculation. The number is a **whole-day outlook**, not a minute-by-minute forecast.

**Autocomplete usability fix:** Picking a previously used activity now closes the suggestions without immediately reopening them. The list floats over the form rather than pushing the Save button around; it stays hidden for empty input, shows up to six matching names, and has a softer light background and keyboard access. This fixes the likely cause of inconsistent Save clicks after selecting a suggestion.

No database migration; schema remains **v5**. Reuse existing LXC/SQLite and manually deploy via `cd /opt/fatigue-manager && bash scripts/update.sh`. The CSS/JS query version is **0.2.8** to invalidate browser cache. Run local pytest and verify picking a suggestion followed immediately by Save, plus changes to remaining energy when activities are planned, completed, or removed. No GitHub Actions.

## v0.2.9 — Calendar items without energy readings

An activity may be added solely for scheduling. The small `?` badge next to remaining energy has been removed. Activities without a known energy difference remain on the calendar normally and continue to be omitted from energy arithmetic; the remaining value uses `≈` when it is incomplete or estimated. The battery controls, activity editor and the rest of the week view are unchanged. No database migration, GitHub Actions or new dependencies.


## v0.2.10 — Remaining energy on printed weekly calendar

The **Print Week** page now displays the same estimated energy remaining beneath each weekday name and date as the interactive Week Planner. Values use the shared `daily_energy_projection` calculation, not a second independent formula: saved starting energy plus real energy changes for completed activities, plus estimates for unfinished plans. Unknown-cost calendar appointments are simply ignored in the arithmetic; an `≈` prefix indicates the result involves estimates or incomplete data. If no starting energy was saved, the printed value is `— left`, not a fabricated 0. Negative remaining totals are shown and highlighted.

The calculation runs **before filtering by print hours**, so activities outside the printable 07:00–22:00 window still affect the whole-day total. A4 landscape stays full-bleed with zero requested margins; to fit the extra header line, header height increases from 11mm to 17mm and the body grid decreases by 6mm, totaling the same 297 × 210mm page. Screen week, database, and recurring activities are unchanged.

No database migration. `bash scripts/update.sh` remains the manual deployment method. Print assets use `?v=0.2.10` to avoid old cached styles/scripts. Run local tests and check your browser/printer A4 preview; some physical printers require margins despite zero-margin CSS. No GitHub Actions.


## v0.2.11 — Reference examples versus real calendar activities

**Add Activity** now stores a reusable, historical energy *reference sample* (name, before and after energy, date). It is retained in the Add Activity index/history and contributes to `estimate_stats()` medians, name suggestions, and exported CSV. It is **not** displayed on the weekly planner, does not appear on the printed week, and does **not** reduce the day's remaining-energy total. Use the Week Planner to create actual calendar events, including completed events.

The SQLite migration **v5→v6** adds `entries.calendar_visible`, separating reference samples (`0`) from events created/completed in the planner (`1`). Existing records are not deleted. It automatically recognizes earlier completed events linked to one-off or recurring plans. **Older standalone completed events that were created directly from the calendar were not labeled differently from Add Activity samples; these are conservatively treated as reference samples during migration**. Their data remain in the database, Add Activity history, energy statistics and export. A future explicit “Move to calendar” action could restore such an item to the timetable without guessing its origin.

UI cleanup: removed the Planned/Completed legend and mobile sideways-swiping instruction. Moved each calendar event's name and time toward the top to avoid the last line clipping. The **A4 printed week** no longer repeats the “Weekly planner” title/date banner (each weekday already shows its own date), and the weekday/remaining-energy header has been reduced to 10mm. The 200mm remainder is used for the time grid, still one A4 landscape page with zero requested CSS margins.

This is a **database migration**, so save and verify an external copy of SQLite before running `bash scripts/update.sh` in the Fatigue Manager LXC. Expect SQLite `PRAGMA user_version` = **6** after restart. New code must not be rolled back onto the v6 database without also restoring the corresponding previous backup. Manual local pytest and browser/print checks are required. GitHub Actions remain disabled.


## v0.2.12 — More readable printed activity text

Only the dedicated A4 landscape print stylesheet changed: **activity names grow from 5.5 pt to 7.5 pt**, and **activity times grow from 4.6 pt to 6 pt**. Internal padding and line spacing were tightened slightly so both lines fit comfortably in short (30-minute) entries. For single-slot entries, long activity names are limited to one line with an ellipsis to leave room for the time; longer appointments retain wrapping. The interactive Week Planner typography and sizing in `style.css` are not changed.

The print CSS link now uses `?v=0.2.12` to avoid cached styles. Print hours and A4 page dimensions remain unchanged. No database migration, new dependencies or GitHub Actions. Run `bash scripts/update.sh` in the existing LXC, open **Print Week** and inspect print preview at A4 landscape, 100% scale. Try a short 30-minute event as well as a longer event; browser/printer rendering can vary.

## v0.2.13 — Manual light/dark mode

Use the **moon (☾)** button in the header to switch to dark mode, and the **sun (☀)** button to return to the light theme. This is a **manual choice only**: the site will never change theme based on local time, sunset, or operating-system settings. The choice is remembered in `localStorage` under `fatigue-manager-theme`, separately for each browser/device (no account settings, cookies, or backend/database changes). If browser storage is unavailable, the toggle still works during the current page view.

The light/dark switch appears on the login page and every authenticated page, including Add Activity, Week Planner, Day, and Settings. The dark palette covers page backgrounds, panels, input fields, buttons, the calendar's sticky weekday/time headers and event cards, activity autocomplete, modals, settings, remaining-energy labels, and the green highlight for today. Switching themes does not change diary content, event colors/energy thresholds, or any stored energy data.

The **Print Week** page deliberately retains its separate light A4 stylesheet to avoid printing dark backgrounds or consuming extra ink. The dark preference applies only to the website. A small external, self-hosted `app/static/theme.js` runs before the main stylesheet to avoid flashing a bright page when reloading at night, and updates the phone browser's theme-color metadata. CSP remains `script-src 'self'`, with no inline scripts, trackers, external assets, network calls, or GitHub Actions.

No database migration: SQLite remains **v6**. Update manually with `cd /opt/fatigue-manager && bash scripts/update.sh`, refresh the browser and test switching modes on desktop and mobile, reloading the page, logging out/in, and Print Week.


## v0.2.14 — Calendar and print hour ranges include the selected To hour

The Calendar Settings dialog and its standalone fallback now show **From (hour)** and **To (hour, inclusive)** for both on-screen and printed calendars. The To input accepts **0–23**, like From. Examples: **From 0, To 0** shows 00:00 and 00:30; **From 0, To 23** shows all 48 half-hour slots through 23:30 (ending at midnight); **From 6, To 22** includes 22:00 and 22:30. No 24:00 row is added, since 24:00 is the following day's midnight boundary.

Internally, the stored `day_end` and `print_end` remain *exclusive* so existing calendars, current-time display, and A4 print row sizing continue working. The form displays each saved end as `end - 1` and adds 1 on save. **Existing settings are preserved without reinterpreting their saved hours**, and invalid ranges still return HTTP 422.

No database migration, no print or screen layout changes, no GitHub Actions. Run `cd /opt/fatigue-manager && bash scripts/update.sh` and verify midnight and end-of-day selections in both Week Planner and Print Week.
