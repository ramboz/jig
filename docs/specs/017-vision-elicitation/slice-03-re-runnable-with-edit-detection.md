## Slice 017-03 — re-runnable-with-edit-detection

**STATUS: DONE**

**Scope:** re-run mechanics. The skill must detect manual edits
between runs and warn before overwriting them. Adds the `hash` field
to the marker convention; teaches the skill to read existing markers,
recompute body hashes, and surface divergence to the user.

**SPIDR axis:** Rules — splits the work by adding behavior over the
same surface from 017-02.

**Deliverables:**
- SKILL.md body extended with a "Re-run protocol" section: read
  existing marker → compute current body hash → compare against
  marker's `hash` field → if divergent, surface
  `manual edits detected in section <N> — refresh anyway? [y/N/diff]`.
- Marker convention extended in `docs/conventions.md`: `hash` field
  now required for `status: filled` sections; format is
  `sha256:<first-12-hex>` of the section body (trimmed; bytes
  between the marker line and the next H2 heading).
- Per-section refresh supported: `/jig:vision-elicit --section
  "Core problem"` (or its skill-form equivalent — exact CLI shape
  is implementer's call).
- New worked-example transcript:
  `skills/vision-elicitation/worked-example-rerun.md` showing a
  re-run against jig's own vision doc with one section manually
  edited; skill warns; user confirms; section refreshed; hash
  updated.

**Acceptance criteria:**
1. SKILL.md body contains a "Re-run protocol" section documenting
   the four-step flow (read marker → compute hash → compare →
   surface decision).
2. `docs/conventions.md` marker convention now specifies the `hash`
   field format for `filled` sections.
3. Re-run on a vision doc with no manual edits is silent: no
   warning, only the actual re-elicited-section diffs are surfaced.
4. Re-run on a vision doc with one manually-edited section warns
   before that section is touched. The warning quotes the section
   heading and offers three choices: refresh / skip / diff.
5. Per-section refresh is documented in SKILL.md.
6. Worked-example transcript demonstrates a divergence detection
   end-to-end.
7. Surface tests pin the re-run flow markers in SKILL.md and the
   hash format string in conventions.md.

**Definition of Done:**
- [x] All ACs green.
- [x] New surface tests green; no regression. (695 → 709 total green; +14 from 3 new test classes covering 017-03.)
- [x] Implementation review passed. _(auto-ticks on IN_PROGRESS → REVIEWED)_
- [x] Deviation log written.
- [x] Reconciliation review passed. _(auto-ticks on REVIEWED → RECONCILED)_
- [x] Spec status board updated.

### Close-out (post-DONE)
- [x] CLAUDE.md hot-cache row for 017-03 updated.

### Deviation log (017-03)

**1. Implementer was the main agent; review used general-purpose subagent.**
Same pattern as 017-01 §1+§2 and 017-02 §4+§5. Documented degraded
mode. Implementation review returned `VERDICT: needs-changes` with 5
specific issues + 4 reconciliation notes; all addressed below.

**2. Recurring staleness pattern (4th instance) led to a new learnings.md entry.**
Implementation reviewer caught three places in SKILL.md still using
pre-017-03 future-tense phrasing despite 017-03 *being* the landing:
"once that ships" (line 14 description), "Today (017-02) the skill
is first-run only" (line 109 step-2 detail), "Re-runs are 017-03's
job" (line 294 Gotchas bullet). Same shape as 017-01 §5(a), 017-01
§8, and 017-02 §2. **Fixed inline**: all three rewritten to describe
the now-shipped re-run protocol as current behavior. **New
regression test** `test_no_017_03_future_tense_phrasing` pins
SKILL.md against six pre-017-03 phrases ("once that ships", "Once
slice 017-03 ships", "Today (017-02)…", etc.); positive bound
`test_describes_rerun_as_shipped` ensures the Re-run protocol is
documented as current behavior. **New learnings.md entry**
("Mid-implementation reshape / reword leaves stale future-tense
prose in adjacent stanzas") documents the pattern across all 4
instances and proposes a pre-review grep checklist + test-driven
locking pattern.

**3. Skipped-sections-on-re-run semantics: SKILL.md vs worked example collision.**
Reviewer flagged a real narrative collision: SKILL.md's Re-run
protocol step 1 originally said "`status: skipped` → pass over
(unless `--section <name>` explicitly names this section)", but
worked-example-rerun.md said skipped sections always get fresh Q&A
on re-run with no `--section` flag. **Resolved in favor of the
worked example's rule**: a re-run is the user's explicit
invocation, and a skipped section is the natural moment to revisit.
SKILL.md "How the elicitation works" step 2 rewritten to describe
the three branches (`unfilled` → elicit, `filled` → hash check,
`skipped` → fresh Q&A); SKILL.md Re-run protocol step 1 likewise.
Both files now align on "skipped sections get fresh Q&A on re-run,
no hash check (they have no canonical body)."

**4. Body-bounds edge cases clarified in conventions.md.**
Reviewer flagged that the "Elicitation slots" rule's body-bounds
spec ("bytes between marker line and next H2 heading; whitespace-
trimmed") was ambiguous on two edge cases: (a) the last H2 section
(no trailing H2), (b) H2-looking content inside fenced code blocks.
**Fixed in conventions.md** (via documented `JIG_CONVENTIONS_APPROVED=1`
escape, same as 017-01 §4): rule now clarifies that the next-H2
match excludes fenced code blocks and that the last section bounds
to EOF.

**5. Refresh walk-through in worked example tightened.**
Reviewer noted the `refresh` choice was described in prose in an
"Alternative paths" subsection, while the `diff`+`skip` flow had a
full inline trace. **Fixed inline**: refresh walk-through is now
symmetric with the other choices (full Q&A trace, marker update,
hash distinct from both original and hand-edit). Asymmetry is gone.

**6. Conventions.md edit used the documented `JIG_CONVENTIONS_APPROVED=1` escape.**
Same shape as 017-01 §4 and an earlier conventions edit in this
slice (the hash-field-spec rewrite). User-explicit approval for
slice 017-03 implementation cascaded to the conventions edits (AC
#2 + the body-bounds clarification). Three conventions edits total
in this slice; all under the explicit-approval umbrella.

**7. Reconciliation reviewer caught two more staleness instances — exactly the pattern this slice's learnings.md entry documents.**
The first reconciliation review returned `VERDICT: needs-changes`
flagging: (a) SKILL.md:222 Re-run protocol step 1 still said
`status: skipped → pass over (unless --section <name>)`,
contradicting both SKILL.md step 2 (line 114, "skipped → offer fresh
Q&A") and worked-example-rerun.md — §3's closure claim was
incomplete; only step 2 was rewritten. (b) conventions.md:81 still
said "017-03's re-run mechanics **will** detect divergence" —
future-tense for a now-shipped feature. **Both fixed inline**:
SKILL.md Re-run protocol step 1 rewritten to match step 2's "offer
fresh Q&A" rule; conventions.md "will detect" → "detect". **Test
scope extended**: the `test_no_017_03_future_tense_phrasing`
regression now sweeps BOTH `SKILL.md` AND `docs/conventions.md`,
not just SKILL.md as originally written. This is the
meta-perfect "the slice that documents the staleness pattern just
hit the pattern" moment — recorded prominently because it validates
the pattern is real-enough-to-bite-you-immediately. 6th and 7th
instances. Reviewer notes: the regression test scope expansion is
the right structural fix; widening the sweep to all
slice-deliverable .md files (not just SKILL + conventions) would be
a future refinement-todo entry if a third file is ever caught.

