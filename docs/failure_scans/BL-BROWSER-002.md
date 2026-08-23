# Failure Scan: BL-BROWSER-002 Concrete Playwright Provider

**Slice:** BL-BROWSER-002

## Failure modes checked

- Playwright CLI is absent or configured with an invalid command.
- A non-HTTP URL is passed to the provider.
- The provider exits successfully but omits the screenshot or HAR.
- A requested artifact path escapes the evidence directory.
- A runtime evidence folder omits `runtime_identity.json`.
- Browser evidence claims success without strict schema validation.
- A provider smoke target is mistaken for application runtime proof.

## Mitigations

- Resolve `playwright` from PATH or require an explicit `PLAYWRIGHT_COMMAND`.
- Accept only absolute HTTP(S) URLs.
- Require zero exit status and existence of both generated artifacts.
- Keep all generated paths under the evidence directory.
- Require an existing runtime identity, or require an explicit non-runtime reason.
- Run `projectstate_browser_verify.py check --strict` before reporting success.
- Record the non-runtime smoke-test limitation in the runtime artifact and evidence README.

## Adjacent cases

- Fake provider command used in regression tests.
- Full-page and default viewport capture options.
- Existing downstream runtime identity versus template-root smoke mode.
- Missing provider executable and malformed URL paths.
