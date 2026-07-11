from __future__ import annotations

import subprocess
from pathlib import Path

import statedd_handoff


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def test_handoff_exits_nonzero_when_direct_verification_fails(tmp_path: Path) -> None:
    init_repo(tmp_path)

    code = statedd_handoff.main(
        [
            "statedd_handoff.py",
            "--repo",
            str(tmp_path),
            "--no-include-listeners",
            "--test-command",
            "false",
        ]
    )

    assert code == 1


def test_handoff_exits_zero_when_direct_verification_passes(tmp_path: Path) -> None:
    init_repo(tmp_path)

    code = statedd_handoff.main(
        [
            "statedd_handoff.py",
            "--repo",
            str(tmp_path),
            "--no-include-listeners",
            "--test-command",
            "true",
        ]
    )

    assert code == 0


def test_handoff_fails_when_requested_audit_is_unavailable(tmp_path: Path) -> None:
    init_repo(tmp_path)

    code = statedd_handoff.main(
        [
            "statedd_handoff.py",
            "--repo",
            str(tmp_path),
            "--no-include-listeners",
            "--run-audit",
        ]
    )

    assert code == 1


def test_handoff_distinguishes_stale_tracking_ref_from_direct_remote(
    tmp_path: Path, capsys
) -> None:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    (repo / "file.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "one"], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-qu", "origin", "main"], check=True)
    (repo / "file.txt").write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "commit", "-qam", "two"], check=True)
    local_head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    subprocess.run(
        ["git", "-C", str(repo), "update-ref", "refs/remotes/origin/main", local_head],
        check=True,
    )

    assert statedd_handoff.main(
        [
            "statedd_handoff.py",
            "--repo",
            str(repo),
            "--no-include-listeners",
        ]
    ) == 0
    output = capsys.readouterr().out
    assert "local remote-tracking ref parity: yes" in output
    assert "local HEAD equals direct remote branch: no" in output
    assert "GitHub-visible deliverables: not proven by this helper" in output


def test_handoff_fails_closed_on_malformed_active_agent_context(tmp_path: Path) -> None:
    init_repo(tmp_path)
    context = tmp_path / ".statedd" / "agent.context"
    context.parent.mkdir()
    context.write_text('{"schema":"statedd.agent_context.v1","schema":"duplicate"}', encoding="utf-8")
    assert statedd_handoff.main(
        [
            "statedd_handoff.py",
            "--repo",
            str(tmp_path),
            "--no-include-listeners",
        ]
    ) == 1
