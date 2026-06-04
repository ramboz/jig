---
dependencies: []
last_verified: 2026-06-04
---

# ADR-0017: Code-health as a scaffolded, language-detected capability

## Status

Accepted (2026-06-04)

## Context

jig has no code-health capability. It scaffolds language-appropriate practices for tests, security, and contracts into the projects it touches, but nothing for the *static-analysis* dimension — linting, formatting, duplication, complexity, dead-code. A 2026-06-04 audit of jig's own repo made the gap concrete: the code is clean (token-level duplication ~1%, zero violations of the [ADR-0002](./adr-0002-extract-helper-on-third-caller.md) inline-mirror policy, high cross-component consistency), but that quality rests entirely on manual discipline plus tests. jig has rich *spec/doc* consistency machinery — `/jig:analyze`, `scripts/spec_lint.py`, the [ADR-0014](./adr-0014-review-evidence-model.md) review-evidence gate, `last_verified` staleness — and **no automated equivalent pointed at code**.

The reflexive fix is to wire a linter into jig's CI. That mis-frames the problem. jig is a *scaffold*: its job is to provision AI-native dev practices for the projects it initializes, not to be a well-linted repo in isolation. The missing thing is not "a `ruff.toml` for jig" — it is "a code-health capability jig offers any project, in that project's own language," exactly as `tdd-loop` gives any project a test/TDD loop without caring whether it runs pytest, vitest, or jest. Under that framing, fixing jig's own gap is just *dogfooding* — the same move we make for every other practice jig ships.

Reframed this way, code-health is **not a new pattern**. It is the fourth instance of one jig already runs three times:

- **`tdd-loop` / `tdd.py`** — detect the ecosystem's test runner (pytest > vitest > jest), normalize to exit codes (0 green / 1 red / 2 env-error), allow a `.jig/test-command` override, *drive don't reimplement*.
- **`security-review`** ([ADR-0013](./adr-0013-security-floor-policy.md)) — orchestrate whatever scanners are installed (bandit = Python, gosec = Go, `npm audit` = Node — already multi-ecosystem), degrade to a heuristic floor when none are present, defer to a richer installed skill. It pairs with the deterministic `jig-secret-scan` hook: prevention in the spine, judgment in the skill.
- **`contracts`** — recommend the canonical per-surface artifact and drive the ecosystem's validator (spectral / ajv / buf / graphql-inspector).

Code-health is the same animal: **detect the language → orchestrate its blessed tools (ruff / eslint+prettier / clippy / `go vet`) → normalize → summarize → degrade gracefully.** A `health.py` that is the static-analysis sibling of `tdd.py`. It rides jig's normal SDLC end-to-end — ADR → spec → `scaffold-init` materializes it → `migrate copy-machinery` flows it to existing projects → `scripts/verify_install.py` asserts it → jig dogfoods it — which is precisely how the [ADR-0013](./adr-0013-security-floor-policy.md) security floor shipped.

Two design forces are genuinely open. This ADR fixes the *framing and direction*; it deliberately leaves the two forks (below) to the implementing spec to resolve with its own alternatives.

## Decision Options Considered

### Option A: jig-repo-local config only (reject the generalization)
Add `ruff` + a CI step to the jig repo and stop there.
- **Pros:** trivial; closes the audit gap in one PR; no new product surface to design or maintain.
- **Cons:** serves only jig-the-repo, not jig's actual users (the projects it scaffolds); leaves every downstream project with no code-health floor; breaks the dogfooding model — jig would *follow* a practice it does not *ship*, the inverse of every other capability. Solves the symptom, not the gap.

### Option B: Scaffolded capability — "detect-and-drive"
A `health.py` + skill that detects the project's ecosystem, orchestrates its *installed* linters / formatters / complexity / duplication tools, normalizes exit codes, and degrades gracefully (heuristic + recommendation) when none are installed. Imposes no tool.
- **Pros:** the exact `tdd-loop` analogy; maximally honors "don't force new language constraints" — it adds nothing, it drives what is already there; multi-ecosystem by construction; dogfoods onto jig cleanly.
- **Cons:** a project with no linter installed gets only a recommendation, not an enforced floor; the value depends on the project bringing its own tools.

### Option C: Scaffolded capability — "scaffold-the-floor"
Everything in Option B, plus: at init / migrate time jig *writes* a sensible default config + CI step for the detected ecosystem (`ruff.toml` for Python, eslint + prettier for Node, …), merging with any existing config rather than clobbering it.
- **Pros:** greenfield projects get a real, enforced floor out of the box; the strongest reading of "help set those up"; still language-appropriate.
- **Cons:** opinionated — it imposes a tool and style choices the dev did not pick (the very thing to be careful about); largest multi-ecosystem maintenance surface; config-clobber risk against a project's existing setup.

