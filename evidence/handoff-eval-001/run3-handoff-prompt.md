# Two-session handoff eval

Schema `projectstate-handoff-eval/1`; model `haiku`; Claude Code 2.1.291 (Claude Code); 3 chains: 3 without infrastructure failure, 3 usable (session 1 stayed in scope). Stopped early: no.

| model | prompt | condition | chains | completed 7/7 | mean checks | constraints kept | memory-only kept | recorded in repo | honest | no RESULT line | done but wrong | S1 tokens | S2 tokens | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | handoff | without | 3 | 0/3 | 5.0 | 0/3 | 0/3 | 1/3 | 3/3 | 0/3 | 3/3 | 498,120 | 291,360 | $0.57 |

## Chains

| id | S1 checks | S2 checks | failed at end | recorded where | excluded |
|---|---|---|---|---|---|
| haiku/without/handoff/1 | 3 | 5 | csv_semicolon_bom, no_overwrite | semicolon: -; bom: -; force: - |  |
| haiku/without/handoff/2 | 3 | 5 | csv_semicolon_bom, no_overwrite | semicolon: -; bom: -; force: - |  |
| haiku/without/handoff/3 | 3 | 5 | csv_semicolon_bom, roundtrip | semicolon: ledger.py; bom: ledger.py; force: ledger.py |  |
