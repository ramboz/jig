---
status: DRAFT
skill: (none — hook + docs)
tier: (none — dev infrastructure)
adr_required: true
---

# Spec 042: Spec-gate authentication model — env var vs. file marker

## Overview

`hooks/scripts/jig-spec-gate.sh` blocks Edit/Write to
`docs/conventions.md` unless `JIG_CONVENTIONS_APPROVED=1` is set in the
environment. The docstring at line 7 claims:

> Changes should be a deliberate, human-approved act — not something an
> agent does as a side effect of unrelated work.

But the agent has the Bash tool. An agent that decides to edit
conventions can run a single bash call that exports the env var *and*
triggers the edit, or chain
`JIG_CONVENTIONS_APPROVED=1 some-command-that-pipes-to-edit`. Nothing
prevents the agent from setting it.

The hook is therefore not a *human approval* gate — it's a
**deliberateness speed bump** that forces the agent to articulate
intent in shell. That may be enough! The hook catches the side-effect
case. But the rationale claims a stricter guarantee than what's
enforced.

A secondary concern: the hook matches `docs/conventions.md` literally
(line 28–29). A project using `CONVENTIONS.md` at root, or any other
naming, gets no gate. The hook is implicitly jig-layout-specific,
which isn't documented.

## Why now

- **Framing claim ↔ enforcement reality gap.** Same theme as spec
  040 (isolation honesty). Landing both compounds the trust
  improvement.
- **Path-pattern flexibility surfaces when migrate-mode adopts
  the gate.** Downstream projects with non-jig layouts get
  silent no-op gating today.
- **Hard-to-reverse decision.** Picking (a) speed-bump framing
  vs. (b) file marker vs. (c) two-step token shapes future
  enforcement surfaces. ADR-first.

## Goals

1. **Decide the model via ADR.** Three options minimum:
   - **(a) Speed bump (status quo, accurate framing).** Document
     that the env var is a deliberateness gate, not human-only.
     Update the docstring + README + workflow.md. No code change.
   - **(b) File-marker model.** Replace the env var with a
     short-lived `.jig/conventions-approval-token` file with a
     recent mtime, created by a documented manual command. Agent
     *can* still create it, but the friction is higher and the
     action is auditable on disk.
   - **(c) Two-step token.** Hook expects an env var *and* a file
     marker. Belt-and-suspenders.

2. **Decide whether path-pattern flexibility matters.** Does the
   gate stay jig-layout-specific (`docs/conventions.md` only), or
   grow a `JIG_GATED_FILES` config (or default to a small allowlist
   covering common naming variants)?

3. **Implement under the chosen option.** Under (a) it's docstring
   + README + workflow.md alignment. Under (b) or (c) it's a hook
   rewrite + the matching manual command + tests.

## Non-goals

- **No removal of the hook.** Whatever model wins, the hook keeps
  firing — the question is what signal it requires.
- **No expansion of the gate to other files** (beyond optional
  path-pattern flexibility under Q2). This spec covers the
  *authentication model* of the existing gate.
- **No "always allow" sudo-style mode.** If the agent has legitimate
  reason to edit, it follows the documented approval flow per call.

## Current state (verified 2026-05-26)

- `hooks/scripts/jig-spec-gate.sh:7` — docstring claims
  "human-approved act." Reality: env var any Bash invocation can set.
- `hooks/scripts/jig-spec-gate.sh:28–29` — path match is literal
  `docs/conventions.md`. No `JIG_GATED_FILES` config.
- Path resolution uses `os.path.realpath` (line 22) to defeat
  traversal — that part of the gate is solid.

## Decomposition

**Suggested SPIDR axis: R (Rules)** primary — "what counts as
approval" is the core decision. The implementation shape varies
dramatically by option, so the ADR has to land first.

### Slices (TBD until clarify runs)

1. **`042-01 gate-model-adr`** — ADR with options (a) / (b) / (c)
   spelled out, recommendation, consequences. Accept before slice 2.

2. **`042-02 apply-chosen-model`** — under the accepted policy:
   - **(a)**: docstring + README + workflow.md align with
     "deliberateness gate, not human-only." Smallest possible
     change.
   - **(b)/(c)**: rewrite the hook to check the file marker
     (and/or env var); add a manual approval command (probably
     `python3 scripts/approve_conventions.py` or similar);
     update tests.

3. *(optional)* **`042-03 gate-path-flexibility`** — if the ADR
   decides path patterns need to vary by project, add
   `JIG_GATED_FILES` config or per-project gated-list mechanism.
   Skip if (a) wins and the layout-specific match is acceptable.

## Open questions for `/jig:clarify`

- **Q1.** Is the current gate catching bugs in practice, or is it
  deadweight? Hard to know without telemetry. Worth pairing with
  spec 041 (routing observability) if the trace can also log gate
  trips.
- **Q2.** What's the threat model? (i) unauthorized agent changes,
  (ii) *accidental* agent changes, or (iii) both? The env-var model
  addresses (ii) well and (i) poorly. The file-marker model is
  marginally better on (i). True human-only enforcement requires
  a different channel entirely (e.g., a CI check on PRs, not a
  hook).
- **Q3.** Coordination with spec 036's policy: if 036 picks
  "closed specs are immutable," this gate is a natural enforcement
  mechanism for `docs/conventions.md` only — not the broader
  closed-spec immutability rule. Worth noting in the ADR.

## Dependencies / coordination

- **Run after spec 036** (closed-spec drift policy) — the ADR this
  spec produces will be subject to whatever amendment convention
  036 establishes.
- **Theme-cluster with spec 040** (isolation honesty) — same
  framing-vs-enforcement gap.
- **Light coupling with spec 041** (routing observability) — if
  the trace can include gate trips, Q1 becomes answerable.

## References

- External review brief: [`brief-08-spec-gate-model.md`](../../external-review/brief-08-spec-gate-model.md)
- Verification 2026-05-26: env var + literal path match both
  confirmed in `hooks/scripts/jig-spec-gate.sh`.
