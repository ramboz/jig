"""
Tests for scripts/build_copilot_plugin.py — slice 113-02
(renderer-and-skeleton), grown by 113-03 (agents) and 113-04 (advisory-hooks).

Covers:
  - AC #1/#4: the builder materializes a minimal, directly-installable
    `hosts/copilot/` package: `.plugin/plugin.json` + `.github/skills/<name>/
    SKILL.md` (no companion CLAUDE.md, and — per the 113-02 review fix below
    — no pre-rendered instructions file either).
  - AC #2: the loader-compat invariant — every emitted skill has a
    namespace-safe name and a <=1024-char description, with the full
    original description preserved in the body for any skill the renderer
    had to shorten. A synthetic over-budget fixture proves the truncation
    path fires (the real repo's public skills are ALL currently <=1024 chars
    — see `RealRepoLoaderCompatTests` — so this is exercised against a
    fixture, not real source, per the deviation noted in the slice's
    reconciliation).
  - 113-02 review fix (owner decision): the package does NOT ship a
    pre-rendered `.github/copilot-instructions.md`. Parity ruling: Claude/
    Codex builders ship `templates/CLAUDE.md.template` UNRENDERED (a
    `/plugin` install must not impose instructions on the consuming repo);
    shipping a full-parity, template-carrying package is 113-06 scope, not
    this walking skeleton.
  - 113-03: `agents/*.md` renders to `.github/agents/<name>.agent.md`.
  - 113-04 (`CopilotAdvisoryHookPackagingTests`): the 3 advisory hooks
    (session git-freshness, boundary-change-warn, entry-gate-nudge) render
    to `.github/hooks/*.json`, keyed by Copilot's camelCase event names,
    with their matcher and command paths translated; their scripts ship
    byte-identical under `.github/hooks/scripts/`. AC3 fail-open and AC2
    "firing" are verified via the closest deterministic substitute (direct
    script invocation with a constructed payload), not a live Copilot
    session — see the slice report for what remains unverified live.
  - Build safety mirrors the Claude/Codex builders (refuse unsafe output
    dirs; atomic replace of a stale tree).
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "scaffold-init"))

import build_copilot_plugin  # noqa: E402
import install_contract  # noqa: E402
import scaffold as scaffold_mod  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_repo_behind_origin_main(project_dir: Path) -> None:
    """Turn `project_dir` into a hermetic, no-network git repo whose `HEAD`
    is exactly 1 commit behind a LOCAL `refs/remotes/origin/main` ref —
    the fixture `lib/git_freshness.py`'s `resolve_target`/`_behind_count`
    need to produce a real, non-trivial nudge (craft review fix: prove
    genuine firing, not just "does not crash"). Duplicated (not imported)
    from `skills/scaffold-init/test_copilot_hook_adapter.py`'s identical
    helper — each test file stays self-contained rather than depending on
    a sibling test module.

    Mechanics: commit twice on `main`, pin `refs/remotes/origin/main` to
    the SECOND commit, then hard-reset the branch back to the first — so
    `origin/main` (a real, resolvable ref) is 1 commit ahead of `HEAD` with
    no actual remote or network fetch involved."""
    def _git(*args):
        subprocess.run(
            ["git", *args], cwd=str(project_dir), check=True,
            capture_output=True, text=True,
        )

    _git("init", "-q", "-b", "main")
    _git("config", "user.email", "test@example.com")
    _git("config", "user.name", "Test")
    _git("commit", "-q", "--allow-empty", "-m", "C1")
    first = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(project_dir),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    _git("commit", "-q", "--allow-empty", "-m", "C2")
    second = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(project_dir),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    _git("update-ref", "refs/remotes/origin/main", second)
    _git("reset", "-q", "--hard", first)


def _build(output_dir: Path, source_root: Path = REPO_ROOT):
    out = io.StringIO()
    code = build_copilot_plugin.build(
        source_root=source_root, output_dir=output_dir, out=out
    )
    return code, out.getvalue()


class CopilotPackageContentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-pkg-"))
        self.out_dir = self.tmp / "copilot"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # AC #1
    def test_materializes_manifest(self):
        manifest = self.out_dir / ".plugin" / "plugin.json"
        self.assertTrue(manifest.is_file())
        data = json.loads(manifest.read_text())
        self.assertEqual(
            set(data.keys()),
            {"name", "version", "description", "skills", "agents", "hooks"},
        )
        self.assertEqual(data["name"], "jig")
        self.assertTrue(data["version"])
        self.assertIn("Copilot", data["description"])
        self.assertEqual(data["skills"], ".github/skills")
        self.assertEqual(data["agents"], ".github/agents")
        self.assertEqual(data["hooks"], ".github/hooks/hooks.json")

    def test_manifest_version_matches_claude_manifest(self):
        claude_version = json.loads(
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text()
        )["version"]
        copilot_version = json.loads(
            (self.out_dir / ".plugin" / "plugin.json").read_text()
        )["version"]
        self.assertEqual(copilot_version, claude_version)

    # AC #1 — discovery root per slice 113-01
    def test_materializes_skills_under_github_skills(self):
        skill = self.out_dir / ".github" / "skills" / "scaffold-init" / "SKILL.md"
        self.assertTrue(skill.is_file())

    def test_shared_private_infra_ships_alongside_public_skills(self):
        # skills/_common has no SKILL.md (not a discoverable skill) but other
        # skills' Python modules import it at runtime — it must still ship.
        self.assertTrue(
            (self.out_dir / ".github" / "skills" / "_common").is_dir()
        )

    # 113-02 review fix (owner decision): no pre-rendered instructions file —
    # a `/plugin` install must not impose instructions on the consuming
    # repo; shipping `templates/` (unrendered, like Claude/Codex) is 113-06
    # full-package-parity scope, not this walking skeleton.
    def test_does_not_materialize_an_instructions_file(self):
        self.assertFalse(
            (self.out_dir / ".github" / "copilot-instructions.md").exists()
        )

    def test_no_companion_claude_md_shipped(self):
        leaks = [
            p for p in self.out_dir.rglob("*") if p.is_file() and p.name == "CLAUDE.md"
        ]
        self.assertEqual(leaks, [])

    def test_package_is_exactly_manifest_skills_agents_hooks_scripts_templates(self):
        # 113-03 grew the 113-02 walking skeleton by rendered agents; 113-04
        # grew it by the 3 advisory hooks under `.github/hooks/`; 113-05
        # grows it by 3 MORE hooks in that SAME directory (spec-gate,
        # secret-scan, and the permissions-floor guard — NOT a
        # `.github/copilot/settings.json`; the owner corrected an earlier
        # version of this slice that tried that, since Copilot has no
        # persistent, repo-committable tool-deny mechanism); 113-06 grows it
        # by `.github/scripts/` (the runtime-scripts allowlist, e.g.
        # `spec_lint.py`) and `.github/templates/` (unrendered, matching
        # Claude/Codex) for AC5 package completeness. Still no OTHER new
        # top-level `.github/` directory (MCP config is not this package's
        # scope).
        github_dir = self.out_dir / ".github"
        top_level = {p.name for p in github_dir.iterdir()}
        self.assertEqual(
            top_level, {"skills", "agents", "hooks", "scripts", "templates"}
        )

    def test_manifest_declared_component_paths_resolve_to_expected_types(self):
        manifest = json.loads((self.out_dir / ".plugin" / "plugin.json").read_text())
        self.assertTrue((self.out_dir / manifest["skills"]).is_dir())
        self.assertTrue(
            (self.out_dir / manifest["skills"] / "spec-workflow" / "SKILL.md").is_file()
        )
        self.assertTrue((self.out_dir / manifest["agents"]).is_dir())
        self.assertTrue(
            (self.out_dir / manifest["agents"] / "reviewer.agent.md").is_file()
        )
        hooks_path = self.out_dir / manifest["hooks"]
        self.assertTrue(hooks_path.is_file())
        hooks = json.loads(hooks_path.read_text())
        self.assertEqual(hooks["version"], 1)
        self.assertIn("sessionStart", hooks["hooks"])
        self.assertIn("preToolUse", hooks["hooks"])

    def test_excludes_tests_and_caches(self):
        leaks = [
            p.relative_to(self.out_dir).as_posix()
            for p in self.out_dir.rglob("*")
            if p.is_file()
            and (p.name.startswith("test_") or "__pycache__" in p.parts)
        ]
        self.assertEqual(leaks, [])


class RealRepoLoaderCompatTests(unittest.TestCase):
    """AC #2 against the real repo. NOTE (deviation from the slice brief): at
    spike 113-01 time `memory-sync`/`vision-elicitation` were reported at
    1059/1058 chars; as measured today (via
    `install_contract._read_skill_description`, the same normalization bug
    009 already established for Codex) every current public skill is
    <=1024 chars, `memory-sync` highest at 1010. So today's real build makes
    ZERO truncations — this class asserts that invariant holds (every
    rendered description fits, every rendered name is namespace-safe), and
    `SyntheticOverBudgetDescriptionTests` below exercises the truncation path
    itself against a controlled fixture."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-real-"))
        self.out_dir = self.tmp / "copilot"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _rendered_skill_mds(self):
        skills_dir = self.out_dir / ".github" / "skills"
        return sorted(skills_dir.glob("*/SKILL.md"))

    def test_every_rendered_description_is_within_the_loader_limit(self):
        for skill_md in self._rendered_skill_mds():
            desc = install_contract._read_skill_description(skill_md.read_text())
            self.assertLessEqual(
                len(desc), 1024, f"{skill_md.relative_to(self.out_dir)}: {len(desc)}"
            )

    def test_every_rendered_name_is_namespace_safe(self):
        for skill_md in self._rendered_skill_mds():
            fm, _ = scaffold_mod._split_frontmatter(skill_md.read_text())
            name = scaffold_mod.CopilotScaffoldRenderer.agent_frontmatter_value(
                fm, "name", ""
            )
            self.assertNotIn(":", name, str(skill_md.relative_to(self.out_dir)))

    def test_memory_sync_is_currently_untouched_by_the_render(self):
        # The highest-length real skill today (1010 chars, under the 1024
        # limit) round-trips byte-for-byte through the Copilot renderer,
        # same as Claude/Codex.
        source = (REPO_ROOT / "skills" / "memory-sync" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        rendered = build_copilot_plugin.render_copilot_skill_md(source)
        self.assertEqual(rendered, source)


class SyntheticOverBudgetDescriptionTests(unittest.TestCase):
    """AC #2 — proves the truncation path itself: a source description that
    exceeds Copilot's 1024-character limit renders <=1024 in the frontmatter
    with the full original text preserved in the body, while a compliant
    skill's rendering is untouched. Uses a synthetic fixture (see the
    deviation note on `RealRepoLoaderCompatTests` for why the real
    `memory-sync` no longer exercises this path)."""

    def _make_skill_md(self, description: str) -> str:
        return (
            "---\n"
            "name: over-budget-fixture\n"
            f"description: >\n  {description}\n"
            "user-invocable: true\n"
            "---\n\n"
            "# Over-budget fixture\n\nBody content.\n"
        )

    def test_over_budget_description_truncated_with_full_text_preserved(self):
        long_description = "word " * 300  # > 1024 chars once folded
        self.assertGreater(len(long_description.strip()), 1024)
        source = self._make_skill_md(long_description.strip())
        rendered = build_copilot_plugin.render_copilot_skill_md(source)

        rendered_fm, rendered_body = scaffold_mod._split_frontmatter(rendered)
        rendered_desc = install_contract._read_skill_description(rendered)
        self.assertLessEqual(len(rendered_desc), 1024)
        self.assertIn(long_description.strip(), rendered_body)
        self.assertIn("Full description", rendered_body)
        # The rest of the frontmatter (name, user-invocable) survives.
        self.assertIn("name: over-budget-fixture", rendered_fm)
        self.assertIn("user-invocable: true", rendered_fm)
        # And the rest of the body survives too.
        self.assertIn("# Over-budget fixture", rendered)
        self.assertIn("Body content.", rendered)

    def test_compliant_description_round_trips_byte_identical(self):
        source = self._make_skill_md("a short, compliant description")
        rendered = build_copilot_plugin.render_copilot_skill_md(source)
        self.assertEqual(rendered, source)

    def test_colon_bearing_name_raises(self):
        source = self._make_skill_md("fine").replace(
            "name: over-budget-fixture", "name: jig:over-budget-fixture"
        )
        with self.assertRaises(scaffold_mod.CopilotSkillNameError):
            build_copilot_plugin.render_copilot_skill_md(source)


class CopilotAgentPackagingTests(unittest.TestCase):
    """Slice 113-03 (agents) — the 3 jig custom agents render into
    `.github/agents/<name>.agent.md`.

    AC #1: agents rendered, frontmatter mapped to Copilot's tool vocabulary.
    AC #2: no rendered agent emits a `model:` field or leaks a
    Claude-specific model id.
    AC #3: the rendered reviewer keeps its read-only tool restriction.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-agents-"))
        self.out_dir = self.tmp / "copilot"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _agents_dir(self) -> Path:
        return self.out_dir / ".github" / "agents"

    def _agent_tools(self, name: str) -> list:
        text = (self._agents_dir() / f"{name}.agent.md").read_text()
        fields, _ = scaffold_mod.parse_frontmatter(text)
        return fields.get("tools", [])

    # AC #1
    def test_all_three_agents_render_under_github_agents(self):
        names = sorted(p.name for p in self._agents_dir().glob("*.agent.md"))
        self.assertEqual(
            names,
            ["architect.agent.md", "implementer.agent.md", "reviewer.agent.md"],
        )

    def test_agent_frontmatter_has_name_description_and_tools(self):
        for name in ("architect", "implementer", "reviewer"):
            text = (self._agents_dir() / f"{name}.agent.md").read_text()
            fm, _ = scaffold_mod._split_frontmatter(text)
            self.assertIn(f"name: {name}", fm)
            self.assertIn("description:", fm)
            self.assertIn("tools:", fm)

    def test_agent_body_ships_verbatim_from_source(self):
        for name in ("architect", "implementer", "reviewer"):
            source_body = scaffold_mod._split_frontmatter(
                (REPO_ROOT / "agents" / f"{name}.md").read_text()
            )[1]
            rendered_body = scaffold_mod._split_frontmatter(
                (self._agents_dir() / f"{name}.agent.md").read_text()
            )[1]
            self.assertEqual(rendered_body.strip(), source_body.strip())

    def test_agent_tools_use_copilot_vocabulary_not_claude_names(self):
        # Every rendered tool name must come out of the Copilot mapping
        # table's VALUES — no leftover Claude-cased tool name (Read/Write/
        # Edit/Bash/Glob/Grep/WebSearch) survives the render.
        claude_names = set(scaffold_mod.CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS)
        for name in ("architect", "implementer", "reviewer"):
            tools = self._agent_tools(name)
            self.assertTrue(tools, f"{name} rendered with no tools")
            self.assertFalse(
                claude_names.intersection(tools),
                f"{name} leaked a Claude-cased tool name: {tools}",
            )

    # AC #2
    def test_no_rendered_agent_emits_a_model_field(self):
        for path in self._agents_dir().glob("*.agent.md"):
            fm, _ = scaffold_mod._split_frontmatter(path.read_text())
            self.assertNotIn("model:", fm, path.name)

    def test_no_claude_specific_model_id_leaks_into_any_rendered_agent(self):
        forbidden = ("opus", "sonnet", "claude-")
        for path in self._agents_dir().glob("*.agent.md"):
            text = path.read_text().lower()
            for token in forbidden:
                self.assertNotIn(token, text, f"{path.name} leaked {token!r}")

    # AC #3
    def test_reviewer_carries_zero_mutating_tools(self):
        tools = self._agent_tools("reviewer")
        for mutating in ("create", "edit", "write", "shell", "bash", "fetch"):
            self.assertNotIn(mutating, tools, f"reviewer must stay read-only: {tools}")

    def test_reviewer_keeps_its_read_only_tool_trio(self):
        self.assertEqual(sorted(self._agent_tools("reviewer")), ["glob", "grep", "view"])

    def test_reviewer_prompt_still_states_read_only_access(self):
        text = (self._agents_dir() / "reviewer.agent.md").read_text()
        self.assertIn("Read-only access only", text)

    def test_implementer_keeps_its_write_and_edit_capable_tools(self):
        tools = self._agent_tools("implementer")
        self.assertEqual(
            sorted(tools), sorted(["view", "create", "edit", "bash", "glob", "grep"])
        )

    def test_architect_is_read_only_plus_fetch(self):
        tools = self._agent_tools("architect")
        self.assertEqual(sorted(tools), sorted(["view", "glob", "grep", "fetch"]))


class CopilotAdvisoryHookPackagingTests(unittest.TestCase):
    """Slice 113-04 (advisory-hooks) — the 3 advisory hooks (session
    git-freshness, boundary-change-warn, entry-gate-nudge) render into
    `.github/hooks/*.json` and ship their scripts under
    `.github/hooks/scripts/`.

    NOT E2E (slice 113-08 honesty label): every test in this class invokes
    the rendered `bash` command directly with a constructed stdin payload
    and a manually-chosen `cwd`/`CLAUDE_PROJECT_DIR` — a STATIC PACKAGE
    CHECK proving the command, once spawned, behaves correctly. It does
    NOT prove Copilot itself discovers, resolves, and spawns that command
    from an installed plugin cache with Copilot's own real working
    directory and stdin payload — that is
    `scripts/test_copilot_live_hook_smoke.py`'s `LiveHookRuntimeE2ETests`
    (opt-in, real `copilot` CLI) and `scripts/copilot_live_hook_smoke.py`
    (the documented, repeatable, authenticated/manual command — AC5).

    AC1: event-name + response-schema translation (exercised via the
    rendered JSON's shape). AC2: the 3 hooks are rendered + their scripts
    shipped. AC3: fail-open — verified via the deterministic substitute
    described above. AC4: hook-command paths are plugin-root-relative, not
    the raw `${CLAUDE_PLUGIN_ROOT}` literal.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-hooks-"))
        self.out_dir = self.tmp / "copilot"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _hooks_dir(self) -> Path:
        return self.out_dir / ".github" / "hooks"

    # AC2 — advisory files present (enforcing files are asserted separately
    # by CopilotEnforcingHookPackagingTests; this class stays scoped to the
    # 3 advisory hooks it names).
    def test_all_three_advisory_hook_files_render(self):
        names = {p.name for p in self._hooks_dir().glob("*.json")}
        self.assertTrue(
            {
                "jig-boundary-change-warn.json",
                "jig-entry-gate.json",
                "jig-git-freshness.json",
            }.issubset(names)
        )

    # Schema (CORRECTED 113-05) — every rendered hook file, advisory and
    # enforcing alike, uses the AUTHORITATIVE `{version, hooks: {...}}`
    # shape, not Claude's nested one 113-04 shipped by mistake.
    def test_every_rendered_hook_file_has_the_authoritative_top_level_shape(self):
        for hook_file in self._hooks_dir().glob("*.json"):
            payload = json.loads(hook_file.read_text())
            self.assertEqual(payload.get("version"), 1, hook_file.name)
            self.assertIn("hooks", payload, hook_file.name)

    # AC1
    def test_git_freshness_hook_keyed_by_session_start_camel_case(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-git-freshness.json").read_text()
        )
        self.assertEqual(set(payload["hooks"].keys()), {"sessionStart"})

    def test_boundary_warn_hook_keyed_by_post_tool_use_camel_case(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-boundary-change-warn.json").read_text()
        )
        self.assertEqual(set(payload["hooks"].keys()), {"postToolUse"})

    def test_entry_gate_hook_keyed_by_post_tool_use_camel_case(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-entry-gate.json").read_text()
        )
        self.assertEqual(set(payload["hooks"].keys()), {"postToolUse"})

    def test_boundary_warn_and_entry_gate_matcher_uses_copilot_tool_names(self):
        for stem in ("jig-boundary-change-warn", "jig-entry-gate"):
            payload = json.loads((self._hooks_dir() / f"{stem}.json").read_text())
            matcher = payload["hooks"]["postToolUse"][0]["matcher"]
            self.assertEqual(matcher, "edit|create")
            self.assertNotIn("Edit", matcher)
            self.assertNotIn("Write", matcher)
            self.assertNotIn("MultiEdit", matcher)

    # AC4
    def test_rendered_hook_commands_have_no_raw_claude_plugin_root(self):
        for hook_file in self._hooks_dir().glob("*.json"):
            text = hook_file.read_text()
            self.assertNotIn("CLAUDE_PLUGIN_ROOT", text, hook_file.name)

    def test_rendered_hook_commands_route_through_the_input_adapter(self):
        # 113-04 AC1 follow-up: the rendered command now invokes
        # `copilot_hook_adapter.py <event> <script>` rather than the bare
        # path-rewritten script, so Copilot's camelCase stdin JSON is
        # translated before the (unmodified) jig script sees it.
        payload = json.loads(
            (self._hooks_dir() / "jig-git-freshness.json").read_text()
        )
        command = payload["hooks"]["sessionStart"][0]["bash"]
        self.assertEqual(
            command,
            "python3 .github/hooks/scripts/copilot_hook_adapter.py "
            'SessionStart ".github/hooks/scripts/jig-git-freshness.sh"',
        )

    # AC2 — scripts shipped
    def test_hook_scripts_and_lib_helpers_shipped(self):
        scripts_dir = self._hooks_dir() / "scripts"
        for name in (
            "jig-git-freshness.sh",
            "jig-boundary-change-warn.sh",
            "jig-entry-gate.sh",
            "lib/git_freshness.py",
            "lib/entry_gate.py",
            "lib/read_attribution.py",
            "lib/protected_paths.py",
            "copilot_hook_adapter.py",
        ):
            self.assertTrue(
                (scripts_dir / name).is_file(), f"missing shipped file: {name}"
            )

    def test_adapter_shipped_byte_identical_to_its_canonical_source(self):
        source = (
            REPO_ROOT / "skills" / "scaffold-init" / "copilot_hook_adapter.py"
        ).read_bytes()
        shipped = (
            self._hooks_dir() / "scripts" / "copilot_hook_adapter.py"
        ).read_bytes()
        self.assertEqual(shipped, source)

    def test_shipped_sh_scripts_are_executable(self):
        scripts_dir = self._hooks_dir() / "scripts"
        for sh in scripts_dir.glob("*.sh"):
            mode = sh.stat().st_mode
            self.assertTrue(mode & 0o111, f"{sh.name} is not executable")

    def test_shipped_hook_scripts_are_byte_identical_to_source(self):
        # Spike 113-01 AC5's design: ship the EXISTING scripts unchanged —
        # all translation lives in the rendered `.github/hooks/*.json`, none
        # in the script bodies.
        for name in ("jig-git-freshness.sh", "jig-boundary-change-warn.sh",
                     "jig-entry-gate.sh"):
            source = (REPO_ROOT / "hooks" / "scripts" / name).read_bytes()
            shipped = (self._hooks_dir() / "scripts" / name).read_bytes()
            self.assertEqual(shipped, source, name)

    # AC2 — resolvable relative climb to _common (see
    # `_copy_copilot_hook_scripts`'s docstring: nesting under `.github/`
    # keeps `jig-entry-gate.sh`'s unmodified `../../skills` climb correct).
    def test_common_helpers_are_reachable_from_shipped_hook_scripts(self):
        scripts_dir = self._hooks_dir() / "scripts"
        common_dir = (scripts_dir / ".." / ".." / "skills" / "_common").resolve()
        self.assertTrue(
            common_dir.is_dir(),
            f"entry_gate.py's ../../skills climb from {scripts_dir} does not "
            f"reach a real _common dir (looked at {common_dir})",
        )
        self.assertTrue((common_dir / "project_layout.py").is_file())

    # AC3 — fail-open, verified via the closest deterministic substitute:
    # invoking the shipped script directly (a real Copilot session is not
    # available in this environment; see the slice report for what remains
    # unverified live).
    def test_git_freshness_script_fires_under_a_copilot_shaped_payload(self):
        script = self._hooks_dir() / "scripts" / "jig-git-freshness.sh"
        # git-freshness only reads `source` (spelled identically under
        # Claude and Copilot) plus `project_dir` from the environment — it
        # is the one advisory hook this slice's payload-shape gap does not
        # affect (see the slice report). A non-git CLAUDE_PROJECT_DIR is
        # expected to degrade silently (fail-open), not crash.
        payload = json.dumps({
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.tmp),
            "source": "startup",
        })
        result = subprocess.run(
            ["bash", str(script)],
            input=payload,
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.tmp)},
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # `self.tmp` is not a git repo, so `resolve_target` finds no base —
        # fail-open degrades to silence, not a crash.
        self.assertEqual(result.stdout.strip(), "")

    def test_git_freshness_script_fires_a_real_behind_nudge(self):
        # Craft review fix: prove genuine firing (an `additionalContext`
        # nudge naming the real behind-count), not merely "does not
        # crash" — a hermetic, no-network "HEAD is behind origin/main"
        # fixture.
        repo_dir = Path(tempfile.mkdtemp(prefix="jig-copilot-freshness-behind-"))
        try:
            _make_repo_behind_origin_main(repo_dir)
            script = self._hooks_dir() / "scripts" / "jig-git-freshness.sh"
            payload = json.dumps({
                "sessionId": "abc123",
                "timestamp": "2026-09-15T00:00:00Z",
                "workingDirectory": str(repo_dir),
                "source": "startup",
            })
            result = subprocess.run(
                ["bash", str(script)],
                input=payload,
                capture_output=True,
                text=True,
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo_dir)},
                timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("additionalContext", result.stdout)
            self.assertIn("1 commit(s) behind", result.stdout)
            self.assertIn("origin/main", result.stdout)
        finally:
            shutil.rmtree(repo_dir, ignore_errors=True)

    def test_boundary_warn_script_never_crashes_on_a_copilot_shaped_payload(self):
        # This test invokes the RAW jig script directly (bypassing
        # `copilot_hook_adapter.py`, which the actually-rendered hook
        # command routes through — see
        # `RenderedHookCommandFiresEndToEndTests` below for the real,
        # adapter-fronted firing path). It pins a second-layer safety net:
        # even the unmodified script, given Copilot's un-translated
        # camelCase payload directly, must degrade silently rather than
        # crash or emit malformed output (AC3) — the same defensive
        # property it already had before this slice for ANY unrecognized
        # payload shape.
        script = self._hooks_dir() / "scripts" / "jig-boundary-change-warn.sh"
        payload = json.dumps({
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.tmp),
            "toolName": "edit",
            "toolArgs": {"path": "openapi.yaml"},
        })
        result = subprocess.run(
            ["bash", str(script)],
            input=payload,
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.tmp)},
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # Fail-open degrades to no output at all (sys.exit(0) with nothing
        # printed) rather than emitting anything malformed.
        if result.stdout.strip():
            json.loads(result.stdout)  # must at least be valid JSON if non-empty

    def test_boundary_warn_script_still_fires_under_a_claude_shaped_payload(self):
        # Regression guard: the Copilot packaging must not have broken the
        # shared script's Claude-shaped behavior (it is byte-identical to
        # source — this is really testing the fixture/harness, but pins the
        # contrast with the Copilot-shaped case above).
        script = self._hooks_dir() / "scripts" / "jig-boundary-change-warn.sh"
        target = self.tmp / "openapi.yaml"
        target.write_text("openapi: 3.0.0\n")
        payload = json.dumps({
            "session_id": "abc123",
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target)},
        })
        result = subprocess.run(
            ["bash", str(script)],
            input=payload,
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.tmp),
                 "JIG_PROTECTED_PATHS": "0"},
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("additionalContext", result.stdout)


