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

SHA_RE = re.compile(r"\b([0-9a-f]{7,40})\b")
HEAD_LINE_RE = re.compile(
    r"^[ \t>*-]*(?:\*\*)?(HEAD|Proof head|Final PR head)(?:\*\*)?\s*[:=]\s*([0-9a-f]+)",
    re.IGNORECASE | re.MULTILINE,
)

AGENT_CONTEXT_SCHEMA = "statedd.agent_context.v1"
AGENT_CONTEXT_FILE = Path(".statedd/agent.context")

PR_FIELDS = """
  number
  headRefOid
  headRefName
  body
  mergeStateStatus
  url
"""

COMMIT_FIELDS = """
  object(expression: $sha) {
    ... on Commit {
      statusCheckRollup {
        state
      }
      checkSuites(first: 10) {
        nodes {
          databaseId
          app {
            name
          }
          workflowRun {
            databaseId
            runNumber
            url
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
    cleaned = url.rstrip("/")
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", cleaned)
    if not match:
        return None
    return match.group(1), match.group(2)


def find_agent_context(root: Path, explicit: str | None = None) -> Path | None:
    """Return the path to an agent context file, or None if not found."""
    candidate: Path
    if explicit:
        path = Path(explicit)
        if path.is_absolute():
            candidate = path
        else:
            candidate = (root / path).resolve()
        # Allow passing the worktree root or the context file itself.
        if candidate.is_dir():
            candidate = candidate / AGENT_CONTEXT_FILE
        return candidate if candidate.exists() else None
    candidate = root / AGENT_CONTEXT_FILE
    return candidate if candidate.exists() else None


def load_agent_context(path: Path) -> dict | None:
    """Load and validate an agent.context JSON file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema") != AGENT_CONTEXT_SCHEMA:
        return None
    return data


def latest_evidence_folder(root: Path) -> Path | None:
    evidence_root = root / "docs" / "evidence"
    if not evidence_root.exists():
        return None
    candidates = [
        entry
        for entry in evidence_root.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


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
    pr_final_head: str | None = field(default=None, init=False)
    proof_head: str | None = field(default=None, init=False)

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
            self._check_remote_contains_head()
            self._resolve_owner_repo()
            self._fetch_pr_and_ci_state()
            self._check_remote_head_unchanged()
            self._check_agent_branch_matches_pr()
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
        self._find_actions_run(commit.get("checkSuites", {}).get("nodes", []))
        self.merge_state = pr.get("mergeStateStatus")

        print(f"\nGitHub truth:")
        print(f"  PR:     #{pr.get('number')} — {pr.get('url')}")
        print(f"  PR head: {pr.get('headRefOid')}")
        print(f"  CI:     {self.ci_state or 'no checks'}")
        if self.ci_run_id:
            print(f"  Run:    {self.ci_run_url or self.ci_run_id}")
        print(f"  Merge:  {self.merge_state}")

    def _find_actions_run(self, suites: list[dict[str, Any]]) -> None:
        for suite in suites:
            app = suite.get("app") or {}
            if app.get("name") != "GitHub Actions":
                continue
            run = suite.get("workflowRun")
            if run and run.get("databaseId"):
                self.ci_run_id = str(run["databaseId"])
                self.ci_run_url = run.get("url")
                return

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
        if not pr_branch or not agent_branch:
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

    def _check_pr_body(self) -> None:
        body = self.pr.get("body") or ""
        marked = extract_marked_heads(body)
        self.proof_head = marked.get("proof_head")

        if self.local_head in body:
            self.pr_final_head = self.local_head
            if self.verbose:
                print("  ✓ PR body references current HEAD")
            return

        final_head = marked.get("final_pr_head")
        if final_head and final_head == self.local_head:
            self.pr_final_head = self.local_head
            if self.verbose:
                print("  ✓ PR body uses explicit proof_head/final_head split")
            return

        self.failures.append(
            "PR body does not reference the current HEAD (use full SHA or explicit Proof head/Final PR head split)"
        )

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

        if not self.ci_run_id:
            self.failures.append("No GitHub Actions run found for current HEAD")
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

    def _check_evidence_heads(self) -> None:
        self.evidence_folder = latest_evidence_folder(self.root)
        if not self.evidence_folder:
            self.warnings.append("No evidence folder found under docs/evidence/; skipping evidence head check")
            return

        manifest = self.evidence_folder / "manifest.json"
        readme = self.evidence_folder / "README.md"
        closure = self.evidence_folder / "closure.json"

        checked = 0
        for path in (manifest, readme, closure):
            if not path.exists():
                continue
            checked += 1
            text = path.read_text(encoding="utf-8")
            if not self._evidence_file_has_current_head(text, path.name):
                self.failures.append(
                    f"Evidence file {path.relative_to(self.root)} does not reference current HEAD "
                    f"({self.local_head})"
                )
            elif self.verbose:
                print(f"  ✓ evidence file agrees with closure HEAD: {path.relative_to(self.root)}")

        if checked == 0:
            self.warnings.append(
                f"Evidence folder {self.evidence_folder.relative_to(self.root)} has no manifest.json, README.md, or closure.json"
            )

    def _evidence_file_has_current_head(self, text: str, filename: str) -> bool:
        marked = extract_marked_heads(text)
        if marked.get("final_pr_head") == self.local_head:
            return True
        if marked.get("head") == self.local_head:
            return True
        # Also allow a repo.head style JSON value.
        if f'"head": "{self.local_head}"' in text or f'"head": "{self.local_head[:7]}' in text:
            return True
        sha_refs = extract_sha_refs(text)
        if self.local_head in sha_refs or self.local_head[:7] in sha_refs:
            return True
        # If the PR body uses an explicit proof_head/final_head split, evidence
        # may reference the proof head instead of the metadata-only final head.
        if (
            self.pr_final_head == self.local_head
            and self.proof_head
            and (self.proof_head in text or self.proof_head in sha_refs)
        ):
            return True
        # If the file mentions any head-like SHA but not the current one, treat as stale.
        if sha_refs:
            return False
        # No SHA references at all: not a head-bearing file.
        return True

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
        print(f"- worktree_clean: {'yes' if not (self._git(['status', '--short'], '') or '').strip() else 'no'}")
        print(f"- closure_label: {self.closure_label}")
        print(f"- evidence_folder: {self.evidence_folder.relative_to(self.root) if self.evidence_folder else 'not found'}")
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
            "ci_state": self.ci_state,
            "merge_state": self.merge_state,
            "worktree_clean": not (self._git(["status", "--short"], "") or "").strip(),
            "closure_label": self.closure_label,
            "evidence_folder": str(self.evidence_folder) if self.evidence_folder else None,
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
    parser.add_argument("--verbose", "-v", action="store_true", help="Print passed checks")
    parser.add_argument(
        "--agent-context",
        default=None,
        help="Path to agent.context JSON (auto-detects .statedd/agent.context if omitted)",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    root = Path(args.root).resolve()
    agent_context_path = find_agent_context(root, args.agent_context)
    agent_context = load_agent_context(agent_context_path) if agent_context_path else None
    finalizer = RemoteClosureFinalizer(
        root=root,
        verbose=args.verbose,
        pr_number=args.pr_number,
        output=args.output,
        github_token=args.github_token,
        agent_context=agent_context,
    )
    return finalizer.run()


if __name__ == "__main__":
    raise SystemExit(main())
