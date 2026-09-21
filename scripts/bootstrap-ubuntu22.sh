#!/usr/bin/env bash
set -euo pipefail

# MINI-MOBILE-7 deterministic Ubuntu 22.04 bootstrap.
# Open5GS is built from the exact v2.8.0 source tag instead of a floating PPA build.

OPEN5GS_VERSION="v2.8.0"
OPEN5GS_SRC="${OPEN5GS_SRC:-$HOME/src/open5gs-${OPEN5GS_VERSION}}"

if [[ "$(. /etc/os-release && echo "$VERSION_ID")" != "22.04" ]]; then
  echo "This bootstrap targets Ubuntu 22.04 only." >&2
  exit 1
fi

sudo apt update
sudo apt install -y ca-certificates curl gnupg git iproute2 iptables \
  python3-pip python3-setuptools python3-wheel ninja-build build-essential \
  flex bison cmake libsctp-dev libc-ares-dev libgnutls28-dev libgcrypt-dev \
  libssl-dev libmongoc-dev libbson-dev libyaml-dev libnghttp2-dev \
  libmicrohttpd-dev libcurl4-gnutls-dev libtins-dev libtalloc-dev meson

if apt-cache show libidn-dev >/dev/null 2>&1; then
  sudo apt install -y --no-install-recommends libidn-dev
else
  sudo apt install -y --no-install-recommends libidn11-dev
fi

# MongoDB 8.0 package line, matching the Open5GS Ubuntu guidance.
curl -fsSL https://pgp.mongodb.com/server-8.0.asc \
  | sudo gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor

echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/8.0 multiverse" \
  | sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list >/dev/null

sudo apt update
sudo apt install -y mongodb-org
sudo systemctl enable --now mongod

mkdir -p "$(dirname "$OPEN5GS_SRC")"
if [[ ! -d "$OPEN5GS_SRC/.git" ]]; then
  git clone --depth 1 --branch "$OPEN5GS_VERSION" https://github.com/open5gs/open5gs.git "$OPEN5GS_SRC"
else
  git -C "$OPEN5GS_SRC" fetch --tags --force
  git -C "$OPEN5GS_SRC" checkout "$OPEN5GS_VERSION"
fi

git -C "$OPEN5GS_SRC" describe --tags --exact-match | grep -Fx "$OPEN5GS_VERSION" >/dev/null
cd "$OPEN5GS_SRC"
rm -rf build
meson setup build --prefix=/usr --sysconfdir=/etc --localstatedir=/var
ninja -C build
sudo ninja -C build install
sudo ldconfig
sudo systemctl daemon-reload

# Create the lab TUN interface used for UE traffic.
if ! ip link show ogstun >/dev/null 2>&1; then
  sudo ip tuntap add name ogstun mode tun
fi
sudo ip addr replace 10.20.0.1/24 dev ogstun
sudo ip link set ogstun up

echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-mini-mobile-7.conf >/dev/null
sudo sysctl --system >/dev/null

printf '\nBootstrap complete: Open5GS %s built from source tag and MongoDB 8.0 installed.\n' "$OPEN5GS_VERSION"
printf 'Next: configure the core, provision one synthetic subscriber, and validate UERANSIM before any physical RF.\n'
