#!/usr/bin/env bash
set -Eeuo pipefail
[[ $(id -u) -eq 0 ]] || exit 1
src=/var/lib/fatigue-manager/fatigue.sqlite3
dst=/var/backups/fatigue-manager
install -d -m 700 "$dst"
[[ -e "$src" ]] || { echo 'No database yet'; exit 0; }
python3 - "$src" "$dst/$(date -u +%Y%m%dT%H%M%SZ).sqlite3" <<'PY'
import sqlite3,sys
src=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
dst=sqlite3.connect(sys.argv[2])
with dst: src.backup(dst)
dst.close();src.close()
PY
chmod 600 "$dst"/*.sqlite3
find "$dst" -maxdepth 1 -type f -name '*.sqlite3' -printf '%T@ %p\n' | sort -rn | tail -n +31 | cut -d' ' -f2- | while IFS= read -r file; do rm -f -- "$file"; done
echo "Backup complete in $dst"
