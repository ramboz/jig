---
status: Proposed
dependencies: [adr-0011, adr-0013, adr-0051, adr-0059]
last_verified: 2026-09-08
frame_review: true
---

# ADR-0060: Per-execution-mode write-boundary enforcement

## Status

Proposed (2026-09-08)

## Context

jig enforces its checkpoints with soft, advisory hooks, a posture that quietly
assumes a human is attending every run. Every jig hook is an advisory nudge that
exits 0 ([ADR-0011](./adr-0011-spec-gate-model.md) — the spec-gate is a
*deliberateness* signal, "real control is out-of-band";
[ADR-0013](./adr-0013-security-floor-policy.md) — "defense-in-depth, not a
firewall"). The real control is delegated out-of-band to GitHub branch
protection + CI, and the governance plane
([ADR-0051](./adr-0051-autonomy-governance-plane.md)) scaffolds CODEOWNERS +
protected-path CI but is **inert until branch protection is armed** — arming is
a manual step the adopter must take.

Verified current state (2026-09-08, probed this session): `hooks/hooks.json`'s
`PreToolUse` matchers are `Task` / `Skill` / `Edit|Write|MultiEdit` / `Read` —
**none match `Bash`**, so `git push` and `gh pr create` (the write boundary)
pass through with no hard gate. The only hard control near the boundary is the
`permissions.deny` floor (destructive-command globs — force-push / reset /
`rm -rf`; non-exhaustive, and *not* a confirmation on an ordinary push).
`governance.py identity-check` **is** built and Accepted, but it is a *fail-safe
reporting signal* (is the run identity distinct and NOT merge-capable?) intended
to be consumed by a servo-side readiness gate — it does not itself block any
write, and the servo halves that would consume it (servo specs 023/024/025 in
`ramboz/servo`) are not built.

This soft posture is **silently coupled to an attended-execution assumption**: a
human is at the terminal, so a nudge is enough. That assumption breaks the moment
jig work runs **unattended** — the servo-delivered `--background` path in the
composed servo×vellum pilot ([ADR-0059](./adr-0059-servo-delivered-work-design-review-gate.md),
Proposed) and the [ADR-0051](./adr-0051-autonomy-governance-plane.md) autonomy
bridge. Under an unattended run the nudge is the wrong control, and the
in-helper-only nature of jig's review/land gates (they are bypassed by manual
`gh`/`git`, the web UI, or vendored-copy merges) means an autonomous loop can
reach `push`/`PR`/merge with nothing hard in its way.

Two Adobe "re-think" engineering posts (reviewed 2026-09-08) independently land
on the same control jig has deliberately not built, *because both run
unattended*: Mysticat-skills ("safety is inherited, not bolted on" — reach the
write boundary through the product's own code, never a parallel operational path
that "will drift, silently, and cause the incident nobody predicted"), and
agentic-ic (**"Rule = should; Hook = must — only the hook survives an agent
getting it wrong,"** implemented as a `PreToolUse` hook that hard-denies
destructive git ops and forces explicit human confirmation on every push / PR).

This ADR decides jig's enforcement *posture* across execution modes. It does not,
by itself, build the mechanism; it fixes the principle and the boundary of
responsibility so the mechanism can be built (and partly delegated to servo) when
the pilot is first scheduled to run unattended. A hard constraint frames the
decision: per the servo↔jig coupling rule, jig stays supervised + soft-hook-gated
and **must not take an autonomy primitive into its own always-on flow**
([ADR-0022](./adr-0022-pluggable-oracle-boundary.md); the `servo-jig-coupling-boundary`
memory) — servo owns unattended/autonomous operation.

## Decision Options Considered

### Option A: Status quo — soft nudge only, rely entirely on out-of-band branch protection
- **Pros:** Zero new jig machinery; fully consistent with ADR-0011 / ADR-0013; simplest to reason about; keeps all enforcement server-side where the "parallel path drifts" argument says the true boundary lives.
- **Cons:** Inert by default (arming is manual and often skipped); the push/PR boundary an agent reaches *directly* stays ungated even when branch protection is armed (protection gates the *merge*, not the push or the PR); the attended-execution assumption stays hidden and unaddressed; leaves the servo-integration seam exactly where the incident-nobody-predicted lives.

### Option B: Hard-deny always (attended and unattended alike)
- **Pros:** Uniform; no execution-mode signal to obtain or trust; the strongest single-rule guarantee.
- **Cons:** Breaks jig's deliberate soft-hook philosophy for the common attended case, where a present human makes the nudge sufficient; adds friction/annoyance to ordinary solo/attended development; over-rotates against "defense-in-depth, not a firewall" (ADR-0013); an always-on Bash hard-deny is close to an autonomy primitive living in jig's own flow, which the coupling rule forbids.

### Option C: Per-execution-mode posture — attended nudge, unattended hard boundary (recommended)
- **Pros:** Preserves attended-dev ergonomics unchanged; closes the unattended gap; matches what agentic-ic / Mysticat actually do; aligns with ADR-0051's fail-safe identity model (posture keys on *capability/mode*, not name, and fails safe when unknown); keeps the hard-deny out of jig's own always-on hooks by assigning it to the unattended executor (servo) and/or server-side arming.
- **Cons:** Needs a *trustworthy* execution-mode signal that the agent-under-test cannot set for itself (a spoofable signal is worthless — the identity-check lesson); introduces mode plumbing and a cross-repo contract; risk of a mis-scoped fail-closed gate blocking a legitimately-attended run if the signal is wrong.

