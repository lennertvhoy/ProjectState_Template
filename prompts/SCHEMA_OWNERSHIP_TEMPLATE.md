# Schema Ownership Template

Use this whenever a repo exchanges structured data with an external system
(including ChatGPT-generated packets, API clients, importers, or event
consumers). The goal is to prevent schema drift and silent repair.

## Rule

**No schema may exist only in prose.**

Every packet or message schema must have a single canonical owner.

## Required Artifacts

1. **Canonical schema file**
   - TypeScript/Zod, JSON Schema, or another machine-readable schema format.
   - Located in a predictable directory such as `src/schemas/` or `schemas/`.

2. **Generated example JSON**
   - Produced from the canonical schema, not hand-written separately.
   - Path: `schemas/<name>/example.json` or similar.

3. **Generated ChatGPT / external prompt snippet**
   - A prompt fragment that tells the external system the exact shape to return.
   - Generated from the same schema the app validates.
   - Path: `schemas/<name>/prompt-snippet.md` or similar.

4. **Import validation tests**
   - Tests that run the canonical validator against valid and invalid inputs.
   - Invalid inputs must produce clear field-level errors.

5. **"Copy this exact shape" sample**
   - A minimal, runnable example the external user can paste.
   - Must match the canonical schema byte-for-byte in shape.

6. **Version field**
   - Every packet must carry `"schemaVersion": "x.y"`.
   - The app must reject packets with unsupported major versions.

7. **Migration policy**
   - Document how older schema versions are handled (reject, migrate, or deprecate).
   - Path: `schemas/<name>/MIGRATION.md` or section in the ADR.

## Anti-Patterns

- ChatGPT invents a new shape because the prompt was prose-only.
- The app silently repairs invalid packets.
- Example JSON is maintained separately from the validator.
- Two parts of the repo disagree on the canonical shape.

## Recommended Layout

```text
schemas/
  goal-update-packet/
    schema.ts          # canonical Zod / TypeScript schema
    schema.json        # generated JSON Schema
    example.json       # generated example
    prompt-snippet.md  # generated external prompt
    invalid-cases.json # examples used by validation tests
    MIGRATION.md       # version policy
src/
  __tests__/
    goal-update-packet.test.ts
```
