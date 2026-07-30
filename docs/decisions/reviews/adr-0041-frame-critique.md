---
adr: 0041
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-30T03:56:03Z
prompt_source: review.py frame-critique docs/decisions/adr-0041-scaffold-defaults-to-plugin-mode.md (6 independent rounds)
---

Frame-critique of ADR-0041, run as six independent rounds. Each reviewer saw the
record fresh, with no access to the implementation conversation; rounds 2–6 were
told what the prior round had objected to and instructed not to re-run it, so
each pass had to find its own strongest attack.

Rounds 1–5 returned `needs-changes`. Round 6 returned `pass`.

**The load-bearing assumption** is the population claim: that the modal no-flag
caller has the jig plugin installed. It is *asserted*, never probed, and the
critique took it apart — the first round showed that two of README's four
documented install recipes are bare `git clone` + run-the-script, so flipping the
default silently produced an empty scaffold for anyone following jig's own
instructions, with no error to search for.

**The frame passes not because the claim was established, but because the design
stopped depending on it.** The plugin-mode summary now prints unconditionally and
is true for a plugin-less run: it names the outcome and a documented recovery. If
the population claim is wrong, the cost is one truthful sentence and a
`copy-machinery` run, not misdirected work. Round 6's judgement: "the
load-bearing assumption has been made non-load-bearing by design, which is the
correct disposal, not a dodge."

**What each round changed** (detail in spec 099-01's deviation log §11–§15):

1. Named the missed population; added an advisory note; rewrote a kill-criteria
   detector that could never fire on a silent failure.
2. Killed the note's first mechanism — keyed on a plugin-root env var being
   *unset*, which is one-sided, and whose Codex arm rested on a claim
   `docs/architecture.md` does not support. Gave the security-floor table a host
   axis.
3. Caught the replacement detector overclaiming: it detects a *topology* (jig
   source checkout), not the *condition* (no plugin). Scoped it honestly rather
   than piling on heuristics, and priced the residual populations it cannot see.
4. Found the honest scoping had reached the docstring, the ADR and the spec but
   not the **printed strings the adopter reads** — and surfaced the costless fix
   hiding behind the residual accounting: make the unconditional mode line true
   for everyone. That is now the property the frame rests on.
5. Confirmed the frame holds; blocked only on the ADR still carrying a claim it
   had retracted, and a deviation-log entry that recorded the fix as done when it
   had silently no-opped.
6. **PASS.** Two below-the-frame residues offered as "record, don't block" were
   fixed instead, both being the same defect family: `verify_install.py` still
   asserted where the machinery *is*, and the recovery advice was one flag short
   of executable.

**Open, and honestly so:** OQ2 (a *detected* rather than static default) stays
open — it needs a two-sided plugin-presence probe that jig has considered and
declined to pay for, not one that cannot be built. The advisory note covers the
largest detectable slice of the plugin-less population; release-zip,
copied-tree, and cross-host runs trip nothing, and are named rather than papered
over. OQ1 (`permissions.deny` in plugin mode) and OQ3 (Codex plugin-mode doc
paths) are resolved and implemented.

**Known asymmetry, stated:** `permissions.deny` is Claude-only in *both* modes —
probed, not assumed: a `--host codex --in-repo` scaffold writes no settings file
and no permissions anywhere. Codex has no equivalent project-scoped permission
surface. That gap predates this decision and is not closed by it.
