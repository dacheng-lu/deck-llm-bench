# Steam Deck local-LLM benchmark

Frozen 64-case wiki retrieval per model; deterministic checks. Scores: wiki 35, JSON 20, IF 15, NIAH 15, speed 10, tool 5.

| # | model | tier | GB | tg/s | wiki ans | cite | total | gates |
|---|---|---|---|---|---|---|---|---|
| 1 | qwen35-4b-base | full | 2.74 | 20.34 | 0.6346 | 0.5962 | 84.81 | FAIL |
| 2 | gemma4-e2b-base | full | 3.11 | 31.35 | 0.6731 | 0.2692 | 67.07 | FAIL |
