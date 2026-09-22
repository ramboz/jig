---
status: Proposed
dependencies: [adr-0011, adr-0014, adr-0055]
last_verified: 2026-09-22
frame_review: true
---

# ADR-0062: Convention rules carry MUST/SHOULD severity and an advisory-to-enforced promotion state

## Status

Proposed (2026-09-22)

## Context

jig's conventions live in `docs/conventions.md` as prose blocks —
`**Rule:** / **Why:** / **How to apply:**` — grouped under four headings
(skill authoring, hook authoring, agent authoring, document conventions; probed
2026-09-22: ~20 rules, no severity marker on any of them, the words "must" /
"should" appearing five times as ordinary prose). Every rule carries the same
implicit weight. The file is protected by the spec-gate
([ADR-0011](./adr-0011-spec-gate-model.md)): editing it is a *deliberate* act
behind `JIG_CONVENTIONS_APPROVED=1`, and the scaffolded copy
(`templates/docs/conventions.md.template`) inherits the same shape.

Enforcement is binary and per-gate. The reviewer prompts built by `review.py`
append an unconditional principles check that names the seven design principles
in `docs/product-vision.md` (`_principles_check_block`, spec 024-01) — but the
conventions file itself is not rendered to the reviewer by rule, and a reviewer
finding does not say *which* rule it violates or whether that rule is
blocking. The review-evidence gate ([ADR-0014](./adr-0014-review-evidence-model.md))
withholds `REVIEWED` on a `verdict != pass`, so in practice the reviewer decides
ad hoc which convention breaches are pass-blocking. The gate-bypass telemetry
(spec 078) counts bypasses with no denominator — the deferred
`docs/refinement-todo.md` entry "gate-bypass digest denominator" names exactly
this gap: a count of zero cannot distinguish a golden rule from one that never
fires.

The trigger for deciding now is external prior art recorded in
[R-001](../research/R-001-cloudflare-adlc-assessment.md): Cloudflare's
engineering-standards "Codex" structures each standard as an RFC item with a
MUST or SHOULD keyword, explicit ownership, and a **lifecycle state** — a rule
starts as a non-blocking recommendation the moment it is approved, and someone
must *explicitly promote* it to "enforced" before an unmet MUST withholds
approval. Their reported ratio (roughly 230,000 deviations surfaced, roughly
16,000 approvals withheld) shows most of the value is in the *reporting*, with
blocking reserved for a promoted minority. That is ADR-0011's deliberateness
principle applied per rule rather than per file, and it supplies the missing
denominator for free: a finding keyed to a rule is a fire; an override is a
bypass.

