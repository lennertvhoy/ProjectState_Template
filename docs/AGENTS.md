---
scope: docs
purpose: Optional reference and migration documentation
---

# Docs agent instructions

`PROJECT.md`, `STATE.yaml`, and the current slice evidence summary are the
only current product/workflow truth. Documents here are references, historical
evidence, or compatibility material.

## Rules

- Read only the document relevant to the task.
- Keep current outcome and slice state out of reference docs.
- Add an ADR only for a durable architectural decision that future maintainers
  would otherwise have to rediscover.
- Add a failure scan only when a risky change benefits from an adversarial
  pre-mortem; it is not a routine checkbox.
- Keep new evidence under `evidence/<slice-id>/summary.md` unless a selected
  hardened or legacy workflow explicitly requires more.
- Historical ledgers and incidents remain immutable evidence. Do not rewrite
  them to make current state look consistent.
- Do not duplicate exact metrics, command catalogs, or state across documents.
- A document can explain a gate but cannot turn prose into proof.

When updating migration or profile guidance, verify the initializer output rather
than copying assumptions from earlier docs.
