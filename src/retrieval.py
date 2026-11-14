from __future__ import annotations

import importlib.util
import math
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from .common import ROOT, load

FILTER_FIELDS = {"chapter", "language", "version", "document_id", "page"}


def tokens(text):
    # Preserve Python identifiers and operators which ordinary word tokenizers lose.
    return re.findall(r"\w+|//|\*\*|==|!=|<=|>=|[%/]", unicodedata.normalize("NFC", text).casefold())


def validate_filters(filters):
    if not isinstance(filters, dict) or not set(filters).issubset(FILTER_FIELDS):
        raise ValueError("Unsupported metadata filter")
    if any(type(v) not in (str, int) for v in filters.values()):
        raise ValueError("Filters require string/integer equality")


def matches(chunk, filters):
    fields = {**chunk["metadata"], "document_id": chunk["source_id"], "page": chunk["page"]}
    return all(fields.get(k) == v for k, v in filters.items())


class BM25:
    def __init__(self, chunks, k1=1.5, b=0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.counts = [Counter(tokens(c["text"])) for c in chunks]
        self.lengths = [sum(c.values()) for c in self.counts]
        self.avg_length = sum(self.lengths) / max(1, len(chunks)) or 1
        df = Counter(t for row in self.counts for t in row)
        self.idf = {t: math.log(1 + (len(chunks) - n + .5) / (n + .5)) for t, n in df.items()}

    def search(self, query, *, filters=None, top_k=3):
        filters = filters or {}
        validate_filters(filters)
        if top_k < 1:
            raise ValueError("top_k must be positive")
        results = []
        for c, counts, length in zip(self.chunks, self.counts, self.lengths):
            if not matches(c, filters):
                continue
            score = 0.0
            for t in set(tokens(query)):
                tf = counts.get(t, 0)
                if tf:
                    score += self.idf[t] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / self.avg_length))
            if score > 0:
                results.append({**c, "score": score, "method": "bm25"})
        return sorted(results, key=lambda c: (-c["score"], c["id"]))[:top_k]


def rrf(rankings, top_k, constant=60):
    scores, records, ranks = {}, {}, {}
    for name, ranking in rankings.items():
        for rank, c in enumerate(ranking, 1):
            cid = c["id"]
            records[cid] = c
            scores[cid] = scores.get(cid, 0) + 1 / (constant + rank)
            ranks.setdefault(cid, {})[name] = {"rank": rank, "score": c["score"]}
    return [{**records[cid], "score": scores[cid], "component_ranks": ranks[cid], "method": "hybrid"}
            for cid in sorted(scores, key=lambda cid: (-scores[cid], cid))[:top_k]]


def day6_package(day6_root):
    """Load Day 6 under an alias: both repositories have a package named src."""
    name = "day6_lab_src"
    if name not in sys.modules:
        path = Path(day6_root) / "starter/src/__init__.py"
        spec = importlib.util.spec_from_file_location(name, path, submodule_search_locations=[str(path.parent)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return name


class Dense:
    def __init__(self, config):
        import importlib
        from qdrant_client import QdrantClient, models
        day6 = (ROOT / config["day6_root"]).resolve()
        package = day6_package(day6)
        embedder_class = importlib.import_module(package + ".embeddings").MyEmbedder
        os.environ.setdefault("FASTEMBED_OFFLINE", "1")
        self.embedder = embedder_class(config["model"], str(day6 / ".cache/models"))
        # All new query-cache writes belong to Day 7; Day 6 files remain intact.
        self.embedder.cache_path = ROOT / ".cache/embeddings.json"
        if self.embedder.cache_path.exists():
            self.embedder.cache.update(load(self.embedder.cache_path))
        self.client = QdrantClient(path=str(ROOT / ".cache/qdrant"))
        self.collection = config["collection"]
        try:
            vector_config = self.client.get_collection(self.collection).config.params.vectors
            if vector_config.size != self.embedder.dimensions or vector_config.size != config["dimensions"] or vector_config.distance != models.Distance.COSINE:
                raise ValueError("Day 6 embedding/index configuration mismatch")
            expected = {c["id"] for c in load(ROOT / "data/chunks.json")}
            actual, offset = set(), None
            while True:
                points, offset = self.client.scroll(self.collection, limit=256, offset=offset, with_vectors=False)
                actual.update(p.payload["chunk_id"] for p in points)
                if offset is None:
                    break
            if actual != expected:
                raise ValueError("Index chunk IDs differ from frozen Day 6 export")
        except Exception:
            self.client.close()
            raise

    def search(self, query, *, filters=None, top_k=3):
        from qdrant_client import models
        filters = filters or {}
        validate_filters(filters)
        if top_k < 1 or not query.strip():
            raise ValueError("Invalid query/top_k")
        conditions = [models.FieldCondition(key=k, match=models.MatchValue(value=v)) for k, v in filters.items()]
        hits = self.client.query_points(self.collection, query=self.embedder.embed_query(query), limit=top_k,
            query_filter=models.Filter(must=conditions) if conditions else None,
            search_params=models.SearchParams(exact=True), with_payload=True).points
        output = []
        for h in hits:
            p = h.payload
            output.append({"id": p["chunk_id"], "source_id": p["document_id"], "source": p["source"],
                           "page": p["page"], "text": p["text"], "metadata": {k: v for k, v in p.items()
                           if k not in {"chunk_id", "document_id", "source", "page", "text"}},
                           "score": h.score, "method": "dense"})
        return output

    def close(self):
        self.client.close()


class Retriever:
    def __init__(self, method, bm25, dense=None):
        if method not in {"bm25", "dense", "hybrid"}:
            raise ValueError("Unknown retrieval method")
        self.method, self.bm25, self.dense = method, bm25, dense

    def search(self, query, *, filters=None, top_k=3):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Empty query")
        if self.method == "bm25":
            return self.bm25.search(query, filters=filters, top_k=top_k)
        if self.dense is None:
            raise RuntimeError("Dense retrieval is unavailable; no lexical fallback")
        dense = self.dense.search(query, filters=filters, top_k=max(20, top_k) if self.method == "hybrid" else top_k)
        if self.method == "dense":
            return dense
        lexical = self.bm25.search(query, filters=filters, top_k=max(20, top_k))
        return rrf({"dense": dense, "bm25": lexical}, top_k)


def pack_context(results, budget):
    blocks, selected, seen = [], [], set()
    for c in results:
        # Skip duplicate IDs and identical text on the same source unit.
        key = (c["source_id"], c["page"], canonical_text(c["text"]))
        if c["id"] in selected or key in seen:
            continue
        seen.add(key)
        block = f'[{c["id"]} | {c["source"]} | source unit {c["page"]}]\n{c["text"]}'
        if len("\n\n".join(blocks + [block])) <= budget:
            blocks.append(block)
            selected.append(c["id"])
    return "\n\n".join(blocks), selected


def canonical_text(text):
    return " ".join(text.split())
