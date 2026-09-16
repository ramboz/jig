#!/bin/bash
# Fires on UserPromptSubmit. Scans the user's prompt for capitalized references
# (proper nouns, acronyms) not found in the hot cache (CLAUDE.md) or
# docs/memory/glossary.md. Surfaces unknowns as additionalContext so Claude
# can ask about them naturally in the current response.
#
# Heuristic refinements (slice 002-03):
# - Strip fenced + inline code blocks before scanning
# - Strip URL hosts (https://Foo.com → " ")
# - Strip absolute paths (/Users/Foo/Bar → " ")
# - Skip COMMON acronyms (API, JSON, etc.)
#
# Lexicon surfacing (slice 065-02):
# - In ADDITION to unknown-reference surfacing, inject the plain-language
#   `short` definition of any jig lexicon term that appears in the prompt,
#   resolved through skills/_common/lexicon.py (shipped + project glossary
#   overlay). Bounded to 5, first-appearance order. Fully fail-open: any
#   error in the lexicon path leaves the existing behavior intact.
#
# Resolve the directory this script lives in so the embedded Python can locate
# skills/_common/lexicon.py whether jig runs as a plugin
# (${CLAUDE_PLUGIN_ROOT}/hooks/scripts/) or a scaffolded install
# (${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/) — the same idiom as
# jig-context-check.sh. JIG_LEXICON_COMMON_DIR overrides it (test seam).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import sys, json, os, re

try:
    data = json.load(sys.stdin)
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '.')
    prompt = data.get('prompt', '')

    # Strip fenced code blocks (\`\`\`...\`\`\`) — multi-line, non-greedy
    prompt = re.sub(r'\`\`\`.*?\`\`\`', ' ', prompt, flags=re.DOTALL)
    # Strip inline code spans (\`...\`)
    prompt = re.sub(r'\`[^\`]*\`', ' ', prompt)
    # Strip URLs (greedy through non-space)
    prompt = re.sub(r'https?://\S+', ' ', prompt)
    # Strip absolute paths (rough — /word/word/...)
    prompt = re.sub(r'(?<!\w)/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+', ' ', prompt)

    known = set()
    for path in ['CLAUDE.md', 'docs/memory/glossary.md']:
        full = os.path.join(project_dir, path)
        if os.path.exists(full):
            with open(full) as f:
                content = f.read()
            known.update(re.findall(r'\b[A-Z][A-Za-z0-9_-]+\b', content))

    COMMON = {
        'I', 'A', 'The', 'In', 'On', 'At', 'To', 'Of', 'Or', 'And', 'But',
        'For', 'Is', 'It', 'Be', 'Do', 'If', 'As', 'We', 'He', 'She', 'You',
        'My', 'No', 'OK', 'Hi', 'So', 'Go', 'Mr', 'Ms', 'Dr', 'St',
        'API', 'URL', 'HTTP', 'HTTPS', 'JSON', 'XML', 'YAML', 'TOML',
        'CSV', 'TSV', 'PDF', 'HTML', 'CSS', 'CLI', 'GUI', 'IDE', 'PR',
        'UI', 'UX', 'AI', 'ML', 'LLM', 'SDK', 'MCP', 'TDD', 'BDD', 'ADR',
        'CI', 'CD', 'MVP', 'OS', 'DB', 'SQL', 'NoSQL', 'AWS', 'GCP',
    }
    candidates = re.findall(r'\b[A-Z]{2,}|[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', prompt)
    unknowns = [c for c in candidates if c not in known and c not in COMMON]
    unknowns = list(dict.fromkeys(unknowns))

    sections = []

    # ----- Lexicon definitions (slice 065-02) ---------------------------
    # Fully isolated + fail-open: any error here must not affect the existing
    # unknown-reference surfacing below. Surfaces the plain-language 'short'
    # def of any jig lexicon term in the (already-stripped) prompt, bounded to
    # 5 in first-appearance order, resolved via skills/_common/lexicon.py.
    try:
        common_dir = os.environ.get('JIG_LEXICON_COMMON_DIR')
        if not common_dir:
            script_dir = os.environ.get('SCRIPT_DIR', '.')
            common_dir = os.path.join(script_dir, '..', '..', 'skills', '_common')
        if common_dir not in sys.path:
            sys.path.insert(0, common_dir)
        import lexicon as _lex
        merged = _lex.load(project_dir)

        haystack = prompt.lower()
        hits = []
        for key, entry in merged.items():
            # Whole-word / whole-phrase match on a boundary, not a substring.
            pattern = r'(?<![\w-])' + re.escape(key) + r'(?![\w-])'
            m = re.search(pattern, haystack)
            if not m:
                continue
            short = (entry or {}).get('short') if isinstance(entry, dict) else None
            if short:
                hits.append((m.start(), key, short))
        # First-appearance order, then cap at 5.
        hits.sort(key=lambda t: t[0])
        hits = hits[:5]
        if hits:
            lines = ['Jig terms in this prompt (plain-language definitions):']
            for _pos, key, short in hits:
                lines.append(f'- {key}: {short}')
            sections.append('\n'.join(lines))
    except Exception:
        # Never let the lexicon path break the hook or the unknown surfacing.
        pass

    # ----- Unknown-reference surfacing (slice 002-03, unchanged) --------
    if unknowns:
        refs = ', '.join(unknowns)
        msg = (
            f'Unrecognized references in prompt: {refs}. '
            'If these are project-specific terms, ask the user once and persist the answer to '
            'CLAUDE.md (if high-frequency) or docs/memory/glossary.md (if niche).'
        )
        sections.append(msg)

    if sections:
        msg = '\n\n'.join(sections)
        try:
            script_dir = os.environ.get('SCRIPT_DIR', '.')
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
            from lib.read_attribution import append_additional_context_event
            append_additional_context_event(
                project_dir, data.get('session_id') or 'default',
                data.get('hook_event_name') or 'UserPromptSubmit',
                'jig-memory-scan', 'memory_terms', msg)
        except Exception:
            pass
        print(json.dumps({'continue': True, 'additionalContext': msg}))
except Exception:
    pass
"
exit 0
