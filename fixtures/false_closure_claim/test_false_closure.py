#!/usr/bin/env python3
"""
Regression test for false closure claim detection.

Tests that statedd_remote_truth_check.py correctly fails when:
- Claimed files are not tracked
- Local HEAD not on remote
"""

import subprocess
import sys
import tempfile
import os
from pathlib import Path


def run_cmd(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_false_closure_detection():
    """Test that false closure claims are detected."""
    print("Testing false closure detection...")

    # Create temp repo
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        # Init git repo
        run_cmd(["git", "init"], repo)
        run_cmd(["git", "config", "user.email", "test@test.com"], repo)
        run_cmd(["git", "config", "user.name", "Test"], repo)
        run_cmd(["git", "branch", "-M", "main"], repo)

        # Create initial commit
        (repo / "README.md").write_text("# Test")
        run_cmd(["git", "add", "README.md"], repo)
        run_cmd(["git", "commit", "-m", "initial"], repo)

        # Create a fake "remote" (bare repo)
        remote_dir = Path(tmpdir).parent / f"remote-{Path(tmpdir).name}.git"
        run_cmd(["git", "init", "--bare", str(remote_dir)], repo)
        run_cmd(["git", "remote", "add", "origin", str(remote_dir)], repo)
        run_cmd(["git", "push", "--set-upstream", "origin", "main"], repo)

        # Create untracked claimed file
        (repo / "claimed_deliverable.py").write_text("# fake deliverable\n")

        # Run remote truth check - should FAIL
        script_path = Path(__file__).parent.parent.parent / "scripts" / "statedd_remote_truth_check.py"
        code, out, err = run_cmd([
            sys.executable, str(script_path),
            "--root", str(repo),
            "--claim", "claimed_deliverable.py"
        ], repo)

        print(f"Exit code: {code}")
        print(f"Output:\n{out}")
        if err:
            print(f"Stderr:\n{err}")

        # Must fail
        assert code == 1, f"Expected exit code 1, got {code}"

        # Check for expected failure messages
        assert "Claimed file not tracked" in out or "claimed_files_tracked" in out, \
            "Should detect untracked claimed file"
        assert "NOT CLOSURE-GRADE" in out, "Should label as NOT CLOSURE-GRADE"

        print("✓ False closure correctly detected")


def test_true_closure_passes():
    """Test that true closure (tracked, pushed) passes."""
    print("Testing true closure passes...")

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        run_cmd(["git", "init"], repo)
        run_cmd(["git", "config", "user.email", "test@test.com"], repo)
        run_cmd(["git", "config", "user.name", "Test"], repo)
        run_cmd(["git", "branch", "-M", "main"], repo)

        (repo / "README.md").write_text("# Test")
        run_cmd(["git", "add", "README.md"], repo)
        run_cmd(["git", "commit", "-m", "initial"], repo)

        remote_dir = Path(tmpdir).parent / f"remote-{Path(tmpdir).name}.git"
        run_cmd(["git", "init", "--bare", str(remote_dir)], repo)
        run_cmd(["git", "remote", "add", "origin", str(remote_dir)], repo)
        run_cmd(["git", "push", "--set-upstream", "origin", "main"], repo)

        # Create AND TRACK a real deliverable
        (repo / "real_deliverable.py").write_text("# real deliverable\n")
        run_cmd(["git", "add", "real_deliverable.py"], repo)
        run_cmd(["git", "commit", "-m", "add deliverable"], repo)
        run_cmd(["git", "push", "origin", "main"], repo)

        script_path = Path(__file__).parent.parent.parent / "scripts" / "statedd_remote_truth_check.py"
        code, out, err = run_cmd([
            sys.executable, str(script_path),
            "--root", str(repo),
            "--claim", "real_deliverable.py"
        ], repo)

        print(f"Exit code: {code}")
        print(f"Output:\n{out}")

        # Must pass
        assert code == 0, f"Expected exit code 0, got {code}: {out}"
        assert "GitHub-verified" in out or "pushed" in out, f"Should label as pushed/GitHub-verified: {out}"

        print("✓ True closure correctly passes")


if __name__ == "__main__":
    test_false_closure_detection()
    test_true_closure_passes()
    print("\n✅ All regression tests passed")
