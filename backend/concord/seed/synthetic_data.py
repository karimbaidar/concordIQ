"""Generate deterministic, synthetic B2B SaaS data for Concord IQ."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

FIXED_SEED = 20260606
REFERENCE_DATE = date(2026, 6, 1)
CUSTOMER_COUNT = 120

type Scalar = str | int | float
type Row = dict[str, Scalar]

TABLE_FIELDS: dict[str, tuple[str, ...]] = {
    "customers": (
        "customer_id",
        "customer_name",
        "region",
        "segment",
        "annual_recurring_revenue",
        "created_at",
    ),
    "contracts": (
        "contract_id",
        "customer_id",
        "start_date",
        "end_date",
        "status",
        "grace_days",
        "monthly_recurring_revenue",
    ),
    "opportunities": (
        "opportunity_id",
        "customer_id",
        "stage",
        "updated_at",
        "amount",
    ),
    "usage_events": (
        "usage_event_id",
        "customer_id",
        "event_date",
        "event_type",
        "qualifying",
    ),
    "revenue_events": (
        "revenue_event_id",
        "customer_id",
        "event_date",
        "amount",
        "event_type",
    ),
    "churn_events": (
        "churn_event_id",
        "customer_id",
        "finance_churn_date",
        "cs_churn_date",
        "reason",
    ),
    "reports": (
        "report_id",
        "business_unit",
        "report_name",
        "business_term",
        "decision_criticality",
    ),
}


@dataclass(frozen=True)
class SyntheticDataset:
    """In-memory synthetic tables plus a canonical content digest."""

    tables: dict[str, list[Row]]
    seed: int
    reference_date: date

    @property
    def digest(self) -> str:
        payload = json.dumps(
            {
                "reference_date": self.reference_date.isoformat(),
                "seed": self.seed,
                "tables": self.tables,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def row_counts(self) -> dict[str, int]:
        return {name: len(rows) for name, rows in self.tables.items()}


def _iso(value: date) -> str:
    return value.isoformat()


def generate_synthetic_data(seed: int = FIXED_SEED) -> SyntheticDataset:
    """Build fixed-date cohorts that support the planned reconciliation scenarios."""
    rng = random.Random(seed)
    tables: dict[str, list[Row]] = {name: [] for name in TABLE_FIELDS}
    regions = ("North America", "Europe", "Asia Pacific")
    segments = ("Enterprise", "Mid-Market", "Growth")
    event_types = ("dashboard_view", "api_call", "workflow_run")

    for index in range(1, CUSTOMER_COUNT + 1):
        customer_id = f"C{index:04d}"
        arr = rng.randrange(24, 241) * 1_000
        mrr = round(arr / 12, 2)
        created_at = REFERENCE_DATE - timedelta(days=400 + rng.randrange(0, 900))

        tables["customers"].append(
            {
                "customer_id": customer_id,
                "customer_name": f"Northstar Synthetic {index:03d}",
                "region": regions[(index - 1) % len(regions)],
                "segment": segments[(index - 1) % len(segments)],
                "annual_recurring_revenue": arr,
                "created_at": _iso(created_at),
            }
        )

        contract_active = index % 6 != 0
        contract_end = (
            REFERENCE_DATE + timedelta(days=120 + index)
            if contract_active
            else REFERENCE_DATE - timedelta(days=10 + index % 75)
        )
        tables["contracts"].append(
            {
                "contract_id": f"CTR{index:04d}",
                "customer_id": customer_id,
                "start_date": _iso(created_at + timedelta(days=30)),
                "end_date": _iso(contract_end),
                "status": "active" if contract_active else "expired",
                "grace_days": (0, 15, 30)[index % 3],
                "monthly_recurring_revenue": mrr,
            }
        )

        sales_active = index % 4 != 0
        tables["opportunities"].append(
            {
                "opportunity_id": f"OPP{index:04d}",
                "customer_id": customer_id,
                "stage": ("open" if index % 2 else "won") if sales_active else "closed_lost",
                "updated_at": _iso(
                    REFERENCE_DATE
                    - timedelta(days=index % 150 if sales_active else 190 + index % 80)
                ),
                "amount": round(arr * rng.uniform(0.8, 1.25), 2),
            }
        )

        usage_recent = index % 3 != 0
        usage_date = REFERENCE_DATE - timedelta(
            days=index % 29 if usage_recent else 65 + index % 100
        )
        tables["usage_events"].append(
            {
                "usage_event_id": f"USE{index:04d}",
                "customer_id": customer_id,
                "event_date": _iso(usage_date),
                "event_type": event_types[index % len(event_types)],
                "qualifying": 1,
            }
        )

        finance_active = index % 5 != 0
        revenue_date = REFERENCE_DATE - timedelta(
            days=index % 89 if finance_active else 100 + index % 120
        )
        tables["revenue_events"].append(
            {
                "revenue_event_id": f"REV{index:04d}",
                "customer_id": customer_id,
                "event_date": _iso(revenue_date),
                "amount": mrr,
                "event_type": "recognized_revenue",
            }
        )

        finance_churned = not contract_active
        cs_churned = not usage_recent
        if finance_churned or cs_churned:
            finance_churn_date = _iso(contract_end) if finance_churned else ""
            cs_churn_date = _iso(usage_date + timedelta(days=60)) if cs_churned else ""
            tables["churn_events"].append(
                {
                    "churn_event_id": f"CHN{index:04d}",
                    "customer_id": customer_id,
                    "finance_churn_date": finance_churn_date,
                    "cs_churn_date": cs_churn_date,
                    "reason": "synthetic cohort divergence",
                }
            )

    tables["reports"] = [
        {
            "report_id": "RPT001",
            "business_unit": "Finance",
            "report_name": "Quarterly Board Metrics",
            "business_term": "Active Customer",
            "decision_criticality": "high",
        },
        {
            "report_id": "RPT002",
            "business_unit": "Sales",
            "report_name": "Enterprise Pipeline",
            "business_term": "Active Customer",
            "decision_criticality": "high",
        },
        {
            "report_id": "RPT003",
            "business_unit": "Customer Success",
            "report_name": "Adoption Health",
            "business_term": "Active Customer",
            "decision_criticality": "high",
        },
        {
            "report_id": "RPT004",
            "business_unit": "Finance",
            "report_name": "Net Revenue",
            "business_term": "Net Revenue",
            "decision_criticality": "high",
        },
        {
            "report_id": "RPT005",
            "business_unit": "Sales",
            "report_name": "Booked Revenue",
            "business_term": "Net Revenue",
            "decision_criticality": "medium",
        },
        {
            "report_id": "RPT006",
            "business_unit": "Customer Success",
            "report_name": "Retention Review",
            "business_term": "Churned Customer",
            "decision_criticality": "high",
        },
    ]

    return SyntheticDataset(tables=tables, seed=seed, reference_date=REFERENCE_DATE)


def write_synthetic_csvs(dataset: SyntheticDataset, output_dir: Path) -> None:
    """Write stable CSV files with explicit columns and Unix line endings."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for table_name, fields in TABLE_FIELDS.items():
        output_path = output_dir / f"{table_name}.csv"
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(dataset.tables[table_name])
