# Anti-Brittleness Gate Design

## Authority

The authority path is the structured review, not the scanner.

The gate requires the slice to identify:

- the invariant that prevents the failure class;
- whether the implementation is typed, schema-backed, state-machine-backed,
  validator-backed, or contract-backed;
- which behavior is centralized;
- which observed examples are covered by general rules;
- which adjacent cases were tested;
- which brittle pattern was avoided or justified.

## Scanner Role

`scripts/statedd_brittleness_check.py` is intentionally conservative and
advisory. It can warn on suspicious additions such as large keyword buckets,
many `.includes(...)` checks, exact prompt strings, sleeps/timeouts, silent
fallbacks, temporary production comments, and fixture-only test shapes.

A clean scanner result says only that these heuristics did not fire. It does
not prove that the implementation is durable.

## Audit Role

`scripts/statedd_audit.py` checks whether the latest evidence README contains
the anti-brittleness review markers when the evidence describes a non-trivial
feature/fix/refactor/ops slice. Normal audit warns; `--strict` fails.

This preserves migration compatibility while making the gate enforceable for
new closure-grade slices.
