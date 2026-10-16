# Evidence: handoff-eval-001

## Scope and authorization

Follow-up to resume-eval-001, whose scenarios were too easy to separate the
conditions. The owner asked whether the template is useful (2026-10-07) and then
said "proceed" on the recommendation to build a harder eval before adding
anything. This slice measures one thing: whether a session that follows the core
leaves a better handoff than one that does not. It tests two real sessions.
Session 1 works under three owner constraints given only in its prompt, then
stops. Session 2 is a fresh session with only the repository. Two of the
constraints (semicolon CSV with a UTF-8 BOM, and refuse to overwrite without
`--force`) exist nowhere in the repository unless session 1 wrote them down.
Grading uses a hidden 7-check acceptance suite that runs the agent's CLI. The
grader was proven first with a reference implementation (7/7), the skeleton
(0/7) and six single-fault mutations (each failed exactly its own check).

## Primary journey

- Environment: local Linux workstation; Claude Code 2.1.291 headless, model haiku, isolated settings; repositories built under /tmp outside every repository
- Command: `python3 evals/resume/handoff.py --model haiku --repeats 3 --variants plain --budget-usd 3 --out ~/.local/state/projectstate/evals/handoff-haiku-plain-20261007T145814Z`
- Result: passed
- Exit code: 0

The harness ran 6 two-session chains (3 with the core, 3 without), graded all of
them, and no chain was lost to infrastructure. "Passed" means the measurement
completed; the findings below are mostly negative for the core.

## Findings

All runs used haiku, 3 repeats per cell, one task and one host.

| Cell | Chains | Reached 5/7 | Chat-only constraints kept | Honest | Cost per chain |
| --- | --- | --- | --- | --- | --- |
| Core, plain prompt | 3 | 2 | 0/3 | 1/3 (2 ended with a question, no RESULT line) | $0.33 |
| No core, plain prompt | 3 | 3 | 0/3 | 3/3 | $0.16 |
| No core, prompt asks for a handoff | 3 | 3 | 0/3 | 3/3 | $0.19 |
| Core plus one candidate rule (run 2) | 2 usable | 0 | 0/2 | 1/1 with a result | $0.33 |

1. **No condition preserved the chat-only constraints.** None of the 11 usable
   chains kept both (0/11). Asking explicitly for a handoff did not change it:
   in one of those three chains the constraints were written as comments in
   `ledger.py`, and session 2 still missed them.
2. **The core cost about twice as much per chain** and gave no gain on the
   measured outcome. In these runs it also did not make agents record the
   constraints.
3. **Records written by a weak model can be wrong, and the next session trusts
   them.** In 3 of the 5 core chains the gate exited 0 while the repository's
   visible journey was failing, or had been edited by session 2 to fit the
   work done:
   - In all three, session 1 had recorded the primary journey as passed (and,
     in two, set `next_action` to await the owner), although `journey.py` still
     failed on the unbuilt export and import.
   - In two of those chains session 2 then stopped to ask the owner for a
     decision, as the core prescribes, and made no progress.
   - In the third, session 2 edited `journey.py` to pass (`journey_tampered`).
   - The gate reads records and cannot see this. In the no-core chains,
     session 2 ran `journey.py`, saw what was missing, and finished the README
     work every time (6 of 6).
4. **Neither condition could know the hidden constraints**, so every chain that
   claimed "done" while failing them is wrong but not dishonest. All 3 no-core
   plain chains and 3 of 3 handoff-prompt chains did so.

## Candidate rule (inconclusive)

Run 2 added one line to the core's local rules: write owner-stated constraints
into the slice summary under `## Constraints from the owner`. One of the two
usable chains recorded the semicolon and BOM constraints (in the summary), but
neither chain finished the work, because both stopped at the owner-decision
step. A third chain was lost to a usage-limit error and excluded. The result
says nothing about the rule. It is not added to the template.

## Secondary checks

- `evals/resume/test_handoff.py`: 17 tests pass (6 subtests). The grader tests
  prove the reference passes 7/7, the skeleton passes 0/7, and each of six
  mutations fails exactly its intended checks.
- A smoke chain found session 1 building everything; the prompt now forbids
  that, and an overreaching chain is excluded from the measure (none occurred
  in the runs above).
- Spend: about $2.9 of notional usage across the smoke chain and all runs.
  Chains cut off by the plan's session limit are listed in the run files and
  excluded from the tables.

## Artifacts

- `evals/resume/handoff.py` and `evals/resume/test_handoff.py`.
- `run1-plain`, `run2-with-rule` and `run3-handoff-prompt` (`.md` and `.json`)
  in this directory. Transcripts and diffs stay in
  `~/.local/state/projectstate/evals/handoff-haiku-*`.

