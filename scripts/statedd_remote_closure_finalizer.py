#!/usr/bin/env python3
"""StateDD Remote Closure Finalizer.

Final closure gate: local HEAD, pushed branch, PR head, PR body, in-repo
evidence, the latest GitHub Actions result, and merge state must all agree on
the same final head. No success exit until they do.

Exit codes:
  0 = remote closure verified (CI green, mergeable, all heads agree)
  1 = closure gate failed (conditions not met)
  2 = unexpected runtime error
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.request
from urllib.parse import urlparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

try:
    from statedd_contracts import ContractError, UnsafePathError, confined_path, load_json_file, normalize_relative_path
    from statedd_evidence_pack import command_check as check_evidence_pack, scan_text_file
    from statedd_validate_schema import StateDDYamlError, parse_yaml_text, validate_file
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.statedd_contracts import ContractError, UnsafePathError, confined_path, load_json_file, normalize_relative_path
    from scripts.statedd_evidence_pack import command_check as check_evidence_pack, scan_text_file
    from scripts.statedd_validate_schema import StateDDYamlError, parse_yaml_text, validate_file


ROOT = Path(__file__).resolve().parents[1]

SHA_RE = re.compile(r"\b([0-9a-f]{7,40})\b")
HEAD_LINE_RE = re.compile(
    r"^[ \t>*-]*(?:\*\*)?(HEAD|Proof head|Final PR head)(?:\*\*)?\s*[:=]\s*(?:\*\*)?\s*([0-9a-f]+)",
    re.IGNORECASE | re.MULTILINE,
)

AGENT_CONTEXT_SCHEMA = "statedd.agent_context.v2"
AGENT_CONTEXT_FILE = Path(".statedd/agent.context")
AUTHORITATIVE_WORKFLOW_CANDIDATES = (
    Path(".github/workflows/validate.yml"),
    Path(".github/workflows/statedd-validate.yml"),
)

PR_FIELDS = """
  number
  headRefOid
  headRefName
  body
  isDraft
  reviewDecision
  reviewThreads(first: 100) {
    nodes {
      isResolved
      isOutdated
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
  mergeStateStatus
  url
"""

COMMIT_FIELDS = """
  object(expression: $sha) {
    ... on Commit {
      oid
      statusCheckRollup {
        state
      }
      checkSuites(first: 100) {
        nodes {
          databaseId
          status
          conclusion
          app {
            name
          }
          workflowRun {
            databaseId
            runNumber
            url
            file {
              path
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
"""

PR_BY_NUMBER_QUERY = f"""
query($owner: String!, $repo: String!, $sha: String!, $number: Int!) {{
  repository(owner: $owner, name: $repo) {{
    byNumber: pullRequest(number: $number) {{
{PR_FIELDS}
    }}
{COMMIT_FIELDS}
  }}
}}
"""

PR_BY_BRANCH_QUERY = f"""
query($owner: String!, $repo: String!, $branch: String, $sha: String!) {{
  repository(owner: $owner, name: $repo) {{
    byBranch: pullRequests(headRefName: $branch, states: [OPEN], first: 1) {{
      nodes {{
{PR_FIELDS}
      }}
    }}
{COMMIT_FIELDS}
  }}
}}
"""


def run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a subprocess command and return (code, stdout, stderr)."""
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def git_value(repo: Path, args: list[str], fallback: str | None = None) -> str | None:
    code, stdout, _ = run_command(["git", *args], repo)
    if code != 0:
        return fallback
    return stdout or fallback


def parse_remote_url(url: str) -> tuple[str, str] | None:
    """Return (owner, repo) for a GitHub HTTPS or SSH URL."""
    cleaned = url.rstrip("/")
    scp = re.fullmatch(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?", cleaned)
    if scp:
        return scp.group(1), scp.group(2)
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"https", "ssh"} or parsed.hostname != "github.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        return None
    owner, repo = parts
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        return None
    return owner, repo


def find_agent_context(root: Path, explicit: str | None = None) -> Path | None:
    """Return the path to an agent context file, or None if not found."""
    candidate: Path
    if explicit:
        path = Path(explicit)
        candidate = path if path.is_absolute() else root / path
        # Allow passing the worktree root or the context file itself.
        if candidate.is_dir():
            candidate = candidate / AGENT_CONTEXT_FILE
        if not candidate.exists():
            raise ContractError(f"Explicit agent context does not exist: {candidate}")
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ContractError("Agent context must remain inside the repository worktree") from exc
        return candidate
    candidate = root / AGENT_CONTEXT_FILE
    return candidate if candidate.exists() else None


def load_agent_context(path: Path) -> dict:
    """Strictly load an existing agent context; malformed context is fatal."""
    data = load_json_file(path)
    if not isinstance(data, dict) or data.get("schema") != AGENT_CONTEXT_SCHEMA:
        raise ContractError("Agent context has an unsupported schema")
    required = ("agent_id", "slice_id", "worktree_path", "branch", "base_branch", "isolation_mode")
    for field_name in required:
        if not isinstance(data.get(field_name), str) or not data[field_name]:
            raise ContractError(f"Agent context field {field_name!r} must be a non-empty string")
    if not isinstance(data.get("reservation_ref"), str):
        raise ContractError("Agent context reservation_ref must be a string")
    if data.get("isolation_mode") == "worktree" and not data["reservation_ref"]:
        raise ContractError("Worktree agent context requires a reservation ref")
    return data


def extract_sha_refs(text: str) -> set[str]:
    """Return all 7-40 char hex strings that look like git SHAs."""
    return set(SHA_RE.findall(text.lower()))


def extract_marked_heads(text: str) -> dict[str, str]:
    """Look for HEAD / Proof head / Final PR head markers and return values."""
    found: dict[str, str] = {}
    for match in HEAD_LINE_RE.finditer(text):
        key = match.group(1).lower().replace(" ", "_")
        found[key] = match.group(2).lower()
    return found


def extract_marked_head_lists(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for match in HEAD_LINE_RE.finditer(text):
        key = match.group(1).lower().replace(" ", "_")
        found.setdefault(key, []).append(match.group(2).lower())
    return found


class GitHubApi:
    """Minimal GitHub GraphQL client using `gh` when available, urllib fallback."""

    def __init__(self, root: Path, token: str | None = None):
        self.root = root
        self.token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    def query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        if shutil.which("gh"):
            try:
                return self._query_gh(query, variables)
            except RuntimeError as exc:
                errors.append(f"gh failed: {exc}")
        if self.token:
            try:
                return self._query_urllib(query, variables)
            except RuntimeError as exc:
                errors.append(f"urllib failed: {exc}")
        raise RuntimeError("; ".join(errors) if errors else "No GitHub API backend available")

    def _query_gh(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        args = ["gh", "api", "graphql"]
        for key, value in variables.items():
            if value is None:
                continue
            if isinstance(value, str):
                # Static string variables use --raw-field so they are quoted as JSON strings.
                args.extend(["-f", f"{key}={value}"])
            else:
                # gh's --field applies magic type coercion for integers, booleans, null, etc.
                args.extend(["-F", f"{key}={json.dumps(value)}"])
        args.extend(["-f", f"query={query}"])
        env = os.environ.copy()
        if self.token:
            env["GH_TOKEN"] = self.token
        try:
            completed = subprocess.run(
                args,
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(str(exc))
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or "unknown gh error")
        data = json.loads(completed.stdout)
        if data.get("errors"):
            raise RuntimeError(str(data["errors"]))
        return data.get("data", {})

    def _query_urllib(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables}).encode()
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "statedd-remote-closure-finalizer",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        if data.get("errors"):
            raise RuntimeError(str(data["errors"]))
        return data.get("data", {})


@dataclass
class RemoteClosureFinalizer:
    root: Path
    verbose: bool = False
    pr_number: int | None = None
    output: Path | None = None
    github_token: str | None = None
    run_command_fn: Callable[[list[str], Path], tuple[int, str, str]] = field(
        default_factory=lambda: run_command
    )
    github_client: GitHubApi | None = None
    agent_context: dict | None = None
    evidence_folder_arg: Path | None = None
    workflow_path_arg: Path | None = None
    pr_final_head: str | None = field(default=None, init=False)
    proof_head: str | None = field(default=None, init=False)
    pr_proof_head: str | None = field(default=None, init=False)
    pr_evidence_ref: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.github_client is None:
            self.github_client = GitHubApi(self.root, self.github_token)
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.closure_label = "NOT CLOSURE-GRADE — LOCAL OR UNVERIFIED CLAIM"
        self.local_head: str = ""
        self.branch: str = ""
        self.remote_url: str = ""
        self.owner: str = ""
        self.repo: str = ""
        self.pr: dict[str, Any] = {}
        self.ci_run_id: str | None = None
        self.ci_run_url: str | None = None
        self.ci_state: str | None = None
        self.merge_state: str | None = None
        self.evidence_folder: Path | None = None
        self.remote_head: str | None = None
        self.workflow_path: str = ""
        self.ci_workflow_path: str | None = None
        self.github_requery_completed = False

    def _git(self, args: list[str], fallback: str | None = None) -> str | None:
        code, stdout, _ = self.run_command_fn(["git", *args], self.root)
        if code != 0:
            return fallback
        return stdout or fallback

    def _git_result(self, args: list[str]) -> tuple[int, str, str]:
        return self.run_command_fn(["git", *args], self.root)

    def run(self) -> int:
        print("=" * 60)
        print("StateDD Remote Closure Finalizer")
        print("=" * 60)

        try:
            self._validate_output_path()
            self._collect_local_truth()
            self._resolve_workflow_path()
            self._check_worktree_clean()
            self._check_remote_contains_head()
            self._resolve_owner_repo()
            self._fetch_pr_and_ci_state()
            self._check_remote_head_unchanged()
            self._check_agent_branch_matches_pr()
            self._check_pr_head_agrees()
            self._check_pr_branch_agrees()
            self._check_pr_body()
            self._check_review_state()
            self._check_ci_status()
            self._check_merge_state()
            self._check_evidence_heads()
            self._final_truth_recheck()
        except RuntimeError as exc:
            self.failures.append(str(exc))
        except Exception as exc:
            print(f"\n💥 Remote closure finalizer crashed: {exc}")
            return 2

        if self.failures:
            self._print_handoff()
            print(f"\n❌ REMOTE CLOSURE FINALIZER FAILED — {self.closure_label}")
            for failure in self.failures:
                print(f"  ✗ {failure}")
            return 1

        self._set_closure_label()
        if self.output:
            try:
                self._write_output()
            except OSError as exc:
                self.failures.append(f"Could not write external closure handoff: {exc}")
                self._print_handoff()
                return 1
        self._print_handoff()

        if self.warnings:
            print(f"\n⚠️  REMOTE CLOSURE FINALIZER PASSED WITH WARNINGS — {self.closure_label}")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        else:
            print(f"\n✅ REMOTE CLOSURE FINALIZER PASSED — {self.closure_label}")

        return 0

    def _validate_output_path(self) -> None:
        if self.output is None:
            return
        output = self.output.resolve(strict=False)
        try:
            output.relative_to(self.root.resolve(strict=False))
        except ValueError:
            self.output = output
            return
        raise RuntimeError(
            "Remote closure output must be an external sidecar; writing inside the repository would create post-proof dirt"
        )

    def _collect_local_truth(self) -> None:
        self.local_head = self._git(["rev-parse", "HEAD"], "") or ""
        self.branch = self._git(["branch", "--show-current"], "") or ""
        self.remote_url = self._git(["remote", "get-url", "origin"], "") or ""

        if not self.local_head:
            raise RuntimeError("Could not determine local HEAD")
        if not self.branch:
            raise RuntimeError("Could not determine current branch")
        if not self.remote_url:
            raise RuntimeError("Could not determine origin remote URL")

        print("\nLocal truth:")
        print(f"  branch: {self.branch}")
        print(f"  head:   {self.local_head}")
        print(f"  remote: {self.remote_url}")

    def _resolve_workflow_path(self) -> None:
        """Bind CI proof to the declared workflow and its executable gate contract."""
        manifest_path = self.root / "STATEDD_ASSETS.json"
        required_gate_level: int
        expected_hash: str | None = None
        if manifest_path.is_file() and not manifest_path.is_symlink():
            try:
                manifest = load_json_file(manifest_path)
            except ContractError as exc:
                raise RuntimeError(f"Cannot bind authoritative workflow from asset lock: {exc}") from exc
            if not isinstance(manifest, dict) or manifest.get("schema") != "statedd.runtime_assets.v2":
                raise RuntimeError("Authoritative workflow requires a v2 STATEDD_ASSETS.json lock")
            required_gate_level = manifest.get("required_gate_level")
            if isinstance(required_gate_level, bool) or not isinstance(required_gate_level, int):
                raise RuntimeError("Asset lock required_gate_level is invalid")
            declared_records = [
                record
                for record in manifest.get("managed_assets", [])
                if isinstance(record, dict)
                and record.get("role") == "generated_control"
                and record.get("owner") == "template"
                and record.get("merge_strategy") == "regenerate"
                and record.get("path") == ".github/workflows/statedd-validate.yml"
            ]
            if len(declared_records) != 1:
                raise RuntimeError(
                    "Asset lock must declare exactly one generated StateDD validation workflow"
                )
            relative = Path(declared_records[0]["path"])
            expected_hash = declared_records[0].get("installed_sha256")
            if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                raise RuntimeError("Declared validation workflow has no valid installed hash")
        else:
            state_path = self.root / "PROJECT_STATE.yaml"
            try:
                state = parse_yaml_text(state_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, StateDDYamlError) as exc:
                raise RuntimeError(f"Cannot identify template workflow authority: {exc}") from exc
            workflow = state.get("workflow") if isinstance(state, dict) else None
            if not isinstance(workflow, dict) or workflow.get("repo_role") != "template_repository":
                raise RuntimeError(
                    "No lock-declared downstream workflow or template_repository workflow authority found"
                )
            relative = Path(".github/workflows/validate.yml")
            required_gate_level = 2

        if self.workflow_path_arg is not None:
            if self.workflow_path_arg.is_absolute():
                raise RuntimeError("--workflow-path must be repository-relative")
            try:
                requested = normalize_relative_path(self.workflow_path_arg)
            except UnsafePathError as exc:
                raise RuntimeError(f"Invalid --workflow-path: {exc}") from exc
            if requested != relative:
                raise RuntimeError(
                    f"--workflow-path {requested} is not the declared authoritative workflow {relative}"
                )
        if (
            relative.parent != Path(".github/workflows")
            or relative.suffix.lower() not in {".yml", ".yaml"}
        ):
            raise RuntimeError("Authoritative workflow must be a YAML file under .github/workflows")
        try:
            path = confined_path(self.root, relative)
        except UnsafePathError as exc:
            raise RuntimeError(f"Unsafe authoritative workflow path: {exc}") from exc
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Authoritative workflow is missing or unsafe: {relative}")
        content = path.read_bytes()
        if expected_hash is not None and hashlib.sha256(content).hexdigest() != expected_hash:
            raise RuntimeError("Authoritative workflow bytes do not match the asset-lock installed hash")
        try:
            workflow_payload = parse_yaml_text(content.decode("utf-8"))
        except (UnicodeDecodeError, StateDDYamlError) as exc:
            raise RuntimeError(f"Authoritative workflow is malformed: {exc}") from exc
        jobs = workflow_payload.get("jobs") if isinstance(workflow_payload, dict) else None
        authoritative_steps: list[dict[str, Any]] = []
        if isinstance(jobs, dict):
            for job in jobs.values():
                if not isinstance(job, dict) or job.get("if") is not None or job.get("continue-on-error") is True:
                    continue
                steps = job.get("steps")
                if not isinstance(steps, list):
                    continue
                authoritative_steps.extend(
                    step
                    for step in steps
                    if isinstance(step, dict)
                    and step.get("if") is None
                    and step.get("continue-on-error") is not True
                    and isinstance(step.get("run"), str)
                )
        expected_tokens = [
            "python3",
            "scripts/statedd_quality_gate.py",
            "--gate-level",
            str(required_gate_level),
            "--conformance",
        ]
        matching = []
        for step in authoritative_steps:
            try:
                tokens = shlex.split(step["run"])
            except ValueError:
                continue
            if tokens in (expected_tokens, [*expected_tokens, "--verbose"]):
                matching.append(step)
        if len(matching) != 1:
            raise RuntimeError(
                "Authoritative workflow must invoke exactly one unconditional StateDD quality gate "
                f"at level {required_gate_level} with --conformance"
            )
        code, _, _ = self._git_result(["cat-file", "-e", f"HEAD:{relative.as_posix()}"])
        if code != 0:
            raise RuntimeError(f"Authoritative workflow is not tracked at exact HEAD: {relative}")
        self.workflow_path = relative.as_posix()

    def _check_worktree_clean(self) -> None:
        status = self._git(["status", "--short"], "") or ""
        if status.strip():
            self.failures.append(f"Worktree is dirty:\n{status}")
        elif self.verbose:
            print("  ✓ worktree clean")

    def _check_remote_contains_head(self) -> None:
        output = self._git(["ls-remote", "origin", self.branch], "") or ""
        remote_sha = output.split("\t")[0] if "\t" in output else ""
        self.remote_head = remote_sha
        if not remote_sha:
            self.failures.append(f"Branch '{self.branch}' not found on origin")
        elif remote_sha != self.local_head:
            self.failures.append(
                f"Remote branch head ({remote_sha}) does not match local HEAD ({self.local_head})"
            )
        elif self.verbose:
            print("  ✓ remote branch contains local HEAD")

    def _resolve_owner_repo(self) -> None:
        parsed = parse_remote_url(self.remote_url)
        if not parsed:
            self.failures.append(f"Could not parse GitHub owner/repo from remote: {self.remote_url}")
            return
        self.owner, self.repo = parsed
        if self.verbose:
            print(f"  ✓ GitHub owner/repo: {self.owner}/{self.repo}")

    def _fetch_pr_and_ci_state(
        self,
        *,
        selected_pr_number: int | None = None,
        announce: bool = True,
    ) -> None:
        if not self.owner or not self.repo:
            raise RuntimeError("Cannot query GitHub without owner/repo")

        query_pr_number = selected_pr_number if selected_pr_number is not None else self.pr_number
        if query_pr_number is not None:
            query = PR_BY_NUMBER_QUERY
            variables: dict[str, Any] = {
                "owner": self.owner,
                "repo": self.repo,
                "sha": self.local_head,
                "number": query_pr_number,
            }
        else:
            query = PR_BY_BRANCH_QUERY
            variables = {
                "owner": self.owner,
                "repo": self.repo,
                "branch": self.branch,
                "sha": self.local_head,
            }
        data = self.github_client.query(query, variables)
        repository = data.get("repository", {})

        # Resolve the PR either by explicit number or by branch.
        pr = repository.get("byNumber") if query_pr_number is not None else None
        if query_pr_number is None and repository.get("byBranch"):
            nodes = repository["byBranch"].get("nodes", [])
            if nodes:
                pr = nodes[0]
        if not pr:
            raise RuntimeError(f"No open PR found for branch '{self.branch}'")
        self.pr = pr

        commit = repository.get("object", {}) or {}
        if commit.get("oid") != self.local_head:
            self.failures.append(
                f"GitHub commit query returned oid {commit.get('oid')!r}, expected {self.local_head}"
            )
        rollup = commit.get("statusCheckRollup") or {}
        self.ci_state = rollup.get("state")
        self.ci_run_id = None
        self.ci_run_url = None
        self.ci_workflow_path = None
        suites_connection = commit.get("checkSuites")
        if not isinstance(suites_connection, dict):
            self.failures.append("GitHub check-suite connection is unavailable")
            suites = []
        else:
            suites = suites_connection.get("nodes")
            page_info = suites_connection.get("pageInfo")
            if not isinstance(suites, list) or not isinstance(page_info, dict):
                self.failures.append("GitHub check-suite pagination state is unavailable")
                suites = []
            elif not isinstance(page_info.get("hasNextPage"), bool):
                self.failures.append("GitHub check-suite pageInfo.hasNextPage is unavailable")
            elif page_info["hasNextPage"]:
                self.failures.append(
                    "More than 100 check suites exist; closure refuses incomplete CI enumeration"
                )
        self._find_actions_run(suites)
        self.merge_state = pr.get("mergeStateStatus")

        if announce:
            print("\nGitHub truth:")
            print(f"  PR:     #{pr.get('number')} — {pr.get('url')}")
            print(f"  PR head: {pr.get('headRefOid')}")
            print(f"  CI:     {self.ci_state or 'no checks'}")
            if self.ci_run_id:
                print(f"  Run:    {self.ci_run_url or self.ci_run_id}")
            print(f"  Workflow: {self.ci_workflow_path or 'not found'}")
            print(f"  Merge:  {self.merge_state}")

    def _find_actions_run(self, suites: list[dict[str, Any]]) -> None:
        matches: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
        for suite in suites:
            if not isinstance(suite, dict):
                continue
            app = suite.get("app") or {}
            if app.get("name") != "GitHub Actions":
                continue
            run = suite.get("workflowRun")
            file_block = run.get("file") if isinstance(run, dict) else None
            workflow_path = file_block.get("path") if isinstance(file_block, dict) else None
            if workflow_path != self.workflow_path:
                continue
            if suite.get("status") != "COMPLETED" or suite.get("conclusion") != "SUCCESS":
                self.failures.append(
                    f"Authoritative workflow {self.workflow_path} is not successfully completed "
                    f"(status={suite.get('status')}, conclusion={suite.get('conclusion')})"
                )
                continue
            if isinstance(run, dict) and run.get("databaseId"):
                try:
                    ordering = int(run["databaseId"])
                except (TypeError, ValueError):
                    ordering = -1
                matches.append((ordering, suite, run))
        if not matches:
            return
        _, _, selected = max(matches, key=lambda item: item[0])
        self.ci_run_id = str(selected["databaseId"])
        self.ci_run_url = selected.get("url")
        self.ci_workflow_path = self.workflow_path

    def _check_remote_head_unchanged(self) -> None:
        """Re-check remote HEAD after fetching PR state to catch interleaved pushes."""
        output = self._git(["ls-remote", "origin", self.branch], "") or ""
        remote_sha = output.split("\t")[0] if "\t" in output else ""
        if not remote_sha:
            self.failures.append(f"Could not re-check remote HEAD for branch '{self.branch}'")
        elif remote_sha != self.local_head:
            self.failures.append(
                f"Remote HEAD changed during finalization: expected {self.local_head}, found {remote_sha}"
            )
        elif self.verbose:
            print("  ✓ remote HEAD unchanged since initial check")

    def _check_agent_branch_matches_pr(self) -> None:
        """In agent context, ensure the PR branch matches the reserved agent branch."""
        if not self.agent_context:
            return
        agent_branch = self.agent_context.get("branch", "")
        pr_branch = self.pr.get("headRefName", "") if self.pr else ""
        context_worktree = Path(self.agent_context["worktree_path"])
        if context_worktree.absolute() != self.root.absolute():
            self.failures.append(
                f"Agent context worktree {context_worktree} does not match current root {self.root}"
            )
        if agent_branch != self.branch:
            self.failures.append(
                f"Agent context branch '{agent_branch}' does not match current branch '{self.branch}'"
            )
        if not pr_branch:
            self.failures.append("PR head branch is unavailable")
            return
        if pr_branch != agent_branch:
            self.failures.append(
                f"PR branch '{pr_branch}' does not match agent branch '{agent_branch}'; "
                "another agent may have pushed to a different branch for this slice"
            )
        elif self.verbose:
            print("  ✓ PR branch matches agent branch")

    def _check_pr_head_agrees(self) -> None:
        pr_head = self.pr.get("headRefOid", "")
        if pr_head != self.local_head:
            self.failures.append(
                f"PR head ({pr_head}) does not match local HEAD ({self.local_head})"
            )
        elif self.verbose:
            print("  ✓ PR head matches local HEAD")

    def _check_pr_branch_agrees(self) -> None:
        pr_branch = self.pr.get("headRefName")
        if not isinstance(pr_branch, str) or not pr_branch:
            self.failures.append("PR head branch is unavailable")
        elif pr_branch != self.branch:
            self.failures.append(
                f"PR branch '{pr_branch}' does not match current branch '{self.branch}'"
            )
        elif self.verbose:
            print("  ✓ PR branch matches current branch")

    def _check_pr_body(self) -> None:
        body = self.pr.get("body") or ""
        marked = extract_marked_head_lists(body)
        proof_values = marked.get("proof_head", [])
        final_values = marked.get("final_pr_head", [])
        if len(proof_values) != 1 or not re.fullmatch(r"[0-9a-f]{40}", proof_values[0] if proof_values else ""):
            self.failures.append("PR body must contain exactly one full `Proof head:` marker")
        else:
            self.pr_proof_head = proof_values[0]
        if len(final_values) != 1 or not re.fullmatch(r"[0-9a-f]{40}", final_values[0] if final_values else ""):
            self.failures.append("PR body must contain exactly one full `Final PR head:` marker")
        elif final_values[0] != self.local_head:
            self.failures.append(
                f"PR body final head ({final_values[0]}) does not match local HEAD ({self.local_head})"
            )
        else:
            self.pr_final_head = final_values[0]

        evidence_refs = re.findall(r"docs/evidence/[A-Za-z0-9._-]+", body)
        if len(evidence_refs) != 1:
            self.failures.append("PR body must reference exactly one docs/evidence/<folder> path")
        else:
            self.pr_evidence_ref = evidence_refs[0]

    def _check_review_state(self) -> None:
        if not isinstance(self.pr.get("isDraft"), bool):
            self.failures.append("PR draft state is unavailable")
        elif self.pr.get("isDraft") is True:
            self.failures.append("PR is still draft")
        if "reviewDecision" not in self.pr:
            self.failures.append("PR review decision metadata is unavailable")
        review_decision = self.pr.get("reviewDecision")
        if review_decision in {"CHANGES_REQUESTED", "REVIEW_REQUIRED"}:
            self.failures.append(f"PR review decision is {review_decision}")
        review_threads = self.pr.get("reviewThreads")
        if not isinstance(review_threads, dict) or not isinstance(review_threads.get("nodes"), list):
            self.failures.append("PR unresolved-review-thread state is unavailable")
            return
        page_info = review_threads.get("pageInfo")
        if not isinstance(page_info, dict) or not isinstance(page_info.get("hasNextPage"), bool):
            self.failures.append("PR review-thread pagination state is unavailable")
            return
        if page_info["hasNextPage"]:
            self.failures.append(
                "More than 100 review threads exist; closure refuses incomplete review enumeration"
            )
        threads = review_threads["nodes"]
        unresolved = [
            thread
            for thread in threads
            if isinstance(thread, dict)
            and thread.get("isResolved") is not True
            and thread.get("isOutdated") is not True
        ]
        if unresolved:
            self.failures.append(f"PR has {len(unresolved)} unresolved current review thread(s)")

    def _check_ci_status(self) -> None:
        if not self.ci_state:
            self.failures.append("No CI check rollup found for current HEAD")
            return
        if self.ci_state == "SUCCESS":
            if self.verbose:
                print("  ✓ CI check rollup reports SUCCESS")
        elif self.ci_state == "PENDING":
            self.failures.append(f"CI is still pending on current HEAD ({self.ci_state})")
        else:
            self.failures.append(f"CI did not succeed on current HEAD ({self.ci_state})")

        if not self.ci_run_id or self.ci_workflow_path != self.workflow_path:
            self.failures.append(
                f"No successful authoritative GitHub Actions run for {self.workflow_path} at current HEAD"
            )
        elif self.verbose:
            print(f"  ✓ GitHub Actions run ID: {self.ci_run_id}")

    def _check_merge_state(self) -> None:
        allowed = {"CLEAN", "HAS_HOOKS", "MERGED"}
        if self.merge_state in allowed:
            if self.verbose:
                print(f"  ✓ mergeStateStatus is {self.merge_state}")
            return
        self.failures.append(
            f"mergeStateStatus is '{self.merge_state}', expected one of {allowed}"
        )

    def _evidence_candidates(self) -> list[Path]:
        evidence_root = self.root / "docs" / "evidence"
        if not evidence_root.is_dir() or evidence_root.is_symlink():
            return []
        return sorted(
            (
                entry
                for entry in evidence_root.iterdir()
                if entry.is_dir() and not entry.is_symlink() and not entry.name.startswith(".")
            ),
            key=lambda path: path.name,
        )

    def _select_evidence_folder(self) -> Path | None:
        evidence_root = self.root / "docs" / "evidence"
        candidates = self._evidence_candidates()
        if self.pr_evidence_ref is None:
            self.failures.append("Cannot select evidence without one explicit PR-body evidence reference")
            return None
        body_selected = (self.root / self.pr_evidence_ref).resolve(strict=False)
        if body_selected not in candidates:
            self.failures.append(f"PR-referenced evidence folder is missing or unsafe: {self.pr_evidence_ref}")
            return None

        if self.evidence_folder_arg is not None:
            raw = self.evidence_folder_arg
            requested = raw if raw.is_absolute() else self.root / raw
            try:
                selected = requested.resolve(strict=False)
                selected.relative_to(evidence_root.resolve(strict=False))
            except ValueError:
                self.failures.append(f"Evidence folder is outside docs/evidence: {raw}")
                return None
            if selected not in candidates:
                self.failures.append(f"Evidence folder is missing, symlinked, or invalid: {raw}")
                return None
            if selected != body_selected:
                self.failures.append("--evidence-folder does not match the unique PR-body evidence reference")
                return None
        return body_selected

    def _require_tracked_at_head(self, path: Path) -> None:
        try:
            rel = path.relative_to(self.root).as_posix()
        except ValueError:
            self.failures.append(f"Evidence path is outside repository: {path}")
            return
        code, _, _ = self._git_result(["ls-files", "--error-unmatch", "--", rel])
        if code != 0:
            self.failures.append(f"Evidence path is not tracked: {rel}")
            return
        code, _, _ = self._git_result(["cat-file", "-e", f"HEAD:{rel}"])
        if code != 0:
            self.failures.append(f"Evidence path is not present in exact final HEAD: {rel}")

    def _check_evidence_heads(self) -> None:
        self.evidence_folder = self._select_evidence_folder()
        if self.evidence_folder is None:
            return
        manifest_path = self.evidence_folder / "manifest.json"
        readme_path = self.evidence_folder / "README.md"
        if not manifest_path.is_file() or manifest_path.is_symlink():
            self.failures.append("Selected evidence folder has no regular manifest.json")
            return
        if not readme_path.is_file() or readme_path.is_symlink():
            self.failures.append("Selected evidence folder has no regular README.md")
            return

        schema_path = self.root / "schemas" / "evidence_manifest.schema.json"
        if not schema_path.exists():
            schema_path = ROOT / "schemas" / "evidence_manifest.schema.json"
        try:
            issues = validate_file(manifest_path, schema_path)
            manifest = load_json_file(manifest_path)
        except (ContractError, OSError, UnicodeDecodeError) as exc:
            self.failures.append(f"Evidence manifest could not be validated: {exc}")
            return
        if issues:
            self.failures.extend(
                f"Evidence manifest schema failure {issue.path}: {issue.message}" for issue in issues
            )
            return
        if check_evidence_pack(self.evidence_folder, strict=True) != 0:
            self.failures.append("Evidence manifest failed strict evidence-pack validation")
            return
        if not isinstance(manifest, dict):
            self.failures.append("Evidence manifest root is not an object")
            return
        if self.agent_context and manifest.get("slice_id") != self.agent_context.get("slice_id"):
            self.failures.append(
                f"Evidence slice_id {manifest.get('slice_id')!r} does not match agent slice_id "
                f"{self.agent_context.get('slice_id')!r}"
            )

        readme_text = readme_path.read_text(encoding="utf-8")
        readme_heads = extract_marked_head_lists(readme_text)
        readme_proof = readme_heads.get("proof_head", [])
        readme_final = readme_heads.get("final_pr_head", [])
        if len(readme_proof) != 1:
            self.failures.append("Evidence README must contain exactly one Proof head marker")
        if readme_final:
            self.failures.append(
                "Tracked evidence README must not claim its containing final commit; exact Final PR head belongs in the mutable PR body"
            )

        repo = manifest.get("repo")
        proof_head = repo.get("head") if isinstance(repo, dict) else None
        evidence_branch = repo.get("branch") if isinstance(repo, dict) else None
        if evidence_branch != self.branch:
            self.failures.append(
                f"Evidence manifest branch ({evidence_branch!r}) does not match current branch ({self.branch!r})"
            )
        if not isinstance(proof_head, str) or not re.fullmatch(r"[0-9a-f]{40}", proof_head):
            self.failures.append("Evidence manifest repo.head must be one full 40-character proof commit")
            return
        self.proof_head = proof_head
        if self.pr_proof_head != proof_head:
            self.failures.append(
                f"PR body proof head ({self.pr_proof_head}) does not match evidence proof head ({proof_head})"
            )
        if len(readme_proof) == 1 and readme_proof[0] != proof_head:
            self.failures.append(
                f"Evidence README proof head ({readme_proof[0]}) does not match manifest ({proof_head})"
            )
        code, _, _ = self._git_result(["merge-base", "--is-ancestor", proof_head, self.local_head])
        if code != 0:
            self.failures.append(
                f"Evidence proof head {proof_head} is not an ancestor of final head {self.local_head}"
            )
            return

        code, diff_output, diff_error = self._git_result(
            ["diff", "--name-only", f"{proof_head}..{self.local_head}"]
        )
        if code != 0:
            self.failures.append(f"Could not inspect proof-to-final diff: {diff_error}")
            return
        evidence_prefix = self.evidence_folder.relative_to(self.root).as_posix() + "/"
        allowed_exact = {
            "STATUS.md",
            "PROJECT_STATE.yaml",
            "NEXT_ACTIONS.md",
            "BACKLOG.md",
            "WORKLOG.md",
            "docs/EVIDENCE_LOG.md",
        }
        disallowed = [
            path
            for path in diff_output.splitlines()
            if path
            and path not in allowed_exact
            and not path.startswith(evidence_prefix)
            and path != "docs/metrics/profile_metrics.json"
        ]
        if disallowed:
            self.failures.append(
                "Proof-to-final commits contain non-finalization changes: " + ", ".join(disallowed)
            )
        for relative in diff_output.splitlines():
            if relative not in allowed_exact and relative != "docs/metrics/profile_metrics.json":
                continue
            try:
                finalization_path = confined_path(self.root, normalize_relative_path(relative))
            except UnsafePathError as exc:
                self.failures.append(f"Unsafe finalization metadata path {relative!r}: {exc}")
                continue
            if finalization_path.is_symlink() or not finalization_path.is_file():
                self.failures.append(f"Finalization metadata is not a regular file: {relative}")
                continue
            sensitive_status, findings = scan_text_file(finalization_path)
            if sensitive_status != "none_found":
                self.failures.append(
                    f"Finalization metadata privacy scan failed for {relative}: {findings}"
                )

        self._require_tracked_at_head(manifest_path)
        self._require_tracked_at_head(readme_path)
        artifacts = manifest.get("artifacts")
        if isinstance(artifacts, list):
            for artifact in artifacts:
                raw = artifact.get("path") if isinstance(artifact, dict) else None
                if not isinstance(raw, str):
                    continue
                try:
                    artifact_path = confined_path(self.evidence_folder, normalize_relative_path(raw))
                except UnsafePathError as exc:
                    self.failures.append(f"Unsafe evidence artifact path {raw!r}: {exc}")
                    continue
                self._require_tracked_at_head(artifact_path)
        if self.verbose and not self.failures:
            print(
                f"  ✓ typed evidence proof {proof_head} is tracked in exact final HEAD with finalization-only successors"
            )

    def _final_truth_recheck(self) -> None:
        """Re-prove Git truth, then make a final exact-PR GitHub query."""
        current_head = self._git(["rev-parse", "HEAD"], "") or ""
        status = self._git(["status", "--short"], "") or ""
        output = self._git(["ls-remote", "origin", self.branch], "") or ""
        remote_sha = output.split("\t")[0] if "\t" in output else ""
        if current_head != self.local_head:
            self.failures.append(
                f"Local HEAD changed during finalization: expected {self.local_head}, found {current_head}"
            )
        if status.strip():
            self.failures.append(f"Worktree became dirty during finalization:\n{status}")
        if remote_sha != self.local_head:
            self.failures.append(
                f"Remote HEAD changed before final label: expected {self.local_head}, found {remote_sha or 'not found'}"
            )
        selected_pr_number = self.pr.get("number") if self.pr else None
        expected_evidence_ref = self.pr_evidence_ref
        expected_proof_head = self.proof_head
        if not isinstance(selected_pr_number, int):
            self.failures.append("Cannot make final GitHub requery without an exact PR number")
            return

        # Clear mutable PR-body bindings so an earlier valid snapshot cannot
        # survive a malformed or stale final response.
        self.pr_proof_head = None
        self.pr_final_head = None
        self.pr_evidence_ref = None
        self._fetch_pr_and_ci_state(
            selected_pr_number=selected_pr_number,
            announce=False,
        )
        self._check_pr_head_agrees()
        self._check_pr_branch_agrees()
        self._check_agent_branch_matches_pr()
        self._check_pr_body()
        self._check_review_state()
        self._check_ci_status()
        self._check_merge_state()
        if self.pr.get("number") != selected_pr_number:
            self.failures.append("Final GitHub requery returned a different pull request")
        if self.pr_proof_head != expected_proof_head:
            self.failures.append(
                "Final GitHub PR body no longer matches the validated evidence proof head"
            )
        if self.pr_evidence_ref != expected_evidence_ref:
            self.failures.append(
                "Final GitHub PR body no longer references the validated evidence folder"
            )
        self.github_requery_completed = True

    def _set_closure_label(self) -> None:
        if self.merge_state == "MERGED":
            self.closure_label = "merged"
        elif (
            self.github_requery_completed
            and self.ci_state == "SUCCESS"
            and self.ci_run_id
            and self.ci_workflow_path == self.workflow_path
        ):
            self.closure_label = "CI verified"
        elif self.pr:
            self.closure_label = "PR opened"
        elif self.remote_head == self.local_head:
            self.closure_label = "pushed"
        else:
            self.closure_label = "local-only"

    def _print_handoff(self) -> None:
        now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
        print("\n" + "=" * 60)
        print("Remote Closure Handoff")
        print("=" * 60)
        print(f"- generated_at: {now}")
        print(f"- repo_path: {self.root}")
        print(f"- branch: {self.branch}")
        print(f"- local_head: {self.local_head}")
        print(f"- pr_head: {self.pr.get('headRefOid') if self.pr else 'not found'}")
        print(f"- pr_number: {self.pr.get('number') if self.pr else 'not found'}")
        print(f"- pr_url: {self.pr.get('url') if self.pr else 'not found'}")
        print(f"- ci_run_id: {self.ci_run_id or 'not found'}")
        print(f"- ci_run_url: {self.ci_run_url or 'not found'}")
        print(f"- ci_workflow_path: {self.ci_workflow_path or 'not found'}")
        print(f"- github_final_requery: {'yes' if self.github_requery_completed else 'no'}")
        print(f"- ci_state: {self.ci_state or 'not found'}")
        print(f"- merge_state: {self.merge_state or 'not found'}")
        print(f"- worktree_clean: {'yes' if not (self._git(['status', '--short'], '') or '').strip() else 'no'}")
        print(f"- closure_label: {self.closure_label}")
        print(f"- evidence_folder: {self.evidence_folder.relative_to(self.root) if self.evidence_folder else 'not found'}")
        print(f"- evidence_proof_head: {self.proof_head or 'not found'}")
        if self.agent_context:
            print(f"- agent_id: {self.agent_context.get('agent_id', 'not found')}")
            print(f"- slice_id: {self.agent_context.get('slice_id', 'not found')}")
            print(f"- reservation_ref: {self.agent_context.get('reservation_ref', 'not found')}")

        risks = list(self.warnings)
        if self.failures:
            risks.extend(self.failures)
        if not risks:
            risks.append("none")
        print("- remaining_risks:")
        for risk in risks:
            print(f"  - {risk}")

    def _write_output(self) -> None:
        artifact = {
            "schema": "statedd.remote_closure_handoff.v1",
            "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
            "repo_path": str(self.root),
            "branch": self.branch,
            "local_head": self.local_head,
            "remote_url": self.remote_url,
            "pr_head": self.pr.get("headRefOid") if self.pr else None,
            "pr_number": self.pr.get("number") if self.pr else None,
            "pr_url": self.pr.get("url") if self.pr else None,
            "ci_run_id": self.ci_run_id,
            "ci_run_url": self.ci_run_url,
            "ci_workflow_path": self.ci_workflow_path,
            "github_final_requery": self.github_requery_completed,
            "ci_state": self.ci_state,
            "merge_state": self.merge_state,
            "worktree_clean": not (self._git(["status", "--short"], "") or "").strip(),
            "closure_label": self.closure_label,
            "evidence_folder": str(self.evidence_folder) if self.evidence_folder else None,
            "evidence_proof_head": self.proof_head,
            "failures": self.failures,
            "warnings": self.warnings,
        }
        if self.agent_context:
            artifact["agent_id"] = self.agent_context.get("agent_id")
            artifact["slice_id"] = self.agent_context.get("slice_id")
            artifact["reservation_ref"] = self.agent_context.get("reservation_ref")
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\nWrote remote closure handoff: {self.output}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="StateDD Remote Closure Finalizer: verify pushed PR/CI state before calling a slice done"
    )
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect")
    parser.add_argument("--pr-number", type=int, default=None, help="Explicit PR number")
    parser.add_argument("--github-token", default=None, help="GitHub token (fallback: GH_TOKEN / GITHUB_TOKEN env)")
    parser.add_argument("--output", "-o", type=Path, help="Write handoff JSON to this path")
    parser.add_argument(
        "--evidence-folder",
        type=Path,
        help="Explicit evidence folder under docs/evidence (required when selection is ambiguous)",
    )
    parser.add_argument(
        "--workflow-path",
        type=Path,
        help="Repository-relative authoritative GitHub Actions workflow (auto-detected when unique)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print passed checks")
    parser.add_argument(
        "--agent-context",
        default=None,
        help="Path to agent.context JSON (auto-detects .statedd/agent.context if omitted)",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    try:
        from statedd_contracts import safe_root_path
    except ModuleNotFoundError:  # pragma: no cover
        from scripts.statedd_contracts import safe_root_path
    try:
        root = safe_root_path(args.root, must_exist=True)
        agent_context_path = find_agent_context(root, args.agent_context)
        agent_context = load_agent_context(agent_context_path) if agent_context_path else None
    except (ContractError, UnsafePathError, OSError) as exc:
        print(f"Remote closure finalizer refused: {exc}")
        return 1
    finalizer = RemoteClosureFinalizer(
        root=root,
        verbose=args.verbose,
        pr_number=args.pr_number,
        output=args.output,
        github_token=args.github_token,
        agent_context=agent_context,
        evidence_folder_arg=args.evidence_folder,
        workflow_path_arg=args.workflow_path,
    )
    return finalizer.run()


if __name__ == "__main__":
    raise SystemExit(main())
