#!/usr/bin/env bash
# Run on Proxmox HOST. Does not alter existing containers.
set -Eeuo pipefail
[[ $(id -u) -eq 0 ]] && command -v pct >/dev/null || { echo 'Run as root on Proxmox host'; exit 1; }
ID="${1:-120}"
[[ "$ID" =~ ^[0-9]{3,}$ ]] || exit 1
if pct status "$ID" >/dev/null 2>&1; then echo "CT $ID already exists; refusing overwrite"; exit 1; fi
TEMPLATE_STORAGE="${TEMPLATE_STORAGE:-local}"
ROOTFS_STORAGE="${ROOTFS_STORAGE:-local-lvm}"
BRIDGE="${BRIDGE:-vmbr0}"
pveam update
template=$(pveam available --section system | awk '$2 ~ /debian-13-standard.*amd64.tar.zst$/ {print $2}' | sort -V | tail -n 1)
if [[ -z "$template" ]]; then
  template=$(pveam available --section system | awk '$2 ~ /debian-12-standard.*amd64.tar.zst$/ {print $2}' | sort -V | tail -n 1)
fi
[[ -n "$template" ]] || { echo 'No supported Debian template'; exit 1; }
if ! pveam list "$TEMPLATE_STORAGE" | grep -Fq "$template"; then pveam download "$TEMPLATE_STORAGE" "$template"; fi
pct create "$ID" "${TEMPLATE_STORAGE}:vztmpl/$template" --hostname fatigue-manager --cores 1 --memory 512 --swap 256 --rootfs "${ROOTFS_STORAGE}:8" --net0 "name=eth0,bridge=${BRIDGE},ip=dhcp" --unprivileged 1 --ostype debian --onboot 1
pct start "$ID"
echo "Container $ID running. Next: pct enter $ID"
