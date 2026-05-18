"""Surface tests for skills/contracts/SKILL.md (spec 022-01).

Mirrors the surface-test pattern from skills/pr-review/test_skill_surface.py.
Pins every AC for slice 022-01:

  AC #1 — frontmatter is active (no disable-model-invocation; new framing)
  AC #2 — per-surface recommendation table with 6+ surface types
  AC #3 — "nudge, don't mandate" / "when to opt out" language
  AC #4 — worked-example-openapi-http.md exists + key tokens
  AC #5 — worked-example-json-schema-envelope.md exists + key tokens
  AC #6 — deferral hint in description (category-based)
  AC #7 — this file IS the surface-pinning test class set;
          DescriptionBoundsTests is the anti-greediness companion
  AC #8 — no contracts.py exists in skills/contracts/

These tests are pure-file inspections — no subprocess, no runner. They
run under the same `python3 -m unittest discover skills/` invocation
used for every other jig skill.
"""

import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SKILL_MD = SKILL_DIR / "SKILL.md"
WORKED_OPENAPI = SKILL_DIR / "worked-example-openapi-http.md"
WORKED_JSON_SCHEMA = SKILL_DIR / "worked-example-json-schema-envelope.md"


def _frontmatter(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return m.group(1) if m else ""


def _body(text: str) -> str:
    m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.DOTALL)
    return m.group(1) if m else text


def _normalize(s: str) -> str:
    """Match the normalization pattern used by pr-review's tests (slice 012-01):
    YAML folded scalars insert newlines in raw bytes but parse to
    single-space-collapsed strings. Normalize so substring assertions match
    the parsed shape, not the raw bytes."""
    return " ".join(s.lower().split())


_FENCED_BLOCK_RE = re.compile(r"(?ms)^```.*?^```[ \t]*$")


def _strip_fenced_blocks(text: str) -> str:
    """Remove fenced ```...``` regions so H2/H3-shaped lines inside code
    examples don't trip the `_h2_positions` regex helper.
    Offsets refer to the returned (stripped) body, not the source."""
    return _FENCED_BLOCK_RE.sub("", text)


