#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-runtime/evidence}"
umask 077
mkdir -p "$OUT_DIR"

write_cmd() {
  local name="$1"
  shift
  {
    printf '$'
    printf ' %q' "$@"
    printf '\n'
    if ! command -v "$1" >/dev/null 2>&1; then
      printf 'UNAVAILABLE: command not found: %s\n' "$1"
      return 0
    fi
    "$@"
  } >"$OUT_DIR/${name}.txt" 2>&1 || true
}

{
  printf '%s\n' 'MINI-MOBILE-7 Project-72 host evidence'
  printf '%s\n' 'Read-only collection. Authentication material is not intentionally collected.'
  printf 'collected_at=%s\n' "$(date --iso-8601=seconds)"
} >"$OUT_DIR/README.txt"

write_cmd os-release cat /etc/os-release
write_cmd kernel uname -a
write_cmd ip-address ip -br address
write_cmd ip-route ip -4 route
write_cmd ogstun-address ip -4 addr show dev ogstun
write_cmd forwarding sysctl net.ipv4.ip_forward
write_cmd firewall iptables -S
write_cmd listening-sockets ss -lntup

if [[ -f scripts/project-72-runtime-capabilities.sh ]]; then
  bash scripts/project-72-runtime-capabilities.sh >"$OUT_DIR/runtime-capabilities.txt" 2>&1 || true
else
  printf '%s\n' 'UNAVAILABLE: scripts/project-72-runtime-capabilities.sh is missing' >"$OUT_DIR/runtime-capabilities.txt"
fi

for service in mongod open5gs-amfd open5gs-smfd open5gs-upfd kamailio asterisk; do
  if command -v systemctl >/dev/null 2>&1; then
    write_cmd "service-${service}" systemctl status "$service" --no-pager
    write_cmd "service-${service}-active" systemctl is-active "$service"
  else
    {
      printf '$ systemctl status %q --no-pager\n' "$service"
      printf '%s\n' 'UNAVAILABLE: systemctl is not present on this host'
    } >"$OUT_DIR/service-${service}.txt"
    {
      printf '$ systemctl is-active %q\n' "$service"
      printf '%s\n' 'UNAVAILABLE: systemctl is not present on this host'
    } >"$OUT_DIR/service-${service}-active.txt"
  fi
done

if command -v mongosh >/dev/null 2>&1; then
  write_cmd mongodb-version mongosh --quiet --eval 'db.version()'
else
  printf '%s\n' 'UNAVAILABLE: command not found: mongosh' >"$OUT_DIR/mongodb-version.txt"
fi

if [[ -d runtime/ueransim ]]; then
  find runtime/ueransim -maxdepth 1 -type f -name 'ue-*.yaml' -print0 \
    | sort -z \
    | while IFS= read -r -d '' file; do
        stat -c '%a %n' "$file"
        sha256sum "$file"
      done >"$OUT_DIR/ueransim-files.txt"
fi

if command -v systemctl >/dev/null 2>&1; then
  systemctl list-units --type=service --state=running --no-pager >"$OUT_DIR/running-services.txt" 2>&1 || true
else
  printf '%s\n' 'UNAVAILABLE: systemctl is not present on this host' >"$OUT_DIR/running-services.txt"
fi

printf 'Evidence written to %s\n' "$OUT_DIR"
