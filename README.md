# Fatigue Manager — Energiedagboek

A small, private, mobile-first Dutch activity and energy diary. Designed for people who want to learn what uses or restores their energy, without overwhelming app features.

## First release (v0.1)

- Activity name, starting energy (0–100), ending energy (0–100).
- Immediate energy-change feedback.
- Automatic date/time with optional editing.
- Day-by-day diary; edit/delete entries; reuse recent activity names.
- CSV export; local SQLite database; one password login.
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
- [Changelog](CHANGELOG.md)

## Roadmap

1. Activity tracker and history (current).
2. Optional calendar/history view.
3. Personal energy patterns with uncertainty.
4. Opt-in routines and activity planning.
5. Optional assisted schedule suggestions.

Do not commit .env secrets, SQLite records, backup files, or real health data to the public repository.
