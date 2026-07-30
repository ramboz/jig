---
adr: 0044
pass: frame-critique
verdict: needs-changes
reviewer: jig:reviewer subagent (2 rounds)
reviewed_at: 2026-07-27T17:33:32Z
prompt_source: review.py frame-critique docs/decisions/adr-0044-lifecycle-entry-gate.md
---

Two adversarial rounds against ADR-0044 + spec 098. Both returned
`needs-changes`. Every finding below was independently re-probed against the
tree before being accepted.

## Round 1 (2026-07-27) — needs-changes

1. **Presence is not liveness.** The draft read "inside the lifecycle" as *any*
   `IN_PROGRESS` slice or open bug record existing on the branch. Falsified on
   jig's own `main`: slice 088-02 is `IN_PROGRESS` and bug 008 is `REPORTED`
   (open per `bug.py OPEN_STATUSES`). The gate would have been **permanently
   silent on this repository**, and on any project whose board is not perfectly
   clean — the common case, not the corner case.
2. **`docs_root: "."` collapses the source boundary.** `project_layout.docs_base`
   returns the project directory itself when `docs_root == "."`, so a boundary
   phrased as "anything under `docs_root`" classifies the whole repo as lifecycle
   artifacts. The draft listed that outcome as a *passing* test.
3. **Bash-written edits never reach the trigger.** The hook sees
   `Edit|Write|MultiEdit` only; `sed -i` / heredoc writes bypass it. #111 counts
   incidents, not the tool that produced them, so coverage is unknown.

Revised: liveness via `.jig/spec-ref` + slice-status cross-check; boundary (b)
narrowed to named artifact subtrees; Bash limit recorded; under-fire kill
criterion added.

## Round 2 (2026-07-27) — needs-changes

The round-1 fix removed a permanent false negative and installed a systematic
false positive. All four findings re-verified:

4. **The claim is destroyed mid-lifecycle.** `workflow.py`
   `_CLAIM_CLEARING_STATUSES = ("REVIEWED", "READY_FOR_IMPLEMENTATION", "DRAFT")`
   — the claim clears and the slice leaves `IN_PROGRESS` at REVIEWED, while
   `docs/workflow.md` step 7 puts **reconciliation after** that transition
   (updating `architecture.md`, `CLAUDE.md`, `roadmap.md` — all tracked, none
   under the artifact subtrees, therefore "source"). The gate would fire **once
   per slice, on every slice**, at the reconciliation step, telling the agent to
   claim a slice while it executes the mandated final step of one. AC5's
   "re-arm on lifecycle state change" guarantees the re-arm lands exactly there.
5. **The bug arm has no live signal.** `bug.py new_bug(push=True)` calls
   `reserve_bug_on_origin` and returns `None` — the record exists only on
   `origin/main`, nothing in the working tree — and `bug.py` never writes
   `.jig/spec-ref`. A bug fix opened the prescribed way is invisible to both
   arms of the detection rule.
6. **"Operator identity" does not exist.** `_claim_identifier` (both
   `workflow.py` and `bug.py`) resolves `JIG_CLAIM_ID` or the **branch name**,
   falling back to the literal `"detached"` — with the explicit spec 049
   non-goal "no human-identity inference." So: a bug reported on `main` and
   fixed on a task branch can never match; `claimed_by: detached` is the
   function's return value, not (as round 1's revision asserted) a stale
   artifact; two agents on same-named branches match each other.
7. **Session scoping is unprobed.** `jig-context-check.sh` keys its once-per-
   session state on `payload.session_id or 'default'`, not on `$TMPDIR` alone.
   If the `PostToolUse` payload carries no `session_id`, every session shares
   the `default` key and a single fire silences the gate until `$TMPDIR` clears
   — a silent death the 8-week under-fire criterion cannot distinguish from
   success.
8. **The anti-dead-gate tests are one-directional** — they assert the gate
   fires when nothing is live, never that it stays silent during reconciliation,
   during a bug fix, or after a `--push` bug reservation.

## Disposition

Findings 1, 2, 3 are fixed in the artifacts. Findings 4, 5, 6, 7, 8 are recorded
as open: 6 is corrected as a matter of fact (the ADR asserted something untrue
about the code), and 4/5/7/8 are carried into **open question #5** — jig has no
signal today that means "this session is inside the lifecycle," and inventing
one is a decision for the maintainer, not for this revision.

**ADR-0044 therefore stays `Proposed`.** It cannot pass its own accept gate, and
should not: the frame critique did precisely its job, twice.

## Amendments

<!-- ADR-0010: this is a closed review record. Its findings are preserved as
     written; what happened to them afterwards is appended here, never edited
     into the prose above. -->

- **2026-07-30 — the record was renumbered from ADR-0040 to ADR-0044.** 0040 was
  taken on `main` on 2026-07-27 by an unrelated reservation. Every "ADR-0040"
  above refers to what is now
  [ADR-0044](../adr-0044-lifecycle-entry-gate.md); the findings themselves are
  unchanged.
- **2026-07-30 — the disposition above is superseded; the ADR is now Accepted.**
  The maintainer answered question #5 on
  [#128](https://github.com/ramboz/jig/pull/128): *"Yes, let's do #138 first, and
  just address the remaining gap here."* Against the findings carried into that
  question:
  - **4, 5** (no signal spans the working lifecycle; claim-based rules fire
    during reconciliation) — closed by depending on
    [#138](https://github.com/ramboz/jig/pull/138), which makes the claim span
    `READY_FOR_REVIEW` → `RECONCILED`.
  - **7** (session scoping unprobed) — **probed 2026-07-30 and present.** The
    `PostToolUse` payload carries a real `session_id`: `jig-decision-inflight.sh`
    wrote `.jig/decision-scratch/411b8c7a-4d9e-45d7-be01-5b4fab17d725.log`,
    keyed on the host's session UUID rather than the `default` fallback.
    Claude host only; Codex is 098-02's to re-probe.
  - **8** (anti-dead-gate tests one-directional) — closed in slice 098-01, which
    now carries anti-false-fire tests for reconciliation and for a bug fix, plus
    anti-stale-marker and foreign-claim cases.
  - **6** (the `claimed_by: detached` misreading) — remains corrected in the ADR;
    the identity question is answered as *branch scoping*, not operator identity,
    preserving spec 049's non-goal.
  - The bug arm, which no finding could close and #138 does not touch, becomes
    slice 098-04.
