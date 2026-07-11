#!/usr/bin/env python3
"""Regression tests for statedd_upgrade.py.

Stays stdlib-only.
"""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

try:
    import statedd_upgrade as upgrade_module
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts import statedd_upgrade as upgrade_module


ROOT = Path(__file__).resolve().parents[1]
UPGRADE_SCRIPT = ROOT / "scripts" / "statedd_upgrade.py"
INIT_SCRIPT = ROOT / "scripts" / "init_template.py"


def run_upgrade(args: list[str], *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(UPGRADE_SCRIPT), *args],
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
        raise AssertionError(
            f"Expected failure for {args}, got success\nstdout:\n{completed.stdout}"
        )
    return completed


def run_init(args: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(INIT_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"init failed: {completed.returncode}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def manifest_payload(target: Path) -> dict[str, object]:
    return json.loads((target / "STATEDD_ASSETS.json").read_text(encoding="utf-8"))


def test_dry_run_on_current_repo_refuses_template_root() -> None:
    run_upgrade([str(ROOT)], expect_success=False)


def test_dry_run_on_generated_repo_is_no_op_or_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(["new", "--name", "Upgrade Demo", "--target", str(target)])
        completed = run_upgrade([str(target)], expect_success=True)
        output = completed.stdout
        if "Will add:" not in output:
            raise AssertionError("Upgrade plan missing 'Will add' section")
        if "Will modify:" not in output:
            raise AssertionError("Upgrade plan missing 'Will modify' section")


def test_dry_run_on_older_fixture_reports_missing_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        # Simulate an older repo by removing newer assets.
        (target / "scripts" / "statedd_evidence_pack.py").unlink(missing_ok=True)
        (target / "schemas" / "evidence_manifest.schema.json").unlink(missing_ok=True)
        (target / "scripts" / "test_evidence_pack.py").unlink(missing_ok=True)
        (target / "scripts" / "statedd_worktree_guard.py").unlink(missing_ok=True)
        (target / "ANTI_BRITTLENESS_GUARD.md").unlink(missing_ok=True)

        completed = run_upgrade([str(target)], expect_success=True)
        output = completed.stdout
        if "statedd_evidence_pack.py" not in output:
            raise AssertionError("Missing evidence pack script not reported")
        if "evidence_manifest.schema.json" not in output:
            raise AssertionError("Missing evidence manifest schema not reported")
        if "statedd_worktree_guard.py" not in output:
            raise AssertionError("Missing worktree guard script not reported")
        if "ANTI_BRITTLENESS_GUARD.md" not in output:
            raise AssertionError("Missing anti-brittleness guard doc not reported")


def test_apply_adds_safe_missing_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        (target / "scripts" / "statedd_evidence_pack.py").unlink(missing_ok=True)
        (target / "schemas" / "evidence_manifest.schema.json").unlink(missing_ok=True)
        (target / "QUALITY_FIREWALL.md").unlink(missing_ok=True)
        (target / "docs" / "quality_gates" / "README.md").unlink(missing_ok=True)
        (target / "scripts" / "statedd_worktree_guard.py").unlink(missing_ok=True)
        (target / "docs" / "quality_gates" / "ANTI_BRITTLENESS_GATE.md").unlink(missing_ok=True)

        run_upgrade([str(target), "--apply"], expect_success=True)
        if not (target / "scripts" / "statedd_evidence_pack.py").exists():
            raise AssertionError("Apply did not add missing script")
        if not (target / "schemas" / "evidence_manifest.schema.json").exists():
            raise AssertionError("Apply did not add missing schema")
        if not (target / "QUALITY_FIREWALL.md").exists():
            raise AssertionError("Apply did not add missing quality firewall")
        if not (target / "docs" / "quality_gates" / "README.md").exists():
            raise AssertionError("Apply did not add missing quality gates README")
        if not (target / "scripts" / "statedd_worktree_guard.py").exists():
            raise AssertionError("Apply did not add missing worktree guard")
        if not (target / "docs" / "quality_gates" / "ANTI_BRITTLENESS_GATE.md").exists():
            raise AssertionError("Apply did not add missing anti-brittleness gate")


def test_apply_preserves_readme_and_project_truth() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        original_readme = (target / "README.md").read_text(encoding="utf-8")
        original_state = (target / "PROJECT_STATE.yaml").read_text(encoding="utf-8")

        run_upgrade([str(target), "--apply"], expect_success=True)

        if (target / "README.md").read_text(encoding="utf-8") != original_readme:
            raise AssertionError("Apply unexpectedly changed README.md")
        if (target / "PROJECT_STATE.yaml").read_text(encoding="utf-8") != original_state:
            raise AssertionError("Apply unexpectedly changed PROJECT_STATE.yaml")


def test_conflict_fixture_refuses_unsafe_overwrite() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        # Modify a safe managed asset locally so it differs from template.
        script = target / "scripts" / "statedd_evidence_pack.py"
        script.write_text("# locally modified\n", encoding="utf-8")

        completed = run_upgrade([str(target)], expect_success=True)
        if "Conflicts" not in completed.stdout:
            raise AssertionError("Expected conflict section in dry-run output")
        if "statedd_evidence_pack.py" not in completed.stdout:
            raise AssertionError("Expected modified script to be reported as conflict")

        # Apply without --force-managed should refuse.
        run_upgrade([str(target), "--apply"], expect_success=False)


def test_force_managed_replaces_outdated_safe_asset() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        script = target / "scripts" / "statedd_evidence_pack.py"
        script.write_text("# locally modified\n", encoding="utf-8")

        run_upgrade([str(target), "--apply", "--force-managed"], expect_success=True)
        if "# locally modified" in script.read_text(encoding="utf-8"):
            raise AssertionError("--force-managed did not replace outdated safe asset")


def test_force_managed_never_overwrites_truth_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        state = target / "PROJECT_STATE.yaml"
        state.write_text("# locally modified state\n", encoding="utf-8")

        run_upgrade([str(target), "--apply", "--force-managed"], expect_success=True)
        if "# locally modified state" not in state.read_text(encoding="utf-8"):
            raise AssertionError("--force-managed unexpectedly overwrote a project-truth file")


def test_upgrade_never_installs_template_tests_or_history() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "legacy-downstream"
        run_init(
            ["new", "--name", "No Leak", "--profile", "minimal", "--target", str(target)]
        )
        (target / "VERSION").unlink()
        run_upgrade([str(target), "--apply"], expect_success=True)
        leaked = [
            path.relative_to(target).as_posix()
            for path in target.rglob("*")
            if path.is_file()
            and (
                path.name.startswith("test_")
                or path.name == "init_template.py"
                or "fixtures" in path.parts
                or ("evidence" in path.parts and path.name != ".gitkeep")
                or path.name == "CHANGELOG.md"
            )
        ]
        if leaked:
            raise AssertionError(f"Upgrade installed template-only payload: {sorted(leaked)}")


def test_report_writes_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        report = Path(tmp) / "report.json"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        run_upgrade([str(target), "--report", str(report)], expect_success=True)
        if not report.exists():
            raise AssertionError("Report file was not written")
        data = json.loads(report.read_text(encoding="utf-8"))
        if data.get("schema") != "statedd.upgrade_report.v2":
            raise AssertionError("Report has unexpected schema")


def test_report_reflects_dry_run_value() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        dry_report = Path(tmp) / "dry_report.json"
        applied_report = Path(tmp) / "applied_report.json"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])

        run_upgrade([str(target), "--report", str(dry_report)], expect_success=True)
        dry_data = json.loads(dry_report.read_text(encoding="utf-8"))
        if dry_data.get("apply_requested") is not False:
            raise AssertionError("Dry-run plan report should state apply_requested: false")

        run_upgrade([str(target), "--apply", "--report", str(applied_report)], expect_success=True)
        applied_data = json.loads(applied_report.read_text(encoding="utf-8"))
        if applied_data.get("apply_requested") is not True:
            raise AssertionError("Apply-mode plan report should state apply_requested: true")
        if applied_data.get("application_status") != "not_proven_by_plan_report":
            raise AssertionError("Plan report must not claim that application succeeded")
        if "template_root" in applied_data or "target" in applied_data:
            raise AssertionError("Upgrade plan report leaked absolute local paths")


