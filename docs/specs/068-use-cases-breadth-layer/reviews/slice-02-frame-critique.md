---
slice: 068-02 — feed-forward-and-trace-links
pass: frame-critique
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-10T23:20:11Z
prompt_source: review.py frame-critique
---

VERDICT: pass

REASONING:
The frame's genuinely load-bearing assumption is **part (1) of the uptake bet**:
that an author, prompted at the empty-`use_cases:` state, will choose *cite* or
*grow* often enough — rather than reflexively *decline* — for the prompt to reduce
init-incompleteness. The author handles this honestly: the assumption is explicitly
named as thin-evidence (one user, not measured), the more brittle sub-assumptions
have been *retired by design* (the trigger now fires mechanically on the empty-field
state, not on voluntary self-report — closing the "inert on the gaps it must catch"
hole; and the grow-quality guard verifiably reuses slice 01's real dedup + goal-level
normalize pass, vision-elicitation SKILL.md L200-216), and a clean discriminating
signal (signal (i): thin section despite many empty-field prompts ⇒ "doesn't-bind")
plus a kill criterion let the failure be *attributed and unwound cheaply* post-ship
using only slice 03's coverage data and git history — no new instrumentation. The
residual bet is named, bounded, and cheap to discover/reverse; that is a surviving
frame, not a proven-zero risk.

SPECIFIC ISSUES:
- **Primary load-bearing assumption — "prompted at the empty-field state, authors
  choose grow/cite often enough rather than reflexively declining (c)":** The
  strongest attack is the spec's *own* §A2 "doesn't-bind" worry turned on the prompt
  itself — decline is deliberately the cheapest, zero-friction, one-step path (AC5:
  "every path including decline is one step"), and the agent hitting it is
  *mid-depth-first-draft under 055/057 context pressure*, exactly the condition the
  ADR names as the possible true cause of divergence. So the rational move at that
  moment is almost always (c) decline ("infra / refactor / defer"), and a decline is
  indistinguishable in the moment from a legitimate untraced spec — meaning the
  mechanism could fire perfectly, log perfectly, and still grow the section almost
  never. If that is how reality behaves, the *knowability-at-init* gap that this
  slice exists to close stays open, and the whole "grow where behaviors surface"
  claim (slice 02's reason to exist) collapses to ceremony — slice 03 then reports
  gaps the author already waved through. **Why the frame nonetheless survives:** this
  is correctly diagnosed as an *effectiveness/uptake* bet, not a *reachability* bet
  (the reframing from slice 01 is real and sound); it is honestly flagged as the
  thin-evidence load-bearing premise; it is observable post-ship via signal (i) (high
  decline rate on specs that do serve behavior) with **no new instrumentation**; and
  it is cheap to unwind — ADR-0025's third kill criterion already says "if authors
  routinely carry no resolvable trace link, drop the trace requirement, keep the
  section documentation-only." Discovering this after implementation is *not*
  expensive (the trace-link/prompt machinery is a bounded `parsing.py` + template +
  prompt change, and slice 04 — the only thing load-bearing on populated trace links
  — is deferred), so building it to *learn the uptake rate* is itself the cheapest
  available probe. Risk named, bounded, cheaply reversible — the bar for a surviving
  frame, not for a fail.

---
PROVENANCE: This verdict validates the frame for slice 02 after a 3-round
adversarial iteration. All rounds run by a fresh, independent `general-purpose`
reviewer (no shared context between rounds). History:

- **Round 1 (needs-changes) — trigger reachability.** The original AC5 grow trigger
  fired only when `use_cases:` cited an *unresolvable* id or the author *volunteered*
  "this is a new behavior." But AC4 blesses an empty/absent `use_cases:` as the soft,
  non-erroring state — so a gap-creating author most naturally leaves the field empty,
  tripping *neither* branch. The trigger was therefore unreachable in exactly the gap
  case it must catch (the same Design-X dead end slice 01's frame-critique documented),
  collapsing grow-on-discovery onto voluntary self-report under the §A2 context
  pressure the ADR itself doubts. **Fix:** AC5 reframed to fire on a *deterministic
  predicate over the trace field* — empty/absent/unresolvable `use_cases:` at
  spec-draft/framing — the same signal slice 03's coverage check reads, just earlier.

- **Round 2 (needs-changes) — grow quality + frame integrity.** Two findings.
  *(Primary)* The reachable trigger left grow *quality* unobserved: AC5(b)-grow could
  mint a spec-shaped (requirements-level) entry or a near-duplicate of an existing use
  case, feeding §A2 *coarseness/false-coverage* while the discriminating signals
  (count-up, decline-low) misread it as success — so the kill criterion structurally
  could not see that failure. **Fix:** AC5(b) gained a point-of-growth confirm-step
  guard (goal-level grain enforcement + near-duplicate → route-to-cite, reusing slice
  01's real normalize/dedup pass), and the spec's `## Assumptions` reframed the residual
  to a *two-part uptake-and-quality* bet and added discriminating signal (ii), which
  makes coarseness-via-grow visible via slice 03's coverage data + section text.
  *(Secondary)* The spec had pre-narrated this very critique as completed ("sharpened by
  slice 02's own frame-critique, 2026-06-10…") and forward-linked a not-yet-existing
  verdict file — pre-writing the verdict. **Fix:** all premature dated self-references
  and the dead forward-link removed; the design rationale now stands on its own merits.

- **Round 3 (pass) — this verdict.** With reachability and grow-quality retired by
  design, the residual is the honestly-named effectiveness/uptake bet above. The frame
  survives the strongest attack: risk named, bounded by the overridable default,
  observable post-ship without new instrumentation, and cheaply reversible.

Model policy: all frame-critique passes run at Opus (equal-or-stronger than the
author); never downgraded for cost (ADR-0020).
