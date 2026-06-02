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
Adding `security-review` to Tier 1 (slice 052-05) required updating **three** hardcoded skill lists — `_TIER_SKILLS["tier-1"]` (`skills/scaffold-init/scaffold.py`, the source of truth), `TierSkillSetTests.EXPECTED_TIER_1` (`skills/scaffold-init/test_scaffold.py`), and **`TierUpgradeTests.TIER1`** (`skills/migrate/test_migrate.py`, easy to miss because it lives in the *migrate* suite, not scaffold's) — plus **three doc sites**: `docs/product-vision.md` (the "7 Tier 0 + N Tier 1" count *and* the numbered skill list), `skills/vision-elicitation/worked-example-jig.md` (count + two separate Tier-1 enumerations, one pinned by `test_..._tier_line_in_sync`), and `README.md` ("N skills total" / "all N skills" counts). The tier-gated *copy* tests read `_TIER_SKILLS` directly so they don't need touching, but the two upgrade/inventory tests keep parallel hardcoded copies. Miss any one and either `TierSkillSetTests` / `TierUpgradeTests` or a doc-sync test fails.

**Generalizable rule:** when adding a Tier-1 skill, the checklist is `_TIER_SKILLS` + `EXPECTED_TIER_1` + `TierUpgradeTests.TIER1` + product-vision (count + list) + worked-example-jig (count + 2 lists) + README (counts) + the CLAUDE.md Skills table row. Run the full suite — the consistency tests name the location you missed. (Related but narrower: "Hook-count callouts in docs drift on hook additions" above.)

Provenance: slice 052-05 implementation + reconciliation, 2026-06-01.
## Scaffold doc templates render into two install shapes — `${CLAUDE_PLUGIN_ROOT}` paths break in scaffold mode
The `templates/docs/*.md.template` + `CLAUDE.md.template` files render for BOTH
install shapes: `--plugin-only` (machinery stays under the plugin root) and the
default in-repo scaffold (machinery copied to `.claude/skills/jig-*`). A
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

## `.claude/skill-usage.jsonl` has two writers — readers must filter `event=='skill_invoked'`
The same log file is appended to by **two** hooks with **different row shapes**: `jig-telemetry.sh` (`PreToolUse`/`Task`) writes Task-spawn rows with no `event`/`skill_name`, and `jig-skill-trace.sh` (`PreToolUse`/`Skill`, spec 041-01) writes `{event: "skill_invoked", skill_name, ...}` rows. Any reader that wants *skill* invocations (e.g. `workflow.py routing-stats`, slice 041-02, or the recipe in `docs/skill-routing-verification.md`) MUST filter `event == 'skill_invoked'` first — a naïve "count every line" miscounts Task spawns as skills. **Rule:** when adding a third writer or reader of `skill-usage.jsonl`, preserve the `event`-tag discriminator; don't assume one row shape. Provenance: spec 041 (041-01 hook + 041-02 routing-stats), 2026-06-02.
