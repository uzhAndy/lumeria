from cti_app.models import Technique
from cti_app.services.prompt_templates import (
    USER_FAQ_PROMPT_ANSWER, ATTACK_STORYTELLING_PROMPT,
)
import hashlib
import json
from django.core.cache import cache


def invoke_agent(agent, campaign_id: str, user_prompt: str) -> str:
    # additional_kwargs needed for rag to filter docs and configurable needed for InMemorySaver
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_prompt, "additional_kwargs": {"campaign_id": campaign_id}}]},
        {"configurable": {"thread_id": campaign_id}},
    )
    return result["messages"][-1].content.strip()


def generate_campaign_answer_for_user_question(
    agent,
    campaign,
    question
):
    # Users may ask unpredictable FAQs that differ from the precomputed Q&A that are based on provided campaign knowledge.
    # A RAG agent is used to generate relevant context for providing accurate answers.
    prompt = USER_FAQ_PROMPT_ANSWER.format(
        campaign_name=campaign.name,
        question=question
    )
    return invoke_agent(agent, str(campaign.mitre_id), prompt)

def generate_story_cache_key(campaign_id, current_tactic):
    """
    As story outputs don't change often (displayed attack path per campaign will always be the same), build a cache for faster response
    Function creates a deterministic cache key using the campaign ID and the current tactic name to get the corresponding current story
    """
    payload = {
        "campaign_id": campaign_id,
        "current_tactic": current_tactic
    }
    raw = json.dumps(payload, sort_keys=True)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"story:{digest}"

def build_tactic_context_for_campaign_story(campaign, current_tactic):
    """
    Build previous attack steps and current tactic steps for prompt.
    """
    attack_example = campaign.attack_example.get("attack_example", [])

    previous_attack_steps = []
    current_tactic_steps = []

    for step in attack_example:
        tactic_name = step.get("tactic", "Unknown Tactic")

        if step["tactic"] == current_tactic:
            for tech in step.get("techniques", []):
                technique_obj = Technique.objects.filter(mitre_id=tech.get("technique_id")).first()
                technique_desc = technique_obj.description if technique_obj else ""
                summary = tech.get("usage_description", "No summary available")

                line = f"Name of the technique: {tech['technique_name']}, Usage description of the technique in the campaign: {summary}"
                if technique_desc:
                    technique_desc_clean = technique_desc.replace("\n", " ").replace("\r", " ").strip()
                    line += f", General description of the technique: {technique_desc_clean}"

                current_tactic_steps.append(line)
            break # stop attack_example loop when current tactic is reached (all previous tactics were collected)

        for tech in step.get("techniques", []):
            summary = tech.get("usage_description", "No summary available")
            previous_attack_steps.append(f"{tactic_name}: {tech['technique_name']} — {summary}")

    previous_tactics_string = "\n".join(previous_attack_steps)
    current_tactic_string = (
        f"Current Tactic: {current_tactic}\n"
        f"Used Techniques in this tactic:\n"
        f"{'- ' + '\n- '.join(current_tactic_steps) if current_tactic_steps else 'No techniques recorded.'}"
    )

    return previous_tactics_string, current_tactic_string


def get_story_response(agent, campaign, current_tactic):
    """
    Generate or retrieve cached story for a campaign step.
    """
    cache_key = generate_story_cache_key(
        campaign_id=campaign.id,
        current_tactic=current_tactic
    )

    # Try cache first
    cached_response = cache.get(cache_key)
    if cached_response:
        return cached_response

    # Build context
    previous_tactics_string, current_tactic_string = build_tactic_context_for_campaign_story(campaign, current_tactic)

    prompt_value = ATTACK_STORYTELLING_PROMPT.format(
        campaign=campaign.name,
        previous_attack_steps=previous_tactics_string,
        new_attack_step=current_tactic_string
    )

    # Generate response
    response_text = invoke_agent(agent, str(campaign.mitre_id), prompt_value)

    # Store in cache for future
    cache.set(cache_key, response_text, timeout=None)

    return response_text