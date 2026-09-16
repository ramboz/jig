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

    def test_copilot_still_inherits_bind_paths_from_claude(self):
        # Design decision (113-02, RECONFIRMED 113-04): `bind_paths` stays
        # inherited — no Copilot plugin-root env var was found even after
        # 113-04 re-probed (see CopilotScaffoldRenderer's docstring and
        # `rewrite_hook_command`'s). `translate_hook_protocol` DOES diverge
        # now (113-04) — see `CopilotHookProtocolTranslationTests` below,
        # which supersedes this test's old identity assertion for that
        # method.
        self.assertIs(
            scaffold.CopilotScaffoldRenderer.bind_paths,
            scaffold.ClaudeScaffoldRenderer.bind_paths,
        )

    def test_copilot_translate_hook_protocol_no_longer_identical_to_claude(self):
        # Supersedes the old 113-02 identity assertion: 113-04 gives
        # Copilot its own `translate_hook_protocol` (event-adjacent response
        # schema differs from Claude's — see CopilotHookProtocolTranslationTests).
        self.assertIsNot(
            scaffold.CopilotScaffoldRenderer.translate_hook_protocol,
            scaffold.ClaudeScaffoldRenderer.translate_hook_protocol,
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


class ClaudeToCopilotToolMappingTests(unittest.TestCase):
    """Slice 113-03 (agents) — the Claude->Copilot tool-name vocabulary.

    Verified against the installed `copilot` 1.0.84-9 CLI: the shipped
    `app.js` tool-kind switch statements (`case"view"`/`case"create"`/
    `case"edit"`/`case"glob"`/`case"grep"`/`case"web_fetch":case"fetch"`),
    the ONE shipped built-in custom agent with a genuinely restrictive
    (non-`"*"`) `tools:` allowlist (`definitions/explore.agent.yaml`, which
    lists `bash`/`read_bash`/`stop_bash`/`powershell`/... — never `shell`),
    and the bundled `copilot-sdk/docs/agent-author.md` ("Modify ... using
    `edit` or `create` tools"). `shell` is a DIFFERENT, coarser vocabulary —
    confirmed via `copilot --help`'s own `--allow-tool='shell(git:*)'`
    example — for the CLI's session-level permission-category flags, not
    this custom-agent frontmatter `tools:` allowlist; using it here would be
    an unverified guess dressed as a citation."""

    def test_read_maps_to_view(self):
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS["Read"], "view"
        )

    def test_glob_maps_to_glob(self):
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS["Glob"], "glob"
        )

    def test_grep_maps_to_grep(self):
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS["Grep"], "grep"
        )

    def test_write_maps_to_create(self):
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS["Write"], "create"
        )

    def test_edit_maps_to_edit(self):
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS["Edit"], "edit"
        )

    def test_bash_maps_to_bash_not_shell(self):
        # Deliberate correction vs. an unverified "Bash -> shell" guess —
        # see the class docstring.
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS["Bash"], "bash"
        )

    def test_websearch_maps_to_fetch(self):
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS["WebSearch"],
            "fetch",
        )

    def test_copilot_tool_names_maps_a_list_preserving_order(self):
        result = scaffold.CopilotScaffoldRenderer.copilot_tool_names(
            ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebSearch"]
        )
        self.assertEqual(
            result, ["view", "create", "edit", "bash", "glob", "grep", "fetch"]
        )

    def test_copilot_tool_names_empty_list_is_a_no_op(self):
        self.assertEqual(scaffold.CopilotScaffoldRenderer.copilot_tool_names([]), [])

    def test_unmapped_tool_raises(self):
        with self.assertRaises(scaffold.CopilotAgentToolError):
            scaffold.CopilotScaffoldRenderer.copilot_tool_names(["NotARealClaudeTool"])