## Recommended Decision

**Adopt the scaffolded, language-detected capability (reject Option A), and resolve the detect-vs-scaffold fork by *tiering* it rather than choosing globally:**

- **Tier 1 (always on): detect-and-drive + review** — Option B. The `health.py` detector/runner, plus a *judgment* layer that rides the existing post-implementation **craft pass**. Adds no tool to the project; degrades to a recommendation. This is the floor that is safe for every project, because it forces nothing.
- **Tier 2 (opt-in): scaffold-the-floor** — Option C. For projects that *want* jig to provision the config + CI, materialize a language-appropriate default — idempotent and non-clobbering, reusing the scaffold-mode append-with-marker / refuse-on-unmanaged merge strategy ([ADR-0013](./adr-0013-security-floor-policy.md) / spec 016-02) so an existing lint config is never overwritten. Strictly behind a tier/prompt so it is never imposed.

This keeps "don't force constraints" as the *default* (Tier 1 adds nothing) while still offering the stronger help to those who ask for it (Tier 2).

**Layering (inherit, don't reinvent — [ADR-0011](./adr-0011-spec-gate-model.md) / [ADR-0013](./adr-0013-security-floor-policy.md)):** the *deterministic* parts (running the linter; an "every helper path named in a design doc actually exists" check) live in the **spine** — the target's CI, and optionally a hook. The *judgment* parts (is this duplication within the ADR-0002 mirror budget? is this complexity inherent or fixable?) live in a **reviewer**. Crucially, the read-only reviewer subagent cannot run tools (Read / Glob / Grep only), so the spine *runs* the tools and the reviewer *judges a tight summary* of the results (spec 057's "tight envelope, not a transcript") — never the raw logs. This is the security model verbatim: prevention/measurement deterministic and out-of-band, judgment in the LLM layer, real enforcement never depending on the LLM remembering to run something.

**Settled specifics (resolved during review, 2026-06-04):**
- **Shipped as a new skill, `jig:code-health`** — the static-analysis sibling of `tdd-loop`, not an extension of it (testing and static analysis are different cadences and lifecycles).
- **Duplication: per-language-native first, ephemeral `npx jscpd` fallback.** Prefer the ecosystem's own duplication tool where one exists; otherwise fall back to `npx jscpd` (ephemeral, no install — the Node analogue of `pipx run`), which works on any language; degrade to a recommendation only when neither a native tool nor Node is available. Duplication therefore never *forces* a Node dependency, but is available everywhere Node already is.
- **Judgment rides a distinct reviewer pass** — a dedicated code-health review (consuming `health.py`'s summary), added alongside the existing compliance / craft / arch passes rather than folded into craft. It reuses the read-only `reviewer` agent shape; whether it runs always or is gated (the way arch-review is gated on `arch_review: true`) is left to the spec.

**jig is the first dogfood target.** Closing jig's own audit gap is a *slice* of the implementing spec, not a separate chore — the capability gets proven on a real codebase before it ships.

## Consequences

**Becomes easier:**
- Every scaffolded or migrated project gains a language-appropriate code-health floor through the same path as tests, security, and contracts — one consistent story instead of a special case.
- jig's audit gap closes as a dogfood slice, with the capability validated on a real codebase (jig) before downstream projects rely on it.
- The "jig has a practice it does not itself ship" inconsistency disappears; code-health joins the detect-and-orchestrate family it clearly belongs to.

**Becomes harder:**
- More multi-ecosystem surface to maintain — per-language tool detection (and, for Tier 2, config templates) — a larger version of `tdd-loop`'s runner matrix.
- Tier 2 introduces config-clobber risk and style opinion that must be tightly bounded (idempotent merge, opt-in only).
- Duplication leans on an ephemeral `npx jscpd` fallback, so a project without a native duplication tool gains it only where Node is already present — a bounded, opt-in cross-ecosystem touch rather than a forced dependency.
- A distinct code-health reviewer pass adds per-slice review cost — the turn-count / peak-context lever that specs 055/057 exist to protect — so the spec should weigh gating it (as arch-review is gated) rather than always running it.

## Open questions

One fork remains open for the implementing spec; the other three were resolved during review (2026-06-04) and folded into the Recommended Decision above:

- **Tier placement and the install contract.** Which tier(s) host Tier-1 (detect-and-drive + review) versus Tier-2 (opt-in scaffold-the-floor), and exactly what `scripts/verify_install.py` / the scaffold contract assert about a code-health install. Deferred — to be settled as the spec is sliced.
