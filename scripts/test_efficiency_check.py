#!/usr/bin/env python3
"""Tests for scripts/projectstate_efficiency_check.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = ROOT / "scripts" / "projectstate_efficiency_check.py"


def run_check(args: list[str], *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), *args],
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


def write_budget(root: Path, **overrides: int) -> None:
    defaults = {
        "schema": "projectstate.efficiency_budget.v1",
        "instruction_budgets": {
            "root_agents_max_lines": 100,
            "nested_agents_max_lines": 80,
            "skill_max_lines": 180,
            "command_max_lines": 120,
            "prompt_max_lines": 250,
            "duplicate_instruction_max_lines": 5,
            "max_steps_per_workflow": 8,
        },
        "state_budgets": {"active_next_actions_max": 5, "active_backlog_items_max": 12},
        "evidence_budgets": {"default_max_files": 5},
        "anti_bloat_rules": {
            "no_duplicate_instruction_files": True,
            "no_unreferenced_skills": True,
            "no_full_repo_audit_for_single_file_edit": True,
        },
    }
    section_map = {
        "active_next_actions_max": "state_budgets",
        "active_backlog_items_max": "state_budgets",
        "default_max_files": "evidence_budgets",
        "docs_only_max_files": "evidence_budgets",
        "runtime_change_min_files": "evidence_budgets",
        "runtime_change_max_files": "evidence_budgets",
    }
    for key, value in overrides.items():
        if "." in key:
            section, sub = key.split(".", 1)
            defaults[section][sub] = value  # type: ignore[index]
        elif key in section_map:
            defaults[section_map[key]][key] = value  # type: ignore[index]
        else:
            defaults["instruction_budgets"][key] = value  # type: ignore[index]
    import yaml

    (root / "EFFICIENCY_BUDGET.yaml").write_text(yaml.safe_dump(defaults), encoding="utf-8")


def add_context_budget(root: Path, *, max_startup_bytes: int) -> None:
    import yaml

    path = root / "EFFICIENCY_BUDGET.yaml"
    budget = yaml.safe_load(path.read_text(encoding="utf-8"))
    budget["context_budgets"] = {
        "token_estimator": "utf8_bytes_div_4_ceiling",
        "startup_files": ["AGENTS.md", "STATUS.md"],
        "profiles": {
            "minimal": {
                "max_startup_files": 2,
                "max_startup_bytes": max_startup_bytes,
                "max_startup_estimated_tokens": 100,
                "max_footprint_files": 10,
                "max_footprint_bytes": 10000,
            }
        },
    }
    path.write_text(yaml.safe_dump(budget), encoding="utf-8")


def write_minimal_context_fixture(root: Path) -> None:
    (root / "AGENTS.md").write_text("short\n", encoding="utf-8")
    (root / "STATUS.md").write_text("short\n", encoding="utf-8")
    (root / "PROJECT_STATE.yaml").write_text(
        "workflow:\n  repo_role: downstream_project\n"
        "current_state:\n  project:\n    profile: minimal\n",
        encoding="utf-8",
    )
    assets = ["AGENTS.md", "STATUS.md", "PROJECT_STATE.yaml", "PROJECTSTATE_ASSETS.json"]
    (root / "PROJECTSTATE_ASSETS.json").write_text(
        json.dumps(
            {
                "schema": "projectstate.runtime_assets.v1",
                "generation_mode": "new",
                "profile": "minimal",
                "assets": assets,
            }
        ),
        encoding="utf-8",
    )


def test_oversized_root_agents_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, root_agents_max_lines=5)
        (root / "AGENTS.md").write_text("line\n" * 10, encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_oversized_skill_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, skill_max_lines=5)
        skill = root / "skills" / "big" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "---\nname: big\ngate_level: 1\n---\n\n" + "line\n" * 10,
            encoding="utf-8",
        )
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_missing_gate_level_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        skill = root / "skills" / "nogate" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: nogate\n---\n\nstep_by_step:\n  - name: do thing\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_full_gate_at_level_one_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        skill = root / "skills" / "heavy" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "---\nname: heavy\ngate_level: 1\n---\n\nRun the full pipeline here.\n",
            encoding="utf-8",
        )
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_too_many_steps_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, max_steps_per_workflow=2)
        skill = root / "skills" / "long" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        steps = "\n".join([f"  - name: step {i}" for i in range(5)])
        skill.write_text(
            f"---\nname: long\ngate_level: 2\n---\n\nstep_by_step:\n{steps}\n",
            encoding="utf-8",
        )
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_duplicate_instructions_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        lines = "\n".join(
            [f"This is duplicated canonical instruction number {i} that appears in every shim file." for i in range(8)]
        )
        (root / "AGENTS.md").write_text(lines + "\n", encoding="utf-8")
        (root / "CLAUDE.md").write_text(lines + "\n", encoding="utf-8")
        (root / "GEMINI.md").write_text(lines + "\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_active_queue_too_long_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, active_next_actions_max=2)
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        items = "\n".join([f"### P{i} [BL-{i:03d}] item" for i in range(1, 5)])
        (root / "NEXT_ACTIONS.md").write_text(f"## Active Work\n\n{items}\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_evidence_bundle_too_large_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, default_max_files=2)
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        evidence = root / "docs" / "evidence" / "2026-06-28-test"
        evidence.mkdir(parents=True)
        for i in range(5):
            (evidence / f"a{i}.txt").write_text("x", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_bloat_fixture_fails() -> None:
    fixture = ROOT / "fixtures" / "efficiency_bloat_overcorrection"
    completed = run_check(["--root", str(fixture)], expect_success=False)
    stdout = completed.stdout
    assert "instruction_size" in stdout or "workflow_gate_level" in stdout
    assert "active_queue" in stdout or "evidence_bundle" in stdout


def test_clean_repo_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=True)


def test_context_metrics_are_reported_and_enforced() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        add_context_budget(root, max_startup_bytes=20)
        write_minimal_context_fixture(root)
        completed = run_check(["--root", str(root)], expect_success=True)
        for phrase in ("startup_estimated_tokens", "footprint_files", "footprint_bytes"):
            if phrase not in completed.stdout:
                raise AssertionError(f"Missing context metric {phrase}:\n{completed.stdout}")

        add_context_budget(root, max_startup_bytes=1)
        completed = run_check(["--root", str(root)], expect_success=False)
        if "startup_bytes" not in completed.stdout:
            raise AssertionError(f"Expected startup byte budget failure:\n{completed.stdout}")


def test_duplicate_budget_key_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        budget = root / "EFFICIENCY_BUDGET.yaml"
        budget.write_text(budget.read_text(encoding="utf-8") + "\nschema: duplicate\n", encoding="utf-8")
        completed = run_check(["--root", str(root)], expect_success=False)
        if "duplicate mapping key 'schema'" not in completed.stdout:
            raise AssertionError(f"Expected duplicate YAML key failure:\n{completed.stdout}")


def test_context_footprint_rejects_manifest_asset_through_symlink_parent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "root"
        outside = Path(tmp) / "outside"
        root.mkdir()
        outside.mkdir()
        write_budget(root)
        add_context_budget(root, max_startup_bytes=20)
        write_minimal_context_fixture(root)
        (outside / "secret.txt").write_text("private\n", encoding="utf-8")
        os.symlink(outside, root / "linked")
        manifest = json.loads((root / "PROJECTSTATE_ASSETS.json").read_text(encoding="utf-8"))
        manifest["assets"].append("linked/secret.txt")
        (root / "PROJECTSTATE_ASSETS.json").write_text(json.dumps(manifest), encoding="utf-8")
        completed = run_check(["--root", str(root)], expect_success=False)
        if "symlink" not in completed.stdout.lower():
            raise AssertionError(f"Symlinked manifest asset was not rejected:\n{completed.stdout}")


def test_evidence_budget_selects_active_slice_not_mutable_mtime() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, default_max_files=2)
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        context = root / ".projectstate" / "agent.context"
        context.parent.mkdir()
        context.write_text(json.dumps({"slice_id": "BL-ACTIVE"}), encoding="utf-8")
        active = root / "docs" / "evidence" / "2026-01-01-active"
        active.mkdir(parents=True)
        (active / "manifest.json").write_text(
            json.dumps({"slice_id": "BL-ACTIVE"}), encoding="utf-8"
        )
        for index in range(4):
            (active / f"artifact-{index}.txt").write_text("x\n", encoding="utf-8")
        decoy = root / "docs" / "evidence" / "9999-12-31-small"
        decoy.mkdir()
        (decoy / "manifest.json").write_text(
            json.dumps({"slice_id": "BL-DECOY"}), encoding="utf-8"
        )
        os.utime(decoy, None)
        completed = run_check(["--root", str(root)], expect_success=False)
        if "2026-01-01-active" not in completed.stdout:
            raise AssertionError(f"Evidence budget did not bind active slice:\n{completed.stdout}")


if __name__ == "__main__":
    tests = [
        test_oversized_root_agents_fails,
        test_oversized_skill_fails,
        test_missing_gate_level_fails,
        test_full_gate_at_level_one_fails,
        test_too_many_steps_fails,
        test_duplicate_instructions_fails,
        test_active_queue_too_long_fails,
        test_evidence_bundle_too_large_fails,
        test_bloat_fixture_fails,
        test_clean_repo_passes,
        test_context_metrics_are_reported_and_enforced,
        test_duplicate_budget_key_fails,
    ]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
