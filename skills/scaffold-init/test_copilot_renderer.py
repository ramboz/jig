"""
Tests for `CopilotScaffoldRenderer` + host-renderer dispatch — slice 113-02
(renderer-and-skeleton).

Covers:
  - AC #1: `CopilotScaffoldRenderer(HostRenderer)` exists and
    `renderer_for_host("copilot")` / `read_host_renderer` resolve it;
    `claude`/`codex`/unknown-host resolution is unchanged.
  - AC #2: the loader-compat invariant — `loader_safe_description` returns a
    description unchanged when it already fits Copilot's 1024-character
    skill-loader limit, and truncates (without ever exceeding the limit) when
    it does not; `assert_namespace_safe_name` raises on a `:`-bearing name and
    is a no-op otherwise.
  - 113-02 review fix (craft/arch): `agent_frontmatter_value` is a generic
    frontmatter accessor, not Codex-specific — it lives on `HostRenderer` and
    every host renderer inherits it unchanged (no cross-host reach-into).
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scaffold  # noqa: E402


class RendererDispatchTests(unittest.TestCase):
    """AC #1 — dispatch resolves copilot; claude/codex/unknown unchanged."""

    def test_renderer_for_host_copilot_resolves(self):
        self.assertIs(
            scaffold.renderer_for_host("copilot"), scaffold.CopilotScaffoldRenderer
        )

    def test_copilot_renderer_is_a_host_renderer(self):
        self.assertTrue(
            issubclass(scaffold.CopilotScaffoldRenderer, scaffold.HostRenderer)
        )

    def test_copilot_renderer_name_attribute(self):
        self.assertEqual(scaffold.CopilotScaffoldRenderer.name, "copilot")

    def test_renderer_for_host_claude_unchanged(self):
        self.assertIs(
            scaffold.renderer_for_host("claude"), scaffold.ClaudeScaffoldRenderer
        )

    def test_renderer_for_host_codex_unchanged(self):
        self.assertIs(
            scaffold.renderer_for_host("codex"), scaffold.CodexScaffoldRenderer
        )

    def test_renderer_for_host_unknown_falls_back_to_claude(self):
        self.assertIs(
            scaffold.renderer_for_host("some-unknown-host"),
            scaffold.ClaudeScaffoldRenderer,
        )

    def test_copilot_inherits_hook_protocol_and_bind_paths_from_claude(self):
        # Design decision (113-02): the Copilot renderer does NOT override
        # translate_hook_protocol or bind_paths — neither is exercised until
        # 113-04/05, and inventing a shape now would just be unwound later.
        self.assertIs(
            scaffold.CopilotScaffoldRenderer.translate_hook_protocol,
            scaffold.ClaudeScaffoldRenderer.translate_hook_protocol,
        )
        self.assertIs(
            scaffold.CopilotScaffoldRenderer.bind_paths,
            scaffold.ClaudeScaffoldRenderer.bind_paths,
        )


class ReadHostRendererResolvesCopilotTests(unittest.TestCase):
    """AC #1 — `read_host_renderer` (bug 023's accessor) recognizes "copilot"
    now that it is registered in `_HOST_RENDERERS`."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-hostrenderer-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reads_copilot_host_renderer_claim(self):
        (self.tmp / "scaffold.json").write_text(
            json.dumps({"host_renderer": "copilot"})
        )
        self.assertEqual(scaffold.read_host_renderer(self.tmp), "copilot")

    def test_unrecognised_host_still_collapses_to_none(self):
        (self.tmp / "scaffold.json").write_text(
            json.dumps({"host_renderer": "not-a-real-host"})
        )
        self.assertIsNone(scaffold.read_host_renderer(self.tmp))


class LoaderSafeDescriptionTests(unittest.TestCase):
    """AC #2 — the loader-compat invariant's length half."""

    def test_short_description_returned_unchanged(self):
        text = "a short description"
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.loader_safe_description(text), text
        )

    def test_exactly_at_limit_returned_unchanged(self):
        text = "x" * 1024
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.loader_safe_description(text), text
        )

    def test_over_limit_is_truncated_to_the_limit(self):
        text = "word " * 300  # well over 1024 chars
        result = scaffold.CopilotScaffoldRenderer.loader_safe_description(text)
        self.assertLessEqual(len(result), 1024)
        self.assertNotEqual(result, text)

    def test_truncated_result_never_exceeds_limit_across_lengths(self):
        for extra in (1, 2, 50, 500, 5000):
            text = "d" * (1024 + extra)
            result = scaffold.CopilotScaffoldRenderer.loader_safe_description(text)
            self.assertLessEqual(
                len(result), 1024, f"failed for source length {len(text)}"
            )

    def test_truncated_result_preserves_a_leading_prefix_of_the_source(self):
        text = ("alpha bravo charlie delta echo foxtrot " * 40).strip()
        self.assertGreater(len(text), 1024)
        result = scaffold.CopilotScaffoldRenderer.loader_safe_description(text)
        self.assertTrue(text.startswith(result.split(" (")[0]))


