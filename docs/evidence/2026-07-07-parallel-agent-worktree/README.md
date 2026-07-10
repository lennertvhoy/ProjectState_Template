# Evidence: Parallel-Agent Worktree Orchestrator

**Slice:** [BL-PARALLEL-001] Parallel-Agent Worktree Orchestrator  
**Date:** 2026-07-07  
**Agent:** coding-agent  
**Branch:** bl-workflow-002-worktree-brittleness  
**HEAD:** 434f882ea28291584cdcb8b145d39bf35a419e91  
**Proof head:** 434f882ea28291584cdcb8b145d39bf35a419e91  
**Final PR head:** not yet pushed  
**Closure state:** local tests passing; pending push, PR, CI, and remote closure

## Claims

- Claim: StateDD provides a `scripts/statedd_agent_worktree.py` orchestrator that provisions isolated per-agent branches, worktrees, and reservation refs.
  Evidence: `scripts/statedd_agent_worktree.py`, `scripts/test_agent_worktree.py`, `command_outputs/test_agent_worktree.txt`
  Evidence type: implementation | test

- Claim: Existing StateDD scripts are agent-context-aware via `.statedd/agent.context`.
  Evidence: `scripts/statedd_worktree_guard.py`, `scripts/statedd_handoff.py`, `scripts/statedd_audit.py`, `scripts/statedd_closure_check.py`, `scripts/statedd_remote_closure_finalizer.py`
  Evidence type: implementation

- Claim: Git lock contention is detected and reported without deleting lock files.
  Evidence: `scripts/statedd_agent_worktree.py`, `scripts/statedd_worktree_guard.py`, `scripts/test_agent_worktree.py`
  Evidence type: implementation | test

- Claim: Reservation refs prevent branch/worktree double-claiming.
  Evidence: `scripts/statedd_agent_worktree.py`, `scripts/test_agent_worktree.py`
  Evidence type: implementation | test

- Claim: The implementation is validated by regression tests and a CI smoke test.
  Evidence: `scripts/test_agent_worktree.py`, `.github/workflows/validate.yml`, `command_outputs/test_agent_worktree.txt`
  Evidence type: test | ci

- Claim: State, documentation, and skills are updated for parallel-agent support.
  Evidence: `AGENTS.md`, `BACKLOG.md`, `NEXT_ACTIONS.md`, `PROJECT_STATE.yaml`, `docs/failure_scans/BL-PARALLEL-001.md`, `skills/close-slice/SKILL.md`, `prompts/CODING_AGENT_STARTUP_PROMPT.md`
  Evidence type: state_update | docs

## Failure Scan

