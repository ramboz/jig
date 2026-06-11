---
status: DONE
dependencies: [adr-0025, 068-01]
last_verified: 2026-06-10
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
4. **The discipline is soft (advisory) — never blocked, but never silent
   either.** A spec is **never blocked** for lacking a trace link: drafting or
   transitioning a spec with an empty/absent `use_cases:` **does not error** (per
   ADR-0011 / the lean arc). But *not blocked* is **not *not noticed*** — an
   empty/absent/unresolvable `use_cases:` deterministically **surfaces the soft
   framing prompt (AC5)** at draft/framing time, and any gap the author then
   declines is the advisory coverage finding slice 03 reports as the **backstop**.
   Observable: the empty-field state produces a *prompt*, never an *error*.
5. **Grow-on-discovery — the knowability-at-init mitigation, via a mechanical,
   reachable trigger (advisory).** Because behaviors surface *while drafting specs*,
   not at init, this slice is where the use-case set **grows**. **The trigger is a
   deterministic predicate over the trace field — not a voluntary self-report:**
   whenever a spec reaches draft/framing with an **empty, absent, or unresolvable
   `use_cases:`** (AC3), the author is **prompted** with three one-step paths —
   - **(a) cite an existing** use case (records the trace);
   - **(b) grow the vision** — this spec serves a behavior not yet captured: reuse
     slice 01's capture loop **seeded with the existing entries** (+ the new one) →
     normalize → confirm → write (**additive**, never discard-and-replace). Because
     the capture loop is seeded with the existing entries, the confirm step
     **actively guards grow quality**: it (i) **enforces goal-level grain** — the
     same `"[actor] can [goal]"` normalization slice 01 applies, rejecting
     spec-shaped / requirements-level phrasing (the Non-goal) — and (ii) **checks
     the proposed entry for near-duplication against the seeded existing entries**,
     routing an apparent match back to path (a)-**cite** rather than minting a
     duplicate. So a *reachable* trigger cannot silently bloat the section with the
     two low-quality shapes that would otherwise feed §A2 coarseness/false-coverage
     while reading as success.
   - **(c) decline** — legitimately untraced (infra / refactor / no user-facing
     behavior) or defer; leaves the vision unchanged, and any resulting gap is
     slice 03's advisory backstop.

   **Reachability is the whole point:** the prompt fires on the **empty-field state
   AC4 blesses as non-erroring** — the state a gap-creating author *most naturally
   produces* — so the author who **creates** the gap is reached, **not only** the
   diligent author who already typed an unresolvable id or volunteered "this is
   new." A trigger that fired only on a self-inflicted unresolvable id or a
   volunteered "this is new" would sit inert on exactly the gap cases it must catch. It fires on the **same deterministic signal slice
   03's coverage check reads project-wide**, just earlier (at framing, the primary
   mechanism). This is the *triggered* counterpart to slice 01's *seed*. **Soft** —
   every path including decline is one step, never blocks drafting (AC4 / ADR-0011);
   suppressed entirely when the use-case layer is overridden off for the project.
   Observable: a spec reaching draft/framing with empty/absent/unresolvable
   `use_cases:` surfaces the prompt; choosing (b) grows the vision additively
   (existing entries preserved) through the confirm-gated pass; choosing (a) records
   the trace; declining (c) is a no-op on the vision.

**DoD:**
- [x] All ACs pass; full test suite green (2580 tests OK, skipped=3; ruff clean — no regressions).
- [x] Coverage: `parse_frontmatter` round-trips `use_cases:`; the stub generator
      emits the prompt; the resolver maps a link to a use-case id and reports an
      unresolvable one; **the grow trigger is reachable in the gap case — a spec
      with an empty/absent `use_cases:` (the state AC4 blesses), *as well as* one
      citing an unresolvable id, trips the prompt; accepting (b) grows the vision
      additively (existing entries preserved); declining (c) is a no-op** — with
      fixtures. Per `docs/conventions.md`, the new field updates `parsing.py`
      **and** the spec template/stub together.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] **Frame-critique passed** (`frame_review: true`, 3-round iteration) — gates DRAFT →
      READY_FOR_REVIEW. Per the team decision that moved grow out of slice 01, the
      thin-evidence load-bearing assumption now lives here: that **prompting growth
      at spec-draft time actually gets used and reduces init-incompleteness** — the
      knowability-at-init mitigation's *effectiveness*, not merely its reachability.
      Adversarially attacked before the grow mechanism is built.
- [x] Implementation review passed (compliance + craft; **arch** — `arch_review:
      true`, since this adds a typed frontmatter contract + a resolution surface
      that slice 03 and future tooling read).
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred during
      implementation. *(N/A — no decisions deferred during implementation.)*

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] `CLAUDE.md` hygiene per spec 025-01 (spec still in flight — leave the entry
      until 068-03 closes it).

