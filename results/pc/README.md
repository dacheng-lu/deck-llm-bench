# PC sweep, 2026-11-10

Same 64-case frozen wiki subset as the Deck benchmark, run on the laptop:

- i5-12500H, 15 GiB RAM, RTX 3050 Mobile 4 GB.
- llama.cpp Vulkan backend, one model at a time.
- 13 runs: the 12 Deck models plus LFM3-1.7B.

## Timeline (CET)

- 2026-11-09 20:24: user GO for the PC A/B run.
- 20:37: `bench5-ab.service` started and waited for the 12 GGUF downloads.
- 2026-11-10 01:10: downloads complete; sweep started.
- 01:10–06:09: twelve models completed with 64/64 responses.
- 06:09: `gemma4-12b-qat` hit the 4-hour per-model timeout at 52/64 responses
  (`rc=124`); scoring completed.
- 06:09: unit exited. No report was emitted and no notification was sent.

## Files

- `laptop-scores.json`: per-model aggregate metrics.
- `run.log`: queue timeline and per-model return codes.

`laptop-scores.json` fields:

- `responses`: responses produced, out of 64.
- `answerable_n`: answerable cases in the scored subset.
- `answer_ok`: fraction of all responses judged correct.
- `citation_ok`: fraction with an acceptable citation.
- `valid_json`: fraction with valid JSON.
- `lat_mean_s`, `lat_p50_s`: end-to-end latency.
- `prompt_tokens_mean`: mean prompt size.

## Limits

- The 12B row is partial and must not be ranked with complete runs.
- `bimo-7b` produced almost no valid JSON; treat it as a template/format failure
  in this harness, not a general model verdict.
- One run per model, temperature 0, no confidence intervals.
- The PC and Deck latency difference is expected from the hardware and backend.
