"""
performance.py
--------------
MongoDB Index Inspection and Query Optimization Analysis.
Implements controlled, reproducible explain() benchmarks comparing COLLSCAN vs IXSCAN
using real PyMongo executionStats.
"""

from typing import Dict, Any, List, Optional
import time
from database import get_db

# Educational content for Viva and UI
INDEX_CONCEPTS_EXPLANATION = {
    "COLLSCAN": (
        "Collection Scan: MongoDB must inspect every single document in the collection "
        "from start to finish because no relevant index exists. As the collection grows, "
        "query time scales linearly O(N), resulting in high disk I/O and CPU utilization."
    ),
    "IXSCAN": (
        "Index Scan: MongoDB navigates a B-Tree index data structure in O(log N) time to "
        "locate matching index keys directly. Only matching documents are fetched into memory, "
        "drastically reducing totalDocsExamined."
    ),
    "SELECTIVITY": (
        "Index selectivity measures how effectively an index filters out non-matching rows. "
        "Highly selective fields (like unique emails or UUIDs) benefit the most from indexes. "
        "Low-selectivity fields (e.g., boolean flags) may see minimal gain."
    ),
    "OVERHEAD": (
        "Indexes speed up reads but incur a write penalty. Every insert, update, or delete "
        "must update the corresponding B-Tree nodes. Each index also consumes additional RAM "
        "in the WiredTiger storage engine cache."
    )
}


def get_collection_indexes(collection_name: str) -> List[Dict[str, Any]]:
    """Retrieve all index specifications for a given collection."""
    db = get_db()
    try:
        col = db[collection_name]
        raw_indexes = list(col.list_indexes())
        formatted = []
        for idx in raw_indexes:
            formatted.append({
                "name": idx.get("name"),
                "key": list(idx.get("key", {}).items()),
                "unique": idx.get("unique", False),
                "sparse": idx.get("sparse", False),
                "version": idx.get("v")
            })
        return formatted
    except Exception as e:
        print(f"Error fetching indexes for {collection_name}: {e}")
        return []


