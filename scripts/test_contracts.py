#!/usr/bin/env python3
"""Regression tests for shared ProjectState contract primitives."""

from __future__ import annotations

import os
import copy
import json
import tempfile
from pathlib import Path

import pytest

try:
    from projectstate_contracts import (
        ContractError,
        UnsafePathError,
        confined_path,
        load_profile_catalog,
        normalize_relative_path,
        resolve_profile,
        safe_root_path,
        strict_json_loads,
    )
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.projectstate_contracts import (
        ContractError,
        UnsafePathError,
        confined_path,
        load_profile_catalog,
        normalize_relative_path,
        resolve_profile,
        safe_root_path,
        strict_json_loads,
    )


def test_strict_json_rejects_duplicate_keys_and_non_finite_numbers() -> None:
    with pytest.raises(ContractError, match="duplicate JSON key 'assets'"):
        strict_json_loads('{"assets": [], "assets": ["VERSION"]}')
    with pytest.raises(ContractError, match="non-finite"):
        strict_json_loads('{"value": NaN}')


@pytest.mark.parametrize(
    "raw",
    ["/absolute", "../escape", "a/../escape", "a//b", "./a", "C:\\escape", "a\\b"],
)
def test_normalize_relative_path_rejects_nonportable_or_unsafe_paths(raw: str) -> None:
    with pytest.raises(UnsafePathError):
        normalize_relative_path(raw)


def test_safe_root_rejects_root_and_parent_symlinks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        actual = base / "actual"
        actual.mkdir()
        root_link = base / "root-link"
        os.symlink(actual, root_link)
        with pytest.raises(UnsafePathError, match="symlink"):
            safe_root_path(root_link, must_exist=True)

        parent_link = base / "parent-link"
        os.symlink(actual, parent_link)
        with pytest.raises(UnsafePathError, match="symlink"):
            safe_root_path(parent_link / "new-root", must_exist=False)


def test_confined_path_rejects_nested_symlink_even_when_referent_is_inside() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        real = root / "real"
        real.mkdir()
        os.symlink(real, root / "linked")
        with pytest.raises(UnsafePathError, match="symlink"):
            confined_path(root, "linked/file.txt")


def test_profile_catalog_expands_dependencies_and_enforces_capabilities() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog = load_profile_catalog(root)
    minimal = resolve_profile(catalog, "minimal")
    team = resolve_profile(catalog, "team")
    regulated = resolve_profile(catalog, "regulated")
    assert set(minimal.assets) < set(regulated.assets)
    assert regulated.profile_dependencies == ("minimal", "solo", "team")
    assert regulated.asset_sets == ("collaboration", "core", "proof", "regulated_controls")
    assert regulated.required_gate_level == 2
    assert "post_merge_verification" in regulated.capabilities
    assert "agent_owned_remote_closure" in team.capabilities
    assert Path("scripts/projectstate_finish_slice.py") in team.assets
    assert Path("scripts/projectstate_post_merge_verify.py") in team.assets
    assert "finish_slice_contract" in team.validations
    assert "quality_gate_level_1" in regulated.validations
    assert "quality_gate_level_2" in regulated.validations

    catalog["profiles"]["minimal"]["required_gate_level"] = 3
    assert resolve_profile(catalog, "regulated").required_gate_level == 3


def test_profile_catalog_rejects_missing_dependency() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog = load_profile_catalog(root)
    catalog["asset_sets"]["core"]["depends_on"] = ["missing"]
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "profiles").mkdir()
        import json

        (target / "profiles" / "catalog.json").write_text(
            json.dumps(catalog), encoding="utf-8"
        )
        with pytest.raises(ContractError, match="unknown set"):
            load_profile_catalog(target)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda catalog: catalog["asset_sets"]["core"].update({"version": "bogus"}),
        lambda catalog: catalog["asset_sets"]["core"].update({"unexpected": True}),
        lambda catalog: catalog["asset_sets"]["core"]["validation"].append("unknown_check"),
        lambda catalog: catalog["profiles"]["minimal"].update({"required_gate_level": True}),
        lambda catalog: catalog["lifecycle_defaults"]["template_asset"].update(
            {"owner": "project", "merge_strategy": "preserve", "protected": True}
        ),
    ],
)
def test_profile_catalog_rejects_schema_valid_and_semantic_corruption(mutate) -> None:
    root = Path(__file__).resolve().parents[1]
    catalog = copy.deepcopy(load_profile_catalog(root))
    mutate(catalog)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "profiles").mkdir()
        (target / "profiles" / "catalog.json").write_text(
            json.dumps(catalog), encoding="utf-8"
        )
        with pytest.raises(ContractError):
            load_profile_catalog(target)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
