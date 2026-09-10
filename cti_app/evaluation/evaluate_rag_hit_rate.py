import ast
import json
import re
from collections import defaultdict
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from cti_app.services.agent_builder import get_llm, load_vectorstore, build_graph_retriever, build_prompt_middleware
from cti_app.services.prompt_templates import SYSTEM_PROMPT
from pathlib import Path

LOG_DIR = Path("rag_documents_from_queries")
GROUND_TRUTH_FILE = "query_to_relevant_docs.json"
RESULTS_FILE = Path("results/retrieval_evaluation.json")

def load_ground_truth():
    with open(GROUND_TRUTH_FILE, "r") as f:
        return json.load(f)

def load_retrieved_documents_file(last_message):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_identification = last_message.replace(" ", "_")
    file_path = LOG_DIR / f"{file_identification}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r") as f:
        return json.load(f)

def safe_parse(meta_str):
    # remove np.float32(...) wrappers
    cleaned = re.sub(r"np\.float32\((.*?)\)", r"\1", meta_str)
    return ast.literal_eval(cleaned)

def extract_ids_from_docs(docs):
    ids = set()
    for d in docs:
        meta = d.get("metadata", {})
        # metadata may be string -> dict
        if isinstance(meta, str):
            try:
                meta = safe_parse(meta)
            except Exception:
                meta = {}
        # common keys
        for key in ["stix_id", "target_ref", "source_ref"]:
            if key in meta:
                ids.add(meta[key])
    return ids

def evaluate(rerun=False):
    ground_truth = load_ground_truth()
    chat_llm = get_llm()
    vectorstore = load_vectorstore()
    graph_retriever = build_graph_retriever()
    prompt_middleware = build_prompt_middleware(vectorstore, graph_retriever, evaluation_mode=True)
    rag_agent = create_agent(
        model=chat_llm,
        tools=[],
        system_prompt=SYSTEM_PROMPT.format(),
        middleware=[prompt_middleware],
        checkpointer=InMemorySaver(),
    )
    retriever_hits = defaultdict(list)
    pre_reranker_hits = []
    query_hits = []
    results = []
    for entry in ground_truth:
        query_has_hit = False
        pre_reranker_hit = False
        campaign_to_evaluate = f"{entry["campaign_id"]}"
        additional_kwargs = {
            "campaign_id": campaign_to_evaluate,
            "filter_pdf": "false",
        }
        user_query_to_evaluate = f"{entry["query"]}"
        # check if query was already run and if yes, skip invocation:
        retrieved_documents = load_retrieved_documents_file(user_query_to_evaluate)
        if rerun or not retrieved_documents:
            rag_agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": user_query_to_evaluate,
                            "additional_kwargs": additional_kwargs,
                        }
                    ]
                },
                {
                    "configurable": {
                        "thread_id": campaign_to_evaluate
                    }
                }
            )
            retrieved_documents = load_retrieved_documents_file(user_query_to_evaluate)
        # print(retrieved_documents)
        retriever_results = retrieved_documents.get("retrievers", {})
        reranker_results = retrieved_documents.get("reranker", {}).get("output", [])

        entry_result = {
            "query": user_query_to_evaluate,
            "campaign_id": campaign_to_evaluate,
            "evaluation": {}
        }

        # check if documents were found from the graph cypher (can't use metadata because retrieved graph documents don't have any)
        graph_results = retrieved_documents.get("graph", None)
        graph_cypher = None
        graph_has_results = False
        if graph_results:
            graph_cypher = graph_results.get("cypher")
            graph_docs = graph_results.get("documents", [])
            graph_has_results = len(graph_docs) > 0
            if graph_has_results:
                query_has_hit = True
        entry_result["graph_evaluation"] = {
            "cypher": graph_cypher,
            "has_results": graph_has_results,
        }

        # define which document metadata is expected
        expected_ids = set()
        for key in ["stix_id", "source_ref", "target_ref"]:
            if key in entry:
                value = entry[key]
                if isinstance(value, list):
                    expected_ids.update(value)
                else:
                    expected_ids.add(value)
        # Iterate over each retriever and the reranker and check if document from ground truth file was found and collect how many documents were retrieved. Graph results are manually checked if they make sense.
        for retriever_name, docs in retriever_results.items():
            retrieved_ids = extract_ids_from_docs(docs)
            matched_ids = expected_ids.intersection(retrieved_ids)
            hit = len(matched_ids) > 0
            num_matched = len(matched_ids)
            num_expected = len(expected_ids)
            recall = num_matched / num_expected if num_expected > 0 else 0.0
            if hit:
                pre_reranker_hit = True
            retriever_hits[retriever_name].append(int(hit))
            entry_result["evaluation"][retriever_name] = {
                "num_docs": len(docs),
                "retrieved_ids": list(retrieved_ids),
                "expected_ids": list(expected_ids),
                "hit": hit,
                "recall_ratio": recall,
                "recall_binary": 1 if hit else 0
            }
        reranker_retrieved_ids = extract_ids_from_docs(reranker_results)
        reranker_matched = expected_ids.intersection(reranker_retrieved_ids)
        reranker_hit = len(reranker_matched) > 0
        reranker_num_matched = len(reranker_matched)
        reranker_recall = (reranker_num_matched / len(expected_ids) if len(expected_ids) > 0 else 0.0)
        # find documents that have at least 2 of the expected documents (or the one if only one is expected)
        k = min(2, len(expected_ids))
        reranker_recall_at_k = 1 if len(reranker_matched) >= k else 0
        retriever_hits["reranker"].append(int(reranker_hit))
        entry_result["evaluation"]["reranker"] = {
            "num_docs": len(reranker_results),
            "retrieved_ids": list(reranker_retrieved_ids),
            "expected_ids": list(expected_ids),
            "hit": reranker_hit,
            "recall_ratio": reranker_recall,
            "recall_at_k": reranker_recall_at_k,
            "recall_binary": 1 if reranker_hit else 0
        }
        # reranker contributes to final query success
        if reranker_hit:
            query_has_hit = True

        pre_reranker_hits.append(int(pre_reranker_hit))
        query_hits.append(int(query_has_hit))
        results.append(entry_result)

    retriever_avg_hit_rate = {r: sum(v) / len(v) for r, v in retriever_hits.items()}
    pre_reranker_hit_rate = (sum(pre_reranker_hits) / len(pre_reranker_hits) if pre_reranker_hits else 0.0)
    overall_hit_rate = sum(query_hits) / len(query_hits) if query_hits else 0.0
    graph_success_rate = sum(int(r["graph_evaluation"]["has_results"]) for r in results) / len(results)
    average_recall = sum(r["evaluation"]["reranker"]["recall_ratio"] for r in results) / len(results)

    output = {
        "retriever_avg_hit_rate": retriever_avg_hit_rate,
        "overall_hit_rate": overall_hit_rate,
        "pre_reranker_hit_rate": pre_reranker_hit_rate,
        "graph_success_rate": graph_success_rate,
        "results": results,
        "average_recall": average_recall,
    }
    # save full evaluation
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved evaluation to {RESULTS_FILE}")
    print("Retriever hit rates:", retriever_avg_hit_rate)
    print("Overall hit rate:", overall_hit_rate)
    print("Pre-reranker hit rate:", pre_reranker_hit_rate)
    print("Graph success rate:", graph_success_rate)
    print("Average recall:", average_recall)


if __name__ == "__main__":
    evaluate()