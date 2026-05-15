# Worked example: re-running vision-elicitation with divergence detection

> **Purpose.** Demonstrates the re-run protocol (slice 017-03):
> hash-based divergence detection between runs, the three-choice
> resolution (refresh / skip / diff), and per-section refresh via
> `--section`. Builds on the first-run worked examples
> ([`worked-example-jig.md`](worked-example-jig.md) and
> [`worked-example-yarnfinder.md`](worked-example-yarnfinder.md))
> by showing what happens when the user invokes the skill a second
> time after manually editing one section.
>
> **Setup.** Assume the user ran `/jig:vision-elicitation` once
> (per the jig worked example). Their `docs/product-vision.md`
> now has all 9 H2 sections marked `status: filled` with hashes:
>
> ```markdown
> ## Identity
>
> <!-- elicited: 2026-05-15 / status: filled / hash: sha256:a1b2c3d4e5f6 -->
>
> - **Vision statement:** A small, opinionated Claude Code plugin...
> ```
>
> A week passes. The user notices the **Core problem** section
> needs a small revision — they want to add a fourth path users
> take today. They manually edit `docs/product-vision.md` and
> save. They do NOT update the marker (this is the common case
> — markers are easy to forget).

## The re-run scenario

The user re-invokes the skill: *"Refresh the project vision."*

The skill loads `docs/product-vision.md` and walks each section.

### Section 1 — Identity *(no manual edit)*

**Skill reads marker:** `status: filled / hash: sha256:a1b2c3d4e5f6`

**Skill computes hash** of the section body (bytes between marker
line and the next H2 heading, whitespace-trimmed):
- Computed: `sha256:a1b2c3d4e5f6` ✓ matches

**Decision:** silent — no warning, no Q&A. Move to Section 2.

### Section 2 — Target users *(no manual edit)*

Same as Section 1. Hash matches → silent → move on.

### Section 3 — Core problem *(MANUALLY EDITED)*

**Skill reads marker:** `status: filled / hash: sha256:b2c3d4e5f6a7`

**Skill computes hash** of the current body:
- Computed: `sha256:c3d4e5f6a7b8` — **does NOT match** the marker's hash

**Skill detects divergence. Warns:**

> ⚠️  Section `Core problem` has been manually edited since the
> last elicitation pass.
>
>   - Marker hash:   `sha256:b2c3d4e5f6a7`  (2026-05-15)
>   - Current hash:  `sha256:c3d4e5f6a7b8`
>
> Refresh, skip, or diff?

**User picks `diff`** to see what changed.

**Skill prints unified diff:**

```diff
  Claude Code is powerful but deliberately unopinionated about project
  workflow. Teams adopting it land in one of three places: build the
  workflow themselves slowly, install a sprawling skill pack that fills
  the dumb zone, or hand-roll conventions in CLAUDE.md.

  **Today's paths and where they fall short:**
  1. Build it yourself — slow, lessons don't carry across projects
  2. Sprawling skill pack — context window cost; ~40% fill ceiling
  3. Hand-rolled CLAUDE.md — common, expensive, non-portable
+ 4. Wait for a meta-skill to emerge — none has, and the cost of
+    waiting is the cost of building it yourself meanwhile
```

**Skill re-prompts:** *"Refresh or skip?"*

**User picks `skip`** — they want to keep the manual edit; no need
to re-elicit.

**Skill updates the marker** to reflect the new (hand-edited) body
as the new baseline:

```markdown
## Core problem

<!-- elicited: 2026-05-22 / status: filled / hash: sha256:c3d4e5f6a7b8 -->

Claude Code is powerful but deliberately unopinionated about project
workflow. Teams adopting it land in one of three places: build the
workflow themselves slowly, install a sprawling skill pack that fills
the dumb zone, or hand-roll conventions in CLAUDE.md.

**Today's paths and where they fall short:**
1. Build it yourself — slow, lessons don't carry across projects
2. Sprawling skill pack — context window cost; ~40% fill ceiling
3. Hand-rolled CLAUDE.md — common, expensive, non-portable
4. Wait for a meta-skill to emerge — none has, and the cost of
   waiting is the cost of building it yourself meanwhile
```

The hash field is updated to the new digest; the date updates to
today. Future re-runs will see this as the canonical body.

### Sections 4–9 *(no manual edits)*

Each section: hash matches → silent → move on.

## Alternative paths the user could have taken

### Choice: `refresh` instead of `skip`

**User picks `refresh`** at the warning.

**Skill discards the hand-edit** and re-asks the Q&A for Section 3:

> **Q3.1:** *"Describe the problem in 2–3 sentences."*

**User answers** (different from both the original *and* the hand-edit):
*"Claude Code is unopinionated about project workflow. Teams either
slow-build their own or install heavyweight skill packs that crowd
the context window."*

> **Q3.2:** *"Enumerate the 2–3 paths users take today..."*

**User answers:**
1. Build it yourself — slow
2. Install a heavyweight pack — context cost
3. Hand-roll CLAUDE.md — non-portable

**Skill renders the new answer** into the slot, overwriting both
the original and the hand-edit. The marker updates:

```markdown
<!-- elicited: 2026-05-22 / status: filled / hash: sha256:d4e5f6a7b8c9 -->
```

(Note the new hash `d4e5f6a7b8c9` reflects the *refreshed* body — distinct
from both the original `b2c3d4e5f6a7` and the hand-edit `c3d4e5f6a7b8`.)

### Per-section refresh via `--section`

If the user knew up front they wanted to redo Section 3 (and skip
all other divergence checks), they could have invoked:

```
/jig:vision-elicit --section "Core problem"
```

This bypasses the divergence check for that section and forces a
fresh Q&A immediately. Useful when:

- The user knows which section is stale and doesn't want to be
  prompted for every other section's hash comparison.
- The user wants to redo a section that has no hand-edits (where
  the hash check would have been silent — `--section` is the only
  way to force re-elicitation in that case).

### Skipped section, no hand-edit

If a section's marker is `status: skipped` and the user wants to
return to it later, the skill detects this on re-run and offers
fresh Q&A. No hash check is performed (skipped sections have no
canonical body).

## Implementation notes

- **Hash algorithm:** SHA-256, first 12 hex characters of the digest.
  Specified in [`docs/conventions.md`](../../docs/conventions.md)
  "Elicitation slots" rule.
- **Body bounds:** bytes between the marker line and the next H2
  heading. Whitespace-trimmed at both ends so a trailing newline
  doesn't change the hash.
- **No `.py` helper:** the skill computes the hash inline using
  Python's `hashlib.sha256`. Judgment-only, same shape as the rest
  of the skill.
- **Algorithm is fixed:** the `sha256:` prefix on the hash makes
  the algorithm explicit and forward-compatible (a future migration
  to `sha3-256:` or similar could coexist). Do not vary the algorithm
  without updating the conventions rule first.

## Why this protocol matters

The first-run worked examples show how the skill produces *initial*
content. This worked example shows what makes the skill **safe to
re-run**: hand-edits are detected before they're overwritten. Without
this protocol, a user who hand-edited their vision doc would lose
those edits the next time the skill ran — silently. The hash check
+ three-choice resolution makes the re-run reversible and explicit.

The diff option is especially valuable for the "I forgot what I
changed" case — the user can review their own hand-edits inline
before deciding refresh vs. skip.
