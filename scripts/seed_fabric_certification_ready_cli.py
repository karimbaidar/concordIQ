from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import subprocess
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

SEED = 20260606
TODAY = date(2026, 6, 6)

CERT_ID = "cert-enterprise-ai-safety"
CERT_NAME = "Enterprise AI Safety Certification"

MODULES = [
    ("mod-policy", "AI Policy and Risk Controls", 1),
    ("mod-data", "Data Handling and Privacy", 2),
    ("mod-incident", "Incident Response Simulation", 3),
]

LABS = [
    ("lab-redteam", "Red Team Review Lab", 1),
    ("lab-escalation", "Manager Escalation Lab", 2),
]

ROLES = [
    "Sales Engineer",
    "Support Specialist",
    "Customer Success Manager",
    "Implementation Consultant",
    "Product Manager",
    "HR Business Partner",
    "Learning Program Manager",
    "Security Analyst",
]

DEPARTMENTS = [
    "Sales",
    "Support",
    "Customer Success",
    "Professional Services",
    "Product",
    "Human Resources",
    "Learning and Development",
    "Security",
]

REGIONS = ["NA", "EMEA", "APAC", "LATAM"]


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def stable_int(value: str, modulo: int) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


def bool_by_rate(key: str, rate_percent: int) -> bool:
    return stable_int(key, 100) < rate_percent


def csv_value(value):
    if isinstance(value, date):
        return value.isoformat()
    if value is None:
        return ""
    return value


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(value) for key, value in row.items()})


def storage_token() -> str:
    completed = subprocess.run(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            "https://storage.azure.com",
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    token = completed.stdout.strip()
    if not token:
        raise RuntimeError("Azure CLI returned an empty OneLake storage token.")
    return token


def onelake_url(workspace_id: str, lakehouse_id: str, relative_path: str) -> str:
    encoded = "/".join(quote(part) for part in relative_path.strip("/").split("/"))
    return f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}/{encoded}"


def request(method: str, url: str, token: str, data: bytes | None = None, extra_headers: dict | None = None) -> int:
    headers = {
        "Authorization": f"Bearer {token}",
        "x-ms-version": "2023-11-03",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=60) as response:  # noqa: S310
            return response.status
    except HTTPError as error:
        body = error.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"{method} {url} failed with HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"{method} {url} failed: {error.reason}") from error


def try_request(method: str, url: str, token: str, data: bytes | None = None, extra_headers: dict | None = None) -> None:
    try:
        request(method, url, token, data=data, extra_headers=extra_headers)
    except RuntimeError as error:
        text = str(error)
        if "HTTP 404" in text or "HTTP 409" in text:
            return
        raise


def ensure_directory(workspace_id: str, lakehouse_id: str, relative_dir: str, token: str) -> None:
    parts = relative_dir.strip("/").split("/")
    current = []
    for part in parts:
        current.append(part)
        path = "/".join(current)
        url = onelake_url(workspace_id, lakehouse_id, path) + "?resource=directory"
        try_request("PUT", url, token)


def upload_file(workspace_id: str, lakehouse_id: str, local_path: Path, remote_path: str, token: str) -> None:
    body = local_path.read_bytes()
    remote_dir = "/".join(remote_path.split("/")[:-1])
    ensure_directory(workspace_id, lakehouse_id, remote_dir, token)

    base_url = onelake_url(workspace_id, lakehouse_id, remote_path)
    try_request("DELETE", base_url, token)

    request("PUT", f"{base_url}?resource=file", token)
    if body:
        request(
            "PATCH",
            f"{base_url}?action=append&position=0",
            token,
            data=body,
            extra_headers={"Content-Length": str(len(body))},
        )
    request("PATCH", f"{base_url}?action=flush&position={len(body)}", token)


