# ProjectState in five minutes

## 1. Generate or adopt

New project:

```bash
python3 scripts/init_template.py new --name "Your Project" --target ../your-project
```

Existing project:

```bash
python3 scripts/init_template.py adopt --name "Your Project" --target ../your-project --dry-run
python3 scripts/init_template.py adopt --name "Your Project" --target ../your-project
```

The default profile is `core`. Adoption preserves the existing product README.

## 2. Confirm the project contract

Open `PROJECT.md`. Replace the honest placeholders with:

- the primary user;
- one observable outcome;
- current scope and non-goals;
- durable product constraints.

The human owns these choices. An agent can draft them, but cannot approve them.

## 3. Define one slice

Open `STATE.yaml`. Keep one current slice. Its primary journey should be the
smallest representative path that would convince the user the slice works.

For example:

> Clean checkout → documented start command → browser opens → user completes one
> real operation → result survives restart.

If users install a package, start from that package in the intended clean
environment. Record its identity and setup in the evidence summary. A source
checkout or a preconfigured development machine can hide missing package files.

Do not begin with the broad test suite. Try this journey early enough that a bad
packaging or architecture assumption is cheap to change.

## 4. Record bounded evidence

Run the journey yourself. Update `evidence/bootstrap-001/summary.md` with the
exact command, environment, result, artifacts, and limitations. Then align the
journey status in `STATE.yaml`.

## 5. Run the outcome gate

```bash
python3 scripts/projectstate_gate.py
```

A new scaffold initially returns `OUTCOME NOT VALIDATED`. That is correct until
the real journey passes. Passing tests cannot overrule it.

A successful gate prints `RECORDED OUTCOME VALIDATED`. It checks the records;
it does not run the journey or authenticate the human's acceptance.

If the same delivery boundary fails twice, fill the simplification review in
`STATE.yaml`: reconsider the assumption, remove a moving part, and name the
smallest rerun.

Select `--profile hardened` only when a real security, compliance, or delivery
obligation justifies the overlay.

For a runnable failure-and-recovery lesson, use the [worked example](WORKED_EXAMPLE.md).
