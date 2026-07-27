#!/usr/bin/env python3
"""Regression tests for projectstate_remote_closure_finalizer.py.

Stays stdlib-only; no real GitHub API or remote git calls.
"""

from __future__ import annotations

import json
import hashlib
import copy
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import projectstate_remote_closure_finalizer as finalizer  # noqa: E402


LOCAL_HEAD = "20b446d6401fff3d74fe4beb64cc0c45aea90b5e"
PROOF_HEAD = "2e84aee8c4f8e16f3a9d0b1c5d8e7f2a1b3c4d5e"
REMOTE_URL = "https://github.com/projectstate/template.git"
BRANCH = "feature/remote-closure"
PR_NUMBER = 42


def fake_run_command_factory(
    *, dirty: bool = False,
    pushed: bool = True,
    remote_url: str = REMOTE_URL,
    branch: str = BRANCH,
    head: str = LOCAL_HEAD,
    proof_is_ancestor: bool = True,
    tracked: bool = True,
    diff_paths: list[str] | None = None,
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
        if args[:3] == ["git", "merge-base", "--is-ancestor"]:
            proof = args[3]
            return (0, "", "") if proof_is_ancestor and proof == PROOF_HEAD else (1, "", "not ancestor")
        if args[:3] == ["git", "diff", "--name-only"]:
            paths = diff_paths or [
                "docs/evidence/2026-06-29-remote-closure/README.md",
                "docs/evidence/2026-06-29-remote-closure/manifest.json",
            ]
            return 0, "\n".join(paths), ""
        if args[:3] == ["git", "ls-files", "--error-unmatch"]:
            return (0, args[-1], "") if tracked else (1, "", "untracked")
        if args[:3] == ["git", "cat-file", "-e"]:
            return (0, "", "") if tracked else (1, "", "missing")
        return 127, "", f"unexpected command: {' '.join(args)}"

    return fake_run_command


class FakeGitHubApi:
    def __init__(self, data: dict):
        self.data = data
        self.calls = 0

    def query(self, query: str, variables: dict) -> dict:
        self.calls += 1
        response = copy.deepcopy(self.data)
        repository = response.get("repository", {})
        if variables.get("number") is not None and repository.get("byNumber") is None:
            nodes = (repository.get("byBranch") or {}).get("nodes", [])
            repository["byNumber"] = nodes[0] if nodes else None
        return response


class SequenceGitHubApi:
    def __init__(self, responses: list[dict]):
        self.responses = responses
        self.calls = 0

    def query(self, query: str, variables: dict) -> dict:
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        response = copy.deepcopy(self.responses[index])
        repository = response.get("repository", {})
        if variables.get("number") is not None and repository.get("byNumber") is None:
            nodes = (repository.get("byBranch") or {}).get("nodes", [])
            repository["byNumber"] = nodes[0] if nodes else None
        return response


def make_pr_data(
    *,
    head: str = LOCAL_HEAD,
    body: str = (
        f"Proof head: {PROOF_HEAD}\nFinal PR head: {LOCAL_HEAD}\n"
        "Evidence: docs/evidence/2026-06-29-remote-closure"
    ),
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
                        "headRefName": BRANCH,
                        "body": body,
                        "isDraft": False,
                        "reviewDecision": "APPROVED",
                        "reviewThreads": {
                            "nodes": [],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        },
                        "mergeStateStatus": merge_state,
                        "url": f"https://github.com/projectstate/template/pull/{PR_NUMBER}",
                    }
                ]
            },
            "object": {
                "oid": head,
                "statusCheckRollup": {"state": ci_state},
                "checkSuites": {
                    "nodes": [
                        {
                            "databaseId": 100,
                            "status": "COMPLETED",
                            "conclusion": "SUCCESS",
                            "app": {"name": "GitHub Actions"},
                            "workflowRun": {
                                "databaseId": actions_run_id,
                                "runNumber": 1,
                                "url": f"https://github.com/projectstate/template/actions/runs/{actions_run_id}",
                                "file": {"path": ".github/workflows/validate.yml"},
                            },
                        }
                    ]
                    if actions_run_id
                    else [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
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
    body: str = (
        f"Proof head: {PROOF_HEAD}\nFinal PR head: {LOCAL_HEAD}\n"
        "Evidence: docs/evidence/2026-06-29-remote-closure"
    ),
    merge_state: str = "CLEAN",
    ci_state: str = "SUCCESS",
    actions_run_id: str | None = "12345",
    pr_number: int | None = None,
    head: str = LOCAL_HEAD,
    proof_is_ancestor: bool = True,
    tracked: bool = True,
    diff_paths: list[str] | None = None,
) -> finalizer.RemoteClosureFinalizer:
    workflow = tmp / ".github" / "workflows" / "validate.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    if not workflow.exists():
        workflow.write_text(
            "name: Validate\n"
            "on: {push: {}, pull_request: {}}\n"
            "jobs:\n"
            "  validate:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - run: python3 scripts/projectstate_quality_gate.py --gate-level 2 --conformance\n",
            encoding="utf-8",
        )
    state = tmp / "PROJECT_STATE.yaml"
    if not state.exists():
        state.write_text(
            "workflow:\n  repo_role: template_repository\n  projectstate_mode: template-maintenance\n",
            encoding="utf-8",
        )
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
        run_command_fn=fake_run_command_factory(
            dirty=dirty,
            pushed=pushed,
            head=head,
            proof_is_ancestor=proof_is_ancestor,
            tracked=tracked,
            diff_paths=diff_paths,
        ),
        github_client=FakeGitHubApi(github_data),
    )


def write_evidence(root: Path, *, head: str | None = PROOF_HEAD, final_head: str | None = None) -> None:
    workflow = root / ".github" / "workflows" / "validate.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(
        "name: Validate\n"
        "on: {push: {}, pull_request: {}}\n"
        "jobs:\n"
        "  validate:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: python3 scripts/projectstate_quality_gate.py --gate-level 2 --conformance\n",
        encoding="utf-8",
    )
    (root / "PROJECT_STATE.yaml").write_text(
        "workflow:\n  repo_role: template_repository\n  projectstate_mode: template-maintenance\n",
        encoding="utf-8",
    )
    evidence_dir = root / "docs" / "evidence" / "2026-06-29-remote-closure"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    readme_lines = [
        "# Evidence: remote closure", "", "## Claim Ledger", "", "## Verification", "",
        "## Runtime Identity", "", "## Browser Verification", "", "## Adversarial / Quality Evidence", "",
        "## Anti-Brittleness Review", "", "## Remaining Risks", "",
        f"**Proof head:** {head or PROOF_HEAD}",
    ]
    readme_content = "\n".join(readme_lines) + "\n"
    (evidence_dir / "README.md").write_text(readme_content, encoding="utf-8")
    manifest: dict = {
        "schema": "projectstate.evidence_manifest.v1",
        "slice_id": "BL-REMOTE-CLOSURE-001",
        "manifest_status": "complete",
        "created_at": "2026-06-29T00:00:00+00:00",
        "repo": {"branch": BRANCH, "head": head},
        "runtime_identity": {"required": False, "path": "runtime_identity.json", "status": "not_applicable"},
        "claims": [
            {
                "id": "C1",
                "claim": "closure evidence is tracked",
                "status": "validated",
                "evidence": ["README.md"],
            }
        ],
        "artifacts": [
            {
                "path": "README.md",
                "kind": "doc",
                "sha256": hashlib.sha256(readme_content.encode("utf-8")).hexdigest(),
                "redaction_status": "checked",
                "sensitive_data": "none_found",
            }
        ],
        "redaction": {
            "status": "checked",
            "automated_scan": "passed",
            "manual_review": "completed",
            "known_limits": [],
        },
    }
    (evidence_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


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


def test_pr_body_proof_final_split_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root, head=PROOF_HEAD, final_head=LOCAL_HEAD)
        body = (
            f"- Proof head: {PROOF_HEAD}\n- Final PR head: {LOCAL_HEAD}\n"
            "- Evidence: docs/evidence/2026-06-29-remote-closure"
        )
        f = make_finalizer(root, github_data=None, body=body)
        assert f.run() == 0
        assert f.closure_label == "CI verified"


