# Backend Engineering Assignment

## Project description

A FastAPI backend service for managing workspace-scoped users, resources, resource policies, and access checks. The app uses JWT authentication, PostgreSQL persistence, Alembic migrations, and versioned API routes under `/api/v1`.

## Technology stack

- Python 3.12+
- FastAPI
- Uvicorn
- PostgreSQL
- SQLAlchemy async ORM
- Alembic
- Pydantic / pydantic-settings
- PyJWT
- pytest
- uv
- Docker / Docker Compose

## Prerequisites

- Docker
- Docker Compose
- Python 3.12 or newer, if running tests locally
- [`uv`](https://docs.astral.sh/uv/), if running tests locally

## Setup instructions

### Environment variables

Create a `.env` file in the project root:

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

### Database creation, dependency installation, and migrations

Use Docker Compose for local setup:

```bash
docker compose up --build
```

Docker Compose will:

- build the API image
- start PostgreSQL
- create the configured database on first startup
- install dependencies inside the API container
- run Alembic migrations
- start the FastAPI application

### Creating initial data

Create the first workspace and admin user through the API:

```bash
curl -X POST http://localhost:8000/api/v1/workspaces/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Workspace",
    "admin_email": "admin@example.com",
    "admin_password": "StrongPass123!"
  }'
```

Use the returned `workspace.id` when logging in.

## How to run the application

Start the app and database:

```bash
docker compose up --build
```

Run in the background:

```bash
docker compose up --build -d
```

View logs:

```bash
docker compose logs -f api
```

Stop the app:

```bash
docker compose down
```

Remove local PostgreSQL data as well:

```bash
docker compose down -v
```

The app runs at:

```text
http://localhost:8000
```

## How to run tests

Install development/test dependencies:

```bash
uv sync --dev
```

Run the test suite:

```bash
uv run pytest
```

### Database integration tests

Set `TEST_DATABASE_URL` in `.env`:

```env
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/backend_eng_assignment_test
```

Run integration tests with the helper script:

```bash
./scripts/run-integration-tests.sh
```

The script starts PostgreSQL through Docker Compose, creates the dedicated test database if needed, and runs the integration test suite.

## API documentation

After starting the app, open:

```text
http://localhost:8000/docs
```

The OpenAPI schema is available at:

```text
http://localhost:8000/openapi.json
```

Useful endpoints:

- `GET /` — application status
- `GET /health` — health check
- `GET /docs` — interactive API documentation
- `GET /openapi.json` — OpenAPI schema

## Example API calls

Replace placeholder IDs and tokens with values returned by the API.

### Health check

```bash
curl http://localhost:8000/health
```

### Create a workspace

```bash
curl -X POST http://localhost:8000/api/v1/workspaces/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Workspace",
    "admin_email": "admin@example.com",
    "admin_password": "StrongPass123!"
  }'
```

### Log in

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "<workspace_id>",
    "email": "admin@example.com",
    "password": "StrongPass123!"
  }'
```

### Create a resource

```bash
curl -X POST http://localhost:8000/api/v1/workspaces/<workspace_id>/resources/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer API",
    "type": "api",
    "description": "Customer-facing API resource",
    "status": "active"
  }'
```

### Check access

```bash
curl -X POST http://localhost:8000/api/v1/access-check/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "<workspace_id>",
    "user_id": "<user_id>",
    "resource_id": "<resource_id>"
  }'
```

## Project structure

```text
.
├── app/                 # Application code, API routes, services, schemas, auth, middleware
├── config/              # Runtime settings
├── scripts/             # Helper scripts
├── tests/               # Pytest test suite
├── main.py              # FastAPI app entry point
├── pyproject.toml       # Project metadata and dependencies
└── uv.lock              # Locked dependency versions
```

## Assumptions made
- It was assumed that the Multi-tenant architecture should be able to support large number of workspaces not just a handful.
- The Assignment Requirements document refers to 'Resources' on which policies were to be applied. This was assumed to be a dedicated 'Resources' table in the DB.
- The folder structure mentioned in the Assignment Requirements document was assumed to be based on Django. Therefore, I took the liberty to adjust it according to Layered architecture patterns. The tests folder structure is also adjusted accordingly to better reflect the app folder structure.
- Much of the test coverage requirements (above 80%) was achieved through property based tests using 'hypothesis' and 'schemathesis'. This was assumed to be sufficient to meet the test coverage requirement.
- Logging out invalidates all auth tokens. Therefore, if user is logged in on multiple devices they must login on all required devices again. This was assumed to be satisfactory for the scope of this assignment.
- It is assumed that the responses in the API contract mentioned in the Assignment requirement document is referring to the data field and not the entire response including success status, message etc.
