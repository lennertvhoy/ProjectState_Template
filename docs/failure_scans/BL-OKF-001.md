# Failure Scan: BL-OKF-001 Optional OKF Knowledge Layer

**Date:** 2026-07-11
**Backlog item:** [BL-OKF-001]
**Author:** coding-agent
**Severity:** P1
**Execution mode impact:** quality_freeze

## What Happened Or Could Happen

- OKF concepts could duplicate canonical ProjectState operational facts.
- A validator could accidentally reject valid unknown OKF types, extension keys,
  broken links, or missing indexes.
- Derived knowledge could remain apparently valid after its source changes.
- An optional module could silently increase ordinary generated profile footprint
  or startup context.

## How The User Or Operator Would Notice

- Agents receive conflicting project status or stale metric definitions.
- A valid third-party OKF bundle cannot be consumed.
- Generated minimal, solo, or team repositories contain unexpected knowledge files.
- A source-linked explanation is trusted after its source hash no longer matches.

## Likely Adjacent Failures

- Duplicate YAML keys or malformed frontmatter.
- Absolute, traversal, or symlinked source paths.
- Case-colliding concept paths on case-insensitive filesystems.
- Canonical concepts without owners or reference concepts without citations.

## Previous Tests That Might Miss This

- Existing ProjectState schema tests do not inspect Markdown frontmatter or OKF reserved files.
- Existing profile tests do not exercise an explicitly selected optional asset set.
- Existing evidence checks do not determine whether a derived knowledge source is stale.

## Global Invariant Needed

- One fact has one authority; optional knowledge must never replace canonical
  operational ProjectState files.
- Validation must preserve OKF's permissive base contract while enforcing explicit
  ProjectState governance only in the namespaced extension.

## Adversarial Case

- Input/event: a bundle with duplicate frontmatter keys, a symlinked source path,
  unknown `type`, broken links, and a stale derived source hash.
- Expected protected behavior: fail only the malformed/unsafe/governance claims;
  preserve unknown-type, broken-link, and missing-index compatibility.
- Evidence required: focused validator tests and generated optional-profile checks.

## Runtime Or Live Proof Required

- Required: no
- Why: this is a template docs/scripts and generated-profile contract slice.
- Artifact: strict local evidence and GitHub Actions conformance.

## Post-Deploy Watch Required

- Required: no
- Duration or trigger: not applicable to template root.
- Artifact: not applicable.

## Closure Blockers

- Optional profile value and context-efficiency improvement are not benchmark-proven.
- Upstream OKF v0.1 remains draft and non-authoritative.
- Human acceptance remains unproven; the separate draft PR is published and both CI subjects pass, but remote closure remains intentionally blocked while the PR is draft.
