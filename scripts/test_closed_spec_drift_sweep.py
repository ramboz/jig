"""
Tests for the closed-spec drift policy as amended by ADR-0010.

ADR-0008 (slice 036-02) originally swept four drifted artifacts by
appending a `## Amendments` section to each. ADR-0010 supersedes it and
narrows the amendment mechanism:

- **Records** (closed `DONE` / `SUPERSEDED` specs + slices) keep the
  `## Amendments` section — the original prose is preserved and a dated
  entry overrides it.
- **Live operational prose** (SKILL.md descriptions, `docs/workflow.md`,
  README) is corrected **inline**; git history is the audit trail. These
  artifacts must NOT carry a `## Amendments` section.

So this suite asserts:

- spec 016 (a closed spec — a *record*) still carries its `## Amendments`
  section with the corrected hook count.
- pr-review / memory-sync SKILL.md and workflow.md (*live prose*) carry
  NO `## Amendments` section, the stale claim is gone, and the corrected
  claim is present inline.
- README.md carries no `## Amendments` section (unchanged).
- `skills/spec-workflow/SKILL.md`'s reconciliation-checklist gate names
  "closed-spec drift", links **ADR-0010**, and sits before `**Commit**`.

Run:
    python3 scripts/test_closed_spec_drift_sweep.py
    # or from repo root:
    python3 -m unittest scripts.test_closed_spec_drift_sweep
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SPEC_016 = REPO_ROOT / "docs" / "specs" / "016-scaffold-mode" / "spec.md"
PR_REVIEW = REPO_ROOT / "skills" / "pr-review" / "SKILL.md"
MEMORY_SYNC = REPO_ROOT / "skills" / "memory-sync" / "SKILL.md"
WORKFLOW_MD = REPO_ROOT / "docs" / "workflow.md"
README = REPO_ROOT / "README.md"
SPEC_WORKFLOW_SKILL = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"

DATE_HEADING_RE = re.compile(r"^### \d{4}-\d{2}-\d{2} — ", re.MULTILINE)
AMENDMENTS_HEADING_RE = re.compile(r"^## Amendments\s*$", re.MULTILINE)

# Live-prose artifacts that must be corrected inline (no amendments) per ADR-0010.
LIVE_PROSE = (PR_REVIEW, MEMORY_SYNC, WORKFLOW_MD, README)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _amendments_body(text: str) -> str:
    """Return the text after the `## Amendments` heading, or '' if missing."""
    m = AMENDMENTS_HEADING_RE.search(text)
    if not m:
        return ""
    return text[m.end():]


class RecordSpec016KeepsAmendment(unittest.TestCase):
    """ADR-0010: spec 016 is a record (closed spec) — it KEEPS its amendment."""

    def setUp(self) -> None:
        self.text = _read(SPEC_016)
        self.body = _amendments_body(self.text)

    def test_has_amendments_section(self) -> None:
        self.assertRegex(self.text, AMENDMENTS_HEADING_RE,
                         "spec 016 (a record) must keep its '## Amendments' section")

    def test_has_dated_entry(self) -> None:
        self.assertRegex(self.body, DATE_HEADING_RE,
                         "spec 016 amendments must include an ISO-dated entry")

    def test_body_asserts_seven_hooks(self) -> None:
        self.assertTrue(
            "seven" in self.body.lower() or "five → seven" in self.body,
            "spec 016 amendment must state corrected hook count (seven / five → seven)",
        )


class LiveProseHasNoAmendments(unittest.TestCase):
    """ADR-0010: live operational prose is fixed inline — no `## Amendments`."""

    def test_each_live_prose_file_has_no_amendments_section(self) -> None:
        for p in LIVE_PROSE:
            with self.subTest(path=str(p)):
                self.assertNotRegex(
                    _read(p), AMENDMENTS_HEADING_RE,
                    f"{p} is live prose — drift must be corrected inline, "
                    f"not via a '## Amendments' section (ADR-0010)",
                )


class PrReviewArchReviewCorrectedInline(unittest.TestCase):
    """The router-read frontmatter no longer denies arch-review ships."""

    def setUp(self) -> None:
        self.text = _read(PR_REVIEW)

    def test_stale_claim_is_gone(self) -> None:
        self.assertNotIn(
            "does not ship an arch-review skill today", self.text,
            "the stale 'arch-review doesn't ship' claim must be removed "
            "from pr-review SKILL.md (it biased the router)",
        )

    def test_correction_is_inline(self) -> None:
        # The corrected pointer must live in the body/frontmatter, not an
        # amendment block.
        self.assertIn("/jig:arch-review", self.text,
                      "pr-review SKILL.md must point at /jig:arch-review inline")


class MemorySyncSpec002CorrectedInline(unittest.TestCase):
    """The top blockquote reflects spec 002 closed — inline, no amendment."""

    def setUp(self) -> None:
        self.text = _read(MEMORY_SYNC)

    def test_stale_pending_claim_is_gone(self) -> None:
        self.assertNotIn(
            "(reconciliation-integration) are pending", self.text,
            "memory-sync SKILL.md must not still claim 002-03/04 are pending",
        )

    def test_corrected_claim_inline(self) -> None:
        for token in ("002-03", "002-04", "DONE"):
            self.assertIn(token, self.text,
                          f"memory-sync SKILL.md must state {token} inline")


class WorkflowSkillInvocationCorrectedInline(unittest.TestCase):
    """The Skill-invocation prose states auto-trigger inline, no amendment."""

    def setUp(self) -> None:
        self.text = _read(WORKFLOW_MD)

    def test_stale_stub_claim_is_gone(self) -> None:
        self.assertNotIn(
            "do not auto-trigger until implemented", self.text,
            "workflow.md must not still describe the three skills as stubs",
        )

    def test_corrected_claim_inline(self) -> None:
        lower = self.text.lower()
        self.assertIn("auto-trigger", lower)
        for token in ("spec-workflow", "independent-review", "contracts"):
            self.assertIn(token, lower)


class ReconciliationChecklistGate(unittest.TestCase):
    """The closed-spec-drift gate is wired in and points at ADR-0010."""

    def setUp(self) -> None:
        self.text = _read(SPEC_WORKFLOW_SKILL)

    def test_checklist_section_exists(self) -> None:
        self.assertIn("## Reconciliation checklist", self.text)

    def test_gate_names_closed_spec_drift(self) -> None:
        self.assertIn("closed-spec drift", self.text.lower(),
                      "Reconciliation checklist must name the 'closed-spec drift' gate")

    def test_gate_links_adr_0010(self) -> None:
        self.assertIn("adr-0010-amendment-scope-records-vs-live-prose", self.text,
                      "the gate must link to ADR-0010 (supersedes ADR-0008)")

    def test_gate_sits_before_commit(self) -> None:
        section_start = self.text.find("## Reconciliation checklist")
        self.assertNotEqual(section_start, -1)
        next_heading = self.text.find("\n## ", section_start + 1)
        section = self.text[section_start:next_heading if next_heading != -1 else len(self.text)]

        drift_pos = section.lower().find("closed-spec drift")
        commit_pos = section.find("**Commit**")
        self.assertGreater(drift_pos, 0,
                           "closed-spec drift gate not found in reconciliation checklist")
        self.assertGreater(commit_pos, 0,
                           "'**Commit**' gate must remain in reconciliation checklist")
        self.assertLess(drift_pos, commit_pos,
                        "closed-spec drift gate must precede the Commit gate")


if __name__ == "__main__":
    unittest.main()
