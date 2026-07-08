# Skill-routing evals

jig routes work to skills entirely through each skill's `SKILL.md`
`description:` — the host surfaces every description each session and the
model picks (spec 076 / EngTip #23). This directory guards that mechanism the
way jig guards everything else: with a deterministic, CI-safe check.

The idea (and the eval-case shape) is borrowed from
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills), which
borrowed the case schema from Anthropic's skill-creator. It is a **lexical
approximation** of routing — stemmed TF-IDF cosine over descriptions — so it
cannot judge semantics. What it catches are the two failure modes that
dominate real routing bugs:

- **false negative** — a description missing the vocabulary a realistic prompt
  uses, so its owner fails to rank for that prompt;
- **collision** — two descriptions so similar the model cannot route between
  them.

## Run it

```bash
python3 scripts/skill_routing.py                 # human-readable report
python3 scripts/skill_routing.py --json          # machine-readable
python3 scripts/skill_routing.py --min-rank1 0.9 # gate: fail if rank-1 rate < floor
python3 scripts/test_skill_routing.py            # the CI gate (unittest)
```

The test is auto-discovered by `scripts/run_tests.py`, so it runs in the
suite. Its gates:

| Check | Kind | Current baseline |
|---|---|---|
| No description pair collides ≥ `COLLISION_ERROR` (0.75) | hard | max pair 0.22 |
| Every positive prompt routes its owner within `top_k` | hard | 57/57 |
| rank-1 rate ≥ `MIN_RANK1_RATE` (0.85) | ratchet | 95% |
| negative route-away rate ≥ `MIN_NEG_ROUTE_AWAY` (0.90) | ratchet | 100% |

**What gets vectorized.** Only the *positive* routing surface (`routing_surface()`)
— the negative-disambiguation tail (`Do not use for … use /jig:X instead`,
`Defers to …`) is stripped before scoring. That boilerplate is what teaches the
*model* to route siblings apart, so counting it as lexical *similarity* inverts
the signal (frame-critique 086-01). Stripping it dropped the top collision
0.44→0.22 and lifted negative routing to 100%.

Floors sit just below the baseline on purpose — raise them as descriptions are
sharpened, so the gate catches regressions without demanding a perfect lexical
proxy.

## Add a case

One file per skill: `evals/cases/<skill-name>.json`.

```json
{
  "skill_name": "clarify",
  "trigger": {
    "positive": [
      { "prompt": "a realistic user ask that should route here", "top_k": 3 }
    ],
    "negative": [
      { "prompt": "an ask a sibling skill owns", "owner": "independent-review" }
    ]
  }
}
```

- **Paraphrase how users actually talk. Do not copy the description** — that
  games the eval. If a realistic prompt can't rank because the description
  lacks its vocabulary, that is a real finding: **sharpen the description**
  (and regenerate host packages — `python3 scripts/build_host_packages.py`).
- `top_k` defaults to 3; tighten to 1 for a skill's signature ask.
- `owner` on a negative turns it into a real pairwise test: the owner must
  outrank this skill, not merely "this skill isn't #1".

## Known limitations (why this is a canary, not ground truth)

- **Lexical, not semantic.** The host routes with the model; this is surface
  words. Value is regression detection, not perfect prediction.
- **Self-authored cases (the closed loop).** Trigger prompts are hand-written by
  the same author as the descriptions, so a green baseline can measure author
  *self-consistency*, not routing fitness — and the ratchet then freezes that
  (frame-critique 086-01 SECONDARY). So this eval catches **regression against
  the pinned case set**, not the full space of vocabulary real users say. There
  is **no automatic mis-route detector** — `.claude/skill-usage.jsonl` records
  only which skill *fired*. The durable fixes (deferred, `docs/refinement-todo.md`):
  extend the trace hook to capture the invoking prompt and seed cases from real
  phrasings, plus the semantic Tier-3 eval.
- **TF-IDF length bias.** A very long description dilutes its own cosine — a
  proxy artifact a semantic router would not share; hence the *floor* on
  negatives rather than a demand that every pairwise tie break correctly.
- **Small corpus.** ~19 descriptions → coarse IDF (house vocabulary like
  `spec` / `slice` / `review` is IDF-suppressed, which is intended).
- The semantic tier (run each skill through headless `claude -p`, grade the
  trace) is the natural next step — jig already subprocesses `claude` in
  `servo:agent-loop`. Token-costly, so on-demand only.