class NamespaceSafeNameTests(unittest.TestCase):
    """AC #2 — the loader-compat invariant's namespace-safe-name half."""

    def test_colon_free_name_is_a_no_op(self):
        # Must not raise.
        scaffold.CopilotScaffoldRenderer.assert_namespace_safe_name("memory-sync")

    def test_colon_bearing_name_raises(self):
        with self.assertRaises(scaffold.CopilotSkillNameError):
            scaffold.CopilotScaffoldRenderer.assert_namespace_safe_name("jig:memory-sync")


class AgentFrontmatterValueHoistedOntoHostRendererTests(unittest.TestCase):
    """113-02 review fix (arch + craft) — `agent_frontmatter_value` is a
    generic `key: value` frontmatter-line accessor, not a Codex-specific
    concern. It lives on `HostRenderer` (the shared base) so
    `CopilotScaffoldRenderer` reads it without reaching into
    `CodexScaffoldRenderer`, and `CodexScaffoldRenderer` keeps working via
    ordinary inheritance — not a private per-subclass copy."""

    _FRONTMATTER = 'name: memory-sync\ndescription: "quoted value"\n'

    def test_lives_on_host_renderer(self):
        self.assertTrue(hasattr(scaffold.HostRenderer, "agent_frontmatter_value"))

    def test_extracts_a_simple_field(self):
        self.assertEqual(
            scaffold.HostRenderer.agent_frontmatter_value(
                self._FRONTMATTER, "name", ""
            ),
            "memory-sync",
        )

    def test_strips_surrounding_quotes(self):
        self.assertEqual(
            scaffold.HostRenderer.agent_frontmatter_value(
                self._FRONTMATTER, "description", ""
            ),
            "quoted value",
        )

    def test_falls_back_to_default_when_key_absent(self):
        self.assertEqual(
            scaffold.HostRenderer.agent_frontmatter_value(
                self._FRONTMATTER, "missing-key", "fallback"
            ),
            "fallback",
        )

    def test_codex_renderer_inherits_it_unchanged(self):
        # No private CodexScaffoldRenderer copy — the same bound function,
        # resolved via ordinary MRO inheritance.
        self.assertIs(
            scaffold.CodexScaffoldRenderer.agent_frontmatter_value,
            scaffold.HostRenderer.agent_frontmatter_value,
        )

    def test_copilot_renderer_inherits_it_unchanged(self):
        self.assertIs(
            scaffold.CopilotScaffoldRenderer.agent_frontmatter_value,
            scaffold.HostRenderer.agent_frontmatter_value,
        )

    def test_codex_agent_rendering_still_resolves_the_field(self):
        # Regression guard for the actual call site (render_codex_agent_toml
        # calls `cls.agent_frontmatter_value(...)` inside a classmethod) —
        # proves the hoist doesn't change behavior at jig's one production
        # caller.
        self.assertEqual(
            scaffold.CodexScaffoldRenderer.agent_frontmatter_value(
                self._FRONTMATTER, "name", "fallback-role"
            ),
            "memory-sync",
        )


if __name__ == "__main__":
    unittest.main()
