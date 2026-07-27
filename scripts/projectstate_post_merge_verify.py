#!/usr/bin/env python3
"""Verify a merged PR without requiring tracked files to predict merge truth.

The tracked evidence bundle is immutable pre-merge proof.  It binds claims,
tests, artifact hashes, and a proof commit.  The mutable PR body binds that
proof commit to the exact final PR head and evidence folder.  GitHub supplies
the merge commit and default-branch head after merge; this verifier records
those post-merge identities only in an external handoff.

Exit codes:
  0 = post-merge default-branch truth and CI verified
  1 = verification failed
  2 = unexpected runtime error
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]

FULL_SHA_RE = re.compile(r"[0-9a-f]{40}")
HEAD_LINE_RE = re.compile(
    r"^[ \t>*-]*(?:\*\*)?(HEAD|Proof head|Final PR head)(?:\*\*)?\s*[:=]\s*"
    r"(?:\*\*)?\s*([0-9a-f]+)",
    re.IGNORECASE | re.MULTILINE,
)
EVIDENCE_REF_RE = re.compile(r"(?<![A-Za-z0-9._/-])(docs/evidence/[A-Za-z0-9._-]+)(?![A-Za-z0-9._/-])")
FUTURE_SHA_MARKER_RE = re.compile(
    r"^[ \t>*-]*(?:\*\*)?(?:merge commit|merge commit sha|default branch head|main head)"
    r"(?:\*\*)?\s*[:=]\s*(?:\*\*)?\s*[0-9a-f]{7,40}\b",
    re.IGNORECASE | re.MULTILINE,
)
FUTURE_IDENTITY_KEYS = {
    "merge_commit",
    "merge_commit_sha",
    "default_branch_head",
    "main_head",
    "main_ci_run",
    "main_ci_run_id",
}

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
      headRefName
      baseRefName
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


def stable_patch_id(root: Path, base: str, target: str) -> tuple[str | None, str | None]:
    """Return Git's stable patch-id for one aggregate base..target diff."""
    try:
        diff = subprocess.run(
            [
                "git",
                "diff",
                "--binary",
                "--full-index",
                "--no-ext-diff",
                base,
                target,
                "--",
            ],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if diff.returncode != 0:
        return None, diff.stderr.decode(errors="replace").strip() or "git diff failed"
    try:
        patch = subprocess.run(
            ["git", "patch-id", "--stable"],
            cwd=root,
            input=diff.stdout,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if patch.returncode != 0:
        return None, patch.stderr.decode(errors="replace").strip() or "git patch-id failed"
    output = patch.stdout.decode(errors="replace").strip()
    if not output:
        return None, "diff produced no stable patch-id"
    patch_id = output.split()[0]
    if not re.fullmatch(r"[0-9a-f]{40,64}", patch_id):
        return None, f"unexpected patch-id output: {output}"
    return patch_id, None


def parse_remote_url(url: str) -> tuple[str, str] | None:
    cleaned = url.rstrip("/")
    match = re.fullmatch(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?", cleaned)
    if not match:
        match = re.fullmatch(r"(?:https|ssh)://(?:git@)?github\.com/([^/]+)/([^/]+?)(?:\.git)?", cleaned)
    if not match:
        return None
    return match.group(1), match.group(2)


def extract_marked_head_lists(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for match in HEAD_LINE_RE.finditer(text):
        key = match.group(1).lower().replace(" ", "_")
        found.setdefault(key, []).append(match.group(2).lower())
    return found


def strict_json_object(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def nested_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key).lower())
            keys.update(nested_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(nested_keys(nested))
    return keys


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    expected_pr_head: str
    evidence_folder_arg: Path
    output: Path | None = None
    verbose: bool = False
    github_token: str | None = None
    run_command_fn: Callable[[list[str], Path], tuple[int, str, str]] = field(
        default_factory=lambda: run_command
    )
    patch_id_fn: Callable[[Path, str, str], tuple[str | None, str | None]] = field(
        default_factory=lambda: stable_patch_id
    )
    github_client: GitHubApi | None = None

    def __post_init__(self) -> None:
        if self.github_client is None:
            self.github_client = GitHubApi(self.github_token)
        self.root = self.root.resolve()
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.local_head = ""
        self.branch = ""
        self.remote_url = ""
        self.owner = ""
        self.repo = ""
        self.default_branch = ""
        self.default_branch_head = ""
        self.pr: dict[str, Any] = {}
        self.ci_state: str | None = None
        self.ci_run_id: str | None = None
        self.ci_run_url: str | None = None
        self.ci_workflow_path: str | None = None
        self.proof_head: str | None = None
        self.proof_tree: str | None = None
        self.pr_tree: str | None = None
        self.merge_tree: str | None = None
        self.content_identity_method: str | None = None
        self.evidence_folder: Path | None = None
        self.source_hashes: dict[str, str] = {}

    def _git_result(self, args: list[str]) -> tuple[int, str, str]:
        return self.run_command_fn(["git", *args], self.root)

    def _git(self, args: list[str], fallback: str | None = None) -> str | None:
        code, stdout, _ = self._git_result(args)
        return stdout or fallback if code == 0 else fallback

    def run(self) -> int:
        print("=" * 64)
        print("StateDD Post-Merge Main Verifier")
        print("=" * 64)
        try:
            self._validate_inputs()
            self._collect_local_truth()
            self._resolve_owner_repo()
            self._fetch_default_branch_truth()
            self._fetch_pr_state()
            self._check_pr_and_body_binding()
            self._fetch_remote_commits()
            self._check_main_contains_merge()
            self._check_content_identity()
            self._check_ci_on_default_head()
            self._check_tracked_evidence()
        except RuntimeError as exc:
            self.failures.append(str(exc))
        except Exception as exc:  # pragma: no cover - defensive CLI boundary
            print(f"\nPost-merge verifier crashed: {exc}")
            return 2

        self._write_external_handoff()
        self._print_handoff()
        if self.failures:
            print("\nPOST-MERGE VERIFICATION FAILED")
            for failure in self.failures:
                print(f"  - {failure}")
            return 1
        print("\nPOST-MERGE VERIFICATION PASSED — remote default branch and CI are verified")
        return 0

    def _validate_inputs(self) -> None:
        if not self.root.is_dir() or self.root.is_symlink():
            raise RuntimeError(f"Repository root must be a real directory: {self.root}")
        if not FULL_SHA_RE.fullmatch(self.expected_pr_head):
            raise RuntimeError("--expected-pr-head must be one full 40-character lowercase SHA")
        if self.pr_number <= 0:
            raise RuntimeError("--pr-number must be positive")

    def _collect_local_truth(self) -> None:
        self.local_head = self._git(["rev-parse", "HEAD"], "") or ""
        self.branch = self._git(["branch", "--show-current"], "") or ""
        self.remote_url = self._git(["remote", "get-url", "origin"], "") or ""
        status = self._git(["status", "--short"], "") or ""
        if not self.local_head or not self.remote_url:
            raise RuntimeError("Could not determine local HEAD and origin")
        if self.local_head != self.expected_pr_head:
            self.failures.append(
                f"Local HEAD {self.local_head} does not equal expected PR head {self.expected_pr_head}"
            )
        if status.strip():
            self.failures.append(f"Worktree is dirty before post-merge verification:\n{status}")
        print(f"\nLocal: {self.branch or '(detached)'} @ {self.local_head}")

    def _resolve_owner_repo(self) -> None:
        parsed = parse_remote_url(self.remote_url)
        if not parsed:
            self.failures.append(f"Could not parse GitHub owner/repo from origin: {self.remote_url}")
            return
        self.owner, self.repo = parsed

    def _fetch_default_branch_truth(self) -> None:
        if not self.owner or not self.repo:
            raise RuntimeError("Cannot query GitHub without owner/repo")
        data = self.github_client.query(
            DEFAULT_BRANCH_QUERY,
            {"owner": self.owner, "repo": self.repo},
        )
        default_ref = (data.get("repository") or {}).get("defaultBranchRef") or {}
        self.default_branch = default_ref.get("name") or ""
        self.default_branch_head = (default_ref.get("target") or {}).get("oid") or ""
        if not self.default_branch or not FULL_SHA_RE.fullmatch(self.default_branch_head):
            raise RuntimeError("GitHub did not return a valid default branch and full HEAD")
        code, _, err = self._git_result(["check-ref-format", "--branch", self.default_branch])
        if code != 0:
            raise RuntimeError(f"GitHub returned an unsafe default branch name: {err or self.default_branch}")
        print(f"GitHub default: {self.default_branch} @ {self.default_branch_head}")

    def _fetch_pr_state(self) -> None:
        data = self.github_client.query(
            PR_QUERY,
            {
                "owner": self.owner,
                "repo": self.repo,
                "number": self.pr_number,
                "sha": self.default_branch_head,
            },
        )
        repository = data.get("repository") or {}
        self.pr = repository.get("pullRequest") or {}
        if not self.pr:
            raise RuntimeError(f"PR #{self.pr_number} not found")
        commit = repository.get("object") or {}
        if commit.get("oid") != self.default_branch_head:
            self.failures.append("CI query subject does not equal GitHub default-branch HEAD")
        self.ci_state = (commit.get("statusCheckRollup") or {}).get("state")
        suites = commit.get("checkSuites") or {}
        page_info = suites.get("pageInfo") or {}
        if page_info.get("hasNextPage") is True:
            self.failures.append("More than 100 default-head check suites exist; CI enumeration is incomplete")
        self._find_actions_run(suites.get("nodes") or [])
        print(
            f"PR #{self.pr_number}: {self.pr.get('state')} head={self.pr.get('headRefOid')} "
            f"merge={(self.pr.get('mergeCommit') or {}).get('oid')}"
        )

    def _find_actions_run(self, suites: list[dict[str, Any]]) -> None:
        successful: list[tuple[str, str | None, str | None]] = []
        for suite in suites:
            if not isinstance(suite, dict) or (suite.get("app") or {}).get("name") != "GitHub Actions":
                continue
            run = suite.get("workflowRun") or {}
            if suite.get("conclusion") != "SUCCESS" or not run.get("databaseId"):
                continue
            successful.append(
                (
                    str(run["databaseId"]),
                    run.get("url"),
                    (run.get("file") or {}).get("path"),
                )
            )
        if successful:
            self.ci_run_id, self.ci_run_url, self.ci_workflow_path = successful[0]

    def _check_pr_and_body_binding(self) -> None:
        if self.pr.get("state") != "MERGED" or self.pr.get("merged") is not True:
            self.failures.append(f"PR #{self.pr_number} is not in merged state")
        pr_head = self.pr.get("headRefOid")
        if pr_head != self.expected_pr_head:
            self.failures.append(
                f"PR head moved: expected {self.expected_pr_head}, GitHub reports {pr_head or 'missing'}"
            )
        merge_commit = (self.pr.get("mergeCommit") or {}).get("oid")
        if not isinstance(merge_commit, str) or not FULL_SHA_RE.fullmatch(merge_commit):
            self.failures.append(f"PR #{self.pr_number} has no full merge commit SHA")

        body = self.pr.get("body") or ""
        marked = extract_marked_head_lists(body)
        proof = marked.get("proof_head", [])
        final = marked.get("final_pr_head", [])
        if len(proof) != 1 or not FULL_SHA_RE.fullmatch(proof[0] if proof else ""):
            self.failures.append("PR body must contain exactly one full `Proof head:` marker")
        else:
            self.proof_head = proof[0]
        if len(final) != 1 or not FULL_SHA_RE.fullmatch(final[0] if final else ""):
            self.failures.append("PR body must contain exactly one full `Final PR head:` marker")
        elif final[0] != self.expected_pr_head:
            self.failures.append(
                f"PR body final head {final[0]} does not equal expected PR head {self.expected_pr_head}"
            )
        refs = EVIDENCE_REF_RE.findall(body)
        if len(refs) != 1:
            self.failures.append("PR body must reference exactly one docs/evidence/<folder> path")
            return
        requested = self.evidence_folder_arg
        requested_path = requested if requested.is_absolute() else self.root / requested
        body_path = self.root / refs[0]
        try:
            evidence_root = (self.root / "docs" / "evidence").resolve(strict=True)
            selected = requested_path.resolve(strict=True)
            selected.relative_to(evidence_root)
        except (FileNotFoundError, ValueError, OSError):
            self.failures.append(f"Evidence folder is missing or outside docs/evidence: {requested}")
            return
        if selected.is_symlink() or not selected.is_dir():
            self.failures.append(f"Evidence folder must be a real directory: {requested}")
            return
        if selected != body_path.resolve(strict=False):
            self.failures.append("--evidence-folder does not match the unique PR-body evidence reference")
            return
        self.evidence_folder = selected

    def _fetch_remote_commits(self) -> None:
        default_ref = f"refs/remotes/origin/{self.default_branch}"
        commands = [
            [
                "fetch",
                "--no-tags",
                "origin",
                f"+refs/heads/{self.default_branch}:{default_ref}",
            ],
            [
                "fetch",
                "--no-tags",
                "origin",
                f"+refs/pull/{self.pr_number}/head:refs/statedd/post-merge/pr-{self.pr_number}",
            ],
        ]
        for args in commands:
            code, _, err = self._git_result(args)
            if code != 0:
                self.failures.append(f"Could not fetch post-merge Git truth: {err or 'git fetch failed'}")
                return
        fetched_main = self._git(["rev-parse", default_ref], "") or ""
        fetched_pr = self._git(["rev-parse", f"refs/statedd/post-merge/pr-{self.pr_number}"], "") or ""
        if fetched_main != self.default_branch_head:
            self.failures.append(
                f"Fetched origin/{self.default_branch} {fetched_main or 'missing'} does not match GitHub {self.default_branch_head}"
            )
        if fetched_pr != self.expected_pr_head:
            self.failures.append(
                f"Fetched PR ref {fetched_pr or 'missing'} does not match expected head {self.expected_pr_head}"
            )

    def _check_main_contains_merge(self) -> None:
        merge_commit = (self.pr.get("mergeCommit") or {}).get("oid") or ""
        if not FULL_SHA_RE.fullmatch(merge_commit):
            return
        code, _, _ = self._git_result(
            ["merge-base", "--is-ancestor", merge_commit, self.default_branch_head]
        )
        if code != 0:
            self.failures.append(
                f"Merge commit {merge_commit} is not contained by default HEAD {self.default_branch_head}"
            )

    def _check_content_identity(self) -> None:
        merge_commit = (self.pr.get("mergeCommit") or {}).get("oid") or ""
        if not FULL_SHA_RE.fullmatch(merge_commit):
            return
        self.pr_tree = self._git(["rev-parse", f"{self.expected_pr_head}^{{tree}}"], "") or ""
        self.merge_tree = self._git(["rev-parse", f"{merge_commit}^{{tree}}"], "") or ""
        if self.pr_tree and self.pr_tree == self.merge_tree:
            self.content_identity_method = "source_tree_equal"
            return

        parents_line = self._git(["rev-list", "--parents", "-n", "1", merge_commit], "") or ""
        parents = parents_line.split()[1:]
        if not parents:
            self.failures.append("Merge commit has no parent for patch-equivalence proof")
            return
        merge_parent = parents[0]
        pr_base = self._git(["merge-base", self.expected_pr_head, merge_parent], "") or ""
        if not FULL_SHA_RE.fullmatch(pr_base):
            self.failures.append("Could not determine PR base for squash patch-equivalence proof")
            return
        pr_patch, pr_error = self.patch_id_fn(self.root, pr_base, self.expected_pr_head)
        merged_patch, merge_error = self.patch_id_fn(self.root, merge_parent, merge_commit)
        if pr_patch and pr_patch == merged_patch:
            self.content_identity_method = "stable_patch_equal"
            return
        details = "; ".join(part for part in (pr_error, merge_error) if part)
        self.failures.append(
            "Squash result is neither source-tree-equal nor stable-patch-equivalent to the exact PR head"
            + (f": {details}" if details else "")
        )

    def _check_ci_on_default_head(self) -> None:
        if self.ci_state != "SUCCESS":
            self.failures.append(
                f"CI on exact default-branch HEAD is {self.ci_state or 'missing'}, expected SUCCESS"
            )
        if not self.ci_run_id:
            self.failures.append("No successful GitHub Actions run found on exact default-branch HEAD")

    def _require_tracked_at_pr_head(self, path: Path) -> None:
        try:
            relative = path.relative_to(self.root).as_posix()
        except ValueError:
            self.failures.append(f"Evidence path escapes repository: {path}")
            return
        code, _, _ = self._git_result(["cat-file", "-e", f"{self.expected_pr_head}:{relative}"])
        if code != 0:
            self.failures.append(f"Evidence path is not tracked at exact PR head: {relative}")

    def _check_tracked_evidence(self) -> None:
        if self.evidence_folder is None:
            return
        manifest_path = self.evidence_folder / "manifest.json"
        readme_path = self.evidence_folder / "README.md"
        for path in (manifest_path, readme_path):
            if path.is_symlink() or not path.is_file():
                self.failures.append(f"Selected evidence has no regular {path.name}")
                return
            self._require_tracked_at_pr_head(path)
        try:
            manifest = strict_json_object(manifest_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self.failures.append(f"Evidence manifest is invalid: {exc}")
            return
        future_keys = nested_keys(manifest) & FUTURE_IDENTITY_KEYS
        if future_keys:
            self.failures.append(
                "Tracked evidence contains post-merge identity field(s): " + ", ".join(sorted(future_keys))
            )
        if manifest.get("manifest_status") != "complete":
            self.failures.append("Evidence manifest_status must be complete")
        repo = manifest.get("repo") or {}
        manifest_proof = repo.get("head") if isinstance(repo, dict) else None
        if manifest_proof != self.proof_head:
            self.failures.append(
                f"Manifest proof head {manifest_proof!r} does not match PR body {self.proof_head!r}"
            )
            return
        if repo.get("branch") != self.pr.get("headRefName"):
            self.failures.append("Evidence branch does not match the PR head branch")
        code, _, _ = self._git_result(["cat-file", "-e", f"{self.proof_head}^{{commit}}"])
        if code != 0:
            self.failures.append(f"Evidence proof commit is not fetchable: {self.proof_head}")
            return
        code, _, _ = self._git_result(
            ["merge-base", "--is-ancestor", self.proof_head or "", self.expected_pr_head]
        )
        if code != 0:
            self.failures.append("Evidence proof head is not an ancestor of the exact PR head")
        self.proof_tree = self._git(["rev-parse", f"{self.proof_head}^{{tree}}"], "") or ""
        if not FULL_SHA_RE.fullmatch(self.proof_tree):
            self.failures.append("Could not derive the immutable proof tree from evidence repo.head")

        claims = manifest.get("claims")
        if not isinstance(claims, list) or not claims:
            self.failures.append("Evidence manifest must contain claims")
        else:
            for index, claim in enumerate(claims):
                if not isinstance(claim, dict) or claim.get("status") != "validated":
                    self.failures.append(f"Evidence claim {index} is not validated")
                if not isinstance(claim, dict) or not claim.get("evidence"):
                    self.failures.append(f"Evidence claim {index} has no test/source evidence references")

        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            self.failures.append("Evidence manifest must contain hashed artifacts")
        else:
            for index, artifact in enumerate(artifacts):
                if not isinstance(artifact, dict):
                    self.failures.append(f"Evidence artifact {index} is not an object")
                    continue
                raw = artifact.get("path")
                expected_hash = artifact.get("sha256")
                if not isinstance(raw, str) or not re.fullmatch(r"[A-Za-z0-9._/-]+", raw):
                    self.failures.append(f"Evidence artifact {index} has an unsafe path")
                    continue
                relative = Path(raw)
                if relative.is_absolute() or ".." in relative.parts:
                    self.failures.append(f"Evidence artifact path escapes its folder: {raw}")
                    continue
                artifact_path = (self.evidence_folder / relative).resolve(strict=False)
                try:
                    artifact_path.relative_to(self.evidence_folder)
                except ValueError:
                    self.failures.append(f"Evidence artifact path escapes its folder: {raw}")
                    continue
                if artifact_path.is_symlink() or not artifact_path.is_file():
                    self.failures.append(f"Evidence artifact is missing or unsafe: {raw}")
                    continue
                self._require_tracked_at_pr_head(artifact_path)
                if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                    self.failures.append(f"Evidence artifact has no full SHA-256: {raw}")
                    continue
                actual_hash = sha256_file(artifact_path)
                self.source_hashes[raw] = actual_hash
                if actual_hash != expected_hash:
                    self.failures.append(f"Evidence artifact hash mismatch: {raw}")

        readme_text = readme_path.read_text(encoding="utf-8")
        heads = extract_marked_head_lists(readme_text)
        readme_proof = heads.get("proof_head", [])
        if readme_proof != [self.proof_head]:
            self.failures.append("Tracked evidence README must bind exactly the manifest proof head")
        if heads.get("final_pr_head"):
            self.failures.append("Tracked evidence README must not embed the final PR head")
        if FUTURE_SHA_MARKER_RE.search(readme_text):
            self.failures.append("Tracked evidence README must not embed post-merge commit/main identities")
        closure = self.evidence_folder / "closure.json"
        if closure.exists():
            self._require_tracked_at_pr_head(closure)
            try:
                closure_data = strict_json_object(closure)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                self.failures.append(f"Tracked closure.json is invalid: {exc}")
            else:
                forbidden = nested_keys(closure_data) & FUTURE_IDENTITY_KEYS
                if forbidden:
                    self.failures.append(
                        "Tracked closure.json contains future post-merge identity field(s): "
                        + ", ".join(sorted(forbidden))
                    )

    def _handoff_payload(self) -> dict[str, Any]:
        return {
            "schema": "statedd.post_merge_handoff.v1",
            "status": "failed" if self.failures else "verified",
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "repository": {
                "path": str(self.root),
                "origin": self.remote_url,
                "local_head": self.local_head,
            },
            "pull_request": {
                "number": self.pr_number,
                "url": self.pr.get("url"),
                "proof_head": self.proof_head,
                "final_head": self.expected_pr_head,
                "merge_commit": (self.pr.get("mergeCommit") or {}).get("oid"),
            },
            "default_branch": {
                "name": self.default_branch,
                "head": self.default_branch_head,
                "ci_state": self.ci_state,
                "ci_run_id": self.ci_run_id,
                "ci_run_url": self.ci_run_url,
                "ci_workflow_path": self.ci_workflow_path,
            },
            "evidence": {
                "folder": str(self.evidence_folder) if self.evidence_folder else None,
                "proof_tree": self.proof_tree,
                "pr_tree": self.pr_tree,
                "merge_tree": self.merge_tree,
                "content_identity_method": self.content_identity_method,
                "artifact_sha256": dict(sorted(self.source_hashes.items())),
            },
            "failures": list(self.failures),
            "warnings": list(self.warnings),
        }

    def _write_external_handoff(self) -> None:
        if self.output is None:
            return
        output = self.output if self.output.is_absolute() else Path.cwd() / self.output
        try:
            resolved = output.resolve(strict=False)
            resolved.relative_to(self.root)
        except ValueError:
            pass
        else:
            self.failures.append("Post-merge handoff output must be external to the repository")
            return
        parent = resolved.parent
        if not parent.exists() or parent.is_symlink() or not parent.is_dir():
            self.failures.append(f"External handoff parent must be an existing real directory: {parent}")
            return
        payload = self._handoff_payload()
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=parent,
                prefix=f".{resolved.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                temp_path = Path(handle.name)
            os.replace(temp_path, resolved)
        except OSError as exc:
            self.failures.append(f"Could not write external post-merge handoff: {exc}")

    def _print_handoff(self) -> None:
        payload = self._handoff_payload()
        print("\nPost-Merge Verification Handoff")
        print(json.dumps(payload, indent=2, sort_keys=True))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prove merged-PR content, default-branch CI, and external post-merge truth"
    )
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect")
    parser.add_argument("--pr-number", type=int, required=True, help="Merged PR number")
    parser.add_argument(
        "--expected-pr-head",
        required=True,
        help="Exact 40-character PR head authorized before merge",
    )
    parser.add_argument(
        "--evidence-folder",
        type=Path,
        required=True,
        help="Tracked proof folder under docs/evidence; must match the PR body",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="External JSON handoff path (must be outside the repository)",
    )
    parser.add_argument("--github-token", default=None, help="GitHub token fallback")
    parser.add_argument("--verbose", "-v", action="store_true", help="Reserved for detailed output")
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    verifier = PostMergeVerifier(
        root=Path(args.root),
        pr_number=args.pr_number,
        expected_pr_head=args.expected_pr_head,
        evidence_folder_arg=args.evidence_folder,
        output=args.output,
        verbose=args.verbose,
        github_token=args.github_token,
    )
    return verifier.run()


if __name__ == "__main__":
    raise SystemExit(main())
