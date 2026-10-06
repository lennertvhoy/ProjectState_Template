# Assignment W4-update-command (stopped 2026-10-06; resume from its worktree)

You are a worker on the ProjectState template repository (Python, standard library only). You run in your own git worktree created from branch feat/release-channel-6.3 at commit 189f31b; confirm with `git log -1 --oneline` and work only inside your worktree. A coordinator integrates your branch, owns STATE.yaml, PROJECT.md, evidence/, CHANGELOG.md and docs/, and reviews your diff. Other workers change other files in parallel (one is changing the generator so new projects carry the managed block; another is changing the gate).

Before coding, read: AGENTS.md (root), scripts/AGENTS.md, core/AGENTS.managed.md, releases/index.json, scripts/projectstate_release.py (shared helpers: use them, do not duplicate them), scripts/projectstate_gate.py, and render_outcome_agents_template in scripts/init_template.py.

Rules:
- Standard library only; match the existing style (from __future__ import annotations, type hints, argparse, small functions).
- Edit only the files listed under "Allowed files". Never edit STATE.yaml, PROJECT.md, evidence/, CHANGELOG.md or docs/. Never write inside any other repository; real instances may only be read (git archive into a temporary directory).
- Do not push, tag or merge. Commit on your worktree branch; end each commit message with the line: Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
- Run your tests, then `python3 scripts/test_outcome_core.py` and `python3 -m pytest scripts/ -q -p no:cacheprovider --deselect scripts/test_init_template.py::test_template_root_bootstrap_gate_passes` (that test fails until the coordinator records the slice journey; leave it). If a legacy v5 test fails only because it does not know a new v6 file, register the file minimally and say so; never weaken a check.
- Stop and report instead of guessing when the spec is ambiguous in a way that changes behavior, or when two attempts at the same failure do not converge.

TASK W4: mechanical update command for instances (release 6.3.0).

Allowed files: scripts/projectstate_update.py (new), scripts/test_update.py (new), releases/contract-history.json (new).

Purpose: bring one instance to the template's current release by replacing only two template-owned things: scripts/projectstate_gate.py and the managed block in AGENTS.md. It never touches PROJECT.md, STATE.yaml, evidence/ or project-owned text, and never runs a git command that writes.

Source of truth: --template (default: this repository): its scripts/projectstate_gate.py, core/AGENTS.managed.md and releases/index.json via scripts/projectstate_release.py. Target release = gate_release() of the template gate; it must equal the index `latest` (refuse otherwise).

CLI: python3 scripts/projectstate_update.py --target DIR [--apply] [--check] [--json] [--template DIR] [--replace-edited-gate] [--replace-edited-contract] [--accept-modified-sections] [--allow-dirty]
- Default is a dry run that prints the plan and writes nothing. --apply writes. --check writes nothing and exits 1 when any change is needed. Exit 0: up to date, planned or applied. Exit 2: refused or invalid, with the reason.

