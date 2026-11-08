#!/bin/sh
# Run one model: start llama-server, run extra tasks + frozen wiki QA, stop it.
# usage: run_model.sh <label> <gguf> <full|variant>
set -u
LABEL="$1"; FILE="$2"; TIER="${3:-full}"
BENCH="$HOME/deck-bench"
PORT=11437
SIZE=$(stat -c%s "$FILE")
if [ "$SIZE" -le 3600000000 ]; then NGL=99
elif [ "$SIZE" -le 5600000000 ]; then NGL=12
elif [ "$SIZE" -le 7500000000 ]; then NGL=8
else NGL=0
fi
mkdir -p "$BENCH/results" "$BENCH/logs"
LOG="$BENCH/logs/$LABEL.server.log"

setsid nohup "$HOME/llama.cpp/build/bin/llama-server" -m "$FILE" \
  --host 127.0.0.1 --port $PORT -c 8192 -ngl "$NGL" -t 4 -tb 8 \
  --jinja --reasoning-budget 0 --seed 42 --temp 0 --top-k 1 \
  > "$LOG" 2>&1 < /dev/null &
PID=$!
echo "started $LABEL pid=$PID ngl=$NGL size=$SIZE"
up=0
i=0
while [ $i -lt 240 ]; do
  if curl -s --max-time 2 "http://127.0.0.1:$PORT/health" | grep -q ok; then up=1; break; fi
  if ! kill -0 "$PID" 2>/dev/null; then break; fi
  sleep 2; i=$((i+2))
done
if [ "$up" -ne 1 ]; then
  echo "LOAD-FAIL $LABEL after ${i}s"; tail -5 "$LOG"
  kill "$PID" 2>/dev/null
  echo "{\"label\":\"$LABEL\",\"status\":\"LOAD-FAIL\",\"log\":\"$LOG\"}" > "$BENCH/results/$LABEL.loadfail.json"
  exit 2
fi
echo "ready $LABEL after ${i}s"

cd "$BENCH"
SKIP=""
[ "$TIER" = "variant" ] && SKIP="--skip-niah8k"
python3 bench_extra.py --label "$LABEL" --file "$FILE" --tier "$TIER" --pid "$PID" \
  --ngl "$NGL" --ctx 8192 --load "$i" --commit "$(cat "$HOME/llama.cpp/build/commit.txt" 2>/dev/null)" \
  --out "$BENCH/results/$LABEL-extra.json" $SKIP 2>&1 | tail -3
rc=$?

# Frozen-retrieval wiki QA: same 64 cases for every model, p0_run scores them.
cd "$HOME/deck-rag/pilot3"
python3 scripts/p0_run.py --limit 64 --arms embed --out "runs/$LABEL-wiki64" > "$BENCH/logs/$LABEL.wiki.log" 2>&1
echo "wiki rc=$? log=$BENCH/logs/$LABEL.wiki.log"

kill "$PID" 2>/dev/null
sleep 2
kill -9 "$PID" 2>/dev/null
echo "DONE $LABEL extra_rc=$rc"
