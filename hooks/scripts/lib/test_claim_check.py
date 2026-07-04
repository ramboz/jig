"""Unit tests for hooks/scripts/lib/claim_check.py (memory-recall
verification — the cheapest-first-cut mitigation from the refinement-todo
"Memory-recall verification (claims-from-memory linter)" entry).

Hook-integration test is a sibling at
hooks/scripts/test_jig_claim_check.py.

Run from the repo root:
    python3 hooks/scripts/lib/test_claim_check.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claim_check import (  # noqa: E402
    last_assistant_text,
    render_warning,
    scan_claims,
)


def _user(text):
    return {"role": "user", "content": text}


def _agent(text):
    return {"role": "assistant", "content": text}


class LastAssistantTextTests(unittest.TestCase):
    def test_returns_most_recent_assistant_message(self):
        messages = [_user("hi"), _agent("first"), _user("more"), _agent("second")]
        self.assertEqual(last_assistant_text(messages), "second")

    def test_no_assistant_message_returns_empty(self):
        self.assertEqual(last_assistant_text([_user("hi")]), "")

    def test_non_list_returns_empty(self):
        self.assertEqual(last_assistant_text(None), "")

    def test_content_block_list_extracts_text_only(self):
        messages = [_agent([
            {"type": "text", "text": "spec 042"},
            {"type": "tool_use", "name": "Read", "input": {}},
        ])]
        self.assertEqual(last_assistant_text(messages), "spec 042")


class ScanClaimsTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-claimcheck-")
        self.project = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_spec(self, num, slug="demo", slices=()):
        spec_dir = self.project / "docs" / "specs" / f"{num:03d}-{slug}"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text(
            "---\nstatus: DONE\n---\n\n# Spec\n\n## Overview\n\nx.\n"
        )
        for slice_no in slices:
            (spec_dir / f"slice-{slice_no:02d}-thing.md").write_text(
                f"---\nstatus: DONE\n---\n\n## Slice {num:03d}-{slice_no:02d} — thing\n"
            )
        return spec_dir

    def _make_adr(self, num, slug="decision"):
        decisions_dir = self.project / "docs" / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        (decisions_dir / f"adr-{num:04d}-{slug}.md").write_text("# ADR\n")

    def test_existing_spec_resolves(self):
        self._make_spec(42)
        claims = scan_claims(str(self.project), "see spec 42 for details")
        self.assertEqual(len(claims), 1)
        self.assertTrue(claims[0].resolved)
        self.assertEqual(claims[0].label, "spec 42")

    def test_missing_spec_unresolved(self):
        claims = scan_claims(str(self.project), "see spec 999 for details")
        self.assertEqual(len(claims), 1)
        self.assertFalse(claims[0].resolved)

    def test_existing_slice_file_resolves(self):
        self._make_spec(42, slices=(1,))
        claims = scan_claims(str(self.project), "slice 42-01 is done")
        self.assertEqual(len(claims), 1)
        self.assertTrue(claims[0].resolved)
        self.assertEqual(claims[0].label, "slice 042-01")

    def test_missing_slice_in_existing_spec_unresolved(self):
        self._make_spec(42, slices=(1,))
        claims = scan_claims(str(self.project), "slice 42-99 handles that")
        self.assertEqual(len(claims), 1)
        self.assertFalse(claims[0].resolved)

    def test_embedded_slice_heading_resolves(self):
        # File-per-slice layout isn't the only shape — an embedded
        # `## Slice NNN-NN` heading inside spec.md also counts.
        spec_dir = self._make_spec(42)
        (spec_dir / "spec.md").write_text(
            "---\nstatus: DONE\n---\n\n## Slice 042-03 — embedded\n\n**Goal:** x.\n"
        )
        claims = scan_claims(str(self.project), "slice 42-03 covers it")
        self.assertTrue(claims[0].resolved)

    def test_existing_adr_resolves(self):
        self._make_adr(11)
        claims = scan_claims(str(self.project), "per ADR-0011 this is fine")
        self.assertEqual(len(claims), 1)
        self.assertTrue(claims[0].resolved)
        self.assertEqual(claims[0].label, "ADR-0011")

    def test_missing_adr_unresolved(self):
        claims = scan_claims(str(self.project), "per ADR-0099 this is fine")
        self.assertFalse(claims[0].resolved)

    def test_case_insensitive_and_zero_padding(self):
        self._make_adr(11)
        claims = scan_claims(str(self.project), "per adr-11 this is fine")
        self.assertTrue(claims[0].resolved)
        self.assertEqual(claims[0].label, "ADR-0011")

    def test_no_claims_returns_empty(self):
        self.assertEqual(scan_claims(str(self.project), "just some prose"), [])

    def test_duplicate_mentions_deduped(self):
        self._make_spec(42)
        claims = scan_claims(
            str(self.project), "spec 42 and spec 42 again")
        self.assertEqual(len(claims), 1)

    def test_mixed_claims_in_one_message(self):
        self._make_spec(42, slices=(1,))
        self._make_adr(11)
        text = "spec 42 has slice 42-01; per ADR-0011 and spec 999"
        claims = scan_claims(str(self.project), text)
        by_label = {c.label: c.resolved for c in claims}
        self.assertEqual(by_label, {
            "spec 42": True,
            "slice 042-01": True,
            "ADR-0011": True,
            "spec 999": False,
        })


class RenderWarningTests(unittest.TestCase):
    def test_empty_claims_renders_nothing(self):
        self.assertEqual(render_warning([]), "")

    def test_all_resolved_renders_nothing(self):
        from claim_check import Claim
        self.assertEqual(
            render_warning([Claim("spec", "spec 42", True)]), "")

    def test_unresolved_claim_renders_warning(self):
        from claim_check import Claim
        msg = render_warning([Claim("spec", "spec 999", False)])
        self.assertIn("spec 999", msg)
        self.assertIn("verify", msg.lower())

    def test_only_unresolved_listed(self):
        from claim_check import Claim
        msg = render_warning([
            Claim("spec", "spec 42", True),
            Claim("spec", "spec 999", False),
        ])
        self.assertNotIn("spec 42", msg)
        self.assertIn("spec 999", msg)


if __name__ == "__main__":
    unittest.main()
