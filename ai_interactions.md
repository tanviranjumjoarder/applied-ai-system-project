# AI Interactions Log

This file covers two things:

1. **VibeFinder's own agent traces** (stretch feature: Agentic Workflow Enhancement). Every run records each decision the pipeline makes, so you can see how it got to an answer and not just the answer itself.
2. **How I used an AI coding agent to build the project** (prompts, what it changed, what I verified or fixed by hand).

---

## 1. VibeFinder decision traces

VibeFinder works as a decision chain, not a single model call:

check the input → parse with the model → validate and fix the profile → decide whether to refuse → retrieve → judge confidence → explain → self-check → keep the answer, retry with feedback, or fall back to the template

Each step adds a row to `Result.trace` (see `src/pipeline.py`). To save a trace, run:

```bash
python -m src.app --trace evaluation/agent_traces.md "your request"
```

Live traces from real Gemini runs are saved in **[`evaluation/agent_traces.md`](evaluation/agent_traces.md)**. They cover:

- two normal requests ("something calm for a rainy study night", "music for a beach day with friends") where the self-check passes on the first try,
- a request for a genre the catalog doesn't have ("k-pop for dancing"),
- a prompt-injection request that's refused at the routing step, before any retrieval.

Earlier, with the plain parser prompt, the trace for the rainy-study request also had a "validate profile → fix applied" row, because Gemini guessed the genre "ambient" and the validator dropped it. With the few-shot prompt, Gemini doesn't make that guess anymore.

The retry and fallback branch can't be triggered on demand with the real model, so the trace below was produced with the fake model from the test suite (`tests/test_pipeline.py`). The fake model's first draft recommends "Gym Hero" (not retrieved), and its second draft only says "Iron Tide." The test `test_trace_shows_retry_then_fallback` checks this same path.

**Request:** `chill lofi for studying` (simulated model)

| # | Step | Decision | Detail |
|---|------|----------|--------|
| 1 | input guardrail | pass | 23 characters |
| 2 | parse | used gemini (fewshot prompt) | {'genre': 'lofi', 'mood': 'chill', 'energy': 0.3, 'likes_acoustic': None, 'keywords': ['chill', 'lofi', 'study', 'studying']} |
| 3 | route | music request: retrieve | notes search on |
| 4 | retrieve | top 5 picked | Library Rain 4.95, Midnight Coding 4.88, Focus Flow 3.90, Spacewalk Thoughts 1.98, Coffee Shop Stories 1.43 |
| 5 | confidence | high | 0.99 = top score / best possible |
| 6 | self-check (attempt 1) | FAIL: retry with feedback | mentions songs that were not retrieved: Gym Hero; skips retrieved songs: Midnight Coding, Focus Flow, Spacewalk Thoughts, Coffee Shop Stories |
| 7 | self-check (attempt 2) | FAIL: give up on model | mentions songs that were not retrieved: Iron Tide; skips retrieved songs: Library Rain, Midnight Coding, Focus Flow, Spacewalk Thoughts, Coffee Shop Stories |
| 8 | explain | fallback: use template | built straight from the retrieved data |
| 9 | answer | explainer: template (fallback) | template after failed checks |

Final answer shown to the listener (Gym Hero and Iron Tide never reach the user):

```text
Here are the closest matches in the catalog.
1. Library Rain by Paper Lanterns (lofi, chill): genre match (+2.0); mood match (+1.0); energy 0.35 vs target 0.30 (+0.95); notes mention lofi, studying (+1.0)
2. Midnight Coding by LoRoom (lofi, chill): genre match (+2.0); mood match (+1.0); energy 0.42 vs target 0.30 (+0.88); notes mention lofi, studying (+1.0)
3. Focus Flow by LoRoom (lofi, focused): genre match (+2.0); energy 0.40 vs target 0.30 (+0.90); notes mention lofi, studying (+1.0)
4. Spacewalk Thoughts by Orbit Bloom (ambient, chill): mood match (+1.0); energy 0.28 vs target 0.30 (+0.98)
5. Coffee Shop Stories by Slow Stereo (jazz, relaxed): energy 0.37 vs target 0.30 (+0.93); notes mention studying (+0.5)
```

---

## 2. Building it with an AI coding agent

**What task did I give the agent?**
Extend my Module 3 recommender into an applied AI system: plain-English requests through Gemini, retrieval from a song-notes knowledge base, an explanation the model writes but can't make up songs in, guardrails, logging, tests, and an evaluation script. Then read the CodePath rubric and fill in anything missing.

**Key prompts I used (paraphrased):**
- "Choose one of my earlier projects and turn it into an applied AI system that meets the Project 4 requirements. Keep the ranking explainable."
- "Make the model's output checkable: validate the parsed profile, and reject any explanation that mentions a song that wasn't retrieved."
- "Write tests with a fake Gemini so the failure cases (junk JSON, invented songs, API outage) can be forced offline."
- "Run the evaluation live, tell me what failed and why, and don't tune the system just to pass my own test set."
- "Complete everything in the rubric, including the stretch features, and keep all writing simple and human."

**What did the agent generate or change?**
- New modules: `src/llm.py`, `src/parser.py`, `src/retriever.py`, `src/guardrails.py`, `src/pipeline.py`, `src/app.py`, `src/evaluate.py`
- Data: `data/song_notes.json` (a note and good-for tags for each of the 20 songs)
- Tests: `tests/test_pipeline.py` (21 new tests, 26 total including the Module 3 ones)
- Stretch features: the few-shot parser prompt, the `--no-notes` switch for the before/after comparison, and the decision trace
- Docs: `README.md`, `model_card.md`, `diagrams/architecture.mmd`, `presentation.md`, this file
- Commands it ran: pytest, offline and live evaluations, sample runs, and a render check of the diagram on GitHub

**What did I verify or fix by hand?**
- I read every live explanation against the song notes. That's how the "late-night feel" given to the wrong song got caught, since the automatic name check can't see it.
- I checked that `.env` was git-ignored before the first commit. The Module 3 `.gitignore` didn't cover it, and that was fixed before anything was pushed.
- The evaluation exposed three mistakes in the agent's own code:
  - "k-pop" was parsed as "pop."
  - The genre guardrail was too strict and rejected "synthwave" for "80s synth."
  - The "grounded" metric marked correct template answers as failures.
  All three are fixed, and the first one has a test.
- One of the agent's test helpers built its expected songs from the wrong profile, so a test failed for a reason that had nothing to do with the app. I traced it and fixed the test, not the app.
- The first few-shot prompt mentioned "beach" and "drive," which are words from my own test requests. I caught that after the 14/14 result, had them replaced with words outside the test set, and reran. The result held.
- I rejected the idea of caching the model's parsed profiles to make the consistency check pass, because it would have hidden real variation in the model.
- The Mermaid diagram first failed to render on GitHub because of quotation marks inside a label. I found that by opening the file on GitHub, then fixed it.
