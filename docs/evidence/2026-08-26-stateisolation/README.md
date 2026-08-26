# Evidence: Per-test Git-safety state-root isolation for integration regressions

**Slice:** [BL-STATEISOLATION-001] Integration tests must not inherit ambient machine session state
**Date:** 2026-08-26
**Agent:** opencode integration agent (ox-alpha)
**Branch:** `bl-bl-stateisolation-001-agen-6wnng`
**HEAD:** pending proof commit (final value recorded in `manifest.json`)
**Proof head:** recorded in `manifest.json` after the proof commit; final state commit follows

## Claims

- Claim: The golden-path regression failed spuriously under an ambient read-only
  Git-safety latch in the shared default state root; reproduced on `main` before
  any repair (exit 1, preflight blocked writable isolation).
  Evidence: `repro_before_fix_golden_path.txt`
  Evidence type: command_output
- Claim: After the fix, both integration harnesses (`test_golden_path.py`,
  `test_agent_worktree.py`) pin `PROJECTSTATE_GIT_SAFETY_STATE_ROOT` to a
  per-test isolated root, point the legacy variable at a decoy root holding an
  ambient latch, and pass under that hostile environment (golden path PASS;
  agent-worktree suite 27/27 PASS).
  Evidence: `after_fix_hostile_env.txt`
  Evidence type: implementation, test
- Claim: The decoy root is never consulted or mutated during a passing run;
  the isolated root receives the preflight lock file. A precedence regression
  (legacy variable winning again) would fail loudly against the decoy latch.
  Evidence: `quality_gate_output.txt`
  Evidence type: test
- Claim: Runtime boundary recorded; no application runtime claimed.
  Evidence: `runtime_identity.json`
  Evidence type: runtime_truth

## Failure Scan

- Required: no
- Path: not applicable; test-harness isolation only, production scripts
  unchanged, covered by the authoritative suite.
- Known bad event being closed: ambient Git-safety latch cross-contaminated the
  golden-path regression twice on 2026-08-26 and blocked this slice's own
  preflight until an explicit `--restart-session` restart (third occurrence,
  latch payload inspected: stale `explicit read_only mode selected` from an
  earlier session head).

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| modified/new | files in `git status --short` at verification time | intended_slice_work | BL-STATEISOLATION-001 |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | Session-state truth boundary: machine-wide Git-safety session state must not leak into hermetic regressions; harnesses override both state-root variables unconditionally. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Yes: env-contract precedence documented by `default_state_root()` is enforced by construction, and a byte-compared decoy latch turns any precedence regression into a loud failure. |
| Which behavior is centralized instead of scattered? | One helper per harness (`isolate_git_safety_state`) feeds every subprocess through the central `run()` env merge / `init_repo()` wiring point. |
| Which observed examples are covered by general rules? | Any ambient latch content or location is ignored because the state root is overridden; coverage does not depend on the specific repro fixture. |
| What adjacent cases were tested? | Clean environment, hostile `PROJECTSTATE_`-root, legacy-only hostile root, and full suites under all three; decoy untouched assertion after agent starts. |
| What brittle pattern was explicitly avoided? | No sleeps, no fixture-specific latch paths, no assertions on machine-global directories; decoy byte comparison instead of path guesses. |
| Did the slice add provider-specific assumptions? | No. |
| If yes, why is that not the authority path? | Not applicable. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| defect reproduction (before fix, main) | `PROJECTSTATE_GIT_SAFETY_STATE_ROOT=<latched> python3 scripts/test_golden_path.py` | fail as expected (see `repro_before_fix_golden_path.txt`) |
| hostile-env golden path (after fix) | same command in clone | pass (see `after_fix_hostile_env.txt`) |
| hostile-env agent-worktree suite (after fix) | same command in clone | 27/27 pass |
| clean-env runs (after fix) | `python3 scripts/test_golden_path.py`; legacy-only hostile variant | pass |
| full level-2 gate | `projectstate_quality_gate.py --gate-level 2 --conformance --verbose` | pass; exit 0 (see `quality_gate_output.txt`) |
| evidence manifest strict | `projectstate_evidence_pack.py check . --strict` | pass |

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Redaction status: checked with limits; automated scan passed and manual review completed

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`

## Browser Verification

- Browser verification required: no
- Reason: test-harness-only changes; no user-facing behavior.

## Closure State At Current Worktree

- Implemented: yes; captured at the immutable proof head recorded in `manifest.json`
- Validated locally: yes
- Closure-grade: no until remote finalization
- Remote closure: pending
- Human product acceptance: pending

## Human Override

- Human override used: no
- Stale session latch blocking this slice's own start was cleared through the
  documented `--restart-session` restart path after inspecting and disproving
  the underlying blocker; no permission was repaired automatically.
- Still closure-grade: no, by the Remote Truth Gate

## Risks / What Remains Partial

- Follow-up candidate observed while closing: `projectstate_doctor.py` still
  expects `runtime_identity.v1` while the canonical generator emits v2, so
  doctor reports a cosmetic schema mismatch on healthy packs.
