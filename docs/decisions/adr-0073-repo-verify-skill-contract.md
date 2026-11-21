---
status: Proposed
dependencies: [adr-0040]
last_verified: 2026-11-21
frame_review: true
---

# ADR-0073: A repo-owned verify skill is the run-the-app contract

## Status

Proposed (2026-11-21)

## Context

Investigation record: [R-002](../research/R-002-claude-code-verification-assessment.md)
(mechanism 4, plus the end-to-end half of mechanism 3). The Claude Code team's
post says "Running the app end to end matters more than tests." Its practice is
to "create a skill called verify. Put it in a .claude/skills/ folder in your
repo, as close to the relevant code as you can", so that "Claude knows to use
the verify skill before committing changes." The skill is the smoke-test
harness, so it has to be fast and reliable, and it is where the agent gets its
hands and eyes: a browser over the Chrome DevTools Protocol (CDP), a device
simulator, an API harness. A feature map can double as the agent's rubric.

**What jig has today.** Spec 118 (behavioral-verification pilot, DONE) added an
optional "Verification scenario" section to the slice template
(`templates/docs/specs/slice-template.md:56-79`) with `pass` / `fail` /
`not-run` / `environment-error` outcomes. Its authoring step says "Reuse the
existing test command or project browser/service tools; jig owns neither
execution infrastructure nor credentials" (`skills/spec-workflow/SKILL.md:336-347`),
and its compliance block checks supplied scenarios
(`skills/independent-review/review.py:426-439`). So each slice that needs
runtime proof re-works out how to boot and drive the app, and nothing in the
repository keeps that knowledge between slices. The only per-repo command jig
knows is `.jig/test-command` (`skills/tdd-loop/tdd.py:142-154`), which runs the
unit suite, not the app.

**Spec 118 drew this line on purpose.** Its non-goals read: "no new skill,
lifecycle state, gate, frontmatter field, parser, runner, wiki sync,
authentication system, or universal end-to-end test mandate"
([spec 118](../specs/118-behavioral-verification-pilot/spec.md), Scope). Its
Evaluation section left the next step open: "A later real-project review can
evaluate omitted state rules caught, broken journeys caught, and
authoring/execution cost before considering stronger enforcement." This ADR is
a deliberate revisit of one part of that line: a durable, project-owned home
for *how to run the app*. It does not revisit enforcement.

**A consumer is waiting.** servo's `_gather_candidate`
(`ramboz/servo` `skills/eval-authoring/score.py:415-429`) is "a documented,
deliberately-unbuilt seam" that raises `EnvError` rather than score a
placeholder; servo's refinement-todo entry "eval-authoring — candidate-gather
(running the system under test) is unbuilt" (servo
`docs/refinement-todo.md:862`) waits for a first real consumer. servo spec 049
plans to use a project's verify skill there. servo's nearest working shape is
content-fidelity's command source: an argv list, run from the project root,
exit 0 required, stdout as the output, anything else an `EnvError` (servo
`skills/content-fidelity/score.py:125-161`).

**Hosts do not share one project-skill folder.** Claude Code reads
`.claude/skills/`, Codex reads `.agents/skills/`
(`skills/_common/skill_discovery.py:52-71`; `skills/scaffold-init/scaffold.py:1352-1353`),
and Copilot CLI reads `.github/skills/`, `.agents/skills/` and `.claude/skills/`
([spike 113-01](../specs/113-copilot-third-host/slice-01-copilot-contract-spike.md) AC2;
[ADR-0061](./adr-0061-copilot-third-host.md)). No single folder reaches all
three, which is R-002's open question for this ADR.

**jig's skill discovery has an invariant a verify stub touches.** Richer-skill
discovery tells jig's own baselines from a team's skills by the `jig-` prefix
([ADR-0040](./adr-0040-richer-skill-discovery-explicit-candidate-channel.md) D2), and the module states
that "every user-facing skill a jig scaffold writes at project scope is `jig-`
prefixed" (`skills/_common/skill_discovery.py:23-29`). A scaffolded,
unprefixed `verify` skill is not a jig baseline — it is the project's own — so
discovery will list it as a review candidate (`enumerate_candidates`,
`skill_discovery.py:240`), tiered `speculative` unless its description hits a
category trigger (`skill_discovery.py:195-237`).

## Decision Options Considered

### Option A: Status quo — per-slice scenarios only
Keep spec 118's optional scenario as the only home for runtime evidence;
`.jig/test-command` stays the only per-repo command.
- **Pros:** Nothing to build; 118's boundary stays exactly where it is.
- **Cons:** How to run the app is re-derived per slice and lost between
  sessions. Agents fall back to unit tests, which the post says are easier to
  fool. servo 049 has nothing to call.

### Option B: A "How to run the app" section in the scaffolded primer
Add a section to `templates/CLAUDE.md.template` / `AGENTS.md.template`.
- **Pros:** Always loaded, so the agent cannot miss it; no new file kind.
- **Cons:** Costs context on every turn whether or not the turn touches the
  app — the cost spec 055/057 exists to keep down. Two host primers to keep
  aligned. Prose only: nothing a machine (servo) can call. Primers are
  user-edited and template-rendered, so jig cannot add it to existing projects
  without touching user content.

