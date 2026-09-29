# SwasthyaSetu — build status

Updated 2026-09-29. All operational records and actors are synthetic. No physical delivery, government integration or clinical validation is claimed. No paid service, automatic upgrade, cloud account resource, public deployment or submission has been enabled.

## Phase gates

| Phase | Implemented | Verified / evidence | Remaining gate |
|---|---|---|---|
| P0 | Repository, API contracts, Alembic migrations, separate state engines, eight-product generator, 180 history days and evaluator-only 28 days | Both local PostgreSQL databases migrated/seeded; compound scope and balance constraints tested | Apply migrations/permissions to owner's two Supabase Free projects |
| P1 | Signed expiring judge sessions, role simulation, scoped inventory, idempotency, version conflicts, capacity/staff/footfall, health endpoints | SQLite and PostgreSQL integrity/isolation tests; real browser report and refresh | Remote runtime-role/restart tests |
| P2 | OR-Tools golden plan, reservation, both district approvals, dispatch, partial/full receipt, cancellation, expiry and ledger | Golden conservation, competing reservations, duplicate/conflicting receipts, stale/expired/late cases; browser receipt completed | Hosted concurrency/latency profiling |
| P3 | Manual entry, CSV preview/confirm, sample PNG, browser PCM WAV recording, private-storage adapter, real Gemini structured extraction, quotas | Media signature/duration tests; explicit confirmation; missing provider remains visible failure | **Blocked:** owner Gemini key/model/free-tier quota and private Supabase buckets. No successful live provider call claimed. Hindi/Telugu audio unverified |
| P4 | Censored count model, local effects, calibration, baselines, 100-path forecasts, replenishment ETA sampling, single/multi-recipient solvers and independent verifiers | S02/S03/S08, atomic network reservation, donor protection and late-supply risk tests; 24 matched transport/expiry/surge replays | Real-world calibration and hosted profiling remain outside local evidence |
| P5 | Guided React/TS PWA, responsive UI, labels, partial language previews, bounded wake-up retry, offline drafts/conflicts | Desktop report→forecast→plan→approve→dispatch→receipt and reload; mobile language previews/offline conflict/microphone denial passed | Complete fluent-reviewed translations; production service-worker/cold-start checks |
| P6 | Strict parameter coordinator, private node effects, persisted bounded steps, local acceptance/rejection, separate-process harness | Actual exchange in `data/evaluation/federation.json`; raw-row/NaN/shape rejection tests | Docker launch unverified (Docker absent); secure aggregation/independent administration not claimed |
| P7 | Single-project Vercel configuration, plus Docker/Render Free/Firebase Spark alternatives, CSP/CORS, restricted-role SQL, deployment guide and smoke command | Production web build passed; Vercel JSON parsed; hosted-mode ASGI entrypoint imported against both local PostgreSQL databases; npm audit clean | **Blocked:** owner-authenticated Vercel and PostgreSQL projects, final URL, provider build, public incognito workflow and genuinely idle cold-start tests |
| P8 | Video script, 12-slide pitch outline, release instructions | Preparation documents written | **Blocked:** deployed release/live AI, team/public links, recording, final PDF and submission access |

Account-blocked gates are not complete. Later work is independent local implementation and preparation, not a claim that earlier live gates passed.

## Reproducible evidence

- `python -m pytest -q` — integrity tests; PostgreSQL mode sets `TEST_POSTGRES_URL`. Saved report: `data/evaluation/postgres-tests.xml`.
- `python -m scripts.train` — trusted JSON model artifact, validation-based model selection.
- `python -m scripts.evaluate` — measured synthetic forecasts and limited matched policy replay; results include regressions and limitations.
- `python -m scripts.federation_check` — two Python processes, distinct connection environments, real parameter exchange and local decisions.
- `python -m scripts.demo_check` — real HTTP approval/dispatch/receipt smoke test.
- `npm --prefix apps/web run build` — TypeScript/Vite production build.
- `cd apps/web; npx playwright test` — desktop/mobile checks; screenshots in `docs/screenshots`, report in `data/evaluation/browser-results.json`.

