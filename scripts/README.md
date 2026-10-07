# Scripts

This directory holds the ProjectState Template's tooling.

All setup and usage instructions live in the repository root `README.md`. The
procedure for updating an existing project is in `docs/UPGRADING.md`. The v5
tooling, including the old automatic upgrader, lives at tag `v5-final`.

## Tools

- `init_template.py` - creates a new project (`new`) or adopts the workflow into an existing repository (`adopt`); `core` is the default profile and `hardened` the explicit opt-in
- `projectstate_gate.py` - the dependency-free outcome gate that every project vendors; it reads recorded state and evidence only, exits 0, 1 or 2, and prints its release with `--version`
- `projectstate_release.py` - release identity: `check` validates `releases/index.json` against the gate, the managed `AGENTS.md` block and the local tags; `cut --date` records a draft's hashes and marks it released; `hashes` prints the current ones
- `projectstate_fleet.py` - read-only fleet doctor: release and drift, size and the owner inbox for every repository under a root folder; it writes only `fleet.md` and `fleet.json`, outside that folder
- `projectstate_update.py` - brings one project to the current release by replacing its vendored gate and its managed `AGENTS.md` block; dry run by default
- `projectstate_decide.py` - records the owner's accept, reject or waive decision in `STATE.yaml` and the slice summary; never commits
- `projectstate_improve_check.py` - read-only guard for the opt-in measured improvement rounds; copied into a project by hand, never generated

## Usage

```bash
python3 scripts/init_template.py --help
python3 scripts/projectstate_gate.py
python3 scripts/projectstate_release.py check
python3 scripts/projectstate_fleet.py --stdout
python3 scripts/projectstate_update.py --target ../your-project
python3 scripts/projectstate_decide.py --help
python3 scripts/projectstate_improve_check.py --help
```

`projectstate_fleet.py --stdout` and the update command without `--apply` write
nothing.

## Tests and journeys

- `python3 scripts/test_outcome_core.py` runs the generated-core and packaged-product journey and the generator tests.
- `python3 -m pytest scripts/ -q` runs every test file.
- `test_release_channel.py` and `test_acceptance_loop.py` are plain scripts that take `--fleet-root DIR`. They copy real projects with `git archive` and only read the originals. The first runs the 6.3.0 release-channel journey (generated projects, the fleet doctor, and the update command on copies); the second proves the decide command on copies of projects that wait for the owner.

Add project-specific scripts only after a real project is attached to this template.
