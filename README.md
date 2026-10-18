# Newtonite Ops

**Operations Under Pressure — Full-Stack Software Engineering Challenge**

Newtonite Ops is a team-based operations management application for creating, assigning, tracking, and resolving operational work items. It brings ownership, workflow state, comments, and change history into one place so teams can coordinate work without relying on scattered messages and spreadsheets.

**[Open the Live Application](https://newtonite-ops-60091829404.development.catalystserverless.in/app/index.html)** · **[Backend API / Swagger Docs](https://newtonite-backend-50046981711.development.catalystappsail.in/docs)** · **[Source Code](https://github.com/princeraj3377/newtonite-ops)**

> **Reviewer quick start:** Open the live application, sign in with one of the demo accounts below, and explore the dashboard and work-item workflow. The hosted environment uses its own Neon PostgreSQL database; it does **not** automatically contain work items created in a developer's local Docker database. A fresh or empty work-item list is therefore possible and does not mean the application failed to load.

## Live demo and test accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | `demo@example.com` | `Demo@12345` |
| Lead | `lead@example.com` | `Lead@12345` |
| Member | `member@example.com` | `Member@12345` |
| Viewer | `viewer@example.com` | `Viewer@12345` |

These are **seeded demonstration accounts**, not personal or production credentials. The seed script creates an `Engineering` team and assigns the corresponding demo roles. Four demo accounts are provided; this is not a limit on the number of users the application can support.

### How to try the hosted application

1. Open the **Live Application** link above.
2. Log in with an account from the table (start with **Admin**).
3. Explore the dashboard and available work items; create a work item if the list is empty and your role permits it.
4. Open an item to inspect its details, ownership, status, comments, and activity history.
5. Sign out and log in as **Lead**, **Member**, or **Viewer** to compare the available actions. Authorization is enforced by the backend, not merely by hiding UI controls.

> The live demo runs on the **Zoho Catalyst Development Environment**. Availability and data may change as the project is updated. Please do not use the demo for sensitive or real business information.

## What the application does

- **JWT authentication:** users log in and access authenticated API endpoints.
- **Team-based roles:** Admin, Lead, Member, and Viewer demonstration accounts illustrate different responsibilities.
- **Work-item management:** create, view, update, and assign operational work items.
- **Workflow validation:** the server checks permitted status transitions.
- **Optimistic concurrency control:** version numbers help prevent stale edits from silently overwriting newer changes.
- **Idempotent creation:** protection against duplicate work-item creation from retried requests.
- **Collaboration and traceability:** comments and activity history help explain what happened to an item.
- **Database migrations:** Alembic manages schema changes.
- **Automated backend tests:** pytest covers important application behaviour; see the test instructions below.

## Technology stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| Frontend | React, Vite, JavaScript | Interactive browser application |
| HTTP client | Axios | Communication with the REST API |
| Backend | Python 3.11, FastAPI | API endpoints and business rules |
| ORM | SQLAlchemy | Database access and models |
| Database | PostgreSQL | Persistent users, teams, work items, and history |
| Migrations | Alembic | Database schema evolution |
| Authentication | JWT | Authenticated API access |
| Local environment | Docker Compose | Local application/database setup |
| Testing | pytest | Automated backend tests |
| Frontend hosting | Zoho Catalyst Client | Serves the built React application |
| Backend hosting | Zoho Catalyst AppSail | Runs the FastAPI service |
| Hosted database | Neon PostgreSQL | Database used by the deployed backend |

## High-level architecture

```text
Browser
   |
   v
React + Vite frontend (Zoho Catalyst Client)
   |
   | HTTPS / REST (Axios)
   v
FastAPI backend (Zoho Catalyst AppSail)
   |
   | SQLAlchemy
   v
PostgreSQL (Neon for hosted deployment)
```

The backend is responsible for authentication, permissions, workflow validation, and database writes. The frontend is responsible for presenting work items and sending user actions to the API.

## Repository guide

- `frontend/` — React/Vite application; see [`frontend/README.md`](frontend/README.md) for frontend-specific instructions.
- `backend/` — FastAPI application, database models, migrations, seed script, and tests.
- [`ENGINEERING_DECISIONS.md`](ENGINEERING_DECISIONS.md) — design choices, trade-offs, and limitations.
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — deployment notes (where present in the repository).

## Run locally

### Prerequisites

- Git
- Docker Desktop with Docker Compose
- Node.js and npm for running the frontend locally
- Python 3.11 for a non-containerized backend or local pytest execution

### 1. Clone the repository

```bash
git clone https://github.com/princeraj3377/newtonite-ops.git
cd newtonite-ops
```

### 2. Configure the backend

Create `backend/.env` with the environment variables expected by your local Docker configuration. The existing setup uses a JWT secret; supply a **new local secret**, never a deployed credential.

```env
JWT_SECRET_KEY=replace-with-a-long-random-local-secret
```

Database connection settings depend on the Docker Compose configuration. Review the Compose file and backend environment template/configuration before starting; do not copy production or Neon credentials into Git.

### 3. Start the backend and database

From the **`backend/`** directory:

```bash
cd backend
docker compose up -d --build
```

Once running, open **http://127.0.0.1:8000/docs** to explore the API. If the local database has not been initialized, apply the repository's Alembic migrations and seed procedure before testing login. The backend contains a `seed.py` script for demo accounts; run it in the backend environment after configuring the database.

### 4. Start the frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open the local address printed by Vite. The frontend uses `VITE_API_BASE_URL` when provided, and otherwise uses `/api`. Configure the frontend's API target or local proxy as described in [`frontend/README.md`](frontend/README.md) so requests reach your running FastAPI backend.

> **Setup note:** The commands above describe the known project layout. Exact local database environment values, migration commands, and frontend proxy configuration should be verified against the checked-in configuration before a fresh-machine evaluation.

## Run tests

From the `backend/` directory, with Python dependencies and the test database configured:

```bash
python -m pytest -v
```

Database-dependent tests require a **separate test database** and appropriate test configuration. Tests should not run against the hosted Neon demo database.

## Reliability and engineering considerations

The project focuses on correctness beyond basic CRUD, including server-side authorization, workflow rules, version-aware updates, and idempotent work-item creation. For the rationale, alternatives considered, and trade-offs, read [`ENGINEERING_DECISIONS.md`](ENGINEERING_DECISIONS.md). Automated tests should be used to validate the behaviours claimed in that document.

## Deployment overview

- **Frontend:** Vite production build served through Zoho Catalyst Client.
- **Backend:** FastAPI deployed through Zoho Catalyst AppSail.
- **Database:** hosted Neon PostgreSQL, separate from local Docker PostgreSQL.
- **Configuration:** production API URL is set at frontend build time using `VITE_API_BASE_URL`; backend database credentials and JWT signing secret must be kept out of version control.

The hosted application and local development environment do not share work-item records unless data is explicitly migrated.

## Known limitations and scope

- The hosted demo may begin with **no work items**; local Docker data is not automatically copied to Neon.
- The application is a challenge implementation, not a production-hardened enterprise platform.
- Demo accounts have published passwords and should be used only for evaluation; do not store sensitive information.
- The current deployment uses Catalyst's **development** environment rather than a separately configured production domain.
- Background processing, notification delivery, real-time updates, and other optional enterprise capabilities should not be assumed unless verified in the implementation.
- A clean-machine setup and full test run should be checked before final submission.

## Security

- Keep `.env` files, database passwords, JWT secrets, and deployment tokens **out of Git**.
- Use separate credentials for local development, tests, and hosted deployment.
- Rotate any secret that has been exposed in chat, logs, or committed files.
- Do not use the public demo accounts for real organizational data.

## Additional documentation

- [Engineering decisions](ENGINEERING_DECISIONS.md)
- [Frontend setup](frontend/README.md)
- [Deployment notes](DEPLOYMENT.md)
- [Interactive API documentation](https://newtonite-backend-50046981711.development.catalystappsail.in/docs)

---

**Newtonite Software Engineering Challenge — Operations Under Pressure**  
A full-stack demonstration of team-based operational work management, with emphasis on backend correctness, collaboration, and engineering trade-offs.
