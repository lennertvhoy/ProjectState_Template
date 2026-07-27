# ProjectState feature slice contract

A small schema-driven contract for a single ProjectState backlog slice.

This prompt is generated from `feature_slice.schema.json`. Regenerate it with `python3 schemas/examples/schema_prompt_loop/generate_prompt.py`.

## Required fields

- **slice_id**: Stable backlog identifier for this slice, e.g. BL-005.
- **title**: Short human-readable title for the slice.
- **goal**: One-paragraph goal statement describing the slice's intent.
- **repo_role**: Repo role this slice applies to.
- **projectstate_mode**: ProjectState mode this slice runs in.
- **acceptance_criteria**: List of concrete acceptance criteria.
- **evidence_required**: Whether evidence artifacts are required for acceptance.
- **verification_commands**: Commands that must pass before the slice is closure-grade.

## Optional fields

- **runtime_required**: Whether runtime identity proof is required for acceptance.
- **non_goals**: Explicit non-goals to prevent scope creep.
- **known_limits**: Known limits or caveats for this slice.

## Acceptance checklist

Before accepting a feature slice, confirm:

- [ ] `slice_id` is present and valid.
- [ ] `title` is present and valid.
- [ ] `goal` is present and valid.
- [ ] `repo_role` is present and valid.
- [ ] `projectstate_mode` is present and valid.
- [ ] `acceptance_criteria` is present and valid.
- [ ] `evidence_required` is present and valid.
- [ ] `verification_commands` is present and valid.