def test_report_cannot_overwrite_target_truth_or_existing_sidecar() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "target"
        run_init(["new", "--name", "Report Safety", "--profile", "minimal", "--target", str(target)])
        truth = target / "PROJECT_STATE.yaml"
        before = truth.read_bytes()
        run_upgrade(
            [str(target), "--apply", "--report", str(truth)],
            expect_success=False,
        )
        if truth.read_bytes() != before:
            raise AssertionError("Upgrade report path overwrote protected project truth")

        sidecar = Path(tmp) / "existing.json"
        sidecar.write_text("preserve\n", encoding="utf-8")
        run_upgrade([str(target), "--report", str(sidecar)], expect_success=False)
        if sidecar.read_text(encoding="utf-8") != "preserve\n":
            raise AssertionError("Upgrade report overwrote an existing sidecar")


def test_no_lock_apply_refuses_false_profile_capabilities() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "legacy"
        target.mkdir()
        before = tree_digest(target)
        completed = run_upgrade(
            [str(target), "--profile", "minimal", "--apply"],
            expect_success=False,
        )
        if "init_template.py adopt" not in completed.stdout:
            raise AssertionError(f"No-lock refusal did not direct safe adoption:\n{completed.stdout}")
        if tree_digest(target) != before:
            raise AssertionError("No-lock apply wrote a partial false-capability instance")


