---
bug: 013
pass: craft
verdict: pass
reviewer: general-purpose subagent (fresh context per round, read-only) — 3 rounds
reviewed_at: 2026-07-30T02:32:10Z
prompt_source: pr-review skill craft pass
---

Craft pass (`pr-review` methodology, richer installed skill per ADR-0039's
discovery rule), **three rounds**, fresh read-only reviewer each time.
Rounds 1 and 2 returned `pass` with nits; round 2 also raised two blockers.
Round 3 (commit `b5a4685`) returned **pass**.

## Round 1 — pass, six nits

Verified the gate/rewrite separation is well-shaped and that comments and
docstrings cite the ADR's rulings accurately. Two mutation probes survived:
the `last_verified` date-substitution branch, and the dedicated `Superseded`
refusal branch (its test asserted a word the generic catch-all also emits).
Four more nits: a comment claiming callers read regex groups that nothing
reads, a note misdescribing a canonical-but-wrong-state line, a docstring
overclaiming a mirror of `workflow.py::_lookup_adr_accepted`, and SKILL.md
stating the supersession as fact while the ADR was still Proposed.

## Round 2 — two blockers, both about the same wrong premise

Independently reached the same conclusion as frame-critique round 2:
`last_verified` is a *freshness* field, not an acceptance date
(`reaffirm` refreshes it — ADR-0024 / `skills/reframe/SKILL.md`; manual
freshness bumps are documented in `spec-workflow/SKILL.md`). Two paths were
asserting a provenance the field does not have:

- `_no_anchor_message` told the operator "the line to write is almost
  certainly `Accepted ({last_verified})`" — a confident wrong date, written
  into a record ADRs treat as immutable.
- `_extract_status_and_date` published that date into
  `docs/decisions/README.md` with **no human in the loop**.

Both fixed by removing the premise rather than hedging it: the diverged case
publishes no date, and the refusal reads no frontmatter at all.

Round 2 also flagged the vestigial `adr_text` default parameter (removed with
the premise), and two unexercised branches: the new-ADR anchor refusal
(stubbing it left the suite green) and the blank-but-present `status:`
fallthrough. Both now have mutation-verified tests.

## Round 3 — pass

Verification: suite `Ran 149 tests — OK` on Python 3.9.6; no 3.10+ syntax;
host mirrors byte-identical (codex `SKILL.md` differs only by the documented
host-token substitutions); the printed `git log` command verified working from
the repo root **and** from a subdirectory, returning the accept commit; the
ADR's load-bearing claims about `reaffirm`, the staleness reader, the renderer
omitting the date, and the bug record's "18 cases" all spot-verified accurate.

Mutation probes: 6 of 7 killed — diverged-date→prose-date,
diverged-date→`last_verified` (the round-2 bug), dropping the `git log` line,
dropping the "freshness field" wording, blank-`status:`-read-as-a-state, and
removing the new-ADR anchor refusal all fail the suite.

**Three nits, all closed rather than logged:**

1. *(the surviving mutation)* Reverting the pathspec to `{adr_path.name}` —
   the exact defect frame-critique round 3 caught — left the suite green,
   because the test asserted only `"git log"`. Sharp because
   `docs/memory/learnings.md` records "run the remediation command you print"
   as a learning while the fix itself was untested. Now asserts the full
   resolved pathspec and that it carries a directory separator; the mutation
   dies.
2. The parenthetical advising a prose search "for a legacy ADR carrying no
   frontmatter" was **unreachable**: a prose-only ADR classifies Accepted
   through `_STATUS_ACCEPTED_RE`, the same pattern `_insert_after_accepted`
   searches, so if it classified Accepted the anchor exists by construction.
   A message describing a state its code cannot reach is precisely the
   artifact class that filed bug 013 — removed, and the docstring now states
   the reachability condition.
3. `-S` matches every commit that changed the string's occurrence count, so
   "the accept commit" was ambiguous and unordered. Now `--reverse`, with the
   message naming the first line as the one wanted. Pinned by a test.

No gratuitous churn in any round; everything touched is inside the fix's own
surface.
