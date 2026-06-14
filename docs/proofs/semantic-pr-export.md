# Semantic PR export — Active Customer

> Governed definition-change artifact. Generated deterministically from executed SQL;
> contains no secrets and no tenant data.

- **Term:** Active Customer
- **Verdict:** `conflict`
- **SHA-256:** `81582bd5768365f016032a90dc0c089075aab911e71d03747d5e84ecdb002d5e`
- **Timestamp (UTC):** 2026-06-14T09:22:46Z
- **Machine-readable artifact:** `artifacts/semantic-pr/latest.json`

## Conflicting definitions

| Team | Definition | Count |
|---|---|---:|
| Finance | Customer with recognized revenue during the trailing 90-day reporting window. | 1,600 |
| Sales | Customer with an open or won opportunity updated during the trailing 180 days. | 1,500 |
| Customer Success | Customer with an active contract and qualifying product usage in the trailing 30 days. | 1,334 |

## Proposed canonical definition

Active Customer means a customer with an active contract and qualifying usage in the trailing 30 days. Finance and Sales variants remain named domain views and must not publish under the unqualified canonical term.

- **Source definition:** `active_customer_customer_success`
- **Rationale:** The three executed definitions diverge by 266 customers and 33,198,000.00 ARR. The proposed canonical definition uses the contract and usage semantics from Customer Success Active Customer; Finance Active Customer remains a governed financial activity view.
- **Expected dashboard impact:** Up to 266 customers and 33,198,000.00 ARR differ across current views.

## Governance

- **Owner / approver:** Data Governance Council
- **Authority status:** `clear`
- **Requires human approval:** True

## SQL / verifier result

- **Verdict:** `conflict`
- **Verification status:** `passed`
- **Deterministic checks passed:** 17/17

## Evidence IDs

- `6dc955c4-41fe-5c7a-96c2-6641ab12d0a8`
- `4dce6ac6-409f-580b-a3d3-e3c21d543c02`
- `fe70d2bd-1683-58eb-993e-f4c1f3852abc`

The canonical proposal is exported with `requires_human_approval=true`. Concord IQ
never merges a canonical definition without the configured governance owner.
