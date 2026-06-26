---
adr: 0030
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-26T13:48:09Z
prompt_source: review.py frame-critique docs/decisions/adr-0030-python-39-floor.md
---

VERDICT: pass

Load-bearing assumption — the 3.9.6 CI job actually exercises shipped adopter-facing import paths — verified grounded: ci.yml runs the matrix on 3.9.6 via run_tests.py (discovers test_*.py importing the shipped helpers); ruff.toml sets target-version=py39; install_contract.RELEASE_INCLUDE_ROOTS excludes scripts/. Frame survives. Sharp residual-risk finding (CI is import/test coverage, not full behavior coverage — an untested + ruff-invisible 3.10+ path could ship green) incorporated into Assumptions + Kill criteria before acceptance.
