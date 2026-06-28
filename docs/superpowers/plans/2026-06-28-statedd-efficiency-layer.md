# StateDD v5 Efficiency Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or implement manually task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a hard Efficiency Invariant to StateDD v5: tiered gate levels, an efficiency budget, an executable efficiency checker, and workflow metadata that prevents bureaucracy bloat.

**Architecture:** A new `EFFICIENCY_BUDGET.yaml` declares hard limits. `scripts/statedd_efficiency_check.py` reads it and enforces instruction size, duplicate-instruction, queue-length, evidence-bundle, and gate-level rules. Quality/closure gates call it. Skills/commands declare their gate level, cheapest proof, evidence max, and escalation rule in frontmatter.

**Tech Stack:** Python 3, PyYAML (already used), pytest.

---

## Task 1: Add Efficiency Invariant, Budget, and Handoff Fields

**Files:**
- Modify: `AGENTS.md`
- Create: `EFFICIENCY_BUDGET.yaml`
- Modify: `prompts/FINAL_HANDOFF_TEMPLATE.md`

- [ ] **Step 1: Replace `AGENTS.md` with the version below**

```markdown
---
repo_role: "template_repository"
statedd_mode: "template-maintenance"
repo_mode: "template-maintenance"
statedd_version: "statedd-template-v5"
initialized_on: 2026-04-26
last_updated: 2026-06-28
project: "StateDD_Template"
---

# StateDD v5 — Agent Operating System Constitution

**Purpose:** Minimal constitutional contract for AI agents. Procedural detail lives in `skills/`, `commands/`, and executable gates in `scripts/`.

## Agent Read Order
1. `AGENTS.md` (this file)
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `PROJECT_DNA.yaml`
5. `NEXT_ACTIONS.md`
6. Nearest nested `AGENTS.md` in working directory (nearest wins)

## Invariants (Non-Negotiable)
- No fake completeness — unverified claims = false
- User-facing behavior requires runtime identity proof (not screenshots alone)
- Browser verification required for user-facing closure (Kimi WebBridge preferred; fallback: Playwright, agent-native tools, manual)
- Negative searches stay negative: `not found`, `not currently locatable`, `not proven`
- Active queue stays short (`NEXT_ACTIONS.md` only)
- History → `WORKLOG.md` only; live state files stay machine-checkable
- End every session: handoff + hygiene check (`scripts/statedd_handoff.py`, `scripts/check_state_docs.py`)
- Implemented ≠ Validated ≠ Closure-grade ≠ Accepted
- Handoffs are claims until verified by evidence or independent gate
- Quality gates are executable, not prose (`scripts/statedd_quality_gate.py`)
- **Remote Truth Gate:** No implementation may be called complete unless:
  1. Repo identity proven with `pwd` + `git remote -v`
  2. Branch proven with `git branch --show-current`
  3. Changed files proven tracked with `git status --short` and `git ls-files`
  4. Final commit SHA proven with `git rev-parse HEAD`
  5. Remote contains that SHA with `git ls-remote origin <branch>`
  6. GitHub-visible files match claimed deliverables
  7. Final handoff states: `local-only` / `pushed` / `PR opened` / `merged` / `CI verified`
  Without this, every handoff must be labeled: `NOT CLOSURE-GRADE — LOCAL OR UNVERIFIED CLAIM`
- **Efficiency Invariant:** StateDD exists to reduce agent confusion and false closure, not to create bureaucracy. Every required file, gate, command, and evidence artifact must justify its cost. Prefer the smallest proof that crosses the relevant truth boundary.

## Gate Levels
Use the cheapest gate that honestly proves the current claim.

| Level | Name | When to use | Required proof |
|-------|------|-------------|----------------|
| 0 | Orientation | Starting or resuming | Read `AGENTS.md`, identify mode/current task; no full audit |
| 1 | Edit Loop | Single-file or non-runtime changes | Cheap tests, relevant lint; no evidence bundle unless runtime change |
| 2 | Slice Closure | Closing a slice | Quality gate, closure check, remote truth, evidence type check |
| 3 | Release / Template Migration | Deployment or migration | Full probes, compatibility shims, generated fixture checks, CI proof |

## Final v5 Invariant Set
No fake closure. No truth-boundary crossing without proof. No bureaucracy without measurable value. No full gate when a cheap gate proves the claim. No evidence dump when a small proof is enough. No duplicated instruction sources. No “done” unless GitHub-visible truth matches the handoff.

## Truth Boundary
The agent must always distinguish:
- Sandbox truth
- Local worktree truth
- Git index truth
- Local commit truth
- Remote branch truth
- GitHub main truth
- CI truth
- Runtime truth
- User-accepted truth

**Invariant:** No state transition may cross a truth boundary without proof.

## Modes
| Mode | Purpose | Repo Role |
|------|---------|-----------|
| `template-maintenance` | Maintain this template repo | Root template repo only |
| `bootstrap` | Discover truth, establish baseline | Downstream repos (initial) |
| `operating` | Steady-state delivery | Downstream repos (steady) |

Downstream repos **never** use `template-maintenance`.

## Subsystems (Load on Demand)
- **Skills** → `skills/<name>/SKILL.md` — executable workflows (load via `/skill-name`)
- **Commands** → `commands/statedd-*.md` — slash-command playbooks (invoke via `/statedd-*`)
- **Gates** → `scripts/statedd_*_gate.py`, `scripts/statedd_*_check.py` — executable quality gates
- **Docs** → `docs/` — reference (FAILURE_TAXONOMY, QUALITY_FIREWALL, INCIDENT_RESPONSE, failure_scans/, quality_gates/, adr/)
- **Schemas** → `schemas/` — machine-checkable contracts (YAML/JSON schemas)
- **Prompts** → `prompts/` — CTO/agent startup prompts, templates

## Human Override
Strong defaults, not a prison. Explicit human override = proceed, record tradeoff, mark `override-approved` in handoff. Decline only if destructive, illegal, unsafe, unrecoverable, or corrupts project truth.

## Hygiene Limits
- `STATUS.md` ≤ 120 lines
- `PROJECT_STATE.yaml` ≤ 900 lines
- `NEXT_ACTIONS.md` active only
- No roadmap prose in structured state
- No closed history in `STATUS.md`

## Handoff Requirements (Every Session)
Run `scripts/statedd_handoff.py` and include: changes, verification, repo path, branch, partial/risky items, git head, serving process/port, rebuild status, clean worktree, evidence refs, absolute evidence paths, next action, CTO-pasteable handoff text.
```

