#!/usr/bin/env python3
"""
StateDD Efficiency Check

Enforces the Efficiency Invariant and EFFICIENCY_BUDGET.yaml.
Fails on instruction bloat, duplicate canonical sources, unreferenced
skills/commands, oversized evidence bundles, bloated active queues,
and workflows that demand heavy gates without declaring a gate level.

Exit codes: 0=pass, 1=fail, 2=error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a project dependency
    yaml = None


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    severity: Severity
    check: str
    message: str
    file: Optional[str] = None


class EfficiencyCheck:
    BUDGET_FILE = "EFFICIENCY_BUDGET.yaml"
    INSTRUCTION_SHIMS = {"AGENTS.md", "CLAUDE.md", "GEMINI.md", "Copilot.md"}
    FULL_GATE_PHRASES = ["run all checks", "full pipeline", "full gate", "run everything"]

    def __init__(self, root: Path, gate_level: int = 1, verbose: bool = False):
        self.root = root
        self.gate_level = gate_level
        self.verbose = verbose
        self.findings: list[Finding] = []
        self.budget: dict[str, Any] = {}

    def _log(self, severity: Severity, check: str, message: str, file: Optional[str] = None) -> None:
        finding = Finding(severity, check, message, file)
        self.findings.append(finding)
        if self.verbose:
            prefix = "❌" if severity == Severity.ERROR else "⚠️"
            suffix = f" ({file})" if file else ""
            print(f"{prefix} [{check}] {message}{suffix}", file=sys.stderr)

    def load_budget(self) -> bool:
        path = self.root / self.BUDGET_FILE
        if not path.exists():
            self._log(Severity.ERROR, "budget", f"{self.BUDGET_FILE} not found")
            return False
        if yaml is None:
            self._log(Severity.ERROR, "budget", "PyYAML not installed; cannot parse budget")
            return False
        try:
            self.budget = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            self._log(Severity.ERROR, "budget", f"Failed to parse {self.BUDGET_FILE}: {exc}")
            return False
        return True

    def _budget(self, *keys: str, default: Any = None) -> Any:
        value: Any = self.budget
        for key in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(key, default)
        return value

    def _line_count(self, path: Path) -> int:
        return len(path.read_text(encoding="utf-8").splitlines())

    def _is_fixture_path(self, rel: Path) -> bool:
        return rel.parts and rel.parts[0] == "fixtures"

    def check_instruction_sizes(self) -> None:
        budgets = self._budget("instruction_budgets", default={})
        root_agents = self.root / "AGENTS.md"
        if root_agents.exists():
            lines = self._line_count(root_agents)
            max_lines = budgets.get("root_agents_max_lines", 100)
            if lines > max_lines:
                self._log(
                    Severity.ERROR,
                    "instruction_size",
                    f"root AGENTS.md has {lines} lines, max {max_lines}",
                    "AGENTS.md",
                )

        max_nested = budgets.get("nested_agents_max_lines", 80)
        for path in self.root.rglob("AGENTS.md"):
            rel = path.relative_to(self.root)
            if rel == Path("AGENTS.md") or self._is_fixture_path(rel):
                continue
            lines = self._line_count(path)
            if lines > max_nested:
                self._log(
                    Severity.ERROR,
                    "instruction_size",
                    f"nested {rel} has {lines} lines, max {max_nested}",
                    str(rel),
                )

        max_skill = budgets.get("skill_max_lines", 180)
        for path in self.root.glob("skills/*/SKILL.md"):
            rel = path.relative_to(self.root)
            if self._is_fixture_path(rel):
                continue
            lines = self._line_count(path)
            if lines > max_skill:
                self._log(
                    Severity.ERROR,
                    "instruction_size",
                    f"{rel} has {lines} lines, max {max_skill}",
                    str(rel),
                )

        max_command = budgets.get("command_max_lines", 120)
        for path in self.root.glob("commands/*.md"):
            rel = path.relative_to(self.root)
            if self._is_fixture_path(rel):
                continue
            lines = self._line_count(path)
            if lines > max_command:
                self._log(
                    Severity.ERROR,
                    "instruction_size",
                    f"{rel} has {lines} lines, max {max_command}",
                    str(rel),
                )

        max_prompt = budgets.get("prompt_max_lines", 250)
        for path in self.root.glob("prompts/*.md"):
            rel = path.relative_to(self.root)
            if self._is_fixture_path(rel):
                continue
            lines = self._line_count(path)
            if lines > max_prompt:
                self._log(
                    Severity.ERROR,
                    "instruction_size",
                    f"{rel} has {lines} lines, max {max_prompt}",
                    str(rel),
                )

    def _substantive_lines(self, path: Path) -> set[str]:
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2]
        lines: set[str] = set()
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            if line.startswith(("- ", "* ", "1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. ")):
                continue
            if len(line) < 25:
                continue
            lines.add(line.lower())
        return lines

    def check_duplicate_instructions(self) -> None:
        if not self._budget("anti_bloat_rules", "no_duplicate_instruction_files"):
            return
        max_dup = self._budget("instruction_budgets", "duplicate_instruction_max_lines", default=5)
        shims = [self.root / name for name in self.INSTRUCTION_SHIMS if (self.root / name).exists()]
        if len(shims) < 2:
            return
        sets = {p: self._substantive_lines(p) for p in shims}
        for i, p1 in enumerate(shims):
            for p2 in shims[i + 1 :]:
                common = sets[p1] & sets[p2]
                if len(common) > max_dup:
                    rel1 = p1.relative_to(self.root)
                    rel2 = p2.relative_to(self.root)
                    self._log(
                        Severity.ERROR,
                        "duplicate_instructions",
                        f"{rel1} and {rel2} share {len(common)} substantive lines (max {max_dup})",
                        f"{rel1},{rel2}",
                    )

    def _parse_frontmatter(self, text: str) -> dict[str, Any]:
        if not text.startswith("---"):
            return {}
        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}
        if yaml is None:
            return {}
        try:
            return yaml.safe_load(parts[1]) or {}
        except Exception:
            return {}

    def _reference_corpus(self, *extra: Path) -> str:
        parts: list[str] = []
        for src in [self.root / "AGENTS.md", self.root / "README.md", *extra]:
            if src.exists():
                parts.append(src.read_text(encoding="utf-8"))
        for cmd in self.root.glob("commands/*.md"):
            parts.append(cmd.read_text(encoding="utf-8"))
        return "\n".join(parts)

    def check_unreferenced_skills_commands(self) -> None:
        if not self._budget("anti_bloat_rules", "no_unreferenced_skills"):
            return
        corpus = self._reference_corpus()
        for skill_path in self.root.glob("skills/*"):
            if not skill_path.is_dir():
                continue
            rel = skill_path.relative_to(self.root)
            if self._is_fixture_path(rel):
                continue
            name = skill_path.name
            skill_file = skill_path / "SKILL.md"
            if not skill_file.exists():
                continue
            if name not in corpus:
                self._log(
                    Severity.WARNING,
                    "unreferenced_skill",
                    f"Skill '{name}' not referenced in AGENTS.md, README.md, or commands",
                    str(skill_file.relative_to(self.root)),
                )

        root_corpus = ""
        for src in [self.root / "AGENTS.md", self.root / "README.md"]:
            if src.exists():
                root_corpus += src.read_text(encoding="utf-8") + "\n"
        for cmd_path in self.root.glob("commands/*.md"):
            rel = cmd_path.relative_to(self.root)
            if self._is_fixture_path(rel):
                continue
            text = cmd_path.read_text(encoding="utf-8")
            front = self._parse_frontmatter(text)
            name = front.get("command") or cmd_path.stem
            if name not in root_corpus:
                self._log(
                    Severity.WARNING,
                    "unreferenced_command",
                    f"Command '{name}' not referenced in AGENTS.md or README.md",
                    str(cmd_path.relative_to(self.root)),
                )

    def _count_skill_steps(self, text: str) -> int:
        match = re.search(r"^step_by_step:\s*\n([\s\S]*?)(?=^\S|\Z)", text, re.MULTILINE)
        if not match:
            return 0
        return len(re.findall(r"^  - name:", match.group(1), re.MULTILINE))

    def check_workflow_gate_levels(self) -> None:
        max_steps = self._budget("instruction_budgets", "max_steps_per_workflow", default=8)
        for skill_path in self.root.glob("skills/*/SKILL.md"):
            text = skill_path.read_text(encoding="utf-8")
            rel = skill_path.relative_to(self.root)
            if self._is_fixture_path(rel):
                continue
            front = self._parse_frontmatter(text)
            if "gate_level" not in front:
                self._log(
                    Severity.ERROR,
                    "workflow_gate_level",
                    f"{rel} missing gate_level in frontmatter",
                    str(rel),
                )
            steps = self._count_skill_steps(text)
            if steps > max_steps:
                self._log(
                    Severity.ERROR,
                    "workflow_steps",
                    f"{rel} has {steps} steps, max {max_steps}",
                    str(rel),
                )
            lower = text.lower()
            if any(phrase in lower for phrase in self.FULL_GATE_PHRASES):
                level = front.get("gate_level")
                if level is None or int(level) <= 1:
                    self._log(
                        Severity.ERROR,
                        "workflow_full_gate",
                        f"{rel} says 'run all checks/full pipeline' but gate_level is {level} (must be ≥ 2)",
                        str(rel),
                    )

        for cmd_path in self.root.glob("commands/*.md"):
            text = cmd_path.read_text(encoding="utf-8")
            rel = cmd_path.relative_to(self.root)
            if self._is_fixture_path(rel):
                continue
            front = self._parse_frontmatter(text)
            if "gate_level" not in front:
                self._log(
                    Severity.ERROR,
                    "workflow_gate_level",
                    f"{rel} missing gate_level in frontmatter",
                    str(rel),
                )
            steps = len(re.findall(r"^\d+\.", text, re.MULTILINE))
            if steps > max_steps:
                self._log(
                    Severity.ERROR,
                    "workflow_steps",
                    f"{rel} has {steps} steps, max {max_steps}",
                    str(rel),
                )
            lower = text.lower()
            if any(phrase in lower for phrase in self.FULL_GATE_PHRASES):
                level = front.get("gate_level")
                if level is None or int(level) <= 1:
                    self._log(
                        Severity.ERROR,
                        "workflow_full_gate",
                        f"{rel} says 'run all checks/full pipeline' but gate_level is {level} (must be ≥ 2)",
                        str(rel),
                    )

    def check_active_queues(self) -> None:
        state_budgets = self._budget("state_budgets", default={})
        next_actions = self.root / "NEXT_ACTIONS.md"
        if next_actions.exists():
            text = next_actions.read_text(encoding="utf-8")
            active = re.findall(r"^###\s+", text, re.MULTILINE)
            max_active = state_budgets.get("active_next_actions_max", 5)
            if len(active) > max_active:
                self._log(
                    Severity.ERROR,
                    "active_queue",
                    f"NEXT_ACTIONS.md has {len(active)} active items, max {max_active}",
                    "NEXT_ACTIONS.md",
                )

        backlog = self.root / "BACKLOG.md"
        if backlog.exists():
            text = backlog.read_text(encoding="utf-8")
            match = re.search(r"^##\s+NOW\s*$([\s\S]*?)(?=^##\s|\Z)", text, re.MULTILINE)
            if match:
                section = match.group(1)
                items = re.findall(r"^- ", section, re.MULTILINE)
                max_now = state_budgets.get("active_backlog_items_max", 12)
                if len(items) > max_now:
                    self._log(
                        Severity.ERROR,
                        "active_queue",
                        f"BACKLOG.md NOW has {len(items)} items, max {max_now}",
                        "BACKLOG.md",
                    )

    def check_evidence_budget(self) -> None:
        evidence_root = self.root / "docs" / "evidence"
        if not evidence_root.exists():
            return
        budgets = self._budget("evidence_budgets", default={})
        default_max = budgets.get("default_max_files", 5)
        candidates = [
            entry
            for entry in evidence_root.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        ]
        if not candidates:
            return
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        files = [p for p in latest.rglob("*") if p.is_file()]
        if len(files) > default_max:
            self._log(
                Severity.ERROR,
                "evidence_bundle",
                f"Evidence folder {latest.name} has {len(files)} files, max {default_max}",
                str(latest.relative_to(self.root)),
            )

    def check_single_file_edit_audit(self) -> None:
        if not self._budget("anti_bloat_rules", "no_full_repo_audit_for_single_file_edit"):
            return
        for cmd_path in self.root.glob("commands/*.md"):
            rel = cmd_path.relative_to(self.root)
            if self._is_fixture_path(rel):
                continue
            text = cmd_path.read_text(encoding="utf-8").lower()
            if "single file" in text or "minor edit" in text or "one file" in text:
                if any(phrase in text for phrase in self.FULL_GATE_PHRASES):
                    self._log(
                        Severity.ERROR,
                        "audit_escalation",
                        f"{rel} tells user to run a full gate for a single-file/minor edit",
                        str(rel),
                    )

    def run(self) -> tuple[int, list[Finding]]:
        if not self.load_budget():
            return 1, self.findings
        self.check_instruction_sizes()
        self.check_duplicate_instructions()
        self.check_unreferenced_skills_commands()
        self.check_workflow_gate_levels()
        self.check_active_queues()
        self.check_evidence_budget()
        self.check_single_file_edit_audit()
        errors = [f for f in self.findings if f.severity == Severity.ERROR]
        return (0 if not errors else 1), self.findings

    def report(self) -> str:
        lines = ["=" * 50, "StateDD Efficiency Check", "=" * 50, ""]
        lines.append(f"Gate level: {self.gate_level}")
        lines.append(f"Budget file: {self.BUDGET_FILE}")
        lines.append("")
        if not self.findings:
            lines.append("✅ All efficiency checks passed")
            return "\n".join(lines)
        by_check: dict[str, list[Finding]] = {}
        for f in self.findings:
            by_check.setdefault(f.check, []).append(f)
        for check, fs in sorted(by_check.items()):
            lines.append(f"## {check}")
            for f in fs:
                sev = f.severity.value.upper()
                suffix = f"  ({f.file})" if f.file else ""
                lines.append(f"  [{sev}] {f.message}{suffix}")
            lines.append("")
        errors = sum(1 for f in self.findings if f.severity == Severity.ERROR)
        warnings = sum(1 for f in self.findings if f.severity == Severity.WARNING)
        lines.append(f"Summary: {errors} error(s), {warnings} warning(s)")
        return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="StateDD Efficiency Check")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--gate-level", type=int, default=1, help="Gate level being proven")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output JSON findings")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "info"],
        default="error",
        help="Minimum severity to fail",
    )
    args = parser.parse_args(argv or sys.argv[1:])

    root = Path(args.root).resolve()
    checker = EfficiencyCheck(root, args.gate_level, args.verbose)
    exit_code, findings = checker.run()

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "severity": f.severity.value,
                        "check": f.check,
                        "message": f.message,
                        "file": f.file,
                    }
                    for f in findings
                ],
                indent=2,
            )
        )
    else:
        print(checker.report())

    if args.fail_on in ("warning", "info"):
        if any(f.severity == Severity.WARNING for f in findings):
            exit_code = 1
    if args.fail_on == "info":
        if any(f.severity == Severity.INFO for f in findings):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
