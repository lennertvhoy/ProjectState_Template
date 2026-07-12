# BL-OKF-001 Evidence

**Date:** 2026-07-11
**Agent:** integration-agent
**Slice:** `BL-OKF-001`
**HEAD:** d4127b11823c3b7e27a94ac6d8119717ad522fb6 (proof tree)
**Branch:** `bl-okf-001`
**Proof head:** d4127b11823c3b7e27a94ac6d8119717ad522fb6
**Final PR head:** merged into `main` as `840ebaa69b95c1ecda1c2113d53011e4e3dde77d`; post-merge metrics finalization is `886710edc9032465302f8bc6c390fe470f1fde3d`.

## Claims

Claim: OKF v0.1 is an optional contained knowledge layer and does not replace StateDD operational truth.
Evidence: `command_outputs/okf_validator.txt`, `command_outputs/optional_profile.txt`

Claim: The optional module validates OKF base structure while preserving unknown types, unknown extension fields, broken links, and missing indexes as compatible warnings.
Evidence: `command_outputs/pytest_scripts.txt`, `command_outputs/okf_validator.txt`

Claim: StateDD authority, source provenance, source hashes, and staleness checks are enforced for canonical, derived, and reference concepts.
Evidence: `command_outputs/pytest_scripts.txt`

Claim: Ordinary profiles remain unchanged unless `knowledge_okf` is explicitly selected, and the selected profile passes its declared gate within budget.
Evidence: `command_outputs/optional_profile.txt`, `command_outputs/quality_gate.txt`, `command_outputs/efficiency.txt`

## Verification Log

| Check | Result |
| --- | --- |
| `python3 -m pytest scripts/ -q` | pass |
| `python3 -m pytest schemas/examples/ -q` | pass |
| `python3 scripts/statedd_okf_validate.py knowledge --source-root . --strict` | pass |
| Explicit `minimal --asset-set knowledge_okf` conformance | pass |
| `python3 scripts/statedd_quality_gate.py --gate-level 2 --conformance --verbose` | pass |
| `python3 scripts/check_state_docs.py` | pass |
| `python3 scripts/statedd_validate_schema.py` | pass |
| Strict audit | pass |
| Remote branch, PR, and CI | merged into `main`; post-merge main validation passed in run 29184051017 |

## Closure State

- Implemented: yes
- Validated locally: yes
- Pushed: yes
- PR opened: yes — PR #9 merged
- Branch-head CI verified: yes — main run 29184051017
- PR merge-candidate CI verified: yes — run 29183819393 before merge
- Closure-grade: yes for merged mainline CI; human acceptance recorded by explicit user directive
- Human accepted: no
- Runtime: not applicable for this template docs/scripts slice

## Human Override

- Human override used: yes
- rule overridden: feature work during the PR #8 quality-freeze boundary
- requested by: user
- reason accepted: proceed with BL-OKF-001 in a separate isolated branch without modifying PR #8
- remaining risk: OKF retrieval value and benchmark superiority remain unproven; PR #6/#7 remain superseded drafts
- still closure-grade: no

## Risks / What Remains Partial

- OKF v0.1 remains a draft upstream specification pinned to commit `ee67a5ca27044ebe7c38385f5b6cffc2305a9c1a`.
- Optional knowledge value, startup-context impact, and promotion to any default profile are not benchmark-proven.
- Real project concepts remain project-owned; this bundle contains only a generic scaffold.
- The user explicitly directed merging the integrated golden path; OKF retrieval value and promotion beyond opt-in asset selection remain evidence-gated.

## Anti-Brittleness Review

- Durable authorities are the declarative profile catalog, the OKF v0.1 contract,
  the StateDD extension schema, source hashes, and executable validator.
- Tests cover malformed, adjacent, stale, unsafe, permissive, and explicit-selection cases; behavior is not keyed to one observed concept or prompt string.