- [ ] **Step 2: Create `EFFICIENCY_BUDGET.yaml`**

```yaml
schema: statedd.efficiency_budget.v1
instruction_budgets:
  root_agents_max_lines: 110
  nested_agents_max_lines: 80
  skill_max_lines: 180
  command_max_lines: 120
  prompt_max_lines: 200
  duplicate_instruction_max_lines: 5
  max_steps_per_workflow: 8

state_budgets:
  active_next_actions_max: 5
  active_backlog_items_max: 12
  final_handoff_max_lines: 80

evidence_budgets:
  default_max_files: 5
  docs_only_max_files: 2
  runtime_change_min_files: 2
  runtime_change_max_files: 8

gate_budgets:
  edit_loop_target_seconds: 30
  closure_gate_target_seconds: 180
  release_gate_target_seconds: 600

anti_bloat_rules:
  no_duplicate_instruction_files: true
  no_more_than_one_canonical_source: true
  no_unreferenced_skills: true
  no_unbounded_evidence_dumps: true
  no_full_repo_audit_for_single_file_edit: true
```

- [ ] **Step 3: Insert two fields into `prompts/FINAL_HANDOFF_TEMPLATE.md`**

After the `failure_scan` line in the Slice contract block, add:

```text
- gate level used: 0 | 1 | 2 | 3
- efficiency budget result: pass | fail
```

