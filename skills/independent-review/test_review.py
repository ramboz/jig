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


class SubagentTypeTests(unittest.TestCase):
    """`review.py subagent-type <mode>` — slice 011-02.

    Detection: presence of `${CLAUDE_PLUGIN_ROOT}/agents/reviewer.md`.
    - env var set + reviewer.md present → "reviewer"
    - env var unset → "general-purpose"
    - env var set, reviewer.md absent → "general-purpose" (graceful)
    - env var set to nonexistent path → "general-purpose" (graceful)
    """

    def _run(self, *args: str, env_overrides=None, drop_plugin_root: bool = False):
        env = os.environ.copy()
        if drop_plugin_root:
            env.pop("CLAUDE_PLUGIN_ROOT", None)
        if env_overrides:
            env.update(env_overrides)
        return subprocess.run(
            [sys.executable, str(REVIEW), *args],
            capture_output=True, text=True, env=env,
        )

    def test_returns_reviewer_when_plugin_root_set_and_agent_present(self):
        # Repo root satisfies the "installed" shape: agents/reviewer.md exists
        result = self._run(
            "subagent-type", "implementation",
            env_overrides={"CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0,
                         msg=f"stderr: {result.stderr}")
        self.assertEqual(result.stdout.strip(), "reviewer")

    def test_returns_general_purpose_when_plugin_root_unset(self):
        result = self._run("subagent-type", "implementation",
                           drop_plugin_root=True)
        self.assertEqual(result.returncode, 0,
                         msg=f"stderr: {result.stderr}")
        self.assertEqual(result.stdout.strip(), "general-purpose")

    def test_returns_general_purpose_when_reviewer_missing(self):
        with tempfile.TemporaryDirectory() as td:
            result = self._run(
                "subagent-type", "implementation",
                env_overrides={"CLAUDE_PLUGIN_ROOT": td},
            )
            self.assertEqual(result.returncode, 0,
                             msg=f"stderr: {result.stderr}")
            self.assertEqual(result.stdout.strip(), "general-purpose")

    def test_returns_general_purpose_when_plugin_root_path_missing(self):
        result = self._run(
            "subagent-type", "implementation",
            env_overrides={"CLAUDE_PLUGIN_ROOT": "/no/such/jig/install"},
        )
        self.assertEqual(result.returncode, 0,
                         msg=f"stderr: {result.stderr}")
        self.assertEqual(result.stdout.strip(), "general-purpose")

    def test_reconciliation_mode_returns_same_as_implementation(self):
        # AC #1: mode arg is informational only; both return same name today
        result = self._run(
            "subagent-type", "reconciliation",
            env_overrides={"CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0,
                         msg=f"stderr: {result.stderr}")
        self.assertEqual(result.stdout.strip(), "reviewer")

    def test_missing_mode_argument_errors(self):
        result = self._run("subagent-type", drop_plugin_root=True)
        self.assertNotEqual(result.returncode, 0,
                            msg="argparse should reject missing required arg")

    def test_unknown_mode_argument_errors(self):
        result = self._run("subagent-type", "bogus", drop_plugin_root=True)
        self.assertNotEqual(result.returncode, 0,
                            msg="argparse should reject unknown choice")

    def test_stdout_only_emits_the_name_no_trailing_noise(self):
        # SKILL.md's bash recipe relies on this: `--subagent-type "$(... subagent-type ...)"`
        result = self._run(
            "subagent-type", "implementation",
            env_overrides={"CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0)
        # No leading whitespace, no trailing extras beyond a single newline
        self.assertIn(result.stdout, ("reviewer\n", "reviewer"),
                      f"stdout must be clean for shell substitution; got {result.stdout!r}")


class SkillRecipeIntegrationTests(unittest.TestCase):
    """SKILL.md's bash recipe must call the new helper subcommand (AC #4)."""

    def setUp(self):
        self.skill = SKILL_MD.read_text()

    def test_skill_recipe_calls_subagent_type_subcommand(self):
        # SKILL.md must invoke `review.py … subagent-type <mode>` from its
        # bash recipe. Allow line continuations / closing quotes between
        # `review.py` and `subagent-type`.
        self.assertIn(
            "subagent-type implementation",
            self.skill,
            "SKILL.md must call `subagent-type implementation` to pick the "
            "Task argument deterministically",
        )
        self.assertIn(
            "subagent-type reconciliation",
            self.skill,
            "SKILL.md must call `subagent-type reconciliation` for the "
            "reconciliation-pass recipe",
        )

    def test_skill_no_longer_uses_hand_written_fallback_hedge(self):
        # The pre-011-02 text was: "subagent_type: \"general-purpose\" (or
        # \"reviewer\" if that filesystem-based agent is loaded)". Replace
        # that hedge with deterministic selection via the helper.
        self.assertNotRegex(
            self.skill,
            r"or\s+`?\"reviewer\"`?\s+if\s+that\s+filesystem-based\s+agent",
            "SKILL.md must drop the hand-written fallback hedge — "
            "the helper now picks deterministically",
        )


class ArchitectureNoteTests(unittest.TestCase):
    """AC #8: a sentence under 'Three subagents, no more' notes spec 011 reachability."""

    def test_architecture_md_records_spec_011_reachability(self):
        arch = (REPO_ROOT / "docs" / "architecture.md").read_text()
        # Look for any sentence under "Three subagents" that mentions
        # spec 011 and reachable / installed / live
        self.assertRegex(
            arch,
            r"(?is)Three\s+subagents.*?(spec\s*011|011-0[12]|plugin-self-install)",
            "docs/architecture.md must record that subagents are reachable "
            "in jig's dev env as of spec 011",
        )


class MixedLayoutResolutionTests(unittest.TestCase):
    """Slice 018-02 AC #4: review.py resolves slice fragments correctly
    against a mixed-layout spec dir (one slice in a sibling file, one
    embedded in spec.md). Tests both shapes are equally findable from
    the same `find_slice_label(spec_path, ...)` call."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-rev-mixed-"))
        # Slice 018-01 lives in a sibling file
        (self.tmpdir / "slice-01-foo.md").write_text(
            "---\nstatus: DONE\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 018-01 — alpha-via-file\n\n"
            "**Goal:** Demonstrates file-per-slice resolution.\n"
        )
        # Slice 018-02 lives inside spec.md
        self.spec = self.tmpdir / "spec.md"
        self.spec.write_text(
            "---\nstatus: DRAFT\nskill: spec-workflow\n---\n\n"
            "# Spec 018\n\n## Overview\n\nStuff.\n\n"
            "## Slice 018-02 — beta-via-section\n\n"
            "**STATUS: IN_PROGRESS**\n\n"
            "**Goal:** Demonstrates embedded resolution.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_label_resolves_from_slice_file(self):
        result = run_review(
            "implementation", str(self.spec), "018-01", "x.py",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("018-01 — alpha-via-file", result.stdout)

    def test_label_resolves_from_embedded_section(self):
        result = run_review(
            "implementation", str(self.spec), "018-02", "x.py",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("018-02 — beta-via-section", result.stdout)


if __name__ == "__main__":
    unittest.main()
