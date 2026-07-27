#!/usr/bin/env python3
"""Generate reproducible profile and task-context metrics.

The checked artifact is derived evidence. It never becomes project truth and it
records the source commit/tree used for measurement instead of pretending a
checked-in file can contain the SHA of the commit that contains itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path
from typing import Any

try:
    from statedd_contracts import ContractError, load_profile_catalog, resolve_profile
    from statedd_validate_schema import StateDDYamlError, parse_yaml_text
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.statedd_contracts import ContractError, load_profile_catalog, resolve_profile
    from scripts.statedd_validate_schema import StateDDYamlError, parse_yaml_text


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "statedd.profile_metrics.v1"
DEFAULT_OUTPUT = Path("docs/metrics/profile_metrics.json")
DEFAULT_SOURCE_DATE_EPOCH = 1783728000
IGNORED_PARTS = {".git", ".pytest_cache", "__pycache__"}


class MetricsError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def squash_stable_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    """Return metric content excluding commit identities that squash merges change."""
    stable = json.loads(json.dumps(payload))
    stable.pop("template_commit", None)
    stable.pop("generation_command", None)
    stable.pop("provenance", None)
    return stable


def metrics_match_after_squash(existing: dict[str, Any], regenerated: dict[str, Any]) -> bool:
    """Accept a content-identical metric proof when GitHub rewrote commit ancestry."""
    return (
        existing.get("source_tree_sha256") == regenerated.get("source_tree_sha256")
        and squash_stable_metrics(existing) == squash_stable_metrics(regenerated)
    )


def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )


def git_commit(root: Path) -> str:
    completed = run(["git", "rev-parse", "HEAD"], cwd=root)
    value = completed.stdout.strip()
    if completed.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise MetricsError("Could not prove a full local Git commit for metrics provenance")
    return value


def prove_source_commit(root: Path, commit: str, source_inputs: list[str]) -> dict[str, Any]:
    exists = run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root).returncode == 0
    ancestor = exists and run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=root).returncode == 0
    mismatches: list[str] = []
    if exists:
        for rel in source_inputs:
            recorded = run(["git", "show", f"{commit}:{rel}"], cwd=root)
            if recorded.returncode != 0 or recorded.stdout.encode("utf-8") != (root / rel).read_bytes():
                mismatches.append(rel)
    else:
        mismatches = list(source_inputs)
    return {
        "commit_exists": exists,
        "commit_is_ancestor_of_head": ancestor,
        "source_inputs_match_commit": exists and ancestor and not mismatches,
        "mismatched_inputs": mismatches,
    }


def load_selection_policies(root: Path) -> dict[str, list[str]]:
    path = root / "EFFICIENCY_BUDGET.yaml"
    try:
        payload = parse_yaml_text(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, StateDDYamlError) as exc:
        raise MetricsError(f"Invalid efficiency budget: {exc}") from exc
    context = payload.get("context_budgets") if isinstance(payload, dict) else None
    policies = context.get("selection_policies") if isinstance(context, dict) else None
    if not isinstance(policies, dict) or "initial_orientation" not in policies:
        raise MetricsError("EFFICIENCY_BUDGET.yaml has no initial_orientation selection policy")
    result: dict[str, list[str]] = {}
    for name, files in policies.items():
        if not isinstance(name, str) or not isinstance(files, list) or not all(isinstance(item, str) for item in files):
            raise MetricsError(f"Invalid context selection policy: {name!r}")
        if len(files) != len(set(files)):
            raise MetricsError(f"Duplicate file in context selection policy: {name}")
        result[name] = files
    return result


def normalized_bytes(path: Path, target: Path) -> bytes:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw
    return text.replace(str(target), "<TARGET_ROOT>").encode("utf-8")


def normalized_file_blobs(
    files: list[Path],
    target: Path,
    template_commit: str,
) -> dict[str, bytes]:
    """Normalize path-bearing content and its lifecycle hashes as one unit."""
    blobs = {
        path.relative_to(target).as_posix(): normalized_bytes(path, target)
        for path in files
    }
    manifest_blob = blobs.get("STATEDD_ASSETS.json")
    if manifest_blob is None:
        return blobs
    manifest = json.loads(manifest_blob.decode("utf-8"))
    # Profile generation intentionally refuses to label a dirty source tree with
    # HEAD. Metrics are different: they measure a caller-proven commit and must
    # not drift when unrelated finalization artifacts make the worktree dirty.
    manifest["template_commit"] = template_commit
    for record in manifest.get("managed_assets", []):
        rel = record.get("path") if isinstance(record, dict) else None
        if not isinstance(rel, str) or rel == "STATEDD_ASSETS.json" or rel not in blobs:
            continue
        digest = sha256_bytes(blobs[rel])
        if record.get("base_sha256") is not None:
            record["base_sha256"] = digest
        if record.get("installed_sha256") is not None:
            record["installed_sha256"] = digest
    blobs["STATEDD_ASSETS.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return blobs


def counted_files(target: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in target.rglob("*")
            if path.is_file() and not any(part in IGNORED_PARTS for part in path.relative_to(target).parts)
        ),
        key=lambda path: path.relative_to(target).as_posix(),
    )


def tokenizer() -> tuple[str, str | None, Any | None]:
    try:
        import tiktoken  # type: ignore

        return "o200k_base", metadata.version("tiktoken"), tiktoken.get_encoding("o200k_base")
    except (ImportError, metadata.PackageNotFoundError):
        return "o200k_base", None, None


def token_metrics(blobs: list[bytes], encoding: Any | None) -> tuple[int, int | None]:
    estimated = sum(math.ceil(len(blob) / 4) for blob in blobs)
    if encoding is None:
        return estimated, None
    actual = 0
    for blob in blobs:
        actual += len(encoding.encode(blob.decode("utf-8", errors="replace")))
    return estimated, actual


def source_tree_digest(root: Path, catalog: dict[str, Any]) -> tuple[str, list[str]]:
    inputs = {
        "VERSION",
        "EFFICIENCY_BUDGET.yaml",
        "profiles/catalog.json",
        "scripts/init_template.py",
        "scripts/statedd_contracts.py",
        "scripts/statedd_profile_metrics.py",
        "schemas/profile_metrics.schema.json",
    }
    for profile in catalog["profiles"]:
        inputs.update(path.as_posix() for path in resolve_profile(catalog, profile).assets)
    ordered = sorted(inputs)
    digest = hashlib.sha256()
    for rel in ordered:
        path = root / rel
        if not path.is_file():
            raise MetricsError(f"Metric source input is missing: {rel}")
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_bytes(path.read_bytes()).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), ordered


def measure_profile(
    root: Path,
    profile: str,
    policies: dict[str, list[str]],
    epoch: int,
    encoding: Any | None,
    template_commit: str,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="statedd-profile-metrics-") as raw_tmp:
        target = Path(raw_tmp) / profile
        env = os.environ.copy()
        env["SOURCE_DATE_EPOCH"] = str(epoch)
        generation = run(
            [
                sys.executable,
                "scripts/init_template.py",
                "new",
                "--name",
                f"Metrics {profile}",
                "--profile",
                profile,
                "--target",
                str(target),
            ],
            cwd=root,
            env=env,
        )
        if generation.returncode != 0:
            raise MetricsError(f"Profile {profile} generation failed: {generation.stderr or generation.stdout}")

        lock = json.loads((target / "STATEDD_ASSETS.json").read_text(encoding="utf-8"))
        gate_level = lock["required_gate_level"]
        gate_command = [
            sys.executable,
            str(target / "scripts" / "statedd_quality_gate.py"),
            "--root",
            str(target),
            "--gate-level",
            str(gate_level),
            "--conformance",
        ]
        quality = run(gate_command, cwd=target, env=env)
        if quality.returncode != 0:
            detail = quality.stderr or quality.stdout
            raise MetricsError(f"Generated profile {profile} failed its required gate: {detail}")

        files = counted_files(target)
        blob_map = normalized_file_blobs(files, target, template_commit)
        blobs = [blob_map[path.relative_to(target).as_posix()] for path in files]
        estimated, actual = token_metrics(blobs, encoding)
        contexts: dict[str, Any] = {}
        for policy, requested in policies.items():
            selected = [target / rel for rel in requested if (target / rel).is_file()]
            missing = [rel for rel in requested if not (target / rel).is_file()]
            selected_blobs = [blob_map[path.relative_to(target).as_posix()] for path in selected]
            context_estimated, context_actual = token_metrics(selected_blobs, encoding)
            contexts[policy] = {
                "requested_files": requested,
                "included_files": [path.relative_to(target).as_posix() for path in selected],
                "missing_optional_files": missing,
                "file_count": len(selected),
                "total_bytes": sum(len(blob) for blob in selected_blobs),
                "estimated_tokens": context_estimated,
                "actual_tokens": context_actual,
            }

        startup = contexts["initial_orientation"]
        return {
            "profile": profile,
            "resolved_asset_sets": lock["asset_sets"],
            "required_gate_level": gate_level,
            "generated_file_count": len(files),
            "total_bytes": sum(len(blob) for blob in blobs),
            "estimated_tokens": estimated,
            "actual_tokens": actual,
            "startup_file_count": startup["file_count"],
            "startup_bytes": startup["total_bytes"],
            "startup_estimated_tokens": startup["estimated_tokens"],
            "startup_actual_tokens": startup["actual_tokens"],
            "quality_gate": {
                "result": "pass",
                "exit_code": quality.returncode,
                "gate_level": gate_level,
                "command": "python3 scripts/statedd_quality_gate.py --gate-level "
                + str(gate_level)
                + " --conformance",
            },
            "contexts": contexts,
        }


def build_metrics(root: Path, *, template_commit: str, epoch: int) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", template_commit):
        raise MetricsError("template_commit must be a full 40-character SHA")
    try:
        catalog = load_profile_catalog(root)
    except ContractError as exc:
        raise MetricsError(str(exc)) from exc
    policies = load_selection_policies(root)
    encoding_name, tokenizer_version, encoding = tokenizer()
    tree_hash, source_inputs = source_tree_digest(root, catalog)
    provenance = prove_source_commit(root, template_commit, source_inputs)
    profiles = [
        measure_profile(root, profile, policies, epoch, encoding, template_commit)
        for profile in catalog["profiles"]
    ]
    generated_at = __import__("datetime").datetime.fromtimestamp(
        epoch, tz=__import__("datetime").timezone.utc
    ).isoformat().replace("+00:00", "Z")
    return {
        "schema": SCHEMA,
        "schema_version": 1,
        "template_version": (root / "VERSION").read_text(encoding="utf-8").strip(),
        "template_commit": template_commit,
        "source_tree_sha256": tree_hash,
        "source_inputs": source_inputs,
        "generated_at": generated_at,
        "generation_command": " ".join(
            [
                "python3 scripts/statedd_profile_metrics.py",
                "--output docs/metrics/profile_metrics.json",
                f"--template-commit {template_commit}",
                *(
                    [f"--source-date-epoch {epoch}"]
                    if epoch != DEFAULT_SOURCE_DATE_EPOCH
                    else []
                ),
            ]
        ),
        "provenance": provenance,
        "reproducibility": {
            "source_date_epoch": epoch,
            "path_normalization": "absolute generated root replaced with <TARGET_ROOT> before byte/token counts",
            "file_order": "relative POSIX path ascending",
            "token_aggregation": "sum of per-file counts",
            "self_reference_rule": "template_commit is the measured source/proof commit, not the later artifact commit",
        },
        "tokenizer": {
            "estimated_method": "sum(ceil(normalized_utf8_file_bytes/4))",
            "actual_encoding": encoding_name,
            "actual_tokenizer_package": "tiktoken" if tokenizer_version else None,
            "actual_tokenizer_version": tokenizer_version,
            "actual_counts_available": encoding is not None,
        },
        "profiles": profiles,
    }


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate reproducible StateDD profile/context metrics")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--template-commit", default=None)
    parser.add_argument("--source-date-epoch", type=int, default=DEFAULT_SOURCE_DATE_EPOCH)
    parser.add_argument("--check", action="store_true", help="Regenerate and compare with the existing artifact")
    parser.add_argument(
        "--allow-dirty-source",
        action="store_true",
        help="Allow an artifact whose measured source inputs differ from the recorded commit",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    try:
        existing = json.loads(output.read_text(encoding="utf-8")) if args.check and output.exists() else None
        source_commit = args.template_commit
        if source_commit is None and isinstance(existing, dict):
            source_commit = existing.get("template_commit")
        payload = build_metrics(
            root,
            template_commit=source_commit or git_commit(root),
            epoch=args.source_date_epoch,
        )
    except (MetricsError, OSError, json.JSONDecodeError) as exc:
        print(f"Profile metrics failed: {exc}", file=sys.stderr)
        return 1

    squash_equivalent = (
        args.check
        and isinstance(existing, dict)
        and metrics_match_after_squash(existing, payload)
    )
    if not payload["provenance"]["source_inputs_match_commit"] and not args.allow_dirty_source and not squash_equivalent:
        print(
            "Profile metrics refused: source inputs do not match the recorded template commit",
            file=sys.stderr,
        )
        return 1
    if args.check:
        if existing == payload or squash_equivalent:
            print(f"Profile metrics reproducible: {output}")
            return 0
        print(f"Profile metrics drift: {output}", file=sys.stderr)
        return 1
    atomic_write(output, payload)
    print(f"Profile metrics written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
