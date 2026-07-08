"""Tests + CI gate for the deterministic skill-routing eval (spec 086).

The engine lives in `scripts/skill_routing.py`; this file is the gate:

  - engine unit tests on synthetic fixtures (deterministic, model-free);
  - real-data invariants driven by `evals/cases/*.json` — every positive
    trigger routes its owning skill within top_k, every negative routes away,
    and no two real descriptions collide at/above the error threshold.

Run:
    python3 scripts/test_skill_routing.py
    # or from repo root:
    python3 -m unittest scripts.test_skill_routing
"""

from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import skill_routing as sr  # noqa: E402  (sys.path insert first — jig pattern)


class DescriptionReaderTests(unittest.TestCase):
    def test_folded_scalar(self):
        md = "---\nname: x\ndescription: >\n  first line\n  second line\n---\nbody\n"
        self.assertEqual(sr.read_description(md), "first line second line")

    def test_folded_scalar_stops_at_next_key(self):
        md = (
            "---\nname: x\ndescription: >\n  the description\n"
            "user-invocable: true\n---\nbody\n"
        )
        self.assertEqual(sr.read_description(md), "the description")

    def test_plain_scalar(self):
        md = "---\nname: x\ndescription: a one-line description\n---\n"
        self.assertEqual(sr.read_description(md), "a one-line description")

    def test_quoted_scalar(self):
        md = '---\nname: x\ndescription: "quoted desc"\n---\n'
        self.assertEqual(sr.read_description(md), "quoted desc")

    def test_missing_description(self):
        self.assertEqual(sr.read_description("---\nname: x\n---\n"), "")


class RoutingSurfaceTests(unittest.TestCase):
    """Positive-surface reduction (frame-critique 086-01 PRIMARY)."""

    def test_drops_do_not_use_tail(self):
        surf = sr.routing_surface(
            "Lint this project. Use when you say lint this. "
            "Do not use for running tests (use `/jig:tdd-loop`)."
        )
        self.assertIn("lint this project", surf.lower())
        self.assertNotIn("running tests", surf.lower())

    def test_drops_defers_sentence(self):
        surf = sr.routing_surface(
            "Security review. Auto-triggers on any vulnerabilities here. "
            "Defers to any other installed skill whose description handles SAST."
        )
        self.assertIn("vulnerabilities", surf.lower())
        self.assertNotIn("sast", surf.lower())

    def test_strips_skill_pointers(self):
        surf = sr.routing_surface("Use `/jig:analyze` and jig:clarify for drift.")
        self.assertNotIn("jig:analyze", surf)
        self.assertNotIn("jig:clarify", surf)

    def test_keeps_positive_triggers(self):
        surf = sr.routing_surface(
            "Explain jig vocabulary. Auto-triggers when you say what does this "
            "term mean. Do not use for persisting a term (use `/jig:memory-sync`)."
        )
        self.assertIn("term mean", surf.lower())
        self.assertNotIn("persisting", surf.lower())


class TokenizerTests(unittest.TestCase):
    def test_stopwords_and_short_tokens_dropped(self):
        self.assertNotIn("the", sr.tokenize("the a of"))
        self.assertNotIn("skill", sr.tokenize("this skill"))  # house-vocab stop

    def test_light_stemming_folds_inflections(self):
        self.assertEqual(sr._stem("reviews"), "review")
        self.assertEqual(sr._stem("reviewing"), "review")
        self.assertEqual(sr._stem("ambiguities"), "ambiguity")
        # Conservative: do not truncate short words or -ss endings.
        self.assertEqual(sr._stem("class"), "class")


class VectorSpaceTests(unittest.TestCase):
    def test_ubiquitous_term_gets_zero_idf(self):
        # A term in every doc carries no routing signal → idf 0 → drops out.
        corpus = sr.Corpus({"a": "review widget", "b": "review gadget", "c": "review gizmo"})
        self.assertAlmostEqual(corpus.idf["review"], 0.0)
        self.assertNotIn("review", corpus.vectors["a"])

    def test_rank_prefers_lexical_overlap(self):
        corpus = sr.Corpus({
            "auth": "authenticate login sessions and tokens",
            "billing": "invoices payments and refunds",
        })
        top = corpus.rank("fix the login token bug")[0][0]
        self.assertEqual(top, "auth")

    def test_query_term_absent_from_corpus_scores_zero(self):
        corpus = sr.Corpus({"a": "alpha beta", "b": "gamma delta"})
        self.assertEqual(corpus.rank("nonexistent vocabulary")[0][1], 0.0)

    def test_cosine_identical_is_one_disjoint_is_zero(self):
        v = {"x": 1.0, "y": 2.0}
        self.assertAlmostEqual(sr.cosine(v, v), 1.0)
        self.assertEqual(sr.cosine({"x": 1.0}, {"y": 1.0}), 0.0)

    def test_collisions_sorted_descending(self):
        corpus = sr.Corpus({"a": "red blue", "b": "red blue", "c": "green"})
        scores = [s for _, _, s in corpus.collisions()]
        self.assertEqual(scores, sorted(scores, reverse=True))


