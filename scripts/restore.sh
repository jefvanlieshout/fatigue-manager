#!/usr/bin/env bash
set -Eeuo pipefail
[[ $(id -u) -eq 0 && $# -eq 1 && -f "$1" ]] || { echo 'Usage: root restore.sh /path/backup.sqlite3'; exit 1; }
file=$(realpath "$1")
[[ "$(sqlite3 "$file" 'PRAGMA integrity_check;')" == ok ]] || { echo 'Bad backup'; exit 1; }
systemctl stop fatigue-manager
dst=/var/lib/fatigue-manager/fatigue.sqlite3
[[ ! -f "$dst" ]] || cp -a "$dst" "$dst.before-restore.$(date -u +%Y%m%dT%H%M%SZ)"
rm -f "$dst-wal" "$dst-shm"
cp "$file" "$dst"
chown fatigue-manager:fatigue-manager "$dst"
chmod 600 "$dst"
systemctl start fatigue-manager
echo 'Restored'
