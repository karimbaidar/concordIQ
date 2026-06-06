# Fabric bootstrap report

Mode: dry run

- Seed artifacts were regenerated from LocalProvider.
- No access token was written or printed.

Manual ontology fallback:
1. Open the Fabric workspace.
2. Open ConcordIQOntology.
3. Add or import:
   - fabric_seed/ontology_seed.md
   - fabric_seed/active-customer-snapshot.md
   - fabric_seed/net-revenue-snapshot.md
   - fabric_seed/churned-customer-snapshot.md
4. Publish the ontology.
5. Put the printed MCP endpoint and a fresh token in .env, then run capture.