class FrontmatterTests(unittest.TestCase):
    """AC #1 — active frontmatter (name + user-invocable + no disable)."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(
            SKILL_MD.is_file(),
            f"skills/contracts/SKILL.md must exist at {SKILL_MD}",
        )

    def test_has_frontmatter_block(self):
        fm = _frontmatter(self.text)
        self.assertTrue(fm, "SKILL.md must start with a YAML frontmatter block")

    def test_name_field(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^name:\s*contracts\s*$")

    def test_user_invocable_true(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^user-invocable:\s*true\s*$")

    def test_no_disable_model_invocation(self):
        # AC #1 — the skill is no longer a stub; it auto-triggers.
        # If a future fallback ever flips this, that's a separate slice.
        fm = _frontmatter(self.text)
        self.assertNotIn("disable-model-invocation: true", fm)


class DescriptionTests(unittest.TestCase):
    """AC #1 / AC #6 — description opens with the team-baseline framing,
    contains trigger phrases, deferral hint, "do not use for" carve-outs."""

    @classmethod
    def setUpClass(cls):
        cls.fm = _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.normalized = _normalize(cls.fm)

    def test_one_sentence_summary(self):
        self.assertIn(
            "team baseline for external-interface contract artifacts",
            self.normalized,
        )

    def test_six_trigger_phrases(self):
        phrases = [
            "what contract should i use for this api",
            "do we have an openapi spec",
            "add a json schema for this",
            "recommend a schema for this endpoint",
            "validate this api contract",
            "what's the right artifact for events",
        ]
        for phrase in phrases:
            self.assertIn(
                phrase, self.normalized,
                f"description missing trigger phrase: {phrase!r}",
            )

    def test_artifact_names_present(self):
        # AC #1 names the per-surface artifacts at a high level.
        for token in ["openapi", "json schema", "asyncapi", ".proto", "graphql sdl"]:
            self.assertIn(
                token, self.normalized,
                f"description missing artifact token: {token!r}",
            )

    def test_ecosystem_tools_present(self):
        # AC #1 names the ecosystem tools the skill orchestrates.
        for token in ["spectral", "ajv", "buf", "graphql-inspector"]:
            self.assertIn(
                token, self.normalized,
                f"description missing ecosystem tool: {token!r}",
            )

    def test_deferral_hint_present(self):
        # AC #6 — category-based deferral hint (mirrors 012-01 / 014-01).
        self.assertIn(
            "defers to any other installed skill whose description "
            "identifies it as handling external-interface contract "
            "artifacts, api schema design, or contract-first workflow",
            self.normalized,
        )

    def test_do_not_use_clause_names_carve_outs(self):
        self.assertRegex(self.normalized, r"do not use")
        # Carve-out: internal module-boundary refactoring (ADR-0002 stub).
        self.assertIn("internal module-boundary refactoring", self.normalized)
        # Carve-out: scaffolding a contracts/ dir (out per ADR-0005).
        self.assertIn("scaffolding a contracts/ directory", self.normalized)
        # Carve-out: auto-generating schemas from code (skill recommends).
        self.assertIn("auto-generating schemas from code", self.normalized)

    def test_nudge_framing_in_description(self):
        # AC #1 / AC #3 — the description itself signals nudge-not-mandate.
        self.assertIn("nudges devs", self.normalized)
        # The skill never writes / never scaffolds — boundary-statements,
        # not active over-claims.
        self.assertIn("never writes them", self.normalized)
        self.assertIn("never scaffolds a", self.normalized)


class DescriptionBoundsTests(unittest.TestCase):
    """AC #7 (anti-greediness) — the normalized description does NOT contain
    over-claiming phrases that would shadow a richer user-installed skill."""

    @classmethod
    def setUpClass(cls):
        cls.fm = _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.normalized = _normalize(cls.fm)

    def test_no_over_claiming_phrases(self):
        forbidden = [
            "generates openapi for you",
            "scaffolds your contracts",
            "writes the schema for you",
            "auto-generated contracts",
            "comprehensive contract",
            "enforces all contracts",
            "deep schema analysis",
            "complete schema validation",
            "full contract audit",
            "expert-level",
            "multi-persona",
        ]
        for phrase in forbidden:
            self.assertNotIn(
                phrase, self.normalized,
                f"description over-claims with phrase: {phrase!r}",
            )


class BodyTests(unittest.TestCase):
    """AC #1 / AC #3 — body has the canonical H2 sections in order."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def _h2_positions(self, body: str):
        body = _strip_fenced_blocks(body)
        results = []
        for m in re.finditer(r"(?m)^##\s+(.+?)\s*$", body):
            results.append((m.group(1).lower(), m.start()))
        return results

    def test_fenced_block_h2_h3_are_ignored(self):
        synthetic = (
            "## Real H2\n"
            "Text.\n"
            "```\n"
            "## Fake H2 in code block\n"
            "### Fake H3 in code block\n"
            "```\n"
            "### Real H3\n"
        )
        headings = [h for h, _ in self._h2_positions(synthetic)]
        self.assertIn("real h2", headings)
        self.assertNotIn("fake h2 in code block", headings)

    def test_has_what_this_skill_does(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("what this skill does" in h for h, _ in positions),
            f"missing 'What this skill does' H2; found: {[h for h, _ in positions]}",
        )

    def test_has_when_to_use_vs_defer(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("when to use" in h and "defer" in h for h, _ in positions),
            "missing 'When to use vs. when to defer' H2",
        )

    def test_has_per_surface_recommendations(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("per-surface" in h for h, _ in positions),
            "missing 'Per-surface artifact recommendations' H2",
        )

    def test_has_when_to_opt_out(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("opt out" in h or "opt-out" in h for h, _ in positions),
            "missing 'When to opt out' H2",
        )

    def test_has_worked_examples(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("worked example" in h for h, _ in positions),
            "missing 'Worked examples' H2",
        )

    def test_has_gotchas(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("gotchas" in h for h, _ in positions),
            "missing 'Gotchas' H2",
        )

    def test_has_relationship_to_other_skills(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("relationship to other skills" in h for h, _ in positions),
            "missing 'Relationship to other skills' H2",
        )

    def test_sections_in_order(self):
        """Sections must appear in the order specified by the skill's design."""
        body_lower = self.body.lower()
        expected_order = [
            "what this skill does",
            "when to use",
            "per-surface artifact recommendations",
            "when to opt out",
            "worked examples",
            "gotchas",
            "relationship to other skills",
        ]
        positions = []
        for phrase in expected_order:
            idx = body_lower.find(phrase)
            self.assertGreater(
                idx, -1,
                f"section header {phrase!r} not found in body",
            )
            positions.append(idx)
        self.assertEqual(
            positions, sorted(positions),
            f"section order wrong; got positions {positions} for {expected_order}",
        )


