# Learnings

> Dead ends, failed approaches, "we tried X and here's why it didn't work."
> The institutional memory that ADRs don't capture because they're not decisions —
> they're anti-patterns and gotchas discovered in practice.
>
> Update via `/jig:memory-sync` during reconciliation.

## Bug 001: stale-base failures need a branch graph check, not only test output

When review/reconcile tests fail on a long-lived worktree, the first question
is whether the branch contains current `origin/main`. Test output from a stale
base can make already-fixed failures look like current main failures. Surface a
non-blocking `HEAD..origin/main` warning before review/reconcile/land, and
verify against a freshly fetched base before recording "pre-existing on main."

## Bug 003: built-in test runners need explicit first-class signals

Dependency-light projects can use platform test runners without installing a
test library, so dependency/config-only detection silently misses them. Treat a
package manager's test script and runner-native imports as first-class signals:
`node --test` is detected from `package.json` `scripts.test` and shallow
`node:test` imports in both tdd-loop and scaffold-init. For Node selectors,
place `--test-name-pattern` before the file path and normalize TAP `1..0`
missing-pattern output to jig's exit 2 rather than a false green.

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

## Hook-count callouts in docs drift on hook additions
When jig's hook count changes (a new hook ships, or one is removed), three docs still carry explicit numeric counts that need sweeping: `docs/architecture.md` (multiple sites — paragraph + mermaid subgraph title), `docs/memory/glossary.md`, and `README.md`. As of slice 005-03 (2026-05-20), `skills/scaffold-init/scaffold.py:660` was deliberately rewritten count-free ("the jig hooks ... globbing `jig-*.sh`") to remove one drift site, but the three docs above still carry explicit counts because they're prose, not code.

**How to apply:** Before landing any slice that adds or removes a hook script (or registration), grep for the current count + "hook" / "jig hooks" across the docs above and bump in lockstep with the slice's other changes. The hook-script set is canonical via `hooks/scripts/jig-*.sh` glob; the doc counts are mirrors that must be kept in sync manually until/unless someone makes those docs derive from the glob (out-of-scope today).

**Provenance:** Reconciliation reviewer's forward-looking note on slice 005-03 boundary-change-detection. The reviewer verified the slice swept all five sites named in AC #8 (six → seven), but flagged the same drift will need a fresh sweep at any future hook-count change.

