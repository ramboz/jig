---
name: security-review
description: >
  Team baseline for security review — a best-effort heuristic security
  pass over a diff or change-set. Auto-triggers for review this for security,
  any vulnerabilities here, security pass on this diff, is this code secure,
  check this for security issues, or security review this. Uses installed
  scanners when available; installs nothing. Defers to any other installed
  skill whose description identifies it as handling security review, SAST, or
  vulnerability analysis, including `adobe-security-*`; prefer it over this
  slim baseline. Do not use for spec-compliance review (use
  `/jig:independent-review`), general PR craft (use `/jig:pr-review`), or
  secret prevention (`jig-secret-scan`).
user-invocable: true
---

> Spec 052 introduced this skill as jig's **team baseline** for security
> review, under [ADR-0013](../../docs/decisions/adr-0013-security-floor-policy.md)'s
> "jig provides the floor; bring your own depth" principle. Like
> `/jig:pr-review` (spec 012), `/jig:arch-review` (spec 014), and
> `/jig:contracts` (spec 022), it ships as SKILL.md only — no `.py`
> helper. It is fundamentally a judgment skill; the determinism it needs
> (detect a scanner on `PATH`, run it, read a diff) Codex runs inline.
> If any other skill is installed whose description identifies it as
> handling security review, SAST, or vulnerability analysis, the Codex
> Code skill router prefers that one over jig's baseline — the deferral
> is **category-based, not name-specific**, so a richer skill named
> anything (`security-review`, `adobe-security-reviewer`, `sast-scan`,
> `vuln-audit`, etc.) wins. Jig's slim version remains the auto-trigger
> when no such skill is installed.

## What this skill does

Produces a **breadth-over-depth heuristic security pass** over a diff, a
branch's changes, or a pasted snippet, in a four-bucket markdown envelope:

1. **Summary** — a one-paragraph read of what changed and the overall
   security posture (clean / needs fixes before merge / needs a deeper
   look).
2. **Blockers** — concrete must-fix security issues. Each cites a
   `file:line` and a one-sentence rationale.
3. **Nits** — lower-urgency hardening suggestions. Same shape as blockers.
4. **Strengths** — security-positive choices worth repeating (parameterized
   queries, secrets read from env, input validated at the boundary).

It works in two modes that compose:

- **Orchestrate-if-present.** When a real scanner (`semgrep`, `bandit`,
  `gosec`, `npm audit` / `osv-scanner`) is on `PATH`, it runs the ones
  present and folds their output into the review. It **installs nothing.**
- **Defer-if-richer.** When a richer security/SAST/vuln skill is installed,
  the router prefers it; jig's baseline yields.

