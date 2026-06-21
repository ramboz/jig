# Spec 077 Implementation Plan

## 077-02 — jig self typed baseline

- Add a repo-local pyright baseline config that gates `skills/` helper code and
  `scripts/run_tests.py`, while excluding `test_*.py` dynamic harnesses.
- Fix real pyright findings in helper/runtime files rather than suppressing
  optional-return and optional-argument bugs.
- Refactor `scripts/run_tests.py` into an importable runner and append a
  pyright gate after the unittest suite.
- Add focused tests for resolver order and for a pyright diagnostic failing
  the gate.
- Verify the full documented local gate and a reversible introduced type
  error failure.
