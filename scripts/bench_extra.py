#!/usr/bin/env python3
"""Non-wiki tasks for the Deck benchmark: speed, IF, JSON, NIAH, tool schema.

Assumes a llama-server on 127.0.0.1:11437 with -c 8192. Writes one JSON record.
Deterministic checks only; no model judges another model.
"""
import argparse
import hashlib
import json
import os
import re
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:11437"
HERE = Path(__file__).resolve().parent

IF_TASKS = [
    {"id": "if-exact-en", "prompt": "Reply with exactly: OK", "check": "exact", "expect": "OK"},
    {"id": "if-arith", "prompt": "What is 17 * 23? Reply with the number only.", "check": "contains", "expect": "391"},
    {"id": "if-zh-capital", "prompt": "用一句中文回答：法国的首都是哪里？", "check": "contains", "expect": "巴黎"},
    {"id": "if-de-exact", "prompt": "Antworte nur mit: Berlin", "check": "exact", "expect": "Berlin"},
    {"id": "if-translate", "prompt": "Translate to German, answer with the translation only: good morning", "check": "contains", "expect": "Guten Morgen"},
    {"id": "if-json", "prompt": 'Return JSON only: {"a": 1, "b": 2}', "check": "json", "expect": {"a": 1, "b": 2}},
    {"id": "if-list", "prompt": "List three primary colors, comma separated, no other text.", "check": "all_contains", "expect": ["red", "blue", "yellow"]},
    {"id": "if-summary", "prompt": "Summarize in one short sentence: The Steam Deck is a handheld gaming computer made by Valve. It runs Linux and can also run local language models.", "check": "contains", "expect": "valve"},
]

DOCS = [
    {"invoice": "INV-1042", "vendor": "Acme GmbH", "date": "2026-03-04", "total": 1299.5, "category": "hardware"},
    {"invoice": "INV-2087", "vendor": "Northwind Ltd", "date": "2026-04-12", "total": 87.25, "category": "software"},
    {"invoice": "INV-3311", "vendor": "Contoso AG", "date": "2026-05-30", "total": 450.0, "category": "services"},
    {"invoice": "INV-4420", "vendor": "Globex Inc", "date": "2026-06-18", "total": 12.99, "category": "hardware"},
    {"invoice": "INV-5502", "vendor": "Initech", "date": "2026-07-01", "total": 2300.75, "category": "services"},
    {"invoice": "INV-6614", "vendor": "Umbrella KG", "date": "2026-08-09", "total": 64.4, "category": "software"},
    {"invoice": "INV-7721", "vendor": "Soylent LLC", "date": "2026-09-23", "total": 999.99, "category": "hardware"},
    {"invoice": "INV-8830", "vendor": "Hooli", "date": "2026-10-05", "total": 310.1, "category": "services"},
    {"invoice": "INV-9940", "vendor": "Vandelay", "date": "2026-10-31", "total": 5.5, "category": "software"},
    {"invoice": "INV-1055", "vendor": "Wayne Enterprises", "date": "2026-11-02", "total": 780.0, "category": "services"},
]

TOOLS = [
    {"name": "get_weather", "args": ["city"]},
    {"name": "search_web", "args": ["query"]},
    {"name": "read_file", "args": ["path"]},
    {"name": "send_email", "args": ["to", "subject"]},
]
TOOL_CASES = [
    {"prompt": "What is the weather in Berlin?", "tool": "get_weather", "args": {"city": "Berlin"}},
    {"prompt": "Search the web for Steam Deck OLED reviews.", "tool": "search_web", "args": {"query": "Steam Deck OLED reviews"}},
    {"prompt": "Read the file /tmp/notes.txt", "tool": "read_file", "args": {"path": "/tmp/notes.txt"}},
    {"prompt": "Send an email to a@example.com with subject Report", "tool": "send_email", "args": {"to": "a@example.com", "subject": "Report"}},
    {"prompt": "What's the weather in Tokyo?", "tool": "get_weather", "args": {"city": "Tokyo"}},
    {"prompt": "Search for llama.cpp RPC benchmarks", "tool": "search_web", "args": {"query": "llama.cpp RPC benchmarks"}},
    {"prompt": "Open the file /etc/hostname", "tool": "read_file", "args": {"path": "/etc/hostname"}},
    {"prompt": "Email bob@example.org about the invoice", "tool": "send_email", "args": {"to": "bob@example.org", "subject": "invoice"}},
    {"prompt": "Weather in Paris please", "tool": "get_weather", "args": {"city": "Paris"}},
    {"prompt": "Search: Qwen3.5 9B GGUF", "tool": "search_web", "args": {"query": "Qwen3.5 9B GGUF"}},
]

