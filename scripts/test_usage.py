"""
Tests for scripts/usage.py — on-demand per-spec usage report
(orchestrator + subagent, spec 056).

Run:
    python3 scripts/test_usage.py
    # or from repo root:
    python3 -m unittest scripts.test_usage

These tests build a synthetic `~/.claude/projects`-shaped fixture tree (a
temp dir pointed at via `--projects-dir` / the `projects_dir=` seam) with
crafted JSONL transcripts: flat orchestrator session files, and nested
`<session>/subagents/agent-*.jsonl` subagent transcripts. They assert:

  * correct attribution of sessions to a target spec (the dominant-mention
    heuristic);
  * the four orchestrator token sums + total (056-01);
  * subagent accounting from the nested transcripts — the orchestrator/subagent
    split, the combined total, and the per-`attributionAgent` breakdown (056-02);
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


def _subagent_record(model, usage, attribution_agent, cwd=None,
                     session="s1"):
    """One nested-subagent assistant transcript record (slice 056-02).

    Mirrors the real shape: ``isSidechain: true``, a per-turn
    ``message.usage`` block, and the subagent type in the TOP-LEVEL
    ``attributionAgent`` field (NOT inside message).
    """
    return {
        "type": "assistant",
        "isSidechain": True,
        "attributionAgent": attribution_agent,
        "cwd": cwd,
        "sessionId": session,
        "uuid": session + "-sa",
        "message": {
            "role": "assistant",
            "model": model,
            "content": [],
            "usage": usage,
        },
    }


def _write_subagents(projects_dir: Path, encoded_cwd: str, session_id: str,
                     agent_file: str, records: list):
    """Write a nested subagent JSONL under
    ``projects_dir/<encoded_cwd>/<session_id>/subagents/<agent_file>.jsonl``.

    This is the nested layout slice 056-02 reads: a sibling directory named
    for the session UUID, holding one ``agent-*.jsonl`` per delegated turn.
    """
    d = projects_dir / encoded_cwd / session_id / "subagents"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{agent_file}.jsonl"
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

    def test_output_notes_estimate_orchestrator_and_subagent(self):
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        out = uu.render(rep).lower()
        self.assertIn("estimate", out)
        self.assertIn("orchestrator", out)
        # Subagent dimension landed in 056-02.
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
# Slice 056-02 — nested subagent transcripts (measured, not proxied)
# ---------------------------------------------------------------------------

class _SubagentTreeMixin:
    """A spec-099 session in the main root with a nested subagents dir holding
    TWO agent transcripts of DIFFERENT types, each with known per-turn usage:

      * agent-aaa.jsonl — `jig:reviewer`, one turn: in 7, out 70, cR 700, cC 7
      * agent-bbb.jsonl — `jig:implementer`, two turns:
            in 3+1, out 30+10, cR 300+100, cC 3+1

    Subagent totals: in 11, out 110, cR 1100, cC 11 (= 1232 tokens).
    The flat (orchestrator) session carries its own distinct sums so the split
    is unambiguous: in 100, out 200, cR 3000, cC 400 (= 3700 tokens).
    """

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="jig-usage-sa-"))
        self.projects = self._tmp / "projects"
        self.projects.mkdir()

        # Flat orchestrator session for spec 099.
        _write_session(
            self.projects, ENC_MAIN, "sessSA",
            [
                _user_record(MAIN_CWD,
                             "Work on specs/099-delegated — spec 099, slice 099-01.",
                             session="sessSA"),
                _assistant_record(
                    "claude-opus-4-8",
                    _usage(inp=100, out=200, cache_read=3000, cache_create=400),
                    MAIN_CWD, session="sessSA",
                    text="099-01, specs/099-delegated."),
            ],
        )

        # Nested subagent transcripts for that session.
        _write_subagents(
            self.projects, ENC_MAIN, "sessSA", "agent-aaa",
            [
                _user_record(MAIN_CWD, "review this", session="sessSA"),
                _subagent_record(
                    "claude-opus-4-8",
                    _usage(inp=7, out=70, cache_read=700, cache_create=7),
                    "jig:reviewer", cwd=MAIN_CWD, session="sessSA"),
            ],
        )
        _write_subagents(
            self.projects, ENC_MAIN, "sessSA", "agent-bbb",
            [
                _subagent_record(
                    "claude-opus-4-8",
                    _usage(inp=3, out=30, cache_read=300, cache_create=3),
                    "jig:implementer", cwd=MAIN_CWD, session="sessSA"),
                _subagent_record(
                    "claude-opus-4-8",
                    _usage(inp=1, out=10, cache_read=100, cache_create=1),
                    "jig:implementer", cwd=MAIN_CWD, session="sessSA"),
            ],
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)


class SubagentSumTests(_SubagentTreeMixin, unittest.TestCase):

    def test_subagent_per_turn_sum(self):
        rep = uu.build_report(spec="099", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        # Summed across BOTH nested agent files, ALL turns.
        self.assertEqual(rep.subagent_input_tokens, 11)
        self.assertEqual(rep.subagent_output_tokens, 110)
        self.assertEqual(rep.subagent_cache_read_tokens, 1100)
        self.assertEqual(rep.subagent_cache_creation_tokens, 11)
        self.assertEqual(rep.subagent_total_tokens, 11 + 110 + 1100 + 11)

    def test_orchestrator_sums_unchanged_by_subagents(self):
        # The flat-session (056-01) sums must NOT absorb subagent tokens.
        rep = uu.build_report(spec="099", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        self.assertEqual(rep.input_tokens, 100)
        self.assertEqual(rep.output_tokens, 200)
        self.assertEqual(rep.cache_read_tokens, 3000)
        self.assertEqual(rep.cache_creation_tokens, 400)
        self.assertEqual(rep.total_tokens, 100 + 200 + 3000 + 400)

    def test_combined_total_is_orchestrator_plus_subagent(self):
        rep = uu.build_report(spec="099", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        self.assertEqual(rep.combined_total_tokens,
                         rep.total_tokens + rep.subagent_total_tokens)
        self.assertEqual(rep.combined_total_tokens, 3700 + 1232)

    def test_subagent_breakdown_by_attribution_agent(self):
        rep = uu.build_report(spec="099", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        by_type = rep.subagent_by_type
        self.assertIn("jig:reviewer", by_type)
        self.assertIn("jig:implementer", by_type)
        # reviewer: single turn.
        r = by_type["jig:reviewer"]
        self.assertEqual(r["input_tokens"], 7)
        self.assertEqual(r["output_tokens"], 70)
        self.assertEqual(r["cache_read_input_tokens"], 700)
        self.assertEqual(r["cache_creation_input_tokens"], 7)
        # implementer: two turns summed.
        i = by_type["jig:implementer"]
        self.assertEqual(i["input_tokens"], 4)
        self.assertEqual(i["output_tokens"], 40)
        self.assertEqual(i["cache_read_input_tokens"], 400)
        self.assertEqual(i["cache_creation_input_tokens"], 4)

    def test_render_shows_orchestrator_subagent_and_combined(self):
        rep = uu.build_report(spec="099", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        out = uu.render(rep)
        low = out.lower()
        self.assertIn("orchestrator", low)
        self.assertIn("subagent", low)
        self.assertIn("combined", low)
        # The measured subagent total and combined total are rendered.
        self.assertTrue(_shows_number(out, 1232), msg=out)   # subagent total
        self.assertTrue(_shows_number(out, 3700 + 1232), msg=out)  # combined
        # The per-type breakdown surfaces the agent types.
        self.assertIn("jig:reviewer", out)
        self.assertIn("jig:implementer", out)

    def test_render_has_no_estimate_or_proxy_label_for_subagents(self):
        # AC2: subagent usage is MEASURED, not a proxy/estimate. The output
        # must not relabel the subagent dimension as an estimate/proxy, and
        # must not carry the old 056-01 "subagent ... not yet included" line.
        rep = uu.build_report(spec="099", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        low = uu.render(rep).lower()
        self.assertNotIn("proxy", low)
        self.assertNotIn("not yet included", low)
        self.assertNotIn("arrives in slice 056-02", low)


class SubagentCostTests(_SubagentTreeMixin, unittest.TestCase):

    def test_combined_cost_prices_orchestrator_and_subagent_tokens(self):
        # ccusage rate: $0.001/token for claude-opus-4-8 (2.0 over 2000).
        rep = uu.build_report(spec="099", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN,
                              ccusage_runner=lambda: CCUSAGE_JSON)
        # Orchestrator $ over its 3700 tokens.
        self.assertAlmostEqual(rep.cost_usd, 3700 * 0.001, places=6)
        # Subagent $ over its 1232 tokens.
        self.assertIsNotNone(rep.subagent_cost_usd)
        self.assertAlmostEqual(rep.subagent_cost_usd, 1232 * 0.001, places=6)
        # Combined $ = the true per-spec cost.
        self.assertIsNotNone(rep.combined_cost_usd)
        self.assertAlmostEqual(rep.combined_cost_usd,
                               (3700 + 1232) * 0.001, places=6)


class NoSubagentTests(_TreeMixin, unittest.TestCase):
    """The 056-01 fixture tree has NO nested subagents dirs. Subagent totals
    must be zero, silently — never throwing — and the orchestrator sums stay
    exactly as 056-01 asserts.
    """

    def test_no_nested_dir_means_zero_subagent_total(self):
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        self.assertEqual(rep.subagent_total_tokens, 0)
        self.assertEqual(rep.subagent_by_type, {})
        # Orchestrator sums identical to the 056-01 expectations.
        self.assertEqual(rep.total_tokens, 16 + 160 + 1800 + 340)
        # Combined collapses to the orchestrator total.
        self.assertEqual(rep.combined_total_tokens, rep.total_tokens)

    def test_no_subagent_cost_is_zero_not_none(self):
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN,
                              ccusage_runner=lambda: CCUSAGE_JSON)
        # No subagent tokens -> subagent $ is 0.0 (a measured zero), and the
        # combined cost equals the orchestrator cost.
        self.assertEqual(rep.subagent_cost_usd, 0.0)
        self.assertAlmostEqual(rep.combined_cost_usd, rep.cost_usd, places=9)


class SubagentRobustnessTests(_SubagentTreeMixin, unittest.TestCase):

    def test_malformed_nested_file_skipped_never_throws(self):
        # Corrupt one nested agent file; the OTHER agent's turns still count,
        # and the build must not raise.
        bad = (self.projects / ENC_MAIN / "sessSA" / "subagents"
               / "agent-aaa.jsonl")
        with bad.open("w") as fh:
            fh.write("not json at all\n")
            fh.write('{"type": "assistant", "message": {oops}\n')
        rep = uu.build_report(spec="099", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        # Only agent-bbb (implementer, 2 turns) survives: in 4, out 40,
        # cR 400, cC 4.
        self.assertEqual(rep.subagent_input_tokens, 4)
        self.assertEqual(rep.subagent_output_tokens, 40)
        self.assertEqual(rep.subagent_cache_read_tokens, 400)
        self.assertEqual(rep.subagent_cache_creation_tokens, 4)
        self.assertNotIn("jig:reviewer", rep.subagent_by_type)
        self.assertIn("jig:implementer", rep.subagent_by_type)

    def test_subagent_record_missing_usage_skipped(self):
        # A nested assistant record with no usage key must be skipped, not crash.
        _write_subagents(
            self.projects, ENC_MAIN, "sessSA", "agent-ccc",
            [{"type": "assistant", "isSidechain": True,
              "attributionAgent": "Explore",
              "message": {"role": "assistant", "model": "claude-opus-4-8",
                          "content": []}}],  # no usage
        )
        rep = uu.build_report(spec="099", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        # Subagent totals unchanged by the usage-less Explore turn.
        self.assertEqual(rep.subagent_total_tokens, 11 + 110 + 1100 + 11)
        # Explore contributes a zero-valued breakdown bucket (or none); either
        # way it adds no tokens.
        explore = rep.subagent_by_type.get("Explore")
        if explore is not None:
            self.assertEqual(sum(explore.values()), 0)


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


# ---------------------------------------------------------------------------
# Slice 056-03 — .jig/spec-ref marker attribution (exact session->spec)
# ---------------------------------------------------------------------------

class SpecRefMarkerReadTests(unittest.TestCase):
    """Unit-level tests for the marker reader: it parses the `spec=` line out
    of a `<cwd>/.jig/spec-ref` file and normalizes to a 3-digit number,
    returning None when absent / unreadable / spec-less.
    """

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="jig-usage-marker-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_marker(self, body: str) -> str:
        jig = self._tmp / ".jig"
        jig.mkdir(parents=True, exist_ok=True)
        (jig / "spec-ref").write_text(body)
        return str(self._tmp)

    def test_reads_spec_number_from_marker(self):
        cwd = self._write_marker("spec=056\nslice=056-03\n")
        self.assertEqual(uu.read_spec_ref_marker(cwd), "056")

    def test_marker_spec_is_normalized_to_three_digits(self):
        cwd = self._write_marker("spec=56\nslice=56-03\n")
        self.assertEqual(uu.read_spec_ref_marker(cwd), "056")

    def test_absent_marker_returns_none(self):
        # A cwd with no .jig/spec-ref file.
        self.assertIsNone(uu.read_spec_ref_marker(str(self._tmp)))

    def test_marker_without_spec_line_returns_none(self):
        cwd = self._write_marker("slice=056-03\n")
        self.assertIsNone(uu.read_spec_ref_marker(cwd))

    def test_nonexistent_cwd_returns_none_no_throw(self):
        self.assertIsNone(
            uu.read_spec_ref_marker(str(self._tmp / "does-not-exist")))

    def test_none_cwd_returns_none(self):
        self.assertIsNone(uu.read_spec_ref_marker(None))


class _MarkerTreeMixin:
    """Two sessions for the same repo whose `cwd` points at REAL temp dirs:

      * sessMarker — cwd has a .jig/spec-ref naming spec 070, but its TEXT
        content dominantly mentions a DIFFERENT spec (071). The marker must
        win — proving attribution is by marker, not content, when present.
      * sessHeuristic — cwd has NO marker; content dominantly mentions 070.
        It must fall back to the heuristic and be FLAGGED as heuristic.
    """

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="jig-usage-mtree-"))
        self.projects = self._tmp / "projects"
        self.projects.mkdir()

        # Real cwd dirs (the marker reader stats <cwd>/.jig/spec-ref).
        self.marker_cwd = self._tmp / "wt-marker"
        self.marker_cwd.mkdir()
        (self.marker_cwd / ".jig").mkdir()
        (self.marker_cwd / ".jig" / "spec-ref").write_text(
            "spec=070\nslice=070-01\n")
        self.bare_cwd = self._tmp / "wt-bare"
        self.bare_cwd.mkdir()  # no .jig/spec-ref

        enc_marker = uu.encode_cwd(str(self.marker_cwd))
        enc_bare = uu.encode_cwd(str(self.bare_cwd))
        # A single encoded prefix that spans both (their common ancestor).
        self.prefix = uu.encode_cwd(str(self._tmp))

        # Marker session: content screams 071, marker says 070.
        _write_session(
            self.projects, enc_marker, "sessMarker",
            [
                _user_record(str(self.marker_cwd),
                             "specs/071-decoy spec 071 071-01 071-02 "
                             "specs/071-decoy spec 071.",
                             session="sessMarker"),
                _assistant_record(
                    "claude-opus-4-8",
                    _usage(inp=10, out=20, cache_read=30, cache_create=40),
                    str(self.marker_cwd), session="sessMarker",
                    text="071-01 specs/071-decoy spec 071 everywhere 071-02."),
            ],
        )
        # Bare session: no marker; content dominantly mentions 070.
        _write_session(
            self.projects, enc_bare, "sessHeuristic",
            [
                _user_record(str(self.bare_cwd),
                             "specs/070-real spec 070 070-01.",
                             session="sessHeuristic"),
                _assistant_record(
                    "claude-opus-4-8",
                    _usage(inp=1, out=2, cache_read=3, cache_create=4),
                    str(self.bare_cwd), session="sessHeuristic",
                    text="070-01 specs/070-real spec 070."),
            ],
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)


class MarkerAttributionTests(_MarkerTreeMixin, unittest.TestCase):

    def test_marker_session_attributed_by_marker_not_content(self):
        # The marker session's content dominantly mentions 071, but its
        # marker names 070 — so it must attribute to 070 (marker wins).
        rep = uu.build_report(spec="070", projects_dir=self.projects,
                              encoded_prefix=self.prefix, ccusage_runner=None)
        # Both the marker session AND the bare (heuristic) session land on 070.
        self.assertEqual(rep.session_count, 2)
        # Marker session tokens (10/20/30/40) + bare (1/2/3/4) are both summed.
        self.assertEqual(rep.input_tokens, 11)
        self.assertEqual(rep.output_tokens, 22)
        self.assertEqual(rep.cache_read_tokens, 33)
        self.assertEqual(rep.cache_creation_tokens, 44)

    def test_marker_session_not_attributed_to_content_spec(self):
        # Spec 071 (the content-dominant spec of the marker session) must get
        # NO sessions, because the marker overrides content.
        rep = uu.build_report(spec="071", projects_dir=self.projects,
                              encoded_prefix=self.prefix, ccusage_runner=None)
        self.assertEqual(rep.session_count, 0)

    def test_attribution_method_counts_recorded(self):
        rep = uu.build_report(spec="070", projects_dir=self.projects,
                              encoded_prefix=self.prefix, ccusage_runner=None)
        # One attributed by marker, one by heuristic.
        self.assertEqual(rep.marker_session_count, 1)
        self.assertEqual(rep.heuristic_session_count, 1)

    def test_report_flags_heuristic_sessions(self):
        # AC3: the reader must be able to see that some sessions were
        # attributed heuristically (lower confidence) vs by marker.
        rep = uu.build_report(spec="070", projects_dir=self.projects,
                              encoded_prefix=self.prefix, ccusage_runner=None)
        out = uu.render(rep).lower()
        self.assertIn("marker", out)
        self.assertIn("heuristic", out)
        # The counts surface in the output (1 marker, 1 heuristic).
        self.assertIn("1", uu.render(rep))


class AllMarkerNoHeuristicFlagTests(unittest.TestCase):
    """When every attributed session has a marker, the report should say so
    (no heuristic caveat) — the confidence is high.
    """

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="jig-usage-allmark-"))
        self.projects = self._tmp / "projects"
        self.projects.mkdir()
        self.cwd = self._tmp / "wt"
        self.cwd.mkdir()
        (self.cwd / ".jig").mkdir()
        (self.cwd / ".jig" / "spec-ref").write_text("spec=080\nslice=080-02\n")
        enc = uu.encode_cwd(str(self.cwd))
        self.prefix = uu.encode_cwd(str(self._tmp))
        _write_session(
            self.projects, enc, "sessOnly",
            [
                _assistant_record(
                    "claude-opus-4-8",
                    _usage(inp=5, out=5, cache_read=5, cache_create=5),
                    str(self.cwd), session="sessOnly",
                    text="no spec mentions in text at all"),
            ],
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_marker_attributes_even_with_no_content_mention(self):
        # The session text mentions NO spec, so the heuristic alone would
        # leave it unattributed. The marker rescues it -> attributed to 080.
        rep = uu.build_report(spec="080", projects_dir=self.projects,
                              encoded_prefix=self.prefix, ccusage_runner=None)
        self.assertEqual(rep.session_count, 1)
        self.assertEqual(rep.marker_session_count, 1)
        self.assertEqual(rep.heuristic_session_count, 0)

    def test_all_marker_report_has_no_heuristic_caveat(self):
        rep = uu.build_report(spec="080", projects_dir=self.projects,
                              encoded_prefix=self.prefix, ccusage_runner=None)
        out = uu.render(rep).lower()
        # All attributions are by marker -> exact; no "fell back" caveat.
        self.assertNotIn("fell back", out)
        self.assertNotIn("heuristic (lower confidence)", out)


class MarkerFallbackRegressionTests(_TreeMixin, unittest.TestCase):
    """AC2 fallback: the 056-01 fixture tree has NO markers anywhere, so the
    content heuristic must still drive attribution exactly as before — and
    every attributed session is flagged heuristic.
    """

    def test_no_markers_falls_back_to_heuristic_unchanged(self):
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        # 056-01 expectations are unchanged.
        self.assertEqual(rep.session_count, 2)
        self.assertEqual(rep.total_tokens, 16 + 160 + 1800 + 340)
        # Both attributed by heuristic (no markers present).
        self.assertEqual(rep.marker_session_count, 0)
        self.assertEqual(rep.heuristic_session_count, 2)

    def test_heuristic_only_report_is_flagged(self):
        rep = uu.build_report(spec="055", projects_dir=self.projects,
                              encoded_prefix=ENC_MAIN, ccusage_runner=None)
        out = uu.render(rep).lower()
        self.assertIn("heuristic", out)


if __name__ == "__main__":
    unittest.main()
