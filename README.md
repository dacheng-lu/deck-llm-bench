# Steam Deck local-LLM benchmark

Twelve GGUF models, one at a time, on a Steam Deck OLED (16 GB LPDDR5, 4 GB
carved to VRAM). The point is not a leaderboard for its own sake: it answers
which local model is actually usable for a wiki-RAG workflow on this hardware,
and where the failure is (retrieval, context, instruction following, speed).

## Hardware and software

- Steam Deck OLED, AMD Sephiroth: 4 Zen2 cores / 8 threads, 16 GB LPDDR5-6400.
- Measured sequential read 25–26 GB/s; memcpy ~16 GB/s; WiFi is the download
  bottleneck (2–5 MB/s in this run).
- llama.cpp build `9f0e509` (2026-11-07), `llama-server`, `-c 8192 -t 4 -tb 8
  --jinja --reasoning-budget 0 --seed 42 --temp 0 --top-k 1`.
- Wiki corpus: 52 GB English Wikipedia ZIM served by Kiwix; retrieval index is
  the frozen `pilot3` index (3,693 chunks, nomic-embed-text 768-d) with the same
  top-5 chunks for every model. Generation and embedding are never concurrent.

## Models

See `models.json` for repository, filename, exact byte size and SHA-256. Base
and uncensored variants are deliberately paired so the effect of the fine-tune
is visible without confounding size.

## Tasks and scoring

| task | weight | check |
|---|---|---|
| Wiki QA, 64 frozen cases | 35 | answer alias/numeric (70%) + citation validity (30%) |
| Strict JSON extraction, 10 docs | 20 | exact keys and values |
| Instruction following, 8 zh/en/de prompts | 15 | exact / contains / JSON checks |
| Needle-in-a-haystack, 4K + 8K | 15 | exact code retrieval, 5 needles per depth |
| Speed and memory | 10 | tg128 on a ~3.5K-token prompt, peak RSS |
| Tool-call schema, 10 requests | 5 | exact tool name and arguments |

Gates: loads at 8K; tg ≥ 5 tok/s; wiki answer ≥ 50% and citation ≥ 60%;
JSON ≥ 9/10; 4K needle ≥ 4/5; peak RSS ≤ 10.5 GB with no swap. A failed or
timed-out run is reported as NOT-RUN and stays in the denominator.

## Pre-registration

The 64-case wiki subset is every third case of `cases/test.jsonl` (64 of 193,
covering all eight domains; `sha256` of the newline-joined case IDs is
`7504b6370c29457d3b54e6952df2124631afccb864c9df45bb7714d1597e904e`). The main
queue runs the 4K needle test only; an 8K pass is run separately for finalists
because the 4 GB VRAM carveout plus resident download cache evicts model pages
and thrashes.

## Results

Filled by `scripts/aggregate.py` after the queue finishes; see
`results/REPORT.md`, `results/summary.json` and `results/summary.csv`.

## Reproduce

```sh
# on the Deck, with the GGUFs in ~/models/bench5
./scripts/run_model.sh <label> <path.gguf> full|variant
python3 scripts/aggregate.py
```

`run_model.sh` starts one server, records load time and peak RSS, runs the
deterministic tasks, then the frozen wiki set through `p0_run.py`. Raw
per-request outputs and timings are in `results/<label>-extra.json` and the
pilot3 `runs/<label>-wiki64/` directory.

## Caveats

- One Deck, one run per model, temperature 0. Latency is single-sample and
  includes WiFi/download contention.
- The 64-case wiki subset is pre-registered by taking the first 64 cases of the
  pilot3 test file; the 193-case set is run only for finalists.
- Q4_K_M (and Q4_K_P for one model) is a memory-driven choice, not an
  apples-to-apples quality comparison with larger quants.
- No model judges another model. Every score above comes from a deterministic
  checker.
