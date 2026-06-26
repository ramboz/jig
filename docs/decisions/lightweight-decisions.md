# Lightweight Decisions

Small shipped decisions that fall outside spec slices but carry durable rationale:
brand/icon swaps, cosmetic CSS polish, UI string or translation choices, scoped
visual decisions, and "future sessions should/should not override this" notes.

## When to write here vs. an ADR

**Write here (lightweight)** if the decision **both**:
- (a) does **not** change a module boundary, public contract, or cross-cutting
  policy (if it does → ADR), and
- (b) a future agent or maintainer **would need to know it to avoid undoing it**.

**Write an ADR** if (a) fails — the decision changes a module boundary, public
contract, or cross-cutting policy.

**Write nothing** if it's already obvious from the code or a commit message.

**Write to `refinement-todo.md`** if the decision is still *open* (has a
resolution trigger — it isn't shipped yet).

## Template

```markdown
### [Date] — [Short title]
**Decision:** _what was decided_
**Context:** _why — constraint, user feedback, design call_
**Scope:** _which screen / component / string / asset — not product-wide_
**Commit:** _optional — git SHA or PR; may be added retroactively_
```

---

## Entries

> _Illustrative only — the entry below is a worked example of the format, not a
> real jig decision (jig is a CLI/plugin with no UI). Adopter projects replace it
> with their first real entry; the scaffold template ships with no entries._

### 2026-01-15 — Onboarding CTA copy: "Get started" over "Sign up"

**Decision:** The first-run onboarding screen's primary button reads
**"Get started"**, not "Sign up" or "Create account".

**Context:** User testing showed "Sign up" read as a commitment gate and
suppressed first-tap; "Get started" tested as lower-friction for a flow that
doesn't actually require an account until step 3. Not worth an ADR — it changes
no contract or boundary — but a future redesign should know the wording is
deliberate, not a placeholder.

**Scope:** Onboarding screen primary CTA only. Does not set a product-wide
button-copy convention.

**Commit:** _(example — no SHA)_
