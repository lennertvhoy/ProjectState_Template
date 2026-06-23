# Provider-Agnostic Browser Verification

StateDD requires browser-verification evidence for user-facing closure, not a specific browser automation provider.

Kimi WebBridge is a preferred provider when available, not a required dependency. The same evidence contract accepts Playwright, agent-native browser tools, existing E2E/browser tests, manual browser screenshots, or custom project tooling.

## Design rule

> Browser-verification evidence must be durable, linked to runtime identity, and honestly scoped. The provider that produced it is an implementation detail.

## Fallback chain

1. Agent-native browser tool, if the coding agent has one.
2. Kimi WebBridge, if running in Kimi and available.
3. Playwright, if already present or explicitly allowed.
4. Existing project E2E/browser tests, if they produce durable artifacts.
5. Manual browser verification with screenshots/logs and explicit limits.
6. Not applicable for docs/scripts-only slices.

## Evidence artifact

Every closure-grade evidence folder for a user-facing/runtime slice should contain:

```text
docs/evidence/<slice>/browser_verification.json
```

When the slice is docs/scripts-only, the file may still be present with `provider.kind` set to `not_applicable` semantics via an empty or `not_applicable` record, or it may be omitted. The strict audit treats missing browser verification as acceptable only when no user-facing/runtime claim is made.

## Schema

`schemas/browser_verification.schema.json` defines `statedd.browser_verification.v1`.

Top-level fields:

- `schema`: must be `statedd.browser_verification.v1`
- `captured_at`: ISO 8601 timestamp
- `provider`: the automation or manual provider used
- `runtime_identity`: link to the runtime identity artifact and match checks
- `checks`: browser claims with status and evidence
- `artifacts`: durable evidence files (screenshots, logs, traces, etc.)
- `limits`: explicit known limits

## Provider object

```json
{
  "kind": "kimi_webbridge",
  "required": false,
  "available": true,
  "selection_reason": "preferred provider available in current agent",
  "fallbacks_considered": ["playwright", "manual_browser"]
}
```

Recognized `kind` values:

- `kimi_webbridge` — preferred only when available in the current Kimi environment.
- `playwright` — acceptable if the project already has Playwright or the human permits setup.
- `agent_native_browser` — acceptable for agents with built-in browser/screenshot tooling.
- `existing_e2e` — acceptable when the project's own tests produce durable browser evidence.
- `manual_browser` — acceptable when automation is unavailable, but must include explicit known limits.
- `custom` — acceptable only with `tool`, `command`, evidence files, and limits.
- `not_applicable` — used when the slice has no user-facing/runtime behavior to verify (for example, docs/scripts-only template changes).

## Runtime identity link

```json
{
  "path": "runtime_identity.json",
  "head_matches": true,
  "endpoint_matches": true
}
```

## Checks

```json
{
  "id": "BV1",
  "route": "/settings",
  "claim": "Settings page renders after saving profile changes.",
  "status": "passed",
  "evidence": [
    "screenshots/settings-after-save.png",
    "logs/browser-console.txt"
  ],
  "known_limits": []
}
```

`status` must be one of `passed`, `failed`, `partial`, `not_run`.

## Artifacts

```json
{
  "path": "screenshots/settings-after-save.png",
  "kind": "screenshot",
  "sha256": "...",
  "redaction_status": "manual_review_completed"
}
```

`kind` must be one of `screenshot`, `browser_log`, `trace`, `video`, `test_output`, `other`.

## Manual fallback

Manual browser proof is allowed, but it must be honest:

```json
{
  "provider": {
    "kind": "manual_browser",
    "required": false,
    "available": true,
    "selection_reason": "no automation provider available; human captured browser evidence"
  },
  "limits": [
    "Manual browser verification was used because no browser automation provider was available."
  ]
}
```

## Helper script

`scripts/statedd_browser_verify.py` validates and records browser verification artifacts. It does not drive browsers itself.

```bash
python3 scripts/statedd_browser_verify.py init docs/evidence/YYYY-MM-DD-slice
python3 scripts/statedd_browser_verify.py check docs/evidence/YYYY-MM-DD-slice --strict
python3 scripts/statedd_browser_verify.py hash docs/evidence/YYYY-MM-DD-slice
python3 scripts/statedd_browser_verify.py summarize docs/evidence/YYYY-MM-DD-slice
```

## Audit behavior

For user-facing/runtime closure:

- `runtime_identity.json` is required.
- `browser_verification.json` is required.
- `provider.kind` must be recognized or `custom` with an explanation.
- Every browser claim must map to evidence artifacts.
- Artifacts must exist and be covered by the evidence manifest.
- Known limits must be explicit.

A valid closure can use any recognized provider, including `manual_browser` with explicit limits.

## Non-goals

- Do not require Kimi WebBridge.
- Do not require Playwright.
- Do not install browsers.
- Do not add browser automation dependencies.
- Do not add OCR.
- Do not weaken runtime identity, evidence pack, schema, audit, or upgrade safety rules.
