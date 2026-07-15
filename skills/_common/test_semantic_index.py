import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import semantic_index
from semantic_index import (
    ActivationState,
    CommandProvider,
    ProviderMetadata,
    activate,
    load_state,
    record_telemetry,
    write_state,
)


class FakeProvider:
    def __init__(self, name="fake", profile="public", detected=True, status="ready"):
        self.metadata = ProviderMetadata(
            name=name,
            profile=profile,
            executable=name,
            overlay=name if profile == "internal-overlay" else None,
        )
        self.detected = detected
        self.status_value = status
        self.ensure_calls = []

    def detect(self):
        return self.detected

    def status(self, repo_root, timeout_seconds):
        return self.status_value

    def ensure_ready(self, repo_root, timeout_seconds):
        self.ensure_calls.append((Path(repo_root), timeout_seconds))
        return self.status_value

    def recommendation(self, project_root):
        return f"enable {self.metadata.name} in .jig/semantic-index.json"


class SemanticIndexStateTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_missing_state_defaults_public_no_auto_attach(self):
        state = load_state(self.tmpdir)

        self.assertFalse(state.auto_attach)
        self.assertEqual(state.provider, "tokensave")
        self.assertEqual(state.allowed_overlays, ())
        self.assertFalse(state.per_worktree_indexing)
        self.assertFalse(state.provider_explicit)

    def test_state_round_trips_explicit_opt_in(self):
        state = ActivationState(
            auto_attach=True,
            provider="fake",
            allowed_overlays=("scout",),
            per_worktree_indexing=True,
            timeout_seconds=1.5,
        )

        path = write_state(self.tmpdir, state)

        self.assertEqual(path, self.tmpdir / ".jig" / "semantic-index.json")
        self.assertEqual(load_state(self.tmpdir), state)

    def test_implicit_default_round_trip_preserves_provider_discovery(self):
        state = ActivationState(auto_attach=True)

        path = write_state(self.tmpdir, state)
        raw = json.loads(path.read_text())
        loaded = load_state(self.tmpdir)

        self.assertNotIn("provider", raw)
        self.assertFalse(loaded.provider_explicit)
        installed = FakeProvider(name="symdex", detected=True, status="ready")
        result = activate(
            self.tmpdir,
            providers={
                "tokensave": FakeProvider(name="tokensave", detected=False),
                "symdex": installed,
            },
            emit_telemetry=False,
        )
        self.assertEqual(result.provider, "symdex")
        self.assertEqual(result.provider_selection, "auto_discovered")

    def test_state_requires_json_boolean_true_for_attach_flags(self):
        path = self.tmpdir / ".jig" / "semantic-index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "auto_attach": "false",
            "per_worktree_indexing": "true",
        }))

        state = load_state(self.tmpdir)

        self.assertFalse(state.auto_attach)
        self.assertFalse(state.per_worktree_indexing)

    def test_allowed_overlays_empty_list_overrides_legacy_key(self):
        path = self.tmpdir / ".jig" / "semantic-index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "allowed_overlays": [],
            "internal_overlays": ["scout"],
        }))

        state = load_state(self.tmpdir)

        self.assertEqual(state.allowed_overlays, ())

    def test_builtin_registry_names_public_reference_candidates(self):
        registry = semantic_index.builtin_registry()

        self.assertIn("tokensave", registry)
        self.assertIn("codebase-memory-mcp", registry)
        self.assertIn("symdex", registry)
        self.assertIn("cocoindex-code", registry)
        self.assertNotIn("scout", registry)


class SemanticIndexActivationTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_provider_returns_actionable_missing_result(self):
        result = activate(
            self.tmpdir,
            providers={"fake": FakeProvider(detected=False)},
            emit_telemetry=False,
        )

        self.assertEqual(result.action, "recommend")
        self.assertEqual(result.outcome, "provider_missing")
        self.assertIn(".jig/semantic-index.json", result.recommendation)
        self.assertEqual(result.provider_selection, "absent")

    def test_unconfigured_project_discovers_later_public_candidate(self):
        missing = FakeProvider(name="tokensave", detected=False)
        installed = FakeProvider(name="symdex", detected=True)

        result = activate(
            self.tmpdir,
            providers={"tokensave": missing, "symdex": installed},
            emit_telemetry=False,
        )

        self.assertEqual(result.provider, "symdex")
        self.assertEqual(result.action, "recommend")
        self.assertEqual(result.outcome, "not_opted_in")
        self.assertEqual(result.provider_selection, "auto_discovered")

    def test_explicit_empty_provider_registry_disables_builtins(self):
        write_state(
            self.tmpdir,
            ActivationState(
                auto_attach=True,
                provider="tokensave",
                provider_explicit=True,
            ),
        )

        with mock.patch("semantic_index.shutil.which", return_value="/bin/tokensave"):
            result = activate(self.tmpdir, providers={}, emit_telemetry=False)

        self.assertEqual(result.provider, "tokensave")
        self.assertEqual(result.outcome, "provider_missing")

    def test_unknown_explicit_provider_does_not_fallback_and_attach(self):
        write_state(self.tmpdir, ActivationState(auto_attach=True, provider="missing"))
        fallback = FakeProvider(name="tokensave", status="attach_started")

        result = activate(
            self.tmpdir,
            providers={"tokensave": fallback},
            emit_telemetry=False,
        )

        self.assertEqual(result.provider, "missing")
        self.assertEqual(result.outcome, "provider_missing")
        self.assertEqual(result.provider_selection, "explicit")
        self.assertEqual(fallback.ensure_calls, [])

    def test_public_provider_present_without_opt_in_recommends_once(self):
        write_state(self.tmpdir, ActivationState(provider="fake"))

        result = activate(
            self.tmpdir,
            providers={"fake": FakeProvider(detected=True)},
            emit_telemetry=False,
        )

        self.assertEqual(result.action, "recommend")
        self.assertEqual(result.outcome, "not_opted_in")
        self.assertIn(".jig/semantic-index.json", result.recommendation)

    def test_opted_in_already_ready(self):
        write_state(self.tmpdir, ActivationState(auto_attach=True, provider="fake"))
        provider = FakeProvider(status="ready")

        result = activate(self.tmpdir, providers={"fake": provider}, emit_telemetry=False)

        self.assertEqual(result.action, "ready")
        self.assertEqual(result.outcome, "ready")
        self.assertEqual(len(provider.ensure_calls), 1)

    def test_opted_in_readiness_needed_records_attach(self):
        write_state(self.tmpdir, ActivationState(auto_attach=True, provider="fake"))
        provider = FakeProvider(status="attach_started")

        result = activate(self.tmpdir, providers={"fake": provider}, emit_telemetry=False)

        self.assertEqual(result.action, "attach")
        self.assertEqual(result.outcome, "attach_started")

    def test_scout_overlay_disabled_when_not_explicitly_allowed(self):
        write_state(self.tmpdir, ActivationState(auto_attach=True, provider="scout"))

        result = activate(self.tmpdir, providers={}, emit_telemetry=False)

        self.assertEqual(result.provider, "scout")
        self.assertEqual(result.outcome, "overlay_disabled")

    def test_injected_internal_provider_still_requires_overlay_permission(self):
        write_state(self.tmpdir, ActivationState(auto_attach=True, provider="scout"))
        provider = FakeProvider(name="scout", profile="internal-overlay")

        result = activate(
            self.tmpdir, providers={"scout": provider}, emit_telemetry=False
        )

        self.assertEqual(result.provider, "scout")
        self.assertEqual(result.outcome, "overlay_disabled")
        self.assertEqual(provider.ensure_calls, [])

    def test_scout_name_requires_overlay_even_when_metadata_mislabels_public(self):
        write_state(self.tmpdir, ActivationState(auto_attach=True, provider="scout"))
        provider = FakeProvider(name="scout", profile="public")

        result = activate(
            self.tmpdir, providers={"scout": provider}, emit_telemetry=False
        )

        self.assertEqual(result.provider, "scout")
        self.assertEqual(result.outcome, "overlay_disabled")
        self.assertEqual(provider.ensure_calls, [])

    def test_scout_overlay_enabled_through_state(self):
        write_state(
            self.tmpdir,
            ActivationState(
                auto_attach=True,
                provider="scout",
                allowed_overlays=("scout",),
            ),
        )
        provider = FakeProvider(name="scout", profile="internal-overlay")

        result = activate(self.tmpdir, providers={"scout": provider}, emit_telemetry=False)

        self.assertEqual(result.provider_profile, "internal-overlay")
        self.assertEqual(result.outcome, "ready")

    def test_unrelated_overlay_does_not_enable_scout(self):
        write_state(
            self.tmpdir,
            ActivationState(
                auto_attach=True,
                provider="scout",
                allowed_overlays=("other",),
            ),
        )
        provider = FakeProvider(name="scout", profile="internal-overlay")

        result = activate(
            self.tmpdir, providers={"scout": provider}, emit_telemetry=False
        )

        self.assertEqual(result.provider, "scout")
        self.assertEqual(result.outcome, "overlay_disabled")
        self.assertEqual(provider.ensure_calls, [])

    def test_worktree_policy_uses_canonical_root_by_default(self):
        write_state(self.tmpdir, ActivationState(auto_attach=True, provider="fake"))
        canonical = self.tmpdir / "main"
        worktree = self.tmpdir / "worktree"
        provider = FakeProvider()

        with mock.patch(
            "semantic_index.resolve_repo_root",
            return_value=semantic_index.RepoRoot(
                requested=worktree,
                canonical=canonical,
                selected=canonical,
                root_class="worktree",
            ),
        ):
            result = activate(
                self.tmpdir, providers={"fake": provider}, emit_telemetry=False
            )

        self.assertEqual(result.repo_root_class, "worktree")
        self.assertEqual(result.considered_root, str(canonical))
        self.assertEqual(provider.ensure_calls[0][0], canonical)

    def test_telemetry_is_content_free_and_fail_open(self):
        result = semantic_index.ActivationResult(
            provider="fake",
            provider_profile="public",
            action="ready",
            outcome="ready",
            repo_root_class="canonical",
            considered_root=str(self.tmpdir),
            auto_attach=True,
        )

        record_telemetry(self.tmpdir, result, host="claude", now=lambda: 123)
        rows = (self.tmpdir / ".jig" / "semantic-index-events.jsonl").read_text()
        event = json.loads(rows)

        self.assertEqual(event["timestamp"], 123)
        self.assertEqual(event["host"], "claude")
        self.assertNotIn("considered_root", event)
        self.assertNotIn("command_output", event)
        self.assertEqual(event["provider_selection"], "unknown")

        with mock.patch("semantic_index.Path.open", side_effect=OSError("readonly")):
            record_telemetry(self.tmpdir, result)


