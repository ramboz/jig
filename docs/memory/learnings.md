# Learnings

> Dead ends, failed approaches, "we tried X and here's why it didn't work."
> The institutional memory that ADRs don't capture because they're not decisions —
> they're anti-patterns and gotchas discovered in practice.
>
> Update via `/jig:memory-sync` during reconciliation.

## Hook PATH injection does not apply to hook commands

`bin/` scripts are added to PATH for the **Bash tool only**, not for hook `command` fields.
Hook commands must use `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>.sh`.
Discovered: plan review (rev 2). Would have caused silent failures at runtime.

## jq is not safe as a hook script dependency

`jq` is not installed by default on macOS. Hook scripts that depend on it will fail
silently on fresh installs. Use Python 3 (reliably present) for JSON parsing.
Discovered: plan review (rev 2). Rule: all hook scripts use `python3 - <<'EOF'`.

## The bootstrap paradox for self-enforcing hooks

A spec-gate hook for `docs/conventions.md` cannot enforce itself during scaffold creation —
the hook only activates after scaffold-init completes. This is fine: the gate starts
working from the second session onward. Don't fight the paradox; document it.
Discovered: plan review (rev 2), issue #3.

## `python3 - <<'EOF'` consumes stdin — fatal for hook scripts

The pattern `python3 - <<'EOF' ... EOF` runs Python with `-` (script from stdin)
where stdin is the heredoc. Python reads the script, leaving `sys.stdin` at EOF.
So `json.load(sys.stdin)` returns "Expecting value: line 1 column 1" — there is
no JSON to read. This silently broke ALL 5 hook scripts in the initial commit.

**Fix:** Use `python3 -c "<script>"` instead. The script is a command-line argument,
and stdin remains available for the hook payload. `docs/memory/tooling.md` was
updated to reflect this.

Discovered: slice 001-01 TDD, while running `test_conventions_gate_blocks`. The
test failed with "Expecting value: line 1 column 1 (char 0)" — the smoking gun.
Caught only because the spec-gate hook had a deterministic test; the other hooks
appeared to "work" because they only ran the silent telemetry/scan paths and
exited 0.

**Generalizable lesson:** If a hook is async and exits 0 on errors (telemetry pattern),
you cannot tell whether it works without a deterministic test that asserts a
specific output. Every new hook needs a unit test that pipes mock stdin and
checks behavior.

## Stocktake → ADR is a working dogfood loop

Slice 001-04 shipped `stocktake.py`. Running it against jig itself surfaced a
deferred-decision item whose resolution trigger literally read "After 3 reconciled
specs in a dogfood project. Write the `scaffold-stable` ADR then." — and jig had
exactly hit that threshold. ADR-0001 was written in response; the deferred item
was struck through in refinement-todo.md.

**Generalizable lesson:** The pattern works. When a deferred decision's resolution
trigger is well-specified (with a measurable condition), stocktake will surface it
at the right moment without anyone needing to remember. Worth replicating: every
deferred item should have a measurable trigger, not a vague "later" or "when
relevant".

## Memory templates are coupled to summary() counting logic

Slice 002-01 removed `## Adding terms` from `glossary.md.template` because
`memory.py summary` counts `^## ` headings as glossary entries. Keeping the
how-to as an H2 would have caused the count to be permanently off-by-one.
The how-to text was preserved as blockquote prose at the top of the file.

**Generalizable lesson:** When a template feeds into automated counting/parsing,
the template structure is part of the contract. Mark this coupling explicitly,
or future template edits will silently break the parser. Mitigation options:
(a) the parser ignores everything before a known delimiter; (b) the parser
recognizes only `add_term`-produced sections via a marker; (c) the template uses
non-H2 styling for instructional content. We chose (c) — simplest, requires no
parser change, and keeps the template visually distinct.

## Python regex \s matches newlines — use [ \t]*$ for end-of-line anchors that must not consume the line terminator
In Python regex, \s matches whitespace **including \n**. Using \s*$ as an end-of-line anchor with re.MULTILINE will silently consume the trailing newline, causing substitutions to glue the next line into the replacement.

**Symptom:** A pattern like `re.sub(r'^Proposed.*\s*$', 'Accepted', text, flags=re.M)` on a Status line will eat the blank-line separator after it and merge the next section's heading into the replacement output.

**Fix:** Use `[ \t]*$` (literal spaces and tabs only) when you want to anchor at end-of-line without consuming the line terminator.

**Occurrences in jig:**
- Slice 006-01 (tdd-helper): adr.py:165 cmd_accept and adr.py:307 cmd_index regen. Surfaced by dogfood (Status line glued to next section heading on first run; reformulated as [ \t]*$ + a regression test test_accept_preserves_section_separator).
- Both occurrences were inside slice 005-01 / 006-01 reconciliation. The pattern is: locate-a-section-and-mutate-the-status-line.

