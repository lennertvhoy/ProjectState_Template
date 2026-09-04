# ProjectState adoption profiles

Use `core` unless a concrete obligation requires more. Profile choice never
changes the product outcome or makes a failed primary journey acceptable.

## `core` (default)

Installs:

- `AGENTS.md`
- `PROJECT.md`
- `STATE.yaml`
- `evidence/bootstrap-001/summary.md`
- `scripts/projectstate_gate.py`

For a new repository, the initializer also creates a product `README.md`.
Adoption preserves an existing README.

```bash
python3 scripts/init_template.py new --name "Your Project" --profile core
python3 scripts/init_template.py adopt --name "Your Project" --profile core --dry-run
```

The initial outcome gate fails until a human confirms the project definition and
the real primary journey passes. This is intentional.

## `hardened` (opt-in)

Adds `HARDENED_POLICY.md` for explicit security, compliance, and delivery
stop-lines. Choose it when real exposure or obligations justify the extra policy,
not as a generic signal that a project is important.

```bash
python3 scripts/init_template.py new --name "Your Project" --profile hardened
```

The hardened overlay cannot override the primary journey. Remote proof, signing,
threat models, or audit retention are still required only when the project or
current slice actually crosses those boundaries.

## Compatibility profiles

The v5 `minimal`, `solo`, `team`, and `regulated` profiles remain explicitly
available so existing repositories can migrate deliberately. They retain the old
multi-file state and closure tooling. They are not defaults and should not be
selected for a new project without a compatibility reason.

The legacy `--minimal` flag still maps to `--profile minimal`; it does not select
the new core. Prefer the explicit `--profile core` spelling.

## Optional assets

Optional GitHub or knowledge assets can add substantial process surface. Install
them only after checking that they advance an actual project need. The
initializer refuses automatic optional-set expansion for `core` and `hardened`;
add project-specific tooling in a separately reviewed change. Asset presence is
not proof of product behavior.

## Choosing

Use `core` when the answer to all of these is yes:

- Can one real journey establish the current slice?
- Are ordinary Git review and project tests enough secondary proof?
- Is there no current regulatory or externally audited obligation?

Use `hardened` when a named risk owner can explain the extra stop-lines and who
will maintain them. Use a v5 compatibility profile only while preserving or
migrating an existing v5 installation.
