# Engineering Decisions

Updated: 18 October 2026

This document records the current Newtonite Ops implementation, its rationale, and its limits. Future improvements below are not implemented features. Setup instructions are in the [project README](README.md) and [frontend README](frontend/README.md).

## 1. Application structure

**Decision:** Use a React/Vite single-page frontend and a single FastAPI application, with routers for work items, teams, comments, and activity. PostgreSQL stores the domain data; SQLAlchemy manages database access and Alembic manages schema changes.

**Rationale:** A single backend keeps authorization, work-item mutations, and activity recording within one database transaction. Separate frontend components and backend routers provide boundaries without introducing service-to-service coordination.

**Trade-off:** Database sessions and routes are synchronous. The application does not currently have background workers, a distributed cache, or separate services. Revisit those choices when concrete workload requirements justify them.

Sources: [API entry point](backend/app/main.py), [database setup](backend/app/database.py), [models](backend/app/models.py), [frontend entry point](frontend/src/App.jsx).

## 2. Authentication and browser sessions

**Decision:** Login accepts JSON credentials and returns an HS256 JWT with a 30-minute lifetime. Passwords are hashed through `pwdlib`. The API validates the bearer token and loads the current user for authenticated requests.

The frontend verifies `/me` before saving the token in `sessionStorage`. If storage is unavailable, it keeps the token in memory. The shared Axios client attaches tokens and clears the session on an authenticated HTTP 401 for the current token. A response for an older token cannot clear a newer session. Network failures during restoration offer a retry.

**Rationale:** This matches the existing bearer-token API and supports same-tab refresh without storing passwords or introducing a persistent login across browser sessions.

**Trade-off:** JavaScript can access the token, so this storage does not protect it from an XSS vulnerability. Sign-out clears the browser session; it does not revoke an issued JWT. Refresh tokens, server-side revocation, registration, and password-reset flows are not implemented. Cookie-based authentication would require an explicit backend/session and CSRF design change.

Sources: [backend authentication](backend/app/auth.py), [frontend API client](frontend/src/lib/api.js).

## 3. Team authorization is enforced by the API

**Decision:** Memberships connect users to teams and roles. Every protected team operation checks membership and the required action. The frontend uses permissions returned by `/teams` to display controls, but those controls are not an authorization boundary.

Current endpoint behavior:

| Operation | Admin | Lead | Member | Viewer |
| --- | --- | --- | --- | --- |
| Read team items, comments, activity, and members | Yes | Yes | Yes | Yes |
| Create work items | Yes | Yes | Yes | No |
| Edit work items or change status | Yes | Yes | No | No |
| Assign or reassign to a team member | Yes | Yes | No | No |
| Claim an unassigned item | Yes | Yes | Yes | No |
| Post comments | Yes | Yes | Yes | Yes |

**Trade-off:** Comment posting currently requires `view`, so viewers can comment. `edit_own` exists in the member permission set, but edit/status endpoints require `edit`; claiming an item does not give a member edit permission. `manage_members` is declared for admins, but no membership-management endpoint is implemented. These distinctions must remain explicit in UI and API changes.

Sources: [permissions](backend/app/permissions.py), [team endpoints](backend/app/routers/teams.py), [comment endpoints](backend/app/routers/comments.py).

## 4. Optimistic locking prevents lost updates

**Decision:** Work items have an integer `version`. Edit, assign, claim, and status requests include `expected_version`. The update checks this version in SQL and increments it atomically. A failed match returns HTTP 409. The frontend reloads the latest item after a conflict and leaves the retry to the user.

**Rationale:** Two users can read the same item without holding database locks while they interact with the UI. The later write cannot silently overwrite a change based on an older version.

**Trade-off:** Users may need to review a change and retry. There is no automatic field merge or blind retry of conflicted writes.

**Claim-specific rule:** The same SQL update also checks `assignee_id IS NULL` and sets the assignee from the authenticated user, not from a client-supplied user ID. Even a request with the current version cannot claim an already assigned item. Admin/lead reassignment uses the separate assign endpoint and verifies that the target belongs to the same team. Assignment targets are not restricted by role beyond that membership check.

Source: [work-item mutations](backend/app/routers/items.py).

## 5. Creation retries use idempotency keys

**Decision:** `POST /items` requires an `Idempotency-Key`. A unique `(user_id, key)` record stores a SHA-256 hash of the normalized request and the successful response. A matching replay returns the recorded response; a different payload under the same key returns HTTP 409. A savepoint handles key-reservation conflicts without aborting the outer transaction.

The frontend reuses a key for an unchanged payload within the same open create form. The item, creation activity, and saved response commit together.

**Rationale:** A timeout can occur after a successful commit. Retrying the same request should not create a second work item.

