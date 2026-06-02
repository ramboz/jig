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
`Task` spawns with no `skill_name`), so filter on the `skill_invoked` event:

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

**Fix (file-read dispatch — spec 031 option (b)):** `review.py` now
*deterministically detects* a user-installed skill on disk
(`detect_richer_skill()` → `~/.claude/skills/<name>/SKILL.md`) and, when found,
points the reviewer at that concrete path to **read and apply**, falling back to
jig's baseline buckets only when none is installed.

**How to verify (deterministic):**

```bash
export CLAUDE_PLUGIN_ROOT="$(pwd)"
# With your richer skill installed → prompt names its path + "read that SKILL.md":
python3 skills/independent-review/review.py pr-review <spec.md> <slice> <file> | grep -i "read that SKILL.md\|/.claude/skills/"
# Simulate a machine without it → baseline branch:
HOME="$(mktemp -d)" python3 skills/independent-review/review.py pr-review <spec.md> <slice> <file> | grep -i "jig's bundled .*baseline"
```

Detection is **user-scope only** by design: a *project*-scope `.claude/skills/`
copy may be jig's own `scaffold-init` baseline, indistinguishable by path from a
genuinely richer project skill (see `docs/refinement-todo.md`).

## Summary

| Path | Mechanism | Determinism | How to verify |
|---|---|---|---|
| A — interactive | skill router (description match) | model-mediated | `.claude/skill-usage.jsonl` trace |
| B — workflow craft/arch | `review.py` file-read detection | deterministic detection + graceful fallback | inspect the built prompt |
