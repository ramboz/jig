---
status: Proposed
dependencies: [adr-0011, adr-0014, adr-0055]
last_verified: 2026-11-21
frame_review: true
---

# ADR-0070: Gates ship with off, observe, and enforce modes

## Status

Proposed (2026-11-21)

## Context

jig's refusing gates are binary. Each is on by default and has a
deliberate escape: an env var that turns it off for the session. That is the
model [ADR-0011](./adr-0011-spec-gate-model.md) settled: a gate inside the
agent's trust boundary is a deliberateness signal, and real control is
out-of-band (CODEOWNERS, CI, branch protection). [Spec 078](../specs/078-gate-bypass-telemetry/spec.md)
then made the escapes visible by logging a `gate_bypassed` event when a gate
honours its override (`skills/_common/gate_telemetry.py:24-52`), and
`workflow.py gate-stats` counts them (`skills/spec-workflow/workflow.py:3221`).

Probed 2026-11-21, jig has ten refusing gates, plus nudges that never
refuse:

- **CLI gates** (a helper raises and exits 2): review-evidence
  (`JIG_REVIEW_EVIDENCE_GATE`; `workflow.py:919`, `adr.py:933`,
  `review_evidence.py:830`), scaffold-precondition (`JIG_SCAFFOLD_PRECONDITION`;
  `workflow.py:4544`, `adr.py:675`), start-collision (`JIG_START_COLLISION_GATE`;
  `workflow.py:5283`), cross-ref (`JIG_CROSSREF_GATE` plus `--reopen`;
  `workflow.py:5512`, `land.py:213`), and four bug gates
  (`JIG_BUG_DIAGNOSE_GATE`, `JIG_BUG_MAIN_CHECK_GATE`, `JIG_BUG_CLOSURE_GATE`,
  `JIG_BUG_TEST_GATE`; `bug.py:894-989`).
- **Hook gates** (PreToolUse, exit 2): the conventions spec-gate
  (`JIG_CONVENTIONS_APPROVED=1`; `hooks/scripts/jig-spec-gate.sh:61-81`) and
  secret-scan (`JIG_SECRET_SCAN_APPROVED=1`; `hooks/scripts/jig-secret-scan.sh:31`).
  These are the only two hooks that can block (`docs/architecture.md:185`).
- **Nudges** such as the entry gate, git freshness, boundary-change warn and
  post-edit verify. They inject context or stay silent, never refuse, and
  have an opt-out at most.

The switch has four separate implementations: the shared
`env_gate_enabled` helper (`skills/_common/parsing.py:88-99`), a private copy
in `bug.py` (`_DISABLE_VALUES` at `bug.py:95`, `_gate_enabled` at
`bug.py:216`), and inline literals in the two hooks (the spec-gate accepts
`1/true/yes/on`, secret-scan only `1`). Bypass logging is uneven: the review-evidence
gate logs from `transition` but not from `adr.py accept` or bug evidence; the
scaffold-precondition, bug and secret-scan gates log nothing.

Two gaps follow. First, a gate can only be **on or off**. There is no way to
run a check, see what it would have refused, and decide whether it is right
before it starts refusing. So a new gate either ships enforcing (and its false
positives land on whoever hits them first) or stays a nudge, and several
deferred items in `docs/refinement-todo.md` are parked on exactly that
choice. Second, `gate-stats` only counts bypasses. Its own legend says the
counts have "no denominator of respected fires" (`workflow.py:3279-3284`), and
the deferred entry "gate-bypass digest denominator" waits for a maintainer who
wants "to make a keep/retire decision on a gate *from data*".

The trigger for deciding now is the Claude Code team's verification post,
read in [R-002](../research/R-002-claude-code-verification-assessment.md)
(item 11). Their commit gate has three modes: "Observe mode will log what
would have been blocked, so that we can review any false positives and ensure
no one is impacted." Enforce blocks, but a commit can carry an explanation
instead of verification; and "If commits have been blocked twice in the
session, the next one will be allowed through so Claude doesn't get stuck."
Item 6 adds: "When a check pulls in a reviewer, it should say why". R-002
rejects "make everything enforcing immediately" for jig on these grounds.