When neither a scanner nor a richer skill is present, the heuristic
baseline below is the floor — even a tooling-less user gets a real,
structured pass. This is **not a SAST engine** and **not a guarantee** —
see [Honest framing](#honest-framing).

## When to use vs. when to defer

There are several things people confuse with this skill. Pick the right one:

- **Any other installed security / SAST / vulnerability-analysis skill.**
  The deferral is **category-based, not name-based**: a skill named
  anything whose description claims security review, SAST, or
  vulnerability analysis is preferred. The routes the Codex router
  may resolve to include **the user's own** skill (commonly
  `$HOME/.agents/skills/security-review/`), **Adobe's `adobe-security-*`
  family** (depth jig deliberately does not ship), or a **built-in
  `security-review`**. If one is present, **defer to it** — explicitly
  invoke it if you want to be sure. The deferral is a router hint, not a
  filesystem probe (see [Gotchas](#gotchas)).
- **`/jig:pr-review`** — sibling jig skill for **general PR craft review**
  (scope / blockers / nits / strengths across correctness, readability,
  test coverage). This skill is the **security lens** specifically. Reach
  for `/jig:pr-review` for overall code-review craft; reach for this skill
  when the question is "is this *secure*?" The two compose: pr-review for
  craft, security-review for the security pass.
- **`/jig:independent-review`** — sibling jig skill for **spec-compliance
  review** of a finished slice (does the implementation satisfy `spec.md`'s
  acceptance criteria?). That is a spec-shape review against a written
  spec. This skill is a diff-shape security review. Reach for
  `/jig:independent-review` when a slice is in REVIEWED-or-similar state
  with a spec.md to evaluate against.
- **The `jig-secret-scan` PreToolUse hook** (spec 052-02) — the secret
  *prevention* floor. It blocks an obvious secret from being written to
  disk at agent-edit time. **This skill is *review*, not *prevention*.**
  The hook stops a secret going in; this skill reads a change-set after
  the fact and flags security issues (including secrets that slipped past
  the hook, e.g. in a file the agent didn't write). They are different
  primitives at different times — keep both.

Rule of thumb: **"is this secure?" → this skill (or the richer installed
one). "does this match the spec?" → `/jig:independent-review`. "is this
good code?" → `/jig:pr-review`. "stop me committing a secret" → the
`jig-secret-scan` hook.**

## Orchestrate installed scanners (never bundle)

This skill **runs the tools you already have; it installs nothing and
bundles nothing.** Before the heuristic pass, detect what is on `PATH` and
run the ones present, folding their findings into the four-bucket envelope.

**Scanner-present path.** For each scanner detected on `PATH`, run it
scoped to the change-set and merge its output:

| Scanner | Surface | Detect | Typical invocation |
|---|---|---|---|
| `semgrep` | Multi-language SAST | `command -v semgrep` | `semgrep --config auto <paths>` |
| `bandit` | Python SAST | `command -v bandit` | `bandit -r <python paths>` |
| `gosec` | Go SAST | `command -v gosec` | `gosec ./...` |
| `npm audit` | JS/TS dependency CVEs | `command -v npm` + `package-lock.json` | `npm audit --json` |
| `osv-scanner` | Cross-ecosystem dependency CVEs | `command -v osv-scanner` | `osv-scanner --lockfile=<file>` |

Treat scanner output as **input to your judgment**, not the verdict:
de-duplicate against the heuristic findings, drop noise that is clearly
out of the change's scope, and promote genuine high-severity hits to
Blockers with the scanner named in the rationale.

**Scanner-absent path (graceful degradation).** When **none** of these is
on `PATH`, say so once in the Summary ("no security scanner detected on
PATH; this is a heuristic-only pass") and fall back to the
[heuristic baseline categories](#heuristic-baseline-categories) — the
review still ships, just without scanner corroboration. Degrading
gracefully to heuristic-only is the designed floor, not a failure mode:
a tooling-less user still gets a structured security pass.

**Never** `pip install`, `npm install -g`, `go install`, or otherwise
fetch a scanner. If a scanner would help and isn't present, note it as a
Nit ("consider wiring `semgrep` in CI") — do not install it.

## Heuristic baseline categories

With no scanner and no richer skill, this is the floor: a structured pass
over the change-set across eight named categories. For each, the bullets
are "what triggers a finding."

- **Secrets** — hard-coded API keys / tokens / passwords / private keys;
  credentials in source, config, or test fixtures; secrets echoed to logs.
  (Prevention is the `jig-secret-scan` hook; this catches what slipped
  past it.)
- **Injection** — string-built SQL / shell / LDAP / NoSQL queries;
  unescaped interpolation into commands or templates; `eval`-on-input.
- **Authn/authz** — missing or post-hoc authorization checks; broken
  object-level access (IDOR); trusting client-supplied identity / roles;
  auth logic that fails open.
- **Crypto misuse** — weak or broken algorithms (MD5/SHA-1 for security,
  DES, ECB mode); hard-coded keys/IVs; `Math.random()` for tokens;
  homegrown crypto; missing TLS verification.
- **Input validation** — unvalidated/unsanitized external input crossing a
  trust boundary; missing bounds/type checks; path traversal from
  user-controlled paths; SSRF from user-controlled URLs.
- **Unsafe deserialization** — `pickle` / `yaml.load` / Java
  native-deserialization / `Marshal` on untrusted data; type confusion
  from untrusted object graphs.
- **Dangerous functions** — `eval` / `exec` / `system` / `subprocess
  shell=True` / `child_process.exec` on dynamic input; reflection or
  dynamic import driven by user input.
- **Dependency risk** — pinned-to-vulnerable or unpinned dependencies;
  known-CVE packages; abandoned/typosquat-shaped names; lockfile drift.
  (A `npm audit` / `osv-scanner` run, when present, corroborates this
  category.)

The pass is **breadth over depth**: catch the obvious across any
language/stack, and leave the deep language-specific antipatterns and
exhaustive rulesets to a real SAST tool or a richer installed security
skill.

## Review structure / output

Emit a markdown report with exactly these four H2 sections — the same
four-bucket envelope jig's other review skills use:

```markdown
## Summary
<one paragraph: what changed, the security posture, and — if no scanner
was on PATH — a one-line "heuristic-only pass" note>

## Blockers
- `path/to/file.py:42` — <category>: <one-sentence rationale>. Must fix
  before merge because <why>.
- (or: "None.")

## Nits
- `path/to/file.py:7` — <category>: <one-sentence hardening suggestion>.
- (or: "None.")

## Strengths
- <security-positive choice>. Worth repeating because <why>.
```

If a section is empty, write "None." rather than omitting the heading.
Blockers and Nits cite `file:line` so the finding is actionable.

### Worked example

Suppose the diff is:

```diff
+ DB_PASSWORD = "hunter2"
+
+ def find_user(name):
+     q = "SELECT * FROM users WHERE name = '" + name + "'"
+     return db.execute(q)
+
+ def token():
+     return hashlib.md5(str(random.random()).encode()).hexdigest()
```

A baseline review (no scanner on PATH) would read:

```markdown
## Summary
Adds a user lookup and a token helper to the auth module. No security
scanner detected on PATH — this is a heuristic-only pass. Two blockers:
a hard-coded DB password and a SQL injection in the lookup.

## Blockers
- `auth.py:1` — secrets: `DB_PASSWORD` is hard-coded. Must fix before
  merge because the credential lands in version control; read it from an
  env var or secret manager instead.
- `auth.py:4` — injection: `find_user` builds SQL by string
  concatenation on `name`. Must fix before merge because an attacker
  controls `name`; use a parameterized query.

## Nits
- `auth.py:7` — crypto misuse: `token()` uses MD5 over `random.random()`,
  which is not cryptographically secure. Prefer `secrets.token_hex()`.

## Strengths
- The functions are small and single-purpose, which makes the security
  fixes localized and easy to verify. Worth repeating.
```

Notice: no exhaustive per-language ruleset, no CVE database lookup, no
taint-tracking. That depth belongs in a real SAST tool (run via
orchestration) or a richer installed security skill, not the baseline.

## Honest framing

This skill is a **best-effort heuristic baseline, NOT a guarantee.** It
does not prove the absence of vulnerabilities. A clean review here does
**not** mean the code is secure.

It is **not a substitute** for:

- **CI security scanning** — SAST (semgrep/CodeQL), secret-scanning,
  dependency/CVE monitoring running on every push, server-side, outside
  the agent's trust boundary.
- **A dedicated security review** — a human security engineer with full
  threat-model context, or a richer installed security skill (the user's
  own, Adobe's `adobe-security-*`).
- **The `jig-secret-scan` hook** — that covers secret **prevention** at
  edit time; this skill covers **review** after the fact. Different
  primitives; keep both.

The real controls are **out-of-band** — consistent with
[ADR-0013](../../docs/decisions/adr-0013-security-floor-policy.md) and
[ADR-0011](../../docs/decisions/adr-0011-spec-gate-model.md)'s honesty
boundary: CI SAST + secret-scanning, dependency monitoring, and branch
protection are what actually enforce security. jig raises the floor; it
does not replace them. Say so in the review when the stakes warrant it
(e.g., recommend wiring a CI SAST gate as a Nit).

## Gotchas

- **The deferral hint is the routing mechanism, not a code path.** Jig's
  description tells Codex "prefer any other installed
  skill whose description identifies it as handling security review,
  SAST, or vulnerability analysis." There is no filesystem probe, no
  plugin-precedence lookup, no name-matching against `security-review`
  specifically. The deferral is **category-based**: a richer skill named
  anything that claims that surface area wins. If the router consistently
  picks jig's baseline over such a skill, jig's description is too greedy
  — open an issue.
- **Lightweight is a feature, not a limitation.** The baseline does not
  ship a bundled SAST engine, a CVE database, per-language reference
  rulesets, or taint analysis. It orchestrates the scanners you have and
  falls back to eight heuristic categories. If you find yourself wishing
  the baseline did more, you are in the target audience for installing a
  richer security skill at the user scope (commonly
  `$HOME/.agents/skills/security-review/`) or Adobe's `adobe-security-*`.
- **Heuristic ≠ SAST engine.** The eight categories are pattern-level
  cues a careful reviewer would check, not a sound static analysis. False
  negatives are expected; that is exactly why the [Honest framing](#honest-framing)
  section says this is not a guarantee and points to out-of-band scanning.
- **Review, not prevention.** Do not confuse this skill with the
  `jig-secret-scan` hook. The hook blocks a secret being written; this
  skill reviews a change-set. A secret can still appear in a file the hook
  never saw (an existing file, a generated artifact) — this skill is where
  that gets flagged.
- **Scanner output is input, not verdict.** When a scanner runs, fold its
  findings into your judgment: de-duplicate, drop out-of-scope noise, and
  name the scanner in the rationale of any finding you promote. A raw
  scanner dump is not a review.

## Relationship to other skills

- **`jig-secret-scan` hook** (spec 052-02) — the secret **prevention**
  floor: a PreToolUse hook that blocks an obvious secret from being
  written at agent-edit time. This skill is the **review** counterpart;
  the hook is prevention, this is detection-after-the-fact. They compose:
  the hook is the gate, this skill is the second look.
- **`/jig:pr-review`** — sibling baseline for general PR craft review
  (correctness, readability, tests). This skill is the security lens; run
  both for a full picture. Same four-bucket envelope, different lens.
- **`/jig:independent-review`** — sibling skill for spec-compliance review
  against `spec.md`. Different shape (spec-shape, not diff-shape security).
  See "When to use vs. when to defer" above.
- **Adobe's `adobe-security-*` family** — the depth jig deliberately does
  **not** ship (full SAST, deep IaC/cloud rules, exhaustive per-language
  dangerous-function rulesets per ADR-0013). When installed, the router
  prefers it over this baseline; jig yields. This baseline exists so a
  non-Adobe user with nothing installed still gets a real security pass.
