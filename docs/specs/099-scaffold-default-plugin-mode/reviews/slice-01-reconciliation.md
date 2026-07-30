---
slice: 099-01 — default-plugin-mode
pass: reconciliation
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-30T17:10:38Z
prompt_source: review.py reconciliation docs/specs/099-scaffold-default-plugin-mode/spec.md 099-01 (2 rounds)
---

Independent reconciliation review of slice 099-01, verifying the deviation log
and sweep against the tree rather than against intent.

Round 1 returned `needs-changes`; round 2 returned `pass`.

**Round 1's blocker was the log's own recurring defect, one level up.**
`AGENTS.md` — jig's own Codex primer — never got the 099-01 Active-specs entry
that `CLAUDE.md` carries, while the sweep row said `updated`. The row read
"Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates". **A grouped
disposition is true of the group and unfalsifiable per member**, which is exactly
why deviation §8 declared grouped rows replaced by file-level ones. That rule was
applied to the rows §8 was looking at and not to this one, so the miss rode
inside the group for nine further entries. Row split into three; `AGENTS.md`
updated.

Five further inaccuracies, all the same shape — the record describing a state the
tree had moved past: a deferral count of three where there were four; §16
describing a fixture assertion that §17 later changed; an ADR sentence still
carrying the loose detector form since tightened; a sweep row crediting rationale
to two assertions when one carries it; and three "default (in-repo)" framings
surviving in a test file two entries claim to have swept, beside a sibling
docstring that *was* corrected.

**Round 2 verified each fix individually** and spot-checked the rest against
source: §20's corrected `verify_install.py` account matches the real
`seed_expected` branch; §22's fixture pins the question heading rather than the
vacuous `--in-repo` grep; §23's revert is visible in the builder; §24's "only
`/skills`" probe holds against the packaged Codex templates; and every sweep row
opened matched its disposition — README recipes, product-vision principle #7,
philosophy, adoption-readiness, glossary, learnings, `migrate/SKILL.md` in both
packages, the ADR index, the status-board Notes cell, both host packages, and the
host-neutral `SKILL.md` Output section.

Two non-blocking items were raised and then fixed rather than carried: §16 lacked
an in-place staleness marker (unlike §13/§18/§20, which carry one), and a comment
this slice wrote in `test_scaffold.py` still said `permissions.deny` is "only
written in in-repo mode" — false after the OQ1 fold-in, and the same
"the sweep never reaches the test suite's own prose" gap §19 and §25 name, one
file over.

**Stated limits of this pass.** The reviewer had read-only tools, so claims were
verified at source and artifact level rather than by execution; host-package
parity was checked by symbol counts across the source and both packaged copies
rather than by running the drift guard. Two things remain unverifiable from this
branch by construction and the log says so: bug 018 lives in PR #145, and §9's
`TierUpgradeTests` flake is recorded as cause-unknown. File-count figures differ
across artifacts (79 tracked / 22 / ~128 / ~130); these are different quantities
and the spec figure is original preserved text, but no artifact reconciles them.
