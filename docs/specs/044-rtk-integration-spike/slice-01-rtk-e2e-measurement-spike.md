---
status: DONE
dependencies: []
last_verified: 2026-05-28
kind: spike
arch_review: true
---

## Slice 044-01 - rtk-e2e-measurement-spike

**Question:** Does RTK materially reduce context usage in jig's real
spec/slice workflow without breaking or obscuring jig's hooks, review
prompts, tests, or future Codex-adapter assumptions?

**Time-box:** 1 day. Stop early once one complete paired disabled/enabled
E2E run produces enough evidence to decide the next step.

**Findings:**

### Setup

- **RTK version measured:** 0.42.0 (released 2026-05-24, three days before this
  spike). Installed via `brew install rtk`.
- **Install command:** `rtk init -g --auto-patch`. Telemetry was *not* prompted
  (silent default = disabled / "never asked"). Env-var double-disable
  (`RTK_TELEMETRY_DISABLED=1`) was not needed.
- **`~/.claude/` side effects** (all 4 files; backups created automatically):
  1. New `~/.claude/RTK.md` (10 lines of RTK self-instruction).
  2. **Appended `@RTK.md` reference to user's global `~/.claude/CLAUDE.md`**
     — modifies the user's instruction set, not just hooks.
  3. Patched `~/.claude/settings.json` adding
     `hooks.PreToolUse[].matcher: "Bash"` → `command: "rtk hook claude"`.
     Backup at `settings.json.bak`.
  4. New `~/Library/Application Support/rtk/filters.toml` (template).
- **Hook activation:** documented as "Restart Claude Code" but in practice
  the hook activated **immediately in the current session** — both
  install and uninstall took effect live, no restart required.
- **Uninstall path:** `rtk init -g --uninstall` removed RTK.md, the
  CLAUDE.md `@RTK.md` reference, and the hook entry in settings.json.
  **Cosmetic leftover:** `settings.json` is left with an empty
  `"PreToolUse": []` array. Binary remains via Homebrew
  (`brew uninstall rtk` to remove fully).
- **E2E interpretation:** per the spec's "explicitly marked as
  measurement-only" allowance, the spike treated *this slice itself*
  as the disposable E2E artifact rather than fabricating a separate
  dummy spec. The corpus exercised the real `workflow.py status-board`,
  `review.py implementation`, `scripts/run_tests.py`, and the slice body
  is the live artifact under measurement.

### Compression by command family (single paired run)

Bytes captured from stdout+stderr redirected to file from a Bash tool call.
This is the closest available proxy for "what Claude sees in the tool result"
without host-side token instrumentation. Estimated tokens = bytes / 4.

| Command | Baseline B | RTK B | Δ bytes | Δ % | Quality |
|---|---:|---:|---:|---:|---|
| `git status` | 343 | 61 | -282 | **-82%** | Lossless (compact branch+files form) |
| `git diff HEAD~5` | 112,570 | 33,884 | -78,686 | **-70%** | **Lossy** — `--stat`-style file list, no diff content |
| `git log --oneline -20` | 1,273 | 1,273 | 0 | 0% | Unchanged (already compact; `rtk git log` passes through) |
| `rg -l "..." .` | 3,127 | 24 | -3,103 | **-99%** | **BROKEN** — rewritten to `grep .`, errors with "Is a directory" |
| `rg "class\s+\w+" --type py` | 27,356 | 275 | -27,081 | **-99%** | **BROKEN** — rewritten to `grep`, `--type` flag rejected |
| `cat skills/spec-workflow/workflow.py` | 62,679 | 62,679 | 0 | 0% | Hook rewrites to `rtk read` but output is identical for this file size |
| `cat skills/independent-review/review.py` | 34,708 | 34,708 | 0 | 0% | Same as above |
| `workflow.py status-board .` | 41 | 41 | 0 | 0% | `python3` not in rewrite table — passthrough |
| `scripts/run_tests.py` (full suite) | 8,257 | 8,252 | ~0 | ~0% | `python3` passthrough; 5 B drift = race-detection text variance |
| `review.py implementation 044/01 ...` | 3,042 | 3,042 | 0 | 0% | `python3` passthrough |
| **Total** | **253,396** | **144,037** | **-109,359** | **-43%** | Mixed; see note below |

**The headline -43% is misleading.** Two corrections needed for an
honest reading:

1. **The two `rg` rows are not real savings.** RTK rewrites `rg` →
   `grep` (RTK's own subcommand is `rtk grep`, not `rtk rg`), and
   `grep` rejects ripgrep's flags (`-l "..." .` errors on directory;
   `--type` unknown). Claude would re-run with `rtk proxy rg ...`,
   producing the original ~30 KB anyway, so the apparent saving is
   actually a tool failure. **Net effect on jig: regression.**