Preflight (refuse with exit 2): target is not a directory; target resolves to the template root; STATE.yaml missing or its version is not the index state_schema (parse with the gate's parse_state); AGENTS.md, the gate path, or any directory between them and the target is a symlink; inside a git work tree, `git status --porcelain -- AGENTS.md scripts/projectstate_gate.py` is non-empty, unless --allow-dirty (read-only git with GIT_OPTIONAL_LOCKS=0).

Gate: missing → install it; sha equals the template gate → nothing; sha matches a released index entry → replace it and report the old release; otherwise it was edited locally → refuse unless --replace-edited-gate, and show a unified diff (first 80 lines) against the template gate in the dry run. Keep the file mode.

Contract when AGENTS.md has a managed block (extract_managed_block): content equal to the template block → nothing; matches a released contract_sha256 → replace the content and the marker release; otherwise edited → refuse unless --replace-edited-contract; malformed markers → refuse.

First conversion when AGENTS.md has no block:
1. Keep a leading YAML frontmatter (from a first line "---" through the next "---" line) byte for byte.
2. Remove refresh-notice blocks delimited by `<!-- projectstate-NAME:start -->` and `<!-- projectstate-NAME:end -->` with the same NAME, and every section whose heading text starts with "Required first action" or "Latest required refresh". List each removal. Do this even when a block already exists.
3. Split the rest into heading blocks: each ATX heading of level 1-3 outside fenced code starts a block that runs to the next such heading. A level-1 or level-2 block is template-owned when its normalized heading (lower-case, trimmed) is one of: "projectstate outcome-first contract", "projectstate contract", "read order", "authority", "workflow", "core workflow", "continuation decision (separate from closure)", "optional persistent threads", "outcome precedence", "simplification and risk", "simplification rule", "closure", "risk stop-lines", "runtime and git boundaries", "profiles", "boundaries", "template repository note". A level-3 block takes the ownership of the nearest preceding level-1 or level-2 block. Everything else, including text before the first heading, is local.
4. A template-owned block whose normalized text (trailing spaces stripped per line, trailing blank lines dropped) equals a known text in releases/contract-history.json is replaced silently. One matching no known text is a modified template section: the dry run shows it with a diff against the closest known text for that heading; --apply refuses unless --accept-modified-sections, in which case the removed text goes into the report (and --json) so a person can move any project rule into the local sections.
5. If a level-3 heading inside a local block matches a template heading, report "possible template text in local sections" and refuse --apply unless --accept-modified-sections (such layouts need hand conversion).
6. New file: frontmatter, a blank line when there was frontmatter, render_managed_block(release, managed_block_text()), a blank line, then the local blocks in original order, byte for byte (leading blank lines trimmed). Before writing, verify that every local block's text occurs verbatim in the new file and that the frontmatter is unchanged; refuse otherwise.
7. A missing AGENTS.md becomes the managed block followed by exactly these local sections (report it):

## Local rules

<!-- Project-owned: domain rules, commands, and safety limits for this project. -->

## Owner directives

<!-- Standing instructions from the owner, one line each:
- 2026-10-06, until 2026-12-31: the directive.
Use "until revoked" for open-ended ones. Delete lines once they expire. -->

Contract history, releases/contract-history.json: the known template block texts of releases 6.0.0, 6.0.1, 6.1.0 and 6.2.0, so conversion can tell an untouched template section from an edited one. Produce it from the tags: for each of v6.0.0, v6.0.1, v6.1.0 and v6.2.0, `git worktree add --detach <tmp> <tag>` in a temporary directory outside every repository, run that checkout's `python3 scripts/init_template.py new --name History --target <tmp2> --no-init-git` with --profile core and with --profile hardened, plus `adopt` into a temporary git repository that has a README; split each AGENTS.md with the block rules above, normalize, and record texts by heading with the releases that produced them: {"format": "projectstate-contract-history/1", "headings": {"<heading>": [{"text": "...", "releases": ["6.1.0"]}]}}. Exclude frontmatter. Remove the temporary worktrees afterwards (`git worktree remove`, then `git worktree prune`). Put the builder inside projectstate_update.py as a `--build-history` maintenance mode, and say in your report exactly how you ran it.

Writes are atomic (temporary file in the same directory, then os.replace). A second --apply right after the first changes nothing and exits 0.

Output: a human-readable plan by default; --json emits {"target", "release", "gate": {"action", "from_release", "sha_before", "sha_after"}, "contract": {"action", "removed_sections", "removed_notices", "modified_sections", "local_bytes_preserved"}, "applied"}.

Tests (scripts/test_update.py), in temporary directories: convert a pure 6.2.0-generated AGENTS.md plus an older gate; a file with template sections plus local sections (local bytes preserved exactly, including a level-3 local subsection); notice blocks and "Required first action" sections removed; a modified template section (dry run reports it, apply refuses, the flag allows it and reports the text); a level-3 template heading inside a local section refused; an edited gate refused without its flag; an edited managed block refused without its flag; a current instance reports up to date and --check exits 0; a behind instance --check exits 1; dirty AGENTS.md in a git repository refused without --allow-dirty; symlinked AGENTS.md refused; target equal to the template refused; a second apply is a no-op; frontmatter preserved.

Finally, exercise copies of two real instances, never the originals: `git -C ~/Projects/example-project-08 archive HEAD | tar -x -C <tmp>/example-project-08` and the same for ~/Projects/example-project-05. Run --json dry runs, then --apply on the copies, and report per copy: gate action, removed sections and notices, modified sections (headings only), whether local bytes were preserved, and whether a second --apply was a no-op.

Report (final message, under 450 words): branch and commit hashes; files changed; how you built the contract history; exact test commands with pass/fail counts; the two real-copy results; any deviation and why; known limitations.