class RenderCopilotAgentTests(unittest.TestCase):
    """Slice 113-03 (agents) — `CopilotScaffoldRenderer.render_copilot_agent`
    against a synthetic fixture (isolates the render from source-agent
    drift; real 3-agent end-to-end coverage lives in
    scripts/test_build_copilot_plugin.py)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-agent-render-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_fixture(self, tools):
        text = (
            "---\n"
            "name: fixture-agent\n"
            "description: A fixture agent for render tests.\n"
            "tools:\n"
            + "".join(f"  - {t}\n" for t in tools)
            + "---\n\n"
            "You are a fixture agent.\n"
            "Second body line.\n"
        )
        path = self.tmp / "fixture-agent.md"
        path.write_text(text)
        return path

    def test_renders_name_description_and_mapped_tools(self):
        path = self._write_fixture(["Read", "Glob", "Grep"])
        rendered = scaffold.CopilotScaffoldRenderer.render_copilot_agent(path)
        fm, body = scaffold._split_frontmatter(rendered)
        self.assertIn("name: fixture-agent", fm)
        self.assertIn('description: "A fixture agent for render tests."', fm)
        self.assertIn("tools:\n  - view\n  - glob\n  - grep\n", fm)
        self.assertIn("You are a fixture agent.", body)

    def test_never_emits_a_model_field(self):
        path = self._write_fixture(["Read"])
        rendered = scaffold.CopilotScaffoldRenderer.render_copilot_agent(path)
        fm, _ = scaffold._split_frontmatter(rendered)
        self.assertNotIn("model:", fm)

    def test_body_ships_verbatim_from_source(self):
        # `.strip()` on both sides: the one blank line separating the closing
        # frontmatter fence from the body (present in both the fixture and
        # the render, matching every real `agents/*.md` source file's own
        # shape) is formatting, not body content to pin exactly.
        path = self._write_fixture(["Read"])
        rendered = scaffold.CopilotScaffoldRenderer.render_copilot_agent(path)
        _, body = scaffold._split_frontmatter(rendered)
        self.assertEqual(
            body.strip(), "You are a fixture agent.\nSecond body line."
        )

    def test_raises_on_an_unmapped_source_tool(self):
        path = self._write_fixture(["NotARealClaudeTool"])
        with self.assertRaises(scaffold.CopilotAgentToolError):
            scaffold.CopilotScaffoldRenderer.render_copilot_agent(path)


class CopilotAgentFileNameTests(unittest.TestCase):
    """Slice 113-03 — the committed file shape (spike 113-01 AC3:
    `.github/agents/<name>.agent.md`), bare-named (no `jig-` prefix, unlike
    Codex's global-namespace `jig-<role>.toml`) since Copilot agents/skills
    both ship bare-named under the plugin's own `.github/` tree already
    (113-02 ships skills this way)."""

    def test_agent_file_name_has_agent_md_suffix(self):
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.copilot_agent_file_name("architect.md"),
            "architect.agent.md",
        )

    def test_agent_file_name_has_no_jig_prefix(self):
        result = scaffold.CopilotScaffoldRenderer.copilot_agent_file_name(
            "reviewer.md"
        )
        self.assertFalse(result.startswith("jig-"))


class ClaudeToCopilotEventMappingTests(unittest.TestCase):
    """Slice 113-04 (advisory-hooks) AC1 — the Claude PascalCase -> Copilot
    camelCase `HookType` event map, grounded against the shipped CLI's
    `schemas/api.schema.json` `HookType` enum (spike 113-01 AC3)."""

    def test_session_start_maps_to_camel_case(self):
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.copilot_event_name("SessionStart"),
            "sessionStart",
        )

    def test_post_tool_use_maps_to_camel_case(self):
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.copilot_event_name("PostToolUse"),
            "postToolUse",
        )

    def test_pre_tool_use_maps_to_camel_case(self):
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.copilot_event_name("PreToolUse"),
            "preToolUse",
        )

    def test_stop_maps_to_agent_stop(self):
        # Claude's "Stop" (main agent finished responding) is the closest
        # confirmed Copilot analogue to `agentStop` in the shipped HookType
        # enum — there is no Copilot event literally named "stop".
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.copilot_event_name("Stop"), "agentStop"
        )

    def test_unmapped_event_raises(self):
        with self.assertRaises(scaffold.CopilotHookEventError):
            scaffold.CopilotScaffoldRenderer.copilot_event_name("NotARealClaudeEvent")

    def test_every_mapped_value_is_a_confirmed_copilot_hooktype(self):
        # Closed-world check against the exact 17-member enum spike 113-01
        # AC3 read out of the shipped `schemas/api.schema.json` — every
        # mapped-TO value must be a real Copilot event, not a typo.
        confirmed_hooktypes = {
            "preToolUse", "preMcpToolCall", "postToolUse", "postToolUseFailure",
            "userPromptSubmitted", "userPromptTransformed", "sessionStart",
            "sessionEnd", "postResult", "prePRDescription", "errorOccurred",
            "agentStop", "subagentStart", "subagentStop", "preCompact",
            "permissionRequest", "notification",
        }
        for claude_event, copilot_event in (
            scaffold.CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_EVENTS.items()
        ):
            self.assertIn(
                copilot_event, confirmed_hooktypes,
                f"{claude_event} -> {copilot_event!r} is not a confirmed HookType",
            )


class CopilotHookProtocolTranslationTests(unittest.TestCase):
    """Slice 113-04 AC1/AC3 — `CopilotScaffoldRenderer.translate_hook_protocol`
    (response-schema half), grounded against the shipped
    `copilot-sdk/types.d.ts` `HookOutput` interfaces."""

    def setUp(self):
        self.renderer = scaffold.CopilotScaffoldRenderer(
            plugin=Path("."), target=Path(".")
        )

    def test_additional_context_maps_to_additionalContext(self):
        result = self.renderer.translate_hook_protocol(
            {"continue": True, "additional_context": "nudge text"}
        )
        self.assertEqual(result, {"additionalContext": "nudge text"})

    def test_continue_key_is_dropped_not_translated(self):
        # AC3 fail-open / AC1 shape: no Copilot HookOutput interface carries
        # a boolean `continue` field, so it is dropped rather than guessed.
        result = self.renderer.translate_hook_protocol({"continue": True})
        self.assertNotIn("continue", result)
        self.assertEqual(result, {})

    def test_block_reason_maps_to_deny_permission_decision(self):
        result = self.renderer.translate_hook_protocol(
            {"block_reason": "denied for cause"}
        )
        self.assertEqual(
            result,
            {
                "permissionDecision": "deny",
                "permissionDecisionReason": "denied for cause",
            },
        )

    def test_empty_logical_result_translates_to_empty_dict(self):
        self.assertEqual(self.renderer.translate_hook_protocol({}), {})

    def test_a_translated_advisory_hook_emits_copilot_shaped_json(self):
        # AC1's own acceptance wording: "a test asserts a translated
        # advisory hook emits Copilot-shaped JSON" — exactly what jig's 3
        # advisory hooks print (`{'continue': True, 'additionalContext': ...}`
        # is the CLAUDE-shaped literal; the LOGICAL/host-neutral form is
        # `{'continue': True, 'additional_context': ...}`).
        #
        # Unit-contract test ONLY — this calls the method directly. It does
        # NOT prove a real shipped advisory hook's stdout is transformed
        # this way today (it isn't: `copilot_hook_adapter.py` forwards
        # child stdout verbatim; nothing calls this method at runtime yet —
        # see the method's own HONESTY NOTE). For what a real shipped hook
        # actually emits through the adapter, see
        # `test_copilot_hook_adapter.ShippedAdvisoryOutputThroughAdapterTests`.
        logical = {"continue": True, "additional_context": "branch is behind"}
        copilot_shaped = self.renderer.translate_hook_protocol(logical)
        self.assertEqual(copilot_shaped, {"additionalContext": "branch is behind"})
        # And it must be valid, round-trippable JSON.
        self.assertEqual(
            json.loads(json.dumps(copilot_shaped)), copilot_shaped
        )

    def test_claude_translate_hook_protocol_unaffected(self):
        # Regression guard: Copilot's override must not leak onto Claude's
        # own method (each host answers `self.translate_hook_protocol`
        # through its own MRO).
        claude_renderer = scaffold.ClaudeScaffoldRenderer(
            plugin=Path("."), target=Path(".")
        )
        result = claude_renderer.translate_hook_protocol(
            {"continue": True, "additional_context": "nudge text"}
        )
        self.assertEqual(
            result, {"continue": True, "additionalContext": "nudge text"}
        )

    def test_codex_translate_hook_protocol_unaffected(self):
        codex_renderer = scaffold.CodexScaffoldRenderer(
            plugin=Path("."), target=Path(".")
        )
        result = codex_renderer.translate_hook_protocol(
            {"continue": True, "additional_context": "nudge text"}
        )
        self.assertEqual(
            result, {"continue": True, "additionalContext": "nudge text"}
        )


class CopilotHookMatcherTranslationTests(unittest.TestCase):
    """Slice 113-04 — hook `matcher` tool-name translation (distinct from
    113-03's agent `tools:` vocabulary — see `HOOK_MATCHER_TOOL_MAP`'s
    docstring)."""

    def test_edit_write_multiedit_matcher_translates_and_dedupes(self):
        result = scaffold.CopilotScaffoldRenderer.copilot_hook_matcher(
            "Edit|Write|MultiEdit"
        )
        self.assertEqual(result, "edit|create")

    def test_single_token_matcher(self):
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.copilot_hook_matcher("Edit"), "edit"
        )

    def test_unmapped_token_passes_through_unchanged(self):
        # "Task"/"Skill" have no Copilot tool-call analogue (113-05's
        # mapped-or-unmappable inventory records them UNMAPPABLE, and this
        # builder does not render a hook file for them at all — see
        # `build_copilot_plugin._JIG_HOOK_INVENTORY`) — an unmapped token
        # passes through rather than raising.
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.copilot_hook_matcher("Task"), "Task"
        )

    def test_read_matcher_maps_to_view(self):
        # 113-05 bug fix: jig-context-check.sh's PreToolUse matcher is the
        # bare string "Read" — without this mapping the rendered matcher
        # would be the literal, never-matching "Read" (Copilot's own tool
        # name is "view", per 113-03's `CLAUDE_TO_COPILOT_TOOLS`).
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.copilot_hook_matcher("Read"), "view"
        )


class CopilotHookCommandPathRewriteTests(unittest.TestCase):
    """Slice 113-04 AC4 — hook-command half of the `${CLAUDE_PLUGIN_ROOT}`
    path rewrite (best-hypothesis, plugin-root-relative; see
    `rewrite_hook_command`'s docstring for the residual)."""

    def test_rewrites_plugin_hook_script_prefix(self):
        result = scaffold.CopilotScaffoldRenderer.rewrite_hook_command(
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-git-freshness.sh"
        )
        self.assertEqual(
            result, "bash .github/hooks/scripts/jig-git-freshness.sh"
        )

    def test_command_with_no_plugin_root_prefix_is_unchanged(self):
        result = scaffold.CopilotScaffoldRenderer.rewrite_hook_command(
            "python3 -c 'print(1)'"
        )
        self.assertEqual(result, "python3 -c 'print(1)'")

    def test_claude_rewrite_hook_command_unaffected(self):
        result = scaffold.ClaudeScaffoldRenderer.rewrite_hook_command(
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-git-freshness.sh"
        )
        self.assertEqual(
            result,
            "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/jig-git-freshness.sh",
        )


class BuildHookCommandInputAdapterTests(unittest.TestCase):
    """Slice 113-04 AC1 (input-payload half) — `build_hook_command` wraps
    the path-rewritten command through `copilot_hook_adapter.py`."""

    def test_wraps_command_through_the_adapter_with_event_and_script_path(self):
        result = scaffold.CopilotScaffoldRenderer.build_hook_command(
            "SessionStart",
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-git-freshness.sh",
        )
        self.assertEqual(
            result,
            "python3 .github/hooks/scripts/copilot_hook_adapter.py "
            'SessionStart ".github/hooks/scripts/jig-git-freshness.sh"',
        )

    def test_different_event_and_script_are_both_reflected(self):
        result = scaffold.CopilotScaffoldRenderer.build_hook_command(
            "PostToolUse",
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-entry-gate.sh",
        )
        self.assertEqual(
            result,
            "python3 .github/hooks/scripts/copilot_hook_adapter.py "
            'PostToolUse ".github/hooks/scripts/jig-entry-gate.sh"',
        )

    def test_script_path_is_quoted_against_a_hypothetical_space(self):
        # Arch review fix: a space in the script path must not split into
        # extra shell words.
        result = scaffold.CopilotScaffoldRenderer.build_hook_command(
            "PostToolUse",
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig with space.sh",
        )
        self.assertIn('".github/hooks/scripts/jig with space.sh"', result)

    def test_adapter_path_matches_the_shipped_filename_constant(self):
        result = scaffold.CopilotScaffoldRenderer.build_hook_command(
            "PostToolUse",
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-entry-gate.sh",
        )
        self.assertIn(
            scaffold.CopilotScaffoldRenderer.COPILOT_HOOK_ADAPTER_FILENAME, result
        )

    # 113-05 — the enforcing-vs-advisory mode switch.
    def test_default_mode_is_advisory_with_no_enforce_flag(self):
        result = scaffold.CopilotScaffoldRenderer.build_hook_command(
            "PreToolUse",
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-spec-gate.sh",
        )
        self.assertNotIn("--enforce", result)
        self.assertEqual(
            result,
            "python3 .github/hooks/scripts/copilot_hook_adapter.py "
            'PreToolUse ".github/hooks/scripts/jig-spec-gate.sh"',
        )

    def test_enforcing_true_inserts_the_enforce_flag_before_the_event(self):
        result = scaffold.CopilotScaffoldRenderer.build_hook_command(
            "PreToolUse",
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-spec-gate.sh",
            enforcing=True,
        )
        self.assertEqual(
            result,
            "python3 .github/hooks/scripts/copilot_hook_adapter.py --enforce "
            'PreToolUse ".github/hooks/scripts/jig-spec-gate.sh"',
        )

    def test_enforcing_flag_uses_the_shared_constant(self):
        result = scaffold.CopilotScaffoldRenderer.build_hook_command(
            "PreToolUse",
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-secret-scan.sh",
            enforcing=True,
        )
        self.assertIn(
            scaffold.CopilotScaffoldRenderer.COPILOT_HOOK_ADAPTER_ENFORCE_FLAG,
            result,
        )


class CopilotSkillBodyPathRewriteTests(unittest.TestCase):
    """Slice 113-04 AC4 — skill-body half of the `${CLAUDE_PLUGIN_ROOT}`
    path rewrite, closing the gap 113-02 documented and deferred."""

    def test_rewrites_a_skills_path_reference(self):
        body = 'python3 "${CLAUDE_PLUGIN_ROOT}/skills/spec-workflow/workflow.py" new'
        result = scaffold.CopilotScaffoldRenderer.rewrite_skill_md_paths(body)
        self.assertEqual(
            result, 'python3 ".github/skills/spec-workflow/workflow.py" new'
        )

    def test_rewrites_a_bare_scripts_path_reference(self):
        body = '${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py'
        result = scaffold.CopilotScaffoldRenderer.rewrite_skill_md_paths(body)
        self.assertEqual(result, ".github/scripts/spec_lint.py")

    def test_rewrites_a_hooks_scripts_path_reference(self):
        body = '${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-git-freshness.sh'
        result = scaffold.CopilotScaffoldRenderer.rewrite_skill_md_paths(body)
        self.assertEqual(result, ".github/hooks/scripts/jig-git-freshness.sh")

    def test_body_with_no_plugin_root_mention_is_byte_identical(self):
        body = "# spec-workflow\n\nNo runtime paths mentioned here.\n"
        self.assertEqual(
            scaffold.CopilotScaffoldRenderer.rewrite_skill_md_paths(body), body
        )

    def test_multiple_mentions_all_rewritten(self):
        body = (
            'python3 "${CLAUDE_PLUGIN_ROOT}/skills/a/a.py"\n'
            'python3 "${CLAUDE_PLUGIN_ROOT}/skills/b/b.py"\n'
        )
        result = scaffold.CopilotScaffoldRenderer.rewrite_skill_md_paths(body)
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", result)
        self.assertIn(".github/skills/a/a.py", result)
        self.assertIn(".github/skills/b/b.py", result)

    def test_claude_rewrite_skill_md_paths_unaffected(self):
        body = '${CLAUDE_PLUGIN_ROOT}/skills/spec-workflow/workflow.py'
        result = scaffold.ClaudeScaffoldRenderer.rewrite_skill_md_paths(body)
        self.assertEqual(
            result, "${CLAUDE_PROJECT_DIR}/.claude/skills/jig-spec-workflow/workflow.py"
        )


class RenderCopilotHookFileTests(unittest.TestCase):
    """Slice 113-04 AC1/AC2 (SCHEMA CORRECTED 113-05) —
    `scaffold.render_copilot_hook_file`, the source-hooks.json ->
    one-Copilot-hook-file extraction/render, in the AUTHORITATIVE
    `{"version": 1, "hooks": {event: [<flat entry>]}}` on-disk shape (NOT
    Claude's nested `{event: [{matcher?, hooks:[...]}]}` shape 113-04
    shipped by mistake — see `render_copilot_hook_file`'s own docstring)."""

    def _source_hooks(self):
        return {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Edit|Write|MultiEdit",
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
                                    "jig-spec-gate.sh"
                                ),
                                "timeout": 5,
                            },
                            {
                                "type": "command",
                                "command": (
                                    "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
                                    "jig-secret-scan.sh"
                                ),
                                "timeout": 5,
                            },
                        ],
                    },
                    {
                        "matcher": "Read",
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
                                    "jig-context-check.sh"
                                ),
                                "timeout": 5,
                            }
                        ],
                    },
                ],
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
                                    "jig-git-freshness.sh"
                                ),
                                "timeout": 10,
                            }
                        ]
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "Edit|Write|MultiEdit",
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
                                    "jig-post-edit-verify.sh"
                                ),
                                "timeout": 5,
                            },
                            {
                                "type": "command",
                                "command": (
                                    "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
                                    "jig-boundary-change-warn.sh"
                                ),
                                "timeout": 5,
                            },
                            {
                                "type": "command",
                                "command": (
                                    "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
                                    "jig-entry-gate.sh"
                                ),
                                "timeout": 5,
                            },
                        ],
                    }
                ],
            }
        }

    def test_top_level_shape_has_version_and_hooks_keys(self):
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "SessionStart",
            "jig-git-freshness.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        self.assertEqual(set(payload.keys()), {"version", "hooks"})
        self.assertEqual(payload["version"], 1)

    def test_session_start_hook_renders_keyed_by_camel_case_event(self):
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "SessionStart",
            "jig-git-freshness.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        self.assertEqual(set(payload["hooks"].keys()), {"sessionStart"})

    def test_session_start_hook_entry_is_flat_not_nested(self):
        # The authoritative shape has NO Claude-style nested `hooks:[...]`
        # array inside an entry — each entry IS the hook, flat.
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "SessionStart",
            "jig-git-freshness.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        entry = payload["hooks"]["sessionStart"][0]
        self.assertNotIn("hooks", entry)
        self.assertEqual(entry["type"], "command")
        self.assertIn("bash", entry)

    def test_session_start_hook_has_no_matcher(self):
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "SessionStart",
            "jig-git-freshness.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        entry = payload["hooks"]["sessionStart"][0]
        self.assertNotIn("matcher", entry)

    def test_session_start_hook_command_routes_through_the_input_adapter(self):
        # 113-04 AC1 follow-up: the rendered command now invokes
        # `copilot_hook_adapter.py <event> <script>` instead of the bare
        # path-rewritten script, so Copilot's camelCase stdin JSON is
        # translated before the (unmodified) jig script sees it.
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "SessionStart",
            "jig-git-freshness.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        command = payload["hooks"]["sessionStart"][0]["bash"]
        self.assertEqual(
            command,
            "python3 .github/hooks/scripts/copilot_hook_adapter.py "
            'SessionStart ".github/hooks/scripts/jig-git-freshness.sh"',
        )

    def test_session_start_hook_preserves_timeout_as_timeout_sec(self):
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "SessionStart",
            "jig-git-freshness.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        entry = payload["hooks"]["sessionStart"][0]
        self.assertEqual(entry["timeoutSec"], 10)
        self.assertNotIn("timeout", entry)

    def test_extracts_only_the_named_script_from_a_shared_matcher_entry(self):
        # boundary-change-warn and entry-gate share the SAME source entry
        # (and jig-post-edit-verify.sh, which is out of scope) — each
        # extraction must yield exactly its own single flat entry.
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "PostToolUse",
            "jig-boundary-change-warn.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        entries = payload["hooks"]["postToolUse"]
        self.assertEqual(len(entries), 1)
        self.assertIn("jig-boundary-change-warn.sh", entries[0]["bash"])

    def test_post_tool_use_matcher_is_translated_to_copilot_tool_names(self):
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "PostToolUse",
            "jig-entry-gate.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        self.assertEqual(payload["hooks"]["postToolUse"][0]["matcher"], "edit|create")

    def test_pre_tool_use_read_matcher_translates_to_view(self):
        # 113-05 bug fix (see CopilotHookMatcherTranslationTests) exercised
        # end-to-end through the full render.
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "PreToolUse",
            "jig-context-check.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        self.assertEqual(payload["hooks"]["preToolUse"][0]["matcher"], "view")

    def test_pre_tool_use_shared_matcher_extracts_only_spec_gate(self):
        # jig-spec-gate.sh and jig-secret-scan.sh share ONE source entry
        # (Edit|Write|MultiEdit) — extracting by script name must not leak
        # the sibling hook in.
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "PreToolUse",
            "jig-spec-gate.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        entries = payload["hooks"]["preToolUse"]
        self.assertEqual(len(entries), 1)
        self.assertIn("jig-spec-gate.sh", entries[0]["bash"])
        self.assertNotIn("jig-secret-scan.sh", entries[0]["bash"])

    def test_missing_script_returns_none(self):
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "PostToolUse",
            "jig-not-a-real-hook.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        self.assertIsNone(payload)

    def test_missing_event_returns_none(self):
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "Stop",
            "jig-git-freshness.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        self.assertIsNone(payload)

    def test_output_is_valid_json(self):
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "SessionStart",
            "jig-git-freshness.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        self.assertEqual(json.loads(json.dumps(payload)), payload)

    # 113-05 — the enforcing-vs-advisory mode switch, exercised through the
    # full render (not just `build_hook_command` in isolation).
    def test_advisory_default_does_not_enforce(self):
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "SessionStart",
            "jig-git-freshness.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
        )
        self.assertNotIn(
            "--enforce", payload["hooks"]["sessionStart"][0]["bash"]
        )

    def test_enforcing_true_renders_the_enforce_flag(self):
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "PreToolUse",
            "jig-spec-gate.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
            enforcing=True,
        )
        command = payload["hooks"]["preToolUse"][0]["bash"]
        self.assertIn("--enforce", command)
        self.assertIn("jig-spec-gate.sh", command)

    def test_enforcing_secret_scan_also_renders_the_enforce_flag(self):
        payload = scaffold.render_copilot_hook_file(
            self._source_hooks(),
            "PreToolUse",
            "jig-secret-scan.sh",
            renderer_cls=scaffold.CopilotScaffoldRenderer,
            enforcing=True,
        )
        command = payload["hooks"]["preToolUse"][0]["bash"]
        self.assertIn("--enforce", command)
        self.assertIn("jig-secret-scan.sh", command)


