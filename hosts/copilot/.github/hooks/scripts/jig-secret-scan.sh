#!/bin/bash
# Secret-scan gate (deliberateness gate — see Rationale): blocks Edit/Write/
# MultiEdit when the PENDING content matches a high-confidence secret pattern,
# unless JIG_SECRET_SCAN_APPROVED=1 is set in the environment.
#
# Fires on PreToolUse / Edit|Write|MultiEdit. Exit 2 to block; exit 0 to allow.
#
# Rationale (see ADR-0013, which borrows ADR-0011's model): this is an
# AGENT-TIME, DEFENSE-IN-DEPTH deliberateness check — NOT a guarantee that a
# secret never reaches history. The hook runs inside the agent's own trust
# boundary, and the override env var is satisfiable by anyone with a shell
# (including the agent itself, via Bash), so it does not enforce anything a
# determined actor can't bypass. What it reliably catches is the ACCIDENTAL
# case: an agent about to write an obvious AWS key, PEM private-key block, or a
# .env secret as a side effect of unrelated work is stopped and told why. Real
# enforcement of "no secret ever reaches history" stays OUT-OF-BAND: CI
# secret-scanning, server-side git hooks, and branch protection.
#
# Ruleset note (refinement-todo / ADR-0013 Scope): this is a CURATED MINIMAL
# set of high-confidence patterns maintained in-tree — jig deliberately does
# NOT bundle a scanner (detect-secrets / gitleaks). The wrap-a-real-detector-
# if-present path is a deferred enhancement; this floor is intentionally
# conservative to keep false positives near zero.
#
# Fails OPEN on any internal error (like jig-spec-gate.sh): a buggy scanner
# must never wedge the agent. No jq — Python 3 for JSON parsing (project rule).
python3 -c "
import sys, json, os, re

