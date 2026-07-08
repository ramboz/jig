"""Deterministic skill-routing eval engine (spec 086).

jig routes work to skills entirely through their SKILL.md `description:` — the
host surfaces every skill's description each session and the model picks (spec
076 / EngTip #23). Nothing currently guards that mechanism: two descriptions
can drift toward each other until the model can no longer tell them apart, and
a description can silently lose the vocabulary users actually say until the
right skill stops ranking for a realistic prompt.

This is the "Tier 2" deterministic, CI-safe routing check borrowed from
addyosmani/agent-skills (which in turn borrowed the eval-case shape from
Anthropic's skill-creator). It is a *lexical approximation* of routing —
stemmed TF-IDF cosine over descriptions — so it cannot judge semantics (that
would need a behavioral pass through a real model). What it does catch are the
two failure modes that dominate real routing bugs:

  - false negative — a description missing the vocabulary a realistic prompt
    uses, so the owning skill fails to rank top-k for that prompt;
  - collision — two descriptions so similar the model cannot route between
    them.

Zero-dependency and pure-Python (jig helpers run on the adopter's `python3`;
3.9 floor). The tokenizer/stemmer are deliberately simple and swappable — a
Porter stemmer or a real embedding model could drop in behind the same API.

Run the human-readable report:

    python3 scripts/skill_routing.py            # report over all skills + cases
    python3 scripts/skill_routing.py --json     # machine-readable

The assertions that gate CI live in `scripts/test_skill_routing.py`.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
CASES_DIR = REPO_ROOT / "evals" / "cases"

# Collision thresholds (addyosmani/agent-skills' values): a pair at/above ERROR
# is a routing hazard; at/above WARN is worth a look. jig descriptions share a
# lot of house vocabulary ("spec", "slice", "review"), so IDF down-weighting is
# load-bearing — without it every pair would look similar.
COLLISION_ERROR = 0.75
COLLISION_WARN = 0.50

# Floor ratchets for the CI gate (scripts/test_skill_routing.py). Set
# CONSERVATIVELY below the current baseline (rank-1 95%, negatives 100%) — the
# ~10pp slack is deliberate: honest case churn or a single legitimate semantic
# contest shouldn't fail CI or get "fixed" by stuffing keywords, while a real
# regression (a large rank-1 / route-away drop) still trips. Raise-only, toward
# the baseline, as the corpus stabilizes.
MIN_RANK1_RATE = 0.85       # share of positives whose owner ranks #1
MIN_NEG_ROUTE_AWAY = 0.90   # share of negatives where the owner outranks

# Words that carry no routing signal: generic English + jig-wide vocabulary
# present in nearly every description. IDF already suppresses ubiquitous terms,
# but stripping the obvious noise keeps the vectors and the report readable.
_STOPWORDS = frozenset(
    """
    a an the this that these those and or but if then else when while for to of
    in on at by with from into onto out up down over under is are was were be
    been being do does did done has have had it its as not no nor so than too
    very can will just use used using where what which who whom whose how
    you your yours we our ours they their them
    skill skills jig
    """.split()
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


# --------------------------------------------------------------------------- #
# Description extraction                                                        #
# --------------------------------------------------------------------------- #
def read_description(skill_md_text: str) -> str:
    """Extract the `description:` value from SKILL.md frontmatter.

    Every jig skill writes its description as a YAML *folded* block scalar
    (`description: >` + indented continuation lines), which `_common`'s
    YAML-lite `parse_frontmatter` does not decode — hence this dedicated
    reader. Handles the three shapes that occur in practice:

      description: single line
      description: >   (folded)
      description: |   (literal)

    Both block forms are joined with single spaces here — the raw text is only
    tokenized for TF-IDF, so preserving literal newlines would buy nothing.
    """
    m = _FM_RE.match(skill_md_text)
    block = m.group(1) if m else skill_md_text
    lines = block.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        rest = line[len("description:"):].strip()
        if rest and rest not in (">", "|", ">-", "|-", ">+", "|+"):
            return rest.strip("\"'")
        # Block scalar: gather the indented continuation until dedent.
        collected: list[str] = []
        for cont in lines[i + 1:]:
            if cont.strip() and not cont.startswith((" ", "\t")):
                break  # dedent — next top-level key
            collected.append(cont.strip())
        return " ".join(part for part in collected if part).strip()
    return ""


_NEGATIVE_TAIL_RE = re.compile(r"(?i)\bdo\s+not\s+use\b")
_DEFERS_SENTENCE_RE = re.compile(r"(?i)\b(?:defers to|does not defer)\b.*?(?:\.|$)")
_SKILL_POINTER_RE = re.compile(r"/?\bjig:[a-z0-9-]+")


def routing_surface(description: str) -> str:
    """Reduce a description to the *positive* routing surface it should be
    matched on — what the skill is FOR — dropping the negative-disambiguation
    scaffolding (frame-critique 086-01, PRIMARY finding).

    jig descriptions disambiguate siblings with shared boilerplate — a
    ``Do not use for: … (use `/jig:X` instead)`` tail and ``Defers to any other
    installed skill …`` sentences. That cross-reference vocabulary is what
    teaches the *model* to route siblings apart, but as raw TF-IDF input it
    reads as *similarity* among exactly the hardest-to-route cluster, and it
    also makes a skill spuriously match a prompt describing what it explicitly
    does NOT do. Stripping it means the collision + trigger signals measure
    positive-territory overlap — the real routing hazard — not shared
    disclaimers.
    """
    m = _NEGATIVE_TAIL_RE.search(description)
    text = description[: m.start()] if m else description
    text = _DEFERS_SENTENCE_RE.sub(" ", text)
    text = _SKILL_POINTER_RE.sub(" ", text)
    return text


def load_descriptions(skills_dir: Path = SKILLS_DIR) -> "dict[str, str]":
    """Map skill name -> description for every `skills/*/SKILL.md`."""
    out: dict[str, str] = {}
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith((".", "_")):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        desc = read_description(skill_md.read_text(encoding="utf-8"))
        if desc:
            out[skill_dir.name] = desc
    return out


# --------------------------------------------------------------------------- #
# Tokenize / stem / TF-IDF                                                      #
# --------------------------------------------------------------------------- #
def _stem(token: str) -> str:
    """Conservative inflection stripper (deterministic, no over-merging).

    Deliberately light so the report stays interpretable. Only the most common
    inflections are folded; swap in Porter here if recall matters more than
    legibility.
    """
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> "list[str]":
    """Lowercase → split → drop stopwords/short tokens → light stem."""
    toks = []
    for raw in _TOKEN_RE.findall(text.lower()):
        if len(raw) < 2 or raw in _STOPWORDS:
            continue
        stemmed = _stem(raw)
        if stemmed in _STOPWORDS:
            continue
        toks.append(stemmed)
    return toks


class Corpus:
    """TF-IDF vector space over the skill descriptions."""

    def __init__(self, descriptions: "dict[str, str]"):
        self.descriptions = dict(descriptions)
        self.names = list(descriptions)
        # Vectorize the positive routing surface, not the raw description — the
        # negative-disambiguation tail is scaffolding, not trigger vocabulary
        # (frame-critique 086-01 PRIMARY). Full text is retained in
        # `self.descriptions` for display.
        self._tokens = {n: tokenize(routing_surface(d)) for n, d in descriptions.items()}
        n_docs = max(len(self.names), 1)
        df: dict[str, int] = {}
        for toks in self._tokens.values():
            for term in set(toks):
                df[term] = df.get(term, 0) + 1
        # idf = ln(N / df): a term in every description gets idf 0 and drops
        # out, which is exactly how house vocabulary stops dominating.
        self.idf = {t: math.log(n_docs / c) for t, c in df.items()}
        self.vectors = {n: self._vectorize(toks) for n, toks in self._tokens.items()}

    def _vectorize(self, tokens: "list[str]") -> "dict[str, float]":
        tf: dict[str, float] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0.0) + 1.0
        # Drop zero-weight terms: a term in every description has idf 0 and
        # carries no routing signal, so it should not even occupy the vector.
        return {t: c * self.idf.get(t, 0.0) for t, c in tf.items() if self.idf.get(t, 0.0)}

    def vectorize_query(self, text: str) -> "dict[str, float]":
        """Weight a free-text prompt by the corpus IDF (unseen/ubiquitous drop)."""
        tf: dict[str, float] = {}
        for t in tokenize(text):
            if self.idf.get(t, 0.0):
                tf[t] = tf.get(t, 0.0) + 1.0
        return {t: c * self.idf[t] for t, c in tf.items()}

    def rank(self, text: str) -> "list[tuple[str, float]]":
        """Rank every skill by cosine similarity of its description to `text`."""
        q = self.vectorize_query(text)
        scored = [(n, cosine(q, self.vectors[n])) for n in self.names]
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return scored

    def collisions(self) -> "list[tuple[str, str, float]]":
        """All description pairs, most-similar first."""
        pairs = []
        for i, a in enumerate(self.names):
            for b in self.names[i + 1:]:
                pairs.append((a, b, cosine(self.vectors[a], self.vectors[b])))
        pairs.sort(key=lambda t: -t[2])
        return pairs


def cosine(a: "dict[str, float]", b: "dict[str, float]") -> float:
    if not a or not b:
        return 0.0
    # Iterate the smaller vector for the dot product.
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    dot = sum(v * large.get(k, 0.0) for k, v in small.items())
    if dot == 0.0:
        return 0.0
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


# --------------------------------------------------------------------------- #
# Eval cases                                                                    #
# --------------------------------------------------------------------------- #
def load_cases(cases_dir: Path = CASES_DIR) -> "list[dict]":
    if not cases_dir.exists():
        return []
    out = []
    for path in sorted(cases_dir.glob("*.json")):
        out.append(json.loads(path.read_text(encoding="utf-8")))
    return out


def evaluate_case(case: "dict", corpus: Corpus) -> "dict":
    """Run one skill's trigger cases; return per-prompt pass/fail detail."""
    skill = case["skill_name"]
    trigger = case.get("trigger", {})
    results = {"skill_name": skill, "positive": [], "negative": []}

    for pos in trigger.get("positive", []):
        prompt, top_k = pos["prompt"], pos.get("top_k", 3)
        ranking = corpus.rank(prompt)
        order = [n for n, _ in ranking]
        rank = order.index(skill) + 1 if skill in order else None
        results["positive"].append({
            "prompt": prompt,
            "top_k": top_k,
            "rank": rank,
            "rank1": rank == 1,
            "passed": rank is not None and rank <= top_k,
            "top3": ranking[:3],
        })

    for neg in trigger.get("negative", []):
        prompt, owner = neg["prompt"], neg.get("owner")
        ranking = corpus.rank(prompt)
        order = [n for n, _ in ranking]
        skill_rank = order.index(skill) + 1 if skill in order else None
        owner_rank = order.index(owner) + 1 if owner in order else None
        # This skill must not rank first; when an owner is named, it must
        # outrank this skill (turns a vacuous negative into a real pairwise
        # routing test — addyosmani/agent-skills' refinement).
        if owner is not None and owner_rank is not None:
            passed = owner_rank < (skill_rank or math.inf)
        else:
            passed = skill_rank != 1
        results["negative"].append({
            "prompt": prompt,
            "owner": owner,
            "skill_rank": skill_rank,
            "owner_rank": owner_rank,
            "passed": passed,
            "top3": ranking[:3],
        })
    return results