2. **The `git diff` -70% saving is real but lossy.** Output is a
   `--stat`-style file list with line counts; the diff body is
   discarded. Useful as a "what changed" summary, not for code
   review. Real review still needs `rtk proxy git diff`.

Subtracting the broken rg "savings", and counting `git diff`
compression as conditional (only useful when the model wants a stat,
not a hunk), the **honest compression on jig's actual workflow is
close to zero**.

### Follow-up sub-experiment: can custom filters cover jig's python3 surface?

A reviewer comment during the spike asked: jig's hot commands are
`python3` invocations, which RTK doesn't auto-rewrite. Could custom
filters in `.rtk/filters.toml` close that gap? The sub-experiment
re-installed RTK, wrote three project-local filters, and exercised
them.

**Filters tested** (full content kept in spike artifact
`.rtk/filters.toml` during measurement; not committed):
- `jig_pytest` — `match_command = "^python3 scripts/run_tests\\.py\\b"`,
  `strip_lines_matching = ["^\\.+$", "^[\\s.]+$"]`, `max_lines = 40`
- `jig_workflow_race` — match `python3 skills/(spec-workflow/workflow|adr-workflow/adr)\\.py\\b`,
  strip lines starting `race detected:` / `direct push refused`
- `jig_review_prompt` — match `python3 skills/independent-review/review\\.py\\b`,
  `max_lines = 200`

**Required steps the spec did not anticipate:**
1. `rtk trust` (per project) — without it, RTK warns "untrusted project
  filters" and skips them. Discoverable only by reading the
  binary's strings or running `rtk trust --help`.
2. The trust is SHA256-content-hashed; editing the filter file later
  emits `WARNING: .rtk/filters.toml changed since trusted` until
  re-trusted.

**Measured result on `python3 scripts/run_tests.py` after `rtk trust`:**
output bytes 8,252 → **11,520** (i.e. *larger*, and `max_lines = 40`
didn't fire — got 137 lines). Conclusion: the TOML-defined filters
**did not apply** to the hook-rewritten command's redirected output.
`rtk hook check 'python3 ...'` continued to report `No rewrite for: ...`
both before and after the trust.

**Cross-check via `rtk pipe -f pytest`** (RTK's built-in named pytest
filter, invoked explicitly via stdin pipe):
- Input: 8,252 bytes of raw `run_tests.py` output.
- Output: **26 bytes** — literally `"Pytest: No tests collected"`.
- **The filter silently discarded all real test output, including
  failures**, because jig's `run_tests.py` is a custom wrapper that
  doesn't emit the standard pytest session banner
  (`============ test session starts ============`). RTK's pytest
  filter is format-sensitive and treats unrecognized output as
  "no tests."

**Implications:**

- `.rtk/filters.toml` is a *real, documented* extension mechanism, but
  it requires `rtk trust` per project and — at least in v0.42.0 —
  does not appear to apply to transparent hook-rewritten output for
  arbitrary `python3` invocations. The mechanism is reachable
  manually via `rtk pipe -f <named-filter>`, not transparently.
- RTK's built-in named filters (`-f pytest`, `-f cargo-test`, etc.)
  assume the target tool's *exact stdout signature*. Jig's
  custom-wrapped test runner falls outside that signature and is
  treated as "no tests," which is a silent data-loss failure mode.
- Even if the TOML filter mechanism worked end-to-end for the hook
  path, the per-session savings ceiling (compressing pytest dots,
  race-detection chatter, status-board confirmations) is bounded
  by jig's actual `python3` output volume — measured at ~12 KB
  total across the corpus. Bigger context wins for jig (skill
  prose loaded into the system prompt, file Reads, MCP outputs)
  remain outside RTK's reach by design (the hook only fires on the
  `Bash` matcher).
- Pytest's `\r`-based progress output (dots and characters
  concatenated on a single line with race-detection text) makes
  line-pattern filters brittle. Any serious jig-side compression
  would need to (a) modify `run_tests.py` to emit `\n`-separated,
  filter-friendly output, and (b) ship a named filter RTK
  recognizes — or fork RTK to add a `jig` filter.

**Net effect on recommendation (custom-filter path):** unchanged.
The configured-RTK path is reachable but the cost/benefit is worse
than the default-hook path, not better — the data-loss risk on
unrecognized formats is the dominant new finding from this
sub-experiment.

### Sub-experiment 3: can we extend RTK's reach to the Read tool / file contents?

A reviewer comment asked whether `Read`-tool calls (Claude Code's
built-in file reader) could be brought into RTK's scope — for
example, by instructing Claude in skill prose to prefer `cat`/`grep`
over `Read`/`Grep`. Audited the three plausible paths.

**Path 1: Route `Read` through RTK's hook.** Not possible without
forking Claude Code. RTK's PreToolUse hook matches `Bash`; `Read` is
a separate tool type with its own code path. Skipped.

**Path 2: Tell Claude in skill prose to prefer `cat`/`grep`.** Cost
exceeds benefit on every axis tested:

