#!/usr/bin/env python3
"""Focused fake-provider regressions for the agent-owned finish state machine."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from statedd_finish_slice import (  # noqa: E402
    CiObservation,
    DefaultBranchSnapshot,
    DeliveryPolicy,
    FinishRefused,
    FinishSlice,
    LocalTruth,
    MergeResult,
    PostMergeProof,
    PullRequestSnapshot,
    RemoteClosureProof,
    Stage,
    load_policy,
)
from statedd_validate_schema import validate_json_schema  # noqa: E402


HEAD = "1" * 40
PROOF = "2" * 40
MERGE = "3" * 40
EVIDENCE_REF = "docs/evidence/slice-proof"


def ci(state: str = "SUCCESS", *, subject: str = HEAD, name: str = "branch-head") -> CiObservation:
    return CiObservation(
        state=state,
        subject_sha=subject,
        run_id="101",
        run_url="https://example.invalid/actions/runs/101",
        workflow_path=".github/workflows/validate.yml",
        check_name=name,
    )


def pr_snapshot(**changes: object) -> PullRequestSnapshot:
    value = PullRequestSnapshot(
        number=17,
        url="https://example.invalid/pull/17",
        state="OPEN",
        head=HEAD,
        branch="slice-branch",
        base_branch="main",
        draft=False,
        review_decision=None,
        unresolved_threads=0,
        merge_state="CLEAN",
        proof_head=PROOF,
        final_pr_head=HEAD,
        evidence_ref=EVIDENCE_REF,
        branch_head_ci=ci(),
        merge_candidate_ci=ci(name="merge-candidate"),
        merge_commit=None,
    )
    return replace(value, **changes)


def policy(*, mode: str = "agent_after_green", confirmed: bool = True) -> DeliveryPolicy:
    return DeliveryPolicy(
        status="confirmed" if confirmed else "proposed_default",
        confirmation="human_confirmed" if confirmed else "pending_during_bootstrap",
        mode=mode,
    )


class FakeLocal:
    def __init__(self, root: Path, events: list[str]) -> None:
        self.root = root
        self.events = events
        self.pushes: list[tuple[str, str]] = []
        self.failures: list[tuple[str, str]] = []
        self.default_head = MERGE

    def validate(self, expected_head: str, evidence_folder: Path) -> LocalTruth:
        self.events.append("local-proof")
        assert expected_head == HEAD
        return LocalTruth(
            root=self.root,
            branch="slice-branch",
            head=HEAD,
            evidence_folder=self.root / EVIDENCE_REF,
            evidence_ref=EVIDENCE_REF,
            agent_id="agent-test",
            slice_id="BL-TEST",
        )

    def authorize_remote(self, operation: str) -> None:
        self.events.append(f"authorize:{operation}")

    def push_exact(self, branch: str, expected_head: str) -> None:
        self.events.append("push")
        self.pushes.append((branch, expected_head))

    def remote_closure(
        self, pr_number: int, expected_head: str, evidence_folder: Path, output: Path
    ) -> RemoteClosureProof:
        self.events.append("remote-closure")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("{}\n", encoding="utf-8")
        return RemoteClosureProof(
            head=expected_head,
            proof_head=PROOF,
            evidence_ref=EVIDENCE_REF,
            ci_run_id="101",
            output=output,
        )

    def fetch_default_branch(self, branch: str) -> str:
        self.events.append("fetch-main")
        assert branch == "main"
        return self.default_head

    def post_merge_verify(
        self,
        pr_number: int,
        expected_head: str,
        evidence_folder: Path,
        output: Path,
    ) -> PostMergeProof:
        self.events.append("post-merge-verify")
        payload = {"result": "passed", "expected_pr_head": expected_head}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload), encoding="utf-8")
        return PostMergeProof(output=output, payload=payload)

    def release_isolation(self) -> None:
        self.events.append("release")

    def record_remote_failure(self, operation: str, diagnostic: str) -> None:
        self.events.append(f"record-failure:{operation}")
        self.failures.append((operation, diagnostic))


class FakeProvider:
    def __init__(self, snapshot: PullRequestSnapshot, events: list[str]) -> None:
        self.snapshot = snapshot
        self.events = events
        self.merge_calls: list[tuple[int, str, str]] = []
        self.mark_ready_calls = 0
        self.delete_calls = 0
        self.branch_exists = True
        self.merge_failure: str | None = None
        self.main = DefaultBranchSnapshot("main", MERGE, ci(subject=MERGE))

    def pull_request(self, number: int) -> PullRequestSnapshot:
        self.events.append("query-pr")
        assert number == 17
        return self.snapshot

    def mark_ready(self, number: int) -> None:
        self.events.append("mark-ready")
        self.mark_ready_calls += 1
        self.snapshot = replace(self.snapshot, draft=False)

    def merge(self, number: int, expected_head: str, method: str) -> MergeResult:
        self.events.append("merge")
        self.merge_calls.append((number, expected_head, method))
        if self.merge_failure:
            raise FinishRefused(self.merge_failure)
        self.snapshot = replace(self.snapshot, state="MERGED", merge_state="MERGED", merge_commit=MERGE)
        return MergeResult(True, MERGE, "merged")

    def default_branch(self) -> DefaultBranchSnapshot:
        self.events.append("query-main")
        return self.main

    def delete_branch(self, branch: str, expected_head: str) -> bool:
        self.events.append("delete-branch")
        self.delete_calls += 1
        assert branch == "slice-branch"
        assert expected_head == HEAD
        existed = self.branch_exists
        self.branch_exists = False
        return existed


def build(
    tmp_path: Path,
    *,
    snapshot: PullRequestSnapshot | None = None,
    delivery_policy: DeliveryPolicy | None = None,
    pr_timeout: float = 0,
    main_timeout: float = 0,
) -> tuple[FinishSlice, FakeLocal, FakeProvider, list[str], Path]:
    root = tmp_path / "repo"
    root.mkdir()
    events: list[str] = []
    local = FakeLocal(root, events)
    provider = FakeProvider(snapshot or pr_snapshot(), events)
    output = tmp_path / "handoff.json"
    finish = FinishSlice(
        local=local,
        provider=provider,
        policy=delivery_policy or policy(),
        pr_number=17,
        expected_head=HEAD,
        evidence_folder=Path(EVIDENCE_REF),
        handoff_output=output,
        pr_ci_timeout=pr_timeout,
        main_ci_timeout=main_timeout,
        poll_interval=0,
    )
    return finish, local, provider, events, output


def test_confirmed_agent_after_green_exact_head_merge_completes(tmp_path: Path) -> None:
    finish, _, provider, events, output = build(tmp_path)
    assert finish.run() == 0
    assert finish.report.status == Stage.HANDOFF_COMPLETE.value
    assert provider.merge_calls == [(17, HEAD, "squash")]
    assert events.index("remote-closure") < events.index("merge")
    assert output.exists()


def test_human_merge_policy_refuses_automatic_merge(tmp_path: Path) -> None:
    finish, local, provider, _, _ = build(tmp_path, delivery_policy=policy(mode="human_merge"))
    assert finish.run() == 1
    assert "human_merge" in (finish.report.failure or "")
    assert not local.pushes
    assert not provider.merge_calls


def test_unconfirmed_policy_refuses_automatic_merge(tmp_path: Path) -> None:
    finish, local, provider, _, _ = build(tmp_path, delivery_policy=policy(confirmed=False))
    assert finish.run() == 1
    assert "confirmed" in (finish.report.failure or "")
    assert not local.pushes
    assert not provider.merge_calls


def test_policy_loader_refuses_missing_protected_operation_guards(tmp_path: Path) -> None:
    payload = {
        "delivery_policy": {
            "status": "confirmed",
            "confirmation": "human_confirmed",
            "merge": {
                "mode": "agent_after_green",
                "method": "squash",
                "delete_branch_after_verification": True,
                "require_exact_pr_head": True,
                "require_clean_merge_state": True,
                "require_no_requested_changes": True,
                "require_no_unresolved_review_threads": True,
                "require_branch_head_ci": True,
                "require_merge_candidate_ci": True,
                "require_remote_closure": True,
                "require_post_merge_main_ci": True,
            },
            "protected_operations": {
                "force_push": "allowed",
                "rewrite_shared_history": "forbidden",
            },
            "ci_unavailable": {
                "automatic_merge": "forbidden",
                "override": "requires_separate_explicit_human_authorization",
            },
        }
    }
    source = tmp_path / "policy.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FinishRefused, match="force-push"):
        load_policy(source)


@pytest.mark.parametrize("state", ["PENDING", "FAILURE"])
def test_non_green_branch_head_ci_blocks_merge(tmp_path: Path, state: str) -> None:
    snapshot = pr_snapshot(branch_head_ci=ci(state))
    finish, _, provider, _, _ = build(tmp_path, snapshot=snapshot)
    assert finish.run() == 1
    assert "branch-head" in (finish.report.failure or "")
    assert not provider.merge_calls


@pytest.mark.parametrize("state", ["PENDING", "FAILURE"])
def test_non_green_merge_candidate_ci_blocks_merge(tmp_path: Path, state: str) -> None:
    snapshot = pr_snapshot(merge_candidate_ci=ci(state, name="merge-candidate"))
    finish, _, provider, _, _ = build(tmp_path, snapshot=snapshot)
    assert finish.run() == 1
    assert "merge-candidate" in (finish.report.failure or "")
    assert not provider.merge_calls


def test_draft_is_made_ready_only_after_local_proof(tmp_path: Path) -> None:
    finish, _, provider, events, _ = build(tmp_path, snapshot=pr_snapshot(draft=True))
    assert finish.run() == 0
    assert provider.mark_ready_calls == 1
    assert events.index("local-proof") < events.index("mark-ready")
    assert events.index("push") < events.index("mark-ready")


def test_requested_changes_block_merge(tmp_path: Path) -> None:
    finish, _, provider, _, _ = build(
        tmp_path, snapshot=pr_snapshot(review_decision="CHANGES_REQUESTED")
    )
    assert finish.run() == 1
    assert "CHANGES_REQUESTED" in (finish.report.failure or "")
    assert not provider.merge_calls


def test_unresolved_current_review_threads_block_merge(tmp_path: Path) -> None:
    finish, _, provider, _, _ = build(tmp_path, snapshot=pr_snapshot(unresolved_threads=2))
    assert finish.run() == 1
    assert "unresolved" in (finish.report.failure or "")
    assert not provider.merge_calls


def test_dirty_merge_state_blocks_merge(tmp_path: Path) -> None:
    finish, _, provider, _, _ = build(tmp_path, snapshot=pr_snapshot(merge_state="DIRTY"))
    assert finish.run() == 1
    assert "merge state" in (finish.report.failure or "")
    assert not provider.merge_calls


def test_unexpected_pr_head_movement_blocks_push_and_merge(tmp_path: Path) -> None:
    finish, local, provider, _, _ = build(tmp_path, snapshot=pr_snapshot(head="9" * 40))
    assert finish.run() == 1
    assert "unexpected PR-head movement" in (finish.report.failure or "")
    assert not local.pushes
    assert not provider.merge_calls


def test_non_default_pr_base_blocks_merge(tmp_path: Path) -> None:
    finish, local, provider, _, _ = build(
        tmp_path, snapshot=pr_snapshot(base_branch="release-candidate")
    )
    assert finish.run() == 1
    assert "not the provider default branch" in (finish.report.failure or "")
    assert not local.pushes
    assert not provider.merge_calls


def test_merge_api_failure_retains_branch_and_isolation(tmp_path: Path) -> None:
    finish, local, provider, events, _ = build(tmp_path)
    provider.merge_failure = "expected-head merge rejected"
    assert finish.run() == 1
    assert provider.branch_exists is True
    assert provider.delete_calls == 0
    assert "release" not in events
    assert local.failures and local.failures[-1][0] == "expected-head pull-request merge"
    assert finish.report.status == Stage.REMOTE_CLOSURE_VERIFIED.value


def test_main_ci_failure_reports_merged_but_not_verified_and_retains_state(tmp_path: Path) -> None:
    finish, _, provider, events, _ = build(tmp_path)
    provider.main = DefaultBranchSnapshot("main", MERGE, ci("FAILURE", subject=MERGE))
    assert finish.run() == 1
    assert finish.report.status == Stage.MERGED.value
    assert finish.report.merge_commit == MERGE
    assert finish.report.post_merge_verified is False
    assert provider.delete_calls == 0
    assert "release" not in events


def test_rerun_after_existing_merge_is_idempotent(tmp_path: Path) -> None:
    merged = pr_snapshot(state="MERGED", merge_state="MERGED", merge_commit=MERGE)
    finish, local, provider, events, _ = build(tmp_path, snapshot=merged)
    provider.branch_exists = False
    assert finish.run() == 0
    assert not local.pushes
    assert not provider.merge_calls
    assert provider.delete_calls == 1
    assert finish.report.status == Stage.HANDOFF_COMPLETE.value
    assert "post-merge-verify" in events


def test_branch_deletion_and_release_follow_post_merge_verification(tmp_path: Path) -> None:
    finish, _, _, events, _ = build(tmp_path)
    assert finish.run() == 0
    assert events.index("post-merge-verify") < events.index("delete-branch")
    assert events.index("delete-branch") < events.index("release")


def test_final_external_handoff_records_remote_first_truth(tmp_path: Path) -> None:
    finish, _, _, _, output = build(tmp_path)
    assert finish.run() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "HANDOFF_COMPLETE"
    assert payload["expected_pr_head"] == HEAD
    assert payload["merge_commit"] == MERGE
    assert payload["default_branch_head"] == MERGE
    assert payload["post_merge_verified"] is True
    assert payload["remote_branch_absent"] is True
    assert payload["isolation_released"] is True
    assert payload["recoverable_state_retained"] is False


def test_final_external_handoff_is_machine_checkable(tmp_path: Path) -> None:
    finish, _, _, _, output = build(tmp_path)
    assert finish.run() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    schema = json.loads(
        (SCRIPTS.parent / "schemas" / "finish_slice_handoff.schema.json").read_text(encoding="utf-8")
    )
    assert validate_json_schema(payload, schema) == []
    del payload["merge_commit"]
    issues = validate_json_schema(payload, schema)
    assert any("merge_commit" in issue.message for issue in issues)


def test_legacy_close_help_names_pre_merge_boundary() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "statedd_agent_worktree.py"), "close", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "Deprecated pre-merge" in completed.stdout
    assert "statedd_finish_slice.py" in completed.stdout