## Limitations

- One model (haiku), 3 repeats per cell, one task and one host. A stronger model
  or a different task could behave differently, and the n is small.
- The design confounds the core's owner-decision step with completion. In a real
  project the owner would record a decision between sessions, and the next work
  would start as a new slice. This harness does neither, so the core's stops are
  counted against it. The next version should add an owner-accept step.
- Session 1's slice covers all five README requirements, while its prompt scopes
  it to three. That mismatch made false "validated" records easier to produce.
- Constraints belong in `PROJECT.md` (durable constraints), which the core makes
  owner-owned. The candidate rule used the slice summary, which a later slice's
  read order does not include. A better rule has not been tested.

## Corrections (2026-10-09)

Later runs showed three statements above to be wrong or unfair. The text above is
kept as written; these corrections take precedence.

1. **Constraints kept.** The grader's `csv_semicolon_bom` check also failed
   implementations that honored the constraint but did not quote a note holding
   `;`. It is now two checks (`csv_format` for the constraint, `csv_quoting` for
   quality), and every earlier run was graded again from its saved diff. Across the
   23 chains of the first five experiments, exactly one kept the memory-only
   constraints: the no-core chain that was asked for a handoff and wrote them as
   code comments. So "0 of 11" should read "1 of 23".
2. **False records.** The "gate green while the journey failed" finding (3 of 5
   core chains) came from a slice scoped wider than the session: the slice covered
   all five requirements while session 1 was told to build three. With a coherent
   slice (journey `--through 3`) there were 0 false records in 9 core chains.
3. **Stalls.** Core chains stopped at the owner-decision step because the harness
   had no owner. With the harness recording an accept between sessions through the
   real decide command, every core chain moved on and reached the same 5 of 7 as
   the no-core chains.

## Follow-up: capturing the owner's words mechanically (2026-10-09)

Five attempts to make agents write the constraints down all failed (a rule in the
local rules, a rule aimed at `PROJECT.md`, a rule aimed at `next_action`, the core
alone, and a prompt asking for a handoff: 1 of 23 in total). The cause is agent
behavior, not file layout, so the owner's words are now captured by the host.
`scripts/projectstate_owner_log.py` is a pair of Claude Code hooks: one records
each owner prompt verbatim to a local log, the other puts the recent entries into
context at session start, resume and compaction.

All haiku, same task, scoped slice, harness acting as owner between sessions:

| Cell | Chains | Kept both memory-only constraints | Reached 7 of 8 | Cost per chain |
| --- | --- | --- | --- | --- |
| Core, no log | 3 | 0 | 0 (5 of 8) | $0.25 |
| No core, no log | 3 | 0 | 0 (5 of 8) | $0.15 |
| Core plus log, first header | 3 | 2 | 2 | $0.29 |
| No core plus log, first header | 3 | 2 | 2 | $0.15 |
| Core plus log, fixed header | 3 | 3 | 3 | $0.34 |
| No core plus log, fixed header | 3 | 3 | 3 | $0.19 |

- **The first header failed in one chain per cell.** It said the replayed words
  were binding, so session 2 obeyed "do not implement export yet" from session 1's
  prompt and did nothing. The header now says that constraints about how things are
  built stay in force, while a limit on what a past session should do applied to
  that session only. With it, 6 of 6 chains kept the constraints.
- **The log works without the core**, with identical results, so it is useful in
  any repository. The core added about 1.8 times the cost and no measured benefit
  on this task (the eight-check score was equal).
- All twelve hook chains failed only `csv_quoting`, an implementation-quality check
  that the owner's constraints do not cover.
- **A briefing probe** (a fresh agent briefs the owner from the saved state; three
  per cell) found the core's files made "what is done" accurate 6 of 6 times against
  2 of 3 without, and made the pending owner decision visible 6 of 6 against 2 of 3.
  They hurt on "what is next" (4 of 6 against 3 of 3), because session 1's
  `next_action` pointed at the owner decision. Small numbers; no constraint was
  surfaced by any briefing.
- `scripts/projectstate_verify.py` (the journey result recorded from a run, not
  typed) was built and tested but is not shipped: with a coherent slice no chain
  made a false record, so there was nothing for it to fix.

Limits: one cheap model, one task, three repeats per cell, one host (Claude Code).
Hooks exist for other hosts under other names and were not tested. The log is
plain text: it holds whatever the owner types, so it is local and gitignored, with
best-effort redaction of obvious secrets. A stronger model might follow the rules
that haiku ignored, and was not tested.

