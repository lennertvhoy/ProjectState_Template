#!/usr/bin/env python3
"""Regression tests for ProjectState schema-backed validation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "projectstate_validate_schema.py"
INIT_SCRIPT = ROOT / "scripts" / "init_template.py"


def run(args: list[str], *, cwd: Path = ROOT, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
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


def run_init(args: list[str]) -> subprocess.CompletedProcess[str]:
    if "--profile" not in args:
        args = [*args, "--profile", "team"]
    return run([str(INIT_SCRIPT), *args], expect_success=True)


def assert_output_contains(completed: subprocess.CompletedProcess[str], expected: str) -> None:
    output = f"{completed.stdout}\n{completed.stderr}"
    if expected not in output:
        raise AssertionError(f"Expected output to contain {expected!r}, got:\n{output}")


def test_root_schema_validation_passes() -> None:
    run([str(VALIDATOR)], expect_success=True)


def test_asset_lock_state_and_adapter_profiles_must_agree() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "profile-agreement"
        run_init(["new", "--name", "Profile Agreement", "--profile", "solo", "--target", str(target)])
        adapter = target / "PROJECT_ADAPTER.yaml"
        adapter.write_text(
            adapter.read_text(encoding="utf-8").replace("  profile: solo\n", "  profile: team\n", 1),
            encoding="utf-8",
        )

        completed = run(
            [str(target / "scripts" / "projectstate_validate_schema.py"), str(target)],
            cwd=target,
            expect_success=False,
        )

        assert_output_contains(completed, "manifest/project metadata agreement")
        assert_output_contains(completed, "must match asset manifest profile 'solo'")


def test_asset_lock_requires_profile_metadata_in_both_documents() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "profile-metadata-required"
        run_init(["new", "--name", "Profile Metadata", "--profile", "solo", "--target", str(target)])
        adapter = target / "PROJECT_ADAPTER.yaml"
        adapter.write_text(
            adapter.read_text(encoding="utf-8").replace("  profile: solo\n", "", 1),
            encoding="utf-8",
        )

        completed = run(
            [str(target / "scripts" / "projectstate_validate_schema.py"), str(target)],
            cwd=target,
            expect_success=False,
        )

        assert_output_contains(completed, "PROJECT_ADAPTER.yaml.project.profile")
        assert_output_contains(completed, "profile is missing")


def test_invalid_project_state_fails_with_actionable_message() -> None:
    completed = run(
        [
            str(VALIDATOR),
            "--file",
            str(ROOT / "fixtures" / "schema_validation" / "invalid_project_state" / "PROJECT_STATE.yaml"),
            "--schema",
            str(ROOT / "schemas" / "project_state.schema.json"),
        ],
        expect_success=False,
    )
    assert_output_contains(completed, "template_repository")
    assert_output_contains(completed, "template-maintenance")


def project_state_fixture(*, active_problem: str = "", repository_extra: str = "") -> str:
    return f"""metadata:
  updated_at: 2026-07-12T00:00:00+00:00
  updated_by: test
  version: projectstate-template-v5
workflow:
  repo_role: template_repository
  projectstate_mode: template-maintenance
  repo_mode: template-maintenance
current_state:
  execution_mode:
    status: observed
    mode: template-maintenance
  open_p0_failures: []
  repository:
    canonical_path: .
    path_status: observed
{repository_extra}  operating_mode:
    status: observed
    mode: template-maintenance
  project:
    name: ProjectState Test
    type: template
    lifecycle_stage: template-maintenance
  evidence:
    status: active
    ledger: docs/EVIDENCE_LOG.md
