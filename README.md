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

Raw data:

- `results/deck/extras/`: 11 Deck component records plus the 12B load failure.
- `results/deck/sweep-scores.json`: Deck 64-case wiki runs.
- `results/pc/laptop-scores.json`: 2026-11-10 PC sweep.
- `results/pc/run.log`: PC queue timeline.
- `results/pc/README.md`: PC run notes and field definitions.

The older `results/summary.json` only covers the first two completed Deck models;
do not treat it as the final aggregate.

### PC run, 2026-11-10

Hardware: i5-12500H, 15 GiB RAM, RTX 3050 Mobile 4 GB, Vulkan backend. Same
frozen 64-case wiki subset and the same deterministic scorer. The 12B model
timed out after 52 of 64 responses; its row is partial and must not be ranked
against complete runs.

| model | n | answerable n | answer ok | citation ok | valid JSON | p50 s | mean s |
|---|---:|---:|---:|---:|---:|---:|---:|
| `gemma4-12b-qat` | 52/64 | 42 | 66.7% | 73.8% | 100.0% | 318.46 | 269.76 |
| `gemma4-e2b-base` | 64/64 | 52 | 51.9% | 65.4% | 100.0% | 0.82 | 1.11 |
| `gemma4-e4b-base` | 64/64 | 52 | 51.9% | 59.6% | 100.0% | 2.63 | 2.67 |
| `deepseek-9b-unc` | 64/64 | 52 | 51.9% | 55.8% | 100.0% | 7.28 | 7.38 |
| `qwen35-4b-base` | 64/64 | 52 | 50.0% | 57.7% | 98.4% | 3.02 | 3.19 |
| `qwen35-9b-base` | 64/64 | 52 | 50.0% | 55.8% | 100.0% | 7.26 | 7.31 |
| `qwen35-4b-unc` | 64/64 | 52 | 48.1% | 55.8% | 100.0% | 3.24 | 3.23 |
| `gemma4-e4b-unc` | 64/64 | 52 | 48.1% | 53.8% | 100.0% | 2.55 | 2.67 |
| `forge-1-e2b` | 64/64 | 52 | 46.2% | 59.6% | 96.9% | 0.80 | 0.96 |
| `nanbeige-3b` | 64/64 | 52 | 44.2% | 55.8% | 100.0% | 9.69 | 10.91 |
| `gemma4-e2b-unc` | 64/64 | 52 | 38.5% | 50.0% | 100.0% | 0.79 | 0.81 |
| `lfm3-1.7b` | 64/64 | 52 | 36.5% | 51.9% | 76.6% | 1.04 | 1.40 |
| `bimo-7b` | 64/64 | 52 | 0.0% | 0.0% | 4.7% | 6.26 | 6.41 |

`bimo-7b` completes every request but produces almost no valid JSON and no
correct answers. That is a template/output-format failure in this harness, not
evidence that the model is generally useless; do not use its row as a quality
ranking.

### PC vs Deck, 64-case wiki

Only models with 64/64 wiki responses on both machines are shown. Δ is PC minus
Deck in percentage points. Latency is single-run p50 and includes the different
hardware and backends, so it is a deployment signal, not a model-only metric.

| model | PC ans | Deck ans | Δ pp | PC cite | Deck cite | Δ pp | PC p50 | Deck p50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `gemma4-e2b-base` | 51.9% | 50.0% | +1.9 | 65.4% | 63.5% | +1.9 | 0.82s | 8.92s |
| `qwen35-4b-base` | 50.0% | 50.0% | +0.0 | 57.7% | 59.6% | -1.9 | 3.02s | 19.18s |
| `qwen35-4b-unc` | 48.1% | 48.1% | +0.0 | 55.8% | 55.8% | +0.0 | 3.24s | 18.77s |
| `forge-1-e2b` | 46.2% | 46.2% | +0.0 | 59.6% | 59.6% | +0.0 | 0.80s | 8.94s |
| `nanbeige-3b` | 44.2% | 42.3% | +1.9 | 55.8% | 53.8% | +2.0 | 9.69s | 31.50s |
| `gemma4-e2b-unc` | 38.5% | 40.4% | -1.9 | 50.0% | 51.9% | -1.9 | 0.79s | 8.95s |

The quality deltas are small. The large latency gap is expected: the PC runs
on a discrete GPU, the Deck on a 4 GB carveout. The Deck runs below are partial
and are not included in the comparison: `bimo-7b` 31/64, `deepseek-9b-unc` 4/64,
`gemma4-e4b-base` 47/64, `gemma4-e4b-unc` 43/64, `qwen35-9b-base` 17/64,
`gemma4-12b-qat` 0/64.

### Deck component scores

Raw deterministic components. These `gates` are the component gates only
(`tg`, `json`, `niah`, `rss`); the wiki gates live in the wiki records, not in
this table.

| model | IF/15 | JSON/20 | tool/5 | NIAH/15 | speed/10 | tg/s | component gates |
|---|---:|---:|---:|---:|---:|---:|---|
| `bimo-7b` | 9.38 | 0.00 | 5.00 | 15.00 | 9.32 | 7.46 | FAIL |
| `deepseek-9b-unc` | 13.12 | 0.00 | 5.00 | 15.00 | 4.89 | 3.91 | FAIL |
| `forge-1-e2b` | 15.00 | 0.00 | 5.00 | 15.00 | 10.00 | 32.19 | FAIL |
| `gemma4-e2b-base` | 15.00 | 4.00 | 5.00 | 15.00 | 10.00 | 33.01 | FAIL |
| `gemma4-e2b-unc` | 15.00 | 0.00 | 5.00 | 15.00 | 10.00 | 32.39 | FAIL |
| `gemma4-e4b-base` | 15.00 | 0.00 | 5.00 | 15.00 | 4.59 | 3.67 | FAIL |
| `gemma4-e4b-unc` | 15.00 | 0.00 | 5.00 | 15.00 | 4.66 | 3.73 | FAIL |
| `nanbeige-3b` | 13.12 | 2.00 | 5.00 | 15.00 | 10.00 | 13.36 | FAIL |
| `qwen35-4b-base` | 15.00 | 18.00 | 5.00 | 15.00 | 10.00 | 20.34 | PASS |
| `qwen35-4b-unc` | 15.00 | 20.00 | 5.00 | 15.00 | 10.00 | 20.67 | PASS |
| `qwen35-9b-base` | 13.12 | 0.00 | 5.00 | 15.00 | 4.65 | 3.72 | FAIL |
| `gemma4-12b-qat` | — | — | — | — | — | — | NOT-RUN |

Only the two Qwen 3.5 4B models pass every component gate. The JSON column is
the main separator: most runs fail the strict 9/10 gate even when their prose
answers look reasonable.


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
- The 64-case wiki subset is pre-registered as every third case of the pilot3
  test file; the 193-case set is run only for finalists.
- Q4_K_M (and Q4_K_P for one model) is a memory-driven choice, not an
  apples-to-apples quality comparison with larger quants.
- No model judges another model. Every score above comes from a deterministic
  checker.
