# Deployment environment template

Use this file as a manual checklist. Replace every `<...>` value in your hosting dashboards; never commit completed values or paste secrets into chat.

## Why the current Render build failed

Render cloned Git commit `d166245`, which does **not** include the local `render.yaml` or the deployment changes created in this workspace. It therefore searched for `./Dockerfile` and failed. Until these changes are pushed, configure the Render service manually as follows:

```text
Runtime: Docker
Repository root directory: leave blank (repository root)
Dockerfile path: apps/api/Dockerfile
Health check path: /health
Plan: Free
```

Do not set a Render root directory of `apps/api`: the Dockerfile intentionally builds with the repository root as its Docker build context.

## Render dashboard environment variables

Paste these names into Render. Values marked `<...>` must be replaced. Render supplies `PORT` automatically; do **not** add it yourself.

```dotenv
# Required runtime mode
FLOWPILOT_ENV=production
RUN_EMBEDDED_WORKERS=true
DEMO_MODE=false

# Required Supabase database connection. Use the Session Pooler connection string.
DATABASE_URL=postgresql+asyncpg://postgres.<project-ref>:<password>@aws-<region>.pooler.supabase.com:5432/postgres
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Required Supabase authentication and encryption.
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_JWKS_URL=
SUPABASE_JWT_AUDIENCE=authenticated
ENCRYPTION_KEY=<paste-a-new-production-encryption-key>
ENCRYPTION_PREVIOUS_KEYS=

# Replace <workers-dev-subdomain> after setting up Workers.dev in Cloudflare.
CORS_ORIGINS=https://flowpilot-web.<workers-dev-subdomain>.workers.dev

# Request limits and observability
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_MANUAL_EVENTS=30
RATE_LIMIT_WEBHOOKS=60
RATE_LIMIT_AI_REQUESTS=10
REQUEST_BODY_LIMIT_BYTES=1048576
EVENT_ATTACHMENT_MAX_BYTES=5242880
WEBHOOK_TIMESTAMP_WINDOW_SECONDS=300
METRICS_ENABLED=false
```

## Render optional integration variables

Add only the integrations you enable. Replace the two URL placeholders with the final Render and Cloudflare URLs.

```dotenv
# OAuth connection callbacks
GOOGLE_CLIENT_ID=<google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<google-oauth-client-secret>
GOOGLE_REDIRECT_URI=https://<render-service>.onrender.com/api/v1/connections/google/callback
GITHUB_CLIENT_ID=<github-oauth-client-id>
GITHUB_CLIENT_SECRET=<github-oauth-client-secret>
GITHUB_REDIRECT_URI=https://<render-service>.onrender.com/api/v1/connections/github/callback
CONNECTION_SUCCESS_URL=https://flowpilot-web.<workers-dev-subdomain>.workers.dev/dashboard/connections

# Optional integrations
TELEGRAM_BOT_TOKEN=<telegram-bot-token>
TELEGRAM_MOCK_MODE=false
MOCK_BANK_WEBHOOK_SECRET=<long-random-webhook-secret>
CLIENT_AVAILABILITY_START_HOUR=10
CLIENT_AVAILABILITY_END_HOUR=16

# Optional OpenRouter-compatible AI provider
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=<openrouter-api-key>
OPENROUTER_MODEL=openai/gpt-4o-mini

# Used only when manually running Alembic migrations; do not add this to the web service.
MIGRATIONS_DATABASE_URL=postgresql+asyncpg://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

## Cloudflare Workers build and runtime variables

Set these values in the Cloudflare Worker dashboard as both **Build variables** and **Worker runtime variables**. `NEXT_PUBLIC_*` values are intentionally browser-visible; never use a Supabase service-role key here.

```dotenv
NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com
APP_BASE_URL=https://flowpilot-web.<workers-dev-subdomain>.workers.dev
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<supabase-publishable-key>
```

## Final URL checklist

1. Configure a Workers.dev subdomain in Cloudflare, then deploy the Worker. The exact frontend CORS origin is `https://flowpilot-web.<workers-dev-subdomain>.workers.dev` with no trailing slash.
2. Create the Render service and copy its HTTPS URL into `NEXT_PUBLIC_API_URL`, the OAuth callback URLs, and the Supabase allowed redirect URLs.
3. Paste the final frontend URL into Render `CORS_ORIGINS` and `CONNECTION_SUCCESS_URL`.
4. Run `alembic upgrade head` once against the production Supabase database before sending traffic to the API.

Render Free runs the action and Gmail workers in the FastAPI process only while the service is awake. Scheduled work can be delayed after idle sleep; this is appropriate for a demo, not continuous production automation.

## Google-only authentication correction

The current local authentication implementation does not use Supabase Auth. Ignore the previous `NEXT_PUBLIC_SUPABASE_*`, `SUPABASE_URL`, `SUPABASE_JWKS_URL`, and Supabase provider instructions when deploying this version. Keep `DATABASE_URL` only because the application still needs PostgreSQL; it may point at Supabase Postgres or any compatible PostgreSQL host.

Use these Render values for direct Google login:

```dotenv
FLOWPILOT_ENV=production
CORS_ORIGINS=https://flowpilot-web.sarkarsujit9052.workers.dev
AUTH_APP_URL=https://flowpilot-web.sarkarsujit9052.workers.dev
AUTH_GOOGLE_CLIENT_ID=<google-web-oauth-client-id>
AUTH_GOOGLE_CLIENT_SECRET=<google-web-oauth-client-secret>
AUTH_GOOGLE_REDIRECT_URI=https://flowpilot-s0lr.onrender.com/api/v1/auth/google/callback
AUTH_SESSION_SECRET=<independent-random-secret>
AUTH_STATE_SECRET=<independent-random-secret>
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_DOMAIN=
```

For the Cloudflare frontend, the only required public build/runtime variable is:

```dotenv
NEXT_PUBLIC_API_URL=https://flowpilot-s0lr.onrender.com
APP_BASE_URL=https://flowpilot-web.sarkarsujit9052.workers.dev
```

`CONNECTION_SUCCESS_URL`, `GOOGLE_CLIENT_ID`, and `GOOGLE_REDIRECT_URI` without the `AUTH_` prefix are only for the optional Google Calendar/Gmail/Drive connector. They are not needed for Google login.
