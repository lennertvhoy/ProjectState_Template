# Evidence: BL-GIT-ISOLATION-001 Git metadata safety boundary

**Slice:** [BL-GIT-ISOLATION-001] Repair Git metadata safety and agent isolation  
**Date:** 2026-07-11  
**Agent:** coding-agent  
**Branch:** bl-git-isolation-001  
**HEAD:** c2fe7b25625cc855a47deff721251cdb5d4141b2  
**Proof head:** pending commit  
**Closure state:** targeted local validation; quality freeze remains active

## Claims

- Claim: The initiating repository mutation and StateDD's causal contribution are
  recorded as separate causes.
  Evidence: `docs/incidents/20260711-141533-git-object-ownership-permission.md`
  Evidence type: known_bad_event

- Claim: One centralized executable reports and decides requested/canonical repo
  identity, Git/common directories, UID/GID, nested ownership, real writability,
  fsck, mandatory synchronization, worktree topology, runtime identity, isolation,
  and external read-only latching.
  Evidence: `scripts/statedd_git_safety_check.py`,
  `schemas/git_safety_report.schema.json`, `git_safety_report.json`
  Evidence type: implementation

- Claim: Containers and independent agents default to full clones; linked worktree
  creation is blocked unless explicitly opted into on a trusted local same-identity
  runtime.
  Evidence: `scripts/statedd_agent_worktree.py`,
  `scripts/test_agent_worktree.py`, `scripts/test_git_safety_check.py`
  Evidence type: test

- Claim: StateDD has no automatic production path for permission repair,
  destructive reset/clean, Git garbage collection, worktree pruning, forced
  worktree removal, or forced branch deletion.
  Evidence: AST/static regression in `scripts/test_git_safety_check.py`
  Evidence type: adversarial

- Claim: The reported Git object-write permission error class is reproduced only
  in a disposable repository and blocked by the general metadata policy.
  Evidence: `test_exact_git_object_permission_error_is_reproduced_safely` and
  `test_unwritable_objects_fails` in `scripts/test_git_safety_check.py`
  Evidence type: known_bad_event

## Failure Scan

- Required: yes
- Path: `docs/failure_scans/BL-GIT-ISOLATION-001.md`
- Adjacent failures checked: objects/refs/logs/worktree metadata; nested foreign
  owner; fetch failure and restart latch; root container; unknown/mismatched
  worktree identity; clone alternates/hardlinks; stale/dirty worktrees; locks;
  fsck failure; critical Git-read failure; schema validation; forbidden cleanup.
- Known bad events covered: reported 2026-07-11 shared object-database permission
  failure. The verbatim originating transcript remains not currently locatable.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| M | `.github/workflows/validate.yml` | intended_slice_work | CI regression propagation |
