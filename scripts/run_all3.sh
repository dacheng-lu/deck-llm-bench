#!/bin/sh
# Resume queue: skip models that already have extra JSON + wiki metrics.
set -u
BENCH="$HOME/deck-bench"; M="$HOME/models/bench5"
cd "$BENCH" || exit 1
QUEUE="
nanbeige-3b|Nanbeige_Nanbeige4.2-3B-Q4_K_M.gguf|full
qwen35-4b-unc|Qwen3.5-4B-Unc-Q4_K_M.gguf|variant
gemma4-e2b-unc|Gemma-4-E2B-Unc-Q4_K_P.gguf|variant
forge-1-e2b|Forge-1-E2B-Q4_K_M.gguf|variant
gemma4-e4b-base|gemma-4-E4B-it-Q4_K_M.gguf|full
qwen35-9b-base|Qwen3.5-9B-Q4_K_M.gguf|full
gemma4-12b-qat|Gemma4-12B-QAT-Q4_K_M.gguf|full
gemma4-e4b-unc|Gemma-4-E4B-Unc-Q4_K_M.gguf|variant
deepseek-9b-unc|DeepSeek-V4-Pro-Qwen3.5-9B-Unc-Q4_K_M.gguf|variant
bimo-7b|Bimo-7B-CyberAgent-Q4_K_M.gguf|variant
"
echo "QUEUE3 START $(date -Is)"
echo "$QUEUE" | while IFS='|' read -r label file tier; do
  [ -z "$label" ] && continue
  if [ -f "results/$label-extra.json" ] && [ -f "$HOME/deck-rag/pilot3/runs/$label-wiki64s/metrics.json" ]; then
    echo "$(date -Is) SKIP $label (complete)"; continue
  fi
  n=0
  while [ ! -f "$M/$file.ok" ]; do
    n=$((n+1)); [ $((n % 20)) -eq 0 ] && echo "$(date -Is) waiting-ok $label"
    sleep 30
  done
  echo "$(date -Is) RUN $label tier=$tier"
  pkill -f "llama-server.*11437" 2>/dev/null; sleep 2
  if ./run_model.sh "$label" "$M/$file" "$tier" > "logs/run-$label.log" 2>&1; then
    echo "$(date -Is) OK $label"
  else
    echo "$(date -Is) FAIL $label rc=$?"
  fi
done
echo "QUEUE3 DONE $(date -Is)"
