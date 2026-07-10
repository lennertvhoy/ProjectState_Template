#!/usr/bin/env python3
"""Regression tests for scripts/statedd_post_merge_verify.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_SCRIPT = ROOT / "scripts" / "statedd_post_merge_verify.py"
sys.path.insert(0, str(ROOT / "scripts"))

import statedd_post_merge_verify as post_merge  # noqa: E402


PR_HEAD = "1111111111111111111111111111111111111111"
MAIN_HEAD = "2222222222222222222222222222222222222222"
OTHER_HEAD = "3333333333333333333333333333333333333333"
MERGE_COMMIT = MAIN_HEAD
PR_NUMBER = 42
REMOTE_URL = "https://github.com/statedd/template.git"


def run_verify(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class FakeGitHubApi:
    def __init__(self, default_data: dict, pr_data: dict):
        self.default_data = default_data
        self.pr_data = pr_data

    def query(self, query: str, variables: dict) -> dict:
        if "defaultBranchRef" in query:
            return self.default_data
        return self.pr_data


def make_default_data(
    *,
    main_head: str = MAIN_HEAD,
    required_checks: tuple[str, ...] = ("validate",),
) -> dict:
    return {
        "repository": {
            "defaultBranchRef": {
                "name": "main",
                "target": {"oid": main_head},
                "branchProtectionRule": {
                    "requiresStatusChecks": bool(required_checks),
                    "requiredStatusChecks": [
                        {"context": name, "app": {"id": "MDM6QXBwMTUzNjg="}}
                        for name in required_checks
                    ],
                },
            }
        }
    }


def make_pr_data(
    *,
    main_head: str = MAIN_HEAD,
    commit_head: str | None = None,
    ci_state: str = "SUCCESS",
    check_status: str = "COMPLETED",
    check_conclusion: str = "SUCCESS",
    emitted_checks: tuple[str, ...] = ("validate",),
    actions_run_id: str | None = "12345",
) -> dict:
    contexts = []
    for name in emitted_checks:
        contexts.append(
            {
                "__typename": "CheckRun",
                "name": name,
                "status": check_status,
                "conclusion": check_conclusion,
                "checkSuite": {
                    "app": {
                        "id": "MDM6QXBwMTUzNjg=",
                        "databaseId": 15368,
                        "name": "GitHub Actions",
                        "slug": "github-actions",
                    },
                    "commit": {"oid": commit_head or main_head},
                    "workflowRun": {
                        "databaseId": actions_run_id,
                        "runNumber": 1,
                        "url": f"https://github.com/statedd/template/actions/runs/{actions_run_id}",
                    }
                    if actions_run_id
                    else None,
                },
            }
        )
    return {
        "repository": {
            "pullRequest": {
                "number": PR_NUMBER,
                "headRefName": "feature/closure",
                "headRefOid": PR_HEAD,
                "mergeCommit": {"oid": MERGE_COMMIT},
                "merged": True,
                "state": "MERGED",
                "body": f"Final PR head: {PR_HEAD}",
                "mergeStateStatus": "MERGED",
                "url": f"https://github.com/statedd/template/pull/{PR_NUMBER}",
            },
            "object": {
                "oid": commit_head or main_head,
                "statusCheckRollup": {
                    "state": ci_state,
                    "contexts": {
                        "nodes": contexts,
                        "pageInfo": {"hasNextPage": False},
                    },
                },
                "checkSuites": {
                    "nodes": [
                        {
                            "databaseId": 100,
                            "app": {"name": "GitHub Actions"},
                            "workflowRun": {
                                "databaseId": actions_run_id,
                                "runNumber": 1,
                                "url": f"https://github.com/statedd/template/actions/runs/{actions_run_id}",
                            },
                        }
                    ]
                    if actions_run_id
                    else []
                },
            },
        }
    }


def fake_git(
    *,
    local_head: str = MAIN_HEAD,
    branch: str = "main",
    status: str = "",
    upstream: str | None = "origin/main",
    upstream_head: str = MAIN_HEAD,
    remote_head: str = MAIN_HEAD,
):
    def run(args: list[str], cwd: Path) -> tuple[int, str, str]:
        if args == ["git", "rev-parse", "HEAD"]:
            return 0, local_head, ""
        if args == ["git", "branch", "--show-current"]:
            return 0, branch, ""
        if args == ["git", "remote", "get-url", "origin"]:
            return 0, REMOTE_URL, ""
        if args in (
            ["git", "status", "--short"],
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        ):
            return 0, status, ""
        if args == ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"]:
            if upstream is None:
                return 128, "", "no upstream configured"
            return 0, upstream, ""
        if args == ["git", "rev-parse", "@{upstream}"]:
            if upstream is None:
                return 128, "", "no upstream configured"
            return 0, upstream_head, ""
        if args[:4] == ["git", "ls-remote", "--heads", "origin"]:
            return 0, f"{remote_head}\trefs/heads/main", ""
        if args[:3] == ["git", "fetch", "origin"]:
            return 0, "", ""
        if args[:3] == ["git", "merge-base", "--is-ancestor"]:
            return 0, "", ""
        return 127, "", f"unexpected command: {' '.join(args)}"

    return run


def write_evidence(root: Path, *, pr_head: str = PR_HEAD, main_head: str = MAIN_HEAD) -> Path:
    folder = root / "docs" / "evidence" / "slice"
    folder.mkdir(parents=True)
    manifest = {
        "schema": "statedd.evidence_manifest.v1",
        "slice_id": "BL-CORE-001",
        "manifest_status": "complete",
        "created_at": "2026-07-10T00:00:00+00:00",
        "repo": {"branch": "feature/closure", "head": pr_head},
        "final_pr_head": pr_head,
        "merge_commit_sha": MERGE_COMMIT,
        "main_head_after_merge": main_head,
        "privacy": {"profile": "public", "machine_identity": "normalized"},
        "change": {"type": "config"},
        "runtime_identity": {"required": False, "path": "runtime_identity.json", "status": "not_applicable"},
        "claims": [{"id": "C1", "claim": "Post-merge verification passed.", "status": "validated", "evidence": ["runtime_identity.json", "validation.txt"]}],
        "artifacts": [
            {"path": "runtime_identity.json", "kind": "runtime_identity", "evidence_types": ["runtime_proof"], "redaction_status": "checked", "sensitive_data": "none_found"},
            {"path": "validation.txt", "kind": "command_output", "evidence_types": ["diff", "validation_output"], "redaction_status": "checked", "sensitive_data": "none_found"},
        ],
        "redaction": {"status": "checked", "automated_scan": "passed", "manual_review": "completed", "known_limits": []},
    }
    runtime_identity = {
        "schema": "statedd.runtime_identity.v1",
        "captured_at": "2026-07-10T00:00:00+00:00",
        "privacy": {"profile": "public", "machine_identity": "normalized"},
        "repo": {"path": "$REPO_ROOT", "branch": "feature/closure", "head": pr_head, "worktree_clean": True},
        "runtime": {"required": False, "reason": "scripts-only validation"},
        "checks": {"runtime_not_applicable_recorded": True, "head_recorded": True},
        "limits": [],
    }
    (folder / "runtime_identity.json").write_text(json.dumps(runtime_identity), encoding="utf-8")
    (folder / "validation.txt").write_text("validation\n", encoding="utf-8")
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    closure = {
        "schema": "statedd.remote_closure_handoff.v1",
        "slice_id": "BL-CORE-001",
        "pr_head": pr_head,
        "merge_commit_sha": MERGE_COMMIT,
        "main_head_after_merge": main_head,
    }
    (folder / "closure.json").write_text(json.dumps(closure), encoding="utf-8")
    (folder / "README.md").write_text(
        f"Final PR head: {pr_head}\nMerge commit: {MERGE_COMMIT}\nMain head: {main_head}\n",
        encoding="utf-8",
    )
    return folder


def make_verifier(
    root: Path,
    *,
    local_head: str = MAIN_HEAD,
    branch: str = "main",
    status: str = "",
    upstream: str | None = "origin/main",
    upstream_head: str = MAIN_HEAD,
    remote_head: str = MAIN_HEAD,
    default_head: str = MAIN_HEAD,
    commit_head: str | None = None,
    ci_state: str = "SUCCESS",
    check_status: str = "COMPLETED",
    check_conclusion: str = "SUCCESS",
    required_checks: tuple[str, ...] = ("validate",),
    emitted_checks: tuple[str, ...] = ("validate",),
    actions_run_id: str | None = "12345",
) -> post_merge.PostMergeVerifier:
    verifier = post_merge.PostMergeVerifier(
        root=root,
        pr_number=PR_NUMBER,
        run_command_fn=fake_git(
            local_head=local_head,
            branch=branch,
            status=status,
            upstream=upstream,
            upstream_head=upstream_head,
            remote_head=remote_head,
        ),
        github_client=FakeGitHubApi(
            make_default_data(main_head=default_head, required_checks=required_checks),
            make_pr_data(
                main_head=default_head,
                commit_head=commit_head,
                ci_state=ci_state,
                check_status=check_status,
                check_conclusion=check_conclusion,
                emitted_checks=emitted_checks,
                actions_run_id=actions_run_id,
            ),
        ),
    )
    verifier.slice_id = "BL-CORE-001"
    return verifier


def test_help_runs() -> None:
    completed = run_verify(["--help"])
    assert completed.returncode == 0, completed.stderr
    assert "pr-number" in completed.stdout


def test_missing_pr_number_fails() -> None:
    completed = run_verify([])
    assert completed.returncode == 2, completed.stderr


def test_all_green() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        assert make_verifier(root).run() == 0


def test_each_porcelain_dirty_category_fails() -> None:
    for status in ("M  staged.py", " M unstaged.py", "?? untracked.py"):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root)
            verifier = make_verifier(root, status=status)
            assert verifier.run() == 1, status
            assert any("dirty" in failure.lower() for failure in verifier.failures)


def test_local_default_head_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        verifier = make_verifier(root, local_head=OTHER_HEAD)
        assert verifier.run() == 1
        assert any("local" in failure.lower() and "head" in failure.lower() for failure in verifier.failures)


def test_wrong_local_branch_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        verifier = make_verifier(root, branch="feature/closure")
        assert verifier.run() == 1
        assert any("branch" in failure.lower() for failure in verifier.failures)


def test_missing_upstream_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        verifier = make_verifier(root, upstream=None)
        assert verifier.run() == 1
        assert any("upstream" in failure.lower() for failure in verifier.failures)


def test_upstream_head_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        verifier = make_verifier(root, upstream_head=OTHER_HEAD)
        assert verifier.run() == 1
        assert any("upstream" in failure.lower() for failure in verifier.failures)


def test_remote_default_head_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        verifier = make_verifier(root, remote_head=OTHER_HEAD)
        assert verifier.run() == 1
        assert any("remote" in failure.lower() and "head" in failure.lower() for failure in verifier.failures)


def test_stale_ci_commit_head_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        verifier = make_verifier(root, commit_head=OTHER_HEAD)
        assert verifier.run() == 1
        assert any("CI" in failure and "head" in failure.lower() for failure in verifier.failures)


def test_pending_required_check_fails_even_with_success_rollup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        verifier = make_verifier(root, ci_state="SUCCESS", check_status="IN_PROGRESS")
        assert verifier.run() == 1
        assert any("validate" in failure and "completed" in failure.lower() for failure in verifier.failures)


def test_omitted_required_check_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        verifier = make_verifier(
            root,
            required_checks=("validate", "security"),
            emitted_checks=("validate",),
        )
        assert verifier.run() == 1
        assert any("security" in failure and "missing" in failure.lower() for failure in verifier.failures)


def test_missing_evidence_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        verifier = make_verifier(Path(tmp))
        assert verifier.run() == 1
        assert any("evidence" in failure.lower() for failure in verifier.failures)


def main() -> int:
    tests = [
        test_help_runs,
        test_missing_pr_number_fails,
        test_all_green,
        test_each_porcelain_dirty_category_fails,
        test_local_default_head_mismatch_fails,
        test_wrong_local_branch_fails,
        test_missing_upstream_fails,
        test_upstream_head_mismatch_fails,
        test_remote_default_head_mismatch_fails,
        test_stale_ci_commit_head_fails,
        test_pending_required_check_fails_even_with_success_rollup,
        test_omitted_required_check_fails,
        test_missing_evidence_fails,
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
