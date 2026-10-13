# Fatigue Manager — Handover

Updated: 2026-10-13 (v0.2.1 weekly timetable prepared). Repository: https://github.com/jefvanlieshout/fatigue-manager

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