**Watch sites elsewhere in the codebase** (per slice 006-01 deviation log): adr.py:224 _extract_status_and_date uses \s+ in a locator-only role — currently safe but would be more defensible as [ \t]+.

## Spec-number collisions in concurrent sessions — fetch origin/main before picking a number

Surfaced in spec 015's merge (originally drafted as spec 014). A long in-session
spec draft picked `014` based on the local view of `docs/specs/`; meanwhile,
`014-arch-review` landed on `origin/main` from a parallel session. At merge
time, the spec dir collided at the *number* level (different slugs, same NNN)
and the entire spec — directory name, 18 internal cross-references in
`spec.md`, CLAUDE.md entry, status-board rows — had to be renumbered 014 → 015
before the PR could land cleanly.

**Generalizable lesson:** before authoring a new spec, `git fetch origin main`
and check both `git ls-tree origin/main docs/specs/` AND the local
`docs/specs/`. If you're in a long session and another spec might land
concurrently, picking the *next* number is a leaky abstraction.

**Mitigation options** (none implemented; this is documented as a discipline rule):
- (a) `workflow.py new-spec <slug>` helper that fetches origin/main and computes
  the next free number atomically.
- (b) A pre-PR check in `slice-land` that grep's spec dirs against origin/main
  and refuses if there's a number collision.
- (c) Reserve spec numbers explicitly by pushing an empty `docs/specs/NNN-<slug>/`
  commit at spec creation time.
- (d) Accept the discipline ("fetch first") and don't tool it — current default.