Two constraints frame the decision. The leanness lens
([ADR-0055](./adr-0055-leanness-lens-folds-into-existing-passes.md)) says fold
lenses into existing passes — no new gate. And jig's design principle 1 says
everything that MUST happen is a hook; a judgment rule (e.g. "one skill, one
job") cannot be a hook, so severity here governs the *review verdict*, not a
deterministic block.

## Decision Options Considered

### Option A: Status quo — prose rules, reviewer judgment, binary gates
- **Pros:** Zero change; the file stays human-readable prose; no migration.
- **Cons:** Every rule weighs the same, so a reviewer either over-blocks on nits or under-blocks on load-bearing rules; findings cannot cite a rule; the bypass telemetry stays denominator-less; adding a rule is implicitly adding a blocker (or implicitly adding noise) with no way to say which.

### Option B: Per-rule severity + promotion state, rendered into the review passes (recommended)
- **Pros:** Keeps `conventions.md` as the single prose source (no parallel registry); reuses the existing spec-gate for promotion (a promotion is an edit to the protected file, already deliberate); reuses the existing review passes and verdict envelope (no new gate, per ADR-0055); new rules default to advisory so adding a convention never silently adds a blocker; findings keyed to a rule id give `gate-stats` a per-rule fire count.
- **Cons:** A one-time owner-approved migration to tag the ~20 existing rules; the reviewer prompt grows by the rendered rule list (context cost — see the refinement-todo entry on context-filtered rules); severity of a judgment rule is still applied by a model, so "enforced MUST" is a strong verdict instruction, not a deterministic guarantee.

### Option C: Structured rule registry (JSON/YAML) rendered to `conventions.md`
- **Pros:** Machine-filterable — a consumer can load only the rules relevant to the artifact under review (Cloudflare's shape; directly serves spec 055 context discipline).
- **Cons:** Two sources of truth, or a generated prose file that the spec-gate then protects for no reason; premature — no consumer needs filtering today and the rule count is small. Parked as the mitigation in the refinement-todo entry "context-filtered convention rules"; its trigger is a measured prompt-size cost or a second consumer.

### Option D: A standalone conventions-check hook that scans diffs against rules
- **Pros:** Deterministic where a rule is mechanically checkable.
- **Cons:** Most conventions are judgment rules and cannot be linted; a new gate contradicts ADR-0055; the mechanically checkable subset already has homes (`validate_manifests.py`, `spec_lint.py`, `health.py`). Rejected.

## Recommended Decision

Adopt **Option B**.

1. **Every `**Rule:**` block in `docs/conventions.md` gains three fields:** a
   stable `**Id:**` slug (e.g. `skill.description-shape`), a `**Severity:**` of
   `MUST` or `SHOULD`, and a `**State:**` of `advisory` or `enforced`. The
   scaffold template mirrors the shape. Design principles in
   `docs/product-vision.md` are **not** re-tagged — they are principles, not
   rules, and the existing principles check block is unchanged.
2. **New rules start `advisory`, whatever their severity.** Promotion to
   `enforced` (and demotion back) is a deliberate edit to the protected file —
   already gated by ADR-0011 — and is recorded as a lightweight decision (or an
   ADR when contested). The one-time migration that assigns severity and state
   to the existing rules is an owner-approved change under the spec 102
   guardrail; this ADR does not pre-assign them.
3. **The review passes render the rules by severity and state.** `review.py`
   appends the enforced rules to the compliance/craft prompts as *blocking*
   checks and the advisory rules as *report-only* checks; a finding cites the
   rule id. The verdict envelope withholds `pass` **only** for an unmet
   `enforced` + `MUST` rule. Advisory findings are still reported — that is
   where most of the value lives.
4. **Findings keyed to a rule id feed the telemetry.** A recorded review
   verdict lists the rule ids it found against; `workflow.py gate-stats` can
   then report per-rule fire counts next to bypass counts, closing the
   denominator gap for conventions without a new emit surface.

## Consequences

**Becomes easier:**
- Adding a convention is safe by default: it reports, it does not block, until
  someone deliberately promotes it.
- A reviewer verdict says which rule was breached and whether that rule is
  blocking, so a `needs-changes` is auditable and a `pass` with advisory
  findings is legible.
- A keep/retire decision on a rule can be made from data (fires vs overrides),
  the exact ask the deferred spec 078 denominator entry was waiting on.

**Becomes harder:**
- One owner-approved migration of the existing rules, and template parity to
  keep (`templates/docs/conventions.md.template`).
- The reviewer prompt carries the rule list; prompt-size hygiene must be
  watched (the existing 500-character block precedent), which is what parks
  Option C as a later step rather than a rejected one.
- Two more fields per rule to keep honest; a rule with a stale state is worse
  than an untagged one.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **Verified (probed 2026-09-22):** `docs/conventions.md` uses the
  `**Rule:** / **Why:** / **How to apply:**` block shape under four `##`
  headings; `review.py` builds reviewer prompts from composable blocks
  (`_principles_check_block`, `_practices_check_block`) with a stated
  per-block size precedent; the review-evidence gate keys on `verdict: pass`.
- **Unverified, load-bearing:** that a model reviewer reliably maps a breach to
  a rule *id* when the rules are rendered inline rather than hallucinating an
  id — slice 114-01 must include a fixture where the reviewer is given a
  breach and the expected id is checked.
- **Second-hand, non-load-bearing:** the Codex promotion-state description
  and its figures come from the engineering-standards *sibling* post as
  rendered by InfoQ, not read directly (the ADLC post itself was verified
  from its full text on 2026-09-22 and does not carry those details); the
  decision depends on them only for "reporting dominates blocking".

## Kill criteria

- After the migration, no rule is ever promoted or demoted in six months and
  reviewers' verdicts never cite an id → the states are dead weight; drop the
  `State:` field and keep only severity (or revert to Option A).
- The rendered rule list pushes the reviewer prompt past the prompt-size
  hygiene bar and the context-filtered mitigation (Option C) is not worth
  building → revert to the principles-only check.
- The reviewer cannot map breaches to ids reliably (the load-bearing
  assumption above fails) → keep severity as *prose* emphasis only and drop
  the telemetry leg.

## Open questions

- Who assigns the initial severity/state to the existing rules, and in what
  artifact is that migration recorded (a lightweight decision per rule, or one
  ADR-amendment-shaped record)? The spec 102 guardrail says the owner decides;
  slice 114-01's DoR carries the approval.
- Should the `analyze` skill's "principle violations" category also key on
  severity, so a cross-artifact audit distinguishes an enforced-MUST drift
  from an advisory one? Probably yes, but it is a consumer decision for the
  slice, not this record.
- Whether scaffolded projects should receive the tagged template immediately
  or only on the next `migrate` pass — the template change is safe (advisory
  by default) but adds fields adopters did not ask for.
