"""Record Codex's disclosed semantic review AFTER reading all dev answers/sources.

These are explicit per-case judgments, not substring-generated answer grades.
They are AI review labels; the student has not confirmed them.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "starter"))
from agent_metrics import aggregate
from src.common import load, now, save

GRADES = {
    "dense_base": [2, 0, 2, 0, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 0],
    "bm25": [2, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 2, 0],
    "hybrid": [2, 0, 2, 0, 2, 2, 2, 2, 2, 2, 1, 2, 0, 2, 0],
    "hybrid_context": [2, 2, 1, 1, 2, 2, 2, 2, 2, 1, 2, 2, 1, 1, 2],
}
FALSE_CITATIONS = {
    "dense_base": {"d7-q02": ["3b23c270"], "d7-q04": ["28159438"], "d7-q07": ["90c0d4e9"],
                   "d7-q11": ["1c86f2a6"], "d7-q14": ["bf0a4dba"], "d7-q15": ["26168ce0"], "d7-u02": ["8b225ef0"]},
    "bm25": {"d7-q02": ["255f100c"], "d7-q13": ["03255e35", "8b225ef0"], "d7-q15": ["26168ce0"]},
    "hybrid": {"d7-q02": ["3b23c270"], "d7-q04": ["28159438"], "d7-q07": ["b2d879a1"],
               "d7-q11": ["1c86f2a6"], "d7-q13": ["8b225ef0"], "d7-q14": ["bf0a4dba"],
               "d7-q15": ["26168ce0"], "d7-u02": ["695484b1"]},
    "hybrid_context": {"d7-q04": ["f935f66e"], "d7-q08": ["1a0126fe"], "d7-q10": ["99259945"],
                       "d7-q13": ["0f8e9a2f"], "d7-q14": ["9d532c51"], "d7-q15": ["26168ce0"],
                       "d7-u02": ["695484b1", "bbdb74eb"]},
}
REASONS = {
    "d7-q01": "Source text and worked examples support / -> float, // floor division and % remainder for the tutorial's integer operands.",
    "d7-q02": "Small-budget configurations omit the immutable/TypeError paragraph and cite indexing/slicing instead. BM25 also invents an incorrect slicing example. Larger context contains the explicit immutable and TypeError example.",
    "d7-q03": "Source explicitly shows -1 and says -0 equals 0. hybrid_context's phrase 'not a valid index' is misleading: -0 is valid but identical to 0, so grade 1.",
    "d7-q04": "BM25 cites the exact innermost for/while definition. Dense/small hybrid omit it. Larger hybrid includes it in context but cites a different loop-else example, so answer grade 1 and citation unsupported for the full claim.",
    "d7-q05": "Loop-else runs when no break occurs. The adjacent analogy paragraph is valid equivalent evidence even when strict frozen-quote context_hit is false; frozen gold is unchanged.",
    "d7-q06": "Source says default evaluated once, shows accumulated list and None workaround; the additional short definition-scope citation supports evaluation time.",
    "d7-q07": "Function source explicitly says implicit return is None. Unrelated finally/list-method sources do not prove the general function claim and are marked unsupported.",
    "d7-q08": "Definition and/or stack.append example support adding at list end. list.pop documentation does not support append and is marked unsupported when cited.",
    "d7-q09": "list.pop documentation explicitly says no index removes/returns last item.",
    "d7-q10": "deque paragraph supports efficient operations at both ends. hybrid_context cites queue.Queue/thread coordination instead; core answer is correct but sourced incorrectly, grade 1.",
    "d7-q11": "Dictionary paragraph explains mutable lists and immutable keys. Dense/small hybrid add an unsupported changing-hash explanation (lists are unhashable), grade 1; unrelated key-order citation is unsupported.",
    "d7-q12": "Set paragraph and dictionary paragraph support set() versus {}.",
    "d7-q13": "Dense/large hybrid contain explicit file-always-closed evidence; small BM25/hybrid cite exception chaining/notes instead. Large hybrid adds an unsupported try/finally comparison and extra irrelevant citation, grade 1.",
    "d7-q14": "Text-mode empty string is explicitly supported. readline/seek citations do not establish read-at-EOF. Large hybrid incorrectly extends the str claim to binary mode (which returns bytes), grade 1.",
    "d7-q15": "Small contexts show exceptional/early-exit conditions only, not ordinary completion. Large context includes the explicit whether-or-not exception paragraph and successful divide example; unrelated conditional-only citation is marked unsupported for no-exception claim.",
    "d7-u01": "Agent explicitly abstains without adding a timeout assertion; full-corpus absence audit has no TaskGroup API.",
    "d7-u02": "Only BM25 abstains. Other configurations invent DEFERRED/default transaction behavior that is absent from the snapshot; cited sqlite wrapper/example text does not support it.",
}


def main():
    cases = [c for c in load(ROOT / "data/questions.json") if c["split"] == "dev"]
    for name, grades in GRADES.items():
        folder = ROOT / "results/agent/dev" / name
        traces = load(folder / "traces.json")
        reviews = []
        for t in traces:
            qid = t["query_id"]
            false = FALSE_CITATIONS[name].get(qid, [])
            review = {"query_id": qid, "citation_support": [not any(cid.startswith(p) for p in false) for cid in t["citations"]],
                      "reason": REASONS[qid], "reviewer": "Codex (AI), read answer and cited source text", "human_confirmed": False}
            if t["answerable"]:
                review["answer_grade"] = grades[int(qid[-2:]) - 1]
            else:
                review["abstention_correct"] = t["status"] == "abstain"
            reviews.append(review)
        save(folder / "reviews_ai.json", reviews)
        metrics = aggregate(cases, traces, reviews)
        metrics["review_provenance"] = "AI semantic audit; not human-confirmed"
        metrics["search_count_distribution"] = dict(Counter(t["search_count"] for t in traces))
        save(folder / "agent_metrics_ai.json", metrics)
    selection_path = ROOT / "results/agent/selection.json"
    selection = load(selection_path)
    selection["quality_review_status"] = "AI-reviewed before test; no human verification claimed"
    selection["reviewed_at_utc"] = now()
    selection["review_conclusion"] = "Keep hybrid_context by the predeclared retrieval/context criterion. AI grounded score improves, but sqlite abstention still fails and citation precision remains imperfect; the BM25 tradeoff is disclosed. No test results consulted."
    selection["review_hashes"] = {n: __import__("hashlib").sha256((ROOT / "results/agent/dev" / n / "reviews_ai.json").read_bytes()).hexdigest() for n in GRADES}
    save(selection_path, selection)
    print("Recorded 68 explicit dev AI reviews; selection frozen before test")


if __name__ == "__main__": main()
