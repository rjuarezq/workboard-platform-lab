#!/usr/bin/env sh

set -eu

psql \
  --set=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=database_name="$POSTGRES_DB" \
  --set=migrator_password="$WORKBOARD_MIGRATOR_DB_PASSWORD" \
  --set=app_password="$WORKBOARD_APP_DB_PASSWORD" \
  --file /opt/workboard-bootstrap/create-roles.sql