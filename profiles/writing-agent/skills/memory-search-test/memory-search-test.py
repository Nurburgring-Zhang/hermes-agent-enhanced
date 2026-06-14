#!/usr/bin/env python3
"""
Hermes Memory Search Test Command

Usage:
    hermes memory_search_test [--query QUERY] [--limit N] [--db PATH]
"""

import argparse
import json
import sys
from pathlib import Path

skill_path = Path.home() / ".hermes" / "skills" / "rag-memory-enhanced"
if skill_path.exists():
    sys.path.insert(0, str(skill_path))

from rag_core import RAGIndexer


def main():
    parser = argparse.ArgumentParser(description="Test RAG memory search quality")
    parser.add_argument("query", nargs="?", default=None,
                        help="Single query to test (default: run all test queries)")
    parser.add_argument("--limit", type=int, default=10,
                        help="Number of results per query (default: 10)")
    parser.add_argument("--db", type=str, default="~/.hermes/memory/main.sqlite",
                        help="Database path (default: ~/.hermes/memory/main.sqlite)")
    parser.add_argument("--workspace", type=str, default="~/.hermes/workspace",
                        help="Workspace directory (default: ~/.hermes/workspace)")
    parser.add_argument("--json", action="store_true",
                        help="Output in JSON format")

    args = parser.parse_args()

    db_path = Path(args.db).expanduser()
    workspace_dir = Path(args.workspace).expanduser()

    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        print("Run 'hermes memory_index' first to index files.")
        sys.exit(1)

    indexer = RAGIndexer(db_path=db_path, workspace_dir=workspace_dir, auto_watch=False)

    if args.query:
        # Single query test
        results = indexer.search(args.query, limit=args.limit)

        if args.json:
            output = {
                "query": args.query,
                "results": [
                    {
                        "chunk_id": r["id"],
                        "file": r["path"],
                        "score": r["score"],
                        "text_preview": r["text"][:300]
                    }
                    for r in results
                ],
                "total": len(results)
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\nSearch results for: '{args.query}'")
            print("=" * 80)
            if not results:
                print("  (No results)")
            for i, r in enumerate(results, 1):
                print(f"\n[{i}] Score: {r['score']:.4f} | Source: {r['path']}")
                print(f"    Lines: {r['start_line']}-{r['end_line']}")
                print(f"    Text: {r['text'][:300]}{'...' if len(r['text']) > 300 else ''}")

    else:
        # Run all test queries
        test_queries = [
            "authentication",
            "configuration",
            "database connection",
            "error handling",
            "file operations",
            "API endpoint",
            "user interface",
            "security",
            "logging",
            "data model",
            "function definition",
            "class definition",
            "import statement",
            "async function",
            "try except"
        ]

        print("\n<RAG Memory Search Test>")
        print("=" * 80)

        all_results = {}
        total_hits = 0

        for query in test_queries:
            results = indexer.search(query, limit=args.limit)
            total_hits += len(results)

            if args.json:
                all_results[query] = [
                    {"file": r["path"], "score": r["score"]}
                    for r in results
                ]
            else:
                print(f"\n'{query}': {len(results)} results")
                for r in results[:3]:  # Show top 3
                    print(f"  [{r['score']:.3f}] {Path(r['path']).name}")

        stats = indexer.get_stats()

        summary = {
            "queries_tested": len(test_queries),
            "total_results": total_hits,
            "avg_results_per_query": round(total_hits / len(test_queries), 2),
            "total_chunks": stats["chunks"]["total"],
            "total_files": stats["files"]["total"],
            "vector_coverage": stats["chunks"]["vector_coverage_percent"]
        }

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(json.dumps(summary, indent=2))

        # Recall estimate
        avg_recall_estimate = min(100, summary["avg_results_per_query"] * 10)  # rough heuristic
        print(f"\nEstimated retrieval quality: {'GOOD' if avg_recall_estimate >= 40 else 'NEEDS_IMPROVEMENT'}")
        print(f"  (Average {summary['avg_results_per_query']} results per query)")
        print("  Target: 5+ results per query for good coverage")

        if args.json:
            print("\nFull output:")
            print(json.dumps({
                "summary": summary,
                "details": all_results
            }, indent=2))

    indexer.close()

if __name__ == "__main__":
    main()
