from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ENTITY_TABLES = {
    "CertificationReady": {
        "table": "ciq_certification_ready",
        "key": "learner_id",
        "display": "canonical_term",
        "columns": {
            "concept_key": "String",
            "canonical_term": "String",
            "learner_id": "String",
            "employee_id": "String",
            "certification_id": "String",
            "certification_name": "String",
            "hr_eligible": "Boolean",
            "lms_claimed_ready": "Boolean",
            "manager_approved": "Boolean",
            "modules_completed": "BigInt",
            "modules_required": "BigInt",
            "labs_completed": "BigInt",
            "labs_required": "BigInt",
            "assessment_score": "BigInt",
            "assessment_passed": "Boolean",
            "truth_certification_ready": "Boolean",
            "false_ready": "Boolean",
            "decision": "String",
            "conflict_reason_count": "BigInt",
            "conflict_reasons": "String",
            "source_systems_compared": "String",
            "evaluated_on": "DateTime",
        },
    },
    "Learner": {
        "table": "ciq_learners",
        "key": "learner_id",
        "display": "full_name",
        "columns": {
            "learner_id": "String",
            "employee_id": "String",
            "full_name": "String",
            "email": "String",
            "role": "String",
            "department": "String",
            "region": "String",
            "manager_id": "String",
            "employment_status": "String",
            "role_requires_certification": "Boolean",
            "hire_date": "DateTime",
            "source_system": "String",
        },
    },
    "FalseReadyLearner": {
        "table": "ciq_false_ready_learners",
        "key": "learner_id",
        "display": "canonical_term",
        "columns": {
            "learner_id": "String",
            "employee_id": "String",
            "certification_id": "String",
            "canonical_term": "String",
            "lms_claimed_ready": "Boolean",
            "truth_certification_ready": "Boolean",
            "block_reason": "String",
            "risk_level": "String",
            "recommended_action": "String",
            "evaluated_on": "DateTime",
        },
    },
    "ReadinessDefinition": {
        "table": "ciq_readiness_definitions",
        "key": "definition_id",
        "display": "display_name",
        "columns": {
            "definition_id": "String",
            "entity_type": "String",
            "display_name": "String",
            "canonical_term": "String",
            "definition_text": "String",
            "false_ready_rule": "String",
            "owner_department": "String",
            "review_status": "String",
            "effective_on": "DateTime",
        },
    },
    "Certification": {
        "table": "ciq_certifications",
        "key": "certification_id",
        "display": "certification_name",
        "columns": {
            "certification_id": "String",
            "certification_name": "String",
            "certification_term": "String",
            "entity_type": "String",
            "version": "String",
            "owner_department": "String",
            "validity_days": "BigInt",
            "minimum_assessment_score": "BigInt",
            "requires_all_modules": "Boolean",
            "requires_all_labs": "Boolean",
            "requires_manager_approval": "Boolean",
            "created_on": "DateTime",
        },
    },
    "ModuleCompletion": {
        "table": "ciq_module_completions",
        "key": "learner_id",
        "display": "module_name",
        "columns": {
            "learner_id": "String",
            "certification_id": "String",
            "module_id": "String",
            "module_name": "String",
            "completion_status": "String",
            "completion_score": "BigInt",
            "completed_on": "DateTime",
            "source_system": "String",
        },
    },
    "LabCompletion": {
        "table": "ciq_lab_completions",
        "key": "learner_id",
        "display": "lab_name",
        "columns": {
            "learner_id": "String",
            "certification_id": "String",
            "lab_id": "String",
            "lab_name": "String",
            "completion_status": "String",
            "completed_on": "DateTime",
            "source_system": "String",
        },
    },
    "PracticeAssessment": {
        "table": "ciq_practice_assessments",
        "key": "assessment_id",
        "display": "assessment_name",
        "columns": {
            "learner_id": "String",
            "certification_id": "String",
            "assessment_id": "String",
            "assessment_name": "String",
            "latest_score": "BigInt",
            "passed": "Boolean",
            "attempts": "BigInt",
            "last_attempt_on": "DateTime",
            "source_system": "String",
        },
    },
    "ManagerApproval": {
        "table": "ciq_manager_approvals",
        "key": "learner_id",
        "display": "approval_status",
        "columns": {
            "learner_id": "String",
            "certification_id": "String",
            "manager_id": "String",
            "approval_status": "String",
            "approved_on": "DateTime",
            "source_system": "String",
        },
    },
    "RequiredModule": {
        "table": "ciq_required_modules",
        "key": "module_id",
        "display": "module_name",
        "columns": {
            "module_id": "String",
            "certification_id": "String",
            "module_name": "String",
            "sequence_number": "BigInt",
            "required": "Boolean",
        },
    },
    "RequiredLab": {
        "table": "ciq_required_labs",
        "key": "lab_id",
        "display": "lab_name",
        "columns": {
            "lab_id": "String",
            "certification_id": "String",
            "lab_name": "String",
            "sequence_number": "BigInt",
            "required": "Boolean",
        },
    },
}


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def token() -> str:
    result = subprocess.run(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            "https://api.fabric.microsoft.com",
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    access_token = result.stdout.strip()
    if not access_token:
        raise RuntimeError("Empty Fabric token from Azure CLI")
    return access_token


def call(method: str, url: str, access_token: str, body: dict | None = None) -> tuple[int, dict, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=120) as response:  # noqa: S310
            raw = response.read().decode("utf-8", "replace")
            payload = json.loads(raw) if raw.strip() else {}
            return response.status, dict(response.headers), payload
    except HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"{method} {url} failed HTTP {error.code}: {raw[:3000]}") from error