Two constraints frame the choice. [ADR-0055](./adr-0055-leanness-lens-folds-into-existing-passes.md):
no new gate. This ADR is a mechanism for the gates jig already has and the
ones later specs add. And [ADR-0011](./adr-0011-spec-gate-model.md): modes
change how a gate behaves in process; they do not turn any gate into
human-only control.

## Decision Options Considered

### Option A: Status quo — binary gates, env bypass, bypass log
- **Pros:** No change. Every gate already has a documented deliberate escape
  and the important ones log it.
- **Cons:** No way to trial a gate before it refuses. `gate-stats` cannot
  answer keep/retire. A bypass carries no reason and covers a whole session.
  Four readers of the switch drift (the bug gates already have their own
  falsey set).

### Option B: Per-gate modes through one resolver, with recorded fires and a reasoned override (recommended)
Every refusing gate resolves `off | observe | enforce` through one shared
helper. The existing env var keeps its meaning and accepts the mode words; a
project can also set the mode in `scaffold.json`. Observe runs the check and
records what it would have refused. Enforce refuses and records the refusal.
A lifecycle transition can pass one named gate with a written reason that is
kept on the slice or bug record.
- **Pros:** New gates can be trialled; existing ones can be relaxed to
  observe instead of off, which still records. The recorded fires are the
  denominator 078 deferred. One reader of the switch for all ten gates. No new
  gate (ADR-0055). Defaults keep today's behaviour exactly.
- **Cons:** A config surface (`gates.<name>.mode`) that a change can edit, so
  it inherits the base-anchoring question [ADR-0068](./adr-0068-base-anchored-gate-definitions.md)
  owns. Hook gates gain an import of a shared helper, which is a new failure
  mode to guard. More event types in the 078 sink.

### Option C: One global mode for all gates
A single `JIG_GATE_MODE=observe` (or one `scaffold.json` key) flips every gate
at once.
- **Pros:** Smallest surface; one knob to document.
- **Cons:** Too coarse for the rollout it exists for: trialling one new gate
  would relax all the others. The post's modes are per gate, and jig's gates
  guard very different things (a secret in a file vs. a missing review).