class CopilotEnforcingHookPackagingTests(unittest.TestCase):
    """Slice 113-05 — the 2 ENFORCING hooks (spec-gate, secret-scan) render
    into `.github/hooks/*.json` (AUTHORITATIVE flat schema) and ship their
    scripts under `.github/hooks/scripts/`, exactly like
    `CopilotAdvisoryHookPackagingTests` for the advisory 3, plus the
    `--enforce` adapter flag and end-to-end exit-code-preserved firing.

    NOT E2E (slice 113-08 honesty label — see
    `CopilotAdvisoryHookPackagingTests`'s own docstring for the full
    rationale): the `_run_rendered_command` tests below spawn the rendered
    command directly with a constructed payload, not through a real
    Copilot session. Live, Copilot-driven enforcement proof is
    `scripts/test_copilot_live_hook_smoke.py`'s `LiveHookRuntimeE2ETests`
    (opt-in) / `scripts/copilot_live_hook_smoke.py` (AC5's documented
    manual command)."""

    # Built by concatenation so this file's own source text never contains
    # the contiguous AWS-key-shaped substring — see
    # `skills/scaffold-init/test_copilot_hook_adapter.EnforcingModeTests`'s
    # identical comment for why.
    _FAKE_AWS_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-enforcing-hooks-"))
        self.out_dir = self.tmp / "copilot"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)
        self.project_dir = Path(tempfile.mkdtemp(prefix="jig-copilot-enforcing-proj-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def _hooks_dir(self) -> Path:
        return self.out_dir / ".github" / "hooks"

    # AC2
    def test_both_enforcing_hook_files_render(self):
        names = {p.name for p in self._hooks_dir().glob("*.json")}
        self.assertTrue(
            {"jig-spec-gate.json", "jig-secret-scan.json"}.issubset(names)
        )

    # AC1 — schema
    def test_spec_gate_hook_keyed_by_pre_tool_use_camel_case(self):
        payload = json.loads((self._hooks_dir() / "jig-spec-gate.json").read_text())
        self.assertEqual(payload["version"], 1)
        self.assertEqual(set(payload["hooks"].keys()), {"preToolUse"})

    def test_spec_gate_and_secret_scan_matcher_uses_copilot_tool_names(self):
        for stem in ("jig-spec-gate", "jig-secret-scan"):
            payload = json.loads((self._hooks_dir() / f"{stem}.json").read_text())
            matcher = payload["hooks"]["preToolUse"][0]["matcher"]
            self.assertEqual(matcher, "edit|create")

    def test_spec_gate_and_secret_scan_do_not_leak_into_each_others_file(self):
        # They share ONE source entry (Edit|Write|MultiEdit) — each
        # rendered file must carry only its own script.
        spec_gate = json.loads((self._hooks_dir() / "jig-spec-gate.json").read_text())
        secret_scan = json.loads(
            (self._hooks_dir() / "jig-secret-scan.json").read_text()
        )
        spec_gate_command = spec_gate["hooks"]["preToolUse"][0]["bash"]
        secret_scan_command = secret_scan["hooks"]["preToolUse"][0]["bash"]
        self.assertIn("jig-spec-gate.sh", spec_gate_command)
        self.assertNotIn("jig-secret-scan.sh", spec_gate_command)
        self.assertIn("jig-secret-scan.sh", secret_scan_command)
        self.assertNotIn("jig-spec-gate.sh", secret_scan_command)

    # AC1 — the enforcing mode switch
    def test_both_enforcing_hooks_render_with_the_enforce_flag(self):
        for stem in ("jig-spec-gate", "jig-secret-scan"):
            payload = json.loads((self._hooks_dir() / f"{stem}.json").read_text())
            command = payload["hooks"]["preToolUse"][0]["bash"]
            self.assertIn("--enforce", command, stem)

    def test_advisory_hooks_do_not_render_with_the_enforce_flag(self):
        # Regression guard: the schema fix must not have bled the enforcing
        # mode into the advisory hooks.
        for stem in ("jig-git-freshness", "jig-boundary-change-warn", "jig-entry-gate"):
            payload = json.loads((self._hooks_dir() / f"{stem}.json").read_text())
            event = next(iter(payload["hooks"]))
            command = payload["hooks"][event][0]["bash"]
            self.assertNotIn("--enforce", command, stem)

    # AC2 — scripts shipped
    def test_enforcing_hook_scripts_shipped_and_executable(self):
        scripts_dir = self._hooks_dir() / "scripts"
        for name in ("jig-spec-gate.sh", "jig-secret-scan.sh"):
            path = scripts_dir / name
            self.assertTrue(path.is_file(), f"missing shipped file: {name}")
            self.assertTrue(path.stat().st_mode & 0o111, f"{name} is not executable")

    def test_enforcing_hook_scripts_are_byte_identical_to_source(self):
        for name in ("jig-spec-gate.sh", "jig-secret-scan.sh"):
            source = (REPO_ROOT / "hooks" / "scripts" / name).read_bytes()
            shipped = (self._hooks_dir() / "scripts" / name).read_bytes()
            self.assertEqual(shipped, source, name)

    # AC1 — positive confirmation, not absence-of-error: the ACTUALLY-BUILT
    # package's rendered command, run end to end, DENIES a real blocked
    # edit (exit 2 + a deny body) and ALLOWS a real safe one (exit 0).
    def _run_rendered_command(self, stem: str, payload: dict, extra_env=None):
        hook_file = self._hooks_dir() / f"{stem}.json"
        rendered = json.loads(hook_file.read_text())
        event = next(iter(rendered["hooks"]))
        command = rendered["hooks"][event][0]["bash"]
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(self.project_dir),
            **(extra_env or {}),
        }
        return subprocess.run(
            ["bash", "-c", command],
            input=json.dumps(payload).encode(),
            capture_output=True,
            cwd=str(self.out_dir),
            env=env,
            timeout=15,
        )

    def test_spec_gate_rendered_command_denies_conventions_md(self):
        result = self._run_rendered_command("jig-spec-gate", {
            "sessionId": "abc123",
            "toolName": "edit",
            "toolArgs": {"path": "docs/conventions.md"},
        })
        self.assertEqual(result.returncode, 2)
        deny = json.loads(result.stdout.decode())
        self.assertEqual(deny["permissionDecision"], "deny")

    def test_spec_gate_rendered_command_allows_a_non_gated_file(self):
        result = self._run_rendered_command("jig-spec-gate", {
            "sessionId": "abc123",
            "toolName": "edit",
            "toolArgs": {"path": "README.md"},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_secret_scan_rendered_command_denies_an_aws_key(self):
        result = self._run_rendered_command("jig-secret-scan", {
            "sessionId": "abc123",
            "toolName": "edit",
            "toolArgs": {"path": "config.py", "new_string": self._FAKE_AWS_KEY},
        })
        self.assertEqual(result.returncode, 2)
        deny = json.loads(result.stdout.decode())
        self.assertEqual(deny["permissionDecision"], "deny")

    def test_secret_scan_rendered_command_allows_benign_content(self):
        result = self._run_rendered_command("jig-secret-scan", {
            "sessionId": "abc123",
            "toolName": "edit",
            "toolArgs": {"path": "config.py", "new_string": "hello world"},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")


class CopilotPermissionsFloorHookPackagingTests(unittest.TestCase):
    """Slice 113-05 AC3 (owner reshape) — jig's `_PERMISSIONS_DENY_DEFAULTS`
    security floor renders as `.github/hooks/jig-permissions-floor.json`, a
    REAL enforcing `preToolUse` hook — NOT a `.github/copilot/settings.json`
    file (an earlier version of this slice tried that; the owner corrected
    it after confirming Copilot has no persistent, repo-committable
    tool-deny mechanism). See `CopilotEnforcingHookPackagingTests` for the
    sibling coverage of the spec-gate/secret-scan enforcing hooks."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-permfloor-"))
        self.out_dir = self.tmp / "copilot"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _hooks_dir(self) -> Path:
        return self.out_dir / ".github" / "hooks"

    def test_no_dead_settings_json_rendered(self):
        # The corrected design ships NO `.github/copilot/` directory at all
        # — there is no valid persisted key to put there.
        self.assertFalse((self.out_dir / ".github" / "copilot").exists())

    def test_permissions_floor_hook_file_renders(self):
        self.assertTrue(
            (self._hooks_dir() / "jig-permissions-floor.json").is_file()
        )

    def test_keyed_by_pre_tool_use_camel_case(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-permissions-floor.json").read_text()
        )
        self.assertEqual(payload["version"], 1)
        self.assertEqual(set(payload["hooks"].keys()), {"preToolUse"})

    def test_matcher_is_the_bash_tool_name(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-permissions-floor.json").read_text()
        )
        self.assertEqual(payload["hooks"]["preToolUse"][0]["matcher"], "bash")

    def test_command_is_enforcing_and_targets_the_floor_script(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-permissions-floor.json").read_text()
        )
        command = payload["hooks"]["preToolUse"][0]["bash"]
        self.assertIn("--enforce", command)
        self.assertIn("copilot_permissions_floor.py", command)

    def test_floor_script_shipped_alongside_the_adapter(self):
        scripts_dir = self._hooks_dir() / "scripts"
        self.assertTrue((scripts_dir / "copilot_permissions_floor.py").is_file())
        self.assertTrue((scripts_dir / "copilot_hook_adapter.py").is_file())

    def test_floor_script_shipped_byte_identical_to_source(self):
        source = (
            REPO_ROOT / "skills" / "scaffold-init" / "copilot_permissions_floor.py"
        ).read_bytes()
        shipped = (
            self._hooks_dir() / "scripts" / "copilot_permissions_floor.py"
        ).read_bytes()
        self.assertEqual(shipped, source)

    # AC1/AC3 — positive confirmation via the ACTUALLY-BUILT package's
    # rendered command: a real destructive command denies; a real safe one
    # allows.
    def _run_rendered_command(self, command_string: str):
        hook_file = self._hooks_dir() / "jig-permissions-floor.json"
        rendered = json.loads(hook_file.read_text())
        command = rendered["hooks"]["preToolUse"][0]["bash"]
        payload = {
            "sessionId": "abc123",
            "toolName": "bash",
            "toolArgs": {"command": command_string},
        }
        return subprocess.run(
            ["bash", "-c", command],
            input=json.dumps(payload).encode(),
            capture_output=True,
            cwd=str(self.out_dir),
            timeout=15,
        )

    def test_rendered_command_denies_rm_rf(self):
        result = self._run_rendered_command("rm -rf /tmp/x")
        self.assertEqual(result.returncode, 2)
        deny = json.loads(result.stdout.decode())
        self.assertEqual(deny["permissionDecision"], "deny")

    def test_rendered_command_denies_force_push_after_remote_and_branch(self):
        # The mid-string-wildcard case Copilot's own permission syntax
        # could not express — the whole reason this is a script, not a
        # settings.json rule.
        result = self._run_rendered_command("git push origin main --force")
        self.assertEqual(result.returncode, 2)

    def test_rendered_command_allows_git_status(self):
        result = self._run_rendered_command("git status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_rendered_command_allows_plain_git_push(self):
        result = self._run_rendered_command("git push origin main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")


class HookInventoryCoverageTests(unittest.TestCase):
    """Slice 113-05 AC2 — `build_copilot_plugin._JIG_HOOK_INVENTORY` covers
    every REAL (event, matcher, script) hook registration in
    `hooks/hooks.json` — no jig hook silently dropped (ADR-0061). This is a
    STRUCTURAL check, not documentation-only: it fails if a future hook is
    added to `hooks.json` without a matching inventory entry (or vice
    versa), and it fails if a `SHIPPED` entry is not actually present in the
    built package. Entries with `source == "copilot-only"` (currently: the
    permissions-floor hook, which has no hooks.json counterpart to
    translate FROM) are exempt from the hooks.json cross-check, but still
    covered by the status/notes/actually-built checks below."""

    def _real_registrations(self):
        source = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        registrations = set()
        for event, entries in source["hooks"].items():
            for entry in entries:
                matcher = entry.get("matcher")
                for h in entry.get("hooks", []):
                    command = h.get("command", "")
                    match = re.search(r"(jig-[A-Za-z0-9-]+\.sh)", command)
                    if match:
                        registrations.add((event, matcher, match.group(1)))
        return registrations

    def _inventoried_from_hooks_json(self):
        return {
            (r["event"], r["matcher"], r["script"])
            for r in build_copilot_plugin._JIG_HOOK_INVENTORY
            if r["source"] == "hooks.json"
        }

    def test_every_real_registration_is_in_the_inventory(self):
        missing = self._real_registrations() - self._inventoried_from_hooks_json()
        self.assertEqual(missing, set(), f"undocumented hook registrations: {missing}")

    def test_inventory_has_no_stale_hooks_json_entries(self):
        stale = self._inventoried_from_hooks_json() - self._real_registrations()
        self.assertEqual(
            stale, set(), f"inventory entries no longer in hooks.json: {stale}"
        )

    def test_every_entry_has_a_known_source(self):
        for r in build_copilot_plugin._JIG_HOOK_INVENTORY:
            self.assertIn(r["source"], {"hooks.json", "copilot-only"})

    def test_every_entry_has_a_known_status(self):
        for r in build_copilot_plugin._JIG_HOOK_INVENTORY:
            self.assertIn(r["status"], {"SHIPPED", "MAPPABLE", "UNMAPPABLE"})

    def test_every_entry_has_documented_notes(self):
        for r in build_copilot_plugin._JIG_HOOK_INVENTORY:
            self.assertTrue(r.get("notes"), f"{r['script']} ({r['event']}) has no notes")

    def test_permissions_floor_is_a_copilot_only_shipped_entry(self):
        # The permissions floor (AC3) is NOT a hooks.json translation — it
        # has no Claude-side hook script (Claude enforces the floor via its
        # native permissions.deny engine) — but it must still show up here,
        # accurately, as SHIPPED (not silently left implying "still a
        # settings.json" or omitted entirely).
        floor_entries = [
            r for r in build_copilot_plugin._JIG_HOOK_INVENTORY
            if r["script"] == "copilot_permissions_floor.py"
        ]
        self.assertEqual(len(floor_entries), 1)
        entry = floor_entries[0]
        self.assertEqual(entry["source"], "copilot-only")
        self.assertEqual(entry["status"], "SHIPPED")

    def test_every_shipped_entry_is_actually_built(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-inventory-"))
        try:
            out_dir = tmp / "copilot"
            code, log = _build(out_dir)
            self.assertEqual(code, 0, log)
            hooks_dir = out_dir / ".github" / "hooks"
            rendered_text = "\n".join(
                f.read_text() for f in hooks_dir.glob("*.json")
            )
            for r in build_copilot_plugin._JIG_HOOK_INVENTORY:
                if r["status"] != "SHIPPED":
                    continue
                self.assertIn(
                    r["script"], rendered_text,
                    f"{r['script']} marked SHIPPED but not found in any "
                    "rendered hook file",
                )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # 113-06 AC6 — the invariant-closure check: every remaining advisory hook
    # this slice renders flips MAPPABLE -> SHIPPED, so the ONLY entries left
    # at a non-SHIPPED status are the genuinely UNMAPPABLE ones (Task/Skill/
    # AskUserQuestion). A future hook landing back at MAPPABLE (added to
    # hooks.json but never rendered) fails this test rather than silently
    # sitting in limbo forever.
    def test_no_mappable_entry_remains(self):
        mappable = [
            r for r in build_copilot_plugin._JIG_HOOK_INVENTORY
            if r["status"] == "MAPPABLE"
        ]
        self.assertEqual(
            mappable, [],
            f"MAPPABLE entries remain un-rendered: {mappable!r}",
        )


class RemainingAdvisoryHookPackagingTests(unittest.TestCase):
    """Slice 113-06 AC6 (remaining-advisory-hook parity) — the 9 remaining
    `MAPPABLE` advisory hooks (`jig-context-check.sh`,
    `jig-post-edit-verify.sh`, `jig-project-orient.sh`,
    `jig-semantic-index.sh`, `jig-memory-scan.sh`,
    `jig-decision-inflight.sh`, `jig-task-capture.sh`,
    `jig-decision-capture.sh`, `jig-claim-check.sh`) render into
    `.github/hooks/*.json` and ship their scripts + `lib/` deps under
    `.github/hooks/scripts/`, exactly like `CopilotAdvisoryHookPackagingTests`
    for the original 3.

    `jig-context-check.sh` backs THREE Claude events (PreToolUse/Read,
    SessionStart, UserPromptSubmit) — the multi-event MERGE fix this slice
    makes: without it, three separate `.github/hooks/jig-context-check.json`
    writes would collide (last-write-wins), silently dropping two of the
    three registrations."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-remaining-hooks-"))
        self.out_dir = self.tmp / "copilot"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _hooks_dir(self) -> Path:
        return self.out_dir / ".github" / "hooks"

    # The multi-event merge, the load-bearing fix.
    def test_context_check_is_one_file_with_three_event_keys(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-context-check.json").read_text()
        )
        self.assertEqual(payload["version"], 1)
        self.assertEqual(
            set(payload["hooks"].keys()),
            {"preToolUse", "sessionStart", "userPromptSubmitted"},
        )

    def test_context_check_pretooluse_matcher_is_view(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-context-check.json").read_text()
        )
        entry = payload["hooks"]["preToolUse"][0]
        self.assertEqual(entry["matcher"], "view")

    def test_context_check_sessionstart_and_userpromptsubmit_have_no_matcher(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-context-check.json").read_text()
        )
        for event in ("sessionStart", "userPromptSubmitted"):
            entry = payload["hooks"][event][0]
            self.assertNotIn("matcher", entry, event)

    def test_context_check_every_event_command_targets_the_script(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-context-check.json").read_text()
        )
        for event, entries in payload["hooks"].items():
            self.assertIn("jig-context-check.sh", entries[0]["bash"], event)

    # Filename-uniqueness guard (spec 113-06 AC6): the merge-by-stem fix must
    # never let two DIFFERENT scripts collide on the same output filename —
    # every rendered `.json` file corresponds to exactly one script.
    def test_no_two_distinct_scripts_share_an_output_filename(self):
        all_registrations = (
            build_copilot_plugin._COPILOT_ADVISORY_HOOKS
            + build_copilot_plugin._COPILOT_REMAINING_ADVISORY_HOOKS
            + build_copilot_plugin._COPILOT_ENFORCING_HOOKS
        )
        stem_to_scripts: dict = {}
        for _event, script_name, stem in all_registrations:
            stem_to_scripts.setdefault(stem, set()).add(script_name)
        collisions = {
            stem: scripts
            for stem, scripts in stem_to_scripts.items()
            if len(scripts) > 1
        }
        self.assertEqual(collisions, {}, f"stem collides across scripts: {collisions!r}")

    def test_merge_collision_on_same_stem_same_event_raises_not_silently_drops(self):
        # Defensive guard (113-06 arch review): the per-script event merge must
        # RAISE if two registrations under one output stem ever resolve to the
        # same Copilot event key — never silently drop one (the exact bug this
        # slice fixes, at event granularity). Force it with two SessionStart
        # scripts sharing a stem: both render {sessionStart: [...]}, colliding on
        # the "sessionStart" key. Guards against a future non-injective event map
        # or a duplicate registration reintroducing the silent drop.
        colliding = (
            ("SessionStart", "jig-project-orient.sh", "jig-collide"),
            ("SessionStart", "jig-semantic-index.sh", "jig-collide"),
        )
        out = Path(tempfile.mkdtemp(prefix="jig-copilot-collide-"))
        saved = build_copilot_plugin._COPILOT_REMAINING_ADVISORY_HOOKS
        build_copilot_plugin._COPILOT_REMAINING_ADVISORY_HOOKS = colliding
        try:
            with self.assertRaises(ValueError) as ctx:
                build_copilot_plugin._write_copilot_hooks(REPO_ROOT, out)
            self.assertIn("merge collision", str(ctx.exception))
        finally:
            build_copilot_plugin._COPILOT_REMAINING_ADVISORY_HOOKS = saved
            shutil.rmtree(out, ignore_errors=True)

    def test_every_rendered_hook_file_on_disk_maps_to_exactly_one_stem(self):
        # Every *.json file under .github/hooks/ is named after exactly one
        # stem — no two registrations ever wrote to the same path for
        # different content (the specific silent-drop bug this slice fixes).
        rendered_stems = {p.stem for p in self._hooks_dir().glob("*.json")}
        expected_stems = {
            stem for _event, _script, stem in (
                build_copilot_plugin._COPILOT_ADVISORY_HOOKS
                + build_copilot_plugin._COPILOT_REMAINING_ADVISORY_HOOKS
                + build_copilot_plugin._COPILOT_ENFORCING_HOOKS
            )
        }
        expected_stems.add("jig-permissions-floor")
        expected_stems.add("hooks")
        self.assertEqual(rendered_stems, expected_stems)

    def test_aggregate_hooks_file_contains_every_per_hook_registration(self):
        aggregate = json.loads((self._hooks_dir() / "hooks.json").read_text())
        self.assertEqual(aggregate["version"], 1)
        per_hook_entries = 0
        for hook_file in self._hooks_dir().glob("*.json"):
            if hook_file.name == "hooks.json":
                continue
            payload = json.loads(hook_file.read_text())
            for event, entries in payload["hooks"].items():
                per_hook_entries += len(entries)
                for entry in entries:
                    self.assertIn(entry, aggregate["hooks"][event])
        aggregate_entries = sum(len(entries) for entries in aggregate["hooks"].values())
        self.assertEqual(aggregate_entries, per_hook_entries)

    # AC2/AC6 — every hook file for the 9 remaining scripts renders.
    def test_post_edit_verify_renders_under_post_tool_use(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-post-edit-verify.json").read_text()
        )
        self.assertEqual(set(payload["hooks"].keys()), {"postToolUse"})

    def test_project_orient_and_semantic_index_render_under_session_start(self):
        for stem in ("jig-project-orient", "jig-semantic-index"):
            payload = json.loads((self._hooks_dir() / f"{stem}.json").read_text())
            self.assertEqual(set(payload["hooks"].keys()), {"sessionStart"})

    def test_memory_scan_renders_under_user_prompt_submit(self):
        payload = json.loads(
            (self._hooks_dir() / "jig-memory-scan.json").read_text()
        )
        self.assertEqual(set(payload["hooks"].keys()), {"userPromptSubmitted"})

    def test_decision_inflight_renders_only_the_mappable_userpromptsubmit_registration(self):
        # The PostToolUse/AskUserQuestion registration of this SAME script
        # stays UNMAPPABLE (no confirmed Copilot AskUserQuestion analogue) —
        # only the UserPromptSubmit registration renders.
        payload = json.loads(
            (self._hooks_dir() / "jig-decision-inflight.json").read_text()
        )
        self.assertEqual(set(payload["hooks"].keys()), {"userPromptSubmitted"})

    def test_task_capture_decision_capture_claim_check_render_under_stop(self):
        for stem in ("jig-task-capture", "jig-decision-capture", "jig-claim-check"):
            payload = json.loads((self._hooks_dir() / f"{stem}.json").read_text())
            self.assertEqual(set(payload["hooks"].keys()), {"agentStop"}, stem)

    # AC2 — scripts + lib deps shipped (the 113-06 audit: these libs are NOT
    # covered by the 113-04/113-05 lib allowlist, which was curated for the
    # original 6 hooks only).
    def test_nine_remaining_scripts_shipped_and_executable(self):
        scripts_dir = self._hooks_dir() / "scripts"
        for name in (
            "jig-context-check.sh",
            "jig-post-edit-verify.sh",
            "jig-project-orient.sh",
            "jig-semantic-index.sh",
            "jig-memory-scan.sh",
            "jig-decision-inflight.sh",
            "jig-task-capture.sh",
            "jig-decision-capture.sh",
            "jig-claim-check.sh",
        ):
            path = scripts_dir / name
            self.assertTrue(path.is_file(), f"missing shipped file: {name}")
            self.assertTrue(path.stat().st_mode & 0o111, f"{name} is not executable")

    def test_nine_remaining_scripts_are_byte_identical_to_source(self):
        scripts_dir = self._hooks_dir() / "scripts"
        for name in (
            "jig-context-check.sh",
            "jig-post-edit-verify.sh",
            "jig-project-orient.sh",
            "jig-semantic-index.sh",
            "jig-memory-scan.sh",
            "jig-decision-inflight.sh",
            "jig-task-capture.sh",
            "jig-decision-capture.sh",
            "jig-claim-check.sh",
        ):
            source = (REPO_ROOT / "hooks" / "scripts" / name).read_bytes()
            shipped = (scripts_dir / name).read_bytes()
            self.assertEqual(shipped, source, name)

    def test_newly_required_lib_deps_shipped(self):
        # The 113-06 audit findings: context-check needs lib/context_fill.py;
        # decision-inflight and decision-capture need lib/decision_scratch.py;
        # decision-capture also needs lib/decision_scan.py; claim-check needs
        # lib/claim_check.py. None of these 4 were in the 113-04/05 allowlist
        # (curated for the original 6 hooks only).
        scripts_dir = self._hooks_dir() / "scripts"
        for rel_name in (
            "lib/context_fill.py",
            "lib/decision_scratch.py",
            "lib/decision_scan.py",
            "lib/claim_check.py",
        ):
            self.assertTrue(
                (scripts_dir / rel_name).is_file(), f"missing shipped lib dep: {rel_name}"
            )

    def test_project_orient_can_resolve_spec_workflow_skill_via_relative_climb(self):
        # jig-project-orient.sh's fallback candidate is
        # `script_dir.parents[1] / 'skills' / 'spec-workflow' / 'workflow.py'`
        # — from `.github/hooks/scripts` that climbs to `.github/skills/
        # spec-workflow/workflow.py`, which `_copy_skills` already ships.
        scripts_dir = self._hooks_dir() / "scripts"
        workflow = scripts_dir.parents[1] / "skills" / "spec-workflow" / "workflow.py"
        self.assertTrue(workflow.is_file(), str(workflow))


class RenderedHookCommandFiresEndToEndTests(unittest.TestCase):
    """Slice 113-04 follow-up (coordinator-requested AC1 completion) — the
    ACTUALLY-BUILT package's rendered `command` string (adapter + script,
    exactly what a Copilot session would run) fires correctly under a real
    Copilot-shaped (camelCase) payload. This is the "make boundary-warn +
    entry-gate fire too" verification, exercised against the real build
    output rather than a hand-constructed path (see
    `skills/scaffold-init/test_copilot_hook_adapter.py` for the adapter's
    own direct/unit-level coverage of the same claim)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-e2e-"))
        self.out_dir = self.tmp / "copilot"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)
        self.project_dir = Path(tempfile.mkdtemp(prefix="jig-copilot-e2e-proj-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def _run_rendered_command(self, stem: str, payload: dict):
        hook_file = self.out_dir / ".github" / "hooks" / f"{stem}.json"
        rendered = json.loads(hook_file.read_text())
        event = next(iter(rendered["hooks"]))
        command = rendered["hooks"][event][0]["bash"]
        # cwd=self.out_dir: the best-hypothesis assumption this slice's
        # renderer commits to (plugin-root-relative paths) — see
        # `CopilotScaffoldRenderer.rewrite_hook_command`'s docstring for the
        # residual on whether Copilot actually spawns hook commands with
        # this CWD.
        #
        # ALSO force CLAUDE_PROJECT_DIR to this test's own temp project dir
        # (craft review fix — hermeticity): the adapter only exports it
        # from the payload's `workingDirectory` when it is NOT already
        # present in the inherited environment. Under a real Claude Code
        # session CLAUDE_PROJECT_DIR is set to the actual repo being worked
        # in; without this override, entry_gate.py would evaluate
        # lifecycle state against THAT repo (which has its own
        # `.jig/spec-ref` marker) instead of this test's isolated temp
        # dir — an environment-dependent result, not a hermetic one.
        env = {
            **os.environ,
            "TMPDIR": str(self.project_dir),
            "CLAUDE_PROJECT_DIR": str(self.project_dir),
        }
        return subprocess.run(
            ["bash", "-c", command],
            input=json.dumps(payload).encode(),
            capture_output=True,
            cwd=str(self.out_dir),
            env=env,
            timeout=15,
        )

    def test_git_freshness_rendered_command_fires_cleanly(self):
        # `self.project_dir` is not a git repo, so `resolve_target` finds
        # no base — fail-open degrades to silence, not a crash.
        result = self._run_rendered_command("jig-git-freshness", {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "source": "startup",
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")

    def test_git_freshness_rendered_command_fires_a_real_behind_nudge(self):
        # Craft review fix: prove genuine firing (an `additionalContext`
        # nudge naming the real behind-count) through the ACTUALLY-BUILT
        # package's rendered command, not merely "does not crash".
        _make_repo_behind_origin_main(self.project_dir)
        result = self._run_rendered_command("jig-git-freshness", {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "source": "startup",
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        stdout = result.stdout.decode()
        self.assertIn("additionalContext", stdout)
        self.assertIn("1 commit(s) behind", stdout)
        self.assertIn("origin/main", stdout)

    def test_boundary_warn_rendered_command_fires_on_a_contract_artifact(self):
        result = self._run_rendered_command("jig-boundary-change-warn", {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "toolName": "edit",
            "toolArgs": {"path": "openapi.yaml"},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("additionalContext", result.stdout.decode())

    def test_boundary_warn_rendered_command_fires_on_create_tool(self):
        result = self._run_rendered_command("jig-boundary-change-warn", {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "toolName": "create",
            "toolArgs": {"path": "schema.proto"},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("additionalContext", result.stdout.decode())

    def test_entry_gate_rendered_command_fires_on_an_out_of_lifecycle_edit(self):
        result = self._run_rendered_command("jig-entry-gate", {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "toolName": "edit",
            "toolArgs": {"path": "app.py"},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("additionalContext", result.stdout.decode())
        self.assertIn("outside the jig lifecycle", result.stdout.decode())

    def test_boundary_warn_rendered_command_stays_silent_on_a_non_contract_file(self):
        result = self._run_rendered_command("jig-boundary-change-warn", {
            "sessionId": "abc123",
            "timestamp": "2026-09-15T00:00:00Z",
            "workingDirectory": str(self.project_dir),
            "toolName": "edit",
            "toolArgs": {"path": "README.md"},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), "")


class ClaudeCodexAgentOutputUnaffectedByCopilotAgentRenderingTests(unittest.TestCase):
    """Slice 113-03 design decision #5 — rendering Copilot agents must not
    touch the Claude/Codex agent source or their own committed outputs."""

    def test_canonical_source_agents_directory_untouched(self):
        # The Copilot builder reads FROM agents/*.md; it must never write
        # back into the canonical source tree the Claude/Codex builders also
        # read from.
        before = {
            p: p.read_bytes() for p in (REPO_ROOT / "agents").glob("*.md")
        }
        tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-agents-noimpact-"))
        try:
            code, log = _build(tmp / "copilot")
            self.assertEqual(code, 0, log)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        after = {p: p.read_bytes() for p in (REPO_ROOT / "agents").glob("*.md")}
        self.assertEqual(before, after)

    def test_committed_codex_agent_toml_unaffected(self):
        codex_agent = (
            REPO_ROOT / "hosts" / "codex" / "plugins" / "jig" / "agents"
            / "jig-reviewer.toml"
        )
        if not codex_agent.is_file():
            self.skipTest("committed hosts/codex package not built in this checkout")
        before = codex_agent.read_bytes()
        tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-agents-codex-noimpact-"))
        try:
            code, log = _build(tmp / "copilot")
            self.assertEqual(code, 0, log)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(codex_agent.read_bytes(), before)


class DescriptionFieldEncodingTests(unittest.TestCase):
    """113-02 review fix (craft) — `_replace_description_field` must not
    `\\uXXXX`-escape non-ASCII characters. `install_contract._read_skill_description`
    (the re-measurement `loader_safe_description`'s budget is meant to bind)
    does not decode escapes — it just strips surrounding quotes — so an
    `ensure_ascii=True` JSON dump would inflate a single "é" into the 6
    literal characters `\\u00e9`, making jig's own re-measured length
    disagree with what a real YAML-aware loader (and the intended 1024-char
    budget) would see. Writing the raw UTF-8 character keeps the two
    consistent."""

    def test_non_ascii_value_is_not_escaped(self):
        fm = "---\nname: x\ndescription: old\nuser-invocable: true\n---\n"
        new_value = "café résumé — naïve"
        result = build_copilot_plugin._replace_description_field(fm, new_value)
        self.assertIn(new_value, result)
        self.assertNotIn("\\u", result)

    def test_re_measured_length_matches_the_original_value(self):
        fm = "---\nname: x\ndescription: old\nuser-invocable: true\n---\n"
        new_value = "café résumé — naïve, exactly as truncated"
        result = build_copilot_plugin._replace_description_field(fm, new_value)
        remeasured = install_contract._read_skill_description(result)
        self.assertEqual(remeasured, new_value)
        self.assertEqual(len(remeasured), len(new_value))

    def test_render_copilot_skill_md_preserves_non_ascii_in_truncated_description(self):
        # End-to-end: a synthetic over-budget, non-ASCII description
        # truncates without corrupting the surviving accented text.
        long_description = ("café bar baz qux naïve " * 60).strip()
        self.assertGreater(len(long_description), 1024)
        source = (
            "---\n"
            "name: accent-fixture\n"
            f"description: >\n  {long_description}\n"
            "user-invocable: true\n"
            "---\n\n"
            "Body.\n"
        )
        rendered = build_copilot_plugin.render_copilot_skill_md(source)
        rendered_fm, _ = scaffold_mod._split_frontmatter(rendered)
        self.assertNotIn("\\u", rendered_fm)
        self.assertIn("é", rendered_fm)


class PackageCompletenessTests(unittest.TestCase):
    """Slice 113-06 AC5 (package completeness) — every `.github/...` path a
    rendered SKILL.md body or hook `.json` command references must resolve
    to a real path inside the built package. Surfaced by the 113-04
    compliance review: `rewrite_skill_md_paths` rewrites
    `${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py` (the `analyze` skill body)
    to `.github/scripts/spec_lint.py`, but the package shipped no
    `scripts/` tree at all — a rewritten reference pointing at nothing."""

    # Matches a `.github/...` path reference in rendered text, trimmed of a
    # trailing sentence-period a naked (non-code-span) prose mention might
    # carry (no such case exists in the repo TODAY — every real reference is
    # inside a code span/quotes — but stripping it keeps this robust against
    # a future prose-only mention).
    _GITHUB_PATH_RE = re.compile(r'\.github/[A-Za-z0-9_.\-/]+')

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-completeness-"))
        self.out_dir = self.tmp / "copilot"
        code, self.log = _build(self.out_dir)
        self.assertEqual(code, 0, self.log)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _referenced_github_paths(self) -> set:
        refs: set = set()
        skills_dir = self.out_dir / ".github" / "skills"
        for skill_md in skills_dir.glob("*/SKILL.md"):
            text = skill_md.read_text(encoding="utf-8")
            refs.update(m.rstrip(".") for m in self._GITHUB_PATH_RE.findall(text))
        hooks_dir = self.out_dir / ".github" / "hooks"
        for hook_file in hooks_dir.glob("*.json"):
            text = hook_file.read_text(encoding="utf-8")
            refs.update(m.rstrip(".") for m in self._GITHUB_PATH_RE.findall(text))
        return refs

    def test_every_referenced_github_path_resolves_in_the_package(self):
        refs = self._referenced_github_paths()
        self.assertTrue(refs, "no .github/ references found — fixture drifted")
        missing = []
        for ref in sorted(refs):
            target = self.out_dir / ref
            ok = target.is_dir() if ref.endswith("/") else target.is_file()
            if not ok:
                missing.append(ref)
        self.assertEqual(
            missing, [],
            f"rendered .github/ reference(s) resolve to nothing in the "
            f"package: {missing!r}",
        )

    # Explicit per slice 113-06: the analyze skill's rewritten
    # ${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py reference.
    def test_spec_lint_reference_resolves_explicitly(self):
        analyze_skill = self.out_dir / ".github" / "skills" / "analyze" / "SKILL.md"
        text = analyze_skill.read_text(encoding="utf-8")
        # Bug 036: plugin mode names the runtime root, which maps to the
        # package's own `.github/` directory.
        self.assertIn("$JIG_ROOT/scripts/spec_lint.py", text)
        self.assertTrue(
            (self.out_dir / ".github" / "scripts" / "spec_lint.py").is_file()
        )

    def test_migrate_skill_references_still_resolve(self):
        migrate_skill = self.out_dir / ".github" / "skills" / "migrate" / "SKILL.md"
        text = migrate_skill.read_text(encoding="utf-8")
        self.assertIn("$JIG_ROOT/skills/migrate/migrate.py", text)
        self.assertTrue(
            (self.out_dir / ".github" / "skills" / "migrate" / "migrate.py").is_file()
        )

    def test_templates_tree_directory_reference_resolves(self):
        scaffold_skill = (
            self.out_dir / ".github" / "skills" / "scaffold-init" / "SKILL.md"
        )
        text = scaffold_skill.read_text(encoding="utf-8")
        self.assertIn("$JIG_ROOT/templates/", text)
        self.assertTrue((self.out_dir / ".github" / "templates").is_dir())

    def test_every_documented_runtime_path_resolves_in_the_package(self):
        """Bug 036 — the general form of the three checks above.

        `$JIG_ROOT` resolves to the package's `.github/` directory, so every
        `$JIG_ROOT/...` path a shipped skill tells the agent to run must name
        a file that is actually in the package. This is the invariant the
        old project-relative spelling silently violated for all 88 sites."""
        root = self.out_dir / ".github"
        pattern = re.compile(r"\$JIG_ROOT/([A-Za-z0-9_./-]+\.py)")
        missing = []
        for skill_md in (root / "skills").rglob("SKILL.md"):
            for rel in pattern.findall(skill_md.read_text(encoding="utf-8")):
                if not (root / rel).is_file():
                    missing.append(f"{skill_md.relative_to(root)} -> $JIG_ROOT/{rel}")
        self.assertEqual([], missing, "documented helper paths do not resolve")

    def test_jig_root_locator_is_packaged(self):
        """Bug 036 — the fresh-shell fallback for resolving `$JIG_ROOT`."""
        self.assertTrue(
            (self.out_dir / ".github" / "scripts" / "jig_root.py").is_file()
        )

    def test_templates_ship_canonical_so_scaffold_can_render_per_mode(self):
        """Bug 036 — a `.md.template` must ship byte-for-byte from source.

        Templates are rendered by `scaffold.py` at scaffold time, which picks
        the transform from the target project's mode. Pre-rendering here makes
        that dispatch a no-op and burns one mode's spelling into both, which is
        how a plugin-mode project ended up documenting an in-repo path.

        Asserts the positive invariant (identity with the canonical source),
        not merely the absence of two known-bad spellings — a rewrite to some
        third, unrelated path would pass an absence-only check."""
        src_root = REPO_ROOT / "templates"
        packaged_root = self.out_dir / ".github" / "templates"
        if not packaged_root.is_dir():
            self.skipTest("templates not packaged")

        checked = 0
        for packaged in sorted(packaged_root.rglob("*.md.template")):
            src = src_root / packaged.relative_to(packaged_root)
            self.assertTrue(src.is_file(), f"no source for {packaged}")
            self.assertEqual(
                src.read_bytes(),
                packaged.read_bytes(),
                f"{packaged.name} was rendered at package time",
            )
            checked += 1
        self.assertGreater(checked, 0, "no .md.template files were checked")

        # And at least one really does carry a canonical helper reference,
        # so the identity assertion above is guarding something real.
        canonical = [
            p
            for p in packaged_root.rglob("*.md.template")
            if "${CLAUDE_PLUGIN_ROOT}" in p.read_text(encoding="utf-8")
        ]
        self.assertTrue(
            canonical, "no packaged template retains ${CLAUDE_PLUGIN_ROOT}"
        )

    # AC3 — the actually-built package satisfies the static Copilot
    # install-contract validator.
    def test_actually_built_package_validates_clean(self):
        problems = install_contract.validate_copilot_package(self.out_dir)
        self.assertEqual(problems, [])


class CopilotLivePluginDiscoverySmokeTests(unittest.TestCase):
    """Slice 113-07 AC2 — install the committed package into an isolated
    Copilot home and prove a clean working directory discovers jig's declared
    components. The agent assertion uses Copilot's own "available agents" error
    path so it does not require an authenticated model call."""

    @unittest.skipUnless(shutil.which("copilot"), "copilot CLI is not installed")
    def test_installed_committed_package_discovers_skill_agent_and_hooks(self):
        copilot_home = Path(tempfile.mkdtemp(prefix="jig-copilot-home-"))
        work_dir = Path(tempfile.mkdtemp(prefix="jig-copilot-work-"))
        try:
            env = {**os.environ, "COPILOT_HOME": str(copilot_home)}
            install = subprocess.run(
                ["copilot", "plugin", "install", str(REPO_ROOT / "hosts" / "copilot")],
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
            self.assertEqual(install.returncode, 0, install.stderr + install.stdout)
            self.assertIn("Installed", install.stdout)

            skills = subprocess.run(
                ["copilot", "-C", str(work_dir), "skill", "list"],
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
            self.assertEqual(skills.returncode, 0, skills.stderr)
            self.assertIn("spec-workflow", skills.stdout)

            agent = subprocess.run(
                [
                    "copilot",
                    "-C",
                    str(work_dir),
                    "--agent",
                    "definitely-not-a-real-agent",
                    "-p",
                    "Reply exactly READY.",
                    "--allow-all-tools",
                    "--silent",
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
            self.assertNotEqual(agent.returncode, 0)
            agent_output = agent.stdout + agent.stderr
            self.assertIn("jig:reviewer", agent_output)
            self.assertNotIn("failed to load hook", agent_output.lower())
            self.assertNotIn("invalid hook", agent_output.lower())
        finally:
            shutil.rmtree(copilot_home, ignore_errors=True)
            shutil.rmtree(work_dir, ignore_errors=True)


class CopilotPackageBuildSafetyTests(unittest.TestCase):
    """Build safety mirrors Claude/Codex — refuse unsafe output dirs; replace
    atomically."""

    def test_refuses_source_root(self):
        code, _ = _build(REPO_ROOT)
        self.assertNotEqual(code, 0)
        self.assertTrue(
            (REPO_ROOT / "skills" / "scaffold-init" / "SKILL.md").is_file()
        )

    def test_refuses_source_owned_runtime_path(self):
        code, _ = _build(REPO_ROOT / "skills")
        self.assertNotEqual(code, 0)
        self.assertTrue(
            (REPO_ROOT / "skills" / "scaffold-init" / "SKILL.md").is_file()
        )

    def test_refuses_ancestor_of_source_root(self):
        code, _ = _build(REPO_ROOT.parent)
        self.assertNotEqual(code, 0)

    def test_stale_tree_is_fully_replaced_not_merged(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-stale-"))
        try:
            out_dir = tmp / "copilot"
            out_dir.mkdir()
            stale = out_dir / "STALE_LEFTOVER.txt"
            stale.write_text("should be wiped")
            code, log = _build(out_dir)
            self.assertEqual(code, 0, log)
            self.assertFalse(stale.exists(), "stale file survived a rebuild")
            self.assertTrue((out_dir / ".plugin" / "plugin.json").is_file())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_claude_manifest_fails_loudly(self):
        src = Path(tempfile.mkdtemp(prefix="jig-copilot-nomanifest-"))
        tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-nomanifest-out-"))
        try:
            code, log = _build(tmp / "copilot", source_root=src)
            self.assertNotEqual(code, 0)
            self.assertIn("plugin.json", log)
        finally:
            shutil.rmtree(src, ignore_errors=True)
            shutil.rmtree(tmp, ignore_errors=True)


class DefaultOutputTargetTests(unittest.TestCase):
    def test_default_output_dir_is_hosts_copilot(self):
        ns = build_copilot_plugin._build_parser().parse_args([])
        self.assertIsNone(ns.output_dir)
        default = REPO_ROOT / "hosts" / "copilot"
        self.assertEqual(default.name, "copilot")
        self.assertEqual(default.parent.name, "hosts")


class CommittedCopilotPackageTests(unittest.TestCase):
    """The committed hosts/copilot/ package must exist once regenerated."""

    def test_committed_package_present(self):
        pkg = REPO_ROOT / "hosts" / "copilot"
        self.assertTrue(
            (pkg / ".plugin" / "plugin.json").is_file(),
            "committed hosts/copilot manifest missing — run "
            "`python3 scripts/build_host_packages.py`",
        )
        self.assertTrue(
            (pkg / ".github" / "skills" / "scaffold-init" / "SKILL.md").is_file(),
            "committed hosts/copilot skills missing",
        )

    def test_committed_agents_present(self):
        # 113-03: agents/ joins the committed package.
        pkg = REPO_ROOT / "hosts" / "copilot"
        for name in ("architect", "implementer", "reviewer"):
            self.assertTrue(
                (pkg / ".github" / "agents" / f"{name}.agent.md").is_file(),
                f"committed hosts/copilot agent missing: {name} — run "
                "`python3 scripts/build_host_packages.py`",
            )

    def test_committed_advisory_hooks_present(self):
        # 113-04: hooks/ joins the committed package.
        pkg = REPO_ROOT / "hosts" / "copilot"
        for stem in ("jig-git-freshness", "jig-boundary-change-warn",
                     "jig-entry-gate"):
            self.assertTrue(
                (pkg / ".github" / "hooks" / f"{stem}.json").is_file(),
                f"committed hosts/copilot hook missing: {stem} — run "
                "`python3 scripts/build_host_packages.py`",
            )
        self.assertTrue(
            (pkg / ".github" / "hooks" / "scripts" / "jig-git-freshness.sh")
            .is_file()
        )

    def test_committed_enforcing_hooks_present(self):
        # 113-05: the 2 enforcing hooks join the committed package.
        pkg = REPO_ROOT / "hosts" / "copilot"
        for stem in ("jig-spec-gate", "jig-secret-scan"):
            self.assertTrue(
                (pkg / ".github" / "hooks" / f"{stem}.json").is_file(),
                f"committed hosts/copilot hook missing: {stem} — run "
                "`python3 scripts/build_host_packages.py`",
            )
        self.assertTrue(
            (pkg / ".github" / "hooks" / "scripts" / "jig-spec-gate.sh").is_file()
        )

    def test_committed_permissions_floor_present(self):
        # 113-05 AC3 (owner reshape): an enforcing preToolUse hook, not a
        # settings.json file.
        pkg = REPO_ROOT / "hosts" / "copilot"
        floor_hook = pkg / ".github" / "hooks" / "jig-permissions-floor.json"
        self.assertTrue(
            floor_hook.is_file(),
            "committed hosts/copilot permissions floor hook missing — run "
            "`python3 scripts/build_host_packages.py`",
        )
        data = json.loads(floor_hook.read_text())
        self.assertEqual(set(data["hooks"].keys()), {"preToolUse"})
        self.assertTrue(
            (pkg / ".github" / "hooks" / "scripts" / "copilot_permissions_floor.py")
            .is_file()
        )
        self.assertFalse((pkg / ".github" / "copilot").exists())

    def test_no_pre_rendered_instructions_file_committed(self):
        # 113-02 review fix: no pre-rendered instructions file ships.
        pkg = REPO_ROOT / "hosts" / "copilot"
        self.assertFalse((pkg / ".github" / "copilot-instructions.md").exists())

    def test_committed_remaining_advisory_hooks_present(self):
        # 113-06 AC6: the 9 remaining MAPPABLE advisory hooks join the
        # committed package.
        pkg = REPO_ROOT / "hosts" / "copilot"
        for stem in (
            "jig-context-check", "jig-post-edit-verify", "jig-project-orient",
            "jig-semantic-index", "jig-memory-scan", "jig-decision-inflight",
            "jig-task-capture", "jig-decision-capture", "jig-claim-check",
        ):
            self.assertTrue(
                (pkg / ".github" / "hooks" / f"{stem}.json").is_file(),
                f"committed hosts/copilot hook missing: {stem} — run "
                "`python3 scripts/build_host_packages.py`",
            )

    def test_committed_context_check_has_three_event_keys(self):
        # The multi-event merge fix (113-06) — one file, three Copilot event
        # keys, not a last-write-wins collision.
        pkg = REPO_ROOT / "hosts" / "copilot"
        data = json.loads(
            (pkg / ".github" / "hooks" / "jig-context-check.json").read_text()
        )
        self.assertEqual(
            set(data["hooks"].keys()),
            {"preToolUse", "sessionStart", "userPromptSubmitted"},
        )

    def test_committed_scripts_and_templates_present(self):
        # 113-06 AC5: package-completeness — the runtime scripts allowlist
        # and the unrendered templates tree both join the committed package.
        pkg = REPO_ROOT / "hosts" / "copilot"
        self.assertTrue(
            (pkg / ".github" / "scripts" / "spec_lint.py").is_file(),
            "committed hosts/copilot scripts/spec_lint.py missing — run "
            "`python3 scripts/build_host_packages.py`",
        )
        self.assertTrue(
            (pkg / ".github" / "templates" / "CLAUDE.md.template").is_file(),
            "committed hosts/copilot templates/ tree missing — run "
            "`python3 scripts/build_host_packages.py`",
        )

    def test_committed_package_validates_clean(self):
        pkg = REPO_ROOT / "hosts" / "copilot"
        self.assertEqual(install_contract.validate_copilot_package(pkg), [])


if __name__ == "__main__":
    unittest.main()
