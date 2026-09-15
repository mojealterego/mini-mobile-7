#!/usr/bin/env bash
set -euo pipefail

# Static IMS safety gate. This does not claim live SIP/TLS/SRTP operation.
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
KAMAILIO_CFG="$ROOT_DIR/ims/kamailio/kamailio.cfg.example"
ASTERISK_CFG="$ROOT_DIR/ims/asterisk/pjsip.conf.example"
DISPATCHER="$ROOT_DIR/ims/kamailio/dispatcher.list.example"
RENDERER="$ROOT_DIR/scripts/project-72-render-asterisk-pjsip.sh"

for file in "$KAMAILIO_CFG" "$ASTERISK_CFG" "$DISPATCHER" "$RENDERER"; do
  test -f "$file" || { echo "missing IMS file: $file" >&2; exit 1; }
done

# The checked-in templates must not expose SIP services on wildcard/public binds.
if grep -En '(^|[[:space:]])(bind|listen)[[:space:]]*[=:][[:space:]]*0\.0\.0\.0|0\.0\.0\.0:506[01]' \
    "$KAMAILIO_CFG" "$ASTERISK_CFG" "$DISPATCHER"; then
  echo "wildcard/public SIP bind detected" >&2
  exit 1
fi

# Private IMS routing and encrypted Asterisk service boundary are mandatory.
grep -Fq '10\\.40\\.0\\.' "$KAMAILIO_CFG"
grep -Fq 'is_method("REGISTER")' "$KAMAILIO_CFG"
grep -Fq 'sip:10.40.0.20:5061;transport=tls' "$DISPATCHER"
grep -Fq 'protocol=tls' "$ASTERISK_CFG"
grep -Fq 'bind=10.40.0.20:5061' "$ASTERISK_CFG"
grep -Fq 'media_encryption=sdes' "$ASTERISK_CFG"
grep -Fq 'media_encryption_optimistic=no' "$ASTERISK_CFG"
grep -Fq 'direct_media=no' "$ASTERISK_CFG"

# Checked-in configuration must use deployment-time credentials, never literal passwords.
if grep -Eiq '(^|[[:space:]])password[[:space:]]*=[[:space:]]*[^$[:space:];]+' "$ASTERISK_CFG"; then
  echo "literal Asterisk password detected in checked-in template" >&2
  exit 1
fi

# Architecture must remain private: no PSTN/public-PLMN gateway is part of the IMS template.
if grep -Eiq '(^|[^A-Za-z])(pstn|public[[:space:]-]*plmn|tel:[+][0-9])' \
    "$KAMAILIO_CFG" "$ASTERISK_CFG" "$DISPATCHER"; then
  echo "public telephony gateway marker detected in IMS template" >&2
  exit 1
fi

echo "IMS static safety gate: PASS"
echo "Live SIP registration, TLS certificate validation, SRTP negotiation and calls require host acceptance."