class RenderPermissionsFloorHookTests(unittest.TestCase):
    """Slice 113-05 AC3 (owner reshape) —
    `CopilotScaffoldRenderer.render_permissions_floor_hook`: the
    destructive-command permissions floor renders as a REAL enforcing
    `preToolUse` hook, not a settings.json file (an earlier version of this
    slice rendered `.github/copilot/settings.json` — the owner corrected
    it: Copilot has no persistent, repo-committable tool-deny mechanism)."""

    def test_top_level_shape_has_version_and_hooks_keys(self):
        payload = scaffold.CopilotScaffoldRenderer.render_permissions_floor_hook()
        self.assertEqual(set(payload.keys()), {"version", "hooks"})
        self.assertEqual(payload["version"], 1)

    def test_keyed_by_pre_tool_use_camel_case(self):
        payload = scaffold.CopilotScaffoldRenderer.render_permissions_floor_hook()
        self.assertEqual(set(payload["hooks"].keys()), {"preToolUse"})

    def test_matcher_is_the_bash_tool_name(self):
        payload = scaffold.CopilotScaffoldRenderer.render_permissions_floor_hook()
        entry = payload["hooks"]["preToolUse"][0]
        self.assertEqual(
            entry["matcher"], scaffold.CopilotScaffoldRenderer.CLAUDE_TO_COPILOT_TOOLS["Bash"]
        )
        self.assertEqual(entry["matcher"], "bash")

    def test_entry_is_flat_with_type_command(self):
        payload = scaffold.CopilotScaffoldRenderer.render_permissions_floor_hook()
        entry = payload["hooks"]["preToolUse"][0]
        self.assertNotIn("hooks", entry)  # flat, no Claude-style nesting
        self.assertEqual(entry["type"], "command")

    def test_command_routes_through_the_adapter_in_enforcing_mode(self):
        payload = scaffold.CopilotScaffoldRenderer.render_permissions_floor_hook()
        command = payload["hooks"]["preToolUse"][0]["bash"]
        self.assertIn(
            scaffold.CopilotScaffoldRenderer.COPILOT_HOOK_ADAPTER_ENFORCE_FLAG,
            command,
        )
        self.assertIn(
            scaffold.CopilotScaffoldRenderer.COPILOT_PERMISSIONS_FLOOR_FILENAME,
            command,
        )
        self.assertIn("PreToolUse", command)

    def test_command_targets_the_floor_script_under_hooks_scripts(self):
        payload = scaffold.CopilotScaffoldRenderer.render_permissions_floor_hook()
        command = payload["hooks"]["preToolUse"][0]["bash"]
        self.assertIn(
            ".github/hooks/scripts/copilot_permissions_floor.py", command
        )

    def test_has_a_timeout(self):
        payload = scaffold.CopilotScaffoldRenderer.render_permissions_floor_hook()
        entry = payload["hooks"]["preToolUse"][0]
        self.assertIn("timeoutSec", entry)

    def test_output_is_valid_json(self):
        payload = scaffold.CopilotScaffoldRenderer.render_permissions_floor_hook()
        self.assertEqual(json.loads(json.dumps(payload)), payload)

    def test_no_raw_claude_plugin_root_leaks_through(self):
        payload = scaffold.CopilotScaffoldRenderer.render_permissions_floor_hook()
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
