#!/usr/bin/env python3
"""Aggregate per-model results into summary.json, summary.csv and REPORT.md."""
import csv
import json
from pathlib import Path

BENCH = Path.home() / "deck-bench"
PILOT = Path.home() / "deck-rag/pilot3/runs"
TIER = {
    "qwen35-4b-base": "full", "gemma4-e2b-base": "full", "nanbeige-3b": "full",
    "gemma4-e4b-base": "full", "qwen35-9b-base": "full", "gemma4-12b-qat": "full",
    "qwen35-4b-unc": "variant", "gemma4-e2b-unc": "variant", "gemma4-e4b-unc": "variant",
    "deepseek-9b-unc": "variant", "forge-1-e2b": "variant", "bimo-7b": "variant",
}


def main():
    rows = []
    for extra_path in sorted((BENCH / "results").glob("*-extra.json")):
        e = json.loads(extra_path.read_text())
        label = e["label"]
        mpath = PILOT / f"{label}-wiki64/metrics.json"
        wiki = None
        if mpath.exists():
            m = json.loads(mpath.read_text()).get("embed", {})
            wiki = {"n": m.get("n"), "answer_ok": m.get("answer_ok"),
                    "citation_ok": m.get("citation_ok"),
                    "mean_latency_s": m.get("mean_latency_s")}
        s = e.get("scores", {})
        wiki_score = 0.0
        if wiki and wiki.get("answer_ok") is not None:
            wiki_score = 35.0 * (0.7 * wiki["answer_ok"] + 0.3 * (wiki.get("citation_ok") or 0))
        total = sum(v for k, v in s.items() if isinstance(v, (int, float))) + wiki_score
        niah4 = e.get("tasks", {}).get("niah4k", [])
        json_ok = sum(1 for r in e.get("tasks", {}).get("json", []) if r.get("ok"))
        gates = {
            "tg_ge_5": (e.get("tasks", {}).get("speed4k", {}).get("tg") or 0) >= 5,
            "wiki_answer_ge_50": bool(wiki and (wiki.get("answer_ok") or 0) >= 0.5),
            "wiki_citation_ge_60": bool(wiki and (wiki.get("citation_ok") or 0) >= 0.6),
            "json_ge_9": json_ok >= 9,
            "niah4k_ge_4": sum(1 for r in niah4 if r.get("ok")) >= 4,
            "rss_le_10_5_gb": (e.get("tasks", {}).get("speed4k", {}).get("rss_mb") or 999999) <= 10752,
        }
        rows.append({
            "label": label, "tier": e.get("tier") or TIER.get(label, "?"),
            "size_gb": e.get("size_gb"), "sha256": e.get("sha256"),
            "params": e.get("params", {}),
            "tg": e.get("tasks", {}).get("speed4k", {}).get("tg"),
            "pp": e.get("tasks", {}).get("speed4k", {}).get("pp"),
            "rss_mb": e.get("tasks", {}).get("speed4k", {}).get("rss_mb"),
            "wiki": wiki, "wiki_score": round(wiki_score, 2),
            "scores": s, "total": round(total, 2), "gates": gates,
            "all_gates": all(gates.values()), "elapsed_s": e.get("elapsed_s"),
        })

    rows.sort(key=lambda r: r["total"], reverse=True)
    (BENCH / "results/summary.json").write_text(json.dumps(rows, indent=1))
    with (BENCH / "results/summary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "label", "tier", "size_gb", "tg", "rss_mb", "wiki_ans",
                    "wiki_cit", "if", "json", "tool", "niah", "speed", "wiki", "total", "all_gates"])
        for i, r in enumerate(rows, 1):
            w.writerow([i, r["label"], r["tier"], r["size_gb"], r["tg"], r["rss_mb"],
                        (r["wiki"] or {}).get("answer_ok"), (r["wiki"] or {}).get("citation_ok"),
                        r["scores"].get("if"), r["scores"].get("json"), r["scores"].get("tool"),
                        r["scores"].get("niah"), r["scores"].get("speed"),
                        r["wiki_score"], r["total"], r["all_gates"]])

    lines = ["# Steam Deck local-LLM benchmark", "",
             "Frozen 64-case wiki retrieval per model; deterministic checks. "
             "Scores: wiki 35, JSON 20, IF 15, NIAH 15, speed 10, tool 5.", "",
             "| # | model | tier | GB | tg/s | wiki ans | cite | total | gates |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        wiki = r["wiki"] or {}
        lines.append(f"| {i} | {r['label']} | {r['tier']} | {r['size_gb']} | {r['tg']} | "
                     f"{wiki.get('answer_ok')} | {wiki.get('citation_ok')} | {r['total']} | "
                     f"{'PASS' if r['all_gates'] else 'FAIL'} |")
    (BENCH / "results/REPORT.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
