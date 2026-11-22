---
status: DRAFT
dependencies: [adr-0070]
last_verified: 2026-11-21
kind: feature
arch_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 125-01 — gate-mode-resolver

**Goal:** a project can set the review-evidence gate to `off`, `observe` or
`enforce` from its env var or `scaffold.json`; in `observe` a transition that
would have been refused goes through and the would-block is recorded; every
refusal and would-block says which gate, which rule, why, and how the mode
was set.

**Decision:** [ADR-0070](../../decisions/adr-0070-gate-modes-off-observe-enforce.md)
§1–§4; spec 125 D1–D2.

**DoR:**
- ⬜ ADR-0070 Accepted.
- ✅ The review-evidence switch is read at three sites, all through
  `evidence_gate_enabled` (`_common/review_evidence.py:160-174`):
  `workflow.py:919` (transition), `adr.py:933` (ADR accept),
  `review_evidence.py:830` (bug evidence). Only the first logs a bypass
  (`workflow.py:926`).
- ✅ The shared opt-out predicate and falsey set are
  `_common/parsing.py:85-99` (`ENV_FALSEY`, `env_gate_enabled`).
- ✅ The review-passed DoD auto-tick runs after the gate in `transition`
  (`workflow.py:1625-1629`).
- ⬜ If spec 123's base-ref seam has landed, read the `gates` block through
  it (ADR-0068 §2: other gates opt in "when they gain a project-editable
  definition"); otherwise read the working tree, as this slice's ACs say.
- ⬜ Confirm the docs that state the `=0` bypass before editing them:
  `docs/workflow.md:443-449`, `skills/spec-workflow/SKILL.md:615`,
  `templates/docs/workflow.md.template:107`.

**Assumptions:** None beyond spec A2, A3, A5.

**Acceptance Criteria:**

1. **One resolver.** `skills/_common/gate_mode.py` returns `(mode, source)`
   for a named gate, with `mode` in `off | observe | enforce` and `source` in
   `env | config | default`. Precedence: the gate's env var, then
   `scaffold.json` → `gates.<name>.mode` at the project root, then the gate's
   default. A registry in the module lists each gate's name, env var, default
   mode and rule source (ADR or spec). This slice registers
   `review-evidence` (env `JIG_REVIEW_EVIDENCE_GATE`, default `enforce`, rule
   ADR-0014 §5).
2. **Old values keep meaning; typos fail safe.** Env tokens in `ENV_FALSEY`
   resolve to `off`; `observe` and `enforce` resolve to themselves; the truthy
   tokens (`1/true/on/yes`) resolve to `enforce`. Matching is
   case-insensitive and whitespace-trimmed. Any other env or config value, a
   malformed `scaffold.json`, or a non-object `gates` block resolves to the
   gate's default and prints one stderr warning naming the bad value and its
   source. Nothing resolves to `off` by accident.
3. **Review-evidence uses it at all three sites.** In `transition`, ADR
   `accept` and bug evidence validation:
   - `off`: today's behaviour (the check does not run), and all three sites
     now append the `gate_bypassed` event with `mode_source`.
   - `enforce`: today's refusal, unchanged exit code.
   - `observe`: the check runs; if it would refuse, the command proceeds and
     exits as it would have without the gate, prints one `would block` note
     naming the diagnostics, and appends a `gate_would_block` event (gate,
     reason codes, spec ref, `mode_source`, timestamp; no file content). If
     it would not refuse, nothing is printed or logged.
4. **Observe does not tick the review box.** When `observe` lets a
   transition through whose evidence did not clear, the review-passed DoD
   auto-tick is skipped and the note says so. `off` keeps today's tick (the
   check did not run, so nothing is known); `enforce` only ticks after the
   evidence clears, as today.
5. **A refusal says why.** Block and would-block output opens with one header
   line naming the gate, the mode and its source, and the rule, for example
   `[gate review-evidence · enforce (default) · ADR-0014 §5]`, followed by
   today's diagnostics and the ways forward: produce the evidence, or set the
   mode deliberately (`JIG_REVIEW_EVIDENCE_GATE=observe|0`, or
   `gates.review-evidence.mode`).
6. **The docs say it.** `docs/workflow.md`, `skills/spec-workflow/SKILL.md`
   and `templates/docs/workflow.md.template` describe the three modes, the
   precedence, that `=0` still means off, and that observe skips the DoD
   tick. Live prose is corrected inline (ADR-0010).

**Edge cases to cover explicitly:**
- `JIG_REVIEW_EVIDENCE_GATE=OFF` (case) and `" 0 "` (whitespace) resolve to
  `off`.
- `JIG_REVIEW_EVIDENCE_GATE=obsrve` resolves to `enforce` with a warning.
- Env `observe` beats config `enforce`; config `observe` beats the default.
- `scaffold.json` absent, unparseable, or with `"gates": []` → default, no
  crash.
- Observe at `→ DONE` with a missing reconciliation verdict: proceeds,
  records one event, does not tick.
- A frame-review-flagged ADR accepted in observe without its frame-critique
  verdict: accept proceeds and the event names the ADR.

### Behavioral rules

| Rule | Operation/control | Actor | State/precondition | Outcome | Rationale | AC |
|------|-------------------|-------|--------------------|---------|-----------|----|
| BR-1 | evidence-gated transition / accept | agent or person | mode `off` | allowed; check not run; `gate_bypassed`; DoD tick as today | `=0` back-compat | AC3, AC4 |
| BR-2 | same | same | mode `observe`, evidence clears | allowed; silent; no event | nothing would have blocked | AC3 |
| BR-3 | same | same | mode `observe`, evidence does not clear | allowed; one `would block` note; `gate_would_block`; no DoD tick | log what would have been blocked, impact no one | AC3, AC4 |
| BR-4 | same | same | mode `enforce`, evidence does not clear | refused, exit 2; header line + diagnostics | today's behaviour, now says why | AC3, AC5 |
| BR-5 | mode resolution | any | unrecognised env/config value | gate default + warning | a typo never turns a gate off | AC2 |

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule (only if this slice closes the
      spec).

**Anti-horizontal-phasing check:** after this slice, a project can run the
review-evidence gate in `observe`, keep working, and find each transition
that would have been refused in `.claude/skill-usage.jsonl`, with the
review-passed box left unticked so nobody mistakes it for a review.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO_ |
| `docs/specs/README.md` | `updated` | _TODO_ |
| `docs/product-vision.md` | `no-op` | _TODO_ |
| `docs/architecture.md` | `no-op` | _TODO: new `_common/gate_mode.py` module boundary._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO_ |
| `docs/inbox.md` | `no-op` | _TODO_ |
| `docs/refinement-todo.md` | `no-op` | _TODO_ |
| `docs/memory/**` | `no-op` | _TODO_ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO_ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO_ |
