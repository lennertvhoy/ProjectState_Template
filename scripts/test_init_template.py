#!/usr/bin/env python3
"""Regression tests for the StateDD initializer.

These tests intentionally stay stdlib-only so template maintainers and
downstream repos can run them without installing a test framework.
"""

from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import init_template as init_module


ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = ROOT / "scripts" / "init_template.py"


def run_init(args: list[str], *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(INIT_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(
            f"Expected success for {args}, got {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not expect_success and completed.returncode == 0:
        raise AssertionError(f"Expected failure for {args}, got success\nstdout:\n{completed.stdout}")
    return completed


def assert_no_external_files(path: Path) -> None:
    leaked = sorted(item.relative_to(path) for item in path.rglob("*") if item.is_file())
    if leaked:
        raise AssertionError(f"Initializer wrote outside the target repo: {leaked}")


def assert_mentions_symlink(completed: subprocess.CompletedProcess[str]) -> None:
    output = f"{completed.stdout}\n{completed.stderr}".lower()
    if "symlink" not in output:
        raise AssertionError(f"Expected symlink refusal message, got:\n{output}")


def test_adopt_rejects_symlinked_managed_directory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        outside = root / "outside"
        repo.mkdir()
        outside.mkdir()
        os.symlink(outside, repo / "docs")

        completed = run_init(["adopt", "--name", "Audit Demo", "--target", str(repo)], expect_success=False)

        assert_mentions_symlink(completed)
        assert_no_external_files(outside)
        if [entry.name for entry in repo.iterdir() if entry.name != "docs"]:
            raise AssertionError("Adoption wrote partial files before nested-symlink refusal")


def test_new_rejects_symlinked_existing_directory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        outside = root / "outside"
        repo.mkdir()
        outside.mkdir()
        os.symlink(outside, repo / "docs")

        completed = run_init(
            [
                "new",
                "--name",
                "Audit Demo",
                "--target",
                str(repo),
                "--overwrite",
                "--force-overwrite",
            ],
            expect_success=False,
        )

        assert_mentions_symlink(completed)
        assert_no_external_files(outside)
        if [entry.name for entry in repo.iterdir() if entry.name != "docs"]:
            raise AssertionError("Initializer wrote partial files before nested-symlink refusal")


def test_new_rejects_symlinked_target_root() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        actual = root / "actual"
        actual.mkdir()
        linked = root / "linked"
        os.symlink(actual, linked)

        completed = run_init(
            ["new", "--name", "Root Symlink", "--target", str(linked)],
            expect_success=False,
        )
        assert_mentions_symlink(completed)
        assert_no_external_files(actual)


def test_new_rejects_directory_destination_before_any_write() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "AGENTS.md").mkdir()

        completed = run_init(
            [
                "new",
                "--name",
                "Directory Collision",
                "--target",
                str(repo),
                "--overwrite",
                "--force-overwrite",
            ],
            expect_success=False,
        )
        if "non-file destination" not in (completed.stdout + completed.stderr):
            raise AssertionError(f"Expected directory-destination refusal:\n{completed.stdout}{completed.stderr}")
        if [entry.name for entry in repo.iterdir() if entry.name != "AGENTS.md"]:
            raise AssertionError("Initializer wrote partial files before directory-destination refusal")


def test_new_rejects_file_parent_before_any_write() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "scripts").write_text("parent collision\n", encoding="utf-8")

        completed = run_init(
            [
                "new",
                "--name",
                "Parent Collision",
                "--target",
                str(repo),
                "--overwrite",
                "--force-overwrite",
            ],
            expect_success=False,
        )
        if "non-directory destination parent" not in (completed.stdout + completed.stderr):
            raise AssertionError(f"Expected parent-file refusal:\n{completed.stdout}{completed.stderr}")
        if sorted(path.name for path in repo.iterdir()) != ["scripts"]:
            raise AssertionError("Initializer wrote partial files before parent-file refusal")


def test_new_replaces_hardlinked_managed_file_without_mutating_external_inode() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        external = root / "external-managed.txt"
        external.write_text("external sentinel\n", encoding="utf-8")
        os.link(external, repo / "AGENTS.md")
        external_inode = external.stat().st_ino

        run_init(
            [
                "new", "--name", "Hardlink Managed", "--profile", "minimal",
                "--target", str(repo), "--overwrite", "--force-overwrite",
            ],
            expect_success=True,
        )

        assert external.read_text(encoding="utf-8") == "external sentinel\n"
        assert external.stat().st_ino == external_inode
        assert (repo / "AGENTS.md").stat().st_ino != external_inode


def test_new_replaces_hardlinked_copied_asset_without_mutating_external_inode() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        managed = set(
            init_module.build_managed_files_for_new(
                "Hardlink Asset",
                repo,
                "2026-07-11",
                "20260711",
                "2026-07-11T00:00:00+00:00",
                "minimal",
            )
        )
        copied = next(
            path
            for path in init_module.assets_for_profile("minimal")
            if path.as_posix() not in managed
        )
        destination = repo / copied
        destination.parent.mkdir(parents=True, exist_ok=True)
        external = root / "external-asset.txt"
        external.write_text("external asset sentinel\n", encoding="utf-8")
        os.link(external, destination)
        external_inode = external.stat().st_ino

        run_init(
            [
                "new", "--name", "Hardlink Asset", "--profile", "minimal",
                "--target", str(repo), "--overwrite", "--force-overwrite",
            ],
            expect_success=True,
        )

        assert external.read_text(encoding="utf-8") == "external asset sentinel\n"
        assert external.stat().st_ino == external_inode
        assert destination.stat().st_ino != external_inode
        assert destination.read_bytes() == (ROOT / copied).read_bytes()


def test_new_materialization_failure_rolls_back_every_write() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "rollback"
        original = init_module.copy_file
        calls = 0

        def fail_second_copy(source: Path, destination: Path, relpath: Path) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected copy failure")
            original(source, destination, relpath)

        with mock.patch.object(init_module, "copy_file", side_effect=fail_second_copy):
            try:
                init_module.main(
                    [
                        "init_template.py",
                        "new",
                        "--name",
                        "Rollback",
                        "--profile",
                        "minimal",
                        "--target",
                        str(target),
                    ]
                )
            except OSError as exc:
                if "injected copy failure" not in str(exc):
                    raise
            else:
                raise AssertionError("Injected materialization failure did not propagate")
        if target.exists():
            leaked = sorted(path.relative_to(target) for path in target.rglob("*"))
            raise AssertionError(f"Failed initializer left partial target state: {leaked}")


def test_template_commit_provenance_is_null_when_source_tree_is_dirty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
        (repo / "source.txt").write_text("clean\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "source.txt"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "source"], check=True)
        proven = init_module.clean_git_head(repo)
        if not isinstance(proven, str) or len(proven) != 40:
            raise AssertionError("Clean source tree did not produce commit provenance")
        (repo / "source.txt").write_text("dirty\n", encoding="utf-8")
        if init_module.clean_git_head(repo) is not None:
            raise AssertionError("Dirty source bytes were falsely attributed to HEAD")


def test_new_rejects_template_root() -> None:
    completed = run_init(
        ["new", "--name", "Template Root", "--target", str(ROOT)],
        expect_success=False,
    )
    output = f"{completed.stdout}\n{completed.stderr}".lower()
    if "template root" not in output:
        raise AssertionError(f"Expected template-root refusal, got:\n{output}")


def test_readme_link_rejects_symlinked_readme_before_writes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        outside = root / "outside"
        repo.mkdir()
        outside.mkdir()
        (outside / "README.md").write_text("# External\n", encoding="utf-8")
        os.symlink(outside / "README.md", repo / "README.md")

        completed = run_init(
            ["adopt", "--name", "Audit Demo", "--target", str(repo), "--readme-link"],
            expect_success=False,
        )

        assert_mentions_symlink(completed)
        if any(item.name in {"AGENTS.md", "PROJECT_STATE.yaml", "prompts"} for item in repo.iterdir()):
            raise AssertionError("README symlink preflight failed after writing workflow files")
        if (outside / "README.md").read_text(encoding="utf-8") != "# External\n":
            raise AssertionError("Initializer modified the external README target")


def test_top_level_help_shows_subcommands() -> None:
    completed = run_init(["--help"], expect_success=True)
    help_text = completed.stdout
    if "new" not in help_text or "adopt" not in help_text:
        raise AssertionError(f"Top-level help does not advertise both subcommands:\n{help_text}")


def test_legacy_new_invocation_still_works() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "legacy"
        run_init(["--name", "Legacy Demo", "--target", str(target)], expect_success=True)
        if not (target / "AGENTS.md").exists():
            raise AssertionError("Legacy initializer invocation did not create AGENTS.md")


def test_new_copies_curated_template_surface_only() -> None:
    sentinel = ROOT / "LOCAL_UNTRACKED_SENTINEL_FOR_TEST.md"
    if sentinel.exists():
        raise AssertionError(f"Unexpected pre-existing test sentinel: {sentinel}")

    try:
        sentinel.write_text("local maintenance artifact\n", encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "demo"
            run_init(["new", "--name", "Audit Demo", "--target", str(target)], expect_success=True)
            if (target / sentinel.name).exists():
                raise AssertionError("Initializer copied an untracked root-level maintenance artifact")
    finally:
        sentinel.unlink(missing_ok=True)


def test_new_includes_tool_model_routing_guide() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(
            ["new", "--name", "Routing Demo", "--target", str(target), "--profile", "team"],
            expect_success=True,
        )

        guide = target / "prompts" / "TOOL_MODEL_ROUTING_GUIDE.md"
        if not guide.exists():
            raise AssertionError("New repo did not include prompts/TOOL_MODEL_ROUTING_GUIDE.md")

def assert_usability_assets_exist(root: Path) -> None:
    required = [
        root / "README.md",
        root / "prompts" / "CODING_AGENT_STARTUP_PROMPT.md",
        root / "scripts" / "statedd_handoff.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing usability assets: {missing}")


def assert_version_assets_exist(root: Path) -> None:
    required = [
        root / "VERSION",
        root / "scripts" / "statedd_version_check.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing version assets: {missing}")


def assert_runtime_proof_assets_exist(root: Path) -> None:
    required = [
        root / "scripts" / "statedd_runtime_proof.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing runtime proof assets: {missing}")


def assert_worktree_and_brittleness_assets_exist(root: Path) -> None:
    required = [
        root / "ANTI_BRITTLENESS_GUARD.md",
        root / "docs" / "quality_gates" / "ANTI_BRITTLENESS_GATE.md",
        root / "scripts" / "statedd_worktree_guard.py",
        root / "scripts" / "statedd_brittleness_check.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing worktree/anti-brittleness assets: {missing}")


def assert_evidence_pack_assets_exist(root: Path) -> None:
    required = [
        root / "schemas" / "evidence_manifest.schema.json",
        root / "scripts" / "statedd_evidence_pack.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing evidence pack assets: {missing}")


def assert_upgrade_assets_exist(root: Path) -> None:
    required = [
        root / "scripts" / "statedd_upgrade.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing upgrade assets: {missing}")


def assert_quality_firewall_assets_exist(root: Path) -> None:
    required = [
        root / "QUALITY_FIREWALL.md",
        root / "FAILURE_TAXONOMY.md",
        root / "INCIDENT_RESPONSE.md",
        root / "docs" / "failure_scans" / "TEMPLATE.md",
        root / "docs" / "incidents" / "README.md",
        root / "docs" / "quality_gates" / "README.md",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing quality firewall assets: {missing}")

    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    state = (root / "PROJECT_STATE.yaml").read_text(encoding="utf-8")
    evidence = (root / "docs" / "EVIDENCE_LOG.md").read_text(encoding="utf-8")
    if "P0 product failure enters `quality_freeze`" not in agents:
        raise AssertionError("Generated AGENTS.md does not include the compact quality firewall rule")
    if "quality_gates:" not in state or "runtime_truth:" not in state:
        raise AssertionError("Generated PROJECT_STATE.yaml lacks quality gate/runtime truth fields")
    if "known_bad_event" not in evidence or "runtime_truth" not in evidence:
        raise AssertionError("Generated EVIDENCE_LOG.md lacks the expanded evidence taxonomy")


def assert_schema_validation_assets_exist(root: Path) -> None:
    required = [
        root / "schemas" / "project_state.schema.json",
        root / "schemas" / "project_dna.schema.json",
        root / "schemas" / "project_adapter.schema.json",
        root / "schemas" / "statedd_assets.schema.json",
        root / "schemas" / "runtime_identity.schema.json",
        root / "schemas" / "evidence_readme_contract.json",
        root / "schemas" / "evidence_manifest.schema.json",
        root / "schemas" / "final_handoff_contract.json",
        root / "scripts" / "statedd_validate_schema.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing schema validation assets: {missing}")


def assert_downstream_bootstrap_context(root: Path) -> None:
    project_state = (root / "PROJECT_STATE.yaml").read_text(encoding="utf-8")
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    for text, label in ((project_state, "PROJECT_STATE.yaml"), (agents, "AGENTS.md")):
        if "repo_role: downstream_project" not in text:
            raise AssertionError(f"{label} does not declare repo_role: downstream_project")
        if "statedd_mode: bootstrap" not in text:
            raise AssertionError(f"{label} does not declare statedd_mode: bootstrap")


def assert_runtime_manifest_matches_files(root: Path) -> None:
    manifest_path = root / "STATEDD_ASSETS.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "statedd.runtime_assets.v2":
        raise AssertionError("Generated runtime asset manifest has the wrong schema")
    records = payload.get("managed_assets", [])
    if not isinstance(records, list):
        raise AssertionError("Generated runtime asset manifest has no managed_assets list")
    declared = {record.get("path") for record in records if isinstance(record, dict)}
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    if declared != actual:
        raise AssertionError(
            f"Runtime asset manifest drift: missing={sorted(actual - declared)}, extra={sorted(declared - actual)}"
        )
    template_records = [record for record in records if record.get("owner") == "template"]
    if not template_records or any("merge_strategy" not in record for record in template_records):
        raise AssertionError("Generated lock lacks per-asset lifecycle semantics")


def assert_template_only_payload_absent(root: Path) -> None:
    forbidden = [
        root / "CHANGELOG.md",
        root / "fixtures",
        root / "scripts" / "init_template.py",
        root / "docs" / "incidents" / "INCIDENT-2026-06-28-false-closure.md",
        root / ".github" / "workflows" / "validate.yml",
    ]
    present = [path.relative_to(root).as_posix() for path in forbidden if path.exists()]
    copied_tests = sorted(path.relative_to(root).as_posix() for path in (root / "scripts").glob("test_*.py"))
    historical_evidence = sorted(
        path.relative_to(root).as_posix()
        for path in (root / "docs" / "evidence").rglob("*")
        if path.is_file() and path.name != ".gitkeep"
    )
    if present or copied_tests or historical_evidence:
        raise AssertionError(
            f"Template-only payload leaked: paths={present}, tests={copied_tests}, evidence={historical_evidence}"
        )


def assert_v2_assets_exist(root: Path) -> None:
    required = [
        root / "scripts" / "statedd_audit.py",
        root / "scripts" / "statedd_doctor.py",
        root / "prompts" / "SLICE_CONTRACT_TEMPLATE.md",
        root / "prompts" / "EVIDENCE_README_TEMPLATE.md",
        root / "prompts" / "SCHEMA_OWNERSHIP_TEMPLATE.md",
        root / "prompts" / "SUBAGENT_REVIEW_TEMPLATE.md",
        root / "prompts" / "CTO_REVIEW_CHECKLIST.md",
        root / "docs" / "adr" / "README.md",
        root / "docs" / "adr" / "0000-adr-template.md",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing v2 executable workflow assets: {missing}")


def test_new_includes_usability_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(["new", "--name", "Usability Demo", "--target", str(target)], expect_success=True)
        assert_usability_assets_exist(target)


def test_new_includes_version_assets_and_passes_version_check() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(["new", "--name", "Version Demo", "--target", str(target)], expect_success=True)
        assert_version_assets_exist(target)
        completed = subprocess.run(
            [sys.executable, str(target / "scripts" / "statedd_version_check.py"), str(target)],
            cwd=target,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"Generated repo version check failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        assert_downstream_bootstrap_context(target)


def test_new_includes_runtime_proof_asset() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(["new", "--name", "Runtime Demo", "--target", str(target)], expect_success=True)
        assert_runtime_proof_assets_exist(target)


def test_new_includes_quality_firewall_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(["new", "--name", "Quality Demo", "--target", str(target)], expect_success=True)
        assert_quality_firewall_assets_exist(target)
        assert_worktree_and_brittleness_assets_exist(target)


def test_new_includes_schema_validation_assets_and_passes_schema_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(["new", "--name", "Schema Demo", "--target", str(target)], expect_success=True)
        assert_schema_validation_assets_exist(target)
        assert_evidence_pack_assets_exist(target)
        assert_upgrade_assets_exist(target)
        dna_text = (target / "PROJECT_DNA.yaml").read_text(encoding="utf-8")
        if dna_text.count("\ninvariants:\n") != 1:
            raise AssertionError("Generated PROJECT_DNA.yaml must contain exactly one invariants mapping key")
        completed = subprocess.run(
            [sys.executable, str(target / "scripts" / "statedd_validate_schema.py"), str(target)],
            cwd=target,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"Generated repo schema validation failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )


def test_new_repo_still_fails_bootstrap_gate_until_investigated() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(["new", "--name", "Bootstrap Demo", "--target", str(target)], expect_success=True)
        completed = subprocess.run(
            [sys.executable, str(target / "scripts" / "check_state_docs.py"), "--bootstrap-gate", str(target)],
            cwd=target,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            raise AssertionError("Generated downstream bootstrap repo unexpectedly passed bootstrap gate")
        if "system investigation is still false" not in completed.stdout:
            raise AssertionError(f"Bootstrap gate did not preserve downstream investigation failure:\n{completed.stdout}")


def test_new_includes_v2_executable_workflow_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(
            ["new", "--name", "v2 Demo", "--target", str(target), "--profile", "team"],
            expect_success=True,
        )
        assert_v2_assets_exist(target)


def test_new_excludes_template_only_payload_and_manifest_is_exact() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(["new", "--name", "Boundary Demo", "--target", str(target)], expect_success=True)
        assert_template_only_payload_absent(target)
        assert_runtime_manifest_matches_files(target)


def test_adopt_installs_tool_model_routing_guide() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Existing Project\n", encoding="utf-8")

        run_init(
            ["adopt", "--name", "Routing Demo", "--target", str(repo), "--profile", "team"],
            expect_success=True,
        )

        guide = repo / "prompts" / "TOOL_MODEL_ROUTING_GUIDE.md"
        if not guide.exists():
            raise AssertionError("Adopted repo did not install prompts/TOOL_MODEL_ROUTING_GUIDE.md")

        readme = (repo / "README.md").read_text(encoding="utf-8")
        if readme != "# Existing Project\n":
            raise AssertionError("Adoption unexpectedly modified README.md without --readme-link")


def test_adopt_installs_usability_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        run_init(["adopt", "--name", "Usability Demo", "--target", str(repo)], expect_success=True)
        assert_usability_assets_exist(repo)


def test_adopt_installs_version_assets_and_passes_version_check() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        run_init(["adopt", "--name", "Version Demo", "--target", str(repo)], expect_success=True)
        assert_version_assets_exist(repo)
        completed = subprocess.run(
            [sys.executable, str(repo / "scripts" / "statedd_version_check.py"), str(repo)],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"Adopted repo version check failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        assert_downstream_bootstrap_context(repo)


def test_adopt_installs_runtime_proof_asset() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        run_init(["adopt", "--name", "Runtime Demo", "--target", str(repo)], expect_success=True)
        assert_runtime_proof_assets_exist(repo)


def test_adopt_installs_quality_firewall_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        run_init(["adopt", "--name", "Quality Adopted", "--target", str(repo)], expect_success=True)
        assert_quality_firewall_assets_exist(repo)
        assert_worktree_and_brittleness_assets_exist(repo)


def test_adopt_installs_schema_validation_assets_and_passes_schema_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        run_init(["adopt", "--name", "Schema Adopted", "--target", str(repo)], expect_success=True)
        assert_schema_validation_assets_exist(repo)
        assert_evidence_pack_assets_exist(repo)
        assert_upgrade_assets_exist(repo)
        completed = subprocess.run(
            [sys.executable, str(repo / "scripts" / "statedd_validate_schema.py"), str(repo)],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"Adopted repo schema validation failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )


def test_template_root_uses_template_maintenance_mode() -> None:
    project_state = (ROOT / "PROJECT_STATE.yaml").read_text(encoding="utf-8")
    if "repo_role: template_repository" not in project_state:
        raise AssertionError("Root PROJECT_STATE.yaml does not declare repo_role: template_repository")
    if "statedd_mode: template-maintenance" not in project_state:
        raise AssertionError("Root PROJECT_STATE.yaml does not declare statedd_mode: template-maintenance")
    if "Your Project" in project_state:
        raise AssertionError("Root PROJECT_STATE.yaml still contains downstream placeholder text")


def test_template_root_bootstrap_gate_passes() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_state_docs.py"), "--bootstrap-gate", str(ROOT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"Template-maintenance root should pass bootstrap gate\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


def test_adopt_installs_v2_executable_workflow_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        run_init(
            ["adopt", "--name", "v2 Adopted", "--target", str(repo), "--profile", "team"],
            expect_success=True,
        )
        assert_v2_assets_exist(repo)


def test_optional_github_assets_are_recorded_in_resolved_lock() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Existing\n", encoding="utf-8")
        run_init(
            [
                "adopt",
                "--name",
                "GitHub Optional",
                "--target",
                str(repo),
                "--profile",
                "team",
                "--install-github-assets",
            ],
            expect_success=True,
        )
        manifest = json.loads((repo / "STATEDD_ASSETS.json").read_text(encoding="utf-8"))
        if "github" not in manifest["asset_sets"]:
            raise AssertionError("Optional github asset set is absent from lock provenance")
        if "github_issue_and_pr_templates" not in manifest["capabilities"]:
            raise AssertionError("Optional github capability is absent from lock provenance")


def test_handoff_snapshot_runs() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "statedd_handoff.py"), "--no-include-listeners"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"Expected handoff helper success, got {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if "StateDD Handoff Snapshot" not in completed.stdout or "repo path:" not in completed.stdout:
        raise AssertionError(f"Handoff helper output is missing required fields:\n{completed.stdout}")


def test_doctor_runs() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "statedd_doctor.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"Expected doctor helper success, got {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    for phrase in ("StateDD Health", "Local audit readiness:", "Remote closure: not checked", "Current HEAD:"):
        if phrase not in completed.stdout:
            raise AssertionError(f"Doctor helper output missing phrase: {phrase}")


def main() -> int:
    tests = [
        test_adopt_rejects_symlinked_managed_directory,
        test_new_rejects_symlinked_existing_directory,
        test_new_rejects_symlinked_target_root,
        test_new_rejects_directory_destination_before_any_write,
        test_new_rejects_file_parent_before_any_write,
        test_new_replaces_hardlinked_managed_file_without_mutating_external_inode,
        test_new_replaces_hardlinked_copied_asset_without_mutating_external_inode,
        test_readme_link_rejects_symlinked_readme_before_writes,
        test_top_level_help_shows_subcommands,
        test_legacy_new_invocation_still_works,
        test_new_copies_curated_template_surface_only,
        test_new_includes_tool_model_routing_guide,
        test_new_includes_usability_assets,
        test_new_includes_version_assets_and_passes_version_check,
        test_new_includes_runtime_proof_asset,
        test_new_includes_quality_firewall_assets,
        test_new_includes_schema_validation_assets_and_passes_schema_validation,
        test_new_repo_still_fails_bootstrap_gate_until_investigated,
        test_new_includes_v2_executable_workflow_assets,
        test_new_excludes_template_only_payload_and_manifest_is_exact,
        test_adopt_installs_tool_model_routing_guide,
        test_adopt_installs_usability_assets,
        test_adopt_installs_version_assets_and_passes_version_check,
        test_adopt_installs_runtime_proof_asset,
        test_adopt_installs_quality_firewall_assets,
        test_adopt_installs_schema_validation_assets_and_passes_schema_validation,
        test_adopt_installs_v2_executable_workflow_assets,
        test_optional_github_assets_are_recorded_in_resolved_lock,
        test_template_root_uses_template_maintenance_mode,
        test_template_root_bootstrap_gate_passes,
        test_handoff_snapshot_runs,
        test_doctor_runs,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
