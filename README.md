# Backend Engineering Assignment

A FastAPI backend service for the backend engineering assignment. The app exposes a root endpoint, a health check endpoint, and versioned API routes mounted from `app/api/v1`.

## Requirements

To run the app:

- Docker
- Docker Compose

To run tests:

- Python 3.12 or newer
- [`uv`](https://docs.astral.sh/uv/) for dependency management

## Setup

Create a `.env` file in the project root. Docker Compose uses this file for both the API and PostgreSQL services.

Common settings include:

```env
APP_NAME=backend-eng-assignment
APP_HOST=0.0.0.0
APP_PORT=8000
APP_RELOAD=false
LOG_LEVEL=INFO
LOG_API_REQUESTS=true
DATABASE_DRIVER=postgresql+asyncpg
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=backend_eng_assignment
JWT_SECRET_KEY=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## Run the application with Docker Compose

Start the API and PostgreSQL database with:

```bash
docker compose up --build
```

Docker Compose will:

- build the API image from `Dockerfile`
- start a PostgreSQL 16 container named `db`
- wait for PostgreSQL to become healthy
- run Alembic migrations with `alembic upgrade head`
- start the FastAPI app with Uvicorn

By default, the app is available at:

```text
http://127.0.0.1:8000
```

After the app starts, open the interactive API documentation in a browser at:

```text
http://127.0.0.1:8000/docs
```

Useful endpoints:

- `GET /` — confirms the application is running
- `GET /health` — health check endpoint
- `GET /docs` — interactive FastAPI/OpenAPI documentation

Run the containers in the background with:

```bash
docker compose up --build -d
```

View logs with:

```bash
docker compose logs -f api
```

Stop the app with:

```bash
docker compose down
```

To also remove the PostgreSQL data volume, run:

```bash
docker compose down -v
```

## Run tests

Install development/test dependencies first if you have not already:

```bash
uv sync --dev
```

Run the test suite with:

```bash
uv run pytest
```

### Run database integration tests

The integration tests in `tests/integration` use a real PostgreSQL database to verify Alembic migrations, SQLAlchemy mappings, database constraints, foreign keys, and cascade behavior. The expected flow is to run PostgreSQL through Docker Compose and run pytest locally.

The tests are skipped unless `TEST_DATABASE_URL` is set. Use a dedicated test database only: the URL must contain `_test`. The test database must exist before pytest starts; the tests then run `alembic upgrade head` to create or update the application tables and truncate those tables between tests.

Start the Docker Compose database service:

```bash
docker compose up -d db
```

Create the dedicated test database inside the container:

```bash
docker compose exec -T db createdb -U postgres backend_eng_assignment_test
```

If the database already exists, `createdb` will print an error. That is safe to ignore, or you can recreate it with:

```bash
docker compose exec -T db dropdb -U postgres --if-exists backend_eng_assignment_test
docker compose exec -T db createdb -U postgres backend_eng_assignment_test
```

Set `TEST_DATABASE_URL` in your `.env` file:

```env
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/backend_eng_assignment_test
```

Run the integration tests with the helper script:

```bash
./scripts/run-integration-tests.sh
```

The helper script loads `.env`, starts the Docker Compose database service, keeps the local database user password aligned with `TEST_DATABASE_URL`, creates the dedicated test database if it is missing, and runs `uv run pytest tests/integration`. It refuses to run unless the parsed test database name ends with `_test` and does not match `POSTGRES_DB`. This avoids failures caused by an existing Docker volume that was initialized with an older password without dropping any database.

To pass additional pytest arguments, append them to the script command:

```bash
./scripts/run-integration-tests.sh -k cascade
```

To run everything, including DB integration tests, load `.env` and run the full suite:

```bash
set -a; . ./.env; set +a; uv run pytest
```

When you are done, stop the database service with:

```bash
docker compose down
```

To remove all local Postgres data, including the test database, remove the Docker volume too:

```bash
docker compose down -v
```

## Project structure

```text
.
├── app/                 # Application code, API routes, services, schemas, auth, middleware
├── config/              # Runtime settings
├── tests/               # Pytest test suite
├── main.py              # FastAPI app entry point
├── pyproject.toml       # Project metadata and dependencies
└── uv.lock              # Locked dependency versions
```
