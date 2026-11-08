#!/usr/bin/env python3
"""Aggregate per-model results into summary.json, summary.csv and REPORT.md."""
import csv
import json
from pathlib import Path

BENCH = Path.home() / "deck-bench"
DOCS = json.loads((Path(__file__).resolve().parent / "docs.json").read_text())
PILOT = Path.home() / "deck-rag/pilot3/runs"
TIER = {
    "qwen35-4b-base": "full", "gemma4-e2b-base": "full", "nanbeige-3b": "full",
    "gemma4-e4b-base": "full", "qwen35-9b-base": "full", "gemma4-12b-qat": "full",
    "qwen35-4b-unc": "variant", "gemma4-e2b-unc": "variant", "gemma4-e4b-unc": "variant",
    "deepseek-9b-unc": "variant", "forge-1-e2b": "variant", "bimo-7b": "variant",
}


def check_json(output, doc):
    import re
    try:
        obj = json.loads(re.search(r"\{.*\}", output, re.S).group())
    except Exception:
        return False
    if set(obj) != set(doc):
        return False
    for k, want in doc.items():
        got = obj.get(k)
        if isinstance(want, (int, float)):
            try:
                num = re.sub(r"[^0-9.\-]", "", str(got))
                if abs(float(num) - float(want)) > 1e-6:
                    return False
            except ValueError:
                return False
        elif str(got).strip() != str(want).strip():
            return False
    return True


def main():
    rows = []
    for extra_path in sorted((BENCH / "results").glob("*-extra.json")):
        e = json.loads(extra_path.read_text())
        label = e["label"]
        mpath = PILOT / f"{label}-wiki64s/metrics.json"
        wiki = None
        if mpath.exists():
            m = json.loads(mpath.read_text()).get("embed", {})
            wiki = {"n": m.get("n"), "answer_ok": m.get("answer_ok"),
                    "answer_correct_answerable": m.get("answer_correct_answerable"),
                    "citation_ok": m.get("citation_ok_answerable"),
                    "citation_lenient": m.get("citation_ok_lenient_answerable"),
                    "abstention_ok_unanswerable": m.get("abstention_ok_unanswerable"),
                    "mean_latency_s": m.get("mean_latency_s")}
        s = dict(e.get("scores", {}))
        jrows = sorted(e.get("tasks", {}).get("json", []), key=lambda r: r["id"])
        jok = sum(check_json(r.get("output", ""), d) for r, d in zip(jrows, DOCS))
        s["json"] = round(jok / len(DOCS) * 20, 2)
        wiki_score = 0.0
        if wiki and wiki.get("answer_ok") is not None:
            wiki_score = 35.0 * (0.7 * (wiki.get("answer_correct_answerable") or 0)
                                 + 0.3 * (wiki.get("citation_lenient") or 0))
        total = sum(v for k, v in s.items() if isinstance(v, (int, float))) + wiki_score
        niah4 = e.get("tasks", {}).get("niah4k", [])
        json_ok = jok
        gates = {
            "tg_ge_5": (e.get("tasks", {}).get("speed4k", {}).get("tg") or 0) >= 5,
            "wiki_answer_ge_50": bool(wiki and (wiki.get("answer_correct_answerable") or 0) >= 0.5),
            "wiki_citation_ge_60": bool(wiki and (wiki.get("citation_lenient") or 0) >= 0.6),
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
                        (r["wiki"] or {}).get("answer_correct_answerable"),
                        (r["wiki"] or {}).get("citation_lenient"),
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
                     f"{wiki.get('answer_correct_answerable')} | {wiki.get('citation_lenient')} | {r['total']} | "
                     f"{'PASS' if r['all_gates'] else 'FAIL'} |")
    (BENCH / "results/REPORT.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
