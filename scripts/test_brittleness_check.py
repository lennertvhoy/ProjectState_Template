#!/usr/bin/env python3
"""Regression tests for scripts/projectstate_brittleness_check.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "projectstate_brittleness_check.py"
AUDIT = ROOT / "scripts" / "projectstate_audit.py"


def load_audit_module():
    spec = importlib.util.spec_from_file_location("projectstate_audit_for_test", AUDIT)
    if spec is None or spec.loader is None:
        raise AssertionError("Could not load projectstate_audit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_diff(diff_text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        diff = Path(tmp) / "slice.diff"
        diff.write_text(diff_text, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(CHECK), "--diff-file", str(diff)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"Expected scanner success, got {completed.returncode}\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        return completed


def assert_contains(output: str, expected: str) -> None:
    if expected not in output:
        raise AssertionError(f"Expected output to contain {expected!r}, got:\n{output}")


def test_warns_on_large_keyword_bucket_and_exact_prompt_string() -> None:
    completed = run_diff(
        """diff --git a/src/router.ts b/src/router.ts
--- a/src/router.ts
+++ b/src/router.ts
@@ -0,0 +1,20 @@
+const keywords = ["refund", "billing", "invoice", "charge", "card", "subscription", "cancel", "renew", "trial", "payment", "receipt", "tax"];
+if (user_prompt === "please refund my subscription using this exact observed customer sentence") {
+  return "refund";
+}
"""
    )
    assert_contains(completed.stdout, "large_keyword_bucket")
    assert_contains(completed.stdout, "exact_prompt_string")
    assert_contains(completed.stdout, "advisory warnings found")


def test_warns_on_many_includes_and_sleep() -> None:
    completed = run_diff(
        """diff --git a/src/sync.js b/src/sync.js
--- a/src/sync.js
+++ b/src/sync.js
@@ -0,0 +1,20 @@
+if (message.includes("a")) route = "a";
+if (message.includes("b")) route = "b";
+if (message.includes("c")) route = "c";
+if (message.includes("d")) route = "d";
+if (message.includes("e")) route = "e";
+await new Promise(resolve => setTimeout(resolve, 2000));
"""
    )
    assert_contains(completed.stdout, "many_includes_checks")
    assert_contains(completed.stdout, "sleep_or_timeout_sync")


def test_warns_on_fixture_only_exact_prompt_test() -> None:
    completed = run_diff(
        """diff --git a/tests/router.test.ts b/tests/router.test.ts
--- a/tests/router.test.ts
+++ b/tests/router.test.ts
@@ -0,0 +1,8 @@
+it("handles observed prompt", () => {
+  expect(route("please refund my subscription using this exact observed customer sentence")).toEqual("refund");
+});
"""
    )
    assert_contains(completed.stdout, "fixture_only_test_shape")


def test_no_warning_output_does_not_claim_quality_proof() -> None:
    completed = run_diff(
        """diff --git a/src/schema.ts b/src/schema.ts
--- a/src/schema.ts
+++ b/src/schema.ts
@@ -0,0 +1,4 @@
+export type RouteKind = "refund" | "support";
+export function route(kind: RouteKind) {
+  return kind;
+}
"""
    )
    assert_contains(completed.stdout, "No heuristic warnings found")
    assert_contains(completed.stdout, "does not prove absence of brittleness")
    if "proves absence" in completed.stdout:
        raise AssertionError(f"Scanner made an overclaim:\n{completed.stdout}")


def write_evidence(root: Path, body: str) -> None:
    folder = root / "docs" / "evidence" / "slice"
    folder.mkdir(parents=True)
    (folder / "README.md").write_text(body, encoding="utf-8")


def test_anti_brittleness_evidence_marker_passes_audit_check() -> None:
    audit = load_audit_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(
            root,
            """# Evidence

- type: fix

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | State transition owns routing. |
| Is the fix typed/schema/state-machine/validator/contract-based? | State-machine-backed. |
| Which behavior is centralized instead of scattered? | Routing authority. |
| Which observed examples are covered by general rules rather than exact strings? | All refund intents. |
| What adjacent cases were tested? | Refund, cancel, unknown. |
| What brittle pattern was explicitly avoided? | Exact prompt matching. |
| Did the slice add keyword buckets, regex branches, exact prompt handling, fixture-only behavior, sleeps/timeouts, global mutable state, silent fallback, or provider-specific assumptions? | No. |
| If yes, why is that not the authority path? | Not applicable. |
""",
        )
        result = audit.AuditResult()
        audit.check_anti_brittleness_review(root, result, strict=True)
        if result.has_failures() or result.has_warnings():
            raise AssertionError(f"Expected pass, got: {result.findings}")


def test_missing_anti_brittleness_marker_warns_and_fails_strict() -> None:
    audit = load_audit_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root, "# Evidence\n\n- type: fix\n\n## Claims\n\n- Claim: fixed\n")
        normal = audit.AuditResult()
        audit.check_anti_brittleness_review(root, normal, strict=False)
        if not normal.has_warnings() or normal.has_failures():
            raise AssertionError(f"Expected warning only, got: {normal.findings}")

        strict = audit.AuditResult()
        audit.check_anti_brittleness_review(root, strict, strict=True)
        if not strict.has_failures():
            raise AssertionError(f"Expected strict failure, got: {strict.findings}")


def main() -> int:
    tests = [
        test_warns_on_large_keyword_bucket_and_exact_prompt_string,
        test_warns_on_many_includes_and_sleep,
        test_warns_on_fixture_only_exact_prompt_test,
        test_no_warning_output_does_not_claim_quality_proof,
        test_anti_brittleness_evidence_marker_passes_audit_check,
        test_missing_anti_brittleness_marker_warns_and_fails_strict,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
