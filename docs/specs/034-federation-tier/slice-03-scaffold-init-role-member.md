---
status: DRAFT
dependencies: ["034-01"]
last_verified:
arch_review: true
---

## Slice 034-03 — scaffold-init-role-member

**Goal:** Extend `scaffold-init` with a `--role` flag so a fresh install
can target federation mode (`central` or `member`) and an existing
standalone install can be upgraded in place.

**DoR:**
- Slice 034-01 is DONE.
- `scaffold.json` federation fields are published.

**Acceptance Criteria:**

1. **`--role` flag accepted.**
   `scaffold-init --role=<standalone|central|member>` is honored.
   Default is `standalone` (current behavior). When `member`,
   `--central=<url>` is required; refused otherwise with a clear
   message.
2. **Tier 2 skills installed when `role != standalone`.** All five
   federation skills install (skills self-gate by role at invocation
   time; see slice 034-07 for hook gating).
3. **Re-scaffold from standalone to federation is non-destructive.**
   Running `scaffold-init --role=member --central=<url>` against an
   existing standalone install upgrades scaffold.json, installs Tier
   2 skills, and leaves all existing skills + hooks + state
   untouched. Idempotent if re-run.
4. **`AGENTS.md` / `CLAUDE.md` carry a federation pointer when
   `role != standalone`.** A single concise line ("This repo is a
   member of <central-url>; see
   `<central>/docs/product-vision.md` for org context.") so the
   primer stays lean.
5. **Member install does not duplicate central docs.** No copy of
   central `conventions.md` / `glossary.md` / org ADRs lands
   locally. Federation-aware skills fetch on demand (slice 034-07).
6. **`--dry-run` shows the planned changes** without writing
   anything.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Implementer test coverage exercises new install +
      upgrade-in-place + re-run idempotency.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] `docs/architecture.md` updated where scaffold-init contract is
      described.

**Anti-horizontal-phasing check:** After this slice lands, a dev can
`scaffold-init --role=member --central=<url>` against either a fresh
directory or an existing standalone install and end up with a
federation-aware jig install. The Tier 2 skills are present and the
scaffold.json reflects the new mode.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