try:
    if os.environ.get('JIG_SECRET_SCAN_APPROVED') == '1':
        sys.exit(0)

    data = json.load(sys.stdin)
    tool_name = data.get('tool_name') or ''
    tool_input = data.get('tool_input') or {}
    file_path = tool_input.get('file_path') or tool_input.get('path') or ''

    # Extract the NEW content being written, per tool. Anything else → nothing
    # to scan → allow.
    if tool_name == 'Write':
        content = tool_input.get('content') or ''
    elif tool_name == 'Edit':
        content = tool_input.get('new_string') or ''
    elif tool_name == 'MultiEdit':
        parts = []
        for e in (tool_input.get('edits') or []):
            ns = e.get('new_string')
            if ns:
                parts.append(ns)
        content = '\n'.join(parts)
    else:
        sys.exit(0)

    if not content.strip():
        sys.exit(0)

    # Files that legitimately hold placeholder secrets are never scanned.
    PLACEHOLDER_FILE_SUFFIXES = ('.example', '.sample', '.template', '.dist')
    low_path = file_path.lower()
    if any(low_path.endswith(suf) for suf in PLACEHOLDER_FILE_SUFFIXES):
        sys.exit(0)

    def looks_placeholder(value):
        # Conservative false-positive guard (AC #3): treat obvious
        # non-secrets as placeholders. Keeps the floor quiet on the common
        # 'fill-this-in' shapes that pepper config files and docs.
        v = value.strip().strip('\'\"').strip()
        if not v:
            return True
        if v.startswith('<') or v.startswith('\${') or v.startswith('\$'):
            return True
        if v.endswith('>'):
            return True
        # Runs of x/* used as redaction (e.g. xxxxxxxx, ********).
        if re.fullmatch(r'[x*]{3,}', v, re.IGNORECASE):
            return True
        low = v.lower()
        PLACEHOLDER_WORDS = (
            'example', 'placeholder', 'changeme', 'change-me', 'your-',
            '<your', 'dummy', 'replace', 'todo', 'fixme', 'redacted',
            'xxxx', 'sample', 'test-', 'fake',
        )
        if any(w in low for w in PLACEHOLDER_WORDS):
            return True
        return False

    # Opaque-credential prefixes — high-confidence even when short.
    SECRET_VALUE_PREFIXES = (
        'sk-', 'sk_', 'pk_', 'rk_', 'ghp_', 'gho_', 'ghu_', 'ghs_',
        'github_pat_', 'xox', 'glpat-', 'AIza', 'ya29.', 'eyJ',
        'hf_', 'shpat_', 'npm_', 'dop_v1_',
    )
    # Bare language literals / keywords / type names — never secrets.
    CODE_LITERALS = frozenset((
        'none', 'null', 'nil', 'true', 'false', 'undefined', 'nan',
        'int', 'str', 'float', 'bool', 'bytes', 'list', 'dict', 'set',
        'tuple', 'object', 'any', 'number', 'string', 'boolean', 'char',
    ))
    NUMBER_RE = r'[-+]?(?:0[xXbBoO][0-9A-Fa-f_]+|[0-9][0-9_]*(?:\.[0-9_]*)?(?:[eE][-+]?[0-9]+)?)'

    # looks_like_secret_value: True only when the value looks like an opaque
    # credential token, so ordinary CODE — Python/TS type annotations like
    # int = 0 or Optional[str] = None, bare literals, numbers — is NOT
    # mistaken for a .env secret. ADR-0013: keep the floor conservative; a
    # false negative (missed exotic secret) beats a false positive (blocking
    # normal code). Real enforcement stays out-of-band (CI / server-side).
    def looks_like_secret_value(value):
        v = value.strip()
        # Strip one balanced layer of surrounding quotes.
        if len(v) >= 2 and v[0] in '\'\"' and v[-1] == v[0]:
            v = v[1:-1].strip()
        if not v:
            return False
        # Opaque tokens have no internal whitespace; expressions and
        # annotations (int = 0, Optional[str] = None) do.
        if re.search(r'\s', v):
            return False
        # Bare literals / keywords / type names.
        if v.lower() in CODE_LITERALS:
            return False
        # Pure numeric literals (0, 0.0, -1, 1_000, 0x1f).
        if re.fullmatch(NUMBER_RE, v):
            return False
        # Known credential prefixes are high-confidence on their own.
        if any(v.startswith(p) for p in SECRET_VALUE_PREFIXES):
            return True
        # Code expressions: brackets / calls / comparisons, or an interior
        # '=' (int=0, Optional[int]); trailing base64 '=' padding is allowed.
        if re.search(r'[\[\](){}<>,;]', v):
            return False
        if '=' in v.rstrip('='):
            return False
        # Otherwise require a credential-like profile: a long opaque run
        # mixing character classes (so a bare word or path fragment is safe).
        if len(v) < 12:
            return False
        classes = (
            bool(re.search(r'[a-z]', v))
            + bool(re.search(r'[A-Z]', v))
            + bool(re.search(r'[0-9]', v))
        )
        return classes >= 2

    findings = []  # (rule_name, snippet)

    # Rule 1 — AWS access key id (incl. ASIA temp/session keys). The trailing
    # 16 chars are the body; the EXAMPLE-suffixed canonical key is caught by
    # looks_placeholder below.
    for m in re.finditer(r'(?:AKIA|ASIA)[0-9A-Z]{16}', content):
        if not looks_placeholder(m.group(0)):
            findings.append(('AWS access key id', m.group(0)))
            break

    # Rule 2 — PEM private-key block.
    if re.search(
        r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----',
        content,
    ):
        findings.append(('PEM private key block', 'BEGIN ... PRIVATE KEY'))

    # Rule 3 — .env-style assignment of a secret-named key to a real-looking
    # value. Conservative: the key name must look secret-y, and the value must
    # not look like a placeholder. '=' or ': ' separators (env + yaml-ish).
    SECRET_KEY_RE = re.compile(
        r'(?im)^[ \t]*(?:export[ \t]+)?'
        r'([A-Za-z0-9_.\-]*'
        r'(?:secret|token|password|passwd|api[_-]?key|access[_-]?key|'
        r'private[_-]?key|client[_-]?secret)'
        r'[A-Za-z0-9_.\-]*)'
        r'[ \t]*(?:=|:[ \t])[ \t]*'
        r'(.+?)[ \t]*\$'
    )
    for m in SECRET_KEY_RE.finditer(content):
        key, value = m.group(1), m.group(2)
        if looks_placeholder(value):
            continue
        # The value must look like a real opaque credential — not ordinary
        # code. A bare 'token: true', a type annotation 'tokens: int = 0',
        # or a numeric default must NOT trip the floor (see helper above).
        if not looks_like_secret_value(value):
            continue
        findings.append(('secret-named .env assignment', key))
        break

    if not findings:
        sys.exit(0)

    rule_name, _snippet = findings[0]
    where = file_path or '(unknown file)'
    sys.stderr.write(
        f'Blocked: a high-confidence secret pattern ({rule_name}) was '
        f'detected in the pending content for {where}.\n'
        'This is an agent-time, defense-in-depth deliberateness gate — NOT a '
        'guarantee that secrets never reach history. Real enforcement stays '
        'out-of-band (CI secret-scanning, server-side git hooks, branch '
        'protection).\n'
        'Fix: remove the secret and load it from an env var or a secret '
        'manager; commit a placeholder in a *.example file instead.\n'
        'If this is a deliberate, reviewed exception, set '
        'JIG_SECRET_SCAN_APPROVED=1 in your shell session and retry.\n'
    )
    sys.exit(2)
except SystemExit:
    raise
except Exception as exc:
    sys.stderr.write(f'jig-secret-scan hook error: {exc}\n')
    sys.exit(0)
"
