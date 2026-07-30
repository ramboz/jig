"""
AC verification tests for slice 004-01 (review-helper).

Run from the repo root:
    python3 skills/independent-review/test_review.py
"""

from __future__ import annotations

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


def run_review(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(REVIEW), *args],
        capture_output=True, text=True, env=env,
        cwd=str(cwd) if cwd else None,
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


# Spec 097-02 / issue #124 instance 2, question 4 — the stable anchor of the
# vacuous-test question both code-review prompts must pose. Asserting a phrase,
# not a runtime gate: a reviewer subagent reads and applies it (see the
# no-lexical-marker-gates note). Always matched against `normalize_ws()` output
# so line-wrapping in the source prompt block can't make the assertion vacuous.
#
# In slice 101-01 four tests were found to pass with the feature removed, and
# the reconciliation reviewer caught the last one essentially by asking this
# question. Making it an explicit prompt line front-loads the catch onto the
# always-on compliance and craft passes instead of a late round.
VACUOUS_TEST_ANCHOR = "would it still pass if the feature under test were deleted"


def normalize_ws(text: str) -> str:
    """Collapse all runs of whitespace to single spaces."""
    return " ".join(text.split())


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

    # Spec 097-02 AC #2 — the compliance prompt poses the vacuous-test question.
    def test_asks_vacuous_test_question(self):
        prompt = self._prompt()
        self.assertIn(
            VACUOUS_TEST_ANCHOR, normalize_ws(prompt),
            "implementation prompt must ask whether each test would still pass "
            "if the feature under test were deleted (spec 097-02 AC #2)",
        )


