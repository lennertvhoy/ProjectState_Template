from __future__ import annotations

import json
from pathlib import Path

from statedd_profile_metrics import (
    DEFAULT_SOURCE_DATE_EPOCH,
    build_metrics,
    normalized_file_blobs,
)
from statedd_contracts import load_profile_catalog


def test_profile_metrics_are_deterministic_and_validate_every_profile() -> None:
    root = Path(__file__).resolve().parents[1]
    import subprocess

    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()

    first = build_metrics(root, template_commit=source_commit, epoch=DEFAULT_SOURCE_DATE_EPOCH)
    second = build_metrics(root, template_commit=source_commit, epoch=DEFAULT_SOURCE_DATE_EPOCH)

    assert first == second
    assert first["provenance"]["commit_exists"] is True
    assert [item["profile"] for item in first["profiles"]] == list(
        load_profile_catalog(root)["profiles"]
    )
    assert all(item["quality_gate"]["result"] == "pass" for item in first["profiles"])
    assert all("initial_orientation" in item["contexts"] for item in first["profiles"])
    assert all(item["startup_file_count"] == 4 for item in first["profiles"])


def test_profile_metrics_normalize_dirty_generated_lock_to_proof_commit(tmp_path: Path) -> None:
    target = tmp_path / "profile"
    target.mkdir()
    managed = target / "AGENTS.md"
    managed.write_text("# Agent contract\n", encoding="utf-8")
    lock = target / "STATEDD_ASSETS.json"
    lock.write_text(
        json.dumps(
            {
                "template_commit": None,
                "managed_assets": [
                    {
                        "path": "AGENTS.md",
                        "base_sha256": "0" * 64,
                        "installed_sha256": "0" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    proof_commit = "a" * 40
    blobs = normalized_file_blobs([managed, lock], target, proof_commit)
    normalized_lock = json.loads(blobs["STATEDD_ASSETS.json"].decode("utf-8"))
    assert normalized_lock["template_commit"] == proof_commit
