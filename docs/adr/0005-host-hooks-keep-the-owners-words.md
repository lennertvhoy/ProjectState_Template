# ADR-0005: The host keeps the owner's words and the slice in front of every session

**Status:** proposed (awaits the owner)
**Date:** 2026-10-09
**Author:** human-directed agent

## Context

The template's evals (`evidence/handoff-eval-001/summary.md`) measured what the
ProjectState core does for a fresh session that must continue earlier work:

- Rules do not make agents write down what the owner says in chat. Across 23
  two-session chains with five different rules or prompts, one chain kept the two
  constraints that existed only in the owner's words.
- Capturing the words mechanically does. Claude Code hooks that logged every owner
  prompt and replayed the newest ones at session start kept them in 6 of 6 chains,
  with or without the core (`scripts/projectstate_owner_log.py`, v1).
- The core cost about 1.7 to 1.8 times a session without it, for the same
  outcome. Of that extra cost, 94 to 99% was bookkeeping: hand-editing
  `STATE.yaml` and the evidence summary, repeated gate runs, and reading the files
  in the read order. The contract text itself is about 1,000 tokens.

v1 had three flaws for real use. It replayed only the newest ~3,500 characters,
and the owner's real prompts (median ~45 characters, frequent pastes of 1,500 to
3,000) push a first-day constraint out of that window within days; the 6 of 6
result came from a two-entry log. It replayed pasted text (agent reports, logs,
web pages) as the owner's own words, which is wrong and a prompt-injection path.
And it existed for Claude Code only, while the owner also works through OpenCode,
mostly as an orchestrator that delegates to subagents.

## Decision

**One tool, two hosts.** `scripts/projectstate_hooks.py` (stdlib, one file,
copied into an instance) implements three hook commands that read the host's hook
JSON on stdin; `scripts/projectstate_opencode_plugin.js` drives the same commands
from OpenCode. `install --root DIR [--host claude|opencode|all] [--no-stop]`
merges the hooks into `.claude/settings.json` without removing anything, copies
the plugin to `.opencode/plugins/`, and replaces v1's hooks; `uninstall` removes
exactly what install added and keeps the log.

- `record` (owner prompt) appends the owner's typed words verbatim to the local,
  self-ignoring `.projectstate/owner-log.md`, with v1's redaction and caps. A
  pasted block becomes one line, `[pasted text, N characters, not the owner's
  words: "..."]`. OpenCode subagent sessions are never recorded: their prompts are
  written by the orchestrating agent.
- `brief` (session start, resume, compaction) prints one block of at most 6,000
  characters, built only from files and git: the durable constraints in
  `PROJECT.md` (and `.projectstate/standing.md` in a repository without the
  core); the current slice, its journey status, whether that status was recorded
  by a run (`projectstate_verify.py`) or typed by hand and how many commits came
  after, and any owner decision that is pending with the command that records it;
  the owner's logged words that read as standing instructions but are not yet in
  the files; and the owner's three most recent requests, labelled as possibly done.
- `stop` (the agent finishes a turn) asks the agent once per log entry, when the
  owner used directive words (always, never, must, from now on, ...), to copy any
  standing constraint or decision verbatim into `## Durable constraints` with
  `(owner, date)`, and to leave one-off requests and limits on a past session's
  scope out. It also runs the read-only gate and blocks once per distinct output
  when the records are invalid (exit 2). It never blocks twice in a chain.

So the owner's word reaches every later session even when no agent writes it
down, and when an agent is asked at the right moment it does write it into the
file a human reads.

**Opt-in, released and checked like the gate.** The release index gains optional
`hooks_sha256` and `opencode_plugin_sha256` (required from 6.4.0). The fleet
doctor reports each instance's hooks as `current`, `behind`, `edited`, `v1`,
`partial`, or `absent`, prints the install command for the first four, and never
treats `absent` as a problem. `install` replaces a vendored copy only when its
hash is a released one, unless `--replace-edited`.

**The contract is not changed by this ADR.** A lean managed block (briefing
instead of the read order, `projectstate_verify.py` records the journey, one gate
run) is measured as an eval candidate (`evals/resume/candidates/`), not adopted.
Adopting it is a separate owner decision, because it is a semantic release for
every instance and needs `projectstate_verify.py` vendored.

## Consequences

- Measured on the durability eval (30 realistic owner prompts between the
  constraints and the work that needs them; haiku and sonnet): see
  `evidence/handoff-eval-001/summary.md`, "Follow-up 2".
- The owner's prompts are private text on disk. The log stays local and ignores
  itself in Git; redaction of obvious secrets is best-effort, not a guarantee.
  A curious agent can read the log file (measured: several did).
- The host cannot tell who typed a prompt. Anything typed into a primary session,
  including by an agent driving a terminal, is recorded as the owner's words.
- The stop question costs one extra agent turn when it fires (about 2 to 5% of the
  owner's real prompts contain the directive words). In a non-interactive run its
  answer would replace the final message, so the reason asks the agent to repeat a
  required final line.
- OpenCode support uses `experimental.chat.system.transform` and the
  `session.idle` event of 1.18.32; a plain one-shot `opencode run` exits before
  the stop follow-up can be delivered (the TUI and `opencode serve` deliver it).
- Replaying recent requests can lead a fresh agent to redo old work; the brief
  shows only three and says they may be done.

## Alternatives Considered

- More rules in the contract: measured, did not work (1 of 23).
- Replaying the whole log: unbounded, and it replays pastes and one-off requests.
- Writing constraints to `PROJECT.md` automatically from a keyword filter: the
  owner owns that file, and a filter cannot tell a standing rule from a one-off
  ("only do X this session"); the agent decides once, quoting the owner.
- A global install in the user's host configuration: one command for every
  project, but invisible to the repository, untracked by the release channel, and
  outside the owner's per-project choice. Not chosen; possible later.
