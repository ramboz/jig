---
status: DRAFT
dependencies: [adr-0044]
last_verified: 2026-07-30
frame_review: false
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about runnable
     surfaces by probe first (run it / read source) or a citation, else mark them
     as assumptions — never assert an unverified claim as fact. -->

## Slice 098-04 — bug-lifecycle claim marker

**Goal:** A bug fix opened the way `bug-fix/SKILL.md` prescribes leaves the same
working-tree lifecycle marker a spec slice does, so anything asking "is this
session inside jig?" reads **one** signal instead of two — and gets the right
answer for bugs, which today it cannot get at all.

**Scope:** `skills/bug-fix/bug.py` and the marker's readers. No hook work: slice
098-01 is the consumer, and it is a separate slice.

**Why this exists.** Settled call #5(a). The entry gate must stay silent while
the agent is legitimately fixing a bug, and today nothing in the working tree
says that is happening:

- `bug.py new_bug(project_dir, slug, push=True)` calls `reserve_bug_on_origin`
  and **returns `None`** — the record is committed to `origin/main`; the working
  tree gets nothing (`skills/bug-fix/bug.py`, `new_bug`).
- `bug.py` never writes `.jig/spec-ref`. Grepping the file for `spec-ref` /
  `spec_ref` returns nothing; only `workflow.py` stamps it, and only under
  `if new_status == IN_PROGRESS_STATUS` (`_write_spec_ref_marker`, slice 056-03).

So the bug arm of the gate has no local signal whatsoever. That is not a gate
bug to be worked around in the hook — it is a missing piece of the bug
lifecycle, and it belongs in `bug.py`.

**DoR:**
- ✅ [ADR-0044](../../decisions/adr-0044-lifecycle-entry-gate.md) is Accepted;
  settled call #5(a) names this slice as the fix.
- ✅ The spec-side marker exists and its writer is identified:
  `workflow.py._write_spec_ref_marker` → `<project-root>/.jig/spec-ref`
  (slice 056-03), working-tree-local and git-ignored.
- ✅ The readers are enumerable: `lib/read_attribution.read_spec_ref`,
  `_common/gate_telemetry` (`read_spec_ref`, used by `emit_gate_bypass`), and
  `scripts/usage.py`. The compatibility constraint below is written against
  these three.
- ✅ The claim machinery is shared: `bug.py pickup <id>` already reuses the spec
  049 claim/release mechanism (`bug-fix/SKILL.md` §1).
- ⚠️ Independent of [#138](https://github.com/ramboz/jig/pull/138). This slice
  touches `bug.py`; #138 touches `workflow.py`. They can proceed in parallel,
  but 098-01 needs both.

**Acceptance criteria:**

1. **Stamp on local entry.** `bug.py pickup <id>` writes the working-tree
   lifecycle marker naming the bug record it just claimed. `pickup` is the right
   hook point because it is the step that runs *in the working tree* and is
   already the documented claim step — including in the `--push` flow, where the
   record itself originated on `origin/main`.
2. **Stamp on transition into a working status.** `bug.py transition <id>
   <status>` re-stamps for statuses that mean work is underway — `OPEN_STATUSES`
   minus `REPORTED`, i.e. `DIAGNOSING` / `ROOT_CAUSED` / `FIXING` / `REVIEWED` /
   `VERIFIED` — so a session that resumes an already-claimed bug without
   re-running `pickup` is still inside. Derive the set from the existing
   `OPEN_STATUSES` constant rather than re-listing it, and pin the derivation by
   test, so a future status added to the lifecycle cannot silently fall outside
   the gate's notion of "working". `REPORTED` is deliberately excluded — a bug
   can sit reported for weeks with nobody on it; AC1's `pickup` is what marks
   entry.
   Mirror `workflow.py`'s ordering: stamp **after** the status write succeeds,
   never before.
3. **Backwards compatibility is a hard requirement.** The three existing readers
   (`read_attribution.read_spec_ref`, `_common/gate_telemetry`,
   `scripts/usage.py`) must keep returning today's values for today's
   spec-shaped marker content, byte for byte. A bug-shaped marker must be
   distinguishable from a spec-shaped one by the reader, and must not be
   mistaken for a spec reference by any of the three. **Extend, do not
   repurpose** — if that cannot be done cleanly in `.jig/spec-ref`, write a
   sibling marker file and say so in the deviation log; do not silently widen
   the existing format.
4. **Best-effort, never blocking.** A failed marker write never fails `pickup`
   or `transition` — same posture as `_write_spec_ref_marker`, which is
   deliberately side-effect-isolated so a marker failure cannot block a lifecycle
   transition or its gates.
5. **Released claims clear it.** `bug.py pickup <id> --release --reason "…"`
   removes the marker for that bug: releasing a claim means the session is no
   longer inside that work item.
6. **Terminal statuses clear it.** A transition to a status that ends the work
   (`DONE`, and the resolution paths `RESOLVED_ON_MAIN` / `ESCALATED`) clears the
   marker. Without this the marker outlives the work and the consumer has to
   compensate — the same staleness `workflow.py` currently leaves behind and
   which 098-01 has to cross-check its way around.
7. **Documented.** `bug-fix/SKILL.md` states that `pickup` stamps the marker and
   that this is what tells jig's gates a bug fix is in flight — one sentence, in
   the §1 claim/release paragraph that already exists.

**Tests first (TDD):**
- `pickup` on a local bug record → marker present, names that bug.
- `pickup` after a `--push` reservation (record fetched from `origin/main`,
  nothing written locally by `new_bug`) → marker present. This is the case the
  gate exists for.
- `transition` into each working status with no prior `pickup` → marker present.
- **the working set is derived, not hard-coded:** the statuses that stamp are
  exactly `OPEN_STATUSES - {"REPORTED"}` (AC2), asserted against the constant so
  a newly added status cannot quietly drop out of the gate's coverage.
- `pickup --release` → marker gone.
- transition to `DONE` / `RESOLVED_ON_MAIN` / `ESCALATED` → marker gone.
- **compatibility:** a spec-shaped marker written by `workflow.py` is read
  identically by `read_attribution.read_spec_ref`, `gate_telemetry` and
  `scripts/usage.py` before and after this slice — assert on the returned
  values, not on "it didn't crash".
- **no cross-talk:** a bug-shaped marker is not returned as a spec reference by
  any of the three readers.
- marker write fails (unwritable `.jig/`) → `pickup` and `transition` still
  succeed, exit 0, status written.
- transition ordering: a *failed* status write leaves no marker behind.

**DoD:**
- [ ] All acceptance criteria met, tests green (red→green witnessed).
- [ ] The three readers exercised directly, not assumed (AC3).
- [ ] `bug-fix/SKILL.md` updated (AC7).
- [ ] Post-impl review (compliance + craft).
- [ ] Deviation log written; reconciliation review.
- [ ] If AC3 forced a sibling marker file rather than extending `.jig/spec-ref`,
      that choice and its reason are in the deviation log, and slice 098-01's
      AC2 is updated to name the file it actually reads.
