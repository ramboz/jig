"""Shared skill-discovery primitives — spec 096-02 (ADR-0040 D2).

The zero-config richer-skill layer needs two deterministic, host-portable
primitives, built here so 096-03's candidate channel can compose them:

  1. **Name → path resolution across scopes** (`resolve_skill_path`): resolve a
     bare skill name to an existing `SKILL.md`, searching project → user →
     admin/plugin scope, on either host (Claude / Codex). Conservative on every
     error; `$HOME`-honoring; returns `None` on miss.
  2. **jig-baseline exclusion** (`is_jig_baseline_path`): jig's own shipped
     baselines are machine-identifiable *by path* — a `jig-`-prefixed dir at
     project scope (what `scaffold-init` writes; `migrate.py` already uses this
     discriminator), or a skill under a `jig` plugin directory at admin scope
     (the plugin is named `jig` on both hosts). No frontmatter marker is needed
     (ADR-0040 D2 / OQ4 resolved: a path test suffices, so no host-package
     regeneration and no forward-only migration problem).

Plus a tolerant frontmatter reader (`parse_skill_frontmatter`) that extracts
`name` + `description`, handling the plain / folded (`>`) / literal (`|`) YAML
scalar shapes both hosts' skills actually use — malformed / absent frontmatter
yields `None`, never an exception.

**The load-bearing exclusion invariant** (tested in 096-02): every user-facing
skill a jig scaffold writes at project scope is `jig-` prefixed, and the only
*unprefixed* things a scaffold writes carry no `SKILL.md` (the `_`-prefixed
shared modules and the Codex logical-name alias). So "a project-scope candidate
must carry a `SKILL.md`, and `jig-`-prefixed ones are jig's own" cleanly
separates jig baselines from genuine richer skills — for old AND new scaffolds,
with no migration.

`_common` is a LEAF: stdlib only (mirrors `project_layout.py`; note
`review_config` is NOT a leaf — it imports THIS module). `$HOME`-honoring
(`Path.home()`), so it is hermetically testable.
"""

from __future__ import annotations

import re
from pathlib import Path

# Host identifiers.
CLAUDE = "claude"
CODEX = "codex"

# The `jig-` project-scope prefix `scaffold-init` writes + `migrate.py` keys on.
_JIG_PREFIX = "jig-"
# The plugin directory name on both hosts (hosts/codex/plugins/jig,
# Claude plugin.json name "jig").
_JIG_PLUGIN_SEGMENT = "jig"


def scope_roots(host: str, project_dir: Path, home: "Path | None" = None,
                admin_roots: "list[Path] | None" = None) -> "list[Path]":
    """The skill-container directories to search, in precedence order
    (project → user → admin/plugin), for `host`.

    `admin_roots` is injectable (hermetic tests supply their own); when omitted,
    host defaults are used. `home` defaults to `Path.home()` (honors `$HOME`)."""
    home = Path.home() if home is None else home
    project_dir = Path(project_dir)
    if host == CODEX:
        roots = [project_dir / ".agents" / "skills",
                 home / ".agents" / "skills"]
        admins = admin_roots if admin_roots is not None \
            else [Path("/etc/codex/skills")]
    else:  # CLAUDE
        roots = [project_dir / ".claude" / "skills",
                 home / ".claude" / "skills"]
        admins = admin_roots if admin_roots is not None \
            else _default_claude_admin_roots(home)
    roots.extend(admins)
    return roots


def _default_claude_admin_roots(home: Path) -> "list[Path]":
    """Best-effort installed-plugin skill roots for Claude: each plugin's
    `skills/` dir under `~/.claude/plugins`. jig's own cache layout nests a few
    levels (`plugins/cache/<mkt>/<plugin>/<ver>/skills`), so glob a couple of
    depths. Conservative: any glob error yields no admin roots."""
    base = home / ".claude" / "plugins"
    roots: list[Path] = []
    try:
        if not base.is_dir():
            return roots
        for pattern in ("*/skills", "*/*/skills", "*/*/*/skills",
                        "*/*/*/*/skills"):
            roots.extend(sorted(p for p in base.glob(pattern) if p.is_dir()))
    except OSError:
        return []
    return roots


