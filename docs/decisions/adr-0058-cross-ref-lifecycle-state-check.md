---
status: Accepted
dependencies: [docs/decisions/adr-0048-session-git-freshness-fetch-and-nudge.md, docs/decisions/adr-0053-reservation-numbering-sees-in-flight-branches.md, docs/decisions/adr-0044-lifecycle-entry-gate.md, docs/decisions/adr-0045-slice-claim-covers-active-lifecycle.md]
last_verified: 2026-08-27
frame_review: true
---

# ADR-0058: Ref-aware lifecycle checks and claim-based work reservation

## Status

Accepted (2026-08-27)

<!-- History: briefly Accepted 2026-08-27 then reverted to Proposed the same
     session, by explicit owner grant, to revise the decision before any
     implementation — the un-integrated case moved from "advisory-only" to
     "coordinated by claim reservation." Nothing was built against the accepted
     version. Re-accepted after a fresh frame-critique pass. -->


## Context

A session rebuilt an already-finished slice from scratch — a duplicate
implementation and a duplicate ADR — because it trusted a stale on-disk marker
over a durable record that named the real work.

The reported chain: slice `003-02` was already `DONE`, landed on a sibling
branch at a specific commit, with its ADR `Accepted`. The session's own memory
recorded that correctly at time zero ("003-02 DONE, merged to `<commit>`, ADR
accepted"). But the slice file *in the session's checkout* still read `DRAFT`,
because that checkout's branch did not contain the sibling commit. The session
read the `DRAFT` marker, believed it, and built a second `003-02` + a second
ADR on a fresh branch — never checking the branch its own memory named. The
"ready to archive" gate then said GO, because the duplicate *was* self-
consistently committed; and the session overwrote the memory pointer that named
the authoritative commit, corrupting the record for the next session.

Investigation of the current helpers shows this is not an edge case that slipped
one guard — **every lifecycle check in jig trusts the current checkout as the
whole truth**, and each is blind to sibling refs holding a more-advanced state
of the same identifier:

- **Status reads** — `workflow.py` `_slice_status_from_section` /
  `collect_slices` / `compute_spec_status` read the marker from the file in the
  current checkout only. Nothing compares it to memory or another ref.
- **Reconciliation** (`spec-workflow/SKILL.md` REVIEWED→RECONCILED checklist)
  validates local artifacts — status board, deviation log, docs. It never diffs
  the marker against another ref or against memory.
- **Session git-freshness** ([ADR-0048](./adr-0048-session-git-freshness-fetch-and-nudge.md))
  watches **exactly one** ref — the integration base — and its own-remote guard
  deliberately *excludes* the branch's own remote. It reports a behind-count; it
  reads no slice/ADR identifier state and watches no sibling feature branch.
- **Lifecycle-entry-gate** ([ADR-0044](./adr-0044-lifecycle-entry-gate.md)) and
  **slice-claim** (spec 049) read local files only; slice-claim's own docstring
  admits an unpushed sibling claim is invisible.
- **`new` / reservation** ([ADR-0053](./adr-0053-reservation-numbering-sees-in-flight-branches.md))
  is the one helper that already enumerates **every** local and remote ref
  (`for-each-ref` + `ls-tree`) — but it reads filenames for the next free
  *number*. It never reads the *state* of the identifier it is about to reuse.
- **Land gate** (`land.py` `prepare`) blocks on four self-consistency checks
  (STATUS=DONE, tests not red, deviation log present, DoD ticked). None asks
  whether the work already exists on the base or a sibling ref.

The incident's exact signature — `disk=DRAFT`, `memory=DONE`, work landed on a
sibling commit — falls through all of them. The corrupted memory is a symptom,
not the disease: the authoritative "landed at `<commit>`" pointer only ever
lived in prose session/Scout memory, because **jig keeps no ref-committed record
of where a slice or ADR actually landed**. Memory was the single copy of that
truth, which is why overwriting it was catastrophic.

## Decision Options Considered

### Option A: Guard the memory write path

Make memory writes conflict-aware — refuse to overwrite a pointer naming commit
X as authoritative with a different commit Y.

- **Pros:** Directly targets the visible corruption step.
- **Cons:** Wrong layer. The authoritative pointer never lived in jig-native
  memory (`memory.py` is prose-only, append-only, and *skips* on a duplicate
  heading rather than overwriting). The overwrite happened in session/Scout
  memory, outside this repo's reach. Even a perfect guard here would not have
  stopped the duplicate *build*, which is the actual harm — it fires far
  downstream of the root read. Protects a copy, not the truth.

### Option B: Ref-aware lifecycle-state check (recommended)

Introduce one shared primitive: for a given slice/ADR identifier, read its
lifecycle state across sibling and remote refs and detect when another ref holds
it at a **strictly more-advanced** state than the current checkout. Reuse the
ref-enumeration plumbing ADR-0053 already built; teach it to read the STATUS
marker per ref rather than only the filename. Wire the primitive at the points
where a stale premise forms or turns into duplicate work.

- **Pros:** Attacks the root — "checkout is not the whole truth" — with one
  reusable check rather than six point-patches. Reuses the ref-scan machinery
  ADR-0053 built for enumeration. Surfaces a stale marker (advisorily) before it
  is believed, and hard-blocks the integrated-duplication case at create/land —
  the split of what it can gate vs only surface is settled in Recommended
  Decision.
- **Cons:** Adds git calls to hot paths (mitigated: timeout-guarded /
  best-effort, matching the existing git-freshness contract). Extends ADR-0048's
  deliberately single-base semantics to sibling refs — a real scope change that
  must be bounded. Cross-ref matching must handle a renamed slug for the same
  identifier. **Crucially, the *signal* must be chosen carefully** (see
  Recommended Decision): a raw "some ref holds a more-advanced marker" reading is
  unreliable — ADR-0053 records that abandoned / spike / reverted branches
  persist on `origin`, so raw state cannot tell authoritative done-work from a
  dead branch that happened to reach `DONE`. And the ref-scan reuse is a genuine
  extension, not free: ADR-0053's scan reads `--name-only` filenames, whereas
  reading a marker per ref needs a content read (`git show <ref>:<path>`).

### Option C: Durable landed-at anchor

At DONE / accept, record the landed commit + branch into a ref-committed field
(status-board Notes, or slice/ADR frontmatter), so the authoritative pointer
lives in the repo, not only in memory.

- **Pros:** Removes memory as the single copy of "where it landed"; gives the
  Option-B check a *trustworthy* anchor to compare against — one written only at
  a genuine DONE/land moment on the authoritative branch, so an abandoned spike
  never produces one. This is the signal raw sibling state cannot supply.
- **Cons:** Heavier than a pure git scan — a new field and a new write moment
  (though at an *existing* transition, not a new step). Existing slices predate
  the anchor, so an advisory fallback is still needed for un-anchored work.

### Option D: Rely on human/agent vigilance

Document the failure and expect the reader to reconcile marker-vs-memory by
hand.

- **Pros:** Zero code.
- **Cons:** This *is* the status quo, and it failed. The whole premise of jig's
  gates is that load-bearing checks are mechanical, not vigilance-dependent.

### Option E: Claim-based work reservation (ref as a CAS lock)

Reframe the in-flight case from "detect a duplicate" to "prevent one": on
entering a working state, reserve the identifier by publishing a claim on a
shared ref — a compare-and-swap `refs/claims/<N>` (local `git update-ref`
create-if-absent; cross-machine `git push --force-with-lease` create) — the same
lock primitive ADR-0053 uses for spec numbers. A peer both *sees* the claim
(ref scan) and *loses cleanly* on a simultaneous create (CAS rejection).

- **Pros:** Closes the in-flight case (Classes B and committed-local/near-window
  C) as **mutual exclusion**, which needs no authority adjudication — dissolving
  the spike-ambiguity that made a raw-state halt unsafe. Reuses a proven jig
  primitive; makes `claimed_by` ([ADR-0045](./adr-0045-slice-claim-covers-active-lifecycle.md))
  atomically enforceable, closing spec 049's unpushed-claim gap.
- **Cons:** Introduces a reserve/release lifecycle with a genuine stale-claim
  failure mode (crashed session holds the lock). Depends on host support for a
  custom ref namespace (unverified — Assumption A1). A pure-offline cross-machine
  peer remains unreachable (narrow residual).

## Recommended Decision

Adopt **Option B (read-side ref-awareness) combined with Option E (write-side
claim reservation)**, and split the response by whether the competing work is
**integrated** — the two halves take different signals, and conflating them is
what produced the earlier drafts' false claim that the in-flight case was
inherently ungateable.

The load-bearing decision: **jig work-coordination must be both ref-aware (read)
and claim-reserved (write).** The current checkout is one witness, not the truth.
Duplication has **four** distinct shapes, and — the correction this ADR's own
review process forced — they are caught by *different* mechanisms; no single one
closes them all. The earlier "un-integrated is inherently advisory-only" was
wrong (a reservation mutex does gate concurrent races), but the opposite
overclaim — that the mutex closes the *reported* incident — is also wrong: the
incident was **sequential** duplication of **finished** work, where no live claim
exists to key on.

- **Class A — re-doing ALREADY-INTEGRATED work.** N is `DONE`/`Accepted` on
  `origin/main` (or a merged ancestor) — authoritative *by definition*, no spike
  ambiguity. **Hard gate**: create/advance/land may halt. False-positive-free bar
  a sanctioned re-open/supersession (bypass — see Open questions).
- **Class B — CONCURRENT in-flight race.** A peer holds N `IN_PROGRESS` (on a
  sibling/remote ref, or a same-machine worktree in the shared `refs/heads/*`
  store) while *this* session also enters `IN_PROGRESS` on N. This is exactly the
  both-ends-`IN_PROGRESS` collision [ADR-0045](./adr-0045-slice-claim-covers-active-lifecycle.md)
  already blocks locally; ADR-0058 makes that block **see the foreign claim on
  sibling/remote refs**. Keyed on the *claim at the build boundary* (not raw
  `DONE`), so it never fires on ADR-0045's sanctioned non-build handoff states
  (implementer `IN_PROGRESS` + reviewer→`REVIEWED`), which stay warn-and-transfer.
  First-claim-wins mutual exclusion needs no authority adjudication; the spike
  ambiguity **converts** to *claim liveness* (stale vs active — solvable via
  timestamp/heartbeat + `--release`).
- **Class C — SEQUENTIAL re-do of work FINISHED on a sibling (the reported
  incident).** N is `DONE` on a sibling branch, un-integrated (not on `main`), and
  its claim was **cleared at `DONE`** (ADR-0045's terminal-release) — so Class A
  misses it (not on `main`) *and* Class B misses it (no live claim, not a
  concurrent build). This is the case the earlier drafts kept losing. It is
  caught only by **reading the sibling refs for N at `DONE`**. Raw `DONE` is
  spike-ambiguous in general — but jig's `DONE` is **evidence-gated** (recorded
  compliance/craft/reconciliation verdicts; ADR-0014), so an evidence-complete
  `DONE` on a sibling is expensive to reach and very unlikely to be a casual
  spike. That makes a **halt-and-reconcile** defensible here (with a bypass): the
  reconciliation is "build *on* that branch / integrate it — don't duplicate it."
  The residual false-positive (a genuinely abandoned yet evidence-complete branch,
  or parallel legitimate completion — which *is* the duplication to catch) is
  handled by the bypass, not by staying silent.
- **Class D — uncommitted or offline-cross-machine (residual → advisory).** A
  peer uncommitted (index/worktree only) or on a machine with no reachable remote
  is on no ref this session can read. Narrow, not irreducible: reserve-early +
  push-immediately plus the CAS claim (below) shrinks Class-B's window to a push
  round-trip; when no shared ref is reachable, fall back to the fail-open advisory.

**The reservation mechanism (Class B).** A git ref as a compare-and-swap lock —
the primitive ADR-0053 already uses for spec *numbers* on `origin/main`,
generalized to per-identifier work claims:

- **Same-machine / concurrent worktrees (jig's topology):** linked worktrees
  share the ref store, so scanning local `refs/heads/*` for a peer's
  `claimed_by`/`IN_PROGRESS` on N detects the collision — *no lock needed for
  detection*. `git update-ref refs/claims/<N> HEAD ""` (empty old-value =
  create-if-absent) is an atomic local mutex for the simultaneous-create window.
- **Cross-machine:** `git push --force-with-lease=refs/claims/<N>: origin HEAD:refs/claims/<N>`
  — first pusher wins; a racing create is rejected. The remote ref store is the
  distributed lock.
- **`claimed_by:`** is the human-readable *who*; the CAS ref is the atomic
  *mechanism*.

Wiring, prioritized:

1. **Class-A hard gate** — halt on integrated `DONE`/`Accepted` at
   create/advance/land. False-positive-free (bar sanctioned re-open). Ship first.
2. **Class-C sibling-`DONE` read (the incident's actual fix)** — at create /
   advance-into-working, scan local+remote sibling refs for N at an
   *evidence-complete* `DONE`; halt-and-reconcile with a bypass. This is what the
   reported incident needed and neither A nor B provides.
3. **Class-B claim reservation + cross-ref build-boundary halt** — reserve N via
   the CAS claim on entering `IN_PROGRESS`; extend ADR-0045's
   both-ends-`IN_PROGRESS` block to consult foreign claims on sibling/remote refs.
   Closes concurrent races without re-blocking ADR-0045's sanctioned handoff.
4. **Divergence advisory (fallback)** — fail-open, low-confidence SessionStart +
   create-time nudge for the offline/no-reachable-ref case and un-claimed
   divergence (extending git-freshness, [ADR-0048](./adr-0048-session-git-freshness-fetch-and-nudge.md)).
   Never blocks.
5. **Durable landed-at anchor (Option C)** — provenance refinement for Class C:
   record `landed_commit`/`landed_branch` at `DONE`/land so the sibling read has a
   precise pointer (and memory stops being the single copy).

Two viability tiers, kept distinct so the heavier work is opt-in:

- **Closes the *reported* incident: items 1 + 2** (Class-A gate + Class-C
  sibling-`DONE` read). This is the lean core — both are *read-side*, reusing
  ADR-0053's verified plumbing, no reserve/release lifecycle, not gated on any
  unverified capability. If nothing else ships, the incident is closed.
- **Full class coverage: + item 3** (Class-B reservation), which closes the
  *concurrent-race* class the incident was not. Item 3 is heavier — a reserve/
  release lifecycle whose same-machine mutex rests on A2 and whose *cross-machine*
  CAS path is gated on the unverified A1 capability — so it is a deliberate second
  step, sequenced after its spike, not bundled into the incident fix.

Item 4 is the offline fallback; item 5 (anchor) is a hardening refinement.
**Open capability risk:** Class B's cross-machine CAS assumes hosts permit
pushing a custom `refs/claims/*` namespace with `--force-with-lease` create
semantics — an unknown a spike must confirm before item 3's remote path is built
(Assumptions / Kill criteria).

## Consequences

**Becomes easier:**
- Catching the reported incident (Class C): re-doing work already `DONE` on a
  sibling branch now hits a halt-and-reconcile ("build on that branch, don't
  duplicate"), instead of a silent GO.
- Hard-stopping a *concurrent* duplicate build (Class B) at the door — same-machine
  worktree or cross-machine peer — via a reservation claim, not an eyeballed nudge.
- Hard-blocking re-do of already-integrated work (Class A), false-positive-free
  bar the sanctioned-supersession case.
- Making `claimed_by` load-bearing: a claim now has an atomic mechanism (a CAS
  ref) behind the human-readable owner, closing spec 049's unpushed-claim gap.

**Becomes harder:**
- A new reserve/release lifecycle (Class B): claims published on entering a
  working state, released on exit, reclaimed when stale — a real state-management
  surface (crash-leaves-stale-claim is the failure mode to design for).
- Lifecycle paths now touch git refs (scan + push), adding latency and a
  network-timeout surface to what were pure local reads. Must stay best-effort;
  the remote CAS push must degrade gracefully offline.
- Must preserve ADR-0045's per-state boundary exactly: halt only at
  both-ends-`IN_PROGRESS`, warn-and-transfer for every other foreign-claim state.
  ADR-0058 widens *where the claim is read from* (sibling/remote refs), not *when
  the halt fires* — over-broadening it would re-block the sanctioned handoff.
- Class C's sibling-`DONE` halt accepts a small false-positive surface (an
  abandoned-but-evidence-complete branch), traded against catching the incident;
  the bypass makes it a reconcile-then-proceed, not a hard wall.
- Identifier identity across refs must survive a renamed slug — match on the
  `NNN-MM` / `NNNN` number, not the filename.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

Verified by reading current source in this checkout:

- ADR-0053's reservation scan enumerates every local + remote ref via
  `for-each-ref` + `ls-tree --name-only` (filenames only); reading per-ref
  *state* adds a content read (`git show <ref>:<path>`).
- `git-freshness` watches exactly one base ref and excludes the branch's own
  remote. `land.py prepare` has no already-landed detection. `origin/main` is the
  canonical integration line, so Class-A state read from it is authoritative.
- jig's `DONE` is **evidence-gated** — `transition … DONE` re-validates recorded
  compliance/craft/reconciliation verdicts (ADR-0014 §5) — so an evidence-complete
  `DONE` on a sibling ref is deliberate, completed work, not a casual spike. This
  is the ground under Class C's sibling-`DONE` halt being defensible (vs the
  general spike-ambiguity of a raw marker). **Bridge caveat:** ADR-0014 validates
  evidence against the *working tree at transition time*, while a cross-ref
  `git show` reads what is *committed on the ref*. For the reported incident this
  holds (the sibling landed — whole tree committed/pushed). If the spec chooses
  the stronger "evidence files present on the ref" read (Open questions), it must
  make this ref-vs-working-tree distinction explicit; the weaker "`DONE` marker
  on the ref" read always works but carries more spike exposure.

Load-bearing forward assumptions (unverified — hence `frame_review` + a spike):

- **A1 (host capability).** Git hosts permit pushing a custom `refs/claims/*`
  namespace, and `--force-with-lease=<ref>:` gives create-if-absent CAS
  semantics against a concurrent creator. If false, the cross-machine path needs
  a different shared surface (e.g. an ADR-0053-style `reserve/<N>` branch on
  `refs/heads/*`, which hosts do allow). **A spike must confirm this before item
  3's (Class-B) remote CAS path is built.** (Item 2, the Class-C read, uses only
  ADR-0053's verified `for-each-ref` + `git show` plumbing — no `refs/claims`
  push, so A1 does not gate it.)
- **A2 (worktree ref sharing).** Linked worktrees share the `refs/heads/*` /
  `refs/claims/*` store, so a same-machine peer's claim is locally visible
  without a push. (High-confidence, but the mechanism rests on it — verify.)
- **A3 (claim liveness).** A stale claim from a crashed/abandoned session can be
  distinguished from a live one cheaply enough (timestamp/TTL or heartbeat) that
  the occupied-gate does not become a chronic false-halt requiring routine
  force-release.

## Kill criteria

- If A1 fails (hosts reject custom-ref pushes), fall back to reserving the Class-B
  claim on a `refs/heads/*` reservation branch (ADR-0053's proven path) for
  cross-machine, keeping the local ref-CAS for same-machine.
- If A3 fails (stale claims common, hard to detect), demote the Class-B halt
  (item 3) to a **strong nudge-with-easy-override** rather than eroding trust with
  false blocks — reservation still surfaces the collision, without the teeth.
- If Class C's sibling-`DONE` halt proves too noisy (abandoned yet
  evidence-complete branches are common in practice), demote item 2 to a strong
  advisory — but note that would leave the *reported incident* only advisorily
  covered, so the anchor (item 5) becomes the path to keep it a gate.
- If the reserve/release lifecycle proves too heavy for the value, keep items 1
  (Class-A) + 2 (Class-C read) + 4 (advisory) and drop the Class-B mutex — still
  closes the reported incident.

## Open questions

- **Class-C posture:** hard halt or strong advisory on a sibling `DONE`? And must
  the read require the recorded evidence files present (stronger, ADR-0014-keyed)
  or trust the `DONE` marker alone (cheaper, more spike-exposed)? Resolve in spec.
- **Claim liveness policy (Class B):** TTL, heartbeat, or manual `--release`
  only? Decides whether the Class-B halt (item 3) can be hard (A3).
- **Claim home (Class B):** `refs/claims/*` CAS ref, an ADR-0053-style reservation
  branch, or a pushed `claimed_by`? Depends on A1; resolve in the spike.
- **Cross-ref transfer semantics:** ADR-0045's warn-and-transfer for non-build
  states assumes a local claim; how does "transfer" behave when the foreign claim
  is on a remote ref? Halt boundary is settled (both-ends-`IN_PROGRESS`); the
  transfer half needs a cross-ref story.
- **Class-A sanctioned re-open** (supersession, or revert-then-redo where the
  `DONE` marker wasn't reverted): needs a bypass distinct from the blanket escape.
- Does item 5's landed-at anchor add enough over the sibling-`DONE` read to be
  worth a new field? It buys precise provenance for reconciliation and a keeps-
  it-a-gate path if Class C is demoted — weigh in spec.
