# ADR-0001: Use OKF as an Optional Interoperable Knowledge Layer

**Status:** accepted
**Date:** 2026-07-11
**Author:** CTO / coding-agent

## Context

ProjectState needs durable, readable domain knowledge without duplicating or weakening
its canonical operational state. OKF v0.1 is an emerging draft format for
portable Markdown knowledge bundles. Its upstream reference specification is
pinned to commit `ee67a5ca27044ebe7c38385f5b6cffc2305a9c1a` in
`GoogleCloudPlatform/knowledge-catalog`.

## Decision

ProjectState will treat OKF as an optional contained knowledge layer, normally under
`knowledge/`. ProjectState remains authoritative for project status, architecture
governance, active work, backlog, evidence, delivery boundaries, and acceptance.

The optional `knowledge_okf` module owns only generic scaffolding, validation,
the ProjectState extension contract, provenance, and staleness checks. Real project
concepts remain project-owned. StateIR and StatePack are future generated layers
and do not replace readable canonical ProjectState files.

## Consequences

- Ordinary `minimal`, `solo`, and `team` profiles do not gain knowledge files or
  startup context unless the module is explicitly selected.
- OKF base conformance stays permissive for unknown types, unknown extension
  keys, broken links, and missing indexes.
- ProjectState governance can be strict for canonical, derived, and reference concepts
  without forking OKF.
- Source hashes make derived knowledge visibly stale instead of silently trusted.

## Alternatives Considered

- Declaring the whole repository an OKF bundle: rejected because operational state,
  instructions, evidence, and prompts have different authorities and semantics.
- Replacing ProjectState with OKF: rejected because OKF does not govern workflow truth,
  ownership, acceptance, or delivery closure.
- Making OKF mandatory in all profiles: rejected until context size and correctness
  value are measured.

## Related

- Backlog item: [BL-OKF-001]
- Upstream specification: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/ee67a5ca27044ebe7c38385f5b6cffc2305a9c1a/okf
