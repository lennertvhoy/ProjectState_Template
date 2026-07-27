# Anti-Brittleness Guard

**Purpose:** Prevent feature and fix slices from closing by only matching the
observed failing example.

This guard is a review contract, not a keyword scanner. The optional
`scripts/projectstate_brittleness_check.py` helper can warn about suspicious shapes,
but the closure authority is the anti-brittleness review in the slice contract,
evidence README, and CTO review.

## Closure Rule

A non-trivial fix or feature slice is not closure-grade if it only handles the
observed failing input without a durable invariant.

Closure-grade work must identify the general failure class, name the invariant
that prevents it, and show adjacent cases or adversarial checks that exercise
that invariant.

## Required Review Questions

Every non-trivial fix or feature slice answers:

- What invariant prevents the failure class?
- Is the fix typed, schema-backed, state-machine-backed, validator-backed, or
  contract-backed?
- Which behavior is centralized instead of scattered?
- Which observed examples are covered by general rules rather than exact strings?
- What adjacent cases were tested?
- What brittle pattern was explicitly avoided?
- Did the slice add keyword buckets, regex branches, exact prompt handling,
  fixture-only behavior, sleeps/timeouts, global mutable state, silent fallback,
  or provider-specific assumptions?
- If yes, why is that not the authority path?

## Brittle Shapes To Challenge

- Large ad hoc keyword arrays as routing authority.
- Many scattered `.includes(...)` or substring branches.
- Exact prompt, fixture, screenshot, or provider-output strings in production
  behavior paths.
- Sleeps or timeouts used as synchronization without an event/state proof.
- Catch-all fallback that suppresses errors or turns unknown states into success.
- Tests that prove only the observed input and no adjacent cases.
- Global mutable state used to patch sequencing instead of expressing the state
  transition directly.

## Evidence

Use `docs/quality_gates/ANTI_BRITTLENESS_GATE.md` for the reusable gate wording.
Record the completed answers in the evidence README for the slice.