active_problems:{active_problem}
"""


def test_project_state_schema_accepts_stable_post_merge_target_state() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "PROJECT_STATE.yaml"
        path.write_text(project_state_fixture(active_problem=" []"), encoding="utf-8")
        run(
            [
                str(VALIDATOR),
                "--file",
                str(path),
                "--schema",
                str(ROOT / "schemas" / "project_state.schema.json"),
            ],
            expect_success=True,
        )


def test_project_state_schema_rejects_terminal_active_problem() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "PROJECT_STATE.yaml"
        path.write_text(
            project_state_fixture(
                active_problem=(
                    "\n  - id: BL-DONE-001\n"
                    "    severity: P1\n"
                    "    status: merged_into_main"
                )
            ),
            encoding="utf-8",
        )
        completed = run(
            [
                str(VALIDATOR),
                "--file",
                str(path),
                "--schema",
                str(ROOT / "schemas" / "project_state.schema.json"),
            ],
            expect_success=False,
        )
        assert_output_contains(completed, "terminal work cannot remain in active_problems")


def test_project_state_schema_rejects_volatile_main_head_field() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "PROJECT_STATE.yaml"
        path.write_text(
            project_state_fixture(
                active_problem=" []",
                repository_extra=(
                    "    main_head: 0123456789abcdef0123456789abcdef01234567\n"
                ),
            ),
            encoding="utf-8",
        )
        completed = run(
            [
                str(VALIDATOR),
                "--file",
                str(path),
                "--schema",
                str(ROOT / "schemas" / "project_state.schema.json"),
            ],
            expect_success=False,
        )
        assert_output_contains(completed, "volatile containing-main SHA")


def test_invalid_evidence_readme_fails_contract() -> None:
    completed = run(
        [
            str(VALIDATOR),
            "--file",
            str(ROOT / "fixtures" / "schema_validation" / "invalid_evidence_readme" / "README.md"),
            "--schema",
            str(ROOT / "schemas" / "evidence_readme_contract.json"),
        ],
        expect_success=False,
    )
    assert_output_contains(completed, "missing required heading")


def test_runtime_not_applicable_fixture_passes() -> None:
    run(
        [
            str(VALIDATOR),
            "--file",
            str(ROOT / "fixtures" / "schema_validation" / "runtime-not-applicable" / "runtime_identity.json"),
            "--schema",
            str(ROOT / "schemas" / "runtime_identity.schema.json"),
        ],
        expect_success=True,
    )


def test_runtime_required_unreachable_fixture_fails() -> None:
    completed = run(
        [
            str(VALIDATOR),
            "--file",
            str(ROOT / "fixtures" / "schema_validation" / "runtime-required-unreachable" / "runtime_identity.json"),
            "--schema",
            str(ROOT / "schemas" / "runtime_identity.schema.json"),
        ],
        expect_success=False,
    )
    assert_output_contains(completed, "runtime.required is true")
    assert_output_contains(completed, "endpoint_reachable must be true")


def test_duplicate_root_yaml_key_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "duplicate-root"
        run_init(["new", "--name", "Duplicate Root", "--target", str(target), "--profile", "minimal"])
        dna = target / "PROJECT_DNA.yaml"
        dna.write_text(dna.read_text(encoding="utf-8") + "\ninvariants:\n  - duplicate\n", encoding="utf-8")
        completed = run(
            [str(target / "scripts" / "projectstate_validate_schema.py"), str(target)],
            cwd=target,
            expect_success=False,
        )
        assert_output_contains(completed, "duplicate mapping key 'invariants'")


def test_duplicate_nested_yaml_key_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "duplicate-nested"
        run_init(["new", "--name", "Duplicate Nested", "--target", str(target), "--profile", "minimal"])
        state = target / "PROJECT_STATE.yaml"
        text = state.read_text(encoding="utf-8")
        text = text.replace(
            "  repo_role: downstream_project\n",
            "  repo_role: downstream_project\n  repo_role: downstream_project\n",
            1,
        )
        state.write_text(text, encoding="utf-8")
        completed = run(
            [str(target / "scripts" / "projectstate_validate_schema.py"), str(target)],
            cwd=target,
            expect_success=False,
        )
        assert_output_contains(completed, "duplicate mapping key 'repo_role'")


def evidence_manifest_fixture() -> dict:
    return {
        "schema": "projectstate.evidence_manifest.v1",
        "slice_id": "BL-SCHEMA-001",
        "created_at": "2026-07-11T00:00:00+00:00",
        "repo": {"branch": "main", "head": "abc"},
        "claims": [
            {"id": "C1", "claim": "valid", "status": "validated", "evidence": ["artifact.txt"]}
        ],
        "artifacts": [
            {
                "path": "artifact.txt",
                "kind": "doc",
                "sha256": None,
                "redaction_status": "checked",
                "sensitive_data": "none_found",
            }
        ],
        "redaction": {"status": "checked"},
    }


def test_local_ref_shapes_unique_items_and_safe_paths_are_enforced() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "manifest.json"
        schema = ROOT / "schemas" / "evidence_manifest.schema.json"

        missing_ref_field = evidence_manifest_fixture()
        del missing_ref_field["artifacts"][0]["kind"]
        path.write_text(json.dumps(missing_ref_field), encoding="utf-8")
        completed = run(
            [str(VALIDATOR), "--file", str(path), "--schema", str(schema)],
            expect_success=False,
        )
        assert_output_contains(completed, "missing required property 'kind'")

        duplicate = evidence_manifest_fixture()
        duplicate["artifacts"].append(dict(duplicate["artifacts"][0]))
        path.write_text(json.dumps(duplicate), encoding="utf-8")
        completed = run(
            [str(VALIDATOR), "--file", str(path), "--schema", str(schema)],
            expect_success=False,
        )
        assert_output_contains(completed, "duplicate array item")

        unsafe = evidence_manifest_fixture()
        unsafe["artifacts"][0]["path"] = "/etc/hosts"
        unsafe["claims"][0]["evidence"] = ["/etc/hosts"]
        path.write_text(json.dumps(unsafe), encoding="utf-8")
        completed = run(
            [str(VALIDATOR), "--file", str(path), "--schema", str(schema)],
            expect_success=False,
        )
        assert_output_contains(completed, "absolute managed path")


def test_duplicate_json_keys_fail_schema_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "duplicate.json"
        path.write_text('{"schema":"one","schema":"two"}', encoding="utf-8")
        completed = run(
            [
                str(VALIDATOR),
                "--file",
                str(path),
                "--schema",
                str(ROOT / "schemas" / "evidence_manifest.schema.json"),
            ],
            expect_success=False,
        )
        assert_output_contains(completed, "duplicate JSON key 'schema'")


def test_numeric_and_object_size_constraints_are_enforced() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data = root / "data.json"
        schema = root / "schema.json"
        data.write_text('{"count":4}', encoding="utf-8")
        schema.write_text(
            json.dumps(
                {
                    "type": "object",
                    "minProperties": 2,
                    "properties": {
                        "count": {"type": "integer", "minimum": 5, "maximum": 7}
                    },
                }
            ),
            encoding="utf-8",
        )
        completed = run(
            [str(VALIDATOR), "--file", str(data), "--schema", str(schema)],
            expect_success=False,
        )
        assert_output_contains(completed, "expected at least 2 properties")
        assert_output_contains(completed, "expected value >= 5")


def test_repo_validation_rejects_symlinked_evidence_folder_without_reading_outside() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        outside = Path(tmp) / "outside"
        run_init(["new", "--name", "Symlink Evidence", "--target", str(root), "--profile", "minimal"])
        outside.mkdir()
        (outside / "manifest.json").write_text('{"secret":"do-not-read"}', encoding="utf-8")
        evidence_root = root / "docs" / "evidence"
        (evidence_root / ".gitkeep").unlink(missing_ok=True)
        os.symlink(outside, evidence_root / "linked")

        completed = run(
            [str(root / "scripts" / "projectstate_validate_schema.py"), str(root)],
            cwd=root,
            expect_success=False,
        )
        assert_output_contains(completed, "symlinked evidence folder")
        if "do-not-read" in completed.stdout + completed.stderr:
            raise AssertionError("Validator exposed outside-repository content")


def assert_schema_assets_exist(root: Path) -> None:
    required = [
        root / "schemas" / "project_state.schema.json",
        root / "schemas" / "project_dna.schema.json",
        root / "schemas" / "project_adapter.schema.json",
        root / "schemas" / "projectstate_assets.schema.json",
        root / "schemas" / "runtime_identity.schema.json",
        root / "schemas" / "evidence_readme_contract.json",
        root / "schemas" / "final_handoff_contract.json",
        root / "scripts" / "projectstate_validate_schema.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing schema validation assets: {missing}")


def test_generated_new_repo_includes_schema_validation_assets_and_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "generated-new"
        run_init(["new", "--name", "Schema Demo", "--target", str(target)])
        assert_schema_assets_exist(target)
        run([str(target / "scripts" / "projectstate_validate_schema.py"), str(target)], cwd=target, expect_success=True)


def test_adopted_repo_includes_schema_validation_assets_and_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "adopted"
        target.mkdir()
        (target / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        run_init(["adopt", "--name", "Schema Adopted", "--target", str(target)])
        assert_schema_assets_exist(target)
        run([str(target / "scripts" / "projectstate_validate_schema.py"), str(target)], cwd=target, expect_success=True)


def main() -> int:
    tests = [
        test_root_schema_validation_passes,
        test_asset_lock_state_and_adapter_profiles_must_agree,
        test_asset_lock_requires_profile_metadata_in_both_documents,
        test_invalid_project_state_fails_with_actionable_message,
        test_invalid_evidence_readme_fails_contract,
        test_runtime_not_applicable_fixture_passes,
        test_runtime_required_unreachable_fixture_fails,
        test_duplicate_root_yaml_key_fails,
        test_duplicate_nested_yaml_key_fails,
        test_local_ref_shapes_unique_items_and_safe_paths_are_enforced,
        test_duplicate_json_keys_fail_schema_validation,
        test_numeric_and_object_size_constraints_are_enforced,
        test_repo_validation_rejects_symlinked_evidence_folder_without_reading_outside,
        test_generated_new_repo_includes_schema_validation_assets_and_passes,
        test_adopted_repo_includes_schema_validation_assets_and_passes,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
