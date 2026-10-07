# Evidence: resume-eval-001

## Scope and authorization

Plan item S7: give the template a measure of its own outcome. Does the
ProjectState core help a fresh agent session, with no chat history, resume a
project correctly? Owner-approved CTO plan (owner words "i choose all ur recs",
2026-10-06). The harness was built by Sonnet worker W7. The real run used the
owner's Claude usage under a 5-dollar cap.

## Primary journey

- Environment: local Linux workstation; Claude Code 2.1.291 headless, model sonnet, isolated settings; scenarios built under /tmp outside every repository
- Command: `python3 evals/resume/run.py --model sonnet --repeats 1 --max-turns 15 --out ~/.local/state/projectstate/evals/resume-20261007T083444Z`
- Result: passed
- Exit code: 0

All 10 planned runs completed (5 scenarios × with/without the core, 1 repeat),
and each was graded by trusted code. The grader reruns the journey and checks
scenario facts, so the agents' claims are not taken on trust.

| Condition | Success | Honest | Tokens | Cost | Seconds |
| --- | --- | --- | --- | --- | --- |
| with core | 5/5 | 5/5 | 753,349 | $0.463 | 106 |
| without core | 5/5 | 5/5 | 482,080 | $0.272 | 76 |

Per-scenario numbers are in `results.md` and `results.json`.

## Findings

- **No outcome difference** on these scenarios: Sonnet resumed all five correctly
  with or without the core.
- **The core cost about 1.6 times the tokens and 1.7 times the money.** With
  the core, agents read the records, ran the gate, and updated STATE and
  evidence; that coordination work is what costs more.
- **Behavior differed.** With the core, agents never claimed done before the
  journey passed. Without it, they claimed done in 4 of 5 runs. Those claims
  were true here, because each agent had fixed and verified the problem.
- **The eval does not discriminate yet.** The product is tiny, the facts sit
  in recent commit messages, and the host injects those messages. Harder
  scenarios are needed: long histories, misleading tests, multi-session
  handoffs, and repositories where the next action is not obvious from code.
- This agrees with the research record cited in the review (arXiv 2602.11988):
  context files raise cost, and their benefit has to be shown, not assumed.

## Secondary checks

- `python3 evals/resume/test_eval.py`: 50 tests OK (111 subtests). No model
  calls are made.
- `--dry-run reference`: success and honest in 10/10 runs. `--dry-run lying`:
  honest in 0/10, which shows the grader catches false claims.
- An earlier attempt (`resume-20261007T065529Z`) stopped on usage-limit errors
  after 9 runs; 2 of those runs were invalid. It is kept outside the
  repository and superseded by this complete run.
- Total model spend for the eval work was about $1.40 across all attempts.

## Artifacts

- `evals/resume/`: scenarios, product, runner, grader and tests.
- `results.md`, `results.json` (copied from the run's output directory).
- Per-run transcripts stay in the output directory, outside the repository.

## Limitations

- One repeat per cell, so the numbers are noisy.
- Only one host (Claude Code with Sonnet) ran; OpenCode and Codex were not run.
- The scenarios are too easy to separate the conditions.
- Runs used isolated settings (`--setting-sources project,local`, strict MCP),
  so the owner's global instructions were excluded on purpose.

## Owner decision

- Decision: waived
- Date: 2026-10-07
- Owner words: "youve got enough usage to implement each change yourself, do that but do it with cheaper sonnet subagents"
- Context: Roadmap item S7. The cost finding is reported to the owner for a decision on next steps; final acceptance of the roadmap is requested at the end.
