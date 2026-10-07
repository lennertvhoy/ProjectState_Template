# Documentation

Reference and migration documentation. The user guide for the template is the
repository root `README.md`. The current outcome, slice, and proof live in
`PROJECT.md`, `STATE.yaml`, and `evidence/`, never here.

## Files

- `GETTING_STARTED_5_MIN.md` - short first-setup path for a new or adopted project
- `WORKFLOW_FOR_BEGINNERS.md` - the outcome-first workflow on one page
- `WORKED_EXAMPLE.md` - a runnable lesson: a packaged product fails, is handed off, and recovers
- `UPGRADING.md` - updating a v6 project to the current release, and migrating a v5 project
- `adr/` - architecture decision records; accepted ADRs are history
- `benchmarks/PROJECTSTATE_BENCHMARK_SPEC.md` - the controlled benchmark specification (a specification only)

## Rules

- Put proof for a slice in `evidence/<slice-id>/summary.md`, not here.
- Do not use generated or temporary paths as durable references.
- History lives in Git, the ADRs, and `CHANGELOG.md`. The v5 documents live at
  tag `v5-final`.
