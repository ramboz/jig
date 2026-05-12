"""
AC verification tests for slice 004-01 (review-helper).

Run from the repo root:
    python3 skills/independent-review/test_review.py
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW = REPO_ROOT / "skills" / "independent-review" / "review.py"
SKILL_MD = REPO_ROOT / "skills" / "independent-review" / "SKILL.md"


def run_review(*args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(REVIEW), *args],
        capture_output=True, text=True, env=env,
    )


def write_synthetic_spec(path: Path, slice_name: str, status: str = "IN_PROGRESS") -> None:
    path.write_text(
        "---\nstatus: DRAFT\n---\n\n"
        "# Spec X\n\n"
        f"## Slice {slice_name}\n\n"
        f"**STATUS: {status}**\n\n"
        "**Goal:** placeholder.\n\n"
        "**Acceptance Criteria:**\n"
        "1. Thing one happens.\n"
        "2. Thing two happens.\n\n"
        "### Deviation log (after reconciliation)\n\n"
        "Some claims about what changed.\n"
    )


class ImplementationPromptTests(unittest.TestCase):
    """`review.py implementation <spec> <slice> <deliverable>...` shape."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-rev-")
        self.spec = Path(self.tmpdir) / "spec.md"
        write_synthetic_spec(self.spec, "001-01 alpha")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _prompt(self, *extra_args: str):
        result = run_review("implementation", str(self.spec), "001-01",
                            "skills/foo/foo.py", "skills/foo/test_foo.py", *extra_args)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        return result.stdout

    def test_includes_standard_preamble(self):
        prompt = self._prompt()
        self.assertIn("You are an independent reviewer", prompt)
        self.assertIn("seeing this work for the first time", prompt)

    def test_includes_spec_path(self):
        prompt = self._prompt()
        self.assertIn(str(self.spec), prompt)

    def test_includes_slice_fragment(self):
        prompt = self._prompt()
        # The slice fragment or its full label should be present
        self.assertIn("001-01", prompt)

    def test_lists_deliverable_paths(self):
        prompt = self._prompt()
        self.assertIn("skills/foo/foo.py", prompt)
        self.assertIn("skills/foo/test_foo.py", prompt)

    def test_includes_dont_refer_to_prior(self):
        prompt = self._prompt()
        self.assertRegex(prompt, r"(?i)not.+refer.+prior|prior.+reasoning")

    def test_includes_no_soften_directive(self):
        prompt = self._prompt()
        self.assertRegex(prompt, r"(?i)soften.+feedback|not\s+soften")

    def test_includes_no_file_writes_directive(self):
        prompt = self._prompt()
        self.assertRegex(prompt, r"(?i)do not\s+(?:write|modify|edit).+files?|read-only")

    def test_includes_no_memory_writes_directive(self):
        prompt = self._prompt()
        # Must explicitly call out docs/memory/ — reviewer never defines glossary
        self.assertIn("docs/memory", prompt)

    def test_includes_output_format(self):
        prompt = self._prompt()
        # All four output sections must be present
        for marker in ("VERDICT", "REASONING", "SPECIFIC ISSUES", "RECONCILIATION NOTES"):
            self.assertIn(marker, prompt, f"missing output marker: {marker}")

    def test_includes_verdict_options(self):
        prompt = self._prompt()
        self.assertRegex(prompt, r"pass\s*\|\s*fail\s*\|\s*needs-changes")


class ReconciliationPromptTests(unittest.TestCase):
    """`review.py reconciliation <spec> <slice>` shape."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-rev2-")
        self.spec = Path(self.tmpdir) / "spec.md"
        write_synthetic_spec(self.spec, "001-01 alpha")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _prompt(self):
        result = run_review("reconciliation", str(self.spec), "001-01")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        return result.stdout

    def test_includes_standard_preamble(self):
        prompt = self._prompt()
        self.assertIn("You are an independent reviewer", prompt)

    def test_frames_as_reconciliation_review(self):
        prompt = self._prompt()
        self.assertRegex(prompt, r"(?i)reconciliation\s+review")

    def test_explicitly_excludes_ac_re_review(self):
        prompt = self._prompt()
        # Must tell the reviewer not to re-evaluate against original ACs
        self.assertRegex(prompt, r"(?i)not\s+re-?reviewing.+(?:original\s+)?ACs?")

    def test_points_at_deviation_log(self):
        prompt = self._prompt()
        self.assertRegex(prompt, r"(?i)deviation\s+log")

    def test_includes_output_format(self):
        prompt = self._prompt()
        for marker in ("VERDICT", "REASONING"):
            self.assertIn(marker, prompt, f"missing output marker: {marker}")

    def test_no_deliverable_paths_required(self):
        """reconciliation mode takes only spec + slice — no deliverable args."""
        # Already exercised by self._prompt() — confirms no extra args needed
        result = run_review("reconciliation", str(self.spec), "001-01")
        self.assertEqual(result.returncode, 0)


class HelperErrorTests(unittest.TestCase):
    """review.py refuses bad input with exit 2."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-rev-err-")
        self.spec = Path(self.tmpdir) / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_refuses_missing_spec(self):
        result = run_review("implementation", str(self.spec), "001-01", "deliv.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    def test_refuses_unknown_slice(self):
        write_synthetic_spec(self.spec, "001-01 alpha")
        result = run_review("implementation", str(self.spec), "999-99", "deliv.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    def test_refuses_ambiguous_slice(self):
        self.spec.write_text(
            "## Slice 001-01 alpha\n\n**STATUS: DRAFT**\n\n"
            "## Slice 001-01 alpha-fork\n\n**STATUS: DRAFT**\n"
        )
        result = run_review("implementation", str(self.spec), "001-01", "deliv.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("ambig", result.stderr.lower())

    def test_implementation_requires_at_least_one_deliverable(self):
        write_synthetic_spec(self.spec, "001-01 alpha")
        # No deliverable args
        result = run_review("implementation", str(self.spec), "001-01")
        self.assertNotEqual(result.returncode, 0)


class SkillPromotionTests(unittest.TestCase):
    """The independent-review SKILL.md must be promoted from stub to active."""

    def setUp(self):
        self.skill = SKILL_MD.read_text()

    def test_skill_frontmatter_no_disable_invocation(self):
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        self.assertIsNotNone(m, "SKILL.md must have frontmatter")
        fm = m.group(1)
        self.assertNotIn("disable-model-invocation: true", fm,
                         "independent-review must auto-trigger (frontmatter promoted)")

    def test_skill_is_user_invocable(self):
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        fm = m.group(1)
        self.assertNotIn("user-invocable: false", fm)

    def test_skill_body_no_stub_banner(self):
        self.assertNotRegex(
            self.skill,
            r"(?i)status:\s*draft\s*—\s*not\s+yet\s+implemented",
            "stub banner must be removed",
        )
        self.assertNotIn("(when implemented)", self.skill)

    def test_skill_references_review_helper(self):
        self.assertIn("review.py", self.skill,
                      "SKILL.md must reference the review.py helper")

    def test_skill_describes_both_modes(self):
        # Must explain implementation review AND reconciliation review
        self.assertRegex(self.skill, r"(?i)implementation\s+review")
        self.assertRegex(self.skill, r"(?i)reconciliation\s+review")


if __name__ == "__main__":
    unittest.main()
