"""Freeze Day 6 provenance and a new Day 7 holdout before retrieval."""
from __future__ import annotations

import shutil
from pathlib import Path

from .common import ROOT, canonical, digest, load, now, save


TEST_SPECS = [
    ("stdlib", "Why does the tutorial recommend import os instead of from os import *?",
     "Be sure to use the import os style", "operates much differently.",
     "To keep os.open from shadowing the built-in open function, which behaves differently."),
    ("stdlib", "Where are command-line arguments stored, and what container type holds them?",
     "Common utility scripts", "*argv* attribute as a list.", "In sys.argv, as a list."),
    ("stdlib", "Which module checks examples embedded in a program's docstrings?",
     "The doctest module provides", "tests embedded in a program's docstrings.", "doctest."),
    ("stdlib2", "What happens to an unresolved placeholder with string.Template.safe_substitute?",
     "The string.Template.substitute method raises", "it will leave placeholders unchanged if data is missing::",
     "It leaves the placeholder unchanged instead of raising KeyError for missing data."),
    ("stdlib2", "For a heapq heap, which position always holds the lowest-valued entry?",
     "The heapq module provides", "position zero.", "Position zero (index 0)."),
]

ABSENCE_SPECS = [
    ("dev", "What timeout value does asyncio.TaskGroup use by default?", ["TaskGroup"],
     "The complete snapshot has no TaskGroup API or default timeout specification."),
    ("dev", "What default transaction isolation level does sqlite3.connect use?", ["isolation_level"],
     "The sqlite3 paragraph describes a wrapper only, without connection isolation defaults."),
    ("test", "Which Django command rolls back exactly the latest database migration?", ["Django", "migrate"],
     "The snapshot contains no Django migration instructions; generic Python modules are insufficient."),
    ("test", "How does pip --require-hashes validate every dependency's archive hash?", ["require-hashes"],
     "The venv chapter explains pip install/freeze but not hash-checking mode or its dependency rules."),
]


def prepare(config):
    day6 = (ROOT / config["day6_root"]).resolve()
    if (ROOT / "data/frozen.json").exists():
        frozen = load(ROOT / "data/frozen.json")
        for name, checksum in frozen["hashes"].items():
            if digest(ROOT / name) != checksum:
                raise ValueError("Frozen dataset changed: " + name)
        print("Frozen data already prepared; no overwrite")
        return
    raw = [__import__("json").loads(line) for line in (day6 / "results/chunks_B.jsonl").read_text(encoding="utf-8").splitlines()]
    chunks = [{"id": c["chunk_id"], "source_id": c["document_id"], "source": c["source"],
               "page": c["page"], "text": c["text"], "metadata": c["metadata"]} for c in raw]
    pages = [__import__("json").loads(line) for line in (day6 / "data/pages.jsonl").read_text(encoding="utf-8").splitlines()]
    questions = []
    for old in load(day6 / "benchmark/questions.json"):
        if old["split"] != "dev":
            continue
        gold = [{"source_id": old["gold_source_id"], "page": old["gold_page"], "evidence": old["evidence_quote"]}]
        questions.append({"id": "d7-" + old["id"], "split": "dev", "answerable": True,
                          "question": old["question"], "expected_answer": old["expected_answer"],
                          "gold": gold, "filter": old.get("filter", {}), "origin": "Day 6 dev reused; never held out"})
    # Alternatives identified in Day 6's disclosed audit are frozen BEFORE Day 7.
    alternatives = {
        "d7-q07": ("python-controlflow", 6, "In fact, even functions without a return statement do return a value, albeit a rather boring one. This value is called None (it's a built-in name)."),
        "d7-q13": ("python-errors", 6, "After the statement is executed, the file *f* is always closed, even if a problem was encountered while processing the lines."),
    }
    for q in questions:
        if q["id"] in alternatives:
            doc, page, text = alternatives[q["id"]]
            q["gold"].append({"source_id": doc, "page": page, "evidence": text})
    for i, (chapter, query, start, end, answer) in enumerate(TEST_SPECS, 1):
        options = []
        for c in chunks:
            text = canonical(c["text"])
            left = text.find(start)
            right = text.find(end, left) if left >= 0 else -1
            if c["metadata"]["chapter"] == chapter and right >= 0:
                options.append({"source_id": c["source_id"], "page": c["page"], "evidence": text[left:right + len(end)]})
        if not options:
            raise ValueError("Cannot resolve new test evidence: " + query)
        questions.append({"id": f"d7-t{i:02d}", "split": "test", "answerable": True,
                          "question": query, "expected_answer": answer, "gold": options, "filter": {},
                          "origin": "New Day 7 holdout, separate facts from Day 6 test"})
    corpus_text = canonical(" ".join(p["text"] for p in pages)).casefold()
    for i, (split, query, terms, reason) in enumerate(ABSENCE_SPECS, 1):
        audit = {term: corpus_text.count(term.casefold()) for term in terms}
        questions.append({"id": f"d7-u{i:02d}", "split": split, "question": query, "answerable": False,
                          "expected_behavior": "search_and_abstain", "absence_reason": reason,
                          "absence_audit": {"scope": "All 77 normalized source units, not retrieval top-k", "term_counts": audit,
                                            "review": "AI checked corpus scope and nearby paragraphs; student confirmation pending"},
                          "gold": [], "filter": {}})
    save(ROOT / "data/chunks.json", chunks)
    save(ROOT / "data/questions.json", questions)
    shutil.copy2(day6 / "data/pages.jsonl", ROOT / "data/pages.jsonl")
    shutil.copy2(day6 / "data/manifest.json", ROOT / "data/day6_manifest.json")
    shutil.copy2(day6 / "data/raw/LICENSE-PYTHON.txt", ROOT / "data/LICENSE-PYTHON.txt")
    shutil.copy2(day6 / "starter/model_lock.json", ROOT / "data/model_lock.json")
    # Copy the actual persistent Day 6 vector store; never fabricate/re-embed vectors.
    target = ROOT / ".cache/qdrant"
    if target.exists():
        raise ValueError("Index destination exists before data freeze; inspect it before retrying")
    shutil.copytree(day6 / ".cache/qdrant", target)
    hashes = {name: digest(ROOT / name) for name in ["data/chunks.json", "data/questions.json", "data/pages.jsonl", "data/day6_manifest.json", "data/model_lock.json"]}
    save(ROOT / "data/frozen.json", {"created_at_utc": now(), "hashes": hashes,
        "day6_root": str(day6), "chunk_strategy": "B", "collection": config["collection"],
        "day6_chunk_export_sha256": digest(day6 / "results/chunks_B.jsonl"),
        "provenance": "PSF-licensed Python Tutorial v3.12.0; 10 chapters, 77 logical text units (not physical PDF pages), 281 chunks. AI-assisted benchmark; no human review claimed.",
        "test_policy": "Day 6 test was opened in its report and is NOT reused. Five new facts plus two missing-evidence cases frozen before Day 7 retrieval."})
    print(f"Prepared {len(chunks)} chunks, {len(pages)} units, {len(questions)} cases")
