---
status: RECONCILED
dependencies: []
last_verified: 2026-07-08
frame_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon). -->
<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 086-01 — routing-eval harness (collision + trigger + ratchet)

**Goal:** Ship a runnable, deterministic skill-routing eval — one TF-IDF vector
space over the skill descriptions that reports description **collisions** and
**trigger routing**, plus a CI-gating test with floor ratchets — so a
description edit that collides two skills or strips a skill's routing vocabulary
fails in CI.

## Assumptions

Two load-bearing premises, surfaced sharply (frame-critique 086-01) rather than
in their most defensible form:

1. **Lexical overlap on the *positive* surface tracks semantic routing fitness —
   its gradient is not anti-aligned.** The host routes with the model
   (semantic); this slice scores surface-word overlap (lexical). Sharp failure
   mode (frame-critique PRIMARY): jig disambiguates siblings with shared
   cross-reference boilerplate ("Do not use for … use `/jig:X` instead"), which
   is exactly what teaches the *model* to route them apart but reads to a naive
   TF-IDF as *similarity* among the hardest-to-route cluster — so the gradient
   is anti-aligned (the correct fix raises cosine; the rewarded move degrades
   routing). **Mitigation (implemented):** `routing_surface()` vectorizes only
   the positive surface, dropping the negative-disambiguation tail; this dropped
   the top collision 0.44→0.22 and lifted negative routing to 100% — evidence
   the residual signal measures positive-territory overlap. **Residual + kill
   criterion:** the deeper premise (lexical ≈ semantic on the positive surface)
   is un-probed until the Tier-3 behavioral eval. If a description sharpened to
   satisfy this eval is later observed to mis-route in a real session — either
   direction (gamed-and-mis-routes, or a correct edit the eval false-flagged and
   someone reverted) — the collision + trigger gates drop to advisory
   (report-only) and slice 02's sharpening is reverted. This premise is why the
   slice carries `frame_review: true`.

2. **The pinned trigger cases track real user speech — not merely the
   descriptions.** What the trigger rule *guarantees* is narrow and sound: an
   edit that regresses a **pinned** case is caught. The un-probed leap is that
   these author-authored cases *represent how real users phrase things*. Sharp
   failure mode (frame-critique SECONDARY): the cases are hand-authored by the
   same author as the descriptions, guarded only by an honor-system "don't copy
   the description" note — so vocabulary converges and a green baseline can
   measure author *self-consistency*, not routing fitness; the ratchet freezes
   that. A craft-pass edit that strips a word real users say but that no case
   encodes passes green — so the eval does **not** guarantee that failure mode
   is caught (the spec Overview is scoped to say exactly this). **No automatic
   detector exists:** `.claude/skill-usage.jsonl` logs only which skill *fired*
   — not the prompt, and not whether it was the *wrong* skill — so
   `routing-stats` cannot flag a mis-route, and nothing today captures real user
   phrasings to seed cases from. **Guards (in force / deferred):** in force —
   the authoring note + periodic manual routing review; deferred (unbuilt,
   `docs/refinement-todo.md`) — extend the trace hook to capture the invoking
   prompt, seed cases from real phrasings, and add the semantic Tier-3 eval that
   grades an actual model's routing. **Kill criterion (manual, not automatic):**
   if a real session is observed mis-routing a prompt no case covers, add it as
   a case and treat the set as non-representative until reseeded; if it recurs,
   demote the trigger gate to advisory until Tier-3 lands.

**DoR:**
- ✅ Skill descriptions are the routing surface (spec 076 / EngTip #23) and live
  in each `skills/<name>/SKILL.md` frontmatter.
- ✅ Probe-verified: every jig skill writes its description as a YAML *folded*
  (`description: >`) block scalar, which `_common.parse_frontmatter` does not
  decode — a dedicated reader is required (confirmed against all skills).
- ✅ Probe-verified: `run_tests.py` discovers `scripts/test_*.py`
  (`start_dir=scripts`), so a test placed there runs in the suite.

**Acceptance Criteria:**

1. **A report command exists.** `python3 scripts/skill_routing.py` prints: the
   skill count, the most-similar description pairs (IDF-weighted cosine) flagged
   `~` at ≥ `COLLISION_WARN` (0.50) and `!!` at ≥ `COLLISION_ERROR` (0.75), and
   per-case trigger results. `--json` emits the same data machine-readably.
2. **Every skill is in the corpus.** The description reader extracts
   `description:` from every `skills/<name>/SKILL.md`, decoding folded (`>`),
   literal (`|`), and plain scalars; no routable skill silently resolves to an
   empty description.
3. **Collision rule.** Pairwise IDF-weighted cosine over descriptions is
   computed and reported most-similar first; the gate fails when any pair scores
   ≥ `COLLISION_ERROR`.
4. **Trigger rule.** For each `evals/cases/<skill>.json`: every `positive`
   prompt ranks its owning skill within the case's `top_k`, and every `negative`
   prompt's declared `owner` outranks the case's skill. A case file exists for
   every routable skill.
5. **Ratchet.** `skill_routing.py --min-rank1 X` exits non-zero when the rank-1
   rate < X (proving teeth). The `unittest` gate asserts: no collision ≥
   `COLLISION_ERROR`; every positive within `top_k`; rank-1 rate ≥
   `MIN_RANK1_RATE`; negative route-away rate ≥ `MIN_NEG_ROUTE_AWAY` (floors set
   just below the current baseline, raise-only).
6. **jig idiom.** The gate is a `unittest` module under `scripts/`
   auto-discovered by `run_tests.py`; zero third-party dependencies; clean under
   `ruff` (target py39) and `pyright`.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one fixture
      (engine units on synthetic corpora + real-data invariants).
- [ ] Reviewed by `reviewer` subagent (compliance). Prompt built by `review.py`.
- [ ] Craft pass (`pr-review`) passed.
- [ ] Frame-critique (adversarial) pass passed — `frame_review: true`.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice, a maintainer runs one
command and sees which skill descriptions collide and whether realistic prompts
route to the right skill, and CI fails on a routing regression — end-to-end
observable value, not scaffolding for a later slice.

### Close-out (post-DONE)
- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] Primer hygiene per spec 025-01 if this slice closes the spec.

