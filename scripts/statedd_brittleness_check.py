#!/usr/bin/env python3
"""Advisory brittleness heuristic scan for StateSpec slices.

This script emits warnings only. It does not prove code quality and it does not
replace the anti-brittleness review gate.

Exit codes:
  0 = scan completed, with or without warnings
  2 = scan could not read diff input
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".cs", ".swift", ".kt"}
TEST_MARKERS = {"/test/", "/tests/", "__tests__", ".test.", ".spec.", "fixtures/"}


@dataclass(frozen=True)
class AddedLine:
    file: str
    line_no: int
    text: str


@dataclass(frozen=True)
class Finding:
    kind: str
    file: str
    line_no: int
    message: str


def run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout, completed.stderr


def read_diff(args: argparse.Namespace) -> tuple[int, str, str]:
    if args.diff_file:
        path = Path(args.diff_file)
        try:
            return 0, path.read_text(encoding="utf-8"), ""
        except (OSError, UnicodeDecodeError) as exc:
            return 2, "", str(exc)

    repo = Path(args.repo).resolve()
    commands: list[list[str]] = []
    if args.base:
        commands.append(["git", "diff", "--unified=0", "--no-ext-diff", args.base, "--"])
    else:
        commands.extend(
            [
                ["git", "diff", "--unified=0", "--no-ext-diff", "--"],
                ["git", "diff", "--cached", "--unified=0", "--no-ext-diff", "--"],
                ["git", "diff-tree", "--root", "--unified=0", "--no-ext-diff", "HEAD"],
            ]
        )

    combined: list[str] = []
    errors: list[str] = []
    for command in commands:
        code, stdout, stderr = run_command(command, repo)
        if code != 0:
            errors.append(stderr.strip() or f"{' '.join(command)} exited {code}")
            continue
        if stdout.strip():
            combined.append(stdout)
            if args.base:
                break
    if combined:
        return 0, "\n".join(combined), ""
    if errors and args.base:
        return 2, "", "; ".join(errors)
    return 0, "", ""


def parse_added_lines(diff_text: str) -> list[AddedLine]:
    added: list[AddedLine] = []
    current_file = "not proven"
    new_line = 0
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            current_file = raw.removeprefix("+++ ").strip()
            if current_file.startswith("b/"):
                current_file = current_file[2:]
            if current_file == "/dev/null":
                current_file = "not proven"
            continue
        if raw.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,(\d+))?", raw)
            new_line = int(match.group(1)) if match else 0
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            added.append(AddedLine(current_file, new_line, raw[1:]))
            new_line += 1
            continue
        if raw.startswith("-") and not raw.startswith("---"):
            continue
        if current_file != "not proven":
            new_line += 1
    return added


def is_test_file(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return any(marker in normalized for marker in TEST_MARKERS)


def is_code_file(path: str) -> bool:
    return Path(path).suffix.lower() in CODE_EXTENSIONS


def is_production_code(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return is_code_file(path) and not is_test_file(normalized) and not normalized.startswith("docs/")


def quoted_strings(text: str) -> list[str]:
    return re.findall(r"""["']([^"']+)["']""", text)


def group_by_file(lines: list[AddedLine]) -> dict[str, list[AddedLine]]:
    grouped: dict[str, list[AddedLine]] = {}
    for line in lines:
        grouped.setdefault(line.file, []).append(line)
    return grouped


def scan_keyword_buckets(lines: list[AddedLine]) -> list[Finding]:
    findings: list[Finding] = []
    for file, file_lines in group_by_file(lines).items():
        if not is_production_code(file):
            continue
        joined = "\n".join(line.text for line in file_lines)
        if not re.search(r"\b(keyword|keywords|phrases|synonyms|bucket|intent)\b", joined, re.IGNORECASE):
            continue
        strings = [value for value in quoted_strings(joined) if len(value) >= 2]
        if len(strings) >= 12:
            first = file_lines[0]
            findings.append(
                Finding(
                    "large_keyword_bucket",
                    file,
                    first.line_no,
                    f"{len(strings)} quoted strings added near keyword/bucket logic; verify a typed authority path owns routing.",
                )
            )
    return findings


def scan_many_includes(lines: list[AddedLine]) -> list[Finding]:
    findings: list[Finding] = []
    for file, file_lines in group_by_file(lines).items():
        if not is_production_code(file):
            continue
        includes = [line for line in file_lines if ".includes(" in line.text]
        if len(includes) >= 5:
            findings.append(
                Finding(
                    "many_includes_checks",
                    file,
                    includes[0].line_no,
                    f"{len(includes)} .includes(...) checks added; verify this is not scattered keyword routing.",
                )
            )
    return findings


def scan_exact_prompt_strings(lines: list[AddedLine]) -> list[Finding]:
    findings: list[Finding] = []
    for line in lines:
        if not is_production_code(line.file):
            continue
        lower = line.text.lower()
        if not any(marker in lower for marker in ("prompt", "message", "user_", "userinput", "input", "request")):
            continue
        long_strings = [value for value in quoted_strings(line.text) if len(value) >= 40]
        if long_strings:
            findings.append(
                Finding(
                    "exact_prompt_string",
                    line.file,
                    line.line_no,
                    "Long exact user/prompt string added in production code; verify general parsing or schema/state authority.",
                )
            )
    return findings


def scan_sleep_timeouts(lines: list[AddedLine]) -> list[Finding]:
    pattern = re.compile(r"\b(sleep|setTimeout|setInterval)\s*\(|await\s+new\s+Promise|time\.sleep\s*\(", re.IGNORECASE)
    return [
        Finding(
            "sleep_or_timeout_sync",
            line.file,
            line.line_no,
            "Sleep/timeout-based synchronization added; verify event/state-based synchronization is not available.",
        )
        for line in lines
        if is_production_code(line.file) and pattern.search(line.text)
    ]


def scan_silent_fallbacks(lines: list[AddedLine]) -> list[Finding]:
    findings: list[Finding] = []
    grouped = group_by_file(lines)
    for file, file_lines in grouped.items():
        if not is_production_code(file):
            continue
        for index, line in enumerate(file_lines):
            lower = line.text.lower().strip()
            window = "\n".join(item.text.lower().strip() for item in file_lines[index : index + 4])
            if "except exception" in lower and re.search(r"\b(pass|return\s+(none|null|undefined|false|\"\"|''))\b", window):
                findings.append(
                    Finding(
                        "silent_catch_all",
                        file,
                        line.line_no,
                        "Catch-all exception path appears to suppress errors; verify this is not the authority path.",
                    )
                )
            if re.search(r"\bcatch\s*\(", lower) and re.search(r"\breturn\s+(null|undefined|false|\"\"|'')\b", window):
                findings.append(
                    Finding(
                        "silent_catch_all",
                        file,
                        line.line_no,
                        "Catch-all fallback appears to suppress errors; verify errors remain observable.",
                    )
                )
    return findings


def scan_brittle_comments(lines: list[AddedLine]) -> list[Finding]:
    findings: list[Finding] = []
    for line in lines:
        if not is_production_code(line.file):
            continue
        lower = line.text.lower()
        if ("#" not in line.text and "//" not in line.text) or not re.search(r"\b(temporary|hack|quick fix|for now)\b", lower):
            continue
        findings.append(
            Finding(
                "brittle_comment",
                line.file,
                line.line_no,
                "Comment marks production code as temporary/hack/quick fix; record why this is not brittle closure.",
            )
        )
    return findings


def scan_fixture_only_tests(lines: list[AddedLine]) -> list[Finding]:
    findings: list[Finding] = []
    for file, file_lines in group_by_file(lines).items():
        if not is_test_file(file):
            continue
        joined = "\n".join(line.text for line in file_lines).lower()
        long_strings = [value for value in quoted_strings("\n".join(line.text for line in file_lines)) if len(value) >= 40]
        if long_strings and not any(marker in joined for marker in ("adjacent", "variant", "parametrize", "parameterized", "table")):
            findings.append(
                Finding(
                    "fixture_only_test_shape",
                    file,
                    file_lines[0].line_no,
                    "Test adds a long exact observed string without adjacent/variant cases mentioned.",
                )
            )
    return findings


def scan(lines: list[AddedLine]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(scan_keyword_buckets(lines))
    findings.extend(scan_many_includes(lines))
    findings.extend(scan_exact_prompt_strings(lines))
    findings.extend(scan_sleep_timeouts(lines))
    findings.extend(scan_silent_fallbacks(lines))
    findings.extend(scan_brittle_comments(lines))
    findings.extend(scan_fixture_only_tests(lines))
    return findings


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Advisory StateSpec brittleness heuristic scan")
    parser.add_argument("--repo", default=str(ROOT), help="Repo root for git diff scanning")
    parser.add_argument("--base", help="Optional git diff base/ref")
    parser.add_argument("--diff-file", help="Unified diff file to scan instead of git diff")
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    code, diff_text, error = read_diff(args)
    if code != 0:
        print("StateSpec Brittleness Check")
        print("Result: error")
        print(f"- {error}")
        return 2

    added = parse_added_lines(diff_text)
    findings = scan(added)

    print("StateSpec Brittleness Check")
    print("This scan is advisory. It can warn about brittle shapes, but it cannot prove absence of brittleness.")
    print()
    print(f"Added lines scanned: {len(added)}")
    print(f"Warnings: {len(findings)}")
    print()
    if findings:
        for finding in findings:
            print(f"- [{finding.kind}] {finding.file}:{finding.line_no}: {finding.message}")
        print()
        print("Result: advisory warnings found; complete the anti-brittleness review before claiming closure-grade.")
    else:
        print("No heuristic warnings found; this does not prove absence of brittleness.")
        print("Result: complete the anti-brittleness review before claiming closure-grade.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