## Status-board Notes column: never write `ADR-NNNN`-style placeholders
The Notes column in `docs/specs/README.md` is preserved across `workflow.py status-board` regen (by design — that's where load-bearing per-slice invariants live). The side effect: any placeholder text written before the real value is known will persist silently. Witnessed in slice 036-01: I wrote "ADR-NNNN governs closed-spec drift" into the Notes column at slice-reshape time, before `adr.py new` had reserved ADR-0008. After the regen at close-out, the placeholder was still there until I edited it manually. Rule: do not write placeholder identifiers (`ADR-NNNN`, `SPEC-NNN`, `PR-NNNN`) into the Notes column. Either wait until the real number exists, or use a self-flagging placeholder like `TBD` that's obviously not a real reference.

## `adr.py new` push-refused leaves working-tree-only state with no clear signal
Slice 036-01 implementation: the implementer subagent ran `adr.py new closed-spec-drift-policy`, which created `docs/decisions/adr-0008-closed-spec-drift-policy.md` as an untracked working-tree file with NO local commit and NO push to origin/main. The subagent had no clear error to act on and stopped. Cause: `adr.py new` attempted the push, the push was refused (likely by branch protection — main is protected on this repo), and the function exited without surfacing the refusal in a way the caller could detect. The fallback path (PR mode) didn't trigger either. Reserved number 0008 stayed safe only because no other worktree raced for it. Action items: (1) when invoking `adr.py new` from a subagent, check that the ADR file is committed AND that the push succeeded (or PR fallback fired); (2) consider adding a non-zero exit code path in `adr.py new` when neither the direct push nor the PR fallback succeeds, so the caller sees a hard failure instead of silent working-tree-only state. The second is a candidate refinement-todo if the pattern recurs.

## Amendment-shape patterns from spec 036-02's sweep
Three patterns the craft-review pass on slice 036-02 flagged as `[strength]` worth mirroring in future amendment / sweep work. Captured here so specs 038 / 039 / 040 (and any later closed-spec sweep) can adopt them by reference.

1. **Two-link amendment shape.** When a single drift has multiple causal steps in its history, link them all. Example from spec 016's amendment: the "five → seven hooks" reconciliation links *both* slice 005-03 (six → seven) AND spec 027 (five → six), not just the most recent step. Surfaces full provenance without bloat — a reader who lands on the amendment sees the complete sweep trail in one block. Pattern: `- Link: [<one causal step>](<path>)` per line, one per causal step, ordered most-recent-first.

2. **`subTest` per file for cross-artifact invariants.** When a slice asserts the same structural rule across N files (here: AC #7's "all four amendments use the same `## Amendments` + `### YYYY-MM-DD — ` shape"), wrap the assertion in `unittest.TestCase.subTest(file=...)`. Each failure identifies *which* file broke the invariant — much faster diagnosis than a single combined assertion. Reusable for any future "same-shape-across-N-files" gate.

3. **Structural gate-ordering tests.** When a checklist or pipeline depends on relative ordering (here: AC #6's "**Closed-spec drift** gate must sit before **Commit**"), assert *positions*, not wording. The pattern: read the file once, find the section bounds, locate each gate by its bold-headed pattern, then assert `position(A) < position(B)`. Survives prose polish on the gate text; catches a misplaced gate cleanly. See `scripts/test_closed_spec_drift_sweep.py` lines 194–209 for the canonical form.

**Provenance:** Craft-pass `[strength]` flags on slice 036-02. The two-link pattern was a deliberate scope extension flagged by the compliance pass; the other two emerged from the test-craft review. All three pre-date any tooling that would enforce them — they remain conventions for humans to apply.

## Reserve ADR/spec numbers on origin/main — even from worktrees
Creating an ADR (or spec) file **locally** instead of reserving the number on `origin/main` (via `adr.py new` / `workflow.py new`) risks a **land-time number collision** that forces a renumber + rebase. Incident (2026-05-29): spec 038's `ADR-0010` (tier-gating) was created locally in a worktree because the reserve-on-main flow refuses off-main + dirty/clean-tree constraints made it awkward. Meanwhile another session landed a *different* `ADR-0010` (amendment-scope) + `ADR-0011` (spec-gate) on main. At land time this collided: the tier-gating ADR had to be renumbered to **0012** across 13 files, then the branch rebased onto the advanced main (regenerating the ADR index + status board, hand-checking CLAUDE.md). Cost: a full renumber + conflict-resolution pass that reserve-on-main would have prevented. Mitigation: prefer the reservation flow even from a worktree (`adr.py new --pr` lands a reservation commit on origin/main via PR-fallback when direct push is refused); spec 051 (worktree-aware reservation) is the durable fix. If you must create locally, treat the number as provisional and expect a possible renumber before landing.

**FIXED 2026-06-02 by [ADR-0015](../decisions/adr-0015-worktree-aware-reservation.md) (spec 051-01/02 DONE).** `workflow.py new` / `adr.py new` are now **worktree-aware**: they route on the current branch and no longer refuse off-main. What changed — off `main` (feature branch or linked worktree), the reservation commit is built in an ephemeral **detached** worktree at `origin/main` and pushed by SHA from the project dir; the caller's branch / cwd / working tree are untouched (no clean-tree precondition off-main). The on-`main` in-place flow is unchanged. So the awkward off-main refusal that motivated this entry is gone — run the reservation flow directly from your worktree. (One hardening lesson rode along: push the reservation commit BY SHA from the project dir, never from inside the temp worktree, or repos with a relative `origin` URL break.)

## Worktrees fork off stale local `main` after reserve-on-origin/main — set `worktree.baseRef: fresh`
Flip side of the entry above. `workflow.py new` (and `--push` slice claims) advance `origin/main` but never fast-forward the local `main` *branch*, so a worktree forked from local `main` starts on a stale baseline and silently misses already-shipped specs. Mechanism: the remote-tracking refs (`origin/main` / `origin/HEAD`) are shared across all worktrees of a repo and advanced by every push — so they're never stale; the local `main` branch only moves on an explicit pull/merge. Fix (2026-06-15 dogfood): `worktree.baseRef: "fresh"` in `~/.claude/settings.json` (user-scoped) makes Claude Code's worktree isolation fork each new worktree from `origin/HEAD` instead of local `main`. Verify on a *freshly created* worktree (a pre-existing one predates the setting): `git merge-base --is-ancestor origin/main HEAD` (exit 0 = fresh baseline). Caveat: a known Claude Code regression can ignore `fresh` and fork from local HEAD anyway — if the check fails, park the primary checkout off `main` (`git switch --detach`) so `git fetch origin main:main` keeps local `main` perpetually current. Don't teach `workflow.py new` to advance local `main` itself — that means reaching into the primary's checked-out branch from a worktree (cross-worktree state conflation).

## jig relies on artifact-momentum, not hook enforcement
Diagnosed 2026-06-01: a freshly scaffolded project skipped the workflow + auto-advanced past review, while a mature repo (servo) followed it neatly. Both had the IDENTICAL jig plugin active — the mechanical wiring was never the variable. The real differentiator is content-momentum: servo's populated docs/specs (15+ DONE slices, ADRs, a lifecycle-spelling status board) act as a giant few-shot prompt that pulls the model into the ritual; a cold scaffold has an empty board + a thin template CLAUDE.md that only LINKS to workflow.md. Because jig's hooks enforce nothing about the lifecycle (only conventions.md is gated; the SCAFFOLD_HOOK_PROFILE knob is a documented no-op), the zero-enforcement design only bites at cold-start, where there's neither enforcement nor an example to imitate. Fix shipped: seed a complete DONE worked example (048-05) + a deterministic completion check (048-06). Lifecycle ENFORCEMENT itself remains delegated to spec 045 (review-lifecycle-gates, DRAFT).

## Stale plugin install drifts behind the repo (re-creates removed artifacts)
During the 048 dogfood, the jig:implementer subagent ran from the PLUGIN-INSTALLED copy (~/.claude/plugins/.../jig), which was an older pre-spec-039 version: it wrote .claude/review-queue.json, the transient handoff file spec 039 removed. The worktree repo's agents/implementer.md (post-039) only reports deliverable paths. Result: test_stale_review_queue_file_removed failed until the file was deleted. Gotcha: when dogfooding jig-on-jig in a worktree while the plugin install lags the repo, removed behaviors can reappear via the stale installed agents/hooks/skills. Fix: reinstall/update the local jig plugin to resync; or run helpers from the repo, not the install. Plausibly contributed to the original 'felt unwired' report.

## Markdown scanners must strip fenced code blocks — docs that document a marker match their own examples
Surfaced in slice 048-04 (amendment digest). A scanner that greps `docs/` for a `## Amendments` heading also matches the *illustrative* example that ADR-0008 documents inside a fenced code block (`adr-0008-closed-spec-drift-policy.md` lines 96-108: a `markdown` fence whose caption reads "the above is what a `## Amendments` block on spec 016 would look like"). The first cut of `workflow.py amendments` did exactly this and false-positived ADR-0008 as carrying spec 016's "Hook count: five → seven" override — when only spec 016 has a real amendment. The unit tests missed it because the fixture wrote a *non-fenced* amendment block.

**Fix:** strip fenced code blocks before scanning (`_strip_code_fences` in `skills/spec-workflow/workflow.py` — a DOTALL+MULTILINE regex that removes each fence-open-to-fence-close region), and add a fixture whose `## Amendments` lives inside a fence and must be ignored (`test_ignores_fenced_amendments_example`).

**Generalizable rule:** any tool that greps jig's own markdown for a structural marker (`## Amendments`, `### YYYY-MM-DD —`, status markers) will eventually hit a doc that *documents that marker's format* in a code fence. Strip fences first, or scope the scan to the artifact classes that legitimately carry the marker. The existing `scripts/test_closed_spec_drift_sweep.py` regexes dodge this because they are line-anchored AND run against a fixed file allowlist — a free-roaming scanner has neither guard.

**Why the compliance pass caught it and craft didn't:** the compliance reviewer ran the digest against the *real repo* and read ADR-0008; the craft reviewer validated the parsing logic in isolation against synthetic fixtures. Running new read-only tooling against the live tree (not just fixtures) is a cheap, high-signal review step for any scanner/report.

Provenance: slice 048-04 compliance review (jig:reviewer), 2026-06-01.

## A content-scanning PreToolUse hook blocks the writing of its own test fixtures
Distinct from "the bootstrap paradox for self-enforcing hooks" above (that one is about *timing* — the spec-gate can't gate during scaffold creation). This one is about *content*: `jig-secret-scan.sh` (slice 052-02) is a PreToolUse `Edit|Write|MultiEdit` hook that scans the *pending content* for secret patterns. Once it's registered in `hooks/hooks.json`, it is live in the same session — so an `Edit`/`Write` of its own test file (`test_jig_secret_scan.py`, which must contain AWS-key / PEM / `.env`-secret literals to exercise the block path) would be blocked by the very hook under test, and would also commit a real-looking secret to the repo.

**Fix (two-for-one):** assemble every secret-shaped literal in the test at *runtime* by string concatenation (`"AKIA" + "JKL4MNOP5QRS6TUV"`, build the PEM header from parts) so no contiguous secret-shaped match exists in any source file on disk. The hook never fires on the test file, AND no real-looking secret is committed (which would otherwise trip downstream scanners / CI). The TDD order also helps: write the failing hook-unit-test before the hook exists, so the first write predates the live hook.

**Generalizable rule:** any new PreToolUse hook that inspects *content* (not just `file_path`) must have its test fixtures constructed so the fixtures themselves don't trip it — runtime assembly for secrets, or out-of-band file writes. The deliberate-override env var (`JIG_SECRET_SCAN_APPROVED=1`) does NOT help here: it must be in the Claude Code *process* env, which a subagent's `export` in a Bash call can't set.

Provenance: slice 052-02 implementation + review, 2026-06-01.

## Adding a jig tier skill touches more hardcoded lists than `_TIER_SKILLS`
Adding `security-review` in slice 052-05 exposed the first hidden inventory and
prose mirrors beyond the canonical tier table. Adding `bug-fix` in slice 058-06
exposed two more stdlib-only validator mirrors plus helper rosters and
enumerations that count-pinned tests could not fully protect. The recurring
lesson is that a bundled skill changes a product surface, not just one registry.

The canonical, current checklist now lives in
[CONTRIBUTING § Contributing a bundled skill](../../CONTRIBUTING.md#contributing-a-bundled-skill).
Keep the live flow there rather than duplicating it in this historical note.

Provenance: slice 052-05 implementation + reconciliation, 2026-06-01; updated
from slice 058-06 implementation + review, 2026-06-25.

## Scaffold doc templates render into two install shapes — `${CLAUDE_PLUGIN_ROOT}` paths break in scaffold mode
The `templates/docs/*.md.template` + `CLAUDE.md.template` files render for BOTH
install shapes: plugin mode (machinery stays under the plugin root — the
**default** as of slice 099-01 / [ADR-0041](../decisions/adr-0041-scaffold-defaults-to-plugin-mode.md);
also reachable explicitly via `--plugin-only`) and the in-repo scaffold
(`--in-repo`, machinery copied to `.claude/skills/jig-*`; it was the default only
between slices 016-03 and 099-01). A
`${CLAUDE_PLUGIN_ROOT}/skills/<name>/...` command path in a doc template is correct
for plugin-only but **silently broken in a scaffolded project** — the env var is
unset there and the helper actually lives at `.claude/skills/jig-<name>/...`. A real
scaffold verification (2026-05-27) found the documented stocktake command failing for
exactly this reason; slice 046-01 was the fix. **Fix pattern:** don't hard-code either
shape into the template — render normally, then in scaffold mode apply the SAME
`_rewrite_skill_md_paths` transform SKILL.md bodies already get, gated on
`with_machinery` (`copy_template(..., post_render=...)`); plugin-only passes `None`
and keeps the plugin-root path. **Generalizable lesson:** any new `${CLAUDE_PLUGIN_ROOT}`
reference added to an adopter-facing doc template must survive the scaffold-mode rewrite
(or be install-shape-aware), and generated docs should be tested by *running* the commands
they document inside a temp scaffold, not just asserting on strings.

## Don't cite assistant-memory files (or any out-of-repo path) in checked-in docs
Slice 055 (spec authoring, 2026-06-01) cited a `token-cost-findings.md` "memory file" as the spec's evidence source — but that file lives in the assistant's private memory (`~/.claude/projects/.../memory/`), NOT in the repo. Both review passes (independent reviewers, no prior context) flagged it as a dangling/unverifiable citation: a teammate reading the spec cannot open it. **Rule:** a checked-in doc must be self-contained against the repo — state findings inline, or cite an in-repo artifact (a research doc, an ADR, `docs/memory/`). Never reference assistant-memory or other out-of-repo paths from a spec/ADR/doc. Fix: reworded the citation to inline provenance. Provenance: slice 055-01 compliance + craft review, 2026-06-01.

## Subagents must not `git stash` in a shared-`.git` worktree setup
During slice 056-01's reconciliation a fix-implementer subagent ran `git stash push -- <files>` (a no-op — the slice's files were untracked) then `git stash pop`, which applied an **unrelated, pre-existing stash** belonging to a *sibling* branch (`032-atomic-writes` WIP from `claude/funny-goldberg-828e9e`). Git worktrees **share one stash stack** (it lives in the common `.git`), so `git stash pop` with no arg pops whatever is on top — possibly another worktree's WIP. It left conflict markers + syntax errors in 5 out-of-scope files (`scaffold.py`, `land.py`, two `032` spec files, a staged `memory.py` tweak). The sandbox correctly blocked the subagent from `git checkout`-discarding them; the orchestrator recovered by verifying `stash@{0}` was still intact (pop-on-conflict keeps the stash) and restoring the 5 files to HEAD — no WIP lost.

**Rule:** subagents (and agents generally) must NOT use `git stash` in jig's worktree-per-task setup. To get a TDD red state on untracked files, copy them aside (`cp`) or delete-and-recreate — never stash. **Generalizable:** the stash stack is shared across all worktrees of a repo, so `git stash pop`/`apply` without an explicit ref is unsafe in any multi-worktree workflow. Provenance: slice 056-01 reconciliation, 2026-06-02.

## `.claude/skill-usage.jsonl` has multiple writers — readers must filter by `event`
The same log file is appended to by **three** writers with **different row shapes**: `jig-telemetry.sh` (`PreToolUse`/`Task`) writes Task-spawn rows with no `event`/`skill_name`; `jig-skill-trace.sh` (`PreToolUse`/`Skill`, spec 041-01) writes `{event: "skill_invoked", skill_name, ...}` rows; and `_common/gate_telemetry.py`'s `emit_gate_bypass` (spec 078-01, called from `workflow.py`'s review-evidence gate + the `jig-spec-gate.sh` conventions hook) writes `{event: "gate_bypassed", gate, env_var, ...}` rows. Any reader that wants *skill* invocations (e.g. `workflow.py routing-stats`, slice 041-02, or the recipe in `docs/skill-routing-verification.md`) MUST filter `event == 'skill_invoked'` first; the gate-bypass digest (`workflow.py gate-stats`, spec 078-02) filters `event == 'gate_bypassed'`. A naïve "count every line" miscounts across all three. **Rule:** when adding a writer or reader of `skill-usage.jsonl`, preserve the `event`-tag discriminator; don't assume one row shape. (Spec 078 followed this rule — it added the third writer behind a new `event` value and its reader filters on it.) Provenance: spec 041 (041-01 hook + 041-02 routing-stats), 2026-06-02; third writer added by spec 078, 2026-07-08.

## Hand-maintained 'expected set' constants silently drift — pin them with a consistency test
verify_install._EXPECTED_HOOK_SCRIPTS listed 8 hook scripts while hooks/hooks.json registered 9 (it had silently lost jig-skill-trace.sh). Lesson: any restated 'expected X' constant mirroring a real source of truth drifts unless a test pins it. Fix pattern (spec 047-01): restate-plus-consistency-test — keep the restated constant (needed when the source isn't importable, e.g. install_contract.py is stdlib-only but scaffold.py imports _common.atomic_io), and add a test asserting it equals its source (scaffold._TIER_SKILLS union; the hooks.json-derived set; build_release_zip._EXCLUDE_DIR_NAMES). Where the source IS the registration (hooks.json), derive from it directly. Matches the pre-existing _EXPECTED_DENY_GLOBS / _EXPECTED_GITIGNORE_* pointer-comment convention — 047 added the missing tests.

## In a jig project the spec/slice IS the plan — skip generic plan mode
Reaching for Claude Code's generic plan mode (a ~/.claude/plans/*.md file) for spec work creates a parallel artifact that competes with the spec/slice and splits the source of truth. The slice file already carries Goal/DoR/AC/DoD. Drive the lifecycle (workflow.py transition -> implementer subagent -> review passes -> reconcile) and fold any design steer into the implementer's prompt, not a separate plan doc. Surfaced (and corrected) mid-session when starting spec 047.

## Scaffold SKILL.md: 046-01 rewrites helper bash paths, NOT markdown doc-links
When validating a scaffolded target (spec 047-02 AC #4), do NOT flag copied SKILL.md '../../docs/...' markdown links as broken. Spec 046-01's _rewrite_skill_md_paths rewrites only ${CLAUDE_PLUGIN_ROOT}/skills/<name>/ bash *helper* paths to local .claude paths — it deliberately leaves markdown doc-links pointing at source-plugin docs. A scaffolded SKILL.md lives at .claude/skills/jig-*/, so '../../docs/...' resolves to .claude/docs/... (absent); scanning those would false-fail every scaffold. So: scope the doc-link smoke check to the target's OWN docs (docs/**, CLAUDE.md) and check SKILL.md bodies only for broken helper *commands* (the load-bearing rewritten paths). The dangling SKILL.md doc-link is a known 046 non-rewrite (inbox follow-up).

## Runtime code in dev-only `scripts/` is invisible to the release zip

`build_release_zip.py`'s `_INCLUDE_ROOTS` ships only `.claude-plugin/agents/skills/hooks/templates` — top-level `scripts/` is dev-only and excluded. But scaffold-init's closing completion self-check (slice 048-06) imports `verify_install` (→ `install_contract` + `scaffold_contract`) from `<plugin-root>/scripts/` at install time. Result: every *packaged* plugin install (desktop-app zip / marketplace zip-release) scaffolded fine, printed `scaffolded …`, then crashed with `ModuleNotFoundError` on the closing report. A git-clone install (`~/.claude/plugins/marketplaces/jig/`, full tree) hid it — `scripts/` is present there, so it only bit zip installs.

**Why no test caught it:** every test imported the verifier with the repo's `scripts/` on `sys.path`, and even the release-zip `smoke_test` imported `verify_install` from the *source repo*, not the *extracted* tree — so none simulated the packaged, `scripts`-less layout.

**Fix (no spec — bug-shaped):** `_INCLUDE_SCRIPT_FILES` allowlists exactly the three runtime modules into the zip under their original `scripts/` path (dev tooling stays out); the import is guarded (degrade to a one-line note, never crash, but a genuine FAIL still surfaces); and `PackagedVerifierImportTests` extracts the built zip and imports the verifier from the *extracted* tree in a clean subprocess.

**Generalizable lesson:** if a shipped component (skill/hook) imports a module at runtime, that module must live under a distributed root (`skills/`, `hooks/`, `agents/`, `templates/`) — or be explicitly allowlisted into the release. `scripts/` is dev-only. And package-footprint tests must exercise the *extracted artifact*, not the source repo, or they validate the wrong tree.

Discovered: 2026-06-07, user-reported scaffold crash on a v1.10.0 zip install.

## Spec slice headings + dependency tokens must use the NNN-MM shape
The RECONCILED→DONE dependency gate (workflow.py _validate_dependencies / _lookup_slice_status) only resolves 'adr-NNNN' and the 'NNN-MM' slice fragment, and it matches NNN-MM as a SUBSTRING of the slice's heading label. So a slice heading must be '## Slice NNN-MM — name' (as in 045/060/031), NOT the short '## Slice 0N — name'; and 'dependencies:' must list 'NNN-MM' tokens, not 'slice-NN'. Spec 064 was authored with both wrong — latent until the first slice depending on a sibling (the spike 064-01 only depended on adr-0020, which resolved fine). Symptoms at the DONE gate: 'unknown dependency token shape' then 'slice not found in any spec'. Fix is mechanical (rename headings + tokens across the spec's slices). Gotcha: renaming a heading re-keys the status-board Notes column, so re-add Notes after 'workflow.py status-board' regen.

## Don't treat a sibling repo's README as ground truth for your own repo's behavior
Drafting ADR-0022 (jig<->servo oracle boundary), I asserted jig's `slice-land prepare` "already emits servo pull-hints" and marked it *verified* — but that came from *servo's* README describing what it expects jig to do. A grep of jig's `skills/` (2026-06-09) found no such code; the pull-hint does not exist (land.py's only "hint" is a git-rebase recovery message). An independent frame-critique caught it. Lesson: a cross-repo behavioral claim about repo A must be verified against repo A's *actual code*, never against repo B's docs describing A — the other side's README is intent, not implementation.

## 'Integrate on signal' deferrals mean demand (real cases), not supply (a tool now exists)
ADR-0019 deferred a jig<->EDD eval interface "until signal", and its deferred-enhancements section named the signal precisely: ">=2 eval-oracle refactors where the attest-only posture proves too loose" (demonstrated DEMAND). ADR-0022 mis-read "the signal has arrived" as servo merely *existing* (SUPPLY); an independent frame-critique flagged it premature — it would ship the binding for the deterministic path (where servo is actually *weaker* than jig's existing tdd.py machine-witnessing) while the motivating eval path stays unbacked (servo spec 006 DRAFT). Lesson: when acting on an "integrate on signal" deferral, re-read the original deferral's stated trigger — a tool becoming *available* is not the need being *demonstrated*. ADR-0022 was parked as a result.

## Some test files are runner-only — they can't run standalone
Several test modules (e.g. `skills/spec-workflow/test_workflow.py`, the `NewSpecScaffoldsFilePerSliceTests` class) load the module-under-test via `importlib.import_module("skills.spec-workflow.workflow")` / `import skills`, which needs the **repo root on `sys.path`**. `scripts/run_tests.py` sets that up; running a single file directly (`python3 skills/.../test_workflow.py`) or under bare `pytest` yields confusing `ModuleNotFoundError: No module named 'skills'` for exactly those tests while the rest of the file passes. Lesson: run the suite via `scripts/run_tests.py` (the canonical runner) — a standalone `ModuleNotFoundError: No module named 'skills'` is a runner-context artifact, not a real failure, and is **not** grounds to "fix" the test. (Surfaced reviewing spec 068-02; the 4 standalone errors pass cleanly under the runner — full suite 2580 OK.)

## `workflow.py transition` takes the spec.md path, never a slice-file path

`transition <spec> <slice-fragment> <status>` resolves the slice via `load_slice`, which **also** accepts a slice-file path directly (dual-read) — so passing `docs/specs/NNN-slug/slice-NN-*.md` *looks* like it works (the status write lands on the right file). But the post-write `_write_spec_rollup(spec_md)` (slice 030-01) is then handed the **slice file as if it were `spec.md`**: it runs `compute_spec_status` over that file's single `## Slice` section, rolls the "spec" up to **IN_PROGRESS** for any active slice state, and **overwrites the slice's own just-written `status:`**. Net effect — every transition silently collapses to IN_PROGRESS. It's *masked* on the way up (DRAFT→…→IN_PROGRESS all roll to IN_PROGRESS anyway) and only bites when you try to reach REVIEWED / RECONCILED / DONE, where the rollup reverts the intended status right after the transition reports success. Always pass the **`spec.md`** path + a fragment (`load_slice` finds the sibling slice file) — then the rollup targets the real `spec.md` (correct: the spec stays IN_PROGRESS while a slice advances) and the slice file keeps its status. Hit dogfooding spec 068-03 (2026-06-10); re-running with `spec.md` fixed it. A defensive guard (refuse a slice-file path, or derive the spec.md from `loc`) is a candidate follow-up.

## Semantic-index overlays are exact provider permissions
Spec 080-01 established that semantic-index internal overlays must be authorized per provider: allowed_overlays=["scout"] enables Scout, allowed_overlays=["other"] does not, and allowed_overlays=[] must override legacy internal_overlays. Host adapters should preserve providers={} as an explicit empty registry rather than falling back to built-ins.

## Reconcile-checklist additions require both workflow.md and SKILL.md
When adding a new reconciliation checklist item, BOTH docs/workflow.md (Reconciliation rules section, human-readable) AND skills/spec-workflow/SKILL.md (## Reconciliation checklist, the operative gate agents walk) must be updated. Updating only workflow.md leaves the forcing function absent from the checklist that reviewer subagents and spec-workflow drive. Caught by compliance reviewer on spec 083-01.

## Scaffold helper-closure: a helper referenced from tier-0 surfaces must live in a tier-0 skill
A SKILL.md or scaffolded doc that references `${CLAUDE_PLUGIN_ROOT}/skills/<name>/<helper>.py` must point at a skill that is actually in the default (tier-0) scaffold — the scaffold-verify **helper-closure** + **docs** checks resolve every such local-helper path against the scaffolded set and fail (exit 4) otherwise. Bit during 083-05: `decisions.py` was first placed in tier-1 `adr-workflow` but referenced from the always-scaffolded memory-sync prompt + `lightweight-decisions.md` → ~237 cascading test errors (every test that calls `scaffold_project` in setUp). Fix: put the helper in a tier-0 skill (memory-sync). Always-scaffolded docs can only safely reference tier-0 helpers.

## docs/architecture.md hook inventory is a restated constant — update it when adding a hook
The hook-spine subgraph in docs/architecture.md hardcodes the hook count ("Deterministic spine — N hooks"), a per-hook node diagram (h1..hN), and a prose count ("via N hook scripts" + the inject/block/async categorization). It is a RESTATED CONSTANT of the same class as verify_install._EXPECTED_HOOK_SCRIPTS + test_install_contract's count assertion. Adding/removing a hook means updating ALL of: hooks.json, _EXPECTED_HOOK_SCRIPTS, the install-contract count test, AND architecture.md (count + diagram + prose). The install-contract guards fire on drift; architecture.md has NO test guard, so it silently goes stale (caught only by reconciliation review in 083-07). Treat architecture.md as an 'updated' reconciliation target on any hook change, never 'no-op'.

## Hook-safe / contract modules must not import project_layout
`skills/_common/lexicon.py` and `scripts/verify_install.py` must stay STDLIB-ONLY. lexicon is run by the memory-scan hook via `python3 -c` (no package root on sys.path; enforced by `test_stdlib_only_no_third_party_imports`), and verify_install is a release-trio contract script that never imports jig internals. When making them layout-aware (spec 084), do NOT `from _common import project_layout` — inline a tiny fail-soft `docs_root` read from scaffold.json instead. Gotcha: the per-module `python3 test_x.py` PASSED while the full `run_tests.py` suite caught the violation (test_hooks + the stdlib-only test went red) — always run the full suite after touching a shared _common module.

## Bug 002: lifecycle registries need cross-discovery from both front doors
When adding or changing a first-class lifecycle registry, update the other
workflow's front door too: live status board preambles, scaffolded board
templates, loaded primer key-document rows, and the authoring procedure in the
peer skill. Bug 002 showed that documenting `docs/bugs/` only inside
`bug-fix` left spec authors working from `docs/specs/README.md` and the primer
blind to existing defect records, causing duplicate/contradictory ownership.

## Mirroring a lifecycle state's mechanism ≠ mirroring its semantics
When slice 085-01 added ABANDONED by mirroring DEFERRED's mechanism (restricted outbound edges, rollup exclusion, own status-board section), five rounds of frame-critique found the surface-level mirror masked real semantic divergences: (1) DEFERRED's unrestricted inbound edges (any state, including DONE) don't automatically transfer — DONE->ABANDONED conflates 'never attempted' with 'shipped, then removed', two events with different audit value; (2) DEFERRED's 'no cascade to dependents' precedent relied on spike Outcome prose never tripping the hard DONE dependency check, which doesn't hold for a permanent state like ABANDONED; (3) widening a function's documented return-type (compute_spec_status: 3 values -> 4) needs an actual audit of every consumer, not just an appeal to how DEFERRED handled a narrower case (pure exclusion, never a new return value). Lesson: when extending an existing mechanism to a new-but-different concept, treat each inherited behavior as its own claim to verify, not a free pass by analogy.

## Bug 004: terminal lifecycle states need status-board segregation, not just a distinct status word
A correctly-terminal state (`ESCALATED`/`RESOLVED_ON_MAIN`) read as "unfinished"
across sessions because `bug.py`'s `_render_board` rendered every row in one
flat table — the only closure signal was one word in the status column, and the
blank fix/test columns pattern-matched as open work. The spec board had already
solved this (`render_deferred_table`/`render_abandoned_table` split out
`DEFERRED`/`ABANDONED`); the bug board never inherited the pattern even though
`OPEN_STATUSES` already encoded the open/closed seam. Lesson: when a lifecycle
registry gains a terminal-but-not-success state, giving it a status *value* is
not enough — the surfaced artifact (status board) must make closure legible by
segregating those rows, at parity with peer registries. Keep `DONE` (terminal-
*success*) in the active table; only the "closed, not completed" states need the
separate section. Tooling gotcha hit while fixing this: `.jig/test-command`
(`python3 scripts/run_tests.py`) ignores any appended test selector and runs the
FULL suite + a `uvx pyright` gate, so `bug.py transition FIXING/REVIEWED` runs
the whole repo suite (~4min, network on first pyright fetch), not the named
regression test in isolation — the red→green teeth are repo-wide here; warm the
pyright cache and budget minutes.

## Spec 086: an adversarial frame-critique catches metric-gradient bugs the deterministic gates can't
Spec 086 added a deterministic Tier-2 skill-routing eval (`scripts/skill_routing.py`)
— TF-IDF cosine over SKILL.md descriptions for collision + trigger-routing. The
first cut vectorized the *whole* description, including the shared negative-
disambiguation boilerplate ("Do not use for … use `/jig:X` instead", "Defers to
…"). The adversarial **frame-critique** pass (064-03) caught what the compliance
and craft passes did not: that boilerplate is exactly what teaches the *model* to
route siblings apart, so counting it as lexical *similarity* **inverted the
metric's gradient** — the correct fix (add a pointer) would *raise* the collision
score while the rewarded move (strip it) degrades real routing. Fix:
`routing_surface()` vectorizes the **positive surface only**. Effect: top
collision 0.44→0.22, rank-1 93→95%, negatives 97→100% — the fix validated the
diagnosis. Lessons:
1. For a lexical similarity/routing metric over jig descriptions, vectorize the
   **positive** surface; the disambiguation tail is shared scaffolding that
   inverts similarity among the hardest-to-route cluster.
2. The frame-critique earns its cost on **premise** bugs a conformance review
   steps over. It took 3 cycles (gradient inversion → Overview overclaim →
   inoperable kill-criterion), each a distinct real finding — not doubt-theater.
3. A self-authored eval measures author *self-consistency*, not ground truth:
   green catches *regression against the pinned case set*, NOT "vocabulary real
   users say." Scope the claim honestly; the durable fix (real-usage-sourced
   prompts + a semantic Tier-3 eval) is deferred in refinement-todo.
4. `.claude/skill-usage.jsonl` logs only which skill *fired* — not the prompt or
   correctness — so `routing-stats` cannot detect a mis-route. Kill criteria that
   need mis-route detection are **manual**, not automatic, until the trace hook
   captures the invoking prompt.

## Bug 005: a Markdown-parsing gate must accept every shape the docs invite — and be precise about structure
The diagnose gate (`bug.py:_diagnosis_gaps`) counted candidate hypotheses with
`line.strip().startswith("-")`. That single line was both **too narrow** (ordered
`1.` and `*`/`+` bullets counted as zero — a false negative that hard-blocks
gnarly tier) and **too loose** (stripping indentation let nested `- Confirm:` /
`- Falsify:` sub-bullets count as top-level hypotheses — a false *positive* that
green-lit records with zero real hypotheses). Neither `SKILL.md` nor the record
template ever stated the dash-bullet/`[x]` convention, so good-faith records
failed. Fix: `_top_level_list_items` matches every Markdown marker but only at
`indent < 2`; `_has_leading_marker` accepts `[x]`/`(leading)`/`Leading:`; the gap
messages name the shape; the template ships a worked example. Lessons:
1. A machine-checked gate over free-form Markdown must be **liberal in what it
   accepts** (all list markers, all documented leading tokens) yet **precise
   about structure** (top-level only) — the same rewrite fixes both a false
   negative and a false positive.
2. When a false negative's only escape is a **total bypass**
   (`JIG_BUG_DIAGNOSE_GATE=0`), a cosmetic parse nit pressures users into
   disabling a real safety gate. Precision keeps the gate credible.
3. A presence/shape gate and its scaffold must teach the same shape — put the
   convention in the **template** and in the **gate message**, or the
   machine-checked shape and the human-taught shape drift apart.
4. Scoped out (logged to `docs/inbox.md`): `_section`'s exact-match heading regex
   is the same class of fragility (`### Hypotheses`, `## Hypotheses (…)`, and
   `## Hypotheses` inside a fenced code block all read empty) but it is a shared
   helper — widen it in its own change with its own tests.

## `## Assumptions` is a frame_review sentinel — bare `None`, not "None + explanation"
`workflow.py frame-review-needed` derives `frame_review: true` from the spec's
`## Assumptions` body via `_assumptions_are_real`: it skips only fully
emphasis-wrapped stubs and lines whose *whole* content is a bare placeholder
token (`None`/`TBD`/`TODO`/`N/A`). A line that merely *begins* with "None" but
continues with prose ("None — every claim was verified …") counts as a **real
assumption** (deliberate, per the 064-04 craft fix that stopped a first-token
heuristic from false-negativing real assumptions like "None of the dates are
tz-aware"). Consequence (spec 087): listing *probe-verified premises* as bullets
under `## Assumptions` — even under a "None." lead — flips `frame_review` on and
drags in the adversarial frame-critique pass for a low-risk change. Fix: put
verified facts in a `## Current state (verified)` section and keep `## Assumptions`
a bare `None.` when there are no *unverified* load-bearing claims. Lesson: the
risk-gate is for **unverified** assumptions only; verified facts are grounding,
not assumptions, and belong elsewhere or the trigger over-fires.

## Bug 006: normalize permissive path aliases without erasing validation
When a command accepts a canonical overview path but child lookup also makes a child-file path appear valid, normalize once at the command boundary before downstream writes. Validate the original caller-supplied path before normalization; otherwise a typo can be reinterpreted and mutate a different artifact selected by a secondary fragment. Test both the successful alias and fail-before-mutation typo path.

## Tier-gated packaging contracts need exact sets
When plugin packaging recursively ships every public skills/*/SKILL.md but scaffold copying is gated by _TIER_SKILLS, checking only EXPECTED_SKILLS ⊆ present permits accidental plugin-only skills. Validate both directions: the public skill set must exactly match the tier-derived contract, excluding private _... infrastructure. See bug 007 and GitHub issue #89.

## Bug 009: host-normalized skill description limits
When validating SKILL.md metadata, enforce host limits on the normalized value the host checks. Codex applies split_whitespace().join(" ") to YAML description text before its 1024-character limit, so raw source length and YAML chomping semantics are not the contract. Keep every public description comfortably below the cap and validate the generated package.

## Bug 012: an init-time-only seed is a permanent gap for every existing project
`scaffold-init`'s template walk runs at init and cannot be re-run on a scaffolded
project, so anything it is the *sole* seeder of silently never reaches projects
that adopted jig earlier — and a helper that refuses to create what it needs
("scaffold it first") converts that gap into an unrecoverable dead path. Two
consequences worth generalizing. First: **any new scaffolded artifact needs a
backfill op from day one**, or every existing project is excluded by construction;
`migrate.py` is where that lives. Second: **an error message that states a fact
without naming a remedy is the actual defect.** The reported project's agent was
handed a path with no shape, invented an LD table, and `decisions.py` refused it
forever — zero successful writes across the repo's entire jig lifetime, with no
signal. A nudge that names only a destination will get a format invented for it.
Related: a helper's template lookup is host-shaped — `templates/` ships in both
plugin packages and in Codex scaffold mode, but *not* in Claude scaffold mode
(`copy_machinery` omits it), so `parents[2]/templates/` is reachable in three of
four install modes and `adr.py` inherits the same gap.

## Bug 010: Node default discovery needs no directory operand
Runner adapters must preserve the distinction between an implicit project target and an explicit test path. Node test default discovery is cwd-based: bare `node --test` discovers the suite, while a positional directory is treated as a module entry point and can fail with MODULE_NOT_FOUND. Keep explicit file/path and name-selector behavior covered separately.

## Bug 011: correct withdrawn prose by sweeping, not by chasing cited lines
When a fix withdraws a documented rationale, correcting only the lines a reviewer names leaves siblings behind — a stale `spec.md` constraint survived three consecutive review passes that way. Grep the withdrawn *phrasing* across `docs/` instead (here: "repeat runs stay quiet", "dedup-against-recorded", "until recorded", "then pruned"). Two traps make this worse than ordinary doc drift: prose under a heading like "Design constraints (locked in, all phases)" reads as binding and can license re-introducing the bug, and `workflow.py status-board` *preserves* the Notes column across regeneration, so a stale note there never self-corrects.

## Bug 013: a field's meaning lives in its readers, not its writers
Three lessons from one gate, in ascending order of how easy they are to repeat.

**A regex that both gates and transforms exports the transform's strictness
into the gate**, where it reads as an arbitrary format rule. `cmd_accept`'s
pattern legitimately needed an exact `Proposed (YYYY-MM-DD)` match to *rewrite*
the line, and that requirement leaked into the *decision to proceed*. When one
pattern serves both roles the tolerant read and the exact rewrite want different
patterns — and a comment claiming otherwise ("or with extra trailing content",
never true) is the tell that the two roles were never separated.

**Do not infer a field's semantics from its provenance.** Fixing this bug, the
implementer needed an acceptance date, found that only `cmd_accept` writes
`last_verified` in code, and concluded it *is* the acceptance date. It is not: it
is a freshness stamp. [ADR-0024](../decisions/adr-0024-reference-reframe.md)'s
`reaffirm` disposition refreshes it as a documented judgment step (no code path
to grep), `workflow.py`'s staleness check reads it as "verified N days ago", and
eight prose-`Proposed` ADRs already carry a filled value. The grep answered
"who writes this?" while the question was "what does this mean?" — and a field's
contract lives in its defining ADR and in what *reads* it. The near-miss cost:
a plausible wrong date published in the README index and offered to a human to
write into an immutable record. **A plausible wrong value is worse than an
absent one**, because nothing about it looks wrong; the diverged index entry now
publishes no date at all.

**Run the remediation command you print.** The refusal message told the operator
to recover the date with `git log … -- <basename>`. Git resolves pathspecs
relative to cwd, so from a repo root it matched nothing and exited 0 — output
indistinguishable from "there is no such commit". An error message is a
deliverable; an unexecuted one is an untested code path with a human on the
other end.

**Process note:** the frame-critique earned its cost here, but only because it
ran four times. Rounds 1–3 each found something verifiable, and round 2 refuted
round 1's *fix* rather than the original design — an adversarial pass is worth
re-running against your own repairs, not just against the initial draft.

## Bug 014: a partial signal teaches a total inference
A mechanism that answers a *narrow* question reliably will be read as answering
the *broad* one — and the working cases are what make the misreading stick.
`claimed_by:` honestly meant "who is implementing this slice"; every reader
generalized it to "jig tracks who is working on what", because it was correct
every single time they checked. It looked reliable right up until it silently
wasn't, which is worse than having no marker at all: nothing prompts you to
doubt a signal that has never yet been wrong in front of you.

Three things generalize. First: **when one system produces a signal and another
routes decisions on it, the coverage limit must be written where the reader is,
not where the writer is.** Spec 049 documented its `IN_PROGRESS`-only scoping
precisely and correctly — in spec 049. `orient`, the status board, and the
pickup flow never repeated it, and they are what an agent actually reads.
Second: **the phase with the heaviest writes deserves the strongest signal, and
lifecycle machinery tends to give it the weakest** — the claim was deliberately
*cleared* on entry to `REVIEWED`, i.e. immediately before reconciliation, the
single biggest write phase jig has. Check the ordering whenever a marker is
released on a state change. Third: **absence-of-record is not evidence-of-
absence, and prose must say so out loud.** jig's own `collect_slices` docstring
called an empty field "unclaimed"; that one word is the whole bug in miniature.
The fix now states, in the docstring and in both skill surfaces, that blank
means *no claim recorded* — unpushed claims are invisible and plain `Edit`
writes take no claim, so blank can never mean free.

**The sharpest lesson is about the fix, not the bug: widening a signal can
invert the very defect it was meant to close.** The first cut stamped every
non-terminal state, including the two the pickup flow tells readers to choose
work from. That left the spec author's branch name on slices that were now free,
so the board labelled available work as owned and the routine
author→implementer handoff warned every single time. "Blank reads as free" became
"residue reads as occupied" — same surface, same class, sign flipped. The rule
that fixes it generalizes: **classify lifecycle states by whether a session is
DOING something there or the item is QUEUED for whoever comes next, and only mark
the first kind.** Marking a queue is what produces false occupancy, and a warning
that fires on the most routine path trains readers to ignore warnings. A
corollary for reversals: check whether a recorded non-goal makes *more than one*
claim before rebutting it — spec 049's said both "browsing doesn't reserve" and
"no claim on READY_FOR_IMPLEMENTATION", and rebutting only the first missed that
the real objection is *the actor is not the future worker*.

Process notes. Reversing a recorded non-goal makes pre-existing tests fail
*correctly* — that is the design conversation surfacing, not breakage — but
rewriting them is legitimate only with the reversal recorded first (ADR + spec
`## Amendments`); and the count of inverted tests is a useful proxy for how big
the reversal really is (ours fell from four to two once the design was narrowed).
Three separate over-reaches all came from the same root: **widening a marker,
widening the blocking that shares its condition, and widening the machinery that
consumes it are three decisions, not one.** The suite caught the first (a session
could no longer move its own slice out of `IN_PROGRESS`); review caught the
second (the trunk reservation still hardcoded one status, and later still
overwrote a foreign trunk claim silently); and the third only surfaced when a
reviewer asked what *reads* the newly-written field — the answer was nothing, so
the docs' promise of cross-worktree visibility was untrue until a read path was
added. When widening a write, always ask what consumes it.

**A batched edit script's per-step log is not evidence the edit landed.** Two
regression tests were recorded in the bug record as pinning a fix, and neither
existed: the script that added them raised on a *later* assertion and returned
before its single `write_text`, discarding every earlier substitution — after
already printing `ok: <step>` for each one. Per-step logging plus
all-or-nothing writing makes partial failure look exactly like success. It
happened twice in one session. **Verify by grepping for the artifact
(`grep -c '<test name>' <file>`), never by trusting the script's own echo** —
and for a guard, go further: remove each conjunct, re-run under `python3 -B`,
confirm red, restore. Both refusal conjuncts here were unpinned; the suite stayed
green with either deleted, which no amount of "the tests pass" would have
revealed. This compounds the [[mutation-testing-pycache-false-negative]] trap:
a test that cannot fail is worse than a missing test, because the record then
cites it as evidence.

**A cross-host transform is only ever tested by the non-default host**
(bug 015). `brief.md` and the seed spec were rendered through paths that never
received the Claude→Codex host transform, so a Codex project's two
first-read documents told the user to open `CLAUDE.md` — a file only Claude
projects have. Both paths were added over time and each simply forgot the hook;
`_emit_seed_spec` even built its own *narrower* transform, which reads as
deliberate and is easy to approve in review. Nothing caught it because the
Claude host is the identity case: on the host every contributor runs,
untransformed text is already correct. Host-parity assertions have to be
written on purpose — they will never fall out of ordinary development.

Two corollaries from the same bug, both cheap and both general:

- **A docstring that reassures on a neighbouring axis suppresses the question
  you needed asked.** `_emit_seed_spec` promised its templates "never leak
  `${CLAUDE_PLUGIN_ROOT}` or source-checkout paths" — true, and about *paths*.
  Anyone checking whether the seed needed the host transform found an
  authoritative-sounding "this is fine" that did not cover *vocabulary*.
  Reassurance should name its axis.
- **When a fix reuses an existing hook, check what else flows through that
  hook.** The obvious fix here (`post_render=doc_rewrite`) resolves the symptom
  and corrupts user data: `copy_template` substitutes *before* post-rendering,
  and the Codex transform does a blanket `Claude` → `Codex` replace, so a
  project directory named `Claude-Tools` is emitted as `Codex-Tools`. That is a
  live, separate defect on the primer path ([[jig-bug-016]] — filed, not fixed);
  the 015 fix avoided inheriting it by adding a `pre_render` hook that runs
  before substitution. A guard test pins it, proven by a single-variable
  variant: switching only the brief back to post-substitution turns it red.

**`isatty()` answers "is this a terminal", never "is there input waiting"**
(bug 017). `record-review` guarded a `sys.stdin.read()` fallback with
`if not sys.stdin.isatty()`. That splits three real cases into two: a terminal
(skip), a closed stdin (`""` immediately), and **an open pipe nobody ever
closes — which blocks forever**. A human at a prompt is always the first case;
an agent harness and most CI runners are always the third. So the failure
appeared only where nobody was watching, and jig's whole suite could hang for
13+ minutes on a ~100s run while the bug "never reproduced by hand". That
signature is itself the tell: **a defect that only shows up when a human is not
driving points at a terminal-shaped assumption.** The fix removed the branch
rather than bounding it — `--summary-file -` is now the only route to stdin —
because a timeout or a readiness poll would have kept behaviour forking on what
stdin happens to be.

Two corollaries worth keeping:

- **Don't use one property as a proxy for another.** `isatty()` was standing in
  for "input is available", which no syscall on a pipe can answer without
  either blocking or racing. When the question can't be asked, make the caller
  state the answer (an explicit flag) instead of guessing.
- **The obvious regression test proves nothing here.**
  `subprocess.run(stdin=subprocess.PIPE)` closes the write end immediately, so
  the child sees EOF and exits — it passes against the *unfixed* code. Only
  `os.pipe()` with the write end held open by the test reproduces it. One wrong
  repro of exactly this shape briefly appeared to *disprove* the bug. Compare
  [[mutation-testing-pycache-false-negative]]: when a test passes sooner than
  expected, suspect the harness before believing the result.

## Bug 018: a restated contract is a contract that will drift — and a host parameter needs a fixture per host

`copy-machinery` converts a plugin-mode project to in-repo. A project's mode
lives in three places — the machinery on disk, `scaffold_mode` in
`scaffold.json`, and the helper paths its rendered docs cite — and the command
updated only the first. The original defect was not a regression: **spec 099-01
advertised `copy-machinery` as the plugin-mode recovery route by writing one
summary line, widening a contract the callee was never told about.** No test,
review, or diff on either side had cause to ask whether the command did what it
was now being sold as doing.

The instructive part is what happened next.

**The same failure recurred inside the fix for it, a few hundred lines later.**
The fix's docs half searched for the single literal `${CLAUDE_PLUGIN_ROOT}`.
Codex renders its plugin-mode docs against `${PLUGIN_ROOT}`, so the scan
returned empty for every Codex project: the mode flipped, no advisory printed,
and the shipped Codex `SKILL.md` promised those users a warning they would never
see. The Claude-only literal was a *restatement* of a constant that already had
an owner (`CodexScaffoldRenderer` / `ClaudeScaffoldRenderer`). Writing the
"widened contract" learning into this very record did not prevent repeating it.

- **Structure beats vigilance.** The fix is now
  `scaffold.renderer_for_host(host).PLUGIN_ROOT_PREFIX` — read the host's
  spelling from the host, so there is no second copy to go stale. A per-host
  constant living in a *consumer* module is a contract restatement, and
  restatements drift silently: nothing fails, the feature just stops happening.
  When you catch yourself writing a lookup table keyed by host/mode/variant,
  check whether the thing you are keying on already owns that answer.
- **A parameterized path needs a fixture per value, or the untested value is a
  guess.** The function threaded `resolved_host` all the way through and looked
  fully covered at 15 green tests — every fixture was a Claude scaffold. Half
  the supported hosts were never exercised. The reviewers found it; the suite
  could not.
- **Two of those 15 were passing without testing anything**, in the specific way
  that is hardest to see: the assertion was true for a reason unrelated to the
  code under test. `test_copied_machinery_is_not_reported_as_stale_user_docs`
  ran on a default-`docs_root` project where `.claude/` is outside the scan root
  *structurally*, so deleting the entire skip-set left it green. A negative
  assertion needs a fixture where the positive case is actually reachable.
- **Never read an exit code through a pipe.** `cmd | tail` reports `tail`'s
  status. This record spent a full cycle asserting the suite failed on a known
  flake when it exits 0 and the alarming `ERROR: committed host packages are
  stale…` text is *expected output* from `DriftCheckTests`, which induces drift
  on purpose to assert the message shape. Redirect to a file and check `$?`, or
  use `PIPESTATUS`. See also [[jig-ci-check-needs-pipx]].

Process note: neither required review pass (`bug-review`, `craft`) was recorded
before the first fix merged as `dd0d350`. Both were run retroactively in
[#150](https://github.com/ramboz/jig/pull/150) and both returned
`needs-changes`, which is how the Codex gap surfaced — after shipping. The
`→ REVIEWED` evidence gate is what would have caught it before.

## Bug 019: a resolver that returns half its answer makes every caller guess the rest

`_common.parsing.load_slice` resolves both *what* a slice is called and *which
file it lives in*. `review.py`'s wrapper returned the label and dropped the
path. With the location gone, seven prompt builders had nothing left to name
but `spec_path` — so all seven sent the read-only reviewer to `spec.md`, which
under file-per-slice contains none of the acceptance criteria, deviation log, or
reconciliation sweep it was being asked to verify. **When a lookup computes two
facts and a wrapper discards one, the discarded fact gets re-invented downstream
as a guess.** Return the whole answer, or the abstraction is a lie by omission.

Two generalizable points:

- **A defect that a human driver silently corrects is a defect only unattended
  runs pay for.** Interactively you notice the path is wrong and retype it; the
  session succeeds and nothing gets filed. The same prompt handed to an
  unattended reviewer — explicitly told not to look beyond the files it is
  pointed at — returns a confident verdict about the wrong file. **Anywhere a
  human-in-the-loop routinely patches output by hand, put a test**: the loop is
  hiding the bug, not fixing it. Bug 017 above reached the same rule from the
  opposite direction — a defect visible only when nobody is driving. Two
  independent bugs, one signature: **"never reproduces by hand" is a clue about
  the observer, not a verdict on the bug.**
- **When two layouts coexist, render the difference in exactly one place.** The
  fix is one `_slice_source()` that decides how the reading target is phrased;
  the builders interpolate it. Seven independently-worded `## What to read`
  entries were seven chances to get the layout wrong, and the eighth builder
  would have made it eight.

The dual-layout support itself was never broken — `MixedLayoutResolutionTests`
proved the *label* resolved correctly in both layouts, and that green test read
as coverage of the feature. **Asserting that the right thing was found is not
asserting that the right thing was reported.**


## Bug 022: a default is a decision, and reuse inherits a contract

`scaffold.copy_machinery` grew a `docs_root` parameter in spec 084 with a
default of `"docs"`. Spec 084 updated the greenfield caller and missed the
other one, `migrate.copy_machinery` — so `migrate copy-machinery` wrote its two
managed `workflow.md` blocks into a hardcoded `docs/` on every project,
correct for the majority and wrong for exactly the track-local (`docs_root:
"."`) shape that spec 084 existed to support.

**An optional parameter with a sensible default is an invisible call site.** A
missing argument is not a diff, not a warning, and not a test failure; it is
silence that happens to be right most of the time. The caller being actively
worked on gets updated because it is in front of you. Every other caller keeps
the default, and the wrong behaviour surfaces only on the minority
configuration nobody is testing. Cheap guard: when a shared helper gains a
project-scoped parameter, grep for *every* caller in the same change and decide
explicitly for each — the default is a decision, not an absence of one.

The sharper lesson was in the repair, not the defect. The right fix reused an
existing in-module resolver, `_project_docs_root`, which the bug-018
stale-citation scan had introduced. Reusing it also inherited its documented
contract — and that docstring justified swallowing every exception on the
grounds that the value "only decides where to LOOK for stale citations, so a
bad config must degrade to a narrower scan." True for a read. The fix silently
promoted the same value to deciding where files are **written**, where the
identical fallback means a malformed `scaffold.json` on a `docs_root: "."`
project silently reproduces the very symptom being fixed. Same code, same
fallback, materially different consequence.

**A helper's docstring is part of its contract; widening its set of consumers
without revisiting it leaves a justification that no longer covers the code.**
Both reviewer passes caught this independently and both called it the blocker —
the one-line fix was fine, the stale promise around it was not. Worth noting
that neither reviewer objected to the *behaviour*: degrading was still right.
They objected to a code comment asserting a reason that had stopped being true.

Two mechanical notes worth keeping:

- **A test that pins a property rather than a defect cannot be red-witnessed.**
  The degrade contract above was untested; the test added for it would pass
  before the fix too, so the red→green ritual proves nothing about it. Mutation
  is the substitute — force the resolver to raise, confirm the test goes red,
  under `python3 -B` so stale bytecode cannot mask the edit. Compare
  [[mutation-testing-pycache-false-negative]].
- **Assert the outcome, not the exit code.** That test first checked only
  `returncode == 0`, which a copy that wrote nothing at all would also satisfy.
  Pinning *where the blocks landed* is what makes it mean the documented thing.
## Bug 023: a `host` argument answers *some* host's question — say which one

`migrate.py copy_machinery` takes one `host`, and it was answering two
different questions with it:

- **where does the machinery go?** — a property of *this invocation*
  (`--host`, or inferred from where the copied helper sits on disk);
- **what variable do this project's docs cite?** — a property of *the project*,
  fixed when its docs were rendered, and already recorded in `scaffold.json`
  as `host_renderer`.

Feeding the invocation host to the second question makes a Codex-installed
helper scan Claude-rendered docs for `${PLUGIN_ROOT}`, match nothing, and print
nothing — output identical to a clean project. The manifest flip still
succeeds, so the run looks fine.

- **A variable that is in scope and plausible is still a guess.**
  `resolved_host` was correct for the copy and merely *available* for the
  advisory. Nothing at the call site distinguished the two meanings, so one
  name served both and the second answer was right only by coincidence. When a
  helper takes a `host` (or `mode`, or `profile`) argument, name whose it is —
  in the signature or the comment.
- **Varying two inputs together is not coverage.** Bug 018 shipped 28 tests
  across both hosts, and every one scaffolded and invoked the *same* host. All
  28 would pass against a hard-coded constant. Only a fixture where project
  host ≠ invocation host can show which input the code actually reads.
- **Splitting a conflated read means splitting it in both directions.** The
  token now follows the project; the offered replacement path deliberately
  stays on the invocation, because after `--host codex` the skills really are
  under `.codex/skills/` and no `.claude/skills/` exists. Moving *both* halves
  to the project host would have traded one false statement for another.
- **Third instance in one function.** Bug 018 recorded "a caller widened a
  contract the callee was never told about", then repeated it a few hundred
  lines later, and its fix moved the *spellings* to their owner while leaving
  the *host selection* pointing at the invocation. Recording a learning does
  not enforce it; the enforcement here is `read_host_renderer` returning `None`
  for a host it does not recognise instead of quietly defaulting to Claude, so
  an unknown answer cannot masquerade as a known one. See the bug 018 entry
  above.
- **A host name written inside a cross-host contrast will invert in the other
  host's package.** `build_codex_plugin.py` rewrites `Claude` → `Codex`
  wholesale, so "run a Codex-installed helper against a Claude-scaffolded
  project" ships to Codex users as "...against a Codex-scaffolded project" —
  the same-host case the sentence just dismissed. This happened here, in the
  documentation *of the two-host fix*, and it had already happened once in
  scaffold-init's SKILL.md (`test_scaffold_mode.py::test_skill_md_output_
  survives_the_codex_translation`). The rule: in any host-translated file,
  phrase host contrasts **neutrally** ("a helper installed for one host
  against a project scaffolded for the other") so there is no literal for the
  builder to rewrite — and pin it against the RENDERED artifact, because the
  source always reads fine. That is why a source-only assertion cannot catch
  it. It recurred a *third* time in the same cycle: the editor comment added
  to warn future editors off host literals named both hosts itself, and
  shipped as `NO host literals ("Codex", "Codex", .codex/, .codex/) …
  rewrites the first to the second`. A rule stated in prose that violates
  itself is worth less than no rule.
- **Because the rewrite runs one way, "renders identically" is only half a
  guard.** The builder maps Claude spellings to Codex ones and never the
  reverse, so section identity catches every Claude spelling *the builder
  rewrites* and is **blind** to a Codex one — both packages render it
  verbatim, and the other host's readers get a sentence about a host they are
  not using. Pin both directions: identity for the translated side, an
  explicit absence check for the untranslated one. The guard's **second**
  version asserted identity alone and claimed it held "iff the section
  contains nothing host-specific", which was false in exactly that direction.
  (The first banned two known-bad sentences and was useless; four versions in
  total — the sequence is in bug 023's `## Proof`.)
- **And take the forbidden set FROM the translator, not from memory.** The
  **third** version kept identity and hand-wrote `Codex` / `.codex/` /
  `CODEX_` for the blind direction — and let `${PLUGIN_ROOT}`, `AGENTS.md`,
  `--host codex` / `--host claude` (lowercase — the builder is
  case-sensitive) and unslashed `.codex` straight through. A restated table
  is the bug-018 defect, and writing it *inside the guard built to stop this
  bug's version of it* is how little the lesson transfers by memory alone.
  It is now parsed out of `build_codex_plugin.py` by an AST walk over its
  `.replace()` calls, taking **both** sides of each pair: the left-hand side
  is a spelling the build consumes, the right-hand side one it produces —
  and the second group is exactly what a hand-written list forgets, because
  those strings never appear in the source you are looking at.

**A deterministic extractor needs a way to say "I don't know"** (bug 020,
[`020-adr-index-summary-degradation`](../bugs/020-adr-index-summary-degradation.md)
/ [issue #140](https://github.com/ramboz/jig/issues/140)).
`adr.py index` derives each ADR's one-line summary from the record's first
`## Context` paragraph, and `_extract_description` had to return a string for
every input. When the paragraph is a lead-in to a list it contains no complete
sentence, so the helper emitted the lead-in verbatim — colon and all — or cut
it at 120 chars with a trailing `…`. Five of 46 bullets were in that state and
nobody noticed, because **a fragment and a summary are the same shape**: the
output was well-formed, just meaningless. Letting the helper return `""`, and
reporting it as `(no description)` plus a warning naming the record, closed
every live case.

The corollary is about policy, not code. The maintainer's ruling ([#151](https://github.com/ramboz/jig/pull/151),
reaffirmed on [#154](https://github.com/ramboz/jig/pull/154)) is that a
generated index stays a **pure function of its sources** — hand edits to the
generated file are overwritten by design, and the remedy for a bad row is to
fix the source. That is workable **only if the generator names the source that
needs fixing**. A derive-only policy plus a generator that silently invents
something plausible is the worst pairing: the human is told to fix the source
and given no way to find it. If you rule that a generated artifact may not be
hand-edited, make sure it reports what it could not derive.

**A safety gate that fails "open" reads exactly like a gate that passed** (bug 024,
[`024-slice-land-tests-inert-vendored`](../bugs/024-slice-land-tests-inert-vendored.md)
/ [issue #129](https://github.com/ramboz/jig/issues/129)).
`slice-land`'s `check_tests` located `tdd.py` with a fixed
`Path(__file__).parents[2] / "skills" / "tdd-loop" / "tdd.py"`. That path is
only correct for an un-prefixed plugin install; in a **vendored** layout — jig
copied into a consuming repo's `.claude/skills/` with the marketplace `jig-`
prefix (`jig-slice-land/`, `jig-tdd-loop/`) and `CLAUDE_PLUGIN_ROOT` unset — it
missed, and the "helper missing" branch returned a **non-blocking** `warn`
worded as *"no test runner detected (slice may be doc-only)"*. So a repo with a
full green suite (and one with genuinely red tests) both rendered the same
reassuring doc-only line, and the Tests gate was a silent no-op. Two lessons:
(1) **resolve sibling helpers by content, not by a hard-coded parent name** —
glob `*tdd-loop/tdd.py` / `*/tdd.py` off `land.py`'s own directory so the
resolution survives a renamed/prefixed parent; and (2) **"the check could not
run" and "there was nothing to check" must be different states.** Collapsing an
environment failure into the legitimate doc-only case is what let the failure
hide — the fix split them (`not_run` vs `warn`) and rendered `not_run` as a
loud `[!] NOT RUN … This is NOT a pass`. A bonus corollary: when you widen a
status enum, re-audit every consumer — the doc-only servo-suggestion guard
keyed on `== "warn"` had to learn about `not_run` too, or it would leak.