- [ ] **Step 4: Verify line counts**

Run:

```bash
wc -l AGENTS.md EFFICIENCY_BUDGET.yaml prompts/FINAL_HANDOFF_TEMPLATE.md
```

Expected: AGENTS.md ≤ 110 lines, FINAL_HANDOFF_TEMPLATE.md ≤ 200 lines.

---

## Task 2: Implement `scripts/statedd_efficiency_check.py` and Tests

**Files:**
- Create: `scripts/statedd_efficiency_check.py`
- Create: `scripts/test_efficiency_check.py`
- Create: `fixtures/efficiency_bloat_overcorrection/README.md`
- Create: `fixtures/efficiency_bloat_overcorrection/AGENTS.md`
- Create: `fixtures/efficiency_bloat_overcorrection/CLAUDE.md`
- Create: `fixtures/efficiency_bloat_overcorrection/GEMINI.md`
- Create: `fixtures/efficiency_bloat_overcorrection/skills/bloat-skill/SKILL.md`
- Create: `fixtures/efficiency_bloat_overcorrection/commands/statedd-bloat-gate.md`
- Create: `fixtures/efficiency_bloat_overcorrection/NEXT_ACTIONS.md`
- Create: `fixtures/efficiency_bloat_overcorrection/BACKLOG.md`
- Create: `fixtures/efficiency_bloat_overcorrection/docs/evidence/2026-06-28-bloat/artifact1.txt`
- Create: `fixtures/efficiency_bloat_overcorrection/docs/evidence/2026-06-28-bloat/artifact2.txt`
- Create: `fixtures/efficiency_bloat_overcorrection/docs/evidence/2026-06-28-bloat/artifact3.txt`
- Create: `fixtures/efficiency_bloat_overcorrection/docs/evidence/2026-06-28-bloat/artifact4.txt`
- Create: `fixtures/efficiency_bloat_overcorrection/docs/evidence/2026-06-28-bloat/artifact5.txt`
- Create: `fixtures/efficiency_bloat_overcorrection/docs/evidence/2026-06-28-bloat/artifact6.txt`
- Create: `fixtures/efficiency_bloat_overcorrection/EFFICIENCY_BUDGET.yaml`

- [ ] **Step 1: Create `scripts/statedd_efficiency_check.py`**

```python
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
            if rel != Path("AGENTS.md"):
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
            lines = self._line_count(path)
            rel = path.relative_to(self.root)
            if lines > max_skill:
                self._log(
                    Severity.ERROR,
                    "instruction_size",
                    f"{rel} has {lines} lines, max {max_skill}",
                    str(rel),
                )

        max_command = budgets.get("command_max_lines", 120)
        for path in self.root.glob("commands/*.md"):
            lines = self._line_count(path)
            rel = path.relative_to(self.root)
            if lines > max_command:
                self._log(
                    Severity.ERROR,
                    "instruction_size",
                    f"{rel} has {lines} lines, max {max_command}",
                    str(rel),
                )

        max_prompt = budgets.get("prompt_max_lines", 250)
        for path in self.root.glob("prompts/*.md"):
            lines = self._line_count(path)
            rel = path.relative_to(self.root)
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

    def check_workflow_gate_levels(self) -> None:
        max_steps = self._budget("instruction_budgets", "max_steps_per_workflow", default=8)
        for skill_path in self.root.glob("skills/*/SKILL.md"):
            text = skill_path.read_text(encoding="utf-8")
            rel = skill_path.relative_to(self.root)
            front = self._parse_frontmatter(text)
            if "gate_level" not in front:
                self._log(
                    Severity.ERROR,
                    "workflow_gate_level",
                    f"{rel} missing gate_level in frontmatter",
                    str(rel),
                )
            steps = len(re.findall(r"^  - name:", text, re.MULTILINE))
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
            if re.search(r"^##\s+NOW", text, re.MULTILINE):
                section = re.split(r"^##\s+NOW", text, flags=re.MULTILINE)[-1]
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
        for folder in evidence_root.iterdir():
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            files = [p for p in folder.rglob("*") if p.is_file()]
            if len(files) > default_max:
                self._log(
                    Severity.ERROR,
                    "evidence_bundle",
                    f"Evidence folder {folder.name} has {len(files)} files, max {default_max}",
                    str(folder.relative_to(self.root)),
                )

    def check_single_file_edit_audit(self) -> None:
        if not self._budget("anti_bloat_rules", "no_full_repo_audit_for_single_file_edit"):
            return
        for cmd_path in self.root.glob("commands/*.md"):
            text = cmd_path.read_text(encoding="utf-8").lower()
            if "single file" in text or "minor edit" in text or "one file" in text:
                if any(phrase in text for phrase in self.FULL_GATE_PHRASES):
                    rel = cmd_path.relative_to(self.root)
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
```