# --------------------------------------------------------------------------- #
# Report                                                                        #
# --------------------------------------------------------------------------- #
def build_report(skills_dir: Path = SKILLS_DIR, cases_dir: Path = CASES_DIR) -> "dict":
    descriptions = load_descriptions(skills_dir)
    corpus = Corpus(descriptions)
    cases = load_cases(cases_dir)
    return {
        "skill_count": len(descriptions),
        "collisions": corpus.collisions(),
        "case_results": [evaluate_case(c, corpus) for c in cases],
    }


def _fmt_top3(top3: "list[tuple[str, float]]") -> str:
    return ", ".join(f"{n} {s:.2f}" for n, s in top3)


def print_report(report: "dict") -> "dict":
    """Print the human-readable report; return a summary dict of the tallies.

    Summary keys: pos_pass / pos_total / neg_pass / neg_total / rank1 /
    hazards. The caller (main / the test) applies gates to these — the printer
    itself never decides pass/fail, so the two agree on the same numbers.
    """
    print(f"\n=== Skill routing eval — {report['skill_count']} skills ===\n")

    print("Description collisions (most-similar pairs; IDF-weighted cosine):")
    shown = 0
    hazards = 0
    for a, b, score in report["collisions"]:
        if score < 0.20 and shown >= 12:
            break
        flag = "  "
        if score >= COLLISION_ERROR:
            flag, hazards = "!!", hazards + 1
        elif score >= COLLISION_WARN:
            flag = " ~"
        print(f"  {flag} {score:.2f}  {a}  ×  {b}")
        shown += 1
    print(f"\n  thresholds: ~ warn ≥{COLLISION_WARN:.2f}   !! error ≥{COLLISION_ERROR:.2f}"
          f"   ({hazards} hazard(s))\n")

    pos_pass = pos_total = neg_pass = neg_total = rank1 = 0
    for res in report["case_results"]:
        print(f"--- {res['skill_name']} ---")
        for p in res["positive"]:
            pos_total += 1
            pos_pass += p["passed"]
            rank1 += p["rank1"]
            mark = "PASS" if p["passed"] else "FAIL"
            rank = p["rank"] if p["rank"] is not None else "—"
            print(f"  [{mark}] +  rank {rank}/{p['top_k']}  «{p['prompt']}»")
            if not p["passed"] or not p["rank1"]:
                print(f"           top3: {_fmt_top3(p['top3'])}")
        for n in res["negative"]:
            neg_total += 1
            neg_pass += n["passed"]
            mark = "PASS" if n["passed"] else "FAIL"
            owner = f" owner={n['owner']}({n['owner_rank']})" if n["owner"] else ""
            print(f"  [{mark}] -  this={n['skill_rank']}{owner}  «{n['prompt']}»")
            if not n["passed"]:
                print(f"           top3: {_fmt_top3(n['top3'])}")
        print()

    rank1_rate = rank1 / pos_total if pos_total else 0.0
    if pos_total:
        print(f"positive triggers: {pos_pass}/{pos_total} routed within top_k  "
              f"(rank-1 rate {rank1}/{pos_total} = {rank1_rate:.0%})")
    if neg_total:
        print(f"negative triggers: {neg_pass}/{neg_total} routed away correctly")
    return {
        "pos_pass": pos_pass, "pos_total": pos_total,
        "neg_pass": neg_pass, "neg_total": neg_total,
        "rank1": rank1, "hazards": hazards,
    }


