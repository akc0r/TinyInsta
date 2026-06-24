#!/usr/bin/env bash
# Create one DEDICATED database per service on the shared Postgres instance.
# Golden rule: a service never reads another service's database (logical isolation).
# Runs automatically on the first start of the postgres container.
set -euo pipefail

DATABASES=(
  user_svc
  interaction_svc
  stories_svc
  realtime_svc
  keycloak
)

for db in "${DATABASES[@]}"; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-SQL
    SELECT 'CREATE DATABASE $db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
SQL
  echo "ensured database: $db"
done
