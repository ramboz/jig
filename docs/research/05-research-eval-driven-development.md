# Research: Eval-Driven Development (EDD)

> Reference notes from the design phase. Pull into context only when relevant.

## Framing

**EDD makes explicit what TDD does implicitly.** TDD assumes deterministic outputs (this function returns 42). EDD handles stochastic outputs (this LLM call should produce a helpful, on-topic, non-toxic response) by defining rubrics and combining LLM-as-judge with deterministic scorers.

The key insight from evaldriven.org: **"The eval comes first — before the prompt, before the pipeline, before the model selection."** Not "we'll add evals once we ship." If you can't articulate what good looks like, you can't build toward it.

## TDD vs EDD — when each applies

| | TDD | EDD |
|---|---|---|
| **Output type** | Deterministic | Stochastic |
| **Test format** | Assertions | Rubrics + scorers |
| **Pass criteria** | Exact match | Threshold + variance |
| **Single failure means** | Bug | Maybe variance; need pass@k |
| **Default for** | Pure code, business logic | Anything LLM-touched |

**Both apply in AI-native projects.** TDD is the right inner loop for deterministic logic; EDD is the right outer loop for anything LLM-touched (prompts, agent behavior, RAG retrieval, classification, generation).

## When to opt in to EDD in our scaffold

The `scaffold-init` wizard detects project signals:

- Presence of prompt files (`prompts/`, `.prompt` files)
- LLM API calls in dependencies (`@anthropic-ai/sdk`, `openai`, `langchain`, etc.)
- Vector DB or RAG signals (`pinecone`, `chroma`, `weaviate`, etc.)
- Keywords in project pitch: "agent", "prompt", "RAG", "classification", "summarization"
- Filename signals: `agent-`, `prompt-`, `-llm-`

If any signals present → install Tier 2 `eval-harness` skill.
If no signals → only TDD scaffolding.

This is the right default. Forcing EDD on a plain CRUD app is over-engineering. Skipping it on an agentic project is under-engineering.

## The three grader types

From Anthropic's "Demystifying evals" post (<https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>):

### 1. Static analysis (code-based scorers)

Deterministic checks. Format validation, schema compliance, length limits, regex patterns, exact-match on key fields.

Example: "Output must be valid JSON matching this schema."

### 2. LLM judges

Automated scorers that use a language model to assess subjective qualities. Correctness, relevance, safety, helpfulness, instruction following.

Example: "Rate the helpfulness of this response on a scale of 1-5. Helpfulness is defined as..."

### 3. Browser / agent graders

For end-to-end agent tasks. A separate agent (often a browser-using one) tests whether the system under test actually accomplished the task.

Example: "Did the agent successfully complete the user's checkout flow?"

**Key finding from the research:** combining grader types catches more failure modes than any single type. The arxiv paper on automated quality gates found `κ = 0.13` between LLM judges and structural checks — they catch *different* failures. Use both.

## Tiered eval suites

Same pattern as unit vs integration tests:

| Tier | Cadence | Cost | Scope |
|---|---|---|---|
| Smoke | Every commit | Cheap | Fast, deterministic, catches obvious breakage |
| Standard | Every PR | Medium | LLM judges, broader coverage |
| Comprehensive | Nightly | Expensive | Full regression suite, pass@k, variance analysis |

The `eval-harness` skill generates templates for all three.

## Pass@k

A single passing eval run proves nothing about stochastic systems. Run k times (typically 3-10), measure pass rate.

Convention in our templates:

```python
@eval(passes_required=8, runs=10)  # pass@8 of 10
def test_agent_handles_ambiguous_request():
    ...
```

## Two suites: quality benchmarking vs regression testing

Borrowed from Descript's pattern (cited in Anthropic's eval post):

- **Quality benchmark suite** — "Is this output good in absolute terms?" Run when changing prompts or models. Periodic human calibration of LLM judges.
- **Regression suite** — "Did this change break anything that previously worked?" Run on every PR. Built from production failures converted to test cases.

Different cadences. Different ownership. Don't conflate.

## The data flywheel

Production failures → regression dataset. Every real-world failure becomes a test case. Over time, the regression suite becomes a comprehensive map of failure modes the system has previously hit.

Our scaffold's `eval-harness` skill generates a `failures-to-tests.md` runbook that explains this loop and provides the conversion template.

## LLM judge calibration

LLM judges drift. They can be inconsistent with human judgment. They need periodic calibration:

1. Sample ~30-60 outputs.
2. Have humans grade them.
3. Compare to LLM judge grades.
4. If disagreement is high (κ < 0.4), revise the judge rubric.
5. Repeat quarterly or after major prompt changes.

Our `eval-harness` skill generates a calibration runbook.

## Things to avoid

- **LLM judge as the only signal.** Combine with static analysis.
- **Eval as deployment gate without variance.** A single passing run is noise.
- **Evals that grade things a regex could grade.** Don't burn LLM-judge budget on format checks.
- **No regression suite.** Quality benchmarking alone tells you "are we good?" but not "did we just regress?"
- **Evals on synthetic data only.** Real production traffic catches modes synthetic data misses.

## Source signals

- Eval-Driven Development: <https://evaldriven.org/>
- Anthropic's "Demystifying evals for AI agents": <https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>
- LangChain's LLM-as-judge calibration: <https://www.langchain.com/articles/llm-as-a-judge>
- MLflow LLM evaluation: <https://mlflow.org/llm-evaluation/>
- Xia et al. on Evaluation-Driven Development of LLM Agents (arxiv 2411.13768)
