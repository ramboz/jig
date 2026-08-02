---
bug: 025
pass: bug-review
verdict: pass
reviewer: subagent (general-purpose)
reviewed_at: 2026-08-02T02:42:33Z
prompt_source: review.py bug-review
---

The fix resolves #167 at its documented root cause by making the committed-package builders consume the install_contract runtime-scripts allowlist that was previously honoured only by the dead iter_release_files enumerator. Regression tests confirmed red pre-fix and green post-fix with non-vacuous drift guards; the Claude(4)/Codex(1) split is correct given spec_lint's host-neutrality vs the verify_install trio's .claude/ hardcoding; committed hosts/ trees match a fresh build byte-for-byte. Change stays within its structural_fix class with no unrelated edits. Reviewer independently reproduced red-before/green-after by stripping the include loops.
