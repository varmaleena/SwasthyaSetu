# Owner configuration and deployment gates

No cloud resource has been provisioned and no paid service enabled. Local development credentials are intentionally confined to loopback PostgreSQL and must not be reused remotely.

## Recommended demo route: one Vercel project

The repository now includes `vercel.json` and `api/index.py`. Vercel builds the React app, serves it at `/`, and runs the existing FastAPI application for `/api/*` and `/health/*` on the same domain. The production browser bundle therefore uses same-origin API calls and does not need `VITE_API_BASE_URL`.

This route still requires the two migrated PostgreSQL databases below. Vercel's function filesystem must not be used for SQLite or uploaded evidence because it is temporary. Keep `GEMINI_FREE_TIER_VERIFIED=false` and `AI_GLOBAL_DAILY_LIMIT=0` until a real free-tier Gemini account check succeeds.

After creating and seeding the two databases, import this repository into a personal Vercel Hobby project with the repository root as the Root Directory. Do not select `apps/web` as the root. Keep the detected commands from `vercel.json` and add these server-side Production environment variables:

- `APP_ENV=demo`
- `STATE_A_DATABASE_URL` and `STATE_B_DATABASE_URL`: distinct pooled PostgreSQL URLs with SSL
- `DEMO_TOKEN_SECRET`: a new random value of at least 32 characters
- `ALLOWED_ORIGINS`: the final `https://<project>.vercel.app` origin
- `BUILD_SHA`: the deployed Git commit
- `GEMINI_FREE_TIER_VERIFIED=false`
- `AI_GLOBAL_DAILY_LIMIT=0`

Do not add either database URL or any key with a `VITE_` prefix. Deploy only after migrations and synthetic seeding have completed. Verify `https://<project>.vercel.app/health/ready` first; it must report both states `true`, PostgreSQL persistence and `source: synthetic`. Then run the complete guided story in a private browser window and confirm that refresh preserves the completed receipt.

Vercel Hobby is suitable for a personal, non-commercial judge demo within its current usage limits. A real deployment, cold start, function bundle size, database connection behavior and public workflow are not verified by the local checks.

## 1. Two Supabase Free projects

Create State A and State B under the legitimate account project allowance. Confirm both are Free and that no paid plan or automatic upgrade is enabled. Use distinct PostgreSQL connection strings (provider-supported pooled configuration, SSL required). Set `STATE_A_DATABASE_URL` and `STATE_B_DATABASE_URL` privately. Apply `python -m scripts.migrate`, then `python -m data.generate` from the developer environment as migration owner. Apply `infra/app-role.sql` separately in each project and set the role password privately. Change runtime URLs to that restricted role. Migration access stays separate from runtime access.

Create a **private** Storage bucket named `evidence` in each project, maximum object size 2 MB, allowed PNG/JPEG/WAV MIME types. Do not add public download policies. Set `STATE_A_STORAGE_URL`, `STATE_B_STORAGE_URL` to each project origin and the matching server-only storage keys. Never place these keys in `VITE_*` variables. The two storage credentials are not interchangeable.

## 2. Gemini Developer API

In Google AI Studio, choose a currently eligible **free-tier** model supporting image, audio and structured output. Verify actual account quota and billing configuration before making calls. This repository deliberately does not guess a model or free-tier entitlement.

Set server-only `GEMINI_API_KEY`, `GEMINI_MODEL_ID`, `GEMINI_FREE_TIER_VERIFIED=true` and `AI_GLOBAL_DAILY_LIMIT` no higher than the verified account allowance (application caps at 100; start lower). The default limit is zero and verification defaults false. No billing is enabled by code.

Run a real text/image/audio account smoke check; then use the app's sample stock card and actual Hindi/Telugu WAV clips. Record model ID, date, observed latency, returned metadata, exact-match errors and successful human confirmation. Live AI, Hindi/Telugu accuracy and quota behavior are **unverified until this is done**. A structured JSON response alone does not prove transcription accuracy. Do not put keys in chat, Git or screenshots.

## 3. Render Free API (alternative split-host route)

Connect the public repository and use `render.yaml` with `plan: free`, one worker and automatic deploy disabled. Review the dashboard plan before creating the service. Do not attach paid databases, workers, cron, persistent disks or add-ons. Set all server variables from `.env.example`, including a random 32+ character `DEMO_TOKEN_SECRET`, `APP_ENV=demo`, the final Firebase HTTPS origin in `ALLOWED_ORIGINS`, and `BUILD_SHA`.

Migrate/seed before deployment. `/health/live` proves process liveness; `/health/ready` checks both schema versions and database connectivity without making AI calls. Render's writable filesystem is not persistence. Confirm sessions survive a restart using PostgreSQL and private storage. Profile actual free-instance memory and runtime; local timings are not hosting evidence.

## 4. Firebase Hosting Spark

Create a Firebase project on **Spark**. Use static Hosting only, not App Hosting. Set frontend `VITE_API_BASE_URL` to the exact Render HTTPS origin. Replace `REPLACE-WITH-API.onrender.com` in `firebase.json` CSP with that origin. Run `npm ci` and `npm run build` in `apps/web`; authenticate the Firebase CLI as owner, select the project and run `firebase deploy --only hosting`. No credentials belong in the frontend build. Add final repository/video URLs only when the public links exist.

## 5. Release verification

Run `DEMO_API_URL=<actual API URL> python -m scripts.demo_check` (PowerShell uses `$env:DEMO_API_URL`). Then use an incognito browser on the final Hosting URL: report → forecast → plan → both approvals → dispatch → partial/full receipt. Verify CORS, deep links, narrow layout, refresh, restart, media upload and real Gemini confirmation. Leave the service genuinely idle and verify wake-up and bounded retry. Do not simulate cold-start success. Restore paused projects manually under provider rules.

Keep a private owner backup export and release commit. Public source, video, pitch PDF and app must open signed out. Record all URLs, release SHA, model ID and verification date in the release checklist. P7/P8 cannot be marked complete from localhost.

## Current provider references

Checked during implementation: [Render free service constraints](https://render.com/docs/free), [Supabase pricing](https://supabase.com/pricing), [Firebase Hosting setup](https://firebase.google.com/docs/hosting/quickstart), [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output). Before deployment recheck [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) and actual account quotas; documented offers do not establish this account's eligibility.
