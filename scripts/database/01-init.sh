#!/usr/bin/env bash
set -euo pipefail

# The bootstrap role owns the databases; app privileges are granted by migrations.
psql --username "$POSTGRES_USER" --dbname postgres --set ON_ERROR_STOP=1 \
  --set app_user="$APP_DB_USER" --set app_password="$APP_DB_PASSWORD" \
  --set app_db="$APP_DB_NAME" --set test_db="$TEST_DB_NAME" \
  --set bootstrap_user="$POSTGRES_USER" <<'SQL'
CREATE ROLE :"app_user" LOGIN PASSWORD :'app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE :"app_db" OWNER :"bootstrap_user";
CREATE DATABASE :"test_db" OWNER :"bootstrap_user";
GRANT CONNECT ON DATABASE :"app_db" TO :"app_user";
GRANT CONNECT ON DATABASE :"test_db" TO :"app_user";
SQL

for database in "$APP_DB_NAME" "$TEST_DB_NAME"; do
  psql --username "$POSTGRES_USER" --dbname "$database" --set ON_ERROR_STOP=1 \
    --set app_user="$APP_DB_USER" <<'SQL'
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO :"app_user";
SQL
done
