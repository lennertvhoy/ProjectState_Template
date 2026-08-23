#!/usr/bin/env python3
"""Tests for the concrete Playwright browser provider adapter."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "projectstate_playwright_capture.py"


class TestPlaywrightCapture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.fake = self.tmp / "fake-playwright"
        self.fake.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "args = sys.argv[1:]\n"
            "har = pathlib.Path(args[args.index('--save-har') + 1])\n"
            "screenshot = pathlib.Path(args[-1])\n"
            "har.parent.mkdir(parents=True, exist_ok=True)\n"
            "har.write_text('{\\\"log\\\":{\\\"entries\\\":[]}}\\n')\n"
            "screenshot.write_bytes(b'png-fixture')\n"
            "print('fake playwright capture')\n",
            encoding="utf-8",
        )
        self.fake.chmod(self.fake.stat().st_mode | os0111())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_capture(self, evidence: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--url",
                "https://example.com/settings",
                "--evidence-dir",
                str(evidence),
                "--repo",
                str(ROOT),
                "--playwright-command",
                str(self.fake),
                "--no-runtime-required",
                "Template repository has no application runtime; this is a provider smoke test.",
                *extra,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_capture_writes_strict_browser_contract(self) -> None:
        evidence = self.tmp / "evidence"
        result = self.run_capture(evidence, "--slice-id", "BL-BROWSER-002")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads((evidence / "browser_verification.json").read_text(encoding="utf-8"))
        self.assertEqual(data["provider"]["kind"], "playwright")
        self.assertEqual(data["checks"][0]["status"], "passed")
        self.assertTrue((evidence / "playwright" / "page.png").exists())
        self.assertTrue((evidence / "playwright" / "network.har").exists())
        check = subprocess.run(
            [sys.executable, str(ROOT / "scripts/projectstate_browser_verify.py"), "check", str(evidence), "--strict"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_capture_rejects_non_http_urls(self) -> None:
        evidence = self.tmp / "bad"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--url",
                "file:///tmp/page.html",
                "--evidence-dir",
                str(evidence),
                "--playwright-command",
                str(self.fake),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("absolute http:// or https://", result.stderr or result.stdout)


def os0111() -> int:
    return 0o111


if __name__ == "__main__":
    unittest.main()