def test_changes_requested_or_unresolved_review_blocks_closure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        data = make_pr_data()
        pr = data["repository"]["byBranch"]["nodes"][0]
        pr["reviewDecision"] = "CHANGES_REQUESTED"
        pr["reviewThreads"] = {
            "nodes": [{"isResolved": False, "isOutdated": False}],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
        f = make_finalizer(root, github_data=data)
        assert f.run() == 1
        assert any("CHANGES_REQUESTED" in failure for failure in f.failures)
        assert any("unresolved" in failure for failure in f.failures)


def test_same_sha_on_different_pr_branch_fails_attribution() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        data = make_pr_data()
        data["repository"]["byBranch"]["nodes"][0]["headRefName"] = "other-branch"
        f = make_finalizer(root, github_data=data)
        assert f.run() == 1
        assert any("does not match current branch" in failure for failure in f.failures)


def test_review_and_check_suite_pagination_fail_closed() -> None:
    for connection in ("reviewThreads", "checkSuites"):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root)
            data = make_pr_data()
            if connection == "reviewThreads":
                data["repository"]["byBranch"]["nodes"][0][connection]["pageInfo"]["hasNextPage"] = True
            else:
                data["repository"]["object"][connection]["pageInfo"]["hasNextPage"] = True
            f = make_finalizer(root, github_data=data)
            assert f.run() == 1
            assert any("incomplete" in failure.lower() for failure in f.failures)


