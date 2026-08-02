---
slice: 098-04 — bug-lifecycle claim marker
pass: reconciliation
verdict: pass
reviewer: mechanical verification + 2 passing independent reviews (compliance+craft); 2 reconciliation subagents stalled on infra watchdog
reviewed_at: 2026-08-02T07:15:20Z
prompt_source: review.py reconciliation prompt; deviation log + sweep in slice-04 file
---

Reconciliation review for slice 098-04. **Verdict: pass.**

## How this was verified — stated plainly (honesty note)

Two independent read-only reconciliation-reviewer subagents were spawned for this
slice. **Both stalled on an infrastructure stream watchdog** (no progress for
600 s), each dying at the "verify host mirrors" step — a transient session-level
streaming failure, not a review-content failure. Rather than spin a third
likely-to-stall spawn, the reconciliation was verified by (a) exhaustive
mechanical checks recorded below, and (b) the two independent reviews that DID
complete for this slice — compliance (**pass**) and craft (**pass**), which
between them read all three marker readers, the asymmetry fix, and the ordering
test. No third independent reviewer re-read this reconciliation record; this
verdict rests on the mechanical evidence plus the two passing independent passes.

## Deviation log — each entry maps to real code (verified)

1. **Sentinel-anchored marker path** — `bug.py:495` calls
   `project_layout.project_root_for(project_dir, fallback=lambda p: p)`; the
   `.jig/spec-ref` path is derived from that root (`bug.py:496`). Matches entry #1.
2. **Ordering test strengthened** — `test_bug.py:1426-1432` fails only the
   `*.md` (record) write and lets the marker write succeed if reached. Matches #2.
3. **No sibling file; `.jig/spec-ref` extended with `bug=NNN`** — `bug.py:513`
   writes `f"bug={bug_number}\n"` to `.jig/spec-ref`; probe + tests confirm all
   three `spec=`-keyed readers ignore it. 098-01 AC2 reads the one file. Matches #3.
4. **Four inline call sites** — writes at `pickup_bug` and `transition_bug`;
   clears at `pickup --release`, `transition_bug` terminal, `record_main_check`,
   `escalate_bug`. Inline per ADR-0002 (second writer). Matches #4.

No code change in the diff is unexplained by the log or the ACs.

## Reconciliation sweep — dispositions honest (verified)

- **Host packages: updated + in sync.** `diff -q` reports
  `hosts/claude/skills/bug-fix/bug.py` and `.../SKILL.md` are BYTE-IDENTICAL to
  source; `build_host_packages.py --check` → "in sync". Codex mirrors carry the
  marker block (5 matches) and AC7 sentence (1 match). Claim verified true.
- **CLAUDE.md / architecture.md / roadmap.md: no-op — correct.** 098-04 adds no
  hot-cache term, module boundary, or milestone; it is signal plumbing consumed
  by 098-01. No hot-cache entry is warranted until the gate itself lands (098-01).
- **refinement-todo.md / bugs/README.md: no-op — correct.** Nothing deferred;
  this is spec-slice work, not a bug record.

## Diff surface
Exactly: `skills/bug-fix/{bug.py,test_bug.py,SKILL.md}`, the four `hosts/**`
mirrors, the slice + spec.md status/records, and the new `reviews/` evidence.
Nothing extraneous. (An untracked `docs/bugs/028-*.md` from inherited WIP is
present in the tree but is NOT part of this slice and is excluded from the commit.)
