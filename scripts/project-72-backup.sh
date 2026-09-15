#!/usr/bin/env bash
set -euo pipefail
umask 077

usage() {
  cat >&2 <<'EOF'
Usage: project-72-backup.sh <output-dir>

Environment:
  MM7_MONGODB_URI             canonical subscriber MongoDB URI (required)
  MM7_IDEMPOTENCY_DB_URI      durable idempotency MongoDB URI (required)
  MM7_ESIM_DB_URI             optional eSIM metadata MongoDB URI
  MM7_BACKUP_ALLOW_REMOTE=1   required for non-localhost MongoDB URIs
EOF
  exit 2
}

[[ $# -eq 1 ]] || usage
OUT=$1
: "${MM7_MONGODB_URI:?MM7_MONGODB_URI is required}"
: "${MM7_IDEMPOTENCY_DB_URI:?MM7_IDEMPOTENCY_DB_URI is required}"

mkdir -p "$OUT"
chmod 700 "$OUT"

uri_host() {
  python3 - "$1" <<'PY'
from urllib.parse import urlparse
import sys
u=urlparse(sys.argv[1])
print(u.hostname or "")
PY
}

for uri in "$MM7_MONGODB_URI" "$MM7_IDEMPOTENCY_DB_URI" ${MM7_ESIM_DB_URI:+"$MM7_ESIM_DB_URI"}; do
  host=$(uri_host "$uri")
  case "$host" in
    localhost|127.0.0.1|::1) ;;
    *) [[ "${MM7_BACKUP_ALLOW_REMOTE:-0}" == "1" ]] || { echo "Refusing remote MongoDB backup without MM7_BACKUP_ALLOW_REMOTE=1" >&2; exit 1; } ;;
  esac
done

backup_db() {
  local uri=$1 name=$2
  local target="$OUT/$name"
  mkdir -p "$target"
  chmod 700 "$target"
  mongodump --uri="$uri" --archive="$target/database.archive" --gzip
  chmod 600 "$target/database.archive"
}

backup_db "$MM7_MONGODB_URI" canonical
backup_db "$MM7_IDEMPOTENCY_DB_URI" idempotency
if [[ -n "${MM7_ESIM_DB_URI:-}" ]]; then
  backup_db "$MM7_ESIM_DB_URI" esim-metadata
fi

# Back up configuration structure, never the secret store itself.
mkdir -p "$OUT/config"
cp -a core ims ran network subscribers "$OUT/config/"
find "$OUT/config" -type f -exec chmod 600 {} +
find "$OUT/config" -type d -exec chmod 700 {} +

cat > "$OUT/manifest.txt" <<EOF
Project-72 backup manifest
created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
secret_material=excluded
canonical=canonical/database.archive
idempotency=idempotency/database.archive
esim_metadata=${MM7_ESIM_DB_URI:+esim-metadata/database.archive}
EOF
chmod 600 "$OUT/manifest.txt"
sha256sum "$OUT"/*/database.archive > "$OUT/database.sha256"
chmod 600 "$OUT/database.sha256"

echo "Project-72 backup created: $OUT"
echo "Raw authentication, private keys and external secret-store contents are excluded."
