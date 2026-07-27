#!/usr/bin/env python3
"""Apply one validated structured bootstrap answer document to a downstream repo."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

try:
    from projectstate_contracts import ContractError, load_json_file
    from projectstate_generated_controls import (
        SUPPORTED_DELIVERY_MERGE_MODES,
        confirmed_delivery_policy,
    )
    from projectstate_validate_schema import load_schema, parse_yaml_text, validate_json_schema
except ModuleNotFoundError:  # pragma: no cover
    from scripts.projectstate_contracts import ContractError, load_json_file
    from scripts.projectstate_generated_controls import (
        SUPPORTED_DELIVERY_MERGE_MODES,
        confirmed_delivery_policy,
    )
    from scripts.projectstate_validate_schema import load_schema, parse_yaml_text, validate_json_schema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "bootstrap_answers.schema.json"


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]+", text):
        return text
    return json.dumps(text, ensure_ascii=False)


def dump_yaml(value: Any, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, child in value.items():
            key_text = str(key)
            if isinstance(child, (dict, list)) and child:
                lines.append(f"{prefix}{key_text}:")
                lines.extend(dump_yaml(child, indent + 2))
            elif isinstance(child, (dict, list)):
                lines.append(f"{prefix}{key_text}: {'{}' if isinstance(child, dict) else '[]'}")
            else:
                lines.append(f"{prefix}{key_text}: {yaml_scalar(child)}")
        return lines
    if isinstance(value, list):
        lines = []
        for child in value:
            if isinstance(child, dict):
                first = True
                for key, nested in child.items():
                    if first:
                        first = False
                        if isinstance(nested, (dict, list)) and nested:
                            lines.append(f"{prefix}- {key}:")
                            lines.extend(dump_yaml(nested, indent + 4))
                        elif isinstance(nested, (dict, list)):
                            lines.append(f"{prefix}- {key}: {'{}' if isinstance(nested, dict) else '[]'}")
                        else:
                            lines.append(f"{prefix}- {key}: {yaml_scalar(nested)}")
                    elif isinstance(nested, (dict, list)) and nested:
                        lines.append(f"{' ' * (indent + 2)}{key}:")
                        lines.extend(dump_yaml(nested, indent + 4))
                    elif isinstance(nested, (dict, list)):
                        lines.append(f"{' ' * (indent + 2)}{key}: {'{}' if isinstance(nested, dict) else '[]'}")
                    else:
                        lines.append(f"{' ' * (indent + 2)}{key}: {yaml_scalar(nested)}")
            else:
                lines.append(f"{prefix}- {yaml_scalar(child)}")
        return lines
    return [f"{prefix}{yaml_scalar(value)}"]


def load_answers(path: Path) -> dict[str, Any]:
    try:
        payload = load_json_file(path)
        schema = load_schema(SCHEMA)
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid bootstrap answers: {exc}") from exc
    issues = validate_json_schema(payload, schema)
    if issues:
        detail = "; ".join(f"{issue.path}: {issue.message}" for issue in issues[:8])
        raise SystemExit(f"Bootstrap answers violate schema: {detail}")
    return payload


def apply_answers(root: Path, answers: dict[str, Any]) -> None:
    state_path = root / "PROJECT_STATE.yaml"
    try:
        state = parse_yaml_text(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise SystemExit(f"Cannot read PROJECT_STATE.yaml: {exc}") from exc
    if not isinstance(state, dict):
        raise SystemExit("PROJECT_STATE.yaml must contain a mapping")

    answer_policy = answers["delivery_policy"]
    answer_merge = answer_policy["merge"]
    requested_mode = answer_merge["mode"]
    requested_method = answer_merge["method"]
    existing_policy = state.get("delivery_policy", {})
    if not isinstance(existing_policy, dict):
        raise SystemExit("PROJECT_STATE.yaml delivery_policy must contain a mapping")
    existing_status = existing_policy.get("status")
    existing_confirmation = existing_policy.get("confirmation")
    existing_confirmed = (
        existing_status == "confirmed" or existing_confirmation == "human_confirmed"
    )
    if existing_confirmed:
        if existing_status != "confirmed" or existing_confirmation != "human_confirmed":
            raise SystemExit(
                "Existing delivery policy has inconsistent confirmed status; repair it explicitly"
            )
        existing_merge = existing_policy.get("merge")
        if not isinstance(existing_merge, dict):
            raise SystemExit("Existing confirmed delivery policy has no valid merge mapping")
        existing_mode = existing_merge.get("mode")
        existing_method = existing_merge.get("method")
        if existing_mode not in SUPPORTED_DELIVERY_MERGE_MODES or existing_method != "squash":
            raise SystemExit("Existing confirmed delivery policy has unsupported merge settings")
        if existing_mode != requested_mode or existing_method != requested_method:
            raise SystemExit(
                "Refusing to silently change the confirmed delivery policy merge mode or method"
            )

    workflow = state.setdefault("workflow", {})
    bootstrap = workflow.setdefault("bootstrap", {})
    bootstrap.update({
        "completed": False,
        "system_investigated": True,
        "repo_investigated": True,
        "user_intake_complete": True,
        "unknowns_remaining": [],
    })
    state["delivery_policy"] = confirmed_delivery_policy(
        requested_mode,
        method=requested_method,
    )
    current = state.setdefault("current_state", {})
    project = current.setdefault("project", {})
    project.update({
        "name": answers["project_name"],
        "purpose": answers["purpose"],
        "primary_user": answers["primary_user"],
        "architecture": answers["architecture"],
        "constraints": answers["constraints"],
        "first_milestone": answers["first_milestone"],
    })
    current["bootstrap_truth"] = {
        "source": "structured bootstrap answers",
        "status": "complete",
        "captured_on": date.today().isoformat(),
    }
    state_path.write_text("# PROJECT_STATE.yaml - Structured current truth\n\n" + "\n".join(dump_yaml(state)) + "\n", encoding="utf-8")

    backlog_lines = [
        "# BACKLOG - Strategic Roadmap",
        "",
        f"**Product:** {answers['project_name']}",
        "**Execution Mode:** bootstrap",
        f"**Updated At:** {date.today().isoformat()}",
        "",
        "## Purpose",
        "",
        "This backlog was created from the validated structured bootstrap answer document.",
        "Reference these IDs from `NEXT_ACTIONS.md`.",
        "",
        "## NOW",
        "",
    ]
    for item in answers["backlog"]:
        backlog_lines.append(f"- [{item['id']}] {item['title']}")
    backlog_lines.extend(["", "## NEXT", "", "- [BL-BOOTSTRAP-CONTINUITY] Keep the bootstrap baseline truthful and transition only after review.", "", "## CLOSED", "", "## WATCHLIST", "", "- Unverified claims.", "- Premature operating-mode transition.", ""])
    (root / "BACKLOG.md").write_text("\n".join(backlog_lines), encoding="utf-8")

    queue_lines = ["# NEXT_ACTIONS - Active Execution Queue", "", f"**Updated At:** {date.today().isoformat()}", "**Execution Mode:** bootstrap", "**Max Items:** 10", "", "## Active Work", ""]
    for item in answers["active_queue"]:
        queue_lines.extend([
            f"### {item['priority']} [{item['id']}] Bootstrap work",
            f"Owner: {item['owner']}",
            f"Next: {item['next']}",
            f"Exit: {item['exit']}",
            "",
        ])
    queue_lines.extend(["## Queue Rules", "", "- Keep this file short.", "- List only active, open work.", "- Remove completed items immediately.", "- Every active item must reference a backlog ID.", "- Include owner, next action, and exit criteria when items exist.", ""])
    (root / "NEXT_ACTIONS.md").write_text("\n".join(queue_lines), encoding="utf-8")

    with (root / "WORKLOG.md").open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {date.today().isoformat()} - Structured bootstrap baseline\n\n**Type:** bootstrap_baseline\n**Status:** COMPLETE\n\n- Purpose, primary user, architecture, constraints, first milestone, backlog, active queue, and confirmed `{requested_mode}` delivery policy were applied from the validated answer document.\n")
    with (root / "docs" / "EVIDENCE_LOG.md").open("a", encoding="utf-8") as handle:
        handle.write(f"\n## EV-{date.today().isoformat()}-003: Structured bootstrap baseline\n\n- Source: validated structured bootstrap answer document.\n- Result: canonical project truth, backlog, queue, and confirmed `{requested_mode}` delivery policy populated.\n")


def apply_integration_result(root: Path, result: dict[str, Any]) -> None:
    required = {"status", "commit_count", "working_tree_clean", "agent_scope_respected", "conflicts_resolved"}
    if set(result) != required:
        raise SystemExit(f"Integration result fields must be exactly {sorted(required)}")
    if result["status"] != "complete" or result["working_tree_clean"] is not True or result["agent_scope_respected"] is not True:
        raise SystemExit("Integration result is not complete and clean")
    state_path = root / "PROJECT_STATE.yaml"
    state = parse_yaml_text(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise SystemExit("PROJECT_STATE.yaml must contain a mapping")
    current = state.setdefault("current_state", {})
    current["integration_result"] = {
        "status": result["status"],
        "commit_count": result["commit_count"],
        "working_tree_clean": result["working_tree_clean"],
        "agent_scope_respected": result["agent_scope_respected"],
        "conflicts_resolved": result["conflicts_resolved"],
        "updated_by": "integration agent",
    }
    state_path.write_text("# PROJECT_STATE.yaml - Structured current truth\n\n" + "\n".join(dump_yaml(state)) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--answers")
    parser.add_argument("--integration-result")
    args = parser.parse_args(argv)
    root = Path(args.repo).resolve()
    if not args.answers and not args.integration_result:
        raise SystemExit("one of --answers or --integration-result is required")
    if args.answers:
        apply_answers(root, load_answers(Path(args.answers).resolve()))
        print(f"Applied structured bootstrap baseline to {root}")
    if args.integration_result:
        result = load_json_file(Path(args.integration_result).resolve())
        if not isinstance(result, dict):
            raise SystemExit("Integration result must contain a JSON object")
        apply_integration_result(root, result)
        print(f"Applied structured integration result to {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
