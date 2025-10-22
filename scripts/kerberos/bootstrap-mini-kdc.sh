#!/usr/bin/env bash
set -euo pipefail

KDC_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
COMPOSE_FILE="$KDC_DIR/docker-compose.mini-kdc.yml"
SERVICE_NAME="mini-kdc"
REALM=${REALM:-EXAMPLE.COM}
PRINCIPAL=${PRINCIPAL:-hive/localhost@$REALM}
KEYTAB_NAME=${KEYTAB_NAME:-hive.service.keytab}

if ! command -v docker >/dev/null 2>&1; then
  echo "[bootstrap-mini-kdc] docker is required but not found in PATH" >&2
  exit 1
fi

echo "[bootstrap-mini-kdc] Starting Kerberos KDC ($REALM)..."
docker compose -f "$COMPOSE_FILE" up -d

echo "[bootstrap-mini-kdc] Waiting for KDC to become healthy..."
until docker compose -f "$COMPOSE_FILE" ps --format '{{.ID}} {{.Name}} {{.Health}}' | grep -q "$SERVICE_NAME"; do
  sleep 2
done

# Give the container a few seconds to finish booting the KDC daemons
sleep 3

echo "[bootstrap-mini-kdc] Creating service principal $PRINCIPAL"
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" kadmin.local -q "addprinc -randkey $PRINCIPAL" || true

echo "[bootstrap-mini-kdc] Exporting keytab to /keytabs/$KEYTAB_NAME"
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" kadmin.local -q "ktadd -k /keytabs/$KEYTAB_NAME $PRINCIPAL"

HOST_KEYTAB="$KDC_DIR/keytabs/$KEYTAB_NAME"
if [ -f "$HOST_KEYTAB" ]; then
  echo "[bootstrap-mini-kdc] Keytab available at $HOST_KEYTAB"
else
  echo "[bootstrap-mini-kdc] Keytab export failed" >&2
  exit 2
fi

echo "[bootstrap-mini-kdc] Done. Use REALM=$REALM, principal=$PRINCIPAL"
