---
adr: 0046
pass: frame-critique
verdict: pass
reviewer: jig:reviewer subagent (fresh context per round, read-only) — 4 rounds
reviewed_at: 2026-07-30T02:07:03Z
prompt_source: review.py frame-critique docs/decisions/adr-0046-adr-status-frontmatter-authority.md
---

Adversarial frame-critique on ADR-0046, **four rounds**, each a fresh
read-only `jig:reviewer` subagent. Rounds 1–3 returned `needs-changes` and
every finding was verified against the code or the corpus before being
acted on. Round 4 returned **pass**.

## Round 1 — the ruling-2 / ruling-5 trap

Found that the ADR claimed Option D delivers flexible prose, but rulings 2
and 5 compose: `accept` leaves a decorated line untouched, so the ADR never
gains a canonical `Accepted (date)` line, and `supersede` then hard-refuses
for want of that anchor. **The hand-edit Option C was rejected for is
deferred, not eliminated** — and to a worse moment, since the acceptance date
has left the prose. Also: the flexible-prose promise was stated
unconditionally though it only holds for frontmatter-bearing ADRs, and no
kill criterion could fire on the block.

*Response:* residual stated in "Why not Option C"; Consequences bullet;
kill criterion with a named observer; promise scoped; two Open questions.

## Round 2 — the mitigation was refuted

Round 1's mitigation (report frontmatter `last_verified` as the acceptance
date) was **wrong on the facts**. `last_verified` is a *freshness* field:
ADR-0024's `reaffirm` disposition refreshes it, `workflow.py`'s staleness
check reads it as "verified N days ago", and eight prose-`Proposed` ADRs in
this corpus already carry a filled value. The mitigation would have published
a plausible wrong date in the README index and invited a false acceptance
date into an immutable record — worse than the reconstruction it replaced.

*Response:* the claim was **removed, not defended**. The index now publishes
no date for a diverged ADR; the refusal points at the accept commit.

*Mechanism of the error, recorded:* round 1 established the field's
*provenance* (only `cmd_accept` writes it in code) and treated that as its
*semantics*. A field's contract lives in its defining ADR and in its readers,
not in its writers.

## Round 3 — four findings, all verified

1. **The printed `git log` recovery command did not work.** A bare basename
   pathspec resolves relative to cwd, so from a repo root it matched nothing
   and returned empty output — reading as "there is no accept commit".
   `--diff-filter=M` additionally excluded squash-merged create+accept.
2. **The "four lenient readers" assumption is `Proposed`-only.**
   `_STATUS_ACCEPTED_RE` is anchored, so a decorated `Accepted` line
   classifies `Unknown`; a legacy no-frontmatter ADR therefore refuses
   through `not Accepted (got Unknown)`, never reaching ruling 5's message.
3. **Ruling 2's benefit was over-stated.** The pre-fix gate was a `search`
   over the whole `## Status` body, so a canonical first line plus free prose
   below it already passed. What ruling 2 newly unlocks is only same-line
   trailing text and an unparseable first line.
4. **The kill criteria had no observer.** All 41 live ADRs carry a canonical
   first Status line and `adr.py new` emits one, so the divergence cannot
   arise in this repo. Its home is downstream scaffolds, which jig cannot
   see.

*Response:* command fixed and verified working; Assumptions corrected;
narrowed benefit stated in Consequences; observers restated as "a downstream
report" with the missing durable trace named.

## Round 4 — pass

Verified every load-bearing claim about `adr.py` independently: the
frontmatter-first classifier, the state-based accept gate, the no-date
divergence path and the renderer omitting it, both ruling-5 refusals firing
before either write ("Neither ADR was modified" is true), the printed
recovery command's search string matching what the writer emits, the
anchored-`Accepted` correction, and the corpus claims (41 ADRs, all
canonical; only 073-01/073-02, both DONE, depend on ADR-0026).

Verdict reasoning: the frame is candid where it matters — the deferred
hand-edit, the lost machine-readable acceptance date, the ruling-2/ruling-5
trap, the narrowed benefit, the downstream-only observer and the standing
Option-C challenge are stated rather than buried, and the kill criteria name
both their observers and those observers' limits.

Two wording residuals were logged as not worth a fifth round. Both were
closed anyway, since an over-claiming comment is what filed this bug:
- "`accept` refuses for exactly one reason" was literally untrue (the
  frame-critique gate, a missing `## Status` heading and an ambiguous number
  all still refuse) — now scoped to the status gate.
- Ruling 2's "never half-rewritten" is guaranteed only for a section holding
  no canonical line; the `.search` mechanism would rewrite a canonical line
  sitting *below* a decorated one. Contrived and unreachable via `adr.py
  new`, but the guarantee is now stated precisely.

## The standing challenge — NOT resolved by this pass

Rounds 1 and 3 both argued Option C is cheaper on the ADR's own accounting.
That argument is recorded verbatim in the ADR as a standing challenge for the
maintainer, with the cost of switching (one superseding ADR; rulings 1, 3, 4
and 5 survive unchanged, only ruling 2 flips). It was deliberately **not**
adopted: the maintainer ruled for Option D explicitly on the issue thread and
approved this ADR on [PR #139](https://github.com/ramboz/jig/pull/139)
(*"I approve ADR-0039"* — this record, drafted under that number; see its
numbering note), and reversing that mid-implementation is not the
implementer's call. This pass certifies the record is honest about the
trade — not that the trade is the right one.

**The approval predates the last three rounds of this critique.** It was
given while the ADR still claimed the flexible-prose benefit unconditionally,
still carried the `last_verified`-as-acceptance-date mitigation, and did not
yet contain the standing Option-C challenge. Nothing in the *decision* moved —
Option D and all five rulings stand as approved — but the accounting around it
did, and the maintainer has not seen that version. Flag it on the PR rather
than treating the original approval as covering the amended record.
