---
status: DONE
dependencies: [083-01]
last_verified: 2026-06-25
---

## Slice 083-02 — Scaffold seeds the empty template (OQ3)

**Goal:** `jig:scaffold-init` seeds `docs/decisions/lightweight-decisions.md`
on greenfield scaffold, so the convention is discoverable from day one and a
first-write is never broken. Resolves OQ3 (yes, scaffold seeds it).

**DoR:**
- ✅ OQ3 resolved (maintainer decision, 2026-06-25): scaffold seeds it.
- ✅ Scaffold copies `templates/docs/**/*.md.template` recursively
  (`scaffold.py` ~line 2243) — a new template file drops in with no wiring
  change beyond the file itself and its test-coverage entry.
- ✅ `test_scaffold.py` carries an exhaustive expected-scaffolded-files list.

**Acceptance Criteria:**

1. **Template exists.** `templates/docs/decisions/lightweight-decisions.md.template`
   exists with the `Status: Draft (wizard-generated)` marker, the routing
   heuristic, the field template, and a "no entries yet" placeholder.
2. **No unrendered placeholders.** The template carries no `{{KEY}}` tokens that
   aren't in the scaffold substitution dict (it uses none), so
   `copy_template`'s `UnrenderedPlaceholderError` guard never trips.
3. **Scaffolded greenfield emits it.** A greenfield scaffold produces
   `docs/decisions/lightweight-decisions.md`; `test_scaffold.py` asserts its
   presence.

---

### Deviation log

_No deviations from acceptance criteria. The template intentionally carries no
`{{PROJECT_NAME}}` substitution (unlike the decisions README template) — the
content is project-agnostic, and avoiding placeholders sidesteps any
`UnrenderedPlaceholderError` coupling to the subs dict._

**Accepted craft nits (non-blocking):** the trigger-example enumeration differs
in surface wording between the README/SKILL family ("UI strings, visual choices,
translation corrections, scoped brand/icon calls") and the live-file/template
family ("brand/icon swaps, cosmetic CSS polish, UI string or translation
choices, scoped visual decisions") — same intent, left as-is to avoid a
host-package rebuild for cosmetic drift. The template's `> Status: Draft
(wizard-generated)` marker is intentionally present (matches the README
template); the live dogfood file drops it (no longer a wizard placeholder).

### Reconciliation sweep

| Surface | Status | Notes |
|---|---|---|
| `templates/docs/decisions/lightweight-decisions.md.template` | updated | created (scaffold seed) |
| `skills/scaffold-init/test_scaffold.py` | updated | added file to expected-scaffolded-files list |
| `hosts/` (claude + codex) | updated | committed host packages regenerated (`build_host_packages.py`) — the new template ships in the release zip; both copies byte-identical to source, drift `--check` green |
| `skills/scaffold-init/scaffold.py` | no-op | recursive rglob already copies it; no wiring change |
| `docs/architecture.md` | no-op | no module boundary changed |
| `CLAUDE.md` primer | no-op | no load-bearing cross-ref at this scale |
