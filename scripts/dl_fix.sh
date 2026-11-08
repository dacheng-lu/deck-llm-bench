#!/bin/sh
# Repair corrupted/partial downloads, verify size and SHA-256, then mark .ok.
set -u
cd "$HOME/models/bench5" || exit 1
exec 9> .dl.lock
flock -n 9 || { echo "another downloader holds the lock"; exit 1; }
BASE=https://huggingface.co

fetch() {
  url="$1"; out="$2"; size="$3"; sha="$4"
  if [ -f "$out.ok" ] && [ "$(stat -c%s "$out" 2>/dev/null || echo 0)" = "$size" ]; then
    echo "$(date -Is) OK-cached $out"; return 0
  fi
  rm -f "$out.ok"
  have=$(stat -c%s "$out" 2>/dev/null || echo 0)
  if [ "$have" -gt "$size" ]; then echo "oversized $have > $size, restarting $out"; rm -f "$out"; have=0; fi
  echo "$(date -Is) FETCH $out have=$have need=$size"
  curl -L --retry 8 --retry-delay 5 --connect-timeout 20 -C - -o "$out" "$url"
  got=$(stat -c%s "$out" 2>/dev/null || echo 0)
  if [ "$got" != "$size" ]; then echo "SIZE-FAIL $out $got != $size"; return 1; fi
  echo "$(date -Is) HASH $out"
  echo "$sha  $out" | sha256sum -c - || { echo "HASH-FAIL $out"; rm -f "$out"; return 1; }
  touch "$out.ok"
  echo "$(date -Is) VERIFIED $out"
}

fetch "$BASE/bartowski/Nanbeige_Nanbeige4.2-3B-GGUF/resolve/main/Nanbeige_Nanbeige4.2-3B-Q4_K_M.gguf" \
  Nanbeige_Nanbeige4.2-3B-Q4_K_M.gguf 2684023968 b92d2e35c9876b0c4bc671996360204f4149d0546c23d5954d5eb3b106c81f24
fetch "$BASE/HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive/resolve/main/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf" \
  Gemma-4-E4B-Unc-Q4_K_M.gguf 5335285728 d0027dd3a9128d9323e9f282c8bf010a8526c46477584535991dc1a869b56e96
fetch "$BASE/mradermacher/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic-GGUF/resolve/main/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic.Q4_K_M.gguf" \
  DeepSeek-V4-Pro-Qwen3.5-9B-Unc-Q4_K_M.gguf 5629111264 a692de9520e4c0bb1512deb91e950f38e14854650aff43419112f87e6052c44b
fetch "$BASE/mradermacher/Bimo-7B-CyberAgent-GGUF/resolve/main/Bimo-7B-CyberAgent.Q4_K_M.gguf" \
  Bimo-7B-CyberAgent-Q4_K_M.gguf 4683073696 623c5868423f6fead2169800b3495611c979ecec346f3f999fb3a62735e8124a
echo "$(date -Is) FIX-DONE"