class PerSurfaceTableTests(unittest.TestCase):
    """AC #2 — the per-surface recommendation table covers at least 6 surface
    types, each with the canonical artifact + validation + codegen tools."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.body_lower = cls.body.lower()

    def test_table_has_required_columns(self):
        # The table header row must list the four logical columns. We don't
        # require an exact column-name match; we require the conceptual
        # tokens are present somewhere in the table region.
        for token in ["surface", "artifact", "validation", "codegen", "rationale"]:
            self.assertIn(
                token, self.body_lower,
                f"per-surface table missing column concept: {token!r}",
            )

    def test_table_header_row_locked(self):
        """Stricter than test_table_has_required_columns: requires the five
        column-concept tokens to appear together in a single pipe-delimited
        markdown header row. Catches the failure mode where the table is
        deleted but those tokens still appear scattered in body prose."""
        pattern = re.compile(
            r"\|[^|\n]*surface[^|\n]*\|[^|\n]*artifact[^|\n]*\|"
            r"[^|\n]*validation[^|\n]*\|[^|\n]*codegen[^|\n]*\|"
            r"[^|\n]*rationale[^|\n]*\|",
            re.IGNORECASE,
        )
        self.assertIsNotNone(
            pattern.search(self.body),
            "per-surface table header row must contain Surface | Artifact | "
            "Validation | Codegen | Rationale (in some recognizable form)",
        )

    def test_six_surface_types_present(self):
        # AC #2 — at least these six surfaces are covered.
        surfaces = [
            "http api",
            "event bus",
            "rpc",
            "graphql",
            "internal data shapes",
            "config / env vars",
        ]
        for surface in surfaces:
            self.assertIn(
                surface, self.body_lower,
                f"per-surface table missing surface row: {surface!r}",
            )

    def test_canonical_artifacts_present(self):
        # Each surface row names its canonical artifact.
        for artifact in [
            "openapi 3",       # HTTP
            "asyncapi",        # events
            ".proto",          # RPC
            "schema.graphql",  # GraphQL
            "*.schema.json",   # internal data shapes
        ]:
            self.assertIn(
                artifact.lower(), self.body_lower,
                f"per-surface table missing artifact: {artifact!r}",
            )

    def test_validation_tools_present(self):
        for tool in ["spectral", "ajv", "buf lint", "graphql-inspector"]:
            self.assertIn(
                tool, self.body_lower,
                f"per-surface table missing validation tool: {tool!r}",
            )


class NudgeLanguageTests(unittest.TestCase):
    """AC #3 — body has an explicit "When to opt out" subsection covering
    migration scenarios + structural-enforcement framing from 022-02."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.body_lower = cls.body.lower()

    def test_nudge_not_refuse_statement(self):
        # AC #3 explicitly: "structural enforcement, not jig refusing edits."
        self.assertIn("nudges; it does not refuse edits", self.body_lower)

    def test_021_02_touchpoints_referenced(self):
        # AC #3: the structural touchpoints (022-02 wiring) are noted.
        self.assertIn("022-02", self.body_lower)
        self.assertIn("/jig:vision-elicitation", self.body_lower)
        self.assertIn("review.py", self.body_lower)

    def test_opt_out_scenarios_covered(self):
        scenarios = [
            "migration of a project with a working bespoke pattern",
            "one-off internal tool",
            "pre-existing different artifact",
            "pre-product-market-fit prototype",
        ]
        for s in scenarios:
            self.assertIn(
                s, self.body_lower,
                f"opt-out section missing scenario: {s!r}",
            )

    def test_adr_workflow_referenced_for_structural_opt_out(self):
        # AC #3 + Relationship-to-other-skills: ADR captures the rationale
        # when a project opts out structurally.
        self.assertIn("/jig:adr-workflow", self.body_lower)