- [ ] **Step 2: Create `scripts/test_efficiency_check.py`**

```python
#!/usr/bin/env python3
"""Tests for scripts/statedd_efficiency_check.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = ROOT / "scripts" / "statedd_efficiency_check.py"


def run_check(args: list[str], *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(
            f"Expected success for {args}, got {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not expect_success and completed.returncode == 0:
        raise AssertionError(
            f"Expected failure for {args}, got success\nstdout:\n{completed.stdout}"
        )
    return completed


def write_budget(root: Path, **overrides: int) -> None:
    defaults = {
        "schema": "statedd.efficiency_budget.v1",
        "instruction_budgets": {
            "root_agents_max_lines": 100,
            "nested_agents_max_lines": 80,
            "skill_max_lines": 180,
            "command_max_lines": 120,
            "prompt_max_lines": 250,
            "duplicate_instruction_max_lines": 5,
            "max_steps_per_workflow": 8,
        },
        "state_budgets": {"active_next_actions_max": 5, "active_backlog_items_max": 12},
        "evidence_budgets": {"default_max_files": 5},
        "anti_bloat_rules": {
            "no_duplicate_instruction_files": True,
            "no_unreferenced_skills": True,
            "no_full_repo_audit_for_single_file_edit": True,
        },
    }
    for key, value in overrides.items():
        if "." in key:
            section, sub = key.split(".", 1)
            defaults[section][sub] = value  # type: ignore[index]
        else:
            defaults["instruction_budgets"][key] = value  # type: ignore[index]
    import yaml

    (root / "EFFICIENCY_BUDGET.yaml").write_text(yaml.safe_dump(defaults), encoding="utf-8")


def test_oversized_root_agents_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, root_agents_max_lines=5)
        (root / "AGENTS.md").write_text("line\n" * 10, encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_oversized_skill_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, skill_max_lines=5)
        (root / "EFFICIENCY_BUDGET.yaml").write_text(
            (root / "EFFICIENCY_BUDGET.yaml").read_text(encoding="utf-8"), encoding="utf-8"
        )
        skill = root / "skills" / "big" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "---\nname: big\ngate_level: 1\n---\n\n" + "line\n" * 10,
            encoding="utf-8",
        )
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_missing_gate_level_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        skill = root / "skills" / "nogate" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: nogate\n---\n\nstep_by_step:\n  - name: do thing\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_full_gate_at_level_one_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        skill = root / "skills" / "heavy" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "---\nname: heavy\ngate_level: 1\n---\n\nRun the full pipeline here.\n",
            encoding="utf-8",
        )
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_too_many_steps_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, max_steps_per_workflow=2)
        skill = root / "skills" / "long" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        steps = "\n".join([f"  - name: step {i}" for i in range(5)])
        skill.write_text(
            f"---\nname: long\ngate_level: 2\n---\n\nstep_by_step:\n{steps}\n",
            encoding="utf-8",
        )
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_duplicate_instructions_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        text = "This is a long canonical instruction sentence that should not be duplicated.\n"
        (root / "AGENTS.md").write_text(text, encoding="utf-8")
        (root / "CLAUDE.md").write_text(text, encoding="utf-8")
        (root / "GEMINI.md").write_text(text, encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_active_queue_too_long_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, active_next_actions_max=2)
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        items = "\n".join([f"### P{i} [BL-{i:03d}] item" for i in range(1, 5)])
        (root / "NEXT_ACTIONS.md").write_text(f"## Active Work\n\n{items}\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_evidence_bundle_too_large_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, default_max_files=2)
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        evidence = root / "docs" / "evidence" / "2026-06-28-test"
        evidence.mkdir(parents=True)
        for i in range(5):
            (evidence / f"a{i}.txt").write_text("x", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_bloat_fixture_fails() -> None:
    fixture = ROOT / "fixtures" / "efficiency_bloat_overcorrection"
    completed = run_check(["--root", str(fixture)], expect_success=False)
    stdout = completed.stdout
    assert "instruction_size" in stdout or "workflow_gate_level" in stdout
    assert "active_queue" in stdout or "evidence_bundle" in stdout


def test_clean_repo_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=True)


if __name__ == "__main__":
    tests = [
        test_oversized_root_agents_fails,
        test_oversized_skill_fails,
        test_missing_gate_level_fails,
        test_full_gate_at_level_one_fails,
        test_too_many_steps_fails,
        test_duplicate_instructions_fails,
        test_active_queue_too_long_fails,
        test_evidence_bundle_too_large_fails,
        test_bloat_fixture_fails,
        test_clean_repo_passes,
    ]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
```