**Anti-horizontal-phasing check:** After this slice, an author drafting a spec is
shown the use-case framing, records which use case the spec serves, and — whenever
the trace field is left empty/absent/unresolvable — is prompted (cite / grow /
decline) to either anchor the spec or grow the vision additively. Observable trace
data **and a closed, reachably-triggered grow loop** exist end-to-end, usable by a
reader immediately (and by slice 03).

### Deviation log (after reconciliation)

1. **Frame hardened pre-implementation by a 3-round frame-critique.** The
   original DRAFT AC5 grow trigger fired only on an unresolvable id or a
   *volunteered* "this is new" — unreachable in the empty-field gap case AC4
   blesses. It was reframed to a **deterministic empty/absent/unresolvable
   predicate** (`classify_spec`), and a **grow-quality guard** (goal-level grain
   + near-duplicate→cite) plus discriminating signal (ii) were added so
   coarseness-via-grow is observable. Full narrative in
   [reviews/slice-02-frame-critique.md](reviews/slice-02-frame-critique.md). The
   implementation matches this hardened frame, not the original DRAFT.
2. **`UC-N` id format established here (AC3 left it open: "`UC-1` / a slug").**
   Chose `UC-N` — plain integer, **append-only**, stable under reorder/edit/delete
   (mirrors jig's spec `NNN` / ADR `NNNN` numbering; slug-safe for the unquoted
   flow-list serializer). Slice 01 shipped the `## Use cases` entries **id-less**,
   so this slice retrofits ids onto the section format. Per
   [ADR-0010](../../decisions/adr-0010-amendment-scope-records-vs-live-prose.md)
   the template / `vision-elicitation` SKILL.md / worked examples are **live
   operational prose** (updated inline to show `- UC-N: …`); the closed-DONE
   slice-01 *slice file* was left untouched.
3. **`use_cases:` lives in `spec.md` frontmatter, not slice frontmatter.** The
   trace unit is a *spec* (AC2/AC3 say "a new spec carries…"). The
   `dependencies:`-style shape is the same flow-list *shape*, not the same
   physical line (`dependencies:` is per-slice).
4. **No field-specific parse code added.** `parse_frontmatter`'s generic
   `_parse_flow_list` already round-trips `use_cases: [UC-1, UC-3]`; verified by
   a round-trip test rather than new code. The `docs/conventions.md` "update
   `parsing.py` AND the template together" obligation is met by that round-trip
   test pinning the pairing.
5. **Deterministic core ships a broader API than 068-02 consumes — intentional
   forward-shaping for slice 03, not scope creep.** `use_cases.py` exposes
   `parse_use_cases` / `resolve_use_cases` (+ `has_entries`, `is_resolved`,
   `ResolveResult`) shaped for slice 03's project-wide coverage check, and
   explicitly disclaims building that check. `is_near_duplicate` ships as a
   deterministic helper that **informs** the conversational confirm step
   (AC5b-ii), never replacing the judgment.
6. **Seed `002-first-spec` template also got `use_cases: []`** for
   scaffold→first-spec parity (slightly beyond AC2's strict `workflow.py new`
   scope); the closed-DONE `001-adopt-jig` worked-example record was left
   untouched.
7. **Review nits (all non-blocking) addressed inline at reconciliation
   (ADR-0010 live prose):** `classify` → `classify_spec` in SKILL.md (compliance +
   craft) + surface test tightened to pin the exact symbol; "`workflow.py`/`use_cases.py`
   allocate `max+1`" → "`use_cases.next_use_case_id` allocates `max+1`" (craft —
   only `use_cases.py` has the allocator); docstring notes added to
   `parse_use_cases` (no fenced-code awareness; duplicate-`UC-N` last-win) and
   `is_near_duplicate` (pre-parsed-map signature asymmetry) — the two edges slice
   03 inherits.
8. **One arch nit empirically dismissed (false positive).** The claim that
   `_UC_BULLET_RE` lacks `_ANY_BULLET_RE`'s `(?!>)` blockquote guard and so would
   parse a quoted `> - UC-N:` line as a real entry was **tested and disproven**:
   `^\s*[-*+]` requires a bullet char at line start, and `>` blocks `[-*+]`
   (`\s*` cannot consume `>`), so blockquoted UC lines never match. No guard was
   added — it would be a no-op.
9. **Runner-only tests (no fix; flagged).** Running `test_workflow.py` standalone
   surfaces 4 `ModuleNotFoundError: No module named 'skills'`
   (`NewSpecScaffoldsFilePerSliceTests`) — they need the repo root on `sys.path`,
   which `scripts/run_tests.py` provides; they pass there. Pre-existing, unrelated
   to this slice; **filed** as a learnings entry ("Some test files are runner-only"
   in [docs/memory/learnings.md](../../memory/learnings.md)) at reconciliation, per
   the reconciliation review's note.

**Verification:** full suite green (`scripts/run_tests.py` — 2580 OK after the
reconciliation edits, exit 0), `uvx ruff check .` clean, `spec_lint` clean,
`validate_manifests.py` 3/3.
