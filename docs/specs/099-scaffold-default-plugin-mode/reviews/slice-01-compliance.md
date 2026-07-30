---
slice: 099-01 — default-plugin-mode
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-30T16:49:30Z
prompt_source: review.py implementation docs/specs/099-scaffold-default-plugin-mode/spec.md 099-01 (7 independent rounds)
---

Independent compliance review of slice 099-01, run as seven rounds. Each reviewer
saw the slice fresh with no access to the implementation conversation; rounds 2-7
were told what the prior round objected to and instructed not to re-run it, so
each had to find its own strongest finding.

Rounds 1-6 returned `needs-changes`. Round 7 returned `pass`.

All four acceptance criteria are met against their amended text, and every
amendment is recorded in the artifact that carries it (spec §Out of scope,
ADR-0041 OQ1/OQ3, the slice's AC #1 and DoR annotations). The reviewer checked
specifically for unrecorded or self-serving amendments and found none.

**What the rounds actually caught** — the pattern matters more than the list:

1. `SKILL.md`'s Output section omitted `.claude/settings.json`, which the OQ1
   fold-in made the default path write. A skill contract understating a
   security-relevant artifact of its own default path.
2. That same section, once fixed, named a host inside a conditional — and
   `SKILL.md` bodies are machine-translated per host, so it shipped to Codex as
   "Codex host only; Codex has no equivalent…", promising Codex projects a
   destructive-command floor they never get. An understated claim became an
   overstated one.
3. Nothing pinned the *rendered* contract, which is why (2) shipped.
4. The status board still asserted the `permissions.deny` gap as open and out of
   scope, in the file built to be read *instead of* the spec.
5. A deviation entry written to be honest about a gap was itself over-claimed —
   it said the completion summary "runs zero checks in plugin mode"; running the
   command showed `1/1 checks passed`.
6. The OQ3 mode gate was a **no-op on the only path that ships**: the Codex build
   pre-rewrote packaged templates, so the gate matched nothing when scaffolding
   from an installed plugin. Every source-tree test passed throughout.
7. The fix for (6) broke a second consumer — `decisions.py` and friends read
   packaged templates at runtime and copy them verbatim, so canonical templates
   handed Codex an unresolvable variable. It also turned a packaging test red
   *invisibly*, because that module self-skips below Python 3.11 and the local
   floor is 3.9 while CI runs 3.12.

**The recurring shape, which is the slice's real lesson:** source is transformed
before shipping, so a test on the source is not a test of the contract. It
appeared three times — printed strings, `SKILL.md` bodies, `templates/` — and
each time the source read correctly. The fixtures that finally had teeth all read
the *shipped* artifact: `test_skill_md_output_survives_the_codex_translation`
against the packaged `SKILL.md`, and
`test_codex_docs_correct_when_scaffolded_from_the_shipped_package`, which
scaffolds out of `hosts/codex/plugins/jig/` in both modes and asserts the cited
tree equals the tree actually created.

Vacuity was checked, including on a fixture added to close a vacuity finding: the
AC #4 pin asserted a string the invocation example already guaranteed, so
deleting the entire sixth Q&A question left it green. It now pins the question's
own heading and content, verified red by deletion.

**Open and honestly bounded:** OQ2 (a *detected* default) stays open — the
advisory note covers the clone-and-run population, and release-zip, copied-tree
and cross-host runs trip nothing. `permissions.deny` is Claude-only in **both**
modes; Codex has no project-scoped permission surface, a gap this slice does not
close and did not open. Four deferrals carry resolution triggers in
`refinement-todo.md`, two of them written to re-probe before spending anything.
Bug 018 is verifiable only via PR #145, which the log states explicitly.
