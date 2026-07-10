#!/usr/bin/env python3
"""Focused regressions for scripts/statedd_closure_check.py."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import statedd_closure_check as closure  # noqa: E402
import statedd_remote_closure_finalizer as finalizer_module  # noqa: E402
import statedd_remote_truth_check as truth_module  # noqa: E402


class FakeRemoteTruth:
    def __init__(self, *args, **kwargs):
        self.failures: list[str] = []
        self.closure_label = "pushed"

    def run(self) -> int:
        return 0


class FakeRemoteFinalizer:
    exit_code = 0
    failure_messages: list[str] = []

    def __init__(self, *args, **kwargs):
        self.failures = list(self.failure_messages)
        self.closure_label = "CI verified" if self.exit_code == 0 else "NOT CLOSURE-GRADE"

    def run(self) -> int:
        return self.exit_code


def with_fake_remote_checks(finalizer_exit: int, failures: list[str]):
    original_truth = truth_module.RemoteTruthCheck
    original_finalizer = finalizer_module.RemoteClosureFinalizer
    truth_module.RemoteTruthCheck = FakeRemoteTruth
    FakeRemoteFinalizer.exit_code = finalizer_exit
    FakeRemoteFinalizer.failure_messages = failures
    finalizer_module.RemoteClosureFinalizer = FakeRemoteFinalizer
    return original_truth, original_finalizer


def restore_remote_checks(originals) -> None:
    truth_module.RemoteTruthCheck, finalizer_module.RemoteClosureFinalizer = originals


def test_remote_truth_without_current_head_ci_is_not_closure() -> None:
    originals = with_fake_remote_checks(1, ["Required CI check is missing"])
    try:
        with tempfile.TemporaryDirectory() as tmp:
            checker = closure.ClosureCheck(Path(tmp))
            assert checker.check_remote_truth() is False
            assert any("CI" in failure for failure in checker.failures)
    finally:
        restore_remote_checks(originals)


def test_remote_truth_and_current_head_ci_pass() -> None:
    originals = with_fake_remote_checks(0, [])
    try:
        with tempfile.TemporaryDirectory() as tmp:
            checker = closure.ClosureCheck(Path(tmp))
            assert checker.check_remote_truth() is True
            assert checker.closure_label == "CI verified"
    finally:
        restore_remote_checks(originals)


def test_false_check_result_cannot_exit_zero_without_failure_text() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        checker = closure.ClosureCheck(Path(tmp))
        checker.check_no_unproven_claims = lambda: True  # type: ignore[method-assign]
        checker.check_no_broken_links = lambda: True  # type: ignore[method-assign]
        checker.check_runtime_proof = lambda: True  # type: ignore[method-assign]
        checker.check_evidence_bundle = lambda: True  # type: ignore[method-assign]
        checker.check_acceptance_freeze = lambda: True  # type: ignore[method-assign]
        checker.check_handoff_complete = lambda: True  # type: ignore[method-assign]
        checker.check_remote_truth = lambda: True  # type: ignore[method-assign]
        checker.check_efficiency = lambda: False  # type: ignore[method-assign]
        assert checker.run() == 1


def main() -> int:
    tests = [
        test_remote_truth_without_current_head_ci_is_not_closure,
        test_remote_truth_and_current_head_ci_pass,
        test_false_check_result_cannot_exit_zero_without_failure_text,
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
