# CTO Review Checklist

After every coding-agent handoff, the CTO lane must explicitly answer these
questions. This makes review repeatable instead of vibes-based.

```text
Closure verdict: accepted / rejected / conditionally accepted

Reason:
- ...

Missing proof:
- ...

Contradictions:
- ...

Repo hygiene:
- clean / dirty / unknown

Worktree/source-of-truth:
- worktree topology captured: yes / no
- upstream comparison: local equals upstream / differs / not proven
- GitHub-visible deliverables: yes / no / not proven
- local-only files claimed: yes / no

Product value:
- real / cosmetic / unclear

Anti-brittleness:
- invariant named: yes / no / not applicable
- authority path typed/schema/state-machine/validator/contract-based: yes / no / not applicable
- adjacent cases tested: yes / no / not applicable
- brittle easy-way-out avoided or justified: yes / no / not applicable

Next best slice:
- ...
```

## How To Use

1. Read the handoff and evidence README first.
2. Run or review `scripts/statedd_doctor.py` for a quick shared snapshot.
3. Check `scripts/statedd_audit.py` output if available.
4. Check `scripts/statedd_worktree_guard.py --mode closure` output when available.
5. Confirm runtime identity proof was captured for user-facing claims.
6. Confirm schema ownership rules were followed if a schema changed in this slice.
7. Confirm the anti-brittleness gate was answered for non-trivial fix or feature work.
8. Look for overrides and confirm they are recorded honestly.
9. Do not accept closure-grade unless the audit passes or the override is explicit.
10. Paste the completed checklist into the handoff thread before choosing the next slice.

## Optional Checklist Table

```text
- [ ] Evidence README claim ledger reviewed
- [ ] Runtime identity proof verified (for user-facing changes)
- [ ] Schema ownership validated (for schema changes)
- [ ] Worktree topology and upstream comparison reviewed
- [ ] Anti-brittleness review completed (for non-trivial fix/feature slices)
- [ ] Human override recorded correctly, if any
- [ ] Audit passes or explicit override documented
```
