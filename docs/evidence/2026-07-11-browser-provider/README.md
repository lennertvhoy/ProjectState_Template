# Evidence: Concrete Playwright Provider

**Slice:** [BL-BROWSER-002] Concrete Playwright provider integration  
**Date:** 2026-07-11  
**Agent:** codex-browser  
**Branch:** bl-bl-browser-002-code-g3trh  
**HEAD:** recorded in `manifest.json`

## Claims

- Claim: The template includes a stdlib-only adapter that invokes the installed Playwright CLI and records the resulting evidence contract.
  Evidence: `scripts/projectstate_playwright_capture.py`, `scripts/test_playwright_capture.py`
  Evidence type: implementation | test

- Claim: Playwright captured a real page screenshot and HAR through the adapter.
  Evidence: `playwright/page.png`, `playwright/network.har`, `playwright/capture_command.txt`
  Evidence type: product_behavior | test

- Claim: The generated browser evidence passes the strict provider-agnostic validator and evidence-pack checks.
  Evidence: `browser_verification.json`, `manifest.json`, command output from the verification log
  Evidence type: test | state_update

## Failure Scan

- Required: yes
- Path: `docs/failure_scans/BL-BROWSER-002.md`
- Adjacent failures checked: missing CLI, non-HTTP URLs, artifact path escape, missing runtime identity, partial capture, and false success after a non-zero provider exit.
- Known bad events covered: provider command succeeds without producing required screenshot/HAR artifacts.

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | A provider run is successful only when Playwright exits zero and both declared artifacts exist; the canonical browser schema is then validated strictly. |
| Is the fix contract-based? | Yes. The adapter emits the existing `projectstate.browser_verification.v1` contract and uses the existing evidence manifest. |
| Which behavior is centralized? | Playwright command construction, artifact containment, runtime identity linking, hashing, and strict validation are centralized in one adapter. |
| What brittle pattern was avoided? | No browser-specific selectors, prompt strings, sleeps, fallback success, or hard-coded downstream application routes were added. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| adapter tests | `python3 scripts/test_playwright_capture.py` | pass |
| real provider smoke | `python3 scripts/projectstate_playwright_capture.py --url https://example.com ...` | pass |
| browser contract | `python3 scripts/projectstate_browser_verify.py check ... --strict` | pass |
| evidence manifest | `python3 scripts/projectstate_evidence_pack.py check ... --strict` | pass |

## Runtime Identity

- Runtime required: no; this template root has no application runtime.
- Artifact: `runtime_identity.json`
- Endpoint: `https://example.com/` used only as a provider smoke target.
- Known limit: This evidence proves provider execution, not a downstream product runtime.

## Browser Verification

- Browser verification required: yes for this provider-integration slice.
- Browser verification artifact: `browser_verification.json`
- Provider used: Playwright CLI (`playwright screenshot`)
- Fallbacks considered: Kimi WebBridge, agent-native browser, manual browser.
- Known limits: The CLI capture records screenshot and HAR; browser console messages are not captured by this command.

## Closure State

- Implemented: yes
- Validated: yes locally
- Global quality gates: pending after state/docs propagation
- Closure-grade: not yet — requires pushed PR, GitHub-visible CI, and remote closure agreement
- Accepted: pending

## Human Override

- Human override used: no

## Risks / What Remains Partial

- The smoke target is `example.com`, not a downstream application runtime.
- Screenshot content was captured and visually inspected locally; downstream users must review their own screenshots and runtime identity before closure.
