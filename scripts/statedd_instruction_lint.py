#!/usr/bin/env python3
"""
StateDD Instruction Linter

Detects configuration "smells" in AGENTS.md, SKILL.md, and command files:
- Context bloat: files exceeding line/token limits
- Conflicting instructions: contradictory rules
- Lint leakage: repeated lint rules across files
- Skill leakage: inline procedures that should be skills
- Missing failure cases: skills/commands without failure handling
- Outdated claims: stale URLs, versions, time-based statements
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class SmellType(Enum):
    CONTEXT_BLOAT = "context_bloat"
    CONFLICTING_INSTRUCTIONS = "conflicting_instructions"
    LINT_LEAKAGE = "lint_leakage"
    SKILL_LEAKAGE = "skill_leakage"
    MISSING_FAILURE_CASES = "missing_failure_cases"
    OUTDATED_CLAIMS = "outdated_claims"


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Smell:
    type: SmellType
    severity: Severity
    file: str
    line: int
    message: str
    suggestion: str = ""


@dataclass
class FileAnalysis:
    path: str
    lines: List[str]
    line_count: int
    word_count: int
    smells: List[Smell] = field(default_factory=list)


class InstructionLinter:
    def __init__(self, root: Path, max_lines: int = 180, max_words: int = 4000):
        self.root = root
        self.max_lines = max_lines
        self.max_words = max_words
        self.analyses: Dict[str, FileAnalysis] = {}
        self.all_smells: List[Smell] = []

        # Patterns for detection
        self.conflict_patterns = [
            (r"run browser test", r"skip browser test", "browser test"),
            (r"require.*browser", r"skip.*browser", "browser requirement"),
            (r"must.*verify", r"skip.*verif", "verification"),
            (r"no fake completeness", r"placeholder.*ok|mock.*ok|stub.*ok", "completeness"),
            (r"human override.*proceed", r"human override.*refuse", "override"),
        ]

        self.lint_leakage_keywords = [
            "run flake8", "run ruff", "run mypy", "run pylint",
            "run eslint", "run prettier", "run black", "run isort",
            "on every commit", "on every push", "pre-commit",
        ]

        self.skill_leakage_patterns = [
            r"step\s+\d+[:.]\s+run\s+\w+",
            r"step\s+\d+[:.]\s+execute\s+\w+",
            r"run\s+pytest\s+.*\s+and\s+then",
            r"then\s+run\s+",
            r"after that\s+,?\s*run\s+",
            r"finally\s+run\s+",
        ]

        self.failure_case_keywords = [
            "failure case", "failure cases", "if.*fail", "on failure",
            "error handling", "rollback", "retry", "fallback"
        ]

        self.outdated_claim_patterns = [
            r"202\d[-/]\d{1,2}[-/]\d{1,2}",  # dates
            r"version\s+\d+\.\d+\.\d+",  # versions
            r"latest\s+version",  # "latest" claims
            r"as of\s+202\d",  # "as of" dates
            r"github\.com/.*/blob/main/",  # main branch refs
        ]

        # Known skills to reference
        self.known_skills = [
            "close-slice", "ingest-bad-event", "failure-scan",
            "runtime-truth", "quality-gate"
        ]

    def find_files(self) -> List[Path]:
        """Find all instruction files to lint."""
        patterns = [
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "*.md",
        ]
        files = []
        for pattern in patterns:
            files.extend(self.root.rglob(pattern))
        # Filter to relevant files
        relevant = []
        for f in files:
            if f.is_file():
                rel = f.relative_to(self.root)
                # Include root AGENTS.md, skills, commands, prompts, docs
                if any(str(rel).startswith(p) for p in ["", "skills/", "commands/", "prompts/", "docs/", "scripts/"]):
                    if rel.name in {"AGENTS.md", "CLAUDE.md", "GEMINI.md"} or \
                       rel.suffix == ".md" and not str(rel).startswith(".git"):
                        relevant.append(f)
        return list(set(relevant))  # dedupe

    def analyze_file(self, path: Path) -> FileAnalysis:
        """Analyze a single file."""
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        words = len(content.split())

        analysis = FileAnalysis(
            path=str(path.relative_to(self.root)),
            lines=lines,
            line_count=len(lines),
            word_count=words,
        )

        # Run all checks
        self._check_context_bloat(analysis)
        self._check_conflicting_instructions(analysis)
        self._check_lint_leakage(analysis)
        self._check_skill_leakage(analysis)
        self._check_missing_failure_cases(analysis)
        self._check_outdated_claims(analysis)

        return analysis

    def _check_context_bloat(self, analysis: FileAnalysis):
        """Check for context bloat (too many lines/words)."""
        if analysis.line_count > self.max_lines:
            self._add_smell(analysis, Smell(
                type=SmellType.CONTEXT_BLOAT,
                severity=Severity.WARNING,
                file=analysis.path,
                line=analysis.line_count,
                message=f"File has {analysis.line_count} lines (limit: {self.max_lines})",
                suggestion=f"Split into smaller files or move procedures to skills/commands"
            ))
        if analysis.word_count > self.max_words:
            self._add_smell(analysis, Smell(
                type=SmellType.CONTEXT_BLOAT,
                severity=Severity.WARNING,
                file=analysis.path,
                line=analysis.line_count,
                message=f"File has ~{analysis.word_count} words (limit: {self.max_words})",
                suggestion="Move procedural content to skills/ or commands/"
            ))

    def _check_conflicting_instructions(self, analysis: FileAnalysis):
        """Check for contradictory rules in the same file."""
        content = "\n".join(analysis.lines).lower()
        for pat1, pat2, topic in self.conflict_patterns:
            if re.search(pat1, content) and re.search(pat2, content):
                # Find line numbers
                line1 = self._find_line(analysis.lines, pat1)
                line2 = self._find_line(analysis.lines, pat2)
                self._add_smell(analysis, Smell(
                    type=SmellType.CONFLICTING_INSTRUCTIONS,
                    severity=Severity.ERROR,
                    file=analysis.path,
                    line=max(line1, line2),
                    message=f"Conflicting instructions about {topic}: '{pat1}' vs '{pat2}'",
                    suggestion="Resolve contradiction; keep one authoritative rule"
                ))

    def _check_lint_leakage(self, analysis: FileAnalysis):
        """Check for repeated lint rules across files."""
        content = "\n".join(analysis.lines).lower()
        found = [kw for kw in self.lint_leakage_keywords if kw in content]
        if len(found) >= 2:
            # Check if this is the "lint rules" file itself
            if "lint" not in analysis.path.lower() and "quality" not in analysis.path.lower():
                self._add_smell(analysis, Smell(
                    type=SmellType.LINT_LEAKAGE,
                    severity=Severity.WARNING,
                    file=analysis.path,
                    line=self._find_line(analysis.lines, found[0]),
                    message=f"Lint rules repeated in instruction file: {', '.join(found[:3])}",
                    suggestion="Move lint configuration to CI config; reference it once in docs"
                ))

    def _check_skill_leakage(self, analysis: FileAnalysis):
        """Check for inline procedures that should be skills."""
        content = "\n".join(analysis.lines)
        for pattern in self.skill_leakage_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                for m in matches[:2]:  # limit reports
                    line = content[:m.start()].count("\n") + 1
                    self._add_smell(analysis, Smell(
                        type=SmellType.SKILL_LEAKAGE,
                        severity=Severity.WARNING,
                        file=analysis.path,
                        line=line,
                        message=f"Inline procedure detected (should be a skill): {m.group()[:80]}",
                        suggestion=f"Create skill in skills/<name>/SKILL.md and invoke via /<name>"
                    ))

    def _check_missing_failure_cases(self, analysis: FileAnalysis):
        """Check skills/commands for missing failure case handling."""
        if not (analysis.path.startswith("skills/") or analysis.path.startswith("commands/")):
            return
        content = "\n".join(analysis.lines).lower()
        has_failure = any(kw in content for kw in self.failure_case_keywords)
        if not has_failure:
            self._add_smell(analysis, Smell(
                type=SmellType.MISSING_FAILURE_CASES,
                severity=Severity.ERROR,
                file=analysis.path,
                line=analysis.line_count,
                message="Skill/command missing failure case handling",
                suggestion="Add 'failure_cases' section with: what fails, detection, recovery, evidence"
            ))

    def _check_outdated_claims(self, analysis: FileAnalysis):
        """Check for potentially stale claims."""
        content = "\n".join(analysis.lines)
        for pattern in self.outdated_claim_patterns:
            matches = list(re.finditer(pattern, content))
            for m in matches[:3]:
                line = content[:m.start()].count("\n") + 1
                self._add_smell(analysis, Smell(
                    type=SmellType.OUTDATED_CLAIMS,
                    severity=Severity.INFO,
                    file=analysis.path,
                    line=line,
                    message=f"Potentially outdated claim: {m.group()}",
                    suggestion="Verify current version/date/URL; mark as 'reported' or 'assumed' if unconfirmed"
                ))

    def _find_line(self, lines: List[str], pattern: str) -> int:
        """Find first line matching pattern (case-insensitive)."""
        pat = pattern.lower()
        for i, line in enumerate(lines):
            if pat in line.lower():
                return i + 1
        return 1

    def _add_smell(self, analysis: FileAnalysis, smell: Smell):
        analysis.smells.append(smell)
        self.all_smells.append(smell)

    def run(self) -> Tuple[int, List[Smell]]:
        """Run linter on all files."""
        files = self.find_files()
        for f in files:
            analysis = self.analyze_file(f)
            self.analyses[analysis.path] = analysis

        # Cross-file lint leakage check
        self._check_cross_file_lint_leakage()

        return len(self.all_smells), self.all_smells

    def _check_cross_file_lint_leakage(self):
        """Detect same lint rules mentioned in multiple files."""
        keyword_files: Dict[str, List[str]] = {}
        for analysis in self.analyses.values():
            content = "\n".join(analysis.lines).lower()
            for kw in self.lint_leakage_keywords:
                if kw in content:
                    keyword_files.setdefault(kw, []).append(analysis.path)

        for kw, files in keyword_files.items():
            if len(files) > 2:  # mentioned in 3+ files
                for f in files:
                    if f in self.analyses:
                        self._add_smell(self.analyses[f], Smell(
                            type=SmellType.LINT_LEAKAGE,
                            severity=Severity.WARNING,
                            file=f,
                            line=1,
                            message=f"Lint rule '{kw}' appears in {len(files)} files: {', '.join(files[:3])}",
                            suggestion="Centralize lint config in CI; reference once in docs"
                        ))

    def report(self) -> str:
        """Generate human-readable report."""
        if not self.all_smells:
            return "✓ No configuration smells detected."

        by_type: Dict[SmellType, List[Smell]] = {}
        for s in self.all_smells:
            by_type.setdefault(s.type, []).append(s)

        lines = [f"Found {len(self.all_smells)} configuration smell(s):\n"]
        for smell_type, smells in sorted(by_type.items(), key=lambda x: -len(x[1])):
            lines.append(f"## {smell_type.value.upper()} ({len(smells)})")
            for s in smells:
                sev = s.severity.value.upper()
                lines.append(f"  [{sev}] {s.file}:{s.line} - {s.message}")
                if s.suggestion:
                    lines.append(f"    → {s.suggestion}")
            lines.append("")

        # Summary
        error_count = sum(1 for s in self.all_smells if s.severity == Severity.ERROR)
        warning_count = sum(1 for s in self.all_smells if s.severity == Severity.WARNING)
        info_count = sum(1 for s in self.all_smells if s.severity == Severity.INFO)
        lines.append(f"Summary: {error_count} errors, {warning_count} warnings, {info_count} info")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="StateDD Instruction Linter")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--max-lines", type=int, default=180, help="Max lines per file")
    parser.add_argument("--max-words", type=int, default=4000, help="Max words per file")
    parser.add_argument("--fail-on", choices=["error", "warning", "info"], default="error",
                        help="Exit code threshold")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    linter = InstructionLinter(root, args.max_lines, args.max_words)
    count, smells = linter.run()

    if args.json:
        import json
        print(json.dumps([
            {
                "type": s.type.value,
                "severity": s.severity.value,
                "file": s.file,
                "line": s.line,
                "message": s.message,
                "suggestion": s.suggestion
            }
            for s in smells
        ], indent=2))
    else:
        print(linter.report())

    # Exit code logic
    threshold = {"error": Severity.ERROR, "warning": Severity.WARNING, "info": Severity.INFO}[args.fail_on]
    severities = [s.severity for s in smells]
    if any(s.value >= threshold.value for s in [Severity.ERROR, Severity.WARNING, Severity.INFO]
           if s in severities):
        # Check if any smell meets or exceeds threshold
        order = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}
        if any(order[s] >= order[threshold] for s in severities):
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()