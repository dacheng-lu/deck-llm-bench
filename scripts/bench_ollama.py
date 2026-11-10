#!/usr/bin/env python3
"""Run the multi-task Ollama benchmark on PC or Deck.

Usage:
  python3 scripts/bench_ollama.py --model lfm3 --label lfm3 --machine pc --out results/ollama/lfm3-pc.json

Only the Python standard library is used. The checker is deterministic; no model
judges another model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

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
]

NEEDLES = [
    ("ORBITAL-7", "Q7-4419"),
    ("HALCYON-3", "K3-8820"),
    ("MERIDIAN-9", "M9-1274"),
]

CODE_TASKS = [
    {
        "id": "code-add",
        "prompt": "Write a Python function add(a, b) that returns the sum. Reply with code only.",
        "check": "regex_all",
        "patterns": [r"def\s+add\s*\(", r"return\s+a\s*\+\s*b"],
    },
    {
        "id": "code-sql",
        "prompt": "Write a SQL query selecting name from users where age is greater than 18. Reply with SQL only.",
        "check": "regex_all",
        "patterns": [r"(?i)select\s+name", r"(?i)from\s+users", r"(?i)where", r"(?i)age\s*>\s*18"],
    },
    {
        "id": "code-reverse",
        "prompt": "Write a Python expression that reverses a string s. Reply with code only.",
        "check": "any_regex",
        "patterns": [r"\[\s*::\s*-1\s*\]", r"reversed\s*\("],
    },
    {
        "id": "code-email",
        "prompt": "Write a Python regex that matches a basic email address. Reply with the regex only.",
        "check": "regex_all",
        "patterns": [r"@", r"\.", r"\+"],
    },
]


def get(base, path, timeout=60):
    req = urllib.request.Request(base.rstrip("/") + path, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())


def post(base, path, payload, timeout=900):
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())


def chat(base, model, prompt, max_tokens=512, num_ctx=8192):
    started = time.time()
    response = post(
        base,
        "/api/chat",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "keep_alive": "5m",
            "options": {
                "temperature": 0,
                "seed": 42,
                "num_predict": max_tokens,
                "num_ctx": num_ctx,
                "top_k": 1,
            },
        },
    )
    wall = time.time() - started
    message = response.get("message") or {}
    content = (message.get("content") or "").strip()
    if not content and message.get("thinking"):
        content = (message.get("thinking") or "").strip()
    timing = {
        "wall_s": round(wall, 3),
        "load_ms": round((response.get("load_duration") or 0) / 1e6, 1),
        "prompt_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
        "ttft_s": None,
        "pp": None,
        "tg": None,
    }
    prompt_duration = response.get("prompt_eval_duration") or 0
    eval_duration = response.get("eval_duration") or 0
    if prompt_duration and timing["prompt_count"]:
        timing["pp"] = round(timing["prompt_count"] / (prompt_duration / 1e9), 2)
    if eval_duration and timing["eval_count"]:
        timing["tg"] = round(timing["eval_count"] / (eval_duration / 1e9), 2)
    return content, timing, response


def parse_json(text):
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        value = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def check_if(task, output):
    low = output.lower()
    if task["check"] == "exact":
        return output.strip() == task["expect"]
    if task["check"] == "contains":
        return task["expect"].lower() in low
    if task["check"] == "all_contains":
        return all(item.lower() in low for item in task["expect"])
    obj = parse_json(output)
    return obj == task["expect"]


def run_if(base, model):
    rows = []
    for task in IF_TASKS:
        output, timing, _ = chat(base, model, task["prompt"], max_tokens=256)
        rows.append({"id": task["id"], "ok": check_if(task, output), "output": output[:500], **timing})
    return rows


def run_json(base, model):
    rows = []
    keys = ["invoice", "vendor", "date", "total", "category"]
    for index, doc in enumerate(DOCS):
        text = (
            "Invoice {invoice} from {vendor}, dated {date}, total EUR {total:.2f}, "
            "category {category}."
        ).format(**doc)
        prompt = (
            "Extract the invoice fields as JSON only, with exactly these keys: "
            + ", ".join(keys)
            + ". Text: "
            + text
        )
        output, timing, _ = chat(base, model, prompt, max_tokens=768)
        obj = parse_json(output)

        def same(key):
            if obj is None:
                return False
            actual, expected = obj.get(key), doc[key]
            if isinstance(expected, (int, float)):
                try:
                    return abs(float(actual) - float(expected)) < 1e-6
                except (TypeError, ValueError):
                    return False
            return str(actual).strip() == str(expected)

        ok = obj is not None and set(obj) == set(keys) and all(same(key) for key in keys)
        rows.append({"id": "json-%02d" % (index + 1), "ok": ok, "output": output[:600], **timing})
    return rows


def make_haystack():
    sentence = (
        "The archive records routine maintenance notes, shipping manifests, and weather "
        "observations for the northern region. Nothing in this paragraph is a secret. "
    )
    text = sentence * 140
    for index, (entity, code) in enumerate(NEEDLES):
        position = int(len(text) * (index + 0.5) / len(NEEDLES))
        text = text[:position] + "\nThe access code for %s is %s.\n" % (entity, code) + text[position:]
    return text


def run_niah(base, model):
    rows = []
    haystack = make_haystack()
    for entity, code in NEEDLES:
        prompt = (
            "Read the text and answer with the access code only.\n\nTEXT:\n"
            + haystack
            + "\n\nQUESTION: What is the access code for %s?" % entity
        )
        output, timing, _ = chat(base, model, prompt, max_tokens=64, num_ctx=8192)
        rows.append({"id": "niah-4k-%s" % entity, "ok": code in output, "output": output[:200], **timing})
    return rows


def run_tool(base, model):
    rows = []
    spec = json.dumps(TOOLS)
    for index, case in enumerate(TOOL_CASES):
        prompt = (
            "Tools: %s\nChoose one tool for the request and reply with JSON only: "
            '{"tool": "<name>", "arguments": {...}}. Request: %s' % (spec, case["prompt"])
        )
        output, timing, _ = chat(base, model, prompt, max_tokens=320)
        obj = parse_json(output)
        ok = False
        if obj is not None and obj.get("tool") == case["tool"]:
            args = obj.get("arguments") or {}
            if isinstance(args, dict):
                ok = all(str(args.get(key, "")).lower() == str(value).lower() for key, value in case["args"].items())
        rows.append({"id": "tool-%02d" % (index + 1), "ok": ok, "output": output[:500], **timing})
    return rows


def run_code(base, model):
    rows = []
    for task in CODE_TASKS:
        output, timing, _ = chat(base, model, task["prompt"], max_tokens=768)
        if task["check"] == "regex_all":
            ok = all(re.search(pattern, output) for pattern in task["patterns"])
        else:
            ok = any(re.search(pattern, output) for pattern in task["patterns"])
        rows.append({"id": task["id"], "ok": ok, "output": output[:800], **timing})
    return rows


def score(rows):
    total = len(rows)
    passed = sum(1 for row in rows if row["ok"])
    speeds = [row["tg"] for row in rows if row.get("tg")]
    prompts = [row["pp"] for row in rows if row.get("pp")]
    return {
        "n": total,
        "ok": passed,
        "pct": round(100.0 * passed / total, 1) if total else 0.0,
        "tg_mean": round(sum(speeds) / len(speeds), 2) if speeds else None,
        "pp_mean": round(sum(prompts) / len(prompts), 2) if prompts else None,
        "wall_mean": round(sum(row["wall_s"] for row in rows) / total, 2) if total else None,
    }


def model_info(base, model):
    tags = get(base, "/api/tags")
    for item in tags.get("models", []):
        name = item.get("name") or item.get("model") or ""
        if name == model or name.split(":")[0] == model or name == model + ":latest" or model == name.split(":")[0]:
            return {
                "name": name,
                "size_gb": round((item.get("size") or 0) / 1e9, 2),
                "digest": item.get("digest"),
                "details": item.get("details"),
            }
    return {"name": model, "size_gb": None, "digest": None, "details": None}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:11434")
    parser.add_argument("--model", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--machine", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--categories", default="if,json,niah4k,tool,code")
    args = parser.parse_args(argv)

    selected = {item.strip() for item in args.categories.split(",") if item.strip()}
    unknown = selected - {"if", "json", "niah4k", "tool", "code"}
    if unknown:
        parser.error("unknown categories: %s" % ", ".join(sorted(unknown)))

    started = time.time()
    result = {
        "label": args.label,
        "model": args.model,
        "machine": args.machine,
        "base": args.base,
        "model_info": model_info(args.base, args.model),
        "started_at": round(started, 3),
        "tasks": {},
    }
    if "if" in selected:
        result["tasks"]["if"] = run_if(args.base, args.model)
    if "json" in selected:
        result["tasks"]["json"] = run_json(args.base, args.model)
    if "niah4k" in selected:
        result["tasks"]["niah4k"] = run_niah(args.base, args.model)
    if "tool" in selected:
        result["tasks"]["tool"] = run_tool(args.base, args.model)
    if "code" in selected:
        result["tasks"]["code"] = run_code(args.base, args.model)
    result["summary"] = {name: score(rows) for name, rows in result["tasks"].items()}
    result["summary"]["macro_pct"] = round(
        sum(result["summary"][name]["pct"] for name in result["summary"] if name != "macro_pct")
        / max(1, len(result["summary"])),
        1,
    )
    result["elapsed_s"] = round(time.time() - started, 1)

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
