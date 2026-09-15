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

for service in mongod open5gs-amfd open5gs-smfd open5gs-upfd kamailio asterisk; do
  write_cmd "service-${service}" systemctl status "$service" --no-pager
  write_cmd "service-${service}-active" systemctl is-active "$service"
done

if command -v mongosh >/dev/null 2>&1; then
  write_cmd mongodb-version mongosh --quiet --eval 'db.version()'
fi

if [[ -d runtime/ueransim ]]; then
  find runtime/ueransim -maxdepth 1 -type f -name 'ue-*.yaml' -print0 \
    | sort -z \
    | while IFS= read -r -d '' file; do
        stat -c '%a %n' "$file"
        sha256sum "$file"
      done >"$OUT_DIR/ueransim-files.txt"
fi

systemctl list-units --type=service --state=running --no-pager >"$OUT_DIR/running-services.txt" 2>&1 || true
printf 'Evidence written to %s\n' "$OUT_DIR"
