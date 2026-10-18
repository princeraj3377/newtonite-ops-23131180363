# Zoho deployment

The frontend is on Slate and the API is on AppSail in the existing Catalyst
**Development** environment (India data center).

- Frontend: https://newtonite-ops-nshaafqv.onslate.in
- API: https://newtonite-backend-50046981711.development.catalystappsail.in
- Liveness: `/health`; database readiness: `/ready`; API reference: `/docs`.

## Backend package

`backend/` is the source of truth. `catalyst.json` deploys `deploy-backend/`,
which is a generated directory excluded from Git because its `app-config.json`
contains deployment credentials. Do not commit that file or copy a Windows
virtual environment into the Linux deployment.

The package must contain `app/`, `alembic/`, `alembic.ini`, `requirements.txt`,
`start.py`, and Linux Python 3.11 dependencies under `vendor/`.
After source changes, refresh these files from `backend/` before deploying.
Install dependencies from the repository root with:

```powershell
backend/.venv/Scripts/python.exe -m pip install --target deploy-backend/vendor --upgrade --platform manylinux_2_28_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 --python-version 3.11 --implementation cp --only-binary=:all: -r backend/requirements.txt
```

Use `python3 start.py` as the AppSail startup command. It imports bundled
dependencies and binds to `0.0.0.0` on `X_ZOHO_CATALYST_LISTEN_PORT` (9000 fallback).
The deployment config uses `build_path: "./"`, `stack: "python_3_11"`,
`port: {"http": 9000}` and these environment variables:

- `DATABASE_URL`: a PostgreSQL URL beginning `postgresql+psycopg://`, with TLS.
- `JWT_SECRET_KEY`: a private, random signing secret.
- `CORS_ALLOWED_ORIGINS`: empty on AppSail, where Catalyst handles CORS.
  For hosting outside Catalyst, this optional comma-separated setting enables
  the application's own CORS middleware.

Keep `catalyst_auth` false because this application implements its own JWT login.

Run `alembic upgrade head` from `backend/` with the **cloud** database URL supplied
as `DATABASE_URL` before deploying schema changes. Do not run database tests or
the demonstration seed against the cloud database. The test suite uses only
the separate `newtonite_ops_test` database.

```powershell
catalyst.cmd deploy --only appsail --non-interactive
```

`catalyst.cmd` works even when PowerShell blocks `catalyst.ps1`. CLI deployment
success means the package was uploaded; verify `/health` and `/ready` over HTTPS
and check login responses before considering the service operational.

## Frontend connection

Slate app `24098000000005004`, deployment `24098000000005006`, builds from the
connected repository `princeraj3377/newtonite-ops-23131180363`, which is different
from this checkout's Git remote. Set this build variable for each Slate rebuild:

```text
VITE_API_BASE_URL=https://newtonite-backend-50046981711.development.catalystappsail.in
```

Vite embeds it at build time; changing a running service's environment alone
does not update an existing browser bundle. The local `/api` Vite proxy does not
exist on Slate. Verify the published JavaScript bundle contains the API origin
after rebuilding.

In Catalyst Console, open **Cloud Scale > Authentication > Whitelisting >
Authorized Domains**, add `https://newtonite-ops-nshaafqv.onslate.in`, and enable
CORS. AppSail's gateway answers `OPTIONS` before the application, so application
CORS middleware alone cannot fix browser preflight requests. Keep application
CORS disabled on AppSail to avoid duplicate headers after domain authorization.
Check that preflight returns `Access-Control-Allow-Origin` for the frontend and
allows `authorization`, `content-type`, and `idempotency-key`.

Reference: [AppSail packaging](https://docs.catalyst.zoho.com/en/serverless/help/appsail/catalyst-managed-runtimes/key-concepts/)
and [Slate redeployment API](https://docs.catalyst.zoho.com/en/api/oauth2/generate-grant-token/#redeploy-application).
The platform CORS behavior is documented in
[Zoho's AppSail cross-origin guide](https://github.com/catalystbyzoho/agent-skills/blob/main/skills/catalyst-appsail/references/appsail-crossorigin.md).
