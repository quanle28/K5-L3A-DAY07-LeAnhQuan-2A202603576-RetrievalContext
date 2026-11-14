"""Restore the frozen Day 6 B collection on another machine. No fake vectors."""
from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.common import digest, load
from src.retrieval import day6_package


def main():
    config = load(ROOT / "config.json")
    day6 = (ROOT / config["day6_root"]).resolve()
    destination = ROOT / ".cache/qdrant"
    if destination.exists():
        print("Index already exists. It will not be overwritten.")
        return
    source = day6 / ".cache/qdrant"
    if source.exists():
        shutil.copytree(source, destination)
        print("Copied actual Day 6 persistent vector store")
        return
    name = day6_package(day6)
    embedder = importlib.import_module(name + ".embeddings").MyEmbedder(config["model"], str(day6 / ".cache/models"))
    embedder.cache_path = ROOT / ".cache/embeddings.json"
    models = importlib.import_module(name + ".models")
    store_class = importlib.import_module(name + ".store").QdrantStore
    chunks = [models.Chunk(c["id"], c["source_id"], c["source"], c["page"], c["text"], c["metadata"])
              for c in load(ROOT / "data/chunks.json")]
    vectors = embedder.embed_documents([c.text for c in chunks])
    store = store_class(str(destination), embedder.dimensions)
    try:
        store.upsert("B", chunks, vectors)
        if store.count("B") != len(chunks):
            raise RuntimeError("Incomplete reconstructed index")
        print("Rebuilt Day 6 B from frozen chunks with locked real BGE model")
    finally:
        store.close()


if __name__ == "__main__": main()
