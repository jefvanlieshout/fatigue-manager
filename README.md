# Fatigue Manager — Energiedagboek

A small, private, mobile-first activity and energy diary (English by default, with Dutch selectable). Designed for people who want to learn what uses or restores their energy, without overwhelming app features.

## Current release: v0.2.1 (weekly timetable and insights)

- Activity name, starting energy (0–100), ending energy (0–100).
- Immediate energy-change feedback.
- Automatic date/time with optional editing.
- Day-by-day diary; edit/delete entries; reuse recent activity names.
- CSV export; local SQLite database; one password login.
- Week calendar with all seven days across the top and all 24 hours along the left, using 30-minute time slots.
- Click a slot to open a small activity-planning form with the chosen date and time filled in.
- Plans and recorded activities appear at their selected or actual times; untimed plans remain visible.
- On phones, scroll horizontally to see every day and vertically to see all hours.
- Daily starting-energy inputs (0–100) remain in the week header, with blank meaning unknown.
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

The timetable initially scrolls near 07:00; earlier and later hours remain available. Events retain their actual timestamps, even when visually grouped into a half-hour row. A time-slot link works without JavaScript by opening the existing day form with date and time prefilled. v0.2.1 introduces no database schema change and continues to use the existing LXC, SQLite and manual GitHub updates.