class DeferralLanguageTests(unittest.TestCase):
    """Body explicitly references `~/.claude/skills/contracts/` as the
    deferral target (mirrors pr-review's body-level deferral hint)."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def test_body_references_user_skill_path(self):
        self.assertIn("~/.claude/skills/contracts", self.body)


class WorkedExampleOpenAPITests(unittest.TestCase):
    """AC #4 — the OpenAPI worked-example file exists and shows the
    before / after / CI-gate / codegen story."""

    @classmethod
    def setUpClass(cls):
        cls.exists = WORKED_OPENAPI.is_file()
        cls.text = WORKED_OPENAPI.read_text() if cls.exists else ""
        cls.text_lower = cls.text.lower()

    def test_file_exists(self):
        self.assertTrue(
            self.exists,
            f"worked example #1 must exist at {WORKED_OPENAPI}",
        )

    def test_references_aso_shallow_validator_as_source(self):
        # AC #4 — source-of-record is aso-shallow-validator §5.
        self.assertIn("aso-shallow-validator", self.text_lower)
        self.assertIn("architecture.md", self.text_lower)

    def test_has_before_and_after_sections(self):
        for phrase in ["## before", "## after"]:
            self.assertIn(
                phrase, self.text_lower,
                f"OpenAPI worked example missing section: {phrase!r}",
            )

    def test_shows_openapi_yaml_fragment(self):
        self.assertIn("openapi: 3", self.text_lower)
        # Sanity — the example shows a `paths:` block with at least one path.
        self.assertIn("paths:", self.text_lower)
        self.assertIn("components:", self.text_lower)

    def test_wires_spectral_ci_gate(self):
        self.assertIn("spectral", self.text_lower)
        self.assertIn("npm run lint:openapi", self.text_lower)

    def test_calls_openapi_typescript_codegen(self):
        self.assertIn("openapi-typescript", self.text_lower)


class WorkedExampleJSONSchemaTests(unittest.TestCase):
    """AC #5 — the JSON Schema worked-example file exists and shows the
    schema artifact + ajv validation + stack-coupled alternatives."""

    @classmethod
    def setUpClass(cls):
        cls.exists = WORKED_JSON_SCHEMA.is_file()
        cls.text = WORKED_JSON_SCHEMA.read_text() if cls.exists else ""
        cls.text_lower = cls.text.lower()

    def test_file_exists(self):
        self.assertTrue(
            self.exists,
            f"worked example #2 must exist at {WORKED_JSON_SCHEMA}",
        )

    def test_shows_json_schema_artifact(self):
        # Schema URI + a $schema field — both surface a real JSON Schema.
        self.assertIn("$schema", self.text)
        self.assertIn("json-schema.org/draft", self.text)

    def test_validates_with_ajv(self):
        self.assertIn("ajv", self.text_lower)
        # Both producer and consumer paths are shown.
        self.assertIn("producer", self.text_lower)
        self.assertIn("consumer", self.text_lower)

    def test_calls_codegen(self):
        # AC #5 — codegen is shown (quicktype OR json-schema-to-typescript).
        codegen_tools = ["quicktype", "json-schema-to-typescript"]
        self.assertTrue(
            any(tool in self.text_lower for tool in codegen_tools),
            f"worked example missing codegen tool from {codegen_tools}",
        )

    def test_notes_stack_coupled_alternatives(self):
        # AC #5 — Zod / Pydantic / TypeBox called out as opt-outs.
        for alt in ["zod", "pydantic", "typebox"]:
            self.assertIn(
                alt, self.text_lower,
                f"worked example missing stack-coupled alternative: {alt!r}",
            )


class NoPyHelperTests(unittest.TestCase):
    """AC #8 — skills/contracts/ does NOT gain a contracts.py helper."""

    def test_no_contracts_py(self):
        py_file = SKILL_DIR / "contracts.py"
        self.assertFalse(
            py_file.is_file(),
            f"AC #8: skills/contracts/contracts.py must not exist (found at {py_file})",
        )


if __name__ == "__main__":
    unittest.main()
