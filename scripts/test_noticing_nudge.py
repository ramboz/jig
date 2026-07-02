"""Structural tests for the spec 067-03 reframe noticing nudge.

Slice 067-03 ships a soft, best-effort standing practice — "reframe before
building on a new load-bearing reference" — that is explicitly **not a detector**
and **not a gate** (ADR-0024 §4/§7 / ADR-0011 defense-in-depth). It lands as:

  AC1 — a subsection in jig's own `docs/workflow.md`;
  AC2 — a marker-delimited managed block written by BOTH `scaffold()` and
        `copy_machinery()` so scaffolded / copy-machinery'd projects inherit it,
        sharing the ADR-0002 rule-of-three `_upsert_marked_block` helper;
  AC3 — a one-line cross-reference in `spec-workflow` + `adr-workflow` SKILL.md;
  AC4 — best-effort, no new hook / automated trigger.

Pure-file + in-tmp inspection; no network, no plugin install.
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "skills" / "scaffold-init"))
import scaffold  # noqa: E402

WORKFLOW = REPO_ROOT / "docs" / "workflow.md"
SCAFFOLD_PY = (REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py").read_text()
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"

# Reference categories the practice must name (ADR-0024's load-bearing-reference
# examples).
REF_CATEGORIES = [
    "design system", "vendor", "test", "compliance", "platform",
    "product-positioning",
]


class WorkflowSectionTests(unittest.TestCase):
    """AC1 — the standing practice is present in jig's own docs/workflow.md."""

    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text()
        cls.low = cls.text.lower()

    def test_section_present(self):
        self.assertIn("## Bringing in a new load-bearing reference", self.text)

    def test_points_at_reframe(self):
        self.assertIn("/jig:reframe", self.text)

    def test_names_reference_categories(self):
        for c in REF_CATEGORIES:
            self.assertIn(
                c, self.low, f"reframe practice must name reference category: {c!r}"
            )

    def test_labelled_soft_not_detector_not_gate(self):
        # AC4 surfaced at the practice text: explicitly best-effort, not a detector.
        self.assertIn("not a detector", self.low)
        self.assertIn("not a gate", self.low)

    def test_is_a_managed_block(self):
        self.assertIn(scaffold._REFRAME_BLOCK_BEGIN, self.text)
        self.assertIn(scaffold._REFRAME_BLOCK_END, self.text)

    def test_dogfood_byte_identity_with_render(self):
        # jig's own block is exactly what the writer emits (dogfood).
        block = scaffold._render_reframe_practice_block().strip()
        self.assertIn(block, self.text)


class ScaffoldWriterTests(unittest.TestCase):
    """AC2 — a managed-block writer, called by scaffold() + copy_machinery(),
    sharing the extracted marker-upsert helper (ADR-0002 rule-of-three)."""

    def test_render_and_ensure_exist(self):
        self.assertTrue(hasattr(scaffold, "_render_reframe_practice_block"))
        self.assertTrue(hasattr(scaffold, "_ensure_reframe_practice_block"))

    def test_shares_extracted_upsert_helper(self):
        # ADR-0002 rule-of-three: the marker-upsert core is extracted + shared by
        # the gitignore, self-defining, and reframe blocks.
        self.assertTrue(
            hasattr(scaffold, "_upsert_marked_block"),
            "the marker-upsert mechanic must be extracted to _upsert_marked_block "
            "(3rd caller — ADR-0002 rule-of-three)",
        )

    def test_written_by_both_scaffold_and_copy_machinery(self):
        # Two call sites: copy_machinery() (reaches fresh + --with-machinery and
        # existing projects on their next copy-machinery run) and scaffold()'s
        # --plugin-only branch. Between them every scaffold path writes the block.
        n = len(re.findall(
            r"_ensure_reframe_practice_block\(target, docs_root\)", SCAFFOLD_PY
        ))
        self.assertGreaterEqual(
            n, 2,
            "the reframe block must be written on every scaffold path — a call "
            f"site in copy_machinery() and one in scaffold() (found {n})",
        )

    def test_upsert_orphaned_begin_marker_appends_fresh(self):
        # Documented malformed-input edge (craft-review nit): a begin marker
        # WITHOUT a matching end falls through to append a fresh, well-formed
        # block rather than corrupt the half-block — the orphaned begin + any
        # intervening text are left verbatim.
        begin, end = scaffold._REFRAME_BLOCK_BEGIN, scaffold._REFRAME_BLOCK_END
        block = scaffold._render_reframe_practice_block()
        existing = "# Workflow\n\n" + begin + "\nhalf-written, no end marker\n"
        merged = scaffold._upsert_marked_block(existing, begin, end, block)
        # A fresh, well-formed block was appended (carries both markers)...
        self.assertIn(block.strip(), merged)
        self.assertIn(end, merged)
        # ...and the pre-existing orphaned content is preserved verbatim.
        self.assertIn("half-written, no end marker", merged)

    def test_scaffolded_target_gets_the_block(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            scaffold._ensure_reframe_practice_block(target, "docs")
            wf = target / "docs" / "workflow.md"
            self.assertTrue(wf.is_file(), "workflow.md must be created")
            body = wf.read_text()
            self.assertIn("## Bringing in a new load-bearing reference", body)
            self.assertIn("/jig:reframe", body)

    def test_idempotent_no_duplicate_block(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            scaffold._ensure_reframe_practice_block(target, "docs")
            first = (target / "docs" / "workflow.md").read_text()
            scaffold._ensure_reframe_practice_block(target, "docs")
            second = (target / "docs" / "workflow.md").read_text()
            self.assertEqual(first, second, "re-run must be a no-op")
            self.assertEqual(
                second.count(scaffold._REFRAME_BLOCK_BEGIN), 1,
                "idempotent upsert must not duplicate the block",
            )

    def test_appends_without_clobbering_existing_workflow(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / "docs").mkdir()
            (target / "docs" / "workflow.md").write_text(
                "# Workflow\n\n## Existing section\n\nkeep me.\n"
            )
            scaffold._ensure_reframe_practice_block(target, "docs")
            body = (target / "docs" / "workflow.md").read_text()
            self.assertIn("## Existing section", body)
            self.assertIn("keep me.", body)
            self.assertIn("## Bringing in a new load-bearing reference", body)


class CrossRefTests(unittest.TestCase):
    """AC3 — the lifecycle skills point at /jig:reframe for a moved reference."""

    @staticmethod
    def _collapsed(path: Path) -> str:
        # Collapse whitespace so the assertion is robust to markdown line-wrapping
        # (e.g. "load-bearing\nreference" across a line break).
        return " ".join(path.read_text().lower().split())

    def test_spec_workflow_cross_ref(self):
        t = self._collapsed(REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md")
        self.assertIn("/jig:reframe", t)
        self.assertIn("load-bearing reference", t)

    def test_adr_workflow_cross_ref(self):
        t = self._collapsed(REPO_ROOT / "skills" / "adr-workflow" / "SKILL.md")
        self.assertIn("/jig:reframe", t)
        self.assertIn("load-bearing reference", t)


class NoNewHookTests(unittest.TestCase):
    """AC4 — the nudge is doc-only: no hook or automated trigger is registered."""

    def test_no_reframe_hook_registered(self):
        hooks = HOOKS_JSON.read_text().lower()
        self.assertNotIn(
            "reframe", hooks,
            "067-03 must NOT register a hook — the noticing nudge is doc-only, "
            "soft, and not a detector (ADR-0024 §7)",
        )


if __name__ == "__main__":
    unittest.main()