### Option D: Server-side only — arm branch protection + a required identity-separation check, ship nothing in-process
- **Pros:** The genuinely non-bypassable layer; the "parallel path" argument says the real boundary is server-side anyway; nothing new in jig's client-side flow.
- **Cons:** Inert until the adopter arms it (jig cannot force server-side settings); gates the *merge* only — an unattended run can still push a branch and open a PR, which is exactly the boundary servo's `--background` path acts on; unavailable as the *whole* answer for a pilot that wants to run before arming is complete.

## Recommended Decision

Adopt **Option C**, with **Option D as its server-side complement, not an
alternative to it**. jig's enforcement posture is a function of execution mode:

1. **Attended execution keeps today's posture unchanged** — soft, advisory,
   exit-0 nudges (ADR-0011 / ADR-0013). Nothing about the interactive developer
   experience changes.
2. **Unattended execution requires a hard boundary** at `push` / `PR` / merge,
   **fail-closed**: when execution mode is unknown, or when the autonomy
   preconditions are unattested, the run is treated as unsafe and stopped —
   mirroring `governance.py identity-check`'s fail-safe-on-unknown rule.
3. **jig does not own the unattended hard-deny mechanism.** Per the coupling
   rule, the always-on hard-deny is not added to jig's own hook set. jig's half
   is: (a) make the attended-execution assumption *explicit* in the ADR-0011 /
   ADR-0013 posture rather than implicit; (b) keep `governance.py identity-check`
   as the precondition signal; and (c) define the mode-aware seam — a reciprocal
   execution-mode/arming contract (the same shape as the spec-072 `available.json`
   breadcrumb servo already writes) that the unattended executor reads to arm its
   own hard-deny. The hard boundary itself is armed by **servo** (for the runs it
   drives) and by **server-side branch protection + a required identity-separation
   check** (the non-bypassable merge backstop). The reciprocal servo half is its
   own servo-side ADR, not this one.

The unifying rule: an unattended run may reach the write boundary only when the
mode is known *and* the ADR-0051 autonomy preconditions (distinct,
non-merge-capable run identity + armed branch protection) actually hold;
otherwise it stops. Attended runs are unaffected.

## Consequences

**Becomes easier:**
- An unattended servo run can no longer silently push, open a PR, or merge past
  jig's gates — the failure mode both blog posts warn about is closed by
  construction rather than by hoping the adopter armed branch protection.
- The autonomy story becomes honest: "safe to run unattended" is a checkable
  precondition (mode known + identity separated + protection armed), not an
  implicit assumption baked into a soft nudge.
- The long-hidden attended-execution coupling in ADR-0011 / ADR-0013 is named,
  so future gate design states the mode it assumes.

**Becomes harder:**
- Someone must define and wire the trustworthy execution-mode/arming signal —
  cross-repo work with servo, and a genuinely agent-uncontrollable source (an
  env/mode the loop cannot set for itself, or a server-side attestation).
- A new hard boundary + mode plumbing to build, test, and keep in step across
  jig and servo; more moving parts at the seam.
- A fail-closed gate scoped too broadly could block a legitimately-attended run;
  the fail-closed bias must apply to *unattended-or-unknown*, never to the
  attended path.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **Verified this session (probed):** `hooks/hooks.json` has no `PreToolUse`
  `Bash` matcher, so `git push` / `gh pr create` are ungated in-process;
  `governance.py identity-check` is a fail-safe *reporting* function (read of
  `skills/scaffold-init/governance.py`), not an in-process block.
- **Unverified, load-bearing — probe before building:** that the host (Claude
  Code / Codex) can express a `PreToolUse` matcher on the `Bash` tool that denies
  specific git commands *and* can supply an execution-mode signal the
  agent-under-test cannot itself set. If the host cannot supply an
  agent-uncontrollable mode signal, the in-process leg of Option C is spoofable
  and collapses to Option D. (This is a harness-capability claim; the
  `permissions.deny` floor proves command-level denial exists, but not a
  mode-conditioned one.)
- **Point-in-time:** the servo readiness/consumer halves (servo specs 023/024/025)
  remain unbuilt; re-read `ramboz/servo` before asserting its shape (its
  ADRs/specs move fast — `servo-jig-coupling-boundary` memory).

## Kill criteria

- The host cannot provide an agent-uncontrollable "unattended" signal → the
  in-process hard-deny is unenforceable; fall back to Option D (server-side only)
  and drop the in-process leg.
- jig autonomy is never actually run unattended (the servo pilot is abandoned) →
  the decision is moot; shelve it (the attended posture is already the status quo).
- Armed server-side branch protection + a required identity-separation check
  proves sufficient in practice over a meaningful sample (no push/PR-boundary
  incident on unattended runs) → the in-process boundary is redundant; keep D,
  retire C's in-process leg.

## Open questions

- **Who writes the execution-mode/arming signal?** A reciprocal servo breadcrumb
  (mirroring spec-072's `available.json` — servo, as the unattended executor,
  is the natural writer), a host-native run-mode the agent can't set, or a
  server-side attestation? The signal's trust model is the crux.
- **What exactly is "the write boundary"?** `git push`, `gh pr create`, and/or
  the merge — likely push+PR for the in-process leg (Option C) and merge for the
  server-side leg (Option D). Name the set precisely before building.
- **Where does the hard-deny live?** The coupling rule points it at servo (or
  server-side), not jig's own hooks. Confirm the split: jig ships the
  attended posture + the mode-aware seam + the identity-check precondition; servo
  arms the unattended hard-deny for its own runs. This interacts with
  [ADR-0022](./adr-0022-pluggable-oracle-boundary.md)'s coupling boundary.
- **Should the unattended hard-deny be contingent on `identity-check` reporting
  `ready`?** i.e. unattended + not-`ready` = hard stop, unattended + `ready` +
  armed protection = proceed — folding this decision into ADR-0051's existing
  arming checklist rather than standing up a parallel precondition.
