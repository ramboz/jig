---
slice: 096-02 — baseline-marker-and-resolve
pass: frame-critique
verdict: needs-changes
reviewer: jig:reviewer subagent (frame-critique pass)
reviewed_at: 2026-07-28T02:08:55Z
prompt_source: review.py frame-critique
---

Frame-critique of 096-02 returned **needs-changes**.

**Primary (orchestrator-verified against the tree).** AC4's justification —
that a scaffolded jig baseline copy is "indistinguishable *by path*" from a
richer skill, so a forward-only `jig_baseline:` marker is what makes
project-scope discovery safe — is false:

- `skills/scaffold-init/scaffold.py:742` — `dst_dir = skills_dst /
  f"jig-{skill_dir.name}"`. Every user-facing skill lands at
  `.claude/skills/jig-<name>/`, never `.claude/skills/<name>/`.
  (The unprefixed copy at :726 is only for `_`-prefixed shared modules, which
  carry no SKILL.md and are never discovery candidates.)
- `skills/migrate/migrate.py:287` — `entry.name.startswith("jig-")` already
  ships as exactly this discriminator.
- `migrate.py:108-115` documents jig routinely retrofitting a real field
  population, contradicting ADR-0039's "not yet expected to exist in the field."

Consequence of forward-only: in every project scaffolded *before* this slice,
`.claude/skills/jig-pr-review/SKILL.md` keeps untouched frontmatter
(`scaffold.py:701` — "The frontmatter is left untouched") whose description is
the strongest lexical match for the `pr-review` category, unmarked, at the
*winning* precedence scope. Zero-config discovery then offers jig's baseline
back to itself as "richer" — the exact failure AC4 exists to prevent — and
096-05's anomaly is blind to it, since a skill *was* applied. AC5's CI test
measures only the population that cannot fail.

Unconsidered alternative: exclude `jig-*` at project scope (the shipped
`migrate.py` discriminator) — covers old and new scaffolds, needs no marker, no
migration, no host-package regeneration. The marker retains a genuine job at
plugin/admin scope, but that is not the argument AC4 makes.

**Secondary.** The one assumption spec.md:83-85 assigned to this slice
("reviewer can Read a SKILL.md at project and admin scope … cheap to verify in
096-02") has no AC or DoD item. AC1 verifies a *Python helper* can `stat` a
path; the read-only reviewer subagent is a different actor with a different
permission surface. DoD:78-79 forecloses the only check that would settle it.

**Secondary.** Verticality: none of AC1–AC6 changes what any review pass does;
the marker's only consumer arrives in 096-03. The slice commits a permanent
cross-cutting frontmatter contract plus a CI gate across both host packages
before the layer that needs it is validated.
