#!/usr/bin/env python3
"""End-to-end regression for the agent-operated downstream golden path."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

try:
    from scripts.projectstate_finish_slice import (
        CiObservation,
        DefaultBranchSnapshot,
        DeliveryPolicy,
        FinishSlice,
        IsolationRelease,
        LocalTruth,
        MergeResult,
        PostMergeProof,
        PullRequestSnapshot,
        RemoteClosureProof,
        Stage,
    )
    from scripts.projectstate_validate_schema import parse_yaml_text
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from projectstate_finish_slice import (
        CiObservation,
        DefaultBranchSnapshot,
        DeliveryPolicy,
        FinishSlice,
        IsolationRelease,
        LocalTruth,
        MergeResult,
        PostMergeProof,
        PullRequestSnapshot,
        RemoteClosureProof,
        Stage,
    )
    from projectstate_validate_schema import parse_yaml_text


ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], cwd: Path, *, expected: int = 0) -> str:
    environment = os.environ.copy()
    environment.setdefault(
        "STATEDD_WORKSPACE_ROOT",
        str(cwd.parent / ".projectstate-test-workspaces"),
    )
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != expected:
        raise AssertionError(
            f"Command failed: {' '.join(args)}\n"
            f"expected={expected} actual={completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout.strip()


def git(repo: Path, *args: str, expected: int = 0) -> str:
    return run(["git", *args], repo, expected=expected)


def commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def start_agent(repo: Path, slice_id: str, agent_id: str) -> tuple[Path, str]:
    output = run(
        [
            sys.executable,
            str(repo / "scripts" / "projectstate_agent_worktree.py"),
            "--repo",
            str(repo),
            "start",
            "--slice-id",
            slice_id,
            "--agent-id",
            agent_id,
        ],
        repo,
    )
    line = next(line for line in output.splitlines() if line.startswith("Agent clone ready:"))
    clone = Path(line.split(":", 1)[1].strip())
    context = json.loads((clone / ".projectstate" / "agent.context").read_text(encoding="utf-8"))
    git(clone, "config", "user.email", f"{agent_id}@example.invalid")
    git(clone, "config", "user.name", f"ProjectState {agent_id}")
    return clone, context["branch"]


def test_golden_path() -> None:
    with tempfile.TemporaryDirectory(prefix="projectstate-golden-path-") as tmp:
        root = Path(tmp)
        template_clone = root / "template-source"
        downstream = root / "downstream"
        remote = root / "downstream.git"

        # Exercise the public materialization shape: a temporary template clone
        # is the source, and the downstream target starts without Git metadata.
        run(["git", "clone", "--no-local", str(ROOT), str(template_clone)], root)
        # Keep the regression runnable before the maintainer commits the slice:
        # a real public clone is clean, while this local test may contain the
        # candidate changes that the clone must exercise.
        changed = set(git(ROOT, "diff", "--name-only", "HEAD").splitlines())
        changed.update(git(ROOT, "ls-files", "--others", "--exclude-standard").splitlines())
        for relpath in changed:
            source = ROOT / relpath
            destination = template_clone / relpath
            if source.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        source_head = git(template_clone, "rev-parse", "HEAD")
        run(
            [
                sys.executable,
                str(template_clone / "scripts" / "init_template.py"),
                "new",
                "--name",
                "Golden Path Demo",
                "--profile",
                "team",
                "--target",
                str(downstream),
            ],
            template_clone,
        )

        if not (downstream / ".git").is_dir():
            raise AssertionError("new-project materialization did not initialize Git metadata")
        if git(downstream, "branch", "--show-current") != "main":
            raise AssertionError("new-project materialization did not initialize main")
        for required_finish_asset in (
            "scripts/projectstate_finish_slice.py",
            "scripts/projectstate_post_merge_verify.py",
            "schemas/finish_slice_handoff.schema.json",
        ):
            if not (downstream / required_finish_asset).is_file():
                raise AssertionError(f"team profile omitted finish asset: {required_finish_asset}")
        workflow_text = (
            downstream / ".github" / "workflows" / "projectstate-validate.yml"
        ).read_text(encoding="utf-8")
        for required_subject in ("branch-head:", "merge-candidate:"):
            if required_subject not in workflow_text:
                raise AssertionError(f"generated CI omitted subject: {required_subject}")
        inherited = subprocess.run(
            ["git", "cat-file", "-e", f"{source_head}^{{commit}}"],
            cwd=downstream,
            capture_output=True,
            text=True,
            check=False,
        )
        if inherited.returncode == 0:
            raise AssertionError("downstream repository inherited template Git history")
        for forbidden in (
            "scripts/test_init_template.py",
            "fixtures",
            "docs/evidence",
            "docs/incidents/20260711-141533-git-object-ownership-permission.md",
        ):
            candidate = downstream / forbidden
            leaked = candidate.is_file() or (
                candidate.is_dir()
                and any(path.is_file() and path.name != ".gitkeep" for path in candidate.rglob("*"))
            )
            if leaked:
                raise AssertionError(f"template-maintenance payload leaked: {forbidden}")

        run([sys.executable, str(downstream / "scripts" / "projectstate_validate_schema.py"), str(downstream)], downstream)
        run([sys.executable, str(downstream / "scripts" / "check_state_docs.py"), str(downstream)], downstream)

        # Bootstrap is a structured contract, not a string-replacement shortcut.
        answers_path = root / "bootstrap-answers.json"
        answers_path.write_text(
            json.dumps(
                {
                    "project_name": "Golden Path Demo",
                    "purpose": "Prove a truthful, recoverable coding-agent delivery loop.",
                    "primary_user": "CTO and coding agent",
                    "architecture": "Template initializer plus canonical YAML state, executable gates, and isolated Git agents.",
                    "constraints": [
                        "No inherited template Git history",
                        "No writes through symlinked roots",
                        "Confirmed delivery policy controls merge; human controls acceptance",
                    ],
                    "first_milestone": "Complete the bootstrap baseline and integrate two bounded agent commits.",
                    "backlog": [
                        {
                            "id": "BL-GOLDEN-PATH-001",
                            "title": "Complete the coding-agent golden path",
                            "priority": "P0",
                            "next": "Run the structured bootstrap and isolated-agent regression.",
                            "exit": "Bootstrap and integration evidence validate strictly.",
                        },
                        {
                            "id": "BL-AGENT-ISOLATION-001",
                            "title": "Keep independent agents on isolated clones",
                            "priority": "P1",
                            "next": "Return bounded commits from two independent clones.",
                            "exit": "Both commits integrate without shared object-database ambiguity.",
                        },
                        {
                            "id": "BL-BOOTSTRAP-EVIDENCE-001",
                            "title": "Record a truthful bootstrap evidence pack",
                            "priority": "P1",
                            "next": "Generate and strictly validate proportional evidence.",
                            "exit": "Evidence claim, artifact hash, and redaction status agree.",
                        },
                    ],
                    "active_queue": [
                        {
                            "id": "BL-GOLDEN-PATH-001",
                            "priority": "P0",
                            "owner": "integration agent",
                            "next": "Complete bootstrap and integrate the bounded agent commits.",
                            "exit": "Whole-project gate and strict evidence pack pass.",
                        }
                    ],
                    "delivery_policy": {
                        "confirmation": "human_confirmed",
                        "merge": {
                            "mode": "agent_after_green",
                            "method": "squash",
                        },
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        run(
            [sys.executable, str(downstream / "scripts" / "check_state_docs.py"), str(downstream), "--bootstrap-gate"],
            downstream,
            expected=1,
        )
        run(
            [
                sys.executable,
                str(downstream / "scripts" / "projectstate_bootstrap_apply.py"),
                "--repo",
                str(downstream),
                "--answers",
                str(answers_path),
            ],
            downstream,
        )
        run([sys.executable, str(downstream / "scripts" / "check_state_docs.py"), str(downstream), "--bootstrap-gate"], downstream)
        state = parse_yaml_text((downstream / "PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        project = state["current_state"]["project"]
        if project["purpose"] != "Prove a truthful, recoverable coding-agent delivery loop.":
            raise AssertionError("structured bootstrap purpose did not reach canonical project state")
        if project["primary_user"] != "CTO and coding agent":
            raise AssertionError("structured bootstrap primary user did not reach canonical project state")
        if state["delivery_policy"]["confirmation"] != "human_confirmed":
            raise AssertionError("structured delivery policy was not confirmed")
        if state["delivery_policy"]["merge"]["mode"] != "agent_after_green":
            raise AssertionError("structured delivery policy merge mode did not round-trip")

        git(downstream, "config", "user.email", "projectstate-golden@example.invalid")
        git(downstream, "config", "user.name", "ProjectState Golden Path")
        git(root, "init", "--bare", str(remote))
        git(downstream, "remote", "add", "origin", str(remote))
        commit(downstream, "bootstrap: establish golden-path baseline")
        git(downstream, "push", "-u", "origin", "main")
        git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
        git(downstream, "remote", "set-head", "origin", "main")

        agent_a, branch_a = start_agent(downstream, "BL-GOLDEN-PATH-001", "agent-a111")
        agent_b, branch_b = start_agent(downstream, "BL-GOLDEN-PATH-001", "agent-b222")
        (agent_a / "subagent-a.txt").write_text("independent package A\n", encoding="utf-8")
        (agent_b / "subagent-b.txt").write_text("independent package B\n", encoding="utf-8")
        commit_a = commit(agent_a, "feat: integrate package A")
        commit_b = commit(agent_b, "feat: integrate package B")
        git(agent_a, "push", "origin", f"HEAD:refs/heads/{branch_a}")
        git(agent_b, "push", "origin", f"HEAD:refs/heads/{branch_b}")

        integration_branch = "bl-golden-path-001-integration"
        git(downstream, "switch", "-c", integration_branch)
        git(downstream, "fetch", "origin", branch_a, branch_b)
        git(downstream, "merge", "--no-ff", "--no-edit", f"origin/{branch_a}")
        git(downstream, "merge", "--no-ff", "--no-edit", f"origin/{branch_b}")
        integration_result = root / "integration-result.json"
        integration_result.write_text(
            json.dumps(
                {
                    "status": "complete",
                    "commit_count": 2,
                    "working_tree_clean": True,
                    "agent_scope_respected": True,
                    "conflicts_resolved": 0,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        run(
            [
                sys.executable,
                str(downstream / "scripts" / "projectstate_bootstrap_apply.py"),
                "--repo",
                str(downstream),
                "--integration-result",
                str(integration_result),
            ],
            downstream,
        )
        manifest = json.loads((downstream / "PROJECTSTATE_ASSETS.json").read_text(encoding="utf-8"))
        required_gate = manifest["required_gate_level"]
        run(
            [
                sys.executable,
                str(downstream / "scripts" / "projectstate_quality_gate.py"),
                "--gate-level",
                str(required_gate),
                "--conformance",
            ],
            downstream,
        )
        integration_head = commit(downstream, "chore: record integrated ProjectState truth")
        git(downstream, "push", "-u", "origin", f"HEAD:refs/heads/{integration_branch}")

        evidence_dir = downstream / "docs" / "evidence" / "golden-path-integration"
        run(
            [
                sys.executable,
                str(downstream / "scripts" / "projectstate_evidence_pack.py"),
                "init",
                str(evidence_dir),
                "--repo",
                str(downstream),
                "--slice-id",
                "BL-GOLDEN-PATH-001",
            ],
            downstream,
        )
        artifact = evidence_dir / "verification.txt"
        artifact.write_text(
            "structured bootstrap passed; isolated agent commits integrated; local gate passed; remote parity checked\n",
            encoding="utf-8",
        )
        evidence_manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
        evidence_manifest.update(
            {
                "manifest_status": "complete",
                "repo": {"branch": integration_branch, "head": integration_head},
                "runtime_identity": {"required": False, "path": "runtime_identity.json", "status": "not_applicable"},
                "claims": [
                    {
                        "id": "bootstrap-and-integration",
                        "claim": "The structured bootstrap and isolated-agent integration path completed.",
                        "status": "validated",
                        "evidence": ["verification.txt"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "verification.txt",
                        "kind": "command_output",
                        "sha256": None,
                        "redaction_status": "unchecked",
                        "sensitive_data": "unknown",
                    }
                ],
                "redaction": {
                    "status": "checked_with_limits",
                    "automated_scan": "passed",
                    "manual_review": "completed",
                    "known_limits": ["Automated scan is conservative and does not prove absence of secrets."],
                },
            }
        )
        (evidence_dir / "manifest.json").write_text(json.dumps(evidence_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        run([sys.executable, str(downstream / "scripts" / "projectstate_evidence_pack.py"), "hash", str(evidence_dir)], downstream)
        run([sys.executable, str(downstream / "scripts" / "projectstate_evidence_pack.py"), "scan", str(evidence_dir)], downstream)
        evidence_manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
        evidence_manifest["redaction"]["manual_review"] = "completed"
        evidence_manifest["redaction"]["status"] = "checked_with_limits"
        (evidence_dir / "manifest.json").write_text(json.dumps(evidence_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        run([sys.executable, str(downstream / "scripts" / "projectstate_evidence_pack.py"), "check", "--strict", str(evidence_dir)], downstream)
        integration_head = commit(downstream, "chore: finalize golden-path evidence")
        git(downstream, "push", "-u", "origin", f"HEAD:refs/heads/{integration_branch}")

        remote_head = git(remote, "show-ref", "--hash", f"refs/heads/{integration_branch}")
        if remote_head != integration_head:
            raise AssertionError("final remote integration branch does not contain exact local HEAD")
        if commit_a not in git(downstream, "log", "--all", "--format=%H"):
            raise AssertionError("integration branch does not contain subagent A commit")
        if commit_b not in git(downstream, "log", "--all", "--format=%H"):
            raise AssertionError("integration branch does not contain subagent B commit")
        if git(downstream, "status", "--short"):
            raise AssertionError("golden-path integration worktree is not clean")

        handoff = run(
            [
                sys.executable,
                str(downstream / "scripts" / "projectstate_handoff.py"),
                "--repo",
                str(downstream),
                "--no-include-listeners",
            ],
            downstream,
        )
        for phrase in (
            "## Remote-First Status",
            f"- exact local HEAD: {integration_head}",
            f"- remote branch HEAD: {integration_head}",
            "- remote contains exact local HEAD: yes",
            "- delivery status: pushed",
        ):
            if phrase not in handoff:
                raise AssertionError(f"handoff is missing remote proof: {phrase}")

        # Continue the same journey through the provider boundary with a
        # deterministic fake. Unit tests exercise every failure branch; this
        # end-to-end regression proves that the materialized team policy and
        # real bootstrap/integration evidence feed the authoritative finish
        # state machine without any human Git or follow-up metadata action.
        merge_commit = "f" * 40
        events: list[str] = []

        class GoldenLocal:
            def validate(self, expected_head: str, evidence_folder: Path) -> LocalTruth:
                events.append("local-validated")
                if expected_head != integration_head or not evidence_dir.is_dir():
                    raise AssertionError("finish inputs do not bind the integrated proof")
                return LocalTruth(
                    root=downstream,
                    branch=integration_branch,
                    head=integration_head,
                    evidence_folder=evidence_dir,
                    evidence_ref="docs/evidence/golden-path-integration",
                    agent_id="integration-agent",
                    slice_id="BL-GOLDEN-PATH-001",
                )

            def authorize_remote(self, operation: str) -> None:
                events.append(f"authorized:{operation}")

            def push_exact(self, branch: str, expected_head: str) -> None:
                events.append("exact-head-pushed")
                if git(remote, "show-ref", "--hash", f"refs/heads/{branch}") != expected_head:
                    raise AssertionError("fake provider saw a different pushed head")

            def remote_closure(
                self, pr_number: int, expected_head: str, evidence_folder: Path, output: Path
            ) -> RemoteClosureProof:
                events.append("remote-closure-verified")
                output.write_text("{}\n", encoding="utf-8")
                return RemoteClosureProof(
                    head=expected_head,
                    proof_head=integration_head,
                    evidence_ref="docs/evidence/golden-path-integration",
                    ci_run_id="501",
                    output=output,
                )

            def fetch_default_branch(self, branch: str) -> str:
                events.append("default-branch-fetched")
                return merge_commit

            def post_merge_verify(
                self,
                pr_number: int,
                expected_head: str,
                evidence_folder: Path,
                output: Path,
            ) -> PostMergeProof:
                events.append("post-merge-verified")
                payload = {"schema": "projectstate.post_merge_handoff.v1", "status": "verified"}
                output.write_text(json.dumps(payload), encoding="utf-8")
                return PostMergeProof(output=output, payload=payload)

            def release_isolation(self) -> IsolationRelease:
                events.append("isolation-released")
                return IsolationRelease(
                    released=True,
                    isolation_mode="clone",
                    disposition="quarantined",
                    original_path=str(downstream),
                    original_path_absent=True,
                    quarantine_path=str(root / "quarantine"),
                    recoverable_state_retained=True,
                    branch=integration_branch,
                    head=integration_head,
                    reservation_absent=True,
                )

            def record_remote_failure(self, operation: str, diagnostic: str) -> None:
                raise AssertionError(f"unexpected remote failure: {operation}: {diagnostic}")

        green_branch = CiObservation(
            state="SUCCESS",
            subject_sha=integration_head,
            run_id="501",
            run_url="https://example.invalid/actions/runs/501",
            workflow_path=".github/workflows/projectstate-validate.yml",
            check_name="branch-head",
        )
        green_candidate = replace(green_branch, check_name="merge-candidate")

        class GoldenProvider:
            def __init__(self) -> None:
                self.snapshot = PullRequestSnapshot(
                    number=1,
                    url="https://example.invalid/pull/1",
                    state="OPEN",
                    head=integration_head,
                    branch=integration_branch,
                    base_branch="main",
                    draft=True,
                    review_decision=None,
                    unresolved_threads=0,
                    merge_state="CLEAN",
                    proof_head=integration_head,
                    final_pr_head=integration_head,
                    evidence_ref="docs/evidence/golden-path-integration",
                    branch_head_ci=green_branch,
                    merge_candidate_ci=green_candidate,
                )
                self.open_pr_count = 1
                self.human_git_actions = 0
                self.follow_up_metadata_prs = 0

            def pull_request(self, number: int) -> PullRequestSnapshot:
                events.append("pr-observed")
                return self.snapshot

            def mark_ready(self, number: int) -> None:
                events.append("pr-ready")
                self.snapshot = replace(self.snapshot, draft=False)

            def merge(self, number: int, expected_head: str, method: str) -> MergeResult:
                events.append("exact-head-squash-merged")
                if expected_head != integration_head or method != "squash":
                    raise AssertionError("merge did not use the confirmed exact-head policy")
                self.snapshot = replace(
                    self.snapshot,
                    state="MERGED",
                    merge_state="MERGED",
                    merge_commit=merge_commit,
                )
                self.open_pr_count = 0
                return MergeResult(True, merge_commit, "merged")

            def default_branch(self) -> DefaultBranchSnapshot:
                events.append("default-branch-observed")
                main_ci = replace(
                    green_branch,
                    subject_sha=merge_commit,
                    run_id="502",
                    run_url="https://example.invalid/actions/runs/502",
                )
                return DefaultBranchSnapshot("main", merge_commit, main_ci)

            def delete_branch(self, branch: str, expected_head: str) -> bool:
                events.append("remote-branch-deleted")
                git(
                    remote,
                    "update-ref",
                    "-d",
                    f"refs/heads/{branch}",
                    expected_head,
                )
                return True

        provider = GoldenProvider()
        final_handoff = root / "golden-path-final-handoff.json"
        finish = FinishSlice(
            local=GoldenLocal(),
            provider=provider,
            policy=DeliveryPolicy.from_mapping(state),
            pr_number=1,
            expected_head=integration_head,
            evidence_folder=Path("docs/evidence/golden-path-integration"),
            handoff_output=final_handoff,
            pr_ci_timeout=0,
            main_ci_timeout=0,
            poll_interval=0,
        )
        if finish.run() != 0:
            raise AssertionError(f"agent-owned finish failed: {finish.report.failure}")
        expected_transitions = [stage.value for stage in Stage]
        if finish.report.transitions != expected_transitions:
            raise AssertionError(f"finish transitions drifted: {finish.report.transitions}")
        if provider.open_pr_count != 0 or provider.human_git_actions != 0:
            raise AssertionError("golden path still requires a human Git action or leaves an open PR")
        deleted_branch_probe = subprocess.run(
            ["git", "show-ref", "--verify", f"refs/heads/{integration_branch}"],
            cwd=remote,
            capture_output=True,
            text=True,
            check=False,
        )
        if deleted_branch_probe.returncode == 0:
            raise AssertionError("golden path retained the verified remote slice branch")
        if provider.follow_up_metadata_prs != 0:
            raise AssertionError("golden path created a follow-up metadata PR")
        if events.index("post-merge-verified") > events.index("remote-branch-deleted"):
            raise AssertionError("remote branch was deleted before post-merge verification")
        final_payload = json.loads(final_handoff.read_text(encoding="utf-8"))
        if final_payload["status"] != "HANDOFF_COMPLETE":
            raise AssertionError("external final handoff is not complete")


if __name__ == "__main__":
    test_golden_path()
    print("PASS test_golden_path")
