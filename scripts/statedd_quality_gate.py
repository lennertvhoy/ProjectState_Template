#!/usr/bin/env python3
"""
StateDD Quality Gate

Post-slice quality gate: verify all tests pass, static analysis clean,
state files updated, and new evidence recorded.
Exit codes: 0=pass, 1=fail, 2=error
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional

try:
    from statedd_contracts import (
        ContractError,
        UnsafePathError,
        VALIDATION_REQUIREMENTS,
        confined_path,
        load_json_file,
    )
    from statedd_validate_schema import StateDDYamlError, parse_yaml_text
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.statedd_contracts import (
        ContractError,
        UnsafePathError,
        VALIDATION_REQUIREMENTS,
        confined_path,
        load_json_file,
    )
    from scripts.statedd_validate_schema import StateDDYamlError, parse_yaml_text


class QualityGate:
    def __init__(
        self,
        root: Path,
        verbose: bool = False,
        gate_level: int = 1,
        conformance: bool = False,
        runtime_endpoint: str | None = None,
        allow_remote_runtime: bool = False,
    ):
        self.root = root
        self.verbose = verbose
        self.gate_level = gate_level
        self.conformance = conformance
        self.runtime_endpoint = runtime_endpoint
        self.allow_remote_runtime = allow_remote_runtime
        self.failures: List[str] = []
        self.warnings: List[str] = []

    @staticmethod
    def command_output(stdout: str, stderr: str) -> str:
        parts = []
        if stdout.strip():
            parts.append("stdout:\n" + stdout.strip())
        if stderr.strip():
            parts.append("stderr:\n" + stderr.strip())
        return "\n".join(parts) or "no output"

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

    def is_template_repository(self) -> bool:
        state_path = self.root / "PROJECT_STATE.yaml"
        if not state_path.exists():
            return False
        try:
            payload = parse_yaml_text(state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, StateDDYamlError):
            return False
        workflow = payload.get("workflow") if isinstance(payload, dict) else None
        return isinstance(workflow, dict) and workflow.get("repo_role") == "template_repository"

    def check_tests(self) -> bool:
        """Run every applicable declared test suite and aggregate failures."""
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
        has_pytest_config = (self.root / "pytest.ini").exists()
        if pyproject.exists():
            has_pytest_config = has_pytest_config or "[tool.pytest" in pyproject.read_text(
                encoding="utf-8", errors="ignore"
            )
        setup_cfg = self.root / "setup.cfg"
        if setup_cfg.exists():
            has_pytest_config = has_pytest_config or "[tool:pytest]" in setup_cfg.read_text(
                encoding="utf-8", errors="ignore"
            )
        if pytest_tests or has_pytest_config:
            pytest_scope = ["scripts/"] if self.is_template_repository() else []
            test_commands.append([sys.executable, "-m", "pytest", *pytest_scope, "-q"])
            if self.is_template_repository() and (self.root / "schemas" / "examples").is_dir():
                test_commands.append(
                    [sys.executable, "-m", "pytest", "schemas/examples/", "-q"]
                )

        makefile = self.root / "Makefile"
        if makefile.exists() and re.search(
            r"(?m)^[^#\n]*\btest\s*:", makefile.read_text(encoding="utf-8", errors="ignore")
        ):
            test_commands.append(["make", "test"])

        package_json = self.root / "package.json"
        configuration_ok = True
        if package_json.exists():
            try:
                package = load_json_file(package_json)
            except ContractError as exc:
                self.failures.append(f"Cannot inspect declared npm tests: package.json is invalid: {exc}")
                package = None
                configuration_ok = False
            scripts = package.get("scripts") if isinstance(package, dict) else None
            if isinstance(scripts, dict) and isinstance(scripts.get("test"), str):
                test_commands.append(["npm", "test"])

        if (self.root / "Cargo.toml").exists():
            test_commands.append(["cargo", "test"])
        tox_ini = self.root / "tox.ini"
        if tox_ini.exists() and "[tox]" in tox_ini.read_text(encoding="utf-8", errors="ignore"):
            test_commands.append(["tox"])

        if not test_commands:
            self.warnings.append("No project test command detected")
            return configuration_ok

        passed = configuration_ok
        for cmd in test_commands:
            code, out, err = self.run_cmd(cmd)
            if code == 0:
                print(f"  ✓ Tests passed ({' '.join(cmd)})")
                continue
            command = " ".join(cmd)
            detail = self.command_output(out, err)
            if code == -1:
                self.failures.append(f"Declared test runner unavailable or could not start ({command}): {detail}")
            else:
                self.failures.append(f"Test suite failed ({command}, exit {code}):\n{detail}")
            passed = False
        return passed

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
        setup_cfg_text = (self.root / "setup.cfg").read_text(
            encoding="utf-8", errors="ignore"
        ) if (self.root / "setup.cfg").exists() else ""
        if (self.root / ".flake8").exists() or "[flake8]" in setup_cfg_text:
            lint_commands.append(["flake8", "."])
        if not lint_commands:
            self.warnings.append("No configured static-analysis command detected")
            return True
        passed = True
        for cmd in lint_commands:
            code, out, err = self.run_cmd(cmd)
            if code == 0:
                print(f"  ✓ {cmd[0]} passed")
            elif code == -1:
                self.failures.append(
                    f"Configured static-analysis runner unavailable ({cmd[0]}): "
                    f"{self.command_output(out, err)}"
                )
                passed = False
            else:
                self.failures.append(f"{cmd[0]} failed: {self.command_output(out, err)}")
                passed = False
        return passed

    def check_compile(self) -> bool:
        """Compile all present Python source trees through automatic discovery."""
        print("🧩 Compiling Python sources...")
        roots = [name for name in ("scripts", "schemas/examples") if (self.root / name).exists()]
        if not roots:
            self.warnings.append("No Python source tree detected for compileall")
            return True
        code, out, err = self.run_cmd([sys.executable, "-m", "compileall", "-q", *roots])
        if code == 0:
            print("  ✓ Python sources compile")
            return True
        self.failures.append(f"Python compileall failed: {self.command_output(out, err)}")
        return False

    def check_profile_policy(self) -> bool:
        """Require at least the gate level declared by a resolved downstream lock."""
        manifest = self.root / "STATEDD_ASSETS.json"
        if not manifest.exists():
            return True
        try:
            payload = load_json_file(manifest)
        except ContractError as exc:
            self.failures.append(f"Cannot enforce profile policy: invalid STATEDD_ASSETS.json: {exc}")
            return False
        if not isinstance(payload, dict) or payload.get("schema") != "statedd.runtime_assets.v2":
            return True
        required = payload.get("required_gate_level")
        profile = payload.get("profile")
        if isinstance(required, bool) or not isinstance(required, int):
            self.failures.append("Cannot enforce profile policy: required_gate_level is missing or invalid")
            return False
        if self.gate_level < required:
            self.failures.append(
                f"Profile {profile!r} requires gate level {required}; requested level is {self.gate_level}"
            )
            return False
        print(f"  ✓ Profile policy permits gate level {self.gate_level}")
        return True

    def check_profile_validations(self) -> bool:
        """Dispatch every validation contract recorded by a generated profile lock."""
        manifest = self.root / "STATEDD_ASSETS.json"
        if not manifest.exists():
            return True
        try:
            payload = load_json_file(manifest)
        except ContractError as exc:
            self.failures.append(f"Cannot dispatch profile validations: invalid lock: {exc}")
            return False
        if not isinstance(payload, dict) or payload.get("schema") != "statedd.runtime_assets.v2":
            return True
        validations = payload.get("validations")
        if (
            not isinstance(validations, list)
            or not validations
            or not all(isinstance(item, str) and item for item in validations)
            or len(validations) != len(set(validations))
        ):
            self.failures.append("Profile lock validations must be a unique non-empty string list")
            return False
        unknown = sorted(set(validations) - set(VALIDATION_REQUIREMENTS))
        if unknown:
            self.failures.append(f"Profile lock contains unknown validation IDs: {unknown}")
            return False

        passed = True
        for validation_id in validations:
            requirement = VALIDATION_REQUIREMENTS[validation_id]
            minimum = requirement.get("minimum_gate_level")
            if isinstance(minimum, int) and self.gate_level < minimum:
                self.failures.append(
                    f"Validation {validation_id!r} requires gate level {minimum}; "
                    f"requested level is {self.gate_level}"
                )
                passed = False
            for raw_path in requirement.get("required_paths", ()):
                try:
                    path = confined_path(self.root, raw_path)
                except UnsafePathError as exc:
                    self.failures.append(
                        f"Validation {validation_id!r} has unsafe required path {raw_path!r}: {exc}"
                    )
                    passed = False
                    continue
                if path.is_symlink() or not path.is_file():
                    self.failures.append(
                        f"Validation {validation_id!r} requires regular asset {raw_path}"
                    )
                    passed = False
        if passed:
            print(f"  ✓ Dispatched {len(validations)} profile validation contract(s)")
        return passed

    def check_profile_metrics(self) -> bool:
        """Reproduce the canonical template metrics artifact when applicable."""
        if not self.is_template_repository():
            return True
        artifact = self.root / "docs" / "metrics" / "profile_metrics.json"
        generator = self.root / "scripts" / "statedd_profile_metrics.py"
        if not artifact.is_file() or not generator.is_file():
            self.failures.append("Template repository is missing canonical reproducible profile metrics")
            return False
        print("📏 Reproducing profile metrics...")
        code, out, err = self.run_cmd([sys.executable, str(generator), "--root", str(self.root), "--check"])
        if code == 0:
            print("  ✓ Profile/context metrics reproduce from their recorded proof commit")
            return True
        self.failures.append(f"Profile metrics drift: {self.command_output(out, err)}")
        return False

    def check_state_files(self) -> bool:
        """Validate state files with check_state_docs.py."""
        print("📋 Validating state files...")
        code, out, err = self.run_cmd([sys.executable, "scripts/check_state_docs.py"])
        if code == 0:
            print("  ✓ State files valid")
            return True
        else:
            self.failures.append(f"State validation failed: {self.command_output(out, err)}")
            return False

    def check_schemas(self) -> bool:
        """Validate YAML/JSON against schemas."""
        print("📐 Validating schemas...")
        code, out, err = self.run_cmd([sys.executable, "scripts/statedd_validate_schema.py"])
        if code == 0:
            print("  ✓ Schemas valid")
            return True
        else:
            self.failures.append(f"Schema validation failed: {self.command_output(out, err)}")
            return False

    def check_runtime_truth(self, evidence_folder: Path) -> bool:
        """Re-probe the exact runtime artifact selected by the active slice."""
        artifact = evidence_folder / "runtime_identity.json"
        if not artifact.is_file():
            self.failures.append(
                f"Gate level {self.gate_level} requires {artifact.relative_to(self.root)}"
            )
            return False
        try:
            payload = load_json_file(artifact)
        except ContractError as exc:
            self.failures.append(f"Runtime identity is invalid: {exc}")
            return False
        runtime = payload.get("runtime") if isinstance(payload, dict) else None
        required = runtime.get("required") if isinstance(runtime, dict) else None
        command = [
            sys.executable,
            "scripts/statedd_runtime_truth_check.py",
            "--artifact",
            str(artifact.relative_to(self.root)),
        ]
        if required is True:
            if not self.runtime_endpoint:
                self.failures.append(
                    "Runtime-required gate needs --runtime-endpoint from trusted configuration"
                )
                return False
            command.extend(["--expected-endpoint", self.runtime_endpoint])
            if self.allow_remote_runtime:
                command.append("--allow-remote")
        code, out, err = self.run_cmd(command)
        if code != 0:
            self.failures.append(f"Runtime truth check failed:\n{self.command_output(out, err)}")
            return False
        print(f"  ✓ Runtime truth checked ({artifact.relative_to(self.root)})")
        return True

    def check_evidence(self) -> bool:
        """Use cheap log proof at level 1 and a strict slice pack at level 2+."""
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
        if self.gate_level < 2:
            print("  ✓ Evidence log has content (level 1)")
            return True

        context_path = self.root / ".statedd" / "agent.context"
        if not context_path.exists():
            if self.conformance:
                self.warnings.append(
                    "Conformance mode: no active slice, so strict slice evidence is not applicable"
                )
                print("  ✓ Evidence log has content (conformance mode; no active slice)")
                return True
            self.failures.append(
                "Gate level 2 requires an active slice context and exactly one strict evidence pack; "
                "use --conformance only for clean template/profile validation"
            )
            return False
        try:
            context = load_json_file(context_path)
        except ContractError as exc:
            self.failures.append(f"Agent context is invalid: {exc}")
            return False
        slice_id = context.get("slice_id") if isinstance(context, dict) else None
        if not isinstance(slice_id, str) or not slice_id:
            self.failures.append("Agent context has no valid slice_id")
            return False

        matches: List[Path] = []
        evidence_root = self.root / "docs" / "evidence"
        manifests = evidence_root.glob("*/manifest.json") if evidence_root.exists() else []
        for manifest in manifests:
            try:
                payload = load_json_file(manifest)
            except ContractError:
                continue
            if isinstance(payload, dict) and payload.get("slice_id") == slice_id:
                matches.append(manifest.parent)
        if len(matches) != 1:
            self.failures.append(
                f"Gate level 2 requires exactly one evidence pack for {slice_id}; found {len(matches)}"
            )
            return False
        code, out, err = self.run_cmd(
            [sys.executable, "scripts/statedd_evidence_pack.py", "check", "--strict", str(matches[0])]
        )
        if code != 0:
            self.failures.append(
                f"Strict evidence pack validation failed:\n{self.command_output(out, err)}"
            )
            return False
        if not self.check_runtime_truth(matches[0]):
            return False
        print(f"  ✓ Strict evidence pack valid ({matches[0].relative_to(self.root)})")
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
        code, out, err = self.run_cmd([sys.executable, "scripts/statedd_instruction_lint.py", "--fail-on", "error"])
        if code == 0:
            print("  ✓ No instruction smells (errors)")
            return True
        else:
            self.failures.append(f"Instruction lint errors: {self.command_output(out, err)}")
            return False

    def check_efficiency(self) -> bool:
        """Run efficiency budget check."""
        print("⚡ Running efficiency check...")
        code, out, err = self.run_cmd(
            [sys.executable, "scripts/statedd_efficiency_check.py", "--gate-level", str(self.gate_level)]
        )
        if code == 0:
            print("  ✓ Efficiency check passed")
            return True
        self.failures.append(f"Efficiency check failed:\n{self.command_output(out, err)}")
        return False

    def check_diff_whitespace(self) -> bool:
        """Run git diff --check when the target is a Git worktree."""
        print("🧹 Checking diff whitespace...")
        if not (self.root / ".git").exists():
            self.warnings.append("Git diff check not applicable outside a Git worktree")
            return True
        code, out, err = self.run_cmd(["git", "diff", "--check", "HEAD"])
        if code == 0:
            print("  ✓ Git diff whitespace clean")
            return True
        self.failures.append(f"git diff --check failed: {self.command_output(out, err)}")
        return False

    def run(self) -> int:
        """Run all quality checks."""
        print("=" * 50)
        print("StateDD Quality Gate")
        if self.conformance:
            print("Mode: template/profile conformance — NOT SLICE CLOSURE")
        elif self.gate_level == 3:
            print("Mode: release preflight — NOT CI-VERIFIED RELEASE CLOSURE")
        print("=" * 50)

        checks = [
            ("Compile", self.check_compile),
            ("Profile Policy", self.check_profile_policy),
            ("Profile Validations", self.check_profile_validations),
            ("Profile Metrics", self.check_profile_metrics),
            ("Tests", self.check_tests),
            ("Static Analysis", self.check_static_analysis),
            ("State Files", self.check_state_files),
            ("Schemas", self.check_schemas),
            ("Evidence", self.check_evidence),
            ("Acceptance Freezes", self.check_acceptance_freezes),
            ("Instruction Lint", self.check_instruction_lint),
            ("Efficiency", self.check_efficiency),
            ("Diff Whitespace", self.check_diff_whitespace),
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
            print("❌ CONFORMANCE FAILED — NOT SLICE CLOSURE" if self.conformance else "❌ QUALITY GATE FAILED")
            return 1

        if self.conformance:
            print("✅ CONFORMANCE PASS — NOT SLICE CLOSURE")
        elif self.gate_level == 3:
            print("✅ RELEASE PREFLIGHT PASS — NOT CI-VERIFIED")
        else:
            print("✅ ALL QUALITY GATES PASSED")
        print("=" * 50)
        return 0


def main():
    parser = argparse.ArgumentParser(description="StateDD Quality Gate")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--gate-level", type=int, choices=range(0, 4), default=1, help="Gate level 0..3 being proven")
    parser.add_argument(
        "--conformance",
        action="store_true",
        help="Validate a clean template/profile without claiming slice evidence or closure",
    )
    parser.add_argument(
        "--runtime-endpoint",
        help="Trusted endpoint for a runtime-required level-2/3 evidence artifact",
    )
    parser.add_argument(
        "--allow-remote-runtime",
        action="store_true",
        help="Permit remote runtime re-probe when revision-header binding is present",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    gate = QualityGate(
        root,
        args.verbose,
        args.gate_level,
        args.conformance,
        args.runtime_endpoint,
        args.allow_remote_runtime,
    )
    sys.exit(gate.run())


if __name__ == "__main__":
    main()
