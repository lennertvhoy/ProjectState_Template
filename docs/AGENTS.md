---
scope: docs
purpose: Optional reference and migration documentation
---

# Docs agent instructions

`PROJECT.md`, `STATE.yaml`, and the current slice evidence summary are the
only current product/workflow truth. Documents here are references or history.

## Rules

- Read only the document relevant to the task.
- Keep current outcome and slice state out of reference docs.
- Add an ADR only for a durable architectural decision that future maintainers
  would otherwise have to rediscover.
- Keep new evidence under `evidence/<slice-id>/summary.md` unless a selected
  hardened workflow explicitly requires more.
- ADRs and the changelog are history. Do not rewrite them to make current state
  look consistent; supersede an ADR with a new one.
- Do not duplicate exact metrics, command catalogs, or state across documents.
- A document can explain a gate but cannot turn prose into proof.

When updating migration or profile guidance, verify the initializer output rather
than copying assumptions from earlier docs.
