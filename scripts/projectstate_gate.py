#!/usr/bin/env python3
"""Validate the outcome-first ProjectState core without executing repo text.

The parser intentionally supports the conservative YAML subset used by
``STATE.yaml`` so a generated project needs only Python's standard library.
Exit 0 means recorded evidence supports validation and no recorded stop-line
blocks it. This does not execute journeys or authenticate human approval.
Exit 1 means the state is honest but not closure-ready. Exit 2 means it is invalid.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


VERSION = "projectstate-template-v6"
TOP_LEVEL_KEYS = {
    "version",
    "profile",
    "project",
    "current_slice",
    "validation",
    "delivery_boundary",
    "blockers",
    "risks",
    "next_action",
}
CLOSURE_STATUSES = {"validated", "ready_for_human", "accepted"}
PRIMARY_STATUSES = {"not_run", "passed", "failed", "blocked"}
AUTOMATED_STATUSES = {"not_run", "passed", "failed", "not_applicable"}
HUMAN_STATUSES = {"pending", "accepted", "rejected"}
SLICE_STATUSES = {
    "planned",
    "implementing",
    "implemented",
    "validated",
    "blocked",
    "ready_for_human",
    "accepted",
}
MANDATORY_STOP_CATEGORIES = {
    "data_loss",
    "data_corruption",
    "destructive_operation",
    "privilege_escalation",
    "secrets_exposure",
    "private_data_exposure",
    "permission_boundary",
}
EXPOSED = {"reachable", "unknown"}
EXPOSURES = {
    "reachable",
    "unreachable",
    "build_only",
    "development_only",
    "test_only",
    "local_only",
    "opt_in_only",
    "unknown",
}


class StateSyntaxError(ValueError):
    """Raised when STATE.yaml is outside the supported YAML subset."""


def _strip_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
            continue
        if char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def _scalar(raw: str) -> Any:
    value = _strip_comment(raw.strip())
    if value in {"[]", "[ ]"}:
        return []
    if value in {"{}", "{ }"}:
        return {}
    if value.lower() == "null":
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise StateSyntaxError(f"invalid quoted string: {exc}") from exc
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _lines(text: str) -> list[tuple[int, str, int]]:
    result: list[tuple[int, str, int]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if "\t" in raw[:len(raw) - len(raw.lstrip())] or indent % 2:
            raise StateSyntaxError(f"line {number}: use two-space indentation and no tabs")
        result.append((indent, raw[indent:].rstrip(), number))
    return result


def _split(content: str, number: int) -> tuple[str, str]:
    if ":" not in content:
        raise StateSyntaxError(f"line {number}: expected key: value")
    key, value = content.split(":", 1)
    key = key.strip()
    if not key or not re.fullmatch(r"[A-Za-z0-9_.-]+", key):
        raise StateSyntaxError(f"line {number}: invalid mapping key")
    return key, value.strip()


def _block_scalar(
    lines: list[tuple[int, str, int]], index: int, minimum: int, folded: bool
) -> tuple[str, int]:
    parts: list[str] = []
    baseline: int | None = None
    while index < len(lines):
        indent, content, _ = lines[index]
        if indent < minimum:
            break
        baseline = indent if baseline is None else baseline
        if indent < baseline:
            break
        parts.append(" " * (indent - baseline) + content)
        index += 1
    return ((" " if folded else "\n").join(parts), index)


def _parse_block(
    lines: list[tuple[int, str, int]], index: int, indent: int
) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    return (
        _parse_sequence(lines, index, indent)
        if lines[index][1].startswith("- ")
        else _parse_mapping(lines, index, indent)
    )


def _parse_mapping(
    lines: list[tuple[int, str, int]], index: int, indent: int
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        current, content, number = lines[index]
        if current < indent or current != indent or content.startswith("- "):
            break
        key, raw = _split(content, number)
        if key in result:
            raise StateSyntaxError(f"line {number}: duplicate key {key!r}")
        index += 1
        if raw in {"|", ">"}:
            result[key], index = _block_scalar(lines, index, indent + 2, raw == ">")
        elif raw:
            result[key] = _scalar(raw)
        elif index < len(lines) and lines[index][0] > indent:
            result[key], index = _parse_block(lines, index, lines[index][0])
        else:
            result[key] = {}
    return result, index


def _parse_sequence(
    lines: list[tuple[int, str, int]], index: int, indent: int
) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        current, content, number = lines[index]
        if current != indent or not content.startswith("- "):
            break
        raw = content[2:].strip()
        index += 1
        if not raw:
            if index < len(lines) and lines[index][0] > indent:
                item, index = _parse_block(lines, index, lines[index][0])
            else:
                item = None
            result.append(item)
            continue
        if re.match(r"^[A-Za-z0-9_.-]+:\s*", raw):
            key, value = _split(raw, number)
            item_map: dict[str, Any] = {key: _scalar(value) if value else {}}
            if index < len(lines) and lines[index][0] > indent:
                extra, index = _parse_mapping(lines, index, lines[index][0])
                duplicate = set(item_map) & set(extra)
                if duplicate:
                    raise StateSyntaxError(f"line {number}: duplicate key {sorted(duplicate)[0]!r}")
                item_map.update(extra)
            result.append(item_map)
        else:
            result.append(_scalar(raw))
    return result, index


def parse_state(text: str) -> dict[str, Any]:
    lines = _lines(text)
    if not lines:
        raise StateSyntaxError("STATE.yaml is empty")
    payload, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines) or not isinstance(payload, dict):
        number = lines[index][2] if index < len(lines) else 1
        raise StateSyntaxError(f"line {number}: unexpected content")
    return payload


def _mapping(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path} must be a mapping")
        return {}
    return value


def _exact_keys(
    value: dict[str, Any], required: set[str], path: str, errors: list[str], optional: set[str] | None = None
) -> None:
    optional = optional or set()
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        errors.append(f"{path} is missing {sorted(missing)}")
    if unknown:
        errors.append(f"{path} contains unsupported fields {sorted(unknown)}")


def _text(value: Any, path: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be non-empty text")
        return ""
    return value.strip()


def _list(value: Any, path: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{path} must be a list")
        return []
    return value


def _defined_text(value: Any, path: str, errors: list[str], blockers: list[str]) -> str:
    text = _text(value, path, errors)
    visible = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()
    if text and (not visible or re.search(
        r"^[ \t]*[-*>` \t]*(?:not yet defined\b|(?:TODO|TBD)(?:[ \t]*$|[ \t]*[:—-]))",
        visible, re.IGNORECASE | re.MULTILINE
    )):
        blockers.append(f"{path} is unresolved; replace placeholders with the human-owned contract and observed journey")
    return text


def _is_choice(value: Any, choices: set[str]) -> bool:
    return isinstance(value, str) and value in choices


def _markdown_sections(text: str, path: str, errors: list[str]) -> dict[str, str]:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    headings = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    result: dict[str, str] = {}
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        heading = match.group(1).strip().lower()
        if heading in result:
            errors.append(f"{path} has duplicate ## {heading} sections")
        result[heading] = text[match.end() : end].strip()
    return result


def _summary_value(text: str, label: str) -> str | None:
    matches = re.findall(rf"^-\s+{re.escape(label)}:[ \t]*(.*?)[ \t]*$", text, re.MULTILINE | re.IGNORECASE)
    if len(matches) != 1:
        return None
    return matches[0].strip().strip("`")


def _local_file(root: Path, relative: PurePosixPath, errors: list[str]) -> Path | None:
    """Refuse symlinks before reading any contract or evidence content."""
    current = root
    try:
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                errors.append(f"{relative} is symlinked")
                return None
        if not current.is_file():
            errors.append(f"{relative} is missing or not a regular file")
            return None
    except (OSError, ValueError) as exc:
        errors.append(f"cannot inspect {relative}: {exc}")
        return None
    return current


def _evidence_path(root: Path, raw: Any, slice_id: str, errors: list[str]) -> Path | None:
    value = _text(raw, "current_slice.primary_journey.evidence", errors)
    if not value:
        return None
    relative = PurePosixPath(value)
    expected = PurePosixPath("evidence") / slice_id / "summary.md"
    if relative.is_absolute() or ".." in relative.parts or relative != expected:
        errors.append(f"primary journey evidence must be {expected.as_posix()}")
        return None
    return _local_file(root, relative, errors)


def _attempt_evidence_path(
    root: Path, raw: Any, slice_id: str, index: int, errors: list[str]
) -> None:
    label = f"delivery_boundary.failed_attempts[{index}].evidence"
    value = _text(raw, label, errors)
    if not value:
        return
    relative = PurePosixPath(value)
    expected_parent = PurePosixPath("evidence") / slice_id
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.parent != expected_parent
        or relative.name == "summary.md"
    ):
        errors.append(f"{label} must name a supporting file directly under {expected_parent}")
        return
    _local_file(root, relative, errors)


def _validate_failures(
    root: Path,
    slice_id: str,
    delivery: dict[str, Any],
    errors: list[str],
    blockers: list[str],
) -> None:
    _exact_keys(delivery, {"name", "failed_attempts", "simplification_review"}, "delivery_boundary", errors)
    _text(delivery.get("name"), "delivery_boundary.name", errors)
    attempts = _list(delivery.get("failed_attempts"), "delivery_boundary.failed_attempts", errors)
    for index, item in enumerate(attempts):
        attempt = _mapping(item, f"delivery_boundary.failed_attempts[{index}]", errors)
        _exact_keys(attempt, {"evidence", "cause"}, f"delivery_boundary.failed_attempts[{index}]", errors)
        _attempt_evidence_path(root, attempt.get("evidence"), slice_id, index, errors)
        _text(attempt.get("cause"), f"failed_attempts[{index}].cause", errors)
    review = delivery.get("simplification_review")
    if len(attempts) >= 2:
        if review is None:
            blockers.append("two failures at this delivery boundary require simplification before more work")
        else:
            review_map = _mapping(review, "delivery_boundary.simplification_review", errors)
            required = {"assumption_reconsidered", "complexity_removed", "smallest_rerun"}
            _exact_keys(review_map, required, "delivery_boundary.simplification_review", errors)
            for key in required:
                _text(review_map.get(key), f"simplification_review.{key}", errors)
    elif review is not None and not isinstance(review, dict):
        errors.append("delivery_boundary.simplification_review must be null or a mapping")


def _temporary_acceptance_is_valid(risk: dict[str, Any], errors: list[str], index: int) -> bool:
    approval = risk.get("approval")
    rationale = risk.get("rationale")
    expires = risk.get("expires")
    if not all(isinstance(value, str) and value.strip() for value in (approval, rationale, expires)):
        errors.append(f"risks[{index}] temporary acceptance needs approval, rationale, and expiry")
        return False
    try:
        expiry = dt.date.fromisoformat(str(expires))
    except ValueError:
        errors.append(f"risks[{index}].expires must be an ISO date")
        return False
    if expiry < dt.date.today():
        errors.append(f"risks[{index}] temporary acceptance expired on {expiry.isoformat()}")
        return False
    return True


def _validate_risks(raw_risks: Any, errors: list[str], blockers: list[str], warnings: list[str]) -> None:
    risks = _list(raw_risks, "risks", errors)
    seen: set[str] = set()
    required = {
        "id",
        "category",
        "severity",
        "exposure",
        "affected_environment",
        "consequence",
        "owner",
        "decision",
        "expires",
    }
    for index, item in enumerate(risks):
        risk = _mapping(item, f"risks[{index}]", errors)
        _exact_keys(risk, required, f"risks[{index}]", errors, {"approval", "rationale"})
        risk_id = _text(risk.get("id"), f"risks[{index}].id", errors)
        category = _text(risk.get("category"), f"risks[{index}].category", errors)
        severity = _text(risk.get("severity"), f"risks[{index}].severity", errors)
        exposure = _text(risk.get("exposure"), f"risks[{index}].exposure", errors)
        _text(risk.get("affected_environment"), f"risks[{index}].affected_environment", errors)
        _text(risk.get("consequence"), f"risks[{index}].consequence", errors)
        _text(risk.get("owner"), f"risks[{index}].owner", errors)
        decision = _text(risk.get("decision"), f"risks[{index}].decision", errors)
        if risk_id in seen:
            errors.append(f"duplicate risk id {risk_id!r}")
        seen.add(risk_id)
        if severity not in {"critical", "high", "medium", "low"}:
            errors.append(f"risks[{index}].severity is invalid")
        if exposure not in EXPOSURES:
            errors.append(f"risks[{index}].exposure is invalid")
        if decision not in {"mitigate", "resolved", "defer", "accept_temporarily"}:
            errors.append(f"risks[{index}].decision is invalid")
        accepted = decision == "accept_temporarily" and _temporary_acceptance_is_valid(risk, errors, index)
        mandatory = category in MANDATORY_STOP_CATEGORIES
        exposed_risk = severity in {
            "critical",
            "high",
        } and exposure in EXPOSED
        if (mandatory or exposed_risk) and decision != "resolved" and not accepted:
            blockers.append(f"risk {risk_id!r} crosses a mandatory stop-line")
        elif decision != "resolved":
            warnings.append(
                f"risk {risk_id!r} remains {decision} ({severity}, exposure={exposure}); it does not override the journey"
            )


def validate(root: Path) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    state_path = _local_file(root, PurePosixPath("STATE.yaml"), errors)
    if state_path is None:
        return errors, blockers, warnings
    try:
        payload = parse_state(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, StateSyntaxError) as exc:
        return [f"cannot read STATE.yaml: {exc}"], [], []

    _exact_keys(payload, TOP_LEVEL_KEYS, "STATE.yaml", errors)
    if payload.get("version") != VERSION:
        errors.append(f"STATE.yaml version must be {VERSION!r}")
    if not _is_choice(payload.get("profile"), {"core", "hardened"}):
        errors.append("STATE.yaml profile must be core or hardened")

    project = _mapping(payload.get("project"), "project", errors)
    _exact_keys(project, {"outcome_ref"}, "project", errors)
    if project.get("outcome_ref") != "PROJECT.md#outcome":
        errors.append("project.outcome_ref must be PROJECT.md#outcome")
    project_path = _local_file(root, PurePosixPath("PROJECT.md"), errors)
    try:
        project_text = project_path.read_text(encoding="utf-8") if project_path else ""
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"cannot read PROJECT.md: {exc}")
        project_text = ""
    sections = _markdown_sections(project_text, "PROJECT.md", errors)
    for heading in ("user", "outcome", "scope", "non-goals", "durable constraints"):
        body = sections.get(heading, "")
        if not body:
            errors.append(f"PROJECT.md needs a non-empty ## {heading.title()} section")
        else:
            _defined_text(body, f"PROJECT.md ## {heading.title()}", errors, blockers)

    slice_state = _mapping(payload.get("current_slice"), "current_slice", errors)
    _exact_keys(
        slice_state,
        {"id", "objective", "status", "acceptance", "primary_journey"},
        "current_slice",
        errors,
    )
    slice_id = _text(slice_state.get("id"), "current_slice.id", errors)
    if slice_id and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slice_id):
        errors.append("current_slice.id must use lowercase letters, digits, and hyphens")
    _defined_text(slice_state.get("objective"), "current_slice.objective", errors, blockers)
    status = slice_state.get("status")
    if not _is_choice(status, SLICE_STATUSES):
        errors.append(f"current_slice.status must be one of {sorted(SLICE_STATUSES)}")
    if status == "blocked":
        blockers.append("current slice is explicitly blocked")
    acceptance = _list(slice_state.get("acceptance"), "current_slice.acceptance", errors)
    if not acceptance:
        errors.append("current_slice.acceptance must contain observable criteria")
    for index, criterion in enumerate(acceptance):
        _defined_text(criterion, f"current_slice.acceptance[{index}]", errors, blockers)

    journey = _mapping(slice_state.get("primary_journey"), "current_slice.primary_journey", errors)
    _exact_keys(
        journey,
        {"description", "command", "environment", "status", "evidence"},
        "current_slice.primary_journey",
        errors,
    )
    _defined_text(journey.get("description"), "current_slice.primary_journey.description", errors, blockers)
    command = _defined_text(journey.get("command"), "current_slice.primary_journey.command", errors, blockers)
    environment = _defined_text(journey.get("environment"), "current_slice.primary_journey.environment", errors, blockers)
    journey_status = journey.get("status")
    if not _is_choice(journey_status, PRIMARY_STATUSES):
        errors.append(f"primary journey status must be one of {sorted(PRIMARY_STATUSES)}")
    evidence_path = _evidence_path(root, journey.get("evidence"), slice_id, errors)

    validation = _mapping(payload.get("validation"), "validation", errors)
    _exact_keys(validation, {"primary_journey", "automated_tests", "human_acceptance"}, "validation", errors)
    if not _is_choice(validation.get("primary_journey"), PRIMARY_STATUSES):
        errors.append("validation.primary_journey is invalid")
    if validation.get("primary_journey") != journey_status:
        errors.append("validation.primary_journey must match current_slice.primary_journey.status")
    automated = validation.get("automated_tests")
    if not _is_choice(automated, AUTOMATED_STATUSES):
        errors.append("validation.automated_tests is invalid")
    if automated == "failed":
        blockers.append("automated tests are explicitly failed")
    human = validation.get("human_acceptance")
    if not _is_choice(human, HUMAN_STATUSES):
        errors.append("validation.human_acceptance is invalid")
    if human == "rejected":
        blockers.append("human product acceptance is rejected")
    if human == "accepted" and status != "accepted":
        errors.append("human acceptance requires current_slice.status: accepted")
    if status == "accepted" and human != "accepted":
        errors.append("current_slice.status: accepted requires explicit human acceptance")

    if journey_status != "passed":
        blockers.insert(0, f"primary journey is {journey_status}; secondary checks cannot override it")
    if _is_choice(status, CLOSURE_STATUSES) and journey_status != "passed":
        errors.append(f"current_slice.status {status!r} requires a passed primary journey")
    raw_blockers = _list(payload.get("blockers"), "blockers", errors)
    for index, blocker in enumerate(raw_blockers):
        text = _text(blocker, f"blockers[{index}]", errors)
        if text:
            blockers.append(text)
    _validate_failures(
        root,
        slice_id,
        _mapping(payload.get("delivery_boundary"), "delivery_boundary", errors),
        errors,
        blockers,
    )
    _validate_risks(payload.get("risks"), errors, blockers, warnings)
    _text(payload.get("next_action"), "next_action", errors)

    _local_file(root, PurePosixPath("AGENTS.md"), errors)

    if payload.get("profile") == "hardened":
        _local_file(root, PurePosixPath("HARDENED_POLICY.md"), errors)

    if evidence_path is not None:
        try:
            summary = evidence_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"cannot read evidence summary: {exc}")
            summary = ""
        evidence_sections = _markdown_sections(summary, "evidence summary", errors)
        for heading in ("Primary journey", "Secondary checks", "Artifacts", "Limitations"):
            if heading.lower() not in evidence_sections:
                errors.append(f"evidence summary needs ## {heading}")
        primary_evidence = evidence_sections.get("primary journey", "")
        if journey_status == "passed":
            if (_summary_value(primary_evidence, "Result") or "").lower() != "passed":
                errors.append("passed primary journey needs evidence Result: passed")
            if _summary_value(primary_evidence, "Exit code") != "0":
                errors.append("passed primary journey needs evidence Exit code: 0")
            recorded_command = _summary_value(primary_evidence, "Command")
            if recorded_command != command:
                errors.append("evidence Command must match STATE.yaml primary journey command")
            recorded_environment = _summary_value(primary_evidence, "Environment")
            if recorded_environment != environment:
                errors.append("evidence Environment must match STATE.yaml primary journey environment")

    return errors, blockers, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate outcome-first ProjectState truth")
    parser.add_argument("--root", default=".", help="Repository root")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    errors, blockers, warnings = validate(root)
    for warning in warnings:
        print(f"WARN: {warning}")
    if errors:
        print("INVALID PROJECTSTATE CORE")
        for error in errors:
            print(f"- {error}")
        if blockers:
            print("Outcome blockers:")
            for blocker in blockers:
                print(f"- {blocker}")
        return 2
    if blockers:
        print("OUTCOME NOT VALIDATED")
        for blocker in blockers:
            print(f"- {blocker}")
        return 1
    print("RECORDED OUTCOME VALIDATED")
    print("- primary journey: recorded as passed")
    print("- secondary checks: do not override the primary journey")
    print("- this gate does not execute journeys or authenticate human approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
