# Fatigue Manager — Handover

Updated: 2026-10-13. Repository: https://github.com/jefvanlieshout/fatigue-manager

## Background and core requirement

Project created for a family member managing fatigue and using an MS clinic-inspired paper activity/energy diary. Existing apps were judged overwhelming, including unrelated features such as pain tracking. The most important goal is a simple, sleek mobile experience that costs very little energy to use.

Core flow: activity name, subjective energy before (0–100), energy after (0–100), save. Changes and daily history should be clear. Optional advanced features must remain **opt-in or hidden**, and NEVER clutter the primary screen. Interface is in Dutch. No medical diagnosis, clinical energy budget or deterministic battery accounting.

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
6. Consider additional accounts only if required; current v0.1 is a single private diary.

## Maintenance / future agent notes

- On server: updates via /opt/fatigue-manager/scripts/update.sh as root, after reviewing changes.
- Before each schema change: database backup; forward migration with PRAGMA user_version.
- Test with python -m pytest -q in a venv before deployment.
- Verify startup, login, add/edit/delete, date boundaries (including DST), CSV export, backups and restoration.
- No GitHub Actions; keep release process manual.
- App not yet installed on user's Proxmox; scripts still need real-environment verification.
- Keep main UI simple as new optional features are added.

## Hotfix v0.1.1 — 2026-10-13

First live installation exposed HTTP 500 after successful login: `app/templates/index.html` omitted the closing Jinja `{% endblock %}`. Appended the missing tag. Added `scripts/check-templates.py`, invoked in install/update, and a pytest regression test to prevent further undetected template syntax errors. Current release should be updated in the LXC via `bash /opt/fatigue-manager/scripts/update.sh`. This fix is not yet verified on the actual LXC; if login still fails, capture `journalctl -u fatigue-manager -n 80 --no-pager`.