class InvestigationGuidanceTests(unittest.TestCase):
    """Spec 087-01: narrow-first, deliverable-anchored investigation guidance
    is present in the CODE-review prompts and absent from the PROSE/framing
    prompts (task-shaped, not blanket)."""

    # Stable distinctive marker for the investigation-discipline block.
    HEADING = "How to investigate (read efficiently)"

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-rev-invest-"))
        self.spec = self.tmpdir / "spec.md"
        write_synthetic_spec(self.spec, "001-01 alpha")
        self.bug = self.tmpdir / "docs" / "bugs" / "001-x.md"
        self.bug.parent.mkdir(parents=True)
        self.bug.write_text(
            "---\nstatus: FIXING\nsecurity_surface: false\n---\n\n"
            "# Bug 001\n\n## Symptom\n\nx\n"
        )
        self.summary = self.tmpdir / "health.txt"
        self.summary.write_text("duplication: 0\ncomplexity: ok\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _prompt(self, mode, *extra):
        result = run_review(mode, str(self.spec), "001-01",
                            "skills/foo/foo.py", *extra)
        self.assertEqual(result.returncode, 0, f"{mode} stderr: {result.stderr}")
        return result.stdout

    # --- AC1: compliance prompt carries the block + the five narrow-first moves
    def test_implementation_includes_investigation_block(self):
        prompt = self._prompt("implementation")
        self.assertIn(self.HEADING, prompt)
        self.assertRegex(prompt, r"(?i)anchor")
        self.assertRegex(prompt, r"(?i)locate before you read|Grep/Glob")
        self.assertRegex(prompt, r"(?i)batch")
        self.assertRegex(prompt, r"(?i)focused ranges")
        self.assertRegex(prompt, r"(?i)simpler query|retry")

    # --- AC2: every other code-review pass carries the block
    def test_pr_review_includes_investigation_block(self):
        self.assertIn(self.HEADING, self._prompt("pr-review"))

    def test_arch_review_includes_investigation_block(self):
        self.assertIn(self.HEADING, self._prompt("arch-review"))

    def test_code_health_includes_investigation_block(self):
        self.assertIn(self.HEADING,
                      self._prompt("code-health", "--summary-file", str(self.summary)))

    def test_bug_review_includes_investigation_block(self):
        result = run_review("bug-review", str(self.bug), "skills/foo/foo.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.HEADING, result.stdout)

    # --- AC3: prose/framing passes do NOT carry the block
    def test_reconciliation_excludes_investigation_block(self):
        result = run_review("reconciliation", str(self.spec), "001-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(self.HEADING, result.stdout)

    def test_frame_critique_excludes_investigation_block(self):
        self.assertNotIn(self.HEADING, self._prompt("frame-critique"))

    def test_design_review_excludes_investigation_block(self):
        self.assertNotIn(self.HEADING, self._prompt("design-review"))


class ReviewerAgentInvestigationTests(unittest.TestCase):
    """Spec 087-01 AC4: the standing reviewer agent definition carries an
    equivalent investigation-efficiency section."""

    def test_reviewer_agent_has_investigation_section(self):
        text = (REPO_ROOT / "agents" / "reviewer.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?i)how to investigate")
        self.assertRegex(text, r"(?i)focused ranges|locate before you read")


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

    def test_points_at_reconciliation_sweep(self):
        prompt = self._prompt()
        self.assertIn("Reconciliation sweep", prompt)
        self.assertRegex(prompt, r"(?i)read.+Deviation log.+Reconciliation sweep")

    def test_checks_for_sweep_omissions_across_core_artifacts(self):
        prompt = self._prompt()
        self.assertRegex(prompt, r"(?i)missing.+sweep")
        for artifact in (
            "front-door docs",
            "primers/templates",
            "inbox",
            "refinement todo",
            "memory",
            "ADR index",
            "generated status board",
        ):
            self.assertIn(artifact, prompt)

    def test_judges_sweep_disposition_quality(self):
        prompt = self._prompt()
        for disposition in ("updated", "no-op", "deferred"):
            self.assertIn(disposition, prompt)
        self.assertRegex(prompt, r"(?i)deferred.+(?:owner|trigger)")
        self.assertRegex(prompt, r"(?i)no-op.+(?:touched files|landed behavior)")

    def test_keeps_reconciliation_scope_narrow(self):
        prompt = self._prompt()
        self.assertIn("no scope creep in doc updates", prompt)
        self.assertNotIn("test-quality", prompt)
        self.assertNotIn("implementation review", prompt.lower())

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


class BugReviewPromptTests(unittest.TestCase):
    """Spec 058-04: bug-review prompt shape."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-rev-bug-"))
        self.bug = self.tmpdir / "docs" / "bugs" / "001-cache-race.md"
        self.bug.parent.mkdir(parents=True)
        self.bug.write_text(
            "---\n"
            "status: FIXING\n"
            "tier: standard\n"
            "fix_class: workaround\n"
            "regression_test: tests/test_cache.py::test_race\n"
            "security_surface: false\n"
            "---\n\n"
            "# Bug 001: cache-race\n\n"
            "## Symptom\n\n"
            "Flaky stale cache.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_bug_review_prompt_names_bug_specific_concerns(self):
        result = run_review(
            "bug-review", str(self.bug),
            "skills/bug-fix/bug.py", "skills/bug-fix/test_bug.py",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = result.stdout
        self.assertIn(str(self.bug), prompt)
        self.assertIn("skills/bug-fix/bug.py", prompt)
        for phrase in (
            "root cause vs. symptom",
            "regression test fails without the fix",
            "blast radius",
            "scope creep",
            "workaround honesty",
        ):
            self.assertIn(phrase, prompt)
        self.assertIn("VERDICT: pass | fail | needs-changes", prompt)


class BugReviewEvidenceRecorderTests(unittest.TestCase):
    """Spec 058-04: record-review writes bug-keyed evidence."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-rev-bugev-"))
        self.bug = self.tmpdir / "docs" / "bugs" / "001-cache-race.md"
        self.bug.parent.mkdir(parents=True)
        self.bug.write_text(
            "---\nstatus: FIXING\nsecurity_surface: false\n---\n\n# Bug\n"
        )
        # Bug 017: this fixture is the one that hung the whole suite — it
        # inherited the runner's stdin and record-review read it. Pass the
        # body explicitly, so the fixture never depends on stdin at all.
        self.summary = self.tmpdir / "summary.md"
        self.summary.write_text("## VERDICT\npass\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_record_review_bug_mode_writes_bug_frontmatter(self):
        result = run_review(
            "record-review", "--bug", str(self.bug),
            "--pass", "bug-review",
            "--verdict", "pass",
            "--reviewer", "reviewer",
            "--prompt-source", "review.py bug-review docs/bugs/001-cache-race.md",
            "--summary-file", str(self.summary),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = self.tmpdir / "docs" / "bugs" / "reviews" / "bug-001-bug-review.md"
        self.assertTrue(evidence.is_file())
        text = evidence.read_text()
        self.assertIn("bug: 001", text)
        self.assertIn("pass: bug-review", text)
        self.assertIn("verdict: pass", text)


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

    def test_skill_describes_all_modes(self):
        # Must explain all three modes: implementation, pr-review (slice
        # 031-01 craft pass), and reconciliation.
        self.assertRegex(self.skill, r"(?i)implementation\s+review")
        self.assertRegex(self.skill, r"(?i)reconciliation\s+review")
        self.assertRegex(self.skill, r"(?i)pr-review|craft\s+pass")


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


# ---------------------------------------------------------------------------
# Bug 019 (issue #134) — every prompt must name the file that HOLDS the slice
# ---------------------------------------------------------------------------


# The seven spec+slice prompt modes, with the extra CLI arguments each needs
# beyond `<spec> <slice>`. `bug-review` is excluded on purpose: it takes a bug
# record, not a spec, so it has no slice to resolve.
_SPEC_SLICE_MODES = (
    "implementation",
    "pr-review",
    "arch-review",
    "code-health",
    "frame-critique",
    "design-review",
    "reconciliation",
)


def extract_what_to_read(prompt: str) -> str:
    """Return the `## What to read…` section of a reviewer prompt.

    Bounded to that one section so the assertions below test the reading
    LIST — the instruction that actually sends the reviewer to a file —
    rather than an incidental path mention elsewhere in the prompt.
    """
    start = prompt.find("## What to read")
    assert start >= 0, "prompt has no '## What to read' section"
    nxt = prompt.find("\n## ", start + 1)
    return prompt[start:] if nxt < 0 else prompt[start:nxt]


class FilePerSliceReviewTargetTests(unittest.TestCase):
    """Bug 019 / issue #134: the prompt builders resolved the slice through
    the shared dual-layout loader for its LABEL, then emitted `spec.md` as the
    path to read and dropped the resolved location.

    In a file-per-slice project — the layout `workflow.py new` emits — the
    slice's acceptance criteria, deviation log, and reconciliation sweep live
    in a sibling `slice-NN-*.md`; `spec.md` is only the overview. The
    read-only reviewer is told not to assume context beyond the files it is
    pointed at, so an unattended pass returned a verdict about a file holding
    none of the artifacts it was asked to verify.

    Red without the fix: the slice file's path never appears in the prompt.
    """

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-rev-fps-"))
        # spec.md is the OVERVIEW only — no slice section, no deviation log.
        self.spec = self.tmpdir / "spec.md"
        self.spec.write_text(
            "---\nstatus: DRAFT\nskill: spec-workflow\n---\n\n"
            "# Spec 019 — file-per-slice\n\n## Overview\n\nOverview prose.\n"
        )
        # The slice — and everything a reviewer is asked to verify — is here.
        self.slice_file = self.tmpdir / "slice-01-alpha.md"
        self.slice_file.write_text(
            "---\nstatus: IN_PROGRESS\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 019-01 — alpha\n\n"
            "**Goal:** placeholder.\n\n"
            "**Acceptance Criteria:**\n"
            "1. Thing one happens.\n\n"
            "### Deviation log (after reconciliation)\n\n"
            "Some claims about what changed.\n\n"
            "### Reconciliation sweep\n\n"
            "Swept the artifacts.\n"
        )
        self.summary = self.tmpdir / "health-summary.txt"
        self.summary.write_text("duplication: none\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, mode: str) -> str:
        extra = ["x.py"] if mode != "reconciliation" else []
        if mode == "code-health":
            extra += ["--summary-file", str(self.summary)]
        result = run_review(mode, str(self.spec), "019-01", *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_every_mode_points_at_the_slice_file(self):
        for mode in _SPEC_SLICE_MODES:
            with self.subTest(mode=mode):
                block = extract_what_to_read(self._run(mode))
                self.assertIn(
                    str(self.slice_file), block,
                    f"{mode} sends the reviewer to a file that does not "
                    "contain the slice",
                )

    def test_every_mode_names_the_slice_file_before_the_overview(self):
        """The slice file is the reading target; `spec.md` is context. If the
        overview is named first the reviewer still opens the wrong file
        first — so ordering is part of the fix, not cosmetics."""
        for mode in _SPEC_SLICE_MODES:
            with self.subTest(mode=mode):
                block = extract_what_to_read(self._run(mode))
                slice_pos = block.find(str(self.slice_file))
                spec_pos = block.find(str(self.spec))
                self.assertGreaterEqual(
                    slice_pos, 0, f"{mode} never names the slice file")
                self.assertGreaterEqual(
                    spec_pos, 0, f"{mode} drops the spec overview entirely")
                self.assertLess(
                    slice_pos, spec_pos,
                    f"{mode} names spec.md before the slice file",
                )

    def test_reconciliation_anchors_the_deviation_log_on_the_slice_file(self):
        """The reconciliation prompt names two subsections by title. Both live
        in the slice file; `spec.md` contains neither."""
        block = extract_what_to_read(self._run("reconciliation"))
        slice_pos = block.find(str(self.slice_file))
        self.assertGreaterEqual(slice_pos, 0, "slice file not named at all")
        self.assertLess(
            slice_pos, block.find("Deviation log"),
            "the 'Deviation log' / 'Reconciliation sweep' instruction must "
            "hang off the slice file, not spec.md",
        )

    def test_implementation_focus_instruction_hangs_off_the_slice_file(self):
        """`Focus on Slice X only` is worthless if it attaches to a file with
        no slice in it."""
        block = extract_what_to_read(self._run("implementation"))
        slice_pos = block.find(str(self.slice_file))
        self.assertGreaterEqual(slice_pos, 0, "slice file not named at all")
        self.assertLess(slice_pos, block.find("Focus on Slice"))


class EmbeddedLayoutReviewTargetTests(unittest.TestCase):
    """Bug 019 guard against overcorrection: when the slice IS a section of
    `spec.md`, the prompt must keep naming `spec.md` and must NOT point at a
    sibling slice file.

    Two shapes, because they fail differently. The pure embedded dir has no
    `slice-*.md` to mis-resolve, so it only pins that nothing invents one. The
    MIXED dir is the shape that can actually go wrong: a sibling slice file
    exists, but the requested fragment lives in `spec.md`, so a fix that
    resolved "the spec dir has slice files → point at one" would send the
    reviewer to the WRONG slice's file.
    """

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-rev-emb-"))
        self.spec = self.tmpdir / "spec.md"
        write_synthetic_spec(self.spec, "019-02 — beta")
        # Mixed layout: a sibling slice file for a DIFFERENT slice.
        self.mixed = Path(tempfile.mkdtemp(prefix="jig-rev-mix-"))
        self.mixed_spec = self.mixed / "spec.md"
        write_synthetic_spec(self.mixed_spec, "019-02 — beta")
        self.other_slice = self.mixed / "slice-01-alpha.md"
        self.other_slice.write_text(
            "---\nstatus: DONE\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 019-01 — alpha\n\n**Goal:** a different slice.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        shutil.rmtree(self.mixed, ignore_errors=True)

    def _extra_args(self, mode: str, tmpdir: Path) -> list:
        extra = ["x.py"] if mode != "reconciliation" else []
        if mode == "code-health":
            summary = tmpdir / "s.txt"
            summary.write_text("ok\n")
            extra += ["--summary-file", str(summary)]
        return extra

    def test_embedded_layout_still_reads_spec_md(self):
        for mode in _SPEC_SLICE_MODES:
            with self.subTest(mode=mode):
                result = run_review(
                    mode, str(self.spec), "019-02",
                    *self._extra_args(mode, self.tmpdir))
                self.assertEqual(result.returncode, 0, result.stderr)
                block = extract_what_to_read(result.stdout)
                self.assertIn(str(self.spec), block)
                self.assertNotIn("slice-", block)

    def test_mixed_layout_reads_spec_md_not_the_other_slices_file(self):
        """The sibling `slice-01-alpha.md` holds a DIFFERENT slice. Pointing
        the reviewer at it would be worse than the original bug."""
        for mode in _SPEC_SLICE_MODES:
            with self.subTest(mode=mode):
                result = run_review(
                    mode, str(self.mixed_spec), "019-02",
                    *self._extra_args(mode, self.mixed))
                self.assertEqual(result.returncode, 0, result.stderr)
                block = extract_what_to_read(result.stdout)
                self.assertIn(str(self.mixed_spec), block)
                self.assertNotIn(
                    str(self.other_slice), block,
                    f"{mode} points at a slice file holding a different slice",
                )


# ---------------------------------------------------------------------------
# Slice 022-02 — contract-surface check conditional on architecture.md slot
# ---------------------------------------------------------------------------


CONTRACT_SURFACE_HINT = "Contract-surface check"


class ContractSurfaceCheckTests(unittest.TestCase):
    """Slice 022-02 AC #2: the implementation- and reconciliation-prompt
    builders append a `Contract-surface check` bullet to their Evaluate
    block IFF the project's `docs/architecture.md` has a
    `## Contract surfaces` section with at least one declared-surface
    bullet (matching the wizard output shape from spec 022-02 AC #1).

    Each test sets up a fixture project root with `docs/architecture.md`
    + a spec under `docs/specs/<slug>/spec.md`, runs `review.py`, and
    asserts the presence/absence of the contract-surface hint."""

    def _make_project(self, arch_md_body: str) -> Path:
        """Build a tmpdir project layout:
            <root>/docs/architecture.md   (body = arch_md_body)
            <root>/docs/specs/myspec/spec.md  (synthetic, one slice)
        Returns the spec path."""
        root = Path(tempfile.mkdtemp(prefix="jig-rev-csurf-"))
        self._tmpdirs.append(root)
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "architecture.md").write_text(arch_md_body)
        spec_dir = root / "docs" / "specs" / "myspec"
        spec_dir.mkdir(parents=True)
        spec = spec_dir / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")
        return spec

    def setUp(self):
        self._tmpdirs: list[Path] = []

    def tearDown(self):
        import shutil
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    # ---- impl prompt ----

    def test_impl_prompt_omits_check_when_no_contract_surfaces_section(self):
        spec = self._make_project(
            "# Architecture\n\n## Tech stack\n\nPython.\n\n## Data model\n\nFiles.\n"
        )
        result = run_review("implementation", str(spec), "099-01", "x.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(
            CONTRACT_SURFACE_HINT, result.stdout,
            "no `## Contract surfaces` section → contract-surface "
            "hint must be absent (022-02 AC #2: no surfaces → no check)",
        )

    def test_impl_prompt_omits_check_when_surfaces_section_skipped(self):
        # Wizard wrote the section but the user skipped — no bullets.
        spec = self._make_project(
            "# Architecture\n\n"
            "<!-- elicited: 2026-05-15 / status: skipped -->\n"
            "## Contract surfaces\n\n"
            "_Skipped at elicitation; no external surfaces declared._\n"
        )
        result = run_review("implementation", str(spec), "099-01", "x.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(
            CONTRACT_SURFACE_HINT, result.stdout,
            "`## Contract surfaces` section exists but is empty/skipped → "
            "contract-surface hint must be absent",
        )

    def test_impl_prompt_includes_check_when_surfaces_declared(self):
        spec = self._make_project(
            "# Architecture\n\n"
            "<!-- elicited: 2026-05-15 / status: filled -->\n"
            "## Contract surfaces\n\n"
            "External interfaces this project commits to:\n\n"
            "- **HTTP API** (recommended: OpenAPI 3.x at `openapi.yaml`) — `/v1/foo`, `/v1/bar`\n"
            "- **Internal data shapes** (recommended: JSON Schema) — `src/events/*.schema.json`\n\n"
            "## Next section\n\nStuff.\n"
        )
        result = run_review("implementation", str(spec), "099-01", "x.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            CONTRACT_SURFACE_HINT, result.stdout,
            "declared surfaces → contract-surface hint MUST appear in the "
            "Evaluate section (022-02 AC #2)",
        )
        # Hint must be phrased as a suggestion, not a blocker (AC #4).
        self.assertIn(
            "suggestion", result.stdout.lower(),
            "contract-surface hint must frame as suggestion (not blocker) — "
            "022-02 AC #4 nudge-don't-mandate audit",
        )

    # ---- recon prompt ----

    def test_recon_prompt_omits_check_when_no_surfaces(self):
        spec = self._make_project("# Architecture\n\n## Tech stack\n\nGo.\n")
        result = run_review("reconciliation", str(spec), "099-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(CONTRACT_SURFACE_HINT, result.stdout)

    def test_recon_prompt_includes_check_when_surfaces_declared(self):
        spec = self._make_project(
            "# Architecture\n\n## Contract surfaces\n\n"
            "- **GraphQL** (recommended: SDL at `schema.graphql`)\n"
        )
        result = run_review("reconciliation", str(spec), "099-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            CONTRACT_SURFACE_HINT, result.stdout,
            "022-02 AC #2: reconciliation prompt must ALSO grow the hint "
            "when surfaces are declared (both prompts get the gate)",
        )

    # ---- detection edge cases ----

    def test_detection_is_section_scoped(self):
        """A `## Contract surfaces` heading later in the doc should bound
        cleanly — bullets in OTHER sections must not satisfy the detector.
        This guards against the failure mode where a `- **Foo**` bullet
        in `## Data model` triggers a false positive."""
        spec = self._make_project(
            "# Architecture\n\n"
            "## Contract surfaces\n\n"
            "_Skipped at elicitation — no surfaces declared._\n\n"
            "## Data model\n\n"
            "- **JobStore** — append-only event log.\n"
            "- **CacheLayer** — per-customer build artefacts.\n"
        )
        result = run_review("implementation", str(spec), "099-01", "x.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        # Bullets are in `## Data model`, NOT in `## Contract surfaces`.
        # The detector must scope to the Contract-surfaces section only.
        self.assertNotIn(
            CONTRACT_SURFACE_HINT, result.stdout,
            "detector must scope to `## Contract surfaces` body — bullets "
            "elsewhere must not trigger the hint",
        )

    def test_detection_works_when_section_is_last_in_file(self):
        """No trailing H2 → section bounds extend to EOF. Reviewer prompt
        should still include the check when at least one bullet is present."""
        spec = self._make_project(
            "# Architecture\n\n## Contract surfaces\n\n"
            "- **HTTP API** (recommended: OpenAPI 3.x)\n"
        )
        result = run_review("implementation", str(spec), "099-01", "x.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(CONTRACT_SURFACE_HINT, result.stdout)

    def test_negation_bullet_is_not_a_declaration(self):
        """A bullet like `- **No external surfaces** — library only` is the
        user opting out in-bullet rather than skipping the whole section.
        Detector must NOT treat it as a declared surface (022-02
        post-impl-review fix per reviewer SPECIFIC ISSUE on
        `_DECLARED_SURFACE_BULLET_RE` false positives)."""
        for neg in [
            "- **No external surfaces** — this is a library only.",
            "- **None** — single-consumer internal tool.",
            "- **TBD** — surfaces not yet declared.",
            "- **Not yet** — pre-product-market-fit prototype.",
            "- **Skipped** — opting out for now.",
        ]:
            spec = self._make_project(
                f"# Architecture\n\n## Contract surfaces\n\n{neg}\n"
            )
            result = run_review("implementation", str(spec), "099-01", "x.py")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(
                CONTRACT_SURFACE_HINT, result.stdout,
                f"negation-bullet {neg!r} must NOT trigger the contract "
                "hint — it's an in-bullet opt-out, not a declaration",
            )

    def test_mixed_negation_and_declaration_fires(self):
        """If even ONE bullet is a real declaration, the hint fires —
        even alongside negation bullets explaining what's NOT exposed."""
        spec = self._make_project(
            "# Architecture\n\n## Contract surfaces\n\n"
            "- **No async messaging** — synchronous only.\n"
            "- **HTTP API** (recommended: OpenAPI 3.x) — `/v1/foo`\n"
        )
        result = run_review("implementation", str(spec), "099-01", "x.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(CONTRACT_SURFACE_HINT, result.stdout)


# ---------------------------------------------------------------------------
# Slice 024-01 — unconditional principles-check block (constitution-gate)
# ---------------------------------------------------------------------------


PRINCIPLES_CHECK_HINT = "Principles check"


class PrinciplesCheckBlockTests(unittest.TestCase):
    """Slice 024-01 AC #6: the implementation- and reconciliation-prompt
    builders UNCONDITIONALLY append a `Principles check` bullet to their
    Evaluate block, asking the reviewer to verify the slice doesn't
    violate any of the seven principles in `docs/product-vision.md`
    § Design principles.

    Unlike `_contract_surface_check_block()` (which is gated on
    `has_declared_contract_surfaces`), this block has NO gate — principle
    adherence is universal.

    Tests cover:
      (a) helper returns a block containing "principles 1" and
          "principles 7" grep markers
      (b) both prompt builders include the block
      (c) the block references `docs/product-vision.md`
      (d) the block stays under 500 characters (prompt-size hygiene)
      (e) the block appends UNCONDITIONALLY (no gating on contract-surface
          presence or similar — different from 022-02's helper)
    """

    def setUp(self):
        self._tmpdirs: list[Path] = []

    def tearDown(self):
        import shutil
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _import_review_module(self):
        """Load `review.py` as a module so we can call `_principles_check_block`
        directly. Using importlib keeps this independent of subprocess
        invocation — we just need the in-process return value."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "review_module_024", REVIEW,
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    # ---- (a) helper-level: block contains principle-1 and principle-7 markers

    def test_helper_block_names_principle_1_and_7(self):
        module = self._import_review_module()
        block = module._principles_check_block()
        block_lower = block.lower()
        self.assertIn(
            "principles 1", block_lower,
            "helper must reference 'principles 1' as a grep marker for "
            "principle-1 (hooks deterministic / skills judgment)",
        )
        self.assertIn(
            "principles 7", block_lower,
            "helper must reference 'principles 7' as a grep marker for "
            "principle-7 (scaffolding beats renting)",
        )

    # ---- (b) both prompt builders include the block

    def _make_minimal_spec(self) -> Path:
        """Build a tmpdir with `docs/architecture.md` containing NO
        contract-surfaces section — this proves the block appears even
        when the contract-surface check is OMITTED."""
        root = Path(tempfile.mkdtemp(prefix="jig-rev-pchk-"))
        self._tmpdirs.append(root)
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "architecture.md").write_text(
            "# Architecture\n\n## Tech stack\n\nPython.\n"
        )
        spec_dir = root / "docs" / "specs" / "myspec"
        spec_dir.mkdir(parents=True)
        spec = spec_dir / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")
        return spec

    def test_impl_prompt_includes_principles_block(self):
        spec = self._make_minimal_spec()
        result = run_review("implementation", str(spec), "099-01", "x.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            PRINCIPLES_CHECK_HINT, result.stdout,
            "024-01 AC #6: implementation prompt MUST include the "
            "Principles check block unconditionally",
        )

    def test_recon_prompt_includes_principles_block(self):
        spec = self._make_minimal_spec()
        result = run_review("reconciliation", str(spec), "099-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            PRINCIPLES_CHECK_HINT, result.stdout,
            "024-01 AC #6: reconciliation prompt MUST include the "
            "Principles check block unconditionally",
        )

    # ---- (c) the block references docs/product-vision.md

    def test_helper_block_references_product_vision_md(self):
        module = self._import_review_module()
        block = module._principles_check_block()
        self.assertIn(
            "docs/product-vision.md", block,
            "block must cite `docs/product-vision.md` so the reviewer "
            "can grep the seven principles",
        )
        self.assertIn(
            "Design principles", block,
            "block must name the `## Design principles` section",
        )

    # ---- (d) the block stays under 500 characters (prompt-size hygiene)

    def test_helper_block_under_500_chars(self):
        module = self._import_review_module()
        block = module._principles_check_block()
        self.assertLess(
            len(block), 500,
            f"prompt-size hygiene: block must be < 500 chars; got "
            f"{len(block)}. Same precedent as `_contract_surface_check_block()`.",
        )

    # ---- (e) the block appends UNCONDITIONALLY (no gating)

    def test_block_appears_with_no_arch_md(self):
        """Even when the project has NO `docs/architecture.md` (which
        would silence the contract-surface check), the principles block
        must still fire — it has no gate."""
        # Build a tmpdir with no docs/architecture.md at all.
        root = Path(tempfile.mkdtemp(prefix="jig-rev-pchk-noarch-"))
        self._tmpdirs.append(root)
        spec = root / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")
        result = run_review("implementation", str(spec), "099-01", "x.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            PRINCIPLES_CHECK_HINT, result.stdout,
            "024-01 AC #6: principles block must appear even without "
            "architecture.md — no gating",
        )
        # And the contract-surface hint must NOT appear (no arch.md).
        self.assertNotIn(
            CONTRACT_SURFACE_HINT, result.stdout,
            "no architecture.md → contract-surface hint stays absent; "
            "the two checks are independent",
        )

    def test_block_appears_alongside_contract_surface_hint(self):
        """When BOTH checks fire (declared surfaces + universal principles),
        both blocks must be present in the prompt."""
        root = Path(tempfile.mkdtemp(prefix="jig-rev-pchk-both-"))
        self._tmpdirs.append(root)
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "architecture.md").write_text(
            "# Architecture\n\n## Contract surfaces\n\n"
            "- **HTTP API** (recommended: OpenAPI 3.x) — `/v1/foo`\n"
        )
        spec_dir = root / "docs" / "specs" / "myspec"
        spec_dir.mkdir(parents=True)
        spec = spec_dir / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")
        result = run_review("implementation", str(spec), "099-01", "x.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(CONTRACT_SURFACE_HINT, result.stdout)
        self.assertIn(PRINCIPLES_CHECK_HINT, result.stdout)


# ---------------------------------------------------------------------------
# Engineering-practices check block (SDD process gaps)
# ---------------------------------------------------------------------------


PRACTICES_CHECK_HINT = "Engineering-practices check"


class PracticesCheckBlockTests(unittest.TestCase):
    """The implementation- and reconciliation-prompt builders UNCONDITIONALLY
    append an `Engineering-practices check` bullet covering four SDD
    process gaps (task completeness, approach alignment, ADR signal,
    tech-debt tracking).

    Unlike `_contract_surface_check_block()` (gated on
    `has_declared_contract_surfaces`), this block has no gate — the
    reviewer self-gates on "not applicable" cases.

    Tests cover:
      (a) helper returns a block naming the four sub-checks
      (b) both prompt builders include the block
      (c) the block references jig's debt-tracking files
      (d) the block stays under 900 characters (looser than the
          500-char principles bound — four sub-bullets need more room)
      (e) the block appends UNCONDITIONALLY (no gating)
    """

    def setUp(self):
        self._tmpdirs: list[Path] = []

    def tearDown(self):
        import shutil
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _import_review_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "review_module_practices", REVIEW,
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    # ---- (a) helper names the four sub-checks

    def test_helper_block_names_four_subchecks(self):
        module = self._import_review_module()
        block = module._practices_check_block()
        for marker in (
            "Task completeness",
            "Approach alignment",
            "ADR signal",
            "Tech-debt tracking",
        ):
            self.assertIn(marker, block,
                          f"helper must name '{marker}' as one of the "
                          "four sub-checks")

    # ---- (b) both prompt builders include the block

    def _make_minimal_spec(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="jig-rev-pract-"))
        self._tmpdirs.append(root)
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "architecture.md").write_text(
            "# Architecture\n\n## Tech stack\n\nPython.\n"
        )
        spec_dir = root / "docs" / "specs" / "myspec"
        spec_dir.mkdir(parents=True)
        spec = spec_dir / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")
        return spec

    def test_impl_prompt_includes_practices_block(self):
        spec = self._make_minimal_spec()
        result = run_review("implementation", str(spec), "099-01", "x.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(PRACTICES_CHECK_HINT, result.stdout,
                      "implementation prompt MUST include the "
                      "engineering-practices check block unconditionally")

    def test_recon_prompt_includes_practices_block(self):
        spec = self._make_minimal_spec()
        result = run_review("reconciliation", str(spec), "099-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(PRACTICES_CHECK_HINT, result.stdout,
                      "reconciliation prompt MUST include the "
                      "engineering-practices check block unconditionally")

    # ---- (c) the block references jig's debt-tracking files

    def test_helper_block_references_jig_debt_files(self):
        module = self._import_review_module()
        block = module._practices_check_block()
        self.assertIn("docs/inbox.md", block,
                      "block must cite docs/inbox.md as a tech-debt "
                      "tracking location")
        self.assertIn("docs/refinement-todo.md", block,
                      "block must cite docs/refinement-todo.md as a "
                      "deferred-decision tracking location")

    # ---- (d) the block stays under 900 characters

    def test_helper_block_under_900_chars(self):
        module = self._import_review_module()
        block = module._practices_check_block()
        self.assertLess(len(block), 900,
                        f"prompt-size hygiene: block must be < 900 chars "
                        f"(four sub-bullets need more room than the "
                        f"500-char principles bound); got {len(block)}.")

    # ---- (e) the block appends UNCONDITIONALLY (no gating)

    def test_block_appears_with_no_arch_md(self):
        """Even when the project has NO docs/architecture.md (which would
        silence the contract-surface check), the practices block must
        still fire — it has no gate."""
        root = Path(tempfile.mkdtemp(prefix="jig-rev-pract-noarch-"))
        self._tmpdirs.append(root)
        spec_dir = root / "docs" / "specs" / "myspec"
        spec_dir.mkdir(parents=True)
        spec = spec_dir / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")
        result = run_review("implementation", str(spec), "099-01", "x.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(PRACTICES_CHECK_HINT, result.stdout)


# ---------------------------------------------------------------------------
# Slice 031-01 — pr-review mode (post-implementation craft pass)
# ---------------------------------------------------------------------------


class PrReviewPromptTests(unittest.TestCase):
    """Slice 031-01 AC #1: `review.py pr-review <spec> <slice> <deliverable>...`
    builds a self-contained prompt that:
      - tells the reviewer it's seeing the work for the first time
      - cites the deliverable file paths verbatim
      - does NOT re-evaluate ACs (that's the compliance pass's job)
      - names the four canonical output buckets (scope / blockers / nits /
        strengths) the `jig:pr-review` skill produces
      - instructs the reviewer to apply the craft concerns from the
        most-specific `pr-review` SKILL.md reachable
      - wraps the output in the standard VERDICT/REASONING/SPECIFIC
        ISSUES/RECONCILIATION NOTES envelope
      - tags SPECIFIC ISSUES entries [blocker]/[nit]/[strength]
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-rev-prr-")
        self.spec = Path(self.tmpdir) / "spec.md"
        write_synthetic_spec(self.spec, "031-01 alpha")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _prompt(self, *extra_args: str):
        result = run_review(
            "pr-review", str(self.spec), "031-01",
            "skills/foo/foo.py", "skills/foo/test_foo.py", *extra_args,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        return result.stdout

    # AC #1 — standard preamble
    def test_includes_standard_preamble(self):
        prompt = self._prompt()
        self.assertIn("You are an independent reviewer", prompt)
        self.assertIn("seeing this work for the first time", prompt)

    # AC #1 — cites deliverable paths verbatim
    def test_lists_deliverable_paths_verbatim(self):
        prompt = self._prompt()
        self.assertIn("skills/foo/foo.py", prompt)
        self.assertIn("skills/foo/test_foo.py", prompt)

    # AC #1 — does NOT re-evaluate ACs
    def test_does_not_re_evaluate_acceptance_criteria(self):
        prompt = self._prompt()
        # The compliance pass owns AC re-evaluation; the craft pass must NOT
        # tell the reviewer to walk each AC.
        self.assertNotRegex(
            prompt,
            r"(?i)for\s+each\s+acceptance\s+criterion",
            "pr-review prompt must not re-evaluate ACs — that's the "
            "compliance pass's job (031-01 AC #1)",
        )

    # AC #1 — names the four canonical output buckets
    def test_names_four_output_buckets(self):
        prompt = self._prompt()
        for bucket in ("Scope", "Blockers", "Nits", "Strengths"):
            self.assertIn(
                bucket, prompt,
                f"pr-review prompt must name the '{bucket}' output bucket "
                f"(031-01 AC #1: scope / blockers / nits / strengths)",
            )

    # AC #1 — instructs reviewer to apply pr-review skill's craft concerns
    def test_instructs_reviewer_to_apply_pr_review_skill(self):
        prompt = self._prompt()
        # The prompt must point the reviewer at the `pr-review` SKILL.md so
        # the most-specific installed one wins (031-01 AC #4).
        self.assertRegex(
            prompt,
            r"(?is)pr-review.*SKILL\.md",
            "pr-review prompt must instruct reviewer to apply the most-"
            "specific `pr-review` SKILL.md concerns (031-01 AC #1 + #4)",
        )

    # AC #1 — wraps output in canonical envelope
    def test_includes_verdict_envelope(self):
        prompt = self._prompt()
        for marker in ("VERDICT", "REASONING", "SPECIFIC ISSUES",
                       "RECONCILIATION NOTES"):
            self.assertIn(
                marker, prompt,
                f"pr-review prompt must wrap output in the canonical "
                f"envelope; missing marker: {marker} (031-01 AC #1)",
            )
        # And the verdict options must be the same enumerated set
        self.assertRegex(prompt, r"pass\s*\|\s*fail\s*\|\s*needs-changes")

    # AC #1 — SPECIFIC ISSUES entries tagged [blocker] / [nit] / [strength]
    def test_specific_issues_entries_tagged(self):
        prompt = self._prompt()
        # The prompt must instruct the reviewer to tag SPECIFIC ISSUES
        # entries [blocker] / [nit] / [strength] so the workflow can
        # decide what blocks vs. becomes a reconciliation-log entry.
        for tag in ("[blocker]", "[nit]", "[strength]"):
            self.assertIn(
                tag, prompt,
                f"pr-review prompt must instruct reviewer to tag SPECIFIC "
                f"ISSUES entries with {tag} (031-01 AC #1)",
            )

    # AC #5 — read-only constraint (inherited from preamble + prohibitions)
    def test_includes_read_only_directive(self):
        prompt = self._prompt()
        self.assertRegex(
            prompt, r"(?i)do not\s+(?:write|modify|edit).+files?|read-only",
        )

    # Spec 097-02 AC #2 — the craft prompt poses the vacuous-test question too.
    def test_asks_vacuous_test_question(self):
        prompt = self._prompt()
        self.assertIn(
            VACUOUS_TEST_ANCHOR, normalize_ws(prompt),
            "pr-review prompt must ask whether each test would still pass if "
            "the feature under test were deleted (spec 097-02 AC #2)",
        )

    # Spec path appears for context
    def test_includes_spec_path(self):
        prompt = self._prompt()
        self.assertIn(str(self.spec), prompt)

    # Slice label appears for context
    def test_includes_slice_label(self):
        prompt = self._prompt()
        self.assertIn("031-01", prompt)

    # CLI surface — requires at least one deliverable
    def test_pr_review_requires_at_least_one_deliverable(self):
        result = run_review("pr-review", str(self.spec), "031-01")
        self.assertNotEqual(result.returncode, 0)

    # CLI surface — fails cleanly on missing spec
    def test_pr_review_refuses_missing_spec(self):
        missing = Path(self.tmpdir) / "nope.md"
        result = run_review("pr-review", str(missing), "031-01", "x.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    # CLI surface — fails cleanly on unknown slice
    def test_pr_review_refuses_unknown_slice(self):
        result = run_review("pr-review", str(self.spec), "999-99", "x.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())


class PrReviewSubagentTypeTests(unittest.TestCase):
    """Slice 031-01 AC #2: `review.py subagent-type pr-review` returns the
    same precedence the existing `subagent-type` subcommand uses for
    `jig:reviewer` (plugin) vs. `general-purpose` (running from source)."""

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

    def test_pr_review_returns_reviewer_when_plugin_root_set(self):
        # AC #2: same precedence rule as implementation/reconciliation
        result = self._run(
            "subagent-type", "pr-review",
            env_overrides={"CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        self.assertEqual(result.stdout.strip(), "reviewer")

    def test_pr_review_returns_general_purpose_when_plugin_root_unset(self):
        result = self._run("subagent-type", "pr-review", drop_plugin_root=True)
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        self.assertEqual(result.stdout.strip(), "general-purpose")

    def test_pr_review_returns_general_purpose_when_reviewer_missing(self):
        with tempfile.TemporaryDirectory() as td:
            result = self._run(
                "subagent-type", "pr-review",
                env_overrides={"CLAUDE_PLUGIN_ROOT": td},
            )
            self.assertEqual(result.returncode, 0,
                             msg=f"stderr: {result.stderr}")
            self.assertEqual(result.stdout.strip(), "general-purpose")


# ---------------------------------------------------------------------------
# Slice 031-02 — arch-review mode (post-implementation arch pass, on-demand)
# ---------------------------------------------------------------------------


class ArchReviewPromptTests(unittest.TestCase):
    """Slice 031-02 AC #2: `review.py arch-review <spec> <slice> <deliverable>...`
    builds a self-contained prompt that:
      - tells the reviewer it's seeing the work for the first time
      - cites the deliverable file paths verbatim
      - does NOT re-evaluate ACs (compliance pass's job)
      - names the four canonical arch-review output buckets (summary /
        strengths / concerns / open questions) the `jig:arch-review`
        skill produces
      - instructs the reviewer to apply arch concerns from the
        most-specific `arch-review` SKILL.md reachable
      - wraps output in the same VERDICT/REASONING/SPECIFIC ISSUES/
        RECONCILIATION NOTES envelope as `pr-review`
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-rev-arr-")
        self.spec = Path(self.tmpdir) / "spec.md"
        write_synthetic_spec(self.spec, "031-02 alpha")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _prompt(self, *extra_args: str):
        result = run_review(
            "arch-review", str(self.spec), "031-02",
            "skills/foo/foo.py", "skills/foo/test_foo.py", *extra_args,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        return result.stdout

    # AC #2 — standard preamble
    def test_includes_standard_preamble(self):
        prompt = self._prompt()
        self.assertIn("You are an independent reviewer", prompt)
        self.assertIn("seeing this work for the first time", prompt)

    # AC #2 — cites deliverable paths verbatim
    def test_lists_deliverable_paths_verbatim(self):
        prompt = self._prompt()
        self.assertIn("skills/foo/foo.py", prompt)
        self.assertIn("skills/foo/test_foo.py", prompt)

    # AC #2 — does NOT re-evaluate ACs
    def test_does_not_re_evaluate_acceptance_criteria(self):
        prompt = self._prompt()
        # The compliance pass owns AC re-evaluation; the arch pass must NOT
        # tell the reviewer to walk each AC.
        self.assertNotRegex(
            prompt,
            r"(?i)for\s+each\s+acceptance\s+criterion",
            "arch-review prompt must not re-evaluate ACs — that's the "
            "compliance pass's job (031-02 AC #2)",
        )

    # AC #2 — names the four canonical arch output buckets
    def test_names_four_output_buckets(self):
        prompt = self._prompt()
        for bucket in ("Summary", "Strengths", "Concerns", "Open questions"):
            self.assertIn(
                bucket, prompt,
                f"arch-review prompt must name the '{bucket}' output bucket "
                f"(031-02 AC #2: summary / strengths / concerns / open questions)",
            )

    # AC #2 — instructs reviewer to apply arch-review skill's concerns
    def test_instructs_reviewer_to_apply_arch_review_skill(self):
        prompt = self._prompt()
        # The prompt must point the reviewer at the `arch-review` SKILL.md
        # so the most-specific installed one wins.
        self.assertRegex(
            prompt,
            r"(?is)arch-review.*SKILL\.md",
            "arch-review prompt must instruct reviewer to apply the most-"
            "specific `arch-review` SKILL.md concerns (031-02 AC #2)",
        )

    # AC #2 — wraps output in canonical envelope
    def test_includes_verdict_envelope(self):
        prompt = self._prompt()
        for marker in ("VERDICT", "REASONING", "SPECIFIC ISSUES",
                       "RECONCILIATION NOTES"):
            self.assertIn(
                marker, prompt,
                f"arch-review prompt must wrap output in the canonical "
                f"envelope; missing marker: {marker} (031-02 AC #2)",
            )
        self.assertRegex(prompt, r"pass\s*\|\s*fail\s*\|\s*needs-changes")

    # AC #2 — read-only directive (inherited from preamble + prohibitions)
    def test_includes_read_only_directive(self):
        prompt = self._prompt()
        self.assertRegex(
            prompt, r"(?i)do not\s+(?:write|modify|edit).+files?|read-only",
        )

    # Spec path appears for context
    def test_includes_spec_path(self):
        prompt = self._prompt()
        self.assertIn(str(self.spec), prompt)

    # Slice label appears for context
    def test_includes_slice_label(self):
        prompt = self._prompt()
        self.assertIn("031-02", prompt)

    # CLI surface — requires at least one deliverable
    def test_arch_review_requires_at_least_one_deliverable(self):
        result = run_review("arch-review", str(self.spec), "031-02")
        self.assertNotEqual(result.returncode, 0)

    # CLI surface — fails cleanly on missing spec
    def test_arch_review_refuses_missing_spec(self):
        missing = Path(self.tmpdir) / "nope.md"
        result = run_review("arch-review", str(missing), "031-02", "x.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    # CLI surface — fails cleanly on unknown slice
    def test_arch_review_refuses_unknown_slice(self):
        result = run_review("arch-review", str(self.spec), "999-99", "x.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())


class ArchReviewSubagentTypeTests(unittest.TestCase):
    """Slice 031-02 AC #3: `review.py subagent-type arch-review` returns the
    same precedence the existing `subagent-type` subcommand uses for
    `jig:reviewer` (plugin) vs. `general-purpose` (running from source)."""

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

    def test_arch_review_returns_reviewer_when_plugin_root_set(self):
        result = self._run(
            "subagent-type", "arch-review",
            env_overrides={"CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        self.assertEqual(result.stdout.strip(), "reviewer")

    def test_arch_review_returns_general_purpose_when_plugin_root_unset(self):
        result = self._run("subagent-type", "arch-review", drop_plugin_root=True)
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        self.assertEqual(result.stdout.strip(), "general-purpose")

    def test_arch_review_returns_general_purpose_when_reviewer_missing(self):
        with tempfile.TemporaryDirectory() as td:
            result = self._run(
                "subagent-type", "arch-review",
                env_overrides={"CLAUDE_PLUGIN_ROOT": td},
            )
            self.assertEqual(result.returncode, 0,
                             msg=f"stderr: {result.stderr}")
            self.assertEqual(result.stdout.strip(), "general-purpose")


class FrameCritiquePromptTests(unittest.TestCase):
    """Slice 064-03 / ADR-0020 AC1: `review.py frame-critique <spec> <slice>
    <deliverable>...` builds a self-contained ADVERSARIAL prompt that:
      - directs the reviewer to find the single highest-risk load-bearing
        assumption and argue why it could be wrong
      - is explicitly NOT a conformance check / AC re-evaluation
      - wraps output in the canonical VERDICT envelope
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-rev-frame-")
        self.spec = Path(self.tmpdir) / "spec.md"
        write_synthetic_spec(self.spec, "064-03 alpha")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _prompt(self, *extra_args: str):
        result = run_review(
            "frame-critique", str(self.spec), "064-03",
            "skills/foo/foo.py", "skills/foo/test_foo.py", *extra_args,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        return result.stdout

    def test_includes_standard_preamble(self):
        prompt = self._prompt()
        self.assertIn("You are an independent reviewer", prompt)
        self.assertIn("seeing this work for the first time", prompt)

    def test_lists_deliverable_paths_verbatim(self):
        prompt = self._prompt()
        self.assertIn("skills/foo/foo.py", prompt)
        self.assertIn("skills/foo/test_foo.py", prompt)

    # AC1 — adversarial: hunt the load-bearing assumption most likely wrong.
    def test_directs_reviewer_to_attack_load_bearing_assumption(self):
        prompt = self._prompt()
        self.assertRegex(
            prompt, r"(?i)load-bearing assumption",
            "frame-critique prompt must direct the reviewer at the "
            "load-bearing assumption (064-03 AC1)",
        )
        self.assertRegex(
            prompt, r"(?i)(most likely.*wrong|likely to be wrong|could be wrong)",
            "frame-critique prompt must ask WHY the assumption could be wrong",
        )

    # AC1 — explicitly NOT a conformance check.
    def test_explicitly_not_a_conformance_check(self):
        prompt = self._prompt()
        self.assertRegex(
            prompt, r"(?i)not\s+a\s+conformance\s+check",
            "frame-critique prompt must say it is NOT a conformance check "
            "(064-03 AC1)",
        )
        # And it must NOT re-evaluate ACs (that's the compliance pass).
        self.assertNotRegex(
            prompt, r"(?i)for\s+each\s+acceptance\s+criterion",
            "frame-critique must not re-evaluate ACs — it hunts the frame",
        )

    # AC1 — distinct from arch-review/pr-review (adversarial framing).
    def test_distinct_adversarial_framing_vs_conformance(self):
        prompt = self._prompt()
        self.assertRegex(
            prompt, r"(?i)adversarial",
            "frame-critique must frame itself as the adversarial pass",
        )
        # It runs pre-implementation: assert it says so.
        self.assertRegex(
            prompt, r"(?i)(no implementation yet|before implementation|"
                    r"pre-implementation)",
            "frame-critique must state it runs before any implementation",
        )

    def test_includes_verdict_envelope(self):
        prompt = self._prompt()
        for marker in ("VERDICT", "REASONING", "SPECIFIC ISSUES"):
            self.assertIn(marker, prompt,
                          f"frame-critique missing envelope marker: {marker}")
        self.assertRegex(prompt, r"pass\s*\|\s*fail\s*\|\s*needs-changes")

    def test_includes_read_only_directive(self):
        prompt = self._prompt()
        self.assertRegex(
            prompt, r"(?i)do not\s+(?:write|modify|edit).+files?|read-only",
        )

    def test_includes_spec_path(self):
        self.assertIn(str(self.spec), self._prompt())

    def test_includes_slice_label(self):
        self.assertIn("064-03", self._prompt())

    # No richer-skill detection wired (no standard external equivalent).
    def test_no_richer_skill_detection(self):
        prompt = self._prompt()
        self.assertNotRegex(
            prompt, r"(?i)richer.*frame-critique.*installed",
            "frame-critique must not detect a richer skill (none exists)",
        )

    def test_frame_critique_requires_at_least_one_deliverable(self):
        result = run_review("frame-critique", str(self.spec), "064-03")
        self.assertNotEqual(result.returncode, 0)

    def test_frame_critique_refuses_missing_spec(self):
        missing = Path(self.tmpdir) / "nope.md"
        result = run_review("frame-critique", str(missing), "064-03", "x.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    def test_frame_critique_refuses_unknown_slice(self):
        result = run_review("frame-critique", str(self.spec), "999-99", "x.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())


class FrameCritiqueEvidenceRoundTripTests(unittest.TestCase):
    """Slice 064-03 AC4: a frame-critique verdict round-trips through
    record-review → file at reviews/slice-NN-frame-critique.md →
    check-reviews --stage READY_FOR_REVIEW clears."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-frame-rt-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _record(self, spec, slice_frag, verdict):
        return subprocess.run(
            [sys.executable, str(REVIEW), "record-review",
             str(spec), slice_frag, "--pass", "frame-critique",
             "--verdict", verdict, "--reviewer", "jig:reviewer",
             "--prompt-source", "review.py frame-critique x",
             "--summary-file", "-"],
            input="## VERDICT\n" + verdict + "\n", capture_output=True,
            text=True, env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )

    def _check(self, spec, slice_frag, stage="READY_FOR_REVIEW"):
        return subprocess.run(
            [sys.executable, str(REVIEW), "check-reviews",
             str(spec), slice_frag, "--stage", stage],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )

    def test_record_lands_at_frame_critique_path(self):
        spec = _make_spec_with_slice(self.tmp / "064-a", "03", "foo",
                                     frame_review=True)
        r = self._record(spec, "0XX-03", "pass")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        f = spec.parent / "reviews" / "slice-03-frame-critique.md"
        self.assertTrue(f.is_file(), f"missing evidence file: {f}")

    def test_check_clears_after_passing_frame_verdict(self):
        spec = _make_spec_with_slice(self.tmp / "064-b", "03", "foo",
                                     frame_review=True)
        self._record(spec, "0XX-03", "pass")
        r = self._check(spec, "0XX-03")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

    def test_check_blocks_when_frame_missing(self):
        spec = _make_spec_with_slice(self.tmp / "064-c", "03", "foo",
                                     frame_review=True)
        r = self._check(spec, "0XX-03")
        self.assertEqual(r.returncode, 2)
        self.assertIn("frame-critique", r.stderr)

    def test_check_clears_when_unflagged(self):
        # No frame_review flag → no required passes → clears freely.
        spec = _make_spec_with_slice(self.tmp / "064-d", "03", "foo",
                                     frame_review=False)
        r = self._check(spec, "0XX-03")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")


class DesignReviewPromptTests(unittest.TestCase):
    """Slice 071-01 AC1: `review.py design-review <spec> <slice>
    <deliverable>...` builds a self-contained, ATTEST-ONLY prompt that:
      - tells the reviewer it is seeing the work for the first time
      - cites the deliverable file paths verbatim
      - directs the reviewer to LOCATE and READ the external design-fidelity
        eval evidence (frozen config threshold + ledger composite)
      - directs the reviewer to ATTEST (do not re-derive): confirm the eval
        actually RAN, is NON-STALE, is HONEST (env_error ≠ pass / ≠ 0.0),
        composite >= the eval's own threshold — and RECORD that verdict
      - explicitly forbids re-running / re-deriving / re-judging the eval
        (servo runs/scores; jig attests — ADR-0022 honesty boundary)
      - wraps output in the canonical VERDICT envelope
      - does NOT detect a richer external skill (no such category exists)
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-rev-design-")
        self.spec = Path(self.tmpdir) / "spec.md"
        write_synthetic_spec(self.spec, "071-01 alpha")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _prompt(self, *extra_args: str):
        result = run_review(
            "design-review", str(self.spec), "071-01",
            "skills/foo/foo.py", "skills/foo/test_foo.py", *extra_args,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        return result.stdout

    def test_includes_standard_preamble(self):
        prompt = self._prompt()
        self.assertIn("You are an independent reviewer", prompt)
        self.assertIn("seeing this work for the first time", prompt)

    def test_lists_deliverable_paths_verbatim(self):
        prompt = self._prompt()
        self.assertIn("skills/foo/foo.py", prompt)
        self.assertIn("skills/foo/test_foo.py", prompt)

    # AC1 — attest-only: explicitly NOT re-derive / re-run / re-judge.
    def test_instructs_not_to_re_derive_the_eval(self):
        prompt = self._prompt()
        self.assertRegex(
            prompt, r"(?i)attest",
            "design-review prompt must frame itself as ATTEST-only (071-01)",
        )
        self.assertRegex(
            prompt, r"(?i)(do not|must not|never)\s+re-?(derive|run|judge|score)",
            "design-review prompt must instruct the reviewer NOT to "
            "re-derive / re-run / re-judge the eval (071-01 / ADR-0022)",
        )

    # AC1 — directs the reviewer at the external eval evidence.
    def test_points_at_external_eval_evidence(self):
        prompt = self._prompt()
        self.assertRegex(
            prompt, r"(?i)design-fidelity",
            "design-review prompt must point at the design-fidelity eval",
        )
        self.assertRegex(
            prompt, r"(?i)(ledger|composite|threshold)",
            "design-review prompt must name the eval's ledger / composite / "
            "threshold evidence (071-01 AC1)",
        )

    # AC1 — honesty: env_error / infra failure is NOT a pass and NOT 0.0.
    def test_honesty_env_error_not_a_pass(self):
        prompt = self._prompt()
        self.assertRegex(
            prompt, r"(?i)env_error",
            "design-review prompt must call out that an env_error / infra "
            "failure is NOT a pass (071-01 AC1 honesty)",
        )

    # AC1 — non-stale: frozen definition unchanged.
    def test_non_stale_frozen_definition(self):
        prompt = self._prompt()
        self.assertRegex(
            prompt, r"(?i)(non-stale|frozen|unchanged)",
            "design-review prompt must require the eval definition be "
            "frozen / non-stale (071-01 AC1)",
        )

    def test_includes_verdict_envelope(self):
        prompt = self._prompt()
        # Distinct, observable attest-only buckets (071-01 AC1): summary /
        # eval-ran / non-stale / threshold-met / verdict.
        for marker in ("VERDICT", "SUMMARY", "EVAL-RAN", "NON-STALE",
                       "THRESHOLD-MET"):
            self.assertIn(marker, prompt,
                          f"design-review missing envelope marker: {marker}")
        self.assertRegex(prompt, r"pass\s*\|\s*fail\s*\|\s*needs-changes")

    def test_includes_read_only_directive(self):
        prompt = self._prompt()
        self.assertRegex(
            prompt, r"(?i)do not\s+(?:write|modify|edit).+files?|read-only",
        )

    def test_does_not_re_evaluate_acceptance_criteria(self):
        prompt = self._prompt()
        self.assertNotRegex(
            prompt, r"(?i)for\s+each\s+acceptance\s+criterion",
            "design-review attests an eval verdict — it does not re-walk ACs",
        )

    def test_includes_spec_path(self):
        self.assertIn(str(self.spec), self._prompt())

    def test_includes_slice_label(self):
        self.assertIn("071-01", self._prompt())

    # AC1 — no richer-skill detection (no standard external category).
    def test_no_richer_skill_detection(self):
        prompt = self._prompt()
        self.assertNotRegex(
            prompt, r"(?i)richer.*design-review.*installed",
            "design-review must not detect a richer skill (none exists) — it "
            "attests jig's own eval evidence",
        )

    def test_design_review_requires_at_least_one_deliverable(self):
        result = run_review("design-review", str(self.spec), "071-01")
        self.assertNotEqual(result.returncode, 0)

    def test_design_review_refuses_missing_spec(self):
        missing = Path(self.tmpdir) / "nope.md"
        result = run_review("design-review", str(missing), "071-01", "x.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    def test_design_review_refuses_unknown_slice(self):
        result = run_review("design-review", str(self.spec), "999-99", "x.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())


class DesignReviewEvidenceRoundTripTests(unittest.TestCase):
    """Slice 071-01 AC4: a design-review verdict round-trips through
    record-review → file at reviews/slice-NN-design-review.md →
    check-reviews --stage REVIEWED clears (and re-validates at DONE)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-design-rt-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _record(self, spec, slice_frag, pass_name, verdict):
        return subprocess.run(
            [sys.executable, str(REVIEW), "record-review",
             str(spec), slice_frag, "--pass", pass_name,
             "--verdict", verdict, "--reviewer", "jig:reviewer",
             "--prompt-source", "review.py design-review x",
             "--summary-file", "-"],
            input="## VERDICT\n" + verdict + "\n", capture_output=True,
            text=True, env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )

    def _check(self, spec, slice_frag, stage="REVIEWED"):
        return subprocess.run(
            [sys.executable, str(REVIEW), "check-reviews",
             str(spec), slice_frag, "--stage", stage],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )

    def test_record_review_accepts_design_review_pass(self):
        # AC2: --pass choices come from _evidence.PASSES, so design-review
        # is accepted automatically.
        spec = _make_spec_with_slice(self.tmp / "070-a", "01", "foo",
                                     design_review=True)
        r = self._record(spec, "0XX-01", "design-review", "pass")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        f = spec.parent / "reviews" / "slice-01-design-review.md"
        self.assertTrue(f.is_file(), f"missing evidence file: {f}")

    def test_check_blocks_when_design_review_missing(self):
        spec = _make_spec_with_slice(self.tmp / "070-b", "01", "foo",
                                     design_review=True)
        self._record(spec, "0XX-01", "compliance", "pass")
        self._record(spec, "0XX-01", "craft", "pass")
        r = self._check(spec, "0XX-01")
        self.assertEqual(r.returncode, 2)
        self.assertIn("design-review", r.stderr)

    def test_check_clears_after_passing_design_verdict(self):
        spec = _make_spec_with_slice(self.tmp / "070-c", "01", "foo",
                                     design_review=True)
        self._record(spec, "0XX-01", "compliance", "pass")
        self._record(spec, "0XX-01", "craft", "pass")
        self._record(spec, "0XX-01", "design-review", "pass")
        r = self._check(spec, "0XX-01")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

    def test_check_clears_when_unflagged(self):
        spec = _make_spec_with_slice(self.tmp / "070-d", "01", "foo",
                                     design_review=False)
        self._record(spec, "0XX-01", "compliance", "pass")
        self._record(spec, "0XX-01", "craft", "pass")
        r = self._check(spec, "0XX-01")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")


class FrameCritiqueAdrCliTests(unittest.TestCase):
    """Slice 064-05: `review.py frame-critique <adr-path>` (no slice) builds an
    ADR frame-critique prompt — the command the accept-gate's refusal message
    advertises. ADRs aren't sliced, so find_slice_label must be skipped."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-frame-adr-cli-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(REVIEW), "frame-critique", *args],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )

    def test_builds_prompt_for_adr_target_without_slice(self):
        adr = self.tmp / "adr-0099-some-decision.md"
        adr.write_text("---\nstatus: Proposed\nframe_review: true\n---\n\n"
                       "# ADR-0099\n\n## Context\n\nx.\n")
        r = self._run(str(adr))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        # Adversarial framing + the ADR label, the ADR listed as deliverable.
        self.assertIn("ADR-0099", r.stdout)
        self.assertIn("frame-critique pass", r.stdout)
        self.assertIn("adr-0099-some-decision.md", r.stdout)

    def test_spec_target_without_slice_errors(self):
        spec = self.tmp / "spec.md"
        spec.write_text("---\nstatus: DRAFT\n---\n\n# Spec X\n\n"
                        "## Slice 001-01 — a\n\n**Goal:** x.\n")
        r = self._run(str(spec))  # no slice fragment, not an ADR
        self.assertEqual(r.returncode, 2)
        self.assertIn("slice", r.stderr.lower())


class CodeHealthPromptTests(unittest.TestCase):
    """Slice 060-05 AC1/AC2: `review.py code-health <spec> <slice>
    <deliverable>... [--summary-file PATH]` builds a self-contained prompt
    that:
      - feeds in the spec + slice + deliverable paths + the health.py summary
      - states the spine ran health.py (the read-only reviewer must NOT)
      - asks for the duplication / complexity / lint judgment a tool can't make
      - tags SPECIFIC ISSUES with [blocker]/[nit]/[strength]
      - wraps output in the standard VERDICT envelope
    """

    SUMMARY = "lint: 3 findings (C901 x2, PLR0913 x1); duplication: 2 clones"

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-rev-ch-")
        self.spec = Path(self.tmpdir) / "spec.md"
        write_synthetic_spec(self.spec, "060-05 alpha")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _prompt(self, summary: str = None):
        sfile = Path(self.tmpdir) / "summary.txt"
        sfile.write_text(self.SUMMARY if summary is None else summary)
        result = run_review(
            "code-health", str(self.spec), "060-05",
            "skills/foo/foo.py", "skills/foo/test_foo.py",
            "--summary-file", str(sfile),
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        return result.stdout

    def test_includes_standard_preamble(self):
        prompt = self._prompt()
        self.assertIn("You are an independent reviewer", prompt)

    def test_includes_spec_path(self):
        prompt = self._prompt()
        self.assertIn(str(self.spec), prompt)

    def test_includes_slice_label(self):
        prompt = self._prompt()
        self.assertIn("060-05", prompt)

    def test_lists_deliverable_paths_verbatim(self):
        prompt = self._prompt()
        self.assertIn("skills/foo/foo.py", prompt)
        self.assertIn("skills/foo/test_foo.py", prompt)

    def test_injects_summary_text(self):
        prompt = self._prompt()
        self.assertIn(self.SUMMARY, prompt)

    def test_states_spine_ran_the_tool(self):
        prompt = self._prompt()
        # AC2: the reviewer must be told health.py was already run and it
        # must NOT run it (read-only, no Bash).
        self.assertRegex(
            prompt,
            r"(?is)health\.py.*(already\s+been\s+run|run by the).*",
            "prompt must state health.py was run by the spine/orchestrator",
        )
        self.assertRegex(
            prompt, r"(?i)(no Bash|must NOT (try to )?run|read-only)",
            "prompt must tell the reviewer not to run health.py itself",
        )

    def test_asks_for_duplication_and_complexity_judgment(self):
        prompt = self._prompt()
        self.assertRegex(prompt, r"(?i)duplication")
        self.assertRegex(prompt, r"(?i)complexity")
        self.assertIn("ADR-0002", prompt)

    def test_tags_blocker_nit_strength(self):
        prompt = self._prompt()
        for tag in ("[blocker]", "[nit]", "[strength]"):
            self.assertIn(tag, prompt,
                          f"prompt must instruct the {tag} tag")

    def test_includes_verdict_envelope(self):
        prompt = self._prompt()
        for marker in ("VERDICT", "REASONING", "SPECIFIC ISSUES",
                       "RECONCILIATION NOTES"):
            self.assertIn(marker, prompt, f"missing envelope marker: {marker}")
        self.assertRegex(prompt, r"pass\s*\|\s*fail\s*\|\s*needs-changes")

    def test_does_not_re_evaluate_acceptance_criteria(self):
        prompt = self._prompt()
        self.assertNotRegex(
            prompt, r"(?i)for\s+each\s+acceptance\s+criterion",
            "code-health prompt must not re-evaluate ACs",
        )

    def test_summary_read_from_stdin_when_requested(self):
        # Bug 017 amendment to slice 060-05: stdin injection still works, but
        # it must be asked for with `--summary-file -`. The old implicit
        # fallback read stdin whenever it was not a terminal, which blocked
        # forever on a pipe nobody closed.
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        result = subprocess.run(
            [sys.executable, str(REVIEW), "code-health", str(self.spec),
             "060-05", "skills/foo/foo.py", "--summary-file", "-"],
            input="STDIN-SUMMARY-SENTINEL\n",
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("STDIN-SUMMARY-SENTINEL", result.stdout)

    def test_requires_at_least_one_deliverable(self):
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        result = subprocess.run(
            [sys.executable, str(REVIEW), "code-health", str(self.spec),
             "060-05"],
            input="", capture_output=True, text=True, env=env,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_refuses_missing_spec(self):
        missing = Path(self.tmpdir) / "nope.md"
        result = run_review("code-health", str(missing), "060-05", "x.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    def test_empty_summary_degrades_gracefully(self):
        # AC2 graceful-degrade: no summary provided (no --summary-file at all;
        # stdin is not consulted since bug 017) → the prompt still builds
        # (exit 0) and tells the reviewer to judge on the deliverables, rather
        # than emitting an empty/blank summary block.
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        result = subprocess.run(
            [sys.executable, str(REVIEW), "code-health", str(self.spec),
             "060-05", "skills/foo/foo.py"],
            input="", capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("no health.py summary", result.stdout.lower())

    def test_missing_summary_file_errors(self):
        # --summary-file pointing at a nonexistent path → clean exit-2
        # ReviewError, not a traceback.
        missing = Path(self.tmpdir) / "no-such-summary.txt"
        result = run_review(
            "code-health", str(self.spec), "060-05", "skills/foo/foo.py",
            "--summary-file", str(missing),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("summary file not found", result.stderr.lower())
        self.assertNotIn("traceback", result.stderr.lower())


class CodeHealthSubagentTypeTests(unittest.TestCase):
    """Slice 060-05: `review.py subagent-type code-health` returns the same
    reviewer/general-purpose precedence as the other modes."""

    def _run(self, *args, env_overrides=None, drop_plugin_root=False):
        env = os.environ.copy()
        if drop_plugin_root:
            env.pop("CLAUDE_PLUGIN_ROOT", None)
        if env_overrides:
            env.update(env_overrides)
        return subprocess.run(
            [sys.executable, str(REVIEW), *args],
            capture_output=True, text=True, env=env,
        )

    def test_returns_reviewer_when_plugin_root_set(self):
        result = self._run(
            "subagent-type", "code-health",
            env_overrides={"CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        self.assertEqual(result.stdout.strip(), "reviewer")

    def test_returns_general_purpose_when_plugin_root_unset(self):
        result = self._run("subagent-type", "code-health", drop_plugin_root=True)
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        self.assertEqual(result.stdout.strip(), "general-purpose")


class SpecWorkflowSkillThreePassTests(unittest.TestCase):
    """Slice 031-01 AC #3 + AC #6: `skills/spec-workflow/SKILL.md`
    § "After implementation" documents the three-pass flow:
      1. Compliance (jig:independent-review) — always.
      2. Craft (pr-review) — always.
      3. (Slice 031-02 adds arch — out of scope here.)

    The SKILL.md prose must:
      - mention BOTH the compliance and craft passes under
        "After implementation"
      - name the order (compliance → craft)
      - name the block rule (fail blocks; needs-changes blocks for
        compliance, becomes a reconciliation-log entry for craft)
    """

    SKILL_MD = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"

    def setUp(self):
        self.skill = self.SKILL_MD.read_text()

    def _after_implementation_section(self) -> str:
        """Slice the SKILL.md to just the `### After implementation`
        section (up to the next `### ` or `## ` heading)."""
        m = re.search(
            r"(?m)^###\s+After\s+implementation\s*$", self.skill,
        )
        self.assertIsNotNone(m, "SKILL.md must have '### After implementation'")
        rest = self.skill[m.end():]
        nxt = re.search(r"(?m)^(?:###|##)\s", rest)
        return rest[: nxt.start()] if nxt else rest

    def test_after_implementation_mentions_both_passes(self):
        section = self._after_implementation_section()
        section_lower = section.lower()
        # Compliance pass
        self.assertIn(
            "independent-review", section_lower,
            "After implementation must name the compliance pass via "
            "jig:independent-review (031-01 AC #3)",
        )
        # Craft pass
        self.assertIn(
            "pr-review", section_lower,
            "After implementation must name the craft pass via "
            "pr-review (031-01 AC #3)",
        )

    def test_after_implementation_names_pass_order(self):
        section = self._after_implementation_section()
        # The order must be discoverable: compliance must appear before craft
        compliance_pos = section.lower().find("independent-review")
        craft_pos = section.lower().find("pr-review")
        self.assertGreater(compliance_pos, -1)
        self.assertGreater(craft_pos, -1)
        self.assertLess(
            compliance_pos, craft_pos,
            "SKILL.md must document compliance → craft order "
            "(031-01 AC #3: compliance first, then craft)",
        )

    def test_after_implementation_names_block_rule(self):
        section = self._after_implementation_section()
        # The block rule: any `fail` blocks; `needs-changes` is split —
        # blocks for compliance, becomes a reconciliation-log entry for
        # craft. Look for "fail" + "block" in the prose.
        self.assertRegex(
            section,
            r"(?is)fail.*block|block.*fail",
            "After implementation must name the block rule "
            "(any `fail` blocks REVIEWED transition) (031-01 AC #3)",
        )

    # Slice 031-02 AC #5 + AC #6 — conditional arch pass documented
    def test_after_implementation_documents_conditional_arch_pass(self):
        section = self._after_implementation_section()
        section_lower = section.lower()
        # The arch pass must appear under "After implementation"
        self.assertIn(
            "arch-review", section_lower,
            "After implementation must name the conditional arch pass "
            "via arch-review (031-02 AC #5)",
        )
        # And it must be gated on `arch_review:` frontmatter
        self.assertIn(
            "arch_review", section,
            "After implementation must name the `arch_review:` "
            "frontmatter flag that gates the arch pass (031-02 AC #5)",
        )

    def test_arch_pass_appears_after_craft_pass(self):
        section = self._after_implementation_section()
        # Order: compliance → craft → arch
        craft_pos = section.lower().find("pr-review")
        arch_pos = section.lower().find("arch-review")
        self.assertGreater(craft_pos, -1)
        self.assertGreater(arch_pos, -1)
        self.assertLess(
            craft_pos, arch_pos,
            "SKILL.md must document craft → arch order "
            "(031-02 AC #5: arch pass runs after craft pass)",
        )


# ---------------------------------------------------------------------------
# Slice 043-04 — test-quality snapshot injection into implementation prompt
# ---------------------------------------------------------------------------


TEST_QUALITY_HEADING = "## Test-quality snapshot"
TEST_QUALITY_UNAVAIL_PREFIX = "_Test-quality snapshot unavailable"


def _run_git(cwd, *args):
    return subprocess.run(
        ["git", *args],
        cwd=cwd, capture_output=True, text=True, check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


def _make_repo_with_diff(root: Path) -> None:
    """Initialize a tmp git repo with a `main` branch, an initial commit,
    a feature branch with an added test file. The test file is committed
    so `git diff <merge-base>...HEAD` returns the diff."""
    _run_git(root, "init", "-q", "-b", "main")
    _run_git(root, "config", "user.email", "test@example.com")
    _run_git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("baseline\n")
    _run_git(root, "add", "README.md")
    _run_git(root, "commit", "-q", "-m", "init")
    _run_git(root, "checkout", "-q", "-b", "feature")
    tests_dir = root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_alpha.py").write_text(
        "def test_alpha():\n    assert True\n"
    )
    _run_git(root, "add", "tests/test_alpha.py")
    _run_git(root, "commit", "-q", "-m", "add tests")


def _make_repo_no_diff(root: Path) -> None:
    """Init a repo with a single commit on `main` and HEAD pointed at it
    — `git diff main...HEAD` is empty."""
    _run_git(root, "init", "-q", "-b", "main")
    _run_git(root, "config", "user.email", "test@example.com")
    _run_git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("baseline\n")
    _run_git(root, "add", "README.md")
    _run_git(root, "commit", "-q", "-m", "init")


class TestQualitySnapshotHelperTests(unittest.TestCase):
    """Slice 043-04 AC #1 + #2 + #3: `_test_quality_snapshot_block(spec_path)`
    helper.

    - Happy path: tmp git repo with a slice-shaped diff → returns a block
      with the `## Test-quality snapshot (deterministic)` heading and the
      cite-or-stay-silent sentences.
    - Empty-diff path: tmp git repo with no diff against main → returns the
      `_Test-quality snapshot unavailable: <reason>._` single-line fallback.
    - Missing-merge-base path: tmp dir with no git → fallback single-line.
    """

    def setUp(self):
        self._tmpdirs: list[Path] = []

    def tearDown(self):
        import shutil
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _import_review_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "review_module_043", REVIEW,
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def test_helper_returns_block_when_diff_present(self):
        module = self._import_review_module()
        root = Path(tempfile.mkdtemp(prefix="jig-rev-tq-"))
        self._tmpdirs.append(root)
        _make_repo_with_diff(root)
        # Place the spec file inside the repo so the helper's CWD resolves.
        spec_dir = root / "docs" / "specs" / "myspec"
        spec_dir.mkdir(parents=True)
        spec = spec_dir / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")
        block = module._test_quality_snapshot_block(spec)
        self.assertIn(TEST_QUALITY_HEADING, block)
        # YAML fence + the schema marker should both appear.
        self.assertIn("```yaml", block)
        self.assertIn("test-quality-snapshot:", block)
        # Cite-or-stay-silent sentences (AC #2)
        self.assertIn("cite the fired signal", block)
        self.assertIn(
            "absence of a signal is evidence of nothing-to-flag", block,
        )

    def test_helper_fallback_when_empty_diff(self):
        module = self._import_review_module()
        root = Path(tempfile.mkdtemp(prefix="jig-rev-tq-empty-"))
        self._tmpdirs.append(root)
        _make_repo_no_diff(root)
        spec_dir = root / "docs" / "specs" / "myspec"
        spec_dir.mkdir(parents=True)
        spec = spec_dir / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")
        block = module._test_quality_snapshot_block(spec)
        self.assertIn(TEST_QUALITY_UNAVAIL_PREFIX, block)
        # The unavailable-line should NOT have a YAML fence.
        self.assertNotIn("```yaml", block)

    def test_helper_fallback_when_no_git_repo(self):
        module = self._import_review_module()
        root = Path(tempfile.mkdtemp(prefix="jig-rev-tq-nogit-"))
        self._tmpdirs.append(root)
        # No git init. Just a spec.
        spec = root / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")
        block = module._test_quality_snapshot_block(spec)
        self.assertIn(TEST_QUALITY_UNAVAIL_PREFIX, block)
        self.assertNotIn("```yaml", block)

    def test_helper_never_raises(self):
        """AC #3: prompt builder must not crash on the snapshot helper.
        Pass a non-existent path; helper must return a string."""
        module = self._import_review_module()
        block = module._test_quality_snapshot_block(
            Path("/no/such/path/spec.md"),
        )
        self.assertIsInstance(block, str)
        self.assertIn(TEST_QUALITY_UNAVAIL_PREFIX, block)

    def test_helper_fallback_when_applicable_false(self):
        """AC #3: a docs-only diff drives quality.py to emit
        `applicable: false` with a docs-only reason. The helper must
        surface that reason inline in the unavailable line.

        Closes the AC3 coverage gap flagged at review (the
        `applicable: false` branch was previously untested)."""
        module = self._import_review_module()
        root = Path(tempfile.mkdtemp(prefix="jig-rev-tq-docs-"))
        self._tmpdirs.append(root)
        # Repo with a docs-only diff between main and HEAD.
        _run_git(root, "init", "-q", "-b", "main")
        _run_git(root, "config", "user.email", "test@example.com")
        _run_git(root, "config", "user.name", "Test")
        (root / "README.md").write_text("baseline\n")
        _run_git(root, "add", "README.md")
        _run_git(root, "commit", "-q", "-m", "init")
        _run_git(root, "checkout", "-q", "-b", "feature")
        (root / "README.md").write_text("baseline\nupdated docs\n")
        _run_git(root, "add", "README.md")
        _run_git(root, "commit", "-q", "-m", "docs tweak")
        spec_dir = root / "docs" / "specs" / "myspec"
        spec_dir.mkdir(parents=True)
        spec = spec_dir / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")
        block = module._test_quality_snapshot_block(spec)
        self.assertIn(TEST_QUALITY_UNAVAIL_PREFIX, block)
        self.assertIn("not applicable", block)
        # Reason from the YAML snapshot (docs-only-or-no-test-or-code-changes)
        # is surfaced inline so the reviewer knows why.
        self.assertIn("docs-only", block.lower())
        self.assertNotIn("```yaml", block)

    def test_helper_fallback_when_quality_py_exits_nonzero(self):
        """AC #3: simulate quality.py exiting non-zero. The git plumbing
        runs normally; only the quality.py subprocess returns rc != 0.
        Verifies the `quality.py exited non-zero` fallback message.

        Closes the AC3 coverage gap flagged at review."""
        from types import SimpleNamespace
        from unittest import mock
        module = self._import_review_module()
        root = Path(tempfile.mkdtemp(prefix="jig-rev-tq-nzexit-"))
        self._tmpdirs.append(root)
        _make_repo_with_diff(root)
        spec_dir = root / "docs" / "specs" / "myspec"
        spec_dir.mkdir(parents=True)
        spec = spec_dir / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")

        real_run = module.subprocess.run

        def fake_run(cmd, *args, **kwargs):
            # Detect the quality.py call (third subprocess.run in the
            # helper) and return a non-zero exit; pass git calls through.
            if isinstance(cmd, (list, tuple)) and any(
                "quality.py" in str(c) for c in cmd
            ):
                return SimpleNamespace(returncode=2, stdout="", stderr="boom\n")
            return real_run(cmd, *args, **kwargs)

        with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
            block = module._test_quality_snapshot_block(spec)
        self.assertIn(TEST_QUALITY_UNAVAIL_PREFIX, block)
        self.assertIn("exited non-zero", block)
        self.assertNotIn("```yaml", block)


class TestQualitySnapshotPromptPlacementTests(unittest.TestCase):
    """Slice 043-04 AC #1 + #4: the snapshot block lands in the
    implementation prompt only.

    Calls the prompt builders in-process so the helper's git-shell-out
    happens with the test's cwd (which may or may not be a git repo).
    The fallback path covers the no-diff / no-git cases — the assertion
    is on the heading or fallback, not on a fully-populated YAML."""

    def setUp(self):
        self._tmpdirs: list[Path] = []

    def tearDown(self):
        import shutil
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _import_review_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "review_module_043_p", REVIEW,
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def _make_repo_with_spec(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="jig-rev-tq-prompt-"))
        self._tmpdirs.append(root)
        _make_repo_with_diff(root)
        spec_dir = root / "docs" / "specs" / "myspec"
        spec_dir.mkdir(parents=True)
        spec = spec_dir / "spec.md"
        write_synthetic_spec(spec, "099-01 alpha")
        return spec

    def test_impl_prompt_includes_snapshot_heading(self):
        module = self._import_review_module()
        spec = self._make_repo_with_spec()
        prompt = module.build_implementation_prompt(spec, "099-01 alpha", ["x.py"])
        # Either the heading (happy path) OR the fallback line — both are
        # acceptable evidence the snapshot wiring fired.
        self.assertTrue(
            TEST_QUALITY_HEADING in prompt
            or TEST_QUALITY_UNAVAIL_PREFIX in prompt,
            "implementation prompt must include the snapshot block "
            "(heading or fallback line) — AC #1",
        )
        # If the heading is present, the YAML fence must be too.
        if TEST_QUALITY_HEADING in prompt:
            self.assertIn("```yaml", prompt)

    def test_snapshot_lands_before_principles_check(self):
        """AC #1: 'between the `## Evaluate` block and the
        `_principles_check_block`.' The snapshot heading (or fallback)
        must precede the Principles-check bullet."""
        module = self._import_review_module()
        spec = self._make_repo_with_spec()
        prompt = module.build_implementation_prompt(spec, "099-01 alpha", ["x.py"])
        principles_pos = prompt.find("Principles check")
        self.assertGreater(principles_pos, -1, "principles block missing")
        # Find the snapshot marker — heading or fallback
        snap_pos = prompt.find(TEST_QUALITY_HEADING)
        if snap_pos < 0:
            snap_pos = prompt.find(TEST_QUALITY_UNAVAIL_PREFIX)
        self.assertGreater(snap_pos, -1, "snapshot marker missing")
        self.assertLess(
            snap_pos, principles_pos,
            "snapshot block must land BEFORE the principles-check "
            "block (AC #1: between Evaluate and principles)",
        )

    def test_pr_review_prompt_excludes_snapshot(self):
        """AC #4: snapshot must NOT appear in the pr-review prompt."""
        module = self._import_review_module()
        spec = self._make_repo_with_spec()
        prompt = module.build_pr_review_prompt(spec, "099-01 alpha", ["x.py"])
        self.assertNotIn(TEST_QUALITY_HEADING, prompt)
        self.assertNotIn(TEST_QUALITY_UNAVAIL_PREFIX, prompt)

    def test_arch_review_prompt_excludes_snapshot(self):
        """AC #4: snapshot must NOT appear in the arch-review prompt."""
        module = self._import_review_module()
        spec = self._make_repo_with_spec()
        prompt = module.build_arch_review_prompt(spec, "099-01 alpha", ["x.py"])
        self.assertNotIn(TEST_QUALITY_HEADING, prompt)
        self.assertNotIn(TEST_QUALITY_UNAVAIL_PREFIX, prompt)

    def test_reconciliation_prompt_excludes_snapshot(self):
        """AC #4: snapshot must NOT appear in the reconciliation prompt."""
        module = self._import_review_module()
        spec = self._make_repo_with_spec()
        prompt = module.build_reconciliation_prompt(spec, "099-01 alpha")
        self.assertNotIn(TEST_QUALITY_HEADING, prompt)
        self.assertNotIn(TEST_QUALITY_UNAVAIL_PREFIX, prompt)


# ---------------------------------------------------------------------------
# Slice 043-04 AC #5 + AC #6: SKILL.md + workflow.md mentions
# ---------------------------------------------------------------------------


class TddLoopSkillMentionsQualityTests(unittest.TestCase):
    """AC #5: `skills/tdd-loop/SKILL.md` mentions quality.py as a sibling
    helper and points at independent-review for the snapshot wiring."""

    TDD_SKILL_MD = REPO_ROOT / "skills" / "tdd-loop" / "SKILL.md"

    def setUp(self):
        self.skill = self.TDD_SKILL_MD.read_text()

    def test_mentions_quality_py(self):
        self.assertIn("quality.py", self.skill,
                      "tdd-loop SKILL.md must mention `quality.py`")

    def test_points_at_independent_review_for_snapshot(self):
        self.assertRegex(
            self.skill,
            r"(?is)independent-review",
            "tdd-loop SKILL.md must point at `independent-review` so "
            "readers can follow the snapshot wiring (AC #5)",
        )


class WorkflowMdMentionsSnapshotTests(unittest.TestCase):
    """AC #6: `docs/workflow.md` step 4 / post-implementation review
    section mentions the deterministic test-quality snapshot."""

    WORKFLOW_MD = REPO_ROOT / "docs" / "workflow.md"

    def setUp(self):
        self.text = self.WORKFLOW_MD.read_text()

    def test_mentions_test_quality_snapshot(self):
        self.assertRegex(
            self.text,
            r"(?i)test-quality\s+snapshot|deterministic\s+test-quality",
            "workflow.md must mention the deterministic test-quality "
            "snapshot in the post-implementation review section (AC #6)",
        )


# ---------------------------------------------------------------------------
# Slice 045-02 — review-artifact-recorder CLI (record-review / check-reviews)
# ---------------------------------------------------------------------------


def _make_spec_with_slice(spec_dir: Path, slice_no: str, slug: str,
                          *, arch_review: bool = False,
                          frame_review: bool = False,
                          design_review: bool = False) -> Path:
    """Create `spec_dir/spec.md` + a sibling `slice-NN-<slug>.md` file in
    a temp dir (NOT the real docs/specs/ tree). Returns the spec.md path."""
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec = spec_dir / "spec.md"
    spec.write_text(
        "---\nstatus: IN_PROGRESS\n---\n\n# Spec\n\n## Overview\n\nStuff.\n"
    )
    fm = "---\nstatus: IN_PROGRESS\ndependencies: []\n"
    if arch_review:
        fm += "arch_review: true\n"
    if frame_review:
        fm += "frame_review: true\n"
    if design_review:
        fm += "design_review: true\n"
    fm += "---\n"
    (spec_dir / f"slice-{slice_no}-{slug}.md").write_text(
        f"{fm}\n## Slice 0XX-{slice_no} — {slug}\n\n**Goal:** placeholder.\n"
    )
    return spec


class RecordReviewTests(unittest.TestCase):
    """Slice 045-02 AC #1: `review.py record-review` writes a verdict file
    for a (slice, pass) with all ADR-required frontmatter fields, plus the
    freeform summary body."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-rec-"))
        self.spec = _make_spec_with_slice(self.tmp / "045-x", "02", "foo")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _record(self, *args, summary="## VERDICT\npass\n\n## REASONING\nok.\n"):
        return subprocess.run(
            [sys.executable, str(REVIEW), "record-review", *args,
             "--summary-file", "-"],
            input=summary, capture_output=True, text=True,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )

    def _evidence_file(self, pass_name: str) -> Path:
        return self.spec.parent / "reviews" / f"slice-02-{pass_name}.md"

    def test_writes_evidence_file_at_canonical_path(self):
        r = self._record(str(self.spec), "0XX-02",
                         "--pass", "compliance",
                         "--verdict", "pass",
                         "--reviewer", "jig:reviewer",
                         "--prompt-source", "review.py implementation x")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        f = self._evidence_file("compliance")
        self.assertTrue(f.is_file(), f"missing evidence file: {f}")

    def test_evidence_has_required_frontmatter_fields(self):
        self._record(str(self.spec), "0XX-02",
                     "--pass", "compliance",
                     "--verdict", "pass",
                     "--reviewer", "jig:reviewer",
                     "--prompt-source", "review.py implementation x")
        text = self._evidence_file("compliance").read_text()
        from _common.parsing import parse_frontmatter
        fields, _ = parse_frontmatter(text)
        for key in ("slice", "pass", "verdict", "reviewer",
                    "reviewed_at", "prompt_source"):
            self.assertIn(key, fields,
                          f"frontmatter must carry '{key}' (ADR §2)")
        self.assertEqual(fields["pass"], "compliance")
        self.assertEqual(fields["verdict"], "pass")
        self.assertEqual(fields["reviewer"], "jig:reviewer")

    def test_reviewed_at_is_iso8601(self):
        self._record(str(self.spec), "0XX-02",
                     "--pass", "craft", "--verdict", "pass",
                     "--reviewer", "pr-review",
                     "--prompt-source", "review.py pr-review x")
        text = self._evidence_file("craft").read_text()
        from _common.parsing import parse_frontmatter
        fields, _ = parse_frontmatter(text)
        # ISO-8601 UTC: YYYY-MM-DDTHH:MM:SS(.ffffff)?Z or +00:00
        self.assertRegex(
            fields["reviewed_at"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
            f"reviewed_at must be ISO-8601; got {fields['reviewed_at']!r}",
        )

    def test_summary_body_is_preserved(self):
        self._record(str(self.spec), "0XX-02",
                     "--pass", "compliance", "--verdict", "pass",
                     "--reviewer", "jig:reviewer",
                     "--prompt-source", "x",
                     summary="## VERDICT\npass\n\n## REASONING\nclean impl.\n")
        text = self._evidence_file("compliance").read_text()
        self.assertIn("clean impl.", text)
        self.assertIn("## REASONING", text)

    def test_accepts_summary_from_file(self):
        summary_file = self.tmp / "summary.md"
        summary_file.write_text("## VERDICT\nfail\n\n## REASONING\nbug.\n")
        r = subprocess.run(
            [sys.executable, str(REVIEW), "record-review",
             str(self.spec), "0XX-02",
             "--pass", "compliance", "--verdict", "fail",
             "--reviewer", "jig:reviewer", "--prompt-source", "x",
             "--summary-file", str(summary_file)],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        text = self._evidence_file("compliance").read_text()
        self.assertIn("bug.", text)

    def test_re_record_overwrites_in_place(self):
        """ADR §4: re-recording the same (slice, pass) overwrites in place
        (git history is the audit trail; no append). The file must contain
        ONLY the latest verdict."""
        self._record(str(self.spec), "0XX-02",
                     "--pass", "compliance", "--verdict", "needs-changes",
                     "--reviewer", "jig:reviewer", "--prompt-source", "x",
                     summary="## VERDICT\nneeds-changes\n")
        self._record(str(self.spec), "0XX-02",
                     "--pass", "compliance", "--verdict", "pass",
                     "--reviewer", "jig:reviewer", "--prompt-source", "x",
                     summary="## VERDICT\npass\n")
        text = self._evidence_file("compliance").read_text()
        from _common.parsing import parse_frontmatter
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["verdict"], "pass",
                         "latest verdict must win on overwrite")
        # The superseded verdict must NOT be appended/duplicated.
        self.assertEqual(text.count("---\n"), 2,
                         "exactly one frontmatter block (no append)")
        self.assertNotIn("needs-changes", text,
                         "prior verdict must not survive (overwrite, "
                         "not append — ADR §4)")

    def test_re_record_is_stable_round_trip(self):
        """AC #3 stability: recording the same inputs twice produces
        byte-identical files modulo the timestamp. We strip reviewed_at
        and compare the rest."""
        def normalized():
            self._record(str(self.spec), "0XX-02",
                         "--pass", "craft", "--verdict", "pass",
                         "--reviewer", "pr-review", "--prompt-source", "p",
                         summary="## VERDICT\npass\n")
            text = self._evidence_file("craft").read_text()
            return re.sub(r"reviewed_at: .*\n", "", text)
        first = normalized()
        second = normalized()
        self.assertEqual(first, second,
                         "record→record must be stable modulo timestamp")

    def test_rejects_unknown_pass(self):
        r = self._record(str(self.spec), "0XX-02",
                         "--pass", "smoke", "--verdict", "pass",
                         "--reviewer", "x", "--prompt-source", "x")
        self.assertEqual(r.returncode, 2,
                         f"unknown pass must exit 2; stderr={r.stderr}")

    def test_rejects_unknown_verdict(self):
        r = self._record(str(self.spec), "0XX-02",
                         "--pass", "compliance", "--verdict", "approved",
                         "--reviewer", "x", "--prompt-source", "x")
        self.assertEqual(r.returncode, 2,
                         f"unknown verdict must exit 2; stderr={r.stderr}")

    def test_rejects_invalid_slice_target(self):
        r = self._record(str(self.spec), "999-99",
                         "--pass", "compliance", "--verdict", "pass",
                         "--reviewer", "x", "--prompt-source", "x")
        self.assertEqual(r.returncode, 2,
                         f"invalid slice must exit 2; stderr={r.stderr}")

    def test_rejects_missing_spec(self):
        missing = self.tmp / "nope" / "spec.md"
        r = self._record(str(missing), "0XX-02",
                         "--pass", "compliance", "--verdict", "pass",
                         "--reviewer", "x", "--prompt-source", "x")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not found", r.stderr.lower())


class CheckReviewsTests(unittest.TestCase):
    """Slice 045-02 AC #2: `review.py check-reviews` validates the evidence
    set for a target slice and exits non-zero with actionable diagnostics
    for every edge case. Exit 0 when the required set clears."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-chk-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _spec(self, slug, slice_no, *, arch_review=False):
        return _make_spec_with_slice(self.tmp / slug, slice_no, "foo",
                                     arch_review=arch_review)

    def _record(self, spec, slice_frag, pass_name, verdict,
                summary="## VERDICT\nx\n"):
        return subprocess.run(
            [sys.executable, str(REVIEW), "record-review",
             str(spec), slice_frag, "--pass", pass_name,
             "--verdict", verdict, "--reviewer", "jig:reviewer",
             "--prompt-source", "x", "--summary-file", "-"],
            input=summary, capture_output=True, text=True,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )

    def _check(self, spec, slice_frag, stage="REVIEWED"):
        return subprocess.run(
            [sys.executable, str(REVIEW), "check-reviews",
             str(spec), slice_frag, "--stage", stage],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )

    # ---- clean case ----

    def test_clears_when_compliance_and_craft_pass(self):
        spec = self._spec("045-a", "02")
        self._record(spec, "0XX-02", "compliance", "pass")
        self._record(spec, "0XX-02", "craft", "pass")
        r = self._check(spec, "0XX-02")
        self.assertEqual(r.returncode, 0,
                         f"expected clean exit 0; stderr={r.stderr}\n"
                         f"stdout={r.stdout}")

    # ---- missing file ----

    def test_missing_file_exits_nonzero_with_diag(self):
        spec = self._spec("045-b", "02")
        self._record(spec, "0XX-02", "compliance", "pass")
        # craft missing
        r = self._check(spec, "0XX-02")
        self.assertEqual(r.returncode, 2)
        out = (r.stdout + r.stderr).lower()
        self.assertIn("craft", out, "diagnostic must name the missing pass")

    # ---- malformed frontmatter ----

    def test_malformed_frontmatter_exits_nonzero(self):
        spec = self._spec("045-c", "02")
        self._record(spec, "0XX-02", "compliance", "pass")
        self._record(spec, "0XX-02", "craft", "pass")
        # Corrupt the compliance file's frontmatter.
        f = spec.parent / "reviews" / "slice-02-compliance.md"
        f.write_text("not even close to frontmatter\n")
        r = self._check(spec, "0XX-02")
        self.assertEqual(r.returncode, 2)

    # ---- unknown pass name ----

    def test_unknown_pass_name_in_file_exits_nonzero(self):
        spec = self._spec("045-d", "02")
        self._record(spec, "0XX-02", "compliance", "pass")
        self._record(spec, "0XX-02", "craft", "pass")
        f = spec.parent / "reviews" / "slice-02-compliance.md"
        f.write_text(f.read_text().replace("pass: compliance",
                                           "pass: smoke-test"))
        r = self._check(spec, "0XX-02")
        self.assertEqual(r.returncode, 2)
        self.assertIn("pass", (r.stdout + r.stderr).lower())

    # ---- unknown verdict ----

    def test_unknown_verdict_in_file_exits_nonzero(self):
        spec = self._spec("045-e", "02")
        self._record(spec, "0XX-02", "compliance", "pass")
        self._record(spec, "0XX-02", "craft", "pass")
        f = spec.parent / "reviews" / "slice-02-compliance.md"
        f.write_text(f.read_text().replace("verdict: pass",
                                           "verdict: approved"))
        r = self._check(spec, "0XX-02")
        self.assertEqual(r.returncode, 2)
        self.assertIn("verdict", (r.stdout + r.stderr).lower())

    # ---- superseded-only / non-clearing verdict ----

    def test_superseded_only_fail_verdict_exits_nonzero(self):
        """A `fail` not overwritten by a later `pass` blocks (ADR §3/§4 —
        the superseded-only half of AC2's 'stale/superseded-only')."""
        spec = self._spec("045-f", "02")
        self._record(spec, "0XX-02", "compliance", "fail")
        self._record(spec, "0XX-02", "craft", "pass")
        r = self._check(spec, "0XX-02")
        self.assertEqual(r.returncode, 2)
        out = (r.stdout + r.stderr).lower()
        self.assertIn("compliance", out)
        self.assertIn("fail", out)

    def test_needs_changes_only_verdict_exits_nonzero(self):
        spec = self._spec("045-g", "02")
        self._record(spec, "0XX-02", "compliance", "needs-changes")
        self._record(spec, "0XX-02", "craft", "pass")
        r = self._check(spec, "0XX-02")
        self.assertEqual(r.returncode, 2)
        self.assertIn("needs-changes", (r.stdout + r.stderr).lower())

    # ---- invalid slice target ----

    def test_invalid_slice_target_exits_nonzero(self):
        spec = self._spec("045-h", "02")
        r = self._check(spec, "999-99")
        self.assertEqual(r.returncode, 2)

    def test_missing_spec_exits_nonzero(self):
        r = self._check(self.tmp / "nope" / "spec.md", "0XX-02")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not found", r.stderr.lower())

    # ---- arch-gated behavior ----

    def test_arch_required_but_missing_exits_nonzero(self):
        spec = self._spec("045-i", "02", arch_review=True)
        self._record(spec, "0XX-02", "compliance", "pass")
        self._record(spec, "0XX-02", "craft", "pass")
        r = self._check(spec, "0XX-02")
        self.assertEqual(r.returncode, 2)
        self.assertIn("arch", (r.stdout + r.stderr).lower())

    def test_arch_present_when_flagged_clears(self):
        spec = self._spec("045-j", "02", arch_review=True)
        self._record(spec, "0XX-02", "compliance", "pass")
        self._record(spec, "0XX-02", "craft", "pass")
        self._record(spec, "0XX-02", "arch", "pass")
        r = self._check(spec, "0XX-02")
        self.assertEqual(r.returncode, 0,
                         f"stderr={r.stderr}\nstdout={r.stdout}")

    # ---- reconciliation stage ----

    def test_reconciled_stage_requires_reconciliation_pass(self):
        spec = self._spec("045-k", "02")
        r = self._check(spec, "0XX-02", stage="RECONCILED")
        self.assertEqual(r.returncode, 2)
        self.assertIn("reconciliation", (r.stdout + r.stderr).lower())

    def test_reconciled_stage_clears_with_reconciliation_pass(self):
        spec = self._spec("045-l", "02")
        self._record(spec, "0XX-02", "reconciliation", "pass")
        r = self._check(spec, "0XX-02", stage="RECONCILED")
        self.assertEqual(r.returncode, 0,
                         f"stderr={r.stderr}\nstdout={r.stdout}")


class ReviewEvidenceSkillDocTests(unittest.TestCase):
    """Slice 045-02 AC #1/#2: the new subcommands are documented in
    `skills/independent-review/SKILL.md` ('a documented command')."""

    def setUp(self):
        self.skill = SKILL_MD.read_text()

    def test_skill_documents_record_review(self):
        self.assertIn("record-review", self.skill,
                      "SKILL.md must document the record-review subcommand")

    def test_skill_documents_check_reviews(self):
        self.assertIn("check-reviews", self.skill,
                      "SKILL.md must document the check-reviews subcommand")


class ReviewEvidenceScaffoldParityTests(unittest.TestCase):
    """Slice 045-02 AC #4: a scaffolded project receives the recorder/
    validator path. The shared schema module rides `_common/`, which
    `scaffold.py`'s `_copy_skills_and_agents` copies unprefixed. Verify
    the module is included in the scaffold-copied set rather than adding
    new copy plumbing (per the slice brief)."""

    def test_review_evidence_module_exists_in_common(self):
        mod = REPO_ROOT / "skills" / "_common" / "review_evidence.py"
        self.assertTrue(mod.is_file(),
                        "review_evidence.py must live in skills/_common/ so "
                        "it rides the existing scaffold copy of _common/")

    def test_scaffold_copies_review_evidence_module(self):
        """End-to-end: scaffold into a temp dir, assert review_evidence.py
        lands at .claude/skills/_common/ (the path the unprefixed-copy
        logic produces) and its test file is excluded."""
        import importlib.util
        scaffold_py = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"
        spec = importlib.util.spec_from_file_location("scaffold_045", scaffold_py)
        scaffold = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = scaffold
        sys.path.insert(0, str(scaffold_py.parent))
        spec.loader.exec_module(scaffold)
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "proj"
            target.mkdir()
            scaffold._copy_skills_and_agents(REPO_ROOT, target, None)
            copied = target / ".claude" / "skills" / "_common" / "review_evidence.py"
            self.assertTrue(
                copied.is_file(),
                f"scaffold must copy review_evidence.py to {copied}",
            )
            self.assertFalse(
                (target / ".claude" / "skills" / "_common"
                 / "test_review_evidence.py").exists(),
                "test files must be excluded from the scaffold copy",
            )


class RicherSkillFileReadDispatchTests(unittest.TestCase):
    """Richer-skill file-read dispatch (craft + arch passes).

    The craft/arch reviewer subagent has read-only tools (Read/Glob/Grep) and
    NO `Skill` tool — a live probe confirmed it cannot route to a user skill
    via Claude's skill router, but CAN `Read` files under `~/.claude/`. So
    `review.py` detects a USER-scope installed skill on disk and hands the
    reviewer its concrete path to read-and-apply; otherwise it inlines jig's
    baseline buckets.

    User-scope only by design: a project-scope `.claude/skills/<name>/` may be
    jig's own `scaffold-init` baseline copy, indistinguishable by path from a
    richer project skill — so it must NOT trigger the richer branch.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jig-rev-richer-")
        self.home = Path(self.tmp) / "home"
        self.home.mkdir(parents=True)
        self.spec = Path(self.tmp) / "spec.md"
        write_synthetic_spec(self.spec, "031-01 alpha")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_user_skill(self, name: str) -> Path:
        d = self.home / ".claude" / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        path = d / "SKILL.md"
        path.write_text(f"---\nname: {name}\n---\n# Richer {name}\n")
        return path

    def _prompt(self, mode: str, *, home: Path, cwd: str = None,
                extra_env: dict = None) -> str:
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        env["HOME"] = str(home)  # Path.home() honors $HOME → hermetic
        env.pop("CLAUDE_PROJECT_DIR", None)  # no inherited leakage
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(
            [sys.executable, str(REVIEW), mode, str(self.spec), "031-01",
             "skills/foo/foo.py"],
            capture_output=True, text=True, env=env, cwd=cwd,
        )
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        return result.stdout

    # ---- pr-review ----
    def test_pr_review_richer_detected_points_at_user_path(self):
        skill = self._make_user_skill("pr-review")
        prompt = self._prompt("pr-review", home=self.home)
        self.assertIn(str(skill), prompt,
                      "richer branch must name the concrete user-skill path")
        self.assertRegex(prompt, r"(?i)read that SKILL\.md in full")
        self.assertRegex(prompt, r"(?i)supersedes the baseline")
        # Still tells the reviewer to normalize into the workflow envelope.
        self.assertRegex(prompt, r"(?i)normalize your findings into the required")

    def test_pr_review_baseline_when_no_user_skill(self):
        prompt = self._prompt("pr-review", home=self.home)  # empty home
        self.assertNotIn(str(self.home / ".claude"), prompt)
        self.assertNotRegex(prompt, r"(?i)read that SKILL\.md in full")
        self.assertRegex(prompt, r"(?i)jig's bundled `pr-review` SKILL\.md baseline")

    def test_pr_review_envelope_preserved_in_richer_branch(self):
        self._make_user_skill("pr-review")
        prompt = self._prompt("pr-review", home=self.home)
        for marker in ("VERDICT", "REASONING", "SPECIFIC ISSUES",
                       "[blocker]", "[nit]", "[strength]"):
            self.assertIn(marker, prompt,
                          f"workflow envelope must survive richer branch: {marker}")

    # ---- arch-review ----
    def test_arch_review_richer_detected_points_at_user_path(self):
        skill = self._make_user_skill("arch-review")
        prompt = self._prompt("arch-review", home=self.home)
        self.assertIn(str(skill), prompt)
        self.assertRegex(prompt, r"(?i)read that SKILL\.md in full")

    def test_arch_review_baseline_when_no_user_skill(self):
        prompt = self._prompt("arch-review", home=self.home)
        self.assertNotRegex(prompt, r"(?i)read that SKILL\.md in full")
        self.assertRegex(prompt,
                         r"(?i)jig's bundled `arch-review` SKILL\.md baseline")

    # ---- user-scope only: project-scope copy must NOT trigger richer branch ----
    def test_project_scope_skill_does_not_trigger_richer_branch(self):
        proj = Path(self.tmp) / "proj"
        d = proj / ".claude" / "skills" / "pr-review"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: pr-review\n---\n# scaffolded copy\n")
        # Empty HOME (no user skill). Guard BOTH likely project-detection
        # vectors a future change might wrongly add: cwd-relative AND
        # CLAUDE_PROJECT_DIR-relative. Detection is user-scope only, so the
        # baseline branch must hold despite the project-scope copy being present.
        prompt = self._prompt("pr-review", home=self.home, cwd=str(proj),
                              extra_env={"CLAUDE_PROJECT_DIR": str(proj)})
        self.assertNotRegex(
            prompt, r"(?i)read that SKILL\.md in full",
            "a project-scope `.claude/skills` copy (possibly jig's own "
            "scaffolded baseline) must NOT be treated as a richer skill",
        )


class RecordReviewAdrModeTests(unittest.TestCase):
    """Slice 064-05 AC #1: `record-review --adr NNNN` writes an ADR-side
    verdict at docs/decisions/reviews/adr-NNNN-<pass>.md keyed on `adr`
    (no `slice` field), mutually exclusive with the spec+slice positionals."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-rec-adr-"))
        (self.tmp / "docs" / "decisions").mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _record(self, *args, summary="## VERDICT\npass\n"):
        return subprocess.run(
            [sys.executable, str(REVIEW), "record-review", *args,
             "--summary-file", "-"],
            input=summary, capture_output=True, text=True, cwd=str(self.tmp),
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )

    def _evidence_file(self):
        return (self.tmp / "docs" / "decisions" / "reviews"
                / "adr-0020-frame-critique.md")

    def test_adr_verdict_lands_at_defined_path(self):
        r = self._record("--adr", "0020", "--pass", "frame-critique",
                         "--verdict", "pass", "--reviewer", "jig:reviewer",
                         "--prompt-source", "review.py frame-critique x")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertTrue(self._evidence_file().is_file(),
                        f"missing: {self._evidence_file()}")

    def test_adr_verdict_keyed_on_adr_not_slice(self):
        self._record("--adr", "20", "--pass", "frame-critique",
                     "--verdict", "pass", "--reviewer", "jig:reviewer",
                     "--prompt-source", "x")
        from _common.parsing import parse_frontmatter
        fields, _ = parse_frontmatter(self._evidence_file().read_text())
        self.assertEqual(fields.get("adr"), "0020",
                         "adr number must be zero-padded to 4 digits")
        self.assertNotIn("slice", fields,
                         "ADR verdict must NOT carry a `slice` field")
        self.assertEqual(fields.get("pass"), "frame-critique")

    def test_adr_and_spec_mutually_exclusive(self):
        # Passing both a spec positional AND --adr → argparse error (exit 2).
        spec = _make_spec_with_slice(self.tmp / "064-z", "05", "foo")
        r = self._record(str(spec), "0XX-05", "--adr", "0020",
                         "--pass", "frame-critique", "--verdict", "pass",
                         "--reviewer", "x", "--prompt-source", "x")
        self.assertEqual(r.returncode, 2, f"stdout: {r.stdout}")

    def test_neither_spec_nor_adr_refused(self):
        r = self._record("--pass", "frame-critique", "--verdict", "pass",
                         "--reviewer", "x", "--prompt-source", "x")
        self.assertEqual(r.returncode, 2, f"stdout: {r.stdout}")


class Bug017RecordReviewStdinTests(unittest.TestCase):
    """Bug 017: `record-review` must never block waiting on stdin.

    The old fallback guarded `sys.stdin.read()` with `not sys.stdin.isatty()`.
    `isatty()` answers "is this a terminal", never "is there input waiting", so
    a pipe whose write end is still open passes the guard and the read blocks
    until an EOF that never arrives. A human at a prompt never hits it; an
    agent harness or CI runner always does — which is why jig's whole suite
    could hang while the bug never reproduced by hand.

    The teeth are in the pipe shape. `subprocess.run(stdin=subprocess.PIPE)`
    closes the write end immediately, the child sees EOF and exits, so a test
    written that way passes against the unfixed helper and proves nothing.
    Only a pipe whose write end the *test* holds open reproduces the hang.
    """

    # Generous: the assertion is termination-vs-hang, not latency. The
    # unfixed helper never returns, so no bound is too short to catch it.
    TIMEOUT = 15

    ARGS = (
        "record-review", "--adr", "0001", "--pass", "frame-critique",
        "--verdict", "pass", "--reviewer", "r", "--prompt-source", "p",
    )

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-bug017-"))
        (self.tmp / "docs" / "decisions").mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _env(self):
        return {**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)}

    def _evidence_file(self):
        return (self.tmp / "docs" / "decisions" / "reviews"
                / "adr-0001-frame-critique.md")

    def test_terminates_when_stdin_is_a_pipe_nobody_closes(self):
        read_fd, write_fd = os.pipe()
        proc = None
        try:
            proc = subprocess.Popen(
                [sys.executable, str(REVIEW), *self.ARGS],
                stdin=read_fd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, cwd=str(self.tmp), env=self._env(),
            )
            os.close(read_fd)
            read_fd = -1
            try:
                proc.communicate(timeout=self.TIMEOUT)
                # Terminating by crashing would also clear the timeout, so
                # pin the exit code: this is the refusal, not a traceback.
                self.assertEqual(proc.returncode, 2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                self.fail(
                    "record-review did not terminate within "
                    f"{self.TIMEOUT}s with stdin a pipe whose write end is "
                    "still open — it is blocked on sys.stdin.read()"
                )
        finally:
            if read_fd != -1:
                os.close(read_fd)
            os.close(write_fd)
            if proc is not None and proc.poll() is None:
                proc.kill()

    def test_missing_body_errors_and_names_the_option(self):
        # Non-interactive with no body source at all: fail fast and say what
        # to pass, rather than recording a verdict with an empty body.
        result = subprocess.run(
            [sys.executable, str(REVIEW), *self.ARGS],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            cwd=str(self.tmp), env=self._env(),
        )
        self.assertEqual(result.returncode, 2, f"stdout: {result.stdout}")
        self.assertIn("--summary-file", result.stderr)
        self.assertNotIn("traceback", result.stderr.lower())
        self.assertFalse(
            self._evidence_file().exists(),
            "a refused record-review must not leave a verdict file behind",
        )

    def test_blank_body_is_refused_like_a_missing_one(self):
        # The enforcement is on the *body*, not on having typed the option:
        # a file (or a pipe) that resolves to whitespace is the verdict with
        # no body that the rule exists to refuse.
        blank = self.tmp / "blank.md"
        blank.write_text("\n   \n")
        result = subprocess.run(
            [sys.executable, str(REVIEW), *self.ARGS,
             "--summary-file", str(blank)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            cwd=str(self.tmp), env=self._env(),
        )
        self.assertEqual(result.returncode, 2, f"stdout: {result.stdout}")
        self.assertIn("empty verdict body", result.stderr)
        self.assertFalse(self._evidence_file().exists())

    def test_explicit_dash_reads_the_body_from_stdin(self):
        # Piping a body stays supported — it just has to be asked for, so the
        # read is the caller's choice and never an implicit gamble on stdin.
        result = subprocess.run(
            [sys.executable, str(REVIEW), *self.ARGS, "--summary-file", "-"],
            input="PIPED-BODY-SENTINEL\n", capture_output=True, text=True,
            cwd=str(self.tmp), env=self._env(),
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("PIPED-BODY-SENTINEL", self._evidence_file().read_text())


if __name__ == "__main__":
    unittest.main()
