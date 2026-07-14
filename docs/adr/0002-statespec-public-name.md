# ADR 0002: StateSpec public name and compatibility identifiers

Status: accepted for public terminology; physical identifiers remain compatible.

## Decision

The public name of this specification and template is **StateSpec** and
**StateSpec Template**. The engineering method is **State-Centric
Engineering**. The broader software category is **Stateware**.

`StateDD`, `StateDD_Template`, `statedd-template-v5`, `.statedd`, `statedd_*`,
schema IDs, format versions, package/import names, source locks, receipts,
release digests, URLs, and Git history remain compatibility identifiers. This
change does not silently rename or invalidate them.

Current public and operator documentation uses StateSpec. Historical evidence,
release notes, licenses, and prior decisions keep the terminology that was true
when they were created. A later physical migration requires dual-read support,
rollback, and a deprecation window.

Completion is defined as no unexplained legacy wording in current public or
operator surfaces, not a zero-result repository search.