### Option D: Adopt the post's valves on every gate
Option B plus the anti-stuck valve everywhere: after two refusals in a
session, the next attempt passes.
- **Pros:** No session can loop on a gate.
- **Cons:** Wrong for every gate jig has. The post's gate checks whether a
  step was skipped, and the pass-through is recorded as "none", so it stays
  honest. jig's gates guard things with a remedy in reach: record the review,
  remove the secret, set the approval. A third retry of a stray
  `conventions.md` edit or a secret write is exactly what those gates exist
  to stop. A lifecycle gate that keeps failing is a case for a person (spec
  129's round cap), not for letting it through.

## Recommended Decision

**Option B.**

1. **Three modes, one meaning each.**
   - `off`: the check does not run; the gate records a `gate_bypassed` event
     (spec 078, unchanged).
   - `observe`: the check runs; a violation is allowed and recorded as
     `gate_would_block`. Nobody is stopped. CLI gates print a one-line
     `would block` note; hook gates stay silent to the agent.
   - `enforce`: the check runs; a violation is refused (today's behaviour) and
     recorded as `gate_blocked`.
2. **One resolver, fixed precedence.** A shared `_common` helper resolves a
   named gate's mode: the gate's env var, then `scaffold.json`
   `gates.<name>.mode`, then the gate's default. Existing env vars keep their
   meaning (`0/false/off/no` = off) and also accept `observe` and `enforce`;
   the hook gates' approval vars (`JIG_CONVENTIONS_APPROVED=1`,
   `JIG_SECRET_SCAN_APPROVED=1`) resolve as `off`. An unrecognised value
   falls back to the gate's default with a warning; a typo never turns a gate
   off. Every event records where the mode came from (`env`, `config`,
   `default`).
3. **Defaults keep today.** All ten gates default to `enforce`, except
   bug-diagnose, which keeps its current tier split (refuse on `gnarly`, warn
   on `standard`; `bug.py:894-903`). A gate added after this ADR is born
   `observe` unless its spec argues for `enforce` from day one (a security
   floor gate might).
4. **A refusal says why.** Every block and would-block names the gate, the
   rule it enforces (ADR or spec), why this case tripped it, the mode and
   where it came from, and the ways forward. That is the post's "it should say
   why", applied to gates. Say-why checks inside existing review passes
   belong to spec 127 ([ADR-0072](./adr-0072-diff-triggered-review-rules.md));
   pulling in an extra pass or a person stays open (ADR-0072 open
   question 1).
5. **Promotion is deliberate and recorded.** `gate-stats` reports blocked,
   would-block, bypassed and overridden counts per gate and lists recent
   fires for false-positive review. A gate moves `observe → enforce` (or back)
   by a config or code change recorded as a lightweight decision that cites
   the window it looked at. No automatic promotion.
6. **Two valves, scoped.**
   - **Reasoned override** (built now): `workflow.py transition` and
     `bug.py transition` take `--override <gate> --reason "<why>"`, which
     passes one named gate for one transition and appends the reason to the
     record's `## Gate override log`, mirroring the `--release --reason`
     release log (`workflow.py:5638`). The event records that an override
     happened, not the text, so the 078 sink stays content-free. Hooks keep
     their approval vars.
   - **Anti-stuck release** (specified, not built): a gate may declare that
     after two refusals in a session the next attempt passes and is recorded.
     Only for session-scoped gates whose refusal means "a step was skipped"
     and whose pass-through is itself recorded (for example, a
     verification stamp of `none`). All ten current gates declare it off (see
     Option D). It is built with its first consumer.
     [ADR-0069](./adr-0069-commit-bound-verification-evidence.md) records
     verification stamps (`none` included) and leaves blocking on them to
     this ADR; this ADR adds no commit or landing gate either (no new gate).
     If one is proposed, it is born on the resolver in `observe` and is the
     natural first user of this valve.
7. **Scope.** Modes apply to gates that can refuse. Nudges keep their
   opt-outs and nothing else. Host permission floors (Claude
   `permissions.deny`, Copilot's `jig-permissions-floor` hook) are not jig
   gates in this sense and are untouched.
8. **Out-of-band control is unchanged.** Modes are a deliberateness and
   rollout mechanism inside the trust boundary, as ADR-0011 says. Setting a
   gate to `observe` is as deliberate as setting it to `off` today, and better
   recorded.

**Relationship to existing records.** Extends ADR-0011 (adds an observed
state between "bypassed" and "enforced"; the threat analysis and the
out-of-band recommendation stand) and spec 078 (new event types in the same
sink; `gate-stats` grows rather than being replaced). Honours ADR-0055 (no new
gate). The gates owned by ADR-0013, ADR-0014, ADR-0016, ADR-0037 and ADR-0058
become mode-aware with their rules and defaults unchanged; `=0` keeps
meaning off, as ADR-0016 §2 and `docs/workflow.md` state it. **Amends no
ADR.** If the owner reads the widened env-var values as a change to
ADR-0016's bypass contract, that needs an `## Amendments` entry with explicit
owner approval (spec 102); this ADR does not write one.
[ADR-0060](./adr-0060-unattended-execution-write-boundary.md) (Proposed,
acceptance deferred) is complementary: an unattended executor could set a
gate's env var to `enforce` for its runs, but who owns the hard-deny at the
write boundary stays ADR-0060's decision. [ADR-0068](./adr-0068-base-anchored-gate-definitions.md)
§2 lets other gates opt in to base-ref reads "when they gain a
project-editable definition". The `gates` block is one, so it is read through
that seam once spec 123 builds it, and from the working tree (with
`mode_source` recorded) until then. PR #230's
convention-rule `advisory` / `enforced` states are the same posture applied to
review rules judged by a model; see Open questions.

## Consequences

**Becomes easier:**
- A new gate can ship in `observe`, collect would-block events, and be
  promoted from evidence. Deferred items stuck between "nudge" and "hard
  gate" get a cheaper first step when their triggers fire (the
  `docs/decisions/**` PreToolUse gate, CI consumption of `check-reviews`,
  code-staleness gating).
- A project adopting jig can run a gate in `observe` instead of turning it
  off, and still see what it would have caught.
- `gate-stats` can answer keep/retire from data: fires versus bypasses. This
  meets the trigger of the "gate-bypass digest denominator" entry.
- Overriding a lifecycle gate leaves a written reason on the record, where
  the reconciliation reviewer sees it, instead of a reasonless session-wide
  env var.

**Becomes harder:**
- `scaffold.json` gains a block that can weaken a gate from inside a change.
  Until ADR-0068 settles base-anchored reads, the mitigation is visibility:
  every event carries `mode_source: config`, and `gate-stats` prints each
  gate's current mode.
- Hook gates import a shared helper. Any import or read failure must fall back
  to `enforce`, today's behaviour, and that needs a test per hook.
- The 078 sink carries four event types instead of one; readers must keep
  filtering by `event`.
- Observe on a lifecycle gate lets a slice advance without the evidence. The
  review-passed DoD box must not be auto-ticked in that case, or it stops
  meaning "a passing review exists".

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **Grounded (2026-11-21):** the ten-gate inventory, the three switch readers
  and the uneven bypass logging cited in Context; `scaffold.json` is already
  read by a hook, fail-open (`hooks/scripts/lib/protected_paths.py:74`); a
  per-session state file keyed on `session_id` already exists
  (`hooks/scripts/lib/entry_gate.py:272`); `--release --reason` already writes
  a dated log on the slice (`workflow.py:5638`, `:5888`).
- **Grounded, cross-repo:** servo's oracle-hook already blocks a stop once and
  lets the next through (`servo/skills/oracle-hook/SKILL.md:76`), the same
  shape as the anti-stuck valve.
- **Not re-probed, host-sensitive:** Codex runs plugin hook gates only after
  the user trusts them through `/hooks` (`docs/architecture.md:241-243`), and
  its `session_id` handling is recorded as degraded
  (`docs/architecture.md:63-64`). Copilot maps exit 2 to a deny through the
  adapter's `--enforce` mode (`skills/scaffold-init/copilot_hook_adapter.py:85-99`)
  and maps `sessionId` (`:213-214`); neither was run live for this ADR.
  Observe mode exits 0 on every host, so it is host-uniform; enforce keeps
  each host's current semantics. The deferred anti-stuck valve is the part
  that would depend on reliable session ids.
- **Owner call:** whether reasons written to `## Gate override log` in
  committed records are acceptable. The release log sets the precedent.

## Kill criteria

- Six months after 125-02 lands, no gate has run in `observe` (no
  `gate_would_block` events, no `observe` in any config) and no new gate was
  born in `observe`. Then the modes are dead weight; collapse back to
  on/off and keep only the fire counts.
- `observe` is found left on a gate in a real project for weeks with unread
  would-block events, acting as a quiet `off`. Then add an expiry to
  `observe` config, or drop `observe` from the config surface and keep it
  env-only.
- The shared resolver causes a hook gate to block falsely or allow silently in
  practice. Then revert the hook gates to inline checks and keep modes for CLI
  gates only.

## Open questions

1. Should the `gates` block join `governance.PROTECTED_PATHS`
   (`skills/scaffold-init/governance.py:60-67`), so lowering a gate's mode
   needs owner review? ADR-0068 asks the same of `scaffold.json` as a whole
   (its open questions); one answer should cover both.
2. Vocabulary with PR #230 (unmerged; its ADR and spec numbers are
   provisional). Its `advisory` / `enforced` rule states and this ADR's
   `observe` / `enforce` gate modes describe the same posture (report, do not
   block / block) for different checkers: a rule a reviewer weighs vs. a
   deterministic gate. Proposal: keep both words, share one promotion rule
   and the `gate-stats` report, and let whichever merges second add the
   mapping to the glossary. A rule has no `off`; deleting it is off.
3. Should `review.py check-reviews` honour the resolved mode when CI runs it
   (the deferred "CI consumption of `check-reviews`" entry)? Not decided here;
   `check-reviews` stays a validator that exits 2 when evidence does not clear.
4. Is `--override` needed on `adr.py accept`, `land.py execute`, and
   `workflow.py new`? This ADR limits it to the two lifecycle `transition`
   commands, where a record exists to hold the reason.
5. Should `observe` in config carry a `since:` date so `gate-stats` can flag a
   gate that has been observed for longer than a set window?
