"""
Docs-lint for the context-cost discipline section (spec 055-01).

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


if __name__ == "__main__":
    unittest.main()
