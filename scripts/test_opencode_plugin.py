#!/usr/bin/env python3
"""Static checks for projectstate_opencode_plugin.js.

The plugin is an OpenCode (Bun) ESM module, so these checks read its source
and assert that it drives exactly the three projectstate_hooks.py commands
with the fixed JSON stdin shapes, wires the required hooks, and fails safe.
`node --check` runs when node exists and the test skips cleanly without it.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
PLUGIN = SCRIPTS / "projectstate_opencode_plugin.js"

# The fixed interface of scripts/projectstate_hooks.py, as JSON keys per command.
TOOL_INTERFACE = {
    "record": ("hook_event_name", "cwd", "session_id", "prompt"),
    "brief": ("hook_event_name", "cwd", "session_id", "source"),
    "stop": ("hook_event_name", "cwd", "session_id", "stop_hook_active"),
}


@pytest.fixture(scope="module")
def source() -> str:
    assert PLUGIN.exists(), f"missing {PLUGIN.name}"
    return PLUGIN.read_text(encoding="utf-8")


def payload_block(source: str, command: str) -> str:
    """Return the runTool payload object literal for one command."""
    calls = re.findall(rf'runTool\(\s*tool,\s*"{command}",\s*(\{{.*?\}})\s*\)', source, re.DOTALL)
    assert len(calls) == 1, f"expected exactly one {command!r} call, found {len(calls)}"
    return calls[0]


def hook_body(source: str, name: str) -> str:
    """Return the body of one hook, up to its closing brace line."""
    start = source.index(name)
    end = source.index("\n    },", start)
    return source[start:end]


@pytest.mark.parametrize("command", sorted(TOOL_INTERFACE))
def test_exactly_one_call_per_command(source: str, command: str) -> None:
    assert source.count(f'"{command}"') >= 1
    # No other tool command is ever invoked.
    all_commands = set(re.findall(r'runTool\(\s*tool,\s*"([a-z_]+)"', source))
    assert all_commands == set(TOOL_INTERFACE), f"unexpected commands: {all_commands - set(TOOL_INTERFACE)}"


@pytest.mark.parametrize("command", sorted(TOOL_INTERFACE))
def test_payload_shape(source: str, command: str) -> None:
    block = payload_block(source, command)
    for key in TOOL_INTERFACE[command]:
        assert re.search(rf"\b{key}:", block), f"{command} payload missing {key!r}"


@pytest.mark.parametrize(
    ("command", "event"),
    [
        ("record", "UserPromptSubmit"),
        ("brief", "SessionStart"),
        ("stop", "Stop"),
    ],
)
def test_payload_event_names(source: str, command: str, event: str) -> None:
    block = payload_block(source, command)
    assert f'hook_event_name: "{event}"' in block


def test_record_skips_synthetic_and_own_followup(source: str) -> None:
    chat = hook_body(source, '"chat.message"')
    assert "synthetic" in chat and "ignored" in chat, "synthetic/ignored parts not skipped"
    assert "FOLLOWUP_MARKER" in chat, "own follow-up messages not skipped"
    assert "prompt: text" in chat, "record does not pass the message text"


def test_child_sessions_skip_record(source: str) -> None:
    chat = hook_body(source, '"chat.message"')
    assert "isChildSession(input.sessionID)" in chat, "child sessions must not record"
    assert chat.index("isChildSession(input.sessionID)") < chat.index('runTool(tool, "record"'), (
        "the child check must gate the record call"
    )


def test_child_sessions_skip_stop(source: str) -> None:
    event = hook_body(source, "event:")
    assert "session.idle" in event
    assert event.index('type !== "session.idle"') < event.index("isChildSession(sessionID)"), (
        "the idle branch must check for child sessions"
    )
    assert event.index("isChildSession(sessionID)") < event.index('runTool(tool, "stop"'), (
        "child sessions must never reach the stop command"
    )


def test_child_lookup_uses_sdk_and_fails_closed(source: str) -> None:
    assert "client.session.get" in source, "child status must come from the SDK session lookup"
    finder = re.search(
        r"async function isChildSession\(sessionID\) \{.*?\n  \}", source, re.DOTALL
    )
    assert finder, "isChildSession helper missing"
    body = finder.group(0)
    assert "path: { id: sessionID }" in body, "lookup must pass the session id"
    assert "childCache.set(" in body or "rememberChild(" in body, "answer must be cached per session"
    assert "parentID" in body, "child means the session has a parentID"
    assert 'rememberChild(sessionID, true)' in body, "lookup failure must fail closed (child)"


def test_brief_applies_to_child_sessions(source: str) -> None:
    system = hook_body(source, '"experimental.chat.system.transform"')
    assert "getBrief" in system
    assert "isChildSession" not in system, "brief must not be gated on child sessions"
    event = hook_body(source, "event:")
    compacted = event.index("session.compacted")
    child_check = event.index("isChildSession(sessionID)")
    assert compacted < child_check, "compaction re-injection must stay before the child gate"


def test_brief_once_per_session_and_after_compaction(source: str) -> None:
    assert "experimental.chat.system.transform" in source
    assert "session.compacted" in source, "compaction re-injection missing"
    assert 'getBrief(sessionID, "startup")' in source
    assert 'getBrief(sessionID, "compact")' in source
    assert "briefs.set(" in source and "briefs.get(" in source, "brief text not cached per session"


def test_stop_block_sends_one_followup_via_client(source: str) -> None:
    assert "session.idle" in source
    assert "stop_hook_active" in source, "stop chains must pass stop_hook_active"
    assert "alreadyChained) return" in source or "alreadyChained" in source
    assert "client.session.promptAsync" in source, "follow-up must go through the SDK client"
    assert "FOLLOWUP_MARKER" in source, "follow-up must be marked so record skips it"


def test_never_breaks_a_session(source: str) -> None:
    hooks = re.findall(r"(?:async \((?:input|input, output|\{ event \})\) => \{)", source)
    assert len(hooks) >= 3, "expected the three hook bodies"
    for hook_name in ['"chat.message"', '"experimental.chat.system.transform"', "event:"]:
        start = source.index(hook_name)
        segment = source[start : start + 2000]
        assert "try {" in segment, f"{hook_name} does not catch everything"
    assert f"TIMEOUT_MS = 5000" in source, "subprocess calls must be time-limited to 5s"
    assert "setTimeout(() => finish(false, \"timeout\"), TIMEOUT_MS)" in source


def test_no_external_dependencies(source: str) -> None:
    imports = re.findall(r'import[^"\']*["\']([^"\']+)["\']', source)
    for module in imports:
        assert module.startswith("node:") or module.startswith("."), f"non-node import: {module}"


def test_node_syntax_check() -> None:
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    result = subprocess.run(
        ["node", "--check", str(PLUGIN)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"node --check failed:\n{result.stderr}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
