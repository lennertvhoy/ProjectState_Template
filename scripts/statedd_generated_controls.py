#!/usr/bin/env python3
"""Deterministic generated controls shared by initialization and upgrades."""

from __future__ import annotations


SUPPORTED_DELIVERY_MERGE_MODES = frozenset({"human_merge", "agent_after_green"})
DELIVERY_MERGE_REQUIREMENTS = (
    "require_exact_pr_head",
    "require_clean_merge_state",
    "require_no_requested_changes",
    "require_no_unresolved_review_threads",
    "require_branch_head_ci",
    "require_merge_candidate_ci",
    "require_remote_closure",
    "require_post_merge_main_ci",
)


def recommended_merge_mode(profile: str) -> str:
    """Return the safe proposal for a known downstream profile.

    A recommendation is deliberately not authorization. Generated state keeps
    the policy pending until structured bootstrap records human confirmation.
    """

    if profile not in {"minimal", "solo", "team", "regulated"}:
        raise ValueError(f"unknown StateDD profile: {profile!r}")
    return "agent_after_green" if profile == "team" else "human_merge"


def _merge_policy(mode: str, *, method: str = "squash") -> dict[str, object]:
    if mode not in SUPPORTED_DELIVERY_MERGE_MODES:
        raise ValueError(f"unsupported delivery merge mode: {mode!r}")
    if method != "squash":
        raise ValueError(f"unsupported delivery merge method: {method!r}")
    return {
        "mode": mode,
        "method": method,
        "delete_branch_after_verification": True,
        **{requirement: True for requirement in DELIVERY_MERGE_REQUIREMENTS},
    }


def proposed_delivery_policy(profile: str) -> dict[str, object]:
    """Build the non-authorizing policy proposal installed during generation."""

    return {
        "status": "proposed_default",
        "confirmation": "pending_during_bootstrap",
        "merge": _merge_policy(recommended_merge_mode(profile)),
        "protected_operations": {
            "force_push": "forbidden",
            "rewrite_shared_history": "forbidden",
        },
        "ci_unavailable": {
            "automatic_merge": "forbidden",
            "override": "requires_separate_explicit_human_authorization",
        },
    }


def confirmed_delivery_policy(mode: str, *, method: str = "squash") -> dict[str, object]:
    """Build the complete confirmed-once delivery policy."""

    return {
        "status": "confirmed",
        "confirmation": "human_confirmed",
        "merge": _merge_policy(mode, method=method),
        "protected_operations": {
            "force_push": "forbidden",
            "rewrite_shared_history": "forbidden",
        },
        "ci_unavailable": {
            "automatic_merge": "forbidden",
            "override": "requires_separate_explicit_human_authorization",
        },
    }


def confirmed_delivery_policy_refusal(policy: object) -> str | None:
    """Return why a policy is not a complete confirmed bootstrap decision."""

    if not isinstance(policy, dict):
        return "delivery policy is missing or malformed"
    if policy.get("status") != "confirmed":
        return "delivery policy status is not confirmed"
    if policy.get("confirmation") != "human_confirmed":
        return "delivery policy lacks explicit human confirmation"
    merge = policy.get("merge")
    if not isinstance(merge, dict):
        return "delivery policy merge settings are missing or malformed"
    if merge.get("mode") not in SUPPORTED_DELIVERY_MERGE_MODES:
        return "delivery policy merge mode is unsupported"
    if merge.get("method") != "squash":
        return "delivery policy merge method is not supported"
    if merge.get("delete_branch_after_verification") is not True:
        return "delivery policy does not defer branch deletion until verification"
    for requirement in DELIVERY_MERGE_REQUIREMENTS:
        if merge.get(requirement) is not True:
            return f"delivery policy safeguard {requirement} is not enabled"
    protected = policy.get("protected_operations")
    if not isinstance(protected, dict):
        return "delivery policy protected operations are missing or malformed"
    if protected.get("force_push") != "forbidden":
        return "delivery policy does not forbid force-push"
    if protected.get("rewrite_shared_history") != "forbidden":
        return "delivery policy does not forbid shared-history rewrite"
    ci_unavailable = policy.get("ci_unavailable")
    if not isinstance(ci_unavailable, dict):
        return "delivery policy CI-unavailable behavior is missing or malformed"
    if ci_unavailable.get("automatic_merge") != "forbidden":
        return "delivery policy does not forbid automatic merge without CI"
    if ci_unavailable.get("override") != "requires_separate_explicit_human_authorization":
        return "delivery policy does not require an explicit CI-unavailable override"
    return None


def agent_merge_policy_refusal(policy: object) -> str | None:
    """Return why policy forbids agent merge, or ``None`` when it permits it.

    This checks policy authority only. The finish path must still prove the PR,
    review, exact-head, CI, evidence, and post-merge conditions at runtime.
    """

    refusal = confirmed_delivery_policy_refusal(policy)
    if refusal is not None:
        return refusal
    assert isinstance(policy, dict)  # narrowed by confirmed_delivery_policy_refusal
    merge = policy["merge"]
    assert isinstance(merge, dict)
    if merge.get("mode") != "agent_after_green":
        return "delivery policy merge mode is not agent_after_green"
    return None


def render_proposed_delivery_policy(profile: str) -> str:
    """Render deterministic YAML for generated PROJECT_STATE.yaml."""

    mode = recommended_merge_mode(profile)
    requirements = "\n".join(
        f"    {requirement}: true" for requirement in DELIVERY_MERGE_REQUIREMENTS
    )
    return f"""delivery_policy:
  status: proposed_default
  confirmation: pending_during_bootstrap
  merge:
    mode: {mode}
    method: squash
    delete_branch_after_verification: true
{requirements}
  protected_operations:
    force_push: forbidden
    rewrite_shared_history: forbidden
  ci_unavailable:
    automatic_merge: forbidden
    override: requires_separate_explicit_human_authorization
"""


def render_coding_agent_startup_prompt() -> str:
    return """# Coding Agent Start

Read `AGENTS.md` and its declared read order. Treat `PROJECT_STATE.yaml` as
canonical current truth, keep `NEXT_ACTIONS.md` open-only, and load backlog,
history, inventory, or evidence only when the task needs them.

In bootstrap, investigate before implementing and keep unknowns explicit. For
implementation, take one coherent slice, verify the relevant truth boundary,
update live state, and end with a precise handoff. Before repository or StateDD
mutation, run `scripts/statedd_git_safety_check.py` and use a full clone for
containers or independent agents. The integration agent owns the final slice
branch; subagents return bounded commits and do not edit global StateDD truth.

Read the confirmed `delivery_policy` before remote closure. A proposed or
pending policy grants no merge authority. With `human_merge`, stop before merge
and return exact remote truth. With confirmed `agent_after_green`, the coding
agent owns exact-head squash merge, direct-main CI verification, the external
post-merge handoff, and branch deletion only after verification. Never infer a
CI-unavailable override or silently change the confirmed mode.
"""


def render_downstream_workflow(required_gate_level: int) -> str:
    return f"""name: StateDD

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
        with:
          python-version: "3.13"
      - run: python3 scripts/statedd_quality_gate.py --gate-level {required_gate_level} --conformance
"""
