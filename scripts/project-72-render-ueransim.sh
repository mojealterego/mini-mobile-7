#!/usr/bin/env bash
set -euo pipefail

# Render deployment-local UERANSIM UE configs from the canonical seven-subscriber
# mapping. Authentication material is read from external environment variables
# and is never written to Git. Secrets are passed through file descriptor 3,
# not as process arguments or generated shell files.

OUT_DIR="${1:-runtime/ueransim}"
GNB_ADDRESS="${MM7_GNB_ADDRESS:-10.10.0.6}"
MCC="${MM7_MCC:-001}"
MNC="${MM7_MNC:-01}"

command -v python3 >/dev/null 2>&1 || { echo 'ERROR python3 is required' >&2; exit 1; }
mkdir -p "$OUT_DIR"

for slot in 1 2 3 4 5 6 7; do
    subscriber_id="700${slot}"
    imsi="00101000000000${slot}"
    secret_var="MM7_SECRET_MINI_MOBILE_7_700${slot}"
    output="${OUT_DIR}/ue-${subscriber_id}.yaml"

    secret_json="${!secret_var:-}"
    if [[ -z "$secret_json" ]]; then
        echo "ERROR missing external authentication reference for ${subscriber_id} (${secret_var})" >&2
        exit 1
    fi

    if python3 - "$imsi" "$MCC" "$MNC" "$GNB_ADDRESS" 3<<<"$secret_json" > "$output" <<'PY'
import ipaddress
import json
import re
import sys

imsi, mcc, mnc, gnb = sys.argv[1:]
with open(3, encoding="utf-8") as secret_stream:
    raw = secret_stream.read()
value = json.loads(raw)
if not isinstance(value, dict):
    raise SystemExit("authentication reference must resolve to an object")
for field in ("k", "opc", "amf"):
    if not isinstance(value.get(field), str) or not value[field]:
        raise SystemExit(f"authentication reference is missing {field}")
if not re.fullmatch(r"[0-9A-Fa-f]{32}", value["k"]):
    raise SystemExit("K must be exactly 32 hexadecimal characters")
if not re.fullmatch(r"[0-9A-Fa-f]{32}", value["opc"]):
    raise SystemExit("OPc must be exactly 32 hexadecimal characters")
if not re.fullmatch(r"[0-9A-Fa-f]{4}", value["amf"]):
    raise SystemExit("AMF must be exactly 4 hexadecimal characters")
if not re.fullmatch(r"[0-9]{3}", mcc) or not re.fullmatch(r"[0-9]{2,3}", mnc):
    raise SystemExit("MCC/MNC must be numeric PLMN components")
try:
    ipaddress.ip_address(gnb)
except ValueError as exc:
    raise SystemExit("gNB address must be a valid IP address") from exc
if not re.fullmatch(r"00101000000000[1-7]", imsi):
    raise SystemExit("IMSI is outside the MINI-MOBILE-7 seven-UE catalog")

print(f"# Generated deployment-local UERANSIM UE configuration for {imsi}")
print("# Authentication material came from an external secret reference.")
print("# This generated file must not be committed to Git.")
print("supi: 'imsi-" + imsi + "'")
print("mcc: '" + mcc + "'")
print("mnc: '" + mnc + "'")
print("key: '" + value["k"] + "'")
print("opc: '" + value["opc"] + "'")
print("amf: '" + value["amf"] + "'")
print("sessions:")
print("  - type: IPv4")
print("    apn: internet")
print("    slice:")
print("      sst: 1")
print("configured-nssai:")
print("  - sst: 1")
print("default-nssai:")
print("  - sst: 1")
print("gnbSearchList:")
print("  - " + gnb)
print("tunName: uesimtun-" + imsi[-4:])
print("integrity:")
print("  IA1: true")
print("  IA2: true")
print("  IA3: true")
print("ciphering:")
print("  EA1: true")
print("  EA2: true")
print("  EA3: true")
PY
    then
        :
    else
        rm -f "$output"
        echo "ERROR failed to render ${subscriber_id}" >&2
        exit 1
    fi

    chmod 600 "$output"
done

printf 'RENDERED %s\n' "$OUT_DIR"
