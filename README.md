# SwasthyaSetu

A working synthetic health-supply prototype: stock reports, demand forecasts, donor-protecting allocation, two district approvals, dispatch, partial receipt and an auditable ledger.

**All operational data and actors are fictional. No physical deliveries or clinical decisions. No cloud services have been provisioned.** See [BUILD_STATUS.md](BUILD_STATUS.md) for verified gates and blockers.

## Local setup

Prerequisites: Python 3.12, Node.js 22+, Git. PostgreSQL 16+ or Docker is preferred. Local SQLite is a development fallback only and is rejected in hosted mode. Tested here with Python 3.12, Node and Edge on Windows, plus repository-local PostgreSQL 18.4. Dependencies are pinned in `requirements.lock.txt` and npm lockfiles.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.lock.txt
.venv/Scripts/python -m scripts.migrate
.venv/Scripts/python -m data.generate
.venv/Scripts/python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000
# In a second terminal:
npm --prefix apps/web ci
npm --prefix apps/web run dev
```

Open `http://localhost:5173`. The SQLite fallback requires no credentials. The local signing secret is generated in ignored `.local-secret`; retain it to resume sessions across restarts. Environment variables are read from the process, not automatically from `.env`; export them privately before starting. Never commit secrets.

### PostgreSQL without Docker (optional local tooling)

```powershell
npm --prefix infra/local-postgres ci
npm --prefix infra/local-postgres start
# In another terminal, before migration/seeding/API:
$env:STATE_A_DATABASE_URL='postgresql+psycopg://demo:local-development-only@127.0.0.1:55432/state_a'
$env:STATE_B_DATABASE_URL='postgresql+psycopg://demo:local-development-only@127.0.0.1:55432/state_b'
.venv/Scripts/python -m scripts.migrate
.venv/Scripts/python -m data.generate
```

The portable server binds loopback, stores files under `tmp/postgres`, creates no OS account/service and costs nothing. Its password is for local testing only. `make dev` starts the Docker Compose alternative with two database containers, API and frontend. Docker execution remains to be verified on a Docker-equipped machine.

## Reproduce checks

```powershell
.venv/Scripts/python -m pytest -q --basetemp=tmp/pytest-run -p no:cacheprovider
# PostgreSQL fixture isolates each test in random schemas:
$env:TEST_POSTGRES_URL='postgresql+psycopg://demo:local-development-only@127.0.0.1:55432/test_a'
.venv/Scripts/python -m pytest -q --basetemp=tmp/pytest-pg -p no:cacheprovider
.venv/Scripts/python -m scripts.train
.venv/Scripts/python -m scripts.evaluate
.venv/Scripts/python -m scripts.transport_evaluation
.venv/Scripts/python -m scripts.federation_check
.venv/Scripts/python -m scripts.demo_check
.venv/Scripts/python -m scripts.export_contracts
npm --prefix apps/web run build
# With local API/web running, from apps/web:
npx playwright test
```

Browser tests use installed Microsoft Edge by default; change the Playwright channel for another supported installed browser. They create real local sessions and mutate only synthetic data. Session creation is rate limited; repeated full runs can legitimately hit the hourly limit. Do not disable hosted limits to make a test pass.

Windows helpers: `./scripts/local.ps1 api`, `./scripts/local.ps1 web`, `./scripts/local.ps1 test`, `./scripts/local.ps1 evaluate`, `./scripts/local.ps1 build`. Start the optional portable PostgreSQL server first for the API helper. Docker federation check: after Compose migration/seed, run `docker compose -f infra/compose.yaml --profile federation run --rm federation-check`; this launches actual separate node processes, not canned messages.

Make targets provide the specification's command contract: `dev`, `migrate`, `seed`, `test`, `evaluate`, `build`, `demo-check`. On Windows the commands above are equivalent; `make build` additionally builds the backend Docker image.

## Walkthrough

Start **GOLDEN**. Custodian D1 reports A's stock. Planner computes a plan (the deterministic golden demand is clearly separate from the forecast). Reserve C → A. Approver D1 signs, then approver D2 signs. Custodian D2 dispatches. Receiver D1 receives 20 and then 40. Inspect stock and audit. Switch to other scenarios to run numerical analysis and failure cases.

Manual entry and CSV do not need Gemini. Photo/WAV extraction needs the server configuration in [deployment instructions](docs/DEPLOYMENT.md); without it the app returns `AI_NOT_CONFIGURED`. No successful Google integration is claimed yet. Hindi/Telugu UI previews are partial and unreviewed.

## Repository

`apps/web` PWA · `services/api` contracts/ledger/API · `ai` provider/private evidence · `forecasting` training/inference/JSON artifact · `allocation` solver/verifier · `federation` nodes/coordinator · `data` synthetic generator and measured evidence · `migrations` schema · `tests` correctness · `infra` free deployment/local runtime · `docs` architecture, deployment, screenshots and submission preparation.

See [architecture](docs/ARCHITECTURE.md), [deployment](docs/DEPLOYMENT.md), [demo script](docs/DEMO_SCRIPT.md), [pitch outline](docs/PITCH_OUTLINE.md). Source plan text is retained in `docs/specification.txt` for traceability.
