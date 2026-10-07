# Assignment W11: domain packs (not started; resume next session)

You are a worker on the ProjectState template repository (Python, standard library only). You run in your own git worktree. First run `git log -1 --oneline` and `git merge-base --is-ancestor 780a787 HEAD && echo ok`; if HEAD is not at or after 780a787 (branch feat/release-channel-6.3), run `git reset --hard 780a787` inside your worktree only. A coordinator integrates your branch and owns STATE.yaml, PROJECT.md (the template's own), evidence/ and releases/; do not edit those. Do not push, tag or merge. Commit in logical steps on your worktree branch; end each commit message with the line: Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>. Stop and report instead of guessing if something is ambiguous in a way that changes behavior, or if two attempts at the same failure do not converge.

Read first: AGENTS.md, core/AGENTS.managed.md, scripts/init_template.py (v6 only, 643 lines), scripts/test_outcome_core.py (it pins sha256 digests of the default generator output; those must stay valid), README.md, docs/README.md.

Background: the owner uses this template for every kind of project, not only software: products, a public platform, learning, career and finance records, home operations and workstation configuration, content (posts, video, music), game guides. The kernel's keys stay as they are; only wording and optional starters change.

TASK W11: domain-neutral wording and optional domain packs (plan item S9).

1. Packs. Create core/packs/<name>.md for software, learning, operations, content and personal. Each is a short local-rules starter of at most 15 lines, inserted into a generated AGENTS.md's "## Local rules" section. It holds domain safety and evidence rules, not contract text:
   - software: installed-artifact journeys; never edit generated files by hand.
   - learning: never inflate readiness; grade the actual answer; keep sources explicit.
   - operations (devops, configuration, home infrastructure): dry run before apply; no destructive or privileged command without explicit authority; record rollback.
   - content: claims need sources; the owner approves anything published.
   - personal (career, finance, life records): private data never leaves the machine; no external send or submission without the owner's explicit go; never invent facts about the person.
   Write plainly and concretely.

2. Guide: docs/packs/README.md, one page. For each pack: when to use it; what a good primary journey looks like, with real examples from the owner's instances, cited by name and command. Read these from ~/Projects/*/STATE.yaml (read only):
   - example-project-26's scan command;
   - example-project-13' `python3 scripts/check_posts.py`;
   - example-project-19's study-loop smoke test;
   - example-project-05's operating journey;
   - example-project-08's camera alert journey;
   - example-project-20's `runtime/<control script>` check/start/status;
   - a game-guide instance's `tools/session.py`.
   Also give typical risks and stop-lines, and typical owner decisions. Keep personal details out: describe the projects by type and command, not their private content.

3. Generator: add `--pack NAME` to `new` and `adopt`. It inserts the pack text into "## Local rules" after the placeholder comment, and after the hardened paragraph when present. An unknown name exits 2 and lists the available packs. Without --pack, output must stay byte-identical: the pinned digests in test_outcome_core.py keep passing unchanged. With a pack, the managed block is unchanged (same hash) and STATE.yaml, PROJECT.md and the evidence summary are unchanged.

4. Wording: in the generated PROJECT.md and evidence-summary placeholder comments, and in README.md, replace software-only wording ("product", "application") with outcome wording where it would mislead non-software projects. Keep runtime independence explicit for software. Changing the default generated text will change the pinned digests. If you change default generated text at all, update the pins in one clearly separate commit that explains why; prefer leaving default output untouched unless the wording is actually wrong for non-software projects. Do not touch core/AGENTS.managed.md.

5. Tests: for each pack, new and adopt × core and hardened produce the pack text inside Local rules, the managed block hash is unchanged, and the gate on the generated scaffold still exits 1 (honest) and never 2. An unknown pack is refused. The default output is unchanged.

6. Journey, scripts/test_domain_packs.py: in a temporary directory outside ~/Projects, generate a learning-pack instance and an operations-pack instance. Give each a tiny real primary journey that a person would recognize:
   - learning: a quiz checker that grades an answers file against a key and exits 0 only when all answers are correct;
   - operations: a config validator for a small INI service config (required keys, port range, no world-writable paths) that exits 0 only for a valid config.
   For each, fill PROJECT.md (user, outcome, scope, non-goals, constraints), set STATE.yaml to the slice with the real command, environment and status passed, and write the evidence summary with the exact Command, Environment, "Result: passed" and "Exit code: 0". Run the journey for real, then require the instance's own gate to exit 0. Also prove one failing case: a wrong answer or a bad port makes the journey exit non-zero. The script exits 0 only if everything holds.

7. Docs: README.md: one short section on packs and `--pack`. CHANGELOG.md: an "Unreleased" bullet.

Verify: `python3 scripts/test_outcome_core.py`, `python3 -m pytest scripts/ evals/ -q -p no:cacheprovider`, `python3 scripts/projectstate_release.py check`, `python3 scripts/test_domain_packs.py`.

Report (final message, under 400 words): branch and commit hashes; files changed; whether default output changed (and why, if so); test and journey results; any deviation and why.
