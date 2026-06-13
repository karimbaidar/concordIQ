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

## Docs & honesty

- [x] **README updated** — three-act demo scenario described; "Microsoft IQ usage" reframed to the
  learning default with honest replay-capture wording; no claim that Fabric computed counts; no live
  Work IQ claim.
- [x] No architecture images claimed; screenshot/video placeholders retained.

## Gates (real, reproducible)

- [x] `make test` → **202 backend passed, 1 skipped; 12 frontend passed**.
- [x] `make lint` → ruff check + format clean; frontend `tsc` clean.
- [x] `make eval` → safety scorecard **11/11** (business pack, LLM disabled).
- [x] `make judge-proof` → six mandatory local checks **PASSED**; Foundry/Fabric-live **SKIPPED**,
  Work IQ **LICENSE-GATED** (honest, not a success claim).
- [x] Secret scan clean; `.env` not tracked; `.env.example` token-free.

## IQ proof artifacts

- [x] Fabric IQ semantic grounding proven via the committed sanitized replay (business pack).
- [x] Foundry Agent Service hosted invocation recorded as a sanitized capture.
- [ ] **Learning Certification Ready live capture** — scaffolded as the planned strongest artifact;
  runs only when Azure access + budget are available (`docs/proofs/`, `artifacts/replay/sanitized/`).
- [x] Work IQ live retrieval — license-gated in the available tenant; documented, never faked.

## Manual / pending submission steps

- [ ] Add architecture image (`docs/images/` placeholder).
- [ ] Record and link the 2–3 minute Challenge A demo video (README video placeholder).
- [ ] Push to `main` and make the repo public (user decision; nothing pushed yet).
- [ ] Submission text and repo link ready.

## Repo

- Repo link: _pending public push_
- Final video link: _pending_
