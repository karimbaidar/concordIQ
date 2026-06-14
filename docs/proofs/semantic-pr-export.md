# Semantic PR export — Active Customer

> Governed definition-change artifact. Generated deterministically from executed SQL;
> contains no secrets and no tenant data.

- **Term:** Active Customer
- **Verdict:** `conflict`
- **SHA-256:** `81582bd5768365f016032a90dc0c089075aab911e71d03747d5e84ecdb002d5e`
- **Timestamp (UTC):** 2026-06-14T08:47:39Z
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

- `b864af43-6caf-5457-aa33-1fd710c502af`
- `1a3a0a56-09b6-53d1-b921-65f06264ac97`
- `59291ff0-592c-5adb-9ca2-f843596330e8`

The canonical proposal is exported with `requires_human_approval=true`. Concord IQ
never merges a canonical definition without the configured governance owner.
