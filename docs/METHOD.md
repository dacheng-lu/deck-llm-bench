# Method and deviations

## What is measured

Every model runs alone on the Deck through `llama-server` at 8K context,
temperature 0, seed 42, `--jinja --reasoning-budget 0`, with placement chosen by
file size (99 layers for ≤3.6 GB, 12 for ≤5.6 GB, 8 for ≤7.5 GB, CPU for larger).
The same frozen wiki index and the same 64 cases are used for every model;
retrieval is not re-run per model beyond the query embedding.

Scores (0–100): wiki 35, JSON 20, instruction following 15, 4K needle 15,
speed 10, tool schema 5. The wiki part is
`35 * (0.7 * answer_correct_answerable + 0.3 * citation_ok_lenient_answerable)`;
`answer_ok` (which folds in abstention on unanswerable cases) and strict
citation are reported as diagnostics. JSON values are compared numerically
after stripping currency symbols, so `"EUR 1299.50"` matches `1299.5`; keys and
string values must still match exactly.

Gates: loads at 8K; tg ≥ 5 tok/s; wiki answerable accuracy ≥ 50%; lenient
citation ≥ 60%; JSON ≥ 9/10; 4K needle ≥ 4/5; peak RSS ≤ 10.5 GB with no swap.

## Pre-registration

The wiki subset is every third case of `cases/test.jsonl` (64 of 193, all eight
domains). SHA-256 of the newline-joined case IDs:
`7504b6370c29457d3b54e6952df2124631afccb864c9df45bb7714d1597e904e`.
It was fixed before any model's wiki run was scored. The first attempt used the
first 64 cases, which are all mathematics; that attempt was discarded before
scoring and is not reported.

## Deviations and known issues

- **8K needle not in the main queue.** With a 4 GB VRAM carveout and the
  download page cache resident, a 7K-token prompt evicted model pages and drove
  the machine into zram thrash (PSI full ≈ 26%). The main queue therefore runs
  4K only; 8K is a separate finalist pass on an idle machine.
- **Download corruption.** Early parallel queue scripts appended to the same
  filenames. Three GGUFs were larger than the official size (Nanbeige +16 MB,
  Gemma-4-E4B-Unc +658 MB, DeepSeek-9B +754 MB). They were deleted and
  re-downloaded by a single locked queue that verifies byte size and the HF
  SHA-256 before writing a `.ok` marker. All files used for scoring carry a
  verified hash in `models.json` / the per-model JSON.
- **WiFi.** The Deck's link is weak (-85 dBm). It dropped off the LAN during the
  run; tests continue locally (localhost only), downloads pause until it
  returns. An overnight watcher restarts dead jobs and pushes results.
- **Reasoning traces.** `--reasoning-budget 0` is not honoured by every chat
  template. Models that emit a visible reasoning preamble are scored as-is on
  instruction following; this is a real behaviour difference, not stripped.
- **JSON scoring** was tightened after the first two models: exact types were
  not stated in the prompt, so numeric strings with a currency are accepted.
  All models are rescored from their stored raw outputs with the same rule.
- **One sample per model.** Latency is single-run and includes any download
  contention; treat differences under ~10% as noise.

## Reproduce

```sh
./scripts/run_model.sh <label> <path.gguf> full|variant
python3 scripts/aggregate.py
```

Raw per-request outputs are in `results/<label>-extra.json`; wiki per-case
records are in the pilot3 `runs/<label>-wiki64s/` directory.
