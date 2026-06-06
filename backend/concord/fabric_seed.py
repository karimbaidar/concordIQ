"""Export deterministic Concord IQ artifacts for a tiny Fabric setup."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from concord.config import Settings
from concord.demo import DEMO_SCENARIOS, DemoScenario
from concord.providers import LocalProvider
from concord.providers.replay_schema import ReplayScenarioSnapshot, snapshot_provider_scenario
from concord.seed.seed_duckdb import DEFAULT_DATA_DIR, seed_duckdb

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "fabric_seed"

SCENARIO_EXPLANATIONS = {
    "active-customer": (
        "Finance, Sales, and Customer Success use different activity windows and "
        "signals, producing a material three-way population conflict."
    ),
    "net-revenue": (
        "Finance and Sales describe Net Revenue differently, but their executable "
        "definitions select the same synthetic entities and totals."
    ),
    "churned-customer": (
        "Finance and Customer Success produce different churn populations, while "
        "shared and ambiguous authority requires a governed refusal."
    ),
}


@dataclass(frozen=True, slots=True)
class FabricSeedManifest:
    """Paths and typed snapshots produced by one deterministic export."""

    output_dir: Path
    snapshots: tuple[ReplayScenarioSnapshot, ...]
    files: tuple[Path, ...]


def _snapshot_markdown(
    scenario: DemoScenario,
    snapshot: ReplayScenarioSnapshot,
) -> str:
    explanation = SCENARIO_EXPLANATIONS[scenario.scenario_id]
    return (
        f"# {scenario.term} snapshot\n\n"
        f"{explanation}\n\n"
        "This artifact contains synthetic data only. The fenced JSON is generated "
        "from `LocalProvider` and validates as `ReplayScenarioSnapshot`.\n\n"
        "```json\n"
        f"{snapshot.model_dump_json(indent=2)}\n"
        "```\n"
    )


def _csv_text(headers: tuple[str, ...], rows: list[dict[str, object]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _metric_definitions_csv(snapshots: tuple[ReplayScenarioSnapshot, ...]) -> str:
    headers = (
        "scenario_id",
        "term",
        "concept_id",
        "definition_id",
        "binding_id",
        "name",
        "owner",
        "rule_text",
        "semantic_dimensions",
        "source_tables",
        "entity_key",
        "grain",
        "population",
        "time_window_days",
        "filters",
        "exclusions",
        "sql_template",
    )
    rows = [
        {
            "scenario_id": snapshot.scenario_id,
            "term": snapshot.term,
            "concept_id": binding.concept_id,
            "definition_id": binding.definition_id,
            "binding_id": binding.binding_id,
            "name": binding.name,
            "owner": binding.owner,
            "rule_text": binding.rule_text,
            "semantic_dimensions": "|".join(binding.semantic_dimensions),
            "source_tables": "|".join(binding.source_tables),
            "entity_key": binding.entity_key,
            "grain": binding.grain,
            "population": binding.population,
            "time_window_days": binding.time_window_days or "",
            "filters": "|".join(binding.filters),
            "exclusions": "|".join(binding.exclusions),
            "sql_template": binding.sql_template,
        }
        for snapshot in snapshots
        for binding in snapshot.bindings
    ]
    return _csv_text(headers, rows)


def _authority_rules_csv(snapshots: tuple[ReplayScenarioSnapshot, ...]) -> str:
    headers = (
        "scenario_id",
        "term",
        "concept_id",
        "semantic_dimension",
        "status",
        "owner",
        "rationale",
    )
    rows = [
        {
            "scenario_id": snapshot.scenario_id,
            "term": snapshot.term,
            "concept_id": rule.concept_id,
            "semantic_dimension": rule.semantic_dimension,
            "status": rule.status,
            "owner": rule.owner or "",
            "rationale": rule.rationale,
        }
        for snapshot in snapshots
        for rule in snapshot.authority_rules
    ]
    return _csv_text(headers, rows)


def _ontology_seed_markdown(snapshots: tuple[ReplayScenarioSnapshot, ...]) -> str:
    concepts = "\n".join(
        f"- **{snapshot.concept.canonical_name}** (`{snapshot.concept.concept_id}`): "
        f"{snapshot.concept.description}"
        for snapshot in snapshots
    )
    nodes: dict[str, tuple[str, str]] = {}
    relationships: set[tuple[str, str, str]] = set()
    for snapshot in snapshots:
        for node in snapshot.subgraph.nodes:
            nodes[node.node_id] = (node.node_type, node.label)
        relationships.update(
            (item.source, item.relationship_type, item.target)
            for item in snapshot.subgraph.relationships
        )
    node_lines = "\n".join(
        f"- `{node_id}`: {label} ({node_type})"
        for node_id, (node_type, label) in sorted(nodes.items())
    )
    relationship_lines = "\n".join(
        f"- `{source}` --{relationship_type}--> `{target}`"
        for source, relationship_type, target in sorted(relationships)
    )
    return f"""# Concord IQ ontology seed