class RealCorpusTests(unittest.TestCase):
    """Invariants over jig's actual descriptions + authored eval cases."""

    @classmethod
    def setUpClass(cls):
        cls.descriptions = sr.load_descriptions()
        cls.corpus = sr.Corpus(cls.descriptions)
        cls.cases = sr.load_cases()

    def test_no_routable_skill_resolves_empty(self):
        # AC2 (real guard): independently walk every skill dir and assert its
        # description parses non-empty — a folded-scalar reader regression that
        # emptied one description would fail here rather than silently drop the
        # skill from routing. (The old count>=15 check was vacuous because
        # load_descriptions() pre-filters empties.)
        routable = {}
        for skill_dir in sorted(sr.SKILLS_DIR.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith((".", "_")):
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            desc = sr.read_description(skill_md.read_text(encoding="utf-8"))
            self.assertTrue(desc, f"{skill_dir.name}: description parsed empty")
            routable[skill_dir.name] = desc
        self.assertEqual(set(self.descriptions), set(routable))

    def test_case_file_per_routable_skill(self):
        # AC4: every routable skill has a trigger-case file, and no case names a
        # skill that doesn't exist. Add a skill without its case file and this
        # fails — closing the silent "zero routing coverage" gap.
        case_skills = {c["skill_name"] for c in self.cases}
        self.assertEqual(
            set(self.descriptions), case_skills,
            f"skills missing a case file: {sorted(set(self.descriptions) - case_skills)}; "
            f"cases naming no real skill: {sorted(case_skills - set(self.descriptions))}",
        )

    def test_negative_case_owners_are_real_skills(self):
        # A typo'd `owner` silently degrades the pairwise route-away test into
        # the weaker "this skill isn't #1" check — a coverage hole in the guard
        # itself. Fail loudly on an unknown owner.
        for case in self.cases:
            for n in case.get("trigger", {}).get("negative", []):
                owner = n.get("owner")
                if owner is not None:
                    self.assertIn(
                        owner, self.descriptions,
                        f"{case['skill_name']}: negative owner {owner!r} is not a real skill",
                    )

    def test_no_description_pair_collides_at_error_threshold(self):
        for a, b, score in self.corpus.collisions():
            self.assertLess(
                score, sr.COLLISION_ERROR,
                f"{a} × {b} collide at {score:.2f} ≥ {sr.COLLISION_ERROR}",
            )

    def test_authored_cases_exist(self):
        self.assertTrue(self.cases, "no evals/cases/*.json found")

    def test_positive_triggers_route_within_top_k(self):
        # Hard gate: a realistic prompt must at least surface its owner in the
        # top_k. Failing this is an unambiguous routing defect (the description
        # lacks the vocabulary the prompt uses).
        for case in self.cases:
            res = sr.evaluate_case(case, self.corpus)
            for p in res["positive"]:
                with self.subTest(skill=res["skill_name"], prompt=p["prompt"]):
                    self.assertTrue(
                        p["passed"],
                        f"{res['skill_name']} ranked {p['rank']} > top_k {p['top_k']} "
                        f"for «{p['prompt']}» — top3 {p['top3']}",
                    )

    def test_rank1_rate_meets_floor(self):
        # Ratchet: most positives should rank their owner #1. A floor (not
        # 100%) tolerates honest semantic contests while catching regressions.
        rank1 = total = 0
        misses = []
        for case in self.cases:
            for p in sr.evaluate_case(case, self.corpus)["positive"]:
                total += 1
                rank1 += p["rank1"]
                if not p["rank1"]:
                    misses.append(f"{case['skill_name']}@{p['rank']}: «{p['prompt']}»")
        rate = rank1 / total if total else 0.0
        self.assertGreaterEqual(
            rate, sr.MIN_RANK1_RATE,
            f"rank-1 rate {rate:.0%} < floor {sr.MIN_RANK1_RATE:.0%}. Misses:\n  "
            + "\n  ".join(misses),
        )

    def test_negative_route_away_rate_meets_floor(self):
        # Ratchet: a negative prompt should route to its declared owner, not to
        # this skill. Floored (not 100%) to absorb genuine near-ties without
        # gaming descriptions to win a 0.01 lexical margin.
        ok = total = 0
        misses = []
        for case in self.cases:
            for n in sr.evaluate_case(case, self.corpus)["negative"]:
                total += 1
                ok += n["passed"]
                if not n["passed"]:
                    misses.append(
                        f"{case['skill_name']} lost to nobody / owner {n['owner']}"
                        f"({n['owner_rank']}) for «{n['prompt']}»"
                    )
        rate = ok / total if total else 0.0
        self.assertGreaterEqual(
            rate, sr.MIN_NEG_ROUTE_AWAY,
            f"negative route-away rate {rate:.0%} < floor {sr.MIN_NEG_ROUTE_AWAY:.0%}. "
            f"Misses:\n  " + "\n  ".join(misses),
        )


class GateTests(unittest.TestCase):
    """The report's exit-code gates (main) behave as documented.

    Report output is swallowed — these assert on exit codes / return values,
    not prose, and would otherwise flood the suite log with full reports.
    """

    @staticmethod
    def _quiet(fn, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*args)

    def test_min_rank1_flag_parsing(self):
        self.assertEqual(sr._parse_float_flag(["--min-rank1", "0.9"], "--min-rank1"), 0.9)
        self.assertIsNone(sr._parse_float_flag(["--json"], "--min-rank1"))
        with self.assertRaises(SystemExit):
            sr._parse_float_flag(["--min-rank1"], "--min-rank1")

    def test_report_exits_clean_on_real_data(self):
        self.assertEqual(self._quiet(sr.main, []), 0)

    def test_min_rank1_ratchet_can_fail(self):
        # An impossible floor must trip the gate (proves the ratchet has teeth).
        self.assertEqual(self._quiet(sr.main, ["--min-rank1", "1.01"]), 1)

    def test_print_report_returns_tally(self):
        summary = self._quiet(sr.print_report, sr.build_report())
        self.assertEqual(set(summary), {
            "pos_pass", "pos_total", "neg_pass", "neg_total", "rank1", "hazards",
        })


if __name__ == "__main__":
    unittest.main()
