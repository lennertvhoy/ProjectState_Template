"""Backward-compat regression tests for the StateDD -> ProjectState rename.

These tests lock in the one-migration-cycle compatibility surface so future
refactors cannot silently drop aliases that downstream projects still rely on:

* legacy ``scripts/statedd_*.py`` shims re-export the canonical module's ``main``
  (or all public names for library modules);
* legacy ``STATEDD_ASSETS.json`` filename is honored by the manifest resolver;
* legacy ``STATEDD_*`` env vars are still read with lower priority than the
  canonical ``PROJECTSTATE_*`` names;
* schema ``enum`` constants accept both ``projectstate.*`` and ``statedd.*``
  identifiers for runtime assets, runtime identity, and template version;
* legacy ``statedd_mode`` YAML field is accepted alongside ``projectstate_mode``.

Historical artifacts that must remain unchanged (evidence, fixtures, WORKLOG,
RELEASE_NOTES_statedd-template-v4, BL-STATEDD-INTEGRATION-001) are also checked
so the rename stays surgical.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from projectstate_contracts import (  # noqa: E402
    ASSETS_MANIFEST_CANONICAL,
    ASSETS_MANIFEST_LEGACY,
    resolve_assets_manifest,
)


def _shim_names() -> list[str]:
    return sorted(p.name for p in (ROOT / "scripts").glob("statedd_*.py"))


def test_every_canonical_script_has_a_legacy_shim() -> None:
    canonical = sorted(p.name for p in (ROOT / "scripts").glob("projectstate_*.py"))
    shims = _shim_names()
    expected_shims = sorted(f"statedd_{name.removeprefix('projectstate_')}" for name in canonical)
    assert shims == expected_shims, (
        "Every canonical projectstate_*.py must have a statedd_*.py backward-compat shim. "
        f"Missing or extra: {set(expected_shims).symmetric_difference(shims)}"
    )


@pytest.mark.parametrize("shim_name", _shim_names())
def test_legacy_shim_imports_canonical_module(shim_name: str) -> None:
    """Each statedd_*.py shim must import successfully and re-export public names."""
    module_name = shim_name[: -len(".py")]
    canonical = "projectstate_" + module_name.removeprefix("statedd_")
    canonical_path = ROOT / "scripts" / f"{canonical}.py"
    if not canonical_path.exists():
        pytest.skip(f"canonical {canonical} not present (template-only shim)")
    canonical_text = canonical_path.read_text()
    ns: dict[str, object] = {}
    shim_path = ROOT / "scripts" / shim_name
    exec(compile(shim_path.read_text(), shim_path, "exec"), ns)
    if "def main(" in canonical_text:
        assert callable(ns.get("main")), (
            f"{shim_name}: canonical has main(); shim must re-export it"
        )
    else:
        # Library module shim (star-import): at least one public name re-exported.
        public = [k for k in ns if not k.startswith("_") and k not in {"sys", "pathlib"}]
        assert public, f"{shim_name}: star-import shim re-exported no public names"


def test_assets_manifest_filename_constants() -> None:
    assert ASSETS_MANIFEST_CANONICAL == "PROJECTSTATE_ASSETS.json"
    assert ASSETS_MANIFEST_LEGACY == "STATEDD_ASSETS.json"


def test_resolve_assets_manifest_prefers_canonical_then_legacy(tmp_path: Path) -> None:
    canonical = tmp_path / ASSETS_MANIFEST_CANONICAL
    legacy = tmp_path / ASSETS_MANIFEST_LEGACY
    # Neither exists -> None
    assert resolve_assets_manifest(tmp_path) is None
    # Legacy only -> legacy
    legacy.write_text("{}", encoding="utf-8")
    assert resolve_assets_manifest(tmp_path) == legacy
    # Both exist -> canonical wins
    canonical.write_text("{}", encoding="utf-8")
    assert resolve_assets_manifest(tmp_path) == canonical


def test_assets_schema_accepts_both_runtime_asset_identifiers() -> None:
    schema = json.loads((ROOT / "schemas" / "projectstate_assets.schema.json").read_text())
    schema_enum = schema["properties"]["schema"]["enum"]
    assert "projectstate.runtime_assets.v2" in schema_enum
    assert "statedd.runtime_assets.v2" in schema_enum
    template_pattern = schema["properties"]["template_version"]["pattern"]
    assert "projectstate" in template_pattern
    assert "statedd" in template_pattern


@pytest.mark.parametrize(
    "schema_file,field_path,expected_values",
    [
        ("project_state.schema.json",
         ["properties", "workflow", "properties", "projectstate_mode", "enum"],
         ["template-maintenance", "bootstrap", "operating"]),
        ("project_state.schema.json",
         ["properties", "workflow", "properties", "statedd_mode", "enum"],
         ["template-maintenance", "bootstrap", "operating"]),
        ("project_dna.schema.json",
         ["properties", "version", "enum"],
         ["projectstate-template-v5", "statedd-template-v5"]),
        ("project_adapter.schema.json",
         ["properties", "version", "enum"],
         ["projectstate-template-v5", "statedd-template-v5"]),
        ("runtime_identity_v2.schema.json",
         ["properties", "schema", "enum"],
         ["projectstate.runtime_identity.v2", "statedd.runtime_identity.v2"]),
    ],
)
def test_schemas_accept_both_canonical_and_legacy_identifiers(
    schema_file: str, field_path: list[str], expected_values: list[str]
) -> None:
    schema = json.loads((ROOT / "schemas" / schema_file).read_text())
    node = schema
    for key in field_path:
        node = node[key]
    assert node == expected_values


def test_project_state_workflow_allows_either_mode_field() -> None:
    schema = json.loads((ROOT / "schemas" / "project_state.schema.json").read_text())
    workflow = schema["properties"]["workflow"]
    # projectstate_mode removed from hard-required; anyOf allows either spelling.
    assert "projectstate_mode" not in workflow.get("required", [])
    any_of = workflow["anyOf"]
    required_sets = [frozenset(clause.get("required", [])) for clause in any_of]
    assert frozenset(["projectstate_mode"]) in required_sets
    assert frozenset(["statedd_mode"]) in required_sets

def test_check_state_docs_reads_legacy_statedd_mode_field(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_state_docs import detect_repo_context  # noqa: E402

    project_state = tmp_path / "PROJECT_STATE.yaml"
    project_state.write_text(
        "workflow:\n  repo_role: downstream_project\n  statedd_mode: operating\n  repo_mode: operating\n",
        encoding="utf-8",
    )
    role, mode = detect_repo_context(tmp_path)
    assert role == "downstream_project"
    assert mode == "operating"


def test_legacy_env_vars_are_honored_with_lower_priority_than_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from projectstate_agent_worktree import generate_agent_id  # noqa: E402
    from projectstate_git_safety_session import default_state_root  # noqa: E402
    from projectstate_workspace_inventory import workspace_state_root  # noqa: E402

    monkeypatch.delenv("PROJECTSTATE_AGENT_ID", raising=False)
    monkeypatch.setenv("STATEDD_AGENT_ID", "legacy-agent-42")
    agent_id, short = generate_agent_id()
    assert agent_id == "legacy-agent-42"
    assert short == "lega"  # first 4 chars lowercased

    monkeypatch.delenv("PROJECTSTATE_GIT_SAFETY_STATE_ROOT", raising=False)
    monkeypatch.setenv("STATEDD_GIT_SAFETY_STATE_ROOT", str("/tmp/legacy-state-root"))
    assert str(default_state_root()) == "/tmp/legacy-state-root"

    monkeypatch.delenv("PROJECTSTATE_WORKSPACE_ROOT", raising=False)
    monkeypatch.setenv("STATEDD_WORKSPACE_ROOT", str("/tmp/legacy-ws-root"))
    assert str(workspace_state_root()) == "/tmp/legacy-ws-root"

    # Canonical wins over legacy when both are set.
    monkeypatch.setenv("PROJECTSTATE_AGENT_ID", "canonical-agent-7")
    agent_id2, _ = generate_agent_id()
    assert agent_id2 == "canonical-agent-7"


def test_canonical_env_vars_take_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from projectstate_workspace_inventory import workspace_state_root  # noqa: E402

    monkeypatch.setenv("STATEDD_WORKSPACE_ROOT", "/tmp/legacy-should-lose")
    monkeypatch.setenv("PROJECTSTATE_WORKSPACE_ROOT", "/tmp/canonical-wins")
    assert str(workspace_state_root()) == "/tmp/canonical-wins"


def test_historical_artifacts_are_not_rewritten() -> None:
    """Files in the preserve set must still contain original StateDD references."""
    worklog = (ROOT / "WORKLOG.md").read_text()
    # Banner explains the rename but old entries retain the prior name.
    assert "StateDD" in worklog or "statedd" in worklog, "WORKLOG history must be preserved"
    evidence_log = (ROOT / "docs" / "EVIDENCE_LOG.md").read_text()
    assert "StateDD" in evidence_log, "EVIDENCE_LOG history must be preserved"

    release_notes = ROOT / "docs" / "RELEASE_NOTES_statedd-template-v4.md"
    assert release_notes.exists(), "historical v4 release notes filename must be preserved"
    notes_text = release_notes.read_text()
    assert "statedd-template-v4" in notes_text, "historical v4 version string must be preserved"


def test_legacy_command_alias_files_exist_and_point_at_canonical() -> None:
    aliases = sorted(p.name for p in (ROOT / "commands").glob("statedd-*.md"))
    assert aliases == [
        "statedd-close-slice.md",
        "statedd-failure-scan.md",
        "statedd-git-safety.md",
        "statedd-ingest-bad-event.md",
        "statedd-quality-freeze.md",
        "statedd-release-gate.md",
        "statedd-remote-closure.md",
    ]
    for alias_name in aliases:
        text = (ROOT / "commands" / alias_name).read_text()
        canonical = "projectstate-" + alias_name.removeprefix("statedd-")
        assert canonical in text, f"{alias_name} must reference canonical {canonical}"
        assert "alias_for:" in text


def test_legacy_command_alias_files_are_short() -> None:
    """Alias files are routing stubs and must stay small (efficiency invariant)."""
    for alias in (ROOT / "commands").glob("statedd-*.md"):
        size = alias.stat().st_size
        assert size < 600, f"{alias.name} is {size} bytes; alias stubs must stay tiny"


def test_legacy_shims_are_small() -> None:
    """Shims are routing stubs and must stay small (efficiency invariant)."""
    for shim in (ROOT / "scripts").glob("statedd_*.py"):
        size = shim.stat().st_size
        assert size < 800, f"{shim.name} is {size} bytes; shim must stay tiny"


def test_bl_statedd_integration_historical_id_is_preserved() -> None:
    """The historical scan id must remain unchanged across the rename."""
    backlog = (ROOT / "BACKLOG.md").read_text()
    assert "BL-STATEDD-INTEGRATION-001" in backlog
    scan_file = ROOT / "docs" / "failure_scans" / "BL-STATEDD-INTEGRATION-001.md"
    assert scan_file.exists(), "historical scan filename must be preserved"


def test_version_check_recognizes_all_three_readme_prefixes(tmp_path: Path) -> None:
    """repo_is_template_maintenance must accept canonical and both legacy prefixes."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from projectstate_version_check import repo_is_template_maintenance  # noqa: E402

    for heading, expected in [
        ("# ProjectState Template\n", True),
        ("# StateDD Template\n", True),  # legacy short brand
        ("# State Driven Development Template\n", True),  # legacy long form
        ("# Some Other Project\n", False),
    ]:
        (tmp_path / "README.md").write_text(heading, encoding="utf-8")
        assert repo_is_template_maintenance(tmp_path) is expected, (
            f"README heading {heading!r} -> expected {expected}"
        )


