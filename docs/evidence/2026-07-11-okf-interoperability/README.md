# BL-OKF-001 Evidence

**Date:** 2026-07-11
**Agent:** integration-agent
**Slice:** `BL-OKF-001`
**HEAD:** d4127b11823c3b7e27a94ac6d8119717ad522fb6 (proof tree)
**Branch:** `bl-okf-001`
**Proof head:** d4127b11823c3b7e27a94ac6d8119717ad522fb6
**Final PR head:** intentionally not embedded in tracked evidence; the mutable PR body owns the final head.

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
| Remote branch, PR, and CI | verified for final PR head; branch-head run 29164232824 and merge-candidate run 29164234097 |

## Closure State

- Implemented: yes
- Validated locally: yes
- Pushed: yes
- PR opened: yes — draft PR #9
- Branch-head CI verified: yes — run 29164232824
- PR merge-candidate CI verified: yes — run 29164234097
- Closure-grade: no
- Human accepted: no
- Runtime: not applicable for this template docs/scripts slice

## Human Override

- Human override used: yes
- rule overridden: feature work during the PR #8 quality-freeze boundary
- requested by: user
- reason accepted: proceed with BL-OKF-001 in a separate isolated branch without modifying PR #8
- remaining risk: PR #8 and PR #9 remain draft; OKF value and human acceptance are unproven
- still closure-grade: no

## Risks / What Remains Partial

- OKF v0.1 remains a draft upstream specification pinned to commit `ee67a5ca27044ebe7c38385f5b6cffc2305a9c1a`.
- Optional knowledge value, startup-context impact, and promotion to any default profile are not benchmark-proven.
- Real project concepts remain project-owned; this bundle contains only a generic scaffold.
- Human acceptance, OKF value, promotion to a default profile, and benchmark superiority remain unproven; remote closure is intentionally blocked while PR #9 remains draft.

## Anti-Brittleness Review

- Durable authorities are the declarative profile catalog, the OKF v0.1 contract,
  the StateDD extension schema, source hashes, and executable validator.
- Tests cover malformed, adjacent, stale, unsafe, permissive, and explicit-selection cases; behavior is not keyed to one observed concept or prompt string.
