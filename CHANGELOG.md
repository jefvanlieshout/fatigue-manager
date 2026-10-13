# Changelog

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