def test_required_readme_phrases_use_canonical_name() -> None:
    """The required-phrases list must ask for the new brand, not the legacy one."""
    src = (ROOT / "scripts" / "check_state_docs.py").read_text()
    assert "ProjectState Template" in src
    assert '"State Driven Development Template"' not in src
    assert '"StateDD Template"' not in src


def test_current_facing_docs_have_no_legacy_brand() -> None:
    """Canonical current-facing docs must not still say 'State Driven Development'."""
    for relpath in [
        "README.md",
        "PROJECT_DNA.yaml",
        "docs/WORKFLOW_FOR_BEGINNERS.md",
        "scripts/README.md",
        "docs/architecture/PROJECTSTATE_MAXIMUM_VALUE_REVIEW.md",
        "docs/benchmarks/PROJECTSTATE_BENCHMARK_SPEC.md",
    ]:
        text = (ROOT / relpath).read_text(encoding="utf-8")
        assert "State Driven Development" not in text, (
            f"{relpath} still contains legacy long-form brand name"
        )
        assert "STATE_DD_" not in text, f"{relpath} still references STATE_DD_ filenames"


def test_init_template_constants_use_canonical_name() -> None:
    """Generated downstream projects must use the new brand in rendered text."""
    src = (ROOT / "scripts" / "init_template.py").read_text()
    assert 'TEMPLATE_NAME = "ProjectState Template"' in src
    assert 'CONTRACT_TITLE = "ProjectState Template Contract"' in src
    assert "State Driven Development" not in src


def main() -> int:
    return pytest.main([__file__, "-v"])


if __name__ == "__main__":
    raise SystemExit(main())