| M | `AGENTS.md` | intended_slice_work | constitutional Git safety invariant |
| M | `BACKLOG.md` | intended_slice_work | P0 supersession |
| M | `EFFICIENCY_BUDGET.yaml` | intended_slice_work | mandatory core safety asset cost |
| M | `INCIDENT_RESPONSE.md` | intended_slice_work | causal separation and naming contract |
| M | `NEXT_ACTIONS.md` | intended_slice_work | P0-only active queue |
| M | `PROJECT_DNA.yaml` | intended_slice_work | durable isolation invariant |
| M | `PROJECT_STATE.yaml` | intended_slice_work | quality freeze/current truth |
| M | `README.md` | intended_slice_work | safe startup guidance |
| M | `STATUS.md` | intended_slice_work | human current truth |
| M | `commands/statedd-close-slice.md` | intended_slice_work | preflight before closure writes |
| M | `commands/statedd-ingest-bad-event.md` | intended_slice_work | correct execution-mode field |
| M | `commands/statedd-quality-freeze.md` | intended_slice_work | repo-mode/ledger correction |
| M | `docs/ADOPTION_PROFILES.md` | intended_slice_work | clone-default team policy |
| M | `docs/EVIDENCE_LOG.md` | intended_slice_work | incident evidence ledger |
| M | `docs/failure_scans/BL-PARALLEL-001.md` | intended_slice_work | append-only supersession note |
| M | `docs/superpowers/specs/2026-07-07-parallel-agent-worktree-orchestrator-design.md` | intended_slice_work | superseded design warning |
| M | `prompts/CODING_AGENT_STARTUP_PROMPT.md` | intended_slice_work | single fail-closed startup transaction |
| M | `prompts/CTO_REVIEW_CHECKLIST.md` | intended_slice_work | Git safety review fields |
| M | `prompts/CTO_SESSION_PROMPT.md` | intended_slice_work | generated implementation contract |
| M | `prompts/EVIDENCE_README_TEMPLATE.md` | intended_slice_work | safety evidence shape |
| M | `prompts/FINAL_HANDOFF_TEMPLATE.md` | intended_slice_work | required safety handoff fields |
| M | `prompts/OPENCODE_STARTUP_PROMPT.md` | intended_slice_work | single fail-closed startup transaction |
| M | `prompts/SLICE_CONTRACT_TEMPLATE.md` | intended_slice_work | safety/isolation scope |
| M | `schemas/evidence_readme_contract.json` | intended_slice_work | optional Git safety marker |
| M | `schemas/final_handoff_contract.json` | intended_slice_work | required safety markers |
| M | `scripts/AGENTS.md` | intended_slice_work | executable catalog correction |
| M | `scripts/README.md` | intended_slice_work | script documentation |
| M | `scripts/check_state_docs.py` | intended_slice_work | asset/CI/handoff contract validation |
| M | `scripts/init_template.py` | intended_slice_work | every-profile propagation |
| M | `scripts/statedd_agent_worktree.py` | intended_slice_work | clone default and report-only cleanup |
| M | `scripts/statedd_handoff.py` | intended_slice_work | safety report handoff rendering |
| M | `scripts/statedd_upgrade.py` | intended_slice_work | mandatory safety migration assets |
| M | `scripts/statedd_validate_schema.py` | intended_slice_work | evidence report validation |
| M | `scripts/statedd_worktree_guard.py` | intended_slice_work | centralized authority integration |
| M | `scripts/test_adoption_profiles.py` | intended_slice_work | footprint budget regression |
| M | `scripts/test_agent_worktree.py` | intended_slice_work | clone/worktree/cleanup regressions |
| M | `scripts/test_init_template.py` | intended_slice_work | generated safety assets |
| M | `scripts/test_schema_validation.py` | intended_slice_work | schema propagation regression |
| M | `scripts/test_upgrade.py` | intended_slice_work | security migration regression |
| M | `scripts/test_worktree_guard.py` | intended_slice_work | fail-closed compatibility regression |
| M | `skills/close-slice/SKILL.md` | intended_slice_work | safe isolation/retained cleanup |
| M | `skills/ingest-bad-event/SKILL.md` | intended_slice_work | correct execution-mode field |
| M | `skills/quality-gate/SKILL.md` | intended_slice_work | Git safety gate step |
| ?? | `commands/statedd-git-safety.md` | intended_slice_work | new command wrapper |
| ?? | `docs/adr/0001-git-isolation-safety-boundary.md` | intended_slice_work | architecture decision |
| ?? | `docs/evidence/2026-07-11-git-isolation-safety/` | generated_artifact | slice evidence |
| ?? | `docs/failure_scans/BL-GIT-ISOLATION-001.md` | intended_slice_work | P0 failure scan |
| ?? | `docs/incidents/20260711-141533-git-object-ownership-permission.md` | intended_slice_work | P0 incident |
| ?? | `schemas/git_safety_report.schema.json` | intended_slice_work | machine-readable report contract |
| ?? | `scripts/statedd_git_safety_check.py` | intended_slice_work | centralized preflight |
| ?? | `scripts/test_git_safety_check.py` | intended_slice_work | 17 incident/adjacent regressions |
| ?? | `skills/git-safety/` | intended_slice_work | new skill wrapper |

## Git Safety

- Report: `git_safety_report.json`
- Requested path: `/home/ff/Documents/Projects/StateDD_Template`
- Canonical repo root: `/home/ff/Documents/Projects/StateDD_Template`
- Git directory / common directory: both
  `/home/ff/Documents/Projects/StateDD_Template/.git`
- Effective UID/GID: `1000/1000` (`ff:ff`)
- Runtime/container classification: host, unprivileged, no risky capabilities
- Metadata ownership/writability result: 828 entries scanned completely; zero
  mismatches, unreadable/unwritable entries, symlinks, locks, or hardlinked objects
- Write-probe result: pass for repo root, common/Git directory, objects, refs,
  logs, and worktrees; no residue
- Git fsck result: pass (`git fsck --no-dangling`)
- Mandatory synchronization result: pass (`fetch --prune origin`, automatic
  maintenance disabled)
- Selected isolation mode: `worktree`, explicit trusted-local opt-in for this
  already-running repair; no new worktree was created
- Worktree topology: six registered paths, all UID/GID matches; the current path
  and one pre-existing sibling were dirty and were not modified or cleaned
