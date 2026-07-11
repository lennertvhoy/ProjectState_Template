from __future__ import annotations

from statedd_profile_metrics import DEFAULT_SOURCE_DATE_EPOCH, build_metrics
from statedd_contracts import load_profile_catalog


def test_profile_metrics_are_deterministic_and_validate_every_profile() -> None:
    from pathlib import Path

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
