# Verifying skill-routing delegation (pr-review / arch-review)

jig ships **baseline** `pr-review` and `arch-review` skills and is designed to
**defer to a richer user-installed skill** (commonly `~/.claude/skills/pr-review/`)
when one is present. "Delegation" happens on **two different paths**, verified
two different ways. Knowing which path you're on is the whole game.

## Path A — interactive (you ask for a review at the top level)

You type/say "review this diff" or "review this design" in a normal session.
Here Claude's **skill router** picks between the installed skills by description.
Your richer `pr-review` and jig's `jig:pr-review` have *different names*, so both
are visible and the router chooses by relevance; jig's description explicitly
defers, and a user-scope skill outranks a plugin one. The richer one should win
— but it's model-mediated, so **verify, don't assume.**

**How to verify (deterministic per-run observation):** the `PreToolUse`/`Skill`
hook (`hooks/scripts/jig-skill-trace.sh`) logs every Skill-tool invocation —
including auto-triggered ones — to `.claude/skill-usage.jsonl`:

`.claude/skill-usage.jsonl` is **shared** with `jig-telemetry.sh` (which logs
`Task` spawns as `event: task_spawned`, optionally with `phase`, `spec`, and
`slice` when the Task prompt carries `[jig:...]` tags), so filter on the
`skill_invoked` event:

```bash
# after asking for a review, read which skill actually fired:
python3 -c "import json
for l in open('.claude/skill-usage.jsonl'):
    e = json.loads(l)
    if e.get('event') == 'skill_invoked':
        print(e['timestamp'][:19], e['skill_name'])"
```

A line with `pr-review` means your richer skill fired; `jig:pr-review` means the
baseline did. If the baseline keeps winning over a richer installed skill, jig's
description is too greedy — open an issue.

**Limits of the hook.** It sees the **main agent's** Skill-tool calls. Typed
`/slash` commands expand via `UserPromptExpansion` (not `PreToolUse`), and a
*subagent's* own Skill calls are not guaranteed to surface here.

## Path B — the spec-workflow craft / arch pass

During the spec lifecycle, the craft (`pr-review`) and arch (`arch-review`)
passes spawn a read-only `reviewer` **subagent** (Read/Glob/Grep — **no `Skill`
tool**). A live probe confirmed it has *no way to invoke a skill at all*, so the
skill router is **not reachable** on this path. Earlier prose ("apply the
most-specific SKILL.md the router resolves to") was therefore inert — the
reviewer just followed jig's inlined baseline buckets.

**Fix — the explicit candidate channel (spec 096-03 / ADR-0040 D3;
supersedes spec 031's user-scope `detect_richer_skill`, now removed).**
Resolution is a precedence chain, not a user-scope name lookup:
1. **Config wins** — an explicit `review.<category>_skill` in `scaffold.json`
   (spec 096-01). Deterministic, reproducible, both hosts.
2. **Zero-config pick** — absent config, `review.py candidates <category> <spec>
   <slice> --pass <pass>` enumerates non-baseline skills across scopes, prints
   them **tiered** (`[high-confidence]` with descriptions, `[speculative]` names
   only), and writes the shown set to a sidecar; the orchestrator picks the best
   and passes it as the **required** `--richer-skill <name|none>`; the pass
   validates the pick against the shown tiers (off-list / unresolvable → baseline,
   recorded).
3. **Baseline** otherwise. jig's own baselines are excluded from discovery by the
   `jig-` path prefix / plugins-`jig` segment (spec 096-02), not a marker.

**How to verify (deterministic):**

```bash
export CLAUDE_PLUGIN_ROOT="$(pwd)"
# Config path: name a richer skill in scaffold.json → the craft prompt names it.
# Zero-config path: show candidates, then pick.
python3 skills/independent-review/review.py candidates pr_review <spec.md> <slice> --pass craft
python3 skills/independent-review/review.py pr-review <spec.md> <slice> <file> --richer-skill <name-or-none> | grep -i "read that SKILL.md\|bundled .*baseline"
# Missing --richer-skill, or no sidecar + no config + no --non-interactive → fails fast (exit 2).
```

**How to verify deferral actually worked (spec 096-05).** `record-review`
derives a closed `substrate:` into each slice-keyed extensible-pass evidence file
(`config` / `shown` / `not-shown` / `non-interactive` / `n/a`), plus the
`applied_skill` and the `shown_candidates` set. Two committed consumers surface
it: `review.py check-reviews` emits a **non-blocking** stderr advisory naming any
high-confidence richer skill that was *shown and not applied* (never changes the
exit code — the ADR-0014 gate stays a `verdict:` predicate), and
`workflow.py status-board` renders a **"Richer-skill selection audit"** section
aggregating the `not-shown` + `non-interactive` counts and the shown-and-declined
anomalies (the ADR-0040 kill-criterion-1 aggregator).

**Two accepted blind spots (documented, not solved — mitigation is config
precedence, 096-01):**
- **`config` is anomaly-blind.** A `substrate: config` run records the configured
  skill from *presence*, not proof the reviewer applied it, and never fires the
  anomaly (the user chose deliberately). So the audit is silent exactly where the
  *guaranteed* layer lives — by design; config is the deterministic floor, not a
  thing to audit.
- **A recall failure is invisible.** If enumeration nominates *nothing* (or misses
  a genuine richer skill), the orchestrator picks `none`, no candidate was shown,
  and no anomaly fires — a real miss looks identical to "nothing installed". The
  matcher is recall-oriented to shrink this, but it cannot see what it never
  enumerated. The mitigation is to name the skill in `scaffold.json` (config
  precedence), which needs no enumeration at all.

## Summary

| Path | Mechanism | Determinism | How to verify |
|---|---|---|---|
| A — interactive | skill router (description match) | model-mediated | `.claude/skill-usage.jsonl` trace |
| B — workflow craft/arch/code-health | config (096-01) → tiered `candidates` + required `--richer-skill` pick (096-03) → baseline; jig baselines excluded by path (096-02) | deterministic config + validated pick + graceful fallback | run `candidates`, inspect the built prompt |
