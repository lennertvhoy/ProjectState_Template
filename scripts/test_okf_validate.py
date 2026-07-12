#!/usr/bin/env python3
"""Regression tests for the optional OKF v0.1 validator."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "statedd_okf_validate.py"


def run_validator(bundle: Path, source_root: Path, *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR), str(bundle), "--source-root", str(source_root), "--strict"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if (completed.returncode == 0) != expect_success:
        raise AssertionError(
            f"validator expectation failed: {expect_success=} returncode={completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def write_concept(bundle: Path, relative: str, frontmatter: str, body: str = "# Notes\n\nContent.\n") -> Path:
    path = bundle / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n\n{body}", encoding="utf-8")
    return path


def test_template_scaffold_passes() -> None:
    completed = run_validator(ROOT / "knowledge", ROOT, expect_success=True)
    assert "OKF v0.1 validation: passed" in completed.stdout


def test_unknown_type_broken_link_and_missing_index_are_permissive() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = root / "knowledge"
        bundle.mkdir()
        (bundle / "index.md").write_text("# Knowledge\n", encoding="utf-8")
        write_concept(
            bundle,
            "domain/thing.md",
            "type: VendorSpecificConcept\ntags: [one, two]\n",
            "See [future](missing.md).\n",
        )
        completed = run_validator(bundle, root, expect_success=True)
        assert "broken link target" in completed.stdout
        assert "no index.md" in completed.stdout


def test_root_and_nested_reserved_files_have_distinct_contracts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = root / "knowledge"
        bundle.mkdir()
        (bundle / "index.md").write_text(
            '---\nokf_version: "0.1"\n---\n\n# Knowledge\n', encoding="utf-8"
        )
        (bundle / "nested").mkdir()
        (bundle / "nested" / "index.md").write_text("---\ntype: Wrong\n---\n", encoding="utf-8")
        completed = run_validator(bundle, root, expect_success=False)
        assert "reserved index.md/log.md files must not contain frontmatter" in completed.stdout


def test_canonical_and_reference_governance_are_checked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = root / "knowledge"
        bundle.mkdir()
        (bundle / "index.md").write_text("# Knowledge\n", encoding="utf-8")
        write_concept(
            bundle,
            "domain/canonical.md",
            "type: BusinessRule\nstatedd:\n  authority: canonical\n  owner: product\n  reviewed_at: 2026-07-11T12:00:00Z\n",
        )
        write_concept(
            bundle,
            "references/external.md",
            "type: UnknownReference\nstatedd:\n  authority: reference\n  citations:\n    - https://example.com/source\n  last_checked_at: 2026-07-11T12:00:00Z\n",
        )
        run_validator(bundle, root, expect_success=True)


def test_derived_source_hash_is_validated_and_stale_sources_fail() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = root / "knowledge"
        bundle.mkdir()
        (bundle / "index.md").write_text("# Knowledge\n", encoding="utf-8")
        source = root / "schemas" / "metric.yaml"
        source.parent.mkdir()
        source.write_text("metric: active\n", encoding="utf-8")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        write_concept(
            bundle,
            "metrics/active.md",
            f"type: Metric\nstatedd:\n  authority: derived\n  sources:\n    - path: schemas/metric.yaml\n      sha256: {digest}\n",
        )
        run_validator(bundle, root, expect_success=True)
        source.write_text("metric: changed\n", encoding="utf-8")
        completed = run_validator(bundle, root, expect_success=False)
        assert "derived source is stale" in completed.stdout


def test_duplicate_keys_missing_type_and_unsafe_source_fail() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = root / "knowledge"
        bundle.mkdir()
        (bundle / "index.md").write_text("# Knowledge\n", encoding="utf-8")
        write_concept(bundle, "bad/duplicate.md", "type: One\ntype: Two\n")
        write_concept(bundle, "bad/no-type.md", "title: Missing\n")
        write_concept(
            bundle,
            "bad/traversal.md",
            "type: Derived\nstatedd:\n  authority: derived\n  sources:\n    - path: ../outside.yaml\n      sha256: " + "0" * 64 + "\n",
        )
        completed = run_validator(bundle, root, expect_success=False)
        assert "duplicate mapping key" in completed.stdout
        assert "requires a non-empty type" in completed.stdout
        assert "unsafe or unavailable derived source" in completed.stdout


def test_case_collision_local_path_and_secret_like_values_fail() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = root / "knowledge"
        bundle.mkdir()
        (bundle / "index.md").write_text("# Knowledge\n", encoding="utf-8")
        write_concept(bundle, "A.md", "type: A\n")
        write_concept(bundle, "a.md", "type: a\n")
        write_concept(bundle, "secret.md", "type: Secret\napi_key: 'not-a-real-secret-value'\n")
        write_concept(bundle, "local.md", "type: Local\npath: /home/example/project\n")
        completed = run_validator(bundle, root, expect_success=False)
        assert "case-colliding" in completed.stdout
        assert "secret-like" in completed.stdout
        assert "personal or machine-local" in completed.stdout


def test_symlinked_bundle_content_fails_closed_when_supported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = root / "knowledge"
        bundle.mkdir()
        (bundle / "index.md").write_text("# Knowledge\n", encoding="utf-8")
        outside = root / "outside.md"
        outside.write_text("---\ntype: Outside\n---\n", encoding="utf-8")
        try:
            os.symlink(outside, bundle / "escape.md")
        except (OSError, NotImplementedError):
            return
        completed = run_validator(bundle, root, expect_success=False)
        assert "symlink components" in completed.stdout


def test_json_report_is_machine_readable() -> None:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR), str(ROOT / "knowledge"), "--source-root", str(ROOT), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["okf_version"] == "0.1"
    assert payload["status"] == "passed"


def test_optional_module_is_explicit_and_profile_conformance_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ordinary = root / "ordinary"
        optional = root / "optional"
        init = ROOT / "scripts" / "init_template.py"
        for target, extra in ((ordinary, []), (optional, ["--asset-set", "knowledge_okf"])):
            completed = subprocess.run(
                [sys.executable, str(init), "new", "--name", "OKF Profile", "--target", str(target), "--profile", "minimal", "--no-init-git", *extra],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            assert completed.returncode == 0, completed.stderr
        assert not (ordinary / "knowledge").exists()
        assert (optional / "knowledge" / "index.md").is_file()
        manifest = json.loads((optional / "STATEDD_ASSETS.json").read_text(encoding="utf-8"))
        assert "knowledge_okf" in manifest["asset_sets"]
        gate = subprocess.run(
            [sys.executable, str(optional / "scripts" / "statedd_quality_gate.py"), "--root", str(optional), "--gate-level", "1", "--conformance"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert gate.returncode == 0, f"stdout:\n{gate.stdout}\nstderr:\n{gate.stderr}"
