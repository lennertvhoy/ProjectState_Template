# A packaged product that survives a handoff

This lesson runs a small note-saving CLI through a real packaging failure and
recovery. It uses temporary directories and Python's standard library, without
network access or installation into your machine.

From the template repository, run:

```bash
python3 scripts/test_outcome_core.py OutcomeCoreTests.test_packaged_journey_survives_handoff
```

The [executable example](../scripts/test_outcome_core.py) checks this sequence:

| Step | Observation | What may be claimed |
| --- | --- | --- |
| Generate | Default core starts with unresolved contract and journey | Scaffold created |
| Define | Example user needs a packaged launcher that saves and restores a note | One observable outcome |
| Try source | Running from source saves successfully | Source check passed |
| Try distribution | A clean `notes.pyz` launcher fails because `title.txt` was omitted | Primary journey failed |
| Hand off | Save failed state, error output, and the exact packaging repair as next action | Work is resumable from disk |
| Resume | A new Python process reads the contract, state, and evidence | The saved handoff preserves the failure and next action |
| Recover | Remove the incomplete packaging filter and rebuild the same product | Small packaging correction |
| Verify | Packaged launcher saves; a second process reads the same note | Primary journey passed locally |
| Remove coordination | Hide ProjectState files; the installed product still reads the note | Product runtime is independent |

The installed product runs with Python's `-I` isolation from a separate directory
that contains only the archive before launch. Source files are moved out of the
build location before recovery runs. This catches dependencies hidden by a
prepared checkout. The test never runs commands taken from `STATE.yaml`; it
records the equivalent commands after executing fixed test operations.

The failed handoff retains `automated_tests: passed` for the source check and
`primary_journey: failed` for the packaged operation. The gate refuses validation.
After the repaired package actually saves and restores the note, the records
are updated and the gate passes. Human acceptance remains `pending` throughout.

For teaching with a person or a fresh agent, apply the same sequence to an actual
project: stop after recording the failure, resume using the four core artifacts,
perform the next action, and ask the human to try the result. Record acceptance
only after they explicitly provide it.

This automated lesson proves a packaging boundary, runtime independence, and a
handoff read by a new process. It does not measure fresh-agent reasoning, prove
Windows/WSL support, establish remote delivery, or demonstrate superiority over a
project without ProjectState. Those require separate observations.
