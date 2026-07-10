#!/usr/bin/env python3
"""Regression tests for statedd_remote_closure_finalizer.py.

Stays stdlib-only; no real GitHub API or remote git calls.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import statedd_remote_closure_finalizer as finalizer  # noqa: E402


LOCAL_HEAD = "20b446d6401fff3d74fe4beb64cc0c45aea90b5e"
PROOF_HEAD = "2e84aee8c4f8e16f3a9d0b1c5d8e7f2a1b3c4d5e"
REMOTE_URL = "https://github.com/statedd/template.git"
BRANCH = "feature/remote-closure"
PR_NUMBER = 42


def fake_run_command_factory(
    *,
    status: str = "",
    pushed: bool = True,
    remote_url: str = REMOTE_URL,
    branch: str = BRANCH,
    head: str = LOCAL_HEAD,
    upstream: str | None = f"origin/{BRANCH}",
    upstream_head: str | None = None,
) -> callable:
    """Return a run_command stand-in that returns canned git output."""

    def fake_run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
        if args == ["git", "rev-parse", "HEAD"]:
            return 0, head, ""
        if args == ["git", "branch", "--show-current"]:
            return 0, branch, ""
        if args == ["git", "remote", "get-url", "origin"]:
            return 0, remote_url, ""
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
            return 0, upstream_head or head, ""
        if args[:4] == ["git", "ls-remote", "--heads", "origin"]:
            if pushed:
                return 0, f"{head}\trefs/heads/{branch}", ""
            return 1, "", "no remote"
        if args[:3] == ["git", "ls-remote", "origin"]:
            if pushed:
                return 0, f"{head}\trefs/heads/{branch}", ""
            return 1, "", "no remote"
        return 127, "", f"unexpected command: {' '.join(args)}"

    return fake_run_command


class FakeGitHubApi:
    def __init__(self, data: dict):
        self.data = data

    def query(self, query: str, variables: dict) -> dict:
        return self.data


def make_pr_data(
    *,
    head: str = LOCAL_HEAD,
    body: str = f"Final PR head: {LOCAL_HEAD}",
    merge_state: str = "CLEAN",
    ci_state: str = "SUCCESS",
    actions_run_id: str | None = "12345",
    commit_head: str | None = None,
    check_status: str = "COMPLETED",
    check_conclusion: str = "SUCCESS",
    required_checks: tuple[str, ...] = ("validate",),
    emitted_checks: tuple[str, ...] = ("validate",),
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
                    "commit": {"oid": commit_head or head},
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
            "byNumber": None,
            "byBranch": {
                "nodes": [
                    {
                        "number": PR_NUMBER,
                        "headRefOid": head,
                        "body": body,
                        "baseRef": {
                            "name": "main",
                            "branchProtectionRule": {
                                "requiresStatusChecks": bool(required_checks),
                                "requiredStatusChecks": [
                                    {"context": name, "app": {"id": "MDM6QXBwMTUzNjg="}}
                                    for name in required_checks
                                ],
                            },
                        },
                        "mergeStateStatus": merge_state,
                        "url": f"https://github.com/statedd/template/pull/{PR_NUMBER}",
                    }
                ]
            },
            "object": {
                "oid": commit_head or head,
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


def make_finalizer(
    tmp: Path,
    *,
    github_data: dict,
    dirty: bool = False,
    status: str = "",
    pushed: bool = True,
    body: str = f"Final PR head: {LOCAL_HEAD}",
    merge_state: str = "CLEAN",
    ci_state: str = "SUCCESS",
    actions_run_id: str | None = "12345",
    pr_number: int | None = None,
    head: str = LOCAL_HEAD,
    upstream: str | None = f"origin/{BRANCH}",
    upstream_head: str | None = None,
    commit_head: str | None = None,
    check_status: str = "COMPLETED",
    check_conclusion: str = "SUCCESS",
    required_checks: tuple[str, ...] = ("validate",),
    emitted_checks: tuple[str, ...] = ("validate",),
) -> finalizer.RemoteClosureFinalizer:
    if github_data is None:
        github_data = make_pr_data(
            head=head,
            body=body,
            merge_state=merge_state,
            ci_state=ci_state,
            actions_run_id=actions_run_id,
            commit_head=commit_head,
            check_status=check_status,
            check_conclusion=check_conclusion,
            required_checks=required_checks,
            emitted_checks=emitted_checks,
        )
    instance = finalizer.RemoteClosureFinalizer(
        root=tmp,
        verbose=False,
        pr_number=pr_number,
        run_command_fn=fake_run_command_factory(
            status=status or (" M file.txt" if dirty else ""),
            pushed=pushed,
            head=head,
            upstream=upstream,
            upstream_head=upstream_head,
        ),
        github_client=FakeGitHubApi(github_data),
    )
    instance.slice_id = "BL-REMOTE-CLOSURE-001"
    return instance


def write_evidence(root: Path, *, head: str | None = LOCAL_HEAD, final_head: str | None = None) -> None:
    evidence_dir = root / "docs" / "evidence" / "2026-06-29-remote-closure"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    manifest_head = final_head or head
    runtime_identity = {
        "schema": "statedd.runtime_identity.v1",
        "captured_at": "2026-06-29T00:00:00+00:00",
        "privacy": {"profile": "public", "machine_identity": "normalized"},
        "repo": {"path": "$REPO_ROOT", "branch": BRANCH, "head": manifest_head, "worktree_clean": True},
        "runtime": {"required": False, "reason": "scripts-only validation"},
        "checks": {"runtime_not_applicable_recorded": True, "head_recorded": True},
        "limits": [],
    }
    (evidence_dir / "runtime_identity.json").write_text(json.dumps(runtime_identity, indent=2), encoding="utf-8")
    (evidence_dir / "validation.txt").write_text("remote closure validation\n", encoding="utf-8")
    manifest: dict = {
        "schema": "statedd.evidence_manifest.v1",
        "slice_id": "BL-REMOTE-CLOSURE-001",
        "manifest_status": "complete",
        "created_at": "2026-06-29T00:00:00+00:00",
        "repo": {"branch": BRANCH, "head": manifest_head},
        "privacy": {"profile": "public", "machine_identity": "normalized"},
        "change": {"type": "config"},
        "runtime_identity": {"required": False, "path": "runtime_identity.json", "status": "not_applicable"},
        "claims": [{"id": "C1", "claim": "Remote closure checks passed.", "status": "validated", "evidence": ["runtime_identity.json", "validation.txt"]}],
        "artifacts": [
            {"path": "runtime_identity.json", "kind": "runtime_identity", "evidence_types": ["runtime_proof"], "redaction_status": "checked", "sensitive_data": "none_found"},
            {"path": "validation.txt", "kind": "command_output", "evidence_types": ["diff", "validation_output"], "redaction_status": "checked", "sensitive_data": "none_found"},
        ],
        "redaction": {"status": "checked", "automated_scan": "passed", "manual_review": "completed", "known_limits": []},
    }
    if final_head:
        manifest["proof_head"] = PROOF_HEAD
        manifest["final_pr_head"] = final_head
    (evidence_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    readme_lines = ["# Evidence: remote closure"]
    if final_head:
        readme_lines.append(f"**Proof head:** {PROOF_HEAD}")
        readme_lines.append(f"**Final PR head:** {final_head}")
    elif head:
        readme_lines.append(f"**HEAD:** {head}")
    (evidence_dir / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")


def test_all_green() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None)
        assert f.run() == 0
        assert f.closure_label == "CI verified"
        assert f.ci_run_id == "12345"


def test_dirty_worktree_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, dirty=True)
        assert f.run() == 1
        assert any("dirty" in failure.lower() for failure in f.failures)


def test_each_porcelain_dirty_category_fails() -> None:
    for status in ("M  staged.py", " M unstaged.py", "?? untracked.py"):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root)
            f = make_finalizer(root, github_data=None, status=status)
            assert f.run() == 1, status
            assert any("dirty" in failure.lower() for failure in f.failures)


def test_unpushed_branch_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, pushed=False)
        assert f.run() == 1


def test_missing_upstream_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, upstream=None)
        assert f.run() == 1
        assert any("upstream" in failure.lower() for failure in f.failures)


def test_stale_upstream_tracking_ref_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, upstream_head=PROOF_HEAD)
        assert f.run() == 1
        assert any("upstream" in failure.lower() for failure in f.failures)


def test_no_pr_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        data = {"repository": {"byNumber": None, "byBranch": {"nodes": []}, "object": None}}
        f = make_finalizer(root, github_data=data)
        assert f.run() == 1


def test_pr_head_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        data = make_pr_data(head=PROOF_HEAD)
        f = make_finalizer(root, github_data=data)
        assert f.run() == 1
        assert any("PR head" in failure for failure in f.failures)


def test_stale_pr_body_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, body=f"Proof head: {PROOF_HEAD}")
        assert f.run() == 1
        assert any("PR body" in failure for failure in f.failures)


def test_incidental_current_sha_does_not_override_stale_final_head() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        body = f"Historical reference: {LOCAL_HEAD}\nFinal PR head: {PROOF_HEAD}"
        f = make_finalizer(root, github_data=None, body=body)
        assert f.run() == 1
        assert any("PR body" in failure for failure in f.failures)


def test_pr_body_proof_final_split_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root, head=None, final_head=LOCAL_HEAD)
        body = f"Proof head: {PROOF_HEAD}\nFinal PR head: {LOCAL_HEAD}"
        f = make_finalizer(root, github_data=None, body=body)
        assert f.run() == 0
        assert f.closure_label == "CI verified"


def test_ci_pending_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, ci_state="PENDING")
        assert f.run() == 1
        assert any("pending" in failure.lower() for failure in f.failures)


def test_ci_failure_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, ci_state="FAILURE")
        assert f.run() == 1
        assert any("FAILURE" in failure for failure in f.failures)


def test_stale_ci_commit_head_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, commit_head=PROOF_HEAD)
        assert f.run() == 1
        assert any("CI" in failure and "head" in failure.lower() for failure in f.failures)


def test_pending_required_check_fails_even_if_rollup_claims_success() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(
            root,
            github_data=None,
            ci_state="SUCCESS",
            check_status="IN_PROGRESS",
            check_conclusion="SUCCESS",
        )
        assert f.run() == 1
        assert any("validate" in failure and "completed" in failure.lower() for failure in f.failures)


def test_omitted_required_check_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(
            root,
            github_data=None,
            required_checks=("validate", "security"),
            emitted_checks=("validate",),
        )
        assert f.run() == 1
        assert any("security" in failure and "missing" in failure.lower() for failure in f.failures)


def test_no_required_ci_configuration_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, required_checks=())
        assert f.run() == 1
        assert any("required" in failure.lower() and "configured" in failure.lower() for failure in f.failures)


def test_no_actions_run_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, actions_run_id=None)
        assert f.run() == 1
        assert any("Actions" in failure for failure in f.failures)


def test_merge_state_blocked_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, merge_state="BLOCKED")
        assert f.run() == 1
        assert any("mergeStateStatus" in failure for failure in f.failures)


def test_evidence_head_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root, head=PROOF_HEAD)
        f = make_finalizer(root, github_data=None)
        assert f.run() == 1
        assert any("evidence" in failure.lower() for failure in f.failures)


def test_abbreviated_evidence_head_fails_exact_equality() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root, head=LOCAL_HEAD[:7])
        f = make_finalizer(root, github_data=None)
        assert f.run() == 1
        assert any("evidence" in failure.lower() for failure in f.failures)


def test_missing_evidence_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        f = make_finalizer(root, github_data=None)
        assert f.run() == 1
        assert any("evidence" in failure.lower() for failure in f.failures)


def test_evidence_selected_by_head_not_mtime() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        valid = root / "docs" / "evidence" / "2026-06-29-remote-closure"
        stale = root / "docs" / "evidence" / "newer-but-stale"
        stale.mkdir(parents=True)
        manifest = json.loads((valid / "manifest.json").read_text(encoding="utf-8"))
        manifest["slice_id"] = "BL-OTHER-001"
        manifest["repo"]["head"] = PROOF_HEAD
        (stale / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (stale / "README.md").write_text(f"HEAD: {PROOF_HEAD}\n", encoding="utf-8")
        os.utime(stale, (valid.stat().st_mtime + 100, valid.stat().st_mtime + 100))

        f = make_finalizer(root, github_data=None)
        assert f.run() == 0
        assert f.evidence_folder == valid


def test_evidence_proof_final_split_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root, head=None, final_head=LOCAL_HEAD)
        f = make_finalizer(root, github_data=None)
        assert f.run() == 0
        assert f.closure_label == "CI verified"


def test_explicit_pr_number() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        data = make_pr_data()
        pr = data["repository"]["byBranch"]["nodes"][0]
        # Wipe branch lookup so we prove the finalizer used the explicit number.
        data["repository"]["byBranch"] = {"nodes": []}
        data["repository"]["byNumber"] = pr
        f = make_finalizer(root, github_data=data, pr_number=PR_NUMBER)
        assert f.run() == 0
        assert f.pr.get("number") == PR_NUMBER


def test_writes_output_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        output = root / "closure.json"
        write_evidence(root)
        f = make_finalizer(root, github_data=None)
        f.output = output
        assert f.run() == 0
        assert output.exists()
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["local_head"] == LOCAL_HEAD
        assert data["closure_label"] == "CI verified"


def main() -> int:
    tests = [
        test_all_green,
        test_dirty_worktree_fails,
        test_each_porcelain_dirty_category_fails,
        test_unpushed_branch_fails,
        test_missing_upstream_fails,
        test_stale_upstream_tracking_ref_fails,
        test_no_pr_fails,
        test_pr_head_mismatch_fails,
        test_stale_pr_body_fails,
        test_incidental_current_sha_does_not_override_stale_final_head,
        test_pr_body_proof_final_split_passes,
        test_ci_pending_fails,
        test_ci_failure_fails,
        test_stale_ci_commit_head_fails,
        test_pending_required_check_fails_even_if_rollup_claims_success,
        test_omitted_required_check_fails,
        test_no_required_ci_configuration_fails,
        test_no_actions_run_fails,
        test_merge_state_blocked_fails,
        test_evidence_head_mismatch_fails,
        test_abbreviated_evidence_head_fails_exact_equality,
        test_missing_evidence_fails,
        test_evidence_selected_by_head_not_mtime,
        test_evidence_proof_final_split_passes,
        test_explicit_pr_number,
        test_writes_output_json,
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
        except Exception as exc:
            failures += 1
            print(f"ERROR {test.__name__}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
