# Cloud runtime

Cloud is off by default and fails closed. Every cloud mode acquires a **short-lived token
at runtime** and passes it to the child backend through the environment only. Tokens are
never printed, written to `.env`, placed on a command line, or committed. The
implementation lives in [`backend/concord/cloud_auth.py`](../backend/concord/cloud_auth.py)
and [`backend/concord/dev_launcher.py`](../backend/concord/dev_launcher.py).

Stable, non-secret configuration (endpoints, workspace IDs, client/tenant IDs) lives in a
local `.env` copied from [`.env.example`](../.env.example). Access tokens never go there.

## Switchable reviewer UI

```bash
make dev
```

This explicit presenter command acquires both Fabric and Foundry tokens, starts Learning
with Fabric IQ Live selected, and enables the UI runtime selector. Fabric Replay and
Local make no cloud calls. Foundry Agent Service Live calls the deployed hosted runtime
over the verified learning replay.

## Foundry-hosted UI

```bash
make dev-foundry
```

Reads `FOUNDRY_HOSTED_ENDPOINT` from `.env`, then acquires a token automatically:

```bash
az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv
```

It starts the stack with `PROVIDER=foundry_hosted`, `ALLOW_CLOUD=true`, strict workflow.
If Azure CLI authentication is missing it prints `Run: az login --tenant <configured
tenant>`.

## Live Fabric IQ UI

```bash
make dev-fabric
```

Requires the stable Fabric IDs/endpoint in `.env` (`FABRIC_WORKSPACE_ID`,
`FABRIC_LAKEHOUSE_ID`, `FABRIC_ONTOLOGY_ID`, `FABRIC_IQ_MCP_ENDPOINT`). It fails closed
with the exact missing names if any are absent, then acquires a Fabric token via Azure
CLI (`--resource https://api.fabric.microsoft.com`) and starts `PROVIDER=fabric_iq` with
an explicit cloud budget.

## Work IQ UI

```bash
make dev-work-iq
```

Uses MSAL delegated authentication through the Entra app configured by
`WORK_IQ_CLIENT_ID` and `WORK_IQ_TENANT_ID`. It attempts silent acquisition from a
user-local MSAL cache (`~/.cache/concord-iq/msal-token-cache.json`, outside the repo), and
falls back to device-code sign-in. It requests the delegated scopes `User.Read`,
`Files.Read.All`, `Sites.Read.All` and validates the token contains them.

Install the optional dependency once: `uv sync --extra cloud`.

If Microsoft returns a license-entitlement error, Concord IQ reports:

```text
Work IQ authentication and delegated permissions succeeded.
Microsoft 365 Retrieval API remains license-gated for this tenant.
```

License-gated is never classified as successful retrieval.

## One-command live cloud proof

```bash
make cloud-proof
```

Runs every configured live proof — Foundry Agent Service, Fabric IQ (replay always; live
diagnostics when configured), and Work IQ retrieval — and records each outcome honestly
as `passed`, `skipped`, `license_gated`, `permission_blocked`, or `failed`. Missing
optional configuration is `skipped` and never fails the command. Reports are written to
`docs/proofs/cloud-proof-report.md` and `artifacts/proof/cloud-latest.json` with no
tokens, Authorization headers, or tenant URLs.

## Safety guarantees

- `make dev-local` forces safe local mode and strips inherited cloud tokens.
- `make dev` is the explicit cloud-enabled reviewer command and keeps tokens only in the
  backend child environment.
- Cloud providers fail closed without explicit permission, a positive budget, an
  endpoint, and authentication.
- Automated tests inject token runners/transports and never call Microsoft services.
- See [cost controls](cost-controls.md) for the Fabric F2 budget runbook.