## Follow-up 2 (2026-10-09/10): host hooks v2

The durability eval showed v1's injection window (newest ~3500 characters) loses a constraint stated on
day one once a realistic week of owner prompts has passed. Four lanes built and measured v2:

- `scripts/projectstate_hooks.py` (v2, then v2.1): `record` replaces each pasted block with one
  summary line (pastes are usually not the owner's words), `brief` puts a capped 6000-character block in
  front of every session (the standing words already in the files, the current slice with whether the
  journey result was recorded by a run or typed, and the owner's earlier words), and `stop` asks once,
  at the end of a session, for standing words to be filed into `PROJECT.md` (or `standing.md`).
  Install/uninstall merge into host settings without removing anything and refuse to overwrite an
  edited copy unless `--replace-edited` is given.
- `scripts/projectstate_opencode_plugin.js`: the same three hooks for OpenCode, including a re-brief
  after compaction and at most one follow-up message per stop block.
- Release and fleet support: the hook tool and plugin are released assets with recorded sha256 hashes;
  the fleet doctor reports per-instance `hooks` and `opencode` status.
- `evals/resume/durability.py`: the harness for the table below. Two sessions, plus a fixed week of 30
  later owner prompts (terse, with two long pastes) replayed through the hooks between them. "At S2
  start" is whether the injected context still shows each constraint (matched on owner text only);
  "filed" is whether the constraints reached `PROJECT.md`'s durable constraints.

All chains: haiku or sonnet, 3 repeats, same task, the harness acting as owner between sessions.

| model | condition | version | chains | mean checks /8 | memory-only kept | at S2 start | filed in repo | scope filed | honest | done but wrong | $/chain |
|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | none | - | 3 | 6.00 | 0/3 | n/a | 0/3 | 0/3 | 3/3 | 3/3 | $0.022 |
| haiku | core | - | 3 | 6.00 | 0/3 | n/a | 0/3 | 0/3 | 3/3 | 3/3 | $0.039 |
| haiku | core-log1 (v1) | - | 3 | 6.33 | 1/3 | 0/3 | 0/3 | 0/3 | 3/3 | 3/3 | $0.043 |
| haiku | nocore-log1 (v1) | - | 3 | 8.00 | 3/3 | 0/3 | 0/3 | 0/3 | 3/3 | 0/3 | $0.027 |
| haiku | core-host-nostop | v2.0 | 3 | 8.00 | 3/3 | 3/3 | 0/3 | 0/3 | 3/3 | 0/3 | $0.043 |
| haiku | core-host | v2.0 | 3 | 8.00 | 3/3 | 3/3 | 3/3 | 0/3 | 3/3 | 0/3 | $0.047 |
| haiku | nocore-host | v2.0 | 3 | 8.00 | 3/3 | 3/3 | 3/3 | 0/3 | 3/3 | 0/3 | $0.033 |
| haiku | lean-host | wording 1 | 3 | 6.33 | 2/3 | 3/3 | 3/3 | 0/3 | 2/3 | 0/3 | $0.041 |
| haiku | lean-host | wording 2 | 2 | 8.00 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 0/2 | $0.047 |
| sonnet | none | - | 3 | 6.00 | 0/3 | n/a | 0/3 | 0/3 | 3/3 | 3/3 | $0.159 |
| sonnet | core | - | 3 | 6.33 | 0/3 | n/a | 0/3 | 0/3 | 3/3 | 0/3 | $0.382 |
| sonnet | core-host | v2.0 | 3 | 8.00 | 3/3 | 3/3 | 3/3 | 0/3 | 3/3 | 0/3 | $0.490 |
| sonnet | core-host | v2.1 | 3 | 7.33 | 3/3 | 3/3 | 3/3 | 0/3 | 3/3 | 1/3 | $0.471 |
| sonnet | nocore-host | v2.0 | 3 | 8.00 | 3/3 | 3/3 | 3/3 | 0/3 | 3/3 | 0/3 | $0.272 |
| sonnet | lean-host | wording 1 | 3 | 8.00 | 3/3 | 3/3 | 3/3 | 0/3 | 3/3 | 0/3 | $0.367 |
| sonnet | lean-host | wording 2 | 2 | 8.00 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 0/2 | $0.420 |

Excluded from the table: two lean wording-2 chains (one haiku, one sonnet) lost to API 429 errors; the
incomplete v2.1 haiku run (3 of 6 chains finished, no results.json — not measured); "done but wrong"
means the session claimed done while a hidden check failed.

Findings:

1. **The hooks keep the owner's words.** The two constraints that exist nowhere in the repository
   unless session 1 writes them down (semicolon CSV with a UTF-8 BOM, refuse to overwrite without
   `--force`) were kept in every host condition, both models (3/3; 2/3 in the one defective lean
   wording-1 cell) — against 0/3 without hooks (plain core, plain none), the same result as every
   prompt-only attempt before. v1's one 8/8 cell (nocore-log1) is not a counter-example to v1's
   measured window failure: in all three of those chains session 2 found and read the raw log file
   itself (`cat .projectstate/*`), while the injected context no longer showed the constraints (0/3).
2. **The stop question files the constraints.** With the stop hook, session 1 filed all three owner
   constraints into `PROJECT.md` verbatim and quoted, 3/3 in both models; without it (`--no-stop`),
   0/3 — the constraints still reached session 2 through the brief. The scope limit ("do not implement
   export or import yet") was never filed as standing (0/3 everywhere): the header's sentence that a
   past session's scope limit applies to that session only held in all 46 graded chains.
3. **Cost.** On sonnet, the hooks without the core cost 1.7x the plain repository ($0.272 vs $0.159 per
   chain); the core alone costs 2.4x ($0.382). The earlier cost attribution stands: 94-99% of the
   core's overhead is coordination bookkeeping (record edits, gate runs, the read order), not product
   work. The hooks add the briefing injection and the filing edits on top.
4. **The lean contract's first wording had a defect.** It said never to type a journey status by hand,
   and 5 of 6 lean chains left the slice `implementing` after `projectstate_verify.py` had recorded a
   passing journey, so the harness's owner accept was refused (sonnet 0/3 accepted: "accept needs
   current_slice.status validated or ready_for_human, not 'implementing'"). Wording 2 adds that the
   agent still sets by hand what the tool cannot decide: the slice `status` (`validated` once the
   journey passed). After the fix the owner accept went through 2/2 on both models.
5. **Briefing probe, round 2** (a fresh haiku agent briefs the owner from the saved pre-session-2
   state): with the hooks, constraints surfaced more often (core-host 1.0 of 3, lean-host 2.0 of 3,
   against 0.33 for the core's files alone) but the briefs got less reliable: 2 of 3 core-host
   briefings had no parseable BRIEF line, and no briefing named a correct next action (0/3). The v2.1
   probe was not measured: one chain was graded in a log before the spending pause, no results files
   exist.
6. **v2.1 kept the words and cost one product check.** Stop now fires on directive words only, and the
   brief separates standing words from recent requests. Memory-only constraints stayed 3/3, but mean
   checks fell to 7.33 (v2.0: 8.00) and one of three sonnet chains is done-but-wrong: session 2
   reimplemented `list` so the note always prints on its own indented line (`12.50 food` on one line,
   `lunch` on the next), which fails the acceptance suite's order-and-content check, and claimed done
   because the visible journey does not test notes. All three v2.1 chains acted on the noise week's
   wrap-the-notes requests; in v2.0 the same three requests sat in the context under "history, not
   this session's request" and no sonnet chain acted (one of eighteen v2.0 chains with saved diffs
   wrapped at all, and still scored 8/8). The requests section itself held only the two pastes, and
   no chain redid or undid work because of it. The plausible cause is the new framing — those requests
   now sit under "THE OWNER'S STANDING WORDS NOT YET IN THE FILES" — which reads as pending work; the
   third chain avoided the defect under the same context, so the framing is a plausible cause of the
   behavior change, not a proven cause of the defect. n=3.

7. **v2.2 answers finding 6, unmeasured.** Requests that carry a one-off cue (please, pls, just, for
   now, whichever, this session, this run, again) leave the standing pool unless they also carry an
   unambiguous directive (always, never, must, from now on, every time, by default); they still show
   among the three recent requests, labelled as possibly done. The section is now titled "THE OWNER'S
   EARLIER WORDS THAT MAY SET STANDING RULES ... not a request for this session" and says not to implement
   old requests that are not in `STATE.yaml`'s `next_action`. On the eval's noise week the pool went
   from 8 of 30 prompts to 5, and all three wrap requests left it; the memory-only constraints still
   appear after 30 noise prompts (tests). Whether this stops session-2 agents acting on old requests
   needs a real durability run (about $2 of Claude usage for haiku and sonnet core-host, three each), which
   was not run.

Limits: one task; n=3 per cell (2 for lean wording 2; two more chains lost to 429s); haiku and sonnet
only; Claude Code headless only in the evals — the OpenCode plugin was verified live on OpenCode
1.18.32 but not evaluated end-to-end; the v2.1 haiku run is incomplete and unmeasured. Nothing further
was measured because the owner paused Claude spending. The stop heuristic is a word list (precision
0.90, recall 0.72 on a 51-prompt labelled set for the stop set); it can miss constraints phrased as
nouns or "do not", which the brief's standing pool still catches.

## Release 6.4.0 (2026-10-16)

Owner words, 2026-10-16: "make it finished then, use subagents" and "commit push when done". The
coordinator read these as authority to cut release 6.4.0 with the hooks as an opt-in asset, add the
community files, tidy the public repository and publish it. They are not a decision on this slice: no
acceptance is recorded and `validation.human_acceptance` stays `pending`.

- **Release.** The gate's `RELEASE` and the managed block's marker moved to 6.4.0; the index entry was
  filled by `projectstate_release.py cut --date 2026-10-16` and records the gate, contract, hooks and
  OpenCode plugin hashes. The contract hash equals 6.3.0's: the block text did not change. The instance
  action is `mechanical`. The hooks stay opt-in per instance.
- **Publication hygiene.** License holder filled in and a FAQ answer that the project is source-available,
  not OSI open source; CONTRIBUTING, SECURITY, CODE_OF_CONDUCT and issue templates; README sections "Status
  and license" and "What the evidence shows"; a 6.4.0 section in `docs/UPGRADING.md`; personal paths and the
  workstation label replaced in STATE.yaml, the evidence and one test docstring; a stray draft heading removed
  from this file.
- **Workers.** Three OpenCode workers on a free model (no Claude quota) wrote the community files, audited and
  drafted the docs, and ran CI parity from a clean clone. The coordinator corrected their output before
  merging: the community files had a stale version number, a scope list that omitted the tools that execute
  commands or store prompts, and a "no network calls" claim that ignored the eval harnesses; the README draft
  understated the core's effect on sonnet's claimed-done-but-wrong rate and did not say which hooks version
  the numbers describe.
- **Checks.** CI parity, run on `main` before the release commits (8e627a9): clean `--no-hardlinks` clone,
  `pytest==9.0.3` only and no PyYAML, `test_outcome_core.py` (41 tests), `projectstate_release.py check`,
  436 tests passed with 612 subtests, the gate, a clean tree; `init_template.py new` and `adopt`, and a hooks
  dry run, all behaved as documented.
- **Backup.** A git bundle of every ref, outside the repository, was made and verified before any remote
  change.
- **History.** Before publication the unpublished commits were rewritten with `git filter-branch`: the names of
  private projects became neutral aliases (`example-project-NN`) and personal paths became `~`, in file
  contents and commit messages. The commit hashes cited in the evidence were remapped to the rewritten
  commits. Commits already on GitHub were not touched, so no force-push is needed. The original refs are in
  the backup bundle.
- **Limits.** The hooks shipped are v2.2, which was not measured. CI uses Python 3.13; this workstation has
  only 3.14.7. Remote delivery and CI are separate claims and are recorded below once they happened.

### Remote delivery (2026-10-16)

Separate claims from the local checks above.

- `main` was first pushed as a fast-forward from 7e4cb7c, together with the tags `v5-final` and `v6.0.0` to
  `v6.4.0`. GitHub Actions passed on that push (Python 3.13, only `pytest==9.0.3` installed) and the GitHub
  release `v6.4.0` was created. A follow-up check then found a few private project names and the owner's git
  email still in the pushed history. With the owner's explicit approval ("Rewrite + force-push"), the 96 commits
  after 7e4cb7c were rewritten a second time, their author and committer email was changed to the GitHub noreply
  address, and `main` and all seven tags were force-pushed with a lease. 7e4cb7c, the earlier public tip, did not
  change, so only commits pushed that day were replaced. The hashes cited in this file are the rewritten commits
  (`v6.4.0` is 237f1d0); the CI result for the final head is on GitHub Actions for that commit.
- Private vulnerability reporting was enabled on the repository, because SECURITY.md and the code of conduct send
  reporters there. 26 stale remote branches were deleted after each tip was found in the verified backup bundle;
  `main` is the only remote branch.
- An independent review by a separate model found two blockers (the reporting channel was off, and private
  project names were in the unpublished history) and several wording and tooling defects, which were fixed before
  the first push. Its follow-up check found the remaining names and the email, which the second rewrite removed.
- Limits: GitHub keeps a read-only ref for every pull request (28 here) and those still carry the original,
  unredacted commits from before this release; only GitHub Support can remove them. Anyone who cloned between the
  first push and the second may hold the first-pass history; the repository had no forks at that time.
  The three evidence files on GitHub before this release that named private projects were already public.