def build_seed(n_learners: int) -> dict[str, list[dict]]:
    random.Random(SEED)

    certifications = [
        {
            "certification_id": CERT_ID,
            "certification_name": CERT_NAME,
            "certification_term": "Certification Ready",
            "entity_type": "CertificationReady",
            "version": "2026.06",
            "owner_department": "Learning and Development",
            "validity_days": 365,
            "minimum_assessment_score": 80,
            "requires_all_modules": True,
            "requires_all_labs": True,
            "requires_manager_approval": True,
            "created_on": TODAY,
        }
    ]

    readiness_definitions = [
        {
            "definition_id": "ready-v2026-06",
            "entity_type": "CertificationReady",
            "display_name": "Certification Ready",
            "canonical_term": "Certification Ready",
            "definition_text": (
                "A learner is Certification Ready only when HR confirms active eligibility, "
                "Learning and Development confirms all required modules and labs are complete, "
                "the practice assessment score is at least 80, and the manager approval is present."
            ),
            "false_ready_rule": (
                "False Ready means a source system marks the learner ready while at least one "
                "required control is missing."
            ),
            "owner_department": "Learning and Development",
            "review_status": "published",
            "effective_on": TODAY,
        }
    ]

    required_modules = [
        {
            "module_id": module_id,
            "certification_id": CERT_ID,
            "module_name": module_name,
            "sequence_number": sequence,
            "required": True,
        }
        for module_id, module_name, sequence in MODULES
    ]

    required_labs = [
        {
            "lab_id": lab_id,
            "certification_id": CERT_ID,
            "lab_name": lab_name,
            "sequence_number": sequence,
            "required": True,
        }
        for lab_id, lab_name, sequence in LABS
    ]

    learners = []
    module_completions = []
    lab_completions = []
    practice_assessments = []
    manager_approvals = []
    certification_ready = []
    false_ready_learners = []

    for i in range(1, n_learners + 1):
        learner_id = f"L{i:05d}"
        employee_id = f"E{i:05d}"

        role_idx = stable_int(f"{learner_id}:role", len(ROLES))
        dept_idx = role_idx % len(DEPARTMENTS)
        region = REGIONS[stable_int(f"{learner_id}:region", len(REGIONS))]

        employment_status = "Active" if bool_by_rate(f"{learner_id}:active", 94) else "Inactive"
        role_requires_certification = bool_by_rate(f"{learner_id}:requires_cert", 88)
        hire_date = TODAY - timedelta(days=stable_int(f"{learner_id}:hire", 1800) + 30)
        manager_id = f"M{stable_int(f'{learner_id}:manager', 80) + 1:03d}"

        learners.append(
            {
                "learner_id": learner_id,
                "employee_id": employee_id,
                "full_name": f"Learner {i:05d}",
                "email": f"learner{i:05d}@example.com",
                "role": ROLES[role_idx],
                "department": DEPARTMENTS[dept_idx],
                "region": region,
                "manager_id": manager_id,
                "employment_status": employment_status,
                "role_requires_certification": role_requires_certification,
                "hire_date": hire_date,
                "source_system": "HRIS",
            }
        )

        completed_module_count = 0
        for module_id, module_name, sequence in MODULES:
            completed = bool_by_rate(f"{learner_id}:{module_id}:completed", 86 - (sequence * 5))
            score = 65 + stable_int(f"{learner_id}:{module_id}:score", 36) if completed else None
            completed_on = TODAY - timedelta(days=stable_int(f"{learner_id}:{module_id}:date", 120)) if completed else None
            if completed:
                completed_module_count += 1

            module_completions.append(
                {
                    "learner_id": learner_id,
                    "certification_id": CERT_ID,
                    "module_id": module_id,
                    "module_name": module_name,
                    "completion_status": "completed" if completed else "missing",
                    "completion_score": score,
                    "completed_on": completed_on,
                    "source_system": "LMS",
                }
            )

        completed_lab_count = 0
        for lab_id, lab_name, sequence in LABS:
            completed = bool_by_rate(f"{learner_id}:{lab_id}:completed", 78 - (sequence * 6))
            passed = completed and bool_by_rate(f"{learner_id}:{lab_id}:passed", 92)
            completed_on = TODAY - timedelta(days=stable_int(f"{learner_id}:{lab_id}:date", 90)) if completed else None
            if completed and passed:
                completed_lab_count += 1

            lab_completions.append(
                {
                    "learner_id": learner_id,
                    "certification_id": CERT_ID,
                    "lab_id": lab_id,
                    "lab_name": lab_name,
                    "completion_status": "passed" if passed else ("failed" if completed else "missing"),
                    "completed_on": completed_on,
                    "source_system": "LabPlatform",
                }
            )

        assessment_score = 55 + stable_int(f"{learner_id}:assessment", 46)
        assessment_passed = assessment_score >= 80

        practice_assessments.append(
            {
                "learner_id": learner_id,
                "certification_id": CERT_ID,
                "assessment_id": f"A-{learner_id}",
                "assessment_name": "Certification Readiness Practice Assessment",
                "latest_score": assessment_score,
                "passed": assessment_passed,
                "attempts": 1 + stable_int(f"{learner_id}:attempts", 3),
                "last_attempt_on": TODAY - timedelta(days=stable_int(f"{learner_id}:assessment_date", 60)),
                "source_system": "AssessmentPlatform",
            }
        )

        manager_approved = bool_by_rate(f"{learner_id}:manager_approved", 74)

        manager_approvals.append(
            {
                "learner_id": learner_id,
                "certification_id": CERT_ID,
                "manager_id": manager_id,
                "approval_status": "approved" if manager_approved else "pending",
                "approved_on": TODAY - timedelta(days=stable_int(f"{learner_id}:approval_date", 45)) if manager_approved else None,
                "source_system": "ManagerPortal",
            }
        )

        hr_eligible = employment_status == "Active" and role_requires_certification
        all_modules_complete = completed_module_count == len(MODULES)
        all_labs_complete = completed_lab_count == len(LABS)
        true_ready = (
            hr_eligible
            and all_modules_complete
            and all_labs_complete
            and assessment_passed
            and manager_approved
        )

        lms_claimed_ready = completed_module_count >= 2 and assessment_score >= 75

        conflict_reasons = []
        if lms_claimed_ready and not hr_eligible:
            conflict_reasons.append("HR eligibility missing")
        if lms_claimed_ready and not all_modules_complete:
            conflict_reasons.append("Required module missing")
        if lms_claimed_ready and not all_labs_complete:
            conflict_reasons.append("Required lab missing")
        if lms_claimed_ready and not assessment_passed:
            conflict_reasons.append("Assessment below 80")
        if lms_claimed_ready and not manager_approved:
            conflict_reasons.append("Manager approval missing")

        false_ready = lms_claimed_ready and not true_ready
        decision = "certification_ready" if true_ready else "not_ready"
        if false_ready:
            decision = "false_ready_blocked"

        ready_row = {
            "concept_key": "CertificationReady",
            "canonical_term": "Certification Ready",
            "learner_id": learner_id,
            "employee_id": employee_id,
            "certification_id": CERT_ID,
            "certification_name": CERT_NAME,
            "hr_eligible": hr_eligible,
            "lms_claimed_ready": lms_claimed_ready,
            "manager_approved": manager_approved,
            "modules_completed": completed_module_count,
            "modules_required": len(MODULES),
            "labs_completed": completed_lab_count,
            "labs_required": len(LABS),
            "assessment_score": assessment_score,
            "assessment_passed": assessment_passed,
            "truth_certification_ready": true_ready,
            "false_ready": false_ready,
            "decision": decision,
            "conflict_reason_count": len(conflict_reasons),
            "conflict_reasons": "; ".join(conflict_reasons) if conflict_reasons else "none",
            "source_systems_compared": "HRIS; LMS; AssessmentPlatform; LabPlatform; ManagerPortal",
            "evaluated_on": TODAY,
        }

        certification_ready.append(ready_row)

        if false_ready:
            false_ready_learners.append(
                {
                    "learner_id": learner_id,
                    "employee_id": employee_id,
                    "certification_id": CERT_ID,
                    "canonical_term": "Certification Ready",
                    "lms_claimed_ready": lms_claimed_ready,
                    "truth_certification_ready": true_ready,
                    "block_reason": ready_row["conflict_reasons"],
                    "risk_level": "high" if len(conflict_reasons) >= 2 else "medium",
                    "recommended_action": "Block certification release until missing evidence is resolved",
                    "evaluated_on": TODAY,
                }
            )

    ontology_entities = [
        {
            "entity_type": "CertificationReady",
            "display_name": "Certification Ready",
            "source_table": "ciq_certification_ready",
            "primary_key": "learner_id",
            "search_terms": "Certification Ready; certification readiness; false readiness; learner ready",
            "description": "Canonical readiness decision joining HR, LMS, assessment, lab, and manager evidence.",
        },
        {
            "entity_type": "Learner",
            "display_name": "Learner",
            "source_table": "ciq_learners",
            "primary_key": "learner_id",
            "search_terms": "learner; employee; participant",
            "description": "Person who may need enterprise certification.",
        },
        {
            "entity_type": "Certification",
            "display_name": "Certification",
            "source_table": "ciq_certifications",
            "primary_key": "certification_id",
            "search_terms": "certification; enterprise AI safety certification",
            "description": "Certification program and policy threshold.",
        },
        {
            "entity_type": "RequiredModule",
            "display_name": "Required Module",
            "source_table": "ciq_required_modules",
            "primary_key": "module_id",
            "search_terms": "required module; learning module; LMS",
            "description": "Required training module for readiness.",
        },
        {
            "entity_type": "ModuleCompletion",
            "display_name": "Module Completion",
            "source_table": "ciq_module_completions",
            "primary_key": "learner_id,module_id",
            "search_terms": "module completion; training completion",
            "description": "Learner module completion evidence.",
        },
        {
            "entity_type": "PracticeAssessment",
            "display_name": "Practice Assessment",
            "source_table": "ciq_practice_assessments",
            "primary_key": "assessment_id",
            "search_terms": "assessment; score; practice test",
            "description": "Practice assessment score used in readiness.",
        },
        {
            "entity_type": "RequiredLab",
            "display_name": "Required Lab",
            "source_table": "ciq_required_labs",
            "primary_key": "lab_id",
            "search_terms": "required lab; hands-on lab",
            "description": "Required lab for certification readiness.",
        },
        {
            "entity_type": "LabCompletion",
            "display_name": "Lab Completion",
            "source_table": "ciq_lab_completions",
            "primary_key": "learner_id,lab_id",
            "search_terms": "lab completion; passed lab",
            "description": "Learner lab evidence.",
        },
        {
            "entity_type": "ManagerApproval",
            "display_name": "Manager Approval",
            "source_table": "ciq_manager_approvals",
            "primary_key": "learner_id,certification_id",
            "search_terms": "manager approval; approval status",
            "description": "Manager approval evidence.",
        },
        {
            "entity_type": "ReadinessDefinition",
            "display_name": "Readiness Definition",
            "source_table": "ciq_readiness_definitions",
            "primary_key": "definition_id",
            "search_terms": "readiness definition; certification ready definition",
            "description": "Canonical definition and ownership for Certification Ready.",
        },
        {
            "entity_type": "FalseReadyLearner",
            "display_name": "False Ready Learner",
            "source_table": "ciq_false_ready_learners",
            "primary_key": "learner_id",
            "search_terms": "false ready; blocked learner; readiness risk",
            "description": "Learners claimed ready by one source but blocked by canonical readiness.",
        },
    ]

    return {
        "ciq_ontology_entities": ontology_entities,
        "ciq_certifications": certifications,
        "ciq_readiness_definitions": readiness_definitions,
        "ciq_required_modules": required_modules,
        "ciq_required_labs": required_labs,
        "ciq_learners": learners,
        "ciq_module_completions": module_completions,
        "ciq_lab_completions": lab_completions,
        "ciq_practice_assessments": practice_assessments,
        "ciq_manager_approvals": manager_approvals,
        "ciq_certification_ready": certification_ready,
        "ciq_false_ready_learners": false_ready_learners,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--learners", type=int, default=int(os.environ.get("CIQ_N_LEARNERS", "2000")))
    parser.add_argument("--out", default=os.environ.get("CIQ_SEED_OUTPUT_DIR", "fabric_seed/learning_cli"))
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--remote-dir", default=os.environ.get("CIQ_FABRIC_REMOTE_DIR", "Files/concord_iq_seed/learning"))
    args = parser.parse_args()

    load_dotenv()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    tables = build_seed(args.learners)

    for name, rows in tables.items():
        write_csv(out_dir / f"{name}.csv", rows)

    summary = {
        "canonical_term": "Certification Ready",
        "entity_type": "CertificationReady",
        "learner_count": len(tables["ciq_learners"]),
        "certification_ready_count": sum(1 for row in tables["ciq_certification_ready"] if row["decision"] == "certification_ready"),
        "false_ready_blocked_count": len(tables["ciq_false_ready_learners"]),
        "tables": sorted(tables.keys()),
        "remote_dir": args.remote_dir,
    }

    (out_dir / "ciq_certification_ready_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("Generated seed files:")
    for path in sorted(out_dir.glob("*")):
        print(f"- {path}")

    print("\nSummary:")
    print(json.dumps(summary, indent=2))

    if not args.upload:
        print("\nLocal only. Re-run with --upload to push to OneLake.")
        return

    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "").strip()
    lakehouse_id = os.environ.get("FABRIC_LAKEHOUSE_ID", "").strip()

    if not workspace_id or not lakehouse_id:
        raise SystemExit(
            "Missing FABRIC_WORKSPACE_ID or FABRIC_LAKEHOUSE_ID. Put them in .env or export them."
        )

    token = storage_token()

    for path in sorted(out_dir.glob("*")):
        remote_path = f"{args.remote_dir.rstrip('/')}/{path.name}"
        upload_file(workspace_id, lakehouse_id, path, remote_path, token)
        print(f"Uploaded {path.name} -> {remote_path}")

    print("\nDONE.")
    print(f"Uploaded to OneLake: {args.remote_dir}")
    print("Now map/publish the ontology entity type CertificationReady to ciq_certification_ready.")
    print("Then rerun make fabric-mcp-diagnose.")


if __name__ == "__main__":
    main()
