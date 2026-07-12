# StateDD Maximum-Value Architecture Review

## Verified strengths

- Canonical responsibilities are already separable: `PROJECT_STATE.yaml` is
  current structured truth, `PROJECT_DNA.yaml` stable architecture,
  `NEXT_ACTIONS.md` the short queue, `BACKLOG.md` stable work IDs, `WORKLOG.md`
  append-only history, evidence the claim ledger, and acceptance freezes human
  acceptance. Executable cross-file checks cover key synchronization rules.
- Truth boundaries, worktree isolation, anti-brittleness review, runtime proof,
  evidence manifests, and exact-head remote closure address real false-completion
  failure classes observed in the repository's incident and PR history.
- Profiles now resolve through one declarative catalog with explicit profile and
  module dependencies, capabilities, validation requirements, and owned assets.
- The v2 asset lock now records file lifecycle semantics and base/installed
  hashes that the upgrade engine uses; it is no longer merely an inventory.
- Local and CI validation now enter through the same automatically discovered
  quality gate. Profile/context measurements have one reproducible machine
  artifact at `docs/metrics/profile_metrics.json`; prose does not duplicate its
  exact values.

## Verified weaknesses

- Merged PR #5 demonstrated that passing CI could coexist with skipped suites,
  manually enumerated tests, unsafe upgrade evolution, and stale evidence. The
  previous checks tested artifacts more often than the governing invariant.
- `STATUS.md` remains manually synchronized. It is useful, but only selected
  cross-file fields are currently protected against drift; automatic rendering
  has not yet proved a net usability benefit.
- Historical local-audit, closure-check, and remote-truth tools used overlapping
  closure language. They are now labeled preflights, but compatibility entrypoints
  remain and should be removed only through a versioned migration.
- Profile behavior remains cumulative. `regulated` has an enforceable level-2
  gate and post-merge verifier, but evidence and acceptance controls still depend
  on the claim type and cannot manufacture human acceptance.
- Linux is tested. Windows path forms are rejected at input boundaries, but
  Windows/macOS execution, executable-bit behavior, case collisions, and line
  endings are not CI-proven; cross-platform support must remain qualified.
- No controlled run yet proves that task-scoped loading or StatePack improves
  agent correctness, continuity, or cost over a simpler workflow.
- Historical evidence and ledgers already contain absolute local paths from
  earlier slices. Current/generated canonical state now uses portable repo-root
  identity, but removing legacy path disclosure requires an explicit history and
  Git-history privacy decision rather than silently rewriting append-only truth.
- `check_state_docs.py` still contains a large legacy template-asset list and
  exact prose-marker assertions alongside the new catalog. This is duplicate
  authority and brittle maintenance debt; migrate it incrementally to catalog,
  schema, and structural checks rather than rewriting a closure-critical gate in
  the same repair slice.
- Capability IDs remain descriptive interface labels. Validation IDs now dispatch
  concrete gate-level and asset-presence contracts; only those validations are
  proof that a generated profile contains its claimed controls.

## Deletion and simplification opportunities

- Delete hand-maintained script/file catalogs from live state and nested
  instructions; filesystem discovery, the profile catalog, CLI help, and tests
  already provide fresher authority.
- Keep one local validation entrypoint. Focused commands remain edit-loop tools,
  not a second closure pipeline.
- Retire `statedd_closure_check.py` and the compatibility label
  `closure_label` in a future breaking release after downstream usage is known;
  until then they must explicitly stop at local preflight or pushed state.
- Keep `STATUS.md` small and synchronized by checks. Do not build an automatic
  renderer until drift frequency, agent comprehension, and human edit friction
  are measured.
- Do not add a script, skill, command, schema, and prose page for every concern.
  A reusable workflow earns a skill; a deterministic invariant earns code; a
  one-off judgment stays in the active slice.

## Architecture decisions

- Readable canonical StateDD remains authority. StateIR is derived and
  source-linked; StatePack is task/model/budget-specific, disposable, stale when
  canonical sources change, and never hand-edited.
- Startup selection is task-scoped. Architecture, history, evidence, and
  inventories load on demand. Selection policy remains independent of rendering
  format; ultra-terse rendering stays experimental.
- StateDD_Template owns generic workflow contracts, candidate policies, schemas,
  deterministic self-tests, and public-safe fixtures. StatePort already owns the
  StateIR/StatePack compiler and independent benchmark evaluator; this repository
  will not duplicate them.
- The profile catalog is a declarative module composition contract, not an
  executable plugin system or marketplace. Modules require stable ID/version,
  dependencies/conflicts, assets, capabilities, validation, and upgrade rules.
- Managed-file behavior uses distinct lifecycle fields and merge strategies.
  Project truth is preserved, history is append-only, pristine template assets
  may be replaced, generated controls regenerate transactionally, and removals
  are reported rather than silently deleted.
- A checked artifact cannot contain the SHA of the commit that contains itself.
  Metrics and evidence record a measured proof commit/tree; the finalizer allows
  only explicitly allowlisted metadata changes between proof and final heads.
- Implemented, locally validated, pushed, PR-opened, CI-verified, merged, and
  human-accepted remain separate states. Only the exact-head remote finalizer may
  establish closure-grade remote agreement.

## Benchmark gaps

The controlled protocol is specified in
`docs/benchmarks/STATE_DD_BENCHMARK_SPEC.md`. Missing evidence includes the
no-StateDD control, repeated paired tasks, independent hidden validators,
model/tokenizer-pinned execution, continuity measurements, safety violation
rates, confidence intervals, and Pareto comparisons. Token reduction alone is
not evidence of better agent performance.

## Recommended dependency order

1. Finish and remotely prove the current lifecycle/gate/evidence repair.
2. Execute exactly one next slice: **worktree ownership lifecycle hardening**.
   Expected impact is high because every parallel slice depends on attribution;
   cost is medium; it reduces stale/forged context, reservation, wrong-worktree,
   and cleanup risk; dependencies are present; temporary-Git tests can measure
   duplicate reservations, path/branch mismatch, stale ownership, and idempotent
   cleanup deterministically.
3. After that gate, expose a versioned template-side benchmark candidate contract
   and StatePack conformance fixtures without implementing another compiler.
4. Let StatePort run the independent benchmark. Change defaults only after
   repeated paired evidence.

## Explicit non-goals

- No StateIR/StatePack compiler duplication in StateDD_Template.
- No marketplace, arbitrary executable plugins, automatic prompt evolution,
  canonical caveman-language rewrite, auto-promotion, or one-number leaderboard.
- No silent semantic merge of customized project truth, destructive asset
  removal, force-push, PR merge, or CI/acceptance claim inferred from local tests.
- No private learner/canary data, absolute personal paths in public artifacts, or
  official benchmark holdouts/scores in this repository.
