---
status: DEFERRED
dependencies: ["034-01"]
last_verified:
arch_review: true
---

## Slice 034-07 — tier0-1-federation-aware-tweaks

**Resolution trigger:** A real distributed-peer / multi-member consumer starts *building* (see spec.md § Peer tier) — jig state scaffolded into many member repos coordinated by a central. Re-open via DEFERRED → DRAFT.

**Goal:** Extend existing Tier 0/1 skills + hooks with minimal,
federation-aware read-through behaviors that activate only when
`role != standalone`. No new skills are introduced.

**DoR:**
- Slice 034-01 is DONE.

**Acceptance Criteria:**

1. **`memory-sync` reads through to central glossary on miss.** When
   `lookup` doesn't find a term in local
   `docs/memory/glossary.md`, the helper consults the central
   repo's glossary via the host adapter. Read-only; never writes to
   central.
2. **`spec-workflow` recognizes `parent_spec:` frontmatter.**
   Transitions on a child slice don't break when `parent_spec:` is
   set; the helper preserves the field and surfaces it in
   status-board regen. Cross-repo rollup is handled in slice 034-04.
3. **`adr-workflow` is read-only aware of central ADRs in member
   mode.** `adr.py index` reads `<central>/docs/decisions/` and
   includes accepted org-wide ADRs in the index output under a
   separate `## Org-wide ADRs` heading. Members never *write* to
   central's ADRs.
4. **`independent-review` reviewer prompt includes parent context
   when present.** When a slice has `parent_spec:`, the reviewer
   prompt includes a "this is a child of org/NNN-<slug>; see
   <url>" pointer.
5. **Hook `jig-memory-scan` falls through to central glossary** in
   federation mode. Same shape as memory-sync's read-through.
6. **Hook `jig-spec-gate` enforces central conventions in federation
   mode.** Central `conventions.md` takes precedence on conflict;
   local `conventions.md` may extend but not contradict. Behavior
   gated on `role != standalone`.
7. **Federation read-through is cache-aware and fail-open by default.**
   Each tweak documents its central/authority unreachable behavior:
   stale-but-present cached context may be used with a short note;
   absent/unreachable authority context produces a warning or silent
   no-op as appropriate, but routine member-local work is never blocked
   solely because a central/authority repo cannot be reached. Only
   malformed local federation config may refuse.
8. **Standalone mode is unchanged.** All six tweaks above no-op when
   `role: standalone`; tests pin this.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions in
      single-repo behavior).
- [ ] Implementer test coverage exercises each tweak in standalone
      + member modes, including reachable authority, stale cached
      authority, and unreachable/no-cache behavior.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] `docs/architecture.md` updated to name the read-through
      precedence rules.
- [ ] CLAUDE.md hot cache updated only if a new term entered the
      glossary.

**Anti-horizontal-phasing check:** After this slice lands, an
engineer in a member repo can use any Tier 0/1 skill and see
federation awareness (glossary read-through, ADR index, conventions
precedence) without any new skill invocations.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
