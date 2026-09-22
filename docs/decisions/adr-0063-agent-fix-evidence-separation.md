---
status: Proposed
dependencies: [adr-0014, adr-0016, adr-0050, adr-0051, adr-0060]
last_verified: 2026-09-22
frame_review: true
---

# ADR-0063: Agent-proposed fixes never green-wash failing evidence

## Status

Proposed (2026-09-22)

## Context

jig's bug-fix lifecycle ([ADR-0016](./adr-0016-bug-fix-lifecycle.md)) has
teeth around the *fix*: a diagnose-before-fix gate and a witnessed red→green
regression test — the test must be seen failing before the fix and passing
after. The autonomy bridge adds a bound on *retrying* a fix
([ADR-0050](./adr-0050-durable-failure-quarantine.md), quarantine after N
attempts), a governance plane and identity separation
([ADR-0051](./adr-0051-autonomy-governance-plane.md)), and a per-execution-mode
write boundary ([ADR-0060](./adr-0060-unattended-execution-write-boundary.md)).

None of those records states what an agent-proposed fix may do to the
**failing evidence itself**. Today the red witness, the diagnosis, and the fix
all live on the same branch under the same principal. An attended developer
would not rewrite the failure to make it pass; an unattended loop under retry
pressure will, in the ways every steward rule set has to forbid by hand: edit
the assertion, skip or quarantine the test, re-run until a flaky check goes
green and record that as the pass, or overwrite the red witness with a green
one. The bug record's evidence gate (`_diagnosis_gaps`, the red→green teeth)
checks that evidence *exists*; it does not check that the evidence was not
*replaced*.

[R-001](../research/R-001-cloudflare-adlc-assessment.md) records the prior
art that names the invariant cleanly. Cloudflare's self-healing CI example
pushes a verified fix to a separate `ci-autofix/<run-id>` branch and **the
source run still fails** (`CiRunFailedWithFix`) "because its original revision
remains broken"; a human merges the fix. The ADLC post itself frames the bar
the same way: "why haven't you yet just let your agent auto-approve and merge
its own PRs to your production services? The higher the stakes … the longer
your list of reasons almost surely is." Their Astro issue factory (verified
from the post's full text) runs each of its four stages — reproduce,
diagnose, verify-it-is-a-bug, fix — in an *isolated* subagent "to prevent the
frequent LLM bias toward forcing a solution when a bug might not actually
exist," and its fix stage converts the reproduction into failing unit tests
first. A landed fix ships as a *preview release* posted back to the issue with
full logs; only when "the original reporter can then try the patch against
their own project, and if they confirm it works" does "the automation open[]
a pull request linked to the issue," which a maintainer merges. Both keep
the failure record and the proposed fix as separate artifacts with separate
provenance, and both make a human merge the only way the failure turns green;
Astro adds a reporter checkpoint before the maintainer's.

This ADR fixes that invariant for jig. It is distinct from ADR-0050 (which
bounds *how many times* a fix is attempted) and ADR-0060 (which gates *where an
unattended run may write*): it governs the **integrity of the evidence** a fix
is judged against, in attended and unattended runs alike.

## Decision Options Considered

### Option A: Status quo — red→green witness plus review
- **Pros:** No new rule; the witness and the reviewer already catch the crude cases in attended runs.
- **Cons:** The witness lives on the fix branch and is rewritable by the same principal; nothing says the original failure must remain on record; the reviewer sees the green state, not the history; an unattended loop under ADR-0050's retry budget is exactly the actor that will "fix" the test.

### Option B: Evidence-separation invariant (recommended)
- **Pros:** Small, statable, and checkable: a fix is a separate ref from the failure it addresses, the failure record stays red until a human merge (or an ADR-0060 executor-level attestation) resolves it, "green" is a fresh run on the fix revision recorded as *new* evidence, and any fix that modifies the test or oracle is flagged as evidence-modifying for owner review. Reuses the bug record (attempt evidence appends, never overwrites), the existing VERIFIED state (reporter or owner confirmation), and the spec 105 freeze semantics.
- **Cons:** One more rule to state in the governance doc and bug-fix skill; an evidence-modifying fix (a genuinely wrong test) needs an explicit owner path so the rule does not block legitimate test corrections; branch hygiene (a `fix/` ref per attempt) adds refs to clean up.

### Option C: Auto-merge a fix once it passes on the fix revision
- **Pros:** Fastest loop; no human wait.
- **Cons:** Collapses the two principals ADR-0051 separates — the agent's own green run would be the approval; a flaky or tampered check becomes a merge. Cloudflare's own example deliberately does *not* do this. Rejected.