### Option C: `.jig/verify-command`, analogous to `.jig/test-command`
A tracked one-line file holding the command that boots and checks the app.
- **Pros:** Host-neutral, machine-callable, mirrors a shipped convention
  (including the opt-in `{test}` placeholder, `tdd.py:46-47`).
- **Cons:** Holds no judgment. Booting, driving a UI, what to inspect and which
  steps are flaky do not fit in one command line. Nothing tells the agent to
  run it before committing, so it needs a skill or primer line anyway.

### Option D: A repo-owned `verify` skill with an optional machine entry point
A project skill named `verify` whose body says how to boot, drive, inspect and
tear down the app, and whose frontmatter may declare one `verify-command:` for
machines. scaffold-init writes a stub once; from then on the project owns it.
- **Pros:** Matches the post's practice and where hosts already look for
  skills. Loaded on demand by its description, so it costs no context until
  used. One file holds both the agent's know-how and the machine entry point,
  so they cannot drift apart. Gives servo 049 a command without making every
  project write one.
- **Cons:** No single folder reaches all three hosts (see Context). An
  unprefixed scaffolded skill changes the discovery invariant's wording and
  shows up in review candidate lists. Relies on each host loading a SKILL.md
  with one extra frontmatter key (an assumption, below). A stub nobody fills in
  is noise.

### Option E: Per-host artifacts rendered by jig
jig renders and maintains a Claude skill, a Codex skill and a Copilot skill
(or slash commands) from one source, as it does for its own packages.
- **Pros:** Each host gets its native shape; jig can update them.
- **Cons:** The content is the project's knowledge, not jig's, so jig
  regenerating it would overwrite the owner's edits or need a merge story.
  Three files to keep aligned for what is the same text. More machinery than
  the problem needs.

## Recommended Decision

**Option D.** It is the only option that gives the agent the know-how on
demand and gives a machine a command, in one file the project owns. A pays the
re-derivation cost on every slice. B pays context on every turn and has
nothing to call. C has the command but not the know-how, and would still need
a skill to get used. E makes jig maintain knowledge that belongs to the
project. D's costs (two possible folders, one unprefixed skill in discovery,
an unprobed frontmatter key) are each small and handled below.

1. **The contract is a project skill named `verify`.** It lives in the project
   scope of the host the project uses: `.claude/skills/verify/SKILL.md` (read
   by Claude Code and Copilot CLI) or `.agents/skills/verify/SKILL.md` (read by
   Codex and Copilot CLI). Its bytes are host-neutral — no plugin-root
   variables, no `jig:` skill names, no host primer names — so a project on
   two hosts keeps one copy and links the second folder to it. jig does not
   sync them. Machine consumers look in project scope only, `.claude/skills/`
   then `.agents/skills/`; a user-scope `verify` skill is never this repo's.
2. **Body sections:** Boot, Drive, Inspect, Teardown, Known flaky, and an
   optional Feature map. The description says when to use it: before
   committing a change that affects what the app does, when asked to verify,
   smoke-test or run the app, and when a slice's verification scenario needs
   runtime evidence. The description avoids review-category phrases, so
   discovery tiers it `speculative` for every review category.
3. **Machine entry point (optional):** frontmatter `verify-command:` holds one
   command line, split the way `.jig/test-command` is (`shlex.split`,
   `tdd.py:365`), run from the repository root. Exit `0` = pass, `1` = fail,
   `2` = environment error — tdd.py's normalized codes (`tdd.py:7-11`) and
   spec 118's outcome words. stdout and stderr are the evidence. Absent or
   empty means `not-run`, never pass. A consumer must not pass extra arguments
   unless a later revision of this contract says how (see Open questions).
4. **Ownership:** scaffold-init writes the stub once, only when no `verify`
   skill exists in either project folder, and never overwrites or updates it —
   not on `--force` re-scaffold, not on `migrate copy-machinery`. jig ships the
   stub as a template, never as a loadable skill in any host package, and it
   is not in `scaffold._TIER_SKILLS`. Until the owner fills it in, the stub
   tells the agent to report runtime verification as `not-run`.
5. **Not a gate.** Nothing in jig refuses a transition, review or commit
   because the skill is missing, unfilled or failing. Spec 118's scenario and
   compliance block may name it as the way evidence was produced
   ([spec 128](../specs/128-repo-verify-skill/spec.md) slice 03). Whether a
   verify run becomes a gate input is decided by
   [ADR-0070](./adr-0070-gate-modes-off-observe-enforce.md), not here.
   **What earns the `verify` stamp token.**
   [ADR-0069](./adr-0069-commit-bound-verification-evidence.md) §4 reserves
   `Verified-by: verify` for this ADR to define. It is earned by a slice
   verification scenario whose `Produced via:` line names the `verify` skill,
   with every step `pass` and a code revision equal to the commit the stamp
   names. A scenario produced any other way earns ADR-0069's `scenario` token,
   not `verify`. Reading the line is spec 124's renderer's job (it already
   reads scenario outcomes); spec 128 adds no parser.