- [ ] **Step 3: Create the bloat fixture**

Create `fixtures/efficiency_bloat_overcorrection/EFFICIENCY_BUDGET.yaml` with the same content as the root budget.

Create `fixtures/efficiency_bloat_overcorrection/AGENTS.md`:

```markdown
---
repo_role: downstream_project
statedd_mode: operating
repo_mode: operating
statedd_version: statedd-template-v5
---

# Bloat Project

This AGENTS.md is intentionally oversized to simulate an agent that tried to fix false closure by adding rules.
line
line
...(repeat to exceed 110 lines)...
```

Create `fixtures/efficiency_bloat_overcorrection/CLAUDE.md` and `GEMINI.md` with the same long duplicate paragraph repeated many times.

Create `fixtures/efficiency_bloat_overcorrection/skills/bloat-skill/SKILL.md`:

```markdown
---
name: bloat-skill
---

# Bloat Skill

This skill has too many steps and no gate level.

step_by_step:
  - name: step 1
  - name: step 2
  - name: step 3
  - name: step 4
  - name: step 5
  - name: step 6
  - name: step 7
  - name: step 8
  - name: step 9
  - name: step 10
```

Create `fixtures/efficiency_bloat_overcorrection/commands/statedd-bloat-gate.md`:

```markdown
---
command: statedd-bloat-gate
---

# Bloat Gate

For any edit, run all checks and the full pipeline.

1. Run everything.
2. Run everything again.
3. Run everything one more time.
```

Create `fixtures/efficiency_bloat_overcorrection/NEXT_ACTIONS.md`:

```markdown
## Active Work

### P1 [BL-001] a
### P2 [BL-002] b
### P3 [BL-003] c
### P4 [BL-004] d
### P5 [BL-005] e
### P6 [BL-006] f
```

Create `fixtures/efficiency_bloat_overcorrection/BACKLOG.md`:

```markdown
## NOW

- a
- b
- c
- d
- e
- f
- g
- h
- i
- j
- k
- l
- m
```

Create six artifact files in `fixtures/efficiency_bloat_overcorrection/docs/evidence/2026-06-28-bloat/`.

- [ ] **Step 4: Run the new tests**

