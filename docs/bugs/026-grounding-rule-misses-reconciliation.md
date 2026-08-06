---
status: DONE
tier: standard
severity: low
claimed_by: claude/jig-131-ceremony-review-6v7g4l
regression_test: skills/spec-workflow/test_workflow.py::ReconciliationGroundingRequirementTests
main_repro_checked_at: 2026-08-02
main_repro_ref: origin/main@2850a09
main_repro_result: reproduces
red_confirmed_at: 2026-08-02
green_confirmed_at: 2026-08-02
fix_class: guardrail
security_surface: false
escalated_to:
---

# Bug 026: grounding-rule-misses-reconciliation

> Reported as [issue #131](https://github.com/ramboz/jig/issues/131) by a
> collaborator, with partial fix in [PR #164](https://github.com/ramboz/jig/pull/164).
> Maintainer pre-approved the approach on the issue ("Sounds good to me. Simple
> enough fix.").

## Symptom

ADR-0020 §1's grounding rule — a load-bearing factual claim about a *runnable*
surface (library/API capability, version/perf behavior, behavior of existing
code) must be backed by an executed probe or a `file:line` citation, and
anything unverifiable is marked as an assumption rather than asserted — governs
**spec/ADR authoring** but never reaches the **reconciliation checklist**.

Reconciliation is where long-lived front-door prose (`docs/architecture.md`)
actually gets rewritten — docs everyone reads and nobody re-derives — so it is
the authoring surface with the highest blast radius, and it was the only one
without the discipline. During a real reconciliation pass (SymPill slice
008-17, reported on the issue) several confident factual claims were written
into `architecture.md`; two were false and caught only by the reconciliation
reviewer. Every claim written **with** a `file:line` citation was true; both
written **without** one were false.

## Repro

On `origin/main`, read the reconciliation checklist's "Architecture impact"
item (`skills/spec-workflow/SKILL.md:702-703`):

```markdown
- [ ] **Architecture impact** — did module boundaries or public contracts change?
      If yes, update `docs/architecture.md` AND write an ADR.
```

It says *update the doc*. It does not say *ground what you write into it*. The
grounding requirement that spec-authoring step 6 carries
(`skills/spec-workflow/SKILL.md:254`, "Ground your factual claims (spec 064-02
/ ADR-0020 §1–§2)") is absent here. `grep -c "executed probe or a"
skills/spec-workflow/SKILL.md` → `0` on main.

## Evidence

- `skills/spec-workflow/SKILL.md:254-259` — spec-authoring step 6, under
  "### Creating a new spec", carries the full grounding rule (executed probe /
  `## Assumptions`, citing spec 064-02 / ADR-0020 §1–§2).
- `skills/spec-workflow/SKILL.md:702-703` — the reconciliation checklist's
  "Architecture impact" item, under `## Reconciliation checklist` (heading at
  line 686), carries no grounding requirement at all.
- `docs/decisions/adr-0020-spec-frame-hardening.md:77-82` — the canonical
  "Grounding requirement" (mechanism 1 of the frame-hardening ADR). Its scope
  is stated as claims "in a spec/ADR", i.e. authoring — reconciliation is not
  named.
- Reporter's mechanizable signal (issue #131): in that session every claim
  written with a `file:line` citation was true; both written without one were
  false. Writing the citation is what forces the read.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. -->
- [ ] H1: the grounding rule is genuinely present for reconciliation but phrased
      generally elsewhere (e.g. in `docs/workflow.md`'s reconciliation section),
      so this is only a local omission in the SKILL checklist — falsify by
      grepping the reconciliation surfaces for the grounding language. Falsified:
      `grep -rn "executed probe" skills/spec-workflow/SKILL.md docs/workflow.md`
      finds it only at spec-authoring step 6, never on any reconciliation
      surface.
- [x] H2 (leading): the grounding discipline was authored **only** into the
      "Creating a new spec" path (step 6) and never propagated to the
      reconciliation checklist, because the two authoring surfaces evolved
      independently — so the highest-blast-radius surface (live front-door prose
      rewritten during reconciliation) inherited no grounding requirement.
      Confirmed by reading both sites: step 6 (line 254) has the rule; the
      reconciliation "Architecture impact" item (line 702) says only "update the
      doc AND write an ADR".

## Root cause

ADR-0020 §1 scoped its grounding requirement to spec/ADR *authoring* and the
rule was wired into exactly one checklist — spec-authoring step 6. The
reconciliation checklist's "Architecture impact" item, which is what actually
directs an agent to rewrite `docs/architecture.md`, was written to answer "did
boundaries change? then update the doc and write an ADR" and never inherited
the "ground what you write" clause. Nothing single-sourced the grounding rule
across both authoring surfaces, so the surface with the highest blast radius —
live prose that everyone reads and nobody re-derives — was the one left without
the discipline. This is a coverage gap in a soft guardrail, not a logic defect.

## Fix class

`guardrail` — extends an existing preventive discipline (ADR-0020 §1 grounding)
to the authoring surface that was missing it, and adds a regression test that
pins the requirement's presence so it cannot silently regress. No runtime logic
changes; the deliverable is checklist prose plus its drift guard.

## Fix

Extend the "Architecture impact" item in the reconciliation checklist
(`skills/spec-workflow/SKILL.md`) with the same grounding requirement ADR-0020
§1 imposes at spec-authoring time — probe or `file:line` citation, unverified
marked as an assumption — cross-referencing ADR-0020 §1 and spec-authoring step
6. Regenerate the two generated host copies via
`scripts/build_host_packages.py` so all three `SKILL.md` copies stay
byte-identical (CI drift guard enforces this).

The added prose dogfoods its own rule: both factual self-citations were
verified against source — "ADR-0020 §1" →
`docs/decisions/adr-0020-spec-frame-hardening.md:77`; "spec-authoring step 6" →
`skills/spec-workflow/SKILL.md:254`.

## Already tried

Nothing discarded. The prose wording originated in PR #164 (author preserved on
the fix commit) and was accepted as-is after review; three non-blocking craft
nits (verbatim restatement vs. single-sourcing; "candidate warning" phrasing;
"§1" vs "§1–§2") were recorded as reconciliation notes rather than applied, to
keep the maintainer-approved wording faithful to what was reviewed.

## Regression test

`skills/spec-workflow/test_workflow.py::ReconciliationGroundingRequirementTests`
— asserts that the reconciliation checklist section (sliced from the
`## Reconciliation checklist` heading to the next `##` heading, so a match in
spec-authoring step 6 cannot satisfy it) carries the grounding requirement, in
all three `SKILL.md` copies (source + both `hosts/**` mirrors). It pins the
distinctive clause "executed probe or a `file:line` citation" plus the
mark-as-assumption instruction, so removing the requirement — or letting a host
mirror drift from source — turns the test red.

## Proof

- **Red:** the `→ FIXING` gate witnessed the regression test red (stamped
  `red_confirmed_at: 2026-08-02`). Full-suite baseline against the unmodified
  reconciliation checklist: `Ran 3872 tests in 255.861s — FAILED (failures=1,
  skipped=7)`, the sole failure being
  `ReconciliationGroundingRequirementTests` (the grounding clause absent from
  the reconciliation section in all three `SKILL.md` copies).
- **Green:** after adding the grounding clause to source and regenerating the
  two host mirrors, `python3 skills/spec-workflow/test_workflow.py
  ReconciliationGroundingRequirementTests` → `Ran 1 test — OK`. The
  `→ REVIEWED` gate re-ran the full suite green (stamped `green_confirmed_at`),
  and `python3 scripts/build_host_packages.py --check` reports the committed
  host packages in sync with source.
- **No regressions:** the only changed test is the new one; the full suite is
  green at the REVIEWED gate.

## Learning

A discipline wired into one authoring surface does not automatically cover its
siblings. ADR-0020 §1's grounding rule lived only in spec-authoring step 6; the
reconciliation "Architecture impact" item — the surface that actually rewrites
live front-door prose, the highest blast radius — inherited nothing. When a
rule has more than one authoring entry point, enumerate them: the one you
forget is often the one that matters most.

Tooling gotcha surfaced while running this through `bug-fix`: jig's
`.jig/test-command` (`python3 scripts/run_tests.py`) ignores the `path::Class`
selector `tdd.py` appends and always runs the full discovered suite (~256s in
this environment). The red→green teeth still hold — a single failing test turns
the whole suite red — but a bug whose `regression_test` points at the largest
test file makes both the FIXING and REVIEWED gates run the entire suite.
Recorded in [docs/memory/learnings.md](../memory/learnings.md).

## Main recheck
- 2026-08-02 - `origin/main@2850a09` -> reproduces: git show origin/main:skills/spec-workflow/SKILL.md | grep -c 'executed probe or a `file:line` citation' -> 0; the reconciliation 'Architecture impact' item (SKILL.md:702-703) carries no grounding requirement on fresh origin/main
