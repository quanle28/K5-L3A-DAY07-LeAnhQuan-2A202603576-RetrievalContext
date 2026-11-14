"""Regression tests. Fake model responses test control flow, never benchmark quality."""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.agent import run
from src.common import canonical, evidence_hit, load
from src.experiment import annotate, summarize
from src.retrieval import BM25, Retriever, pack_context, rrf, tokens


def chunk(cid, text, chapter="one", page=1):
    return {"id": cid, "text": text, "source_id": "doc", "source": "https://example.test/doc",
            "page": page, "metadata": {"chapter": chapter}}


class RetrievalTests(unittest.TestCase):
    def test_bm25_identifiers_operators_and_filter(self):
        rows = [chunk("a", "Use // for floor division; % returns remainder."), chunk("b", "sys.path is a Python module path.", "two")]
        index = BM25(rows)
        self.assertEqual(index.search("floor division //")[0]["id"], "a")
        self.assertIn("__name__", tokens("__name__ // % /"))
        self.assertIn("//", tokens("__name__ // % /"))
        self.assertEqual(index.search("Python module path", filters={"chapter": "one"}), [])
        with self.assertRaises(ValueError): index.search("q", filters={"gold_page": 1})
        with self.assertRaises(ValueError): index.search("q", filters={"page": True})

    def test_rrf_uses_ranks_not_incomparable_raw_scores(self):
        a, b = chunk("a", "a"), chunk("b", "b")
        ranking = rrf({"dense": [{**a, "score": .8}, {**b, "score": .7}],
                       "bm25": [{**b, "score": 1000}]}, 2)
        self.assertEqual(ranking[0]["id"], "b")
        self.assertAlmostEqual(ranking[0]["score"], 1/62 + 1/61)
        self.assertEqual(ranking[0]["component_ranks"]["bm25"]["rank"], 1)

    def test_context_budget_counts_headers_and_preserves_whole_chunks(self):
        a = chunk("a", "Some evidence.")
        same = {**a, "id": "duplicate"}
        self.assertEqual(pack_context([a, same], 1000)[1], ["a"])
        self.assertEqual(pack_context([a], 1), ("", []))
        block, ids = pack_context([a], 1000)
        self.assertEqual(pack_context([a], len(block)), (block, ids))
        self.assertEqual(pack_context([a], len(block) - 1), ("", []))

    def test_dense_unavailable_does_not_silently_fallback(self):
        retriever = Retriever("dense", BM25([chunk("a", "evidence")]))
        with self.assertRaises(RuntimeError): retriever.search("evidence")


class DatasetTests(unittest.TestCase):
    def test_frozen_corpus_and_new_holdout(self):
        from src.common import digest
        frozen = load(ROOT / "data/frozen.json")
        for path, checksum in frozen["hashes"].items():
            self.assertEqual(digest(ROOT / path), checksum)
        chunks = load(ROOT / "data/chunks.json")
        cases = load(ROOT / "data/questions.json")
        self.assertEqual(len({c["id"] for c in chunks}), 281)
        self.assertEqual(len({q["id"] for q in cases}), 24)
        for split, yes, no in [("dev", 15, 2), ("test", 5, 2)]:
            selected = [q for q in cases if q["split"] == split]
            self.assertEqual(sum(q["answerable"] for q in selected), yes)
            self.assertEqual(sum(not q["answerable"] for q in selected), no)
        for q in cases:
            if q["answerable"]:
                for gold in q["gold"]:
                    self.assertTrue(any(evidence_hit(c, [gold]) for c in chunks), q["id"])
            else:
                self.assertIn("All 77", q["absence_audit"]["scope"])
        self.assertTrue(all(q["id"].startswith("d7-t") for q in cases if q["split"] == "test" and q["answerable"]))

    def test_unanswerables_are_excluded_from_retrieval_denominator(self):
        rows = [{"status": "retrieved", "answerable": a, "hit1": False, "hit3": False,
                 "context_hit": False, "elapsed_seconds": .1, "context_chars": 0, "cost_usd": 0} for a in (True, False)]
        self.assertEqual(summarize(rows)["hit3"]["N"], 1)

    @unittest.skipUnless(importlib.util.find_spec("fastembed"), "real embedding dependencies unavailable in this interpreter")
    def test_actual_day6_qdrant_reopens_and_enforces_filter(self):
        from src.retrieval import Dense
        dense = Dense(load(ROOT / "config.json"))
        try:
            hits = dense.search("What is a class?", filters={"chapter": "classes"}, top_k=3)
            self.assertEqual(len(hits), 3)
            self.assertTrue(all(c["metadata"]["chapter"] == "classes" for c in hits))
            self.assertTrue(all(c["source_id"] == "python-classes" for c in hits))
        finally:
            dense.close()


class FakeClient:
    def __init__(self, actions): self.actions, self.messages = iter(actions), []
    def chat(self, messages, tools, tool_choice):
        self.messages.append(json.loads(json.dumps(messages)))
        action = next(self.actions)
        if isinstance(action, Exception): raise action
        name, args = action
        return {"tool_calls": [{"id": "call-1", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}, {"usage": {}, "cost_usd": 0, "model": "unit-test-only"}


class AgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.cid = "a" * 64
        self.row = chunk(self.cid, "A supported statement.")
        self.retriever = Retriever("bm25", BM25([self.row]))

    def test_valid_structured_citation_is_rendered_and_no_gold_enters_model(self):
        client = FakeClient([("search", {"query": "supported statement"}),
                             ("finish", {"answer": "A supported statement.", "citations": [self.cid], "abstain": False})])
        result = run("question", client, self.retriever, top_k=3, budget=800, max_searches=1)
        self.assertEqual(result["status"], "answered")
        self.assertIn(f"[{self.cid}]", result["answer"])
        self.assertNotIn("expected_answer", json.dumps(client.messages))
        self.assertEqual(result["search_count"], 1)

    def test_hallucinated_citation_abstains(self):
        client = FakeClient([("search", {"query": "supported"}), ("finish", {"answer": "claim", "citations": ["b" * 64], "abstain": False})])
        result = run("question", client, self.retriever, top_k=3, budget=800, max_searches=1)
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["citations"], [])

    def test_provider_failure_preserves_prior_search_and_cost(self):
        client = FakeClient([("search", {"query": "supported"}), ConnectionError("provider unavailable")])
        result = run("question", client, self.retriever, top_k=3, budget=800, max_searches=1)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["search_count"], 1)
        self.assertEqual(result["events"][-1]["error_type"], "ConnectionError")
        self.assertTrue(result["context_ids"])

    def test_multi_search_budget_is_cumulative_and_old_context_superseded(self):
        client = FakeClient([("search", {"query": "supported"}), ("search", {"query": "statement"}),
                             ("finish", {"answer": "", "citations": [], "abstain": True})])
        result = run("question", client, self.retriever, top_k=3, budget=800, max_searches=2)
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["context_ids"], [self.cid])
        tool_messages = [m for m in client.messages[-1] if m["role"] == "tool"]
        self.assertIn("superseded", tool_messages[0]["content"])
        self.assertLessEqual(result["context_chars"], 800)


if __name__ == "__main__": unittest.main()
