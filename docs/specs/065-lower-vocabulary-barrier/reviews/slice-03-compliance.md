---
slice: 065-03 — `/jig:explain` skill (term + artifact modes)
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-07T18:06:30Z
prompt_source: review.py implementation
---

VERDICT: pass

All six acceptance criteria for slice 065-03 are met. `skills/explain/SKILL.md`
has active frontmatter (`name: explain`, `user-invocable: true`, no disable),
declares both modes + both invocation styles, documents term mode (merged-lexicon
def + example + see-also; absent term flagged, never invented), artifact mode with
the exact fixed six-block shape + auto-pull-linked-refs, the ephemeral contract
(writes nothing, no `--save`), no `.py` helper, and the deferral clause (defers to
richer plain-language/onboarding/walkthrough skill, not the generic built-in). The
skill is registered in all three real surfaces (`scaffold._TIER_SKILLS`,
`install_contract.EXPECTED_SKILLS`, `scaffold_contract._TIER_SKILLS`) + the CLAUDE.md
skills table; surface tests pin each AC against load-bearing content. The lexicon
loader API referenced (`lexicon.load('.')`, `plain`/`example`/`see_also`) matches the
actual 065-01 loader.

Non-blocking: AC1's literal "listed in the plugin manifest (passing
validate_manifests.py)" is imprecise about jig's discovery mechanism (skills are
directory-auto-discovered + registered via the install/scaffold contract surfaces;
validate_manifests.py only checks the three JSON manifests). The implementation
satisfies AC1's *intent* via the real registration surfaces. Worth a one-line
deviation note. (Reviewer: jig:reviewer, read-only.)