6. **Discovery:** the stub is a genuine project skill, not a jig baseline.
   ADR-0040 D2's rule is unchanged (`jig-` prefix = jig baseline); the module
   docstring's "every skill a scaffold writes is `jig-` prefixed" is corrected
   to name the one user-owned exception.
7. **jig dogfoods it.** jig's own repository gets a filled `verify` skill whose
   command scaffolds a throwaway project from the working tree and drives
   jig's real helpers through a slice's lifecycle — what "run the app" means
   for a plugin.

**Relationship to existing decisions.** Spec 118's closed record is not
amended ([ADR-0010](./adr-0010-amendment-scope-records-vs-live-prose.md),
[spec 102](../specs/102-amendment-authorization-guardrail/spec.md)); this ADR
records the revisit. Against 118's non-goals: jig still adds no skill of its
own, no lifecycle state, gate, slice frontmatter field or parser, and no
mandate; jig runs no project's command (only jig's own, in its own repo). The
new thing is a scaffolded file the project owns. ADR-0040 is extended, not
superseded (point 6). [ADR-0011](./adr-0011-spec-gate-model.md)'s
deliberateness posture is unchanged (point 5). ADR-0069 (Proposed) is a
consumer: this ADR fills the one value it left open, and changes nothing else
in it. [ADR-0068](./adr-0068-base-anchored-gate-definitions.md) owns whether a check
definition such as this skill is read from the base ref; this ADR does not add
it to `governance.PROTECTED_PATHS` (`skills/scaffold-init/governance.py:60-67`).

## Consequences

**Becomes easier:**
- An agent finds how to run the app in one place, before committing, without
  that text sitting in every turn's context.
- A slice's verification scenario can point at the skill instead of
  re-describing boot and drive steps.
- servo 049 has a command to call, and a documented `not-run` when a project
  has none.
- jig itself gets checked by running jig, not only by its unit tests.

**Becomes harder:**
- scaffold-init writes one file it never maintains; an owner who deletes it
  gets it back on a `--force` re-scaffold.
- Review candidate lists show `verify` as a speculative candidate.
- Multi-host projects link two folders by hand.
- Existing projects get no stub automatically; they copy the template until a
  `migrate` step is asked for.

## Assumptions

- **Hosts load a SKILL.md with an extra top-level key.** Partial evidence
  only: jig's Codex and Copilot packages already carry `user-invocable: true`
  (`hosts/codex/plugins/jig/skills/tdd-loop/SKILL.md:11`,
  `hosts/copilot/.github/skills/tdd-loop/SKILL.md:11`), and Copilot's builtin
  skills use that key too (spike 113-01 AC2). No host was probed with an
  arbitrary unknown key; spec 128-01's readiness requires that probe.
- **Project-skill folders per host** come from jig's shipped discovery code
  and the 113-01 spike (`copilot skill --help`, CLI 1.0.84), not a fresh probe.
- **Hosts pick a project `verify` skill by its description before a commit.**
  Reported by the post for Claude Code; not probed for any host.
- **servo 049 can work with a whole-app command** (no per-case input). servo
  spec 049 is still a stub, so this is unverified.

## Kill criteria

- Projects leave the stub unfilled: if the first three projects that adopt it
  show no filled Boot section after their first five `DONE` slices, stop
  writing the stub and keep the contract as documentation.
- A host refuses to load the SKILL.md with `verify-command:` and nesting it
  under `metadata:` does not fix it: move the command to `.jig/verify-command`
  (Option C) and keep the skill for the prose.
- Agents on a host never invoke the project skill before committing, even when
  it is filled in: the skill is the wrong carrier on that host; revisit B or C
  there.
- servo 049 needs per-case input that no opt-in extension can express without
  every project implementing it.

## Open questions

- **One file across hosts, or one per host?** (R-002.) This ADR leans to one
  file in the scaffolding host's folder plus a documented link for a second
  host. Should scaffold-init write both folders when a project declares two
  hosts?
- **Top-level `verify-command:` or `metadata.verify-command`?** The open
  Agent Skills format is understood to allow a free-form `metadata` map (not
  verified here); every jig SKILL.md uses flat keys. Decided by the 128-01
  host probe.
- **Per-case input for servo.** If servo 049 needs it, an opt-in `{input}`
  placeholder mirroring `.jig/test-command`'s `{test}` (`tdd.py:46-47`, bug
  021) would keep it optional. Not built until servo 049 asks.
- **Is the verify skill a protected check definition?** A change that edits
  the skill can change the check that judges it (R-002 mechanism 9). Belongs to
  ADR-0068's scope.
- **Existing projects.** A `migrate` step that seeds the stub, mirroring
  `seed-decisions`, once someone asks.
