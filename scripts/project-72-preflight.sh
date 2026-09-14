#!/usr/bin/env bash
set -euo pipefail

fail=0
warn=0

ok() { printf 'OK   %s\n' "$1"; }
warn() { printf 'WARN %s\n' "$1"; warn=$((warn + 1)); }
block() { printf 'BLOCK %s\n' "$1"; fail=$((fail + 1)); }

printf '%s\n' '== MINI-MOBILE-7 Project-72 runtime preflight =='

if [[ -f /etc/os-release ]]; then
  . /etc/os-release
  if [[ "${VERSION_ID:-}" == "22.04" ]]; then
    ok "Ubuntu 22.04 (${VERSION_CODENAME:-unknown})"
  else
    block "Ubuntu 22.04 required; detected ${NAME:-unknown} ${VERSION_ID:-unknown}"
  fi
else
  block '/etc/os-release is missing'
fi

for cmd in ip systemctl sysctl iptables python3; do
  if command -v "$cmd" >/dev/null 2>&1; then ok "command $cmd"; else block "missing command: $cmd"; fi
done

if command -v mongod >/dev/null 2>&1 || systemctl list-unit-files mongod.service >/dev/null 2>&1; then
  ok 'MongoDB installation detected'
else
  block 'MongoDB (mongod) not detected'
fi

if systemctl is-active --quiet mongod; then
  ok 'mongod active'
else
  block 'mongod is not active'
fi

if command -v open5gs-amfd >/dev/null 2>&1 && [[ -d /etc/open5gs ]]; then
  ok 'Open5GS AMF binary and /etc/open5gs present'
else
  block 'Open5GS AMF binary or /etc/open5gs missing'
fi

if systemctl list-unit-files 'open5gs-*.service' --no-legend 2>/dev/null | grep -q 'open5gs-'; then
  ok 'Open5GS systemd units detected'
else
  block 'no Open5GS systemd units detected'
fi

if ip link show ogstun >/dev/null 2>&1; then
  ok 'ogstun interface present'
else
  block 'ogstun interface missing'
fi

if ip -4 addr show dev ogstun 2>/dev/null | grep -Eq 'inet 10\.20\.0\.1/24([[:space:]]|$)'; then
  ok 'ogstun has 10.20.0.1/24'
else
  block 'ogstun does not have 10.20.0.1/24'
fi

if sysctl -n net.ipv4.ip_forward 2>/dev/null | grep -qx '1'; then
  ok 'IPv4 forwarding enabled'
else
  block 'IPv4 forwarding is disabled'
fi

if ip route show 10.20.0.0/24 2>/dev/null | grep -q 'dev ogstun'; then
  ok 'UE subnet 10.20.0.0/24 routed via ogstun'
else
  block 'UE subnet route 10.20.0.0/24 via ogstun missing'
fi

if iptables -S >/dev/null 2>&1; then
  ok 'iptables policy readable'
  input_policy=$(iptables -S INPUT 2>/dev/null | awk '$1=="-P" && $2=="INPUT" {print $3; exit}')
  if [[ "$input_policy" == 'DROP' || "$input_policy" == 'REJECT' ]]; then
    ok "INPUT default policy is $input_policy"
  else
    warn "INPUT default policy is ${input_policy:-unknown}; verify fail-closed firewall rules before execution"
  fi
else
  block 'unable to read iptables policy'
fi

if python3 - <<'PY'
try:
    import pymongo  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
then
  ok 'Python pymongo module available'
else
  block 'Python pymongo module missing'
fi

MM7_MONGODB_URI="${MM7_MONGODB_URI:-mongodb://localhost/open5gs}"
export MM7_MONGODB_URI

if python3 - <<'PY'
import os
import sys
try:
    from pymongo import MongoClient
    client = MongoClient(os.environ["MM7_MONGODB_URI"], serverSelectionTimeoutMS=2000)
    client.admin.command("ping")
except Exception as exc:
    print(f"MongoDB ping failed: {exc}", file=sys.stderr)
    raise SystemExit(1)
PY
then
  ok "MongoDB reachable via MM7_MONGODB_URI"
else
  block 'MongoDB is not reachable using MM7_MONGODB_URI'
fi

if [[ -n "${MM7_IDEMPOTENCY_DB_URI:-}" ]]; then
  export MM7_IDEMPOTENCY_DB_URI
  if python3 - <<'PY'
import os
import sys
try:
    from pymongo import MongoClient
    client = MongoClient(os.environ["MM7_IDEMPOTENCY_DB_URI"], serverSelectionTimeoutMS=2000)
    client.admin.command("ping")
except Exception as exc:
    print(f"Idempotency MongoDB ping failed: {exc}", file=sys.stderr)
    raise SystemExit(1)
PY
  then
    ok 'durable idempotency MongoDB reachable via MM7_IDEMPOTENCY_DB_URI'
  else
    block 'durable idempotency MongoDB is not reachable using MM7_IDEMPOTENCY_DB_URI'
  fi
else
  block 'MM7_IDEMPOTENCY_DB_URI is required for runtime execution'
fi

if [[ "${MM7_SKIP_SECRET_PREFLIGHT:-0}" == '1' ]]; then
  warn 'secret preflight explicitly skipped by MM7_SKIP_SECRET_PREFLIGHT=1'
else
  if PYTHONPATH=. python3 - <<'PY'
from project_72.assurance_core.catalog import build_seven_subscriber_catalog
from adapters.open5gs.secrets import EnvironmentSecretResolver, SecretResolutionError

resolver = EnvironmentSecretResolver()
failed = []
for subscriber in build_seven_subscriber_catalog():
    try:
        value = resolver.resolve(subscriber.secret_refs["authentication"])
        if not all(value.get(key) for key in ("k", "opc", "amf")):
            failed.append(subscriber.subscriber_id)
    except SecretResolutionError:
        failed.append(subscriber.subscriber_id)
if failed:
    print("unresolved authentication secret refs:", ",".join(failed))
    raise SystemExit(1)
PY
  then
    ok 'authentication secret refs resolve for all seven subscribers (values not printed)'
  else
    block 'one or more authentication secret refs cannot be resolved'
  fi
fi

printf 'RESULT fail=%d warn=%d\n' "$fail" "$warn"
if (( fail > 0 )); then
  printf '%s\n' 'PREFLIGHT BLOCKED: do not run runtime provisioning.'
  exit 1
fi
printf '%s\n' 'PREFLIGHT PASS: runtime provisioning may proceed only on the controlled lab host.'
