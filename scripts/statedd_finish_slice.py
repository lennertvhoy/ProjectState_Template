#!/usr/bin/env python3
"""Finish one StateDD slice from a validated local head through verified main.

The orchestration core is provider-neutral.  ``GitHubProvider`` is the bundled
adapter, while tests and future providers implement the small ``RemoteProvider``
protocol.  The command is deliberately resume-oriented: observed remote truth,
not an in-repository progress marker, determines the next safe transition.

Exit codes:
  0 = HANDOFF_COMPLETE
  1 = policy or proof gate refused; recoverable state was retained
  2 = malformed input or unexpected runtime failure
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import quote

try:
    from statedd_agent_worktree import (
        context_hash,
        dirty_files,
        load_agent_context,
        safety_for_context,
        verify_agent_context_binding,
    )
    from statedd_git_safety_session import (
        MutationBlocked,
        record_required_git_failure,
        require_mutation_permit,
        sanitized_git_environment,
    )
    from statedd_generated_controls import confirmed_delivery_policy_refusal
    from statedd_remote_closure_finalizer import parse_remote_url
    from statedd_validate_schema import StateDDYamlError, parse_yaml_text
except ModuleNotFoundError:  # pragma: no cover - package-import fallback
    from scripts.statedd_agent_worktree import (
        context_hash,
        dirty_files,
        load_agent_context,
        safety_for_context,
        verify_agent_context_binding,
    )
    from scripts.statedd_git_safety_session import (
        MutationBlocked,
        record_required_git_failure,
        require_mutation_permit,
        sanitized_git_environment,
    )
    from scripts.statedd_generated_controls import confirmed_delivery_policy_refusal
    from scripts.statedd_remote_closure_finalizer import parse_remote_url
    from scripts.statedd_validate_schema import StateDDYamlError, parse_yaml_text


ROOT = Path(__file__).resolve().parents[1]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RUN_ID_RE = re.compile(r"/actions/runs/(\d+)")
EVIDENCE_RE = re.compile(r"docs/evidence/[A-Za-z0-9._-]+")
HEAD_MARKER_RE = re.compile(
    r"^[ \t>*-]*(?:\*\*)?(Proof head|Final PR head)(?:\*\*)?\s*[:=]\s*"
    r"(?:\*\*)?\s*([0-9a-f]{40})(?![0-9a-f])",
    re.IGNORECASE | re.MULTILINE,
)
MERGE_METHODS = {"merge", "rebase", "squash"}
SUCCESS = "SUCCESS"
PENDING = "PENDING"
FAILURE = "FAILURE"
MISSING = "MISSING"
WORKFLOW_CANDIDATES = (
    ".github/workflows/validate.yml",
    ".github/workflows/statedd-validate.yml",
)


class Stage(str, Enum):
    LOCAL_VALIDATED = "LOCAL_VALIDATED"
    PUSHED = "PUSHED"
    PR_OPEN = "PR_OPEN"
    PR_READY = "PR_READY"
    REMOTE_CLOSURE_VERIFIED = "REMOTE_CLOSURE_VERIFIED"
    MERGED = "MERGED"
    MAIN_CI_VERIFIED = "MAIN_CI_VERIFIED"
    HANDOFF_COMPLETE = "HANDOFF_COMPLETE"


class FinishRefused(RuntimeError):
    """A required proof is absent or contradictory; remote state is retained."""


@dataclass(frozen=True)
class DeliveryPolicy:
    status: str
    confirmation: str
    mode: str
    method: str = "squash"
    delete_branch_after_verification: bool = True
    require_exact_pr_head: bool = True
    require_clean_merge_state: bool = True
    require_no_requested_changes: bool = True
    require_no_unresolved_review_threads: bool = True
    require_branch_head_ci: bool = True
    require_merge_candidate_ci: bool = True
    require_remote_closure: bool = True
    require_post_merge_main_ci: bool = True

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "DeliveryPolicy":
        policy = payload.get("delivery_policy", payload)
        if not isinstance(policy, dict):
            raise FinishRefused("delivery_policy must be a mapping")
        refusal = confirmed_delivery_policy_refusal(policy)
        if refusal is not None:
            raise FinishRefused(refusal)
        merge = policy.get("merge")
        if not isinstance(merge, dict):
            raise FinishRefused("delivery_policy.merge must be a mapping")
        return cls(
            status=str(policy.get("status", "")),
            confirmation=str(policy.get("confirmation", "")),
            mode=str(merge.get("mode", "")),
            method=str(merge.get("method", "squash")),
            delete_branch_after_verification=merge.get("delete_branch_after_verification") is True,
            require_exact_pr_head=merge.get("require_exact_pr_head") is True,
            require_clean_merge_state=merge.get("require_clean_merge_state") is True,
            require_no_requested_changes=merge.get("require_no_requested_changes") is True,
            require_no_unresolved_review_threads=merge.get("require_no_unresolved_review_threads") is True,
            require_branch_head_ci=merge.get("require_branch_head_ci") is True,
            require_merge_candidate_ci=merge.get("require_merge_candidate_ci") is True,
            require_remote_closure=merge.get("require_remote_closure") is True,
            require_post_merge_main_ci=merge.get("require_post_merge_main_ci") is True,
        )

    def authorize(self, requested_method: str | None = None) -> str:
        if self.status != "confirmed" or self.confirmation != "human_confirmed":
            raise FinishRefused("automatic merge requires a confirmed, human-confirmed delivery policy")
        if self.mode == "human_merge":
            raise FinishRefused("delivery policy is human_merge; automatic merge is forbidden")
        if self.mode != "agent_after_green":
            raise FinishRefused(f"unsupported delivery policy merge mode: {self.mode or 'missing'}")
        method = requested_method or self.method or "squash"
        if method not in MERGE_METHODS:
            raise FinishRefused(f"unsupported merge method: {method}")
        if requested_method and self.method and requested_method != self.method:
            raise FinishRefused(
                f"requested merge method {requested_method!r} differs from confirmed policy {self.method!r}"
            )
        required = {
            "delete_branch_after_verification": self.delete_branch_after_verification,
            "require_exact_pr_head": self.require_exact_pr_head,
            "require_clean_merge_state": self.require_clean_merge_state,
            "require_no_requested_changes": self.require_no_requested_changes,
            "require_no_unresolved_review_threads": self.require_no_unresolved_review_threads,
            "require_branch_head_ci": self.require_branch_head_ci,
            "require_merge_candidate_ci": self.require_merge_candidate_ci,
            "require_remote_closure": self.require_remote_closure,
            "require_post_merge_main_ci": self.require_post_merge_main_ci,
        }
        disabled = sorted(name for name, enabled in required.items() if not enabled)
        if disabled:
            raise FinishRefused(
                "agent_after_green policy is missing mandatory fail-closed controls: "
                + ", ".join(disabled)
            )
        return method


@dataclass(frozen=True)
class CiObservation:
    state: str
    subject_sha: str
    run_id: str | None = None
    run_url: str | None = None
    workflow_path: str | None = None
    check_name: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class PullRequestSnapshot:
    number: int
    url: str
    state: str
    head: str
    branch: str
    base_branch: str
    draft: bool
    review_decision: str | None
    unresolved_threads: int
    merge_state: str
    proof_head: str | None
    final_pr_head: str | None
    evidence_ref: str | None
    branch_head_ci: CiObservation
    merge_candidate_ci: CiObservation
    merge_commit: str | None = None


@dataclass(frozen=True)
class MergeResult:
    merged: bool
    merge_commit: str | None
    message: str = ""


@dataclass(frozen=True)
class DefaultBranchSnapshot:
    name: str
    head: str
    ci: CiObservation


@dataclass(frozen=True)
class LocalTruth:
    root: Path
    branch: str
    head: str
    evidence_folder: Path
    evidence_ref: str
    agent_id: str
    slice_id: str


@dataclass(frozen=True)
class RemoteClosureProof:
    head: str
    proof_head: str
    evidence_ref: str
    ci_run_id: str | None
    output: Path


@dataclass(frozen=True)
class PostMergeProof:
    output: Path
    payload: dict[str, Any]


class RemoteProvider(Protocol):
    def pull_request(self, number: int) -> PullRequestSnapshot: ...

    def mark_ready(self, number: int) -> None: ...

    def merge(self, number: int, expected_head: str, method: str) -> MergeResult: ...

    def default_branch(self) -> DefaultBranchSnapshot: ...

    def delete_branch(self, branch: str, expected_head: str) -> bool: ...


class LocalActions(Protocol):
    def validate(self, expected_head: str, evidence_folder: Path) -> LocalTruth: ...

    def authorize_remote(self, operation: str) -> None: ...

    def push_exact(self, branch: str, expected_head: str) -> None: ...

    def remote_closure(
        self, pr_number: int, expected_head: str, evidence_folder: Path, output: Path
    ) -> RemoteClosureProof: ...

    def fetch_default_branch(self, branch: str) -> str: ...

    def post_merge_verify(
        self,
        pr_number: int,
        expected_head: str,
        evidence_folder: Path,
        output: Path,
    ) -> PostMergeProof: ...

    def release_isolation(self) -> None: ...

    def record_remote_failure(self, operation: str, diagnostic: str) -> None: ...


@dataclass
class FinishReport:
    schema: str = "statedd.finish_slice_handoff.v1"
    generated_at: str = ""
    status: str = "NOT_STARTED"
    transitions: list[str] = field(default_factory=list)
    repository: str = ""
    pr_number: int = 0
    pr_url: str | None = None
    expected_pr_head: str | None = None
    proof_head: str | None = None
    evidence_folder: str = ""
    delivery_policy_mode: str = ""
    merge_method: str = ""
    branch: str | None = None
    branch_head_ci: dict[str, Any] | None = None
    merge_candidate_ci: dict[str, Any] | None = None
    merge_commit: str | None = None
    default_branch: str | None = None
    default_branch_head: str | None = None
    main_ci: dict[str, Any] | None = None
    remote_closure_output: str | None = None
    post_merge_output: str | None = None
    post_merge_verified: bool = False
    remote_branch_absent: bool = False
    isolation_released: bool = False
    recoverable_state_retained: bool = True
    failure: str | None = None


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def _strict_json(text: str, source: Path) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {source}")
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON value {value}")))


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _run(args: list[str], cwd: Path, *, timeout: int = 120) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            env=sanitized_git_environment(),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired:
        return -1, "", f"timed out after {timeout}s"
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _require(args: list[str], cwd: Path, label: str, *, timeout: int = 120) -> str:
    code, stdout, stderr = _run(args, cwd, timeout=timeout)
    if code != 0:
        raise FinishRefused(f"{label} failed ({code}): {stderr or stdout or 'no diagnostic'}")
    return stdout


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        value = _strict_json(path.read_text(encoding="utf-8"), path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise FinishRefused(f"cannot read trusted JSON output {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FinishRefused(f"JSON output must be an object: {path}")
    return value


def load_policy(path: Path) -> DeliveryPolicy:
    try:
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            value = _strict_json(text, path)
        else:
            value = parse_yaml_text(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, StateDDYamlError) as exc:
        raise FinishRefused(f"cannot load delivery policy from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FinishRefused(f"delivery policy source must contain a mapping: {path}")
    return DeliveryPolicy.from_mapping(value)


def _body_bindings(body: str) -> tuple[str | None, str | None, str | None]:
    markers: dict[str, list[str]] = {"proof head": [], "final pr head": []}
    for name, value in HEAD_MARKER_RE.findall(body or ""):
        markers[name.lower()].append(value.lower())
    refs = EVIDENCE_RE.findall(body or "")
    proof = markers["proof head"][0] if len(markers["proof head"]) == 1 else None
    final = markers["final pr head"][0] if len(markers["final pr head"]) == 1 else None
    evidence = refs[0] if len(refs) == 1 else None
    return proof, final, evidence


class RepositoryActions:
    """Production local adapter composed from existing StateDD authorities."""

    def __init__(
        self,
        root: Path,
        *,
        agent_context: Path | None = None,
        restart_session: bool = False,
        workflow_path: str | None = None,
        verbose: bool = False,
    ) -> None:
        self.root = root.resolve()
        self.context_path = (agent_context or self.root / ".statedd" / "agent.context").resolve()
        self.restart_session = restart_session
        if workflow_path is None:
            matches = [
                candidate
                for candidate in WORKFLOW_CANDIDATES
                if (self.root / candidate).is_file() and not (self.root / candidate).is_symlink()
            ]
            if len(matches) != 1:
                raise FinishRefused(
                    "cannot uniquely detect authoritative workflow; pass --workflow-path"
                )
            workflow_path = matches[0]
        workflow = Path(workflow_path)
        if workflow.is_absolute() or any(part in {"", ".", ".."} for part in workflow.parts):
            raise FinishRefused(f"unsafe authoritative workflow path: {workflow_path!r}")
        workflow_file = (self.root / workflow).resolve(strict=False)
        try:
            workflow_file.relative_to(self.root)
        except ValueError as exc:
            raise FinishRefused("authoritative workflow escapes repository root") from exc
        if not workflow_file.is_file() or workflow_file.is_symlink():
            raise FinishRefused(f"authoritative workflow is missing or unsafe: {workflow_path}")
        self.workflow_path = workflow.as_posix()
        self.verbose = verbose
        self.context: dict[str, Any] = {}
        self.truth: LocalTruth | None = None

    def _git(self, *args: str, label: str) -> str:
        return _require(["git", *args], self.root, label)

    def _authorization(self) -> dict[str, str | None]:
        if not self.context or not self.truth:
            raise FinishRefused("local adapter has not established strict agent context")
        return {
            "slice_id": self.context["slice_id"],
            "agent_id": self.context["agent_id"],
            "context_hash": context_hash(self.context),
            "reservation_ref": self.context["reservation_ref"],
            "expected_branch": self.truth.branch,
            "expected_head": self.truth.head,
        }

    def validate(self, expected_head: str, evidence_folder: Path) -> LocalTruth:
        code, context, error = load_agent_context(self.context_path)
        if code:
            raise FinishRefused(error)
        try:
            verify_agent_context_binding(self.root, context)
        except (MutationBlocked, RuntimeError) as exc:
            raise FinishRefused(f"agent context ownership verification failed: {exc}") from exc
        safety_code, report, safety_error = safety_for_context(
            self.root,
            context,
            self.restart_session,
            operation_class="remote_mutation",
            operator_authorized=True,
        )
        if safety_code != 0 or not report.get("decision", {}).get("mutation_permitted"):
            blockers = report.get("decision", {}).get("blockers", []) if report else []
            raise FinishRefused(
                "central Git-safety remote-mutation preflight failed: "
                + "; ".join(str(item) for item in blockers or [safety_error or "no diagnostic"])
            )
        branch = self._git("branch", "--show-current", label="branch inspection")
        head = self._git("rev-parse", "HEAD", label="HEAD inspection")
        if not SHA_RE.fullmatch(expected_head):
            raise FinishRefused("expected PR head must be one full lowercase SHA-1")
        if head != expected_head:
            raise FinishRefused(f"local HEAD changed: expected {expected_head}, found {head}")
        if branch != context.get("branch"):
            raise FinishRefused("current branch does not match strict agent context")
        if report.get("repository", {}).get("branch") != branch or report.get("repository", {}).get("head") != head:
            raise FinishRefused("branch or HEAD changed after centralized Git-safety decision")
        changed = dirty_files(self.root)
        if changed:
            raise FinishRefused("finish path requires a clean worktree: " + ", ".join(changed))

        requested = evidence_folder if evidence_folder.is_absolute() else self.root / evidence_folder
        evidence = requested.resolve(strict=False)
        evidence_root = (self.root / "docs" / "evidence").resolve(strict=False)
        try:
            relative = evidence.relative_to(evidence_root)
        except ValueError as exc:
            raise FinishRefused("evidence folder must be under docs/evidence") from exc
        if len(relative.parts) != 1 or not evidence.is_dir() or evidence.is_symlink():
            raise FinishRefused("evidence folder must be one real directory directly under docs/evidence")
        evidence_ref = f"docs/evidence/{relative.as_posix()}"
        self.context = context
        self.truth = LocalTruth(
            root=self.root,
            branch=branch,
            head=head,
            evidence_folder=evidence,
            evidence_ref=evidence_ref,
            agent_id=context["agent_id"],
            slice_id=context["slice_id"],
        )

        closure = self.root / "scripts" / "statedd_closure_check.py"
        command = [
            sys.executable,
            str(closure),
            "--root",
            str(self.root),
            "--gate-level",
            "2",
            "--evidence-folder",
            evidence_ref,
            "--agent-context",
            str(self.context_path),
        ]
        if self.verbose:
            command.append("--verbose")
        _require(command, self.root, "strict local slice proof", timeout=900)
        self.authorize_remote("finish-slice remote mutation")
        return self.truth

    def authorize_remote(self, operation: str) -> None:
        try:
            require_mutation_permit(
                self.root,
                operation,
                operation_class="remote_mutation",
                authorization=self._authorization(),
            )
        except MutationBlocked as exc:
            raise FinishRefused(str(exc)) from exc

    def _assert_unchanged(self, branch: str, expected_head: str) -> None:
        actual_branch = self._git("branch", "--show-current", label="branch recheck")
        actual_head = self._git("rev-parse", "HEAD", label="HEAD recheck")
        if actual_branch != branch or actual_head != expected_head:
            raise FinishRefused(
                f"local branch/HEAD moved during finish: {actual_branch}@{actual_head}"
            )
        if dirty_files(self.root):
            raise FinishRefused("worktree became dirty during finish")

    def push_exact(self, branch: str, expected_head: str) -> None:
        self._assert_unchanged(branch, expected_head)
        self.authorize_remote("exact slice-head push")
        code, stdout, stderr = _run(
            ["git", "push", "origin", f"{expected_head}:refs/heads/{branch}"], self.root, timeout=300
        )
        if code != 0:
            self.record_remote_failure("exact slice-head push", stderr or stdout)
            raise FinishRefused(f"exact slice-head push failed: {stderr or stdout or 'no diagnostic'}")
        remote = self._git("ls-remote", "origin", f"refs/heads/{branch}", label="remote head proof")
        remote_head = remote.split("\t", 1)[0] if "\t" in remote else ""
        if remote_head != expected_head:
            raise FinishRefused(
                f"remote branch does not contain exact authorized head: {remote_head or 'not found'}"
            )

    def remote_closure(
        self, pr_number: int, expected_head: str, evidence_folder: Path, output: Path
    ) -> RemoteClosureProof:
        finalizer = self.root / "scripts" / "statedd_remote_closure_finalizer.py"
        command = [
            sys.executable,
            str(finalizer),
            "--root",
            str(self.root),
            "--pr-number",
            str(pr_number),
            "--evidence-folder",
            str(evidence_folder),
            "--agent-context",
            str(self.context_path),
            "--workflow-path",
            self.workflow_path,
            "--output",
            str(output),
        ]
        if self.verbose:
            command.append("--verbose")
        _require(command, self.root, "remote closure finalizer", timeout=300)
        payload = _load_json_file(output)
        if payload.get("local_head") != expected_head or payload.get("pr_head") != expected_head:
            raise FinishRefused("remote closure handoff does not bind the expected PR head")
        if payload.get("github_final_requery") is not True or payload.get("ci_state") != SUCCESS:
            raise FinishRefused("remote closure handoff lacks final GitHub requery/green CI")
        proof_head = payload.get("evidence_proof_head")
        if not isinstance(proof_head, str) or not SHA_RE.fullmatch(proof_head):
            raise FinishRefused("remote closure handoff lacks one full evidence proof head")
        folder_value = payload.get("evidence_folder")
        if not isinstance(folder_value, str) or Path(folder_value).resolve() != evidence_folder.resolve():
            raise FinishRefused("remote closure handoff evidence folder differs from the requested folder")
        return RemoteClosureProof(
            head=expected_head,
            proof_head=proof_head,
            evidence_ref=self.truth.evidence_ref if self.truth else "",
            ci_run_id=str(payload["ci_run_id"]) if payload.get("ci_run_id") else None,
            output=output,
        )

    def fetch_default_branch(self, branch: str) -> str:
        if not branch or branch.startswith("-") or any(part in {"", ".", ".."} for part in branch.split("/")):
            raise FinishRefused(f"unsafe default branch name: {branch!r}")
        self.authorize_remote("default-branch fetch")
        refspec = f"refs/heads/{branch}:refs/remotes/origin/{branch}"
        code, stdout, stderr = _run(["git", "fetch", "origin", refspec], self.root, timeout=300)
        if code != 0:
            self.record_remote_failure("default-branch fetch", stderr or stdout)
            raise FinishRefused(f"default-branch fetch failed: {stderr or stdout or 'no diagnostic'}")
        return self._git("rev-parse", f"refs/remotes/origin/{branch}", label="fetched default head")

    def post_merge_verify(
        self,
        pr_number: int,
        expected_head: str,
        evidence_folder: Path,
        output: Path,
    ) -> PostMergeProof:
        verifier = self.root / "scripts" / "statedd_post_merge_verify.py"
        command = [
            sys.executable,
            str(verifier),
            "--root",
            str(self.root),
            "--pr-number",
            str(pr_number),
            "--expected-pr-head",
            expected_head,
            "--evidence-folder",
            str(evidence_folder),
            "--output",
            str(output),
        ]
        if self.verbose:
            command.append("--verbose")
        _require(command, self.root, "post-merge verifier", timeout=600)
        return PostMergeProof(output=output, payload=_load_json_file(output))

    def release_isolation(self) -> None:
        orchestrator = self.root / "scripts" / "statedd_agent_worktree.py"
        _require(
            [
                sys.executable,
                str(orchestrator),
                "handoff",
                "--worktree",
                str(self.root),
                "--release",
                "--validated",
            ],
            self.root,
            "isolation release",
            timeout=300,
        )

    def record_remote_failure(self, operation: str, diagnostic: str) -> None:
        if not self.truth:
            return
        record_required_git_failure(
            self.root,
            operation,
            diagnostic,
            binding={
                "branch": self.truth.branch,
                "head": self.truth.head,
                "slice_id": self.truth.slice_id,
                "agent_id": self.truth.agent_id,
                "context_hash": context_hash(self.context),
                "reservation_ref": self.context.get("reservation_ref"),
                "worktree_clean": True,
            },
        )


PR_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      id number url state isDraft reviewDecision mergeStateStatus
      headRefOid headRefName baseRefName body
      mergeCommit { oid }
      reviewThreads(first: 100) {
        nodes { isResolved isOutdated }
        pageInfo { hasNextPage }
      }
      commits(last: 1) {
        nodes {
          commit {
            oid
            statusCheckRollup {
              state
              contexts(first: 100) {
                nodes {
                  __typename
                  ... on CheckRun {
                    name status conclusion detailsUrl
                    checkSuite {
                      workflowRun { databaseId url file { path } }
                    }
                  }
                }
                pageInfo { hasNextPage }
              }
            }
          }
        }
      }
    }
  }
}
"""

