#!/usr/bin/env bash
set -Eeuo pipefail
[[ $(id -u) -eq 0 ]] || exit 1
cd /opt/fatigue-manager
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo 'Tracked files modified. Refusing update'; exit 1; }
git fetch origin main
old=$(git rev-parse HEAD)
new=$(git rev-parse origin/main)
[[ "$old" != "$new" ]] || { echo 'Already up to date'; exit 0; }
git merge-base --is-ancestor "$old" "$new" || { echo 'Not a fast-forward'; exit 1; }
bash scripts/backup.sh
git merge --ff-only origin/main
.venv/bin/pip install -r requirements.txt
systemctl restart fatigue-manager
sleep 2
systemctl is-active --quiet fatigue-manager && curl -fsS http://127.0.0.1:8080/healthz || { echo "Update failed; previous commit $old; see deployment guide for restore"; exit 1; }
echo 'Update complete'
