#!/usr/bin/env bash
set -euo pipefail

# Create 10 compression-test tables and 10 archive-test tables on a CDP Hive cluster via beeline.
#
# Requirements:
# - beeline in PATH
# - A reachable HiveServer2 JDBC URL
# - Proper auth (simple user/pass or Kerberos principal)
#
# Usage examples:
#   scripts/ops/create_cdp_test_tables.sh \
#     --jdbc "jdbc:hive2://cdp-14.example.com:10000/default" \
#     --db cdp14_lab --prefix cdp14
#
#   # Kerberos (HS2 with SPNEGO/principal)
#   kinit your_user@EXAMPLE.COM
#   scripts/ops/create_cdp_test_tables.sh \
#     --jdbc "jdbc:hive2://cdp-14.example.com:10000/default;principal=hive/_HOST@EXAMPLE.COM" \
#     --db cdp14_lab --prefix cdp14
#
#   # Simple auth (if enabled)
#   scripts/ops/create_cdp_test_tables.sh \
#     --jdbc "jdbc:hive2://cdp-14.example.com:10000/default" \
#     --user hive --pass yourpass --db cdp14_lab --prefix cdp14

print_usage() {
  cat <<'USAGE'
Create 10 compression-test tables and 10 archive-test tables in Hive (CDP).

Required:
  --jdbc <JDBC_URL>         HiveServer2 JDBC URL (beeline). For Kerberos, include ;principal=...

Optional:
  --db <DB_NAME>            Target database (default: cdp14_lab)
  --prefix <PREFIX>         Table name prefix (default: cdp14)
  --user <USER>             Simple auth user (if HS2 allows)
  --pass <PASS>             Simple auth password

Examples:
  scripts/ops/create_cdp_test_tables.sh \
    --jdbc "jdbc:hive2://cdp-14.example.com:10000/default" \
    --db cdp14_lab --prefix cdp14

  kinit your_user@EXAMPLE.COM
  scripts/ops/create_cdp_test_tables.sh \
    --jdbc "jdbc:hive2://cdp-14.example.com:10000/default;principal=hive/_HOST@EXAMPLE.COM" \
    --db cdp14_lab --prefix cdp14
USAGE
}

JDBC_URL=""
DB_NAME="cdp14_lab"
PREFIX="cdp14"
USER_NAME=""
USER_PASS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --jdbc)
      JDBC_URL="$2"; shift 2 ;;
    --db)
      DB_NAME="$2"; shift 2 ;;
    --prefix)
      PREFIX="$2"; shift 2 ;;
    --user)
      USER_NAME="$2"; shift 2 ;;
    --pass)
      USER_PASS="$2"; shift 2 ;;
    -h|--help)
      print_usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      print_usage; exit 1 ;;
  esac
done

if [[ -z "$JDBC_URL" ]]; then
  echo "ERROR: --jdbc is required." >&2
  print_usage
  exit 1
fi

if ! command -v beeline >/dev/null 2>&1; then
  echo "ERROR: beeline not found in PATH. Please ensure Hive client is installed." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HQL_FILE="$SCRIPT_DIR/hql/create_cdp_test_tables.hql"

if [[ ! -f "$HQL_FILE" ]]; then
  echo "ERROR: HQL file not found: $HQL_FILE" >&2
  exit 1
fi

echo "Target JDBC: $JDBC_URL"
echo "Database:    $DB_NAME"
echo "Table prefix: $PREFIX"

BEELINE_ARGS=( -u "$JDBC_URL" --hivevar DB="$DB_NAME" --hivevar PREFIX="$PREFIX" -f "$HQL_FILE" )

if [[ -n "$USER_NAME" ]]; then
  BEELINE_ARGS=( -u "$JDBC_URL" -n "$USER_NAME" -p "$USER_PASS" --hivevar DB="$DB_NAME" --hivevar PREFIX="$PREFIX" -f "$HQL_FILE" )
fi

echo "Running beeline to create tables..."
beeline "${BEELINE_ARGS[@]}"

echo "\nAll requested tables created (or already existed)."
echo "Database: $DB_NAME"
echo "Compression tables: 10"
echo "Archive tables:     10"

