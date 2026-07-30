---
status: DONE
tier: standard
severity: low
claimed_by: claude/issue-123-comment-9ba699
regression_test: skills/adr-workflow/test_adr.py::NonCanonicalProseStatusTests
main_repro_checked_at: 2026-07-27
main_repro_ref: fd7115a
main_repro_result: reproduces
red_confirmed_at: 2026-07-27
green_confirmed_at: 2026-07-29
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 013: adr-accept-strict-prose-gate

> Reported as [issue #123](https://github.com/ramboz/jig/issues/123). The
> resolution is a decision change, recorded in
> [ADR-0046](../decisions/adr-0046-adr-status-frontmatter-authority.md)
> (supersedes [ADR-0026](../decisions/adr-0026-adr-status-frontmatter.md)).

## Symptom

`adr.py accept` refuses an ADR whose prose `## Status` line carries any text
after the date, with an error that never names the trailing clause as the
cause:

```
ADR adr-0004-....md Status is not 'Proposed (...)'. Refusing to flip;
only Proposed → Accepted is supported in this slice.
```

The line *is* `Proposed (2026-07-22)`; only the decoration is unexpected. The
natural reading of the message is that the file is malformed some other way,
which is what made the diagnosis expensive enough to file.

## Repro

```markdown
## Status

Proposed (2026-07-22) — awaiting owner acceptance.
```

`python3 skills/adr-workflow/adr.py accept 0004` → exit 2. Deleting
` — awaiting owner acceptance.` makes it accept immediately.

Reported from a downstream project scaffolded from jig; the scaffolded
`adr.py` is byte-identical to the source, so the defect is upstream.

## Evidence

- `skills/adr-workflow/adr.py` — `_STATUS_PROPOSED_RE` ends `[ \t]*$`, which
  permits only whitespace after the closing paren, while its own comment
  claimed "(or with extra trailing content)". Comment and code disagreed.
- The same file's other four status readers — `_classify_status`,
  `_extract_status_and_date`, `cmd_supersede`'s gate, and the index renderer
  — all tolerate the same line and classify it correctly as `Proposed`.
  `cmd_accept` was the lone strict reader.
- `skills/adr-workflow/test_adr.py` seeded every ADR with the bare
  `<State> (date)` form, so no test ever exercised trailing content. The
  comment's promise had never been executed.

## Hypotheses

- [ ] H1: the regex is simply too strict and should be loosened to match
      trailing content — falsified by reading the rewrite it drives
      (`sub(lambda _m: f"Accepted ({_today()})", …)`): a looser pattern drops
      the authored clause, and preserving it yields the self-contradictory
      `Accepted (2026-07-23) — awaiting owner acceptance`. The reporter hit
      exactly that shape.
- [x] H2 (leading): one regex is doing two jobs — *gating* the flip and
      *rewriting* the line — so the strictness the rewrite legitimately needs
      leaks into the gate, where it does not belong. Confirmed by separating
      them: the gate now reads the classified state and the pattern is used
      only to decide whether the prose is safe to rewrite.

## Root cause

`cmd_accept` conflated two concerns in `_STATUS_PROPOSED_RE`. The rewrite
genuinely requires an exact `Proposed (YYYY-MM-DD)` match — it substitutes
the whole matched line — but the *gate* was implemented as "does the rewrite
pattern match?", which makes an authored prose format a precondition for a
machine operation whose source of truth is a different field
(frontmatter `status:`, canonical since ADR-0026).

The underlying frame is what actually had to change: ADR-0026 cast prose as a
**synchronized** mirror that the writer must always be able to rewrite, and
that invariant is only reachable if the writer can recognise every prose
line. The strict gate is a faithful consequence of that model, not an
independent slip — which is why the fix is a decision change (ADR-0046)
rather than a regex tweak.

## Fix class

`structural_fix` — the conflated gate/rewrite responsibility is separated,
and the data model it came from is replaced. Not a workaround: no reader is
patched to tolerate a symptom.

## Fix

Per [ADR-0046](../decisions/adr-0046-adr-status-frontmatter-authority.md):

1. **Gate on the classified state, not on prose formatting.** New
   `_adr_status()` reads the frontmatter `status:` field first and falls back
   to the lenient prose classifier for legacy ADRs. `cmd_accept` refuses only
   when the state is not `Proposed`, and the refusal names the state it
   found (`already Accepted`, `Superseded`, or `state: <X>`).
2. **Flip frontmatter unconditionally**, in the same single atomic write as
   before.
3. **Rewrite the prose line only when canonical.** A decorated line is left
   byte-identical and `accept` emits a note on stderr naming the file, the
   surviving line, and the value the prose should carry.
4. **Every reader is frontmatter-first** (the cost of allowing divergence):
   `cmd_supersede`'s gate and `_extract_status_and_date` (which drives the
   README index and `resolve-todo`'s Accepted check) now read frontmatter
   first, prose as the legacy fallback.
5. **`supersede` still requires a canonical `Accepted (date)` anchor**, since
   it *inserts* a load-bearing `Superseded by …` link rather than rewriting a
   line. It refuses with an actionable message, before either file is
   written, and the gate covers **both** ADRs.
6. **The misleading comment is corrected** and now explains why the pattern
   stays strict and that it is not the gate.
7. **A diverged ADR publishes no date** in the README index. The prose date
   belongs to the stale state, and there is deliberately no substitute:
   `last_verified` is a freshness field, not an acceptance date (see
   `## Already tried`). `supersede`'s refusal names the `git log` invocation
   that recovers the acceptance date from the accept commit instead.

## Already tried

Nothing discarded from the diagnosis — the two rejected shapes (loosen the
regex; keep the strict gate and only improve the message) are recorded as
Options B and A in ADR-0046, with the maintainer's ruling on the issue thread.

**One attempted mitigation was tried and withdrawn.** To bound the residual
that frame-critique round 1 surfaced (an ADR accepted with decorated prose
never gains a canonical `Accepted (date)` line, so `supersede` later refuses
and the acceptance date is no longer in the prose), `_no_anchor_message` was
changed to report frontmatter `last_verified` as the acceptance date, and
`_extract_status_and_date` to publish it in the index for the diverged case.

Round 2 refuted it: `last_verified` is a *freshness* field, not an acceptance
date. ADR-0024's `reaffirm` disposition refreshes it (a judgment step, so no
code path to grep), `workflow.py`'s staleness check reads it as "verified N
days ago", and eight prose-`Proposed` ADRs in this corpus already carry a
filled value. The mitigation would have published a plausible wrong date in
`docs/decisions/README.md` and invited a false acceptance date into an
immutable record — worse than the reconstruction it replaced.

