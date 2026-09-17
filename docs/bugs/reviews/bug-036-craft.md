---
bug: 036
pass: craft
verdict: pass
reviewer: jig:reviewer subagent
reviewed_at: 2026-09-17T17:13:27Z
prompt_source: pr-review skill craft pass
---

Verdict: pass (round 3 of 3). Source: pr-review skill craft pass.

Scope: code quality, clarity, naming, comment quality, test quality, error
handling, Python 3.9 compatibility, dead code.

Round 1 raised two should-fixes and a nit: `_install_roots` assumed a parsed
manifest was a mapping (a valid JSON array/scalar would raise `AttributeError`
rather than being skipped); the documented fresh-shell bootstrap hardcoded
`~/.copilot` while the locator supported `COPILOT_HOME`; and the adapter
root-location test derived its expectation from the same `parents[2]` formula
as the implementation, so it could pass while the package topology was wrong.

Round 2 confirmed those were resolved and raised two more: the
`_copy_templates` docstring contradicted the fixed behaviour, and the new
template test asserted only the absence of two known-bad spellings, so a
rewrite to an unrelated path would still pass.

Round 3: pass. The template builder preserves canonical source byte-for-byte
with accurate documentation, and the regression test positively verifies source
identity, non-vacuous coverage, and retained `${CLAUDE_PLUGIN_ROOT}`
references. No remaining craft, test-quality, error-handling, or Python 3.9
compatibility findings.