NEEDLES = [
    ("ORBITAL-7", "Q7-4419"),
    ("HALCYON-3", "K3-8820"),
    ("MERIDIAN-9", "M9-1274"),
    ("CASCADE-5", "R2-6631"),
    ("TUNDRA-2", "T5-9084"),
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def post(path, payload, timeout=900):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def chat(prompt, max_tokens=256):
    t0 = time.time()
    r = post("/v1/chat/completions", {"messages": [{"role": "user", "content": prompt}],
                                     "temperature": 0, "max_tokens": max_tokens})
    wall = time.time() - t0
    msg = r["choices"][0]["message"]
    return (msg.get("content") or "").strip(), wall, r.get("usage", {})


def count_tokens(text):
    return len(post("/tokenize", {"content": text})["tokens"])


def haystack(target_tokens, chunks):
    out, n = [], 0
    for c in chunks:
        t = c["text"]
        out.append(t)
        n += len(t.split()) * 1.3
        if n >= target_tokens * 4:  # chars ~= 4 * tokens
            break
    text = "\n\n".join(out)
    # trim to target tokens with the model's tokenizer
    while count_tokens(text) > target_tokens and len(text) > 1000:
        text = text[: int(len(text) * 0.9)]
    return text


def speed(pid, depth, chunks):
    hs = haystack(depth, chunks)
    r = post("/completion", {"prompt": hs, "n_predict": 128, "temperature": 0,
                             "cache_prompt": False, "top_k": 1})
    t = r.get("timings", {})
    rss = 0
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                rss = int(line.split()[1]) // 1024
    except OSError:
        pass
    return {"depth_tokens": t.get("prompt_n"), "pp": round(t.get("prompt_per_second", 0), 2),
            "tg": round(t.get("predicted_per_second", 0), 2), "rss_mb": rss}


def run_if():
    rows = []
    for task in IF_TASKS:
        out, wall, usage = chat(task["prompt"], 256)
        low = out.lower()
        if task["check"] == "exact":
            ok = out.strip() == task["expect"]
        elif task["check"] == "contains":
            ok = task["expect"].lower() in low
        elif task["check"] == "all_contains":
            ok = all(x in low for x in task["expect"])
        else:
            try:
                ok = json.loads(re.search(r"\{.*\}", out, re.S).group()) == task["expect"]
            except Exception:
                ok = False
        rows.append({"id": task["id"], "ok": ok, "output": out[:300], "wall": round(wall, 2)})
    return rows


def run_json():
    rows = []
    keys = ["invoice", "vendor", "date", "total", "category"]
    for i, doc in enumerate(DOCS):
        text = ("Invoice {invoice} from {vendor}, dated {date}, total EUR {total:.2f}, "
                "category {category}.").format(**doc)
        prompt = ("Extract the invoice fields as JSON only, with exactly these keys: "
                  + ", ".join(keys) + ". Text: " + text)
        out, wall, usage = chat(prompt, 768)
        try:
            obj = json.loads(re.search(r"\{.*\}", out, re.S).group())
            def same(k):
                a, b = obj.get(k), doc[k]
                if isinstance(b, (int, float)):
                    try: return abs(float(a) - float(b)) < 1e-6
                    except (TypeError, ValueError): return False
                return str(a).strip() == str(b)
            ok = set(obj) == set(keys) and all(same(k) for k in keys)
        except Exception:
            obj, ok = None, False
        rows.append({"id": f"json-{i+1:02d}", "ok": ok, "output": out[:400], "wall": round(wall, 2)})
    return rows


def run_niah(chunks, depths):
    rows = []
    for depth in depths:
        hs = haystack(depth, chunks)
        for i, (entity, code) in enumerate(NEEDLES):
            pos = int(len(hs) * (i + 0.5) / len(NEEDLES))
            needle = f"The access code for {entity} is {code}."
            text = hs[:pos] + "\n\n" + needle + "\n\n" + hs[pos:]
            prompt = ("Read the text and answer with the access code only.\n\nTEXT:\n"
                      + text + f"\n\nQUESTION: What is the access code for {entity}?")
            out, wall, usage = chat(prompt, 48)
            rows.append({"id": f"niah-{depth}-{entity}", "ok": code in out,
                         "output": out[:120], "wall": round(wall, 2)})
    return rows


def run_tool():
    rows = []
    spec = json.dumps(TOOLS)
    for i, case in enumerate(TOOL_CASES):
        prompt = (f"Tools: {spec}\nChoose one tool for the request and reply with JSON only: "
                  '{"tool": "<name>", "arguments": {...}}. Request: ' + case["prompt"])
        out, wall, usage = chat(prompt, 256)
        try:
            obj = json.loads(re.search(r"\{.*\}", out, re.S).group())
            ok = (obj.get("tool") == case["tool"]
                  and all(str(obj.get("arguments", {}).get(k, "")).lower() == str(v).lower()
                          for k, v in case["args"].items()))
        except Exception:
            ok = False
        rows.append({"id": f"tool-{i+1:02d}", "ok": ok, "output": out[:300], "wall": round(wall, 2)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--tier", choices=("full", "variant"), default="full")
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-niah8k", action="store_true")
    ap.add_argument("--ngl", type=int, default=-1)
    ap.add_argument("--ctx", type=int, default=8192)
    ap.add_argument("--load", type=float, default=-1)
    ap.add_argument("--commit", default="")
    args = ap.parse_args()

    idx = json.loads(Path("/home/dav-sd/deck-rag/pilot3/index/test_embedded_prefix.json").read_text())
    chunks = idx["chunks"]
    started = time.time()
    res = {"label": args.label, "file": args.file, "tier": args.tier,
           "params": {"ngl": args.ngl, "ctx": args.ctx, "threads": 4,
                      "load_s": args.load, "llama_commit": args.commit},
           "sha256": sha256_file(args.file),
           "size_gb": round(os.path.getsize(args.file) / 1e9, 2), "tasks": {}}

    sp4 = speed(args.pid, 3500, chunks)
    res["tasks"]["speed4k"] = sp4
    sp8 = None
    if not args.skip_niah8k:
        try:
            sp8 = speed(args.pid, 7400, chunks)
        except Exception as exc:
            sp8 = {"error": str(exc)}
        res["tasks"]["speed8k"] = sp8

    res["tasks"]["if"] = run_if()
    res["tasks"]["json"] = run_json()
    res["tasks"]["tool"] = run_tool()
    res["tasks"]["niah4k"] = run_niah(chunks, [3500])
    if not args.skip_niah8k:
        res["tasks"]["niah8k"] = run_niah(chunks, [7000])

    if_score = sum(r["ok"] for r in res["tasks"]["if"]) / len(IF_TASKS) * 15
    json_score = sum(r["ok"] for r in res["tasks"]["json"]) / len(DOCS) * 20
    tool_score = sum(r["ok"] for r in res["tasks"]["tool"]) / len(TOOL_CASES) * 5
    niah_all = res["tasks"]["niah4k"] + res["tasks"].get("niah8k", [])
    niah_score = sum(r["ok"] for r in niah_all) / len(niah_all) * 15
    tg = sp4.get("tg") or 0
    speed_score = min(10.0, 10.0 * tg / 8.0)
    res["scores"] = {"if": round(if_score, 2), "json": round(json_score, 2),
                     "tool": round(tool_score, 2), "niah": round(niah_score, 2),
                     "speed": round(speed_score, 2)}
    res["gates"] = {"tg_ge_5": tg >= 5, "json_ge_9": sum(r["ok"] for r in res["tasks"]["json"]) >= 9,
                    "niah4k_ge_4": sum(r["ok"] for r in res["tasks"]["niah4k"]) >= 4,
                    "rss_le_10_5_gb": sp4.get("rss_mb", 999999) <= 10752}
    res["elapsed_s"] = round(time.time() - started, 1)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({"label": args.label, "scores": res["scores"], "gates": res["gates"],
                      "tg": tg, "elapsed": res["elapsed_s"]}))


if __name__ == "__main__":
    main()
