#!/usr/bin/env sh
set -eu

if [ ! -f ./.env ]; then
  echo "Missing .env file in project root." >&2
  exit 1
fi

set -a
. ./.env
set +a

: "${POSTGRES_USER:?POSTGRES_USER must be set in .env}"
: "${TEST_DATABASE_URL:?TEST_DATABASE_URL must be set in .env}"

TEST_DB_ENV_FILE="$(mktemp)"
uv run python > "$TEST_DB_ENV_FILE" <<'PY'
import os
import shlex
from urllib.parse import urlparse

url = urlparse(os.environ["TEST_DATABASE_URL"])
user = url.username or os.environ.get("POSTGRES_USER", "postgres")
password = url.password or ""
db_name = (url.path or "").lstrip("/")
user_ident = '"' + user.replace('"', '""') + '"'
password_literal = "'" + password.replace("'", "''") + "'"
db_name_literal = "'" + db_name.replace("'", "''") + "'"

values = {
    "TEST_DATABASE_USER": user,
    "TEST_DATABASE_PASSWORD": password,
    "TEST_DATABASE_NAME": db_name,
    "TEST_DATABASE_USER_IDENT": user_ident,
    "TEST_DATABASE_PASSWORD_LITERAL": password_literal,
    "TEST_DATABASE_NAME_LITERAL": db_name_literal,
}

for key, value in values.items():
    print(f"{key}={shlex.quote(value)}")
PY
. "$TEST_DB_ENV_FILE"
rm -f "$TEST_DB_ENV_FILE"

if [ -z "$TEST_DATABASE_NAME" ]; then
  echo "Could not determine test database name from TEST_DATABASE_URL." >&2
  exit 1
fi

case "$TEST_DATABASE_NAME" in
  *_test) ;;
  *)
    echo "Refusing to run integration tests: test database name must end with '_test'." >&2
    exit 1
    ;;
esac

if [ "${POSTGRES_DB:-}" = "$TEST_DATABASE_NAME" ]; then
  echo "Refusing to run integration tests: TEST_DATABASE_URL points at POSTGRES_DB." >&2
  exit 1
fi

if [ -z "$TEST_DATABASE_PASSWORD" ]; then
  echo "Could not determine test database password from TEST_DATABASE_URL." >&2
  exit 1
fi

docker compose up -d db

POSTGRES_READY_DB="${POSTGRES_DB:-postgres}"
POSTGRES_READY_ATTEMPTS=24
attempt=1

echo "Waiting for Postgres to accept connections..."
while [ "$attempt" -le "$POSTGRES_READY_ATTEMPTS" ]; do
  if docker compose exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_READY_DB" >/dev/null 2>&1; then
    break
  fi

  if [ "$attempt" -eq "$POSTGRES_READY_ATTEMPTS" ]; then
    echo "Postgres did not become ready in time." >&2
    docker compose logs db >&2
    exit 1
  fi

  attempt=$((attempt + 1))
  sleep 1
done

# The Postgres image applies POSTGRES_PASSWORD only when the Docker volume is first initialized.
# Keep the existing local volume usable by aligning the DB user with TEST_DATABASE_URL.
docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "ALTER USER $TEST_DATABASE_USER_IDENT WITH PASSWORD $TEST_DATABASE_PASSWORD_LITERAL;"

if ! docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = $TEST_DATABASE_NAME_LITERAL" | grep -q 1; then
  docker compose exec -T db createdb -U "$POSTGRES_USER" "$TEST_DATABASE_NAME"
fi

uv run pytest tests/integration "$@"
