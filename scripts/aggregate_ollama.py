#!/usr/bin/env python3
"""Render the Ollama PC/Deck comparison matrix as Markdown."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ["mimo-v2.6", "pplx-decider-flash", "bonsai-2-9b", "lfm3-1.7b"]
CATEGORIES = ["if", "json", "niah4k", "tool", "code"]
MANIFEST = json.loads((ROOT / "models_ollama.json").read_text(encoding="utf-8"))
SIZES = {item["label"]: item.get("size_gb") for item in MANIFEST["models"]}


def load(machine, label):
    path = ROOT / "results" / "ollama" / machine / (label + ".json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def cell(value):
    return "—" if value is None else f"{value:.1f}"


def mean_tg(summary):
    values = [summary[cat]["tg_mean"] for cat in CATEGORIES if summary.get(cat, {}).get("tg_mean") is not None]
    return sum(values) / len(values) if values else None


def main():
    rows = []
    for label in MODELS:
        pc = load("pc", label)
        deck = load("deck", label)
        if not pc and not deck:
            continue
        base = pc or deck
        size = (base.get("model_info") or {}).get("size_gb") or SIZES.get(label)
        rows.append((label, size, pc, deck))

    print("| model | GB | PC macro | Deck macro | Δ pp | PC tg/s | Deck tg/s |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for label, size, pc, deck in rows:
        p = (pc or {}).get("summary", {})
        d = (deck or {}).get("summary", {})
        pm, dm = p.get("macro_pct"), d.get("macro_pct")
        delta = None if pm is None or dm is None else pm - dm
        ptg = mean_tg(p)
        dtg = mean_tg(d)
        print(f"| `{label}` | {size if size is not None else '—'} | {cell(pm)} | {cell(dm)} | "
              f"{'—' if delta is None else f'{delta:+.1f}'} | {cell(ptg)} | {cell(dtg)} |")

    print("\n| model | IF | JSON | NIAH | Tool | Code |")
    print("|---|---:|---:|---:|---:|---:|")
    for label, _, pc, deck in rows:
        for machine, data in (("PC", pc), ("Deck", deck)):
            if not data:
                continue
            s = data["summary"]
            cells = " | ".join(cell(s.get(cat, {}).get("pct")) for cat in CATEGORIES)
            print(f"| `{label}` {machine} | {cells} |")


if __name__ == "__main__":
    main()
