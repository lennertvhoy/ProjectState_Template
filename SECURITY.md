# Security Policy

## Supported versions

Security fixes apply to the latest release, the `latest` field in
[`releases/index.json`](releases/index.json). Older releases are not maintained.

## Reporting a vulnerability

Report vulnerabilities privately through GitHub private vulnerability reporting:
open the repository **Security** tab and choose **Report a vulnerability**. Do not
open a public issue for a suspected vulnerability.

Please include the affected version, the file or command involved, the impact,
and a minimal reproduction if you have one.

## Scope

The repository is a small set of local tools. In scope are the scripts under
`scripts/` that read and write files on the user's machine:

- `scripts/projectstate_gate.py` (the read-only outcome gate)
- `scripts/init_template.py`, `scripts/projectstate_update.py`,
  `scripts/projectstate_decide.py` (write into a target repository)
- `scripts/projectstate_release.py`, `scripts/projectstate_fleet.py` (release
  identity and the read-only fleet doctor)
- `scripts/projectstate_verify.py` (runs the journey command recorded in
  `STATE.yaml` through `bash -c`; running it is as trusted as typing that command)
- `scripts/projectstate_hooks.py`, `scripts/projectstate_owner_log.py`,
  `scripts/projectstate_opencode_plugin.js` (host hooks that store the owner's
  prompts in a local, gitignored log; secret redaction is best-effort, not a
  guarantee)

These tools operate on local files and Git repositories. None of them opens a
socket or issues an HTTP request. The eval harnesses under `evals/resume/` launch
the Claude Code CLI, which does talk to a service; they are development tools and
are not installed into instances. Behavior that depends on the host's Git or
Python installation is out of scope.

## Response

Reports are handled on a best-effort basis. This is a volunteer-maintained
project, maintained by a single owner, and no response time or fix deadline is
promised. A confirmed report will
be acknowledged in the repository once a fix is available, with credit unless you
ask to remain anonymous.
