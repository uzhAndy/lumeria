import json
import os
import django
from json_repair import repair_json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.shortcuts import get_object_or_404
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI
from cti_app.evaluation.evaluation_models import MODELS
from cti_app.models import Campaign
from cti_app.services.llm_tasks import build_tactic_context_for_campaign_story, invoke_agent
from cti_app.services.prompt_templates import ATTACK_STORYTELLING_PROMPT
from cti_app.services.agent_builder import build_simple_agent_with_memory
from dotenv import load_dotenv
load_dotenv()

judge = ChatOpenAI(model="gpt-4o", temperature=0)


def rank_stories(stories: list[dict], current_tactic: str) -> str:
    """
    Rank multiple stories from different llm models and give usability grades.
    `stories` is a list of dicts: [{"provider": ..., "story": ...}, ...]
    Returns a ranked summary in plain text.
    """

    system_prompt = SystemMessagePromptTemplate.from_template(
        """
        You are an expert cybersecurity content reviewer who is unbiased.
        You will evaluate multiple stories from different llm models describing the same campaign tactic: "{current_tactic}" that was used in an attack.
        The stories may also reference tactics that were applied earlier in the same attack.
        Assess each story on:
        - Clarity: Is the explanation easy to understand?
        - Completeness: Are all relevant steps and terms explained?
        - Style: Is it engaging yet professional and readable?
        
        Provide:
        1. A ranked list from best to worst.
        2. A usability grade for each story: Excellent / Good / Fair / Poor.
        3. Short rationale for each story’s ranking.
        4. A general impression of the usability of the story, independent of the ranking.
        
         Return ONLY valid JSON. Do NOT include code fences or extra text.
         JSON format:
            {{
              "ranking": [
                {{
                  "model": "<model name>",
                  "tactic": "<tactic name>",
                  "rank": <number>,
                  "grade": "Excellent | Good | Fair | Poor",
                  "rationale": "<short explanation>"
                }}
              ],
              "overall_impression": "<summary of usability across all stories>"
            }}
        """
    )

    # Build the human prompt with all stories
    story_texts = "\n\n".join([f"Model: {s['model']}\nStory:\n{s['story']}" for s in stories])
    human_prompt = HumanMessagePromptTemplate.from_template(
        """
        Here are the stories to evaluate:
        
        {story_texts}
        
        Rank them and provide usability grades as instructed.
        """
    )

    chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_prompt])
    prompt = chat_prompt.format_prompt(story_texts=story_texts, current_tactic=current_tactic).to_messages()

    verdict = judge.invoke(prompt)
    return verdict.content


def run():
    campaign_mitre_ids = ["campaign--0c259854-4044-4f6c-ac49-118d484b3e3b", "campaign--4fdd2487-26c1-494e-8702-ec5abe9aa1d9"]  # KV Botnet Activity and Cutting Edge
    generated_stories = {}
    generated_stories_ranked = {}
    for campaign_mitre_id in campaign_mitre_ids:
        campaign = get_object_or_404(Campaign, mitre_id=campaign_mitre_id)
        current_tactic = "persistence"
        stories = []
        for provider, model_name in MODELS:
            agent = build_simple_agent_with_memory(provider=provider, model_name=model_name)
            previous_tactics_string, current_tactic_string = build_tactic_context_for_campaign_story(campaign, current_tactic)
            prompt_value = ATTACK_STORYTELLING_PROMPT.format(
                campaign=campaign.name,
                previous_attack_steps=previous_tactics_string,
                new_attack_step=current_tactic_string
            )
            response_text = invoke_agent(agent, campaign_mitre_id, prompt_value)
            stories.append({"model": model_name, "story": response_text})

        ranked_summary = json.loads(repair_json(rank_stories(stories, current_tactic=current_tactic)))
        generated_stories_ranked[campaign_mitre_id] = ranked_summary
        generated_stories[campaign_mitre_id] = stories

    os.makedirs("results", exist_ok=True)
    file_path_stories_ranking_results = os.path.join("results", "stories_ranking_results_ollama.json")
    with open(file_path_stories_ranking_results, "w") as f:
        json.dump(generated_stories_ranked, f, indent=2)
    file_path_evaluated_stories = os.path.join("results", "evaluated_stories_ollama.json")
    with open(file_path_evaluated_stories, "w") as f:
        json.dump(generated_stories, f, indent=2)


if __name__ == "__main__":
    run()