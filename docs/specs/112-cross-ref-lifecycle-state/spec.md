---
status: IN_PROGRESS
skill:
use_cases: []
---

# Spec 112: Cross-ref lifecycle checks & claim-based work reservation

> Implements [ADR-0058](../../decisions/adr-0058-cross-ref-lifecycle-state-check.md)
> (Accepted 2026-08-27). Reserved via `workflow.py new`.

## Overview

jig's lifecycle checks all trust the current checkout as the whole truth, so a
session can build a duplicate of work that already exists on another ref — the
motivating incident, where a stale on-disk `DRAFT` was believed over finished
work on a sibling branch. ADR-0058 makes coordination **ref-aware (read)** and
**claim-reserved (write)**, splitting duplication into four cases caught by
*different* mechanisms:

- **Class A — already integrated** on `origin/main`: hard gate (authoritative by
  definition).
- **Class B — concurrent in-flight race** (both-ends-`IN_PROGRESS`): extend
  ADR-0045's block cross-ref via a claim reservation (a git ref used as a CAS
  lock).
- **Class C — sequential re-do of work FINISHED on a sibling** (the reported
  incident): read sibling refs for N at an evidence-complete `DONE`;
  halt-and-reconcile with bypass (defensible because jig's `DONE` is
  evidence-gated, ADR-0014).
- **Class D — uncommitted / offline-cross-machine**: fail-open advisory residual.

**Incident-minimum = Class-A gate + Class-C read** (both read-side, no
reserve/release, no unverified-capability gate). **Full coverage** adds the
Class-B reservation, which is gated on a host-capability spike (custom
`refs/claims/*` CAS push).

## Assumptions

<!-- Risk-gated (spec 064-02 / ADR-0020). -->

Verified by reading current source:

- `reservation.py` enumerates every local + remote ref (`for-each-ref` +
  `ls-tree --name-only`); reading per-ref *state* adds a `git show <ref>:<path>`.
- `git_freshness.py` watches exactly one base ref, excluding the branch's own
  remote. `land.py prepare` has no already-landed detection.
- `origin/main` is the canonical integration line (Class-A read authoritative).
- jig's `DONE` is evidence-gated (`transition … DONE` re-validates recorded
  verdicts, ADR-0014 §5) — the ground under Class C's sibling-`DONE` halt.

Forward assumptions (unverified — carried on the slices that rest on them):

- **A1 (host capability):** hosts permit pushing a custom `refs/claims/*`
  namespace with `--force-with-lease` create-CAS. Gates the Class-B *cross-machine*
  path only; **spike 112-04 resolves it.** Fallback = ADR-0053 reservation branch.
- **A2 (worktree ref sharing):** linked worktrees share the ref store (same-machine
  claim visible without push).
- **A3 (claim liveness):** stale claims (crashed session) are cheaply
  distinguishable from live ones — decides whether Class-B halt can be hard.
- **Class-C evidence-on-ref bridge:** ADR-0014 validates the working tree at
  transition; a cross-ref `git show` reads committed ref state. Holds for a
  landed sibling; the "evidence files present on ref" read must make this explicit.

## Decomposition

SPIDR — **Rules** axis (one slice per class/mechanism), **Interface** sub-split on
Class A (land vs create/advance), and one **Spike** for the genuine host-capability
unknown (A1) that gates Class B.

- **112-01 / 112-02 (Class A, item 1):** hard gate at the land and create/advance
  boundaries. Incident-minimum.
- **112-03 (Class C, item 2):** sibling-`DONE` read — *the reported incident's
  fix*. Incident-minimum.
- **112-04 (spike):** does the host permit `refs/claims/*` CAS pushes? Gates 112-05.
- **112-05 (Class B, item 3):** claim reservation + cross-ref build-boundary halt.
  Full coverage; depends on 112-04.
- **112-06 (Class D, item 4, DEFERRED):** fail-open advisory divergence fallback.
- **112-07 (item 5, DEFERRED):** durable landed-at anchor (provenance refinement).

## Slices

- [112-01 — classa-land-backstop](slice-01-classa-land-backstop.md)
- [112-02 — classa-create-advance](slice-02-classa-create-advance.md)
- [112-03 — classc-sibling-done-read](slice-03-classc-sibling-done-read.md)
- [112-04 — refclaims-cas-spike](slice-04-refclaims-cas-spike.md)
- [112-05 — classb-claim-reservation](slice-05-classb-claim-reservation.md)
- [112-06 — classd-advisory-fallback (DEFERRED)](slice-06-classd-advisory-fallback.md)
- [112-07 — durable-landed-anchor (DEFERRED)](slice-07-durable-landed-anchor.md)