def test_missing_manifest_fails_closed_without_explicit_profile() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "legacy"
        target.mkdir()
        before = tree_digest(target)
        completed = run_upgrade([str(target), "--apply"], expect_success=False)
        if "--profile" not in completed.stdout:
            raise AssertionError(f"Missing explicit-profile guidance:\n{completed.stdout}")
        if tree_digest(target) != before:
            raise AssertionError("No-lock upgrade changed the target before explicit profile selection")


def test_old_manifest_does_not_suppress_new_profile_asset() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "old-minimal"
        run_init(["new", "--name", "Old Minimal", "--profile", "minimal", "--target", str(target)])
        new_asset = target / "EFFICIENCY_BUDGET.yaml"
        new_asset.unlink()
        v1 = {
            "schema": "statedd.runtime_assets.v1",
            "template_version": "statedd-template-v4",
            "profile": "minimal",
            "generation_mode": "new",
            "assets": ["VERSION", "STATEDD_ASSETS.json"],
            "excluded_classes": ["template_tests"],
        }
        (target / "STATEDD_ASSETS.json").write_text(json.dumps(v1), encoding="utf-8")

        completed = run_upgrade([str(target)], expect_success=True)
        if "EFFICIENCY_BUDGET.yaml" not in completed.stdout or "new_profile_asset" not in completed.stdout:
            raise AssertionError(f"New profile asset was suppressed by old manifest:\n{completed.stdout}")
        run_upgrade([str(target), "--apply"], expect_success=True)
        if not new_asset.is_file():
            raise AssertionError("New profile asset was not installed")
        upgraded = manifest_payload(target)
        if upgraded.get("schema") != "statedd.runtime_assets.v2":
            raise AssertionError("Successful apply did not migrate the asset lock")


