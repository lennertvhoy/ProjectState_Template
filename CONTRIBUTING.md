# Contributing

Thanks for considering a contribution to ProjectState Template. This repository
is the template itself, not a product built with it. It contains the outcome-first
core, the outcome gate, and the release channel that ships both to instances.

## What this project is for

ProjectState keeps a person and a coding agent able to resume a project and
deliver one observable slice from a small, truthful coordination surface without
letting governance become the work. See [`PROJECT.md`](PROJECT.md) for the full
outcome and scope.

### Non-goals

Reproduced from [`PROJECT.md`](PROJECT.md):

- Acting as an application runtime dependency.
- Encoding any project's architecture in the workflow.
- Making local tests equivalent to user success, remote delivery, or owner acceptance.
- Requiring backlog, history, release, signing, or multi-agent machinery for every project.
- Schedulers, thread routers, autonomous loops, or host-specific team configuration in the template.

A change that pulls the template toward one of these is out of scope.

## Setup

The scripts are dependency-free and use only the Python standard library. Install
the test runner used by CI:

```bash
python3 -m pip install pytest==9.0.3
```

`PyYAML==6.0.3` is needed only for the fleet journeys, which read the owner's own
repositories and do not run in CI. Do not add those imports to the core.

## Checks a pull request must pass

Run these exactly as CI runs them (`.github/workflows/validate.yml`), from the
repository root:

```bash
python3 scripts/test_outcome_core.py
python3 scripts/projectstate_release.py check
python3 -m pytest scripts/ -q
python3 scripts/projectstate_gate.py
```

The gate is expected to exit `1` while the template's own current slice is not
validated; that is the honest result, not a reason to weaken a record. After the
checks, the checkout must be clean:

```bash
git status
```

CI also runs `git diff --check` and fails on any untracked or modified file.

## The managed contract and the gate

The managed contract block in `AGENTS.md` (source `core/AGENTS.managed.md`) and
`scripts/projectstate_gate.py` change only through a recorded release: a draft
entry in `releases/index.json`, hashes recorded by `cut`, and a tag. Do not edit
the managed block inside an instance or hand-edit a released entry. If your
change touches the contract or the gate, open an issue describing the change and
its rationale first so the release can be planned and recorded.

## License

By contributing, you agree that your contributions are licensed under the
repository [license](LICENSE), including its condition that reserves teaching,
training, courses, workshops, tutorials, curricula, and coaching rights to the
copyright holder. See [`LICENSE_FAQ.md`](LICENSE_FAQ.md) for the plain-language
version.

## Pull requests

Use the [pull request template](.github/pull_request_template.md). It asks for the
primary journey result, any owner decision needed, and the boundaries the change
does not prove.
