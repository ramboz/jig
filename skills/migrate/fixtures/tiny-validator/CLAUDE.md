# Tiny validator fixture

This is a synthetic project shaped like aso-shallow-validator. Used by
`migrate.py report` tests to exercise the `adoptable` verdict path:
flat `docs/slices/`, `docs/decisions/` with `adr-` prefix, milestone-
referencing slice frontmatter, a custom skill in `.claude/skills/`.

Real CLAUDE.md content would be larger and project-specific — this is
just enough for the report's Inventory + Mapping + Ambiguities sections
to have rows.
