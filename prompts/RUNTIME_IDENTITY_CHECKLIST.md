# Runtime Identity Checklist

Use this before accepting user-facing work, and before investigating a visual
regression or “this was different earlier” report.

Do not start from screenshots alone. Prove runtime identity first.

Required runtime identity proof:

1. repo path or source tree path serving the app
2. branch
3. HEAD commit
4. process or container serving the app
5. port, base URL, or endpoint under test
6. whether the artifact was rebuilt or restarted in this slice
7. whether duplicate dev servers, stale containers, or stale build artifacts were checked

Minimum investigation sequence:

1. identify which process owns the relevant port
2. prove which working directory, image, or container that process came from
3. prove which commit that runtime corresponds to
4. verify whether the current artifact was rebuilt in this slice
5. only then compare the running behavior against git history, screenshots, and evidence

Wording discipline:

- use `not found` when a search failed
- use `not currently locatable` when prior existence is plausible but not proven in the current search scope
- use `not proven` when evidence is still incomplete
- do not upgrade a negative search result into `never existed`
