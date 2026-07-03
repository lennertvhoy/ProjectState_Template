# Incident Analysis: Dirty Shared Worktree Local-Only Claims

## Failure Class

- Severity: P1 workflow hardening issue.
- Classes: `state_truth`, `workflow`, `brittleness`.

## Observed Pattern

```text
dirty shared worktree
-> agent creates local-only files
-> refuses commit because unrelated dirt exists
-> handoff claims local files exist
-> GitHub source of truth does not contain them
-> next reviewer sees contradiction
```

## Missing Boundary

Remote closure catches the contradiction at the end, but it does not prevent a
long-running coding-agent slice from starting in an ambiguous local worktree.

## Added Boundary

- `scripts/statedd_worktree_guard.py --mode start-slice` reports repo root,
  branch, origin, upstream, HEAD comparison, worktree topology, dirty files, and
  classification status before implementation.
- `scripts/statedd_worktree_guard.py --mode classify-dirty` prints a dirty-file
  classification table.
- `scripts/statedd_worktree_guard.py --mode closure` fails dirty worktrees.
- Handoffs now expose worktree topology, upstream comparison, GitHub-visible
  deliverables, and local-only files.

## Second Failure Pattern

Agents can solve observed examples through brittle prompt-specific, string,
keyword, fixture-only, timeout, silent fallback, or provider-specific behavior.

## Added Anti-Brittleness Boundary

- `ANTI_BRITTLENESS_GUARD.md` and
  `docs/quality_gates/ANTI_BRITTLENESS_GATE.md` define the review questions.
- `prompts/SLICE_CONTRACT_TEMPLATE.md`, `prompts/EVIDENCE_README_TEMPLATE.md`,
  and `prompts/CTO_REVIEW_CHECKLIST.md` require the review for non-trivial
  fix/feature slices.
- `scripts/statedd_brittleness_check.py` gives advisory warnings without
  pretending to prove quality.
