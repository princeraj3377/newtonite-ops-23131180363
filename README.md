
# Newtonite Ops

A team-based operations management REST API built with FastAPI, PostgreSQL, SQLAlchemy, and Docker.

## Features

- JWT authentication
- Team-based role permissions
- Work item creation, updates, and assignment
- Status workflow validation
- Optimistic locking using version numbers
- Activity history and comments
- Idempotency protection for work item creation
- Database migrations with Alembic
- Automated tests with pytest

## Tech Stack

Architecture decisions, permission behavior, trade-offs, and current limitations are documented in [ENGINEERING_DECISIONS.md](ENGINEERING_DECISIONS.md). See the [frontend README](frontend/README.md) for UI setup and API connection details.

- Python 3.11
- FastAPI
- PostgreSQL 17
- SQLAlchemy
- Alembic
- Docker Compose
- Pytest

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/princeraj3377/newtonite-ops.git
cd newtonite-ops/backend
```

### 2. Configure environment variables

Create `backend/.env` with a strong JWT secret:

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
```

### 3. Start the application

```bash
docker compose up -d --build
```

### 4. Open API documentation

http://127.0.0.1:8000/docs

### 5. Run tests

For local Python setup with dependencies installed:

```bash
python -m pytest -v
```

Database-dependent tests require a separate test database and appropriate test configuration.

## Security

Environment files and local secrets are excluded from Git using `.gitignore`.