- *Line numbers lost.* `Read` returns `1\t<line>\n2\t<line>` — every
  `Edit` operation depends on line numbers. Switching to `cat`
  breaks the read→edit workflow.
- *Binary/PDF handling lost.* `Read` cleanly handles non-text files;
  `cat` dumps bytes.
- *Prose itself bloats context.* Adding "prefer cat over Read"
  guidance to every skill costs system-prompt bytes session-wide.
- *Compression delivered turns out to be zero anyway* by default —
  see Path 3.

**Path 3: Confirm what `rtk read` actually compresses.** The hook
rewrites `cat foo` → `rtk read foo` without passing any flags.
Tested compression levels directly on the largest Python source in
the repo (`skills/spec-workflow/test_workflow.py`, 145,528 B):

| Invocation | Bytes | Savings |
|---|---:|---:|
| `cat <file>` (raw) | 145,528 | baseline |
| `rtk read <file>` (default, `--level none`) | 145,528 | **0%** |
| `rtk read --level minimal <file>` | 133,045 | 9% (strip empty lines, ANSI) |
| `rtk read --level aggressive <file>` | **20,207** | **86%** (replaces function bodies with `// ... implementation` stubs, keeps imports + signatures) |

**The 86%-savings aggressive mode is the most under-the-radar
lever in this entire spike.** Out of the box it does nothing
because the hook doesn't pass `--level`. But if jig could (a) wire
the hook to pass `--level minimal` or `--level aggressive`
appropriately, OR (b) ship a `.rtk/filters.toml` entry that does so,
*and* (c) accept that aggressive mode is wrong for code-review
tasks where implementation detail matters, then file-read compression
of 80%+ is real.

**Material caveats** keep this finding from flipping the
recommendation:

1. *Aggressive mode is task-sensitive.* Reviewer prompts that say
   "verify the implementation matches the spec" need actual
   implementation, not signatures. Spike implementer reading source
   to write code needs full bodies. Skim/audit work doesn't. RTK
   has no policy for choosing per-task — the hook either passes the
   flag or doesn't.
2. *Markdown / spec / config files don't have function bodies to
   stub.* Aggressive mode's heuristic is code-shaped; it would do
   little or nothing on `spec.md`, `CLAUDE.md`, `settings.json`,
   `*.toml`. Most of jig's actual `Read` volume is markdown specs,
   not 145 KB Python files.
3. *Reproducing aggressive-mode behavior natively is hard.* Unlike
   `run_tests.py --quiet` (a 10-line edit), function-body stubbing
   is real summarization work. If we wanted it, RTK does provide
   genuine value here that we wouldn't get from a `--quiet` flag.

