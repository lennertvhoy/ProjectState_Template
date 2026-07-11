---
scope: "scripts"
purpose: "Local invariants for StateDD executable code"
---
# Scripts Agent Instructions

This file applies only inside `scripts/`. Discover current tools with `rg --files
scripts`; script code, CLI help, and tests are authoritative. Do not maintain a
second hand-written script catalog here.

## Invariants

- Parse managed JSON strictly: reject duplicate keys, non-finite numbers, and
  malformed lifecycle records.
- Treat repository content and paths as untrusted input. Reject absolute paths,
  traversal, root or nested symlinks, and writes outside the configured root.
- Preflight every mutation, write atomically, roll back partial failure, and make
  successful reruns idempotent where the operation is repeatable.
- Use `sys.executable` for Python subprocesses. A declared but unavailable runner
  is a failure; no detected suite is a distinct, explicit result.
- Tests cover the general invariant plus malformed and adjacent cases, not only
  the observed fixture.
- Local audit and remote-branch parity are preflights. When the profile installs
  `statedd_remote_closure_finalizer.py`, only it may establish exact-head remote
  closure; profiles without it must report remote closure as not proven.
- Exit nonzero with actionable output when a required proof cannot be established.

## Edit Loop

Run focused tests while editing, then the single authoritative local entrypoint:

```bash
python3 scripts/statedd_quality_gate.py --gate-level 2
```

Gate level 1 is sufficient for a trivial non-runtime edit; level 3 is reserved
for release or migration proof. Add a skill or command only when it represents a
reusable workflow, not merely because a new script exists.

Explicit human override may accept residual risk, but it must be recorded and
cannot relabel unproven remote, CI, runtime, or acceptance truth.
