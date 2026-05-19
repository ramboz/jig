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


if __name__ == "__main__":
    unittest.main()