### Deviation log (after reconciliation)

The original spec/ACs are preserved above.

1. **Retro ordering.** A working prototype (engine + tests + 19 case files +
   README) was built earlier in the same session, before spec 086 was filed;
   the lifecycle then evaluated the as-built code against these ACs. No AC was
   satisfied differently — the prototype already met AC1/3/5/6; the review round
   added the AC2/AC4 test *guards* the prototype lacked.
2. **Frame-critique drove a real design change (3 cycles).** Cycle 1 found the
   collision/trigger vectors included the shared negative-disambiguation
   boilerplate ("Do not use for … use `/jig:X` instead"), inverting the metric's
   gradient vs the semantic router. Fixed by `routing_surface()` (vectorize the
   positive surface only): top collision 0.44→0.22, negatives 93%→100%. Cycle 2
   found the Overview overclaimed ("catches vocabulary users actually say"),
   rescoped to "regression against the pinned case set." Cycle 3 PASS. See
   `reviews/slice-01-frame-critique.md`.
3. **Compliance re-review added test guards.** AC2's empty-description test was
   vacuous (`load_descriptions` pre-filters empties) and AC4's "case per skill"
   was unguarded. Added `test_no_routable_skill_resolves_empty`,
   `test_case_file_per_routable_skill`, `test_negative_case_owners_are_real_skills`.
4. **Craft nits folded in:** trimmed dead/duplicate stopwords; corrected the
   `|`-scalar docstring; dropped the stale "prototype/spike" labels; reworded the
   floor comment to state the deliberate ~10pp slack honestly.
5. **Logged, not fixed here:** several positive prompts (bug-fix, tdd-loop,
   vision-elicitation) echo description vocabulary near-verbatim — the
   self-authored-case limitation; reseed from real phrasings when the deferred
   trace-hook prompt capture lands (refinement-todo). `evaluate_case` reads
   `case["skill_name"]` unguarded (opaque KeyError on a malformed case) — minor,
   author-controlled input.
6. **Negatives are floor-ratcheted, not hard-gated.** AC4 says a negative's
   owner "outranks"; enforcement is the `MIN_NEG_ROUTE_AWAY` (0.90) floor, not a
   hard 100% (baseline 100%). By design — `main()`'s hard gate covers only
   positives-outside-top_k + collisions.
7. **ADR trigger evaluated → not warranted.** The load-bearing choices
   (lexical-not-semantic, positive-surface stripping, floors-not-hard-100%) carry
   rejected alternatives, but their rationale is fully captured in the spec
   `## Assumptions` + the frame-critique evidence + refinement-todo; a separate
   ADR would duplicate without adding a decision a future agent couldn't already
   reconstruct.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Front-door README unaffected; the eval harness is dev-internal (`evals/` + `scripts/`). |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board` (086 rows). |
| `docs/product-vision.md` | `no-op` | No product-scope change (internal dev tooling; jig has no `## Use cases` layer). |
| `docs/architecture.md` | `updated` | Added `skill_routing.py` to the `scripts/` tooling inventory alongside `spec_lint.py`/`validate_manifests.py` (parity); no module-boundary or contract change. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `deferred` | Primer hygiene runs at spec close (slice 03). `skill_routing.py` is a CI-gate script, not a skill `.py` helper, so it does not join CLAUDE.md's helper list. |
| `docs/inbox.md` | `no-op` | No inbox items resolved. |
| `docs/refinement-todo.md` | `updated` | Added the Tier-3 / real-usage-prompt-seeding follow-up. |
| `docs/memory/**` | `deferred` | `/jig:memory-sync` at spec close (slice 03) to capture the routing-eval + frame-critique learnings. |
| `docs/decisions/README.md` / ADR index | `no-op` | No ADR minted (deviation log #7). |