- Mutation permitted: yes
- Read-only latch/restart status: a prior rejected `normal_branch` attempt was
  diagnosed, then the explicit repaired-mode restart passed; this saved report
  records a fresh permit (`restart_session=true`, latch inactive)
- Enforcement scope: StateDD-managed session permit; no OS read-only mount was proven

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | No StateDD-managed mutation until one transaction proves identity, common-directory metadata safety, real writes, fsck, synchronization, and a permitted isolation mode; failure selects read-only. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Yes. `statedd.git_safety_report.v1` is schema validated; policy is centralized and the external latch represents the failed-session state. |
| Which behavior is centralized instead of scattered? | Runtime/UID detection, recursive metadata inspection, probes, fsck, fetch, post-fetch scan, isolation decision, and latch handling live in one script. |
| Which observed examples are covered by general rules rather than exact strings? | Any foreign/unwritable/unreadable/symlinked/locked metadata and any failed mandatory Git command blocks; the original permission string is test evidence only. |
| What adjacent cases were tested? | Objects, refs, logs, worktrees, root/unknown identity, containers, alternates/hardlinks, dirty/stale paths, locks, fsck/fetch/read failures, schema, and cleanup prohibitions. |
| What brittle pattern was explicitly avoided? | No prompt authority, permission-error string routing, fixture-only production rule, sleep synchronization, silent success fallback, or provider-specific isolation rule. |
| Did the slice add keyword buckets, regex branches, exact prompt handling, fixture-only behavior, sleeps/timeouts, global mutable state, silent fallback, or provider-specific assumptions? | Runtime classification uses multiple conservative signals and a bounded subprocess timeout; no one string grants permission, unknown blocks shared modes, and no sleep/fallback is an authority path. |
| If yes, why is that not the authority path? | Marker/cgroup tokens add container evidence only. Permission depends on the complete typed report and mode policy. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| incident regressions | `python3 scripts/test_git_safety_check.py` | pass (17 tests) |
| worktree guard | `python3 scripts/test_worktree_guard.py` | pass (11 tests) |
| isolation orchestrator | `python3 scripts/test_agent_worktree.py` | pass (12 tests) |
| initializer | `python3 scripts/test_init_template.py` | pass (25 tests) |
| profiles | `python3 scripts/test_adoption_profiles.py` | pass (9 tests) |
| upgrade migration | `python3 scripts/test_upgrade.py` | pass (12 tests) |
| schema validation | `python3 scripts/statedd_validate_schema.py` | pass after report regeneration |
| state hygiene | `python3 scripts/check_state_docs.py` | pass after report regeneration |
| instruction lint | `python3 scripts/statedd_instruction_lint.py --fail-on error` | pass; advisory warnings remain |
| actual Git safety preflight | `python3 scripts/statedd_git_safety_check.py --mode worktree --worktree-opt-in --trusted-local-machine --restart-session` | pass; permit recorded; latch inactive |
| full template quality gate | `python3 scripts/statedd_quality_gate.py --gate-level 2` | not yet run |
| remote/CI closure | GitHub Actions + remote closure finalizer | not proven |

## Evidence Pack Manifest

- Manifest: `manifest.json` (to be generated after command outputs are final)
- Redaction status: pending

## Runtime Identity

- Runtime required: no application runtime; operator/Git runtime proof required
- Artifact: `git_safety_report.json`; template-not-applicable runtime artifact remains optional
- Endpoint: not applicable
- Process ownership proven: Git safety effective identity observed; application process not applicable
- Known limits: original external actor is not proven

## Browser Verification

- Browser verification required: no
- Browser verification artifact: not applicable
- Provider used: not applicable
- Fallbacks considered: not applicable
- Known browser verification limits: no user-facing application/runtime change

## Closure State

- Implemented: yes
- Validated: targeted checks only
- Global quality gates passed: not yet
- Closure-grade: no
- Accepted: pending

## Human Override

- Human override used: no

## Risks / What Remains Partial

- Full template tests, quality gate, evidence manifest, clean commit, remote branch,
  PR, final-head GitHub Actions, and remote closure are not yet proven.
- `read_only` is enforced by StateDD-managed entrypoints/policy, not an OS mount.
- POSIX UID/GID and mode checks do not prove every ACL/NFS/Windows permission edge;
  unknown runtime/identity semantics block shared worktree modes.
- The actor, exact command, timestamp, and verbatim original failure transcript
  remain not proven.
- Existing linked worktrees remain registered and one sibling is dirty; they were
  reported and preserved, not automatically removed.
