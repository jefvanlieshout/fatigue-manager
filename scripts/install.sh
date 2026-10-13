#!/usr/bin/env bash
set -Eeuo pipefail
[[ $(id -u) -eq 0 ]] || { echo "Run as root inside Debian LXC"; exit 1; }
cd /opt/fatigue-manager
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip git ca-certificates curl sqlite3 openssl
if ! id fatigue-manager >/dev/null 2>&1; then useradd --system --home-dir /var/lib/fatigue-manager --shell /usr/sbin/nologin fatigue-manager; fi
install -d -o fatigue-manager -g fatigue-manager -m 700 /var/lib/fatigue-manager
install -d -m 700 /var/backups/fatigue-manager
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
if [[ ! -e /etc/fatigue-manager.env ]]; then
  read -r -s -p 'Choose password (12+ characters): ' password; echo
  (( ${#password} >= 12 )) || { echo 'Password too short'; exit 1; }
  export FM_PASSWORD="$password"
  hash=$(.venv/bin/python -c 'import os;from app.main import hash_password;print(hash_password(os.environ["FM_PASSWORD"]))')
  unset password FM_PASSWORD
  secret=$(openssl rand -hex 32)
  umask 077
  printf 'FATIGUE_PASSWORD_HASH=%s\nFATIGUE_SESSION_SECRET=%s\nFATIGUE_DB_PATH=/var/lib/fatigue-manager/fatigue.sqlite3\nFATIGUE_TIMEZONE=Europe/Brussels\nFATIGUE_COOKIE_SECURE=0\n' "$hash" "$secret" > /etc/fatigue-manager.env
  chmod 600 /etc/fatigue-manager.env
fi
cat > /etc/systemd/system/fatigue-manager.service <<'EOF'
[Unit]
Description=Fatigue Manager diary
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=fatigue-manager
Group=fatigue-manager
WorkingDirectory=/opt/fatigue-manager
EnvironmentFile=/etc/fatigue-manager.env
ExecStart=/opt/fatigue-manager/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --no-server-header
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/fatigue-manager
UMask=0077
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now fatigue-manager
systemctl restart fatigue-manager
sleep 2
systemctl is-active --quiet fatigue-manager || { journalctl -u fatigue-manager -n 50 --no-pager; exit 1; }
echo 'Website: http://LXC-IP:8080 (trusted LAN only)'
