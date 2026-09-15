#!/usr/bin/env bash
set -euo pipefail

fail() { echo "SECURITY GATE: FAIL: $*" >&2; exit 1; }
check_file() { test -f "$1" || fail "missing required file: $1"; }
check_dir() { test -d "$1" || fail "missing required directory: $1"; }

check_dir "core/open5gs"
check_file "ims/kamailio/kamailio.cfg.example"
check_file "ims/kamailio/dispatcher.list.example"
check_file "ims/asterisk/pjsip.conf.example"
check_file "scripts/project-72-render-ueransim.sh"
check_file "scripts/project-72-render-asterisk-pjsip.sh"

if grep -RInE '(:latest([[:space:]"'"'\]|$)|ppa:[^[:space:]]+/latest)' core ims ran scripts network --include='*.yml' --include='*.yaml' --include='*.yaml.example' --include='*.conf' --include='*.list' --include='*.sh' --exclude='project-72-security-check.sh' 2>/dev/null; then
  fail "floating latest package/image reference detected"
fi

if grep -RInE '(password[[:space:]]*=[[:space:]]*[^$[:space:]#]+|secret(_key)?[[:space:]]*=[[:space:]]*[^$[:space:]#]+|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)' core ims ran subscribers network --exclude='*.md' 2>/dev/null; then
  fail "possible checked-in credential/private-key literal detected"
fi

if grep -RInE '(^|[^0-9])0\.0\.0\.0:(5060|5061)([^0-9]|$)|host_network[[:space:]]*[:=][[:space:]]*true|network_mode[[:space:]]*[:=][[:space:]]*["'"']host|privileged[[:space:]]*[:=][[:space:]]*true' core ims ran scripts network --include='*.yml' --include='*.yaml' --include='*.yaml.example' --include='*.conf' --include='*.list' --include='*.sh' --exclude='project-72-security-check.sh' 2>/dev/null; then
  fail "public IMS bind or unsafe host/privileged default detected"
fi

grep -Fq 'Private IMS Network Required' ims/kamailio/kamailio.cfg.example || fail "Kamailio private IMS ACL missing"
grep -Fq 'sip:10.40.0.20:5061;transport=tls' ims/kamailio/dispatcher.list.example || fail "private TLS dispatcher target missing"
grep -Fq 'media_encryption=sdes' ims/asterisk/pjsip.conf.example || fail "Asterisk SRTP/SDES baseline missing"
grep -Fq 'direct_media=no' ims/asterisk/pjsip.conf.example || fail "Asterisk direct-media isolation baseline missing"

echo "Project-72 static security/isolation gate: PASS"
echo "Live firewall rules, service permissions and network exposure still require host evidence."
