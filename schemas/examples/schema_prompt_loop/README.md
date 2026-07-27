# Schema/Prompt Loop Example

A minimal, stdlib-only demonstration of ProjectState's schema-driven contract idea:
**one schema validates data and generates prompt material**, so docs, prompts, and
examples cannot quietly drift from the canonical contract.

## Files

| File | Purpose |
| --- | --- |
| `feature_slice.schema.json` | Canonical JSON Schema for a small "feature slice" contract. |
| `valid_slice.json` | A slice that passes schema validation. |
| `invalid_slice.json` | A slice that deliberately fails schema validation. |
| `validate_example.py` | Validates both JSON files against the schema. |
| `generate_prompt.py` | Generates a deterministic prompt/checklist from the schema. |
| `generated_prompt.md` | Checked-in fixture of the generated prompt. |
| `test_schema_prompt_loop.py` | Regression tests: valid passes, invalid fails, prompt fixture stays in sync. |

## Why this matters

In many projects, the "schema", "example", and "prompt instructions" live in
separate files and drift apart. This example keeps them tied together:

1. The schema is the source of truth.
2. Examples prove the schema accepts/rejects real data.
3. The prompt is generated from the same schema, so a schema change forces the
   prompt fixture to update (the test fails if it does not).

## Run it

From the repo root:

```bash
python3 schemas/examples/schema_prompt_loop/validate_example.py
python3 schemas/examples/schema_prompt_loop/generate_prompt.py
python3 schemas/examples/schema_prompt_loop/test_schema_prompt_loop.py
```

## What it proves

- `valid_slice.json` passes `feature_slice.schema.json`.
- `invalid_slice.json` fails with an actionable error.
- `generate_prompt.py` output is deterministic.
- `generated_prompt.md` stays synchronized with the schema.
- No external dependencies are required.

## Limits

- This is a teaching example, not a replacement for `scripts/projectstate_validate_schema.py`.
- The generated prompt uses only field names and descriptions; it does not
  attempt natural-language paraphrasing.
