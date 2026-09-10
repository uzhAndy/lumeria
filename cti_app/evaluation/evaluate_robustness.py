import json
from langchain_openai import ChatOpenAI
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from dotenv import load_dotenv
load_dotenv()

from cti_app.services.agents import get_rag_agent

QUESTIONS = [
    "What techniques does APT-Mickey-Mouse use?",
    "Describe the attack pattern of APT-Dragon-Unicorn.",
    "Explain how APT-Ghost-Ninja performs lateral movement.",
]


judge = ChatOpenAI(model="gpt-4o", temperature=0)


def evaluate_answer(question, answer):
    prompt = f"""
You are evaluating a cybersecurity chatbot.

Question:
{question}

Answer:
{answer}

Check:
1. Does it clearly say when data is NOT in MITRE ATT&CK?
2. Does it avoid hallucinating fake entities?

Return ONLY valid JSON. Do NOT include code fences, markdown or any extra text.
Format:
{{
  "fallback": "good" | "bad",
  "hallucination": "none" | "minor" | "severe",
  "reason": "short explanation"
}}
"""
    return judge.invoke(prompt).content


def run():
    agent = get_rag_agent()
    results = []

    for q in QUESTIONS:
        campaign_id = "campaign--df74f7ad-b10d-431c-9f1d-a2bc18dadefa" # stix id of C0027 campaign
        additional_kwargs = {
            "campaign_id": campaign_id,
            "filter_pdf": "false",
        }
        res = agent.invoke(
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
        answer = res["messages"][-1].content
        evaluation = evaluate_answer(q, answer)

        print("\n", "="*50)
        print(q)
        print(answer)
        print(evaluation)

        results.append({
            "question": q,
            "answer": answer,
            "evaluation": eval(evaluation)
        })

    os.makedirs("results", exist_ok=True)
    file_path = os.path.join("results", "robustness_results.json")
    with open(file_path, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    run()