def b64(obj: dict) -> str:
    raw = json.dumps(obj, indent=2).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def stable_bigint(*parts: str) -> str:
    import hashlib

    digest = hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()
    # keep positive and below signed 63-bit
    return str(int(digest[:15], 16) % 9_000_000_000_000_000_000 + 1_000_000_000_000)


def list_ontologies(workspace_id: str, access_token: str) -> list[dict]:
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/ontologies"
    _, _, payload = call("GET", url, access_token)
    return payload.get("data", [])


def get_definition(workspace_id: str, ontology_id: str, access_token: str) -> dict:
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/ontologies/{ontology_id}/getDefinition"
    _, headers, payload = call("POST", url, access_token, {})
    location = headers.get("Location") or headers.get("location")

    if not location:
        return payload.get("definition", payload)

    for _ in range(80):
        _, _, status = call("GET", location, access_token)
        state = str(status.get("status", status.get("Status", ""))).lower()
        if state in {"succeeded", "success", "completed", "3"}:
            return status.get("definition", status)
        if state in {"failed", "4"}:
            raise RuntimeError(json.dumps(status, indent=2))
        time.sleep(5)

    raise TimeoutError("Timed out waiting for getDefinition")


def build_definition(workspace_id: str, lakehouse_id: str, ontology_name: str) -> dict:
    parts = [
        {
            "path": ".platform",
            "payload": b64({"metadata": {"type": "Ontology", "displayName": ontology_name}}),
            "payloadType": "InlineBase64",
        },
        {
            "path": "definition.json",
            "payload": b64({}),
            "payloadType": "InlineBase64",
        },
    ]

    for entity_name, spec in ENTITY_TABLES.items():
        entity_id = stable_bigint("entity", entity_name)
        property_ids = {
            col: stable_bigint("property", entity_name, col)
            for col in spec["columns"]
        }

        key_property_id = property_ids[spec["key"]]
        display_property_id = property_ids[spec["display"]]

        properties = [
            {
                "id": property_ids[column],
                "name": column,
                "redefines": None,
                "baseTypeNamespaceType": None,
                "valueType": value_type,
            }
            for column, value_type in spec["columns"].items()
        ]

        entity_definition = {
            "id": entity_id,
            "namespace": "usertypes",
            "baseEntityTypeId": None,
            "name": entity_name,
            "entityIdParts": [key_property_id],
            "displayNamePropertyId": display_property_id,
            "namespaceType": "Custom",
            "visibility": "Visible",
            "properties": properties,
            "timeseriesProperties": [],
        }

        binding_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"concord-iq:{entity_name}:{spec['table']}"))
        data_binding = {
            "id": binding_id,
            "dataBindingConfiguration": {
                "dataBindingType": "NonTimeSeries",
                "propertyBindings": [
                    {
                        "sourceColumnName": column,
                        "targetPropertyId": property_ids[column],
                    }
                    for column in spec["columns"]
                ],
                "sourceTableProperties": {
                    "sourceType": "LakehouseTable",
                    "workspaceId": workspace_id,
                    "itemId": lakehouse_id,
                    "sourceTableName": spec["table"],
                    "sourceSchema": "dbo",
                },
            },
        }

        parts.append(
            {
                "path": f"EntityTypes/{entity_id}/definition.json",
                "payload": b64(entity_definition),
                "payloadType": "InlineBase64",
            }
        )
        parts.append(
            {
                "path": f"EntityTypes/{entity_id}/DataBindings/{binding_id}.json",
                "payload": b64(data_binding),
                "payloadType": "InlineBase64",
            }
        )

    return {"parts": parts}


