# Deployment / maintenance guide

## Proxmox

Run these commands on the Proxmox HOST (not inside an existing CT):

    apt-get update && apt-get install -y git
    git clone https://github.com/jefvanlieshout/fatigue-manager.git /root/fatigue-manager
    cd /root/fatigue-manager
    pvesm status
    TEMPLATE_STORAGE=local ROOTFS_STORAGE=local-lvm BRIDGE=vmbr0 bash scripts/proxmox-create-lxc.sh 120

Check which storage, bridge and CTID are correct for your host before running. Default CTID 120 is not verified as free; the script refuses to overwrite an existing CT. It provisions Debian 13 or 12, unprivileged, one core, 512 MB memory and 8 GB disk. Does not touch any existing LXC or VM.

Enter newly created container:

    pct enter 120
    apt-get update && apt-get install -y git
    git clone https://github.com/jefvanlieshout/fatigue-manager.git /opt/fatigue-manager
    cd /opt/fatigue-manager
    bash scripts/install.sh

Choose a login password of 12+ characters. Installer creates service account, root-only /etc/fatigue-manager.env, private /var/lib/fatigue-manager SQLite database and systemd service. Find IP: pct exec 120 -- hostname -I.

Open http://LXC-IP:8080 **only on trusted LAN**. Never forward TCP 8080 publicly. For remote access use HTTPS via Tailscale Serve or an authenticated reverse proxy, then set FATIGUE_COOKIE_SECURE=1 in /etc/fatigue-manager.env and restart. Restrict direct HTTP reachability when switching to HTTPS.

## GitHub updates (no Actions)

Inside LXC, as root:

    cd /opt/fatigue-manager
    bash scripts/update.sh

Script refuses modified files or non-fast-forward updates, takes SQLite online backup, installs dependencies, restarts and checks the service. Manual tests with python -m pytest -q.

## Backup

Take backup as root:

    bash /opt/fatigue-manager/scripts/backup.sh

Backups stored root-only in /var/backups/fatigue-manager; newest 30 retained. Add to /etc/cron.d/fatigue-manager-backup to back up daily:

    17 3 * * * root /bin/bash /opt/fatigue-manager/scripts/backup.sh >> /var/log/fatigue-backup.log 2>&1

Install/enable cron for that schedule. Also copy backups **outside the LXC** to your NAS or Proxmox backup storage. Never commit personal data to GitHub.

Restore is destructive to current live entries. To restore as root:

    bash /opt/fatigue-manager/scripts/restore.sh /var/backups/fatigue-manager/NAME.sqlite3

It stops the service, makes a pre-restore copy, replaces DB and starts service.

## Troubleshooting / rollback

    systemctl status fatigue-manager --no-pager
    journalctl -u fatigue-manager -n 100 --no-pager
    curl -fsS http://127.0.0.1:8080/healthz

For a code rollback, inspect git log, checkout previous known-good commit, re-install requirements and restart service. If schema migrations changed DB, also restore the matching pre-update database backup. To resume normal updates return to main branch and pull fast-forward.

## Security

Single-user app for private network use. Session cookies are HTTP-compatible initially (LAN only); prefer HTTPS with secure cookies. Password is scrypt-hashed, sessions signed and CSRF-protected. Built-in IP-based login throttling is best-effort and not a substitute for a firewall. Store exports securely. No health-related data in GitHub.

## v0.2.0 planner upgrade

This release migrates SQLite user_version 1 → 2 when the service starts. Existing entries remain intact; new tables hold day-by-day starting energy and planned activities. Use the normal manual update command **inside the LXC** as root:

    cd /opt/fatigue-manager
    bash scripts/backup.sh
    bash scripts/update.sh

Before running it, copy the backup outside the container. Test after updating: login, activity entry, language switch, opening a week, daily starting energy, planning/completing an activity and the insights page.

Check:
    systemctl status fatigue-manager --no-pager
    journalctl -u fatigue-manager -n 80 --no-pager

Rollback requires both a matching source version and database backup if the schema changed. The current app remains single-user. Account isolation is a separate future security release. Never share the same password between people who need private records.

## v0.2.2 activity durations and calendar energy entry

**SQLite schema update v2 -> v3** (or direct v1 -> v3 on older installs): adds `planned_activities.end_time` and `entries.ended_at`, preserving existing records. Run as root **inside** the Fatigue Manager LXC:

    cd /opt/fatigue-manager
    bash scripts/backup.sh
    bash scripts/update.sh

Copy a consistent backup to external NAS storage **before** updating, and do not commit personal health data to GitHub. The usual updater automatically backs up the database, then the service migrates it on startup. To verify the schema, execute:

    sqlite3 /var/lib/fatigue-manager/fatigue.sqlite3 'PRAGMA user_version;'

Expected output: `3`. Also run tests locally and verify the week view, multi-slot blocks, energy readings, editing and activity history. Do not automatically downgrade the database to a code version which expects older columns; pair code rollback with the appropriate pre-update backup. No GitHub Actions.

## v0.2.4 — recurring calendar and mobile UI

**Database migration v3 to v4** adds `recurring_rules` and `recurring_exceptions`, without rewriting existing diary entries or plans. Before upgrading, save a verified SQLite backup outside the container on NAS/PBS storage.

Inside the Fatigue Manager LXC (as root):

    cd /opt/fatigue-manager
    bash scripts/backup.sh
    bash scripts/update.sh

Verify service and schema:

    systemctl status fatigue-manager --no-pager
    sqlite3 /var/lib/fatigue-manager/fatigue.sqlite3 'PRAGMA user_version;'

Expected schema number: `4`. Also run local pytest in a temporary virtual environment and smoke-test the new calendar on phone and desktop: mobile layout, edit/delete dialog, current-time indicator, daily starting-energy default, recurring task generation and skipping single occurrences. Hard refresh the browser if an old JS/CSS bundle is cached.

To revert to an earlier code release which only understands schema v3, restore BOTH that code and the matching pre-migration database backup. No actions were run on existing containers other than the deployment steps the user chooses to execute.

## v0.2.5 — Calendar settings and A4 print

This release applies the v4→v5 SQLite migration on service startup: adds an `app_preferences` settings row; retains all diary, day-energy, planned and recurring records. Create a verified external backup **before** updating.

    cd /opt/fatigue-manager
    bash scripts/backup.sh
    bash scripts/update.sh
    sqlite3 /var/lib/fatigue-manager/fatigue.sqlite3 'PRAGMA user_version;'

Expected schema: **5**. Perform local pytest in a temporary virtual environment, then try the gear dialog, save setting preferences, Enter-to-save daily battery field, lookup of earlier calendar tasks, current-time rollover, and A4 print view. Browser hard reload if static assets are cached; asset query version is v0.2.5. Print CSS asks for zero margins but actual hardware may prevent borderless output.

If reverting to code that only supports schema v4, restore both its Git revision and a pre-update v4 database backup. No GitHub Actions or additional services are needed.