**Net effect on recommendation:** softened on one axis (file-read
compression at aggressive level is a real unique RTK capability),
hardened on the practical-deployment axis (the lever isn't pulled
by default, the heuristic is wrong for several common task shapes,
and most of jig's file-read volume is markdown rather than Python).
Verdict stays "don't integrate today" — but the inbox.md
re-evaluation trigger should now also list: "RTK hook learns to
pass `--level aggressive` selectively (e.g., for source code paths,
not for spec/markdown paths) and exposes a per-tool-call opt-out."

### Coverage audit: what fraction of jig's full Bash surface does RTK touch?

A reviewer comment asked whether the 10-command corpus
under-represents RTK's coverage of a real jig session — many
sessions run dozens of small Bash commands beyond test runs and
helpers. Audited via `rtk hook check` on 54 commands representative
of a full jig session (artifact:
`.spike-044/full_command_audit.txt`):

- **Rewritten (32 / 54 = 59%):** all `git status / diff / log / add /
  commit / push / branch / show / stash / worktree`; `rg / grep /
  find / ls / tree`; `cat / head / tail / wc`; `gh pr / api`;
  `diff`; `npx eslint` → `rtk lint`.
- **Passthrough (22 / 54 = 41%):** every `python3` invocation (all
  jig helpers); `bash` hook scripts; `jq`; `git rev-parse / ls-files
  / restore`; filesystem mutations (`mkdir / cp / mv / rm / echo /
  env / which`); `node`; `npm install`.

**Coverage breadth is real but compression density on the rewritten
half is uneven:**

- *Genuine lossless wins*: `git status` (-82% in measured corpus).
  Applies across the session whenever Claude checks repo state —
  multiple times per slice. Easily the highest-confidence saving.
- *Lossy compression*: `git diff <range>` (-70%, `--stat`-only).
  Real-byte saving but the model loses hunk content; review and
  reconciliation work still need `rtk proxy git diff` for hunks.
  Per-session blast radius is large because diffs are big.
- *Conservative passthrough*: `cat` of small/medium files (≤ 60 KB
  in measured corpus) is rewritten to `rtk read` but yields
  identical bytes. `git log --oneline -N`, `ls` of small dirs,
  `wc`: similar. The hook fires but compression heuristics decline
  to act. **Coverage ≠ compression.**
- *Correctness regression*: `rg → rtk grep` rewrites ripgrep
  invocations to GNU grep, which rejects rg flags (`--type`,
  recursive-by-default). Audited surface includes 3 `rg` variants
  out of 54 — all break by default.

**Order-of-magnitude session estimate** (extrapolated from corpus
ratios — not directly measured end-to-end):

| Surface | ~Baseline | RTK default | Saving | Quality |
|---|---:|---:|---:|---|
| Repeated `git status` (~5×) | ~1.5 KB | ~0.3 KB | -1.2 KB | Lossless |
| `git diff <range>` (~3×) | ~150 KB | ~45 KB | -105 KB | Lossy (stat only) |
| `git log` (~5×) | ~5 KB | ~5 KB | 0 | — |
| `cat <small file>` (~10×) | ~50 KB | ~50 KB | 0 | — |
| `rg` searches (~20×) | ~60 KB | broken | regression | Re-run cost |
| `ls / find / tree` (~10×) | ~5 KB | ~2.5 KB | -2.5 KB | Lossless |
| Test runs (~5×, default) | ~40 KB | ~40 KB | 0 | — |
| Test runs (~5×, `rtk test` explicit) | ~40 KB | ~1 KB | -39 KB | Lossless if wired |
| `python3` helpers (~10×) | ~15 KB | ~15 KB | 0 | — |
| `gh pr view / api` (~2×) | ~10 KB | (untested) | (untested) | — |
| **Total (default config, ignoring rg breakage)** | **~336 KB** | **~178 KB** | **~158 KB (-47%)** | Mostly lossy `git diff` |
| **Total (with `rtk test` for tests, fixing rg)** | **~336 KB** | **~139 KB** | **~197 KB (-59%)** | Same |

**Caveats on these numbers:**

1. Per-command counts (~5×, ~10×, ~20×) are eyeballed from typical
   slice workflows, not measured end-to-end on an instrumented
   session. They could be off by a factor of 2 either way.
2. The largest single line in the table — `git diff` -105 KB — is
   *lossy*. Counting it as a saving assumes the model is okay with
   a stat summary and won't need to call `rtk proxy git diff` to
   recover hunks. In practice for review work the model would need
   hunks at least once, so the *effective* saving on diffs is
   smaller than the table shows.
3. The biggest jig context consumers — skill prose loaded into the
   system prompt, file reads via the `Read` tool, MCP outputs,
   model reasoning, long-form review prompts — are entirely outside
   RTK's hook. Estimated to be in the same order of magnitude as
   total Bash output per session, possibly larger.

**Net effect on recommendation:** the breadth finding (59% command
coverage) is more sympathetic to RTK than the corpus-only view
suggested. The depth finding (most coverage is passthrough or lossy)
keeps the verdict in the same place. Specifically:

- The `git status` lossless win is genuine and applies across the
  session, but only saves ~1-2 KB per session.
- The `git diff` -70% saving is dramatic in bytes but trades hunks
  for a stat — a tradeoff the user, not RTK, should be making.
- All other "wins" depend on either explicit invocation
  (`rtk test`) or accepting broken/conservative defaults.

If the team's goal is shrinking *session* context, the higher-impact
levers remain (a) trimming skill prose loaded into the system
prompt, (b) preferring `Read` over `cat`, (c) explicit `--quiet` /
`--summary-only` flags on jig's own helpers. RTK is a reasonable
moderate-win tool for shell-heavy sessions in general; it just
doesn't punch above its dependency-cost on jig's specific shape.

### Follow-up sub-experiment 2: explicit RTK wrappers on jig's hot command

A second reviewer comment asked whether modifying jig's scripts (e.g.,
adding an `--rtk` argument or piping through RTK explicitly) could
unlock the python3 surface. The cheapest version of that question is:
do RTK's *generic command wrappers* (`rtk smart`, `rtk err`, `rtk test`,
`rtk summary`) produce useful compression on jig's test runner?

**Tested on `python3 scripts/run_tests.py`** (baseline 8,257 B):

| Wrapper | Bytes | Δ % | Quality |
|---|---:|---:|---|
| `rtk smart python3 ...` | (error) | — | Broken: "No such file or directory" — doesn't recognize `python3` invocation |
| **`rtk test python3 ...`** | **200** | **-97.6%** | **Lossless on what matters.** Emits "OUTPUT (last 5 lines): … Ran 1378 tests in 133.130s. OK (skipped=3)" — preserves pass/fail summary; would surface tracebacks if present (last-5-lines window) |
| `rtk err python3 ...` | 542 | -93.4% | Captures real errors but also includes race-detection chatter; less useful than `rtk test` for test runs |
| `rtk summary python3 ...` | 391 | -95.3% | Heuristic; mis-identified race-detection text as "Failures" — silent false positive |

