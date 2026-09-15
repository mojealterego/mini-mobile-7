#!/usr/bin/env bash
set -euo pipefail

# Read-only diagnostic. It does not install packages, change interfaces,
# start services, alter firewall rules, or modify kernel/network state.

fail=0
warn=0

ok() { printf 'OK    %s\n' "$1"; }
warn() { printf 'WARN  %s\n' "$1"; warn=$((warn + 1)); }
block() { printf 'BLOCK %s\n' "$1"; fail=$((fail + 1)); }

printf '%s\n' '=== MINI-MOBILE-7 Project-72 runtime capability report ==='

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  printf 'OS=%s %s\n' "${NAME:-unknown}" "${VERSION_ID:-unknown}"
else
  block '/etc/os-release is not readable'
fi

printf 'ARCH=%s\n' "$(uname -m 2>/dev/null || printf unknown)"
printf 'KERNEL=%s\n' "$(uname -r 2>/dev/null || printf unknown)"
printf 'PID1=%s\n' "$(cat /proc/1/comm 2>/dev/null || printf unavailable)"

if command -v systemctl >/dev/null 2>&1; then
  ok 'systemctl command present'
  if systemctl is-system-running >/dev/null 2>&1; then
    ok 'systemd is operational'
  else
    state=$(systemctl is-system-running 2>/dev/null || true)
    if [[ -n "$state" ]]; then
      block "systemd is not operational (state=$state)"
    else
      block 'systemd is not operational'
    fi
  fi
else
  block 'systemctl command missing'
fi

if [[ -r /proc/1/cgroup ]]; then
  if grep -q '^0::/' /proc/1/cgroup; then
    ok 'cgroup v2 hierarchy visible'
  else
    warn 'cgroup v2 unified hierarchy not visible from PID 1'
  fi
else
  block '/proc/1/cgroup is not readable'
fi

if [[ -e /dev/kvm ]]; then
  if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    ok '/dev/kvm is accessible'
  else
    warn '/dev/kvm exists but is not both readable and writable'
  fi
else
  warn '/dev/kvm is absent; hardware-accelerated KVM virtualization is unavailable'
fi

if [[ -e /dev/net/tun ]]; then
  if [[ -r /dev/net/tun && -w /dev/net/tun ]]; then
    ok '/dev/net/tun is accessible'
  else
    block '/dev/net/tun exists but is not both readable and writable'
  fi
else
  block '/dev/net/tun is absent'
fi

if command -v ip >/dev/null 2>&1; then
  ok 'ip command present'
  if ip -4 route >/dev/null 2>&1; then
    ok 'IPv4 route inspection is permitted'
  else
    block 'IPv4 route inspection is not permitted'
  fi
  if ip link show >/dev/null 2>&1; then
    ok 'network link inspection is permitted'
  else
    block 'network link inspection is not permitted'
  fi
else
  block 'ip command missing'
fi

if [[ -r /proc/sys/net/ipv4/ip_forward ]]; then
  ok 'IPv4 forwarding sysctl is readable'
else
  block 'IPv4 forwarding sysctl is not readable'
fi

if command -v iptables >/dev/null 2>&1; then
  if iptables -S >/dev/null 2>&1; then
    ok 'iptables policy inspection is permitted'
  else
    block 'iptables policy inspection is not permitted'
  fi
else
  block 'iptables command missing'
fi

if command -v ss >/dev/null 2>&1; then
  if ss -H -lntup >/dev/null 2>&1; then
    ok 'listening-socket inspection is permitted'
  else
    warn 'listening-socket inspection is restricted or unavailable'
  fi
else
  warn 'ss command missing'
fi

if [[ -r /proc/net/sctp/assocs ]]; then
  ok 'kernel SCTP state is visible'
else
  warn 'kernel SCTP association state is not visible'
fi

if [[ -r /proc/self/status ]] && grep -Eq '^CapEff:[[:space:]]+[0-9a-fA-F]+$' /proc/self/status; then
  cap_eff=$(awk '/^CapEff:/ {print $2; exit}' /proc/self/status)
  printf 'CAP_EFF=%s\n' "$cap_eff"
else
  warn 'effective capability mask is not readable'
fi

printf 'RESULT block=%d warn=%d\n' "$fail" "$warn"
if (( fail > 0 )); then
  printf '%s\n' 'RUNTIME CAPABILITY RESULT: BLOCKED'
  printf '%s\n' 'This environment is not suitable for Project-72 live runtime acceptance.'
  exit 1
fi

printf '%s\n' 'RUNTIME CAPABILITY RESULT: NO HARD BLOCKS DETECTED'
printf '%s\n' 'Run project-72-preflight.sh before any runtime provisioning.'
