#!/usr/bin/env python3
"""Regression tests for provider-agnostic browser verification."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "statedd_browser_verify.py"


class TestBrowserVerification(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def evidence_dir(self, name: str) -> Path:
        return self.tmp / name

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def write_browser_verification(self, evidence_dir: Path, data: dict) -> Path:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        path = evidence_dir / "browser_verification.json"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return path

    def write_runtime_identity(self, evidence_dir: Path, required: bool = True) -> Path:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        path = evidence_dir / "runtime_identity.json"
        artifact = {
            "schema": "statedd.runtime_identity.v1",
            "captured_at": "2026-06-23T12:34:56+02:00",
            "repo": {
                "path": str(evidence_dir),
                "branch": "main",
                "head": "947a8964085b8377017d6681e20fa24d266dcab9",
                "worktree_clean": True,
            },
            "runtime": {"required": required},
            "checks": {},
            "limits": [],
        }
        path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        return path

    def valid_data(self, provider_kind: str, limits: list[str] | None = None) -> dict:
        return {
            "schema": "statedd.browser_verification.v1",
            "captured_at": "2026-06-23T12:34:56+02:00",
            "provider": {
                "kind": provider_kind,
                "required": False,
                "available": True,
                "selection_reason": f"{provider_kind} provider selected for test",
                "fallbacks_considered": ["playwright", "manual_browser"],
            },
            "runtime_identity": {
                "path": "runtime_identity.json",
                "head_matches": True,
                "endpoint_matches": True,
            },
            "checks": [
                {
                    "id": "BV1",
                    "route": "/settings",
                    "claim": "Settings page renders.",
                    "status": "passed",
                    "evidence": ["screenshots/settings.png"],
                    "known_limits": [],
                }
            ],
            "artifacts": [
                {
                    "path": "screenshots/settings.png",
                    "kind": "screenshot",
                    "sha256": None,
                    "redaction_status": "manual_required",
                }
            ],
            "limits": limits or [],
        }

    def test_init_creates_skeleton(self) -> None:
        ev = self.evidence_dir("ev")
        result = self.run_script("init", str(ev), "--slice-id", "BL-BROWSER-001")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((ev / "browser_verification.json").exists())

    def test_init_not_applicable_passes_strict(self) -> None:
        ev = self.evidence_dir("ev")
        result = self.run_script("init", str(ev), "--not-applicable")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_script("check", str(ev), "--strict")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_kimi_webbridge_accepted(self) -> None:
        ev = self.evidence_dir("kimi")
        self.write_runtime_identity(ev)
        (ev / "screenshots").mkdir(parents=True)
        (ev / "screenshots" / "settings.png").write_bytes(b"fake-screenshot")
        data = self.valid_data("kimi_webbridge")
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_playwright_accepted(self) -> None:
        ev = self.evidence_dir("playwright")
        self.write_runtime_identity(ev)
        (ev / "screenshots").mkdir(parents=True)
        (ev / "screenshots" / "settings.png").write_bytes(b"fake-screenshot")
        data = self.valid_data("playwright")
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_agent_native_browser_accepted(self) -> None:
        ev = self.evidence_dir("agent")
        self.write_runtime_identity(ev)
        (ev / "screenshots").mkdir(parents=True)
        (ev / "screenshots" / "settings.png").write_bytes(b"fake-screenshot")
        data = self.valid_data("agent_native_browser")
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_existing_e2e_accepted(self) -> None:
        ev = self.evidence_dir("e2e")
        self.write_runtime_identity(ev)
        (ev / "test_output.txt").write_text("e2e output", encoding="utf-8")
        data = self.valid_data("existing_e2e")
        data["checks"][0]["evidence"] = ["test_output.txt"]
        data["artifacts"] = [{"path": "test_output.txt", "kind": "test_output"}]
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_custom_provider_accepted_when_valid(self) -> None:
        ev = self.evidence_dir("custom")
        self.write_runtime_identity(ev)
        (ev / "output.txt").write_text("custom output", encoding="utf-8")
        data = self.valid_data("custom", limits=["Custom tooling used."])
        data["provider"]["tool"] = "my-browser-tool"
        data["provider"]["command"] = "my-browser-tool capture /settings"
        data["checks"][0]["evidence"] = ["output.txt"]
        data["artifacts"] = [{"path": "output.txt", "kind": "other"}]
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_manual_browser_accepted_with_limits(self) -> None:
        ev = self.evidence_dir("manual")
        self.write_runtime_identity(ev)
        (ev / "screenshots").mkdir(parents=True)
        (ev / "screenshots" / "settings.png").write_bytes(b"fake-screenshot")
        data = self.valid_data("manual_browser", limits=["Manual capture because no automation available."])
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_manual_browser_fails_strict_without_limits(self) -> None:
        ev = self.evidence_dir("manual")
        self.write_runtime_identity(ev)
        (ev / "screenshots").mkdir(parents=True)
        (ev / "screenshots" / "settings.png").write_bytes(b"fake-screenshot")
        data = self.valid_data("manual_browser")
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires explicit known limits", result.stdout)

    def test_custom_provider_fails_strict_without_tool_or_command(self) -> None:
        ev = self.evidence_dir("custom")
        self.write_runtime_identity(ev)
        (ev / "output.txt").write_text("custom output", encoding="utf-8")
        data = self.valid_data("custom", limits=["Custom tooling used."])
        data["checks"][0]["evidence"] = ["output.txt"]
        data["artifacts"] = [{"path": "output.txt", "kind": "other"}]
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("custom provider requires", result.stdout)

    def test_missing_referenced_artifact_fails(self) -> None:
        ev = self.evidence_dir("missing")
        self.write_runtime_identity(ev)
        data = self.valid_data("playwright")
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing artifact", result.stdout)

    def test_hash_mismatch_fails(self) -> None:
        ev = self.evidence_dir("hash")
        self.write_runtime_identity(ev)
        (ev / "screenshots").mkdir(parents=True)
        (ev / "screenshots" / "settings.png").write_bytes(b"fake-screenshot")
        data = self.valid_data("playwright")
        data["artifacts"][0]["sha256"] = "0" * 64
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Hash mismatch", result.stdout)

    def test_hash_command_updates_hashes(self) -> None:
        ev = self.evidence_dir("hash")
        self.write_runtime_identity(ev)
        (ev / "screenshots").mkdir(parents=True)
        (ev / "screenshots" / "settings.png").write_bytes(b"fake-screenshot")
        data = self.valid_data("playwright")
        self.write_browser_verification(ev, data)
        result = self.run_script("hash", str(ev))
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = json.loads((ev / "browser_verification.json").read_text(encoding="utf-8"))
        self.assertIsNotNone(updated["artifacts"][0]["sha256"])
        self.assertNotEqual(updated["artifacts"][0]["sha256"], "0" * 64)

    def test_missing_runtime_identity_fails_when_required(self) -> None:
        ev = self.evidence_dir("missing-runtime")
        (ev / "screenshots").mkdir(parents=True)
        (ev / "screenshots" / "settings.png").write_bytes(b"fake-screenshot")
        data = self.valid_data("playwright")
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_identity.json", result.stdout)

    def test_not_applicable_for_docs_only(self) -> None:
        ev = self.evidence_dir("docs-only")
        data = {
            "schema": "statedd.browser_verification.v1",
            "captured_at": "2026-06-23T12:34:56+02:00",
            "provider": {
                "kind": "not_applicable",
                "required": False,
                "available": False,
                "selection_reason": "Browser verification is not applicable for this docs/scripts-only slice.",
                "fallbacks_considered": [],
            },
            "runtime_identity": {"path": "runtime_identity.json"},
            "checks": [],
            "artifacts": [],
            "limits": ["Browser verification is not applicable for this docs/scripts-only slice."],
        }
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_path_traversal_rejected(self) -> None:
        ev = self.evidence_dir("traversal")
        self.write_runtime_identity(ev)
        outside = self.tmp / "outside_secret.txt"
        outside.write_text("secret", encoding="utf-8")
        data = self.valid_data("playwright")
        data["artifacts"] = [{"path": "../../../outside_secret.txt", "kind": "screenshot"}]
        data["checks"] = []
        self.write_browser_verification(ev, data)
        result = self.run_script("check", str(ev), "--strict")
        self.assertNotEqual(result.returncode, 0)
        combined = f"{result.stdout}\n{result.stderr}".lower()
        self.assertIn("invalid artifact path", combined)

    def test_no_single_provider_required(self) -> None:
        """Any recognized provider must be accepted in strict mode when valid."""
        for kind in ("kimi_webbridge", "playwright", "agent_native_browser", "existing_e2e"):
            with self.subTest(provider=kind):
                ev = self.evidence_dir(f"provider-{kind}")
                self.write_runtime_identity(ev)
                if kind == "existing_e2e":
                    (ev / "test_output.txt").write_text("output", encoding="utf-8")
                    data = self.valid_data(kind)
                    data["checks"][0]["evidence"] = ["test_output.txt"]
                    data["artifacts"] = [{"path": "test_output.txt", "kind": "test_output"}]
                else:
                    (ev / "screenshots").mkdir()
                    (ev / "screenshots" / "settings.png").write_bytes(b"screenshot")
                    data = self.valid_data(kind)
                self.write_browser_verification(ev, data)
                result = self.run_script("check", str(ev), "--strict")
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
