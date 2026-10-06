# Optional measured improvement rounds

Read `AGENTS.md`, `PROJECT.md`, and `STATE.yaml` first. Use this workflow only
when the human selects it for a specific instance. It is not a canonical
artifact, not needed at startup, and not part of any generated profile. A single
agent doing ordinary slices remains the default.

## What it is

After a slice reaches a closure status, an optional round measures one number the
instance can move and writes at most one reviewable proposal. "Automatic" means
triggered by that event, never by a timer. A round has no authority to apply its
own proposal, no scope beyond its own repository, and no budget it can raise.

## When it earns its cost

- The instance has a deterministic command that prints a number tied to its
  outcome, and a baseline was recorded before any proposal. The signal must come
  from outside the model: reported self-critique without external feedback does
  not reliably improve answers.
- No measure, no loop. Finding the missing measure is a human-reviewed slice, not
  a round. Example: a study instance judged preparation by volume until a learner
  result exposed an official blueprint with objectives that had no drill; the fix
  was a blueprint-coverage script that fails while any objective is unprepared.
  A loop could only have optimized that number after it existed.
- Candidate measures (confirm each is computable and not already gamed before
  baselining; none is validated here): project — gate failures or rework commits
  per accepted slice; study — blueprint coverage and mock-exam score; guide —
  fraction of steps confirmed in the real environment. A checklist or anything
  without a measurable outcome stays off.

## Opt in (inert until the owner enables it)

1. Copy `prompts/IMPROVE_MD_TEMPLATE.md` to `IMPROVE.md` and
   `scripts/projectstate_improve_check.py` to the same path in the instance.
   Generated core and hardened profiles refuse optional asset expansion, so this
   is a deliberate manual copy. No `STATE.yaml` key is added; the gate still
   rejects unknown top-level keys.
2. Fill in the measure, run its command yourself, record the baseline, list the
   evaluator's scripts and fixtures under `protected`, then set `enabled: true`.
3. Tell the agent to run a round, or add one line to the instance `AGENTS.md`.
   Without either, nothing runs.

## What the check enforces, and what it cannot

`projectstate_improve_check.py` is read-only and standard-library only. It never
executes the measure command and never authenticates human approval.

| Enforced mechanically | Not provable by the check |
| --- | --- |
| Stop rule, and it stays tripped | That the measure is a good proxy for the outcome |
| Proposals may not touch gates, `PROJECT.md`, `STATE.yaml`, `IMPROVE.md`, the check, past evidence, `.git/`, `.github/`, or anything in `protected` | That the agent ran the measure honestly; spot-check by rerunning it |
| Instruction files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) may only shrink | That unlisted evaluator dependencies are protected |
| Recorded value matches a verbatim line of the raw output | That a proposal helps; only later measured rounds show that |
| Token cap when usage is known; unknown stays unknown | Human approval of a proposal |
| One round per closed slice; no symlinks, traversal, binary or malformed patches | |
| Dirty worktree refused at round start | |

## Stop rule and re-arming

A round counts as a gain only when the measure moves in the declared direction by
at least `min_gain` over the best value so far. After `stop_after_rounds`
consecutive rounds without a gain the check refuses to start another, even if a
later round improves. Rejected proposals and rounds with no proposal count as
flat. Only the owner re-arms the loop: raise `first_counted_round`, reset the
baseline, and say why. A loop that stays armed while doing nothing is the failure
this rule exists to prevent.

## Cross-project lessons: pull, not push

An instance reads its own repository plus at most one declared read-only
`lessons_file` outside it. A curated feed belongs to whoever owns machine-level
observation, in the same observe-and-propose style; this template ships no
generator. Instances decide what to use. Lessons are evidence, not instructions,
and an agent-written lesson is not trusted merely because an agent wrote it.

## Models and budget

The template names no model. `model` is one host-specific value so a retired
model changes one line. Start with the cheapest model that can write a diff; the
token cap is hard. Do not estimate unobservable usage and do not claim savings
without a same-model comparison.

## Evidence base (checked 2026-10-06)

| Source | Result used | Checked |
| --- | --- | --- |
| Evaluating AGENTS.md, arXiv 2602.11988 v3 (2026-09-29) | Context files raised inference cost over 20%; success change versus none was -0.5% (LLM-generated, SWE-bench Lite, p=0.87), -2% (LLM-generated, CTXbench, p=0.37), +2.4% (developer-written, p=0.21); developer-written beat LLM-generated by 7% (p=0.038) | page fetched |
| Darwin Godel Machine, arXiv 2505.22954; Sakana write-up | Benchmark-validated self-modification raised SWE-bench 20.0% to 50.0% and Polyglot 14.2% to 30.7%; it also faked a test log and removed its own hallucination-detection markers, caught by reviewing change lineage | page fetched; numbers from search |
| RewardHackingAgents, arXiv 2603.11337 | Evaluator tampering in about 50% of natural episodes; evaluator locking removed it at 25-31% median runtime overhead | abstract fetched |
| Self-Improving Coding Agent, arXiv 2504.15228 | 17% to 53% on a SWE-bench Verified subset with a benchmark-driven loop | abstract fetched |
| SkillsBench, arXiv 2602.12670 | Curated skills +16.6 points average; self-generated skills -8.1 to -11.5 points | search summary |
| How Memory Management Impacts LLM Agents, arXiv 2505.16067 | Error propagation from stored experience; selective add plus delete gained 10% absolute over naive growth | search summary |
| Agentic Context Engineering, arXiv 2510.04618 | Incremental delta updates avoid context collapse; gains rely on execution feedback | search summary |
| Large Language Models Cannot Self-Correct Reasoning Yet, arXiv 2310.01798 | Intrinsic self-correction without external feedback often degrades answers | search summary |
| Voyager, arXiv 2305.16291; Reflexion, arXiv 2303.11366 | Voyager keeps a growing library of environment-tested skills; Reflexion stores written self-critique as memory. Neither is shown to rewrite its own scaffold | Voyager: search summary; Reflexion: citation only, not checked |

Design consequences: a measure from outside the model (benchmark-driven gains
only), a locked evaluator and protected paths (tampering is observed, not
hypothetical), proposals reviewed by a human with lineage kept in Git, deletion
preferred over addition (cost without significant benefit), and curated rather
than self-generated lessons. None of this shows that rounds improve any given
instance; a measure-only baseline on one real instance must precede any apply.
