# Concord IQ — submission checklist

Microsoft Agents League 2026 · Track: Reasoning Agents · Challenge A: Enterprise Learning System

## Product

- [x] **Default pack is `learning`** — missing `CONCORD_SCENARIO_PACK` defaults to learning.
- [x] **Business pack still switches** — `CONCORD_SCENARIO_PACK=business` runs the preserved pack.
- [x] **Three-act learning arc present** — all run through the real ten-stage workflow:
  - [x] Conflict — `certification-ready` (80/56/56, 24 false-ready, $10,800 at risk → governed proposal).
  - [x] Decoy — `required-training-complete` (80/80, same set → `consistent`, no proposal/refusal).
  - [x] Refusal — `exam-eligible` (80/56 under ambiguous authority → refusal, no promotion).
- [x] Certification-ready numbers and the synthetic seed digest are unchanged.
- [x] **Exact case lifecycle** — the Court receives a bounded cached case by `run_id`,
  performs no second reconciliation/cloud call, and creates no duplicate proposal.
- [x] **Second Agent Framework workflow** — conditional Court graph, pairwise evidence,
  targeted replan, distinct steward dispositions, immutable engine verdict.
- [x] Hosted cases import idempotently into the local registry for owner-gated approval;
  governed reruns execute locally with no Fabric or Foundry writeback.

## Docs & honesty

- [x] **README and script updated** — the 120-learner workbench and separate 10,000-row
  Fabric scale artifact are never presented as one execution.
- [x] Two UI phases are explicit: ten-stage evidence workflow, then the separate Court
  over the frozen run.
- [x] Architecture image added at `docs/assets/architecture.png` and linked from README.
- [x] Mermaid architecture, lifecycle, IQ provenance, and trust-boundary diagrams align
  with the Learning system.

## Gates (real, reproducible)

- [x] `make test` → **230 backend passed, 1 skipped; 16 frontend passed**.
- [x] `make lint` → ruff check + format clean; frontend `tsc` clean.
- [x] `make eval` → safety scorecard **15/15** (business pack plus Court invariants,
  LLM disabled).
- [x] `make judge-proof` → eight mandatory local checks **PASSED**;
  Foundry/Fabric-live **SKIPPED**, Work IQ **LICENSE-GATED** (honest, not a success claim).
- [x] Secret scan clean; `.env` not tracked; `.env.example` token-free.

## IQ proof artifacts

- [x] Fabric IQ semantic grounding proven via committed sanitized replays for the
  business and Certification Ready packs.
- [x] Foundry Agent Service hosted Certification Ready invocation recorded over verified
  replay; the separate Court is not claimed as hosted.
- [x] **Fabric scale artifact** — 10,000 synthetic learners, 522 canonical-ready,
  4,334 false-ready, explicitly separated from the 120-learner workbench.
- [x] Semantic Court capture uses the repaired typed graph and digest-sealed transcript.
- [x] Work IQ live retrieval — license-gated in the available tenant; documented, never faked.

## Manual / pending submission steps

- [ ] Record, upload, and add the final 2–3 minute Challenge A demo video URL.
- [x] Repository is public at `https://github.com/karimbaidar/concordIQ`.
- [x] Submission text, architecture, proof links, and repo link are ready.
- [x] Final product changes pushed to the repository.

## Repo

- Repo link: https://github.com/karimbaidar/concordIQ
- Final video link: _pending_
