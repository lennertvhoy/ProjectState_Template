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
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]

HEAD_LINE_RE = re.compile(
    r"^[ \t>*-]*(?:\*\*)?(HEAD|Proof head|Final PR head)(?:\*\*)?\s*[:=]\s*([0-9a-f]{40})\s*(?:\*\*)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

PR_FIELDS = """
  number
  headRefOid
  body
  baseRef {
    name
    branchProtectionRule {
      requiresStatusChecks
      requiredStatusChecks {
        context
        app {
          id
        }
      }
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
        contexts(first: 100) {
          nodes {
            __typename
            ... on CheckRun {
              name
              status
              conclusion
              checkSuite {
                app {
                  id
                  databaseId
                  name
                  slug
                }
                commit {
                  oid
                }
                workflowRun {
                  databaseId
                  runNumber
                  url
                }
              }
            }
            ... on StatusContext {
              context
              state
            }
          }
          pageInfo {
            hasNextPage
          }
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
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not match:
        return None
    return match.group(1), match.group(2)


def extract_marked_heads(text: str) -> dict[str, str]:
    """Parse the explicit PR/evidence head contract from anchored fields."""
    found: dict[str, str] = {}
    for match in HEAD_LINE_RE.finditer(text):
        key = match.group(1).lower().replace(" ", "_")
        found[key] = match.group(2).lower()
    return found


def _required_check_specs(
    protection: dict[str, Any] | None,
    explicit_names: list[str] | tuple[str, ...],
) -> list[dict[str, str | None]]:
    specs: list[dict[str, str | None]] = []
    if isinstance(protection, dict) and protection.get("requiresStatusChecks") is True:
        raw_specs = protection.get("requiredStatusChecks")
        if isinstance(raw_specs, list):
            for raw in raw_specs:
                if not isinstance(raw, dict) or not isinstance(raw.get("context"), str):
                    continue
                app = raw.get("app") if isinstance(raw.get("app"), dict) else {}
                specs.append({"context": raw["context"], "app_id": app.get("id")})
    for name in explicit_names:
        specs.append({"context": name, "app_id": None})

    unique: dict[tuple[str, str | None], dict[str, str | None]] = {}
    for spec in specs:
        unique[(str(spec["context"]), spec["app_id"])] = spec
    return list(unique.values())


def verify_ci_commit(
    commit: dict[str, Any] | None,
    protection: dict[str, Any] | None,
    expected_head: str,
    explicit_required_checks: list[str] | tuple[str, ...] = (),
) -> tuple[list[str], dict[str, Any] | None, list[str]]:
    """Validate exact-head required checks and return a required Actions run."""
    failures: list[str] = []
    observed_names: list[str] = []
    if not isinstance(commit, dict):
        return ["No CI commit object found for current HEAD"], None, observed_names

    commit_head = str(commit.get("oid") or "").lower()
    if commit_head != expected_head.lower():
        failures.append(
            f"CI commit head ({commit_head or 'missing'}) does not match expected head ({expected_head})"
        )

    rollup = commit.get("statusCheckRollup")
    if not isinstance(rollup, dict):
        failures.append("No CI check rollup found for current HEAD")
        return failures, None, observed_names
    if rollup.get("state") != "SUCCESS":
        failures.append(f"CI check rollup did not succeed on current HEAD ({rollup.get('state') or 'missing'})")

    contexts = rollup.get("contexts")
    if not isinstance(contexts, dict):
        failures.append("CI check contexts are missing for current HEAD")
        return failures, None, observed_names
    page_info = contexts.get("pageInfo")
    if isinstance(page_info, dict) and page_info.get("hasNextPage") is True:
        failures.append("CI check context query was truncated; required checks cannot be proven")
    nodes = contexts.get("nodes")
    if not isinstance(nodes, list):
        failures.append("CI check contexts are malformed for current HEAD")
        return failures, None, observed_names

    specs = _required_check_specs(protection, explicit_required_checks)
    if not specs:
        failures.append("No required CI checks are configured or explicitly declared")
        return failures, None, observed_names

    required_actions_run: dict[str, Any] | None = None
    for spec in specs:
        context = str(spec["context"])
        app_id = spec["app_id"]
        matches: list[dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            name = node.get("name") if node.get("__typename") == "CheckRun" else node.get("context")
            if isinstance(name, str):
                observed_names.append(name)
            if name != context:
                continue
            if app_id is not None:
                suite = node.get("checkSuite") if isinstance(node.get("checkSuite"), dict) else {}
                app = suite.get("app") if isinstance(suite.get("app"), dict) else {}
                if app.get("id") != app_id:
                    continue
            matches.append(node)

        if not matches:
            failures.append(f"Required CI check '{context}' is missing from current HEAD")
            continue

        successful = False
        for node in matches:
            node_type = node.get("__typename")
            if node_type == "CheckRun":
                if node.get("status") != "COMPLETED":
                    failures.append(
                        f"Required CI check '{context}' is not completed ({node.get('status') or 'missing'})"
                    )
                    continue
                if node.get("conclusion") != "SUCCESS":
                    failures.append(
                        f"Required CI check '{context}' did not succeed ({node.get('conclusion') or 'missing'})"
                    )
                    continue
                suite = node.get("checkSuite") if isinstance(node.get("checkSuite"), dict) else {}
                suite_commit = suite.get("commit") if isinstance(suite.get("commit"), dict) else {}
                suite_head = str(suite_commit.get("oid") or "").lower()
                if suite_head != expected_head.lower():
                    failures.append(
                        f"Required CI check '{context}' belongs to stale head {suite_head or 'missing'}"
                    )
                    continue
                successful = True
                app = suite.get("app") if isinstance(suite.get("app"), dict) else {}
                run = suite.get("workflowRun") if isinstance(suite.get("workflowRun"), dict) else None
                if (
                    (app.get("slug") == "github-actions" or app.get("name") == "GitHub Actions")
                    and run
                    and run.get("databaseId")
                ):
                    required_actions_run = run
            elif node_type == "StatusContext":
                if node.get("state") == "SUCCESS":
                    successful = True
                else:
                    failures.append(
                        f"Required CI status '{context}' did not succeed ({node.get('state') or 'missing'})"
                    )
        if not successful and not any(context in failure for failure in failures):
            failures.append(f"Required CI check '{context}' has no successful current-head result")

    if required_actions_run is None:
        failures.append("No successful required GitHub Actions run found for current HEAD")
    return failures, required_actions_run, sorted(set(observed_names))


def select_evidence_manifest(
    root: Path,
    *,
    head: str,
    branch: str,
    slice_id: str | None,
    privacy_profile: str = "public",
) -> tuple[Path | None, dict[str, Any] | None, list[str]]:
    """Load the shared evidence contract for one slice, branch, and exact head."""
    try:
        from statedd_validate_schema import ArtifactContractError, load_evidence_bundle
    except ImportError as exc:
        return None, None, [f"Shared evidence validator is unavailable: {exc}"]

    evidence_root = root / "docs" / "evidence"
    if not evidence_root.is_dir():
        return None, None, ["No evidence root found under docs/evidence/"]

    resolved_slice = slice_id
    if resolved_slice is None:
        inferred: set[str] = set()
        for manifest_path in sorted(evidence_root.glob("*/manifest.json")):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            repo = data.get("repo") if isinstance(data.get("repo"), dict) else {}
            candidate_slice = data.get("slice_id")
            if (
                repo.get("branch") == branch
                and repo.get("head") == head.lower()
                and isinstance(candidate_slice, str)
                and candidate_slice
            ):
                inferred.add(candidate_slice)
        if len(inferred) != 1:
            detail = "none" if not inferred else ", ".join(sorted(inferred))
            return None, None, [
                f"Could not infer one evidence slice for branch {branch}, exact head {head}; candidates: {detail}"
            ]
        resolved_slice = next(iter(inferred))

    try:
        bundle = load_evidence_bundle(
            root,
            resolved_slice,
            head,
            privacy_profile=privacy_profile,
        )
    except ArtifactContractError as exc:
        return None, None, [f"Evidence artifact contract failed: {exc}"]

    repo = bundle.manifest.get("repo")
    manifest_branch = repo.get("branch") if isinstance(repo, dict) else None
    if manifest_branch != branch:
        return None, None, [
            f"Evidence manifest branch ({manifest_branch or 'missing'}) does not match expected branch ({branch})"
        ]
    return bundle.directory, bundle.manifest, []


class GitHubApi:
    """Minimal GitHub GraphQL client using `gh` when available, urllib fallback."""

    def __init__(self, token: str | None = None):
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
        code, out, err = run_command(args, Path.cwd())
        if code != 0:
            raise RuntimeError(err or out or "unknown gh error")
        data = json.loads(out)
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
    slice_id: str | None = None
    required_checks: list[str] = field(default_factory=list)
    privacy_profile: str = "public"
    run_command_fn: Callable[[list[str], Path], tuple[int, str, str]] = field(
        default_factory=lambda: run_command
    )
    github_client: GitHubApi | None = None
    pr_final_head: str | None = field(default=None, init=False)
    proof_head: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.github_client is None:
            self.github_client = GitHubApi(self.github_token)
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
        self.upstream_ref: str | None = None
        self.upstream_head: str | None = None
        self.worktree_clean = False
        self.required_check_names: list[str] = []

    def _git(self, args: list[str], fallback: str | None = None) -> str | None:
        code, stdout, _ = self.run_command_fn(["git", *args], self.root)
        if code != 0:
            return fallback
        return stdout or fallback

    def run(self) -> int:
        print("=" * 60)
        print("StateDD Remote Closure Finalizer")
        print("=" * 60)

        try:
            self._collect_local_truth()
            self._check_worktree_clean()
            self._check_upstream_equality()
            self._check_remote_contains_head()
            self._resolve_owner_repo()
            self._fetch_pr_and_ci_state()
            self._check_pr_head_agrees()
            self._check_pr_body()
            self._check_ci_status()
            self._check_merge_state()
            self._check_evidence_heads()
        except RuntimeError as exc:
            self.failures.append(str(exc))
        except Exception as exc:
            print(f"\n💥 Remote closure finalizer crashed: {exc}")
            return 2

        if not self.failures:
            self._set_closure_label()

        self._print_handoff()

        if self.failures:
            print(f"\n❌ REMOTE CLOSURE FINALIZER FAILED — {self.closure_label}")
            for failure in self.failures:
                print(f"  ✗ {failure}")
            return 1

        if self.warnings:
            print(f"\n⚠️  REMOTE CLOSURE FINALIZER PASSED WITH WARNINGS — {self.closure_label}")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        else:
            print(f"\n✅ REMOTE CLOSURE FINALIZER PASSED — {self.closure_label}")

        if self.output:
            self._write_output()

        return 0 if not self.failures else 1

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

        print(f"\nLocal truth:")
        print(f"  branch: {self.branch}")
        print(f"  head:   {self.local_head}")
        print(f"  remote: {self.remote_url}")

    def _check_worktree_clean(self) -> None:
        code, status, err = self.run_command_fn(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            self.root,
        )
        self.worktree_clean = code == 0 and not status.strip()
        if code != 0:
            self.failures.append(f"Could not inspect worktree status: {err or 'git status failed'}")
        elif status.strip():
            self.failures.append(f"Worktree is dirty:\n{status}")
        elif self.verbose:
            print("  ✓ worktree clean")

    def _check_upstream_equality(self) -> None:
        code, upstream, err = self.run_command_fn(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
            self.root,
        )
        expected = f"origin/{self.branch}"
        self.upstream_ref = upstream.strip() if code == 0 else None
        if code != 0 or self.upstream_ref != expected:
            self.failures.append(
                "Current branch has no matching upstream: "
                + (err or f"expected {expected}, got {self.upstream_ref or 'missing'}")
            )

        code, upstream_head, err = self.run_command_fn(
            ["git", "rev-parse", "@{upstream}"],
            self.root,
        )
        self.upstream_head = upstream_head.strip().lower() if code == 0 else None
        if code != 0 or self.upstream_head != self.local_head.lower():
            self.failures.append(
                "Upstream tracking head does not match local HEAD: "
                + (err or f"{self.upstream_head or 'missing'} != {self.local_head}")
            )
        elif self.verbose:
            print("  ✓ upstream tracking ref equals local HEAD")

    def _check_remote_contains_head(self) -> None:
        code, output, err = self.run_command_fn(
            ["git", "ls-remote", "--heads", "origin", f"refs/heads/{self.branch}"],
            self.root,
        )
        lines = [line.split("\t", 1) for line in output.splitlines() if "\t" in line]
        matching = [parts[0].lower() for parts in lines if parts[1] == f"refs/heads/{self.branch}"]
        remote_sha = matching[0] if len(matching) == 1 else ""
        self.remote_head = remote_sha
        if code != 0:
            self.failures.append(f"Could not read origin branch head: {err or 'git ls-remote failed'}")
        elif not remote_sha:
            self.failures.append(f"Branch '{self.branch}' not found uniquely on origin")
        elif remote_sha != self.local_head.lower() or remote_sha != self.upstream_head:
            self.failures.append(
                f"Remote branch head ({remote_sha}) does not match local HEAD "
                f"({self.local_head}) and upstream ({self.upstream_head or 'missing'})"
            )
        elif self.verbose:
            print(f"  ✓ remote branch contains local HEAD")

    def _resolve_owner_repo(self) -> None:
        parsed = parse_remote_url(self.remote_url)
        if not parsed:
            self.failures.append(f"Could not parse GitHub owner/repo from remote: {self.remote_url}")
            return
        self.owner, self.repo = parsed
        if self.verbose:
            print(f"  ✓ GitHub owner/repo: {self.owner}/{self.repo}")

    def _fetch_pr_and_ci_state(self) -> None:
        if not self.owner or not self.repo:
            raise RuntimeError("Cannot query GitHub without owner/repo")

        if self.pr_number is not None:
            query = PR_BY_NUMBER_QUERY
            variables: dict[str, Any] = {
                "owner": self.owner,
                "repo": self.repo,
                "sha": self.local_head,
                "number": self.pr_number,
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
        pr = repository.get("byNumber")
        if not pr and repository.get("byBranch"):
            nodes = repository["byBranch"].get("nodes", [])
            if nodes:
                pr = nodes[0]
        if not pr:
            raise RuntimeError(f"No open PR found for branch '{self.branch}'")
        self.pr = pr

        commit = repository.get("object", {}) or {}
        rollup = commit.get("statusCheckRollup") or {}
        self.ci_state = rollup.get("state")
        base_ref = pr.get("baseRef") if isinstance(pr.get("baseRef"), dict) else {}
        protection = (
            base_ref.get("branchProtectionRule")
            if isinstance(base_ref.get("branchProtectionRule"), dict)
            else None
        )
        ci_failures, actions_run, observed = verify_ci_commit(
            commit,
            protection,
            self.local_head,
            self.required_checks,
        )
        self.failures.extend(ci_failures)
        self.required_check_names = observed
        if actions_run:
            self.ci_run_id = str(actions_run["databaseId"])
            self.ci_run_url = actions_run.get("url")
        self.merge_state = pr.get("mergeStateStatus")

        print(f"\nGitHub truth:")
        print(f"  PR:     #{pr.get('number')} — {pr.get('url')}")
        print(f"  PR head: {pr.get('headRefOid')}")
        print(f"  CI:     {self.ci_state or 'no checks'}")
        if self.ci_run_id:
            print(f"  Run:    {self.ci_run_url or self.ci_run_id}")
        print(f"  Merge:  {self.merge_state}")

    def _check_pr_head_agrees(self) -> None:
        pr_head = self.pr.get("headRefOid", "")
        if pr_head != self.local_head:
            self.failures.append(
                f"PR head ({pr_head}) does not match local HEAD ({self.local_head})"
            )
        elif self.verbose:
            print("  ✓ PR head matches local HEAD")

    def _check_pr_body(self) -> None:
        body = self.pr.get("body") or ""
        marked = extract_marked_heads(body)
        self.proof_head = marked.get("proof_head")
        final_head = marked.get("final_pr_head")
        if final_head and final_head == self.local_head:
            self.pr_final_head = self.local_head
            if self.verbose:
                print("  ✓ PR body uses explicit proof_head/final_head split")
            return

        self.failures.append(
            "PR body does not declare the exact current HEAD in an explicit Final PR head field"
        )

    def _check_ci_status(self) -> None:
        # Detailed CI failures are produced while parsing the exact commit and
        # its required contexts. This method only reports the positive receipt.
        if self.ci_state == "SUCCESS" and self.ci_run_id and self.verbose:
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

    def _check_evidence_heads(self) -> None:
        folder, manifest_data, errors = select_evidence_manifest(
            self.root,
            head=self.local_head,
            branch=self.branch,
            slice_id=self.slice_id,
            privacy_profile=self.privacy_profile,
        )
        self.failures.extend(errors)
        self.evidence_folder = folder
        if folder is None or manifest_data is None:
            return

        if self.slice_id is None:
            self.slice_id = str(manifest_data["slice_id"])
        if self.verbose:
            print(f"  ✓ evidence manifest matches slice/branch/exact head: {folder.relative_to(self.root)}")

        closure = folder / "closure.json"
        if not closure.exists():
            return
        try:
            data = json.loads(closure.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.failures.append(f"Evidence closure artifact is malformed: {exc}")
            return
        if not isinstance(data, dict):
            self.failures.append("Evidence closure artifact is not a JSON object")
            return
        for field_name in ("local_head", "pr_head", "final_pr_head"):
            if field_name in data and data.get(field_name) != self.local_head:
                self.failures.append(
                    f"Evidence closure field {field_name} ({data.get(field_name)}) does not match current HEAD ({self.local_head})"
                )

    def _set_closure_label(self) -> None:
        if self.merge_state == "MERGED":
            self.closure_label = "merged"
        elif self.ci_state == "SUCCESS" and self.ci_run_id:
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
        print(f"- ci_state: {self.ci_state or 'not found'}")
        print(f"- merge_state: {self.merge_state or 'not found'}")
        print(f"- upstream_ref: {self.upstream_ref or 'not found'}")
        print(f"- upstream_head: {self.upstream_head or 'not found'}")
        print(f"- remote_head: {self.remote_head or 'not found'}")
        print(f"- worktree_clean: {'yes' if self.worktree_clean else 'no'}")
        print(f"- closure_label: {self.closure_label}")
        print(f"- evidence_folder: {self.evidence_folder.relative_to(self.root) if self.evidence_folder else 'not found'}")

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
            "upstream_ref": self.upstream_ref,
            "upstream_head": self.upstream_head,
            "remote_head": self.remote_head,
            "pr_head": self.pr.get("headRefOid") if self.pr else None,
            "pr_number": self.pr.get("number") if self.pr else None,
            "pr_url": self.pr.get("url") if self.pr else None,
            "ci_run_id": self.ci_run_id,
            "ci_run_url": self.ci_run_url,
            "ci_state": self.ci_state,
            "merge_state": self.merge_state,
            "worktree_clean": self.worktree_clean,
            "closure_label": self.closure_label,
            "slice_id": self.slice_id,
            "required_checks_observed": self.required_check_names,
            "evidence_folder": str(self.evidence_folder) if self.evidence_folder else None,
            "failures": self.failures,
            "warnings": self.warnings,
        }
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\nWrote remote closure handoff: {self.output}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="StateDD Remote Closure Finalizer: verify pushed PR/CI state before calling a slice done"
    )
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect")
    parser.add_argument("--pr-number", type=int, default=None, help="Explicit PR number")
    parser.add_argument("--slice-id", default=None, help="Exact evidence slice_id to verify")
    parser.add_argument(
        "--privacy-profile",
        choices=["public", "private", "local_only"],
        default="public",
        help="Required evidence privacy profile",
    )
    parser.add_argument(
        "--required-check",
        action="append",
        default=[],
        help="Required CI context when branch protection does not expose it (repeatable)",
    )
    parser.add_argument("--github-token", default=None, help="GitHub token (fallback: GH_TOKEN / GITHUB_TOKEN env)")
    parser.add_argument("--output", "-o", type=Path, help="Write handoff JSON to this path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print passed checks")
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    finalizer = RemoteClosureFinalizer(
        root=Path(args.root).resolve(),
        verbose=args.verbose,
        pr_number=args.pr_number,
        output=args.output,
        github_token=args.github_token,
        slice_id=args.slice_id,
        required_checks=args.required_check,
        privacy_profile=args.privacy_profile,
    )
    return finalizer.run()


if __name__ == "__main__":
    raise SystemExit(main())