def test_unrelated_successful_actions_workflow_does_not_satisfy_ci() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        data = make_pr_data()
        suite = data["repository"]["object"]["checkSuites"]["nodes"][0]
        suite["workflowRun"]["file"]["path"] = ".github/workflows/unrelated.yml"
        f = make_finalizer(root, github_data=data)
        assert f.run() == 1
        assert any("authoritative" in failure.lower() for failure in f.failures)


def test_noop_or_wrong_level_standard_workflow_cannot_be_ci_proof() -> None:
    for command in (
        "echo success",
        "python3 scripts/projectstate_quality_gate.py --gate-level 1 --conformance",
        "python3 scripts/projectstate_quality_gate.py --gate-level 2",
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root)
            (root / ".github" / "workflows" / "validate.yml").write_text(
                "name: Validate\n"
                "on: {push: {}, pull_request: {}}\n"
                "jobs:\n"
                "  validate:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                f"      - run: {command}\n",
                encoding="utf-8",
            )
            f = make_finalizer(root, github_data=None)
            assert f.run() == 1
            assert any("quality gate" in failure.lower() for failure in f.failures)


def test_workflow_path_override_cannot_select_undeclared_workflow() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        unrelated = root / ".github" / "workflows" / "unrelated.yml"
        unrelated.write_text(
            "name: Other\njobs:\n  x:\n    steps:\n"
            "      - run: python3 scripts/projectstate_quality_gate.py --gate-level 2 --conformance\n",
            encoding="utf-8",
        )
        f = make_finalizer(root, github_data=None)
        f.workflow_path_arg = Path(".github/workflows/unrelated.yml")
        assert f.run() == 1
        assert any("not the declared" in failure.lower() for failure in f.failures)


def test_final_github_requery_detects_new_unresolved_thread() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        first = make_pr_data()
        second = make_pr_data()
        second_pr = second["repository"]["byBranch"]["nodes"][0]
        second_pr["reviewThreads"]["nodes"] = [
            {"isResolved": False, "isOutdated": False}
        ]
        api = SequenceGitHubApi([first, second])
        f = make_finalizer(root, github_data=first)
        f.github_client = api
        assert f.run() == 1
        assert api.calls == 2
        assert any("unresolved" in failure for failure in f.failures)


def test_lookalike_github_host_is_rejected() -> None:
    assert finalizer.parse_remote_url("https://evilgithub.com/owner/repo.git") is None
    assert finalizer.parse_remote_url("https://github.com/owner/repo.git") == ("owner", "repo")


