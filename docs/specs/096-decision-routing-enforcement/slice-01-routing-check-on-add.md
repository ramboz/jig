---
status: READY_FOR_IMPLEMENTATION
dependencies: []
last_verified: 2026-07-22
arch_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 096-01 — routing-check-on-add

**Goal:** `decisions.py add-lightweight` refuses a decision whose own text says
it belongs in an Architectural Decision Record (ADR), names what it matched, and
points at `adr.py new` — with `--confirm-lightweight` as the documented escape
hatch. `ADR_TRIGGER` stops being a string the helper only renders.

`arch_review: true` — this adds a gate to a **tier-0** helper that four
documented surfaces and the scaffold path invoke, and gates are governed by
[ADR-0011](../../decisions/adr-0011-spec-gate-model.md). The shape of the check
(two-signal, derived from the rubric rather than invented) is the reviewable
decision, recorded in
[ADR-0039](../../decisions/adr-0039-decision-routing-gate.md).

**DoR:**
- ✅ [ADR-0031](../../decisions/adr-0031-load-bearing-decision-adr-trigger.md)
  defines the trigger sentence; this slice applies it rather than changing it.
- ✅ [ADR-0011](../../decisions/adr-0011-spec-gate-model.md) + [spec 078](../078-gate-bypass-telemetry/spec.md)
  set the house gate shape: on by default, documented escape hatch, bypass
  telemetry. `_common/parsing.py:88` and `_common/gate_telemetry.py:24` are the
  shared backings.
- ✅ The rubric's two ADR criteria are already written down and are what the
  evaluator reads from (`lightweight-decisions.md:13`) — the check is a
  transcription of an existing rule, not a new policy.
- ✅ jig's own `lightweight-decisions.md` supplies the must-not-flag corpus: one
  illustrative UI-copy entry (`:55`) and one `## Template` fence heading.

### The two-signal rule (why it is not a keyword list)

The rubric states **two** independent ADR criteria, and they are not the same
shape:

| # | Criterion (verbatim from the rubric) | Condition |
|---|---|---|
| (a) | "A load-bearing design choice **with rejected alternatives**…" | conjunction — needs *both* |
| (b) | "Also: any change to a **module boundary, public contract, or cross-cutting policy**." | unconditional |

A flat keyword list collapses that distinction and breaks immediately on jig's
own corpus: the illustrative entry is *"Onboarding CTA copy: 'Get started' over
'Sign up'"* — a rejected alternative in the plainest sense, and one the rubric
sends to the **lightweight** home by name ("UI string or translation choices").
The rubric's own wording is what saves it: *"no **real** rejected alternatives"*.
"Real" is doing the work, and criterion (a) supplies its test — the alternatives
have to attach to a **load-bearing** choice.

So the evaluator carries three marker groups and one rule:

- `BOUNDARY` — module boundary, public contract, protocol, schema, cross-cutting
  policy, public API surface. **Flags alone** (criterion b).
- `ALTERNATIVES` — rejected, ruled out, discarded, instead of, rather than, as
  opposed to, in favour/favor of, alternative(s), trade-off. **Never flags
  alone.**
- `LOAD_BEARING` — load-bearing, architectural, structural, replaces/replacing,
  native implementation, vendored, dependency, coupling, invariant, migration,
  irreversible/hard to reverse. **Never flags alone.**

**Flag iff `BOUNDARY`, or (`ALTERNATIVES` and `LOAD_BEARING`).**

Checked against both cases that matter: the illustrative UI-copy entry hits at
most `ALTERNATIVES` → no flag. The reported case hits `LOAD_BEARING`
("replacing… with our own native implementation") *and* `ALTERNATIVES` (the
rejected alternatives it added at step 3) → flag.

**Acceptance Criteria:**

1. **A load-bearing decision with rejected alternatives is refused.** `add-lightweight`
   with `--decision`/`--context` text hitting `ALTERNATIVES` **and**
   `LOAD_BEARING` exits non-zero, writes **nothing** (no seed, no append), and
   the message (a) names which groups matched and the matched phrase, (b) quotes
   `ADR_TRIGGER` verbatim from the constant, and (c) names `adr.py new` as the
   route and `--confirm-lightweight` as the escape hatch.
2. **A boundary change is refused on its own.** Text hitting `BOUNDARY` alone —
   no alternatives language anywhere — is refused identically. Criterion (b) is
   unconditional, so requiring a second signal would under-enforce it.
3. **A genuinely lightweight decision is untouched.** jig's own illustrative
   entry, re-recorded through the CLI verbatim (title, decision, context, scope),
   exits 0 and appends exactly as it does today. This is the false-positive
   guard, and it uses the real corpus rather than a fixture invented to pass.
4. **`ALTERNATIVES` alone does not flag, and `LOAD_BEARING` alone does not
   flag.** Two explicit tests, one per group, so a later "simplification" to a
   flat keyword list fails rather than silently re-breaking AC3.
5. **`--confirm-lightweight` proceeds.** The same input as AC1, plus the flag,
   exits 0 and appends. The gate is a deliberateness signal, not an authority
   (ADR-0011) — the operator who has read the flag can still record.
6. **`JIG_DECISION_ROUTING_GATE=0` disables the check**, honouring
   `_common.parsing.env_gate_enabled`'s falsey-token set, and emits one
   `gate_bypassed` event via `_common.gate_telemetry.emit_gate_bypass` naming
   this gate and that env var. `--confirm-lightweight` emits **no** event — it is
   the gate working as designed, not an override of it (spec 078 instruments
   env-var escapes).
7. **Matching is case-insensitive and whitespace-tolerant**, and scans all four
   text fields (`--title`, `--decision`, `--context`, `--scope`) — `--scope` is
   where "module" lands.
8. **The evaluator is importable and pure.** A module-level function returning
   the matched groups/phrases for a text, with no filesystem or environment
   access, so 096-02 and 096-04 reuse it rather than re-deriving the rule.
9. **No change to `add-lightweight`'s existing arguments or output on the happy
   path.** Every documented command block (`SKILL.md:122-124`,
   `lightweight-decisions.md:26`, the template, `decision_scan.py:357-362`,
   `migrate.py`'s nudge) keeps working unchanged.

**Edge cases covered explicitly:**

- A marker inside a larger word must not match (`"alternatively"` must not fire
  `alternative`; `"interfaces"` in prose about a UI must not fire `interface`) —
  word-boundary matching, asserted.
- Empty `--context`/`--scope` (both default to `""`) must not crash the scan.
- The refusal must fire **before** `seed_lightweight`, so a refused call cannot
  leave a record home behind as a side effect — the same ordering
  `CliOrderingTests::test_invalid_input_does_not_seed` already pins for field
  validation.

**Anti-horizontal-phasing check:** after this slice an operator who tries to
misfile an ADR-worthy decision is stopped at the moment of writing, with the
route named. It is not "the evaluator exists and a later slice will call it".

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions) on Python 3.9.
- [ ] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Architecture review passed (`arch_review: true`).
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] Host packages regenerated (`scripts/build_host_packages.py`) — the helper
      is mirrored into `hosts/claude/` and `hosts/codex/`.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.
