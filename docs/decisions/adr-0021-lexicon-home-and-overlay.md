---
dependencies: []
last_verified: 2026-06-07
---

# ADR-0021: Canonical lexicon home and project-glossary overlay

## Status

Accepted (2026-06-07)

## Context

[Spec 065](../specs/065-lower-vocabulary-barrier/spec.md) lowers the vocabulary
barrier for non-expert readers of jig artifacts. Its load-bearing dependency is a
**single canonical definition per jig term**, consumed by four things that must
not drift apart: the `jig-memory-scan.sh` hook (surfaces a def when a term
appears), the `/jig:explain` skill (term + artifact modes), the self-defining
generation convention (new specs link the lexicon), and the human-browsable
glossary. If each consumer carries its own wording, the whole point — *one*
authoritative definition — collapses.

That forces a structural decision the spec's three downstream slices all depend
on (065-01 declares `arch_review: true` for exactly this reason): **where does
jig's own vocabulary live, and what happens when a project wants to redefine a
term?** jig's terms (SPIDR, ADR, reconciliation, deviation log, vertical slice,
frontmatter) are *constant across every jig project* — they are jig's vocabulary,
not any one project's. But a consuming project legitimately needs to specialize a
term to its own domain. Two axes, then: a *shipped* layer (jig-constant) and a
*project* layer (per-repo), plus a precedence rule between them.

A second constraint: the hook reads the lexicon inside a `python3 -c` invocation
with no third-party dependencies, so the shipped format must be stdlib-parseable.
And per [spec 055](../specs/055-context-cost-discipline/spec.md) /
[spec 057](../specs/057-thin-orchestrator/spec.md), none of this may land in the
always-loaded hot path (`CLAUDE.md`) — it is read on demand.

## Decision Options Considered

### Option A: Shipped structured lexicon + project-**glossary** prose overlay (project wins)
jig ships `skills/_common/lexicon.json` (the constant vocabulary, structured);
the per-project overlay is parsed from the project's existing
`docs/memory/glossary.md` (`## Term` heading + first paragraph), overriding the
shipped def for that term.
- **Pros:** one human-facing project artifact — devs keep editing the glossary
  they already maintain (`memory-sync` already writes it); no new per-project
  file to keep in sync; project specialization is natural; shipped layer stays
  the single source for jig-constant terms.
- **Cons:** the overlay parse is a heuristic over prose markdown (couples the
  loader to the glossary's documented `## TERM` format); a glossary that drifts
  from that format silently contributes no overrides (mitigated: fail-soft to
  shipped-only, and the format is documented in `glossary.md.template`).

### Option B: Shipped lexicon + a structured per-project `docs/memory/lexicon.json` overlay
Same shipped layer, but the project overlay is a *second* structured file the
project authors, not the prose glossary.
- **Pros:** robust, unambiguous parse on both layers; no prose heuristic.
- **Cons:** introduces a second per-project vocabulary artifact alongside
  `glossary.md`, which then **drift against each other** — reviving the exact
  single-source-of-truth problem this spec exists to kill; worse ergonomics
  (hand-authored JSON) for the human-facing layer.

### Option C: Per-project glossary only, no shipped lexicon
Drop the shipped layer; every project's `glossary.md` is the whole story.
- **Pros:** simplest; nothing new shipped.
- **Cons:** jig's constant vocabulary gets **duplicated into every project** and
  drifts as the plugin evolves; a freshly-scaffolded project starts with no jig
  definitions at all until someone backfills them — the newcomer this spec
  targets is the least equipped to do that. Defeats "one lexicon, four
  consumers."

## Recommended Decision

**Adopt Option A: a shipped structured lexicon plus a project-glossary prose
overlay, project-wins.**

- **Shipped layer:** `skills/_common/lexicon.json` — JSON (stdlib-parseable for
  the hook), keyed by term, each entry carrying `short` / `plain` / optional
  `example` / `see_also`. Seeded from today's `glossary.md` terms, expanded into
  plain language. It travels as machinery (inside `skills/_common/`, already
  copied by `scaffold-init` / `migrate copy-machinery`) rather than as a rendered
  template — so existing projects pick it up on their next copy, no re-scaffold,
  honoring principle 7 (own the scaffolding).
- **Project layer:** parsed from the project's `docs/memory/glossary.md` in its
  **documented canonical format** — `## TERM`, followed by definition prose (the
  directive already in `glossary.md.template`). One human-facing artifact, the
  one devs already edit.
- **Precedence:** **project wins.** A term defined in both resolves to the
  project's definition; the shipped def is the fallback. Projects specialize;
  jig provides the floor — the same "bring your own depth, jig provides the floor"
  shape as the baseline skills (principle 5).
- **Failure mode:** the overlay parse is **fail-soft** — a missing or
  off-format glossary degrades to shipped-only and never raises. The parse
  targets `## Term` (H2); an H3 or otherwise-shaped heading simply contributes no
  override (no false positives).

This is the only option that keeps a *single* authoritative source per term
(shipped for jig-constant, project glossary for local overrides) while adding
**zero** new per-project artifacts and keeping the human-facing layer the
ergonomic prose doc devs already maintain.

## Consequences

**Becomes easier:**
- One definition per term, four consumers, no drift — the spec's core premise.
- A newcomer to any jig project gets jig's vocabulary immediately (shipped
  layer), with no backfill required.
- Projects specialize a term by editing the glossary they already use — no new
  file, no new format to learn.

**Becomes harder:**
- The loader is coupled to the glossary's documented `## TERM` prose shape; if
  that format ever changes, the parser changes with it (bounded: one documented
  format, fail-soft on mismatch).
- Two names now coexist deliberately — **lexicon** (shipped jig vocabulary) vs
  **glossary** (per-project overlay). The distinction must stay crisp in docs to
  avoid its own terminology drift.

## Open questions

- **None blocking.** If the prose-overlay heuristic proves too fragile in
  practice (signal: real projects whose overrides silently fail to apply), the
  fallback is Option B's structured `lexicon.json` overlay — a later, bounded
  change behind the same loader interface. Not adopted now to avoid the
  two-artifact drift it reintroduces.
