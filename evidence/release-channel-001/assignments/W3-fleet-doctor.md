# Assignment W3-fleet-doctor (stopped 2026-10-06; resume from its worktree)

You are a worker on the ProjectState template repository (Python, standard library only). You run in your own git worktree created from branch feat/release-channel-6.3 at commit dc48af5; confirm with `git log -1 --oneline` and work only inside your worktree. A coordinator integrates your branch, owns STATE.yaml, PROJECT.md, evidence/, CHANGELOG.md and docs/, and reviews your diff. Other workers change other files in parallel (one is changing the gate's warnings and owner-decision rules; import the gate module, do not copy its logic).

Before coding, read: AGENTS.md (root), scripts/AGENTS.md, core/AGENTS.managed.md, releases/index.json, scripts/projectstate_release.py (shared helpers: use them, do not duplicate them), scripts/projectstate_gate.py.

Rules:
- Standard library only; match the existing style (from __future__ import annotations, type hints, argparse, small functions).
- Edit only the files listed under "Allowed files". Never edit STATE.yaml, PROJECT.md, evidence/, CHANGELOG.md or docs/. Never write inside any other repository.
- Do not push, tag or merge. Commit on your worktree branch; end each commit message with the line: Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
- Run your tests, then `python3 scripts/test_outcome_core.py` and `python3 -m pytest scripts/ -q -p no:cacheprovider --deselect scripts/test_init_template.py::test_template_root_bootstrap_gate_passes` (that test fails until the coordinator records the slice journey; leave it). If a legacy v5 test fails only because it does not know a new v6 file, register the file minimally and say so; never weaken a check.
- Stop and report instead of guessing when the spec is ambiguous in a way that changes behavior, or when two attempts at the same failure do not converge.

TASK W3: read-only fleet doctor with an owner inbox.

Allowed files: scripts/projectstate_fleet.py (new), scripts/test_fleet.py (new).

Purpose: one command shows, for every repository under a root folder (default: the template repository's parent directory, which is ~/Projects), which ProjectState release it runs, whether its gate or managed contract drifted or was edited, how large its startup context is, and which decisions wait for the owner. It must never write inside any repository.

CLI: python3 scripts/projectstate_fleet.py [--root DIR] [--template DIR] [--out DIR] [--stdout] [--format md|json] [--today YYYY-MM-DD]
- --template defaults to this repository; read releases/index.json and core/AGENTS.managed.md from it through scripts/projectstate_release.py. Import the gate module (sibling import of scripts/projectstate_gate.py) for parse_state and validate. Never run an instance's own gate or any instance code.
- Default: write fleet.md and fleet.json atomically into --out (default ~/.local/state/projectstate), then print both paths and a one-line summary. --stdout prints one report (md by default, json with --format json) and writes nothing. Refuse (exit 2) an --out inside --root. --today overrides the date (for tests).

Discovery: immediate children of --root that are real directories (skip symlinks and names starting with "." or "_"), sorted case-insensitively. Kind: v6 when STATE.yaml parses and its version equals the index state_schema; v6-invalid when STATE.yaml exists but does not; v5 when only PROJECT_STATE.yaml exists; other otherwise. Mark the template repository itself with role "template".

Git, for every repository with .git: branch, short HEAD, last commit date, upstream or none, staged/unstaged/untracked counts from `git status --porcelain=v1`. Run every git command read-only with env GIT_OPTIONAL_LOCKS=0 and GIT_TERMINAL_PROMPT=0, `-c core.fsmonitor=false`, a timeout, and never anything that touches the network.

Per v6 repository:
- Gate scripts/projectstate_gate.py: missing, symlink (refused), or its sha256. Status: current (matches the current release = projectstate_release.current_release, the highest index entry with status released), behind (matches an older release; name the newest match), or unknown (matches none: edited or foreign).
- Contract AGENTS.md: missing; unmanaged (no block); malformed; or the block content hash compared with contract_sha256 values: current, behind or edited.
- Sizes: bytes and lines of AGENTS.md, PROJECT.md and STATE.yaml; startup_tokens = total bytes // 4. Flags: STATE.yaml > 16384 bytes; PROJECT.md > 6144 bytes; with a managed block, local lines (outside the block and frontmatter) > 150; without one, AGENTS.md > 200 lines.
- Refresh notices: count of `<!-- projectstate-NAME:start -->` blocks plus headings (levels 1-3) containing "Required first action" or "Latest required refresh".
- Owner directives: under a "## Owner directives" heading, lines starting "- YYYY-MM-DD" that contain "until YYYY-MM-DD"; count total and expired (until before today).
- Gate verdict from the template gate's validate(root): invalid (errors), not validated (blockers) or validated; keep the first error or blocker (160 characters).
- Slice: id, status, journey status, human_acceptance, objective (120 characters), next_action (160 characters); risks whose decision is accept_temporarily and whose expiry is within 14 days or past.
- Slice age and churn: first commit whose STATE.yaml contains the current slice id (`git log --reverse --format=%cs -S<id> -- STATE.yaml`); age in days; commits since that date touching STATE.yaml versus all commits since that date. An uncommitted slice has unknown age.
- Silent replacements: commits that changed the `  id:` line of STATE.yaml (`git log --format=%H -G'^  id:' -- STATE.yaml`, newest 50). For each, parse the parent and commit versions (skip unparsable ones). When the id changed and the old slice had status validated or ready_for_human with human_acceptance pending, check whether evidence/<old-id>/summary.md (working tree, else HEAD) contains a "## Owner decision" heading; if not, record {from, to, date}. Compare the working-tree STATE.yaml with HEAD the same way (uncommitted replacement).
- Update branch: a local branch named projectstate/release-<current release> that is not an ancestor of HEAD.

Inbox, in this order:
1. Your decisions: every v6 slice with status validated or ready_for_human and human_acceptance pending: `<repo>: <slice-id> is validated and waits for your decision. Run: python3 <template>/scripts/projectstate_decide.py <absolute repo path> accept|reject|waive "<your words>"` (that script arrives in a later change; print the command anyway).
2. Blocked: status blocked or journey blocked, with the first blocker.
3. Needs review: gate unknown; contract edited or malformed; silent replacements; expired owner directives; risk acceptances expiring or expired.
4. Ready to merge: update branches, with `git -C <path> merge --ff-only <branch>`.

Markdown: title "ProjectState fleet"; one line with generation time, template release (current, and latest marked draft when it is a draft) and root; the line "Read-only: no repository was modified."; the four inbox sections with counts; a v6 table (repository, gate, contract, slice, status, journey, owner, age days, STATE churn, startup tokens, notices, dirty); a table of v5 and other repositories (kind, last commit, dirty); a summary list. JSON carries the same data with "format": "projectstate-fleet/1". Output is deterministic for the same inputs apart from the generation time.

Tests (scripts/test_fleet.py), all in temporary directories with real `git init` repositories and a temporary template root (copy the real gate and helper modules; write a test index and managed block): current, behind and edited gates; missing gate; unmanaged, current and edited contracts; notice counting; awaiting-owner, blocked and expiring-risk inbox items; silent replacement detected without a record and not detected with one; uncommitted replacement; update-branch detection; v5 and other classification; symlinked child skipped; unparsable STATE.yaml reported without stopping the scan; --out inside --root refused; --stdout writes nothing. Prove no writes: hash every file (including .git/index and refs) under the fixture root before and after a default run.

Finally run it once against the real ~/Projects with --stdout. Prove no writes there by comparing, before and after, every repository's `git status --porcelain` output and .git/index mtime plus the sha256 of each STATE.yaml and AGENTS.md. Report the summary counts, the number of inbox items per section, the runtime, and the no-write result. Do not paste the full report.

Report (final message, under 450 words): branch and commit hashes; files changed; exact test commands with pass/fail counts; the real-fleet results above; any deviation and why; known limitations.