```bash
python -m pytest scripts/test_efficiency_check.py -v
python scripts/test_efficiency_check.py
```

Expected: all 10 tests pass.

---

## Task 3: Wire Efficiency Check into Quality, Closure, and Release Gates

**Files:**
- Modify: `scripts/statedd_quality_gate.py`
- Modify: `scripts/statedd_closure_check.py`
- Modify: `commands/statedd-release-gate.md`

- [ ] **Step 1: Modify `scripts/statedd_quality_gate.py`**

Add to `QualityGate.__init__`:

```python
self.gate_level = 1
```

Add method:

```python
    def check_efficiency(self) -> bool:
        """Run efficiency check."""
        print("⚡ Running efficiency check...")
        code, out, err = self.run_cmd(
            ["python", "scripts/statedd_efficiency_check.py", "--gate-level", str(self.gate_level)]
        )
        if code == 0:
            print("  ✓ Efficiency check passed")
            return True
        self.failures.append(f"Efficiency check failed:\n{err or out}")
        return False
```

Add `"Efficiency", self.check_efficiency` to the `checks` list. Add `--gate-level` argument to `main()` and pass it to the gate.

- [ ] **Step 2: Modify `scripts/statedd_closure_check.py`**

Add to `ClosureCheck.__init__`:

```python
self.gate_level = 2
```

Add method:

```python
    def check_efficiency(self) -> bool:
        """Run efficiency check."""
        print("⚡ Running efficiency check...")
        code, out, err = self.run_cmd(
            ["python", "scripts/statedd_efficiency_check.py", "--gate-level", str(self.gate_level)]
        )
        if code == 0:
            print("  ✓ Efficiency check passed")
            return True
        self.failures.append(f"Efficiency check failed:\n{err or out}")
        return False
```

Add `"Efficiency", self.check_efficiency` to the `checks` list. Add `--gate-level` argument to `main()` and pass it to the checker.

- [ ] **Step 3: Modify `commands/statedd-release-gate.md`**

Replace the Procedure section with:

```markdown
**Procedure:**
1. Gate level: **3**.
2. Run `skills/quality-gate/SKILL.md` — full pipeline.
3. Run `scripts/statedd_efficiency_check.py --gate-level 3` — efficiency budget check.
4. Run `scripts/statedd_runtime_proof.py` — capture deployment runtime.
5. Run `scripts/statedd_runtime_truth_check.py` — verify matches.
6. Run `scripts/statedd_evidence_type_check.py` — verify release evidence.
7. Verify `docs/ACCEPTANCE_FREEZES.md` has all milestones.
8. Generate release handoff with:
   - Version/tag
   - Runtime identity
   - Evidence bundle
   - Rollback plan
   - Gate level used: 3
   - Efficiency budget result
```

Update Required evidence to include:

```markdown
**Required evidence:**
- All quality gate outputs
- Efficiency check output (exit 0)
- Deployment runtime proof
- Acceptance freezes for all user-facing changes
- Rollback plan documented
```

- [ ] **Step 4: Verify the gates still import**

```bash
python -c "import scripts.statedd_quality_gate; import scripts.statedd_closure_check"
```

Expected: no errors.

---

## Task 4: Add Gate Metadata to All Skills and Commands

**Files:**
- Modify: `skills/close-slice/SKILL.md`, `skills/failure-scan/SKILL.md`, `skills/ingest-bad-event/SKILL.md`, `skills/quality-gate/SKILL.md`, `skills/runtime-truth/SKILL.md`
- Modify: `commands/statedd-close-slice.md`, `commands/statedd-failure-scan.md`, `commands/statedd-ingest-bad-event.md`, `commands/statedd-quality-freeze.md`, `commands/statedd-release-gate.md`

- [ ] **Step 1: Update each skill frontmatter**

Add these fields to the YAML frontmatter of each skill:

