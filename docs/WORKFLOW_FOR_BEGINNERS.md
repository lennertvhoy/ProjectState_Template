# Outcome-first workflow for beginners

ProjectState keeps an agent from confusing busy work with a working product.

```text
PROJECT.md                 STATE.yaml
human-owned outcome  ---> one current slice
                               |
                               v
                       primary user journey
                               |
                     +---------+---------+
                     |                   |
                   fails               passes
                     |                   |
          simplify the assumption       v
                     |          secondary checks may
                     +--------> add blockers only
                                         |
                                         v
                                human accepts or rejects
```

## The four files

- `PROJECT.md`: who the product is for and what observable outcome matters.
- `STATE.yaml`: the one thing being delivered now and its exact next action.
- `AGENTS.md`: what an agent may change and where it must stop.
- `evidence/<slice-id>/summary.md`: what actually ran, where, and with what result.

You do not need a mandatory backlog, worklog, release ledger, architecture file,
or multi-agent matrix to start. Add one only when it solves a real coordination
problem.

## A normal session

1. Read the three root files.
2. Try the primary journey early.
3. Change the smallest amount of product code needed.
4. Rerun the journey and record honest evidence.
5. Run relevant tests and checks.
6. Update `STATE.yaml` and hand off the exact next action.

On resume, compare the recorded next action with the actual worktree and the
current evidence. Preserve a failed journey until it has been rerun successfully.
If code or packaging changes invalidate an earlier pass, rerun the affected
journey before claiming validation again.

If the journey fails, the result is not validated—even if thousands of unit tests
pass. If the same boundary fails twice, stop adding machinery and simplify one
assumption first.

Keep journey status to `not_run`, `passed`, `failed`, or `blocked`. For example,
publishing an installer while its intended Windows test machine is unavailable
is supporting progress; the Windows journey stays `blocked` or `not_run`.

The [worked example](WORKED_EXAMPLE.md) demonstrates a source run passing while
its packaged launcher fails, then resumes from the saved handoff and recovers.

## Who decides what

The human owns outcome, scope, acceptance, governance, risk exceptions, and
product acceptance. The agent owns implementation and honest observation inside
those boundaries. The agent can propose a changed rule; it cannot adopt that rule
to grade its own work.

## When to harden

Use the `hardened` profile for a named security, compliance, review, or delivery
obligation. Hardened checks can stop a release. They can never transform a failed
user journey into a passing product.
