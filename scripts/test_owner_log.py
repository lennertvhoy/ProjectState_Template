#!/usr/bin/env python3
"""Tests for projectstate_owner_log.py: the owner's words are captured mechanically and never break a session."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import projectstate_owner_log as owner_log  # noqa: E402

TOOL = SCRIPTS / "projectstate_owner_log.py"
NOW = dt.datetime(2026, 10, 9, 12, 0, tzinfo=dt.timezone.utc)


def cli(root: Path, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=root, input=stdin, capture_output=True, text=True, check=False)


def hook(root: Path, event: str, **payload: object) -> subprocess.CompletedProcess[str]:
    return cli(root, event, stdin=json.dumps({"cwd": str(root), **payload}))


def test_prompts_are_recorded_verbatim_oldest_first_and_injected(tmp_path: Path) -> None:
    assert owner_log.append_entry(tmp_path, "Export must use semicolons and a UTF-8 BOM.", "abc12345", NOW)
    assert owner_log.append_entry(tmp_path, "Refuse to overwrite a file unless --force is given.", "abc12345", NOW)
    text = owner_log.inject_text(tmp_path)
    assert "semicolons and a UTF-8 BOM" in text and "--force" in text
    assert text.index("semicolons") < text.index("--force")
    assert text.startswith("Earlier instructions from the owner")
    assert "HOW things are built" in text and "this session's request" in text  # stale scope must not bind the new session


def test_the_log_ignores_itself_in_git_and_stays_out_of_status(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    owner_log.append_entry(tmp_path, "A constraint that must not be committed.", "s1", NOW)
    assert (tmp_path / ".projectstate" / ".gitignore").read_text() == "*\n"
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=tmp_path, capture_output=True, text=True)
    assert status.stdout.strip() == ""


def test_obvious_secrets_are_redacted_before_they_reach_the_file(tmp_path: Path) -> None:
    prompt = ("use sk-abcdefghijklmnopqrstuvwx and ghp_abcdefghijklmnopqrstuvwxyz1234 with password=hunter2\n"
              "-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJBAK\n-----END RSA PRIVATE KEY-----\nAKIAABCDEFGHIJKLMNOP")
    owner_log.append_entry(tmp_path, prompt, "s1", NOW)
    stored = (tmp_path / ".projectstate" / "owner-log.md").read_text()
    for leaked in ("sk-abcdefghijklmnopqrstuvwx", "ghp_abcdefghijklmnopqrstuvwxyz1234", "hunter2", "MIIBOgIBAAJBAK", "AKIAABCDEFGHIJKLMNOP"):
        assert leaked not in stored
    assert stored.count("[redacted") >= 4


def test_short_and_repeated_prompts_are_not_logged(tmp_path: Path) -> None:
    assert not owner_log.append_entry(tmp_path, "ok", "s1", NOW)
    assert owner_log.append_entry(tmp_path, "Keep money as integer cents.", "s1", NOW)
    assert not owner_log.append_entry(tmp_path, "Keep money as integer cents.", "s1", NOW)  # same session, same words
    assert owner_log.append_entry(tmp_path, "Keep money as integer cents.", "s2", NOW)  # said again in a new session


def test_the_log_is_capped_and_keeps_the_newest_entries(tmp_path: Path) -> None:
    for number in range(40):
        owner_log.append_entry(tmp_path, f"entry {number:02d} " + "x" * 6000, f"s{number}", NOW)
    path = tmp_path / ".projectstate" / "owner-log.md"
    assert path.stat().st_size <= owner_log.MAX_LOG_BYTES
    stored = path.read_text()
    assert "entry 39" in stored and "entry 00" not in stored


def test_inject_is_bounded_and_prefers_the_newest(tmp_path: Path) -> None:
    for number in range(30):
        owner_log.append_entry(tmp_path, f"decision {number:02d} " + "y" * 900, f"s{number}", NOW)
    text = owner_log.inject_text(tmp_path)
    assert len(text) <= owner_log.INJECT_CHARS + 1500
    assert "decision 29" in text and "decision 00" not in text
    assert owner_log.inject_text(tmp_path / "empty") == ""


def test_symlinked_log_directory_is_never_written_through(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (tmp_path / ".projectstate").symlink_to(elsewhere)
    assert not owner_log.append_entry(tmp_path, "must not land outside the repository", "s1", NOW)
    assert list(elsewhere.iterdir()) == []
    assert owner_log.inject_text(tmp_path) == ""


def test_hooks_record_and_inject_through_the_real_command_line(tmp_path: Path) -> None:
    (tmp_path / "STATE.yaml").write_text("version: x\n")
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)
    done = hook(nested, "record", session_id="c7c45ad3-1111", prompt="Always write semicolon-delimited CSV.")
    assert done.returncode == 0 and done.stdout == ""  # a hook's stdout would be injected into the session
    assert "semicolon-delimited" in (tmp_path / ".projectstate" / "owner-log.md").read_text()  # found the project root
    injected = hook(nested, "inject", session_id="c7c45ad3-2222")
    assert injected.returncode == 0 and "semicolon-delimited CSV" in injected.stdout


def test_hooks_never_fail_a_session(tmp_path: Path) -> None:
    for stdin in ("", "not json", "[]", '{"prompt": null}', '{"cwd": "/nonexistent/dir", "prompt": "hello there"}'):
        for event in ("record", "inject"):
            done = cli(tmp_path, event, stdin=stdin)
            assert done.returncode == 0, (event, stdin, done.stderr)
            assert done.stdout == "" or event == "inject"


def test_install_merges_idempotently_and_keeps_existing_settings(tmp_path: Path) -> None:
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"model": "sonnet", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo done"}]}],
                                                              "SessionStart": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}))
    assert cli(tmp_path, "install", "--root", str(tmp_path), "--dry-run").returncode == 0
    assert "projectstate_owner_log" not in settings.read_text()
    done = cli(tmp_path, "install", "--root", str(tmp_path))
    assert done.returncode == 0
    merged = json.loads(settings.read_text())
    assert merged["model"] == "sonnet" and merged["hooks"]["Stop"][0]["hooks"][0]["command"] == "echo done"
    starts = [h["command"] for g in merged["hooks"]["SessionStart"] for h in g["hooks"]]
    assert starts[0] == "echo mine" and len(starts) == 2 and "owner_log.py inject" in starts[1]
    assert "owner_log.py record" in merged["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    before = settings.read_text()
    again = cli(tmp_path, "install", "--root", str(tmp_path))
    assert again.returncode == 0 and "already installed" in again.stdout and settings.read_text() == before


def test_install_refuses_unreadable_or_symlinked_settings(tmp_path: Path) -> None:
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text("{not json")
    broken = cli(tmp_path, "install", "--root", str(tmp_path))
    assert broken.returncode == 2 and settings.read_text() == "{not json"
    settings.unlink()
    target = tmp_path / "real.json"
    target.write_text("{}")
    settings.symlink_to(target)
    linked = cli(tmp_path, "install", "--root", str(tmp_path))
    assert linked.returncode == 2 and target.read_text() == "{}"


def test_show_prints_the_log_for_a_human_or_an_agent(tmp_path: Path) -> None:
    owner_log.append_entry(tmp_path, "Show me this later.", "s1", NOW)
    assert "Show me this later." in cli(tmp_path, "show", "--root", str(tmp_path)).stdout
