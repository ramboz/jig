---
status: DRAFT
dependencies: [adr-0025, 068-01]
last_verified:
arch_review: true
frame_review: true
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section. -->

## Slice 068-02 — feed-forward-and-trace-links

**Goal:** Spec drafting reads the vision `## Use cases` section as framing, each
spec records a **machine-resolvable trace link** to the use case(s) it serves,
and — because behaviors surface *while drafting specs*, not at init — this slice is
where the use-case set **grows**: drafting a spec that serves an uncaptured
behavior **prompts** an additive add to the vision (AC5). So divergence is caught
at framing time (the primary mechanism), coverage (slice 03) is a query rather than
a re-read of spec bodies, and the knowability-at-init gap (the set is only a *seed*
at init — slice 01) is closed **where behaviors actually surface** — the
*triggered* counterpart to slice 01's *seed*.

**DoR:**
- ✅ 068-01 DONE — the `## Use cases` section exists and use-case entries carry a
  stable identifier the trace link can resolve against; **slice 01's capture loop
  (any-shape → normalize → confirm) exists to be reused — seeded with the existing
  entries — for the grow pass (AC5).**
- ✅ Frontmatter machinery located: `skills/_common/parsing.py`
  (`parse_frontmatter`, `_parse_flow_list` for list-valued fields,
  `set_frontmatter_field`); the `dependencies:` field is the proven precedent
  (resolves `NNN-MM` tokens for the DONE gate).

**Acceptance Criteria:**

1. **Spec drafting reads use cases as framing.** The spec-author contract (the
   `spec-workflow` SKILL.md / spec-author guidance the orchestrator follows)
   instructs reading the vision `## Use cases` section as framing context
   *before* drafting. Observable as updated contract prose.
2. **A spec records a machine-resolvable trace link.** A new spec carries a
   `use_cases:` list field in its frontmatter (the `dependencies:`-style shape
   `parsing.py` already parses), naming the use case(s) it serves. Observable:
   `parse_frontmatter` returns the list; `workflow.py new` / the spec template
   prompts for it.
3. **The link resolves to a use-case identifier in the vision.** Use-case entries
   carry a stable id (e.g. `UC-1` / a slug), and a resolver maps a spec's
   `use_cases:` entry to that id. Observable: given a vision with `UC-3` and a
   spec citing `use_cases: [UC-3]`, the resolver links them; an unresolvable id
   is reported.
4. **The discipline is soft (advisory).** A spec with no trace link is **not
   blocked** — the coverage *gap* it creates is surfaced advisory at reconcile
   (slice 03), per ADR-0011 / the lean arc. Observable: drafting or transitioning
   a spec with an empty/absent `use_cases:` does not error.
5. **Grow-on-discovery — the knowability-at-init mitigation (advisory).** Because
   behaviors surface *while drafting specs*, not at init, this slice is where the
   use-case set **grows**. When a spec is drafted/traced to a behavior **not yet in
   the vision** — its `use_cases:` cites an id the resolver (AC3) reports
   unresolvable, or the author names a new behavior — the author is **prompted** to
   add it, **additively growing** the vision: reuse slice 01's capture loop
   **seeded with the existing entries** (+ the new one) → normalize → confirm →
   write (additive, never discard-and-replace). This is the *triggered* counterpart
   to slice 01's *seed* — it fires where behaviors actually surface. **Soft** —
   declinable, never blocks drafting (consistent with AC4 / ADR-0011). Observable:
   drafting a spec that cites an absent use case surfaces the add-prompt; declining
   leaves the vision unchanged; accepting grows it through the confirm-gated pass.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Coverage: `parse_frontmatter` round-trips `use_cases:`; the stub generator
      emits the prompt; the resolver maps a link to a use-case id and reports an
      unresolvable one; **the grow path — a spec citing an absent use case surfaces
      the add-prompt, accepting grows the vision additively (existing entries
      preserved), declining is a no-op** — with fixtures. Per `docs/conventions.md`,
      the new field updates `parsing.py` **and** the spec template/stub together.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] **Frame-critique passed** (`frame_review: true`) — gates DRAFT →
      READY_FOR_REVIEW. Per the team decision that moved grow out of slice 01, the
      thin-evidence load-bearing assumption now lives here: that **prompting growth
      at spec-draft time actually gets used and reduces init-incompleteness** — the
      knowability-at-init mitigation's *effectiveness*, not merely its reachability.
      Adversarially attacked before the grow mechanism is built.
- [ ] Implementation review passed (compliance + craft; **arch** — `arch_review:
      true`, since this adds a typed frontmatter contract + a resolution surface
      that slice 03 and future tooling read).
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred during
      implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] `CLAUDE.md` hygiene per spec 025-01 (spec still in flight — leave the entry
      until 068-03 closes it).

**Anti-horizontal-phasing check:** After this slice, an author drafting a spec is
shown the use-case framing, records which use case the spec serves, and — when the
spec serves an uncaptured behavior — is prompted to grow the vision additively.
Observable trace data **and a closed grow loop** exist end-to-end, usable by a
reader immediately (and by slice 03).

### Deviation log (after reconciliation)

_To be filled at reconciliation._