def parse_execution_stats(explain_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract execution statistics from MongoDB explain command output.
    Gracefully handles different MongoDB versions and execution plan formats.
    """
    stats = explain_output.get("executionStats", {})
    winning_plan = explain_output.get("queryPlanner", {}).get("winningPlan", {})

    # Extract root or child stage
    stage = winning_plan.get("stage", "UNKNOWN")
    if stage == "FETCH" and "inputStage" in winning_plan:
        stage = f"FETCH -> {winning_plan['inputStage'].get('stage', 'IXSCAN')}"
    elif stage == "PROJECTION_DEFAULT" and "inputStage" in winning_plan:
        stage = winning_plan["inputStage"].get("stage", stage)

    n_returned = stats.get("nReturned", 0)
    total_docs = stats.get("totalDocsExamined", 0)
    total_keys = stats.get("totalKeysExamined", 0)
    exec_time_ms = stats.get("executionTimeMillis", 0)

    return {
        "stage": stage,
        "nReturned": n_returned,
        "totalDocsExamined": total_docs,
        "totalKeysExamined": total_keys,
        "executionTimeMillis": exec_time_ms,
        "raw_stats": stats,
        "winning_plan": winning_plan
    }


def run_controlled_explain_benchmark(num_sample_docs: int = 500) -> Dict[str, Any]:
    """
    Execute a controlled, isolated benchmark comparing unindexed vs indexed query.
    1. Creates temporary collection 'temp_perf_benchmark'.
    2. Inserts representative course documents across varied categories.
    3. Runs explain(executionStats) on category filter WITHOUT index (COLLSCAN).
    4. Creates index on category.
    5. Runs identical explain(executionStats) WITH index (IXSCAN).
    6. Safely drops temporary collection so project data remains pristine.
    """
    db = get_db()
    temp_coll_name = "temp_perf_benchmark"
    db.drop_collection(temp_coll_name)
    temp_col = db[temp_coll_name]

    # Generate sample documents
    categories = [
        "Data Science",
        "Artificial Intelligence",
        "Web Development",
        "Database Systems",
        "Cloud Computing",
        "Cybersecurity"
    ]
    levels = ["Beginner", "Intermediate", "Advanced"]

    sample_docs = []
    for i in range(num_sample_docs):
        cat = categories[i % len(categories)]
        lvl = levels[i % len(levels)]
        sample_docs.append({
            "title": f"Course Module #{i+1:04d}",
            "category": cat,
            "level": lvl,
            "duration_hours": 20.0 + (i % 30),
            "rating": 4.0 + ((i % 10) / 10.0),
            "description": f"Benchmark syllabus covering technical competencies in {cat}."
        })
    temp_col.insert_many(sample_docs)

    target_category = "Data Science"
    query_filter = {"category": target_category}

    # 1. Unindexed Explain (COLLSCAN expected)
    unindexed_explain = db.command(
        "explain",
        {
            "find": temp_coll_name,
            "filter": query_filter
        },
        verbosity="executionStats"
    )
    unindexed_metrics = parse_execution_stats(unindexed_explain)

    # 2. Create index on category
    temp_col.create_index([("category", 1)], name="idx_temp_category")

    # 3. Indexed Explain (IXSCAN expected)
    indexed_explain = db.command(
        "explain",
        {
            "find": temp_coll_name,
            "filter": query_filter
        },
        verbosity="executionStats"
    )
    indexed_metrics = parse_execution_stats(indexed_explain)

    # 4. Clean up temporary test collection
    db.drop_collection(temp_coll_name)

    return {
        "dataset_size": num_sample_docs,
        "query_filter": query_filter,
        "unindexed": unindexed_metrics,
        "indexed": indexed_metrics,
        "comparison": {
            "docs_examined_reduction": unindexed_metrics["totalDocsExamined"] - indexed_metrics["totalDocsExamined"],
            "docs_reduction_pct": (
                round(
                    ((unindexed_metrics["totalDocsExamined"] - indexed_metrics["totalDocsExamined"]) / unindexed_metrics["totalDocsExamined"]) * 100,
                    1
                )
                if unindexed_metrics["totalDocsExamined"] > 0
                else 0.0
            ),
            "unindexed_stage": unindexed_metrics["stage"],
            "indexed_stage": indexed_metrics["stage"],
        }
    }


if __name__ == "__main__":
    print("=" * 65)
    print("MongoDB Performance Benchmark: COLLSCAN vs IXSCAN")
    print("=" * 65)
    res = run_controlled_explain_benchmark(num_sample_docs=500)
    print(f"Dataset Size      : {res['dataset_size']} documents")
    print(f"Query Filter      : {res['query_filter']}")
    print("-" * 65)
    print("UNINDEXED (COLLSCAN):")
    print(f"  Stage           : {res['unindexed']['stage']}")
    print(f"  Docs Examined   : {res['unindexed']['totalDocsExamined']}")
    print(f"  Keys Examined   : {res['unindexed']['totalKeysExamined']}")
    print(f"  Returned        : {res['unindexed']['nReturned']}")
    print(f"  Execution Time  : {res['unindexed']['executionTimeMillis']} ms")
    print("-" * 65)
    print("INDEXED (IXSCAN):")
    print(f"  Stage           : {res['indexed']['stage']}")
    print(f"  Docs Examined   : {res['indexed']['totalDocsExamined']}")
    print(f"  Keys Examined   : {res['indexed']['totalKeysExamined']}")
    print(f"  Returned        : {res['indexed']['nReturned']}")
    print(f"  Execution Time  : {res['indexed']['executionTimeMillis']} ms")
    print("-" * 65)
    print("OPTIMIZATION RESULTS:")
    print(f"  Docs Avoided    : {res['comparison']['docs_examined_reduction']}")
    print(f"  Efficiency Gain : {res['comparison']['docs_reduction_pct']}% reduction in scanned documents")
    print("=" * 65)

