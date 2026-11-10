# Ollama multi-task run, 2026-11-10

This run compares the same models on the PC and the Steam Deck with a compact,
deterministic task suite. It is separate from the GGUF/llama.cpp benchmark in
the parent README; do not merge the two scoring scales.

## Models

- `mimo-v2.6` (9B, 6.6 GB, vision/thinking) — tested.
- `pplx-decider-flash` (4B, 5.6 GB, decision/vision) — **not run on Linux**.
  Ollama 0.40.15 returns `this model requires MLX support, but the MLX runtime is
  not available`; the manifest requires 0.40.7 and ships safetensors. No score is
  reported.
- `bonsai-2:9b` (9B ternary, 3.2 GB, vision/tools/thinking) — tested.
- `lfm3` (1.7B, 1.1 GB, text/tools/thinking) — tested.

## Tasks

| Category | Count | Check |
|---|---:|---|
| IF | 8 | exact / contains / JSON / list, zh/en/de |
| JSON | 8 | invoice fields, exact keys and numeric values |
| NIAH 4K | 3 | access-code retrieval from a synthetic haystack |
| Tool | 8 | exact tool name and arguments |
| Code | 4 | Python, SQL, reverse expression, email regex |

Scores are per-category pass percentages; `macro` is the unweighted mean of the
five categories. Speed is the mean of Ollama's `eval_count / eval_duration`
over the task rows. One request per task, temperature 0, seed 42.

## Raw files

- `pc/<label>.json`, `deck/<label>.json`: full per-task outputs and timings.
- `deck/bonsai-2-9b-partial.json`: IF/code only; JSON/NIAH/tool stopped for
  runtime, so no full Deck macro.
- `pplx-decider-flash.unsupported.json`: the exact failure record.

## Caveats

- `pplx-decider-flash` has no Linux result; it is not a zero score.
- The suites are small and single-run; treat differences under ~10 points as
  noise.
- The PC and Deck are different hardware. Speed is a deployment signal, not a
  model-only benchmark.
- Vision capabilities are not tested; all prompts are text-only.
- `bimo-7b` is not part of this run.
