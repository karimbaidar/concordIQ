# Foundry Agent Service

Concord IQ can expose its Microsoft Agent Framework workflow through the
Foundry Responses hosting protocol. The hosted surface remains a thin deployment
layer: specialist agents still call the deterministic reconciliation runner,
which owns SQL execution, evidence, authority, verification, and persistence.

## Cloud-free validation

Install and validate the optional preview host without opening a socket, touching
Microsoft services, or requiring Fabric credentials:

```bash
make foundry-agent-dry-run
```

The command forces `PROVIDER=local`, `ALLOW_CLOUD=false`, and
`MAX_CLOUD_CALLS=0`. It constructs the Agent Framework workflow, wraps it in
`ResponsesHostServer`, and verifies the `/readiness` and `/responses` routes.

Exercise the complete OpenAI-compatible Responses request path in process:

```bash
make foundry-agent-smoke
```

The default smoke uses LocalProvider, strict workflow mode, synthetic DuckDB
data, PostgreSQL persistence, all ten specialist steps, and no cloud call.
The command validates HTTP readiness, parses the returned typed casefile, and
requires deterministic verification to pass.

To exercise a reviewed sanitized replay artifact instead:

```bash
FOUNDRY_AGENT_PROVIDER=replay make foundry-agent-smoke
```

Replay mode requires the configured artifact to satisfy the existing verified
capture gate. It does not contact Fabric or Foundry.

## Why the host is stateless

Each request creates an independent reconciliation casefile, so the host builds a
fresh Agent Framework workflow per Responses request. The hosted smoke uses an
ephemeral SQLite database at
`sqlite+pysqlite:////tmp/concord_iq_foundry_learning.db`; production deployments can
replace it with a durable SQLAlchemy URL when persistent approval history is
required.

## Deploy with azd

The verified deployment path uses the Microsoft Foundry extension for Azure
Developer CLI:

1. Install [Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
   and the Foundry extension:

   ```bash
   azd extension install azure.ai.agents
   azd extension list
   ```

2. Initialize from the official hosted-agent quickstart:

   ```bash
   azd ai agent init
   ```

   Select the existing Foundry project `aiskillfest`, or create a new project.
   Leave Azure Container Registry and Application Insights blank if you want
   `azd` to create them. If `gpt-4.1-mini` quota is unavailable, select a model
   deployment with quota in the chosen region.

3. Copy the Concord IQ product files into the generated scaffold. Replace its
   `main.py` with:

   ```python
   from concord.ms_agent.foundry_hosted_entrypoint import main

   if __name__ == "__main__":
       main()
   ```

   Install the `foundry-hosting` extra and include `backend/concord/`,
   `pyproject.toml`, `uv.lock`, `ontology/`, `data/synthetic/`, and
   `artifacts/replay/sanitized/certification-ready.latest.json`. Do not include
   `.env`, access tokens,
   `.venv/`, `node_modules/`, `artifacts/replay/raw/`, diagnostics, or planning
   files.

4. Configure the hosted container:

   ```text
   PROVIDER=replay
   CONCORD_SCENARIO_PACK=learning
   CONCORD_WORKFLOW_MODE=strict
   ALLOW_CLOUD=false
   MAX_CLOUD_CALLS=0
   DATABASE_URL=sqlite+pysqlite:////tmp/concord_iq_foundry_learning.db
   REPLAY_ARTIFACT_PATH=artifacts/replay/sanitized/certification-ready.latest.json
   ```

   Use `CONCORD_WORKFLOW_MODE`, not `AGENT_WORKFLOW_MODE`; Foundry reserves the
   `AGENT_*` namespace.

5. Build and deploy the verified Linux AMD64 image:

   ```bash
   make foundry-hosted-deploy
   ```

   The target uses `azd deploy --from-package`, which falls back to a local Docker
   publish when ACR Tasks are disabled by tenant policy.

6. Inspect and verify:

   ```bash
   azd ai agent show concord-iq-2
   make foundry-hosted-smoke
   ```

   The verified Concord IQ response reports `provider_mode=replay`,
   `workflow_mode=strict`, `verdict=conflict`,
   `verification_status=passed`, and `specialist_steps=10`.

## Connect the main app

The application-side `FoundryHostedProvider` calls the full Foundry Responses
endpoint and never calls Fabric IQ. Put only local, gitignored values in `.env`:

```text
FOUNDRY_HOSTED_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>/agents/<agent>/endpoint/protocols/openai/responses?api-version=v1
FOUNDRY_HOSTED_AGENT_ID=
FOUNDRY_ACCESS_TOKEN=
```

`FOUNDRY_HOSTED_AGENT_ID` is optional for an agent-specific endpoint. Tokens are
acquired automatically and must remain empty in `.env`. Run:

```bash
make dev
```

Open `http://127.0.0.1:5173`, choose a scenario, and confirm the badge reads
**Foundry Agent Service**, **hosted runtime**, and **Cloud enabled**. `/analyze`,
`/ask`, and `/demo/run/{scenario_id}` all render the returned remote case through
the existing workbench.

The one-call proof check is:

```bash
make foundry-hosted-smoke
```

It validates the proof envelope and writes only a secret-free report under the
gitignored `artifacts/foundry/` folder.

## Safety

- Hosted mode refuses unless `ALLOW_CLOUD=true` and `MAX_CLOUD_CALLS` is positive.
- Missing endpoint or token configuration fails before any request.
- The access token is sent only in the Authorization header; it is never logged,
  persisted, or included in provider status.
- A completed response with empty output, wrong provider/workflow fields, or an
  unpassed verifier is rejected.
- The deployed replay runtime does not need Fabric credentials and does not make
  Fabric calls.

Do not assume Foundry, Fabric, or IQ usage is free or unlimited. Verify current
Microsoft pricing, trial limits, tenant settings, and permissions before enabling
cloud mode. Keep datasets tiny, use cloud only for smoke tests, pause or delete
idle resources, and replay sanitized captured responses through ReplayProvider
for demo rehearsal.

## Microsoft references

- [Host Agent Framework agents on Foundry](https://learn.microsoft.com/en-us/agent-framework/hosting/foundry-hosted-agent)
- [Hosted agents concepts](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents)
- [Azure Developer CLI installation](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
- [Foundry azd extension](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/extensions/azure-ai-foundry-extension)
