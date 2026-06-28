#!/usr/bin/env python3
"""Regression tests for the StateDD initializer.

These tests intentionally stay stdlib-only so template maintainers and
downstream repos can run them without installing a test framework.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


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
        run_init(["new", "--name", "Routing Demo", "--target", str(target)], expect_success=True)

        guide = target / "prompts" / "TOOL_MODEL_ROUTING_GUIDE.md"
        if not guide.exists():
            raise AssertionError("New repo did not include prompts/TOOL_MODEL_ROUTING_GUIDE.md")

        agents = (target / "AGENTS.md").read_text(encoding="utf-8")
        if "prompts/TOOL_MODEL_ROUTING_GUIDE.md" not in agents:
            raise AssertionError("Generated AGENTS.md does not reference the routing guide")


def assert_usability_assets_exist(root: Path) -> None:
    required = [
        root / "docs" / "GETTING_STARTED_5_MIN.md",
        root / "prompts" / "OPENCODE_STARTUP_PROMPT.md",
        root / "scripts" / "statedd_handoff.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing usability assets: {missing}")


def assert_version_assets_exist(root: Path) -> None:
    required = [
        root / "VERSION",
        root / "docs" / "UPGRADING.md",
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


def assert_evidence_pack_assets_exist(root: Path) -> None:
    required = [
        root / "schemas" / "evidence_manifest.schema.json",
        root / "scripts" / "statedd_evidence_pack.py",
        root / "scripts" / "test_evidence_pack.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing evidence pack assets: {missing}")


def assert_upgrade_assets_exist(root: Path) -> None:
    required = [
        root / "scripts" / "statedd_upgrade.py",
        root / "scripts" / "test_upgrade.py",
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
    if "## Quality Firewall" not in agents:
        raise AssertionError("Generated AGENTS.md does not include the quality firewall contract")
    if "quality_gates:" not in state or "runtime_truth:" not in state:
        raise AssertionError("Generated PROJECT_STATE.yaml lacks quality gate/runtime truth fields")
    if "known_bad_event" not in evidence or "runtime_truth" not in evidence:
        raise AssertionError("Generated EVIDENCE_LOG.md lacks the expanded evidence taxonomy")


def assert_schema_validation_assets_exist(root: Path) -> None:
    required = [
        root / "schemas" / "project_state.schema.json",
        root / "schemas" / "project_dna.schema.json",
        root / "schemas" / "project_adapter.schema.json",
        root / "schemas" / "runtime_identity.schema.json",
        root / "schemas" / "evidence_readme_contract.json",
        root / "schemas" / "evidence_manifest.schema.json",
        root / "schemas" / "final_handoff_contract.json",
        root / "scripts" / "statedd_validate_schema.py",
        root / "scripts" / "test_schema_validation.py",
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


def test_new_includes_schema_validation_assets_and_passes_schema_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(["new", "--name", "Schema Demo", "--target", str(target)], expect_success=True)
        assert_schema_validation_assets_exist(target)
        assert_evidence_pack_assets_exist(target)
        assert_upgrade_assets_exist(target)
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
        run_init(["new", "--name", "v2 Demo", "--target", str(target)], expect_success=True)
        assert_v2_assets_exist(target)


def test_new_includes_license_faq() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(["new", "--name", "License Demo", "--target", str(target)], expect_success=True)
        faq = target / "LICENSE_FAQ.md"
        if not faq.exists():
            raise AssertionError("New repo did not include LICENSE_FAQ.md")
        license_text = (target / "LICENSE").read_text(encoding="utf-8")
        if "Teaching Rights Reserved" not in license_text:
            raise AssertionError("Generated LICENSE does not reserve teaching rights")


def test_adopt_installs_tool_model_routing_guide() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Existing Project\n", encoding="utf-8")

        run_init(["adopt", "--name", "Routing Demo", "--target", str(repo)], expect_success=True)

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
        run_init(["adopt", "--name", "v2 Adopted", "--target", str(repo)], expect_success=True)
        assert_v2_assets_exist(repo)


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
    for phrase in ("StateDD Health", "Closure grade:", "Current HEAD:"):
        if phrase not in completed.stdout:
            raise AssertionError(f"Doctor helper output missing phrase: {phrase}")


def main() -> int:
    tests = [
        test_adopt_rejects_symlinked_managed_directory,
        test_new_rejects_symlinked_existing_directory,
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
        test_new_includes_license_faq,
        test_adopt_installs_tool_model_routing_guide,
        test_adopt_installs_usability_assets,
        test_adopt_installs_version_assets_and_passes_version_check,
        test_adopt_installs_runtime_proof_asset,
        test_adopt_installs_quality_firewall_assets,
        test_adopt_installs_schema_validation_assets_and_passes_schema_validation,
        test_adopt_installs_v2_executable_workflow_assets,
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