class CommandProviderTests(unittest.TestCase):
    def test_daemon_fallback_then_attach(self):
        calls = []

        def runner(argv, timeout):
            calls.append(argv)
            if argv[:2] == ["fake", "status"]:
                return subprocess.CompletedProcess(argv, 1)
            if argv[:3] == ["fake", "daemon", "status"]:
                return subprocess.CompletedProcess(argv, 1)
            return subprocess.CompletedProcess(argv, 0)

        provider = CommandProvider(
            ProviderMetadata(name="fake", profile="public", executable="fake"),
            status_args=("status", "{repo_root}"),
            daemon_status_args=("daemon", "status"),
            daemon_start_args=("daemon", "start"),
            attach_args=("attach", "{repo_root}"),
            runner=runner,
        )

        with mock.patch("semantic_index.shutil.which", return_value="/bin/fake"):
            outcome = provider.ensure_ready(Path("/repo"), 0.1)

        self.assertEqual(outcome, "attach_started")
        self.assertIn(["fake", "daemon", "start"], calls)
        self.assertIn(["fake", "attach", "/repo"], calls)

    def test_timeout_fails_open(self):
        def runner(argv, timeout):
            raise subprocess.TimeoutExpired(argv, timeout)

        provider = CommandProvider(
            ProviderMetadata(name="fake", profile="public", executable="fake"),
            status_args=("status", "{repo_root}"),
            attach_args=("attach", "{repo_root}"),
            runner=runner,
        )

        with mock.patch("semantic_index.shutil.which", return_value="/bin/fake"):
            outcome = provider.ensure_ready(Path("/repo"), 0.1)

        self.assertEqual(outcome, "not_ready")


if __name__ == "__main__":
    unittest.main()
