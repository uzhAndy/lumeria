import json
import os
import django
from langchain_ollama import ChatOllama
from json_repair import repair_json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI

from cti_app.evaluation.evaluation_models import MODELS
from cti_app.services.agent_builder import build_rag_agent

def get_queries_to_evaluate():
    queries_to_evaluate = [
          {
            "query": "The following question may pertain to the campaign named 'C0027' or could be a general question about the MITRE ATT&CK framework: Who carried out this campaign?",
            "campaign_id": "campaign--df74f7ad-b10d-431c-9f1d-a2bc18dadefa"
          },
          {
            "query": "The following question may pertain to the campaign named 'SolarWinds Compromise' or could be a general question about the MITRE ATT&CK framework: How can domains be compromised?",
            "campaign_id": "campaign--808d6b30-df4e-4341-8248-724da4bac650"
          },
          {
            "query": "The following question may pertain to the campaign named 'KV Botnet Activity' or could be a general question about the MITRE ATT&CK framework: Can you explain me the technique Multi-Factor Authentication Request Generation?",
            "campaign_id": "campaign--0c259854-4044-4f6c-ac49-118d484b3e3b"
          }
    ]
    return queries_to_evaluate

def load_responses(user_query_to_evaluate):
    file_identification = user_query_to_evaluate.replace(" ", "_")
    try:
        os.makedirs("results/user_queries_responses", exist_ok=True)
        with open(f"results/user_queries_responses/model_responses_{file_identification}.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# Create a judge model to rank outputs (for final results the strongest possible model will be chosen)
# judge = ChatOpenAI(model="gpt-4o", temperature=0)
judge = ChatOllama(model="llama3.1", temperature=0)

def rank_responses(responses: list[dict], query: str) -> str:
    """
    Use a judge LLM to evaluate all responses, rank them, and provide usability feedback.
    responses: [{"provider":..., "model":..., "response":...}, ...]
    """
    system_prompt = SystemMessagePromptTemplate.from_template(
        """
        You are an expert cybersecurity content reviewer.
        You will evaluate multiple answers to the same executive query:
        "{query}"
        
        Assess each response on:
        - Clarity: How easy is it for a non-technical executive to understand?
        - Business relevance: How well does it highlight risk, impact, and strategic relevance?
        - Completeness: Are all important points addressed?
        
        Provide:
        1. Ranked list from best to worst, including provider and model.
        2. Usability grade for each response: Excellent / Good / Fair / Poor.
        3. Short rationale for each ranking.
        4. General impression of usability for each response, independent of ranking.
        
        Return ONLY valid JSON. Do NOT include code fences, markdown or any extra text. The JSON must follow exactly this structure:
        {{
            "ranked_list": [
                {{
                    "provider": "...",
                    "model": "...",
                    "rank": 1,
                    "usability_grade": "...",
                    "rationale": "...",
                    "general_usability": "..."
                }}
            ]
        }}
        """
    )

    answer_texts = "\n\n".join(
        [f"Provider: {r['provider']}\nModel: {r['model']}\nResponse:\n{r['response']}" for r in responses])
    human_prompt = HumanMessagePromptTemplate.from_template(
        """
        Here are the responses to evaluate for query: "{query}":
        
        {answer_texts}
        """
    )

    chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_prompt])
    prompt = chat_prompt.format_prompt(query=query, answer_texts=answer_texts).to_string()
    verdict = judge.invoke([{"role": "user", "content": prompt}])
    return verdict.content

def evaluate_single_response(response: dict, query: str) -> str:
    """
    Evaluate a single response independently (no comparison).
    """
    system_prompt = SystemMessagePromptTemplate.from_template(
        """
        You are an expert cybersecurity content reviewer.
        You will evaluate an answer to the following executive query:

        "{query}"

        Assess the response on:
        - Clarity: How easy is it for a non-technical executive to understand?
        - Business relevance: How well does it highlight risk, impact and strategic relevance?
        - Completeness: Are all important points addressed?

        Provide:
        - A usability grade: Excellent / Good / Fair / Poor
        - A short rationale
        - A general usability assessment

        Return ONLY valid JSON. Do NOT include code fences or extra text.

        JSON format:
        {{
            "usability_grade": "...",
            "rationale": "...",
            "general_usability": "..."
        }}
        """
    )

    human_prompt = HumanMessagePromptTemplate.from_template(
        """
        Query: "{query}"
        
        Response:
        {response}
        """
    )

    chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_prompt])

    prompt = chat_prompt.format_prompt(
        query=query,
        response=response["response"]
    ).to_string()

    verdict = judge.invoke([{"role": "user", "content": prompt}])
    return verdict.content

def main(rerun=False):
    queries = get_queries_to_evaluate()
    all_rankings = []
    all_individual_evals = []
    for entry in queries:
        user_query_to_evaluate = f"{entry["query"]}"
        campaign_to_evaluate = f"{entry["campaign_id"]}"
        responses = load_responses(user_query_to_evaluate)
        if rerun or not responses:
            responses = []
            for provider, model_name in MODELS:
                print(f"Generating response from {provider} ({model_name})")
                rag_agent = build_rag_agent(provider=provider, model_name=model_name)
                additional_kwargs = {
                    "campaign_id": campaign_to_evaluate,
                    "filter_pdf": "false",
                }
                response_text = rag_agent.invoke(
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
                responses.append({"provider": provider, "model": model_name, "response": response_text["messages"][-1].content})

            # Save raw responses
            file_identification = user_query_to_evaluate.replace(" ", "_")
            with open(f"results/user_queries_responses/model_responses_{file_identification}.json", "w") as f:
                json.dump(responses, f, indent=2)

            # Rank responses
            ranked_summary = repair_json(rank_responses(responses, user_query_to_evaluate))
            parsed = json.loads(ranked_summary)
            all_rankings.append({
                "query": user_query_to_evaluate,
                "campaign_id": campaign_to_evaluate,
                "ranking": parsed
            })

            # Usability evaluation (for each model independently to be more unbiased) ---
            individual_evaluations = []
            for r in responses:
                raw_eval = evaluate_single_response(r, user_query_to_evaluate)
                repaired = repair_json(raw_eval)
                parsed = json.loads(repaired)
                parsed["provider"] = r["provider"]
                parsed["model"] = r["model"]
                individual_evaluations.append(parsed)
            all_individual_evals.append({
                "query": user_query_to_evaluate,
                "campaign_id": campaign_to_evaluate,
                "evaluations": individual_evaluations
            })

        # Save individual evaluations
        os.makedirs("results", exist_ok=True)
        with open("results/model_responses_ranked_and_evaluated_ollama.json", "w") as f:
            json.dump(all_rankings, f, indent=2)
        with open("results/model_responses_individual_evaluation_ollama.json", "w") as f:
            json.dump(all_individual_evals, f, indent=2)

if __name__ == "__main__":
    main()