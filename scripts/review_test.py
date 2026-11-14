"""Disclosed AI review of all seven held-out cases, after model execution."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "starter"))
from agent_metrics import aggregate
from src.common import load, save

LABELS = {
    "dense_base": {
        "d7-t01": (2, 2, [True], "stdlib/1 explicitly says os.open can shadow built-in open; answer and citation match."),
        "d7-t02": (0, 0, [False], "Answer says sys.argv/list but final context and cited controlflow/11 only explain variadic function arguments, not command-line arguments."),
        "d7-t03": (0, 0, [False, False], "Answer names doctest from general knowledge; context contains module names and docstring examples, without doctest's validation behavior."),
        "d7-t04": (2, 2, [True], "stdlib2/2 explicitly defines safe_substitute leaving unresolved placeholders and gives matching owner example."),
        "d7-t05": (2, 2, [True], "stdlib2/5 explicitly states lowest-valued heap entry at position zero; worked heapq example confirms."),
        "d7-u03": (None, None, [], "Correct explicit refusal, with no Django command added; all-source absence audit has no Django instructions."),
        "d7-u04": (None, None, [], "Correct explicit refusal, with no hash-checking assertion; venv snapshot lacks --require-hashes."),
    },
    "hybrid_context": {
        "d7-t01": (2, 2, [True], "stdlib/1 supports avoiding shadowing of built-in open by os.open."),
        "d7-t02": (2, 2, [True], "stdlib/1 says sys.argv is a list and shows demo.py/one/two/three, exactly matching answer."),
        "d7-t03": (1, 2, [False], "Final context contains sufficient doctest definition in stdlib/3, but model cites modules/6's builtins list with a doctest directive instead of the definition. Correct answer, wrong supporting citation."),
        "d7-t04": (2, 2, [True, False], "First citation in stdlib2/2 fully supports unchanged placeholders/KeyError example; second citation only custom delimiter renaming and does not support safe_substitute semantics."),
        "d7-t05": (2, 2, [True], "stdlib2/5 explicitly gives heap root position zero."),
        "d7-u03": (None, None, [False] * 6, "Fails abstention: invents Django rollback commands. Every citation is generic pip, exception, sys.argv or compilation text, not Django migration evidence."),
        "d7-u04": (None, None, [False] * 2, "Fails abstention: describes hash-checking behavior absent from snapshot, citing pip list/freeze/install paragraphs without --require-hashes."),
    },
}


def main():
    cases = [c for c in load(ROOT / "data/questions.json") if c["split"] == "test"]
    for name, labels in LABELS.items():
        folder = ROOT / "results/agent/test" / name
        traces = load(folder / "traces.json")
        reviews = []
        for t in traces:
            grade, context, support, reason = labels[t["query_id"]]
            if len(support) != len(t["citations"]):
                raise ValueError("Trace changed; these judgments apply only to the saved run")
            review = {"query_id": t["query_id"], "context_grade": context, "citation_support": support,
                      "reason": reason, "reviewer": "Codex (AI), read final context, answer and every cited source", "human_confirmed": False}
            if t["answerable"]:
                review["answer_grade"] = grade
            else:
                review["abstention_correct"] = name == "dense_base"
            reviews.append(review)
        save(folder / "reviews_ai.json", reviews)
        metrics = aggregate(cases, traces, reviews)
        metrics["review_provenance"] = "AI semantic audit, not human-confirmed; test has not been used to change pipeline"
        metrics["context_grades_0_1_2"] = dict(Counter(r["context_grade"] for r in reviews if r["context_grade"] is not None))
        metrics["search_count_distribution"] = dict(Counter(t["search_count"] for t in traces))
        save(folder / "agent_metrics_ai.json", metrics)
    print("Reviewed all 14 test outputs; no pipeline changes from test")


if __name__ == "__main__": main()
