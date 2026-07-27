"""One-shot rename helper: StateDD -> ProjectState.

PRESERVE set  : frozen historical artifacts (evidence, fixtures, EVIDENCE_LOG, WORKLOG).
DENYLIST      : historical IDs that must remain literal even inside rewritten files
                (e.g. BL-STATEDD-INTEGRATION-001, dated evidence dir names).
SUBSTITUTIONS : ordered most-specific first so longer patterns win.

This script is intentionally self-contained and idempotent on a fresh branch.
After running it, manual surgical work follows: schema aliases, shims, banners.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class BinaryFileError(Exception):
    """Sentinel for binary file handling."""

# Directory / file prefixes whose contents are frozen historical artifacts.
PRESERVE_PREFIXES = (
    "docs/evidence/",
    "fixtures/",
)
PRESERVE_FILES = {
    Path("docs/EVIDENCE_LOG.md"),
    Path("WORKLOG.md"),
    Path("scripts/_rename_helper.py"),  # do not rewrite self
}

# Historical IDs / literals that must survive the rename unchanged.
DENYLIST = [
    "BL-STATEDD-INTEGRATION-001",
    "2026-06-14-statedd-v2-executable-workflow",
    "2026-06-23-statedd-version-source",
    "2026-07-11-statedd-integration",
]

# Ordered substitutions (longest/most-specific first). Regex-safe strings.
SUBSTITUTIONS = [
    (r"StateDD_Template", "ProjectState_Template"),
    (r"StateDD Template", "ProjectState Template"),
    (r"StateDD-Free-Use", "ProjectState-Free-Use"),
    (r"StateDD Free Use", "ProjectState Free Use"),
    (r"StateDD", "ProjectState"),
    (r"statedd-template-v5", "projectstate-template-v5"),
    (r"statedd-template", "projectstate-template"),
    (r"statedd_template", "projectstate_template"),
    (r"statedd-clones", "projectstate-clones"),
    (r"statedd-runtime", "projectstate-runtime"),
    (r"STATEDD_ASSETS", "PROJECTSTATE_ASSETS"),
    # script module prefix: statedd_foo -> projectstate_foo
    (r"statedd_", "projectstate_"),
    # command prefix: statedd-foo -> projectstate-foo
    (r"statedd-", "projectstate-"),
    # schema id prefix: statedd.foo -> projectstate.foo
    (r"statedd\.", "projectstate."),
    # bare lowercase token (last)
    (r"statedd", "projectstate"),
]


def is_preserved(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if Path(rel) in PRESERVE_FILES:
        return True
    return any(rel.startswith(p) for p in PRESERVE_PREFIXES)


def protect_denylist(text: str) -> tuple[str, dict[str, str]]:
    """Replace denylist literals with unique tokens, return mapping for restore."""
    mapping: dict[str, str] = {}
    for i, lit in enumerate(DENYLIST):
        token = f"\x00DENY{i}\x00"
        mapping[token] = lit
        text = text.replace(lit, token)
    return text, mapping


def restore_denylist(text: str, mapping: dict[str, str]) -> str:
    for token, lit in mapping.items():
        text = text.replace(token, lit)
    return text


def rewrite_file(path: Path) -> tuple[bool, int]:
    try:
        original = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, BinaryFileError):
        return False, 0
    protected, mapping = protect_denylist(original)
    new = protected
    for pat, repl in SUBSTITUTIONS:
        new = re.sub(pat, repl, new)
    new = restore_denylist(new, mapping)
    if new != original:
        path.write_text(new, encoding="utf-8")
        return True, sum(1 for a, b in zip(original, new) if a != b)
    return False, 0


def main() -> int:
    changed = 0
    skipped = 0
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        if is_preserved(path):
            skipped += 1
            continue
        ok, _ = rewrite_file(path)
        if ok:
            changed += 1
    print(f"changed={changed} preserved={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


class BinaryFileError(Exception):
    """Sentinel for binary file handling."""