def _parse_float_flag(argv: "list[str]", flag: str) -> "float | None":
    if flag not in argv:
        return None
    idx = argv.index(flag)
    if idx + 1 >= len(argv):
        raise SystemExit(f"{flag} requires a value, e.g. {flag} 0.85")
    return float(argv[idx + 1])


def main(argv: "list[str] | None" = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    report = build_report()
    if "--json" in argv:
        # Tuples → lists for JSON.
        serializable = {
            "skill_count": report["skill_count"],
            "collisions": [[a, b, s] for a, b, s in report["collisions"]],
            "case_results": report["case_results"],
        }
        print(json.dumps(serializable, indent=2))
        return 0

    min_rank1 = _parse_float_flag(argv, "--min-rank1")
    summary = print_report(report)

    # Hard gates — unambiguous defects: a description collision at/above the
    # error threshold, or a realistic prompt that fails to route its owner even
    # within top_k. Negative-routing misses and rank-2 positives are surfaced
    # in the report but are not hard failures here (they are floor-ratcheted in
    # the test) — forcing a lexical proxy to win every pairwise tie invites
    # gaming the descriptions rather than improving them.
    failures = []
    if summary["hazards"]:
        failures.append(f"{summary['hazards']} description collision(s) ≥ {COLLISION_ERROR}")
    missed_pos = summary["pos_total"] - summary["pos_pass"]
    if missed_pos:
        failures.append(f"{missed_pos} positive trigger(s) outside top_k")

    # Optional ratchet: gate the rank-1 rate against a caller-supplied floor.
    if min_rank1 is not None and summary["pos_total"]:
        rate = summary["rank1"] / summary["pos_total"]
        if rate < min_rank1:
            failures.append(f"rank-1 rate {rate:.0%} below --min-rank1 {min_rank1:.0%}")
        print(f"\nratchet: rank-1 rate {rate:.0%} vs floor {min_rank1:.0%} — "
              f"{'PASS' if rate >= min_rank1 else 'FAIL'}")

    if failures:
        print("\nGATE FAILED: " + "; ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