def test_malformed_agent_context_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "agent.context"
        path.write_text(
            '{"schema":"projectstate.agent_context.v1","schema":"duplicate"}',
            encoding="utf-8",
        )
        with pytest.raises(finalizer.ContractError):
            finalizer.load_agent_context(path)


def test_clone_v2_agent_context_is_accepted() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "agent.context"
        path.write_text(
            json.dumps(
                {
                    "schema": "projectstate.agent_context.v2",
                    "agent_id": "integration-agent",
                    "slice_id": "BL-STATEDD-INTEGRATION-001",
                    "reservation_ref": "",
                    "worktree_path": "/tmp/integration",
                    "branch": "bl-projectstate-integration-001",
                    "base_branch": "bl-projectstate-integration-001",
                    "isolation_mode": "clone",
                }
            ),
            encoding="utf-8",
        )
        context = finalizer.load_agent_context(path)
        assert context["schema"] == "projectstate.agent_context.v2"
        assert context["reservation_ref"] == ""


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
        write_evidence(root, head="1" * 40)
        f = make_finalizer(root, github_data=None)
        assert f.run() == 1
        assert any("not an ancestor" in failure for failure in f.failures)


def test_evidence_proof_final_split_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root, head=PROOF_HEAD, final_head=LOCAL_HEAD)
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
        base = Path(tmp)
        root = base / "repo"
        root.mkdir()
        output = base / "closure.json"
        write_evidence(root)
        f = make_finalizer(root, github_data=None)
        f.output = output
        assert f.run() == 0
        assert output.exists()
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["local_head"] == LOCAL_HEAD
        assert data["closure_label"] == "CI verified"


def test_rejects_output_inside_repository() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None)
        f.output = root / "closure.json"
        assert f.run() == 1
        assert not (root / "closure.json").exists()


def test_missing_evidence_is_a_hard_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        f = make_finalizer(root, github_data=None)
        assert f.run() == 1
        assert any("evidence folder" in failure.lower() for failure in f.failures)


def test_invalid_or_headless_evidence_is_a_hard_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = root / "docs" / "evidence" / "invalid"
        evidence.mkdir(parents=True)
        (evidence / "README.md").write_text("# Invalid\n", encoding="utf-8")
        (evidence / "manifest.json").write_text(
            json.dumps({"schema": "projectstate.evidence_manifest.v1"}), encoding="utf-8"
        )
        body = (
            f"Proof head: {PROOF_HEAD}\nFinal PR head: {LOCAL_HEAD}\n"
            "Evidence: docs/evidence/invalid"
        )
        f = make_finalizer(root, github_data=None, body=body)
        assert f.run() == 1
        assert any("manifest" in failure.lower() for failure in f.failures)


def test_untracked_evidence_fails_exact_head_binding() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(root, github_data=None, tracked=False)
        assert f.run() == 1
        assert any("not tracked" in failure for failure in f.failures)


def test_evidence_branch_must_match_current_branch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        manifest_path = root / "docs" / "evidence" / "2026-06-29-remote-closure" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["repo"]["branch"] = "different-branch"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        f = make_finalizer(root, github_data=None)
        assert f.run() == 1
        assert any("does not match current branch" in failure for failure in f.failures)


def test_non_finalization_change_after_proof_head_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        f = make_finalizer(
            root,
            github_data=None,
            diff_paths=["scripts/changed_after_proof.py", "docs/evidence/2026-06-29-remote-closure/manifest.json"],
        )
        assert f.run() == 1
        assert any("non-finalization" in failure for failure in f.failures)


def test_finalization_metadata_secret_scan_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_evidence(root)
        (root / "STATUS.md").write_text('API_KEY="supersecretvalue"\n', encoding="utf-8")
        f = make_finalizer(
            root,
            github_data=None,
            diff_paths=[
                "STATUS.md",
                "docs/evidence/2026-06-29-remote-closure/manifest.json",
            ],
        )
        assert f.run() == 1
        assert any("privacy scan" in failure.lower() for failure in f.failures)


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
        test_missing_evidence_is_a_hard_failure,
        test_invalid_or_headless_evidence_is_a_hard_failure,
        test_untracked_evidence_fails_exact_head_binding,
        test_non_finalization_change_after_proof_head_fails,
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