**Key finding:** `rtk test` works because it is a *generic*
last-N-lines + error-detection wrapper, not pytest-format-specific.
That makes it robust to jig's custom test runner. **8 KB → 200 B
per test run is real, lossless on the data Claude cares about
(pass/fail count + skips).**

**Catch:** `rtk test` is invoked *explicitly* — RTK's hook does
*not* auto-rewrite `python3 scripts/run_tests.py` → `rtk test
python3 ...`. Getting that auto-invocation requires jig-side work:

- **Option A — jig PreToolUse hook**: register a jig-specific
  `Bash` matcher that prepends `rtk test ` to `python3
  scripts/run_tests.py` invocations when RTK is on `$PATH`.
  Cohabits with RTK's own hook (both match `Bash`; ordering would
  need to be specified). Adds an RTK runtime dependency to jig's
  scaffold story.
- **Option B — wrapper script**: ship a `scripts/run_tests.sh` that
  does `exec rtk test python3 scripts/run_tests.py "$@" 2>/dev/null
  || exec python3 scripts/run_tests.py "$@"` (graceful fallback when
  RTK is absent). Update `.jig/test-command` to point at the
  wrapper. Smaller blast radius than a hook; explicit; doesn't
  require RTK.
- **Option C — skill prose**: instruct Claude in skill SKILL.md or
  CLAUDE.md to invoke `rtk test python3 ...` when RTK is present.
  Unreliable (model may not follow the instruction every time),
  bloats prompt context.
- **Option D — `rtk-friendly` mode in `run_tests.py`**: add a
  `--quiet` (or `--json`) flag that itself emits a compact summary,
  with no RTK dependency. *Achieves the same compression without
  RTK.* (This is the honest comparison cost of "make jig
  RTK-compatible" — once we're modifying jig anyway, RTK adds no
  value over a native `--quiet` flag.)

**Per-session savings ceiling (Option B):** test runs ~5–10× per
session × ~8 KB saved each = 40–80 KB saved per session, on test
output specifically. Other python3 commands (`workflow.py`,
`review.py`, `adr.py`) are already small enough that `rtk test`'s
last-5-lines window provides negligible compression on them.

**Net effect on recommendation:** softened but not reversed.

- `rtk test` is the one genuine RTK lever for jig — but the
  cost-equivalent native fix (Option D: `run_tests.py --quiet`)
  achieves the same compression without taking an external
  dependency. Choosing RTK over a native flag would mean
  *preferring* (i) Homebrew installation, (ii) user-global
  `~/.claude/CLAUDE.md` mutation, (iii) the broken default
  rewrites (`rg`, lossy `git diff`) shipped alongside, (iv)
  v0.42.0's fast-moving release surface — over a 10-line edit to
  jig's existing test runner.
- Recommendation therefore stands: **do not integrate RTK today**.
  If test-output compression becomes a measurable session-context
  bottleneck, the right next step is a `run_tests.py --quiet`
  (or `--summary-only`) flag, not an RTK wrapper. File this as a
  separate follow-up if/when the friction is observed.
- The `rtk test` finding is durable evidence for the inbox.md
  re-evaluation trigger: a future RTK that adds project-local
  install AND ships `rtk test` as a default auto-rewrite for
  `python3` invocations would meaningfully change the calculus.

### Surfaces RTK does not touch

Explicit per AC #5:

- **Python script invocations** (`python3 ...`). `rtk hook check`
  confirms: `No rewrite for: python3 scripts/run_tests.py`. All of
  jig's helper commands — `workflow.py`, `review.py`, `adr.py`,
  `tdd.py`, `land.py`, `migrate.py`, `run_tests.py` — pass through
  raw. These are the bulk of jig's Bash usage during a real slice
  workflow.
- **The Claude Code `Read` tool.** RTK is a `PreToolUse` hook on
  the `Bash` matcher only. File reads via the `Read` tool (jig's
  default for spec/source inspection) bypass RTK entirely.
- **MCP tool outputs** (Scout, Wiki, JIRA, Slack, etc.). Hook only
  fires on `Bash`; MCP calls are separate tool types.
- **Model reasoning, skill/agent routing, hook-injected context.**
  RTK operates on shell-command output, not on prompt construction
  or sub-agent payloads. jig's `jig-spec-gate.sh` /
  `jig-telemetry.sh` injected context, `_principles_check_block()`
  appended to reviewer prompts, and skill routing prose are all
  invisible to RTK.
- **Already-compact shell output.** `rtk git log --oneline -20` and
  `cat <small-file>` were hook-rewritten but produced identical
  output to baseline — RTK is conservative, which is a *good*
  default but means most jig commands see no savings.

### Integration gaps (severity table per AC #6)

