#!/usr/bin/env python3
"""Focused regressions for confirmed-once downstream delivery policy."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

try:
    import check_state_docs as state_docs
    import projectstate_bootstrap_apply as bootstrap_apply
    from projectstate_generated_controls import (
        DELIVERY_MERGE_REQUIREMENTS,
        agent_merge_policy_refusal,
        confirmed_delivery_policy,
        confirmed_delivery_policy_refusal,
        proposed_delivery_policy,
        render_downstream_workflow,
    )
    from projectstate_validate_schema import load_schema, parse_yaml_text, validate_json_schema
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts import check_state_docs as state_docs
    from scripts import projectstate_bootstrap_apply as bootstrap_apply
    from scripts.projectstate_generated_controls import (
        DELIVERY_MERGE_REQUIREMENTS,
        agent_merge_policy_refusal,
        confirmed_delivery_policy,
        confirmed_delivery_policy_refusal,
        proposed_delivery_policy,
        render_downstream_workflow,
    )
    from scripts.projectstate_validate_schema import load_schema, parse_yaml_text, validate_json_schema


ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = ROOT / "scripts" / "init_template.py"
PROJECT_STATE_SCHEMA = ROOT / "schemas" / "project_state.schema.json"
UPGRADE_SCRIPT = ROOT / "scripts" / "projectstate_upgrade.py"


def run_init(target: Path, profile: str = "team") -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(INIT_SCRIPT),
            "new",
            "--name",
            "Delivery Policy Demo",
            "--profile",
            profile,
            "--target",
            str(target),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"initializer failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


def answers_for(mode: str) -> dict[str, object]:
    return {
        "project_name": "Delivery Policy Demo",
        "purpose": "Prove confirmed-once merge authority.",
        "primary_user": "Human owner and coding agent",
        "architecture": "ProjectState bootstrap plus an exact-head delivery state machine.",
        "constraints": ["No implicit merge authority"],
        "first_milestone": "Confirm delivery policy and establish a truthful baseline.",
        "backlog": [
            {
                "id": "BL-POLICY-001",
                "title": "Confirm delivery policy",
                "priority": "P0",
                "next": "Apply the structured bootstrap answer.",
                "exit": "Canonical state contains the human-confirmed mode.",
            },
            {
                "id": "BL-DELIVERY-001",
                "title": "Exercise delivery closure",
                "priority": "P1",
                "next": "Run a bounded delivery regression.",
                "exit": "The configured merge boundary is enforced.",
            },
            {
                "id": "BL-ACCEPTANCE-001",
                "title": "Keep product acceptance human",
                "priority": "P2",
                "next": "Record acceptance separately from delivery.",
                "exit": "Delivery does not imply product acceptance.",
            },
        ],
        "active_queue": [
            {
                "id": "BL-POLICY-001",
                "priority": "P0",
                "owner": "integration agent",
                "next": "Apply the structured bootstrap answer.",
                "exit": "Canonical state contains the human-confirmed mode.",
            }
        ],
        "delivery_policy": {
            "confirmation": "human_confirmed",
            "merge": {"mode": mode, "method": "squash"},
        },
    }


@pytest.mark.parametrize(
    ("profile", "expected_mode"),
    [
        ("minimal", "human_merge"),
        ("solo", "human_merge"),
        ("team", "agent_after_green"),
        ("regulated", "human_merge"),
    ],
)
def test_generated_profile_policy_is_only_a_non_authorizing_proposal(
    tmp_path: Path,
    profile: str,
    expected_mode: str,
) -> None:
    target = tmp_path / profile
    run_init(target, profile)
    state = parse_yaml_text((target / "PROJECT_STATE.yaml").read_text(encoding="utf-8"))
    policy = state["delivery_policy"]

    assert policy == proposed_delivery_policy(profile)
    assert policy["status"] == "proposed_default"
    assert policy["confirmation"] == "pending_during_bootstrap"
    assert policy["merge"]["mode"] == expected_mode
    assert agent_merge_policy_refusal(policy) == "delivery policy status is not confirmed"
    assert any(
        issue == "Bootstrap gate failed: delivery policy status is not confirmed"
        for issue in state_docs.check_bootstrap_gate(target)
    )


@pytest.mark.parametrize("mode", ["human_merge", "agent_after_green"])
def test_structured_bootstrap_policy_round_trips_through_schema_and_apply(
    tmp_path: Path,
    mode: str,
) -> None:
    target = tmp_path / mode
    run_init(target)
    answers_path = tmp_path / f"{mode}.json"
    answers_path.write_text(json.dumps(answers_for(mode), indent=2) + "\n", encoding="utf-8")

    answers = bootstrap_apply.load_answers(answers_path)
    bootstrap_apply.apply_answers(target, answers)
    state = parse_yaml_text((target / "PROJECT_STATE.yaml").read_text(encoding="utf-8"))
    policy = state["delivery_policy"]

    assert policy["status"] == "confirmed"
    assert policy["confirmation"] == "human_confirmed"
    assert policy["merge"]["mode"] == mode
    assert policy["merge"]["method"] == "squash"
    assert all(policy["merge"][key] is True for key in DELIVERY_MERGE_REQUIREMENTS)
    assert policy["merge"]["delete_branch_after_verification"] is True
    assert confirmed_delivery_policy_refusal(policy) is None
    assert not any(
        "delivery policy" in issue for issue in state_docs.check_bootstrap_gate(target)
    )
    issues = validate_json_schema(state, load_schema(PROJECT_STATE_SCHEMA))
    assert issues == []
    if mode == "agent_after_green":
        assert agent_merge_policy_refusal(policy) is None
    else:
        assert (
            agent_merge_policy_refusal(policy)
            == "delivery policy merge mode is not agent_after_green"
        )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (
            lambda payload: payload["delivery_policy"].update(
                {"confirmation": "pending_during_bootstrap"}
            ),
            "human_confirmed",
        ),
        (
            lambda payload: payload["delivery_policy"]["merge"].pop("mode"),
            "missing required property 'mode'",
        ),
        (
            lambda payload: payload["delivery_policy"]["merge"].update(
                {"mode": "provider_auto_merge"}
            ),
            "human_merge",
        ),
    ],
)
def test_bootstrap_answer_schema_refuses_unconfirmed_missing_or_provider_specific_policy(
    tmp_path: Path,
    mutation: object,
    expected: str,
) -> None:
    payload = answers_for("agent_after_green")
    mutation(payload)
    answers_path = tmp_path / "invalid.json"
    answers_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit, match=expected):
        bootstrap_apply.load_answers(answers_path)


def test_bootstrap_apply_refuses_silent_change_to_confirmed_mode(tmp_path: Path) -> None:
    target = tmp_path / "confirmed"
    run_init(target)
    agent_answers = answers_for("agent_after_green")
    bootstrap_apply.apply_answers(target, agent_answers)
    before = (target / "PROJECT_STATE.yaml").read_bytes()

    with pytest.raises(SystemExit, match="Refusing to silently change"):
        bootstrap_apply.apply_answers(target, answers_for("human_merge"))

    assert (target / "PROJECT_STATE.yaml").read_bytes() == before


def test_agent_merge_policy_refuses_missing_safeguard() -> None:
    policy = confirmed_delivery_policy("agent_after_green")
    unsafe = copy.deepcopy(policy)
    unsafe["merge"]["require_post_merge_main_ci"] = False

    assert agent_merge_policy_refusal(policy) is None
    assert confirmed_delivery_policy_refusal(policy) is None
    assert confirmed_delivery_policy_refusal(confirmed_delivery_policy("human_merge")) is None
    assert (
        agent_merge_policy_refusal(unsafe)
        == "delivery policy safeguard require_post_merge_main_ci is not enabled"
    )
    assert confirmed_delivery_policy_refusal(unsafe) is not None
    assert confirmed_delivery_policy_refusal(proposed_delivery_policy("team")) is not None
    assert agent_merge_policy_refusal(proposed_delivery_policy("team")) is not None
    assert agent_merge_policy_refusal(confirmed_delivery_policy("human_merge")) is not None


def test_generated_workflow_proves_branch_and_merge_candidate_subjects() -> None:
    workflow = render_downstream_workflow(2)
    assert "branch-head:" in workflow
    assert "merge-candidate:" in workflow
    assert "github.event.pull_request.head.sha" in workflow
    assert "EXPECTED_MERGE: ${{ github.sha }}" in workflow
    assert workflow.count("projectstate_quality_gate.py --gate-level 2 --conformance") == 2


def test_upgrade_refreshes_agent_control_without_changing_confirmed_policy(
    tmp_path: Path,
) -> None:
    target = tmp_path / "upgrade"
    run_init(target)
    bootstrap_apply.apply_answers(target, answers_for("human_merge"))
    state_before = (target / "PROJECT_STATE.yaml").read_bytes()

    prompt = target / "prompts" / "CODING_AGENT_STARTUP_PROMPT.md"
    legacy = b"# Legacy generated coding-agent control\n"
    prompt.write_bytes(legacy)
    manifest_path = target / "PROJECTSTATE_ASSETS.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prompt_record = next(
        record
        for record in manifest["managed_assets"]
        if record["path"] == "prompts/CODING_AGENT_STARTUP_PROMPT.md"
    )
    legacy_hash = hashlib.sha256(legacy).hexdigest()
    prompt_record["base_sha256"] = legacy_hash
    prompt_record["installed_sha256"] = legacy_hash
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(UPGRADE_SCRIPT), str(target), "--apply"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"upgrade failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )

    assert (target / "PROJECT_STATE.yaml").read_bytes() == state_before
    upgraded_prompt = prompt.read_text(encoding="utf-8")
    assert "A proposed or" in upgraded_prompt
    assert "pending policy grants no merge authority" in upgraded_prompt
    assert "confirmed `agent_after_green`" in upgraded_prompt
