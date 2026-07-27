#!/usr/bin/env python3
"""Regression tests for scripts/projectstate_post_merge_verify.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFY_SCRIPT = ROOT / "scripts" / "projectstate_post_merge_verify.py"
sys.path.insert(0, str(ROOT / "scripts"))

from projectstate_post_merge_verify import PostMergeVerifier, run_command  # noqa: E402


def run_verify(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed.stdout.strip()


class FakeGitHub:
    def __init__(self, *, main_head: str, pr: dict[str, Any]):
        self.main_head = main_head
        self.pr = pr

    def query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        del variables
        if "defaultBranchRef" in query:
            return {
                "repository": {
                    "defaultBranchRef": {
                        "name": "main",
                        "target": {"oid": self.main_head},
                    }
                }
            }
        return {
            "repository": {
                "pullRequest": dict(self.pr),
                "object": {
                    "oid": self.main_head,
                    "statusCheckRollup": {"state": "SUCCESS"},
                    "checkSuites": {
                        "nodes": [
                            {
                                "databaseId": 991,
                                "status": "COMPLETED",
                                "conclusion": "SUCCESS",
                                "app": {"name": "GitHub Actions"},
                                "workflowRun": {
                                    "databaseId": 123456,
                                    "runNumber": 77,
                                    "url": "https://github.com/acme/repo/actions/runs/123456",
                                    "file": {"path": ".github/workflows/validate.yml"},
                                },
                            }
                        ],
                        "pageInfo": {"hasNextPage": False},
                    },
                },
            }
        }


def github_remote_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
    if args == ["git", "remote", "get-url", "origin"]:
        return 0, "https://github.com/acme/repo.git", ""
    return run_command(args, cwd)


def build_merged_scenario(
    root: Path,
    *,
    alter_squash: bool = False,
    advance_main: bool = False,
) -> dict[str, Any]:
    repo = root / "repo"
    remote = root / "remote.git"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "ProjectState Test")
    git(repo, "config", "user.email", "projectstate@example.invalid")

    (repo / "source.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", "source.txt")
    git(repo, "commit", "-m", "base")
    git(repo, "switch", "-c", "bl-one-pr")

    (repo / "source.txt").write_text("feature\n", encoding="utf-8")
    evidence = repo / "docs" / "evidence" / "one-pr"
    outputs = evidence / "command_outputs"
    outputs.mkdir(parents=True)
    test_output = outputs / "tests.txt"
    test_output.write_text("all focused tests passed\n", encoding="utf-8")
    git(repo, "add", "source.txt", "docs/evidence/one-pr/command_outputs/tests.txt")
    git(repo, "commit", "-m", "implementation proof")
    proof_head = git(repo, "rev-parse", "HEAD")

    readme = evidence / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# One-PR evidence",
                "",
                f"**Proof head:** {proof_head}",
                "**Final PR head:** intentionally owned by the mutable PR body.",
                "",
                "## Claims",
                "Claim: the implementation passed its focused regression.",
                "Evidence: `command_outputs/tests.txt`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    artifact_hash = hashlib.sha256(test_output.read_bytes()).hexdigest()
    manifest = {
        "schema": "projectstate.evidence_manifest.v1",
        "slice_id": "BL-ONE-PR-001",
        "manifest_status": "complete",
        "created_at": "2026-07-12T00:00:00+00:00",
        "repo": {"branch": "bl-one-pr", "head": proof_head},
        "claims": [
            {
                "id": "focused-regression",
                "claim": "The implementation passed its focused regression.",
                "status": "validated",
                "evidence": ["command_outputs/tests.txt"],
            }
        ],
        "artifacts": [
            {
                "path": "command_outputs/tests.txt",
                "kind": "command_output",
                "sha256": artifact_hash,
                "redaction_status": "checked",
                "sensitive_data": "none_found",
            }
        ],
        "redaction": {
            "status": "checked",
            "automated_scan": "passed",
            "manual_review": "completed",
        },
    }
    (evidence / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    git(repo, "add", "docs/evidence/one-pr")
    git(repo, "commit", "-m", "bind immutable evidence")
    pr_head = git(repo, "rev-parse", "HEAD")

    git(repo, "switch", "main")
    if advance_main:
        (repo / "main-only.txt").write_text("concurrent main change\n", encoding="utf-8")
        git(repo, "add", "main-only.txt")
        git(repo, "commit", "-m", "advance main independently")
    git(repo, "merge", "--squash", "bl-one-pr")
    if alter_squash:
        (repo / "source.txt").write_text("unexpected merge-time content\n", encoding="utf-8")
        git(repo, "add", "source.txt")
    git(repo, "commit", "-m", "squash one green PR")
    merge_commit = git(repo, "rev-parse", "HEAD")
    main_head = merge_commit

    git(root, "init", "--bare", str(remote))
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "origin", "main:refs/heads/main")
    git(repo, "push", "origin", "bl-one-pr:refs/pull/12/head")
    git(repo, "switch", "bl-one-pr")

    body = "\n".join(
        [
            "## Evidence refs",
            f"Proof head: {proof_head}",
            f"Final PR head: {pr_head}",
            "docs/evidence/one-pr",
        ]
    )
    pr = {
        "number": 12,
        "headRefOid": pr_head,
        "headRefName": "bl-one-pr",
        "baseRefName": "main",
        "mergeCommit": {"oid": merge_commit},
        "merged": True,
        "state": "MERGED",
        "body": body,
        "mergeStateStatus": "MERGED",
        "url": "https://github.com/acme/repo/pull/12",
    }
    return {
        "repo": repo,
        "evidence": evidence,
        "proof_head": proof_head,
        "pr_head": pr_head,
        "merge_commit": merge_commit,
        "main_head": main_head,
        "pr": pr,
    }


def verifier_for(scenario: dict[str, Any], output: Path | None = None) -> PostMergeVerifier:
    return PostMergeVerifier(
        root=scenario["repo"],
        pr_number=12,
        expected_pr_head=scenario["pr_head"],
        evidence_folder_arg=Path("docs/evidence/one-pr"),
        output=output,
        github_client=FakeGitHub(main_head=scenario["main_head"], pr=scenario["pr"]),
        run_command_fn=github_remote_command,
    )


def test_help_runs() -> None:
    completed = run_verify(["--help"])
    assert completed.returncode == 0, completed.stderr
    assert "expected-pr-head" in completed.stdout
    assert "evidence-folder" in completed.stdout


def test_missing_required_bindings_fails_cli() -> None:
    completed = run_verify(["--pr-number", "12"])
    assert completed.returncode == 2, completed.stderr


def test_one_green_squash_pr_closes_without_metadata_followup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        scenario = build_merged_scenario(root)
        handoff = root / "post-merge-handoff.json"
        verifier = verifier_for(scenario, handoff)

        assert verifier.run() == 0, verifier.failures
        payload = json.loads(handoff.read_text(encoding="utf-8"))
        assert payload["status"] == "verified"
        assert payload["pull_request"]["merge_commit"] == scenario["merge_commit"]
        assert payload["default_branch"]["head"] == scenario["main_head"]
        assert payload["evidence"]["proof_tree"]
        assert payload["evidence"]["content_identity_method"] == "source_tree_equal"

        tracked = (
            scenario["evidence"] / "manifest.json"
        ).read_text(encoding="utf-8") + (
            scenario["evidence"] / "README.md"
        ).read_text(encoding="utf-8")
        assert scenario["merge_commit"] not in tracked
        assert not (scenario["evidence"] / "closure.json").exists()
        assert git(scenario["repo"], "status", "--short") == ""

        # A rerun observes the already-merged PR and reproduces the same truth.
        rerun = verifier_for(scenario, handoff)
        assert rerun.run() == 0, rerun.failures
        repeated = json.loads(handoff.read_text(encoding="utf-8"))
        assert repeated["pull_request"] == payload["pull_request"]
        assert repeated["default_branch"] == payload["default_branch"]
        assert repeated["evidence"] == payload["evidence"]


def test_content_changed_during_squash_fails_equivalence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        scenario = build_merged_scenario(Path(tmp), alter_squash=True)
        verifier = verifier_for(scenario)
        assert verifier.run() == 1
        assert any("neither source-tree-equal nor stable-patch-equivalent" in item for item in verifier.failures)


def test_squash_after_unrelated_main_advance_uses_patch_equivalence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        scenario = build_merged_scenario(Path(tmp), advance_main=True)
        verifier = verifier_for(scenario)
        assert verifier.run() == 0, verifier.failures
        assert verifier.content_identity_method == "stable_patch_equal"


def test_pr_body_must_bind_exact_final_head() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        scenario = build_merged_scenario(Path(tmp))
        scenario["pr"]["body"] = scenario["pr"]["body"].replace(
            scenario["pr_head"], "f" * 40
        )
        verifier = verifier_for(scenario)
        assert verifier.run() == 1
        assert any("PR body final head" in item for item in verifier.failures)


def test_tracked_closure_must_not_predict_future_merge_identity() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        scenario = build_merged_scenario(Path(tmp))
        closure = scenario["evidence"] / "closure.json"
        closure.write_text(
            json.dumps({"merge_commit_sha": scenario["merge_commit"]}) + "\n",
            encoding="utf-8",
        )
        git(scenario["repo"], "add", "docs/evidence/one-pr/closure.json")
        git(scenario["repo"], "commit", "-m", "bad future identity")
        bad_head = git(scenario["repo"], "rev-parse", "HEAD")
        # This focused check exercises the tracked-artifact rule without
        # pretending the earlier merged PR had this later commit as its head.
        verifier = verifier_for(scenario)
        verifier.local_head = bad_head
        verifier.evidence_folder = scenario["evidence"]
        verifier.proof_head = scenario["proof_head"]
        verifier._check_tracked_evidence()
        assert any("future post-merge identity" in item for item in verifier.failures)


if __name__ == "__main__":
    tests = [
        test_help_runs,
        test_missing_required_bindings_fails_cli,
        test_one_green_squash_pr_closes_without_metadata_followup,
        test_content_changed_during_squash_fails_equivalence,
        test_squash_after_unrelated_main_advance_uses_patch_equivalence,
        test_pr_body_must_bind_exact_final_head,
        test_tracked_closure_must_not_predict_future_merge_identity,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
