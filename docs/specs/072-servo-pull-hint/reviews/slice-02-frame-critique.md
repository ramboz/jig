---
slice: 072-02 — unscaffolded-suggestion
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-27T20:26:51Z
prompt_source: review.py frame-critique docs/specs/072-servo-pull-hint/spec.md 072-02 docs/specs/072-servo-pull-hint/slice-02-unscaffolded-suggestion.md (round 3)
---

VERDICT: pass

REASONING:
Three rounds of pre-impl frame-critique. The frame now survives its strongest
attack. Round 1 caught (a) machine-global marker vs per-project nudge causing a
forever-nag and (b) unexamined writer-timing. Round 2 caught (c) reachability
mis-grounded on an assumed verify step and (d) AC6 conflating "shown" with
"seen." All four are closed: A1 makes machine-global presence the intended
trigger with AC6 + opt-out as scoping levers; A2 grounds reachability on the
scaffold writers (the Q1 target has the marker by construction) and demotes
verify-install to a bonus; AC6 consumes the once-per-project budget only on an
interactive isatty() land, so an unobserved CI/headless run cannot silently burn
the one budgeted nudge. The single residual is a deliberate, named trade-off, not
an unexamined assumption.

SPECIFIC ISSUES:
- [nit] AC6's `sys.stdout.isatty()` is a fail-open proxy for "human saw the
  nudge": a human observing `prepare` through an agent harness / pty wrapper
  (non-TTY — jig's own dogfooding mode) does not consume the budget, so the
  one-line nudge re-fires on each land until `.jig/no-servo-hint` is dropped.
  NON-BLOCKING: the frame deliberately fails open (an unseen budget burn is
  unrecoverable; a re-nudge is one line + a one-file opt-out), the maintainer
  named isatty() as the cadence lever (2026-06-27), and A3 already accepts
  bounded over-nudge. Captured as a "Known residual" note in the slice; flag at
  reconciliation, do not add harness detection speculatively (072-03 lesson).
- [nit] A2 assumes "uses servo on other projects" => a scaffold writer wrote the
  marker. True for any servo project created via scaffold-init/scaffold_runtime;
  not provably true for a `.servo/` acquired without a local scaffold writer
  (e.g. a committed `.servo/` cloned in). That is a degenerate, non-functional
  servo setup, and the slice treats never-scaffolded silence as desired — the
  boundary is named, not hidden. Not load-bearing.