Withdrawn in favour of publishing **no** date for a diverged ADR and pointing
`supersede`'s refusal at the accept commit. The reasoning error is recorded in
`## Learning`.

## Regression test

`skills/adr-workflow/test_adr.py::NonCanonicalProseStatusTests` — 18 cases
covering the reported repro (legacy and frontmatter-canonical shapes), the
unconditional frontmatter flip, byte-identical prose preservation, the
stderr note, stdout staying machine-readable, state-named refusals, the
frontmatter-first index / `resolve-todo` / `supersede` gates, the
missing-anchor refusal being atomic **on both ADRs**, the diverged index
entry publishing no date, the refusal pointing at the accept commit rather
than at metadata, and a blank-but-present `status:` falling through to the
prose classifier.

`WriterStampsFrontmatterStatusTests`' two ADR-0026 sync-lock cases are
narrowed to the canonical-prose case they still hold for.

Four of these cases exist because a review pass proved the assertion they
replaced could not fail: the original supersede-anchor test asserted only
exit 2 plus the literal `"Status"`, both of which the *pre-fix* code also
produced (via `_classify_status` → `Unknown`), so ruling 5 was unguarded.
The new-ADR anchor branch and the blank-`status:` fallthrough were likewise
mutation-verified: stubbing either now fails the suite.

## Proof

- **Red:** 11 of the 15 new cases failed against unmodified `adr.py`
  (`Ran 146 tests … FAILED (failures=11)`). The 4 that passed did so
  vacuously — `accept` refused, so the file was trivially unmodified.
- **Green:** `Ran 146 tests in 4.9s — OK` after the fix.
- **No regressions:** full suite `Ran 3512 tests in 115s — OK (skipped=4)`.
  The suite's host-package drift step reports
  `hosts/claude/.claude-plugin/plugin.json` stale; that is
  [bug 008](008-flaky-host-package-drift-guard.md), pre-existing and
  unrelated — a fresh build of that file is byte-identical to the committed
  one.

## Learning

A regex that both *gates* and *transforms* will export the transform's
strictness into the gate, where it reads as an arbitrary format rule. When
one pattern serves both roles, the tolerant read and the exact rewrite want
different patterns — and a comment claiming otherwise is a sign the two roles
were never separated.

Two more, both earned during the fix rather than during the diagnosis:

**A field's meaning lives in its readers, not its writers.** Needing an
acceptance date, the fix grepped for who writes `last_verified`, found only
`cmd_accept`, and concluded the field *is* the acceptance date. The grep
answered "who writes this?" while the question was "what does this mean?" —
and the answer lives in the field's defining ADR and in what reads it
(ADR-0024's `reaffirm` refreshes it; `workflow.py` reads it as freshness).
Corollary: **a plausible wrong value is worse than an absent one**, because
nothing about it looks wrong.

**Run the remediation command you print.** The refusal told the operator to
recover the date with `git log … -- <basename>`; git resolves pathspecs
relative to cwd, so from a repo root it matched nothing and exited 0 — output
indistinguishable from "no such commit exists". An error message is a
deliverable, and an unexecuted one is an untested code path with a human on
the other end.

Full detail in [docs/memory/learnings.md](../memory/learnings.md).

## Main recheck

- 2026-07-27 - `fd7115a` -> reproduces: adr.py accept 0004 on a Status line 'Proposed (2026-07-22) — awaiting owner acceptance.' exits 2 against a clean origin/main export; message never names the trailing clause