| Skill | gate_level | evidence_max | cheapest_proof | escalate_when |
|-------|------------|--------------|----------------|---------------|
| close-slice | 2 | 8 | Quality gate + closure check + remote truth exit 0 | Release or migration needs level 3 |
| failure-scan | 1 | 2 | Copy template, fill failure modes, log to EVIDENCE_LOG | Slice closure needs level 2 |
| ingest-bad-event | 1 | 3 | Incident file + failure scan + backlog entry + handoff | P0 triggers level 2 quality freeze |
| quality-gate | 2 | 8 | All gate scripts exit 0 for the slice | Release needs level 3 |
| runtime-truth | 2 | 4 | runtime_identity.json + runtime_truth_check exit 0 | Browser verification can escalate to level 2 |

Example for `skills/close-slice/SKILL.md`:

```yaml
---
name: "close-slice"
gate_level: 2
evidence_max: 8
cheapest_proof: "Quality gate + closure check + remote truth check all exit 0"
escalate_when: "Release or template migration requires level 3 with CI proof"
description: ...
---
```

- [ ] **Step 2: Update each command frontmatter**

Add these fields to the YAML frontmatter of each command:

| Command | gate_level | evidence_max | cheapest_proof | escalate_when |
|---------|------------|--------------|----------------|---------------|
| statedd-close-slice | 2 | 8 | quality gate + closure check + remote truth exit 0 | release gate (level 3) |
| statedd-failure-scan | 1 | 2 | template filled and logged | slice closure (level 2) |
| statedd-ingest-bad-event | 1 | 3 | incident + scan + backlog + handoff | P0 quality freeze (level 2) |
| statedd-quality-freeze | 2 | 8 | quality gate exit 0 and freeze documented | release (level 3) |
| statedd-release-gate | 3 | 8 | all level 2 gates + CI proof | never |

- [ ] **Step 3: Run the efficiency checker on the repo**

```bash
python scripts/statedd_efficiency_check.py --gate-level 2 --verbose
```

Expected: passes (no errors). Warnings about unreferenced skills/commands are acceptable unless `--fail-on warning` is used.

---

## Task 5: Verify and Hand Off

**Files:**
- Modify: `NEXT_ACTIONS.md`, `WORKLOG.md`, `docs/EVIDENCE_LOG.md` as needed

- [ ] **Step 1: Run the new tests**

```bash
python -m pytest scripts/test_efficiency_check.py -v
```

Expected: 10 passes.

- [ ] **Step 2: Run the efficiency check at gate level 2**

```bash
python scripts/statedd_efficiency_check.py --gate-level 2
```

Expected: exit 0.

- [ ] **Step 3: Run the wired gates**

```bash
python scripts/statedd_quality_gate.py --gate-level 1
python scripts/statedd_closure_check.py --gate-level 2 --claimed-files AGENTS.md EFFICIENCY_BUDGET.yaml scripts/statedd_efficiency_check.py scripts/test_efficiency_check.py
```

Note: the closure check requires `runtime_identity.json`, which may not exist. Create a minimal one if needed:

```bash
python scripts/statedd_runtime_proof.py
```

- [ ] **Step 4: Run the full pytest suite and capture baseline**

```bash
python -m pytest -q
```

There are pre-existing template-version failures (v4 vs v5 in `init_template.py`); note them in the handoff. Our new tests should pass.

- [ ] **Step 5: Update state files and generate handoff**

Run:

```bash
python scripts/statedd_handoff.py
```

Capture output for the handoff. Update `NEXT_ACTIONS.md`, `WORKLOG.md`, and `docs/EVIDENCE_LOG.md` with the efficiency-layer slice.

- [ ] **Step 6: Final truth check**

```bash
git status --short
git add -A
git commit -m "feat: StateDD v5 efficiency layer - invariant, budget, checker, and gate wiring"
git push -u origin efficiency-layer
```

If push fails (no network/credentials), leave as local-only and label the handoff accordingly.
