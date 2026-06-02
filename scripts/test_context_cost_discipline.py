"""
Docs-lint for the context-cost discipline section (spec 055-01; extended
in 055-04 to also guard the implementer "surface results, not logs"
instruction, the verbose-Bash rule, and the tdd-loop contract).

Slice 055-01 establishes the thin-orchestrator principle in jig's
workflow: file-heavy reading/analysis is delegated to a read-only
subagent (the built-in `Explore` / `general-purpose`) so that content
never enters the orchestrator's re-read loop. The discipline lives as
standing guidance in `docs/workflow.md`, pointed to from the CLAUDE.md
Hot Cache.

This test fails if that section goes missing or loses a load-bearing
phrase — the principle, the delegate-reads trigger, the named built-in
target, the inline reuse decision, or the worked "$540 session"
anti-pattern — and if the CLAUDE.md template's Hot-Cache pointer
dangles. Mirrors the existing doc-presence tests (e.g. spec 048's
test_adoption_readiness.py).

Run:
    python3 scripts/test_context_cost_discipline.py
    # or from repo root:
    python3 -m unittest scripts.test_context_cost_discipline
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / "docs" / "workflow.md"
TEMPLATE = REPO_ROOT / "templates" / "CLAUDE.md.template"
IMPLEMENTER = REPO_ROOT / "agents" / "implementer.md"
TDD_PY = REPO_ROOT / "skills" / "tdd-loop" / "tdd.py"

HEADING = "Context-cost discipline"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class DisciplineSectionExists(unittest.TestCase):
    """AC #1: the workflow doc gains a 'Context-cost discipline' section
    stating the design principle and the delegate-reads rule."""

    def test_section_heading_present(self) -> None:
        self.assertRegex(
            _read(WORKFLOW),
            rf"(?m)^#+\s+{HEADING}\b",
            "docs/workflow.md must have a 'Context-cost discipline' "
            "heading (spec 055-01 AC #1)",
        )

    def test_states_orchestrator_principle(self) -> None:
        body = _read(WORKFLOW).lower()
        self.assertIn(
            "most expensive real estate", body,
            "the section must state the design principle — the "
            "orchestrator's context is the most expensive real estate, "
            "re-read every turn, so keep it lean (spec 055-01 AC #1)",
        )

    def test_states_delegate_reads_trigger(self) -> None:
        body = _read(WORKFLOW).lower()
        # The concrete trigger: a step that reads more than a couple of
        # files / scans a large or unknown area gets delegated.
        self.assertIn(
            "more than a couple of files", body,
            "the section must give a concrete delegate-reads trigger — "
            "'when a step will read more than a couple of files, or scan "
            "a large/unknown area' (spec 055-01 AC #1)",
        )


class DisciplineNamesBuiltInTarget(unittest.TestCase):
    """AC #2: the section names the built-in `Explore` / `general-purpose`
    agents and specifies the return shape (compact summary, never raw
    file contents)."""

    def test_names_builtin_agents(self) -> None:
        body = _read(WORKFLOW)
        self.assertIn(
            "Explore", body,
            "the section must name the built-in `Explore` delegation "
            "target (spec 055-01 AC #2)",
        )
        self.assertIn(
            "general-purpose", body,
            "the section must name the built-in `general-purpose` "
            "delegation target (spec 055-01 AC #2)",
        )

    def test_specifies_return_shape(self) -> None:
        body = _read(WORKFLOW).lower()
        self.assertIn(
            "summary", body,
            "the section must specify the expected return shape — a "
            "compact structured summary (spec 055-01 AC #2)",
        )
        self.assertIn(
            "never raw file contents", body,
            "the section must say the subagent returns a summary, never "
            "raw file contents (spec 055-01 AC #2)",
        )


class DisciplineRecordsReuseDecision(unittest.TestCase):
    """AC #3: the reuse decision is recorded inline — jig reuses the
    built-ins rather than shipping its own explorer/analyst — and no new
    agents/*.md file is added."""

    def test_records_reuse_decision_inline(self) -> None:
        body = _read(WORKFLOW).lower()
        self.assertIn(
            "reuse", body,
            "the section must record the reuse decision inline — jig "
            "deliberately reuses the built-in agents (spec 055-01 AC #3)",
        )
        # The one-line rationale: avoid duplicating a capable built-in;
        # revisit only if the return contract proves insufficient.
        self.assertIn(
            "return contract", body,
            "the reuse decision must carry its rationale — revisit only "
            "if the return contract proves insufficient (spec 055-01 AC #3)",
        )

    def test_no_new_explorer_agent_added(self) -> None:
        # AC #3's real constraint: jig adds NO bespoke explorer/analyst agent
        # (it reuses the built-in Explore / general-purpose). Assert that
        # intent — no explorer/analyst-named agent file — rather than pinning
        # the exact agent set, which would false-positive on any unrelated
        # future agent (review finding, slice 055-01 reconciliation).
        agents_dir = REPO_ROOT / "agents"
        names = {p.name.lower() for p in agents_dir.glob("*.md")}
        offenders = {n for n in names if "explor" in n or "analyst" in n}
        self.assertEqual(
            offenders,
            set(),
            "spec 055-01 AC #3 forbids a bespoke explorer/analyst agent — jig "
            f"reuses the built-in Explore / general-purpose agents; found {offenders}",
        )


class DisciplineCaptures540AntiPattern(unittest.TestCase):
    """AC #5: the $540 anti-pattern is captured as a worked do/don't
    example (gap-review in the orchestrator vs. delegated reading)."""

    def test_540_example_present(self) -> None:
        body = _read(WORKFLOW)
        self.assertIn(
            "$540", body,
            "the section must include the worked '$540 session' "
            "anti-pattern (spec 055-01 AC #5)",
        )

    def test_540_example_is_do_dont(self) -> None:
        body = _read(WORKFLOW).lower()
        # Worked do/don't framing.
        self.assertIn(
            "don't", body,
            "the $540 example must be framed as a do/don't (spec 055-01 AC #5)",
        )
        self.assertIn(
            "do:", body,
            "the $540 example must be framed as a do/don't (spec 055-01 AC #5)",
        )
        # The case: a gap review run entirely in the orchestrator.
        self.assertIn(
            "985 turns", body,
            "the $540 example must cite the real case — 985 turns, "
            "context climbing to ~840K (spec 055-01 AC #5)",
        )


class CladeMdTemplatePointsToSection(unittest.TestCase):
    """AC #4: the CLAUDE.md template gains a Hot-Cache pointer to the
    discipline section."""

    def test_template_references_discipline(self) -> None:
        body = _read(TEMPLATE)
        self.assertIn(
            HEADING, body,
            "templates/CLAUDE.md.template must carry a Hot-Cache pointer "
            "to the 'Context-cost discipline' section (spec 055-01 AC #4)",
        )

    def test_template_pointer_is_in_hot_cache(self) -> None:
        body = _read(TEMPLATE)
        hot_cache_idx = body.find("## Hot Cache")
        next_h2_idx = body.find("\n## ", hot_cache_idx + 1)
        self.assertNotEqual(hot_cache_idx, -1, "template must have a Hot Cache")
        hot_cache_block = body[hot_cache_idx:next_h2_idx]
        self.assertIn(
            HEADING, hot_cache_block,
            "the Context-cost discipline pointer must live inside the "
            "Hot Cache block (spec 055-01 AC #4)",
        )


class ImplementerSurfacesResultsNotLogs(unittest.TestCase):
    """Slice 055-04 AC #1: agents/implementer.md is updated to make explicit
    that the implementer runs its own test/build commands and surfaces only
    the result (pass/fail + key failing lines) to the orchestrator, not full
    logs."""

    def test_implementer_runs_its_own_commands(self) -> None:
        body = _read(IMPLEMENTER).lower()
        # The implementer runs the verbose commands in its own bounded context.
        self.assertIn(
            "run your own test", body,
            "agents/implementer.md must state the implementer runs its own "
            "test/build commands in its bounded context (spec 055-04 AC #1)",
        )

    def test_implementer_surfaces_result_not_full_logs(self) -> None:
        body = _read(IMPLEMENTER).lower()
        # The load-bearing instruction: surface the result, never full logs.
        self.assertIn(
            "surface only the result", body,
            "agents/implementer.md must instruct surfacing only the result — "
            "pass/fail plus the key failing lines (spec 055-04 AC #1)",
        )
        self.assertIn(
            "pass/fail", body,
            "the surface-only-results instruction must name what 'result' "
            "means — pass/fail plus the key failing lines (spec 055-04 AC #1)",
        )
        self.assertIn(
            "not full logs", body,
            "agents/implementer.md must explicitly exclude full logs from "
            "what the orchestrator receives (spec 055-04 AC #1)",
        )


class DisciplineKeepsVerboseBashOut(unittest.TestCase):
    """Slice 055-04 AC #2/#3: the Context-cost discipline section gains a rule
    that verbose commands belong in a subagent (or a summary), citing the
    ≈19% Bash-output share, and gives concrete idioms."""

    def test_verbose_bash_rule_present(self) -> None:
        body = _read(WORKFLOW).lower()
        # The rule's named cost driver — verbose command output.
        self.assertIn(
            "verbose command output", body,
            "the section must add the verbose-command rule — verbose command "
            "output belongs in a subagent or a summary (spec 055-04 AC #2)",
        )
        # The named verbose offenders.
        self.assertIn(
            "full test runs", body,
            "the rule must name the verbose offenders — full test runs, "
            "builds, long git log/diff (spec 055-04 AC #2)",
        )
        self.assertIn(
            "git log", body,
            "the rule must name long git log/diff among the verbose "
            "offenders (spec 055-04 AC #2)",
        )

    def test_verbose_bash_rule_cites_19pct(self) -> None:
        body = _read(WORKFLOW)
        self.assertIn(
            "19%", body,
            "the verbose-command rule must cite Bash output ≈ 19% of "
            "orchestrator context (spec 055-04 AC #2)",
        )

    def test_verbose_bash_rule_routes_to_subagent(self) -> None:
        body = _read(WORKFLOW).lower()
        # Idiom #1: run the suite via the implementer subagent. Match the
        # phrase, not the bare word "implementer" (which already appears
        # elsewhere in the doc), so this is a real red test for the new rule.
        self.assertIn(
            "run the suite via the implementer", body,
            "the rule must give the concrete idiom — run the suite via the "
            "implementer subagent (spec 055-04 AC #3)",
        )

    def test_verbose_bash_rule_gives_summarize_idiom(self) -> None:
        body = _read(WORKFLOW).lower()
        # Idiom #2: for one-off orchestrator commands, summarize before the
        # output lands — summarizing flags or pipe to a count.
        self.assertIn(
            "summariz", body,
            "the rule must give the summarize idiom for one-off orchestrator "
            "commands (spec 055-04 AC #3)",
        )
        self.assertIn(
            "wc -l", body,
            "the rule must give a concrete reduce-the-output idiom — pipe to "
            "a count (e.g. `… | wc -l`) rather than dumping full output "
            "(spec 055-04 AC #3)",
        )


class TddLoopContractUnchanged(unittest.TestCase):
    """Slice 055-04 AC #4: no regression to the tdd-loop helper contract —
    tdd.py still exposes its normalized 0 green / 1 red / 2 env-error exit
    codes. A source-level guard; runtime behavior is covered by
    skills/tdd-loop/test_tdd.py."""

    def test_tdd_py_exists(self) -> None:
        self.assertTrue(
            TDD_PY.is_file(),
            "skills/tdd-loop/tdd.py must still exist (spec 055-04 AC #4)",
        )

    def test_tdd_py_declares_normalized_exit_codes(self) -> None:
        body = _read(TDD_PY)
        # The contract phrase the helper documents in its run subcommand.
        self.assertIn(
            "0 (green) / 1 (red) / 2 (env error)", body,
            "tdd.py must still declare the normalized 0 green / 1 red / 2 "
            "env-error exit-code contract (spec 055-04 AC #4)",
        )


if __name__ == "__main__":
    unittest.main()
