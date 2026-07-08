> Status: Draft (wizard-generated equivalent — manually seeded for jig itself)
>
> Changes to this file require explicit human approval. Do not modify via agent without confirmation.

# Conventions: jig

## Skill authoring

**Rule:** Every skill description follows: `<verb-led summary>. Use when <specific triggers>. Do not use for <common false positives>.`
**Why:** The description is a trigger, not a summary. Vague descriptions don't fire. Overly broad descriptions fire on irrelevant prompts.
**How to apply:** Write the description, then read it aloud. Does it start with a verb? Is the trigger clause specific enough to distinguish from 3 similar prompts you might type? Is the negative clause present?

**Rule:** One skill, one job. No mega-skills.
**Why:** Splitting improves triggering accuracy. Kitchen-sink skills are the most common failure mode (ECC).
**How to apply:** If a skill handles commits AND PRs AND branch naming AND changelogs, split it.

**Rule:** Every skill has a `## Gotchas` section.
**Why:** Gotchas accumulate failure points over time. They're the highest-signal content in a skill file.
**How to apply:** Add gotchas as you discover them, not upfront. A skill with no gotchas is either perfect or hasn't been used yet.

**Rule:** Stubs use `disable-model-invocation: true`.
**Why:** An unimplemented skill that auto-triggers is worse than no skill — it interrupts the user with a DRAFT warning.
**How to apply:** All skills without a corresponding implemented spec use `disable-model-invocation: true`.

**Rule:** Skills are host-neutral and never restate agent hygiene the host prelude already guarantees on **both** Claude Code and Codex.
**Why:** jig renders one skill source per host. Content both host base prompts already enforce — batching independent tool calls, citing code as file:line, bias-to-action, skipping tool-call preamble — is pure context cost with zero marginal effect (cost = context × turns), and restating only one host's guarantee breaks host-neutrality.
**How to apply:** Write to the *intersection*: assume the host handles generic tool-use hygiene; spend prose only on jig-specific procedure and judgment. Do state things *not* in the intersection when they matter (e.g. reversibility caution — Codex's prelude is more action-biased than Claude's). Instructing a subagent/reviewer on the exact output format it must emit is an output contract, not a restatement — keep it.

**Rule:** A skill steers the *shape and length* of the output it induces, not just the process it follows.
**Why:** jig's conventions govern skill *triggering* but not the verbosity of the agent output a skill produces when it runs — which spends the context × turns budget unpriced. The review and scan families already enforce this ad hoc; this rule promotes it from per-skill habit to convention.
**How to apply:** If a skill's natural output can balloon (reviews, scans, explainers, reports), give it one of: a hard numeric cap with a truncation note (`analyze`), a "shape to content — don't default to bullets" clause, or "emit findings only, `None.` over omission" (`pr-review`). Never instruct "define every term" / "no hard cap".

## Hook authoring

**Rule:** Hooks use `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>.sh` — never bare names.
**Why:** `bin/` PATH injection is Bash-tool only. Hook commands need the full path.
**How to apply:** Every hook command in `hooks.json` must start with `bash ${CLAUDE_PLUGIN_ROOT}/`.

**Rule:** Hook scripts use Python 3 for JSON parsing — never `jq`.
**Why:** `jq` is not installed by default on macOS. Python 3 is reliable everywhere.
**How to apply:** Use `python3 - <<'EOF' ... EOF` in hook scripts for JSON work.

**Rule:** Non-blocking hooks exit 0 with JSON stdout. Blocking hooks exit 2 with stderr message.
**Why:** Exit code 2 is the only blocking mechanism. Anything else either fails silently or errors noisily.
**How to apply:** `{ "continue": true, "additionalContext": "..." }` for informational hooks; `echo "reason" >&2 && exit 2` for gates.

**Rule:** All hooks are non-blocking in the starting move. Gates are introduced per spec.
**Why:** A premature block with no escape hatch is worse than no block.
**How to apply:** Wire the gate hooks; implement their blocking logic only when the corresponding spec slice is done.

**Rule:** Hook messages are terse, single-concern, and self-labeling.
**Why:** A hook's `additionalContext` lands directly in the agent's context every turn it fires (context × turns again), and an unlabeled injection reads as if the user authored it. Production agent prompts cap machine-surface messages hard and flag injected context explicitly.
**How to apply:** One concern per message — no multi-paragraph essays in `additionalContext`. Lead with what it is (`jig gate:` / `jig hint:`) so the agent doesn't attribute it to the user. Blocking-hook stderr (exit 2) states the reason **and** the escape hatch in one or two lines, no markdown.

## Agent authoring

**Rule:** Reviewer agent has read-only tools: `Read`, `Glob`, `Grep` only.
**Why:** Reviewers cannot be trusted not to modify the work they're reviewing.
**How to apply:** The `tools` list in `agents/reviewer.md` must never include `Write` or `Edit`.

**Rule:** Reviewer system prompt must include: "You are seeing this work for the first time."
**Why:** Breaks the implicit assumption of shared context.
**How to apply:** First paragraph of every reviewer invocation prompt.

## Document conventions

**Rule:** Every wizard-generated doc carries `Status: Draft (wizard-generated)` at the top.
**Why:** Distinguishes generated stubs from deliberate content.
**How to apply:** scaffold-init adds this marker. It flips to `Stable` after 3-5 reconciled specs via a `scaffold-stable` ADR.

**Rule:** Deferred decisions use the format: `> **Deferred — <reason>. Will be decided in the first <X>-touching spec.**`
**Why:** Explicit deferral is honest. Silent gaps get forgotten.
**How to apply:** Any time scaffold-init doesn't have enough signal to fill a section.

