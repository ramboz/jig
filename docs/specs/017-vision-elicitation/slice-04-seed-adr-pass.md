## Slice 017-04 — seed-ADR-pass

**STATUS: DEFERRED** _(deferred — optional optimization, gated on real usage signal)_

**Resolution trigger:** First 5 real `/jig:vision-elicit` runs after 017-02 lands. If >25% of those runs name an explicit locked-in decision during Section 6 (Stack) elicitation that the user would have wanted auto-scaffolded as an ADR, promote 017-04 to DRAFT. If <25%, deferral becomes permanent — the elicitation output already names decisions inline and ADR seeding can stay manual.

**Goal:** when the user names a decision during Section 6 (Stack)
elicitation, the skill scaffolds a draft ADR via
`/jig:adr-workflow new` rather than just writing a sub-bullet.

---