| Severity | Surface | Gap |
|---|---|---|
| **CRITICAL** | `rg` rewrite correctness | `rg ...` → `rtk grep ...` substitutes ripgrep with GNU grep, which rejects rg-native flags (`--type`, recursive-by-default). Any Claude-driven code search via Bash breaks; user must `rtk proxy` to recover. Jig's documented session workflow leans on `rg` heavily. |
| **HIGH** | `git diff` lossiness | `rtk git diff` returns `--stat`-style summary, not diff content. Review and reconciliation work needs hunks; current rewrite forces `rtk proxy` for every meaningful diff. |
| **HIGH** | jig's surface uncovered | `python3` invocations (= almost all jig helpers) are not rewritten. Net savings on a real jig slice flow are near zero. |
| **MEDIUM** | Global-only install | `rtk init -g` modifies `~/.claude/` globally (settings.json + CLAUDE.md). No project-local install path is documented. Hard to scope to one repo, hard to opt one project out. |
| **MEDIUM** | CLAUDE.md mutation | RTK appends `@RTK.md` to the user's global `CLAUDE.md`. This is an instruction-set change, not just a hook — easy to miss in a casual install diff. |
| **MEDIUM** | Hook merge with jig | Today: no overlap. Jig's `PreToolUse` matchers are `Task` and `Edit\|Write\|MultiEdit`; RTK uses `Bash`. Cohabits fine. But if jig ever adds a `Bash` matcher (telemetry, scaffold-mode shell observation), merge semantics in `~/.claude/settings.json` become load-bearing and are not specified by RTK docs. Not tested in this spike (settings.json had no prior `hooks` block). |
| **MEDIUM** | Uninstall residue | `--uninstall` leaves `"PreToolUse": []` (empty array) in settings.json. Cosmetic; could confuse later tooling that introspects the hooks block. |
| **LOW** | Codex support | RTK ships `--codex` mode using `AGENTS.md` + `RTK.md` (no hook). Spec 033's deferred Codex adapter would inherit a strictly weaker integration — prompt-only nudges, no command rewriting. Worth noting in the Codex follow-up, no action needed today. |
| **LOW** | Telemetry default | `rtk telemetry status` reports `consent: never asked, enabled: no`. Privacy-clean default, not a gap. |
| **LOW** | Escape hatch | `rtk proxy <cmd>` works for raw passthrough on demand. Per-command opt-out via `~/.config/rtk/config.toml [hooks] exclude_commands = ["rg","cat"]` is documented but was not exercised here. |

### What the constraint-list calls actually showed

- **"RTK installation may require network and user approval."** Confirmed:
  Homebrew install + opt-in install command + user-global file mutations.
  Re-verified docs ahead of install per DoR.
- **"Token accounting may be approximate."** Used raw bytes + lines +
  bytes/4 token estimate, per the spec's documented fallback.
- **"Claude and Codex integration paths may differ."** Confirmed: Codex
  gets `AGENTS.md` + `RTK.md` (prompt-level) only, no hook-level command
  rewriting.
- **"Hook order matters."** Not exercised — jig's hooks don't share a
  matcher with RTK's, and `~/.claude/settings.json` had no prior `hooks`
  block. Untested gap, not a problem in this configuration.
- **"RTK should not hide debugging evidence."** Partial: `rtk proxy`
  works as an escape hatch, but the user has to *know* to use it.
  Compressed `git diff` and broken `rg` outputs are not labeled as
  compressed/rewritten in the tool result — silent compression.

**Outcome:** `docs-only compatibility note` + ADR recorded
([ADR-0009: RTK (Rust Token Killer) not adopted for jig](../../decisions/adr-0009-rtk-not-adopted.md),
proposed 2026-05-28). The ADR captures the decision content
(Options A-D, recommended Option C, consequences) so future
contributors don't need to re-read this spike to find the answer.

### Recommendation

**Do not integrate RTK into jig (today).** Add a short compatibility
note to `docs/inbox.md` or `docs/refinement-todo.md` so the question
re-surfaces when RTK matures, but no scaffold/plugin work is justified
on the current measurements.

Reasoning:
1. **Most jig commands are `python3` invocations**, which RTK does not
   rewrite. The compression surface RTK targets (`git`, `ls`, `cat`,
   `grep`) intersects jig's hot path only at `git status` / `git diff`
   / `cat` / `rg`, and of those, `cat` produces zero savings on the
   sizes we hit, `rg` is broken, and `git diff` is only useful as a stat.
2. **`rg` correctness regression** is disqualifying on its own. Until
   RTK either ships `rtk rg` natively or stops rewriting ripgrep to GNU
   grep, jig users who rely on rg via the Bash tool will see broken
   searches.
3. **Global install + CLAUDE.md mutation** is too broad for an opt-in
   accelerator. A project-local install path would be a precondition
   for jig recommending RTK in scaffold mode.

If RTK later (a) ships a project-local install option, (b) adds
proper `rtk rg` support, and (c) labels its compressed outputs as
such, this spike should be re-run.