- Required: yes
- Path: `docs/failure_scans/BL-PARALLEL-001.md`
- Adjacent failures checked: shared-worktree panic, branch collision, git lock races, interleaved pushes, unclassified agent dirt, stale reservations.
- Known bad events covered: concurrent agents on shared worktree, double-claimed branches, lock file corruption, stale reservation refs.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| M | `.github/workflows/validate.yml` | intended_slice_work | CI smoke test for orchestrator |
| M | `AGENTS.md` | intended_slice_work | Parallel-Agent Invariant |
| M | `BACKLOG.md` | intended_slice_work | BL-PARALLEL-001 backlog entry |
| M | `NEXT_ACTIONS.md` | intended_slice_work | Active work entry |
| M | `PROJECT_STATE.yaml` | intended_slice_work | parallel_agent_support section and asset lists |
| M | `prompts/CODING_AGENT_STARTUP_PROMPT.md` | intended_slice_work | Mention agent worktree orchestrator |
| M | `scripts/init_template.py` | intended_slice_work | Propagate new assets downstream |
| M | `scripts/statedd_audit.py` | intended_slice_work | Agent-context-aware audit |
| M | `scripts/statedd_closure_check.py` | intended_slice_work | Agent-context-aware closure check |
| M | `scripts/statedd_handoff.py` | intended_slice_work | Agent-context-aware handoff |
| M | `scripts/statedd_remote_closure_finalizer.py` | intended_slice_work | Agent-context + interleaved-push detection |
| M | `scripts/statedd_upgrade.py` | intended_slice_work | Propagate new assets downstream |
| M | `scripts/statedd_worktree_guard.py` | intended_slice_work | Agent context + lock detection |
| M | `skills/close-slice/SKILL.md` | intended_slice_work | Use orchestrator start/close |
| ?? | `docs/evidence/2026-07-07-parallel-agent-worktree/` | generated_artifact | Evidence bundle for this slice |
| ?? | `docs/failure_scans/BL-PARALLEL-001.md` | generated_artifact | Failure scan document |
| ?? | `scripts/statedd_agent_worktree.py` | intended_slice_work | New orchestrator script |
| ?? | `scripts/test_agent_worktree.py` | intended_slice_work | New regression tests |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | Each non-trivial parallel slice runs in an isolated branch + worktree with a reservation ref; existing scripts detect `.statedd/agent.context` and relax single-agent checks; lock detection fails fast without deleting locks. |
| Is the fix typed/schema/state-machine/validator/contract-based? | The orchestrator is a contract-based CLI with schema-validated agent.context; reservation refs are git-native atomic refs. |
| Which behavior is centralized instead of scattered? | Worktree provisioning, reservation management, and lock detection are centralized in `scripts/statedd_agent_worktree.py`; agent-context detection is centralized in helper functions across consumers. |
| Which observed examples are covered by general rules rather than exact strings? | Branch collision, worktree collision, git lock contention, unclassified agent dirt, interleaved remote pushes, and stale reservations are handled generically. |
| What adjacent cases were tested? | Start creates worktree/reservation, double-reservation fails, guard passes with dirty files, lock detection reports contention, handoff includes agent context, close removes worktree, cleanup removes stale worktree, audit passes in agent context. |
| What brittle pattern was explicitly avoided? | No provider-specific behavior, no keyword buckets, no exact prompt strings, no sleeps/timeouts as authority, no deletion of lock files, no unsafe worktree removal outside `.worktrees/`. |
| Did the slice add keyword buckets, regex branches, exact prompt handling, fixture-only behavior, sleeps/timeouts, global mutable state, silent fallback, or provider-specific assumptions? | No. Lock wait uses bounded polling with clear messaging; worktree removal verifies path under repo-root/.worktrees/. |
| If yes, why is that not the authority path? | Not applicable. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| agent worktree tests | `python3 -m pytest scripts/test_agent_worktree.py -v` | pass (8 passed) |
| existing regression tests | `python3 -m pytest scripts/test_worktree_guard.py scripts/test_remote_closure_finalizer.py -v` | pass (25 passed) |
| full script test suite | `python3 -m pytest scripts/ -q` | pass (152 passed, 4 subtests passed) |
| state docs | `python3 scripts/check_state_docs.py` | pass |
| schema validation | `python3 scripts/statedd_validate_schema.py` | pass |
| orchestrator dry-run smoke | `python3 scripts/statedd_agent_worktree.py --dry-run start --slice-id CI-SMOKE-001` | pass |
| diff whitespace | `git diff --check` | pass |

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Verification logs: `command_outputs/`
- Redaction status: checked

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`
- Endpoint: not applicable
- Process ownership proven: not applicable
- Known limits: Template root has no application runtime.

## Browser Verification

- Browser verification required: not applicable
- Browser verification artifact: not applicable
- Provider used: not applicable
- Fallbacks considered: not applicable
- Known browser verification limits: No user-facing runtime behavior changed in this template-maintenance slice.

## Closure State

- Implemented: yes
- Validated: yes
- Global quality gates passed: yes
- Closure-grade: not yet — requires push, PR, GitHub-visible CI success, and remote closure agreement
- Accepted: no

## Human Override

- Human override used: no

## Risks / What Remains Partial

- GitHub-visible PR, CI, and remote closure remain pending until the branch is pushed.
- Downstream repos do not receive the orchestrator until they generate from or upgrade to this template revision.
