#!/usr/bin/env python3
"""
StateDD Failure Scan Check

Scans for unhandled signals or "bad events" (errors in chat, logs, tests)
and ensures they are ingested via the ingest-bad-event skill.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class BadEvent:
    source: str
    location: str
    description: str
    severity: str  # P0-P4
    ingested: bool = False


class FailureScanCheck:
    def __init__(self, root: Path):
        self.root = root
        self.events: List[BadEvent] = []

    def scan_logs(self) -> List[BadEvent]:
        """Scan log files for error patterns."""
        events = []
        log_dirs = [
            self.root / "logs",
            self.root / ".logs",
            self.root / "var" / "log",
        ]
        error_patterns = [
            (r"ERROR|CRITICAL|FATAL|PANIC", "P1"),
            (r"Exception|Error:|traceback", "P2"),
            (r"WARN|WARNING", "P3"),
            (r"failed|timeout|connection refused", "P2"),
        ]
        for log_dir in log_dirs:
            if log_dir.exists():
                for log_file in log_dir.rglob("*.log"):
                    try:
                        content = log_file.read_text(encoding="utf-8", errors="ignore")
                        for pattern, sev in error_patterns:
                            for match in re.finditer(pattern, content, re.IGNORECASE):
                                line_no = content[:match.start()].count("\n") + 1
                                events.append(BadEvent(
                                    source="log",
                                    location=f"{log_file.relative_to(self.root)}:{line_no}",
                                    description=match.group()[:200],
                                    severity=sev
                                ))
                    except Exception:
                        pass
        return events

    def scan_test_output(self) -> List[BadEvent]:
        """Scan recent test output for failures."""
        events = []
        # Check pytest cache / test results
        test_dirs = [self.root / ".pytest_cache", self.root / "test-results", self.root / "reports"]
        for td in test_dirs:
            if td.exists():
                for f in td.rglob("*"):
                    if f.is_file():
                        try:
                            content = f.read_text(encoding="utf-8", errors="ignore")
                            if "FAILED" in content or "ERROR" in content:
                                events.append(BadEvent(
                                    source="test",
                                    location=str(f.relative_to(self.root)),
                                    description="Test failure detected",
                                    severity="P1"
                                ))
                        except Exception:
                            pass
        return events

    def scan_git_changes(self) -> List[BadEvent]:
        """Scan recent git changes for FIXME, TODO, HACK, BUG markers."""
        events = []
        try:
            import subprocess
            result = subprocess.run(
                ["git", "diff", "HEAD~5..HEAD", "--name-only"],
                cwd=self.root, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for fname in result.stdout.strip().split("\n"):
                    if fname:
                        fpath = self.root / fname
                        if fpath.exists() and fpath.is_file():
                            try:
                                content = fpath.read_text(encoding="utf-8", errors="ignore")
                                for pattern, sev in [
                                    (r"FIXME|TODO|HACK|BUG|XXX", "P3"),
                                    (r"#.*broken|#.*fail|#.*crash", "P2"),
                                ]:
                                    for match in re.finditer(pattern, content, re.IGNORECASE):
                                        line_no = content[:match.start()].count("\n") + 1
                                        events.append(BadEvent(
                                            source="code",
                                            location=f"{fname}:{line_no}",
                                            description=match.group()[:100],
                                            severity=sev
                                        ))
                            except Exception:
                                pass
        except Exception:
            pass
        return events

    def check_incidents_ingested(self, events: List[BadEvent]) -> List[BadEvent]:
        """Check if events have corresponding incident records."""
        incidents_dir = self.root / "docs" / "incidents"
        ingested_ids = set()
        if incidents_dir.exists():
            for inc in incidents_dir.glob("*.md"):
                ingested_ids.add(inc.stem)

        unmatched = []
        for e in events:
            # Simple heuristic: check if any incident mentions this
            matched = False
            for inc_id in ingested_ids:
                inc_file = incidents_dir / f"{inc_id}.md"
                try:
                    if inc_file.exists():
                        content = inc_file.read_text(encoding="utf-8", errors="ignore")
                        if e.description[:50] in content or e.location.split(":")[0] in content:
                            matched = True
                            break
                except Exception:
                    pass
            if not matched:
                e.ingested = False
                unmatched.append(e)
            else:
                e.ingested = True
        return unmatched

    def run(self) -> Tuple[int, List[BadEvent]]:
        """Run full failure scan."""
        print("Scanning for unhandled bad events...")

        all_events = []
        all_events.extend(self.scan_logs())
        all_events.extend(self.scan_test_output())
        all_events.extend(self.scan_git_changes())

        unmatched = self.check_incidents_ingested(all_events)

        print(f"Found {len(all_events)} potential bad events")
        print(f"Unmatched (not ingested): {len(unmatched)}")

        for e in unmatched:
            print(f"  [{e.severity}] {e.source}:{e.location} - {e.description[:80]}")

        if unmatched:
            print("\n⚠ Run /statedd-ingest-bad-event to record these")
            return 1, unmatched

        print("✅ All detected events appear ingested")
        return 0, []


def main():
    parser = argparse.ArgumentParser(description="StateDD Failure Scan Check")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--fail-on-unmatched", action="store_true", default=True,
                        help="Exit 1 if unmatched events found")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    checker = FailureScanCheck(root)
    exit_code, unmatched = checker.run()

    if args.fail_on_unmatched and unmatched:
        sys.exit(exit_code)
    sys.exit(0)


if __name__ == "__main__":
    main()