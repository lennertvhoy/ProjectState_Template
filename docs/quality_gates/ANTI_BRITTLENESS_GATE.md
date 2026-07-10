# Anti-Brittleness Gate

This gate applies to every non-trivial feature or fix slice. It is intentionally
semi-executable: a warning script may help, but a human or CTO review must still
confirm that the implementation follows a durable invariant.

## Required Answers

Record these answers in the evidence README:

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | |
| Is the fix typed/schema/state-machine/validator/contract-based? | |
| Which behavior is centralized instead of scattered? | |
| Which observed examples are covered by general rules rather than exact strings? | |
| What adjacent cases were tested? | |
| What brittle pattern was explicitly avoided? | |
| Did the slice add keyword buckets, regex branches, exact prompt handling, fixture-only behavior, sleeps/timeouts, global mutable state, silent fallback, or provider-specific assumptions? | |
| If yes, why is that not the authority path? | |

## Optional Heuristic Scan

Run when the slice touches production code or routing/classification behavior:

```bash
python3 scripts/statedd_brittleness_check.py
```

The scan may warn about large keyword buckets, repeated `.includes(...)` checks,
exact prompt strings, sleep/timeout synchronization, silent catch-all fallbacks,
temporary comments, and fixture-only tests. A clean scan is not proof of quality.

## Closure Language

A slice that only handles the observed failing input without a durable invariant
is not closure-grade.