**Rule:** ADRs are immutable after acceptance.
**Why:** Editing history destroys the audit trail that makes ADRs valuable.
**How to apply:** New decision → new ADR with `Supersedes: ADR-NNNN`. Never edit an accepted ADR.

**Rule:** New slices use the slice template at `templates/docs/specs/slice-template.md`. New ADRs use `templates/docs/decisions/adr-0000-template.md`. Both carry a YAML frontmatter block with `status`, `dependencies`, and `last_verified` fields (slice 015-01).
**Why:** Typed frontmatter lets `workflow.py` validate dependency satisfaction on `→ DONE`, stamp `last_verified` on `→ RECONCILED`, and surface stale items via `workflow.py stale`. Free-text prose markers can't do this.
**How to apply:** Copy the template, replace placeholders, and treat the frontmatter as the source of truth for the slice's state. Legacy slices using prose `**STATUS:** DRAFT` markers continue to work via lazy migration — no retroactive mass rewrite. Do not invent new frontmatter fields without updating `_common/parsing.py` and the related templates together.

**Rule:** Deferred slices use the `DEFERRED` lifecycle state, not `DRAFT` + prose annotations (slice 015-02).
**Why:** `DEFERRED` is rendered as a dedicated section in the status board with `**Resolution trigger:**` as the per-row context — discoverable in one place. Prose annotations on `DRAFT` slices look like in-progress work and don't index.
**How to apply:** Transition with `workflow.py transition <spec.md> <slice> DEFERRED`. Add a `**Resolution trigger:** <condition>` line in the slice body that names the concrete signal that would re-open the slice. Re-open via `transition <slice> DRAFT` — `DEFERRED` may only transition to `DRAFT` (or stay `DEFERRED` idempotently); all other targets are refused.

**Rule:** Permanently dropped slices use the `ABANDONED` lifecycle state, not `DEFERRED` or `DRAFT` + prose annotations (slice 085-01).
**Why:** `DEFERRED` means parked-but-resumable, with a stated resolution trigger — it misrepresents work that's permanently dropped as still-pending. `ABANDONED` renders in its own dedicated status-board section with `**Abandonment reason:**` as the per-row context, and is excluded from the spec-level rollup the same way `DEFERRED` is (a spec where every slice is `ABANDONED` rolls up to `ABANDONED` itself). Distinct from marking already-shipped (`DONE`) work as abandoned/removed — that's a different, unbuilt concept; `ABANDONED` only applies to work that never reached `DONE`.
**How to apply:** Transition with `workflow.py transition <spec.md> <slice> ABANDONED` from any pre-`DONE` state (`DONE → ABANDONED` is refused). Add a `**Abandonment reason:** <why>` line in the slice body. Re-open via `transition <slice> DRAFT` — `ABANDONED` may only transition to `DRAFT` (or stay `ABANDONED` idempotently); all other targets are refused. The transition also prints a one-time, non-blocking warning naming any live dependent elsewhere in the project — advisory only, it never cascades.

**Rule:** `templates/` files that should be hand-edited at slice-creation time (rather than substituted at scaffold-init time) use the `.md` suffix, not `.md.template`.
**Why:** `scaffold-init` globs `templates/docs/**/*.md.template` and refuses on any unrendered `{{KEY}}` placeholder. A slice or ADR template carrying `{{NUMBER}}` / `{{NAME}}` placeholders meant for future slice authors would block scaffold-init.
**How to apply:** Hand-edited templates → `.md`. Scaffold-time-substituted templates → `.md.template`. Existing precedent: `templates/docs/decisions/adr-0000-template.md` and `templates/docs/specs/slice-template.md` both use `.md`.

**Rule:** Elicitation slots in `product-vision.md` and `architecture.md` carry a section-head marker comment. For `unfilled` or `skipped` sections: `<!-- elicited: <date-or-PENDING> / status: <unfilled|skipped> -->`. For `filled` sections: `<!-- elicited: <date> / status: filled / hash: sha256:<first-12-hex> -->` (slice 017-01 + 017-03).
**Why:** The three-state convention (`unfilled` / `filled` / `skipped`) lets `/jig:vision-elicitation` (slice 017-02) detect which sections need attention on first run, and (slice 017-03) detect manual edits between runs via the `hash:` field. The `hash:` value is SHA-256 of the section body (bytes between the marker line and the next H2 heading; whitespace-trimmed at both ends), encoded as the first 12 hex characters of the digest — prefix `sha256:` makes the algorithm explicit and forward-compatible. `PENDING` is the wizard-default placeholder; concrete ISO dates appear once a section gets filled.
**How to apply:** Every H2 section in `templates/docs/product-vision.md.template` starts with `<!-- elicited: PENDING / status: unfilled -->`. The four elicitation slots in `templates/docs/architecture.md.template` (Repository structure / Tech stack / Module boundaries / Data model) each carry the same marker; two sibling sections (Core architecture decisions, Open questions) deliberately carry no marker — they're populated by ADRs over time and by `refinement-todo.md` references, respectively. Hand-filling a slot? Replace `PENDING` with today's ISO date, flip `unfilled` to `filled`, and append `/ hash: sha256:<first-12-hex>` computed over the section body. Skipping a section? Flip to `skipped` (no hash field needed — skipped sections have no canonical body). Hand-editing a previously-`filled` section is valid; 017-03's re-run mechanics detect divergence by recomputing the hash and offering refresh / skip / diff. **Body bounds for hashing:** the section body is everything between the marker line and the next H2 heading at the document root (not inside fenced code blocks — `## …` lines inside ```` ``` ```` fences are content, not headings). For the *last* H2 section in a document (no trailing H2 to terminate on), the body extends to EOF. Whitespace at both ends is trimmed before hashing so a trailing newline doesn't change the digest.