**Trade-off:** Frontend keys are held in memory and are not retained after a reload or closing the form. Records have no expiry/cleanup policy. Comments do not have idempotency keys and are not automatically retried; an uncertain post asks the user to refresh comments before retrying.

Sources: [request hashing](backend/app/idempotency.py), [creation endpoint](backend/app/routers/items.py), [frontend submission helper](frontend/src/lib/workItems.js).

## 6. Status changes follow an explicit workflow

**Decision:** The backend accepts only these transitions:

| Current status | Allowed next status |
| --- | --- |
| `open` | `in_progress` |
| `in_progress` | `open`, `resolved` |
| `resolved` | `in_progress`, `closed` |
| `closed` | None |

Invalid transitions return HTTP 400. Status updates check the expected version and observed status atomically. The activity event records the status captured before SQLAlchemy synchronizes the updated object.

**Trade-off:** Closed items cannot be reopened through this workflow. The frontend mirrors allowed transitions for usable controls; the backend remains authoritative, so both definitions must be updated together.

Sources: [workflow rules](backend/app/workflow.py), [frontend workflow options](frontend/src/lib/workItems.js).

## 7. Activity is transactional history

**Decision:** Creation, edits, assignments, claims, status changes, and new comments record an activity event in the same transaction as the mutation. Comments include author names and timestamps; activity includes actor names, actions, details, and timestamps. Lists have deterministic chronological ordering.

**Rationale:** A successful mutation should have a corresponding history entry without relying on a second network request or a background job.

**Trade-off:** This is an activity log, not event sourcing: current state lives in work-item rows, and history is not sufficient to reconstruct every prior state. Names come from current user records rather than historical name snapshots. Comments created before comment-event recording was added are not backfilled. The API does not provide comment editing or deletion.

Sources: [comments](backend/app/routers/comments.py), [activity](backend/app/routers/acitivity.py), [discussion UI](frontend/src/components/ItemDiscussion.jsx).

## 8. Filtering and UI state

**Decision:** The API applies team scope, status, priority, type, and case-insensitive title/description search. Filters combine with AND; text matches either title or description. SQL wildcard characters in search text are escaped and treated literally. Items are returned newest first.

The frontend stores selected filters in URL search parameters, waits 250 ms after search typing, and cancels superseded reads. Local React state holds forms and drafts; no global state library is needed for the current screens. Successful mutations explicitly reload affected data and activity.

**Trade-off:** Item, comment, and activity lists are not paginated. Search is substring matching rather than indexed full-text search. There is no shared query cache, polling, or real-time subscription; updates from other users appear on refresh. Pagination and search indexes should be considered as data volume grows.

Sources: [item queries](backend/app/routers/items.py), [resource hook](frontend/src/hooks/useResource.js), [work-item UI](frontend/src/components/WorkItems.jsx).

## 9. Local development and deployment boundaries

**Decision:** Browser requests default to `/api`. Vite development/preview proxies strip that prefix and forward to `http://127.0.0.1:8000`, configurable through `API_PROXY_TARGET`. This avoids a cross-origin setup locally.

Docker Compose runs PostgreSQL and the API, waits for database health, and runs Alembic migrations before starting the API. The database uses a named volume and is not exposed through a host port in Compose. The API host port is bound to loopback. The frontend runs separately.

**Trade-off:** A production static host must supply the `/api` reverse proxy and an `index.html` fallback for frontend routes. Vite's proxy is not part of the generated frontend build. An alternate `VITE_API_BASE_URL` origin requires explicit backend CORS configuration. The current Compose configuration is for local development, not a complete production deployment. Secrets belong in backend configuration, never in browser-exposed `VITE_` variables.

Sources: [Vite configuration](frontend/vite.config.js), [Compose configuration](backend/compose.yaml), [migrations](backend/alembic/versions).

## 10. Verification and test isolation

**Decision:** Pytest exercises API behavior against a dedicated PostgreSQL test database. Fixtures require a database named `newtonite_ops_test`, inject the test session, and roll back an outer transaction after each database test. Savepoints allow endpoint commits/rollbacks without persisting test records.

Frontend Node tests cover authentication, query construction, and create-request retry keys. Lint and a production build catch additional source/build failures. Browser checks have also exercised role-specific controls, conflict recovery, draft retention, and responsive layouts using isolated API fixtures.

**Trade-off:** The browser checks used during implementation are not currently a committed automated end-to-end suite. Backend database tests require the dedicated database and schema to be provisioned; they must not be pointed at development data.

Run from `backend/` with its Python environment active:

```sh
python -m pytest -q
```

Run from `frontend/`:

```sh
npm run lint
npm test
npm run build
```

Use `npm.cmd` in Windows PowerShell if execution policy blocks `npm.ps1`.

Sources: [database test fixtures](backend/tests/conftest.py), [backend tests](backend/tests), [frontend tests](frontend/tests).
