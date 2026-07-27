#!/usr/bin/env python3
"""Plan and transactionally apply safe ProjectState downstream asset upgrades.

The current profile catalog is desired-state authority. A validated historical
PROJECTSTATE_ASSETS.json supplies ownership and base-hash evidence. Default mode is
dry-run; ambiguity causes zero writes. Removed assets are reported, never
deleted. Project truth is preserved.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from projectstate_contracts import (
        ContractError,
        ResolvedProfile,
        UnsafePathError,
        confined_path,
        load_json_file,
        load_profile_catalog,
        normalize_relative_path,
        regular_source_path,
        resolve_assets_manifest,
        resolve_profile,
        safe_root_path,
    )
    from projectstate_validate_schema import load_schema as load_json_schema_contract, validate_json_schema
    from projectstate_generated_controls import render_coding_agent_startup_prompt, render_downstream_workflow
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.projectstate_contracts import (
        ContractError,
        ResolvedProfile,
        UnsafePathError,
        confined_path,
        load_json_file,
        load_profile_catalog,
        normalize_relative_path,
        regular_source_path,
        resolve_assets_manifest,
        resolve_profile,
        safe_root_path,
    )
    from scripts.projectstate_validate_schema import load_schema as load_json_schema_contract, validate_json_schema
    from scripts.projectstate_generated_controls import render_coding_agent_startup_prompt, render_downstream_workflow


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path("PROJECTSTATE_ASSETS.json")
PROJECT_TRUTH_FILES = {
    Path("AGENTS.md"),
    Path("STATUS.md"),
    Path("PROJECT_STATE.yaml"),
    Path("PROJECT_DNA.yaml"),
    Path("PROJECT_ADAPTER.yaml"),
    Path("NEXT_ACTIONS.md"),
    Path("BACKLOG.md"),
    Path("README.md"),
}
APPEND_ONLY_FILES = {
    Path("WORKLOG.md"),
    Path("docs/EVIDENCE_LOG.md"),
    Path("docs/ACCEPTANCE_FREEZES.md"),
}
EXCLUDED_CLASSES = [
    "template_tests",
    "fixtures",
    "template_evidence",
    "incident_history",
    "release_history",
    "maintenance_changelog",
]
HASH_PATTERN_LENGTH = 64
GENERATED_CONTROL_PATHS = {
    Path(".github/workflows/projectstate-validate.yml"),
    Path("prompts/CODING_AGENT_STARTUP_PROMPT.md"),
}


@dataclass
class ManifestState:
    schema: str | None
    template_version: str | None
    profile: str
    generation_mode: str
    raw: dict[str, Any] | None
    template_records: dict[Path, dict[str, Any]]
    generated_records: dict[Path, dict[str, Any]]
    protected_records: dict[Path, dict[str, Any]]
    retired_assets: list[dict[str, Any]]
    upgrade_history: list[dict[str, Any]]
    optional_asset_sets: set[str]
    manifest_sha256: str | None


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_version(root: Path) -> str | None:
    path = root / "VERSION"
    if not path.is_file() or path.is_symlink():
        return None
    try:
        return path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        return None


def git_head(root: Path) -> str | None:
    import subprocess

    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        if status.stdout.strip():
            return None
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def _valid_hash(value: Any, *, nullable: bool = True) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or len(value) != HASH_PATTERN_LENGTH:
        raise ContractError("asset hashes must be 64 lowercase hexadecimal characters or null")
    if any(char not in "0123456789abcdef" for char in value):
        raise ContractError("asset hashes must be 64 lowercase hexadecimal characters or null")
    return value


def _legacy_record(path: Path, *, owner: str) -> dict[str, Any]:
    if path in APPEND_ONLY_FILES:
        role = "project_history"
        provision = "create-if-missing"
        strategy = "append-only"
        protected = True
        append_only = True
    elif owner == "project":
        role = "project_truth"
        provision = "generate-or-preserve"
        strategy = "preserve"
        protected = True
        append_only = False
    else:
        role = "workflow_asset"
        provision = "copy"
        strategy = "replace-if-unmodified"
        protected = False
        append_only = False
    return {
        "path": path.as_posix(),
        "role": role,
        "owner": owner,
        "required": True,
        "provision": provision,
        "merge_strategy": strategy,
        "schema": None,
        "generated_by": "legacy-manifest",
        "sensitivity": "project" if owner == "project" else "public",
        "protected": protected,
        "append_only": append_only,
        "desired_by": ["legacy-manifest"],
        "base_sha256": None,
        "installed_sha256": None,
    }


def _validate_v2_payload(payload: dict[str, Any], *, label: str) -> None:
    schema = load_json_schema_contract(TEMPLATE_ROOT / "schemas" / "projectstate_assets.schema.json")
    issues = validate_json_schema(payload, schema)
    if issues:
        detail = "; ".join(f"{issue.path}: {issue.message}" for issue in issues[:12])
        raise ContractError(f"{label} violates projectstate.runtime_assets.v2: {detail}")


def _validate_v2_record(record: Any, index: int) -> tuple[Path, dict[str, Any]]:
    if not isinstance(record, dict):
        raise ContractError(f"managed_assets[{index}] must be an object")
    required = {
        "path",
        "role",
        "owner",
        "required",
        "provision",
        "merge_strategy",
        "schema",
        "generated_by",
        "sensitivity",
        "protected",
        "append_only",
        "desired_by",
        "base_sha256",
        "installed_sha256",
    }
    if set(record) != required:
        raise ContractError(
            f"managed_assets[{index}] fields differ from the v2 contract: "
            f"missing={sorted(required - set(record))}, extra={sorted(set(record) - required)}"
        )
    path = normalize_relative_path(record["path"])
    if record["owner"] not in {"template", "project"}:
        raise ContractError(f"managed_assets[{index}].owner is invalid")
    if record["merge_strategy"] not in {
        "preserve",
        "append-only",
        "create-if-missing",
        "replace-if-unmodified",
        "regenerate",
        "forbid",
    }:
        raise ContractError(f"managed_assets[{index}].merge_strategy is invalid")
    if not isinstance(record["required"], bool) or not isinstance(record["protected"], bool) or not isinstance(record["append_only"], bool):
        raise ContractError(f"managed_assets[{index}] boolean lifecycle fields are invalid")
    if not isinstance(record["desired_by"], list) or not record["desired_by"] or not all(
        isinstance(item, str) and item for item in record["desired_by"]
    ):
        raise ContractError(f"managed_assets[{index}].desired_by must be a non-empty string list")
    if len(record["desired_by"]) != len(set(record["desired_by"])):
        raise ContractError(f"managed_assets[{index}].desired_by contains duplicates")
    for field in ("role", "provision", "generated_by", "sensitivity"):
        if not isinstance(record[field], str) or not record[field]:
            raise ContractError(f"managed_assets[{index}].{field} must be a non-empty string")
    if record["schema"] is not None and not isinstance(record["schema"], str):
        raise ContractError(f"managed_assets[{index}].schema must be a string or null")
    _valid_hash(record["base_sha256"])
    _valid_hash(record["installed_sha256"])
    return path, dict(record)


def load_manifest(target: Path, *, explicit_profile: str | None, catalog: dict[str, Any]) -> ManifestState:
    resolved = resolve_assets_manifest(target)
    if resolved is None:
        manifest_path = confined_path(target, MANIFEST_PATH)  # placeholder for error messages
        if explicit_profile is None:
            raise ContractError(
                "PROJECTSTATE_ASSETS.json is missing; pass --profile explicitly to adopt a legacy/no-lock target"
            )
        if explicit_profile not in catalog["profiles"]:
            raise ContractError(f"unknown profile {explicit_profile!r}")
        return ManifestState(
            schema=None,
            template_version=None,
            profile=explicit_profile,
            generation_mode="adopt",
            raw=None,
            template_records={},
            generated_records={},
            protected_records={},
            retired_assets=[],
            upgrade_history=[],
            optional_asset_sets=set(),
            manifest_sha256=None,
        )
    manifest_path = resolved
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ContractError("PROJECTSTATE_ASSETS.json must be a regular file")
    payload = load_json_file(manifest_path)
    manifest_sha256 = sha256_file(manifest_path)
    if not isinstance(payload, dict):
        raise ContractError("PROJECTSTATE_ASSETS.json root must be an object")
    schema = payload.get("schema")
    recorded_profile = payload.get("profile")
    if explicit_profile is not None and explicit_profile != recorded_profile:
        raise ContractError(
            "profile transitions require an explicit semantic migration and are not supported by this upgrader"
        )
    profile = recorded_profile
    if not isinstance(profile, str) or profile not in catalog["profiles"]:
        raise ContractError(f"manifest profile is missing or unknown: {profile!r}")
    generation_mode = payload.get("generation_mode")
    if generation_mode not in {"new", "adopt"}:
        raise ContractError("manifest generation_mode must be 'new' or 'adopt'")
    template_version = payload.get("template_version")
    if not isinstance(template_version, str) or not template_version:
        raise ContractError("manifest template_version must be a non-empty string")

    template_records: dict[Path, dict[str, Any]] = {}
    generated_records: dict[Path, dict[str, Any]] = {}
    protected_records: dict[Path, dict[str, Any]] = {}
    optional_sets: set[str] = set()
    optional_paths = {
        set_id: {normalize_relative_path(raw) for raw in definition["assets"]}
        for set_id, definition in catalog["asset_sets"].items()
        if definition.get("optional") is True
    }

    if schema == "projectstate.runtime_assets.v1":
        allowed = {
            "schema",
            "template_version",
            "profile",
            "generation_mode",
            "assets",
            "excluded_classes",
        }
        if set(payload) != allowed:
            raise ContractError(
                f"v1 manifest fields differ from contract: extra={sorted(set(payload) - allowed)}"
            )
        raw_assets = payload.get("assets")
        if not isinstance(raw_assets, list) or not raw_assets or not all(isinstance(item, str) for item in raw_assets):
            raise ContractError("v1 manifest assets must be a non-empty string list")
        seen: set[Path] = set()
        for raw in raw_assets:
            path = normalize_relative_path(raw)
            if path in seen:
                raise ContractError(f"duplicate managed asset path: {raw}")
            seen.add(path)
            owner = "project" if path in PROJECT_TRUTH_FILES or path in APPEND_ONLY_FILES else "template"
            record = _legacy_record(path, owner=owner)
            if path in GENERATED_CONTROL_PATHS:
                generated = _legacy_record(path, owner="template")
                generated.update(
                    {
                        "role": "generated_control",
                        "provision": "regenerate",
                        "merge_strategy": "regenerate",
                        "generated_by": "legacy-generated-control",
                    }
                )
                generated_records[path] = generated
            elif owner == "template" and path != MANIFEST_PATH:
                template_records[path] = record
            else:
                protected_records[path] = record
            optional_sets.update(
                set_id for set_id, paths in optional_paths.items() if path in paths
            )
        retired_assets: list[dict[str, Any]] = []
        upgrade_history: list[dict[str, Any]] = []
    elif schema == "projectstate.runtime_assets.v2":
        _validate_v2_payload(payload, label="existing manifest")
        required_top = {
            "schema",
            "template_version",
            "template_commit",
            "catalog",
            "profile",
            "profile_dependencies",
            "asset_sets",
            "capabilities",
            "validations",
            "required_gate_level",
            "generation_mode",
            "managed_assets",
            "retired_assets",
            "upgrade_history",
            "excluded_classes",
        }
        if set(payload) != required_top:
            raise ContractError(
                f"v2 manifest fields differ from contract: "
                f"missing={sorted(required_top - set(payload))}, extra={sorted(set(payload) - required_top)}"
            )
        records = payload.get("managed_assets")
        if not isinstance(records, list) or not records:
            raise ContractError("v2 manifest managed_assets must be a non-empty list")
        seen: set[Path] = set()
        for index, raw_record in enumerate(records):
            path, record = _validate_v2_record(raw_record, index)
            if path in seen:
                raise ContractError(f"duplicate managed asset path: {path.as_posix()}")
            seen.add(path)
            if record["owner"] == "template" and record["merge_strategy"] == "regenerate" and path != MANIFEST_PATH:
                generated_records[path] = record
            elif record["owner"] == "template" and record["merge_strategy"] == "replace-if-unmodified":
                template_records[path] = record
            else:
                protected_records[path] = record
            optional_sets.update(
                set_id for set_id, paths in optional_paths.items() if path in paths
            )
        retired_assets = payload.get("retired_assets")
        upgrade_history = payload.get("upgrade_history")
        if not isinstance(retired_assets, list) or not all(isinstance(item, dict) for item in retired_assets):
            raise ContractError("v2 manifest retired_assets must be an object list")
        if not isinstance(upgrade_history, list) or not all(isinstance(item, dict) for item in upgrade_history):
            raise ContractError("v2 manifest upgrade_history must be an object list")
        retired_seen: set[Path] = set()
        for index, item in enumerate(retired_assets):
            if set(item) - {"path", "reason", "base_sha256"} or "path" not in item or "reason" not in item:
                raise ContractError(f"retired_assets[{index}] is malformed")
            retired_path = normalize_relative_path(item["path"])
            if retired_path in retired_seen:
                raise ContractError(f"retired_assets[{index}] duplicates path {retired_path.as_posix()}")
            retired_seen.add(retired_path)
            _valid_hash(item.get("base_sha256"))
        raw_sets = payload.get("asset_sets")
        if not isinstance(raw_sets, list) or not all(isinstance(item, str) for item in raw_sets):
            raise ContractError("v2 manifest asset_sets must be a string list")
        if "github" in raw_sets:
            optional_sets.add("github")
    else:
        raise ContractError(f"unsupported PROJECTSTATE_ASSETS.json schema: {schema!r}")

    return ManifestState(
        schema=schema,
        template_version=template_version,
        profile=profile,
        generation_mode=generation_mode,
        raw=payload,
        template_records=template_records,
        generated_records=generated_records,
        protected_records=protected_records,
        retired_assets=list(retired_assets),
        upgrade_history=list(upgrade_history),
        optional_asset_sets=optional_sets,
        manifest_sha256=manifest_sha256,
    )


def _desired_by(catalog: dict[str, Any], resolved: ResolvedProfile, relpath: Path) -> list[str]:
    desired: list[str] = []
    raw = relpath.as_posix()
    for set_id in resolved.asset_sets:
        if raw in catalog["asset_sets"][set_id]["assets"]:
            desired.append(set_id)
    if not desired:
        raise ContractError(f"desired asset has no owning asset set: {raw}")
    return sorted(desired)


def _template_record(catalog: dict[str, Any], resolved: ResolvedProfile, relpath: Path, source_hash: str) -> dict[str, Any]:
    defaults = catalog["lifecycle_defaults"]["template_asset"]
    schema_path = None
    schema_names = {
        "PROJECT_STATE.yaml": "schemas/project_state.schema.json",
        "PROJECT_DNA.yaml": "schemas/project_dna.schema.json",
        "PROJECT_ADAPTER.yaml": "schemas/project_adapter.schema.json",
        "PROJECTSTATE_ASSETS.json": "schemas/projectstate_assets.schema.json",
    }
    if relpath.as_posix() in schema_names:
        schema_path = schema_names[relpath.as_posix()]
    return {
        "path": relpath.as_posix(),
        **defaults,
        "schema": schema_path,
        "generated_by": f"copy:{relpath.as_posix()}",
        "desired_by": _desired_by(catalog, resolved, relpath),
        "base_sha256": source_hash,
        "installed_sha256": source_hash,
    }


def desired_generated_controls(history: ManifestState, resolved: ResolvedProfile) -> dict[Path, str]:
    controls = {
        Path("prompts/CODING_AGENT_STARTUP_PROMPT.md"): render_coding_agent_startup_prompt(),
    }
    needs_workflow = (
        history.generation_mode == "new"
        or "remote_closure_contract" in resolved.validations
        or "github_issue_and_pr_templates" in resolved.capabilities
        or Path(".github/workflows/projectstate-validate.yml") in history.generated_records
    )
    if needs_workflow:
        controls[Path(".github/workflows/projectstate-validate.yml")] = render_downstream_workflow(
            resolved.required_gate_level
        )
    return controls


def _generated_record(
    catalog: dict[str, Any], resolved: ResolvedProfile, relpath: Path, content_hash: str
) -> dict[str, Any]:
    return {
        "path": relpath.as_posix(),
        **catalog["lifecycle_defaults"]["generated"],
        "schema": None,
        "generated_by": f"scripts/projectstate_generated_controls.py:{relpath.name}",
        "desired_by": [f"profile:{resolved.profile}"],
        "base_sha256": content_hash,
        "installed_sha256": content_hash,
    }


def plan_upgrade(
    target: Path,
    history: ManifestState,
    catalog: dict[str, Any],
    resolved: ResolvedProfile,
    *,
    force_managed: bool,
) -> dict[str, Any]:
    will_add: list[dict[str, Any]] = []
    will_modify: list[dict[str, Any]] = []
    will_skip: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    manual_actions: list[str] = []
    desired_records: dict[Path, dict[str, Any]] = {}
    desired_generated_records: dict[Path, dict[str, Any]] = {}
    retired_history = {
        normalize_relative_path(item["path"]): item
        for item in history.retired_assets
    }

    # Full source and destination preflight happens before any plan is returned.
    for relpath in resolved.assets:
        source = regular_source_path(TEMPLATE_ROOT, relpath)
        source_hash = sha256_file(source)
        destination = confined_path(target, relpath)
        desired_records[relpath] = _template_record(catalog, resolved, relpath, source_hash)
        old = history.template_records.get(relpath)
        if old is None and relpath in retired_history:
            old = _legacy_record(relpath, owner="template")
            old["base_sha256"] = retired_history[relpath].get("base_sha256")
        if not destination.exists():
            will_add.append(
                {
                    "relpath": relpath.as_posix(),
                    "reason": "new_profile_asset" if old is None else "missing_managed_asset",
                    "template_hash": source_hash,
                }
            )
            continue
        if destination.is_symlink() or not destination.is_file():
            conflicts.append(
                {"relpath": relpath.as_posix(), "reason": "destination_is_not_a_regular_file"}
            )
            continue
        target_hash = sha256_file(destination)
        if target_hash == source_hash:
            will_skip.append(
                {
                    "relpath": relpath.as_posix(),
                    "reason": "up_to_date",
                    "target_hash": target_hash,
                }
            )
            continue
        if old is None:
            conflicts.append(
                {
                    "relpath": relpath.as_posix(),
                    "reason": "unowned_path_collision",
                    "target_hash": target_hash,
                    "template_hash": source_hash,
                }
            )
            continue
        base_hash = old.get("base_sha256")
        if isinstance(base_hash, str) and target_hash == base_hash:
            will_modify.append(
                {
                    "relpath": relpath.as_posix(),
                    "reason": "unmodified_since_previous_install",
                    "target_hash": target_hash,
                    "template_hash": source_hash,
                }
            )
        elif force_managed:
            will_modify.append(
                {
                    "relpath": relpath.as_posix(),
                    "reason": "force_managed_local_modification",
                    "target_hash": target_hash,
                    "template_hash": source_hash,
                }
            )
        else:
            conflicts.append(
                {
                    "relpath": relpath.as_posix(),
                    "reason": "local_modification_or_legacy_base_unknown",
                    "target_hash": target_hash,
                    "template_hash": source_hash,
                }
            )

    for relpath, content in desired_generated_controls(history, resolved).items():
        destination = confined_path(target, relpath)
        content_hash = sha256_bytes(content.encode("utf-8"))
        desired_generated_records[relpath] = _generated_record(
            catalog, resolved, relpath, content_hash
        )
        old = history.generated_records.get(relpath)
        common = {
            "relpath": relpath.as_posix(),
            "template_hash": content_hash,
            "generated_content": content,
        }
        if not destination.exists():
            will_add.append({**common, "reason": "missing_generated_control"})
            continue
        if destination.is_symlink() or not destination.is_file():
            conflicts.append(
                {"relpath": relpath.as_posix(), "reason": "generated_control_is_not_a_regular_file"}
            )
            continue
        target_hash = sha256_file(destination)
        if target_hash == content_hash:
            will_skip.append(
                {
                    "relpath": relpath.as_posix(),
                    "reason": "up_to_date",
                    "target_hash": target_hash,
                }
            )
            continue
        if old is None:
            conflicts.append(
                {
                    "relpath": relpath.as_posix(),
                    "reason": "unowned_generated_control_collision",
                    "target_hash": target_hash,
                    "template_hash": content_hash,
                }
            )
            continue
        installed_hash = old.get("installed_sha256") or old.get("base_sha256")
        if target_hash == installed_hash or force_managed:
            reason = (
                "regenerate_unmodified_control"
                if target_hash == installed_hash
                else "force_regenerate_modified_control"
            )
            will_modify.append(
                {**common, "reason": reason, "target_hash": target_hash}
            )
        else:
            conflicts.append(
                {
                    "relpath": relpath.as_posix(),
                    "reason": "locally_modified_generated_control",
                    "target_hash": target_hash,
                    "template_hash": content_hash,
                }
            )

    desired_paths = set(desired_records) | set(desired_generated_records)
    retired = []
    existing_retired = {
        normalize_relative_path(item["path"]): dict(item)
        for item in history.retired_assets
    }
    for desired_path in desired_paths:
        existing_retired.pop(desired_path, None)
    historical_owned = {**history.template_records, **history.generated_records}
    for relpath, record in historical_owned.items():
        if relpath in desired_paths:
            continue
        item = {
            "path": relpath.as_posix(),
            "reason": "removed_from_current_profile_or_catalog",
            "base_sha256": record.get("base_sha256"),
        }
        existing_retired[relpath] = item
        retired.append(item)
    retired_assets = [existing_retired[path] for path in sorted(existing_retired, key=lambda p: p.as_posix())]
    if retired:
        manual_actions.extend(
            f"{item['path']} is no longer desired; retained on disk and recorded as retired"
            for item in retired
        )

    # Protected/project records are validated and observed without changing them.
    protected_records: dict[Path, dict[str, Any]] = {}
    protected_observations: dict[Path, str | None] = {}
    for relpath, old in history.protected_records.items():
        if relpath == MANIFEST_PATH:
            continue
        destination = confined_path(target, relpath)
        record = dict(old)
        if destination.exists():
            if destination.is_symlink() or not destination.is_file():
                conflicts.append(
                    {"relpath": relpath.as_posix(), "reason": "protected_path_is_not_a_regular_file"}
                )
                protected_observations[relpath] = None
            else:
                observed_hash = sha256_file(destination)
                if record.get("installed_sha256") is None:
                    # Migrate legacy inventory without pretending this is a template base.
                    record["installed_sha256"] = observed_hash
                protected_observations[relpath] = observed_hash
        elif record.get("required") is True:
            conflicts.append(
                {
                    "relpath": relpath.as_posix(),
                    "reason": "required_protected_asset_is_missing",
                }
            )
            manual_actions.append(f"protected asset {relpath.as_posix()} is missing; restore or migrate manually")
            record["installed_sha256"] = None
            protected_observations[relpath] = None
        else:
            protected_observations[relpath] = None
        protected_records[relpath] = record

    return {
        "will_add": will_add,
        "will_modify": will_modify,
        "will_skip": will_skip,
        "conflicts": conflicts,
        "manual_actions": manual_actions,
        "retired_assets": retired_assets,
        "desired_records": desired_records,
        "desired_generated_records": desired_generated_records,
        "protected_records": protected_records,
        "protected_observations": protected_observations,
        "source_manifest_present": history.raw is not None,
        "source_manifest_hash": history.manifest_sha256,
    }


def _manifest_record(catalog: dict[str, Any], profile: str) -> dict[str, Any]:
    defaults = catalog["lifecycle_defaults"]["generated"]
    return {
        "path": MANIFEST_PATH.as_posix(),
        **defaults,
        "schema": "schemas/projectstate_assets.schema.json",
        "generated_by": "scripts/projectstate_upgrade.py",
        "desired_by": [f"profile:{profile}"],
        "base_sha256": None,
        "installed_sha256": None,
    }


def build_manifest(
    history: ManifestState,
    plan: dict[str, Any],
    catalog: dict[str, Any],
    resolved: ResolvedProfile,
    template_version: str,
) -> tuple[dict[str, Any], bool]:
    catalog_path = TEMPLATE_ROOT / "profiles" / "catalog.json"
    records = [
        *plan["desired_records"].values(),
        *plan["desired_generated_records"].values(),
        *plan["protected_records"].values(),
    ]
    records.append(_manifest_record(catalog, resolved.profile))
    records.sort(key=lambda record: record["path"])
    candidate = {
        "schema": "projectstate.runtime_assets.v2",
        "template_version": template_version,
        "template_commit": history.raw.get("template_commit") if history.raw else None,
        "catalog": {
            "schema": catalog["schema"],
            "version": catalog["catalog_version"],
            "sha256": sha256_file(catalog_path),
        },
        "profile": resolved.profile,
        "profile_dependencies": list(resolved.profile_dependencies),
        "asset_sets": list(resolved.asset_sets),
        "capabilities": list(resolved.capabilities),
        "validations": list(resolved.validations),
        "required_gate_level": resolved.required_gate_level,
        "generation_mode": history.generation_mode,
        "managed_assets": records,
        "retired_assets": plan["retired_assets"],
        "upgrade_history": list(history.upgrade_history),
        "excluded_classes": EXCLUDED_CLASSES,
    }
    changed = history.raw != candidate
    if changed:
        source_head = git_head(TEMPLATE_ROOT)
        candidate["template_commit"] = source_head
        transition = {
            "from_template_version": history.template_version,
            "to_template_version": template_version,
            "source_commit": source_head,
        }
        if not candidate["upgrade_history"] or candidate["upgrade_history"][-1] != transition:
            candidate["upgrade_history"].append(transition)
    _validate_v2_payload(candidate, label="candidate manifest")
    return candidate, changed


def print_plan(plan: dict[str, Any], target: Path, template_version: str, history: ManifestState, manifest_will_update: bool) -> None:
    print("ProjectState Upgrade Plan")
    print(f"Target: {target}")
    print(f"Profile: {history.profile}")
    print(f"Template version: {template_version}")
    print(f"Target version: {history.template_version or 'not detected'}")

    sections = (
        ("Will add", "will_add", "+"),
        ("Will modify", "will_modify", "~"),
        ("Will skip", "will_skip", "="),
        ("Conflicts", "conflicts", "!"),
    )
    for title, key, marker in sections:
        entries = plan[key]
        print(f"\n{title}:")
        if not entries:
            print("  (none)")
        for info in entries:
            print(f"  {marker} {info['relpath']} [{info.get('reason', 'unspecified')}]")
    print("\nRetired assets (report only; never deleted):")
    if not plan["retired_assets"]:
        print("  (none)")
    for item in plan["retired_assets"]:
        print(f"  - {item['path']} [{item['reason']}]")
    print("\nManual actions:")
    if not plan["manual_actions"]:
        print("  (none)")
    for action in plan["manual_actions"]:
        print(f"  * {action}")
    print(f"\nManifest update: {'yes' if manifest_will_update else 'no'}")


def _ensure_parent(target: Path, destination: Path, created_dirs: list[Path]) -> None:
    relative_parent = destination.parent.relative_to(target)
    current = target
    for part in relative_parent.parts:
        current = current / part
        if current.is_symlink():
            raise UnsafePathError(f"refusing symlink directory during apply: {current}")
        if current.exists():
            if not current.is_dir():
                raise ContractError(f"parent path is not a directory: {current}")
            continue
        current.mkdir()
        created_dirs.append(current)
        if current.is_symlink() or not current.is_dir():
            raise UnsafePathError(f"unsafe directory appeared during apply: {current}")


def _atomic_replace_bytes(destination: Path, content: bytes, mode: int) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, destination)
    finally:
        tmp_path.unlink(missing_ok=True)


def _snapshot(path: Path) -> tuple[bytes, int] | None:
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"transaction path is not a regular file: {path}")
    return path.read_bytes(), stat.S_IMODE(path.stat().st_mode)


def execute_transaction(plan: dict[str, Any], target: Path, manifest: dict[str, Any] | None) -> None:
    actions = [*plan["will_add"], *plan["will_modify"]]
    # Recheck every input before the first write.
    manifest_path = confined_path(target, MANIFEST_PATH)
    if plan.get("source_manifest_present") is True:
        expected_manifest_hash = plan.get("source_manifest_hash")
        if (
            not isinstance(expected_manifest_hash, str)
            or manifest_path.is_symlink()
            or not manifest_path.is_file()
            or sha256_file(manifest_path) != expected_manifest_hash
        ):
            raise ContractError("PROJECTSTATE_ASSETS.json changed after planning")
    elif os.path.lexists(manifest_path):
        raise ContractError("PROJECTSTATE_ASSETS.json appeared after planning")
    for observation in plan.get("will_skip", []):
        relpath = normalize_relative_path(observation["relpath"])
        destination = confined_path(target, relpath)
        expected = observation.get("target_hash")
        if (
            not isinstance(expected, str)
            or destination.is_symlink()
            or not destination.is_file()
            or sha256_file(destination) != expected
        ):
            raise ContractError(f"up-to-date asset changed after planning: {relpath}")
    for relpath, expected in plan.get("protected_observations", {}).items():
        destination = confined_path(target, relpath)
        if expected is None:
            if os.path.lexists(destination):
                raise ContractError(f"protected asset appeared after planning: {relpath}")
        elif (
            destination.is_symlink()
            or not destination.is_file()
            or sha256_file(destination) != expected
        ):
            raise ContractError(f"protected asset changed after planning: {relpath}")
    for info in actions:
        relpath = normalize_relative_path(info["relpath"])
        generated_content = info.get("generated_content")
        if isinstance(generated_content, str):
            if sha256_bytes(generated_content.encode("utf-8")) != info["template_hash"]:
                raise ContractError(f"generated control changed after planning: {relpath}")
        else:
            source = regular_source_path(TEMPLATE_ROOT, relpath)
            if sha256_file(source) != info["template_hash"]:
                raise ContractError(f"template source changed after planning: {relpath}")
        destination = confined_path(target, relpath)
        expected = info.get("target_hash")
        if expected is None and destination.exists():
            raise ContractError(f"destination appeared after planning: {relpath}")
        if expected is not None:
            if not destination.is_file() or destination.is_symlink() or sha256_file(destination) != expected:
                raise ContractError(f"destination changed after planning: {relpath}")

    destinations = [confined_path(target, info["relpath"]) for info in actions]
    if manifest is not None:
        destinations.append(manifest_path)
    snapshots = {path: _snapshot(path) for path in destinations}
    created_dirs: list[Path] = []
    written: list[Path] = []
    try:
        for info in actions:
            relpath = normalize_relative_path(info["relpath"])
            destination = confined_path(target, relpath)
            _ensure_parent(target, destination, created_dirs)
            generated_content = info.get("generated_content")
            if isinstance(generated_content, str):
                content = generated_content.encode("utf-8")
                mode = 0o644
            else:
                source = regular_source_path(TEMPLATE_ROOT, relpath)
                content = source.read_bytes()
                mode = stat.S_IMODE(source.stat().st_mode)
            _atomic_replace_bytes(
                destination,
                content,
                mode,
            )
            written.append(destination)
            print(f"Applied {info['relpath']}")
        if manifest is not None:
            _ensure_parent(target, manifest_path, created_dirs)
            content = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
            _atomic_replace_bytes(manifest_path, content, 0o644)
            written.append(manifest_path)
            print("Updated PROJECTSTATE_ASSETS.json")
    except BaseException:
        rollback_errors: list[str] = []
        for destination in reversed(written):
            previous = snapshots[destination]
            try:
                if previous is None:
                    destination.unlink(missing_ok=True)
                else:
                    _atomic_replace_bytes(destination, previous[0], previous[1])
            except Exception as exc:  # surface rollback failure with the original exception
                rollback_errors.append(f"{destination}: {exc}")
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass
        if rollback_errors:
            raise ContractError(f"upgrade failed and rollback was incomplete: {rollback_errors}")
        raise


def preflight_report_path(raw_path: str, target: Path) -> Path:
    """Return a new external sidecar path or fail before target mutation."""
    raw = Path(raw_path)
    if not raw.name or raw.name in {".", ".."}:
        raise ContractError("upgrade report must name a new file")
    parent = safe_root_path(raw.parent, must_exist=True, cwd=Path.cwd())
    path = parent / raw.name
    if os.path.lexists(path):
        raise ContractError(f"upgrade report already exists; refusing overwrite: {path}")
    for protected_root, label in ((target, "upgrade target"), (TEMPLATE_ROOT, "template root")):
        try:
            path.relative_to(protected_root)
        except ValueError:
            continue
        raise ContractError(f"upgrade report must remain outside the {label}: {path}")
    return path


def write_report(
    path: Path,
    plan: dict[str, Any],
    target: Path,
    template_version: str,
    history: ManifestState,
    *,
    dry_run: bool,
    manifest_will_update: bool,
) -> None:
    def public_actions(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {key: value for key, value in entry.items() if key != "generated_content"}
            for entry in entries
        ]

    report = {
        "schema": "projectstate.upgrade_report.v2",
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "template_version": template_version,
        "target_version": history.template_version,
        "profile": history.profile,
        "apply_requested": not dry_run,
        "application_status": "not_proven_by_plan_report",
        "manifest_will_update": manifest_will_update,
        "summary": {
            "will_add": len(plan["will_add"]),
            "will_modify": len(plan["will_modify"]),
            "will_skip": len(plan["will_skip"]),
            "conflicts": len(plan["conflicts"]),
            "retired_assets": len(plan["retired_assets"]),
            "manual_actions": len(plan["manual_actions"]),
        },
        "will_add": public_actions(plan["will_add"]),
        "will_modify": public_actions(plan["will_modify"]),
        "will_skip": plan["will_skip"],
        "conflicts": plan["conflicts"],
        "retired_assets": plan["retired_assets"],
        "manual_actions": plan["manual_actions"],
    }
    content = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    print(f"Wrote upgrade report: {path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    catalog = load_profile_catalog(TEMPLATE_ROOT)
    optional_sets = sorted(
        set_id
        for set_id, definition in catalog["asset_sets"].items()
        if definition.get("optional") is True
    )
    parser = argparse.ArgumentParser(description="Safe ProjectState downstream upgrade planner")
    parser.add_argument("target", nargs="?", default=".", help="Downstream repo root to upgrade")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply a conflict-free transactional plan")
    mode.add_argument("--dry-run", action="store_true", help="Explicitly select the default read-only mode")
    parser.add_argument(
        "--profile",
        choices=sorted(catalog["profiles"]),
        help="Explicit profile for a legacy/no-lock target; profile transitions require semantic migration",
    )
    parser.add_argument(
        "--force-managed",
        action="store_true",
        help="Replace a locally modified historically template-owned asset; never claims a merge",
    )
    parser.add_argument(
        "--include-github-assets",
        action="store_true",
        help="Enable the optional declarative GitHub asset set",
    )
    parser.add_argument(
        "--include-asset-set",
        action="append",
        default=[],
        choices=optional_sets,
        help="Enable an optional catalog asset set; repeat for multiple sets",
    )
    parser.add_argument("--report", help="Write a JSON upgrade report")
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    try:
        target = safe_root_path(args.target, must_exist=True)
        if target == TEMPLATE_ROOT:
            raise ContractError("target is the template root; upgrade is for downstream repositories")
        catalog = load_profile_catalog(TEMPLATE_ROOT)
        history = load_manifest(target, explicit_profile=args.profile, catalog=catalog)
        if args.apply and history.raw is None:
            raise ContractError(
                "no-lock apply is refused because it cannot prove project-truth ownership; "
                "use init_template.py adopt to establish a complete instance contract"
            )
        optional_sets = set(history.optional_asset_sets) | set(args.include_asset_set)
        if args.include_github_assets:
            if "github" not in catalog["asset_sets"] or catalog["asset_sets"]["github"].get("optional") is not True:
                raise ContractError("legacy --include-github-assets alias is unavailable in this catalog")
            optional_sets.add("github")
        resolved = resolve_profile(catalog, history.profile, optional_asset_sets=optional_sets)
        template_version = read_version(TEMPLATE_ROOT)
        if template_version is None or template_version != catalog["template_version"]:
            raise ContractError("VERSION and profiles/catalog.json template_version do not agree")
        plan = plan_upgrade(
            target,
            history,
            catalog,
            resolved,
            force_managed=args.force_managed,
        )
        manifest, manifest_will_update = build_manifest(
            history,
            plan,
            catalog,
            resolved,
            template_version,
        )
        print_plan(plan, target, template_version, history, manifest_will_update)
        if args.report:
            report_path = preflight_report_path(args.report, target)
            # The report describes the plan, not successful application. Write it
            # before target mutation so report I/O can never create partial target
            # state after an otherwise successful transaction.
            write_report(
                report_path,
                plan,
                target,
                template_version,
                history,
                dry_run=not args.apply,
                manifest_will_update=manifest_will_update,
            )
        if args.apply:
            if plan["conflicts"]:
                print("\nRefusing to apply: unresolved conflicts exist.")
                return 1
            execute_transaction(plan, target, manifest if manifest_will_update else None)
            print("\nUpgrade applied transactionally.")
        return 0
    except (ContractError, UnsafePathError, OSError) as exc:
        print(f"Upgrade refused: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