READY_MUTATION = """
mutation($id: ID!) {
  markPullRequestReadyForReview(input: {pullRequestId: $id}) {
    pullRequest { number isDraft headRefOid }
  }
}
"""

DEFAULT_BRANCH_QUERY = """
query($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    defaultBranchRef {
      name
      target {
        ... on Commit {
          oid
          statusCheckRollup {
            state
            contexts(first: 100) {
              nodes {
                __typename
                ... on CheckRun {
                  name status conclusion detailsUrl
                  checkSuite {
                    workflowRun { databaseId url file { path } }
                  }
                }
              }
              pageInfo { hasNextPage }
            }
          }
        }
      }
    }
  }
}
"""


class GitHubProvider:
    """GitHub adapter; merge uses the API's expected-head ``sha`` constraint."""

    def __init__(
        self,
        root: Path,
        *,
        token: str | None = None,
        workflow_path: str = ".github/workflows/validate.yml",
        branch_head_job: str = "branch-head",
        merge_candidate_job: str = "merge-candidate",
    ) -> None:
        self.root = root.resolve()
        self.token = token
        self.workflow_path = workflow_path
        self.branch_head_job = branch_head_job
        self.merge_candidate_job = merge_candidate_job
        remote = _require(["git", "remote", "get-url", "origin"], self.root, "origin URL inspection")
        parsed = parse_remote_url(remote)
        if not parsed:
            raise FinishRefused(f"GitHub adapter cannot parse origin URL: {remote}")
        self.owner, self.repo = parsed

    def _gh(self, args: list[str], *, timeout: int = 120, allow_not_found: bool = False) -> dict[str, Any]:
        env = sanitized_git_environment()
        if self.token:
            env["GH_TOKEN"] = self.token
        try:
            completed = subprocess.run(
                ["gh", *args],
                cwd=self.root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise FinishRefused("GitHub adapter requires gh or a future provider adapter") from exc
        except subprocess.TimeoutExpired as exc:
            raise FinishRefused(f"GitHub API timed out after {timeout}s") from exc
        if completed.returncode != 0:
            diagnostic = completed.stderr or completed.stdout or "no diagnostic"
            if allow_not_found and ("HTTP 404" in diagnostic or "Not Found" in diagnostic):
                return {"_not_found": True}
            raise FinishRefused(f"GitHub API failed: {diagnostic.strip()}")
        if not completed.stdout.strip():
            return {}
        try:
            value = _strict_json(completed.stdout, Path("gh-output"))
        except (json.JSONDecodeError, ValueError) as exc:
            raise FinishRefused(f"GitHub API returned malformed JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise FinishRefused("GitHub API response must be a JSON object")
        if value.get("errors"):
            raise FinishRefused(f"GitHub GraphQL error: {value['errors']}")
        return value

    def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        args = ["api", "graphql"]
        for key, value in variables.items():
            if isinstance(value, str):
                args.extend(["-f", f"{key}={value}"])
            else:
                args.extend(["-F", f"{key}={json.dumps(value)}"])
        args.extend(["-f", f"query={query}"])
        return self._gh(args).get("data", {})

    def _ci(self, rollup: Any, name: str, subject: str) -> CiObservation:
        if not isinstance(rollup, dict):
            return CiObservation(MISSING, subject, check_name=name, detail="status rollup missing")
        contexts = rollup.get("contexts")
        if not isinstance(contexts, dict) or not isinstance(contexts.get("nodes"), list):
            return CiObservation(MISSING, subject, check_name=name, detail="check contexts missing")
        page = contexts.get("pageInfo")
        if not isinstance(page, dict) or page.get("hasNextPage") is not False:
            return CiObservation(FAILURE, subject, check_name=name, detail="check context pagination incomplete")
        matches: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
        skipped = False
        for node in contexts["nodes"]:
            if not isinstance(node, dict) or node.get("__typename") != "CheckRun" or node.get("name") != name:
                continue
            workflow = ((node.get("checkSuite") or {}).get("workflowRun") or {})
            file_block = workflow.get("file") or {}
            if file_block.get("path") != self.workflow_path:
                continue
            conclusion = str(node.get("conclusion") or "").upper()
            if conclusion in {"SKIPPED", "NEUTRAL"}:
                skipped = True
                continue
            run_id = workflow.get("databaseId")
            try:
                ordering = int(run_id)
            except (TypeError, ValueError):
                details_match = RUN_ID_RE.search(str(node.get("detailsUrl") or ""))
                ordering = int(details_match.group(1)) if details_match else -1
            matches.append((ordering, node, workflow))
        if not matches:
            state = PENDING if skipped else MISSING
            return CiObservation(state, subject, workflow_path=self.workflow_path, check_name=name)
        _, node, workflow = max(matches, key=lambda item: item[0])
        status = str(node.get("status") or "").upper()
        conclusion = str(node.get("conclusion") or "").upper()
        if status != "COMPLETED":
            state = PENDING
        elif conclusion == SUCCESS:
            state = SUCCESS
        else:
            state = FAILURE
        run_id = workflow.get("databaseId")
        return CiObservation(
            state=state,
            subject_sha=subject,
            run_id=str(run_id) if run_id is not None else None,
            run_url=workflow.get("url") or node.get("detailsUrl"),
            workflow_path=self.workflow_path,
            check_name=name,
            detail=f"status={status or 'missing'}, conclusion={conclusion or 'missing'}",
        )

    def pull_request(self, number: int) -> PullRequestSnapshot:
        data = self._graphql(
            PR_QUERY,
            {"owner": self.owner, "repo": self.repo, "number": number},
        )
        pr = (data.get("repository") or {}).get("pullRequest")
        if not isinstance(pr, dict):
            raise FinishRefused(f"pull request #{number} was not found")
        threads = pr.get("reviewThreads")
        if not isinstance(threads, dict) or not isinstance(threads.get("nodes"), list):
            raise FinishRefused("review-thread state is unavailable")
        if (threads.get("pageInfo") or {}).get("hasNextPage") is not False:
            raise FinishRefused("review-thread pagination is incomplete")
        unresolved = sum(
            1
            for thread in threads["nodes"]
            if isinstance(thread, dict)
            and thread.get("isResolved") is not True
            and thread.get("isOutdated") is not True
        )
        commits = ((pr.get("commits") or {}).get("nodes") or [])
        commit = ((commits[-1] or {}).get("commit") or {}) if commits else {}
        head = str(pr.get("headRefOid") or "")
        if commit.get("oid") != head:
            raise FinishRefused("PR status-check subject does not match its head")
        rollup = commit.get("statusCheckRollup")
        proof, final, evidence = _body_bindings(str(pr.get("body") or ""))
        merge_commit = (pr.get("mergeCommit") or {}).get("oid")
        return PullRequestSnapshot(
            number=int(pr.get("number")),
            url=str(pr.get("url") or ""),
            state=str(pr.get("state") or "").upper(),
            head=head,
            branch=str(pr.get("headRefName") or ""),
            base_branch=str(pr.get("baseRefName") or ""),
            draft=pr.get("isDraft") is True,
            review_decision=(str(pr["reviewDecision"]).upper() if pr.get("reviewDecision") else None),
            unresolved_threads=unresolved,
            merge_state=str(pr.get("mergeStateStatus") or "").upper(),
            proof_head=proof,
            final_pr_head=final,
            evidence_ref=evidence,
            branch_head_ci=self._ci(rollup, self.branch_head_job, head),
            merge_candidate_ci=self._ci(rollup, self.merge_candidate_job, head),
            merge_commit=str(merge_commit) if merge_commit else None,
        )

    def mark_ready(self, number: int) -> None:
        snapshot = self.pull_request(number)
        if not snapshot.draft:
            return
        data = self._graphql(
            "query($owner:String!,$repo:String!,$number:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$number){id}}}",
            {"owner": self.owner, "repo": self.repo, "number": number},
        )
        pr = (data.get("repository") or {}).get("pullRequest") or {}
        node_id = pr.get("id")
        if not node_id:
            raise FinishRefused("cannot resolve pull-request node ID for ready transition")
        self._graphql(READY_MUTATION, {"id": node_id})

    def merge(self, number: int, expected_head: str, method: str) -> MergeResult:
        response = self._gh(
            [
                "api",
                "--method",
                "PUT",
                f"repos/{self.owner}/{self.repo}/pulls/{number}/merge",
                "-f",
                f"sha={expected_head}",
                "-f",
                f"merge_method={method}",
            ],
            timeout=300,
        )
        return MergeResult(
            merged=response.get("merged") is True,
            merge_commit=str(response.get("sha")) if response.get("sha") else None,
            message=str(response.get("message") or ""),
        )

    def default_branch(self) -> DefaultBranchSnapshot:
        data = self._graphql(DEFAULT_BRANCH_QUERY, {"owner": self.owner, "repo": self.repo})
        ref = (data.get("repository") or {}).get("defaultBranchRef")
        if not isinstance(ref, dict) or not isinstance(ref.get("target"), dict):
            raise FinishRefused("default branch truth is unavailable")
        target = ref["target"]
        head = str(target.get("oid") or "")
        return DefaultBranchSnapshot(
            name=str(ref.get("name") or ""),
            head=head,
            ci=self._ci(target.get("statusCheckRollup"), self.branch_head_job, head),
        )

    def delete_branch(self, branch: str, expected_head: str) -> bool:
        encoded = quote(branch, safe="")
        read_path = f"repos/{self.owner}/{self.repo}/git/ref/heads/{encoded}"
        delete_path = f"repos/{self.owner}/{self.repo}/git/refs/heads/{encoded}"
        current = self._gh(["api", read_path], allow_not_found=True)
        if current.get("_not_found"):
            return False
        actual = ((current.get("object") or {}).get("sha"))
        if actual != expected_head:
            raise FinishRefused(
                f"remote branch moved before deletion: expected {expected_head}, found {actual or 'not found'}"
            )
        self._gh(["api", "--method", "DELETE", delete_path])
        absent = self._gh(["api", read_path], allow_not_found=True)
        if not absent.get("_not_found"):
            raise FinishRefused("remote branch still exists after deletion request")
        return True


class FinishSlice:
    def __init__(
        self,
        *,
        local: LocalActions,
        provider: RemoteProvider,
        policy: DeliveryPolicy,
        pr_number: int,
        expected_head: str,
        evidence_folder: Path,
        handoff_output: Path,
        merge_method: str | None = None,
        pr_ci_timeout: float = 1800,
        main_ci_timeout: float = 1800,
        poll_interval: float = 15,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.local = local
        self.provider = provider
        self.policy = policy
        self.pr_number = pr_number
        self.expected_head = expected_head
        self.evidence_folder = evidence_folder
        self.output = handoff_output.resolve(strict=False)
        self.requested_method = merge_method
        self.pr_ci_timeout = max(0.0, pr_ci_timeout)
        self.main_ci_timeout = max(0.0, main_ci_timeout)
        self.poll_interval = max(0.0, min(poll_interval, 60.0))
        self.clock = clock
        self.sleep = sleep
        self.truth: LocalTruth | None = None
        self.report = FinishReport(
            generated_at=_now(),
            repository="",
            pr_number=pr_number,
            expected_pr_head=expected_head if SHA_RE.fullmatch(expected_head) else None,
            evidence_folder=str(evidence_folder),
        )

    def _persist(self) -> None:
        self.report.generated_at = _now()
        _atomic_json(self.output, asdict(self.report))

    def _transition(self, stage: Stage) -> None:
        if stage.value not in self.report.transitions:
            self.report.transitions.append(stage.value)
        self.report.status = stage.value
        self.report.failure = None
        self._persist()

    def _external_children(self) -> tuple[Path, Path]:
        suffix = self.output.suffix or ".json"
        stem = self.output.name[: -len(suffix)] if self.output.name.endswith(suffix) else self.output.name
        return (
            self.output.with_name(f"{stem}.remote-closure{suffix}"),
            self.output.with_name(f"{stem}.post-merge{suffix}"),
        )

    def _record_ci(self, snapshot: PullRequestSnapshot) -> None:
        self.report.branch_head_ci = asdict(snapshot.branch_head_ci)
        self.report.merge_candidate_ci = asdict(snapshot.merge_candidate_ci)

    def _validate_pr_identity(self, snapshot: PullRequestSnapshot, *, require_open: bool) -> None:
        if snapshot.number != self.pr_number:
            raise FinishRefused("provider returned a different pull request")
        if snapshot.head != self.expected_head:
            raise FinishRefused(
                f"unexpected PR-head movement: expected {self.expected_head}, found {snapshot.head or 'not found'}"
            )
        if self.truth and snapshot.branch != self.truth.branch:
            raise FinishRefused(
                f"PR branch {snapshot.branch!r} differs from agent branch {self.truth.branch!r}"
            )
        if require_open and snapshot.state != "OPEN":
            raise FinishRefused(f"PR is not open: state={snapshot.state or 'missing'}")

    def _validate_mutable_merge_truth(self, snapshot: PullRequestSnapshot) -> None:
        self._validate_pr_identity(snapshot, require_open=True)
        if snapshot.draft:
            raise FinishRefused("PR is still draft")
        if snapshot.review_decision in {"CHANGES_REQUESTED", "REVIEW_REQUIRED"}:
            raise FinishRefused(f"review state blocks merge: {snapshot.review_decision}")
        if snapshot.unresolved_threads:
            raise FinishRefused(
                f"PR has {snapshot.unresolved_threads} unresolved current review thread(s)"
            )
        if snapshot.merge_state not in {"CLEAN", "HAS_HOOKS"}:
            raise FinishRefused(
                f"merge state is not clean: {snapshot.merge_state or 'missing'}"
            )
        if snapshot.final_pr_head != self.expected_head:
            raise FinishRefused("PR body Final PR head does not bind the expected head")
        if not snapshot.proof_head or not SHA_RE.fullmatch(snapshot.proof_head):
            raise FinishRefused("PR body lacks exactly one full Proof head")
        if self.truth and snapshot.evidence_ref != self.truth.evidence_ref:
            raise FinishRefused("PR body evidence reference differs from the selected evidence folder")

    @staticmethod
    def _ci_failure(label: str, observation: CiObservation) -> FinishRefused:
        detail = f" ({observation.detail})" if observation.detail else ""
        return FinishRefused(f"{label} CI is {observation.state}{detail}")

    def _wait_pr_green(self) -> PullRequestSnapshot:
        deadline = self.clock() + self.pr_ci_timeout
        while True:
            snapshot = self.provider.pull_request(self.pr_number)
            self._validate_mutable_merge_truth(snapshot)
            self._record_ci(snapshot)
            observations = (
                ("branch-head", snapshot.branch_head_ci),
                ("merge-candidate", snapshot.merge_candidate_ci),
            )
            failed = [(label, value) for label, value in observations if value.state == FAILURE]
            if failed:
                raise self._ci_failure(*failed[0])
            if all(value.state == SUCCESS for _, value in observations):
                return snapshot
            if self.clock() >= deadline:
                missing = ", ".join(
                    f"{label}={value.state}" for label, value in observations if value.state != SUCCESS
                )
                raise FinishRefused(f"timed out waiting for PR CI: {missing}")
            self.sleep(self.poll_interval)

    def _wait_main_green(self, expected_branch: str, expected_head: str) -> DefaultBranchSnapshot:
        deadline = self.clock() + self.main_ci_timeout
        while True:
            current = self.provider.default_branch()
            if current.name != expected_branch or current.head != expected_head:
                raise FinishRefused(
                    "default branch moved while waiting for direct main CI; rerun against fresh observed truth"
                )
            if current.ci.subject_sha != current.head:
                raise FinishRefused("main CI subject differs from the default-branch head")
            self.report.default_branch = current.name
            self.report.default_branch_head = current.head
            self.report.main_ci = asdict(current.ci)
            if current.ci.state == SUCCESS:
                return current
            if current.ci.state == FAILURE:
                raise self._ci_failure("default-branch", current.ci)
            if self.clock() >= deadline:
                raise FinishRefused(
                    f"timed out waiting for direct default-branch CI: {current.ci.state}"
                )
            self.sleep(self.poll_interval)

    def run(self) -> int:
        try:
            method = self.policy.authorize(self.requested_method)
            if not SHA_RE.fullmatch(self.expected_head):
                raise FinishRefused("--expected-pr-head must be one full lowercase SHA-1")
            self.report.delivery_policy_mode = self.policy.mode
            self.report.merge_method = method

            self.truth = self.local.validate(self.expected_head, self.evidence_folder)
            self.report.repository = str(self.truth.root)
            self.report.branch = self.truth.branch
            self.report.evidence_folder = str(self.truth.evidence_folder)
            try:
                self.output.relative_to(self.truth.root.resolve())
            except ValueError:
                pass
            else:
                raise FinishRefused("final handoff output must be outside the repository")
            self._transition(Stage.LOCAL_VALIDATED)

            snapshot = self.provider.pull_request(self.pr_number)
            self.report.pr_url = snapshot.url
            self._validate_pr_identity(snapshot, require_open=False)
            default_before_merge = self.provider.default_branch()
            if snapshot.base_branch != default_before_merge.name:
                raise FinishRefused(
                    f"PR base {snapshot.base_branch!r} is not the provider default branch "
                    f"{default_before_merge.name!r}"
                )
            remote_output, post_output = self._external_children()

            if snapshot.state == "MERGED":
                if not snapshot.merge_commit or not SHA_RE.fullmatch(snapshot.merge_commit):
                    raise FinishRefused("merged PR has no full merge commit")
                if snapshot.final_pr_head != self.expected_head:
                    raise FinishRefused("merged PR body does not bind its exact final PR head")
                if not snapshot.proof_head or not SHA_RE.fullmatch(snapshot.proof_head):
                    raise FinishRefused("merged PR body lacks exactly one full Proof head")
                if snapshot.evidence_ref != self.truth.evidence_ref:
                    raise FinishRefused("merged PR body evidence differs from selected evidence")
                self.report.proof_head = snapshot.proof_head
                self.report.merge_commit = snapshot.merge_commit
                self._record_ci(snapshot)
                self._transition(Stage.MERGED)
            else:
                self._validate_pr_identity(snapshot, require_open=True)
                self.local.push_exact(self.truth.branch, self.expected_head)
                self._transition(Stage.PUSHED)

                snapshot = self.provider.pull_request(self.pr_number)
                self._validate_pr_identity(snapshot, require_open=True)
                self.report.pr_url = snapshot.url
                self._transition(Stage.PR_OPEN)

                if snapshot.draft:
                    self.local.authorize_remote("mark pull request ready")
                    try:
                        self.provider.mark_ready(self.pr_number)
                    except FinishRefused as exc:
                        self.local.record_remote_failure("mark pull request ready", str(exc))
                        raise
                    snapshot = self.provider.pull_request(self.pr_number)
                    self._validate_pr_identity(snapshot, require_open=True)
                    if snapshot.draft:
                        raise FinishRefused("ready-for-review mutation did not clear draft state")
                self._transition(Stage.PR_READY)

                snapshot = self._wait_pr_green()
                closure = self.local.remote_closure(
                    self.pr_number,
                    self.expected_head,
                    self.truth.evidence_folder,
                    remote_output,
                )
                if closure.head != self.expected_head or closure.evidence_ref != self.truth.evidence_ref:
                    raise FinishRefused("remote closure proof does not bind finish-slice inputs")
                self.report.proof_head = closure.proof_head
                self.report.remote_closure_output = str(closure.output)
                self._transition(Stage.REMOTE_CLOSURE_VERIFIED)

                # This query is intentionally adjacent to the expected-head merge mutation.
                snapshot = self.provider.pull_request(self.pr_number)
                self._validate_mutable_merge_truth(snapshot)
                if snapshot.branch_head_ci.state != SUCCESS or snapshot.merge_candidate_ci.state != SUCCESS:
                    raise FinishRefused("CI changed after remote closure and before merge")
                if snapshot.proof_head != closure.proof_head:
                    raise FinishRefused("PR body proof head changed after remote closure")
                self._record_ci(snapshot)
                self.local.authorize_remote("expected-head pull-request merge")
                try:
                    merged = self.provider.merge(self.pr_number, self.expected_head, method)
                except FinishRefused as exc:
                    self.local.record_remote_failure("expected-head pull-request merge", str(exc))
                    raise
                if not merged.merged or not merged.merge_commit or not SHA_RE.fullmatch(merged.merge_commit):
                    diagnostic = merged.message or "merge API did not return a full merge commit"
                    self.local.record_remote_failure("expected-head pull-request merge", diagnostic)
                    raise FinishRefused(diagnostic)
                self.report.merge_commit = merged.merge_commit
                self._transition(Stage.MERGED)
                snapshot = self.provider.pull_request(self.pr_number)
                self._validate_pr_identity(snapshot, require_open=False)
                if snapshot.state != "MERGED" or snapshot.merge_commit != merged.merge_commit:
                    raise FinishRefused("post-merge PR requery disagrees with merge API result")

            default = self.provider.default_branch()
            fetched_head = self.local.fetch_default_branch(default.name)
            if fetched_head != default.head:
                raise FinishRefused(
                    f"fetched default branch differs from provider truth: {fetched_head} != {default.head}"
                )
            main = self._wait_main_green(default.name, default.head)
            self.report.default_branch = main.name
            self.report.default_branch_head = main.head
            self.report.main_ci = asdict(main.ci)
            self._transition(Stage.MAIN_CI_VERIFIED)

            post = self.local.post_merge_verify(
                self.pr_number,
                self.expected_head,
                self.truth.evidence_folder,
                post_output,
            )
            self.report.post_merge_output = str(post.output)
            self.report.post_merge_verified = True

            self.local.authorize_remote("verified remote slice-branch deletion")
            try:
                self.provider.delete_branch(self.truth.branch, self.expected_head)
            except FinishRefused as exc:
                self.local.record_remote_failure("verified remote slice-branch deletion", str(exc))
                raise
            self.report.remote_branch_absent = True
            self.local.release_isolation()
            self.report.isolation_released = True
            self.report.recoverable_state_retained = False
            self._transition(Stage.HANDOFF_COMPLETE)
            return 0
        except FinishRefused as exc:
            self.report.failure = str(exc)
            self.report.generated_at = _now()
            try:
                self._persist()
            except OSError:
                pass
            return 1
        except Exception as exc:  # pragma: no cover - final fail-closed guard
            self.report.failure = f"unexpected finish-path error: {exc}"
            self.report.generated_at = _now()
            try:
                self._persist()
            except OSError:
                pass
            return 2


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agent-owned StateDD finish path: exact PR head through verified default branch"
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="Strict agent clone/worktree root")
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--expected-pr-head", required=True, help="Exact 40-character PR head")
    parser.add_argument(
        "--delivery-policy",
        type=Path,
        default=Path("PROJECT_STATE.yaml"),
        help="JSON/YAML containing delivery_policy (default: PROJECT_STATE.yaml)",
    )
    parser.add_argument("--merge-method", choices=sorted(MERGE_METHODS))
    parser.add_argument("--evidence-folder", type=Path, required=True)
    parser.add_argument("--handoff-output", type=Path)
    parser.add_argument(
        "--workflow-path",
        help="Authoritative workflow path (auto-detects the one canonical candidate)",
    )
    parser.add_argument("--branch-head-job", default="branch-head")
    parser.add_argument("--merge-candidate-job", default="merge-candidate")
    parser.add_argument("--pr-ci-timeout", type=float, default=1800)
    parser.add_argument("--main-ci-timeout", type=float, default=1800)
    parser.add_argument("--poll-interval", type=float, default=15)
    parser.add_argument("--agent-context", type=Path)
    parser.add_argument("--restart-session", action="store_true")
    parser.add_argument("--github-token")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    root = args.root.resolve()
    if args.pr_number <= 0:
        print("Finish slice refused: --pr-number must be positive", file=sys.stderr)
        return 2
    policy_path = args.delivery_policy
    if not policy_path.is_absolute():
        policy_path = root / policy_path
    output = args.handoff_output
    if output is None:
        output = root.parent / ".statedd-handoffs" / f"{root.name}-pr-{args.pr_number}.json"
    elif not output.is_absolute():
        output = Path.cwd() / output
    try:
        output.resolve(strict=False).relative_to(root)
    except ValueError:
        pass
    else:
        print("Finish slice refused: --handoff-output must be outside --root", file=sys.stderr)
        return 2
    try:
        policy = load_policy(policy_path.resolve())
        local = RepositoryActions(
            root,
            agent_context=args.agent_context,
            restart_session=args.restart_session,
            workflow_path=args.workflow_path,
            verbose=args.verbose,
        )
        provider = GitHubProvider(
            root,
            token=args.github_token,
            workflow_path=local.workflow_path,
            branch_head_job=args.branch_head_job,
            merge_candidate_job=args.merge_candidate_job,
        )
        finish = FinishSlice(
            local=local,
            provider=provider,
            policy=policy,
            pr_number=args.pr_number,
            expected_head=args.expected_pr_head,
            evidence_folder=args.evidence_folder,
            handoff_output=output,
            merge_method=args.merge_method,
            pr_ci_timeout=args.pr_ci_timeout,
            main_ci_timeout=args.main_ci_timeout,
            poll_interval=args.poll_interval,
        )
    except (FinishRefused, OSError) as exc:
        print(f"Finish slice refused: {exc}", file=sys.stderr)
        return 2
    code = finish.run()
    print(json.dumps(asdict(finish.report), indent=2, sort_keys=True))
    if code:
        print(f"Finish slice stopped at {finish.report.status}: {finish.report.failure}", file=sys.stderr)
    else:
        print(f"Finish slice complete; external handoff: {output}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