def is_jig_baseline_path(skill_md: Path) -> bool:
    """True iff `skill_md` (a `.../<skill>/SKILL.md` path) is one of jig's own
    shipped baselines, identified purely by path (ADR-0040 D2):

      - its immediate skill directory is `jig-`-prefixed (project-scope
        scaffold copy — `.claude/skills/jig-pr-review/SKILL.md`), OR
      - a `jig` plugin directory appears **under a `plugins/` ancestor** on its
        path (admin/plugin scope — `.../plugins/**/jig/**/skills/<skill>/SKILL.md`;
        the jig plugin is named `jig` on both hosts).

    The admin test is **anchored to a `plugins/` ancestor** — NOT a bare `jig`
    segment anywhere — so a genuine richer skill at project scope inside a
    directory that merely happens to contain `jig` (jig's own repo while
    dogfooding, a checkout under `.../misc/jig/...`) is NOT misclassified as a
    baseline. Matching `jig` anywhere was a fail-*closed* false positive that
    would silently hide a genuine richer skill — the exact bug this spec exists
    to fix (caught by the 096-02 arch/craft passes).

    Conservative: any path error → False. False means "treat as a genuine
    candidate" — the safe direction, since a genuine richer skill is never
    wrongly hidden; a mis-shaped jig path merely slips through, which the
    project-scope `jig-` prefix and the invariant test guard against."""
    try:
        skill_md = Path(skill_md)
        skill_dir = skill_md.parent
        if skill_dir.name.startswith(_JIG_PREFIX):
            return True
        # Admin/plugin scope: a `jig` segment AT OR AFTER a `plugins/` ancestor.
        # (Above the skill dir itself — for a jig baseline the skill dir is the
        # unprefixed skill name inside the jig plugin, e.g.
        # .../plugins/**/jig/.../skills/pr-review.)
        parts = skill_dir.parent.parts
        if "plugins" in parts:
            plugins_idx = parts.index("plugins")
            if _JIG_PLUGIN_SEGMENT in parts[plugins_idx:]:
                return True
        return False
    except (OSError, ValueError):
        return False


def resolve_skill_path_any_host(name: str, *, project_dir: Path,
                                home: "Path | None" = None,
                                exclude_jig_baselines: bool = False
                                ) -> "str | None":
    """Resolve a bare skill `name` on EITHER host (Claude scopes first, then
    Codex), returning the first existing `SKILL.md` or `None`. Host-agnostic
    resolution for a config value that names a skill without knowing which host
    it is installed under (spec 096-01 config bare names — this closes the
    Codex bare-name seam 096-01 left open).

    Precedence is Claude-then-Codex, each host fully swept (project → user →
    admin) before the next. A config value names a *single* skill installed on
    whichever host the developer uses, so a same-name collision across BOTH
    hosts is pathological; the deterministic Claude-first order is the documented
    tiebreak rather than a host-adaptive heuristic."""
    for host in (CLAUDE, CODEX):
        got = resolve_skill_path(
            name, host=host, project_dir=project_dir, home=home,
            exclude_jig_baselines=exclude_jig_baselines,
        )
        if got is not None:
            return got
    return None


def resolve_skill_path(name: str, *, host: str, project_dir: Path,
                       home: "Path | None" = None,
                       admin_roots: "list[Path] | None" = None,
                       exclude_jig_baselines: bool = False) -> "str | None":
    """Resolve a bare skill `name` to an existing `SKILL.md`, searching scopes in
    precedence order (project → user → admin). Returns the first match as a
    string, or `None` when unresolvable.

    `exclude_jig_baselines=True` skips any match that `is_jig_baseline_path`
    identifies as jig's own — the DISCOVERY mode (a jig baseline must never be
    offered back as "richer"). Config resolution (096-01) uses the default
    `False` — explicit config overrides exclusion.

    Conservative on every error (a `stat`/permissions failure on one scope never
    raises — that scope is skipped). Deterministic + order-stable for a given
    filesystem state."""
    for root in scope_roots(host, project_dir, home, admin_roots):
        try:
            candidate = Path(root) / name / "SKILL.md"
            if not candidate.is_file():
                continue
            if exclude_jig_baselines and is_jig_baseline_path(candidate):
                continue
            return str(candidate)
        except (OSError, ValueError):
            continue
    return None


# -- tolerant name/description frontmatter reader (AC2) --------------------

_FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


def parse_skill_frontmatter(text: str) -> "dict | None":
    """Extract `{'name': ..., 'description': ...}` from a SKILL.md's leading
    frontmatter, tolerating plain, folded (`>`) and literal (`|`) block scalars.

    Returns `None` when there is no frontmatter block. Missing keys are simply
    absent from the returned dict (never an exception). Never raises on a
    malformed body — best-effort extraction only."""
    m = _FM_RE.match(text or "")
    if not m:
        return None
    body = m.group(1)
    lines = body.splitlines()
    out: dict = {}
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.startswith((" ", "\t")) or ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if key not in ("name", "description"):
            i += 1
            continue
        if rest in (">", "|", ">-", "|-", ">+", "|+"):
            # Block scalar: gather subsequent more-indented lines.
            block: list[str] = []
            j = i + 1
            while j < n and (lines[j].startswith((" ", "\t")) or
                             not lines[j].strip()):
                block.append(lines[j].strip())
                j += 1
            joiner = "\n" if rest.startswith("|") else " "
            out[key] = joiner.join(b for b in block if b).strip()
            i = j
            continue
        # Plain scalar, optionally quoted.
        out[key] = rest.strip().strip('"').strip("'")
        i += 1
    return out
