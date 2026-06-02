"""
Tests for scripts/usage.py — on-demand per-spec orchestrator usage report.

Run:
    python3 scripts/test_usage.py
    # or from repo root:
    python3 -m unittest scripts.test_usage

These tests build a synthetic `~/.claude/projects`-shaped fixture tree (a
temp dir pointed at via `--projects-dir` / the `projects_dir=` seam) with
crafted JSONL transcripts: assistant records carrying `message.usage`, and
spec-path mentions in the content used for attribution. They assert:

  * correct attribution of sessions to a target spec (the dominant-mention
    heuristic);
  * the four orchestrator token sums + total;
  * the no-ccusage degradation path (an injected unavailable-ccusage seam);
  * read-only / no-mutation of the fixture tree.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
USAGE = REPO_ROOT / "scripts" / "usage.py"

# Import the module directly for unit tests.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import usage as uu


# ---------------------------------------------------------------------------
# Fixture helpers — build a synthetic ~/.claude/projects tree.
# ---------------------------------------------------------------------------

def _assistant_record(model, usage, cwd, branch="claude/x", session="s1",
                      text=""):
    """One assistant transcript record with a message.usage block."""
    content = [{"type": "text", "text": text}] if text else []
    return {
        "type": "assistant",
        "cwd": cwd,
        "gitBranch": branch,
        "sessionId": session,
        "uuid": session + "-u",
        "message": {
            "role": "assistant",
            "model": model,
            "content": content,
            "usage": usage,
        },
    }


def _user_record(cwd, text, session="s1"):
    """A user record carrying text (used for spec-path mentions)."""
    return {
        "type": "user",
        "cwd": cwd,
        "sessionId": session,
        "uuid": session + "-uu",
        "message": {"role": "user", "content": text},
    }


def _tool_use_record(cwd, tool_input, name="Read", session="s1"):
    """An assistant record whose ONLY content is a tool_use block (e.g. a
    Read call). Spec-path mentions live inside the serialized tool input —
    no plain `text` block — exercising the _record_texts tool_use branch.
    """
    return {
        "type": "assistant",
        "cwd": cwd,
        "sessionId": session,
        "uuid": session + "-tu",
        "message": {
            "role": "assistant",
            "model": "claude-opus-4-8",
            "content": [{"type": "tool_use", "id": "tu1", "name": name,
                         "input": tool_input}],
        },
    }


def _tool_result_record(cwd, result_text, session="s1"):
    """A user record carrying a tool_result whose content (list-of-text form)
    holds spec-path mentions — exercising the _record_texts tool_result
    branch. No plain `text` block elsewhere.
    """
    return {
        "type": "user",
        "cwd": cwd,
        "sessionId": session,
        "uuid": session + "-tr",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "tu1",
                         "content": [{"type": "text", "text": result_text}]}],
        },
    }


def _usage(inp=0, out=0, cache_read=0, cache_create=0):
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_create,
    }


def _write_session(projects_dir: Path, encoded_cwd: str, session_id: str,
                   records: list):
    """Write a JSONL session file under projects_dir/<encoded_cwd>/."""
    d = projects_dir / encoded_cwd
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{session_id}.jsonl"
    with p.open("w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return p


# Encoded-cwd dir names for a fake repo at /Users/me/Projects/demo, with a
# worktree at /Users/me/Projects/demo/.claude/worktrees/foo.
MAIN_CWD = "/Users/me/Projects/demo"
WT_CWD = "/Users/me/Projects/demo/.claude/worktrees/foo"
ENC_MAIN = "-Users-me-Projects-demo"
ENC_WT = "-Users-me-Projects-demo--claude-worktrees-foo"


class _TreeMixin:
    """Builds a temp projects tree with two sessions attributed to spec 055
    (one in the main root, one in a worktree) and one noise session for spec
    042. The 055 sessions carry distinct, known token sums.
    """

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="jig-usage-"))
        self.projects = self._tmp / "projects"
        self.projects.mkdir()

        # Session A — main root, clearly about spec 055.
        _write_session(
            self.projects, ENC_MAIN, "sessA",
            [
                _user_record(MAIN_CWD,
                             "Please work on docs/specs/055-token-usage-tracking/"
                             "slice-01.md — this is spec 055.",
                             session="sessA"),
                _assistant_record(
                    "claude-opus-4-8",
                    _usage(inp=10, out=100, cache_read=1000, cache_create=200),
                    MAIN_CWD, session="sessA",
                    text="Working on 055-01. See specs/055-token-usage-tracking."),
                _assistant_record(
                    "claude-opus-4-8",
                    _usage(inp=5, out=50, cache_read=500, cache_create=100),
                    MAIN_CWD, session="sessA",
                    text="More on slice 055-01."),
            ],
        )

        # Session B — worktree, also spec 055 (must be picked up via the
        # main-root prefix glob spanning worktrees).
        _write_session(
            self.projects, ENC_WT, "sessB",
            [
                _user_record(WT_CWD,
                             "Continue specs/055-token-usage-tracking work.",
                             session="sessB"),
                _assistant_record(
                    "claude-opus-4-8",
                    _usage(inp=1, out=10, cache_read=300, cache_create=40),
                    WT_CWD, session="sessB",
                    text="055-01 again, specs/055-token-usage-tracking."),
            ],
        )

        # Session C — main root, dominantly about a DIFFERENT spec (042).
        _write_session(
            self.projects, ENC_MAIN, "sessC",
            [
                _user_record(MAIN_CWD,
                             "Work on specs/042-other-thing — spec 042, slice 042-01.",
                             session="sessC"),
                _assistant_record(
                    "claude-opus-4-8",
                    _usage(inp=9999, out=9999, cache_read=9999, cache_create=9999),
                    MAIN_CWD, session="sessC",
                    text="042-01, specs/042-other-thing, spec 042 everywhere."),
            ],
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Encoded-prefix derivation
# ---------------------------------------------------------------------------

class EncodePrefixTests(unittest.TestCase):

    def test_encode_replaces_slashes_and_dots(self):
        self.assertEqual(uu.encode_cwd(MAIN_CWD), ENC_MAIN)

    def test_encode_worktree_path(self):
        self.assertEqual(uu.encode_cwd(WT_CWD), ENC_WT)

    def test_worktree_prefix_is_main_root_prefix(self):
        # The worktree's encoded name must start with the main root's encoded
        # name, so a single prefix glob spans the repo + all worktrees.
        self.assertTrue(uu.encode_cwd(WT_CWD).startswith(uu.encode_cwd(MAIN_CWD)))


# ---------------------------------------------------------------------------
# Session discovery (prefix glob across worktrees)
# ---------------------------------------------------------------------------

class SessionDiscoveryTests(_TreeMixin, unittest.TestCase):

    def test_finds_sessions_across_main_and_worktree(self):
        sessions = uu.find_sessions(self.projects, ENC_MAIN)
        names = sorted(p.name for p in sessions)
        self.assertIn("sessA.jsonl", names)
        self.assertIn("sessB.jsonl", names)  # worktree session
        self.assertIn("sessC.jsonl", names)

    def test_unrelated_repo_dirs_excluded(self):
        # Drop a session for a totally different repo; it must not be returned.
        _write_session(self.projects, "-Users-me-Projects-elsewhere", "z",
                       [_assistant_record("claude-opus-4-8", _usage(inp=1),
                                          "/Users/me/Projects/elsewhere")])
        sessions = uu.find_sessions(self.projects, ENC_MAIN)
        names = {p.name for p in sessions}
        self.assertNotIn("z.jsonl", names)


# ---------------------------------------------------------------------------
# Attribution (dominant spec-path mention heuristic)
# ---------------------------------------------------------------------------

class AttributionTests(_TreeMixin, unittest.TestCase):

    def test_session_attributed_to_dominant_spec(self):
        recs = uu.read_session(self.projects / ENC_MAIN / "sessA.jsonl")
        self.assertEqual(uu.dominant_spec(recs), "055")

    def test_noise_session_attributed_elsewhere(self):
        recs = uu.read_session(self.projects / ENC_MAIN / "sessC.jsonl")
        self.assertEqual(uu.dominant_spec(recs), "042")

    def test_session_with_no_mentions_is_none(self):
        p = _write_session(self.projects, ENC_MAIN, "blank",
                           [_assistant_record("claude-opus-4-8", _usage(inp=1),
                                              MAIN_CWD, session="blank",
                                              text="no spec references here")])
        recs = uu.read_session(p)
        self.assertIsNone(uu.dominant_spec(recs))

    def test_attribution_via_tool_use_input(self):
        # A real transcript can mention a spec ONLY inside a Read tool_use
        # input (file_path), with no plain-text reference. Attribution must
        # still find it via the _record_texts tool_use branch.
        p = _write_session(
            self.projects, ENC_MAIN, "tooluse",
            [_tool_use_record(
                MAIN_CWD,
                {"file_path": "docs/specs/077-tool-attribution/slice-01.md"},
                session="tooluse")],
        )
        recs = uu.read_session(p)
        self.assertEqual(uu.dominant_spec(recs), "077")

    def test_attribution_via_tool_result_content(self):
        # A spec mentioned only inside a tool_result (e.g. a Grep hit or file
        # read echoed back) must attribute via the _record_texts tool_result
        # branch.
        p = _write_session(
            self.projects, ENC_MAIN, "toolresult",
            [_tool_result_record(
                MAIN_CWD,
                "match: docs/specs/088-grep-hit/spec.md — see spec 088.",
                session="toolresult")],
        )
        recs = uu.read_session(p)
        self.assertEqual(uu.dominant_spec(recs), "088")


# ---------------------------------------------------------------------------
# Token sums for the attributed spec
# ---------------------------------------------------------------------------

class TokenSumTests(_TreeMixin, unittest.TestCase):

    def test_token_sums_for_target_spec(self):
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        # Session A: in 10+5=15, out 100+50=150, cR 1000+500=1500, cC 200+100=300
        # Session B: in 1, out 10, cR 300, cC 40
        self.assertEqual(rep.input_tokens, 16)
        self.assertEqual(rep.output_tokens, 160)
        self.assertEqual(rep.cache_read_tokens, 1800)
        self.assertEqual(rep.cache_creation_tokens, 340)

    def test_total_is_sum_of_four_categories(self):
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        self.assertEqual(
            rep.total_tokens,
            rep.input_tokens + rep.output_tokens
            + rep.cache_read_tokens + rep.cache_creation_tokens,
        )
        self.assertEqual(rep.total_tokens, 16 + 160 + 1800 + 340)

    def test_session_count_and_models(self):
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        self.assertEqual(rep.session_count, 2)  # sessA + sessB, NOT sessC
        self.assertEqual(rep.models, ["claude-opus-4-8"])

    def test_noise_spec_not_summed(self):
        # The 042 session's huge 9999s must not leak into the 055 totals.
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        self.assertLess(rep.total_tokens, 9999)

    def test_slug_argument_resolves_to_number(self):
        # A slug like "055-token-usage-tracking" attributes the same as "055".
        rep = uu.build_report(spec="055-token-usage-tracking",
                              projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        self.assertEqual(rep.total_tokens, 16 + 160 + 1800 + 340)


# ---------------------------------------------------------------------------
# Per-model token totals (needed for the ccusage rate application)
# ---------------------------------------------------------------------------

class PerModelTotalsTests(_TreeMixin, unittest.TestCase):

    def test_per_model_tokens_recorded(self):
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        self.assertIn("claude-opus-4-8", rep.per_model)
        m = rep.per_model["claude-opus-4-8"]
        self.assertEqual(m["input_tokens"], 16)
        self.assertEqual(m["output_tokens"], 160)
        self.assertEqual(m["cache_read_input_tokens"], 1800)
        self.assertEqual(m["cache_creation_input_tokens"], 340)


# ---------------------------------------------------------------------------
# ccusage rate derivation + application
# ---------------------------------------------------------------------------

# A minimal ccusage --json payload (per-model breakdowns under daily[]).
CCUSAGE_JSON = {
    "daily": [
        {
            "period": "2026-06-01",
            "modelBreakdowns": [
                {
                    "modelName": "claude-opus-4-8",
                    "cost": 2.0,
                    "inputTokens": 100,
                    "outputTokens": 100,
                    "cacheReadTokens": 1700,
                    "cacheCreationTokens": 100,
                    # total = 2000 tokens -> $0.001 / token effective
                },
            ],
        },
    ],
    "totals": {},
}


class CcusageRateTests(unittest.TestCase):

    def test_effective_rate_derivation(self):
        rates = uu.ccusage_rates_from_json(CCUSAGE_JSON)
        # cost 2.0 over 2000 tokens -> 0.001 $/token.
        self.assertAlmostEqual(rates["claude-opus-4-8"], 0.001, places=9)

    def test_rate_aggregates_across_days(self):
        payload = {
            "daily": [
                {"modelBreakdowns": [{"modelName": "m", "cost": 1.0,
                                      "inputTokens": 500, "outputTokens": 0,
                                      "cacheReadTokens": 0,
                                      "cacheCreationTokens": 0}]},
                {"modelBreakdowns": [{"modelName": "m", "cost": 1.0,
                                      "inputTokens": 500, "outputTokens": 0,
                                      "cacheReadTokens": 0,
                                      "cacheCreationTokens": 0}]},
            ],
        }
        rates = uu.ccusage_rates_from_json(payload)
        # $2.0 over 1000 tokens -> 0.002 $/token.
        self.assertAlmostEqual(rates["m"], 0.002, places=9)

    def test_zero_token_model_skipped(self):
        payload = {"daily": [{"modelBreakdowns": [
            {"modelName": "z", "cost": 0.0, "inputTokens": 0,
             "outputTokens": 0, "cacheReadTokens": 0,
             "cacheCreationTokens": 0}]}]}
        rates = uu.ccusage_rates_from_json(payload)
        self.assertNotIn("z", rates)


class CcusageApplicationTests(_TreeMixin, unittest.TestCase):

    def test_cost_applied_from_injected_runner(self):
        # Inject a runner that returns the canned ccusage payload — no network.
        rep = uu.build_report(
            spec="055", projects_dir=self.projects, encoded_prefix=ENC_MAIN,
            ccusage_runner=lambda: CCUSAGE_JSON,
        )
        # 055 total = 2316 tokens at 0.001 $/token = $2.316.
        self.assertIsNotNone(rep.cost_usd)
        self.assertAlmostEqual(rep.cost_usd, 2316 * 0.001, places=6)

    def test_cost_in_rendered_output(self):
        rep = uu.build_report(
            spec="055", projects_dir=self.projects, encoded_prefix=ENC_MAIN,
            ccusage_runner=lambda: CCUSAGE_JSON,
        )
        out = uu.render(rep)
        self.assertIn("055", out)
        self.assertIn("$", out)


class CcusagePartialRateTests(unittest.TestCase):
    """Two attributed models, but ccusage prices only one of them. The priced
    model must still contribute to the $, and a "partial: no rate for ..."
    note must surface the unpriced one (the apply_rates partial branch).
    """

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="jig-usage-partial-"))
        self.projects = self._tmp / "projects"
        self.projects.mkdir()
        # One session about spec 066, two assistant turns on DIFFERENT models.
        _write_session(
            self.projects, ENC_MAIN, "twomodel",
            [
                _user_record(MAIN_CWD,
                             "Work on specs/066-two-model — spec 066, slice 066-01.",
                             session="twomodel"),
                _assistant_record(
                    "claude-opus-4-8",
                    _usage(inp=100, out=0, cache_read=0, cache_create=0),
                    MAIN_CWD, session="twomodel",
                    text="066-01, specs/066-two-model."),
                _assistant_record(
                    "claude-haiku-only",
                    _usage(inp=50, out=0, cache_read=0, cache_create=0),
                    MAIN_CWD, session="twomodel",
                    text="066-01 again."),
            ],
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_partial_rate_note_and_priced_model_contributes(self):
        # ccusage prices ONLY the opus model ($0.01/token over 100 tokens);
        # claude-haiku-only has no rate.
        payload = {"daily": [{"modelBreakdowns": [
            {"modelName": "claude-opus-4-8", "cost": 1.0,
             "inputTokens": 100, "outputTokens": 0, "cacheReadTokens": 0,
             "cacheCreationTokens": 0}]}]}  # 1.0 / 100 = 0.01 $/token
        rep = uu.build_report(spec="066", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN,
                              ccusage_runner=lambda: payload)
        # Priced model contributes: 100 opus tokens * 0.01 = $1.00.
        self.assertIsNotNone(rep.cost_usd)
        self.assertAlmostEqual(rep.cost_usd, 1.00, places=6)
        # The unpriced model is called out in a "partial" note.
        self.assertIsNotNone(rep.cost_note)
        self.assertIn("partial", rep.cost_note)
        self.assertIn("claude-haiku-only", rep.cost_note)


# ---------------------------------------------------------------------------
# ccusage degradation path
# ---------------------------------------------------------------------------

class CcusageDegradationTests(_TreeMixin, unittest.TestCase):

    def test_unavailable_ccusage_still_prints_tokens(self):
        # A runner that raises (npx/ccusage missing) -> cost None, tokens intact.
        def boom():
            raise FileNotFoundError("npx not found")

        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=boom)
        self.assertIsNone(rep.cost_usd)
        self.assertEqual(rep.total_tokens, 16 + 160 + 1800 + 340)

    def test_unavailable_message_in_output(self):
        def boom():
            raise FileNotFoundError("npx not found")

        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=boom)
        out = uu.render(rep)
        self.assertIn("unavailable", out.lower())
        # Tokens still appear (cache_read total).
        self.assertTrue(_shows_number(out, 1800), msg=out)

    def test_ccusage_returns_no_matching_model(self):
        # ccusage works but has no rate for the model -> cost None, clear note.
        payload = {"daily": [{"modelBreakdowns": [
            {"modelName": "some-other-model", "cost": 5.0,
             "inputTokens": 1000, "outputTokens": 0, "cacheReadTokens": 0,
             "cacheCreationTokens": 0}]}]}
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN,
                              ccusage_runner=lambda: payload)
        self.assertIsNone(rep.cost_usd)

    def test_ccusage_timeout_degrades_gracefully(self):
        # A runner that raises subprocess.TimeoutExpired (a network/package
        # fetch stall) must degrade like any other failure: cost None, tokens
        # intact, "unavailable" in the output. Guards against `report` hanging.
        def hang():
            raise subprocess.TimeoutExpired(cmd="npx ccusage@latest --json",
                                            timeout=60)

        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=hang)
        self.assertIsNone(rep.cost_usd)
        self.assertEqual(rep.total_tokens, 16 + 160 + 1800 + 340)
        self.assertIn("unavailable", uu.render(rep).lower())


class CcusageRunnerTimeoutTests(unittest.TestCase):
    """The real npx runner must pass a bounded timeout= to subprocess.run so a
    stalled network/package-fetch cannot hang `report` indefinitely (the
    degradation path catches errors, not hangs).
    """

    def test_run_ccusage_npx_passes_a_timeout(self):
        import unittest.mock as mock
        captured = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

        with mock.patch.object(uu.subprocess, "run", side_effect=fake_run):
            uu.run_ccusage_npx()
        self.assertIn("timeout", captured)
        self.assertIsNotNone(captured["timeout"])
        self.assertGreater(captured["timeout"], 0)


# ---------------------------------------------------------------------------
# Honest framing in the output
# ---------------------------------------------------------------------------

class HonestFramingTests(_TreeMixin, unittest.TestCase):

    def test_output_notes_estimate_and_orchestrator_only(self):
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        out = uu.render(rep).lower()
        self.assertIn("estimate", out)
        self.assertIn("orchestrator", out)
        # Mentions subagents land later (056-02).
        self.assertIn("subagent", out)


# ---------------------------------------------------------------------------
# Robustness — malformed / missing transcripts never throw
# ---------------------------------------------------------------------------

class RobustnessTests(_TreeMixin, unittest.TestCase):

    def test_malformed_jsonl_line_skipped(self):
        p = self.projects / ENC_MAIN / "sessA.jsonl"
        with p.open("a") as fh:
            fh.write("this is not json\n")
            fh.write('{"type": "assistant", "message": {bad json}\n')
        # Reading must not raise; the good records still count.
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        self.assertEqual(rep.total_tokens, 16 + 160 + 1800 + 340)

    def test_missing_projects_dir_no_throw(self):
        rep = uu.build_report(spec="055",
                              projects_dir=self._tmp / "does-not-exist",
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        self.assertEqual(rep.total_tokens, 0)
        self.assertEqual(rep.session_count, 0)

    def test_record_missing_usage_skipped(self):
        p = _write_session(self.projects, ENC_MAIN, "nousage",
                           [_user_record(MAIN_CWD, "specs/055-token-usage-tracking",
                                         session="nousage"),
                            {"type": "assistant", "cwd": MAIN_CWD,
                             "sessionId": "nousage",
                             "message": {"role": "assistant",
                                         "model": "claude-opus-4-8",
                                         "content": []}}])  # no usage key
        recs = uu.read_session(p)
        # Should not raise when summing.
        sums = uu.sum_usage(recs)
        self.assertEqual(sums["input_tokens"], 0)


# ---------------------------------------------------------------------------
# Read-only / no-mutation guarantee
# ---------------------------------------------------------------------------

class ReadOnlyTests(_TreeMixin, unittest.TestCase):

    def _tree_snapshot(self):
        """Map of relative path -> (size, mtime_ns) for every file in the tree."""
        snap = {}
        for root, _dirs, files in os.walk(self._tmp):
            for f in files:
                fp = Path(root) / f
                st = fp.stat()
                snap[str(fp.relative_to(self._tmp))] = (st.st_size, st.st_mtime_ns)
        return snap

    def test_report_does_not_mutate_tree(self):
        before = self._tree_snapshot()
        uu.build_report(spec="055", projects_dir=self.projects,
                        encoded_prefix=ENC_MAIN,
                        ccusage_runner=lambda: CCUSAGE_JSON)
        after = self._tree_snapshot()
        self.assertEqual(before, after, "usage report mutated the projects tree")

    def test_no_new_files_created(self):
        before = set(self._tree_snapshot().keys())
        uu.build_report(spec="055", projects_dir=self.projects,
                        encoded_prefix=ENC_MAIN, ccusage_runner=None)
        after = set(self._tree_snapshot().keys())
        self.assertEqual(before, after)


# ---------------------------------------------------------------------------
# CLI subprocess tests
# ---------------------------------------------------------------------------

def _run_usage(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(USAGE), *args],
        capture_output=True, text=True,
    )


def _shows_number(text: str, n: int) -> bool:
    """True if `n` is rendered in `text`, tolerant of thousands grouping
    (so an assertion on the cache_read total survives a `1,800` formatter
    choice without coupling the test to the exact separator style).
    """
    return str(n) in text or f"{n:,}" in text


class CliTests(_TreeMixin, unittest.TestCase):

    def _ccusage_file(self) -> str:
        p = self._tmp / "ccusage.json"
        p.write_text(json.dumps(CCUSAGE_JSON))
        return str(p)

    def test_cli_report_runs_with_overrides(self):
        # --projects-dir + --main-root + --ccusage-json => fully offline run.
        result = _run_usage(
            "report", "055",
            "--projects-dir", str(self.projects),
            "--main-root", MAIN_CWD,
            "--ccusage-json", self._ccusage_file(),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("055", result.stdout)
        self.assertTrue(_shows_number(result.stdout, 1800),   # cache_read sum
                        msg=result.stdout)
        self.assertIn("$", result.stdout)

    def test_cli_no_ccusage_flag_degrades(self):
        result = _run_usage(
            "report", "055",
            "--projects-dir", str(self.projects),
            "--main-root", MAIN_CWD,
            "--no-ccusage",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("unavailable", result.stdout.lower())
        self.assertTrue(_shows_number(result.stdout, 1800), msg=result.stdout)

    def test_cli_unknown_spec_exits_nonzero_or_zero_with_zero_tokens(self):
        # A spec with no attributed sessions reports zeros (not a crash).
        result = _run_usage(
            "report", "999",
            "--projects-dir", str(self.projects),
            "--main-root", MAIN_CWD,
            "--no-ccusage",
        )
        # Must not crash; reports a clear "no sessions" state.
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("0", result.stdout)

    def test_cli_ccusage_json_missing_file_degrades(self):
        # --ccusage-json pointing at a non-existent file: the _from_file seam
        # raises (FileNotFoundError), which degrades to "$ unavailable" with
        # tokens intact — no crash.
        missing = str(self._tmp / "no-such-ccusage.json")
        result = _run_usage(
            "report", "055",
            "--projects-dir", str(self.projects),
            "--main-root", MAIN_CWD,
            "--ccusage-json", missing,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("unavailable", result.stdout.lower())
        self.assertTrue(_shows_number(result.stdout, 1800), msg=result.stdout)

    def test_cli_ccusage_json_malformed_file_degrades(self):
        # --ccusage-json pointing at a garbage (non-JSON) file: _from_file's
        # json.loads raises -> "$ unavailable", tokens intact.
        bad = self._tmp / "garbage-ccusage.json"
        bad.write_text("this is not json {")
        result = _run_usage(
            "report", "055",
            "--projects-dir", str(self.projects),
            "--main-root", MAIN_CWD,
            "--ccusage-json", str(bad),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("unavailable", result.stdout.lower())
        self.assertTrue(_shows_number(result.stdout, 1800), msg=result.stdout)


if __name__ == "__main__":
    unittest.main()
