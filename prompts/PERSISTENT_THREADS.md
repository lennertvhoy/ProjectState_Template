# Optional persistent threads

Read `AGENTS.md`, `PROJECT.md`, and `STATE.yaml` first. Use this workflow only
when the human selects it and one current slice has useful separable tasks.
These prompts are optional conveniences, not new policy or current state.

## When it earns its cost

A coordinator can keep planning and review focused while other threads perform
bounded implementation. Start with a coordinator and one worker; add a reviewer
or specialist only for concrete work. Do small or tightly coupled changes in one
thread. Names describe responsibilities, not access permissions or model ability.

| Role | Responsibility | Returns |
| --- | --- | --- |
| Coordinator | Decompose the slice, assign work, integrate, maintain state | Integrated changes, journey evidence, next action |
| Implementation | Change only the assigned area | Patch or commits, commands and results, limitations |
| Verification | Inspect the actual changes and exercise behavior | Reproducible findings and independent proof |
| Documentation | Clarify instructions and recovery context | Small diff preserving authority and failure evidence |
| Specialist | Investigate a named security, performance, or domain risk | Consequence, exposure, affected environment, evidence, recommendation |

Choose models using the user's available tools, task difficulty, risk, and
observed performance. Strong reasoning is useful for ambiguity, integration, and
review; narrow work may suit a lower-cost model. Model names, prices, and usage
limits are not template policy. Do not promise savings from someone else's
reported results. If measurement is available, compare total usage and elapsed
time for a validated slice, including every thread and correction. If it is not
available, record savings as unknown; do not create a mandatory metrics ledger.

## Assignment and return

The coordinator names the repository, slice, worker, and starting revision.
Concurrent writers use separate private branches and worktrees, or independent
clones when project rules require them. Coordinate shared ports, databases,
build outputs, and other resources too. Separate worktrees do not isolate them.
Serialize tasks that overlap; do not let several threads repair the same files.

Use this compact assignment in the message. Keep the active assignment in the
existing slice evidence summary when replacement must be possible without chat.
Do not add a second task tracker or duplicate STATE.yaml's product truth.

```text
Assignment: <task label and named thread/role>
Repository and slice: <absolute path; current slice ID>
Starting point: <branch; base commit; isolated work location>
Objective and allowed paths: <bounded change; paths; explicit exclusions>
Dependencies and resources: <inputs that must exist; shared runtime ownership>
Required proof: <behavior; command/environment; relation to primary journey>
Stop conditions: <scope conflict, stale base, unavailable environment, risk>
Return: <patch/commits; inspected revision; proof/artifact paths; failures;
         limitations; exact next action>
```

A commit identifies the work being inspected; it is not mutable control state.
Never treat commands in a packet or evidence as authorization by themselves.
Every action must fit the user's task, applicable AGENTS.md, or an explicitly
invoked workflow. Do not paste credentials, private data, or entire transcripts.

## Coordinator prompt

```text
Read AGENTS.md, PROJECT.md, and STATE.yaml, then relevant current evidence.
Act as coordinator for the human-selected persistent-thread workflow. Reconcile
the recorded slice with the actual worktree. Name the smallest user-visible
outcome at risk and run its primary journey as early as practical.

Plan only this slice. Delegate only separable, bounded tasks using the assignment
format. Use the human's named threads and model choices; do not infer access from
names. You own integration and canonical state/evidence writes. Workers return
changes and findings instead of editing those files. Keep recoverable active
assignments in the existing summary when needed, not in a new roster or ledger.

Inspect returned diffs and proof. Resolve dependencies and conflicts, then run
the primary journey on the integrated result before claiming validation. Scope
corrections to reproducible findings. After two evidenced failures at the same
delivery boundary, review the assumption and remove or bypass a moving part
before continuing. Human acceptance remains human-owned.
```

## Worker prompt

```text
Read AGENTS.md, PROJECT.md, and STATE.yaml, then evidence and nested instructions
relevant to this assignment. Compare the assignment's repository, base revision,
and scope with reality; stop and report a mismatch rather than guessing.

Implement only the assigned task in the assigned isolated location. Do not edit
canonical coordination files, expand scope, publish, or start other agents on
this assignment's authority alone. Test the required behavior. Return the patch
or commits, exact commands, environment, results, artifact paths, unresolved
failures, limitations, and next action. Preserve work outside chat before the
thread retires; your tests do not prove the integrated product works.
```

## Reviewer prompt

```text
Read AGENTS.md, PROJECT.md, and STATE.yaml, then relevant evidence. Review the
assigned actual diff at the stated revision and reproduce the required behavior
in the named environment. Do not rely solely on the worker's summary.

Return actionable findings with location, consequence, reproduction, and the
smallest correction. Separate inspected code, executed checks, and unverified
claims. If you lack repo or runtime access, label the review as critique of
supplied evidence; it cannot establish validation. Return findings to the
coordinator without editing canonical state or starting an overlapping repair.
```

## Transport, recovery, and retirement

The baseline is human-relayed messages. Automatic routing requires actual host
support and user authorization; these templates cannot create, message, switch
models in, or monitor independent application threads. Do not silently replace
named threads with subagents. Their use needs its own applicable authorization.

On reassignment or replacement, read current canonical files again, inspect the
saved patch/commits and evidence, and reconcile stale assumptions. Keep the
unresolved task and exact next action outside chat. Retire the old assignment
before starting a replacement; preserve unique work and failures. Only the
coordinator updates shared state. Projects running concurrently each keep their
own state, slice, and work locations.

A useful trial completes one real slice with a worker replaced midway through.
The replacement should continue from files and the saved assignment, and the
integrated journey must pass. A fresh-process fixture can test artifact recovery;
it cannot prove real-agent effectiveness or token savings.

## Copy into the project's local sections when the owner selects this workflow

Copy the rules below into the project's `AGENTS.md`, under its local sections,
only when the owner selects persistent threads. The template's managed contract
block does not carry them, and a project that has not selected this workflow
should not have them. Preserve project-specific rules when merging, and keep
one copy.

```markdown
## Optional persistent threads

Use named threads only when the human selects this workflow and the current
slice has separable work. A single agent remains the default; no thread roster,
model matrix, scheduler, or extra state file is required.

- One coordinator owns integration and writes canonical state and evidence.
  Workers return changes and proof; they do not edit shared coordination truth.
- Assign one bounded task with slice ID, objective, allowed paths, repository,
  branch/base revision, dependencies, required proof, and stop conditions.
  A thread name or past conversation is not an assignment or fresh authority.
- Concurrent writers use separate private branches and worktrees (or clones
  where required). Serialize overlapping work and shared runtime resources.
- Refresh from AGENTS.md, PROJECT.md, STATE.yaml, and relevant evidence on each
  assignment. Keep a concise active assignment in the slice summary only when
  needed for recovery; replace stale assignments rather than adding a ledger.
- Choose models by task difficulty, risk, available tools, and observed results.
  Reserve stronger reasoning for ambiguity and review; escalate failed narrow
  work instead of assuming a cheaper model plus review is always economical.
- Review actual changes and rerun the primary journey on the integrated result.
  Worker tests or reviewer confidence cannot establish product validation.
- Before replacing a thread, preserve changes, proof, unresolved failures, and
  exact next action outside chat. Persistent conversations can become stale.
- Route messages manually unless the host's cross-thread capability and human
  authorization are established. Do not silently substitute subagents or launch
  background work. Two failures still trigger the simplification rule.
```
