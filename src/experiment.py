from __future__ import annotations

import statistics
import time

from .common import ROOT, digest, evidence_hit, load, now, save
from .retrieval import pack_context


def frozen_hashes():
    frozen = load(ROOT / "data/frozen.json")
    for name, checksum in frozen["hashes"].items():
        if digest(ROOT / name) != checksum:
            raise ValueError("Frozen data changed: " + name)
    # Changes to runtime code after selection invalidate a held-out run.
    paths = [ROOT / "config.json", *sorted((ROOT / "src").glob("*.py"))]
    return {**frozen["hashes"], **{p.relative_to(ROOT).as_posix(): digest(p) for p in paths}}


def ratio(n, total):
    return {"n": n, "N": total, "rate": n / total if total else None}


def summarize(rows):
    valid = [r for r in rows if r["status"] != "error"]
    answerable = [r for r in valid if r["answerable"]]
    costs = [r.get("cost_usd") for r in rows]
    return {"cases": len(rows), "errors": len(rows) - len(valid),
            **{key: ratio(sum(r[key] for r in answerable), len(answerable)) for key in ("hit1", "hit3", "context_hit")},
            "median_seconds": statistics.median(r["elapsed_seconds"] for r in rows),
            "total_seconds": sum(r["elapsed_seconds"] for r in rows),
            "cost_usd": sum(costs) if costs and all(c is not None for c in costs) else None,
            "mean_context_chars": statistics.mean(r["context_chars"] for r in valid) if valid else None,
            "answer_quality": "Not inferred from evidence substring matches; requires per-query semantic review."}


def annotate(case, trace):
    searches = [e for e in trace["events"] if e["event"] == "search"]
    first = searches[0]["results"] if searches else []
    all_hits = {c["id"]: c for e in searches for c in e["results"]}
    gold = case.get("gold", [])
    return {**trace, "query_id": case["id"], "split": case["split"], "question": case["question"],
            "answerable": case["answerable"], "hit1": bool(first and evidence_hit(first[0], gold)),
            "hit3": any(evidence_hit(c, gold) for c in first[:3]),
            "context_hit": any(evidence_hit(all_hits[cid], gold) for cid in trace["context_ids"]),
            "metric_scope": "Single-chunk alternative evidence; hit1/hit3 on FIRST query, context_hit on cumulative final context"}


def evaluate(config, split, retrievers, client=None, experiment_names=None):
    from .agent import run
    cases = [c for c in load(ROOT / "data/questions.json") if c["split"] == split]
    output = ROOT / "results" / ("agent" if client else "retrieval")
    hashes = frozen_hashes()
    selection_path = output / "selection.json"
    if split == "test":
        selection = load(selection_path)
        if selection["hashes"] != hashes:
            raise ValueError("Inputs/code changed since dev selection; do not tune on existing test")
        names = list(dict.fromkeys([config["baseline"], selection["selected"]]))
        if (output / "test/summary.json").exists():
            raise ValueError("Test already evaluated; preserve it instead of overwriting")
    else:
        names = experiment_names or list(config["experiments"])
    summaries = {}
    for name in names:
        spec = config["experiments"][name]
        retriever = retrievers[spec["method"]]
        traces = []
        for case in cases:
            start = time.perf_counter()
            if client:
                trace = run(case["question"], client, retriever, filters=case.get("filter", {}),
                            **{k: spec[k] for k in ("top_k", "budget", "max_searches")})
            else:
                try:
                    hits = retriever.search(case["question"], filters=case.get("filter", {}), top_k=max(3, spec["top_k"]))
                    context, ids = pack_context(hits[:spec["top_k"]], spec["budget"])
                    trace = {"status": "retrieved", "events": [{"event": "search", "tool": spec["method"],
                             "query": case["question"], "filter": case.get("filter", {}), "results": hits}],
                             "context": context, "context_ids": ids, "context_chars": len(context),
                             "elapsed_seconds": time.perf_counter() - start, "cost_usd": 0}
                except Exception as exc:
                    trace = {"status": "error", "events": [{"event": "error", "error_type": type(exc).__name__, "message": str(exc)[:300]}],
                             "context": "", "context_ids": [], "context_chars": 0, "elapsed_seconds": time.perf_counter() - start, "cost_usd": 0}
            row = {**annotate(case, trace), "configuration": name}
            traces.append(row)
            # Incremental checkpoints survive interrupted paid API experiments.
            save(output / split / name / "traces.json", traces)
            print(f'{"agent" if client else "retrieval"}/{split}/{name}/{case["id"]}: {trace["status"]}', flush=True)
            if trace["status"] == "error" and not any(t["status"] != "error" for t in traces):
                raise RuntimeError("First case failed; partial trace preserved. Resolve setup before spending on the remaining cases.")
        summaries[name] = summarize(traces)
        save(output / split / name / "summary.json", summaries[name])
        if client:
            reviews = [{"query_id": t["query_id"], "answer_grade": None if t["answerable"] else None,
                        "context_grade": None, "citation_support": [None] * len(t["citations"]),
                        "abstention_correct": None, "reason": "", "reviewer": "", "human_confirmed": False}
                       for t in traces if t["status"] != "error"]
            review_path = output / split / name / "reviews_template.json"
            if not review_path.exists():
                save(review_path, reviews)
    save(output / split / "summary.json", summaries)
    if split == "dev":
        if len({config["experiments"][n]["method"] for n in names}) < 3:
            raise ValueError("Selection requires all three methods on dev")
        selected = sorted(names, key=lambda n: (-summaries[n]["context_hit"]["n"], -summaries[n]["hit3"]["n"],
            -summaries[n]["hit1"]["n"], config["experiments"][n]["budget"], config["experiments"][n]["max_searches"], n))[0]
        if any(m["errors"] for m in summaries.values()):
            raise RuntimeError("Cannot select with provider errors")
        save(selection_path, {"selected": selected, "selected_at_utc": now(), "hashes": hashes,
            "rule": config["selection_rule"], "dev_metrics": summaries, "test_evaluated_before_selection": False,
            "quality_review_status": "Pending semantic review" if client else "Retrieval only; not a model-quality claim"})
        print("Selected on dev: " + selected, flush=True)
    return summaries
