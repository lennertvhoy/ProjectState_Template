#!/usr/bin/env python3
"""Fail-closed regressions for the local closure preflight aggregator."""

from __future__ import annotations

from pathlib import Path

from statedd_closure_check import ClosureCheck


def test_run_fails_when_a_check_returns_false_without_diagnostic(tmp_path: Path) -> None:
    check = ClosureCheck(tmp_path, evidence_folder=tmp_path / "evidence")
    method_names = [
        "check_no_unproven_claims",
        "check_no_broken_links",
        "check_runtime_proof",
        "check_evidence_bundle",
        "check_acceptance_freeze",
        "check_handoff_complete",
        "check_dirty_worktree",
        "check_efficiency",
    ]
    for name in method_names:
        setattr(check, name, lambda: True)
    check.check_runtime_proof = lambda: False  # type: ignore[method-assign]

    assert check.run() == 1
    assert check.failures == ["One or more closure checks returned failure without a diagnostic"]
