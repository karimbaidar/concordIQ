# Deploy the public Concord IQ demo

The public deployment is intentionally cloud-free and starts in **verified Fabric IQ
Replay** mode. Reviewers can run the captured Certification Ready case, inspect exact
SQL evidence, convene the Semantic Court, and exercise the owner gate without receiving
Microsoft credentials.

The replay is a sanitized capture from the verified live Fabric IQ ontology. It is
clearly labeled as replay and never presented as a fresh cloud call.

## Free Render deployment

The repository includes:

- `Dockerfile.web`: builds the React UI and FastAPI API into one image;
- `render.yaml`: creates one free Render web service;
- `deploy/start_web.sh`: initializes the registry and starts the service.

The free demo uses an ephemeral SQLite registry. Approvals work during the active
service session, but the registry resets after a restart, redeploy, or free-instance
spin-down. That behavior is useful for a repeatable public demo. It is not production
persistence.

### Steps

1. Sign in to [Render](https://dashboard.render.com/) with GitHub.
2. Open the Concord IQ Blueprint:
   [Deploy Concord IQ](https://dashboard.render.com/blueprint/new?repo=https://github.com/karimbaidar/concordIQ)
3. Select the `main` branch and accept the detected `render.yaml`.
4. Choose the free instance type if Render asks for confirmation.
5. Click **Deploy Blueprint**.
6. Wait for the health check at `/health` to pass.
7. Open the generated `https://concord-iq-demo-....onrender.com` URL.
8. Confirm the runtime bar says **Fabric IQ Replay · no cloud**.
9. Run **Certification Ready**, then convene the Semantic Court.

Free Render web services can spin down after inactivity, so the first request after an
idle period can take about a minute. Their filesystem is ephemeral; this demo is
designed to reset safely. Automatic deploys are disabled in the public Blueprint so
each reviewer-created copy stays pinned until its owner chooses to redeploy it.

## Enabling live Microsoft modes

Do not place Microsoft tokens in GitHub or `render.yaml`. Live Fabric IQ and Foundry
Agent Service require short-lived credentials and active tenant resources. For a
presenter-controlled live demo, run `make dev` locally so the launcher acquires tokens
in memory through Azure CLI.

When credentials or an active Fabric capacity are unavailable, the hosted UI keeps the
live buttons disabled and explains that reviewers should use the verified replay.
Runtime cloud failures also return a friendly recovery action instead of raw provider
payloads or stack traces.

## Durable registry option

For a longer-lived installation, replace the SQLite `DATABASE_URL` with a managed
PostgreSQL connection string. Concord IQ initializes its schema automatically. Keep the
connection string in the hosting provider's secret environment settings, never in the
repository.
