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

Product value:
- real / cosmetic / unclear

Next best slice:
- ...
```

## How To Use

1. Read the handoff and evidence README first.
2. Run or review `scripts/statedd_doctor.py` for a quick shared snapshot.
3. Check `scripts/statedd_audit.py` output if available.
4. Confirm runtime identity proof was captured for user-facing claims.
5. Confirm schema ownership rules were followed if a schema changed in this slice.
6. Look for overrides and confirm they are recorded honestly.
7. Do not accept closure-grade unless the audit passes or the override is explicit.
8. Paste the completed checklist into the handoff thread before choosing the next slice.

## Optional Checklist Table

```text
- [ ] Evidence README claim ledger reviewed
- [ ] Runtime identity proof verified (for user-facing changes)
- [ ] Schema ownership validated (for schema changes)
- [ ] Human override recorded correctly, if any
- [ ] Audit passes or explicit override documented
```
