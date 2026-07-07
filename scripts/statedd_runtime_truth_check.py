#!/usr/bin/env python3
"""
StateDD Runtime Truth Check

Verifies that the current runtime identity matches what's recorded in runtime_identity.json.
Exit codes: 0=match, 1=mismatch, 2=error
"""

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple


class RuntimeTruthCheck:
    def __init__(self, root: Path, verbose: bool = False):
        self.root = root
        self.verbose = verbose
        self.mismatches: List[str] = []

    def capture_current(self) -> Dict[str, Any]:
        """Capture current runtime identity."""
        identity = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "os": platform.system(),
            "os_version": platform.version(),
            "kernel": platform.release(),
            "arch": platform.machine(),
            "python": platform.python_version(),
            "hostname": platform.node(),
            "cwd": str(self.root),
        }

        # Git info
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                identity["git_head"] = result.stdout.strip()
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.root, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                identity["git_branch"] = result.stdout.strip()
        except Exception:
            pass

        # Container detection
        identity["in_container"] = Path("/.dockerenv").exists()
        if identity["in_container"]:
            try:
                cgroup = Path("/proc/self/cgroup").read_text()
                if "docker" in cgroup:
                    identity["container_runtime"] = "docker"
                elif "kubepods" in cgroup:
                    identity["container_runtime"] = "kubernetes"
                else:
                    identity["container_runtime"] = "unknown"
            except Exception:
                pass

        return identity

    def load_recorded(self) -> Dict[str, Any]:
        """Load recorded runtime identity."""
        path = self.root / "runtime_identity.json"
        if not path.exists():
            raise FileNotFoundError("runtime_identity.json not found")
        return json.loads(path.read_text())

    def compare(self, current: Dict, recorded: Dict) -> List[str]:
        """Compare current vs recorded, return list of mismatches."""
        mismatches = []

        # Fields that must match exactly
        critical_fields = [
            "os", "kernel", "arch", "python", "git_head"
        ]

        for field in critical_fields:
            curr_val = current.get(field)
            rec_val = recorded.get(field)
            if curr_val != rec_val:
                mismatches.append(f"{field}: current={curr_val} recorded={rec_val}")

        # Fields that can differ (warn only)
        flexible_fields = ["timestamp", "hostname", "cwd", "git_branch"]
        for field in flexible_fields:
            curr_val = current.get(field)
            rec_val = recorded.get(field)
            if curr_val != rec_val and self.verbose:
                print(f"  ℹ {field} differs (expected): current={curr_val} recorded={rec_val}")

        # Container runtime
        curr_cont = current.get("in_container")
        rec_cont = recorded.get("in_container")
        if curr_cont != rec_cont:
            mismatches.append(f"container: current={curr_cont} recorded={rec_cont}")

        return mismatches

    def run(self) -> int:
        print("=" * 50)
        print("StateDD Runtime Truth Check")
        print("=" * 50)

        try:
            print("📸 Capturing current runtime...")
            current = self.capture_current()

            print("📖 Loading recorded runtime...")
            recorded = self.load_recorded()

            print("🔍 Comparing...")
            self.mismatches = self.compare(current, recorded)

            if self.mismatches:
                print("\n❌ RUNTIME MISMATCH DETECTED:")
                for m in self.mismatches:
                    print(f"  ✗ {m}")
                print("\n💡 Run 'python scripts/statedd_runtime_proof.py' to update runtime_identity.json")
                print("=" * 50)
                return 1

            print("\n✅ RUNTIME IDENTITY MATCHES RECORDED")
            print("=" * 50)
            return 0

        except FileNotFoundError as e:
            print(f"\n❌ ERROR: {e}")
            print("💡 Run 'python scripts/statedd_runtime_proof.py' to create runtime_identity.json")
            print("=" * 50)
            return 2
        except json.JSONDecodeError:
            print("\n❌ ERROR: runtime_identity.json is invalid JSON")
            print("=" * 50)
            return 2
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            print("=" * 50)
            return 2


def main():
    parser = argparse.ArgumentParser(description="StateDD Runtime Truth Check")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    checker = RuntimeTruthCheck(root, args.verbose)
    sys.exit(checker.run())


if __name__ == "__main__":
    main()