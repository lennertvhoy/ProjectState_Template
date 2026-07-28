# ProjectState Controlled Benchmark Specification

Status: specification only. No ProjectState performance or superiority claim follows
until repeated paired runs satisfy this protocol.

## Ownership boundary

ProjectState_Template owns immutable public candidate definitions, selection-policy
IDs, render-profile IDs, deterministic generation, schemas, self-tests, and
public-safe fixtures. StatePort owns the no-ProjectState control, isolated runner,
instrumentation, authoritative validators, private holdouts, reports, and result
tiers. Private canary content never enters this repository.

## Compared configurations

Each candidate is pinned by template commit, profile, modules, selection policy,
render profile, generator version, source hashes, and token budget.

1. `control/no-projectstate`: repository and task only; no ProjectState files or hints.
2. `projectstate/eager-human`: all canonical startup files, human rendering.
3. `projectstate/compact-canonical`: task-scoped canonical file selection, unchanged
   human-readable source.
4. `projectstate/modular-statepack`: task-specific selection through the versioned
   StateIR/StatePack contract, with source links and staleness checks.
5. `projectstate/ultra-experimental`: the same selected facts as configuration 4,
   rendered ultra-terse. It is never promoted by token reduction alone.

Selection policy and rendering format are independent experimental factors. An
eager selection may use compact rendering, and a modular selection may use human
rendering, when a factorial run is explicitly registered.

## Paired controls

Within each repository/task/model block, every configuration uses the same:

- sanitized fixture and starting commit;
- task text and hidden acceptance validator;
- model snapshot, tokenizer, tools, permissions, and system instructions other
  than the registered ProjectState treatment;
- runner image, dependency cache policy, network policy, temperature/settings,
  wall-time limit, and token/cost limit;
- pre-seeded dirty state, interrupted state, or failure state where the task
  requires one.

Run order is randomized and recorded. A run gets a fresh clone and process. No
candidate may observe another candidate's output. Provider retries and tool
failures are recorded, never silently discarded.

## Task set

The public task taxonomy includes:

- resume an interrupted feature without losing state;
- detect contradictory canonical state;
- implement and validate a small feature;
- recover safely from a dirty or multi-worktree repository;
- update project state without moving history into live truth;
- prepare evidence without false closure;
- diagnose failing CI without reusing stale results;
- avoid editing the wrong repository or worktree;
- maintain continuity across a fresh session.

StatePort supplies equivalent private holdouts and owns their validators. Tasks
must exercise behavior, not exact strings from public fixtures.

## Measurements

Report every dimension separately:

- task correctness and hidden acceptance failures;
- state integrity, contradiction handling, and stale-state writes;
- false completion and truth-boundary violations;
- privacy, path-confinement, and unsafe-execution violations;
- continuity/resumption fidelity;
- context tokens, total tokens, runtime, cost, and tool calls;
- files loaded, files changed, unnecessary changes, and validation failures;
- unnecessary questions and human interventions.

Do not collapse these into one leaderboard score. Show per-task distributions,
paired deltas, confidence intervals, failure cases, and a Pareto frontier for
correctness/integrity versus context/cost. Safety and false-completion violations
are hard-gate outcomes, not costs that a weighted score may hide.

## Repetition and analysis

Pre-register the model snapshot, configurations, tasks, exclusions, and analysis
before execution. Use at least ten valid paired repetitions per
fixture/task/model block, then add repetitions when intervals remain too wide for
the registered decision. Report all attempted runs and reasons for invalidation.
Use paired bootstrap intervals (or a registered equivalent) and publish raw
public-safe run manifests.

A new default requires repeated evidence that it:

1. introduces no safety, privacy, wrong-repository, or false-closure regression;
2. preserves task correctness and state integrity within the registered
   non-inferiority margin; and
3. improves at least one declared resource dimension without material harm to
   continuity or human intervention.

No margin or promotion threshold is chosen after seeing results.

## Candidate manifest and reproducibility

Each template candidate must expose a machine-readable manifest containing:

- candidate ID/version and immutable template commit;
- profile, modules, selection policy, render profile, and budgets;
- canonical source hashes and generated-pack hashes;
- included/excluded source fields, provenance, lossiness, truncation, and stale
  status;
- estimated tokens plus tokenizer/model-specific counts when available;
- deterministic build and self-test commands.

Generated packs are disposable and non-authoritative. A canonical source change
invalidates a stale pack. StatePort independently validates candidate manifests;
template self-tests cannot change official scoring.

## Explicit exclusions

This specification does not authorize automatic prompt evolution, canonical
state compression, auto-promotion, private-data fixtures, provider-specific
architecture, a StateBench marketplace, or a third benchmark repository.
