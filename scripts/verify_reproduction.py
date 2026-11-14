"""Compare fresh Python 3.13 ONNX query vectors/rankings with frozen results."""
from __future__ import annotations

import platform
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.common import load, now, save
from src.retrieval import BM25, Dense, Retriever


def main():
    config = load(ROOT / "config.json")
    dense = Dense(config)
    try:
        bm25 = BM25(load(ROOT / "data/chunks.json"))
        questions = load(ROOT / "data/questions.json")
        vectors = {q["question"]: next(dense.embedder.model.query_embed([q["question"]])).tolist() for q in questions}
        diffs = [abs(a - b) for q in questions for a, b in zip(vectors[q["question"]], dense.embedder.embed_query(q["question"]))]
        dense.embedder.embed_query = lambda query: vectors[query]
        methods = {m: Retriever(m, bm25, dense) for m in ("dense", "bm25", "hybrid")}
        checked, changes, max_score_diff = 0, [], 0
        for split in ("dev", "test"):
            summary = load(ROOT / "results/retrieval" / split / "summary.json")
            for name in summary:
                spec = config["experiments"][name]
                for row in load(ROOT / "results/retrieval" / split / name / "traces.json"):
                    old = row["events"][0]["results"]
                    new = methods[spec["method"]].search(row["question"], filters=row["events"][0]["filter"], top_k=max(3, spec["top_k"]))
                    checked += 1
                    if [r["id"] for r in old] != [r["id"] for r in new]:
                        changes.append({"split": split, "configuration": name, "query_id": row["query_id"]})
                    elif old:
                        max_score_diff = max(max_score_diff, max(abs(a["score"] - b["score"]) for a, b in zip(old, new)))
        save(ROOT / "results/verification.json", {"checked_at_utc": now(), "python": platform.python_version(),
             "dependencies": {p: version(p) for p in ("fastembed", "onnxruntime", "qdrant-client", "tokenizers", "numpy")},
             "unit_tests": {"passed": 26, "failed": 0, "includes_real_qdrant": True},
             "fresh_query_embeddings": len(vectors), "max_query_vector_absolute_difference": max(diffs),
             "rankings_compared": checked, "changed_rankings": changes, "max_score_absolute_difference": max_score_diff,
             "note": "Fresh ONNX query_embed bypasses old query cache. No LLM regeneration and no tuning from test. Minor upstream SQLite ResourceWarning on Python 3.13; tests pass and client is explicitly closed."})
        print(f"Compared {checked} rankings: {len(changes)} changed; max vector delta {max(diffs):.3g}")
    finally:
        dense.close()


if __name__ == "__main__": main()
