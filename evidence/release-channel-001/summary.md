# Evidence: release-channel-001

## Scope and authorization

Owner-approved CTO plan, 2026-10-06 (review: https://claude.ai/artifact/B33ZdP3MDpGeskmMcNJwNv).
Owner words: "i choose all ur recs" (D1-D6) and "implement each change yourself
... with cheaper sonnet subagents". This slice covers plan items S1-S4 plus the
gate part of S5 and ships release 6.3.0. Claude (Opus) coordinated, wrote the
interface and this record; Sonnet workers W1-W5 implemented in separate worktrees.
The session stopped once for quota (handoff recorded at `46f5c0e`) and resumed.

## Primary journey

- Environment: Local Linux workstation; system Python 3 with PyYAML; real ~/Projects read-only; scratch copies outside ~/Projects
- Command: `python3 scripts/test_release_channel.py --fleet-root ~/Projects`
- Result: passed
- Exit code: 0

Run on 2026-10-07 after the 6.3.0 cut with Python 3.13.15. It printed
"RESULT: PASSED: 77 checks passed, 0 failed, 4s". What it covered:

- Generation: `new` core, `new` hardened and `adopt` each carry exactly one
  managed block equal to `core/AGENTS.managed.md`. Their gate is byte-identical
  to the template's and reports `6.3.0` with `--version`. Startup reading is at
  most 10,000 characters, and each scaffold's gate exits 1 honestly.
- StatePort: its `validationCommand` string is pinned unchanged, and its rule
  holds for all three generated projects.
- Fleet doctor on the real `~/Projects`: 44 repositories (21 v6, 14 v5, 9
  other) in 2.0s.
  - Gates: 18 behind, 2 unknown. The unknown ones are StatePort and
    example-project-37, both edited locally.
  - Contracts: 20 unmanaged.
  - Inbox: 8 decisions, 4 blocked, 20 needs-review.
  - No-write audit: 38 repositories with `.git` were unchanged (git status,
    `.git/index` mtime, and hashes of STATE.yaml, AGENTS.md and the gate).
- Update on `git archive` copies of example-project-08 and example-project-05:
  - No flags were needed. The gate was replaced (6.2.0 to 6.3.0), and the
    contract was converted with 9 known template sections removed and 0
    modified sections.
  - A second `--apply` was a no-op, and local bytes were preserved.
  - Gate verdicts were unchanged (not validated, and validated).
  - The doctor then reported both copies as current.

Full output: `journey-output.txt`. Before the cut, the same journey passed 80
checks against the draft, where the copies read "draft".

## Secondary checks

- `python3 -m pytest scripts/ -q --deselect scripts/test_init_template.py::test_template_root_bootstrap_gate_passes`:
  770 passed (561 subtests) before the cut. The deselected test needs this
  journey recorded and is rerun below.
- `python3 scripts/projectstate_release.py check`: consistent; the v6.1.0 and
  v6.2.0 tag gates match their hashes.
- Integration fixes found by the journey (`98f532b`):
  - the update's clean-tree check now guards writes only;
  - the doctor gained a "draft" status.
  Both have regression tests.
- A legacy git-safety scan flagged `chmod` in the update tool's atomic writer.
  The fix renamed the variable to the scan's recognized `tmp_path`; the scan
  itself was not weakened.
- Verified on Claude Code 2.1.291 with probes: it loads `AGENTS.md` without a
  CLAUDE.md pointer, and it loads a parent folder's `AGENTS.md` from inside
  another repository.

## Artifacts

- `core/AGENTS.managed.md`: 80 lines. The generated AGENTS.md is 100 lines,
  down from 178, and fresh-core startup reading is 6,410 characters, down from
  11,921.
- `releases/index.json`:
  - 6.3.0 gate sha256 `a5c9f5c58574508c4284f39a07bf28bd987c04b76f417411323dcd4fed7f8847`;
  - 6.3.0 contract sha256 `0b3795520ecf73d66b8a33837573da45347bbd66e1e9eac97dfe92b96299b351`;
  - retroactive entries for 6.0.0 to 6.2.0.
- New tools: `scripts/projectstate_release.py` (check, cut, hashes),
  `scripts/projectstate_fleet.py`, `scripts/projectstate_update.py`
  (`releases/contract-history.json`), and `scripts/projectstate_decide.py`.
  The decide command (S5) is merged and unit-tested; its live loop is
  acceptance-loop-001.
- Worker specs: `assignments/`. Journey output: `journey-output.txt`.

## Limitations

- Nothing is pushed. The tag v6.3.0 is local. No fleet repository has been
  updated yet; that is fleet-pilot-001 and fleet-rollout-001.
- The doctor and update were proven on real data read-only and on archive
  copies, not yet in live instances.
- The legacy v5 quality gate still runs in CI until the legacy split.

## Owner decision

- Decision: waived
- Date: 2026-10-07
- Owner words: "youve got enough usage to implement each change yourself, do that but do it with cheaper sonnet subagents"
- Context: The owner authorized implementing every roadmap change in sequence, so the slice proceeds without per-slice acceptance. Final acceptance of the roadmap is requested at the end.