The initial pooled model failed validation against the baseline. The specified local effects produced `nb-v2-local-effects`: validation MAE 4.9665 versus weekday baseline 5.3716. This is synthetic evidence, not a clinical outcome. Both nodes currently reject the shared candidate after local-effect validation; rejection is preserved.

## Explicit limits

- Hosted persistence requires PostgreSQL/Supabase. SQLite is a labelled local fallback. Check preview mode in `/health/ready`.
- Ancillary entities use a scoped versioned JSON records table. Stock ledger and transfer invariants are relational.
- Guided golden allocation supports B/C → A; the network solver supports cross-district routes in the eight-facility state graph with unmet-demand, equity and transport/expiry objectives. One exact product per plan. Golden demand is fixed arithmetic; other scenarios compute forecasts.
- CSV supports catalogue base units for all eight products and packs only when explicit pack size exactly matches the catalogue. No inferred conversion.
- Media: verified PNG/JPEG/16-bit PCM WAV. Live language accuracy untested. Translations are partial previews.
- Guest global model publication/deletion endpoints do not exist. Owner maintenance uses authenticated provider/database access.
- Evidence has a conservative 45 MiB lifetime budget per state. Expired cloud objects require owner cleanup/reconciliation.
- Docker image execution, public cold starts and hosted CPU/memory measurements remain unverified.

## Local completion verification

### Plain-language demonstration update

The default screen now offers a guided shortage-to-delivery story with named fictional staff and health centres. Each action explains the responsible person's job and submits the appropriate scoped role to the real API. The walkthrough covers stock counting, safe allocation, both district approvals, dispatch and partial/full receipt, with saved activity and live demo balances. The detailed workspace remains accessible. New sessions include varied fictional facility staffing, footfall, beds and medicine stocks. The golden MED-001 opening counts remain 40/120/150.

Verified on 2026-09-29: **5 browser tests passed**, including the new full guided flow, persisted completion, mobile layout, role explanations and a changed starting count producing a different recommendation. **18 PostgreSQL backend tests passed** with a fresh writable temporary directory; the initial rerun failed on old temporary-file permissions before those tests executed. Production web build passed. Screenshots: `docs/screenshots/guided-*.png`. The story uses declared example demand; no AI response, live journey, or external integration is simulated as successful. Account-dependent gates above remain blocked.

Vercel preparation verified locally on 2026-09-29: production now defaults to same-origin API requests, `vercel.json` is valid JSON, the React production build passes, and `api/index.py` imports the real application with `APP_ENV=demo` against the two local PostgreSQL databases. The Vercel CLI was not installed and no Vercel account/project or remote build was available, so deployment success is not claimed.

PostgreSQL suite: **18 passed**, including cross-session/state isolation, concurrent reservation, duplicate receipts, atomic network reservation, media ownership, imports and replenishments. Browser suite: **5 passed** (guided full/partial receipt and reload; guided mobile/change-sensitive recommendation; advanced golden workflow; mobile/offline/language previews/microphone denial; replenishment confirmation/model-round reload). Production web build passed. The real local HTTP smoke test passed. The transport sensitivity run contains 24 actual matched policy replays. Reports and screenshots are saved in the repository.

Local preview: `http://localhost:5173`, API `http://localhost:8000`, two PostgreSQL databases on loopback port 55432. Restart commands are in README and `scripts/local.ps1`. This is a runnable local release, not a claim that P3/P7/P8 live gates have passed. Language previews still require full translation and fluent review before a multilingual submission claim.

Local resource bounds: 40 live sandboxes per state, approximately 1 MB conservatively accounted mutation responses per sandbox, 500 commands, 30 forecasts, 40 plans, 3 model rounds, 8 uploads and 6 AI attempts per session. Hosted session creation is 10 per IP/hour (local test mode 100), plus 200 per state/day. External free-tier quotas still require owner verification.

## Required owner configuration

Follow `docs/DEPLOYMENT.md`: two Supabase Free projects/private buckets; verified free-tier Gemini model/key/quota; one Render Free service; Firebase static Hosting on Spark. Keep credentials server-side. Only the public API origin goes in frontend configuration. Do not send secrets in chat or commit them.
