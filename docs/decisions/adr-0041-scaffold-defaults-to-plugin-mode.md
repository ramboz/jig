---
status: Accepted
dependencies: [adr-0013]
last_verified: 2026-07-29
frame_review: true
---

# ADR-0041: scaffold-init defaults to plugin mode

## Status

Accepted (2026-07-29)

This record reverses a default set by [spec 016-03](../specs/016-scaffold-mode/spec.md)
and is implemented by [spec 099](../specs/099-scaffold-default-plugin-mode/spec.md).
It starts `Proposed`; because it reverses a framing decision it carries
`frame_review: true`, so `adr.py accept` will not flip it to `Accepted` without a
passing frame-critique verdict (ADR-0020). Provenance: reported by Marie-Rose on
[issue #127](https://github.com/ramboz/jig/issues/127); the ADR-plus-spec route
was her call.

## Context

jig has two scaffold topologies — **plugin mode**, which leaves the machinery in
the installed jig plugin, and **in-repo mode**, which copies it into the project.
One axis in `scaffold.py` selects between them:

- **plugin mode** (`scaffold_mode: "plugin-only"`) — scaffold writes only the
  docs tree and the host primer. Skills, agents, hooks, and templates stay under
  the installed jig plugin and run from `${CLAUDE_PLUGIN_ROOT}`.
- **in-repo mode** (`scaffold_mode: "in-repo"`) — scaffold additionally *copies*
  jig's machinery into the project's `.claude/` (skills, agents, hooks,
  templates, a generated `settings.json`), so the project is self-contained and
  needs no installed plugin.

Spec 016-03 flipped the default from plugin mode to **in-repo** and pinned it
with `test_default_includes_machinery`. So today a no-flag scaffold copies jig's
whole machinery into the target. In one real scaffold that was **79 tracked
files** (21 skills, 19 hooks, agents, `_common` helpers) — about half the repo's
tracked files, dwarfing the actual project.

For the common case — a solo or personal project on a machine where the jig
plugin is already installed — that is the wrong default, for four reasons:

1. **Two sources of truth / silent drift.** The copied machinery is pinned to the
   jig version at scaffold time and never updates with the installed plugin. The
   project diverges from jig with no signal.
2. **Repo pollution.** Vendored tooling dominates the file count, every diff, and
   every `git log`. Reviews and history are mostly jig internals, not the project.
3. **Ownership ambiguity.** The user now holds editable copies of jig's internals.
   Are edits customizations or stale copies? There is no answer in the tree.
4. **The heavier choice, taken silently.** in-repo is a real commitment
   (self-contained, no plugin dependency). Defaulting to it for a project that
   *has* the plugin inverts the principle of least surprise.

in-repo genuinely serves cases where the plugin cannot be assumed present — CI or
cloud agents running a bare checkout, teams where not every contributor has jig
installed, fully self-contained or archival repos, **and one case this record
first missed: a user following jig's own README**. Two of the four documented
install recipes (`README.md`, "Claude scaffold" / "Codex scaffold") are
`git clone … && python3 …/scaffold.py <project>` — no plugin anywhere. Under the
old in-repo default those recipes worked, because the copy *was* the install.
Flipping the default breaks them, and breaks them **silently**: the scaffold
exits 0 and reports that jig runs from the installed plugin, which on that path
is not true.

That is the sharpest cost of this decision, and it lands on the least
experienced users — a first-time adopter following the README gets docs with no
runtime and no error to search for. It is addressed, not waved away: plugin mode
now emits an advisory note whenever it detects that shape — a run out of a jig
source checkout, with no plugin host driving it. The two exits (install the
plugin, or re-run `--in-repo`) are named by the **mode line**, which prints
unconditionally and so reaches the populations no detector catches; the note
points at it. README's two scaffold recipes were also corrected
to pass `--in-repo`, since being self-contained is their whole purpose. See OQ2
and the Kill criteria detector, both rewritten for this.

The problem is not that in-repo exists; it is that it is the **silent default**. And the axis is undiscoverable:
the `scaffold-init` Q&A lists five *content* questions (runtime, team, CI, tests,
LLM/AI) and never surfaces the machinery-vs-plugin choice, which is architectural
(repo topology, what gets committed) and appears in no project's own docs. So an
operator following the skill never sees the choice and silently accepts in-repo.

### Why 016-03 chose in-repo, and why that reasoning has narrowed

016-03's driving goal was **dogfooding**: jig itself, and early adopters, needed a
scaffold that fully wired up `.claude/` — hooks registered, settings written — so
the workflow could be exercised end-to-end without a separately-installed plugin.
At that stage jig was not yet distributed as a stable plugin, so "copy everything
in" was the only way to get a working install. That constraint has since lifted:
jig ships as a versioned Claude plugin (`.claude-plugin/plugin.json`, currently
2.8.0) whose own `hooks/hooks.json` registers every gate globally from
`${CLAUDE_PLUGIN_ROOT}`. The mode that 016-03 needed to *manufacture* now exists
by installing the plugin. What remains correct about 016-03 is that in-repo must
stay a first-class, fully-wired mode — this ADR keeps it exactly, behind a flag.

### What plugin mode does and does not provide (the security-floor question)

Flipping the default raises one real question: does a no-flag scaffold still get
jig's security floor (ADR-0013)? Probed against `hooks/hooks.json` and the
`scaffold()` plugin-only branch:

| Floor part | in-repo | plugin mode | Source in plugin mode |
|---|---|---|---|
| `.gitignore` secret patterns | ✅ | ✅ | scaffold writes it in **both** modes (`_write_gitignore_secret_block`) |
| secret-scan hook (`jig-secret-scan.sh`) | ✅ copied + registered in project `settings.json` | ✅ **runs from the plugin** | plugin `hooks/hooks.json` `Edit\|Write\|MultiEdit` |
| spec-gate / context-check / other gates | ✅ copied | ✅ **run from the plugin** | plugin `hooks/hooks.json` |
| `## Security (MUST)` primer block | ✅ | ✅ | primer template, written in both modes |
| `permissions.deny` guardrails (force-push / `rm -rf` / hard-reset) | ✅ **Claude only** — written to `.claude/settings.json`; ✗ on Codex | ✅ **Claude only** — seeded by a settings-only write (OQ1); ✗ on Codex | `_merge_permissions_deny` (in-repo) / `_write_permissions_deny_floor` (plugin mode, gated `host == "claude"`). Probed: a `--host codex --in-repo` scaffold writes no `settings.json` and no `permissions` anywhere — Codex has no equivalent project-scoped permission surface, so this floor part is absent on Codex in **both** modes |

**Read the ✅s with their precondition.** Every "runs from the plugin" row is
true *iff a plugin is actually installed for the target host*. Plugin mode does
not make the gates portable; it relocates them. In a plugin-**less** plugin-mode
scaffold what survives is only what the scaffold itself writes — `.gitignore`,
the primer block, and (Claude) `permissions.deny`. The hooks are simply absent.
That is the whole reason the silent-empty-scaffold risk below is treated as the
sharpest cost of this decision rather than a footnote.

Given the plugin is installed: in **Claude** plugin mode all five floor parts
hold. In **Codex** plugin mode four of five hold — `permissions.deny` has no
Codex analogue to write to, so ADR-0013 part 3 is absent there. Note that gap is
*not* introduced by this decision: Codex lacks it in in-repo mode too.

Two host asymmetries in this table are worth stating plainly, because an earlier
draft flattened both:

- **`permissions.deny` is Claude-only** (above). Codex projects do not get the
  destructive-command guardrail in *either* mode via a settings file.
- **"runs from the plugin" is conditional on Codex.** Per
  [architecture.md](../architecture.md), Codex treats plugin-bundled command
  hooks as non-managed: users must review and trust them through `/hooks` before
  jig's gates run. The ✅ is accurate about where the hooks *live*, not about
  their being active before that out-of-band step — which the scaffold never
  prompts for.

That last row was an ✗ when this record was first drafted. `permissions.deny` is
the one floor part that cannot be served from the plugin root — it lives in the
project's own `settings.json`, and no plugin mechanism injects it — so the
already-shipped `--plugin-only` path never wrote it (spec 052-04 routed only the
`.gitignore` floor there). Making plugin mode the *default* would therefore have
silently dropped the destructive-command guardrail from every new project: not a
regression in what plugin mode does, but a large change in how many projects get
the floor. The record originally accepted that and parked the question; the
maintainer ruled the other way on [#136](https://github.com/ramboz/jig/pull/136),
and slice 099-01 closes it. See **OQ1** below.

## Decision Options Considered

### Option A: Default to plugin mode; in-repo behind an explicit `--in-repo`
Flip `with_machinery` to default `False`. Add `--in-repo` (with `--with-machinery`
and `--copy-machinery` as aliases) as the deliberate opt-in. Keep `--plugin-only`
(now redundant with the default) for clarity and back-compat. Surface the axis as
a sixth Q&A question, and have the wizard summary name the chosen mode and why.

- **Pros:** The lean topology is the default for the common (plugin-installed)
  case, eliminating silent drift, pollution, and ownership ambiguity. in-repo
  becomes the deliberate choice its weight deserves. The axis is discoverable in
  both the Q&A and the summary. Minimal code change — the off-switch already
  exists; this flips which side is the default and renames the opt-in for clarity.
- **Cons:** Reverses a pinned 016-03 default, so its tests must invert and the
  many machinery-exercising tests must pass `--in-repo` explicitly. A no-flag
  scaffold no longer seeds `permissions.deny` (see the floor table) — *this con
  was accepted at decision time and has since been retired by OQ1; plugin mode
  now seeds them.* Existing automation that relied on the implicit in-repo
  default must add a flag.

### Option B: Keep in-repo default; only add the sixth question + summary
Leave the default as in-repo; make the axis discoverable via the Q&A and summary,
so at least the operator is prompted before accepting the heavy mode.

- **Pros:** No test inversion; no behavior change for existing callers. Addresses
  the pure *discoverability* complaint.
- **Cons:** Does not address the core objection — the heavy mode stays the default
  and stays taken by anyone who skips the question. "Principle of least surprise"
  is unfixed; a skipped question still lands in-repo. The four structural
  problems (drift, pollution, ownership, silent heaviness) remain the out-of-box
  reality for most projects.

### Option C: Per-host default (plugin for Claude, in-repo for Codex)
Flip the default only for the Claude host, leaving Codex on in-repo.

- **Pros:** Smaller Codex test churn.
- **Cons:** The in-repo-vs-plugin axis is host-independent, and the four
  objections apply identically to a Codex project whose plugin is installed. A
  split default is a surprising inconsistency that the ADR would have to justify
  on grounds that do not exist. It also complicates the mental model and the
  summary ("why did the same command choose differently here?").

> **Amended after implementation.** "The axis is host-independent" is the
> premise this rejection rests on, and it survives only as a statement about the
> *default*, which is genuinely the same on both hosts. The *mechanisms* turned
> out not to be: implementing this slice required three host-specific carve-outs
> — `permissions.deny` is Claude-only (`host == "claude"` gate, see the floor
> table), Codex plugin-mode docs need their own rewrite target (OQ3), and the
> two hosts' plugin-root variables have different documented scope (OQ2). None
> of these argues for a split *default*, so Option C stays rejected; but the
> rejection should be read as "same default, host-native materialization",
> not as "no host differences exist".

## Recommended Decision

**Option A**, applied to **both hosts**. The change is small where it counts (one
default, one new flag name, one summary line, one Q&A question) and the reversal
is proportionate: 016-03's in-repo default solved a problem — no installable
plugin — that no longer exists. in-repo stays a fully-wired, first-class mode; it
just stops being the silent default. The default now matches the common case
(plugin installed) and the principle of least surprise (the lean topology is the
unsurprising one; the heavy, self-contained commitment is opt-in).

The record is explicit that Option A is not free: as drafted it accepted the
`permissions.deny` gap in the default path (since closed — OQ1) and the silent
empty-scaffold risk on README clone-and-run installs (since mitigated by the
unconfirmed-plugin note — OQ2), and it forces every machinery-exercising test and
any in-repo-dependent automation to name `--in-repo` rather than rely on the
implicit default. The last of those stands as a real, unmitigated cost.

## Consequences

**Becomes easier:**
- The common case: a plugin-installed project scaffolds lean, and jig updates flow
  from the plugin with no drift.
- Reviewing and reasoning about a scaffolded repo — its history and diffs are the
  project's, not jig's internals.
- Choosing in-repo *deliberately*, for the cases that need it (CI, cloud agents,
  plugin-less teammates, archival), with the summary stating which mode ran and why.

**Becomes harder:**
- Anyone (or any script) that relied on the implicit in-repo default must now pass
  `--in-repo`. The wizard summary and the sixth Q&A question mitigate the
  interactive case; automation is on its own and must be updated.
- A `git clone … && python3 …/scaffold.py` install (two of README's four
  recipes) no longer produces a working jig, because the copy *was* the install
  on that path. Plugin mode's summary states the plugin-less case and both exits
  unconditionally (and the source-checkout note adds a nudge where it can), but
  the user must act on it — the scaffold cannot install a plugin for them.

## Assumptions

Probed on this branch (`main@fd7115a`), not asserted:

> **Not listed, deliberately:** the population claim itself — that the modal
> no-flag caller has the plugin installed (Context). It is *asserted*, and five
> rounds of frame-critique took it apart. It stays unprobed because the design
> no longer depends on it: the plugin-mode summary prints unconditionally and is
> true for a plugin-less run, so if the claim is wrong the cost is one truthful
> sentence and a documented recovery, not misdirected work. Making a shaky
> assumption non-load-bearing is a legitimate disposal of it; pretending it was
> probed would not be. See spec 099-01's deviation log §14.

- **The plugin registers every gate globally.** `hooks/hooks.json` at the plugin
  root registers `jig-secret-scan.sh`, `jig-spec-gate.sh`, `jig-context-check.sh`,
  and the rest under `${CLAUDE_PLUGIN_ROOT}` — so in plugin mode the hooks run
  from the installed plugin, not from a per-project copy. This is what makes the
  floor table's "runs from the plugin" rows true.
- **plugin mode already writes the `.gitignore` floor and omits the settings
  write.** The `scaffold()` `else` (plugin-only) branch calls
  `_write_gitignore_secret_block`, `_ensure_self_defining_convention_block`, and
  `_ensure_reframe_practice_block`, and does **not** call `copy_machinery` — so no
  `settings.json` and no `permissions.deny` on that path. *Probed and true when
  drafted; deliberately no longer true.* OQ1 added `_write_permissions_deny_floor`
  to that branch, so the flip does change plugin-mode behavior — by design, and
  scoped to `permissions.deny` alone.
- **The off-switch already exists.** `--plugin-only` (dest `with_machinery`,
  `store_false`) has shipped since 016-03; this ADR flips the group's default and
  adds `--in-repo`/`--copy-machinery` as `store_true` aliases of the existing
  `--with-machinery`. No new copy/skip machinery is written.

## Kill criteria

- **The plugin stops registering the gates globally.** If a future change moves
  hook registration out of the plugin's `hooks/hooks.json` (e.g. hooks become
  per-project-only), plugin mode would silently lose the secret-scan and spec-gate
  floor, and defaulting to it would be unsafe. *Detector:* the plugin manifest /
  `hooks/hooks.json` no longer lists `jig-secret-scan.sh`.
- **plugin mode proves too lean to be usable out of the box.** If real adopters
  routinely hit "jig doesn't work here" because they scaffolded plugin mode without
  the plugin installed, the default is wrong for the population and in-repo should
  return (or a detect-plugin-presence default should replace this static one).
  *Detector:* **partial, in-band, at scaffold time** — plugin mode prints the
  source-checkout note (`scaffolding_from_source_checkout()` returned True, with
  no plugin-root variable suppressing it), so for the clone-and-run population
  the condition is visible to the user in the moment rather than inferred later.

  **Three honest limits.** (a) *Coverage (false negatives):* it fires only on
  the clone-and-run shape, not on release-zip, copied-tree, or cross-host
  plugin-less runs (see OQ2's residual) — for those the criterion remains
  un-fireable. (b) *Precision (false positives):* the detected set is a
  **superset** of the failing population — a contributor who has the plugin
  installed but ran `scaffold.py` from a clone in a terminal also trips it.
  Rejected detector #2 below was killed for exactly this defect; this one
  inherits a bounded version of it, which is why the note states what was
  *detected* rather than asserting the condition. (c) *Audience:*
  the note reaches the **adopter's terminal**, never jig, while this criterion is
  a population-level claim. Worse, by telling the user how to self-serve it
  further suppresses the reports channel. So the detector improves the *user's*
  situation more than the *maintainer's* evidence, and this criterion should be
  read as weakly instrumented until a two-sided presence probe exists.

  Two earlier detectors were rejected, both for the same underlying reason —
  a detector must be able to *discriminate*, not merely to exist:

  1. "Repeated reports of plugin-mode scaffolds in plugin-less environments" —
     cannot fire at all. The failure emits no error and nobody files "nothing
     happened".
  2. "The host's plugin-root variable is unset" — fires too often. It flags
     plugin-installed users who used a terminal, and (on Codex, where the
     variable's documented scope is plugin *hooks*) would have flagged every
     healthy scaffold.

  Reports remain a *secondary* signal for the stronger claim — that the default
  is wrong for the population — but not the primary one for the failure itself.

## Open questions

**OQ1 — Should plugin mode also seed `permissions.deny`? → RESOLVED: yes.**
The one floor part plugin mode did not provide is the destructive-command
guardrail, because it lives in the project's `settings.json` and no plugin
mechanism injects it. Originally deferred here as out of scope; the maintainer
ruled on [#136](https://github.com/ramboz/jig/pull/136) to fold it in, and slice
099-01 implements it as `_write_permissions_deny_floor` — a **settings-only**
write reusing `_merge_permissions_deny` / `_PERMISSIONS_DENY_DEFAULTS`, guarded
so it drags in neither hooks nor skills, and deliberately *not* running the
unmanaged-hooks refusal (which protects hook config this write never touches).
The floor table's one ✗ is now a ✓; the "Becomes harder" bullet that named this
gap no longer applies.

**OQ2 — Should the default eventually be *detected* rather than static?**
Still open. Two claims in the first draft were wrong and are corrected here.

It claimed "a reliable plugin-presence probe from inside the scaffold does not
exist today". The accurate statement is narrower: a *presence* oracle is
fragile — [spec 011](../specs/011-plugin-self-install/spec.md) considered
probing `~/.claude/plugins/` and ruled it out for path fragility across scopes,
which is "we chose not to pay for it", not "it cannot be done". What does exist,
cheaply and on both hosts, is detection of the **failing population**: whether
the scaffold is running out of a jig *source checkout* (`hosts/` plus `scripts/build_host_packages.py` — a dev-only builder the release zip excludes, tightened from a looser `hosts/` + `scripts/` first draft that an unrelated monorepo could trip) rather than an installed plugin. That is what
`scaffolding_from_source_checkout()` keys on, and it is what the plugin-mode
advisory note fires on.

An earlier amendment keyed the note on the host's plugin-root environment
variable and warned whenever it was unset. That was wrong twice over, and the
second frame-critique caught both: `unset` is one-sided, so it also flags a
plugin-installed user who merely used a terminal (an unbounded false-positive
class); and its Codex arm assumed `PLUGIN_ROOT` reaches a skill subprocess's
environment, which [architecture.md](../architecture.md) does not establish — it
documents `PLUGIN_ROOT` for plugin *hooks*, a different mechanism, and
`plugin_root()` pointedly does not trust it for Codex. Had it shipped, the note
would have fired on every Codex plugin-mode scaffold including healthy ones: a
detector that cannot discriminate, which is the same defect class as the
report-based detector it replaced.

The checkout-shape signal needs no claim about any host's environment. A set
plugin-root variable still suppresses the note — but as suppression in the safe
direction, **not** as proof. On Claude it is well-grounded (the host populates it
for plugin scripts); on Codex the name is generic, so an unrelated export could
silence the note. That is the wrong direction to err on this record's own terms,
since it holds silence to be the sharpest cost. It is tolerable only because the
mode line is unconditional and already carries the plugin-less case; the note is
a nudge, not the sole warning. If that line is ever made conditional again, this
suppression must be revisited with it.

Switching the *default* on this signal is a further step and is not taken here:
the signal identifies a topology, and a jig contributor running from source may
well want plugin mode anyway. Telling them beats guessing for them.

**The residual, priced rather than waved away.** The note detects a *topology*
(clone-and-run), not the *condition* (no plugin installed). It therefore does
**not** cover every way a user reaches a plugin-less plugin-mode scaffold:

- an **unzipped release package** run directly — that tree is `hosts/claude`
  repackaged, so it is deliberately classified as installed-plugin-shaped, and
  [adoption-readiness.md](../adoption-readiness.md) names the release zip as an
  acquisition route peer to the marketplace;
- a hand-copied plugin tree;
- a **cross-host** run — `--host codex` driven from an installed *Claude* plugin
  yields a Codex project with no Codex plugin, tripping neither arm.

Those users trip no detector. What they do get — and this is the residual's
cheapest and most important mitigation — is a **mode line that is true for
them**: it prints unconditionally and names the plugin-less case rather than
asserting "jig runs from the installed plugin", which for them would be an
affirmative false statement (worse than the silence it replaced). That fix needs
no detection at all, and pricing the residual as unclosable-pending-a-probe had
obscured it: the reachable mitigation was wording, not machinery.

So: this record does **not** claim the note discharges the silent-empty-scaffold
risk. It claims (i) the unconditional mode line makes the failure *self-
describing* for every population, and (ii) the note adds an extra nudge for the
largest detectable slice. A genuinely *detected default* still needs the
two-sided presence probe — which is why OQ2 stays open rather than being marked
mitigated.

**OQ3 — What should Codex plugin-mode docs point at? → RESOLVED:
`${PLUGIN_ROOT}`.** Not raised in this record's first version; surfaced during
implementation and ruled on in [#136](https://github.com/ramboz/jig/pull/136).
The Codex doc rewrite was unconditional, so a Codex plugin-mode project's
`AGENTS.md` and `docs/workflow.md` cited a `.codex/skills/` tree the scaffold
never creates. The rewrite is now mode-gated like Claude's, but *gated*, not
skipped: skipping it entirely was measured and is strictly worse (a Codex
project's docs would then say `CLAUDE.md`, "Claude Code", and
`${CLAUDE_PLUGIN_ROOT}` — an unset variable *and* the wrong host). Plugin mode
instead names the installed plugin via Codex's own `${PLUGIN_ROOT}`, which is
not an invention for this slice: jig already depends on Codex expanding it for
every command in the packaged `hooks/hooks.json`, and `build_codex_plugin.py`
renders the plugin's own SKILL.md bodies against it. The two hosts end up
symmetric — in-repo names the copied tree, plugin mode names the plugin root.

**Second-order fix, found by compliance round 5 and worth recording because the
first fix looked complete:** the mode gate alone was a no-op on the path that
matters. `build_codex_plugin.py` pre-rewrote the *packaged* templates to the
in-repo shape at build time, and `scaffold()`'s gate keys on
`${CLAUDE_PLUGIN_ROOT}/skills/` — already gone from a pre-rewritten template.
So a scaffold run from an **installed Codex plugin** still emitted docs citing a
`.codex/skills/` tree it never created, while every source-tree test passed. Shipping the
packaged templates canonical was tried and reverted — they feed runtime readers
(`decisions.py` and friends) that copy them verbatim and have no transform of
their own. Instead the plugin-mode arm now normalizes an *already* project-local
input back to the plugin root, so the gate no longer depends on its input being
canonical. Pinned by a fixture that scaffolds from the shipped package rather
than the source tree.
