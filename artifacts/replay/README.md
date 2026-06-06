# Replay artifacts

Concord IQ separates provider captures into two locations:

- `raw/` contains exact cloud responses and is gitignored except for `.gitkeep`.
- `sanitized/` is public only after a human verifies that an artifact contains
  synthetic data, no credentials, and no tenant-identifying values.

`make capture` fails closed unless a cloud provider, `ALLOW_CLOUD=true`, a positive
`MAX_CLOUD_CALLS`, and the required endpoint and authentication are configured.
It writes raw responses first, validates them against the typed replay contract,
then writes a sanitized artifact for review.

No verified Microsoft IQ capture is currently committed. The `.gitkeep` file is
intentional; do not replace it with generated or locally fabricated output.
