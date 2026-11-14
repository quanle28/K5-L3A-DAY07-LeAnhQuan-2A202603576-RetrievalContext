from __future__ import annotations

import argparse
import json
import sys

from .common import ROOT, load


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Day 7 Agentic RAG lab")
    parser.add_argument("command", choices=["prepare", "check", "retrieval", "agent", "ask"])
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--configuration", default="hybrid_context")
    parser.add_argument("--question")
    parser.add_argument("--chapter")
    args = parser.parse_args()
    config = load(ROOT / "config.json")
    if args.command == "prepare":
        from .prepare import prepare
        prepare(config)
        return
    from .retrieval import BM25, Dense, Retriever
    from .experiment import evaluate, frozen_hashes
    frozen_hashes()
    dense = Dense(config)
    try:
        chunks = load(ROOT / "data/chunks.json")
        lexical = BM25(chunks)
        retrievers = {method: Retriever(method, lexical, dense) for method in ("dense", "bm25", "hybrid")}
        if args.command == "retrieval":
            evaluate(config, args.split, retrievers)
            return
        from .llm import ModelClient
        client = ModelClient()
        if args.command == "check":
            print(json.dumps({"embedding": dense.embedder.model_name, "dimensions": dense.embedder.dimensions,
                              "chunks": len(chunks), "model": client.model, "endpoint": client.base_url,
                              "api_key_configured": bool(client.key)}, indent=2))
        elif args.command == "agent":
            evaluate(config, args.split, retrievers, client)
        elif args.command == "ask":
            if not args.question:
                parser.error("ask requires --question")
            from .agent import run
            from .common import save
            spec = config["experiments"][args.configuration]
            trace = run(args.question, client, retrievers[spec["method"]], filters={"chapter": args.chapter} if args.chapter else {},
                        **{k: spec[k] for k in ("top_k", "budget", "max_searches")})
            save(ROOT / "results/demo.json", trace)
            print(trace["answer"] if trace["status"] != "error" else trace["events"][-1])
    finally:
        dense.close()


if __name__ == "__main__":
    main()