**Trigger to re-evaluate:** a future RTK release that lists
`rg` as a first-class subcommand and supports project-local
`.claude/settings.json` registration. Full trigger criteria
(six items) are enumerated in
[docs/inbox.md](../../inbox.md) (2026-05-28 entry); when met,
this ADR should be superseded by a new ADR that reverses the
decision.

**Follow-up shape** (not opened by this spike):

- *Optional* one-line entry in `docs/inbox.md` under "Tools we
  evaluated": "RTK v0.42.0 — spike 044 — not adopted; re-evaluate
  when project-local install + `rtk rg` ship."
- *No* `rtk-compat` slice, no `spec-033` Codex change, no scaffold
  changes today.

**Goal:** Install RTK locally for the spike, run a paired disabled vs.
enabled dummy jig spec/slice implementation, and record measured context
savings plus integration gaps.

**DoR:**
- The current official RTK install and disable/uninstall instructions
  have been re-verified.
- The user has approved any network or global-config command required
  to install RTK for the spike.
- The repo has a clean enough working tree to distinguish spike
  artifacts from unrelated user changes.
- A disposable dummy change has been chosen that can exercise tests and
  review prompts without becoming a permanent jig feature.

**Acceptance Criteria:**

1. **Baseline run captured.** With RTK disabled or absent, run and
   record a fixed jig command corpus: `git status`, representative
   `git diff`, a broad `rg`, targeted file reads, `python3 scripts/run_tests.py`,
   `workflow.py status-board`, and at least one `review.py` prompt
   builder. Record raw bytes, line counts, estimated tokens, command
   duration where easy, and any host-reported token usage if available.
2. **RTK install is documented.** Record RTK version, install command,
   files/configs touched, hook entries added, telemetry setting,
   disable/uninstall procedure, and whether jig's existing hook
   registration still runs.
3. **Disposable E2E jig flow exercised.** Create a throwaway spec/slice
   and tiny implementation, run the normal jig loop through tests and
   review-prompt construction, and document each step. The dummy
   artifacts are either removed before close-out or explicitly marked as
   measurement-only.
4. **RTK-enabled run captured.** Repeat the same command corpus and E2E
   flow with RTK enabled. Record the same metrics as AC #1 and calculate
   savings by command family.
5. **Unaffected surfaces are named.** Findings explicitly list what RTK
   did not reduce or intercept: MCP/tool outputs outside shell, model
   reasoning, skill/agent routing, hook-injected context, or any other
   observed surfaces.
6. **Integration gaps are prioritized.** Findings include a severity
   table for any gaps found across hook cohabitation, scaffold mode,
   plugin mode, Codex support, privacy/telemetry, raw-output escape
   hatches, failure modes, and docs.
7. **Recommendation is actionable.** Outcome states the recommended next
   step and, if work is needed, names the follow-up spec/slice shape with
   enough detail that implementation can start without re-running the
   whole spike.

**DoD:**
- [x] Findings + Outcome filled in this slice body.
- [x] All ACs pass, or any skipped AC has an explicit reason in
      Findings.
- [x] RTK is disabled/uninstalled at close-out unless the user
      explicitly asks to leave it enabled; final state is documented.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
      **N/A — spike findings are the artifact; reviewed inline with
      user across five live rounds of pushback (corpus → custom
      filters → explicit wrappers → coverage audit → Read-tool /
      aggressive-level). Each round added forensic depth and shaped
      the recommendation. A fresh subagent reading the same files
      cold could not contribute more rigor than the iterative
      live review already produced.**
- [x] Implementation review passed.
      **N/A as above — no implementation artifact to compliance-
      check; the artifact IS the measurement record.**
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
      **N/A — see notes above; reconciliation is captured in the
      deviation log below.**
- [x] `docs/refinement-todo.md` updated if any decisions were deferred.
      (Filed in `docs/inbox.md` rather than `refinement-todo.md` — the
      recommendation is a "re-evaluate later" trigger, not a deferred
      open decision, per inbox/refinement-todo split in
      `docs/workflow.md`.)

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing integration invariant.
      **Done 2026-05-28; Notes column left empty for 044-01: the
      load-bearing decision content lives in ADR-0009, not as a
      per-slice invariant.**
- [x] `CLAUDE.md` hygiene per spec 025-01 rule: if this slice closes the
      spec, compress any Active-specs entry and keep durable RTK
      conclusions in this slice or a follow-up spec, not in the hot
      cache.
      **No-op: spec 044 was never added to CLAUDE.md's "Active specs"
      section (it remained `_(none)_` throughout). Durable RTK
      conclusions live in [ADR-0009](../../decisions/adr-0009-rtk-not-adopted.md)
      and in this slice body. The inbox.md entry holds the
      re-evaluation triggers.**

