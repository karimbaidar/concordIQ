# Foundry Agent Service smoke proof

This document records a real hosted Foundry Agent Service smoke test for Concord IQ.

## What this proves

- Concord IQ was deployed to Microsoft Foundry Agent Service.
- The hosted `/responses` endpoint was invoked from the Concord IQ app.
- The hosted agent returned the strict Concord IQ proof envelope.
- `FoundryHostedProvider` accepted and validated that envelope.
- The verifier passed and the 10-step Microsoft Agent Framework workflow completed.

## Important honesty note

The hosted runtime uses `ReplayProvider` inside Foundry Agent Service for deterministic, reproducible evidence. Fabric IQ proof is carried by the sanitized replay artifact. No LLM decides the verdict.

This proof does not require judges to have access to my Azure subscription. The cloud resource may be deleted after proof/video capture to avoid ongoing cost.

## Captured run

```text
UTC timestamp:
Tue Jun  9 22:40:06 UTC 2026

Repo commit:
0f8beed6db3656b12edff98fc32a0c5b57b4e45a

Foundry hosted responses endpoint:
https://ai-account-ambiejfhijgv4.services.ai.azure.com/api/projects/ai-project-concord-iq-foundry-proof/agents/concord-iq/endpoint/protocols/openai/responses?api-version=v1

Smoke command output:
.venv/bin/python -m concord.ms_agent.foundry_hosted --smoke
Foundry Agent Service cloud runtime smoke verified.
{"provider_mode":"replay","workflow_mode":"strict","term":"Active Customer","verdict":"conflict","verification_status":"passed","specialist_steps":10}
```

## Local verification without Azure credentials

Judges can still verify the integration logic without my Azure credentials:

```bash
make test
make lint
make eval
make replay-check
```
