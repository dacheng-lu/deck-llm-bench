#!/bin/sh
# Run the Ollama multi-task suite sequentially for the 2026-11-10 models.
# Usage: ./scripts/run_ollama_sweep.sh pc|deck
set -eu

MACHINE="${1:?usage: run_ollama_sweep.sh pc|deck}"
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
OUT="$ROOT/results/ollama/$MACHINE"
mkdir -p "$OUT"

run() {
  label="$1"
  tag="$2"
  echo "START $label $tag $(date -Is)"
  python3 "$ROOT/scripts/bench_ollama.py" \
    --model "$tag" --label "$label" --machine "$MACHINE" \
    --out "$OUT/$label.json"
  echo "END $label $(date -Is)"
}

run mimo-v2.6 mimo-v2.6
run pplx-decider-flash pplx-decider-flash
run bonsai-2-9b bonsai-2:9b
run lfm3-1.7b lfm3
echo "SWEEP DONE $(date -Is)"
