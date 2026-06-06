# Fabric seed artifacts

These files are generated locally from Concord IQ's fixed-seed synthetic data,
`LocalProvider`, and the typed replay schema. They contain no tenant data or
credentials and do not prove a real Fabric IQ connection.

Use `make fabric-bootstrap-dry-run` to refresh them without Microsoft API calls.
Use `ALLOW_CLOUD=true make fabric-bootstrap` to create or reuse the supported
Fabric workspace, lakehouse, and preview ontology resources.

If preview ontology definition import is unavailable in your tenant, open the
generated ontology in Fabric, add or import the content in this directory, and
publish it. Then place the printed MCP endpoint and a short-lived token in your
local `.env` before running:

```bash
PROVIDER=fabric_iq ALLOW_CLOUD=true MAX_CLOUD_CALLS=6 make capture
make replay-check
```

The six-call Fabric budget covers MCP initialization, initialized notification,
tool discovery, and one semantic request for each of the three scenarios.
