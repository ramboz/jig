---
dependencies: []
last_verified: 2026-05-29
---

# ADR-0010: Amendment scope — records vs. live operational prose

## Status

Accepted (2026-05-29)

Supersedes ADR-0008

## Context

The `## Amendments` drift mechanism fits records but not live operational prose; this ADR narrows its scope accordingly.

[ADR-0008](./adr-0008-closed-spec-drift-policy.md) established the
closed-spec drift policy: when a `DONE` / `SUPERSEDED` spec drifts
from reality, the fix is a `## Amendments` section appended to the
artifact (Option C — amendments for prose drift, a new/superseding
ADR for decision-content changes). That ADR extended the same
amendment mechanism beyond specs to **load-bearing skill / router
prose** — "SKILL.md descriptions, `docs/workflow.md` routing prose,
README claims that drive decisions" (ADR-0008 § Scope) — on the
reasoning that such prose is "the same kind of artifact for policy
purposes."

In practice that extension backfired, and the failure is concrete.
Slice 036-02 swept the `pr-review` SKILL.md arch-review drift by
appending a `## Amendments` block to the **body** of
[`skills/pr-review/SKILL.md`](../../skills/pr-review/SKILL.md)
while leaving the stale claim ("jig does not ship an arch-review
skill today") untouched in the frontmatter `description:` field. But
the router reads the **frontmatter description**, not the body. The
amendment therefore preserved the exact defect ADR-0008 cited as its
own motivation — "the false claim biases the router toward pr-review"
— because the false claim stayed fully operational in the string the
router actually reads. The same shape applies to the amendments
appended to `skills/memory-sync/SKILL.md` and `docs/workflow.md`.

The root cause is that ADR-0008 conflated two artifact kinds that
drift the same way but are *read* differently:

- **Records** — closed specs and slices. Read as a snapshot of a
  contract as it stood at a point in time. Their value is partly
  historical; rewriting them destroys the audit artifact. Preserving
  the original prose and annotating it with a dated amendment is the
  right discipline, and the audit trail belongs *in the document*
  because that is how the document is read.
- **Live operational prose** — SKILL.md descriptions (read by the
  skill router at dispatch time), `docs/workflow.md` routing prose,
  README claims (read by the next agent / contributor as current
  truth). Nobody reads these as a historical snapshot. Stale text is
  not an archival artifact — it is a live defect. The correct fix is
  to edit it in place so the corrected text is the text being read,
  and the audit trail belongs in **git history** (`git blame` /
  `git log -p`), which is the right home for configuration history.

ADR-0008's Option C is correct for records and wrong for live prose.
This ADR narrows the amendment mechanism to records and routes live
operational prose to inline edits. It does not disturb ADR-0008's
core machinery (amendments for closed specs/slices, default-to-ADR
for decision content); it removes one over-reach from the scope.

## Decision Options Considered

### Option A: Keep ADR-0008 as written; fix amendments more carefully

Retain the `## Amendments`-on-live-prose rule, but add guidance that
an amendment touching a router-read field must *also* edit that field.

- **Pros:** No scope change; preserves a single uniform drift rule.
- **Cons:** Once you accept that the field must be edited in place for
  the fix to work, the appended amendment block is pure redundancy —
  it duplicates, in the body, a correction that already lives inline.
  Keeps two audit trails (in-document + git) for an artifact that only
  needs one. Treats the symptom, not the conflation.

### Option B: Narrow amendments to records; live prose is corrected inline (git history is the audit trail)

Amendments (`## Amendments`) apply to closed specs and slices only.
Load-bearing skill / router / workflow / README prose is corrected
**inline**; its audit trail is git history. Decision-content changes
to any artifact still warrant a new or superseding ADR, unchanged
from ADR-0008.

- **Pros:** Matches the fix to how each artifact is read. For
  router-read fields it is the *only* model where the fix actually
  takes effect. One audit trail per artifact kind, each in its
  natural home. Removes the redundancy Option A would entrench.
- **Cons:** Two rules to remember instead of one ("is this a record or
  live prose?"). The boundary is usually obvious (status frontmatter
  on a spec vs. a SKILL.md description) but a new artifact kind could
  sit on the line.

### Option C: Drop amendments entirely; everything is edited inline with git history as the trail

Abolish the `## Amendments` mechanism; treat specs like live prose.

- **Pros:** One rule, no boundary call.
- **Cons:** Throws out the part of ADR-0008 that works. A closed spec
  is a contract read as a snapshot; silently rewriting its body
  destroys the "what did we commit to, and when" record that the
  in-document amendment trail preserves. Over-corrects.

## Recommended Decision

**Option B — amendments are scoped to records (closed specs and
slices); load-bearing skill / router / workflow / README prose is
corrected inline, with git history as the audit trail. Decision-
content changes continue to warrant a new or superseding ADR.**

The effective rule:

| Artifact | Drift fix | Audit trail |
|---|---|---|
| Closed spec / slice (`DONE` / `SUPERSEDED`) | `## Amendments` (original prose preserved) | in-document |
| ADR | supersede (per ADR-0006) | ADR index |
| SKILL.md / `workflow.md` / README prose | **edit inline** | git history |

Two reasons this is the right cut:

1. **For router-read fields, inline edit is the only model that
   works.** ADR-0008's own motivating defect — a false SKILL
   description biasing the router — is *not fixed* by an amendment
   block in the body, because the router never reads the body. The
   evidence is live in the repo today (`pr-review/SKILL.md`).
2. **Each artifact kind gets exactly one audit trail, in its natural
   home.** Records carry their history in-document because they are
   read as snapshots; live config carries its history in git because
   that is where config history belongs and where it is already
   captured for free. ADR-0008 inadvertently gave live prose two
   trails (an in-body amendment *and* git) while leaving the
   operational defect unfixed.

The boundary call — "is this a record or live operational prose?" —
is decided by how the artifact is read, not by its file type: a spec
is read as a snapshot of a past commitment; a SKILL.md description is
read by the router as current truth. When genuinely in doubt, treat
it as live prose and edit inline — the git trail is always present,
whereas an amendment block on something that is not read as a record
is the failure mode this ADR corrects.

## Consequences

**Becomes easier:**

- Fixing drifted SKILL.md descriptions, workflow.md routing prose,
  and README claims: edit the live text, done. The fix lands where it
  is read, and `git blame` carries the history.
- Reading live skill/router prose: one current statement, no
  body-level "original said X, now Y" footnote to reconcile against
  the frontmatter.
- The `pr-review` SKILL.md misrouting bug gets a clean fix path:
  correct the frontmatter `description:` inline and drop the now-
  redundant `## Amendments` block.

**Becomes harder:**

- Two rules to internalize instead of ADR-0008's one. Mitigation: the
  table above, and the default-to-inline-when-in-doubt tie-breaker.
- The retroactive cleanup of three already-landed amendment blocks
  (`workflow.md`, `memory-sync/SKILL.md`, `pr-review/SKILL.md`) is
  follow-up work this ADR authorizes but does not itself perform.

**Implementation status:**

- This ADR supersedes ADR-0008 and narrows its scope. ADR-0008's
  closed-spec/slice machinery and its default-to-ADR carve-out for
  decision content are carried forward unchanged.
- Cleanup of the three live-prose amendment blocks (fold each
  correction inline, fix the `pr-review` frontmatter, remove the
  `## Amendments` sections) is a follow-up sweep, mirroring how
  036-02 was the sweep that followed ADR-0008.
- `skills/spec-workflow/SKILL.md`'s reconciliation-checklist pointer
  and the CLAUDE.md Hot Cache entry both reference ADR-0008's drift
  policy; they should be updated to point at this ADR and to state
  the records-vs-live-prose split.
- No new tooling falls out of this ADR. If inline edits to live prose
  start silently dropping context that mattered, a future slice can
  revisit; the rule first has to fail before we tool it.

## Scope

**In scope:**

- The *mechanism* for fixing drift in load-bearing skill / router /
  workflow / README prose: changed from `## Amendments` to inline
  edit.
- Reaffirms amendments for closed specs and slices (`DONE` /
  `SUPERSEDED`) unchanged.

**Out of scope:**

- ADRs — still governed by ADR-0006 / Nygard immutability; superseded,
  never amended. Unchanged.
- Specs in any non-closed state (`DRAFT` … `RECONCILED`, `DEFERRED`) —
  in-body edits remain normal; unchanged from ADR-0008.
- Decision-content changes to any artifact — still warrant a new or
  superseding ADR (or superseding spec); unchanged from ADR-0008.

## Relationship to other decisions

- **ADR-0008 (closed-spec drift policy).** Superseded by this ADR.
  Its records machinery (amendments for closed specs/slices) and its
  default-to-ADR carve-out are carried forward; only the extension of
  amendments to live operational prose is reversed.
- **ADR-0006 (adr.py accept-then-index ordering).** Unchanged.
  Provides the immutability baseline that keeps ADRs out of the
  amendment mechanism in the first place.
- **Spec 042 (spec-gate model).** Same light coupling ADR-0008
  declared; if 042 lands a stricter edit-permission gate, this ADR is
  the more general drift rule and the two should not contradict.

## Open questions

None. The records-vs-live-prose split is decided; the boundary
tie-breaker (default to inline when in doubt) is stated; the cleanup
sweep is named as follow-up; the immutability baseline for ADRs is
untouched.