**Why it matters:** the rename touched 18 file-internal references and produced
a meta-confusing deviation log ("spec 015 has 014-shaped slice IDs throughout
its history"). The user-facing fix was straightforward; the lesson is to avoid
it at authoring time.

## Scaffold-init glob trap — `.md.template` triggers placeholder substitution

Surfaced in slice 015-01 implementation. `scaffold-init.py` does
`templates/docs/**/*.md.template` → `target/docs/**/*.md` with placeholder
substitution (`{{SUBS}}` → value, refusing on any leftover). Files placed
under `templates/docs/` with the `.md.template` suffix are caught by this
glob. The new slice-creation template (which legitimately ships with
`{{NAME}}` / `{{NUMBER}}` placeholders meant for slice authors to fill in
*much later*) initially used `.md.template` and broke the entire test suite
because scaffold-init tried to substitute those placeholders at scaffold time
and refused with `unrendered placeholders`.

**Fix:** name templates that should be hand-edited later with `.md` only, not
`.md.template`. The existing ADR template at
`templates/docs/decisions/adr-0000-template.md` had already established this
precedent; the slice template just needed to follow it.

**Generalizable rule:** the `.template` suffix in jig is reserved for files
scaffold-init renders at install time. Hand-edited templates use bare `.md`
and live alongside content files unchanged.

## Substitute-reviewer convention — user-in-session can stand in for the reviewer subagent

Surfaced in spec 015's implementation. The jig methodology specifies that
implementation review is performed by a `reviewer` subagent spawn via
`review.py`. For methodology-tooling specs where the user has full context
of the change in-session, an explicit user approval ("I approve those slices,
go ahead and implement them") can substitute for the subagent spawn.

**Constraint:** the substitution must be **documented in the slice's
deviation log §1** as a deliberate methodology shortcut, with the
substantive review criterion the user actually applied (e.g. "all ACs pass,
no regressions, test coverage verified") stated explicitly. Without this,
the deviation looks like a missed review gate.

**When to use:** methodology-tooling specs where the user has been part of
the in-session implementation conversation and the implementer has reported
green tests + no regressions. **When not to use:** any spec with non-trivial
business logic, any spec the user hasn't been hands-on with, any spec where
"a second pair of eyes with no implementation context" is the actual value.

**Future direction:** the convention is currently uncodified — it's a
case-by-case judgment. If the pattern recurs >2 more times, consider a
`workflow.py transition --reviewer user-in-session` flag that requires a
non-empty `--review-summary` and records both in the slice frontmatter.

## Mid-implementation reshape / reword leaves stale future-tense prose in adjacent stanzas

Surfaced across 4 slices in spec 017's run: 017-01 §5(a) (AC #7 said
"three slots" after the AC #4 reshape made it 4); 017-01 §8 (the very
convention rule 017-01 introduced still listed the pre-reshape 3 stanzas
in its How-to-apply line); 017-02 §2 (SKILL.md "byte-for-byte match"
claim contradicted the reworded AC #4); 017-03's reconciliation cycle
(three SKILL.md spots still said "017-03 ships" / "Today (017-02)" /
"once that ships" after 017-03 *did* ship). Each instance was caught
by an independent reviewer; each was a real defect that the
implementer's own re-read missed.

**Pattern:** when you reshape or reword an AC mid-slice, every sentence
that *consumes* the AC needs an audit, not just the AC text. Sentences
elsewhere in the spec, in adjacent skill files, in the very convention
rule the slice is introducing, in worked-example transcripts — all are
load-bearing references to the pre-reshape phrasing.

**Pre-review checklist (informal):** before requesting implementation
review on a slice with a mid-flight AC reshape or post-shipping
landing, grep the diff for:

- the pre-reshape AC text verbatim, if short enough to grep
- "byte-for-byte" / "matches the hand-seeded" (reshape-specific exact wording)
- "Today (017-NN)" / "Once slice 017-NN ships" / "added in 017-NN"
- "will be added" / "once that ships" / "in a future slice"

If anything pre-reshape survives in the deliverable, fix it before
review. The reviewers will flag it otherwise — cheaper to catch inline.

**Test-driven version:** for SKILL.md / convention-rule files where
the staleness pattern is recurrent, add a regression test that pins
post-reshape phrasing as both *required* and pre-reshape phrasing as
*forbidden*. Example:
`test_worked_examples_section_acknowledges_template_shape` in
`skills/vision-elicitation/test_vision_elicitation_skill_surface.py`
locks "template" required + "byte-for-byte" forbidden in the
worked-examples section body.

**When this matters most:** post-shipping landings (a deferred slice
finally lands; prose elsewhere still describes it as deferred) and
mid-flight AC reshapes (the AC text changes; sentences elsewhere in
the spec / deliverables keep the old wording). Easy mistake to make
twice; explicitly call it out in the slice's deviation log.

## Prefer direct-inventory over behavioral-introspection for skill-routing tests

When testing whether a skill router prefers one skill over another,
asking the model to *behave* and then *self-report* its routing
decision conflates three layers of potential unreliability: routing
decision, output production, and metacognitive accuracy. In slice
012-01's routing-dogfood (deviation §9), three independent sessions
all produced the same wrong report about the available descriptions
— it looked like signal, but was actually three samples of the same
hallucination pattern. The implementer almost applied an AC #9
fallback (disabling auto-trigger) based on the confabulated reports.

**Rule of thumb:** ask the model to enumerate static metadata
verbatim, not to introspect a dynamic decision.

- **Bad** (behavioral self-report): "Which skill would you pick for a
  PR review and why?"
- **Good** (direct inventory): "List the skills you have access to
  with `pr-review` in the name and paste their full description
  fields verbatim."

The direct-inventory question is harder to confabulate against
because it asks for ground-truth enumeration of static metadata
rather than introspection of dynamic decisions.

**Secondary lesson:** when an LLM-based test gives a suspicious
answer, **disambiguate with non-LLM evidence** (terminal `cat`,
filesystem inspection, direct API enumeration) before concluding a
system bug. The 012-01 incident was only resolved when the direct-
inventory question pinned the truth — the prior three sessions had
all been confabulating.

**Applies to:** any AC that says "the skill router prefers X over Y"
or "skill X auto-triggers on phrase Y." Prefer enumeration-based
verification over behavioral-self-report verification.

Surfaced: slice 012-01 deviation §9 (post-merge 2026-05-14).

## Lock surface for cross-worktree synchronization: <git-common-dir>/jig-locks/

Multiple git worktrees of the same project share a single `.git/`
directory (the "common dir"), so `<git-common-dir>` is the only
filesystem path that serializes writes ACROSS worktrees. A naive
`<target>/.jig/locks/` path would only serialize within ONE
worktree — wrong scope for any concurrent-write protection across
parallel sessions.

Pattern: resolve via `git rev-parse --git-common-dir` from target as
cwd; resolve relative paths against target; fall back to
`<target>/.jig/locks/` when not in a git repo. `fcntl.flock` on a
sentinel file in that dir gives kernel-managed lock release on
process exit (no PID-reuse window).

Demonstrated in slice 028-02 (`skills/memory-sync/memory.py` —
`_resolve_lock_dir` + `_file_lock`).

## Python except ordering: first-match-wins, not most-specific

When a subclass exception and its parent appear in adjacent `except`
blocks, the parent's handler catches the subclass UNLESS the
subclass is listed first. Example from slice 028-03:
`class StatusBoardRaceError(WorkflowError)` must be caught via
`except StatusBoardRaceError` BEFORE `except WorkflowError`,
otherwise the parent's exit code (2) wins over the subclass's
intended exit code (4).

This is Python's documented behavior — `except` blocks are evaluated
in order. Most-specific-first is convention, not language semantics.
Worth pinning in mental model when designing exception hierarchies
for CLI exit codes.