### Option D: Reporter-verifies-patch as the primary gate
- **Pros:** Strong human-in-the-loop signal where a reporter exists (Astro's flow: preview release → reporter confirms → PR opens → maintainer merges).
- **Cons:** Not every bug has an external reporter; it is a confirmation step, not an evidence rule, and Astro itself still has a maintainer merge behind it. Folded into B as a use of the existing VERIFIED state, not adopted as the mechanism.

## Recommended Decision

Adopt **Option B**. The invariant, in four clauses:

1. **Separate ref.** An agent-proposed fix lands on its own ref
   (`fix/<bug-id>` for bug-fix work; a `ci-autofix/<run-id>` shape for a
   CI-originated failure) and never rewrites the failing revision, the red
   witness, or the diagnosis evidence. Each attempt appends to the bug record
   (`attempts:` per ADR-0050); it never overwrites a prior attempt's evidence.
2. **Failure stays red until a human merges.** The failing record — the red
   CI run, the witnessed failing test, the bug record's diagnosis — remains
   red/frozen until a human merges the fix. In an unattended run the only
   substitute is the executor-level enforcer ADR-0060 names, attesting the
   merge; the loop itself can never turn its own failure green.
3. **Green is new evidence on the fix revision.** The passing run is a fresh
   execution on the fix ref, recorded as a new evidence artifact beside the
   red one. A re-run of the *failing* revision that happens to pass is a flake
   signal, not a fix, and is recorded as such.
4. **Evidence-modifying fixes are flagged.** A fix that edits the regression
   test, its assertions, its oracle, or skips/quarantines/disables a check is
   marked evidence-modifying and requires owner review before merge. This is
   the "never skip, disable, or quarantine a test to get green" rule given a
   home; a genuinely wrong test is corrected through that owner path, not
   silently.

Where it lands: the scaffolded `<docs>/governance.md` (the invariant as a
stated rule beside the identity-separation section), the `bug-fix` skill (fix
ref + append-only evidence wording), and a cross-link from spec 105 so the
quarantine freeze and this freeze are the same semantics. Spec 115 slice 02
carries the build.

## Consequences

**Becomes easier:**
- An unattended fix loop cannot manufacture its own green: the worst it can do
  is propose, and the proposal is auditable against an intact failure record.
- The bug record becomes a history of attempts rather than the last attempt's
  story, which is what a human recovering a quarantined bug needs.
- Steward-style rule sets ("never skip a test to get green") get a governing
  record instead of living only in per-tool prompts.

**Becomes harder:**
- More refs and more evidence artifacts per bug; cleanup after merge is real
  work.
- Legitimate test corrections take an explicit owner step, which is friction
  by design.
- The unattended substitute for a human merge depends on ADR-0060's
  executor-level attestation, which is not built; until it is, clause 2 means
  an unattended fix simply waits.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **Verified (probed 2026-09-22):** `bug-fix` witnesses red→green on one
  branch and the evidence gate checks for the presence of evidence pointers;
  spec 105 / ADR-0050 already specify freezing the evidence sections on
  quarantine, so clause 1's append-only semantics have a precedent to reuse.
- **Verified:** the `ci-autofix/<run-id>` / `CiRunFailedWithFix` mechanics
  are read from the cloudflare/ci repository README and example (the primary
  source for them); the ADLC post's own text (verified 2026-09-22) confirms
  `@cloudflare/ci` "can self-heal" and supplies the auto-merge framing quoted
  above. The Astro flow (isolated per-stage subagents, failing-test-first
  fix, preview release, reporter confirmation before the PR opens) is read
  from that post's full text (supplied by the owner 2026-09-22).
- **Unverified, load-bearing for clause 4:** that "evidence-modifying" can be
  detected mechanically enough to flag (a diff touching the regression test
  path or a skip marker) — slice 115-02 must probe the detection surface
  before promising it as a gate rather than a nudge.

## Kill criteria

- No jig run is ever executed unattended and attended reviewers report the
  rule as pure friction → demote clauses 1–3 to guidance and keep only
  clause 4.
- Clause 4's detection produces more false flags than real catches over a
  meaningful sample → drop the mechanical flag, keep the rule as reviewer
  guidance.
- ADR-0060 is shelved (no executor-level enforcer ever exists) → clause 2's
  unattended substitute is moot; the rule collapses to "a human merges",
  which still stands.

## Open questions

- Is the fix ref per *attempt* or per *bug*? Per-bug keeps refs few; per-attempt
  keeps each attempt's green run attributable. Lean per-bug with per-attempt
  evidence artifacts, decide in the slice.
- Should the VERIFIED state be *required* when a reporter exists (Astro's
  reporter-confirms step), or remain the optional path it is today?
- Does slice-land's readiness check need to assert clause 3 (the recorded
  green is on the landing revision) for bug-shaped landings, or is the
  review-evidence gate sufficient?
