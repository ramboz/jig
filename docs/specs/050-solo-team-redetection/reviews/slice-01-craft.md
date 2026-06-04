---
slice: 050-01 — memory-sync-team-recheck
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-04T22:37:15Z
prompt_source: review.py pr-review docs/specs/050-solo-team-redetection/spec.md 050-01 skills/scaffold-init/scaffold.py skills/memory-sync/memory.py skills/memory-sync/SKILL.md skills/memory-sync/test_memory.py skills/scaffold-init/test_scaffold.py
---

VERDICT: pass

REASONING:
High-craft work that matches the slice's stated scope. The cross-skill importlib
loader, TTY/non-TTY branching, and `--bootstrap` overwrite-refusal are all sound:
the loader tries four layout-aware candidate paths and degrades to an advisory
exit-0 on failure (matching the established `migrate.py` precedent), the non-TTY
path never blocks, and bootstrap refuses-on-exists before any write. Tests assert
behavior rather than smoke — the AC6 parity matrix asserts `detect_team ==
(count >= 2)` across the full fixture set, the bootstrap test verifies template
substitution and no leaked placeholders, and the explicit-vs-inferred-solo marker
distinction is pinned by two separate tests. The one gap (an untested defensive
branch) is a nit, not a blocker.

SPECIFIC ISSUES:
- [strength] skills/scaffold-init/scaffold.py:415-456 — Threshold parity made
  structural: `detect_team` delegates to `count_team_contributors`, the `>= 2`
  lives in one place; the parity matrix is a genuine behavior check, not a tautology.
- [strength] skills/memory-sync/memory.py:78-98 — `_load_scaffold_module` failure
  path well-formed: skips non-files/null specs, raises naming every tried path +
  remediation hint; `team-check` catches it and exits 0 (advisory, never blocks).
- [strength] skills/memory-sync/memory.py:197-224 — TTY branching clean and
  testable: `isatty` injectable, non-TTY prints follow-ups and exits 0 (AC7),
  `EOFError` defaults to safe "n", unrecognized answers fall through to skip.
- [nit] skills/memory-sync/memory.py:148-154 — the scaffold-unreachable
  degradation branch (`_ScaffoldUnavailableError` -> diagnostic + exit 0) is not
  directly exercised by a test (the sibling template-missing degradation IS).
  Low risk given the four-path search; the one defensive arm without coverage.
- [nit] skills/memory-sync/memory.py:161-168 — `--bootstrap`/`--never` run before
  the signal-fires check, so explicit `--bootstrap` writes people.md even on a
  solo repo. Intended (the flag relays the user's explicit `[y]`; signal gated at
  nudge time) and documented in the deviation log, but a one-line comment at the
  action site would save a future reader the round-trip.

RECONCILIATION NOTES:
Address both nits in reconciliation: (1) add coverage for the scaffold-unreachable
branch; (2) add the clarifying comment. Deviation log is faithful; no scope creep;
the 050-02 stale-audit work is correctly left out.

Reviewer: jig:reviewer (read-only craft pass, pr-review baseline). Full suite green (exit 0).
