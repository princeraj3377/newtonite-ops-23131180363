# Newtonite Ops frontend

React login UI connected to the existing FastAPI backend.

## Local setup

1. Start the backend from `backend/`: `docker compose up -d --build` (requires `JWT_SECRET_KEY` in `backend/.env`).
2. From `frontend/`, run `npm install` and `npm run dev`.
3. Open the URL printed by Vite and sign in with an existing database user.

On Windows PowerShell, use `npm.cmd` if script execution policy blocks `npm`.

No frontend environment file is needed for the default backend at `http://127.0.0.1:8000`. For a different address, copy `.env.example` to `.env.local`, update `API_PROXY_TARGET`, and restart Vite. Never put secrets in `VITE_` variables.

For a local demo account, run `docker compose exec api python seed.py` from `backend/`. The existing seed creates `demo@example.com` with password `Demo@12345` when that account does not exist. Use this only with a development database; it does not reset an existing user's password.

## Authentication

- `/login` posts JSON `{ email, password }` to the backend `/login` endpoint.
- The returned bearer token is used for `/me`; the session is saved only after that succeeds.
- `/dashboard` shows the team's work items. Anonymous visitors are redirected to `/login`.
- The token is kept in `sessionStorage`, survives refresh in the same tab, and is cleared on sign-out or an authenticated HTTP 401. Passwords are never stored. If storage is unavailable, the session lasts in memory until reload.
- API requests from `src/lib/api.js` attach the bearer token automatically. The backend currently expires tokens after 30 minutes and has no refresh or revoke endpoint; sign-out clears the browser session.
- Network failures during session restoration offer a retry without discarding the token.

## Work items

- Team choices come from authenticated `GET /teams`, with permissions derived from the user's membership.
- Search by title/description, status, priority and type are combined by `GET /items`. Selections are kept in the dashboard URL; search waits 250 ms after typing.
- Members with create permission can submit a title, description, type and priority. Retries of an unchanged form reuse the same idempotency key.
- Click an item title to view its description and metadata. Admins and leads can use the allowed status transitions; writes include the current version and conflicts reload the latest item.
- Loading, empty results, missing teams and request failures have explicit states. Refresh and Clear filters are available in the list toolbar.
- The list currently displays all matching items, newest first, without pagination.
- Item details include Comments and Activity tabs. Comments show authors and timestamps, preserve drafts across tab changes, and accept up to 2,000 characters. Posting a comment refreshes both feeds; status changes refresh activity. The backend's existing `view` permission permits commenting, including viewer memberships.
- Activity shows authors, timestamps and recorded changes in chronological order. Comments now create activity events; comments saved before this change are not backfilled.
- Open an item to use Assignment: admins/leads can choose a team member and assign or reassign it. Admins, leads and members can claim an unassigned item for themselves. Viewers cannot assign or claim. Claiming checks the version and unassigned state atomically, so another person's assignment cannot be overwritten. Assignment changes refresh the item and activity while preserving comment drafts.

Restart the backend after pulling these changes, or rebuild its Docker image with `docker compose up -d --build`, so the new teams endpoint and filters are available.

## Validation

```sh
npm run lint
npm test
npm run build
```

## Deployment

Build with `npm run build`. Configure your host to serve `index.html` for frontend routes such as `/login` and `/dashboard`, and reverse-proxy `/api/*` to the backend with the `/api` prefix removed. Vite's proxy is for local development/preview only. Alternatively, set `VITE_API_BASE_URL` to an API origin at build time and explicitly allow the frontend origin in the backend's CORS configuration. The current backend has no cross-origin CORS configuration, so the same-origin proxy is the default.
