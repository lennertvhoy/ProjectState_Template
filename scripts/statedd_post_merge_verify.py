#!/usr/bin/env python3
"""StateDD Post-Merge Main Verifier.

After a PR merges, this gate proves that `main` (or the repo default branch) is
now the source of truth and that the closure artifacts agree with GitHub truth.

Exit codes:
  0 = post-merge main verified
  1 = verification failed
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

DEFAULT_BRANCH_QUERY = """
query($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    defaultBranchRef {
      name
      target {
        oid
      }
    }
  }
}
"""

PR_QUERY = """
query($owner: String!, $repo: String!, $number: Int!, $sha: String!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      number
      headRefOid
      mergeCommit {
        oid
      }
      merged
      state
      body
      mergeStateStatus
      url
    }
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
  }
}
"""


def run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
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


def parse_remote_url(url: str) -> tuple[str, str] | None:
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not match:
        return None
    return match.group(1), match.group(2)


class GitHubApi:
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
                args.extend(["-f", f"{key}={value}"])
            else:
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
                "User-Agent": "statedd-post-merge-verify",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        if data.get("errors"):
            raise RuntimeError(str(data["errors"]))
        return data.get("data", {})


@dataclass
class PostMergeVerifier:
    root: Path
    pr_number: int
    verbose: bool = False
    github_token: str | None = None
    run_command_fn: Callable[[list[str], Path], tuple[int, str, str]] = field(
        default_factory=lambda: run_command
    )
    github_client: GitHubApi | None = None

    def __post_init__(self) -> None:
        if self.github_client is None:
            self.github_client = GitHubApi(self.github_token)
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.local_head: str = ""
        self.branch: str = ""
        self.remote_url: str = ""
        self.owner: str = ""
        self.repo: str = ""
        self.default_branch: str = ""
        self.default_branch_head: str = ""
        self.pr: dict[str, Any] = {}
        self.ci_state: str | None = None
        self.ci_run_id: str | None = None
        self.ci_run_url: str | None = None

    def _git(self, args: list[str], fallback: str | None = None) -> str | None:
        code, stdout, _ = self.run_command_fn(["git", *args], self.root)
        if code != 0:
            return fallback
        return stdout or fallback

    def run(self) -> int:
        print("=" * 60)
        print("StateDD Post-Merge Main Verifier")
        print("=" * 60)

        try:
            self._collect_local_truth()
            self._resolve_owner_repo()
            self._fetch_default_branch()
            self._fetch_pr_state()
            self._check_pr_merged()
            self._check_main_contains_merge()
            self._check_ci_on_final_commit()
            self._check_closure_artifacts()
        except RuntimeError as exc:
            self.failures.append(str(exc))
        except Exception as exc:
            print(f"\n💥 Post-merge verifier crashed: {exc}")
            return 2

        self._print_handoff()

        if self.failures:
            print(f"\n❌ POST-MERGE VERIFICATION FAILED")
            for failure in self.failures:
                print(f"  ✗ {failure}")
            return 1

        if self.warnings:
            print(f"\n⚠️  POST-MERGE VERIFICATION PASSED WITH WARNINGS")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        else:
            print(f"\n✅ POST-MERGE VERIFICATION PASSED — main is the source of truth")

        return 0

    def _collect_local_truth(self) -> None:
        self.local_head = self._git(["rev-parse", "HEAD"], "") or ""
        self.branch = self._git(["branch", "--show-current"], "") or ""
        self.remote_url = self._git(["remote", "get-url", "origin"], "") or ""

        if not self.local_head:
            raise RuntimeError("Could not determine local HEAD")
        if not self.remote_url:
            raise RuntimeError("Could not determine origin remote URL")

        print(f"\nLocal truth:")
        print(f"  branch: {self.branch}")
        print(f"  head:   {self.local_head}")
        print(f"  remote: {self.remote_url}")

    def _resolve_owner_repo(self) -> None:
        parsed = parse_remote_url(self.remote_url)
        if not parsed:
            self.failures.append(f"Could not parse GitHub owner/repo from remote: {self.remote_url}")
            return
        self.owner, self.repo = parsed
        if self.verbose:
            print(f"  ✓ GitHub owner/repo: {self.owner}/{self.repo}")

    def _fetch_default_branch(self) -> None:
        if not self.owner or not self.repo:
            raise RuntimeError("Cannot query GitHub without owner/repo")
        data = self.github_client.query(
            DEFAULT_BRANCH_QUERY,
            {"owner": self.owner, "repo": self.repo},
        )
        repository = data.get("repository", {})
        default_ref = repository.get("defaultBranchRef", {}) or {}
        self.default_branch = default_ref.get("name", "")
        target = default_ref.get("target", {}) or {}
        self.default_branch_head = target.get("oid", "")

        if not self.default_branch:
            raise RuntimeError("Could not determine default branch from GitHub")
        if not self.default_branch_head:
            raise RuntimeError("Could not determine default branch HEAD from GitHub")

        print(f"\nGitHub default branch:")
        print(f"  branch: {self.default_branch}")
        print(f"  head:   {self.default_branch_head}")

    def _fetch_pr_state(self) -> None:
        if not self.default_branch_head:
            raise RuntimeError("Cannot fetch PR state without default branch HEAD")
        data = self.github_client.query(
            PR_QUERY,
            {
                "owner": self.owner,
                "repo": self.repo,
                "number": self.pr_number,
                "sha": self.default_branch_head,
            },
        )
        repository = data.get("repository", {})
        pr = repository.get("pullRequest", {})
        if not pr:
            raise RuntimeError(f"PR #{self.pr_number} not found")
        self.pr = pr

        commit = repository.get("object", {}) or {}
        rollup = commit.get("statusCheckRollup") or {}
        self.ci_state = rollup.get("state")
        self._find_actions_run(commit.get("checkSuites", {}).get("nodes", []))

        print(f"\nPR #{self.pr_number}:")
        print(f"  state:   {pr.get('state')}")
        print(f"  merged:  {pr.get('merged')}")
        print(f"  PR head: {pr.get('headRefOid')}")
        print(f"  merge commit: {pr.get('mergeCommit', {}).get('oid')}")
        print(f"  CI:      {self.ci_state or 'no checks'}")
        if self.ci_run_id:
            print(f"  Run:     {self.ci_run_url or self.ci_run_id}")

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
            if suite.get("databaseId"):
                self.ci_run_id = str(suite["databaseId"])
                return

    def _check_pr_merged(self) -> None:
        pr = self.pr
        if pr.get("state") != "MERGED":
            self.failures.append(f"PR #{self.pr_number} state is '{pr.get('state')}', expected MERGED")
        if not pr.get("merged"):
            self.failures.append(f"PR #{self.pr_number} is not marked as merged")
        merge_commit = (pr.get("mergeCommit") or {}).get("oid", "")
        if not merge_commit:
            self.failures.append(f"PR #{self.pr_number} has no merge commit")

    def _check_main_contains_merge(self) -> None:
        merge_commit = (self.pr.get("mergeCommit") or {}).get("oid", "")
        if not merge_commit:
            return
        # Ensure the remote default branch head is present locally before ancestry check.
        if self.default_branch:
            fetch_code, _, fetch_err = self.run_command_fn(
                ["git", "fetch", "origin", self.default_branch],
                self.root,
            )
            if fetch_code != 0:
                self.failures.append(
                    f"Could not fetch origin/{self.default_branch}: {fetch_err or 'unknown error'}"
                )
                return
        # Check that the merge commit is an ancestor of default branch HEAD
        code, _, _ = self.run_command_fn(
            ["git", "merge-base", "--is-ancestor", merge_commit, self.default_branch_head],
            self.root,
        )
        if code != 0:
            self.failures.append(
                f"Merge commit {merge_commit} is not an ancestor of default branch HEAD {self.default_branch_head}"
            )
        elif self.verbose:
            print(f"  ✓ merge commit is on default branch")

    def _check_ci_on_final_commit(self) -> None:
        if not self.ci_state:
            self.failures.append("No CI check rollup found for default branch HEAD")
            return
        if self.ci_state == "SUCCESS":
            if self.verbose:
                print("  ✓ CI check rollup reports SUCCESS on default branch HEAD")
        elif self.ci_state == "PENDING":
            self.failures.append(f"CI is still pending on default branch HEAD ({self.ci_state})")
        else:
            self.failures.append(f"CI did not succeed on default branch HEAD ({self.ci_state})")

        if not self.ci_run_id:
            self.failures.append("No GitHub Actions run found for default branch HEAD")

    def _check_closure_artifacts(self) -> None:
        evidence_root = self.root / "docs" / "evidence"
        candidates = [
            entry
            for entry in evidence_root.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        ]
        if not candidates:
            self.warnings.append("No evidence folder found under docs/evidence/")
            return
        folder = max(candidates, key=lambda p: p.stat().st_mtime)

        closure = folder / "closure.json"
        readme = folder / "README.md"
        manifest = folder / "manifest.json"

        merge_commit = (self.pr.get("mergeCommit") or {}).get("oid", "")
        pr_head = self.pr.get("headRefOid", "")

        checked = 0
        for path in (closure, readme, manifest):
            if not path.exists():
                continue
            checked += 1
            text = path.read_text(encoding="utf-8")
            sha_refs = set(SHA_RE.findall(text.lower()))
            expected = {sha for sha in (merge_commit, pr_head) if sha}
            missing = expected - sha_refs
            if missing:
                self.failures.append(
                    f"{path.relative_to(self.root)} does not reference expected SHAs: {', '.join(sorted(missing))}"
                )
            elif self.verbose:
                print(f"  ✓ {path.relative_to(self.root)} agrees with PR merge commit/head")

        if checked == 0:
            self.warnings.append(f"Evidence folder {folder.relative_to(self.root)} has no closure.json, README.md, or manifest.json")

    def _print_handoff(self) -> None:
        now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
        print("\n" + "=" * 60)
        print("Post-Merge Verification Handoff")
        print("=" * 60)
        print(f"- generated_at: {now}")
        print(f"- repo_path: {self.root}")
        print(f"- local_head: {self.local_head}")
        print(f"- default_branch: {self.default_branch}")
        print(f"- default_branch_head: {self.default_branch_head}")
        print(f"- pr_number: {self.pr_number}")
        print(f"- pr_url: {self.pr.get('url')}")
        print(f"- pr_head: {self.pr.get('headRefOid')}")
        print(f"- merge_commit: {(self.pr.get('mergeCommit') or {}).get('oid')}")
        print(f"- ci_state: {self.ci_state or 'not found'}")
        print(f"- ci_run_id: {self.ci_run_id or 'not found'}")

        risks = list(self.warnings)
        if self.failures:
            risks.extend(self.failures)
        if not risks:
            risks.append("none")
        print("- remaining_risks:")
        for risk in risks:
            print(f"  - {risk}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="StateDD Post-Merge Main Verifier: prove main is the source of truth after a merge"
    )
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect")
    parser.add_argument("--pr-number", type=int, required=True, help="Merged PR number")
    parser.add_argument("--github-token", default=None, help="GitHub token (fallback: GH_TOKEN / GITHUB_TOKEN env)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print passed checks")
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    verifier = PostMergeVerifier(
        root=Path(args.root).resolve(),
        pr_number=args.pr_number,
        verbose=args.verbose,
        github_token=args.github_token,
    )
    return verifier.run()


if __name__ == "__main__":
    raise SystemExit(main())
