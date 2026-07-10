#!/usr/bin/env python3
"""Non-destructive downstream upgrade helper for StateDD template assets.

Default mode is dry-run. It compares the downstream repo against the template
root and reports which managed assets are missing, outdated, or conflict with
local changes. It never overwrites project-specific truth files unless the human
explicitly uses --force-managed, and even then it only touches safe template
managed assets.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]

# Assets that are safe to add or replace during an upgrade. These are reusable
# workflow assets, not project-specific truth files.
SAFE_TEMPLATE_ASSETS: list[Path] = [
    Path("VERSION"),
    Path("QUALITY_FIREWALL.md"),
    Path("FAILURE_TAXONOMY.md"),
    Path("INCIDENT_RESPONSE.md"),
    Path("scripts/init_template.py"),
    Path("scripts/check_state_docs.py"),
    Path("scripts/statedd_version_check.py"),
    Path("scripts/test_version_check.py"),
    Path("scripts/statedd_handoff.py"),
    Path("scripts/statedd_audit.py"),
    Path("scripts/statedd_remote_truth_check.py"),
    Path("scripts/statedd_closure_check.py"),
    Path("scripts/statedd_post_merge_verify.py"),
    Path("scripts/statedd_quality_gate.py"),
    Path("scripts/statedd_doctor.py"),
    Path("scripts/statedd_runtime_proof.py"),
    Path("scripts/statedd_runtime_truth_check.py"),
    Path("scripts/statedd_evidence_type_check.py"),
    Path("scripts/statedd_validate_schema.py"),
    Path("scripts/statedd_evidence_pack.py"),
    Path("scripts/test_init_template.py"),
    Path("scripts/test_runtime_proof.py"),
    Path("scripts/test_schema_validation.py"),
    Path("scripts/test_evidence_pack.py"),
    Path("scripts/statedd_remote_closure_finalizer.py"),
    Path("scripts/test_remote_closure_finalizer.py"),
    Path("scripts/test_remote_truth_check.py"),
    Path("scripts/test_closure_check.py"),
    Path("scripts/test_audit_closure.py"),
    Path("scripts/test_handoff.py"),
    Path("scripts/test_quality_gate.py"),
    Path("scripts/test_runtime_evidence_contract.py"),
    Path("scripts/test_post_merge_verify.py"),
    Path("schemas/project_state.schema.json"),
    Path("schemas/project_dna.schema.json"),
    Path("schemas/project_adapter.schema.json"),
    Path("schemas/runtime_identity.schema.json"),
    Path("schemas/evidence_readme_contract.json"),
    Path("schemas/evidence_manifest.schema.json"),
    Path("schemas/final_handoff_contract.json"),
    Path("schemas/examples/runtime_identity_not_required.json"),
    Path("schemas/tests/README.md"),
    Path("prompts/CTO_SESSION_PROMPT.md"),
    Path("prompts/CODING_AGENT_STARTUP_PROMPT.md"),
    Path("prompts/OPENCODE_STARTUP_PROMPT.md"),
    Path("prompts/BOOTSTRAP_INTAKE_PROMPT.md"),
    Path("prompts/TOOL_MODEL_ROUTING_GUIDE.md"),
    Path("prompts/FINAL_HANDOFF_TEMPLATE.md"),
    Path("prompts/RUNTIME_IDENTITY_CHECKLIST.md"),
    Path("prompts/ACCEPTANCE_FREEZE_TEMPLATE.md"),
    Path("prompts/SLICE_CONTRACT_TEMPLATE.md"),
    Path("prompts/EVIDENCE_README_TEMPLATE.md"),
    Path("prompts/SCHEMA_OWNERSHIP_TEMPLATE.md"),
    Path("prompts/SUBAGENT_REVIEW_TEMPLATE.md"),
    Path("prompts/CTO_REVIEW_CHECKLIST.md"),
    Path("docs/GETTING_STARTED_5_MIN.md"),
    Path("docs/BOOTSTRAP_QUALITY.md"),
    Path("docs/failure_scans/TEMPLATE.md"),
    Path("docs/incidents/README.md"),
    Path("docs/quality_gates/README.md"),
    Path("docs/WORKFLOW_FOR_BEGINNERS.md"),
    Path("docs/UPGRADING.md"),
    Path("docs/adr/README.md"),
    Path("docs/adr/0000-adr-template.md"),
]

# Optional GitHub assets that are only upgraded when the downstream repo already
# has a .github directory or when explicitly requested.
GITHUB_ASSET_PATHS: list[Path] = [
    Path(".github/workflows/validate.yml"),
    Path(".github/pull_request_template.md"),
    Path(".github/ISSUE_TEMPLATE/config.yml"),
    Path(".github/ISSUE_TEMPLATE/bootstrap-init.md"),
    Path(".github/ISSUE_TEMPLATE/bug-regression.md"),
    Path(".github/ISSUE_TEMPLATE/backlog-item.md"),
    Path(".github/ISSUE_TEMPLATE/architecture-change.md"),
]

# Files that carry project-specific truth. These are never overwritten by default
# and require explicit human review even with --force-managed.
PROJECT_TRUTH_FILES: set[Path] = {
    Path("AGENTS.md"),
    Path("STATUS.md"),
    Path("PROJECT_STATE.yaml"),
    Path("PROJECT_DNA.yaml"),
    Path("PROJECT_ADAPTER.yaml"),
    Path("NEXT_ACTIONS.md"),
    Path("BACKLOG.md"),
    Path("WORKLOG.md"),
    Path("docs/EVIDENCE_LOG.md"),
    Path("docs/ACCEPTANCE_FREEZES.md"),
    Path("README.md"),
    Path("CHANGELOG.md"),
    Path("LICENSE"),
    Path("LICENSE_FAQ.md"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_version(root: Path) -> str | None:
    path = root / "VERSION"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        return None


def managed_asset_list(target: Path, include_github: bool) -> list[Path]:
    assets = list(SAFE_TEMPLATE_ASSETS)
    if include_github or (target / ".github").exists():
        assets.extend(GITHUB_ASSET_PATHS)
    return assets


def classify_asset(relpath: Path, template_root: Path, target: Path) -> dict[str, Any]:
    template_path = template_root / relpath
    target_path = target / relpath
    is_truth = relpath in PROJECT_TRUTH_FILES

    if not template_path.exists():
        return {"relpath": str(relpath), "status": "skip", "reason": "template source missing"}

    if not target_path.exists():
        return {
            "relpath": str(relpath),
            "status": "missing",
            "is_truth": is_truth,
            "template_hash": sha256_file(template_path),
        }

    template_hash = sha256_file(template_path)
    target_hash = sha256_file(target_path)
    if template_hash == target_hash:
        return {
            "relpath": str(relpath),
            "status": "up_to_date",
            "is_truth": is_truth,
        }

    return {
        "relpath": str(relpath),
        "status": "outdated",
        "is_truth": is_truth,
        "template_hash": template_hash,
        "target_hash": target_hash,
    }


def plan_upgrade(target: Path, assets: list[Path], force_managed: bool) -> dict[str, Any]:
    will_add: list[dict[str, Any]] = []
    will_modify: list[dict[str, Any]] = []
    will_skip: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    manual_actions: list[str] = []

    for relpath in assets:
        info = classify_asset(relpath, TEMPLATE_ROOT, target)
        status = info["status"]
        is_truth = info.get("is_truth", False)

        if status == "missing":
            if is_truth:
                manual_actions.append(
                    f"{info['relpath']} is missing but is a project-truth file; review before adding"
                )
            else:
                will_add.append(info)
        elif status == "up_to_date":
            will_skip.append(info)
        elif status == "outdated":
            if is_truth:
                manual_actions.append(
                    f"{info['relpath']} differs from template but is a project-truth file; merge manually"
                )
            elif force_managed:
                will_modify.append(info)
            else:
                conflicts.append(info)
        else:
            will_skip.append(info)

    return {
        "will_add": will_add,
        "will_modify": will_modify,
        "will_skip": will_skip,
        "conflicts": conflicts,
        "manual_actions": manual_actions,
    }


def print_plan(plan: dict[str, Any], target: Path, template_version: str, target_version: str | None) -> None:
    print("StateDD Upgrade Plan")
    print(f"Target: {target}")
    print(f"Template version: {template_version}")
    print(f"Target version: {target_version or 'not detected'}")
    print()

    if plan["will_add"]:
        print("Will add:")
        for info in plan["will_add"]:
            print(f"  + {info['relpath']}")
    else:
        print("Will add: (none)")

    if plan["will_modify"]:
        print("\nWill modify:")
        for info in plan["will_modify"]:
            print(f"  ~ {info['relpath']}")
    else:
        print("\nWill modify: (none)")

    if plan["will_skip"]:
        print("\nWill skip (up to date or not applicable):")
        for info in plan["will_skip"]:
            print(f"  = {info['relpath']}")
    else:
        print("\nWill skip: (none)")

    if plan["conflicts"]:
        print("\nConflicts (requires --force-managed or manual merge):")
        for info in plan["conflicts"]:
            print(f"  ! {info['relpath']}")
    else:
        print("\nConflicts: (none)")

    if plan["manual_actions"]:
        print("\nManual actions required:")
        for action in plan["manual_actions"]:
            print(f"  * {action}")
    else:
        print("\nManual actions required: (none)")


def execute_plan(plan: dict[str, Any], target: Path) -> None:
    for info in plan["will_add"]:
        relpath = Path(info["relpath"])
        source = TEMPLATE_ROOT / relpath
        destination = target / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        print(f"Added {info['relpath']}")

    for info in plan["will_modify"]:
        relpath = Path(info["relpath"])
        source = TEMPLATE_ROOT / relpath
        destination = target / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        print(f"Modified {info['relpath']}")


def write_report(
    path: Path,
    plan: dict[str, Any],
    target: Path,
    template_version: str,
    target_version: str | None,
    *,
    dry_run: bool,
) -> None:
    report = {
        "schema": "statedd.upgrade_report.v1",
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "template_root": str(TEMPLATE_ROOT),
        "target": str(target),
        "template_version": template_version,
        "target_version": target_version,
        "dry_run": dry_run,
        "summary": {
            "will_add": len(plan["will_add"]),
            "will_modify": len(plan["will_modify"]),
            "will_skip": len(plan["will_skip"]),
            "conflicts": len(plan["conflicts"]),
            "manual_actions": len(plan["manual_actions"]),
        },
        "will_add": [{"relpath": i["relpath"]} for i in plan["will_add"]],
        "will_modify": [{"relpath": i["relpath"]} for i in plan["will_modify"]],
        "will_skip": [{"relpath": i["relpath"]} for i in plan["will_skip"]],
        "conflicts": [{"relpath": i["relpath"]} for i in plan["conflicts"]],
        "manual_actions": plan["manual_actions"],
    }
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote upgrade report: {path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Non-destructive StateDD downstream upgrade helper"
    )
    parser.add_argument("target", nargs="?", default=".", help="Downstream repo root to upgrade")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply safe changes (missing managed assets only by default)",
    )
    parser.add_argument(
        "--force-managed",
        action="store_true",
        help="Also replace outdated safe template-managed assets (never project-truth files)",
    )
    parser.add_argument(
        "--include-github-assets",
        action="store_true",
        help="Include GitHub workflow/template assets in the plan",
    )
    parser.add_argument(
        "--report",
        help="Write a JSON upgrade report to the given path",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    target = Path(args.target).resolve()

    if target == TEMPLATE_ROOT:
        print("Target is the template root itself; upgrade is meant for downstream repos.")
        return 1

    if not target.exists() or not target.is_dir():
        print(f"Target is not a directory: {target}")
        return 1

    template_version = read_version(TEMPLATE_ROOT) or "unknown"
    target_version = read_version(target)
    assets = managed_asset_list(target, args.include_github_assets)
    plan = plan_upgrade(target, assets, args.force_managed)

    print_plan(plan, target, template_version, target_version)

    if args.apply:
        if plan["conflicts"]:
            print("\nRefusing to apply: unresolved conflicts exist. Review or use --force-managed for safe assets.")
            return 1
        execute_plan(plan, target)
        print("\nUpgrade applied.")

    if args.report:
        write_report(
            Path(args.report).resolve(),
            plan,
            target,
            template_version,
            target_version,
            dry_run=not args.apply,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
