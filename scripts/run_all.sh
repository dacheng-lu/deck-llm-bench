#!/bin/sh
# Sequential queue: wait for each GGUF to finish downloading, then benchmark it.
set -u
BENCH="$HOME/deck-bench"
M="$HOME/models/bench5"
cd "$BENCH" || exit 1
mkdir -p results logs

# label|filename|expected_bytes|tier
QUEUE="
gemma4-e2b-base|gemma-4-E2B-it-Q4_K_M.gguf|3106738272|full
nanbeige-3b|Nanbeige_Nanbeige4.2-3B-Q4_K_M.gguf|2684023968|full
qwen35-4b-unc|Qwen3.5-4B-Unc-Q4_K_M.gguf|2707513696|variant
gemma4-e2b-unc|Gemma-4-E2B-Unc-Q4_K_P.gguf|3450277824|variant
forge-1-e2b|Forge-1-E2B-Q4_K_M.gguf|3416119936|variant
gemma4-e4b-base|gemma-4-E4B-it-Q4_K_M.gguf|4977171584|full
gemma4-e4b-unc|Gemma-4-E4B-Unc-Q4_K_M.gguf|5335285728|variant
qwen35-9b-base|Qwen3.5-9B-Q4_K_M.gguf|5680522464|full
deepseek-9b-unc|DeepSeek-V4-Pro-Qwen3.5-9B-Unc-Q4_K_M.gguf|5629111264|variant
gemma4-12b-qat|Gemma4-12B-QAT-Q4_K_M.gguf|7381381760|full
bimo-7b|Bimo-7B-CyberAgent-Q4_K_M.gguf|4683073696|variant
"

# Wait for the already-running first model.
while pgrep -f "run_model.sh qwen35-4b-base" >/dev/null 2>&1; do sleep 30; done

echo "QUEUE START $(date -Is)"
echo "$QUEUE" | while IFS='|' read -r label file size tier; do
  [ -z "$label" ] && continue
  n=0
  while :; do
    have=$(stat -c%s "$M/$file" 2>/dev/null || echo 0)
    [ "$have" -ge "$size" ] && break
    n=$((n+1))
    [ $((n % 20)) -eq 0 ] && echo "$(date -Is) waiting $label $have/$size"
    sleep 30
  done
  echo "$(date -Is) RUN $label tier=$tier size=$size"
  pkill -f "llama-server.*11437" 2>/dev/null; sleep 2
  if ./run_model.sh "$label" "$M/$file" "$tier" > "logs/run-$label.log" 2>&1; then
    echo "$(date -Is) OK $label"
  else
    echo "$(date -Is) FAIL $label rc=$?"
  fi
done
echo "QUEUE DONE $(date -Is)"
