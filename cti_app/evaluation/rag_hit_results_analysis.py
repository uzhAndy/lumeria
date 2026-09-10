import json
from collections import defaultdict
# from itertools import combinations

RESULTS_FILE = "results/retrieval_evaluation.json"

def analyze_results():
    with open(RESULTS_FILE, "r") as f:
        data = json.load(f)

    results = data.get("results", [])

    # Total queries analyzed
    total_queries = len(results)

    exclusive_hits = defaultdict(int)
    combination_hits = defaultdict(int)
    no_hit_queries = []

    # Define retrievers to consider (exclude reranker)
    BASE_RETRIEVERS = {"dense", "sparse", "intent_filter"}

    for entry in results:
        evaluation = entry.get("evaluation", {})
        graph_eval = entry.get("graph_evaluation", {})

        hit_sources = set()

        for retriever_name, retriever_data in evaluation.items():
            if retriever_name not in BASE_RETRIEVERS:
                continue
            if retriever_data.get("hit"):
                hit_sources.add(retriever_name)

        # Graph is considered a hit if there were retrieved documents
        graph_hit = graph_eval.get("has_results", False)
        if graph_hit:
            hit_sources.add("graph")

        # track queries that weren't supported by any documents
        reranker = evaluation.get("reranker", {})
        reranker_hit = reranker.get("hit", False)
        supported = reranker_hit or graph_hit
        if not supported:
            no_hit_queries.append(entry["query"])

        # Exclusive hits (only one source succeeded)
        if len(hit_sources) == 1:
            source = next(iter(hit_sources))
            exclusive_hits[source] += 1
            print(source)
            print(entry["query"])

        # Multiple hit combinations
        if len(hit_sources) > 1:
            combo = tuple(sorted(hit_sources))
            combination_hits[combo] += 1

        """
        # if to analyse how often do these retrievers succeed together at least
        if len(hit_sources) > 1:
            # Loop over combination sizes (max. len hit source size pair)
            for r in range(2, len(hit_sources) + 1):
                for combo in combinations(sorted(hit_sources), r):
                    combination_hits[combo] += 1
        """

    print(f"Total queries analyzed: {total_queries}")
    print("=== Exclusive Hits (only this retriever succeeded) ===")
    for source, count in exclusive_hits.items():
        percentage = count / total_queries if total_queries else 0
        print(f"{source}: {count} ({percentage:.2%})")

    print("\n=== Multiple Hit Combinations ===")
    for combo, count in sorted(combination_hits.items(), key=lambda x: -x[1]):
        combo_name = " + ".join(combo)
        percentage = count / total_queries if total_queries else 0
        print(f"{combo_name}: {count} ({percentage:.2%})")

    print("\n=== Summary ===")
    total_exclusive = sum(exclusive_hits.values())
    total_multi = sum(
        count for combo, count in combination_hits.items() if len(combo) >= 2
    )

    print(f"Queries with exclusive hits: {total_exclusive}")
    print(f"Queries with multi-retriever hits: {total_multi}")

    print("\n=== Queries with NO hits ===")
    for q in no_hit_queries:
        print(f"- {q}")

if __name__ == "__main__":
    analyze_results()