@pytest.mark.parametrize(
    "content",
    [
        "{broken",
        '{"schema":"wrong"}',
        '{"schema":"statedd.runtime_assets.v1","schema":"statedd.runtime_assets.v1"}',
        json.dumps(
            {
                "schema": "statedd.runtime_assets.v1",
                "template_version": "statedd-template-v4",
                "profile": "minimal",
                "generation_mode": "new",
                "assets": ["../escape"],
                "excluded_classes": ["template_tests"],
            }
        ),
        json.dumps(
            {
                "schema": "statedd.runtime_assets.v1",
                "template_version": "statedd-template-v4",
                "profile": "minimal",
                "generation_mode": "new",
                "assets": ["/absolute"],
                "excluded_classes": ["template_tests"],
            }
        ),
    ],
)
def test_malformed_or_unsafe_manifest_fails_closed_without_writes(content: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "malformed"
        run_init(["new", "--name", "Malformed", "--profile", "minimal", "--target", str(target)])
        (target / "STATEDD_ASSETS.json").write_text(content, encoding="utf-8")
        before = tree_digest(target)
        run_upgrade([str(target), "--apply"], expect_success=False)
        if tree_digest(target) != before:
            raise AssertionError("Malformed manifest caused target writes")


def test_upgrade_rejects_symlinked_root_before_writes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        actual = root / "actual"
        run_init(["new", "--name", "Symlink Root", "--profile", "minimal", "--target", str(actual)])
        link = root / "linked"
        os.symlink(actual, link)
        before = tree_digest(actual)
        completed = run_upgrade([str(link), "--apply"], expect_success=False)
        if "symlink" not in completed.stdout.lower():
            raise AssertionError(f"Expected root-symlink refusal:\n{completed.stdout}")
        if tree_digest(actual) != before:
            raise AssertionError("Symlink-root refusal happened after writes")


def test_nested_symlink_preflight_causes_zero_partial_writes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "target"
        outside = root / "outside"
        outside.mkdir()
        run_init(["new", "--name", "Nested Symlink", "--profile", "minimal", "--target", str(target)])
        (target / "VERSION").unlink()
        schemas = target / "schemas"
        for path in schemas.iterdir():
            path.unlink()
        schemas.rmdir()
        os.symlink(outside, schemas)
        before = tree_digest(target)
        run_upgrade([str(target), "--apply"], expect_success=False)
        if (target / "VERSION").exists():
            raise AssertionError("Upgrade wrote an earlier asset before detecting nested symlink")
        if list(outside.iterdir()):
            raise AssertionError("Upgrade wrote through nested target symlink")
        if tree_digest(target) != before:
            raise AssertionError("Nested-symlink preflight changed target")


def test_pristine_old_base_updates_without_force_but_local_change_conflicts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "pristine-old"
        run_init(["new", "--name", "Pristine Old", "--profile", "minimal", "--target", str(target)])
        path = target / "VERSION"
        old = b"statedd-template-v4\n"
        path.write_bytes(old)
        payload = manifest_payload(target)
        for record in payload["managed_assets"]:  # type: ignore[index]
            if record["path"] == "VERSION":
                old_hash = hashlib.sha256(old).hexdigest()
                record["base_sha256"] = old_hash
                record["installed_sha256"] = old_hash
        (target / "STATEDD_ASSETS.json").write_text(json.dumps(payload), encoding="utf-8")
        completed = run_upgrade([str(target), "--apply"], expect_success=True)
        if "unmodified_since_previous_install" not in completed.stdout:
            raise AssertionError(f"Pristine base was not recognized:\n{completed.stdout}")
        if path.read_text(encoding="utf-8").strip() != "statedd-template-v5":
            raise AssertionError("Pristine old asset was not upgraded")


def test_removed_asset_is_reported_retained_and_locked_as_retired() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "retired"
        run_init(["new", "--name", "Retired", "--profile", "minimal", "--target", str(target)])
        obsolete = target / "obsolete-template-asset.txt"
        obsolete.write_text("old\n", encoding="utf-8")
        payload = manifest_payload(target)
        sample = next(record for record in payload["managed_assets"] if record["path"] == "VERSION")  # type: ignore[index]
        retired_record = dict(sample)
        retired_record["path"] = obsolete.name
        retired_record["base_sha256"] = hashlib.sha256(obsolete.read_bytes()).hexdigest()
        retired_record["installed_sha256"] = retired_record["base_sha256"]
        payload["managed_assets"].append(retired_record)  # type: ignore[index]
        (target / "STATEDD_ASSETS.json").write_text(json.dumps(payload), encoding="utf-8")

        completed = run_upgrade([str(target), "--apply"], expect_success=True)
        if "retained on disk" not in completed.stdout:
            raise AssertionError(f"Removed asset was not reported:\n{completed.stdout}")
        if not obsolete.is_file():
            raise AssertionError("Removed template asset was silently deleted")
        upgraded = manifest_payload(target)
        if obsolete.name not in {item["path"] for item in upgraded["retired_assets"]}:  # type: ignore[index]
            raise AssertionError("Removed asset was not retained as historical ownership evidence")


def test_interrupted_apply_rolls_back_files_and_manifest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "rollback"
        run_init(["new", "--name", "Rollback", "--profile", "minimal", "--target", str(target)])
        (target / "VERSION").unlink()
        (target / "EFFICIENCY_BUDGET.yaml").unlink()
        before = tree_digest(target)
        catalog = upgrade_module.load_profile_catalog(ROOT)
        history = upgrade_module.load_manifest(target, explicit_profile=None, catalog=catalog)
        resolved = upgrade_module.resolve_profile(catalog, history.profile)
        plan = upgrade_module.plan_upgrade(target, history, catalog, resolved, force_managed=False)
        manifest, changed = upgrade_module.build_manifest(
            history, plan, catalog, resolved, upgrade_module.read_version(ROOT) or "unknown"
        )
        original = upgrade_module._atomic_replace_bytes
        calls = 0

        def fail_once(destination: Path, content: bytes, mode: int) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected interruption")
            original(destination, content, mode)

        with mock.patch.object(upgrade_module, "_atomic_replace_bytes", side_effect=fail_once):
            with pytest.raises(OSError, match="injected interruption"):
                upgrade_module.execute_transaction(plan, target, manifest if changed else None)
        if tree_digest(target) != before:
            raise AssertionError("Interrupted upgrade did not restore original tree bytes")


def test_manifest_change_after_planning_blocks_all_upgrade_writes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "manifest-race"
        run_init(["new", "--name", "Race", "--profile", "minimal", "--target", str(target)])
        (target / "VERSION").unlink()
        catalog = upgrade_module.load_profile_catalog(ROOT)
        history = upgrade_module.load_manifest(target, explicit_profile=None, catalog=catalog)
        resolved = upgrade_module.resolve_profile(catalog, history.profile)
        plan = upgrade_module.plan_upgrade(target, history, catalog, resolved, force_managed=False)
        manifest, changed = upgrade_module.build_manifest(
            history, plan, catalog, resolved, upgrade_module.read_version(ROOT) or "unknown"
        )
        lock = target / "STATEDD_ASSETS.json"
        lock.write_text(lock.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        altered = lock.read_bytes()

        with pytest.raises(upgrade_module.ContractError, match="changed after planning"):
            upgrade_module.execute_transaction(plan, target, manifest if changed else None)

        if (target / "VERSION").exists() or lock.read_bytes() != altered:
            raise AssertionError("Manifest race was detected only after target mutation")


@pytest.mark.parametrize("changed_path", ["VERSION", "PROJECT_STATE.yaml"])
def test_observed_skip_or_protected_change_after_planning_blocks_all_writes(
    changed_path: str,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "observation-race"
        run_init(["new", "--name", "Observe", "--profile", "minimal", "--target", str(target)])
        missing = target / "EFFICIENCY_BUDGET.yaml"
        missing.unlink()
        catalog = upgrade_module.load_profile_catalog(ROOT)
        history = upgrade_module.load_manifest(target, explicit_profile=None, catalog=catalog)
        resolved = upgrade_module.resolve_profile(catalog, history.profile)
        plan = upgrade_module.plan_upgrade(target, history, catalog, resolved, force_managed=False)
        manifest, changed = upgrade_module.build_manifest(
            history, plan, catalog, resolved, upgrade_module.read_version(ROOT) or "unknown"
        )
        observed = target / changed_path
        observed.write_text(observed.read_text(encoding="utf-8") + "# concurrent edit\n", encoding="utf-8")
        altered = observed.read_bytes()

        with pytest.raises(upgrade_module.ContractError, match="changed after planning"):
            upgrade_module.execute_transaction(plan, target, manifest if changed else None)

        if missing.exists() or observed.read_bytes() != altered:
            raise AssertionError("Observation race was detected only after upgrade writes")


def test_missing_required_project_truth_blocks_apply() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "missing-truth"
        run_init(["new", "--name", "Truth", "--profile", "minimal", "--target", str(target)])
        (target / "PROJECT_STATE.yaml").unlink()
        (target / "VERSION").unlink()
        before = tree_digest(target)
        completed = run_upgrade([str(target), "--apply"], expect_success=False)
        if "required_protected_asset_is_missing" not in completed.stdout:
            raise AssertionError(f"Missing required truth was not blocking:\n{completed.stdout}")
        if tree_digest(target) != before:
            raise AssertionError("Upgrade wrote other assets while required project truth was missing")


def test_successful_apply_updates_manifest_and_second_run_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "idempotent"
        run_init(["new", "--name", "Idempotent", "--profile", "minimal", "--target", str(target)])
        (target / "VERSION").unlink()
        run_upgrade([str(target), "--apply"], expect_success=True)
        first = tree_digest(target)
        completed = run_upgrade([str(target), "--apply"], expect_success=True)
        if "Manifest update: no" not in completed.stdout:
            raise AssertionError(f"Second run still planned manifest churn:\n{completed.stdout}")
        if "Will add:\n  (none)" not in completed.stdout or "Will modify:\n  (none)" not in completed.stdout:
            raise AssertionError(f"Second run was not a no-op:\n{completed.stdout}")
        if tree_digest(target) != first:
            raise AssertionError("Second upgrade run changed the target")


def test_malformed_v2_top_level_and_history_fail_before_writes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "malformed-v2"
        run_init(["new", "--name", "Malformed v2", "--profile", "minimal", "--target", str(target)])
        payload = manifest_payload(target)
        payload["profile_dependencies"] = "invalid"
        payload["required_gate_level"] = -99
        payload["upgrade_history"] = [{}]
        (target / "STATEDD_ASSETS.json").write_text(json.dumps(payload), encoding="utf-8")
        before = tree_digest(target)

        completed = run_upgrade([str(target), "--apply"], expect_success=False)

        if "violates statedd.runtime_assets.v2" not in completed.stdout:
            raise AssertionError(f"Expected schema-backed lock refusal:\n{completed.stdout}")
        if tree_digest(target) != before:
            raise AssertionError("Malformed v2 lock caused upgrade writes")


def test_profile_transition_is_rejected_until_semantic_migration_exists() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "profile-transition"
        run_init(["new", "--name", "Profile", "--profile", "minimal", "--target", str(target)])
        before = tree_digest(target)

        completed = run_upgrade(
            [str(target), "--profile", "regulated", "--apply"],
            expect_success=False,
        )

        if "semantic migration" not in completed.stdout:
            raise AssertionError(f"Expected honest profile-transition refusal:\n{completed.stdout}")
        if tree_digest(target) != before:
            raise AssertionError("Rejected profile transition changed the target")


def test_reintroduced_retired_asset_recovers_ownership_and_is_not_still_retired() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "reintroduced"
        run_init(["new", "--name", "Reintroduced", "--profile", "minimal", "--target", str(target)])
        old_content = b"statedd-template-v0\n"
        (target / "VERSION").write_bytes(old_content)
        payload = manifest_payload(target)
        payload["managed_assets"] = [
            record for record in payload["managed_assets"] if record["path"] != "VERSION"
        ]
        payload["retired_assets"] = [
            {
                "path": "VERSION",
                "reason": "previously retired",
                "base_sha256": hashlib.sha256(old_content).hexdigest(),
            }
        ]
        (target / "STATEDD_ASSETS.json").write_text(json.dumps(payload), encoding="utf-8")

        run_upgrade([str(target), "--apply"], expect_success=True)

        upgraded = manifest_payload(target)
        if any(item["path"] == "VERSION" for item in upgraded["retired_assets"]):
            raise AssertionError("Reintroduced asset remains simultaneously retired")
        if (target / "VERSION").read_bytes() != (ROOT / "VERSION").read_bytes():
            raise AssertionError("Reintroduced pristine retired asset was not upgraded")


def test_modified_generated_control_conflicts_then_force_regenerates_and_locks_hash() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "generated-control"
        run_init(["new", "--name", "Generated", "--profile", "regulated", "--target", str(target)])
        workflow = target / ".github" / "workflows" / "statedd-validate.yml"
        workflow.write_text(workflow.read_text(encoding="utf-8") + "# STALE-HACK\n", encoding="utf-8")

        completed = run_upgrade([str(target), "--apply"], expect_success=False)
        if "locally_modified_generated_control" not in completed.stdout:
            raise AssertionError(f"Generated-control modification was not surfaced:\n{completed.stdout}")
        if "STALE-HACK" not in workflow.read_text(encoding="utf-8"):
            raise AssertionError("Conflict path silently overwrote generated control")

        run_upgrade([str(target), "--apply", "--force-managed"], expect_success=True)
        if "STALE-HACK" in workflow.read_text(encoding="utf-8"):
            raise AssertionError("Forced generated-control regeneration did not replace stale content")
        manifest = manifest_payload(target)
        record = next(
            item for item in manifest["managed_assets"]
            if item["path"] == ".github/workflows/statedd-validate.yml"
        )
        if record["installed_sha256"] != hashlib.sha256(workflow.read_bytes()).hexdigest():
            raise AssertionError("Generated-control lock hash does not match installed content")
        second = run_upgrade([str(target), "--apply"], expect_success=True)
        if "Manifest update: no" not in second.stdout:
            raise AssertionError(f"Generated-control second run is not idempotent:\n{second.stdout}")


def main() -> int:
    tests = [
        test_dry_run_on_current_repo_refuses_template_root,
        test_dry_run_on_generated_repo_is_no_op_or_safe,
        test_dry_run_on_older_fixture_reports_missing_assets,
        test_apply_adds_safe_missing_assets,
        test_apply_preserves_readme_and_project_truth,
        test_conflict_fixture_refuses_unsafe_overwrite,
        test_force_managed_replaces_outdated_safe_asset,
        test_force_managed_never_overwrites_truth_files,
        test_upgrade_never_installs_template_tests_or_history,
        test_report_writes_json,
        test_report_reflects_dry_run_value,
        test_missing_manifest_fails_closed_without_explicit_profile,
        test_old_manifest_does_not_suppress_new_profile_asset,
        test_upgrade_rejects_symlinked_root_before_writes,
        test_nested_symlink_preflight_causes_zero_partial_writes,
        test_pristine_old_base_updates_without_force_but_local_change_conflicts,
        test_removed_asset_is_reported_retained_and_locked_as_retired,
        test_interrupted_apply_rolls_back_files_and_manifest,
        test_successful_apply_updates_manifest_and_second_run_is_idempotent,
        test_malformed_v2_top_level_and_history_fail_before_writes,
        test_profile_transition_is_rejected_until_semantic_migration_exists,
        test_reintroduced_retired_asset_recovers_ownership_and_is_not_still_retired,
        test_modified_generated_control_conflicts_then_force_regenerates_and_locks_hash,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