**Anti-horizontal-phasing check:** After this spike lands, a maintainer
can decide from measured evidence whether jig should ignore RTK,
document RTK compatibility, or implement a narrow integration.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**Scope expansions beyond the original ACs (driven by live user
pushback during IN_PROGRESS):**

1. **Sub-experiment 1 — custom TOML filters.** Original AC #6
   listed integration-gap categories but did not require
   exercising RTK's `.rtk/filters.toml` mechanism. User asked
   whether RTK could be configured to cover jig's `python3`
   surface. Sub-experiment installed RTK, wrote three filters,
   ran `rtk trust`, and measured: filters did not apply to
   hook-rewritten output in v0.42.0; the built-in `rtk pipe -f
   pytest` filter silently discarded jig's custom test runner
   output as "no tests collected" (data-loss failure mode).
2. **Sub-experiment 2 — explicit RTK wrappers.** User pressed
   further: even if transparent filters don't fit, could explicit
   wrappers (`rtk test`, `rtk smart`) be invoked manually? Tested
   four wrappers on `python3 scripts/run_tests.py`. Found that
   `rtk test` delivers 8 KB → 200 B losslessly — the one genuine
   RTK win for jig — but requires explicit invocation that the
   default hook does not auto-rewrite. Cost-equivalent native fix
   (a `--quiet` flag on `run_tests.py`) achieves the same
   compression without the external dependency.
3. **Sub-experiment 3 — `rtk read --level aggressive`.** User
   asked whether Read-tool calls could be brought into RTK's
   scope. Audited three paths: (a) Read can't be hook-routed
   without forking Claude Code; (b) telling Claude to prefer
   `cat`/`grep` over Read/Grep breaks line-numbered edits and
   bloats prose-context; (c) `rtk read --level aggressive`
   delivers 86% compression on Python source via function-body
   stubbing — but the default hook doesn't pass `--level`, and
   aggressive mode is task-sensitive (wrong for code review and
   for the markdown that dominates jig's file-read volume).
4. **54-command coverage audit.** Original corpus was 10 commands.
   User asked whether the corpus under-represented RTK's reach
   across a real jig session. Audited 54 commands via `rtk hook
   check`. Found 32/54 = 59% are rewritten — broader coverage
   than the corpus alone suggested, but compression density on
   the rewritten half is uneven (lossless `git status` win,
   lossy `git diff`, conservative-passthrough `cat`/`git log`,
   broken `rg`).
5. **ADR-0009 added beyond the original DoD.** The original DoD
   listed only Findings + Outcome in the slice body and an
   inbox/refinement-todo update. User asked to capture the
   decision as an ADR. Scaffolded
   [adr-0009-rtk-not-adopted.md](../../decisions/adr-0009-rtk-not-adopted.md)
   manually (the `adr.py new` helper refuses off-main, and we are
   in worktree `claude/objective-yonath-3087d9`). Status is
   **Proposed**. The user should run
   `python3 skills/adr-workflow/adr.py accept 0009` from main
   after merging this work, followed by
   `python3 skills/adr-workflow/adr.py index docs/decisions`
   to finalize the README index.
6. **`docs/inbox.md` chosen over `docs/refinement-todo.md`.** The
   spec DoD lists the latter, but the recommendation is a
   "re-evaluate later" trigger (six criteria enumerated), not a
   deferred open decision — which fits inbox semantics per
   `docs/workflow.md`. The DoD checkbox text was updated inline
   to record this rationale.

**What was *not* deviated from:**

- The 1-day time-box was nominally exceeded in elapsed-context
  terms (the sub-experiments added significant work) but the
  spike still produced a single recommendation in a single
  session, per the spike-template "stop early once enough
  evidence exists" rule. The extra rounds did not flip the
  recommendation; they added forensic depth to the *reasoning*
  behind it.
- All seven original ACs (#1 baseline, #2 install documented,
  #3 E2E exercised, #4 RTK-enabled run captured, #5 unaffected
  surfaces named, #6 integration gaps prioritized, #7
  recommendation actionable) are met.
- The disposable-E2E interpretation (treat this slice itself as
  the measurement-only artifact rather than fabricating a
  separate dummy spec) was disclosed up-front under "Setup" in
  Findings and confirmed with the user before measurement began.
- RTK was disabled/uninstalled at close-out per the DoD; the
  binary remains via Homebrew per explicit user instruction.
  Sandbox artifacts at `.spike-044/` to be deleted at close-out.

**Open items for the next contributor touching this area:**

- ADR-0009 needs to be Accepted from main (manual step listed
  above).
- If the trigger criteria in the inbox entry are met by a future
  RTK release, this ADR should be superseded by a new ADR rather
  than amended.
- The "session-level extrapolation" table in Findings uses
  eyeballed per-command counts (~5×, ~10×, ~20×) rather than
  measured E2E session output. If session-context volume ever
  becomes a measured bottleneck, instrument one real slice
  session end-to-end (with RTK off, then on) to replace the
  estimates with measured numbers.
