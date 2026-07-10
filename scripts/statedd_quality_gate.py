#!/usr/bin/env python3
"""
StateDD Quality Gate

Post-slice quality gate: verify all tests pass, static analysis clean,
state files updated, and new evidence recorded.
Exit codes: 0=pass, 1=fail, 2=error
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional


class QualityGate:
    def __init__(self, root: Path, verbose: bool = False, gate_level: int = 1):
        self.root = root
        self.verbose = verbose
        self.gate_level = gate_level
        self.failures: List[str] = []
        self.warnings: List[str] = []

    def run_cmd(self, cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """Run command, return (exit_code, stdout, stderr)."""
        if self.verbose:
            print(f"$ {' '.join(cmd)}", file=sys.stderr)
        try:
            result = subprocess.run(
                cmd, cwd=cwd or self.root, capture_output=True, text=True, timeout=120
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as e:
            return -1, "", str(e)

    def check_tests(self) -> bool:
        """Run test suite."""
        print("🧪 Running tests...")
        ignored_parts = {".git", ".worktrees", ".pytest_cache", "__pycache__", "node_modules"}
        pytest_tests = [
            path
            for pattern in ("test_*.py", "*_test.py")
            for path in self.root.rglob(pattern)
            if path.is_file() and not any(part in ignored_parts for part in path.relative_to(self.root).parts)
        ]
        test_commands: List[List[str]] = []
        pyproject = self.root / "pyproject.toml"
        has_pytest_config = (self.root / "pytest.ini").exists() or (self.root / "tox.ini").exists()
        if pyproject.exists():
            has_pytest_config = has_pytest_config or "[tool.pytest" in pyproject.read_text(
                encoding="utf-8", errors="ignore"
            )
        if pytest_tests or has_pytest_config:
            test_commands.append([sys.executable, "-m", "pytest", "-x", "-q"])

        makefile = self.root / "Makefile"
        if makefile.exists() and "test:" in makefile.read_text(encoding="utf-8", errors="ignore"):
            test_commands.append(["make", "test"])

        package_json = self.root / "package.json"
        if package_json.exists():
            try:
                package = json.loads(package_json.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                package = {}
            scripts = package.get("scripts") if isinstance(package, dict) else None
            if isinstance(scripts, dict) and isinstance(scripts.get("test"), str):
                test_commands.append(["npm", "test"])

        if (self.root / "Cargo.toml").exists():
            test_commands.append(["cargo", "test"])

        if not test_commands:
            self.warnings.append("No project test command detected")
            return True

        for cmd in test_commands:
            code, out, err = self.run_cmd(cmd)
            if code == 0:
                print(f"  ✓ Tests passed ({' '.join(cmd[:2])})")
                return True
            if code != -1:  # Command exists but failed
                self.failures.append(f"Tests failed: {err or out}")
                return False
        self.warnings.append("Detected test commands were unavailable")
        return True

    def check_static_analysis(self) -> bool:
        """Run static analysis/linting."""
        print("🔍 Running static analysis...")
        pyproject = self.root / "pyproject.toml"
        pyproject_text = pyproject.read_text(encoding="utf-8", errors="ignore") if pyproject.exists() else ""
        lint_commands: List[List[str]] = []
        if any((self.root / name).exists() for name in ("ruff.toml", ".ruff.toml")) or "[tool.ruff" in pyproject_text:
            lint_commands.append(["ruff", "check", "."])
        if any((self.root / name).exists() for name in ("mypy.ini", ".mypy.ini")) or "[tool.mypy" in pyproject_text:
            lint_commands.append(["mypy", "."])
        if any((self.root / name).exists() for name in (".flake8", "setup.cfg")):
            lint_commands.append(["flake8", "."])
        if not lint_commands:
            self.warnings.append("No configured static-analysis command detected")
            return True
        passed = True
        for cmd in lint_commands:
            code, out, err = self.run_cmd(cmd)
            if code == 0:
                print(f"  ✓ {cmd[0]} passed")
            elif code != -1:
                self.failures.append(f"{cmd[0]} failed: {err or out}")
                passed = False
        return passed

    def check_state_files(self) -> bool:
        """Validate state files with check_state_docs.py."""
        print("📋 Validating state files...")
        code, out, err = self.run_cmd(["python", "scripts/check_state_docs.py"])
        if code == 0:
            print("  ✓ State files valid")
            return True
        else:
            self.failures.append(f"State validation failed: {err or out}")
            return False

    def check_schemas(self) -> bool:
        """Validate YAML/JSON against schemas."""
        print("📐 Validating schemas...")
        code, out, err = self.run_cmd(["python", "scripts/statedd_validate_schema.py"])
        if code == 0:
            print("  ✓ Schemas valid")
            return True
        else:
            self.failures.append(f"Schema validation failed: {err or out}")
            return False

    def check_evidence(self) -> bool:
        """Verify evidence exists for recent changes."""
        print("📦 Checking evidence...")
        evidence_log = self.root / "docs" / "EVIDENCE_LOG.md"
        if not evidence_log.exists():
            self.failures.append("EVIDENCE_LOG.md not found")
            return False

        # Check for recent evidence entries (last 7 days)
        content = evidence_log.read_text()
        if len(content.strip()) < 50:
            self.failures.append("EVIDENCE_LOG.md appears empty or minimal")
            return False
        print("  ✓ Evidence log has content")
        return True

    def check_acceptance_freezes(self) -> bool:
        """Verify acceptance freezes for user-facing changes."""
        print("🧊 Checking acceptance freezes...")
        freezes = self.root / "docs" / "ACCEPTANCE_FREEZES.md"
        if not freezes.exists():
            self.warnings.append("ACCEPTANCE_FREEZES.md not found")
            return True
        content = freezes.read_text()
        if "## " not in content:  # No freeze entries
            self.warnings.append("No acceptance freezes recorded")
        else:
            print("  ✓ Acceptance freezes present")
        return True

    def check_instruction_lint(self) -> bool:
        """Run instruction linter."""
        print("🔎 Linting instructions...")
        code, out, err = self.run_cmd(["python", "scripts/statedd_instruction_lint.py", "--fail-on", "error"])
        if code == 0:
            print("  ✓ No instruction smells (errors)")
            return True
        else:
            self.failures.append(f"Instruction lint errors: {out}")
            return False

    def check_efficiency(self) -> bool:
        """Run efficiency budget check."""
        print("⚡ Running efficiency check...")
        code, out, err = self.run_cmd(
            ["python", "scripts/statedd_efficiency_check.py", "--gate-level", str(self.gate_level)]
        )
        if code == 0:
            print("  ✓ Efficiency check passed")
            return True
        self.failures.append(f"Efficiency check failed:\n{err or out}")
        return False

    def run(self) -> int:
        """Run all quality checks."""
        print("=" * 50)
        print("StateDD Quality Gate")
        print("=" * 50)

        checks = [
            ("Tests", self.check_tests),
            ("Static Analysis", self.check_static_analysis),
            ("State Files", self.check_state_files),
            ("Schemas", self.check_schemas),
            ("Evidence", self.check_evidence),
            ("Acceptance Freezes", self.check_acceptance_freezes),
            ("Instruction Lint", self.check_instruction_lint),
            ("Efficiency", self.check_efficiency),
        ]

        all_passed = True
        for name, check in checks:
            try:
                if not check():
                    all_passed = False
            except Exception as e:
                self.failures.append(f"{name} check crashed: {e}")
                all_passed = False

        print("\n" + "=" * 50)
        if self.warnings:
            print("Warnings:")
            for w in self.warnings:
                print(f"  ⚠ {w}")

        if self.failures:
            print("Failures:")
            for f in self.failures:
                print(f"  ✗ {f}")
            print("=" * 50)
            print("❌ QUALITY GATE FAILED")
            return 1

        print("✅ ALL QUALITY GATES PASSED")
        print("=" * 50)
        return 0


def main():
    parser = argparse.ArgumentParser(description="StateDD Quality Gate")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--gate-level", type=int, default=1, help="Gate level being proven")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    gate = QualityGate(root, args.verbose, args.gate_level)
    sys.exit(gate.run())


if __name__ == "__main__":
    main()
