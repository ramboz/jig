---
dependencies: []
last_verified: 2026-05-28
---

# ADR-0009: RTK (Rust Token Killer) not adopted for jig

## Status

Accepted (2026-05-28)

## Context

[RTK](https://github.com/rtk-ai/rtk) is a Rust-based CLI proxy
("Rust Token Killer") that compresses command output before it
reaches an LLM's context window. Its marketing claim is 60-90%
token reduction on common dev operations via a Claude Code
`PreToolUse` hook that transparently rewrites `Bash` tool
invocations. The pitch overlaps directly with jig's context-economy
design principle: reduce noise before it consumes useful context.

Spec 044's spike measured RTK v0.42.0 (released 2026-05-24) against
jig's actual workflow with a paired baseline-vs-enabled run plus
three follow-up sub-experiments (custom TOML filters, explicit RTK
wrappers, file-read aggressive mode) and a 54-command coverage
audit. The measurement evidence (full forensic trace in
[docs/specs/044-rtk-integration-spike/slice-01-rtk-e2e-measurement-spike.md](../specs/044-rtk-integration-spike/slice-01-rtk-e2e-measurement-spike.md))
showed a more textured picture than the marketing claim:

- The default hook rewrites **32 of 54 typical jig Bash commands
  (59%)** — `git`, `rg`, `cat`, `ls`, `find`, `gh`, `wc`, `diff`,
  `npx eslint`. Coverage is real.
- But **compression density on the rewritten half is uneven** and
  fails in safety-relevant ways:
  - `rg → rtk grep` rewrites ripgrep invocations to GNU grep,
    which rejects rg-native flags (`--type`, recursive-by-default).
    A correctness regression on every Claude code-search via Bash.
  - `git diff <range> → rtk git diff` returns `--stat`-style file
    list only — diff hunks are discarded. The 70% byte saving is
    lossy; real review work still needs `rtk proxy git diff`.
  - `cat` of small/medium source files is rewritten to `rtk read`
    but produces *identical* bytes — the default `--level none`
    means zero compression unless the hook were extended to pass
    `--level minimal` or `--level aggressive` (which it isn't).
  - `git log`, `ls` of small dirs, and many small-output commands
    are rewritten but yield no compression.
- **All `python3` invocations pass through unchanged**, and
  `python3` is jig's hot path: `workflow.py`, `review.py`,
  `adr.py`, `tdd.py`, `migrate.py`, `land.py`, `run_tests.py`.
  Out-of-the-box, RTK touches zero jig-internal commands.
- The most powerful unique-to-RTK capability is **`rtk read
  --level aggressive`** — function-body stubbing that delivers 86%
  compression on a 145 KB Python source file. But the default
  hook does not pass `--level`, the heuristic is wrong for
  spec/markdown/review tasks, and most jig file-reads are
  markdown anyway.
- Install side effects extend beyond hooks: `rtk init -g`
  **appends `@RTK.md` to the user's *global* `~/.claude/CLAUDE.md`**.
  Mutation to the user's instruction set, not just hook config.
  No project-local install path is documented.
- The custom-filter extension mechanism (`.rtk/filters.toml` with
  `rtk trust`) is real but in v0.42.0 did not apply to
  transparent hook-rewritten output. The built-in named filters
  (`rtk pipe -f pytest`) silently *discard* jig's custom test
  runner output as "no tests collected" — a data-loss failure
  mode on format mismatch.

The session-level estimate (extrapolated, not instrumented E2E)
puts genuinely lossless useful savings around 5–10 KB per typical
jig slice session, with another ~100 KB of conditional
diff-summary savings the user has to decide whether to accept.
The biggest jig context consumers — skill prose loaded into the
system prompt, `Read` tool output, MCP outputs, model reasoning
— are entirely outside RTK's hook scope.

## Decision Options Considered

### Option A: Adopt RTK as a recommended optional accelerator

Scaffold-init writes an `rtk-compat` block into `.claude/settings.json`,
documents RTK in `docs/architecture.md` as a recommended companion,
and ships a project-local `.rtk/filters.toml` template with
`exclude_commands = ["rg", "git diff"]` to mute the broken/lossy
rewrites.

- **Pros:** Tracks a tool whose direction (context economy) is
  aligned with jig's. Low friction for users who already have RTK
  installed. Free `git status` compression session-wide.
- **Cons:** Adds an external runtime dependency on a 3-day-old
  v0.42.0 tool with a fast-moving release surface. Recommending
  it pulls jig into the maintenance loop every RTK release.
  Out-of-the-box savings on jig's actual command profile are
  marginal (`python3` untouched, `cat` produces 0% by default).
  Telemetry / install-mutation / hook-merge edges aren't worth
  shouldering for the measured benefit. Endorsing a tool whose
  default behavior includes a known correctness regression
  (`rg → grep`) and a silent lossy compression (`git diff`)
  damages trust.

### Option B: Build jig-side compatibility shims that explicitly invoke RTK wrappers

Add a jig PreToolUse hook (or wrap `scripts/run_tests.py` in a
shell wrapper) that prepends `rtk test ` to test runs when RTK is
on `$PATH`. Optionally extend to other jig helpers via `rtk smart`
or `rtk summary`. Configure the hook to pass `--level minimal` to
`rtk read` for source-code paths.

- **Pros:** Unlocks the one genuine RTK win for jig (`rtk test
  python3 scripts/run_tests.py` — 8 KB → 200 B losslessly). Keeps
  jig in control of which RTK features it activates, side-stepping
  the broken defaults.
- **Cons:** All the engineering and ongoing maintenance lives in
  jig. The work to wire and test `rtk test` is comparable to the
  work to add a `--quiet` flag to `run_tests.py` natively — and
  the native flag has no external dependency, no version-drift
  risk, no install ritual. Same compression outcome, less surface.

### Option C: Document RTK as known-compatible-but-not-recommended

Add a single inbox entry naming RTK, the measured findings, and
explicit re-evaluation triggers. Do not modify scaffold-init,
hooks, or any jig artifact to assume RTK's presence. Users who
want RTK install it independently.

- **Pros:** Costs zero ongoing maintenance. Captures the
  evaluation so future contributors don't re-spike the same
  question. Leaves the door open for a future RTK release that
  fixes the noted gaps.
- **Cons:** Users who would benefit from RTK have to find this
  decision themselves. The inbox entry will age out of working
  memory eventually.

### Option D: Fork RTK or write a jig-specific compression layer

Build (or fork) a context-compression tool that understands jig's
command surface: stubs `python3` helper output to summary lines,
runs aggressive read-level on source paths but not spec paths,
preserves diff hunks during review work.

- **Pros:** Could deliver materially larger savings than RTK gives
  off-the-shelf. Solves the "right tool for jig's shape"
  problem properly.
- **Cons:** Substantial engineering investment for a benefit
  that's bounded (bash output is a fraction of total session
  context). Ongoing maintenance burden. Out of scope for the
  spike that produced this ADR — would need its own spec, design,
  and time-box.

## Recommended Decision

**Option C: Document RTK as known-compatible-but-not-recommended.**

Spec 044's measurement evidence does not justify the dependency
and maintenance cost of Option A (recommended adoption) or
Option B (jig-side wrapper shims) at RTK v0.42.0. The most
useful single lever — `rtk test` for test-output compression —
can be replicated by a `--quiet` flag on `scripts/run_tests.py`
with no external dependency, no install ritual, no version-drift
risk, and identical compression outcome. The most powerful
unique RTK capability — aggressive-level file reads with
function-body stubbing — is task-sensitive (wrong for code
review and for the markdown that dominates jig's file-read
volume) and not activated by RTK's default hook anyway.

The inbox entry captures the evaluation with re-evaluation
triggers ([docs/inbox.md](../inbox.md), 2026-05-28); the
forensic record lives in
[the spec 044 slice body](../specs/044-rtk-integration-spike/slice-01-rtk-e2e-measurement-spike.md).
This ADR records the decision itself so future contributors who
search `docs/decisions/` for "RTK" land on the answer without
needing to re-read the spike.

Option D (fork or build a jig-specific compression layer) is
deferred indefinitely. It may become attractive if session
context starvation becomes a measured problem and the
aggressive-mode source-file lever becomes the bottleneck — but
that's speculative today.

## Consequences

**Becomes easier:**

- Future evaluations of similar token-compression tools have a
  measurement template to follow (spec 044's command corpus +
  coverage audit + sub-experiment shape).
- Contributors asking "should we adopt RTK?" get a one-link
  answer (this ADR) instead of re-running the spike.
- jig stays free of an external runtime dependency on a young
  tool with a fast-moving release surface.

**Becomes harder:**

- Users who would prefer RTK's session-wide `git status`
  compression and `rtk test` lever will need to wire it
  themselves. The inbox entry points them in the right
  direction, but jig will not scaffold the integration.
- If a future RTK release closes the documented gaps (project-
  local install, `rtk rg`, default `--level` selection,
  `python3` rewrites, lossless `git diff` mode), this ADR will
  need to be superseded by a new ADR that reverses the
  decision. The inbox trigger list makes that revisit explicit.

## Open questions

None at this time. The inbox entry's re-evaluation triggers
enumerate the conditions under which this decision should be
reconsidered.
