#!/usr/bin/env python3
"""Regression tests for the StateSpec Git safety preflight.

The filesystem permission fixtures operate only in disposable temporary
repositories and restore their original modes in ``finally`` blocks.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "statedd_git_safety_check.py"
SCHEMA = ROOT / "schemas" / "git_safety_report.schema.json"
VALIDATOR = ROOT / "scripts" / "statedd_validate_schema.py"


def run(
    args: list[str],
    *,
    cwd: Path,
    expect_code: int | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_code is not None and completed.returncode != expect_code:
        raise AssertionError(
            f"Expected exit {expect_code}, got {completed.returncode}: {args}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def git(repo: Path, *args: str, expect_code: int = 0, input_text: str | None = None) -> str:
    completed = run(["git", *args], cwd=repo, expect_code=expect_code, input_text=input_text)
    return completed.stdout.strip()


def init_remote_clone(root: Path, name: str = "repo") -> tuple[Path, Path]:
    bare = root / f"{name}.git"
    seed = root / f"{name}-seed"
    clone = root / f"{name}-clone"
    git(root, "init", "--bare", str(bare))
    git(root, "init", "-b", "main", str(seed))
    git(seed, "config", "user.email", "tests@example.com")
    git(seed, "config", "user.name", "StateSpec Tests")
    (seed / "PROJECT_STATE.yaml").write_text("state: baseline\n", encoding="utf-8")
    (seed / "README.md").write_text("# Disposable safety test\n", encoding="utf-8")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "initial")
    git(seed, "remote", "add", "origin", str(bare))
    git(seed, "push", "-u", "origin", "main")
    git(bare, "symbolic-ref", "HEAD", "refs/heads/main")
    git(root, "clone", "--no-local", str(bare), str(clone))
    git(clone, "config", "user.email", "tests@example.com")
    git(clone, "config", "user.name", "StateSpec Tests")
    git(clone, "switch", "-c", "feature/safety-test")
    return clone, bare


def run_check(
    repo: Path,
    mode: str,
    *,
    latch_root: Path,
    extra: list[str] | None = None,
    expect_code: int,
) -> tuple[subprocess.CompletedProcess[str], dict]:
    command = [
        sys.executable,
        str(SCRIPT),
        "--repo",
        str(repo),
        "--mode",
        mode,
        "--format",
        "json",
        "--latch-root",
        str(latch_root),
    ]
    if extra:
        command.extend(extra)
    completed = run(command, cwd=repo, expect_code=expect_code)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Preflight did not emit JSON: {completed.stdout}\n{completed.stderr}") from exc
    return completed, payload


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("statedd_git_safety_check", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def content_snapshot(root: Path) -> dict[str, tuple[str, int]]:
    snapshot: dict[str, tuple[str, int]] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[rel] = (f"symlink:{os.readlink(path)}", stat.S_IMODE(path.lstat().st_mode))
        elif path.is_file():
            snapshot[rel] = (hashlib.sha256(path.read_bytes()).hexdigest(), stat.S_IMODE(path.stat().st_mode))
        elif path.is_dir():
            snapshot[rel] = ("directory", stat.S_IMODE(path.stat().st_mode))
    return snapshot


def test_normal_same_user_clone_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo, _ = init_remote_clone(root)
        _, report = run_check(repo, "normal_branch", latch_root=root / "latches", expect_code=0)
        assert report["decision"]["permitted"] is True
        assert report["decision"]["mutation_permitted"] is True
        assert report["decision"]["effective_mode"] == "normal_branch"
        assert report["synchronization"]["result"] == "pass"


def test_same_user_linked_worktree_requires_explicit_opt_in() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo, _ = init_remote_clone(root)
        linked = root / "linked"
        git(repo, "worktree", "add", "-b", "feature/linked-test", str(linked), "HEAD")
        _, blocked = run_check(linked, "worktree", latch_root=root / "blocked-latches", expect_code=1)
        assert blocked["decision"]["effective_mode"] == "read_only"
        assert any("opt-in" in item.lower() for item in blocked["decision"]["blockers"])
        _, allowed = run_check(
            linked,
            "worktree",
            latch_root=root / "allowed-latches",
            extra=["--worktree-opt-in", "--trusted-local-machine"],
            expect_code=0,
        )
        assert allowed["decision"]["mutation_permitted"] is True


def test_unwritable_objects_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo, _ = init_remote_clone(root)
        objects = Path(git(repo, "rev-parse", "--git-path", "objects"))
        if not objects.is_absolute():
            objects = repo / objects
        original = stat.S_IMODE(objects.stat().st_mode)
        try:
            objects.chmod(0o555)
            _, report = run_check(repo, "normal_branch", latch_root=root / "latches", expect_code=1)
            assert report["decision"]["effective_mode"] == "read_only"
            assert report["metadata"]["unwritable"] or report["write_probe"]["result"] == "fail"
        finally:
            objects.chmod(original)


def test_root_owned_nested_object_prefix_fails_policy() -> None:
    module = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "objects"
        nested = tree / "ab"
        nested.mkdir(parents=True)
        real_lstat = os.lstat
        euid = os.geteuid()
        foreign_uid = 0 if euid != 0 else 1

        def synthetic_lstat(path: os.PathLike[str] | str):
            result = real_lstat(path)
            if Path(path) == nested:
                return SimpleNamespace(
                    st_mode=result.st_mode,
                    st_uid=foreign_uid,
                    st_gid=result.st_gid,
                    st_nlink=result.st_nlink,
                    st_size=result.st_size,
                )
            return result

        report = module.scan_metadata_tree(
            tree,
            label="objects",
            effective_uid=euid,
            effective_gid=os.getegid(),
            stat_fn=synthetic_lstat,
        )
        assert report["scan_complete"] is True
        assert any(item["path"] == str(nested) for item in report["mismatches"])
        policy_report = safe_policy_report()
        policy_report["repository"].update(
            {"git_dir_equals_common_dir": True, "common_dir_inside_repo": True}
        )
        policy_report["worktrees"]["total_count"] = 1
        policy_report["metadata"]["mismatches"] = report["mismatches"]
        blockers, _ = module.mode_policy(
            "normal_branch",
            policy_report,
            worktree_opt_in=False,
            trusted_local_machine=False,
        )
        assert any("owner/group" in item for item in blockers)


def test_unwritable_refs_logs_and_worktrees_fail() -> None:
    for target_name in ("refs", "logs", "worktrees"):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, _ = init_remote_clone(root, name=target_name)
            common = Path(git(repo, "rev-parse", "--git-common-dir"))
            if not common.is_absolute():
                common = (repo / common).resolve()
            target = common / target_name
            target.mkdir(parents=True, exist_ok=True)
            original = stat.S_IMODE(target.stat().st_mode)
            try:
                target.chmod(0o555)
                _, report = run_check(repo, "normal_branch", latch_root=root / "latches", expect_code=1)
                assert report["decision"]["effective_mode"] == "read_only"
                assert any(str(target) in item.get("path", "") for item in report["metadata"]["unwritable"])
            finally:
                target.chmod(original)


def test_fetch_failure_latches_read_only_before_state_writes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo, bare = init_remote_clone(root)
        latch_root = root / "latches"
        state_before = (repo / "PROJECT_STATE.yaml").read_bytes()
        git(repo, "remote", "set-url", "origin", str(root / "missing-origin.git"))
        _, failed = run_check(repo, "normal_branch", latch_root=latch_root, expect_code=1)
        assert failed["synchronization"]["result"] == "fail"
        assert failed["decision"]["restart_required"] is True
        assert (repo / "PROJECT_STATE.yaml").read_bytes() == state_before

        git(repo, "remote", "set-url", "origin", str(bare))
        _, latched = run_check(repo, "normal_branch", latch_root=latch_root, expect_code=1)
        assert latched["decision"]["restart_required"] is True
        assert latched["synchronization"]["attempted"] is False

        _, restarted = run_check(
            repo,
            "normal_branch",
            latch_root=latch_root,
            extra=["--restart-session"],
            expect_code=0,
        )
        assert restarted["decision"]["restart_required"] is False
        assert restarted["decision"]["mutation_permitted"] is True


def safe_policy_report() -> dict:
    return {
        "repository": {
            "git_dir_equals_common_dir": False,
            "common_dir_inside_repo": False,
            "branch": "feature/policy",
            "default_branch": "main",
        },
        "identity": {
            "effective_uid": 1000,
            "effective_gid": 1000,
            "known": True,
            "is_root": False,
        },
        "runtime": {
            "classification": "host",
            "privilege": "unprivileged",
            "risky_capabilities": [],
        },
        "metadata": {
            "scan_complete": True,
            "mismatches": [],
            "unreadable": [],
            "unwritable": [],
            "symlinks": [],
        },
        "worktrees": {"total_count": 2, "unknown_identity_count": 0, "mismatched_identity_count": 0},
        "write_probe": {"result": "pass"},
        "fsck": {"result": "pass"},
        "synchronization": {"result": "pass"},
        "isolation": {"independent_common_dir": False, "alternates_present": False, "hardlinked_object_files": 0},
    }


def test_unknown_or_mismatched_uid_blocks_worktree_mode() -> None:
    module = load_module()
    for field in ("unknown_identity_count", "mismatched_identity_count"):
        report = safe_policy_report()
        report["worktrees"][field] = 1
        blockers, _ = module.mode_policy(
            "worktree", report, worktree_opt_in=True, trusted_local_machine=True
        )
        assert any("identity" in item.lower() for item in blockers)


def test_root_container_blocks_worktree_mode() -> None:
    module = load_module()
    report = safe_policy_report()
    report["identity"]["effective_uid"] = 0
    report["identity"]["is_root"] = True
    report["runtime"]["classification"] = "container"
    report["runtime"]["privilege"] = "privileged"
    blockers, _ = module.mode_policy(
        "worktree", report, worktree_opt_in=True, trusted_local_machine=True
    )
    assert any("container" in item.lower() or "privilege" in item.lower() for item in blockers)


def test_clone_mode_has_independent_common_directory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source, bare = init_remote_clone(root, name="source")
        clone = root / "independent"
        git(root, "clone", "--no-local", "--no-hardlinks", str(bare), str(clone))
        git(clone, "switch", "-c", "feature/independent")
        _, report = run_check(
            clone,
            "clone",
            latch_root=root / "latches",
            extra=["--source-repo", str(source)],
            expect_code=0,
        )
        assert report["isolation"]["independent_common_dir"] is True
        assert report["isolation"]["alternates_present"] is False
        assert report["isolation"]["hardlinked_object_files"] == 0


def test_read_only_mode_does_not_mutate_repository() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo, _ = init_remote_clone(root)
        before = content_snapshot(repo)
        _, report = run_check(repo, "read_only", latch_root=root / "latches", expect_code=0)
        after = content_snapshot(repo)
        assert after == before
        assert report["decision"]["permitted"] is True
        assert report["decision"]["mutation_permitted"] is False
        assert report["write_probe"]["result"] == "not_run_read_only"
        assert report["synchronization"]["result"] == "not_run_read_only"
        assert report["decision"]["enforcement_scope"] == "statedd_managed_session_permit"


def test_dirty_and_stale_worktrees_are_reported_without_cleanup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo, _ = init_remote_clone(root)
        dirty = root / "dirty-worktree"
        stale = root / "stale-worktree"
        git(repo, "worktree", "add", "-b", "feature/dirty", str(dirty), "HEAD")
        git(repo, "worktree", "add", "-b", "feature/stale", str(stale), "HEAD")
        (dirty / "README.md").write_text("dirty\n", encoding="utf-8")
        shutil.rmtree(stale)
        topology_before = git(repo, "worktree", "list", "--porcelain")
        _, report = run_check(repo, "read_only", latch_root=root / "latches", expect_code=0)
        topology_after = git(repo, "worktree", "list", "--porcelain")
        assert topology_after == topology_before
        entries = report["worktrees"]["entries"]
        assert any(item["path"] == str(dirty) and item["dirty"] is True for item in entries)
        assert any(item["path"] == str(stale) and item["missing"] is True for item in entries)


def test_no_automatic_dangerous_git_or_permission_repair_path() -> None:
    forbidden_sequences = {
        ("git", "reset", "--hard"),
        ("git", "clean"),
        ("git", "gc"),
        ("git", "worktree", "prune"),
        ("git", "worktree", "remove", "--force"),
        ("git", "branch", "-D"),
    }
    violations: list[str] = []
    for path in sorted((ROOT / "scripts").glob("*.py")):
        if path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"chmod", "chown", "lchmod", "lchown"}:
                    violations.append(f"{path.name}:{node.lineno} os/path {node.func.attr}")
            if not isinstance(node, (ast.List, ast.Tuple)):
                continue
            values = [item.value for item in node.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)]
            joined = tuple(values)
            for forbidden in forbidden_sequences:
                if len(joined) >= len(forbidden) and joined[: len(forbidden)] == forbidden:
                    violations.append(f"{path.name}:{node.lineno} {' '.join(forbidden)}")
    assert not violations, "Forbidden automatic production paths:\n" + "\n".join(violations)


def test_json_output_validates_against_schema() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo, _ = init_remote_clone(root)
        completed, _ = run_check(repo, "normal_branch", latch_root=root / "latches", expect_code=0)
        report_path = root / "git_safety_report.json"
        report_path.write_text(completed.stdout, encoding="utf-8")
        run(
            [sys.executable, str(VALIDATOR), "--file", str(report_path), "--schema", str(SCHEMA)],
            cwd=ROOT,
            expect_code=0,
        )


def test_exact_git_object_permission_error_is_reproduced_safely() -> None:
    if os.geteuid() == 0:
        # Root bypasses ordinary mode-bit denial; policy coverage for privileged
        # identity is exercised separately without weakening the production check.
        return
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        git(Path(tmp), "init", str(repo))
        objects = repo / ".git" / "objects"
        content = b"statedd original object permission regression\n"
        while True:
            object_id = git(repo, "hash-object", "--stdin", input_text=content.decode("utf-8"))
            prefix = objects / object_id[:2]
            if not prefix.exists():
                break
            content += b"x"
        prefix.mkdir()
        original = stat.S_IMODE(prefix.stat().st_mode)
        try:
            prefix.chmod(0o555)
            failed = run(
                ["git", "hash-object", "-w", "--stdin"],
                cwd=repo,
                input_text=content.decode("utf-8"),
            )
            assert failed.returncode != 0
            error = (failed.stdout + failed.stderr).lower()
            assert "object" in error
            assert "permission" in error or "insufficient" in error
        finally:
            prefix.chmod(original)


def test_failed_critical_git_reads_cannot_become_clean_results() -> None:
    module = load_module()

    def failing_runner(args: list[str], cwd: Path, timeout: float = 30.0):
        if args[:4] == ["git", "--no-optional-locks", "status", "--porcelain=v1"]:
            return 128, "", "simulated status failure"
        if args[:4] == ["git", "worktree", "list", "--porcelain"]:
            return 128, "", "simulated worktree-list failure"
        return 0, "", ""

    try:
        module.collect_worktrees(Path.cwd(), runner=failing_runner)
    except module.InspectionError as exc:
        assert "worktree" in str(exc).lower()
    else:
        raise AssertionError("failed worktree read was treated as empty topology")


def test_git_lock_blocks_central_preflight() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo, _ = init_remote_clone(root)
        common_raw = Path(git(repo, "rev-parse", "--git-common-dir"))
        common = common_raw if common_raw.is_absolute() else (repo / common_raw).resolve()
        lock = common / "index.lock"
        lock.write_text("preserve for diagnosis\n", encoding="utf-8")
        try:
            _, report = run_check(repo, "normal_branch", latch_root=root / "latches", expect_code=1)
            assert report["metadata"]["locks"]
            assert any("lock" in item.lower() for item in report["decision"]["blockers"])
            assert lock.exists()
        finally:
            lock.unlink()


def test_fsck_failure_blocks_writable_mode() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo, _ = init_remote_clone(root)
        common_raw = Path(git(repo, "rev-parse", "--git-common-dir"))
        common = common_raw if common_raw.is_absolute() else (repo / common_raw).resolve()
        loose = common / "objects" / "aa" / ("b" * 38)
        loose.parent.mkdir(exist_ok=True)
        loose.write_bytes(b"corrupt disposable object\n")
        _, report = run_check(repo, "normal_branch", latch_root=root / "latches", expect_code=1)
        assert report["fsck"]["result"] == "fail"
        assert any("fsck" in item.lower() for item in report["decision"]["blockers"])


def main() -> int:
    tests = [
        test_normal_same_user_clone_passes,
        test_same_user_linked_worktree_requires_explicit_opt_in,
        test_unwritable_objects_fails,
        test_root_owned_nested_object_prefix_fails_policy,
        test_unwritable_refs_logs_and_worktrees_fail,
        test_fetch_failure_latches_read_only_before_state_writes,
        test_unknown_or_mismatched_uid_blocks_worktree_mode,
        test_root_container_blocks_worktree_mode,
        test_clone_mode_has_independent_common_directory,
        test_read_only_mode_does_not_mutate_repository,
        test_dirty_and_stale_worktrees_are_reported_without_cleanup,
        test_no_automatic_dangerous_git_or_permission_repair_path,
        test_json_output_validates_against_schema,
        test_exact_git_object_permission_error_is_reproduced_safely,
        test_failed_critical_git_reads_cannot_become_clean_results,
        test_git_lock_blocks_central_preflight,
        test_fsck_failure_blocks_writable_mode,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