def update_definition(workspace_id: str, ontology_id: str, definition: dict, access_token: str) -> None:
    url = (
        f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"
        f"/ontologies/{ontology_id}/updateDefinition?updateMetadata=True"
    )
    status, headers, payload = call("POST", url, access_token, {"definition": definition})
    location = headers.get("Location") or headers.get("location")

    if not location:
        print(f"Update returned HTTP {status}")
        print(json.dumps(payload, indent=2)[:4000])
        return

    print(f"Update accepted. Polling: {location}")

    for _ in range(80):
        _, _, status_payload = call("GET", location, access_token)
        state = str(status_payload.get("status", status_payload.get("Status", ""))).lower()
        print(f"Operation status: {state}")

        if state in {"succeeded", "success", "completed", "3"}:
            print("Ontology definition update completed.")
            return
        if state in {"failed", "4"}:
            raise RuntimeError(json.dumps(status_payload, indent=2))

        time.sleep(5)

    raise TimeoutError("Timed out waiting for ontology updateDefinition")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--ontology-id", default=os.environ.get("FABRIC_ONTOLOGY_ID", ""))
    parser.add_argument("--ontology-name", default=os.environ.get("FABRIC_ONTOLOGY_NAME", "ConcordIQCertificationOntology"))
    parser.add_argument("--out", default="fabric_seed/certification_ready_ontology_definition.json")
    args = parser.parse_args()

    load_dotenv()

    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "").strip()
    lakehouse_id = os.environ.get("FABRIC_LAKEHOUSE_ID", "").strip()

    if not workspace_id:
        raise SystemExit("Missing FABRIC_WORKSPACE_ID")
    if not lakehouse_id:
        raise SystemExit("Missing FABRIC_LAKEHOUSE_ID. Use the Lakehouse that contains ciq_certification_ready.")

    access_token = token()

    if args.list:
        print("Ontologies in workspace:")
        for item in list_ontologies(workspace_id, access_token):
            print(json.dumps(item, indent=2))
        return

    ontology_id = args.ontology_id.strip()

    if not ontology_id:
        ontologies = list_ontologies(workspace_id, access_token)
        matches = [
            item for item in ontologies
            if args.ontology_name.lower() in item.get("displayName", item.get("name", "")).lower()
        ]

        if not matches:
            print("No ontology matched. Available ontologies:")
            for item in ontologies:
                print(f"- {item.get('displayName') or item.get('name')}  id={item.get('id')}")
            raise SystemExit("Set FABRIC_ONTOLOGY_ID=<ontology id> and rerun.")

        ontology_id = matches[0]["id"]
        print(f"Using ontology: {matches[0].get('displayName') or matches[0].get('name')} ({ontology_id})")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    definition = build_definition(workspace_id, lakehouse_id, args.ontology_name)
    out_path.write_text(json.dumps({"definition": definition}, indent=2), encoding="utf-8")
    print(f"Wrote definition payload: {out_path}")

    backup_dir = Path("fabric_seed/ontology_backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    try:
        current = get_definition(workspace_id, ontology_id, access_token)
        backup_path = backup_dir / f"ontology_backup_{ontology_id}_{int(time.time())}.json"
        backup_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        print(f"Backed up current ontology definition: {backup_path}")
    except Exception as error:
        print(f"Warning: could not backup current definition: {error}")

    if not args.apply:
        print("\nDry run only. To apply:")
        print(f"FABRIC_ONTOLOGY_ID={ontology_id} .venv/bin/python {Path(__file__).as_posix()} --apply")
        return

    update_definition(workspace_id, ontology_id, definition, access_token)
    print("\nDONE.")
    print("Now rerun make fabric-mcp-diagnose.")


if __name__ == "__main__":
    main()