This is a synthetic, human-readable seed for a tiny Fabric ontology. Use the
snapshot documents as semantic evidence and the CSV files as definition and
authority reference data.

## Business concepts

{concepts}

## Entity and concept nodes

{node_lines}

## Relationships

{relationship_lines}

## Suggested ontology setup

1. Create entity types for Business Concept, Metric Definition, Business Unit,
   Source Table, and Authority Rule.
2. Add the concept IDs and descriptions above.
3. Add definition ownership and operational dimensions from
   `metric_definitions.csv`.
4. Add governance ownership from `authority_rules.csv`.
5. Add the three snapshot markdown files as searchable semantic documents.
6. Publish the ontology before using its MCP endpoint.
"""


def _readme_text() -> str:
    return """# Fabric seed artifacts

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
"""


def _bootstrap_report_text() -> str:
    return """# Fabric bootstrap report

Mode: local dry run

- Synthetic DuckDB data was regenerated with the fixed Concord IQ seed.
- Three typed scenario snapshots were exported from LocalProvider.
- No Microsoft API was called.
- No access token or tenant identifier was written.
- Cloud bootstrap will create or reuse the configured workspace, lakehouse, and
  ontology, then print non-secret IDs and the MCP endpoint for manual `.env` entry.
"""


def _stable_numeric_id(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return str(int.from_bytes(digest[:8], "big") & ((1 << 63) - 1) or 1)


def _inline_json(value: dict[str, Any]) -> str:
    payload = json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode()
    return base64.b64encode(payload).decode("ascii")


def build_ontology_definition(
    ontology_name: str,
    snapshots: tuple[ReplayScenarioSnapshot, ...],
) -> dict[str, object]:
    """Build a small public-definition payload for the preview Ontology API."""
    parts: list[dict[str, str]] = [
        {
            "path": ".platform",
            "payload": _inline_json(
                {"metadata": {"type": "Ontology", "displayName": ontology_name}}
            ),
            "payloadType": "InlineBase64",
        },
        {
            "path": "definition.json",
            "payload": _inline_json({}),
            "payloadType": "InlineBase64",
        },
    ]
    for snapshot in snapshots:
        entity_id = _stable_numeric_id(f"entity:{snapshot.concept.concept_id}")
        name_property_id = _stable_numeric_id(f"name:{snapshot.concept.concept_id}")
        description_property_id = _stable_numeric_id(f"description:{snapshot.concept.concept_id}")
        scenario_property_id = _stable_numeric_id(f"scenario:{snapshot.concept.concept_id}")
        entity_name = "".join(part.capitalize() for part in snapshot.concept.concept_id.split("_"))
        entity = {
            "id": entity_id,
            "namespace": "usertypes",
            "baseEntityTypeId": None,
            "name": entity_name,
            "entityIdParts": [scenario_property_id],
            "displayNamePropertyId": name_property_id,
            "namespaceType": "Custom",
            "visibility": "Visible",
            "properties": [
                {
                    "id": name_property_id,
                    "name": "DisplayName",
                    "redefines": None,
                    "baseTypeNamespaceType": None,
                    "valueType": "String",
                },
                {
                    "id": description_property_id,
                    "name": "Description",
                    "redefines": None,
                    "baseTypeNamespaceType": None,
                    "valueType": "String",
                },
                {
                    "id": scenario_property_id,
                    "name": "ScenarioId",
                    "redefines": None,
                    "baseTypeNamespaceType": None,
                    "valueType": "String",
                },
            ],
            "timeseriesProperties": [],
        }
        parts.append(
            {
                "path": f"EntityTypes/{entity_id}/definition.json",
                "payload": _inline_json(entity),
                "payloadType": "InlineBase64",
            }
        )
    return {"parts": parts}


def export_fabric_seed(
    settings: Settings | None = None,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> FabricSeedManifest:
    """Regenerate local data and export all Fabric bootstrap artifacts."""
    active_settings = settings or Settings()
    seed_duckdb(database_path=active_settings.duckdb_path, data_dir=data_dir)
    provider = LocalProvider(duckdb_path=active_settings.duckdb_path)
    snapshots = tuple(snapshot_provider_scenario(provider, scenario) for scenario in DEMO_SCENARIOS)
    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for scenario, snapshot in zip(DEMO_SCENARIOS, snapshots, strict=True):
        path = output_dir / f"{scenario.scenario_id}-snapshot.md"
        path.write_text(_snapshot_markdown(scenario, snapshot), encoding="utf-8")
        files.append(path)

    generated = {
        "ontology_seed.md": _ontology_seed_markdown(snapshots),
        "metric_definitions.csv": _metric_definitions_csv(snapshots),
        "authority_rules.csv": _authority_rules_csv(snapshots),
        "bootstrap-report.md": _bootstrap_report_text(),
        "README.md": _readme_text(),
    }
    for name, content in generated.items():
        path = output_dir / name
        path.write_text(content, encoding="utf-8")
        files.append(path)

    return FabricSeedManifest(
        output_dir=output_dir,
        snapshots=snapshots,
        files=tuple(files),
    )
