import time
import json
import os
import django

from cti_app.evaluation.evaluation_models import MODELS

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from cti_app.services.agent_builder import get_llm, build_rag_agent

# get env variables for running private models
from dotenv import load_dotenv
load_dotenv()

QUESTIONS = [
    "What is Spearphishing Voice?",
    "Explain privilege escalation.",
    "What was the goal of the C0027 campaign?"
]


def run():
    results = []

    for provider, model in MODELS:
        rag_agent = build_rag_agent(provider=provider, model_name=model)
        campaign_id = "campaign--df74f7ad-b10d-431c-9f1d-a2bc18dadefa"  # stix id of C0027 campaign
        additional_kwargs = {
            "campaign_id": campaign_id,
            "filter_pdf": "false",
        }

        for q in QUESTIONS:
            start = time.time()
            rag_agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": q,
                            "additional_kwargs": additional_kwargs,
                        }
                    ]
                },
                {
                    "configurable": {
                        "thread_id": campaign_id
                    }
                }
            )
            latency = time.time() - start

            print(provider, model, latency)

            results.append({
                "provider": provider,
                "model": model,
                "question": q,
                "latency": latency
            })

    # compute averages per provider and overall average
    provider_latencies = {}
    latency_sum = 0
    for r in results:
        latency_sum += r["latency"]
        provider = r["provider"]
        provider_latencies.setdefault(provider, []).append(r["latency"])
    per_provider_avg = {provider: sum(values) / len(values) for provider, values in provider_latencies.items()}
    overall_avg = latency_sum / len(results)
    output = {
        "results": results,
        "averages": {
            "per_provider": per_provider_avg,
            "overall": overall_avg
        }
    }
    os.makedirs("results", exist_ok=True)
    file_path = os.path.join("results", "latency.json",)
    with open(file_path, "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    run()