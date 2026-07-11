#!/usr/bin/env python3
"""Regression tests for statedd_remote_closure_finalizer.py.

Stays stdlib-only; no real GitHub API or remote git calls.
"""

from __future__ import annotations

import json
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
    *, dirty: bool = False,
    pushed: bool = True,
    remote_url: str = REMOTE_URL,
    branch: str = BRANCH,
    head: str = LOCAL_HEAD,
) -> callable:
    """Return a run_command stand-in that returns canned git output."""

    def fake_run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
        if args == ["git", "rev-parse", "HEAD"]:
            return 0, head, ""
        if args == ["git", "branch", "--show-current"]:
            return 0, branch, ""
        if args == ["git", "remote", "get-url", "origin"]:
            return 0, remote_url, ""
        if args == ["git", "status", "--short"]:
            return 0, ("M file.txt\n" if dirty else ""), ""
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
    body: str = f"Final head: {LOCAL_HEAD}",
    merge_state: str = "CLEAN",
    ci_state: str = "SUCCESS",
    actions_run_id: str | None = "12345",
) -> dict:
    return {
        "repository": {
            "byNumber": None,
            "byBranch": {
                "nodes": [
                    {
                        "number": PR_NUMBER,
                        "headRefOid": head,
                        "body": body,
                        "mergeStateStatus": merge_state,
                        "url": f"https://github.com/statedd/template/pull/{PR_NUMBER}",
                    }
                ]
            },
            "object": {
                "statusCheckRollup": {"state": ci_state},
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
    pushed: bool = True,
    body: str = f"Final head: {LOCAL_HEAD}",
    merge_state: str = "CLEAN",
    ci_state: str = "SUCCESS",
    actions_run_id: str | None = "12345",
    pr_number: int | None = None,
    head: str = LOCAL_HEAD,
) -> finalizer.RemoteClosureFinalizer:
    if github_data is None:
        github_data = make_pr_data(
            head=head,
            body=body,
            merge_state=merge_state,
            ci_state=ci_state,
            actions_run_id=actions_run_id,
        )
    return finalizer.RemoteClosureFinalizer(
        root=tmp,
        verbose=False,
        pr_number=pr_number,
        run_command_fn=fake_run_command_factory(dirty=dirty, pushed=pushed, head=head),
        github_client=FakeGitHubApi(github_data),
    )


def write_evidence(root: Path, *, head: str | None = LOCAL_HEAD, final_head: str | None = None) -> None:
    evidence_dir = root / "docs" / "evidence" / "2026-06-29-remote-closure"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "schema": "statedd.evidence_manifest.v1",
        "slice_id": "BL-REMOTE-CLOSURE-001",
        "manifest_status": "complete",
        "created_at": "2026-06-29T00:00:00+00:00",
        "repo": {"branch": BRANCH, "head": head},
        "runtime_identity": {"required": False},
        "claims": [],
        "artifacts": [],
        "redaction": {"status": "checked"},
    }
    if final_head:
        manifest["proof_head"] = PROOF_HEAD
        manifest["final_head"] = final_head
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


def test_unpushed_branch_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, pushed=False)
        assert f.run() == 1


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
        f = make_finalizer(root, github_data=None, head=PROOF_HEAD)
        assert f.run() == 1
        assert any("PR head" in failure for failure in f.failures)


def test_stale_pr_body_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, body=f"Proof head: {PROOF_HEAD}")
        assert f.run() == 1
        assert any("PR body" in failure for failure in f.failures)


def test_pr_body_proof_final_split_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root, head=None, final_head=LOCAL_HEAD)
        body = f"- Proof head: {PROOF_HEAD}\n- Final PR head: {LOCAL_HEAD}"
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
        assert any("Evidence" in failure for failure in f.failures)


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
        test_unpushed_branch_fails,
        test_no_pr_fails,
        test_pr_head_mismatch_fails,
        test_stale_pr_body_fails,
        test_pr_body_proof_final_split_passes,
        test_ci_pending_fails,
        test_ci_failure_fails,
        test_no_actions_run_fails,
        test_merge_state_blocked_fails,
        test_evidence_head_mismatch_fails,
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
