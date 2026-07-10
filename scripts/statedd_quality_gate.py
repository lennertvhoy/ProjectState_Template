#!/usr/bin/env python3
"""
StateDD Quality Gate

Post-slice quality gate: verify all tests pass, static analysis clean,
state files updated, and new evidence recorded.
Exit codes: 0=pass, 1=fail, 2=error
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional

from statedd_validate_schema import ArtifactContractError, load_evidence_bundle


class QualityGate:
    def __init__(
        self,
        root: Path,
        verbose: bool = False,
        gate_level: int = 1,
        *,
        slice_id: str | None = None,
        expected_head: str | None = None,
        evidence_dir: Path | None = None,
        privacy_profile: str = "public",
    ):
        self.root = root
        self.verbose = verbose
        self.gate_level = gate_level
        self.slice_id = slice_id
        self.expected_head = expected_head
        self.evidence_dir = evidence_dir
        self.privacy_profile = privacy_profile
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

    def config_has_section(self, path: Path, section: str) -> bool:
        """Return whether a text config declares an exact INI/TOML section."""
        if not path.is_file():
            return False
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False
        return re.search(rf"^\s*\[{re.escape(section)}\]\s*$", content, re.MULTILINE) is not None

    def package_script(self, name: str) -> bool:
        package = self.root / "package.json"
        if not package.is_file():
            return False
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        scripts = data.get("scripts")
        return isinstance(scripts, dict) and isinstance(scripts.get(name), str) and bool(scripts[name].strip())

    def configured_test_commands(self) -> List[List[str]]:
        """Discover test runners only from checked-in test/configuration surfaces."""
        commands: List[List[str]] = []
        python_tests = list(self.root.glob("test_*.py"))
        tests_dir = self.root / "tests"
        scripts_dir = self.root / "scripts"
        if tests_dir.is_dir():
            python_tests.extend(tests_dir.rglob("test_*.py"))
        if scripts_dir.is_dir():
            python_tests.extend(scripts_dir.glob("test_*.py"))
        pytest_configured = bool(python_tests) or any(
            (
                (self.root / "pytest.ini").is_file(),
                self.config_has_section(self.root / "pyproject.toml", "tool.pytest.ini_options"),
                self.config_has_section(self.root / "setup.cfg", "tool:pytest"),
                self.config_has_section(self.root / "tox.ini", "pytest"),
            )
        )
        if pytest_configured:
            commands.append([sys.executable, "-m", "pytest", "-x", "-q"])

        makefile = self.root / "Makefile"
        if makefile.is_file():
            try:
                make_text = makefile.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                make_text = ""
            if re.search(r"^test\s*:", make_text, re.MULTILINE):
                commands.append(["make", "test"])
        if self.package_script("test"):
            commands.append(["npm", "test"])
        if (self.root / "Cargo.toml").is_file():
            commands.append(["cargo", "test"])
        return commands

    def configured_lint_commands(self) -> List[List[str]]:
        """Discover linters from checked-in configuration, not executable presence."""
        commands: List[List[str]] = []
        if (
            (self.root / "ruff.toml").is_file()
            or (self.root / ".ruff.toml").is_file()
            or self.config_has_section(self.root / "pyproject.toml", "tool.ruff")
        ):
            commands.append(["ruff", "check", "."])
        if (
            (self.root / "mypy.ini").is_file()
            or (self.root / ".mypy.ini").is_file()
            or self.config_has_section(self.root / "pyproject.toml", "tool.mypy")
            or self.config_has_section(self.root / "setup.cfg", "mypy")
        ):
            commands.append(["mypy", "."])
        if (
            (self.root / ".flake8").is_file()
            or self.config_has_section(self.root / "setup.cfg", "flake8")
            or self.config_has_section(self.root / "tox.ini", "flake8")
        ):
            commands.append(["flake8", "."])
        if self.package_script("lint"):
            commands.append(["npm", "run", "lint"])
        return commands

    def check_tests(self) -> bool:
        """Run test suite."""
        print("🧪 Running tests...")
        test_commands = self.configured_test_commands()
        if not test_commands:
            self.failures.append(
                "Tests NOT_CONFIGURED: no test files, runner configuration, or declared test target found"
            )
            return False

        passed = True
        for cmd in test_commands:
            code, out, err = self.run_cmd(cmd)
            if code == 0:
                print(f"  ✓ Tests passed ({' '.join(cmd)})")
            elif code == -1:
                self.failures.append(
                    f"Tests NOT_CONFIGURED: configured runner {' '.join(cmd)} is unavailable: {err or out}"
                )
                passed = False
            else:
                self.failures.append(f"Tests failed: {err or out}")
                passed = False
        return passed

    def check_static_analysis(self) -> bool:
        """Run static analysis/linting."""
        print("🔍 Running static analysis...")
        lint_commands = self.configured_lint_commands()
        if not lint_commands:
            self.failures.append(
                "Static analysis NOT_CONFIGURED: no checked-in linter configuration or lint target found"
            )
            return False

        passed = True
        for cmd in lint_commands:
            code, out, err = self.run_cmd(cmd)
            if code == 0:
                print(f"  ✓ {' '.join(cmd)} passed")
            elif code == -1:
                self.failures.append(
                    f"Static analysis NOT_CONFIGURED: configured linter {' '.join(cmd)} is unavailable: {err or out}"
                )
                passed = False
            else:
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
        """Validate evidence selected by exact slice/head manifest fields."""
        print("📦 Checking evidence...")
        if not self.slice_id:
            self.failures.append(
                "Evidence NOT_CONFIGURED: --slice-id is required; global evidence history is not current-slice proof"
            )
            return False
        code, out, err = self.run_cmd(["git", "rev-parse", "HEAD"])
        if code != 0 or not out.strip():
            self.failures.append(f"Evidence check could not determine current HEAD: {err or out}")
            return False
        current_head = out.strip().lower()
        expected_head = (self.expected_head or current_head).lower()
        if expected_head != current_head:
            self.failures.append(
                f"Evidence head mismatch: expected {expected_head}, current repository is {current_head}"
            )
            return False
        try:
            bundle = load_evidence_bundle(
                self.root,
                self.slice_id,
                expected_head,
                evidence_dir=self.evidence_dir,
                privacy_profile=self.privacy_profile,
            )
        except ArtifactContractError as exc:
            self.failures.append(f"Evidence contract failed: {exc}")
            return False
        try:
            label = bundle.manifest_path.relative_to(self.root).as_posix()
        except ValueError:
            label = bundle.manifest_path.as_posix()
        print(f"  ✓ Exact-slice evidence contract valid ({label})")
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
    parser.add_argument("--slice-id", help="Exact backlog slice identity for evidence selection")
    parser.add_argument("--head", help="Expected exact commit; defaults to current HEAD")
    parser.add_argument("--evidence-dir", help="Explicit evidence bundle directory")
    parser.add_argument(
        "--privacy-profile",
        choices=["public", "private", "local_only"],
        default="public",
        help="Required evidence privacy profile",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    gate = QualityGate(
        root,
        args.verbose,
        args.gate_level,
        slice_id=args.slice_id,
        expected_head=args.head,
        evidence_dir=Path(args.evidence_dir) if args.evidence_dir else None,
        privacy_profile=args.privacy_profile,
    )
    sys.exit(gate.run())


if __name__ == "__main__":
    main()
