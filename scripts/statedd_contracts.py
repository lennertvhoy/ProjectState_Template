#!/usr/bin/env python3
"""Shared strict-contract and path-confinement primitives for StateDD.

This is a library, not a CLI. StateDD-controlled JSON must reject duplicate
keys and non-finite numbers. Repository-controlled relative paths must use
portable POSIX syntax and must never cross or traverse symlink components.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


class ContractError(ValueError):
    """Raised when a StateDD-controlled contract is malformed or unsafe."""


class UnsafePathError(ContractError):
    """Raised when a requested path can escape its declared root."""


# Catalog validation IDs are executable/presence contracts, not descriptive
# labels. Generated-profile quality gates dispatch every resolved ID here.
VALIDATION_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "quality_gate_level_1": {
        "minimum_gate_level": 1,
        "required_paths": ("scripts/statedd_quality_gate.py",),
    },
    "git_safety_contract": {
        "minimum_gate_level": 1,
        "required_paths": (
            "scripts/statedd_git_safety_check.py",
            "scripts/statedd_git_safety_session.py",
            "schemas/git_safety_report.schema.json",
        ),
    },
    "bootstrap_contract": {
        "minimum_gate_level": 1,
        "required_paths": (
            "scripts/statedd_bootstrap_apply.py",
            "schemas/bootstrap_answers.schema.json",
        ),
    },
    "runtime_contracts": {
        "required_paths": (
            "scripts/statedd_runtime_proof.py",
            "scripts/statedd_runtime_truth_check.py",
            "schemas/runtime_identity.schema.json",
            "schemas/runtime_identity_v2.schema.json",
        ),
    },
    "evidence_contracts": {
        "required_paths": (
            "scripts/statedd_evidence_pack.py",
            "schemas/evidence_manifest.schema.json",
        ),
    },
    "remote_closure_contract": {
        "required_paths": ("scripts/statedd_remote_closure_finalizer.py",),
    },
    "finish_slice_contract": {
        "required_paths": (
            "scripts/statedd_finish_slice.py",
            "scripts/statedd_post_merge_verify.py",
            "schemas/finish_slice_handoff.schema.json",
            "schemas/isolation_release.schema.json",
        ),
    },
    "worktree_contract": {
        "required_paths": (
            "scripts/statedd_worktree_guard.py",
            "scripts/statedd_agent_worktree.py",
            "scripts/statedd_workspace_inventory.py",
        ),
    },
    "quality_gate_level_2": {
        "minimum_gate_level": 2,
        "required_paths": (
            "scripts/statedd_quality_gate.py",
            "scripts/statedd_evidence_pack.py",
        ),
    },
    "post_merge_contract": {
        "required_paths": ("scripts/statedd_post_merge_verify.py",),
    },
    "github_asset_presence": {
        "required_paths": (
            ".github/pull_request_template.md",
            ".github/ISSUE_TEMPLATE/config.yml",
            ".github/ISSUE_TEMPLATE/bootstrap-init.md",
            ".github/ISSUE_TEMPLATE/bug-regression.md",
            ".github/ISSUE_TEMPLATE/backlog-item.md",
            ".github/ISSUE_TEMPLATE/architecture-change.md",
        ),
    },
    "okf_v0_1_conformance": {
        "minimum_gate_level": 1,
        "required_paths": (
            "scripts/statedd_okf_validate.py",
            "schemas/statedd_okf_extension.schema.json",
            "knowledge/index.md",
        ),
    },
}


def _require_exact_fields(
    value: Any,
    *,
    field: str,
    required: set[str],
    optional: set[str] = frozenset(),
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{field} must be an object")
    keys = set(value)
    missing = required - keys
    unknown = keys - required - optional
    if missing:
        raise ContractError(f"{field} is missing required fields: {sorted(missing)}")
    if unknown:
        raise ContractError(f"{field} contains unknown fields: {sorted(unknown)}")
    return value


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ContractError(f"{field} must be a positive integer")
    return value


@dataclass(frozen=True)
class ResolvedProfile:
    """Validated, dependency-expanded profile definition."""

    profile: str
    profile_dependencies: tuple[str, ...]
    asset_sets: tuple[str, ...]
    assets: tuple[Path, ...]
    capabilities: tuple[str, ...]
    validations: tuple[str, ...]
    required_gate_level: int


def _reject_duplicate_pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise ContractError(f"non-finite JSON number {value!r} is not allowed")


def strict_json_loads(text: str) -> Any:
    """Parse standards-compliant JSON without last-key-wins behavior."""
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_non_finite,
        )
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON: {exc}") from exc


def load_json_file(path: Path) -> Any:
    """Read and strictly parse a UTF-8 JSON contract."""
    try:
        return strict_json_loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise ContractError(f"could not read JSON contract {path}: {exc}") from exc


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ContractError(f"{field} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ContractError(f"{field} contains duplicate values")
    return value


def load_profile_catalog(root: Path) -> dict[str, Any]:
    """Load and semantically validate the single profile/asset-set authority."""
    path = root / "profiles" / "catalog.json"
    payload = load_json_file(path)
    payload = _require_exact_fields(
        payload,
        field="profile catalog",
        required={
            "schema",
            "catalog_version",
            "template_version",
            "asset_sets",
            "profiles",
            "lifecycle_defaults",
        },
    )
    if payload.get("schema") != "statedd.profile_catalog.v1":
        raise ContractError("profiles/catalog.json has an unsupported schema")
    _positive_int(payload.get("catalog_version"), "profile catalog catalog_version")
    if not isinstance(payload.get("template_version"), str) or not payload["template_version"]:
        raise ContractError("profile catalog template_version must be a non-empty string")
    asset_sets = payload.get("asset_sets")
    profiles = payload.get("profiles")
    lifecycle = payload.get("lifecycle_defaults")
    if not isinstance(asset_sets, dict) or not asset_sets:
        raise ContractError("profile catalog asset_sets must be a non-empty object")
    if not isinstance(profiles, dict) or not profiles:
        raise ContractError("profile catalog profiles must be a non-empty object")
    if not isinstance(lifecycle, dict) or not lifecycle:
        raise ContractError("profile catalog lifecycle_defaults must be a non-empty object")

    required_lifecycle = {"template_asset", "project_truth", "append_only", "generated"}
    missing_lifecycle = required_lifecycle - set(lifecycle)
    if missing_lifecycle:
        raise ContractError(
            f"profile catalog lifecycle_defaults is missing classes: {sorted(missing_lifecycle)}"
        )
    lifecycle_fields = {
        "role",
        "owner",
        "required",
        "provision",
        "merge_strategy",
        "sensitivity",
        "protected",
        "append_only",
    }
    for lifecycle_id, raw_definition in lifecycle.items():
        if not isinstance(lifecycle_id, str) or not lifecycle_id:
            raise ContractError("lifecycle class IDs must be non-empty strings")
        definition = _require_exact_fields(
            raw_definition,
            field=f"lifecycle_defaults.{lifecycle_id}",
            required=lifecycle_fields,
        )
        for name in ("role", "provision"):
            if not isinstance(definition[name], str) or not definition[name]:
                raise ContractError(f"lifecycle_defaults.{lifecycle_id}.{name} must be non-empty")
        if definition["owner"] not in {"template", "project"}:
            raise ContractError(f"lifecycle_defaults.{lifecycle_id}.owner is invalid")
        if definition["merge_strategy"] not in {
            "preserve",
            "append-only",
            "create-if-missing",
            "replace-if-unmodified",
            "regenerate",
            "forbid",
        }:
            raise ContractError(f"lifecycle_defaults.{lifecycle_id}.merge_strategy is invalid")
        if definition["sensitivity"] not in {"public", "project", "sensitive"}:
            raise ContractError(f"lifecycle_defaults.{lifecycle_id}.sensitivity is invalid")
        for name in ("required", "protected", "append_only"):
            if not isinstance(definition[name], bool):
                raise ContractError(f"lifecycle_defaults.{lifecycle_id}.{name} must be boolean")
    lifecycle_invariants = {
        "template_asset": {
            "role": "workflow_asset",
            "owner": "template",
            "provision": "copy",
            "merge_strategy": "replace-if-unmodified",
            "protected": False,
            "append_only": False,
        },
        "project_truth": {
            "role": "project_truth",
            "owner": "project",
            "provision": "generate-or-preserve",
            "merge_strategy": "preserve",
            "protected": True,
            "append_only": False,
        },
        "append_only": {
            "role": "project_history",
            "owner": "project",
            "provision": "create-if-missing",
            "merge_strategy": "append-only",
            "protected": True,
            "append_only": True,
        },
        "generated": {
            "role": "generated_control",
            "owner": "template",
            "provision": "regenerate",
            "merge_strategy": "regenerate",
            "protected": True,
            "append_only": False,
        },
    }
    for lifecycle_id, expected in lifecycle_invariants.items():
        actual = lifecycle[lifecycle_id]
        mismatches = {
            key: (actual.get(key), value)
            for key, value in expected.items()
            if actual.get(key) != value
        }
        if mismatches:
            raise ContractError(
                f"lifecycle_defaults.{lifecycle_id} violates ownership semantics: {mismatches}"
            )

    all_paths: dict[Path, str] = {}
    for set_id, definition in asset_sets.items():
        if not isinstance(set_id, str) or not set_id or not isinstance(definition, dict):
            raise ContractError("asset set IDs and definitions must be strings and objects")
        definition = _require_exact_fields(
            definition,
            field=f"asset_sets.{set_id}",
            required={
                "version",
                "depends_on",
                "conflicts_with",
                "capabilities",
                "validation",
                "assets",
            },
            optional={"optional"},
        )
        _positive_int(definition["version"], f"asset_sets.{set_id}.version")
        if "optional" in definition and not isinstance(definition["optional"], bool):
            raise ContractError(f"asset_sets.{set_id}.optional must be boolean")
        for field in ("depends_on", "conflicts_with", "capabilities", "validation", "assets"):
            values = _string_list(definition.get(field), f"asset_sets.{set_id}.{field}")
            if field == "validation":
                unknown_validations = set(values) - set(VALIDATION_REQUIREMENTS)
                if unknown_validations:
                    raise ContractError(
                        f"asset_sets.{set_id}.validation contains unknown IDs: "
                        f"{sorted(unknown_validations)}"
                    )
            if field == "assets":
                for raw in values:
                    rel = normalize_relative_path(raw)
                    previous = all_paths.get(rel)
                    if previous is not None:
                        raise ContractError(f"asset {raw!r} is owned by both {previous!r} and {set_id!r}")
                    all_paths[rel] = set_id
        for dependency in definition["depends_on"]:
            if dependency not in asset_sets:
                raise ContractError(f"asset set {set_id!r} depends on unknown set {dependency!r}")
        for conflict in definition["conflicts_with"]:
            if conflict not in asset_sets:
                raise ContractError(f"asset set {set_id!r} conflicts with unknown set {conflict!r}")

    def visit_set(set_id: str, active: tuple[str, ...]) -> None:
        if set_id in active:
            raise ContractError(f"asset-set dependency cycle: {' -> '.join((*active, set_id))}")
        for dependency in asset_sets[set_id]["depends_on"]:
            visit_set(dependency, (*active, set_id))

    for set_id in asset_sets:
        visit_set(set_id, ())

    def visit_profile(profile: str, active: tuple[str, ...]) -> None:
        if profile in active:
            raise ContractError(f"profile dependency cycle: {' -> '.join((*active, profile))}")
        definition = _require_exact_fields(
            profiles[profile],
            field=f"profiles.{profile}",
            required={
                "depends_on",
                "asset_sets",
                "required_capabilities",
                "required_gate_level",
            },
        )
        dependencies = _string_list(definition.get("depends_on"), f"profiles.{profile}.depends_on")
        _string_list(definition.get("asset_sets"), f"profiles.{profile}.asset_sets")
        _string_list(
            definition.get("required_capabilities"),
            f"profiles.{profile}.required_capabilities",
        )
        gate_level = definition.get("required_gate_level")
        if isinstance(gate_level, bool) or not isinstance(gate_level, int) or gate_level not in {0, 1, 2, 3}:
            raise ContractError(f"profiles.{profile}.required_gate_level must be 0..3")
        for dependency in dependencies:
            if dependency not in profiles:
                raise ContractError(f"profile {profile!r} depends on unknown profile {dependency!r}")
            visit_profile(dependency, (*active, profile))
        for set_id in definition["asset_sets"]:
            if set_id not in asset_sets:
                raise ContractError(f"profile {profile!r} references unknown asset set {set_id!r}")

    for profile in profiles:
        if not isinstance(profile, str) or not profile:
            raise ContractError("profile IDs must be non-empty strings")
        visit_profile(profile, ())
    return payload


def resolve_profile(
    catalog: dict[str, Any],
    profile: str,
    *,
    optional_asset_sets: Iterable[str] = (),
) -> ResolvedProfile:
    """Expand profile and asset-set dependencies with deterministic output."""
    profiles = catalog["profiles"]
    asset_sets = catalog["asset_sets"]
    if profile not in profiles:
        raise ContractError(f"unknown profile {profile!r}")

    resolved_profiles: set[str] = set()
    resolved_sets: set[str] = set()

    def add_set(set_id: str) -> None:
        for dependency in asset_sets[set_id]["depends_on"]:
            add_set(dependency)
        resolved_sets.add(set_id)

    def add_profile(profile_id: str) -> None:
        for dependency in profiles[profile_id]["depends_on"]:
            add_profile(dependency)
        for set_id in profiles[profile_id]["asset_sets"]:
            add_set(set_id)
        resolved_profiles.add(profile_id)

    add_profile(profile)
    for set_id in optional_asset_sets:
        if set_id not in asset_sets or asset_sets[set_id].get("optional") is not True:
            raise ContractError(f"unknown or non-optional asset set {set_id!r}")
        add_set(set_id)

    for set_id in resolved_sets:
        conflicts = set(asset_sets[set_id]["conflicts_with"]) & resolved_sets
        if conflicts:
            raise ContractError(f"asset set {set_id!r} conflicts with {sorted(conflicts)}")

    assets = sorted(
        {
            normalize_relative_path(raw)
            for set_id in resolved_sets
            for raw in asset_sets[set_id]["assets"]
        },
        key=lambda path: path.as_posix(),
    )
    capabilities = sorted(
        {
            capability
            for set_id in resolved_sets
            for capability in asset_sets[set_id]["capabilities"]
        }
    )
    validations = sorted(
        {
            validation
            for set_id in resolved_sets
            for validation in asset_sets[set_id]["validation"]
        }
    )
    required = {
        capability
        for profile_id in resolved_profiles
        for capability in profiles[profile_id]["required_capabilities"]
    }
    missing = required - set(capabilities)
    if missing:
        raise ContractError(f"profile {profile!r} is missing required capabilities: {sorted(missing)}")
    return ResolvedProfile(
        profile=profile,
        profile_dependencies=tuple(sorted(resolved_profiles - {profile})),
        asset_sets=tuple(sorted(resolved_sets)),
        assets=tuple(assets),
        capabilities=tuple(capabilities),
        validations=tuple(validations),
        required_gate_level=max(
            profiles[profile_id]["required_gate_level"]
            for profile_id in resolved_profiles
        ),
    )


def normalize_relative_path(value: str | Path) -> Path:
    """Return a portable managed path or fail before filesystem access."""
    raw = value.as_posix() if isinstance(value, Path) else value
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise UnsafePathError(f"unsafe relative path: {value!r}")
    if "\\" in raw:
        raise UnsafePathError(f"managed paths must use POSIX separators: {raw!r}")
    if raw.startswith("/") or PureWindowsPath(raw).drive:
        raise UnsafePathError(f"absolute managed path is not allowed: {raw!r}")
    raw_parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise UnsafePathError(f"traversal or non-normalized managed path: {raw!r}")
    normalized = PurePosixPath(raw)
    if normalized.is_absolute() or normalized.as_posix() != raw:
        raise UnsafePathError(f"non-normalized managed path: {raw!r}")
    return Path(*normalized.parts)


def _absolute_without_traversal(value: str | Path, *, cwd: Path | None = None) -> Path:
    raw_text = os.fspath(value)
    if os.name != "nt" and ("\\" in raw_text or PureWindowsPath(raw_text).drive):
        raise UnsafePathError(f"foreign Windows target root is not allowed: {value}")
    raw = Path(value)
    if ".." in raw.parts:
        raise UnsafePathError(f"target root traversal is not allowed: {value}")
    if not raw.is_absolute():
        raw = (cwd or Path.cwd()) / raw
    return Path(os.path.abspath(raw))


def reject_symlink_components(path: Path, *, label: str = "path") -> None:
    """Reject every existing symlink component, including the final path."""
    absolute = path if path.is_absolute() else _absolute_without_traversal(path)
    anchor = Path(absolute.anchor)
    current = anchor
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise UnsafePathError(f"refusing symlink component in {label}: {current}")


def safe_root_path(
    value: str | Path,
    *,
    must_exist: bool,
    cwd: Path | None = None,
) -> Path:
    """Validate the requested root before returning its canonical path."""
    requested = _absolute_without_traversal(value, cwd=cwd)
    reject_symlink_components(requested, label="target root")
    canonical = requested.resolve(strict=False)
    if must_exist and (not canonical.exists() or not canonical.is_dir()):
        raise UnsafePathError(f"target root is not an existing directory: {requested}")
    if canonical.exists() and not canonical.is_dir():
        raise UnsafePathError(f"target root is not a directory: {requested}")
    return canonical


def confined_path(root: Path, relpath: str | Path) -> Path:
    """Build a lexically confined path and reject existing symlink components."""
    normalized = normalize_relative_path(relpath)
    canonical_root = root.resolve(strict=False)
    reject_symlink_components(canonical_root, label="configured root")
    candidate = canonical_root / normalized
    try:
        candidate.relative_to(canonical_root)
    except ValueError as exc:  # defensive: normalize_relative_path already blocks this
        raise UnsafePathError(f"path escapes configured root: {relpath}") from exc
    reject_symlink_components(candidate, label="managed path")
    return candidate


def regular_source_path(root: Path, relpath: str | Path) -> Path:
    """Return a confined regular source file without following source symlinks."""
    source = confined_path(root, relpath)
    if source.is_symlink() or not source.is_file():
        raise UnsafePathError(f"source is not a regular file: {relpath}")
    return source
